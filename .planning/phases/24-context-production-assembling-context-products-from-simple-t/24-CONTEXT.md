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
- **D-15: CI posture — the target sits OUTSIDE the always-on `examples:` aggregate.** (The word *"live-leg"* stood here and is SUPERSEDED by the CI ruling below: `s1-00`'s pattern is a marked test against a CI-provisioned service container the test seeds, not a live leg against the LAN host.) Follows the `s1-00` precedent exactly: a networked substrate cannot sit in the always-on job. **This is a deliberate cost, accepted so the example points at a real store rather than a shipped copy.**
- **D-16: The spec is authored to the FULL Standard** — front matter plus sections A–G — so the phase validates the AUTHORING path and not merely the assembly path. A reduced spec would prove nothing about the Standard.
- **D-17: The example prints its SPECIFICATION and the RESULTING JSON.** This is Dave's stated requirement for every example in the ladder.

### Example tree naming — RULED 2026-08-25

- **D-18: Context Production example trees are named `cp-NN-<slug>`.** `examples/cp-00-institutional-holders` is 24.1; `examples/cp-01-counterparty-reference` is 24.2. Make targets parallel the existing shape: `example-cp-00`, `example-cp-01`. Zero-based, matching `s1-00` and the archived trees.
- **D-19: `NN` is BUILD ORDER — not tier, not spec id.** The spec id lives in the README front matter. Spec-id naming would run backwards from day one, because `CP-SPEC-001` is 24.2 while the new product is 24.1.
- **D-20: The `sN-` scheme is NOT revived, and the reason is on the record.** `s1-`/`s2-`/`s3-` encode documentation Sections 1/2/3 from **Phase 16's documentation rewrite, RETIRED at `D-IMPL-152`**. Sections 2 and 3 were never built. Adopting a taxonomy from a retired approach is the Phase 16 failure mode Dave named when he deferred `DOCS-14`/`EXAM-02` — *"docs against a surface that does not survive."* The scheme had already drifted before it died: `hw1-harness-clients` is functionally Section-2 content that never took an `s2-` name.
- **D-21: THREE DEFERRED ROWS MUST BE RE-POINTED, NOT SILENTLY INHERITED.** `EXAM-01`, `EXAM-03` and `DOCS-11` were deferred to Phase 24 by Phase 23.1 naming `s2-`/`s3-` targets that will now never exist. Required re-points, each to be made in the minor phase that first creates a `cp-*` tree: **`EXAM-01`** — the seven-heading README obligation moves from *"every new Section-1/2/3 example"* to every new `cp-*` example; **`EXAM-03`** — the `make example-s*` target surface becomes `example-cp-*`; **`DOCS-11`** — the spine-separation gate's `SECTION_ONE_GLOB` (`s1-*`) is widened to include `cp-*`, or a second glob is added beside it. **Re-pointing makes explicit on the record that `s2-` and `s3-` will never exist. Silently carrying them would leave three rows owing work against directory names nothing will ever create.**

### TTL and the two globs — RULED 2026-08-25

- **D-22: TTL IS A DECLARED ANCHOR, NOT A ROW TIMESTAMP, and 13F's quarterly `report_period` is a legitimate one.** Measured: `ccf.products.contract::TTLAnchor` is `Literal["from_decision", "from_entity_freshness"]` — the SDK takes what the spec DECLARES. Dave: *"When the DE does the specification for the context product they will know how to deal with TTL — it is not always a timestamp."* **The distinction, and it is the load-bearing part:** *"there should be a timestamp and there isn't"* is a DATA DEFECT; *"the dataset reports per period and the spec anchors on that period"* is a NORMAL FRESHNESS DECLARATION. `24.1-RESEARCH.md` framed the absent row timestamp as breaking the debt story — **that framing is WITHDRAWN**; there is no gap and no defect here.
- **D-23: `cp-*` inherits the SPINE-SEPARATION glob and NOT the AGENT-FREE glob.** There are TWO `s1-*` globs in different files enforcing different things. `tests/examples/test_spine_separation.py::SECTION_ONE_GLOB` enforces seven ordered marker regions, exactly one region-bearing module, that module silent — **criterion 15 names this one, and it is widened to `cp-*`**, because the published page's `--8<--` includes depend on those regions. `tests/examples/test_section_one_is_agent_free.py::SECTION_ONE_GLOB` is an AST walk refusing any import of `ccf.agents` — *"Section 1 declares no agent"* — **no criterion names it and it is NOT widened.**
- **D-24: The reason `cp-*` stays outside the agent-free glob must be WRITTEN INTO that test file.** `cp-00` implements `ContextAssemblerProtocol`, which lives in `ccf.agents.assembler`, so bringing it under that guard would fail the example on its own core design. *"Section 1 declares no agent"* is a SECTION-1 rule, not a Context-Product rule. **Without a recorded reason the next reader widens the glob for consistency and breaks the example** — which is the same shape as every stale premise this project has had to re-measure.

### CI coverage — RULED 2026-08-25

- **D-25: `cp-00` follows the `s1-00` CI pattern EXACTLY — a marked test against a CI-PROVISIONED service container that the test SEEDS ITSELF.** The example points at `ccf_dataprep`'s real Postgres locally; CI proves the CODE PATH against a `postgres:16` service container seeded with a small 13F fixture, under a `pytest.mark.postgres` marker. Dave chose this over the two alternatives.
- **D-26: WHY NOT THE OTHER TWO.** *Rejected — the `hw1` precedent* (`examples/hw1-companies-over-revenue` is in NO workflow at all): honest and cheapest, but it leaves the example with zero CI coverage and `make ci` unable to say anything about it. *Rejected — secrets and a real live leg*: most faithful, but CI cannot reach the LAN host and `live-legs.yml` carries no database secrets, so it would mean putting database credentials into Actions. **Neither rejection is a judgement about the data; both are about what CI can honestly assert.**
- **D-27: The fixture is SEEDED BY THE TEST, never committed as a database.** `s1-00`'s test provisions and seeds; `cp-00`'s does the same. This keeps the example's real substrate real and the CI substrate reproducible, and it is why criterion 3's target can stay out of the always-on aggregate while the code path is still covered.

### Documentation

- **D-28: BOTH a deep example README and a published page.** Dave chose this explicitly. README carries the MECHANICS; the published page carries the ARGUMENT and includes from the tree (the shape Phase 22 shipped). Dave: *"It's important as we develop this example of constructing and assembling a context product that we have sufficient documentation on what is being done and why."*

### Sequencing

- **D-29: `CP-SPEC-001` (Counterparty Reference Snapshot) moves to 24.2.** It is single-STORE but spans **five systems of record** — LEI reference data, internal client master, internal credit, CRM, and the entitlement service. That multi-source complexity is 24.2's POINT, not 24.1's obstacle.
- **D-30: Multi-store assembly is DESIRABLE later, not avoided.** Dave: *"it's ok to go against multiple data stores to assemble the context product. This resembles the real situation context product engineers will have to deal with. This means we need to point to Fluree, Postgres, SQLite, and whatever else data store is required."* 24.1 defers it only because it is the FIRST example.

### Claude's Discretion

The operator decomposition of 24.1's recipe (likely Resolve → threshold filter
→ contract assembly), the fixture/anchor company selection, and the exact
published-page structure. All must be reported, none needs a ruling.

</decisions>

### A rule about this document itself — added 2026-08-25 after three incidents

- **D-31: DECISION IDS ARE STABLE AND ARE NEVER RENUMBERED. Append only.** Sequential renumbering broke this file THREE separate times: (1) `D-09`'s inline citation to the acceptance test went stale when the ids it named shifted — **the renumber broke the reference it was renumbering**; (2) a subagent brief cited ids from before a renumber and was offset by three against the committed file; (3) a later reader found a superseded phrase QUOTED INSIDE A CORRECTION and reported it as a live claim. **From here, a new decision takes the next unused number and NOTHING is renumbered.** If a gap appears in the sequence, the gap is the record.
- **D-32: THIS FILE QUOTES ITS OWN SUPERSEDED TEXT ON PURPOSE, AND A READER MUST ANCHOR ON THE OPERATIVE SENTENCE.** Corrections here name what they replace rather than deleting it — that is why the withdrawn readings are still greppable. **Token presence is NOT token force.** A search that finds a phrase inside a correction and reports it as current has read the history, not the answer. This hazard has now caught the orchestrator twice and a planning subagent once; it is a cost the convention creates, not a defect in it.

### What the examples are ABOUT — ruled 2026-08-25, and it resolves criterion 9

- **D-33: THE EXAMPLES TEACH HOW TO ENGINEER AND CONSTRUCT A CONTEXT PRODUCT WITH THE CCF SDK. They are not about the data being accurate.** Dave: *"We have to remember that we have engineered a number of names and relationships into these examples in terms of the data stored in the databases. The idea of these examples are not to necessarily have totally accurate data because we certainly do not have that. Moreover it's about how to engineer and construct a context product using the CCFSDK."* This is the same posture `ccf_dataprep`'s own README takes: ***"Use this to learn the assembly patterns, not the numbers."***
- **D-34: CRITERION 9 NEEDS NO AMENDMENT — the parenthetical is ILLUSTRATIVE, the requirement is NORMATIVE.** The criterion requires *"the EDUCATIONAL nature... is stated where a reader meets a figure... so no number reads as a fact about a real company."* Its em-dash clause *"real LEIs, invented behaviour"* is an ILLUSTRATION, and the planner correctly measured that it does not describe THIS table — both tables `cp-00` reads are 100% `provenance = 'public'`. **The requirement is discharged by stating what is TRUE for this example, not by reciting the illustration and not by auditing provenance row by row.**
- **D-35: What the README and the published page must actually say.** That these examples teach **METHOD — how to engineer and construct a Context Product** — and not the figures; that the surrounding data estate carries **deliberately engineered names and relationships**; that **no number here is a fact about any real company**; and, where it is true and specific, what the reader is looking at (for `cp-00`: one quarterly archive spanning many periods, and issuer matching that is ~22.5% `weak` BY DESIGN). **Do not write *"invented behaviour"* about rows that are public-provenance** — being inaccurate in the cautious direction is the same class of error as being inaccurate in the confident one.

### Criteria 2 and 18 — the tension is FALSE, and the bound is ruled

- **D-36: CRITERIA 2 AND 18 DO NOT CONFLICT, AND NEITHER IS TO BE AMENDED.** Dave, 2026-08-25, explicitly: *"Do not amend either criterion to 'resolve' a false tension."* **Criterion 2 means:** every §D step in THIS spec corresponds to code THIS example actually runs, proven IN-TREE. **Criterion 18 means:** no general-purpose SDK spec-validation surface — no `CP-SPEC` type, no `ccf spec` command, nothing reusable in `src/` or `runtime/`.
- **D-37: THE BOUND, as Dave stated it — four clauses, all of which must hold.** (1) ONE artifact in the example tree — e.g. `assembly-recipe.yaml`, the §D table as data with each step naming a runtime witness; (2) ONE test module under `tests/examples/`; (3) **NOTHING in `src/` or `runtime/`**; (4) **NOT REUSABLE across products.** Dave: *"That is the pressure test: the example proves its own recipe, not the SDK growing a validation framework."* Aligns with `D-01` — the SDK is untouched and the example carries its own proof.
- **D-38: A PROOF THAT DRIFTS OUTSIDE THE FOUR CLAUSES IS THE VIOLATION, not the criteria.** If discharging criterion 2 ever appears to require something reusable, something in `src/`, or a second test module, that is the signal the proof has grown into the machinery criterion 18 forbids — stop and report it, do not widen a criterion to admit it.

### The security is RESOLVED, not pinned — ruled 2026-08-26

- **D-39: `cp-00` RESOLVES the security from `(lei, period)` to the dominant CUSIP. It does NOT pin a literal.** Dave: *"Use an L2 Resolve from (lei, period) to the dominant CUSIP. That is the operator criterion 11 is supposed to place."*
- **D-40: Three reasons, recorded so this is not re-opened.** (1) The resolve step IS the L2 `Resolve` that criterion 11's mapping hypothesis must place — **pinning would skip the pressure test the phase exists to run**. (2) A pinned CUSIP is a DOMAIN VALUE and would have to live in an artifact anyway under the No-Hardcoding Rule (`CLAUDE.md` §6.4). (3) One issuer LEI fans out to as many as 52 CUSIPs; resolving handles the fan-out, pinning hides it.
- **D-41: The extra §D step is ACCEPTED.** Dave: *"Accept the extra §D step. Mapping gets answered now instead of deferred."* The §D operator step table therefore carries a Resolve step, and criterion 2 requires it be proven to correspond to code that actually runs.

### Two Wave 2 items, ruled 2026-08-26 — record only

- **D-42: The citation lint's module-alone invocation is a SHIPPED-TOOL HOLE. Record it; do NOT fix it in 24.1.** Wave 2 measured `python -m tools.lints.citations` exiting **0** on a seeded broken citation AND on a fabricated symbol; `python -m tools.lints --all` exits 1 and names both. Dave: *"`--all` is the real gate; the module-alone exit 0 on a seeded break is a shipped-tool hole. Record only; do not fix in 24.1."* Fixing it would be a build (`D-04`). **Every wave uses `--all`, never the module alone.**
- **D-43: The example EXPIRES 2027-03-31, and that is correct behaviour. The Control Plane `MAX_TTL` requirement must be DOCUMENTED so a too-short default does not read as an example bug.** The declared TTL is 365 days, `from_entity_freshness` on the reported quarter, so `expires_at` is 2027-03-31; after that validation gate 3 refuses to serve — **the gate working, not a defect**. Dave: *"Document the Control Plane `MAX_TTL` >= 31,536,000s requirement so a default that is too short doesn't look like an example bug."* This obligation belongs in the spec's §E/§G and in the example README, not only in a summary.

### D-39/D-40 clarified — the resolve is TWO steps at TWO layers (2026-08-26)

- **D-44: MARKED CLARIFICATION ON `D-39`/`D-40`. OLD WORDING: *"an L2 Resolve from `(lei, period)` to the dominant CUSIP."* MEASURED TWO-STEP:** step 1, **group-and-rank to the dominant CUSIP, at L1**, in the deployment's own source reader — **not SDK mechanism**; step 2, **canonical entity resolution at L2**, `src/ccf/assembly/worker.py::SpecDrivenEntityResolution`.
- **D-45: Why the first half cannot be L2, measured not argued.** `EntityResolutionStrategy.resolve(*, envelope)` takes **one envelope** and so **structurally cannot rank a group**. Dave: *"ranking a group is not `resolve(*, envelope)` because that call is per-envelope."* Confirmed against the tree: both `resolve` definitions in `worker.py` are per-envelope.
- **D-46: `D-39`'s INTENT STANDS UNCHANGED — only the layer of the first half was mis-worded.** Nothing is pinned, no domain value sits in code, the 1-LEI-to-many-CUSIP fan-out is handled, and `Resolve` is placed. **Criterion 11's mapping still gets a real L2 `Resolve`** — which is the whole reason the resolve was chosen over a pin. Dave: *"Do not force the first half into L2."*

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
- **`ContextAssemblerProtocol` IS THE PRODUCER'S SEAM, AND NO EXAMPLE HAS EVER IMPLEMENTED IT. Corrected twice; both superseded readings named.** `~ccf.agents.assembler.ContextAssemblerProtocol` is *"the seam a Context Product's producer implements"* (`D-IMPL-97` ruling 2) — a Protocol precisely so a deployment conforms rather than inherits, and *"the SDK's reference implementation carries no privileged status."* **READING 1, WRONG:** *"24.1 should use `DeterministicAssembler` rather than hand-rolling"* — it names the reference impl, not the seam. **READING 2, ALSO WRONG:** that nothing calling `DeterministicAssembler` makes it a dead surface 24.1 should avoid. **Nothing calls it BY DESIGN** — its own docstring says it exists *"for two reasons and no third: to prove the Protocol composes against a real factory-built agent, and to give a deployment something to diff its own assembler against."* Reading an uncalled reference implementation as dead code mistakes the SDK's Protocol-plus-reference-impl pattern (`CLAUDE.md` §11) for a defect. **THE CORRECT INSTRUCTION: 24.1 IMPLEMENTS `ContextAssemblerProtocol`** — `assembler_id`, `assembler_version`, and a keyword-only `assemble(request, perspective, tenant_id) -> AssemblyOutcome` that reads no clock. `DeterministicAssembler` is what to DIFF AGAINST, never what to call. **Measured 2026-08-25: ZERO examples implement this Protocol** — control, the same search finds `examples/hw1-companies-over-revenue/server/compose.py` implementing another Protocol, so it detects implementations when they exist. **That makes it an UNEXERCISED SEAM, which is exactly what a pressure test is for.**
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
