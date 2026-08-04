---
status: diagnosed
phase: 14-documentation-suite
source: [14-VERIFICATION.md]
started: 2026-08-03T19:32:00Z
updated: 2026-08-03T20:20:00Z
---

## Current Test

Test 2 (browser Mermaid rendering) still pending. Test 1 returned an issue — see Gaps.

## Tests

### 1. Read the adopter's guide end to end as a first-time adopter

Read `public/tutorial/adopters-guide.md` from top to bottom as someone who has never seen
CCF. Follow it literally, starting from `pip install -e ".[dev]"` and continuing through the
replay section.

expected: Each section's prose explains WHY before the included snippet shows HOW; no step
assumes knowledge introduced only in a later section; the reader can reach a governed,
replayable deployment without consulting `docs/` or the source tree.
result: issue — Dave, 2026-08-03. The guide is factually correct and its ordering is right
(Context Product before agent), but it teaches the wrong mental model. Read as an adopter who
already has external agents — the majority banking case — it reads as though assembling a
Context Product *requires* building agents inside CCF. It does not: `examples/00-quickstart`
assembles and serves a product with zero agent references. Nothing in the guide states that
the agent sections are optional, and the guide never argues why CCF beats calling an MCP
server and assembling context yourself.

### 2. Confirm the Mermaid diagrams render in a browser

Run `make docs-serve` and page through Concepts → Pillars.

expected: All five pillar diagrams plus the two seam and four sequence diagrams render as
visual Mermaid graphs rather than raw code blocks or empty figures; labels are legible and
edges resolve.
result: [pending]

## Summary

total: 2
passed: 0
issues: 1
pending: 1
skipped: 0
blocked: 0

## Gaps

### G-01 — the docs teach an agent-first mental model for an agent-optional capability

status: failed
severity: blocking for the phase goal ("adopt using the docs alone")
reported_by: Dave, 2026-08-03

Evidence gathered against the codebase:

- `examples/00-quickstart/run.py` contains **zero** agent references. Its section markers are
  the deterministic pipeline: `ontology → ingest → assemble → operators → project → gate →
  record → serve`. `ContextAssemblyAgent` is one of six optional archetypes, not a
  prerequisite.
- `public/concepts/pillars/data-context.md` opens with *"how does an agent get at
  first-party records…"* — framing the one pillar that needs no agent around agents. It is
  the first Concepts page a reader meets.
- The adopter's guide reads as a required progression (install → product → agent → skill →
  workflow → replay) with no off-ramp. Its single acknowledgement that the SDK ships no
  agents sits at line 133, *inside* the "Declare an agent" section.
- Agent mentions per how-to page: `bind-a-harness-adapter` 14, `grant-and-revoke-a-skill` 15,
  `compose-a-workflow-with-hitl` 4, `run-agents-cross-process` 3. Four of six how-tos are
  agent-shaped, and there is **no** how-to for assembling a Context Product deterministically.
- A grep of the entire published surface for comparative rationale ("why not just",
  "instead of building", "rather than building", "compared to") returns **zero hits**. The
  adoption argument is absent.

Resolution: Phase 14.1 (Part 1 — the deterministic story and the adoption argument).

### G-02 — two of three Assembly Modes are undemonstrated (whitepaper-fidelity gap)

status: failed
severity: fidelity gap; scoped to v0.3, not to Phase 14.1
reported_by: Dave, 2026-08-03

Assembly Mode is the whitepaper's eighth primitive (§7.6), carried as the ninth element of
the Context Product contract (§6.3) and implemented as
`AssemblyMode = Literal["algorithmic", "llm_packaged", "swarm_assembled"]` in
`src/ccf/products/contract.py:70`, with replay capture wired in `src/ccf/replay/record.py`.

`swarm_assembled` and `llm_packaged` each appear in **exactly one place in the repository —
the type definition itself**. No example, artifact, or test declares either. Every example
artifact declares `assembly_mode: algorithmic`. Assembly Mode appears on one published page
(`concepts/replay-anatomy.md`), incidentally; the eighth primitive has no page of its own.

Building blocks that exist: the `ContextAssemblyAgent` archetype, the agent factory and
composition module, the full peering surface (`admission.py`, `identity.py`, `protocol.py`,
`trust_policy.py`), and passage-level claim anchors in `contracts/claims.py`.

Missing: the Pattern 5 unstructured ingestion pipeline. D-IMPL-08 was RESOLVED 2026-07-25
(stage Protocols plus one opinionated reference pipeline) but never built — there is no
`src/ccf/unstructured/`.

Consequence for documentation: Part 2 of the two-part assembly document (agent-swarm
assembly) cannot be written against demonstrated mechanism today. Dave's ruling (2026-08-03)
is to build before documenting — Pattern 5, then the credit-memo exemplar demonstrating both
Mode 2 and Mode 3, then the documentation.

Resolution: v0.3 milestone, not Phase 14.1.
