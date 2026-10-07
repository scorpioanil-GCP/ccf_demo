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

**What this server is.** A transport in front of an artifact substrate the
deployment supplies (:class:`ArtifactSubstrate` — the four
:class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` methods plus the two
readings the split below needs). The substrate owns the bytes and owns the
naming index; this module owns only the mapping from Protocol methods onto MCP
surfaces. Two stores pointed at one of these servers therefore share one index,
which is the property that makes a versioned URI resolvable by a process that
never wrote it.

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
the split (below)             Resource ``ccf-artifact-blob://{address}``,
                              handler returning ``bytes`` —
                              ``Authorized[ArtifactRead]`` for the address
the split (below)             Resource ``ccf-artifact-meta://{address}`` —
                              the same capability; a bit about the address
``resolve_uri(uri)``          Resource ``ccf-artifact://{tenant}/{class}/
                              {name}@{version}`` —
                              ``Authorized[ArtifactRead]`` for
                              ``"<class>/<name>"``
============================  ==========================================

**There is no untenanted read of artifact bytes.** The two hash-addressed
resources carry no tenant on the wire; their capability's tenant is the
verified grant's **sole** tenant, and a grant spanning several is refused as
ambiguous rather than picked for (§1.3).

THE SPLIT — how a hash-addressed read is decided (the D-IMPL-353 join)
----------------------------------------------------------------------
Lane MCP routed every blob and presence read through
:func:`~ccf_runtime.authz.delivery_boundary.govern_dereference`, which resolves
its target as a Decision Replay record — so the §7.4 persistence transport
could round-trip **only** replay records, and every other artifact class
answered the ``nonexistent`` shell. Lane MCP flagged it; the join implements
the split so §7.4 holds for EVERY artifact class. For a bare content address,
in this order:

1. **The capability, first.** ``verify(authorized, kind=ArtifactRead,
   resource=content_address)`` — the address IS the resource the wrapper
   decided on. Nothing below runs on a fabricated, retargeted or wrong-kind
   capability.
2. **What the address is**, from the substrate's own naming index
   (:meth:`ArtifactSubstrate.names_at`): every ``(tenant, class, name)`` the
   address was filed under. Content addressing means one address may be filed
   under several names, by several tenants; the decision is taken over the
   whole set, in the safe direction.
3. **Governed evidence goes through the governed dereference.** If ANY name's
   class is one the substrate's :class:`~ccf.artifacts.protocol.WriteKinds`
   declares under ``ReplayMint`` — a replay record, a query pin, an admitted
   child contract, whatever the deployment declared as fabric-written
   evidence — the read is a ``D-IMPL-345`` dereference: entitlement re-decided,
   refusal recorded, disclosed, the ``nonexistent`` shell for anything that is
   not a readable record. So a query pin under ``ReplayMint`` is
   indistinguishable from nothing here exactly as it is on the HTTP door
   (``D-IMPL-345`` C23).
4. **Everything else is served tenant-scoped.** An address filed under the
   capability's tenant in an undeclared (client-lane) class — or the workflow
   engine's trace class, declared under ``Execute | Resume`` — is served: the
   exact stored bytes, with one ``authz_decision`` audit event naming the read.
   An address filed under **no** name of the capability's tenant — another
   tenant's, or nothing at all — goes through the governed dereference too and
   answers the ``nonexistent`` shell: byte-identical, up to the reference asked
   and the record it produced, to a missing address. A caller cannot learn
   from this door that another tenant holds bytes at an address it names.

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
from typing import Protocol, runtime_checkable

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.artifacts.protocol import (
    ARTIFACT_URI_SCHEME,
    ArtifactName,
    ArtifactRef,
    ArtifactStoreProtocol,
    ArtifactUriUnresolvable,
    WriteKinds,
    artifact_uri,
)
from ccf.authz.actions import ACTION_ARTIFACT_READ, ACTION_ARTIFACT_WRITE
from ccf.authz.capability import ArtifactRead, ArtifactWrite, Authorized, ReplayMint, verify
from ccf.erasure import ErasedContentRefused, ErasureIndexProtocol, ErasureTrust, compose_erasure_consult
from ccf.erasure.approval import PinnedPolicySource
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
    "ARTIFACT_NAMES_URI_SCHEME",
    "BLOB_URI_TEMPLATE",
    "META_URI_TEMPLATE",
    "NAMES_URI_TEMPLATE",
    "NAME_URI_TEMPLATE",
    "PUT_ARTIFACT_TOOL",
    "ArtifactPresence",
    "ArtifactResolution",
    "ArtifactSubstrate",
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

#: The naming resource (SEC-009; ``D-IMPL-374`` (4), ruling 2): every
#: ``(tenant, class, name)`` an address was filed under, scoped to the caller's
#: verified tenant — what the erasure door reads to verify an address's STORED
#: class and tenant over the §7.4 reference store. Naming only, never bytes.
ARTIFACT_NAMES_URI_SCHEME = "ccf-artifact-names"
NAMES_URI_TEMPLATE = f"{ARTIFACT_NAMES_URI_SCHEME}://{{content_address}}"

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


@runtime_checkable
class ArtifactSubstrate(ArtifactStoreProtocol, Protocol):
    """What this server needs of its substrate: the Protocol, plus the split's two readings.

    The four :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` methods
    are inherited. On top of them, the hash-addressed resources have to know
    **what** an address is before deciding **how** to read it, and a bare
    content address says nothing about class or tenant on its own:

    * :attr:`write_kinds` — the deployment's declaration of which classes are
      fabric-written and under which kinds, so a class declared under
      ``ReplayMint`` is recognized as governed evidence;
    * :meth:`names_at` — the reverse of the naming index, every
      ``(tenant, class, name)`` an address was filed under.

    The shipped :class:`~ccf.artifacts.file_store.FileArtifactStore` conforms.
    Structural, so a deployment's own substrate conforms by carrying the two
    members; a store carrying neither cannot be put behind this server, which
    is the honest posture — without them the server could not tell a
    tenant's own blob from governed evidence or from another tenant's bytes.
    """

    @property
    def write_kinds(self) -> WriteKinds:
        """Which artifact classes are fabric-written here, and by which kinds."""
        ...

    def names_at(self, *, content_address: str) -> tuple[ArtifactName, ...]:
        """Every ``(tenant, class, name)`` this address was filed under."""
        ...


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


def artifact_names_uri(*, content_address: str) -> str:
    """Render the naming URI for one content address (SEC-009; `D-IMPL-374` (4), ruling 2)."""
    return f"{ARTIFACT_NAMES_URI_SCHEME}://{content_address}"


def build_artifact_server(
    *,
    server_name: str,
    store: ArtifactSubstrate,
    token_verifier: TokenVerifier,
    auth_settings: AuthSettings,
    authorizer: TenantAuthorizerProtocol,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: DisclosingRecorderProtocol,
    audit_log: AuditLog,
    erasure_index: ErasureIndexProtocol,
    control_plane: PinnedPolicySource,
    erasure_trust: ErasureTrust,
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
        store: The persistence substrate (:class:`ArtifactSubstrate`). Owns
            the bytes and the naming index — this server owns neither, which
            is why two clients against one server see one index.
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
            hold and for the instant a client-lane read is audited at.
        refusal_recorder: The ONE minting seam, which also states the
            disclosure level, for the dereference's third hold and for the
            shell it records on every refusal.
        audit_log: The Control Plane's own append-only log, where every
            dereference — governed or client-lane — appends the trail of its
            read (``D-IMPL-345`` R-5).
        erasure_index: The deployment's durable erasure index (SEC-009;
            ``D-IMPL-374`` (4), MCP ruling and fix round 1 C1). **Required, no
            default**: this server is the ArtifactStore's persistence
            transport (CLAUDE.md §7.4), so it composes ``store`` with the
            erasure consult itself, through
            :func:`~ccf.erasure.compose_erasure_consult`. Every byte read goes
            through a view scoped to the caller's verified tenant (I6): a
            governed record follows ``govern_dereference``'s
            authorization-first order, and an erased client-lane artifact
            crosses as the erased reading — the not-found shell at
            ``minimal``, ``erased-content`` above it — never as bytes. The
            naming resource still resolves through ``store``: it returns an
            address, never bytes (the ``exists`` reasoning, U8).
        control_plane: The deployment's Control Plane (SEC-009; fix round 4).
            **Required, no default**: an erasure's approval is a signed HITL
            attestation, verified against the key the pinned HITL policy
            declares for the approver, and that policy is resolved through this
            Control Plane. An approval that does not verify here is
            ``index-unsupported``.
        erasure_trust: The deployment's per-tenant erasure authorities
            (SEC-009; fix round 5, R1, R2, R4). **Required, no default**: for
            each tenant that may erase, the HITL policy key its transport is
            bound to, its erasure workflow's content hash and the erasure
            door's public key — fixed here, never chosen by a filed artifact.
            A tenant it names no authority for reads ``index-unsupported``.

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure surface.
    """
    # SEC-009 (`D-IMPL-374` (4), MCP ruling): the one composition helper.
    consulted = compose_erasure_consult(
        store,
        index=erasure_index,
        audit_log=audit_log,
        clock=entitlement_source.clock,
        control_plane=control_plane,
        # Fix round 5, R1, R2, R4: the deployment's per-tenant trust root, fixed here.
        erasure_trust=erasure_trust,
    )
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
        """THE SPLIT — the one governed read both hash-addressed resources make.

        See the module docstring. Returns the exact stored bytes, or an
        already-recorded, already-disclosed shell.
        """
        # (1) The capability first, bound to the address the wrapper decided
        # on. The wrapper minted it for this address; a body reached any other
        # way holds proof or holds nothing (D-IMPL-353 §1.5c, f).
        verify(authorized, kind=ArtifactRead, resource=content_address)
        # (2) What the address IS, over every name it was filed under.
        names = store.names_at(content_address=content_address)
        governed = any(
            ReplayMint in store.write_kinds.for_class(named.artifact_class)
            for named in names
        )
        own = [named for named in names if named.tenant_id == authorized.tenant]
        if governed or not own:
            # (3) Governed evidence, another tenant's bytes, or nothing at all:
            # the governed dereference decides, records and discloses — and
            # answers the nonexistent shell for everything that is not a
            # record this principal may read.
            decided = govern_dereference(
                authorized,
                reference=DereferenceRequest(
                    reference=content_address, by_uri=False, wants_bytes=True
                ),
                store=consulted,
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
        # (4) The client lane: filed under the capability's tenant in a class
        # the deployment did not declare governed. Served tenant-scoped, and
        # the read leaves the same trail a governed one does (D-IMPL-345 R-5).
        try:
            # I6: the caller's own tenant's view — the split above decided it
            # owns this client-lane artifact.
            payload = consulted.scoped(authorized.tenant).get(content_address=content_address)
        except ErasedContentRefused as erased:
            # SEC-009: the caller owns this client-lane artifact (decided by the
            # split above), so it receives the erased reading at its level.
            decided = govern_dereference(
                authorized,
                reference=DereferenceRequest(
                    reference=content_address, by_uri=False, wants_bytes=True
                ),
                store=consulted,
                entitlement_source=entitlement_source,
                refusal_recorder=refusal_recorder,
                audit_log=audit_log,
                surface=SURFACE_MCP_RESOURCE,
                address=address,
                erased_client_read=erased,
            )
            assert isinstance(decided, RefusalEnvelope)  # an erased read only refuses
            return decided
        audit_log.append(
            action="authz_decision",
            key=content_address,
            version=content_address,
            resolved=True,
            occurred_at=entitlement_source.clock(),
            actor=authorized.principal,
            artifact_class=own[0].artifact_class,
            authz_action_id=ArtifactRead.action_id,
            authz_matched_pattern=None,
            authz_resource=content_address,
        )
        return payload

    @door.resource(
        BLOB_URI_TEMPLATE,
        action=ACTION_ARTIFACT_READ,
        subject=door.from_grant(),
        resource=door.resource_argument("content_address"),
        mutating=False,
        products=door.products_unknown(
            "an artifact is addressed by content address or by class and name;"
            " no Context Product class is known at the call"
        ),
        mime_type=_BLOB_MIME_TYPE,
    )
    def artifact_blob(authorized: Authorized[ArtifactRead], content_address: str) -> bytes:
        """Return the exact canonical bytes stored at ``content_address``.

        ``-> bytes`` and never ``-> str``: this annotation is what selects
        ``BlobResourceContents`` over ``TextResourceContents``, and the
        difference is byte fidelity for every artifact the fabric will ever
        replay against (06-RESEARCH.md Pitfall 4).

        **Under a read capability, through the split** (``D-IMPL-353`` §2 P5;
        the module docstring). No tenant appears on this surface, so the
        capability's tenant is the verified grant's sole tenant — a grant
        spanning several is refused as ambiguous before this body runs. A
        refusal crosses as the shell's canonical bytes.
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
        products=door.products_unknown(
            "an artifact is addressed by content address or by class and name;"
            " no Context Product class is known at the call"
        ),
        mime_type=_JSON_MIME_TYPE,
    )
    def artifact_presence(authorized: Authorized[ArtifactRead], content_address: str) -> str:
        """Answer whether the substrate holds ``content_address`` for this caller.

        A successful read either way, and the structured signal the client
        discriminates absence from outage on. Decided exactly as
        :func:`artifact_blob` is — the same capability, the same split — and
        strictly less disclosing: one bit about an address the caller already
        holds. A refusal, absence included, crosses as the shell, which the
        ``kind`` key tells apart from a presence answer.
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
        NAMES_URI_TEMPLATE,
        action=ACTION_ARTIFACT_READ,
        subject=door.from_grant(),
        resource=door.resource_argument("content_address"),
        mutating=False,
        products=door.products_unknown(
            "an artifact is addressed by content address or by class and name;"
            " no Context Product class is known at the call"
        ),
        mime_type=_JSON_MIME_TYPE,
    )
    def artifact_names(authorized: Authorized[ArtifactRead], content_address: str) -> str:
        """Every ``(tenant, class, name)`` this address was filed under — the caller's tenant only.

        SEC-009 (``D-IMPL-374`` (4), ruling 2): the backing store's naming
        introspection, so the erasure door can verify an address's STORED
        class and tenant through the MCP-backed reference store. Scoped to the
        capability's verified tenant: another tenant's filing of the same bytes
        never crosses (I6). Naming only — no artifact byte is read; a malformed
        address answers the empty list, as the store's ``names_at`` does.

        **The same entitlement the blob read requires** (fix round 2, N4). An
        address filed under a class the deployment declared governed answers
        its names only to a principal the governed dereference admits — the
        same decision, record and disclosure :func:`artifact_blob` makes, asked
        without bytes. A refusal crosses as the shell, which the client reads
        as an unverifiable answer and the erasure door as ``class-unverifiable``.
        """
        verify(authorized, kind=ArtifactRead, resource=content_address)
        names = store.names_at(content_address=content_address)
        governed = any(
            ReplayMint in store.write_kinds.for_class(named.artifact_class) for named in names
        )
        if governed:
            decided = govern_dereference(
                authorized,
                reference=DereferenceRequest(
                    reference=content_address, by_uri=False, wants_bytes=False
                ),
                store=consulted,
                entitlement_source=entitlement_source,
                refusal_recorder=refusal_recorder,
                audit_log=audit_log,
                surface=SURFACE_MCP_RESOURCE,
                address=artifact_names_uri(content_address=content_address),
            )
            if isinstance(decided, RefusalEnvelope):
                return canonical_bytes(decided).decode("utf-8")
        own = tuple(named for named in names if named.tenant_id == authorized.tenant)
        return canonical_bytes(own).decode("utf-8")

    @door.resource(
        NAME_URI_TEMPLATE,
        action=ACTION_ARTIFACT_READ,
        subject=door.from_argument("tenant"),
        resource=door.resource_composed(_CLASS_AND_NAME),
        mutating=False,
        products=door.products_unknown(
            "an artifact is addressed by content address or by class and name;"
            " no Context Product class is known at the call"
        ),
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
        products=door.products_unknown(
            "an artifact is addressed by content address or by class and name;"
            " no Context Product class is known at the call"
        ),
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
        return consulted.put(authorized, artifact)

    return door.build()
