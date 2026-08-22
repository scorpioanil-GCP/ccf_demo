# Phase 21 — Findings

**For Dave.** Five sections: what the audit found, what is genuinely not built,
the verification debt nobody but you can discharge, which counters moved, and
four things the audit saw and deliberately did not touch.

Every figure below was produced by running the strict parse on 2026-08-22, not
recalled from a plan or a SUMMARY.

---

## 1. What the audit found

Fifty-four rows were audited. All fifty-four now carry a verdict in both of the
ledger's status channels: **38 `Complete`, 2 `Complete as ruled`, 9 `Partial`,
5 `Not built`, 0 `Orphaned`.** Two-thirds of the ledger's outstanding debt was
work that had already shipped and was never ticked.

**The traceability table holds 143 rows at the moment this was written.** That
is a reported measurement, not a number any check carries (`D-21`). It was 133
at the pinned base `c51406b`; the difference is this phase's own ten `RECON-`
rows, minted in wave 1. **The ten are not members of the 54** — the working set
is a frozen roster of named ids taken at the pinned base, and the `RECON-` rows
are Phase 21's own. Their verdicts are written in plan `21-06`.

**The working set is 54, and the predicate is the point.** A row is in it when
its verdict is *not a member of the Complete family* — `Complete`, `Complete as
ruled`, `Complete over the ruled scope`. It is **never** a string inequality
against `"Complete"`. A later reader who runs `grep -vc "| Complete |"` will get
**56**, not 54, because that reading drags in `DCD-09` (`Complete over the ruled
scope`) and `DCD-10` (`Complete as ruled`). You have already ruled on both, and
both are checked `[x]` in the other channel. **56 is the wrong predicate finding
nothing, not a skipped row.**

**One reading of criterion 3, stated once and marked as a reading rather than a
relaxation** (`D-17`, logged as `D-IMPL-172`). `path::symbol` is the preferred
form and is *required wherever the evidence is Python*. Where the evidence is a
document, an anchored line citation that the lint resolves is admissible —
because `tools/lints/citations.py:252` anchors the `::` pattern to `.py` files,
so a markdown document has **no `path::symbol` form at all**, and roughly
twenty-four of the fifty-four rows are about documentation. The citation still
has to resolve; the machinery that resolves it already ships. Full repo-relative
paths only — a bare basename is refused (`D-06`, unchanged).

---

## 2. The work list — what is genuinely not built

Five rows carry the verdict `Not built`. Nothing here was built in this phase
(`D-11`); the list exists so you can rule what is worth a phase and what should
be dropped. Costs are lifted from the lane records, not re-derived.

### Group A — one knot, four rows, blocked on you rather than on an executor

These four cannot be sequenced independently. Each one's obvious first move
breaks another's evidence.

| Row | What it requires | What closing it means |
|---|---|---|
| `DOCS-17` | retire `examples/00-quickstart`…`08-e2e-demo` and `examples/external/00-hello-context` | retire all ten directories **and** re-cut every published page that sources from them in the same change — **111 references across 15 published pages, 102 of them snippet includes**, re-measured 2026-08-22 and unmoved — plus the make targets, the CI `examples:` job, the floor constants those trees feed, and the seam-obligation gate whose only surviving `refuse_bound_payload` witness is `examples/04-cross-process/producer_child.py`. `D-IMPL-145` limb 2 quarantined the group deliberately, in your ruling, and plan `17-08` returned the `00`–`08` half of `D-27` to you undecided. |
| `CLNT-17` | disposition the two condemned Section-1 trees | remove `examples/s1-00-companies-over-revenue` and `examples/s1-01-hello-context-product` together with every gate, make target, floor constant and published snippet that names them, in one change because `D-27` forbids a partial state; retire `tests/examples/test_spine_separation.py` and `tests/examples/test_section_one_is_agent_free.py` rather than leave them blind; re-count `MINIMUM_GATE_CALL_SITES`, `MINIMUM_PROJECTING_BODIES` and `MINIMUM_RESOLVED_BINDER_SITES` from the post-removal tree; and first supply a replacement worked example for `ccf.products.request::refuse_request` so the seam-obligation gate keeps a live call site. Needs the same undecided `D-27` ruling. |
| `DOCS-14` | Section 3 — host embedding and agentic skilling, plus its pages | re-derive the demonstration against the surface that exists now rather than lifting Phase 16's abandoned Section-3 plan: in-process consumption, MCP egress, A2A admission and an ArtifactStore swap in one coherent worked example, plus the published pages, plus the plain statement that SDK agents are governed identity and are structurally barred from calling a model. The substance exists — `examples/04-cross-process`, `07-artifact-store-mcp`, `02-skilling` — but **all three are among the ten `DOCS-17` condemns.** |
| `EXAM-02` | the re-homed example-enrichment obligation | re-derive the enrichment obligation against today's surface: a worked example whose definition artifacts carry the specialization axes, skilling, HITL and replay, with the example code thin and generic under the No-Hardcoding Rule. Coupled to `DOCS-14` — same missing Section-3 home. Building a replacement before the Phase-13 trees are retired duplicates the surface; retiring them first deletes the only worked demonstration of skilling and HITL in the tree. |

**The knot in one sentence:** the replacements have to exist before the
condemned trees can go, and the condemned trees are where the replacements'
subject matter currently lives.

**Two questions inside Group A are yours and only yours:**

1. The `00`–`08` half of `D-27` — plan `17-08` returned it undecided and
   `D-IMPL-145` quarantined it pending your ruling.
2. Whether a Section-3 replacement keeps the `s3-` naming at all. The section
   scheme was Phase 16's, and Phase 16 is not resumable.

### Group B — stands nearly alone

| Row | What it requires | What closing it means |
|---|---|---|
| `DOCS-15` | the adoption-argument page | one published page naming RAG over a vector store, hand-rolled context assembly, and a semantic layer plus prompt templates, stating what each lacks against **cited shipped mechanism**, using the UBO question as its worked demonstration, and carrying the passage-anchor honesty caveat. The UBO demonstration already exists and is gated five ways in `examples/s1-01-hello-context-product`, so the page has a subject to point at rather than one to invent. **The cheapest of the five and the highest adoption leverage.** Coupled to nothing except that tree's survival, which `CLNT-17` proposes ending. |

### The owed halves of the nine `Partial` rows

Not on the work list above, because each of these rows is partly discharged.
One line each, so you can rule on them without re-reading the ledger.

| Row | Owed |
|---|---|
| `EXAM-01` | Sections 2 and 3 have no example, so the seven-heading README template covers two trees; the only gate on the template guards a pre-Phase-17 tree and reaches neither Section-1 README. |
| `EXAM-03` | no `example-s2-` or `example-s3-` target, and neither Section-1 target is in the `examples:` aggregate — both declare a networked substrate. |
| `DOCS-03` | six artifact class ids are named on no published page: `ccf.admission-record`, `ccf.deployment-config`, `ccf.peering-inbound-payload-ceiling`, `ccf.product-entitlement-policy`, `ccf.product-request-contract`, `ccf.scope-mapping`; and no page publishes a schema. |
| `DOCS-10` | the six-backend `content_hash` CI matrix — `backends.yaml` declares one profile and `example-s1-00` is in no job. |
| `DOCS-11` | scope: the spine/deployment gate globs `s1-*`, two directories out of thirteen. |
| `DOCS-12` | the published pages — zero pages name `s1-00` or `s1-01`. |
| `DOCS-13` | the published pages — one paragraph, no Section-2 page. |
| `DOCS-18` | limb 3 only, which is this phase. Limb 1 is **orphaned by your own `D-IMPL-96`** and should stay closed, not re-opened. |
| `DCD-02` | pointer population, `Pending by design` under `D-IMPL-119` limb 3(b) until the assembly path is principal-scoped. Confirmed against the tree, not rewritten. |

**`DOCS-12`, `-13`, `-14` and `-15` are short by the same thing** — a
documentation surface for the examples that actually shipped. That is one ruling
question, not four.

---

## 3. The verification debt — named, not touched

Eleven phase records carry undischarged `human_verification` blocks totalling
**27 items**. The roster below was produced by parsing every
`.planning/phases/*/[0-9]*-VERIFICATION.md` for a `human_verification:` block —
sixteen files match the glob, eleven carry the block — and it agrees path for
path with `21-RESEARCH.md` §7's corrected table.

| Phase | Items | Record |
|---|---|---|
| 11 | 1 | `.planning/phases/11-performance-battery/11-VERIFICATION.md` |
| 12 | 1 | `.planning/phases/12-synthetic-data-demonstration/12-VERIFICATION.md` |
| 13 | 1 | `.planning/phases/13-examples-suite-upgrade/13-VERIFICATION.md` |
| 14 | 2 | `.planning/phases/14-documentation-suite/14-VERIFICATION.md` |
| 15.1 | 2 | `.planning/phases/15.1-ergonomics-gap-closure/15.1-VERIFICATION.md` |
| 15.2 | 2 | `.planning/phases/15.2-substrate-adapters-and-query-pushdown/15.2-VERIFICATION.md` |
| 15.3 | 5 | `.planning/phases/15.3-fluree-adapter-tier-1-substrate-inserted/15.3-VERIFICATION.md` |
| 15.4 | 5 | `.planning/phases/15.4-backend-registration-seam-the-substrate-stops-naming-its-ada/15.4-VERIFICATION.md` |
| 18 | 2 | `.planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/18-VERIFICATION.md` |
| 18.1 | 3 | `.planning/phases/18.1-simplify-the-mcp-example-separate-the-server-from-the-client/18.1-VERIFICATION.md` |
| 19 | 3 | `.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-VERIFICATION.md` |
| **Total** | **27** | **11 records** |

### Why the tool says 24 and the files say 27

`gsd-sdk query audit-uat` reports **24 items across 9 files**. The files carry
**27 across 11**. The query **filters on each record's frontmatter `status:`**,
so it drops two records that hold undischarged blocks under a different status:

- **Phase 12** — frontmatter `status: passed`, 1 item. Its own prose one screen
  below reads *"**Status:** human_needed (all automated checks passed; one
  subjective legibility check remains)"*. That gap is exactly what the filter
  falls into.
- **Phase 18** — frontmatter `status: gaps_found`, 2 items, the
  `human_verification:` key at line 74.

**This is this phase's own subject, arriving a third time.** First
`grep -c "| Pending |"` reported 52 where a strict parse says 54, because two
cells are bolded. Then `grep -vc "| Complete |"` reported 56, because a string
inequality is not a membership test. Now a query that appears to report all of
something reports only the subset its filter admits. Three tools, three counts,
one shape: **a check structurally incapable of reporting the thing it appears to
report.**

Criterion 11 was **amended on your ruling** (`D-20`, 2026-08-21). It read *"the
24 `human_needed` verification items across 9 phases (11, 13, 14, 15.1–15.4,
18.1, 19)"*; it now reads *"all 27 across 11 phase records"*, with the roster
re-derived by parse rather than by query.

**`audit-uat`'s filter is named, not fixed** — the same reasoning as `D-07` for
the citation lint. Tooling repair inside an audit phase surfaces defects
elsewhere that then need their own fixes, and the phase would stop being an
audit.

### Why no executor can discharge them

Every one of the 27 needs you at a keyboard: a live GitHub Actions dispatch, a
credentialed run against a real substrate, a subjective read of a document as a
newcomer, or a ruling only you have the authority to make. None of that is
programmable from inside this repository (`D-13`).

At the discuss sitting you chose **"out, name them"** over "out, and open a
separate phase", so **no separate phase is commissioned** for this debt. It is
recorded here so it is not lost at the milestone close.

### The untouched claim is mechanical, not attested

`tools/docs_tests/test_requirement_ledger.py::test_the_human_needed_verification_records_are_untouched`
diffs **all eleven** paths against the pinned base `c51406b` and requires the
result to be empty. It was widened from nine to eleven under `D-20` consequence
(c), so Phase 12's and Phase 18's records cannot be edited without the gate
going red. Nobody is asking you to take an executor's word that the records were
left alone.

### The 27 items, verbatim from the records

**Phase 11** (1)

1. "Manually dispatch .github/workflows/perf.yml (suite=all) on GitHub, download perf/results artifact, and record the first perf/baselines/gh-ubuntu-24.04.json via the six-step ritual in perf/README.md with Dave's D-IMPL-70 approval logged in docs/DECISIONS.md"

**Phase 12** (1)

1. "Read docs/demo-walkthrough.md and examples/08-e2e-demo/README.md as a newcomer, then run `make example-08` and read the staged console narration"

**Phase 13** (1)

1. "Read one example's README + artifacts cold (suggest examples/01-agent-basics) and identify which artifact/key to edit to adapt it to a new domain"

**Phase 14** (2)

1. "Read public/tutorial/adopters-guide.md end to end as an adopter who has never seen CCF. Follow it literally from `pip install -e \".[dev]\"` through the replay section."
2. "Open the built site (`make docs-serve`) and page through Concepts → Pillars. Confirm each of the five pillar diagrams renders as a Mermaid graph, not as a raw code block or an empty figure."

**Phase 15.1** (2)

1. "Rule on the four `public/` sites (N-2). They are the same claim family Dave ordered fixed in W-2/W-3, in the tree mkdocs publishes, and they are recorded nowhere. Two options, and the choice is a scope call: (a) correct them now — docs-only, no assertion, no example behavior, the same shape as the tests/ corrections just accepted; or (b) widen deferred-items.md a fifth time to name `public/` with the four sites enumerated, and carry them to Phase 16 explicitly."
2. "Rule on whether the fourth reproduction of the citation-staling defect (N-1) changes the tooling answer already deferred to Phase 16. The strongest datum is now stronger than the register's own: the plan caught the three citations it staled inside `tests/` and missed the one it staled inside `deferred-items.md` — the file it had open — because its sweep scope was the phase-touched trees and the live citers are in `docs/` and `.planning/`."

**Phase 15.2** (2)

1. "Decide whether to amend the 'all five adapters carry a push proof' / 'each with native pushdown proven by its own translated_answers telemetry' wording in .planning/REQUIREMENTS.md (SUBQ-08 annotation) and docs/DECISIONS.md (D-GATE-15.2 entry)."
2. "Refresh .planning/STATE.md to the post-gate reality."

**Phase 15.3** (5)

1. "Confirm the `Fluree leg (service container)` step is green on `main` in GitHub Actions, and that the workflow run shows it as blocking (no skip, no continue-on-error)"
2. "Rule on the `schedule:` trigger added to .github/workflows/live-legs.yml (weekly cron, Mondays 07:00 UTC)"
3. "Rule on the goal's own wording: 'zero changes to the SDK core' and 'suite diff: one fixture parameter'"
4. "Rule on the nine open code-review findings (WR-01, WR-04..WR-08, IN-01..IN-03) — fix in phase, defer with a DI entry, or accept"
5. "Rule on refreshing 15.3-GATE-PACKAGE.md §3 and §11 against merged `main`"

**Phase 15.4** (5)

1. "Rule on whether D-IMPL-93's `D-IMPL-92's gate is superseded ... not deleted` reaches the gate SCRIPT or only the gate's normative RULE."
2. "Re-run `make leg-postgres` against a live Postgres and confirm 25 passed."
3. "Decide whether `docs/15.4-GATE-PACKAGE.md` gets a post-review addendum before the §3.1 step-3 presentation."
4. "Confirm Success Criterion 2's wording against what the rules actually enforce."
5. "CLAUDE.md §3.1 step 3 — phase gate approval."

**Phase 18** (2)

1. "Rule on whether the `mcp+stdio` portability claim must be reachable from `examples/hw1-companies-over-revenue/consume.py`"
2. "Rule on whether an adopter has a supported path to write an mcp+stdio server program"

**Phase 18.1** (3)

1. "Rule on the ROADMAP scope preamble's phrase `three changes, none of them new mechanism`, given what actually shipped in `src/`."
2. "Rule on the two observations the phase recorded but deliberately did not fix, both of which currently live only in SUMMARY files: (a) a misnamed surface fragment is silently dropped from the assembled record, with data loss on the obvious remedy; (b) `tools/retirement_sweep.py --report` is not read-only."
3. "Run both documented commands against a POPULATED hw1 deployment, twice each, and compare the printed content addresses."

**Phase 19** (3)

1. "Rule whether Phase 19 may take its D-GATE with NO Success Criteria section in its ROADMAP entry. `gsd-sdk query roadmap.get-phase 19` returns `success_criteria: []`. The phase was therefore verified against plan `must_haves` only — 63 truths across eight plans — with no phase-level contract above them."
2. "Rule on two stale citations THIS PHASE introduced into `.planning/STATE.md` and that no gate can see. `.planning/STATE.md:15` cites `client.py:139-141` for the false-clock sentence (line 139-141 is now the `product_id` property) and `.planning/STATE.md:30` cites `client.py:196-201` for the `check_outcome` thesis paragraph (196-201 is now the `as_of` Args block). Both were accurate when written at planning time; `19-02`/`19-07` moved the code. The citation lint DROPS both, because `client.py` is an ambiguous basename — `resolve_cited` returns `(None, True)` and `tools/lints/citations.py` records `ambiguous_path` as UNCHECKED rather than as a finding. This is exactly the defect class the phase's own ROADMAP note named at `.planning/ROADMAP.md:1652`."
3. "Rule whether `gsd-sdk query verify.key-links` is fixed or worked around. The verb double-escapes YAML backslashes and reports `Invalid regex pattern: door_answer\\(` for every key-link pattern containing an escaped paren, marking the link `verified: false` without ever running it. Six of this phase's twelve declared key links are unevaluated by the SDK for this reason."

---

## 4. The counter corrections

`D-19` required three stale counters to be corrected rather than merely
reported, under three constraints: the replacement figure comes from the strict
parse and is never assumed; every edit is a hand-edit with a backup and a diff;
and this record names each correction and its old value. A phase about honest
counters that silently edited three counters would be its own defect one level
up.

| Where | OLD | NEW | Source of the new figure |
|---|---|---|---|
| `.planning/REQUIREMENTS.md` — the `Coverage:` line | `Coverage: 94/94 v0.2 requirements mapped, each to exactly one phase.` | `Coverage: 143/143 v0.2 requirements mapped, each to exactly one phase.` | the strict parse's row count of the traceability table, which is what the counter's own explanatory sentence says it counts |
| `.planning/REQUIREMENTS.md` — the running-total sentence beneath it | `56 rows before Phase 16's minting, 68 after, 82 after Phase 15.5's, 94 after Phase 15.6's.` | the same four totals, extended: `101` after Phase 16's post-stop plans minted `DOCS-19`..`DOCS-25`, `123` after Phase 17's and Phase 18's `CLNT-01`..`CLNT-22`, `133` after Phase 20's `CLNT-23`..`CLNT-32`, `143` after Phase 21's `RECON-01`..`RECON-10` | the strict parse, family by family; each total was re-derived rather than carried, and `133` independently matches the row count at the pinned base |
| `.planning/ROADMAP.md` §Coverage — `All **42** v0.2 requirements mapped` | `42` | **reported, not corrected** — see below | — |
| `.planning/ROADMAP.md:47` — the Phase 21 commissioning bullet | `each of the 52 gets a verdict` | `each of the 54 gets a verdict` | criterion 1's own figure, which the same paragraph already uses two sentences earlier |
| `.planning/ROADMAP.md:47` — the same bullet's lane list | six lanes summing to 52: `21 against Phase 17, 18 against Phase 16, 6 against Phase 14, 3 against Phase 9, 3 against Phase 13, 1 against Phase 18` | eight lanes summing to 54, adding `1 against Phase 15.5, 1 against Phase 15.6` | the strict parse's by-phase breakdown of the 54-member working set |
| `.planning/ROADMAP.md:1888` — the Phase 21 goal line | `every one of the 52 `Pending` requirement rows` | `every one of the 54 not-`Complete` requirement rows` | as above; `not-`Complete`` rather than `Pending` because two of the 54 were never spelled `Pending` — which is the miscount the phase exists to correct |
| `.planning/ROADMAP.md:1890` — the rationale line | `the ledger reads 52 outstanding` | `the ledger reads 54 outstanding` | as above |

### Reported, not corrected: the ROADMAP's `All **42**`

`.planning/ROADMAP.md` §Coverage reads *"All **42** v0.2 requirements mapped,
each to exactly one phase — the figure `.planning/REQUIREMENTS.md`'s
traceability table carries, counted from it rather than remembered."*

**The sentence describes itself two incompatible ways, and the parse cannot
settle which one it means.**

- The first half claims to be the traceability table's row count. That is
  **143** today, and was never 42 — the table held 56 rows even before Phase
  16's minting.
- The two paragraphs immediately beneath it enumerate the figure as **21 + 21**:
  the 21 defined at milestone definition (2026-08-01) plus the 21 minted by
  inserted phases through Phase 15.1. Those two lists are internally consistent
  and sum to exactly 42, and the next line says outright that *"Phase 16 mints
  its own (DOCS-07..NN) at planning and is **not yet counted above**."*

So `42` is a **defined subset**, correctly counted, sitting under a sentence
that mis-describes where it came from. Replacing `42` with `143` would leave the
number contradicting the breakdown one line below it. Replacing the breakdown
means ruling whether the ~101 rows minted since Phase 15.1 belong inside a count
of *"v0.2 requirements"* — a milestone-scope question, not a parse result.

`D-19` constraint (a) governs exactly this case: **a counter the strict parse
cannot settle is reported, not guessed.** It is reported here and left as it
stands. What is needed to close it is one ruling from you: **is "v0.2
requirements" the whole traceability table, or the milestone-definition set plus
what inserted phases minted through 15.1?** Either answer makes the sentence
correctable in a line.

---

## 5. Observations — adjacent, and not this phase's to act on

**1. `DEMO-03`'s re-homing note points at a file that is not in the tree.**
`.planning/REQUIREMENTS.md:59` reads *"Re-homes onto `public/tutorial/hello-ccf.md`,
the narrated Section-1 walkthrough that replaces `demo-walkthrough.md`."*
`public/tutorial/` holds `adopters-guide.md` and `demo-walkthrough.md` only. The
row is ticked and sits **outside the 54**, so it is reported rather than
flipped — `D-19`'s explicit carve-out.

**2. The citation lint has two silent-drop holes and both stay open and named.**
The ambiguous-basename hole (`F-3` / `WR-08`) is not fixed here (`D-07`), and
`21-RESEARCH.md` §4(b) measured a **second hole of the same shape**: a citation
to a path that does not exist at all is also dropped without a finding
(`tally={'unresolved_path': 1}`, zero findings). This phase's own rows are put
out of reach of both from the outside, by a standing check that requires every
cited path to exist exactly as written. The repo-wide surface is untouched:
`git diff` over `tools/lints/citations.py` against the pinned base is empty.

**3. The ten phases with no `D-GATE` entry are ruled and closed.** `D-IMPL-171`
(Dave, 2026-08-21) settled it — phases 9, 10, 11, 12, 13, 13.1, 13.2, 13.3, 14
and 16 are gated by their ROADMAP completion rows and **no gate entry is
backfilled**. This phase did nothing about them beyond not quietly re-opening
the question (`D-14`).

**4. A shipped docstring states a CI fact that is false today.**
`tools/docs_tests/test_resolver_seam_obligations.py:38-41` reads *"`testpaths =
["tests"]`, so `tools/docs_tests` runs as its own CI step and **not** under
`make ci-core`."* `Makefile:138` reads `ci-core: lint typecheck test
gate-tools`, and `gate-tools` runs `tools/docs_tests` — a change made
deliberately in Phase 17 after three waves shipped past a red gate. The
docstring's own stated purpose is to stop a reader believing the gate ran when
it did not, and it now produces the opposite belief. Reported; fixing it is
outside this phase.

**5. Two `Complete` rows are true today and guarded by nothing, and they say
so in their own cells.** `DOCS-06` and `DOCS-08` both turn on the `ci` target
containing the docs and gate suites. It does — `ci` is `ci-core examples
docs-strict gate-tools`, and `gate-tools` runs `tools/publish_scan_tests` and
`tools/docs_tests` — so the verdict is right. But **no test in this tree reads
the `ci` target's composition or the workflow**, so the *always-on* limb is
true by inspection and would not go red if a later edit dropped a suite. Both
cells name the gap; `CLNT-16` carries a third instance, where its *"before any
example tree moves"* limb is simply not yet under load.

Why it is here rather than in §2: it is not a `Not built` row and not an owed
half of a `Partial`. It is a **guard** that is missing behind three verdicts
that are otherwise correct. It cannot be closed from inside an audit — the
`Makefile` has no suffix and is invisible to the citation lint by construction
(the same shape as observation 2 and as the stale `Makefile` pointer in
`deferred-items.md`), so closing it means writing a test that reads the
`Makefile`, which is building. **Added at the phase close**: plan `21-03`
identified this and handed it to plan `21-05`, and it reached the ledger cells
but not this document. The §3.1 panel found it from the other end — two
reviewers reading the cells and asking what guards them. *A gap named in a
hand-off and absent from the document Dave rules from is the ledger-debt
pattern this phase exists over, one level up.*

---

*Written 2026-08-22 by plan `21-05`. Every count in this document was produced
by running the strict parse at the time of writing. §5 observation 5 was added
at the phase close by plan `21-07`, as a blocking finding from the CLAUDE.md
§3.1 review; nothing else in this document changed.*
