---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 03
subsystem: skills
tags: [d-impl-56, skill-catalog, tool-surface, harness-adapters, d-17]
requires:
  - ccf.skills.catalog (I.2 four-type entry schema)
  - runtime/ccf_runtime/adapters/{claude_agent,langgraph,adk} (I.3 adapters)
  - ccf.agents.definitions.InstructionBinding (I.2 axis 6)
provides:
  - SkillCatalogEntry.description (required, D-16 — no default, no sentinel)
  - SkillCatalogEntry.argument_schema (typed SkillArgumentSchema, MCP-inputSchema-renderable)
  - fifth `procedure` SkillType + ProcedureBinding (seam-1-only instruction ref)
  - ccf.skills.toolsurface.render_tool_surface — one shared derivation, three adapter consumers
  - D-17 three-way tool-surface equality test over real harness tool objects
affects:
  - 07-workflow slice (agent-nodes bind skills against the widened entry schema)
tech-stack:
  added: []
  patterns:
    - bottom-of-module import + model_rebuild for the skills->agents contract cycle
    - FunctionTool subclass overriding _get_declaration to carry a declared (not inferred) schema into ADK
key-files:
  created:
    - src/ccf/skills/toolsurface.py
    - tests/skills/test_tool_surface.py
  modified:
    - src/ccf/skills/catalog.py
    - runtime/ccf_runtime/adapters/claude_agent/adapter.py
    - runtime/ccf_runtime/adapters/claude_agent/__init__.py
    - runtime/ccf_runtime/adapters/langgraph/adapter.py
    - runtime/ccf_runtime/adapters/adk/adapter.py
    - tests/skills/test_catalog.py
    - tests/fixtures/banking/skills/covenant_metrics_tool.yaml
    - tests/fixtures/banking/skills/document_fetch_mcp.yaml
    - tests/fixtures/banking/skills/remote_products_peering.yaml
    - tests/fixtures/banking/skills/grants.yaml
decisions:
  - "Entry schema lane bumped for D-IMPL-56 (1.0.0->2.0.0; peering entries 2.0.0->3.0.0); artifact_version pins left untouched — no registry lifetime ever sees pre-D-IMPL-56 content beside post-, so no D-05 unbumped-change condition can arise, and re-pinning ~13 grant references would have been churn without a verifiable property"
  - "render_tool_surface refuses procedure entries (ProcedureHasNoToolSurface) — seam-1-only is enforced at the derivation, not left to adapter discipline (T-07-05)"
  - "SkillArgumentSchema defines a custom __hash__ (mapping field) so catalog entries remain set-comparable in discovery tests"
  - "InstructionBinding imported at the bottom of catalog.py + model_rebuild — the skills<->agents import cycle closes safely in both import orders"
metrics:
  duration: "16m (21:03:35Z -> 21:19:09Z, 2026-07-30)"
  completed: 2026-07-30
  tasks: 3
  tests: "998 passed / 2 skipped (baseline 987/2) under CCF_REQUIRE_HARNESSES=1"
---

# Phase 7 Plan 03: D-IMPL-56 — Declared Tool Surface + Shared Derivation Summary

**One-liner:** SkillCatalogEntry now declares its tool surface (required description + typed JSON-Schema-shaped argument_schema) plus a fifth seam-1-only `procedure` type; one shared derivation in `ccf.skills.toolsurface` renders it into all three harness adapters, pinned by a D-17 three-way equality test over real harness tool objects.

## What was built

### Task 1 — Catalog schema (TDD: `1fc589d` RED, `797b627` GREEN)
- `SkillCatalogEntry.description: str` and `.argument_schema: SkillArgumentSchema`, both required with no default and no sentinel (D-16). No `NO_DESCRIPTION`-style symbol exists.
- `SkillArgumentSchema` exactly as pre-specified: `properties: Mapping[str, SkillArgumentProperty]` (each property a JSON-type Literal + required description), `required: tuple[str, ...]` validated as a subset of property names, `extra=forbid` throughout, and a pure `to_input_schema()` that always emits `"additionalProperties": false`. Nested specs beyond one level are out of v0 scope; no fixture needed nesting (no gap to record).
- `procedure` added to the `SkillType` Literal, `SKILL_TYPES`, and `_BINDING_CONTRACTS`, with `ProcedureBinding` carrying a pinned `InstructionBinding` reference — the binding deliberately has no field that could carry inline text. `_binding_agrees_with_skill_type` refuses mismatches (verified by test).
- `mypy --strict` clean.

### Task 2 — Shared derivation + adapter retrofit + D-17 (`996c3aa`)
- `src/ccf/skills/toolsurface.py`: `render_tool_surface(entry) -> RenderedToolSurface` composing only artifact-carried values (name, artifact_version, skill_type, description, argument_schema). Procedure entries are refused (`ProcedureHasNoToolSurface`).
- All three `_tool_description` helpers deleted (`grep -rn "_tool_description" runtime/` → zero hits); Claude's `SKILL_ARGUMENT_SCHEMA` shared constant removed; all three adapters import `ccf.skills.toolsurface`.
- ADK: `_DeclaredSkillTool(FunctionTool)` overrides `_get_declaration` to carry the rendered schema (types **and** per-property descriptions) instead of signature inference — without this, ADK's surface would structurally diverge from the other two.
- LangGraph/ADK tool functions now take declared arguments as named kwargs, forwarded to `Agent.invoke_skill` as its `Mapping[str, str]`.
- `tests/skills/test_tool_surface.py`: three-way equality read back off real harness tool objects (Claude `SdkMcpTool.input_schema`, LangGraph `StructuredTool.args_schema`, ADK `FunctionDeclaration.parameters`), anchored to the shared derivation and asserted pairwise — any adapter re-deriving goes red. Absent-SDK legs skip via `conftest.harness_unavailable`, naming SDK + extra; under `CCF_REQUIRE_HARNESSES=1` a missing leg fails.

### Task 3 — Fixture retrofit sweep (verified here; edits landed in `797b627` — see Deviations)
Full enumerated fixture inventory of `SkillCatalogEntry` documents/construction sites:

| Location | Entry documents |
|---|---|
| `tests/fixtures/banking/skills/covenant_metrics_tool.yaml` | 5 — `entry`, `variants.local_callable`, `variants.peering`, `variants.procedure` (new), `callables.hostile_entry` |
| `tests/fixtures/banking/skills/document_fetch_mcp.yaml` | 2 — `entry`, `agent_invocable.entry` |
| `tests/fixtures/banking/skills/remote_products_peering.yaml` | 4 — `entry`, `denied.entry`, `agent_invocable.entry`, `retired_token.entry` |
| `tests/fixtures/banking/skills/grants.yaml` | 5 — `skills.{writeback,offcontract,crosstenant,metrics_upgrade}`, `late_skills.latecomer` |

**16 entry documents, 4 fixture files.** All Python-side constructions (`tests/skills/`, `tests/conformance/`, `tests/integration/`, `tests/agents/`) validate these fixture documents — no inline entry literals exist. One deliberate `model_construct` bypass remains in `tests/skills/test_dispatch.py` (`test_an_unrecognized_skill_type_still_raises_not_yet_bound`), which is intentionally unvalidated future-type material, not a fixture. Every description is real banking prose; `grep -rn "description=\"\"\|description: ''" tests` → 0.

## Verification
- Full suite under `CCF_REQUIRE_HARNESSES=1`: **998 passed, 2 skipped** (baseline pre-plan: 987/2; +11 = 9 new catalog tests + 3 new tool-surface tests − 1 renamed four→five-types test net). The 2 skips are the tracked CINV-04 Phase I.4 deferrals, unchanged.
- `tools.lints --all` exit 0 (CINV-01: no skill prose in /src or /runtime — descriptions live in fixture artifacts only).
- `mypy --strict src runtime`: clean, 100 files.
- Acceptance greps all pass (procedure recipe present in catalog.py; zero `_tool_description` remnants; all three adapters import the shared derivation).

## Deviations from Plan

**1. [Rule 3 - Blocking] Task 3's fixture sweep executed inside Task 1's GREEN commit**
- **Found during:** Task 1
- **Issue:** Making `description`/`argument_schema` required breaks every fixture-loading test immediately; Task 1's verify (`pytest tests/skills`) cannot pass without the fixture retrofit.
- **Fix:** All 16 entry documents retrofitted in `797b627`; Task 3 then verified the sweep was complete via full suite + greps + lints (no further edits needed, so Task 3 produced no separate commit).
- **Files modified:** the four skills fixture YAMLs
- **Commit:** `797b627`

**2. [Deviation - versioning discipline] schema-lane-only bump**
- Entry `schema_version` majors bumped (1.0.0→2.0.0; peering 2.0.0→3.0.0) for the breaking D-IMPL-56 schema change; `artifact_version` values and all grant `skill_version` pins left untouched. Rationale recorded in frontmatter decisions: no registry lifetime ever registers pre- and post-D-IMPL-56 content under one version, so no D-05 condition arises; re-pinning ~13 grant references would add churn without a verifiable property. `retired_token.entry` keeps `schema_version: 1.0.0` as a frozen historical document.

**3. [Rule 2 - Missing critical functionality] procedure refused a tool surface at the derivation**
- The plan specified the procedure type and seam-1-only travel but not where seam-2 exclusion is enforced. `render_tool_surface` raises `ProcedureHasNoToolSurface` — the T-07-05 mitigation enforced by mechanism, not adapter discipline.

## Threat model dispositions
- **T-07-04 (spoofing / surface divergence):** mitigated — single shared derivation + D-17 pairwise equality test over real harness tool objects.
- **T-07-05 (elevation / instruction smuggling into seam 2):** mitigated — `ProcedureBinding` carries only a pinned `InstructionBinding` ref; `_binding_agrees_with_skill_type` refuses mismatches; `render_tool_surface` refuses procedure entries outright.

## Known Stubs
None. `procedure` seam-1 *consumption* (injecting the referenced instruction through context injection) is deliberately not implemented here — this plan lands the contract and the seam-2 exclusion per D-15; consumption is workflow-slice scope.

## Commits
- `1fc589d` test(07-03): failing D-IMPL-56 catalog tests (RED)
- `797b627` feat(07-03): catalog schema + fixture retrofit (GREEN)
- `996c3aa` feat(07-03): shared derivation + adapter retrofit + D-17 test

## Self-Check: PASSED
All created/modified files present; commits 1fc589d, 797b627, 996c3aa verified on branch.
