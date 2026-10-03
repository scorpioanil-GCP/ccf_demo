"""The human-principal binding every HITL action carries (D-IMPL-21).

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so). D-IMPL-21 rules that HITL identity is pluggable via the same
``IdentityProvider`` Protocol family as D-IMPL-15 — the approver's identity
is a *reference into that existing machinery*
(:class:`ApproverIdentity.identity_provider_ref`), never a new identity
mechanism — with a distinct human-principal binding shape: every HITL
action record carries a typed :class:`HumanPrincipalBinding` holding the
approver identity, the authentication context, the action time, and the
D-IMPL-26 content hash of the Context Product the approver saw.

**This is the actor-doctrine hook discharged.** The audit plane's
``AuditEvent.actor`` field states that the SDK does not synthesize an
identity and names identity binding as D-IMPL-21's problem
(:mod:`ccf.controlplane.audit`, the actor doctrine): this contract is that
binding. No HITL action type is constructible without one — the HITL
primitives (07-07/07-08) take the binding as a required field, so an
unattributed human action is unrepresentable through the typed surface
rather than merely discouraged.

**Where a binding's values come from, and where they may not (D-IMPL-353
§2 P6).** At every served door the binding is *minted by the door*, never
described by the caller: the subject is the capability's principal
(:class:`~ccf.authz.capability.Authorized`), the identity-provider
reference and the authentication context are the verified credential's
:class:`AuthenticationClaims` carried verbatim, and the action time is the
door's injected clock. The request contract at the doors
(:class:`~ccf.hitl.transport.HitlActionRequest`) carries none of those
fields, so a caller-typed step-up-MFA claim is unrepresentable, not refused.
:class:`AuthenticationClaims` is the shape the deployment's credential
verifier states those facts in; it travels on the verified grant and, on
the MCP transports, in the token's claims under :data:`AUTHENTICATION_CLAIM`.

**The action time is injected, never read from a wall clock inside the
type**, in the registry's injected-clock discipline: the caller that
observed the action supplies the time, and the canonical serializer refuses
a naive datetime (D-IMPL-38), so an ambiguous timestamp cannot reach the
replay record.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import string
from datetime import datetime
from typing import Final

from pydantic import Field, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

__ccf_mode__ = "algorithmic"

__all__ = [
    "AUTHENTICATION_CLAIM",
    "ApproverIdentity",
    "AuthenticationClaims",
    "AuthenticationContext",
    "HumanPrincipalBinding",
    "validate_content_hash",
]

#: The length of a lowercase sha256 hex digest — the shape
#: :func:`ccf.contracts.canonical.content_hash` produces (D-IMPL-26).
_SHA256_HEX_LENGTH = 64

#: Where a verified caller's :class:`AuthenticationClaims` travel inside the
#: MCP library's ``AccessToken.claims`` (D-IMPL-353 §2 P6) — the sibling of
#: :data:`ccf_runtime.mcp.auth.TENANT_CLAIM`. A wire-format constant of the
#: SDK, not a deployment value: it names no provider, method or level.
AUTHENTICATION_CLAIM: Final[str] = "ccf.authentication"


def validate_content_hash(value: str) -> str:
    """Return ``value`` if it is a lowercase sha256 hex digest, else raise.

    The one reading of *what a product identity looks like*, shared by
    :class:`HumanPrincipalBinding` and by the door-facing
    :class:`~ccf.hitl.transport.HitlActionRequest`, so the request a human
    sends and the binding the door mints from it cannot disagree about the
    shape (D-IMPL-26; D-IMPL-21).

    Raises:
        ValueError: ``value`` is not the shape
            :func:`ccf.contracts.canonical.content_hash` produces.
    """
    if len(value) != _SHA256_HEX_LENGTH or any(
        character not in string.hexdigits[:16] for character in value
    ):
        raise ValueError(
            "product_content_hash must be the lowercase sha256 content hash"
            " of the Context Product the approver saw"
            " (ccf.contracts.canonical.content_hash; D-IMPL-26, D-IMPL-21)"
            " — a decision replays against what the human actually reviewed,"
            " not a paraphrase of it"
        )
    return value


class ApproverIdentity(CCFContract):
    """Who approved: subject id plus identity-provider reference (D-IMPL-21).

    SDK-defined. ``identity_provider_ref`` names the provider that
    authenticated the subject — the pluggable ``IdentityProvider`` family of
    D-IMPL-15 (OIDC/SAML enterprise providers being the realistic
    human-principal path, vs. mTLS+JWS for workloads). The SDK enumerates no
    provider vocabulary: which providers exist is deployment configuration,
    and this contract only requires that the binding *names* one, so replay
    can answer "who, per which authority" (D-23 multi-principal).
    """

    subject_id: str
    identity_provider_ref: str


class AuthenticationContext(CCFContract):
    """How the approver was authenticated (D-IMPL-21).

    SDK-defined. Method, assurance level, and session reference are the
    provider's statements carried verbatim — deployment vocabulary the SDK
    does not enumerate (mechanism, not values), present so the replay record
    can distinguish a strongly-authenticated approval from a weakly-
    authenticated one without interpreting either.
    """

    method: str
    assurance_level: str
    session_ref: str


class AuthenticationClaims(CCFContract):
    """What the credential verifier states about HOW a bearer authenticated
    (D-IMPL-353 §2 P6; D-IMPL-21).

    SDK-defined. The four provider statements a
    :class:`HumanPrincipalBinding` carries besides the subject — which
    provider, by what method, at what assurance, in which session — as the
    deployment's token source attested them when it recognized the
    credential. **This is the doors' only source for those four values.** A
    request body or tool argument that named an assurance level would make
    step-up MFA a thing the caller types into its own audit record, which
    is the finding this contract closes; so the door copies these verbatim
    and the request contracts have no such field.

    Every axis is required and none has a default (CINV-01: the SDK
    enumerates no provider vocabulary, and a verifier that has not stated an
    axis has not attested the authentication — the door refuses rather than
    fills the blank; see
    :func:`ccf_runtime.identity_binding.attested_authentication`).
    """

    identity_provider_ref: str
    method: str
    assurance_level: str
    session_ref: str


class HumanPrincipalBinding(CCFContract):
    """One human action's complete principal binding (D-IMPL-21; CLAUDE.md §8.2).

    SDK-defined. The four D-IMPL-21 fields plus the verdict, all required:
    approver identity, authentication context, action time (injected), the
    content hash of the Context Product the approver saw, and WHAT THEY
    DECIDED. Audit-by-construction holds
    regardless of identity provider: no HITL action lands without a binding,
    because the HITL action contracts require this type as a field —
    omission is a validation error at the boundary, never a null in the
    replay record.

    At the served doors this is minted by
    :func:`ccf_runtime.identity_binding.principal_from_authorized` from the
    capability, the verified :class:`AuthenticationClaims` and the door's
    clock — the caller supplies the product hash and the verdict, and nothing
    about their own identity (D-IMPL-353 §2 P6; SEC-005). The sentence that
    stood here until 2026-10-03 said "only the product hash", which this
    contract's own `verdict` field made false the moment it was added, and that
    description is PUBLISHED in `openapi.json`.
    """

    approver: ApproverIdentity
    authentication: AuthenticationContext
    action_time: datetime
    product_content_hash: str

    #: WHAT THE APPROVER DECIDED, and a SIGNED claim (`SEC-005`; Dave,
    #: 2026-10-03: *"The verdict joins the signed claim set. A signature that
    #: still verifies after the action is swapped authorizes a decision the
    #: approver never made."*). Until it was a field here the signed payload —
    #: ``canonical_bytes(binding)`` — covered who acted, how they
    #: authenticated, when, and what they saw, but never the decision: that
    #: travelled beside the binding as ``HitlActionSubmission.action`` and
    #: again as ``ApprovalGate.resolve``'s own parameter, so ONE valid
    #: signature authorized either verdict. Measured before this field
    #: existed: a binding signed to reject was presented as an approval,
    #: admitted, and the workflow completed at the approving terminal.
    #:
    #: A GENERATION BOUNDARY (`D-IMPL-243` amendment 1), not hash-transparent.
    #: It is rendered into every binding's hash, which is the point — a
    #: signature that did not cover the verdict belongs to an earlier
    #: generation of this contract, and `generation_mismatch` names it rather
    #: than letting it verify silently.
    #:
    #: The vocabulary is the submission's, deliberately not re-declared here:
    #: this value is compared against ``HitlActionSubmission.action`` by
    #: ``ccf.hitl.transport.enforce_signed_binding``, and a second enumeration
    #: would be a second place for the two to drift apart.
    verdict: str = Field(json_schema_extra={HASH_TRANSPARENT_KEY: False})

    @field_validator("product_content_hash")
    @classmethod
    def _product_hash_is_a_content_hash(cls, value: str) -> str:
        return validate_content_hash(value)
