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
    # SEC-005: the verdict is a signed claim and `enforce_attestation`
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


# --- 10-02 Task 2 / `D-IMPL-363`: resolve-surface attestation verification ---
#
# SEC-005's remaining leg (`D-IMPL-363`) replaced the signed door-minted
# binding with signer-stated `HitlActionClaims` carried as an `attestation`,
# and moved BOTH the trust map and the freshness window INSIDE the pinned
# `HitlPolicy` (E3/E5) — there is no `trusted_keys` constructor argument on the
# transport or on a primitive any more. These tests sign `issued_at` equal to
# the binding's FIXED `action_time`: that is the recorded instant the
# directional window is judged against (E2), so no participant reads a clock.
#
# `OverrideBoundary` DERIVES the action it submits — ``override`` when a
# substitute is supplied, ``approve`` when the human lets the determination
# stand — so the signed `action` must equal that derived verdict, and a
# signature over the other one refuses as a mismatch.

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
    kid = "override-approver-key"
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


def _bound_boundary(
    tmp_path: Path, fixture: dict[str, Any]
) -> tuple[
    OverrideBoundary[_Determination], InMemoryHitlTransport, Any, str, str
]:
    """The boundary, its transport, the signer's provider and key id, and the
    ``key@version`` the transport stamps on an admitted submission — derived
    from the registry's own resolution (`D-IMPL-363` E3), never a literal."""
    from ccf.controlplane.artifacts import parse_artifact
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
    boundary: OverrideBoundary[_Determination] = OverrideBoundary(
        transport=transport,
        audit=AuditLog(),
        clock=_clock(),
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
    )
    return (
        boundary,
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


def test_override_required_and_unsigned_resolve_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.transport import SignedBindingRequiredRefused

    fixture = _hitl()
    boundary, transport, provider, kid, _ = _bound_boundary(tmp_path, fixture)
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
    # A subsequent valid resolve of the SAME event succeeds. No substitute is
    # supplied, so the derived action is `approve` — and that is what is signed.
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture),
        nonce="override-nonce-after-unsigned",
    )
    resolution = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        override=None,
        attestation=attestation,
    )
    assert isinstance(resolution, OverrideResolution)


def test_override_required_and_tampered_attestation_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    """A tampered SIGNATURE refuses invalid and the event stays pending.

    Successor to
    ``test_override_required_and_tampered_binding_is_refused_event_pending``:
    the same property over the `D-IMPL-363` attestation rather than the removed
    signed binding.
    """
    from ccf.hitl.transport import SignedBindingInvalidRefused

    fixture = _hitl()
    boundary, transport, provider, kid, _ = _bound_boundary(tmp_path, fixture)
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    principal = _principal(
        fixture, product_content_hash=content_hash(original)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture),
        nonce="override-nonce-tampered",
    )
    tampered = attestation.model_copy(
        update={"signature": attestation.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        boundary.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
            override=None,
            attestation=tampered,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_override_required_and_an_attestation_for_the_other_derived_action_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    """`D-IMPL-363` C1(a): the signed action must equal the action the boundary
    DERIVES, and a signature over the other one authorizes nothing.

    The sibling a tampered signature cannot reach. The signature is genuine and
    the key is declared for this subject, so it verifies; the human signed
    ``approve`` — letting the determination stand — while actually supplying a
    substitute, which makes the boundary's derived action ``override``. Refused
    as a MISMATCH, with the event still pending: a signature over a confirmation
    may not be spent as a substitution.
    """
    from ccf.hitl.transport import SignedBindingMismatchRefused

    fixture = _hitl()
    boundary, transport, provider, kid, _ = _bound_boundary(tmp_path, fixture)
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    substitute = _Determination(**fixture["override"]["substitute"])
    principal = _principal(
        fixture, product_content_hash=content_hash(original)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",  # the human signed a confirmation...
        principal=principal,
        subject_id=_subject(fixture),
        nonce="override-nonce-other-derived-action",
    )
    with pytest.raises(SignedBindingMismatchRefused, match=r"\['action'\]"):
        boundary.resolve(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
            override=substitute,  # ...but a substitute is supplied
            attestation=attestation,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_override_required_and_valid_attestation_passes_both_layers(
    tmp_path: Path,
) -> None:
    """The transport's own second verification also passes (D-13).

    Successor to
    ``test_override_required_and_valid_binding_passes_both_layers``: one
    attestation satisfies the primitive's verification AND the transport's
    independent re-verification, the recorded submission carries it, and the
    record names the pinned policy that admitted it (`D-IMPL-363` E3).
    """
    fixture = _hitl()
    boundary, transport, provider, kid, pinned_ref = _bound_boundary(
        tmp_path, fixture
    )
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    substitute = _Determination(**fixture["override"]["substitute"])
    principal = _principal(
        fixture,
        product_content_hash=content_hash(original),
        # This approver IS substituting a value, so the action the boundary
        # derives is `override` — and that is what the binding records and what
        # the claims are signed over (D-IMPL-363 C1(a)).
        verdict="override",
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="override",
        principal=principal,
        subject_id=_subject(fixture),
        nonce="override-nonce-valid",
    )
    resolution = boundary.resolve(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        override=substitute,
        attestation=attestation,
    )
    assert isinstance(resolution, OverrideResolution)
    recorded = transport.submissions(tenant=document["tenant"])
    assert len(recorded) == 1
    assert recorded[0].attestation == attestation
    assert recorded[0].hitl_policy_ref == pinned_ref


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
