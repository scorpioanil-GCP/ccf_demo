# cp-10 — Rating & Spread Migration

**Has this obligor deteriorated — and does the market think so before the
credit file does?**

Three signals that are all "credit quality", moving at three different rates,
where **the interesting fact is the divergence** and any average destroys it.

## What this demonstrates

Rung 9 proved one `as_of` can govern four *kinds* of time without flattening
them. This rung asks the next question: what happens when the signals
themselves disagree, and the disagreement is the answer.

- **Three spread components, served separately and never summed.** A Treasury
  benchmark, the option-adjusted spread of the band the bond was issued into,
  and the residual — the issuer-specific move. A product serving only their
  total would report a market-wide widening as a deterioration. Scenario 3 is
  the measured case: the headline moves **+166.6 bp** while the residual moves
  **+1.5 bp**, and 22 of the 30 rated obligors show the same pattern over that
  window.
- **The instrument is the observation unit.** A bond is what trades; an
  obligor-level spread is a mean over instruments that may be pricing different
  things. The anchor's two bonds have medians of 29.0 and 29.5 bp — normally
  indistinguishable — and on the same day one reaches **8.0×** its own median
  while the other reaches **1.3×**. Averaging first halves the peak and erases a
  term-structure signal. That was found at Gate 2 against the approved spec, and
  Gate 1 was reopened for it (`CP10-F-06`).
- **A ninety-fold half-life spread inside one product.** Spreads decay on a
  1-day λ_c, internal grades on 90 days. They are separate entity classes,
  because the reference debt scorer types an observation by its class — one
  class would price a daily quote and a quarterly grade identically.
- **Freshness reads the leading edge of each series, not its history.** This
  product keeps years of daily quotes on purpose. Averaging freshness over all
  of them drove `F` to **0.004750** and the product to `fail_closed` with a
  two-day-old newest quote. The fix is an SDK ruling, `D-IMPL-333`: a λ_c row
  declares `freshness_over: leading-edge` and a `series_key_attribute`, and `F`
  ranges over the newest quote **per bond** at or before `as_of` plus the grade
  in force. 996 observations in the view, **two** entering `F`. See `CP10-F-07`.
- **Two clocks on every grade, both served.** When a grade took effect
  (`validFrom`) and when the system learned it (`assertedAt`) are different
  facts; this estate's booking lag runs 1–5 days. The anchor's downgrade took
  effect 2025-03-17 and was booked four days later.
- **A confirmation is three separate tests.** Later, a downgrade, **and**
  off-cycle — each reported on its own. Temporal proximity alone is not
  confirmation: quarterly reviews land every ~90 days, so some review is near
  any date. My own Gate-1 measurement found six "confirmations" this way where
  there is one, and that failure is recorded as TRAP 2.
- **An honest basis, reported rather than corrected.** The market leg is netted
  on `static_issue_band`. Two of 30 obligors have left their issue band, so for
  them the residual is less precise — and the product says so. It must not
  infer a replacement band from the internal grade: that would make the market
  component a function of the grade the divergence is measured against, and a
  residual computed that way could not disagree with it (`CP10-F-04`).

**Illustrative calibration.** This example runs against a point-in-time
demonstration estate rather than continuously refreshed production data.
Freshness half-lives and related thresholds are calibrated to make the governed
behavior observable in that snapshot. They demonstrate how the SDK applies these
controls and should not be interpreted as recommended production coverage-policy
thresholds.

**This product consumes no agency ratings and no TRACE data**, and both were
verified rather than assumed. No agency column exists in any of the estate's 118
tables; the internal scale is `synthetic — internal`. Instrument identifiers are
`syn-i-*` and the issuer-specific spread is a **residual**, not an observed
trade. An SDK example ships with the SDK and is copied by adopters, so licensed
values in one would be redistribution exactly as in a product.

## Run it

The example reads the live estate. Four variables, and **the namespaces are the
v2 ones, which are not in the estate's own `.env`** — that file names v1:

```bash
export CCF_CP_10_POSTGRES_DSN='postgresql://<user>:<pw>@192.168.4.76:5432/parkavedb'
export CCF_CP_10_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_10_FLUREE_URL=http://192.168.4.76:8090
export CCF_CP_10_FLUREE_LEDGER=fibo-v2

make -s example-cp-10
```

Every request parameter is optional. Omitted, the program asks the
demonstration question in `artifacts/question.yaml` — an anchor, a window and a
divergence threshold are **request** parameters, and a build tool is not a
request channel.

The three scenarios `CP-SPEC-010` §D.4 declares:

```bash
# 1 — the confirmation. The market moved; the credit file followed 96 days later.
make -s example-cp-10

# 2 — a standing disagreement. A bond 7x its own median; a grade that never moved.
make -s example-cp-10 LEI=529900VKCYZW8GZ4WW58

# 3 — the market move that is not a deterioration. No episode, and the reason.
make -s example-cp-10 LEI=549300TRW1LZMDJZAQ78 \
    AS_OF=2025-04-07T00:00:00+00:00 WINDOW_DAYS=48 GRANULARITY=daily
```

And the governed refusal, which is an answer rather than an error. `D_c` is
0.3651 on the anchor, so a caller declaring a lower ceiling gets a refusal that
arrives as **data** — not an exception, so a client cannot swallow it:

```bash
make -s example-cp-10 DEBT_TOLERANCE=0.10
```

## The story

Celanese Corp, `549300FHJQTDPPN41627`, over the two years to 2026-08-20.

On **2024-12-11** the issuer-specific spread on the five-year bond
`syn-i-b23153` peaks at **233.245 bp** — **8.039×** that bond's own 29.015 bp
median, with the market component already netted out. The obligor's internal
grade that day is **BB**.

The 25-year sibling `syn-i-f87e69` reaches 37.378 bp on the same day: **1.27×**
its own median. **No episode.** The concern is entirely at the short end, and an
obligor-level average would have reported a single blurred figure for both.

The credit file follows on **2025-03-17**: **BB → BB-**, **96 days** later,
**off-cycle**, with the trigger recorded in the file's own words — *"ad hoc
credit review following sustained spread widening in the obligor's traded
debt."* That assertion was booked on 2025-03-21, four days after it took
effect, and the product reports the lag as a figure.

Three separate tests say this is a confirmation rather than a coincidence: the
change is **later** than the peak, it is a **downgrade**, and it is
**off-cycle**. Drop any one and the verdict changes — which is why all three
are in the payload rather than a single boolean.

Scenario 2 is the same machinery returning the opposite answer. Sabre's
`syn-i-4d322a` peaks at **282.633 bp**, **7.004×** its own median, and the grade
stays `B` through two later reviews. That is a **standing disagreement**, not
missing evidence — and telling those two apart is `CP10-F-08`, a defect found at
Gate 2 when the product reported a rated obligor as unrated.

Scenario 3 is the error pointing the other way. Over `2025-02-18 → 2025-04-07`
every band widened together — `B` +165.0 bp, `BB` +150.5, `BBB` +51.2, `A`
+36.0, `AA` +28.9. B&G Foods' headline moved +166.6 bp and its residual +1.5 bp.
All three signals agree nothing happened to this obligor, and the product
reports **no episode**.

## Artifact-by-artifact

| file | what it carries |
|---|---|
| `ccf_config.yaml` | the Control Plane document. Four entity classes, the two λ_c rows and their `decay_basis` / `freshness_over` / `series_key_attribute`, the operator parameters, the request contract, the debt profile, and the identity of the one declared product gate. Delete it and `produce.py` has nothing to interpret. |
| `artifacts/question.yaml` | the demonstration question, in the caller's vocabulary. The `as_of` pin lives here because it is a request parameter. |
| `artifacts/source-vocabulary.yaml` | the source terms this deployment reads, named once. |
| `artifacts/gates.yaml` | all 24 declared gates, each with its executing test, its sabotage and the observed result. |
| `backends.yaml` | where the fabric's own L3 lives for a run. Never a source store. |
| `acquisition.py` | the two source legs and the window bound at `asked_at`. Nothing later than the decision instant is read on either. |
| `deployment.py` | this deployment's own values: the request shape, the envelopes and their ingestion order, the measured `C` and `S`, and the deployment half of the one declared gate. |
| `projection.py` | Π. Per-bond series, episode detection, the three-part confirmation test, the derived summary with its dispersion, the series register and the band-migration report. |
| `produce.py` | the spine. Boot, acquire, govern — and nothing else. No binder, no local gates, no replay record, no debt scorer. |
| `run.py` | the client. Asks one question and prints what came back. |

## Whitepaper / CLAUDE.md sections exercised

- **§7.7 Context Half-life and Context Debt** — two classes ninety-fold apart in
  one product; `decay_basis: valid-from` on both; `freshness_over: leading-edge`
  so `F` measures the current state rather than the archive's length.
- **§7.3 the T axis's two clocks** — `validFrom` and `assertedAt` served
  separately, with the booking lag as a figure.
- **§7.4 / §7.5 operators and projection** — a policy operator scoping the
  subgraph to the admitted obligors, a typed-neighborhood traversal, and a Π
  that computes the divergence the answer is made of.
- **§7.6 the Context Product Contract** — the four §6.3 axes as `ProductRequest`
  fields; `ProductLineage` as exactly three fields; TTL anchored on the decision
  instant.
- **CLAUDE.md §6.4 the No-Hardcoding Rule** — every domain value is in
  `ccf_config.yaml` or under `artifacts/`.
- **CLAUDE.md §9** — the curated estate is evidence: both legs are read live,
  nothing is written, and the illustrative calibration is disclosed at every
  site that carries it.

## What to change first

**`divergence_multiple`.** It is a multiple of *each bond's own* median, never
an absolute basis-point figure — 100 bp means one thing at `AA` and another at
`B`, and one thing on a 2-year and another on a 25-year. Lower it and more bonds
produce episodes; raise it and the anchor's 8× survives while the sibling's 1.3×
still does not. That is the fastest way to see why the baseline has to be
per-subject.

After that: the two `half_life_seconds` rows, to watch `D_c` move; and
`granularity`, to see resampling take the last real observation in each bucket
rather than inventing a midpoint.

## What would fail

- **Summing the three spread components.** The product's entire subject is
  *which* of the three moved. `RSM-G07` asserts the total is **absent**, not
  merely that the parts are present — a payload carrying both still hands a
  reader the number that destroys the signal.
- **Averaging bonds before detection.** The anchor's peak halves and the
  term-structure signal disappears. `RSM-G09` asserts the episode's baseline is
  not the obligor blend.
- **Deriving the market band from the internal grade.** It would make the market
  component a function of the grade, and the residual could then never disagree
  with the grade — which is the only thing this product is for. `RSM-G23`
  asserts the reported issue bands match the *instruments'* own.
- **Averaging freshness over the archive.** `F` becomes a measure of how much
  history was kept rather than how old the answer's evidence is. Measured:
  0.004750 against 0.664139, and `fail_closed` against `ok`.
- **Reporting the current grade at a past peak.** The downgrade this product
  exists to detect would be erased — the peak would show `BB-` and there would
  be nothing left to confirm.
- **Collapsing "not rated" and "rated but unchanged".** Scenario 2 becomes
  indistinguishable from missing data, and a standing disagreement reads as an
  absence of evidence.
