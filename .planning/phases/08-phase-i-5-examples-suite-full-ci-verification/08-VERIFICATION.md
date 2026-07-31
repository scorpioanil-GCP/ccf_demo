---
phase: 08-phase-i-5-examples-suite-full-ci-verification
verified: 2026-07-31T00:00:00Z
status: human_needed
score: 50/51 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open GitHub Actions for drcastillo/ccf_code and confirm the first remote run of .github/workflows/ci.yml on the pushed main/v0.1.0 is green (lints, mypy --strict, full suite with CCF_REQUIRE_HARNESSES=1, make examples)"
    expected: "All always-on jobs green with no continue-on-error masking; the examples job runs `make examples` and exits 0"
    why_human: "gh CLI is not installed in this environment and the run is remote-only evidence; local `make ci` reproduction is verified green but the D-10 truth is 'runs on every push', which requires an observed remote run"
  - test: "Optionally dispatch .github/workflows/live-legs.yml (Ollama job) once to confirm the opt-in live leg is executable"
    expected: "workflow_dispatch job installs Ollama, pulls the model, and example-03-live-ollama exits 0"
    why_human: "Opt-in job requiring remote dispatch and model download; cannot be exercised locally within verification constraints"
---

# Phase 8 (I.5): Examples Suite, Full CI, Hardening, Phase I Gate — Verification Report

**Phase Goal:** Ship the v0 examples suite (eight examples per CLAUDE.md §9), full CI verification (D-10/D-11), hardening obligations (D-14..D-17), Phase I gate culminating in D-GATE-I, merge to main, v0.1.0 tag.
**Verified:** 2026-07-31
**Status:** human_needed (all codebase must-haves verified; remote Actions run is the one item requiring observation)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (grouped by plan; 51 truths total across 13 plans)

| Plan | Truths | Status | Evidence |
| --- | --- | --- | --- |
| 08-01 | 4/4 | ✓ VERIFIED | `Makefile` has `help` (default), `ci-core`, `ci: ci-core examples`, `example-00..07`, `example-03-live-{ollama,anthropic}`, `PYTHONPATH=src:runtime` (line 11); `tests/lints/test_examples_scope.py` pins CINV-01-in/CINV-02-out; exemption lives in `tools/lints/__main__.py:42` (linter config), not test-only |
| 08-02 | 4/4 | ✓ VERIFIED | `decide` verb absent from `runtime/ccf_runtime/cli/commands/hitl.py` (docstring records removal); absence test in `tests/cli/test_cli.py`; `runtime/ccf_runtime/http_api/errors.py` ships typed constants incl. `ERROR_SIGNED_BINDING_REQUIRED/INVALID` (lines 51, 55); D-15 removal recorded in `docs/DECISIONS.md` line 205 |
| 08-03 | 5/5 | ✓ VERIFIED | `src/ccf/hitl/transport.py:388` calls `verify_principal_binding` at admission; `tests/hitl/test_signed_binding_authority.py`, `tests/http_api/test_signed_binding_door.py`, `tests/hitl/test_was_called_derivation.py` all exist and substantive; MCP door maps same constants (`runtime/ccf_runtime/mcp/hitl_server.py:356`); `hitl.signed_binding_required` asserted from Control Plane artifact (e.g. `examples/06-decision-replay/run.py:594`) |
| 08-04 | 3/3 | ✓ VERIFIED | `runtime/ccf_runtime/orchestration/adk/driver.py` imports `BaseAgent`/`Runner` from `google.adk` — no `SequentialAgent`; D-IMPL-62 verb-status note at `docs/DECISIONS.md:179`; `docs/security-notes.md` covers signing-key sourcing |
| 08-05 | 4/4 | ✓ VERIFIED | `examples/00-quickstart/run.py` (435 lines, loads all domain values from `artifacts/` — ontology/events/controlplane/halflife YAML); README documents `make example-00`; **behavioral spot-check: `make example-00` exit 0**, serves `meridian-bank.payment-context-summary`, replay record hash printed |
| 08-06 | 4/4 | ✓ VERIFIED | `examples/01-agent-basics/run.py` uses `ccf-artifact://` factory refs (line 413); `examples/02-skilling/run.py` drives grant/exercise/revoke with governance-refusal and audit assertions; both keyless with artifacts dirs |
| 08-07 | 4/4 | ✓ VERIFIED | `examples/04-cross-process/run.py:314-334` spawns `producer_child.py` with `READY {mcp_port} {a2a_port}` handshake; A2A admission verified before L3, tampered-product negative case documented in driver; property-intelligence artifacts fresh |
| 08-08 | 5/5 | ✓ VERIFIED | `examples/05-workflow-hitl/run.py` binds `create_app(auth=BearerTokenAuth(...))`; `examples/06-decision-replay/run.py:774-803` records an auth-bound approval (`BearerTokenAuth` + `sign_principal_binding`/`HumanPrincipalBinding`), asserts `signed_binding_required is True` (line 594), exact `@X.Y.Z` versioned refs in artifacts (e.g. `workflow.yaml:25`) |
| 08-09 | 3/3 | ✓ VERIFIED | `examples/07-artifact-store-mcp/run.py` constructs `FileArtifactStore` vs `McpArtifactStore` from `store_file.yaml`/`store_mcp.yaml` config artifacts (single factory keyed on `store.type`); `mcp_store_child.py` on READY handshake |
| 08-10 | 4/4 | ✓ VERIFIED | `examples/03-harness-portability/legs/deterministic.py` imports all three adapters (`ccf_runtime.adapters.adk`, `claude_agent`, langgraph leg); `tests/conformance/test_a3_discharge.py` drives a real SDK-produced `ResultMessage` through seam 4 (its docstring explicitly contrasts with the hand-built prior) |
| 08-11 | 3/3 | ✓ VERIFIED | `legs/ollama_client.py` (httpx wrapper) and `legs/live.py` (provider selection ollama/anthropic at each harness model seam) exist; Makefile live targets excluded from `examples` |
| 08-12 | 3/4 | ✓ 3 VERIFIED, ? 1 UNCERTAIN | `.github/workflows/ci.yml` has always-on examples job running `make examples` (line 157), explicitly never continue-on-error (lines 120-123); `live-legs.yml` has workflow_dispatch Ollama job + secret-gated Anthropic job; `make ci` = ci-core + examples reproduces pipeline; local sweep green per D-GATE-I (1339 passed / 0 skipped, mypy clean, 8/8 examples exit 0). UNCERTAIN: "runs on every push" — remote Actions run not yet observed (gh unavailable here) → human item |
| 08-13 | 4/4 | ✓ VERIFIED | Top-level `README.md` exists with install/quickstart pointers; `docs/PHASE_I5_GATE.md` exists; `D-GATE-I` logged at `docs/DECISIONS.md:225` (Dave, 2026-07-31) with correct ordering (approval → gate entry → merge --no-ff → tag); `pyproject.toml` version = "0.1.0"; tag `v0.1.0` exists and is contained in `main` |

**Score:** 50/51 truths verified; 1 uncertain (remote CI run observation).

### Required Artifacts

All artifacts declared across the 13 plans exist and are substantive (spot-checked at levels 1-3): all eight `examples/NN-*/` directories with `run.py` + `README.md` + `artifacts/`, `examples/04`'s `producer_child.py`, `examples/07`'s `mcp_store_child.py`, `examples/03`'s `legs/{deterministic,live,ollama_client}.py`, the five new test files (08-01/02/03/10), `runtime/ccf_runtime/http_api/errors.py`, `.github/workflows/{ci,live-legs}.yml`, `docs/PHASE_I5_GATE.md`, `docs/security-notes.md`, top-level `README.md`. No stubs found.

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| Makefile | .venv python | `PYTHONPATH=src:runtime` | ✓ WIRED |
| routes/hitl.py + mcp/hitl_server.py | errors.py | `ERROR_SIGNED_BINDING_*` constants | ✓ WIRED |
| transport.py | identity_binding.py | `verify_principal_binding` at admission (line 388) | ✓ WIRED |
| adk/driver.py | google.adk | non-deprecated API (no SequentialAgent) | ✓ WIRED |
| ex00 run.py | artifacts/ | YAML loading, all domain values | ✓ WIRED |
| ex01 run.py | AgentFactory | `ccf-artifact://` refs | ✓ WIRED |
| ex04 run.py | producer_child.py | READY handshake (Popen) | ✓ WIRED |
| ex05/ex06 run.py | BearerTokenAuth / SignedPrincipalBinding | `create_app(auth=...)`, `sign_principal_binding` | ✓ WIRED |
| ex06 run.py/artifacts | ArtifactStore | exact `@X.Y.Z` versioned refs | ✓ WIRED |
| ex07 run.py | ArtifactStoreProtocol | store factory from config artifact | ✓ WIRED |
| deterministic.py | three adapters | HarnessAdapterProtocol impls | ✓ WIRED |
| test_a3_discharge.py | claude adapter seam 4 | real SDK ResultMessage | ✓ WIRED |
| ci.yml examples job | Makefile | `make examples` identical string | ✓ WIRED |
| D-GATE-I entry | v0.1.0 tag | tag on main post-approval | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Smallest fabric end-to-end | `make example-00` | exit 0, product served, replay hash emitted | ✓ PASS |
| CLI decide verb absent | grep of cli/commands/hitl.py | verb removed, only removal note remains | ✓ PASS |
| v0 declaration | git tag / pyproject / DECISIONS | v0.1.0 on main, version 0.1.0, D-GATE-I logged | ✓ PASS |
| Full suite / all 8 examples | `make ci` (local, per D-GATE-I record) | 1339 passed / 0 skipped, examples 8/8 exit 0 | ✓ PASS (recorded; ex00 independently re-run here) |

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| --- | --- | --- | --- |
| EXAM-01 | 08-05 | ✓ SATISFIED | example 00 exists, runs, artifact-driven |
| EXAM-02 | 08-06 | ✓ SATISFIED | example 01 factory-constructed agent |
| EXAM-03 | 08-06 | ✓ SATISFIED | example 02 grant/exercise/revoke + governance refusal |
| EXAM-04 | 08-04, 08-10, 08-11 | ✓ SATISFIED | example 03 deterministic 3-harness + live legs; A3 discharged |
| EXAM-05 | 08-07 | ✓ SATISFIED | example 04 subprocess MCP + A2A with admission |
| EXAM-06 | 08-02, 08-03, 08-08 | ✓ SATISFIED | example 05 auth-bound HITL workflow; D-14/D-15/D-16 hardening |
| EXAM-07 | 08-08 | ✓ SATISFIED | example 06 exact-version replay with auth-bound approval |
| EXAM-08 | 08-09 | ✓ SATISFIED | example 07 store swap via config |
| EXAM-09 | 08-01, 08-12, 08-13 | ✓ SATISFIED (local); remote Actions observation pending → human item | Makefile/CI wiring, D-GATE-I, v0.1.0 |

No orphaned requirements: REQUIREMENTS.md maps exactly EXAM-01..09 to Phase 8, all claimed by plans, all marked Complete.

### Anti-Patterns Found

None. No TBD/FIXME/XXX in `src/`, `runtime/`, or `examples/` Python files. No stub returns or placeholder drivers observed in sampled files.

### Human Verification Required

1. **First remote CI run** — Open GitHub Actions and confirm the always-on `ci.yml` run on the pushed main/v0.1.0 is green end-to-end. Expected: examples job runs `make examples` and passes. Why human: remote-only evidence; gh CLI unavailable to the verifier; local reproduction is verified green.
2. **(Optional) Live-legs dispatch** — Dispatch `live-legs.yml` Ollama job once. Expected: exit 0. Why human: opt-in remote job with model download.

### Gaps Summary

No codebase gaps. All 13 plans' must-haves are realized in the tree: eight runnable examples with fresh per-domain artifacts and no hardcoding, the D-14..D-17 hardening wave (fail-closed grant typing, typed refusal constants, D-16 signed-binding enforcement at both doors, decide-verb removal, ADK migration, key-management note, top-level README), D-10/D-11 CI wiring, D-GATE-I logged, phase-i5 merged to main, v0.1.0 tagged. The single outstanding item is observational, not implementational: the first remote GitHub Actions run has not been witnessed from this environment.

---

_Verified: 2026-07-31_
_Verifier: Claude (gsd-verifier)_
