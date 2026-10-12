# Example amendments — 2026-10-11 ("make examples actually run", Dave 14:51 MST)

One line per compatibility repair: example · file · what changed · why · finding id. Historical
transcripts and findings are preserved; nothing here changes a governed value, threshold, expected
business result or security assertion.

- s1-00-companies-over-revenue · deployment.py `read()` · reads every Control Plane key from `booted.keys` (placed `{tenant}/…` strings) instead of bare section names, and hands the same placed keys to the resolver · the loader places keys under the tenant (D-IMPL-354); bare read raised `KeyError: 'request_contract'` · SEC353-G-07
- s1-00-companies-over-revenue · produce.py · `FileArtifactStore(..., write_kinds=WriteKinds.declare({replay, query-pin, admitted-child: ReplayMint}))`, s1-01's shape · `write_kinds` became a required argument (D-IMPL-353 §1.2) · G1-S100-F02
- s1-00-companies-over-revenue · ccf_config.yaml · added `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue's values, labeled illustrative) · undeclared boundary refuses every serve (D-IMPL-358 ruling 11) · SEC358-G-01
- s1-00-companies-over-revenue · README.md §1 · labeled the old output block historical, showed the current governed refusal for the default question, and documented the `--as-of now` command that serves · pinned 2026-08-01 instant is outside the bound and past TTL on Postgres (demonstration serve instant is dev-substrate only, D-IMPL-378 C1) · G1-S100-F03
- hw1-harness-clients · client_anthropic.py · waits on `ClaudeSDKClient.get_mcp_status()` until the door's server reports `connected` (refuses by name on failed/needs-auth/disabled) before sending the query · bundled CLI 2.1.220 connects MCP servers without blocking; the live model was advertised no tool and the leg failed "the agent never reached the door" · G1-HWC-F01
- hw1-harness-clients · client_anthropic.py · appends the tool's arguments (the question's seven plus the opaque `request`, encoded exactly as `client_adk.py::encoded_request`) as JSON after the declared instruction; trimmed comments to stay within the README's 300-line budget · under `--live` a real model had no argument values and could not infer the opaque `request` (door refused "Invalid JSON"); the offline stand-in hid it · G1-HWC-F02
- dr-01-replay-a-governed-determination · replay.py · reads the record through the opened product's own `opened.artifact_store` instead of constructing a second `FileArtifactStore` on its directory · `FileArtifactStore` now requires `write_kinds` (TypeError at both call sites); the opened product already holds the declared store · G1-DR01-F01
- dr-02-package-a-context-product · ccf_config.yaml · added `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1's values, labeled illustrative) · undeclared boundary refused every question (`temporal-boundary-undeclared`); the pinned 2026-09-07 instant still refuses `asked-at-outside-temporal-bound` because the paved road cannot declare a demonstration serve instant (G1-SDK-01) · SEC358-G-01
- peer-cp-20-co-lender · ccf_config.yaml · added `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1's values, labeled illustrative; run.py asks as of now) · every documented question refused `temporal-boundary-undeclared` · SEC358-G-01
# Example amendments — 2026-10-11 (Dave's Tuesday GO: compatibility repairs authorized)

One line per repair: example · file · what changed · why · finding id.

- cp-03-canonical-obligor-financial-spread · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` with the illustrative-calibration disclosure (hw1-companies-over-revenue precedent values) · every governed serve refused `temporal-boundary-undeclared` (D-IMPL-358 ruling 11 made the declaration mandatory; the tree predates it) · SEC358-G-01 / G2-F-02
- cp-04-canonical-corporate-family-tree · ccf_config.yaml · same `temporal_boundary:` declaration · same reason · SEC358-G-01 / G2-F-02
- cp-06-canonical-collateral-and-setoff-coverage · ccf_config.yaml · same `temporal_boundary:` declaration · same reason · SEC358-G-01 / G2-F-02
- cp-04-canonical-corporate-family-tree · tests/examples/test_cp_04_canonical_output.py (CFC-G05) · the dimension-2 key assertions read the tenant-placed keys (`{tenant}/request_contract`, `{tenant}/policy`) instead of the bare names; the assertion (request contract recorded in dimension 2, dimension 2 strictly wider than the policy) is unchanged · D-IMPL-354 places every manifest key under the tenant · SEC353-G-07 class / G2-F-03
- cp-06-canonical-collateral-and-setoff-coverage · tests/examples/test_cp_06_canonical_output.py (CSCC-G11) · `{tenant}/request_contract` instead of `request_contract` in the dimension-2 assertion · same · SEC353-G-07 class / G2-F-03
- cp-03-canonical-obligor-financial-spread · tests/examples/test_cp_03_canonical_output.py (OFC-G09) · the shadow probe reads `booted.artifacts[booted.keys.request_contract]` instead of the bare `"request_contract"`; the asserted refusal ("shadow") is unchanged and now observed again · same · SEC353-G-07 class / G2-F-03
- G3 · cp-07, cp-08 · `deployment.py` · read the request contract by `namespaced_key(tenant=booted.tenant_id, key="request_contract")` instead of the bare key · artifacts are tenant-placed since D-IMPL-354 · finding G3-F-01 (SEC353-G-07 class)
- G3 · cp-07, cp-08 · `deployment.py` · pass `served_at=datetime.now(UTC)` to `ReferencePolicyConstraintResolver.resolve()` (the live serve instant, as the SDK's own door does) · `served_at` became a required keyword under D-IMPL-358 step 5 · finding G3-F-02
- G3 · cp-07 (+ `server/serve.py`), cp-08, cp-09, cp-10, cp-11, cp-12, cp-13 · `produce.py` · `FileArtifactStore(..., write_kinds=WriteKinds.declare({"ccf.replay-record", "ccf.graph-query", ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,)}))` · `write_kinds` became required (D-IMPL-353 §1.2); the three classes are the ones the resolver files, per the s1-01 pattern · finding G3-F-03
- G3 · cp-07, cp-08, cp-09, cp-10, cp-11, cp-12, cp-13 · `produce.py` · every manifest key handed to `build_governed_resolver` (product_class, request_contract, operator parameters, policy, half_life, debt_profile) placed under the tenant with `namespaced_key` · D-IMPL-354 tenant placement; the bare key resolved no artifact (`ProductNotResolvable`) · finding G3-F-01
- G3 · cp-07, cp-08, cp-09, cp-10, cp-11, cp-12, cp-13 · `ccf_config.yaml` · appended a `temporal_boundary:` section (max_past_seconds 3600, permitted_clock_skew_seconds 0 — hw1-companies-over-revenue precedent, labeled illustrative) · an undeclared boundary refuses every question (`temporal-boundary-undeclared`, D-IMPL-358 ruling 11; coordinator-authorized class) · finding G3-F-04
- G3 · cp-13-canonical, cp-14 · `ccf_config.yaml` · appended the same `temporal_boundary:` section (3600 / 0, illustrative, hw1 precedent) · paved-road config refused every question `temporal-boundary-undeclared` · finding G3-F-04
- G3 · cp-13-canonical · `run.py` line 138 · print `governing_text.documents_in_force` / `documents_not_yet_governing` directly instead of `len()` of them · the example's own projection emits counts (ints), so every served run crashed with `TypeError: object of type 'int' has no len()` after printing SERVED · finding G3-F-05 (example defect)
- G3 · cp-08 · `README.md` "Run it" · bare `python …` / `pytest …` replaced by `PYTHONPATH=src:runtime:examples/cp-08-covenant-in-force-as-of .venv/bin/python …` and `.venv/bin/python -m pytest …`; dropped the stale "18 tests" count (module defines 20) · this repo has no `python` on PATH and the run needs the example dir on the path (example_delivery.md §4) · finding G3-F-06
One line per repair: example · file · what changed · why · finding id. Historical evidence is preserved; nothing is deleted.

- cp-15-kyc-refresh-beneficial-ownership · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-16-abs-securitization-surveillance · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-17-mnpi-wall-enforcement · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-18-ib-opportunity-synthesis · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-19-aml-typology-match · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-20-syndicated-lending-co-lender · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-21-large-exposure · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-23-portfolio-early-warning · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-24-portfolio-what-if · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue precedent values, disclosed as illustrative) · D-IMPL-358 refuses every governed serve for a tenant with no declared boundary (`temporal-boundary-undeclared`); the tree predates it · G4-F-02
- cp-15-kyc-refresh-beneficial-ownership · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-16-abs-securitization-surveillance · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-17-mnpi-wall-enforcement · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-18-ib-opportunity-synthesis · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-19-aml-typology-match · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-21-large-exposure · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-23-portfolio-early-warning · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-24-portfolio-what-if · server/serve.py · `open_door(..., token_verifier=...)` → `open_door_with_verifier(...)`, and each `TokenGrant` scoped `tenants=frozenset({opened.tenant_id})` (the one-tenant door case SEC-018 documents; narrows, never widens) · D-IMPL-353 §4 removed the `token_verifier` parameter from `open_door` (TypeError at door boot) and SEC-018 made an unscoped grant open nothing · G4-F-03 (partial: the door still fails at `entitle()`, G4-F-04, not repaired)
- cp-24-portfolio-what-if · README.md · the SCENARIO variation re-quoted as `SCENARIO="--scenario '{\"rate_shift_bp\":300,...}'"` · the documented form lost its JSON double quotes in the make recipe's shell (`JSONDecodeError: Expecting property name enclosed in double quotes`) before the SDK was reached · G4-F-07

## SQLite identity-lock migration (lane-tue-security; P1 (a), Tuesday GO item 4)


Authority: Dave, 2026-10-11 14:51 MST (the Tuesday delivery GO): *"Compatibility repairs to example configuration,
clients, launchers and README commands are authorized, including previously frozen runnable specimens. Record the
amendment and preserve historical evidence. Do not weaken security assertions or change intended business results to
manufacture a pass."*

Cause: from the commit that made a SQLite file writer mint only under a declared identity lock
(`SqliteGraphStore.writer_lease`, P1 (a), `D-IMPL-378`), every direct SQLite boot that declared no lock directory is
refused `WriterLeaseRequired`. Examples that boot through the standard product boot (`open_product`, a
`ccf_environment.yaml`) need nothing: the SDK supplies its managed directory. Each example below booted SQLite
directly, so it now declares a private (`0o700`) per-run lock directory. No business result, threshold, query or
assertion changed. The history of each example before this amendment is in git, unchanged.

| Example | What changed |
| --- | --- |
| cp-00, cp-01, cp-02 | `backends.yaml` declares `writer_lease_lock_dir: {lock_directory: .ccf-writer-locks}`; `deployment.py::connection` composes it as a private directory under the run root. |
| cp-03, cp-04 | The same, as a new value source beside `from_env` and `per_run: path`. |
| cp-05 | The same, in `deployment.py::connection`. |
| cp-06 through cp-13 (cp-06, cp-07, cp-08, cp-09, cp-10, cp-11, cp-12, cp-13) | The same, in `deployment.py::connection`. |
| s1-01 | `artifacts/backends.yaml` declares `writer_lease_lock_dir: {per_run: lock_directory, filename: .ccf-writer-locks}`; `deployment.py::_per_run` interprets the new rule. |
| dr-01 | `replay.py` reopens the question's substrate with the product's own SDK-managed directory (`OpenedProduct.writer_lock_directory`). |
| hw1-companies-over-revenue | `deployment/binding.yaml` declares `writer_lease_lock_dir: {path: .ccf-writer-locks}`; `runner/seed.py` and `server/compose.py` create it; `.gitignore` lists it. |
| hw1-harness-clients | `runner/drive.py` creates the copied deployment's lock directory before seeding, and does not copy one. |

**Frozen specimens with a diff gate.** cp-03, cp-04, cp-05, cp-06 and cp-13 are pinned by `tests/examples/specimen_base.py`
gates that require no diff against the branch point (`CFC-G09` and its siblings). The gates are not disabled. They read
red on a branch carrying these amendments and read the specimen as untouched once the amendment is on `main`.

## Round 2 — client Hello World (`01-client-developer`), 2026-10-11 (Dave 16:23 rulings)

- hw1-companies-over-revenue · tests/examples/test_hw1_two_transports.py `NOT_COPIED` (+ `.ccf-writer-locks` in test_client_example_purity.py) · the temporary copy now excludes `graph.sqlite3*` and `.ccf-writer-locks`, matching `hw1-harness-clients/runner/drive.py::COPY_IGNORE` · the narrower `graph.sqlite3` / `graph.sqlite3-*` pair let the SDK's dot-suffixed store marker, store-creation lock and writer lease ride from a developer's documented run into every test copy: 8 tests errored "the copy carries a graph" after `make example-hw1` (measured on b279ecf8). Tests own their tmp_path copies and seed them; nothing in the developer's store is deleted · G1-HW1-F01 (§B.4, test/example defect)
- hw1-companies-over-revenue · deployment/.gitignore · `graph.sqlite3.ccf-*` listed beside `graph.sqlite3` so the documented run leaves `git status` clean; NOT the contamination fix (that is the line above) · G1-HW1-F01
- hw1-companies-over-revenue · new tests/examples/test_hw1_expired_question_refusal.py · the expired-question case as an ordinary passing test (ruling 1): both documented commands with only `--as-of` moved refuse `asked-at-outside-temporal-bound` and `ttl-bounds` by name, exit 1, no content address; instants read from the deployment's own `demonstration_serve_instant`, `temporal_boundary` and `product_ttl_seconds` · ruling 1 "Keep an expired-question case as a normal test that asserts the correct refusal"
- hw1-companies-over-revenue, hw1-harness-clients · README.md · prerequisites (`make venv`, nothing else), what varies per run (replay address; harness temp paths), actual stderr of the MCP leg, the expired-question refusals, the harness legs' measured expected output (`c38d30f2…9197`, scenario-rows) vs the live legs (`a8335bb4…2df4`) · step 5 of the priority amendment
## Round 2 — the producer Hello Worlds (s1-00, s1-01), Dave's rulings 1, 5 and 6 (2026-10-11 16:23 MST)

One line per repair: example · file · what changed · why · finding id. Historical output is kept in each README under a dated heading; nothing here changes a governed value, threshold, business result or security assertion.

- s1-00-companies-over-revenue · consume.py · with no `--as-of`, the question is asked as of NOW (the driver reads the clock once, to the second) instead of the pinned 2026-08-01 · the pinned default was refused `asked-at-outside-temporal-bound` on every run, and the SDK's demonstration serve instant cannot be declared here because it is admitted only on the SDK's development substrates (D-IMPL-378 C1 decision 6 (b)) and this graph is Postgres (ruling 1: a default command must ask a valid question) · R2-S100-F01
- s1-00-companies-over-revenue · consume.py · a refusal prints its key only when it names one (was `— None`), the hw1 client's own rule · cosmetic, client output · R2-S100-F02
- s1-00-companies-over-revenue · produce.py · `assemble_and_serve` takes an optional `serve_clock`, passed to the SDK's `admission_clock` seam only when supplied (s1-01's `D-IMPL-358` step-13 shape); `consume.py` never passes it · the served-path tests need a controlled time setup (ruling 6) · R2-S100-F03
- s1-00-companies-over-revenue · deployment.py · comment on `DEFAULT_ASKED_AT` says it is the dated scenario instant the tests ask under a controlled serve clock; value unchanged · same · R2-S100-F03
- s1-00 · tests/examples/test_s1_00_output.py · the nine `xfail(strict, raises=KeyError)` marks (SEC353-G-07) REMOVED, not relabeled; served-path tests ask the dated scenario (2026-08-01) on a serve clock held at the question's instant, so every original assertion runs; two new ordinary passing tests on the real clock — a question asked now is served, and the 2026-08-01 question is refused `asked-at-outside-temporal-bound`; plus an anchor-equality check · ruling 6 · R2-S100-F03
- s1-00 · tests/examples/test_frozen_family_quarantine.py · roster 12 → 3 (cp-00, cp-01 unchanged); new `test_the_released_s1_00_tests_carry_no_expected_failure_mark` asserts the nine still exist and carry NO xfail mark, so a relabeled quarantine goes red (proved: adding one turned it red) · ruling 6 + ruling 3 (update specimen checks explicitly) · R2-S100-F03
- s1-00-companies-over-revenue · README.md §1, §2, §4, §5 · prerequisites; the measured output with run-varying values marked; how to reproduce an address; the provokable refusals; the test commands; the old output kept under "History"; §5's claim "HW-2 reuses this product unchanged" corrected to what is measured (same class and request contract, a different deployment and data; the hw1 client cannot reach this example) · ruling 1 + Dave's step 4/5 · R2-S100-F01, R2-S100-F04
- s1-01-hello-context-product · README.md · the reproducible disposable Fluree command (`--name ccf-s1-01-fluree --memory 4g`, readiness check, `docker stop`), `python` → `.venv/bin/python` (no `python` on PATH), the measured output with the per-answer replay addresses marked, the test commands; the fourth (ad-hoc) question now asks as of now — its pinned 2026-08-01 instants were refused `ttl-bounds` (an ad-hoc question has no declared service period and is served on the real clock) · ruling 1 + ruling 5 · R2-S101-F01, R2-S101-F02
- Makefile · comments on `example-s1-00` (asks as of now; run-varying values) and `example-s1-01` (the disposable server command); recipes unchanged · step 5 · R2-S100-F01, R2-S101-F01
## SDK round 2, item 1 — several principals on the standard door (G4-F-04), 2026-10-11

Dave, 16:23 MST, ruling 4. `server/serve.py::entitle` registered a three-grant `ProductEntitlementPolicy` by hand,
which D-IMPL-353 refuses (`CapabilityBypassError`). The SDK now takes the policy as a declared `product_entitlement:`
section in `ccf_config.yaml`, registered by composition at `open_product`; the standard door composes over it.

| Example | What changed |
| --- | --- |
| cp-15 | `ccf_config.yaml` declares `product_entitlement:` with the three grants `entitle()` used to register (PRIN-KYC-004 kyc-analyst, PRIN-COV-001 coverage-banker, PRIN-RES-002 research-analyst — the roles the estate's `ccf_v2.principal.perspective` names); `server/serve.py::entitle` and its two calls are removed. PRIN-TRD-003 stays undeclared (the negative control). Recorded friction: each granted role is now stated in the config AND read from the estate; a disagreement is refused `product-role-ungranted`, never served. |

Other paved-road doors (cp-16..24; cp-07's bespoke door) adopt the same section; not changed in this round.

## SDK round 2, item 3 — cp-14 declares its agent's grants, 2026-10-11

Dave, 16:23 MST, ruling 4. cp-14 refused `GrantNotInForce` at open for all five skills: since D-IMPL-353 the paved road
cannot grant and no example-reachable door could. The SDK now takes a `grants:` list in `ccf_config.yaml`; `open_product`
requests each through the grant ledger at composition (tier-1 regime check, tier-2 approval rule, audit and state records).

| Example | What changed |
| --- | --- |
| cp-14 | `ccf_config.yaml` declares `grants: [spread-ask, family-ask, exposure-ask, collateral-ask, covenant-ask]` — exactly its five `skills:`, one per required child class. Open now succeeds with the five in force (`grant_effective`, actor `ccf.composition-root`). Its served question still needs its producers: `door-cp-05-credit-exposure-rollup` does not boot (`examples/cp-05-credit-exposure-rollup/deployment.py` `FileArtifactStore` lacks `write_kinds` — the cp-05 owner's compatibility repair). |

## SDK round 2, item 2 — cp-20's request-scoped optional child, 2026-10-11

Dave, 16:23 MST, ruling 4. cp-20's `build_children=` factory hand-registered its agent and skill and requested its grant,
which D-IMPL-353 refuses (`CapabilityBypassError` at open, federation on or off). The SDK now derives a declared chain
for a `build_children=` factory (`ConsumerContext.derived_children`).

| Example | What changed |
| --- | --- |
| cp-20 | `ccf_config.yaml` declares `skills: {peer-position-ask}`, `agent: {syndicate-co-lender-composer}` and `grants: [peer-position-ask]` (the agent and skill `artifacts/consumer-chain.yaml` carried, now derived by the SDK); `deployment.FederatedChildren.factory` wraps the derived resolver and registers nothing (`_registered_chain`, `_pinned_ref` and the ledger code removed); `produce.py` passes `questions=children.question`. The `include_federated` switch, the envelope check before dispatch, and the requirement's `required: false` + `absence_treatment` are unchanged. `artifacts/consumer-chain.yaml` is kept as the historical record. Not changed here: `tests/examples/test_cp_20_co_lender.py`'s own reader still builds `FileArtifactStore(root=...)` without `write_kinds` (15 errors, the cp-20 owner's test repair). |
