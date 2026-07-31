"""Minimal bearer-auth hook for the HTTP front door (D-IMPL-66(a)).

SDK-defined (CLAUDE.md §8.3). This is a *hook* over the deployment's
D-26 :class:`~ccf_runtime.mcp.auth.TokenSourceProtocol` — never a vendor
auth integration. There is no OIDC client, no SAML assertion parser, and
no token issuance here: an enterprise identity provider is a conforming
implementation of the token-source seam the deployment supplies, not SDK
code. The hook answers exactly one question — does this request carry a
bearer token the deployment's source recognises, and what grant does it
carry — reusing the D-26 constant-time verification path unchanged
(T-07.1-06: no new comparison code exists in this module).

Binding the hook is a composition decision at
:func:`~ccf_runtime.http_api.app.create_app`; the unbound default is the
recorded T-07-24 unauthenticated posture, byte-for-byte unchanged.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf_runtime.mcp.auth import TokenGrant, TokenSourceProtocol

__ccf_mode__ = "algorithmic"

__all__ = ["BearerTokenAuth", "HttpAuthProtocol"]


@runtime_checkable
class HttpAuthProtocol(Protocol):
    """How the HTTP app asks whether a request is authenticated.

    Protocol rather than a base class (CLAUDE.md §11): what "authenticated"
    means is the deployment's statement; the app has business only with
    the signature.
    """

    def grant_for_request(
        self, *, authorization_header: str | None
    ) -> TokenGrant | None:
        """Return the request's grant, or ``None`` if it must be refused."""
        ...


class BearerTokenAuth:
    """Reference ``HttpAuthProtocol`` over a D-26 token source.

    Parses ``Authorization: Bearer <token>`` — the scheme comparison is
    case-insensitive per RFC 9110 §11.1; a missing header, another scheme,
    or an empty credential yields ``None`` — and delegates recognition to
    the deployment's ``token_source``, whose constant-time comparison is
    reused unchanged (T-07.1-06).

    Args:
        token_source: The deployment's token source. No default: which
            tokens exist is a deployment value (CINV-01).
    """

    def __init__(self, *, token_source: TokenSourceProtocol) -> None:
        self._token_source = token_source

    def grant_for_request(
        self, *, authorization_header: str | None
    ) -> TokenGrant | None:
        """Return the header's grant, or ``None`` to refuse the request."""
        if authorization_header is None:
            return None
        scheme, _, credential = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            return None
        return self._token_source.grant_for(token=credential.strip())
