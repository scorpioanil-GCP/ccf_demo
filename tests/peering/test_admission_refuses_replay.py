"""`SEC-022`: an admitted A2A envelope cannot be replayed, and carries its question.

The row: ``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
``### SEC-022``, ruled at Q14 (a) on all four parts of
``docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md`` and widened
by ``D-IMPL-371`` to carry the signed question that completes SEC-025's peered
leg. Its final *MEASURED before execution* block governs.

**The defect, reproduced before the repair.**
``src/ccf/peering/admission.py::PeeringAdmissionGate.admit`` had no
``issued_at``, no nonce and no seen-set: the same bytes were admitted twice
(two ``peering_admitted`` events, zero refusals), a later presentation wrote a
SECOND ``AdmissionRecord`` at a different address, and a second gate instance
admitted a third time.

The cases (the row's letters):

* (a) the identical bytes presented twice → ``replayed``, and no second record;
* (b) ``issued_at`` outside the grant's declared window, on either side →
  ``stale-issuance``; the window's two edges are admitted;
* (c) an envelope **without** the claims → refused ``claims-missing``;
* (d) a deployment's shared seen-set, plugged through the Protocol, refuses the
  replay across two receiver instances;
* (e) the question binding lives with SEC-025's own cases:
  ``tests/products/test_composite_child_subject_binding.py::test_a_peered_child_answering_another_subject_is_refused_by_name``
  (un-xfailed) and its peered positive control
  ``tests/products/test_composite_child_subject_binding.py::test_a_peered_child_answering_the_asked_subject_serves``.

The window is judged against the ``now`` ``admit()`` already receives; nothing
here hands the gate a clock (``tests/peering/test_admission_clock.py``).
"""

from __future__ import annotations

import inspect
import threading
from datetime import datetime, timedelta

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.peering.admission import (
    ADMISSION_RECORD,
    AdmittedProduct,
    PeeringAdmissionGate,
)
from ccf.peering.identity import DetachedJwsIdentityProvider
from ccf.peering.protocol import InboundProduct, PeerRef
from ccf.products.gates import TTLRefusal

from tests.composition import composition_replay_mint
from tests.peering.issuance_fixture import (
    WINDOW_MAX_AGE_SECONDS,
    WINDOW_SKEW_SECONDS,
    issuance_member,
)
from tests.peering.test_admission import (  # noqa: F401  (pytest fixtures)
    BOUNDARY,
    PEER_A,
    PEER_A_KID,
    PEER_A_PRODUCER,
    PRODUCER_ASSERTION_HEADER,
    PRODUCT_CLASS,
    TENANT,
    _grant,
    _register_ceiling,
    _register_policy,
    artifact_store,
    banking_product,
    consumer_lineage,
    key_dir,
    keys,
    product_class,
    provider,
    registry,
    two_peer_gate,
)

#: The refusal the gate returns for every failure of this check.
GATE_ISSUANCE = "peering-issuance"


def _now() -> datetime:
    return BOUNDARY + timedelta(seconds=1)


def _signed(
    provider: DetachedJwsIdentityProvider,
    *,
    issued_at: datetime | None = None,
    claims: bool = True,
    product: object | None = None,
) -> InboundProduct:
    """One honest envelope from peer A, with (or without) the issuance claims."""
    body = product if product is not None else banking_product()
    assertions = {PRODUCER_ASSERTION_HEADER: PEER_A_PRODUCER}
    if claims:
        assertions.update(
            issuance_member(
                product=body, issued_at=issued_at if issued_at is not None else BOUNDARY
            )
        )
    signed = provider.sign(product=body, key_id=PEER_A_KID, assertions=assertions)
    return InboundProduct(
        observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER_A), signed=signed
    )


def _events(registry: ControlPlaneRegistry, action: str) -> list[object]:
    return [e for e in registry.audit_events() if e.action == action]


def _assert_issuance_refusal(outcome: object, failure: str) -> None:
    assert not isinstance(outcome, AdmittedProduct), (
        f"SEC-022: expected a {failure!r} refusal and the gate ADMITTED the envelope"
    )
    assert getattr(outcome, "gate", None) == GATE_ISSUANCE, outcome
    assert getattr(outcome, "failure", None) == failure, outcome
    assert getattr(outcome, "peer_id", None) == PEER_A, outcome


# --- (a) replay ---------------------------------------------------------------


def test_a_the_identical_bytes_presented_twice_are_refused_replayed(
    provider: DetachedJwsIdentityProvider,
    two_peer_gate: PeeringAdmissionGate,
    registry: ControlPlaneRegistry,
    artifact_store: object,
) -> None:
    """Admitted once; the same bytes again, later, refuse ``replayed`` and write nothing."""
    inbound = _signed(provider)
    first = two_peer_gate.admit(
        inbound=inbound, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(first, AdmittedProduct), first
    address = first.content_address

    # A LATER instant, inside every window: on the base tree this wrote a
    # second AdmissionRecord at a different address, so "no second record" is
    # only a claim if the second presentation would otherwise have been dated
    # differently.
    again = two_peer_gate.admit(
        inbound=inbound,
        consumer_lineage=consumer_lineage(),
        now=_now() + timedelta(seconds=30),
    )
    _assert_issuance_refusal(again, "replayed")

    admitted = _events(registry, "peering_admitted")
    refused = _events(registry, "peering_admission_refused")
    assert len(admitted) == 1, admitted
    assert len(refused) == 1, refused
    assert refused[0].resolved is False  # type: ignore[attr-defined]
    assert refused[0].version == address  # type: ignore[attr-defined]
    versions = artifact_store.versions(  # type: ignore[attr-defined]
        tenant_id=TENANT, artifact_class=ADMISSION_RECORD.class_id, name=address
    )
    assert len(versions) == 1, versions


# --- (b) the window -----------------------------------------------------------


def test_b_an_envelope_issued_beyond_the_skew_after_now_is_stale(
    provider: DetachedJwsIdentityProvider, two_peer_gate: PeeringAdmissionGate
) -> None:
    """Post-dated by more than the declared skew → ``stale-issuance``."""
    now = _now()
    outcome = two_peer_gate.admit(
        inbound=_signed(
            provider, issued_at=now + timedelta(seconds=WINDOW_SKEW_SECONDS + 1)
        ),
        consumer_lineage=consumer_lineage(),
        now=now,
    )
    _assert_issuance_refusal(outcome, "stale-issuance")


def test_b_an_envelope_issued_beyond_the_max_age_before_now_is_stale(
    provider: DetachedJwsIdentityProvider, two_peer_gate: PeeringAdmissionGate
) -> None:
    """Older than the declared max age → ``stale-issuance``.

    The product itself is still inside its TTL at ``now``, so the refusal is the
    window's and not the TTL gate's.
    """
    issued_at = BOUNDARY
    now = issued_at + timedelta(seconds=WINDOW_MAX_AGE_SECONDS + 1)
    product = banking_product(expires_at=now + timedelta(seconds=60))
    outcome = two_peer_gate.admit(
        inbound=_signed(provider, issued_at=issued_at, product=product),
        consumer_lineage=consumer_lineage(),
        now=now,
    )
    _assert_issuance_refusal(outcome, "stale-issuance")


def test_b_the_windows_two_edges_are_admitted(
    provider: DetachedJwsIdentityProvider, two_peer_gate: PeeringAdmissionGate
) -> None:
    """Exactly the skew ahead and exactly the max age behind both admit.

    The positive control for (b): a check that refused everything would pass
    both stale cases above.
    """
    now = BOUNDARY + timedelta(seconds=WINDOW_MAX_AGE_SECONDS)
    product = banking_product(expires_at=now + timedelta(seconds=60))
    for issued_at in (now + timedelta(seconds=WINDOW_SKEW_SECONDS), BOUNDARY):
        outcome = two_peer_gate.admit(
            inbound=_signed(provider, issued_at=issued_at, product=product),
            consumer_lineage=consumer_lineage(),
            now=now,
        )
        assert isinstance(outcome, AdmittedProduct), (issued_at, outcome)


def test_b_a_grant_cannot_be_declared_without_its_window() -> None:
    """No SDK default (Q14-3): both window fields are required on the grant."""
    import pytest
    from pydantic import ValidationError

    from ccf.peering.trust_policy import PeerTrustGrant

    with pytest.raises(ValidationError) as missing:
        PeerTrustGrant(
            signing_keys={},
            permitted_producer_hashes=frozenset(),
            permitted_schema_names=frozenset(),
            permitted_policy_regimes=frozenset(),
        )
    text = str(missing.value)
    assert "signature_max_age_seconds" in text, text
    assert "permitted_clock_skew_seconds" in text, text


# --- (c) absent claims --------------------------------------------------------


def test_c_an_envelope_without_the_claims_is_refused(
    provider: DetachedJwsIdentityProvider,
    two_peer_gate: PeeringAdmissionGate,
    registry: ControlPlaneRegistry,
) -> None:
    """Today's happy-path envelope, no claims → ``claims-missing``, audited unresolved."""
    outcome = two_peer_gate.admit(
        inbound=_signed(provider, claims=False),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    _assert_issuance_refusal(outcome, "claims-missing")
    assert not _events(registry, "peering_admitted")
    refused = _events(registry, "peering_admission_refused")
    assert len(refused) == 1 and refused[0].resolved is False  # type: ignore[attr-defined]


# --- (d) a shared seen-set across receivers ------------------------------------


class _DeploymentSharedSeenSet:
    """A deployment's own seen-set, shared by several receivers.

    Implements the Protocol's one method and nothing else; the gate is handed
    it through its constructor and never learns what is behind it.
    """

    def __init__(self) -> None:
        self._seen: set[tuple[str, str, str]] = set()
        self._lock = threading.Lock()
        self.calls = 0

    def admit_once(self, *, tenant_id: str, key_thumbprint: str, nonce: str) -> bool:
        # `SEC-022-C-01`: the Protocol scopes by the verified signing key's
        # thumbprint; it offers no peer id to key on.
        with self._lock:
            self.calls += 1
            key = (tenant_id, key_thumbprint, nonce)
            if key in self._seen:
                return False
            self._seen.add(key)
            return True


def _receiver(
    *,
    provider: DetachedJwsIdentityProvider,
    registry: ControlPlaneRegistry,
    product_class: object,
    policy_version: str,
    ceiling_version: str,
    artifact_store: object,
    seen: object,
) -> PeeringAdmissionGate:
    return PeeringAdmissionGate(
        identity=provider,
        control_plane=registry,
        audit_log=registry.audit_log,
        artifact_store=artifact_store,  # type: ignore[arg-type]
        authorized=composition_replay_mint(
            registry, tenant=TENANT, artifact_class=ADMISSION_RECORD.class_id
        ),
        trust_policy_version=policy_version,
        payload_ceiling_version=ceiling_version,
        product_classes={PRODUCT_CLASS["schema_name"]: product_class},  # type: ignore[dict-item]
        seen=seen,  # type: ignore[arg-type]
    )


def test_d_a_shared_seen_set_refuses_the_replay_across_two_receivers(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, object],
    registry: ControlPlaneRegistry,
    product_class: object,
    artifact_store: object,
) -> None:
    """Two gates over one shared seen-set: the second receiver refuses ``replayed``."""
    assert "seen" in inspect.signature(PeeringAdmissionGate).parameters, (
        "SEC-022: PeeringAdmissionGate takes no seen-set, so a deployment with"
        " several receivers has nothing to share and each admits the replay"
    )
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant(
                kid=PEER_A_KID, key=keys[PEER_A_KID], producer=PEER_A_PRODUCER  # type: ignore[arg-type]
            )
        },
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    shared = _DeploymentSharedSeenSet()
    gates = [
        _receiver(
            provider=provider,
            registry=registry,
            product_class=product_class,
            policy_version=policy_version,
            ceiling_version=ceiling_version,
            artifact_store=artifact_store,
            seen=shared,
        )
        for _ in range(2)
    ]
    inbound = _signed(provider)
    first = gates[0].admit(inbound=inbound, consumer_lineage=consumer_lineage(), now=_now())
    assert isinstance(first, AdmittedProduct), first
    second = gates[1].admit(inbound=inbound, consumer_lineage=consumer_lineage(), now=_now())
    _assert_issuance_refusal(second, "replayed")
    assert shared.calls == 2, shared.calls
    assert len(_events(registry, "peering_admitted")) == 1


def test_d_a_refused_presentation_does_not_spend_the_nonce(
    provider: DetachedJwsIdentityProvider, two_peer_gate: PeeringAdmissionGate
) -> None:
    """Only an ADMISSION consumes the nonce.

    Refused at an instant past the product's expiry (TTL), the same bytes are
    then admitted at an instant inside it — the measurement's ordering rule,
    which ``tests/products/test_d364_peered_child_served_at.py::test_the_peered_verdict_itself_moves_when_the_instant_moves``
    depends on.
    """
    product = banking_product(expires_at=BOUNDARY + timedelta(seconds=60))
    inbound = _signed(provider, product=product)
    late = two_peer_gate.admit(
        inbound=inbound,
        consumer_lineage=consumer_lineage(),
        now=BOUNDARY + timedelta(seconds=120),
    )
    assert isinstance(late, TTLRefusal), late
    early = two_peer_gate.admit(
        inbound=inbound, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(early, AdmittedProduct), early


# --- the claim set's question types mirror the door's --------------------------


def test_the_issued_question_types_mirror_the_door_types_member_for_member() -> None:
    """``IssuedAnswer``/``IssuedRequest`` exist only to break an import cycle.

    ``src/ccf/peering/issuance.py`` cannot use the door's types as field types
    (the door imports this package's gate). The shapes must not drift, or
    composition's conversion (``src/ccf/products/composite.py::signed_question``)
    would start failing closed on honest envelopes — or, worse, drop a member.
    """
    from ccf.peering.issuance import IssuedAnswer, IssuedRequest
    from ccf.products.door import AnsweredQuestion, WireRequest

    assert set(IssuedAnswer.model_fields) == set(AnsweredQuestion.model_fields)
    assert set(IssuedRequest.model_fields) == set(WireRequest.model_fields)
