# CCF SDK — Data Engineering Requirements

**Derived from:** *Context Product Specification Standard v0.3* (18 pp., draft
for Data Engineering review; basis CCF Whitepaper Ch 6 §§6.2–6.5 and Ch 7
§§7.4–7.10 — v1.1 and v1.2 are the same document per Dave's ruling, so the
standard's section citations are authoritative for traceability).

**Role of this document:** requirements input to the CCF SDK build. It tells
Claude Code what data engineers will actually *do* with the SDK — authoring,
validating, binding, assembling, registering, certifying, and operating
Context Products against a format contract — so the SDK plugs the gaps the
whitepaper and CLAUDE.md do not explicitly commit to. It is **subordinate to
the whitepaper and to CLAUDE.md**: where this document surfaces a conflict
with either, the conflict is logged as a decision candidate (§9 below), never
silently absorbed. Where it surfaces a gap, the gap becomes a requirement.

Requirement IDs are `DE-RQ-NN`. Decision candidates are proposed as
`D-IMPL-30` through `D-IMPL-39`, continuing CLAUDE.md's log, which currently
ends at D-IMPL-29. Nothing here is ruled until Dave rules it.

---

## 1. The data engineer the SDK serves

The standard's own definition of done for a spec is the SDK's definition of
its primary user journey: *"a spec written to this standard is complete
enough that a data engineer can identify the source systems, build the
assembly path, register the product, and operate it without a further design
conversation."* Every section of the standard is therefore a station on a
workflow the SDK must make executable:

1. **Author** a Context Product spec (sections A–G plus front matter) against
   a machine-readable schema, with honest gaps marked rather than papered
   over.
2. **Validate** the spec mechanically — completeness, capability gate,
   ontology binding, unowned-gap detection — before any human review.
3. **Bind sources** — declare systems of record, provenance, correlation
   keys, readiness, and identity authority per element.
4. **Build the assembly path** as an operator composition from a closed
   vocabulary with budgets, failure behavior, and composition invariants.
5. **Register** the product: name, address, version, tier, Assembly Mode —
   with registration *blocked* on stated preconditions.
6. **Certify** via fixtures, replay tests, measured latency/cost, and gap
   closure — moving λ_c and debt_tolerance from illustrative to measured.
7. **Operate**: degradation contracts, observability, supersession cascades,
   retention, deprecation.

The SDK's success test against this document: a competent data engineer with
a conforming spec reaches a served, replayable, governed Context Product
using SDK mechanism plus their own configuration — and at no point writes
bespoke platform logic, because *"a spec describing bespoke logic instead of
an operator composition has moved cost from the platform to the product,
which is the failure mode this architecture exists to prevent."*

---

## 2. Spec lifecycle and registration (standard §0, §13, §15)

**DE-RQ-01 — Machine-readable spec artifact.** The SDK defines a spec
artifact schema (`CP-SPEC-{nnn}`) mirroring the standard's section skeleton —
front matter, then sections A (Decision frame), B (Contract), C (Data
catalog), D (Assembly recipe), E (Volatility, debt & materialization), F
(Source binding & readiness), G (Operate & govern) — with all seven sections
structurally required. A section with nothing to say carries a one-line
rationale; an absent section fails validation. The spec document id is stable
across versions of the same product. This artifact is a Control Plane
artifact under the No-Hardcoding Rule and persists via the ArtifactStore.

**DE-RQ-02 — Front matter as registration metadata.** Registry name, tier,
Assembly Mode, cost band, lifecycle state, accountable owner, last review
date, a two-sentence resolution statement, the four-question build-test
result, and a build-order note — all machine-readable, all required before
registration.

**DE-RQ-03 — Four-question build test, recorded.** The SDK records the
four-question test (perspective-dependence, validity window, forensic
reconstructibility, runtime composition) with its answers and, where a yes is
qualified, the stated basis. A product admitted on partials is admitted on a
recorded basis a reviewer can challenge — the SDK stores the basis, not just
the verdict.

**DE-RQ-04 — Placeholder discipline as mechanism.** `[TBC]` markers are
first-class spec objects, each carrying a named owner, each re-surfaced in
§F. Validation enforces the standard's rule directly: *"'does not exist yet'
is a valid state; unattributed is not"* — an unowned gap blocks review
submission. The inverse defect (an invented system name) is caught by
DE-RQ-14's binding checks: an element whose system of record is not a
registered estate system fails validation.

**DE-RQ-05 — Capability gate above §A.** A blocking capability dependency is
declared in front matter, not discovered in §C. Registration surfaces it as a
scheduling decision.

**DE-RQ-06 — Lifecycle state machine.** `draft → in-build → certified →
deprecated`, with date and reviewer per transition. Certification is
evidence-gated (DE-RQ-40); deprecation requires consumer notification (from
the §B consumers list), a sunset date at least one migration window out, and
a named successor or an explicit statement that none exists. The SDK enforces
these transitions; it does not merely record them.

---

## 3. Contract requirements (standard §2, §8, §9)

**DE-RQ-07 — Nine-element contract model.** Schema (ontology-bound,
machine-readable artifact — *"prose is not a contract"*), Freshness SLA
(**per signal class**, never one value per product), TTL (duration plus
`ttl_anchor`: `from_decision` or `from_entity_freshness`; dual TTLs carry
both branches and the selecting condition), Policy Binding (every regime with
a resolvable version id; entitlement scope bound to the actual entitlement
service; classification and residency per DE-RQ-09; past-date pinning
enforced in §D), Lineage (`operators_invoked[]`, `graph_snapshot_at`,
`policy_version`, `projection_plan_id`, passage anchors for text-resting
claims, `context_debt`, `payload_hash`, `model_record` for Modes 2/3 —
omitting `context_debt` is the named common error), Semantic Version
(vMAJOR.MINOR.PATCH with prior supported version and migration window),
Discovery (`domain.product.vN`), Addressability (URL pattern with resolvable
anchor — never an internal surrogate key), and Assembly Mode. *Conflict with
the whitepaper's eight-element specification → D-IMPL-30.*

**DE-RQ-08 — Assembly Mode as registration-time commitment.** Mode 1 (pure
algorithmic), Mode 2 (algorithmic with LLM packaging), Mode 3 (algorithmic
orchestration with agent-swarm assembly), each registered with a one-sentence
cost/quality/determinism rationale. The mode is a documented owner decision,
not an emergent runtime property; changing it is a MAJOR change. This aligns
with the whitepaper's Assembly Modes and with the trust-path-purity
principle already in CLAUDE.md — the SDK makes the commitment enforceable at
registration.

**DE-RQ-09 — Classification, residency, and information barriers.** Policy
Binding carries: data classification (public·internal·confidential·restricted
— the highest of any §C element), information barrier
(none·control-room-restricted·MNPI-bearing), residency constraints
(jurisdictions whose data may not leave, with assembly effect), and
cross-border serving conditions. **The suppression rule is a structural
invariant:** policy-excluded content leaves *no count, marker, or
placeholder* — restricted content is never materialized-then-filtered, and on
an information-barrier product a "3 items hidden" marker is itself a
reportable disclosure. This is Policy-before-Similarity made concrete at the
payload boundary; the SDK enforces it as validation gate (DE-RQ-24), not
convention. It also lands directly on the CB/CIB information-barrier
architecture requirement already flagged in the Wells Fargo strategy work.

**DE-RQ-10 — Model-risk annotation for Modes 2/3.** Pinned model identifier
and version, pinned temperature, versioned and logged prompt template,
model-risk registration reference and validation status, the
substrate/presentation boundary (which fields are algorithmic
artifact-of-record vs model-rendered), and the **smoothing control** — how
the design prevents the model reconciling a conflict the substrate
deliberately surfaced. Mode 1 states "not applicable — no model in the trust
path." The smoothing control operationalizes the "smoothing failure mode"
already named as a monitoring concern in Dave's trust-path-purity principle;
the SDK gives it a required field and a place in replay.

**DE-RQ-11 — Request parameter surface with "Moves" declarations.** Every
parameter declares which dimension it moves (E anchor, R scope, T
reconstruction, P envelope, Π perspective, or a measure); a parameter that
moves nothing is pushed to the consumer. Required on every product: anchor
identifier, `intent` (resolved against the intent registry, DE-RQ-33), and
`debt_tolerance`.

**DE-RQ-12 — Declared-but-inert parameters fail explicitly.** A uniform-
surface parameter unsupported at the product's tier returns
`not_supported_at_tier` — it must never silently succeed against current
state, because *"a parameter that appears to work and does not is worse than
an absent one: it will be relied on in a dispute."* SDK mechanism, not
per-product code.

**DE-RQ-13 — Prerequisites, consumers, and scope boundary.** Prerequisites by
registry name (the build order), consumers as a reverse-dependency list
(required for §E supersession cascades and MAJOR-change notification), and
deliberately-out-of-scope capabilities flagged as *coming next*.

---

## 4. Data catalog requirements (standard §3)

**DE-RQ-14 — Element table as the binding contract.** One row per element:
element in business language, system of record (a named system — "internal"
is not a system), provenance class
(internal-SOR·vendor·public-filing·derived, with derivation appearing in §D),
classification, capability class (a store capability, never a product name),
G dimension (E·R·T·P·Π·L·schema — every element lands somewhere in the graph
or it is not context), and ontology IRI from the shared ontology contract.
**Unbound elements block registration.** Extension classes/properties mint in
the `ex:` namespace, registered centrally with an owner, once — never ad hoc
per product.

**DE-RQ-15 — Capability decomposition and interim posture.** Where a product
depends on a capability the estate may not have, the spec decomposes it into
separable properties, each with a common-estate answer
(widely-available·sometimes·rare) and an if-absent behavior (blocking ·
degrades to a named partial · workaround with stated cost). A partial ships
with an interim posture: which triggers are deliverable, what unsupported
parameters return, what version string the partial ships under. The SDK
models this so *"shipping a partial as though it were complete"* is
structurally impossible.

**DE-RQ-16 — Correlation key with measured coverage.** The identifier(s)
every element joins on, where the crosswalk lives, and its measured coverage
— an unmeasured crosswalk is a stated risk in §F, not a footnote.

**DE-RQ-17 — Single-writer discipline per element.** One authoritative
system per element; where an element exists in two systems today, the spec
names the authority and demotes the other to read replica *as a prerequisite
to build*. This is the whitepaper's single-writer invariant projected onto
source binding; the SDK validates it at the catalog level.

**DE-RQ-18 — Identity authority hierarchy.** Where the anchor identifier
does not cover every entity the product must serve: entity classes tabulated
with identity authority, source-of-record status, and the **freshness
ceiling each class implies**. An anchor that silently excludes a population
propagates the exclusion catalog-wide; the asymmetry belongs in the payload,
never averaged into a single freshness claim.

---

## 5. Assembly requirements (standard §4, §10)

**DE-RQ-19 — Operator step table.** Numbered steps, **one operator per
step** from the closed vocabulary, capability class from §10.1 (never a
product name), inputs, emits (named exactly as they appear in lineage),
failure behavior (fail closed → HTTP code · degrade with debt · skip), and a
p95 budget in milliseconds summing to a stated total against the tier
envelope. A total at 97% of envelope is a design finding the SDK surfaces —
which step dominates, what the first optimization would be. The final step is
always contract assembly.

**DE-RQ-20 — Closed operator vocabulary and capability classes.** The
standard commits eight operators — Resolve, Policy, Projection, Traversal,
Enrich (always batched), Similarity, Evaluate
(aggregate·score·reconcile·rank modes), Federate — each with reads
(capability classes), emits, and cost driver; and seven capability classes
(relational, bitemporal-ledger, graph-traversal, document-passage,
vector-index, federated-external, in-memory). Estate binding lives in **one
platform-owned artifact**; product specs never name a database. Retired
names (Batch Enrich, Temporal Traversal, Aggregate/Score/Reconcile/Rank,
Compose) are rejected by validation. *Relationship to the whitepaper's four
canonical operator categories → D-IMPL-31.*

**DE-RQ-21 — Composition invariants as CI-testable rules.** (1) Policy
before anything that reads graph state — impermissible content is never
materialized then filtered; (2) Resolve before Traversal; (3) Enrich is
batched, always — one query per source per step; (4) algorithmic substrate
before any semantic stage, with the substrate remaining artifact-of-record.
Invariant 4 is the Alternation invariant CLAUDE.md already enforces;
invariants 1–3 extend the composition-preservation test surface.

**DE-RQ-22 — Determinism class and payload hash.** `deterministic` (Mode 1:
same anchor + as_of + policy_version + graph snapshot → byte-identical
payload) and `substrate-deterministic` (Modes 2/3: algorithmic substrate
byte-identical; presentation reproducible only under pinned model,
temperature, prompt). Every product publishes a payload hash over the
deterministic portion, excluding `assembled_at`. **Replay asserts hash
equality, not similarity** — "a similar product" is a defect recorded in §G,
not a caveat.

**DE-RQ-23 — Falsifiable replay test as a runnable procedure.** The SDK
ships the four-step pattern as executable machinery: serve and record the
snapshot → mutate underlying state → re-derive live and confirm the new
value → re-derive at the recorded snapshot and confirm the *original*
returns. If the final step returns the new value, the snapshot is not
load-bearing and `graph_snapshot_at` is decorative. Products carrying two
time axes add a second test constructing a case where the axes **disagree**
— agreement means a filter was dropped ("two filters on two axes are two
filters," separately parameterized, separately testable).

**DE-RQ-24 — Six universal validation gates.** Empty-operator guard
(empty is fail-closed or an explicit debt contribution, never silent),
lineage strict equality, TTL bounds (dual-TTL branch matches its condition),
**debt gate** (assembly halts and returns the debt signal where D_c exceeds
debt_tolerance), **suppression silence** (DE-RQ-09), and **classification
containment** (no element above declared classification in the payload) —
applying to every product without re-argument. Plus product-specific gates,
each a testable assertion naming the defect it detects, cross-referenced to
a fixture ID. *CLAUDE.md commits three gates; the standard commits six →
D-IMPL-32.*

**DE-RQ-25 — Counterfactual acceptance test.** §A's counterfactual is an
executable test, not a narrative: the query, the two answers (conventional
data product vs Context Product), and the condition under which they must
differ — with the failure mode drawn from the closed taxonomy
(context-starved · temporally-incoherent · perspective-flat · policy-blind ·
evidence-free). Where they agree, the product is not doing the work the
counterfactual claims. The SDK makes this runnable against the built
product, because the reviewer's first checklist question is whether they can
run it and watch it fail.

---

## 6. Volatility, debt, and materialization requirements (standard §5)

**DE-RQ-26 — Half-life table with calibration basis.** One row per signal
class: λ_c, calibration basis (**illustrative · expert · measured**), decay
driver, supersession event, owner. λ_c remains **Control Plane configuration
per observation type** — a spec's table is an initial calibration proposal;
conflicts between specs resolve centrally. The SDK models the basis field so
"a value an engineer can challenge" and "a number they assume was measured"
are distinguishable states, with review cadence (annually, or on
supersession-pattern change) trackable.

**DE-RQ-27 — Multiplicative debt model with per-component decomposition.**
`D_c = 1 − (F·C·S)` — multiplicative so a collapsed dimension forces
escalation rather than averaging away; **F normalized over required signal
classes, not classes present**, or losing a source improves the freshness
score. Beyond the model: a per-component debt table (component,
may-be-absent, D_c contribution weight, behavior-when-absent: fail closed ·
serve with flag · mark the affected claim `NOT_EVALUABLE`). **Debt
decomposes per claim, never only per product** — four claims with one
missing input return three evaluated claims and one marked unusable, not a
product-level failure and never a silently-omitted fourth. The gap is
captured *before* the decision and shapes it: a decision input, not a log
line. *Extension to CLAUDE.md's D_c mechanism → D-IMPL-36.*

**DE-RQ-28 — Materialization posture and cache correctness.**
`materialized · derived-on-demand · split` (with fields and reasons), tested
mechanically: if the fastest-moving input's λ_c is shorter than the intended
cache window, the materialization is wrong. The cache key is explicit —
tenant, schema name, plan id, snapshot, time-axis parameters, principal
binding — because a key missing a payload-changing parameter is a
correctness defect presenting as an intermittent one.

**DE-RQ-29 — Supersession triggers and lazy cascade.** Each supersession
event marked local or cascading; cascading names downstream products from
the §B consumers list, and invalidation cascades to **every product whose
`operators_invoked` touched the superseded entity**, not only those named.
Re-derivation is lazy — invalidate for next request, never re-materialize
eagerly, or a routine upstream publication becomes a thundering-herd event
across the catalog. *Cascade engine as SDK mechanism → D-IMPL-37.*

---

## 7. Source readiness and operations requirements (standard §6, §7)

**DE-RQ-30 — Readiness table with owned gaps.** Per element: system of
record, interface and cadence, available-today (yes · partial with named
fields · no), gap owner, blocker — closed with access path (feed, CDC, API,
event stream, new build), identifier reality, **history depth** (which
bounds any `as_of` the contract advertises — where a source publishes
snapshots without history, *start retaining deltas now*), the text-source
boundary (build-time extraction vs runtime operator — runtime document reach
changes capability class and cost band), and **first-build volumetrics**:
the population the first build must contain for every gate and
counterfactual to act on; where a required case does not occur naturally,
widen the sample until it does.

**DE-RQ-31 — Operate & govern contract.** Accountable owner as roles, not
individuals; service objectives (p50/p95 assembly latency, expected volume,
concurrency ceiling, payload bound, absolute per-call cost alongside the
relative band); degradation contract per input class (partial payload with
elevated D_c, or fail closed — mandatory classes named explicitly); debt
model bindings (which inputs drive F, C, S; debt_tolerance default and
basis); retention and record-of-record (the fabric references the system of
record, never replaces it; replay-record retention tier — full-fidelity ·
compressed · tombstoned — with the severity rule that assigns it); named
test fixtures (`{PREFIX}-{F/G/D/R}{nn}` for happy path, each gate, each
degradation branch, and a replay hash assertion); lifecycle per DE-RQ-06.

**DE-RQ-32 — Observability as the calibration evidence base.** Per-operator
latency, D_c distribution, gate-failure counts by gate, cache hit rate,
entitlement denials, degradation-branch frequency, supersession-triggered
invalidations — explicitly the evidence base for moving λ_c and
debt_tolerance from illustrative to measured. This closes the loop with the
whitepaper's closed-loop self-learning ("the loop is in the graph, not the
model") and gives the SDK's logging hooks a required metric surface.

---

## 8. Wire contract, registries, and versioning (standard §8–§9, §11–§12)

**DE-RQ-33 — Uniform response envelope.** Every product returns the same
envelope — *"a wire contract, not a style guide"*: `product`,
`semantic_version`, `payload`, `contract` (`assembled_at`, `expires_at`,
`ttl_anchor`, `ttl_basis`, `assembly_mode`, `determinism_class`,
`freshness[]` with per-signal-class `observed_at`, `lambda_c_hours`,
`relevance`), `lineage` (`operators_invoked[]`, `graph_snapshot_at`,
`policy_version`, `projection_plan_id`, `model_record`, `payload_hash`),
`context_debt` (`F`, `C`, `S`, `D_c`, `contributions[]`), `notices[]`.
Rules: **payload is never returned without contract, lineage, and
context_debt** — a consumer receiving context with no debt signal cannot
know what it is trusting; `notices` is for degradation the consumer must
see, never logging, and policy-suppressed content never appears there. A
consumer that must special-case a product's response shape *"does not have a
contract, it has an integration."* This refines the Context Product Contract
already committed in CLAUDE.md with a concrete serialization.

**DE-RQ-34 — Error semantics taxonomy.** Anchor unresolvable → 404 (never an
empty payload); principal not entitled → 403 with no detail on what exists
(existence is itself disclosure); parameter unsupported at tier → 400
`not_supported_at_tier`; debt gate exceeded → 409 with the debt block (not a
200 with a warning); mandatory input unavailable → 503 naming the failed
source class (silence is not a negative answer — an unretrieved screening
source is not a clean screen); non-mandatory input unavailable → 200 with
notices and elevated D_c. §D names which step raises which. *Adoption into
the Experience Layer HTTP surface → D-IMPL-35.*

**DE-RQ-35 — Shared-contract registries.** Six artifacts referenced by every
spec, of which only ontology/IRI binding exists in the standard's estate
today — the rest **block certification, not build**: intent registry (intent
id, plain-language decision, policy envelope selected, permitted principals,
accepting products, owner, effective date/version, deprecation status),
projection plan registry (plan id, principals, *what is assembled
differently* — a plan whose difference is presentational is rejected —
entitlement precondition, suppression behavior, owner, version), policy
version registry (versioned envelopes with effective dates, resolvable at
replay), half-life calibration table (DE-RQ-26), capability binding
(capability class → estate system, per environment, platform-owned). The SDK
ships registry primitives for all six as Control Plane artifacts; the
*values* are the deployment's. *→ D-IMPL-38.*

**DE-RQ-36 — Naming and addressing conventions.** Registry name
`domain.product.vN` (kebab-case, N = MAJOR only), address
`/context-products/{domain}/{product}/{anchor-id}`, schema artifact
`schemas/{payload_type}.v{MAJOR}.json`, fixture and spec-document id
patterns per DE-RQ-31/DE-RQ-01. SDK validators enforce these as configurable
conventions with the standard's patterns as reference defaults.

**DE-RQ-37 — Change classes with consumer impact.** PATCH (gate, telemetry,
documentation — no impact), MINOR (additive field, new optional parameter,
new projection plan, λ_c recalibration — backward compatible, notify
consumers), MAJOR (field removed/retyped, parameter default changed,
`ttl_anchor` changed, Assembly Mode changed, policy envelope semantics
changed — migration window required, both versions served). **A λ_c or
debt_tolerance change is MINOR by type and material by effect** — it changes
outputs without changing shape, so the SDK announces it to consumers
explicitly rather than letting it surface as unexplained behavior change.

**DE-RQ-38 — Tier model and cost estimation.** Tiers 1–5 by capability
classes with cost bands and required review chains (product owner →
+platform → +second line where P is regulatory → +evidence-chain review →
+legal/control room); tiers describe assembly complexity, **not build
order** — build order comes from the prerequisite graph. Cost estimation
formula (baseline × traversal fan-out term × enrich-sources term ×
mode multiplier [Mode 1 = 1, Mode 2 ≈ 3–5, Mode 3 ≈ 15] × materialization
factor) with recorded assumptions — **state the p95 fan-out, not the mean**,
because the commonest cost surprise is a traversal estimated on the median
entity and paid on the tail. *Mechanism-vs-values boundary → D-IMPL-34: the
tier field, review-chain hooks, and estimator are SDK mechanism; CB/CIB's
specific bands, chains, and multipliers are deployment values.*

**DE-RQ-39 — Reviewer checklist and definition of done as CI.** The §14
six-question reviewer read (counterfactual falsifiable? capabilities not
products? every gap owned? one closed-vocabulary operator per step? debt
decomposed per claim? payload carries types?) and the §15 definition-of-done
list map onto SDK validation: the first three checklist items are rejection
gates, mechanically checkable, and belong in `ccf spec validate`; the §15
items define the spec-complete state registration requires.

**DE-RQ-40 — Certification evidence.** Moving to `certified` requires on
file: published schema artifact; all fixtures passing including the replay
hash assertion; measured p95 latency and per-call cost; debt_tolerance
justified against observed data; every §F gap closed or accepted by a named
owner; and, for Modes 2/3, complete model-risk registration. The SDK's
lifecycle transition (DE-RQ-06) checks this list mechanically.

---

## 9. Conflicts and decision candidates (proposed D-IMPL-30 … D-IMPL-39)

Two genuine conflicts with existing commitments, and eight extensions the
standard implies that current CLAUDE.md scope does not explicitly cover.
None is ruled here.

- **D-IMPL-30 — Nine-element vs eight-element contract.** The whitepaper
  (§6.3) commits eight elements; the standard adds Assembly Mode as a ninth.
  Recommended resolution: adopt Assembly Mode as a required SDK contract
  extension (it operationalizes the whitepaper's own Assembly Modes and the
  trust-path-purity principle), labeled SDK-defined per CLAUDE.md §1's
  extension discipline. Needs Dave's ruling because it touches the Context
  Product Contract base.
- **D-IMPL-31 — Closed operator vocabulary vs four canonical categories.**
  The whitepaper commits four operator categories (Traversal, Temporal,
  Policy, Similarity) with a composition algebra; the standard commits a
  closed eight-operator vocabulary (Resolve, Policy, Projection, Traversal,
  Enrich, Similarity, Evaluate, Federate) over seven capability classes.
  These are reconcilable — the vocabulary reads as a naming/authoring layer
  over the algebra, with Temporal absorbed into Traversal modes and
  Resolve/Enrich/Evaluate/Federate as category refinements — but the mapping
  must be *ruled*, because composition-preservation tests and lineage naming
  both depend on which layer is canonical.
- **D-IMPL-32 — Three vs six universal validation gates.** Extend the SDK's
  gate set with debt gate, suppression silence, classification containment?
  Recommended yes: all three are mechanism, all three are whitepaper-
  consistent, and suppression silence is load-bearing for information-
  barrier deployments.
- **D-IMPL-33 — Capability classes and estate binding.** Ship the
  capability-class taxonomy and the platform-owned capability-binding
  artifact as SDK primitives (specs never name a database)?
- **D-IMPL-34 — Tier/review/cost model boundary.** Which parts are SDK
  mechanism (tier field, review-chain hook, cost estimator with recorded
  assumptions) vs deployment values (band multipliers, chain composition)?
- **D-IMPL-35 — HTTP error taxonomy adoption** into the Experience Layer
  API skeleton (interacts with D-IMPL-23).
- **D-IMPL-36 — Per-claim debt decomposition** extension to the D_c
  mechanism, including `NOT_EVALUABLE` claim marking and the per-component
  debt table.
- **D-IMPL-37 — Supersession cascade engine** (local/cascading triggers,
  operators_invoked-based cascade resolution, lazy invalidation) — interacts
  with D-IMPL-06/26/27 snapshot and artifact machinery.
- **D-IMPL-38 — Shared-contract registries** (intent, projection plan,
  policy version, capability binding) as Control Plane artifact types with
  SDK registry primitives.
- **D-IMPL-39 — Spec artifact schema, registration gating, and
  certification lifecycle** (`CP-SPEC` as a first-class Control Plane
  artifact with `ccf spec` CLI surface) — the largest single addition, and
  the one that most directly serves the data-engineer journey in §1.

---

## 10. Mechanism-vs-values discipline applied to this document

Consistent with CLAUDE.md's core boundary: the SDK takes from this standard
its **shapes** — the spec schema, the gate set, the debt decomposition, the
envelope, the registries, the lifecycle — and leaves its **values** — CB/CIB
tier bands and review chains, the specific provenance-class list where it is
org-specific, information-barrier vocabulary, cost multipliers, λ_c numbers —
to deployment configuration and to the neutral-domain examples suite. Where
this document quotes a CB/CIB-specific value, it is illustrating the shape,
not importing the value.

## 11. Errata against the source standard (for Dave's Word document)

Found during parse; fix before Data Engineering circulation:

1. Rule 4 (p.1) cites "§10" for the response envelope; the envelope is §8.
2. §A Consuming principals (p.3) cites "§13.2" for projection plans; the
   projection plan record is §11.2.
3. §2.4 (p.5) cites "§13.1" for the intent registry; the intent registry
   record is §11.1.

These read as remnants of a renumbering pass. The traceability in this
document uses the final section numbers as printed.
