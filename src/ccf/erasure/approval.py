"""Verifying a recorded erasure approval against its signed HITL attestation (SEC-009; `D-IMPL-374` (4), fix round 4).

The erasure approval is bound to a SIGNED HITL attestation — the SEC-005
:class:`~ccf.hitl.identity_binding.SignedHitlAction` (`D-IMPL-363`). The door
refuses an approval that is unsigned or does not verify; the
:class:`~ccf.erasure.contracts.ErasureApproval` it files carries the signed
claim set, the detached signature and the key id verbatim, with the
transport-stamped pin of the HITL policy in force. :func:`verify_erasure_approval`
is the ONE check both the door and the decorating store run, against the
tenant's :class:`~ccf.erasure.ErasureAuthority` — fixed at composition, never
chosen by a filed artifact. **The requester never chooses the trust root**
(fix round 4, rulings 1–4, as fix round 5 amended them):

0. **The erasure workflow and its tenant are fixed at composition (fix round
   5, R1).** The approval's tenant must be the authority's, and its
   ``workflow_definition_hash`` the declared erasure workflow's content hash;
   anything else refuses by name (``approval-tenant-mismatch``,
   ``approval-workflow-mismatch``).
1. **The HITL policy key is fixed at composition (ruling 1).** The pin the
   approval carries may name the VERSION, never the key: its key must be the
   authority's HITL policy key — the same key the tenant's HITL transport is
   bound to — and any other key refuses by name
   (``approval-policy-key-mismatch``). The authority itself refuses, at
   construction, a key outside its own tenant
   (:class:`~ccf.erasure.ErasureAuthority`), so with item 0 the key always
   lies in the approval's tenant.
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
5. **Approver ≠ requester (ruling 2).** The approver must not be the
   record's requester — and the requester is what the erasure DOOR observed
   and signed (fix round 5, R2; :func:`~ccf.erasure.verify_erasure_entry`
   verifies the door signature before the record is read), never what a filer
   wrote (``approver-is-requester``).
6. **The gate and its policy are the declared workflow's (ruling 3, fix round
   5 R1).** The declared erasure workflow is resolved from the Control Plane
   by its content hash — content-verified, in the authority's tenant
   (``approval-workflow-unresolvable``); ``approval.gate`` must be its ERASURE
   gate — an approval gate whose approve route completes the workflow, the
   only gate the door files a record for (``approval-gate-unknown``); and the
   approver must be eligible under THAT gate's approval policy, resolved at
   its pinned version — the
   SAME judgment the transport applies at the door
   (:func:`ccf.hitl.transport.check_approver_eligibility`), applied again
   here (``approver-not-eligible``). No record field names the policy.

Holding ``ArtifactErase`` lets a requester FILE an approval artifact; it does
not let them produce a signature the deployment's pinned policy accepts, name
a policy or a workflow of their own, approve their own request, or invent a
gate.

:func:`policy_head` is the digest of the Control Plane's registration history
the decorating store keys its validation cache by, so ANY registration — a
rotated HITL policy foremost — re-judges every cached verdict, and a verdict
is never keyed by a Control Plane object's identity.

Disclosed: verification is only as strong as the HITL policy's key custody and
the Control Plane's registration authority under the authority's HITL policy
key. The signed instant is the signer's own claim: a holder of a dropped key
who backdates a signature to before the supersession still verifies under the
old version. An adopter-supplied identity provider that verifies nothing
accepts everything; that is the adopter's trust choice.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Final, Protocol, runtime_checkable

from ccf.contracts.canonical import content_hash
from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.registry import AmbiguousPinnedVersionError
from ccf.controlplane.state import state_key
from ccf.erasure.contracts import ErasureApproval
from ccf.erasure.trust import ErasureAuthority
from ccf.hitl.identity_binding import AttestationInvalid, HitlActionClaims, verify_hitl_action
from ccf.hitl.principal import ApproverIdentity
from ccf.hitl.transport import ApproverNotEligible, HitlPolicy, check_approver_eligibility
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    IdentityProvider,
    JsonWebKey,
    KeyUnavailable,
)
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WORKFLOW_FAILED_STATE, WorkflowDefinition

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

    ``reason_code`` names which judgment refused it: ``approval-tenant-mismatch``
    (the approval is not in the authority's tenant — fix round 5, R1),
    ``approval-workflow-mismatch`` (it names a workflow other than the declared
    erasure workflow — R1), ``approval-unsigned`` (no
    attestation), ``approval-policy-key-mismatch`` (the pin names a key other
    than the authority's HITL policy key), ``approval-policy-unresolvable``
    (the pinned version is absent or not a ``HitlPolicy``),
    ``approval-signature-invalid`` (the key is not declared for the subject,
    or the signature does not verify), ``approval-claims-mismatch`` (a signed
    claim or an artifact field names another request, gate, tenant, state,
    approver, instant or verdict), ``approval-policy-superseded`` (signed
    after the pinned version was superseded), ``approval-policy-window-unknown``
    (the Control Plane records no registration instant for the superseding
    version), ``approver-is-requester``, ``approver-not-eligible`` (the
    transport's door rule under the declared workflow's gate policy, refused
    again here), ``approval-policy-ambiguous`` (two contents declare the
    gate's approval policy at its pinned version, so the Control Plane refuses
    to resolve it — a Control Plane fault, not the approver's; PM6, panel C6),
    ``approval-workflow-unresolvable`` (the Control Plane holds no
    definition with the declared hash, in the authority's tenant) or
    ``approval-gate-unknown`` (the gate is not that definition's erasure gate —
    an approval gate whose approve route completes the workflow).
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


#: The ONE reference verifier: stateless (no signing material, a fixed
#: algorithm), so every composition that declares no provider shares it — and
#: shares the validation cache keyed by the provider instance (fix round 5, R3).
_REFERENCE_VERIFIER: Final[IdentityProvider] = DetachedJwsIdentityProvider(key_source=_NoSigningKeys())


def reference_approval_verifier() -> IdentityProvider:
    """The SDK's reference detached-JWS verifier, with no signing material (SEC-009; `D-IMPL-374` (4)).

    Used where a composition site does not supply the identity provider its HITL
    transport verifies with. A deployment whose transport signs under another
    algorithm passes its own provider; under this one its approvals do not
    verify and fail CLOSED (``index-unsupported``). Always the same instance:
    it holds no state, so the validation cache, keyed by the provider instance
    (fix round 5, R3), is shared by every composition that declares none.
    """
    return _REFERENCE_VERIFIER


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


def _erasure_workflow(control_plane: PinnedPolicySource, authority: ErasureAuthority) -> WorkflowDefinition | None:
    """The DECLARED erasure workflow, resolved from the Control Plane at its pinned version (fix round 5, R1).

    A definition's registered version IS its content address (`D-IMPL-26`), so
    the authority's hash is looked up directly under every key of the
    definition class — and what resolves is held to it: its content must hash
    to the declared hash and name the authority's tenant, so no other content
    registered under that label is ever taken for it.
    """
    wanted = authority.workflow_definition_hash
    for key in control_plane.keys_of_class(WORKFLOW_DEFINITION.class_id):
        if wanted not in control_plane.versions(key):
            continue
        found = control_plane.resolve(key, wanted)
        if (
            isinstance(found, WorkflowDefinition)
            and content_hash(found) == wanted
            and found.tenant == authority.tenant_id
        ):
            return found
    return None


def verify_erasure_approval(
    approval: ErasureApproval,
    *,
    tenant_id: str,
    request_id: str,
    approver: ApproverIdentity,
    requested_by: str,
    authority: ErasureAuthority,
    control_plane: PinnedPolicySource,
    identity_provider: IdentityProvider,
) -> HitlActionClaims:
    """Return the verified signed claims, or raise :class:`ErasureApprovalInvalid` (SEC-009; `D-IMPL-374` (4), fix rounds 4 and 5).

    Args:
        approval: The filed ``ccf.erasure-approval``.
        tenant_id, request_id: The erasure the record (or the door) names.
        approver: The record's actor.
        requested_by: The record's requester — the starter the engine recorded,
            as the erasure door observed and SIGNED it (fix round 5, R2).
        authority: The tenant's :class:`~ccf.erasure.ErasureAuthority`, fixed
            at composition: the erasure workflow and its tenant (R1) and the
            HITL policy key (ruling 1).
        control_plane: The deployment's Control Plane.
        identity_provider: The verifier the deployment's HITL transport
            verifies with.

    Raises:
        ErasureApprovalInvalid: any of the module docstring's judgments.
    """
    # Fix round 5, R1: the erasure workflow, and its tenant, fixed at composition.
    if approval.tenant_id != authority.tenant_id or tenant_id != authority.tenant_id:
        raise ErasureApprovalInvalid(
            f"the approval is for tenant {approval.tenant_id!r} and the erasure for"
            f" {tenant_id!r}; this authority verifies tenant {authority.tenant_id!r}'s"
            " erasures only (SEC-009; D-IMPL-374 (4), fix round 5, R1)",
            reason_code="approval-tenant-mismatch",
        )
    if approval.workflow_definition_hash != authority.workflow_definition_hash:
        raise ErasureApprovalInvalid(
            f"the approval names workflow definition {approval.workflow_definition_hash!r};"
            " the erasure workflow declared at composition is"
            f" {authority.workflow_definition_hash!r} (SEC-009; D-IMPL-374 (4), fix"
            " round 5, R1)",
            reason_code="approval-workflow-mismatch",
        )
    signed = approval.attestation
    key, at, version = approval.hitl_policy_ref.rpartition("@")
    if not at or not key or not version:
        raise ErasureApprovalInvalid(
            f"the approval pins no HITL policy version ({approval.hitl_policy_ref!r})",
            reason_code="approval-policy-unresolvable",
        )
    # Ruling 1: the key is the authority's, never the artifact's choice.
    if key != authority.hitl_policy_key:
        raise ErasureApprovalInvalid(
            f"the approval pins HITL policy key {key!r}; tenant {authority.tenant_id!r}'s"
            f" erasure approvals verify under {authority.hitl_policy_key!r} only"
            " (SEC-009; fix round 4, ruling 1)",
            reason_code="approval-policy-key-mismatch",
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
    # Ruling 2: the door rule, applied again — against the requester the
    # erasure DOOR observed and signed (fix round 5, R2).
    if approver.subject_id == requested_by:
        raise ErasureApprovalInvalid(
            "the approver is the requester of the erasure they are approving"
            " (SEC-009; fix round 4, ruling 2; D-IMPL-366 G3)",
            reason_code="approver-is-requester",
        )
    # Ruling 3 and fix round 5, R1: the gate, and the approval policy that
    # judges the approver, are the DECLARED erasure workflow's — never a field
    # of a filed artifact.
    definition = _erasure_workflow(control_plane, authority)
    if definition is None:
        raise ErasureApprovalInvalid(
            f"the Control Plane holds no workflow definition with the declared content"
            f" address {authority.workflow_definition_hash!r} in tenant"
            f" {authority.tenant_id!r} (SEC-009; fix round 5, R1)",
            reason_code="approval-workflow-unresolvable",
        )
    # THE erasure gate: an approval gate whose approve route ends the workflow
    # — the only gate the door files a record for — never an earlier gate
    # bound to another policy.
    approved_into = definition.gate_routes.get(approval.gate, {}).get(APPROVING_VERDICT)
    if (
        approval.gate not in definition.gate_policies
        or approved_into not in definition.effective_terminal_states
        or approved_into == WORKFLOW_FAILED_STATE
    ):
        raise ErasureApprovalInvalid(
            f"gate {approval.gate!r} is not the erasure gate of workflow definition"
            f" {definition.name!r} — an approval gate whose approve route completes the"
            " workflow (SEC-009; fix round 4, ruling 3; fix round 5, R1)",
            reason_code="approval-gate-unknown",
        )
    gate_policy = definition.gate_policies[approval.gate]
    try:
        check_approver_eligibility(
            policy_ref=gate_policy,
            requested_by=requested_by,
            subject_id=approver.subject_id,
            control_plane=control_plane,
        )
    except AmbiguousPinnedVersionError as ambiguous:
        # PM6 (panel C6; `D-IMPL-374`): not a judgment about the approver —
        # two contents declare the pinned version, so the Control Plane
        # refuses to resolve a moving target (D-IMPL-26). Fails closed, under
        # its own name.
        raise ErasureApprovalInvalid(
            f"the erasure gate's approval policy {gate_policy!r} is ambiguous at its"
            " pinned version: two contents declare it, and a pin that names two"
            f" contents is a moving target ({ambiguous}) (SEC-009; D-IMPL-26)"[:400],
            reason_code="approval-policy-ambiguous",
        ) from ambiguous
    except ApproverNotEligible as ineligible:
        raise ErasureApprovalInvalid(
            f"the approver is not eligible under the erasure gate's approval policy"
            f" {gate_policy!r} ({ineligible}) (SEC-009; fix round 4, ruling 2; fix round 5, R1)"[:400],
            reason_code="approver-not-eligible",
        ) from ineligible
    return verified
