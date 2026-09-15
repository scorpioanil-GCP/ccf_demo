"""Bearer-token verification for the SDK's MCP servers (D-26).

SDK-defined (CLAUDE.md §7.4). §7.4 says the artifact server "sits inside the
tenant trust boundary but is authenticated". D-26 rules that v0 backs that
sentence with mechanism rather than letting it stand as an unbacked claim, so
this module ships a real ``TokenVerifier`` — the Protocol ``FastMCP`` accepts —
over a pluggable token source.

**What this verifies.** That a presented bearer token is one the deployment's
token source recognises, and what client identity and scopes it carries. That
is authentication and coarse authorization, and it is the whole claim.

**What this cannot do, and what a deployment must supply.** It issues no
tokens, rotates none, revokes none, and holds no key material of its own. There
is no OAuth authorization server here, no JWT signature verification, no
introspection endpoint, and no HSM or PKI custody — those remain out of scope
per CLAUDE.md §13, exactly as D-13 scopes key custody for A2A. A production
deployment supplies a ``TokenSourceProtocol`` implementation backed by whatever
its identity infrastructure actually is; :class:`FileTokenSource` is a
**development** implementation and is named so that nobody has to infer it.

**Where the tokens are.** In a file the deployment points at, never in this
repository and never in this module. Token values, client identifiers, scope
vocabulary, and the file's location are all deployment values (CINV-01); the
SDK holds none of them and ships no default token.

Comparison is constant-time (``hmac.compare_digest``) rather than a dict
lookup. A dict lookup on a secret is a timing oracle over the token space, and
the cost of not having one here is a linear scan of a development token file.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import hmac
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from mcp.server.auth.provider import AccessToken

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "FileTokenSource",
    "SourceBackedTokenVerifier",
    "StaticTokenSource",
    "TokenGrant",
    "TokenSourceProtocol",
]


class TokenGrant(CCFContract):
    """What a recognised token entitles its bearer to.

    Attributes:
        client_id: Who the token identifies. Deployment vocabulary — the SDK
            enumerates no client identifiers.
        scopes: The scopes the bearer holds. ``FastMCP`` intersects these with
            the ``required_scopes`` the deployment configured on the server, so
            the two halves of the authorization decision stay with the
            deployment on both sides.
    """

    client_id: str
    scopes: tuple[str, ...]


@runtime_checkable
class TokenSourceProtocol(Protocol):
    """Where a deployment's recognised tokens come from.

    Protocol rather than a base class (CLAUDE.md §11): a deployment's identity
    substrate is its own — a secrets manager, an introspection endpoint, a
    mounted file — and the SDK has business only with the signature.
    """

    def grant_for(self, *, token: str) -> TokenGrant | None:
        """Return the grant ``token`` carries, or ``None`` if unrecognised.

        ``None`` rather than an exception: an unrecognised token is the
        expected case on any exposed endpoint, and routing the ordinary case
        through the exception path makes the log of real failures useless.
        """
        ...


class FileTokenSource:
    """Recognised tokens read from a JSON file — a *development* source.

    The file maps each token to its grant::

        {"<token>": {"client_id": "...", "scopes": ["..."]}}

    Read on every lookup rather than cached at construction, so a deployment
    revoking a token by editing the file does not have to restart the server —
    and so a test can add one between calls. The cost is a small read per
    request, which is the correct trade for a development substrate and the
    wrong one for a production identity provider, which is why this class says
    "development" in its first line.

    A missing file is an empty source: every token is refused. That is the
    fail-closed direction, and it is the one a misconfigured deployment should
    land in.

    Args:
        path: Where the token file lives. A deployment value; there is no
            default, because a default location for a secret is a place an
            attacker knows to look.
    """

    def __init__(self, *, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """The file this source reads."""
        return self._path

    def _load(self) -> dict[str, TokenGrant]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        loaded: dict[str, dict[str, object]] = json.loads(raw)
        return {
            token: TokenGrant.model_validate(grant)
            for token, grant in loaded.items()
        }

    def grant_for(self, *, token: str) -> TokenGrant | None:
        """Return ``token``'s grant, comparing in constant time."""
        for candidate, grant in self._load().items():
            if hmac.compare_digest(candidate, token):
                return grant
        return None


class SourceBackedTokenVerifier:
    """``TokenVerifier`` over a :class:`TokenSourceProtocol` (D-26).

    Structurally conforms to ``mcp.server.auth.provider.TokenVerifier``, which
    is what ``FastMCP`` asks for. The indirection through the source is the
    point: the verification *mechanism* ships with the SDK and the recognised
    tokens are the deployment's, so no token value ever has to exist in this
    repository for the authenticated path to be real.

    Args:
        source: The deployment's token source.
    """

    def __init__(self, *, source: TokenSourceProtocol) -> None:
        self._source = source

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return the access token for ``token``, or ``None`` to refuse.

        Async because the Protocol is: a real source is a network call, and a
        synchronous signature would force every such implementation to block
        the server's event loop.
        """
        grant = self._source.grant_for(token=token)
        if grant is None:
            return None
        return AccessToken(
            token=token,
            client_id=grant.client_id,
            scopes=list(grant.scopes),
        )


class StaticTokenSource:
    """Recognised tokens held in memory — the paved road's per-boot source.

    `D-IMPL-343` (design §5.4). :class:`FileTokenSource` reads a JSON file so
    a deployment can revoke by editing it; the standard product door needs the
    other shape — ONE credential minted or read at boot, held for the life of
    the process, written to no file — and every shipped door built that shape
    by writing a one-entry token file into a temporary directory and deleting
    it on exit. This is that shape without the file.

    Comparison is constant-time, as :meth:`FileTokenSource.grant_for` is, and
    for the same reason. A development substrate, like its sibling: a
    production identity provider conforms to :class:`TokenSourceProtocol` on
    its own terms.

    Args:
        grants: Each recognised token and its grant. A deployment value; no
            default, because a default credential is a credential an attacker
            knows.
    """

    def __init__(self, *, grants: Mapping[str, TokenGrant]) -> None:
        self._grants = dict(grants)

    def grant_for(self, *, token: str) -> TokenGrant | None:
        """Return ``token``'s grant, comparing in constant time."""
        for candidate, grant in self._grants.items():
            if hmac.compare_digest(candidate, token):
                return grant
        return None
