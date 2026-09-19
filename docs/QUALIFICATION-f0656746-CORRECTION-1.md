# Release qualification — first correction group on candidate `f0656746`

**Measured candidate:** `f0656746ec7cfeb734dfff717f388ce8c3623b6f` (`docs/QUALIFICATION-f0656746.md`,
report commit `5c404e3f` on `main`, carried onto this branch as `ae8fd6ab`).
**Disposition:** `docs/DECISIONS.md`, *RELEASE QUALIFICATION — FIRST CORRECTION GROUP GO*, recorded
at `014a8b28` before any repair.
**Correction candidate (every result below was measured on it):** `release/qualification-fixes`
at **`690cce3f`**, working tree clean. This report's commit follows it and was not measured.
**Merge and tag:** HOLD, as ruled. No commit on `main`.

Date: 2026-09-19.

---

## 1. The seventeen targeted nodes — before and after

Before = the qualification measurement on `f0656746`. After = the reruns in §3 on `690cce3f`,
every node by id. **17 of 17 pass. No node remains. No new failing node was observed in any
suite rerun.**

| # | node | before | after | repaired by |
|---|---|---|---|---|
| 1 | `tests/test_surface_completeness.py::test_every_diff_line_has_a_matching_public_log_entry` | FAIL | PASS | `690cce3f` |
| 2 | `tests/test_surface_completeness.py::test_every_public_log_entry_has_a_matching_diff_line` | FAIL | PASS | `690cce3f` |
| 3 | `tests/test_surface_shape_capture.py::test_the_serialized_manifest_carries_no_memory_addresses` | FAIL | PASS | `e4d71a45` + `690cce3f` |
| 4 | `tests/test_surface_shape_capture.py::test_no_committed_plain_class_or_function_shape_is_disturbed` | FAIL | PASS | `690cce3f` |
| 5 | `tests/examples/test_hw1_readme_expected_output.py::test_the_readme_fence_is_the_in_process_commands_output` | FAIL | PASS | `a40ba694` |
| 6 | `tests/http_api/test_openapi.py::test_the_committed_spec_matches_what_the_app_emits` | FAIL | PASS | `6b5d7bb2` |
| 7 | `tests/http_api/test_product_declared_obligation_409.py::test_no_known_refusal_kind_reaches_served_answer[composite-child-refusal]` | FAIL | PASS | `3ef52878` |
| 8 | `tests/http_api/test_product_declared_obligation_409.py::test_no_known_refusal_kind_reaches_served_answer[dependency-invalidation-refusal]` | FAIL | PASS | `3ef52878` |
| 9 | `tests/http_api/test_product_refusal_statuses.py::test_every_kind_answers_its_row_in_the_one_body[composite-child-refusal]` | FAIL | PASS | `3ef52878` |
| 10 | `tests/http_api/test_product_refusal_statuses.py::test_every_kind_answers_its_row_in_the_one_body[dependency-invalidation-refusal]` | FAIL | PASS | `3ef52878` |
| 11 | `tests/http_api/test_product_refusal_statuses.py::test_the_table_is_closed_over_the_refusal_vocabulary` | FAIL | PASS | `3ef52878` |
| 12 | `tests/http_api/test_product_refusal_statuses.py::test_the_closure_assertion_catches_a_planted_drift[extra]` | FAIL | PASS | `3ef52878` |
| 13 | `tests/http_api/test_product_refusal_statuses.py::test_the_closure_assertion_catches_a_planted_drift[removed]` | FAIL | PASS | `3ef52878` |
| 14 | `tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added` | FAIL | PASS | `690cce3f` |
| 15 | `tools/lints/tests/test_runner.py::test_the_registered_rule_set_is_exactly_these_seven` | FAIL | PASS | `5b991706` |
| 16 | `tools/lints/tests/test_runner.py::test_missing_trees_are_skipped_not_errors` | FAIL | PASS | `5b991706` |
| 17 | `tools/lints/tests/test_runner.py::test_main_exits_zero_on_a_clean_tree` | FAIL | PASS | `5b991706` |

The four HTTP-door nodes that share a parametrization (7–10) and the three closure nodes
(11–13) are seven outcomes of one cause; the counts are test outcomes, not root causes.

---

## 2. What was wrong, and the repair — by area

Each root cause was established by execution on the tree and by `git log -S` on the defining
file before anything was changed. Where a red pre-dated this branch the commit that introduced it
is named.

### 2.1 HTTP refusal handling and OpenAPI (8 nodes) — `3ef52878`, `6b5d7bb2`

**Cause.** `a25a5d10` (D-IMPL-334) and `60c3ff94` (D-IMPL-336) added `dependency-invalidation-refusal`
and `composite-child-refusal` to `REFUSAL_KINDS` without a row in the door's status table
(`runtime/ccf_runtime/http_api/refusal_status.py`, keyed by class). At the door, a recorded and
disclosed envelope of either kind failed the membership test `envelope.kind in STATUS_BY_KIND`
and control fell through to the served-answer path, which raised `UngovernedResolverResult`.
Standing on `main` since those commits; the closure test pre-dates both. The qualification
report had left this attribution "not yet established"; it now is.

**Repair.** Two rows, both `STATUS_FULFILLMENT_WITHHELD` (409), by the table's own class rule:
every `GateRefusal`-derived kind maps to 409 (the fabric's measured state conflicts with
fulfilling a well-posed request), and child admission is the composite analog of the peering
`admission-refusal` row already at 409. **Nothing else changed:** not the decision line at the
door, not disclosure (both kinds already carry their minimal sentence and permitted fields in
`src/ccf/products/disclosure.py`), not recording (the envelope is recorded before it reaches
the door), not exception handling. The closure controls still detect a planted extra row and a
removed row; the forged-kind escape control still escapes.

**OpenAPI.** The committed document's drift was separate: the skill-catalog schema changed at
`60c3ff94` (`produces`, `mcp_product`) and `4c822611` (`McpProductBinding`, D-IMPL-340) after the
last regeneration. The spec carries no per-kind refusal statuses, so the rows do not move it.
Regenerated with `make openapi` after the table repair (36 lines added, 1 removed, no path added
or removed). `public/reference/http-api.md` includes the file and rebuilt clean.

### 2.2 Public-surface manifest and log (4 nodes) + fragment-claims (1 node) — `e4d71a45`, `690cce3f`

**Cause, generator.** Two exports render a function as a parameter default —
`open_product(clock=_utc_now)` (since `2e08ff7a`, D-IMPL-343) and
`build_governed_resolver(admission_clock=_utc_now)` (since `be6c76a3`, D-IMPL-336) — and
`inspect.signature` prints such a default as `<function _utc_now at 0x…>`, a different address
in every process. The committed manifest was irreproducible on an unchanged tree; the
same-process double-build test stayed green because it rendered the same object twice.

**Cause, records.** Public names were added by phases that never wrote a surface-change fragment
(D-IMPL-304, 316, 331, 332, 333, 337); `87daab4f` (D-IMPL-336 Amendment 5) added two names and
deleted seven that `336-02` had claimed `added`, with no `removed` claim; D-IMPL-341's three
signature changes were never carried into the committed manifest; seven attribute- or
method-level claims were typed `added`/`reshaped` although the manifest records exports only;
and the fragment `r01-…` was invisible to the assembler's digit-first glob while visible to
`test_class_lookup.py`'s `*.md` glob — which is why the qualification saw one unclaimed name
differ between the two tests.

**Repair.** The generator scrubs only the address, at the manifest entry and nowhere deeper: the
parameter, its annotation and the default's *name* stay, so a real signature change still moves
the manifest. Two separate-process generations are byte-identical; `tools/dump_surface.py --check`
exits 0; the file carries no `0x…` address. The records were reconciled **from implementation
history, not by claiming what is present**: seven new fragments (`304-01`, `316-01`, `331-01`,
`332-01`, `333-01`, `336-06`, `337-01`), each naming its introducing commit and claiming exactly
what that commit added; `340-01` gains the eight names `4c822611`/`dcfb8608` added; `341-01`
claims the seven `ccf.products.expiry` exports in place of a module claim and adds
`compose_children` reshaped (`decided_at`, `8c0388dc`); `343-01` gains the two `ccf.deployment`
re-exports (`e5a64371`, CP05D-F-06, ruled to stay); the seven Amendment-5 deletions are stated
as short-lived pairs; the attribute-level claims are retyped `behavior` in place with the reason
in their `Why`; `r01` is renamed `279-01` with its two missing fields completed from its own
prose. `make surface` changed exactly three manifest lines (the 341 shapes and the two scrubbed
addresses; no export added or removed; the frozen baseline untouched); `make surface-changes`
reassembled `docs/SURFACE-CHANGES.md`.

### 2.3 hw1 README expected output (1 node) — `a40ba694`

**Cause.** Since D-IMPL-341 every served contract carries `ttl_anchor_at`, so the served bytes
changed, and with them the product's content address and the record's version. Exactly two lines
of the fence differed from `consume.py`'s stdout; `D_c`, its routing and the expiry instant did
not move. Not recorded anywhere before the qualification; this branch's own.

**Repair.** The fence is regenerated from the run. The README now states what each printed
identity is — the *content address* is the hash of the served product; the *replay record* line
is the record's own address, its name the pinned graph snapshot and its `@version` the record's
content address; the record names the product, the product does not name its record — why both
moved, what did not, and the old values. No product, policy, debt, window or data change.

### 2.4 Lint-runner tests (3 nodes) — `5b991706`

**Cause.** `c676603f` (D-IMPL-337) registered a third whole-tree rule, `guarded-provenance`,
without touching the runner's closed-set test, and that rule imported `GUARDED_TYPES` from the
installed `ccf` package while its module census walked `--base`. On any base but the real
repository every one of the nine real declarations fired as *"names a module that does not
exist"*, so the empty-tree and clean-tree fixtures exited 1. The rule, not the fixtures, broke
the runner's contract; the other two whole-tree rules derive everything from `--base`.

**Repair, rule side.** The registry is loaded by path from `<base>/src/ccf/contracts/guarded.py`
— absent: no declarations (the token-guarded census still runs); present but unloadable: one
finding, never a skip. Real tree: identical output, exit 0. **Repair, test side.** The closed set
widens to the three registered whole-tree rules (the function keeps its cited name; its docstring
carries the history), and three runner-level controls the rule never had are added: an
undeclared token-guarded class under a fixture is reported; an in-tree registry naming an absent
module is still a finding; an unloadable registry is a finding. No expected exit code was
changed and no assertion weakened.

---

## 3. Regression — what was rerun, and what was not

All on `690cce3f`, CI's quick posture (`CCF_REQUIRE_HARNESSES=1`, no substrate URL), each family
its own process. Junit files: `qualification/f0656746/correction-1/evidence.tar.gz`.

| suite | at qualification (`f0656746`) | now (`690cce3f`) | delta |
|---|---|---|---|
| A `tests/products tests/replay tests/contracts tests/deployment` | 2 028 passed, **1 failed**, 1 skipped | **2 029 passed**, 0 failed, 1 skipped | node 14 fixed; nothing new |
| B `tests/invariants` | 1 993 passed, **44 failed** | 2 089 passed, **44 failed** | the same 44 (the deferred group); the +96 passing nodes are `test_no_superseded_phrase_survives` parametrized over 25 `._README.md` files — macOS AppleDouble sidecars, git-ignored and untracked, dated 2026-09-08 — present in this working tree and absent from the detached qualification worktree; not candidate content (see §4) |
| C `tests/client tests/conformance tests/controlplane tests/graph tests/halflife` | 1 390 passed, 110 skipped | 1 390 passed, 110 skipped | none |
| D the nineteen remaining families + smoke + `tests/test_surface_*` | 1 842 passed, **13 failed**, 3 skipped | 1 854 passed, **1 failed**, 3 skipped | nodes 1–4, 6–13 fixed; the 1 is the deferred peering pin |
| E `tests/perf_gate tests/perf_smoke tests/perf_synth` | 37 passed | 37 passed | none |
| hw1: `test_hw1_readme_expected_output.py`, `test_hw1_two_transports.py`, `test_hw1_empty_fabric_refusal.py` | node 5 failed | 26 passed | node 5 fixed |
| `tools/lints/tests` | 468 passed, **3 failed** | **474 passed** | nodes 15–17 fixed; 3 controls added |
| `tools/product_gates_tests` | 48 passed | 48 passed | none |
| `tools/publish_scan_tests` + `tools/docs_tests` | 349 passed | 349 passed | none (includes the retirement-sweep currency check and the OpenAPI drift control) |
| `make lint` / `make typecheck` | 0 / clean (230 files) | 0 / clean (230 files) | none |
| `make product-gates` / `make schema-headers` | 19 trees, 326/326 / 31 dirs | same | none |
| `make docs-strict` / `make examples` | built / 3 legs MATCH | built / 3 legs MATCH (`c38d30f2…`) | none |

**The deferred group is exactly as measured before: 45 nodes, untouched.** `test_no_obligation_vocabulary.py`
42; `test_determination_authority_disclosure_delivery.py::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]`
1; `test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow` 1
(**86 unanchored citations before, 86 after** — the new fragments cite `path.py::Symbol` only);
`tests/peering/test_admission_record.py::test_claims_py_is_unchanged_so_reading_a_cannot_creep_back_in` 1.

**Not rerun, stated:** the four substrate legs (`leg-fluree`, `leg-mongo`, `leg-neo4j`,
`leg-postgres`) — no change touched substrate code; the estate example chunks F–K other than the
three hw1 modules — no change touched an example tree other than hw1's README; `ci-coverage`
(informational); and **`make test` as a single invocation**, which remains the later checkpoint the
ruling names. The two orchestration-conformance nodes remain **named, not executed**.

**Newly failing nodes in the rerun set: none.**

---

## 4. Problems the fixes created, and what was done about them

Recorded because the ruling asks for them to be identified, not discovered later.

- **Committing evidence under `docs/` made the retirement sweep count it.** The node lists and
  logs added 184 coupling rows across 4 files to `RETIREMENT-COUPLINGS.md`
  (`tools/docs_tests/test_retirement_sweep.py` went red). Moving the directory out of `docs/` was
  not enough — the sweep reads loose text anywhere in the tree — so the evidence ships as
  `qualification/f0656746/evidence.tar.gz` beside a README. The committed report is current
  without regeneration (`16cfc85e`).
- **The manifest could not simply be regenerated.** Regenerating first would have committed two
  fresh addresses; the generator had to be made deterministic before the records repair
  (`e4d71a45` before `690cce3f`).
- **The OpenAPI regeneration changes a published page.** `public/reference/http-api.md` includes
  `openapi.json`; the strict build was rerun and is clean.
- **Two commit trailers were mistyped** on the HTTP and OpenAPI commits and were rewritten before
  anything was pushed.
- **Not created by a fix, but seen only because of one:** the working tree carries 25 git-ignored
  `._*` AppleDouble sidecar files beside example READMEs (dated 2026-09-08). Suites that glob the
  filesystem rather than the index (`tests/invariants`' superseded-phrase sweep) parametrize over
  them — 96 extra passing nodes here — while a fresh checkout such as the qualification worktree
  never sees them. Harmless to every result in this report; the next fixed-candidate
  qualification should run on a fresh checkout, as the first one did, so the collected set is
  the candidate's.

---

## 5. Changed files

Repairs (by commit): `tools/lints/guarded_provenance.py`, `tools/lints/tests/test_runner.py`
(`5b991706`); `examples/hw1-companies-over-revenue/README.md` (`a40ba694`);
`runtime/ccf_runtime/http_api/refusal_status.py` (`3ef52878`); `openapi.json` (`6b5d7bb2`);
`tools/dump_surface.py` (`e4d71a45`); `docs/surface/v0.2-surface.json`, `docs/SURFACE-CHANGES.md`,
seven new and six edited fragments under `docs/surface-changes/`, `r01-…` renamed `279-01-…`
(`690cce3f`). Records: `docs/DECISIONS.md` (`014a8b28`), `docs/QUALIFICATION-f0656746.md`
(carried, plus the pointer appended with this report), `qualification/f0656746/` (evidence).
**Untouched:** every file under `src/`, every test under `tests/`, every example tree but hw1's
README, every calibration, and `docs/surface/v0.2-surface-baseline.json`.

---

## 6. Unresolved questions and advisory leftovers

For the review, not blocking the group:

1. **The 409 for both new rows** is the door's class rule applied consistently; no ruling names a
   status for either kind. A one-line confirmation would close it.
2. **The registry load in the lint rule executes `guarded.py` by path** (it imports only
   `dataclasses` and `typing`); the other checkers are pure AST. An AST extraction of the
   declarations is the stricter alternative, at more code.
3. Advisory, ungated, left as found: the prose count "twenty-three" refusal kinds at
   `src/ccf/products/refusal.py` (module docstring), `runtime/ccf_runtime/http_api/routes/product.py`
   and `docs/surface-changes/24.6-09-…` — the vocabulary is 27; the comment beside
   `_SHAPE_MOVED_BY_FRAGMENT` in `tests/test_surface_shape_capture.py` saying
   `build_governed_resolver`'s signature did not move; the fragments README still documenting only
   `15-NN-` naming; `docs/D-IMPL-343-DESIGN.md` citing `r01`/`r10` as the digit-first
   counterexample (`r10` still is); the `*.md` versus `[0-9]*-*.md` glob split between
   `test_class_lookup.py` and the assembler; and the `guarded-provenance` rule having no
   `--guarded-provenance` flag and not being named in the CI step name or the Makefile help.
4. Whether evidence as a tarball under `qualification/` is the durable location wanted, or the
   home-directory archive (`~/ccf_qual_evidence/`) suffices.

**The remaining sequence is unchanged:** review → stale-test/pin investigation (45 nodes) →
fixed-candidate qualification including single-invocation `make test` → release ruling.
