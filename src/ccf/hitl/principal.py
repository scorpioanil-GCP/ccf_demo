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

from pydantic import field_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ApproverIdentity",
    "AuthenticationContext",
    "HumanPrincipalBinding",
]

#: The length of a lowercase sha256 hex digest — the shape
#: :func:`ccf.contracts.canonical.content_hash` produces (D-IMPL-26).
_SHA256_HEX_LENGTH = 64


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


class HumanPrincipalBinding(CCFContract):
    """One human action's complete principal binding (D-IMPL-21; CLAUDE.md §8.2).

    SDK-defined. The four D-IMPL-21 fields, all required: approver identity,
    authentication context, action time (injected), and the content hash of
    the Context Product the approver saw. Audit-by-construction holds
    regardless of identity provider: no HITL action lands without a binding,
    because the HITL action contracts require this type as a field —
    omission is a validation error at the boundary, never a null in the
    replay record.
    """

    approver: ApproverIdentity
    authentication: AuthenticationContext
    action_time: datetime
    product_content_hash: str

    @field_validator("product_content_hash")
    @classmethod
    def _product_hash_is_a_content_hash(cls, value: str) -> str:
        if len(value) != _SHA256_HEX_LENGTH or any(
            character not in string.hexdigits[:16] for character in value
        ):
            raise ValueError(
                "product_content_hash must be the lowercase sha256 content"
                " hash of the Context Product the approver saw"
                " (ccf.contracts.canonical.content_hash; D-IMPL-26,"
                " D-IMPL-21) — a decision replays against what the human"
                " actually reviewed, not a paraphrase of it"
            )
        return value
