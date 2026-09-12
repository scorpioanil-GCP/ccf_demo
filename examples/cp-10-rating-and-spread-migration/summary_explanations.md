# Rating & Spread Migration — what it does, and why it is not a report

Three numbers that all mean "credit quality", moving at three different speeds.
A report picks one. This product keeps all three apart, and answers the question
that only exists **between** them: *does the market think this obligor has
deteriorated before the credit file says so?*

Every figure below came out of a run against the live estate. Nothing here is
illustrative except where it says so.

## The argument, in one paragraph

A corporate bond's spread over Treasuries is three things added together: the
Treasury benchmark itself, the option-adjusted spread of the *rating band* the
bond sits in, and whatever is left — the issuer-specific residual. When the
whole high-yield market widens, the first two move and the third does not. A
product that serves only the total reports that as a deterioration. Measured on
this estate, over one seven-week window, **22 of the 30 rated obligors** would
have been flagged that way. Meanwhile the internal credit grade is reviewed
quarterly, so it is on a ninety-fold slower clock than the spread — and the
signal the credit officer actually wants is precisely the gap between the two.
Keeping the three components separate, on their own clocks, is the product.

## The pipeline, in three rows

| stage | what happens | where |
|---|---|---|
| **acquire** | two source legs read over one window bounded at the decision instant — the spread decomposition and instrument reference from PostgreSQL, the bitemporal grade history from Fluree | `acquisition.py` |
| **assemble** | envelopes into L2, edges first and nodes last; four entity classes so a daily quote and a quarterly grade cannot share a decay rate | `deployment.py` + `ccf_config.yaml` |
| **project** | per-bond series, episode detection against each bond's own median, the three-part confirmation test, and the series register | `projection.py` |

`produce.py` is the spine — boot, acquire, govern. It contains no gate, no
binder, no debt scorer and no replay record of its own. Those are the SDK's.

## Run 1 — the confirmation

```
$ make -s example-cp-10
```

Celanese Corp, `549300FHJQTDPPN41627`, two years to 2026-08-20.

**The finding.** On **2024-12-11** the issuer-specific spread on the five-year
bond `syn-i-b23153` peaks at **233.245 bp** — **8.039×** that bond's own 29.015
bp median. The obligor's internal grade that day is **BB**. The credit file
moves on **2025-03-17**, **96 days later**: **BB → BB-**, off-cycle, with the
trigger recorded in its own words — *"ad hoc credit review following sustained
spread widening in the obligor's traded debt."*

**What a banker should notice.** The 25-year sibling `syn-i-f87e69` reaches
37.378 bp on the same day — **1.27×** its own median. **No episode.** The
concern is entirely at the short end. The two bonds' medians are 29.015 and
29.538 bp, so nothing about the *level* distinguishes them; only the move does.
Report the obligor-level average and you get one blurred number and no term
structure at all.

**What an engineer should notice.** The grade reported beside the peak is the
grade in force **on the peak date**, not the current one. By the window's end
the obligor is `BB-`, and reporting that would erase the very change the product
exists to detect. The units are deliberately mismatched — the spread prices a
*bond*, the grade assesses the *obligor* — and the product does not invent a
per-bond grade to make them match.

`D_c` **0.3651**, signal `ok`. `F` 0.6641, `C` 0.9559, `S` 1.0000.

## Run 2 — a standing disagreement

```
$ make -s example-cp-10 LEI=529900VKCYZW8GZ4WW58
```

Sabre Corp. The 25-year `syn-i-4d322a` peaks at **282.633 bp**, **7.004×** its
own median, on 2026-01-23. The grade is **B** at the peak and **B** at the
window's end, through two later quarterly reviews.

**This is the same machinery returning the opposite answer**, and the
distinction it draws is the one that took a defect to find. The product does not
say "no confirmation." It says `outcome: unchanged`, names the grade that stood
throughout, and counts the reviews that left it alone. An earlier revision
returned the same empty answer here as for an obligor that carries no grade at
all — so a **standing disagreement** and an **absence of evidence** were
indistinguishable. They are different findings for a credit officer: one says
*nobody has looked*, the other says *somebody looked, twice, and disagreed with
the market.* Recorded as `CP10-F-08`.

## Run 3 — the market move that is not a deterioration

```
$ make -s example-cp-10 LEI=549300TRW1LZMDJZAQ78 \
    AS_OF=2025-04-07T00:00:00+00:00 WINDOW_DAYS=48 GRANULARITY=daily
```

B&G Foods, `2025-02-18 → 2025-04-07`. Every band widened together — `B` +165.0
bp, `BB` +150.5, `BBB` +51.2, `A` +36.0, `AA` +28.9. A risk-off move across the
whole market.

This obligor's **headline** spread moved **+166.6 bp**. Its **residual** moved
**+1.5 bp**, ranging 33.3–46.1 bp across the window. Its grade was `B`
throughout, including a quarterly review inside the run-up.

**The product reports no episode, and says why.** All three signals agree that
nothing happened to this obligor; the widening belonged to the band. `D_c`
**0.0524**, signal `ok`.

**This is the more common error, and it points the opposite way from runs 1 and
2.** A product reading the headline would have flagged 22 of the 30 rated
obligors over this same window. That is the difference between a screen a credit
officer can use and one they learn to ignore.

## Vocabulary

| term | what it means here |
|---|---|
| **benchmark** | the Treasury yield the bond is quoted over. Public. |
| **market OAS** | the option-adjusted spread of the band the bond was **issued** into. Public (ICE BofA series on FRED). |
| **issuer-specific / residual** | what is left after the two above. **Synthetic — engineered**, and a *residual*, never an observed trade price. This estate holds no TRACE data. |
| **own median** | each bond's own median residual over the window. The episode threshold is a multiple of *this*, never an absolute basis-point figure — 100 bp means different things at `AA` and at `B`, and different things on a 2-year and a 25-year. |
| **`validFrom` / `assertedAt`** | when a grade took effect, and when the system learned it. Different facts; this estate's booking lag runs 1–5 days. |
| **off-cycle** | a grade change whose recorded trigger is not a scheduled quarterly review. Read off the trigger **text**, never inferred from spacing. |
| **`static_issue_band`** | the basis the market leg is netted on: the band the bond was issued into, which does not follow the obligor's grade. |
| **leading edge** | the newest observation in a series at or before the decision instant. What `F` measures. |

## Where each claim is enforced

| claim | enforced by |
|---|---|
| the three components are never summed | `RSM-G07` — asserts the total is **absent**, not merely that the parts are present |
| episodes are per bond, against that bond's own median | `RSM-G09` — asserts the baseline is not the obligor blend |
| a market-wide widening is not a deterioration | `RSM-G22` — asserts no episode in run 3, **and** asserts the premise: that the residual really is flat and the market component really did move |
| the grade at a peak is the grade in force then | `RSM-G10` |
| a confirmation is three separate tests | `RSM-G11` — later, downgrade, off-cycle, each reported on its own |
| both clocks are served and differ | `RSM-G13` |
| each class ages on its own λ_c, at the leading edge | `RSM-G15` |
| the basis is named and migration is flagged, never corrected | `RSM-G23` — asserted against an obligor that **has** migrated |
| the obligor-level figure never travels alone | `RSM-G24` — and the declared product gate refuses the serve first |

## Why you can trust these numbers

**Every one of the 24 gates was sabotaged and watched go red.** 21 went red on
their own assertion; 3 could not be falsified from this deployment at all,
because an SDK guard refuses the bad state before the deployment can produce an
artifact — those are recorded as `unavailable`, not as `passed`, because they
mean different things.

**Two gates passed under their own sabotage on the first attempt, and both are
recorded as such.** `RSM-G13` asserted a booking lag computed from the *source*
rather than the two instants actually served, so collapsing the two clocks in
the payload left it green. `RSM-G23` asserted only against an obligor still in
its issue band — where the right answer and the wrong answer are the *same
value*, so the contamination it exists to refuse was invisible. Both were weak
tests, not weak sabotages. A gate asserted only where two answers coincide
proves nothing about which one produced them.

**The freshness figure was wrong, and the fix was an SDK ruling.** Averaging
freshness across 996 historical quotes drove `F` to **0.004750** and the product
to `fail_closed` — with a newest quote two days old. `D-IMPL-333` lets a λ_c row
declare `freshness_over: leading-edge` and a series key; `F` is now 0.664139
over the newest quote per bond plus the grade in force. History is evidence, not
staleness. Recorded as `CP10-F-07`.

## What these runs do NOT show

- **No agency ratings anywhere.** Verified, not assumed: no agency column exists
  in any of the estate's 118 tables. The scale is `synthetic — internal`.
- **No TRACE data.** The residual is a decomposition, not an observed trade.
- **The market leg's basis is imperfect and the product says so.** It is netted
  on the band the bond was *issued* into. Two of the 30 rated obligors have left
  that band, and for them the residual is less precise — in a *knowable*
  direction, since a wider band means the market component is understated. The
  product flags them and does not correct them, because inferring a replacement
  band from the internal grade would make the market component a function of the
  grade the divergence is measured against. A residual computed that way could
  never disagree with the grade, which would leave this product with nothing to
  say. Recorded as `CP10-F-04`.
- **The half-lives are illustrative.** This example runs against a point-in-time
  demonstration estate rather than continuously refreshed production data.
  Freshness half-lives and related thresholds are calibrated to make the
  governed behavior observable in that snapshot. They demonstrate how the SDK
  applies these controls and should not be interpreted as recommended production
  coverage-policy thresholds.
