# Data Acquisition Plan — ccf_dataprep

**Created:** 2026-08-16
**Status:** Waves 0–11a COMPLETE · all decisions resolved · **resume from `docs/HANDOFF.md`**
**Updated:** 2026-08-19 (Wave 11a — `rating-and-spread-migration` — completed)
**Companions:** `docs/ccf_dataprep_v2.md` (reference + IRI binding contract) · `docs/known-issues.md` (limitations and engineered elements)

> This document exists so work can resume after a restart without re-deriving the
> plan from the specs. It records **what was read**, **what was decided**, **what
> is still open**, and **what order things load in**.

## Progress

| Wave | State | Store | Evidence |
|---|---|---|---|
| **0** — cast, FIBO binding, harness, SQLite, validator | ✅ | — | 50-anchor cast approved; Loans/Guaranty/Syndication bound and verified against EDM Council; vault mirror refreshed by the vault project |
| **1** — identity spine + crosswalk | ✅ | Postgres | 50 anchors with real GLEIF LEIs, 0 orphans |
| **2** — XBRL facts + peer set | ✅ | Postgres | 15,055 facts, 162 peers, 39 obligors genuinely restated |
| **3** — ontology + ownership graph | ✅ | Fluree | 500 entities, 565 edges, cycle planted and labelled, t=11 |
| **4** — facility terms from EX-10 | ✅ | Postgres | 45 facilities across 15 borrowers |
| **5** — temporal covenant layer (**flagship**) | ✅ | Fluree | 3 engineered booking-lag amendments, all diverge under `as_of` vs `known_as_of` |
| **6** — document corpus | ✅ | MongoDB | 59 docs / 15,934 passages, embedded |
| **7** — departmental store | ✅ | SQLite | 5 tables — restricted list, covenant tracker, prospect notes, limit workbook |
| **8** — FIBO binding correction + Ownership/Person/Officer extension | ✅ | Fluree (retype) | v1's 10 starter bindings all invalid, all fixed; 121 new terms bound, 0 missing |
| **9** — credit exposure + collateral/set-off | ✅ | Fluree, Postgres | 16 §F conditions verified by query; phantom-borrower defect found and fixed at source |
| **10** — `client-360-coverage-graph` | ✅ | Fluree, Postgres | 704 Person / 323 CorporateOfficer / 40 Banker / 2,050 Interaction / 32 Deal nodes; `traversal.py` proves depth-2 fan-out exceeds limit=200 for 5 anchors |
| **11a** — `rating-and-spread-migration` | ✅ | Fluree, Postgres | 60 debt instruments, 29,885 spread observations (public benchmark + public OAS + engineered idiosyncratic, split per column); 245 Fluree grade assertions, 215-edge supersession chain; 9 confirmed public rating actions; `series.py` recomputes divergence (4/3), sparsity (2/2), and market dominance (0.19/0.40) from the loaded series |
| **11b** — `credit-surveillance-early-warning` | ⏭ next | Fluree, Postgres | inherits Wave 11a's spread series — no new fetch for that leg |

**Gates (current, Wave 11a):** partition validator **13/13** · conditions register **82 passed, 0 failed** — fully green (the `control-WITHOUT-ownership` gap, §0.4, was closed by a Wave 10 follow-up before this wave branched; Wave 11a added 10 more §F checks on top of that 72/0 baseline) · `series.py` PASS · `traversal.py` 5 clients over limit=200 · `bitemporal.py` 3/3 · `projection.py` exit 0 · `artifact_reproduces_store.py` 40/42 (2 remaining failures are the pre-existing Wave 10 duplicate-row items, unrelated to this wave).

**Estate (current, Wave 11a):** Fluree `fibo-v2` t=408 / 32,266 triples · Postgres `ccf_v2` 40 tables · MongoDB `fibo_v2` 4 collections, 59 docs / 15,934 passages · SQLite `departmental.sqlite` 5 tables. v1 untouched throughout: `fibo:main` t=5, `public` 14/16, Mongo `fibo` 14/16, Neo4j 14 nodes (dropped from the estate).

**Decisions closed:** condition-first screening · LLM-extract + deterministic verify · **Neo4j dropped** (estate is four stores) · GLEIF bulk-filtered at ingestion · UCC-1 not viable for this cast, EX-10 collateral schedules are the fallback source (Wave 9) · DEF 14A / Form 4 person data in scope, no PSC-style pseudonymization (that rule is specific to Companies House PSC records) (Wave 10) · per-CUSIP FINRA TRACE history is licensed and unreachable, spread built as a three-leg model instead (real benchmark + real OAS + engineered idiosyncratic component) (Wave 11a) · Wave 11 split into 11a/11b so 11b's plan is written against 11a's actually-loaded data rather than predictions about it (Wave 11a design, `docs/wave11a-design.md` §0).

**Next checkpoint requiring the user:** none outstanding for Wave 11b — the licensing boundary on FINRA TRACE (bond-level history not free to redistribute in bulk) is already a decided constraint from Wave 11a, not an open question. See `docs/HANDOFF.md` §8 for the Wave 11b brief.

---

## 1 · Source provenance for this plan

Authoritative specs live in the Obsidian vault, reachable via the `obsidian-vault`
MCP server. This plan was written against:

| Artifact | Read |
|---|---|
| `get_response("Q019")` — authoring standard, build ladder, public source register | **full** |
| `context-products/fibo-iri-binding` | **full** |
| `context-products/counterparty-reference-snapshot` (#1, T1) | **full** |
| `context-products/facility-terms-snapshot` (#2, T1) | **full** |
| `context-products/obligor-financial-spread` (#3, T1) | **full** |
| `context-products/corporate-family-tree` (#4, T2) | **full** |
| `context-products/covenant-in-force-as-of` (#8, T3 flagship) | **full** |
| `context-products/covenant-cross-reference` (#13, T4) | **full** |
| `context-products/mnpi-wall-enforcement` (#17, T5) | **full** |

**✅ All 22 now read.** The 14 listed below were read in full on **2026-08-17**
and distilled to **`docs/spec-digest.md`** — per-spec §C/§F, a register of ~38
new public sources, volume reconciliation, and a proposed Wave 9–17 plan. The
inferred needs recorded further down this document are **superseded by that
digest** wherever the two disagree.

Read on 2026-08-17:

`credit-exposure-rollup` · `collateral-and-setoff-coverage` ·
`client-360-coverage-graph` · `treasury-liquidity-position` ·
`rating-and-spread-migration` · `credit-surveillance-early-warning` ·
`fx-post-trade-reconciliation` · `credit-memo-context` ·
`kyc-refresh-beneficial-ownership` · `abs-securitization-surveillance` ·
`ib-opportunity-synthesis` · `aml-typology-match` ·
`syndicated-lending-co-lender` · `large-exposure-rwa-concentration`

Note the vault topic holds **22** articles, not 21 — the extra is
`fibo-iri-binding`, a reference article, not a 22nd product.

---

## 2 · The constraint that drives the ordering

**Obligor selection is a joint constraint-satisfaction problem across all 21 §F
envelopes. It is the only genuine big-bang risk in this project.**

The specs do not ask for 21 independent samples. They ask the *same* ~50 anchor
obligors to simultaneously satisfy conditions scattered across every spec. Select
per-product and the result is overlapping-but-disjoint sets — five stores each
holding a valid slice, and nothing that joins.

Consequence: **Wave 0 selects the cast against the union of all conditions.
Nothing bulk-fetches until that list is agreed.**

### Three risk classes, deliberately separated

Bundling these into one "load" step hides the only one that is actually hard.

| Class | Failure mode | Example |
|---|---|---|
| **Fetch** | Loud — works or doesn't | GLEIF bulk download, XBRL API |
| **Extract** | **Silent** — parses cleanly, means the wrong thing | EX-10 covenant article, Exhibit 21 |
| **Engineer** | Misrepresentation if unlabelled | planted cycle, booking lag |

---

## 3 · The waves

Each wave is independently fetchable, loadable, and validatable. Each ends at a
gate that must pass before the next starts.

| Wave | Acquires | Store | Unblocks | Fetch type |
|---|---|---|---|---|
| **0** | Obligor cast · FIBO Loans binding · manifest harness · SQLite · validator skeleton | — | everything | screening only |
| **1** | GLEIF L1 · `company_tickers` · submissions API · **the crosswalk** | Postgres | #1 | bulk + API |
| **2** | XBRL `companyfacts` + `frames` | Postgres | #3 | API only |
| **3** | FIBO T-Box · GLEIF RR-CDF L2 · Exhibit 21 | Fluree | #4 | bulk + parse |
| **4** | EX-10 structured terms · 8-K Item 1.01 | Postgres | #2 | parse |
| **5** | Covenant structure · amendment events · **the booking lag** | Fluree | **#8 flagship** | parse + engineer |
| **6** | EX-10 full text · passages · embeddings | MongoDB | #13 | text + derive |
| **7** | Restricted list · wall state · projection plans | SQLite | #17 | engineer |
| **8** | ✅ Read the 14 specs · ✅ bind 7 FIBO areas (121 terms) · **cast audit pending** | — | 9–17 | none — reading only |
| **9+** | See `docs/spec-digest.md` §5 for the proposed Wave 9–17 ladder | all | — | — |

### Wave 0 — Decide and bind *(nothing loads)*

1. **Screen the obligor cast.** EDGAR full-text search over EX-10 for
   `"Consolidated Leverage Ratio"` + `"as defined in Section"`, cross-filtered
   against 8-K Item 2.04 history, XBRL restatement chains, and GLEIF RR-CDF
   depth. Output: ~50 anchors + ~150 peers, each annotated with **which §F
   conditions it satisfies**. → **user approval gate** (CLAUDE.md open decision)
2. **Extend the FIBO binding** for the Loans module — facility, covenant,
   guarantee, cross-default. Verify each IRI against `spec.edmcouncil.org` or the
   `edmcouncil/fibo` repo *before* writing. Update `docs/ccf_dataprep_v2.md`,
   then **flag the vault mirror for refresh** in the response.
3. **Fetch harness + manifest schema.** `.gitignore` already exempts
   `sources/**/manifest.json` — record source, URL, retrieval date, checksum,
   licence.
4. **Install SQLite**, create the DB file, record the path in v2.
5. **Partition validator skeleton** — written against empty stores so it fails
   loudly from day one. This is the inverted `compare_backends.py`: it asserts
   each store holds its slice **and nothing it doesn't**.

**Gate:** obligor list approved · Loans terms bound and verified against EDM
Council · validator runs and correctly reports "all stores empty".

### Wave 1 — Identity spine · *the crosswalk comes first*

Non-negotiable rule #4 is absolute: `internal_client_id` ↔ `LEI` is generated
**before any internal element loads** — before risk grades, RM assignments,
entitlements, anything.

- GLEIF LEI-CDF Level 1 → ~500 US/UK corporates (filter hard at ingestion)
- SEC `company_tickers.json` + EDGAR submissions API → CIK, SIC, fiscal year end
- **Engineered:** the crosswalk; internal risk grades; RM assignments;
  3 principals with differing jurisdiction entitlement; ~5 `LAPSED` entities

Real GLEIF LEIs for the ~50 public anchors. Visibly distinct synthetic
identifiers for the invented cast (Acme, Beta, Gamma, Delta, Omega) — **record
which format signals which in `docs/ccf_dataprep_v2.md`.**

**Gate:** every anchor resolves LEI → CIK → ticker → `internal_client_id`,
bidirectionally, zero orphans.

### Wave 2 — Financial facts · *cheapest wave, do it early*

Pure API, no parsing — lowest-risk wave and a good confidence build.
`companyfacts` ships `period_end` / `filed_date` / `accession_number` natively,
which is `T` and `L` for free at attribute granularity.

- `companyfacts` for ~50 anchors × 8 periods
- `frames` for ~150 peers at **matching periods only**
- **Engineered:** US-GAAP tag → spread-line mapping; ratio definitions; internal
  adjustments; the restatement subset if absent naturally

**Gate:** ≥3 obligors have two accessions for the same period, so
`basis=as-reported` and `basis=latest-restated` return genuinely different
numbers.

### Wave 3 — Ownership graph · *first Fluree load*

FIBO ships as OWL/RDF and loads unmodified — the ontology **is** the schema.

- FIBO T-Box: Business Entities + Ownership & Control modules
- GLEIF RR-CDF Level 2 → ~800 ownership edges
- EDGAR Exhibit 21 parse → subsidiary lists, ~30 non-LEI stub entities
- **Engineered:** 1 cross-shareholding cycle spanning 3 entities, labelled
  `synthetic — engineered`; depth padding if the natural sample is shallow

Fluree nodes carry `lei` + display label **and nothing else** — first real test
of single-writer discipline.

**Gate:** partition validator confirms Fluree holds no attribute Postgres owns ·
≥2 families reach 4 hops · cycle present, labelled, and returned as a *finding*
rather than an error.

### Wave 4 — Facilities *(requires Wave 0.2 Loans binding)*

- EX-10 header and Article II → ~40 facilities (revolver, term A, term B,
  delayed draw)
- 8-K Item 1.01 → amendment numbers and effective dates
- 10-K debt footnote → aggregate reconciliation
- **Engineered:** outstanding balances; undrawn availability; internal facility
  ratings; `facility_id` ↔ borrower LEI crosswalk

Extraction happens **at build time**, producing Postgres rows. The source
document is not addressable until MongoDB arrives at Wave 6. A T1 example that
reaches into a document has silently become a T4 example.

### Wave 5 — Temporal covenant layer · **the flagship**

The critical condition is not a count:

> **≥1 amendment whose effective date and booking date are separated by weeks,
> with a drawdown falling inside the gap.**

Without it, `as_of` and `known_as_of` return identical answers for every query
and the bitemporal model reads as redundant machinery. Q019 §5 calls this "the
single most important engineered element in the catalog."

- EX-10 financial-covenants article + defined-terms article → covenant structure
- 8-K Item 1.01 (amendments), Item 2.04 (acceleration/breach) → the temporal
  spine. This is a **free, timestamped, publicly filed covenant-lifecycle event
  stream** — it does not need inventing, only selecting for.
- **Engineered:** booking dates and the lag; policy version history; drawdown
  timestamps; breach thresholds

**Gate:** every condition in §4 below proven by a **query**, not a count.

### Wave 6 — Document corpus (MongoDB)

The only wave with a genuine build-time semantic stage. Q019 §7 forbids LLM
inference *inside assembly* but explicitly permits extraction at ingestion as "a
separate build-time semantic stage subject to §8.4 Algorithmic Verification" —
an LLM-proposed `definedBy` edge is a **candidate** until a deterministic check
confirms the referenced section exists at the cited offset.

- ~15 EX-10 agreements as full text, plus amendments and 10-K debt footnotes
- **Structure-aligned** passage spans (section/subsection boundaries preferred
  over a fixed character window) with offsets → ~2,500 passages + embeddings
- **Engineered:** ~20 internal credit memoranda; classification/residency tags;
  ≥1 unresolvable definition (so Context Debt is emitted, not theoretical);
  ≥2 near-duplicate covenants across different facilities

Passage anchors resolve **by offset, never by re-searching text** — a re-search
can match a different occurrence and silently relocate the citation.

### Wave 7 — Departmental store (SQLite)

~95% engineered. Two hard rules bind here and are enforced **at generation time,
not at review**:

- **AML (`aml-typology-match`) — synthetic entities only.** Never a named real
  company or real natural person. Typology definitions and sanctions entries are
  public and should be used; the entities exhibiting the patterns are invented.
- **PSC person data — pseudonymize at ingestion.** UK Companies House PSC
  records concern real living people. Preserve name-variant structure, control
  types, ownership cycles; replace identities. `.gitignore` already blocks
  `**/pseudonym-map.*`.

---

### Wave 9 — decision: UCC-1 is not viable for this cast; EX-10 is the source

**Probed 2026-08-17.** `collateral-and-setoff-coverage` §C names UCC-1 filings as
"the strongest public source for real security interests" and instructs the
project to **confirm coverage before committing**. Confirmed, and the answer is no.

Under **UCC §9-307** a registered organization files in its **state of
incorporation**, so the cast's domicile *is* its filing-state distribution:

| Filing state | Anchors | Share | Public search |
|---|---|---|---|
| **US-DE** | 32 | **64%** | ❌ **Closed to the public** — Delaware-authorized searchers only, $25/debtor plus a mandatory $25 expedite |
| US-MD | 8 | 16% | ✅ Free, by debtor name, via SDAT |
| US-NV · US-FL · US-OH · US-MN | 6 | 12% | mixed, four separate interfaces |
| NZ · CA-BC · CA | 3 | 6% | no UCC regime |

**Two independent blockers, not one.** The cost is secondary; the hard stop is
that Delaware's database is **not publicly searchable at all**. Even paying, this
project cannot query it directly. Best realistic coverage is ~28% of the cast,
scraped across five incompatible state interfaces.

**Resolution — take the fallback the spec already sanctions:** *"Where UCC data
is thin, the `securedBy` topology falls back to EX-10 collateral schedules, which
are uniformly available but less granular."*

**The fallback is measured, not assumed.** Against the 59 filed documents already
fetched:

| Signal | Obligors | Serves |
|---|---|---|
| collateral (any mention) | 27 | the population |
| security agreement · "grants a security interest" | 15 · 13 | `securedBy` edges |
| first / second lien | 10 | **lien priority** — the `shared_collateral=priority` case |
| real property · equipment · receivables · inventory | 25 · 28 · 25 · 21 | §F's four asset categories |
| negative pledge | 8 | §F wants ≥ 1 |
| set-off · netting | 25 · 20 | `setOffAgainst` / `nettedUnder` |

Ample for §F's ~60 assets across ~40 facilities.

**What is lost, and it must be labelled.** UCC-1 supplies a real *filing date*,
which is what establishes priority between competing secured parties. EX-10
gives contractual first/second-lien language but **no filing dates**, so lien
priority becomes `synthetic — engineered` rather than `public`. Recorded here
because the spec leans on filing date as the priority mechanism, and presenting
an engineered priority ordering as filed fact would misrepresent the source.

The debtor-name → LEI fuzzy match the spec expects UCC to force is **not
exercised** by this route: EX-10 exhibits already resolve to a filer CIK. That
entity-resolution problem lands properly in `kyc-refresh-beneficial-ownership`.

---

## 4 · Conditions register *(seed — from the 8 specs read)*

Every `≥ N` extracted so far. Each needs a query that proves it is **satisfiable
against loaded data**, not merely counted. This becomes the regression suite.

### #1 counterparty-reference-snapshot
- ~500 legal entities from GLEIF L1 (US/UK corporates)
- ~50 anchor obligors with full internal overlay
- ~5 entities in `LAPSED` registration status
- 3 principals with differing jurisdiction entitlement

### #2 facility-terms-snapshot
- ~40 facilities spanning revolver / term A / term B / delayed draw
- ~8 facilities with ≥1 amendment · **see conflict note below**
- ~4 facilities with syndicated structure
- pricing grids with ≥3 leverage tiers

### #3 obligor-financial-spread
- ~50 anchors × 8 periods of tagged facts
- ~150 peer entities at matching periods
- ~3 obligors with a genuine restatement (same period, two accessions)
- ~2 obligors with non-December fiscal year end

### #4 corporate-family-tree
- ~500 entities / ~800 ownership edges in Fluree
- ~50 anchors each resolving to a family of 4–15 entities
- **≥2 families reaching 4+ hops** (so `depth=3` visibly truncates)
- **1 engineered cross-shareholding cycle**, labelled, spanning 3 entities
- ~30 non-LEI stub entities from Exhibit 21
- ≥1 family spanning three jurisdictions

### #8 covenant-in-force-as-of *(flagship)*
- ~40 facilities, **~12 carrying ≥1 amendment**
- ≥3 facilities with two or more sequential amendments
- **≥1 amendment with engineered booking lag + a drawdown inside the gap**
- ≥2 obligors with a real 8-K Item 2.04 in filing history
- ≥4 covenant types per facility (leverage, interest coverage, fixed-charge, liquidity)
- ≥2 policy versions with distinct effective dates
- ≥1 covenant in breach at a past date but compliant today
- drawdown events spread across amendment boundaries

### #13 covenant-cross-reference
- ~15 credit agreements as full text
- ≥3 agreements with a filed amendment
- ~2,500 structure-aligned passages with offsets and embeddings
- ≥5 covenants whose definition chain reaches depth 3
- ≥1 cross-document reference (definition incorporating a 10-K convention)
- ≥2 near-duplicate covenants across different facilities
- ~20 internal credit memoranda, classification-tagged
- ≥1 covenant with an unresolvable definition

### #17 mnpi-wall-enforcement
- ~10 issuers, ≥3 on the restricted list
- 3 test principals with distinct credentials and `ProjectionPlan`s
- ~30 deal/engagement records, ≥10 MNPI-tagged
- ~40 research notes, ≥8 in draft under embargo
- ≥1 issuer where all three principals' products differ in node count, edge
  types, and document set simultaneously
- ≥1 wall crossing with a recorded date
- ≥1 Reg FD event converting private → public mid-series
- ≥1 measured case where restricted documents *would have* altered similarity
  ranking had they participated

> **⚠ Cross-spec conflict.** `facility-terms-snapshot` §F asks for "~8 facilities
> carrying at least one amendment"; `covenant-in-force-as-of` §F asks for "~12"
> over the same facility population. **Resolution: take 12** — the flagship's
> requirement binds. Exactly the class of conflict this register exists to catch.

---

## 5 · Three gates, applied after every wave

1. **Partition gate.** Each store holds its slice *and nothing it doesn't*. The
   inverted validator — v1's `compare_backends.py` asserted the stores agreed;
   this asserts they deliberately differ. Runs after every wave, not at the end.
2. **Join gate.** Every correlation key the wave introduces resolves in both
   directions with zero orphans.
3. **Conditions gate.** Every `≥ N` from §4 that the wave was responsible for is
   satisfiable by a real query.

A wave that passes counts but fails a condition is **not done**.

---

## 6 · Standing rules carried from CLAUDE.md / Q019

- **Load order:** ontology → crosswalk → entities → relationships → temporal
  assertions → documents → departmental.
- **Idempotency:** every loader safely re-runnable. Expect many reloads.
- **Single-writer:** one store authoritative per element. Fluree nodes carry
  `lei` + label only; attributes resolve from Postgres. Never duplicate "for
  convenience."
- **No OWL inference:** Fluree runs without reasoning. Type entities explicitly
  for every role to be queried against.
- **Normalize to full IRIs** before comparing across stores. Fluree SPARQL may
  return compact forms; Mongo/Neo4j `types` arrays may hold only the last path
  segment.
- **Three provenance classes**, labelled per element: `public`,
  `synthetic — internal`, `synthetic — engineered`.
- **Binding before generation:** add FIBO terms to `docs/ccf_dataprep_v2.md`
  first, verify against EDM Council, generate, **then flag the vault mirror for
  refresh in the response.** No write path to the vault exists from here.

### Known technical constraint

**Fluree SPARQL 1.1 dropped bounded `{m,n}` property-path repetition** (`+`, `*`,
`?` are supported). Depth-bounded traversal — `corporate-family-tree`'s `depth`
parameter — must be expressed as unioned fixed-length patterns or a recursive
FlureeQL query. Verify the exact form against the deployed Fluree version before
writing the Wave 3 loader.

Fluree also has **no graph-algorithm library**. Cycle detection is application-
side: maintain a visited set in the traversal caller.

---

## 7 · OPEN DECISIONS — answer before Wave 1

### 7.1 · Obligor cast: screening approach *(BLOCKING)*

| Option | Trade-off |
|---|---|
| **Condition-first, ~50** *(recommended)* | Screen for entities jointly satisfying the union of §F conditions, then fill to ~50. Guarantees every `≥N` is satisfiable by construction. More work up front; may force a smaller cast if conditions prove scarce. |
| Size-first, ~50 by sector | Representative spread across SIC bands, then audit which conditions fall out naturally and engineer the gaps. Faster, more natural-looking. Risks discovering late that 8-K 2.04 / restatement / 4-hop family have no natural carrier and must all be planted — which weakens the "public anchor" claim for the flagship. |
| Narrow deep set, ~20 | Cheapest to fetch and validate. Conflicts with published floors (~50 anchors, ~500 entities); would require explicitly relaxing two envelopes. |

*The "~15 hits" screening estimate in Wave 0 is an estimate, not a measurement —
the EDGAR screen has not been run.*

### 7.2 · EX-10 extraction approach *(BLOCKING — Waves 4/5/6)*

| Option | Trade-off |
|---|---|
| **LLM-extract + deterministic verify** *(recommended)* | LLM proposes covenant/definition/edge candidates; deterministic checker confirms the cited section exists at the cited offset before assertion. Exactly what Q019 §7 permits and §8.4 requires. Unverified candidates drop to Context Debt. |
| Deterministic parse only | Byte-reproducible, no model dependency. But ~15 agreements from different firms use different drafting conventions; likely per-document rule tuning. |
| Hand-curate the 15 | Highest fidelity, every span verified by construction. Slow; no path to widening the corpus; re-work on every amendment. |

### 7.3 · Neo4j — RESOLVED 2026-08-16: DROPPED

**Not part of the v2 estate.** The fabric spans four stores.

GDS and APOC are absent, so it fails Q019 §3's test directly. Community edition
also allows only one user database, so v2 could not be isolated from v1 as it is
everywhere else. Plain Cypher would have covered a genuine gap — Fluree SPARQL
dropped bounded `{m,n}` repetition — but not enough to justify a fourth loader
and a store authoritative for nothing.

Replacements, both straightforward at ~500 entities / ~800 edges:
depth-bounded traversal becomes unioned fixed-length SPARQL patterns or
recursive FlureeQL; cycle detection becomes Tarjan's SCC in application code.
Full rationale in `docs/ccf_dataprep_v2.md`.

### 7.4 · GLEIF acquisition *(not blocking)*

L1 concatenated file is GB-scale; ~500 entities are needed.
**Recommendation: bulk download, filter hard at ingestion**, keep the payload out
of git per the existing `sources/**` rule and commit only the manifest.

---

## 8 · Session state at time of writing

- `autoMode` config moved from `~/.claude/settings.json` to
  `.claude/settings.json` (project scope); verified byte-identical. Untracked —
  **not yet committed**.
- Obsidian vault confirmed reachable; 15 topics, `context-products` holds 22
  articles.
- **Nothing fetched. Nothing loaded. No FIBO terms bound. SQLite not installed.**
- This plan is **proposed, not agreed** — §7.1 and §7.2 are unanswered.
