"""Verifying a recorded erasure approval against its signed HITL attestation (SEC-009; `D-IMPL-374` (4), fix round 4).

The erasure approval is bound to a SIGNED HITL attestation — the SEC-005
:class:`~ccf.hitl.identity_binding.SignedHitlAction` (`D-IMPL-363`). The door
refuses an approval that is unsigned or does not verify; the
:class:`~ccf.erasure.contracts.ErasureApproval` it files carries the signed
claim set, the detached signature and the key id verbatim, with the
transport-stamped pin of the HITL policy in force. :func:`verify_erasure_approval`
is the ONE check both the door and the decorating store run. **The requester
never chooses the trust root** (the fix-round-4 rulings 1–4):

1. **The HITL policy key is fixed at composition (ruling 1).** The pin the
   approval carries may name the VERSION, never the key: its key must be the
   deployment's HITL policy key — the same key the HITL transport is bound to
   — and that key's tenant segment must be the approval's tenant. Any other
   key refuses by name (``approval-policy-key-mismatch``,
   ``approval-policy-tenant-mismatch``).
2. The pinned version is resolved EXACTLY through the composed Control Plane
   (never latest — replay determinism, CLAUDE.md §7.4); the key id must be one
   that version declares for the signing subject, and the signature must
   verify against exactly those keys (`D-IMPL-363` E5).
3. The signed claims must name this request's gate event
   (``{tenant}/{request_id}/{gate}``), this tenant, the gate's state hash the
   approver saw, the approver and the approving verdict, and the artifact's own
   fields must agree, with ``acted_at`` the signer's ``issued_at``.
4. **Revocation (ruling 4).** The signed ``issued_at`` must precede the pinned
   version's SUPERSESSION — the instant the Control Plane's audit plane records
   the registration of the next version under the key; the current version's
   window is open-ended. A signature dated after supersession, under a version
   whose key was since dropped, refuses by name (``approval-policy-superseded``).
   An approval made while that version was current stays valid.
5. **Approver ≠ requester, and eligible (ruling 2).** The record's approver
   must not be its requester, and must be eligible under the approval policy
   the record names, resolved at its exact version — the SAME judgment the
   transport applies at the door (:func:`ccf.hitl.transport
   .check_approver_eligibility`), applied again here
   (``approver-is-requester``, ``approver-not-eligible``).
6. **The gate is the workflow definition's (ruling 3).** The definition is
   resolved by ``workflow_definition_hash`` — its content address, which is
   its registered version — and ``approval.gate`` must be one of that
   definition's HITL gates, bound to the record's approval policy
   (``approval-workflow-unresolvable``, ``approval-gate-unknown``,
   ``approval-gate-policy-mismatch``).

Holding ``ArtifactErase`` lets a requester FILE an approval artifact; it does
not let them produce a signature the deployment's pinned policy accepts, name
a policy of their own, approve their own request, or invent a gate.

:func:`policy_head` is the digest of the Control Plane's registration history
the decorating store keys its validation cache by, so ANY registration — a
rotated HITL policy foremost — re-judges every cached verdict, and a verdict
is never keyed by a Control Plane object's identity.

Disclosed: verification is only as strong as the HITL policy's key custody and
the Control Plane's registration authority. The signed instant is the signer's
own claim: a holder of a dropped key who backdates a signature to before the
supersession still verifies under the old version. An adopter-supplied
identity provider that verifies nothing accepts everything; that is the
adopter's trust choice.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Final, Protocol, runtime_checkable

from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.registry import AmbiguousPinnedVersionError
from ccf.controlplane.state import state_key
from ccf.erasure.contracts import ErasureApproval
from ccf.hitl.identity_binding import AttestationInvalid, HitlActionClaims, verify_hitl_action
from ccf.hitl.principal import ApproverIdentity
from ccf.hitl.transport import ApproverNotEligible, HitlPolicy, check_approver_eligibility
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    IdentityProvider,
    JsonWebKey,
    KeyUnavailable,
)
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition

__ccf_mode__ = "algorithmic"

__all__ = [
    "APPROVING_VERDICT",
    "PinnedPolicySource",
    "ErasureApprovalInvalid",
    "policy_head",
    "reference_approval_verifier",
    "verify_erasure_approval",
]

#: The signed HITL action that approves (the gate's ``approve``).
APPROVING_VERDICT: Final[str] = "approve"

#: The audit actions that record a registration (the Control Plane's
#: registration history, which :func:`policy_head` digests and the
#: supersession instant is read from).
_REGISTRATIONS: Final[frozenset[str]] = frozenset({"register", "register_typed", "register_versioned"})

#: The separator of the ``{tenant}/{class}/{name}`` Control Plane key grammar.
_KEY_SEPARATOR: Final[str] = "/"


@runtime_checkable
class PinnedPolicySource(Protocol):
    """What the approval check reads from the Control Plane (fix round 4).

    Every :class:`~ccf.controlplane.registry.ControlPlaneRegistry` satisfies it.
    Read-only on purpose, and the check never resolves "latest": ``resolve``
    is exact-version; ``versions``, ``peek`` and ``artifact_class_of`` are the
    pinned-read surface the eligibility judgment shares with the transport;
    ``keys_of_class`` locates the workflow definition by its hash; and
    ``audit_events`` is the registration history the supersession instant and
    :func:`policy_head` are read from.
    """

    def resolve(self, key: str, version: str) -> object:
        """Return the artifact registered as exactly ``(key, version)``."""
        ...

    def versions(self, key: str) -> tuple[str, ...]:
        """Return every version registered under ``key``, oldest first."""
        ...

    def peek(self, key: str, version: str) -> object:
        """Return the artifact at ``(key, version)`` without auditing."""
        ...

    def artifact_class_of(self, key: str) -> str | None:
        """Return the artifact class bound to ``key``, if it was typed."""
        ...

    def keys_of_class(self, class_id: str) -> tuple[str, ...]:
        """Every key bound to ``class_id``, in first-registration order."""
        ...

    def audit_events(self) -> tuple[AuditEvent, ...]:
        """The append-only audit log, oldest first."""
        ...


class ErasureApprovalInvalid(ValueError):
    """An erasure approval that is not a verified, approving, signed HITL action for this request.

    ``reason_code`` names which judgment refused it: ``approval-unsigned`` (no
    attestation), ``approval-policy-key-mismatch`` (the pin names a key other
    than the deployment's HITL policy key), ``approval-policy-tenant-mismatch``
    (that key is not in the approval's tenant), ``approval-policy-unresolvable``
    (the pinned version is absent or not a ``HitlPolicy``),
    ``approval-signature-invalid`` (the key is not declared for the subject,
    or the signature does not verify), ``approval-claims-mismatch`` (a signed
    claim or an artifact field names another request, gate, tenant, state,
    approver, instant or verdict), ``approval-policy-superseded`` (signed
    after the pinned version was superseded), ``approval-policy-window-unknown``
    (the Control Plane records no registration instant for the superseding
    version), ``approver-is-requester``, ``approver-not-eligible`` (the
    transport's door rule, refused again here), ``approval-workflow-unresolvable``
    (no registered workflow definition has the approval's hash),
    ``approval-gate-unknown`` (the gate is not one of that definition's HITL
    gates) or ``approval-gate-policy-mismatch`` (that gate is bound to a
    different approval policy than the record names).
    """

    def __init__(self, detail: str, *, reason_code: str) -> None:
        super().__init__(detail)
        self.reason_code = reason_code


class _NoSigningKeys:
    """A key source with no private material: the reference verifier signs nothing."""

    def signing_key(self, *, key_id: str) -> JsonWebKey:
        raise KeyUnavailable(f"the erasure approval verifier holds no signing key ({key_id!r})")

    def key_ids(self) -> tuple[str, ...]:
        return ()


def reference_approval_verifier() -> IdentityProvider:
    """The SDK's reference detached-JWS verifier, with no signing material.

    Used where a composition site does not supply the identity provider its HITL
    transport verifies with. A deployment whose transport signs under another
    algorithm passes its own provider; under this one its approvals do not
    verify and fail CLOSED (``index-unsupported``).
    """
    return DetachedJwsIdentityProvider(key_source=_NoSigningKeys())


def _tenant_segment(key: str) -> str | None:
    tenant, separator, _ = key.partition(_KEY_SEPARATOR)
    return tenant if separator and tenant else None


def _registrations(control_plane: PinnedPolicySource) -> tuple[AuditEvent, ...]:
    return tuple(
        event
        for event in control_plane.audit_events()
        if event.action in _REGISTRATIONS and event.resolved
    )


def policy_head(control_plane: PinnedPolicySource) -> str:
    """The digest of the Control Plane's registration history (fix round 4, ruling 4).

    Every resolved registration — key, version and instant, in order — is
    folded into one sha256, so the head changes on ANY registration and on
    nothing else: a resolution audits but does not move it. Two Control Planes
    with the same registration history have the same head; a Control Plane
    object's identity is never part of it.
    """
    digest = hashlib.sha256()
    for event in _registrations(control_plane):
        digest.update(f"{event.action}\x1f{event.key}\x1f{event.version}\x1f{event.occurred_at.isoformat()}\x1e".encode())
    return digest.hexdigest()


def _registered_at(control_plane: PinnedPolicySource, key: str, version: str) -> datetime | None:
    """The instant the Control Plane first recorded ``(key, version)`` registered, or ``None``."""
    for event in _registrations(control_plane):
        if event.key == key and event.version == version:
            return event.occurred_at
    return None


def _workflow_definition(control_plane: PinnedPolicySource, definition_hash: str) -> WorkflowDefinition | None:
    """The registered workflow definition whose content address is ``definition_hash``.

    A definition's registered version IS its content address (`D-IMPL-26`),
    so the hash the approval carries is looked up directly under every key of
    the definition class; nothing is scanned by content.
    """
    for key in control_plane.keys_of_class(WORKFLOW_DEFINITION.class_id):
        if definition_hash in control_plane.versions(key):
            found = control_plane.resolve(key, definition_hash)
            return found if isinstance(found, WorkflowDefinition) else None
    return None


def verify_erasure_approval(
    approval: ErasureApproval,
    *,
    tenant_id: str,
    request_id: str,
    approver: ApproverIdentity,
    requested_by: str,
    approval_policy_ref: str,
    hitl_policy_key: str,
    control_plane: PinnedPolicySource,
    identity_provider: IdentityProvider,
) -> HitlActionClaims:
    """Return the verified signed claims, or raise :class:`ErasureApprovalInvalid`.

    Args:
        approval: The filed ``ccf.erasure-approval``.
        tenant_id, request_id: The erasure the record (or the door) names.
        approver: The record's actor.
        requested_by: The record's requester — the starter the engine recorded.
        approval_policy_ref: The pinned approval policy the record names (the
            gate's, from the workflow definition).
        hitl_policy_key: The deployment's HITL policy key, fixed at composition
            (ruling 1).
        control_plane: The deployment's Control Plane.
        identity_provider: The verifier the deployment's HITL transport
            verifies with.

    Raises:
        ErasureApprovalInvalid: any of the module docstring's judgments.
    """
    signed = approval.attestation
    key, at, version = approval.hitl_policy_ref.rpartition("@")
    if not at or not key or not version:
        raise ErasureApprovalInvalid(
            f"the approval pins no HITL policy version ({approval.hitl_policy_ref!r})",
            reason_code="approval-policy-unresolvable",
        )
    # Ruling 1: the key is the deployment's, never the artifact's choice.
    if key != hitl_policy_key:
        raise ErasureApprovalInvalid(
            f"the approval pins HITL policy key {key!r}; this deployment's erasure"
            f" approvals verify under {hitl_policy_key!r} only (SEC-009; fix round 4,"
            " ruling 1)",
            reason_code="approval-policy-key-mismatch",
        )
    if _tenant_segment(key) != approval.tenant_id or approval.tenant_id != tenant_id:
        raise ErasureApprovalInvalid(
            f"HITL policy key {key!r} is not in the approval's tenant"
            f" {approval.tenant_id!r} (SEC-009; fix round 4, ruling 1)",
            reason_code="approval-policy-tenant-mismatch",
        )
    try:
        policy = control_plane.resolve(key, version)
    except (KeyError, LookupError, ValueError) as missing:
        raise ErasureApprovalInvalid(
            f"the pinned HITL policy {approval.hitl_policy_ref!r} does not resolve"
            " in this Control Plane",
            reason_code="approval-policy-unresolvable",
        ) from missing
    if not isinstance(policy, HitlPolicy):
        raise ErasureApprovalInvalid(
            f"{approval.hitl_policy_ref!r} is not a HitlPolicy",
            reason_code="approval-policy-unresolvable",
        )
    claims = signed.claims
    declared = policy.keys_for(claims.subject_id)
    if signed.key_id not in declared:
        raise ErasureApprovalInvalid(
            f"key {signed.key_id!r} is not declared for {claims.subject_id!r} by the"
            " pinned HITL policy (D-IMPL-363 E5)",
            reason_code="approval-signature-invalid",
        )
    try:
        verified = verify_hitl_action(signed, provider=identity_provider, public_keys=declared)
    except AttestationInvalid as invalid:
        raise ErasureApprovalInvalid(
            "the approval's signed HITL attestation does not verify under the key"
            " the pinned policy declares for its signer (SEC-009; D-IMPL-363)",
            reason_code="approval-signature-invalid",
        ) from invalid
    expected_event = f"{state_key(tenant=tenant_id, record_id=request_id)}/{approval.gate}"
    mismatches = [
        name
        for name, agrees in (
            ("tenant", verified.tenant == tenant_id == approval.tenant_id),
            ("request", approval.request_id == request_id),
            ("event_key", verified.event_key == expected_event),
            ("verdict", verified.action == APPROVING_VERDICT == approval.verdict),
            ("gate_state_hash", verified.product_content_hash == approval.gate_state_hash),
            (
                "approver",
                verified.subject_id == approver.subject_id
                and approval.approver == approver,
            ),
            ("acted_at", approval.acted_at == verified.issued_at),
        )
        if not agrees
    ]
    if mismatches:
        raise ErasureApprovalInvalid(
            f"the signed approval does not approve this request: {mismatches}"
            " (SEC-009; D-IMPL-374 (4), fix round 4)",
            reason_code="approval-claims-mismatch",
        )
    # Ruling 4: the pinned version's effectivity ends at its supersession.
    versions = control_plane.versions(key)
    position = versions.index(version) if version in versions else -1
    if 0 <= position < len(versions) - 1:
        superseded_at = _registered_at(control_plane, key, versions[position + 1])
        if superseded_at is None:
            raise ErasureApprovalInvalid(
                f"HITL policy {key!r} was superseded after version {version!r}, but the"
                " Control Plane records no registration instant for the superseding"
                " version, so the approval's window cannot be judged (SEC-009; fix"
                " round 4, ruling 4)",
                reason_code="approval-policy-window-unknown",
            )
        if verified.issued_at >= superseded_at:
            raise ErasureApprovalInvalid(
                f"the approval was signed at {verified.issued_at.isoformat()} under HITL"
                f" policy version {version!r}, which {superseded_at.isoformat()}"
                " superseded (SEC-009; fix round 4, ruling 4)",
                reason_code="approval-policy-superseded",
            )
    # Ruling 2: the door rule, applied again.
    if approver.subject_id == requested_by:
        raise ErasureApprovalInvalid(
            "the approver is the requester of the erasure they are approving"
            " (SEC-009; fix round 4, ruling 2; D-IMPL-366 G3)",
            reason_code="approver-is-requester",
        )
    try:
        check_approver_eligibility(
            policy_ref=approval_policy_ref,
            requested_by=requested_by,
            subject_id=approver.subject_id,
            control_plane=control_plane,
        )
    except (ApproverNotEligible, AmbiguousPinnedVersionError) as ineligible:
        raise ErasureApprovalInvalid(
            f"the approver is not eligible under {approval_policy_ref!r} ({ineligible})"
            " (SEC-009; fix round 4, ruling 2)"[:400],
            reason_code="approver-not-eligible",
        ) from ineligible
    # Ruling 3: the gate is the workflow definition's.
    definition = _workflow_definition(control_plane, approval.workflow_definition_hash)
    if definition is None:
        raise ErasureApprovalInvalid(
            f"no registered workflow definition has content address"
            f" {approval.workflow_definition_hash!r} (SEC-009; fix round 4, ruling 3)",
            reason_code="approval-workflow-unresolvable",
        )
    if approval.gate not in definition.gate_policies:
        raise ErasureApprovalInvalid(
            f"gate {approval.gate!r} is not an approval gate of workflow definition"
            f" {definition.name!r} (SEC-009; fix round 4, ruling 3)",
            reason_code="approval-gate-unknown",
        )
    if definition.gate_policies[approval.gate] != approval_policy_ref:
        raise ErasureApprovalInvalid(
            f"gate {approval.gate!r} is bound to approval policy"
            f" {definition.gate_policies[approval.gate]!r}, not the record's"
            f" {approval_policy_ref!r} (SEC-009; fix round 4, ruling 3)",
            reason_code="approval-gate-policy-mismatch",
        )
    return verified
