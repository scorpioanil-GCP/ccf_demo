# Release qualification evidence — CCF SDK v1.0.1, candidate `a4cf2fb7`

**Tag `v1.0.1`** (annotated object `a0ce96e1faa9a19d47c284995561b1e0bc1c70c7`) points at
`a4cf2fb74af4964dcfee29d210d17d94b909d78d`, whose tree is `b345b174aa5dbfd28abaa3fa20cae97806659629`.
`v1.0.0` (`2fe19d1b` → `ff470d40`) is untouched and remains on the pre-D-IMPL-353 line. This
directory was committed after the tag; it is not part of the v1.0.1 release tree.

## Provenance chain

1. `1f081151` — `main` after D-GATE-353 (the capability seam). Qualified 2026-09-25 and ruled
   **RELEASE HOLD**: `s1_01` failed on a fresh empty Fluree with `KeyError: 'events'` (gap-ledger
   `SEC353-G-07`, reached once a live Fluree carried the six adoption nodes past the environment
   stop that had put them in R10), and the committed public-surface manifest was nine D-IMPL-353
   entries behind the live surface. Evidence: `hold-1f081151/`.
2. `f23f0a03` — the narrow repair Dave accepted (Option B for `s1_01` only): tenant-qualified key
   access through `namespaced_key` with no bare-key fallback, the evidence store's `WriteKinds`
   declaration, `max_ttl_key` under the deployment's own tenant, the regenerated surface manifest,
   the regenerated retirement-couplings report, and the gap-ledger sentence making `s1_01` the 1.0
   reference-path exception to the frozen-example posture.
3. `a4cf2fb7` — `f23f0a03` merged `--no-ff` into `main` (merge tree equals the candidate tree).
   Qualified 2026-09-25 in a fresh detached worktree and ruled **RELEASE GO**; tagged `v1.0.1`.

## Board at `a4cf2fb7` (all from the fresh worktree; tree hash verified equal to the freeze hash before and after every phase)

| check | result |
| --- | --- |
| focused D-IMPL-353 suites (authz, http_api, mcp, skills, controlplane, deployment, products, workflow, artifacts, crossproc, gates, lints, replay, invariants, surface gates) | 5818 passed, 1 skipped (Fluree pin, green in the leg), 0 failed |
| D-IMPL-353 severings | 33 of 33 observed RED on their named controls and restored byte-for-byte; tree re-hashed equal to the freeze hash after each; M29 withdrawn, not run |
| canonical `make test` (Makefile target as written; D-GATE-353 census posture: no `CCF_TEST_*`, no `CCF_CP_*`) | 9128 passed, **25 failed = the exact R10 census by node id**, 0 errors, 857 skipped, 74 xfailed, 0 xpassed, 225 deselected; 13:01 |
| typecheck / lint | 241 files clean / rc=0 (D-IMPL-353 authorization invariant included) |
| public-surface `--check` (twice) · assembler `--check` · surface gates | exit 0 · exit 0 · 51 passed |
| schema regeneration/drift · docs-strict | no drift · rc=0 |
| schema headers | red only on the two `archive/` scope-mapping documents (05, 06) — D-IMPL-351 subjects, the same two R10 nodes |
| product-gate inventory | 30 trees / 519 declared / 519 executing |
| tools suites (lints 579 · publish-scan 53 · docs 296 · product-gates 48) | all passed |
| Decision Replay 1.0 surface | replay suite 201 passed; DR-01 4 passed; DR-02 9 passed standalone and 17 passed after the predecessor import case (estate read-only) |
| Fluree leg (fresh, EMPTY — ledger list `[]` before seeding) | 293 passed / 0 failed / 0 errors; `s1_01` 6 of 6 adoption nodes passed; the output module incl. the tenant-key control passed |
| Mongo leg · Neo4j leg (authenticated readiness) | 38 passed · 29 passed |
| Postgres leg (testcontainer path) | 224 passed, **12 failed = the exact R10 node ids** (s1-00 ×9, cp-00 ×2, cp-01 ×1) |
| CP-03 live prerequisite (curated Postgres, count queries) | EXECUTED — PASS |
| estate provenance | `ccf:main @ t=1608`, `fibo-v2 @ t=5878`, 30 ledgers; zero movement across the whole qualification (`t=1608` includes the 2026-09-22 incident's transactions, disclosed at v1.0.0) |
| containers | every disposable instance destroyed; no reaper or qualification container remained |

## Carried residuals

R1 composition key grammar; R2 in-process issuance-table introspection (outside the threat model);
R3 lint scope excludes `examples/` and `tools/`; R4 FastMCP unknown-argument behavior; R5
producer-unavailable wording; R7 vestigial `approval_sink`; R8 duplicate helper spelling; R9 cp-20
direct register call (not served-reachable); R10 the exact 25-node D-GATE-353 census in the census
posture; the two archive schema-header documents under D-IMPL-351; the Postgres leg's 12 failures,
acceptable only as exact R10 node ids; gap-ledger `SEC353-G-01`–`SEC353-G-08` OPEN except the
repaired `s1_01` path.

## Outside this release contract

Three-audience Π projection; retention-tier orchestration; temporal-boundary indexing; automated
sabotage-attestation instrumentation; `/v1/fluree/ledgers` route migration; SEC-005; SEC-006;
D-IMPL-348; M29 withdrawn.

## Not executed

**660 estate-gated example nodes were not executed in the canonical census-posture `make test`
run.** They did not pass; they were not run. The curated estate was read only by the CP-03 live
node and by DR-02's cp-06C upstream; its Mongo was not used at all.

## Inside `evidence.tar.gz`

`FREEZE.txt`; `canonical.log` / `canonical.xml` (junit, 10 084 testcases) / `canonical.posture` /
`canonical.tree-before` / `canonical.tree-after` / `canonical.seconds`; `reconciliation.txt` and
`canonical-nonpass-nodes.txt` (every non-pass by node id and category); `R10-census-node-ids.txt`;
`severings.log`, `severings-table.md` and `severings/M*.log`; `static/*.log` (every check above);
`legs/*` (per-leg logs, readiness proofs, the Fluree ledger list before and after, container sets
before and after); `cp03-live.log` (credentials redacted); `estate-before.*` / `estate-after.*`;
`typecheck.log`, `lint.log`, `focused.log` / `focused.xml`; the runner scripts. No environment
script and no credential is included.
