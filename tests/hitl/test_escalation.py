"""``ExceptionEscalation`` — the routing HITL primitive (07-08).

Written before the implementation per the TDD discipline. The claims:

An escalation condition — an explicit agent escalation, or a D_c-shaped
condition assessed against a Control-Plane :class:`DebtProfile` artifact,
never a code constant — hands the workflow state to a designated role via
the typed HITL transport; the escalated event carries what the human needs
(execution reference, suspended-state ref, trigger); a nominal (OK-signal)
debt assessment is a typed refusal, audited ``resolved=False``; resolution
requires a :class:`~ccf.hitl.principal.HumanPrincipalBinding` by type and
yields the pre-serialized dimension-2 block; a TOCTOU hash mismatch is a
returned typed refusal that leaves the event pending; resolving an event
the queue does not hold raises (broken wiring, I.1 line).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.authz.capability import Authorized, HitlSubmit
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import DEBT_PROFILE, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.halflife.debt import DebtFactors, DebtSignal, assess_debt
from ccf.hitl.escalation import (
    EscalationHandOff,
    EscalationRefused,
    EscalationResolution,
    EscalationResolutionRefused,
    ExceptionEscalation,
    ExplicitEscalation,
    UnknownEscalationEventError,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import PendingHitlEvent, HitlActionSubmission, InMemoryHitlTransport
from tests.controlplane.composition import compose_register_typed

from .capabilities import submit_capability

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _hitl() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "hitl.yaml").read_text()
    )
    return loaded


def _authorized(tenant: str, event_key: str) -> Authorized[HitlSubmit]:
    """The capability a resolver presents (D-IMPL-353 §1.2): minted for
    exactly this tenant and event, for the fixture's credit officer — the
    subject every binding below names, so the transport's actor check and
    the capability agree."""
    subject = _hitl()["approvers"]["credit_officer"]["identity"]["subject_id"]
    return submit_capability(
        tenant=tenant, principal=subject, event_key=event_key
    )


def _halflife() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "halflife.yaml").read_text()
    )
    return loaded


def _clock() -> Any:
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def _principal(
    fixture: dict[str, Any], *, product_content_hash: str
) -> HumanPrincipalBinding:
    approver = fixture["approvers"]["credit_officer"]
    return HumanPrincipalBinding(
        verdict="approve",
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _escalation() -> tuple[ExceptionEscalation, InMemoryHitlTransport, AuditLog]:
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    escalation = ExceptionEscalation(
        transport=transport, audit=audit, clock=_clock()
    )
    return escalation, transport, audit


def _event_document(fixture: dict[str, Any]) -> dict[str, Any]:
    return dict(fixture["escalation"]["event"])


def _assessment(fixture: dict[str, Any], key: str) -> Any:
    profile = parse_artifact(_halflife()["debt_profile"], DEBT_PROFILE)
    factors = DebtFactors(**fixture["escalation"][key])
    return assess_debt(factors, profile=profile)  # type: ignore[arg-type]


def _hand_off(
    escalation: ExceptionEscalation,
    fixture: dict[str, Any],
    trigger: Any,
) -> EscalationHandOff | EscalationRefused:
    document = _event_document(fixture)
    return escalation.escalate(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        product_content_hash=content_hash(document),
        policy_ref=document["policy_ref"],
        trigger=trigger,
    )


# --- the hand-off face --------------------------------------------------------


def test_an_explicit_escalation_hands_the_state_to_the_designated_role() -> None:
    """An explicit agent escalation surfaces on the typed transport, carrying
    the workflow-state ref and the pinned routing artifact (CINV-01)."""
    fixture = _hitl()
    escalation, transport, audit = _escalation()
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    hand_off = _hand_off(escalation, fixture, trigger)
    assert isinstance(hand_off, EscalationHandOff)
    document = _event_document(fixture)
    (pending,) = transport.pending(tenant=document["tenant"])
    assert pending.event_class == "exception-escalation"
    assert pending.event_key == document["event_key"]
    assert pending.workflow_state_ref == document["workflow_state_ref"]
    assert pending.policy_ref == document["policy_ref"]
    assert pending.product_content_hash == content_hash(document)
    assert hand_off.event == pending
    assert hand_off.trigger == trigger
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved


def test_a_breaching_debt_assessment_escalates() -> None:
    """A D_c condition sourced from the DebtProfile artifact — never a code
    constant — is an accepted escalation trigger when its signal breaches."""
    fixture = _hitl()
    escalation, transport, _ = _escalation()
    assessment = _assessment(fixture, "breaching_factors")
    assert assessment.signal is not DebtSignal.OK
    hand_off = _hand_off(escalation, fixture, assessment)
    assert isinstance(hand_off, EscalationHandOff)
    assert hand_off.trigger == assessment
    assert len(transport.pending(tenant=_event_document(fixture)["tenant"])) == 1


def test_a_nominal_debt_assessment_is_a_typed_refusal() -> None:
    """An OK-signal assessment escalates nothing: typed refusal, audited
    ``resolved=False``, nothing enqueued."""
    fixture = _hitl()
    escalation, transport, audit = _escalation()
    assessment = _assessment(fixture, "nominal_factors")
    assert assessment.signal is DebtSignal.OK
    refused = _hand_off(escalation, fixture, assessment)
    assert isinstance(refused, EscalationRefused)
    assert transport.pending(tenant=_event_document(fixture)["tenant"]) == ()
    events = audit.events()
    assert events[-1].action == "hitl_action" and not events[-1].resolved


# --- the resolution face ------------------------------------------------------


def test_a_resolution_without_a_binding_is_unrepresentable() -> None:
    """The typed transport contract requires the principal by type (D-22
    type-unrepresentable leg)."""
    fixture = _hitl()
    document = _event_document(fixture)
    with pytest.raises(ValidationError):
        HitlActionSubmission(  # type: ignore[call-arg]
            event_key=document["event_key"],
            action="approve",
        )


def test_a_resolution_lands_on_dimension_two() -> None:
    """An approved resolution consumes the event and yields the
    pre-serialized dimension-2 block — byte-equal to the canonical record."""
    fixture = _hitl()
    escalation, transport, audit = _escalation()
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    hand_off = _hand_off(escalation, fixture, trigger)
    assert isinstance(hand_off, EscalationHandOff)
    document = _event_document(fixture)
    resolution = escalation.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        action="approve",
        principal=_principal(
            fixture, product_content_hash=content_hash(document)
        ),
    )
    assert isinstance(resolution, EscalationResolution)
    assert resolution.record.trigger == trigger
    assert resolution.hitl_actions_block == canonical_bytes(
        resolution.record
    ).decode("utf-8")
    assert transport.pending(tenant=document["tenant"]) == ()
    (submission,) = transport.submissions(tenant=document["tenant"])
    assert submission.action == "approve"
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved
    assert (
        events[-1].actor
        == fixture["approvers"]["credit_officer"]["identity"]["subject_id"]
    )


def test_a_declined_resolution_is_audited_resolved_false() -> None:
    fixture = _hitl()
    escalation, transport, audit = _escalation()
    hand_off = _hand_off(
        escalation,
        fixture,
        ExplicitEscalation(reason=fixture["escalation"]["explicit_reason"]),
    )
    assert isinstance(hand_off, EscalationHandOff)
    document = _event_document(fixture)
    resolution = escalation.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        action="reject",
        principal=_principal(
            fixture, product_content_hash=content_hash(document)
        ),
    )
    assert isinstance(resolution, EscalationResolution)
    assert not resolution.record.accepted
    events = audit.events()
    assert events[-1].action == "hitl_action" and not events[-1].resolved


def test_a_toctou_mismatch_is_refused_and_the_event_stays_pending() -> None:
    fixture = _hitl()
    escalation, transport, _ = _escalation()
    hand_off = _hand_off(
        escalation,
        fixture,
        ExplicitEscalation(reason=fixture["escalation"]["explicit_reason"]),
    )
    assert isinstance(hand_off, EscalationHandOff)
    document = _event_document(fixture)
    stale = content_hash({"stale": "state"})
    refused = escalation.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        action="approve",
        principal=_principal(fixture, product_content_hash=stale),
    )
    assert isinstance(refused, EscalationResolutionRefused)
    assert len(transport.pending(tenant=document["tenant"])) == 1


def test_resolving_on_a_second_instance_is_typed_and_mutates_nothing() -> None:
    """WR-01: the transport may be shared across primitive instances, but
    the hand-off trigger is per-instance side-band state. Resolving on an
    instance that did not escalate raises the typed broken-wiring error
    *before* any transport mutation — never a bare ``KeyError`` after the
    authority path already recorded the action."""
    fixture = _hitl()
    escalation, transport, audit = _escalation()
    hand_off = _hand_off(
        escalation,
        fixture,
        ExplicitEscalation(reason=fixture["escalation"]["explicit_reason"]),
    )
    assert isinstance(hand_off, EscalationHandOff)
    document = _event_document(fixture)

    other = ExceptionEscalation(
        transport=transport, audit=audit, clock=_clock()
    )
    with pytest.raises(UnknownEscalationEventError):
        other.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            action="approve",
            principal=_principal(
                fixture, product_content_hash=content_hash(document)
            ),
        )

    # Nothing landed on the authority path and the event survives.
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_resolving_an_unknown_event_raises() -> None:
    fixture = _hitl()
    escalation, _, _ = _escalation()
    document = _event_document(fixture)
    with pytest.raises(UnknownEscalationEventError):
        escalation.resolve(
            _authorized(document["tenant"], "acme-bank/exec-esc/no-such-event"),
            event_key="acme-bank/exec-esc/no-such-event",
            action="approve",
            principal=_principal(
                fixture, product_content_hash=content_hash(document)
            ),
        )


# --- 10-02 Task 3 / `D-IMPL-363`: resolve-surface attestation verification ---
#
# SEC-005's remaining leg (`D-IMPL-363`) replaced the signed door-minted
# binding with signer-stated `HitlActionClaims` carried as an `attestation`,
# and moved BOTH the trust map and the freshness window INSIDE the pinned
# `HitlPolicy` (E3/E5) — there is no `trusted_keys` constructor argument on the
# transport or on a primitive any more. These tests sign `issued_at` equal to
# the binding's FIXED `action_time`: that is the recorded instant the
# directional window is judged against (E2), so no participant reads a clock.

#: Deployment vocabulary for this suite (CINV-01): the window the pinned policy
#: declares. Both are REQUIRED whenever `signed_binding_required` is true.
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60


def _signing_env(tmp_path: Path) -> tuple[Any, str, dict[str, Any]]:
    """A provider, its key id, and the public-JWK map for ONE approver subject."""
    import json as _json

    from joserfc.jwk import ECKey

    from ccf.peering.identity import (
        DetachedJwsIdentityProvider,
        FileBackedKeySource,
    )

    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    kid = "escalation-approver-key"
    key = ECKey.generate_key("P-256", parameters={"kid": kid})
    (key_dir / f"{kid}.jwk").write_text(
        _json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    return provider, kid, {kid: key.as_dict(private=False)}


def _subject(fixture: dict[str, Any]) -> str:
    """The approver every binding and every capability in this suite names."""
    subject: str = fixture["approvers"]["credit_officer"]["identity"][
        "subject_id"
    ]
    return subject


def _ruled_policy_document(
    *, subject_id: str, keys: dict[str, Any]
) -> dict[str, Any]:
    """The HITL policy `D-IMPL-363` E3/E5 rules: requiredness, the directional
    freshness window, and the per-subject trusted keys — the ONE trust source."""
    return {
        "semver": "1.0.0",
        "signed_binding_required": True,
        "signature_max_age_seconds": MAX_AGE_SECONDS,
        "permitted_clock_skew_seconds": SKEW_SECONDS,
        "trusted_keys": {subject_id: keys},
    }


def _bound_escalation(
    tmp_path: Path, fixture: dict[str, Any]
) -> tuple[ExceptionEscalation, InMemoryHitlTransport, Any, str, str]:
    """The primitive, its transport, the signer's provider and key id, and the
    ``key@version`` the transport stamps on an admitted submission — derived
    from the registry's own resolution (`D-IMPL-363` E3), never a literal."""
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.hitl.transport import HITL_POLICY, resolve_hitl_policy

    provider, kid, keys = _signing_env(tmp_path)
    plane = ControlPlaneRegistry()
    policy_key = "acme-bank/hitl/policy"
    compose_register_typed(
        plane,
        policy_key,
        parse_artifact(
            _ruled_policy_document(subject_id=_subject(fixture), keys=keys),
            HITL_POLICY,
        ),
        HITL_POLICY,
    )
    resolved = resolve_hitl_policy(
        control_plane=plane, hitl_policy_key=policy_key
    )
    assert resolved is not None
    version, policy = resolved
    transport = InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
    )
    escalation = ExceptionEscalation(
        transport=transport,
        audit=AuditLog(),
        clock=_clock(),
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
    )
    return (
        escalation,
        transport,
        provider,
        kid,
        policy.pinned_ref(key=policy_key, version=version),
    )


def _attestation(
    provider: Any,
    kid: str,
    *,
    tenant: str,
    event_key: str,
    action: str,
    principal: HumanPrincipalBinding,
    subject_id: str,
    nonce: str,
) -> Any:
    """A signed attestation over exactly what a signer can state (E1).

    ``issued_at`` is the binding's own ``action_time`` — the fixed instant the
    door recorded — so the directional window is satisfied exactly, without any
    participant reading a clock (E2/E3).
    """
    from ccf.hitl.identity_binding import HitlActionClaims, sign_hitl_action

    return sign_hitl_action(
        HitlActionClaims(
            tenant=tenant,
            event_key=event_key,
            action=action,
            product_content_hash=principal.product_content_hash,
            subject_id=subject_id,
            issued_at=principal.action_time,
            nonce=nonce,
        ),
        provider=provider,
        key_id=kid,
    )


def test_escalation_required_and_unsigned_resolve_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.transport import SignedBindingRequiredRefused

    fixture = _hitl()
    escalation, transport, provider, kid, _ = _bound_escalation(
        tmp_path, fixture
    )
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    _hand_off(escalation, fixture, trigger)
    document = _event_document(fixture)
    principal = _principal(
        fixture, product_content_hash=content_hash(document)
    )
    with pytest.raises(SignedBindingRequiredRefused):
        escalation.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            action="approve",
            principal=principal,
        )
    # The pending event survives the refusal.
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()
    # A subsequent valid resolve of the SAME event succeeds.
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture),
        nonce="escalation-nonce-after-unsigned",
    )
    resolution = escalation.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, EscalationResolution)


def test_escalation_required_and_tampered_attestation_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    """A tampered SIGNATURE refuses invalid and the event stays pending.

    Successor to
    ``test_escalation_required_and_tampered_binding_is_refused_event_pending``:
    the same property over the `D-IMPL-363` attestation rather than the removed
    signed binding.
    """
    from ccf.hitl.transport import SignedBindingInvalidRefused

    fixture = _hitl()
    escalation, transport, provider, kid, _ = _bound_escalation(
        tmp_path, fixture
    )
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    _hand_off(escalation, fixture, trigger)
    document = _event_document(fixture)
    principal = _principal(
        fixture, product_content_hash=content_hash(document)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture),
        nonce="escalation-nonce-tampered",
    )
    tampered = attestation.model_copy(
        update={"signature": attestation.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        escalation.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            action="approve",
            principal=principal,
            attestation=tampered,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_escalation_required_and_an_attestation_for_the_other_verdict_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    """`D-IMPL-363` C1(a): a verifying signature over ``reject`` does not
    authorize an ``approve``.

    The sibling a tampered signature cannot reach: the envelope is genuine and
    the key is declared for this subject, so the signature verifies — and the
    resolution is still refused, as a MISMATCH, because the signed verdict is
    not the verdict this escalation submits. The event stays pending.
    """
    from ccf.hitl.transport import SignedBindingMismatchRefused

    fixture = _hitl()
    escalation, transport, provider, kid, _ = _bound_escalation(
        tmp_path, fixture
    )
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    _hand_off(escalation, fixture, trigger)
    document = _event_document(fixture)
    principal = _principal(
        fixture, product_content_hash=content_hash(document)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="reject",  # signed for the opposite verdict
        principal=principal,
        subject_id=_subject(fixture),
        nonce="escalation-nonce-other-verdict",
    )
    with pytest.raises(SignedBindingMismatchRefused, match=r"\['action'\]"):
        escalation.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            action="approve",
            principal=principal,
            attestation=attestation,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_escalation_required_and_valid_attestation_passes_both_layers(
    tmp_path: Path,
) -> None:
    """The transport's own second verification also passes (D-13).

    Successor to
    ``test_escalation_required_and_valid_binding_passes_both_layers``: one
    attestation satisfies the primitive's verification AND the transport's
    independent re-verification, the recorded submission carries it, and the
    record names the pinned policy that admitted it (`D-IMPL-363` E3).
    """
    fixture = _hitl()
    escalation, transport, provider, kid, pinned_ref = _bound_escalation(
        tmp_path, fixture
    )
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    _hand_off(escalation, fixture, trigger)
    document = _event_document(fixture)
    principal = _principal(
        fixture, product_content_hash=content_hash(document)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture),
        nonce="escalation-nonce-valid",
    )
    resolution = escalation.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, EscalationResolution)
    recorded = transport.submissions(tenant=document["tenant"])
    assert len(recorded) == 1
    assert recorded[0].attestation == attestation
    assert recorded[0].hitl_policy_ref == pinned_ref


def test_escalation_unbound_kwargs_behave_as_before() -> None:
    """No Control Plane bound: byte-identical pre-Phase-10 behavior."""
    fixture = _hitl()
    escalation, transport, _ = _escalation()
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    _hand_off(escalation, fixture, trigger)
    document = _event_document(fixture)
    resolution = escalation.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        action="approve",
        principal=_principal(
            fixture, product_content_hash=content_hash(document)
        ),
    )
    assert isinstance(resolution, EscalationResolution)


# --- D-IMPL-353 §1.2: the primitive requires the capability for ITS action ----
#
# The resolver mutates (``remove`` claims the event) and audits (a hash
# mismatch writes ``resolved=False``) BEFORE it submits, so the capability
# is verified at entry — a wrong kind or a capability minted for another
# event dies before the queue is read, before anything is audited, and
# before any claim is taken. Without these controls, severing ``verify`` at
# the primitive would redden nothing.


def test_a_queue_read_capability_dies_at_the_primitive_before_anything_is_touched() -> None:
    from ccf.authz.capability import CapabilityBypassError

    from .capabilities import queue_read_capability

    fixture = _hitl()
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    escalation = ExceptionEscalation(transport=transport, audit=audit, clock=_clock())
    document = fixture["escalation"]["event"]
    trigger = ExplicitEscalation(reason=fixture["escalation"]["explicit_reason"])
    hand_off = escalation.escalate(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        product_content_hash=content_hash(trigger),
        policy_ref=document["policy_ref"],
        trigger=trigger,
    )
    assert isinstance(hand_off, EscalationHandOff)
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=document["event_key"] + "-decoy",
            event_class="exception-escalation",
            tenant=document["tenant"],
            workflow_state_ref="decoy/exec",
            product_content_hash="e" * 64,
        )
    )
    # Two events, so a claim taken BEFORE the capability died (and given back
    # at the tail on rollback) shows up as a reorder rather than as nothing.
    pending_before = transport.pending(tenant=document["tenant"])
    assert len(pending_before) == 2
    audit_before = audit.events()
    principal = _principal(
        fixture, product_content_hash=hand_off.event.product_content_hash
    )
    read = queue_read_capability(
        tenant=document["tenant"], principal="credit-officer-11", resource=document["event_key"]
    )
    with pytest.raises(CapabilityBypassError, match="kind"):
        escalation.resolve(
            read,  # type: ignore[arg-type]
            event_key=document["event_key"],
            action="approve",
            principal=principal,
        )
    assert transport.pending(tenant=document["tenant"]) == pending_before
    assert transport.submissions(tenant=document["tenant"]) == ()
    assert audit.events() == audit_before


def test_a_capability_for_another_event_dies_at_the_primitive() -> None:
    from ccf.authz.capability import CapabilityBypassError

    fixture = _hitl()
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    escalation = ExceptionEscalation(transport=transport, audit=audit, clock=_clock())
    document = fixture["escalation"]["event"]
    trigger = ExplicitEscalation(reason=fixture["escalation"]["explicit_reason"])
    hand_off = escalation.escalate(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        product_content_hash=content_hash(trigger),
        policy_ref=document["policy_ref"],
        trigger=trigger,
    )
    assert isinstance(hand_off, EscalationHandOff)
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=document["event_key"] + "-decoy",
            event_class="exception-escalation",
            tenant=document["tenant"],
            workflow_state_ref="decoy/exec",
            product_content_hash="e" * 64,
        )
    )
    # Two events, so a claim taken BEFORE the capability died (and given back
    # at the tail on rollback) shows up as a reorder rather than as nothing.
    pending_before = transport.pending(tenant=document["tenant"])
    assert len(pending_before) == 2
    audit_before = audit.events()
    principal = _principal(
        fixture, product_content_hash=hand_off.event.product_content_hash
    )
    with pytest.raises(CapabilityBypassError, match="resource"):
        escalation.resolve(
            _authorized(document["tenant"], "some-other-event"),
            event_key=document["event_key"],
            action="approve",
            principal=principal,
        )
    assert transport.pending(tenant=document["tenant"]) == pending_before
    assert transport.submissions(tenant=document["tenant"]) == ()
    assert audit.events() == audit_before


def test_the_record_carries_the_authorizing_decision_id() -> None:
    """The recorded submission is the transport's stamped copy: the replay
    block names the authorization that produced the action (D-IMPL-353 §9),
    never the primitive's pre-stamp input."""
    fixture = _hitl()
    escalation, transport, _ = _escalation()
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    _hand_off(escalation, fixture, trigger)
    document = _event_document(fixture)
    authorized = _authorized(document["tenant"], document["event_key"])
    resolution = escalation.resolve(
        authorized,
        event_key=document["event_key"],
        action="approve",
        principal=_principal(
            fixture, product_content_hash=content_hash(document)
        ),
    )
    assert isinstance(resolution, EscalationResolution)
    assert (
        resolution.record.submission.authorizing_decision_id
        == authorized.decision_id
    )
    assert authorized.decision_id in resolution.hitl_actions_block
