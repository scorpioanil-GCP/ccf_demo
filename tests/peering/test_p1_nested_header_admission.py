"""T4-P1 at A2A admission: a nested protected header is a signature refusal by name, never a crash (`D-IMPL-374`, final fix wave FW-1).

The whole-branch review found the defect in the shared parser
``ccf.peering.identity.SignedContextProduct.declared_header``: its ``except``
covered only ``ValueError``, so a deeply nested JSON header raised an uncaught
``RecursionError``. :meth:`~ccf.peering.admission.PeeringAdmissionGate.admit`
reads the declared key id under ``except IdentityError`` and verifies under the
same, so an inbound envelope carrying such a header crashed the admission gate
instead of being refused. A refusal is a returned value here
(``tests/peering/test_admission_attributability.py::test_the_refusal_is_a_returned_value_never_an_exception``);
this holds the nested-header case to that rule, refused at the signature gate
as ``SignatureMalformed``.
"""

from __future__ import annotations

import base64

from ccf.peering.admission import PeeringAdmissionGate, SignatureRefusal
from ccf.peering.identity import DetachedJwsIdentityProvider, SignedContextProduct
from tests.peering.test_admission_attributability import (  # noqa: F401 - pytest fixtures
    _inbound,
    _now,
    _sign,
    artifact_store,
    banking_product,
    consumer_lineage,
    gate,
    key_dir,
    product_class,
    provider,
    public_key,
    registry,
)

#: Nested past any recursion limit the JSON decoder honors (test data).
DEPTH = 100_000


def _nested_header() -> str:
    text = "[" * DEPTH + "]" * DEPTH
    return base64.urlsafe_b64encode(text.encode("ascii")).rstrip(b"=").decode("ascii")


def test_p1_an_inbound_envelope_with_a_nested_header_is_refused_by_name(
    provider: DetachedJwsIdentityProvider, gate: PeeringAdmissionGate
) -> None:
    genuine = _sign(provider, product=banking_product())
    nested = SignedContextProduct(
        payload=genuine.payload, protected=_nested_header(), signature=genuine.signature
    )
    outcome = gate.admit(inbound=_inbound(nested), consumer_lineage=consumer_lineage(), now=_now())
    assert isinstance(outcome, SignatureRefusal), outcome
    assert outcome.failure == "SignatureMalformed"
    assert outcome.declared_key_id is None


def test_p1_control_the_same_envelope_with_its_own_header_is_not_refused_at_the_signature(
    provider: DetachedJwsIdentityProvider, gate: PeeringAdmissionGate
) -> None:
    """Sensitivity: only the header differs from an envelope the gate admits."""
    genuine = _sign(provider, product=banking_product())
    outcome = gate.admit(inbound=_inbound(genuine), consumer_lineage=consumer_lineage(), now=_now())
    assert not isinstance(outcome, SignatureRefusal), outcome
