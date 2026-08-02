---
phase: 11-performance-battery
reviewed: 2026-08-01T00:00:00Z
depth: standard
files_reviewed: 41
files_reviewed_list:
  - .github/workflows/perf.yml
  - Makefile
  - pyproject.toml
  - perf/baselines/.gitkeep
  - perf/conftest.py
  - perf/gate.py
  - perf/__init__.py
  - perf/pytest.ini
  - perf/README.md
  - perf/suites/common.py
  - perf/suites/crossproc/conftest.py
  - perf/suites/crossproc/__init__.py
  - perf/suites/crossproc/test_mcp_egress.py
  - perf/suites/crossproc/test_peering.py
  - perf/suites/__init__.py
  - perf/suites/micro/conftest.py
  - perf/suites/micro/__init__.py
  - perf/suites/micro/test_dispatch.py
  - perf/suites/micro/test_factory.py
  - perf/suites/micro/test_gates.py
  - perf/suites/micro/test_operators.py
  - perf/suites/replay/conftest.py
  - perf/suites/replay/__init__.py
  - perf/suites/replay/test_replay_scale.py
  - perf/suites/scale/conftest.py
  - perf/suites/scale/__init__.py
  - perf/suites/scale/test_assembly.py
  - perf/suites/scale/test_projection.py
  - perf/synth/artifacts/agent.yaml
  - perf/synth/artifacts/controlplane.yaml
  - perf/synth/artifacts/ontology.yaml
  - perf/synth/artifacts/prompt.yaml
  - perf/synth/artifacts/task.yaml
  - perf/synth/artifacts/workflow.yaml
  - perf/synth/generator.py
  - perf/synth/__init__.py
  - perf/thresholds.toml
  - tests/perf_gate/__init__.py
  - tests/perf_gate/test_gate.py
  - tests/perf_smoke/__init__.py
  - tests/perf_smoke/test_smoke.py
  - tests/perf_synth/__init__.py
  - tests/perf_synth/test_determinism.py
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-08-01
**Depth:** standard
**Files Reviewed:** 41
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Reviewed the performance-battery phase: gate script, synthetic generator, four benchmark suites, always-on smoke/determinism/gate tests, Makefile targets, and the opt-in workflow. The load-bearing invariants hold: `perf/gate.py` has no write path to `perf/baselines/` and applies loosen-only override validation; the workflow is `workflow_dispatch`-only with a pinned `ubuntu-24.04` runner and a restricted `choice` input (no shell-injection surface in the `case` block); the runner-class key is charset-sanitized with an anchored full-match plus explicit `.`/`..` rejection before path join; the generator reads no clock (fixed `EPOCH`, seeded RNGs) and all vocabulary/thresholds/prompts live in YAML artifacts (No-Hardcoding honored); ingestion goes exclusively through `handle.worker.ingest` (single-writer); no harness or LLM-client imports anywhere in `perf/`. Speed-ups warn and never fail, as documented.

No blockers found after tracing the gate math (nearest-rank percentile index formula is correct for the pinned 100-element fixture), the replication loop in the replay history factory, and the crossproc teardown ladder. The warnings below are robustness gaps around subprocess lifecycle, a latent infinite loop in the edge sampler, and error-typing gaps in the gate.

## Warnings

### WR-01: Readiness handshake has no deadline — a hung producer child hangs `make perf-xproc` forever

**File:** `perf/suites/crossproc/conftest.py:136`
**Issue:** `proc.stdout.readline()` blocks indefinitely if the child starts but never prints `READY ...` and never exits (e.g., a server that deadlocks during startup). The docstring frames the blocking readline as a virtue ("never a wait-loop"), but a handshake without a deadline is a hang, not a gate. In CI the 30-minute job timeout eventually kills it; a local `make perf-xproc` wedges until the user notices. The teardown `finally` does run only after the readline returns — which it never does.
**Fix:** Bound the handshake, e.g. read the announcement on a helper thread and `thread.join(timeout=HANDSHAKE_TIMEOUT_SECONDS)`, or use `selectors`/`os.set_blocking` with a deadline; on expiry, fall through to the existing killpg teardown and raise with the captured stderr.

### WR-02: Smoke-test timeout can orphan the crossproc producer grandchild — the exact T-11-10 threat the fixture guards against

**File:** `tests/perf_smoke/test_smoke.py:61-76`
**Issue:** `subprocess.run(..., timeout=SUITE_TIMEOUT_SECONDS)` kills only the direct child (the inner pytest). The crossproc suite's producer child is spawned with `start_new_session=True`, so it is in a different session/process group and survives the kill — its fixture `finally` never runs because the inner pytest died on SIGKILL. Result: on a crossproc hang, the always-on job fails loudly (good) but leaves an orphaned two-server process holding ports (the T-11-10 threat, now unmitigated on this path).
**Fix:** Launch the inner pytest with `start_new_session=True` and on `TimeoutExpired` kill its whole process group (`os.killpg`) — mirroring the crossproc fixture's own SIGTERM→wait→SIGKILL discipline — before re-raising/failing.

### WR-03: Unique-edge sampler can loop forever; feasibility is documented in a comment two files away, not enforced

**File:** `perf/synth/generator.py:170-174`
**Issue:** The `while len(edge_set) < target_edges` loop terminates only if `hub_count * tail_count >= K_AVG_DEGREE * rung` unique (hub, tail) pairs exist (each pair admits exactly one relationship type). `perf/suites/scale/conftest.py` documents that below ~400 entities the sampler "cannot terminate," but `_topology()` itself performs no feasibility check — `_topology(300)` is a silent infinite loop, not an error. Any future caller (Phase 12 reuse is explicitly invited by `perf/synth/__init__.py`) that picks a small rung hangs instead of failing.
**Fix:** In `_topology`, before the loop: `if hub_count * tail_count < target_edges: raise ValueError(f"rung {rung} cannot yield {target_edges} unique edges from {hub_count} hubs x {tail_count} tails")`.

### WR-04: Malformed threshold override raises `KeyError`/`ValueError`, not the promised `ThresholdConfigError`

**File:** `perf/gate.py:139-142`
**Issue:** `resolve_threshold` promises typed config errors ("unknown suite, malformed table" per the `ThresholdConfigError` docstring, and README: "gate.py rejects a tighter override with a typed load error"). But an override table missing the `threshold` key raises a bare `KeyError` at `override_table["threshold"]`, and a non-numeric value (`threshold = "0.3"` is fine, but `threshold = "abc"`) raises `ValueError` from `float()`. Same for a non-numeric suite `default` at line 138. These propagate as tracebacks out of `evaluate()`/`main()`.
**Fix:** Wrap both extractions:
```python
try:
    override = float(override_table["threshold"])
except (KeyError, TypeError, ValueError) as exc:
    raise ThresholdConfigError(
        f"override for {benchmark_id!r} is malformed: {exc}") from exc
```
(and equivalently for the suite default).

### WR-05: Replay-side operator construction duplicates `build_operator_registry` instead of sharing it — drift breaks the byte-exact assert at the worst time

**File:** `perf/suites/replay/conftest.py:111-187` (vs `perf/suites/common.py:92-179`)
**Issue:** `_operators()` is a near-verbatim copy of `common.build_operator_registry` (parameter wiring, corpus construction, all four operators), and `PerfPanelPlan` near-duplicates `PerfPlan` (differing only in one payload key). The replay design depends on "same declared parameters → same parameter hashes"; the record phase and replay environment both call the local `_operators`, so they agree with each other — but a future parameter change made in `common.py` (which micro/scale use) silently diverges from the replay suite's copy. The byte-exact assert only protects internal consistency of the replay file, not cross-suite consistency, and the divergence would surface as a confusing opt-in-run failure long after the edit. Also `_load`/`_instant` are now triplicated (`common.py`, `crossproc/conftest.py`, `replay/conftest.py`).
**Fix:** Have `replay/conftest.py` import `build_operator_registry`, `instant`, and (with the one payload key parameterized or accepted as a second plan class) `PerfPlan` from `perf.suites.common`; delete the copies.

## Info

### IN-01: Gate exit code conflates config errors with regressions

**File:** `perf/gate.py:281-306`
**Issue:** The module contract says nonzero means "gated slowdown regression," but an uncaught `ThresholdConfigError` (or malformed raw/baseline JSON) exits 1 via traceback — indistinguishable by exit code from a regression for any wrapper scripting.
**Fix:** Catch `ThresholdConfigError` in `main()` and exit with a distinct code (e.g., 2) after printing the message.

### IN-02: Malformed baseline JSON produces a raw traceback

**File:** `perf/gate.py:232-233`
**Issue:** `load_baseline` assumes `payload["benchmarks"]` exists and values are float-able; a hand-written baseline (the ritual is manual) with a typo tracebacks instead of a clear "baseline file malformed" message.
**Fix:** Wrap parsing in try/except and return a report-only result with a loud reason, or exit with the config-error code from IN-01.

### IN-03: The no-write-to-baselines source assertion is easy to defeat

**File:** `tests/perf_gate/test_gate.py:274-281`
**Issue:** The structural check only inspects lines containing the literal `baselines` together with `open(`/`write_text` and a `"w"` mode on the same line. A write through a variable holding the path (e.g., `p = BASELINES_DIR / f; p.write_text(...)`) on a line not containing "baselines" passes. Affects test reliability of a claimed structural invariant.
**Fix:** Assert on the whole source: no `BASELINES_DIR` usage combined with any write API (`write_text`, `write_bytes`, `open(` with a write mode) anywhere in the file, or AST-walk for attribute calls on paths derived from `BASELINES_DIR`.

### IN-04: Unused parameter `recorded_decision` in `test_curve_shape`

**File:** `perf/suites/replay/test_replay_scale.py:112`
**Issue:** The fixture argument is never used in the test body (it is session-scoped and already built by the ladder tests, so it costs nothing, but it is dead code).
**Fix:** Remove the parameter.

### IN-05: Fragile READY announcement parse

**File:** `perf/suites/crossproc/conftest.py:143`
**Issue:** `_token, mcp_port, a2a_port = announcement.split()` raises a bare `ValueError` (unpack mismatch) if the child prints `READY` with the wrong token count — losing the helpful stderr-capture diagnostic that the `startswith` branch provides.
**Fix:** Split once, check `len(parts) == 3`, and reuse the stderr-dump error path.

### IN-06: `_MEDIANS` module-level mutable state couples the ladder tests to `test_curve_shape` via execution order

**File:** `perf/suites/replay/test_replay_scale.py:69,109,119`
**Issue:** The curve fit depends on all three parametrized tests having run in the same process before it, communicated through a module global. Under `pytest-xdist`, `-k` selection, or test randomization the guard assert fires loudly (so it fails safe), but the mechanism is fragile by construction.
**Fix:** Acceptable as-is given the guard; a class-scoped fixture or `request.config` stash would remove the ordering coupling.

### IN-07: `perf.yml` pip cache is largely ineffective

**File:** `.github/workflows/perf.yml:43-51`
**Issue:** `setup-python` with `cache: pip` caches the runner-level pip cache, but the job then installs into a fresh `.venv`; wheels are cached but the venv build repeats each run. Minor CI-time cost only.
**Fix:** Optionally cache `.venv` keyed on `pyproject.toml`, or accept the cost.

---

_Reviewed: 2026-08-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
