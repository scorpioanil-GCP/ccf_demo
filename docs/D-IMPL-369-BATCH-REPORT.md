# D-IMPL-369 — batch 2: consolidated report

**Date:** 2026-10-05, ~23:05 MST. **Integration SHA:** `integration-remaining-rows` @ **`adc406db`** (pushed).
**`main` @ `933ef91f` untouched** (`D-IMPL-369` itself is recorded on the integration branch, not on `main`).
No tag, no release, no SEC identifier closed; the ledger stays **13 of 29**. The pilot report
(`docs/D-IMPL-368-PILOT-REPORT.md`) and this one are cumulative.

## 1. Rows

| Row | Outcome | Rounds | Branch | Exploit evidence | Severings | Integrated at |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-014 delta (refuse an insecure pre-existing root by name, no chmod) | **INTEGRATED** | authorized post-cap delta + 1 routine correction (the golden fixture) | `row-sec-014` @ `5383c91e` | 2 of 6 red on the tighten code; 6 green; a 0o777 root refused and still 0o777 (orchestrator probe) | (c) drop the refusal, (d) chmod instead of refuse, both red; orchestrator's chmod-before-raise → 1 of 6 red | `886fefab` |
| SEC-021 (bounded receive queues) | **INTEGRATED** | 2 of 2 (corrective round: surface-shape and drift tests) | `row-sec-021` @ `56b49756` | 6 of 6 red on the base; 6 green | a1 drop cap, a2 evict-oldest, a3 append-then-check, c1 carriage-id-after-append, all red; orchestrator's evict severing → 1 of 6 red | `52364813` |
| SEC-015 (CI permissions + SHA pins) | **INTEGRATED** | 2 of 2 (corrective round: job-level string permissions) | `row-sec-015-028` @ `0ac58e62` | 11 red / 20 lint findings on the base; green; all 3 pins equal `ls-remote` of the tags (orchestrator and Fable) | 5 + 1, all red; orchestrator's `@v4` → 2 red, `read-all` re-allowed → 1 red | `9b71843b`, `77a1ae47` |
| SEC-028 (hash-pinned lock incl. build set) | **INTEGRATED** | 2 of 2 (corrective round: installer spellings, operand) | same | 11 red / 13 lint findings on the base; green; 139 lock entries, 0 unhashed (orchestrator); install from lock into a throwaway venv executed | 6 + 3, all red; orchestrator's `--require-hashes` removed → 2 red | same |
| SEC-017 (verification only, by ruling) | **CONFLICT REPORTED, no closure** | — | `verify-sec-017` (nothing committed) | tenant guard real: severing `_select_tenant` reddened the existing test; the `D-IMPL-129` pin stayed green under that severing (it measures within-tenant product entitlement) | — | — |
| SEC-024 | **QUEUED** outside this batch (choice C ruled) | — | `row-sec-024` @ `5ae750c1` (red test only) | — | — | — |

**SEC-017, the conflict as measured (`scratchpad/report-sec-017.md`, 23 KB):** the finding's *issue* sentence
("authenticated but not tenant-entitled; `tenant` is a client argument") is satisfied today by
`runtime/ccf_runtime/mcp/tenancy.py::_select_tenant`. The *remedy* sentence ("Entitle these three tools (known
gap D-IMPL-129 …)") binds the row to `D-IMPL-129`, whose deciding sentences define the gap as within-tenant
entitlement and name the pin whose inversion is the signature of the fix; that pin has not inverted. The
machinery `D-IMPL-129` said was missing has since been built (`D-IMPL-353`'s scope-mapping authorizer already
decides these tools under `agent.list` / `replay.read` / `workflow.invoke`), but no test exercises a
principal-narrowed mapping for them, `invoke_agent` has no action id of its own, and the pin cannot measure
that path. **Which artifact "entitled" means for these three is a ruling, not a measurement.**

## 2. Panels

- **Pre-implementation measurement** (Fable, `scratchpad/measure-015-028-021.md`): all three "Today" sections
  were wrong in material ways before execution and were rewritten (16 action refs across three actions, not
  two; ten unhashed installs and the one `pip-compile` invocation that actually locks the build set; both
  peering legs already size-check before parse, so SEC-021's case (b) was vacuous and dropped; the typed leg's
  ceiling is `max_request_bytes`; the a2a library parses the body before CCF's accept). The orchestrator
  re-verified each claim before applying it.
- **Close panel after integration** (`docs/D-IMPL-369-CLOSE-REVIEWS.md`): Codex, Cursor, Fable; **no blocking
  finding from any seat**. Two lint-grammar holes (B1, B2) were **confirmed by the orchestrator's probes** and,
  for consistency with the pilot's standard, spent the two rows' unused corrective rounds; both re-verified
  and re-integrated. Eleven advisories carried by name. Fable executed the off-runner checks a hosted runner
  would hit (every lock hash is a real, un-yanked PyPI file; every package has a cp312 x86_64 wheel; no job
  needs a write grant; 32 of 32 declared requirements satisfied by the lock).

## 3. Regression on the integrated tree, measured by the orchestrator

| Suite | Result |
| --- | --- |
| artifacts, mcp, contracts, replay, peering, crossproc, surface drift/shape, deployment, lints tests, invariants (`9b71843b`) | **4024 passed, 2 failed, 1 skipped** |
| lints tests + deployment + surface drift (`adc406db`, after the corrective round) | **1132 passed** |
| the 2 failures | the same two standing reds as the pilot (citation ratchet at 365; the worktree child-process test) |
| `python -m tools.lints --all` | rc=0 (now ten checkers, three of them new this day) |
| `python -m mypy` | no issues in 243 files |
| `tools/docs_tests` | 319 passed, **1 failed** — `test_retirement_sweep::test_the_committed_report_is_current`, **red on the base `5f1dbfd6` before any batch-2 code** (measured) |
| `tests/examples` (no estate export) | **28 failed, 992 passed, 743 skipped — identical to the base**, same ids |
| extra suites Fable ran (client, cli, hitl, conformance) | 1157 passed, 0 errors |

**Disclosed, unchanged from the pilot:** the 743 estate-gated example nodes are skipped; no estate export
exists; the `D-IMPL-356` wave-close commitment has never been met. The pinned workflows have not been run on
GitHub; a `main` merge is the first thing that would show their hosted-runner behavior.

## 4. Behavior changes for Dave to confirm

1. An insecure pre-existing artifact-store root is **refused by name** (`InsecureArtifactStoreRoot`, a
   `PermissionError`), mode untouched. Two example servers (cp-06, cp-07 `serve.py`) pre-create their root
   and already fail on a missing `write_kinds` argument; under `D-IMPL-261` they stay carried.
2. Both peering transports **require `max_pending`** (no default). All nine constructor sites in
   `src`/`runtime`/`tests`/`perf` pass it; the frozen archive example-04 pair does not and now raises
   `TypeError` (frozen by `D-IMPL-351`; the perf crossproc suite that spawns it was already erroring at setup
   on the base, and `perf.yml` is manual-dispatch only).
3. Every CI and Makefile install runs **from the hash-pinned lock**; `pip-tools` is a `dev` extra; `pip`,
   `setuptools` and `wheel` in the shared venv moved when pip-tools was installed.
4. `make leg-neo4j` / `make legs` need `CCF_TEST_NEO4J_URI` exported locally (pilot).

## 5. Escalations (rulings needed before the relevant row continues)

- **SEC-017:** what "entitled" means for the three tools: close on the tenant evidence and carry within-tenant
  entitlement under `D-IMPL-129`; or redefine the pin's inversion to the scope-mapping authorizer (and add an
  `agent.invoke` action id); or something else. No closure was made.
- **SEC-021 adjacent (LF leg):** a2a-sdk's `JsonRpcDispatcher.handle_requests` parses an unbounded body before
  CCF's `_accept`; bounding it needs an ASGI body limit in front of the dispatcher, a design addition.
- **SEC-028 adjacent:** nothing checks the lock still matches `pyproject.toml` after a pin bump.
- **New row candidates surfaced by the panels:** `SqliteGraphStore.__init__` creates the live DB at the umask;
  CI service images (`postgres:16`, `neo4j:5-community`, `mongo:7`, fluree) are mutable tags; concurrent
  in-flight request bodies are not bounded process-wide.

## 6. Carried findings (named, not fixed)

- **SEC-014-C-01…C-06** (pilot C-01…C-05 plus the unpicklable refusal class), **F-04** `open_product` parents.
- **SEC-021-C-01** `TypedHttpWire.emit` drops the 503 body so SDK senders see a generic `PeerUnreachable`;
  **C-02** the test reads the private queue; **C-03** LF-leg full-queue rendering (JSON-RPC `InternalError`
  with tracebacks) and the typed 503 reflecting the peer-id header; the base64url decoder drops invalid
  characters silently.
- **SEC-015-C-01** the lint accepts any SHA with a `# vN` comment without checking it equals the tag (verified
  once by hand this batch; Dependabot moves them by PR).
- **SEC-028-C-01** README leads with the unlocked install; **C-02** the installer deny-list is a fixed set and
  installs hidden in `$(…)`/`bash -c` are unseen; `ccf.egg-info` stamped 0.0.0 left at the root by
  `pip-compile` (gitignored; README warns).
- **SEC-026-C-01**, **SEC-024** carries, `ccf_test_password` in `ci.yml`: unchanged from the pilot.

## 7. Where the rounds went, honestly

Seven executor rounds were used across four rows. **Four of the seven were spent on tests and lint grammar**,
not on the mechanism: SEC-021's corrective round on surface-shape tests; SEC-015's and SEC-028's on lint
grammar holes the close panel found; SEC-014's routine correction on a test fixture. The mechanism was right
first time in every row. That is the same pattern as the pilot and the 2.5 weeks before it, bounded by the
cap. The pre-implementation measurement prevented at least three vacuous or mis-aimed tests from being written.

## 8. Recommendation

Continue under the same rules. The three open rulings in §5 should be made before the rows they gate. The
remaining mechanical rows with no open ruling are **SEC-013** (single-writer lease), **SEC-020** (withheld
indistinguishable from nonexistent), **SEC-022** (A2A replay), **SEC-023** (classification authority),
**SEC-025** (composite child subject echo) and **SEC-024** under choice C; the five lows and the two example
lows per Q2/Q3. Three rows per batch has been the right size: parallel executors, one close panel, one
report. **No further run is authorized by this report.**
