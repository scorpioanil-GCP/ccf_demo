# D-IMPL-377 — close-out of D-IMPL-376 (2026-10-07)

**Status.** Draft for the coordinator. No repository file or branch was changed to write it. Sources:
- the coordinator's ledger, through its entry "FINAL CANDIDATE = 421947b8 (all lanes + follow-ups merged)". The ledger is authoritative where sources disagree;
- the baseline list compiled at `main` @ `d9305603` (sections A–F);
- `docs/DECISIONS.md` at `d9305603` (D-IMPL-375, D-IMPL-376);
- the candidate branch `dl-377-integ` @ `421947b8`, the ledger's final candidate. It is neither merged to `main` nor tagged.

Every check has completed; the final results are in §3 (the regression table) and §9, item 1.

**Conventions.**
- `R/` stands for `records/2026-10-07-d-impl-376-execution/`. Evidence is cited by its path under it; §10 gives the full paths.
- "SP §x.y" is `public/how-to/security-and-deployment.md` on the candidate @ `421947b8`, cited by the page's own section number. §5 opens with the section headings.
- Code is cited as `path.py::Symbol`, never by line number.
- "Coordinator" is the session that re-ran each red, green and severing on the joined tree. "Lane" is the agent that built the change.
- UNVERIFIED means that neither the ledger, nor the baseline, nor a cited file settles the point.

## 1. Summary

Dave's GO (D-IMPL-376) was executed on 2026-10-07. Step 1 merged `deadline-rows` into `main` as `d9305603`, ran the ordered checks on the merge commit, and pushed at 12:30 MST with no tag (§2). Eight lanes and four follow-up lanes then ran from that frozen baseline and were integrated onto `dl-377-integ`. The final candidate is `421947b8`.

Three reviews ran on the joined tree:
- an independent review of `feb12052`, which found 2 Critical, 2 Important and 7 Minor findings;
- a focused re-review of `c2c341e2`, which found one more Important finding, a forged record. Dave ordered it fixed;
- a final short review of `421947b8`, which found no Critical or Important finding (ledger, 16:09).

Every item below closed on Dave's three checks. The coordinator re-ran every red and green on the joined tree. It also ran every severing there, except the M-4 and M-1 severings, which ran in their lanes only.

- panel C8;
- review C-2 (a cross-tenant record read, present since v1.0.1) and review M-4;
- the forged-record read found by the re-review (present since D-IMPL-345);
- EX-01;
- EX-09, at 16 of 16 sites;
- a deadline-rows Fluree test regression;
- the estate write fence, plus a follow-up for libpq's environment and an empty host declaration;
- the in-process double pass at an approval gate. Its remaining limits are disclosed on SP §4.13;
- the code half of SEC-027, including a placeholder that no Python 3 installer can select.

No ledger row closes. SEC-020 stays OPEN by Dave's 14:27 MST ruling, SEC-027's row waits for Dave's upload of the new placeholder files, and SEC-029 waits for a tag. The close-out's own findings exceeded the three-issue cap (CLAUDE.md §9), so the documentation and diagnostic items go to one follow-up batch (Dave, 14:27 MST, ruling 4). Merging the candidate is Dave's decision (§9).

| Row | `main` @ `d9305603` | Candidate @ `421947b8` | What changes it next |
|---|---|---|---|
| SEC-020 | OPEN | OPEN. Dave 14:27, ruling 2: keep the fix, the row stays open | Route A's one round is in the candidate. A subject-keyed acquisition now matches a nonexistent subject, while a population-shaped acquisition now leaks, which is the reverse of `main`. Six more channels remain (§4a). Exactness needs a new design (§9) |
| SEC-027 | OPEN | OPEN. The code closed on the three checks (§3h) | Dave uploads the **new** placeholder files only: wheel sha256 `0e6e1b9e…`, sdist sha256 `e24eb5d2…` (`R/lanes/pypi/DAVE-PYPI-STEPS.md`). The earlier `e68dda4f…`/`8d566c80…` files must not be uploaded |
| SEC-029 | OPEN | OPEN | A release tag, after the release checks (D-IMPL-376 (4)) |
| **Count** | **26 of 29** (D-IMPL-376 (2); baseline §A) | **26 of 29** | 27 of 29 if the upload closes SEC-027; 28 of 29 if a tag closes SEC-029 |

## 2. The merge and its checks (step 1)

| Check | Result | Evidence |
|---|---|---|
| Merge | `deadline-rows` @ `1229962f` merged into `main` with `--no-ff` as `d9305603`; parents `e561e01f` and `1229962f` | ledger "Step 1 MERGE" |
| Tree equality | The tree of `d9305603` is `69ac033e`, the same as the tree of `1229962f` (re-measured for this document) | ledger |
| Specimen pins | 2 passed, rc 0; imports resolved inside the merge worktree. The pins are `tests/examples/test_cp_04_canonical_output.py::test_the_specimen_is_untouched` and `tests/examples/test_door_cp_05_exposure.py::test_the_wrapper_is_a_binding_adapter_over_the_standard_door_and_the_specimen_is_untouched`. The merge file records only the count; the ids are the ones listed in `R/lanes/ex0109/specimen-pins-5ee6af4.txt` | `R/merge/pins-d9305603.txt` |
| Chunk 1: 17 directories, from `tests/graph` to `tests/erasure` | 5055 passed, 27 skipped, 0 failed, 0 errors (236 s) | `R/merge/chunk1-d9305603.txt` |
| Chunk 2: `tests/conformance` onward, plus every top-level `tests/*.py` | 4105 passed, 88 skipped, 2 failed. Both failures are allowed standing reds:<br>• `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow`: 365 entries, 362 unique, the same set as `main`'s 362<br>• `tests/test_version_stamp.py::test_the_installed_version_is_not_the_stale_literal_and_is_git_derived`: environmental | `R/merge/chunk2-d9305603.txt`, `R/merge/ratchet-d9305603.txt`, `R/base/ratchet-main.txt` |
| Chunk 3: `tests/examples`, `tests/perf_*` | 1028 passed, 743 skipped, 74 xfailed, 30 failed, 0 errors. The 30 failed ids equal `main`'s 30 standing ids exactly: 29 example ids plus `tests/perf_smoke/test_smoke.py::test_suite_runs_untimed[micro]` | `R/merge/chunk3-d9305603.txt`, `R/merge/chunk3-ids-d9305603.txt`, `R/base/main-chunkD-ids.txt` |
| Gates | All rc 0:<br>• lint<br>• mypy, 258 files clean<br>• product gates, 519 of 519 over 30 trees<br>• docs: pre-build scan, schema scan, `mkdocs build --strict`, site scan<br>Gate tests, all passed: lints 836; publish + docs 373; product gates 48; version stamp 15; estate census 130 | `R/merge/gates-d9305603-groupA.summary`, `R/merge/gates-d9305603-groupB.summary`, `R/merge/gate-d9305603-*.txt` |
| Regeneration | `make surface`, `tools/assemble_surface_changes.py`, `tools/retirement_sweep.py --report` and `make schemas`: rc 0 and porcelain 0, so the generated files were current | `R/merge/regen-surface.txt`, `regen-assemble.txt`, `regen-retire.txt`, `regen-schemas.txt` |
| Push | `origin/main` moved `e561e01f..d9305603` at 12:30 MST. **No tag.** | `R/merge/push-main.txt` |

**Caveat: the specimen pins guard less than their names say.**
- **cp-04 and cp-05 pass by construction on `main`.** Both pins diff their specimen against `git merge-base HEAD main`. On `main` that merge base is HEAD itself, so the pins compare `d9305603` with itself (ledger, "NOTE for Dave"; measured in both test functions). D-IMPL-376 (1) asked for the pins to "demonstrably pass there". They did, but that shows only that the merge commit is green.
- **cp-03, cp-06 and cp-13 never reach their assertion.** Their pins are `test_the_specimen_is_untouched_and_no_identity_is_reused` in `tests/examples/test_cp_03_canonical_output.py`, `test_cp_06_canonical_output.py` and `test_cp_13_canonical_output.py`. Offline they skip, because all three are estate-gated (`R/lanes/estate/audit/READ-ONLY-ids-d9305603.txt`; the cp-03 and cp-13 pins are shown skipping in `R/lanes/ex0109/specimen-pins-5ee6af4.txt`). Against the estate they error at setup in family A (temporal boundary undeclared), on `d9305603` and on the candidate alike. Those three specimen guards are inert (ledger, "FINDING"; `R/lanes/estate/ESTATE-RESULTS-by-id-d9305603.tsv`).
- **The specimens did change.** The merge changed files in all five pinned frozen specimens, under D-IMPL-375 executor ruling (b) (ledger, "MEASURED"; re-measured for this document with `git diff --name-only e561e01f d9305603`):

  | Pinned frozen specimen | Files the merge changed |
  |---|---|
  | `examples/cp-03-obligor-financial-spread` | `ccf_config.yaml` |
  | `examples/cp-04-corporate-family-tree` | `README.md`, `ccf_config.yaml` |
  | `examples/cp-05-credit-exposure-rollup` | `README.md`, `ccf_config.yaml`, `produce.py` |
  | `examples/cp-06-collateral-and-setoff-coverage` | `ccf_config.yaml`, `produce.py` |
  | `examples/cp-13-covenant-cross-reference` | `ccf_config.yaml`, `produce.py` |

  The merge also changed the `ccf_config.yaml` of cp-00, cp-01 and cp-02, and five `s1-01` files. In all it changed 72 files in 33 example trees (measured).

**Caveat: environment.** The merge chunks ran under a shell that exported `.76` connection variables (the "ENV HAZARD", ledger 13:10). A later regression at `34a1f6bf` ran with those variables scrubbed and matched the unscrubbed baseline by test id, so no test depends on them (ledger "COMBINED REGRESSION").

## 3. Closed in this close-out

Each item closed on Dave's three checks:
1. A red test, re-run by the coordinator at its red commit. For the Fluree regression, it was re-run on the joined tree.
2. The same test green after the merge onto `dl-377-integ`, run by the coordinator.
3. One executed severing, with the file restored from saved bytes and its hash compared. The coordinator ran every severing on the joined tree except two that ran only in their lanes: M-4's (§3c) and M-1's (§3h).

Integration order on `dl-377-integ`:

| Merge | What |
|---|---|
| `705fe210` | C8 |
| `2c830372`, `2de65c7b` | EX-01 and EX-09, then the cp-13 site |
| `34a1f6bf` | SEC-027 rename |
| `497c6f6d` | Fluree test fix |
| `cf86fa5d` | SEC-020, provisional |
| `feb12052` | Coordinator docs |
| `1ccc6243` | SEC-027 round 2 |
| `2b919375` | Fence |
| `8ef9e207` | C-2 and M-4 |
| `c2c341e2` | Race |
| `491f0f29` | SEC-020 docs pass. Merged clean; regenerating the generated files changed nothing |
| `2dc17656` | The SP §4 introduction now names SP §4.12 and SP §4.13. Docs pre-build, mkdocs, site scan, lint and the docs tests (320) are green |
| `4387a43d` | SEC-027 round 3: the placeholder declares `requires-python = "<3"` |
| `c4893f90` | Race docs: three measured limits of the claim, on SP §4.13 |
| `06b80efe` | Forged-record fix |
| `421947b8` | Fence follow-up (fence2). This is the ledger's final candidate |

**Combined regressions on the candidate**, compared with the merge commit by test id:

| Tree | Chunk 1 | Chunk 2 | Chunk 3 | Evidence |
|---|---|---|---|---|
| `34a1f6bf`: C8, EX, SEC-027; `.76` variables scrubbed | 5059 passed, 0 failed (5055 + C8's 4) | 4111 passed, plus the 2 allowed reds. The ratchet's unique set is identical (362), and the version-stamp red now gives `PackageNotFoundError` as its reason | 1133 passed, 74 xfailed, and exactly `main`'s 30 failing ids (1028 + 105 EX) | `R/integ/reg-34a1f6bf/` |
| `feb12052`: adds SEC-020, the Fluree fix and docs | 5079 passed, 0 failed | 4111 passed, plus the 2 allowed reds; ratchet set identical | 30 failed (`main`'s ids), 1133 passed, 743 skipped, 74 xfailed | `R/integ/reg-final/*-feb12052.*` |
| `2b919375` | 5079 passed, 0 failed | — | — | `R/integ/reg-final/chunk1-2b919375.txt` |
| `c2c341e2` | 5088 passed, 0 failed | — | — | `R/integ/reg-c2c341e2/chunk1-c2c341e2.txt` |
| `2dc17656` | 5088 passed, 0 failed, 2 xfailed (the C-1 strict xfail) | 4119 passed, plus the 2 allowed reds; ratchet unique set identical (362; measured) | 30 failed, exactly `main`'s 30 ids (measured), 1234 passed, 743 skipped, 74 xfailed | `R/integ/reg-2dc17656/` |
| `421947b8`, the final candidate | 5094 passed, 0 failed, 3 xfailed (the two C-1 xfails and the same-tenant MCP forgery) | 4120 passed, plus the 2 allowed reds; ratchet unique set identical | 30 failed, exactly `main`'s 30 ids, 1260 passed, 743 skipped, 74 xfailed. Gates: lint clean; mypy 258 files; product gates 519/519 over 30 trees; docs pre-build, schema scan, `mkdocs build --strict` and site scan clean; tools suites 836 / 373 / 48 / 15 / 130 passed; regenerating every generated file leaves the tree unchanged | `R/integ/reg-421947b8/` |

### 3a. C8: another tenant's identical bytes changed the owner's reads

- **Hole.** On the MCP artifact server, a governed (`ReplayMint`) filing of identical bytes by another tenant had two effects on the owner tenant:
  - its names and blob reads answered `subject-unavailable`;
  - its erasure door over the MCP-backed store refused `class-unverifiable`.

  D-IMPL-376 (6) called this "likely also a cross-tenant existence oracle" and did not accept disclosure alone (baseline §C.7).
- **Red.** `3709b731` (lane-377-c8). The coordinator re-ran it at `3709b731`, where `src/` and `runtime/` equal the base: 4 failed in `tests/mcp/test_c8_governed_judged_per_tenant.py`. Evidence: `R/integ/c8-red-at-3709b731.txt`; lane copy `R/lanes/c8/red-3709b731.txt`.
- **Fix.** `0d1a5de5`. `runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server` now judges "governed" over the caller's own tenant's names, at both sites that read the naming index: the blob/presence split and the names resource. The lane finished at 12:49 MST, inside the 15:00 timebox, and the fix was merged as `705fe210`.
- **Green on the joined tree.** 4 passed (`R/integ/c8-green-integ.txt`).
- **Severing, by the coordinator.** The dereference site was made to judge over every tenant's names (`own` → `names`): 3 failed, 1 passed. The hash matched (`a9e1a62cc3c2`) and porcelain was 0. Evidence: `R/integ/c8-sever-integ.txt`, `R/integ/c8-sever-old.txt`, `R/integ/c8-sever-new.txt`.
- **Residuals.**
  1. Prose had listed "the MCP client lane" as a tenantless read. The lane was measured tenant-scoped before and after the fix (`R/lanes/c8/probe-client-lane-scoping-d9305603.txt`, `R/lanes/c8/probe-client-lane-scoping-0d1a5de5.txt`). The prose was corrected at `feb12052`, in SP §4.10 and in the `src/ccf/erasure/__init__.py` module docstring.
  2. The fix assumes a name is filed only together with its bytes. That obligation is stated on SP §4.10. It is not stated on `runtime/ccf_runtime/mcp/artifact_server.py::ArtifactSubstrate` or `src/ccf/artifacts/protocol.py::ArtifactStoreProtocol` (measured at `421947b8`).
  3. Behavior change: the names resource no longer records a refusal for an address that only another tenant filed as governed.
  4. Untested: completing an erasure end to end over `src/ccf/artifacts/mcp_store.py::McpArtifactStore`. No test in the tree does this.

### 3b. C-2: another tenant's governed record could be read (pre-existing)

- **Hole.** Found by the independent review at `feb12052`. The coordinator confirmed it at both `feb12052` and `d9305603` (`R/integ/verify-C2-feb12052.txt`, `R/integ/verify-C2-d9305603.txt`).
  - **Mechanism.** The artifact server's "not own" branch calls `runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference`, and the holds there compared only the principal id. Hold 2 authorized under the record's tenant without checking `grant.tenants`, and nothing compared the capability's tenant with the record's.
  - **Effect.** A principal of `tenant-guard-own` received `replay-binding-fixture-tenant`'s governed record bytes. Precondition: the same principal id in both tenants, a known address, entitlement, and full disclosure.
  - **Weaker form.** At `full`, another tenant's record answered `unauthorized` where a missing record answers `nonexistent`, so the answer was a cross-tenant existence oracle.
  - **Scope.** Present in v1.0.1 (the D-IMPL-345 era). It violates D-IMPL-345 R-2.
  - **Evidence.** `R/review/probe_c8_cross_tenant_read.out`, `R/review/probe_c8_cross_tenant_read_portable.*.out`, `R/review/probe_c8_full_disclosure.out`.
- **Ruling (coordinator).** Blocking, fixed now. A cross-tenant request gets the single `nonexistent` envelope; R-4's `unauthorized` stays for other principals of the same tenant. Cost if wrong: a cross-tenant auditor flow would need an explicit multi-tenant grant design, and none exists.
- **Red.** `9f22da65` (lane-377-tenant; changes tests only). Coordinator re-run: 4 failed, covering the HTTP and MCP doors, each with the colliding principal and at full disclosure (`R/integ/tenant-red-9f22da65.txt`).
- **Fix.** `b20ab4cc` adds hold 0 in `govern_dereference`: the deciding tenant must equal `authorized.tenant`, otherwise the request gets the missing-address refusal. Docs `d0a15e7b`: the SP §4.10 bullet, fragment 377-06, and the corrected C8 bullet. Merged as `8ef9e207`.
- **Green.** 43 passed, including D-IMPL-345's 32 and C8's 4 (`R/integ/tenant-green-integ.txt`).
- **Severing, by the coordinator.** Hold 0 → `if False and …`: 4 failed (both doors × both cases). The hash matched (`81120915`) and porcelain was 0. Evidence: `R/integ/c2-sever-integ.txt`, `R/integ/c2-old.txt`, `R/integ/c2-new.txt`.
- **Residuals.**
  1. A read-refusal record carries the door recorder's tenant, as fragment 377-06 states. The focused re-review showed the consequence: a capability for the door's tenant with the same client id reads another tenant's principal's read-refusal records. That is now disclosed on SP §4.10 but not closed (§4f).
  2. `src/ccf/erasure/store.py::ErasureConsultingStore.scoped` still resolves a URI naming another tenant. This is harmless while hold 0 runs first, because the tenant view scopes only the erasure consult.
  3. Within a tenant, another principal's genuine record still answers `unauthorized` at `full`. That is D-IMPL-345 R-4, by design.
  4. The focused re-review of `c2c341e2` found C-2 closed: its probes now answer `False`. Hold 0 is load-bearing: the reviewer's own severing of it turned the 4 tests red, with the file's hash matching after the restore (`R/review/rr/probe_c8_cross_tenant_read.out`, `R/review/rr/probe_c8_full_disclosure_v2.out`, `R/review/rr/sever-hold0.out`). The same review found the forged-record read, fixed in §3j. The final short review of `421947b8` found C-2, the full-disclosure oracle and M-4 still closed (ledger, 16:09; `R/review/rr2/probe_c8_cross_tenant_read.out`, `R/review/rr2/probe_c8_full_disclosure_v2.out`, `R/review/rr2/probe_c8_tenant_slash.out`).

### 3c. M-4: a tenant id containing `/` was read back as another tenant

- **Hole (review).** `src/ccf/artifacts/file_store.py::FileArtifactStore.names_at` reads names back by splitting `tenant/class/name`. A tenant id that contains `/` is therefore attributed to another tenant. The C8 fix relies on this attribution (`R/review/probe_c8_tenant_slash.out`).
- **Red.** `6d981036` (changes tests only). Coordinator re-run: 3 failed (`R/integ/tenant-red-6d981036.txt`).
- **Fix.** `03096722`. `src/ccf/artifacts/protocol.py::authorized_write_target` refuses, by name, a tenant id that contains the naming separator. Merged as `8ef9e207`.
- **Green.** Included in the 43 passed (`R/integ/tenant-green-integ.txt`).
- **Severing.** Run by the lane only. The refusal was changed to `if False and …`: 3 failed, and the hash was `b10a828b` before and after. Evidence: `R/lanes/tenant/severing-m4-red.txt`, `R/lanes/tenant/severing-m4-sha-before.txt`, `R/lanes/tenant/severing-m4-sha-after.txt`. The ledger records no coordinator severing for M-4, so this check is UNVERIFIED by the coordinator.
- **Re-review.** Closed: the reviewer's tenant-slash probe is now refused at the write boundary (`R/review/rr/probe_c8_tenant_slash.out`).
- **Residuals.** Names filed under a `/` tenant before the refusal existed are still attributed to the prefix tenant by `names_at` (disclosed on SP §4.10). A deployment with hierarchical tenant ids must change their spelling; that is the cost stated with the ruling.

### 3d. EX-01: request values spliced into SPARQL text

- **Hole.** Request values were spliced into SPARQL text in cp-16, cp-17 and cp-04-canonical (baseline §B; D-IMPL-375 "Ledger"). D-IMPL-376 (7) ordered the fix.
- **Red.** `58288edf` (lane-377-ex0109). No example code changed relative to the base. Coordinator re-run of `tests/examples/test_ex_01_sparql_value_placement.py`: 41 failed, 28 passed (`R/integ/ex01-red-at-58288edf.txt`).
- **Fix.** `5ee6af41`, after the lint restructure `0e6a2892`. The guards refuse a value rather than escape it, and the output is byte-identical for every value they admit. One dated record was appended to each changed tree's `FINDINGS.md`. Merged as `2c830372`.
  - `examples/cp-17-mnpi-wall-enforcement/acquisition.py::_literal` guards the values placed in `examples/cp-17-mnpi-wall-enforcement/acquisition.py::_over_wall`, `examples/cp-17-mnpi-wall-enforcement/acquisition.py::_reg_fd` and `examples/cp-17-mnpi-wall-enforcement/acquisition.py::_family`.
  - `examples/cp-04-canonical-corporate-family-tree/acquisition.py::_literal` guards the anchor in `examples/cp-04-canonical-corporate-family-tree/acquisition.py::acquire`.
  - `examples/cp-16-abs-securitization-surveillance/acquisition.py::_iri` guards the IRI at `examples/cp-16-abs-securitization-surveillance/acquisition.py::_Graph.triggers`.
- **Green.** 69 passed (`R/integ/ex_01_sparql_value_placement-green-integ.txt`).
- **Severing, by the coordinator.** The coordinator severed a site the lane did not: cp-04-canonical's `_literal` guard → `if False:`. 4 failed: the quote, newline, backslash and `\u` rows. The hash matched (`24ca6563`). Evidence: `R/integ/ex01-sever-cp04c-integ.txt`. The lane's own severings of cp-16 and cp-17 are in `R/lanes/ex0109/sever1-*` and `R/lanes/ex0109/sever2-*`.
- **Residuals.**
  1. Review M-7: the values that cp-04-canonical's graph reads return are not guarded. This is a second-order splice.
  2. The splices outside these three trees are listed in §7b.

### 3e. EX-09: unquoted `search_path`, 16 of 16 sites

- **Hole.** `SET search_path` was built by string formatting. D-IMPL-375 counted "seven modules". `git grep` at `d9305603` measured 16 sites in 15 modules, re-measured for this document.
- **Red.** `58288edf`. Coordinator re-run of `tests/examples/test_ex_09_search_path_identifier.py`: 31 failed, 4 passed, 3 xfailed (`R/integ/ex09-red-at-58288edf.txt`).
- **Fix.** `5ee6af41` fixed 15 sites in 14 modules: cp-08, cp-09, cp-10, cp-11, cp-12, cp-13-canonical, cp-15, cp-16 (two sites), cp-17, cp-18, cp-19, cp-21, cp-23 and cp-24. Each site now sends `SQL("SET search_path TO {}").format(Identifier(schema))` from `psycopg.sql`. Merged as `2c830372`. Green: 35 passed, plus 3 strict xfails for the frozen cp-13 site (`R/integ/ex_09_search_path_identifier-green-integ.txt`).
- **Severing, by the coordinator.** cp-08 was put back to the f-string: 3 failed (the static check and two cp-08 behavioral tests). The hash matched (`5e622ee7`). Evidence: `R/integ/ex09-sever-cp08-integ.txt`. The lane's severing of cp-24 is in `R/lanes/ex0109/sever3-*`.
- **The 16th site.** It is in the frozen specimen `examples/cp-13-covenant-cross-reference`, pinned by gate CXRC-G17. Dave ruled at 13:20 MST: "Fix the one line." The coordinator ran these checks (ledger, the correction recorded at "CLOSE-OUT DRAFT DONE").

  | Check | Result |
  |---|---|
  | Red | `65a89673` removed the test's exemption: 3 failed |
  | Fix | `4bdaff2a`: the Identifier form plus its import, and a `FINDINGS.md` section citing the ruling |
  | Green | 36 passed. cp-13 offline: 2 passed, 46 skipped. Lint rc 0 |
  | Severing | The line reverted: 3 failed. The hash matched (`b63f1714`) and porcelain was 0 |
  | Joined tree | Merged as `2de65c7b`. EX-01 plus EX-09: 105 passed (`R/integ/ex-green-integ-2.txt`) |

  Lane evidence: `R/lanes/ex0109/cp13-red-65a8967.txt`, `R/lanes/ex0109/cp13-green-4bdaff2.txt`, `R/lanes/ex0109/cp13-sever-4bdaff2.txt`.
- **Residuals.**
  1. The CXRC-G17 pin cannot show this change. Offline it skips; against the estate it errors at setup in family A before it reaches its assertion, on `d9305603` and on the candidate alike (§2). The estate re-run on `c2c341e2` accordingly reported no changed outcome (§6).
  2. Behavior change: `SET search_path TO "ccf_v2"` is now quoted. A schema value that relied on unquoted case folding, or a comma-separated list, now fails. No documented value does either.

### 3f. The Fluree test regression

- **Hole.** The test `tests/graph/test_fluree_backend.py::test_fluree_non_traverse_queries_are_pushed_not_silently_degraded` fails with `UngovernedClassificationAttribute` against a live Fluree.
  - **Cause.** The test's fixture boots without `governed_classification=` after SEC-023 (2026-10-06). The test was green on 2026-09-19 and the failure is invisible offline.
  - **Classification.** A test-only regression introduced by `deadline-rows`.
  - **How it was found.** The estate lane's Fluree leg at `d9305603`: 1 failed, 293 passed (`R/lanes/estate/legs/leg-fluree-d9305603.txt`).
  - **Consequence.** The hosted CI Fluree leg would be red on `main`.
- **Red.** Run by the coordinator on the joined tree @ `34a1f6bf`, against a throwaway Fluree at 127.0.0.1:18090 that was removed afterwards: 1 failed (`R/integ/fluree-red-34a1f6bf.txt`).
- **Fix.** `497c6f6d`, committed by the coordinator on `dl-377-integ`. The test boots with `governed_classification=AUTHORITY.governed`, scoped to that one function.
- **Green.** 1 passed. The Fluree-marked tests in `tests/graph`: 20 passed. Evidence: `R/integ/fluree-green.txt`, `R/integ/fluree-graph-leg.txt`.
- **Severing.** The argument removed: 1 failed. The hash matched (`be71fcdc`). Evidence: `R/integ/fluree-sever.txt`, `R/integ/fl-old.txt`, `R/integ/fl-new.txt`.
- **Live confirmation.** The estate re-run's Fluree leg on `c2c341e2`: 294 passed, 0 failed (ledger, "ESTATE RE-RUN DONE"). The leg log itself is owner-only and is excluded from the record (§10).
- **Residuals.** `main` @ `d9305603` keeps this red until the candidate is merged. Cost of the ruling if wrong: one test-file diff that Dave can revert.

### 3g. The estate write fence: addresses, and the Neo4j variable

- **Hole.** Two defects:
  - **Spellings, not addresses.** `tests/examples/estate_guard.py::_names_a_curated_host` compared host strings and never canonicalized an address. This was D-GATE-358 finding 6, which was never closed. Measured: 5 alternate spellings of `.76` were not refused (estate F1; `R/lanes/estate/safety/fence-positive-control-d9305603.txt`).
  - **Neo4j unfenced.** `CCF_TEST_NEO4J_URI` was not fenced, although `.76` hosts a Neo4j and the Neo4j leg runs `MERGE` and creates indexes (estate F2; audit L-1).

  Dave ordered the fix at 14:27 MST (ruling 4).
- **Red.** `e706a5e2` (changes tests only). Coordinator re-run: 85 failed, 38 passed (`R/integ/fence-red-at-e706a5e2.txt`).
- **Fix.** `f70e6aef`. Merged as `2b919375`.
  - `tests/examples/estate_guard.py::_why_refused`, `tests/examples/estate_guard.py::_addresses`, `tests/examples/estate_guard.py::_numeric`, `tests/examples/estate_guard.py::_comparable` and `tests/examples/estate_guard.py::_curated` reduce every destination, and every curated declaration, to the network addresses it reaches. The forms covered are dotted quads, IPv6, `inet_aton` forms, IPv4 embedded in IPv6, and names resolved through `getaddrinfo`.
  - A host that cannot be resolved is refused by name.
  - `tools/estate_fence.py::WRITE_TARGET_VARS` and `tests/conftest.py::DISPOSABLE_STORE_ENV` now include `CCF_TEST_NEO4J_URI`.
- **Green.** 131 passed (`R/integ/fence-green-integ.txt`).
- **Severing, by the coordinator.** The address intersection was replaced with an empty result: 77 failed, which is exactly the set of tests that depend on addresses. The tests for an unresolvable host stayed green, as they should. The hash matched (`1501eeba`). Evidence: `R/integ/fence-sever-integ.txt`.
- **Re-review of `c2c341e2`.** 25 spellings of `.76` are refused (ledger; `R/review/rr/probe_fence_spellings.out`). Two minors: the fence did not read libpq's environment (`PGHOSTADDR`, `PGSERVICE`), and an empty `CCF_CURATED_ESTATE_HOSTS` disabled it (`R/review/rr/probe_fence_spellings.out`, `R/review/rr/probe_estate_fence_tool.out`).
- **Follow-up fix (fence2).**

  | Check | Result |
  |---|---|
  | Red | `01704e94` (changes tests only). Coordinator re-run: 21 failed, 128 passed (`R/integ/fence2-red-01704e94.txt`) |
  | Fix | `9a6f75d7`, merged as `421947b8`. Details below |
  | Green | 157 passed (`R/integ/fence2-green.txt`) |
  | Severing, by the coordinator | The empty-declaration rule reverted: 6 failed, exactly the empty-declaration tests. The hash matched (`3baa0ad6`). Evidence: `R/integ/fence2-sever-integ.txt`, `R/integ/f2-old.txt`, `R/integ/f2-new.txt` |

  What the fix changed:
  - `tests/examples/estate_guard.py::curated_hosts_in_force` treats an empty, blank or separator-only declaration as the default.
  - `tests/examples/estate_guard.py::_libpq_effective` and `tests/examples/estate_guard.py::_target_destinations` judge a Postgres target as libpq will connect it: `PGHOST` and `PGHOSTADDR` fill what the connection string leaves out.
  - Any libpq service (`service=`, `PGSERVICE`, `PGSERVICEFILE`) is refused by name.
  - `tools/estate_fence.py::main` and the guard report the hosts in force and where they came from.
- **Final short review of `421947b8`.** The fence variants are refused. A localhost DSN with `PGHOST` exported still correctly passes, because libpq connected to 127.0.0.1 (ledger, 16:09; `R/review/rr2/probe_fence_spellings.out`, `R/review/rr2/probe_fence_pghost_explicit.out`).
- **Residuals.**
  1. The fence sees only the first-hop address, so an SSH tunnel, a docker port-forward or an outbound proxy passes it.
  2. A name is resolved once per session.
  3. It over-refuses `inet_aton` junk and `mongodb+srv` URIs.
  4. The `make leg-*` targets have no gate on the make side; the session fence covers them.
  5. Behavior change: a `CCF_TEST_*` name that does not resolve stops the session. CI exports localhost, so CI is unaffected.
  6. Estate F3 and F4 remain (§7c).
  7. After fence2: the testcontainer DSN, used when `CCF_TEST_POSTGRES_DSN` is unset, never passes through the fence. `PGHOSTADDR` or `PGSERVICE` could redirect it; its random port makes that low-risk (ledger, "FENCE2 DONE").

### 3h. The PyPI rename, `Private :: Do Not Upload`, the remedy texts and the placeholder (the SEC-027 row stays OPEN)

- **Hole.** Two problems:
  - **Dependency confusion.** The distribution was named `ccf`. On public PyPI, `ccf` is Microsoft's Confidential Consortium Framework (7.0.18), so `pip install ccf` installed Microsoft's package (D-IMPL-376 (4)).
  - **Accidental publication.** An accidental `twine upload dist/*` would have published the proprietary 62 MB sdist, which includes the whitepaper (ledger, 13:20).
- **Round 1: the rename.**

  | Check | Result |
  |---|---|
  | Red | `e4dc3741`; only the test file differs from the base. Coordinator: 6 failed in `tests/test_distribution_name.py` (`R/integ/pypi-red-at-e4dc3741.txt`) |
  | Fix | `eb217b85`, with docs `6d6cfbea`, lock `75e0cfae`, fragment `f094051f`, and placeholder `c89a20da` and `838a921c`. Merged as `34a1f6bf`; the `SURFACE-CHANGES` conflict was re-assembled, and the regenerated files showed no further change |
  | Green | 70 passed and 80 passed (`R/integ/integ3-targeted.txt`, `R/integ/integ3-tools-targeted.txt`) |
  | Severing, by the coordinator | `SDK_DISTRIBUTION` → `"ccf"`: 2 failed, the reader-consistency test and the adapter pin. The hash matched (`7b4231c9`) (`R/integ/pypi-sever-integ.txt`) |

  The fix:
  - `[project] name` is now `ccf-sdk`.
  - `src/ccf/graph/registry.py::SDK_DISTRIBUTION` and `tools/check_version_stamp.py::DISTRIBUTION`, the SDK's readers of its own metadata, name `ccf-sdk`.
  - The install docs and SP §3.1 are updated.
- **Round 2 (Dave, 14:27 MST, ruling 3).**

  | Item | Red → fix | What changed |
  |---|---|---|
  | Classifier | `ac601ae4` → `1bf1aac4` | `Private :: Do Not Upload` is in the SDK's metadata |
  | Review M-1 | `f8150c0b` → `9465e117` | Reinstall remedies name their source, never public PyPI by bare name |
  | Review M-2 | `e606e218` (docs) | Remaining `ccf[...]` references that mean this SDK now read `ccf-sdk` |
  | Review M-3 | `9465e117` | The consequence of a mixed former install is stated |
  | References | `bf051284`, `691e8605` | Remaining references |

  The coordinator re-ran both reds, 1 failed each (`R/integ/pypi2-red-ac601ae4.txt`, `R/integ/pypi2-red-f8150c0b.txt`). The round was merged as `1ccc6243`. Green: 8 passed (`R/integ/pypi2-green-integ.txt`). The severings:
  - **Classifier, by the coordinator.** The classifier → `[]`: 1 failed; the hash matched (`d3d9772e`) (`R/integ/pypi2-sever-classifier.txt`).
  - **M-1, by the lane only.** `R/lanes/pypi/sever5-m1-red-9465e11.txt`, `R/lanes/pypi/sever5-m1-remedy-9465e11.diff`, `R/lanes/pypi/sever5-m1-remedy-9465e11-steps.txt`.
- **Round 3: the re-review's PyPI minor.** The focused re-review found that installing an extra by bare name could replace the installed SDK with the empty placeholder. Before the fix, the SDK was replaced by `ccf-sdk 0.0.0` (`R/review/rr/pip-extra-real.out`; `R/lanes/pypi/scenario-pip-extra-BEFORE-e606e21.txt`).

  | Check | Result |
  |---|---|
  | Red | `e147fb5d` (changes tests only). Coordinator re-run: 1 failed (`R/integ/pypi3-red-e147fb5d.txt`) |
  | Fix | `d4a45175`: the placeholder declares `requires-python = "<3"`, so no Python 3 installer can select it. Hints `87a1774b`: the SDK's install hints install an extra from the SDK's own source, never by bare name from public PyPI. Merged as `4387a43d` |
  | Green | 8 passed (`R/integ/pypi3-green.txt`) |
  | Severing, by the coordinator | `requires-python` removed: 1 failed. The hash matched (`e7416a00`) (`R/integ/pypi3-sever.txt`, `R/integ/rp-old.txt`, `R/integ/rp-new.txt`) |

  After the fix:
  - The same scenario exits 1 and leaves the SDK intact (`R/lanes/pypi/scenario-pip-extra-AFTER-d4a4517.txt`).
  - Installing the placeholder under Python 3.12 is refused (`R/lanes/pypi/placeholder-install-refused-d4a4517.txt`).
  - The final short review confirmed that `requires-python = "<3"` blocks both a force-reinstall and an extra install, and the SDK stays installed (ledger, 16:09; `R/review/rr2/pip-placeholder-requires-python.out`). It also found the hint edits in `mongo.py`, `neo4j.py` and `embedder.py` docstring-only.
- **The upload files changed.** Only these may be uploaded (`R/lanes/pypi/DAVE-PYPI-STEPS.md`; the files are in `R/lanes/pypi/dist-placeholder/`):

  | File | Size | sha256 |
  |---|---|---|
  | `ccf_sdk-0.0.0-py3-none-any.whl` | 1,194 bytes | `0e6e1b9ef494b64c68bfa002b87e6cbad4c05b5f50669816b237b38bdf96372e` |
  | `ccf_sdk-0.0.0.tar.gz` | 1,225 bytes | `e24eb5d20dafe449c1664d0077d3d5c2ff488d26b626edbe6ee1fd8da988a047` |

  The earlier files (wheel `e68dda4f…`, sdist `8d566c80…`) must **not** be uploaded. Step 6 of Dave's steps verifies the upload with a download that needs `--ignore-requires-python` (`R/lanes/pypi/dave-step6-download-d4a4517.txt`). `twine check` passed both new files (`R/lanes/pypi/twine-check-d4a4517.txt`).
- **Status.** The code closes on the three checks. The **SEC-027 row stays OPEN** until Dave uploads the placeholder.
- **Residuals.**
  1. The import name `ccf` still collides with Microsoft's `ccf` when both are installed in one environment (disclosed on SP §3.1).
  2. The release gate cannot detect a mixed `ccf` + `ccf-sdk` environment (§7f).
  3. Dated records still say `pip install "ccf[neo4j]"` and `"ccf[mongo]"`. They are left as written.
  4. The entry-point group `ccf.graph_backends` is prefixed by a name Microsoft owns. There is no collision today.
  5. A PEP 541 challenge against an empty placeholder is possible.
  6. The shared venv is out of step with the lock (click 8.4.2 against 8.5.0).
  7. `/home/parkave/ccf_code/ccf.egg-info` stamps the old version for any interpreter started in that directory.
  8. Reinstalling the shared venv first needs `pip uninstall -y ccf`.

### 3i. The approval-gate race: the in-process double pass

- **Hole.** `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume` had no per-execution lock and no compare-and-set; its docstring said "NOTHING MAKES THIS RESUMPTION'S READ-DECIDE-COMMIT ATOMIC". Two failure modes:
  - **(a) Double pass.** Two concurrent resumptions of one suspension both passed the authority and conflict checks, so the step after the gate ran twice on one human approval.
  - **(b) Outvoted rejection.** A rejection recorded inside the read→commit window was not seen, so the execution completed at the approving terminal with both verdicts on record.

  Context:
  - It was not disclosed under `public/` (grep: 0 hits).
  - It is the same class as SEC-001 (CRITICAL), gated by a race.
  - It had gone untracked since D-IMPL-357 (baseline F3). The coordinator verified it at 13:02 MST.
- **Probe at `34a1f6bf`.** (a) and the follow-on are in `R/lanes/race/results.txt`, `R/lanes/race/http_door_a_results.txt` and `R/lanes/race/followon_results.txt`; (b) is in `R/lanes/race/natural_b_sweep.txt` and `R/lanes/race/natural_b_positive_control.txt`.

  | Case | Result |
  |---|---|
  | (a) threaded | Reproduced 5 of 5, in each of 4 variants |
  | (a) one event loop | Reproduced 5 of 5 |
  | (a) shipped HTTP door | Reproduced 3 of 3: two concurrent `POST /workflow/resumptions` both returned 200, and the node ran twice |
  | (a) sequential controls | Refused 5 of 5; over HTTP, 200 then 409 |
  | Follow-on | The orphaned pending event on the next gate absorbed an approval, 3 of 3 |
  | (b) forced timing | Reproduced 15 of 15 |
  | (b) natural timing, in process | 0 of 6000 |
  | (b) over HTTP | Not measured |
- **Ruling.** Dave, 14:27 MST: "Small fix now". That means a per-run lock in the engine, in-process only, with the multi-process limit disclosed, red/green/severing, and an independent review.
- **Red.** `19f99c59` (changes tests only). Coordinator re-run: 4 failed, covering one event loop, two threads in two variants, and the served door (`R/integ/race-red-at-19f99c59.txt`).
- **Fix.** `e1f7b1d8`. Merged as `c2c341e2`.
  - The resumption takes a single-flight claim before it reads the state: `runtime/ccf_runtime/workflow/engine.py::_claim_resumption`.
  - The claim is released on every exit path by `runtime/ccf_runtime/workflow/engine.py::_release_resumption`; four tests cover the release.
  - A second concurrent resumption is refused with a typed 409, audited `resolved=False`, and never queued. Audit test `87755042`.
  - SP §4.13 and fragment 377-05 were added (`1f432550`, `db0c5916`).
- **Green.** 9 passed (`R/integ/race-green-integ.txt`).
- **Severing, by the coordinator.** The claim check was bypassed (`if False and not _claim_resumption(claim)`): 4 failed, exactly the tests for the hole. The hash matched (`eaf42b55`) and porcelain was 0. Evidence: `R/integ/race-sever-integ.txt`, `R/integ/rc-old.txt`, `R/integ/rc-new.txt`.
- **Re-review of `c2c341e2`.** The guard is sound in its scope (ledger). The race-related suites passed, 307 tests (`R/review/rr/race-tests.out`). The reviewer's own severing of the claim turned the 4 hole tests red, and the file's hash matched after the restore (`R/review/rr/sever-claim.out`). Three minors:
  - a hung step holds the claim, with no timeout;
  - the claim is taken before the gate's authority check, so the in-flight refusal is visible to same-tenant `Resume` holders;
  - the erasure door's message wording.
- **Follow-up: race docs.** `c4fa0556` (lane-377-race-docs; docs only, 55 lines added to SP §4.13), merged as `c4893f90`. It records three measured limits:
  - **A hung step keeps the claim for the life of the process** (3 of 3). After a restart, the shipped in-memory composition has lost the execution: a resumption is refused "no execution exists", and starting it again re-runs its first step. A durable store keeps the approval, and the next resumption runs the step after the gate again (`R/lanes/race2/a-b-hang-2dc17656.txt`, `R/lanes/race2/a-restart-2dc17656.txt`).
  - **The in-flight 409 is visible to same-tenant `Resume` holders.** A `Resume` capability for another tenant learns nothing.
  - **The erasure door's message is cut at 400 characters,** which drops its "stays withheld" clause, so callers should read the reason code. A retry returns the same record (`R/lanes/race2/c-erasure-concurrent-2dc17656.txt`).

  These are documentation changes; no severing applies. The final short review found SP §4.13 consistent with the code (ledger, 16:09).
- **Residuals** (§4d):
  - (b) is still open;
  - (a) is still open across processes or separate state-store objects;
  - `WorkflowEngine.execute` has no single-flight;
  - a failed or canceled resumption leaves an attributed row.

### 3j. The forged record: the governed read served bytes the fabric's record writer never filed (pre-existing)

- **Hole.** Found by the focused re-review of `c2c341e2`. The coordinator confirmed it over MCP and HTTP (`R/integ/verify-forged-mcp.txt`, `R/integ/verify-forged-http.txt`); the reviewer's probes are `R/review/rr/probe_c2_forged_record.out` and `R/review/rr/probe_c2_forged_record_http.out`.
  - **Mechanism.** `runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference` took the tenant and the principal from the stored bytes. It never checked that the fabric's record writer, a `ReplayMint` class, had filed the address under that tenant.
  - **Effect.** Tenant B files bytes on its own client lane that claim tenant A and one of A's principals; A's governed reads then serve them. Measured: MCP `True`; HTTP `/replay/decisions` 200 and `/artifact` 200.
  - **Scope.** Present since D-IMPL-345, which assumed a forged record was "readable by its forger alone" (ledger).
- **Ruling.** Dave, 15:3x MST: "Fix now (Recommended)".
- **Red.** `7960a07e` (lane-377-forged; changes tests only). Coordinator re-run: 5 failed, 1 passed, 1 xfailed (`R/integ/forged-red-7960a07e.txt`).
- **Fix.** `37946325`. Before hold 0, `govern_dereference` now checks provenance:
  - the store's own naming (`names_at`) must show the address filed under the record's deciding tenant, in a class the store's `WriteKinds` declares under `ReplayMint`;
  - anything else answers exactly as a missing address does;
  - a store that cannot say who filed an address refuses with `runtime/ccf_runtime/authz/delivery_boundary.py::UnattributableDeliveryBoundaryError`, a `TypeError`.

  Docs `ce25ca81` cover SP §4.10 and fragment 377-07. Merged as `06b80efe`; regenerating the manifest added the new error type.
- **Green.** 46 passed and 1 xfailed, including the C-2 tests, D-IMPL-345's 32 and C8's 4 (`R/integ/forged-green-integ.txt`).
- **Severing, by the coordinator.** The provenance check was bypassed (`if False and not filed_by_the_record_writer`): 3 failed, the three forgery tests. The hash matched (`fe315ac0`). Evidence: `R/integ/forged-sever-integ.txt`, `R/integ/fr-old.txt`, `R/integ/fr-new.txt`.
- **Residuals** (§4g):
  1. **Same-tenant bytes on the client lane.** Record-shaped bytes filed by a principal of the same tenant still cross the MCP client lane, as a client-lane artifact. A strict xfail records this. Changing it is a C8-split decision for Dave. It is disclosed on SP §4.10, "The MCP client lane is not a governed read".
  2. **Read-refusal attribution is not closed.** The record names the door recorder's tenant, which leaks the asked reference but never content. It is disclosed on SP §4.10 with a mitigation.
  3. **Denials read for nobody** (by code reading). Delivery-boundary denials filed under a different recorder tenant now read for nobody.
  4. **Final short review** (ledger, 16:09, on `421947b8`). It found no Critical or Important finding.
     - The forged record is closed on both doors: MCP served `False`; HTTP answered 404 and 404 (`R/review/rr2/probe_c2_forged_record.out`, `R/review/rr2/probe_c2_forged_record_http.out`).
     - Genuine owners still read their own records (`R/review/rr2/owner-chain.out`).
     - The door suites pass: 1289 passed and 1 known xfail (`R/review/rr2/suite-final-1.out`).

     One minor is deferred. The provenance check's store configuration is judged per request, not at boot: `WriteKinds` must name every `ReplayMint` class, and the store must answer `names_at`. So a mis-built door fails at its first read: genuine records read "nonexistent", or the read fails with `UnattributableDeliveryBoundaryError` (a 500). `create_app` checks only the recorder's class, and fragment 377-07's Migration does not say this. It is not caller-triggerable and is no oracle.

## 4. Still open

### 4a. SEC-020: open, with every remaining channel named

**What route A changed** (D-IMPL-376 (3): one bounded round).

| Step | Commits and results |
|---|---|
| Build | Lane-377-sec020: reapply `6247cd63`, a revert of the revert `91fd7965` whose added and removed lines are identical to `77d5e2a9`. Red `01ce0666`, fix `aa3872ce`, pin `f2c61c59`, docs `d4e06da1` |
| What the fix does | `src/ccf/products/resolver.py::GovernedResolver` reads the fabric once before the acquisition seam. The withheld re-execution then runs over `src/ccf/projection/engine.py::_BeforeAcquisitionReader` |
| Red | Coordinator, at `01ce0666`: 2 failed. The ids are `tests/products/test_withheld_is_indistinguishable_from_absent.py::test_the_paved_road_acquisition_seam_does_not_reveal_a_withheld_subject[from_decision-class]` and `[from_entity_freshness-class]` (`R/integ/sec020-red-at-01ce0666.txt`) |
| Merge and green | Merged **provisionally** as `cf86fa5d`. Green: 39 passed (`R/integ/sec020-green-integ.txt`) |
| Severing | `before_acquisition` → `None`: the same 2 ids failed. The hash matched (`29983861`) and porcelain was 0 (`R/integ/sec020-sever-integ.txt`). The reviewer's own severing agrees: 3 failed (`R/review/sever-before-acquisition.out`) |
| Lane gates at `d4e06da1` | R1–R5, examples (29, the baseline), lint, mypy, surface 246, docs 320. Census: no deterministic content address moved |

**Docs pass.** Lane-377-sec020-docs ran three rounds (`40de9b84`, `3576e293`, `8363351d`) and was merged as `491f0f29`.
- **Docs and comments only.** The coordinator found `resolver.py`, `engine.py` and `plan.py` AST-identical to `feb12052` once docstrings are stripped. The final short review agreed that these edits are docstring-only.
- **C-1 is now a strict expected failure.** The test was `test_c1_a_withheld_answer_carries_the_record_name_a_nonexistent_subject_gets` in `tests/products/test_withheld_is_indistinguishable_from_absent.py` (at `8363351d`). With the marker in place: 2 xfailed. With the marker removed: 2 failed, naming `42e7877e` and `cd5bd4ef`. A control with the instrument broken fails through `pytest.fail`. Evidence: `R/lanes/s20docs/c1-xfail-8363351.txt`, `R/lanes/s20docs/sever-c1-marker-removed-8363351.txt`, `R/lanes/s20docs/sever-c1-instrument-broken-wt.txt`. *Later (D-IMPL-378, Dave's Q11): the name-equality criterion this test pinned was rejected — equal public references must not identify different record contents — and the candidate of lane 378b-s020record replaces it with `tests/http_api/test_sec020_replay_reference_issuance.py`.*
- **Fragment 370-20.** Its policy-withhold sentence was re-measured and holds.

**Status: OPEN** (Dave, 14:27 MST, ruling 2: "Keep fix, row stays OPEN"). The channel numbers below are referenced elsewhere in this document. Every channel was measured on test fixtures.

| # | Channel | What still tells a withheld subject from a nonexistent one | Evidence | Disclosed (SP @ `421947b8`) |
|---|---|---|---|---|
| 1 | Population-shaped acquisition | The candidate mirrors `main`. On `main`, a subject-keyed seam differed and a population seam matched. On the candidate, the subject-keyed seam matches and a population-shaped `acquire` differs: at the empty finding under `from_decision`, and as `ttl-refusal` against `ttl-anchor-refusal` under `from_entity_freshness` | `R/lanes/sec020/probe-shapes-d930560.txt` (main); `R/lanes/sec020/probe-shapes-d4e06da.txt`; `R/lanes/s20docs/population-shapes-feb1205.txt` | SP §4.12, "An acquisition not keyed on the subject" |
| 2 | C-1: the answer's replay reference | The record name, which is dimension 1's `graph_snapshot_id` (`src/ccf/replay/serve.py::ReplayWriter`), differs: `42e7877e…` for the withheld subject against `cd5bd4ef…` for two nonexistent subjects. This holds on the class-seeded paved road for both anchors. The name crosses `ServedProduct.replay_ref`, the MCP door's `replay_ref`, HTTP `X-CCF-Replay-Ref` and a refusal's `replay_reference`, with no dereference needed. The products themselves are equal. It is not a regression: `main` leaked through the product itself | `R/integ/verify-C1.txt`; `R/review/probe_sec020_replay_ref_name.out`; `R/review/probe_sec020_replay_ref_doors.out`; `R/lanes/s20docs/c1-replay-ref-name-feb1205.txt` | SP §4.12, "The answer's replay reference", and the "Until SEC-020 closes" paragraph |
| 3 | The record behind the reference | Dimension 1 lists what the plan read, including the acquired subject, and an owner at `full` can read its own record (D-IMPL-345, ruled). Each half was measured separately; reading a withheld decision's record end to end through the dereference was not run | `R/lanes/s20docs/record-dim1-feb1205.txt`; `R/lanes/s20docs/d345-owner-read-feb1205.txt`; `R/review/probe_sec020_refusal_replay.out` | SP §4.12, "The record behind it" |
| 4 | I-1: composite children | A class that declares `requires` resolves its children for the asked subject before its plan runs. With a child asked about the composite's own subject from a source keyed on it, the products differed at `debt.debt` and `debt.factors.freshness`. With a child asked about a fixed subject, they did not | `R/review/probe_sec020_composite.out`; `R/lanes/s20docs/i1-composite-feb1205.txt` | SP §4.12, "Composite children" |
| 5 | I-2: similarity over an entity the acquisition refreshed | The re-run reuses the operator registry built from the view read after acquisition. The products differed at `computed_empty`, `debt.debt`, `debt.factors.freshness` and `debt.scorers`. A registry built from the view read before acquisition closes this channel; that small fix was offered to Dave (§9) | `R/review/probe_sec020_similarity_registry.out`; `R/lanes/s20docs/i2-similarity-registry-feb1205.txt` | SP §4.12, "Similarity over an entity the acquisition refreshed" |
| 6 | M-6: a fabric that outlives the question | After one question about a withheld subject that the source holds, a later answer about an identifier that names nothing moved at `debt.debt` and `debt.factors.freshness`. That is a two-step existence oracle. The paved road boots one fabric per question; a hand-composed long-lived fabric does not | `R/review/probe_sec020_persistent_fabric.out`; `R/lanes/s20docs/m6-persistent-fabric-feb1205.txt` | SP §4.12, "A fabric that outlives the question" |
| 7 | M-5: records written before the change | A replay limit rather than an existence channel. A record written before `computed_empty` existed still fails replay with `ReplayDivergence` | `R/review/probe_old_record_replay.out`; `R/review/probe_old_record_replay_inproc.out`; `R/lanes/s20docs/m5-old-record-replay-feb1205.txt` | Fragment 370-20 (corrected); **not on the SP** |

**Costs and lane carries.**
- **Extra read.** One extra as-of read per governed call with a seam. On one fixture, median time rose by a factor of 1.2 to 1.3 (`R/review/probe_sec020_readcost.out`; `R/lanes/s20docs/readcost-feb1205.txt`; SP §4.12).
- **Timing.** On one fixture, withheld and nonexistent medians were within 2 percent of each other. Larger fabrics are unmeasured (`R/review/probe_sec020_timing.out`; `R/lanes/s20docs/timing-feb1205.txt`; SP §4.12).
- **Seeded plans.** A subject-seeded paved plan records an empty dimension 1 although it acquired, because `TraversalNeighborhood` walks from seed classes (a D-IMPL-371 finding).
- **Exactness** would need acquisition invoked a second time per question for an identifier that names nothing. That breaks the rule the ledger cites as R-4, "exactly once": `src/ccf/products/resolver.py::AcquisitionSeamProtocol` documents the seam as called exactly once per question. It is a new design (§9).

### 4b. SEC-027: open until Dave's upload

The code closed (§3h). The row closes when Dave uploads the **new** placeholder files from his account (`R/lanes/pypi/DAVE-PYPI-STEPS.md`): the wheel with sha256 `0e6e1b9e…` and the sdist with sha256 `e24eb5d2…`. The earlier files, `e68dda4f…` and `8d566c80…`, must not be uploaded.

Until the upload, `ccf-sdk` on public PyPI is unclaimed. On 2026-10-07, `ccf-sdk`, `ccf_sdk` and `cognitive-context-fabric` returned 404 (D-IMPL-376 (4)). The import-name collision with Microsoft's `ccf` remains and is disclosed (SP §3.1).

### 4c. SEC-029: open until the tag

The row closes only at a release tag, after the release checks (D-IMPL-376 (4)). There was no tag today, and the newest tag is still `v1.0.1` (`git describe` reads `v1.0.1-611-g421947b8`). The standing red `tests/test_version_stamp.py::test_the_installed_version_is_not_the_stale_literal_and_is_git_derived` gives `PackageNotFoundError` in the shared venv since the rename. It passes in a disposable venv built from `requirements.lock` (ledger, "Combined-regression env").

### 4d. The approval-gate race: what the in-process claim does not cover

| Residual | Status | Evidence | Disclosed (SP @ `421947b8`) |
|---|---|---|---|
| **(b) An outvoted rejection.** Verdicts are recorded in `src/ccf/hitl/transport.py::InMemoryHitlTransport.submit` and never pass through the engine. Forced timing still reproduces it 15 of 15 times after the fix. Closing it needs a claim registry in `src/`, keying by event key, a new typed refusal at every submission door, and an amendment to `src/ccf/hitl/transport.py::HITLTransportProtocol` | OPEN | ledger, "RACE FIX DONE 15:11" | SP §4.13, "A verdict recorded while a resumption is in flight is still not seen" (reconcile executions that hold both verdicts) |
| **(a) The double pass across processes,** or across separate state-store objects over one durable store. `src/ccf/controlplane/state.py::ControlPlaneStateStore` has no compare-and-set | OPEN | same | SP §4.13, "Serialize resumptions per execution in front of the door when more than one process can resume" |
| **Retry re-runs the step.** A resumption that fails or is canceled after its step started releases the claim, so a retry runs the step again | OPEN, by design | same | SP §4.13, "Keep the steps after a gate idempotent" |
| **A hung step.** A step that never returns keeps the claim for the life of the process; there is no timeout and no operator override. After a restart, the shipped in-memory composition has lost the execution. A durable store keeps the approval, and the next resumption runs the step after the gate again | OPEN, disclosed | ledger, "RACE DOCS DONE 15:54"; `R/lanes/race2/a-b-hang-2dc17656.txt`; `R/lanes/race2/a-restart-2dc17656.txt` | SP §4.13, "A step that never returns keeps the claim for the life of the process" |
| **In-flight visibility.** The in-flight 409 tells a same-tenant `Resume` holder that a resumption is running | OPEN, disclosed | same ledger entry | SP §4.13, "The in-flight refusal tells a `Resume` holder that a resumption is running" |
| **Erasure door message.** The message is cut at 400 characters, which drops its closing clause | OPEN, disclosed | `R/lanes/race2/c-erasure-concurrent-2dc17656.txt` | SP §4.13, "At the erasure door, read the reason code, not the message, and retry" |
| **New, measured:** `WorkflowEngine.execute` has no single-flight. Two concurrent `execute` calls with one execution id run the start node twice and leave two pending events | OPEN, out of scope | `R/lanes/racefix/out-of-scope-probe.txt` | **No** |
| **New, measured:** a failed or canceled resumption leaves an attributed `workflow_resumed` row for a passage that never committed. A retry adds a second row, and the node runs twice | OPEN, out of scope | same | Partly: SP §4.13 covers the re-run, not the attributed row |
| A conflicted gate wedges permanently, and there is no primitive to reopen it (D-GATE-357 (2); 1.0.3) | OPEN, carried | baseline §C.2 | No |
| The narrowing of the conflict population is unproven (D-GATE-357 (3)) | OPEN, carried | baseline §C.2 | No |

### 4e. Example findings without a lane

EX-02, EX-07, EX-08 and EX-10 have no closure record and no lane (baseline F2; ledger). See §7a.

### 4f. The focused re-review of `c2c341e2`, and what was done with each finding

The re-review ran from 15:13 to 15:30 MST (ledger, "RE-REVIEW DONE 15:30"; probes and severings in `R/review/rr/`). A final short review of `421947b8` followed at 16:09. It found no Critical or Important finding and re-ran the probes (`R/review/rr2/`); its one deferred minor is in §4g.

| Finding | Grade | What was done | Status |
|---|---|---|---|
| C-2 and M-4 | — | Found closed. The probes answer `False`, and hold 0 is load-bearing: its severing turned 4 tests red (`R/review/rr/sever-hold0.out`) | CLOSED (§3b, §3c) |
| Race guard | — | Found sound in its scope (`R/review/rr/race-tests.out`, `R/review/rr/sever-claim.out`) | CLOSED in scope (§3i) |
| Fence | — | 25 spellings of `.76` refused (`R/review/rr/probe_fence_spellings.out`) | CLOSED (§3g) |
| PyPI classifier | — | Present in the built package's METADATA (ledger) | CLOSED (§3h) |
| **Forged record**: the governed read served record-shaped bytes the fabric's record writer never filed | IMPORTANT | Dave: "Fix now (Recommended)". Fixed at `37946325`, merged as `06b80efe` | CLOSED (§3j). The final short review of `421947b8` confirmed it closed on both doors |
| **Read-refusal attribution**: refusal records name the door recorder's tenant, so a door-tenant capability with the same client id reads a foreign principal's refusal record and learns the asked reference. Reproduced on the candidate and on the `main` export (`R/review/rr/probe_c2_read_refusal_attribution.out`, `R/review/rr/probe_c2_read_refusal_attribution.main.out`) | IMPORTANT/MINOR | Disclosed on SP §4.10, with a mitigation: distinct client ids across tenants that share a door, or one door and recorder per tenant | OPEN, disclosed. A redesign is Dave's decision (§9) |
| Race: a hung step holds the claim, with no timeout | MINOR | Disclosed on SP §4.13 (race docs) | OPEN, disclosed (§4d) |
| Race: the claim precedes the gate-authority check, so the in-flight 409 is visible to same-tenant `Resume` holders | MINOR | Disclosed on SP §4.13 | OPEN, disclosed (§4d) |
| Race: the erasure door's message wording | MINOR | Disclosed on SP §4.13: read the reason code | OPEN, disclosed (§4d) |
| Fence: libpq's `PGHOSTADDR` and `PGSERVICE` were not read | MINOR | Fixed by fence2 | CLOSED (§3g) |
| Fence: an empty `CCF_CURATED_ESTATE_HOSTS` disabled the fence | MINOR | Fixed by fence2 | CLOSED (§3g) |
| PyPI: an extra installed by bare name could pull the placeholder over the SDK | MINOR | Fixed in round 3: the placeholder's `requires-python = "<3"`, and install hints that point at the SDK's own source | CLOSED (§3h) |

### 4g. What the follow-up lanes left open

| Item | From | Disclosed (SP @ `421947b8`) | Next |
|---|---|---|---|
| Record-shaped bytes filed by a principal of the same tenant cross the MCP client lane as a client-lane artifact. A strict xfail records it | Forged lane | SP §4.10, "The MCP client lane is not a governed read" | Dave: a C8-split decision (§9) |
| Read-refusal records name the door recorder's tenant. They leak the asked reference, never content | Forged lane; re-review | SP §4.10, "A read-refusal record is attributed to the door's tenant" | Dave: a redesign (§9) |
| Delivery-boundary denials filed under a different recorder tenant now read for nobody (code reading) | Forged lane | No | Carried (§7f) |
| The testcontainer DSN, used when `CCF_TEST_POSTGRES_DSN` is unset, never passes through the fence. `PGHOSTADDR` or `PGSERVICE` could redirect it; its random port makes that low-risk | Fence2 | Not applicable: this is the test fence | Carried (§7c) |
| The fence sees the first hop only | Fence, fence2 | Not applicable | Carried (§3g) |
| The docstrings of `runtime/ccf_runtime/erasure/door.py::ErasureRefused` and `runtime/ccf_runtime/erasure/door.py::ErasureDoor.complete` say "nothing was written". That is false for `workflow-refused`, where the approval artifact and the write-ahead entries are written first | Race docs (out of scope) | No | Follow-up batch (§7f) |
| The 400-character cut drops the closing clauses of long refusals | Race docs (out of scope) | Partly: SP §4.13 covers the erasure door | Follow-up batch (§7f) |
| The provenance check's store configuration is judged per request, not at boot, so a mis-built door fails at its first read: genuine records read "nonexistent", or a 500 with `UnattributableDeliveryBoundaryError`. `create_app` checks only the recorder's class. Not caller-triggerable; no oracle | Final short review (deferred minor) | No: fragment 377-07's Migration does not say it | Follow-up batch (§9) |

## 5. Deployment restrictions an adopter must honor

These are the 47 rows of baseline §D, updated, plus the restrictions added today (rows 48–67). Unless a row says otherwise, "SP" means the page on the candidate @ `421947b8`.

**A deployment of `main` @ `d9305603` lacks several disclosures:** SP §3.1, the SP §4.6 SQLite bullet, the C8, C-2 and forged-record text in SP §4.10, SP §4.12, and SP §4.13. It also still carries C8, C-2, M-4, the forged-record read and the in-process race.

SP section headings, on the candidate @ `421947b8`:

| SP | Heading |
|---|---|
| §1.1 | A2A identity (D-IMPL-15) |
| §1.1a | A2A replay defense and the signed question (SEC-022, D-IMPL-371) |
| §1.2 | SignedHitlAction (D-IMPL-21 / D-IMPL-363, HITL identity) |
| §2 | Rotation posture |
| §3.1 | The distribution name is `ccf-sdk` (SEC-027) |
| §4.1 | Acknowledge the insecure default, or bind an auth hook |
| §4.2 | Choose the authorization posture |
| §4.3 | Decide where key custody lives |
| §4.4 | Decide which transport the product door serves on |
| §4.5 | Declare the Claude adapter's child environment |
| §4.6 | Decide how many processes share a graph (SEC-013) |
| §4.7 | Declare which sources may assert a classification (SEC-023, D-IMPL-372) |
| §4.8 | Two deployment limitations, disclosed rather than fixed |
| §4.9 | Declare a product roster for principals that must not reach every product (SEC-017, D-IMPL-374) |
| §4.10 | Declare and protect the erasure index (SEC-009, D-IMPL-374) |
| §4.11 | Declare a default for a parameter a policy constraint bounds (SEC-019, D-IMPL-356) |
| §4.12 | A withheld subject can still be told from a nonexistent one (SEC-020, open; D-IMPL-376) |
| §4.13 | Resume a suspended run from one process, and serialize resumes beyond it (D-IMPL-377) |
| "SEC-024" | Validation-error text and caller values (SEC-024, choice C), an unnumbered section |

**D.1 Single writer (SEC-013)**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 1 | Run one writer host per graph, or hosts that share a filesystem with working `flock`. Several hosts need the Postgres advisory lease, which is reachable only by constructing the store with `writer_lease=`; `ccf.boot.boot` cannot declare it | D-IMPL-376, "LIMITS CARRIED VISIBLY" | SP §4.6 |
| 2 | On Fluree, MongoDB and Neo4j, declare `writer_lease_lock_dir`. It must be absolute, its real path, existing, owned by the writer's effective user, and neither group- nor world-writable. Otherwise the boot fails with `WriterLeaseRequired` | D-IMPL-374 (1); D-IMPL-375 executor ruling (g) | SP §4.6 |
| 3 | Keep every ancestor of the lock directory writable only by the writers' user or root. Ancestors are not checked | SP | SP §4.6 |
| 4 | Declare one spelling of the server address across every writer of a graph | D-IMPL-375, SEC-013 | SP §4.6 |
| 5 | MongoDB: list the same hosts in the same order in every writer. The usual replica-set URI is refused at construction with a `ValueError` | SP | SP §4.6 |
| 6 | Neo4j cluster: every writer names the same routing address | SP | SP §4.6 |
| 7 | SQLite: keep the database and its sidecar on a local filesystem. A forked child shares the lease | SP | SP §4.6 |
| 8 | The SQLite lease needs `fcntl.flock`; a platform without it is refused | `src/ccf/graph/backends/sqlite.py::SqliteWriterLease` | **No** |
| 9 | Postgres: use direct or session-pooled connections only. A dropped connection loses the lease silently, and the lease shares the database's advisory-lock key space | SP | SP §4.6 |
| 10 | The in-memory store is process-scoped only | SP | SP §4.6 |
| 11 | A read-only boot still runs the store's open-time setup (DDL; Fluree ledger creation), so its credentials must allow that. It is not coordinated with the writer | SP (N-6) | SP §4.6 |
| 12 | Replaying beside a live writer needs `read_only=True` on `boot` or `load_config_and_boot` | D-IMPL-375 executor ruling (f) | SP §4.6, SP §4.7 |
| 13 | A composition that calls the L2 writer directly (the "low road") must compose the temporal write guard itself | D-IMPL-364, SEC-008 B1 | **No** |
| 48 | **New.** SQLite: keep the database file's directory writable only by the account the SDK runs as. The sidecar is opened without `O_NOFOLLOW`, so a symbolic link placed at `<database file>.ccf-writer.lock` is followed | baseline F1; `feb12052` | SP §4.6, SQLite bullet (candidate only) |

**D.2 Doors, tenancy and authorization**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 14 | Bind an auth hook, or acknowledge the insecure default explicitly. Never bind a tenant authorizer without an auth hook | SP | SP §4.1 |
| 15 | Authorization stays at the door. Do not rely on a second enforcement point further in | SP | SP §4.2 |
| 16 | The stdio product door serves one principal: `serve_stdio(identity=…)` is required, and an ambient identity is refused on mutating surfaces. A deployment with several principals uses `serve_loopback` or its own transport. On the paved road, loopback recognizes one boot credential | D-IMPL-361; D-IMPL-373 | SP §4.4 |
| 17 | Declare a `products` roster on every grant that must not reach every product. Build directory entries with `exposed_agent`, declare `replay_record_product_class`, and govern the surfaces that cannot see a product class with the scope mapping | D-IMPL-374 (2) | SP §4.9 |
| 18 | Do not use the stdio client adapter from a process that holds credentials its child must not see | SP | SP §4.8 |
| 19 | Control what is installed beside the SDK, and treat `ReservedBackendName` at boot as a supply-chain finding | SP | SP §4.8 |
| 20 | **Updated.** The candidate does not need isolated tenant stores, the fallback in D-IMPL-376 (6), because C8 and C-2 are closed there (§3a, §3b). `main` @ `d9305603` still carries C8 and C-2, so a deployment of `main` needs isolated tenant stores | D-IMPL-376 (6); ledger | SP §4.10, "Another tenant's filings do not change a tenant's answers (C8 and C-2, D-IMPL-376)" (candidate only) |
| 21 | Every tenant declares a `TemporalBoundaryPolicy`. An undeclared policy refuses every governed serve, and there is no default. An upgraded deployment without one refuses 100% at serve | D-GATE-358 (1); D-IMPL-358 ruling 11; ledger (estate lane) | **No** (measured: neither term appears on the SP); follow-up batch (§7e) |
| 22 | The file artifact store's root must be owner-only (an insecure root is refused by name, and its mode is left untouched), and `write_kinds` must be declared | D-IMPL-369 (3); D-IMPL-375 SEC-014; SEC353-G-03 | **No.** SP §4.10 names `WriteKinds` only for the erasure classes |
| 23 | Validation errors returned to callers no longer echo the rejected value. This is an accepted consequence | D-IMPL-371 (3) | "SEC-024" |
| 49 | **New.** A deployment's own `ArtifactSubstrate` behind a store that several tenants share must file a name only together with its bytes. It must have no verb that registers a name by reference | ledger, C8 carry (2) | SP §4.10, C8/C-2 bullet. Not stated in the Protocol docstrings |
| 50 | **New.** A tenant id must not contain `/`; such writes are refused at the write boundary. A store that already holds filings made under such an id before the refusal still attributes them to the prefix tenant, so audit existing stores | ledger, M-4 | SP §4.10, C8/C-2 bullet |
| 51 | **New.** Another tenant's record answers `nonexistent` at every disclosure level. A cross-tenant auditor flow would need a multi-tenant grant design, which does not exist; the artifact server refuses multi-tenant grants. Within a tenant, another principal's record answers `unauthorized` at `full` (D-IMPL-345 R-4) | ledger, C-2 ruling | SP §4.10 for the answers. The auditor-flow limit: **No** |
| 62 | **New.** Treat a record as evidence only when a governed read returned it. A tenant's MCP client-lane filings are served to every principal of that tenant as the exact stored bytes, whatever their shape, and the answer does not say which lane served it | ledger, forged lane | SP §4.10, "The MCP client lane is not a governed read" |
| 63 | **New.** Keep client ids distinct across tenants that share a door, or give each tenant its own door and recorder: a read-refusal record names the door's tenant | ledger, forged lane | SP §4.10, "A read-refusal record is attributed to the door's tenant" |
| 64 | **New.** A store behind the governed read must answer `names_at`, and its `WriteKinds` must name every `ReplayMint` class. Otherwise the governed read refuses with `UnattributableDeliveryBoundaryError`. The check runs per request, not at boot, so a mis-built door fails at its first read | ledger, forged lane; final short review | SP §4.10, C8/C-2 bullet. That it runs per request: **No** |

**D.3 Keys, peers and HITL**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 24 | Production key custody goes behind `SigningKeySource` / `IdentityProvider`. `FileBackedKeySource` is a development reference. No key material in the tree | SP | SP §1.1, SP §4.3 |
| 25 | Key rotation is the operator's responsibility: there is no schedule and no revocation list | SP | SP §2 |
| 26 | A2A: every `PeerTrustGrant` declares `signature_max_age_seconds` and `permitted_clock_skew_seconds`; there is no default. A producer never reuses a nonce under one signing key | SP | SP §1.1a |
| 27 | A2A receivers in several processes must share one `SeenNonceSetProtocol` store, and none ships. Supply a pruning seen-set under sustained load. After a restart, an envelope still inside its window is admitted once more | SP; D-IMPL-376 (2) | SP §1.1a |
| 28 | A2A LF leg: declare `max_request_bytes`. Bound concurrency and ASGI buffering at the server, and bound outbound response size at the egress proxy or the injected HTTP client | SP | SP §1.1a |
| 29 | HITL signing is declared in a `ccf.hitl-policy` statement. The CLI door is unsigned-only. Nonce uniqueness per `(tenant, event_key)` is the signer's obligation. No byte-level signing rule exists for signers not written in Python (CR-363-01) | SP; D-IMPL-363 C11 | SP §1.2. CR-363-01: **No** |
| 30 | `ApprovalPolicy` is registered by the adopter only. Executions suspended before the upgrade refuse under a bound plane, so re-run them. A custom HITL transport must stamp `event_state_at_submit` (A9). One approver only; there is no quorum | D-IMPL-366; D-IMPL-356 | SP §1.2, dated note. A9 and quorum: **No** |
| 31 | Claude adapter: start sessions with `adapter.transport(carrier)`, declare `child_environment`, and call `remove_prompt_directories()` after use. `max_turns` is a budget, not a boundary | SP | SP §4.5 |
| 52 | **New.** Resume a suspended execution from one process. Where more than one process, or more than one state-store object over one durable store, can resume, serialize resumptions per execution in front of the door | Dave 14:27, ruling 1; ledger 15:11 | SP §4.13 |
| 53 | **New.** Present a refused (409) resumption again only after the other resumption has returned | ledger 15:11 | SP §4.13 |
| 54 | **New.** Keep the steps after a gate idempotent. A failed or canceled resumption releases the claim, so a retry runs the step again and adds a second attributed `workflow_resumed` row | ledger 15:11 | SP §4.13 for the re-run. The attributed row: **No** |
| 55 | **New.** Reconcile outvoted rejections: route every execution that left a gate whose suspension holds both an approve and a reject verdict to human review | ledger 15:11, (b) | SP §4.13 |
| 56 | **New.** Do not start one execution id twice concurrently: `WorkflowEngine.execute` has no single-flight | ledger 15:11, out of scope | **No** |
| 65 | **New.** If a step after a gate never returns, cancel the resumption or restart the process; the claim has no timeout and no operator override. After a restart, the shipped in-memory composition has lost the execution, and a durable store runs the step after the gate again on the next resumption | ledger, race docs | SP §4.13, "A step that never returns keeps the claim for the life of the process" |
| 66 | **New.** Grant `Resume` only to principals entitled to know when a run is being resumed | ledger, race docs | SP §4.13, "The in-flight refusal tells a `Resume` holder that a resumption is running" |
| 67 | **New.** At the erasure door, read the reason code rather than the message, which is cut at 400 characters, and retry | ledger, race docs | SP §4.13, "At the erasure door, read the reason code, not the message, and retry" |

**D.4 Classification (SEC-023)**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 32 | Declare `attribute_authorities` on every rule that writes a classification attribute. Bind `SourceIdentity.system_id` to a real system; the SDK does not attest it. An out-of-tree reader calls `require_query_classification_authority`. An operator that filters on classification declares `read_intent` or calls `require_classification_authority` | SP | SP §4.7 |

**D.5 Erasure (SEC-009)**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 33 | There is no graph erasure: L3 and every new product keep the subject. Only whole artifacts are erased, nothing is destroyed, and no legal-compliance claim is made | D-IMPL-375; D-IMPL-376 | SP §4.10 |
| 34 | The erasure door's private key is the trust root. Its custody is the deployment's | D-IMPL-376 | SP §4.10 |
| 35 | Protect the index: file mode 0600, directory mode 0700. Anyone with write access can un-erase its tail. The mitigation is filesystem controls (SP), or append-only storage (D-IMPL-376) | SP; D-IMPL-376 | SP §4.10. Append-only storage: **No** (baseline F10) |
| 36 | Keep the index on a filesystem where `flock` and `O_APPEND` work for every appender | SP | SP §4.10 |
| 37 | Pending erasure approvals survive a restart only with a durable HITL transport | SP | SP §4.10 |
| 38 | One erasure door per tenant. A third-party HITL transport exposes `hitl_policy_key`. Complete pending erasures before dropping a door key. A third-party Control Plane keeps one content per policy version | SP | SP §4.10 |
| 39 | **Updated.** Accepted: a forged entry in one tenant withholds another tenant's content on tenantless reads. The MCP artifact server's client lane is tenant-scoped and is not one of those reads (corrected at `feb12052`) | SP; D-IMPL-376 | SP §4.10 |
| 40 | Torn index lines are repaired by hand. No repair tool ships | SP | SP §4.10 |
| 41 | The in-process adapter must register the HITL policy, approval policy and erasure workflow in its own code. The `--local` CLI has no erasure door | SP | SP §4.10 |
| 42 | `exists` does not consult the erasure index (U8), so an erased address still answers `exists` | D-IMPL-374 (4); `src/ccf/erasure/store.py::ErasureConsultingStore.exists` | **No** |
| 43 | Retention-lifecycle orchestration is outside the 1.0 boundary | DECISIONS, "Decision Replay — the 1.0 capability boundary"; D-IMPL-374 (4) | **No** |

**D.6 Policy constraints (SEC-019)**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 44 | Declare a default for every bounded parameter, and narrow `applies_to` to the classes that declare it. A custom `PolicyConstraintResolver` refuses an absent bounded parameter itself. Put numeric bounds on numeric parameters only | SP | SP §4.11 |

**D.7 Withheld subjects (SEC-020; new section)**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 57 | **New.** For a product whose projection withholds subjects, key the acquisition on the subject | Dave 14:27, ruling 2 | SP §4.12 |
| 58 | **New.** Do not rely on `withheld=True` to hide whether a subject exists from a caller who can see an answer's replay reference, whenever the plan's walk reaches the subject's records. The in-process answer, the MCP egress door and the HTTP product route all return one (§4a channel 2) | ledger; SEC-020 docs pass | SP §4.12, "Until SEC-020 closes" |
| 59 | **New.** Protect access to replay records as you would the subject itself (§4a channel 3) | SEC-020 docs pass | SP §4.12 |
| 60 | **New.** Only the paved road boots a fabric per question; a hand-composed long-lived fabric does not get that. Composites with subject-keyed children, and similarity over refreshed entities, still distinguish (§4a channels 4–6) | ledger; SEC-020 docs pass | SP §4.12 |

**D.8 Packaging, threat model, examples**

| # | Restriction | Source | Disclosed |
|---|---|---|---|
| 45 | **Updated.** On the candidate the distribution is `ccf-sdk`. Install it from the repository, never by name, and never into an environment that holds Microsoft's `ccf`, because each overwrites the other's `ccf/__init__.py`. Install the extras from the SDK's own source, never by bare name from a public index. On `main` @ `d9305603` the distribution is still `ccf`, and `pip install ccf` installs Microsoft's package | D-IMPL-376 (4); ledger | SP §3.1 (candidate only) |
| 46 | No release tag covers the remediated tree; `v1.0.1` is the newest. SEC-029 closes only at a tag, after the release checks | D-IMPL-376 (1), (4) | **No** |
| 47 | The threat model covers governed served surfaces. Arbitrary Python running in the same interpreter is outside it: mint keys and private tables guard against accident, not against an adversary | D-GATE-353 (1); D-IMPL-354 (1); D-IMPL-375 SEC-023 | **No** |
| 61 | **New, examples only (not the SDK).** `SET search_path` is now sent as a quoted identifier, so a schema value that relied on unquoted case folding, or a comma-separated list, fails | ledger, EX lane | **No** (example `FINDINGS.md` only) |

## 6. Untested paths

These are the 25 rows of baseline §E, updated (E1–E25), plus the paths found today (N1–N10).

| # | Path | Status after today | Source |
|---|---|---|---|
| E1 | The 743 estate-gated example nodes, never run on the candidate | **Run twice, read-only.**<br>• At `d9305603`: 660 read-only ids ran against `.76`, with 36 passed, 161 failed, 405 errors and 58 xfailed. **Only 47 of the 660 opened a `.76` connection.** The 93 ids that write ran against local containers: 85 passed, 8 xfailed, no connection to `.76`. Families are in §6a.<br>• At `c2c341e2`, Dave's re-run on the combined tree: the re-audit was unchanged (660 read-only, 93 local, 0 write risk, 0 unknown; the changed modules issue only SELECTs and session SETs), and nothing moved. **0 of 660 outcomes changed**, the 566 reds have byte-identical first error lines, and the same 47 ids reach `.76`.<br>• The affected-subset check on `421947b8` is pending (§9, item 1) | ledger, "LANE ESTATE DONE" and "ESTATE RE-RUN DONE 15:41"; `R/lanes/estate/AUDIT-d9305603.md`; `R/lanes/estate/ESTATE-RESULTS-by-id-d9305603.tsv`; `R/lanes/estate/netlog/analysis-pass3-d9305603.txt`; `R/lanes/estate-rerun/RE-AUDIT-c2c341e2.md`; `R/lanes/estate-rerun/netlog-analysis-c2c341e2.txt`; `R/lanes/estate-rerun/final-estate-comparison-c2c341e2.txt` |
| E2 | The live Fluree, MongoDB and Neo4j legs | **Ran twice on disposable single-node containers, removed afterwards.**<br>• At `d9305603`: Postgres 243 passed, 12 failed. The 12 are standing reds: cp-00 ×2, cp-01 ×1, s1-00 ×9. Neo4j 29 passed; MongoDB 38 passed; Fluree 293 passed, 1 failed (the regression fixed in §3f).<br>• At `c2c341e2`: Postgres 243 passed, plus the same 12 standing reds; Neo4j 29 passed; MongoDB 38 passed; **Fluree 294 passed, 0 failed**.<br>The 12 standing reds are from the ledger. The `c2c341e2` leg logs and the `d9305603` Postgres leg log are owner-only and excluded from the record (§10) | ledger; `R/lanes/estate/legs/leg-fluree-d9305603.txt`, `leg-mongo-d9305603.txt`, `leg-neo4j-d9305603.txt`; `R/lanes/estate/container-lifecycle-d9305603.txt`; `R/lanes/estate-rerun/container-lifecycle-c2c341e2.txt` |
| E3 | Hosted CI substrate coverage | Unchanged. No hosted run is recorded today: UNVERIFIED | baseline E3 |
| E4 | CI-COVERAGE-01 (14 hosted Postgres-leg failures of undetermined status) | Unchanged | baseline E4 |
| E5 | The D-IMPL-376 (1) checks on the merge commit | **Done (§2), but the pins guard less than their names say.** cp-04 and cp-05 pass by construction on `main`. The cp-03, cp-06 and cp-13 pins never reach their assertion (N10) | ledger |
| E6 | Multiple writer hosts | Unchanged | baseline E6 |
| E7 | A2A receivers in more than one process; re-admission after a restart | Unchanged | baseline E7 |
| E8 | MongoDB replica sets and Neo4j clusters | Unchanged; today's legs used single-node containers | baseline E8 |
| E9 | The erasure index on a shared multi-host filesystem | Unchanged | baseline E9 |
| E10 | The live `claude` CLI under the TP-02 carrier | Unchanged | baseline E10 |
| E11 | Other MCP library versions (the FastMCP private APIs pinned at `mcp` 1.28.1) | Unchanged | baseline E11 |
| E12 | SEC-009: a mixed-signature retry; the concurrent racer's error is unnamed; cryptographic soundness was not judged | Unchanged. Also untested, found today: completing an erasure end to end over `McpArtifactStore` (§3a) | baseline E12; ledger, C8 carry (4) |
| E13 | Peering: B3 covers only the grant-bound route; `_PinnedReader` pins on no shipped substrate | Unchanged | baseline E13 |
| E14 | SEC-008 B1: the named severing was never executed | Unchanged | baseline E14 |
| E15 | SEC-007 under severing | Unchanged | baseline E15 |
| E16 | SEC-001: no control covers concurrent resumes | **Updated.**<br>• (a) within one process now has controls: 4 red-then-green tests (§3i)<br>• (a) across processes has none, because no shared store ships<br>• (b) reproduces 15 of 15 under forced timing; natural timing in process gave 0 of 6000; over HTTP it was not measured<br>• Concurrent `execute`: untested before today's probe<br>• A hung step and a restart were measured; the restart used the reference store and transport persisted to disk, standing in for durable ones (§3i) | ledger 13:53, 15:11, 15:54 |
| E17 | SEC-006: A7, A3, A5 | Unchanged | baseline E17 |
| E18 | The temporal-bound demonstration surface | Measured at `d9305603`: 285 ids in family A and 11 in family A' (§6a). At `c2c341e2` the same reds recurred (E1) | estate TSV; ledger |
| E19 | The `TOKEN_*`-gated modules error instead of skipping | Unchanged. Estate F13 also found rung estate gates that omit the door-token variables | baseline E19; ledger |
| E20 | `s1-01` under SEC-013 | Partly exercised: the 93 write-capable ids, 45 of them `s1-01` ids, passed or xfailed against a local Fluree at `d9305603`. Whether they exercise the N-1 lock-root mode: UNVERIFIED | ledger; `R/lanes/estate/audit/WRITES-LOCAL-ids-d9305603.txt` |
| E21 | SEC-023 example source ids are unconfirmed against the estate | Still unconfirmed: most ids stopped before acquisition (N1) | ledger |
| E22 | Sabotage attestation | Unchanged | baseline E22 |
| E23 | Standing reds that mask coverage | Unchanged by id at `d9305603`, `34a1f6bf` and `feb12052`: the 30 chunk-3 ids, the ratchet (362 unique), and the version stamp | §2, §3 |
| E24 | Weak or vacuous witnesses: LOW-01-C-01, SEC-014-C-01/-C-03, SEC-022-C-04, the CR-363-08 and -10 door siblings | Unchanged | baseline E24 |
| E25 | The adoption probe | Unchanged | baseline E25 |
| N1 | **Estate coverage.** 613 of the 660 read-only ids never opened a `.76` connection, at `d9305603` and again at `c2c341e2`. They stop first at the SDK refusals in §6a, so their behavior against the estate is still untested | **New** | `R/lanes/estate/netlog/analysis-pass3-d9305603.txt`; `R/lanes/estate-rerun/netlog-analysis-c2c341e2.txt` |
| N2 | **The co-lender estate was never read.** No run connected to the co-lender Fluree (`:8091`, `bofa/syndicate`) or to Postgres `bofa_syndicated`, at `d9305603` or at `c2c341e2`. cp-20's 19 ids failed or errored first: 17 in family D and 2 in family A | **New** (measured from the TSV and the two netlog analyses for this document) | `R/lanes/estate/ESTATE-RESULTS-by-id-d9305603.tsv`; `R/lanes/estate-rerun/netlog-analysis-c2c341e2.txt` |
| N3 | **What today's example fixes exercised on `.76`** (the re-run at `c2c341e2`).<br>• EX-09's quoted `search_path` ran live on cp-09 to cp-13.<br>• EX-01's validators were not reached on `.76`; they are tested offline only.<br>• Seven changed trees never reach `.76`: cp-08, cp-15, cp-18, cp-19, cp-21, cp-23 and cp-24 | **New** | ledger, "ESTATE RE-RUN DONE 15:41"; `R/lanes/estate-rerun/changed-code-exercised-c2c341e2.txt` |
| N4 | **C-2 over HTTP.** The coordinator reproduced the pre-fix exploit over the MCP artifact server only. For the HTTP evidence routes, the pre-fix behavior is shown only by red tests, not by an exploit probe. The forged-record exploit, by contrast, was confirmed over both MCP and HTTP (§3j) | **New** | `R/integ/verify-C2-*.txt`; `R/integ/tenant-red-9f22da65.txt` (two `tests/http_api` ids); `R/integ/verify-forged-http.txt` |
| N5 | **The race.** Race (b) over HTTP under natural timing has no test. Neither does race (a) across processes. The restart behavior was measured only with the reference store and transport persisted to disk, standing in for durable ones; no real durable store was run (SP §4.13) | **New** | ledger 13:53, 15:11, 15:54 |
| N6 | **SEC-020.** Reading a withheld decision's record end to end through the dereference was not run. Timing and read cost were measured at one fixture scale only. Channels 4–6 were measured on fixtures, not on the shipped examples | **New** | §4a; `R/lanes/s20docs/` |
| N7 | **PyPI.** The placeholder upload has not been executed; it is Dave's action. `twine check` passed the new files. The upload command was validated only against a dead local endpoint, on the earlier build | **New** | `R/lanes/pypi/twine-check-d4a4517.txt`; `R/lanes/pypi/twine-upload-syntax-dryrun-838a921.txt` |
| N8 | **Fence.** First-hop bypasses (an SSH tunnel, a docker port-forward, an outbound proxy) were not exercised. The `make leg-*` targets have no make-side gate. The testcontainer DSN never passes through the fence (§3g) | **New** | ledger, fence and fence2 residuals |
| N9 | **C8.** No test covers tenant isolation over a deployment-supplied `ArtifactSubstrate` that registers names by reference; it is stated as an obligation only (row 49) | **New** | ledger, C8 carry (2) |
| N10 | **Inert specimen pins.** The cp-03, cp-06 and cp-13 specimen pins never run. Offline they skip; against the estate they error at setup in family A, on `d9305603` and on `c2c341e2`. Nothing checks that those three frozen specimens are unchanged (§2) | **New** (ledger, "FINDING") | `R/lanes/estate/ESTATE-RESULTS-by-id-d9305603.tsv`; `R/lanes/estate/audit/READ-ONLY-ids-d9305603.txt`; `R/lanes/ex0109/specimen-pins-5ee6af4.txt` |

### 6a. The 566 estate reds at `d9305603`, by family

These are the 660 read-only ids, by family. Not counted here: 36 passed and 58 xfailed. Families A and A' are the temporal bound; the rest are SDK refusals or example gaps. The re-run at `c2c341e2` reproduced the same 566 reds, with byte-identical first error lines (ledger).

| Family | Ids | What stops them | Ledger status |
|---|---|---|---|
| A: `temporal-boundary-undeclared` | 285 | The example trees declare no `temporal_boundary:` | SEC358-G-01, ruled NOT-A-GAP; example work owed on 15 trees |
| A': temporal precedence, downstream | 11 | The temporal bound is judged before their own refusal | SEC358-G-02, NOT-A-GAP |
| B: `FileArtifactStore` `write_kinds` | 139 | No example declares `write_kinds=` | SEC353-G-03, OPEN |
| R: artifacts and pins re-keyed under the tenant | 51 | Bare Control Plane key names | SEC353-G-07, OPEN; plus an SDK documentation/diagnostic defect (§7e) |
| H: `GrantNotInForce` on the paved road | 24 | — | **UNLEDGERED** |
| C: `CapabilityBypassError` | 22 | Boot-time registrations refused | SEC353-G-05, plus an unledgered test helper |
| D: `register_manifest_entries(tenant=)` | 17 | cp-20, a frozen specimen | The ledger gives no gap-ledger id: UNVERIFIED which entry this is |
| E: `constraints_in_force` with `asked_at` removed | 12 | — | **UNLEDGERED** |
| F: `open_door(token_verifier=)` | 5 | Frozen custom doors | SEC353-G-09, OPEN (1.0.3) |
| **Total** | **566** | | |

**Safety of the estate run** (ledger; `R/lanes/estate/final-estate-comparison-d9305603.txt`; `R/lanes/estate/safety/`):
- **Nothing moved.** No movement was found at 30 chunk boundaries in each of 3 passes, after the local writes, or after the legs. Watermarks: Fluree `fibo-v2` at t5878; `ccf:main` at t1608 (30 ledgers); `ccf_v2` with 116 tables and 1,583,506 rows; `fibo_v2` with 6 collections and 38,238 documents; co-lender at t16.
- **Departmental SQLite.** Its sha is unchanged; the run read a sha-verified copy.
- **Read-only DSNs.** Every estate Postgres DSN carried `default_transaction_read_only=on`.
- **Fence.** The positive control refused 58 of 58, and every `CCF_TEST_*` variable pointed at 127.0.0.1.
- **Containers.** All four throwaway containers were removed.
- **Population.** The audit classified 660 ids as read-only, 93 as writing locally, 0 as a write risk and 0 as unknown (`R/lanes/estate/AUDIT-d9305603.md`).
- **The re-run at `c2c341e2` was just as safe.** It ran the same audit first (`R/lanes/estate-rerun/RE-AUDIT-c2c341e2.md`). Its fence control refused 58 of 58 through the address fence (`R/lanes/estate-rerun/fence-positive-control-c2c341e2.txt`). Every store was unmoved against both the first sitting's baseline and the re-run's own (`R/lanes/estate-rerun/final-estate-comparison-c2c341e2.txt`). Its containers were stopped and removed (ledger).

## 7. Remaining findings carried

Labels: "estate F*n*" is a finding from today's estate lane (ledger); "baseline F*n*" is a contradiction from baseline §F (§8). "Review C-/I-/M-*n*" is today's independent review; "final-review" and "combined-read" are the deadline-close reviews named in the baseline.

### 7a. Example findings (baseline §B, updated)

| ID | Original severity | Status today | Source or evidence |
|---|---|---|---|
| EX-01 | HIGH | **CLOSED** (§3d) | ledger |
| EX-02 | MEDIUM | **OPEN, no lane.** cp-06 and cp-06-canonical splice `facility_id` into a SPARQL IRI (census C1, C2) | `R/lanes/ex0109/census-d930560.txt` |
| EX-03 | MEDIUM | CLOSED (D-IMPL-373) | baseline |
| EX-04 | MEDIUM | CLOSED (D-IMPL-373) | baseline |
| EX-05 | MEDIUM | VOID (D-IMPL-351) | baseline |
| EX-06 | MEDIUM | VOID (D-IMPL-351) | baseline |
| EX-07 | LOW | **OPEN, no lane.** D-IMPL-368 Q3 ruled it "README notes", and none were found: UNVERIFIED | baseline |
| EX-08 | LOW | **OPEN, no lane.** No example README mentions TLS or `sslmode` | ledger; baseline |
| EX-09 | LOW | **CLOSED**, 16 of 16 sites (§3e) | ledger |
| EX-10 | LOW | **OPEN, no lane.** `examples/hw1-harness-clients/client_langgraph.py::connect` passes `env=dict(os.environ)`, and no disposition is recorded | baseline F2 |
| SEC353-G-01 | — | OPEN, awaiting a ruling: the eight rung HTTP doors do not build | baseline |
| SEC353-G-02 | — | OPEN: the loopback MCP doors refuse every credential | baseline |
| SEC353-G-03 | — | OPEN: `FileArtifactStore` needs `write_kinds=`. 139 estate ids (family B) | baseline; §6a |
| SEC353-G-04 | — | OPEN, blocked on D-IMPL-354: `ReplayWriter` and `QueryPinWriter` need a composition-minted `ReplayMint` | baseline |
| SEC353-G-05 | — | OPEN: boot-time registrations are refused. 22 estate ids (family C, together with an unledgered test helper) | baseline; §6a |
| SEC353-G-06 | — | OPEN, blocked on D-IMPL-354: cp-20's boot-time skill grant cannot be requested | baseline |
| SEC353-G-07 | — | OPEN except `s1-01`: bare Control Plane key names. 51 estate ids (family R) | baseline; §6a |
| SEC353-G-08 | — | OPEN: `boot(…)` naming no tenants raises `TypeError` | baseline |
| SEC353-G-09 | — | OPEN, target 1.0.3: eight frozen custom doors raise at construction. 5 estate ids (family F) | baseline; §6a |
| SEC358-G-01 | — | NOT-A-GAP, with example work owed on 15 trees. 285 estate ids (family A) | baseline; §6a |
| SEC358-G-02 | — | NOT-A-GAP, work owed. 11 estate ids (family A') | baseline; §6a |
| `TOKEN_*` gates | — | OPEN, carried: cp-15, cp-16, cp-18, cp-21, cp-23 and cp-24 error instead of skipping (see also estate F13) | baseline |
| Final-review M-10 | — | OPEN, disclosed in fragment 374-04: 16 example sites pass `control_plane=ControlPlaneRegistry()` inline | baseline |
| cp-04 and cp-05 specimen pins | — | **Measured today:** they pass on `d9305603`, by construction. The cp-03, cp-06 and cp-13 pins never reach their assertion (§2; N10) | ledger |
| SEC-023 example source ids | — | OPEN: never confirmed against the estate (E21) | baseline |
| hw1 reference client | — | OPEN, standing: the examples CI job fails because the hw1 reference client exits 1 | baseline |
| Example red roster | — | Unchanged: 30 chunk-3 ids by id through `feb12052` (29 example ids plus 1 perf id) | §2, §3 |
| R9, cp-20 self-grant | — | OPEN, carried (the same item as SEC353-G-06) | baseline |
| Estate family H | — | **New, UNLEDGERED:** `GrantNotInForce` on the paved road, 24 estate ids | ledger; §6a |
| Estate family E | — | **New, UNLEDGERED:** `constraints_in_force` with `asked_at` removed, 12 estate ids | ledger; §6a |
| Estate family D | — | **New:** `register_manifest_entries(tenant=)`, 17 cp-20 ids (frozen). The ledger gives no gap id | ledger; §6a |

### 7b. Example splices outside EX-01 (new today; census of `main` @ `d9305603`)

Source: `R/lanes/ex0109/census-d930560.txt`, as summarized in the ledger. All are open, reported and not fixed. Backlog: a reusable placement primitive (ledger: "§B.3/§I").

- **EX-02.** cp-06 and cp-06-canonical place `facility_id` in a SPARQL IRI: `examples/cp-06-canonical-collateral-and-setoff-coverage/acquisition.py::_walk_collateral` and its frozen twin `examples/cp-06-collateral-and-setoff-coverage/acquisition.py::_walk_collateral`.
- **cp-08.** `examples/cp-08-covenant-in-force-as-of/acquisition.py::_amendments` places the `as_of` literal and `facility_id` IRIs.
- **Caller values behind bound lookups:**
  - `examples/cp-10-rating-and-spread-migration/acquisition.py::grade_history`;
  - `examples/cp-20-syndicated-lending-co-lender/acquisition.py::_participations` and `examples/cp-20-syndicated-lending-co-lender/acquisition.py::_thresholds`;
  - `examples/peer-cp-20-co-lender/acquisition.py::_counterparty`;
  - the frozen `examples/cp-05-credit-exposure-rollup/produce.py::produce_governed`.
- **cp-07.** `examples/cp-07-client-360-coverage-graph/acquisition.py::_client_nodes` places LEIs unescaped.
- **Second-order (values returned by the store):**
  - `examples/cp-06-canonical-collateral-and-setoff-coverage/acquisition.py::_walk_ucc` and its frozen cp-06 twin place debtor names unescaped. This is the most plausible break on real data.
  - cp-09 intent (`examples/cp-09-treasury-liquidity-position/acquisition.py::posture_overlay`).
  - The cp-19 `subject_party` IRI (`examples/cp-19-aml-typology-match/acquisition.py::_typologies_for`).
  - Node IRIs returned by the graph are placed unvalidated (census D4): in cp-04-canonical, cp-07, cp-06 and cp-06-canonical, cp-13 and cp-13-canonical, and the frozen cp-04 and cp-05. The ledger's summary names cp-04-canonical, cp-07 and cp-13.
  - Review M-7: cp-04-canonical's graph-returned values are not guarded.
- **cp-14.** The `$` in `examples/cp-14-credit-memo-context/acquisition.py::_IRI` admits a trailing newline.
- **Configured names.**
  - Names are double-quoted without escaping an embedded `"` in cp-04-canonical, cp-06 and cp-06-canonical, cp-07 and cp-08 (census E2).
  - SQL table, column and schema names are interpolated unquoted across cp-00 to cp-24, peer-cp-20, s1-00 and s1-01. Values are bound everywhere; only names are spliced (census E1).
  - SPARQL `FROM <{ledger}>` and vocabulary IRIs appear in every graph-reading example. Only cp-14 holds them to an IRI grammar (census E3).

### 7c. Estate lane findings (new today)

Estate F1 and F2 closed in §3g. Estate F8 is also an exclusion rule for the record (§10).

| ID | Finding | Status |
|---|---|---|
| Estate F3 | `tests/examples/fixtures/cp_03_census_schema.sql` runs `CREATE SCHEMA ccf_v2` and `DROP TABLE IF EXISTS ccf_v2.* CASCADE` behind the session fence only. Together with F1, an alternate spelling of `.76` could drop curated tables. F1 is closed; the missing call-site fence remains | OPEN |
| Estate F4 | `tests/examples/test_cp_04_debt.py` writes behind the session fence only | OPEN |
| Estate F5 | Example estate connections are not opened read-only, and the `ccf_dataprep` role can write, so read-only behavior rests on statement text. The lane added `default_transaction_read_only=on` to its own DSNs; an operator following a README does not | OPEN; Dave's estate |
| Estate F6 | cp-15, cp-17, cp-18 and cp-19 runs rewrite `departmental.sqlite-shm` in `ccf_dataprep`: the database is in WAL mode, and `mode=ro` still updates the wal-index | OPEN; this writes into Dave's tree |
| Estate F7 | The census credential detector gives a false positive on JSON `\n` | OPEN |
| Estate F8 | Census redaction misses a dict repr. Dead loopback tokens and a removed container's password are in 16 lane files, now mode 0600; exclude them from any published record | OPEN |
| Estate F9 | The census detail is capped at 8000 | OPEN |
| Estate F10 | The SEC353 gap-ledger roster is stale (see baseline F4) | OPEN |
| Estate F11 | `tests/examples/test_cp_04_seams.py::provenance` reads the wrong store, and a strict xfail hides it | OPEN |
| Estate F12 | cp-15's gate demands `CCF_CP_15_SQLITE_PATH`, which no cp-15 code reads | OPEN |
| Estate F13 | The rungs' estate gates omit the door-token variables | OPEN |
| Estate F14 | CP17-F-10's strict xfail XPASSes. It asserts *that*, not *why* | OPEN |
| Audit L-6 | s1-00's L3 variable `CCF_S1_00_POSTGRES_DSN` (SDK DDL at boot) is fenced for `make` targets but not by the pytest session fence. This is in the audit only, not in the ledger's F-list | OPEN (`R/lanes/estate/AUDIT-d9305603.md`) |
| Specimen pins (ledger, "FINDING") | The cp-03, cp-06 and cp-13 specimen pins error at setup in family A on `d9305603` and on the candidate, so those three specimen guards are inert. The cp-04 and cp-05 pins pass on `main` only by construction (§2) | OPEN |
| Fence2 residual | The testcontainer DSN, used when `CCF_TEST_POSTGRES_DSN` is unset, never passes through the fence. `PGHOSTADDR` or `PGSERVICE` could redirect it; its random port makes that low-risk | OPEN (ledger, "FENCE2 DONE") |

### 7d. Independent review of `feb12052` (2 Critical, 2 Important, 7 Minor)

| ID | Grade | Finding | Status |
|---|---|---|---|
| C-1 | Critical | A withheld subject's answer carries a different replay-record name | OPEN, SEC-020 channel 2; disclosed on SP §4.12; strict xfail |
| C-2 | Critical | Cross-tenant governed-record read | **CLOSED** (§3b) |
| I-1 | Important | Composite child legs resolved for the asked subject | OPEN, SEC-020 channel 4; SP §4.12 |
| I-2 | Important | Similarity registry built from the post-acquisition view | OPEN, SEC-020 channel 5; SP §4.12. A small fix was offered (§9) |
| M-1 | Minor | The force-reinstall remedy would pull the empty placeholder once it is uploaded | **CLOSED**: red `f8150c0b`, fix `9465e117` |
| M-2 | Minor | Stale `ccf[mongo]`/`ccf[neo4j]` docstrings and test skip text | **FIXED** (docs) at `e606e218` |
| M-3 | Minor | The mixed-venv README claim | **FIXED** (docs) at `9465e117` |
| M-4 | Minor | A tenant id containing `/` | **CLOSED** (§3c) |
| M-5 | Minor | Records written before the change fail replay | OPEN, SEC-020 channel 7; fragment 370-20 |
| M-6 | Minor | A persistent fabric | OPEN, SEC-020 channel 6; SP §4.12 |
| M-7 | Minor | cp-04-canonical's graph-returned values are not guarded (second-order) | OPEN, listed in §7b |

The focused re-review of `c2c341e2`, and what was done with each of its findings, is in §4f.

### 7e. SDK documentation and diagnostic defects for the follow-up batch Dave ordered

Dave, 14:27 MST, ruling 4: "docs/diagnostic items go to a follow-up batch after this close-out". Source: ledger, estate lane.
1. **Temporal boundary.** It went live at `3976cbc1` with no migration note and no public documentation. An upgraded deployment refuses every governed serve (estate families A and A'; restriction 21).
2. **`BootedFabric` docstrings.** `src/ccf/deployment/manifest.py::BootedFabric` documents `.artifacts` and `.pins` wrongly, and fragment `353-09` ("Migration: none") is false (family R).
3. **`version_for`.** `src/ccf/deployment/pins.py::ResolvedPins.version_for` misdiagnoses.
4. **`from_declared(None)`.** `src/ccf/products/request.py::ProductRequestContract.from_declared` given `None` raises `AttributeError` instead of refusing.

### 7f. Other findings from today's work

- **The PyPI gate cannot detect a mixed environment.** In one measured mix, the former `ccf` 1.0.1 was installed editable beside `ccf-sdk`. `import ccf` resolved to the former tree, while `tools/check_version_stamp.py` passed with rc 0 (`R/review/probe_sec027_mixed_env_gate.out`). A different mix, with two `ccf-sdk` distributions that disagree, is refused with rc 1 (`R/review/probe_sec027_mixed_env.out`). The lane recommends a `packages_distributions` check, which is a new feature and is listed for Dave.
- **C8's obligation is missing from the Protocol docstrings.** The obligation (row 49) is not stated in the `ArtifactSubstrate` or `ArtifactStoreProtocol` docstrings (§3a).
- **`ErasureConsultingStore.scoped`** resolves a URI that names another tenant. This is harmless while hold 0 runs first (§3b).
- **Race, out of scope.** `WorkflowEngine.execute` has no single-flight, and a failed or canceled resumption leaves an attributed row (§4d).
- **SEC-020, carried by the lane.** The seeded plan's empty dimension 1 is a D-IMPL-371 finding. D-IMPL-345 lets the owner at `full` read its own withheld record, which is pre-existing and ruled (§4a).
- **CXRC-G17 is inert.** The pin cannot show the cp-13 change: it skips offline and errors at setup against the estate (§3e; N10).
- **Same-tenant record-shaped bytes on the MCP client lane.** They cross as client-lane artifacts, recorded by a strict xfail. Changing this is a C8-split decision for Dave (§4g; §9).
- **Read-refusal attribution.** It is disclosed but not closed (§4f; §9).
- **Denials read for nobody** (code reading, forged lane). Delivery-boundary denials filed under a different recorder tenant now read for nobody.
- **Erasure-door docstrings** (race docs, out of scope). The docstrings of `runtime/ccf_runtime/erasure/door.py::ErasureRefused` and `runtime/ccf_runtime/erasure/door.py::ErasureDoor.complete` say "nothing was written". That is false for `workflow-refused`: the approval artifact and the write-ahead entries are written first.
- **The 400-character cut** (race docs, out of scope). The door's message cut drops the closing clauses of long refusals; SP §4.13 covers only the erasure door's case.
- **Superseded placeholder files.** `R/lanes/pypi/dist-placeholder-rebuild/` holds the superseded placeholder wheel (`e68dda4f…`) and a rebuilt sdist. The scratchpad's top-level `dist-placeholder/` and `dist-placeholder2/` hold other placeholder builds (wheel sha256 `cd513d8f…`), which the re-review's install scenario used. `dist-placeholder3/` (wheel sha256 `8e64eb36…`) was built by the final short review. None of these may be uploaded (§3h).

### 7g. Environment hazard (ledger 13:10)

- **What is exported.** The session shell exports `PG*`, `FLUREE_*`, `MONGO_*`, `NEO4J_*` and `CO_LENDER_*`, with passwords, pointing at 192.168.4.76. No `CCF_*` variable is set.
- **Who reads them.** Measured: no code in `tests/`, `src/`, `runtime/` or `examples/` reads the bare names; only `tools/dump_cp03_fixture.py` does, and it is run by hand. The estate tests gate on `CCF_CP_*`, which is unset, so they skipped.
- **Residual risk.** libpq's implicit fallback for a DSN with no host.
- **Rule.** Never export `CCF_TEST_*` pointing at `.76`.
- **Effect on results.** None measured: the scrubbed regression at `34a1f6bf` matched the unscrubbed baseline by id (§2).
- **Owner.** This is an environment finding for Dave's shell profile (§9).

### 7h. Carried from baseline §C, with today's status

"Unchanged" means the ledger records no change today. The source column is the baseline's.

**C.1 Capability seam and composition**

| ID | Statement | Source | Status today |
|---|---|---|---|
| R1 | The composition key grammar does not tenant-key the max-TTL resource identity by an enforced grammar | D-GATE-353 (8); D-IMPL-354 (2) | Unchanged |
| R2 | In-process introspection of the module-private issuance table | D-IMPL-354 (1) | Ruled outside the threat model |
| R3 | The authorization lint excludes `examples/` and `tools/` | D-GATE-353 (8) | Unchanged |
| R4 | FastMCP drops unknown arguments | D-GATE-353 (8) | Fixed as SEC353-J-01 (D-IMPL-373). That R4 and J-01 are the same item is inferred (baseline F15) |
| R5 | `producer-unavailable` wording | D-GATE-353 (8) | Unchanged |
| R7 | Vestigial `approval_sink` | D-GATE-353 (8) | Unchanged |
| R8 | Duplicate helper spelling | D-GATE-353 (8) | Unchanged |
| R9 | cp-20's direct register call (SEC353-G-06) | D-GATE-353 (8) | Unchanged |
| R10 | Census of example reds: 25 at v1.0.1; 30 chunk-3 ids now | D-IMPL-355 | Unchanged by id (§2) |
| D-IMPL-354 | Readings (A), (B) and (C) of the composition recipe, and the attestation naming of the composition `decision_id` | D-IMPL-354 | Still Dave's (§9) |

**C.2 Wave 1 (D-IMPL-357, D-GATE-357)**

| ID | Statement | Status today |
|---|---|---|
| D-GATE-357 (1) | The value floor refuses `( ) & % ' ,` and accented characters | Unchanged |
| D-GATE-357 (2) | A conflicted gate wedges permanently, with no primitive to reopen it (1.0.3) | Unchanged (§4d) |
| D-GATE-357 (3) | Narrowing of the conflict population is unproven | Unchanged (§4d) |
| D-GATE-357 (4) / U4 | The estate DSN reached a census log and junit XML; a DSN type that redacts in `__repr__` is 1.0.3 | Unchanged. Estate F8 measured another census redaction miss. Whether the junit half is covered: UNVERIFIED |
| D-GATE-357 (5) | The printed floor pattern cannot be registered under the SDK's own ReDoS guard (deliberate) | Unchanged |
| D-GATE-357 (6) | The floor judges declared positions only | Unchanged |
| D-GATE-357 (7) | ECMA-262 dialect gap | Unchanged |
| D-GATE-357 (8) | The N9 severing reports an `AttributeError` after a mint | Unchanged |
| D-IMPL-357 One | Resume is not atomic | **Partly closed today:** (a) in one process (§3i). Still open: (a) across processes, and (b) (§4d) |
| D-IMPL-357 Five | The registration-time grammar check reads two private standard-library modules | UNVERIFIED; carried here |
| D-IMPL-357 Six | The adopter changelog is not a complete security ledger | UNVERIFIED; carried here |
| D-IMPL-357 Eight | The adoption probe rests on a hand sweep plus a stated gap | UNVERIFIED; carried here |

**C.3 HITL and identity.** All rows are unchanged today. Their sources are in baseline §C.3.

| ID | Statement |
|---|---|
| CR-362-01 | The `IdentityRefused` message is keyed on `key is None`; the widened constructor admits contradictory pairs. Verified, unfixed |
| CR-362-02 | Optional docstring polish |
| SEC-007 severing residuals | The false-edge assertion was not reached; the reason-exactness assertions were not evaluated |
| CR-363-01 | No byte-level signing rule for non-Python signers |
| CR-363-02 | The MCP `attestation` parameter advertises an unconstrained object |
| CR-363-03 | A fragment sentence implies a production replay re-verifier exists |
| CR-363-05 | A malformed attestation gets HTTP 422 but MCP `signed-binding-invalid` |
| CR-363-06 | One `signed-binding-stale` code covers three conditions |
| CR-363-07 | The reference transport's seen-nonce set is unbounded (1.0.3) |
| CR-363-08 | The product-hash compare is pinned at the verifier only |
| CR-363-10 | Door-level sibling controls owed |
| CR-363-11 | E8's "unsigned-only" headline needs its next clause |
| CR-363-12 | Four dead imports |
| CR-363-13 | Two reason changes disclosed only in a commit |
| CR-363-14 | An overstated in-body-import comment |
| CR-363-15 | The new siblings' positive leg mints a second attestation |
| OP-F-06 | Lint polish on `RETIRED_BY_RULING` |
| SEC-006 unbound gate | A routed `hitl-gate` with no `gate_policies` entry fails closed only at runtime |
| A1 | `APPROVAL_GATE_EVENT_CLASS` and `GATE_EVENT_CLASS` are not pinned equal |
| A2 | `AmbiguousPinnedVersionError` escapes untyped (a 500) |
| A3 | No door control for the 409 mapping |
| A5 | Non-narrowing is pinned only on the missing-state axis |
| A6 | An eligibility refusal is audited as "no approval returned" |
| A7 | Per-gate policy selection is unpinned |
| A8 | The register's S1 row assumes a transport `build_local_dependencies` does not bind |
| A9 | A transport that does not stamp `event_state_at_submit` keeps the pre-H2 hole |
| A10 | `Raises` entries missing for `HitlEventRevalidationRefused` |
| O-1 | The attestation check is pinned by one control |
| Escalation eligibility | Enforced on approval gates only; `requested_by` elsewhere is data only |
| Quorum | One approver only; N-of-M is 1.0.3 |

**C.4 Fabric clock.** All rows are unchanged today except D-GATE-358 finding 6, which closed. Sources are in baseline §C.4.

| ID | Statement |
|---|---|
| D-IMPL-365 | Bitemporal as-of read: nothing designed |
| D-GATE-358 f1 | The clock detector's scope and the clock sites are disjoint |
| D-GATE-358 f2 | `__ccf_mode__` is carried, but its lint forbids only LLM imports |
| D-GATE-358 f5 | Two fabric instants per serve, and the write guard judges the later one |
| **D-GATE-358 f6** | **CLOSED today**: the estate fence now compares addresses (§3g) |
| D-GATE-358 f4 | The step-8 guard governs zero writes in the example suite; coverage of the example suite is UNVERIFIED |
| D-IMPL-364 (1) | The register's docs audit cannot tell a resolving citation from a reddening one |
| D-IMPL-364 (2) | B1 tripwire blind spots; the named severing never executed |
| D-IMPL-364 (3) | The `ingest_admitted` route that admission's docstring describes is wired by no composition root |
| D-IMPL-364 (4) | Two stale published sentences |
| D-IMPL-364 (5) | The severing test's docstring is stale |
| D-IMPL-364 (6) | With the peered hop severed, `child_admitted_at` would overstate (latent) |
| D-IMPL-364 (7) | D1's address half does not discriminate; no resolver-level Gate 3 upper-bound control |
| D-IMPL-364 (8) | E1, C1, C4 and B1 controls are weaker than their clauses |
| D-IMPL-364 (9) | Attributability overstatements; refused serves at equal instants share one replay reference |

**C.5 Remaining-rows batches.** All rows are unchanged today. Sources are in baseline §C.5.

| ID | Statement |
|---|---|
| SEC-014-C-01 | The exploit test is blind to a bracketed-umask refactor |
| SEC-014-C-02 | `_make_private_dirs` leaves a wide intermediate directory created by another process |
| SEC-014-C-03 | The staging-file mode is sampled only at `replace` |
| SEC-014-C-04 | Symlinked root behavior under the refuse-by-name ruling: UNVERIFIED |
| SEC-014-C-05 | `SqliteGraphStore` creates the live DB and its WAL/SHM files at the umask |
| SEC-014-C-06 | The refusal class is not picklable |
| F-04 | `src/ccf/products/product.py::open_product` creates the store root's parents wide |
| SEC-015-C-01 | `ci-posture` does not check that a pinned SHA equals its tag |
| CI images | Service images on mutable tags; `fluree/server:4.1.4` is not a digest |
| Concurrent bodies | Not bounded process-wide (a deployment obligation, SP §1.1a) |
| SEC-021-C-01 | `TypedHttpWire.emit` drops the 503 body |
| SEC-021-C-02 | The test reads the private queue |
| SEC-021-C-03 | The LF leg renders a full queue as `InternalError` with tracebacks; the 503 reflects the peer-id header; base64url drops invalid characters |
| SEC-022-C-02 | `observed_peer.tenant_id` is never checked |
| SEC-022-C-03 | The parity test pins field names, not the validators |
| SEC-022-C-04 | No tests for an unknown claims lane or a naive `issued_at` |
| SEC-022 notes | Consult order; `_admit_peered` hides `replayed`/`stale-issuance`; a failed persist refuses the retry; `_PinnedReader` pins on no shipped substrate |
| SEC-024-C-01 | The same class of value-bearing text in HITL webhook, the claude driver, and the HITL routes |
| SEC-024-C-02 | `format_tb` emits source lines; `ExceptionGroup` is not walked |
| SEC-024 (case 3) | Relies on FastMCP `_tool_manager` internals |
| SEC-025-C-01 | Local and MCP legs bind the subject only; `asked_question` is resolver-authored; `GrantBoundChildResolver` is now request-aware |
| SEC-026-C-01 | One level of indirection; fixed target list; `ccf_test_password` in `ci.yml`; stale lint docstring count |
| SEC-028-C-01 | The README leads with the unlocked install |
| SEC-028-C-02 | The installer deny-list misses `$(…)` and `bash -c` |
| SEC-028-F1 carries | Ruled extras are a lint constant; markers evaluate against the running interpreter |
| SEC-013-C-01 | A store handle can hold the lease without minting |
| SEC-013-C-02 | `":memory:"` takes a sidecar lock file in the working directory |
| SEC-013-C-04 | A plain store open runs DDL unleased |
| SEC-013 misc | Unnormalized SQLite identity; `_BOOT_CACHE` |
| SEC-023-C-02 | `admit_entity_claim` skips authority |
| SEC-023-C-04 | `refused_assertions` has no consumer on the paved path |
| SEC-023 exec. C2 | Source ids are self-declared (SP §4.7) |
| SEC-023 exec. C5 | The `perf/synth` ontology |
| SEC-023 exec. C6 | The same source-authority class on `valid_from`, `series_key_attribute`, the similarity corpus attribute and peered records |
| SEC-023 riders | Unapproved proposals; whether they were built is UNVERIFIED (still Dave's, §9) |
| LOW-01-C-01 | The constant-time witness is vacuous |
| LOW-05-C-01 | The endpoint lint misses privately hosted endpoints and runtime-built URLs |
| Engine tenant assert | `engine.execute` never asserts `view.tenant_id == tenant_id` |

**C.6 Harness adapters.** All rows are unchanged today. Sources are in baseline §C.6.

| ID | Statement |
|---|---|
| TP-01 residual | On LangGraph the refusal returns as the tool's ordinary answer |
| TP-02 residuals | `max_turns=None` takes the vendor default; transport options step and allow-rule ordering unmeasured; the owner check was simulated |
| TP-03 note | No single-severing witness at adapter level |
| TP-04 residual | `str(value)` encoding at dispatch; "owed its own entry", still absent (baseline F11) |
| TP-04 behavior | ADK and LangGraph refuse a number for a string-declared argument |
| SEC353-J-01 residual | Nested open maps are not closed; depends on FastMCP privates at `mcp` 1.28.1 |

**C.7 Deadline-close review stack**

| ID | Status today |
|---|---|
| C8 | **CLOSED** (§3a) |
| Panel C1–C7, C9, C10 | FIXED (D-IMPL-375) |
| Final-review I-1, I-2, I-3, P1 | FIXED (FW-1 … FW-4) |
| Final-review M-2: the names resource does not consult the erasure index | OPEN by design; unchanged |
| Final-review M-5 | FIXED (FW-10) |
| Final-review M-10 | OPEN; see §7a |
| Final-review M-1, M-3, M-4, M-6 … M-9, M-11 | FIXED (FW-4 … FW-9). M-11's tenantless-read text was corrected again at `feb12052` |
| N-1, N-2, N-5, N-6 | FIXED; N-1 stays invisible offline (E20) |
| N-3 | FIXED at `minimal`; disclosed above `minimal` (SP §4.10) |
| N-4 | OPEN, disclosed in fragment 374-02 |
| Combined-read I-1 | FIXED |
| Combined-read M-1 … M-3 | FIXED. M-3's "Also" clause remains open (baseline F14; §8) |
| Combined-read M-4 … M-7 | OPEN, disclosed residuals (SP §1.1a, SP §4.11) |
| Not judged: the cryptographic soundness of the erasure door signature and the HITL attestation | Unchanged |

**C.8 Review items outside the 29 numbered rows**

| ID | Status today |
|---|---|
| LOW-01 … LOW-05 | FIXED; carries in C.5 |
| LOW, reserved backend name | Disclosed, not fixed (SP §4.8) |
| LOW, `mcp_stdio` environment | Disclosed, not fixed (SP §4.8) |
| TP-01 … TP-05 | CLOSED; residuals in C.6 |
| SDK-forced pattern 1 (`ProductRequest.subject` had no shape) | Built; residuals in D-GATE-357 (1), (5), (6), (7) |
| SDK-forced pattern 2 (`serve_stdio` pre-authenticated callers) | CLOSED |
| Review §6 (1): is `.76` reachable beyond the LAN? | UNVERIFIED; Dave's (§9) |
| Review §6 (2): has CCF material left GitHub? | UNVERIFIED; Dave's |
| Review §6 (3): risk appetite on D-IMPL-129 and D-IMPL-68 | UNVERIFIED; Dave's (see baseline F7) |
| Review §6 (5): intended deployment topology | UNVERIFIED; Dave's |
| Review §7 item 10: scanning gate | **OPEN, untracked.** `pip-audit`, `bandit`, `gitleaks` and `SECURITY.md` are absent at `d9305603` (ledger) and on the candidate (measured with `git ls-tree` at `421947b8`) |

**C.9 Verified closed** (listed only so that nothing reads as overlooked). Today changes none of these:
- SEC-013-C-03; SEC-021-U1; SEC-022-C-01 and SEC-022-R1.
- SEC-023-C-01, C-03 and P2.
- SEC-013-P1 and SEC-025-U1.
- CR-363-04, -09 and -10 at the verifier.
- D-GATE-353 R6 and R11.
- D-GATE-358 findings 3, 7 and 8.
- The SEC-019 "wave 2" claim, corrected in D-IMPL-375 (but see baseline F5).

### 7i. Residuals of closed rows not listed elsewhere (baseline §A.1)

All are unchanged today.
- **SEC-001 / SEC-003.** Two Tier-0 guards are backstops that cannot currently fail: the event-key comparison and the SEC-003 containment check (D-IMPL-350).
- **SEC-007.** L2 partial admission and the partial-identity `ValueError` are outside the row by ruling (D-IMPL-362).
- **SEC-010.** The retained posture: a caller-supplied `asked_at` is admitted inside the window; the `_decision_instant` fallback (D-IMPL-308); the client-side default (D-IMPL-159).
- **SEC-011.** Gate 2 is assembly-path integrity, self-satisfying on the governed path by design. Gate 1 is unreachable on the governed path; only a direct `run_gates` call reaches it (D-IMPL-364).
- **SEC-017** (D-IMPL-375; REC final-review §3):
  - Roster refusals write no refusal record.
  - An off-roster, unentitled caller no longer gets the entitlement path's recorded envelope.
  - The `ExposedAgent` guard holds at construction only; `model_copy` and `model_construct` bypass it.
  - `replay_record_product_class` is echoed to a rostered caller before authorization. This is unruled.
  - An exception from a deployment's directory propagates unchanged.
- **SEC-019.** A pre-assembly refusal type is returned after assembly, enveloped without lineage (REC progress).
- **SEC-023** (D-IMPL-375; REC panel #29; REC final-review §3):
  - The mint key guards against accidental misuse only, and this caveat is not on the SP.
  - The omission event is not read by replay dimension 2.
  - `spec_address` is set at boot and compared nowhere, so a permissive spec can be booted and stamp views.
  - A `MappingProxyType` authority is not picklable.

## 8. Corrections to the record

| # | The record says | Correct statement | Status |
|---|---|---|---|
| 1 | D-IMPL-375, "Ledger": EX-09 is "unquoted `search_path`, seven modules" | 16 sites in 15 modules (`git grep` at `d9305603`): 15 sites in 14 modules fixed at `5ee6af41`, and the frozen cp-13 site fixed at `4bdaff2a`. The count of seven came from a stale rulings batch, and the review had said "+15" (ledger) | Corrected here |
| 2 | D-IMPL-375, SEC-013: "Residuals, disclosed on the security page §4.6: … the SQLite sidecar lease still opens without `O_NOFOLLOW`" | False at `d9305603`: the page did not mention it (baseline F1). It was first disclosed on the candidate at `feb12052`, in the SP §4.6 SQLite bullet, dated D-IMPL-377 | Disclosed on the candidate; `main` is undisclosed until the merge |
| 3 | D-IMPL-375, SEC-013: "a missing lock directory surfaces as a raw `FileNotFoundError`" | Stale: `src/ccf/graph/leases.py::require_private_lock_directory` refuses a missing directory by name (baseline F1, checked against the code at `d9305603`) | Corrected here |
| 4 | D-IMPL-357 residual One (resume atomicity) is in no carried list after D-IMPL-357 (D-GATE-357's eight are a different set; baseline F3) | Still open. It was surfaced to Dave first (ledger 13:02) and reproduced (13:53). (a) within one process is now fixed (§3i); (b) and (a) across processes stay open (§4d) | Partly closed |
| 5 | The SP §4.10 FW-4 residual list and the `src/ccf/erasure/__init__.py` docstring named "the MCP client lane" as a tenantless read | False: the lane is tenant-scoped, measured at `d9305603` and after the C8 fix (`R/lanes/c8/probe-client-lane-scoping-*.txt`) | Corrected at `feb12052` |
| 6 | SP §4.10, C8: "disclosed rather than changed … the precondition is narrow" | Superseded: C8 is fixed (§3a), and the bullet was rewritten at `705fe210` and `d0a15e7b` | Resolved on the candidate (baseline F8) |
| 7 | D-IMPL-376 (1): the two pins "must demonstrably pass there" | On `main` they pass by construction, because the merge base is HEAD (§2). The measurement shows only that the merge commit is green. The merge changed files in all five pinned frozen specimens, and the cp-03, cp-06 and cp-13 pins never reach their assertion (§2) | Recorded here |
| 8 | D-IMPL-375: the two pins "diff against `main`'s merge base and turn green on merge" | True as measured at `d9305603`, for the reason given in row 7 | Recorded here |
| 9 | D-IMPL-375: C8 is "a design question for Dave" (D-IMPL-345 R-5) | Dave ruled at D-IMPL-376 (6) that disclosure alone is not accepted. C8 is fixed (§3a) | Resolved |
| 10 | D-IMPL-375, "Not run": the estate-gated nodes and the live Fluree, MongoDB and Neo4j legs | Run today at `d9305603` with the results in §6. The re-run on the candidate is pending | Updated |
| 11 | PyPI lane: "`ratchet-main.txt` is missing 3 sites" | Wrong. The 3 are duplicates in the test output (365 entries, 362 unique), and "0 added" stands (ledger) | Corrected; this also resolves baseline F13 |
| 12 | SEC-020 docs claimed "by construction". Fragment 370-20 said the rehydration fix closes the divergence for every empty-finding product | Both overclaimed (review C-1, M-5). The claims were qualified at `d4e06da1` and corrected by the docs pass (`491f0f29`). SP §4.12 is retitled "A withheld subject can still be told from a nonexistent one (SEC-020, open; D-IMPL-376)". Fragment 370-20 now states that a record written before the change still fails replay | Corrected on the candidate |
| 13 | The SP §4 introduction named only SP §4.8's limitations | Fixed at `2dc17656`: it now names SP §4.12 and SP §4.13 | Corrected on the candidate |
| 14 | D-IMPL-374 (2): "the skill grant … gains a declared `products` roster" | The roster is Context Product class names on `TokenGrant.products` (D-IMPL-375 executor ruling (c); baseline F6) | Recorded here; the DECISIONS text is unchanged |
| 15 | D-IMPL-376: "the ledger is 26 of 29 once this branch is on `main`" | It is on `main` at `d9305603`, so the ledger is 26 of 29 (baseline F9) | Recorded here |
| 16 | The D-IMPL-345 design, and the docstring of `runtime/ccf_runtime/authz/delivery_boundary.py::_is_read_refusal`: a forged record is "readable by its forger and by nobody else" | False: a forger names any tenant and principal, and the governed read served such bytes to the tenant they named (§3j) | The docstring was corrected at `37946325`; the decision text is unchanged |

**Baseline §F contradictions, with their resolution status:**

| Baseline | Subject | Resolution |
|---|---|---|
| F1 | SEC-013 residuals: D-IMPL-375 against the SP against the code | Resolved on the candidate (rows 2 and 3). `main` is unchanged until the merge |
| F2 | Which example findings are open | Partly. EX-01 and EX-09 closed; EX-02, EX-07, EX-08 and EX-10 have no closure record (§7a) |
| F3 | The two wave-1 residual rosters differ | Partly. One was surfaced and partly fixed (row 4). Five, Six and Eight are carried here (§7h, C.2) and remain UNVERIFIED |
| F4 | SEC353 gap-ledger counts: "OPEN (6)", nine rows, and "G-01 to G-08" | OPEN. Estate F10 adds that the roster is stale |
| F5 | The SEC-019 "wave 2" claim in `docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md` | OPEN. The file is unchanged on the candidate (measured) |
| F6 | What the SEC-017 roster hangs on | Recorded here (row 14). DECISIONS is uncorrected |
| F7 | D-IMPL-129 after SEC-017 shipped | OPEN: no supersession is recorded |
| F8 | C8 is disclosed but not accepted | Resolved on the candidate (row 6) |
| F9 | No post-merge record of the merge | Resolved by this entry (§2; row 15) |
| F10 | How a truncated index tail is mitigated | OPEN. SP §4.10 still names only filesystem controls; on the page, "append-only" appears only in SP §4.6's replay sentence (measured) |
| F11 | Residuals missing from D-IMPL-375's row lines | Carried here (§7i; C.6, TP-04). TP-04 still has no entry of its own |
| F12 | Open rows absent from the SP | Resolved on the candidate: SEC-027 is in SP §3.1 and SEC-020 in SP §4.12 |
| F13 | Citation ratchet: 365 or 362 | Resolved: 365 entries, 362 unique (row 11) |
| F14 | The SP §4 introduction | Partly. The introduction now names SP §4.12 and SP §4.13. Combined-read M-3's "Also" point, that the introduction does not count SP §4.10's disclosed residuals, is still unaddressed |
| F15 | Whether R4 is SEC353-J-01 | UNVERIFIED, unchanged |
| F16 | Carries that stopped being restated | Partly. D-GATE-358 finding 6 closed today (§3g). The wave-1 residuals and the D-GATE-353 R-series are restated here (§7h) |
| Reconciled | 660 or 743 nodes; red baselines; SEC-022 per gate or per process; SEC-021-U1; CR-363 counts | Unchanged. Today's estate classification is 660 read-only ids plus 93 ids that write locally (§6) |

## 9. Decisions owed by Dave

1. **Merge GO for the candidate.** This merges `dl-377-integ` @ `421947b8` into `main`. The checks on that exact tree, all complete:
   - **Final regression:** chunk 1 5094 passed / 0 failed / 3 xfailed; chunk 2 4120 passed plus the 2 standing reds (citation set identical); chunk 3 exactly `main`'s 30 ids, 1260 passed; every gate green; generated files current (§3 table).
   - **Final short review of the forged-record fix:** no Critical or Important finding; the forged record is refused on both doors; C-2, its full-disclosure oracle and M-4 stay closed; one deferred minor (the provenance check's store configuration is judged per request, not at boot) (§3j, §4f).
   - **Estate affected-subset check:** by static reachability, `govern_dereference` reaches none of the 753 estate ids and the changed fence code reaches none of the 660 read-only ids, so no read-only id needed `.76` again; the 93 write-local ids the fence does reach were re-run on throwaway local containers with identical outcomes (85 passed, 8 xfailed), the four database legs identical (Fluree 294/0), and every `.76` watermark unchanged since 19:50Z; containers stopped and removed (`R/lanes/estate-final/`).

   Changes Dave can revert separately:
   - the provisional SEC-020 merge (`cf86fa5d`, kept by his ruling 2);
   - the cp-13 specimen line (`4bdaff2a`, his 13:20 ruling);
   - the Fluree test fix (`497c6f6d`);
   - the specimen edits under D-IMPL-375 ruling (b), already on `main` (§2).
2. **PyPI upload, new files only.** Upload the placeholder from Dave's account following `R/lanes/pypi/DAVE-PYPI-STEPS.md`: the wheel with sha256 `0e6e1b9e…` and the sdist with sha256 `e24eb5d2…`. Do not upload the earlier `e68dda4f…` and `8d566c80…` files, or any other placeholder build (§7f). The upload closes SEC-027's row (§4b).
3. **Tag only after the release checks.** SEC-029 closes at a tag. D-IMPL-376 (4): "tagging is the final action, not a substitute for them".
4. **Scope of the follow-up batch.** This close-out's own findings exceeded the three-issue cap (ledger). Already ordered: the four SDK documentation and diagnostic defects (§7e). Candidates for Dave to include or defer:
   - the I-2 small fix, which builds the similarity registry from the view read before acquisition. The coordinator offered it;
   - a mixed-environment check in the release gate (§7f);
   - stating C8's name-with-bytes obligation in the Protocol docstrings (§3a);
   - the erasure-door docstrings and the 400-character cut (§4g);
   - the testcontainer DSN that bypasses the fence (§4g);
   - checking the provenance store configuration at boot rather than per request, and saying so in fragment 377-07 (§4g);
   - EX-02, EX-07, EX-08, EX-10 and the census splices (§7a, §7b);
   - estate F3–F14, audit L-6 and the inert specimen pins (§7c);
   - ledger entries for estate families H and E, and a gap id for family D (§6a).
5. **The C8 split for same-tenant record-shaped bytes.** Record-shaped bytes that a principal files on its tenant's MCP client lane still reach that tenant's principals as client-lane artifacts; a strict xfail records this. Closing it means treating record-shaped content on the client lane differently from other client-lane content, a C8-level design choice (§4g).
6. **Read-refusal attribution redesign.** A read-refusal record names the door recorder's tenant. That is disclosed, with a mitigation, but not closed (§4f).
7. **SEC-020 exactness.** Making a withheld subject identical to a nonexistent one for every acquisition shape needs acquisition invoked a second time per question for an identifier that names nothing. That breaks the seam's "exactly once" rule (§4a). The alternative is to accept the disclosed channels and leave the row open.
8. **Cross-process resumption, the outvoted rejection, and `execute` single-flight** (§4d).
   - (a) across processes needs a compare-and-set on `ControlPlaneStateStore`, or a shared claim.
   - (b) needs a claim registry in `src/`, keying by event key, a typed refusal at every submission door, and an amendment to `HITLTransportProtocol`.
   - `WorkflowEngine.execute` has no single-flight, and a failed or canceled resumption leaves an attributed row.
9. **Other items the ledger marks for Dave.**
   - **Pin check.** Is a by-construction pass on `main` enough for D-IMPL-376 (1)? Or should a specimen check against `e561e01f` replace it, and the cp-03, cp-06 and cp-13 pins be made to run (§2)?
   - **C-2's ruling cost.** A cross-tenant auditor flow would need a multi-tenant grant design (§3b).
   - **M-4's ruling cost.** Hierarchical tenant ids must change spelling (§3c).
   - **The published record.** What it may contain (estate F8; §10).
   - **His estate.** The `ccf_dataprep` role can write, and the READMEs give DSNs without read-only (estate F5). Reading the departmental SQLite writes `-shm` files into his tree (estate F6).
   - **His shell.** It exports `.76` credentials (§7g).
   - **Executor rulings recorded today, each with its cost** (ledger):
     - the estate containers on non-default ports;
     - all lanes on opus;
     - the C8 timebox;
     - fixing the Fluree test regression in the close-out;
     - treating C-2 as blocking;
     - not fixing C-1, I-1, I-2, M-5 and M-6.
10. **Still his from the baseline.**
    - D-IMPL-354 readings (A), (B) and (C).
    - SEC353-G-01.
    - The SEC-023 riders.
    - The SEC-017 `replay_record_product_class` echo.
    - Review §6 questions (1), (2), (3) and (5).
    - Recording D-IMPL-129's supersession (baseline F7).
    - Correcting D-IMPL-374's roster text (baseline F6).

## 10. Evidence index

Every path below is a record path. Per the coordinator's instruction, the record holds the session scratchpad's files under the same relative paths. That covers `lanes/`, `integ/`, `review/`, `merge/`, `base/`, `final/`, and the root files `ledger.md` and `chunk.sh`.

**Inputs**
- `records/2026-10-07-d-impl-376-execution/ledger.md`
- `records/2026-10-07-d-impl-376-execution/final/remaining-baseline.md`
- `records/2026-10-07-d-impl-376-execution/lanes/COMMON.md` (the lane rules and the three checks)

**Step 1: the merge**
- `records/2026-10-07-d-impl-376-execution/chunk.sh`: the chunk definitions and the `.76` scrub. The file was last changed at 13:27 MST, after the merge chunks ran. The test counts at `34a1f6bf` (+4, +6 and +105 over the merge) are consistent with unchanged chunk scopes
- `records/2026-10-07-d-impl-376-execution/merge/pins-d9305603.txt`
- `records/2026-10-07-d-impl-376-execution/merge/chunk1-d9305603.txt`, `chunk2-d9305603.txt`, `chunk3-d9305603.txt`, `chunk3-ids-d9305603.txt`, `chunk1.rc`, `chunk2.rc`, `chunk3.rc`
- `records/2026-10-07-d-impl-376-execution/merge/ratchet-d9305603.txt`
- `records/2026-10-07-d-impl-376-execution/base/ratchet-main.txt`, `base/main-chunkD-ids.txt`
- `records/2026-10-07-d-impl-376-execution/merge/gates-d9305603-groupA.summary`, `gates-d9305603-groupB.summary`, `gate-d9305603-*.txt`
- `records/2026-10-07-d-impl-376-execution/merge/regen-surface.txt`, `regen-assemble.txt`, `regen-retire.txt`, `regen-schemas.txt`
- `records/2026-10-07-d-impl-376-execution/merge/push-main.txt`
- `records/2026-10-07-d-impl-376-execution/lanes/ex0109/specimen-pins-5ee6af4.txt` and `records/2026-10-07-d-impl-376-execution/lanes/estate/ESTATE-RESULTS-by-id-d9305603.tsv` (the five specimen pins)

**Combined regressions**
- `records/2026-10-07-d-impl-376-execution/integ/reg-34a1f6bf/`
- `records/2026-10-07-d-impl-376-execution/integ/reg-final/` (`feb12052`, `2b919375`)
- `records/2026-10-07-d-impl-376-execution/integ/reg-c2c341e2/`
- `records/2026-10-07-d-impl-376-execution/integ/reg-2dc17656/`
- `records/2026-10-07-d-impl-376-execution/integ/reg-421947b8/` (chunks 1–3, the gate summaries and the regeneration check on the final candidate)
- `records/2026-10-07-d-impl-376-execution/lanes/estate-final/` (the static reachability record, the write-local re-run, the fence positive control and the final watermark comparison; owner-only files excluded)

**Closures (§3).** All paths are under `records/2026-10-07-d-impl-376-execution/`.

| Item | Record files |
|---|---|
| C8 | `integ/c8-red-at-3709b731.txt`, `integ/c8-green-integ.txt`, `integ/c8-sever-integ.txt`, `integ/c8-sever-old.txt`, `integ/c8-sever-new.txt`, `integ/merge-c8.txt`; `lanes/c8/red-3709b731.txt`, `lanes/c8/probe-client-lane-scoping-d9305603.txt`, `lanes/c8/probe-client-lane-scoping-0d1a5de5.txt`, `lanes/c8/STEP1-what-the-all-tenant-rule-protects.md` |
| C-2 | `integ/verify-C2-d9305603.txt`, `integ/verify-C2-feb12052.txt`, `integ/tenant-red-9f22da65.txt`, `integ/tenant-green-integ.txt`, `integ/c2-sever-integ.txt`, `integ/c2-old.txt`, `integ/c2-new.txt`, `integ/merge-tenant.txt`; `review/probe_c8_cross_tenant_read.out`, `review/probe_c8_cross_tenant_read_portable.main-tree.out`, `review/probe_c8_cross_tenant_read_portable.wt-review.out`, `review/probe_c8_full_disclosure.out`; `review/rr/probe_c8_cross_tenant_read.out`, `review/rr/probe_c8_full_disclosure_v2.out`, `review/rr/sever-hold0.out` |
| M-4 | `integ/tenant-red-6d981036.txt`; `lanes/tenant/severing-m4-red.txt`, `lanes/tenant/severing-m4-sha-before.txt`, `lanes/tenant/severing-m4-sha-after.txt`, `lanes/tenant/severing-m4-diff.txt`; `review/probe_c8_tenant_slash.out`, `review/rr/probe_c8_tenant_slash.out` |
| Forged record | `integ/verify-forged-mcp.txt`, `integ/verify-forged-http.txt`, `integ/forged-red-7960a07e.txt`, `integ/forged-green-integ.txt`, `integ/forged-sever-integ.txt`, `integ/fr-old.txt`, `integ/fr-new.txt`, `integ/merge-forged.txt`; `review/rr/probe_c2_forged_record.out`, `review/rr/probe_c2_forged_record_http.out`, `review/rr/probe_c2_read_refusal_attribution.out`, `review/rr/probe_c2_read_refusal_attribution.main.out`; `lanes/forged/`; final short review: `review/rr2/probe_c2_forged_record.out`, `review/rr2/probe_c2_forged_record_http.out`, `review/rr2/owner-chain.out`, `review/rr2/suite-final-1.out` |
| EX-01 | `integ/ex01-red-at-58288edf.txt`, `integ/ex_01_sparql_value_placement-green-integ.txt`, `integ/ex01-sever-cp04c-integ.txt`, `integ/ex01-old.txt`, `integ/ex01-new.txt`, `integ/merge-ex.txt`; `lanes/ex0109/sever1-*`, `lanes/ex0109/sever2-*`, `lanes/ex0109/census-d930560.txt`, `lanes/ex0109/EVIDENCE-INDEX-5ee6af4.txt` |
| EX-09 | `integ/ex09-red-at-58288edf.txt`, `integ/ex_09_search_path_identifier-green-integ.txt`, `integ/ex09-sever-cp08-integ.txt`, `integ/ex09-old.txt`, `integ/ex09-new.txt`, `integ/ex-green-integ-2.txt`, `integ/merge-ex-cp13.txt`; `lanes/ex0109/cp13-red-65a8967.txt`, `lanes/ex0109/cp13-green-4bdaff2.txt`, `lanes/ex0109/cp13-sever-4bdaff2.txt`, `lanes/ex0109/sever3-*` |
| Fluree regression | `integ/fluree-red-34a1f6bf.txt`, `integ/fluree-green.txt`, `integ/fluree-graph-leg.txt`, `integ/fluree-sever.txt`, `integ/fl-old.txt`, `integ/fl-new.txt`; `lanes/estate/legs/leg-fluree-d9305603.txt` |
| Estate fence and fence2 | `integ/fence-red-at-e706a5e2.txt`, `integ/fence-green-integ.txt`, `integ/fence-sever-integ.txt`, `integ/fe-old.txt`, `integ/fe-new.txt`, `integ/merge-fence.txt`; `integ/fence2-red-01704e94.txt`, `integ/fence2-green.txt`, `integ/fence2-sever-integ.txt`, `integ/f2-old.txt`, `integ/f2-new.txt`, `integ/merge-fence2.txt`; `lanes/fence/`, `lanes/fence2/`; `lanes/estate/safety/fence-positive-control-d9305603.txt`; `review/rr/probe_fence_spellings.out`, `review/rr/probe_estate_fence_tool.out` |
| PyPI (SEC-027) | `integ/pypi-red-at-e4dc3741.txt`, `integ/integ3-targeted.txt`, `integ/integ3-tools-targeted.txt`, `integ/pypi-sever-integ.txt`, `integ/pypi-old.txt`, `integ/pypi-new.txt`, `integ/pypi2-red-ac601ae4.txt`, `integ/pypi2-red-f8150c0b.txt`, `integ/pypi2-green-integ.txt`, `integ/pypi2-sever-classifier.txt`, `integ/cl-old.txt`, `integ/cl-new.txt`, `integ/pypi3-red-e147fb5d.txt`, `integ/pypi3-green.txt`, `integ/pypi3-sever.txt`, `integ/rp-old.txt`, `integ/rp-new.txt`, `integ/merge-pypi3.txt`; `lanes/pypi/DAVE-PYPI-STEPS.md`, `lanes/pypi/dist-placeholder/`, `lanes/pypi/twine-check-d4a4517.txt`, `lanes/pypi/twine-upload-syntax-dryrun-838a921.txt`, `lanes/pypi/dave-step6-download-d4a4517.txt`, `lanes/pypi/scenario-pip-extra-BEFORE-e606e21.txt`, `lanes/pypi/scenario-pip-extra-AFTER-d4a4517.txt`, `lanes/pypi/placeholder-install-refused-d4a4517.txt`, `lanes/pypi/sever5-m1-red-9465e11.txt`, `lanes/pypi/pypi-name-probe-2026-10-07.txt`; `review/probe_sec027_mixed_env.out`, `review/probe_sec027_mixed_env_gate.out`, `review/probe_sec027_mixed_env_pin.out`, `review/probe_sec027_force_reinstall.out`, `review/rr/pip-extra-real.out` |
| Approval-gate race and race docs | `lanes/race/results.txt`, `lanes/race/http_door_a_results.txt`, `lanes/race/followon_results.txt`, `lanes/race/natural_b_sweep.txt`, `lanes/race/natural_b_positive_control.txt`; `integ/race-red-at-19f99c59.txt`, `integ/race-green-integ.txt`, `integ/race-sever-integ.txt`, `integ/rc-old.txt`, `integ/rc-new.txt`, `integ/merge-race.txt`, `integ/merge-race-docs.txt`; `lanes/racefix/out-of-scope-probe.txt`, `lanes/racefix/b-after-fix-e1f7b1d8.txt`; `lanes/race2/a-b-hang-2dc17656.txt`, `lanes/race2/a-restart-2dc17656.txt`, `lanes/race2/c-erasure-concurrent-2dc17656.txt`; `review/rr/race-tests.out`, `review/rr/sever-claim.out` |

**SEC-020 (§4a).** All paths are under `records/2026-10-07-d-impl-376-execution/`:
- `integ/sec020-red-at-01ce0666.txt`, `integ/sec020-green-integ.txt`, `integ/sec020-sever-integ.txt`, `integ/s20-old.txt`, `integ/s20-new.txt`, `integ/verify-C1.txt`, `integ/merge-sec020.txt`;
- `lanes/sec020/probe-shapes-d930560.txt`, `lanes/sec020/probe-shapes-d4e06da.txt`;
- `lanes/s20docs/`: `c1-xfail-8363351.txt`, `sever-c1-marker-removed-8363351.txt`, `sever-c1-instrument-broken-wt.txt`, `c1-replay-ref-name-feb1205.txt`, `record-dim1-feb1205.txt`, `d345-owner-read-feb1205.txt`, `i1-composite-feb1205.txt`, `i2-similarity-registry-feb1205.txt`, `m5-old-record-replay-feb1205.txt`, `m6-persistent-fabric-feb1205.txt`, `population-shapes-feb1205.txt`, `readcost-feb1205.txt`, `timing-feb1205.txt`;
- `review/probe_sec020_*.out`, `review/probe_old_record_replay.out`, `review/probe_old_record_replay_inproc.out`, `review/sever-before-acquisition.out`.

**Estate (§6).**
- Under `records/2026-10-07-d-impl-376-execution/lanes/estate/`: `AUDIT-d9305603.md`, `ESTATE-RESULTS-by-id-d9305603.tsv`, `final-estate-comparison-d9305603.txt`, `container-lifecycle-d9305603.txt`, `netlog/analysis-pass3-d9305603.txt`, `audit/READ-ONLY-ids-d9305603.txt`, `audit/WRITES-LOCAL-ids-d9305603.txt`, `legs/leg-fluree-d9305603.txt`, `legs/leg-mongo-d9305603.txt`, `legs/leg-neo4j-d9305603.txt`, and `safety/` minus anything listed below.
- Under `records/2026-10-07-d-impl-376-execution/lanes/estate-rerun/`: `RE-AUDIT-c2c341e2.md`, `final-estate-comparison-c2c341e2.txt`, `estate-comparison-c2c341e2.txt`, `netlog-analysis-c2c341e2.txt`, `changed-code-exercised-c2c341e2.txt`, `fence-positive-control-c2c341e2.txt`, `container-lifecycle-c2c341e2.txt`.

**Must not be published** (estate F8; D-IMPL-376; the classifier's purpose):
- **Owner-only estate files.** Every file with mode 0600, as counted when this was drafted:
  - under `lanes/estate/`, 24 files: the `*.env` and `*.dockerenv` files; `containers-hhmm.txt` and `containers-started.txt`; `legs/leg-postgres-d9305603.txt`; the three `netlog/*.jsonl` files and `netlog/sitecustomize.py`; nine `run/` files (the three `COMBINED` JSON files and the E08 `.json` and `.log` of each pass); and `sqlite-copy/departmental.sqlite`;
  - under `lanes/estate-rerun/`, 28 files: the two `*.env` files; all four `legs/leg-*-c2c341e2.txt` logs; the two `netlog-*-c2c341e2.jsonl` files; the `run/*.ids` lists and `run/old-ids-sorted.txt`; and the `R-COMBINED`, `R-E08` and `R-L01` run files.

  Estate F8 counts 16 lane files that carry tokens or a password, and the ledger does not name them. Run the credential sweep again before publishing anything from `lanes/`.
- **Estate data.** `lanes/estate/sqlite-copy/` and `lanes/estate/sqlite-exp/` are copies of Dave's departmental SQLite.
- **Proprietary builds.**
  - `lanes/pypi/dist-sdk/` and `lanes/pypi/dist-sdk-2/` hold the SDK wheel and an sdist of about 62 MB that includes the whitepaper.
  - `lanes/pypi/dist-base/` holds an SDK wheel built under the old name.
  - The scratchpad's top-level build, dist and environment folders (`build-*`, `dist-*`, `venv-*`, `edit-*`, `tmp-nb-*`, `main-tree`, and the `wt-*` worktrees) are not evidence.
- **Superseded and review placeholder builds.** `lanes/pypi/dist-placeholder-rebuild/` and the top-level `dist-placeholder/`, `dist-placeholder2/` and `dist-placeholder3/` may be kept as evidence, but they are not the files to upload (§3h).
- **Third-party and environment files.**
  - `lanes/pypi/venv-*` are environments.
  - `lanes/pypi/msccf/` is Microsoft's `ccf` 7.0.18 wheel.
  - `lanes/pypi/pypi-classifiers.html`, `pypi-help.html` and `pep-0541.rst` are saved third-party pages.
