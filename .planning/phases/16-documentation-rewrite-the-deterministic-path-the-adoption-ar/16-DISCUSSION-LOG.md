# Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-09
**Phase:** 16-documentation-rewrite-the-deterministic-path-the-adoption-argument
**Areas discussed:** Phase structure and sequencing, Backend demonstration, Existing suite disposition, Harness coverage, Requirements homing, Use-case spine, FIBO data role, Adoption argument, Snippet legibility

---

## How this discussion opened

Dave did not accept the initial gray-area framing. Instead he supplied the phase
scope directly: rewrite the examples against the new seam, demonstrate three
assembly approaches (deterministic / deterministic + LLM packaging / agent-based),
show all six backends using the DGX installations, and reorganize into distinct
sections — "Hello CCF" (deterministic, no agents), external MCP agents (no CCF
dependency), and Advanced CCF (algorithms, LLMs, agents; agentic skills within CCF).

That reframing drove the rest of the discussion, which was substantially a
verification exercise: establishing what the SDK demonstrably ships today versus
what Section 3 would require building.

---

## Phase structure and sequencing

Three framings were offered across the discussion as the evidence sharpened.

**First framing (withdrawn):** Section 3 requires fabric that does not exist —
Assembly Modes `llm_packaged` and `swarm_assembled` appear only in the type
definition at `src/ccf/products/contract.py:71`, and `src/ccf/unstructured/`
(Pattern 5, D-IMPL-08) was never built. This matched UAT gap G-02 and Dave's
2026-08-03 build-before-documenting ruling.

**Dave's challenge:** "You have examples today (01-agent-basics, 02-skilling,
05-workflow-hitl etc.) that demonstrate agents within the CCF. Am I missing
something here?"

**Correction issued.** The first framing was too absolute. Of the five things
Dave named for Section 3, three are demonstrated today (in-process embedding,
agentic skills, agents under governance) and two are not (LLM packaging,
agent-based context operators). The distinction established: every file in
`src/ccf/agents/` carries `__ccf_mode__ = "algorithmic"`, and CINV-03 bars a
tagged module from importing `ccf.llm` or any vendor model SDK — so the SDK's
agent surface is structurally forbidden from calling a model. Those examples
demonstrate **agents as governed identity**, not agents as reasoners.

**Dave's decisive question:** does adding Modes 2/3 change the fabric in ways
that would invalidate Sections 1 and 2? If yes, build the fabric first; if no,
start with "Hello CCF" and add a Section 4 later.

**Verification performed at the code level**, which resolved it:

| Evidence | Finding |
|---|---|
| `src/ccf/operators/base.py:120` | The `Operator` Protocol docstring already names swarm realization as permitted (INV-CH7-32) |
| `apply()` contract | "no I/O **against the graph**" — not "no I/O at all" |
| `PushableOperator` at `base.py:162` | Shipped precedent: Phase 15.2 added a capability as a separate Protocol without touching `Operator` |
| `src/ccf/replay/record.py:340` | `ModelVersionRecord` already carries `assembly_mode`; docstring anticipates Mode 2 |
| Whitepaper §7.10 | Same replay record format across all three modes, "without requiring a different replay infrastructure per mode" |

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm 4 sections; rule the serve seam in 16 | Lock the four-section structure; take one D-IMPL ruling in Phase 16 planning confirming Mode 2 packaging attaches above `serve()` rather than within it | ✓ |
| Confirm 4 sections; leave the seam to Phase 17 | Lock the structure, let Phase 17 decide the attachment point against real code | |
| Three sections — fold LLM/swarm into Section 3 later | Keep the original three and let Section 3 grow when Phase 17 lands | |

**User's choice:** Confirm 4 sections; rule the serve seam in 16.
**Notes:** Dave's own proposal — "if we feel confident that the examples will not
be impacted, we can add a Section 4 which introduces LLM and Agent Swarms" — and
better than the 16/17 split originally pushed, because Sections 1–3 ship against
proven mechanism immediately.

---

## Backend demonstration

| Option | Description | Selected |
|--------|-------------|----------|
| Parameterized runner, matrix-proven | One example body, backend by artifact/env; CI matrix across all six asserting equivalent Context Products | ✓ |
| All six visible in Section 1 only | Substrate swap as a Section 1 teaching point; Sections 2–4 run one default | |
| Six literal implementations per example | Six runnable variants per example; ~6x surface and drift risk | |

**User's choice:** Parameterized runner, matrix-proven.
**Notes:** Aligns with the Phase 15.4 registry seam, which exists precisely so
example code stops forking per backend. Six literal variants would re-fork what
15.4 just un-forked.

---

## Existing suite disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Absorb what maps, rebuild the rest | Carry forward 04-cross-process, external/00-hello-context, 02-skilling, 08-e2e-demo; rebuild the rest | |
| Greenfield the examples, rewrite the docs | Retire `examples/00`–`08`, build fresh against the new seam | ✓ |
| Decide after the section outlines exist | Let the mapping decide during planning | |

**User's choice:** Greenfield the examples, rewrite the docs.
**Notes:** Coupling flagged and accepted — those examples are the snippet source
of record for the entire `public/` tree, so all ~50 published pages move in the
same phase. Also noted: greenfield makes the six-backend matrix *cheaper*, since
every current example hardcodes `backend: sqlite` in its artifacts.

---

## Harness coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Claude + ADK in examples; LangGraph adapter still ships | Narrate the two harnesses that matter for adoption; LangGraph stays tested but untaught | |
| All three stay in examples | Keep the three-harness portability proof intact | ✓ |
| Revisit D-IMPL-24 entirely | Open whether LangGraph earns v0 placement — a Phase D mini-cycle | |

**User's choice:** All three stay in examples.
**Notes:** Dave named Claude SDK and Google ADK in his original scope; presented
with D-IMPL-24 and the existing three-way byte-identical assertion in example 03,
he kept all three. Harness neutrality is mission success condition 3.

---

## Requirements homing

| Option | Description | Selected |
|--------|-------------|----------|
| Re-home into the new suite | Map DEMO-01..03 and EXAM-01..05 onto whichever new examples cover them | ✓ |
| Retire old requirements, mint DOCS-07..NN fresh | Treat v0.2 example requirements as satisfied-and-superseded | |
| Decide during planning against the outlines | Let requirement mapping fall out of the section outlines | |

**User's choice:** Re-home into the new suite.
**Notes:** Raised because greenfield retires `examples/08-e2e-demo`, which *is*
the DEMO-01..03 deliverable.

---

## Use-case spine

Dave's instruction: "Use the use case that the backend fibo based data stores can
support today or be provided additional data to support."

Investigation of `mongo-entities.json` and `mongo-relationships.json` found 14
entities and 11 relationships carrying `kycStatus`, `riskRating`, `onboardingDate`,
`lei`, `jurisdiction`, `ownershipPercent`, and `role: "Ultimate Beneficial Owner"`
— unambiguously a KYC / beneficial-ownership graph.

| Option | Description | Selected |
|--------|-------------|----------|
| KYC / UBO resolution and refresh | Anchor on what the data natively is; extends cleanly to Section 4 | ✓ |
| Counterparty risk screening | riskRating/jurisdiction/entityStatus driving a counterparty approval | |
| Counterparty credit exposure (needs new data) | The whitepaper's §7.4/§7.6 worked example; requires loading facilities, limits, covenants | |

**User's choice:** KYC / UBO resolution and refresh.
**Notes:** "Let's do option 1 but we can always add a Credit Memo example in a
later phase." Four properties made it a strong CCF teaching case: multi-hop
ownership traversal (what retrieval does badly), four jurisdictions (real `P`-axis
divergence), two planted near-duplicate company names (real Similarity difficulty),
and Sarah Chen at exactly 25.0% (the FinCEN CDD threshold).

---

## FIBO data role

This area required two corrections and was the most substantive exchange of the
discussion.

**First framing (wrong).** Asked whether the FIBO data should be an external
source ingested at L1, seed data loaded through L2, or both. Dave selected
"external source." The framing implied CCF would bulk-load an enterprise estate.

**Over-correction (also wrong).** Reframed the FIBO data as "a modeling
reference, not a database CCF ingests" — which wrongly excluded reading from
enterprise sources, CCF's actual purpose.

**Dave's correction:** "There are two different concepts going on here. The first
is an enterprise will have data marts, knowledge graphs, databases, lakes, etc.
that are all fair game for a Context Product to be formed. The CCF does not load
that data estate into its KG — as that would be a disaster. The CCF has an
internal KG that it uses to represent the items that help it create the Context
product and it also is able to persist that KG in a backend. So there is a read
and a write capability which can be two different backend stores."

**Verified and confirmed:**
- Read side = L1 ingress adapters (CDC at `runtime/ccf_runtime/cdc/adapter.py`,
  MCP client at `src/ccf/mcp/client.py`, file/stream), plus
  `src/ccf/mcp/acquisition.py` for L4/L5 decision-time acquisition. **None are
  registry backends.**
- Write side = CCF's Context Graph (L3), the six registry backends. `boot()`
  takes `backend: str`, required, no default, **exactly one** — the boot token is
  minted once per graph and single-writer keys on graph identity.
- Read store and write store are independent; may be different databases on the
  same server.
- The rejected posture is *wholesale replication*; the accepted one is *selective
  assembly*.

**User's confirmation:** "Yes it is."

---

## Temporal signal (investigated, not asked)

A question was drafted asking how to get temporal signal into the FIBO data, on
the belief that a static snapshot could not exercise the `T` axis, `λ_c`, or
Context Debt. Investigation before asking found the concern unfounded:
`examples/01-agent-basics` already ships `half-life-table.yaml` (per-observation-type
`λ_c` with `decay_driver` and `supersession_event` rows) and `debt-evaluation.yaml`,
whose dated observations produce an assessed `D_c` landing in a CAR routing state.
Signal arrives via `events.yaml` as an authored L1 artifact. **The question was
withdrawn before being put to Dave** and recorded as D-05.

---

## Adoption argument

| Option | Description | Selected |
|--------|-------------|----------|
| Its own page, named alternatives | Name RAG-over-vector-store, hand-rolled assembly, semantic layer + prompts; state what breaks | ✓ |
| Woven into Section 1's opening | Argument arrives where the reader first meets a Context Product | |
| Both — a page, plus the argument in Section 1 | Covers both the evaluating architect and the learning reader | |

**User's choice:** Its own page, named alternatives.
**Notes:** Closes the second half of G-01, which found **zero** hits across the
entire published surface for comparative rationale. The worked demonstration is
the UBO question — "who ultimately owns Acme?" — whose answer lives in an
ownership chain no passage contains. Accepted cost: the docs now owe a defence of
these comparisons as alternatives evolve.

---

## Snippet legibility

| Option | Description | Selected |
|--------|-------------|----------|
| Structural separation in the example sources | Physically separate CCF call spine from deployment code; boundary visible in the repo | ✓ |
| Both — structural, plus a naming convention | Separate regions *and* name markers by side, auto-labelled in rendered pages | |
| Marker naming convention plus a rendered legend | Docs-layer legend only; repo reader still cannot see the boundary | |

**User's choice:** Structural separation in the example sources.
**Notes:** Traces directly to Dave's originating complaint of 2026-08-03 — "I
can't tell from looking at the code which code is example code and which code is
required by the CCF." The test is whether a repo reader, not a site reader, can
see the line.

---

## Claude's Discretion

- Section-to-example mapping — how many examples per section and their boundaries.
- Whether the six-backend matrix is one CI job or several.
- How DEMO-01..03's fraud-ring scenario re-homes given the KYC/UBO spine.
- Nav structure within the four sections, inside Phase 14's Diátaxis frame.

---

## Deferred Ideas

- **Credit-memo example** — Dave, 2026-08-09: "we can always add a Credit Memo
  example in a later phase." The whitepaper's canonical Mode 2 exemplar; wants
  facilities, limits, covenants in the FIBO stores plus Pattern 5.
- **Tier-3 raw external sources** — reading an enterprise estate at operator time
  without landing in L3. Deferred in 15.2, explicitly designed-for. Fabric work;
  belongs on the roadmap as its own entry.
- **Pattern 5 / `src/ccf/unstructured/`** — D-IMPL-08 resolved 2026-07-25, never
  built.
- **Section 4** — Modes 2 and 3, Phase 17. Open design question carried: how a
  swarm-realized operator enters the composition-preservation suite when it is
  deterministic at the typed boundary but not value-deterministic.
- **A lint for mis-pointed snippet includes** — SURFACE-AUDIT A-5.
- **`make ci` does not reach `tools/`** — process finding from the 15.1 close.
- **DI-15.4-05 / F2** — public-vs-private adapter surface; awaiting Dave's ruling.

---

## Process note

Five of the nine areas were re-framed at least once after Dave pushed back on the
options presented. Two framings were materially wrong and were corrected against
the code: the claim that Section 3 was undemonstrable (too absolute), and the
claim that FIBO data was a modelling reference rather than an ingestible source
(an over-correction). Both corrections changed decisions, and both were driven by
Dave's challenges rather than by self-audit.
