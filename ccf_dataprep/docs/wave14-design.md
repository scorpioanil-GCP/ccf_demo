# Wave 14 — `abs-securitization-surveillance`

**Tier 4 · Postgres + Fluree + MongoDB · the catalog's fan-out stress test**

Everything numeric below was measured against live EDGAR on 2026-08-22, not
estimated. Where a figure is an extrapolation it says so and names the
extrapolation.

---

## 1 · Why this wave is different

Every prior wave was bounded by *finding* the data. This one is bounded by
*carrying* it. The largest table this project has loaded to date is
`sanctions_name` at 45,511 rows, and before this wave the entire `parkavedb`
was 112 MB across 86 tables. Wave 14's loan table alone is **1,322,453 rows and
608 MB** (measured 2026-08-23; the pre-load estimate of "roughly 1.2 GB" was
out by ~2×, and the database now stands at 721 MB across 97 tables) —
an order of magnitude more than everything built so far, in a single table.

That is deliberate and it is the point. §F requires loan records "at genuine
ABS-EE scale, so fan-out cost is **measured rather than estimated**", and §F's
final bullet names the measured cost curve as "this product's most valuable
output for the SDK". Sampling the pool down would satisfy every row count in
the spec and destroy the one thing the product exists to demonstrate.

**Decision, 2026-08-22 (user):** load full fidelity — all three deals, all
~72 ABS-EE fields, all 12 periods. Raw XML retained on disk (gitignored) so
the load is re-derivable.

---

## 2 · Deal selection — proposed and approved 2026-08-22

CLAUDE.md requires public anchors to be proposed before loading. These three
were selected by inspection of EDGAR and approved.

| Deal | CIK | Credit | Vintage | Servicer |
|---|---|---|---|---|
| Santander Drive Auto Receivables Trust 2022-6 | 1943670 | subprime | 2022 | Santander |
| Toyota Auto Receivables 2022-B Owner Trust | 1914281 | prime | 2022 | TMCC |
| Santander Drive Auto Receivables Trust 2024-1 | 2004812 | subprime | 2024 | Santander |

**Why this mix and not another.** Three things had to hold simultaneously,
and only this combination holds all three:

- **A real trigger trajectory.** Prime deals never approach their triggers —
  their proximity is a flat line, and §F asks for "a trajectory rather than a
  static distance". The subprime deals move. Without one, §F's trigger
  condition would have to be engineered.
- **A vintage comparison.** SDART 2022-6 against SDART 2024-1 is the same
  shelf, same underwriting, same servicer, two vintages — the clean
  comparison the "benchmark performance by asset class and vintage" element
  needs.
- **Servicer variance.** §B names servicer variance as a measure. It needs at
  least two servicers, which the Toyota deal supplies.

The same-vintage pair (SDART 2022-6 / TAOT 2022-B) additionally gives a
prime-versus-subprime contrast at one point in the credit cycle, which is what
makes the vintage benchmark interpretable rather than merely computed.

### 2.1 The reporting window

All three deals file monthly and share **31 common reporting months**
(2023-12 → 2026-06). The wave loads the **latest 12 common months, 2025-07
through 2026-06**.

Common-window alignment matters more than recency: a vintage benchmark that
compares deal A's July against deal B's September is not a benchmark. The
window is fixed by reporting period (`reportDate`), never by filing date —
the two differ by 2–7 weeks and vary by filer.

---

## 3 · Sources — all verified reachable 2026-08-22

| Source | Form | Count | Volume | Store |
|---|---|---|---|---|
| Loan-level asset data | **ABS-EE** EX-102 XML | 36 files | **~5.4 GB** | Postgres |
| Deal prospectus, tranche structure, trigger definitions | **424B5** | 3 | ~2.5 MB | MongoDB + Fluree |
| Servicer distribution reports | **10-D** EX-99.1 | 36 | ~7 MB | MongoDB + Postgres |
| Repurchase and R&W activity | **ABS-15G** | depositor-level | small | Postgres |

**ABS-15G is filed by the depositor, not the trust.** Neither Santander trust
files one; the shelf's activity sits under Santander Drive Auto Receivables
LLC (CIK 1383094, 6 filings) and Toyota Auto Finance Receivables LLC
(CIK 1131131, 44 filings). A per-trust search returns nothing and would read
as "no repurchase activity" rather than "wrong CIK" — this is the wave's most
plausible silent-empty failure.

**Corrected 2026-08-23.** An earlier reading here said Santander co-files
ABS-EE and 10-D in a single accession. Measured across all 36 loaded periods,
`absee_accession != servicer_accession` in **every** case, for all three
deals. What is true is narrower: Santander's 10-D accession *also* carries a
copy of the EX-102 loan XML alongside its EX-99.1, so the same loan file is
reachable from two accessions. The fetcher resolves per form dynamically
rather than assuming either layout.

**And the document list must come from the submission header, not
`index.json`.** EDGAR's `index.json` for Toyota accession
0001193125-26-322407 omits `d70261dex991.htm` — the EX-99.1 servicer
certificate — while listing Santander's correctly. The file fetches fine
(HTTP 200, 140 KB) and appears in the submission header as SEQUENCE 2. A
resolver trusting `index.json` therefore works for two deals of three and
reports "no servicer report" for twelve straight Toyota periods, which reads
as a data problem rather than a resolution bug.

### 3.1 Measured volumes — the pool shrinks, so period matters

Asset counts were measured at both ends of the window, not sampled once.
Sampling only the latest file understates the load by about 21%.

| Deal | 2025-07 | 2026-06 | 12-period estimate |
|---|---|---|---|
| SDART 2022-6 | 44,251 (164 MB) | 35,814 (132 MB) | ~480,000 |
| SDART 2024-1 | 48,833 (182 MB) | 36,793 (136 MB) | ~514,000 |
| TAOT 2022-B | 35,272 (122 MB) | 19,430 (72 MB) | ~328,000 |
| **Total** | | | **1,322,453 (actual, Task 5 load)** |

The 12-period figures are **linear midpoint extrapolations from the two
measured endpoints**, not counts. Amortizing pools decay close to linearly, so
the estimate should land within a few percent — but the loader records the
true per-period count and the design doc gets corrected from that, not the
other way round.

**ABS-EE reports more assets than remain in the pool.** SDART 2022-6's
servicer report shows 22,738 receivables outstanding while its EX-102 carries
35,814 asset records, because recently-zero-balanced loans continue to be
reported. The loan table is therefore a *(deal, period, asset)* fact table
whose grain includes paid-off and charged-off assets — not a roster of live
loans. Any pool-balance measure that counts rows rather than summing balances
will be wrong by roughly 60%.

---

## 4 · Store partition

Single-writer discipline. Each element has exactly one owner.

**Postgres** — `E`, benchmarks, policy reference

| Table | Rows | Provenance |
|---|---|---|
| `abs_deal` | 3 | public |
| `abs_loan_period` | 1,322,453 | public |
| `abs_tranche` | 18 | public |
| `abs_servicer_report` | 36 | public |
| `abs_repurchase` | 8 | public |
| `abs_cohort_performance` | 132 | public |
| `abs_vintage_benchmark` | 36 | public |
| `abs_holding` | 6 | **synthetic — internal** |
| `abs_granularity_entitlement` | 3 | **synthetic — internal** |
| `abs_materialization_policy` | 4 | **synthetic — internal** |
| `abs_cost_measurement` | 4 per stored run | *(no provenance column — see below)* |

Corrected 2026-08-23 against the loaded stores; the earlier version of this
table was wrong in four places. It listed `abs_tranche_state`, which does not
exist — the table is `abs_tranche`. It labelled the two materialized
aggregates `derived`, which is **not one of CLAUDE.md's three classes** and is
not what the rows actually carry: both store `public`, correctly, because each
is a pure function of public filed loan data with nothing invented. It gave
`abs_cost_measurement` a fourth class, `derived — measured`; RULING F43
removed that column instead, since a measurement is not a data element *with*
a source, it *is* one — `measured_at`, `row_basis` and `repeats` record its
origin. And it omitted `abs_granularity_entitlement` entirely.

**Fluree** — `R`, `T`, policy binding

Deal → tranche structure via `isCollateralizationOf` and `isSubordinatedTo`; trigger
definitions via `specifiesTrigger` → `TriggerEvent`; **trigger threshold
assertions carrying effective dates**, which is what makes as-of evaluation
mean anything; loan-level privacy constraints (`P`).

Per the single-writer rule, Fluree nodes carry identity and structure only.
Every threshold *value* and every performance measure resolves from Postgres
or MongoDB.

**MongoDB** — passage-level `L`

Prospectus text (3), servicer report text (36), and passage spans with
offsets and embeddings. Every trigger threshold must resolve to the prospectus
sentence that defines it — §D's validation gates name trigger anchoring
explicitly, and a threshold without a passage anchor "is a number nobody can
defend to a committee".

**SQLite and Neo4j are not touched.** Nothing in §C assigns them an element.

---

## 5 · §F conditions — what is real and what is engineered

| # | §F condition | Source | Status |
|---|---|---|---|
| 1 | 2–3 real deals × 12 monthly periods | ABS-EE | **real** — 3 deals, window fixed |
| 2 | ~20,000 loan records per deal per period | ABS-EE | **real** — 19,430–48,833 measured; see the note below |
| 3 | ≥ 4 tranches | 424B5 | **real** — 6, 6 and 6 measured |
| 4 | ≥ 3 trigger definitions anchored to prospectus passages | 424B5 | **real** — delinquency, overcollateralization, reserve (plus a yield-supplement anchor on TAOT). No cumulative-net-loss trigger is filed by any of the three. **Thresholds and wording differ by issuer — see 5.3** |
| 5 | ≥ 1 trigger approaching its threshold across the series | ABS-EE + 10-D | **real** — see 5.1 |
| 6 | ≥ 1 trigger definition amendment | — | **synthetic — engineered** — see 5.2 |
| 7 | Vintage benchmarks across the loaded deals | derived | **public** — a pure function of filed loan data. Keyed `(asset_class, vintage, period)`; keying on `credit_tier` too made every cell a cohort of one |
| 8 | ≥ 1 principal restricted to aggregate-only granularity | internal policy | **synthetic — internal** |
| 9 | Measured cost figures at each granularity | measured | *(no provenance column — a measurement is a source, not a sourced element; see §7)* |

**Condition 2 is approximate on purpose, and one measurement sits just under
it.** The floor reads "~20,000", and TAOT 2022-B's final window period carries
19,430 assets — 570 short of a literal 20,000. Every other deal-period in the
window is above it, most far above. The condition is read as the spec writes
it, approximately, and the gate records the true per-period minimum rather
than asserting a threshold the spec did not set. Recording this here so nobody
later "discovers" the shortfall and quietly samples a different window to hide
it: the number is 19,430, it is real, and it is fine.

### 5.1 The trigger trajectory is real — condition 5 needs no engineering

SDART 2022-6's prospectus defines, in its defined-terms article:

> "*Delinquency Trigger*" means, for any payment date and the related
> Collection Period, **24.00%**.

The servicer report publishes the measured side. Read across the deal's life:

| Reporting date | Cumulative net loss |
|---|---|
| 2023-02 | 0.48% |
| 2023-08 | 3.66% |
| 2024-02 | 6.25% |
| 2024-08 | 7.97% |
| 2025-02 | 9.71% |
| 2025-08 | 10.65% |
| 2026-02 | 11.74% |
| 2026-08 | 12.23% |

and delinquency percentage stands at **10.79% against the 24.00% trigger** in
the most recently filed period (reporting month 2026-07, one month past the
loaded window), rising as the pool amortizes. That is a trajectory, and it
comes out of real filings.

The figures above are the servicer's published numbers, cited here as evidence
that the condition is satisfiable. **The loaded series is recomputed from loan
level across the 12-period window** — these are not the values the gate reads.

This matters beyond convenience. An engineered trajectory would have been
plausible and cheap, and it would have taught the wrong lesson — a consumer
could learn the shape of our generator instead of the shape of a real
amortizing subprime pool.

### 5.3 The 24.00% threshold is Santander's, not the industry's

**Correction, measured 2026-08-23.** An earlier reading of this wave recorded
"the 24.00% Delinquency Trigger stated in all three defined-terms articles".
That is wrong, and wrong in a way worth writing down rather than quietly
fixing.

| Deal | Term as the prospectus writes it | Threshold |
|---|---|---|
| SDART 2022-6 | "*Delinquency Trigger*" **means** … 24.00% | 24.00% |
| SDART 2024-1 | "*Delinquency Trigger*" **means** … 24.00% | 24.00% |
| TAOT 2022-B | The "*Delinquency Trigger Percentage*" **will equal** 4.65% | **4.65%** |

Three differences, each able to produce a confidently wrong number:

1. **The value.** Toyota is prime; its trigger is a fifth of Santander's, and
   its measured delinquency sits at 1.31% against it.
2. **The defined term.** Toyota defines *Delinquency Trigger Percentage*, not
   *Delinquency Trigger*.
3. **The verb.** Santander uses `means`; Toyota uses `will equal`. An
   extractor keyed on `means` finds nothing in the Toyota prospectus.

**And there is a trap underneath.** `24.00%` *does* appear in Toyota's
prospectus — as the upper bound of the receivable-eligibility APR range
("APR 0.00% to 24.00%"). A regex that searches the Toyota document for a
percentage near the words "Delinquency Trigger" can land on an underwriting
criterion and bind it as a performance trigger. The data would be real, the
account of it wrong, and every downstream proximity calculation would be
against a number that means nothing of the sort.

So trigger extraction asserts its result per deal — 24.00 / 24.00 / 4.65 —
rather than trusting a pattern to have matched the right sentence.

### 5.2 The amendment must be engineered — and labelled

Auto ABS trigger definitions are fixed at issuance. Across 135 ABS-EE periods
and 3 prospectuses there is no amendment to find, and there will not be one.
So condition 6 is **`synthetic — engineered`** and is recorded as such in
every store that carries it.

**Shape.** One amendment to SDART 2022-6's Delinquency Trigger, asserted in
Fluree as a superseding threshold with:

- an **effective date** inside the loaded window,
- an **assertion date** materially later than the effective date,
- a **new threshold low enough that the real, unmodified delinquency series
  sits close to it** — so proximity changes character rather than merely
  changing by a constant.

The demonstration is that three questions return three different answers
against the same ledger:

| Question | Answer |
|---|---|
| What is the threshold today? | the amended value |
| What was the threshold as of a date before the effective date? | 24.00% |
| What did we *know* the threshold to be, as of a date after the effective date but before the assertion date? | 24.00% |

The third is the one that matters and the one a mirroring pipeline loses.
It is the same mechanism `covenant-in-force-as-of` proves with booking-lag
amendments, applied to a trigger.

**The engineered value must never be presented as filed.** It carries
`provenance = 'synthetic — engineered'` in Postgres, a distinct assertion
source in Fluree, and it anchors to **no** prospectus passage — because no
prospectus sentence says it. The trigger-anchoring gate must therefore treat
it as a known, named exception rather than silently passing it.

---

## 6 · The conditions most likely to be faked, and the gates that must bite

Wave 12's defect was checks that looked at nothing. Wave 13b's was checks that
counted the wrong quantity. Both shapes are available here, and the third —
reading a flag that states the answer — is unusually tempting because the
servicer publishes one.

**The servicer report contains a field literally named
`Delinquency Trigger Occurred: No`.** Reading it would satisfy condition 5
forever, at any input, without touching a single loan record.

So the gate recomputes, from three independent directions, and requires them
to agree:

1. **From loan level** — sum `reportingPeriodActualEndBalanceAmount` for
   assets 61+ days delinquent, divide by pool balance. This is the only
   derivation that would notice if the loan load were wrong.
2. **From the prospectus** — parse `24.00%` out of the defined-terms passage
   in MongoDB, by span offset, not by a constant in the validator.
3. **From the servicer report** — the published figure, used *only* as a
   cross-check.

Where (1) and (3) disagree beyond tolerance, that disagreement is surfaced,
not smoothed. A reconciliation break between the loan file and the servicer's
own arithmetic is a finding, not a bug in the gate.

**Unit discipline, per condition.** Each floor names a unit and the gate counts
that unit and no other:

| Condition | Unit counted | The wrong unit that would pass anyway |
|---|---|---|
| ≥ 4 tranches | distinct tranche instances per deal | tranche *mentions* in the prospectus |
| ≥ 3 trigger definitions | distinct definitions with a numeric threshold and a passage anchor | occurrences of the word "trigger" |
| ~20,000 loans per deal per period | asset rows for that (deal, period) | total rows across all periods ÷ periods |
| ≥ 1 trigger approaching | periods in the series with a *monotone* narrowing | a single period's distance |
| ≥ 1 principal restricted | principals whose effective ceiling actually differs from requested | principals with a policy row |

The last one is the Wave 13b shape exactly: a policy row that grants a ceiling
nobody ever hits is a label, not a constraint. The gate must issue the
aggregate-only principal's request at `granularity=loan` and prove the
returned granularity is lower than the one asked for.

---

## 7 · The cost curve

§F's final bullet is the product's stated deliverable and sits closest to the
scope boundary. **What is in scope is measuring our own data's fan-out** —
rows touched, bytes read, and latency for the canonical query at each
granularity, against the loaded stores. What is out of scope, per CLAUDE.md,
is the assembly that would consume it: no operators, no contract, no TTL.

`validators/abs_cost.py` measures, per granularity:

| Granularity | Reads | Expected shape |
|---|---|---|
| `deal` | one row from materialized deal state | flat, ~1 row |
| `tranche` | materialized tranche state | ~6–7 rows |
| `cohort` | materialized cohort aggregates | one query per requested cohort |
| `loan` | streamed loan rows for (deal, period) | 19k–49k rows |

The figures are written to `abs_cost_measurement` with the timestamp and the
row counts they were measured against, so a later re-measurement on more data
is comparable rather than merely different. The curve is **recomputed on every
run**, never read from a stored constant — a hard-coded cost table is the same
defect class as a hard-coded threshold.

### 7.1 The measured curve

Measured 2026-08-23, `uv run validators/abs_cost.py --repeat 5`, against
`SDART-2022-6` period `2026-06`, with **1,322,453 rows** in
`ccf_v2.abs_loan_period` as the row basis. `median ms` is the median of five
timed executions after an explicit warm-up; `blocks` is Shared Hit + Shared
Read taken from the top-level `EXPLAIN (ANALYZE, BUFFERS)` node, which carries
the accumulated subtree total.

| Granularity | Rows returned | Shared blocks | Median ms | × deal (time) |
|---|---:|---:|---:|---:|
| `deal` | 1 | 2 | 0.441 | 1.0× |
| `tranche` | 6 | 4 | 0.426 | 1.0× |
| `cohort` | 4 | 2 | 0.187 | 0.4× |
| `loan` | 35,814 | 1,763 | 40.472 | 91.8× |

**Fan-out: 35,814× in rows and 882× in blocks. Those two are the planning
numbers.**

Read the curve as three rungs and a cliff. `deal`, `tranche` and `cohort` are
indistinguishable from each other — all under a millisecond, all accessing two
to four blocks — because all three are materialized and the differences
between them sit below timing noise. The cost is not incurred gradually as
granularity descends; it is incurred entirely at the last step. That is what
the SDK needs: the only choice that costs anything is loan-or-not.

**Do not plan against the time multiple.** Six runs against identical data,
same deal, same period, same row basis, produced ratios of 91.8×, 251.6×,
99.7×, 54.9×, 72.1× and 142.1× — a 4.6× spread, because the denominator is a
sub-millisecond figure on the noise floor. Over the same six runs the block
counts were `2 / 4 / 2 / 1,763` **every time**, an 882× ratio with no
variation at all. The reproducible statement is the block ratio; the time
multiple is order-of-magnitude only, and quoting 91.8× as a planning number
would be wrong by up to 2.7×.

A note on the column name: `shared_blocks_accessed` is Shared Hit + Shared
Read taken from the top-level plan node, which carries the accumulated subtree
total. It counts index pages as well as heap pages — the loan plan's 1,763 is
1,677 heap plus 86 index — and it counts blocks, not bytes.

Two guards run after the measurement, and both must pass:

1. **Rows** — `loan` must return more rows than `deal`, or no fan-out exists.
2. **Blocks** — **each of the three** aggregate rungs must access under 25%
   of `loan`'s blocks. This is the guard that earns its keep. Guard 1 cannot
   see the failure its own rationale names: if an aggregate table were a
   *view* over `abs_loan_period`, its query returns the same row count, so
   guard 1 stays green while that rung silently rescans the pool.
   Falsified twice on 2026-08-23. Repointing the **deal** rung at
   `abs_loan_period`: rows stayed 1, block ratio **1.000**, exit 1. Then the
   case that exposed a first version of this guard which checked `deal`
   alone — leaving `deal` materialized and rescanning only in **cohort** made
   the curve *invert* (loan measured 0.3× the deal time) with both guards
   green. Now the guard takes the worst of the three, and that case fires at
   ratio **1.000**, exit 1.

A failed curve is **not stored**. The insert sits behind the guards, because
`abs_cost_measurement` has no verdict column — four rows from a broken run
would be indistinguishable from a good run, and the registered condition
counts `DISTINCT granularity` across the whole table, so they would satisfy
it forever.

---

## 8 · Build order

Each stage depends on the one before. Stages 3 and 4 are the long ones.

1. **Vocabulary check.** The securitization terms are already bound from Waves
   8 and 11c — `Tranche`, `AssetBackedSecurity`, `PoolBackedSecurity`,
   `StructuredFinanceInstrument`, `TriggerEvent`, `specifiesTrigger`,
   `TrancheType`, `AttachmentPoint`/`DetachmentPoint`, `DefaultRate`,
   `PrepaymentSpeed`, `WeightedAverageLife`, `Servicer`, and the do-not-bind
   entries for `Securitization` and `Waterfall`. **`isSubordinateTo` is the
   one term not yet verified** — confirm against the EDM Council source before
   generating against it, and bind it before use.
2. **Prospectus and servicer text → MongoDB.** Fetch, segment, span-offset,
   embed. Trigger definitions extracted with offsets, because everything
   downstream anchors to them.
3. **Loan-level ABS-EE → Postgres.** Stream-parse; `COPY` per (deal, period);
   **delete that period's rows before inserting**, never upsert.
4. **Tranche structure and trigger assertions → Fluree.** Including the
   engineered amendment, with its effective/assertion split.
5. **Aggregates.** Cohort performance, tranche state, vintage benchmarks —
   materialized tables refreshed by the loader, not views.
6. **Internal overlay.** Holdings, materialization policy, privacy
   constraints, the restricted principal. Extends the LEI ↔ `internal_client_id`
   crosswalk to the three trusts.
7. **Gates.** Conditions register rows; `abs_surveillance.py`;
   `abs_cost.py`; partition check extension.

---

## 9 · Risks carried in from prior waves

**Upsert over variable-length children (§14.10).** The loan table is precisely
this shape: a pool that shrinks period over period, keyed by (deal, period,
asset). An upsert-only loader leaves ghost assets from a larger earlier pool
and every query still works. Stage 3 deletes by (deal, period) first. This is
the single most likely way to produce a silently-wrong load here.

**Positional identity (memory: 4 loaders on main).** Stage 6 touches the
shared crosswalk, which is a table that grows. Verify no loader assigns
identity by row position before adding the three trusts.

**The Fluree post-write read race (§14.2).** Stage 4 writes then verifies by
counting. Use `ccf.fluree.stable_scalar`, which exists for exactly this and
which most loaders still do not use.

**Load time.** 5.4 GB of XML through a streaming parser into ~1.32M rows.
The loader must be resumable per (deal, period) so an interrupted run costs
one period, not the wave.

---

## 10 · Definition of done

1. Every §C element loaded, in the store §C names, with provenance recorded —
   and the three provenance classes distinguished, not two.
2. `deal_id` → CIK → trust resolves; loans key to (deal, period); tranches key
   to CUSIP; the three trusts appear in the crosswalk.
3. All nine §F conditions satisfiable by query, with condition 5 recomputed
   from loan level and condition 6 proving as-of and known-as-of diverge.
4. No element duplicated into a store that does not own it.
5. `isSubordinateTo` verified and bound; if any term is added, the vault
   mirror flagged in the response **and** a punch list sent through the
   exchange.
