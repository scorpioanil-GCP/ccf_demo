# Gate 1 measurement note — the two claims, measured separately

**Date: 2026-09-11. Subject: `.76`, read-only throughout. Nothing was written.**

Dave ordered the two claims measured apart, on a distinction this note exists to
keep: **a booking lag is not proof of supersession.** They were measured apart,
and they do not both hold.

| Claim | What would prove it | Verdict |
|---|---|---|
| **Two clocks** | Same covenant; `as_of` inside its validity interval; moving `known_as_of` from before to after `assertedAt` **changes the answer** | **FAILS on covenants · HOLDS on amendments** |
| **Supersession preserved** | A later amendment replaces a covenant assertion, and querying the ledger at the original `t` still returns the prior one | **FAILS — no such row exists** |

---

## Claim 1 — two clocks

The caveat was load-bearing: the three booking-lag rows prove two-clock behavior
**only if both temporal axes are populated on the rows the product would read.**

| facility | covenants | with `validTo` | **with `assertedAt`** |
|---|---|---|---|
| `FAC-01BB3F` | 5 | 1 (a `BreachOfCovenant`, not a covenant term) | **0** |
| `FAC-2A2C38` | 4 | 0 | **0** |
| `FAC-405B7A` | 4 | 0 | **0** |

**The assertion-time axis is on zero covenants.** It lives on the *amendment*
nodes. So there is nothing on a covenant for `known_as_of` to filter, and moving
it across a booking gap cannot change the covenant set. Measured across the whole
ledger and not only these three: **covenants carrying `assertedAt` = 0 at
`t:1500`, `t:3000` and head.**

**It holds one level up, and genuinely.** `AMD-01BB3F-2` carries
`validFrom 2025-08-14` and `assertedAt 2025-10-05`. At `known_as_of=2025-09-09`
it is not yet booked and is excluded; at any later `known_as_of` it is admitted.
That is a real two-clock demonstration **over the amendment slice**.

---

## Claim 2 — supersession preserved

Three independent measurements, all negative.

**(a) No covenant assertion ever changes.** Thresholds, by ledger point:

```
t:1500   180 thresholds   (baseline)
t:2000   180 | changed 0 | added 0
t:3000   180 | changed 0 | added 0
t:4000   180 | changed 0 | added 0
t:5000   180 | changed 0 | added 0
t:5591   180 | changed 0 | added 0      ← head
```

**(b) No covenant interval is ever closed, and no marker ever appears:**

| probe | `t:1500` | `t:3000` | head |
|---|---|---|---|
| covenants with `validTo` | 2 | 2 | 2 |
| covenants carrying `supersededBy` | **0** | **0** | **0** |
| covenants carrying `assertedAt` | **0** | **0** | **0** |

**(c) The 1,107 supersession markers are not in this product's slice.** They sit
on `WarningSignal` (486), `OpportunitySignal` (354), `CreditRating` (215),
`IssuanceEvent` (111), `PriorObservation` (49), `BreachOfCovenant` (4) and
`PolicyVersion` (2) — every class except the covenants cp-08 reads. Per the
instruction, they **do not count**.

**Conclusion.** The ledger's covenant history is a single staged load, not an
amendment lifecycle. There is no facility where a later amendment supersedes an
earlier covenant assertion, so there is nothing for time-travel to reconstruct.
**cp-08 must not claim "supersession preserved."**

---

## A near-miss, recorded because the control is the only reason it is not in the spec

`ex:covenantOf` returned **182 at `t:1`** while *all typed subjects* returned
**0** at the same point. Both cannot be true of one ledger state, and the
tempting conclusion was a substrate defect: *the pinned read silently ignores
its pin*, which would have been a serious finding against a shipped adapter.

It is not true. The control:

| probe | `t:1` | `t:2000` | head |
|---|---|---|---|
| all typed subjects | **0** | 17,230 | 17,871 |
| `ex:amends` | **0** | 130 | 143 |
| `ex:supersededBy` | **0** | 1,107 | 1,107 |
| `ex:covenantOf` | **182** | 182 | 182 |

The pin is honest — three of four probes move monotonically, and a pin past head
returns `408 err:db/ReadAfterWriteTimeout`. The explanation is the ingestion
discipline this repository already documents: **thin edges first, attributed
nodes last.** The `covenantOf` edges were written in the first transaction; the
type, threshold and `validFrom` attributes came later.

**This also verifies the reproducibility property `CIF-G10` rests on**: a pinned
read at a recorded `t` genuinely reconstructs that ledger point.

---

## Outcome — Option B

No Option A row exists. The spec is narrowed:

- **keep** the two clocks and the booking lag, over the **amendment** slice
  where both axes are populated;
- **remove** "supersession preserved" from the title, the claims, the gates and
  the teaching text;
- **keep** the pinned-read reproducibility claim, which is measured and holds.

---

# Correction, 2026-09-11 (Gate 2) — a real number about the wrong population

**This note's own Gate-1 figures were scoped wrongly, and the correction struck
a finding, a debt metric and two gates.** It is recorded here rather than
overwritten, because the error is more instructive than the number.

## What was claimed

> *"112 of 137 amendments carry no `assertedAt` and cannot be placed on the
> assertion axis. This is the debt signal's subject."* — `CP08-F-03`

That figure counted **every `ex:amends` edge in the ledger**. Measured by what
the edge actually points at:

| target class | `ex:amends` edges |
|---|---|
| `Trade` | **89** |
| **`CreditFacility`** | **25** |
| `TradeLifecycleEvent` | 16 |
| `SyndicatedLoan` | 7 |

**cp-08 reads facility amendments.** Scoped to that slice:

```
amendments whose target is a CreditFacility     25   (across 18 facilities)
  carrying validFrom                            25
  carrying assertedAt                           25
  missing EITHER clock                           0
```

## What it cost, and what was struck

- **`CP08-F-03`** — struck. There is no unplaceable population.
- **The cp-08-specific `D_c`** — removed. Defined as *placeable ÷ served*, the
  ratio is **1 on every facility** and the debt **0 on every answer**: a scalar
  that cannot move with the answer, which is the `CP04C-F-02` defect one rung
  over, rebuilt from scratch here.
- **`CIF-G07`** (unplaceable amendment recorded) and **`CIF-G14`** (`D_c` moves
  with the ratio) — struck. Both guard a population of zero.
- **No replacement metric was invented.** A debt figure exists to report a
  shortfall; this product on this estate has none of that kind.

## Why it survived three checks

The number was measured, not assumed — a query was run and its output quoted.
What was never checked is **which population the query ranged over**, and the
product's slice is a subset the predicate `?a ex:amends ?f` does not express.
The tell was available and missed twice: `facilities with amendments: 135`
against `facilities carrying ≥1 covenant: 45` is an arithmetic impossibility for
one population, and it sat in this note from the first measurement.

**The rule this yields, and it is not the same as "measure it":** a count is
only as good as the population it ranged over, so state the population in the
same breath as the number. *"137 amendments"* is a fact about the ledger;
*"25 facility amendments"* is a fact about the product. Only the second belongs
in a specification.

## What was NOT affected

The exhibit is untouched, and it remains everything cp-08 claims:

```
FAC-01BB3F · as_of 2025-09-09 held · drawdown DRW-01BB3F-0000 inside the 52-day gap
  known_as_of=2025-09-09 → admitted [AMD-01BB3F-1]
                           excluded [(AMD-01BB3F-2, 'assertion-time')]
  known_as_of=2026-09-11 → admitted both, excluded []
  covenants 4, labelled unversioned
```

Two clocks, the booking lag, the assertion-time exclusion named by axis, replay
at a recorded ledger `t`, and covenants served unversioned. All measured through
the governed path, all intact.
