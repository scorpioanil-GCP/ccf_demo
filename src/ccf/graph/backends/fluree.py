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
  Mongo's move (``src/ccf/graph/backends/mongo.py::TRAVERSAL_EDGES``, whose
  module docstring states the doubling) with one strict simplification:
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

**Three temporal axes, named by ``ccf.graph.protocols.TEMPORAL_AXES``, and
``t`` is only ever the second** (D-IMPL-88; ledger rows ``24.5-L-03`` /
``24.5-L-04``). The three, in that vocabulary's order: **event time** is when
the world changed — a claim's ``observed_at`` and its validity window, which
on this substrate is what the backdatable ``@iso:`` addressing speaks;
**transaction time** is when the store recorded it — Fluree's ``t``, a commit
counter that advances on a data no-op and orders *writes*, not observations;
and CCF's **as_of** is a cut over ``observed_at``, which is data: arbitrary,
non-monotone, and frequently late-arriving. Substituting ``t`` for ``as_of``
is the transaction-time-for-observation-time error the ruling forbids, and
this module never does it: the pin bounds the STORE, never the observations.

``t`` appears in this module in **two** roles, both on the transaction-time
axis and neither a temporal cut (D-IMPL-240 (2), ``24.5-L-01``):

* the **FLOOR** — ``Fluree-Min-T`` threaded on the openCypher route by
  :meth:`FlureeGraphStore.post_query`, so read-after-write is exact. A floor
  is a lower bound: on a ledger that has advanced it answers the head;
* the **PIN** — ``from: <ledger>@t:N`` on the JSON-LD route by
  :meth:`FlureeGraphStore.post_query_pinned`, an upper bound distinct from the
  floor, answered by :meth:`FlureeGraphReader.query_pinned` through the
  substrate-neutral fallback. Measured (2026-09-02, ``fluree/server:4.1.4``):
  the Cypher route silently ignores every pin form — header and body alike —
  so the pinned read is a declared second dialect beside D-02's split
  (JSON-LD writes and pinned reads; openCypher unpinned reads). A pin past
  the head is ``408 err:db/ReadAfterWriteTimeout`` and surfaces as
  :class:`FlureePinAhead`.

Under either role, ``q.as_of`` still applies to every answer (``GQ-07``); the
pin is typed :class:`~ccf.graph.protocols.StoreSnapshotPin` precisely so that
``GraphQuery.as_of`` cannot accept it and :meth:`FlureeGraphReader.query_pinned`
refuses an instant offered as a pin.

**Credentials — two channels, exactly one at a time.** The connection URL may
carry userinfo, or the deployment may supply a ``bearer_token``. Userinfo
becomes an HTTP **Basic** ``Authorization`` header and the token becomes a
**Bearer** one; both are computed by :func:`_authorization`, and supplying
both is **refused** rather than resolved by precedence. Both are reachable
from ``boot()`` and ``load_and_boot()`` — the userinfo through this adapter's
``url`` connection setting, the token through the ``secrets`` mapping under
the field this adapter declares in
:attr:`~ccf.graph.registry.BackendRegistration.secret_fields`.

Whichever channel is used, the credential's one and only home is the httpx
client's default headers. It never reaches
:attr:`FlureeGraphStore.graph_identity`, which is built from
host/port/ledger/partition only (threat T-15.2-05, the T-04-24 postgres
precedent); it never survives into a request line, because the client is
built on the credential-free origin :func:`_server_root` returns; and it is
never interpolated into any exception this module raises, so it reaches no
log, no error and no content-hashed manifest artifact.

**Correction (WR-02/WR-03, 2026-08-09).** Until this fix userinfo was stripped
and then *discarded*: httpx 0.28.1 derives no ``Authorization`` header from a
``base_url``'s userinfo (measured), and ``bearer_token`` was reachable from no
supported boot path. A credentialed URL therefore connected **anonymously**
while three documents presented one channel or the other as the credential.
The rule now enforced is the
``src/ccf/graph/backends/neo4j.py::_split_credentials`` precedent this module
always cited: userinfo a caller supplied is *used*, never silently dropped.

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
from base64 import b64encode
from collections.abc import Sequence
from http import HTTPStatus
from types import TracebackType
from typing import Any, ClassVar, Final
from urllib.parse import unquote, urlsplit

import httpx

from ccf.contracts.canonical import canonical_timestamp, content_hash
from ccf.graph import fallback
from ccf.graph.protocols import GraphQuery, GraphView, StoreSnapshotPin
from ccf.graph.reader import (
    BaseGraphReader,
    Row,
    _LineageRowsFor,
    _ordered_view,
    materialize_view,
)

__ccf_mode__ = "algorithmic"

#: The public surface is deliberately seven names. The physical-layout
#: constants below — labels, the link predicate, the ``ccf_``-prefixed
#: property names, :data:`ADAPTER_CONTEXT`, :func:`_mint_id` — are
#: module-level and importable, because ``ccf.graph._writer`` needs them, but
#: they are **not** public surface: the physical layout is backend-internal by
#: D-IMPL-34, and a deployment that coded against a label would be coding
#: against a decision the adapter reserves the right to change. Same line the
#: Mongo adapter draws around its collection names and the Neo4j adapter
#: around ``ATTRIBUTE_PROPERTY_PREFIX``. :data:`FLUREE_SUBSTRATE` and
#: :class:`FlureePinAhead` joined in Phase 24.5 (``24.5-L-01``): the first is
#: the vocabulary a :class:`~ccf.graph.protocols.StoreSnapshotPin` names this
#: adapter by, the second is what a caller catches when a pin is ahead of the
#: ledger — both are things a deployment legitimately writes code against.
__all__ = [
    "DEFAULT_PARTITION",
    "FLUREE_SUBSTRATE",
    "MAX_DEPTH_CEILING",
    "MAX_QUERY_BODY_BYTES",
    "FlureeGraphReader",
    "FlureeGraphStore",
    "FlureePinAhead",
]

#: The substrate name a :class:`~ccf.graph.protocols.StoreSnapshotPin` minted
#: by this adapter carries, and the only one :meth:`FlureeGraphReader.
#: query_pinned` accepts. A name, not a tuning value (CINV-01).
FLUREE_SUBSTRATE: Final[str] = "fluree"

#: The branch a ledger name without a ``:`` lives on, as the server lists it
#: under ``GET …/ledgers`` (``{"name": "ccf", "branch": "main", "t": N}`` for
#: :data:`DEFAULT_LEDGER`). A ledger name is ``name`` or ``name:branch`` — the
#: server's own ``Invalid ledger ID format`` message states the two forms —
#: so :meth:`FlureeGraphStore.head_t` matches BOTH parts: the listing carries
#: every branch of every ledger on the server, and a match on ``name`` alone
#: would answer the head of whichever branch the server listed first.
DEFAULT_BRANCH: Final[str] = "main"

#: The ``@type`` substring identifying a pin past the ledger head, **measured**
#: (2026-09-02, ``fluree/server:4.1.4``) rather than taken from documentation:
#: ``408 {"error": "Ledger has not reached t=3, current t=2", "status": 408,
#: "@type": "err:db/ReadAfterWriteTimeout"}``. The same type the Cypher
#: route's ``Fluree-Min-T`` raises on a floor past the head — one server
#: condition, reachable from both roles of ``t``.
PIN_AHEAD_MARKER: Final[str] = "ReadAfterWriteTimeout"

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
#: differently-mounted **API base** (15.3-RESEARCH.md §R2). Note the bound,
#: made explicit by WR-02: that is the API base *beneath* the origin, not a
#: differently-mounted server root — the discovery document is itself read
#: from the origin, so a root-mounted path is refused by :func:`_server_root`
#: rather than silently dropped.
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

#: Field separator inside a materialized policy key. ``NUL`` is deliberate: it
#: is code-authored, and no *well-formed* class name, attribute name or
#: classification value contains one — but "well-formed" is a convention, not a
#: contract. All three components are artifact-authored and none is charset
#: validated, so the separator alone forges nothing: the guard is
#: :func:`policy_key`, which refuses to build a key from **any** of the three
#: components containing this character. (Until the CR-01 correction of
#: 2026-08-09 this note claimed the class side was safe by construction and the
#: guard covered only the other two — the false premise that produced a pushed
#: answer admitting a claim the fallback excluded. See :func:`policy_key`.)
#:
#: The write half of the pair lives in ``ccf.graph._writer`` (that module
#: imports this one; the reverse would break the CINV-02 confinement and
#: cycle), so the two constructions are held identical by an executable
#: assertion rather than by comment —
#: ``tests/graph/test_fluree_backend.py::
#: test_the_write_path_materializes_exactly_the_key_the_read_path_pushes``
#: projects a real claim through the writer and compares it against
#: :func:`policy_key`. A separator that drifted would otherwise produce a
#: policy family that silently matches nothing, which is the same silent-failure
#: class probe F-A6 caught.
POLICY_KEY_SEPARATOR = "\x00"

#: Namespace prefixes on :data:`P_ADMIT_KEY`, read side. These are what make an
#: ``entity_uri`` and a ``relationship_key`` incapable of colliding inside the
#: walk's single ``$admissible`` parameter list.
#:
#: The write half lives in ``ccf.graph._writer`` (that module imports this one;
#: the reverse would break the CINV-02 confinement and cycle), so — exactly as
#: for :data:`POLICY_KEY_SEPARATOR` — the two constructions are held identical
#: by an executable assertion rather than by comment:
#: ``tests/graph/test_fluree_backend.py::
#: test_the_write_path_materializes_exactly_the_admit_keys_the_walk_pushes``
#: reads both keys back off the server and compares them against these. A
#: drifted prefix would otherwise produce a walk whose ``all(...)`` predicate
#: is false for every path — an **empty reached set with a 200**, which is the
#: same silent-failure class probe F-A6 caught and the exact shape do-not-copy
#: #1 warns about.
ENTITY_ADMIT_PREFIX = "e:"
RELATIONSHIP_ADMIT_PREFIX = "r:"

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
#: at docs/GRAPH_QUERY_SEMANTICS.md:554). The decline is applied by
#: :meth:`FlureeGraphReader._within_body_budget`, against the exact bytes
#: :meth:`FlureeGraphStore.post_query` would send.
MAX_QUERY_BODY_BYTES = 900_000

#: Mechanism safety bound on the ONE value a translated statement inlines into
#: query text: the validated traversal-depth literal. Declared here on the
#: Neo4j precedent (``src/ccf/graph/backends/neo4j.py::MAX_DEPTH_CEILING``,
#: whose own comment states the bound) so the read translation
#: lands against a bound that already exists. A ``depth_limit`` above the
#: ceiling is still answered by the fallback (D-04); the ceiling bounds Cypher
#: text, never the query vocabulary. **Applied to the CCF depth, before
#: :func:`_reach_pattern` doubles it** — see that function.
MAX_DEPTH_CEILING = 100

#: The substring identifying a path-enumeration cap refusal, **measured** by
#: probe F-A3(c) rather than taken from documentation. The full message on
#: ``fluree/server:4.1.4`` is ``"Query error: Resource limit exceeded: path
#: enumeration exceeded max paths (1000); narrow the pattern (tighter hop
#: bounds, a bound end node, or a specific type)"`` under
#: ``"@type":"err:db/InvalidQuery"``.
#:
#: The cap **errors rather than truncating**, which is why it needs an answer
#: at all: a truncating cap would silently narrow a reached set, while an
#: erroring one is a hard failure the adapter can convert into a decline. The
#: match is deliberately the resource-limit phrase rather than the full text —
#: any resource-limit refusal of the walk is answerable the same way, and
#: pinning the parenthesised ``1000`` would bind the adapter to a server
#: default. It is deliberately **not** ``err:db/InvalidQuery``, which also
#: covers genuine statement defects that must keep failing loudly.
PATH_CAP_MARKER = "Resource limit exceeded"


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


def policy_key(entity_class: str, attribute: str, value: str) -> str | None:
    """One materialized `GQ-08` classification key, or ``None`` if unforgeable.

    The read half of the write-time materialization probe F-A6 forced (see
    :data:`P_POLICY_KEY`): ``(entity_class, attribute_name, attribute_value)``
    joined by :data:`POLICY_KEY_SEPARATOR`, so that `GQ-08`'s classification
    cut is a set-membership test over stored literals instead of the dynamic
    property access this engine evaluates to null.

    **Why a component may be refused.** A separator-joined encoding is only
    injective if no component contains the separator, and **all three
    components are artifact-authored**. A class name is user-declared ontology
    vocabulary carried as a bare ``str`` on
    :class:`~ccf.contracts.claims.EntityClaim` with no charset validation, an
    attribute *name* comes from *"an opaque, deployment-defined attribute map —
    the SDK never enumerates its keys"*, and a classification *value* is
    likewise deployment data. A ``NUL`` in **any** of the three could make two
    different triples encode to one key — a pushed answer admitting a claim the
    fallback excludes (threats T-15.2-01 / T-15.2-03, and precisely the
    divergence the differential bar exists to catch). Rather than trust that a
    ``NUL`` cannot occur, this function refuses to encode one and the caller
    declines the translation, so the fallback answers the whole query (D-04;
    `GQ-29` at docs/GRAPH_QUERY_SEMANTICS.md:554). Nothing is lost: the answer
    is identical, only the path differs.

    **All three, not two — the CR-01 correction (2026-08-09).** As first
    shipped this guard covered ``attribute`` and ``value`` only, on the premise
    that *"the class name is safe by construction"*. That premise was false,
    and the whole injectivity argument below rested on it. Reproduced against
    the shipped code: a claim ``entity_class="A"``, ``attributes={"B\\0C": "D"}``
    materializes the stored key ``"A\\0B\\0C\\0D"``, and a query
    ``classification_attribute_by_class={"A\\0B": "C"}`` with
    ``permitted_classifications={"D"}`` built the *identical* pushed key — so
    ``c.ccf_policy_key IN $policy_keys`` returned a claim
    :func:`~ccf.graph.fallback._admissible_entity` excludes, because the
    claim's own class ``"A"`` has no declared classification attribute. That is
    over-disclosure by the pushed path: the exact T-15.2-03 divergence.

    Refusing on the *read* side is sufficient to make matching exact, and the
    argument is now sound because the premise it needs is established rather
    than assumed:

    * every key built here carries **exactly two** separators, since all three
      components were checked;
    * a stored key whose components smuggled in *k* extra separators carries
      ``2 + k``, so it can never equal one built here;
    * a stored key carrying exactly two therefore had separator-free
      components, and a two-separator string splits into
      ``(class, attribute, value)`` one way only.

    So a read key matches a stored key iff the two triples are equal. The write
    half in ``ccf.graph._writer`` needs no gate of its own: an unencodable
    stored key is simply unreachable from here, which is the fail-closed
    direction, and the claim is answered by the fallback.
    """
    if any(
        POLICY_KEY_SEPARATOR in part
        for part in (entity_class, attribute, value)
    ):
        return None
    return POLICY_KEY_SEPARATOR.join((entity_class, attribute, value))


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
    targets or connection-pool keys. Measured against the pinned httpx 0.28.1:
    a client whose ``base_url`` carries userinfo emits it **in the request URL**
    and derives **no** ``Authorization`` header from it — so stripping it here
    is necessary, and :func:`_authorization` is what keeps it a *credential*
    rather than a discarded one (WR-02).

    Anything below the origin is **refused, not silently trimmed**. Every
    request this store issues is rooted here — ``/health`` and
    ``/.well-known/fluree.json`` at the origin, the discovered API base beneath
    it — so a path-mounted server is genuinely unreachable through this store,
    and quietly dropping the path turns "unreachable" into "connected to a
    different server than the caller named". None of ``path``, ``query`` or
    ``fragment`` can carry userinfo, so naming them in the message leaks
    nothing.

    Raises:
        ValueError: the URL carries a path, query or fragment.
    """
    parts = urlsplit(url)
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError(
            "fluree_url must be a bare server origin (scheme://host:port);"
            f" got path={parts.path!r} query={parts.query!r}"
            f" fragment={parts.fragment!r}. Every request this store issues is"
            " rooted at the origin, so anything below it would be dropped"
            " rather than honoured — and a component the caller supplied and"
            " the store silently discarded is the WR-02 failure mode"
        )
    host = parts.hostname or "localhost"
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    return parts._replace(
        netloc=netloc, path="", query="", fragment=""
    ).geturl()


def _authorization(url: str, bearer_token: str | None) -> str | None:
    """The ``Authorization`` header value the supplied credentials stand for.

    Two channels reach this store and **exactly one may be used at a time**:

    * **URL userinfo** — ``http://user:pass@host:8090`` — becomes HTTP Basic.
      This is the Fluree rendering of what ``_split_credentials`` does with a
      Bolt URI at ``ccf.graph.backends.neo4j:151-165``: userinfo a caller
      supplied is *used*, never discarded. Fluree's wire is HTTP, so the
      credential's home is a header rather than a driver ``auth`` argument,
      but the rule is the precedent's. The two halves are percent-decoded
      first, because a password containing ``@`` or ``:`` cannot be written
      into a URL any other way (RFC 3986 §3.2.1).
    * **``bearer_token``** — becomes ``Bearer <token>``, unchanged.

    Supplying **both** is refused rather than resolved by precedence. A store
    that silently preferred one would authenticate as an identity the
    deployment did not unambiguously ask for, and "which credential won" is
    exactly the question an audit cannot afford to answer by convention.

    Returns ``None`` when neither is supplied. That is an anonymous connection
    the caller *asked* for — a different thing from the anonymous connection
    WR-02 produced from a credential the caller did supply.

    Neither credential is interpolated into the refusal below, into
    :func:`_graph_identity`, or into any other exception this module raises.

    Raises:
        ValueError: both channels were supplied.
    """
    parts = urlsplit(url)
    if parts.username is None and parts.password is None:
        return None if bearer_token is None else f"Bearer {bearer_token}"
    if bearer_token is not None:
        raise ValueError(
            "fluree_url carries userinfo and bearer_token was also supplied;"
            " supply exactly one credential. This store refuses to choose"
            " between two rather than silently preferring one — neither value"
            " appears in this message"
        )
    userinfo = f"{unquote(parts.username or '')}:{unquote(parts.password or '')}"
    return "Basic " + b64encode(userinfo.encode("utf-8")).decode("ascii")


def _query_body(cypher: str, params: dict[str, object]) -> str:
    """Render the request body of one Cypher read.

    One function rather than an inline ``json.dumps`` at the call site, because
    two callers must agree on it byte for byte: :meth:`FlureeGraphStore.
    post_query`, which sends it, and :meth:`FlureeGraphReader._translate_query`,
    which measures it against :data:`MAX_QUERY_BODY_BYTES` before deciding
    whether to send it. A budget check that measured a *different* rendering
    than the one transmitted would be a budget check in name only.
    """
    return json.dumps({"cypher": cypher, "params": params})


# --- the pinned JSON-LD claim read (plan 24.5-02, ledger row 24.5-L-01) ------
#
# The second dialect on the READ side, ruled at D-IMPL-240 (2): the Cypher
# route cannot be pinned — every header and body form was measured to answer
# the head silently — so a read pinned to a transaction `t` rides the JSON-LD
# `from: <ledger>@t:N` form and hands raw claim rows to the substrate-neutral
# fallback, which is the oracle every pushed answer is already held
# byte-identical to (D-04, `GQ-34`). Nothing here touches `_translate_query`;
# the unpinned path is D-02's openCypher pushdown, unchanged.
#
# Every value below is DATA in a dict — the pin, the partition, the tenant, the
# predicate names — and the body is rendered by one `json.dumps`. No
# formatting site renders query text (threat T-24.5-03), which is also why
# `test_exactly_one_formatting_site_renders_query_text` stays at exactly one:
# a JSON-LD dict is outside its Cypher-shaped regex by construction.


class FlureePinAhead(LookupError):
    """A pin named a transaction the ledger has not reached.

    Raised by :meth:`FlureeGraphStore.post_query_pinned` on the measured
    ``408 err:db/ReadAfterWriteTimeout`` (:data:`PIN_AHEAD_MARKER`), carrying
    the asked pin and the server's own ``current t=N`` in its message — the
    ledger name and two integers, never the URL's userinfo (threat
    T-24.5-04; the :func:`_server_root` discipline). A :class:`LookupError`
    because that is what :class:`~ccf.graph.protocols.SnapshotPinnable`
    declares for a state the store cannot resolve: the pin is well-formed,
    the substrate simply is not there yet.
    """


#: The row vocabulary of the pinned read, keyed by the Cypher column names
#: the ``SELECT_*_AS_OF`` / ``SELECT_LINEAGE`` statements return, valued by
#: the predicate each column reads. **One place** for the mapping, so the
#: pinned rows and the Cypher rows cannot disagree on a column name — the
#: fallback and :func:`ccf.graph.reader.materialize_view` address rows by
#: exactly these keys.
_PINNED_ENTITY_COLUMNS: Final[dict[str, str]] = {
    "entity_uri": P_ENTITY_URI,
    "claim_id": P_CLAIM_ID,
    "claim_json": P_CLAIM_JSON,
    "policy_bundle_version": P_POLICY_VERSION,
    "superseded_by": P_SUPERSEDED_BY,
    "superseded_at": P_SUPERSEDED_AT,
}
_PINNED_RELATIONSHIP_COLUMNS: Final[dict[str, str]] = {
    "relationship_key": P_RELATIONSHIP_KEY,
    "claim_id": P_CLAIM_ID,
    "claim_json": P_CLAIM_JSON,
    "policy_bundle_version": P_POLICY_VERSION,
    "superseded_by": P_SUPERSEDED_BY,
    "superseded_at": P_SUPERSEDED_AT,
}
#: Lineage rows carry their index key beside ``entry_json`` because the pinned
#: read acquires a tenant's whole L axis in ONE select and indexes it in
#: Python, where the Cypher route asks per claim.
_PINNED_LINEAGE_COLUMNS: Final[dict[str, str]] = {
    "claim_kind": P_CLAIM_KIND,
    "node_key": P_NODE_KEY,
    "claim_id": P_CLAIM_ID,
    "entry_json": P_ENTRY_JSON,
}

#: The JSON-LD variable sigil. A ``where`` VALUE beginning with it is read by
#: the server as a **variable**, not a literal — measured 2026-09-02 on
#: ``fluree/server:4.1.4``: ``{"ccf_tenant_id": "?zzz"}`` matched every
#: tenant, and the ``{"@value": …}`` form did not change that. See
#: :func:`_pinned_select`.
_VARIABLE_SIGIL: Final[str] = "?"


def _pinned_query_body(
    body: dict[str, object], *, ledger: str, pin_t: int
) -> str:
    """Render the request body of one pinned JSON-LD read.

    ``from`` is the ledger name with the transaction pin appended in the
    server's own ``name:branch@t:N`` form — a dict VALUE, never interpolated
    into query text. One function rather than an inline ``json.dumps``, for
    the same reason :func:`_query_body` is one: the budget check in
    :meth:`FlureeGraphStore.post_query_pinned` measures the exact bytes sent.
    ``bool`` is refused because ``True`` renders as ``@t:1`` and is not a pin
    anyone meant.

    Raises:
        ValueError: ``pin_t`` is not a non-negative ``int``.
    """
    if isinstance(pin_t, bool) or pin_t < 0:
        raise ValueError(
            f"a transaction pin is a non-negative int; got {pin_t!r}"
        )
    # The pin LAST, so a body that carried its own `from` cannot override the
    # transaction the caller pinned (Phase 24.6 close panel: the reverse order
    # let `**body` win, which would have measured one pin and sent another).
    return json.dumps({**body, "from": f"{ledger}@t:{pin_t}"})


def _pinned_select(
    node_type: str, *, partition: str, tenant: str, columns: dict[str, str]
) -> dict[str, object]:
    """The JSON-LD select for one node type's rows in one tenant's graph.

    The zero-coercion :data:`ADAPTER_CONTEXT` the writer declares, so the
    predicate names come back as the bare ``ccf_*`` names the writer stored
    them under; ``select`` names exactly the predicates ``columns`` reads,
    and ``where`` scopes by partition and tenant exactly as every Cypher
    statement's inline map does (D-03: two partitions in one ledger are two
    graphs). ``@type`` is a code-authored label, never caller data.

    **A scope value beginning with** :data:`_VARIABLE_SIGIL` **is refused,
    never sent.** Measured: the server reads such a value as a query
    variable, so a tenant id ``"?x"`` would match every tenant in the
    partition — over-disclosure by the pinned path, the exact T-15.2-03
    class and this plan's T-24.5-03. The Cypher route binds the same value
    as a ``$param`` and is immune. There is no literal form on this route
    that closes it (the ``{"@value": …}`` form was measured to behave the
    same), so the read fails closed rather than widening.

    Raises:
        ValueError: ``partition`` or ``tenant`` begins with the variable
            sigil.
    """
    for name, value in (("partition", partition), ("tenant_id", tenant)):
        if value.startswith(_VARIABLE_SIGIL):
            raise ValueError(
                f"{name} {value!r} begins with the JSON-LD variable sigil"
                f" {_VARIABLE_SIGIL!r}; on the pinned route the server would"
                " read it as a query variable and answer every scope in the"
                " ledger, so the read is refused rather than widened"
                " (threat T-24.5-03)"
            )
    return {
        "@context": ADAPTER_CONTEXT,
        "select": {"?node": sorted(columns.values())},
        "where": {
            "@id": "?node",
            "@type": node_type,
            P_PARTITION: partition,
            P_TENANT: tenant,
        },
    }


def _pinned_row(
    node: dict[str, Any], *, columns: dict[str, str]
) -> dict[str, object]:
    """Map one JSON-LD result node to a row keyed by the Cypher column names.

    Written against the envelope **measured** on ``fluree/server:4.1.4``
    (2026-09-02) and recorded verbatim in
    ``tests/graph/test_fluree_backend.py::
    test_fa7_a_pinned_read_answers_the_pinned_state_and_the_floor_answers_the_head``:
    a pinned ``select`` answers a bare JSON array of node objects keyed by
    predicate name, and a predicate the node does not carry is **absent**
    from the object rather than ``null``. The Cypher route renders that same
    absence as a ``null`` column, and both the supersession rule and the
    fallback read ``row["superseded_at"]`` expecting ``None`` — so absence
    maps to ``None`` here, and a row satisfies :class:`ccf.graph.reader.Row`
    exactly as a Cypher row does.
    """
    return {column: node.get(predicate) for column, predicate in columns.items()}


def _require_fluree_pin(pin: object) -> int:
    """The ``D-IMPL-88`` guard: only a Fluree-minted pin becomes a ``t``.

    Typed over ``object`` on purpose — the refusal exists for callers who
    offer something that is *not* a :class:`~ccf.graph.protocols.
    StoreSnapshotPin`: a ``datetime`` (an as-of instant mistaken for a pin),
    an ``int`` (a bare ``t`` mistaken for a value the seam accepts), a
    ``str``. Each is a :class:`TypeError` naming the ruling, so the
    transaction-time-for-observation-time substitution D-IMPL-88 forbids
    fails at the seam instead of answering.

    Raises:
        TypeError: ``pin`` is not a :class:`StoreSnapshotPin`, or was minted
            by a different substrate.
        ValueError: the pin's text is not a decimal transaction number.
    """
    if not isinstance(pin, StoreSnapshotPin):
        raise TypeError(
            f"query_pinned takes a StoreSnapshotPin, not {type(pin).__name__};"
            " a transaction pin is not an as-of instant and an as-of instant"
            " is not a pin — the two are different temporal axes and neither"
            " implements the other (D-IMPL-88)"
        )
    if pin.substrate != FLUREE_SUBSTRATE:
        raise TypeError(
            f"a pin minted by substrate {pin.substrate!r} cannot bound a"
            f" {FLUREE_SUBSTRATE!r} read; a StoreSnapshotPin is"
            " substrate-shaped and only the substrate that minted it can"
            " resolve it"
        )
    try:
        return int(pin.pin)
    except ValueError as malformed:
        raise ValueError(
            f"a {FLUREE_SUBSTRATE!r} pin is a decimal transaction number;"
            f" got {pin.pin!r}"
        ) from malformed


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
        url: Server **origin** (``http://host:8090``), optionally carrying
            userinfo — which becomes an HTTP Basic ``Authorization`` header
            (:func:`_authorization`), not a discarded string. Supplied by the
            deployment (typically from an environment variable); never
            committed, never logged, and never echoed back through
            :attr:`graph_identity`. A URL carrying a path, query or fragment
            is refused: every request is rooted at the origin, so anything
            below it would be dropped rather than honoured (WR-02).
        partition: Which graph in this ledger this store attaches to. Two
            partitions in one ledger are two graphs — what lets one server
            host several fabrics, and what makes the single-writer check
            meaningful per fabric rather than per server (the Postgres
            ``schema`` argument's role, exactly).
        ledger: The CCF-owned ledger (D-03). Bootstrapped idempotently at
            construction; every boot after the first sees ``409``.
        bearer_token: Optional bearer credential, reachable from the supported
            boot path through the ``secrets`` mapping, keyed by the field this
            adapter declares as carrying a credential (WR-03). Held **only** in
            the httpx client's default headers — never in
            :attr:`graph_identity`, never in the URL, and never in a
            content-hashed manifest artifact (threats T-15.2-05 / T-04-24; the
            manifest carries the backend *kind* only). Mutually exclusive with
            userinfo in ``url``.

    As with every backend store, this is *not* a store offering both halves of
    the Protocol: it offers :attr:`reader`, and the transport surface to the
    writer module alone.

    **A construction that fails leaves no open connection pool** (WR-05, D-14).
    The two refusals below are raised before any client exists — the credential
    check runs first, and the origin check runs while evaluating the client's
    own argument — so there is nothing to clean up. Everything *after* the
    client exists is guarded and the client is closed on any failure before the
    exception propagates unchanged, because a constructor that raises returns no
    object the caller could have closed.

    Raises:
        ValueError: ``url`` carries a path/query/fragment, or both credential
            channels were supplied. Both are refusals of an instruction the
            store could otherwise only honour by discarding half of it.
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
        # Computed BEFORE the client, from BOTH channels, so a credentialed
        # URL authenticates instead of connecting anonymously (WR-02) and an
        # ambiguous pair is refused instead of silently resolved.
        credential = _authorization(url, bearer_token)
        if credential is not None:
            # The credential's one and only home: a request header. Never the
            # URL — `_server_root` strips it, and httpx would otherwise emit
            # userinfo in the request line while sending no `Authorization`.
            headers["Authorization"] = credential
        self._client = httpx.Client(
            base_url=_server_root(url),
            timeout=DEFAULT_TIMEOUT,
            headers=headers,
        )
        # Everything after the client exists is guarded, and the guard closes
        # it (WR-05, D-14). The shape is `ccf.boot.boot`'s around
        # `mint_boot_token`: construct, guard, close on ANY failure, re-raise
        # unchanged. `BaseException` rather than `Exception` because a
        # KeyboardInterrupt between the three bootstrap requests leaks a pool
        # exactly as an HTTP error does, and neither is the caller's to clean
        # up — a failed constructor returns no object to close.
        #
        # The phase is why this matters more than it did: D-08 puts a
        # secret-resolution step in front of store construction, so a mis-set
        # environment variable now produces construction failures often, and
        # each one held a connection pool open until the interpreter exited.
        try:
            # Fail at construction, not at first read. `/health` is at the
            # server root, NOT under the API base.
            self._client.get(HEALTH_PATH).raise_for_status()
            # One GET, and it makes the store correct behind a
            # differently-mounted server.
            discovered = self._client.get(WELL_KNOWN_PATH)
            discovered.raise_for_status()
            base = str(discovered.json().get("api_base_url") or "")
            self._base = base or DEFAULT_API_BASE
            # D-03's idempotent bootstrap: one CCF-owned ledger, created on the
            # first boot and answered `409 Conflict` on every boot after it.
            # Probe F-A1 assertion (3) proved the 201-then-409 sequence. `POST
            # /create` has no context parameter, and the context-setting
            # endpoint is never called, so the ledger has no default context by
            # construction (D-02).
            created = self._client.post(
                f"{self._base}/create",
                content=json.dumps({"ledger": ledger}),
            )
            if created.status_code != HTTPStatus.CONFLICT:
                created.raise_for_status()
            #: Highest transaction time this store has written. Threaded into
            #: `Fluree-Min-T` on every read so read-after-write is exact. Note
            #: it is only ever *written* from a commit receipt: `X-Fluree-T` is
            #: not sent on the Cypher route by this build (measured, plan
            #: 15.3-01), so nothing here reads it back.
            self._min_t = 0
            self._reader = FlureeGraphReader(self)
        except BaseException:
            self._client.close()
            raise

    @property
    def graph_identity(self) -> str:
        """Credential-free identity of the graph this store is attached to."""
        return self._identity

    @property
    def max_traversal_depth(self) -> int:
        """The deepest traversal this adapter translates natively — the injection bound.

        :class:`~ccf.graph.protocols.TraversalDepthCapability`
        (``D-IMPL-253`` Q21), satisfied structurally: the value is this
        module's own :data:`MAX_DEPTH_CEILING`, which bounds the one literal
        the adapter injects into query text. Read off the store rather than
        authored anywhere, so a layer that has a governed response can refuse
        an over-ceiling depth **by name** without any product code carrying the
        number (CINV-01). Nothing about this seam's own behavior changes: an
        over-ceiling depth here still declines the native translation and is
        answered by the memory-bounded fallback.
        """
        return MAX_DEPTH_CEILING

    @property
    def capability_identity(self) -> str:
        """The identity a technical bound from this store is resolved by.

        :attr:`graph_identity` itself — credential-free, and already the
        string this fabric identifies this graph by — rather than a second
        name that could drift from it.
        """
        return self.graph_identity

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
            content=_query_body(cypher, params),
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

    def head_t(self) -> int:
        """The ledger's current transaction ``t`` — read off ``GET …/ledgers``.

        Transport, on :meth:`post_query`'s terms. The Cypher route returns no
        ``X-Fluree-T`` (measured, plan 15.3-01) and the commit receipt is
        write-derived, so the listing is the one read-side source of the head
        (the route ``examples/cp-04-corporate-family-tree/deployment.py::
        ledger_t`` reads it by; the shape is copied, never the values). The
        listing carries ``{"name", "branch", "t"}`` for **every** branch of
        every ledger on the server, so the match is on the ``name:branch``
        pair — see :data:`DEFAULT_BRANCH`. No host, port or credential
        literal: the request goes through this store's own client.

        Raises:
            LookupError: the server lists no such ledger. Named by ledger
                only; the message carries nothing from the URL.
            httpx.HTTPError: the listing itself failed.
        """
        response = self._client.get(f"{self._base}/ledgers")
        response.raise_for_status()
        name, _, branch = self._ledger.partition(":")
        branch = branch or DEFAULT_BRANCH
        for entry in response.json():
            if entry.get("name") == name and entry.get("branch") == branch:
                return int(entry["t"])
        raise LookupError(
            f"the server lists no ledger {self._ledger!r}; its head t cannot"
            " be read"
        )

    def post_query_pinned(
        self, body: dict[str, object], *, pin_t: int
    ) -> list[dict[str, Any]]:
        """Run one JSON-LD read PINNED to transaction ``pin_t``; return its nodes.

        Transport, on :meth:`post_query`'s terms — the second read dialect
        D-IMPL-240 (2) declares. The pin rides as ``from: <ledger>@t:N``
        inside the body (:func:`_pinned_query_body`), a dict value and never
        query text, and the request goes to ``POST {base}/query`` with **no
        ledger in the path**: the path form ``/query/<ledger>@t:N`` is a
        measured ``500 Invalid ledger ID format``. The body is measured against
        :data:`MAX_QUERY_BODY_BYTES` on the exact bytes sent — the
        :meth:`post_update` posture, and unlike the Cypher route there is no
        fallback to decline to, so an over-budget body is refused loudly.

        The answer is the envelope measured on ``fluree/server:4.1.4``: a bare
        JSON array of node objects keyed by predicate name, ``[]`` for a scope
        with nothing in it.

        Raises:
            FlureePinAhead: ``pin_t`` is past the ledger head — the measured
                ``408 err:db/ReadAfterWriteTimeout`` (:data:`PIN_AHEAD_MARKER`).
            ValueError: the rendered body exceeds :data:`MAX_QUERY_BODY_BYTES`.
            httpx.HTTPStatusError: any other refusal, unchanged.
        """
        rendered = _pinned_query_body(body, ledger=self._ledger, pin_t=pin_t)
        size = len(rendered.encode("utf-8"))
        if size > MAX_QUERY_BODY_BYTES:
            raise ValueError(
                f"pinned query body is {size} bytes, over this adapter's"
                f" {MAX_QUERY_BODY_BYTES}-byte budget under the server's"
                " documented 1 MB (--max-query-size) limit; a pinned read has"
                " no fallback route to decline to, so it is refused rather"
                " than narrowed"
            )
        response = self._client.post(f"{self._base}/query", content=rendered)
        if (
            response.status_code == HTTPStatus.REQUEST_TIMEOUT
            and PIN_AHEAD_MARKER in response.text
        ):
            served = response.json().get("error", "")
            raise FlureePinAhead(
                f"pin t={pin_t} is past the head of ledger {self._ledger!r}:"
                f" {served}"
            )
        response.raise_for_status()
        nodes: list[dict[str, Any]] = response.json()
        return nodes

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


# --- GraphQuery translation, stage 1 (plan 15.3-03) --------------------------
#
# The Cypher half of the pushdown story, on the shape
# ``src/ccf/graph/backends/neo4j.py::_SURVIVORS_MATCH`` and its siblings
# established: statements composed exclusively of code-authored fragments, with
# every value travelling as a named request parameter. The hook contract is
# all-or-nothing (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583); the surviving
# rows feed ccf.graph.reader.materialize_view exactly as the five fixed
# statements do, so lineage-at-boundary and supersession-as-of stay rendered in
# the one shared place (INV-CH7-14).
#
# **Every predicate family is pushed** as of plan 15.3-04: stage 1 landed the
# non-traverse families, stage 2 the bounded undirected walk. A decline still
# sends the WHOLE query to the fallback — conformant under D-04, byte-identical
# by construction (`GQ-34`), and visible in `fallback_answers` telemetry rather
# than hidden — but it is now reserved for the four named guards rather than
# taken for a whole family.
#
# **This is not the Neo4j translation with a prefix change.** Two of its
# predicates cannot be ported and both were measured rather than assumed:
# `_ENTITY_POLICY`'s dynamic property access evaluates to null here (probe
# F-A6 — it fails *silently*, returning 200), and `_WALK_EDGES_ALL`'s
# relationship-property reads see nothing on a plain RDF edge (probe F-A3(e),
# measured `[null, null]`). The first is resolved below by membership over the
# write-time materialized key; the second is what the interposed edge node
# exists for.
#
# Like Neo4j, this module contains **exactly one string-formatting site** —
# `_reach_pattern`'s variable-length bound. Plan 15.3-03 shipped with none, and
# that stronger property was spent by probe F-A2, which measured both
# parameterized bound forms rejected `400` at parse time. Every other value
# here binds as a `$param` (threat T-15.2-01).

_SURVIVORS_MATCH = (
    "MATCH (c:CcfEntityClaim {ccf_partition: $partition,"
    " ccf_tenant_id: $tenant})\n"
    "WHERE c.ccf_observed_at <= $boundary\n"
    "  AND (c.ccf_superseded_at IS NULL OR c.ccf_superseded_at > $boundary)\n"
)

#: The validity-window cut (`GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185,
#: INV-CH7-25) over the write-time canonical re-renderings, so the pushed
#: comparison is fixed-width text against the canonical boundary (`GQ-24` at
#: docs/GRAPH_QUERY_SEMANTICS.md:482). Correctness rests entirely on probe
#: F-A5, which read ``DATATYPE()`` back for ``ccf_valid_from_cmp`` and
#: ``ccf_valid_to_cmp`` and got ``xsd:string`` for both: under a temporal
#: datatype this comparison would run temporally at the engine's own precision
#: and diverge from the fallback on exactly the boundary cases the corpus
#: generates (§R8 vector 2). An absent projection compares NULL, and NULL fails
#: every comparison — fail-closed, never over-disclosing (threats T-15.2-03 /
#: T-15.2-26), measured directly against the live server before this fragment
#: was written.
_ENTITY_VALIDITY = (
    # `GQ-09`'s ABSENCE LIMB (`D-IMPL-332`) — see the neo4j twin.
    "  AND (c.ccf_valid_from_cmp IS NULL OR c.ccf_valid_from_cmp <= $boundary)\n"
    "  AND (c.ccf_valid_to_cmp IS NULL OR c.ccf_valid_to_cmp > $boundary)\n"
)

#: Policy admissibility, all three cuts of `GQ-08` at
#: docs/GRAPH_QUERY_SEMANTICS.md:163 (INV-CH7-26) — as **pure membership**,
#: which is this backend's whole departure from
#: ``src/ccf/graph/backends/neo4j.py::_ENTITY_POLICY``.
#:
#: Neo4j reads the classification through dynamic property access — ``c[$key]``
#: with the attribute name supplied as map-parameter content
#: (``src/ccf/graph/backends/neo4j.py::_ENTITY_POLICY``). Probe F-A6 measured
#: that expression on this engine: it **parses, returns 200 and evaluates to
#: null**. Ported verbatim it
#: would have excluded every claim while reporting success, on the predicate
#: family that gates the majority of real queries — a wrong answer no status
#: check would catch, which is why the verdict was taken by comparison against
#: a static-access control. The plan's own named alternative
#: ``any(k IN $keys WHERE k IN c.ccf_policy_key)`` is rejected at parse time
#: (400): an ``IN`` right-hand side must be an inline list or a parameter,
#: never a property expression.
#:
#: What works is plain membership over the multi-valued key the write path
#: materializes, because a multi-valued RDF property **fans out into one row
#: per value** rather than yielding a list — so ``IN`` expresses "any
#: materialized key is admissible" and ``RETURN DISTINCT`` collapses the
#: multiplicity. That materializes `GQ-08` exactly: a class with no declared
#: attribute contributes no key and is inadmissible; a claim carrying no value
#: for its class's attribute produces no matching key and is inadmissible
#: (measured — a claim with no ``ccf_policy_key`` at all is excluded while a
#: control proves it exists). And **no artifact-authored string enters query
#: text**: the keys are computed in Python by :func:`policy_key` and travel as
#: a parameter list, which is this backend's realization of the T-15.2-01
#: closure.
_ENTITY_POLICY = (
    "  AND c.ccf_policy_bundle_version IN $policy_versions\n"
    "  AND c.ccf_policy_key IN $policy_keys\n"
)

#: The uniform rule's set membership on entity selection (`GQ-15` at
#: docs/GRAPH_QUERY_SEMANTICS.md:300): every family computes within the set,
#: restricted before anything else evaluates. The set travels as a request list
#: parameter (`GQ-30` at docs/GRAPH_QUERY_SEMANTICS.md:563) — no member is ever
#: rendered into query text. It is also the term that can push the rendered
#: body past :data:`MAX_QUERY_BODY_BYTES`.
_ENTITY_ALLOWED = "  AND c.ccf_entity_uri IN $allowed\n"

#: ``DISTINCT`` is not decoration: the policy fragment above matches per
#: *value* of a multi-valued property, so a claim admissible under two of its
#: own materialized keys would otherwise arrive twice and be materialized as a
#: duplicate record. Applied unconditionally rather than only alongside the
#: policy family, because it cannot change any other answer — ``claim_id`` is
#: unique per claim, so two distinct claims can never render an identical row.
_SURVIVORS_RETURN = (
    "RETURN DISTINCT c.ccf_entity_uri AS entity_uri,"
    " c.ccf_claim_id AS claim_id,\n"
    "       c.ccf_claim_json AS claim_json,\n"
    "       c.ccf_policy_bundle_version AS policy_bundle_version,\n"
    "       c.ccf_superseded_by AS superseded_by,\n"
    "       c.ccf_superseded_at AS superseded_at,\n"
    "       c.ccf_entity_class AS entity_class\n"
    "ORDER BY c.ccf_entity_uri"
)

_EDGES_MATCH = (
    "MATCH (rc:CcfRelationshipClaim {ccf_partition: $partition,"
    " ccf_tenant_id: $tenant})\n"
    "WHERE rc.ccf_observed_at <= $boundary\n"
    "  AND (rc.ccf_superseded_at IS NULL"
    " OR rc.ccf_superseded_at > $boundary)\n"
)

_EDGE_VALIDITY = (
    "  AND (rc.ccf_valid_from_cmp IS NULL OR rc.ccf_valid_from_cmp <= $boundary)\n"
    "  AND (rc.ccf_valid_to_cmp IS NULL OR rc.ccf_valid_to_cmp > $boundary)\n"
)

#: A relationship is admissible under the policy family iff its bundle version
#: is permitted (`GQ-08`) — no classification cut of its own; endpoint survival
#: governs its exposure below.
_EDGE_POLICY = "  AND rc.ccf_policy_bundle_version IN $policy_versions\n"

#: The induced-subgraph rule (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316):
#: both endpoints members of the allowed set, stated natively on the claim's
#: own projected endpoint columns.
_EDGE_ALLOWED = (
    "  AND rc.ccf_subject_uri IN $allowed\n"
    "  AND rc.ccf_object_uri IN $allowed\n"
)

#: Typed crossability doubles as answer membership: edges of other types are
#: absent even between reached endpoints (`GQ-10` at
#: docs/GRAPH_QUERY_SEMANTICS.md:201). **This looks like a relationship read
#: and is not** — it reads a property on the ``CcfRelationshipClaim`` *node*,
#: so it is untouched by the relationship-property break that forced the
#: interposed edge, and the artifact-authored type list rides as a ``$types``
#: parameter rather than as a Cypher relationship-type pattern (threat
#: T-15.2-01). It is also what makes the walk's hop predicate pure membership:
#: because crossability is decided **here**, the walk needs no type cut of its
#: own — which is exactly what saves it from the deferred bounded
#: type-alternation (§R5 Break 2).
_EDGE_TYPES = "  AND rc.ccf_relationship_type IN $types\n"

#: Endpoint closure against the surviving universe (`GQ-16`, INV-CH7-40): an
#: answer view never retains an edge to a node its principal may not see. The
#: degenerate everything-question skips this — a dangling first-class edge is
#: state, not a leak, in the unconstrained answer (`GQ-05` at
#: docs/GRAPH_QUERY_SEMANTICS.md:122).
_EDGE_CLOSURE = (
    "  AND rc.ccf_subject_uri IN $survivors\n"
    "  AND rc.ccf_object_uri IN $survivors\n"
)

_EDGES_RETURN = (
    "RETURN DISTINCT rc.ccf_relationship_key AS relationship_key,\n"
    "       rc.ccf_claim_id AS claim_id,"
    " rc.ccf_claim_json AS claim_json,\n"
    "       rc.ccf_policy_bundle_version AS policy_bundle_version,\n"
    "       rc.ccf_superseded_by AS superseded_by,\n"
    "       rc.ccf_superseded_at AS superseded_at,\n"
    "       rc.ccf_subject_uri AS subject_uri,"
    " rc.ccf_object_uri AS object_uri\n"
    "ORDER BY rc.ccf_relationship_key"
)

# --- the interposed walk, stage 2 (plan 15.3-04) -----------------------------
#
# ⛔ **Do not port `_WALK_EDGES_ALL` (``backends/neo4j.py::_WALK_EDGES_ALL``).** It reads
# RELATIONSHIP properties — `r.partition`, `r.relationship_key`,
# `r.relationship_type` — and on this engine a plain RDF edge has none: a
# property-reading relationship variable sees only reifier-bundled edges. The
# ported predicate would make `all(...)` false for every path, return an
# **empty reached set**, answer `200`, and raise nothing. That is not covered
# by Fluree's "clear error, never a silently wrong result" promise, which is
# about parse-time rejection of unsupported *forms*; this form parses fine
# (15.3-RESEARCH.md §R5 Break 1, §5 do-not-copy #1, Pitfall 7 — whose named
# warning sign is a traversal returning exactly the seeds and nothing else, at
# every depth).
#
# Probe **F-A3(e) CONFIRMED the break by measurement** before these fragments
# were written: projecting a relationship property out of a path's relationship
# list, over the layout the write path produces, returns `[null, null]`. The
# executable form of this rule is
# `tests/graph/test_fluree_backend.py::test_no_relationship_property_is_read`,
# which greps this module for a path-relationship projection and requires zero.
#
# Compounding it, the only bounded variable-length pattern this engine admits
# is a **single fixed relationship type** — bounded type-alternation (a
# pipe-separated relationship pattern with hop bounds) and undirected-untyped
# (`-[*]-`) are both deferred upstream (Break 2) — so a two-type shape such as
# `HAS_EDGE`/`TO` would reintroduce the very constraint being escaped. That
# option was considered and rejected; `CCF_LINK` and nothing else appears in
# any pattern here.
#
# The resolution is Mongo's, in a different physical model: move the
# information onto NODE properties and reduce every hop predicate to
# **membership in a set the adapter already computed**
# (``src/ccf/graph/backends/mongo.py::MongoGraphReader``'s ``_walk``
# docstring). Crossability — type, temporal, policy,
# validity, `allowed_entities` on both endpoints, endpoint closure — is
# already fully decided by the edges statement that computes the crossable
# set; the walk re-states nothing, because a re-derivation is a second place
# for the semantics to live and the two would eventually disagree. Secondary
# "shortcut" relationships are rejected outright for the same reason.

#: The seed, scoped. The inline map is not decoration: D-03 puts every
#: partition of every fabric in **one ledger**, so an unscoped
#: `seed.ccf_admit_key IN $starts` matches that URI in every partition present
#: — measured at 175 matches against 1 on the container the probes ran on
#: (F-A3(f)). The scope also rides inside the path predicate below, so the
#: confinement is a property of the statement rather than a side effect of how
#: `$admissible` happens to be computed elsewhere (threats T-15.2-03 /
#: T-15.2-26), exactly as
#: ``src/ccf/graph/backends/neo4j.py::_WALK_NODES_ALL`` states it.
_WALK_MATCH_PREFIX = (
    "MATCH p = (seed:CcfEntity {ccf_partition: $partition,"
    " ccf_tenant_id: $tenant})"
)
_WALK_MATCH_SUFFIX = "(x:CcfEntity)\n"

#: Hop admissibility as **one** node predicate over **one** prefix-namespaced
#: parameter list (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261, INV-CH7-40):
#: every node on every path — entity nodes and interposed edge nodes alike —
#: must be a member of the set the adapter already computed, so a path through
#: an excluded node **does not exist**. Probe F-A3(b) measured that distinction
#: rather than assuming it: with the intermediate's key removed, the path count
#: to the target is 0, not merely its absence from the returned rows. The
#: difference is the whole of threat T-15.2-26 — output-side filtering would
#: leave the resurrection shape unprotected.
#:
#: `$admissible` is built in Python as the `e:`-prefixed survivors-and-allowed
#: union the `r:`-prefixed crossable keys. The two prefixes are what make an
#: `entity_uri` incapable of colliding with a `relationship_key` in one list.
_WALK_NODES_ALL = (
    "WHERE seed.ccf_admit_key IN $starts\n"
    "  AND all(n IN nodes(p) WHERE n.ccf_partition = $partition\n"
    "          AND n.ccf_tenant_id = $tenant\n"
    "          AND n.ccf_admit_key IN $admissible)\n"
)

_WALK_RETURN = "RETURN DISTINCT x.ccf_entity_uri AS entity_uri"


def _reach_pattern(depth: int) -> str:
    """The variable-length reach pattern — the ONE string-formatting site.

    Probe **F-A2 FAILED** as expected: both `-[:CCF_LINK*1..$depth]-` and the
    quantified `-[:CCF_LINK{1,$depth}]-` are rejected `400` at parse time
    (``"expected `]` but got `$depth`"``), so a variable-length bound cannot be
    a request parameter here any more than it can on Neo4j. Had either parsed,
    this module would have kept plan 15.3-03's stronger property of containing
    **no formatting site at all**; it does not, so this is the single named,
    documented exception to the everything-is-a-parameter rule (threat
    T-15.2-01), and it admits exactly one value shape: a genuine ``int``
    (``bool`` refused), at least 1 (depth 0 never reaches this function — the
    walk is skipped and the starting points are the answer), and at most
    :data:`MAX_DEPTH_CEILING` (over-ceiling queries never reach it either — the
    translation declines and the fallback answers under D-04).

    **The ceiling is checked against the CCF depth, BEFORE the doubling.** A
    CCF hop is *two* Cypher hops through the interposed edge node, so the
    rendered bound is ``2 * depth``. The graph is bipartite
    (entity-edge-entity), so parity handles itself once the terminal is
    labelled ``(x:CcfEntity)``: only even-length paths end at an entity.

    This ``×2`` is the replacement for Mongo's ``maxDepth: depth_limit - 1``
    off-by-one — structurally absent here because Cypher's ``*1..N`` is 1-based
    — and it is exactly the same class of error, which is why it is asserted
    against the fallback at depths 0, 1, 2 **and** 3 rather than reasoned about
    (15.3-RESEARCH.md Pitfall 13: an off-by-factor-of-two is silent and
    surfaces only as an ordinary differential failure at depth >= 2). Replay is
    unaffected: the pinned value is ``content_hash(GraphQuery)``, never the
    rendered Cypher (`GQ-20` at docs/GRAPH_QUERY_SEMANTICS.md:391).

    Raises:
        ValueError: the caller broke the validation contract above — an
            internal invariant violation, never a query-vocabulary refusal.
    """
    if (
        not isinstance(depth, int)
        or isinstance(depth, bool)
        or depth < 1
        or depth > MAX_DEPTH_CEILING
    ):
        raise ValueError(
            f"traversal depth literal must be an int in [1, "
            f"{MAX_DEPTH_CEILING}]; got {depth!r} — callers gate depth 0 and "
            "the over-ceiling decline before rendering, and the ceiling "
            "applies to the CCF depth before the interposed doubling"
        )
    return f"-[:CCF_LINK*1..{2 * depth}]-"


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
    use the inline form as copied from the five fixed statements on
    ``src/ccf/graph/backends/neo4j.py::Neo4jGraphReader``.

    The reader holds the Cypher ``GraphQuery`` translation:
    :meth:`_translate_query` answers **every** predicate family natively — the
    as-of cut, the validity window, the policy family as membership over the
    write-time materialized key, ``allowed_entities`` membership as a request
    list parameter, and (plan 15.3-04) the bounded undirected traversal as a
    walk over the interposed edge-node layout. A declined translation is still
    not a gap: the fallback's answer *is* the definition and is
    byte-identical by construction (`GQ-34` at
    docs/GRAPH_QUERY_SEMANTICS.md:609), which is exactly why a passing
    differential suite cannot be read as evidence of pushdown and why the
    ``translated_answers`` / ``fallback_answers`` telemetry is asserted
    separately.

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

    # -- the pinned read: ``SnapshotPinnable``, structurally (24.5-L-01) -----

    def snapshot_pin(self) -> StoreSnapshotPin:
        """This ledger's head, as a :class:`~ccf.graph.protocols.StoreSnapshotPin`.

        ``substrate`` is :data:`FLUREE_SUBSTRATE`; ``pin`` is the head ``t``
        :meth:`FlureeGraphStore.head_t` reads, as decimal text. A fact about
        the read on the transaction-time axis — recorded beside
        ``graph_snapshot_at``, never inside it (D-IMPL-88).
        """
        return StoreSnapshotPin(
            substrate=FLUREE_SUBSTRATE, pin=str(self._store.head_t())
        )

    def query_pinned(self, q: GraphQuery, *, pin: StoreSnapshotPin) -> GraphView:
        """Answer ``q`` as :meth:`query` would on the ledger frozen at ``pin``.

        The D-IMPL-240 (2) route: three JSON-LD selects pinned to
        ``@t:{pin}`` acquire the tenant's entity claims, relationship claims
        and lineage entries (:func:`_pinned_select`, one per node type), each
        result node is mapped to a Cypher-column-keyed row by
        :func:`_pinned_row`, and everything above the rows is the
        substrate-neutral core — :func:`ccf.graph.reader.materialize_view`,
        then :func:`ccf.graph.fallback.answer` for every predicate family of
        ``q``, then the interface's own ordering — so the answer is
        byte-identical to what the unpinned route would give on a ledger
        frozen at that ``t`` (D-04: the fallback is the oracle, `GQ-34`).

        **Two axes, applied in sequence and never conflated.** The pin bounds
        the STORE: rows are read at the committed state ``t``. ``q.as_of``
        bounds the OBSERVATIONS: the fallback re-applies the full survival
        predicate over ``observed_at`` / ``superseded_at`` (`GQ-12`), so a
        claim committed before ``t`` but observed after ``q.as_of`` is still
        absent. The rows are acquired without an as-of cut on the wire
        precisely because the fallback owns that cut and is independently
        enforceable at this tier.

        The D-IMPL-88 guard runs **first**, before any I/O
        (:func:`_require_fluree_pin`): a ``datetime``, an ``int`` or a pin
        from another substrate is refused by ``TypeError`` naming the ruling.
        This method does not touch :meth:`_translate_query` — the unpinned
        openCypher path is D-02's and is untouched — and it does not move the
        ``translated_answers`` / ``fallback_answers`` telemetry, which counts
        :meth:`query`'s posture and nothing else.

        Raises:
            TypeError: ``pin`` is not a Fluree-minted :class:`StoreSnapshotPin`.
            FlureePinAhead: ``pin`` is past the ledger head.
            ValueError: the tenant or partition would be read as a query
                variable on this route (:func:`_pinned_select`).
        """
        pin_t = _require_fluree_pin(pin)
        partition = self._store.partition

        def rows_of(node_type: str, columns: dict[str, str]) -> list[Row]:
            nodes = self._store.post_query_pinned(
                _pinned_select(
                    node_type,
                    partition=partition,
                    tenant=q.tenant_id,
                    columns=columns,
                ),
                pin_t=pin_t,
            )
            return [_pinned_row(node, columns=columns) for node in nodes]

        entity_rows = rows_of(L_ENTITY_CLAIM, _PINNED_ENTITY_COLUMNS)
        relationship_rows = rows_of(
            L_RELATIONSHIP_CLAIM, _PINNED_RELATIONSHIP_COLUMNS
        )
        # The whole L axis at the pin, once, indexed on the same
        # (kind, node_key, claim_id) key `SELECT_LINEAGE` binds — so a lineage
        # entry that arrived AFTER the pin is as absent as a claim that did.
        lineage_index: dict[tuple[str, str, str], list[Row]] = {}
        for row in rows_of(L_LINEAGE, _PINNED_LINEAGE_COLUMNS):
            key = (
                str(row["claim_kind"]),
                str(row["node_key"]),
                str(row["claim_id"]),
            )
            lineage_index.setdefault(key, []).append(row)

        def lineage_rows_for(kind: str, node_key: str, claim_id: str) -> list[Row]:
            return lineage_index.get((kind, node_key, claim_id), [])

        supplier: _LineageRowsFor = lineage_rows_for
        materialized = materialize_view(
            entity_rows=entity_rows,
            relationship_rows=relationship_rows,
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            lineage_rows_for=supplier,
        )
        entities, relationships = fallback.answer(
            materialized.entities, materialized.relationships, query=q
        )
        return _ordered_view(
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            entities=entities,
            relationships=relationships,
        )

    def _translate_query(
        self, q: GraphQuery
    ) -> tuple[Sequence[Row], Sequence[Row]] | None:
        """Answer the whole query natively in Cypher (plans 15.3-03/15.3-04).

        The hook contract is all-or-nothing (`GQ-32` at
        docs/GRAPH_QUERY_SEMANTICS.md:583): the return is the complete answer's
        row pair — every predicate family applied, ``allowed_entities``
        membership applied — or ``None``, meaning the fallback enforces the
        whole query. Up to three statements run in sequence:

        1. **survivors** — the surviving entity claims: the as-of cut (`GQ-07`
           at docs/GRAPH_QUERY_SEMANTICS.md:148, INV-CH7-14) as canonical-text
           comparison, the validity window (`GQ-09`) over the write-time
           re-renderings, policy admissibility (`GQ-08`) as membership over the
           materialized key, and the uniform rule's set membership (`GQ-15`) as
           a request list parameter;
        2. **edges** — the surviving relationship claims that may appear in the
           answer: typed crossability (`GQ-10`), the induced subgraph under
           ``allowed_entities`` (`GQ-16`) and endpoint closure against the
           materialized survivors on every constrained answer. This statement
           is what **decides crossability**; the walk below re-states none of
           it;
        3. **walk** — on a traverse query only: the bounded undirected reach
           (`GQ-10`) over the interposed edge-node layout, with hop
           admissibility (`GQ-13`) as membership in the set steps 1 and 2
           already computed. The reached set then filters both row sets, which
           is the Cypher analogue of the SQL adapters' outer ``SELECT``s.

        **Fluree has no read transaction to hold these statements in**, and it
        needs none: CCF has exactly one writer (INV-CH7-10), the store threads
        the highest written ``t`` into ``Fluree-Min-T`` on every read, and all
        of them are issued inside one :meth:`query` call — so they observe one
        consistent state without a transaction to hold them.

        Three shapes never reach the server, and each is a *guard* rather than
        a degradation — it changes which path answers, never the answer:

        * the empty ``allowed_entities`` set IS the empty answer (`GQ-04` at
          docs/GRAPH_QUERY_SEMANTICS.md:98), returned without a round trip;
        * an over-ceiling ``depth_limit`` declines (:data:`MAX_DEPTH_CEILING`);
        * a query whose policy family cannot be encoded injectively declines
          (:func:`policy_key`).

        ``admitted_entity_classes`` (`GQ-10` at
        docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0) is HONORED in Python: the
        ``$admissible`` entity keys narrow to admitted-class survivors plus
        the starts before the walk statement is built. ``direction`` other
        than ``"undirected"`` (`GQ-10`, 1.2.0; ledger row ``24.5-L-06``) is
        DECLINED (`GQ-32`): the interposed layout writes both ``CCF_LINK``s
        FROM the edge node, so the link carries no edge direction and a
        directed variable-length pattern is not expressible over it
        (24.5-RESEARCH.md Pitfall 5) — the fallback answers, byte-identical,
        rather than an approximation.

        Two further declines are measured rather than computed: the rendered
        request body is checked against :data:`MAX_QUERY_BODY_BYTES` before
        each statement is sent, and a walk refused by the server's
        path-enumeration cap (:data:`PATH_CAP_MARKER`) declines **after** a
        round trip — see the catch, which explains why that is deliberate.
        """
        if q.allowed_entities is not None and not q.allowed_entities:
            # The empty survivor set IS the answer (`GQ-04`): the empty view,
            # answered without a substrate round trip. An empty answer is an
            # answer, never an error (`GQ-23` at
            # docs/GRAPH_QUERY_SEMANTICS.md:474).
            return (), ()
        if q.traverse is not None and q.traverse.direction != "undirected":
            # Decline → the fallback answers (D-04; ledger row 24.5-L-06). A
            # pure function of the query value, before any translation: a
            # pushdown that ignored `direction` would walk undirected while
            # the oracle walks directed, a divergence nothing would observe.
            return None
        if (
            q.traverse is not None
            and q.traverse.depth_limit > MAX_DEPTH_CEILING
        ):
            # Decline → the fallback answers (D-04). Deliberately BEFORE any
            # request is built: the decline is a pure function of the query
            # value. The ceiling is applied to the **CCF** depth, before the
            # interposed layout's doubling — a CCF hop is two Cypher hops
            # through the edge node, so bounding the rendered pattern means
            # bounding the number this reads, not the number 15.3-04 renders.
            #
            # This is now the ONLY depth guard: plan 15.3-04's promotion
            # removed the blanket traverse decline that used to subsume it, so
            # the branch is reached on its own terms and the unit assertion
            # over it became discriminating.
            return None

        policy_versions = q.permitted_policy_bundle_versions
        attribute_by_class = q.classification_attribute_by_class
        policy_keys: list[str] | None = None
        if policy_versions is not None:
            assert attribute_by_class is not None  # noqa: S101 - GQ-02 whole family
            assert q.permitted_classifications is not None  # noqa: S101
            # The classification cut, computed HERE in Python and compared as
            # stored literals — the F-A6 resolution. A class with no declared
            # attribute contributes no key, so it is inadmissible by producing
            # nothing to match, exactly as the fallback computes it.
            keys: set[str] = set()
            for entity_class, attribute in attribute_by_class.items():
                for classification in q.permitted_classifications:
                    key = policy_key(entity_class, attribute, classification)
                    if key is None:
                        # A component carrying the separator would make the
                        # encoding non-injective, so a pushed answer could
                        # admit a claim the fallback excludes. Decline — still
                        # a pure function of the query value, so like the three
                        # guards above it happens before anything is built.
                        return None
                    keys.add(key)
            policy_keys = sorted(keys)

        boundary = canonical_timestamp(q.as_of)
        constrained = (
            q.allowed_entities is not None
            or policy_versions is not None
            or q.require_valid_at_boundary is not None
            or q.traverse is not None
        )
        require_validity = q.require_valid_at_boundary is True

        params: dict[str, object] = {
            "partition": self._store.partition,
            "tenant": q.tenant_id,
            "boundary": boundary,
        }
        survivor_text = [_SURVIVORS_MATCH]
        edge_text = [_EDGES_MATCH]
        if require_validity:
            survivor_text.append(_ENTITY_VALIDITY)
            edge_text.append(_EDGE_VALIDITY)
        if policy_versions is not None:
            survivor_text.append(_ENTITY_POLICY)
            edge_text.append(_EDGE_POLICY)
            params["policy_versions"] = sorted(policy_versions)
            params["policy_keys"] = policy_keys
        if q.allowed_entities is not None:
            survivor_text.append(_ENTITY_ALLOWED)
            edge_text.append(_EDGE_ALLOWED)
            params["allowed"] = sorted(q.allowed_entities)
        if q.traverse is not None:
            edge_text.append(_EDGE_TYPES)
            params["types"] = sorted(q.traverse.relationship_types)
        if constrained:
            edge_text.append(_EDGE_CLOSURE)
        survivor_text.append(_SURVIVORS_RETURN)
        edge_text.append(_EDGES_RETURN)

        survivors_cypher = "".join(survivor_text)
        if not self._within_body_budget(survivors_cypher, params):
            return None
        entity_rows = self._store.post_query(survivors_cypher, params)

        params["survivors"] = [row["entity_uri"] for row in entity_rows]
        edges_cypher = "".join(edge_text)
        if not self._within_body_budget(edges_cypher, params):
            return None
        relationship_rows = self._store.post_query(edges_cypher, params)
        if q.traverse is None:
            return entity_rows, relationship_rows

        # Walk-start selection within survivors (`GQ-11` at
        # docs/GRAPH_QUERY_SEMANTICS.md:221): seed classes select within the
        # surviving universe; explicit seeds intersect with it — a URI naming
        # nothing in scope contributes no start.
        survivor_uris = {row["entity_uri"] for row in entity_rows}
        starts = {
            row["entity_uri"]
            for row in entity_rows
            if row["entity_class"] in q.traverse.seed_entity_classes
        }
        if q.seeds is not None:
            starts |= set(q.seeds) & survivor_uris
        # Seeds are IN the answer. `*1..N` starts at one hop, so this
        # correction transfers verbatim from the Neo4j template
        # (``src/ccf/graph/backends/neo4j.py::answer_whole_query``, which seeds
        # `reached` the same way) — it is really Neo4j's correction, not
        # Mongo's `$graphLookup` seed exclusion.
        reached = set(starts)
        if starts and q.traverse.depth_limit >= 1:
            # depth_limit=0 skips the MATCH entirely: `*1..0` is not a bound,
            # and depth 0 answers with the walk starting points — a legal
            # bound, not an error (`GQ-10` at
            # docs/GRAPH_QUERY_SEMANTICS.md:201). Mongo's third correction,
            # transferring verbatim.
            reachable = survivor_uris
            if q.allowed_entities is not None:
                # The uniform rule stated explicitly in the term that expands
                # the walk (`GQ-15` at docs/GRAPH_QUERY_SEMANTICS.md:300).
                # Survivors are already restricted to the set by
                # `_ENTITY_ALLOWED`, so this is a closure rather than a new
                # cut — the D-IMPL-87 resurrection defect held shut in the
                # term that could reopen it
                # (``src/ccf/graph/backends/neo4j.py::_WALK_NODES_ALLOWED``).
                reachable = survivor_uris & q.allowed_entities
            if q.traverse.admitted_entity_classes is not None:
                # Node-class admission, HONORED in Python (`GQ-10` at
                # docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0; ledger row
                # 24.5-L-05): the `e:`-prefixed admissible keys narrow to
                # survivors of an admitted class PLUS the starts — the seed
                # is in `nodes(p)` and `GQ-11` starts are never filtered by
                # admission. Survivor rows carry `entity_class` (the same
                # column the start selection reads), so no extra round trip.
                admitted = q.traverse.admitted_entity_classes
                class_of = {
                    row["entity_uri"]: row["entity_class"] for row in entity_rows
                }
                reachable = {
                    uri
                    for uri in reachable
                    if uri in starts or class_of.get(uri) in admitted
                }
            admissible = {ENTITY_ADMIT_PREFIX + uri for uri in reachable} | {
                RELATIONSHIP_ADMIT_PREFIX + row["relationship_key"]
                for row in relationship_rows
            }
            walk_cypher = "".join(
                (
                    _WALK_MATCH_PREFIX,
                    _reach_pattern(q.traverse.depth_limit),
                    _WALK_MATCH_SUFFIX,
                    _WALK_NODES_ALL,
                    _WALK_RETURN,
                )
            )
            params["starts"] = sorted(
                ENTITY_ADMIT_PREFIX + uri for uri in starts
            )
            params["admissible"] = sorted(admissible)
            if not self._within_body_budget(walk_cypher, params):
                return None
            try:
                walk_rows = self._store.post_query(walk_cypher, params)
            except httpx.HTTPStatusError as refusal:
                if PATH_CAP_MARKER not in refusal.response.text:
                    raise
                # The path-enumeration cap **errors** rather than truncating
                # (measured, probe F-A3(c)), so it is a hard failure the
                # adapter converts into a decline: `None` sends the WHOLE
                # query to the D-04 fallback, which answers byte-identically
                # by construction (`GQ-34`) and increments `fallback_answers`.
                #
                # Unlike every existing decline in the tree this one happens
                # **after a round trip** — it cannot be a pure function of the
                # query value, because whether the cap fires depends on the
                # graph's density, which no query inspection can know. That is
                # a deliberate, documentable difference rather than a contract
                # violation: `GQ-32` constrains what a **non-`None`** return
                # must contain, never when `None` may be produced. The cost is
                # wasted requests; the alternative is a `500` reaching the
                # caller for a question the fallback can answer.
                return None
            reached |= {row["entity_uri"] for row in walk_rows}
        # The reached set filters both row sets — the Cypher analogue of the
        # SQL adapters' `IN (SELECT uri FROM walk)` outer SELECTs; the walk
        # itself ran in the engine.
        entity_rows = [
            row for row in entity_rows if row["entity_uri"] in reached
        ]
        relationship_rows = [
            row
            for row in relationship_rows
            if row["subject_uri"] in reached and row["object_uri"] in reached
        ]
        return entity_rows, relationship_rows

    @staticmethod
    def _within_body_budget(cypher: str, params: dict[str, object]) -> bool:
        """Would this statement's rendered body fit the server's query cap?

        The byte-budget guard (:data:`MAX_QUERY_BODY_BYTES`), measured on the
        exact bytes :meth:`FlureeGraphStore.post_query` would send rather than
        estimated from the parameter values. ``allowed_entities`` and the
        materialized survivor list both travel as ``$param`` lists, so a large
        set is the shape that approaches the documented 1 MB
        ``--max-query-size``; the Control Plane's survivor cap (`GQ-18`) bounds
        that set, but the two are unrelated numbers and neither implies the
        other.

        A refusal is not a failure and not a narrowing: the caller returns
        ``None``, the fallback answers the whole query byte-identically (D-04;
        `GQ-29` at docs/GRAPH_QUERY_SEMANTICS.md:554), and the event is visible
        in ``fallback_answers``. This bounds the generated request, never the
        query vocabulary — the :data:`MAX_DEPTH_CEILING` argument ratified at
        the D-GATE-15.2 checkpoint Q2, applied to the other end of the same
        request.
        """
        rendered = _query_body(cypher, params)
        return len(rendered.encode("utf-8")) <= MAX_QUERY_BODY_BYTES
