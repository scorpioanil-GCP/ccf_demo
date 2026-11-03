# Wave 16 — `ib-opportunity-synthesis`

**Status:** design, awaiting approval
**Date:** 2026-08-24
**Product:** `cib.opportunity-synthesis.v1` · Tier 5 · all five stores · cost band ×8–15
**Spec:** vault `context-products/ib-opportunity-synthesis`

---

## 1 · Why this product is different

Every other product in the catalog anchors on an **entity**. This one anchors on
the **banker**. That is not a presentation detail — it is the whole argument.

The coverage portfolio determines *which* prospects are candidates, and the
perspective determines *what the ranking optimises for*. There is therefore no
principal-independent ranking to filter down, which is precisely the failure
(§4.4 "Perspective Flat") the product exists to answer.

The data consequence: **the same signal set must produce different orderings**.
If the estate cannot demonstrate that, the product proves nothing, no matter how
many rows load cleanly.

---

## 2 · What already exists

Four prerequisite products are built, and they carry most of the substrate.

| Piece | Where | Count |
|---|---|---|
| Banker roster | `banker` | 40 |
| Coverage portfolio | `coverage_assignment` | 150 over 37 bankers, 50 obligors |
| Signal events | `signal_event` | 1,603 across 5 types |
| Signal weights with decay | `signal_weight` | 45 (`decay_days` present) |
| Projection plans / principals | `projection_plan`, `principal` | 3 / 4 |
| 13F institutional positioning | `institutional_holder` | 22,476 |
| Sector news | `gdelt_mention` | 951 |
| Spread trajectory | `spread_observation` | 29,885 |
| Insider activity (Form 4) | `sources/form4` | 7,875 filings |
| 8-K Item 1.01 | `sources/form8k502` | fetched |
| Deal pipeline / CRM | `deal`, `interaction` | 32 / 2,050 |
| Merger proxies on disk | `sources/def14a` | 49 |
| Banker-local notes | SQLite `prospect_note` | 18 |
| Restricted list | SQLite `restricted_list` | 4 |

`ex:signalAbout` and `ex:Banker` are **already bound** in the v2 binding table.

---

## 3 · Source feasibility — measured, not assumed

Probed 2026-08-24 against all 53 anchors carrying a CIK. Scripts in scratchpad;
counts reproduced below.

| §C row | Form(s) | Result | Verdict |
|---|---|---|---|
| Activist / beneficial-ownership stakes | `SCHEDULE 13D`, `SCHEDULE 13D/A`, legacy `SC 13D*` | **18+ anchors**, freshest **2026-08-21** | ✅ build |
| M&A / material-agreement events | 8-K Items 1.01, **2.01** | 1.01 fetched; 2.01 one string away | ✅ build |
| Merger proxies and deal terms | `DEFM14A`, `PREM14A`, `DEF 14A` | 5 + 4 in window, 49 on disk | ✅ build |
| IPO / merger registration pipeline | `S-4`, `S-4/A` | 3 + 3 in window, 119 lifetime | ✅ build (S-4 half) |
| IPO / merger registration pipeline | `S-1` | **43 lifetime, 0 since 2023** | ❌ named gap |
| Government-contract concentration | USASpending.gov | 17/50 by recipient name, ~10 genuine | 🟡 build, curated |

### 3.1 The form-name trap

The first probe matched `SC 13D` and returned **zero filings after 2024-12-06**,
which reads exactly like "the source dried up". It had not. The SEC's structured
-XML mandate renamed the form to **`SCHEDULE 13D`** in December 2024, and the
old string silently matches nothing since.

Recorded because the same shape will recur: *a form-name change is
indistinguishable from a dead source when you match on a literal.* Any fetcher
added here matches **both** the legacy and modern names.

### 3.2 Direction is confirmed, not assumed

A Schedule 13D is filed **by** an activist **about** a subject company, so it was
an open question whether it appears under the subject's CIK at all. Sampled 12
recent filings and read the submission header: the anchor is the **SUBJECT** in
**12 of 12**. The join the spec assumes is real.

> **Annotated 2026-08-25 (final fix wave): this "12 of 12" conclusion is
> refuted by §6.1 below, not confirmed by it.** The sample matched only the
> legacy `SC 13D*` form names, so its entire population predated 2024-12 —
> the modern `SCHEDULE 13D*` filings, which are exactly where our anchors
> turn up as **FILER** rather than SUBJECT (Boston Omaha, Charter), were
> invisible to this probe. "12 of 12 SUBJECT" was real for the sample it
> drew; the sample itself was biased by the same form-name trap §3.1 names
> above it. The durable fix is not a bigger sample — it's that `role` is
> resolved per row from each filing's own submission header at signal-
> generation time, never assumed from a probe. Left in place as a record of
> how the bias looked from the inside, not as a standing claim.

### 3.3 Why S-1 is dropped

Our cast is established issuers. An S-1 is an IPO registration; they filed them
before listing and have not since. Zero filings in three years is a fact about
the cast, not a gap in the fetch. Recorded in `spec_coverage.py` with this
evidence. **`S-4` covers the merger-registration half of the same §C row**, so
the row is partially — and honestly — accounted for.

### 3.4 Why USASpending needs curation

USASpending's `keywords` filter searches **award description text**, not
recipient identity. It returned `XPO` → *Lockheed Martin*, `REGIS` → *Humana
Government Business* ($20.4bn). Switching to `recipient_search_text` improves it
but does not fix it: `AMPHENOL` → *MTS Systems*, `XPO` → *Kalama Export*.

CLAUDE.md rule 5 wants joins that are imperfect **on purpose**. These are
imperfect **by accident**, and a government-revenue-concentration measure built
on them would simply be wrong. So: fetch against a **hand-verified recipient
allow-list**, and record a match band per row the way `legal_entity.lei_match_band`
already does. Unverified candidates are dropped, not guessed.

---

## 4 · Dates

The most likely silent failure in this wave is temporal, so it is specified
before anything else.

### 4.1 Real dates are never shifted

A filing date is a public fact. Real 13D, 8-K, proxy and S-4 signals carry their
**true filing date**. Only synthetic signals are dated, and they are dated into
the 12-month window **2025-08-25 → 2026-08-24**.

### 4.2 Fluree takes plain strings, never `xsd:date`

Fluree 4.1.4 corrupts typed date literals on write (known-issues §19.4:
`2026-01-02` reads back as `1972-01-01`). Every date on a new Fluree node in this
wave is a **plain string**. `loaders/dump_fluree.py` already exits non-zero on the
first typed literal, so this is guarded rather than merely written down.

### 4.3 `AS_OF_IB` is pinned — this is the load-bearing one

Every signal class decays (`signal_weight.decay_days`; spec §E gives λ_c ≈ 30d
for 13D, 14d for 8-K, 7d for GDELT). **The ranking is therefore a function of the
clock as much as of the weights.**

If the validator ranks at `date.today()`:

- the engineered divergence passes on the day it is built and **silently dies**
  weeks later as the catalysts decay past the M&A weight floor;
- §F's *"replay under the prior weight version"* proves nothing, because a
  reorder cannot be attributed — it could be the weight change or the clock.

So `AS_OF_IB = "2026-08-24"` is pinned in `ccf/config.py`, and:

> **the weight-replay condition varies the weight version with `as_of` held fixed.**

This is the "oracle from the wrong period" failure in a new costume: a ranking
computed against the wrong instant is internally consistent, plausible, and
wrong.

### 4.4 Bitemporal shape

Opportunity signals carry `observed_at` (valid time — when the event happened)
and `asserted_at` (assertion time — when we recorded it), matching the estate's
existing convention (73 / 37 uses). A `SCHEDULE 13D/A` **supersedes** its parent
13D, reusing the supersession pattern already built in Wave 11a.

---

## 5 · Store assignment

Single-writer discipline per CLAUDE.md. No attribute duplicated.

| Store | Owns here |
|---|---|
| **Fluree** | `ex:OpportunitySignal` nodes; `ex:signalAbout`, `ex:coveredBy`, `ex:comparableTo` edges; supersession; wall state inherited |
| **Postgres** | perspectives, weight vectors, mandates/appetite, maturity ladder, positioning, gov-contract concentration, projection plans |
| **MongoDB** | proxy / S-4 text with passage spans and embeddings |
| **SQLite** | banker-local prospect notes; restricted list |
| **Neo4j** | untouched |

### 5.1 New Postgres tables

Four **new** tables. `signal_weight` is **not** widened with a perspective column:
it belongs to `credit-surveillance-early-warning`, and adding a column would
rewrite that product's 45 rows — the positional-identity defect class this repo
has hit four times.

| Table | Purpose |
|---|---|
| `ib_perspective` | 3 rows: M&A originator, DCM banker, sector strategist |
| `perspective_weight` | signal_type × perspective × `weight_version`, **two versions** |
| `mandate` | live deal pipeline, stage, client stated appetite, mandate history |
| `gov_contract_concentration` | USASpending, with `match_band` per row |

### 5.2 New FIBO bindings

`ex:OpportunitySignal`, `ex:coveredBy`, `ex:comparableTo` are **confirmed
unbound** — zero occurrences in the v2 binding table, checked 2026-08-24. Each is
**verified against `dev.fibo-quickstart.ttl`** before minting —
never `prod`, which omits 40 Provisional modules including nine of our own bound
terms — and by grepping `rdf:about` in the ontology, because an EDM Council URL
returns HTTP 200 for terms that do not exist.

The binding table is extended **before** generation, and **the vault mirror is
flagged for refresh and sent through the exchange**.

---

## 6 · The demonstration

§F's centrepiece: *one prospect top-3 for the M&A originator and outside the
top-20 for the DCM banker, from identical underlying signals.*

**Corrected 2026-08-24, after the fetch disproved the original choice.**

**Candidate: Braemar Hotels & Resorts Inc.** — 13 activist filings inside the
12-month window, the most of any anchor, with **4 confirmed `SUBJECT`** by
submission header. Freshest 2026-07-23.
**Counterpart: Thermon Group Holdings, Inc.** — mirrors it in the shipped
data (`validators/ib_rank.py`'s `MIRROR_PROSPECT`; supersedes the earlier
"Anywhere Real Estate Inc." counterpart named in an earlier draft of this
section — see the correction below).

### 6.1 What the original choice got wrong

The first draft named **Boston Omaha Corp**, on 27 Schedule 13D filings with the
freshest at 2026-08-13. Both numbers were real. The inference was not.

**Boston Omaha is an activist holding company. It *files* 13Ds about other
companies.** Its freshest filing has `role=FILER`, not `SUBJECT` — it is a signal
about Boston Omaha's *targets*, and reading it as "an activist has taken a stake
in Boston Omaha" inverts the signal completely. Charter's 2026-08-21 filing is the
same.

**One defect concealed the other.** The pre-design probe that "confirmed direction,
12 of 12 SUBJECT" matched only the legacy `SC 13D*` form names — so its entire
sample predated 2024-12, and the modern `SCHEDULE 13D*` filings, which are exactly
where our anchors appear as filers, were invisible to it. The form-name bug biased
the check written to validate the join.

The durable remedy is not a different entity. It is that **direction is a per-row
property**: `role` is resolved for every filing from its submission header, signal
generation filters to `role == "SUBJECT"`, and a validator condition asserts no
`FILER` row ever became an activist-stake signal. A sampled direction check can
confirm an assumption; it can never act as a filter.

### 6.2 The engineering shrank

The original plan had to **invent** a debt ladder for Boston Omaha, because it had
**zero** `debt_instrument` rows — the DCM weakness was being manufactured to avoid
ranking on absent data (§6.1 of the first draft called that trap correctly, then
fell into a different one).

Braemar needs none of it. It already carries two instruments maturing **2043** and
**2045** — no near-term wall — with a spread band of 105–141 bp across the window,
i.e. flat. **The condition §F asks for is already true in loaded data**, so this
wave verifies and documents it rather than engineering it. That instrument set
came from an earlier wave and is labelled `synthetic — engineered` there
(anchored to real filings); this wave adds nothing to Braemar's side of the
pair — no new instrument, no new spread observation.

**Correction (final fix wave, 2026-08-25): the sentence above is true of
Braemar and was wrongly read as true of the whole demonstration.** It is
NOT true of the mirror side. Thermon Group Holdings, Inc.'s DCM ranking
rests on `w16-i-01a242`, a bond **this wave minted**
(`generators/extend_debt_ladder_wave16.py`, Task 8b) with a maturity of
**2028-06-13** — inside the 24-month near-term-wall horizon **by
construction**, because the generator's near rung is deliberately dated
inside that horizon for every eligible obligor it touches — and a widening
idiosyncratic spread trajectory, also this wave's construction. That
instrument is correctly labelled `synthetic — engineered` in
`sources/screening/wave16_debt_ladder.json`; the defect was never in the
label, it was that this section's prose described the *pair* as verified
rather than saying which half was measured (Braemar) and which half was
built to order (Thermon). One prospect in the divergence demonstration is
genuinely emergent from loaded public data; its mirror is not, and both
facts need to be visible together for the demonstration to be honest about
what it proves.

---

## 7 · The ranking validator is an instrument, not the product

**Resolved 2026-08-24 against the vault's definition**, and recorded in CLAUDE.md
so it is not re-litigated.

An **Operator** is a runtime SDK entity (`cognitive-context-fabric/ccf-architecture`,
L4): typed composable primitives — Traversal, Temporal, Policy, Similarity —
resolved through a registry, ordered by the Operator Plan DAG Generator, executed
in the **Data Plane**, serving a principal at request time. Operators are how the
fabric assembles a product *dynamically*, which is this product's whole
materialization posture (§E: derived on demand, per banker).

Two things follow. **`Rank` is not one of the four canonical operator
categories** — it appears in this spec's `operators_invoked` lineage list, and §D
describes it as *"in-memory, algorithmic… Deterministic; no LLM inference — the
ranking is arithmetic over a policy-versioned weight vector"*, i.e. Assembly
**Mode 1**, no model at any stage. And **a build-time check is none of those
things.**

The per-perspective **weights are ours to produce** — §C assigns them to Postgres
as `synthetic — internal`, dimension `Π`/`P`. The Rank Operator *consumes* them.
Shipping a weight vector without confirming it separates the M&A and DCM
orderings would be the "counted but not created" failure exactly.

`validators/ib_rank.py` is therefore a **verification instrument**:

- it lives in `validators/`, is imported by no loader and no generator;
- it recomputes scores from Postgres on every run — it never reads a stored
  rank, a cached score, or a boolean flag;
- it exists solely to prove the loaded data satisfies §F.

It is not the Rank Operator, does not assemble a contract, and emits no product.

### 7.1 Conditions it must prove

Four real floors — each recomputed, never counted:

1. **Divergence** — ≥1 prospect top-3 for M&A **and** outside top-20 for DCM, at
   the pinned `as_of`, from one signal set.
2. **Candidate-set containment** — ≥2 restricted prospects **absent entirely**
   from the affected principals' candidate sets. Not flagged, not marked:
   *absent*. A suppressed row with a marker tells the banker exactly what the
   wall exists to hide, so the validator also asserts **no disclosure marker**.
3. **Note materiality** — ≥5 SQLite prospect notes that **change a ranking** when
   included. Proved by ranking twice, with and without notes, and diffing the
   order. Counting 50 notes proves nothing.
4. **Weight replay** — the same candidate set ranked under weight-version 1 and
   version 2, `as_of` held fixed, producing a **different and reproducible**
   order.

Each check is tested with a known-present **and** a known-absent fixture and must
return different answers, per the estate's "output that never varies" rule.

The §F figures without a condition attached — ~40 bankers, ~200 prospects, ~600
signals, ~50 notes — are **shape, not targets**, per Dave's 2026-08-24 ruling.
The four floors above are floors.

---

## 8 · Load order

Ontology/bindings → perspectives & weight vectors → public fetches → signals →
Fluree edges → documents & passages → departmental notes → validators.

Every loader is idempotent and safely re-runnable. Idempotency is proved by
**naming a value that must survive a second run**, never by comparing counts —
a count cannot see a field being reset.

---

## 9 · Definition of done

1. All 18 §C rows mapped in `validators/spec_coverage.py`, each accounted for or
   named as a gap with evidence.
2. Correlation keys resolve: `banker_id` → coverage → `LEI` → `CIK`.
3. All four §F floors in §7.1 satisfiable by a real query.
4. Single-writer discipline holds; `partition.py` green.
5. New FIBO terms bound, verified against `dev.fibo-quickstart.ttl`, **vault
   mirror flagged and sent**.
6. `conditions.py` registers the product; count read from `conditions.py`, never
   a prose list.

---

## 10 · Open

- **How `ex:comparableTo` gets its pairs.** Checked 2026-08-24: there are **no
  existing pairwise peer edges to reuse.** `peer_cohort` (324 rows) is SIC-level
  cohort *statistics* — `sic`, `tag`, `frame`, thinness — with no entity pair in
  it, and `peer_entity` (1,678 rows) is `cik` + `entity_name` + `sic`, a
  membership list rather than a graph.

  So comparability must be **derived**, and the cheapest honest derivation is
  shared SIC between entities already in `legal_entity`, restricted to the
  prospect set. That is a real modelling choice, not a load: SIC is a coarse
  proxy for "comparable", and the sector strategist's whole ranking leans on it.
  Decide at implementation, and record the basis on the edge so a consumer can
  see what "comparable" meant.
