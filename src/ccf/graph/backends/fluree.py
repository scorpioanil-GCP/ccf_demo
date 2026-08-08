"""Fluree v4 ``GraphStore`` — the RDF/JSON-LD substrate that needed no extra.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 six semantics — physical layout is backend-internal);
and the Phase 15.3 rulings recorded in
``.planning/phases/15.3-fluree-adapter-tier-1-substrate-inserted/15.3-CONTEXT.md``.
**D-IMPL-88** rules Fluree v4 in as a *tier-1* substrate; **D-01** fixes the
write shape (the nine typed operations buffered and committed as one POST),
**D-02** the dialect split (JSON-LD writes, openCypher reads) and **D-03** the
container model (one CCF-owned ledger, ``partition`` and ``tenant_id`` carried
as ordinary predicates rather than as separate physical containers).

**The wire client is never an optional extra.** ``httpx==0.28.1`` is a direct
core pin (``pyproject.toml:44``), so ``import httpx`` sits at module top with
the other imports. This adapter's landing adds no
``[project.optional-dependencies]`` entry, no lazy in-constructor import, no
per-import lint suppression and no ``[[tool.mypy.overrides]]`` block. That
quadruple absence is deliberate SUBQ-14 evidence: the ceremony the ``mongo``
and ``neo4j`` adapters carry is a cost of *their* drivers, not a property of
being an adapter, and this substrate demonstrates it by costing none of it.

**Verified client ↔ server pairing (plan 15.3-01 execution).** Every wire shape
below was probed against a live ``fluree/server:4.1.4`` container — ``/health``
reporting ``4.1.4`` — **before this module existed**, which is D-06's
probe-first split. Two documented shapes were falsified there, and this module
is written against the measurements rather than the documentation: the commit
receipt carries **no** ``flakes_added`` field, and ``X-Fluree-T`` is **not**
sent on the Cypher route. Re-verify before moving either side; D-09 pins the
image exactly and makes a bump a deliberate act.

**Physical model (adapter-owned, D-IMPL-34) — edge-as-node interposition.**
Five node labels and **one** predicate:

* ``(:CcfEntity {ccf_entity_uri, ccf_entity_class, ccf_admit_key, …})`` — the
  node-identity row, widening ``ccf_first_observed_at`` /
  ``ccf_last_observed_at`` and never deleted;
* ``(:CcfEntityClaim {…})`` / ``(:CcfRelationshipClaim {…})`` — the bitemporal
  claim chains, carrying ``ccf_claim_json`` verbatim plus write-time
  projections of the predicate-relevant fields (see ``ccf.graph._writer``);
* ``(:CcfLineage {…})`` — the L-axis entries;
* ``(:CcfEntity)-[:CCF_LINK]-(:CcfEdge)-[:CCF_LINK]-(:CcfEntity)`` — **the
  interposed edge node.** A CCF relationship is not written as a Cypher
  relationship, because on this engine a property-reading relationship
  variable sees only reifier-bundled edges: ``r.prop`` over a plain RDF edge
  evaluates to null, so a hop predicate stated on relationship properties
  returns an empty reached set from a syntactically valid query answering
  ``200`` (15.3-RESEARCH.md §R5 Break 1, Pitfall 7). Compounding it, the only
  bounded variable-length pattern this engine admits is a **single fixed
  type**, undirected — bounded type-alternation and undirected-untyped are
  both deferred upstream (Break 2) — so the CCF relationship type has nowhere
  to live on the edge either. Interposing a node moves every hop predicate
  onto **node** properties, where Cypher reads them reliably, and reduces
  admissibility to membership in a set the adapter already computed. This is
  Mongo's move (``backends/mongo.py:33-42``) with one strict simplification:
  Cypher's ``-[:T]-`` is first-class undirected, so the model is written
  **once** and needs none of Mongo's forward/reverse doubling.

  The walk pattern in plan 15.3-04 reads exactly this layout and the two must
  not drift; the layout is maintained by the write path in
  ``ccf.graph._writer``, inside the same buffered transaction as the
  relationship node it represents, for precisely that reason.

**Timestamps are stored as canonical RFC3339 UTC text, never a temporal
datatype.** Comparison in the conformance suite happens on ``canonical_bytes``
of contracts, and a native temporal type would round-trip at the substrate's
own precision — the cross-backend byte-drift trap (04-RESEARCH.md Pitfall 3).
Canonical text sorts lexicographically as chronologically, which is what keeps
the as-of cut pushable as plain text comparison (`GQ-24` at
docs/GRAPH_QUERY_SEMANTICS.md:482). Probe F-A5 read the datatypes back
directly: every temporal property this adapter writes lands as
``xsd:string``.

**Fluree's ``t`` is transaction time and MUST NOT implement ``as_of``**
(D-IMPL-88). ``t`` is a commit counter — it advances on a data no-op, and it
orders *writes*, not observations. CCF's ``as_of`` is a cut over
``observed_at``, which is data: arbitrary, non-monotone, and frequently
late-arriving. Substituting one for the other is the transaction-time-for-
observation-time error the ruling forbids. ``t`` appears in this module in
exactly one role — threading ``Fluree-Min-T`` for read-after-write — and in no
other.

**Credentials.** The connection URL may carry userinfo, and a deployment may
additionally supply a bearer token. Neither ever reaches
:attr:`FlureeGraphStore.graph_identity`, which is built from
host/port/ledger/partition only (threat T-15.2-05, the T-04-24 postgres
precedent). A bearer token is a **header**, not userinfo: it lives in the
httpx client's default headers and nowhere else — not in the identity string,
not in a docstring, and never in a content-hashed manifest artifact.

**No artifact-authored string ever occupies an IRI position.** This is
Fluree's slot for Mongo's :func:`~ccf.graph.backends.mongo.attribute_field_path`
(threat T-15.2-01) and the closure is stronger, because it is structural
rather than a charset gate. JSON-LD parsing applies a **strict compact-IRI
guard**: a value shaped ``prefix:suffix`` whose prefix is undefined in
``@context`` is rejected at parse time, and a ``@context`` that happened to
define the prefix would instead *silently expand* it into a different
identifier. CCF ``entity_uri`` values are artifact-authored, so some would be
accepted, some rejected, and some silently altered — all three wrong. The rule
this module enforces instead: every ``@id`` is minted by :func:`_mint_id`
(colonless, opaque, content-addressed), every ``@type`` label and every
property name is a code-authored module constant, and ``entity_uri``,
``relationship_type``, ``entity_class`` and every claim attribute travel as
``xsd:string`` **literal values**, where the guard explicitly does not apply.
``opts.strictCompactIri: false`` exists for legacy migrations and must **never**
be set — it re-opens the hazard this rule closes.

**What this module deliberately does not contain: any way to write.** As with
every backend, the write path — the nine typed ``_GraphTxn`` operations as one
buffered JSON-LD batch — lives in ``ccf.graph._writer`` behind the CINV-02
import restriction. A new backend adds a transaction *class* there; it does
not add write operations here. The two transport methods below are transport
in exactly the sense :meth:`MongoGraphStore.collection` and
:meth:`Neo4jGraphStore.session` are.

Every Cypher statement is parameterized; no value is ever rendered into query
text.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from http import HTTPStatus
from types import TracebackType
from typing import Any, ClassVar
from urllib.parse import urlsplit

import httpx

from ccf.contracts.canonical import content_hash
from ccf.graph.reader import BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

#: The public surface is deliberately five names. The physical-layout
#: constants below — labels, the link predicate, the ``ccf_``-prefixed
#: property names, :data:`ADAPTER_CONTEXT`, :func:`_mint_id` — are
#: module-level and importable, because ``ccf.graph._writer`` needs them, but
#: they are **not** public surface: the physical layout is backend-internal by
#: D-IMPL-34, and a deployment that coded against a label would be coding
#: against a decision the adapter reserves the right to change. Same line the
#: Mongo adapter draws around its collection names and the Neo4j adapter
#: around ``ATTRIBUTE_PROPERTY_PREFIX``.
__all__ = [
    "DEFAULT_PARTITION",
    "MAX_DEPTH_CEILING",
    "MAX_QUERY_BODY_BYTES",
    "FlureeGraphReader",
    "FlureeGraphStore",
]

#: Partition the fabric's graph lives in when the caller does not say
#: otherwise. A name, not a tuning value — the SDK ships no domain vocabulary
#: (CINV-01); mirrors ``ccf.graph.backends.postgres.DEFAULT_SCHEMA`` and
#: ``ccf.graph.backends.neo4j.DEFAULT_PARTITION``.
DEFAULT_PARTITION = "ccf"

#: The one CCF-owned ledger (D-03). Ledger-per-partition and ledger-per-tenant
#: were both rejected for v1: one ledger is what makes a single
#: ``Fluree-Min-T`` lane sufficient for read-after-write across every
#: partition a process boots. A ledger name is a Fluree identifier in the URL
#: path and the ``/create`` body — never an IRI position, so its colon is not
#: subject to the strict compact-IRI guard.
DEFAULT_LEDGER = "ccf:main"

#: Documented standalone-server API base, used only when
#: ``/.well-known/fluree.json`` omits ``api_base_url``. The store discovers the
#: value rather than hard-coding it, which is what makes it correct behind a
#: differently-mounted server (15.3-RESEARCH.md §R2).
DEFAULT_API_BASE = "/v1/fluree"

#: ``GET /health`` is at the **server root**, not under the API base.
HEALTH_PATH = "/health"

#: The base-discovery document, read exactly once per store construction.
WELL_KNOWN_PATH = "/.well-known/fluree.json"

#: Wire timeout, in seconds. A mechanism bound on one HTTP client, not a
#: deployment-tunable policy value (CINV-01).
DEFAULT_TIMEOUT = 30.0

# --- the adapter-owned physical model (D-IMPL-34) -----------------------------
#
# Every label, every predicate and every property name below is code-authored
# in full. Nothing here is assembled from caller data, so no artifact-authored
# string can ever reach an IRI position (module docstring, threat T-15.2-01).

#: Node-identity label for the E axis.
L_ENTITY = "CcfEntity"
#: Bitemporal claim-chain labels.
L_ENTITY_CLAIM = "CcfEntityClaim"
L_RELATIONSHIP_CLAIM = "CcfRelationshipClaim"
#: The interposed edge node — see the module docstring.
L_EDGE = "CcfEdge"
#: L-axis entries.
L_LINEAGE = "CcfLineage"

#: The ONE predicate joining an interposed edge node to its two endpoints. A
#: single fixed code-authored type is the only shape a bounded undirected
#: variable-length pattern admits on this engine (§R5 Break 2), and CCF
#: relationship types are artifact-authored vocabulary that must never become
#: pattern text.
LINK_PREDICATE = "CCF_LINK"

#: Scope predicates. D-03 carries ``(partition, tenant_id, …)`` compound
#: identity as properties inside one physical container.
P_PARTITION = "ccf_partition"
P_TENANT = "ccf_tenant_id"

#: Node and claim identity.
P_ENTITY_URI = "ccf_entity_uri"
P_RELATIONSHIP_KEY = "ccf_relationship_key"
P_CLAIM_ID = "ccf_claim_id"
P_CLAIM_JSON = "ccf_claim_json"

#: The temporal axis, all canonical RFC3339 UTC text.
P_OBSERVED_AT = "ccf_observed_at"
P_SUPERSEDED_BY = "ccf_superseded_by"
P_SUPERSEDED_AT = "ccf_superseded_at"
P_VALID_FROM_CMP = "ccf_valid_from_cmp"
P_VALID_TO_CMP = "ccf_valid_to_cmp"
P_FIRST_OBSERVED_AT = "ccf_first_observed_at"
P_LAST_OBSERVED_AT = "ccf_last_observed_at"

#: Arrival order within one node's chain — the graph rendering of SQLite's
#: ``rowid`` in the one role the read path uses it for.
P_SEQ = "ccf_seq"

#: Predicate-relevant write-time projections.
P_POLICY_VERSION = "ccf_policy_bundle_version"
P_ENTITY_CLASS = "ccf_entity_class"
P_RELATIONSHIP_TYPE = "ccf_relationship_type"
P_SUBJECT_URI = "ccf_subject_uri"
P_OBJECT_URI = "ccf_object_uri"

#: The walk's single admissibility property, carried by both ``CcfEntity`` and
#: ``CcfEdge`` nodes so one ``all(n IN nodes(p) WHERE n.ccf_admit_key IN
#: $admissible)`` predicate covers every node on a path. The write path
#: prefixes entity keys ``e:`` and relationship keys ``r:``, which is what
#: makes the two namespaces disjoint — an ``entity_uri`` can never collide
#: with a ``relationship_key`` in plan 15.3-04's one parameter list.
P_ADMIT_KEY = "ccf_admit_key"

#: The multi-valued policy-family key, materialized at write time. Probe F-A6
#: established that this engine's ``c[$key]`` dynamic property access **parses,
#: returns 200 and evaluates to null** — it fails silently, so porting Neo4j's
#: ``_ENTITY_POLICY`` would have made the stage-1 policy family exclude every
#: claim while reporting success. Materializing the key instead turns `GQ-08`'s
#: three cuts into pure membership. See ``_fluree_claim_projection`` in
#: ``ccf.graph._writer`` for the key construction and its argument.
P_POLICY_KEY = "ccf_policy_key"

#: L-axis entry identity.
P_CLAIM_KIND = "ccf_claim_kind"
P_NODE_KEY = "ccf_node_key"
P_LINEAGE_ID = "ccf_lineage_id"
P_ENTRY_JSON = "ccf_entry_json"

#: Prefix under which write-time projections of claim attributes land as node
#: properties (see ``ccf.graph._writer``). The prefix is injective over
#: attribute names and disjoint from every adapter-owned property name, so an
#: artifact-authored attribute can never collide with the physical model.
#: **Deliberately not Neo4j's bare ``attr_``**: this adapter may share a ledger
#: with pre-existing data, and the ``ccf_`` prefix is what keeps every property
#: it writes inside its own namespace.
ATTRIBUTE_PROPERTY_PREFIX = "ccf_attr_"

#: The fixed minimal adapter-owned ``@context`` — deliberately empty.
#:
#: No ``@vocab``, no ``@base`` and no term definitions, therefore **no datatype
#: coercion**: a JSON string value lands as ``xsd:string``, which is the
#: default when nothing says otherwise. This is D-02's hard condition, and it
#: is hard for a reason the empty literal does not show on its face: *"adding
#: ``@vocab`` to a ledger whose data was written bare (or vice versa) changes
#: what every Cypher statement matches"* — reads would silently return nothing
#: while writes kept succeeding (Pitfall 9). Probe F-A5 asserted the
#: consequence directly, reading ``DATATYPE()`` back for all six temporal
#: properties and getting ``xsd:string`` for every one, and asserting that
#: ``GET /context/{ledger}`` stays ``null`` after writes. The store never sets
#: a ledger default context — it does not call the context-setting endpoint at
#: all — and never passes ``?default-context=true``, so D-02's "no default
#: context" is satisfied structurally rather than by discipline.
ADAPTER_CONTEXT: dict[str, object] = {}

#: Mechanism safety bound on the rendered **transaction** body, budgeted under
#: the documented 10 MB server limit (``--max-transaction-size``; ``413 Payload
#: Too Large`` on breach). A buffered commit is one body, and a very large L2
#: admission batch could approach it. The adapter **fails loudly and never
#: splits**: splitting would silently sacrifice the all-or-nothing atomicity
#: D-01 exists to preserve, turning a resource limit into a correctness
#: failure. The margin under 10 MB covers header and framing overhead the
#: rendered-body measurement does not see.
MAX_TXN_BODY_BYTES = 9_000_000

#: Mechanism safety bound on the rendered **query** body, budgeted under the
#: documented 1 MB server limit (``--max-query-size``). ``allowed_entities``
#: travels as a ``$param`` list, so a large survivor set is the shape that
#: approaches it. Same posture as :data:`MAX_DEPTH_CEILING` and the same
#: ratified argument (D-GATE-15.2 checkpoint Q2): a mechanism bound is not a
#: domain value (CINV-01), it bounds the generated request rather than the
#: query vocabulary, and an over-budget query is still **answered** — the
#: translation declines and the memory-bounded fallback answers (D-04; `GQ-29`
#: at docs/GRAPH_QUERY_SEMANTICS.md:554). The decline itself belongs to the
#: read-translation plan; the budget is declared here with the layout it
#: measures.
MAX_QUERY_BODY_BYTES = 900_000

#: Mechanism safety bound on the ONE value a translated statement would inline
#: into query text: the validated traversal-depth literal. Declared here on the
#: Neo4j precedent (``backends/neo4j.py:292-306``) so the read translation
#: lands against a bound that already exists. A ``depth_limit`` above the
#: ceiling is still answered by the fallback (D-04); the ceiling bounds Cypher
#: text, never the query vocabulary.
MAX_DEPTH_CEILING = 100


#: The charset an artifact-authored attribute name must satisfy before it may
#: become a Fluree **predicate**. See :func:`attribute_predicate`.
_ATTRIBUTE_NAME = re.compile(r"[A-Za-z0-9_-]+")


def attribute_predicate(attribute: str) -> str | None:
    """The ONE site where an artifact-authored attribute name becomes an IRI.

    The Fluree twin of
    :func:`ccf.graph.backends.mongo.attribute_field_path` (threat T-15.2-01),
    and the reason this adapter needs one at all despite the module docstring's
    "no artifact-authored string ever occupies an IRI position" rule.

    ``EntityClaim.attributes`` is typed ``Mapping[str, str]`` and documented as
    *"an opaque, deployment-defined attribute map — the SDK never enumerates
    its keys"*, so an attribute **name** is arbitrary artifact-authored text.
    Everywhere else in this adapter such text travels as a *value*, where it is
    inert. Here it cannot: a projected attribute is addressed by its
    **predicate**, and the strict compact-IRI guard applies to predicate
    positions. A name containing ``:`` reads as a compact IRI whose prefix is
    undefined and Fluree **rejects the whole transaction at parse time** — so
    an ungated projection would refuse admission of a perfectly legal CCF
    claim, and would do it to the entire buffered batch rather than to the one
    attribute.

    A name is therefore admitted only when it matches ``^[A-Za-z0-9_-]+$``,
    which excludes ``:`` and ``.`` by construction rather than by a blocklist,
    and the answer is the prefixed predicate. A name outside the charset
    returns ``None`` and is simply not projected. **Nothing is lost and no
    predicate is weakened:**

    * ``claim_json`` still carries the attribute verbatim, and the fallback
      reads it from there (D-04 — the answer is identical, the path differs);
    * the policy family does not depend on this projection at all. Probe F-A6
      established that ``c[$key]`` dynamic property access fails *silently* on
      this engine, so the classification cut is pushed as membership over the
      multi-valued :data:`P_POLICY_KEY` instead — and a policy key is a
      **literal value** encoding ``(class, attribute, value)``, which is safe
      for every attribute name including the ones refused here.

    So unlike the Mongo rule, refusing a name here costs no pushdown on the
    predicate family that actually matters.
    """
    if _ATTRIBUTE_NAME.fullmatch(attribute) is None:
        return None
    return ATTRIBUTE_PROPERTY_PREFIX + attribute


class FlureeTransactionTooLarge(RuntimeError):
    """A buffered commit body exceeded the server's transaction size limit.

    Deliberately outside ``__all__`` on the same line the physical-layout
    constants sit outside it: importable by ``ccf.graph._writer``, not public
    surface. Raised rather than worked around — see :data:`MAX_TXN_BODY_BYTES`
    for why splitting the batch is not an option.
    """


def _graph_identity(url: str, *, ledger: str, partition: str) -> str:
    """Name the graph a URL points at, without carrying its credentials.

    The single-writer boot check keys on this string, so it has to be stable
    and it has to distinguish two graphs — but it is also the string that ends
    up in exception messages, which is why the userinfo is dropped rather than
    merely "not usually shown" (threat T-15.2-05; the T-04-24 postgres
    precedent). A bearer token never appears here at all, because it is a
    header rather than part of the URL. Two partitions in one ledger are two
    graphs, exactly as two Postgres schemas are.
    """
    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    port = parts.port or 8090
    return f"fluree://{host}:{port}/{ledger}#{partition}"


def _server_root(url: str) -> str:
    """The scheme/host/port origin of ``url``, with userinfo removed.

    The httpx client is built on this rather than on the supplied URL, so a
    credentialed URL's userinfo does not survive into request lines, redirect
    targets or connection-pool keys.
    """
    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    return parts._replace(
        netloc=netloc, path="", query="", fragment=""
    ).geturl()


def _mint_id(kind: str, *parts: str) -> str:
    """Mint the ``@id`` of one node — the ONE site that produces an identifier.

    An ``@id`` is an **IRI position**, and JSON-LD parsing applies a strict
    compact-IRI guard there: a value shaped ``prefix:suffix`` whose prefix is
    undefined in ``@context`` is rejected at parse time, while a ``@context``
    that *did* define the prefix would silently expand it into a different
    identifier. A CCF ``entity_uri`` is artifact-authored, so it can be any of
    those three — which is why it travels as an ``xsd:string`` literal value on
    :data:`P_ENTITY_URI` and **never** as an identifier.

    What comes back is therefore colonless, opaque and adapter-minted:
    ``ccf_<kind>_<sha256 of the supplied parts>``, content-addressed through
    :func:`ccf.contracts.canonical.content_hash` so the same node identity
    always mints the same ``@id`` — which is what makes a re-admission
    re-assert byte-identical triples and lets RDF set semantics render it a
    data no-op.
    """
    return f"ccf_{kind}_{content_hash(list(parts))}"


class FlureeGraphStore:
    """Connection and ledger owner for the Fluree v4 backend — no extra needed.

    Args:
        url: Server URL (``http://host:8090``), optionally carrying userinfo.
            Supplied by the deployment (typically from an environment
            variable); never committed, never logged, and never echoed back
            through :attr:`graph_identity`.
        partition: Which graph in this ledger this store attaches to. Two
            partitions in one ledger are two graphs — what lets one server
            host several fabrics, and what makes the single-writer check
            meaningful per fabric rather than per server (the Postgres
            ``schema`` argument's role, exactly).
        ledger: The CCF-owned ledger (D-03). Bootstrapped idempotently at
            construction; every boot after the first sees ``409``.
        bearer_token: Optional bearer credential. Held **only** in the httpx
            client's default headers — never in :attr:`graph_identity`, never
            in the URL, and never in a content-hashed manifest artifact
            (threats T-15.2-05 / T-04-24; the manifest carries the backend
            *kind* only).

    As with every backend store, this is *not* a store offering both halves of
    the Protocol: it offers :attr:`reader`, and the transport surface to the
    writer module alone.

    Raises:
        httpx.HTTPError: When the server is unreachable or refuses the
            bootstrap. Raised at construction rather than at first read: a
            store that cannot reach its server is a broken deployment
            (exception), never a refusal.
    """

    def __init__(
        self,
        *,
        url: str,
        partition: str = DEFAULT_PARTITION,
        ledger: str = DEFAULT_LEDGER,
        bearer_token: str | None = None,
    ) -> None:
        self._partition = partition
        self._ledger = ledger
        # Derived BEFORE any client exists, so the credential-free string is
        # not reachable from the credentialed one.
        self._identity = _graph_identity(
            url, ledger=ledger, partition=partition
        )
        headers = {"Content-Type": "application/json"}
        if bearer_token is not None:
            # The token's one and only home. It is a header, not userinfo.
            headers["Authorization"] = f"Bearer {bearer_token}"
        self._client = httpx.Client(
            base_url=_server_root(url),
            timeout=DEFAULT_TIMEOUT,
            headers=headers,
        )
        # Fail at construction, not at first read. `/health` is at the server
        # root, NOT under the API base.
        self._client.get(HEALTH_PATH).raise_for_status()
        # One GET, and it makes the store correct behind a differently-mounted
        # server.
        discovered = self._client.get(WELL_KNOWN_PATH)
        discovered.raise_for_status()
        base = str(discovered.json().get("api_base_url") or "")
        self._base = base or DEFAULT_API_BASE
        # D-03's idempotent bootstrap: one CCF-owned ledger, created on the
        # first boot and answered `409 Conflict` on every boot after it. Probe
        # F-A1 assertion (3) proved the 201-then-409 sequence. `POST /create`
        # has no context parameter, and the context-setting endpoint is never
        # called, so the ledger has no default context by construction (D-02).
        created = self._client.post(
            f"{self._base}/create",
            content=json.dumps({"ledger": ledger}),
        )
        if created.status_code != HTTPStatus.CONFLICT:
            created.raise_for_status()
        #: Highest transaction time this store has written. Threaded into
        #: `Fluree-Min-T` on every read so read-after-write is exact. Note it
        #: is only ever *written* from a commit receipt: `X-Fluree-T` is not
        #: sent on the Cypher route by this build (measured, plan 15.3-01), so
        #: nothing here reads it back.
        self._min_t = 0
        self._reader = FlureeGraphReader(self)

    @property
    def graph_identity(self) -> str:
        """Credential-free identity of the graph this store is attached to."""
        return self._identity

    @property
    def partition(self) -> str:
        """The partition this store's graph lives in."""
        return self._partition

    @property
    def ledger(self) -> str:
        """The CCF-owned ledger this store's graphs live in (D-03)."""
        return self._ledger

    @property
    def reader(self) -> FlureeGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    def scope(self, tenant_id: str) -> dict[str, str]:
        """The two scope parameters every statement of this graph binds.

        One helper rather than two literals per statement: the partition is
        what keeps a reader from answering out of another fabric's graph in the
        same ledger, and a statement that forgot it would still return
        plausible rows.
        """
        return {"partition": self._partition, "tenant": tenant_id}

    def post_query(
        self, cypher: str, params: dict[str, object]
    ) -> list[dict[str, Any]]:
        """Run one parameterized Cypher read and return its rows as dicts.

        Transport, in exactly the sense
        :meth:`~ccf.graph.backends.mongo.MongoGraphStore.collection` and
        :meth:`~ccf.graph.backends.neo4j.Neo4jGraphStore.session` are: reachable
        in principle by any importer, which is why the write *operations* live
        behind the CINV-02 lint in ``ccf.graph._writer``. DESIGN.md §9: no
        unforced path exists, and every forced path fails CI or fails at boot.

        The body is the ``{"cypher": …, "params": …}`` envelope under
        ``Content-Type: application/cypher``. Because it is Cypher rather than
        a JSON-LD query document, the ``Fluree-Min-T`` **header** is the only
        read-after-write form available — ``opts.min-t`` lives in a JSON-LD
        body. A read-after-write timeout **raises**: degrading would answer
        from a stale ``t``, which is a silent correctness failure, and under
        CCF's rules an unreachable guarantee is a broken deployment rather than
        a refusal.

        Row extraction is written against the envelope **recorded verbatim by
        probe F-A1**, not against documentation — ``query/output-formats.md``
        describes JSON-LD, SPARQL-JSON, typed-JSON and AgentJson and says
        nothing about cypher-json's row structure. What comes back is the
        Neo4j-HTTP tabular envelope::

            {"results":[{"columns":["entity_uri"],
                         "data":[{"row":["counterparty://acme"],
                                  "meta":[null]}]}]}

        ``dict(zip(columns, row))`` is what makes rows satisfy
        :class:`ccf.graph.reader.Row` for
        :func:`ccf.graph.reader.materialize_view`, exactly as
        ``Neo4jGraphReader._query``'s ``dict(record)`` does.
        """
        response = self._client.post(
            f"{self._base}/query/{self._ledger}",
            headers={
                "Content-Type": "application/cypher",
                "Fluree-Min-T": str(self._min_t),
            },
            content=json.dumps({"cypher": cypher, "params": params}),
        )
        response.raise_for_status()
        result = response.json()["results"][0]
        columns: Sequence[str] = result["columns"]
        return [
            dict(zip(columns, entry["row"], strict=True))
            for entry in result["data"]
        ]

    def post_update(self, body: dict[str, object]) -> dict[str, Any]:
        """Apply one JSON-LD transaction and return its commit receipt.

        Transport, on the same terms as :meth:`post_query` — this is not a
        write *operation*; the nine typed operations live in
        ``ccf.graph._writer`` and nowhere else (CINV-02).

        One POST is one atomic commit (measured, probe F-A4(b): a body touching
        three distinct subjects advanced ``t`` by exactly one). The receipt's
        ``t`` is threaded into :data:`Fluree-Min-T` for every subsequent read.

        Raises:
            FlureeTransactionTooLarge: When the rendered body exceeds
                :data:`MAX_TXN_BODY_BYTES`, or when the server answers ``413``.
                **Fail loudly, never split** — see :data:`MAX_TXN_BODY_BYTES`.
        """
        rendered = json.dumps(body)
        size = len(rendered.encode("utf-8"))
        if size > MAX_TXN_BODY_BYTES:
            raise FlureeTransactionTooLarge(
                f"transaction body is {size} bytes, over this adapter's"
                f" {MAX_TXN_BODY_BYTES}-byte budget under the server's"
                " documented 10 MB (--max-transaction-size) limit;"
                " the batch is not split because that would sacrifice the"
                " all-or-nothing atomicity of one commit"
            )
        response = self._client.post(
            f"{self._base}/update/{self._ledger}",
            content=rendered,
        )
        if response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
            raise FlureeTransactionTooLarge(
                f"server refused a {size}-byte transaction body with 413;"
                " the documented limit is 10 MB (--max-transaction-size)"
            )
        response.raise_for_status()
        receipt: dict[str, Any] = response.json()
        self._min_t = max(self._min_t, int(receipt["t"]))
        return receipt

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> FlureeGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class FlureeGraphReader(BaseGraphReader):
    """``GraphReader`` over a Fluree ledger — dialect and rows only.

    Identical semantics to every other backend reader by construction: the five
    acquisition reads below are Cypher renderings of the same five reads the
    SQL backends express, the rows they answer are plain dicts satisfying
    :class:`ccf.graph.reader.Row`, and everything above the rows —
    lineage-at-boundary, supersession-as-of, record construction, view ordering
    — is inherited from :class:`ccf.graph.reader.BaseGraphReader` and the
    substrate-neutral materialization core, so the semantics cannot fork here
    (15.2-RESEARCH.md Pitfall 5).

    **Two shapes inside these statements were probed, not assumed.** Multi-key
    ``ORDER BY`` over a string key then an integer key (assumption **A11**) and
    the inline map pattern ``(c:Label {prop: $p0})`` (assumption **A12**) both
    **PASSED** against ``fluree/server:4.1.4`` in plan 15.3-01: two claims
    sharing one ``ccf_observed_at`` arrive in ``ccf_seq`` order, and the inline
    form returns the same count as the ``WHERE``-clause form of the same query.
    So the statements order on both keys with no Python-side stable sort, and
    use the inline form as copied from ``backends/neo4j.py:519-565``.

    :meth:`_translate_query` is **not implemented here**; it belongs to the
    read-translation plan. Until it lands the reader answers every query
    through the inherited fallback, which is fully conformant under D-04 — the
    fallback's answer is the definition, and pushdown is an earned optimization
    visible only in telemetry (`GQ-34` at
    docs/GRAPH_QUERY_SEMANTICS.md:609).

    Positional parameters map onto ``$p0…$pN`` in statement order; the store's
    partition rides along as ``$partition`` on every statement, so a reader can
    never answer from another fabric's graph in the same ledger.
    """

    SELECT_LINEAGE: ClassVar[str] = """
        MATCH (l:CcfLineage {ccf_partition: $partition, ccf_tenant_id: $p0,
                             ccf_claim_kind: $p1, ccf_node_key: $p2,
                             ccf_claim_id: $p3})
        RETURN l.ccf_entry_json AS entry_json
    """
    SELECT_ENTITY_HISTORY: ClassVar[str] = """
        MATCH (c:CcfEntityClaim {ccf_partition: $partition,
                                 ccf_tenant_id: $p0, ccf_entity_uri: $p1})
        RETURN c.ccf_entity_uri AS entity_uri, c.ccf_claim_id AS claim_id,
               c.ccf_claim_json AS claim_json,
               c.ccf_policy_bundle_version AS policy_bundle_version,
               c.ccf_superseded_by AS superseded_by,
               c.ccf_superseded_at AS superseded_at
        ORDER BY c.ccf_observed_at, c.ccf_seq
    """
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str] = """
        MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                       ccf_tenant_id: $p0,
                                       ccf_relationship_key: $p1})
        RETURN c.ccf_relationship_key AS relationship_key,
               c.ccf_claim_id AS claim_id,
               c.ccf_claim_json AS claim_json,
               c.ccf_policy_bundle_version AS policy_bundle_version,
               c.ccf_superseded_by AS superseded_by,
               c.ccf_superseded_at AS superseded_at
        ORDER BY c.ccf_observed_at, c.ccf_seq
    """
    SELECT_ENTITIES_AS_OF: ClassVar[str] = """
        MATCH (c:CcfEntityClaim {ccf_partition: $partition,
                                 ccf_tenant_id: $p0})
        WHERE c.ccf_observed_at <= $p1
          AND (c.ccf_superseded_at IS NULL OR c.ccf_superseded_at > $p2)
        RETURN c.ccf_entity_uri AS entity_uri, c.ccf_claim_id AS claim_id,
               c.ccf_claim_json AS claim_json,
               c.ccf_policy_bundle_version AS policy_bundle_version,
               c.ccf_superseded_by AS superseded_by,
               c.ccf_superseded_at AS superseded_at
        ORDER BY c.ccf_entity_uri
    """
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str] = """
        MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                       ccf_tenant_id: $p0})
        WHERE c.ccf_observed_at <= $p1
          AND (c.ccf_superseded_at IS NULL OR c.ccf_superseded_at > $p2)
        RETURN c.ccf_relationship_key AS relationship_key,
               c.ccf_claim_id AS claim_id,
               c.ccf_claim_json AS claim_json,
               c.ccf_policy_bundle_version AS policy_bundle_version,
               c.ccf_superseded_by AS superseded_by,
               c.ccf_superseded_at AS superseded_at
        ORDER BY c.ccf_relationship_key
    """

    def __init__(self, store: FlureeGraphStore) -> None:
        self._store = store

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        """Run one parameterized Cypher read and return its rows as dicts.

        Positional values bind as ``$p0…$pN``; ``$partition`` is supplied from
        the store on every statement. Every value is a request parameter —
        nothing is rendered into statement text.
        """
        bound: dict[str, object] = {
            f"p{index}": value for index, value in enumerate(params)
        }
        bound["partition"] = self._store.partition
        return self._store.post_query(sql, bound)
