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

**Repair, rule side (as first committed at `5b991706`; superseded after review — see §7.1).** The
registry was loaded by path from `<base>/src/ccf/contracts/guarded.py` — absent: no declarations
(the token-guarded census still runs); present but unloadable: one finding, never a skip. Real
tree: identical output, exit 0. **Repair, test side.** The closed set
widens to the three registered whole-tree rules (the function keeps its cited name; its docstring
carries the history), and three runner-level controls the rule never had are added: an
undeclared token-guarded class under a fixture is reported; an in-tree registry naming an absent
module is still a finding; an unloadable registry is a finding (renamed *unreadable* when the
reader stopped executing the file, §7.1). No expected exit code was changed and no assertion
weakened.

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
**Untouched by the group's repairs:** every file under `src/`, every test under `tests/`, every
example tree but hw1's README, every calibration, and `docs/surface/v0.2-surface-baseline.json`.
The review follow-up (§7) additionally changed `tools/dump_surface.py`,
`tools/lints/guarded_provenance.py`, `tools/lints/tests/test_runner.py` and
`tests/test_surface_shape_capture.py` — the two tools are mechanism changes, the two test files
gain controls only; no assertion was weakened.

---

## 6. Unresolved questions and advisory leftovers

For the review, not blocking the group:

1. **The 409 for both new rows** is the door's class rule applied consistently; no ruling names a
   status for either kind. A one-line confirmation would close it.
2. **The registry load in the lint rule executes `guarded.py` by path** (it imports only
   `dataclasses` and `typing`); the other checkers are pure AST. An AST extraction of the
   declarations is the stricter alternative, at more code. **Resolved after review: the reader
   now parses and never executes (§7.1).**
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

---

## 7. Review follow-up — the two tooling narrowings (added after Dave's review)

Dave's review of this group (2026-09-19): the 409 mapping is acceptable under the existing HTTP
refusal-class convention; merge stays on HOLD until *"the guarded-provenance lint reads the
`--base` registry without executing it, and the surface-manifest normalization is narrowed so it
cannot erase legitimate literal defaults containing `at 0x…`."* Everything else stands as
measured. Both are done on this branch on top of `690cce3f`; the seventeen nodes stay green and
nothing generated moved. Each change went through three adversarial review rounds (§7.3); the
first two versions of each were refuted and reworked before anything was committed.

### 7.1 The lint rule reads the registry by parsing, never by executing

`tools/lints/guarded_provenance.py::_load_registry` reads `<base>/src/ccf/contracts/guarded.py`
with `ast` only, like every other rule in the runner; nothing under `--base` is imported or run,
and the `importlib` loader is gone. It parses the file's bytes (a UTF-8 BOM reads, as under
import), applies a **one-binding rule over the whole file** — exactly one module-level
`GUARDED_TYPES` assignment (plain or `Final`-annotated; a bare annotation restatement is
ignored), and no `+=`, second assignment, loop or `with` target, `global` declaration, `del`,
import or definition of that name anywhere else, inside a block or a function included — and
reads each keyword-only `GuardedTypeDeclaration(...)` call's consulted fields (`type_path`,
`verifier`, `boundaries`, `verifier_aliases`) as string, `None` or tuple-of-string literals of the
shape each field takes. The known and required fields come from the `GuardedTypeDeclaration`
class body in the same file, by the dataclass's own rule: an annotated attribute is a field
unless it is `ClassVar` or `KW_ONLY`; it is required when it has no default or a `field(...)` with
neither `default` nor `default_factory`. A registry that would not construct under its own
dataclass therefore does not read either. The prose fields are not read.

**What is a finding** — one finding naming the cause, never a silent skip: any read or parse
failure inside the guarded scope (a directory, a dangling symlink, a permission error, a syntax
error); no module-level binding; any rebinding as defined above; a value that is not a tuple
literal; an element that is not a `GuardedTypeDeclaration(...)` call; positional arguments; a `**`
splat; a repeated or unknown keyword; a missing required field; a consulted field that is not a
literal or not of its field's shape. What reads correctly: a BOM, an annotation restatement, a
module body that would raise if executed. The module census that walks the tree parses bytes the
same way. Stated as a limit, not hidden: a rebinding the parser cannot see (`exec`, a `setattr`
on the module) is beyond any static reader; a function *parameter* named `GUARDED_TYPES` binds a
local, not the registry, and is accepted; a class-body attribute of that name inside another
class is refused although it does not rebind the module name, and an aliased import of `field`
or `KW_ONLY` is read conservatively — loud false refusals, never a silent read.

Controls in `tools/lints/tests/test_runner.py`: twenty refused shapes, each yielding exactly one
finding with the named cause (nine rebinding forms among them — `+=`, a second assignment, a
loop target, `global`, `except … as`, a `match` capture, a `type` statement, a star import — and
a declaration a permissive class would leave without a `type_path`); the BOM and restatement
cases reading; the dataclass required-field rule (`field(metadata=…)` required, `KW_ONLY` and
`ClassVar` not fields); a dangling symlink; a registry opening with `raise SystemExit` yielding
its declaration; a consulted field bound to a `Name` refused; and
`test_the_parsed_real_registry_equals_the_executed_one` — the real registry read by the rule
equals the executed `GUARDED_TYPES` on the four consulted fields, in order. `tools/lints/tests`:
**480 passed**. Real tree: `python -m tools.lints --all` exit 0, no finding.

### 7.2 The manifest renders each value alone; a literal default is protected by its type

There is no pass over a rendered signature any more. `tools/dump_surface.py::_render_signature`
rebuilds `str(signature)` from a copy in which every default and annotation was rendered **per
value**: a default that *is* a `str` or `bytes` is returned as is — **by type, so no text it
contains can ever be rewritten, whatever its neighbors render as**; any other default whose `repr`
carries an address is replaced by a stand-in printing that one `repr` with the address removed.
Annotations, module-level aliases (the five `Annotated[…, AfterValidator(func=<function … at 0x…>)]`
renderings the manifest actually carries) and contract fields are rendered the same way, one
object at a time. Within one object's `repr`, Python's own tokenizer decides what is quoted — so
`<Foo name='at 0x1' at 0x2>` keeps the quoted address and loses its own, and `<function <lambda>
at 0x…>`, `<function outer.<locals>.inner at 0x…>` and `<bound method X.y of <X object at 0x…>>`
lose exactly their address. The `--check`, the two-process comparison and the committed manifest
are all unchanged by this (it produces byte-identical output on the live surface).

**Fails safe, per value, loudly.** A `repr` that does not tokenize (an unpaired quote, a
truncated pattern, a control character) is kept as it is, and so is an address the tokenizer
places inside a STRING or COMMENT token (a `#` in a custom repr, an even number of unpaired
quotes, a non-string object whose repr is a quoted string) or a `str` *subclass* whose custom
repr carries an address (returned as is, by type): that one value's address survives into the
manifest and the manifest-wide no-address gate goes red, while every neighboring value is
rendered correctly and every literal default is untouched by construction. The one silent
residual, stated as a residual and applying to any single rendering (a default, an alias, an
annotation, a contract field): a custom repr that pairs an unpaired quote before a quoted `at 0x…`
with another after it makes the tokenizer read the quoted text as code, and the quoted address
goes too. No such object exists in the tree (across all 1 402 exports the per-value scrub and
the old whole-string regex disagree nowhere). A hand-set `__signature__` built without parameter
validation renders as the previous generator rendered it. The narrowness tests' independent
legacy comparator normalizes addresses with a regex of its own, so that comparison stays about
shapes and independent of the generator.

Controls in `tests/test_surface_shape_capture.py`, measured through `inspect.signature` on real
objects as the generator does: a function default and a lambda default lose their address and
keep their names; a `str` default, a `bytes` default and a `str` default shaped like a repr sit
between two reprs with unpaired quotes and come through byte for byte; a default whose own repr
quotes an address keeps the quoted one; an untokenizable repr keeps its address while its
neighbors are rendered correctly; an alias carrying a validator renders without the address.
`tests/test_surface_shape_capture.py` + `_completeness` + `_drift`: **51 passed**.
`tools/dump_surface.py --check` exit 0; two separate-process generations byte-identical and equal
to the committed manifest (no regeneration needed); the manifest carries no `0x…`.
`mypy --strict` over both tools (with `MYPYPATH=src:runtime`; `tools/` is outside the
project's configured files): clean.

### 7.3 Adversarial review — what each round found, and what was done

Each round: independent skeptics with distinct lenses, then an independent re-verification of
everything raised; only reproduced findings were acted on.

**Round 1 refuted both first versions.** The regex scrub mis-paired quotes when an unquoted repr
contained an apostrophe and silently rewrote the *next* literal, and under-covered nested or
quoted reprs. The first AST reader silently accepted four registry shapes execution rejected
(`+=`, a `**` splat, a repeated keyword, a missing required field), narrowed exception handling
so a read failure would have escaped the gate as a traceback, rejected a BOM, and mis-read an
annotation restatement as a second binding.

**Round 2 refuted the second versions.** A tokenizer pass over the *whole* signature is defeated
by an even number of unpaired quotes in neighboring reprs, which pair up as a phantom literal
around the real one — silently, with nothing for the no-address gate to see; its line-offset table
also disagreed with the tokenizer's line source on form-feed and Unicode line separators. The
reader's one-binding check looked only at the module body, so a `+=` inside a block was neither
refused nor read — a silent regression against execution; its required-field rule missed
`field()` without a default and mis-counted `ClassVar`/`KW_ONLY`; a permission error and a dangling
symlink escaped its guarded scope.

**What was done.** The scrub moved from text to values (§7.2), which turns the literal-default
guarantee into a matter of type rather than parsing; the reader's binding rule now covers the
whole file and its required-field rule is the dataclass's (§7.1); every reproduced finding has a
control that would catch its return. Not taken, pre-existing and disclosed: the rule's module
docstring promises `mint` resolution that no version checks; the manifest-wide no-address gate
would fire on a legitimate six-hex-digit literal default (a loud tension, kept deliberately).

**Round 3** re-ran the review against the per-value renderer and the whole-file reader and did
not refute either guarantee: no `str`/`bytes` default could be altered by any real-object attack,
and the real registry read identically to execution. What it found was closed afterwards with
controls, without a further review round: an unvalidated hand-set `__signature__` would have
degraded to a type name; `except … as`, `match` captures, the `type` statement and a star import
were parser-visible rebindings the one-binding rule did not yet name; `field(default=MISSING)` and
`dataclasses.field()` were dataclass spellings the required-field rule mis-read; a permissive
class could leave a declaration without a `type_path` and reach the constructor. Its prose
corrections are in §7.1 and §7.2 above.
