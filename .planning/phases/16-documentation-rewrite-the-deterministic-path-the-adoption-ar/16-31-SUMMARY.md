---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 31
subsystem: examples
tags: [ccf-config-yaml, hw1, single-file-config, control-plane, content-addressing, adoption-story]

requires:
  - phase: 16-30
    provides: load_config_and_boot, derive_deployment, the config-form register loop
provides:
  - "examples/s1-00-companies-over-revenue/ccf_config.yaml — HW-1's whole Control Plane configuration in one authored document, byte-address-proven equal to the multi-file form it replaces"
  - "tests/deployment/fixtures/s1-00-multifile/ — the frozen multi-file form, so the equivalence proof survives the conversion"
affects: []

tech-stack:
  added: []
  patterns:
    - "Freeze before convert: copy the multi-file form into a test fixture and prove the fixture-backed test green BEFORE deleting the originals, so the equivalence proof never has a window with only one side"
    - "Content-address-before-and-after as the correctness proof for a config-format migration: the served product's content address, not a structural assertion, is what decides whether the conversion is faithful"

key-files:
  created:
    - examples/s1-00-companies-over-revenue/ccf_config.yaml
    - tests/deployment/fixtures/s1-00-multifile/README.md
    - tests/deployment/fixtures/s1-00-multifile/manifest.yaml
    - tests/deployment/fixtures/s1-00-multifile/product-class.yaml
    - tests/deployment/fixtures/s1-00-multifile/request-contract.yaml
    - tests/deployment/fixtures/s1-00-multifile/resolution-spec.yaml
    - tests/deployment/fixtures/s1-00-multifile/half-life-table.yaml
    - tests/deployment/fixtures/s1-00-multifile/debt-profile.yaml
    - tests/deployment/fixtures/s1-00-multifile/policy-bundle.yaml
    - tests/deployment/fixtures/s1-00-multifile/perspective.yaml
    - tests/deployment/fixtures/s1-00-multifile/operator-parameters-temporal.yaml
  modified:
    - examples/s1-00-companies-over-revenue/deployment.py
    - examples/s1-00-companies-over-revenue/produce.py
    - examples/s1-00-companies-over-revenue/scenario/question.yaml
    - examples/s1-00-companies-over-revenue/MEASUREMENT.md
    - examples/s1-00-companies-over-revenue/README.md
    - tests/examples/test_s1_00_config_equivalence.py
    - tests/products/test_gate_two_call_shape.py
  deleted:
    - examples/s1-00-companies-over-revenue/artifacts/config/manifest.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/product-class.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/request-contract.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/resolution-spec.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/half-life-table.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/debt-profile.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/policy-bundle.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/perspective.yaml
    - examples/s1-00-companies-over-revenue/artifacts/config/operator-parameters-temporal.yaml
  moved:
    - "examples/s1-00-companies-over-revenue/artifacts/config/backends.yaml -> examples/s1-00-companies-over-revenue/backends.yaml (byte-unchanged)"

key-decisions:
  - "BASE measured fresh at 455b702: 3305 passed, 118 skipped, 0 failed (tests/examples/ tests/deployment/ scoped: 580 passed, 37 skipped) — confirms the orchestrator's brief exactly. The plan's own text claims a stale nineteen-failure baseline; disputed, not reproduced, same defect 16-27 through 16-30 already carried."
  - "[Rule 3 - blocking fix, deviation from plan text] produce.py's assemble_and_serve() -- not deployment.py -- holds the direct call to the fabric's boot entry point (load_and_boot, imported at module scope). The plan's own <files_modified> list and its 'Do not touch produce.py, consume.py or scenario/provision.py' instruction omit produce.py, but load_and_boot cannot parse a ccf_config.yaml (config.py's own docstring: 'two names, two doors', no config_path parameter, no auto-detection by filename considered and rejected). Without changing this one call to load_config_and_boot, make example-s1-00 cannot run at all -- contradicting every acceptance criterion in the plan's own Task 3. Fixed with the smallest possible edit: one import line, one call line, inside the existing [start:boot] marker region; the manifest: Path parameter name and consume.py's deployment.MANIFEST reference are both kept unchanged so consume.py needs no edit at all."
  - "[Rule 3 - blocking fix, out of plan scope] tests/products/test_gate_two_call_shape.py's _deployment_root() located a deployment's Control Plane tree by testing for an artifacts/ subdirectory. HW-1's conversion removes that directory entirely (ccf_config.yaml lives at the deployment root, per the plan's own files_modified path and the design spec's own worked example), which broke six tests asserting HW-1's D-IMPL-137 one-document exemption. Fixed by teaching _deployment_root() and _registers_requirements() to also recognise a ccf_config.yaml file directly at the deployment root, alongside the existing artifacts/ check."
  - "resolution_spec_key and policy_bundle_key are NOT authored as explicit top-level fields in ccf_config.yaml, despite the plan's action text saying they 'come across from manifest.yaml unchanged.' Read literally that would require also authoring a key: override inside the resolution:/policy: sections (to keep the explicit pointer consistent with the section's own derived key), which is exactly the kind of authored key/index the plan itself forbids ('If you find yourself authoring a path, a key, or an index of any kind, the loader is not doing its job'). Omitted instead, letting derive_deployment auto-derive both pointers from the resolution:/policy: section names -- matching both the design spec's own §4.1 worked example (which uses HW-1's own values and omits these two fields) and the already-shipped, tested tests/examples/fixtures/s1_00_ccf_config.yaml. Verified this produces byte-identical content addresses to the multi-file form on all 8 artifacts before any deletion happened."
  - "backends.yaml's stale $schema comment path and 'manifest.yaml' prose reference were left uncorrected, even though they are now technically wrong (the relative path assumed the old 4-levels-deep location) -- because the plan's Task 2 acceptance criterion explicitly demands 'backends.yaml still exists and is byte-unchanged (git diff on it is empty)', and that is a stronger, more specific, more easily machine-checked instruction than the general staleness concern. Recorded as a known, minor, untest-covered blemish rather than silently traded against an explicit acceptance criterion."

requirements-completed: [DOCS-25]

duration: ~2.5hr
completed: 2026-08-15
---

# Phase 16 Plan 31: Convert HW-1 to ccf_config.yaml Summary

**HW-1 (`examples/s1-00-companies-over-revenue`) now authors its whole Control Plane configuration in one file, `ccf_config.yaml` (48 non-comment lines) plus `backends.yaml` (10 lines, unchanged) — replacing the ten-document, ninety-nine-line multi-file form — with the served product's content address proven byte-identical before and after the conversion.**

## Performance

- **Duration:** ~2.5 hours
- **Completed:** 2026-08-15
- **Tasks:** 3 of 4 (Task 4 is the blocking human-verify checkpoint — not executed, per instructions)
- **Commits:** 3

## BASE measurement

```
tests/examples/ tests/deployment/ -q  →  580 passed, 37 skipped, 0 failed
```

at `455b702`, matching the orchestrator's brief exactly. The plan's own `<verification>` text was not checked against a stale-failure claim this time (the prompt pre-disputed it); no failures reproduced anywhere in this plan's own runs.

## Task Commits

1. **Task 1: Freeze the multi-file form as a test fixture** — `6800332` (test) — `tests/deployment/fixtures/s1-00-multifile/` (nine documents + README.md), `tests/examples/test_s1_00_config_equivalence.py` (repoint `HW1_MULTIFILE_DIR`, adjust the two committed-figure constants). Verified green against the still-unconverted example: 239 passed.
2. **Task 2: Author `ccf_config.yaml` and retire the nine documents** — `51aae02` (feat) — `ccf_config.yaml` created, nine documents deleted, `backends.yaml` moved (byte-unchanged), `deployment.py` + `produce.py` + `scenario/question.yaml` updated.
3. **Task 3: Prove the conversion changed nothing but the file count** — `dcdff9a` (docs) — `MEASUREMENT.md` and `README.md` restated before/after; `tests/products/test_gate_two_call_shape.py` fixed (see Deviations).

## The content address, before and after — the load-bearing proof

Measured twice, at two different thresholds, before any file was touched and again after every task completed:

| Threshold | Before (pre-conversion, `455b702`) | After (post-conversion, `dcdff9a`) | Equal |
| --- | --- | --- | --- |
| `MIN_REVENUE=1000000000` | `5cfee793e5fb686a82becac08cddf2ca187c3ef9ae26bd9a8fd41030656a6d36` | `5cfee793e5fb686a82becac08cddf2ca187c3ef9ae26bd9a8fd41030656a6d36` | **yes** |
| `MIN_REVENUE=1000000` | `af094c96efc192d7294795e6326a71eda2115b1fe1fbd1f6a2f0fd62b0da787a` | *(not re-measured post-conversion — the `1e9` pair is the one carried through the whole plan; both thresholds were deterministic across repeated pre-conversion runs)* | n/a |

The `1e9` figure also matches `README.md`'s already-published value from before this plan (`5cfee793e5fb686a82becac08cddf2ca187c3ef9ae26bd9a8fd41030656a6d36`) — a second, independent confirmation that this run's output was not merely internally consistent but matched the value already committed to the repository before this plan began.

**Before deleting anything**, `derive_deployment` was run directly over the new `ccf_config.yaml` and compared, artifact by artifact, against the frozen multi-file fixture — all 8 content addresses identical (the same 8-row table `16-30` already printed, reproduced verbatim: `ccf.debt-profile`, `ccf.half-life-table`, `ccf.operator-parameters.temporal`, `ccf.perspective`, `ccf.product-class`, `ccf.resolution-spec`, `hw1.policy-bundle`, `hw1.request-contract`, all equal). This was the gate that had to pass before Task 2's deletion step ran at all.

## The authored line count — 48, not ~30

| Section | Lines | What it carries |
| --- | ---: | --- |
| top level (`semver`, `tenant_id`, `backend`) | 3 | unchanged from `manifest.yaml`'s own three top-level value fields |
| `product_class:` | 7 | header + the six fields `product-class.yaml` carried |
| `operators:` | 3 | header + operator id + the one field `operator-parameters-temporal.yaml` carried |
| `request_contract:` | 12 | header + 3 adopter-owned bookkeeping lines (`class_id`, `role`, `registration` — `D-IMPL-138`(a)) + `schema_name`/`schema_version` (2 lines, needed by `ProductRequestContract.from_declared`) + the 6-line `arguments:` block |
| `resolution:` | 6 | header + the five fields `resolution-spec.yaml` carried |
| `half_life:` | 5 | header + `company:` + the three fields `half-life-table.yaml` carried |
| `debt_profile:` | 4 | header + the three fields `debt-profile.yaml` carried |
| `policy:` | 5 | header + 3 adopter-owned bookkeeping lines + the one field `policy-bundle.yaml` carried |
| `default_perspective:` | 3 | header + the two fields `perspective.yaml` carried |
| **Total** | **48** | |

Design spec target: *"roughly 30 lines against HW-1's current 99."* **Actual: 48.** Gap: 18 lines, accounted for rather than compressed away:

1. **6 lines** — `D-IMPL-138`(a)'s three-bookkeeping-line ruling on the two adopter-owned sections (`request_contract:`, `policy:`). The design spec's own §5.3/§5.7 worked examples show these with **zero** bookkeeping lines; the ruling postdates that illustration.
2. **2 lines** — `request_contract:`'s `schema_name`/`schema_version`, also omitted from the design spec's §5.3 snippet but required by `produce.py`'s `ProductRequestContract.from_declared` call; HW-1's own committed `request-contract.yaml` already carried them, so this is pre-existing content the illustration simply did not show.
3. **10 lines** — the compounding cost of eight section headers plus nesting (`arguments:` → `properties:` → `revenue_threshold:` → two fields; `half_life:` → `company:`) that the design spec's disconnected per-section snippets did not sum when combined into one file.

No line was moved out of `ccf_config.yaml` to shrink this number. `ccf_config.yaml` is also identical in structure and non-comment line count (48) to `tests/examples/fixtures/s1_00_ccf_config.yaml`, the hand-authored fixture `16-30` already proved content-address-equivalent — this file did not need to reinvent that proof, only reproduce it as the shipped example.

## The `find` output

```
examples/s1-00-companies-over-revenue/backends.yaml
examples/s1-00-companies-over-revenue/ccf_config.yaml
examples/s1-00-companies-over-revenue/consume.py
examples/s1-00-companies-over-revenue/deployment.py
examples/s1-00-companies-over-revenue/MEASUREMENT.md
examples/s1-00-companies-over-revenue/produce.py
examples/s1-00-companies-over-revenue/README.md
examples/s1-00-companies-over-revenue/scenario/companies.sql
examples/s1-00-companies-over-revenue/scenario/provision.py
examples/s1-00-companies-over-revenue/scenario/question.yaml
examples/s1-00-companies-over-revenue/scenario/schema.sql
```

11 files (was 19). No `artifacts/` directory remains.

## `make example-s1-00` — exit 0, output captured

```
Q: which companies have revenue over 1000000000?
   asked as of 2026-08-01T00:00:00+00:00

   Contoso Manufacturing       1850000000   updated 2026-07-02
   Litware Systems             7750000000   updated 2025-09-30
   Lucerne Publishing          1500000000   updated 2024-08-09
   Northwind Traders           4200000000   updated 2026-07-20
   Tailspin Logistics         12400000000   updated 2026-03-01
   Wingtip Materials           2900000000   updated 2025-02-04

   6 of 10 companies

What a SELECT would not have told you:
   context debt D_c   0.3886  ->  forced_llm   (F=0.6114 from last_updated on 10 rows against the declared half-life)
   policy version     dd2c515f43012c7908ff9bd82289553be2b2f8d3900291c265e1cc5abeda0f5f
   content address    5cfee793e5fb686a82becac08cddf2ca187c3ef9ae26bd9a8fd41030656a6d36
   replay record      2cffb21c42252e25bfa5ec43e2ce0b4b5679e9dd5a91346a1c2ced2339f30644
```

Output is unchanged in shape and legibility from before the conversion (same columns, same `forced_llm` line, same "what a SELECT would not have told you" block) — only the content address's *stability*, not its value's meaning, was ever at stake. Replay record differs between runs (`2cffb21c…` here vs. `437d9b10…` pre-conversion) — expected and unrelated to the conversion: `backends.yaml`'s `schema_name: {per_run: identifier}` mints a fresh Postgres schema name per run, which flows into replay bookkeeping; the content address (computed over the served product's own payload/lineage, not over run-scoped bookkeeping) is what the plan's threat register and success criteria pin, and it did not move.

## Gate Results

| Gate | Result |
| --- | --- |
| `tests/examples/test_s1_00_config_equivalence.py tests/deployment/ -q` (Task 1, pre-conversion) | 239 passed |
| `derive_deployment` over `ccf_config.yaml` vs. frozen fixture, 8 artifacts (pre-deletion sanity check) | 8/8 content addresses identical |
| `tests/examples/ tests/deployment/ -q` (post-conversion) | 580 passed, 37 skipped, 0 failed |
| `tests/examples/test_s1_00_output.py -q` | 9 passed; diff to that file: **empty** (no edit needed at all) |
| `tests/examples/test_spine_separation.py -q` | 22 passed; diff to that file: **empty** |
| `tests/products/test_gate_two_call_shape.py -q` (after the Rule 3 fix) | 77 passed |
| `command grep -rn "manifest.yaml" examples/s1-00-companies-over-revenue/` | empty after Task 3 (README.md/MEASUREMENT.md were the last two hits, both fixed in Task 3's own commit) |
| `git diff -- examples/s1-00-companies-over-revenue/backends.yaml` (vs. its pre-move content) | empty — byte-unchanged, pure rename |
| `make example-s1-00 MIN_REVENUE=1000000000` | exit 0, content address unchanged |
| `make ci-core` | exit 0 — `3305 passed, 118 skipped, 0 failed`, matching BASE exactly |
| `make docs-strict` | exit 0 |
| `.venv/bin/python -m tools.lints --all` | exit 0 |
| `.venv/bin/python -m pytest tests/invariants/test_citation_coverage.py -q` | 5 passed |
| `git diff --stat $BASE..HEAD -- src/ runtime/` | empty |
| `git diff --name-only $BASE..HEAD -- examples/` | every path under `s1-00-companies-over-revenue/` — no other example touched |
| `git diff --stat $BASE..HEAD -- docs/surface/ tools/lints/allowlist.yaml pyproject.toml .planning/ROADMAP.md docs/DECISIONS.md 16-CONTEXT.md 16-RESEARCH.md 16-PATTERNS.md docs/superpowers/` | empty, all paths |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking fix, deviation from explicit plan instruction] `produce.py`'s boot call had to change to `load_config_and_boot`, contradicting the plan's own "Do not touch produce.py"**
- **Found during:** Task 2, after authoring `ccf_config.yaml` and updating `deployment.py`
- **Issue:** The plan's Interfaces section states *"`deployment.py` currently reaches the fabric through `load_and_boot`... after this plan it reaches it through `load_config_and_boot`"* — but `deployment.py` has never held that call. `produce.py::assemble_and_serve` does, at module scope (`from ccf.deployment import ... load_and_boot`, then `booted = load_and_boot(manifest, ...)`). `load_and_boot` cannot parse a `ccf_config.yaml`: `config.py`'s own module docstring states plainly, *"No `config_path` parameter on `load_and_boot`, and no auto-detection by filename, considered and rejected. Two names, two doors."* Attempting the multi-file schema against the single-file document raises a validation error immediately. The plan's `<files_modified>` frontmatter list and its explicit "Do not touch produce.py, consume.py or scenario/provision.py" instruction both omit `produce.py` from scope, but without this edit `make example-s1-00` cannot run at all — contradicting every acceptance criterion in the plan's own Task 3 (content address proof, `test_s1_00_output.py`, `make example-s1-00` exit 0).
- **Fix:** The smallest possible edit — one `import` line (`load_and_boot` → `load_config_and_boot`) and one call line, both inside the existing `[start:boot]…[end:boot]` marker region (comment text updated to describe the config form; the marker names and every other line untouched). The `manifest: Path` parameter name on `assemble_and_serve` was kept unchanged (still semantically "the file to boot from"), and `deployment.py`'s exported symbol is still named `MANIFEST` (now pointing at `ccf_config.yaml`) — both choices made specifically so `consume.py`'s `deployment.MANIFEST` keyword-argument reference needed **zero** edits, honoring as much of the "do not touch" instruction as is compatible with the example actually running.
- **Files modified:** `examples/s1-00-companies-over-revenue/produce.py` (not in this task's declared file list)
- **Verification:** `tests/examples/test_spine_separation.py` passes with an **empty diff** against that file (the marker-region structural gate the plan explicitly protects); `make example-s1-00` exit 0; content address unchanged before/after; `git diff --stat $BASE..HEAD -- examples/` still touches only `s1-00-companies-over-revenue/` (produce.py lives inside that directory).
- **Committed in:** `51aae02` (Task 2 commit), with the full reasoning also recorded in that commit's own message for anyone reading `git log` without this SUMMARY.

**2. [Rule 3 — blocking fix, out-of-scope file] `tests/products/test_gate_two_call_shape.py`'s artifact-tree detector broke on HW-1's new on-disk shape**
- **Found during:** Task 3, first `make ci-core` run
- **Issue:** `_deployment_root()` located a deployment's Control Plane tree by testing `(candidate / "artifacts").is_dir()` — true for every example when this test module was written, because every example's config lived under `<root>/artifacts/`. HW-1's conversion removes that directory entirely: `ccf_config.yaml` sits directly at the deployment root (per the plan's own `files_modified` path, `examples/s1-00-companies-over-revenue/ccf_config.yaml`, and the design spec's own §4.1 worked example, *"deployment root, where `manifest.yaml` lives today"*). With `artifacts/` gone, `_deployment_root()` returned `None` for HW-1's `produce.py`, which tripped the module's fail-closed guard (`root is None` ⇒ "not exempt" ⇒ the `D-IMPL-137` one-document exemption HW-1 relies on to avoid calling `refuse_operator_set_divergence` no longer applies) — 6 tests failed.
- **Fix:** Taught `_deployment_root()` to also recognise `(candidate / "ccf_config.yaml").is_file()` as a valid deployment-root indicator, alongside the existing `artifacts/` check, and taught `_registers_requirements()` to scan that same file for a `ccf.projection-requirements` registration the same way it already scans every YAML under `artifacts/`. `ccf_config.yaml` can never actually carry that registration — `ccf.projection-requirements` is not one of `D-IMPL-136`'s eight reserved section names — so this always answers `False` for a single-file deployment, which is the correct, scanned-rather-than-assumed answer the rest of the module already insists on for every other reading.
- **Files modified:** `tests/products/test_gate_two_call_shape.py` (not in this task's declared file list, and outside the plan's stated scope of "examples/s1-00-companies-over-revenue/ and the test files the plan names")
- **Verification:** `tests/products/test_gate_two_call_shape.py -q` → 77 passed (was 6 failed / 71 passed); `make ci-core` → 3305 passed, 118 skipped, 0 failed, matching BASE exactly
- **Committed in:** `dcdff9a` (Task 3 commit)

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking fixes required to make the plan's own stated acceptance criteria achievable), both outside the plan's declared file scope, both fully necessary and minimal, both documented in-commit and here.

### Disputed plan claims (not auto-fixed, recorded as findings)

**1. "`tenant_id`... [is] absent from HW-1's manifest and must stay absent" — false, contradicted by the committed manifest.** `examples/s1-00-companies-over-revenue/artifacts/config/manifest.yaml` (as committed at `BASE`, and preserved verbatim in the frozen fixture) states `tenant_id: hw1-demo` at its top level. This value is genuinely used — `_resolve_tenant` reads it when no override is passed, and produce.py's own `booted.tenant_id` flows through every downstream call. `ccf_config.yaml` authors `tenant_id: hw1-demo` accordingly, matching the already-shipped, tested `tests/examples/fixtures/s1_00_ccf_config.yaml`. The plan's claim about `backend_secrets` and `survivor_cap` being genuinely absent and correctly staying absent is accurate; only the `tenant_id` clause of that sentence is wrong.

**2. "`resolution_spec_key` and `policy_bundle_key` come across from `manifest.yaml` unchanged" — not authored as explicit fields; they auto-derive instead, and this is the correct reading.** See the key-decisions entry above. Authoring them explicitly as `resolution-spec`/`policy-bundle` would require also authoring a `key:` override inside the `resolution:`/`policy:` sections to keep the two consistent — exactly the "authored index" the plan's own text forbids two sentences later. Omitted, matching the design spec's own worked example and the already-proven fixture. Both pointers derive to `resolution`/`policy` (not `resolution-spec`/`policy-bundle`) — a different, valid key under the single-file form's own vocabulary, which does not affect content-address equivalence (verified: all 8 addresses identical).

## Known Stubs

None. Every section of `ccf_config.yaml` derives to a real, registered, pinned artifact — proven identical to the multi-file form's own artifacts before the multi-file form was ever deleted.

## Threat Flags

None. All four threat-register entries (`T-16-31-01` through `T-16-31-04`) are mitigated as designed:
- `T-16-31-01` (silent behavior change) — content address proven byte-identical before/after.
- `T-16-31-02` (credential migrating into the content-hashed document) — `backends.yaml` stays out, byte-unchanged, and `ccf_config.yaml` was reviewed line-by-line for any field named `dsn`/`url`/`password`/`connection`: none present.
- `T-16-31-03` (equivalence proof losing a side silently) — Task 1's fixture freeze was proved green against the unconverted example before Task 2 deleted anything.
- `T-16-31-04` (breaking an unrelated example or the multi-file loader) — `git diff` on `src/`, `runtime/` and every other example is empty; `make ci-core` exit 0.

## Issues Encountered

Both deviations above (produce.py's boot call, and `test_gate_two_call_shape.py`'s artifact-tree detector) were genuine blockers not anticipated by the plan text, both fixed minimally and both necessary for the plan's own Task 3 acceptance criteria to be achievable at all. No other issues.

## User Setup Required

None beyond what `make example-s1-00` already provisions (Docker, or `CCF_TEST_POSTGRES_DSN`).

## Next Phase Readiness — Task 4 is a blocking human-verify checkpoint, NOT executed

Per the plan and per instructions, execution stops here. Task 4 asks Dave to perform four reads:

1. **The directory listing** — `find examples/s1-00-companies-over-revenue -type f -not -path '*__pycache__*' | sort` — reproduced above under "The `find` output."
2. **`ccf_config.yaml` top to bottom** — the file is 48 non-comment lines; every line traces to a value HW-1's own multi-file documents already carried (see the line-by-line account above), with the sole exception of the 8 bookkeeping lines `D-IMPL-138`(a) requires on the two adopter-owned sections.
3. **The number against the ~30 target** — 48, not ~30; the gap is fully accounted for above, not compressed away.
4. **`make example-s1-00`'s output** — exit 0, captured above, unchanged in shape and legibility from the pre-conversion run.

No blockers beyond Dave's ruling on the 48-vs-30 gap and the two deviations (both already fixed, both explained above for review).

---
*Phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar*
*Completed: 2026-08-15*

## Self-Check: PASSED

All created/modified files verified present on disk (`ccf_config.yaml`, the nine `tests/deployment/fixtures/s1-00-multifile/` files plus README.md, the deleted nine `artifacts/config/*.yaml` confirmed absent, `backends.yaml` confirmed at its new location). All three task commits (`6800332`, `51aae02`, `dcdff9a`) confirmed present in `git log`.
