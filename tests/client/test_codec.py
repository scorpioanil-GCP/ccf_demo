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

import ast
import hashlib
import inspect
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Final, Literal, Union, get_args, get_origin

import pytest
from pydantic import ValidationError

import ccf.client.codec
from ccf.client.adapters.inprocess import InProcessAdapter
from ccf.client.codec import (
    check_outcome,
    decode_outcome,
    encode_outcome,
    verify_content_address,
)
from ccf.client.errors import TransportError
from ccf.client.wire import WireOutcome, WireRequest
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.refusal import REFUSAL_KINDS, RequestIdentity, envelope_for
from ccf.products.request import ProductRequestViolation

from tests.client.conftest import config_document

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
    if origin is tuple:
        # `tuple[X, ...]` — one member of the declared element type; an empty
        # tuple would let a field that carries nothing pass for one that does.
        inner = get_args(annotation)
        return (_sample_value(inner[0]),) if inner else ()
    if annotation is datetime:
        return _INSTANT
    if annotation is bool:
        return True
    if annotation is int:
        return 7
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        # A closed enumeration (`DebtSignal` on `DebtAssessment`): its first
        # member, which is whatever the SDK declares first — never a string
        # this fixture would have to keep in step with the enum.
        return next(iter(annotation))
    if annotation is Decimal:
        # In [0, 1]: every Decimal a refusal carries today is a D_c figure or a
        # tolerance, and both validate against that interval.
        return Decimal("0.5")
    if inspect.isclass(annotation) and issubclass(annotation, CCFContract):
        # A nested contract (Phase 24.6: `ProvenanceSource`, `ParameterBound`,
        # `DebtAssessment`) is synthesized the same way, field by field, so a
        # refusal kind that grows a typed member still needs no edit here.
        return annotation(
            **{
                name: _sample_value(field.annotation)
                for name, field in annotation.model_fields.items()
            }
        )
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
    assert_round_trip(
        original, decode_outcome(encode_outcome(original), sent=a_request()).outcome
    )


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
    decoded = decode_outcome(encode_outcome(original), sent=a_request()).outcome
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
    decoded = decode_outcome(encode_outcome(outcome), sent=a_request()).outcome
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
    decoded = decode_outcome(
        _encode_dropping_replay_ref(original), sent=a_request()
    ).outcome
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

        def ask(self, request: WireRequest) -> bytes:
            try:
                raise ConnectionRefusedError("the producer is not listening")
            except OSError:
                return encode_outcome(a_refusal_outcome(ProductRequestViolation))

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


# --------------------------------------------------------------------------
# Phase 19 — the checks that could not fail, handed bytes they must reject.
#
# `P2` and `P4` of `19-VALIDATION.md`, plus `C-04`'s refused half and the
# statement ordering `C-04` depends on. The two legs below edit the encoded
# `bytes` **after** `encode_outcome` produced them, which is strictly stronger
# than the `model_copy`-then-encode controls above it: those prove the decoder
# refuses an outcome somebody assembled wrongly, these prove it refuses bytes
# that were correct when they left the producer.
# --------------------------------------------------------------------------

#: A parameter value chosen to appear **exactly once** in an encoded outcome's
#: bytes, so a byte edit aimed at the echo cannot also land in the vessel. The
#: outcome's own payload carries numbers and names that would otherwise collide.
_ECHO_ONLY_TOKEN: Final = "sentinel-parameter-value"

def a_uniquely_valued_request() -> WireRequest:
    """The question of :func:`a_request`, with a value nothing else spells."""
    return a_request().model_copy(
        update={"parameters": {"revenue_threshold": _ECHO_ONLY_TOKEN}}
    )


def _vessel_text_of(raw: bytes) -> str:
    """The served vessel inside ``raw``, by a raw parse and nothing more.

    Never :func:`~ccf.client.codec.decode_outcome`: the decoder runs the very
    checks these legs exist to trip, so it would raise before this could read
    anything.
    """
    vessel = WireOutcome.model_validate_json(raw).product_json
    assert vessel is not None
    return vessel


def _assert_the_tamper_is_attributable(raw: bytes) -> None:
    """The discrimination guard: the tampered vessel still parses and validates.

    ``19-RESEARCH.md`` Pitfall 3. :func:`~ccf.client.codec.check_outcome`
    recomputes the address **before** it parses the contract, so a tamper that
    corrupted the vessel into unparseability raises with the same address
    wording and the leg stays green while proving that the parser fires. This
    is what makes the failure attributable to the check under test.
    """
    tampered = _vessel_text_of(raw)
    try:
        json.loads(tampered)
        ContextProductContract.model_validate_json(tampered)
    except Exception as unattributable:
        raise AssertionError(
            "the tampered vessel no longer parses as JSON or no longer"
            f" validates as a product contract — {unattributable} — so the"
            " `TransportError` the leg caught is not attributable to the check"
            " it names"
        ) from unattributable


def test_a_byte_edit_inside_the_vessel_is_caught_by_the_address_check() -> None:
    """`P2`(b): post-encoding byte sabotage, no transport involved at all.

    One token inside the served vessel is changed in the **encoded bytes**, and
    the producer's ``content_address`` is left exactly where it was — which is
    the corruption, truncation or re-serializing intermediary ``C-10`` names.
    """
    honest = encode_outcome(a_served_outcome())
    # `.replace` over the encoded **bytes**, never a `model_copy` over the
    # outcome: the model form is the control two sections up, and this one has
    # to be a post-encoding edit to be strictly stronger than it. `globex` is a
    # payload name :func:`a_vessel` spells once and the echo does not spell at
    # all, so this edit cannot land anywhere but inside the vessel.
    tampered = honest.replace(b"globex", b"globey")
    assert tampered != honest, "the byte edit found nothing to change"

    with pytest.raises(TransportError, match="content address"):
        decode_outcome(tampered, sent=a_request())

    _assert_the_tamper_is_attributable(tampered)
    # The vacuity guard: the untampered bytes are served and do not raise.
    assert decode_outcome(honest, sent=a_request()).outcome.refusal is None


def test_a_byte_edit_inside_the_echo_is_caught_by_the_question_comparison() -> None:
    """`P2`(b)'s sibling on the other operand — the echoed question's own bytes.

    The vessel and its address are untouched, so the address check passes and
    only the comparison against the question that was sent can catch this.
    """
    asked = a_uniquely_valued_request()
    honest = encode_outcome(a_served_outcome().model_copy(update={"request": asked}))
    assert _ECHO_ONLY_TOKEN.encode("utf-8") in honest, (
        "the token this edit aims at is not in the encoded bytes, so the"
        " literal below and `_ECHO_ONLY_TOKEN` have drifted apart"
    )
    tampered = honest.replace(b"sentinel-parameter-value", b"sentinel-parameter-valuf")
    assert tampered != honest, "the byte edit found nothing to change"

    with pytest.raises(TransportError, match="different question"):
        decode_outcome(tampered, sent=asked)

    # The discrimination guard, in its form for this leg: the vessel this edit
    # never touched is still whole, so the failure is the echo's and not the
    # parser's or the contract check's.
    _assert_the_tamper_is_attributable(tampered)
    assert _vessel_text_of(tampered) == _vessel_text_of(honest)
    # The vacuity guard.
    assert decode_outcome(honest, sent=asked).outcome.refusal is None


def test_a_refusal_echoing_a_question_nobody_asked_is_a_transport_failure(
    seeded_root: Path,
) -> None:
    """`C-04`: one comparison covers a served answer **and** a refusal.

    Until this leg, ``C-04``'s claim was a consequence of statement order
    rather than a measurement — nothing in the tree asserted that the echo
    comparison reaches a refused outcome at all. A crossed refusal is a
    governed "no" attributed to a question nobody asked, and a caller who
    branched correctly on it records an audited refusal that never happened
    about something they never asked.

    The refusal is **captured from the fixture deployment**, never synthesized:
    an invented one would name a refusal vocabulary the fabric does not speak,
    and the leg would then be exercising an outcome no producer could emit.
    """
    declared = config_document(seeded_root)
    refusing = WireRequest(
        product_id=str(declared["product_class"]["schema_name"]),
        parameters={},
        temporal_boundary=_INSTANT,
    )
    captured = WireOutcome.model_validate_json(
        InProcessAdapter(str(seeded_root)).ask(refusing)
    )
    assert captured.refusal is not None, (
        "the fixture served the question this leg needs refused, so there is no"
        " refusal here to attribute to anything"
    )

    parameter = str(declared["request_contract"]["arguments"]["required"][0])
    asked_instead = refusing.model_copy(update={"parameters": {parameter: 0}})
    with pytest.raises(TransportError, match="different question"):
        check_outcome(captured, sent=asked_instead)

    # The vacuity guard: the same refusal against the question it answers is a
    # governed value, not a failure — `check_outcome` returns `None` for it.
    assert check_outcome(captured, sent=refusing) is None


# --------------------------------------------------------------------------
# The ordering `C-04` depends on, asserted over source rather than assumed.
# --------------------------------------------------------------------------


def _is_echo_comparison(statement: ast.stmt) -> bool:
    """``if outcome.request != sent:`` — matched on shape, not on text."""
    if not isinstance(statement, ast.If) or not isinstance(
        statement.test, ast.Compare
    ):
        return False
    left = statement.test.left
    return (
        isinstance(left, ast.Attribute)
        and left.attr == "request"
        and any(isinstance(op, ast.NotEq) for op in statement.test.ops)
    )


def _is_refusal_branch(statement: ast.stmt) -> bool:
    """``if outcome.product_json is None:`` — the served/refused fork."""
    if not isinstance(statement, ast.If) or not isinstance(
        statement.test, ast.Compare
    ):
        return False
    left = statement.test.left
    return (
        isinstance(left, ast.Attribute)
        and left.attr == "product_json"
        and any(isinstance(op, ast.Is) for op in statement.test.ops)
    )


def assert_the_echo_check_precedes_the_refusal_branch(source: str) -> None:
    """`C-04`'s precondition: the echo comparison runs before the refusal fork.

    ``C-04`` puts the echo at outcome level so *one* comparison covers a served
    answer and a refusal identically. That holds only while the comparison sits
    **above** the ``product_json is None`` return — a refactor that moved it
    below would silently uncover the refusal half, and every behavioural test
    in this module would stay green.

    Takes the module **source text** rather than reading a path itself, on the
    ``tests/client/test_surface.py::count_result_construction_sites``
    discipline: a control can then feed it a reordered copy that the function
    genuinely reads.

    It **raises** rather than returning a boolean, and it raises when it cannot
    find either statement — a scan that silently found nothing is a gate that
    silently stopped gating, which this repo has shipped once already.

    Raises:
        AssertionError: ``check_outcome`` is absent, either statement is
            absent, or the echo comparison does not come first.
    """
    functions = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef) and node.name == "check_outcome"
    ]
    if len(functions) != 1:
        raise AssertionError(
            f"the source handed to this guard defines {len(functions)}"
            " functions named `check_outcome` where exactly one was expected,"
            " so the ordering it is meant to hold was never located — a scan"
            " that finds nothing and reports nothing is a gate that stopped"
            " gating"
        )
    body = functions[0].body
    echo = next(
        (i for i, node in enumerate(body) if _is_echo_comparison(node)), None
    )
    refusal = next(
        (i for i, node in enumerate(body) if _is_refusal_branch(node)), None
    )
    if echo is None or refusal is None:
        raise AssertionError(
            "`check_outcome` was found but its statements were not — located"
            f" the echo comparison at {echo} and the refusal branch at"
            f" {refusal}, and `None` means the shape this guard matches on has"
            " changed. It refuses to pass on a scan that found nothing"
        )
    if echo >= refusal:
        raise AssertionError(
            f"`check_outcome` runs the echo comparison at statement {echo} and"
            f" the refusal branch at statement {refusal} — the comparison must"
            " come first, or a refused outcome returns before it is ever"
            " compared and `C-04`'s claim that one comparison covers a served"
            " answer and a refusal identically stops being true"
        )


def test_the_shipped_decoder_compares_the_echo_before_it_returns_a_refusal() -> None:
    """The guard above, over `codec.py`'s **real** source, pinned by module name.

    ``inspect.getsource`` of the imported module rather than a path this test
    composes: a count of calls to the guard proves nothing about which source
    they were handed, and three calls on three synthetic strings would satisfy
    every occurrence check while asserting nothing about the shipped decoder.
    """
    source = inspect.getsource(ccf.client.codec)
    assert "def check_outcome" in source, (
        "the source this test is about to hand the guard does not define"
        " `check_outcome`, so whatever the guard says next is about something"
        " other than the shipped decoder"
    )
    assert_the_echo_check_precedes_the_refusal_branch(source)


#: ``check_outcome``'s two statements, swapped. Synthetic on purpose — the
#: control has to feed the guard source the shipped module does not contain,
#: and editing the shipped file and reverting it would leave nothing in the
#: tree.
_REORDERED_SOURCE: Final = '''
def check_outcome(outcome, *, sent):
    """A copy in which the refusal returns before anything is compared."""
    if outcome.product_json is None:
        return None
    if outcome.request != sent:
        raise TransportError("the outcome echoes a different question")
    return None
'''


def test_control_the_ordering_guard_fires_on_a_reordered_decoder() -> None:
    """`D-22`: the named sabotage for the ordering guard.

    The guard is handed a ``check_outcome`` whose refusal branch returns first,
    which is exactly the refactor that would uncover ``C-04``'s refusal half
    while every behavioural test stayed green.
    """
    with pytest.raises(AssertionError, match="the comparison must come first"):
        assert_the_echo_check_precedes_the_refusal_branch(_REORDERED_SOURCE)


def test_control_the_ordering_guard_refuses_a_scan_that_found_nothing() -> None:
    """The other way the guard could go quiet: it never located its subject.

    A gate that reports success because it found nothing to check is the
    failure mode this repo has already shipped once, so the guard raises rather
    than passes and this is the assertion that says so.
    """
    with pytest.raises(AssertionError, match="0 functions named `check_outcome`"):
        assert_the_echo_check_precedes_the_refusal_branch("x = 1\n")


# --------------------------------------------------------------------------
# `P4` — the guard that prevents a FALSE failure, shown preventing one.
# --------------------------------------------------------------------------


def test_the_parameter_guard_is_what_prevents_a_false_wire_failure() -> None:
    """`P4`: bypass `_parameters_survive_the_wire` and a healthy wire "fails".

    :meth:`~ccf.products.door.WireRequest._parameters_survive_the_wire` states
    the mechanism it exists to prevent: canonical JSON renders a ``Decimal`` as
    text, the decoded echo then differs from what was sent, and the decoder
    reports a ``TransportError`` on a wire that worked perfectly. Nothing went
    wrong here — the outcome was encoded once and decoded once — and the client
    still reports the wire as broken. That is why the value is refused at
    construction, where the message can name the wire-stable spelling, rather
    than at the decoder, where nothing can diagnose it.

    The vacuity twin is the second half of the same test and cannot be deleted
    without leaving the first obviously bare: the identical flow with the value
    rendered as ``str`` — which the guard **admits** — round-trips and does not
    raise.
    """
    # The sabotage, named: `model_construct` skips validation, which is the
    # only way to hold a `WireRequest` the guard would have refused.
    bypassed = WireRequest.model_construct(
        product_id="ccf.test-product",
        parameters={"revenue_threshold": Decimal("1000000.50")},
        temporal_boundary=_INSTANT,
    )
    outcome = a_served_outcome().model_copy(update={"request": bypassed})
    with pytest.raises(TransportError, match="different question"):
        decode_outcome(encode_outcome(outcome), sent=bypassed)

    # The vacuity twin: the spelling the guard admits, and the wire is fine.
    admitted = WireRequest(
        product_id="ccf.test-product",
        parameters={"revenue_threshold": format(Decimal("1000000.50"), "f")},
        temporal_boundary=_INSTANT,
    )
    survived = a_served_outcome().model_copy(update={"request": admitted})
    assert (
        decode_outcome(encode_outcome(survived), sent=admitted).outcome.request
        == admitted
    )
