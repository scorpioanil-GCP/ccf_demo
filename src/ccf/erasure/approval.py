"""Verifying a recorded erasure approval against its signed HITL attestation (SEC-009; `D-IMPL-374` (4), fix round 4).

The erasure approval is bound to a SIGNED HITL attestation — the SEC-005
:class:`~ccf.hitl.identity_binding.SignedHitlAction` (`D-IMPL-363`). The door
refuses an approval that is unsigned or does not verify; the
:class:`~ccf.erasure.contracts.ErasureApproval` it files carries the signed
claim set, the detached signature and the key id verbatim, with the
transport-stamped pin of the HITL policy in force. :func:`verify_erasure_approval`
is the ONE check both the door and the decorating store run:

1. the pinned HITL policy is resolved at its EXACT version through the composed
   Control Plane (never latest — replay determinism, CLAUDE.md §7.4);
2. the key id must be one that policy declares for the signing subject, and the
   signature must verify against exactly those keys (`D-IMPL-363` E5);
3. the signed claims must name this request's gate event
   (``{tenant}/{request_id}/{gate}``), this tenant, the gate's state hash the
   approver saw, the approver, and the approving verdict;
4. the artifact's own fields must agree with the claims, and ``acted_at`` must be
   the signer's ``issued_at``.

Holding ``ArtifactErase`` lets a requester FILE an approval artifact; it does
not let them produce a signature the pinned policy accepts. That is what closes
the forgery the re-review measured (probe D).

Disclosed: verification is only as strong as the HITL policy's key custody. A
party who can register a HITL policy in the Control Plane, or who holds an
approver's private key, can approve; both are outside the erasure surface.
"""

from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

from ccf.controlplane.state import state_key
from ccf.erasure.contracts import ErasureApproval
from ccf.hitl.identity_binding import AttestationInvalid, HitlActionClaims, verify_hitl_action
from ccf.hitl.principal import ApproverIdentity
from ccf.hitl.transport import HitlPolicy
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    IdentityProvider,
    JsonWebKey,
    KeyUnavailable,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "APPROVING_VERDICT",
    "PinnedPolicySource",
    "ErasureApprovalInvalid",
    "reference_approval_verifier",
    "verify_erasure_approval",
]

#: The signed HITL action that approves (the gate's ``approve``).
APPROVING_VERDICT: Final[str] = "approve"


@runtime_checkable
class PinnedPolicySource(Protocol):
    """What the approval check reads from the Control Plane: one EXACT version.

    Every :class:`~ccf.controlplane.registry.ControlPlaneRegistry` satisfies it.
    Narrow on purpose — the check never resolves "latest".
    """

    def resolve(self, key: str, version: str) -> object:
        """Return the artifact registered as exactly ``(key, version)``."""
        ...


class ErasureApprovalInvalid(ValueError):
    """An erasure approval that is not a verified, approving, signed HITL action for this request.

    ``reason_code`` names which judgment refused it: ``approval-unsigned`` (no
    attestation), ``approval-policy-unresolvable`` (the pinned HITL policy is
    absent or not a ``HitlPolicy``), ``approval-signature-invalid`` (the key is
    not declared for the subject, or the signature does not verify), or
    ``approval-claims-mismatch`` (a signed claim or an artifact field names
    another request, gate, tenant, state, approver, instant or verdict).
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


def verify_erasure_approval(
    approval: ErasureApproval,
    *,
    tenant_id: str,
    request_id: str,
    approver: ApproverIdentity,
    control_plane: PinnedPolicySource,
    identity_provider: IdentityProvider,
) -> HitlActionClaims:
    """Return the verified signed claims, or raise :class:`ErasureApprovalInvalid`.

    Raises:
        ErasureApprovalInvalid: any of the module docstring's four judgments.
    """
    signed = approval.attestation
    key, at, version = approval.hitl_policy_ref.rpartition("@")
    if not at or not key or not version:
        raise ErasureApprovalInvalid(
            f"the approval pins no HITL policy version ({approval.hitl_policy_ref!r})",
            reason_code="approval-policy-unresolvable",
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
    return verified
