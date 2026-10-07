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
Both operands are compared as UTF-8 **bytes** (:func:`_tokens_match`), never as
``str``: ``hmac.compare_digest`` refuses a non-ASCII ``str`` with ``TypeError``,
which turned a presented ``Bearer ü`` into a 500 on every door and one
non-ASCII token in a deployment's file into a whole-door outage (LOW-01,
D-IMPL-372). Over bytes, a non-ASCII token is simply a token that does or does
not match, and :meth:`TokenSourceProtocol.grant_for`'s ``None``-not-an-exception
contract holds for every input.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import hmac
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Protocol, runtime_checkable

from mcp.server.auth.provider import AccessToken

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.hitl.principal import AUTHENTICATION_CLAIM, AuthenticationClaims

__ccf_mode__ = "algorithmic"

__all__ = [
    "AMBIENT_STDIO_CLAIM",
    "FileTokenSource",
    "PRODUCT_CLAIM",
    "SourceBackedTokenVerifier",
    "StaticTokenSource",
    "TENANT_CLAIM",
    "TokenGrant",
    "TokenSourceProtocol",
    "authentication_claims",
    "bounded_echo",
    "granted_products",
    "granted_tenants",
    "is_ambient_stdio",
    "product_claims",
    "tenant_claims",
]

#: Where a verified caller's tenants travel inside ``AccessToken.claims``
#: (``SEC-018``). A wire-format constant of the SDK, in the same class as the
#: surface identifiers in :mod:`ccf_runtime.authz.delivery_boundary` — not a
#: deployment value, and it names no tenant.
TENANT_CLAIM: Final[str] = "ccf.tenants"

#: Where a verified caller's declared product roster travels inside
#: ``AccessToken.claims`` (``SEC-017``; ``D-IMPL-374`` (2)). A wire-format
#: constant beside :data:`TENANT_CLAIM`, naming no product. **Absent means no
#: roster was declared** — tenant-wide reach — which is why
#: :func:`product_claims` writes nothing for a grant that declares none.
PRODUCT_CLAIM: Final[str] = "ccf.products"

#: Marks an identity that was *stated* by the process that owns the transport
#: rather than *verified* from a presented credential — MCP stdio's case, where
#: the library installs no authentication middleware because there is no HTTP
#: app to install it on. See
#: :func:`ccf_runtime.mcp.tenancy.ambient_stdio_identity`.
AMBIENT_STDIO_CLAIM: Final[str] = "ccf.ambient-stdio"


class TokenGrant(CCFContract):
    """What a recognised token entitles its bearer to.

    **The tenant axis exists because it was missing** (``SEC-018``). This
    contract carried ``client_id`` and ``scopes`` and nothing else, so every
    surface that consulted it could answer *who is this* and none could answer
    *whose data is this*. A bearer minted for one tenant reached another
    tenant's artifacts, queue and products — not by defeating authentication,
    but because authentication was answering a different question.

    Attributes:
        client_id: Who the token identifies. Deployment vocabulary — the SDK
            enumerates no client identifiers.
        scopes: The scopes the bearer holds. ``FastMCP`` intersects these with
            the ``required_scopes`` the deployment configured on the server, so
            the two halves of the authorization decision stay with the
            deployment on both sides.
        tenants: The tenants this bearer may reach. **A set rather than one
            name**, and the shape is argued rather than assumed: a shipped
            example door serves exactly one tenant and is the one-element case,
            while the artifact store and the HITL queue are deployment-wide
            surfaces a genuine operator credential spans. The one-element case
            is expressible in a set; the operator case is not expressible in a
            scalar without a wildcard, and a wildcard is a fail-open value the
            SDK would be holding on the deployment's behalf (CINV-01).

            **Empty means no tenant, never every tenant.** The default is
            empty, so a deployment that forgets to scope a credential mints one
            that opens nothing. That direction is loud; the other is silent and
            total. Unordered because membership is the only question ever asked
            of it — there is no first tenant, and
            :func:`~ccf.contracts.canonical.canonical_bytes` renders a
            ``frozenset`` sorted, so determinism is not traded for it.

            Tenant identifiers are deployment vocabulary; the SDK enumerates
            none and ships no default (CINV-01).
        products: The within-tenant product roster (``SEC-017``;
            ``D-IMPL-374`` (2)) — the Context Product CLASS names (schema
            names) this bearer may reach. ``None`` — the default — declares no
            roster and reaches tenant-wide, which is the behavior every grant
            minted before the field existed had; **declaring a roster for a
            principal that must not reach every product is the deployment's
            obligation**, and the SDK ships no default roster (CINV-01). In a
            token file, ``"products": null`` (or the key omitted) means
            tenant-wide and ``"products": []`` means NO product. A declared
            roster is held, before the authorizer is asked, on every surface
            that knows a class at the call: the MCP Experience door's
            ``context_product`` resource, ``get_context``, ``get_lineage``,
            ``invoke_agent`` (the agent's ``consumes ∪ emits``),
            ``list_agents`` (filtered) and ``get_replay_record`` (the declared
            ``replay_record_product_class``); the MCP egress door's three
            product surfaces; and the HTTP door's product route and replay
            routes. Surfaces that know no class at the call — artifact
            store, HITL — are not bound by it.
    """

    client_id: str
    scopes: tuple[str, ...]
    #: ``True`` — hash-transparent, and the sentinel really does mean the old
    #: contract (``D-IMPL-243``: *"silence equals yesterday"*). An EMPTY set
    #: is "this token claimed no tenant", which is exactly what was true of
    #: every grant minted before the field existed. It is also the
    #: RESTRICTIVE reading everywhere it is consumed — empty means no tenant,
    #: never every tenant — so a forgotten scope fails loudly rather than
    #: opening a door. A non-empty value is a real claim and is rendered.
    tenants: frozenset[str] = Field(
        default=frozenset(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: What the token source verified about HOW the bearer authenticated
    #: (``D-IMPL-353`` §2 P6) — the four provider statements a
    #: :class:`~ccf.hitl.principal.HumanPrincipalBinding` carries besides the
    #: subject. **The HITL doors' only source for the approver's assurance**:
    #: they read it from the verified credential, never from a request body,
    #: so step-up MFA is not a thing a caller types into its own audit record.
    #: ``None`` — the default — is a credential whose verifier said nothing,
    #: and a door refuses to mint a binding from it rather than fill the blank.
    #: Hash-transparent at the sentinel: every grant minted before the field
    #: existed said nothing, and its canonical bytes do not move.
    authentication: AuthenticationClaims | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: ``SEC-017``; ``D-IMPL-374`` (2). ``None`` is "no roster declared",
    #: exactly what every grant before the field said, so it is
    #: hash-transparent at the sentinel and a pre-existing grant's canonical
    #: bytes do not move. A set — empty included — is a real declaration.
    products: frozenset[str] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


def authentication_claims(grant: TokenGrant) -> Mapping[str, Any]:
    """Render ``grant``'s authentication statement for :attr:`AccessToken.claims`.

    Empty when the grant states nothing, so a silent credential carries no
    claim rather than an empty one — the doors distinguish *unattested* from
    *attested*, and an empty mapping would blur that into a third state.
    """
    if grant.authentication is None:
        return {}
    return {AUTHENTICATION_CLAIM: grant.authentication.model_dump(mode="json")}


def tenant_claims(grant: TokenGrant) -> Mapping[str, Any]:
    """Render ``grant``'s tenants for :attr:`AccessToken.claims`.

    Sorted on the way out. The claim is a JSON-shaped mapping the library
    carries verbatim, and a set has no wire form — rendering it in a stable
    order keeps two verifications of one token byte-identical, which matters
    the moment a claim is logged or hashed.
    """
    return {TENANT_CLAIM: sorted(grant.tenants)}


def product_claims(grant: TokenGrant) -> Mapping[str, Any]:
    """Render ``grant``'s product roster for :attr:`AccessToken.claims`.

    ``SEC-017``; ``D-IMPL-374`` (2). Empty when the grant declares no roster,
    so *no roster* and *an empty roster* stay two states on the wire: the
    first is tenant-wide, the second reaches no product. Sorted for the reason
    :func:`tenant_claims` gives.
    """
    if grant.products is None:
        return {}
    return {PRODUCT_CLAIM: sorted(grant.products)}


def granted_products(token: AccessToken) -> frozenset[str] | None:
    """The product roster ``token`` was verified as carrying, or ``None``.

    ``SEC-017``; ``D-IMPL-374`` (2) — the single read, as
    :func:`granted_tenants` is for tenants. ``None`` only when the claim is
    ABSENT, which is a grant that declared no roster. A claim that is present
    but of the wrong shape yields the empty roster, never ``None``:
    unparseable is not permissive, and an empty roster reaches no product.
    """
    claims = token.claims or {}
    if PRODUCT_CLAIM not in claims:
        return None
    claimed = claims[PRODUCT_CLAIM]
    if not isinstance(claimed, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(name for name in claimed if isinstance(name, str))


def granted_tenants(token: AccessToken) -> frozenset[str]:
    """The tenants ``token`` was verified as carrying — the single read.

    Every tenant decision in :mod:`ccf_runtime.mcp.tenancy` resolves here, so
    there is one answer to *whose data may this caller reach* rather than one
    per handler. A token carrying no claim, an absent claim, or a claim of the
    wrong shape all yield the empty set: unparseable is not permissive, and an
    empty set reaches nothing.
    """
    claimed = (token.claims or {}).get(TENANT_CLAIM)
    if not isinstance(claimed, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(name for name in claimed if isinstance(name, str))


def is_ambient_stdio(token: AccessToken) -> bool:
    """Whether ``token`` was stated by the stdio host rather than verified.

    ``True`` only for an identity :func:`~ccf_runtime.mcp.tenancy.
    ambient_stdio_identity` built. Nothing on the wire can set this claim,
    because claims reach a handler only from :meth:`
    SourceBackedTokenVerifier.verify_token`, which composes them from the
    deployment's own grant — and nothing on the wire can *clear* it either,
    which is the direction that would buy something.
    """
    return bool((token.claims or {}).get(AMBIENT_STDIO_CLAIM))


#: The most characters of any caller- or directory-supplied identifier a roster
#: refusal echoes — the cap :mod:`ccf.skills.wire_arguments` puts on an echoed
#: argument key (``_ECHOED_KEY_CHARACTERS``), so a refusal's text is bounded by
#: the SDK, never by the caller (``SEC-017`` fix round 1).
_ECHOED_CHARACTERS: Final[int] = 64


def bounded_echo(value: object) -> str:
    """``repr`` of ``value``'s first :data:`_ECHOED_CHARACTERS` characters.

    ``SEC-017``; ``D-IMPL-374`` (2). Every identifier a roster refusal names
    passes through here, so a refusal cannot carry an unbounded caller string.
    """
    text = str(value)
    if len(text) > _ECHOED_CHARACTERS:
        return repr(text[:_ECHOED_CHARACTERS]) + "…"
    return repr(text)


def _tokens_match(candidate: str, presented: str) -> bool:
    """Constant-time equality of two tokens, total over every ``str``.

    Encodes both operands as UTF-8 with ``surrogatepass`` so a lone surrogate
    (reachable from a JSON token file's ``\\udXXX`` escape) encodes rather than
    raises, and the encoding stays injective. This is the form the mcp
    library's own ``mcp.server.auth.middleware.client_auth`` uses for client
    secrets. LOW-01, D-IMPL-372; the contract is
    :meth:`TokenSourceProtocol.grant_for`'s.
    """
    return hmac.compare_digest(
        candidate.encode("utf-8", "surrogatepass"),
        presented.encode("utf-8", "surrogatepass"),
    )


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

        {"<token>": {"client_id": "...", "scopes": ["..."],
                     "tenants": ["..."]}}

    ``tenants`` omitted parses as the empty set, which reaches nothing
    (``SEC-018``) — a token file written before the tenant axis existed
    therefore fails closed rather than carrying its old reach forward.

    ``products`` is the opposite on purpose (``SEC-017``): omitted or
    ``null`` declares no roster and reaches tenant-wide, and ``[]`` reaches no
    product. Declaring it is the deployment's obligation.

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
            if _tokens_match(candidate, token):
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

        **The grant's tenants travel in ``claims``** (``SEC-018``).
        ``AccessToken`` has carried a ``claims`` mapping all along, so the
        tenant axis needed no change to ``mcp==1.28.1`` — the gap was never the
        transport. This is the *only* place the SDK writes that claim on the
        authenticated path, and :func:`granted_tenants` is the only place it is
        read, so there is exactly one flow: the deployment's token source, to
        the grant, to the claim, to the guard.

        A remote caller presents a token string and nothing else. It cannot
        author a claim, which is what makes the tenant read here trustworthy in
        a way a wire field never is.

        **The grant's authentication statement travels the same way**
        (``D-IMPL-353`` §2 P6): what the source attested about how the bearer
        authenticated is rendered under
        :data:`~ccf.hitl.principal.AUTHENTICATION_CLAIM`, verbatim, and the
        HITL doors read the approver's assurance from there and from nowhere
        else. A grant that states nothing writes no claim.

        **The grant's product roster travels the same way** (``SEC-017``;
        ``D-IMPL-374`` (2)), under :data:`PRODUCT_CLAIM`, and only when one is
        declared — :func:`granted_products` is its only read.
        """
        grant = self._source.grant_for(token=token)
        if grant is None:
            return None
        return AccessToken(
            token=token,
            client_id=grant.client_id,
            scopes=list(grant.scopes),
            claims={
                **tenant_claims(grant),
                **product_claims(grant),
                **authentication_claims(grant),
            },
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
            if _tokens_match(candidate, token):
                return grant
        return None
