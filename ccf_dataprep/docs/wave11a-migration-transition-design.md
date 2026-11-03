# Wave 11a follow-on design — the migration transition

**Written:** 2026-08-20 · **Status:** implemented 2026-08-20
**Fixes:** `known-issues.md` §9.10 · **Stores:** Postgres only (`spread_observation`)

> This is a corrective design against `docs/wave11a-design.md` §2, not a new
> product. It changes how the composed spread responds to a rating-band
> migration. No §C element is added and no §F condition changes.

---

## 0 · Decisions taken

| # | Question | Decision |
|---|---|---|
| 1 | Fix now, or defer to Wave 11b as originally ruled? | **Fix now.** Nothing outside Wave 11a's own validators consumes the spread series yet; that stops being true the moment 11b builds on it |
| 2 | How should the market leg follow the grade? | **It steps to the in-force band, and the transition is carried by the engineered leg** — not by blending two index series |
| 3 | How much is anticipated by announcement? | **Varies across obligors:** 0.30 / 0.60 / 0.90 |
| 4 | Does lead time vary too? | **Yes, deliberately uncorrelated with strength** — 110 / 40 / 75 trading days |
| 5 | Which date is the migration date? | **`asserted_at`** (announcement), not `valid_from` |
| 6 | Are the migrations declared, or discovered? | **Discovered** from the grade chains. Only the *response* is declared |

---

## 1 · The defect, and why it was not a Wave 11b problem

`generators/generate_spreads.py:360` selects `oas[band][d]` where `band` is
`debt_instrument.rating_band`, fixed when the instrument is generated.
`generate_grades.py` then lets an obligor's grade drift across band boundaries
over the same window. The market leg never notices.

Measured: **3 of 30 obligors, 4 crossings, 6 of 60 instruments.**

The module docstring of the very file that contains the defect states the
product's central claim:

> the product's central claim ("the market anticipates the grade")

For those three obligors the market does not anticipate the grade. It does not
follow it either. The original ruling — document, defer to 11b — was defensible
while the cost sat in the future; it is cheaper to pay now, and the ruling is
superseded.

**No §F condition fails**, then or now. None of the seven
`rating-and-spread-migration` conditions requires a band crossing; "divergence
later confirmed by a worse rerating" is satisfied by a notch move. This is a
workmanship defect, not a contract breach, which is why it lands in
`series.py` and not in `conditions.py`.

---

## 2 · The narrative module

New: `generators/narrative_wave11a.py`, imported by both generators.

### 2.1 · What moves into it

`DIVERGENCES` — today a static, hand-written literal at
`generate_spreads.py:118`. `generate_grades.py:158` currently reaches it the
long way round, by reading `wave11a_spreads.json` and parsing the
`divergence_windows` key, which is nothing more than a projection of that same
literal enriched with `lei` and `rating_band` from the instruments artifact.

**That artifact read is the entire dependency cycle**, and it is a cycle on
*configuration*, not on *computation*. Moving the literal into a shared module
— and the enrichment with it, as one function both generators call rather than
two implementations — dissolves it. `generate_grades.py`'s output is
unaffected: it receives the same data by a shorter path.

### 2.2 · What is new in it

`MIGRATION_PROFILES` — three response shapes, deliberately uncorrelated so
that signal strength and warning horizon cannot be conflated:

| Profile | Anticipation `α` | Lead (trading days) |
|---|---|---|
| `faint` | 0.30 | 110 |
| `moderate` | 0.60 | 40 |
| `pronounced` | 0.90 | 75 |

A dataset with one anticipation fraction teaches a detector that finds one
anticipation fraction. A dataset where strong signals always arrive early
teaches a detector to read timing as strength. Both are artifacts of the
generator rather than facts about credit markets, and Wave 11b
(`credit-surveillance-early-warning`) is measured against exactly this.

### 2.3 · Assignment is a permutation, not a draw

Profiles are assigned by a **seeded shuffle of the catalogue over crossing
LEIs sorted by LEI**, cycling if there are more than three.

An independent per-LEI RNG draw was the obvious construction and is wrong:
three independent draws from three profiles collide with probability ~0.78,
so the "vary across the three" decision would silently fail most of the time
and the failure would look like data. A permutation guarantees distinctness
whenever the count allows it.

**Profile is per obligor, not per crossing.** `5493003QENHHS261UR94` crosses
twice; both crossings share one temperament, which reads as a property of the
name rather than of the event.

**Observed on this seed** (an *outcome* of the permutation, never an input —
do not read this table as configuration):

| LEI | profile | α | lead (observation dates) |
|---|---|---|---|
| `5493003QENHHS261UR94` | faint | 0.30 | 110 |
| `5493004HBTOTE9DI9P12` | moderate | 0.60 | 40 |
| `549300EQD0ZXRSMG3549` | pronounced | 0.90 | 75 |

**Crossings: 4 across 3 obligors, two of them upgrades.**
`5493003QENHHS261UR94` BB→B @2025-11-19 and B→BB @2026-05-23;
`5493004HBTOTE9DI9P12` BBB→BB @2026-03-31; `549300EQD0ZXRSMG3549` B→BB
@2026-05-19. Corrects `known-issues.md` §9.10's original count, which listed
one row per obligor and read as 3.

### 2.4 · Migrations are discovered, not declared

The response is declared; the migration is not. `generate_spreads.py` reads
the grade chains and reacts to whatever crossings it finds.

The alternative — declaring the migrations explicitly — is architecturally
tidier and was rejected on blast radius: it forces `generate_grades.py` to
place declared crossings and suppress undeclared drift, which changes the 245
grade assertions, the 215-edge supersession chain, the Fluree load, and the
§F off-cycle-trigger counts. Discovery leaves all of that untouched.

Its one real cost is recorded rather than designed away: **the crossings exist
because of this seed.** A reseed could produce none, and the product would
silently lose its subject. §6 asserts their existence instead.

---

## 3 · Ramp mechanics

For an obligor crossing band `F` → `T`, announced on `M` (= `asserted_at`),
with profile `(α, lead)`:

```
gap(d)           = oas[T][d] - oas[F][d]           # real, per-date, signed

w(d)             = 0                        for d >= M
                 = LINEAR 0 -> 1 over [M-lead, M)

anticipation(d)  = α · gap(d) · w(d)               # added to idiosyncratic_bp

market_oas_bp(d) = oas[ band_in_force(d) ][d]      # steps at M
```

`lead` is counted in **observation dates present in the Treasury curve**, not
calendar days — the same date universe every other part of this generator
walks. A calendar-day lead would silently shorten across holidays.

The ramp is **linear**. An accelerating (convex) profile is arguably more
faithful to how anticipation builds, but it introduces a second shape
parameter with no way to validate the choice against anything real, and the
existing `divergence_weight` ramps linearly — one ramp idiom in one file.

### 3.1 · Provenance stays one class per column

`market_oas_bp` remains the real published index for whichever band is in
force — `public`, never blended. This is the property that ruled out gliding
between two band curves: a glided value is neither index, and would have
forced either a fourth column or a provenance downgrade during transitions.

The ramp lands in `idiosyncratic_bp`, already `synthetic — engineered`. Its
*magnitude* derives from public data — the real gap between two real indices —
but a shape invented to sit on top of real numbers is engineered, and stays
labelled that way. Deriving an engineered quantity from public inputs does not
make it public.

### 3.2 · The jump size is not a free parameter

Composed spread rises by `α·gap` before `M`, then jumps `(1-α)·gap` at `M`.
That falls out of the arithmetic. `α` is the only knob; there is deliberately
no separate "jump size" to set inconsistently with it.

### 3.3 · The one hard edge

`idiosyncratic_bp` steps down by `α·gap` at `M`, exactly cancelling into the
market's step up. That is a discontinuity in a column otherwise built from a
smooth AR(1) process and trapezoids.

It is intended: the anticipation *is* consumed by the announcement. But it is
the only place this design puts an edge where the existing code has none, and
a reader who finds it should find this paragraph.

**The mechanism is exactly invertible, and Wave 11b needs to know that.** At
any crossing, `α = 1 − jump/gap` from two adjacent rows (the exact identity
`validators/series.py` checks in reverse), and the ramp itself is
`α·gap(d)·w(d)` with `gap(d)` a real, contemporaneous, publicly-derived
quantity, not a latent parameter. A detector trained against this series can
recover the generator's `α` directly from the data rather than learn a
genuine early-warning signal — the series demonstrates the mechanic, it does
not exercise a detector's ability to find one.

### 3.4 · Upgrades need no special case

`gap(d)` is signed, so an upgrade produces a negative ramp and the spread
tightens ahead of the good news. The loaded data exercises both directions —
two downgrades, two upgrades — so this is tested by the corpus, not only by
construction.

---

## 4 · Pipeline and data flow

```
instruments ──► grades ──► spreads ──► load_postgres_wave11a
                  ▲           ▲
                  └─ narrative_wave11a ─┘
```

The order changes: spreads previously ran **before** grades. It now runs
after, because it consumes them.

| File | Change |
|---|---|
| `generators/narrative_wave11a.py` | **new** — `DIVERGENCES`, the enrichment function, `MIGRATION_PROFILES`, the permutation assignment |
| `generators/generate_grades.py` | `load_divergence_windows()` → import. No behavioural change |
| `generators/generate_spreads.py` | reads `wave11a_grades.json`; per-date band selection; the ramp |
| `loaders/load_postgres_wave11a.py` | unchanged code; reloads `spread_observation` |
| `docs/HANDOFF.md` | documented run order |

**Fluree is untouched.** No grade assertion moves, no supersession edge
changes, no reload. The blast radius is one Postgres table.

---

## 5 · Edge cases

| Case | Rule |
|---|---|
| Grades artifact absent | Hard fail naming the run order — not a `KeyError` from a missing file |
| Two crossings closer than `lead` | The later ramp starts no earlier than the previous `asserted_at`. Anticipation cannot precede the announcement it follows. Live-adjacent: `5493003`'s crossings are ~185 days apart against a max lead of ~155 |
| Crossing within `lead` of `WINDOW_START` | Ramp truncates; reported, not special-cased |
| `oas[T][d]` or `oas[F][d]` missing | **Hard fail**, `RuntimeError` naming the invariant broken (every curve date is present in every band's OAS series) — not a `KeyError`, and not a skipped observation. Both dict-index sites (`market_oas_bp` selection and the anticipation-ramp gap) are guarded; measured 0 occurrences across the loaded window, so this path is untested by the live data and exists only to fail loudly if the invariant is ever wrong |
| Obligor never crosses | No ramp, no profile consumed. 27 of 30 obligors |

---

## 6 · Validation and testing

### 6.1 · `validators/series.py`

Recomputed from the loaded series, never from a generator's own flag — the
standard this wave already holds for divergence and sparsity.

- **`>= 1` crossing in EACH direction (upgrade and downgrade) exists**
  (strengthened from `>= 1` crossing total, final-fix wave, I5). The guard
  that makes §2.4's seed dependency survivable — a reseed that removed the
  upgrade path silently would still pass the weaker check and would still
  leave §3.4's "tested by the corpus" claim false.
- For each crossing, **for each instrument of that obligor separately** —
  never averaged across an LEI's instruments, and never let one instrument's
  pass mask another's failure (final-fix wave, I1) — the band whose index
  `market_oas_bp` matches actually changes at `asserted_at`.
- Measured pre-announcement move ≈ `α·gap`, and measured residual jump ≈
  `(1-α)·gap`, each **within 15% relative tolerance** (final-fix wave, I2 —
  this is the first time the pre-announcement half was actually computed and
  checked; `docs/HANDOFF.md` and this document had asserted it without a
  check behind it). The band is wide on purpose: the AR(1) idiosyncratic
  process is still running underneath and a tight bound would be asserting
  that noise is absent rather than that the ramp is present.

  **One correction the first real run surfaced:** `market_oas_bp` is a real
  published index, not frozen while a band stays in force — §3's own
  `market_oas_bp(d) = oas[band_in_force(d)][d]` already says so. Over a
  110-observation lead it can drift materially on its own (measured up to
  23bp), so the check compares `spread_bp`'s pre-announcement move against
  `α·gap` **plus that band's own measured drift over the ramp window**
  (`market_oas_bp` at the two compared dates, both loaded rows) — not
  `α·gap` alone, which under-predicts whenever the band moved during the
  lead. All four crossings pass with the drift term included; three of four
  fail a naive `α·gap`-only comparison by more than the 15% band. `α·gap`
  alone remains the right description of the *ramp's own* contribution;
  the ramp is what `idiosyncratic_bp` carries, and it is exactly what
  `α = 1 − jump/gap` recovers (§3.3) — it is `spread_bp`, the composed
  total, that also carries the band's independent drift.
- Every existing gate still holds: 4 divergence windows, 1 confirmed-later,
  2 sparse instruments, dominance ≤ 0.40.

**Dominance will move.** The ramps add to `|idiosyncratic_bp|`. Present
headroom is 0.1893 against a 0.40 ceiling, with median `|idio|` 22.0 bp
against a 46.4 bp ceiling — but the ramps are large relative to that: peak
`α·gap` is up to ~110 bp *if* the 0.90 profile lands on the ~122 bp gap, which
is not known until the permutation is drawn. Bounded to 6 of 60 instruments
over bounded windows, so the effect on a median across 29,885 observations
should be small — "should be" is the reason this is measured.
**This must be measured and printed, not assumed.** The script already prints
the ratio; if it breaches, that is a design finding, not a tuning exercise.

**Measured, 2026-08-20:** 0.1861 as computed by the generator, 0.1847 as
recomputed by `validators/series.py` from the loaded store — the two differ
slightly and both are recorded rather than reconciled — against the
unchanged 0.40 ceiling (was 0.1893 before this change). No breach; the
prediction above held.

**The realized peak ran past the estimate, and it is worth recording why.**
The 0.90 profile did land on the largest gap: `549300EQD0ZXRSMG3549`'s
B→BB upgrade measures a peak `α·gap` of **≈ −125 bp** (`syn-i-499ec4`,
2026-05-18, `w=0.987`, `gap=−141bp`), above §6.1's pre-permutation estimate
of "~110 bp" — that estimate used the ~122 bp gap observed at generation
time for a different band pair; the pronounced profile instead landed on
the B/BB pair, whose gap runs wider. Not a design finding: the estimate was
explicitly provisional pending the permutation draw (§6.1 above), and the
outcome stays well inside the measured dominance headroom.

**This also produced a new negative tail in `idiosyncratic_bp`.** An
upgrade's ramp is negative (§3.4), and 0.90 · (−141 bp) pushes the column
well below its old floor: measured minimum **−92.7 bp**, against **247** of
29,885 rows negative post-fix (**12** before this change, all AR(1) noise
excursions). `spread_bp` itself never follows: measured minimum **43.3 bp**,
unchanged — the ramp borrows from the idiosyncratic leg, not from the
composed total, because `market_oas_bp` stays comfortably larger than the
largest ramp at every date.

### 6.2 · `validators/conditions.py` — unchanged

These are design-integrity checks, not §F conditions. §F comes from the spec
and says nothing about migration response. Keeping the boundary clean matters:
§F is the contract with the product, `series.py` is our own workmanship.

### 6.3 · Pure-function tests

In the `test_curves.py` idiom — the ramp weight is a pure function and belongs
under test without a database:

- ramp weight is 0 at `M`, 0 at `M-lead`, monotone between, and never exceeds 1
- profile permutation is deterministic across runs and distinct for ≤ 3 LEIs
- lead truncation on adjacent crossings
- negative `gap` yields a negative ramp

### 6.4 · Whole-pipeline gates

- `artifact_reproduces_store.py` agrees after regeneration
- a double run is byte-identical
- `partition.py` 13/13 and `conditions.py` 82/0 unchanged

---

## 7 · What this deliberately does not change

- **Grade generation.** Not one assertion moves.
- **The divergence windows.** All four, and the confirmed-later flag, are
  untouched declarations.
- **§F conditions.** No count changes, no new condition.
- **Fluree.** No reload.
- **Provenance labels.** No column changes class.

---

## 8 · Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Dominance ratio breaches 0.40 | Measured and printed every run; a breach is a design finding, and the honest responses are a lower `α` ceiling or excluding transition dates from the pool the way divergence dates already are — **not** silently raising the ceiling |
| 2 | Reordering the pipeline breaks a caller not yet identified | `HANDOFF.md` run order is the only documented consumer; verified by a clean end-to-end rerun |
| 3 | A future reseed produces zero crossings | §6.1's existence assertion converts a silent loss into a loud failure |
| 4 | The `idiosyncratic_bp` step at `M` reads as a defect to a consumer | §3.3, and it is visible in the artifact rather than only in prose |

---

## 9 · Out of scope

- Wave 11b's detector. This design supplies the signal; it does not read it.
- Declaring migrations explicitly (§2.4) — recorded, rejected on blast radius.
- The estate-wide EDGAR `recent` re-baselining (`known-issues.md` §9.11).
- Any change to `conditions.py` or to the vault spec.
