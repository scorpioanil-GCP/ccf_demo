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
the subject match (below)     Tool ``match_artifact_subject`` —
                              ``Authorized[ArtifactSubjectMatch]`` for
                              the action id itself; the erasure door's
                              verdict, never bytes
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
2. **What the address is to the caller's tenant**, from the substrate's own
   naming index (:meth:`ArtifactSubstrate.names_at`): every
   ``(tenant, class, name)`` the address was filed under, kept to the
   capability's tenant. Content addressing means one address may be filed
   under several names, by several tenants; the decision is taken over every
   name the caller's OWN tenant filed it under, in the safe direction, and
   never over another tenant's (C8, ``D-IMPL-376`` (6)). Judged over every
   tenant's names, another tenant's governed filing of identical bytes turned
   this tenant's own reads into the shell: the address became a channel
   between tenants — an existence oracle, and a way to make an owner's own
   artifact unreadable and unerasable. Judging over the caller's tenant
   relaxes nothing: a governed filing by that tenant still sends every
   principal of it through the governed dereference, and the client lane
   below only serves an address the caller's own tenant filed — which a filing
   can do only by presenting those exact bytes. "Filed by the caller's tenant"
   is read from the naming index, so it holds because a tenant id is one
   naming segment: the store's write boundary refuses a tenant containing the
   separator (:func:`~ccf.artifacts.protocol.authorized_write_target`, M-4).
3. **Governed evidence goes through the governed dereference.** If ANY of
   those names' classes is one the substrate's :class:`~ccf.artifacts.protocol.WriteKinds`
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
   Only bytes that hash to the address are served (Dave's E1 (a),
   ``D-IMPL-378``): the address is the sha256 of the stored canonical bytes,
   so bytes altered under it are not the artifact it names, and the governed
   dereference decides them; its re-hash on arrival answers them exactly as
   a missing address. The answer does not say which lane served it, so
   bytes that validate as a Decision Replay record
   (``DecisionReplayRecord.model_validate_json``, the
   validator every SDK reader of a record applies) are not served this way
   (the client-lane ruling, ``D-IMPL-378``): the governed dereference decides
   them, and it serves a record only where the store's naming shows the
   fabric's record writer filed the address under the record's tenant and that
   tenant is the caller's — never true of an address the caller's tenant filed
   only on its client lane — so they answer exactly as a missing address.
   An address filed under **no** name of the capability's tenant — another
   tenant's, or nothing at all — goes through the governed dereference too,
   which holds the caller to the tenant a record was decided under before any
   other hold (hold 0 of
   :func:`~ccf_runtime.authz.delivery_boundary.govern_dereference`, C-2): it
   answers the ``nonexistent`` shell, at every disclosure level, byte-identical
   up to the reference asked and the record it produced to a missing address —
   another tenant's genuine replay record included, and so are bytes shaped as
   a record that the fabric's record writer did not file (the governed read's
   provenance check). A caller cannot learn from this door that another tenant
   holds bytes at an address it names.

THE SUBJECT MATCH — the erasure door's verdict, never the bytes (D3b)
---------------------------------------------------------------------
``D-IMPL-378``, Dave's 16:40 MST item 5: *"Build the narrowly authorized
server-side subject-match path without serving the bytes."* The erasure door
over the MCP-backed store verifies each requested address's subject; where the
blob resource answers the address as absent — a record-shaped client-lane
filing above all — the door asks the ``match_artifact_subject`` tool instead,
and this server judges the bytes where they are with
:func:`~ccf.erasure.judge_subject`, the function the in-process door applies to
the bytes it reads, and answers one :class:`~ccf.erasure.SubjectMatchAnswer`.
It answers the erasure door of the caller's tenant alone, decided before the
substrate is read: the deployment must grant
:data:`~ccf.authz.actions.ACTION_ARTIFACT_SUBJECT_MATCH` by name (the guard); the
caller's tenant must have an erasure authority in this server's trust; and the
query, rebuilt under the caller's tenant, must carry a signature by that
authority's declared door key (:func:`~ccf.erasure.verify_subject_match_query`).
Every refusal past the guard is the one :data:`SUBJECT_MATCH_REFUSED`. It judges
only an address the caller's tenant filed on its client lane; another tenant's
address, an empty one and governed evidence answer ``subject-unverifiable``
without a byte read.

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
import hashlib
import json
from typing import Protocol, runtime_checkable

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from ccf.artifacts.protocol import (
    ARTIFACT_URI_SCHEME,
    ArtifactName,
    ArtifactRef,
    ArtifactStoreError,
    ArtifactStoreProtocol,
    ArtifactUriUnresolvable,
    WriteKinds,
    artifact_uri,
)
from ccf.authz.actions import ACTION_ARTIFACT_READ, ACTION_ARTIFACT_SUBJECT_MATCH, ACTION_ARTIFACT_WRITE
from ccf.authz.capability import (
    ArtifactRead,
    ArtifactSubjectMatch,
    ArtifactWrite,
    Authorized,
    ReplayMint,
    verify,
)
from ccf.erasure import (
    ErasedContentRefused,
    ErasureIndexProtocol,
    ErasureTrust,
    SubjectMatchAnswer,
    SubjectMatchQuery,
    SubjectMatchVerdict,
    compose_erasure_consult,
    judge_subject,
    reference_approval_verifier,
    subject_match_verdict,
    verify_subject_match_query,
)
from ccf.erasure.approval import PinnedPolicySource
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import AuditLog
from ccf.products.refusal import RefusalEnvelope
from ccf.products.resolver import refuse_incompatible_refusal_recorder
from ccf.replay.record import DecisionReplayRecord
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
    "SUBJECT_MATCH_REFUSED",
    "SUBJECT_MATCH_TOOL",
    "ArtifactPresence",
    "ArtifactResolution",
    "ArtifactSubstrate",
    "NonCanonicalPayload",
    "SubjectMatchRefused",
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

#: The erasure door's subject match (SEC-009; ``D-IMPL-378``, Dave's 16:40 MST
#: item 5 — D3b): a Tool, because it takes the door's whole signed query, and
#: answers one verdict, never bytes. See :func:`build_artifact_server`.
SUBJECT_MATCH_TOOL = "match_artifact_subject"

#: The ONE refusal every caller the subject match does not answer receives,
#: whichever check refused it — no erasure authority for the caller's tenant, a
#: query that is not one, or no signature by that tenant's declared door key over
#: exactly the query. Constant, so the refusal says nothing about the address,
#: the subject or the store; it is raised before the substrate is read.
SUBJECT_MATCH_REFUSED = (
    "the subject match answers the erasure door of the caller's tenant alone: no"
    " signature by that tenant's declared door key verifies over exactly this query"
    " (SEC-009; D-IMPL-378, D3b)"
)

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


class SubjectMatchRefused(PermissionError):
    """The subject match refused its caller: it answers the erasure door of the caller's tenant alone (D3b).

    Its message is always :data:`SUBJECT_MATCH_REFUSED`, and it is raised
    before anything is read from the substrate.
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


def _record_shaped(payload: bytes) -> bool:
    """Whether ``payload`` is a Decision Replay record to the validator SDK readers apply.

    ``DecisionReplayRecord.model_validate_json``: the step
    :func:`ccf.replay.engine.resolve_artifact` ends with, and the parse every
    SDK reader of a record makes. Never a resemblance: bytes that validator
    refuses are no reader's record (the client-lane ruling, ``D-IMPL-378``).
    """
    try:
        DecisionReplayRecord.model_validate_json(payload)
    except ValidationError:
        return False
    return True


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

    Raises:
        ccf.products.resolver.IncompatibleRefusalRecorder: ``refusal_recorder``'s
            ``record`` cannot be passed ``subject_withholding=``, refused before
            anything else is built (Dave's E2 (iii), ``D-IMPL-378``).
    """
    # Dave's E2 (iii) (`D-IMPL-378`): "Detect incompatible recorders at
    # construction, rather than on the first refusal." First, before anything
    # is composed.
    refuse_incompatible_refusal_recorder(refusal_recorder, builder="build_artifact_server")
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
        # (2) What the address IS to the caller's tenant: every name that
        # tenant filed it under, and never another tenant's (C8,
        # D-IMPL-376 (6)) — another tenant's filing of identical bytes does
        # not change this tenant's answer.
        names = store.names_at(content_address=content_address)
        own = [named for named in names if named.tenant_id == authorized.tenant]
        governed = any(
            ReplayMint in store.write_kinds.for_class(named.artifact_class)
            for named in own
        )

        def governed_read() -> bytes | RefusalEnvelope:
            # The governed dereference decides, records and discloses — and
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

        if governed or not own:
            # (3) Governed evidence, another tenant's bytes, or nothing at all.
            return governed_read()
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
        # Dave's E1 (a) (`D-IMPL-378`): "Preserve record content-address
        # integrity." Byte fidelity FIRST (`D-IMPL-89`): the address is the
        # sha256 of the stored canonical bytes, so client-lane bytes that hash
        # to anything else are not the artifact the address names. They never
        # cross as it and decide nothing below: the governed dereference
        # decides them, and its re-hash on arrival answers them exactly as a
        # missing address.
        if hashlib.sha256(payload).hexdigest() != content_address:
            return governed_read()
        if _record_shaped(payload):
            # (5) Bytes on the client lane that validate as a Decision Replay
            # record are not served as a client artifact (the client-lane
            # ruling, D-IMPL-378): the answer would not say which lane served
            # them, and every SDK reader of a record would take them as one.
            # The governed dereference decides them and answers them exactly
            # as a missing address: its provenance check, or for a record
            # claiming another tenant its tenant hold (hold 0), refuses them.
            return governed_read()
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
        address the caller's own tenant filed under a class the deployment
        declared governed answers its names only to a principal the governed
        dereference admits — the same decision, record and disclosure
        :func:`artifact_blob` makes, asked without bytes. A refusal crosses as
        the shell, which the client reads as an unverifiable answer and the
        erasure door as ``class-unverifiable``. Another tenant's filing — of
        any class — takes no part in the decision (C8, ``D-IMPL-376`` (6)), so
        it can neither make this tenant's own naming unverifiable nor tell this
        tenant that some other tenant holds the bytes.
        """
        verify(authorized, kind=ArtifactRead, resource=content_address)
        names = store.names_at(content_address=content_address)
        own = tuple(named for named in names if named.tenant_id == authorized.tenant)
        governed = any(
            ReplayMint in store.write_kinds.for_class(named.artifact_class) for named in own
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

        **It resolves through the consulted store, in the caller's tenant
        view** (FW-6, whole-branch review M-2; SEC-009, ``D-IMPL-374``), like
        the blob, presence and names resources beside it. An address the
        caller's tenant erased answers this resolution's own not-found
        rendering — ``found: false``, no address — so the MCP store client
        refuses to resolve it exactly as the in-process consulting store does
        (CLAUDE.md §7.4: swap the store, nothing else changes). Before this it
        resolved through the raw store and answered ``found: true`` with the
        erased address.
        """
        try:
            address = consulted.scoped(authorized.tenant).resolve_uri(
                uri=artifact_uri(
                    tenant_id=authorized.tenant,
                    artifact_class=artifact_class,
                    name=name,
                    artifact_version=artifact_version,
                )
            )
        except (ArtifactUriUnresolvable, ErasedContentRefused):
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

    # D3b (`D-IMPL-378`): the verifier the door's query signature is checked
    # with — the SDK's reference detached-JWS verifier, the one the consult
    # above verifies the door's record signatures with.
    door_signature_verifier = reference_approval_verifier()

    def the_doors_query(
        authorized: Authorized[ArtifactSubjectMatch],
        *,
        content_address: str,
        subject_ref: str,
        key_paths: list[str],
        subject_ref_salt: str,
        door_signature: str,
    ) -> SubjectMatchQuery:
        """The query, rebuilt under the caller's tenant, if the erasure door of that tenant signed exactly it.

        Reads nothing from the substrate. Every refusal — no authority for the
        tenant, not a query, no signature by the tenant's declared door key over
        it — is the one :class:`SubjectMatchRefused`, audited unresolved.
        """
        authority = erasure_trust.authority_for(authorized.tenant)
        try:
            if authority is None:
                raise ValueError("no erasure authority is declared for the caller's tenant")
            query = SubjectMatchQuery(
                tenant_id=authorized.tenant,
                content_address=content_address,
                subject_ref=subject_ref,
                key_paths=tuple(key_paths),
                subject_ref_salt=subject_ref_salt,
            )
            verify_subject_match_query(
                query,
                door_signature=door_signature,
                authority=authority,
                identity_provider=door_signature_verifier,
            )
        except ValueError:
            audit_log.append(
                action="authz_decision",
                key=authorized.tenant,
                version=ArtifactSubjectMatch.action_id,
                resolved=False,
                occurred_at=entitlement_source.clock(),
                actor=authorized.principal,
                authz_action_id=ArtifactSubjectMatch.action_id,
                authz_resource=ArtifactSubjectMatch.action_id,
            )
            raise SubjectMatchRefused(SUBJECT_MATCH_REFUSED) from None
        return query

    @door.tool(
        name=SUBJECT_MATCH_TOOL,
        action=ACTION_ARTIFACT_SUBJECT_MATCH,
        subject=door.from_grant(),
        resource=door.resource_route(),
        # It writes nothing. Its kind is deliberately not a read kind, and the
        # guard requires such a surface registered mutating: a stated (ambient
        # stdio) identity is refused before any decision is asked for.
        mutating=True,
        products=door.products_unknown(
            "the erasure door's subject match names an address, never a Context Product class"
        ),
    )
    def match_artifact_subject(
        authorized: Authorized[ArtifactSubjectMatch],
        content_address: str,
        subject_ref: str,
        key_paths: list[str],
        subject_ref_salt: str,
        door_signature: str,
    ) -> SubjectMatchAnswer:
        """The erasure door's subject match: a verdict on an address's stored bytes, never the bytes (D3b).

        ``D-IMPL-378``, Dave's 16:40 MST item 5: *"Build the narrowly authorized
        server-side subject-match path without serving the bytes."* The erasure
        door over the MCP-backed store cannot read a client-lane filing the blob
        resource answers as absent — a record-shaped one foremost — so it asks
        here, and gets the verdict the in-process door reaches from the same
        bytes (:func:`~ccf.erasure.judge_subject`, the same function).

        **Authorized three ways, before anything is read.** (1) The deployment's
        authorizer must allow :data:`~ccf.authz.actions.ACTION_ARTIFACT_SUBJECT_MATCH`
        — its own action, granted by name — for the grant's sole tenant (the
        guard, before this body). (2) That tenant must have an
        :class:`~ccf.erasure.ErasureAuthority` in this server's trust. (3) The
        query, rebuilt under the caller's tenant, must carry the signature of
        that authority's declared door key (:func:`~ccf.erasure.verify_subject_match_query`).
        Every refusal past the guard is :class:`SubjectMatchRefused` with
        :data:`SUBJECT_MATCH_REFUSED`, whatever refused.

        **Judged only where the caller's tenant filed the address on its client
        lane.** An address it never filed (another tenant's, or none), and one
        it filed under a class the substrate declares under ``ReplayMint`` —
        governed evidence, read only through the governed dereference — answer
        ``subject-unverifiable`` without a byte read. Otherwise the bytes are
        read from the substrate for this judgment only, as the in-process door
        reads them from its unconsulted store, re-hashed against the address
        before anything is judged, and never leave this function: the answer
        is :class:`~ccf.erasure.SubjectMatchAnswer`, one verdict. Every answer
        appends one ``authz_decision`` audit event naming the address.
        """
        verify(authorized, kind=ArtifactSubjectMatch, resource=ArtifactSubjectMatch.action_id)
        query = the_doors_query(
            authorized,
            content_address=content_address,
            subject_ref=subject_ref,
            key_paths=key_paths,
            subject_ref_salt=subject_ref_salt,
            door_signature=door_signature,
        )
        own = [
            named
            for named in store.names_at(content_address=query.content_address)
            if named.tenant_id == authorized.tenant
        ]
        governed = any(
            ReplayMint in store.write_kinds.for_class(named.artifact_class) for named in own
        )
        verdict: SubjectMatchVerdict = "subject-unverifiable"
        if own and not governed:
            try:
                payload = store.get(content_address=query.content_address)
            except (ArtifactStoreError, KeyError, ValueError):
                pass
            else:
                verdict = subject_match_verdict(judge_subject(payload, query))
        audit_log.append(
            action="authz_decision",
            key=query.content_address,
            version=query.content_address,
            resolved=bool(own) and not governed,
            occurred_at=entitlement_source.clock(),
            actor=authorized.principal,
            artifact_class=own[0].artifact_class if own and not governed else None,
            authz_action_id=ArtifactSubjectMatch.action_id,
            authz_matched_pattern=None,
            authz_resource=query.content_address,
        )
        return SubjectMatchAnswer(verdict=verdict)

    return door.build()
