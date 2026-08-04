---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 05
subsystem: controlplane
tags: [d-02, d-impl-38, artifacts, yaml, timestamps, ergo-06]
requires: ["15-01", "15-02"]
provides:
  - "ccf.controlplane.artifacts._ArtifactLoader (private) — resolver-stripped YAML loader"
  - "ccf.controlplane.artifacts.load_artifact — timestamps reach contracts as text"
  - "docs/surface-changes/15-05-timestamps.md — the behavior-class fragment"
affects:
  - "every caller of load_artifact whose artifact carries a timestamp"
  - "the eleven duplicated _instant helpers in /examples, now deletable"
tech-stack:
  added: []
  patterns:
    - "_reject_floats as the template for a refuse-never-repair parse guard"
    - "SafeLoader subclass with a copied resolver table (never mutated in place)"
key-files:
  created:
    - tests/controlplane/test_timestamps.py
    - docs/surface-changes/15-05-timestamps.md
  modified:
    - src/ccf/controlplane/artifacts.py
decisions:
  - "D-02 realized: Z is the ISO-8601 UTC designator, so the loader preserves it by reading timestamps as text and letting the contract's datetime annotation parse them"
  - "No public timestamp-parsing helper — one would invite adopters to keep hand-normalizing"
  - "The resolver table is copied, not mutated: mutating yaml.SafeLoader would change YAML parsing process-wide (T-15-05-02)"
metrics:
  tasks: 2
  duration: ~25m
  completed: 2026-08-04
---

# Phase 15 Plan 05: Artifact Timestamp Handling Summary

Timestamp handling is now correct once in `/src`: `load_artifact` parses through a
resolver-stripped `_ArtifactLoader` so a timestamp-shaped scalar reaches the contract as
`str`, a `datetime`-annotated field parses it into an aware UTC value, and a date-time
naming no zone is refused at parse with a message citing D-IMPL-38.

## What was built

**Task 1 — `src/ccf/controlplane/artifacts.py`** (commit `632ce2b`)

- `_ArtifactLoader(yaml.SafeLoader)` with its own `yaml_implicit_resolvers` dict, built as
  a comprehension over the base's table with every `tag:yaml.org,2002:timestamp` entry
  filtered out. The base table is read, never mutated — the blast-radius commitment.
- `_reject_naive_timestamps(value, path)`, a sibling of `_reject_floats` copying its three
  load-bearing parts verbatim: the dotted path accumulator with `'<root>'` fallback, the
  `Mapping` / `list`|`tuple` recursion, and the `ArtifactLoadError` type. It refuses a
  `datetime` with `tzinfo is None` (only reachable from a caller that pre-parsed with a
  stock loader) and a string matching `_NAIVE_TIMESTAMP_RE` — an ISO-8601 date-time with
  no `Z` and no offset. Both messages are two lines and one sentence, well inside the
  CINV-01a calibration `_reject_floats` sets.
- `parse_artifact` calls it immediately after `_reject_floats`; `load_artifact`'s single
  changed line is `yaml.safe_load(text)` → `yaml.load(text, Loader=_ArtifactLoader)`.
- The `_ArtifactLoader` docstring carries the D-02 reframing verbatim, so a future reader
  does not mistake "refuse naive, accept `Z`" for an inconsistency to fix.
- No public timestamp helper was added, per the plan's explicit instruction.

**Task 2 — tests and the fragment** (commit `9a126b7`)

`tests/controlplane/test_timestamps.py` pins the five behaviors against two throwaway
`CCFContract` fixtures (one `str`-annotated field, one `datetime`-annotated):

1. a bare timestamp scalar reaches the contract as `str` — the resolver is provably gone;
2. `...Z` yields `tzinfo is not None` and `utcoffset() == timedelta(0)`;
3. `...+00:00` yields the identical value, so the two conventions converge;
4. a designator-less date-time raises `ArtifactLoadError` whose message contains `D-IMPL-38`;
5. `yaml.safe_load("t: 2026-08-03T12:00:00Z")["t"]` is still a `datetime` — the shared
   loader is unmutated.

`docs/surface-changes/15-05-timestamps.md` carries one section with all seven fields,
`Surface: ccf.controlplane.artifacts.load_artifact` written verbatim for 15-21's literal
match, `Public surface: true`, and `Change type: behavior`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `mypy --strict` refused the untyped `SafeLoader` base**

- **Found during:** Task 2, at the `make ci-core` gate
- **Issue:** `artifacts.py:305: error: Class cannot subclass "SafeLoader" (has type "Any")
  [misc]`. PyYAML ships no inline types and `pyproject.toml` sets
  `ignore_missing_imports` for `yaml`, which makes `SafeLoader` an `Any` that strict mode
  will not accept as a base.
- **Fix:** a narrow `# type: ignore[misc]` on the class statement, with a five-line comment
  explaining that the base is exactly `SafeLoader` at runtime, that the subclass narrows
  what it resolves and widens nothing, and that everything parsed is validated by a typed
  contract immediately after — the same closure the existing `yaml` mypy override rests on.
  `pyproject.toml` was not touched (it is outside this plan's `files_modified`, and the
  override's stated rationale still holds unchanged).
- **Files modified:** `src/ccf/controlplane/artifacts.py`
- **Commit:** `9a126b7`

No other deviations. No architectural changes, no auth gates, no package installs
(T-15-05-SC holds).

## Verification

| Check | Result |
| --- | --- |
| `pytest tests/controlplane/ -q` | 73 passed (68 pre-existing + 5 new) |
| `grep -c "yaml.safe_load" src/ccf/controlplane/artifacts.py` | 0 |
| `python -m tools.lints --all` | exit 0 |
| `tools/dump_surface.py --report` | `added (0)`, `removed (0)`, `reshaped (0)` — the required empty diff |
| `pytest tests/test_surface_drift.py -q` | 6 passed |
| `make ci-core` | exit 0 — 1593 passed, 2 skipped |
| `docs/surface/v0.2-surface.json` | untouched |
| `docs/surface/v0.2-surface-baseline.json` | untouched |

The empty `--report` diff is the *expected* result here and is asserted as such: this plan
adds, removes, and reshapes no public name, which is exactly why the fragment is
`behavior`-class and why D-15 ships a curated log a signature diff cannot replace.

## Notes for downstream plans

- **15-07 through 15-10 widen this file further.** The shape left behind admits that
  cleanly: `_ArtifactLoader` and `_NAIVE_TIMESTAMP_RE` sit immediately above the guard
  functions, `parse_artifact` now runs a two-guard sequence any further guard appends to,
  and `__all__` is unchanged and still sorted. New `ArtifactClass` constants and contracts
  follow the file's existing five-part template untouched by this plan.
- **The eleven `_instant` helpers in `/examples` are now deletable** by the example
  rewrites — the loader does what they did, once.
- **`__all__` is unchanged**, so `tests/test_surface_drift.py`'s "no declared export
  resolves to nothing" assertion has nothing new to check from this plan.

## Known Stubs

None.

## Threat Flags

None — this plan narrows what the artifact parse path accepts and introduces no new
network, auth, file-access, or schema surface.

## Self-Check: PASSED

- `src/ccf/controlplane/artifacts.py` — FOUND (modified)
- `tests/controlplane/test_timestamps.py` — FOUND
- `docs/surface-changes/15-05-timestamps.md` — FOUND
- commit `632ce2b` — FOUND
- commit `9a126b7` — FOUND
