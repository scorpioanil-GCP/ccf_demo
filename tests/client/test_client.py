"""``ProductClient`` — the question that goes out and the one shape that comes back.

``D-04``, ``D-07``, ``D-12``. ``tests/client/test_surface.py`` proves the
decoder is the *only* place a :class:`~ccf.client.result.Result` is built; this
module proves the decoder is *right*, which is the half that would otherwise be
left to the adapter plans that come after.

The tests that matter most are the two at the bottom
-----------------------------------------------------
``D-11`` types the adapter seam as returning a
:class:`~ccf.client.wire.WireOutcome` **object**, not bytes. So an adapter that
never went near :mod:`ccf.client.codec` can hand the client a perfectly
well-formed outcome that answers a different question, or carries a content
address that disagrees with the bytes it describes. The client re-runs
:func:`~ccf.client.codec.check_outcome` on everything it is handed for exactly
that reason, and the two adapters at the bottom of this module are the subjects
that prove it: each is a *conforming* transport in the type-checker's eyes and
a lying one in fact.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final

import pytest

from ccf.client.binding import BINDING_ENV_VAR, SCHEME_REGISTRY
from ccf.client.client import ProductClient
from ccf.client.errors import BindingError, RefusedResultError, TransportError
from ccf.client.result import Result
from ccf.client.wire import WireOutcome, WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.refusal import RequestIdentity, envelope_for
from ccf.products.request import ProductRequestViolation

_PRODUCT: Final = "ccf.test-product"
_INSTANT: Final = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
_PARAMETERS: Final[Mapping[str, Any]] = {"revenue_threshold": 1000000}


# --------------------------------------------------------------------------
# Subjects
# --------------------------------------------------------------------------


def a_vessel() -> ContextProductContract:
    return ContextProductContract(
        schema_name=_PRODUCT,
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id="acme-bank",
        temporal_boundary=_INSTANT,
        expires_at=datetime(2026, 9, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=_INSTANT,
        ),
        payload={"companies": ["acme", "globex"], "threshold": 1000000},
    )


def served_outcome_for(request: WireRequest) -> WireOutcome:
    product_json = canonical_bytes(a_vessel()).decode("utf-8")
    return WireOutcome(
        request=request,
        product_json=product_json,
        content_address=hashlib.sha256(product_json.encode("utf-8")).hexdigest(),
        replay_ref="replay-1",
        refusal=None,
    )


def refused_outcome_for(request: WireRequest) -> WireOutcome:
    envelope = envelope_for(
        ProductRequestViolation(
            reason="missing-required-parameter",
            key="revenue_threshold",
            declared_type="int",
            presented_type=None,
            declared_keys=frozenset({"revenue_threshold"}),
            presented_keys=frozenset(),
            detail="the class declares `revenue_threshold` and none was supplied",
        ),
        request=RequestIdentity(
            product_id=_PRODUCT,
            product_version="1.0.0",
            parameters=request.parameters,
            temporal_boundary=request.temporal_boundary,
        ),
    )
    return WireOutcome(
        request=request,
        product_json=None,
        content_address=None,
        replay_ref=None,
        refusal=envelope,
    )


class _ServingAdapter:
    """A transport that answers, and records the question it was asked."""

    def __init__(self) -> None:
        self.asked: list[WireRequest] = []

    def ask(self, request: WireRequest) -> WireOutcome:
        self.asked.append(request)
        return served_outcome_for(request)


class _RefusingAdapter:
    """A transport whose producer refused — the fabric working."""

    def ask(self, request: WireRequest) -> WireOutcome:
        return refused_outcome_for(request)


class _DeadAdapter:
    """A transport that never spoke."""

    def ask(self, request: WireRequest) -> WireOutcome:
        raise TransportError("the connection would not open")


def a_client(adapter: Any) -> ProductClient:
    return ProductClient(product_id=_PRODUCT, adapter=adapter)


# --------------------------------------------------------------------------
# The question that goes out
# --------------------------------------------------------------------------


def test_ask_carries_the_clients_product_id_and_the_callers_parameters() -> None:
    adapter = _ServingAdapter()

    a_client(adapter).ask(parameters=_PARAMETERS, as_of=_INSTANT)

    assert len(adapter.asked) == 1
    sent = adapter.asked[0]
    assert sent.product_id == _PRODUCT
    assert sent.parameters == _PARAMETERS
    assert sent.temporal_boundary == _INSTANT


def test_as_of_none_travels_as_an_absent_temporal_boundary() -> None:
    """``D-04``: ``None`` defers to the server's decision instant.

    Asserted on the wire rather than in prose, because the alternative
    implementation — the client filling in its own clock — is invisible from
    the caller's side and would make two clients disagree about "now".
    """
    adapter = _ServingAdapter()

    a_client(adapter).ask(parameters=_PARAMETERS)

    assert adapter.asked[0].temporal_boundary is None


def test_an_empty_parameter_mapping_is_a_question_and_not_an_omission() -> None:
    adapter = _ServingAdapter()

    a_client(adapter).ask(parameters={})

    assert adapter.asked[0].parameters == {}


# --------------------------------------------------------------------------
# The served half
# --------------------------------------------------------------------------


def test_a_served_outcome_becomes_a_served_result() -> None:
    result = a_client(_ServingAdapter()).ask(parameters=_PARAMETERS, as_of=_INSTANT)

    assert isinstance(result, Result)
    assert result.refused is False
    assert result.refusal is None


def test_a_served_result_carries_the_vessels_own_members() -> None:
    result = a_client(_ServingAdapter()).ask(parameters=_PARAMETERS, as_of=_INSTANT)
    vessel = a_vessel()

    assert result.payload == vessel.payload
    assert result.lineage == vessel.lineage
    assert result.expires_at == vessel.expires_at
    assert result.debt is vessel.debt is None
    assert result.replay_ref == "replay-1"


def test_a_served_result_carries_the_recomputed_content_address() -> None:
    result = a_client(_ServingAdapter()).ask(parameters=_PARAMETERS, as_of=_INSTANT)

    expected = hashlib.sha256(
        canonical_bytes(a_vessel()).decode("utf-8").encode("utf-8")
    ).hexdigest()
    assert result.content_address == expected


def test_a_served_result_carries_the_request_identity() -> None:
    result = a_client(_ServingAdapter()).ask(parameters=_PARAMETERS, as_of=_INSTANT)

    assert result.product_id == _PRODUCT
    assert result.parameters == _PARAMETERS
    assert result.temporal_boundary == _INSTANT


# --------------------------------------------------------------------------
# The refused half — a value, and still auditable
# --------------------------------------------------------------------------


def test_a_refusal_is_returned_and_never_raised() -> None:
    """``D-07``: the gates ran and the governed answer was "no"."""
    result = a_client(_RefusingAdapter()).ask(parameters={}, as_of=_INSTANT)

    assert result.refused is True
    assert result.refusal is not None
    assert result.refusal.reason == "missing-required-parameter"
    assert result.refusal.key == "revenue_threshold"
    assert result.refusal.kind == "product-request-violation"


def test_a_refused_result_from_the_client_still_guards_its_payload() -> None:
    """``D-08`` reaches the caller through the real path, not only in unit form."""
    result = a_client(_RefusingAdapter()).ask(parameters={}, as_of=_INSTANT)

    with pytest.raises(RefusedResultError, match="payload"):
        result.payload


def test_a_refused_result_keeps_the_question_that_was_refused() -> None:
    result = a_client(_RefusingAdapter()).ask(parameters={}, as_of=_INSTANT)

    assert result.product_id == _PRODUCT
    assert result.temporal_boundary == _INSTANT


# --------------------------------------------------------------------------
# The wire failing
# --------------------------------------------------------------------------


def test_a_transport_failure_propagates_and_yields_no_result() -> None:
    """``D-10``/``D-15(d)``: a wire failure never masquerades as a refusal."""
    with pytest.raises(TransportError):
        a_client(_DeadAdapter()).ask(parameters=_PARAMETERS)


# --------------------------------------------------------------------------
# The client trusts no adapter — the two lying transports
# --------------------------------------------------------------------------


class _CrossedQuestionAdapter:
    """A conforming transport that answers a question nobody asked.

    The multiplexing bug, in the shape it actually takes: two questions in
    flight and the answers swapped. Both outcomes are well-formed, so nothing
    but a comparison against what was sent can tell them apart.
    """

    def ask(self, request: WireRequest) -> WireOutcome:
        other = WireRequest(
            product_id=request.product_id,
            parameters={"revenue_threshold": 999},
            temporal_boundary=request.temporal_boundary,
        )
        return served_outcome_for(other)


def test_an_outcome_answering_a_different_question_is_a_transport_error() -> None:
    """The client re-checks the echo itself rather than trusting the adapter.

    Without this, an adapter that builds its ``WireOutcome`` directly — which
    the seam's own type permits — hands the caller a well-formed answer to the
    wrong question, labelled with the question they meant to ask.
    """
    with pytest.raises(TransportError, match="different question"):
        a_client(_CrossedQuestionAdapter()).ask(parameters=_PARAMETERS)


class _AlteredVesselAdapter:
    """A conforming transport whose vessel does not hash to its own address."""

    def ask(self, request: WireRequest) -> WireOutcome:
        honest = served_outcome_for(request)
        return WireOutcome(
            request=request,
            product_json=honest.product_json,
            content_address="0" * 64,
            replay_ref=honest.replay_ref,
            refusal=None,
        )


def test_a_vessel_that_does_not_hash_to_its_address_is_a_transport_error() -> None:
    """The address is recomputed on arrival and the claim is never trusted."""
    with pytest.raises(TransportError, match="content address"):
        a_client(_AlteredVesselAdapter()).ask(parameters=_PARAMETERS)


# --------------------------------------------------------------------------
# for_product — the binding, end to end
# --------------------------------------------------------------------------


def test_for_product_builds_a_client_over_the_scheme_the_binding_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        SCHEME_REGISTRY,
        "fake",
        lambda address: _ServingAdapter(),  # type: ignore[arg-type,return-value]
    )

    client = ProductClient.for_product(_PRODUCT, binding="fake:./deployment")
    result = client.ask(parameters=_PARAMETERS, as_of=_INSTANT)

    assert client.product_id == _PRODUCT
    assert result.refused is False


def test_for_product_reads_the_environment_when_no_binding_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        SCHEME_REGISTRY,
        "fake",
        lambda address: _ServingAdapter(),  # type: ignore[arg-type,return-value]
    )
    monkeypatch.setenv(BINDING_ENV_VAR, "fake:./from-the-environment")

    client = ProductClient.for_product(_PRODUCT)

    assert client.ask(parameters=_PARAMETERS).refused is False


def test_for_product_refuses_when_nothing_names_a_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(BINDING_ENV_VAR, raising=False)

    with pytest.raises(BindingError, match="CCF_BINDING"):
        ProductClient.for_product(_PRODUCT)
