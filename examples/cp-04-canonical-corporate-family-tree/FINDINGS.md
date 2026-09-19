# Findings — cp-04-canonical

Findings raised while authoring this successor against the current SDK surface.
Each is adjudicated under `D-IMPL-315`: *"canonical path is richer"* is a
finding to adjudicate, never a licence to edit the example. The question asked
of every one is whether the behavior is **legitimate SDK semantics** or an
**actual mismatch**, with the basis stated.

---

## `CP04C-F-01` — Entity identity is POSITION-DEPENDENT, so endpoint selection cannot build a graph in which a node appears as both subject and object

**Status: FIXED-`D-IMPL-316` (2026-09-10). Adjudicated as a MISMATCH and
repaired as a bounded SDK fix on Dave's ruling. Reading 2 was taken: an entity
rule declares which payload field supplies a declared identity key, and the
DECLARED key is still what is hashed. The global content-hash and identity
model is untouched, the repair is hash-transparent, and no workaround was
applied — `admit_relationship_claim` was explicitly not used.**

### What the successor was doing

Declaring typed family edges through the resolution spec. cp-04 could not do
this — it recorded `24.4-D-35`, *"the declared resolution spec cannot express a
typed edge"*, and shipped one envelope per node plus explicit
`AssemblyWorker.admit_relationship_claim` calls for every edge.

**That gap is genuinely closed**, and finding it closed is the charter working
as intended: `24.5-L-21` added predicate selection and endpoint selection, and
`RelationshipResolutionRule`'s docstring closes `24.4-D-35` by name. Measured
live — three envelopes carrying `{parent, child, predicate}` minted exactly three
correctly-typed edges, with `owns` and `controls` selected by the payload and
the mutual pair preserved. Copying cp-04's shape would have reproduced a
workaround for a gap that no longer exists, and taught it as current practice.

### The miss

`AssemblyWorker` derives a URI as
`f"{rule.entity_class}://{content_hash(identity)}"` where
`identity = {key: str(payload[key]) for key in rule.identity_keys}`
(`src/ccf/assembly/worker.py::SpecDrivenEntityResolution.resolve`). The hash is
over a **mapping**, so the identity key's *name* is inside it.

Endpoint selection requires the two endpoints to come from two different entity
rules reading two different payload keys. Therefore the two endpoints
necessarily hash different key names, and **the same real-world node receives a
different URI depending on which position it was observed in.**

Both limbs measured:

| limb | declaration | result |
|---|---|---|
| different identity key names (`parent_uri`, `child_uri`) | the only shape endpoint selection permits | edges mint, but 3 real nodes became **5 entities** — `A` as parent `d838f82d…` and `A` as child `5e412b3e…` |
| one shared identity key name (`entity_uri`) | makes identities comparable | both rules read the one value the payload can hold, subject == object, the SDK correctly refuses the self-loop → **0 relationships** |

Hash inputs confirmed directly:
`content_hash({"parent_uri": "A"})` = `d838f82d…`,
`content_hash({"child_uri": "A"})` = `5e412b3e…`, not equal — and those are the
same digests the live fabric produced, so the two measurements agree end to end.

### Why this is a mismatch rather than legitimate semantics

Three grounds, and the adjudication does not rest on preference:

1. **The feature's own docstring names the case it cannot serve.** It states
   endpoint selection *"lets one envelope carrying `{parent, child, predicate}`
   mint a single edge between two entities of the same class."* It does — but
   only in a graph where no node is ever both a parent and a child. This
   fixture's family contains **22 mutual pairs**, so the ordinary case is the
   unsupported one.
2. **It contradicts the invariant the field's own docstring cites.**
   `identity_keys` is documented as making *"the URI stable across
   source-system change (INV-CH7-18)."* If the key's name is inside the
   identity, renaming a source field changes every URI, and two sources
   describing one entity under their own vocabularies can never resolve to one
   URI — which also blocks the multi-source lineage accumulation of
   INV-CH7-17.
3. **The existing test cannot see it.**
   `tests/assembly/test_worker.py::test_a_member_to_member_edge_is_expressible_from_one_envelope`
   ingests one envelope with one parent and one child and asserts
   `subject_uri != object_uri`. That passes for two genuinely different nodes
   and would pass equally if identity were position-dependent, which it is. The
   assertion the case needs — *the same node in both positions is one entity* —
   is absent.

### What was NOT done

- **No workaround.** `admit_relationship_claim` would sidestep this entirely,
  and it is exactly cp-04's shape; reaching for it would make the successor a
  cleaned-up cp-04 and would bury a live SDK defect under an example's
  cleverness.
- **No SDK edit.** Remediation is a ruling, not this sitting's to take.
- **cp-04 untouched** (`D-IMPL-261`).

### Readings for the ruling — none asserted

1. **Identity hashes VALUES in `identity_keys` order, not the mapping.** Makes a
   URI independent of the payload key that carried it, which is what
   INV-CH7-18 appears to promise. Changes existing entity URIs, so every pinned
   address moves — pre-v0, `D-IMPL-293` says that is a consequence to
   regenerate rather than a reason to prefer the smaller change.
2. **An entity rule declares an identity ALIAS** — the logical identity name,
   separate from the payload key that supplies it. Additive; existing rules keep
   their URIs by aliasing to their current key name.
3. **Accept the limitation and narrow the claim.** Same-class typed edges keep
   coming through `admit_relationship_claim`; the docstring stops asserting the
   case it cannot serve, and `24.4-D-35` is recorded as narrowed rather than
   closed.

Reading 1 is the one that makes the documented invariant true; reading 2 is the
one that costs nothing already shipped. **The choice is Dave's.**

---

## `CP04C-F-02` — the debt denominator is the operator view, not the served roster

**Status: CLOSED — reading 1 taken (Dave, 2026-09-10). Acquisition reads at the
governed effective depth, so L3, the operator view and the payload are one set
and `D_c` moves with the served roster. The scorer was NOT changed: whether
debt-over-payload is the right product rule for every deployment is a later
`D-IMPL`, and this tree does not paper over a global semantic by special-casing
one example.**

### After the repair, measured

| request | scorer saw | payload served | `D_c` |
|---|---|---|---|
| `max_depth=1` | 36 / 16 | 36 / 16 | **0.555556** |
| `max_depth=3` | 49 / 29 | 49 / 29 | **0.408163** |
| `max_depth=99` | — | refused `bound-exceeded`, authority `technical` | — |

Dave's stop condition — *"stop if acquire-at-effective-depth still leaves the
scorer on a 50/30 view while the payload is 36/16"* — was **not** triggered: the
two sets match exactly at both depths, so the walk is genuinely bounded.

`depth_limit` remains the technical ceiling and still refuses `max_depth=99`.
Π still clips to the same number, deliberately: depth must exist in more than
one place or a change in either would go unnoticed. The clip is now a no-op on a
correctly bounded read rather than the thing doing the bounding.

**The original finding, preserved:**

### What is measured

`GovernedResolver` calls the debt scorer as
`self.debt_scorer(view=execution.view, evidence=ExecutionEvidence.of(execution))`.
`execution.view` is the view the **operators** produced. `ExecutionResult` also
carries `projection`, and the scorer is not given it. `ExecutionEvidence` is
explicitly cardinality-free — *"no count of rows appears here, because a row
count is the cardinality the ruling removes from this computation"*
(`D-IMPL-255`).

This deployment applies the caller's depth at **Π**, so the served roster is a
subset of the operator view:

| request | scorer saw | payload served | `D_c` served |
|---|---|---|---|
| `max_depth=1` | 50 nodes / 30 resolved | 36 nodes / 16 resolved | **0.4** (should be 0.556) |
| `max_depth=3` | 50 nodes / 30 resolved | 49 nodes / 29 resolved | **0.4** (should be 0.408) |

A debt that is identical whatever the product served is the *"scalar that
cannot fail through the door"* cp-04's specification was corrected for — the
same defect, reached from the opposite direction.

### Adjudication under `D-IMPL-315`

**Legitimate SDK semantics.** Debt is measured over what was *assembled*; a
projection that then serves less is choosing to serve less. Asking the SDK to
score the projection's output would make Π an input to its own governance. The
example is the side that must move.

### Why it is not fixed here

Every available fix interacts with a **ruled** constraint, so choosing one is
not this sitting's call:

1. **Acquire at the effective depth** so L3 == served roster == operator view,
   and Π filters nothing. This is cp-04's shape and it is the only option that
   makes all three sets equal. Cost: the deployment must learn the governed
   `max_depth` *before* the resolver runs, by calling the SDK's public
   `resolve_effective_request` / `ReferencePolicyConstraintResolver` itself. Not
   a local binder — it binds nothing onto a Control Plane declaration — but it
   is a **second derivation** of one value, which the resolver's own comments
   warn is how replay drifts.
2. **Bind `depth_limit` to the effective `max_depth`** so the *operator* does
   the bounding and the view the scorer sees is already the served set. This is
   the cleanest mechanically and is **refused by a standing ruling**:
   `depth_limit` is the technical operator ceiling (Dave, this sitting), and the
   artifact does not admit a `RequestBoundParameter` on that field anyway.
3. **Serve everything acquired** and let `max_depth` condition nothing. Rejected
   on its face: the caller's depth would stop affecting the answer.

**Reading 1 is the only one consistent with the ruled constraints**, and its
cost is a second, deterministic resolution of the same value. Recommended, not
taken.

### What holds regardless

The structural properties are already proved and do not depend on this fork:
`shape_of == "canonical"`, and `_sdk_supplied_operator_set == True` on all five
conditions with the factory's plan sources reading `(('required',),)`.


## Re-expressed on the paved road — CP-14 Gate 2 slice 2 (2026-09-15)

Classified **A** under Dave's slice-2 vocabulary (paved-road compatible: the
existing governed implementation exposed with `open_product` → `open_door`
and minimal product binding) by a four-tree census and an independent pass,
and chosen as the cheapest honest second producer. Nothing about the product's
business behavior changed — measured by content address at a pinned instant
(`2da50196…`, identical before and after; payload, debt, expiry and dimension-2
policy pins identical).

| Id | Observation | Category (`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B) | Disposition |
| --- | --- | --- | --- |
| `CP04C-F-03` | **One number was stated in two documents, and the road collapsed it.** `backends.yaml`'s `max_traversal_depth: 6` restated the traversal operator's `depth_limit: 6` — the same backend ceiling. The environment document cannot carry a literal (a setting is an environment-variable NAME), and the SDK's own `_capabilities_of` derives no ceiling for a dev fabric, so the capability is now read off the ONE declaration in `ccf_config.yaml` (`deployment.py::traversal_capability`). The capability's recorded identity changed from `corporate_family_graph/max_traversal_depth=6` to `traversal.typed-neighborhood/depth_limit=6`; the product's address did not | 2 · ergonomics, closed for this tree (one authority) — and a §I note: the road offers no seam that hands a source leg's technical capability from the environment document to `open_product`; a deployment with a ceiling that is genuinely environmental rather than declared would read the document itself | Closed here; backlog note |
| `CP04C-F-04` | **The road turned two DERIVED TTL figures into a restated declaration.** `FamilyScenario` derived the class ceiling from `half_life.ownership_edges` and the product window from `half_life.entity_attributes`; the SDK's contract keeps TTL as its own declaration (`ttl:`), so the two numbers now appear beside the half-life rows they equal. One number in two places, by the SDK's contract rather than by this tree's choice | 3 · post-launch: a `ttl:` binding that may reference a half-life class instead of restating seconds | Backlog; disclosed in `ccf_config.yaml` |
| `CP04C-F-05` | **The post-ingest ordering assertion has no home on the road.** The canonical `ingest` read the view after writing and raised if any node had lost its attributes to a later thin edge claim. The paved seam ingests what `acquire` yields and holds no reader; the ordering contract is now held by `deployment.envelopes` yielding every edge before any node. The defensive check is dropped, not moved — its class of defect is an ingestion-order mistake this module can no longer make by accident | 4 · example (a defensive assertion, not a product property) | Recorded |
| `CP14-F-21`, here | An unresolvable anchor still RAISES `LookupError` inside `acquire`; through the door it surfaces as an opaque runtime failure and at a consumer as `producer-unavailable`. Unchanged by the road, by ruling (kept open) | open, ruled | Not repaired |
| `D-IMPL-341` / `CP03C-F-01`, here | `ttl_anchor: from_entity_freshness` is declared and unread; `expires_at` is decision-anchored (`asked_at` + 30 days) before and after | open, ruled | Not repaired |
| `CP04C-F-06` | **The class declared an anchor the source cannot supply.** `D-IMPL-341` made `from_entity_freshness` real, and the first thing it measured here was that no family edge in `fibo-v2` carries an assertion instant: `owns` / `controls` are bare triples, the nearest `validFrom` is a `prior-obs-…` supersession record shared by 84 subjects, and every family claim is dated by the question instant. Under the ruled mechanism that class would have served an "evidence" anchor equal to the decision instant — a decision anchor under the other name — so the declaration was corrected to `from_decision` (config, spec element 8, §E) rather than a row invented to satisfy it. The served `expires_at` is unchanged in value (`decided_at` + 30 days) and now carries `ttl_anchor_at` = the decision instant with the basis that produced it. What would let the class return to an evidence anchor: a GLEIF RR-CDF record date ingested onto the edge claims as their `observed_time`. **Reproduce the premise** (read-only, against `fibo-v2` on the estate; measured 2026-09-18): `SELECT (COUNT(?s) AS ?edges) (COUNT(?d) AS ?dated) WHERE { ?s ?p ?o . FILTER(CONTAINS(STR(?p), "owns") || CONTAINS(STR(?p), "controls")) OPTIONAL { ?s ?dp ?d . FILTER(CONTAINS(STR(?dp), "Date") || CONTAINS(STR(?dp), "assertedAt") || CONTAINS(STR(?dp), "validFrom")) } }` → **639 edges, 0 dated**. The gate is `CFC-G14` | 2 · product contract, closed for this tree (the declaration now says what the product does) | Closed here (2026-09-18) |
