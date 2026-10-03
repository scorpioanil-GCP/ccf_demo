"""``OverrideBoundary`` — the typed substitution HITL primitive (07-08).

Written before the implementation per the TDD discipline. The claims:

An override records the original agent output AND the substituted value,
both canonically serialized, in the dimension-2 block — byte-assertable
(T-07-16); an override without a
:class:`~ccf.hitl.principal.HumanPrincipalBinding` is unrepresentable
through the typed contract, and the binding's ``product_content_hash``
must match what the overrider saw (TOCTOU); a declined override — the
human confirms the agent value — is also a recorded action, never an
absence; neither value is mutated in place; resolving an event the queue
does not hold raises (broken wiring, I.1 line).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.contracts.base import CCFContract
from ccf.authz.capability import Authorized, HitlSubmit
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuditLog
from ccf.hitl.override import (
    OverrideBoundary,
    OverrideResolution,
    OverrideResolutionRefused,
    UnknownOverrideEventError,
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


class _Determination(CCFContract):
    """A deployment-shaped agent output; its values live in the fixture."""

    subject_uri: str
    determination: str


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
    fixture: dict[str, Any],
    *,
    product_content_hash: str,
    # SEC-005: the verdict is a signed claim and `enforce_signed_binding`
    # compares it to the submission's action. `OverrideBoundary.resolve`
    # submits `override` only when a substitute is actually supplied
    # (`overridden = override is not None`), so an approver signs `override`
    # exactly when they are substituting a value and `approve` when they are
    # letting the determination stand.
    verdict: str = "approve",
) -> HumanPrincipalBinding:
    approver = fixture["approvers"]["credit_officer"]
    return HumanPrincipalBinding(
        verdict=verdict,
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _boundary() -> tuple[
    OverrideBoundary[_Determination], InMemoryHitlTransport, AuditLog
]:
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    boundary: OverrideBoundary[_Determination] = OverrideBoundary(
        transport=transport, audit=audit, clock=_clock()
    )
    return boundary, transport, audit


def _propose(
    boundary: OverrideBoundary[_Determination], fixture: dict[str, Any]
) -> _Determination:
    document = fixture["override"]["event"]
    original = _Determination(**fixture["override"]["original"])
    boundary.propose(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        original=original,
        policy_ref=document["policy_ref"],
    )
    return original


def test_an_override_records_both_values_byte_assertably() -> None:
    """Original AND substitute land canonically serialized in the dim-2
    block (T-07-16 mitigation), and neither is mutated in place."""
    fixture = _hitl()
    boundary, transport, audit = _boundary()
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    substitute = _Determination(**fixture["override"]["substitute"])
    resolution = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(
            fixture, product_content_hash=content_hash(original)
        ),
        override=substitute,
    )
    assert isinstance(resolution, OverrideResolution)
    assert resolution.record.overridden
    assert resolution.record.original == original
    assert resolution.record.final == substitute
    block = resolution.hitl_actions_block
    assert block == canonical_bytes(resolution.record).decode("utf-8")
    assert canonical_bytes(original).decode("utf-8") in block
    assert canonical_bytes(substitute).decode("utf-8") in block
    # Preserved verbatim: the inputs still equal their fixture values.
    assert original == _Determination(**fixture["override"]["original"])
    assert substitute == _Determination(**fixture["override"]["substitute"])
    (submission,) = transport.submissions(tenant=document["tenant"])
    assert submission.action == "override"
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved


def test_an_unbound_override_is_unrepresentable() -> None:
    """The typed transport contract requires the principal by type (D-22
    type-unrepresentable leg)."""
    fixture = _hitl()
    document = fixture["override"]["event"]
    with pytest.raises(ValidationError):
        HitlActionSubmission(  # type: ignore[call-arg]
            event_key=document["event_key"],
            action="override",
        )


def test_a_hash_mismatch_is_refused_and_the_event_stays_pending() -> None:
    """The binding's product_content_hash must name what the overrider
    actually saw; a mismatch is a typed refusal, audited resolved=False."""
    fixture = _hitl()
    boundary, transport, audit = _boundary()
    _propose(boundary, fixture)
    document = fixture["override"]["event"]
    stale = content_hash({"stale": "output"})
    refused = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(fixture, product_content_hash=stale),
        override=_Determination(**fixture["override"]["substitute"]),
    )
    assert isinstance(refused, OverrideResolutionRefused)
    assert len(transport.pending(tenant=document["tenant"])) == 1
    events = audit.events()
    assert events[-1].action == "hitl_action" and not events[-1].resolved


def test_a_declined_override_is_a_recorded_action() -> None:
    """Confirming the agent value is an action, never an absence: recorded,
    audited, and on dimension 2 with overridden=False."""
    fixture = _hitl()
    boundary, transport, audit = _boundary()
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    resolution = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(
            fixture, product_content_hash=content_hash(original)
        ),
        override=None,
    )
    assert isinstance(resolution, OverrideResolution)
    assert not resolution.record.overridden
    assert resolution.record.original == original
    assert resolution.record.final == original
    assert resolution.hitl_actions_block == canonical_bytes(
        resolution.record
    ).decode("utf-8")
    (submission,) = transport.submissions(tenant=document["tenant"])
    assert submission.action == "approve"
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved


def test_resolving_on_a_second_instance_is_typed_and_mutates_nothing() -> None:
    """WR-01: the transport may be shared across primitive instances, but
    the proposal-time original is per-instance side-band state. Resolving
    on an instance that did not propose raises the typed broken-wiring
    error *before* any transport mutation — never a bare ``KeyError``
    after the authority path already recorded the action."""
    fixture = _hitl()
    boundary, transport, audit = _boundary()
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]

    other: OverrideBoundary[_Determination] = OverrideBoundary(
        transport=transport, audit=audit, clock=_clock()
    )
    with pytest.raises(UnknownOverrideEventError):
        other.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=_principal(
                fixture, product_content_hash=content_hash(original)
            ),
        )

    # Nothing landed on the authority path and the event survives.
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_resolving_an_unknown_event_raises() -> None:
    fixture = _hitl()
    boundary, _, _ = _boundary()
    document = fixture["override"]["event"]
    with pytest.raises(UnknownOverrideEventError):
        boundary.resolve(
            _authorized(document["tenant"], "acme-bank/exec-ovr/no-such-event"),
            event_key="acme-bank/exec-ovr/no-such-event",
            principal=_principal(
                fixture, product_content_hash=content_hash({"any": "thing"})
            ),
            override=None,
        )


# --- 10-02 Task 2: resolve-surface signed-binding verification (D-IMPL-69) ---


def _signing_env(tmp_path: Path) -> tuple[Any, str, dict[str, Any]]:
    import json as _json

    from joserfc.jwk import ECKey

    from ccf.peering.identity import (
        DetachedJwsIdentityProvider,
        FileBackedKeySource,
    )

    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    kid = "override-approver-key"
    key = ECKey.generate_key("P-256", parameters={"kid": kid})
    (key_dir / f"{kid}.jwk").write_text(
        _json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    return provider, kid, {kid: key.as_dict(private=False)}


def _bound_boundary(
    tmp_path: Path,
) -> tuple[OverrideBoundary[_Determination], InMemoryHitlTransport, Any, str]:
    from ccf.controlplane.artifacts import parse_artifact
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.hitl.transport import HITL_POLICY

    provider, kid, trusted = _signing_env(tmp_path)
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
    transport = InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
        trusted_keys=trusted,
    )
    boundary: OverrideBoundary[_Determination] = OverrideBoundary(
        transport=transport,
        audit=AuditLog(),
        clock=_clock(),
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
        trusted_keys=trusted,
    )
    return boundary, transport, provider, kid


def test_override_required_and_unsigned_resolve_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.identity_binding import sign_principal_binding
    from ccf.hitl.transport import SignedBindingRequiredRefused

    fixture = _hitl()
    boundary, transport, provider, kid = _bound_boundary(tmp_path)
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    principal = _principal(
        fixture, product_content_hash=content_hash(original)
    )
    with pytest.raises(SignedBindingRequiredRefused):
        boundary.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
            override=None,
        )
    # The pending event survives the refusal.
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()
    # A subsequent valid resolve of the SAME event succeeds.
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    resolution = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        override=None,
        signed_binding=signed,
    )
    assert isinstance(resolution, OverrideResolution)


def test_override_required_and_tampered_binding_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.identity_binding import sign_principal_binding
    from ccf.hitl.transport import SignedBindingInvalidRefused

    fixture = _hitl()
    boundary, transport, provider, kid = _bound_boundary(tmp_path)
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    principal = _principal(
        fixture, product_content_hash=content_hash(original)
    )
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    tampered = signed.model_copy(
        update={"signature": signed.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        boundary.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
            override=None,
            signed_binding=tampered,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_override_required_and_valid_binding_passes_both_layers(
    tmp_path: Path,
) -> None:
    """The transport's own second verification also passes (D-13)."""
    from ccf.hitl.identity_binding import sign_principal_binding

    fixture = _hitl()
    boundary, transport, provider, kid = _bound_boundary(tmp_path)
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    substitute = _Determination(**fixture["override"]["substitute"])
    principal = _principal(
        fixture,
        product_content_hash=content_hash(original),
        # This approver IS substituting a value, so the action the boundary
        # will submit is `override` — and that is what they sign (SEC-005).
        verdict="override",
    )
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    resolution = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        override=substitute,
        signed_binding=signed,
    )
    assert isinstance(resolution, OverrideResolution)
    recorded = transport.submissions(tenant=document["tenant"])
    assert len(recorded) == 1
    assert recorded[0].signed_binding == signed


def test_override_unbound_kwargs_behave_as_before() -> None:
    """No Control Plane bound: byte-identical pre-Phase-10 behavior."""
    fixture = _hitl()
    boundary, transport, _ = _boundary()
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    resolution = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(
            fixture, product_content_hash=content_hash(original)
        ),
        override=None,
    )
    assert isinstance(resolution, OverrideResolution)


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
    boundary, transport, audit = _boundary()
    document = fixture["override"]["event"]
    original = _Determination(**fixture["override"]["original"])
    pending = boundary.propose(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        original=original,
        policy_ref=document["policy_ref"],
    )
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=document["event_key"] + "-decoy",
            event_class="override-boundary",
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
    principal = _principal(fixture, product_content_hash=pending.product_content_hash)
    read = queue_read_capability(
        tenant=document["tenant"], principal="credit-officer-11", resource=document["event_key"]
    )
    with pytest.raises(CapabilityBypassError, match="kind"):
        boundary.resolve(
            read,  # type: ignore[arg-type]
            event_key=document["event_key"],
            principal=principal,
        )
    assert transport.pending(tenant=document["tenant"]) == pending_before
    assert transport.submissions(tenant=document["tenant"]) == ()
    assert audit.events() == audit_before


def test_a_capability_for_another_event_dies_at_the_primitive() -> None:
    from ccf.authz.capability import CapabilityBypassError

    fixture = _hitl()
    boundary, transport, audit = _boundary()
    document = fixture["override"]["event"]
    original = _Determination(**fixture["override"]["original"])
    pending = boundary.propose(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        original=original,
        policy_ref=document["policy_ref"],
    )
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=document["event_key"] + "-decoy",
            event_class="override-boundary",
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
    principal = _principal(fixture, product_content_hash=pending.product_content_hash)
    with pytest.raises(CapabilityBypassError, match="resource"):
        boundary.resolve(
            _authorized(document["tenant"], "some-other-event"),
            event_key=document["event_key"],
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
    boundary, transport, _ = _boundary()
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    authorized = _authorized(document["tenant"], document["event_key"])
    resolution = boundary.resolve(
        authorized,
        event_key=document["event_key"],
        principal=_principal(
            fixture, product_content_hash=content_hash(original)
        ),
        override=_Determination(**fixture["override"]["substitute"]),
    )
    assert isinstance(resolution, OverrideResolution)
    assert (
        resolution.record.submission.authorizing_decision_id
        == authorized.decision_id
    )
    assert authorized.decision_id in resolution.hitl_actions_block
