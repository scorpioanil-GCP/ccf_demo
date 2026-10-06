# D-IMPL-368 — the three-row PILOT: consolidated report

**Date:** 2026-10-05, ~18:25 MST. **Integration SHA:** `integration-remaining-rows` @ **`d289cac3`** (pushed),
base `main` @ `933ef91f` (= `1f6179c5` + the docs-only `D-IMPL-368` merge). **`main` is untouched by any
implementation.** No tag, no release, no SEC identifier closed; the ledger stays **13 of 29**.

## 1. Rows

| Row | Outcome | Rounds used | Row branch | Exploit test | Severings | Integrated |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-014 file modes | **INTEGRATED** | 2 of 2 (the corrective round changed only the test, to detect a leaked umask) | `row-sec-014` @ `a50152fb` | `tests/artifacts/test_file_store_modes.py`, 4 cases; **4 of 4 red** on the base (dirs `0o777`, pre-existing root `0o777`, staging files `0o666`) → 4 passed | 3 ruled (files, directories, root tightening) + 3 extra, all red; orchestrator's hand severings: both directory chmods → 2 of 4 red, fchmod → 1 of 4 red, restores sha-matched | `fdb7f789` |
| SEC-026 make credential echo | **INTEGRATED** | 2 of 2 (round 1 clean; the corrective round closed the close panel's lint bypass) | `row-sec-026` @ `579f8f04` | behavioral `tools/lints/tests/test_makefile_credential_echo.py` (**7 of 9 red** on the base: all six targets echoed the canary) + lint `makefile_credentials.py` (**9 findings red** on the base: lines 295, 306 via `PG_DSN_ENV`, 310, 314, 318, 339, 341, 367, 369) → 656 lint tests pass, lint rc=0 | 5 in round 1 + 4 in round 2, all red; orchestrator's hand severings: one `@` removed → 1 of 9 red; a directive skip re-introduced → 3 of 46 red; restores sha-matched | `0d0be21b`, then `d17c62c8` |
| SEC-024 error-input leakage | **PARKED** | 1 of 2 (the executor stopped on a design choice rather than spend the corrective round) | `row-sec-024` @ `5ae750c1` (**red test only**, 243 lines; 4 of 4 red on the base) | `tests/mcp/test_egress_logs_carry_no_caller_values.py` | severings (a)(b)(c) each reddened their case on the attempted repair | **no** |

**SEC-024's failing criterion, with the evidence.** The row assumed every door error reaches
`runtime/ccf_runtime/mcp/egress.py::_opaque_failure` and so the log. Measured: the parameters mismatch, the
`product_id` mismatch, `door_question` and `parse_product_address` raise **before** that block, FastMCP returns
their full text **to the client**, and the server log never sees them. Case 2 therefore cannot go green inside the
ruled change surface without changing the wire (which the row forbids). The attempted repair (3 of 4 green) is
saved uncommitted in the row's worktree and as `scratchpad/sec024/sec024-repair.patch`; two existing C-01 tests
in `tests/mcp/test_egress_parameters.py` assert the caller's values ARE in the client error text, so fix (iii) as
ruled conflicts with them directly. **Note on severity:** what reaches the client is the caller's **own**
parameters echoed back in a refusal; that is a wire-shape design question, not a disclosure to a third party.
**For Dave, three choices, none taken:** (A) capture only server-side loggers and let the C-01 wire text be the
keys-only refusal; (B) route the C-01, `door_question` and parse refusals through the opaque id, which changes the
wire; (C) scope SEC-024 to logs and `CCFContract` only, leaving the wire as the C-01 tests assert.

## 2. Panels

- **Pre-run panel** (`docs/D-IMPL-368-PRERUN-REVIEWS.md`): Codex (document-only; sandbox dead, stated), Cursor
  (four tree claims re-verified), Fable (two probes). **All three pilot rows were materially wrong as first
  written** and were rewritten before any executor saw them: SEC-014's severing named an API the store does not
  use and its directory check was vacuous; SEC-024's assertion was green on the unfixed tree and missed the
  door's own f-strings; SEC-026's line list was wrong in both directions and its lint a proxy make could defeat.
  Nothing rejected. **SEC-017 escalated** (below).
- **Close panel, after integration** (`docs/D-IMPL-368-CLOSE-REVIEWS.md`): ten findings. One **BLOCKING
  confirmed by measurement** (the lint exempted tab-prefixed make keywords; `make` echoes them) → SEC-026's
  corrective round, closed and re-verified. One **REJECTED by measurement** (whitespace before `@`; make honors
  it). Cursor's bracketed-umask test hole **confirmed by measurement** (all 4 green under that non-conforming
  shape; the shipped mechanism is correct) → carried. The rest carried by name.

## 3. Regression on the integrated tree (`d289cac3`), measured by the orchestrator

| Suite | Result |
| --- | --- |
| `tests/artifacts tests/mcp tests/contracts tests/replay tools/lints/tests tests/invariants` | **3307 passed, 2 failed, 1 skipped** |
| the 2 failures | both standing before the pilot: `tests/invariants/test_citation_coverage.py` (the ratchet at 365, ceiling 0) and `tests/contracts/test_canonical.py::test_the_child_resolves_the_same_ccf_this_test_is_running` (a worktree's child process resolves the main checkout's package; red on the SEC-024 executor's baseline too) |
| `python -m tools.lints --all` | rc=0 |
| `python -m mypy` | no issues in 243 files |
| `tests/examples` (no estate export) | **28 failed, 992 passed, 743 skipped, 74 xfailed — identical to the base**, same 28 ids |

**Disclosed:** the 743 skipped nodes are the estate-gated examples. No estate export (`CCF_CP_*` variables) exists
in the tree or on this host, and no prior gate has run them either (the v1.0.1 qualification skipped 660). The
"estate-gated examples run read-only at every wave close" commitment of `D-IMPL-356` is therefore **not met by
this pilot and has never been met**; it needs its own decision on how the export is assembled.

## 4. Behavior changes for Dave to confirm or reverse

1. **A pre-existing artifact-store root is tightened to `0o700`** on construction. A root owned by another user
   now fails with `PermissionError`. Q8's other reading is refuse-by-name. Made inside Q8's scope and flagged.
2. **`make leg-neo4j` and `make legs` require `CCF_TEST_NEO4J_URI` exported locally**; CI is unchanged.

## 5. Escalations (need a ruling before any further run)

- **SEC-017** (`D-IMPL-368` pre-run, Cursor): the three tools are already tenant-guarded
  (`runtime/ccf_runtime/mcp/tenancy.py::_select_tenant`, pinned by
  `tests/mcp/test_tenant_guard.py::test_the_three_agent_and_replay_tools_are_tenant_guarded`); Q10's premise is
  false. The open pin is **product entitlement within a tenant**, which `D-IMPL-129` ruled unbuildable. Rule:
  close SEC-017 on the existing tenant evidence, or redefine it to the product-entitlement gap.
- **SEC-024** wire-shape choice A/B/C (§1).
- **SEC-014 root reading** tighten vs refuse (§4).

## 6. Carried findings (named, not fixed)

- **SEC-014-C-01** the exploit test cannot detect a bracketed-umask non-conforming refactor (measured; fail if
  `os.umask` is called during construction or `put`). **C-02** `_make_private_dirs` leaves an intermediate another
  process created wide on `FileExistsError`. **C-03** the staging-file test samples the mode only at `replace`.
  **C-04** a symlinked root is followed and tightened (Fable measured). **C-05** (new row candidate)
  `src/ccf/graph/backends/sqlite.py::SqliteGraphStore.__init__` creates the live graph DB and WAL/SHM at the umask.
  **F-04** `src/ccf/products/product.py::open_product` creates the store root's parents wide.
- **SEC-026-C-01** one level of variable indirection only; a fixed target list in the behavioral test;
  `.github/workflows/ci.yml` carries `ccf_test_password` in plain text; the `tools/lints/__main__.py` docstring
  count is stale; the lint also refuses `$$NAME` shell-variable echoes (a small extension beyond the row).
- **SEC-024** `asked_at` messages still embed values; case 3 relies on FastMCP `_tool_manager` internals;
  worktree child processes import the main checkout's `ccf` (also the cause of the standing contracts red).
- **Process:** `python -c "import ccf"` from a worktree loads the main checkout; pytest is correct because
  `pyproject.toml` sets `pythonpath`. Executors were told to verify; both did.

## 7. What the model measured, honestly

- **Executor cost:** three Opus runs of roughly 141k, 163k and 175k tokens; the SEC-026 corrective round 178k
  more. Two reviewer panels of three seats each. One orchestrator session.
- **Where the rounds went:** of four executor rounds used, **three were spent on tests, not mechanism**: SEC-014's
  corrective round hardened its own test; SEC-026's corrective round closed a lint bypass the panel found; SEC-024
  stopped because the row's premise about the code path was wrong. That is the same pattern as the 2.5 weeks
  before, now bounded by the cap instead of open-ended.
- **What the exploit-test-first rule bought:** every integrated row has a red-before/green-after test whose named
  severings the orchestrator re-ran by hand, so "done" rested on a measurement at every step. The pre-run panel
  caught three vacuous tests before a line of fix was written; on the prior model those would have shipped and
  been reopened.
- **What it did not buy:** correctness of the rows' "Today" descriptions. Three of three pilot rows and three
  non-pilot rows had wrong current-state claims; the panel, not the executor, found them.

## 8. Recommendation on continuing

**Continue, under the same rules, in batches of three rows, with one change: every row's "Today" section is
re-measured by a reviewer before it is executed, as the pre-run panel did here.** The two integrated rows came
in at the cap with measured evidence at every step; the parked row stopped where the rules said to stop and
surfaced a real design question instead of guessing. The cost is bounded and visible per row. The next three
with no open ruling are SEC-015 (CI posture), SEC-028 (lock file) and SEC-021 case (a) (the bounded pending
buffer); SEC-017 and SEC-024 wait on §5. **No further run is authorized by this report.**
