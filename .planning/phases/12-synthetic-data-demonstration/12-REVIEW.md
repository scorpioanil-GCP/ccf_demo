---
phase: 12-synthetic-data-demonstration
reviewed: 2026-08-02T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - Makefile
  - docs/demo-walkthrough.md
  - examples/08-e2e-demo/README.md
  - examples/08-e2e-demo/artifacts/agent.yaml
  - examples/08-e2e-demo/artifacts/controlplane.yaml
  - examples/08-e2e-demo/artifacts/expected_output.txt
  - examples/08-e2e-demo/artifacts/halflife.yaml
  - examples/08-e2e-demo/artifacts/ontology.yaml
  - examples/08-e2e-demo/artifacts/prompt.yaml
  - examples/08-e2e-demo/artifacts/scenario.yaml
  - examples/08-e2e-demo/artifacts/skills.yaml
  - examples/08-e2e-demo/generator.py
  - examples/08-e2e-demo/run.py
  - tests/examples/__init__.py
  - tests/examples/test_demo_generator.py
findings:
  critical: 0
  warning: 5
  info: 5
  total: 10
status: fixed
---

# Phase 12: Code Review Report

**Reviewed:** 2026-08-02
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Reviewed the Phase 12 synthetic-data demonstration: the deterministic
generator, the six-stage e2e driver, all eight definition artifacts, the
determinism test module, the Makefile target, and the two docs. The
No-Hardcoding discipline is genuinely upheld — I traced every vocabulary
and threshold value in `generator.py` and `run.py` back to an artifact key
(scenario roles, ontology roles, dispatch arguments); no domain literal
exists in code. Single-writer holds: the generator writes only standalone
source SQLite files, and the driver's only fabric write path is
`handle.worker.ingest`. Pin arithmetic in `scenario.yaml` and
`controlplane.yaml` was verified by hand (6870 envelopes = 1160+3600+905+1205;
entity_count 4458 = 1205+1188+1160+905; row counts consistent), and the
banner strings in `run.py` reconcile against `expected_output.txt`
line-for-line, including the string-concatenation splits.

No BLOCKER-tier findings. The warnings below are real robustness and
security-hygiene gaps in mechanism code that the docs explicitly invite
users to re-drive with their own scenario artifacts, plus a systemic
reliance on `assert` for all demo verification.

## Warnings

### WR-01: Entire demo verification is `assert`-based and vanishes under `python -O`

**resolution:** RESOLVED — fix(12) 1df8b69 — bare asserts replaced with unconditional `_require` helper

**File:** `examples/08-e2e-demo/run.py:592-1031` (throughout `main`)
**Issue:** Every correctness check in the demo — generation checksum pins
(592–596), the baseline zero (640), envelope/resolution counts (691–692),
gate outcome (820), detection pins (943–950), replay round-trip
(998–1011), and the final narration byte-compare (1029) — is a bare
`assert` statement. Under `python -O` / `PYTHONOPTIMIZE=1` all of them are
stripped and the demo exits 0 having verified nothing, while the README
states "Exit code 0 means every assertion held." CI happens not to use
`-O`, so this is latent rather than active, but a single environment
variable silently converts the "executed, not asserted" claim into
asserted-only.
**Fix:** Replace load-bearing checks with an explicit helper that raises
unconditionally, e.g.:
```python
def _require(condition: bool, message: object) -> None:
    if not condition:
        raise RuntimeError(f"demo verification failed: {message}")
```
and use it for at least the pin comparisons and the narration
byte-compare. (Same pattern already used correctly in `RefusedSink`,
which raises explicitly rather than using an `assert` statement.)

### WR-02: `ZeroDivisionError` / sign bug in amount-tolerance check

**resolution:** RESOLVED — fix(12) fda8cf4 — zero/negative amounts guarded in tolerance check

**File:** `examples/08-e2e-demo/run.py:292-293`
**Issue:** `_extends` computes
`abs(amount - previous) / previous * 100.0 <= tolerance_percent`.
This is generic mechanism explicitly offered for reuse with user-authored
scenarios ("change the scenario to make your own demo"). If any edge
amount is `0`, the division raises `ZeroDivisionError` and the run
crashes; if `previous` is negative (nothing in the code or the skill
argument schema forbids negative amounts), the left side is negative and
the tolerance check is unconditionally true, silently admitting arbitrary
amount jumps into "structured" cycles. Also asymmetric: A→B passes where
B→A may fail.
**Fix:**
```python
def _extends(previous: float, amount: float) -> bool:
    denominator = abs(previous)
    if denominator == 0.0:
        return amount == previous
    return abs(amount - previous) / denominator * 100.0 <= tolerance_percent
```

### WR-03: SQL identifier quoting does not escape embedded double quotes

**resolution:** RESOLVED — fix(12) 997e092 — embedded quotes escaped in centralized identifier quoting

**File:** `examples/08-e2e-demo/generator.py:70-73, 132-138`; `examples/08-e2e-demo/run.py:224-230`; `tests/examples/test_demo_generator.py:113, 128`
**Issue:** Table and column names from `scenario.yaml` are interpolated
into SQL as `f'"{name}"'` with no escaping. A name containing a `"`
character breaks out of the identifier quoting — e.g. a scenario table
name of `x" (y TEXT); --` yields malformed/injected DDL in
`_create_and_fill` and injected SELECT text in `source_checksum` and
`_mapped_rows`. The module docstrings claim "table/column names come from
the versioned artifact and are quoted" as the T-12-01 mitigation; the
quoting is incomplete, so the documented mitigation does not actually
hold for artifact-supplied identifiers. The artifact is versioned and
reviewed, which caps severity at Warning, but the docs explicitly tell
users to author their own scenarios and feed them to this interpreter.
**Fix:** Centralize identifier quoting with escaping and use it at every
interpolation site:
```python
def _ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'
```

### WR-04: Unbounded recursion in `_structured_cycles._walk`

**resolution:** RESOLVED — fix(12) a27785c — recursion converted to explicit-stack iteration

**File:** `examples/08-e2e-demo/run.py:294-315`
**Issue:** `_walk` recurses once per edge appended to the path; maximum
depth equals the number of distinct parties reachable under the tolerance
and span constraints. With the shipped scenario the constraints keep
paths short, but the function is generic mechanism over user-declared
parameters: a scenario with a large connected party set plus a loose
`amount_tolerance_percent` / `max_span_days` (both artifact values) can
exceed Python's default recursion limit (~1000) and abort with
`RecursionError` — for a population of 1200+ parties that is a reachable
configuration, not a theoretical one.
**Fix:** Convert `_walk` to an explicit stack iteration, or at minimum
enforce a documented path-length ceiling (e.g. derive it from
`min_cycle_length` plus a declared `max_cycle_length` dispatch argument)
and stop extending paths beyond it.

### WR-05: Checksum line encoding is collision-prone (`|`-joined `str()` values)

**resolution:** RESOLVED — fix(12) d281efa — collision-safe repr row encoding; pins regenerated

**File:** `examples/08-e2e-demo/generator.py:76-79, 361-363`
**Issue:** `source_checksum` and the ring signature hash rows as
`"|".join(str(v) for v in row)` with `\n` line separators. Values are not
escaped, so a value containing `|` (or `\n`) makes distinct logical rows
hash identically — the determinism pin can then fail to detect a real
content change, which defeats its stated purpose as the drift alarm.
Wire `purpose`, `memo`, address, and name fields are free text in the
artifact; nothing prevents a user scenario from containing either
character. Additionally `str(None)` for a NULL column is
indistinguishable from the literal string `"None"`.
**Fix:** Hash an unambiguous encoding per row, e.g.
`digest.update(repr(tuple(row)).encode())` per sorted row, or
length-prefix each field before joining.

## Info

### IN-01: Duplicated import

**File:** `examples/08-e2e-demo/run.py:68-69`
**Issue:** `from ccf.contracts.canonical import content_hash` appears
twice on consecutive lines.
**Fix:** Delete line 69.

### IN-02: Cycle counting collapses distinct cycles over the same member set

**File:** `examples/08-e2e-demo/run.py:307`
**Issue:** Found cycles are deduplicated as `tuple(sorted(members))`, so
two genuinely distinct edge cycles over the same party set count as one
in `cycles_found`. Harmless for the pinned demo (expected count 1) but a
silent undercount for user scenarios; the skill description ("directed
cycles ... at least the declared length") does not disclose the
member-set semantics.
**Fix:** Either dedupe on the canonical edge sequence (rotation-normalized
edge reference tuple) or document member-set semantics in the skill's
`description` in `skills.yaml`.

### IN-03: Redundant double sorting and O(n²) table lookup in checksum path

**File:** `examples/08-e2e-demo/generator.py:73-76, 85-86`
**Issue:** `source_checksum` both `ORDER BY`s every column and re-sorts
the rendered lines (one of the two is dead weight);
`_combined_source_checksum` does a linear `next(...)` scan inside the
sorted-name loop instead of building a name→spec map once. Correctness is
unaffected; this is clarity/dead-code, not performance scope.
**Fix:** Drop the Python-side `sorted(...)` (the SQL `ORDER BY` already
defines the order) or drop the `ORDER BY`; build
`{t["name"]: t for t in tables.values()}` once.

### IN-04: `--live` prints unfiltered model output to the terminal

**File:** `examples/08-e2e-demo/run.py:492`
**Issue:** `print(response.json()["message"]["content"])` emits raw model
text; a hostile/compromised local endpoint could embed terminal control
sequences. Opt-in, local-only, never CI — noting for completeness.
**Fix:** Strip control characters (e.g. `re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)`) before printing.

### IN-05: `payload` reserved keys can silently collide with artifact-declared keys

**File:** `examples/08-e2e-demo/run.py:239-241`
**Issue:** `_mapped_rows` stores bookkeeping under `"__row_id"` /
`"__observed"` in the same dict as artifact-declared payload keys. An
ontology `ingest.payload` entry named `__row_id` would be silently
overwritten rather than rejected.
**Fix:** Raise `ValueError` if `entry["payload"]` contains either
reserved key.

---

_Reviewed: 2026-08-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
