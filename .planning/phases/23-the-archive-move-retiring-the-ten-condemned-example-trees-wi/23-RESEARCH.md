# Phase 23: The Archive Move — Retiring the Ten Condemned Example Trees Without Deleting Them — Research

**Researched:** 2026-08-24
**Phase base measured at:** `aefd072d816307beaf75650bbb621602a64cec6b`
**Domain:** repository-wide path refactor under standing gates; no fabric change
**Confidence:** HIGH on everything measured by running it; the unknowns are named in §14 and are not smoothed over

---

## 0. Summary — and read §1 before you plan anything

The move itself is trivial: `git mv` ten directories, 265 files, 265 renames and
zero deletions, proven in about four seconds. Everything expensive is what the
move drags with it.

**The single most important research finding is that the input this phase was
told to start from — `docs/surface/examples/RETIREMENT-COUPLINGS.md`, 267 rows
across 81 files — is systematically blind to the two heaviest coupling
populations in the phase.** It reports **175 rows naming the ten condemned
trees**, not 267 (the other 92 name the `s1` pair and the test modules and
published pages that are themselves on the retirement schedule). And it reports
**zero rows** for `public/tutorial/adopters-guide.md`, `public/tutorial/demo-walkthrough.md`
and the eleven `tests/examples/test_*_output.py` modules — the pages carrying 49
of the 102 includes, and the tests carrying most of the 515 that hold the
4105/118 baseline — because the sweep drops a reference whose *source file* is
itself scheduled to retire at the same wave. Under `D-IMPL-190` ruling 2 those
tests do not retire, so the drop is now wrong. **Do not plan from the report's
counts.** The measured inventory is in §5.

The second finding is that this was measured by **performing the move** — `git mv`
all ten trees, run the suite, read the wreckage, `git reset --hard`. Not by
grepping and reasoning. What the tree actually did:

| Gate | At `aefd072` | After a bare `git mv` of the ten, nothing else touched |
|---|---|---|
| `pytest --collect-only` | **4223** | **4154** (−69: 73 lost, 4 renamed-in) |
| `test` leg | **1 FAILED** (pre-existing, §1.1) | **49 failed, 197 errors** |
| `gate-tools` (`tools/docs_tests` + `publish_scan_tests`) | 313 passed | **13 failed** |
| `tools/lints/tests` | 406 passed | 406 passed |
| `python -m tools.lints --all` | exit 0 | **exit 0** — it stopped looking (§7.4) |
| `mkdocs build --strict` | exit 0 | **`SnippetMissingError`**, names the path |

**Primary recommendation:** plan this as *six* work streams, not one — (a) the pure
rename, (b) the in-archive content repairs the archive needs to stay runnable
(220 files, §8.2), (c) the gate-scope widenings without which four count floors
and five walks go red or, worse, go silent (§7), (d) the published-page repoint
including 13 `make example-*` command strings the criteria do not count (§6.3),
(e) the Makefile/CI/README repoint, (f) the ledger, sweep and report. And take
§1 to Dave before Wave 1.

---

## 1. STOP-AND-ASK — four findings that contradict the locked criteria or a standing ruling

These are not executor's judgement calls. Each is measured, each is reproducible,
and each needs Dave.

### 1.1 The phase base is ALREADY RED on the `test` leg, and the commit that made it red is the one that wrote criterion 14

```
$ .venv/bin/python -m pytest tests/invariants/test_citation_coverage.py -q
FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
1 failed, 4 passed in 15.03s
```

The failure names its two offenders:

```
- .planning/ROADMAP.md:2212 cites src/ccf/products/bind.py:74
- .planning/ROADMAP.md:2212 cites runtime/ccf_runtime/mcp/experience.py:483
assert 2 <= 0
```

`.planning/ROADMAP.md:2212` **is criterion 14.** `D-IMPL-192` enumerated the four
permitted edits in the `path.py:LINE` form, and `D-IMPL-114` ruled that prose cites
`path.py::Symbol` while `D-IMPL-123` holds the population of unanchored Python
citations at a **ceiling of zero**. `tests/invariants/test_citation_coverage.py:179`
is `MAXIMUM_UNANCHORED_PY_CITATIONS = 0`.

Bisected:

```
$ git show 2ccac03:.planning/ROADMAP.md | grep -c 'src/ccf/products/bind.py:74'   → 0
$ git show aefd072:.planning/ROADMAP.md | grep -c 'src/ccf/products/bind.py:74'   → 1
```

So `aefd072` — the most recent commit on `main`, the commit that logged
`D-IMPL-192` — turned the always-on `test` leg red. **Criterion 7 (`4105 passed /
118 skipped`) and criterion 15 (`make ci` exits 0 on all six legs) cannot both be
true at the phase base as it stands.** The baseline at `aefd072` is 4104 passed /
1 failed / 118 skipped, not 4105/118.

Three ways out, all Dave's, none an executor's:
1. Convert the two citations in criterion 14 to `path.py::Symbol` form — but that
   edits a LOCKED criterion's text, which `D-GATE-19`/`D-IMPL-174` govern.
2. Raise `MAXIMUM_UNANCHORED_PY_CITATIONS` — the constant's own
   `CEILING_RAISE_INSTRUCTION` says a deliberate raise and a regression need the
   identical edit, and explicitly prefers conversion.
3. Rule the two out of `D-IMPL-123`'s scope by adding `.planning/ROADMAP.md` to
   `HELD_BACK_HOSTS` (which today holds only `docs/surface-changes/*` and
   `docs/SURFACE-CHANGES.md`).

Note the same four citations appear in `docs/DECISIONS.md` `D-IMPL-192` and in
`23-CONTEXT.md`'s table and are **not** flagged — the DECISIONS spelling and the
CONTEXT table's split file/line columns do not match the citation pattern. Only
ROADMAP:2212 does, and only two of the four.

### 1.2 `H-14` — a Dave-ratified ruling — says `examples/external/00-hello-context/` STAYS, and no entry amends it

`tests/examples/test_hw1_harness_clients_retirement.py:16-21`, in its own words:

> **`H-14` is a marking, not a move**, so `examples/external/00-hello-context/`
> stays and keeps `client_adk.py`, `client_anthropic.py` and `client_bare.py`.
> :func:`historical_example_violations` asserts that positively. Without it this
> module would only ever push toward deleting things, and a later change could
> satisfy a count by removing the historical example — the opposite of what was
> ruled.

`H-01`..`H-14` are RATIFIED by `docs/DECISIONS.md:247` **`D-IMPL-167`** (Dave,
2026-08-21). Five standing tests enforce it, and all five went red in the trial
move:

```
FAILED tests/examples/test_hw1_harness_clients_retirement.py::test_the_historical_example_keeps_all_three_of_its_clients
FAILED tests/examples/test_hw1_harness_clients_retirement.py::test_nothing_is_untracked_under_the_historical_example
FAILED tests/examples/test_hw1_harness_clients_retirement.py::test_no_tracked_file_under_the_historical_example_is_dirty
FAILED tests/examples/test_hw1_harness_clients_retirement.py::test_two_of_these_names_under_examples_is_the_mandated_state[client_adk.py]
FAILED tests/examples/test_hw1_harness_clients_retirement.py::test_two_of_these_names_under_examples_is_the_mandated_state[client_anthropic.py]
```

with the assertion message quoting the ruling verbatim:

> `/home/parkave/ccf_code/examples/external/00-hello-context is missing. \`H-14\`
> rules that this example STAYS, running and CI-green, marked historical in its
> README. Ruling 3 is satisfied there by a sentence, not by a move and not by a
> deletion`

**Nothing in `D-IMPL-189`, `-190`, `-191`, `-192`, the ROADMAP entry or
`23-CONTEXT.md` names `H-14` or `D-IMPL-167`.** The standing policy `D-GATE-22`
set for `D-IMPL-188` is that a pin moves only by an explicit entry naming the old
pin, the new pin and why. No such entry exists. Either Dave amends `H-14` in that
form, or `examples/external/00-hello-context` drops out of the ten and the phase
carries nine trees (226 files, not 265) — which would move criterion 1, 2, 3, 8
and 14's fourth permitted edit.

### 1.3 `make docs-strict` cannot go green by re-pointing the includes — the published tree's include allowlist is default-deny and `archive/` is not on it

`tools/publish_scan.py:104-108`:

```python
INCLUDE_ALLOWED_PREFIXES: tuple[str, ...] = (
    "examples/",
    "public/",
    "perf/baselines/",
)
```

Measured directly:

```
include_escapes('examples/00-quickstart/run.py:boot')          = False
include_escapes('archive/examples/00-quickstart/run.py:boot')  = True
include_escapes('archive/examples/08-e2e-demo/artifacts/scenario.yaml') = True
```

`docs-strict` step 1 is `tools/publish_scan.py --pre-build`, which raises
`pub04-include-escape` for every target outside the allowlist. A correctly
re-pointed page therefore fails step 1 with **102 escapes**. The fix is to add
`"archive/examples/"` to the tuple — mechanically one line, but it **widens the
publication default-deny boundary (`D-01`/`D-02`) to a new repo root**, which is a
governance surface, not a path edit. `mkdocs.yml`'s own comment calls the
allowlist "the boundary … never this setting". Flagging rather than assuming.

*(No test asserts the allowlist's contents — grep over the tree found zero
references to `INCLUDE_ALLOWED_PREFIXES` outside `tools/publish_scan.py` and two
`.planning/` documents. So widening it is unwatched.)*

### 1.4 `tools/docs_tests/test_no_stale_example_paths.py` reports the `archive/` prefix as a MISSING `examples/` path — criterion 5's second witness goes red for the wrong reason

`PATH_TOKEN` at `tools/docs_tests/test_no_stale_example_paths.py:78-80`:

```python
PATH_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:tests/examples|examples)/[A-Za-z0-9_./-]*[A-Za-z0-9_/]"
)
```

The lookbehind excludes `[A-Za-z0-9_.-]` but **not `/`**. Proven end-to-end
against the shipped function, on a page whose paths are *correctly* re-pointed:

```
prose_path_offenders([page]) →
  ['…/p.md:3 -> examples/02-skilling',
   '…/p.md:6 -> examples/08-e2e-demo/run.py']
```

The gate reports two paths **the page never wrote**. Its own docstring says the
lookbehind exists so `tests/examples/x` is not re-read as a bare `examples/x` —
that works only because the alternation consumes the whole token first; there is
no earlier match to consume `archive/`. So `PATH_TOKEN` must be widened (add an
optional `archive/` prefix, or add `/` to the lookbehind class) **before**
criterion 5's control can distinguish a real dangling path from this artefact.
Criterion 5 asks the two witnesses to be proven independent; today they would
both be red, for two entirely different reasons, and the phase would be unable to
tell.

---

## 2. User Constraints (from `23-CONTEXT.md`)

### Locked Decisions

- **D-01 (`D-IMPL-190` r1):** **Ten trees, not twelve.** `CLNT-17` and the `s1` pair are excluded and `CLNT-17` stays `Not built`. The client-side pair is `hw1-*`. Benefit of moving `s1` is **zero** (both already outside the `examples:` aggregate); archiving `s1-01` would make a `D-IMPL-189` commitment false; both `s1` trees are live fixtures for **core** suites — `tests/deployment`, `tests/products`, `tests/replay`, `tests/halflife`.
- **D-02 (`D-IMPL-190` r2):** **The paired tests STAY under `tests/`; only the sources move.** AMENDS `D-IMPL-189` point 1. **OLD:** *"their paired tests moved with them"*. **NEW:** they remain under `tests/` and are re-pointed. `pyproject.toml:142` sets `testpaths = ["tests"]`.
- **D-03 (`D-IMPL-191` r1):** **The archive lives OUTSIDE `examples/`.** **The path is PINNED to `archive/examples/…` by Dave 2026-08-24 at the scope-lock**; it is no longer the planner's to choose.
- **D-04 (`D-IMPL-191` r2):** **The archive stays RUNNABLE but ships NO `make` targets.** All ten `example-0N`-family targets are **deleted, not renamed**.
- **D-05 (`D-IMPL-191` r3):** **Re-point the `Retirement` table; archived paths STILL count as couplings.** The ten moved trees re-point to Phase 23 plans; the `s1` pair's `17-08` rows are left alone. A sweep blind to the archive would reproduce the exact defect Phase 22.1 was commissioned to fix.
- **D-06 (`D-IMPL-191` r4):** **The done-limb says "out of the `examples:` aggregate", NOT "out of live CI".** AMENDS `D-IMPL-189` point 3. The cell must NAME what still exercises them.
- **D-07 (`D-IMPL-192`):** **Criterion 14 is AMENDED to permit EXACTLY FOUR path-string-only citation updates, and nothing else** under `src/`, `runtime/` or `pyproject.toml`. A **fifth** edit is a **scope breach**. The five `s1-01` citations are NOT touched.

### Claude's Discretion

- The archive's INTERNAL layout beneath `archive/examples/`, provided every include resolves. **The root path itself is NOT discretionary.**
- How the include re-point is mechanized (path substitution vs. per-page edit), provided criterion 5's RED-before-GREEN control holds.
- Plan and wave decomposition.

### Deferred Ideas (OUT OF SCOPE)

- `CLNT-17`'s stated blocker is wrong on the tree — **raised, expressly not ruled; no plan in this phase may act on it.**
- `CLNT-17` may be mis-framed as an example-retirement row at all — **Dave's ruling, not an executor's.**
- **BACKLOG (`D-IMPL-192`): a standing check that every `path::symbol` node id under `src/` and `runtime/` RESOLVES.** **Rejected as Phase 23 scope.**
- The `00`–`08` half of `D-27` (deletion) remains undecided and Dave's.
- `DOCS-14` / `EXAM-02` still owe the replacement surface.
- The 27-item human-verification packet awaits Dave (`D-20`).
- The archived pages teach the pre-Phase-15 integration surface (Phase 14's `G-01`). The move relabels that; it does not close it.

---

## 3. Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| `DOCS-17` | `examples/00`–`08` and `examples/external/00-hello-context` retired with every published page re-cut, proven by standing gates | §5 (the full inventory the verdict must be true against), §6.3 (the `make example-*` command strings the standing "documented commands" gate reads and the criteria do not count), §11 (the wording available to the `Partial` cell), §9 (the two pinned figures at `.planning/REQUIREMENTS.md:42` and `:336` that criterion 6 must re-measure) |
| `CLNT-17` | **EXCLUDED. No plan may assign it a verdict, limb or disposition.** | §12 records the two byte-identity anchors so the criterion-13 check can be written mechanically |

---

## 4. Project Constraints (from `CLAUDE.md`)

Directives that bind this phase specifically:

- **§3.1 close protocol** — execution → **cross-AI panel on the SHIPPED tree** (`/gsd-review --all`, source **inlined**, not pointed at by path; codex's `bwrap` exits 0 having read nothing) → single-agent depth pass → **verify every finding against the tree** and record rejections as rejected → fix blockers in-phase → then Dave. Both passes run; neither substitutes. Write the close panel to `23-CLOSE-REVIEWS.md`.
- **§3.1 briefing** — give the panel the findings already known and tell it not to re-derive them; ask for what is *adjacent*.
- **§6.4 No-Hardcoding Rule applies to `/examples`** — CI-enforced. See §7.4: the move takes 265 files out of every lint's scope. `tools/lints/__main__.py:71` is `LINTED_TREES = ("src", "runtime", "examples", "tests")`.
- **§11 Mechanism, not values** — nothing in this phase touches `/src` beyond the one permitted docstring path string.
- **§11 whitepaper fidelity** — no fabric change; §7 lists everything under `tests/` and `tools/` the phase must touch and why each is mechanism-scope, not behaviour.
- **§17** — plain English to Dave, options enumerated, no buried decisions. §1 is written to be read by Dave directly.

---

## 5. The complete coupling inventory, by category

### 5.0 How this was measured, and why the committed report is not the answer

```bash
# the committed report — regenerated in the venv, confirmed byte-current
.venv/bin/python -m tools.retirement_sweep --report
#   → 267 coupling rows across 81 files (146 outside the three swept trees); 1911 files scanned
#   → git diff --stat docs/surface/examples/RETIREMENT-COUPLINGS.md  → EMPTY

# the independent sweep — every tracked file containing a literal ten-tree path
git ls-files -z | xargs -0 grep -lE '<the ten paths>' | sort
#   → 487 files total; 460 outside the ten trees; 154 outside the ten trees AND outside .planning/
```

Reconciled, file by file:

| | files |
|---|---:|
| Files the committed report names | 81 |
| …of which name one of the **ten** (rest name `s1`, test modules, published pages) | **58** |
| Files the independent grep finds outside the ten trees and outside `.planning/` | 154 |
| …explained by the sweep's own `EXCLUDED_FROM_ASSIGNMENT` (append-only records) | 85 |
| **…found by grep, NOT in the report, NOT on the exclusion list** | **14** |

Those 14 are the finding:

```
public/tutorial/adopters-guide.md          public/tutorial/demo-walkthrough.md
tests/examples/test_quickstart_output.py   tests/examples/test_agent_basics_output.py
tests/examples/test_skilling_output.py     tests/examples/test_harness_portability_output.py
tests/examples/test_cross_process_output.py tests/examples/test_workflow_hitl_output.py
tests/examples/test_decision_replay_output.py tests/examples/test_artifact_store_output.py
tests/examples/test_e2e_demo_output.py     tests/examples/test_ext00_serve_output.py
tests/examples/test_ext00_fixture_schemas.py tests/examples/test_ext00_hardening.py
```

Every one is itself a member of `RETIREMENT_SCHEDULE`. The sweep drops
*"references from inside a retiring path to a path that retires no earlier"* —
**235 of them** — because they would be deleted with their source. Under `D-02`
the eleven test modules do not retire, and Phase 23 deletes nothing, so the drop
is wrong for this phase. **The report cannot be used as the include inventory or
as the paired-test inventory.**

### 5.1 Rows naming the ten condemned trees — 175 rows / 58 files

| Bucket | rows | files | Disposition |
|---|---:|---:|---|
| `public/` (excl. the 2 tutorial pages the report drops) | 58 | 13 | **Re-point.** §6 |
| `Makefile` | 24 | 1 | **Delete ten targets; decide four live targets.** §6.2 |
| `tests/examples/` | 23 | 7 | **Re-point.** Plus the 11 modules the report drops entirely. §7.1 |
| `README.md` | 9 | 1 | **Re-point** — repo front door. §6.4 |
| `docs/` (evidence + retired + surface records) | 9+3+3 | 2+3+1 | **LEAVE** — historical records. §10 |
| `examples/` (surviving trees referencing moved ones) | 8 | 7 | **Re-point / assess.** §6.5 |
| `tests/products/` | 6 | 2 | **Re-point + widen scan roots — 4 count floors break.** §7.2 |
| `tools/docs_tests/` | 5 | 3 | **Re-point + widen.** §7.3 |
| `perf/suites/`, `perf/synth/` | 3+1 | 2+1 | **Re-point one live path construction.** §7.5 |
| `runtime/`, `src/` | 3, 1 | 2, 1 | **The four permitted `D-07` edits.** §8.4 |
| `docs/superpowers/` | 3 | 1 | **LEAVE** — dated plan record. §10 |
| `tests/conformance/` | 3 | 2 | Docstrings, documentary. No failure in trial. |
| `tools/` (`measure_examples.py`) | 3 | 1 | Docstring + argparse help. Not in `ci`. §7.6 |
| `tools/publish_scan_tests/` | 2 | 1 | `tmp_path` synthetic — survives. |
| `tests/lints/` | 2 | 1 | `tmp_path` synthetic — survives. |
| `.github/workflows/` | 1 | 1 | Comment. **Plus two live target invocations the report does not file.** §6.6 |
| `tests/cli/`, `tests/integration/`, `tests/invariants/`, `tests/perf_smoke/`, `tests/deployment/` | 1 each | 1 each | Mixed — 3 live, 2 documentary. §7 |

### 5.2 The rows that are NOT this phase's — 92 rows

`examples/s1-01-hello-context-product` (31), `examples/s1-00-companies-over-revenue`
(28), `tests/examples/test_s1_*` (23), the eleven `tests/examples/test_*_output.py`
modules as *retiring paths* (7), `public/tutorial/adopters-guide.md` and
`demo-walkthrough.md` as *retiring paths* (3). **None move.** The `s1` rows keep
their `17-08` owner per `D-05`.

---

## 6. Category-by-category: what must change, what may stay stale, and why

### 6.1 `public/` — 111 references across 15 pages, EXACTLY as the criteria pin it

```bash
grep -rnE '<ten paths>' public/ | wc -l                    # 111
grep -rnE '<ten paths>' public/ | grep -c -- '--8<--'      # 102
grep -rnE '<ten paths>' public/ | grep -v -- '--8<--' | wc -l  # 9
```

**102 includes + 9 prose = 111, across 15 pages. Criterion 4's figures are correct
on today's tree.**

| Page | includes | prose |
|---|---:|---:|
| `public/tutorial/adopters-guide.md` | 35 | 0 |
| `public/tutorial/demo-walkthrough.md` | 14 | 4 |
| `public/how-to/compose-a-workflow-with-hitl.md` | 14 | 1 |
| `public/how-to/run-agents-cross-process.md` | 10 | 1 |
| `public/how-to/swap-the-artifact-store.md` | 6 | 1 |
| `public/how-to/grant-and-revoke-a-skill.md` | 6 | 1 |
| `public/how-to/bind-a-harness-adapter.md` | 6 | 1 |
| `public/reference/artifacts/control-plane-artifacts.md` | 3 | 0 |
| `public/reference/artifacts/product-registration.md` | 2 | 0 |
| `public/reference/artifacts/{agent-definitions,prompt-artifacts,skill-catalog,skill-grants,task-definitions,workflow-definitions}.md` | 1 each | 0 |

**All 9 prose paths, verbatim** (these are what criterion 5's second witness reads,
and §1.4 is why it cannot read them correctly yet):

```
public/how-to/grant-and-revoke-a-skill.md:15    `examples/02-skilling`
public/how-to/run-agents-cross-process.md:17    `examples/04-cross-process`
public/how-to/compose-a-workflow-with-hitl.md:17 `examples/05-workflow-hitl`
public/how-to/swap-the-artifact-store.md:15     `examples/07-artifact-store-mcp`
public/how-to/bind-a-harness-adapter.md:16      `examples/03-harness-portability`
public/tutorial/demo-walkthrough.md:10          `examples/08-e2e-demo`
public/tutorial/demo-walkthrough.md:18          PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py
public/tutorial/demo-walkthrough.md:310         PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py
public/tutorial/demo-walkthrough.md:327         `examples/08-e2e-demo/artifacts/scenario.yaml`
```

Two of the nine are **runnable shell commands** a reader types. Re-pointing them
keeps them true only because `D-04` keeps the archive runnable — and only after
§8.2's depth repairs land.

**May stay stale: nothing under `public/`.** `check_paths: true` plus
`test_every_snippet_include_resolves_on_disk` plus
`test_every_prose_path_reference_resolves_on_disk` make it impossible.

### 6.2 `Makefile` — the 29 rows, decomposed

| Lines | What | Rows | Action |
|---|---|---:|---|
| 192–220 | The ten target definitions, each `## comment` + recipe | 20 | **DELETE both lines of each pair** (criterion 3). `make help` regenerates from `##` comments, so help text needs no separate edit. |
| **53–67** | `.PHONY` — **the report files ZERO rows here** because it matches path tokens, and `.PHONY` names targets | 0 | **DELETE the ten names.** Lines 57–58 carry `example-00 … example-ext-00`. Missing this leaves ten phony declarations for targets that do not exist — and see §6.3, the bijection gate reads `.PHONY`. |
| 256 | `examples:` — the eleven-member aggregate | 0 (not a path row) | **Reduce to one member**, `example-hw1-harness-clients` (criterion 3). |
| 253, 305, 307, 319, 321 | `example-s1-01`, `example-s1-00` and a comment | 5 | **LEAVE** — `s1` is out of scope. |
| **445, 448, 451, 454** | Four **live-leg** targets naming condemned trees: `example-03-live-ollama`, `example-03-live-anthropic`, `example-ext-00-live-anthropic`, `example-ext-00-live-adk` | 4 | **DECISION NEEDED — see below.** |

**The four live-leg targets are a gap between `D-04` and criterion 3.** `D-04` says
"all ten `example-0N`-family targets are deleted"; criterion 3 **enumerates** the
ten by name — `example-00`…`example-08`, `example-ext-00` — and these four are not
among them. Leaving them makes four `make` targets that fail at run time. Deleting
them is arguably within `D-04`'s stated reason ("a target is an invitation to
run") but goes beyond criterion 3's enumeration, and criterion 3 also says *"no
archive-form target replaces them"*, so re-pointing them contradicts `D-04`'s
no-targets rule. **Two of the four are invoked by `.github/workflows/live-legs.yml`
(§6.6).** Recommend: put the three options to Dave, do not choose.

`make examples` with one prerequisite works and the documented-commands
non-vacuity precondition (`composed_examples(text)` non-empty) still holds.

### 6.3 The 13 `make example-*` command strings in published pages — NOT counted by any criterion

`tools/docs_tests/test_documented_commands_exist.py` asserts a **bijection**
between published `make <target>` invocations and the Makefile. Forward:
`undefined_commands()` fails if a page names a target absent from `.PHONY`.

Measured — 15 `make example-*` invocations across 8 pages, **13 of them naming a
target this phase deletes**:

```
public/tutorial/adopters-guide.md:44   make example-00     public/tutorial/adopters-guide.md:159  make example-01
public/tutorial/adopters-guide.md:219  make example-02     public/tutorial/adopters-guide.md:278  make example-05
public/tutorial/adopters-guide.md:360  make example-06     public/tutorial/adopters-guide.md:401  make example-ext-00
public/how-to/bind-a-harness-adapter.md:30      make example-03
public/how-to/run-agents-cross-process.md:36    make example-04
public/how-to/grant-and-revoke-a-skill.md:29    make example-02
public/how-to/compose-a-workflow-with-hitl.md:32 make example-05
public/how-to/swap-the-artifact-store.md:31     make example-07
public/tutorial/demo-walkthrough.md:21          make example-08
public/tutorial/demo-walkthrough.md:313         make example-08   (+ `make examples` on the same line)
```

Every one of the ten condemned targets is named by at least one published page.
**Deleting the targets without editing these 13 sites turns
`test_every_documented_make_target_exists` red.** They are neither snippet
includes nor prose paths, so criterion 4's "102 + 9" does not cover them, and my
trial move did not surface them because I did not touch the Makefile. This is
criterion 6's "movement, recorded" in its most concrete form.

The backward direction (`undocumented_examples`) becomes trivially satisfiable —
one member, documented at `public/how-to/run-agents-cross-process.md:202`.

### 6.4 `README.md` — 9 rows, LIVE, ungated

Lines 45 (prose), 58–65 (eight markdown links `[\`00-quickstart\`](examples/00-quickstart/)`),
plus 12 `make example-*` strings at lines 42, 54, 58–65 including
`make example-03-live-ollama` and `make example-03-live-anthropic`, and line 51:

> `make examples` runs all eight in order — the same command CI runs.

After this phase that sentence is false and all eight links 404 on GitHub.
**Nothing gates `README.md`** — it is outside `public/`, so `publish_scan` never
sees it. Live-and-owed by judgement, not by a gate. This is where a coupling
rots silently.

### 6.5 `examples/` — the surviving trees that reference moved ones

Eight rows across seven files. The ones that matter:

- **`examples/external/README.md`** — the family charter, **NOT among the 265**. Line 50 names `00-hello-context` in the band map; line 61 names `examples/03-harness-portability`; line 16 names "existing suite examples `00`–`08`". After the move `examples/external/` survives holding only this README, for a family whose only member has left.
- `examples/hw1-harness-clients/runner/model_stub.py` (3), `runner/drive.py` (1), `examples/hw1-companies-over-revenue/server/serve.py` (1) and `server/egress-door.yaml` (1), `examples/s1-01-hello-context-product/report.py` (1) and `artifacts/source-estate.yaml` (1).

**Criterion 2 tension.** Criterion 2 says `examples/` retains **exactly four**
trees, measured by `git ls-files`. Measured after the trial move:

```
examples/.gitkeep
examples/external/README.md
examples/hw1-companies-over-revenue
examples/hw1-harness-clients
examples/s1-00-companies-over-revenue
examples/s1-01-hello-context-product
```

Six top-level entries, four of them trees. Criterion 2's second clause ("no `00`–`08`
or `external/00-hello-context` directory remains") is satisfied; its first clause
("exactly four") is satisfied only under a reading that excludes `.gitkeep` and
`external/README.md`. **State the reading explicitly in the plan rather than
letting the check pick one.**

### 6.6 `.github/workflows/` — three files, and the report files only one row

**`ci.yml` — the always-on `examples` job, lines 263–295.** It runs `make examples`
(line 295). With a one-member aggregate that command still succeeds; **CI stays
green.** What goes stale and must change:

| Line | Text | After |
|---|---|---|
| 264 | `name: examples suite (00–07, reference backends)` | already stale (eleven members); becomes absurd |
| 266–267 | comment: *"Subprocess-spawning examples (04 cross-process, 07 MCP child) must not be able to hang the runner"* | both named examples have left the job |
| 270–273 | `env: CCF_REQUIRE_HARNESSES: "1"` with the comment *"A skipped harness leg in example 03's deterministic run is a failure"* | example 03 has left the job; the env var is inert |
| 268 | `timeout-minutes: 20` | now guards one example |
| 294 | step name `Run all eight examples (make examples)` | one example |

**No `ci.yml` step invokes any of the ten targets by name.** The aggregate is the
only seam. Criterion 3 is therefore sufficient to keep the always-on job green.

**`live-legs.yml`** — `:92` `run: make example-03-live-ollama`, `:138`
`run: make example-03-live-anthropic`, plus the `:6` comment row the report files.
Trigger is `workflow_dispatch` only, so it cannot redden a push — but it breaks on
dispatch under either disposition of §6.2's four targets.

**`perf.yml`** — `workflow_dispatch` only; `make perf-xproc` reaches
`perf/suites/crossproc` (§7.5).

---

## 7. `tests/`, `tools/` and `perf/` — where the 4105/118 baseline is actually at risk

### 7.1 Collection: a bare move loses 69 tests, and every one is a parametrization over a tree walk

```
before: 4223 collected      after: 4154 collected      lost 73, gained 4 (renamed ids)
```

| File | lost | Root it walks | Constant |
|---|---:|---|---|
| `tests/products/test_gate_two_call_shape.py` | **42** | `SCANNED_TREES = ("src","runtime","examples")` `:487`; `BINDER_SCANNED_TREES = ("examples",)` `:491` | parametrized over `_projecting_scopes()` |
| `tests/examples/test_ext00_fixture_schemas.py` | 12 | `EXAMPLE_DIR = REPO_ROOT/"examples"/"external"/"00-hello-context"` `:28` | fixture-file parametrization |
| `tests/examples/test_artifact_schema_headers.py` | 10 | `EXAMPLES_ROOT = REPO_ROOT/"examples"` `:154` | parametrized over `example_roots()` — 10 roots |
| `tests/products/test_required_operators_guard.py` | 9 | `SCANNED_TREES = ("src","runtime","examples")` `:80` | parametrized over `_implementations()` |

**Every one is fixed by widening the walk root to include `archive/`, and the
collected count then returns to 4223 exactly** — because the same files are found
at the new path. Lowering the constants instead would move the baseline and lose
coverage of the archive, which `D-05` forbids in spirit.

### 7.2 FOUR count floors break — the largest single risk, and no criterion names it

Measured by importing each module and partitioning its own scan output by path:

| Gate | Constant | Total today | Inside the ten | Surviving | Verdict |
|---|---|---:|---:|---:|---|
| `tests/products/test_required_operators_guard.py::test_the_scan_is_not_vacuous` | `MINIMUM_IMPLEMENTATIONS = 9` `:87` | 14 | 9 | **5** | **FAILS** |
| `tests/products/test_gate_two_call_shape.py::test_the_gate_scan_is_not_vacuous` | `MINIMUM_GATE_CALL_SITES = 12` `:617` | 12 | 9 | **3** | **FAILS** |
| `…::test_the_binder_scan_is_not_vacuous` | `MINIMUM_PROJECTING_BODIES = 14` `:637` | 14 | 11 | **3** | **FAILS** |
| `…::test_the_binder_argument_scan_is_not_vacuous` | `MINIMUM_RESOLVED_BINDER_SITES = 12` `:664` | 12 | 11 | **1** | **FAILS** |
| `tests/invariants/test_citation_coverage.py::test_the_citation_walk_is_not_vacuous` | `MINIMUM_SCANNED_CITATION_HOSTS = 953` `:203` | 953 | 96 | **857** | **FAILS** |

All five confirmed red in the trial run. `test_the_binder_scan_is_not_vacuous`'s
own docstring says the floors are deliberately tight — *"Headroom is not slack, it
is a licence"* — and warns that a legitimate removal and an accidental one need the
identical edit. **Widening the scan root preserves the value exactly** (14, 12, 14,
12, 953) and is therefore the honest fix; lowering the constant is the fix that
loses the coverage. For the citation walk, `tools/lints/citations.py:153-165`
`GATED_TREES` must gain `"archive"` (857 + 96 = 953).

### 7.3 `tools/docs_tests` — 13 red in the trial, and two more that only fire later

Trial result (`gate-tools`: 313 passed → 13 failed):

| Test | Cause | Fix |
|---|---|---|
| `test_no_stale_example_paths::test_every_snippet_include_resolves_on_disk` | 102 dangling includes | re-point |
| `test_no_stale_example_paths::test_every_prose_path_reference_resolves_on_disk` | 9 dangling prose paths | re-point **and** §1.4's `PATH_TOKEN` widening |
| `test_no_stale_example_paths::test_the_unmodified_copy_passes`, `::test_a_tests_examples_path_is_not_mis_reported_as_a_bare_examples_path` | both copy `adopters-guide.md` as their control fixture | resolve with the page |
| `test_snippet_gate::{test_the_unmodified_source_builds_clean, test_a_deleted_section_marker_fails_the_strict_build}` | `SNIPPET_SOURCE = REPO_ROOT/"examples"/"00-quickstart"/"run.py"` `:52` | **re-point the constant** (its own comment names 16-18 as the repointing owner — that plan is retired; Phase 23 inherits it) |
| `test_mkdocstrings_gate` ×3 | each runs a strict build of a doctored tree; the base build is broken | resolve with the includes |
| `test_requirement_ledger::test_every_cited_path_in_a_status_cell_resolves_as_written` | **exactly one** citation: `EXAM-01 → examples/external/00-hello-context/run.py`, at `.planning/REQUIREMENTS.md:63` and `:315` | re-point both channels |
| `test_resolver_seam_obligations::test_the_seam_cites_a_shipped_example_that_exists[×2]` | `ccf_runtime.mcp.egress.ProductResolverProtocol` and `…experience.ExperienceProductResolverProtocol` cite `examples/04-cross-process/producer_child.py` | resolved by `D-07` edits 2 and 3 — **but see below** |
| `test_retirement_sweep::test_the_committed_report_is_current` | report stale the moment anything moves | regenerate LAST (criterion 11) |

**Two that did NOT fire in the trial and will fire in the real phase:**

1. **`test_resolver_seam_obligations::test_both_seams_cite_both_call_sites`** —
   `EXAMPLE_PREFIX = "examples/"` at `:119`, and `cited_examples()` filters on
   `path.startswith(EXAMPLE_PREFIX)`. After `D-07` re-points the two runtime
   citations to `archive/examples/…`, they stop being *recognised as citations at
   all*, leaving only the `s1-01` one, and the test asserts `len(paths) >= 2`.
   **`EXAMPLE_PREFIX` must accept `archive/examples/` too.**
2. **`test_documented_commands_exist::test_every_documented_make_target_exists`** —
   fires the moment the ten targets leave `.PHONY`. §6.3.

**A correction to `D-IMPL-192`, recorded rather than smoothed.** The entry says
*"the phase would ship four citations in library code pointing at nothing, with no
gate able to say so."* That is true of `src/ccf/products/bind.py:74` and of
`runtime/ccf_runtime/mcp/experience.py:483`. It is **not** true of
`runtime/ccf_runtime/mcp/egress.py:306` and `runtime/ccf_runtime/mcp/experience.py:334`:
`test_the_seam_cites_a_shipped_example_that_exists` covers both by path and went
red on exactly them in the trial. The sabotage `D-IMPL-192` records was aimed at
`bind.py` and at `python -m tools.lints --all`; both findings stand for that
target. The ruling is unaffected — the four edits are still needed — but the
"no gate" claim is two-thirds right, not wholly right.

### 7.4 `tools/lints` — `python -m tools.lints --all` exits 0 after the move BECAUSE IT STOPPED LOOKING

```
$ .venv/bin/python -m tools.lints --all     # with all ten trees moved to archive/
lints exit=0
```

`tools/lints/__main__.py:71`:

```python
LINTED_TREES: tuple[str, ...] = ("src", "runtime", "examples", "tests")
```

`archive/` is on no lint's list. So after the move, **265 files — including 96
Python modules — leave the scope of CINV-01 (No-Hardcoding), CINV-02 (harness
imports), CINV-03 and the orchestration-split lint.** `CLAUDE.md` §6.4 applies the
No-Hardcoding Rule to `/examples` *explicitly*, and `tests/lints/test_examples_scope.py`
exists to hold that posture.

This is `D-05`'s principle one tool over: *"making the sweep blind to the archive
would reproduce the exact defect Phase 22.1 was commissioned to fix — a tool that
reports clean because it did not look."* Recommend adding `"archive"` to
`LINTED_TREES` **and** extending `RULE_TREE_SCOPE`'s CINV-02 exemption to it
(otherwise `archive/examples/03-harness-portability`'s deliberate harness imports
fire). `tests/lints/test_examples_scope.py` asserts `"examples" in LINTED_TREES`,
which stays true, so the widening does not break it.

### 7.5 `perf/` — one live path construction, in the always-on suite

- `perf/suites/crossproc/conftest.py:52` — `_EXAMPLE_04 = _REPO_ROOT/"examples"/"04-cross-process"`, spawning `producer_child.py`. **LIVE.**
- `perf/suites/common.py:140` — docstring. Documentary.
- `perf/synth/artifacts/controlplane.yaml:3` — comment. Documentary.

`perf.yml` is dispatch-only, **but `tests/perf_smoke/test_smoke.py:71` runs the
crossproc suite out of process in the always-on `test` job**, and it failed in the
trial:

```
FAILED tests/perf_smoke/test_smoke.py::test_suite_runs_untimed[crossproc]
  AssertionError: perf suite 'crossproc' failed under --benchmark-disable (exit 4)
```

Exit 4 is a pytest collection error — the conftest cannot find the child. The
coupling report files this correctly as `indirect-execution`, the only row of that
shape in the inventory.

### 7.6 `tools/` — the rest

- `tools/measure_examples.py:242` — `EXAMPLES_ROOT.rglob("*.py")`; `:261` docstring, `:308`/`:320` argparse help. `make measure-examples` is **not** in `make ci`, and `tests/examples/test_surface_audit.py` (the gate the Makefile comment names) **no longer exists**. So the `before/`/`after/` fragment trees under `docs/surface/examples/` are frozen records with no live reader. **Documentary; may stay stale — say so explicitly rather than leaving it unaddressed.**
- `tools/check_schema_headers.py:389` — `REPO_ROOT.glob("examples/**/artifacts/*.yaml")`, hard-coded. See §8.3.
- `tools/publish_scan_tests/test_publish_scan.py:163,190` and `tests/lints/test_examples_scope.py:41,55` — `tmp_path` synthetic tokens. **`survives` — these outlive their subject by construction and need no edit.** Both were green in the trial.
- `tools/lints/tests/test_citations.py:350` — asserts `exemption_reason("public/tutorial/adopters-guide.md") is None`. Unaffected.
- `tools/docs_tests/test_gate_two_wording.py:162` — names two published pages by path, not by example path. Unaffected.

### 7.7 `tests/` outside `tests/examples` — the live vs documentary split, measured by running it

**LIVE — went red in the trial:**

| File:line | Shape | Fix |
|---|---|---|
| `tests/cli/test_schema_export.py:60` | path-construction `examples/00-quickstart/artifacts` → *"no quickstart artifacts found"* | re-point |
| `tests/products/test_gate_two_call_shape.py:487,491` | scan roots | widen |
| `tests/products/test_required_operators_guard.py:80` | scan roots | widen |
| `tests/invariants/test_citation_coverage.py:203` | walk floor | widen `GATED_TREES` |
| `tests/perf_smoke/test_smoke.py:71` | indirect execution via `perf/suites` | fixed by §7.5 |
| `tests/examples/test_hw1_harness_clients_retirement.py` (5 tests) | **§1.2 — the `H-14` contradiction** | Dave |

**DOCUMENTARY — did NOT go red, docstrings only:**
`tests/conformance/test_a3_discharge.py:31`, `tests/conformance/test_harness_portability.py:58,76`,
`tests/integration/test_proto_quickstart.py:3`, `tests/deployment/test_operator_builder.py:479`,
`tests/products/test_gate_two_call_shape.py:207,425,426,1394,4340`,
`tests/products/test_required_operators_guard.py:3`.
These are prose inside `.py` files that no gate resolves. **They may stay stale
without breaking anything — but they are 12 sentences that start lying.** Recommend
re-pointing them in the same change; the cost is a `sed`, and `D-27`'s
whole complaint is about half-repaired machinery.

**NOT AT RISK — verified green in the trial, contrary to what the brief's row
counts suggest:** `tests/deployment` (8 rows — 7 name `s1`, 1 documentary),
`tests/client` (3 rows, all `s1`), `tests/replay` (1, `s1`), `tests/halflife`
(1, `s1`), `tests/products/test_request_contract.py` (2, `s1`). The `tests/products`
23-row figure is 6 rows on the ten and 17 on `s1` — the `s1` count floors
(`MINIMUM_GATE_CALL_SITES` and friends) are the *same four* floors §7.2 names,
which is why they read as `s1`-owned in the report while breaking on this phase's
move.

---

## 8. The mechanics of the move

### 8.1 `git mv` per tree is sufficient — and criterion 1's proof works, with a caveat

```bash
mkdir -p archive/examples/external
for t in 00-quickstart 01-agent-basics 02-skilling 03-harness-portability \
         04-cross-process 05-workflow-hitl 06-decision-replay \
         07-artifact-store-mcp 08-e2e-demo; do
  git mv "examples/$t" "archive/examples/$t"
done
git mv examples/external/00-hello-context archive/examples/external/00-hello-context
```

Measured:

```
git diff --cached -M --diff-filter=R --name-only | wc -l   → 265
git diff --cached -M --diff-filter=D --name-only | wc -l   → 0
git ls-files archive/ | wc -l                              → 265
```

**Caveat on criterion 1's second clause.** Criterion 1 says the move is a pure
rename set *"so nothing is deleted and no file content changed in the move."*
§8.2 and §8.3 require **220 content edits inside the moved trees**. Those must land
in a **separate commit after** the `git mv` commit, and criterion 1's "no content
changed" half must be evidenced against the **move commit**, not against the phase
end. (`git diff -M --diff-filter=R` still accounts for all 265 at phase end —
rename detection tolerates modification — so the R/D halves survive either way;
the content clause does not.) Note also that a **staged** move needs `--cached`;
the criterion's literal `git diff -M` reads the worktree.

### 8.2 Four `parents[N]` REPO_ROOT computations break — and they are exactly criterion 8's two executing tests

| File | Line | Today | Needed at `archive/` |
|---|---:|---|---|
| `examples/04-cross-process/producer_child.py` | 53 | `_REPO_ROOT = _EXAMPLE_ROOT.parents[1]` | `parents[2]` |
| `examples/07-artifact-store-mcp/mcp_store_child.py` | 32 | `parents[1]` | `parents[2]` |
| `examples/external/00-hello-context/serve.py` | 73 | `parents[2]` | `parents[3]` |
| `examples/external/00-hello-context/run.py` | 64 | `parents[2]` | `parents[3]` |

Each is followed by `sys.path.insert` of `_REPO_ROOT/"src"` and `/"runtime"`.
`examples/03-harness-portability/run.py:106` inserts `EXAMPLE_DIR` — relative to
`__file__`, so it survives.

**Criterion 8 cannot be met without these.** `tests/examples/test_cross_process_output.py`
executes `04-cross-process`; `tests/examples/test_ext00_hardening.py` executes
`external/00-hello-context` — and 27 of its tests were the largest single failure
block in the trial.

### 8.3 216 `$schema` headers break, and the gate that checks them goes SILENT rather than red

```
header occurrences by ../ depth: {3: 196, 4: 20}   total: 216
distinct files carrying one: 216
headers that do NOT resolve today: 0
```

Every artifact YAML in the ten trees opens with
`# yaml-language-server: $schema=../../../docs/schemas/ccf.<class>.json`
(20 at `../../../../`, inside `external/00-hello-context/artifacts/`).
`tests/examples/test_artifact_schema_headers.py` requires — its own words at `:21` —
that *"the target resolves **from the document's own directory**, exactly as an
editor resolves it, not from the repo root where a test happens to run."*

After the move each needs **one more `../`**: 196 → `../../../../`, 20 → `../../../../../`.

**And here is the phase's own defect class arriving inside it.** In the trial,
`test_artifact_schema_headers.py` produced only **2** failures — both about
`PERMANENTLY_DEFERRED` naming `examples/08-e2e-demo/artifacts/scenario.yaml` — and
**10 lost collections**. It did **not** report 216 broken headers, because
`EXAMPLES_ROOT = REPO_ROOT/"examples"` (`:154`) and
`tools/check_schema_headers.py:389` globs `examples/**/artifacts/*.yaml`. The walk
finds nothing in the archive, so it reports clean over 216 rotten headers.

The planner has a real choice and it should be surfaced, not made quietly:
- **(a)** widen both roots to include `archive/` and fix all 216 headers — 216 files edited, the archive stays self-consistent, `D-05`'s principle honoured;
- **(b)** leave the headers broken and the walk narrow — zero edits, CI green, and 216 files that lie to an editor, invisible to every gate.

Recommend (a). Note it makes criterion 1's content clause even more clearly a
per-commit property.

### 8.4 The four permitted `src/`/`runtime/` edits (`D-07`), verified on the tree

| # | File:line | Today |
|---|---|---|
| 1 | `src/ccf/products/bind.py:74` | `examples/04-cross-process/producer_child.py::resolve` |
| 2 | `runtime/ccf_runtime/mcp/egress.py:306` | same target |
| 3 | `runtime/ccf_runtime/mcp/experience.py:334` | same target |
| 4 | `runtime/ccf_runtime/mcp/experience.py:483` | `examples/external/00-hello-context/serve.py::context_provider` |

All four confirmed present at those exact lines. The five untouchable `s1-01`
citations confirmed at `egress.py:304`, `experience.py:332`, `bind.py:76`,
`request.py:365`, `request.py:558`. `pyproject.toml`'s one row (`:83`) names
`tests/examples/test_ext00_fixture_schemas.py`, which is **not** moving — so
`pyproject.toml` genuinely needs no edit, and criterion 14's diff-empty claim over
it holds.

### 8.5 `pymdownx.snippets` — mechanically neutral, as `D-03` says

`mkdocs.yml:90` `base_path: ["."]`, `:95` `check_paths: true`, `:97`
`restrict_base_path: true`. `archive/` is under `.`, so includes resolve from the
new location and `../` escapes stay blocked. **The include mechanism is fine; the
`publish_scan` allowlist is not (§1.3).**

### 8.6 No `conftest.py` inside the ten trees; no relative escape other than the `$schema` headers

```
git ls-files 'examples/*/conftest.py' 'examples/**/conftest.py'  → (empty)
```

The only `../` escapes are the 216 `$schema` headers. Nothing resolves an example
path relative to a changing CWD:
`test_no_stale_example_paths::test_the_walk_does_not_depend_on_the_process_cwd`
already holds that property for the docs walk, and every scanner measured resolves
from `__file__`.

---

## 9. Order of operations

The constraint that shapes everything: **`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
runs in `gate-tools`, which is in `ci-core`, which the project requires green from
Wave 1 onward.** The report goes stale the instant anything moves. So either every
wave regenerates it, or the phase accepts a red `gate-tools` mid-flight and closes
it at the end. Criterion 11 says regenerate **LAST**. Both cannot be true wave by
wave — resolve it by regenerating the report **at the end of every wave that
touches a coupling**, and doing the criterion-11 authoritative regeneration after
the final `.planning/` and `public/` write.

Recommended sequence. Each step names why it cannot move earlier.

**Wave 0 — before anything moves.**
1. Take §1.1–§1.4 to Dave. `1.1` blocks criterion 15 outright; `1.2` blocks
   moving one of the ten; `1.3` and `1.4` block criterion 4/5.
2. Record the phase-base measurements *as they actually are*: 4223 collected,
   4104 passed / 1 failed / 118 skipped, `gate-tools` 406 + 313, `tools.lints --all`
   exit 0, `docs-strict` exit 0. Do not carry `4105/118` from the ROADMAP without
   re-measuring — that is `D-19`'s own rule.
3. **Widen the gates FIRST, while the trees are still at `examples/`.** Every
   widening in §7 is a strict superset: adding `archive` to a scan root, to
   `GATED_TREES`, to `LINTED_TREES`, to `INCLUDE_ALLOWED_PREFIXES`, to
   `EXAMPLE_PREFIX`, to `PATH_TOKEN` changes **nothing** while `archive/` does not
   exist, so the tree stays green and each widening is provable in isolation.
   This is what lets the move itself be the only thing under test in Wave 1.

**Wave 1 — the move, and only the move.**
4. `git mv` ×10, one commit. Prove 265 R / 0 D. Nothing else in the commit.
   Expect: red `test`, red `gate-tools`, red `docs-strict`. Record the wreckage —
   it *is* criterion 5, 8 and 10's RED-before-GREEN evidence, taken once, honestly.

**Wave 2 — make the archive self-consistent (in-archive edits only).**
5. Four `parents[N]` repairs (§8.2) — the two executing tests depend on them.
6. 216 `$schema` header depths (§8.3), if Dave takes option (a).
7. Re-run only the executing tests; expect them green while everything else stays red.

**Wave 3 — `tests/` re-point.**
8. The eleven `tests/examples/test_*_output.py` modules plus `test_ext00_*` (the
   14 files the report cannot see, §5.0).
9. `tests/cli/test_schema_export.py:60`, `perf/suites/crossproc/conftest.py:52`.
10. Documentary docstrings under `tests/conformance`, `tests/integration`,
    `tests/deployment`, `tests/products` (§7.7).
11. Gate: `pytest --collect-only` back to **4223** and the four count floors back
    to 14 / 12 / 14 / 12. If collection is not 4223, a walk is still narrow.

**Wave 4 — `public/` and the command strings.**
12. 102 includes + 9 prose paths.
13. **13 `make example-*` command strings (§6.3)** — must land in the *same* wave as
    step 15 or the bijection is red in one direction or the other.
14. Gate: `make docs-strict` on all four steps, plus
    `test_no_stale_example_paths` and `test_documented_commands_exist`.

**Wave 5 — `Makefile`, CI, README.**
15. Delete the ten target definitions **and** their `.PHONY` names; reduce
    `examples:` to one member; dispose of the four live-leg targets per Dave.
16. `ci.yml` labels/comments/env; `live-legs.yml` per the same ruling.
17. `README.md` — 8 links, the prose, the `make` strings, the "runs all eight" claim.
18. `examples/external/README.md` — the orphaned family charter (§6.5).

**Wave 6 — the sweep, the ledger, the verdict.**
19. `tools/retirement_sweep.py:131-167` per `D-05`. **See §13.3 — the schedule's
    `path` fields are consumed by `tools/docs_tests/test_retirement_sweep.py`
    at import time and a naive re-point breaks module collection.**
20. `.planning/REQUIREMENTS.md`: `EXAM-01` at `:63` and `:315`; `DOCS-17`'s
    `Partial` cell in both channels (`:42` and `:336`) per criterion 12 and `D-06`.
21. Criterion 6's re-measure of the pinned `111` / `102` / `15 pages` at both
    `:42` and `:336`.
22. `STATE.md` and `ROADMAP.md` — **hand-edit, per `D-15`; back up and diff. Do not
    invoke a GSD state or roadmap writer.**

**Wave 7 — close.**
23. Regenerate `RETIREMENT-COUPLINGS.md` **LAST, in `.venv/bin/python`**, after
    every `.planning/` and `public/` write. Commit it.
24. `make ci` — six legs, `test` in **foreground chunks** with set-equality and
    disjointness proven (criterion 15).
25. `CLAUDE.md` §3.1 close: panel on the shipped tree, inlined; then the depth pass.

---

## 10. Historical records vs live documents

The project treats a dated record as history (`D-19`; the *"stale 52 left alone on
purpose"* precedent at `.planning/STATE.md:1065`). `tools/retirement_sweep.py`'s
`EXCLUDED_FROM_ASSIGNMENT` already encodes most of the boundary. Classified against
the actual document headers:

### LEAVE — historical, dated, or append-only. Rewriting these is the defect.

| Path | rows naming the ten | Header / basis |
|---|---:|---|
| `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/SURFACE-AUDIT.md`, `docs/SURFACE-CHANGES.md`, `docs/surface-changes/*` (25 files), `docs/PHASE_*_GATE.md` (4), `CLAUDE.md` | many | append-only, on the sweep's own exclusion list |
| `docs/surface/examples/before/` (24), `after/` (24), `ERGO-03-FROZEN.md` | 49 | *"frozen ERGO-03 baseline (`D-15`)"* — and §7.6: no live gate reads them |
| `docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md` | 7 | *"This document is evidence, not a proposal."* |
| `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md` | 2 | same header |
| `docs/CONTEXT_PRODUCT_REVISION.md` | 0 (s1 only) | *"Status: working record, 2026-08-10."* |
| `docs/retired/16-external-consumers/*` (3 files) | 3 | *"Status: historical record. Nothing here runs…"* |
| `docs/superpowers/plans/2026-08-14-*.md`, `specs/2026-08-14-*.md` | 3 | dated implementation plans |
| `docs/surface/examples/SECTION-2-TRANSPORT.md` | 3 | *"Status: spike record… Measured: 2026-08-10"* |
| `docs/surface/examples/FIBO-EXTENSION.md` | 0 (s1 only) | out of scope |
| `.planning/phases/**` (306 files by grep) | — | the planning tree; not shipped, not published |

**None of them is gated.** No standing check resolves a path in any of these. The
recommendation is to leave every one and **say so explicitly in the phase record**,
so a later reader can tell "researched and decided to leave" from "never checked" —
which is the distinction `D-05` and Phase 22.1 exist to protect.

### LIVE — must be re-pointed

`README.md`, all 15 `public/` pages, `Makefile`, `.github/workflows/ci.yml` and
`live-legs.yml`, `examples/external/README.md`, `.planning/REQUIREMENTS.md`
(`EXAM-01` ×2, `DOCS-17` ×2), `.planning/ROADMAP.md` + `.planning/STATE.md` (this
phase's own record), `docs/surface/examples/RETIREMENT-COUPLINGS.md` (generated),
and everything under `tests/`, `tools/`, `perf/` in §7.

**Borderline, and worth a sentence in the plan either way:** the 12 documentary
docstrings under `tests/` (§7.7). Ungated, so they *may* stay stale; but they are
in live code, not in a dated record, so the historical-record argument does not
protect them.

---

## 11. What the `Partial` cell may claim (criterion 12 / `D-06`), measured

The cell must say **"out of the `examples:` aggregate"**, NOT "out of live CI", and
must NAME what still exercises the archived trees. The naming figures, verified:

- `tests/examples` holds **31** files; **25** name the condemned set; **2** EXECUTE it (`test_cross_process_output.py`, `test_ext00_hardening.py`).
- `tests/examples` collects **515** tests.
- The `examples:` aggregate goes from **11** members to **1**: `example-hw1-harness-clients`.
- After the move, `tests/` still reaches the archive from at least: `tests/examples` (14 modules), `tests/cli`, `tests/products` (4 count floors), `tests/invariants` (the citation walk), `tests/perf_smoke` → `perf/suites/crossproc`, and — if §7.4's widening lands — every CINV lint.

**Two staleness defects already in `DOCS-17`'s cell, which criterion 12's rewrite
must not carry forward:**
1. The cell claims *"zero published references to the `s1-*` trees"*. Measured: **7**, all on `public/concepts/answers-no-document-contains.md`, shipped by Phase 22 on 2026-08-23. That is the same measurement `D-IMPL-190` ruling 1 limb (b) relies on, so the two documents contradict each other today.
2. The pinned `111 references across 15 published pages, 102 of them snippet includes` appears at **`.planning/REQUIREMENTS.md:42` and `:336`** — both are criterion 6's subject and both must move together.

---

## 12. Criterion 13 — `CLNT-17` byte-identity anchor

`CLNT-17` occupies exactly two lines: `.planning/REQUIREMENTS.md:213` (checkbox
channel) and `:420` (table channel). Anchor at the phase base:

```bash
grep -n 'CLNT-17' .planning/REQUIREMENTS.md | sha256sum
# f2839f8fa0a8581b5cd9c7032d46da12e4d5c5544995c62d2bf377e6a7c0ba0c
```

Note this hash includes the line numbers, so it moves if anything above line 213
gains or loses a line. Prefer hashing the two lines' **content** without `-n`, or
extract by requirement id, so the check measures what criterion 13 means (the row's
text) rather than its position. Recording the exact command the plan uses matters
more than which one it is.

---

## 13. Risk list

| # | Risk | Severity | Evidence | Mitigation |
|---|---|---|---|---|
| R-1 | Phase base already red on `test` | **BLOCKING** | §1.1, reproduced | Dave rules before Wave 1 |
| R-2 | `H-14` forbids moving `external/00-hello-context` | **BLOCKING** | §1.2, 5 tests red, `D-IMPL-167` | Dave amends or descopes |
| R-3 | `docs-strict` step 1 rejects every re-pointed include | **BLOCKING** | §1.3, proven on `include_escapes` | widen `INCLUDE_ALLOWED_PREFIXES`; name it as a boundary change |
| R-4 | Criterion 5's second witness reports paths the page never wrote | **BLOCKING** | §1.4, proven end-to-end | widen `PATH_TOKEN` in Wave 0 |
| R-5 | Four count floors + the citation walk break; collection drops 4223→4154 | **HIGH** | §7.1, §7.2, measured | widen scan roots in Wave 0, before the move |
| R-6 | 216 `$schema` headers rot **silently** — the gate stops looking rather than failing | **HIGH** | §8.3, 2 failures where 216 were owed | widen the glob, fix all 216; or record the choice not to |
| R-7 | 265 files leave every CINV lint's scope; `--all` exits 0 having looked at nothing | **HIGH** | §7.4, measured | widen `LINTED_TREES` + `RULE_TREE_SCOPE` |
| R-8 | 13 published `make example-*` strings break the documented-commands bijection | **HIGH** | §6.3 | same wave as the Makefile edit |
| R-9 | Archive not runnable: 4 `parents[N]` off by one | **HIGH** | §8.2 | Wave 2, before criterion 8's control |
| R-10 | Re-pointing the sweep schedule breaks `test_retirement_sweep.py` at import | **HIGH** | §13.3 below | derive `WAVE_*` differently or keep the wave integers |
| R-11 | `README.md` rot is invisible to every gate | MEDIUM | §6.4 | checklist item, not a gate |
| R-12 | `examples/external/README.md` orphaned, references a moved tree | MEDIUM | §6.5 | decide: move it, edit it, or record leaving it |
| R-13 | Four live-leg `make` targets outside criterion 3's enumeration | MEDIUM | §6.2, `live-legs.yml` invokes two | put three options to Dave |
| R-14 | Criterion 2's "exactly four trees" vs six `git ls-files` entries | LOW | §6.5 | state the reading in the plan |
| R-15 | `test_the_committed_report_is_current` red for the whole phase | LOW | §9 | regenerate per wave, authoritatively last |
| R-16 | Criterion 1's "no content changed" vs 220 in-archive edits | LOW | §8.1 | evidence it against the move commit |

### 13.3 The sweep re-point trap, in detail

`tools/docs_tests/test_retirement_sweep.py:86-100` derives its fixture paths from
the schedule **at module import time**:

```python
WAVE_8 = next(entry.path for entry in RETIREMENT_SCHEDULE
              if entry.wave == 8 and entry.path.startswith("examples/"))
```

Three of these (`WAVE_8`, `WAVE_10`, `WAVE_11`). If `D-05`'s re-point changes the
`path` to `archive/examples/…`, `startswith("examples/")` matches nothing and
`next()` raises `StopIteration` **during collection** — the whole 41-test module
disappears. If the `wave` integers change too, same outcome. Either keep the wave
integers and widen the predicate, or re-derive `WAVE_*` from the new owner. Also
check `KNOWN_COUPLED_FILES` (`:105-120`, 14 files, a floor) — if any file's
reference is *removed* rather than re-pointed (e.g. deleting a README link instead
of updating it), it drops off the floor and
`test_every_known_coupled_file_is_found` goes red.

**And a gap in `D-05` itself.** The ruling re-points "the ten moved trees" and
leaves "the `s1` pair's `17-08` rows". It says nothing about the **eleven
`tests/examples/test_*_output.py` entries and the two `public/tutorial/*.md`
entries** in the schedule, all owned by `16-15`/`16-17`/`16-18` — a phase
`D-IMPL-152` retired. Those paths are not moving and not being deleted, so nobody
owns them and they cannot be re-pointed to Phase 23 plans without asserting
Phase 23 will delete them (it will not). Surface this; do not pick a default.

---

## 14. Unknowns and what I could NOT verify

Stated as unknowns rather than filled in.

1. **I did not run the full `make ci` after a *complete* simulated phase.** The trial was a bare `git mv` with zero compensating edits. Every "this will be green after X" in §7 is an inference from a measured red plus a read of the mechanism — not a measured green. The four count floors returning to exactly 14/12/14/12 under a widened root is arithmetic on measured partitions, not an observed test run.
2. **I did not measure the `test` leg's full pass/skip totals at the phase base.** Running the full suite takes ~25 minutes and the host kills background jobs at ~10. I measured `--collect-only` (4223, matching the ROADMAP), ran `tests/invariants` (1 failed / 4 passed), and ran twelve directories under the trial move. **The claim that the base is 4104 passed / 1 failed / 118 skipped is arithmetic on the 22.1-recorded 4105/118 plus the one failure I reproduced — not a single observed run.** The plan should re-measure it in chunks in Wave 0.
3. **I could not determine whether `docs/DECISIONS.md`'s `D-IMPL-192` text is exempt from the citation ceiling by design or by accident.** The gate flags only `.planning/ROADMAP.md:2212`, not the identical citations in `docs/DECISIONS.md:548` or `23-CONTEXT.md`. `HELD_BACK_HOSTS` names neither. I did not trace which pattern or `prose_lines` rule spares them.
4. **I did not verify what a widened `INCLUDE_ALLOWED_PREFIXES` does to the post-build `site` scan** (`docs-strict` step 4). Step 1 is proven to reject; step 4 walks the built site and I did not exercise it against archive-sourced content.
5. **I did not enumerate which of the 25 `tests/examples` files "name the condemned set"** — that figure is `D-IMPL-191`'s and I did not re-derive it. I measured a different thing: 14 files carry a literal ten-tree path (11 `test_*_output.py` + 3 `test_ext00_*`), and 7 more appear in the coupling report. Those two sets overlap. **The `25 of 31` figure criterion 12 requires the cell to state is unverified by me.**
6. **I did not determine whether the archive should carry its own `README.md`** explaining what it is. `D-03` pins the root and leaves internal layout to the planner; nothing measured says either way.
7. **I did not test the `git mv` under a case-insensitive filesystem or with `core.ignorecase`.** Irrelevant on this host (Linux, ext4) but unverified generally.
8. **`tools/measure_examples.py`'s fragments** — I established that `tests/examples/test_surface_audit.py` (the gate the Makefile comment names) does not exist, so the `before/`/`after/` trees have no live reader. I did **not** search exhaustively for a second reader; the claim rests on that one absence plus `measure-examples` not being in `ci`.
9. **Whether `EXAMPLE_PREFIX`, `PATH_TOKEN`, `GATED_TREES`, `LINTED_TREES`, `SCANNED_TREES`, `INCLUDE_ALLOWED_PREFIXES` and the schema-header glob should each take `"archive/"` or `"archive/examples/"`** is a design call I did not settle; both work for the pinned path and they differ in what a *future* archive sibling would inherit.

### Measurement hazards found while doing this research — worth carrying into the plan

- **`echo "EXIT=$?"` after a pipe reports the pipe's last command, not the one you care about.** `mkdocs build --strict 2>&1 | tail -12` printed a `SnippetMissingError` traceback and then `EXIT=0`. Use `${PIPESTATUS[0]}` or drop the pipe. A phase whose primary witness is `make docs-strict` cannot afford this.
- The sweep must run under `.venv/bin/python`; a system-python run silently drops six rows at exit 0 (`D-GATE-22.1`). Every measurement above used the venv.
- `git diff -M --diff-filter=R` needs `--cached` while the move is staged.

---

## 15. Non-vacuity and sabotage targets

Criteria 5, 8, 10 and 16 want controls watched RED before GREEN. Concrete
mutations, each with the check that should catch it — **and, where nothing would,
that is recorded as a finding.**

### Criterion 5 — the include repoint, two independent witnesses

| # | Mutation | Should catch it | Verified? |
|---|---|---|---|
| S-1 | Revert ONE include on `public/how-to/bind-a-harness-adapter.md:63` to `examples/…` | `mkdocs build --strict` → `SnippetMissingError` naming that exact path | **YES** — observed verbatim in the trial |
| S-2 | Same mutation | `tools/docs_tests/test_no_stale_example_paths.py::test_every_snippet_include_resolves_on_disk` → offender naming `page:line -> target` | **YES** — observed, 102 offenders listed |
| S-3 | Revert ONE **prose** path (`public/how-to/grant-and-revoke-a-skill.md:15`) | `::test_every_prose_path_reference_resolves_on_disk` — **and the strict build must stay GREEN**, which is what proves the two witnesses are not the same witness | **YES** for the test; the build's silence on prose is `check_paths`'s documented scope |
| S-4 | Widen `INCLUDE_ALLOWED_PREFIXES` to `("",)` | **NOTHING.** No test anywhere references it (§1.3). **FINDING** — the boundary this phase must widen is itself unguarded. Consider a one-line assertion as part of the widening. | **verified absent** |
| S-5 | Narrow `PATH_TOKEN` so it matches nothing | `test_the_scan_finds_path_tokens_to_check` (`:140`) — the existing non-vacuity precondition | **YES**, by construction |

### Criterion 8 — the two executing tests really execute

| # | Mutation | Should catch it | Verified? |
|---|---|---|---|
| S-6 | Delete `archive/examples/04-cross-process/producer_child.py` | `tests/examples/test_cross_process_output.py` — 19 ERRORS in the trial, at collection | **YES** |
| S-7 | Delete `archive/examples/external/00-hello-context/serve.py` | `test_ext00_hardening.py` — 27 FAILED + `test_ext00_serve_output.py` 15 ERRORS | **YES** |
| S-8 | Leave `producer_child.py:53` at `parents[1]` after the move | The child's `sys.path` misses `src`/`runtime` → `ImportError` in the spawned process | **NOT verified** — I proved the depth is wrong arithmetically, not by running the moved child. **Run it.** |
| S-9 | Make the test **skip** instead of run (e.g. an env guard) | **NOTHING in the total.** A skip and a pass are indistinguishable in `4105 passed / 118 skipped` unless the *skip count* is also asserted. **FINDING** — criterion 8's own wording names this; the control must assert the skip count, or assert on a run artefact the archived source produces, not on the pass count. | **finding, by inspection** |

### Criterion 10 — archived paths still count as couplings

| # | Mutation | Should catch it | Verified? |
|---|---|---|---|
| S-10 | Delete one `Retirement(...)` entry for an archived tree from `RETIREMENT_SCHEDULE` | `test_the_committed_report_is_current` (row count drops, report diffs) **and** `test_every_known_coupled_file_is_found` if that tree was the only witness for a `KNOWN_COUPLED_FILES` entry | **partly** — the staleness half is verified (the report went stale in the trial); the floor half depends on which entry |
| S-11 | Re-point the schedule to `archive/examples/…` but leave the walk narrow so it finds nothing | `test_the_sweep_finds_couplings_at_head` (`:152`) and `test_the_coverage_is_repo_wide` (`:169`, `>= 10` files outside) | **YES**, by construction — these are the sweep's own non-vacuity floors |
| S-12 | Set `RETIREMENT_SCHEDULE = ()` | `test_the_walk_reads_a_non_empty_tree` passes (it counts *files*, not rows); `test_the_sweep_finds_couplings_at_head` fails | **YES** |
| S-13 | Keep the schedule pointed at the **old** `examples/…` paths after the move | The sweep reports **zero** rows for the ten trees and exits 0 — a confident clean total over a tree it did not look at. `test_the_sweep_finds_couplings_at_head` still passes on the `s1` rows. **FINDING: this is exactly the Phase 22.1 defect and the current gates would NOT catch it.** Criterion 10 needs a control aimed here specifically — e.g. an assertion that every scheduled `path` resolves on disk (the schedule's own comment at `:159-167` says each path *"was confirmed to exist before being listed"*, but nothing asserts it). | **finding, by inspection** |

### Criterion 16 — non-vacuity floors

| # | Mutation | Should catch it | Verified? |
|---|---|---|---|
| S-14 | Make the include-repoint check scan an empty page list | `test_the_published_tree_is_populated` (`:135`) + `test_the_scan_finds_path_tokens_to_check` (`:140`) | **YES**, existing |
| S-15 | Make the moved-file check compare an empty pathspec | **The `VAC-01` guard is the precedent**: `git ls-files archive/ \| wc -l > 0` beside the diff, because a misspelled pathspec diffs empty exactly like a clean one. Verified in this research: `git ls-files archive/` → 265. | **YES** |
| S-16 | Widen a scan root to `("archive",)` only, dropping `"examples"` | The four count floors stay green (the same 14/12/14/12 witnesses) while the *surviving* examples stop being scanned. **FINDING: a floor cannot see a swap.** Assert root **membership**, not just the total. | **finding, by inspection** |

---

## 16. Sources

### Primary — authoritative project documents (HIGH)
- `.planning/phases/23-…/23-CONTEXT.md` — `D-01`..`D-07`
- `.planning/ROADMAP.md:2104-2224` — goal, measured scope, the sixteen locked criteria
- `docs/DECISIONS.md:540` `D-IMPL-189`, `:544` `D-IMPL-190`, `:546` `D-IMPL-191`, `:548` `D-IMPL-192`, `:542` `D-GATE-22.1`, `:247` `D-IMPL-167`
- `CLAUDE.md` §3.1, §6.4, §7.3, §11, §17
- `.planning/STATE.md:1065` — the "stale 52 left alone on purpose" precedent

### Primary — measured on the tree (HIGH)
Every count in this document carries the command that produced it. All runs used
`.venv/bin/python` (Python 3.12.3) at `aefd072`. The trial move was performed and
reverted; `git status --porcelain` and `git rev-parse HEAD` confirm the tree is
byte-identical to its starting state (only the three pre-existing untracked
`references/*.md` remain).

Files read directly: `Makefile`, `mkdocs.yml`, `pyproject.toml`,
`.github/workflows/{ci,live-legs,perf}.yml`, `README.md`,
`tools/{retirement_sweep,publish_scan,measure_examples,check_schema_headers}.py`,
`tools/lints/{__main__,citations}.py`,
`tools/docs_tests/{test_no_stale_example_paths,test_documented_commands_exist,test_resolver_seam_obligations,test_retirement_sweep,test_snippet_gate,test_requirement_ledger}.py`,
`tests/products/{test_gate_two_call_shape,test_required_operators_guard}.py`,
`tests/invariants/test_citation_coverage.py`,
`tests/examples/{test_artifact_schema_headers,test_hw1_harness_clients_retirement}.py`,
`tests/lints/test_examples_scope.py`, `perf/suites/crossproc/conftest.py`,
`examples/external/README.md`, `.planning/REQUIREMENTS.md`,
`docs/surface/examples/RETIREMENT-COUPLINGS.md`.

### Not used
No external documentation, no web search, no Context7. This phase's domain is
entirely in-tree; there is no library question to answer and no package to install,
so §Standard Stack and §Package Legitimacy Audit are omitted as inapplicable
rather than left empty.

---

## 17. Assumptions log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Adding `"archive"` to a scan root restores each count floor to its exact current value | §7.2 | A floor still red at Wave 3; caught by the Wave 3 gate, cheap |
| A2 | The base `test` leg is 4104 passed / 1 failed / 118 skipped | §14.2 | Criterion 7's arithmetic is off by whatever else is red; re-measure in Wave 0 |
| A3 | The 12 documentary docstrings under `tests/` are read by no gate | §7.7 | A gate goes red late; the trial run is evidence against this, but it is absence-of-evidence |
| A4 | `docs/superpowers/`, `docs/retired/`, the two `*_RULING_EVIDENCE.md` and `SECTION-2-TRANSPORT.md` are historical and must not be rewritten | §10 | Rewriting history, or leaving a live doc stale — the two failure directions are opposite, which is why this is Dave's call if he disagrees |
| A5 | `examples/external/README.md` is not among the 265 and its disposition is open | §6.5 | Criterion 1's 265 is wrong, or an orphaned charter ships |
| A6 | Fixing 216 `$schema` header depths is the right call over leaving them | §8.3 | 216 unnecessary edits, or 216 silent lies — recommend putting it to Dave as a one-line choice |

---

## 18. Metadata

**Confidence breakdown**
- Coupling inventory: **HIGH** — two independent measurements, reconciled file by file, with the report's blind spot located and explained by the sweep's own documented drop rule.
- What breaks: **HIGH** — the move was performed and the suite run. Nothing in §7 is inferred from a grep alone.
- What fixes it: **MEDIUM** — each fix is read off the mechanism, not observed green (§14.1).
- The four stop-and-asks: **HIGH** — §1.1 reproduced, §1.2 reproduced with the ruling quoted, §1.3 and §1.4 proven against the shipped functions.
- Order of operations: **MEDIUM** — reasoned from the dependency structure, not executed.

**Research date:** 2026-08-24
**Valid until:** the next commit that touches `examples/`, `public/`, `Makefile`,
`tools/` or `.planning/`. Every figure here is pinned to `aefd072` and this project
requires re-measurement rather than carriage (`D-19`, `D-IMPL-174`).
