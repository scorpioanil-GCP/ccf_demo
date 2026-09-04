# Facility Terms Snapshot — Context Product Specification

**CP-SPEC-002** · Authored to Specification Standard v0.3
(`public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`) ·
build order `cp-02`, the **second rung of the vault's 21-product ladder**.

**Authored 2026-08-29 at Gate 1, before any implementation exists**, per
`public/reference/specifications/spec_generation.md` §2. Nothing in this
document is derived from a run. Every term that only a build can supply is
marked `[TBC — this build, phase Pn]` and registered at §F.2.

---

> ## READ THIS BEFORE YOU READ A NUMBER
>
> **These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.**
>
> Every count, coverage figure and match rate in this document is here to show
> how a specification binds to a real store, and for no other reason.
>
> This product reads a **mixture the estate labels honestly, within a single
> table**. `ccf_v2.facility` carries **60 of 60 rows** with
> `provenance_public = 'public'` **and** `provenance_internal = 'synthetic —
> internal'` — because one row is both. The facility type, commitment,
> currency, effective date, maturity date and administrative agent are
> extracted from a filed EX-10 credit agreement. The outstanding balance, the
> undrawn availability, the internal risk rating, the pricing-grid **margins**
> and the `facility_id` ↔ borrower-LEI crosswalk are **invented**, because no
> public source discloses a bank's own loan-system state.
>
> **No number here is a fact about any real company's credit facilities**, and
> no principal named below is a real person or a real role at any institution.
>
> The two places this matters most: the **four facilities whose maturity date
> precedes their effective date** (§C.4 trap 1) are an extraction defect in
> engineered data, not a claim about any borrower; and the **10-of-60
> servable** figure at §B.1 element 3 is a property of *this estate's date
> spread against a declared 90-day window*, not a prediction about any real
> loan book.
>
> The same statements are repeated beside each figure cluster below,
> deliberately, rather than left here as a header a reader scrolls past.

---

## 0 · What this document is

A specification of **one** Context Product — `reference.facility.v1` — written
to the v0.3 format contract, for a product requiring **one capability class**
(`relational`) across **one system of record**.

> **This is an implementation specification, so it names the data concretely.** §C.1's
> system-of-record column carries the actual schema and table behind every element, and
> §F carries the measured readiness of each — a spec that cannot say where an element
> comes from cannot be built from.
>
> ### Which specification this is
>
> **Ruled by Dave, 2026-08-29**, and settled at `CP-SPEC-001` §0: there are **two
> levels** of Context Product specification. The vault holds the
> **implementation-independent** one — `context-products/content/facility-terms-snapshot.md`,
> which answers *what the product is* and correctly names no database. **This is the
> SDK level**: a specific implementation artifact bound to one estate, which answers
> *how it is built* and must name its store or its table references mean nothing.
>
> **Neither supersedes the other**, and the reasoning is not restated here — it is at
> `CP-SPEC-001` §0 and `spec_generation.md` §1.1. What is restated is the consequence:
> **deployment — host, port, credential, instance — appears in neither**, and lives in
> `backends.yaml` as an environment-variable name.

**This spec is written BEFORE the assembly it specifies.** Where the SDK cannot express
something this document orders, the gap is **recorded and not closed** (`D-04`); closing
it is a separate phase.

**What this product is for, in one sentence.** It is the first product on the ladder
that **anchors on something that is not a legal entity** — a facility — and the first
whose expiry is derived from *the dated instrument the terms came from* rather than from
a clock, a calendar quarter, or the moment the question was asked.

### 0.1 Do you need a Context Product? — the four-question test

**`[TBC — vault]`.** The vault article for this product is on the **older Q019 form**
and carries **no four-question test section** at all — `spec_generation.md` §4.1 warns
that twenty of the twenty-one articles are on that form and that sections resolve by
heading name, never by letter. The test result is the vault's term under §1's ownership
table, and it is **not guessed here**.

**What is requested, and why it is not blocking.** A four-question result for
`facility-terms-snapshot`, with honest partials. It does not block Gate 1 because the
vault has already admitted the product to the ladder at rung 02 with a stated primitive
and a stated counterfactual — the test records *why* it qualifies, and this document
can be built and proven without it. Registered at §F.2 row 1 and sent through the §11
return path with this specification.

**One SDK-side observation offered to whoever answers it**, marked plainly as a
proposal and not as an answer: question 2 — *does it have a validity window after which
acting on it is wrong?* — is the axis this entire product exists to teach, and §B.1
element 3 measures what that window does against the real estate. Question 1 looks like
a **No** on content and a **Yes** on population, the same shape rung 01 recorded at its
own §0.1.

### 0.2 Placeholder discipline

Every unresolved item carries `[TBC — <owner>]` and appears again at **§F.2** with a
named owner. Two owner classes appear:

- `[TBC — this build, phase Pn]` — a value only the build can supply. Cleared at Gate 2.
- `[TBC — <agent>]` — a term belonging to another agent under `spec_generation.md`
  §1's ownership table. **Never guessed.**

An unmarked assumption is the more serious defect, because a marked gap gets closed
and an invented one gets built.

### 0.3 Section skeleton

Seven sections, in order, per Standard §0.3. Sections carrying nothing still carry a
line saying why. §B.3 is the instance here.

### 0.4 Front matter

| Field | Value |
|---|---|
| Registry name | `reference.facility.v1` |
| Tier | 1 |
| **Assembly Mode** | **1 — pure algorithmic** |
| Cost band | ×1 (the baseline) |
| Lifecycle state | **draft** — Gate 1 authored, not yet built |
| Accountable owner | product: Wholesale Lending · data steward: loan operations / agency · policy: identity and access |
| Last review | 2026-08-29 (this authoring) |
| What it resolves | A single credit facility to its typed economic and structural terms — as an object a system can reason over, rather than a PDF a human reads |
| Four-question build test | `[TBC — vault]` — §0.1 |
| Build order | **Second on the vault's ladder.** Depends on `counterparty-reference-snapshot` for borrower resolution; supplies facility identity to `credit-exposure-rollup`, `collateral-and-setoff-coverage`, `covenant-in-force-as-of` and `syndicated-lending-co-lender` |

**Capability gate: none.** This product requires only the `relational` capability class.
Like rung 01 it is deliverable against any estate that can serve a set-based query and
an entitlement lookup — **and unlike rung 01 it needs one property beyond that**, a
date-arithmetic predicate in the store or the assembler, which §C.2 decomposes.

---

## Section A — Decision frame

**Decision & trigger.** A credit officer is reviewing a drawdown request, an amendment,
or an annual renewal, and needs the facility's current terms **as a typed object rather
than a PDF**. The vault's term, carried.

**Consuming principals.** Single role at this tier. Projection Π is **not exercised** —
that arrives at T5. The product returns the **same shape** to every authorized caller.

> **The shape is constant; the population is not — and at this rung the population
> collapses harder than at rung 01.** Four principals exist in the estate. Measured
> 2026-08-29, **two of them see no facility at all**, because their jurisdiction grants
> name no country any borrower in this estate is organized in (§D.3). That is
> entitlement scope, not projection, and under the Standard's suppression rule (§2.2)
> a principal who sees nothing must not be able to tell whether that is because
> nothing exists or because nothing is permitted.

**Counterfactual failure — the wrong TTL anchor.** The vault's term, carried verbatim
in substance:

> A facility's terms do not decay on a clock; they are valid until the agreement is
> amended. Anchoring its TTL `from_decision` — expiring it when the review window
> closes — collapses the cache for no reason. Anchoring `from_entity_freshness` keeps
> it live until the underlying agreement is superseded, which may be quarters away.

**The failure is not a missing field; it is an expiry derived from the wrong event.**
Every field a credit officer needs is in the source document. What a document cannot
carry is a statement of *when believing it stops being safe*, and the anchor is the
choice of which event that statement is measured from.

**Closed-taxonomy mode: `[TBC — vault]`, with a reading proposed.** The vault article
names the failure but does not name which of the five closed-taxonomy modes
(`context-starved` · `temporally-incoherent` · `perspective-flat` · `policy-blind` ·
`evidence-free`) it falls under. **The reading proposed here is
`temporally-incoherent`** — the fields are all present and correct, and the defect is
entirely in the time axis, which is the same reasoning rung 01 recorded. It is
proposed rather than asserted because the mode is the vault's term. §F.2 row 2.

**Counterfactual acceptance test.**

| | |
|---|---|
| **Query** | `GET /context-products/reference/facility/{facility_id}?intent=drawdown-review` |
| **Answer A — a document lookup or a loan-system screen** | the same terms: type, commitment, currency, effective and maturity dates, pricing grid, agent |
| **Answer B — this product** | the same terms **plus** `contract.expires_at` derived from the agreement's own date, `contract.ttl_anchor`, `contract.ttl_basis` naming which date it was derived from, `lineage`, `context_debt` |
| **They must differ when** | the same facility is asked for twice, at two different moments. A's currency claim moves with the question; **B's does not move at all** — the expiry is a property of the instrument, not of the request |
| **The test fails if** | `expires_at` shifts when only `asked_at` shifts. Then the anchor is `from_decision` wearing a different label, and the product has enacted the counterfactual it exists to refute |

`[TBC — this build, phase P7]` — fixture `FTS-F01`, and the two calls it compares.

**Primitive taught. `ttl_anchor: from_entity_freshness`, made concrete.** Rung 01
*introduced* the anchor; this rung is where it has to be **computed from a date the
source document carries**, and where getting it wrong is visible rather than
theoretical. The distinction rung 01 could not draw — because its entity freshness and
its load date were close together — is drawn here by measurement: see §E.5.

**Contrast pointer.** Three anchors now exist across three built products, which is what
makes the choice teachable:

| Product | Anchor | Expiry moves with |
|---|---|---|
| `cp-00-institutional-holders` | a **reported quarter end** | the source's calendar, not the entity |
| `cp-01-counterparty-reference-snapshot` | **entity freshness** — a vendor file date | each entity, on a fast cadence |
| **`cp-02` — this product** | **entity freshness** — a filed agreement date | each **facility**, on a cadence measured in **years** |

The vault names the forward contrast too: in `treasury-liquidity-position` the same
mistake breaks in the opposite direction — toward stale context driving a live
decision, rather than toward a cache that collapses for no reason.

---

## Section B — Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Schema** | `facility_terms` — entity `CreditFacility`; attributes: facility type, commitment amount, currency, effective date, maturity date, pricing grid, administrative agent, borrower LEI, amendment number. **No relationships.** Machine-readable artifact: `[TBC — this build, phase P6]` at `docs/schemas/facility_terms.v1.json` |
| 2 | **Freshness SLA** | **Amendment-driven.** Terms are current until an amendment files. The vault's term. §C.3 records what the estate can and cannot evidence about that event |
| 3 | **TTL** | **90 days** · `ttl_anchor: from_entity_freshness`. **The declaration is the vault's and it is not changed here.** A measured consequence is recorded below and is a BUILD finding |
| 4 | **Policy Binding** | **Entitlement scope** — facility-level need-to-know, plus jurisdiction visibility on the **borrower**. No regulatory overlay at this tier. §B.2 |
| 5 | **Lineage** | `operators_invoked: [Resolve, Policy]` · `graph_snapshot_at` · `policy_version` · `payload_hash` · `context_debt`. `projection_plan_id` **null** — Π not exercised at T1. `model_record` **null** — Mode 1 |
| 6 | **Semantic Version** | `v1.0.0`. No prior version; no migration window applies |
| 7 | **Discovery** | `reference.facility.v1` |
| 8 | **Addressability** | `/context-products/reference/facility/{facility-id}` |
| 9 | **Assembly Mode** | **1 — pure algorithmic.** No model is invoked anywhere in the path |

**Mode 1 means §B.3 model-risk annotation does not apply.** That is a consequence of
the declaration, not an omission.

**Element 5 is stated as typed references, not bare names**, for the reason rung 01
records: lineage strict equality compares a declared set against an engine-resolved
set, and a comparison needs addresses on both sides. §D.2's eighth column carries them.

> ### A MEASURED CONSEQUENCE OF ELEMENT 3, found at P2 before any code was written
>
> `from_entity_freshness` computes `expires_at` from the entity's own last observation.
> For a facility, the vault's §D step 3 states which observation that is:
>
> > *"`expires_at` derives from the agreement's effective date plus the 90-day window —
> > **not** from request time."*
>
> Measured against the live estate on 2026-08-29, asking at `2026-08-29`:
>
> ```
> effective_date range across 60 facilities : 2019-07-31 .. 2026-08-04
>
> effective_date + 90d still in the future  : 10 of 60
> ...therefore refused on ttl-bounds        : 50 of 60
>
> age of effective_date, bucketed:
>   < 90 days     10
>   90d .. 1 year 16
>   1 .. 2 years  24
>   > 2 years     10
> ```
>
> `src/ccf/products/gates.py::_refuse_ttl` requires `now < expires_at`. On these
> numbers **50 of 60 facilities are refused on their first call** — including every
> facility carrying an amendment history, which is the population three later rungs
> depend on this one to make servable.
>
> **THE DECLARATION IS NOT CHANGED HERE, AND THAT IS DELIBERATE.** The 90-day TTL and
> the `from_entity_freshness` anchor are both the **vault's** terms under
> `spec_generation.md` §1's ownership table. Inventing a third anchor basis, or
> quietly widening the window until the numbers look healthy, would be writing another
> agent's term — the failure §0 of that document exists to prevent, and the failure
> that produced the grade/coverage break.
>
> **How this resolves.** It is a **build finding**, taken back with evidence from an
> actual run per `spec_generation.md` §2 — *"a Gate-2 value that contradicts an
> approved Gate-1 decision is a deviation — take it back, do not absorb it."* Gate
> **`FTS-G09`** is what settles it, in whichever direction the run settles it, and it
> is written so that **it turns red when the declaration is corrected**. Registered at
> §F.4 finding 1, and the two candidate corrections are set out with their measured
> consequences at **§E.5** rather than chosen here.

**Element 3, and the one thing this anchor must be tested for.** `from_entity_freshness`
means `expires_at` is a function of the facility, not of the request. The test that
matters is therefore not *"is it in the future"* but **"does it stay put when the
question moves"** — §A's acceptance test, and gate `FTS-G01`.

### B.2 Classification and residency

| Field | Value |
|---|---|
| **Data classification** | `internal` — the highest classification of any element in §C.1. The EX-10-derived terms are `public`; the outstanding balance, undrawn availability, internal risk rating, pricing-grid margins and the borrower crosswalk are `internal`. **No `confidential` or `restricted` element is in scope** |
| **Information barrier** | `none` at this tier. **Worth stating rather than skipping:** facility-level need-to-know is an entitlement, not a barrier. The control-room case — where knowing a facility exists is itself restricted — arrives at `mnpi-wall-enforcement` |
| **Residency constraints** | `[TBC — identity and access]` — no jurisdiction is currently declared non-exportable. Borrowers are organized across **8 distinct jurisdiction codes** (§C.1) |
| **Cross-border serving** | `[TBC — identity and access]`. The entitlement scope constrains **which facilities a principal sees**; it does not express **where a principal may be** when they see them |

**The suppression rule, and it bites harder here than at rung 01.** Where policy
excludes content, the payload carries **no count, no marker and no placeholder**.
Measured 2026-08-29, **two of four principals see zero facilities** — so this product
has a live instance of the hardest suppression case: a principal for whom *the correct
response and the withheld response look identical*. A `"you are not entitled to this
facility"` message and a `404` are different disclosures, and only one of them is
allowed. §D.3 fixes which, and gate `FTS-G04` proves it.

### B.3 Model-risk annotation — Mode 2 and Mode 3 only

**Not applicable — no model in the trust path.** Assembly Mode 1; no LLM at any step.
This section carries a line rather than being omitted, per Standard §0.3: an absent
heading reads as an oversight, a short one reads as a decision.

### B.4 Request parameter surface

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `facility_id` | `string`, required | **E** — anchor | — |
| `intent` | enum, required | **P** — selects the policy envelope | — |
| `debt_tolerance` | float, required | **P** — the ceiling above which assembly refuses | `0.25` `[TBC — this build, phase P8]` |
| `include_pricing_grid` | bool | payload shape | `true` |
| `as_of` | timestamp | **T** — reconstruction | **declared-but-inert at this tier** |

**Required on every product** per Standard §2.4: an anchor identifier, `intent`, and
`debt_tolerance`. The vault's article carries the first, second and fourth; **`as_of`
and `debt_tolerance` are added here**, for the reason rung 01 records — §2.4 states
them as universal, and a product that silently drops `debt_tolerance` has no way to
express the debt gate at §D.7. §F.4 finding 3.

**`as_of` is declared-but-inert and must fail loudly**, returning
**`400 not_supported_at_tier`**. The vault is explicit that this is the tier boundary
doing its job rather than a gap:

> *"No `as_of` parameter. Reconstructing terms as they stood on a past date requires
> ledger time-travel and arrives at `covenant-in-force-as-of`."*

**That boundary is worth naming precisely, because this product is the one most likely
to be asked to cross it.** A facility carrying 21 amendments visibly *has* a history;
the estate can say **how many** amendments there were and **not when any of them took
effect** (§C.4 trap 2). A silent success against current state would answer a
historical question with today's terms wearing yesterday's label. Gate `FTS-G05`.

**`include_pricing_grid` changes the payload shape, not the answer.** It is the only
parameter here that does — and the `payload_hash` must therefore include it, or two
genuinely different payloads share a hash. §D.4.

**`debt_tolerance` default 0.25 is provisional and unbacked**, carried from rung 01's
posture and unmeasured here. §F.2.

### B.5 Prerequisites, consumers and scope boundary

**Prerequisites.** **`counterparty-reference-snapshot`** — the vault's term: *"the
borrower LEI must resolve."* Measured 2026-08-29: **all 60 facilities carry a
`borrower_lei` that resolves to a row in `ccf_v2.legal_entity`; zero orphans**, across
**22 distinct borrowers**. The prerequisite is satisfied by the estate as it stands.

**Consumers.** From the vault's cross-references and the ladder's dependency notes:
`credit-exposure-rollup` (rung 05), `collateral-and-setoff-coverage` (rung 06),
`covenant-in-force-as-of` (rung 08, the flagship), `abs-securitization-surveillance`
(rung 16), `syndicated-lending-co-lender` (rung 20).

> **The flagship's dependency is the one to notice.** `covenant-in-force-as-of` exists
> to time-travel over facility amendments. It inherits its facility identity from this
> product — and §C.4 trap 2 records that **the amendment dates it will need do not
> exist in this store**. That is not this product's blocker; it is this product's
> **finding**, surfaced two rungs before the product that needs it. §F.4 finding 2.

**Scope boundary — the vault's term, verbatim.**

> **"Deliberately out of scope at this tier.** No `as_of` parameter. Reconstructing
> terms as they stood on a past date requires ledger time-travel and arrives at
> `covenant-in-force-as-of`. No pointer to the source agreement text — passage-level
> lineage arrives at `covenant-cross-reference`. Both omissions are the tier boundary
> doing its job, and both are worth flagging to the SDK reader as *coming next* rather
> than as gaps."

**Deliberately out of scope, and which product carries each:**

| A reader will expect | It is not here | It is in |
|---|---|---|
| Terms as they stood on a past date | `as_of` is inert — ledger time-travel | `covenant-in-force-as-of` |
| A pointer into the source agreement text | passage-level lineage | `covenant-cross-reference` |
| The covenants the agreement imposes | not a term of the facility's economics | `covenant-in-force-as-of` |
| Collateral and security interests | "no relationships" | `collateral-and-setoff-coverage` |
| Exposure aggregated across facilities | a rollup, not a snapshot | `credit-exposure-rollup` |
| Syndicate composition and shares | "no relationships" | `syndicated-lending-co-lender` |

> **The second exclusion is the one the data actively invites you to violate**, and it
> is why §C.4 trap 3 exists. `ccf_v2.facility` carries `source_accession`,
> `source_document` **and `source_offsets`** — populated on **60 of 60 rows**. The
> character offsets into the credit agreement are *right there*. The vault's own
> extraction note draws the line: *"a T1 example that reaches into a document has
> silently become a T4 example."*

---

## Section C — Data catalog

> **Every figure in this section was measured against the live estate on
> 2026-08-29 by a read-only query, not read off a report.** Where a term belongs
> to `ccf_dataprep` under `spec_generation.md` §1's ownership table — system of
> record, provenance class, classification, capability class, `G` dimension,
> **ontology IRI** — and is not established, it is `[TBC — ccf_dataprep]` and
> **not guessed**.
>
> **This product has no coverage manifest, and that is the first finding.**
> `validators/spec_coverage.py --product facility-terms-snapshot` reports
> **`[UNMAP] 10 catalog rows`** — *0 of 10 accounted for, 0 probed, 0 covered, 0
> waived, 0 deferred.* Nothing in `ccf_dataprep` has ever asserted that an element
> this spec names is actually present. Every row below is therefore evidenced by a
> query run for this document. §F.4 finding 4.

### C.1 Element table

One row per element, not per column. **The system of record names the store, the schema
and the table**, per Dave's ruling of 2026-08-29 (§0).

| # | Element | System of record | Provenance class | Classification | Capability class | `G` | Ontology IRI |
|---|---|---|---|---|---|---|---|
| 1 | Facility type · commitment amount · currency | EDGAR **EX-10** credit agreement, header and Article II, extracted at build time → **PostgreSQL** `ccf_v2.facility` | `public` | `public` | `relational` | **E** | `fibo-fbc-dae-dbt:CreditFacility` — see §C.3 |
| 2 | Effective date · maturity date | EX-10 credit agreement → **PostgreSQL** `ccf_v2.facility` | `public` | `public` | `relational` | **E** · **T** | `fibo-fbc-dae-dbt:CreditFacility` |
| 3 | Pricing grid — margin by leverage tier | EX-10 pricing schedule → **PostgreSQL** `ccf_v2.facility.pricing_grid` (`jsonb`) | **mixed** — tier thresholds `public`, margins `synthetic — internal` | `internal` | `relational` | **E** | `[TBC — ccf_dataprep]` |
| 4 | Administrative agent identity | EX-10 preamble → **PostgreSQL** `ccf_v2.facility.administrative_agent` | `public` | `public` | `relational` | **E** | `[TBC — ccf_dataprep]` |
| 5 | Facility type taxonomy | FIBO → asserted in **Fluree** `fibo-v2`, **not read by this product** — see §C.3 and §F.3 | `public` | `public` | `graph-traversal` | **schema** | `fibo-fbc-dae-dbt:` `CreditFacility` · `CommittedCreditFacility` · `UncommittedCreditFacility` · `RevolvingLineOfCredit` |
| 6 | Aggregate debt reconciliation | 10-K debt footnote → **PostgreSQL** `ccf_v2.debt_reconciliation` | `public` | `public` | `relational` | **E** | `[TBC — ccf_dataprep]` |
| 7 | Amendment **number** | 8-K Item 1.01 filing counts → **PostgreSQL** `ccf_v2.facility.amendment_count`, `.is_amended_restated` | `public` | `public` | `relational` | **E** | `[TBC — ccf_dataprep]` |
| 7b | Amendment **effective date** | **absent from this store** — see §C.4 trap 2 | `synthetic — internal` where it exists at all | — | — | **T** | — |
| 8 | `facility_id` ↔ borrower LEI crosswalk | internal → **PostgreSQL** `ccf_v2.facility.borrower_lei` | `synthetic — internal` | `internal` | `relational` | **E** | `[TBC — ccf_dataprep]` |
| 9 | Outstanding balance · undrawn availability | internal loan system → **PostgreSQL** `ccf_v2.facility`, with `balance_as_of` | `synthetic — internal` | `internal` | `relational` | **E** · **T** | `[TBC — ccf_dataprep]` |
| 10 | Internal facility risk rating | internal → **PostgreSQL** `ccf_v2.facility.internal_risk_rating` | `synthetic — internal` | `internal` | `relational` | **E** | `[TBC — ccf_dataprep]` |
| 11 | **Entitlement scope** — facility need-to-know and borrower jurisdiction | Entitlement service → **PostgreSQL** `ccf_v2.principal`, `ccf_v2.principal_jurisdiction` | `synthetic — internal` | `internal` | `relational` | **P** | `[TBC — ccf_dataprep]` |

> **Eleven rows against the vault's ten, and the delta is deliberate.** Row **7b** splits
> the vault's single *"Amendment number and effective date"* row in two, because the
> estate satisfies one half and not the other, and a single row would have to be marked
> either satisfied or absent — both of which would be wrong. Row **11** is added:
> the vault's §C omits entitlement scope although its §B declares a Policy Binding and
> its §D step 2 runs a Policy Operator. **An operator with no §C row has nothing to
> read.** §F.4 findings 2 and 5.

**Provenance and classification, measured rather than asserted:**

| Table | Rows | `provenance` | Note |
|---|---|---|---|
| `facility` | **60** | `provenance_public = 'public'` **and** `provenance_internal = 'synthetic — internal'` — 60 of 60 on both | one row is both; `source` reads *"SEC EDGAR EX-10 credit agreement (build-time extraction)"* |
| `debt_reconciliation` | **14** | derived from 10-K footnotes | covers **14 of the 22** borrowers |
| `principal` | **4** | `synthetic — internal` | `sees_need_to_know` true for **1** of 4 |
| `principal_jurisdiction` | **17** | `synthetic — internal` | one row per `(principal, jurisdiction prefix)` |

**Population shape, measured 2026-08-29 — and it exceeds the vault's manufacture
envelope on every axis:**

| The vault's §F asks for | Estate holds | |
|---|---|---|
| ~40 facilities | **60** | over |
| across ~50 anchor obligors | **22 distinct borrowers**, 0 orphan LEIs | fewer borrowers, more facilities each |
| revolver, term A, term B, delayed-draw | **5 types**: Revolving Credit Facility 25 · Term Loan 18 · Term Loan A 8 · Term Loan B 6 · Delayed Draw Term Loan 3 | over |
| ~8 facilities with ≥1 amendment | **43**, ranging 1 to **21** amendments | far over |
| ~4 syndicated | **54** | far over |
| pricing grids with ≥3 leverage tiers | **59 of 60 carry a grid, and every one has ≥3 tiers** — 3 tiers ×9, 4 ×6, 5 ×44 | over |

**No number above is a fact about any real company's credit facilities**, and the
margins inside every pricing grid are invented.

### C.2 Capability decomposition

This product requires only `relational`, and Standard §3.2 asks for the decomposition
anyway — an estate rarely fails a capability wholesale, and the partial is the finding
worth having.

| Property | Common estate answer | This estate | If absent |
|---|---|---|---|
| Set-based query over structured records | widely available | satisfied | **blocking** — nothing about this product survives |
| **Date arithmetic in the read path** — `effective_date + interval` compared against a supplied instant | widely available | satisfied | **degrades to computing the expiry in the assembler.** Not blocking, but it moves the TTL out of the query and into code, where §D.4's hash must still see it |
| **Prefix match** of a principal's grant against the **borrower's** jurisdiction | sometimes | satisfied — `US` matches `US-DE`, `US-MD`, `US-MN`, `US-OH`, `US-FL` | degrades to exact match, collapsing 46 US-state facilities out of a `US` grant |
| **Structured document value** — a pricing grid read as a tiered structure, not a scalar | sometimes | satisfied — `jsonb`, `pricing_grid->'tiers'` is an array of `{leverage_le, margin_bps}` | **degrades to a single headline margin**, which is the §C.4 trap 4 failure: a grid flattened to a number answers the wrong question |
| Nullable numeric and date columns with meaning | widely available | satisfied | needed for the 7 null maturities and 1 null commitment to be `NOT_EVALUABLE` rather than zero |

**The fourth property is the one to notice.** A store that can hold the grid only as a
scalar does not fail loudly — it returns *a* margin, and a credit officer reading it
during an amendment negotiation cannot tell that the leverage tiers it depends on were
discarded. **Interim posture if absent:** serve with `pricing_grid` marked
`NOT_EVALUABLE` and the claim excluded from the payload, rather than serving a
headline margin that looks answered.

### C.3 Correlation key, single-writer discipline, and identity authority

**Correlation key.** `facility_id` internally — **60 distinct values over 60 rows**,
unique. `borrower_lei` joins the entity side, and every one of the 60 resolves into
`ccf_v2.legal_entity` with **zero orphans**.

**The anchor is not a legal entity, and that is this rung's structural point.** Rung 01
anchors on an identity — a thing the fabric already knows how to resolve. This product
anchors on an **instrument**, whose identifier is internal, has no external registry
behind it, and cannot be validated against anything outside the bank. There is no GLEIF
for facilities.

**What that costs, stated rather than implied:** `facility_id` is
`synthetic — internal` (§C.1 row 8), so an anchor that does not resolve is
indistinguishable from an anchor that never existed. The step therefore fails closed to
a `404` and **never to an empty payload** (§D.3).

**Single-writer discipline.** The EX-10 extraction writes the public terms; the internal
loan system writes balance, availability and rating; the entitlement service writes
scope. **No element is written by two systems.** Notably, the **borrower's** identity is
written by neither — it is resolved through `counterparty-reference-snapshot`, which is
why that product is the prerequisite rather than an optional enrichment.

**Ontology typing.** `CreditFacility` is a **FIBO** term, and its module is the trap:

> `fibo-fbc-dae-dbt:CreditFacility` lives in **`FBC/DebtAndEquities/Debt/`** — **not in
> `LOAN/`**, where a reader looking for a lending term will look first.

Source: the vault's `fibo-iri-binding` mirror. The four bound classes are
`CreditFacility`, `CommittedCreditFacility`, `UncommittedCreditFacility` and
`RevolvingLineOfCredit`, the last bound specifically to *facility type = revolver*.

**This product does not assert those IRIs, and that is a deliberate tier decision.** The
typing is asserted in Fluree, which this product does not read (§F.3). Measured
2026-08-29, the graph holds **45 `CreditFacility` instances against this store's 60
facilities** — the two populations do not agree, and reconciling them is
`corporate-family-tree`'s problem at rung 04, not this one's. **Stated rather than
silently ignored**, because a reader who finds the discrepancy later will trust the rest
of this document less. §F.4 finding 6.

### C.4 The traps — what the data does not support cleanly

Four, each with the binding chosen and what it costs. Standard §3.2's *"the partial is
the finding worth having."*

**Trap 1 — four facilities whose maturity date precedes their effective date.**

Measured 2026-08-29:

```
FAC-044206  Term Loan                  effective 2026-06-29  maturity 2025-12-15  -196 days
FAC-1F0DF6  Term Loan B                effective 2026-06-29  maturity 2025-12-15  -196 days
FAC-66B83D  Revolving Credit Facility  effective 2026-06-29  maturity 2025-12-15  -196 days
FAC-83731D  Term Loan A                effective 2026-06-29  maturity 2025-12-15  -196 days
```

**All four share one `source_accession`: `0000950142-26-001951`.** One extraction, four
facilities, one defect — which is the shape worth noticing. A per-row plausibility check
reports four independent anomalies; the accession is what says it is one.

**Binding chosen:** the pair is served, and the **tenor claim** — the thing a credit
officer derives from the two dates — is marked **`NOT_EVALUABLE`** rather than computed.
A negative tenor is not a short loan; it is an assertion that the agreement matured
before it began.

**What it costs.** The product cannot repair the dates, and must not: repairing them
would put an invented maturity into a payload that claims `public` provenance on that
field. So four facilities serve with a debt contribution and an unusable claim, which
is exactly what §E.2's per-claim decomposition exists to express. Gate `FTS-G08`.

**Trap 2 — the amendment date does not exist, in a product whose whole subject is
amendment-driven freshness.**

The vault's §C asks for *"Amendment number **and effective date** — 8-K Item 1.01
filings."* The estate holds the number and not the date:

| What the vault names | Where it is | Measured |
|---|---|---|
| amendment **number** | `ccf_v2.facility.amendment_count` | **43 of 60** carry ≥1; range 1–21 |
| amendment **effective date** | **nowhere in `ccf_v2`** | a schema-wide column search for `amend%` returns `facility.amendment_count`, `drawdown.amendment_number` and `system_trade_record.amendment_seq` — **three counters and no date** |

`ccf_dataprep`'s own `docs/known-issues.md` §1.1 documents why, and it is worth quoting
because it is the honest half:

> *"Only the **facility** effective date is public, extracted from the EX-10 'dated as
> of' clause. Amendment effective dates are derived by stepping forward from it
> (`prior + random(120–400) days`); the 8-K Item 1.01 filings were never mapped to the
> specific facility each one amends. The amendment **count** per facility is public.
> The amendment **dates** are not."*

Where synthetic amendment dates do exist they are **in Fluree**, a Tier-2 store this
product does not read.

**Binding chosen:** `amendment_count` is served as a **count**, and the product makes
**no claim about when any amendment took effect**. `ttl_basis` therefore names
`effective_date` — the original agreement — and says so in the payload, so a consumer
can see which date the expiry was measured from rather than inferring it.

**What it costs, and it is the largest cost in this document.** The vault's §B declares
the freshness SLA *"amendment-driven — terms are current until an amendment files"*, and
**the estate cannot evidence that event.** So the product's expiry is anchored on the
agreement's **origination**, and for the 43 amended facilities that is a date the terms
have demonstrably moved away from. **This is the mechanism behind §B.1's 50-of-60
refusal**, and it is the same finding seen from the data side rather than the clock
side. §E.5 sets out what could be done about it; §F.4 finding 2 is the return.

**Trap 3 — the document offsets are right there, and reading them would silently make
this a Tier 4 product.**

`ccf_v2.facility` carries `source_accession`, `source_document` and `source_offsets`,
**populated on 60 of 60 rows**. Character offsets into the credit agreement text are
available in the same row as the terms.

**Binding chosen:** they are **not read**, and not carried in the payload. The vault's
extraction note is the rule: *"The public elements here originate in text, not in a
structured feed. At T1 they arrive pre-extracted as Postgres rows — the parsing is a
build-time step performed once during data assembly, not a runtime operator... a T1
example that reaches into a document has silently become a T4 example."*

**What it costs.** A consumer cannot verify a term against its source passage; that
capability arrives at `covenant-cross-reference` (rung 13). The cost is real and it is
the tier boundary being honest rather than a shortcoming. **A tier boundary the data
does not enforce has to be enforced by the specification**, which is why this is a trap
and not a footnote. Gate `FTS-G06` asserts that no offset, accession or document
identifier appears in the served payload.

**Trap 4 — the pricing grid is a structure, and a scalar reading of it passes every
completeness check.**

`pricing_grid` is `jsonb`, and its shape is an **object**, not an array:

```
{"basis": "Consolidated Leverage Ratio",
 "tiers": [{"leverage_le": 1.0, "margin_bps": 125}, … ],
 "provenance": "public — tier thresholds from EX-10; margins synthetic — internal"}
```

**The obvious check is wrong here, and the estate proves it.** `jsonb_array_length` over
the column returns **0 facilities with ≥3 tiers**, because the column is not an array —
the tiers are one level down. Read correctly through `pricing_grid->'tiers'`, **all 59
grids have at least 3 tiers**: 9 at three, 6 at four, 44 at five.

**Binding chosen:** the grid is served as a **typed tier list**, and the count of tiers
is asserted against the structure rather than the column.

**What it costs.** Nothing in data terms — the estate is richer than the vault's
envelope asked for. What it cost was a **measurement that read 0 and would have been
reported as a gap**, and the discipline that caught it is the one below.

> **The method these four traps share, and it is the same one rung 01 recorded: a check
> whose population is not its question.** A per-row date check asked whether four
> facilities were anomalous when one accession was; a column search for `amend%` found
> three counters and would have read as coverage; a `jsonb_array_length` asked whether a
> grid was an array. **Bound is not the same as materialized, and shaped is not the same
> as bound.** This rung adds the fourth instance of the class to the three rung 01
> cataloged, and the addition was found by re-running the check a different way rather
> than by re-reading it.

---

## Section D — Assembly recipe

### D.1 Client call

```
GET /context-products/reference/facility/FAC-08D5BB
      ?intent=drawdown-review&include_pricing_grid=true&debt_tolerance=0.25
```

The **forensic** case is not available at this tier: `as_of` is declared-but-inert
(§B.4), so the live call is the only one. The `as_of` variant appears at §D.7 as the
input to gate `FTS-G05` rather than as a client call.

### D.2 Operator step table

Numbered, **one operator per step**, with the Standard's seven columns and an **eighth
the Standard does not require: the SDK mechanism, named with its layer** — following
`CP-SPEC-000` and `CP-SPEC-001`, so a name that differs between the Standard's closed
vocabulary and the SDK's four operator categories reads as a **mapping** rather than as
a gap in either direction.

| # | Operator | Capability class | Inputs | Emits (as it appears in lineage) | Failure behavior | p95 budget | **SDK mechanism (layer)** |
|---|---|---|---|---|---|---|---|
| 1 | **Resolve** | `relational` | `facility_id` — an internal instrument identifier | `facility_id`, the canonical term set, `borrower_lei`, and **`ttl_basis`** naming the date the expiry will be measured from | fail closed → **404**. An anchor resolving to nothing is never an empty payload. **A `facility_id` has no external registry** (§C.3), so a `404` is the only honest answer | `[TBC — this build, P6]` | `src/ccf/assembly/worker.py::SpecDrivenEntityResolution` under `::AssemblyWorker`, driven by `::EntityResolutionSpec` — **L2**, the single writer |
| 2 | **Policy** | `relational` | the resolved facility; the principal's `sees_need_to_know` flag and its `principal_jurisdiction` grant set, matched against **the borrower's** `legal_jurisdiction` | `policy_version`, and the **principal-permissible facility set substituted for the full set** | fail closed → **403**, with no detail on what exists. Entitlement source unreachable → **503**, never a permissive default | `[TBC — this build, P6]` | `src/ccf/operators/categories.py::PolicyFilter` — **L4** |
| 3 | *contract assembly* — **not an operator** (Standard §10.2 retires `Compose`) | `in-memory` | outputs of 1–2, the declared lineage, the declared TTL and its anchor, **and `effective_date`** | the served `src/ccf/products/contract.py::ContextProductContract` held inside a `ServableProduct`; `expires_at`; `payload_hash`; `context_debt` | fail closed → **503** on any gate refusal, returned **as data** and never as a `200` with a warning. **409 is reserved for the debt gate** | `[TBC — this build, P6]` | `src/ccf/products/gates.py::run_gates` → `::ServableProduct` — **L6** |

**Budget total: `[TBC — this build, phase P6]` against a declared p95 envelope of
`[TBC — this build, phase P6]`.**

**Two notes on those placeholders, both carried forward from rung 01 because the
reasoning has not changed.** The Standard fixes no numeric latency envelope for Tier 1
— §13 gives cost *bands* and §7 asks each product to publish its own p50/p95 — so any
envelope is **declared by this spec**; and a budget authored before a run is a design
target, not a measurement, so writing three numbers that would be indistinguishable
from measurements once written down is the error §F.2 exists to prevent.

**A third note that is specific to this product.** Step 3 does **date arithmetic that
step 1 supplied the input for**, and the split matters: `Resolve` emits `ttl_basis` — a
date — and contract assembly turns it into `expires_at`. Putting the arithmetic in step
1 would make the expiry a property of the resolution rather than of the contract, and
a later rung that changes the TTL would have to change its resolver.

### D.3 Step detail

**Step 1 — `Resolve` anchors on an instrument, and says which date the expiry will
hang off.**

The anchor is a `facility_id`, and §C.3 records what that costs: no external registry
stands behind it, so resolution is a single-table lookup that either finds a row or
does not. **A miss is a `404` and never an empty payload** — an empty payload for an
instrument identifier reads as *"this facility has no terms"*, which is a claim about
the world rather than about the request.

The step emits **`ttl_basis`** as a named date rather than leaving §D's step 3 to pick
one. This is deliberate and it is the direct consequence of §C.4 trap 2: the estate
holds two dates that a reader could plausibly believe the expiry is measured from —
`effective_date`, the agreement's own *"dated as of"*, and `retrieved_at`, when the
extraction ran — and they mean entirely different things. A payload that does not name
which one it used cannot be checked. §E.5 measures both.

**Step 2 — Policy runs first, and at this rung it is the most exclusionary it has been
in the catalog so far.**

Two conditions compose, and both are the vault's §B term (*"Entitlement scope;
facility-level need-to-know"*):

1. **Need-to-know** — `principal.sees_need_to_know`. Measured 2026-08-29: **1 of 4**
   principals carries it.
2. **Borrower jurisdiction** — the principal's `principal_jurisdiction` prefixes,
   matched against the **borrower's** `legal_jurisdiction`. **A facility inherits its
   visibility from its borrower**, which is a decision rather than a mechanism: an
   instrument has no jurisdiction of its own in this estate.

Measured 2026-08-29 as **visible-set inequality**, not as column presence:

| Principal | Grant set | `sees_need_to_know` | Facilities visible by jurisdiction (of 60) |
|---|---|---|---|
| `PRIN-RES-002` research analyst | `CA`, `GB`, `US` | **false** | **60** |
| `PRIN-COV-001` coverage banker | `US` | **true** | **50** |
| `PRIN-KYC-004` EU KYC analyst | `AT BE DE ES HU IT LU NL SE` | false | **0** |
| `PRIN-TRD-003` trader | `GB HK JP SG` | false | **0** |

**Three things a pass/fail verdict would have hidden, and each shapes a gate:**

- **The two conditions disagree, and that is the point.** `PRIN-RES-002` sees every
  borrower's jurisdiction and holds **no** facility-level need-to-know. If jurisdiction
  alone gated the product, a research analyst would read the whole book. Gate
  `FTS-G03` asserts the need-to-know condition is load-bearing by showing that removing
  it changes the served set — which is the check rung 01's trap 3 exists to teach.
- **Two principals see zero, and zero is a legitimate answer.** `PRIN-KYC-004` and
  `PRIN-TRD-003` have grant sets naming no jurisdiction any borrower here is organized
  in. This is the **empty served set** case that rung 01 registered as having *no
  instance in its data* (`CPR-G08`, §F.2 row 20). **This product has two instances of
  it**, and it therefore has to answer the question rung 01 could only pose.
- **The borrower jurisdictions are concentrated**, which is why the numbers are 50 and
  10 rather than something smoother: `US-DE` alone carries **34 of 60** facilities
  across 13 borrowers, and the entire non-US population is **`CA-BC` (8) and `CA` (2)**.

**What a principal who sees zero receives, decided here.** A **`403` fail-closed
refusal carrying no detail about what exists** — not a `200` with an empty list, and
not a `404`. The reasoning is the suppression rule (§B.2): a `404` asserts the facility
does not exist, which is a disclosure in the opposite direction, and a `200` with an
empty list invites the consumer to conclude the borrower has no facilities. Gate
`FTS-G04` proves the two refusals are indistinguishable from each other.

**The suppression rule is what makes the ordering structural.** Facilities outside the
principal's permission are **never materialized and then filtered** — the permissible
set is substituted *for* the full set, so there is nothing to leak a count from.

**Step 3 — contract assembly computes the expiry, and this is the step the product
exists for.**

Standard §10.2 retires `Compose`; contract assembly is the terminal step and names no
operator. `ServableProduct` is not constructible outside `run_gates`, so **holding one
is itself the evidence** that the shipped gates executed.

The expiry is computed as:

```
expires_at = ttl_basis + 90 days
```

where `ttl_basis` is the date step 1 named. **`asked_at` appears nowhere in that
expression, and that absence is the whole primitive.** Two calls for the same facility
at two different moments return the **same** `expires_at`. Gate `FTS-G01` asserts
exactly that, and it is the one gate whose failure would mean the product had become
its own counterfactual.

**The four composition invariants (Standard §10.3), each stated against this
composition rather than asserted generally:**

| Invariant | Holds here because |
|---|---|
| **Policy before anything that reads graph state** | `Policy` is step 2 of 3, and step 3 is contract assembly — nothing reads graph state after it. Impermissible facilities are **never materialized and then filtered** |
| **Resolve before Traversal** | vacuously — **there is no Traversal step.** Stated rather than skipped: the scope boundary excludes relationships (§B.5), and rung 05 will add traversal over this anchor and inherit a correct ordering |
| **Enrich is batched, always** | vacuously — **there is no Enrich step.** One read per source per step |
| **Algorithmic substrate before any semantic stage** | vacuously and permanently — **Assembly Mode 1.** No LLM anywhere in the path |

**Three of the four hold vacuously**, as at rung 01, and the first is again the only one
this composition could violate.

### D.4 Determinism class and payload hash

**Determinism class: `deterministic`.** Same `facility_id` + `principal` +
`policy_version` + graph snapshot → **byte-identical payload**. Mode 1, no model.

The hash is taken over the deterministic portion, **excluding `assembled_at`**. Replay
asserts **hash equality, not similarity**.

| Input | In the hash? | Why |
|---|---|---|
| the resolved facility's terms at `graph_snapshot_at` | **yes** | it is the payload |
| `policy_version` **and the principal** | **yes** | two principals legitimately receive different answers for the same facility; a hash blind to the principal reports drift where there is none |
| **`include_pricing_grid`** | **yes** | it is the one parameter that changes the payload's **shape** (§B.4). Two genuinely different payloads sharing a hash is a worse failure than two identical ones differing |
| **`expires_at`** | **yes** | it is derived from `ttl_basis`, which is a fact about the facility. A hash blind to it would report agreement between a product anchored on the agreement date and one anchored on the load date — the exact substitution §E.5 is about |
| `asked_at` / `assembled_at` | **no** | they change on every call, and would make every hash unique, which is the same as having no hash |

`payload_hash` value: `[TBC — this build, phase P6]`.

### D.5 Replay statement and replay test

**Replay statement.** The engine re-reads the facility at `graph_snapshot_at`, reloads
`policy_version`, re-runs `Resolve` and `Policy`, and **asserts hash equality**. No
model is invoked, so reproduction is exact.

**Falsifiable replay test.** A numbered procedure ending in an assertion that can fail:

1. Serve the product for a known `facility_id`. Record `graph_snapshot_at`,
   `expires_at` and `payload_hash`.
2. Land a change to that facility's `commitment_amount` in the source.
3. **Re-derive live.** The new commitment returns and the hash **differs**.
4. **Re-derive at the recorded `graph_snapshot_at`.** The original payload returns and
   the hash **matches**.
5. **Re-derive live at a later `asked_at`, with no source change.** The hash
   **matches**, and `expires_at` is **unchanged** — the assertion that separates this
   product's anchor from `from_decision`.

**Step 5 is this product's addition to the rung-01 procedure**, and it is the one that
can fail silently: an implementation that recomputed `expires_at` from `now` would pass
steps 1–4 unchanged and fail only here.

`[TBC — this build, phase P6]` — fixture `FTS-R01`, all three hashes.

### D.6 Emitted contract

The Standard's response envelope (§8 — cited as §10 in the Standard's own text; its
cross-references are stale in six places and resolve **by heading**), populated with
this product's payload schema, **with types**.

```jsonc
{
  "product": "reference.facility",                  // string
  "semantic_version": "1.0.0",                      // string
  "payload": {
    "facility_id":         "string",                // as supplied; internal identifier, no external registry
    "borrower_lei":        "string",                // LEI(20); resolves via cp-01
    "facility_type":       "string",                // e.g. "Revolving Credit Facility"
    "commitment_amount":   "number | null",         // null for 1 of 60; NOT_EVALUABLE, never 0
    "currency":            "string",                // ISO 4217
    "effective_date":      "date",                  // the EX-10 "dated as of" clause
    "maturity_date":       "date | null",           // null for 7 of 60
    "tenor_days":          "number | null",         // null when maturity < effective — §C.4 trap 1
    "administrative_agent":"string | null",
    "amendment_count":     "number",                // a COUNT; no date is claimed — §C.4 trap 2
    "is_amended_restated": "boolean",
    "syndicated":          "boolean",
    "pricing_grid": {                               // omitted entirely when include_pricing_grid=false
      "basis":  "string",                           // e.g. "Consolidated Leverage Ratio"
      "tiers":  [ { "leverage_le": 0.0, "margin_bps": 0 } ]
    },
    "outstanding_balance": "number | null",
    "undrawn_availability":"number | null",
    "balance_as_of":       "date | null",           // the balance's OWN observation date
    "internal_risk_rating":"string | null"
  },
  "contract": {
    "assembled_at":     "iso8601",
    "expires_at":       "iso8601",
    "ttl_anchor":       "from_entity_freshness",
    "ttl_basis":        "effective_date",           // WHICH date the expiry was measured from
    "ttl_basis_value":  "date",                     // and its value, so a consumer can check the arithmetic
    "assembly_mode":    1,
    "determinism_class":"deterministic",
    "freshness": [
      { "signal_class": "agreement-terms" | "loan-system-balance" | "internal-rating",
        "observed_at": "iso8601", "lambda_c_hours": 0, "relevance": 0.0 }
    ]
  },
  "lineage": {
    "operators_invoked": ["Resolve", "Policy"],
    "graph_snapshot_at": "iso8601",
    "policy_version":    "string",
    "projection_plan_id": null,                     // Π not exercised at T1
    "model_record":       null,                     // Mode 1
    "payload_hash":      "string"
  },
  "context_debt": { "F": 0.0, "C": 0.0, "S": 0.0, "D_c": 0.0, "contributions": [] },
  "notices": []
}
```

**Five things this shape commits to, each of which a reviewer can check:**

1. **`ttl_basis` and `ttl_basis_value` are in the contract, not the lineage.** The
   expiry's derivation is a fact *about the answer's validity*, which a consumer must
   be able to check without parsing how the assembly ran. **This is the field §E.5's
   whole argument turns on**: without it, two products anchored on different dates are
   indistinguishable on the wire.
2. **`tenor_days` is nullable and is the only derived field in the payload.** §C.4 trap
   1: for the four facilities whose maturity precedes their effective date it is
   `null` and the claim is `NOT_EVALUABLE` — **never a negative number**, which would
   be arithmetic reported as a term.
3. **`amendment_count` appears and no amendment date does.** §C.4 trap 2. The payload
   states what the estate can evidence and is silent on what it cannot, rather than
   carrying a synthetic date that would look filed.
4. **No `source_accession`, `source_document` or `source_offsets` field exists.** §C.4
   trap 3 — the tier boundary, enforced by the contract's own shape rather than by
   discipline at call time. Gate `FTS-G06`.
5. **`balance_as_of` is separate from `contract.assembled_at` and from
   `ttl_basis_value`.** Three dates that mean three different things; collapsing any
   two is how a 1-day signal starts wearing a 540-day signal's currency (§E.1).

**`extra=forbid` is enforced as a build-time CI invariant.** A per-product subclass may
not add a field the base did not declare, and a pull request introducing a drifted
contract fails before it reaches a deployment surface. `[TBC — this build, phase P6]`
— the schema artifact and its CI binding.

### D.7 Validation gates

**The Standard names six universal gates. This SDK ships THREE** inside
`src/ccf/products/gates.py::run_gates`, and **`D-IMPL-102` limb 3 rules that no fourth
joins them.** What follows is what each of the six actually is here. **Nothing below
claims the SDK runs a gate it does not run.**

**The three that are shipped gates, in `run_gates`' own order:**

| # | Gate | SDK mechanism | What it refuses here |
|---|---|---|---|
| 1 | Empty-operator guard | `gates.py::_refuse_empty_operators` (INV-CH7-46) | a product whose `lineage.operators_invoked` is **empty** — a product computed by nothing |
| 2 | Lineage strict equality | the `declared != engine_resolved` comparison in `run_gates`, returning `::LineageMismatchRefusal` (INV-CH7-47) | any difference, **in either direction**, between `[Resolve, Policy]` as declared at §B.1 and the set the engine resolved |
| 3 | TTL bounds | `gates.py::_refuse_ttl` against the class's pinned `MAX_TTL` | `expires_at` outside `now < expires_at <= now + MAX_TTL`. **This is the gate §B.1's measured consequence trips, on 50 of 60 facilities** |

**The other three, each as it actually stands:**

- **Debt gate.** A **Control Plane posture**, not a shipped gate. `debt_tolerance` is a
  request parameter (§B.4) and the refusal is raised by the deployment, returning
  **`409` with the debt block** — *not* a `200` with a warning. `[TBC — this build,
  phase P7]`.

  **SUPERSEDED, 2026-09-03 (Phase 24.5.1, `D-IMPL-245` (3)).** When measured, no rung
  of the ladder tested `debt_tolerance` against anything and no 409 was wired.
  `24.5-L-14` shipped the mechanism: `src/ccf/products/gates.py::effective_debt_ceiling`
  resolves a CLASS-declared ceiling that a request may only tighten (`D-IMPL-240` (3)),
  and a breach is a `DeclaredObligationRefusal`, which the HTTP door renders as 409
  (`runtime/ccf_runtime/http_api/routes/product.py::build_router`). This product declares no
  ceiling, so nothing in its behavior moved; the `[TBC]` stands as written.
- **Suppression silence.** Not a shipped gate; realized **structurally** by the step
  ordering at §D.2. Proven by product-specific gate `FTS-G04` rather than asserted —
  and this product is the first with a **zero-visible principal** to prove it against.
- **Classification containment.** Not a shipped gate. Declared classification is
  `internal` (§B.2) and no `confidential` or `restricted` element is in scope.

**Product-specific gates.** Nine, each naming the trap or the design decision it
defends:

| Gate | Asserts | Defends against | Fixture |
|---|---|---|---|
| **FTS-G01** Expiry does not move with the question | the **same** facility asked for at two different `asked_at` values returns the **same** `expires_at`, to the second | the entire counterfactual (§A) — an anchor labelled `from_entity_freshness` that is `from_decision` underneath | `FTS-G01` |
| **FTS-G02** Entitlement discriminates | **at least one** principal pair whose **visible facility SETS** differ, with a named facility visible to A and not B. **Counts sets, never sizes.** Carries a **negative control**: a principal differenced against itself must report identical. **It must NOT demand that every pair differ** — see the note below | a Policy step that is a no-op, and a cardinality check that passes one — rung 01's trap 3 | `FTS-G02` |
| **FTS-G03** Need-to-know is load-bearing | removing the `sees_need_to_know` condition **changes** the served set. A principal with jurisdiction but without need-to-know receives nothing | a two-condition policy where only one condition does any work, which passes every set-difference check | `FTS-G03` |
| **FTS-G04** Suppression silence, including the empty case | two principals' payloads differ in **content** and are **indistinguishable in structure**; and a principal seeing **zero** facilities receives a refusal **indistinguishable from** the refusal for a facility that does not exist | a `404` that discloses non-existence, a `200` with an empty list that implies it, and any `"n hidden"` marker | `FTS-G04` |
| **FTS-G05** Inert parameter fails loudly | `as_of` returns **`400 not_supported_at_tier`** and **never** silently succeeds against current state | §B.4 — and it matters more here, because 43 facilities visibly have a history to ask about | `FTS-G05` |
| **FTS-G06** The tier boundary holds | **no** `source_accession`, `source_document` or `source_offsets` value appears anywhere in the served payload or its lineage | §C.4 trap 3 — a T1 product that has silently become a T4 product | `FTS-G06` |
| **FTS-G07** Pricing grid is a structure | the grid is served as `basis` + a **tier list of ≥3 entries**, read through `pricing_grid->'tiers'`; a scalar margin is never substituted | §C.4 trap 4 — a flattened grid that answers the wrong question and passes completeness | `FTS-G07` |
| **FTS-G08** Incoherent tenor is not computed | for a facility whose `maturity_date` precedes its `effective_date`, `tenor_days` is **null** and the claim is marked `NOT_EVALUABLE` — **never a negative number** | §C.4 trap 1 — arithmetic served as a term | `FTS-G08` |
| **FTS-G09** The TTL refusal, asserted so that fixing it goes red | a facility whose `effective_date` is older than 90 days is **refused on `ttl-bounds`**, and the refusal names `ttl_basis`. **The gate is written to assert the shipped behavior, and it is expected to turn RED when the declaration is corrected** — that redness is the signal to close §F.4 finding 1 | §B.1 element 3's measured consequence — **50 of 60** facilities refused on first call | `FTS-G09` |

**Every gate must be made to fail deliberately once.** `[TBC — this build, phase P7]`
— the sabotage applied to each, and the observed result. A gate that has never been
observed red is not evidence that it runs.

> **`FTS-G09` is the one to read twice, and its shape is inherited deliberately.** Rung
> 01's `CPR-G09` established the pattern: a gate that **asserts a shipped defect** must
> be written so that **fixing the defect turns it red**. Otherwise the test ratifies the
> bug and the finding quietly dies. Here the asserted behavior is the 50-of-60 refusal;
> when §E.5's correction is ruled and applied, `FTS-G09` goes red, and that is the
> signal — not a regression.

> **`FTS-G02` inherits rung 01's shape and then has to depart from it, and the
> departure was measured twice before it was right.** Rung 01 could assert that **all
> six** principal pairs discriminate, because all six did. A gate demanding that here
> would fail against correct data, and the first draft of this row demanded exactly that.
>
> **The figure is 3 of 6, and the first correction — to 5 of 6 — was also wrong.** That
> reading came from the **jurisdiction** table at §D.3, where only `PRIN-KYC-004` and
> `PRIN-TRD-003` see zero. But this gate compares the **served** set, which is after
> BOTH conditions compose — and only `PRIN-COV-001` carries facility-level need-to-know,
> so `PRIN-RES-002` collapses to empty as well despite being granted every jurisdiction
> in the estate. **Three principals see nothing, so all three pairings among them are
> identical and three pairs discriminate.**
>
> **The build's own gate caught it**, reporting `PRIN-KYC-004 and PRIN-RES-002 see the
> same set` against a declaration naming one pair. Both figures in this document are
> correct and they are not the same figure — §D.3's table is jurisdiction-only and says
> so. Reading it as the served set is the specific mistake that produced a wrong gate
> twice, and it is why a gate is written against the measured population rather than
> copied from the product before it.

> **`FTS-G03` exists because of a near-miss this specification found in its own
> design.** The first draft gated only on jurisdiction. Measured against the estate that
> would have served **60 facilities to a research analyst holding no facility-level
> need-to-know** — and `FTS-G02`, comparing sets pairwise, would have **passed**,
> because the sets still differ. A gate that discriminates is not the same as a gate
> that discriminates *for the declared reason*.

---

## Section E — Volatility, debt & materialization

### E.1 Half-life table

The vault's §E, carried, with the calibration basis stated per row:

| Signal class | `λ_c` proposed | Calibration basis | Decay driver | Supersession event | Owner |
|---|---|---|---|---|---|
| Structural terms — type, commitment, maturity | ~**540 days** | **expert** — amendment-driven, not clock-driven | agreement amendment | 8-K Item 1.01 filing | lending product |
| Pricing grid | ~**365 days** | **expert** | repricing on amendment or refinancing | amendment or refinancing | lending product |
| Outstanding balance | ~**1 day** | **expert** | every drawdown and repayment | internal drawdown event | loan operations |
| Internal facility rating | ~**90 days** | **illustrative** | credit review cycle | rating action | credit risk |

**`λ_c` values are proposed here and fixed in Control Plane configuration — a spec does
not set them.** Saying so is the difference between a value an engineer can challenge
and a number they assume was measured. `[TBC — this build, phase P8]` measures decay
against observed read frequency.

> **This table spans three orders of magnitude inside one payload, and the vault says
> so explicitly.** *"A product whose payload mixes a 540-day signal and a 1-day signal
> without surfacing the asymmetry is precisely what §6.4 Temporal Validation refuses to
> assemble — the split is not an optimization, it is the contract behaving correctly."*
>
> **The estate supports the claim and makes it concrete.** `outstanding_balance` carries
> its own `balance_as_of` — measured 2026-08-29, **4 distinct values across 60 rows**,
> spanning `2026-08-22` to `2026-08-25` — while `effective_date` spans **seven years**.
> Two dates, two decay rates, one row. §D.6's payload keeps them separate; a single
> `as_of` over both is the error this table exists to prevent.

> **A caution carried from rung 01, because the error class is documented in this
> catalog.** `spec_generation.md` §10.2 records a vault article setting `λ_c` to a
> **publication cadence** where the true half-life was nearer a year, with an inverted
> materialization posture following from it. **This product is not calibrated**: three
> rows are `expert` and one is `illustrative`, none is measured. Stating that plainly is
> more useful than implying otherwise.

### E.2 Debt model and per-component debt table

**`D_c = 1 − (F · C · S)`** — multiplicative, so a collapsed dimension **forces
escalation** rather than being averaged away.

| Term | Meaning here |
|---|---|
| **F** | age of each signal class against its own `λ_c`, **normalized over required signal classes, not over the classes present**. The three-order-of-magnitude spread at §E.1 means this must be per-class or it is meaningless |
| **C** | fraction of contract-declared attributes populated. Measured shortfalls: 7 null maturities, 1 null commitment, 1 null pricing grid, 1 null balance, 1 null undrawn |
| **S** | agreement between the facility's `commitment_amount` and the borrower's reported debt in `ccf_v2.debt_reconciliation` — **the earliest warning that a facility has been attached to the wrong borrower** |

> **`S` has a live negative instance, which is rare enough to name.** Measured
> 2026-08-29, `debt_reconciliation` holds **14 rows covering 14 of the 22 borrowers**,
> and **1 of the 14 carries `plausible = false`**: LEI `549300KTTIRAOGXCRV69`, committed
> **4,786,505,256** against reported debt **2,944,900,000** — a `share` of **1.625**,
> meaning the facilities attributed to that borrower commit 62% more than its own 10-K
> reports as debt. **That is what `S` is for**, and this product can demonstrate it
> rather than describe it. The **8 borrowers with no reconciliation row at all** are the
> other half: `S` is not computable for them and contributes its full weight.

**Per-component debt table.** Debt is decomposed **per claim, never only per product**.

| Component | May be absent? | `D_c` contribution | Behavior when absent |
|---|---|---|---|
| `facility_id` · `facility_type` · `borrower_lei` | **no** | — | **fail closed → 404.** Without these there is no facility |
| Commitment amount | yes — 1 of 60 | `[TBC — this build, P8]` | serve with the claim marked `NOT_EVALUABLE`; **never 0**, which reads as an uncommitted facility |
| Currency | **no** | — | fail closed. 60 of 60 are `USD`; a missing currency makes every amount meaningless |
| Effective date | **no** | — | **fail closed → 503.** It is the TTL basis (§D.3); without it there is no expiry, and a product with no expiry is the counterfactual |
| Maturity date | yes — 7 of 60 | `[TBC — this build, P8]` | serve; `tenor_days` is `NOT_EVALUABLE` |
| **Coherent date pair** | yes — 4 of 60 invert | `[TBC — this build, P8]` | serve both dates as filed; `tenor_days` `NOT_EVALUABLE`. §C.4 trap 1, gate `FTS-G08` |
| Pricing grid | yes — 1 of 60 | `[TBC — this build, P8]` | serve with the claim marked `NOT_EVALUABLE`; **never a headline margin** |
| Administrative agent | yes — 0 of 60 absent today | `[TBC — this build, P8]` | serve with flag |
| Outstanding balance · undrawn | yes — 1 of 60 | `[TBC — this build, P8]` | serve with flag. **Its `F` is computed against the 1-day `λ_c`, not the product's** |
| **Amendment effective date** | **always absent** — §C.4 trap 2 | `[TBC — this build, P8]` | **no claim is made.** Not a debt contribution against a field the contract does not declare — see below |
| **Entitlement scope** | **no** | — | **fail closed → 503.** An unreachable entitlement service is never a permissive default |
| Debt reconciliation row | yes — 8 of 22 borrowers lack one | `[TBC — this build, P8]` | serve; `S` cannot be computed and contributes its full weight |

**The amendment-date row is the one to argue with, and the argument is rung 01's.** A
field that is **out of scope** contributes no debt; a field that is **in scope and
missing** contributes all of it. The amendment date is not in §D.6's payload (§C.4 trap
2), so under this contract it is out of scope and contributes nothing — the product is
not penalized for declining to claim something it cannot evidence. **The cost lands
instead on `F`**, because the structural-terms signal is aged against an
`effective_date` that 43 facilities have demonstrably moved away from. **That is the
honest place for it**, and it is why §E.5 is a section rather than a footnote.

`debt_tolerance` default **0.25 — provisional and unbacked**.

### E.3 Materialization posture

**The vault declares `materialized`, with the outstanding balance carved out as an
on-demand field.** That declaration is carried, and the carve-out is the interesting
half.

**The Standard's test is mechanical:** if the fastest-moving input's `λ_c` is shorter
than the intended cache window, materialization is wrong. Applied to the whole payload
that test **fails immediately** — `outstanding_balance` has a ~1-day `λ_c`. Applied to
the payload **minus the balance**, the slowest input is 540 days and materialization is
plainly right.

**So the split is not an optimization; it is what makes the posture expressible at
all** — the vault's own words. A product that materialized the balance alongside the
terms would serve a seven-year-stable object with a one-day-stale number inside it, and
nothing in the payload would say which part had gone off.

**Cache key, stated explicitly:** `(tenant, schema_name, facility_id, principal_id,
policy_version, graph_snapshot_at, include_pricing_grid)`.

Note what is present and what is absent:

- **`principal_id` is present** because `Policy` produces a per-principal set (§D.3); a
  key without it returns one principal's facilities to another, which on this product is
  a **disclosure**, not a staleness bug.
- **`include_pricing_grid` is present** because it changes the payload's shape (§B.4),
  and a shared key across two shapes is a correctness defect that presents as a
  formatting one.
- **`asked_at` is absent**, and this is the load-bearing absence: `expires_at` does not
  depend on it (§D.3), so including it would fragment the cache **without changing a
  single byte of any payload** — which is the cache-collapse failure the vault's
  counterfactual describes, arriving through the cache key instead of through the TTL.

### E.4 Supersession triggers

| Event | Local or cascading | Named downstream targets |
|---|---|---|
| 8-K Item 1.01 amendment filing | **cascading** | `covenant-in-force-as-of` first — it time-travels over exactly this event; then `credit-exposure-rollup`, `collateral-and-setoff-coverage` |
| Internal drawdown or repayment | **local** to the balance field | none — the terms do not move |
| Borrower identity change upstream | **cascading, inbound** | this product is a consumer of `counterparty-reference-snapshot`; a borrower supersession invalidates every facility joined to it |
| `principal_jurisdiction` or `sees_need_to_know` change | **local** to the affected principal's cached products | — |

> **The first row names an event this estate cannot detect** (§C.4 trap 2). The
> supersession trigger is declared because it is the correct trigger; the estate's
> inability to observe it is recorded at §F.1 as a gap with an owner, not smoothed into
> a trigger that could be observed but is wrong. **A supersession trigger nobody can
> fire is a known gap; a substituted one is a silent defect.**

### E.5 The expiry, the two candidate bases, and what each measures

**This section exists because §B.1's measured consequence needs a decision, and the
decision is not this document's to take.** It sets out both candidates with their
measured behavior so that whoever rules has numbers rather than arguments.

**What `from_entity_freshness` requires, restated precisely.** The expiry must be a
function **of the facility**. Two facilities must be able to expire at different times;
the same facility asked for twice must expire at the same time. Any basis satisfying
both is a candidate; any basis failing either is a different anchor wearing this one's
name.

| | **Basis A — `effective_date`** | **Basis B — `retrieved_at`** |
|---|---|---|
| What it is | the EX-10 *"dated as of"* clause | when the build-time extraction ran |
| Provenance | **`public`** — a filed fact | `synthetic — internal` — an artifact of loading |
| Distinct values across 60 facilities | **many**, spanning 2019-07-31 → 2026-08-04 | **1** — every row reads `2026-08-25` |
| Facilities live at `+90d`, asked 2026-08-29 | **10 of 60** | **60 of 60** |
| Does the expiry vary per facility? | **yes** | **no — one expiry for the whole product** |
| Is it a fact about the instrument? | **yes** | **no — a fact about our pipeline** |

**Basis B is the one that makes the demonstration comfortable, and it is the one that
silently retires the primitive.** With a single distinct `retrieved_at` across all 60
rows, every facility expires at the same instant — which is a **product-level TTL**,
indistinguishable in behavior from `from_decision` measured off the load. The anchor's
entire content is that expiry is per-entity; a basis with one value across the
population does not express it. **The number that settles this is 1, not 60.**

**Basis A is faithful and expensive.** It is a filed date, it varies per facility, and
it refuses 50 of 60 today. **The refusal is not obviously wrong**: the estate cannot
evidence that any of those 43 amended agreements still stands as originally filed
(§C.4 trap 2), and refusing to serve terms whose currency cannot be established is the
behavior a fabric is for. It is also, on the vault's own framing, the failure this
product exists to refute — *"collapses the cache for no reason"* — with the caveat that
the reason here is **measurable and stated** rather than absent.

**A third possibility exists and is named rather than proposed**: the amendment
effective date, which is the semantically correct basis — *"valid until amended"* — and
which **does not exist in this store** (§C.4 trap 2). It is in Fluree, synthetic, and
reading it makes this a Tier-2 product one rung early. **It is the right answer and it
is unavailable**, which is the most useful thing this section can record.

**What this document does.** It declares **Basis A**, because it is the vault's stated
term (§B.1 element 3) and inventing a substitute would be writing another agent's term.
It registers the consequence as a **build finding** (§F.4 finding 1) with `FTS-G09` as
the gate that settles it, and it sends the measurement back through the §11 return path
with this specification. **The 90-day window itself is the vault's value and is
untouched here**; whether it should widen is a separate question from which date it is
measured from, and conflating them would hide one behind the other.

---

## Section F — Source binding & readiness

### F.1 Element readiness

| Element | System of record | Interface & cadence | Available today | Gap owner | Blocker |
|---|---|---|---|---|---|
| Facility type · commitment · currency | EX-10 extraction | build-time, one-off | **yes** — 60 of 60 type and currency; **59 of 60** commitment | — | — |
| Effective date | EX-10 extraction | build-time | **yes** — 60 of 60 | — | — |
| Maturity date | EX-10 extraction | build-time | **partial** — 53 of 60; **4 more invert** (§C.4 trap 1) | `ccf_dataprep` | not a blocker; `FTS-G08` |
| Pricing grid | EX-10 pricing schedule | build-time | **yes** — 59 of 60, **all ≥3 tiers** | — | — |
| Administrative agent | EX-10 preamble | build-time | **yes** — 60 of 60 | — | — |
| Amendment **number** | 8-K Item 1.01 counts | build-time | **yes** — 43 of 60 carry ≥1 | — | — |
| **Amendment effective date** | 8-K Item 1.01 filings | — | **no** — absent from `ccf_v2`; synthetic in Fluree only | `ccf_dataprep` | **not a build blocker; it is the FINDING** — §C.4 trap 2, §F.4 finding 2 |
| Borrower LEI crosswalk | internal | build-time | **yes** — 60 of 60 resolve, **0 orphans**, 22 borrowers | — | — |
| Outstanding balance · undrawn | internal loan system | internal | **yes** — 59 of 60, with `balance_as_of` | — | — |
| Internal facility risk rating | internal | internal | **yes** — 60 of 60, 8 bands `1A`…`5` | — | — |
| Aggregate debt reconciliation | 10-K footnote | build-time | **partial** — 14 rows covering **14 of 22** borrowers; 1 flagged `plausible = false` | `ccf_dataprep` | not a blocker; degrades `S` |
| Entitlement scope | entitlement service | internal | **yes** — 4 principals, 17 jurisdiction grants, `sees_need_to_know` on 1 | — | — |

> **No element of this product is a build blocker, and one is the reason the product is
> worth building now.** The amendment effective date is absent, the flagship at rung 08
> will need it, and surfacing that six rungs early — with the measurement attached — is
> more valuable than a spec that quietly anchors on the date it happens to have.

### F.2 Every `[TBC]` in this document, with an owner

**Built by enumerating every marker in the document and mapping each to a row**, not by
comparing totals. Rung 01 records why: *"a count is not a roster"* — 48 raw marker
occurrences map to 20 rows, because one row legitimately covers several markers and
four occurrences in §0.2 and the front matter are the placeholder *classes* being
defined rather than markers.

| # | Marker | Section | Owner | Cleared at |
|---|---|---|---|---|
| 1 | **Four-question build-test result** — the vault article is on the Q019 form and has no such section | §0.1, §0.4 | **vault** | — |
| 2 | **Closed-taxonomy mode** for the counterfactual; `temporally-incoherent` proposed, not asserted | §A | **vault** | — |
| 3 | Ontology IRI — **8 of the 11 §C.1 rows** (3, 4, 6, 7, 8, 9, 10, 11) | §C.1 | `ccf_dataprep` | — |
| 4 | Residency constraints | §B.2 | identity and access | — |
| 5 | Cross-border serving condition | §B.2 | identity and access | — |
| 6 | `debt_tolerance` calibration (provisional 0.25) | §B.4, §E.2 | product owner + `ccf_dataprep` | P8 / certification |
| 7 | Schema artifact `facility_terms.v1.json` | §B.1 | this build | P6 |
| 8 | p95 budget — step 1 · step 2 · step 3 · total · envelope | §D.2 | this build | P6 |
| 9 | `payload_hash` value | §D.4 | this build | P6 |
| 10 | Replay fixture `FTS-R01`, **three** hashes | §D.5 | this build | P6 |
| 11 | Schema artifact + `extra=forbid` CI binding | §D.6 | this build | P6 |
| 12 | Debt-gate `409` behavior — **SUPERSEDED 2026-09-03** (Phase 24.5.1, `D-IMPL-245` (3)): the mechanism exists since `24.5-L-14` (`src/ccf/products/gates.py::effective_debt_ceiling`; `DeclaredObligationRefusal` → HTTP 409 at `runtime/ccf_runtime/http_api/routes/product.py::build_router`); cp-02 declares no ceiling, so its behavior is unchanged — see §D.7's debt-gate note | §D.7 | this build | P7 |
| 13 | Sabotage result for each of the nine gates | §D.7 | this build | P7 |
| 14 | Counterfactual fixture `FTS-F01` — the two-`asked_at` comparison | §A | this build | P7 |
| 15 | `λ_c` measured against read frequency | §E.1 | this build | P8 |
| 16 | Per-component `D_c` contributions — **8 rows** | §E.2 | this build | P8 |
| 17 | **Amendment effective dates mapped to facilities** — the data condition §E.4's first supersession trigger acts on | §C.4, §E.4, §F.1 | `ccf_dataprep` | — |
| 18 | **A coverage manifest for this product** in `validators/spec_coverage.py` — it is `[UNMAP]`, 0 of 10 rows | §C preamble | `ccf_dataprep` | — |
| 19 | Debt reconciliation rows for the **8 borrowers** that have none — the condition `S` needs to be computable | §E.2 | `ccf_dataprep` | — |
| 20 | A **mutable attribute plus a retained snapshot** — the data condition `FTS-R01` steps 2–4 act on | §D.5, §F.3 | this build + `ccf_dataprep` | P6 |

**Ten are `this build` and clear at Gate 2. Five are `ccf_dataprep`'s. Two are the
vault's. Two are identity and access's. One is shared. Twenty in total.**

**No `[TBC]` above is a guess wearing a marker** — each names a measurement nobody has
taken or a term nobody has ruled, not a value this document declined to write down.

> **Rows 17 and 20 separate the fixture from the data condition it acts on**, following
> rung 01's correction of exactly that omission. The **test** is this build's to write;
> the **estate condition it needs** is `ccf_dataprep`'s to supply. Collapsing them into
> one row assigns an owner who cannot discharge it.

### F.3 Access path, identifiers, history, and volumetrics

**Estate binding — where the data actually lives.**

| Capability class | Store kind | Namespace this product reads | Connection |
|---|---|---|---|
| `relational` | **PostgreSQL** | schema **`ccf_v2`** — tables `facility`, `debt_reconciliation`, `legal_entity`, `principal`, `principal_jurisdiction` | `backends.yaml` → an env-var **name**; no host, port or credential in this tree |

**The four stores this product does NOT read, and why — stated so their absence reads
as a decision rather than an oversight:**

| Store | Namespace | Why not here |
|---|---|---|
| **Fluree** (graph) | ledger `fibo-v2` | requires `graph-traversal`; there is **no Traversal step** (§D.2) and the scope boundary excludes relationships (§B.5). **It holds this product's FIBO typing and 45 `CreditFacility` instances against this store's 60** — reconciling the two is rung 04's problem, and §C.3 records the discrepancy rather than ignoring it |
| **MongoDB** (documents) | database `fibo_v2` | requires `document-passage`. **This is the boundary the data invites crossing** — `source_offsets` is populated on 60 of 60 rows (§C.4 trap 3) — and gate `FTS-G06` is what holds it |
| **SQLite** (departmental) | `data/departmental.sqlite` | no element of this product is departmental |
| **Neo4j** (optional) | — | not required by any capability class in §C.2 |

**Access path.** Existing load. Every element is already extracted and resident in
`ccf_v2`; **no new acquisition is required for rung 02.** The one element that would
require new acquisition — the amendment effective date — is deliberately **not**
acquired, and is a finding rather than a build task (§F.4 finding 2).

**Identifier reality.** `facility_id` is unique — **60 distinct over 60 rows** — and
`borrower_lei` resolves into `legal_entity` with **zero orphans** across 22 borrowers.
**The anchor has no external registry** (§C.3), which is the structural difference
between this rung and rung 01 and the reason a miss is a `404`.

**History depth.** **None retained.** The estate holds current facility state only;
`retrieved_at` is a single value — `2026-08-25` — across all 60 rows. **This bounds the
replay test at §D.5** and it is the same figure that disqualifies Basis B at §E.5:
one distinct load date means one distinct expiry, and one expiry across a population is
not a per-entity anchor. **History not captured cannot be reconstructed later** — if
rung 08 needs amendment history, retention starts now, not then.

**Text-source boundary.** **Applicable, and enforced.** Every public element originates
in EX-10 text, parsed **at build time, once, outside the runtime path**. The offsets
that would allow a runtime reach into the document are present and unread. Capability
class stays `relational`; cost band stays `×1`. §C.4 trap 3, gate `FTS-G06`.

**First-build volumetrics — the population every gate and counterfactual needs
something to act on:**

| Gate / test | Needs | Estate holds | Sufficient? |
|---|---|---|---|
| `FTS-G01` expiry does not move | ≥1 facility, asked twice | **60** | yes |
| `FTS-G02` entitlement discriminates | ≥1 principal **pair** with different sets | **3 of 6 pairs differ** — see the correction at §D.7 | yes |
| `FTS-G02` negative control | 1 principal to difference against itself | 4 | yes |
| `FTS-G03` need-to-know load-bearing | ≥1 principal with jurisdiction and **without** need-to-know | **`PRIN-RES-002`** — 60 by jurisdiction, `sees_need_to_know = false` | yes |
| `FTS-G04` suppression, empty case | ≥1 principal seeing **zero** facilities | **2** — `PRIN-KYC-004`, `PRIN-TRD-003` | yes |
| `FTS-G06` tier boundary | offsets present and available to leak | **60 of 60** | yes |
| `FTS-G07` grid is a structure | ≥1 grid with ≥3 tiers | **59**, all ≥3 | yes |
| `FTS-G08` incoherent tenor | ≥1 facility with maturity < effective | **4**, all from one accession | yes |
| `FTS-G09` TTL refusal | ≥1 facility older than the 90-day window | **50** | yes |
| `FTS-F01` counterfactual | two `asked_at` values over one facility | trivially available | yes |
| `FTS-R01` replay | a mutable attribute + a retained snapshot | see History depth | `[TBC — this build]` |

> **Every gate but one has an instance in the data, and that is worth stating because
> rung 01 could not say it.** Rung 01 registered `CPR-G08` — the empty served set — as
> having **no instance**, and asked `ccf_dataprep` for a one-row fixture. **This product
> has two instances of exactly that case**, arriving for free from a jurisdiction
> concentration nobody engineered for the purpose. Standard §6's requirement — *"a
> demonstrable primitive with no instance in the data reads to reviewers as machinery
> without a purpose"* — is satisfied here without a data request, and the rung-01 request
> at its §F.2 row 20 can be **answered by this product's population** rather than by new
> fixture data. §F.4 finding 7.

### F.4 Recorded findings — not `[TBC]`, because none needs a decision to build

1. **The declared TTL anchor refuses 50 of 60 facilities on first call, and the
   declaration stands.** `ttl_anchor: from_entity_freshness` over an `effective_date`
   spanning seven years, against a 90-day window, puts `expires_at` in the past for
   every facility not originated in the last quarter — including all 43 carrying an
   amendment history. **The declaration is the vault's** (§B.1 element 3) and is not
   changed here; §E.5 sets out both candidate bases with measured behavior, and shows
   that the comfortable alternative (`retrieved_at`) has **one distinct value across 60
   rows** and therefore is not a per-entity anchor at all. **`FTS-G09` settles it**, and
   is written to turn red when the declaration is corrected. **A §11 return is owed and
   is sent with this specification**, because this is a claim about the world that the
   measurement disputes — not a rule applied at the wrong level.
2. **The vault's §C names an element the estate does not hold: the amendment effective
   date.** §C.4 trap 2. `ccf_dataprep`'s own `known-issues.md` §1.1 documents why — the
   8-K Item 1.01 filings were never mapped to the facilities they amend, and the dates
   that exist are synthetic and live in Fluree. **Consequence, surfaced six rungs
   early:** `covenant-in-force-as-of` (rung 08, the flagship) exists to time-travel over
   this event. **Sent to `ccf_dataprep` and to the vault**, as an element the vault names
   that the estate cannot supply — which §11 asks for by name.
3. **The vault's parameter surface omits `debt_tolerance` and `as_of`.** Both are
   universal under Standard §2.4. Added here (§B.4), with `as_of` declared inert rather
   than silently absent. **Identical to rung 01's finding 2**; recorded again because it
   is now a pattern across two of two vault articles rather than a one-off.
4. **This product has no coverage manifest.** `validators/spec_coverage.py --product
   facility-terms-snapshot` reports `[UNMAP]`, **0 of 10 catalog rows accounted for** —
   no element it names has ever been asserted present by the validator that exists to
   assert exactly that. Every §C figure in this document is therefore evidenced by a
   query run for it. **This is the condition that hid rung 01's three gaps**, and it is
   named here before it can hide any of this product's. `ccf_dataprep`'s to close;
   §F.2 row 18.
5. **The vault's §C omits entitlement scope while its §B declares a Policy Binding and
   its §D runs a Policy Operator.** Added as §C.1 row 11 — an operator with no §C row
   has nothing to read. Authoring decision on this side of the ownership line, not a
   vault correction.
6. **The graph holds 45 `CreditFacility` instances against this store's 60 facilities.**
   The two populations do not agree. This product reads only the relational store so the
   discrepancy does not affect it, and reconciling them belongs to the first product that
   reads both (`corporate-family-tree`, rung 04). **Recorded rather than left for that
   rung to discover.**
7. **Rung 01's open data request at its §F.2 row 20 is answerable by this product.** It
   asked `ccf_dataprep` for a fifth principal whose grant set matches no entity, so that
   `CPR-G08`'s empty-served-set case would have an instance. **Two such principals
   already exist against facilities** (§D.3). The request is not withdrawn — rung 01's
   gate is over *entities*, not facilities, and the populations differ — but the cheapest
   discharge may now be a cross-reference rather than new data. **For Dave to scope**, not
   for this document to close.

   **NOTE, 2026-09-03 (Phase 24.5.1, `D-IMPL-245` (4), D-08).** Rung 01's row 20 is now
   answered by ruling rather than by data: `CPR-G08` REFUSES a principal whose grant
   matches no entity, with the same suppression-silent shape this specification's
   finding 9 established for facilities — one text through one function,
   indistinguishable from the nonexistent case. The data request itself is not
   withdrawn by this note; that is Dave's (`D-IMPL-227`).
8. **The canonical encoder refuses a float, and this is the SECOND document format it
   has been met from.** `src/ccf/contracts/canonical.py::_normalize` rejects a Python
   `float` — *"not bit-stable across platforms"* — and the first run of this example
   died inside `content_hash` while building the replay record, because
   `ccf_v2.facility.pricing_grid`'s leverage thresholds (`1.0`, `1.5`, `2.0`) arrive as
   floats from `json.loads`. Rung 01 met the same refusal from a **YAML** artifact
   carrying a bare `debt_tolerance: 0.25`. **Two formats, one refusal, and the fabric is
   right both times** — a content-addressed payload cannot carry a value whose bytes
   depend on the machine that serialized it. Bound with `parse_float=Decimal` and then
   rendered as text, because a `Decimal` survives the content address but not a client's
   `json.dumps`. **Recorded because every adopter carrying a JSON structure out of a
   store into a served payload will meet it on their first run**, and the error message
   names the fix without naming where to apply it.
9. **A suppressed facility and a nonexistent one were distinguishable, and the RUN found
   it — not the specification, which had it right all along.** §B.2 and §D.3 require a
   principal entitled to nothing to receive a refusal indistinguishable from the one for
   a facility that does not exist. The first build returned **`200` with
   `facility: null`** for the suppressed case and **raised `404`** for the missing one —
   so a caller probing facility ids could learn **which ids exist** by watching which
   came back null rather than refused. The payload carried no marker of what was
   withheld and **the status carried it instead**, which is the same disclosure arriving
   through a channel §B.2 did not name. Both now raise one shared refusal string through
   a single function, `assembler.py::_not_available`, so there is no second wording to
   drift. **The distinction is not lost — it moves to the audit plane**: the product is
   assembled, gated and its replay record written before the refusal, so the record
   holds which principal asked and that a facility existed and was withheld. The audit
   knows; the caller does not. Gate `FTS-G04` is the standing proof.
10. **`CP-SPEC-001` and `CP-SPEC-000` carry British spellings that the vault has now ruled
   against.** The vault's ruling of 2026-08-29 fixes Standard headings as `Failure
   behavior` and `Behavior when absent`. `CP-SPEC-001` diverges on three lines and its
   published page; `CP-SPEC-000` diverges on one. **`D-07` forbids retrofitting completed
   work**, and `CP-SPEC-001` is Gate-1 approved, so neither is edited here. **This
   document uses the ruled US spellings throughout.** Raised for Dave; not performed.

---

## Section G — Operate & govern

### G.1 The expiry obligation, restated where an operator will look for it

**This product's reason to exist is which event the expiry is measured from** (§A). An
operator reading only this section must still find it:

> `expires_at` is derived from the **agreement's own dated-as-of clause**, plus 90 days.
> It is **not** derived from when the question was asked, when the extraction ran, or
> when the review window closes. **If it moves when only the question moves, the product
> has failed**, whatever else it returned.

`contract.ttl_basis` and `contract.ttl_basis_value` are in the payload precisely so an
operator can check that arithmetic without reading this document (§D.6).

| Entry | Content |
|---|---|
| **Accountable owner** | product: Wholesale Lending · data steward: loan operations / agency · policy owner: identity and access — **roles, not individuals** |
| **Service objectives** | p50 / p95 assembly latency, volume, concurrency ceiling, payload bound, absolute per-call cost: `[TBC — this build, phase P6]`. The **instrument** is named with the number when it lands |
| **Degradation contract** | **Mandatory** (fail closed): `facility_id`, `facility_type`, `borrower_lei`, `currency`, `effective_date` → `404`; entitlement scope → `503`. **Non-mandatory** (serve with elevated `D_c` + notice): maturity date, tenor, commitment, pricing grid, balance, undrawn, rating, debt-reconciliation row |
| **Debt model** | §E.2. `debt_tolerance` default `0.25`, provisional |
| **Observability** | per-operator latency · `D_c` distribution · **gate-failure counts by gate, all nine** · cache hit rate · **entitlement denials, split by need-to-know and by jurisdiction** · **`ttl-bounds` refusal rate**, which is the instrument §F.4 finding 1 is settled against · supersession-triggered invalidations |
| **Retention & record of record** | The EX-10 filing is record of record for the public terms; the internal loan system for balance, availability and rating. **The fabric references them and does not replace them.** Replay-record retention tier: `[TBC — this build, phase P8]` |
| **Test fixtures** | `FTS-F01` counterfactual · `FTS-G01`…`FTS-G09` one per gate · `FTS-D01` degradation branch · `FTS-R01` replay hash assertion |
| **Lifecycle** | **`draft`** — Gate 1 authored 2026-08-29, reviewer **Dave, pending** |

### G.2 Acceptance criteria

Assertions specific to this product, each independently verifiable, **each phrased so
it can fail**.

1. **The expiry does not move with the question.** The same facility asked at two
   different instants returns the same `expires_at`, to the second. `FTS-F01`,
   `FTS-G01`. **This is the product.**
2. **The payload names which date the expiry was measured from.** `ttl_basis` and
   `ttl_basis_value` are present and the arithmetic checks. `FTS-G01`.
3. **The replay test produces a differing hash, a matching hash, and a matching hash at
   a later `asked_at`.** All three. `FTS-R01`. **A replay that cannot produce a differing
   hash is not demonstrating replay**, and one that cannot produce a *matching* hash at a
   later instant is not demonstrating this anchor.
4. **A facility whose maturity precedes its effective date serves both dates and refuses
   to compute a tenor.** `tenor_days` is null, the claim is `NOT_EVALUABLE`, and no
   negative number appears. `FTS-G08`.
5. **The pricing grid arrives as a tier list of at least three entries**, never as a
   scalar margin. `FTS-G07`.
6. **No document offset, accession or document identifier appears in the served payload
   or its lineage.** `FTS-G06`.
7. **Two principals receive different facility sets and cannot tell.** Content differs;
   structure is indistinguishable; no marker of withheld content. `FTS-G02` + `FTS-G04`.
8. **A principal entitled to nothing is refused indistinguishably from a request for a
   facility that does not exist.** `FTS-G04`.
9. **Removing the need-to-know condition changes the served set.** `FTS-G03`.
10. **`as_of` returns `400 not_supported_at_tier`** and never a silent success.
    `FTS-G05`.
11. **A facility older than the 90-day window is refused on `ttl-bounds`, naming its
    basis** — and the gate asserting it turns **red** when §F.4 finding 1 is settled.
    `FTS-G09`.
12. **Each of the nine gates has been observed RED at least once**, deliberately.

**Open decisions blocking build — named by their §F row:** **none.** Rows 1 and 2 are
the vault's and non-blocking: the product is admitted to the ladder with a stated
primitive, and the four-question result records *why* it qualifies rather than *whether*
it can be built. Every other marker is either `this build` or another agent's and
non-blocking. **The one that would become blocking at certification, not at build, is
row 6** — `debt_tolerance` cannot stop being provisional until it is measured.

### G.3 Catalog contribution

**What this product proves that no earlier product proved:**

- **An anchor that is not a legal entity.** A facility is an instrument with an internal
  identifier and no external registry, and §C.3 records what that costs at resolution.
- **`from_entity_freshness` computed from a date the source document carries** — and
  measured against the alternative, so the anchor is demonstrated rather than declared.
  §E.5 is the first section in this catalog to put two candidate bases side by side with
  the counts that separate them.
- **A materialization posture with a carve-out**, where the carve-out is what makes the
  posture expressible at all: a 540-day signal and a 1-day signal in one payload, with
  the split visible in the contract (§E.3).
- **A policy step with two conditions where only one would have passed the tests** — and
  a gate written specifically to prove the second condition does work (`FTS-G03`).
- **An empty served set with a live instance**, which rung 01 specified and could not
  demonstrate.
- **A structured value served as a structure** — the pricing grid as tiers, with the
  measurement that a naive read of it returns zero (§C.4 trap 4).

**What it deliberately does not prove:**

- **No projection.** Π is not exercised; `projection_plan_id` is null.
- **No traversal, no second time axis, no document passage, no similarity.** One
  capability class, `relational`.
- **No amendment history.** The count is served; no date is claimed. That is the tier
  boundary and the largest recorded finding (§F.4 finding 2).
- **No covenants, no collateral, no syndicate, no exposure rollup** — the scope boundary
  (§B.5), and the first things a credit reader will look for and not find.

---

## Gate 1 — status

**This specification is complete except for its `[TBC]` register at §F.2**, and is
submitted for approval per `spec_generation.md` §2.

**Nothing is implemented until Dave approves it.** At Gate 2 every
`[TBC — this build]` is cleared by a value the build measured, and **a Gate-2 value
that contradicts an approved Gate-1 decision is a deviation** — taken back for a
ruling, never absorbed silently.

**Two §11 returns are owed and are sent with this specification**, not held to Gate 2,
because both are terms the vault or `ccf_dataprep` owns and both affect what gets built:
**finding 1** — the declared anchor refuses 50 of 60, with the measurement — and
**finding 2** — the amendment effective date the vault's §C names and the estate does
not hold.
