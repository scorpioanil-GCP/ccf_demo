# CP-16 — ABS / Securitization Surveillance

**Rung 16 of the Context Product ladder.** How one securitization is
performing, from loan level up through the waterfall — and what asking that
question at greater detail actually costs.

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

---

## What this demonstrates

**Three things the first nineteen rungs did not prove**, none of which needed a
new SDK symbol:

1. **A request parameter that is a shape lever, a cost lever, and the thing a
   role ceiling bounds — all at once.** `granularity` decides the payload's
   members, the assembly's cost band, and is what the caller's credential is
   allowed to bound. A request above the ceiling is **refused by name with the
   bound attached**, never quietly lowered.
2. **Assembly that must not materialize the population it reads.** The loan leg
   carries **1,322,453 rows**; one deal-period is 35,814. The aggregation or
   the sample happens *in acquisition*, before any claim is minted.
3. **The cost of the caller's own question, served back to the caller** — so an
   agent can reason about asking for more detail instead of always choosing
   maximum depth.

It is also the first rung to exercise **residual `341-1`**: acquisition bounded
at the *decision instant* rather than at request time.

## The demonstration, in one contrast

`SDART-2022-6` is the one deal in the estate carrying a **trigger amendment**.
Its published delinquency runs 9.98 %–11.30 % across twelve periods.

| asked at | in-force delinquency trigger | distance | anchored? |
|---|---:|---:|---|
| `2025-09-30` | **24.00 %** (original) | ~13.4 points | yes — filed prospectus text |
| `2026-06-30` | **13.50 %** (amended) | **2.32 points** | **no** |

Evaluating a 2026 pool against the 2022 definition is the anachronism this rung
exists to refuse. And the filed servicer report *still publishes 24.00 %* in
every period, so the product serves **both** the in-force definition and the
filed figure rather than silently preferring one.

## Route B — the unanchored threshold

The amendment is the only one of the estate's eleven trigger definitions with
**no prospectus passage**, because it was engineered and never filed. Dave
ruled (2026-09-21) that it is **served, marked**, not refused and not invented:

- `anchored: false`, classified `engineered`, and named in
  `unanchored_thresholds` and in `findings`;
- **nothing in the payload implies a passage exists** — no empty anchor object,
  no null `passage_id`, no placeholder document id;
- the anchoring invariant is **split in two** so neither half can satisfy the
  other: `ABS-G06` (every publicly sourced threshold anchors and re-hashes) and
  `ABS-G07` (every threshold without a public anchor is named unanchored).

**No prospectus text is minted.** The absence is stated.

## Cost is blocks and records — never time

The estate's own 24 timed runs put `cohort`'s median between **0.148 ms and
205.871 ms** on identical data while its block count never moved off 2. Its
worst run is 4.9× slower than `loan`'s best. **A time-keyed cost gate would
invert the ordering this rung teaches**, so every cost assertion is keyed on
blocks and records, and the measured counts travel as stamped evidence rather
than as thresholds anything is compared against.

The sharpest measurement is counter-intuitive and is why *both* numbers matter:

| approach | rows materialized | blocks | representative? |
|---|---:|---:|---|
| full partition | 35,814 | 1,849 | yes, but materializes the pool |
| prefix `LIMIT` | 200 | **16** | **no** — the cheap option is the forbidden one |
| deterministic stride | 166 | 1,849 | **yes** |

**Sampling saves materialization, not blocks.** Rows alone would have called the
prefix a 178× win.

## Running it

```bash
export CCF_CP_16_POSTGRES_DSN=...   CCF_CP_16_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_16_FLUREE_URL=...     CCF_CP_16_FLUREE_LEDGER=fibo-v2
export CCF_CP_16_MONGO_URI=...      CCF_CP_16_MONGO_DB=fibo_v2
export CCF_CP_16_TOKEN_DESK=...     CCF_CP_16_TOKEN_RISK=... \
       CCF_CP_16_TOKEN_REPORTING=... CCF_CP_16_TOKEN_UNGRANTED=...

make -s example-cp-16
make -s example-cp-16 GRANULARITY="--granularity cohort" PRINCIPAL="--principal PRIN-CRR-002"
make -s example-cp-16 GRANULARITY="--granularity loan" LOAN_SAMPLE="--loan-sample 300"
make -s example-cp-16 AS_OF="--as-of 2025-09-30T00:00:00+00:00" ASKED_AT="--asked-at 2025-09-30T00:00:00+00:00"

.venv/bin/python examples/cp-16-abs-securitization-surveillance/run.py --door
```

**`as_of` is both the reporting period and the decision instant**, so a
historical question is *decided* at the instant it asks about. Holding
`asked_at` at today while moving `as_of` back asks for a product whose
evidence-anchored expiry is already months past, and it is refused.

## The three principals

| credential | role | ceiling |
|---|---|---|
| `CCF_CP_16_TOKEN_DESK` | `structured-finance-desk` | `loan` |
| `CCF_CP_16_TOKEN_RISK` | `credit-risk` | `cohort` |
| `CCF_CP_16_TOKEN_REPORTING` | `client-reporting` | `deal` |
| `CCF_CP_16_TOKEN_UNGRANTED` | — | granted nothing (negative control) |

A role's **shape** follows its ceiling: `client-reporting` carries no
`cohort_performance` member at all, because an empty one would read as *this
deal has no cohorts* rather than *you may not ask*.

`granularity=loan` requires a positive `loan_sample`. The product refuses
`unbounded-loan-request` rather than accepting an instruction to materialize a
1.3-million-row population.

## What to change first to adapt it

- `artifacts/perspectives.yaml` — the roles, their ceilings, and the member set
  each granularity carries. `ABS-G11` checks this against the estate's own
  entitlement rows, so the two authorities cannot drift apart silently.
- `artifacts/source-vocabulary.yaml` — every table, collection and predicate
  this deployment reads, plus the four loan attributes the privacy constraint
  restricts.
- `ccf_config.yaml` — the λ_c table (two observation types: `supersede-only`
  for standing state, `decay_basis: valid-from` for dated events), the operator
  parameters, and `argument_domains`.
- `acquisition.py` — the readers. This is where the ceiling is resolved first
  and where the fan-out is bounded.

## Known limitations

All measured and classified in `FINDINGS.md`. The ones a reader meets first:

- **`blocks_scanned` costs a second execution.** It is read by
  `EXPLAIN (ANALYZE, BUFFERS)` on the same statement, and explaining a statement
  runs it. A production deployment would sample rather than measure every serve.
- **The loan sample is uniform, not band-stratified**, because the
  stratification key derives from a field the estate restricts to cohort
  granularity — stratifying by it would disclose a score bucket per loan.
- **Repurchase activity is depositor-scoped.** ABS-15G covers a whole shelf, so
  a deal with no repurchases has no filing of its own to be absent. No per-deal
  join is invented.
- **A subject with no evidence at the instant is refused, not served empty** —
  and the refusal is uniform, so it is not an existence oracle.
- **The estate's passages carry embeddings the SDK cannot yet use.** The lexical
  operator is used instead; recorded as a backlog item.

## Gates

22 declared gates, `ABS-G01`..`ABS-G22`, in `artifacts/gates.yaml`, each claimed
by an executing test under `tests/examples/test_cp_16_*.py`. **21 observed red**
under their own sabotage; **one `unavailable`** with its guard named —
`ABS-G01`, because `CATEGORY_ORDER` in the SDK's planner fixes the executed
operator order and the forbidden ordering is unreachable from a deployment.

## Specification

`spec/CP-SPEC-016_ABS_Securitization_Surveillance.md`, authored to Context
Product Specification Standard v0.3 before any code existed, with Dave's Gate-2
ruling folded in at §F.4.
