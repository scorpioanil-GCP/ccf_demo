"""The codec is the single point of parity failure, so it gets the densest tests.

``D-20``. Every transport's output enters the client through one decode, so a
property proven here holds for every adapter that ever ships, and a property
*not* proven here is one each adapter gets to break in its own way.

The sabotage controls (``D-22``) live at the bottom of this module. Each one
constructs a deliberately broken subject and passes it into the **shipped**
assertion — :func:`assert_round_trip` or
:func:`~ccf.client.codec.verify_content_address` — rather than re-implementing
the check. A control that re-implements the comparison proves only that the copy
fires.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final, Literal, Union, get_args, get_origin

import pytest
from pydantic import ValidationError

from ccf.client.codec import decode_outcome, encode_outcome, verify_content_address
from ccf.client.errors import TransportError
from ccf.client.wire import WireOutcome, WireRequest
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.refusal import REFUSAL_KINDS, RequestIdentity, envelope_for
from ccf.products.request import ProductRequestViolation

_INSTANT: Final = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)


# --------------------------------------------------------------------------
# Subjects
# --------------------------------------------------------------------------


def a_vessel(*, expires_at: datetime | None = None) -> ContextProductContract:
    """A served product, in the shape every door already emits."""
    return ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id="acme-bank",
        temporal_boundary=_INSTANT,
        expires_at=expires_at or datetime(2026, 9, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=_INSTANT,
        ),
        payload={"companies": ["acme", "globex"], "threshold": 1000000},
    )


def a_request() -> WireRequest:
    return WireRequest(
        product_id="ccf.test-product",
        parameters={"revenue_threshold": 1000000},
        temporal_boundary=_INSTANT,
    )


def a_served_outcome(
    *, vessel: ContextProductContract | None = None, replay_ref: str | None = "replay-1"
) -> WireOutcome:
    """The served half, addressed exactly as an adapter must address it."""
    product_json = canonical_bytes(vessel or a_vessel()).decode("utf-8")
    return WireOutcome(
        request=a_request(),
        product_json=product_json,
        content_address=hashlib.sha256(product_json.encode("utf-8")).hexdigest(),
        replay_ref=replay_ref,
        refusal=None,
    )


def _sample_value(annotation: Any) -> Any:
    """A type-appropriate value for one declared field of a refusal type.

    Driven by the annotation rather than by a per-type table, so the refusal
    round-trip stays parameterized over :data:`REFUSAL_KINDS` itself and a
    refusal type gaining a field next year needs no edit here.
    """
    origin = get_origin(annotation)
    if origin is Literal:
        return get_args(annotation)[0]
    if origin is Union or str(origin) == "<class 'types.UnionType'>":
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        return _sample_value(non_none[0])
    if origin in (frozenset, set):
        return frozenset({"a", "b"})
    if annotation is datetime:
        return _INSTANT
    if annotation is bool:
        return True
    if annotation is int:
        return 7
    return "x"


def a_refusal_outcome(refusal_type: type[CCFContract]) -> WireOutcome:
    """The refused half, for one specific kind — never a generic stand-in."""
    refusal = refusal_type(
        **{
            name: _sample_value(field.annotation)
            for name, field in refusal_type.model_fields.items()
        }
    )
    envelope = envelope_for(
        refusal,
        request=RequestIdentity(
            product_id="ccf.test-product",
            product_version="1.0.0",
            parameters={"revenue_threshold": 1000000},
            temporal_boundary=_INSTANT,
        ),
    )
    return WireOutcome(
        request=a_request(),
        product_json=None,
        content_address=None,
        replay_ref=None,
        refusal=envelope,
    )


# --------------------------------------------------------------------------
# The shipped comparison — one definition, used by the tests AND the controls
# --------------------------------------------------------------------------


def assert_round_trip(original: WireOutcome, decoded: WireOutcome) -> None:
    """Assert the decoded outcome is the value that was encoded.

    **Whole value, never a projection.** Comparing a field selection would pass
    on a codec that silently drops every field outside the selection, which is
    exactly the defect a round-trip test exists to catch. Control
    :func:`test_control_a_narrowed_comparison_passes_where_the_shipped_one_fails`
    proves this function is not such a selection, by behaviour rather than by
    reading its own source.
    """
    assert decoded == original


# --------------------------------------------------------------------------
# Behaviors
# --------------------------------------------------------------------------


def test_a_served_outcome_survives_the_round_trip_whole() -> None:
    original = a_served_outcome()
    assert_round_trip(original, decode_outcome(encode_outcome(original), sent=a_request()))


@pytest.mark.parametrize(
    "refusal_type",
    list(REFUSAL_KINDS),
    ids=[token for token in REFUSAL_KINDS.values()],
)
def test_every_refusal_kind_survives_the_round_trip_whole(
    refusal_type: type[CCFContract],
) -> None:
    """Parameterized over `REFUSAL_KINDS` itself, never over a copied list.

    A copied list is a list that stops matching the tree. `D-28`(a) says the
    envelope carries every kind *without flattening*; if it lost which kind a
    refusal was, `Result.refusal.reason` becomes mush and the auditable-refusal
    guarantee dies at the seam — so every kind is exercised, not a sample.
    """
    original = a_refusal_outcome(refusal_type)
    decoded = decode_outcome(encode_outcome(original), sent=a_request())
    assert_round_trip(original, decoded)
    assert decoded.refusal is not None
    assert decoded.refusal.kind == REFUSAL_KINDS[refusal_type]


def test_the_decoder_recomputes_the_address_and_refuses_a_wire_that_disagrees() -> None:
    original = a_served_outcome()
    assert original.product_json is not None
    tampered = original.model_copy(update={"content_address": "0" * 64})
    with pytest.raises(TransportError, match="content address"):
        decode_outcome(encode_outcome(tampered), sent=a_request())


def test_the_recomputed_address_is_the_vessels_own_content_hash() -> None:
    """The identity the whole encoding ruling rests on — asserted, not reasoned about.

    `product_json` is `canonical_bytes(product).decode("utf-8")` by
    construction, so hashing its UTF-8 bytes is hashing the product's canonical
    bytes. If this ever parted, the client would publish an address no producer
    would agree with.
    """
    vessel = a_vessel()
    outcome = a_served_outcome(vessel=vessel)
    decoded = decode_outcome(encode_outcome(outcome), sent=a_request())
    assert decoded.product_json is not None
    recomputed = hashlib.sha256(decoded.product_json.encode("utf-8")).hexdigest()
    assert recomputed == content_hash(vessel)
    assert recomputed == decoded.content_address


def test_an_echo_naming_a_different_question_is_a_transport_failure() -> None:
    """A transport that answered a *different* question than the one asked.

    Reconstruction from the sent request is cheaper and cannot detect this at
    all; only comparing what came back against what was asked can.
    """
    other = WireRequest(
        product_id="ccf.some-other-product",
        parameters={"revenue_threshold": 1000000},
        temporal_boundary=_INSTANT,
    )
    outcome = a_served_outcome().model_copy(update={"request": other})
    with pytest.raises(TransportError, match="different question"):
        decode_outcome(encode_outcome(outcome), sent=a_request())


@pytest.mark.parametrize(
    ("label", "raw"),
    [
        ("not json at all", b"this is not json"),
        ("empty object", b"{}"),
        ("valid json, wrong shape", b'{"request": 3}'),
        ("truncated", canonical_bytes(a_served_outcome())[:40]),
        ("unknown member", b'{"request": {}, "surprise": 1}'),
    ],
)
def test_a_malformed_wire_raises_and_never_returns_a_refusal(
    label: str, raw: bytes
) -> None:
    """A broken wire is not a governed "no".

    This is the leg where `except Exception: return refusal` silently inverts
    `D-07`/`D-10`: the caller branches correctly on a refusal that never
    happened and records an audited "no" the fabric never said.
    """
    with pytest.raises(TransportError):
        decode_outcome(raw, sent=a_request())


def test_encoding_the_same_outcome_twice_is_byte_identical() -> None:
    outcome = a_served_outcome()
    assert encode_outcome(outcome) == encode_outcome(outcome)


def test_a_served_outcome_is_itself_canonically_serializable() -> None:
    """The property that would have failed outright under a byte-string field."""
    assert canonical_bytes(a_served_outcome()).startswith(b"{")


# --------------------------------------------------------------------------
# Sabotage controls (D-22)
#
# Each constructs a deliberately broken subject and passes it into the SHIPPED
# assertion. A control that re-implements the check proves the copy fires. None
# is performed by editing a `src/` file and reverting — an edit that gets
# reverted leaves nothing in the tree, while a control implemented as a test
# runs on every CI run forever.
# --------------------------------------------------------------------------


def _encode_dropping_replay_ref(outcome: WireOutcome) -> bytes:
    """A saboteur encoder that drops one member's value on the way out.

    Control 1's subject. Deliberately a member the outcome's own validator
    permits to be absent, so the bytes still decode — a saboteur producing
    undecodable bytes would prove the *parser* fires, not the comparison.
    """
    return encode_outcome(outcome.model_copy(update={"replay_ref": None}))


def test_control_a_field_dropped_from_the_encoder_fails_the_round_trip() -> None:
    """Control 1 — the round-trip assertion is not vacuous."""
    original = a_served_outcome(replay_ref="replay-1")
    decoded = decode_outcome(_encode_dropping_replay_ref(original), sent=a_request())
    with pytest.raises(AssertionError):
        assert_round_trip(original, decoded)


def test_control_a_narrowed_comparison_passes_where_the_shipped_one_fails() -> None:
    """Control 2 — the projection trap, decided by behaviour not by inspection.

    One divergent pair, two assertions about it. A deliberately narrowed
    comparison — only the parsed ``payload`` — **passes** on the pair, while the
    shipped :func:`assert_round_trip` **fails** on it. Together those prove the
    shipped comparison is over the whole value and not a projection of it,
    without the test needing to read its own assertion's source.
    """
    original = a_served_outcome(vessel=a_vessel())
    divergent = a_served_outcome(
        vessel=a_vessel(expires_at=datetime(2027, 1, 1, tzinfo=UTC))
    )
    assert original.product_json is not None
    assert divergent.product_json is not None

    # The narrowed comparison a lazy round-trip test would have written.
    left = ContextProductContract.model_validate_json(original.product_json)
    right = ContextProductContract.model_validate_json(divergent.product_json)
    assert left.payload == right.payload  # the projection is blind to the change

    with pytest.raises(AssertionError):
        assert_round_trip(original, divergent)  # the shipped comparison sees it


def test_control_a_refusal_with_its_key_stripped_fails_the_round_trip() -> None:
    """Control 3 — a refusal that loses what it named is not equal to itself.

    ``D-28``(a): losing which parameter a refusal named is exactly the
    flattening the envelope exists to prevent.
    """
    original = a_refusal_outcome(ProductRequestViolation)
    assert original.refusal is not None
    assert original.refusal.key is not None
    stripped = original.model_copy(
        update={"refusal": original.refusal.model_copy(update={"key": None})}
    )
    with pytest.raises(AssertionError):
        assert_round_trip(original, stripped)


def test_control_a_permissive_address_check_tolerates_what_the_shipped_one_refuses() -> (
    None
):
    """Control 4 — the address check is the thing doing the work.

    The shipped :func:`~ccf.client.codec.verify_content_address` raises on a
    mismatched pair. A permissive stand-in with the same signature returns
    instead, and the address leg built on the stand-in then passes on that very
    pair — which is what proves the shipped check, and not something else on the
    decode path, is what makes the address test meaningful.
    """
    text = '{"a": 1}'
    wrong = "0" * 64

    def address_leg(verifier: Any) -> None:
        verifier(text, wrong)

    with pytest.raises(TransportError):
        address_leg(verify_content_address)

    def permissive(product_json: str, claimed: str) -> str:
        return claimed

    address_leg(permissive)  # passes on the identical pair — no assertion fires


def test_control_an_adapter_swallowing_its_wire_failure_is_detected() -> None:
    """Control 5 — ``except Exception: return refusal`` does not pass silently.

    Without this control the inversion ``D-07``/``D-10`` exist to prevent is
    invisible: the swallowing adapter returns a well-formed refusal, every
    round-trip test still passes, and a caller records an audited "no" the
    fabric never said. The detection is that the honest contract — asking a dead
    transport raises — stops holding.
    """

    class SwallowingAdapter:
        """A transport reporting a governed "no" when nothing was ever asked."""

        def ask(self, request: WireRequest) -> WireOutcome:
            try:
                raise ConnectionRefusedError("the producer is not listening")
            except OSError:
                return a_refusal_outcome(ProductRequestViolation)

    adapter = SwallowingAdapter()
    # The assertion every conforming adapter must satisfy (D-15, leg four).
    # It FAILS against the swallowing adapter, which is the whole control.
    with pytest.raises(pytest.fail.Exception):
        with pytest.raises(TransportError):
            adapter.ask(a_request())


@pytest.mark.parametrize(
    ("label", "product_json", "content_address", "carries_refusal"),
    [
        ("both halves", '{"a": 1}', "0" * 64, True),
        ("neither half", None, None, False),
    ],
)
def test_control_a_wire_outcome_with_both_halves_or_neither_is_refused(
    label: str,
    product_json: str | None,
    content_address: str | None,
    carries_refusal: bool,
) -> None:
    """Control 6 — the two-state invariant is enforced, not documented."""
    envelope = (
        a_refusal_outcome(ProductRequestViolation).refusal if carries_refusal else None
    )
    with pytest.raises(ValidationError):
        WireOutcome(
            request=a_request(),
            product_json=product_json,
            content_address=content_address,
            replay_ref=None,
            refusal=envelope,
        )
