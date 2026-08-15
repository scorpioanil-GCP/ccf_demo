---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 30
subsystem: deployment-config
tags: [pydantic, deployment-manifest, single-file-config, control-plane, yaml, content-addressing]

requires:
  - phase: 16-27
    provides: ProductDiscovery.audiences (D-IMPL-135), the surface obligation pattern
  - phase: 16-28
    provides: DeploymentConfig, DEPLOYMENT_CONFIG (ccf.deployment-config), the parse layer of D-IMPL-136
  - phase: 16-29
    provides: derive_deployment, DerivedDeployment, the D-IMPL-138(a) three-line adopter rule, HW1_SINGLE_FILE_DOCUMENT
provides:
  - "load_config_and_boot(config_path, *, registry, connection=None, tenant_id=None) -> BootedFabric — the single-file front door, boots identically to load_and_boot"
  - "_preflight_entries and _register_and_boot, extracted from load_and_boot's body and called by both entry points — one register loop, one preflight, two doors"
  - "The equivalence proof, in two halves: tests/deployment/test_config_equivalence.py (synthetic deployment, full boot, both forms) and tests/examples/test_s1_00_config_equivalence.py (HW-1's real committed documents, content-address comparison, no boot)"
  - "The named constant 16-31 must change to repoint the equivalence test at its frozen fixture: HW1_MULTIFILE_DIR in tests/examples/test_s1_00_config_equivalence.py"
affects: [16-31]

tech-stack:
  added: []
  patterns:
    - "Extract, do not duplicate: the register loop and the per-entry preflight live once in manifest.py; config.py's load_config_and_boot imports and calls them rather than carrying copies"
    - "Two-half equivalence proof: a synthetic full-boot comparison (proves the whole path including boot()) plus a real-deployment content-address comparison with no boot (proves the addressing claim on a committed, measured corpus)"
    - "Pairing by class_id, not by manifest key, when comparing two authoring forms whose key vocabularies differ by design"

key-files:
  created:
    - tests/deployment/test_config_equivalence.py
    - tests/examples/test_s1_00_config_equivalence.py
    - tests/examples/fixtures/s1_00_ccf_config.yaml
    - docs/surface-changes/16-30-config-boot-equivalence.md
  modified:
    - src/ccf/deployment/manifest.py
    - src/ccf/deployment/config.py
    - src/ccf/deployment/__init__.py
    - tests/deployment/test_config_derivation.py
    - docs/SURFACE-CHANGES.md

key-decisions:
  - "BASE re-measured fresh at 4ee3760: 3301 passed, 118 skipped, 0 failed — confirms the orchestrator's independent measurement exactly. The plan's own <verification> section still carries the nineteen-failure claim (16 in test_spine_separation.py, 2 in test_gate_two_call_shape.py, 1 in test_citation_coverage.py); none of the nineteen reproduce. This is the same stale-baseline defect 16-29 already disputed, carried forward unedited into this plan's text; disputed again here with the measurement, not worked around."
  - "[Rule 3 - blocking fix] tests/deployment/test_config_derivation.py::test_derive_deployment_reads_no_file_and_no_environment scanned the WHOLE config.py module source for 'Path(' / 'os.environ' / 'open('. load_config_and_boot legitimately performs file I/O (parsing a real ccf_config.yaml off disk) in the same module derive_deployment lives in, which the whole-module scan cannot distinguish from a purity regression in derive_deployment itself. Narrowed the scan to derive_deployment plus every private helper actually DEFINED in config.py (read dynamically off the module, excluding functions imported from ccf.deployment.manifest for load_config_and_boot to call) — which is exactly what the test's own docstring already claimed to cover. derive_deployment's purity is still asserted with the same three forbidden substrings; the new loader's I/O is no longer mistaken for a regression in it."
  - "Task 3's action text asks this plan to restate three open escalations for Dave. Measured against docs/DECISIONS.md, all three — plus a fourth the plan text does not mention — are already RESOLVED under D-IMPL-138 (Dave, 2026-08-15, i.e. today), and the citation-coverage item is recorded there as already closed and dropped rather than ruled. Reported as resolved rather than restated as pending; see 'Escalations' below."

requirements-completed: [DOCS-25]

duration: ~50min
completed: 2026-08-15
---

# Phase 16 Plan 30: Config boot equivalence Summary

**`load_config_and_boot` boots a fabric from one `ccf_config.yaml` through the exact register loop and preflight `load_and_boot` already uses — extracted, not duplicated — and the compatibility claim is now a regression test with two halves: a full-boot comparison over a synthetic deployment, and an eight-document content-address comparison against HW-1's real, committed multi-file corpus.**

## Performance

- **Duration:** ~50 min (includes an unavoidable ~6.5 min full-suite baseline measurement, run fresh per the orchestrator's brief, plus a second full-suite run at plan close, plus `make examples`, `make docs-strict`, and `make leg-fluree` against a live server)
- **Completed:** 2026-08-15
- **Tasks:** 3 (extraction + front door, equivalence proof, surface claim)
- **Files created:** 4
- **Files modified:** 5

## The BASE baseline — measured fresh, and it confirms the orchestrator's figure exactly

```
3301 passed, 118 skipped, 105 warnings in 375.94s (0:06:15)
```

**Zero failures**, at `4ee3760`, matching the orchestrator's own independent measurement stated in the prompt exactly. The plan's own `<verification>` section still claims a **nineteen-failure** BASE (16 in `tests/examples/test_spine_separation.py`, 2 in `tests/products/test_gate_two_call_shape.py`, 1 in `tests/invariants/test_citation_coverage.py`) — this is the identical stale figure `16-27`, `16-28` and `16-29` all carried and all disputed, present unedited in `16-30`'s own plan text. None of the nineteen reproduce against the tree. Verified directly: `pytest tests/invariants/test_citation_coverage.py -q` → `5 passed`; `pytest tests/examples/ -q` → `343 passed, 37 skipped` (zero failures, not sixteen). This is a plan-text defect inherited across four plans, not a mechanism defect — reported per the "expect the plan's own text to be wrong somewhere, and say so" instruction.

**Post-plan measurement**, full suite, same command:

```
3305 passed, 118 skipped, 105 warnings in 376.27s (0:06:16)
```

**Zero failures**, delta of +4 passed over BASE: exactly the four new tests this plan wrote (2 in `tests/deployment/test_config_equivalence.py`, 2 in `tests/examples/test_s1_00_config_equivalence.py`). No regression; no substitution.

## Accomplishments

- **Task 1 — one registration path, two front doors.** `src/ccf/deployment/manifest.py::load_and_boot`'s body is split into two private helpers — `_preflight_entries` (the per-entry role/registration/containment preflight, moved verbatim, comments included) and `_register_and_boot` (phase two: the register loop, the `boot()` call, and the `BootedFabric` construction, moved verbatim). `load_and_boot`'s signature, docstring and behavior are unchanged; `tests/deployment/test_manifest.py` — the twelve-property regression net — passes with a byte-empty diff against `BASE`. `src/ccf/deployment/config.py::load_config_and_boot` is the config form's sibling: parses a `ccf_config.yaml`, derives via `derive_deployment`, imports and calls the same three preflight functions and the same `_register_and_boot`, then boots. `command grep -c "register_versioned\|register_typed" src/ccf/deployment/config.py` is **0** — the register loop exists exactly once, in `manifest.py`.
- **Task 2 — the equivalence proof, in two halves.** Half A (`tests/deployment/test_config_equivalence.py`) proves the whole boot path — preflight, parse, register, pin, boot — over a synthetic six-artifact deployment authored twice from one set of Python literals in the same module: an equal `ResolvedPins` (`model_dump_json()`), equal `BootedFabric.artifacts` by `canonical_bytes`, equal `tenant_id`/`survivor_cap`, non-vacuous (≥5 pins, actual count 6), plus a negative control (perturbing `half_life_seconds` moves exactly one pin). Half B (`tests/examples/test_s1_00_config_equivalence.py`) proves the content-address claim on HW-1's real, committed, measured deployment: eight documents read from `examples/s1-00-companies-over-revenue/artifacts/config/` (read-only) register at **identical** content addresses to a hand-authored single-file fixture (`tests/examples/fixtures/s1_00_ccf_config.yaml`), paired by `class_id` since the two forms use different key vocabularies by design. 8/8 addresses identical, exactly one `role: load` on each side, non-vacuity asserted at 8. The two `MEASUREMENT.md` recipes (10 files, 99 lines) are reproduced as an in-module assertion.
- **Task 3 — the surface claim.** `docs/surface-changes/16-30-config-boot-equivalence.md` claims the two names `--report` newly lists (`ccf.deployment.config.load_config_and_boot`, `ccf.deployment.load_config_and_boot`), both `added`. `docs/SURFACE-CHANGES.md` regenerated via `make surface-changes`. `tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added` — which failed with exactly those two names as "added but unclaimed" after Tasks 1–2 — passes cleanly once the fragment exists.
- Found and resolved one genuine test/code conflict inherent to adding an I/O-performing public function to a module a prior plan's test had scanned whole-module for purity (see Deviations).

## Half A — the two `ResolvedPins`, printed

Both forms produce this identical `model_dump_json()` (6 entries, in manifest order):

```json
{"entries":[
  {"key":"product_class","version":"90a3c0b4a359e6bf2a61c95faa2847b4397d353a51fa59242ceb937ff5d14193","class_id":"ccf.product-class","registration":"typed"},
  {"key":"temporal.as-of-boundary","version":"1d21552dd6a732a593aed688bd13ec8afca4ac847f9545369dad28ef6c885d0d","class_id":"ccf.operator-parameters.temporal","registration":"typed"},
  {"key":"resolution","version":"e8d918bd020a710e7039f8fac074ea6a5b40f2fe0b23d833eb20c2b470468172","class_id":"ccf.resolution-spec","registration":"typed"},
  {"key":"half_life","version":"cf53063b2caa5eeead1472279a84917b2ed58a50f36231b9205a474e6f221099","class_id":"ccf.half-life-table","registration":"typed"},
  {"key":"policy","version":"48e73b937347eecb885f954f34fed4138fef6dd1df4a52bc1b329c7f9721f76a","class_id":"fixture.equivalence-policy-bundle","registration":"typed"},
  {"key":"default_perspective","version":"300e61daa8b2b293459cd6eabb9b62f7a3b57ba270010ff2d85fd6b477c8e8b7","class_id":"ccf.perspective","registration":"typed"}
]}
```

`multi.pins.model_dump_json() == config.pins.model_dump_json()` → `True`. Entry count: 6 (≥5, non-vacuous). Negative control: perturbing `half_life_seconds` from 3600 to 7200 in the single-file form changed exactly `{"half_life"}` and left the other five pin versions unchanged — asserted in `test_perturbing_the_single_file_form_moves_exactly_one_pin`.

## Half B — the eight-row content-address table

| `class_id` | multi-file address | single-file address | equal |
|---|---|---|---|
| `ccf.debt-profile` | `ab274350d063eeccca801e834dce077f9e70b7caeff7db23f1faf3e2cca3a856` | `ab274350d063eeccca801e834dce077f9e70b7caeff7db23f1faf3e2cca3a856` | yes |
| `ccf.half-life-table` | `7a384544defbfa4f5c71ae4ab3129842a123e3c622551944a0d84e108b5813b8` | `7a384544defbfa4f5c71ae4ab3129842a123e3c622551944a0d84e108b5813b8` | yes |
| `ccf.operator-parameters.temporal` | `1d21552dd6a732a593aed688bd13ec8afca4ac847f9545369dad28ef6c885d0d` | `1d21552dd6a732a593aed688bd13ec8afca4ac847f9545369dad28ef6c885d0d` | yes |
| `ccf.perspective` | `fc69f883aee844350f34b62ec17d36229cd752ac8c6ca300511aa7ee6dc1250f` | `fc69f883aee844350f34b62ec17d36229cd752ac8c6ca300511aa7ee6dc1250f` | yes |
| `ccf.product-class` | `4673999329f2a210c9c7dc36e5ddd3053a8733dbd76fab25de689ec8da3dcf1d` | `4673999329f2a210c9c7dc36e5ddd3053a8733dbd76fab25de689ec8da3dcf1d` | yes |
| `ccf.resolution-spec` | `93ee972fffa467e5858ac0795cb1e0fbf3f7dfc020d8f4fcc8e949ef4b16d626` | `93ee972fffa467e5858ac0795cb1e0fbf3f7dfc020d8f4fcc8e949ef4b16d626` | yes |
| `hw1.policy-bundle` | `dd2c515f43012c7908ff9bd82289553be2b2f8d3900291c265e1cc5abeda0f5f` | `dd2c515f43012c7908ff9bd82289553be2b2f8d3900291c265e1cc5abeda0f5f` | yes |
| `hw1.request-contract` | `56fe50ea1c46ad65af55dc484eb91e1e02aeae49427faeac662d74788b4ebebe` | `56fe50ea1c46ad65af55dc484eb91e1e02aeae49427faeac662d74788b4ebebe` | yes |

**8 rows, 8 yeses, printed count: 8.** Exactly one `role: load` entry on each side (`hw1.request-contract`). `(class_id, role, registration)` triples match on all eight. Non-vacuity asserted at `compared == 8`.

## The named constant `16-31` must change

`tests/examples/test_s1_00_config_equivalence.py::HW1_MULTIFILE_DIR` is the single named constant every read of HW-1's multi-file documents in that module goes through (the manifest path and every artifact document path are computed from it, never threaded through a second helper). When `16-31` freezes the nine multi-file documents into `tests/deployment/fixtures/s1-00-multifile/` before converting HW-1 to single-file, repointing this test is a one-line change:

```python
HW1_MULTIFILE_DIR = (
    pathlib.Path(__file__).resolve().parents[2]
    / "examples" / "s1-00-companies-over-revenue" / "artifacts" / "config"
)
```
becomes
```python
HW1_MULTIFILE_DIR = pathlib.Path(__file__).resolve().parents[1] / "deployment" / "fixtures" / "s1-00-multifile"
```
(exact relative path to be confirmed against `16-31`'s actual fixture location; the point is that only this one assignment changes.)

## Task Commits

1. **Task 1: One registration path, two front doors** — `2257a44` (feat) — `src/ccf/deployment/manifest.py`, `src/ccf/deployment/config.py`, `src/ccf/deployment/__init__.py`, `tests/deployment/test_config_derivation.py` (the Rule 3 fix, see Deviations)
2. **Task 2: The equivalence proof, in two halves** — `7cc6c65` (test) — `tests/deployment/test_config_equivalence.py`, `tests/examples/test_s1_00_config_equivalence.py`, `tests/examples/fixtures/s1_00_ccf_config.yaml`
3. **Task 3: Claim the surface and close the plan set** — `8734bb3` (docs) — `docs/surface-changes/16-30-config-boot-equivalence.md`, `docs/SURFACE-CHANGES.md`

No separate plan-metadata commit beyond these three per this executor's scope — `state.*`/`roadmap.*` SDK writers were **not** invoked (five confirmed corruptions of `.planning/STATE.md`; the orchestrator hand-edits it).

## Gate Results

| Gate | Result |
|---|---|
| `pytest tests/deployment/test_manifest.py -q` | 39 passed; `git diff --stat $BASE..HEAD -- tests/deployment/test_manifest.py` empty |
| `load_and_boot` signature vs BASE | byte-identical (`inspect.signature` string match) |
| `dump_surface.py --report`: `load_and_boot` under `reshaped`/`removed` | absent from both — neither |
| `command grep -c "register_versioned" src/ccf/deployment/manifest.py` | **7** (BASE **7** — matches; one candidate docstring mention was reworded during Task 1 to avoid a spurious +1) |
| `command grep -c "register_versioned\|register_typed" src/ccf/deployment/config.py` | **0** |
| `pytest tests/deployment/ -q` | 236 passed (after Task 3: `test_the_phases_fragments_claim_exactly_what_was_added` also passes) |
| `pytest tests/deployment/test_config_equivalence.py tests/examples/test_s1_00_config_equivalence.py -q` | 4 passed |
| `pytest tests/examples/ -q` | 343 passed, 37 skipped, **0 failed** (plan text expected exactly 16 named failures from `test_spine_separation.py`; none reproduce — same stale-baseline dispute as above) |
| `git diff --stat $BASE..HEAD -- examples/` | empty |
| `command grep -hvE '...' .../config/*.yaml \| command grep -c '[^[:space:]]'` | **99** (MEASUREMENT.md's committed figure) |
| `ls .../config/*.yaml \| wc -l` | **10** |
| mypy (strict, `src`+`runtime`) | `Success: no issues found in 196 source files` |
| `tools.lints --all` | exit 0; `tools/lints/allowlist.yaml` diff empty |
| `dump_surface.py --report` (final) | 14 added total; 8 attributable to this plan set (`16-27`–`16-30`), union of the four fragments' claims equals this 8-name subset exactly, both directions |
| `make surface-changes` | exit 0; `docs/SURFACE-CHANGES.md` diff non-empty (53 insertions, 2 deletions vs. pre-Task-3 working tree) |
| `pytest tests/ -q -k surface` | 94 passed |
| `pytest tests/deployment/test_class_lookup.py -q` | 36 passed |
| `make docs-strict` | exit 0 |
| `make examples` | exit 0 (all ten network-free examples plus the external client legs) |
| `CCF_TEST_FLUREE_URL=http://localhost:8090 make leg-fluree` | exit 0, 76 passed |
| Full suite `pytest -q` | BASE 3301 passed/118 skipped/0 failed → post-plan 3305 passed/118 skipped/0 failed |
| `git diff --stat $BASE..HEAD -- docs/surface/ examples/ tools/lints/allowlist.yaml pyproject.toml .planning/ROADMAP.md docs/DECISIONS.md 16-CONTEXT.md 16-RESEARCH.md 16-PATTERNS.md docs/superpowers/` | empty, all paths |

## Escalations — Task 3 asked me to restate three; all are already resolved

Task 3's `<action>` text asks this plan to restate three open escalations "so they reach Dave in one place." Measured against `docs/DECISIONS.md` at this branch tip, **all three are already ruled, plus a fourth the plan text does not mention**, all under one entry dated *today*:

**`D-IMPL-138` — RESOLVED, 2026-08-15, Dave.** Covers, verbatim from the decision log:

1. *Citation coverage* — **not an open escalation at all**: `docs/DECISIONS.md` records it as "already closed: `tests/invariants/test_citation_coverage.py` passes at HEAD, resolved by commit `868aa4e` after the plans were written. It is dropped rather than ruled." Verified directly in this plan: `pytest tests/invariants/test_citation_coverage.py -q` → `5 passed`.
2. *Three bookkeeping lines vs. design spec §6.1's two* — **Ruled: accept three, and correct §6.1's prose from two to three.** "Not load-bearing." I have **not** made that prose correction — `docs/superpowers/specs/` is out of scope for this plan by the orchestrator's own scope discipline, and the ruling's correction belongs to whoever next touches that document, not to a config/boot plan.
3. *`D-IMPL-135`'s `_SHAPE_MOVED_BY_FRAGMENT` obligation and `contract`-kind entries* — **Ruled: keep the plan's measure-then-decide; do not pre-decide either way.** This is `16-27`'s own measurement to report, not something this plan re-derives.
4. *(Not in Task 3's list, but ruled in the same entry) the four `DeploymentManifest`-parity fields beyond design spec §4.1* — **Ruled: accept all four**, on two grounds (two are required and HW-1's own fixture is unwritable without them; two are unused by HW-1 but load-bearing for §10's "compatibility is absolute").

Also ruled in the same `D-IMPL-138` entry: `depends_on` for `16-14`…`16-19` should rewire to follow `16-30` (three real wave collisions, none of the six documentation plans currently depending on the four this plan set touches). That is a `.planning/ROADMAP.md` / plan-frontmatter concern, explicitly out of scope for this executor (protected files) — flagged for the orchestrator, not acted on here.

**Nothing further escalates from this plan.** I record the resolution rather than restating stale questions as pending.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking fix] `test_derive_deployment_reads_no_file_and_no_environment`'s whole-module purity scan conflicted with Task 1's required `load_config_and_boot`**
- **Found during:** Task 1, first `pytest tests/deployment/test_config_derivation.py` run after adding `load_config_and_boot` to `src/ccf/deployment/config.py`
- **Issue:** The test (shipped by `16-29`, unmodified by this plan's `<files>` list) asserted `"Path(" not in inspect.getsource(config_module)` — a **whole-module** scan. `load_config_and_boot` is a `must_haves.artifacts` requirement of this plan, explicitly required to live in `config.py` (`provides: load_config_and_boot`, `contains: load_config_and_boot`), and it legitimately performs file I/O — that is its entire job, the config form's counterpart to `load_and_boot`'s own I/O in `manifest.py`. The whole-module scan could not tell "the new loader reads a file, as documented" apart from "`derive_deployment` regressed its purity," and failed on the former.
- **Fix:** Narrowed the scan to `derive_deployment` plus every private (`_`-prefixed) function **actually defined in** `config_module` (checked via `obj.__module__ == config_module.__name__`, which also excludes the private helpers `load_config_and_boot` imports from `ccf.deployment.manifest` to call — those are covered by `manifest.py`'s own test suite, not this one). This is exactly the scope the test's own docstring already claimed ("`derive_deployment` and its private helpers"); the implementation is what had drifted wider than its stated intent.
- **Files modified:** `tests/deployment/test_config_derivation.py` (not in this task's `<files>` list; flagged here per the plan's own escape-valve instruction)
- **Verification:** `derive_deployment`'s purity is still asserted with the same three forbidden substrings (`open(`, `os.environ`, `Path(`/`pathlib.Path(`); confirmed the narrowed scan still fails if any of those strings is reintroduced into `derive_deployment` or one of its own private helpers (manually verified by temporarily reintroducing `os.environ.get` into `_derive_entry` and observing the test fail, then reverting)
- **Committed in:** `2257a44` (Task 1 commit)

**2. [minor, self-corrected] A new docstring mention of `register_versioned` in `_register_and_boot` tripped the exact `command grep -c` count against BASE**
- **Found during:** Task 1, acceptance-criteria verification (`command grep -c "register_versioned" src/ccf/deployment/manifest.py` equals BASE)
- **Issue:** BASE = 7; my first draft of `_register_and_boot`'s docstring added an eighth literal mention of `register_versioned` in prose, making the register-loop-exists-once acceptance criterion fail on a raw substring count even though no code was duplicated
- **Fix:** Reworded one sentence in `_register_and_boot`'s docstring to reference "the D-05 bump-check dispatch's own narrowing" instead of repeating the literal identifier
- **Files modified:** `src/ccf/deployment/manifest.py` (within Task 1, before its commit)
- **Verification:** `command grep -c "register_versioned" src/ccf/deployment/manifest.py` → 7, matching BASE exactly
- **Committed in:** `2257a44` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking test-scope fix, 1 self-corrected grep-count mismatch). Neither weakens any assertion's coverage — deviation 1 narrows a scan to what its own docstring already claimed to cover (no coverage lost, a false positive removed), and deviation 2 is a wording change with no test-coverage effect at all.

## Known Stubs

None. Every artifact `load_config_and_boot` produces is a real, registered, pinned artifact; nothing here is placeholder data or an unwired path.

## Threat Flags

None. Every threat register entry (`T-16-30-01` through `T-16-30-08`, plus `T-16-30-SC`) is mitigated as designed; no new surface outside the register was introduced. `load_config_and_boot` adds no new trust boundary beyond what `T-16-30-01` through `T-16-30-03` already name (the two authoring forms, the shared register loop, the shared preflight).

## Issues Encountered

None beyond the two deviations above and the stale plan-text baseline/escalation claims (both reported with measurement, not worked around).

## User Setup Required

None. `make leg-fluree` ran against the environment's already-reachable Fluree server (`localhost:8090`); unrelated to this plan's scope and unaffected by these changes.

## Next Phase Readiness

- `load_and_boot` and `load_config_and_boot` both ship, sharing one register loop and one preflight. `src/ccf/deployment/manifest.py`'s docstring, refusal set, and `tests/deployment/test_manifest.py` are all untouched.
- The equivalence proof is in place and green, in both halves, with printed content addresses.
- **For `16-31`:** the single named constant to change is `tests/examples/test_s1_00_config_equivalence.py::HW1_MULTIFILE_DIR` (see above). `16-31`'s first task must freeze HW-1's nine multi-file documents into `tests/deployment/fixtures/s1-00-multifile/` **before** converting `examples/s1-00-companies-over-revenue` to single-file, or this repointing has nothing to point at.
- `D-IMPL-138` already resolves every escalation this plan set produced; no further ruling is pending from `16-27` through `16-30`. Two follow-up actions it names (the design-spec §6.1 prose correction, and the `depends_on` rewiring for `16-14`…`16-19`) are out of this executor's scope (protected files) and are flagged for the orchestrator.
- No blockers.

---
*Phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar*
*Completed: 2026-08-15*

## Self-Check: PASSED

All created/modified files exist on disk; all three task commits (2257a44, 7cc6c65, 8734bb3) exist in git history.
