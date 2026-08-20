---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
plan: 08
subsystem: decision log / requirement lane / client design spec / phase-18 review record
tags: [C-01..C-18, D-IMPL-156, D-IMPL-157, D-IMPL-158, D-IMPL-159, D-IMPL-160, D-IMPL-161, amend-never-delete, B0-closed]
requires:
  - "src/ccf/client/codec.py — the narrower true claim 19-07 shipped, quoted verbatim here"
  - "docs/DECISIONS.md — D-IMPL-151 (the B0 deferral) and D-GATE-18 (the reservation)"
  - "docs/superpowers/specs/2026-08-15-ccf-client-design.md — Amendment 1's form"
provides:
  - "docs/DECISIONS.md — D-IMPL-156..D-IMPL-161, six appended entries"
  - ".planning/REQUIREMENTS.md — CLNT-05 amended beside its original"
  - "docs/superpowers/specs/2026-08-15-ccf-client-design.md — Amendment 2"
  - ".planning/phases/18-*/18-CLOSE-REVIEWS.md — B0 closed by appending, A5 still open"
affects:
  - "D-GATE-19 (Dave's, at the gate — deliberately NOT written here)"
  - "the next change touching ccf.client.client (D-IMPL-157 rules _result_from's `sent` goes)"
  - "a later tools/errors pass (D-IMPL-156 defers `product-asked-at-naive`)"
  - "a later phase (D-IMPL-159 — move the as_of=None clock producer-side)"
tech-stack:
  added: []
  patterns:
    - "record the MEASURED outcome, never the plan's prediction — this phase is named after that defect"
    - "state a residual two-sidedly in the same paragraph, so neither half can be quoted alone"
    - "leave a superseded status marker visible and append the closure beneath it"
    - "mint a divergence between written law and three phases' practice rather than inherit it invisibly"
key-files:
  created: []
  modified:
    - "docs/DECISIONS.md"
    - ".planning/REQUIREMENTS.md"
    - "docs/superpowers/specs/2026-08-15-ccf-client-design.md"
    - ".planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/18-CLOSE-REVIEWS.md"
    - ".planning/ROADMAP.md"
decisions:
  - "SIX entries, not the plan's five: D-IMPL-161 records Phase 19 landing on `main` against CLAUDE.md §2.2, per the orchestrator's explicit direction that an undocumented divergence between written law and three phases' practice is the drift this phase exists to correct"
  - "The three carried rulings are dispositioned INSIDE the entries their cause belongs to rather than in a sixth ruling entry — `sent` and the TransportError drop in D-IMPL-157 (both are C-05's consequences), the error code in D-IMPL-156 beside C-09 (it is C-09's own measured consequence)"
  - "The ROADMAP citation became a SYMBOL rather than a corrected line number: `client.py` is an ambiguous basename the citation lint DROPS, which is why a number stale on arrival survived three phases green"
metrics:
  duration: "~2h30m"
  tasks: 3
  commits: 3
  collected_delta: "4099 -> 4099 (+0)"
  completed: 2026-08-20
---

# Phase 19 Plan 08: The Rulings Go Where a Future Reader Will Find Them — Summary

Put the phase's eighteen rulings, both wire-compatibility breaks, one deferred
defect and one accepted cost into the decision log; amended the requirement and
the spec beside their originals rather than over them; and closed `B0` in the
Phase 18 review file with `A5` still visibly open — deleting nothing, and
changing no code, so `make ci` came back at exactly the number it started at.

## What Was Written

**Six `D-IMPL` entries, appended.** The plan specified five. The sixth
(`D-IMPL-161`) records the branch divergence, per the orchestrator's explicit
direction; it is the one deviation from the plan's own count and it is
argued below.

| Id | What it rules | Status |
|----|---------------|--------|
| `D-IMPL-156` | Ratification of `C-01`…`C-18`, each with its **rejected alternatives**; `D-IMPL-151` finding `B0` **CLOSED** on the axes measured; the narrower true claim quoted verbatim with its four undetected cases; the reused-error-code ruling | RESOLVED |
| `D-IMPL-157` | `ask(WireRequest) -> bytes` — **amends `D-11` and `CLNT-05`**; disposes the `_result_from`/`sent` and `TransportError` carried rulings | RESOLVED |
| `D-IMPL-158` | **Both** wire-compatibility breaks, one entry, **no deprecation window**; the door's three-axis cross-check including `C-18`'s temporal axis | RESOLVED |
| `D-IMPL-159` | `C-15`'s client-side clock — a **deferral**; the defect is **OPEN**, not accepted; `C-18`'s `as_of=None` residual stated in both directions | RESOLVED as a deferral / defect **OPEN** |
| `D-IMPL-160` | `C-14`'s two extra in-process serializations, **accepted with no benchmark owed** | RESOLVED — ACCEPTED COST |
| `D-IMPL-161` | Phase 19 landed on `main` with no phase branch — diverges from CLAUDE.md §2.2, matches Phases 18 and 18.1 | RESOLVED |

**`CLNT-05`, amended beside its original.** The `-> WireOutcome` sentence is
kept verbatim; the amending clause states the `-> bytes` signature, names
`D-IMPL-157`, gives the reason in one clause, and says plainly that `D-11` is
**amended, not withdrawn** — which is why the original's `D-11` citation stands.

**The client design spec's Amendment 2**, appended at the end in Amendment 1's
exact form (H1 dated heading, `**Status:**`/`**Effect:**` block, a *why this
amendment exists* section with a measured table, lettered sections **A**–**C**,
an effect table, and *What did not change*). §5 and Amendment 1 are unedited.

**`B0` closed by appending.** The closure note sits immediately beneath `B0`'s
existing `⚠ STATUS: DEFERRED` blockquote, which is deliberately left standing.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Six `D-IMPL` entries, appended | `50934da` | `docs/DECISIONS.md` |
| 2 | Amend `CLNT-05` and the client design spec | `deb2bb0` | `.planning/REQUIREMENTS.md`, `docs/superpowers/specs/2026-08-15-ccf-client-design.md` |
| 3 | Close `B0`, fix the ROADMAP's stale citation | `8c4c873` | `18-CLOSE-REVIEWS.md`, `.planning/ROADMAP.md` |

## The Verified Base Id, and the Six Ids Used

`19-RESEARCH.md` §9.3 measured the next free id as **`D-IMPL-156`**. **Confirmed
against the file before writing**, not inherited:
`grep -oE "D-IMPL-1[0-9]{2}" docs/DECISIONS.md | sort -u | tail` ends at
**`D-IMPL-155`**, and `D-GATE-18.1` is the final entry at line 470. The base id
had **not** moved, so no shift was needed. Ids used: **156, 157, 158, 159, 160,
161** — contiguous, ascending, no gap:

```
**D-IMPL-156
**D-IMPL-157
**D-IMPL-158
**D-IMPL-159
**D-IMPL-160
**D-IMPL-161
```

## The `C-01`…`C-18` Coverage Loop, Run and Pasted

The plan's criterion, run against the file and producing the required empty
output:

```
$ for c in $(seq -w 1 18); do grep -qc "C-$c" docs/DECISIONS.md || echo "MISSING C-$c"; done
$
```

**That loop is too weak on its own** — `C-16` matches inside any other token
ending in those characters, and the whole file is in scope, so a pre-existing
mention would satisfy it. It was therefore re-run **restricted to the six new
entries** and **on the backticked form**, which is the stricter measurement:

| | count | | count | | count |
|---|---|---|---|---|---|
| `C-01` | 3 | `C-07` | 3 | `C-13` | 4 |
| `C-02` | 2 | `C-08` | 4 | `C-14` | 4 |
| `C-03` | 5 | `C-09` | 2 | `C-15` | 6 |
| `C-04` | 2 | `C-10` | 6 | `C-16` | 6 |
| `C-05` | 5 | `C-11` | 1 | `C-17` | 3 |
| `C-06` | 1 | `C-12` | 2 | `C-18` | **14** |

**`C-18` was checked by eye as well**, per the plan's instruction: it was ruled
*after* the plans were written and is the decision most likely to be dropped by
a writer working from the original discussion log. It appears in the
ratification entry with **both** of its rejected alternatives, in `D-IMPL-158`
as the shipped cross-check with its measured sabotage evidence, and in
`D-IMPL-159` as the residual — stated in both directions.

## Every Acceptance Criterion, Measured

| Criterion | Required | Measured |
|---|---|---|
| `git diff --numstat docs/DECISIONS.md` | 0 deletions | **12 / 0** |
| first 470 lines byte-identical to the pre-edit backup | yes | **`diff` empty** |
| `grep -c "Rejected" docs/DECISIONS.md` | +5 or more | **16 → 21 (+5)** |
| `grep -c "D-GATE-19" docs/DECISIONS.md` | 0 | **0** |
| the `C-15` entry marked open, not resolved | explicit marker | `RESOLVED as a **deferral**; the underlying defect is **OPEN**, not accepted` |
| the same entry's `as_of=None` count | ≥ 1 | **4** |
| the same entry says a concrete `as_of` **is** cross-checked | yes | *"on the concrete path the door cross-checks the two copies and refuses a disagreement by name"* |
| `git diff --numstat` spec | 0 deletions | **133 / 0** |
| `grep -c "^# Amendment"` spec | 2 | **2** (Amendment 1 is `#`, not `##` — the plan's `^## Amendment` pattern would have returned 1 for a correct implementation) |
| Amendment 2 names `D-10`/`D-11`/`D-12`/`D-13`/`D-15`/`D-28` | ≥ 6 | **10** |
| `grep -c "WireOutcome"` REQUIREMENTS | ≥ 1 | **1** (the kept original) |
| `grep -c "\-> bytes"` REQUIREMENTS | ≥ 1 | **1** |
| `CLNT-05` names the amending id | yes | `D-IMPL-157`, on line 201 |
| REQUIREMENTS numstat | deletions only where a line grew | **1 / 1** — line 201 only; every other line `diff`-identical to backup |
| `18-CLOSE-REVIEWS.md` numstat | insertions only | **40 / 0** |
| ROADMAP Progress table | unchanged | **0** table lines in the diff |
| `.planning/STATE.md` | untouched | **not in `git diff --name-only cdb6337`** |
| `make lint` | exit 0 | **exit 0**, after each of the three tasks |
| **`make ci`** | exit 0 | **exit 0** — 3981 passed / 118 skipped / **0 failed**; 400 lint-tool; 154 gate-tools; nine examples; `mkdocs build --strict` green |

**No `state.*` or `roadmap.*` SDK writer was invoked.** Stated explicitly, as
the plan requires. Every one of the five files was hand-edited; all three
tracked-record files (`docs/DECISIONS.md`, `.planning/REQUIREMENTS.md`,
`.planning/ROADMAP.md`) were **backed up before the first edit** and `diff`ed
against the backup afterwards, line-count deltas checked against the intended
change: DECISIONS 470 → 482 (+12, six entries × two lines), REQUIREMENTS 523 →
523 (one line replaced), ROADMAP 1731 → 1743 (+12, the note plus its reflow).

## The Narrower True Claim — the Two Records Agree, Checked Mechanically

The plan asked for an eye diff. It was done **by string comparison** instead,
whitespace-flattened with RST emphasis normalised, because an eye diff of a
paragraph is exactly the check this phase is named after:

```
the replacement sentence   in codec.py : True    in DECISIONS: True
condition 1 "corruption"                 codec=True  dec=True
condition 2 "truncation"                 codec=True  dec=True
condition 3 "mis-routing that swaps…"    codec=True  dec=True
condition 4 "a re-serializing interm…"   codec=True  dec=True
condition 5 "producer/consumer canon…"   codec=True  dec=True
```

**The four-item undetected count agrees between the two records**, which the
plan named as the place a disagreement would be found: `codec.py`'s numbered
list is `['1. ', '2. ', '3. ', '4. ']` and `D-IMPL-156`'s markers are
`['1', '2', '3', '4']`. The entry also says *"four rather than three"* in terms,
so a later reader who counts three knows one has gone missing.

## The Traceability-Table Reading

**Confirmed: no Phase 19 row is needed, and none was added.**
`19-RESEARCH.md`'s measurement was checked rather than inherited. The table's
rows are `| <REQ-ID> | <phase of origin> | <status> |`, and Phase 19 **minted no
requirement IDs** — the plan's own frontmatter carries `CLNT-05` and `CLNT-12`,
both pre-existing Phase 17 rows. Measured: `grep -cE "\| *[A-Z]+-[0-9]+ *\|
*Phase 19"` returns **0** and `grep -c "Phase 19"` over the whole file returns
**0**.

**`CLNT-05` and `CLNT-12` were left at `Pending` and their status was not
changed.** Stated because the omission is deliberate rather than forgotten: the
`CLNT` lane's completion is a gate-time judgement Dave makes, this plan's scope
is the *amendment* and not the *status*, and `gsd-sdk query
requirements.mark-complete` is a `.planning`-writer of the class MEMORY records
as destructive on this repo. If the rows should move at `D-GATE-19`, they move
by hand there.

## The ROADMAP Citation — Measured, and Then Replaced With a Symbol

The `grep -n` output the plan asked to be pasted beside the number written:

```
$ grep -n "return self._result_from\|decode_outcome(self._adapter.ask" src/ccf/client/client.py
228:        return self._result_from(
229:            decode_outcome(self._adapter.ask(request), sent=request), sent=request
```

**The seam call is at line 228.** The ROADMAP cited `client.py:172`.

**The correction is a symbol, not the measured number**, and that is a
deliberate departure from the plan's literal instruction. Three reasons, all
stated in the ROADMAP's own voice in the appended note:

1. `D-IMPL-114` already rules that prose cites `path.py::Symbol`, precisely
   because a line anchor is wrong the moment code moves — and this one was
   **wrong on arrival**: `19-RESEARCH.md` §9.3 measured the true line as `:186`
   at the phase's base, and `19-02` moved it again. Writing `:228` would have
   been the same defect with a fresher number, in a phase whose five prior
   waves each recorded stale line citations in their own plans.
2. The paragraph is a description of the defect **as it was**, and that defect
   is closed. The note says so, and names the entries that closed it.
3. `client.py` is an **ambiguous basename**, so the citation lint *drops* the
   pointer rather than checking it. That is why a number stale on arrival
   survived three phases with every gate green — and it is now recorded in the
   ROADMAP rather than only here. The symbol form `src/ccf/client/client.py::ProductClient`
   is unambiguous and **is** checked; `make lint` exits 0 with it in place.

The literal string `client.py:172` still appears **once** in the file — inside
the correction note, where it is quoted as the value corrected from. That is
amend-never-delete, not a missed replacement.

## `B0` Closed, `A5` Open — and the One Criterion That Could Not Hold

The closure note names the ratifying entries, states what closed it in one
sentence (producer-minted echo and address, a bytes seam with nothing to
construct, and **single-transport** controls rather than a parity diff), lists
the **four** cases still not covered in `C-10`'s terms, records that
`D-GATE-18`'s prose constraint is **replaced not lifted**, and says in terms
that **`A5` is still open and was not touched**, and that the other nine
carried advisories (`A1`–`A4`, `A6`–`A10`) are unaffected.

**The `⚠ STATUS: DEFERRED` marker was left standing**, per the plan's own
fallback: this file has **no closed form** of that marker (`grep -niE "^> ?#+
?(✅|CLOSED|RESOLVED)"` returns nothing), so rewriting the verdict would have
produced a record reading as though `B0` had never been open. The note's own
first line says why the marker stays.

**A criterion that a correct implementation cannot satisfy, reported rather
than worked around.** The plan requires *both* that `grep -c "A5"` be
**unchanged** *and* that the closure note **name `A5`** as untouched. Those are
in direct conflict: the count moved **2 → 3**, and the third occurrence is the
sentence the plan's own action text demanded. The substantive requirement —
`A5` visibly open, named as untouched, its original advisory entry unedited —
is met, and both pre-existing occurrences are byte-identical. This is the same
defective-criterion shape `19-07` reported and `19-02` inverted into a guard,
and it is the sixth consecutive plan in this phase to hit one.

## The Three Carried Rulings, Each Dispositioned

They are recorded **inside the entries whose ruling caused them** rather than
collected into a sixth entry, because a carried item filed away from its cause
is how it becomes invisible again.

**1. `ProductClient._result_from`'s `sent` parameter — `D-IMPL-157`. RULED: it
goes; ADVISORY, DEFERRED; explicitly not accepted as it stands.** Nothing in
the body reads it once the echo cross-check moved into `decode_outcome`. It is
the *"a member nothing sets and nothing reads"* shape `C-10` names, one scope
over — private, invisible to `mypy --strict` and to every lint, and therefore
exactly the residual that survives by being nobody's job. **The removal is not
made here** because this plan changes no code by its own scope statement and
moving a signature inside a documentation plan is the accretion `D-IMPL-146`
governs. The interim record is the `Args:` paragraph `19-07` wrote (commit
`a4d069b`), which states plainly that the body does not read it. The next change
touching `ccf.client.client` removes it. The alternative — keeping it with the
reason written — was weighed and rejected: the only argument for keeping is
that a future assertion at the construction site *might* want the question in
scope, which is speculative generality and is the same shape.

**2. A dedicated `product-asked-at-naive` error code — `D-IMPL-156`, beside
`C-09`. RULED: the reuse stands; a dedicated code is ADVISORY and DEFERRED.**
Verified against the tree rather than taken from `19-06`'s note:
`ERROR_PRODUCT_REQUEST_INCOMPLETE`'s own recorded meaning is *"a defaulted axis
is a question nobody asked, answered anyway, so the door refuses the partial
address rather than filling one in"*, and the refusal it now carries is an axis
supplied **without the offset that makes it unambiguous** — genuinely the same
condition. The refusal's message carries the guard's own wording, so the caller
is told the spelling that works rather than only *"malformed"*. A dedicated code
would read better and is strictly cosmetic on a message that is already correct;
it is not worth a wire-visible error-code addition inside this phase, and it
belongs to whatever later pass touches `runtime/ccf_runtime/http_api/errors.py`.

**3. `TransportError` dropped from `inprocess.py` — `D-IMPL-157`. CONFIRMED:
the drop STANDS, NO ACTION.** Re-verified independently rather than taken from
`19-07`'s reading: `grep -n "TransportError" src/ccf/client/adapters/inprocess.py`
returns **one** line, a prose cross-reference at `:365` saying `BindingError` is
*"a `TransportError` by inheritance"* — true and correct. The name is **not
imported**; `BindingError` is still imported and used, so `D-10`'s catch-all is
intact; and no in-tree test asserted the deleted raise's wording. `19-07`'s
judgement is upheld.

## The Branch Ruling — and Why It Is a Sixth Entry

**`D-IMPL-161`.** Phase 19 landed directly on `main` with no phase branch. Dave
ruled this explicitly on 2026-08-19 when `19-01`'s SUMMARY stopped and asked:
there are no SDK consumers, so `main` carrying un-gated phase work costs nothing
a branch would protect, and git history still permits carving a branch
retroactively.

This **diverges from CLAUDE.md §2.2** and **matches what Phases 18 and 18.1
actually did** — `D-GATE-18.1` already records *"No merge is required — the work
landed on `main`"*, and `.planning/config.json` carries
`git.branching_strategy: "none"`, which is the mechanical reason no executor
ever had a branch to be on. The entry records the divergence and the ruling; it
deliberately does **not** amend CLAUDE.md, which is Dave's document, and does
**not** rule the general case. It names the two acceptable resolutions (bring
§2.2 into line with the practice, or bring the practice back into line with
§2.2) and states that leaving both as they are is the one outcome the entry
exists to prevent.

**Why a sixth entry rather than a clause in an existing one.** None of the five
planned entries is about process governance, and folding a branch ruling into
the ratification of a wire-shape repair is how a ruling stops being findable.
The plan's *"five entries"* count is therefore exceeded by one, deliberately and
at the orchestrator's explicit direction. The contiguity criterion still holds:
156–161, ascending, no gap.

## Where the Plan Was Measurably Wrong

Recorded because every prior wave in this phase found its own plan wrong, and a
SUMMARY that records the plan's prediction instead of the measurement is the
defect this phase is named after.

**1. `grep -c "^## Amendment"` returns 2 only for an incorrect implementation.**
Amendment 1's heading is `# Amendment 1 — 2026-08-15 (post-research)` — an
**H1**. The only `^## Amendment` in the file is `## Amendment 1 addendum`, so at
base the count was **1**, and an Amendment 2 written at H2 (satisfying the
criterion) would *not* mirror Amendment 1's structure, which the same criterion
demands. The plan anticipated this in parentheses — *"adjust for the actual
heading level used"* — and Amendment 2 is an **H1**. `grep -c "^# Amendment"` is
**2**.

**2. The plan's `<read_first>` line citations were stale — the sixth consecutive
plan in this phase to record it.** `.planning/REQUIREMENTS.md:341-362` for the
traceability table is `:329-358`; the spec's `:290+` for Amendment 1 is `:286+`
and its effect table is at `:394`, not `:401`; `18-CLOSE-REVIEWS.md:195-205` for
`A5` is `:195-210` and `:56-82` for `B0`'s block runs to `:110`. Every **symbol
and section name** was correct and was what found the text. `D-IMPL-114` rules
that prose cites `path.py::Symbol` for exactly this reason, and a plan citing
line ranges is the same defect one document over.

**3. `docs/DECISIONS.md` has no headings for entries at all.** The plan's
criterion says *"shows five **headings** in ascending order"*; the file's format
is one entry per **paragraph line**, opening `**D-IMPL-NNN — …**`, with
`## Open Decisions (D-IMPL)` and `## Gate Log (D-GATE)` the only two headings
after the title. The substantive check — six ids, ascending, contiguous — was
run against the opening bold markers and is pasted above.

**4. The plan's `Rejected` criterion is satisfiable without any of the eighteen
rulings carrying a rejected alternative.** `grep -c "Rejected"` counts *lines*,
and the file is one line per entry, so six entries each containing the word once
would move the count by six. The +5 measured is therefore **not** the evidence;
the evidence is that **thirteen of the eighteen rulings carry an explicit
`*Rejected:*` clause naming what was declined and why**, and the five that do
not (`C-05`, `C-08`, `C-10`, `C-14`, `C-15`, `C-16` — five *entries*, since
`C-05`/`C-08` and `C-16`/`C-18` pair) carry theirs in their own dedicated
entries instead. Counted by reading, not by grep.

## What Was Deliberately Not Done

- **`D-GATE-19` was not written.** It is Dave's ruling at the phase gate per
  CLAUDE.md §3.1 step 4, and writing it in advance would record an approval that
  has not happened. `grep -c "D-GATE-19" docs/DECISIONS.md` is **0**.
- **The ROADMAP Progress table was not touched**, and the Phase 19 row was not
  added. Close-time.
- **`.planning/STATE.md` was not touched at all.** The orchestrator owns it.
  Confirmed by `git diff --name-only cdb6337`.
- **Plan `19-08`'s own checkbox in the ROADMAP Plans list was not checked**, nor
  were `19-01`…`19-07`'s re-touched. The orchestrator's.
- **No code, test or `src`/`runtime`/`examples` prose was changed.** `make ci`
  returns **3981 passed**, the identical figure `19-03` and `19-07` measured;
  the collected count is unchanged at **4099**. For a documentation plan that is
  the load-bearing check: had either moved, something other than documentation
  had changed.
- **No `state.*` or `roadmap.*` SDK writer was invoked**, and no `gsd-sdk`
  writer of any kind touched a tracking file.
- **No surface fragment was filed and no generated record regenerated.** This
  plan adds no public name and shifted no swept citation line; `make ci` green
  confirms rather than assumes it.

## Known Stubs

None. Every entry states a ruling that is in force, every cross-reference
resolves, and nothing was reserved for a later filling-in. The three items this
plan *defers* — the `sent` parameter, the dedicated error code, and the
producer-side clock — are each recorded as a named ruling with a named owner,
not as a placeholder.

## Threat Flags

None beyond the plan's own `<threat_model>`. `T-19-26` is mitigated —
`D-IMPL-158` rules both breaks in one entry with the no-window reasoning stated,
and the adopter-facing migration records exist in `docs/surface-changes/`.
`T-19-27` is mitigated — `D-IMPL-159` marks the clock defect **open**, in
`D-IMPL-151`'s own register, with its integrity cost priced. `T-19-28` is
mitigated and **measured**: `git diff --numstat docs/DECISIONS.md` reports
**0 deletions** and the first 470 lines are byte-identical to a pre-edit backup.
`T-19-29` is mitigated — the closure note states `A5` and the other nine
advisories remain open, in its own paragraph. `T-19-SC` holds: this plan
installed no package and added no dependency.

## Self-Check: PASSED

Modified files, all present:
- FOUND: `docs/DECISIONS.md`
- FOUND: `.planning/REQUIREMENTS.md`
- FOUND: `docs/superpowers/specs/2026-08-15-ccf-client-design.md`
- FOUND: `.planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/18-CLOSE-REVIEWS.md`
- FOUND: `.planning/ROADMAP.md`

Commits (all present in `git log`):
- FOUND: `50934da` `docs(19-08): six D-IMPL entries ratifying C-01..C-18, both wire breaks, the deferred clock and the accepted cost`
- FOUND: `deb2bb0` `docs(19-08): amend CLNT-05 beside its original, and append the spec's Amendment 2`
- FOUND: `8c4c873` `docs(19-08): close B0 in the Phase 18 review file by appending, and fix the ROADMAP's stale citation`

Artifacts and key links (all matched):
- `docs/DECISIONS.md` → `D-IMPL-156` — present, plus 157–161
- `.planning/REQUIREMENTS.md` → `-> bytes` — 1 match, on `CLNT-05`'s line
- `.planning/REQUIREMENTS.md` → `D-IMPL-1` — `D-IMPL-157` named on `CLNT-05`'s line
- `docs/superpowers/specs/2026-08-15-ccf-client-design.md` → `Amendment 2` — present as an H1, citing `D-IMPL-156` and `D-IMPL-157`
