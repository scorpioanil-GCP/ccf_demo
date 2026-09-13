# cp-12 — what each run shows, what you would have missed, and how it works

Three readers are served here: a **technical product manager** deciding whether
this capability is worth having, an **engineer** who has to build or extend it,
and a **markets-operations SME** who knows what a break actually costs to work.
Each run below is given as *the output*, *what a conventional reconciliation
would have missed*, and *how the mechanism produces it*.

---

## Run 1 — the demonstration question

```
make -s example-cp-12
```

Four trades, at amendment 0, with clock alignment on, as of `2026-08-14`.

### The output

```
VERDICTS over 4 trades
  timing              1
  genuine             2
  not-evaluable       1
  no-break            0

TRD-W12-0002  USD/CAD  genuine        divergent=settlement  (estate designated timing)
TRD-W12-0004  GBP/USD  genuine        divergent=trading     (estate designated genuine)
TRD-W12-0124  AUD/USD  not-evaluable  divergent=trading     (estate designated timing)
TRD-W12-0424  USD/JPY  timing         divergent=risk        (estate designated timing)

context debt D_c 0.0572   signal ok
  F 0.9428  C 1.0000  S 1.0000
content address  e3bf887a…
```

### What you would have missed

**For the SME.** A reconciliation report gives you four breaks and a magnitude.
It does not tell you that on `TRD-W12-0004` all three systems observed at the
*same true instant* — 07:34:39, after correcting each system's own clock skew —
and that trading alone still reports a different rate. That trade needs a human.
It also does not tell you that `TRD-W12-0124`'s two observations are 31 hours
apart across a weekend, so any "timing explains it" story is unfalsifiable from
the data you have. **One of these four is worth an investigation, one is worth a
market-data question, and one cannot be adjudicated at all** — and the report
made them look identical.

**For the PM.** Four trades, four different dispositions, and the product says
which is which and why. The `estate designated` column is carried beside the
computed verdict deliberately: the product does not pretend to be the oracle, it
shows its work and lets you compare.

**For the engineer.** `D_c 0.0572, signal ok` is not the same claim as the
verdict. `D_c` measures how old and how complete the *evidence* is; the verdict
measures what the evidence *says*. They are separate models and they move
independently.

### How it works

`acquisition.py` reads both legs — PostgreSQL for the rates, Fluree for the
instants, joined on `obs-<trade>-<system>-<amendment>` — and admits nothing
recorded after `asked_at`. `deployment.py` writes each trade and each observation
into L3 through the single write handle, edges first and nodes last.
`projection.py` partitions the three systems into agreement groups at the
pip-normalised threshold, names the isolated one, and decomposes its variance
into a timing component and a residual — or refuses to.

---

## Run 2 — the break that current state has forgotten

```
make -s example-cp-12 COMPARE_AT=latest
```

### The output

```
TRD-W12-0002  USD/CAD  no-break
TRD-W12-0424  USD/JPY  no-break
content address  4a36c050…        (different from run 1)
```

### What you would have missed

**Everything.** Two of the four breaks are simply gone. Measured across the whole
designated population, **13 of 60 breaks are material at amendment 0 and
immaterial at the latest amendment** — the amendment reconciled the two systems,
and a reconciliation run against current state sees nothing at all.

**For the SME, this is the important one.** The break existed. Someone either
worked it or did not. A control function asking *"were there unworked breaks last
month"* against current state gets a clean answer, and the answer is wrong — not
because anyone lied, but because the question was asked of a state that has
forgotten.

**For the PM.** This is the difference between a reconciliation and an auditable
one, and it is worth noting that **neither state is privileged**. `compare_at` is
an explicit request parameter, both answers are served, and the value in force is
carried in the payload. The product does not choose for the caller.

**For the engineer.** The two answers have different content addresses, which is
what makes them separately replayable. The `as_of` bound is enforced in
`acquisition.acquire`, not in the selection — an observation recorded after the
decision instant is never admitted, so a "latest" reading pinned to a past
instant is a genuine reconstruction rather than today's state relabelled.

---

## Run 3 — the conventional reconciliation

```
make -s example-cp-12 NO_ALIGN_CLOCKS=1
```

### The output

```
TRD-W12-0002  USD/CAD  timing         total 4.14 = timing 5.47 + residual -1.33
TRD-W12-0004  GBP/USD  not-evaluable  — interval-below-tick-spacing
content address  b2aa51db…        (different from both)
```

### What you would have missed

`TRD-W12-0004` — the one trade that genuinely needs a human — **becomes
unanswerable**. With the correction on, the three systems' true instants are
identical, so the timing component is exactly zero and the whole 7.82-pip
variance is residual. With it off, the recorded instants differ by 47 seconds,
which is below the rate series' 5-minute resolution, and the product correctly
refuses to decompose.

**For the SME.** Three systems whose clocks run 0, +47 and −112 seconds apart
will manufacture apparent sequencing that is not there. Correcting for it is not
a nicety; it is what turns *"risk saw it first"* into *"risk and trading saw it
at the same moment."*

**For the PM.** `align_clocks` is in the request surface precisely so both can be
run and the difference measured — the conventional answer is available, and it is
visibly different.

**For the engineer.** The corrected instant never leaves the projection. It is
not a `valid_from`, not an `observed_at`, not a decay basis and not a Context Debt
term. What the λ_c table ages against is the instant the source *recorded*, so the
fabric's freshness figure does not become a function of this product's beliefs
about three clocks. An unaligned answer carries `corrected_at: null` rather than a
correction the caller declined.

---

## Run 4 — the scale error, in one trade

```
make -s example-cp-12 TRADES=TRD-W12-0424 SCOPE=TRD-W12-0424
```

### The output

```
TRD-W12-0424  USD/JPY  timing   total 5.34 pips = timing 6.20 + residual -0.86
```

### What you would have missed

The raw rate difference between risk and the other two systems is **0.0534**. Read
as though the pip were `0.0001` — the scale every other pair in this estate uses —
that is 534 pips and obviously wrong; read as a raw number against a 2-pip
threshold it is **0.0534**, and it passes silently. USD/JPY prices to `0.01`.

**For the SME.** Every JPY-crossed break disappears beneath any threshold, and
nothing in the output says so. 135 of the 500 trades in this estate are USD/JPY.

**For the engineer.** The scale lives in `artifacts/pip-scale.yaml` with its own
semver and provenance, and the artifact declares `no_default: true`. A pair the
artifact does not name is refused, not defaulted. The artifact is also
corroborated against the estate's own `fx_pip_size` table at read time, and a
disagreement is a refusal rather than a silent preference for either — because
either one being wrong is a finding.

---

## Run 5 — the refusal

```
make -s example-cp-12 DEBT_TOLERANCE=0.02
```

### The output

```
REFUSED      tolerance-exceeded
  reason     tolerance-exceeded
  detail     fulfillment was withheld because …
  replay     <content address>
```

### What you would have missed

A governed *no* is an answer. It arrives as **data**, not as an exception, so a
client cannot swallow it with a bare `except` — and the determination is preserved
in the replay record while the consumer's envelope discloses less than the fabric
recorded.

**For the PM.** This is the control that stops a stale reconciliation from being
acted on as a fresh one, and the caller sets its own ceiling.

---

## The three things this rung exists to teach

1. **The unit of analysis is chosen before the phenomenon is understood, and that
   is where the damage happens.** Three systems give three pairs. Every one of the
   60 break trades partitions two-against-one, so counting pairs reports 120
   breaks over 60 divergences — exactly `2.00×`, measured. Rung 10 showed
   averaging *destroying* a signal; this shows pairwise expansion *manufacturing*
   one. Same mistake, opposite direction.

2. **`not-evaluable` is a real answer and zero is not.** The rate series resolves
   to five minutes. Where the observation gap is shorter, a revaluation reports a
   zero timing component — and reading that as *the market did not move*
   misclassifies **22 of 60**. Where the nearest tick is 20 hours old, it reports
   a −72.49-pip residual on a raw variance of 5.15. The product refuses in both
   cases and says which.

   **And the converse mattered just as much.** A gap of *exactly zero* is not the
   same fact: two identical instants leave no interval, so the timing component is
   zero by arithmetic rather than by resolution. The first implementation
   collapsed the two cases and buried 20 breaks — which turned out to be precisely
   the 20 the estate designates genuine, 20 of 20 (`CP12-F-10`).

3. **A correction the product applies is not a clock the fabric keeps.** The
   clock offset is domain knowledge about three named systems. It belongs to the
   reconciliation and to nothing beneath it, and the payload carries the recorded
   instant, the offset and the corrected instant separately so a consumer audits
   the alignment instead of trusting it.
