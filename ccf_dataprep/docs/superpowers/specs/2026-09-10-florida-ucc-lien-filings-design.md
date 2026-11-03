# Florida UCC-1 lien filings — design

**Date:** 2026-09-10
**Product:** `collateral-and-setoff-coverage` (`credit-risk.collateral-coverage.v1`), T2
**Status:** approved in chat 2026-09-10; implementation not started

---

## 0 · Why this exists

`collateral-and-setoff-coverage` §C names three elements sourced from UCC-1
filings. One of them — **Lien filing date** — has been `DEFERRED` in
`validators/spec_coverage.py` since the vault split that row on 2026-08-24, with
this note:

> Not loaded, and it never was — it comes from UCC-1, which the lien-filings row
> above waives on source grounds.

Wave 9 (2026-08-17) probed UCC-1 availability and concluded it was not viable for
this cast, because 64% of the anchors are Delaware-domiciled and Delaware's UCC
database is closed to public search. **That conclusion still holds for Delaware**
and is re-confirmed below. What it missed is that filings are made against the
*debtor*, and a Delaware parent's operating subsidiaries are incorporated
elsewhere.

Florida publishes an unauthenticated JSON API over its Secured Transaction
Registry. That is the opening this design uses.

## 1 · Evidence this is worth doing

Measured 2026-09-10, not assumed:

| Fact | Value | How established |
|---|---|---|
| Anchors free-searchable by parent domicile alone | 12 / 50 | `legal_entity.legal_jurisdiction` |
| Anchors reachable once subsidiaries are included | 22 / 50 | Exhibit 21 join |
| Anchors reachable via **Florida specifically** | 8 / 50 | anchors either FL-domiciled or holding an FL-domiciled subsidiary |
| Real-match rate on a 20-name Florida sample | **9 / 20 (45%)** | live `/search` with `searchCategory=Exact` |
| Delaware still closed | yes | state policy page **and** UCC411 (a 25M-filing aggregator) listing DE as "guide + official links only" |

A worked example, fetched live:

```
MASTEC, INC.   UCC #201700385753
  fileDate       2017-02-23
  securedParty   BANK OF AMERICA, N.A., AS ADMINISTRATIVE AGENT
  documentType   UCC1
  expirationDate 2027-02-23
  filingEvents   2   → UCC3 Termination 2021-11-01, UCC3 Continuation 2021-11-02
```

That single record carries a real filing date, a real secured party, and a real
supersession chain — the three things the estate currently engineers or lacks.

## 2 · Scope

**750 distinct debtor names**: all 50 anchors, plus the 700 distinct
US-domiciled subsidiaries in `sources/screening/exhibit21.json`.

Non-US subsidiaries are excluded — they cannot appear in a Florida register.
Delaware-domiciled subsidiaries **are** included: a Delaware entity operating in
Florida may still be filed against there, and excluding them would assume the
answer.

Estimated ~2,775 API calls (750 searches, plus detail and history calls on the
~45% that hit).

> **Scope correction.** An earlier estimate in conversation said "~350 names".
> That was wrong — it undercounted the subsidiary set by misreading a
> per-state table in which Delaware alone accounts for 394 rows. The design is
> unchanged; the fetch is roughly twice as long.

## 3 · What the source does and does not give

| §C element | Available? | Route |
|---|---|---|
| Lien filing date | **yes** | `/filing-details` → `fileDate` |
| Secured party | **yes** | `/filing-details` → `secureds[]` |
| Debtor | **yes** | `/filing-details` → `debtors[]` |
| Amendment / continuation / termination chain | **yes** | `/filing-history` |
| **Collateral description** | **no** | only inside a scanned `.tif` image |

**Decision: collateral description is not sourced from UCC.** It stays
EX-10-derived, as it is today. Retrieving it would require OCR of scanned forms,
and a mis-OCR'd collateral description stored as filed fact is worse than an
honest absence. The `.tif` is reachable but is not parsed.

## 4 · Architecture

```
fetch     → sources/ucc_fl/               raw JSON + retrieval dates, resumable
match     → generators/match_ucc_debtors.py    filed name → LEI, with score
load      → Fluree: filings, dates, amendments, secured parties
            Postgres: the filed-name → LEI crosswalk, and nothing else
validate  → validators/ucc_fl.py + rows in validators/conditions.py
```

Reuses `ccf.fetch` (`RateLimiter`, `FetchRecord`, `SourceManifest`). The fetch
checkpoints per name so a 750-name run is resumable.

### API contract

Base `https://publicsearchapi.floridaucc.com`, no authentication.

| Endpoint | Parameters |
|---|---|
| `/search` | `text`, `searchOptionType=OrganizationDebtorName`, `searchOptionSubOption=FiledCompactDebtorNameList`, `searchCategory=Exact`, `pageNumber` |
| `/filing-details` | `rowNumber`, `searchOptionSubOption`, `searchCategory`, `text` |
| `/filing-history` | `ucc1Number`, `pageSize`, `currentPage`, `sortOrder`, `orderColumnName=FilingDate` |
| `/filings-completed-through-date` | none — the registry's own currency stamp |

> **`searchCategory` must be `Exact`.** `Standard` is a *proximity browse*: it
> returns the 20 alphabetically-nearest debtor names whether or not they match
> the query, so every call appears to succeed with exactly 20 results. Measured
> with `Standard`, the sample hit rate was 100%; with `Exact` it was 45%. Only
> `Exact` populates `totalExactMatches`, and only that field is a real count.
> A test must assert that a known-absent name returns zero.

Record `filings-completed-through-date` with each run. It is the registry's
statement of its own currency and is the correct as-of stamp for the pull.

## 5 · Data model

### Fluree — owns the filings, per §C

Reified nodes, following the `ex:CollateralPledge` precedent established in
Wave 15: a relationship node carries its own attributes when the fact belongs to
the relationship rather than to either endpoint.

| Term | Kind | Purpose |
|---|---|---|
| `ex:UccFiling` | class | one filed UCC-1 |
| `ex:UccAmendment` | class | one UCC-3 event |
| `ex:SecuredParty` | class | the party named as secured on a filing |
| `ex:filedOn` | property | **the filing date — closes the DEFERRED row** |
| `ex:lapsesOn` | property | expiration date |
| `ex:filingNumber` | property | the UCC number, e.g. `201700385753` |
| `ex:filingStatus` | property | `Filed` / `Lapsed` |
| `ex:documentType` | property | `UCC1` / `UCC3` |
| `ex:amendmentAction` | property | `Continuation` / `Termination` / `Assignment` |
| `ex:debtorOfRecord` | property | filing → `LegalEntity`, only where the match is accepted |
| `ex:securedPartyOf` | property | filing → `ex:SecuredParty` |
| `ex:amendedBy` | property | filing → `ex:UccAmendment` |

**`ex:` rather than FIBO because FIBO has no such terms.** Verified against
`sources/fibo/dev.fibo-quickstart.ttl` with a positive control
(`LenderLienPosition`, 5 hits) and a negative control (an invented term, 0 hits):
`FinancingStatement`, `SecurityInterest`, `Perfection` and `SecuredParty` all
return **zero**. The dev quickstart is used deliberately — the prod quickstart
omits 40 modules and cannot support an absence claim.

**`fibo-loan-reln-org:isLienOn` is deliberately NOT bound.** It exists in FIBO
and is currently unbound, so binding it would look like progress. But without a
collateral description there is nothing to point it at, and a bound term with
zero instances is exactly the "schema row satisfied, classifier classified
nothing" failure the vault already recorded against `LenderLienPosition`.

**No filing image URL is stored.** The `/filing-image` endpoint returns a
*signed CloudFront URL with an expiry*. Persisting it would store a value
guaranteed to break. The UCC number is stored instead; the URL is constructed on
demand.

### Postgres — owns the crosswalk, and nothing else

One new table, `ucc_debtor_crosswalk`:

| Column | Notes |
|---|---|
| `filed_debtor_name` | verbatim as filed, never normalised in place |
| `lei` | the matched entity, nullable |
| `match_score` | numeric |
| `match_band` | reuses the vocabulary already in `legal_entity.lei_match_band` |
| `match_method` | how the match was reached |
| `provenance` | see §6 |

No filing attribute is written to Postgres. Single-writer discipline: Fluree is
sole authority for every filing fact.

## 6 · Provenance

| Element | Class | Source |
|---|---|---|
| Filings, dates, secured parties, amendments | `public` | Florida Secured Transaction Registry, with retrieval date and the registry's `filings-completed-through-date` |
| The filed-name → LEI match | **derived, and stored separately** | computed here; carries its score |

The match is deliberately kept out of the filing node so that no reader can
mistake our name resolution for something the state asserted. A filing is a fact;
its attachment to one of our entities is our claim about that fact.

If a **false-positive pair** is planted to satisfy CLAUDE.md rule 5, it is
labelled `synthetic — engineered`. The register is full of near-identical
corporate names, so a natural false positive is likely — **look for one before
engineering one**, and label whichever is used.

## 7 · Validation

Rows added to `validators/conditions.py`, plus `validators/ucc_fl.py`.

1. **Every condition recomputed from the stores on each run.** No stored score,
   no cached rank, no boolean flag is read.
2. **Every absence check carries a positive and a negative control.** The
   `Standard`/`Exact` trap is the standing proof that a check which cannot fail
   will pass forever.
3. **Idempotency is proved by naming a value that must survive a reload**, not by
   comparing row counts — a count cannot see a field being reset.
4. **Partition check:** Fluree holds every filing fact; Postgres holds only the
   crosswalk. Checked in *both* directions — that an element is present where it
   belongs, not merely absent where it does not.
5. **Count the unit the condition names.** The `≥ N` here is filings with a
   filing date, not names searched and not rows written.

## 8 · Binding-table obligation

`docs/ccf_dataprep_v2.md` is updated **before** any data is generated, per
CLAUDE.md. The new `ex:` terms go into the existing `ex:` extension table with
their instance counts and rationale.

The table is mirrored to the vault at
`wiki/context-products/content/fibo-iri-binding`, which the CCF SDK project reads
and which cannot be edited from here. So on completion:

- state explicitly in the response which terms were added;
- say the vault mirror needs refreshing;
- send the corrected mirror through `~/.agent-exchange/ccf-dataprep/outbox/`.

## 9 · Risks

| Risk | Handling |
|---|---|
| 750 names against a state server | conservative rate limit; per-name checkpoint; resumable |
| Signed image URLs expire | not stored; constructed on demand |
| `Standard` vs `Exact` silently inflates results | `Exact` only; a test asserts a known-absent name returns zero |
| Name punctuation misses ("Inc" vs "Inc.") | expected and *wanted* — this is the imperfect join rule 5 asks for; recorded with a score, not silently normalised |
| Florida covers only 8 anchors | accepted; this closes the filing-date row for a labelled subset, and the label must say which anchors have filed dates and which remain engineered |

**The last risk is the one that matters most.** A 16%-of-cast real layer must not
green a row that claims the whole cast. The validator asserts coverage per
anchor, not in aggregate.

## 10 · Out of scope

- OCR of filing images
- Any other state (Delaware closed; CA/NY/OH bot-walled; TX paid)
- Attaching filings to `CreditFacility` records — the source does not assert that
  link, and manufacturing it would put an inference beside filed fact
- Changing the existing EX-10 collateral topology or the 95 `ex:CollateralPledge`
  nodes
