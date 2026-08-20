---
phase: 20
slug: client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-20
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `20-RESEARCH.md` § Validation Architecture. The per-task map is
> completed by the planner; everything above it is measured.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (measured) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/examples -q` |
| **Full suite command** | `make ci` |
| **Estimated runtime** | quick ~10s · `make ci` minutes |

**Interpreter rule — `.venv/bin/python` always.** Bare `python` does not exist on this
host; a plan that writes `python` reports a false red. CI overrides with `make PYTHON=python`.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/examples -q`
- **After every plan wave:** `make ci-core` — a gate `ci-core` does not reach is not a
  gate (DEF-17-08)
- **Before `/gsd:verify-work`:** `make ci` exit 0, then the §3.1 cross-AI panel on
  shipped code
- **Max feedback latency:** ~10 seconds at task granularity

---

## Criterion → Validation Map

The ten ROADMAP Success Criteria are the gate target and are closed. Each must be
verified by a command, not by inspection.

| # | Criterion | Level | Automated command | Exists? |
|---|-----------|-------|-------------------|---------|
| 1 | ADK registers/calls/prints, zero `ccf` imports | example run + AST gate | `make example-hw1-harness-clients`; `pytest tests/examples/test_client_example_purity.py -q` | ❌ new |
| 2 | Anthropic Agent SDK, same | example run + AST gate | same | ❌ new (Q1 verdict: viable) |
| 3 | LangGraph, same | example run + AST gate | same | ❌ new |
| 4 | Same content address as `consume.py` | assertion inside the runner | `make example-hw1-harness-clients` | ❌ new |
| 5 | AST purity gate + named sabotage control | unit tests + controls | `pytest tests/examples/test_client_example_purity.py -q` | ⚠️ module exists; per-root permitted set + controls are new |
| 6 | Deterministic default, `--live` opt-in | CI target + no-model guard | `make examples`; new no-model guard test with its own control | ❌ new |
| 7 | No new SDK mechanism | diff assertion at close | `git diff --stat <base>..HEAD -- src/ccf/client/` empty | ✅ command exists, assertion new |
| 8 | Duplicates resolved in-phase | tree assertion + green pipeline | `test -d examples/s2-01-external-consumers` must fail; `make example-ext-00`; `make gate-tools` | ⚠️ partly exists |
| 9 | README content | structural test | new test asserting required README elements by name | ❌ new |
| 10 | `make ci` exit 0, target wired | full pipeline | `make ci`; plus a test asserting the new target is in the `examples:` prerequisite list | ⚠️ `make ci` exists, wiring assertion new |

---

## Per-Task Verification Map

*Completed by the planner — one row per task, each with an automated command.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| *(planner fills)* | | | | | | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `examples/hw1-harness-clients/runner/run.py` — seed-and-close runner
- [ ] `examples/hw1-harness-clients/artifacts/scenario-rows.yaml` — the declared input document
- [ ] Per-root permitted set + sabotage controls in `tests/examples/test_client_example_purity.py`
- [ ] No-model guard test for legs 1 and 3, with a control
- [ ] README-structure test
- [ ] `make`-target-wiring test
- [ ] Tree assertion that `examples/s2-01-external-consumers/` is gone
- [ ] Regenerated `docs/surface/examples/RETIREMENT-COUPLINGS.md`

No framework install is needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| x86_64 wheel bundles the `claude` CLI | criterion 2, 10 | No network/CI token in-session; platform-tagged wheel resolution cannot be observed from this ARM host | One CI run, or `pip download claude-agent-sdk==0.2.128 --platform manylinux_2_17_x86_64 --no-deps` and inspect the wheel for `_bundled/claude` |

---

## Validation Sign-Off

- [ ] All tasks have an automated verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Every new gate carries a named sabotage control (`CLNT-12` / `D-22`)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
