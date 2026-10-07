# cp-12 — findings

**The authoritative findings record for `examples/cp-12-fx-post-trade-reconciliation`.**
Every `CP12-F-NN` referenced anywhere in this tree resolves here.

Status vocabulary is `D-IMPL-261`'s: **OPEN** / **FIXED-`<phase>`** /
**ESTATE-LIMITATION** / **NOT-A-GAP**. A constraint or an estate property is not
OPEN work.

**No SDK gap was found and none is authorized.** Every capability this rung
needs already existed: as-of pinned reads, `decay: supersede-only`,
`freshness_over: leading-edge` with a `series_key_attribute`, the declared
product gate seam, and a refusal returned as data.

---

## Gate-1 findings — measured before any code existed

| id | finding | status |
|---|---|---|
| `CP12-F-01` | **No settlement-instruction, netting, ISO 20022 or CLS-cutoff data exists.** The article's schema names a `SettlementInstruction` entity and `settlesVia` / `netsWith` relationships; measured, both predicates are **ABSENT** from this estate's vocabulary — not present with a count of zero. A predicate nothing asserts is not a predicate asserting nothing. The product is specified without a settlement leg, does not claim one, and reports the leg as absent (`FXR-G18`). | ESTATE-LIMITATION |
| `CP12-F-02` | **CFTC Part 43 exists as a DISTRIBUTION PROFILE, not as records.** 44 rows of `(dimension, key, observed_n)` summarising 30,501 real DTCC observations retrieved 2026-08-22. The trades are *patterned on* it. No per-trade public record exists to join to, so Part 43 is provenance and calibration, never an `E` leg. | ESTATE-LIMITATION |
| `CP12-F-03` | **The estate labels two break classes; the article specifies four.** `break_record.designed_class` holds only `timing` and `genuine`. The product classifies into `timing`, `genuine` and `not-evaluable` and **does not invent** `amendment-lag` or `revaluation-basis` (`FXR-G21`). | ESTATE-LIMITATION |
| `CP12-F-04` | **The tick series cannot adjudicate sub-five-minute intervals.** 5-minute spacing against observation gaps frequently below it. Handled by refusing to decompose rather than by interpolating (TRAP 2, `FXR-G10`, `FXR-G25`). | ESTATE-LIMITATION |
| `CP12-F-05` | **The tick series has a 173,100-second weekend gap.** `TRD-W12-0124`'s nearest preceding tick is 20.0 hours old and yields a −72.49-pip residual on a raw variance of 5.15. Same handling (TRAP 4, `FXR-G11`, `FXR-G27`). | ESTATE-LIMITATION |
| `CP12-F-06` | **Intraday ticks are `synthetic — engineered`; the daily reference rates are public.** The split is disclosed rather than blurred. | NOT-A-GAP |
| `CP12-F-07` | **47 pairwise disagreements above 0.5 pip carry no `break_record` row**, against 47 that do — the same underlying divergences seen through the second system pair. `break_record` is a designated sample, never the population. | NOT-A-GAP |
| `CP12-F-08` | **Notionals are banded, never exact.** Part 43 caps large notionals for anonymity. Every variance is reported in pips, which is a property of the rate and not of the size (`FXR-G17`). | ESTATE-LIMITATION |

---

## Gate-2 findings — found by building the product

### `CP12-F-09` — the tick series does not reproduce a designed timing move beyond a short interval

**ESTATE-LIMITATION.**

The intraday tick series and the system values were engineered **independently**,
so revaluing two systems against the series reproduces the designed break
magnitude only when the observation gap is short.

Measured at `compare_at=amendment-0`, 2-pip threshold, over the 60 designated
breaks — 51 evaluated, 9 `not-evaluable`:

```
computed timing   14   of which designated timing   14   (14 of 14)
computed genuine  37   of which designated genuine  20   (20 of 37)
```

**The product never says `timing` about a designated-genuine break.** What it
over-reports is `genuine`: 17 designated-timing breaks read genuine, and the
disagreement grows monotonically with the observation gap —

```
  gap   425 s   total 4.64 pips   timing  8.48   residual  −3.84
  gap   955 s   total 6.95 pips   timing  4.87   residual   2.08
  gap  1966 s   total 4.14 pips   timing  7.82   residual  −3.68   (TRD-W12-0002)
  gap  6866 s   total 7.60 pips   timing  0.33   residual   7.27
  gap 10849 s   total 5.26 pips   timing 19.00   residual  −13.73
```

The designed break magnitudes sit in a 4–8 pip band regardless of gap, while a
real rate series moves further the longer you wait. Beyond roughly ten minutes
the two stop agreeing, and the residual is measuring the difference between two
generators rather than an error in a booking system.

**Not repaired, and deliberately.** `break_record` is a designated sample and
not the truth (`CP12-F-07`), so "agrees with the designation" is not the target
and tuning a cutoff until it did would be the move CLAUDE.md §9 exists to
prevent. The payload carries `estate_designated_class` **beside** the computed
verdict — never instead of it — together with `compared_gap_seconds`,
`tick_staleness_seconds` and the full decomposition, so a consumer can see a
19-pip timing attribution against a 5-pip total and judge it. This is a sharper
statement of TRAP 2 from the other end: the series cannot resolve an interval
below 300 s, and it cannot reproduce a designed move much above 600 s.

### `CP12-F-10` — a zero observation gap is not TRAP 2, and treating it as such destroyed the product's best answer

**FIXED-gate-2.**

The first implementation applied TRAP 2's rule — *an interval shorter than the
tick spacing is not evaluable* — to intervals of length **zero**, and returned
`not-evaluable` for 29 of 60 breaks.

Measured, that buried the strongest signal in the estate:

```
corrected observation gap == 0   on 20 of the 60 break trades
those 20 are EXACTLY the 20 the estate designates `genuine`   (20 of 20)
no other shape present
```

**The two cases are different facts.** TRAP 2 is about two *different* instants
inside one 5-minute bucket: they revalue identically, so a zero timing component
is an artifact of the series' resolution. Two *identical* instants leave no
interval at all — there is no market move to attribute, and the timing component
is zero by arithmetic, at no resolution and with no tick series consulted. That
is `CP-SPEC-012` §D.3 scenario 2 exactly: *risk and trading observed at the same
true instant, and no amount of timing explains the difference.*

Corrected in `projection._verdict`: a zero gap is decomposed with
`timing = 0`, `residual = total`, and a payload note saying no tick series was
consulted. `not-evaluable` fell from 29 to 9.

### `CP12-F-11` — §D.3 scenario 1 names a trade the product's own binding refuses

**FIXED-gate-2** (specification amended at Gate 2).

The spec's scenario 1 names `BRK-TRD-W12-0235` with *"raw 6.95 pips, aligned
residual −0.09, corrected observation gap 296 s"*. But **296 s is below the
300 s tick spacing**, and §D.2 step 6 — with `FXR-G10` and `FXR-G25` — requires
such an interval to be `not-evaluable`.

Those numbers were produced during Gate-1 measurement by the **residual-magnitude
mechanism TRAP 2 refuses**. The binding wins over the illustration: a scenario
paragraph's figures cannot override the rule the gate table enforces.

Measured replacement, selected from the evaluated population with a gap at or
above the tick spacing:

```
TRD-W12-0472  EUR/USD   total 6.01 pips   timing 5.79   residual 0.22
              gap 388 s   tick staleness 279 s   designated: timing
```

Raw variance three times the materiality threshold; residual an eighth of it.
Looks like a genuine error; is the market moving for six and a half minutes.
`TRD-W12-0235` is retained in the gate suite as `FXR-G10`'s subject, which is
what it actually demonstrates.

### `CP12-F-12` — the comparison peer was chosen non-deterministically, and the content address moved with it

**FIXED-gate-2.**

The verdict rests on one comparison: the divergent system against a member of
the agreeing group. The first implementation chose that member with
`next(iter(agreeing_group))`.

**Python salts string hashes per interpreter**, so set iteration order over
system names is not stable across processes. Measured: `TRD-W12-0002` compared
against `risk` on one run and `trading` on the next — same code, same data,
different answer and a different content address.

§D.4 declares determinism class `deterministic`. A determinism class is a
property of the code, not a declaration about it. Fixed by ordering on the
canonical `SYSTEMS` tuple: any member is representative of the agreed value, and
a free choice in a replayable product must still be a fixed one.

### `CP12-F-13` — the three served decomposition figures did not close

**FIXED-gate-2.** Found by `FXR-G09` under sabotage.

Quantizing total, timing-attributable and residual independently does not close.
Measured on `TRD-W12-0100`:

```
served:  12.53 + −5.86  =  6.67       against a served total of 6.68
```

Worse, the payload's `closes` flag read **true**, because it compared the
*unrounded* sum against the rounded total — it asserted a property of
intermediates the consumer cannot see. The residual is by definition the
remainder, so it is now taken as the remainder of the figures actually SERVED,
and `closes` states an arithmetic fact about the payload.

### `CP12-F-14` — no three-way disagreement exists anywhere in the estate

**ESTATE-LIMITATION.**

`FXR-G08`'s second limb — *where the partition is `(1, 1, 1)` the payload names
no divergent system* — has nothing to range over. Measured across **all 500
trades** at a materiality of **0.01 pip**, two hundred times finer than
`break-investigation` uses:

```
all three agree exactly      440
exactly two agree exactly     60
three-way disagreement         0
```

In every break the two agreeing systems match to the last digit, so no threshold
can separate them. The limb is recorded `not-required` in `artifacts/gates.yaml`
and the **absence is asserted** by the executing test rather than assumed — if
the estate ever grows a three-way case the gate goes red and the limb becomes
testable. The `(1, 2)` limb is asserted on all 60 real partitions and is
sabotage-proven.

### `CP12-F-15` — the 1-hour production freshness reference cannot be demonstrated on an 8-day snapshot, so this example binds 48 hours

**ESTATE-LIMITATION.** Illustrative calibration under CLAUDE.md §9 and
`D-IMPL-323`. Ruled by Dave at Gate 2, 2026-09-12.

#### Two figures, and they are not the same contract

| | value | what it is | where it lives | does the served product use it? |
|---|---|---|---|---|
| **Production freshness reference** | **1 hour** | the freshness **SLA** this product would run at against continuously refreshed market data. A *reference figure*, stated so the production intent is on the record | prose in `spec/CP-SPEC-012` §B.5, **and nowhere else** | **NO.** Bound in no artifact in this tree |
| **CP-12's illustrative half-life** | **48 hours** | the value **this example actually runs at**, chosen so the mechanism is observable against a static estate | `ccf_config.yaml` → `half_life.fxr_observation.half_life_seconds: 172800` | **YES.** Every `F` this example serves is computed from it |

**The served product uses the bound value and never the printed reference.**
`FXR-G28` asserts it, by serving the same two trades under each binding.

**48 hours is NOT a production recommendation.** The production recommendation
in this product's specification is the 1-hour reference, and it is deliberately
not what this example runs.

#### Why the reference cannot be demonstrated here

The trade window is 2026-08-06 .. 2026-08-13 — **eight days wide**. At a 1-hour
half-life every observation in it has aged to nothing, so `F` is carried almost
entirely by the non-decaying `fxr_trade` class and reads the same for a trade
booked four days ago and one booked hours ago. The term has stopped measuring
its own subject, which is precisely the cp-07 failure `D-IMPL-323` records.

#### The measured sensitivity

At `as_of = 2026-08-14`, two real trades, served end to end through the governed
path under each binding:

| λ_c | `TRD-W12-0002` | `TRD-W12-0424` | spread |
|---|---|---|---|
| **1 hour** — production reference, *bound nowhere* | F `0.2500` | F `0.2508` | **0.0008** |
| **48 hours** — illustrative, *bound in `ccf_config.yaml`* | F `0.5151` | F `0.8999` | **0.3848** |

All four figures are pinned by `FXR-G28`, which also asserts that the two
bindings produce *different* served figures — if they matched, `F` would not be
reading the Control Plane document at all and the pinned numbers would be
constants. Sabotage: rebinding `ccf_config.yaml` to 3600 turns the gate red.

Only the *declared threshold* is a demonstration value. The observations, the
decay curve and the decision instant stay the estate's and the SDK's.

#### Where the disclosure lives

`ccf_config.yaml` (beside the value), `spec/CP-SPEC-012` §B.5.0 and §E, this
file, `README.md`, and `summary_explanations.md`. A reader arriving at any one
of them is told which figure is bound and which is a reference.

### `CP12-F-16` — a Gate-1 figure in TRAP 4 was wrong, and the gate that defends it does not quote either number

**FIXED-gate-2.**

`CP-SPEC-012` §C.3 recorded `TRD-W12-0124`'s raw variance as **7.99 pips**.
Measured through the served product it is **5.15**:

```
TRD-W12-0124  AUD/USD   pip 0.0001
  trading      0.698121   corrected 2026-08-08 19:55:41
  settlement   0.698636   corrected 2026-08-07 12:42:01
  risk         0.698636   corrected 2026-08-07 12:42:01

  trading vs risk          5.15 pips          <- the raw variance
  nearest tick             2026-08-07 23:55   <- 20.0 hours before 19:55:41
  naive residual         -72.49 pips
```

Everything else in TRAP 4 is confirmed — the `−72.49`-pip naive residual, the
`20.0`-hour staleness, the 173,100-second weekend gap. Only the raw variance was
wrong.

**Why it was found at all.** `FXR-G27` **computes** both mechanisms on the trade
rather than asserting a figure copied out of the specification. A gate that had
pinned `7.99` would have gone **red against correct code** — the third time in
three rungs that a text-quoting instrument would have done so, after cp-11's
gate 20 and this rung's own `FXR-G19` (where `d_c` is a substring of
`estate_designated_class`). The spec paragraph now carries the corrected figure
with the correction marked, rather than being quietly overwritten.

## Security remediation — `EX-09` (2026-10-07)

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before the change: §B.4, the example's own code rather than the SDK. Changed under `D-IMPL-261`'s "objectively wrong" reason, authorized by `D-IMPL-376` ruling (7): *"SDK input rejection is useful defense, but leaves fragile example code for adopters to copy."*

- **`EX-09`.** `acquisition.py::_Relational.rows` built `SET search_path TO {schema}` by f-string (security review 2026-09-23). It now composes the statement with the driver's own `psycopg.sql` — `SQL("SET search_path TO {}").format(Identifier(schema))` — so the configured schema reaches PostgreSQL as one quoted identifier, whatever it contains. The documented schema `ccf_v2` is one lowercase identifier, so it names the same schema quoted or not.

Evidence: `tests/examples/test_ex_09_search_path_identifier.py`.
