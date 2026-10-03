"""``ApprovalGate`` + ``ApprovalSinkAdapter`` — the dual face (07-07).

Written before the implementation per the TDD discipline. The claims:

**The gate face** (async workflow face): a decision submitted without a
:class:`~ccf.hitl.principal.HumanPrincipalBinding` is unrepresentable
through the typed transport contract; approval and rejection both produce
audited outcomes; rejection is a *returned* typed value with a
``resolved=False`` audit record, never an exception; a TOCTOU hash
mismatch (the approver's binding names a product hash other than the one
bound at suspend time) is a returned typed refusal, audited
``resolved=False``.

**The sync grant face** (:class:`ApprovalSinkAdapter`): ``decide`` with no
completed decision bound raises a typed error — it never blocks on a
pending human and never fabricates a verdict. The adapter's conformance to
the ``ApprovalSink`` Protocol is asserted by the shared conformance suite
(``tests/conformance/test_approval_sink.py``), which this file does not
duplicate.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.authz.capability import Authorized, HitlSubmit
from ccf.contracts.canonical import content_hash
from ccf.controlplane.audit import AuditLog
from ccf.hitl.approval_gate import (
    ApprovalGate,
    ApprovalSinkAdapter,
    GateResolution,
    GateResolutionRefused,
    UnboundDecisionError,
    UnknownGateEventError,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (
    HitlActionSubmission,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from ccf.skills.grants import ApprovalOutcome
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


def _gate() -> tuple[ApprovalGate, InMemoryHitlTransport, AuditLog]:
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    gate = ApprovalGate(transport=transport, audit=audit, clock=_clock())
    return gate, transport, audit


def _event(fixture: dict[str, Any]) -> PendingHitlEvent:
    document = dict(fixture["event"])
    return PendingHitlEvent(
        **document, product_content_hash=content_hash(document)
    )


# --- the gate face ------------------------------------------------------------


def test_a_submission_without_a_binding_is_unrepresentable() -> None:
    """The typed transport contract requires the principal by type (07-04)."""
    fixture = _hitl()
    event = _event(fixture)
    with pytest.raises(ValidationError):
        HitlActionSubmission(  # type: ignore[call-arg]
            event_key=event.event_key,
            action="approve",
        )


def test_an_approval_is_an_audited_typed_resolution() -> None:
    fixture = _hitl()
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        _authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    assert isinstance(resolution.outcome, ApprovalOutcome)
    assert resolution.outcome.approved is True
    # The action is on the authority path and the event is consumed.
    assert len(transport.submissions(tenant=event.tenant)) == 1
    assert transport.pending(tenant=event.tenant) == ()
    events = [e for e in audit.events() if e.action == "hitl_action"]
    assert len(events) == 1 and events[0].resolved is True


def test_a_rejection_is_a_returned_value_with_a_resolved_false_audit() -> None:
    """Rejection is a governance verdict, never control flow."""
    fixture = _hitl()
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        _authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="reject",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    assert resolution.outcome.approved is False
    events = [e for e in audit.events() if e.action == "hitl_action"]
    assert len(events) == 1 and events[0].resolved is False


def test_a_toctou_hash_mismatch_is_a_returned_audited_refusal() -> None:
    """The binding's hash must equal the hash bound at suspend time."""
    fixture = _hitl()
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    mutated_hash = content_hash({"mutated": "product"})
    assert mutated_hash != event.product_content_hash
    refusal = gate.resolve(
        _authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=_principal(fixture, product_content_hash=mutated_hash),
    )
    assert isinstance(refusal, GateResolutionRefused)
    # The refused event is NOT consumed and no action reached the authority
    # path: the human must re-review the current product version.
    assert transport.pending(tenant=event.tenant) == (event,)
    assert transport.submissions(tenant=event.tenant) == ()
    events = [e for e in audit.events() if e.action == "hitl_action"]
    assert len(events) == 1 and events[0].resolved is False


def test_resolving_an_unknown_event_raises() -> None:
    """Broken wiring raises; it is never a returned refusal (I.1 line)."""
    fixture = _hitl()
    gate, _, _ = _gate()
    event = _event(fixture)
    with pytest.raises(UnknownGateEventError):
        gate.resolve(
            _authorized(event.tenant, "no-such-event"),
            event_key="no-such-event",
            action="approve",
            principal=_principal(
                fixture, product_content_hash=event.product_content_hash
            ),
        )


def test_the_resolution_carries_the_preserialized_dim_2_block() -> None:
    """The gate serializes the HITL-action block once; replay records it
    verbatim (07-05 keyword discipline)."""
    fixture = _hitl()
    gate, transport, _ = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        _authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    block = resolution.hitl_actions_block
    assert (
        fixture["approvers"]["credit_officer"]["identity"]["subject_id"]
        in block
    )
    assert event.product_content_hash in block


# --- 10-02 Task 2: resolve-surface signed-binding verification (D-IMPL-69) ---


def _signing_env(tmp_path: Path) -> tuple[Any, Any, dict[str, Any]]:
    """A provider, its key id, and the trusted-keys mapping."""
    import json as _json

    from joserfc.jwk import ECKey

    from ccf.peering.identity import (
        DetachedJwsIdentityProvider,
        FileBackedKeySource,
    )

    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    kid = "gate-approver-key"
    key = ECKey.generate_key("P-256", parameters={"kid": kid})
    (key_dir / f"{kid}.jwk").write_text(
        _json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    return provider, kid, {kid: key.as_dict(private=False)}


def _required_policy_plane() -> tuple[Any, str]:
    from ccf.controlplane.artifacts import parse_artifact
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.hitl.transport import HITL_POLICY

    plane = ControlPlaneRegistry()
    policy_key = "acme-bank/hitl/policy"
    compose_register_typed(plane,
        policy_key,
        parse_artifact(
            {"semver": "1.0.0", "signed_binding_required": True},
            HITL_POLICY,
        ),
        HITL_POLICY,
    )
    return plane, policy_key


def _bound_gate(
    tmp_path: Path,
) -> tuple[ApprovalGate, InMemoryHitlTransport, Any, str]:
    provider, kid, trusted = _signing_env(tmp_path)
    plane, policy_key = _required_policy_plane()
    transport = InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
        trusted_keys=trusted,
    )
    gate = ApprovalGate(
        transport=transport,
        audit=AuditLog(),
        clock=_clock(),
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
        trusted_keys=trusted,
    )
    return gate, transport, provider, kid


def test_gate_required_and_unsigned_resolve_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    """Refusal at the primitive layer; the event survives (Pitfall 4)."""
    from ccf.hitl.identity_binding import sign_principal_binding
    from ccf.hitl.transport import SignedBindingRequiredRefused

    fixture = _hitl()
    gate, transport, provider, kid = _bound_gate(tmp_path)
    event = _event(fixture)
    transport.enqueue(event=event)
    principal = _principal(
        fixture, product_content_hash=event.product_content_hash
    )
    with pytest.raises(SignedBindingRequiredRefused):
        gate.resolve(
            _authorized(event.tenant, event.event_key),
            event_key=event.event_key,
            action="approve",
            principal=principal,
        )
    # The pending event survives the refusal.
    assert transport.pending(tenant=event.tenant) == (event,)
    assert transport.submissions(tenant=event.tenant) == ()
    # A subsequent valid resolve of the SAME event succeeds.
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    resolution = gate.resolve(
        _authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=principal,
        signed_binding=signed,
    )
    assert isinstance(resolution, GateResolution)


def test_gate_required_and_tampered_binding_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.identity_binding import sign_principal_binding
    from ccf.hitl.transport import SignedBindingInvalidRefused

    fixture = _hitl()
    gate, transport, provider, kid = _bound_gate(tmp_path)
    event = _event(fixture)
    transport.enqueue(event=event)
    principal = _principal(
        fixture, product_content_hash=event.product_content_hash
    )
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    tampered = signed.model_copy(
        update={"signature": signed.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        gate.resolve(
            _authorized(event.tenant, event.event_key),
            event_key=event.event_key,
            action="approve",
            principal=principal,
            signed_binding=tampered,
        )
    assert transport.pending(tenant=event.tenant) == (event,)
    assert transport.submissions(tenant=event.tenant) == ()


def test_gate_required_and_valid_binding_passes_both_layers(
    tmp_path: Path,
) -> None:
    """The transport's own second verification also passes (D-13)."""
    from ccf.hitl.identity_binding import sign_principal_binding

    fixture = _hitl()
    gate, transport, provider, kid = _bound_gate(tmp_path)
    event = _event(fixture)
    transport.enqueue(event=event)
    principal = _principal(
        fixture, product_content_hash=event.product_content_hash
    )
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    resolution = gate.resolve(
        _authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=principal,
        signed_binding=signed,
    )
    assert isinstance(resolution, GateResolution)
    recorded = transport.submissions(tenant=event.tenant)
    assert len(recorded) == 1
    assert recorded[0].signed_binding == signed


def test_gate_unbound_kwargs_behave_as_before() -> None:
    """No Control Plane bound: byte-identical pre-Phase-10 behavior."""
    fixture = _hitl()
    gate, transport, _ = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        _authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)


# --- the sync grant face ------------------------------------------------------


def test_decide_with_no_bound_decision_raises_a_typed_error() -> None:
    """The sync face is honest: it never blocks, never fabricates."""
    adapter = ApprovalSinkAdapter()
    with pytest.raises(UnboundDecisionError):
        adapter.decide(object())  # type: ignore[arg-type]


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
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=event.event_key + "-decoy",
            event_class="approval-gate",
            tenant=event.tenant,
            workflow_state_ref="decoy/exec",
            product_content_hash="e" * 64,
        )
    )
    # Two events, so a claim taken BEFORE the capability died (and given back
    # at the tail on rollback) shows up as a reorder rather than as nothing.
    pending_before = transport.pending(tenant=event.tenant)
    assert len(pending_before) == 2
    audit_before = audit.events()
    principal = _principal(fixture, product_content_hash=event.product_content_hash)
    read = queue_read_capability(
        tenant=event.tenant, principal="credit-officer-11", resource=event.event_key
    )
    with pytest.raises(CapabilityBypassError, match="kind"):
        gate.resolve(
            read,  # type: ignore[arg-type]
            event_key=event.event_key,
            action="approve",
            principal=principal,
        )
    assert transport.pending(tenant=event.tenant) == pending_before
    assert transport.submissions(tenant=event.tenant) == ()
    assert audit.events() == audit_before


def test_a_capability_for_another_event_dies_at_the_primitive() -> None:
    from ccf.authz.capability import CapabilityBypassError

    fixture = _hitl()
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=event.event_key + "-decoy",
            event_class="approval-gate",
            tenant=event.tenant,
            workflow_state_ref="decoy/exec",
            product_content_hash="e" * 64,
        )
    )
    # Two events, so a claim taken BEFORE the capability died (and given back
    # at the tail on rollback) shows up as a reorder rather than as nothing.
    pending_before = transport.pending(tenant=event.tenant)
    assert len(pending_before) == 2
    audit_before = audit.events()
    principal = _principal(fixture, product_content_hash=event.product_content_hash)
    with pytest.raises(CapabilityBypassError, match="resource"):
        gate.resolve(
            _authorized(event.tenant, "some-other-event"),
            event_key=event.event_key,
            action="approve",
            principal=principal,
        )
    assert transport.pending(tenant=event.tenant) == pending_before
    assert transport.submissions(tenant=event.tenant) == ()
    assert audit.events() == audit_before


def test_the_record_carries_the_authorizing_decision_id() -> None:
    """The recorded submission is the transport's stamped copy: the replay
    block names the authorization that produced the action (D-IMPL-353 §9),
    never the primitive's pre-stamp input."""
    fixture = _hitl()
    gate, transport, _ = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    authorized = _authorized(event.tenant, event.event_key)
    resolution = gate.resolve(
        authorized,
        event_key=event.event_key,
        action="approve",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    assert (
        resolution.record.submission.authorizing_decision_id
        == authorized.decision_id
    )
    assert authorized.decision_id in resolution.hitl_actions_block
