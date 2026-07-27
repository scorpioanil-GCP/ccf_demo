---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 02
subsystem: build-configuration
tags: [dependencies, extras, mypy, pytest-markers, harness-neutrality]
requires: []
provides:
  - "mcp==1.28.1, joserfc==1.7.4, a2a-sdk==1.1.2, uvicorn==0.51.0 as core pins"
  - "adk / claude-agent / langgraph per-harness extras plus the harnesses aggregate"
  - "mypy --strict coverage of /runtime with six individually justified overrides"
  - "crossproc and harness pytest markers"
  - "tests/lints/test_extra_isolation.py — install-time harness neutrality guard"
affects:
  - "every subsequent 06-* plan (all import something pinned here)"
  - ".github/workflows/ci.yml mypy step"
tech-stack:
  added: [mcp, joserfc, a2a-sdk, uvicorn, google-adk, claude-agent-sdk, langgraph]
  patterns: ["self-referential extras for one-command install", "one mypy override block per untyped module"]
key-files:
  created:
    - tests/lints/test_extra_isolation.py
  modified:
    - pyproject.toml
    - .github/workflows/ci.yml
decisions:
  - "joserfc retained: jws.detach_json_content() confirmed to exist at 1.7.4 (open caveat closed)"
  - "chromadb given its own mypy override so 'mypy --strict clean' stops being environment-dependent"
  - "CI mypy step changed from 'mypy --strict src' to bare 'mypy' so /runtime is genuinely checked"
metrics:
  duration: ~25m
  completed: 2026-07-26
---

# Phase 06 Plan 02: Dependency & Type-Check Surface Summary

Pinned the four cross-process core dependencies, added three composable per-harness
extras plus a `harnesses` aggregate that makes `pip install -e ".[dev]"` the one command
installing all three harness legs (D-08), extended `mypy --strict` to `/runtime` with six
individually justified per-module overrides (research finding B2), registered the
`crossproc` and `harness` markers, and made install-time harness neutrality a failing test
rather than a README sentence.

## Task 1 — Package legitimacy checkpoint (pre-cleared)

The `gate="blocking-human"` checkpoint was presented to Dave by the orchestrator before
this executor was spawned. **Response: "approved"** — proceed with all six dependencies as
specified, no swaps. Verification record gathered at the gate:

| Package | Version | Source | Publisher | License | Status |
|---|---|---|---|---|---|
| `mcp` | 1.28.1 | github.com/modelcontextprotocol/python-sdk | Anthropic PBC | MIT | Confirmed |
| `a2a-sdk` | 1.1.2 | github.com/a2aproject/a2a-python | Google LLC | Apache-2.0 | Confirmed |
| `joserfc` | 1.7.4 | github.com/authlib/joserfc | Hsiaoming Yang (lepture, Authlib author) | BSD-3-Clause | Confirmed |

The three harness SDKs (`google-adk`, `claude-agent-sdk`, `langgraph`) were named by
Dave's own D-IMPL-24 ruling and carried `[VERIFIED: PyPI + executed]` status from
06-RESEARCH.md's slopcheck audit (13 OK / 0 SUS / 0 SLOP, 2026-07-26).

### The open joserfc caveat is CLOSED

The gate carried forward one advisory caveat: 06-RESEARCH.md cites
`jws.detach_json_content()` as the reason to prefer `joserfc` over `PyJWT`, but the API
could not be confirmed by name from the PyPI page (the page documents RFC 7797 generally).

**Confirmed empirically after install:**

```
$ python -c "from joserfc import jws; print([n for n in dir(jws) if 'detach' in n.lower()])"
['detach_compact_content', 'detach_content', 'detach_json_content']
```

All three detachment primitives exist at `joserfc==1.7.4`. `jws.detach_json_content()` is
real and available under exactly the name research cited. **Plan 06-07 (identity/signing)
can rely on it; no escalation to Dave is required and no dependency swap is warranted.**

## Task 2 — Core pins and harness extras

Added to `[project] dependencies` under a `# Pins per 06-RESEARCH.md Standard Stack
(slopcheck-audited 2026-07-26).` block: `mcp==1.28.1`, `joserfc==1.7.4`, `a2a-sdk==1.1.2`,
`uvicorn==0.51.0`. `httpx` and `starlette` arrive transitively and were deliberately not
pinned directly, per the plan.

Added to `[project.optional-dependencies]`, each with its D-08 reason inline:
`adk = ["google-adk==2.5.0"]`, `claude-agent = ["claude-agent-sdk==0.2.128"]`,
`langgraph = ["langgraph==1.2.9"]`, `harnesses = ["ccf[adk,claude-agent,langgraph]"]`, and
`dev` extended with `"ccf[harnesses]"`.

**Research assumption A1 (self-referential extras unverified) is resolved: they work.**
Verified in a clean venv against this project's actual setuptools/pip, at *two* levels of
nesting — `dev` → `harnesses` → the three per-harness extras. No fallback to duplicated
requirement strings was needed.

Verification, all in a fresh `python3 -m venv`:
- `pip install -e ".[harnesses]"` → succeeds; `pip check` → "No broken requirements found."
- `pip install -e ".[dev]"` → succeeds; `pip check` clean; the nested self-reference resolves
- `import mcp, joserfc, a2a, google.adk, langgraph, claude_agent_sdk` → exits 0
- `pydantic.VERSION == '2.13.4'` and `yaml.__version__ == '6.0.3'` → the repo's existing
  pins survive the new ~82-package tree unchanged

The one command is documented in a comment block immediately above
`[project.optional-dependencies]`. `.github/workflows/ci.yml` already installs
`-e ".[dev]"` at both jobs, so it required no change to pick up all three harness legs.

## Task 3 — mypy over /runtime, markers, extras isolation

**mypy.** `[tool.mypy] files` is now `["src", "runtime"]` with `strict` and
`warn_unreachable` unchanged. Six `[[tool.mypy.overrides]]` blocks were added, **one per
module, never a blanket block** — a blanket block would silently absorb future untyped
imports and would make the D-21-compliant claim unstateable. Each carries its own
justification arguing the untyped boundary is closed by CCF's own typed validation at the
seam rather than by trusting the vendor:

| Module | Justification theme |
|---|---|
| `google.adk.*` | No `py.typed`; confined to the CINV-02 carve-out module; CCF contracts on both sides of the seam |
| `langgraph.*` | Untyped `StateGraph`/invoke surfaces; adapter signatures fully typed; notes the D-IMPL-17 harness-vs-orchestrator distinction |
| `langchain_core.*` | Separate distribution, separate cadence — collapsing it into `langgraph.*` would hide the day it ships types |
| `claude_agent_sdk.*` | No `py.typed`; governed seam (skill-set, effects) typed CCF-side |
| `a2a.*` | Protobuf-generated; 06-RESEARCH.md Pitfall 5 — proto types are *not* the CCF boundary and must not be typed as if they were |
| `chromadb`, `chromadb.*` | See deviation below |

**Research assumption A3 (protobuf `a2a_pb2` may need more than
`ignore_missing_imports`) did not bite.** No `types-protobuf` and no additional per-module
settings were required; `mypy` is clean over the whole tree with the single `a2a.*`
override. No residual to carry forward. This will want re-checking once
`ccf_runtime/a2a/` actually contains code — nothing imports `a2a` yet.

**Markers.** `crossproc: spawns real subprocesses over loopback — D-15/D-16` and
`harness: requires a harness extra (adk | claude-agent | langgraph) — D-08/D-09`, both in
the existing decision-naming row format.

**Extras isolation.** `tests/lints/test_extra_isolation.py` (9 tests) asserts the claim
declaratively from `pyproject.toml`, since a test process cannot uninstall packages to
prove a negative about what an install would pull. It handles PEP 503 name normalization
and recursively expands self-referential extras, so the aggregate cannot satisfy D-08's
one-command requirement while the isolation assertions silently examine an empty set. Its
module docstring scopes the claim per D-21: it enforces *declaration-site* exclusivity and
says explicitly that it cannot prove anything about transitive arrival.

The regression case was verified as the plan required: temporarily adding
`google-adk==2.5.0` to `[project] dependencies` produced
`FAILED test_no_harness_is_a_core_dependency[google-adk]`; the file was then restored and
`git diff --stat` confirmed the restoration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `mypy` failed on `chromadb` in any environment without the optional `chroma` extra**

- **Found during:** Task 3, first `python -m mypy` run
- **Issue:** `src/ccf/similarity/chroma_index.py:106` imports `chromadb`, which is
  deliberately *not* in `dev` ("NEVER a core dependency", 04-RESEARCH.md). A `dev`-only
  environment — which is exactly what CI installs — cannot resolve it, so
  `mypy` reported `import-not-found` and could not exit 0. This is pre-existing, not
  caused by the `/runtime` extension (it reproduces with `files = ["src"]`), but it
  blocked the task's acceptance criterion.
- **Fix:** Added a sixth `[[tool.mypy.overrides]]` block for `chromadb` with its own
  justification. The substantive point in the comment: without it, "mypy --strict clean"
  is a claim whose truth depends on whether an optional extra happens to be installed
  locally, which is precisely the kind of environment-dependent assertion D-21 objects to.
- **Files modified:** `pyproject.toml`
- **Commit:** `04a6035`

**2. [Rule 2 - Missing critical functionality] CI ran `mypy --strict src`, which would have excluded every file this phase adds**

- **Found during:** Task 3
- **Issue:** `.github/workflows/ci.yml:41` passed an explicit path, overriding
  `[tool.mypy] files`. Extending the config to `["src", "runtime"]` would have had **zero
  effect in CI** — the entire point of finding B2 would have been silently defeated, and
  the phase's adapters, transports, and MCP servers would still have shipped unchecked.
- **Fix:** Changed the step to bare `mypy`, with a comment stating that `[tool.mypy] files`
  is the single source of truth for what is checked and why passing `src` was wrong.
- **Files modified:** `.github/workflows/ci.yml`
- **Commit:** `04a6035`

### Notes for downstream plans

- **06-07 (identity/signing):** `joserfc.jws.detach_json_content()` is confirmed present.
  So are `detach_content` and `detach_compact_content`.
- **06-04+ (`ccf_runtime.a2a`, adapters):** the mypy overrides are in place but **untested
  against real usage** — nothing imports `a2a`, `google.adk`, `langgraph`, or
  `claude_agent_sdk` yet. The A3 protobuf question is answered only for "the override
  parses"; it is not yet answered for "typed code calls into it". Budget a little time in
  the first plan that actually imports `a2a`.
- **CINV-02 carve-out:** landed in 06-01 and is already in this base. The `google.adk.*`
  and `claude_agent_sdk.*` override comments reference `ccf_runtime.adapters.*` as the
  confinement boundary on the assumption that carve-out holds.

## Verification

| Check | Result |
|---|---|
| `pip install -e ".[harnesses]"` clean venv | pass |
| `pip install -e ".[dev]"` clean venv (nested self-ref) | pass |
| `pip check` | "No broken requirements found." |
| `import mcp, joserfc, a2a, google.adk, langgraph, claude_agent_sdk` | exits 0 |
| `pydantic==2.13.4`, `pyyaml==6.0.3` unchanged | pass |
| `python -m mypy` (src + runtime, strict) | Success: no issues found in 70 source files |
| mypy verbose names files under `runtime/ccf_runtime` | 8 |
| `pytest tests/lints/test_extra_isolation.py -q` | 9 passed |
| Regression: harness in core deps fails the test | confirmed, then restored |
| `pytest --markers \| grep -c 'crossproc\|harness:'` | 2 |
| `grep -B3 'ignore_missing_imports' \| grep -c '^#'` | 7 (≥5 required) |
| `python -m tools.lints --all` | exit 0 |
| `pytest tests -q -m "not postgres and not chroma"` | 609 passed, 2 skipped |
| `pytest tools/lints/tests -q` | 49 passed |

## Known Stubs

None.

## Threat Flags

None. The plan's threat register items are addressed: T-06-04/T-06-05/T-06-SC by the
pre-cleared legitimacy checkpoint plus exact `==` pins; T-06-06 by
`tests/lints/test_extra_isolation.py`; T-06-07 by six single-module override blocks with
individual justifications (grep-verified).

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | — | Checkpoint, pre-cleared by orchestrator; no code |
| 2 | `08ec7cd` | Core pins + composable harness extras (D-08) |
| 3 | `04a6035` | mypy over /runtime, markers, extras isolation test, CI fix |

## Self-Check: PASSED

All three artifacts exist on disk (`pyproject.toml`,
`tests/lints/test_extra_isolation.py`, `06-02-SUMMARY.md`) and both task commits
(`08ec7cd`, `04a6035`) are present in `git log`.
