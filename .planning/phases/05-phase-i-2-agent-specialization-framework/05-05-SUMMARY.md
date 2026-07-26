---
phase: 05-phase-i-2-agent-specialization-framework
plan: 05
subsystem: skills
tags: [skills, catalog, d-impl-12, d-impl-29, d-05, d-08, control-plane, tdd]
requires: [05-04]
provides:
  - 4-type skill catalog entry schema (local_callable | tool | mcp | a2a) as a versioned Control Plane artifact class (D-IMPL-12)
  - typed SkillRequirements declaration — frozensets of opaque identifiers (D-IMPL-29 tier-1 substrate)
  - SkillCatalog registration through the D-05 register_versioned path + discovery by type + pinned resolution
  - banking skill fixtures (tool-type covenant-metrics with local_callable/a2a variants; mcp-type document-fetch)
  - schema export coverage for SkillCatalogEntry via the 05-04 ARTIFACT_CONTRACTS registry
affects: [05-06, 05-07]
tech-stack:
  added: []
  patterns:
    - binding-agrees-with-discriminator model validator over a _BINDING_CONTRACTS mapping (TaskStep ref-agrees-with-kind analog)
    - catalog keeps a key index only; all artifact content lives in and resolves through the ControlPlaneRegistry (no second store)
    - skill_catalog_key derives {tenant}/{class_id}/{name} from the entry, mirroring the factory's ref-resolution key convention
key-files:
  created:
    - src/ccf/skills/__init__.py
    - src/ccf/skills/catalog.py
    - tests/skills/__init__.py
    - tests/skills/test_catalog.py
    - tests/fixtures/banking/skills/covenant_metrics_tool.yaml
    - tests/fixtures/banking/skills/document_fetch_mcp.yaml
  modified:
    - tests/agents/test_schema_export.py
decisions:
  - "Binding blocks are pure descriptors (callable_ref / command / server+resource / endpoint) — no transport or resolution code exists for any of the four types in this wave; dispatch is 05-06 scope (D-08)"
  - "SkillCatalog stores only the keys it registered, never entries — the registry stays the single source of artifact content, so discovery and resolution read the same audited versions every other Control Plane consumer reads"
  - "Pinned resolve accepts declared artifact_version or content hash — the same dual acceptance the Agent Factory applies to ccf-artifact:// refs"
  - "The local_callable and a2a variants live as additional entry documents inside the tool fixture (same capability, different binding types) — keeps all four types' values in YAML with no new fixture-only literals in test code"
  - "SkillCatalogEntry re-declares the two-lane version fields locally through validate_semver rather than importing definitions' private _TwoLaneVersioned — the semver grammar stays single-sourced, and no file outside the plan's scope changes"
metrics:
  duration: ~6 min
  completed: 2026-07-26
  tasks: 1
  tests: 532 passed, 3 skipped
---

# Phase 5 Plan 05: Skill Catalog Summary

The four-type D-IMPL-12 skill catalog ships as a versioned Control Plane artifact class — local_callable/tool/mcp/a2a entries with per-type descriptor bindings and typed opaque-identifier requirements declarations, registering through the D-05 hash-verified path and discoverable/pinned-resolvable over the existing ControlPlaneRegistry — the substrate 05-06's grant machinery binds against.

## Tasks

| Task | Name | Commits (RED/GREEN) |
| ---- | ---- | ------------------- |
| 1 | Skill catalog — 4-type entry schema, requirements declaration, registration/discovery | ed43827 / 50f3491 |

## What was built

- **`src/ccf/skills/catalog.py`** (`__ccf_mode__ = "algorithmic"`) — `SkillType` Literal over the four D-IMPL-12 types; four descriptor binding contracts (`LocalCallableBinding`, `ToolBinding`, `McpBinding`, `A2ABinding` — fields only, no transports, D-08); `SkillRequirements` with `required_scopes`/`required_context_products` as required frozensets of opaque identifiers (Pitfall 4 — no vocabulary in /src, empty set is an explicit author statement per D-IMPL-38); `SkillCatalogEntry` with two-field D-IMPL-28 versioning via `validate_semver` and a binding-agrees-with-type model validator; `SKILL_CATALOG_ENTRY = ArtifactClass("ccf.skill-catalog-entry", ...)`; `skill_catalog_key`; `SkillCatalog` with `register` (D-05 `register_versioned`, refusals returned unchanged), `discover(skill_type=...)` (latest versions, browsing surface, never a replay path), and `resolve(tenant, name, version)` (pinned, dual acceptance, `SkillNotInCatalog` on miss).
- **`tests/skills/test_catalog.py`** — all four types validate from fixture documents and the set equals `SKILL_TYPES`; fifth type refused; binding/type disagreement refused; extra fields refused; non-semver refused; requirements are frozensets; registration lands under the derived key with a `register_versioned` audit event; a structural unbumped mutant (extra scope identifier from the fixture's `mutation` block) returns `RefuseUnbumpedChange` with nothing stored; discovery lists all and filters by each type; pinned resolution by artifact_version and by content hash; unknown name/version raise `SkillNotInCatalog`.
- **Fixtures** — `covenant_metrics_tool.yaml` (tool entry + local_callable/a2a variants + mutation value) and `document_fetch_mcp.yaml` (mcp entry, empty `required_context_products` as an explicit statement). All identifiers and binding values in YAML, none in /src or test code (§6.4).
- **`tests/agents/test_schema_export.py`** — `SkillCatalogEntry` appended to `ARTIFACT_CONTRACTS`; closed-world-at-every-level and export assertions now cover the skills contracts (the union's four binding `$defs` included).

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `.venv/bin/pytest tests/skills/test_catalog.py tests/agents/test_schema_export.py -q` → 29 passed
- `.venv/bin/pytest tests/ -q` → 532 passed, 3 skipped
- `.venv/bin/mypy --strict src` → clean (61 files)
- `.venv/bin/python -m tools.lints` → exit 0 (no new allowlist entries)
- `grep -cin "scope:\|read:\|write:" src/ccf/skills/catalog.py` → 0
- All four skill_type values validate; a fifth is refused; both banking fixtures register and are discoverable via the Control Plane path

## Known Stubs

- Binding blocks are descriptors only — no dispatch, no governance check, no grant state; all deliberate 05-06 scope (D-08, D-IMPL-29 tier 1/2). `bound_skills`/`grant_set_hash` stubs carried from 05-02..04 remain until 05-06 binds grants against this catalog.
- `SkillCatalog.discover` sees only entries registered through the same catalog instance (key index); enumeration of pre-existing registry keys is not offered because the registry exposes no key listing — grants (05-06) reference entries by pinned version, which `resolve` serves regardless of which instance registered them.

## Threat Flags

None — both surfaces were in the plan's threat model and mitigated as specified: catalog entry drift goes through the D-05 hash-verified versioned path with content-hash identity (T-05-14); `callable_ref` is a stored descriptor from fixture/user artifacts under the tenant trust boundary, never resolved or accepted from decision-time input in this wave (T-05-18, dispatch enforcement 05-06).

## Self-Check: PASSED

All created files exist (src/ccf/skills/catalog.py, tests/skills/test_catalog.py, both skill fixtures); commits ed43827 and 50f3491 present on `phase-i2`.

## TDD Gate Compliance

RED commit ed43827 (`test(05-05)`, verified failing on collection — `ccf.skills` absent) precedes GREEN commit 8ff-style `feat(05-05)` 50f3491 (all tests passing). No refactor commit needed.
