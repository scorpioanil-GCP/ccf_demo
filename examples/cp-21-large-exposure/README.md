# cp-21 — Large Exposure / Concentration

**What it determines.** Whether one counterparty group's exposure fits inside
the limits that actually bind it — under a regulatory regime selected at the
determination instant, against a capital base whose units are not the units the
arithmetic needs, over a group that does not exist until this product derives
it.

**The specification is
[`spec/CP-SPEC-021_Large_Exposure_Concentration.md`](spec/CP-SPEC-021_Large_Exposure_Concentration.md)**
and it was written, reviewed and ruled on before any of this code existed.

```
make -s example-cp-21 CASE="--case breaching"
make -s example-cp-21 CASE="--case fits"
make -s example-cp-21 CASE="--case fits" NO_MITIGATION=--no-mitigation
make -s example-cp-21 CASE="--case basis" CONNECTION_BASIS="--connection-basis control"
```

---

## What this rung exists to prove

Rungs 01–20 proved a great deal about assembling governed context. This one is
about **regulatory arithmetic over a population nobody handed you**, and four
things it needs that nothing earlier demonstrated.

### 1. The group is DERIVED, and the basis that derives it changes the answer

There is no group registry. The connected group is the transitive closure of
the connection edges admitted by the caller's `connection_basis`, computed at
the ledger point — `control` walks control edges, `economic-dependency` walks
judgment-based edges, `both` walks both and is the default because it is the
conservative posture.

**The whole causal chain moves, and `LEX-G04` asserts all of it.** Measured on
Super Micro Computer, Inc., 2026-09-21:

| basis | members | facilities | commitment | headroom |
|---|---|---|---|---|
| `control` | 2 | 1 | $2.000bn | $12.788bn |
| `both` | 4 | 4 | $2.570bn | $12.218bn |

A different basis gives a different **membership**, therefore a different
**aggregate exposure**, therefore a different **headroom**. A product exposing
only control-based grouping computes a compliant-looking number against an
incomplete group — which is the *Context Starved* counterfactual this rung
exists to refuse.

### 2. The units trap, and why the gate is on the consequence

`bank_capital` is denominated in **thousands of dollars** — the FFIEC Call
Report convention, and legitimate source semantics. Read as dollars:

| reading | Tier 1 | 25 % limit | facilities breaching it single-handedly |
|---|---|---|---|
| raw, as dollars | $0.296bn | **$73,939,500** | **42 of 60** |
| normalized | $295.758bn | **$73.940bn** | 0 |

Three orders of magnitude, and nothing in the output says so. The product
normalizes at the acquisition boundary using a factor **declared in
`artifacts/source-vocabulary.yaml`** and never written in code, does not
rewrite the source table, and serves **both** figures with their units.

**`LEX-G06` does not gate on the conversion constant.** It gates on the
regulatory consequence: the estate carries two engineered proposals with their
own `expected_outcome` labels, and the product has to reproduce them. An
implementation holding the correct factor of 1000 and applying it to the limit
instead of the base still fails — that sabotage was run, and it went red.

### 3. A limit is a percentage of capital OR an absolute amount

Regulation O's limit is **$500,000** — five orders of magnitude below the
percentage limits beside it, and not expressible at all by a product that
assumed `percentage × capital`. The payload names the **rule form** for every
limit (`LEX-G09`), and the regime is an effective-dated artifact selected at
the determination instant **at both ends of its window** (`LEX-G05`): the
estate's CRR version carries an `effectiveTo`, and applying repealed law to a
2026 determination is refused.

### 4. The freshness asymmetry is disclosed, never resolved

Exposure is intraday. The capital base is a quarterly filing, **147 days old**
at the pinned instant. The product does four things it must not do — none of
them:

- it does not pretend capital is intraday;
- it does not age exposure to the capital date;
- it does not refresh capital to the exposure instant;
- it mints no single fused timestamp.

Instead the denominator's own `report_date` and `age_days` travel **with** the
ratio, and `freshness_asymmetry.resolved` says `false` out loud (`LEX-G14`).

---

## The determination, end to end

```
make -s example-cp-21 CASE="--case fits"
```

```
  capital    raw 295758000 usd_thousands  ->  $295.758bn usd
             authority: FFIEC Call Report — amounts reported in thousands of dollars
             reported 2026-03-31 · 147 days old at the determination instant

  regime     regime-version-pra-2022 · effective 2022-01-01 · percentage-of-capital
             limit $73.940bn (25.0% of eligible capital)
             cites crr-art-395-2021-12-31#... [resolved=true, hash_available=false]

  CONFLICT   limit `internal-appetite` is priced differently by two internal authorities:
               graph-limit-envelope: 5.0% = $14.788bn
               relational-limit-register: 15.00% = $44.364bn
             selected `graph-limit-envelope` by rule `most-conservative-internal-authority-binds`

  evaluation BINDS FIRST: `internal-appetite` (graph-limit-envelope)
  proposal   $59.400bn · basis assumption (a hypothetical, not evidence)
             regulatory outcome: FITS
```

and the same question with `--no-mitigation`:

```
               regulatory-large-exposure  counted $74.000bn vs $73.940bn breached=true
             regulatory outcome: BREACHES
```

**$60.5 million** — 0.08 % — is the whole margin, and recognizing the undrawn
relief is what crosses it. That is `LEX-G15`: `apply_mitigation` is not a flag
that travels, it is a flag that decides.

---

## What you should change first to adapt it

| To change | Edit |
|---|---|
| which stores and tables are read | `artifacts/source-vocabulary.yaml` |
| **the capital unit factor and its authority** | `artifacts/source-vocabulary.yaml` → `capital_units` |
| **which connection bases are admissible** | `artifacts/source-vocabulary.yaml` → `connection_bases`, and the matching `argument_domains` in `ccf_config.yaml` (`LEX-G03` asserts they agree) |
| who sees what | `artifacts/perspectives.yaml` |
| the demonstration anchors and instants | `artifacts/question.yaml` |
| operators, λ_c, TTL, debt thresholds | `ccf_config.yaml` |
| environment variable names | `ccf_environment.yaml` |

The code is thin and generic. **An example whose code would still run
meaningfully with its artifacts deleted has violated the No-Hardcoding Rule** —
and one such violation was found and fixed during this build (`LEX-F-07`).

---

## Illustrative calibration

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

Concretely (`D-IMPL-323`): the capital base is a quarterly filing 147 days old
at the pinned instant, so `default_debt_tolerance` is set to `0.98`. A tighter
tolerance would withhold every answer and demonstrate nothing. The staleness is
not hidden by that choice — it is what forced it, it travels with every ratio,
and it is the subject of `LEX-G14`.

---

## What this rung does NOT prove

**Composition.** `Q1` was ruled on 2026-09-21: CP-21 is a **single-class
producer** and builds no child trees. The six prerequisites the source
specification names are re-acquired here. **Composition over children remains a
named coverage gap** and CP-21 was deliberately not enlarged to close it.

**RWA and FFIEC 101 concentration reporting** are out of scope by §0.3, and a
**group registry** does not exist in this estate by design — deriving the group
is the capability under test.

**Rung 23's boundary is preserved** (`PEW-G18`): nothing in
`examples/cp-23-portfolio-early-warning` reads `limit_definition`,
`bank_capital` or a connection basis. Those are this product's inputs. Nothing
here reaches back into rung 23.

---

## Gates and findings

Twenty-one declared gates, `LEX-G01`..`LEX-G21`, in
[`artifacts/gates.yaml`](artifacts/gates.yaml). **All twenty-one were observed
RED under their own sabotage** on 2026-09-21 against the live estate; none is
`unavailable`. Four sabotages failed to redden on the first attempt and were
**corrected rather than swapped** — each is recorded as a finding, because each
was a defect in the proof machinery rather than in the product.

The findings, including three SDK-adjacent ones and four estate limitations,
are in [`FINDINGS.md`](FINDINGS.md).
