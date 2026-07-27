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

**Four methods, three MCP shapes.** The split is not cosmetic — MCP Resources
are read-only, and ``put`` mutates:

============================  ==========================================
``get(content_address)``      Resource ``ccf-artifact-blob://{address}``,
                              handler returning ``bytes``
``exists(content_address)``   Resource ``ccf-artifact-meta://{address}``
``resolve_uri(uri)``          Resource ``ccf-artifact://{tenant}/{class}/
                              {name}@{version}``
``put(...)``                  Tool ``put_artifact``
============================  ==========================================

The blob handler's ``-> bytes`` annotation is load-bearing: it produces
``BlobResourceContents`` (base64) and preserves canonical bytes exactly, where
a ``str`` handler would produce ``TextResourceContents`` and put the fidelity
of every stored artifact at the mercy of a text round trip (06-RESEARCH.md
Pitfall 4, T-06-20).

**Absence is answered, never inferred.** ``McpError`` carries a stringified
server-side exception with no typed code, so a client that learned "missing"
from a failed read would be string-matching another project's error formatting
(06-RESEARCH.md Pitfall 2, T-06-21). Both metadata resources therefore return a
*positive structured answer* — ``found: false`` is a successful read — so the
client discriminates absence from outage on a typed contract and never on a
message.

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
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes

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
) -> FastMCP:
    """Build the authenticated artifact server over ``store``.

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

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure surface.
    """
    server = FastMCP(
        server_name,
        stateless_http=True,
        json_response=True,
        token_verifier=token_verifier,
        auth=auth_settings,
    )

    @server.resource(BLOB_URI_TEMPLATE, mime_type=_BLOB_MIME_TYPE)
    def artifact_blob(content_address: str) -> bytes:
        """Return the exact canonical bytes stored at ``content_address``.

        ``-> bytes`` and never ``-> str``: this annotation is what selects
        ``BlobResourceContents`` over ``TextResourceContents``, and the
        difference is byte fidelity for every artifact the fabric will ever
        replay against (06-RESEARCH.md Pitfall 4).
        """
        return store.get(content_address=content_address)

    @server.resource(META_URI_TEMPLATE, mime_type=_JSON_MIME_TYPE)
    def artifact_presence(content_address: str) -> str:
        """Answer whether the substrate holds ``content_address``.

        A successful read either way. This is the structured signal the client
        discriminates absence from outage on, so it must not fail when the
        answer is "no" — a failure is indistinguishable from the server being
        down, which is exactly the conflation this resource exists to prevent.
        """
        presence = ArtifactPresence(
            found=store.exists(content_address=content_address)
        )
        return canonical_bytes(presence).decode("utf-8")

    @server.resource(NAME_URI_TEMPLATE, mime_type=_JSON_MIME_TYPE)
    def artifact_resolution(
        tenant: str, artifact_class: str, name: str, artifact_version: str
    ) -> str:
        """Resolve a versioned URI to its exact content address.

        The URI is reassembled through the shared renderer and handed to the
        substrate's own resolver, so the scoping rules — a version registered
        under one name does not resolve under another — are the substrate's
        and are not re-derived here.
        """
        try:
            address = store.resolve_uri(
                uri=artifact_uri(
                    tenant_id=tenant,
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

    @server.tool(name=PUT_ARTIFACT_TOOL)
    def put_artifact(
        tenant_id: str, artifact_class: str, name: str, canonical_b64: str
    ) -> ArtifactRef:
        """Store one artifact carried as base64 canonical bytes.

        A Tool rather than a Resource because Resources cannot mutate, and
        base64 rather than text for the same reason the blob resource returns
        bytes.

        The declared ``ArtifactRef`` return type is what populates MCP's
        ``structuredContent``; a handler annotated ``-> dict`` leaves it
        ``None`` and forces the client to parse ``content[0].text``, which is a
        second, untyped contract nobody wrote down.

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
        return store.put(
            tenant_id=tenant_id,
            artifact_class=artifact_class,
            name=name,
            artifact=artifact,
        )

    return server
