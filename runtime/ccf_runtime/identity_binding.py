"""Auth-context-derived principal binding (D-IMPL-21 reference impl #1).

SDK-defined (CLAUDE.md §8.2; D-IMPL-66(a)). D-IMPL-21 rules that HITL
identity binding is pluggable; this module is the first reference
implementation — a *development-grade* derivation that binds the
:class:`~ccf.hitl.principal.ApproverIdentity` to the deployment's verified
auth context: ``subject_id`` is the verified ``TokenGrant.client_id`` from
the D-26 bearer machinery, and **the caller cannot supply a subject id** —
no such parameter exists on the function. The subject is what the
deployment verified, never what the caller typed (T-07.1-05).

Everything else the binding carries — identity-provider reference,
authentication method, assurance level, session reference — is the
deployment's statement carried verbatim, with no defaults (CINV-01: the
SDK enumerates no deployment vocabulary). The underlying contract
validators are not laundered: a naive ``action_time`` or malformed
content hash surfaces as the contract's own validation error.

The companion reference implementation (#2) is the JWS-signed binding in
:mod:`ccf.hitl.identity_binding`.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = ["principal_from_token_grant"]


def principal_from_token_grant(
    *,
    grant: TokenGrant,
    identity_provider_ref: str,
    method: str,
    assurance_level: str,
    session_ref: str,
    action_time: datetime,
    product_content_hash: str,
) -> HumanPrincipalBinding:
    """Derive a :class:`HumanPrincipalBinding` from a verified auth context.

    The approver's subject id is ``grant.client_id`` — the identity the
    deployment's token source verified — and there is deliberately no
    parameter through which a caller could substitute a different subject.

    Args:
        grant: The verified grant from the deployment's D-26 token source.
        identity_provider_ref: Which provider authenticated the subject —
            deployment vocabulary, no default.
        method: The authentication method, as the deployment states it.
        assurance_level: The deployment's assurance statement, verbatim.
        session_ref: The deployment's session reference.
        action_time: The injected (aware) action time — never a wall clock
            read inside this function (D-IMPL-38 discipline).
        product_content_hash: The D-IMPL-26 content hash of the Context
            Product the approver saw.

    Returns:
        The typed binding, validated by the contract's own gates.
    """
    return HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=grant.client_id,
            identity_provider_ref=identity_provider_ref,
        ),
        authentication=AuthenticationContext(
            method=method,
            assurance_level=assurance_level,
            session_ref=session_ref,
        ),
        action_time=action_time,
        product_content_hash=product_content_hash,
    )
