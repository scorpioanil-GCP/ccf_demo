# D-IMPL-368 — the BATCH-CLOSE panel on the three-row pilot (after integration)

**Subject:** the integration branch `integration-remaining-rows` @ `fdb7f789` (base `f49228fd`), carrying
SEC-014 (`row-sec-014` @ `a50152fb`) and SEC-026 (`row-sec-026` @ `e722d758`); SEC-024 PARKED, not in the
diff. The full diff and both executor reports were inlined in one prompt (68,947 bytes).
**Reviewers:** Codex, Cursor, Fable (independent agent, read-only tree, probes in scratchpad). **Executor:**
Opus, excluded. **Date:** 2026-10-05. **Ordering:** integration first, panel after, per `D-IMPL-368`.
**Verifier:** the orchestrator re-measured every tree claim that carried a disposition; the column says how.

## Seat reliability

| Seat | Read the tree? | Counted? |
| --- | --- | --- |
| Codex | **No** (sandbox failed before inspection; stated) — reviewed the inlined diff only | Yes, as a diff reviewer; both of its code claims were re-measured |
| Cursor | Yes (symbols cited and resolved) | Yes |
| Fable | Yes, with measured probes (GNU make 4.3, pydantic, a symlinked root) | Yes |

## Findings, verification, disposition

| # | Seat(s) | Row | Finding | Verified how | Disposition |
| --- | --- | --- | --- | --- | --- |
| C1 | Codex 2, Fable F-01 | SEC-026 | `tools/lints/makefile_credentials.py::check_source` skips tab-prefixed lines whose first word is a make keyword (`_DIRECTIVE`); make echoes those as recipe lines, so `\tifdef $(DSN)` or `\texport DSN=$(DSN); cmd` leaks and the lint accepts it | **MEASURED** by the orchestrator: `make t2 SHELL=/bin/true DSN=CANARY` printed `ifdef CANARY`; `check_source` reported nothing for that line; the real Makefile has zero such lines | **CONFIRMED, BLOCKING.** The shipped Makefile is clean (the exploit is not reopened); the static guard is. **SEC-026 reopened for its one corrective round** (see §Reopen) |
| C2 | Codex 1 | SEC-026 | `_silenced` accepts whitespace before `@` (`\t @cmd`), which make would still echo | **MEASURED**: make did **not** echo `\t @echo cmd X=$(DSN)` — make strips the whitespace and honors the `@` | **REJECTED.** The lint matches make's behavior |
| C3 | Cursor | SEC-014 | A **bracketed** umask (`old=umask(0o077) … umask(old)`) with every `chmod`/`fchmod` removed except the root tightening leaves all four cases green; the corrective round's leak check catches only a leaked umask | **MEASURED** on `row-sec-014`: that exact severing → `4 passed`; the same severing with the root chmod also removed → `1 failed` | **CONFIRMED, ADVISORY, CARRIED.** The shipped mechanism uses explicit `chmod`/`fchmod` (inspected), so the protection is present; the test cannot distinguish a non-conforming umask-bracketed refactor. SEC-014 has used its corrective round. Carried as **SEC-014-C-01**: fail if `os.umask` is called during construction or `put` |
| C4 | Cursor | SEC-014 | `_make_private_dirs`: on `FileExistsError` for an intermediate, `continue` leaves a directory another process created wide | INSPECTED (`except FileExistsError: continue`, then no chmod) | **ADVISORY, CARRIED** as **SEC-014-C-02**: verify mode and ownership on `FileExistsError`, refuse if wider |
| C5 | Cursor | SEC-014 | `test_the_staging_file_is_never_wider_than_its_target` samples mode only at `Path.replace`; a `write_bytes`-then-`chmod` refactor could be briefly `0o666` and stay green | INSPECTED | **ADVISORY, CARRIED** as **SEC-014-C-03** (the shipped `_write_private` does `fchmod` before the first write) |
| C6 | Codex 3, Fable F-04 | SEC-014 | A symlinked root is followed: `is_dir()` and `chmod` resolve the link, so construction tightens and writes into the target | Fable **measured** (victim `0o755 → 0o700`); orchestrator inspected `root.is_dir()` | **ADVISORY, CARRIED** as **SEC-014-C-04**: refuse `root.is_symlink()` by name; `fchmod` via an `O_DIRECTORY|O_NOFOLLOW` descriptor |
| C7 | Fable F-05 | same class | `src/ccf/graph/backends/sqlite.py::SqliteGraphStore.__init__` creates the live graph DB (and WAL/SHM) at the umask via `sqlite3.connect` — the last same-class writer in `src`+`runtime` besides `open_product` | Fable whole-tree grep | **CARRIED** as **SEC-014-C-05** (a new row candidate, not SEC-014's) |
| C8 | Fable F-02/F-03, Cursor | SEC-026 | `$(info)`, `$(warning)`, `$(error …$(VAR))` print regardless of `@`; `$(value NAME)` and `$(shell printenv NAME)` are unseen expansions; rule (iii) misses `X_PASSWORD ?= literal` and `://token@host` | Fable measured `$(info)`; the rest inspected | **ADVISORY.** Offered to the corrective round as optional, same bypass class; whatever does not land is carried as **SEC-026-C-01** |
| C9 | Cursor, Fable F-06 | SEC-026 | Fixed target list in the behavioral test; `make legs` refuses only after the Postgres leg; `__main__` docstring says "Two" whole-tree checkers | INSPECTED | **ADVISORY, CARRIED** (already named by the executor) |
| C10 | all three | both | No executor-report claim contradicted by the diff, except SEC-026's docstring sentence that make treats tab-prefixed keywords as directives (= C1) | — | Fixed with C1 |

## Behavior changes the integration carries (named, for Dave)

- A pre-existing artifact-store root is **tightened** to `0o700`; a root owned by another user now fails at
  construction with `PermissionError`. Q8's alternative reading is refuse-by-name. **Dave's call.**
- `make leg-neo4j` and `make legs` now require `CCF_TEST_NEO4J_URI` exported locally; CI is unchanged
  (`ci.yml` sets it in the job `env`).

## Reopen — SEC-026 corrective round

(filled after re-verification)
