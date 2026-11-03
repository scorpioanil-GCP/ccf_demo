# Wave 11b design — `credit-surveillance-early-warning`

**Spec:** `credit-risk.early-warning.v1` · Tier 3 · Postgres + Fluree, no new store
**Status:** designed 2026-08-20, not yet implemented
**Predecessor:** Wave 11a (`rating-and-spread-migration`), merged at `b89f9fd`

This product is the catalog's dedicated demonstration of **supersession as a
cascading policy event**. Steps 1–6 of its Assembly Recipe produce a warning
list; step 7 — one event invalidating every downstream product that touched the
affected entity — is why the product exists at all. Our job is to produce data
that makes step 7 *demonstrable*. We do not implement step 7. See CLAUDE.md,
§ *Explicitly out of scope*.

It is the first product in the catalog that composes **other Context Products**
rather than raw signals, which is precisely what gives the cascade something to
cascade through. All four prerequisites — `corporate-family-tree`,
`credit-exposure-rollup`, `rating-and-spread-migration`, `covenant-in-force-as-of`
— are already loaded.

---

## 0 · Decisions taken

Recorded here so they are not silently re-opened. Four were put to the user on
2026-08-20; the answers are as given, including where they went against the
recommendation.

| # | Decision | Outcome |
|---|---|---|
| D1 | Signal window | **24 months**, not §F's 18. Chosen so the ≥2-obligor Item 2.04 condition is met by *real, in-window* filings, with no reliance on reading "in their filing history" as history-wide |
| D2 | WARN sourcing | **Texas + California + one further state**, the third scoped during planning. TX+CA alone lands on §F's ≥3 floor with zero margin |
| D3 | Signal budget | **Load everything (~1,000+ events)**, not sub-selected to §F's ~400. User's call, made against the recommendation and with the trade-off stated. See §7.1 — the distribution condition is still *measured*, not assumed |
| D4 | GDELT source | **DOC API**, not the raw CAMEO event/mention stream. A TRACE-shaped substitution; see §2.3 |
| D5 | Item 4.02 | **Load the signal type with zero instances** and record the absence. Non-reliance filings do not exist in this cast in any window; manufacturing them would put synthetic rows in a `public` column |
| D6 | Cascade anchor | **Avis Budget Group**, with an engineered Item 2.04. §F lists the scripted cascade as engineered; the `public` 2.04 column stays entirely real. See §3 |

**D1 note.** The 18-month window was not rejected on the merits — it produces
397 8-K item-hits, almost exactly §F's ~400. It was rejected because Item 2.04
collapses to **1 event across 1 obligor** inside it, and §F wants ≥2 obligors.
24 months yields 4 events across 3. The cost is that §F's stated "18 months"
is restated; that restatement is deliberate and recorded here.

---

## 1 · Feasibility, measured before committing

Every number below was measured against the live sources on 2026-08-20, before
any design was fixed. This follows Wave 11a §1: measure first, then commit.

### 1.1 · 8-K item census — all 50 anchors, sharded history read

The EDGAR submissions index carries an `items` field per filing, so all six item
types are selectable from **metadata alone** — no full-text search, no
pagination trap of the kind that cost Wave 11a a wrong diagnosis.

The probe read `filings.recent` **and** the `filings.files[]` shards (41 shard
files). This matters: `known-issues.md` §9.11 records that `recent` caps at
~1000 filings and that 40 of 50 anchors have unread shards, making every
prior sweep a floor. Item 2.04 is rare enough that a floor could hide it
entirely.

| Item | Description | All history | Obligors |
|---|---|---|---|
| 1.01 | Material definitive agreement | 2,389 | 50 |
| 2.03 | Direct financial obligation | 1,084 | 50 |
| 5.02 | Officer/director departure | 2,062 | 50 |
| 4.01 | Auditor change | 58 | 27 |
| **2.04** | **Acceleration / triggering event** | **58** | **21** |
| 4.02 | Non-reliance | 26 | 18 |

Total item-hits, all history: **5,677**, spanning 2004-08-24 → 2026-08-19.

### 1.2 · The window trade-off, which an aggregate hides

| Window | Total 8-K events | Item 2.04 | Item 4.02 |
|---|---|---|---|
| 18 months | 397 | **1 event / 1 obligor** | 0 |
| **24 months (chosen)** | **534** | **4 events / 3 obligors** | 0 |
| All history | 5,677 | 58 events / 21 obligors | present |

This is the estate's recurring lesson in its own shape: *"~400 signal events"*
is satisfied beautifully at 18 months while the condition that actually matters
fails. Hitting the count while missing the condition is a failure.

The four in-window Item 2.04 filings:

| Obligor | Filed | Character |
|---|---|---|
| Tupperware Brands | 2024-09-18 | genuine distress acceleration |
| Murphy Oil | 2024-12-06 | recurring filer, 10 across history |
| Container Store Group | 2024-12-23 | genuine distress acceleration |
| Murphy Oil | 2026-01-08 | most recent 2.04 in the cast |

Real credit-distress events, not invented ones.

### 1.3 · WARN — reachable, and genuinely lossy without help

State WARN publication is not uniform. Measured:

| State | Format | Window coverage | Verdict |
|---|---|---|---|
| **Texas** | Socrata JSON API, `8w53-c4f6` | 2,368 rows, full | clean, free, no key |
| **California** | live XLSX (current FY) + per-FY PDFs | 3 files span the 24 months | PDFs are text-extractable (`pdftotext -layout` verified) |
| NJ / OH / FL / IL | JS portals; 403/404 on direct probes | — | scraping, cost unscoped |
| All others on Socrata | — | — | none; Texas is the only US state WARN dataset there |

**True positives found (§F wants ≥3 obligors):**

> **CORRECTED 2026-08-21 (Task 13).** The table below previously read:
>
> | Obligor | Matched employer | State |
> |---|---|---|
> | Charter Communications | "Charter Communications (Austin)" | TX |
> | Charter Communications | "Charter Communications", Burbank | CA |
> | **Avis Budget Group** | **"Avis Budget Car Rental" ×6 sites** | **TX** |
> | Quanex Building Products | "Quanex Homeshield LLC" (subsidiary) | CA |
>
> and was followed by *"Three distinct obligors — exactly the floor, which is
> why D2 adds a third state. Charter carries two of the three states on its
> own; losing it on verification would drop the wave below §F."*
>
> **The Avis row was measured against the FULL Texas source, not the 24-month
> window.** Every Avis Budget WARN notice in Texas is from 2020 — COVID-era
> rental-fleet closures — and the most recent unrelated Texas notice mentioning
> the name at all is 2022-06-28. The loaded window opens 2024-08-19. In-window
> Avis WARN notices: **none**. Verified against the loaded `warn_notice` table
> (3,514 rows, 2024-08-19 → 2026-08-19): `employer ILIKE '%avis%'` returns two
> rows, "Davis Street Community Center" and "Management & Training Corporation
> (Travis County State Jail)" — substring collisions, not Avis Budget.
>
> This is the estate's own §1.2 lesson turned back on the document that states
> it: an aggregate measured over the wrong span hides the decision. The mistake
> did not propagate into the data — `generators/warn_match.py` ran against the
> windowed artifact and never resolved an Avis pair; `test_warn_match.py` keeps
> the Avis pair only as a scorer fixture, explicitly commented out-of-window.
> It propagated into §1.5's cascade rationale, corrected there too.

| Obligor | Matched employer | State |
|---|---|---|
| Charter Communications | "Charter Communications", Burbank | CA |
| Quanex Building Products | "Quanex Homeshield LLC" (subsidiary) | CA |
| Bausch Health Companies | "Bausch Health US, LLC" | CA |

Three distinct obligors — exactly the floor, and **all three resolve in
California**, not across two states as first believed. Charter's Austin notice
is out of window; its in-window match is the Burbank one. Bausch Health is the
third true positive and was not in the original probe at all — it was found by
Task 4's scorer running the full 50 × 3,514 join rather than by inspection.

The margin is therefore thinner than the original table suggested, and in one
specific way: **California alone carries the entire §F floor.** Losing CA, not
losing Charter, is the failure that would drop the wave below §F. See §7.4 and
`docs/known-issues.md` §10.3 for what was done about it.

**False positives found — real, not engineered.** §F asks for *≥ 1 deliberately
ambiguous match*. The public data supplies a better set than we would have
manufactured, and CLAUDE.md rule 5 wants exactly this:

| Anchor | Collides with | Why it is instructive |
|---|---|---|
| Caesars Entertainment | CEC Entertainment (Chuck E. Cheese) | shared industry suffix, 0.842 similarity |
| Regis Corp (Supercuts) | St. Regis Houston (hotel) | one distinctive token, different industries |
| Granite Construction | "182 **Granite** Street, Corona CA" | matched a **street address**, not a company |
| Murphy Oil | "1001 **Murphy** Ranch Road, Milpitas CA" | matched a **street address** |
| Boston Omaha | Boston Scientific | shared city token |
| Container Store | Dart Container / Owens-Brockway Glass Container | shared common noun |
| Smith & Wesson | Hill & Smith, Smith Industries | shared surname |

The two address collisions are the most valuable: they demonstrate that matching
must be scoped to the employer column rather than run over free text. That is a
lesson engineered data cannot teach, because we would never have thought to
engineer it.

**Consequence for the design:** the crosswalk must record the *unresolved* pairs
as well as the resolved ones. A WARN match table that contains only true
positives destroys the demonstration.

### 1.4 · GDELT — reachable, rate-limited, substituted

The DOC API returned results for a real anchor query on first success, with
`seendate` at 15-minute granularity (`20250103T221500Z`, `20250103T223000Z`) —
confirming §C's claim that GDELT is the only public source in the catalog with
sub-daily native cadence.

Two constraints found by probe:
- **HTTP 429 on an unthrottled request.** The service asks for one request per
  five seconds. The fetcher must throttle and be resumable.
- Consecutive 15-minute slots return **near-duplicate articles** (same title,
  different slot). Real GDELT behaviour; relevant to mention counting.

Three more were found during implementation, all of the same family — the API
returns something that *looks* like a clean empty answer when it is nothing of
the kind. Each is recorded here because each would have produced a confidently
wrong dataset:

- **The stated 5s rate is a floor, not a guarantee.** Obeying it exactly still
  earned sustained 429s. Measured: 12s cadence 2/8 succeeded, 20s 1/13, 30s
  0/7, and nine minutes of total silence did not clear it — the penalty state
  is probabilistic, not a timed lockout. The fetcher holds a 12s floor and
  retries patiently; a 429 that never clears raises rather than returning `[]`.
- **`mode=artlist` silently clamps a long date range.** Asked for 24 months it
  scans backwards from `enddatetime`, returns only the trailing ~3 months, and
  stops *short of* `maxrecords` — so a full-page truncation test never fires.
  Proof: `"TUPPERWARE BRANDS" tone<-5` over the full window returns **zero**
  articles; the same query over 2024-09..2024-11 returns **71**, the Chapter 11
  coverage. `mode=timelinevolraw` is **not** clamped, so the fetcher timelines
  each obligor first and issues article calls only where volume exists — which
  also yields an expected article count to check the retrieved rows against.
- **Name matching collects other people's bad news.** An obligor whose short
  name is also a place, a person or an ordinary word accumulates adverse
  coverage belonging to something else. Sampling the first full sweep: `"Regis"`
  0/25 genuine (Bognor Regis and Lyme Regis court reports, an Australian gold
  miner), `"Sabre"` 0/25 (a wrestler, and "sabre-rattling"), `"Griffon"` 0/155
  (a vulture, a radio host). 1,809 mentions, 66% of the artifact, none of it
  about the obligors. All three return **zero** under every qualified corporate
  form measured, so the noise was replaced by a fetched zero. Findings ride
  along in `coverage[lei].precision_review`.
- **A quoted phrase can be unmatchable or rejected.** Postgres `legal_name` is
  EDGAR's registrant form (`CHARTER COMMUNICATIONS, INC. /MO/`); quoting it
  verbatim returns zero for a company that had a 42-million-record breach story
  in the window. And a phrase GDELT considers too short is refused with HTTP
  **200** and a plain-text body. Names are normalised before quoting, short
  names fall back to an unquoted term, and every row records the exact query.

### 1.5 · The cascade intersection — the finding that shaped the wave

§F's scripted cascade requires one obligor whose Item 2.04 invalidates the
covenant product, the exposure rollup **and** collateral coverage from a single
event. That is an intersection constraint on already-loaded data, so it was
resolved by query rather than by assumption.

**The three real in-window Item 2.04 obligors have none of the required
downstream data.** Murphy Oil, Container Store and Tupperware carry no facility,
no collateral pledge and no drawdown in `ccf_v2`. The cascade cannot be anchored
on a real in-window 2.04.

Twelve obligors hold the full facility + collateral + drawdown intersection;
eight of those also have real Item 2.04 filing history. One is far better
equipped than the rest:

**AVIS BUDGET GROUP** holds, simultaneously:

- a facility, a collateral pledge, and a drawdown — the three cascade targets
- a `covenant_breach` row — **one of only two in the entire estate**
- a loaded Wave 11a spread series
- real Item 2.04 filing history

> **CORRECTED 2026-08-21 (Task 13).** This list previously carried a sixth
> bullet, *"**6 real Texas WARN notices**"*. It is wrong for the reason §1.3's
> corrected table gives: those six were counted over the full Texas source, all
> six are from 2020, and **Avis Budget has zero WARN notices inside the loaded
> 24-month window**.
>
> **The cascade anchor decision (D6) stands unchanged, and does not need the
> bullet.** Avis was selected on the intersection §F actually constrains — one
> obligor whose Item 2.04 invalidates the covenant product, the exposure rollup
> and collateral coverage from a single event. Avis is the only obligor holding
> a facility, a collateral pledge, a drawdown, a `covenant_breach` row (one of
> two in the estate) and real 2.04 filing history at once. WARN was never part
> of that intersection; the bullet was supporting colour that happened to be
> false. Removing it removes nothing D6 rested on.
>
> **What it did cost.** It made the anchor look better-evidenced than it is, and
> it is the kind of stray number a later wave copies forward. The cascade as
> loaded touches no WARN notice: `surveillance.py` check 1 walks the engineered
> signal's 8 `signalAbout` targets and finds exactly 1 facility, 2 collateral
> pledges and 5 drawdowns — no WARN row among them, which is the check that
> would have caught a WARN-shaped dependency had one existed.

---

## 2 · Sources and their provenance

### 2.1 · The three provenance classes, per element

Per CLAUDE.md rule 1, every element is labelled with one of three classes. The
third class is where the demonstration earns its keep and it must be honest.

| Element | Source | Class | Store |
|---|---|---|---|
| 8-K events, 6 item types | EDGAR submissions index + filing text | `public` | Fluree |
| WARN notices | TX Socrata, CA EDD, +1 state | `public` | Postgres |
| Adverse media mentions | GDELT DOC API | `public` | Postgres |
| Financial trend deltas | XBRL `companyfacts`, period-over-period | `public` | Postgres |
| Spread widening | **inherited** from Wave 11a | `public` (3-leg, split) | Postgres |
| Covenant headroom / exposure at risk | **inherited** from Waves 4 / 9 | mixed | Postgres |
| `signalAbout` · `triggeredBy` edges | derived at ingestion | mixed | Fluree |
| Signal weights, decay constants | internal surveillance policy | `synthetic — internal` | Postgres |
| Escalation thresholds | internal credit policy | `synthetic — internal` | Postgres |
| Prior observation ledger points | internal sweep history | `synthetic — internal` | Fluree |
| **Cascade trigger event** | **manufactured** | **`synthetic — engineered`** | Fluree |
| **Composite case signal set** | **manufactured** | **`synthetic — engineered`** | Postgres + Fluree |

### 2.2 · Nothing is re-fetched that Wave 11a already loaded

`spread_observation` (29,885 rows), `benchmark_curve` (8,917) and
`market_oas_series` (3,930) are **inherited**. Wave 11b does not fetch its own
market data. This was the reason 11a and 11b were split; see
`docs/wave11a-design.md` §0.

The spread signal for surveillance is *derived* from the loaded series, and the
migration-transition work of 2026-08-20 matters here: the series now responds to
rating-band migrations, with anticipation carried in `idiosyncratic_bp` under a
per-obligor response profile. A spread-derived early-warning signal must
therefore **distinguish anticipation from confirmation**, not merely notice a
widening. See `docs/wave11a-migration-transition-design.md`.

### 2.3 · The GDELT substitution, stated plainly

§C names GDELT's "event and mention streams." Those are the raw CAMEO-coded
15-minute CSV files at `data.gdeltproject.org/gdeltv2/`. Twenty-four months is
roughly **52,000 files** — not tractable, and the cost buys nothing the product
needs.

**Substituted with:** the GDELT DOC API (`api.gdeltproject.org/api/v2/doc/doc`),
article-level, queried by entity name, carrying the same 15-minute `seendate`
granularity, with GDELT's tone filter applied so that "adverse media" is
genuinely adverse rather than any mention at all.

This is the same shape as Wave 11a's TRACE decision and is recorded the same
way: name the licensed or intractable source, state what is actually reachable,
label the provenance honestly, and record it in `known-issues.md`. Wave 11a's
carried-forward lesson 1 says a licensed source needs the same treatment
whichever source it is; this extends that to an intractable one.

**What the substitution costs.** GDELT's own entity tagging is not used —
matching is by name query, which is lossy. That loss is not a defect to hide: it
is the same lossy name resolution §C already demands for WARN, and it should be
visibly so.

---

## 3 · The engineered conditions

Three §F conditions cannot be fetched. Each is manufactured deliberately and
labelled `synthetic — engineered`, per CLAUDE.md rule 1.

### 3.1 · The scripted cascade — Avis Budget Group

An Item 2.04 acceleration is asserted against Avis Budget with `signalAbout`
edges reaching the facility that carries its covenant, its collateral pledge and
its drawdown. One event; three downstream products invalidated.

**Why an engineered trigger is correct here rather than a compromise.** §F lists
"the scripted cascade" among the elements that are engineered rather than
fetched. The manufactured event therefore sits in the column that permits it,
while the `public` Item 2.04 column stays entirely real (§3.2). The alternative
— manufacturing 2.04s to satisfy the `≥ 2 obligors` condition — would put
synthetic rows in a column §C classes as public, and was rejected.

The trigger sits on an obligor with **genuine 2.04 filing history**, so the
engineered event follows a pattern the obligor really exhibits rather than being
invented whole.

### 3.2 · The real Item 2.04 condition — kept entirely public

§F's `≥ 2 obligors with a real 8-K Item 2.04` is satisfied by Tupperware,
Murphy Oil and Container Store: real, public, in-window, unengineered. This
separation is the point of the 24-month window.

### 3.3 · The composite case

Three individually-subthreshold signals — a GDELT mention cluster, a WARN
notice, and a spread widening — that breach escalation only in combination.
This is the product's core argument, per §A: signals that look unremarkable
alone and are alarming together.

Placed on an obligor **other than Avis Budget**, so the composite case and the
cascade are independently demonstrable. A single obligor carrying both would let
one defect mask the other. Candidate selection requires an obligor holding all
three signal types; the intersection is computed at generation time, not
assumed here.

**The condition is that all three are individually subthreshold.** A composite
that breaches because one signal was already over the line proves nothing, and
counting three signals does not establish it. `surveillance.py` recomputes it.

### 3.4 · Prior observation points

One seeded ledger point per obligor, so the first sweep is a delta rather than a
cold start. §D's validation gates name **delta anchoring** explicitly: without a
recorded prior, the next sweep double-reports.

These are Fluree ledger points, not Postgres rows — the prior is itself a ledger
`t`, which is what makes the delta exact.

---

## 4 · Data model

### 4.1 · Store partition

Single-writer discipline holds: one store is authoritative per element, and no
attribute is duplicated across stores for convenience.

**Fluree** (`fibo-v2`) — `T` and `R`:
- 8-K event assertions, all six item types, with filing date and accession
- `signalAbout` edges: signal → obligor / facility
- `triggeredBy` edges: signal → source event
- prior observation ledger points, one per obligor
- supersession assertions, reusing the existing `ex:supersededBy`

**Postgres** (`ccf_v2`) — `E` and `P`, new tables:

| Table | Holds | Provenance |
|---|---|---|
| `warn_notice` | state WARN rows as published | `public` |
| `warn_match` | obligor ↔ notice candidates **incl. unresolved and rejected pairs** | mixed |
| `gdelt_mention` | article-level mentions, tone, `seendate` | `public` |
| `signal_event` | the unified signal ledger across all types | mixed |
| `signal_weight` | weight and decay constant per signal type / sector | `synthetic — internal` |
| `escalation_threshold` | thresholds bound to `intent` | `synthetic — internal` |
| `trend_delta` | XBRL period-over-period deltas | `public` |

`warn_match` retaining rejected pairs is load-bearing, not bookkeeping: it is
what makes the lossy join visible and the resolution logic testable.

No new store. Mongo and SQLite are untouched by this wave.

### 4.2 · Vocabulary — bind before generating

CLAUDE.md's named expensive failure is generating against invented local names:
it validates cleanly here and cannot be consumed downstream. So: bind upstream,
verify against the EDM Council source, generate, then flag the mirror.

| Term | Disposition |
|---|---|
| `supersedes` | **reuse** `ex:supersededBy` — already declared, 215 assertions since Wave 11a |
| Item 2.03 debt-issuance signals | **reuse** `ex:IssuanceEvent` / `ex:filedBy` — bound in Wave 11a |
| `BreachOfCovenant` | **reuse** `fibo-fnd-agr-ctr:BreachOfCovenant` where a breach is the signal |
| `WarningSignal` | candidate `ex:` extension — no FIBO equivalent expected |
| `SignalSource` | candidate `ex:` extension |
| `signalAbout` | candidate `ex:` extension |
| `triggeredBy` | candidate `ex:` extension |

The four candidates are recorded as **expected** `ex:` extensions, not as
concluded ones. Each is verified against `spec.edmcouncil.org/fibo` during
implementation before it is written anywhere — module membership does not pin an
IRI, and this estate has already been bitten by inherited bindings that were
never checked (`known-issues.md` §0.1–0.2, where all ten v1 bindings were wrong).

New terms are added to `docs/ccf_dataprep_v2.md` **first**, then to
`published_claims.json` so the next punch list generates itself, then the vault
mirror is flagged in the completion report. This repo is source of truth; the
mirror is downstream and is refreshed by the custodian, never by us.

### 4.3 · Explicit typing, no inference

Fluree runs without OWL reasoning. Every entity is typed explicitly for every
role it must be queried against. A `WarningSignal` that is also an
`ex:IssuanceEvent` carries both types; neither is inferred from the other.

---

## 5 · Pipeline

Load order follows CLAUDE.md: ontology → crosswalk → entities → relationships →
temporal → documents → departmental. Entities and the crosswalk already exist,
so this wave enters at relationships and temporal assertions.

```
generators/fetch_8k_items.py       # 6 item types, sharded history, metadata-selected
generators/fetch_warn.py           # TX Socrata + CA XLSX/PDF + third state
generators/fetch_gdelt.py          # DOC API, timeline-then-articles, 1 req / 12s, resumable
generators/generate_trend_deltas.py# from loaded financial_fact, no fetch
generators/generate_signals.py     # unify into signal_event; weights; thresholds
generators/narrative_wave11b.py    # cascade + composite case (engineered, labelled)
loaders/load_postgres_wave11b.py
loaders/load_fluree_wave11b.py     # events, edges, prior observation points
```

**Ordering constraint, carried from Wave 11a's hard-won lesson.**
`generate_signals.py` reads the loaded spread series and the fetched sources, so
it must run after all fetchers. Where a generator depends on another's artifact,
the dependency is enforced with an explicit guard that **raises naming the
required order** — and, unlike Wave 11a's guard, checks that the artifact is
*current* rather than merely present. `known-issues.md` records that a stale
`wave11a_grades.json` satisfies the existence check silently; that residual
hazard is not repeated here.

> **STATUS, added 2026-08-21.** The paragraph above was written as a commitment
> and Wave 11b shipped without honouring it: every artifact read in the wave was
> a bare `json.loads`, and the whole-branch review found the guard absent. It is
> now **built** — `ccf/currency.py`. A generator records the sha256 of every
> artifact it consumed under `_inputs`; `generate_signals.py` and
> `narrative_wave11b.py` both do, and both Wave 11b loaders plus
> `narrative_wave11b.py` verify those bytes before reading, raising
> `StaleArtifact` and naming the required order.
>
> **What the paragraph above still over-promises, stated rather than left
> implicit.** A content hash establishes *"these are the bytes I was built
> from"*. It does not establish *"these were the right bytes"*. Restoring a
> pre-fix `wave11b_gdelt.json` **and** re-running `generate_signals.py` against
> it produces a self-consistent record that this guard passes. The defence
> against that is `validators/surveillance.py` check 6, which the pre-fix
> GDELT head would fail. See `docs/known-issues.md` §10.11.

Every loader is `--dry-run` capable and idempotent. We will reload many times.

---

## 6 · Validation

### 6.1 · `validators/conditions.py` — extended

New §F row-level checks appended to the existing 82. The baseline is **82 passed
/ 0 failed** with no standing exception; any red from here is a regression.

### 6.2 · `validators/surveillance.py` — the new gate

In the lineage of `series.py` and `traversal.py`: these exist because
`conditions.py` cannot establish their claims by counting rows. A graph must be
walked; a distribution must be recomputed. So must these:

| Claim | Why counting fails |
|---|---|
| The cascade reaches all three downstream products | A count of edges does not prove they terminate on the covenant, the pledge and the drawdown |
| The composite case's signals are each **individually subthreshold** | Counting three signals says nothing about whether one was already over the line |
| …and **jointly** breach escalation | Requires recomputing the composite against loaded weights |
| Composite scores **vary rather than cluster** | §F's distribution condition; see §7.1 |
| Every obligor has a prior observation point | §D's delta-anchoring gate |
| WARN resolution keeps ≥3 true positives **and** leaves the ambiguous pairs unresolved | A match table with only true positives passes a count and destroys the demonstration |

### 6.3 · Unit suites

`validators/test_signals.py` and `validators/test_warn_match.py`, following the
established pattern — the estate currently holds 9 test files / 169 cases, all
green. Name matching in particular is logic that must be tested against known
pairs, including the address collisions of §1.3, which are the cases most likely
to regress silently.

### 6.4 · Partition

`partition.py` must stay 13/13 and gain checks that the new tables live only in
Postgres and the new assertions only in Fluree. The validator asserts each store
holds the slice it owns **and nothing it does not** — it does not assert the
stores agree.

---

## 7 · Risks carried into implementation

### 7.1 · The distribution condition is the one D3 puts at risk

§F wants ~400 signal events *"distributed so composite scores vary rather than
clustering."* D3 loads everything instead — roughly 1,000+ events. Loading more
data does not by itself make composite scores cluster, but it removes the
mechanism by which the distribution was going to be *designed*.

The condition is therefore **measured rather than assumed**, in
`surveillance.py`, and reported honestly whichever way it comes out. If scores
cluster, that is a finding to surface and fix — not a number to quietly report
as satisfied because the event count was met. Hitting the count while missing
the condition is a failure; this is the wave's most likely instance of it.

### 7.2 · CA PDF parsing is a silent-defect surface

Two text-extractable PDFs carry two of the three CA fiscal years. Extraction
will be verified against the source bytes, not against row counts. Wave 10's
Form 4 trap — 120 filings that returned HTTP 200 with the wrong content and
failed silently and identically — is the governing precedent: *a status code is
not evidence of the right content*, and neither is a plausible row count.

### 7.3 · GDELT throttling makes the fetch long and interruptible

One request per twelve seconds across ~50 obligors, over 24 months, with the
window split by timeline volume (203 calls in the run that produced the
artifact: 61 timelines plus 142 article calls; the extra timelines are the
per-obligor query corrections described in §1.4). Most of the wall clock is spent
on 429 retries, not on successful calls. The fetcher must be resumable in the
manner of the embedding pass, and must not silently truncate on a 429. Wave 11a's lesson 2 applies directly: instability
across paged-sweep runs is evidence of incompleteness, not of a changing source.

### 7.4 · The third WARN state is unscoped

D2 commits to a third state without naming it. NJ, OH, FL and IL were probed and
are JS portals or blocked. The third state's cost is unknown until planning, and
it is the one line item in this design that could grow.

### 7.5 · Item 4.02 has no instances *in the chosen window*

The cast files non-reliance 8-Ks — **26 of them across 18 obligors** — but the
most recent falls outside the 24-month window, so the signal type is loaded and
carries zero rows. This is a property of the window, not of the cast: widening
far enough would recover them, at a cost §1.2 already rejected. §F sets no
`≥ N` for Item 4.02, so this is a recorded absence rather than a failure — but it must be recorded, because
`known-issues.md` shows this estate has repeatedly found deleted or empty things
whose names survived elsewhere.

### 7.6 · The spread signal must not re-learn the generator

Wave 11a's series is exactly invertible: at any band crossing, `α = 1 − jump/gap`
from two adjacent rows. A surveillance signal built naively against it can
recover the generator's own parameter rather than detect anything. The signal
must distinguish **anticipation from confirmation**, per
`docs/wave11a-migration-transition-design.md`.

---

## 8 · Out of scope for Wave 11b

Per CLAUDE.md, read the Assembly Recipe to understand what the data must
support; never implement it.

- **The Control Plane and the invalidation cascade itself.** We produce the
  event, the edges, and the prior observation points that make the cascade
  computable. Propagation is a runtime behaviour, consumed downstream.
- **Decay computation.** λ_c constants are stored as policy rows; applying decay
  is the Evaluate operator's job.
- **Any operator, contract, TTL or replay logic.**
- **The reporting bank entity.** Still the estate's only hard cast gap; it gates
  Wave 17, not this wave.
- **PSC / Companies House person data.** Never exercised, and not exercised here.
  It concerns real living people and requires asking the user first.
