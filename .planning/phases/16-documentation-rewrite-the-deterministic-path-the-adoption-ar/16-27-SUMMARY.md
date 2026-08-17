---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 27
subsystem: products-contract
tags: [D-IMPL-135, D-IMPL-138, surface-gates, product-discovery, citation-coverage]
requires:
  - phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
    provides: "16-22's widened surface-change glob and _PLAN_NUMBER regex, which make a 16-* fragment readable"
provides:
  - ccf.products.contract.ProductDiscovery.audiences
  - the discharged D-IMPL-135 full-surface-obligation for a shipped §6.3 element
  - the measured answer to D-IMPL-138(c) (which name the shape-move gate actually catches)
affects: ["16-28", "16-29", "16-30"]
tech-stack:
  added: []
  patterns: [opaque-deployment-declared-axis, sentinel-restated-not-inherited, measure-then-decide-gate-arbitration]
key-files:
  created:
    - tests/products/test_discovery_audiences.py
    - docs/surface-changes/16-27-discovery-audiences.md
  modified:
    - src/ccf/products/contract.py
    - docs/SURFACE-CHANGES.md
    - docs/schemas/ccf.product-class.json
    - tests/test_surface_shape_capture.py
    - .planning/REQUIREMENTS.md
key-decisions:
  - "The default is frozenset() rather than a required field, on D-IMPL-136 §10's compatibility posture by analogy — every existing ProductDiscovery construction, ccf.product-class document, and NOT_DISCOVERABLE itself keep working with no edit"
  - "The rejected-alternative prose lives in the audiences attribute docstring, not the module docstring, so it does not travel into docs/schemas/ description fields"
  - "_SHAPE_MOVED_BY_FRAGMENT is keyed to ccf.products.contract.register_product_class, not ccf.products.contract.ProductDiscovery — measured via pytest -k surface, contradicting both the plan's stated premise and its Task 3(b) instruction"
  - "The fragment carries two reshaped entries, not the plan's instructed 'exactly one', because register_product_class's signature genuinely moves via a transitively-embedded default-value repr"
requirements-completed: [DOCS-22]
duration: one session
completed: 2026-08-15
---

# Phase 16 Plan 27: Discovery Audiences Summary

`ProductDiscovery` gains a fourth axis, `audiences: frozenset[str] = frozenset()`, opaque and additive on the same footing as `domain`/`intents`/`capabilities`, discharging `D-IMPL-135`'s full surface obligation — and the `D-IMPL-138`(c) measure-then-decide arbitration lands on a different name than either the plan or the ruling anticipated: `register_product_class`, not `ProductDiscovery`.

## BASE, verbatim

```
b23f601f3e6f61094fbad0746525c37703a33803
```

Captured with `git rev-parse HEAD` before the first edit. Every scope guard below is `git diff --stat $BASE..HEAD -- <path>`; the bare `git diff -- <path>` form was not used, because all three tasks commit and it is empty for every path once they have.

## The BASE full-suite measurement corrects the plan brief

The plan brief, written against commit `82d4af0`, stated the branch's red baseline as **19 failed, 3177 passed, 118 skipped**, and instructed treating that failure *set* as the regression floor. **Measured fresh at `b23f601`** (`PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q -p no:randomly`, run twice for rigor — once contaminated by concurrent edits and discarded, once clean against a verified-untouched tree):

```
3200 passed, 118 skipped, 105 warnings in 370.43s (0:06:10)
```

**Zero failures.** Six commits landed on `phase-16` between `82d4af0` and `b23f601` (`e890453` through `8fc3103`) that evidently closed all nineteen — including, explicitly, `868aa4e`, which `D-IMPL-138`'s own text confirms closed the citation-coverage failure the plan brief flagged as "new information ... not fixed here." The plan's Task 1 instruction to reproduce a stale 19-line failure list and its `<verification>` block's "the failure set must be exactly those nineteen node ids" are both moot against the tree actually being executed against. The correct regression floor, measured rather than inherited, is **zero failures**, and that is what this plan closes against.

**Post-plan measurement** (same command, same flags, run to completion after all three tasks and the citation-coverage fix): **3208 passed, 118 skipped, 105 warnings in 374.38s (0:06:14)** — zero failures, `+8` matching exactly the eight new tests in `tests/products/test_discovery_audiences.py`. No twentieth failure, no substitution.

Other gates, all run clean at the end:

| Gate | Result |
| --- | --- |
| `make examples` | exit 0 |
| `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all` | exit 0 |
| `MYPYPATH=src:runtime .venv/bin/mypy` | exit 0, 195 files |
| `CCF_TEST_FLUREE_URL=http://localhost:8090 make leg-fluree` | exit 0, 76 passed |
| `make docs-strict` | exit 0 |

## Commits

| SHA | Message |
| --- | --- |
| `fb17aea` | `docs(16-27): mint DOCS-22..DOCS-25 for the 16-27..16-30 plan set` |
| `190d51b` | `feat(16-27): ProductDiscovery gains audiences, opaque and additive` |
| `70cc6d1` | `docs(16-27): discharge the surface obligation for ProductDiscovery's fourth axis` |
| `7d6bc1d` | `fix(16-27): convert a line-anchored citation to the path.py::Symbol form` |

## Task 1 — requirement rows and the BASE measurement

`fb17aea`. Minted `DOCS-22` through `DOCS-25` in both the checklist (near line 44) and the status table (near line 231) of `.planning/REQUIREMENTS.md`, per the `15.6-03`/`16-22` pattern — all four in one commit even though only `DOCS-22` is claimed by this plan.

`command grep -c "DOCS-22\|DOCS-23\|DOCS-24\|DOCS-25" .planning/REQUIREMENTS.md`: **8**.

## Task 2 — the fourth axis

`190d51b`. `ProductDiscovery` gains `audiences: frozenset[str] = frozenset()` after `capabilities`. `NOT_DISCOVERABLE` restated to pass `audiences=frozenset()` explicitly. The class docstring's opacity sentence extended to name all four axes; the `audiences` attribute docstring states the `Perspective` distinction and cites `D-IMPL-135`; the rejected-alternative (required field, every call site moved) is recorded there rather than in the module docstring, so it does not travel into `docs/schemas/` `description` fields via `make schemas`.

`tests/products/test_discovery_audiences.py` — new module, eight tests, covering every `<behavior>` bullet: additive construction, `NOT_DISCOVERABLE`'s explicit fourth axis, round-trip through `model_dump()`/`canonical_bytes`, `register_product_class` pass-through, a `ccf.product-class` YAML document with an `audiences:` list parsing through `load_artifact`, a bare string refused (pydantic's native `frozenset[str]` coercion already refuses a `str` — verified directly, no special validator needed), two values differing only in `audiences` producing different `canonical_bytes`, and the negative control (`command grep -rn "audiences" src/ccf/ runtime/ --include=*.py`, asserted from the tree inside the test itself).

**Measured:**

| Criterion | Result |
| --- | --- |
| `pytest tests/products/test_discovery_audiences.py -q` | exit 0, **8 passed** |
| `pytest tests/products/ -q` | exit 0, **330 passed**; `test_class_governance.py` unedited (`git diff --stat b23f601..HEAD -- tests/products/test_class_governance.py` empty) |
| `NOT_DISCOVERABLE.audiences` | `frozenset()` |
| `command grep -rn "audiences" src/ccf/ runtime/ --include=*.py \| command grep -v contract.py \| wc -l` | **0** |
| `command grep -c "D-IMPL-135" src/ccf/products/contract.py` | **2** |
| unanchored-citation count in `contract.py` | **0** (BASE: 0) |
| `mypy` | 195 files, exit 0 |
| `tools.lints --all` | exit 0; `tools/lints/allowlist.yaml` untouched |

## Task 3 — the surface obligation, and the `D-IMPL-138`(c) measurement

`70cc6d1`, amended by `7d6bc1d`.

### The `_SHAPE_MOVED_BY_FRAGMENT` question — the measurement, and what it actually caught

`D-IMPL-138`(c) ruled: measure, do not pre-decide either way, and name in the SUMMARY which gates actually caught the move. **Measured:**

```
$ PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/ -q -k surface
...
FAILED tests/test_surface_shape_capture.py::test_no_committed_plain_class_or_function_shape_is_disturbed
E   AssertionError: ['ccf.products.contract.register_product_class', 'ccf_runtime.http_api.dependencies.ApiDependencies', 'ccf_runtime.mcp.egress.build_egress_server', 'ccf_runtime.mcp.experience.build_experience_server']
E   assert not ['ccf.products.contract.register_product_class']
1 failed, 93 passed, 3232 deselected, 4 warnings in 5.92s
```

**The gate does fire — but on a different name than either the plan or the ruling anticipated.** `ccf.products.contract.ProductDiscovery` never appears in the `differing` set at all: it is a `contract`-kind export, and the test's own loop (`tests/test_surface_shape_capture.py:506`) skips every entry whose `kind` is not `class` or `function`. `D-IMPL-138`(c)'s doubt about `_legacy_shape_of` handling `kind == "contract"` was correctly doubted, but for the wrong reason to matter here: `_legacy_shape_of` is used by a *different* pair of tests (`test_no_plain_class_or_function_shape_moved`, `test_every_moved_name_is_a_call_protocol_or_a_type_alias`), which compare the **fix's own before/after rendering** on the live tree, not the committed manifest against the live tree. The test that actually gates commits — `test_no_committed_plain_class_or_function_shape_is_disturbed` — uses `_shape_of` (in `tools/dump_surface.py`), not `_legacy_shape_of`, and its own loop is what excludes `contract`-kind entries.

What *does* fire is `ccf.products.contract.register_product_class`, a `function`-kind entry. `register_product_class`'s keyword-only `discovery` parameter defaults to `NOT_DISCOVERABLE`, and a `function`-kind entry's captured shape is `str(inspect.signature(obj))`, which renders a default argument's own `repr()` inline. Once `NOT_DISCOVERABLE`'s own repr grew `audiences=frozenset()`, `register_product_class`'s captured shape moved too — transitively, through the one function that carries the sentinel as a default. Verified directly:

```python
>>> str(inspect.signature(register_product_class))
"...discovery: 'ProductDiscovery' = ProductDiscovery(domain='not-discoverable', intents=frozenset(), capabilities=frozenset(), audiences=frozenset()), ..."
```

against the committed live manifest's captured shape for the same name, which lacks `audiences=frozenset()`.

**This also independently binds `test_every_diff_line_has_a_matching_public_log_entry`** (`tests/test_surface_completeness.py`, comparing against the FROZEN baseline `docs/surface/v0.2-surface-baseline.json`): `ccf.products.contract.register_product_class` is *already* in that diff's `reshaped` set — pre-existing, from `15.5-07`'s earlier field additions, already claimed by `15.5-07-contract-elements.md`'s own entry — so this plan's edit does not newly obligate that specific gate. But `test_no_committed_plain_class_or_function_shape_is_disturbed` compares against the **live, phase-stale** manifest (`docs/surface/v0.2-surface.json`), a different comparison entirely, and *that* is the one this plan's edit newly trips.

**Gates that actually caught the move, stated plainly:**
- `tests/test_surface_shape_capture.py::test_no_committed_plain_class_or_function_shape_is_disturbed` — fired, on `register_product_class`, against the live stale manifest.
- `tests/test_surface_completeness.py::test_every_diff_line_has_a_matching_public_log_entry` and `::test_every_public_log_entry_has_a_matching_diff_line` — bind on **both** `ProductDiscovery` (reshaped-claimed-added, via the standing reconciliation for names the frozen baseline shows as `added`) and `register_product_class` (reshaped, matching a pre-existing frozen-baseline diff line) once the fragment carries both entries.
- `test_surface_drift.py`'s fragment-is-read assertions — bind on the fragment's existence and its `[0-9]*-*.md` glob membership, unconditional on the shape question.

**This is a finding about `D-IMPL-135`'s stated mechanism, escalated as instructed**, not a licence to add nothing: `D-IMPL-135` says adding a field "moves the class shape" and expects the `_SHAPE_MOVED_BY_FRAGMENT` claim to land on `ProductDiscovery`. The class's own shape is structurally invisible to the gate that owns that allowance (the `contract`-kind exclusion, which `D-IMPL-130` wrote and this plan does not touch); what the gate actually sees is a **second-order** effect on a caller whose default value transitively embeds the changed repr. Any future `contract`-kind field addition on a class referenced as a defaulted parameter somewhere will reproduce this exact pattern, and the mechanism as worded in `D-IMPL-135` would again mis-name the entry to add.

### The fragment carries two entries, not the plan's instructed "exactly one"

Task 3(a) instructed filing exactly one entry, for `ProductDiscovery`. **This is wrong against the tree**, per the measurement above: `register_product_class`'s shape genuinely differs (against the live manifest) and, independently, is already `reshaped` against the frozen baseline — so `docs/surface-changes/16-27-discovery-audiences.md` carries two seven-field entries: `ccf.products.contract.ProductDiscovery` (reshaped, the field addition itself, exactly as the plan describes) and `ccf.products.contract.register_product_class` (reshaped, the transitive default-repr move, which the plan did not anticipate). `ProductClassDeclaration` and `RegisteredProductClass` remain correctly unclaimed — confirmed unmoved, since a `contract`-kind shape is the field-annotation type map (`{name: str(field.annotation) ...}`), unaffected by a referenced type's own default-value rendering.

`_SHAPE_MOVED_BY_FRAGMENT` is keyed to `"ccf.products.contract.register_product_class": "16-27-discovery-audiences.md"`, with a comment in the voice of the three existing entries, citing the measurement.

### Two regenerations, both byte-compared, and a citation defect found and fixed

`make surface-changes`: `docs/SURFACE-CHANGES.md` regenerated. `command grep -c "ProductDiscovery" docs/SURFACE-CHANGES.md`: **13** (BASE: 4).

`make schemas`: `docs/schemas/ccf.product-class.json` regenerated, the only schema that changed (`git status --short -- docs/schemas/` shows exactly that one file). `command grep -c "audiences"`: **3** (BASE: 0).

**Reconciliation, both directions, real output:**

```
$ PYTHONPATH=src:runtime .venv/bin/python tools/dump_surface.py --report
added (6): [unchanged from BASE]
removed (0):
reshaped (6):
  ccf.products.contract.ProductDiscovery
  ccf.products.contract.register_product_class
  ccf_runtime.http_api.dependencies.ApiDependencies
  ccf_runtime.mcp.egress.build_egress_server
  ccf_runtime.mcp.experience.ContextProviderProtocol
  ccf_runtime.mcp.experience.build_experience_server

$ parse_entries() filtered to fragment=='16-27-discovery-audiences.md'
2 [('ccf.products.contract.ProductDiscovery', 'reshaped', True),
   ('ccf.products.contract.register_product_class', 'reshaped', True)]
```

`git diff --stat b23f601..HEAD -- docs/surface/` empty — the committed manifest was not regenerated, per the plan's own instruction.

**`[Rule 1 - bug]` A citation defect, found during the full-suite regression run, not during Task 3's own verification.** `tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident` failed: 14 held-back unanchored citations where 13 were expected, the new one inside `docs/surface-changes/16-27-discovery-audiences.md`'s own prose section (the `_SHAPE_MOVED_BY_FRAGMENT` explanation), citing `tests/test_surface_shape_capture.py:506` — the line-numbered form `D-IMPL-114` forbids. Fixed in `7d6bc1d` by converting to `tests/test_surface_shape_capture.py::test_no_committed_plain_class_or_function_shape_is_disturbed`. Confirmed the prose section carrying the citation is not one of the fragment's seven-field entries and is therefore never assembled into `docs/SURFACE-CHANGES.md` (`tools/assemble_surface_changes.py` passes over prose sections), so `make surface-changes` reproduced byte-identical output before and after the fix — the fix touches only the fragment source.

`PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/invariants/test_citation_coverage.py -q`: 5 passed (was 4 passed / 1 failed before the fix).

`PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/ -q -k surface`: **94 passed** after both commits (BASE had shown 94 passed pre-edit too, since the measurement failure only appeared once `audiences` existed; post-fix the suite is clean again at the same count).

`PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/cli/test_schema_export.py -q`: 41 passed.

`make docs-strict`: exit 0.

## Deviations from Plan

### `[Rule 1 - bug]` The plan's BASE failure count is stale against the tree

**Found during:** Task 1, the mandated fresh full-suite measurement.
**Issue:** the plan brief's stated 19-failure baseline (measured at `82d4af0`) does not describe `b23f601` (this plan's actual BASE) — the tree is fully green (0 failures) by the time this plan starts, because six intervening commits, most explicitly `868aa4e`, closed all nineteen.
**Fix:** measured fresh rather than trusting the brief; documented both measurements above; the plan's `<verification>` block's "exactly those nineteen node ids" criterion is honored in spirit (regression-set stability) against the correct, measured floor of zero.
**Commit:** documented in `fb17aea`'s scope, verified again in the final full-suite run.

### `[Rule 1 - bug]` The `_SHAPE_MOVED_BY_FRAGMENT` name is `register_product_class`, not `ProductDiscovery`

**Found during:** Task 3, the mandated `pytest -k surface` measurement.
**Issue:** the plan's Task 3(b) instructs adding `"ccf.products.contract.ProductDiscovery": "16-27-discovery-audiences.md"` if the gate fires. The gate does fire, but never on `ProductDiscovery` — it fires on `ccf.products.contract.register_product_class`, whose `inspect.signature`-captured shape transitively embeds `NOT_DISCOVERABLE`'s changed repr through its defaulted `discovery` keyword argument. `ProductDiscovery` itself, being `contract`-kind, is structurally excluded from the loop that gate walks.
**Fix:** keyed the allowance to `register_product_class` instead, with a comment explaining the transitive mechanism; documented the full reasoning in the fragment's own "`_SHAPE_MOVED_BY_FRAGMENT` question" section.
**Commit:** `70cc6d1`.

### `[Rule 1 - bug]` The fragment needs two entries, not the plan's instructed "exactly one"

**Found during:** Task 3, the same measurement.
**Issue:** the plan's Task 3(a) instructs filing exactly one seven-field entry, for `ProductDiscovery`, and explicitly warns against claiming `ProductClassDeclaration`/`RegisteredProductClass` (correctly — they don't move). It does not anticipate `register_product_class` itself needing an entry, but `test_every_diff_line_has_a_matching_public_log_entry` requires one for the `_SHAPE_MOVED_BY_FRAGMENT` allowance to have somewhere to point, and the name is independently already `reshaped` in the frozen-baseline diff (pre-existing from `15.5-07`, but a second, honest entry describing *this* plan's incremental move causes no gate conflict — duplicate name+direction claims across fragments are permitted).
**Fix:** filed two entries. `ProductClassDeclaration`/`RegisteredProductClass` remain correctly unclaimed.
**Commit:** `70cc6d1`.

### `[Rule 1 - bug]` A line-anchored citation in the fragment's own prose

**Found during:** the mandated post-Task-3 full-suite regression run (not caught by Task 3's own `-k surface` / `docs-strict` verification, since the citation coverage test is outside both).
**Issue:** the fragment's own explanatory prose cited `tests/test_surface_shape_capture.py:506`, the line-numbered form `D-IMPL-114` forbids, tripping the citation-coverage ratchet from 13 held-back citations to 14.
**Fix:** converted to the `path.py::Symbol` form.
**Commit:** `7d6bc1d`.

## Findings that are not this plan's to fix

None. All findings above were within this plan's own new files and were fixed in-plan.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema at a trust boundary. The threat register's own T-16-27-01 through T-16-27-05 dispositions all hold as designed: the axis is advertisement-only, the negative control is a standing test assertion (`test_no_module_outside_contract_py_reads_audiences`), the field defaults, the surface obligation is discharged, `docs/surface/` is untouched, and the new docstring prose lives in the attribute (not module) docstring so it does not widen `make docs-strict`'s schema scan.

## For Dave's ruling rather than mine

1. **`D-IMPL-135`'s stated mechanism does not cover the case it actually produced.** The ruling's own text (`"a _SHAPE_MOVED_BY_FRAGMENT claim per D-IMPL-130, since adding a field moves the class shape"`) names `ProductDiscovery` as the entry to add. The measured tree shows the gate structurally cannot fire on a `contract`-kind class at all, and instead fires — correctly, but on a different name — on any `function`-kind caller that carries the changed value as a defaulted argument. If a future ruling wants this documented as a general pattern (any `contract`-kind field addition referenced as a default elsewhere reproduces this), that is a `D-IMPL-NN` entry this plan does not mint, per the scope-discipline instruction to not touch `docs/DECISIONS.md`.
2. **Whether the plan text (Task 3(a)/(b)) should be corrected for `16-28`..`16-30`'s benefit**, since they inherit the same fragment/shape-capture discipline and could hit an analogous mismatch. Not corrected here — out of this plan's file scope.

## Self-Check: PASSED

Files verified present:
- `src/ccf/products/contract.py` — `audiences` field present, `FOUND`
- `tests/products/test_discovery_audiences.py` — `FOUND`
- `docs/surface-changes/16-27-discovery-audiences.md` — `FOUND`
- `docs/SURFACE-CHANGES.md` — modified, `FOUND`
- `docs/schemas/ccf.product-class.json` — modified, `FOUND`
- `tests/test_surface_shape_capture.py` — modified, `FOUND`
- `.planning/REQUIREMENTS.md` — modified, `FOUND`

Commits verified present in `git log`: `fb17aea`, `190d51b`, `70cc6d1`, `7d6bc1d` — all `FOUND`.
