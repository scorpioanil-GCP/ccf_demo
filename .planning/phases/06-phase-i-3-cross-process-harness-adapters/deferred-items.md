# Deferred items — Phase I.3

Out-of-scope discoveries, logged rather than fixed (executor SCOPE BOUNDARY).

## From plan 06-09 (wave 4)

**1. `tests/conformance/test_harness_adapter.py` — two pre-existing failures,
environment-dependent.**

- `test_an_absent_harness_skips_with_an_instruction_not_a_mystery`
- `test_an_absent_harness_fails_when_the_environment_requires_it`

Both call `harness_unavailable("langgraph", "langgraph")` and expect it to
raise `Skipped` / `Failed`. In the project venv **langgraph is installed**, so
the harness is not absent and neither raises. The tests assert the behaviour of
the *absent*-harness path while naming a harness that is present, so they pass
only in an environment where the `langgraph` extra is missing — which is not
the documented `pip install -e ".[dev]"` environment.

Confirmed pre-existing on base `d51f9af`: the suite fails identically with
06-09's three new files excluded (801 passed / 2 failed), and 06-09 touched
nothing under `tests/conformance/` or `runtime/ccf_runtime/adapters/`.

Owner: plan 06-13 / the harness-adapter wave. The fix is to exercise the
absent-harness path against a name that is genuinely not installed (or to
monkeypatch the availability probe) rather than against a real harness.

**2. `tests/invariants/test_mcp_role_separation.py` digests the SQLite main
file only.**

`test_a_full_store_cycle_leaves_the_fabric_byte_identical` hashes
`database_path.read_bytes()`. The SQLite backend runs in WAL mode
(`src/ccf/graph/backends/sqlite.py:149`), so a committed write lands in
`<db>-wal` and can leave the main file byte-identical — 06-09 hit exactly this
and had to widen its own digest to cover `-wal`. The ArtifactStore assertion is
therefore weaker than it reads: it would not detect a write that had not yet
been checkpointed.

Not a live defect (no artifact-side write exists), but the observable is
weaker than its docstring claims. Owner: whichever plan next touches
`tests/invariants/test_mcp_role_separation.py`; the fix is the same
main-file-plus-WAL digest 06-09 uses.
