# Wave 18 — `syndicated-lending-co-lender` · design

**Product:** `cb.syndicate-co-lender.v1` · Tier 5 · all stores + A2A
**Spec:** vault `context-products/syndicated-lending-co-lender`
**Branch:** `wave18-syndicated-lending`
**Approved by Dave:** 2026-08-25

---

## 1 · Scope, and the line we do not cross

This wave populates **two estates** — ours and the provisioned co-lender peer —
with everything the SDK needs to assemble this product. It builds **no client,
no server, and no Federate operator.**

Dave, 2026-08-25, settling the question directly:

> The context assembly will take care of assembling the context using context
> operators and calls to external agents for them to assemble their context and
> return to the main context assembly agent. This is a very complex context
> product that will be demonstrated by the SDK. Our job here is to ensure all of
> the data necessary to create context products on the main data stores as well
> as the second set of data stores (the ones that simulate a syndicated partner)
> is populated in both sets of stores. That's it.

The consequence that shapes every task below: **every §F condition that sounds
like runtime behaviour becomes a declaration in data.** A federated request that
times out is not a request we make and time; it is a peer product declaration
carrying a stated response latency above the caller's bound. An unattested
remote claim is not a verification we run; it is a peer position with no
attestation record behind it. We supply the fact; the SDK does the acting.

There is no stored "response payload" artifact either. Dave's answer says
populate the stores — the SDK assembles from them. A pre-assembled payload
would be us doing Compose, which is an operator.

---

## 2 · What already exists

| Thing | State |
|---|---|
| Peer fabric — Postgres `bofa_syndicated`/role `colender`, Mongo `bofa_syndicated`, Fluree `bofa/syndicate` | provisioned 2026-08-23, all three reachable. **No longer empty as of Task 14** (2026-08-26): Postgres holds `colender.peer_position` (7 rows), Fluree holds 10 triples under `ex:peer/` (2 typed counterparty nodes). Mongo is still empty — the peer's product carries no passage lineage of its own |
| `validators/test_fabric_isolation.py` | **7/7 arms green**, re-run 2026-08-25 |
| `ccf/config.py` co-lender helpers — `co_lender_pg_connect`, `co_lender_mongo_db`, `assert_distinct_fabrics`, `assert_co_lender_schema` | present, guards proven |
| `ccf/fluree.py` — `co_lender_query`, `co_lender_update`, `co_lender_ledger_t` | present |
| `ccf_v2.facility` | 57 rows, **51 flagged `syndicated`**, each with a total commitment, an admin-agent string, and source offsets |
| `ccf_v2.reporting_bank` | JPMorgan Chase Bank, N.A. — RSSD 852218, LEI `7H6GLXDRUGQFU57RNE97`. **This is who "we" are.** |
| `sources/ex10/` | 65 filed credit agreements |
| Mongo `fibo_v2` | 209 documents, 37,377 passages (Wave 15 agreement corpus) |
| `ccf_v2.context_debt` | table exists — the unattested-claim case lands here |

**What is missing and is this wave's core:** the `facility` table records a
facility's *total* commitment and nothing about **who holds what share of it.**
Wave 4 parsed the facility; Wave 18 parses the schedule beneath it.

---

## 3 · Source selection — six real credit agreements

A scan of all 65 EX-10s for a lender name followed within 90 characters by a
seven-figure-or-larger dollar amount found **eight filings with genuine
multi-lender commitment schedules.** Six are selected, one per borrower, all
already loaded as facilities so no new borrower is introduced:

| # | Borrower | Filing | Facility rows | Distinct lenders found | Admin agent field |
|---|---|---|---|---|---|
| 1 | RB Global Inc. | `tm2511351d1_ex10-1.htm` | `FAC-6F4065`, `FAC-A4A5EE` | 12 | clean |
| 2 | Bausch Health Companies Inc. | `d949183dex101.htm` | `FAC-E08688`, `FAC-105FC5`, `FAC-08F1D1`, `FAC-DFCB72` | 10 | **corrupt** — `'in its capacity'` |
| 3 | American Healthcare REIT, Inc. | `ahr-ex10_1.htm` | `FAC-405B7A`, `FAC-2A2C38` | 10 | **corrupt** |
| 4 | Paychex Inc. | `payx-ex10_1.htm` | `FAC-E386A4` | 12 | **corrupt** |
| 5 | Regis Corp | `d761586dex101.htm` | `FAC-E4D2F8`, `FAC-25F991`, `FAC-01BB3F`, `FAC-5F29AF` | 5 | clean |
| 6 | Sabre Corp | `d133770dex101.htm` | `FAC-3DF1D5` | 9 | clean |

**Two agreements were swapped out on 2026-08-25, and the reason matters more
than the swap.** The original list named Super Micro (`d45696dex101.htm`) and
Vertiv (`d105148dex101.htm`). Neither contains a commitment schedule. What the
selection scan found in them is a **letter-of-credit issuing-bank sublimit
table** — Vertiv's is headed literally *"Issuing Bank | Issuing Bank Individual
Sublimit"*, and Super Micro's reads *"JPMorgan Chase Bank, N.A., with respect to
up to $25,436,410.00 of Letters of Credit"*. Vertiv even cross-references a
"Schedule 2.01 Commitments" whose content is not in the exhibit.

The scan that selected them matched an institution name within 90 characters of
a money figure, which cannot tell the two apart — and the sublimit tables look
*more* like schedules than the real ones do, because their figures are uniform
(six banks at exactly $214,285,714.29). Loading them would have recorded six
banks' letter-of-credit capacity as syndicate shares, and every count would have
passed. Same class as the estate's existing lessons *"one issuer is not the
format"* and *"Exhibit 21 has no ownership %"*: a table that is real, filed, and
not the thing you think it is.

Replacements were found by re-sweeping all 65 filings with the structural parser
Task 2 actually built, then keeping only those with loaded syndicated facilities.

Union of institutions across the six, from the scan's fixed 32-name probe
alone: Bank of America, Bank of Nova Scotia, Barclays, BNP Paribas, Citibank,
Citicorp North America, Citizens Bank, Deutsche Bank, Fifth Third, Goldman
Sachs, HSBC, JPMorgan Chase, KeyBank, Morgan Stanley, MUFG, PNC Bank, Regions
Bank, Royal Bank of Canada, Truist, U.S. Bank, Wells Fargo — **21 before a real
parser runs.** §F asks for ~25 and a real parser reads names the probe never
listed, so the target is reachable without padding.

**JPMorgan and Bank of America appear together on four of the six.** The
co-lender relationship this product demonstrates is therefore *publicly filed
fact*, not a staged arrangement — which is the point §C makes about the
Commitment Schedule being the catalog's best-kept public secret.

**Scope note.** §F says "~6 syndicated facilities". Six *credit agreements* are
selected; after the 2026-08-25 swap they carry **fourteen** `facility` rows
between them. Commitment schedules are per-tranche, so the schedule parse keys
on the facility row, not the agreement. Fourteen ≥ six; the floor is met either
way it is counted.

**Measured after Task 2:** 98 schedule rows, **58 distinct lender names** before
identity resolution collapses variants — comfortably above §F's ~25 once Task 3
maps them to institutions.

**One facility carries no recorded total.** Sabre's `FAC-3DF1D5` has
`commitment_amount = NULL` in `ccf_v2.facility`. Its parsed shares sum sanely on
their own ($130,000,000 Class A plus $122,028,678 Class B = $252,028,678). This
mattered while §8 had a share-reconciliation floor; that floor was measured and
deleted on 2026-08-25 (see §7), so nothing now compares a share against
`commitment_amount` and this facility needs no special exclusion.

**Wave 18's facility set is 12, not 14.** Two Wave 4 extraction defects are
excluded — `FAC-105FC5`, a duplicate of `FAC-08F1D1` for one real Bausch
tranche, and `FAC-DFCB72`, built from a covenant clause about a *hypothetical*
delayed-draw facility plus a dollar figure scraped from an unrelated
debt-incurrence cap. Both are recorded in `docs/known-issues.md` #32 with their
offsets. `ccf_v2.facility` is **not** mutated — other products reference those
rows; the exclusion lives in `ccf.syndicate.WAVE18_EXCLUDED_FACILITIES`, which
every Wave 18 task imports rather than re-deriving.

---

## 4 · Semantic binding

FIBO's **`SEC/Debt/DistributedLoans/`** module
(`https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/`) is
this product's vocabulary and is already present in
`sources/fibo/dev.fibo-quickstart.ttl`:

| §B element | Binds to | Verified |
|---|---|---|
| `SyndicatedFacility` | `fibo-sec-dbt-dln:SyndicatedLoan` — *"credit agreement in which a group of lenders, known as a syndicate, collectively provides a large loan to a single borrower"*; subclass of `CreditFacility` and `CommercialLoan` | in ontology |
| the syndicate itself | `fibo-sec-dbt-dln:FinanceSyndicate` | in ontology |
| `SyndicateMember` | `fibo-sec-dbt-dln:FinanceSyndicateMember` | in ontology |
| administrative agent | `fibo-sec-dbt-dln:AdministrativeAgent` | in ontology |
| arranger roles (if used) | `LeadArranger`, `Bookrunner`, `SyndicationAgent`, `DocumentationAgent` | in ontology |
| `Commitment` | `fibo-fnd-agr-agr:Commitment` | in ontology |

**Two traps recorded before anyone falls into them.**

1. **`fibo-loan-ln-reg:administeredBy` is NOT our `administeredBy`.** Its
   `rdfs:domain` is `LoanRegulatoryRequirement` and its `rdfs:range` is
   `cmns-rga:RegulatoryAgency`. It describes a regulator overseeing a rule. The
   local name reads perfectly and the semantics are unrelated — exactly the
   failure CLAUDE.md means by *"module membership does not pin an IRI."*
2. **`SyndicateMember` resolves twice** — `fibo-be-fct-fct:SyndicateMember`
   (generic) and `fibo-bp-iss-ipo:SyndicateMember` (IPO underwriting
   syndicate). Neither is the lending one. `fibo-sec-dbt-dln:FinanceSyndicateMember`
   is, and it is a subclass of the first.

**Still to determine in the binding task**, not assumed here: whether
`participatesIn` is expressible as FIBO-native `cmns-col:isMemberOf` (the
`FinanceSyndicateMember` restriction already uses it) rather than a new term;
which property carries administered-by for a facility; and which of
`votesOn`, `sharesCollateralWith`, and the envelope/attestation/TTL terms have
no FIBO equivalent and must be minted under `ex:`. Every term is checked by
**grepping `dev.fibo-quickstart.ttl` for `rdf:about`/subject position** — never
by fetching a spec.edmcouncil.org URL, which returns HTTP 200 for names that do
not exist.

Per CLAUDE.md §"The binding table is mirrored": new terms go into
`docs/ccf_dataprep_v2.md` first, then the corrected mirror is sent through
`~/.agent-exchange/ccf-dataprep/outbox/`, and the response says so explicitly.

---

## 5 · Our estate — what lands where

Single-writer discipline holds throughout; nothing below is duplicated across
stores.

**Fluree (`fibo-v2`) — `R`, `T`, policy binding**
- One `SyndicatedLoan` node per selected facility; one `FinanceSyndicate` per agreement.
- One `FinanceSyndicateMember` node per institution, carrying `lei` and a display label **and nothing else** — every attribute resolves from Postgres.
- `participatesIn` edges member → syndicate, **carrying the commitment share** — §C assigns *"syndicate composition — lender names and commitments"* to Fluree as `R`, so the share is an edge attribute here and exists nowhere else. Each edge references the Mongo passage its figure was read from.
- Administrative-agent edges facility → agent institution.
- `votesOn` edges for the live amendment vote, with posture.
- Amendment events and effective dates as temporal assertions.
- **Bilateral disclosure envelopes** — `P` and `T`, versioned, per counterparty.

**Postgres (`ccf_v2`) — `E`, policy reference**
- `syndicate_member` — institution identity: real LEI, real FFIEC RSSD, legal name.
- `member_call_report` — Call Report condition figures per institution (FDIC BankFind, the path `load_reporting_bank.py` already uses).
- `own_position` — our share, internal rating, workout posture. **synthetic — internal.**
- `competition_law_rule` — the constraint register. **synthetic — internal.**
- `syndicate_projection_plan` — one per perspective (`agent` / `participant` / `prospective`). **synthetic — internal.**
- **No crosswalk rows** — superseded by Preflight Ruling P1 (`docs/wave18-plan.md:904`).
  An earlier draft of this design required a crosswalk row per member; syndicate
  members are counterparty institutions, not clients, so a crosswalk row would
  point at no `legal_entity` row by LEI and put `conditions.py`'s
  `CROSSWALK_INVARIANTS["crosswalk rows pointing at no entity"]` red. §C's
  correlation key for this product is `facility_id` plus lender LEI and RSSD,
  not the crosswalk.

**Two things Postgres deliberately does NOT hold**, because §C assigns them
elsewhere and duplicating them would break single-writer discipline: the
per-member **commitment shares** (Fluree, above) and the **bilateral disclosure
envelopes** (Fluree, `P`/`T`). An earlier draft of this design put both in
Postgres "for convenience". That is the exact move CLAUDE.md forbids, and it is
recorded here so the same convenience is not re-invented mid-wave.

**MongoDB (`fibo_v2`) — passage-level lineage**
- Voting thresholds and amendment mechanics; the assignment and transfer article — extracted with span offsets against the six agreements, reusing Wave 15's passage machinery.
- The Shared National Credit Program public annual report, for market context.

**SQLite (`data/departmental.sqlite`) — departmental**
- `syndicate_desk_tracker` — the desk's local position workbook. **synthetic — internal.** New table alongside the existing five.

---

## 6 · The peer estate

Per Dave's decision of 2026-08-25, the single provisioned peer instance hosts
**two counterparty identities**:

| Identity | Disclosure precision | Purpose |
|---|---|---|
| **Bank of America, N.A.** | exact amounts | the primary co-lender |
| **Citibank, N.A.** | band only (e.g. `$50m–$100m`) | satisfies the mixed-precision floor |

One instance, two identities. The alternative — a third fabric — is a day of
infrastructure §F does not ask for; the alternative of leaving the second
counterparty as an envelope row with no data behind it leaves the SDK nothing
to fetch.

The peer's Postgres (`bofa_syndicated`.`colender`), Mongo and Fluree hold that
counterparty's own positions, ratings, workout postures, its side of the
envelope, and its product declarations. **Every write to the peer gates on
`assert_distinct_fabrics()`, `assert_co_lender_schema()`, and an explicit
`current_database()` assertion before any DDL** — both databases sit on
`192.168.4.76:5432` and differ by nothing but a name.

**Citibank's band rows must not be reconstructible to an exact figure.** If the
band is stored alongside a precise amount in any column, or derivable from a
count and a total, the mixed-precision demonstration is theatre. The validator
in §8 checks this by recomputation, not by reading a `granularity` flag.

---

## 7 · The §F conditions, and how each is data

| §F condition | Representation | How it is proven |
|---|---|---|
| ~6 facilities with real Commitment Schedules | six agreements above, parsed to per-lender shares with source offsets | **every share's offset resolves in the source filing to the lender it claims** — summation was measured and deleted, see below |
| ~25 members on real LEI + RSSD | `syndicate_member` | every row's LEI matches GLEIF format and its RSSD resolves via FDIC BankFind |
| 1 simulated peer fabric | the provisioned instance, populated | peer stores non-empty; isolation validator still 7/7 |
| **≥ 2 asymmetric envelopes** | envelope rows where request-scope ≠ disclose-scope | recompute both sets and assert they differ as sets — not that a flag says so |
| **≥ 1 band, ≥ 1 exact** | BofA exact; Citibank band | assert no exact amount for the band peer is present or derivable anywhere in either estate |
| **≥ 1 live vote, divergent postures** | `votesOn` edges on OUR Fluree ledger only (18 edges, one facility's open vote) | recompute distinct postures on one facility's open vote; require ≥ 2 |
| **≥ 1 timeout** | peer product declaration with stated latency > the 5s default bound | recompute: declared latency vs. the declared caller bound |
| **≥ 1 unattested claim** | one peer position with no attestation record; a `context_debt` row on our side | assert the attestation genuinely absent, and that exactly the intended one is |
| **≥ 1 remote TTL below the composite** | peer declaration with a short TTL | recompute min(remote TTL) and assert it is strictly below the local product TTL |

**The vote row was corrected (whole-branch review fix, superseding the
prior "on both fabrics" wording).** Controller finding **C7** ruled Task 9's
scoping of the live vote to our own fabric correct — the peer never carries
vote data. This row previously described `votesOn` edges on both fabrics;
the peer's Fluree ledger holds only 10 triples (2 counterparty nodes × 5
identity predicates: `lei`, `provenance`, `disclosurePrecision`, `rdf:type`,
`rdfs:label`, verified live), no `votesOn` among them. The design row was
simply never updated after C7 settled the question.

**Summation was tried, measured, and deleted (2026-08-25).** An earlier version of this table required per-lender shares to sum to each facility's recorded total. Measured across all twelve facilities, **not one reconciles** — best 4.0% off, worst 3391%. Four causes, all legitimate: filings carry **placeholder rows** the document itself declines to attribute (Bausch hides $1.04bn behind *"Cashless Option Initial Lenders [on file with the Administrative Agent]"*); **amendment exhibits** list only incremental commitments (Regis); **tranche captions** are unreliable when one schedule spans several tranches (AHR); and some Wave 4 totals are themselves mis-extractions (known-issues #32). Reconciling against the filing's own TOTAL line was also checked — the six filings do not reliably state one.

The premise "shares sum to the facility total" is how syndicated lending works conceptually; it is not how filed commitment schedules behave. A schedule is a snapshot of one amendment, with assigned-out lenders folded into an unnamed line. The floor now asserts **provenance** instead of arithmetic: every share must resolve back to the filed text it came from. That is checkable; summation never was.

Every "recompute" above means the validator derives the answer from the stores
on the run — reading no stored score, no cached rank, no boolean flag. This is
the standard CLAUDE.md sets for a build-time validator and the reason it is not
an operator: it registers nothing, composes into no plan, serves no principal,
and emits no contract.

---

## 8 · Validation and registration

**`validators/syndicate.py`** — the §F floors that counting cannot establish,
recomputed live on every run. Each arm must be tested against a known-present
*and* a known-absent input and required to give different answers, or it is
decoration.

The specific traps this wave is exposed to, from prior waves' defect record:

- A check that **selects rows by the property it polices** cannot see that
  property missing. The band-granularity arm must count its denominator
  independently of the granularity column.
- **Counting the wrong unit.** "≥ 2 asymmetric envelopes" counts *envelopes
  whose two scopes differ*, not envelopes, and not scope rows.
- **A tolerance wider than the bias.** Commitment shares that must sum to a
  total need a tolerance derived from the filing's own rounding, measured
  first — not a round number chosen for comfort.

**Registration** — `conditions.py` (the §F block), `partition.py` **extended in
both directions**: peer-owned elements must be absent from our stores *and*
our elements absent from the peer's, `spec_coverage.py` (§C catalog rows), and
`docs/ccf_dataprep_v2.md` (entity tables, counts, binding table).

**Positional identity.** Four loaders on `main` already rewrite other waves'
rows when a table grows. Any loader here that assigns identifiers must key on
content, never on row position, and the check runs before rows are added.

---

## 9 · Repairs in scope

**Administrative-agent extraction is broken.** Four of the six selected
agreements carry a corrupt `administrative_agent` — `'in its capacity'`,
`'that is a party hereto, and BANK O'`, `'and JPMORGAN CHASE BANK, N.A., in '`,
`' on the signature pages hereof and'`. A preamble regex captured the wrong
span. §C makes agent identity a required public element and Dave confirmed the
repair as essential, so it is a task in this wave rather than a separate
errand. The fix re-extracts across **all 51 syndicated facilities**, not only
the six — a parser corrected for six and left wrong for forty-five is a worse
state than the one it replaced, because the field then looks reliable.

---

## 10 · Deliberately not built

- Any client, server, endpoint, poller, or file-drop channel. §1.
- Any pre-assembled product payload. §1.
- `sharesCollateralWith` **edges**. The term appears in §B's relationship list;
  nothing in §C or §F requires it and no current data supports it. The term is
  bound; the edges stay unpopulated unless Dave asks. Recorded so a later
  reader does not mistake the absence for an oversight — see the standing
  lesson that deleted and never-built conditions leave their names behind.
- A third peer fabric. §6.

---

## 11 · Open items

- **Which six borrowers is fixed** (§3) but the eleven-vs-six facility-row
  question is recorded, not hidden — if Dave wants exactly six facility rows,
  drop the smaller tranches of Bausch and AHR.
- The **SNC annual report** must still be located and fetched; it is a public
  PDF from the Federal Reserve/OCC/FDIC and has not been retrieved yet.
- The peer Mongo password is inline in `CO_LENDER_MONGO_URI` and has appeared
  in terminal output. Worth rotating; out of this wave's scope, carried from
  the co-lender provisioning note.
