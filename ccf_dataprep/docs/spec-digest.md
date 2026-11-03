# Spec Digest — the 14 specs unread through Wave 7

**Written:** 2026-08-17 · **Source:** `get_article("context-products", <name>)`, read in full
**Companion to:** `data-acquisition-plan.md` (waves, decisions) · `known-issues.md` (defects, limits)

> Waves 0–7 were planned against **8** specs. This digest covers the remaining
> **14**, read end to end on 2026-08-17. It records only §C (Data Catalog) and
> §F (Manufacture envelope) — the two sections this project acts on.
>
> ⚠️ **Vault specs are patched in place.** Re-read a spec before acting on this
> digest if material time has passed. See `known-issues.md`.

---

## 0 · The headline finding

**The anchor cast was screened against 8 specs; 14 more now impose conditions on it.**

`data-acquisition-plan.md §2` called obligor selection "a joint constraint-satisfaction
problem across all 21 §F envelopes" and "the only genuine big-bang risk in this
project." Wave 0 screened against the conditions then known; the 14 specs read
today add constraints the screen never tested.

**✅ Audited 2026-08-17** — `uv run validators/cast_audit.py`, read-only.
Result: **19 satisfied · 2 shortfall · 9 need a fetch**.

The cast held up considerably better than first feared. Of four constraints
initially flagged as probably-unsatisfiable, **two were already carried**:

| Constraint | From | Verdict |
|---|---|---|
| ~6 facilities with a real **EX-10 Commitment Schedule** | `syndicated-lending-co-lender` | ✅ **11 obligors** already carry one in the fetched corpus — no action |
| ~30 obligors with **TRACE-observable traded debt** | `rating-and-spread-migration` | 🟡 **All 50** have 8-K Item 2.03 debt issuance, so the population exists. TRACE *coverage* still needs confirming — a proxy, not a substitute |
| **A reporting bank entity** with FFIEC Call Report / FR Y-9C | `large-exposure-rwa-concentration` | ✅ **CLOSED 2026-08-22.** JPMorgan Chase Bank, N.A. — RSSD 852218, LEI 7H6GLXDRUGQFU57RNE97, holding company RSSD 1039502 — with **12 quarters of real Call Report capital** (tier 1 $295.8bn, RWA $1.96tn, CET1 15.08% at 2026-03-31). Chosen from the estate's OWN EX-10 filings, where it is administrative agent on 15 facilities across 5 obligors, more than any other agent. `loaders/load_reporting_bank.py` |
| **UK entities** in the Companies House PSC register | `kyc-refresh-beneficial-ownership` | 🔴 **Confirmed shortfall.** Zero GB-domiciled entities |

The audit also surfaced a constraint not previously flagged:

| Constraint | From | Verdict |
|---|---|---|
| A connected group spanning **≥ 3 jurisdictions** | `large-exposure-rwa-concentration` | ✅ **CLOSED 2026-08-27 (corrected; see below).** |

> Counting raw GLEIF codes reports "10 jurisdictions" and hides this — `US-DE`
> and `US-MD` are ISO 3166-2 **sub-national** codes inside one jurisdiction, and
> a large-exposure regime is national. `cast_audit.py` counts countries for
> exactly this reason.

> **⚠️ Correction, 2026-08-27 (Wave 19).** The row above, and the "Thin non-US
> tail" option in the table that follows, were written 2026-08-17 against the
> cast as it stood *before* Wave 15's GLEIF subsidiary fetch. That fetch closed
> the shortfall: the estate now carries **30+ countries across 421 entities**,
> yielding **26 real connected groups** from GLEIF control edges, of which
> **9 span ≥ 3 jurisdictions on control edges alone** — no engineering
> required. Wave 19 Task 7 added `economicallyDependentOn` edges on top of
> those control edges (a judgment relationship the public estate cannot
> supply on its own) and the span **rose to 12 of a ~15 shape** — a shortfall
> against §F's own figure, recorded as a divergence in
> `docs/ccf_dataprep_v2.md` and `docs/HANDOFF.md`, not as an unbuildable
> condition. "3 countries / 3 non-US entities / thin tail" was true of the
> cast on 2026-08-17 and has not been true since Wave 15.

**Also confirmed by the audit** — the already-fetched EX-10 corpus carries far
more T2 structure than expected, which de-risks Wave 9 substantially: guarantor
schedules (15 obligors), cross-default clauses (11), negative pledge (10),
security/collateral schedules (16), related-party dealings (22). And
`credit-memo-context`'s peer-thinness Context Debt arises naturally — 2 rich
cohorts (≥15) and 64 thin ones (≤3) already exist.

Three further constraints are additive rather than contradictory — new populations
alongside the cast, not conditions on it:

- **2–3 real ABS deals** (`abs-securitization-surveillance`) — a separate issuer
  population entirely; ABS trusts are not corporate obligors
- **~200 synthetic AML parties** (`aml-typology-match`) — must correspond to *no*
  real entity, by hard rule; deliberately disjoint from the cast
- **~200 prospect entities** (`ib-opportunity-synthesis`) — "drawn from the anchor
  obligor set **and extended**", so total entity count grows past the current ~500

### Three decisions the audit leaves open

| Gap | Options |
|---|---|
| **No reporting bank entity** | Add one — pick an RSSD from FFIEC NIC and load Call Report Schedules RC-C / RC-R. It is public, free, and the capstone cannot compute a limit without a real capital base. **Cheapest of the three.** |
| **No UK entity for PSC** | Either add UK anchors (they must also carry EDGAR filings to stay joinable, which is restrictive) or build the person layer entirely synthetically, structured on real PSC *patterns*. The spec pseudonymizes persons anyway, so the second option loses less than it appears — and CLAUDE.md rule 3 requires pseudonymization regardless. |
| **Thin non-US tail** | **RESOLVED by Wave 15's GLEIF subsidiary fetch, before this ever needed engineering.** See the 2026-08-27 correction above. |

Re-run `uv run validators/cast_audit.py` after any change — it is read-only and
takes seconds.

---

## 1 · Per-spec digest

Ordered by tier, matching Q019 §5.

### T2 · credit-exposure-rollup — `credit-risk.exposure-rollup.v1`

**Stores.** Fluree owns ownership/guarantee/cross-default/borrower-of edges.
Postgres owns commitments, balances, limit definitions, the XBRL reconciliation.

**New public sources.** None — EX-10 guarantor schedules and 10-K debt footnote,
both already in the fetch path. XBRL total debt already loaded (Wave 2).

**§F conditions.**
- ~40 facilities across ~50 anchors, unevenly distributed (some families several, some none)
- ~25 guarantee edges, **≥ 3 upstream** (parent guarantees a sub holding no facility)
- ~15 cross-default edges, **≥ 2 reaching an entity holding no facility**
- **≥ 3 families where naive and guarantee-adjusted summation differ materially**
- Balances reconciling to a plausible share of each obligor's XBRL-reported total debt

**Engineered.** All balances, borrower-of edges, limit definitions; guarantee and
cross-default topology wherever EX-10 parsing yields too little.

**Note.** The reconciliation against XBRL total debt is a credibility test the
project currently has no equivalent of — synthetic commitments should be a
*plausible share* of real reported debt, never exceed it.

---

### T2 · collateral-and-setoff-coverage — `credit-risk.collateral-coverage.v1`

**Stores.** Fluree: `securedBy`, `pledgedBy`, `setOffAgainst`, `nettedUnder`, lien
priority, negative-pledge presence. Postgres: valuations, deposit balances,
haircut schedule, enforceability register, asset descriptions.

**New public sources.** ⚠️ **UCC-1 lien filings** — free search in *several* US
states only, interfaces vary, some charge. **Availability must be confirmed for the
chosen anchors before committing.** Fallback where thin: EX-10 collateral schedules
(uniformly available, less granular).

**§F conditions.**
- ~60 collateral assets across ~40 facilities (real property, marketable securities, receivables, equipment)
- **≥ 3 shared-collateral cases**, ≥ 1 across differing priorities
- **≥ 2 facilities over-collateralized contractually but under-covered after haircuts**
- ~20 deposit accounts with set-off rights, **≥ 4 where enforceability fails** by jurisdiction
- **≥ 1 negative-pledge covenant conflicting with a proposed new lien** (seeds `covenant-cross-reference`)
- Valuation dates spread from same-day to **18 months stale**

**Engineered.** Valuations, deposit balances, set-off/netting edges, haircut
schedules, enforceability register, and the shared-collateral cases.

**Note.** UCC filings key on **legal name, not LEI** — a genuine fuzzy-match
problem this product surfaces and `kyc-refresh` takes on properly. Consistent with
CLAUDE.md rule 5 (some joins imperfect on purpose).

---

### T2 · client-360-coverage-graph — `coverage.client-360.v1`

**Stores.** Fluree: `employedBy`, `coversClient`, `participatedIn`, `relatedToDeal`.
Postgres: officers, interactions, banker roster, 13F holders, scoring weights.

**New public sources.** **DEF 14A** proxy statements · **Form 3/4/5** · **Form 13F** ·
8-K **Item 5.02** (officer changes).

**§F conditions.**
- ~50 anchor clients, each **8–25 named client-side people** from DEF 14A / Form 4
- ~40 synthetic bankers across coverage, product, credit roles
- **~2,000 interaction records** over 24 months, recency-weighted (not flat)
- **≥ 1 client whose depth-2 traversal exceeds `limit=200`** (exercises truncation disclosure)
- **≥ 5 person records with name variants** across sources ("Robert"/"Bob", middle initials)
- **≥ 3 coverage gaps** — senior client officers with no bank-side interaction
- ~10 interactions classified need-to-know, invisible to ≥ 1 test principal

**Engineered.** The entire bank side — bankers, coverage assignments, interactions,
deals, scoring weights — plus the person crosswalk and its deliberate imperfections.

**Note.** The public/synthetic ratio **inverts** here vs `corporate-family-tree`:
client-side people are public, every bank-side element is necessarily invented.

---

### T3 · treasury-liquidity-position — `treasury.liquidity-position.v1`

**Stores.** Postgres: rates, curves, balances, positions, limits, mandates.
Fluree: `heldAt` / `concentratedIn` edges, regulatory posture overlay (time-versioned).

**New public sources.** **NY Fed SOFR** (daily ~08:00 ET, with percentiles) ·
**Treasury.gov Daily Par Yield Curve** (XML) · **FRED API** (`SOFR`, `DGS1MO`…`DGS30`) ·
**Fed H.10** + **ECB reference rates** · SEC **Form N-MFP** (monthly MMF holdings).

**§F conditions.**
- ~15 treasury clients drawn from the anchors
- ~120 deposit accounts across **4 currencies**
- ~200 investment positions (MMF, commercial paper, T-bills), maturities laddered
- **Intraday tick series at 5-minute granularity for 30 trading days**, interpolated
  from real daily values, **labelled `synthetic — engineered`**
- **≥ 1 trading day carrying an 8bp intraday move** (the Latency Poisoned instance)
- **≥ 2 clients breaching a concentration limit** under a naively optimal allocation
- **≥ 1 deliberately stale signal**, so `max_staleness` fires and fail-closed is observed

**Engineered.** All balances and positions, limits, mandates, posture overlay, the
intraday tick series, and the stale-signal case.

**Note.** **All public rate sources publish daily; the product's premise is
intraday movement.** The interpolated tick series is mandatory and must be labelled
— presenting interpolated ticks as observed market data misrepresents the source.
Same shape as the Wave 5 booking-lag engineering.

---

### T3 · rating-and-spread-migration — `credit-risk.rating-migration.v1`

**Stores.** Postgres: TRACE observations, instrument reference, benchmark curve,
scale mapping, thresholds. Fluree: rating-action events, issuance/redemption events,
`issuedBy` edges, **internal risk-grade assertion history**.

**New public sources.** **FINRA TRACE** (publicly disseminated, delayed) ·
8-K **Item 2.03** (debt issuance) · issuer self-disclosed ratings in 10-K/8-K narrative.

**⚠️ Licensing boundary.** **Agency ratings from S&P, Moody's, Fitch are licensed
and NOT free to redistribute.** Treat "agency rating feed" as **unavailable**, not
as an integration to build. Three legitimate legs instead: issuer self-disclosure
(public because the filer published it), market-implied quality from TRACE spreads,
and the synthetic internal grade.

**§F conditions.**
- **~30 obligors with publicly traded debt TRACE actually carries observations for**
- ~60 instruments, laddered by maturity
- 24 months of TRACE observations + matched benchmark curve points
- Internal grade history quarterly, with **≥ 4 off-cycle reratings**
- **≥ 3 divergence cases** (spread widens, grade unchanged), **≥ 1 where the grade
  later moved to confirm the market**
- **≥ 1 obligor with a rating action in a real 8-K**
- **≥ 2 thinly-traded instruments with observation gaps** (sparse-series handling)

**Engineered.** Internal grade history, scale mapping, divergence thresholds,
rerating triggers, instrument→issuer crosswalk where TRACE reference data is thin.

**Note.** Resample, **do not interpolate across a rating action** — a grade is a
step function; smoothing invents states that never existed.

---

### T3 · credit-surveillance-early-warning — `credit-risk.early-warning.v1`

**Stores.** Fluree: 8-K event assertions, `signalAbout`/`triggeredBy` edges, prior
observation ledger points. Postgres: WARN notices, GDELT, spreads, trend deltas,
weights, thresholds.

**New public sources.** **State WARN Act notices** (free, per state) · **GDELT
Project** event/mention streams (**15-minute cadence, entity-tagged**) · 8-K Items
**2.04 / 1.01 / 2.03 / 5.02 / 4.01 / 4.02**.

**§F conditions.**
- ~50 anchors under surveillance
- **~400 signal events** across 18 months, distributed so composite scores vary
- **≥ 2 obligors with a real 8-K Item 2.04**
- **≥ 3 obligors with real WARN notices matched by name, ≥ 1 deliberately ambiguous match**
- ~200 GDELT mentions, weighted toward a handful of names
- **≥ 1 composite case where three individually-subthreshold signals breach escalation**
- **≥ 1 scripted cascade**: an Item 2.04 lands and invalidates the covenant product,
  exposure rollup, and collateral coverage from a single event
- Prior observation points seeded for every obligor (so first sweep is a delta, not a cold start)

**Engineered.** Signal weights, escalation thresholds, prior observation points,
the composite case, the scripted cascade.

**Note.** GDELT is the **only public source in the catalog with a sub-daily native
cadence** — that is what makes three decay regimes (media ~7d, WARN ~180d, 8-K no
decay) demonstrable from public data alone.

---

### T3 · fx-post-trade-reconciliation — `markets.fx-reconciliation.v1`

**Stores.** Postgres: Part 43 records, FX rates, settlement conventions, internal
trade records per system, thresholds. Fluree: `observedIn` edges, system observation
timestamps and **clock offsets**, `amends` chains, the timing-artefact breaks.

**New public sources.** **CFTC Part 43 real-time public dissemination** (DTCC and
ICE SDR portals — timestamped, **notionals capped and banded**) · **ISO 20022**
published message schemas · Fed H.10 / ECB rates (shared with treasury).

**§F conditions.**
- **~500 FX trades** across **6 currency pairs**, structure/timing patterned on real Part 43
- **3 internal systems** (trading, settlement, risk), each with its own recorded clock offset
- **~60 breaks, ⅔ timing-attributable and ⅓ genuine**
- **≥ 10 trades with amendment chains**, ≥ 3 with two or more amendments
- **≥ 1 break that inverts under `align_clocks`** — the product's entire argument
- **≥ 1 genuine break surviving alignment** (so it isn't explaining everything away)
- Reference rates covering every value date

**Engineered.** All internal trade records, system observations, clock offsets,
amendment chains, thresholds, and **both** break populations.

**Note.** Part 43 notionals are banded for anonymity — **do not attempt to
reconstruct true notionals**. The product's subject is *when* systems observed a
trade, not exact economics.

---

### T4 · credit-memo-context — `credit-risk.credit-memo.v1`

**Stores.** MongoDB: 10-K Item 1A/Item 7, 10-Q MD&A, 8-K EX-99, credit agreement
text, passages, internal memoranda. Postgres: peer facts, benchmarks, GDELT,
relationship history, templates, debt weightings. Fluree: ECOA/Reg O/limit envelopes.

**New public sources.** 10-K **Item 1A / Item 7** full text · **10-Q** MD&A ·
8-K **EX-99** exhibits · SEC XBRL **`frames` API** (already used Wave 2 for peers).

**§F conditions.**
- ~20 obligors with full memo-grade coverage across all five prerequisites
- ~60 filed documents (10-K, 10-Q, EX-99, EX-10) with structure-aligned passages
- ~40 internal credit memoranda from prior cycles
- **Peer sets of genuinely varying size — ≥ 1 with 15+, ≥ 1 with only 3**
- **≥ 1 obligor breaching `debt_tolerance`** (fail-closed observed)
- **≥ 1 cascade case**: an unresolvable covenant definition in `covenant-cross-reference`
  propagating debt into the memo
- 4 memo types with distinct section templates · ≥ 2 policy versions

**Engineered.** Internal memoranda, relationship history, section templates, policy
envelopes, debt weightings, the tolerance-breaching case.

**Note.** Peer thinness is **the catalog's most natural source of real Context
Debt** — it arises from `frames` coverage itself rather than from an engineered gap.
A benchmark from 3 comparables is arithmetically valid and analytically weak.
`covenant-cross-reference` already loaded ≥ 1 unresolvable definition (Wave 6) —
**that cascade case has an existing carrier.**

---

### T4 · kyc-refresh-beneficial-ownership — `compliance.beneficial-ownership.v1`

**Stores.** Fluree: PSC person nodes, ICIJ relationships, `identifiedAs`/`sameAs`
edges with confidence, residency constraints, the engineered cycle. Postgres: UK
company records, OpenCorporates, OFAC, variant rules, thresholds, refresh state.
MongoDB: KYC document text + passages.

**New public sources.** **UK Companies House PSC register** (free bulk, person-level) ·
UK Companies House company/officer bulk · **OpenCorporates** · **ICIJ Offshore Leaks** ·
**OFAC SDN + Consolidated** (daily XML/CSV).

**§F conditions.**
- ~50 anchor entities with chains reaching natural persons
- **~200 pseudonymized person nodes** preserving real PSC variant and control-type patterns
- **≥ 3 chains reaching depth 5+**
- **≥ 2 engineered ownership cycles**, ≥ 1 spanning jurisdictions, labelled as planted
- **≥ 8 person records with name variants**, **≥ 2 transliteration cases**,
  **≥ 1 genuine false-positive pair** (two different people fuzzy-matching strongly)
- **≥ 1 person crossing a sanctions list below certainty** (exercises the review queue)
- **≥ 2 entities with EU-resident persons**, invisible without EU entitlement
- ~30 KYC documents, **≥ 1 ownership declaration contradicting the registry**

**Engineered.** Pseudonymization, cycles, false-positive pair, residency constraints,
variant rules, refresh state, KYC documents, registry contradiction.

**Note.** 🔴 **CLAUDE.md rule 3 applies in full — PSC records concern real living
people. Pseudonymize at ingestion. Ask the user before touching PSC.** The spec
agrees: the `sameAs` problem is about name *shapes*, and synthetic names carrying
the same shapes teach it identically. **US has no equivalent open bulk BO source**
— the demonstration is cross-jurisdictional partly because data availability is.

---

### T4 · abs-securitization-surveillance — `cib.abs-surveillance.v1`

**Stores.** Postgres: loan-level ABS-EE, ABS-15G repurchases, benchmarks, holdings.
MongoDB: 424B prospectus, 10-D servicer reports, passages. Fluree: tranche structure,
`collateralizes`/`subordinateTo`/`triggeredBy` edges, trigger threshold assertions.

**New public sources.** SEC **Form ABS-EE** loan-level XML · **424B** prospectus ·
**ABS-15G** · **10-D** distribution reports.

**§F conditions.**
- **2–3 real deals across 12 monthly periods** — depth, not breadth (CLAUDE.md rule 6)
- **~20,000 loan records per deal per period at genuine ABS-EE scale** ⚠️ see below
- Full tranche structure, **≥ 4 tranches**, **≥ 3 trigger definitions anchored to prospectus passages**
- **≥ 1 trigger approaching its threshold across the period series** (a trajectory, not a static distance)
- **≥ 1 trigger definition amendment** (so as-of evaluation matters)
- Vintage benchmarks computed across loaded deals
- **≥ 1 principal restricted to aggregate-only granularity**
- **Measured cost figures at each granularity** — "this product's most valuable output for the SDK"

**Engineered.** Internal holdings, materialization policy, privacy constraints, the
restricted principal.

**⚠️ Scale.** 20,000 × 12 periods × 2–3 deals = **480,000–720,000 loan rows**. This
is by far the largest single Postgres load in the project and is *deliberate* — the
fan-out cost must be **measured rather than estimated**. Plan storage and load time
accordingly; do not quietly sample it down, as the measured cost curve is the point.

---

### T5 · mnpi-wall-enforcement — *(already built, Wave 7)*

Listed here only because three T5 specs inherit its wall state and restricted list.
No new requirements surfaced.

---

### T5 · ib-opportunity-synthesis — `cib.opportunity-synthesis.v1`

**Stores.** Fluree: 8-K events, SC 13D/13G, Form 4, wall state. MongoDB: merger
proxies, S-1/S-4, passages. Postgres: 13F, maturity ladder, spreads, GDELT,
USASpending, pipeline, appetite, **ranking weights and ProjectionPlans**.
**SQLite: banker-local prospect notes.**

**New public sources.** SEC **SC 13D / 13G** · **DEFM14A** merger proxies ·
**S-1 / S-4** · **USASpending.gov** (government-contract revenue concentration) ·
Form 13F and Form 4 (shared with client-360).

**§F conditions.**
- ~40 bankers across three perspectives, **overlapping** portfolios
- **~200 prospect entities** — anchors **plus extension**
- ~600 opportunity signals across 12 months
- **≥ 5 real SC 13D filings** against prospects in the set
- **≥ 1 prospect top-3 for the M&A originator and outside top-20 for the DCM banker
  from identical signals** — "the single most persuasive output in this spec"
- **≥ 2 prospects on the restricted list**, absent from affected candidate sets **entirely**
- **~50 banker-local prospect notes in SQLite, ≥ 5 of which change a ranking**
- **Two weight-vector versions**, so a ranking can be replayed under the prior one

**Engineered.** Coverage portfolios, deal pipeline, appetite history, ranking
weights, projection plans, local notes, the divergent-ranking case.

**Note.** The **only product anchored on the consumer** (`banker_id`), not an entity.
Second SQLite consumer after `mnpi-wall-enforcement`.

---

### T5 · aml-typology-match — `compliance.aml-typology.v1`

> ### 🔴 HARD RULE — synthetic entities only
> **Never a named real company or real natural person.** Typology *definitions*,
> sanctions entries, and structural patterns are public and should be used. The
> **entities exhibiting them must be invented**. Enforce at **generation time**,
> not at review. CLAUDE.md rule 2; the spec carries the same constraint verbatim
> and calls it the only anchor constraint in the catalog.

**Stores.** MongoDB: FinCEN/FATF advisory text, SAR narratives, passages. Fluree:
typology structural patterns, filing posture history, ICIJ/OpenCorporates *pattern
reference only*, `transactedWith` edges, disposition rules. Postgres: OFAC, GDELT,
synthetic parties/transactions/alerts, ProjectionPlans. **SQLite: SAR confidentiality
classification.**

**New public sources.** **FinCEN advisories** · **FATF typology reports** ·
**Wolfsberg guidance** · OFAC (shared with kyc) · ICIJ/OpenCorporates (**shape only**).

**§F conditions.**
- **~200 synthetic parties, none corresponding to any real entity or person — verified at generation**
- **~5,000 synthetic transactions** over 18 months
- **~150 alerts, ~30 exhibiting a genuine typology** and the rest noise (so precision is measurable)
- **≥ 4 typologies** — structuring, funnel account, rapid pass-through, trade-based —
  **each anchored to a real FinCEN or FATF advisory passage**
- **≥ 1 network requiring depth 3** to reveal the pattern (invisible at default depth 2)
- **≥ 2 posture versions where a disposition permitted under the earlier is forbidden
  under the later** — demonstrates Policy Blind and the `as_of` requirement together
- **≥ 1 alert whose three perspective renderings differ in assembled content**
- **≥ 1 synthetic party fuzzy-matching a real OFAC entry** at moderate confidence —
  *the matched list entry is real and public; the party is invented*
- **≥ 3 SAR records** with confidentiality classification, invisible to ≥ 1 principal

**Engineered.** Every party, transaction, alert, SAR record and classification,
disposition rules, posture versions, projection plans. Public material contributes
typology definitions, sanctions entries, and advisory text — **nothing else**.

---

### T5 · syndicated-lending-co-lender — `cb.syndicate-co-lender.v1`

**Stores.** Fluree: syndicate composition, agent identity, amendment events,
`participatesIn`/`votesOn`, **bilateral disclosure envelopes**. MongoDB: voting
mechanics, assignment provisions, SNC report, passages. Postgres: NIC RSSD, Call
Reports, own position, competition-law rules, ProjectionPlans. **SQLite:
syndicate-desk local position tracker.** Plus a **separate second instance**.

**New public sources.** **EX-10 Commitment Schedule / Schedule I** (names every
syndicate lender and its pro-rata commitment — real institutions, real shares,
publicly filed) · **FFIEC NIC** RSSD · **FFIEC Call Reports** · **Shared National
Credit Program** public annual report.

**§F conditions.**
- **~6 syndicated facilities with real Commitment Schedules** parsed from filed EX-10
- **~25 syndicate member institutions** resolved to **real LEI and RSSD**
- **1 simulated peer fabric** — a second CCF instance holding one co-lender's position
- **≥ 2 bilateral envelopes with asymmetric terms** (request-scope ≠ disclose-scope)
- **≥ 1 peer disclosing at band granularity** while another discloses exactly
- **≥ 1 live amendment vote with divergent postures**
- **≥ 1 federated request that times out** (fail-closed observed)
- **≥ 1 unattested remote claim** (federation Context Debt exercised)
- **≥ 1 remote product with a shorter TTL than the local composite** (TTL floor binds)

**Engineered.** All positions and postures, disclosure envelopes, competition-law
rules, local tracker, projection plans, the entire peer fabric, and the timeout,
attestation, and TTL-floor cases.

**⚠️ Largest infrastructure item in the catalog.** A second Fluree + Postgres
instance. Confirmed by CLAUDE.md build order: this is second-to-last.

---

### T5 · large-exposure-rwa-concentration — `risk.large-exposure.v1`

**Stores.** Postgres: Call Report / FR Y-9C / FFIEC 101 capital, exposure,
ProjectionPlans. MongoDB: **regime rule text**, methodology documentation, passages.
Fluree: NIC hierarchy, connected/`economicallyDependentOn` edges, limit envelope,
regime version history, insider designations. **SQLite: risk-department limit workbook.**

**New public sources.** **FFIEC Call Report Schedules RC-C, RC-R** · **FR Y-9C** ·
**FFIEC 101** · **FFIEC NIC RSSD hierarchy** · **PRA Rulebook** · **CRR published
text** · **Regulation O (12 CFR 215)** · DEF 14A related-party transactions.

**§F conditions.**
- **~15 connected groups** across the anchors, spanning **≥ 3 jurisdictions**
- **Real Call Report and FR Y-9C data for the reporting bank entity** (see §0 — absent from the estate)
- **≥ 4 `economicallyDependentOn` edges** producing groups control-based grouping
  would miss, **≥ 1 of which changes the binding limit**
- **Regime text ingested for PRA 9/17, CRR, and Reg O**, limits anchored to provisions
- **≥ 2 regime versions with distinct effective dates**
- **≥ 1 group compliant under one regime and in breach under another**
- **≥ 1 proposal that breaches**, **≥ 1 that fits only after mitigation**
- **≥ 1 Regulation O related-party case** from a real DEF 14A disclosure
- **≥ 1 group breaching `debt_tolerance`**
- **Three ProjectionPlans**, examiner rendering carrying full methodology + replay attribution

**Engineered.** Economic-dependency edges, internal limits, methodology
documentation, limit workbook, projection plans, every scripted breach and
mitigation case.

> **⚠️ Correction, 2026-08-27 (Wave 19).** Regime version history was listed
> above as engineered. It is not — it is **real**, sourced from SI 2021/1078
> (the UK statutory instrument that moved the large-exposures articles out of
> assimilated CRR on 2022-01-01) and the PRA Rulebook's own point-in-time
> versions of the Large Exposures Part. Wave 19 Task 9 loaded the CRR, Reg O,
> and PRA regime versions with real effective/effectiveTo dates drawn from
> those sources; nothing about *when a rule applied* was invented, only the
> internal appetite level and the scripted breach/mitigation cases layered on
> top of it.

**Note.** `economicallyDependentOn` is "the one relationship the public estate
cannot supply" — a judgment edge that lives in an analyst's head. Placing it in the
graph with an assertion date and an author is much of what the fabric offers here.

---

## 2 · New public source register

Sources introduced by these 14 specs and **not used in Waves 0–7**. Each needs a
fetch harness entry and a manifest with retrieval date, per the standing convention.

| Source | Access | Used by | Caution |
|---|---|---|---|
| **UCC-1 lien filings** | per-state search; several free, some charge | collateral | ⚠️ **confirm state coverage for chosen anchors before committing** |
| **DEF 14A / DEFM14A** | EDGAR | client-360, ib-opportunity, large-exposure | — |
| **Form 3/4/5** | EDGAR | client-360, ib-opportunity | — |
| **Form 13F** | EDGAR | client-360, ib-opportunity | — |
| **SC 13D / 13G** | EDGAR | ib-opportunity | high-signal M&A catalyst |
| **S-1 / S-4** | EDGAR | ib-opportunity | — |
| **8-K EX-99** | EDGAR | credit-memo | — |
| **10-Q MD&A** | EDGAR | credit-memo | — |
| **NY Fed SOFR** | free API, daily ~08:00 ET | treasury | daily only — intraday must be engineered |
| **Treasury.gov Par Yield Curve** | free XML, daily | treasury, rating-migration | daily only |
| **FRED API** | free, key required | treasury | — |
| **Fed H.10 / ECB reference rates** | free | treasury, fx-recon | daily only |
| **Form N-MFP** | EDGAR, monthly | treasury | — |
| **FINRA TRACE** | publicly disseminated, delayed | rating-migration | ⚠️ **thin-traded names give sparse series** |
| **State WARN Act notices** | free, per state | early-warning | name matching is lossy — deliberately so |
| **GDELT Project** | free, **15-min cadence**, entity-tagged | early-warning, credit-memo, ib-opportunity, aml | only sub-daily public source in the catalog |
| **CFTC Part 43** (DTCC / ICE SDR) | free, timestamped | fx-recon | ⚠️ **notionals capped and banded — do not reconstruct** |
| **ISO 20022 schemas** | free published | fx-recon | schema only |
| **UK Companies House PSC** | free bulk download | kyc | 🔴 **real living people — pseudonymize at ingestion; ask user first** |
| **UK Companies House company/officer bulk** | free bulk | kyc | — |
| **OpenCorporates** | free tier | kyc, aml | aml: **shape reference only** |
| **ICIJ Offshore Leaks** | free structured | kyc, aml | aml: **shape reference only** |
| **OFAC SDN + Consolidated** | free daily XML/CSV | kyc, aml | never cache a screening result |
| **SEC Form ABS-EE** | EDGAR, per deal/period XML | abs | ⚠️ **tens of MB and ~20k loans per file** |
| **424B prospectus** | EDGAR | abs | — |
| **ABS-15G** | EDGAR | abs | — |
| **10-D distribution reports** | EDGAR | abs | — |
| **FinCEN advisories** | free | aml | typology definitions — **public and intended for this use** |
| **FATF typology reports** | free | aml | — |
| **Wolfsberg guidance** | free | aml | — |
| **FFIEC NIC (RSSD)** | free | syndicated, large-exposure | — |
| **FFIEC Call Reports (RC-C, RC-R)** | free | syndicated, large-exposure | — |
| **FR Y-9C** | free | large-exposure | — |
| **FFIEC 101** | free | large-exposure | — |
| **PRA Rulebook** | free published | large-exposure | citable regime text |
| **CRR published text** | free | large-exposure | citable regime text |
| **Regulation O (12 CFR 215)** | free | large-exposure | citable regime text |
| **USASpending.gov** | free API | ib-opportunity | — |
| **Shared National Credit Program report** | free annual | syndicated | — |
| **EX-10 Commitment Schedule / Schedule I** | EDGAR (already fetching EX-10) | syndicated | ⚠️ **Wave 4 did not test for its presence** |

**Explicitly unavailable — do not build an integration.**
**Agency credit ratings (S&P / Moody's / Fitch)** are licensed and not redistributable.

---

## 3 · FIBO binding gaps — ✅ CLOSED 2026-08-17

**Status: done.** All seven areas below are now bound in `docs/ccf_dataprep_v2.md`
under *"Wave 8 extension"* — **121 terms confirmed against published Production,
0 missing**. Two scripts support it:

- `generators/verify_fibo_wave8.py` — discovery over candidate module paths
- `generators/verify_fibo_wave8_confirm.py` — confirmation gate over the exact
  proposed list; **must report 0 missing** before anything enters the table

The pass also found a 🔴 **defect in the v1 starter binding**: the two predicates
carrying all 565 ownership edges are **not FIBO terms**. See `known-issues.md` §0.1.
Not yet remediated — awaiting a decision, since it rewrites an append-only ledger
and changes the shared contract.

Terms checked and **not found**, so deliberately unbound: a bare `NaturalPerson`,
a generic `Securitization` class (only Business-Process classes exist, which are
not Production), a `Waterfall` class, `LegalPerson`, and `FloatingInterestRate`.
`Tranche` **does** exist — in `SEC/Debt/PoolBackedSecurities`, not where the spec
implies.

The Wave 0 extension bound Loans, Guaranty, Syndication, Collateral, and Credit
Events. These 14 specs named the following, now bound:

| Need | Named by | Spec's module hint |
|---|---|---|
| Securitization, tranche, subordination, trigger | abs | "FIBO securitization and structured-finance classes" |
| Derivative and FX instrument classes | fx-recon | "FIBO (Derivatives, FX modules)" |
| Debt instrument / bond classes | rating-migration | "FIBO (Securities, Debt modules)" |
| Instrument and rate/index classes | treasury | "FIBO (Securities, Indices modules)" |
| Natural person, beneficial owner, control | kyc | implied by `NaturalPerson`, `ownsInterestIn`, `controls` |
| Officer / director / employment roles | client-360 | implied by `employedBy`, officer roles |
| Deposit account | collateral, treasury | implied by `DepositAccount` |

⚠️ **CLAUDE.md is explicit: module membership does not pin an IRI.** The Wave 0
pass already found three terms living somewhere other than where the specs imply
(`CreditFacility`, `SyndicatedLoan`, `Guaranty`). Verify every term against the
EDM Council source via `generators/verify_fibo_terms.py` before binding, and expect
some to land under `ex:` as `Covenant` did.

**When bound: update `docs/ccf_dataprep_v2.md` AND state in the response that the
vault mirror `wiki/context-products/content/fibo-iri-binding` needs refreshing.**
Then publish the corrected mirror with `contribute()` (see CLAUDE.md; the
`~/.agent-exchange/` outbox was retired 2026-10-10). You do not edit the vault yourself — the custodian applies it.

---

## 4 · Volume reconciliation across specs

Where two specs size the same population, the larger binds unless noted.

| Population | Claims | Resolution |
|---|---|---|
| Facilities | `facility-terms` ~40 · `credit-exposure` ~40 · `collateral` ~40 | **~40** — consistent |
| Facilities with ≥1 amendment | `facility-terms` ~8 · `covenant-in-force` ~12 | **12** — resolved in Wave 0, flagship binds |
| Deposit accounts | `collateral` ~20 (with set-off) · `treasury` ~120 (4 currencies) | **~120 total, ~20 carrying set-off rights** — different attributes of one population, not a conflict |
| Legal entities | `counterparty-ref` ~500 · `ib-opportunity` ~200 prospects "and extended" | **≥ 500, growing** — prospects overlap anchors and extend past them |
| Anchor obligors | ~50 throughout | **~50** — consistent across all 22 |
| Person nodes | `client-360` 8–25 × 50 clients (public officers) · `kyc` ~200 (pseudonymized PSC) | **two disjoint populations** — public US officers vs pseudonymized UK PSC persons. Do not merge |
| Synthetic AML parties | `aml` ~200 | **disjoint from everything** — hard rule, must match no real entity |

---

## 5 · Proposed wave plan, 8+

Ordered so each wave reuses the last, following Q019 §5 and the existing gate
discipline (partition → join → conditions after every wave).

| Wave | Products | Stores touched | Principal new risk |
|---|---|---|---|
| **8** | **Cast condition audit + FIBO binding pass** — *nothing loads* | — | Resolves §0 before it compounds |
| **9** | `credit-exposure-rollup` · `collateral-and-setoff-coverage` | Fluree, Postgres | UCC-1 state coverage; XBRL debt reconciliation |
| **10** | `client-360-coverage-graph` | Fluree, Postgres | DEF 14A/Form 4 person extraction; deliberate name variants |
| **11** | `rating-and-spread-migration` · `credit-surveillance-early-warning` | Fluree, Postgres | TRACE sparsity; GDELT volume; WARN name matching |
| **12** | `treasury-liquidity-position` · `fx-post-trade-reconciliation` | Fluree, Postgres | Two engineered time series (intraday ticks, clock offsets) |
| **13** | `credit-memo-context` · `kyc-refresh-beneficial-ownership` | + MongoDB | 🔴 **PSC — ask user before fetching** |
| **14** | `abs-securitization-surveillance` | + MongoDB | ⚠️ 480k–720k loan rows; measured cost curve is the deliverable |
| **15** | `ib-opportunity-synthesis` · `aml-typology-match` | all four | 🔴 AML synthetic-only enforced at generation |
| **16** | `syndicated-lending-co-lender` | all + **second instance** | Largest infrastructure item |
| **17** | `large-exposure-rwa-concentration` | all four | Composes six prerequisites; needs a reporting bank entity |

**Wave 8 must come first.** Every wave after it selects data against the cast, and
the four §0 gaps get more expensive to fix with each one.
