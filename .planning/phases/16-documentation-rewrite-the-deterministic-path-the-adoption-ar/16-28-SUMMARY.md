---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 28
subsystem: controlplane
tags: [pydantic, artifact-contracts, d-impl-136, deployment-config, ccf_config.yaml]

# Dependency graph
requires:
  - phase: 16-27
    provides: "ProductDiscovery.audiences (D-IMPL-135), the surface-fragment reconciliation pattern this plan repeats"
provides:
  - "DeploymentConfig(VersionedArtifact) — the closed-world, fifteen-field ccf_config.yaml document contract"
  - "DEPLOYMENT_CONFIG = ArtifactClass(class_id=\"ccf.deployment-config\", contract=DeploymentConfig), registered and manifest-addressable"
  - "the committed docs/schemas/ccf.deployment-config.json authoring schema"
  - "HW1_SINGLE_FILE_DOCUMENT — the transcribed HW-1 fixture exported for 16-29/16-30 reuse"
affects: ["16-29 (the derivation loader)", "16-30 (boot + HW-1 equivalence proof)", "16-31 (HW-1 conversion)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "model_validator(mode=\"before\") reading reserved names from cls.model_fields, so a refusal message's reserved-name list cannot drift from the declared fields"
    - "open-mapping section fields (Mapping[str, Any]) at the document layer, deferring validation against the eventual SDK contract to the loader that materialises each section"

key-files:
  created:
    - tests/deployment/test_config_document.py
    - docs/schemas/ccf.deployment-config.json
    - docs/surface-changes/16-28-deployment-config-document.md
  modified:
    - src/ccf/controlplane/artifacts.py
    - src/ccf/deployment/classes.py
    - tests/deployment/test_class_lookup.py
    - docs/SURFACE-CHANGES.md
    - tests/controlplane/test_artifact_roundtrip.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "backend_secrets and survivor_cap accepted per D-IMPL-138(b) — field parity with DeploymentManifest, not a judgement call this plan defends"
  - "resolution_spec_key and policy_bundle_key kept as overridable None-default pointer fields per design spec §6.3, cited rather than re-argued"
  - "SDK-owned and adopter-owned sections both typed as open mappings at the document layer; validation against real SDK contracts deferred to 16-29's materialisation"

requirements-completed: [DOCS-23]

# Metrics
duration: ~70min
completed: 2026-08-15
---

# Phase 16 Plan 28: DeploymentConfig — the closed-world single-file authoring document Summary

**`DeploymentConfig`, a fifteen-field `VersionedArtifact` for `ccf_config.yaml` that refuses unreserved top-level keys by name (all offenders, one message) and holds `policy`/`request_contract` bodies uninterpreted — registered as `ccf.deployment-config`, schema-exported, and surfaced — with zero changes to `DeploymentManifest`, `ManifestEntry`, or the multi-file loader.**

## Performance

- **Started:** 2026-08-15 (session start; BASE measured fresh per instruction)
- **Completed:** 2026-08-15T15:21:11Z
- **Tasks:** 2 planned, both complete, plus two out-of-declared-scope fixes required by the plan's own `<verification>` block
- **Files modified:** 6 modified, 3 created (see `key-files` above)

## BASE, measured fresh

`39a9a05feea59175c5674dba814fc944682db0fa` (branch tip at start). The plan's own `<verification>` block asserts a "nineteen-failure BASE set" carried over from `16-27`'s plan brief. **That is stale.** `16-27`'s own SUMMARY already recorded the correct measurement at its `BASE` (`b23f601`, one commit before `39a9a05`): six intervening commits, most explicitly `868aa4e`, closed all nineteen before `16-27` even started. Measured again here, independently, at this plan's own `BASE`:

```
PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/ -q
3208 passed, 118 skipped, 105 warnings in 380.63s (0:06:20)
```

**Zero failures.** Treated as the regression floor for this plan's own verification, per the orchestrator's instruction and consistent with `16-27`'s precedent — not the plan text's stale nineteen.

## Accomplishments

- `DeploymentConfig(VersionedArtifact)` in `src/ccf/controlplane/artifacts.py`: fifteen fields (inherited `semver`; six `DeploymentManifest`-mirrored deployment-level fields; eight reserved sections, `product_class` required, the rest optional and `None`-by-default). A `model_validator(mode="before")` collects every unreserved top-level key and refuses with one message naming all offenders and every reserved name, built from `cls.model_fields`.
- `DEPLOYMENT_CONFIG = ArtifactClass(class_id="ccf.deployment-config", contract=DeploymentConfig)`, registered in `SDK_ARTIFACT_CLASSES` — `resolve_artifact_class("ccf.deployment-config")` returns it by identity.
- `docs/schemas/ccf.deployment-config.json` committed via `make schemas`: 15 properties, `additionalProperties: false`.
- `docs/surface-changes/16-28-deployment-config-document.md`: claims exactly the two names this plan added (`DeploymentConfig`, `DEPLOYMENT_CONFIG`), reconciled in both directions against `tools/dump_surface.py --report` and `tools/assemble_surface_changes.py::parse_entries`.
- 33 new tests in `tests/deployment/test_config_document.py` covering every `<behavior>` bullet plus the threat register's T-16-28-02 negative control, including `HW1_SINGLE_FILE_DOCUMENT` — the full HW-1 deployment transcribed by hand into one document, exported for `16-29`/`16-30` reuse.
- `DeploymentManifest`, `ManifestEntry`, and `src/ccf/deployment/manifest.py` are untouched — confirmed byte-identical (`inspect.getsource` lengths 10561/7336, matching BASE exactly) and empty `git diff`.

## Task Commits

1. **Task 1: `DeploymentConfig` — the closed-world authoring document** - `52f4d03` (feat)
2. **[out-of-scope fix, required by Task 2's own edit]** - `a5a26af` (fix) — citation repair in `.planning/REQUIREMENTS.md`
3. **Task 2: Make the document addressable, schema-exported, and claimed** - `4544a3a` (feat)
4. **[out-of-scope fix, required by this plan's `<verification>` block]** - `e97bd6e` (fix) — round-trip case in `tests/controlplane/test_artifact_roundtrip.py`
5. **[Task 1 gap-fill: threat register T-16-28-02]** - `a32bd26` (test)

No separate plan-metadata commit was made beyond this SUMMARY's own addition to STATE.md/ROADMAP.md, per the orchestrator's standing instruction not to run `state.*`/`roadmap.*` SDK writers (see "STATE.md and ROADMAP.md" below).

## Files Created/Modified

- `src/ccf/controlplane/artifacts.py` — `DeploymentConfig`, `DEPLOYMENT_CONFIG`, both exported in `__all__`
- `src/ccf/deployment/classes.py` — one import, one `SDK_ARTIFACT_CLASSES` entry
- `tests/deployment/test_config_document.py` — new, 33 tests
- `tests/deployment/test_class_lookup.py` — one explicit identity test added
- `docs/schemas/ccf.deployment-config.json` — new, committed schema
- `docs/surface-changes/16-28-deployment-config-document.md` — new, this plan's surface claim
- `docs/SURFACE-CHANGES.md` — regenerated via `make surface-changes`
- `tests/controlplane/test_artifact_roundtrip.py` — one new `_Case` for `DEPLOYMENT_CONFIG` (out-of-scope fix, see below)
- `.planning/REQUIREMENTS.md` — one citation repaired (out-of-scope fix, see below)

## Decisions Made

- **`D-IMPL-138`(b) applied, not re-argued.** The plan's own action text instructed defending `backend_secrets`/`survivor_cap` as "a judgement this plan must defend in the docstring." Per the orchestrator's note, that judgement was settled by Dave on 2026-08-15 and recorded as `D-IMPL-138`(b). The class docstring cites the ruling and its measured basis (`DeploymentManifest`'s own eight fields) rather than constructing the argument as if undecided.
- **No second hand-maintained reserved-name list.** The plan explicitly warns against this (citing `_preflight_adapter`'s own history), so the unknown-key refusal reads `cls.model_fields` rather than a `_DEPLOYMENT_CONFIG_SECTIONS`-style tuple. An earlier draft of this class did add such a tuple for docstring cross-referencing; caught during self-review and removed before the first commit, since it was unused by the validator and directly contradicted the plan's own instruction.
- **SDK-owned and adopter-owned sections both typed as open mappings at this layer**, for two different reasons stated in the class docstring: materialisation (SDK-owned) vs. `D-IMPL-136` §14.3's reserved-slot ruling (adopter-owned). Neither is "tightened" to the eventual contract here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's stated 19-failure BASE is stale**
- **Found during:** pre-Task-1 BASE measurement, per instruction to measure fresh.
- **Issue:** the plan's `<verification>` block reproduces a 19-node-id failure set as the regression floor. `16-27`'s own SUMMARY had already measured zero failures at its BASE (`b23f601`, one commit before this plan's BASE `39a9a05`) — six intervening commits closed all nineteen before this plan started.
- **Fix:** measured fresh at `39a9a05` (3208 passed, 118 skipped, 0 failed) and treated zero as the regression floor throughout, consistent with `16-27`'s precedent.
- **Commit:** documented here; no code change required.

**2. [Rule 3 - Blocking] A pre-existing citation broke when Task 2's edit shifted line numbers**
- **Found during:** Task 2's own `tools.lints --all` acceptance check.
- **Issue:** registering `DEPLOYMENT_CONFIG` in `src/ccf/deployment/classes.py` added seven lines before `refuse_registration_the_sdk_fixes`'s definition (one import, six for the mapping entry and its comment), shifting it from line 243 to 250 and stranding `.planning/REQUIREMENTS.md`'s line-anchored citation of it. `cite02-anchor` failed: *"cites src/ccf/deployment/classes.py:243 for 'refuse_registration_the_sdk_fixes', which is not what those lines hold."*
- **Fix:** converted the citation to the `path.py::Symbol` form `D-IMPL-114` rules for — `src/ccf/deployment/classes.py::refuse_registration_the_sdk_fixes` — the same class of fix `16-27` made in its own new file (`7d6bc1d`).
- **Files modified:** `.planning/REQUIREMENTS.md` — **outside this plan's declared `files_modified`.** Flagged explicitly: `tools.lints --all exit 0` is a Task 1 acceptance criterion, the break was directly caused by this task's own edit, and the fix is a single substring replacement inside one historical paragraph, touching nothing else in it. Applied under deviation Rule 3.
- **Commit:** `a5a26af`.

**3. [Rule 1 - Bug] Registering `DEPLOYMENT_CONFIG` broke a second anti-drift test outside `tests/deployment/`**
- **Found during:** the mandated full-suite regression run after Task 2's commit.
- **Issue:** `tests/controlplane/test_artifact_roundtrip.py::test_every_sdk_artifact_class_has_a_round_trip_case` is a vacuity guard asserting `set(SDK_ARTIFACT_CLASSES) <= set(_IDS)` — every SDK artifact class must have a round-trip `_Case`. Neither task in the plan's own text, nor its `<files>` lists, nor `files_modified` mentions this module, so it was not touched by either task as written — and the plan's own `<verification>` block commits to "a twentieth failure, or any substitution, is this plan's."
- **Fix:** added one `_Case` for `DEPLOYMENT_CONFIG` exercising `product_class` (open mapping) and `policy` (adopter-owned, uninterpreted), with `unknown_keys=("connection", "dsn")` — neither a field of the contract, echoing `DEPLOYMENT_MANIFEST`'s own case and D-08. All four parametrised tests (round-trip, hash-stability, closed-world, no-semver) pass for it.
- **Files modified:** `tests/controlplane/test_artifact_roundtrip.py` — **outside this plan's declared `files_modified`.** Flagged explicitly: this is a genuine gap in the plan's file inventory (the module should have been listed), fixed under deviation Rule 1 because the plan's own `<verification>` block makes any new full-suite failure this plan's problem regardless of which file must change to close it.
- **Commit:** `e97bd6e`.

**4. [Rule 2 - Missing Critical] The threat register's T-16-28-02 negative control was not implemented in the first commit**
- **Found during:** post-commit self-review against the plan's `<threat_model>` STRIDE register, per the CLAUDE.md threat-model-reference discipline.
- **Issue:** T-16-28-02's stated mitigation includes *"a test asserts the model has no field whose name contains `dsn`, `url`, `password` or `connection`."* Task 1's first commit covered `backend_secrets`' reference-not-value mechanism but not this direct field-name assertion.
- **Fix:** added `test_no_field_name_names_a_connection_value` to `tests/deployment/test_config_document.py` (already in this plan's `files_modified`, no scope issue).
- **Commit:** `a32bd26`.

---

**Total deviations:** 4 auto-fixed (1 stale-baseline correction, 2 out-of-declared-scope blocking fixes, 1 missing-critical threat-model gap). Two of the four touched files outside this plan's declared `files_modified` (`.planning/REQUIREMENTS.md`, `tests/controlplane/test_artifact_roundtrip.py`) — both flagged explicitly above for review, both required by the plan's own acceptance criteria or `<verification>` commitments, neither expanding this plan's actual scope (no new behavior, only closing gaps this plan's own edits opened).
**Impact on plan:** No scope creep in intent — every fix closes a gap this plan's own changes caused or a gap the plan's own text committed to closing. The `files_modified` frontmatter itself was incomplete (missing `tests/controlplane/test_artifact_roundtrip.py`); worth correcting in the next plan that touches `SDK_ARTIFACT_CLASSES`.

## For Dave's ruling rather than mine

1. **`files_modified` for a plan that adds to `SDK_ARTIFACT_CLASSES` should include `tests/controlplane/test_artifact_roundtrip.py` as a standing rule**, not something each such plan discovers at its own full-suite run. This plan's frontmatter listed `tests/deployment/test_class_lookup.py` (the mapping's own anti-drift test) but not the sibling anti-drift test in `tests/controlplane/`. If this is a recurring omission across the `16-NN` plans that touch `SDK_ARTIFACT_CLASSES`, a standing note in the planning template would prevent it recurring in `16-29`/`16-30`, both of which are unlikely to add new `ArtifactClass` constants but worth a preflight check regardless.

## Measured Verification (Task 1 acceptance criteria)

| Criterion | Result |
| --- | --- |
| `pytest tests/deployment/test_config_document.py -q` | exit 0, **33 passed** |
| Unknown-key refusal message (two offenders, reproduced verbatim) | see below |
| `DeploymentConfig.model_fields` | exactly the fifteen names in `<interfaces>` |
| `git diff --stat $BASE..HEAD -- src/ccf/deployment/manifest.py` | empty |
| `DeploymentManifest`/`ManifestEntry` source length | 10561 / 7336, unchanged from BASE |
| `pytest tests/deployment/ -q` | exit 0, **184 passed** (measured after Task 2; before Task 2's registration it read 179 passed / 2 failed — see "The unregistered-then-registered sequence" below) |
| `mypy` (strict, `src`+`runtime`) | exit 0, **195 files** |
| `tools.lints --all` | exit 0; `tools/lints/allowlist.yaml` untouched |

**The unknown-key refusal, verbatim** (two offenders, `poilcy` and `resolutoin`, named together):

```
document is not a valid ccf.deployment-config: 1 validation error for DeploymentConfig
  Value error, ccf_config.yaml names 'poilcy', 'resolutoin', which the SDK does not
  recognise as a section or a deployment-level key; the names it does recognise are:
  backend, backend_secrets, debt_profile, default_perspective, half_life, operators,
  policy, policy_bundle_key, product_class, request_contract, resolution,
  resolution_spec_key, semver, survivor_cap, tenant_id [type=value_error, ...]
```

**`DeploymentConfig.model_fields`, verbatim:**

```
['backend', 'backend_secrets', 'debt_profile', 'default_perspective', 'half_life',
 'operators', 'policy', 'policy_bundle_key', 'product_class', 'request_contract',
 'resolution', 'resolution_spec_key', 'semver', 'survivor_cap', 'tenant_id']
```

## Measured Verification (Task 2 acceptance criteria)

**"The unregistered-then-registered sequence," for the record** — the plan asked this be captured. Before `DEPLOYMENT_CONFIG.class_id` joined `SDK_ARTIFACT_CLASSES`:

```
FAILED tests/deployment/test_class_lookup.py::test_every_exported_artifact_class_is_manifest_addressable
  AssertionError: ccf.controlplane.artifacts exports ArtifactClass constants that no
  manifest can address: {'DEPLOYMENT_CONFIG': 'ccf.deployment-config'} ... add it to
  ccf/deployment/classes.py.
2 failed, 179 passed
```

Immediately after the one-line registration (before the fragment existed): 1 failed (`test_the_phases_fragments_claim_exactly_what_was_added`, expected — no fragment yet), 34 passed. After the fragment (`docs/surface-changes/16-28-deployment-config-document.md`) and `make surface-changes`: **36 passed, 0 failed.**

| Criterion | Result |
| --- | --- |
| `pytest tests/deployment/test_class_lookup.py -q` | exit 0, **36 passed** |
| `resolve_artifact_class("ccf.deployment-config") is DEPLOYMENT_CONFIG` | `True` |
| `make schemas` | exit 0; `docs/schemas/ccf.deployment-config.json` exists, 15 properties, `additionalProperties: false` count 2 |
| `tools/dump_surface.py --report` | `added (8)` — this plan's own two (`ccf.controlplane.artifacts.DeploymentConfig`, `ccf.controlplane.artifacts.DEPLOYMENT_CONFIG`) plus six already claimed by `16-22`'s and `16-23`'s fragments; `removed (0)`; `reshaped (6)`, all pre-existing from `16-27` and earlier |
| `parse_entries()` filtered to this plan's fragment | `[('ccf.controlplane.artifacts.DEPLOYMENT_CONFIG', 'added'), ('ccf.controlplane.artifacts.DeploymentConfig', 'added')]` — exactly this plan's own added set, direction-for-direction |
| `make surface-changes` | exit 0; `git diff --stat $BASE -- docs/SURFACE-CHANGES.md` non-empty (47 insertions, 2 deletions) |
| `pytest tests/ -q -k surface` | exit 0, **94 passed** (same count `16-27`'s SUMMARY recorded) |
| `pytest tests/cli/test_schema_export.py -q` | exit 0, **42 passed** |
| `make docs-strict` | exit 0 |
| `git diff --stat $BASE -- docs/surface/ examples/` | empty |
| `git diff --stat $BASE -- pyproject.toml tools/lints/allowlist.yaml` | empty (no install; T-16-28-SC) |

## Full-suite regression, final state

```
PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/ -q
3248 passed, 118 skipped, 105 warnings in 375.21s (0:06:15)
```

**Zero failures — matches BASE's zero exactly.** No twentieth failure, no substitution. (BASE 3208 passed → final 3248 passed, +40 across the new/extended test modules; skip count unchanged at 118.)

Other gates, all run clean:

| Gate | Result |
| --- | --- |
| `mypy` (strict, `src`+`runtime`) | exit 0, 195 files |
| `tools.lints --all` | exit 0; `tools/lints/allowlist.yaml` untouched |
| `make docs-strict` | exit 0 |
| `make examples` | exit 0 |
| `CCF_TEST_FLUREE_URL=http://localhost:8090 make leg-fluree` | exit 0, **76 passed** (same count `16-27`'s SUMMARY recorded) |
| `pytest tests/invariants/test_citation_coverage.py -q` | exit 0, **5 passed** (unchanged — the citation fix converted a line-anchor to a symbol-anchor, neither counted in the unanchored-population ceiling) |

## Threat Register — measured disposition

- **T-16-28-01** (reserved section name as namespace claim) — mitigated. `git diff --stat $BASE -- src/ccf/deployment/classes.py`: 7 lines (1 import, 6 for the one mapping entry and its comment) — `_CCF_NAMESPACE` and `resolve_artifact_class` untouched. `test_adopter_owned_section_round_trips_arbitrary_content_unread` and `test_a_policy_body_with_a_key_literally_named_role_parses` assert arbitrary adopter content round-trips unread.
- **T-16-28-02** (credential/DSN entering a content-hashable document) — mitigated, gap closed in this plan (see Deviation 4 above). `test_no_field_name_names_a_connection_value` asserts no field name contains `dsn`, `url`, `password`, or `connection`.
- **T-16-28-03** (typo silently changes what is put in force) — mitigated. The named `mode="before"` refusal plus `additionalProperties: false` in the committed schema, both asserted.
- **T-16-28-04** (narrowing implemented as making `role`/`registration` optional on `ManifestEntry`) — mitigated. `ManifestEntry` is unedited; source-length comparison against BASE confirms it (10561/7336 chars, matching exactly).
- **T-16-28-05** (new exports with no migration record) — mitigated. The fragment, reconciled against `--report` in both directions, plus `test_the_phases_fragments_claim_exactly_what_was_added`'s subset-equality, both passing.
- **T-16-28-SC** (package install) — no install occurred; `pyproject.toml` diff empty.

## Known Stubs

None. `DeploymentConfig` is a complete, tested contract; nothing in it is a placeholder pending later work. The sections it holds as open mappings are *intentionally* untyped at this layer per the plan's own materialisation argument, not stubs — `16-29` is where each section gains its real validation.

## Threat Flags

None beyond the register above. No new network endpoint, no new auth path. `DeploymentConfig` introduces a new *parse* surface over adopter-authored YAML, which is exactly the surface the plan's own threat model anticipated and dispositioned.

## Issues Encountered

None beyond the deviations documented above.

## STATE.md and ROADMAP.md

**Not updated by this agent.** Per the standing instruction ("NEVER run the `state.*` or `roadmap.*` SDK writers — every one has corrupted `.planning/STATE.md`"), no `gsd-sdk query state.*` or `roadmap.*` command was run. The orchestrator hand-edits `.planning/STATE.md` and `.planning/ROADMAP.md`; this SUMMARY and the requirement completion (`DOCS-23`) are ready for that hand-edit.

## Next Phase Readiness

- `DeploymentConfig` and `DEPLOYMENT_CONFIG` are ready for `16-29`'s loader to derive against — parsing, closed-world refusal, and adopter-owned-section opacity are all in place and tested.
- `HW1_SINGLE_FILE_DOCUMENT` (in `tests/deployment/test_config_document.py`) is ready for `16-29` and `16-30` to import rather than retype.
- No blockers. `16-29` depends on this plan (`16-28`) per its own `depends_on`; nothing here is incomplete against what `16-29` needs.

---
*Phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar*
*Completed: 2026-08-15*

## Self-Check: PASSED

All 10 files listed in `key-files`/`Files Created/Modified` confirmed present on disk; all 5 commit hashes (`52f4d03`, `a5a26af`, `4544a3a`, `e97bd6e`, `a32bd26`) confirmed in `git log --oneline --all`.
