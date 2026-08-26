# Phase 24: Context Production — Assembling Context Products from Simple to Complex - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning — as an UMBRELLA. The first buildable unit is **24.1**, scoped below.

<domain>
## Phase Boundary

Context Product creation — the heart of the CCF SDK — demonstrated through a
ladder of examples that grows from a single-store deterministic assembly to
agentic assembly across an A2A boundary. Every example prints its
**specification** and the **resulting JSON dataset** side by side.

**PHASE 24 IS AN UMBRELLA, NOT A SINGLE BUILD.** Dave ruled 2026-08-25:
*"Let's not lock into an approach just yet... We take one step at a time and
discuss what the next example will be... We can number our phases with minor
numbers such as 24.1, 24.2."* Each minor phase builds ONE example, is
DISCUSSED before it starts, and the ladder is re-evaluated after each. Do not
plan 24.2 from this document — plan **24.1** only.

</domain>

<decisions>
## Implementation Decisions

### The specification defines what the SDK must implement — CORRECTED 2026-08-25

**This block REPLACES an earlier reading that had the arrow backwards.** The
superseded text said the Standard was DE-binding and that nothing from it
entered the SDK, so an inexpressible construct was merely "a recorded
finding". Dave corrected it, and the correction is load-bearing enough that
the old reading is named rather than quietly deleted.

- **D-01: The Context Product Specification Standard DEFINES WHAT NEEDS TO BE IMPLEMENTED IN THE SDK.** Dave, verbatim: *"The more important document is the specification document as it defines what needs to be implemented in the SDK. That is really the important item. The DE is responsible for implementing the specification but the spec must be implementable in the SDK (see the Counterparty Reference Snapshot document)."* The specification is a REQUIREMENTS SOURCE for the SDK, not merely an authoring convention DEs work within.
- **D-02: The DE has responsibilities BOTH OUTSIDE and WITHIN the SDK.** Outside: sourcing, business framing, authoring the spec document, operating the product. Within: building the assembly against SDK mechanism. Neither half is the whole job, and the earlier reading collapsed them into "outside".
- **D-03: THESE EXAMPLES EXIST TO PRESSURE TEST THE SDK.** Dave: *"That is why these examples were formed because we need a way to pressure test the surface and capabilities of the SDK."* An example is not a demonstration of something already known to work — it is the instrument that finds out.
- **D-04: WHERE THE SDK CANNOT SUPPORT WHAT THE SPECIFICATION ORDERS, THE SDK IS EXTENDED IN A SEPARATE PHASE.** Dave: *"If the SDK cannot support what the specification is ordering, then we need to extend the SDK using a separate phase."* **A minor phase does NOT close its own gaps.** It builds the example, records the gap precisely enough to be actionable, and the extension is separately scoped and separately gated.
- **D-05: THE EXPECTATION IS FEW OR NO GAPS, AND THAT EXPECTATION IS ITSELF A TEST.** Dave: *"The spec was originally derived from the requirements specification of the SDK so in theory there should not be many changes if any."* **A long gap list is therefore a SIGNAL OF DRIFT, not a normal outcome** — it means the spec and the SDK requirements diverged after the derivation, and the divergence is the finding. Any gap must be checked for this before it is proposed as SDK work.

### Adding what is missing — incremental, and the acceptance test for an operator

- **D-06: Missing capability is added ONE AT A TIME, as the examples pressure test the SDK.** Dave, 2026-08-25: *"If the operators don't exist we need to add them one at a time as the examples pressure test the CCF SDK."*
- **D-07: NO RETROFITTING. Work already done is NOT brought in line.** Dave: *"There is no reason we must update all of the work that has been done to date. I don't want to spend that money or time. We are adding new capabilities that are getting exercised through these examples."* A gap record must therefore scope itself to the NEW capability the example needs, never to a sweep of existing operators, examples or products.
- **D-08: THE ACCEPTANCE TEST FOR ANY OPERATOR ADDED TO THE SDK.** It must be **EITHER extensible via Protocol, OR provide functionality that is USE-CASE AGNOSTIC.** Dave: *"Otherwise it is a bespoke implementation designed for a specific use case."* This is `CLAUDE.md`'s *mechanism, not values* and *prefer Protocols over inheritance* sharpened into a PASS/FAIL test on a proposed operator.
- **D-09: A capability that fails `D-08` is a finding, not a build.** If a missing capability can only be stated in terms of one use case's values, entities or thresholds, it belongs in the EXAMPLE'S DEFINITION ARTIFACTS, not in `/src`. Recording that is a genuine result of the pressure test — it says the SDK is right and the spec's step was domain-specific.
- **D-10: Registering a new operator NAME under an existing category is additive; needing a new CATEGORY is not.** `OperatorCategory` is a closed `Literal["policy","similarity","temporal","traversal"]` while `Operator` is a Protocol and `OperatorRegistry` is open. A gap record must state which of the two it needs, because the second reopens the whitepaper's operator algebra and is a different class of decision.

### 24.1 — the first example

- **D-11: 24.1 is a NEW, INVENTED, genuinely simple Context Product** in the shape of the existing client example (`examples/hw1-companies-over-revenue`, *"companies over a revenue threshold you choose"*). Dave: *"I want the first example to be a simple context product that does not span multiple data stores. We may have to make one up like we did in the client example."*
- **D-12: Subject — institutional holders of a company with a position above a threshold the caller chooses.** One anchor entity, one caller parameter, ONE source. Dave named this shape: *"investors who have a larger than X stake in a company."*
- **D-13: ONE store, ONE system of record — SEC Form 13F, in `ccf_dataprep`'s Postgres (`ccf_v2`).** Real public data; `ccf_dataprep/sources/13f` and `generators/fetch_13f.py` already exist.
- **D-14: In-process DETERMINISTIC operator. Assembly Mode 1.** Dave: *"For the first example I want to use an in process deterministic operator to assemble the context product."* No LLM anywhere in the assembly path.
- **D-15: CI posture — LIVE-LEG, outside the always-on `examples:` aggregate.** Follows the `s1-00` precedent exactly: a networked substrate cannot sit in the always-on job. **This is a deliberate cost, accepted so the example points at a real store rather than a shipped copy.**
- **D-16: The spec is authored to the FULL Standard** — front matter plus sections A–G — so the phase validates the AUTHORING path and not merely the assembly path. A reduced spec would prove nothing about the Standard.
- **D-17: The example prints its SPECIFICATION and the RESULTING JSON.** This is Dave's stated requirement for every example in the ladder.

### Example tree naming — RULED 2026-08-25

- **D-18: Context Production example trees are named `cp-NN-<slug>`.** `examples/cp-00-institutional-holders` is 24.1; `examples/cp-01-counterparty-reference` is 24.2. Make targets parallel the existing shape: `example-cp-00`, `example-cp-01`. Zero-based, matching `s1-00` and the archived trees.
- **D-19: `NN` is BUILD ORDER — not tier, not spec id.** The spec id lives in the README front matter. Spec-id naming would run backwards from day one, because `CP-SPEC-001` is 24.2 while the new product is 24.1.
- **D-20: The `sN-` scheme is NOT revived, and the reason is on the record.** `s1-`/`s2-`/`s3-` encode documentation Sections 1/2/3 from **Phase 16's documentation rewrite, RETIRED at `D-IMPL-152`**. Sections 2 and 3 were never built. Adopting a taxonomy from a retired approach is the Phase 16 failure mode Dave named when he deferred `DOCS-14`/`EXAM-02` — *"docs against a surface that does not survive."* The scheme had already drifted before it died: `hw1-harness-clients` is functionally Section-2 content that never took an `s2-` name.
- **D-21: THREE DEFERRED ROWS MUST BE RE-POINTED, NOT SILENTLY INHERITED.** `EXAM-01`, `EXAM-03` and `DOCS-11` were deferred to Phase 24 by Phase 23.1 naming `s2-`/`s3-` targets that will now never exist. Required re-points, each to be made in the minor phase that first creates a `cp-*` tree: **`EXAM-01`** — the seven-heading README obligation moves from *"every new Section-1/2/3 example"* to every new `cp-*` example; **`EXAM-03`** — the `make example-s*` target surface becomes `example-cp-*`; **`DOCS-11`** — the spine-separation gate's `SECTION_ONE_GLOB` (`s1-*`) is widened to include `cp-*`, or a second glob is added beside it. **Re-pointing makes explicit on the record that `s2-` and `s3-` will never exist. Silently carrying them would leave three rows owing work against directory names nothing will ever create.**

### Documentation

- **D-22: BOTH a deep example README and a published page.** Dave chose this explicitly. README carries the MECHANICS; the published page carries the ARGUMENT and includes from the tree (the shape Phase 22 shipped). Dave: *"It's important as we develop this example of constructing and assembling a context product that we have sufficient documentation on what is being done and why."*

### Sequencing

- **D-23: `CP-SPEC-001` (Counterparty Reference Snapshot) moves to 24.2.** It is single-STORE but spans **five systems of record** — LEI reference data, internal client master, internal credit, CRM, and the entitlement service. That multi-source complexity is 24.2's POINT, not 24.1's obstacle.
- **D-24: Multi-store assembly is DESIRABLE later, not avoided.** Dave: *"it's ok to go against multiple data stores to assemble the context product. This resembles the real situation context product engineers will have to deal with. This means we need to point to Fluree, Postgres, SQLite, and whatever else data store is required."* 24.1 defers it only because it is the FIRST example.

### Claude's Discretion

The operator decomposition of 24.1's recipe (likely Resolve → threshold filter
→ contract assembly), the fixture/anchor company selection, and the exact
published-page structure. All must be reported, none needs a ruling.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The DE-binding specification set (read D-01 first — these bind DEs, not the SDK)
- `references/Context_Product_Specification_Standard_v0-3.md` — how a Context Product is specified: nine-element contract (§2.1), seven-section skeleton, closed eight-operator vocabulary (§10.2), composition invariants (§10.3), six universal validation gates (§4.7), response envelope (§8), tiers and certification (§13), definition of done (§15).
- `references/CP-SPEC-001_Counterparty_Reference_Snapshot_v2.md` — a worked spec authored to that Standard. **24.2's subject.** Its §3.1 element table and §4.2 operator step table are the two sections downstream work consumes.
- `references/CCF_SDK_DE_REQUIREMENTS.md` — the seven-station DE journey (author, validate, bind, build, register, certify, operate) and its §9 decision candidates, renumbered `D-IMPL-202`…`211` by Phase 23.1.

### SDK mechanism this phase demonstrates
- `src/ccf/operators/base.py` — `Operator` Protocol; `OperatorCategory` is a CLOSED `Literal["policy","similarity","temporal","traversal"]`.
- `src/ccf/operators/registry.py` — `OperatorRegistry.register()`, append-only. Implementations are OPEN; categories are not.
- `src/ccf/agents/assembler.py` — `ContextAssemblerProtocol`, `DeterministicAssembler`. The Mode 1 path.
- `src/ccf/products/contract.py` — `ContextProductContract`, `AssemblyMode`.
- `src/ccf/products/composition.py` — `compose_lineage`, `compose_expiry`, `refuse_mixing`. The products-off-products machinery, for a later minor phase.
- `src/ccf/products/gates.py` — the SDK's THREE universal gates (`run_gates`).

### Governing rulings
- `docs/DECISIONS.md` — `D-GATE-23.1` (this phase's predecessor and what it left owed), `D-IMPL-102` limb 3 (no fourth gate joins `run_gates`), `D-IMPL-30` (nine contract elements, `AssemblyMode` ships), `D-GATE-19` (criteria locked before Wave 1), `D-15` (hand-edit only), `D-IMPL-114`/`123` (citation form, ceiling zero).
- `.planning/ROADMAP.md` § `### Phase 24:` — the banked requirements and the two flagged surface questions.

### Data
- `/home/parkave/ccf_dataprep/README.md` and `docs/ccf_dataprep_v2.md` — five partitioned stores, row-level provenance, the FIBO IRI binding contract, and the ENGINEERED conditions.
- `/home/parkave/ccf_dataprep/docs/known-issues.md` — **read before trusting any field.**
- Obsidian vault, topic `context-products` — 25 articles on a five-tier ladder, catalog and build order at response `Q019`. Vault access GRANTED by Dave 2026-08-25.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`DeterministicAssembler` is NOT the Mode 1 path — CORRECTED 2026-08-25 by `24.1-RESEARCH.md`.** An earlier reading here said *"24.1 should use it rather than hand-rolling"*; **nothing calls it.** Its only references outside its own unit test are a DOCSTRING citation in `ccf.products.resolver` and an EXPORT in `ccf.agents.__init__` — a grep for the name finds those and reads them as uses. It runs no projection and emits no `ContextProductContract`. **The real Mode 1 path is `ProjectionEngine.execute` -> `ContextProductContract` -> `run_gates` -> `build_replay_record` -> `serve`, which is what `examples/s1-00-companies-over-revenue` actually runs.**
- `examples/hw1-harness-clients` — ADK, Anthropic Agent SDK and LangGraph clients already reach a Context Product over MCP (Phase 20, `D-GATE-20`). **The three-harness consumption leg is REUSE, not new build.** Only the A2A leg is new, and it is not in 24.1.
- `examples/hw1-companies-over-revenue` — the structural template for 24.1: a thin `consume.py` importing only stdlib, `ccf.client` and the adapter.
- `runtime/ccf_runtime/peering/lf_a2a.py` — the A2A surface, for a later minor phase.

### Established Patterns
- **`OperatorCategory` is closed at four; implementations are open.** A DE can register any operator, but each must declare one of `policy`/`similarity`/`temporal`/`traversal`.
- **A networked substrate puts an example outside the always-on `examples:` aggregate** (`s1-00` needs Postgres, `s1-01` needs Fluree; neither is in the aggregate). `D-08` accepts this.
- **The No-Hardcoding Rule** (`CLAUDE.md` §6.4) — the example's code is thin and generic; everything specific lives in definition artifacts. An example whose code still runs meaningfully with its artifacts deleted has violated it.

### Integration Points
- L4 operator registry ← the example's registered operators.
- L6 `ContextProductContract` ← what the example emits and prints.
- MCP egress (`runtime/ccf_runtime/mcp/egress.py`) ← how a later minor phase serves it to the three harness clients.

</code_context>

<specifics>
## Specific Ideas

**THE OPERATOR-MAPPING QUESTION — and a hypothesis that must be tested before
any of it is called a gap.** Measured 2026-08-25: the Standard's closed EIGHT
names do not map onto `OperatorCategory`, a closed `Literal` of FOUR. The Standard's closed EIGHT-operator vocabulary
does not partition cleanly into the SDK's FOUR categories:

| Standard operator | SDK category |
|---|---|
| Policy, Traversal, Similarity | map directly |
| Temporal | an SDK category with **no name in the Standard's eight** (absorbed into Traversal modes) |
| Projection | **not an L4 operator in CCF at all** — Π is L5 |
| Resolve, Enrich, Evaluate, Federate | **no obvious category** |

**`CP-SPEC-001`'s recipe is only THREE steps** — Resolve, Policy, contract
assembly — so 24.2 surfaces exactly ONE mapping question (`Resolve`), and the
Standard itself says contract assembly is *"not an operator"* (§10.2 retired
names). 24.1's recipe should be smaller still. **THE HYPOTHESIS, under `D-05`: none of the five is a capability gap.** The
Standard names them as *operators* in its authoring vocabulary; CCF may hold
every one of them at a DIFFERENT LAYER — `Resolve` as L2 entity resolution,
`Projection` as L5 (Pi is a layer in CCF, not an L4 operator), `Federate` as
the peering surface, `Evaluate` as contract assembly, `Enrich` as batched
traversal. If that holds, what is owed is a documented MAPPING from the
Standard's eight authoring names to the SDK's layers — which is exactly what a
DE needs — and **not** an SDK extension. **This hypothesis is the first thing
24.1 and 24.2 test, and it must be falsified before any operator is proposed
as SDK work.**

**The ten decision candidates, measured against the tree 2026-08-25** — so no
later wave re-derives them: `202` nine-vs-eight is a NON-ISSUE (already
resolved, `AssemblyMode` ships); `203` operator vocabulary and `204` gate count
are the SUFFICIENCY questions above; `205` capability classes, `208` per-claim
debt / `NOT_EVALUABLE`, `211` spec artifact + CLI, and the intent-registry half
of `210` are ABSENT from the tree; `206` tier/cost is **ABSENT, CORRECTED 2026-08-25** -- an earlier reading here said
`tier` was *"on the contract"*; it is NOT a field, only the phrase *"tier-1 default"*
in a docstring, and the reading came from counting grep hits instead of fields; `207` HTTP error taxonomy has a SURFACE
(`runtime/ccf_runtime/http_api/errors.py::refusal_detail`) so the question is
adopting the Standard's specific taxonomy; `209` supersession is a PRIMITIVE
without a cascade engine. **None of these is built by this phase — `D-02`.**

</specifics>

<deferred>
## Deferred Ideas

- **`CP-SPEC-001` and multi-source assembly** → 24.2 (`D-12`).
- **Assembly Mode 2 (LLM packaging), Mode 3 (agent-swarm), products-built-off-products, and the A2A leg** → later minor phases. The A2A product requires standing up a SECOND CCF instance — vault `Q019` §5 calls it *"the largest infrastructure item."*
- **`D-IMPL-205`…`211`** → not this phase. **`211` (the `CP-SPEC` artifact type and `ccf spec` CLI) is
  NOT RULED OUT — that was the superseded reading. It is OPEN**, and Dave has not ruled it. Under `D-01`
  the specification is a requirements source for the SDK, so whether the spec DOCUMENT itself becomes a
  Control Plane artifact is a live question, separate from whether the SDK implements what specs require.
- **The `channel_disagreements` blind spot** carried from `D-GATE-23.1` — a shipped comparator that cannot see a token-level channel drift. Fixing it is a build; it is owed, not scheduled.
- **The four Dave-owned reading items** `#2`–`#5` from the v0.2 packet — explicitly NOT dischargeable at `D-GATE-24`.

### CLOSED 2026-08-25 — was open, now ruled at `D-16`..`D-19`

**Example tree naming, and three rows that assume a scheme that was never
built.** `EXAM-01`, `EXAM-03` and `DOCS-11` were deferred TO Phase 24 by Phase
23.1 and they assume an `s2-`/`s3-` section naming scheme; no `s2-` or `s3-`
tree has ever been tracked. If 24.1's tree adopts a different convention, those
three rows inherit a name that will never exist and must be RE-POINTED rather
than silently carried. **RULED: `cp-NN-<slug>`, and all three rows are re-pointed rather than
inherited.** See `D-16`..`D-19`. Kept in this section rather than deleted so the
question and its answer stay together.

</deferred>
