# Reference refresh evidence

## SDK 1.0.2 pass — 18 October 2026

Runtime/example/API pin: `v1.0.2` at `5f85b389efe9e4b1de62e84a5af62ca4b2e12178`. Merged-main documentation: `2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe`. Adoption starting commit: `88ad98a9e614eda41e3ff2b74dfaa9260560b00c`. The previous SDK pin was `3f914416e9e85cb348d20659d80f3c7e2d3685e6`.

The release has **243 modules and 2,105 exported shapes**. Four existing entries changed: `ccf.controlplane.audit`, `ccf.controlplane.registry`, `ccf.controlplane.state`, and `ccf_runtime.workflow.state`; no module was added. All seven appendices were regenerated and compared entry by entry. Runtime source, examples, configuration, lock and public manifest are byte-identical between the tag and inspected main.

Completed locally:

- Nine covenant-review unit checks pass against the clean tagged SDK source; the console run exactly matches `expected-output.txt`.
- All 32 SDK guide mappings and 203 configuration paths exist, as do both supporting producer READMEs; documented `make` targets resolve in dry-run mode.
- All 14 active JSON/YAML files parse. SK-01 declaration excerpts match source configuration, and CP required source-environment names are documented.
- All 25 analysis implementation copies match their guides in Markdown, standalone HTML and master HTML. Historical specification, standard and recipe blocks remain byte-identical to the starting adoption commit.
- Changed Markdown local file links resolve; explicit-port and complete-DSN checks pass. The historical archive and Oct-9 architecture snapshot are unchanged.

The workflow migration guidance is reconciled with D-IMPL-391 and the source security guide; evidence locking follows D-IMPL-390. Security disposition uses post-tag main because SEC-029 closure was recorded after the tag.

Additional local release checks:

- The clean tagged checkout passes the version check: `v1.0.2 == 1.0.2`. David Castillo accepted this local evidence for the release; SEC-029 is closed and no hosted CI rerun is required.
- On Linux/Python 3.12, **150 targeted SDK tests passed and 2 were skipped**. The selection covers approval identity, copied state, queue retirement, leases, artifact concurrency, retained replay, offline SK-01, cp-06C configuration, legacy erasure and HTTP receipt correlation. The skips concern two in-process stores with no durable copy to test. This is not the full SDK suite.
- The original D-IMPL-392 wheel was received and its SHA-256 confirmed as `1d18f600b121268aa58b6438507f682e7b877c78fedf3ea33b2e13e90be51a71`. All 11 supplied release-manifest entries match. Its original 20/20 verification transcript is preserved. Fresh **13/13 installed-wheel checks pass on both macOS and Linux**, covering exact release version, checksum, wheel contents, installed imports/files, adapter provenance and dependency consistency. All 268 packaged Python source files match the release source. Earlier rebuild checks remain supplemental evidence.
- Two separate Linux processes using the installed original release wheel retained and replayed both a served decision and a refusal. The replay process used fresh scratch storage and disabled source access. This exercises the SDK's estate-free fixture, not a live bank door.

Initial runs are retained as diagnostics: macOS recorded 124 passed, 2 skipped, 16 failed and 10 setup errors; the failures encountered the SDK-managed filesystem refusal, and the SK-01 setup errors required the optional Claude Agent SDK dependency. An initial Linux run also lacked Git and that optional dependency. With those prerequisites installed from the release dependency lock, the Linux selection passed as recorded above; the tagged SDK source was unchanged.

No full private-estate qualification, bank-service-account verification, hosted CI or video rerun is claimed. The old development-wheel checker requires a release-aware replacement, supplied with the local distribution. Package-specific transcripts, original release records and the wheel identity are recorded separately in that distribution. Everything remains local; no new bank delivery is recorded.

The dated report below preserves its original observations; its earlier candidate and unreleased statements are historical.

---

## Prior reference refresh — 17 October 2026

**SDK source:** `drcastillo/ccf_code/main@3f914416e9e85cb348d20659d80f3c7e2d3685e6`  
**Previous technical baseline:** `8193c60780eff21d624c48f78d655dfc6dad0131`  
**Adoption starting head:** `2990c8b3ebc52af7e0da610971669fc242af9e2c`

## Comparison

| Measurement | Result |
| --- | --- |
| SDK commits after previous technical pin | 44 |
| Public manifest modules | 240 → 243 |
| New public modules | 3 |
| Changed existing manifest entries | 7 |
| Current vs qualified v1.0.1 modules | 243 vs 217; 26 added |

New modules are `ccf.replay.evidence`, `ccf.replay.inspection`, `ccf_runtime.cli.evidence`. Changed existing entries are `ccf.controlplane.artifacts`, `ccf.products.child_resolver`, `ccf.products.composite`, `ccf.products.contract`, `ccf.products.product`, `ccf.products.refusal`, `ccf.products.resolver`.

The [public index](PUBLIC_SURFACE_INDEX.md) and seven [API appendices](api/README.md) are generated from the pinned [surface manifest](https://github.com/drcastillo/ccf_code/blob/3f914416e9e85cb348d20659d80f3c7e2d3685e6/docs/surface/v0.2-surface.json). Existing category membership is preserved, with the new replay and runtime modules added to their matching categories.

## Source reconciliation

Reviewed the complete SDK comparison and current source/change records for D-IMPL-383 (durable root, inspection, source-free opening, source outage), D-IMPL-384 (Fluree 4.2.4), D-IMPL-385 (agent identity in dimension 4), D-IMPL-386 (example freeze lifted), D-IMPL-387/388 (scoped security changes) and D-IMPL-389 (composite replay, including zero admitted children).

SK-01 documentation is grounded in its README, findings, configuration, environment, question/projection/vocabulary artifacts, deployment mapping, producer/run/acquisition code, tool inspection glue, over-reach variant and offline/estate tests. The Standard v0.3 section structure was read to build the analysis; no missing SK-01 final spec is invented. The source's estate results are attributed as historical measurements, not newly run results.

Security disposition comes from the pinned [open-items register](https://github.com/drcastillo/ccf_code/blob/3f914416e9e85cb348d20659d80f3c7e2d3685e6/packaging/bank-controlled/OPEN-SECURITY-ITEMS.md), [SEC-030 implementation](https://github.com/drcastillo/ccf_code/blob/3f914416e9e85cb348d20659d80f3c7e2d3685e6/runtime/ccf_runtime/mcp/egress.py) and tests, with separate source/candidate/delivered status. No universal reader-integrity or all-surfaces opacity claim is inferred.

## Documentation checks

- Checked current API module/export/shape coverage against the committed manifest.
- Checked SK-01's YAML excerpt against the actual configuration, including class, producer, policy, agent and grant identities; checked the over-reach variant changes only the skill block.
- Checked changed Markdown links against repository paths, including commit-pinned SDK references, and checked new tables/fences and local heading targets.
- Scanned all active Markdown/text and all 26 existing HTML reading editions for stale Fluree version instructions. Current setup instructions use **4.2.4**. CP-05's embedded older version is retained as quoted historical evidence with a current correction in Markdown, standalone HTML and the master collection.
- Added the SK-01 HTML reading edition and included it in the master collection; retained historical source excerpts and original pins.
- Confirmed no `archive/` path is included in the documentation change set.

## Follow-up example/configuration audit

Starting from adoption `e94b83d`, the follow-up uses the **same** SDK main commit, `3f914416`. The [inventory](../../examples/SDK_BASELINE.json) covers 32 SDK example guides, their YAML configuration files, two supporting producer trees and the local covenant demonstration. The SDK checkout remains unchanged.

Verified in this follow-up:

- All active adoption YAML and JSON files parse; all inventoried SDK README/configuration paths and referenced test/program paths exist.
- Documented SDK example Makefile targets resolve in a dry run; CP source environment names are present in the corresponding runbooks. CP-22's inherited CP-21 names are explicit.
- The SK-01 YAML excerpt matches the current source configuration.
- All 25 Markdown implementation excerpts and their standalone/master HTML copies equal their refreshed guides. The embedded specification, standard and recipe text is byte-for-byte unchanged from the preceding adoption commit.
- Changed local Markdown links resolve; current example exports use explicit ports and complete DSNs.
- The local covenant-review demonstration's console output matches `expected-output.txt`; its evidence export identifies `3f914416`; all **9 existing unittest checks pass** on Python 3.12 with the example's pinned direct dependencies.
- `git diff --check` passes; no archive or synced project source was edited.

These are documentation/configuration checks plus the local demonstration's tests. The database-dependent CP/S1/DR/SK/harness examples, full SDK suite and Fluree backend leg were not executed. There is no restored estate in this workspace. The original refresh scope below describes the preceding pass.

## Scope limits

This is source/documentation reconciliation. No SDK source was written, SDK tests run, model called, live database queried or delivery replaced. The API manifest is the committed public surface, not a newly executed runtime introspection. The Oct-9 architecture inventory and CP source excerpts keep their dated evidence; current overlays document subsequent behavior. The source register's candidate-wheel install and example-test results are not independently revalidated here.
