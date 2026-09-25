"""The door-minted principal binding (D-IMPL-21 reference impl #1; D-IMPL-353 §2 P6).

SDK-defined (CLAUDE.md §8.2; D-IMPL-66(a)). D-IMPL-21 rules that HITL
identity binding is pluggable; this module is the first reference
implementation — a *development-grade* derivation that binds the
:class:`~ccf.hitl.principal.ApproverIdentity` to what the deployment
verified. Its predecessor, ``principal_from_token_grant``, fixed the subject
to the verified ``TokenGrant.client_id`` and took every other axis of the
binding — identity-provider reference, method, assurance level, session
reference, action time — from its caller; the doors passed those through
from the request body, which made a step-up-MFA assurance a thing the
approver typed into their own audit record (the close panel's ``P6``).

**What is minted from what, now, and nothing else:**

* the subject is ``authorized.principal`` — the principal the authorizer
  decided *allowed* for, carried on the capability
  (:class:`~ccf.authz.capability.Authorized`); there is no parameter
  through which a caller could substitute one (T-07.1-05, kept);
* the identity-provider reference and the authentication context are the
  verified credential's :class:`~ccf.hitl.principal.AuthenticationClaims`,
  copied verbatim; there is no parameter for any of the four axes, so a
  caller-typed value is unrepresentable rather than refused;
* the action time is the door's injected clock, passed in — never a wall
  clock read here (D-IMPL-38 discipline);
* the product hash is the one thing the human states: what they saw.

The two readers of the claims — :func:`authentication_of_grant` off the
HTTP door's verified :class:`~ccf_runtime.mcp.auth.TokenGrant`, and
:func:`authentication_of_token` off the MCP library's ``AccessToken`` — are
the single reads, in the shape of :func:`ccf_runtime.mcp.auth.granted_tenants`:
an absent or malformed claim reads as ``None``, and ``None`` is refused by
:func:`attested_authentication` before any binding exists. Unparseable is not
permissive, and an unattested credential mints no approval.

The underlying contract validators are not laundered: a naive
``action_time`` or malformed content hash surfaces as the contract's own
validation error. The companion reference implementation (#2) is the
JWS-signed binding in :mod:`ccf.hitl.identity_binding`.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from mcp.server.auth.provider import AccessToken
from pydantic import ValidationError

from ccf.hitl.principal import (
    AUTHENTICATION_CLAIM,
    ApproverIdentity,
    AuthenticationClaims,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.authz.capability import Authorized, HitlSubmit
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERROR_AUTHENTICATION_UNATTESTED",
    "AuthenticationUnattested",
    "attested_authentication",
    "authentication_of_grant",
    "authentication_of_token",
    "principal_from_authorized",
]

#: The error code both HITL doors carry when the verified credential states
#: no authentication context (D-IMPL-353 §2 P6). Lives beside the mechanism
#: that refuses rather than in :mod:`ccf_runtime.http_api.errors` because it
#: is raised here, once, and mapped by each door into its own shell — the
#: D-16 door-mapping pattern.
ERROR_AUTHENTICATION_UNATTESTED: Final[str] = "authentication-unattested"


class AuthenticationUnattested(PermissionError):
    """The verified credential states nothing about how its bearer authenticated.

    A *deployment* posture rather than a caller fault: the token source
    decides what a grant carries, and a caller has no way to add a claim to
    its own credential. Refused rather than defaulted because the only other
    thing a door could do is invent an assurance level — which is the
    caller-typed assurance defect with the server holding the pen.
    """


def attested_authentication(
    claims: AuthenticationClaims | None,
) -> AuthenticationClaims:
    """The claims, or refuse — the one place ``None`` becomes a refusal.

    Both doors call this on the value their reader returned, so the
    refusal's shape and prose are one thing that cannot drift between them.

    Raises:
        AuthenticationUnattested: the credential carried no claims.
    """
    if claims is None:
        raise AuthenticationUnattested(
            "the verified credential states no authentication context, so no"
            " principal binding can be minted from it: the identity-provider"
            " reference, method, assurance level and session reference on an"
            " approval are the verifier's statements and never the caller's."
            " Mint credentials that carry `authentication` claims"
            " (D-IMPL-353 §2 P6; D-IMPL-21)"
        )
    return claims


def authentication_of_grant(grant: TokenGrant) -> AuthenticationClaims | None:
    """The claims the HTTP door's verified grant carries — the single read."""
    return grant.authentication


def authentication_of_token(token: AccessToken) -> AuthenticationClaims | None:
    """The claims ``token`` was verified as carrying — the single read.

    Mirrors :func:`ccf_runtime.mcp.auth.granted_tenants`: a token carrying
    no claim, an absent claim, or a claim of the wrong shape all yield
    ``None``, which :func:`attested_authentication` refuses. Nothing on the
    wire can author this claim — claims reach a handler only from the
    deployment's own token verifier.
    """
    claimed = (token.claims or {}).get(AUTHENTICATION_CLAIM)
    if not isinstance(claimed, dict):
        return None
    try:
        return AuthenticationClaims.model_validate(claimed)
    except ValidationError:
        return None


def principal_from_authorized(
    authorized: Authorized[HitlSubmit],
    *,
    authentication: AuthenticationClaims,
    action_time: datetime,
    product_content_hash: str,
) -> HumanPrincipalBinding:
    """Mint the binding for one human action from what the door verified.

    Args:
        authorized: The capability the gate minted for this submission. Its
            ``principal`` is the subject; nothing else about the subject is
            representable here.
        authentication: The verified credential's claims, from
            :func:`attested_authentication`. Copied verbatim.
        action_time: The door's injected (aware) clock reading — never a
            wall clock read inside this function.
        product_content_hash: The D-IMPL-26 content hash of the Context
            Product the approver saw — the one value the human states.

    Returns:
        The typed binding, validated by the contract's own gates.
    """
    return HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=authorized.principal,
            identity_provider_ref=authentication.identity_provider_ref,
        ),
        authentication=AuthenticationContext(
            method=authentication.method,
            assurance_level=authentication.assurance_level,
            session_ref=authentication.session_ref,
        ),
        action_time=action_time,
        product_content_hash=product_content_hash,
    )
