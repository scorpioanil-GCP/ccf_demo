---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 16
subsystem: gate
tags: [gate, a2a, skills, invariants, ci, validation]
status: checkpoint-reached
requires: ["06-05", "06-06", "06-15", "06-17"]
provides:
  - "docs/PHASE_I3_GATE.md — the Phase I.3 gate package"
  - "AssemblyWorker.ingest_admitted — L2's typed federated entry point"
  - "McpSkillRegistry/A2ASkillRegistry threaded AgentFactory -> Agent.invoke_skill"
  - "CI leg that fails rather than skips on an absent harness"
  - "06-VALIDATION.md signed off, 48/48 automated rows executed"
affects:
  - ".planning/ROADMAP.md (Phase 6 criteria evidence — HANDED TO ORCHESTRATOR, not written here)"
tech-stack:
  added: []
  patterns:
    - "Type-level invariant enforcement (AdmittedProduct as a parameter type)"
    - "Inversion pairs: same fixture, one dependency withheld"
    - "Instrument-sensitivity guards (assert the digest can see the thing it rules out)"
key-files:
  created:
    - docs/PHASE_I3_GATE.md
  modified:
    - src/ccf/assembly/worker.py
    - src/ccf/a2a/admission.py
    - src/ccf/agents/agent.py
    - src/ccf/agents/factory.py
    - tests/crossproc/test_a2a_exchange.py
    - tests/integration/test_agent_slice.py
    - tests/invariants/test_mcp_role_separation.py
    - tests/fixtures/banking/a2a.yaml
    - tests/fixtures/banking/skills/document_fetch_mcp.yaml
    - .github/workflows/ci.yml
    - pyproject.toml
    - docs/DECISIONS.md
    - .planning/REQUIREMENTS.md
    - .planning/phases/06-phase-i-3-cross-process-harness-adapters/06-VALIDATION.md
decisions:
  - "D-IMPL-56 logged OPEN: where a skill's tool description and argument schema are declared"
  - "A2ASkillRegistry threaded alongside McpSkillRegistry — same gap, same shape"
  - "Four vendor mypy overrides removed as measured inert; all ship py.typed"
metrics:
  duration: ~3h
  completed: 2026-07-27
  tasks_completed: 3
  tasks_total: 4
---

# Phase 06 Plan 16: Phase I.3 Gate Package Summary

Assembled the Phase I.3 gate package and closed the two structural gaps Dave ruled on
before it — `AdmittedProduct` now binds L2's federated door as a **type**, and an
`mcp`-transport skill is invocable through an `Agent` — then stopped at the blocking
human checkpoint with `D-GATE-I.3` deliberately unwritten.

## What Was Built

**Dave's ruling 1 — `AdmittedProduct` bound on L2 (`b8faa6c`).**
`AssemblyWorker.ingest_admitted(admitted: AdmittedProduct, *, spec, ingested_at)` is L2's
second declared entry point. `AdmittedProduct` is constructible only inside
`A2AAdmissionGate.admit`, so offering an unadmitted `InboundProduct` does not typecheck.
CLAUDE.md §7.2's admission commitment is now carried by the type system rather than by
caller discipline, which is what §10's "architectural, not advisory" asks. `ingest(SignalEnvelope)`
is untouched and keeps serving CDC and MCP ingress — the substantive ground on which 06-10
declined to constrain the shared door. The federation vocabulary (which payload member holds
the peer's records, how the peer's key names map onto the consumer's) lives in a declared
`FederatedIngestSpec`; `/src` holds no default key name and no default correspondence.

**Dave's ruling 2 — registries threaded factory → agent (`9ff4486`).**
`AgentFactory(control_plane=..., mcp_skills=..., a2a_skills=...)` carries both registries onto
every constructed agent, on the established optional/fail-closed `callable_registry` shape.
The A2A registry was threaded alongside the MCP one because it had the identical gap and
shape; closing one alone would have re-opened the same deferred item under another name.

**Deferred item 2 — the WAL-blind digest (`5bdf943`).** Fixed, and the fix is *measured*: a
committed L2 write leaves the SQLite main file byte-identical and changes only `<db>-wal`, so
the ArtifactStore single-writer assertion could not have observed the exact write it exists to
rule out. A companion test asserts the instrument's sensitivity, so narrowing the digest back
fails rather than silently passing.

**Gate infrastructure.** A CI leg that fails rather than skips on an absent harness
(`f0783c0`); the gate document itself (`6ff1c18`); the validation sign-off (`67bda9d`).

## Key Implementation Details

Three techniques did the load-bearing work, all replacing text-matching with something a
docstring cannot satisfy:

- **Type-level constraints.** Row 6 of the gate asserts *both* the declared annotation and
  that `AdmittedProduct` is unforgeable — either alone is cosmetic, since dropping the token
  would leave the annotation reading correctly and meaning nothing.
- **Inversion pairs.** The `mcp`-through-agent tests share one grant, one entry and one agent,
  differing only in whether the registry is wired. Without the negative case the positive one
  would pass equally well against an implementation that had stopped fail-closing.
- **AST identifier scans.** Used to replace a validation-map grep that fired on the docstring
  documenting compliance.

## Deviations from Plan

### Auto-fixed / in-scope corrections

**1. [Rule 2 — gate integrity] Four vendor mypy overrides removed as inert (`74c3b52`).**
Research assumption A3 said `mcp`, `a2a-sdk` and `google-adk` ship `py.typed` so their
overrides are inert. Measured: **`google-adk`, `langgraph`, `langchain-core` and
`claude-agent-sdk` all ship `py.typed`**, `mypy` passes over `src` + `runtime` with none of
the four blocks present (verified by deleting and re-running), and `mcp`/`a2a-sdk` never had
a block at all. The removed comments said "ships no py.typed marker" for every one of them.
This is the *mirror* of the D-21 defect — understated enforcement — and a gate citing those
seams as loose would have described a config rather than the build.

**2. [Rule 2 — D-21] `AgentFactory` docstring rewritten (`74c3b52`).** It led with "there is
no path to an `Agent` that bypasses this class". D-12 withdrew the construction token in
favour of a lint, so what holds is a property of the linted trees. Now stated as its
enforcement, contrasted with `AdmittedProduct`, whose token earns the stronger claim.

**3. [Rule 4-adjacent → surfaced, not settled] `D-IMPL-56` logged OPEN.** `SkillCatalogEntry`
declares neither a tool description nor an argument schema; all three adapters surfaced it
independently. Logged for Dave rather than resolved unilaterally — it belongs in the catalog
artifact schema, a Control Plane decision.

**4. [Row defects] Five of fifty validation-map rows were unrunnable or false as written**,
corrected in place with reasons (see `06-VALIDATION.md`). Notably one asserted
`len(model_fields) == 5` against a 7-field record — it would have passed **only on an
implementation that had dropped the envelope fields** — and one named a non-existent test
directory, so `pytest` exited 4 having run nothing. One row was corrupted at planning time by
~30 lines of the plan's own XML pasted into its command cell.

### Deliberate non-execution

**`.planning/ROADMAP.md` was NOT modified.** Plan Task 3 instructs updating it; the
orchestrator's spawn instructions state twice that ROADMAP.md and STATE.md are
orchestrator-owned and must not be touched. The orchestrator's instruction wins. The content
it needs is in the handover section below.

### Plan criteria that were false against the tree

- `grep -c 'D-GATE-I.3' .planning/ROADMAP.md .planning/STATE.md docs/DECISIONS.md` **is not 0**:
  ROADMAP contains one *pre-existing narrative* mention ("Ends with … `D-GATE-I.3` before
  Phase 7 begins"). The substantive requirement — no gate entry *logged* — holds:
  `docs/DECISIONS.md` is 0.
- `grep -c 'pytest\|tools.lints\|mypy' docs/PHASE_I3_GATE.md >= rows` is a weak proxy (it
  counts lines, and several rows cite a `file::function` without the word "pytest"). It is
  satisfied (20 ≥ 20), but the property that actually holds is that **every one of the 20
  rows names a test path or lint rule id and a failure mode**.
- The traceability table's established vocabulary is "Complete" (used for AGNT-01/02/03); the
  plan asked for "Delivered". Followed the plan. Separately noted: that table has
  **pre-existing drift** — RSCH/FEAS/FABR rows still read "Pending" despite those phases being
  gated and merged. Out of scope, not fixed, recorded here.

## Verification Results

Re-measured independently; the orchestrator's baseline was 936 passed / 2 skipped at
`7ec1de9`, and the +4 are this plan's new tests.

| Leg | Result |
|-----|--------|
| `python -m pytest -q` | **940 passed, 2 skipped** |
| `CCF_REQUIRE_HARNESSES=1 python -m pytest -q -rs` | **940 passed, 2 skipped**, no harness leg skipped |
| `CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance -q` | **188 passed**, three harness legs executed |
| `python -m tools.lints --all` | exit 0 |
| `python -m mypy` | Success, **99 source files** (`src` + `runtime`) |
| `python -m pip check` | No broken requirements |
| Validation map | **48/48 automated rows executed, all green**; 2 human checkpoints marked |

Environment: `/home/parkave/ccf_code/.venv/bin/python`, `PYTHONPATH=<worktree>/src:<worktree>/runtime`.
Both skips are the documented Phase I.4 CINV-04 deferrals. No discrepancy with the
orchestrator's figures.

## Handover to the Orchestrator — ROADMAP.md Phase 6 edits

1. `**Plans:** 16/17 plans executed` → `17/17 plans executed`.
2. `- [ ] 06-16-PLAN.md` → `- [x] 06-16-PLAN.md`.
3. Attach evidence to the five success criteria, all pointing at `docs/PHASE_I3_GATE.md`:
   criterion 1 → §3.1/§3.4 **with the Experience edge recorded as a named Phase 7 deferral**;
   criterion 2 → §3.2; criterion 3 → §3.3; criterion 4 → §3.4's three separate boundary
   observables; criterion 5 → §3.4's factory-parametrized `file`/`mcp` conformance suite.
4. Do **not** log `D-GATE-I.3` and do **not** mark the phase gated — both are Dave's.

## Self-Check: PASSED

All created/modified files verified present; all seven commits verified in `git log`.

## Checkpoint

Task 4 is `checkpoint:human-verify` with `gate="blocking"`. Execution stopped there as
required. `D-GATE-I.3` is unwritten in `docs/DECISIONS.md` (grep count 0).
