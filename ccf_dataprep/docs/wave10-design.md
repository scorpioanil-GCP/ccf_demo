# Wave 10 design — `client-360-coverage-graph`

**Written:** 2026-08-18 · **Status:** approved, not yet implemented
**Spec:** `coverage.client-360.v1`, tier 2 · **Stores:** Postgres + Fluree only

> Re-read from the vault on 2026-08-18, per the standing rule that specs are
> patched in place. It had been: §C now carries a row absent from
> `spec-digest.md` — the FIBO officer, director, and employment classes, noted
> as bound as of Wave 8, with `employedBy` binding to `isEmployedBy`.

---

## 0 · Decisions taken

Three questions were put to the user before any fetch. All three are settled;
do not re-open them.

| # | Question | Decision |
|---|---|---|
| 1 | Do DEF 14A / Form 4 identities enter as filed, or pseudonymized? | **As filed, real names.** Provenance stays `public` exactly as §C writes it |
| 2 | How wide does the public-source fetch go? | **Full §C sweep** — Form 4 + DEF 14A + Form 13F + 8-K Item 5.02 |
| 3 | How is person identity keyed? | **Hybrid** — real SEC CIK where it exists, minted id where it does not |

**Decision 1 is scoped to DEF 14A and Form 4.** CLAUDE.md rule 3 names UK
Companies House PSC specifically and is untouched: PSC person data is still
pseudonymized at ingestion when Wave 13 reaches it. Rule 2 (AML synthetic-only)
is likewise unaffected — no AML data loads in this wave.

The recommendation put to the user was to pseudonymize, on the grounds that the
project's settled practice attaches fabricated facilities and covenants to real
*companies*, and that the line it draws is entity versus natural person. Wave 10
is the first wave to attach fabricated *behaviour* — meetings, calls,
relationship strength — to a real named individual. The user chose to load as
filed. Recorded here so the reasoning is available if the question returns.

---

## 1 · Feasibility, measured before committing

Wave 9 established the pattern: probe the named source, and if it does not
support the §C row, say so and take the sanctioned fallback. All four sources
were probed on 2026-08-18. **All four are reachable.** No fallback needed.

### 1.1 · Form 4 and DEF 14A coverage across the 50 anchors

| Signal | Result |
|---|---|
| Anchors with a CIK in `crosswalk` | 50 / 50 |
| Anchors with >= 1 DEF 14A | **48 / 50** |
| Anchors with >= 1 Form 4 | **50 / 50** |
| Anchors with neither | **0** |
| Anchors with 100+ Form 4 filings | 49 / 50 |

The two non-proxy filers are `CrossAmerica Partners LP` (CIK 1538849) and
`GENESIS ENERGY LP` (CIK 1022321). Both are **master limited partnerships**,
which hold no annual shareholder meeting and therefore file no proxy statement.
Neither is a gap: they carry 388 and 591 Form 4 filings respectively.

This corrects `cast_audit.py`, which flags client-360 as NEEDS FETCH with the
note *"anchors that are not proxy filers cannot supply the client-side people."*
That is false for this cast, because it assumed DEF 14A was the only path.

### 1.2 · Form 4 yield per issuer, at a 40-filing lookback

| Issuer | Parsed | Distinct reporting owners | With a role flag | With a title |
|---|---|---|---|---|
| CHARTER COMMUNICATIONS | 40 / 40 | 25 (**21 natural persons**) | 24 | 6 |
| GENESIS ENERGY LP | 40 / 40 | 14 | 14 | 8 |
| AGILYSYS INC | 40 / 40 | 13 | 13 | 6 |

Inside §F's 8–25 band at a 40-filing lookback. Titles appear only on officers;
directors carry none. That is a property of the form, not a shortfall.

**Not every reporting owner is a person.** Charter's 25 include `CCH II LLC`,
`CHARTER COMMUNICATIONS HOLDINGS LLC`, `Charter Communications Holding Company`,
and `Liberty Broadband Corp` — corporate 10% owners. See §3 `owner_kind`.

### 1.3 · 8-K Item 5.02 is free

The EDGAR submissions index exposes an `items` field per filing. Item 5.02
selection is therefore a string match on metadata with **no document parsing at
all**. Agilysys alone: 174 8-K filings in the recent index, **34 carrying
Item 5.02**. The repo already relies on this field — `filing_profile` counts
8-K items from Wave 0.

### 1.4 · Form 13F is reachable, in one file

13F is filed per institutional *manager* and lists that manager's whole book, so
finding holders of one issuer is an inverted-index problem rather than a per-CIK
fetch. The SEC publishes quarterly structured datasets which solve it.

**The naming convention changed** and the older `<YYYY>q<N>_form13f.zip` pattern
404s for recent periods. Current form is a date range:

```
https://www.sec.gov/files/structureddata/data/form-13f-data-sets/01mar2026-31may2026_form13f.zip   99.4 MB
https://www.sec.gov/files/structureddata/data/form-13f-data-sets/01dec2025-28feb2026_form13f.zip   90.3 MB
```

`INFOTABLE` carries CUSIP, `NAMEOFISSUER`, value and shares; `COVERPAGE` carries
manager identity. §C asks for 13F as *relationship context* only, so **one
quarter satisfies it** — no time series.

### 1.5 · The EDGAR rendered-document trap

`primaryDocument` for a Form 4 is `xslF345X06/ownership.xml`. That `xsl.../`
prefix is EDGAR's **XSL-rendered HTML view**, not the filing. Requesting it
returns **HTTP 200 and a complete HTML document**, so it fails as XML rather
than as a fetch. The first probe returned 40 silent failures per issuer, three
issuers, zero parsed, with no error status anywhere.

Strip the prefix — the raw XML sits in the same accession folder:

```
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodashes}/ownership.xml
```

Same family as the Wave 9 phantom-borrower defect: **a constructed URL cannot
fail loudly.** Recorded so the loader is written against it from the start.

---

## 2 · The extraction inversion this design rests on

The obvious reading of §C is *"parse DEF 14A to find officer names"* — an
open-ended extraction problem across 48 filers with different drafting
conventions. That is Wave 4's EX-10 difficulty at greater scale.

**Invert it. We do not need to discover names in DEF 14A. We need to find
renderings of names we already hold.** Form 4 supplies the roster first, with
real CIKs. DEF 14A is then searched for known surnames; 8-K Item 5.02 is
searched for a known person plus a date.

Two consequences:

- **Yield becomes measurable.** Open-ended extraction has no ground truth, so a
  miss is silent. Bounded extraction has a known answer set, so precision and
  recall are both computable.
- **Partial failure stops being fatal.** If DEF 14A yields renderings for 300 of
  ~600 people, we still hold 600 people from Form 4 and 300 confirmed
  cross-source variants — well past §F's floor of 5. Under the open-ended
  reading, a parsing shortfall would cost the roster itself.

This also makes Form 4 the **spine** and DEF 14A the **enrichment pass**,
inverting §C's listing order. §C lists DEF 14A first; it is the more expensive
and less structured of the two, and it cannot reach the two MLPs at all.

---

## 3 · Data model

Per §C: Postgres owns every attribute (`E`, `P`); Fluree owns every edge (`R`).
No MongoDB, no SQLite in this wave. Fluree nodes carry identity and a display
label only — a `Person` node is a URI, a type, and a name; role, title, dates
and match confidence all resolve from Postgres.

### 3.1 · New Postgres tables, schema `ccf_v2`

| Table | Provenance | Holds |
|---|---|---|
| `person` | `public` | `person_key` PK, `person_key_source` (`sec_cik`\|`minted`), `cik`, `name_as_filed`, parsed name parts, `owner_kind` (`natural`\|`entity`) |

**`person_key` format.** `sec_cik` keys are the zero-padded 10-digit CIK, so they
are visibly real and collide with nothing. Minted keys carry a distinct prefix —
`syn-p-<6 hex>` — following the settled rule that synthetic identifiers take a
visibly distinct format from real ones. A reader can tell which half of the
roster is publicly anchored without consulting `person_key_source`.

| `person_role` | `public` | `person_key` x `lei` x `role` (`director`\|`officer`\|`ten_percent_owner`), `officer_title`, `first_seen`, `last_seen`, `appointment_date`, `appointment_source` |
| `person_name_variant` | `public`, else `synthetic — engineered` | every rendering of a name, tagged by source and rendering form |
| `person_crosswalk` | `synthetic — engineered` | source system x source id -> `person_key`, `match_score`, `match_band`, `is_true_match` |
| `institutional_holder` | `public` | 13F: `manager_cik`, `manager_name`, `cusip`, `value_usd`, `shares`, `report_period`, `issuer_match_band` |
| `banker` | `synthetic — internal` | ~40 bankers: `banker_id`, name, `role` (coverage\|product\|credit), `seniority`, desk |
| `coverage_assignment` | `synthetic — internal` | `banker_id` x `lei`, `is_primary`, `assigned_date` |
| `interaction_participant` | `synthetic — internal` | `interaction_id` x (`person`\|`banker`) x key |
| `scoring_weight` | `synthetic — internal` | relationship-strength weights, policy-versioned (`P`) |

`match_band` and `match_score` deliberately mirror the `lei_match_band` /
`lei_match_score` columns `legal_entity` already carries. One imperfect-join
pattern across the estate, not two.

**`owner_kind` earns its column.** Corporate 10% owners must not become `Person`
nodes, and recording them as `entity` rather than dropping them keeps the count
auditable — the "aggregates hide the decision" lesson from Wave 8. They are also
a genuine bridge to the Wave 3 ownership graph, since `Liberty Broadband Corp`
is a real controlling holder of a cast member.

### 3.2 · Extended, not duplicated

Wave 7 already left a live CRM stub. Single-writer discipline says grow it.

| Table | Now | After | Change |
|---|---|---|---|
| `interaction` | 50 | ~2,000 | add `channel`, `subject`, `need_to_know` |
| `deal` | 32 | as needed | no schema change expected |
| `principal` | 3 | 3 | unchanged — reused for the need-to-know condition |

### 3.3 · Fluree — terms and types

All FIBO terms below were **bound in Wave 8 and verified against the contract on
2026-08-18**. Wave 10 requires no new FIBO bindings.

| Spec relationship | Term | Status |
|---|---|---|
| `employedBy` | `fibo-fnd-org-fm:isEmployedBy` | bound |
| officer of | `fibo-be-oac-exec:isOfficerOf` | bound |
| director of | `fibo-be-oac-exec:isDirectorOf` | bound |
| `coversClient` | **`ex:coversClient`** | new extension |
| `participatedIn` | **`ex:participatedIn`** | new extension |
| `relatedToDeal` | **`ex:relatedToDeal`** | new extension |

Types: `fibo-fnd-aap-ppl:Person` (bound), `fibo-be-oac-exec:CorporateOfficer`
(bound), plus new extensions **`ex:Banker`**, **`ex:Interaction`**, **`ex:Deal`**.

**An asymmetry to record rather than paper over.** FIBO gives `CorporateOfficer`
as a class but has no `Director` class — directorship exists only as an edge,
and `BoardOfDirectors` is the board, not the person. So officers carry a type
and directors do not. `ex:Director` is deliberately **not** minted to make the
model look symmetric.

**Third consecutive wave in which FIBO has no vocabulary for the bank's own
operational graph** — `Covenant` in Wave 5, `pledgedBy` / `setOffAgainst` /
`nettedUnder` in Wave 9, coverage and interaction now. This should reach the
vault as a single pattern finding, not three unrelated notes.

### 3.4 · Instance URIs

Follow the documented pattern, `ex:{LocalName}`, and **never construct a URI
for a node that has not been loaded.** Edge targets are taken from loaded nodes.
`partition.py`'s typed-edge-target check, added in Wave 9, enforces this.

---

## 4 · Pipeline

Load order follows CLAUDE.md's stages. Each step is a separate, re-runnable,
`--dry-run`-capable script per existing convention.

| # | Script | Does |
|---|---|---|
| 1 | `generators/fetch_form4.py` | 50 issuers x ~40 filings (~2,000 requests, ~5 min at 8 req/s). Parse `reportingOwner` and `reportingOwnerRelationship`. **Strip the `xsl.../` prefix** (§1.5) |
| 2 | `generators/fetch_def14a.py` | 48 filers, most recent proxy. Bounded search for known surnames -> renderings, titles, seniority |
| 3 | `generators/fetch_8k_502.py` | Select by the `items` field (free), fetch only matches, extract appointment and departure dates for known people |
| 4 | `generators/fetch_13f.py` | One quarterly dataset, filter `INFOTABLE` to the anchors by `NAMEOFISSUER`, join `COVERPAGE` |
| 5 | `generators/resolve_persons.py` | Build `person_crosswalk` and `person_name_variant`, with match bands |
| 6 | `generators/generate_coverage.py` | The entire bank side: bankers, assignments, ~2,000 interactions, need-to-know flags, scoring weights |
| 7 | `loaders/load_postgres_wave10.py` | Attributes |
| 8 | `loaders/load_fluree_wave10.py` | Edges and types |

---

## 5 · The §F conditions, and how each is created

| # | Condition | Mechanism | Class |
|---|---|---|---|
| 1 | ~50 anchors, 8–25 people each | Form 4; lookback starts at 40 filings and doubles to a **hard cap of 160** until >= 8 natural persons. An anchor still short at 160 is recorded as a shortfall, not padded | `public` |
| 2 | ~40 bankers across three roles | generated | `synthetic — internal` |
| 3 | ~2,000 interactions over 24 months, **recency-weighted** | explicit decay; verified as a distribution, not a count | `synthetic — internal` |
| 4 | **>= 1 client exceeding `limit=200` at depth 2** | concentrate interactions on the densest anchor | `synthetic — engineered` |
| 5 | >= 5 person records with name variants | **natural first** — Form 4 `SRINIVASAN RAMESH` against DEF 14A `Ramesh Srinivasan`; plant only if measured yield falls short | `public`, else `synthetic — engineered` |
| 6 | >= 3 coverage gaps | withhold >= 3 senior officers from every participant row | `synthetic — engineered` |
| 7 | ~10 need-to-know interactions | reuse Wave 7's three principals | `synthetic — internal` |
| * | **CLAUDE.md rule 5 false-positive pair** | the natural `Davison James E` / `Davison James E. Jr.` collision at Genesis Energy — distinct CIKs 1403411 and 1403412, near-unity fuzzy match | `public` |

### 5.1 · Two conditions counting can fake

**#3 — recency weighting.** A flat 2,000 satisfies the number and defeats the
purpose, because relationship-strength scoring needs a real gradient to measure.
The check asserts recent-quarter density materially exceeds oldest-quarter
density.

**#4 — truncation disclosure.** Cannot be established arithmetically. The
validator runs an actual bounded traversal from the anchor and confirms the node
set exceeds 200 **before** truncation, exactly as §D step 3 requires the limit
be applied inside the traversal rather than in memory.

### 5.2 · The false-positive pair is public, not engineered

The plan of record assumed rule 5's false-positive pair would be
`synthetic — engineered`. The Form 4 probe found a real one: two different
people, distinct SEC CIKs, names that fuzzy-match at near unity, both filing
against the same issuer.

If it survives into the loaded estate the condition is **`public`** — a real
collision, in a real filing, that a real resolver really would get wrong. That is
a stronger demonstration than a planted pair: an engineered false positive proves
the resolver handles a case built for it; a found one proves the case occurs in
the wild. Label it honestly as what it is.

---

## 6 · Validation gates

| Gate | Change |
|---|---|
| `validators/partition.py` | Person, banker and interaction attributes must not appear in Fluree. Register the new `ex:` types as permitted extensions. The Wave 9 typed-edge-target check already guards §3.4 |
| `validators/conditions.py` | Eight new checks — seven §F plus the false-positive pair |
| `validators/traversal.py` | **New.** The depth-2 truncation proof (§5.1) |
| `validators/projection.py` | **Re-run as a regression check** — see §7.1 |
| `sources/screening/published_claims.json` | Updated as terms load, so the next punch list generates itself |

---

## 7 · Risks carried into implementation

### 7.1 · Wave 7 regression via the interaction table

`interaction` grows 40x. `validators/projection.py:119` counts interaction rows
per principal to prove three products yield three shapes. Reading it, the
assertion is that the shapes **differ**, not that they equal fixed values, so
growth should be safe.

**"Should" is not "does."** `projection.py` is re-run as an explicit gate. If the
shapes stop diverging, the generator gets constrained — the validator does not
get relaxed.

### 7.2 · DEF 14A prose parsing

The only unbounded-effort item in the wave. Bounded by §2's inversion.
Unresolved candidates drop to the existing `context_debt` table rather than being
forced, per Wave 4 doctrine.

### 7.3 · 13F issuer matching is fuzzy

`NAMEOFISSUER` matched against legal names will produce some false hits. Every
row carries `issuer_match_band`. §C asks for 13F as context only, so an imperfect
match degrades gracefully.

### 7.4 · Person URI construction

The phantom-borrower trap, and §1.5 shows the same failure shape already lying in
wait in this wave's fetch layer. Mitigated by §3.4 and enforced by `partition.py`.

### 7.5 · Vault drift this wave creates

Six new `ex:` terms (`coversClient`, `participatedIn`, `relatedToDeal`, `Banker`,
`Interaction`, `Deal`), plus the Wave 8 officer, director and employment terms
moving from bound to materialized. Goes out through
`~/.agent-exchange/ccf-dataprep/outbox/` once the wave lands, batched with the
§3.3 pattern finding.

---

## 8 · Out of scope for Wave 10

Named so they are not quietly absorbed.

- **The role split** — coverage banker vs product specialist vs credit officer as
  distinct consuming principals. §A defers it to `ib-opportunity-synthesis` at
  T5; this wave has a single role.
- **MNPI flag suppression** in the policy binding. §B marks it pending
  `mnpi-wall-enforcement`, which is built; wiring the two together is not this
  wave's job.
- **Runtime assembly** — operators, projection, TTL, truncation disclosure in the
  payload. §D is read to learn what the data must support, never implemented.
