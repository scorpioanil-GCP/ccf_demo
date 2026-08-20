"""``ProductClient`` — the question that goes out and the one shape that comes back.

``D-04``, ``D-07``, ``D-12``. ``tests/client/test_surface.py`` proves the
decoder is the *only* place a :class:`~ccf.client.result.Result` is built; this
module proves the decoder is *right*, which is the half that would otherwise be
left to the adapter plans that come after.

The tests that matter most are the two at the bottom
-----------------------------------------------------
The seam returns **bytes** (``C-05``, ``C-08``, Phase 19): an adapter hands
over the producer's canonical rendering and never an outcome object, so
:func:`~ccf.client.codec.decode_outcome` parses every field out of what the
sender produced. A transport can still *lie* — it can put a well-formed
outcome on that wire which answers a different question, or which carries a
content address that disagrees with the bytes it describes — and the two
adapters at the bottom of this module are exactly those two lies, each a
*conforming* transport in the type-checker's eyes and a lying one in fact.

What changed with ``C-05`` is where the lie is caught and what it costs a
transport to tell. It used to be caught by the client re-running
:func:`~ccf.client.codec.check_outcome` on an object an adapter had built —
necessary because ``D-11`` typed the seam as returning that object, which is
also what let both shipped adapters fill the echo from the request they were
handed and made the check inert on every real transport (``D-IMPL-151``
``B0``). It is now caught on the one decode path, against bytes; the stubs
below reach that path by encoding through the shipped
:func:`~ccf.client.codec.encode_outcome`, never by hand-rolling a rendering,
because a test that copies the encoder proves the copy.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final

import pytest

from ccf.client.binding import BINDING_ENV_VAR, SCHEME_REGISTRY
from ccf.client.client import ProductClient
from ccf.client.codec import encode_outcome
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


# The seam carries bytes (`C-08`), so every stub below puts its outcome on the
# wire through the SHIPPED encoder. The object-returning helpers above are kept
# beside these because several tests still want the outcome itself; what no
# test does is render one by hand — `encode_outcome` is the one encoder, and a
# test that copied it would prove only that the copy fires.


def served_bytes_for(request: WireRequest) -> bytes:
    return encode_outcome(served_outcome_for(request))


def refused_bytes_for(request: WireRequest) -> bytes:
    return encode_outcome(refused_outcome_for(request))


class _ServingAdapter:
    """A transport that answers, and records the question it was asked."""

    def __init__(self) -> None:
        self.asked: list[WireRequest] = []

    def ask(self, request: WireRequest) -> bytes:
        self.asked.append(request)
        return served_bytes_for(request)


class _RefusingAdapter:
    """A transport whose producer refused — the fabric working."""

    def ask(self, request: WireRequest) -> bytes:
        return refused_bytes_for(request)


class _DeadAdapter:
    """A transport that never spoke."""

    def ask(self, request: WireRequest) -> bytes:
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

    def ask(self, request: WireRequest) -> bytes:
        other = WireRequest(
            product_id=request.product_id,
            parameters={"revenue_threshold": 999},
            temporal_boundary=request.temporal_boundary,
        )
        return served_bytes_for(other)


def test_an_outcome_answering_a_different_question_is_a_transport_error() -> None:
    """The echo on the wire is compared against what was sent, and disagrees.

    Without this, a transport that put a well-formed answer to a *different*
    question on the wire would hand the caller that answer labelled with the
    question they meant to ask. The comparison is what makes the label
    trustworthy, and reading the identity off the echo in
    :meth:`~ccf.client.client.ProductClient._result_from` is what keeps the
    comparison load-bearing rather than advisory.
    """
    with pytest.raises(TransportError, match="different question"):
        a_client(_CrossedQuestionAdapter()).ask(parameters=_PARAMETERS)


class _AlteredVesselAdapter:
    """A conforming transport whose vessel does not hash to its own address."""

    def ask(self, request: WireRequest) -> bytes:
        honest = served_outcome_for(request)
        return encode_outcome(
            WireOutcome(
                request=request,
                product_json=honest.product_json,
                content_address="0" * 64,
                replay_ref=honest.replay_ref,
                refusal=None,
            )
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
