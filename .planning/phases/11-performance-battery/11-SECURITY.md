---
phase: 11-performance-battery
status: secured
threats_total: 15
threats_closed: 15
threats_open: 0
audited: 2026-08-01
---

# Phase 11 — Performance Battery — Security Audit

**Date:** 2026-08-01
**Auditor:** gsd-security-auditor
**ASVS Level:** default (1)
**Config:** block_on = open
**Result:** SECURED — 15/15 threats closed (13 mitigated + verified, 2 accepted)

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-11-01 | Tampering | mitigate | CLOSED | `perf/gate.py:306` `tomllib.loads`; `ThresholdConfigError` (`gate.py:71`) raised for unknown suite, malformed value, and tighter-than-default override (loosen-only, `gate.py:125-159`) |
| T-11-02 | Elevation | mitigate | CLOSED | `perf/gate.py:62` anchored `^[A-Za-z0-9._-]+$` pattern; `sanitize_runner_class` (`gate.py:162-171`) rejects `.`/`..` explicitly; invalid key → `load_baseline` returns None → report-only (`gate.py:235-243`) |
| T-11-03 | Repudiation | mitigate | CLOSED | No write path to `perf/baselines/` in `gate.py` (BASELINES_DIR read-only, `gate.py:59`); source-asserted by `tests/perf_gate/test_gate.py:274-280` (`test_gate_source_has_no_baseline_write_path`, rejects `record_baseline` and any baselines+write line) |
| T-11-SC | Tampering | accept | CLOSED (accepted) | See Accepted Risks. Package Legitimacy Audit in `11-RESEARCH.md` (§ line 214); pytest-benchmark 5.2.3 pinned; D-01 user-locked |
| T-11-04 | Tampering | mitigate | CLOSED | `yaml.safe_load` only: `perf/synth/generator.py:68`, `perf/conftest.py:35`; no `yaml.load` anywhere in perf tree. Typed construction: `EntityResolutionSpec`/`EntityResolutionRule` (`perf/conftest.py:38-63`), `SignalEnvelope` (`generator.py:261`, `extra=forbid` per `src/ccf/signal/envelope.py:8`) |
| T-11-05 | Tampering | mitigate | CLOSED | Generator imports only `ccf.signal.envelope` (`generator.py:38`) and emits `SignalEnvelope` tuples only (`generator.py:237-261`); ingestion exclusively via `handle.worker.ingest` (`perf/conftest.py:111`). Grep gate re-executed in this audit: `ccf.graph` imports in `perf/synth/generator.py` = 0. Note: the grep gate is a verification-time check (recorded in 11-02-SUMMARY "Grep gates verified"), not an automated test — see Observations |
| T-11-06 | Info Disclosure | accept | CLOSED (accepted) | See Accepted Risks. Generator is fully synthetic and seed-derived (`PERF_SEED = 20260801`, fixed `EPOCH`, no clock reads — `generator.py:40,55`) |
| T-11-07 | DoS | mitigate | CLOSED | Explicit `benchmark.pedantic(..., rounds=ASSEMBLY_ROUNDS[rung], iterations=1)` (`perf/suites/scale/test_assembly.py:49-52`; per-rung rounds tables in `perf/suites/scale/conftest.py:51-53`); D-07 rung flex exercised (replay 100k via deterministic replication, 11-04-SUMMARY) |
| T-11-08 | Tampering | mitigate | CLOSED | Correctness sanity asserts present in every benchmark module (`micro/test_operators.py:46-48`, `micro/test_dispatch.py`, `micro/test_gates.py`, `micro/test_factory.py`, `scale/test_assembly.py`, `scale/test_projection.py`, `crossproc/test_mcp_egress.py:39-42`, `crossproc/test_peering.py`, `replay/test_replay_scale.py:95-98`); speed-up WARN (never-fail) in `gate.py:204-210` |
| T-11-09 | Spoofing/Info Disclosure | mitigate | CLOSED | All endpoints bound `127.0.0.1` only (`perf/suites/crossproc/conftest.py:174,213`); audit grep for `0.0.0.0` across `perf/` = 0 hits (matches 11-04-SUMMARY source assertion) |
| T-11-10 | DoS | mitigate | CLOSED | `start_new_session=True` (`crossproc/conftest.py:136`) + `finally` block with `os.killpg(SIGTERM)` → wait → `os.killpg(SIGKILL)` escalation (`crossproc/conftest.py:239-253`); WR-01 fix (READY handshake deadline) present in commit b3cb64b |
| T-11-11 | Tampering | mitigate | CLOSED | Hard byte-exact assert `canonical_bytes(outcome.product) == canonical_bytes(...)` precedes the timed call in every rung (`perf/suites/replay/test_replay_scale.py:93-104`); byte-identical artifact staging via `canonical_bytes`/`content_hash` (`replay/conftest.py:273-283`) |
| T-11-12 | Elevation | mitigate | CLOSED | `.github/workflows/perf.yml:17` — `workflow_dispatch:` is the sole trigger; no `push`, `pull_request`, or `schedule` (asserted in header comment lines 4-5); repo private |
| T-11-13 | Repudiation | mitigate | CLOSED | `perf/README.md:65-71` — re-baseline ritual documented as manual, Dave-approved, DECISIONS.md-logged (D-IMPL-70); gate.py cannot write baselines (see T-11-03 evidence) |
| T-11-14 | DoS | mitigate | CLOSED | `tests/perf_smoke/test_smoke.py:36` hard per-suite `SUITE_TIMEOUT_SECONDS`; `proc.communicate(timeout=...)` (`:89`) with kill-grace escalation (`:99`); `CCF_PERF_SMOKE=1` smallest-rung knob (`:63`); WR-02 fix (whole-process-group reap on timeout) present in commit 9d22648 |

## Accepted Risks

| Threat ID | Risk | Rationale | Accepted By |
|-----------|------|-----------|-------------|
| T-11-SC | Supply-chain compromise of `pytest-benchmark` | Dev/CI-only dependency, never in `/src` runtime path; version pinned (5.2.3); Package Legitimacy Audit performed in 11-RESEARCH.md; harness choice user-locked by D-01 | Dave (D-01) |
| T-11-06 | Disclosure of fixture data content | Fixture data is fully synthetic and seed-derived (fixed seed 20260801, fixed epoch, no clock reads, neutral vocabulary from `perf/synth/artifacts/*.yaml`); contains no real-world or tenant data by construction | Plan 11-02 |

## Unregistered Flags

None. All five SUMMARY.md `## Threat Flags` sections (11-01 through 11-05) declare no new attack surface; each maps its claims to existing threat IDs.

## Observations (non-blocking)

1. **T-11-05 grep gate is verification-time, not CI-automated.** The plan's "grep gate asserts zero ccf.graph imports in generator" was executed and recorded at build time (11-02-SUMMARY) and re-executed in this audit (0 hits), but no always-on test performs the source assertion the way `tests/perf_gate/test_gate.py:274` does for T-11-03. The substantive mitigation (envelopes-only emission, ingestion solely via `handle.worker.ingest`) is present in code. Consider promoting the grep to a source-assert test in a future phase.
2. **T-11-09 similarly rests on an audit-time grep** (0 hits for `0.0.0.0` in `perf/`) plus explicit `127.0.0.1` literals at both bind sites, rather than an automated source assertion.
3. Review findings WR-01/WR-02 (11-REVIEW.md), which touched the T-11-10/T-11-14 surfaces, were fixed post-review in commits b3cb64b and 9d22648 and verified present.
