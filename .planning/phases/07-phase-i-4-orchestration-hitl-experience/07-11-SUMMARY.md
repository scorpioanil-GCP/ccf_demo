---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 11
subsystem: experience-layer
tags: [cli, expr-02, d-impl-22, d-impl-56, skill-import, thin-client]
requires: [07-10]
provides:
  - "ccf CLI: argparse noun-verb dispatcher over the full D-IMPL-22 ruled inventory"
  - "--local mode constructing the SAME ApiDependencies bundle create_app consumes"
  - "ccf skill import <dir>: one-way D-18 SKILL.md importer"
  - "HTTP routes: /skill/revocations, /skill/catalog (POST), /config/registrations"
affects: [runtime/ccf_runtime/cli/, runtime/ccf_runtime/http_api/routes/]
tech-stack:
  added: []
  patterns:
    - "RequestSpec translation: verbs are pure argv->request translations; the CLI interprets nothing"
    - "one httpx client per invocation inside one asyncio.run (B3)"
key-files:
  created:
    - runtime/ccf_runtime/cli/__init__.py
    - runtime/ccf_runtime/cli/main.py
    - runtime/ccf_runtime/cli/local.py
    - runtime/ccf_runtime/cli/commands/{__init__,agent,skill,skill_import,workflow,hitl,replay,artifact,product,config}.py
    - tests/cli/{__init__,conftest,test_cli,test_skill_import}.py
    - tests/fixtures/skillmd/covenant-walkthrough/{SKILL.md,references/checklist.md}
  modified:
    - pyproject.toml ([project.scripts] ccf entry point)
    - runtime/ccf_runtime/http_api/routes/skill.py (revocations + catalog register)
    - runtime/ccf_runtime/http_api/routes/config.py (registrations)
decisions:
  - "CLI verbs mirror the HTTP routes exactly; where the §8.3 ruling names a verb the HTTP surface lacked, the ROUTE was added (thin-client posture preserved) rather than a CLI-only path"
  - "reference artifacts on re-import tolerate exactly RefuseEmptyBump (typed discriminant, not prose matching) — unchanged content re-registered is the by-design idempotent case"
  - "exit codes: 0 success / 1 typed 4xx refusal (body on stdout) / 2 wiring error (stderr)"
metrics:
  duration: "~50 min"
  completed: 2026-07-30
  tests: "1232 passed / 0 skipped; mypy --strict clean (141 files); tools.lints --all exit 0"
---

# Phase 7 Plan 11: `ccf` CLI + D-18 SKILL.md Importer Summary

One-liner: stdlib-argparse `ccf` noun-verb CLI as a thin httpx client over the 07-10 HTTP API, with `--local` constructing the identical `ApiDependencies` bundle (type-asserted) and a one-way SKILL.md importer that never maps `allowed-tools` onto requirements.

## What was built

**Task 1 — dispatcher, entry point, command set** (commits `1999f5f` RED, `4a66bf6` GREEN)

- `runtime/ccf_runtime/cli/main.py`: argparse subparser-per-noun over the ruled set (`agent`, `skill`, `workflow`, `hitl`, `replay`, `artifact`, `product`, `config`); `[project.scripts] ccf = "ccf_runtime.cli.main:main"`.
- Verbs: agent declare/list/show/versions; skill list/grant/revoke/import; workflow invoke/resume/status; hitl list/decide; replay query/resolve; artifact inspect/put; product get; config keys/versions/resolve.
- `agent declare` takes `--key` + `--file` only — no inline definition flag exists to parse (asserted by test; T-07-29).
- Base URL is `--base-url` or `CCF_BASE_URL`; no scheme-prefixed URL literal exists in the package (CINV-01; asserted by test scanning the source).
- `--local --local-root DIR` (`cli/local.py`): assembles `ApiDependencies` from reference impls only (in-process `ControlPlaneRegistry`, `FileArtifactStore`, `InMemoryHitlTransport`, `SkillCatalog`/`GrantLedger` with `ApprovalSinkAdapter()`, `WorkflowEngine` with honestly-unwired node bindings that raise into the exception path). Test asserts `type(bundle) is ApiDependencies` — the Codex shared-abstraction finding discharged by type.
- HTTP-vs-injected equivalence proven against a real uvicorn server on loopback: byte-identical stdout for the same read command.
- Exit codes: typed 4xx refusal → 1 with body on stdout; transport error/5xx → 2 on stderr.

**Task 2 — `ccf skill import`** (commits `5be18ad` RED, `bbe1c5d` GREEN)

- Frontmatter `name`/`description` → `procedure` `SkillCatalogEntry` (schema lane 2.0.0); body → `ccf.prompt-artifact` with `declared_parameters` derived from the body via the sandboxed Jinja parse (fixture proves `entity_name` is derived, not invented); `references/` → further pinned prompt artifacts; body bound by `InstructionBinding` ref (`ccf-artifact://{tenant}/ccf.prompt-artifact/{name}@{version}`).
- `allowed-tools` present in the fixture and asserted **absent** from `SkillRequirements` (D-IMPL-29); requirements come only from explicit `--required-scope`/`--required-context-product` flags.
- One-way: byte-level directory snapshot equal before/after import; re-import with a bumped version registers a new version; an unbumped changed re-import is the registry's typed refusal (exit 1).
- Explicit empty `argument_schema` (`properties: {}, required: []`) — a declaration, not a placeholder, matching the D-IMPL-56 ruling that a procedure declares no callable arguments.

## Deviations from Plan

### Auto-fixed / auto-added (Rule 2)

**1. [Rule 2] `/skill/revocations` route added**
- **Found during:** Task 1. §8.3 rules "skill grant/revoke" for the CLI, but 07-10 shipped no revoke route; a CLI-only ledger path would be exactly T-07-27.
- **Fix:** POST route delegating to the audited `GrantLedger.revoke`; `GrantTransitionError` → 409. CLI stays thin.
- **Commit:** `4a66bf6`.

**2. [Rule 2] `/config/registrations` and POST `/skill/catalog` routes added**
- **Found during:** Task 2. The importer must register prompt artifacts and catalog entries "through the same registration surface any client uses (over HTTP or --local)", but no wire registration surface existed.
- **Fix:** `/config/registrations` interprets the four SDK-typed classes (agent/task/prompt/workflow definitions) through `parse_artifact` + `register_versioned` (unknown class → 422; refusal → 409 wrapped with `refusal_type`); `/skill/catalog` POST registers via `SkillCatalog.register` (key derived server-side, so grant refs and registry keys cannot disagree). This widens the config noun from reads-only to Control Plane configuration, which is what D-IMPL-22 names for the noun.
- **Commit:** `bbe1c5d`.

**3. [Rule 1] Re-import empty-bump on unchanged references**
- **Issue:** re-import with a bumped version refused on unchanged `references/` files (`RefuseEmptyBump`), failing the ruled one-way re-import behavior.
- **Fix:** `RequestSpec.tolerate_empty_bump` — reference registrations (only) treat a 409 whose typed `refusal_type` is exactly `RefuseEmptyBump` as the by-design idempotent case; every other refusal still exits 1.
- **Commit:** `bbe1c5d`.

### Deferred

- **Editable reinstall for `.venv/bin/ccf`:** the venv at `/home/parkave/ccf_code/.venv` is shared with the main checkout and sibling wave agents; `pip install -e .` from this worktree would repoint the distribution at a directory the orchestrator force-removes. The entry point is verified as `python -m ccf_runtime.cli.main --help` (exit 0); a post-merge `pip install -e .` materializes `.venv/bin/ccf` with no further change.
- **CLI `skill revoke` naming:** GrantLedger revocation refusals are exceptions (`GrantTransitionError`), so they surface as 409 `detail` strings rather than typed refusal contracts — inherited from the I.2 ledger surface, not changed here.

## Threat register outcomes

- **T-07-27 (privileged CLI path):** mitigated — every verb translates to the same routes; `--local` bundle type-asserted as `ApiDependencies`; equivalence test proves identical output over a real HTTP server.
- **T-07-28 (SKILL.md smuggling permissions):** mitigated — allowed-tools non-mapping asserted; bodies become seam-1 prompt artifacts by reference.
- **T-07-29 (inline definition injection):** mitigated — `agent declare` parser refuses any inline definition flag (asserted).

## Verification

- `tests/cli` 39 tests green; full suite **1232 passed, 0 failed, 0 skipped**.
- `mypy --strict`: clean over 141 source files.
- `tools.lints --all`: exit 0.
- `grep`-equivalent test: no `http(s)://` literal in `runtime/ccf_runtime/cli/`.

## Self-Check: PASSED

- runtime/ccf_runtime/cli/main.py — FOUND
- runtime/ccf_runtime/cli/local.py — FOUND
- runtime/ccf_runtime/cli/commands/skill_import.py — FOUND
- tests/cli/test_cli.py — FOUND
- tests/cli/test_skill_import.py — FOUND
- Commits 1999f5f, 4a66bf6, 5be18ad, bbe1c5d — FOUND in log
