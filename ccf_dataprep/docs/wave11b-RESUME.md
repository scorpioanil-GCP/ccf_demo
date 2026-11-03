# Wave 11b — the record of a finished wave

> **SUPERSEDED as a resume note, 2026-08-21.** This file was written to carry
> Wave 11b across a context clear while the work was unmerged. **Wave 11b is
> merged to `main` at `acbe45b` and pushed**, and Wave 11c (consolidation) is
> merged at `c19d126`. The header below said *"`main` is still at `b33a7c5`.
> Wave 11b is NOT merged"* — true when written, false now, and it contradicted
> this file's own §"one open decision" further down.
>
> **To resume work, read `docs/HANDOFF.md`, not this file.** What is still
> worth reading here is the account of *why* the binding verifier took three
> attempts, and the third-WARN-state reasoning — both are history now, not
> state.

**Written:** 2026-08-21 06:30 MST · Branch `wave11b-early-warning` @ `c59a5c8`

**Read next:** `.superpowers/sdd/wave11b-plan/progress.md` — the SDD execution ledger,
IF it still exists. It holds all 19 rulings with cost-if-wrong, every deferred minor,
and every commit range. It is **gitignored and deleted at wave close**: treat it as
gone, and read `docs/known-issues.md` §10 (Wave 11b defects) plus this file's own
sections instead — they are the tracked, durable half.
This file is tracked, so it carries the half that must not be losable.

---

## Status: COMPLETE. All reviews closed.

All 13 tasks implemented and individually reviewed. The whole-branch final
review returned NOT READY on one Critical; a fix wave closed seven of its
eight items, and the scoped re-review found the Critical still open — a
**gate bypass** in the binding verifier. Two further bounded fixes closed it.

**Nothing is outstanding.** The one user decision below is resolved, and the
branch was merged to `main` on 2026-08-21.

### The Critical, and why it took three fixes

`verify_fibo_wave11b_confirm.py` exists to fail when a new `ex:` term asserts
data with no binding-contract row — CLAUDE.md's named silent-and-expensive
failure. It had **three** holes, each found only by attacking it:

1. **Raw-text substring** — blind to any term whose local name is a common
   English word. `ex:item` (535 assertions) passed as "bound" because the word
   *item* appears in prose.
2. **Tightened to backticks/IRI** — fooled by its own author writing
   `` `unit` `` in a code span while documenting it.
3. **IRI anchored** — still passed anything whose name was a *prefix* of a
   bound term. `ex:trigger` (245 live assertions, no row) read as bound off
   `triggeredBy`. And the **gate** still accepted `mention` as bound, so
   injecting `ex:signal` exited 0.

Final state, verified by attacking it four ways myself:

```
no injection (real estate)   exit=0   <- 45 pre-existing debt terms tolerated
ex:signal injected           exit=1   <- prefix of a bound term
ex:source injected           exit=1   <- mention-only elsewhere in the doc
ex:zzzBogus injected         exit=1   <- genuinely novel
```

**The carried lesson is not "anchor your regex."** Every generation of this
check was verified by someone, and every verification used an input the
mechanism handled well. A guard must be attacked with the input its designer
would not think of, by someone who did not design it.

## Estate state — verify in 60 seconds

```bash
uv run validators/partition.py                  # 19/19
uv run validators/conditions.py                 # 91 passed · 0 failed
uv run validators/surveillance.py               # PASS — SIX claims
uv run validators/series.py                     # PASS
uv run validators/traversal.py                  # 5 clients over limit
uv run validators/bitemporal.py                 # 3/3 diverge
uv run validators/projection.py                 # exit 0
uv run validators/artifact_reproduces_store.py  # 54/56 (2 = pre-existing Wave 10 dupes)
uv run generators/verify_fibo_wave11b_confirm.py
uv run validators/binding_drift.py              # 11 agree · 29 disagree
```
11 pure-function suites, **279 cases**, all green.

## What is loaded

| Store | Contents |
|---|---|
| Postgres `ccf_v2` | 7 new tables — `warn_notice` 3,514 · `warn_match` 36 (4 resolved / 3 obligors, **32 ambiguous retained**) · `gdelt_mention` 951 · `signal_event` 1,603 (13 engineered) · `signal_weight` 45 (now with `decay_days`) · `escalation_threshold` 6 · `trend_delta` 3,705 |
| Fluree `fibo-v2` | 38,582 triples · 538 `ex:WarningSignal` · 409 `ex:SignalSource` · 50 `ex:PriorObservation` · 750 `ex:supersededBy` (215 Wave 11a's, untouched) |

Sources: 534 8-K item events (6 types, 24-month window) · 3,514 WARN notices
(TX Socrata + CA XLSX/PDF) · 951 GDELT adverse-media mentions · 3,705 XBRL
trend deltas. Two engineered conditions: the Avis Budget cascade and the
Bausch Health composite case.

---

## ✅ The one open decision — resolved 2026-08-21

**Ruling 8 deviated from an explicit user decision (D2). The user chose to
defer it, not ratify it:** two states stand for Wave 11b, and **adding a third
WARN state is a scheduled task for the next wave that touches WARN.** D2 was
postponed, not overruled. Entry conditions and the success test — a resolved
obligor from a **non-CA-PDF** leg, not merely a third state loaded — are in
`known-issues.md` §10.3.

The record of why it mattered follows. D2 chose "TX + CA + one more state"; I dropped
the third state because §F's ≥3 floor was met and no further state was reachable
at proportionate cost (CO/MI 403; WA/VA/NY are JS portals; NJ/OH/FL/IL ruled out
at design time).

The final reviewer's verdict, sharper than mine and worth quoting:

> D2's stated purpose was margin above the floor; the delivered margin is
> **exactly zero** on a **single source leg** — the CA PDF path, not merely
> "California". So D2's objective was not partially achieved, it was not
> achieved.

All three resolved obligors (Charter, Quanex, Bausch Health) come from the
**CA PDF extraction leg specifically** — 2,963 rows via `pdftotext -layout`,
the single riskiest path in the wave, where Task 3 already found and fixed a
real 16-row parse defect. The CA XLSX leg (136 rows) and all 415 TX rows
contribute zero.

Overturning it in-wave changed no §F verdict and could not be executed under
the no-network constraint, which is why the decision became a scheduled item
rather than a fix.

## Carried debt — none blocks this wave

- **`known-issues.md` §10.7 — the binding-contract debt is 45 rows.**
  Only **22 of 67** asserted `ex:` terms have a real full-IRI row; 12 more are
  code-span mentions only. All 45 are frozen in `KNOWN_UNBOUND`, so a genuinely
  new unbound term fails the gate rather than joining the pile. Found because the fix wave's tightened verifier
  caught its own author writing `` `unit` `` in a code span. Wants its own task.
- **`load_fluree_wave10.py`** carries a dormant blind-scan `--reconcile` over
  six predicates. Verified genuinely dormant (no other writer asserts them).
  First thing to fix next time Fluree is edited.
- **`ex:grade`** is arguably the same shape as `ex:item` but was deliberately
  left as Wave 11a's row — re-scoping another wave's decision under a Wave 11b
  heading is how the register drifted originally.
- Ten deferred minors, all dispositioned in `known-issues.md` §10.9, plus M1–M6
  from the final review. All carry.
- 🔴 **Five API keys exposed 2026-08-17, still unrotated** — user deferred.

## Vault

Punch list **amended in place** at
`~/.agent-exchange/ccf-dataprep/outbox/2026-08-21T12-12-56Z-wave11b-drift`
(six terms after `ex:item` was bound). Still uncollected; `inbox/` empty.
Wave 10's and Wave 11a's lists remain delivered and awaiting application —
**do not re-send either.**

---

## The lesson this wave actually taught

The failure this project guards against is a large, plausible, silently wrong
*dataset*. What Wave 11b kept producing was a **correct dataset with a silently
wrong account of itself** — five times:

1. Task 7's Table 4 claimed both upgrade crossings produced "correctly none"
   for anticipation. Both produced two rows.
2. Task 10's docstring claimed `--reconcile` covered the artifact-regenerated
   case. It covered edges only.
3. Task 11's note claimed a `provenance='public'` filter excluded the engineered
   cascade. Nothing in Postgres needed excluding.
4. A stale "Avis Budget" claim propagated from my design doc into the plan and
   survived thirteen briefs and twenty reviews.
5. `verify_fibo_wave11b_confirm.py` — the guard built to catch unbound terms —
   reported a false green because it matched against raw document text, so
   `ex:item` passed as "bound" because the word *item* appears in prose.

Every one was caught by testing the **claim**, not the code. Counting never
would have found any of them. Corrections in this wave state what they
previously claimed rather than quietly rewording; that convention is the only
reason the reasoning is auditable.
