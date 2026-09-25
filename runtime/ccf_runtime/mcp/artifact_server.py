"""MCP artifact persistence — the §7.4 ArtifactStore substrate on the wire.

SDK-defined (CLAUDE.md §7.4: "the SDK persists CCF artifacts through an
``ArtifactStoreProtocol`` with an MCP-backed reference implementation, so users
are free to use their own persistent store and decision-playback data store");
addressing per D-IMPL-26; role separation per §7.1 and D-03.

**A separate module and a separate server from L6 egress, deliberately.** §7.1
requires the artifact-persistence role to live apart from the egress role
because the two have different trust postures: egress serves *live*,
TTL-bound products to any MCP-capable consumer, while this server holds
*immutable artifacts at rest* that a replay will resolve years from now, and it
is authenticated (D-26). Keeping them in one module would make that separation
a convention; keeping them in two makes it structural, and
``tests/invariants/test_mcp_role_separation.py`` is what keeps it true. The
egress scheme does not appear anywhere in this module and must not — that
invariant test greps this very source for it, so naming it here even in prose
would defeat the check.

**What this server is.** A transport in front of an
:class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` the deployment supplies.
The substrate owns the bytes and owns the naming index; this module owns only
the mapping from four Protocol methods onto MCP surfaces. Two stores pointed at
one of these servers therefore share one index, which is the property that
makes a versioned URI resolvable by a process that never wrote it.

**What this server cannot do.** It is a persistence substrate reached *through*
Control Plane and L2 mechanism, never a participant in the fabric. It holds no
graph write handle and no graph read handle; it imports nothing from the L3
graph package, and there is no field on it that could hold either. Nothing
enters the Context Graph because an artifact was read back out of here —
admission is L2's, and the single-writer invariant (INV-CH7-10, CLAUDE.md §10)
holds across this boundary because there is no second writer here to hold
(T-06-19). The honest claim (D-21) is the structural one, and the AST scan in
``tests/invariants/test_mcp_role_separation.py`` is the mechanism of record.

**Every body runs under a capability minted for it** (``D-IMPL-353`` §1.2,
§2 P5). The :class:`~ccf_runtime.mcp.tenancy.TenantGuardedServer` decides
tenancy, asks the deployment's authorizer for each surface's declared action on
its declared resource, and hands the body an
:class:`~ccf.authz.capability.Authorized` as its first argument. The body hands
that — and nothing else it could have chosen — to the handle it acts through:

============================  ==========================================
``put(authorized, artifact)`` Tool ``put_artifact`` —
                              ``Authorized[ArtifactWrite]`` for
                              ``"<class>/<name>"``; **no ``tenant_id``
                              argument**, the tenant is the capability's
``govern_dereference(...)``   Resource ``ccf-artifact-blob://{address}``,
                              handler returning ``bytes`` —
                              ``Authorized[ArtifactRead]`` for the address
``govern_dereference(...)``   Resource ``ccf-artifact-meta://{address}`` —
                              the same capability; a bit about the address
``resolve_uri(uri)``          Resource ``ccf-artifact://{tenant}/{class}/
                              {name}@{version}`` —
                              ``Authorized[ArtifactRead]`` for
                              ``"<class>/<name>"``
============================  ==========================================

**There is no untenanted read of artifact bytes.** The two hash-addressed
resources carry no tenant on the wire; their capability's tenant is the
verified grant's **sole** tenant, and a grant spanning several is refused as
ambiguous rather than picked for (§1.3). Their reads go through
:func:`~ccf_runtime.authz.delivery_boundary.govern_dereference` — the one
governed evidence read, with its three holds — because after §1.2 there is no
other way to call the store's read. **A consequence, stated rather than
hidden:** that dereference resolves its target as a Decision Replay record, so
a stored artifact of any other class answers the ``nonexistent`` shell through
the blob resource. The HTTP artifact GET has had this property since
``D-IMPL-345``; the MCP blob now has it too.

The blob handler's ``-> bytes`` annotation is load-bearing: it produces
``BlobResourceContents`` (base64) and preserves canonical bytes exactly, where
a ``str`` handler would produce ``TextResourceContents`` and put the fidelity
of every stored artifact at the mercy of a text round trip (06-RESEARCH.md
Pitfall 4, T-06-20).

**A governed refusal crosses as a response, never as a transport error**
(``D-IMPL-256``). On the blob resource the shell's canonical bytes stand where
the artifact would — they cannot hash to the address asked for, so a verifying
client cannot mistake them for it — and on the presence resource the same
shell stands where ``found: true`` would, told apart by the top-level ``kind``
key a presence answer does not have. Absence is therefore still answered and
never inferred: the answer is the shell.

Server name, bind address, token values, scopes, tenant identifiers, and
artifact-class names are all deployment values supplied by the caller. This
module holds none of them and ships no default token (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import base64
import json

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.artifacts.protocol import (
    ARTIFACT_URI_SCHEME,
    ArtifactRef,
    ArtifactStoreProtocol,
    ArtifactUriUnresolvable,
    artifact_uri,
)
from ccf.authz.actions import ACTION_ARTIFACT_READ, ACTION_ARTIFACT_WRITE
from ccf.authz.capability import ArtifactRead, ArtifactWrite, Authorized
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import AuditLog
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_MCP_RESOURCE,
    DereferenceRequest,
    DisclosingRecorderProtocol,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import ProductEntitlementSourceProtocol
from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
from ccf_runtime.mcp.tenancy import TenantGuardedServer

__ccf_mode__ = "algorithmic"

__all__ = [
    "ARTIFACT_BLOB_URI_SCHEME",
    "ARTIFACT_META_URI_SCHEME",
    "BLOB_URI_TEMPLATE",
    "META_URI_TEMPLATE",
    "NAME_URI_TEMPLATE",
    "PUT_ARTIFACT_TOOL",
    "ArtifactPresence",
    "ArtifactResolution",
    "NonCanonicalPayload",
    "artifact_blob_uri",
    "artifact_meta_uri",
    "build_artifact_server",
]

#: Scheme of the byte-exact artifact body. Distinct from the naming scheme
#: because identity (the content address) and naming (the versioned URI) are
#: two questions, and the Protocol keeps them two calls.
ARTIFACT_BLOB_URI_SCHEME = "ccf-artifact-blob"

#: Scheme of the presence answer. Its own scheme rather than a query parameter
#: on the blob one, so "is it there" can succeed while "give me the bytes"
#: would have failed — which is the whole basis of the absence/outage split.
ARTIFACT_META_URI_SCHEME = "ccf-artifact-meta"

BLOB_URI_TEMPLATE = f"{ARTIFACT_BLOB_URI_SCHEME}://{{content_address}}"
META_URI_TEMPLATE = f"{ARTIFACT_META_URI_SCHEME}://{{content_address}}"

#: The naming surface, mirroring :func:`ccf.artifacts.protocol.artifact_uri`
#: segment for segment. Built from the shared scheme constant rather than
#: spelled out, so the server cannot drift from the grammar the parser enforces.
NAME_URI_TEMPLATE = (
    f"{ARTIFACT_URI_SCHEME}://"
    "{tenant}/{artifact_class}/{name}@{artifact_version}"
)

#: Name of the one mutating surface. A Tool, because Resources are read-only.
PUT_ARTIFACT_TOOL = "put_artifact"

#: The resource a write and a name resolution are decided on: the class and
#: name segments the naming key already uses (``D-IMPL-353`` §1.2), spelled
#: from the wire arguments by the wrapper so a scope mapping names artifacts
#: in one vocabulary for both.
_CLASS_AND_NAME = "{artifact_class}/{name}"

_BLOB_MIME_TYPE = "application/octet-stream"
_JSON_MIME_TYPE = "application/json"


class NonCanonicalPayload(ValueError):
    """A ``put`` payload is not the canonical rendering of what it decodes to.

    The server re-derives ``canonical_bytes`` from the parsed payload and
    compares it to the bytes it received. They agree for every artifact the SDK
    can canonicalize, because the canonical form is a fixed point under a JSON
    round trip — floats are rejected outright, ``Decimal`` and ``datetime``
    render as strings, and mapping keys are sorted on both passes.

    Raised when they disagree, rather than storing the payload anyway. Storing
    it would mean the address a later reader computes from the bytes is not the
    address the store filed them under, which is the one failure content
    addressing exists to make impossible (T-06-22).
    """


class ArtifactPresence(CCFContract):
    """Whether the substrate holds an artifact — a positive answer either way.

    Attributes:
        found: ``True`` if the address is stored.
    """

    found: bool


class ArtifactResolution(CCFContract):
    """What a versioned URI names, or a typed statement that it names nothing.

    Attributes:
        found: ``True`` if the name resolves.
        content_address: The exact address, when it resolves; ``None``
            otherwise. Never an approximate one and never the newest under the
            name — the substrate has no surface that could return either
            (CLAUDE.md §7.4).
    """

    found: bool
    content_address: str | None


def artifact_blob_uri(*, content_address: str) -> str:
    """Render the blob URI for one content address.

    Exists so the server, the store, and the tests agree what the URI *is*
    rather than each formatting it — the same argument
    :func:`ccf_runtime.mcp.egress.product_uri` makes for the egress scheme.
    """
    return f"{ARTIFACT_BLOB_URI_SCHEME}://{content_address}"


def artifact_meta_uri(*, content_address: str) -> str:
    """Render the presence URI for one content address."""
    return f"{ARTIFACT_META_URI_SCHEME}://{content_address}"


def build_artifact_server(
    *,
    server_name: str,
    store: ArtifactStoreProtocol,
    token_verifier: TokenVerifier,
    auth_settings: AuthSettings,
    authorizer: TenantAuthorizerProtocol,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: DisclosingRecorderProtocol,
    audit_log: AuditLog,
) -> FastMCP:
    """Build the authenticated, authorized artifact server over ``store``.

    ``stateless_http=True`` is load-bearing rather than a tuning choice: it is
    what makes the client's session-per-call cheap (:mod:`ccf.mcp.client`, and
    the held-session bridge that deadlocks without it). ``json_response=True``
    pairs with it.

    Both ``token_verifier`` and ``auth_settings`` are required, and required
    *together*, because ``FastMCP`` installs its authentication middleware only
    when both are present — a server given a verifier and no settings would
    look authenticated and refuse nothing. Making them one non-defaulted pair
    is what removes that configuration from the set of reachable states (D-26,
    T-06-18).

    Args:
        server_name: The name this server advertises. Deployment identity.
        store: The persistence substrate. Owns the bytes and the naming index —
            this server owns neither, which is why two clients against one
            server see one index.
        token_verifier: Verifies presented bearer tokens. See
            :mod:`ccf_runtime.mcp.auth` for the reference implementation and
            for what a deployment must supply instead of it.
        auth_settings: Issuer, resource-server identity, and required scopes.
            Deployment values in their entirety.
        authorizer: The deployment's authorizer, asked by the wrapper for
            every surface's declared action before its body runs. **Required**
            (``D-IMPL-353`` §2 P4): there is no arm in which the decision is
            skipped.
        entitlement_source: The deployment's entitlement seam and the holder of
            the determination clock, for the governed dereference's second
            hold.
        refusal_recorder: The ONE minting seam, which also states the
            disclosure level, for the dereference's third hold and for the
            shell it records on every refusal.
        audit_log: The Control Plane's own append-only log, where every
            dereference appends the trail of its read (``D-IMPL-345`` R-5).

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure surface.
    """
    door = TenantGuardedServer(
        FastMCP(
            server_name,
            stateless_http=True,
            json_response=True,
            token_verifier=token_verifier,
            auth=auth_settings,
        ),
        authorizer=authorizer,
    )

    def dereference(
        authorized: Authorized[ArtifactRead], *, content_address: str, address: str
    ) -> bytes | RefusalEnvelope:
        """The one governed read both hash-addressed resources make.

        A bytes ask under this surface's identity and the URI the caller
        read; what comes back is either the exact stored bytes or an
        already-recorded, already-disclosed shell.
        """
        decided = govern_dereference(
            authorized,
            reference=DereferenceRequest(
                reference=content_address, by_uri=False, wants_bytes=True
            ),
            store=store,
            entitlement_source=entitlement_source,
            refusal_recorder=refusal_recorder,
            audit_log=audit_log,
            surface=SURFACE_MCP_RESOURCE,
            address=address,
        )
        if isinstance(decided, RefusalEnvelope):
            return decided
        assert decided.payload is not None  # a bytes ask always carries them
        return decided.payload

    @door.resource(
        BLOB_URI_TEMPLATE,
        action=ACTION_ARTIFACT_READ,
        subject=door.from_grant(),
        resource=door.resource_argument("content_address"),
        mutating=False,
        mime_type=_BLOB_MIME_TYPE,
    )
    def artifact_blob(authorized: Authorized[ArtifactRead], content_address: str) -> bytes:
        """Return the exact canonical bytes stored at ``content_address``.

        ``-> bytes`` and never ``-> str``: this annotation is what selects
        ``BlobResourceContents`` over ``TextResourceContents``, and the
        difference is byte fidelity for every artifact the fabric will ever
        replay against (06-RESEARCH.md Pitfall 4).

        **Through the governed dereference, under a read capability**
        (``D-IMPL-353`` §2 P5). No tenant appears on this surface, so the
        capability's tenant is the verified grant's sole tenant — a grant
        spanning several is refused as ambiguous before this body runs. What
        ``SEC-018`` recorded as a residual (possession of a 64-character
        address as the last thing between a verified caller and another
        tenant's bytes) is now the dereference's three holds: the record's own
        principal, the grant that governed its serve, and the disclosure level
        in force. A refusal crosses as the shell's canonical bytes.
        """
        served = dereference(
            authorized,
            content_address=content_address,
            address=artifact_blob_uri(content_address=content_address),
        )
        if isinstance(served, RefusalEnvelope):
            return canonical_bytes(served)
        return served

    @door.resource(
        META_URI_TEMPLATE,
        action=ACTION_ARTIFACT_READ,
        subject=door.from_grant(),
        resource=door.resource_argument("content_address"),
        mutating=False,
        mime_type=_JSON_MIME_TYPE,
    )
    def artifact_presence(authorized: Authorized[ArtifactRead], content_address: str) -> str:
        """Answer whether the substrate holds ``content_address``.

        A successful read either way, and the structured signal the client
        discriminates absence from outage on. Decided exactly as
        :func:`artifact_blob` is — the same capability, the same three holds —
        and strictly less disclosing: one bit about an address the caller
        already holds. A refusal, absence included, crosses as the shell,
        which the ``kind`` key tells apart from a presence answer.
        """
        served = dereference(
            authorized,
            content_address=content_address,
            address=artifact_meta_uri(content_address=content_address),
        )
        if isinstance(served, RefusalEnvelope):
            return canonical_bytes(served).decode("utf-8")
        return canonical_bytes(ArtifactPresence(found=True)).decode("utf-8")

    @door.resource(
        NAME_URI_TEMPLATE,
        action=ACTION_ARTIFACT_READ,
        subject=door.from_argument("tenant"),
        resource=door.resource_composed(_CLASS_AND_NAME),
        mutating=False,
        mime_type=_JSON_MIME_TYPE,
    )
    def artifact_resolution(
        authorized: Authorized[ArtifactRead],
        artifact_class: str,
        name: str,
        artifact_version: str,
    ) -> str:
        """Resolve a versioned URI to its exact content address.

        The URI is reassembled through the shared renderer and handed to the
        substrate's own resolver, so the scoping rules — a version registered
        under one name does not resolve under another — are the substrate's
        and are not re-derived here.

        **Tenant-decided by its segment, and the tenant that reaches the
        resolver is the capability's** (``SEC-018``; ``D-IMPL-353`` §1.2). The
        ``tenant`` segment stays on the wire — it selects which of a
        multi-tenant grant's tenants — but the body never sees it: the wrapper
        decides it against the grant and this body reads
        ``authorized.tenant``. This is the surface that turns a name into a
        content address, which is why it was never untenanted.
        """
        try:
            address = store.resolve_uri(
                uri=artifact_uri(
                    tenant_id=authorized.tenant,
                    artifact_class=artifact_class,
                    name=name,
                    artifact_version=artifact_version,
                )
            )
        except ArtifactUriUnresolvable:
            resolution = ArtifactResolution(found=False, content_address=None)
        else:
            resolution = ArtifactResolution(found=True, content_address=address)
        return canonical_bytes(resolution).decode("utf-8")

    @door.tool(
        name=PUT_ARTIFACT_TOOL,
        action=ACTION_ARTIFACT_WRITE,
        subject=door.from_grant(),
        resource=door.resource_composed(_CLASS_AND_NAME),
        mutating=True,
    )
    def put_artifact(
        authorized: Authorized[ArtifactWrite],
        artifact_class: str,
        name: str,
        canonical_b64: str,
    ) -> ArtifactRef:
        """Store one artifact carried as base64 canonical bytes.

        A Tool rather than a Resource because Resources cannot mutate, and
        base64 rather than text for the same reason the blob resource returns
        bytes.

        The declared ``ArtifactRef`` return type is what populates MCP's
        ``structuredContent``; a handler annotated ``-> dict`` leaves it
        ``None`` and forces the client to parse ``content[0].text``, which is a
        second, untyped contract nobody wrote down.

        **``tenant_id`` is deleted** (``D-IMPL-353`` §1.2, §1.3). This tool took
        the tenant it wrote under as a caller argument — the same shape as the
        finding on the HTTP door — and ``SEC-018`` turned that into a claim
        decided against the grant. Now there is no argument at all: the store
        files under ``authorized.tenant``, and ``artifact_class`` and ``name``
        reach it as ``authorized.resource`` (``"<class>/<name>"``), the
        resource the write was authorized *for*. The store verifies kind,
        resource and mint by identity before its first statement; a capability
        for another name, or of another kind, dies there.

        Mutating, so a stated stdio identity cannot reach it — the wrapper
        refuses it before any decision is made.

        Raises:
            NonCanonicalPayload: the payload is not the canonical rendering of
                what it parses to, so the address the store would file it under
                is not the address a reader would compute from it.
        """
        canonical = base64.b64decode(canonical_b64, validate=True)
        artifact = json.loads(canonical)
        if canonical_bytes(artifact) != canonical:
            raise NonCanonicalPayload(
                "payload is not the canonical rendering of its own content; "
                "refusing to file bytes under an address a reader would not "
                "recompute"
            )
        return store.put(authorized, artifact)

    return door.build()
