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

### The reference documents are DE-binding, NOT an SDK surface

- **D-01: The Context Product Specification Standard and the DE Requirements are binding on DATA ENGINEERS, not on the SDK.** Dave, verbatim: *"It validates what DEs must do to develop Context Products. It's the specification document that is the binding document that DEs follow when both specifying requirements and implementing them. It is not to be part of the SDK but only to provide a means for DEs to develop against the SDK consistent with the specification."*
- **D-02: NOTHING from those documents is built into the SDK by this phase.** No `CP-SPEC` artifact type, no `ccf spec` CLI subcommand, no spec schema, no spec-validation machinery. Decision candidate `D-IMPL-211` is explicitly OUT — it proposed exactly that, and `D-01` rules it out of the SDK.
- **D-03: This converts the two flagged "SDK-surface impacts" from ADOPTION questions into SUFFICIENCY questions.** Not *"should the SDK adopt the closed eight-operator vocabulary / six gates?"* but *"can a DE authoring to the Standard express their recipe and satisfy their gates with the mechanism the SDK provides?"* **The examples answer this by DOING it. A thing that cannot be expressed is a recorded FINDING, not a guess.**

### 24.1 — the first example

- **D-04: 24.1 is a NEW, INVENTED, genuinely simple Context Product** in the shape of the existing client example (`examples/hw1-companies-over-revenue`, *"companies over a revenue threshold you choose"*). Dave: *"I want the first example to be a simple context product that does not span multiple data stores. We may have to make one up like we did in the client example."*
- **D-05: Subject — institutional holders of a company with a position above a threshold the caller chooses.** One anchor entity, one caller parameter, ONE source. Dave named this shape: *"investors who have a larger than X stake in a company."*
- **D-06: ONE store, ONE system of record — SEC Form 13F, in `ccf_dataprep`'s Postgres (`ccf_v2`).** Real public data; `ccf_dataprep/sources/13f` and `generators/fetch_13f.py` already exist.
- **D-07: In-process DETERMINISTIC operator. Assembly Mode 1.** Dave: *"For the first example I want to use an in process deterministic operator to assemble the context product."* No LLM anywhere in the assembly path.
- **D-08: CI posture — LIVE-LEG, outside the always-on `examples:` aggregate.** Follows the `s1-00` precedent exactly: a networked substrate cannot sit in the always-on job. **This is a deliberate cost, accepted so the example points at a real store rather than a shipped copy.**
- **D-09: The spec is authored to the FULL Standard** — front matter plus sections A–G — so the phase validates the AUTHORING path and not merely the assembly path. A reduced spec would prove nothing about the Standard.
- **D-10: The example prints its SPECIFICATION and the RESULTING JSON.** This is Dave's stated requirement for every example in the ladder.

### Documentation

- **D-11: BOTH a deep example README and a published page.** Dave chose this explicitly. README carries the MECHANICS; the published page carries the ARGUMENT and includes from the tree (the shape Phase 22 shipped). Dave: *"It's important as we develop this example of constructing and assembling a context product that we have sufficient documentation on what is being done and why."*

### Sequencing

- **D-12: `CP-SPEC-001` (Counterparty Reference Snapshot) moves to 24.2.** It is single-STORE but spans **five systems of record** — LEI reference data, internal client master, internal credit, CRM, and the entitlement service. That multi-source complexity is 24.2's POINT, not 24.1's obstacle.
- **D-13: Multi-store assembly is DESIRABLE later, not avoided.** Dave: *"it's ok to go against multiple data stores to assemble the context product. This resembles the real situation context product engineers will have to deal with. This means we need to point to Fluree, Postgres, SQLite, and whatever else data store is required."* 24.1 defers it only because it is the FIRST example.

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
- `DeterministicAssembler` (`src/ccf/agents/assembler.py`) — the Mode 1 assembly path; 24.1 should use it rather than hand-rolling.
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

**The operator-mapping finding, measured 2026-08-25 and to be confirmed by
building rather than argued.** The Standard's closed EIGHT-operator vocabulary
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
names). 24.1's recipe should be smaller still. **This is why the ladder is
built one step at a time: each example converts one abstract mapping question
into a measured answer.**

**The ten decision candidates, measured against the tree 2026-08-25** — so no
later wave re-derives them: `202` nine-vs-eight is a NON-ISSUE (already
resolved, `AssemblyMode` ships); `203` operator vocabulary and `204` gate count
are the SUFFICIENCY questions above; `205` capability classes, `208` per-claim
debt / `NOT_EVALUABLE`, `211` spec artifact + CLI, and the intent-registry half
of `210` are ABSENT from the tree; `206` tier/cost is HALF present (`tier` on
the contract, no cost estimator); `207` HTTP error taxonomy has a SURFACE
(`runtime/ccf_runtime/http_api/errors.py::refusal_detail`) so the question is
adopting the Standard's specific taxonomy; `209` supersession is a PRIMITIVE
without a cascade engine. **None of these is built by this phase — `D-02`.**

</specifics>

<deferred>
## Deferred Ideas

- **`CP-SPEC-001` and multi-source assembly** → 24.2 (`D-12`).
- **Assembly Mode 2 (LLM packaging), Mode 3 (agent-swarm), products-built-off-products, and the A2A leg** → later minor phases. The A2A product requires standing up a SECOND CCF instance — vault `Q019` §5 calls it *"the largest infrastructure item."*
- **Everything in `D-IMPL-205`…`211`** → not this phase, and `211` not the SDK at all under `D-01`.
- **The `channel_disagreements` blind spot** carried from `D-GATE-23.1` — a shipped comparator that cannot see a token-level channel drift. Fixing it is a build; it is owed, not scheduled.
- **The four Dave-owned reading items** `#2`–`#5` from the v0.2 packet — explicitly NOT dischargeable at `D-GATE-24`.

### OPEN — raised, NOT resolved, and it needs a ruling before 24.1 is planned

**Example tree naming, and three rows that assume a scheme that was never
built.** `EXAM-01`, `EXAM-03` and `DOCS-11` were deferred TO Phase 24 by Phase
23.1 and they assume an `s2-`/`s3-` section naming scheme; no `s2-` or `s3-`
tree has ever been tracked. If 24.1's tree adopts a different convention, those
three rows inherit a name that will never exist and must be RE-POINTED rather
than silently carried. This was selected for discussion and the sitting closed
before reaching it.

</deferred>
