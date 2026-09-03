# Graph Query Semantics

**Semantics version: 1.2.0** — the query vocabulary is versioned through this
document only (D-12): the `GraphQuery` contract carries **no version field**
and evolves by additive sentinel-defaulted fields under the existing
frozen/`extra=forbid` discipline; the differential conformance suite is the
compatibility check. 1.0 added `allowed_entities`; 1.1.0 `admitted_entity_classes`; 1.2.0 `direction` (`GQ-10`, `GQ-35`).

This is the normative definition of what a `GraphQuery` means and what any
conformant answerer must return — D-05 artifact 1, written before the
reference implementation and before any adapter, per the D-05 ordering
(prose → fallback → adapters). The reading order is the authority order:
**this prose decides; `ccf.graph.fallback` implements it; adapters agree
with it under the differential suite; the property suite audits the
fallback** — so the oracle is itself answerable to something it does not
define. Adapters relate to this document as the SDK relates to the
whitepaper: failure messages cite clauses, disputes are resolved by quoting
the sentence violated, and semantic changes arrive as versioned amendments
(`GQ-35`), never as silent oracle drift.

The segmentation clauses of §4 implement **the D-IMPL-87 resolution entry**
(`docs/DECISIONS.md`, 2026-08-07) — Dave's ruling of record for
multi-segment pushdown. This document transcribes that ruling into
normative sentences; it does not re-decide it.

**Key words.** MUST, MUST NOT, and MAY are used as requirement levels. A
clause stated with MUST is a conformance obligation on every answerer of
the `GraphReader.query()` seam — storage adapters, the fallback, and
tier-2 sources alike.

**Clause anchors.** Every clause carries a stable backticked anchor of the
form `GQ-NN`. Citing code cites a clause in the anchored form the
`tools/lints/citations.py` citation guard verifies — the backticked anchor
immediately before the file-and-line, as in: per `GQ-07` at
docs/GRAPH_QUERY_SEMANTICS.md:NNN — so an edit that moves a clause without
updating its citations goes red in CI. Clause numbers are never reused; a
future amendment that retires a clause marks it superseded in place.

Where a clause realizes a whitepaper commitment, the whitepaper section is
cited in the clause. Where a clause is an SDK extension beyond the
whitepaper (the tier-2 payload convention of §7), the section is labeled
**SDK-defined** per CLAUDE.md §11.

---

## 1. Vocabulary

### `GQ-01` — The query is a value

A `GraphQuery` is an immutable value with two mandatory fields and no
others: `tenant_id` (every question is tenant-scoped; there is no
untenanted path through the fabric) and `as_of` (the observed-time boundary
of the answer). `as_of` **arrives as data — no answerer, and no code below
the caller of the seam, may read a clock** (whitepaper §7.10 determinism;
the same discipline `temporal_boundary` observes in the operator algebra).
Everything else in the vocabulary is optional: the three predicate families
(`GQ-02`), the explicit seeds set (`GQ-03`), and `allowed_entities`
(`GQ-04`). Because the query is a value, `content_hash(q)`
(`src/ccf/contracts/canonical.py::content_hash`) is well-defined and serves
as the per-round-trip replay pin (`GQ-20`). Realizes whitepaper §7.3 (the
Context Graph as queryable persisted state) and §7.4 (operators as the
intent the query renders).

### `GQ-02` — The three predicate families

A `GraphQuery` MAY carry up to three predicate families, each mirroring the
corresponding pushable operator parameter contract field-for-field:

- **policy family** — `permitted_policy_bundle_versions`,
  `classification_attribute_by_class`, `permitted_classifications`
  (mirrors `src/ccf/operators/params.py::PolicyFilterParameters`).
- **temporal family** — `require_valid_at_boundary`
  (mirrors `src/ccf/operators/params.py::TemporalAsOfParameters`). The
  as-of cut itself is not part of this family: it is carried by the
  mandatory `as_of` field and applies to every answer (`GQ-07`).
- **traverse family** — `seed_entity_classes`, `relationship_types`,
  `depth_limit`
  (mirrors `src/ccf/operators/params.py::TraversalNeighborhoodParameters`).

A family, when present, carries **all** of its fields. The parameter
contracts these families mirror declare fields and never defaults
(D-IMPL-38); a partially-specified family is not a legal value, and the
contract MUST refuse it at construction. There is no Similarity family:
similarity consults an injected index the substrate does not hold, and is
never pushable (D-03).

### `GQ-03` — Explicit seeds

A `GraphQuery` MAY carry `seeds`: a set of entity URIs naming walk starting
points directly. Seeds have exactly one meaning, everywhere: **walk
starting points** (`GQ-15`). Seeds are not part of any operator's
`QueryFragment` (`GQ-06`); they are authored by the caller of the seam —
in the segmented execution path, the engine. A query carrying `seeds`
without a traverse family is not well-formed: there is no walk for the
seeds to start, and the contract MUST refuse it at construction rather
than let a constraint-shaped field constrain nothing.

### `GQ-04` — `allowed_entities`

A `GraphQuery` MAY carry `allowed_entities`: a set of entity URIs
constraining the **whole answer**. Its three values are three different
facts:

- **`None` — no constraint.** `allowed_entities` is `None` on first
  segments and on every segment of a fully-pushable plan, so the common
  no-Similarity case is untouched by this field's existence.
- **The empty set — the empty answer.** An empty `allowed_entities` is a
  legal value whose answer is the empty view. It is distinct from `None`:
  "the survivor set is empty" and "there is no survivor-set constraint"
  are different questions, and collapsing them would turn an empty
  in-process segment into an unconstrained read of the substrate.
- **A non-empty set — the uniform rule applies** (`GQ-15`): every entity
  in the answer MUST be a member of the set, every operator family
  computes within it, and relationships require both endpoints in-set
  (`GQ-16`).

`allowed_entities` is **engine-authored segment-boundary data**. It is
never part of an operator's `QueryFragment` (`GQ-06`): no operator knows
about segments, and no operator's declared intent may smuggle a survivor
set. Extends D-02 per the D-IMPL-87 resolution entry.

### `GQ-05` — Absent families and the degenerate query

An absent family means **no constraint of that family** — not a default
constraint, not an empty constraint. The degenerate query — all three
families absent, no seeds, `allowed_entities` `None` — is the
**everything-question**: its answer is the tenant's full as-of view under
`GQ-07`. The degenerate query is not an error case; it is the definition
of `as_of()` (`GQ-21`) and the compilation target of a plan none of whose
operators is pushable.

### `GQ-06` — `QueryFragment` and the union rule

A `QueryFragment` is one operator's contribution to a segment's query: at
most one of the three predicate families of `GQ-02`, and **nothing else**
— never seeds, never `allowed_entities`. An operator that is not pushable
contributes no fragment. Fragments within a segment union field-wise into
one `GraphQuery`, with **at most one fragment per family**: two fragments
claiming the same family is a broken plan and MUST be refused at plan
compilation — never merged, because a merge rule would silently decide
which operator's parameters win, and a decided-by-accident parameter set
cannot be replayed against an intent.

---

## 2. Evaluation semantics

### `GQ-07` — The as-of cut

A record — entity or relationship — is in scope for a query iff:

    observed_at <= as_of
    AND (superseded_at IS NULL OR superseded_at > as_of)

This is INV-CH7-14 rendered at the query tier (whitepaper §7.3): claims
the fabric had not yet observed at the boundary are absent, and claims
superseded **after** the boundary are still current — an as-of read
re-renders the state the fabric held at `as_of`, with no future
information leaking in. The cut applies to **every** answer, whether or
not any predicate family is present, because `as_of` is mandatory
(`GQ-01`).

### `GQ-08` — Policy admissibility

When the policy family is present, an entity is admissible iff **all
three** hold, exactly as `src/ccf/operators/categories.py::_admits`
computes in-process (INV-CH7-26, whitepaper §7.4):

1. its `policy_bundle_version` is a member of
   `permitted_policy_bundle_versions`;
2. its entity class has a declared classification attribute in
   `classification_attribute_by_class` — **a class with no declared
   classification attribute is inadmissible**;
3. the value of that attribute on the entity is a member of
   `permitted_classifications` — an entity carrying no value for its
   class's classification attribute is inadmissible. The fabric does not
   admit state it cannot prove is admissible.

A relationship is admissible under the policy family iff its
`policy_bundle_version` is a member of
`permitted_policy_bundle_versions`. Relationships carry no classification
check of their own; their exposure is governed by endpoint survival under
the substitution rule (`GQ-16`).

### `GQ-09` — The validity-window rule

When the temporal family is present with `require_valid_at_boundary`
true, a record additionally survives only if its valid interval covers
the boundary, exactly as cut 3 of
`src/ccf/operators/categories.py::_survives` computes in-process
(INV-CH7-25):

    valid_from <= as_of
    AND (valid_to IS NULL OR valid_to > as_of)

When `require_valid_at_boundary` is false, the family imposes nothing
beyond the always-applied as-of cut of `GQ-07` — the two questions "what
did we know?" and "what was true?" are the two axes of the bitemporal
model, and which one a decision needs is declared, never assumed.

### `GQ-10` — Traversal

When the traverse family is present, the answer is a bounded breadth-first
expansion (INV-CH7-24, whitepaper §7.4) with these decided semantics:

- **Undirected.** An edge is crossable in either direction; subject→object order carries no traversal
  meaning — under `direction="undirected"`, the default; `direction="forward"` crosses only from
  `subject_uri` to `object_uri` as stored (amendment 1.2.0, `GQ-35`).
- **Typed.** The walk crosses only edges whose `relationship_type` is a member of `relationship_types`.
  Edges of other types are not crossable — and are **absent from the answer** even when both their
  endpoints are reached: the traverse family's answer contains exactly the permitted-type edges among reached entities.
- **Seeds are included.** Every walk starting point that is itself in scope is in the answer.
- **`depth_limit=0` yields the walk starting points only.** Zero hops is a legal, meaningful bound, not an error and not "unlimited".
- **`depth_limit=N` reaches at most N hops** from a walk starting point. A node whose shortest
  admissible path from every start exceeds N is absent.
- **Admitted.** When `admitted_entity_classes` is present, a hop lands only on an entity whose
  `entity_class` is a member; walk starts (`GQ-11`) are unaffected, and an entity absent from
  in-scope state is not a hop. Absent (`None`), every class is admissible — the 1.0.x behavior
  (amendment 1.1.0, `GQ-35`).

### `GQ-11` — Walk-start selection

The walk starting points of a traverse-family query are the union of two
selections, each computed over in-scope state only:

1. entities whose `entity_class` is a member of `seed_entity_classes`;
2. entities named in the explicit `seeds` set (`GQ-03`).

Either selection may be empty; a URI in `seeds` that names no in-scope
entity simply contributes no start (it is not an error — the record may
be excluded by the very predicates this query carries). A start MUST
satisfy every predicate of the segment and, when `allowed_entities` is
present, be a member of the set (`GQ-16` — `seed_entity_classes` select
within the set; explicit `seeds` intersect with it). When the combined
start set is empty, the answer is the empty view (`GQ-23`).

### `GQ-12` — The fallback input contract

The reference implementation (`ccf.graph.fallback`) receives materialized
`EntityRecord` / `RelationshipRecord` values that **retain their temporal
metadata** — `claim.observed_at`, `claim.valid_from` / `claim.valid_to`,
and the record's `superseded_by` / `superseded_at` — plus the
`GraphQuery`, and it MUST re-apply the **full** as-of survival predicate
(`GQ-07`, and `GQ-09` when the temporal family requires it) over those
retained fields. The consequence is normative, not incidental:

- for substrates whose row acquisition already applied the as-of cut (the
  SQL `SELECT_*_AS_OF` paths of the existing backends), the fallback's
  re-application is an **idempotent no-op**;
- for sources that cannot pre-filter — a mounted product's verbatim
  payload records (`GQ-26`) — the fallback's predicate **is** the as-of
  enforcement.

INV-CH7-14 is therefore independently enforceable at the fallback tier
and MUST never be assumed to have been applied upstream.

---

## 3. Hop admissibility

### `GQ-13` — Every hop, not the result set

Every node and every edge on a traversal path MUST satisfy the segment's
policy (`GQ-08`) and temporal (`GQ-07`, `GQ-09`) predicates — and, when
`allowed_entities` is present, every node on the path MUST be a member of
the set. **A path through an excluded or out-of-set node does not
exist.** This is INV-CH7-40 — the substitution semantics — rendered at
the query tier: in-process, the walk expands over a view that Policy and
Temporal already pruned, so an edge to an excluded node is not a hop the
walk can take, and a pushed traversal MUST behave identically.

This clause is a MUST for every adapter at every tier. Applying the
predicates to the *result set* instead of to *every hop* is the named
information-disclosure defect of this seam: a path seed→X→target where X
is policy-excluded would return `target`, leaking X's existence by
reachability. The differential corpus deliberately targets multi-hop
paths through mixed-admissibility neighborhoods to expose exactly this
divergence.

---

## 4. Segmentation and the uniform rule

This section implements the D-IMPL-87 resolution entry
(`docs/DECISIONS.md`, 2026-08-07) — the ruling of record for
multi-segment pushdown. Nothing here is a planner choice; the clauses
transcribe the ruling.

### `GQ-14` — The split

The engine splits the ordered operator plan at non-pushable boundaries
and issues **one substrate query per pushable segment**. Round-trip count
is plan-dependent. The split is a function of **the plan, the
survivor-set size, and the Control Plane cap configuration** (`GQ-18`) —
and NEVER of the substrate: adapters always answer (`GQ-29`, D-04), so
what the substrate is cannot influence what is asked, and the round-trip
count and provenance chain are identical on every substrate. Replay
portability is total — rows *and* trace.

### `GQ-15` — The uniform rule

Every pushed segment after an in-process segment carries the surviving
entity set as `allowed_entities`, and **every operator family in that
segment computes within the set**: traversal may not cross outside it,
filters select within it. Seeds keep exactly one meaning — walk starting
points (`GQ-03`, `GQ-11`). Per the D-IMPL-87 resolution entry: seeds say
where walks start, not which nodes they may cross. This closes the
entity-resurrection defect — a later pushed query re-reaching entities an
in-process operator already excluded — and is what makes
`apply(full_view) == pushed(intent)` provable per-plan on
Similarity-bearing plans. The rule is uniform across every operator
family, deliberately: a family-specific rule would give seeds two
meanings by family, and a future expanding operator would silently
inherit the unsound default.

### `GQ-16` — The induced subgraph

When `allowed_entities` is present, a relationship is in the answer only
when **both** endpoints are members of the set — and both endpoints
survive the segment's predicates. This is the no-leak-by-absence
substitution rule (`src/ccf/operators/categories.py::_substitute`,
INV-CH7-40) rendered at the query tier: a view retaining an edge to a
node the principal may not see leaks by absence.

The endpoint-closure half of this clause holds for every **constrained**
answer — any family present, or `allowed_entities` non-`None`: such a view
never contains a relationship whose endpoint entity is absent from it. The
degenerate answer is exempt (amendment 1.0.1, stated under `GQ-35`).

### `GQ-17` — Segment-boundary mechanics

The survivors of an in-process segment are the entity URIs present in
the view after its operators applied. They become the next pushed
segment's `allowed_entities`, and the next segment's walk starting
points are computed **within that set**: `seed_entity_classes` select
within `allowed_entities`; explicit `seeds` intersect with it (`GQ-11`).
The surviving *entities* are the boundary data; surviving relationships
are not carried — the next segment's answer re-derives its edges under
`GQ-16`, which is what makes the survivor set the whole constraint
rather than half of one.

### `GQ-18` — The size cap

The survivor-set size cap is **normative mechanism**; the threshold
*value* lives in Control Plane configuration with **default `None` — no
cap** — and never in SDK code (mechanism-not-values, CLAUDE.md §11;
D-10). When the survivor set exceeds the configured cap, the engine runs
that segment **in-process instead of pushing** — semantically identical
by construction, because the surviving view is already in memory after
the in-process segment, and free of any extra substrate read. A cap
firing is visible in the pinned query sequence itself (`GQ-20`): the
record shows what ran. The cap configuration in force pins into replay
dimension 2, so the split stays a function of plan + data + Control
Plane config (`GQ-14`) under replay as in production.

### `GQ-19` — The segment-answer fixed point

The answer to a segment query is a **fixed point** of that segment's
operators applied in order over it: re-applying the segment's operator
sequence to its own answer returns the answer, bit for bit. This holds
per family, under the uniform rule:

- **Policy and temporal predicates are pointwise record filters.** A
  filter applied to its own output is idempotent: every record in the
  answer already satisfies the predicate, so nothing further is removed.
- **Traversal re-walked over its own answer re-reaches exactly the
  answer.** Every node in the answer at walk distance *d* has the
  intermediate nodes of its shortest admissible path in the answer at
  distance < *d* (breadth-first inclusion), and every edge of that path
  survives the induced-subgraph rule (`GQ-16`) because both its
  endpoints are in the answer — so the re-walk reaches every answered
  node within the same bound. It reaches nothing more, because the
  answer's state is a subset of the original input. Walk-start selection
  within the answer equals the original walk-start set: seed-class
  selection over a subset returns the members of the original selection
  that survived — and every original start survived, by seed inclusion
  (`GQ-10`); explicit seeds intersect identically. `allowed_entities`
  membership is preserved under subsetting.
- **The empty-set and `None` cases are trivial fixed points**: the empty
  view maps to the empty view; an unconstrained filter chain over its
  own output removes nothing.

This clause is what entitles the engine to re-apply a pushed segment's
operators over the returned view to derive execution-side provenance —
the re-application is guaranteed to reproduce the substrate's answer, so
the provenance chain records what ran without a second source of truth
for what the rows are. This is a fresh statement under the uniform rule
of `GQ-15`; no earlier formulation of segment idempotence is carried
into this lane.

### `GQ-20` — The replay pin

`content_hash` of each issued `GraphQuery` is the per-round-trip replay
pin, recorded **in execution order** — the recorded sequence is what
ran, never what the plan predicted. The full canonical query bytes land
in the ArtifactStore keyed by those hashes (whitepaper §7.10; CLAUDE.md
§7.4 — immutable, content-addressed, exact-version resolution). Replay
recomputes each query from the pinned snapshot + plan and compares
hashes — a mismatch is caught non-determinism — and an auditor resolves
the literal question asked from the store without re-running anything.
Per the D-IMPL-87 resolution entry and D-11.

### Worked example — a no-Similarity plan, one segment

The plan `[PolicyFilter, TemporalAsOf, TraversalNeighborhood]`, stated
against the actual execution order
`src/ccf/operators/base.py::CATEGORY_ORDER` = (`policy`, `similarity`,
`temporal`, `traversal`) with the similarity slot unoccupied. All three
operators are pushable, so the plan is **one segment**. The engine issues
**one** substrate query carrying all three predicate families —
policy, temporal, and traverse — with `allowed_entities` `None`
(`GQ-04`: first segment of a fully-pushable plan). One round trip, one
pin recorded (`GQ-20`). This is the common case, and it is untouched by
the multi-segment machinery: no survivor set exists because nothing ran
in-process.

### Worked example — a Similarity-bearing plan, two segments

The plan `[PolicyFilter, SimilaritySelect, TemporalAsOf,
TraversalNeighborhood]`, in the same `CATEGORY_ORDER`. `SimilaritySelect`
is not pushable (D-03 — it consults an injected similarity index the
substrate does not hold), so the plan splits at it (`GQ-14`):

1. **Segment 1** pushes `PolicyFilter` alone: one substrate query
   carrying the policy family, `allowed_entities` `None` (first
   segment). The substrate answers the policy-admissible as-of view.
2. **In-process:** `SimilaritySelect` runs over the returned view. The
   entities present in its output view are the **survivors**.
3. **Segment 2** pushes `TemporalAsOf` + `TraversalNeighborhood`: one
   substrate query carrying the temporal and traverse families, with the
   survivor set as `allowed_entities` (`GQ-15`). Walk starting points
   are computed within the set — `seed_entity_classes` select within it
   (`GQ-17`). The traversal cannot re-reach an entity Similarity
   removed: it is out-of-set, and a path through it does not exist
   (`GQ-13`).

Two round trips, two pins recorded in execution order (`GQ-20`). Had the
survivor set exceeded the Control Plane cap, segment 2 would have run
in-process instead (`GQ-18`) — same answer, visible in the pinned
sequence.

---

## 5. `as_of` equivalence

### `GQ-21` — `as_of` is the degenerate query

`as_of(tenant, at)` is **defined** as
`query(GraphQuery(tenant_id=tenant, as_of=at))` — the degenerate
everything-question of `GQ-05`. Identical records, identical ordering,
identical canonical bytes. `as_of()` is therefore reframed, not
deprecated (D-07): `BaseGraphReader` derives it from `query()`, adapter
authors implement one method, and a plan whose operators are all
non-pushable compiles to precisely this query. Every existing `as_of()`
call site remains valid unchanged.

---

## 6. Answer form

### `GQ-22` — Ordering and serialization belong to the interface

The answer to a `GraphQuery` is a `GraphView`
(`src/ccf/graph/protocols.py::GraphView`): frozen, deterministically
ordered — **entities by `entity_uri`, relationships by
`relationship_key`** — with `tenant_id` and `as_of` echoing the query.
Ordering and canonical serialization are owned by the interface, never
by the adapter: an adapter answers *which* records are in the answer;
the shared materialization path decides how they are ordered, rendered,
and hashed. A second ordering convention would make two adapters'
identical answers hash differently, which is the one thing the
differential suite (`GQ-31`) cannot survive.

### `GQ-23` — Empty answers are answers

An empty answer is a legitimate value, never an error. "Nothing is
known", "everything was excluded", and "the walk started nowhere"
(`GQ-11`) all answer with the empty view, and operators compose over it
exactly as over any other view. An answerer MUST NOT raise on emptiness;
raising is reserved for broken deployments, not for absent state.

### `GQ-24` — Canonical timestamps

All timestamps in queries and answers are stored and compared as
canonical RFC3339 UTC text
(`src/ccf/contracts/canonical.py::canonical_timestamp`). The fixed-width
canonical rendering sorts lexicographically, so text-ordered comparison
is chronological comparison — which is what lets the as-of cut of
`GQ-07` be pushed as a plain text comparison on every substrate without
a per-substrate timestamp type, and what keeps cross-substrate answers
byte-identical rather than merely similar.

---

## 7. The tier-2 payload convention — **SDK-defined**

This section is an SDK extension beyond the whitepaper (CLAUDE.md §11):
the whitepaper commits to Context Products as delivery contracts; the
convention by which a product's payload carries queryable graph state is
SDK mechanism, labeled as such.

### `GQ-25` — The `graph_state` payload shape

A graph-shaped product payload carries a well-known top-level key
`graph_state` in the product's `payload` mapping
(`src/ccf/products/contract.py::ContextProductContract`), holding two
keys: `entities` and `relationships` — lists whose items validate
against the existing `EntityRecord` / `RelationshipRecord` contracts via
`model_validate`. Nothing about the records is re-shaped for transport:
they retain their temporal metadata, which is what makes `GQ-12`
enforceable over them. A payload without that shape — no `graph_state`
key, or items that fail record validation — **refuses at mount** with a
typed refusal, before any query is asked: a source that cannot answer
correctly is refused while wiring, not discovered mid-question.

### `GQ-26` — What a mounted product answers

A `ProductSource` mounts only an `AdmittedProduct`
(`src/ccf/peering/admission.py::AdmittedProduct` — the type the peering
admission gate alone can produce), and answers the `GraphReader.query()`
seam with **the fallback semantics of this document over the product's
`graph_state` records**. It needs no query engine: it is the KV-floor
pattern over governed records, and the fallback's re-application of the
as-of predicate (`GQ-12`) is the temporal enforcement — the records
arrive verbatim from the payload, so nothing upstream has pre-filtered
them. The resulting view is ephemeral, owned by the execution; nothing
enters L3, and the single-writer invariant is not implicated.

### `GQ-27` — Source tenant mismatch

A `GraphQuery` whose `tenant_id` does not match a mounted source's
tenant is answered with the **empty view**. It never returns a
cross-tenant mix, and it never raises. Contrast the replay path
deliberately: `SnapshotReader` raises
(`src/ccf/replay/snapshots.py::SnapshotScopeViolation`) on a
tenant/as_of mismatch, because a replay pin names exactly one scope and
a question outside it is a broken replay — **a source answers
questions; a pin enforces one.** The two behaviors are both normative,
and they are different on purpose.

### `GQ-28` — Tenant-boundary conformance

Because `GQ-27` makes the empty view the mismatch answer, an empty
answer alone cannot distinguish "empty because excluded" from "empty
hiding a cross-tenant leak". Tenant-boundary conformance tests MUST
query **both** tenants — the source's own tenant (expecting its records)
and a foreign tenant (expecting the empty view) — so that the empty
answer is evidence of exclusion rather than an untested default.

---

## 8. Conformance, the translation hook, and amendments

### `GQ-29` — Adapters always answer

A conformant adapter answers **any well-formed `GraphQuery`** — one that
validates against the contract (`GQ-02`, `GQ-03`) — degrading internally
to scan-and-filter where it holds no native translation. There is no
capability negotiation and no typed pushdown-refusal path in the
Protocol (D-04). Well-formedness is settled at contract construction;
an adapter may assume it and MUST NOT re-litigate it.

### `GQ-30` — `allowed_entities` translates natively

The *contract* carries the set; the *wire realization* is
adapter-internal. SQL `IN` or a temp table, Cypher `UNWIND` or a list
parameter, an aggregation-pipeline `$in`, the fallback's
set-intersection — all are conformant renderings of the same clause, and
none of them is part of the vocabulary. An adapter MUST apply
`allowed_entities` with the uniform-rule semantics (`GQ-15`, `GQ-16`)
whatever its rendering.

### `GQ-31` — Differential conformance is byte-identity

Every adapter's answer to every corpus query MUST be byte-identical to
the reference implementation's answer over canonical bytes — not
row-count-equal, not semantically-similar: identical. The corpus MUST
include `allowed_entities`-bearing shapes and multi-segment
(Similarity-bearing) plans, because the entity-resurrection defect
(`GQ-15`) and mixed-admissibility paths (`GQ-13`) are exactly the shapes
single-segment corpora never exercise.

### `GQ-32` — The translation-hook contract

A substrate translation answers the **whole query or does not answer at
all**: the hook returns the complete answer's rows — all families
applied, hop admissibility (`GQ-13`) applied, `allowed_entities`
membership applied — or `None`. **No partial-family bookkeeping
exists**: there is no protocol by which a translation reports "I applied
the policy family but not the traverse family", because such bookkeeping
is precisely the per-substrate divergence surface this document exists
to close.

### `GQ-33` — Safe narrowing under a declined translation

When the hook returns `None`, the baseline row acquisition:

- MUST apply tenant narrowing and the as-of cut where it can (`GQ-07`);
- MAY additionally narrow rows by predicates entailed by the query's
  policy and/or temporal families AND by `allowed_entities` membership.
  Safe-narrowing is sound because the fallback re-enforces the whole
  query over whatever arrives (`GQ-12`), and narrowing by the query's
  **own** constraints removes only records the answer excludes anyway;
- MUST NOT narrow by the traverse family. Reachability is a whole-graph
  property, not a row predicate; when the traversal is untranslated it
  belongs to the fallback, whole (`GQ-32`), and a row-level proxy for it
  starves the walk of the state it must expand over.

### `GQ-34` — Staged adapters are conformant

`GQ-32` + `GQ-33` are exactly how a staged adapter is represented: an
aggregation-pipeline adapter whose stage 1 is `$match`-narrowing by the
policy/temporal families plus `allowed_entities`, with traversal left to
the fallback, is **fully conformant under D-04** — it answers every
well-formed query, its answers are byte-identical to the reference, and
what was natively translated versus scanned is telemetry, deliberately
outside the replay record (performance is never a replay input). Native
traversal translation is a promotion an adapter earns by passing the
differential suite, not a conformance requirement.

### `GQ-35` — Amendments

Semantic changes to this vocabulary ship as **versioned amendments to
this document** under the semver lane declared at the top — never as
silent behavioral drift in the fallback or an adapter. The `GraphQuery`
contract carries no version field (D-12): the vocabulary evolves by
additive sentinel-defaulted fields under the frozen/`extra=forbid`
discipline, the differential suite is the compatibility check, and this
document is the record of what each version means. Clause anchors are
stable across amendments; numbers are never reused. Adapter failure
messages MUST cite the clause anchor violated, so a dispute begins from
the sentence it is about.

**Amendment history.** New entries append here rather than rewriting the
clause they amend out of existence, and an amendment is written so it does
not move the clause headings above it — the anchored citations across
`/src` and `/tests` carry line numbers, and a renumbering edit would make
the citation guard report a hundred false moves and hide a real one.

- **1.2.0** — *plan 24.5-18 (the mechanism: plan 24.5-05), ledger row
  `24.5-L-06`.* `GQ-10`'s first bullet gains a direction: the traverse
  family carries `direction: "undirected" | "forward" = "undirected"` on
  `TraversalSpec`, fixed by the operator KEY that emits the spec and
  carried by no parameter class — `traversal.typed-neighborhood` emits
  `"undirected"`, its sibling `traversal.typed-descendants` emits
  `"forward"`.

  *What it means.* Under `"forward"` an edge is crossable only from its
  stored `subject_uri` to its stored `object_uri`; a node one hop from a
  reached node AGAINST the stored orientation is not reached. Everything
  else in `GQ-10` — typing, seeds included, `depth_limit`, admission — and
  `GQ-11`'s walk-start selection are unchanged. `"undirected"` is the
  default and the 1.1.0 walk byte-for-byte, so every query and every
  parameter artifact written before this amendment asks exactly what it
  always asked (D-10, additive over breaking). No artifact value can turn a
  walk around: `TraversalDescendantsParameters` has no `direction` field.

  *Why it was needed.* A family TREE is a directed parent-to-child walk and
  the neighborhood walk had no way to say so — cp-04's `24.4-D-36`.
  Measured on that product's committed fixture from its anchor: the
  directed walk reaches 20 / 21 / 22 nodes at depths 1 / 2 / 3 where the
  undirected neighborhood reaches 20 / 22 / 22, the one divergent node
  being a cycle's closing edge crossed against its orientation
  (`tests/operators/test_traversal_direction.py`). A sibling KEY under the
  existing `traversal` category is additive (D-10); a fifth category is not
  (`D-IMPL-223`). Every answerer honors the field or declines it to the
  fallback (`GQ-32`, D-04): SQLite and Postgres natively — the crossable
  set, or the recursive join, chosen between two constant renderings in
  Python, never a value in statement text; Neo4j natively — the reach
  pattern with its arrow, relationships being directed at write; MongoDB
  and Fluree decline — the doubled-document restriction unmeasured, the
  interposed link carrying no direction. The differential suite holds all
  five to the fallback over
  `tests/conformance/query_corpus.py::direction_cases`.
  `content_hash(GraphQuery)` moves again for every traverse query
  (`GQ-20`); no committed query pin exists in the tree.

- **1.1.0** — *plan 24.5-04, ledger row `24.5-L-05`.* `GQ-10` gains a sixth
  bullet, **Admitted**: the traverse family carries
  `admitted_entity_classes: frozenset[str] | None = None`, mirrored on
  `TraversalSpec` and `TraversalNeighborhoodParameters`.

  *What it means.* When the set is present, a hop lands only on an entity
  whose `entity_class` is a member — a walk stops at a class boundary
  rather than crossing it. Admission filters REACHED nodes and never walk
  STARTS: `GQ-11` selects starts, "seeds are included" stands, and a start
  of an unadmitted class is in the answer and still expands. An entity
  absent from in-scope state has no class and is not a hop. `None` is the
  positive assertion "every class is admissible" — the 1.0.x question,
  byte-for-byte — so every query and every parameter artifact written
  before this amendment asks exactly what it always asked (D-10, additive
  over breaking; the `allowed_entities` precedent). The empty set admits no
  hop and answers the walk starting points. Endpoint closure (`GQ-16`) is
  unchanged: an edge to an unadmitted node is pruned as any excluded
  neighbor's edge is.

  *Why it was needed.* `TraversalNeighborhood` typed the walk on EDGES and
  `seed_entity_classes` seeded only; a walk that must stop at a class
  boundary — cp-04's `24.4-D-33` — had no SDK expression. A new name under
  the existing `traversal` category is additive (D-10); a fifth operator
  category is not (`D-IMPL-223`, four classes). Every answerer honors the
  field or declines it to the fallback (`GQ-32`, D-04): SQLite and Postgres
  natively, inside the recursive walk term; Neo4j and Fluree in Python, by
  narrowing the admissible node list to admitted-class survivors plus the
  starts; MongoDB declines. The differential suite holds all five to the
  fallback over `tests/conformance/query_corpus.py::admission_cases`.
  Because `canonical_bytes` walks every field, `content_hash(GraphQuery)`
  moves for every traverse query (`GQ-20`); no committed query pin exists
  in the tree, and `tests/replay/test_query_sequence_pin.py` re-derives
  pins from live executions.

- **1.0.1** — *plan 15.2-14, the phase-close audit.* `GQ-16`'s
  endpoint-closure half is scoped to **constrained** answers; the
  degenerate answer is exempt.

  *What it means.* Closure's rationale is exclusion: an edge to a node the
  answer *removed* discloses that node's existence by absence. The
  degenerate everything-question of `GQ-05` removes nothing, and its answer
  is the tenant's full as-of view — in which a persisted first-class edge
  whose endpoint carries no entity claim is **state, not a leak**, because
  relationships are first-class in the Context Graph and never derived
  joins (INV-CH7-20). A constrained answer is a valid graph for its
  principal, not a row bag; the degenerate answer is the graph itself.

  *Why it was needed.* The 1.0.0 wording said closure held for "every"
  answer, which contradicted `GQ-05` and `GQ-21` on exactly one shape — a
  dangling first-class edge in the degenerate answer, an edge `as_of()`
  never pruned and which `GQ-21` pins byte-identical. Plan 15.2-05 found
  the contradiction while implementing the reference, resolved it the only
  way consistent with `GQ-21`, and recorded the wording tension as
  DI-15.2-01. Until this amendment that one edge semantic was decided by
  `ccf.graph.fallback::_endpoint_closure`'s docstring rather than by this
  document — the single implementation-defined escape hatch in v1, which
  the reading order at the top of this document does not permit. It is
  closed here, in the document that is supposed to hold it.

  *Clarifying, not behavioral.* Nothing in the tree changes: this states
  what the reference has enforced since 15.2-05 and what every adapter has
  been held to differentially ever since. Conformance is not weakened —
  `tests/conformance/query_corpus.py` generates the dangling-edge shape as
  both a degenerate and a constrained question against every registered
  param, so an adapter scoping closure differently from this clause fails
  `GQ-31` byte-identity.

- **1.0.0** — *plan 15.2-01.* Initial vocabulary: the 35 clauses, including
  `allowed_entities` and the D-IMPL-87 segmentation clauses.
