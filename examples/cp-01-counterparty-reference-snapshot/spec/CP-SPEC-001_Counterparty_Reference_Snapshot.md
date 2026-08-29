# Counterparty Reference Snapshot — Context Product Specification

**CP-SPEC-001** · Authored to Specification Standard v0.3
(`public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`) ·
build order `cp-01`, the second rung built and the **first rung of the vault's
21-product ladder**.

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
> The surrounding data estate carries **deliberately engineered names and
> relationships**, and this product reads a mixture that the estate labels
> honestly: `ccf_v2.legal_entity` is **156 of 156 rows `provenance = 'public'`**,
> while `ccf_v2.internal_client` (30 rows), `ccf_v2.crosswalk` (83 rows) and
> `ccf_v2.principal_jurisdiction` (17 rows) are **`synthetic — internal`** —
> invented here because no public source can supply a bank's internal client
> master or its entitlement service.
>
> **No number here is a fact about any real company**, and no principal named
> below is a real person or a real role at any institution.
>
> The one place this matters most: the 30 no-LEI borrowers at §C.1 row 2 exist
> **to demonstrate an exclusion**, not to describe a book. Their names are
> invented. Their KYC dates are invented. What is real is the *shape* of the
> problem — that a large part of a Commercial Banking book has no LEI, and an
> LEI-only anchor drops it silently.
>
> The same statements are repeated beside each figure cluster below,
> deliberately, rather than left here as a header a reader scrolls past.

---

## 0 · What this document is

A specification of **one** Context Product — `reference.counterparty.v1` — written
to the v0.3 format contract, for a product requiring **one capability class**
(`relational`) across **three systems of record**.

> **This is an implementation specification, so it names the data concretely.** §C.1's
> system-of-record column carries the actual schema and table behind every element, and
> §F carries the measured readiness of each — a spec that cannot say where an element
> comes from cannot be built from.
>
> ### Which specification this is — the distinction that governs the rest
>
> **Ruled by Dave, 2026-08-29.** There are **two levels of Context Product
> specification**, and both are legitimately called `CP-SPEC-001`:
>
> | | **Vault level** | **SDK level — this document** |
> |---|---|---|
> | Document | `context-products/content/counterparty-reference-snapshot.md` | this file |
> | Answers | **what the product is** | **how it is built** |
> | Posture | **implementation-independent** | a **specific implementation artifact**, bound to one estate |
> | Names a database | **no — correctly** | **yes — necessarily** |
> | Owns | decision frame, counterfactual, four-question result, tier, build order, **scope boundary**, typing chain | §B.1 values, parameters, §D steps and witnesses, gates, §E posture, §G — and the merge |
>
> **Neither supersedes the other.** The vault answers a question this document does not
> ask, and the reverse. A reader treating them as rival drafts of one document — which
> is how this pair was first read — will spend their time adjudicating a conflict that
> does not exist.
>
> **This is why this document names its stores.** Standard §10.1 — *"product specs never
> name a database"* — is a rule for the **implementation-independent** level, and it is
> right there. Applied to an implementation artifact it makes the artifact useless:
> `ccf_v2.legal_entity` names a schema and a table, and in a **five-store** estate it
> does not say which engine holds them. Dave: *"If the database is unknown how can we
> even reference the tables?"* A table reference without its store is not a reference.
>
> **What stays out at both levels:** the **deployment** — host, port, credential,
> instance — which lives in `backends.yaml` as an environment-variable name and never in
> a specification of either kind.

**This spec is written BEFORE the assembly it specifies.** That is the point of it.
`24-CONTEXT.md` `D-01` rules that the Standard *"defines what needs to be implemented
in the SDK"* — a requirements source, not an authoring convention — and `D-03` that
these examples exist to **pressure test** the SDK. A spec written after the code
describes the SDK; written before it, it states what must be buildable and lets the
build find out whether it is. Where the SDK cannot express something this document
orders, the gap is **recorded and not closed** (`D-04`); closing it is a separate
phase.

**What this product is for, in one sentence.** Every other product in the vault's
21-product catalog resolves its anchor through this one and inherits its contract
machinery, its typing decisions and its identity authority hierarchy — so a defect
here is a defect everywhere, and that is why it is built first.

### 0.1 Do you need a Context Product? — the four-question test

The vault's answer, carried verbatim as the vault's term (`spec_generation.md` §1)
and **not re-adjudicated here**:

| # | Question | Answer |
|---|---|---|
| 1 | Does the answer change with who is asking, beyond formatting? | **No** — jurisdiction visibility only |
| 2 | Does it have a validity window after which acting on it is wrong? | **Yes** |
| 3 | Must it be reconstructible with the policy and freshness state that produced it? | **Yes** |
| 4 | Is it composed at runtime from sources no schema author pre-joined? | **Partial** — two sources, one join |

**Two clear yeses, one partial, one no — against a standard that says build only if
all four are yes.** The product is admitted as the catalog's contract-machinery entry
point rather than on its own assembly merit, and it qualifies on the TTL and the
replay obligation, not on the composition. That basis is written down so a reviewer
can challenge it, which is what the Standard asks of a qualified admission (§0.1).

**The catalog's flagship example is the one product that does not pass its own entry
test cleanly.** Stated plainly rather than smoothed, because a reader who discovers
it themselves will trust the rest of the document less.

**One SDK-side observation the vault could not make.** Question 1's *"No"* is what
makes this rung's Policy step worth scrutiny rather than a formality — see §D.3. The
answer does not change *in content* by principal, but **which entities exist at all**
does, and the Standard's suppression rule (§2.2) means that difference must be
invisible in the payload. A "No" on question 1 and a live entitlement filter are not
in tension; conflating them is how a Policy step becomes decorative.

### 0.2 Placeholder discipline

Every unresolved item carries `[TBC — <owner>]` and appears again at **§F.2** with a
named owner. Two owner classes appear in this document:

- `[TBC — this build, phase Pn]` — a value only the build can supply (a measured
  budget, a payload hash, a fixture result). Cleared at Gate 2.
- `[TBC — <agent>]` — a term belonging to another agent under `spec_generation.md`
  §1's ownership table. **Never guessed.** A guessed term is indistinguishable from
  an authoritative one once written down.

An unmarked assumption is the more serious defect, because a marked gap gets closed
and an invented one gets built.

### 0.3 Section skeleton

Seven sections, in order, per Standard §0.3. Sections carrying nothing still carry a
line saying why — an absent section reads as an oversight and a short one reads as a
decision. §B.3 is the instance here.

### 0.4 Front matter

| Field | Value |
|---|---|
| Registry name | `reference.counterparty.v1` |
| Tier | 1 |
| **Assembly Mode** | **1 — pure algorithmic** |
| Cost band | ×1 (the baseline) |
| Lifecycle state | **draft** — Gate 1 authored, not yet built |
| Accountable owner | product: Wholesale Reference Data · data steward: client/entity reference data · policy: identity and access |
| Last review | 2026-08-29 (this authoring) |
| What it resolves | A single counterparty to a typed, contract-bound identity snapshot. The minimum viable Context Product: its job is to prove the contract fires, not to demonstrate context assembly. |
| Four-question build test | Yes · Yes · No (qualified) · Partial — recorded basis at §0.1 |
| Build order | **First on the vault's ladder.** Every other product resolves its anchor through this one and inherits its contract machinery, typing decisions and identity authority hierarchy. |

**Capability gate: none.** This product requires only the `relational` capability
class and is deliverable against any estate that can serve a set-based query and an
entitlement lookup. It is the only product in the catalog with no capability risk,
which is a second reason to build it first: it proves the contract machinery before
any platform decision is contested.

---

## Section A — Decision frame

**Decision & trigger.** A relationship manager or credit officer opens a counterparty
record, and the agent needs a canonical identity before it can do anything else.
Every downstream product resolves through this one.

**Consuming principals.** Single role at this tier. Projection Π is **not exercised**
— that arrives at T5. The product returns the **same shape** to every authorized
caller.

> **The shape is constant; the population is not.** Four principals exist in the
> estate and each sees a different set of entities (§C.1 row 3, §D.3). That is
> entitlement scope, not projection: no principal receives a differently *assembled*
> product, and under the Standard's suppression rule (§2.2) no principal can tell
> that another sees more. A reader who takes "same shape to every caller" as "same
> rows to every caller" has misread the tier.

**Counterfactual failure — contract, not context.** Narrower than the rest of the
catalog, and worth stating precisely rather than inflating. **A CRM lookup returns
the same fields.** What it does not return is a **TTL**. The consumer therefore
caches the row indefinitely and continues reasoning against an entity whose GLEIF
registration status has since lapsed to `LAPSED` — meaning nobody has revalidated
that the entity still exists as described.

**The failure is not a missing signal; it is a missing expiry.** That is the entire
lesson of T1.

**Closed-taxonomy mode:** `temporally-incoherent`. The vault's counterfactual names
staleness-without-expiry, which is the temporal axis, not the context axis — the
fields are all present, and that is precisely the problem.

**Counterfactual acceptance test.** Serve the product, let the TTL expire, and assert
the consumer refuses the cached row.

| | |
|---|---|
| **Query** | `GET /context-products/reference/counterparty/{anchor}?intent=kyc-review` |
| **Answer A — a CRM lookup** | the same seven identity fields, no `expires_at`, no `context_debt` |
| **Answer B — this product** | the same seven fields **plus** `contract.expires_at`, `contract.ttl_anchor`, `lineage`, `context_debt` |
| **They must differ when** | the clock passes `expires_at`. A consumer holding A cannot know; a consumer holding B refuses. |
| **The test fails if** | the served product carries no `expires_at`, or carries one the consumer is not obliged to honour. Then B is A wearing more JSON. |

`[TBC — this build, phase P7]` — fixture `CPR-F01`, and the refusal it must produce.

**Primitive taught.** **The TTL and its anchor.** This is the product where `ttl_anchor:
from_entity_freshness` is introduced — the expiry is derived from *when the source
last spoke about the entity*, not from when the question was asked. Every later rung
inherits the choice or deliberately departs from it.

**Contrast pointer.** `cp-00-institutional-holders` anchors its TTL on a **reported
quarter end** — a fixed point in the source's own calendar — while this product
anchors on **entity freshness**, which moves per entity. Two products with different
anchors teach the anchor better than either does alone.

---

## Section B — Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Schema** | `counterparty_reference` — entity `LegalEntity`; attributes: LEI, legal name, jurisdiction, entity status, registration status, legal form, **headquarters address and legal address**. Machine-readable artifact: `[TBC — this build, phase P6]` at `docs/schemas/counterparty_reference.v1.json` |
| 2 | **Freshness SLA** | **Per signal class, never averaged.** 24 hours for LEI-registered entities; **KYC refresh cadence — months** for entities resolved through the internal client master. See §C.3 for why one number over a mixed population is the error the rule exists to prevent |
| 3 | **TTL** | **24 hours** · `ttl_anchor: from_entity_freshness`. **One TTL, per product** (Dave, 2026-08-29). A measured consequence for the no-LEI population is recorded below and is a BUILD finding, not a change to this declaration |
| 4 | **Policy Binding** | **Entitlement scope only** — jurisdiction visibility per calling principal. No regulatory overlay at this tier. Classification and residency at §B.2 |
| 5 | **Lineage** | `operators_invoked: [Resolve, Policy]` · `graph_snapshot_at` · `policy_version` · `payload_hash` · `context_debt`. `projection_plan_id` is **null** — Π is not exercised at T1. `model_record` is **null** — Mode 1 |
| 6 | **Semantic Version** | `v1.0.0`. No prior version; no migration window applies. Change classes per Standard §12 |
| 7 | **Discovery** | `reference.counterparty.v1` |
| 8 | **Addressability** | `/context-products/reference/counterparty/{anchor}` |
| 9 | **Assembly Mode** | **1 — pure algorithmic.** No model is invoked anywhere in the path, which is what makes exact replay possible and makes this the product the replay harness itself should be tested against |

**Mode 1 means §B.3 model-risk annotation does not apply.** That is a consequence of
the declaration, not an omission.

**Element 5 is stated as typed references, not bare names.** `spec_generation.md`
§10.2 records that the vault's own worked example listed `operators_invoked` as bare
strings, which cannot satisfy the **lineage strict equality** gate — that gate compares
the declared operator set against what the engine resolved, and a comparison needs
addresses on both sides. The SDK mechanism each name binds to is the eighth column of
§D.2.

> ### A MEASURED CONSEQUENCE OF ELEMENT 3, found at P5 before any code was written
>
> `from_entity_freshness` computes `expires_at` from **the entity's last observation**.
> For an entity resolved through the internal client master that observation is
> `kyc_last_refresh` — **months** old by design (§C.3's freshness ceiling of 180/270/365
> days). Measured against the live estate on 2026-08-29:
>
> ```
> refreshed 2026-01-07  ->  expires_at @24h = 2026-01-08   already past
> refreshed 2026-02-07  ->  expires_at @24h = 2026-02-08   already past
>
> no-LEI entities whose 24h-from-freshness TTL is already past : 30 of 30
> ...and how many are live under their OWN declared ceiling    : 27 of 30
> ```
>
> `src/ccf/products/gates.py::_refuse_ttl` requires `now < expires_at`. On these
> numbers **every one of the 30 no-LEI entities is refused on its first call** — the
> population §C.4 trap 2 exists to stop being excluded, and the one §G acceptance
> criterion 3 requires to *resolve and report the lower freshness ceiling*. The data is
> not at fault: 27 of 30 are live under their own ceiling.
>
> **THE DECLARATION IS NOT CHANGED HERE, AND THAT IS DELIBERATE.** TTL is per-product
> and this product's is 24 hours — Dave, 2026-08-29: *"it's specific to the product…
> specify the TTL for this product."* An earlier draft of this section invented a
> two-branch TTL structure in `artifacts/ttl.yaml`, keyed on `identity_authority`, with
> a per-entity duration read from `freshness_ceiling_days`. **That was withdrawn**: it
> extended the artifact schema with fields the SDK does not carry, ahead of the run that
> would have justified them.
>
> **How this resolves.** It is a **build finding**, taken back with evidence from an
> actual run per `spec_generation.md` §2 — *"a Gate-2 value that contradicts an approved
> Gate-1 decision is a deviation — take it back, do not absorb it"* — rather than
> pre-empted by machinery written before the evidence. Gate **`CPR-G09`** is what
> settles it, in whichever direction the run settles it. Registered at §F.4 finding 8.

**Element 3, and the two ways this product can hit its TTL bound.** `from_entity_freshness`
means `expires_at` is computed from the entity's own last-observed instant, so:

- An entity the vendor file refreshed this morning expires 24 hours from *that*
  observation, not 24 hours from the request.
- An entity resolved through the internal client master has a freshness ceiling of
  **months**, so a 24-hour TTL over it would advertise a currency the source cannot
  support. §C.3's hierarchy is what prevents that, and §D.7 gate `CPR-G03` is what
  proves it.

### B.2 Classification and residency

| Field | Value |
|---|---|
| **Data classification** | `internal` — the highest classification of any element in §C.1. The GLEIF-sourced identity attributes are `public`; the internal client identity, the crosswalk and the entitlement scope are `internal`. **No `confidential` or `restricted` element is in scope** — the KYC *state* that would be confidential is deliberately out of §C.1 (see §B.5) |
| **Information barrier** | `none`. No MNPI, no control-room restriction at this tier |
| **Residency constraints** | `[TBC — identity and access]` — no jurisdiction is currently declared as non-exportable. The estate holds entities across 12+ jurisdictions (§C.1) and a residency rule would bind here rather than at §D |
| **Cross-border serving** | `[TBC — identity and access]`. The entitlement scope of §C.1 row 3 constrains **which entities a principal sees**; it does not currently express **where a principal may be** when they see them. Those are different questions and only the first is implemented |

**The suppression rule, and it is load-bearing here.** Where policy excludes content,
the payload carries **no count, no marker and no placeholder** indicating that anything
was withheld. This product's entitlement filter removes entities from the visible set
per principal (§D.3); a `"3 entities not shown"` notice would disclose the existence of
what the filter exists to hide. Restricted content is **never materialized and then
filtered** — the ordering at §D.2 is what makes that structural rather than
conventional. Proven by gate `CPR-G04`.

### B.3 Model-risk annotation — Mode 2 and Mode 3 only

**Not applicable — no model in the trust path.** This product is Assembly Mode 1 and
invokes no LLM at any step. This section exists because Standard §0.3 requires a
section with nothing to say to carry one line explaining why, rather than being
omitted: an absent heading reads as an oversight, a short one reads as a decision.

### B.4 Request parameter surface

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `anchor` | `string(20)` LEI **or** internal client id, required | **E** — anchor. See §C.3 identity authority | — |
| `intent` | enum, required | **P** — selects the policy envelope | — |
| `debt_tolerance` | float, required | **P** — the ceiling above which assembly refuses | `0.25` `[TBC — this build, phase P8]` |
| `include_lapsed` | bool | filter | `false` |
| `as_of` | timestamp | **T** — reconstruction | **declared-but-inert at this tier** |

**Required on every product** per Standard §2.4: an anchor identifier, `intent`, and
`debt_tolerance`. The vault's article omits the last two; they are **added here rather
than treated as an oversight**, because §2.4 states them as universal and a product
that silently drops `debt_tolerance` has no way to express the debt gate at §D.7.

**`as_of` is declared-but-inert and must fail loudly.** It is part of the uniform
parameter surface, and this tier does not support historical reconstruction — the
`Resolve` step reads current state. It therefore returns
**`400 not_supported_at_tier`**, and **never silently succeeds against current
state**. *"A parameter that appears to work and does not will be relied on in a
dispute"* (Standard §2.4). Proven by gate `CPR-G05`.

**`debt_tolerance` default 0.25 is provisional and unbacked.** It is carried from the
vault's §E and stays provisional until measured against crosswalk match confidence —
§F.2 registers it, and Standard §13 makes measuring it a condition of certification,
not of build.

### B.5 Prerequisites, consumers and scope boundary

**Prerequisites.** None. This is the entry point of the ladder.

**Consumers.** **Every other product in the vault's catalog** — all 20 remaining
products resolve their anchor through this one. Named first-order consumers, from the
vault article: `corporate-family-tree`, `kyc-refresh-beneficial-ownership`.

> A reverse dependency list this broad has a consequence Standard §5.4 makes explicit:
> a **MAJOR** version change here requires notifying the entire catalog, and a
> supersession cascade from this product reaches every product whose
> `operators_invoked` touched the superseded entity — not only the two named above.

**Scope boundary — the vault's term, verbatim.**

> **"identity only — no exposure, no grade, no relationship."**

**Deliberately out of scope, and which product carries each:**

| A reader will expect | It is not here | It is in |
|---|---|---|
| Internal obligor risk grade | excluded by the scope boundary above | a credit-tier product, not yet specified |
| Coverage assignment (RM, team, LOB) | excluded by the scope boundary above | a coverage/CRM product, not yet specified |
| Ownership and parentage | "no relationship" | `corporate-family-tree` |
| KYC verification *state* | the freshness *ceiling* it implies is in scope (§C.3); the state itself is not | `kyc-refresh-beneficial-ownership` |
| Exposure and limits | excluded by the scope boundary above | `credit-exposure-rollup` |

> **This scope was contested, and the resolution is recorded rather than assumed.**
> An exemplar of this spec placed at
> `public/reference/specifications/CP-SPEC-001_Counterparty_Reference_Snapshot.md`
> declares `internal_risk_grade`, `coverage_rm_id`, `coverage_team` and `coverage_lob`
> in its payload. **That exemplar is a control for comparison, not an authority**
> (`spec_generation.md` §7.1, §10.1). Scope boundary is the **vault's** term under the
> §1 ownership table, and the vault excludes grade. `ccf_dataprep` built to the vault's
> reading and carries none of those fields.
>
> **The arithmetic consequence, stated because it is the interesting half.** Under the
> exemplar's own per-component debt table the absent overlay contributes **0.30 `D_c`**
> against a **0.25 `debt_tolerance`** — the debt gate fires and the product returns
> `409` rather than serving. Under this specification the overlay is **not a debt
> component at all**, so the collision does not arise. A field that is out of scope
> contributes no debt; a field that is in scope and missing contributes all of it.
> That is the difference between a scope decision and a data gap, and §E.2 is where it
> is enforced.

---

## Section C — Data catalog

> **Every figure in this section was measured against the live estate on
> 2026-08-29 by a read-only query, not read off a report.** Where a term belongs
> to `ccf_dataprep` under `spec_generation.md` §1's ownership table — system of
> record, provenance class, classification, capability class, `G` dimension,
> **ontology IRI** — and is not established, it is `[TBC — ccf_dataprep]` and
> **not guessed**.

### C.1 Element table

One row per element, not per column. **The system of record names the store, the
schema and the table** — Dave's ruling of 2026-08-29 (§0), because this is the
implementation specification for a build against a real estate. *"If the database is
unknown how can we even reference the tables?"*

| # | Element | System of record | Provenance class | Classification | Capability class | `G` | Ontology IRI |
|---|---|---|---|---|---|---|---|
| 1 | LEI, legal name, jurisdiction, entity status, registration status, legal form, **headquarters and legal address** | GLEIF LEI-CDF Level 1 → **PostgreSQL** `ccf_v2.legal_entity` | `vendor` | `public` | `relational` | **E** | seven-class chain — see §C.3 |
| 2 | Legal name, jurisdiction and identity for **no-LEI entities** | Internal client master → **PostgreSQL** `ccf_v2.internal_client` | `internal-SOR` | `internal` | `relational` | **E** | `cmns-org:LegalEntity` + chain |
| 3 | **Entitlement scope by jurisdiction** | Entitlement service → **PostgreSQL** `ccf_v2.principal`, `ccf_v2.principal_jurisdiction` | `internal-SOR` | `internal` | `relational` | **P** | `[TBC — ccf_dataprep]` |
| 4 | LEI ↔ internal client **crosswalk** | Internal mapping → **PostgreSQL** `ccf_v2.crosswalk` | `internal-SOR` | `internal` | `relational` | **E** | `[TBC — ccf_dataprep]` |

> **Three levels of specificity, and this is an SDK-level document (§0).**
>
> | Level | Example | In this spec? |
> |---|---|---|
> | **Capability class** — what the store must be able to do | `relational` | yes, its own column, per §3.1 |
> | **Store, schema and table** — where the element actually is | **PostgreSQL** `ccf_v2.legal_entity` | **yes**, above — Dave's ruling, §0 |
> | **Deployment** — host, port, credential, instance | — | **never.** `backends.yaml`, as an env-var name |
>
> The middle row is what makes this an SDK-level artifact rather than a vault-level one.
> At the vault level it is correctly absent; here its absence would leave a developer
> holding `ccf_v2.legal_entity` in a five-store estate with no way to tell whether it is
> the relational store, the graph ledger, the document store or the departmental file.
>
> **Whose term this is.** `spec_generation.md` §1 assigns §C element rows — system of
> record, provenance class, classification, capability class, `G`, ontology IRI — to
> **`ccf_dataprep`**, not to the vault. So the vault article's `Store` column is outside
> the authority of the document carrying it; and the *rule* it follows, Standard §10.1,
> is correct at the level that document occupies. **Nothing here is a correction owed
> upstream** — see §F.4 finding 7.

**Provenance and classification, measured rather than asserted:**

| Table | Rows | `provenance` | Note |
|---|---|---|---|
| `legal_entity` | **156** | `public` — 156 of 156, one distinct value | the vendor identity spine |
| `internal_client` | **30** | `synthetic — internal` — 30 of 30 | `source` reads *"internal client master (invented: public sources cannot supply a no-LEI entity)"* |
| `crosswalk` | **83** | `synthetic — internal` — 83 of 83 | 53 carry a LEI; **30 carry `lei IS NULL`** |
| `principal_jurisdiction` | **17** | `synthetic — internal` — 17 of 17 | one row per `(principal, jurisdiction prefix)` |

**No number above is a fact about any real company, and the 30 no-LEI borrowers are
invented to demonstrate an exclusion.**

### C.2 Capability decomposition

This product requires only `relational`, and Standard §3.2 asks for the decomposition
anyway — an estate rarely fails a capability wholesale, and the partial is the finding
worth having.

| Property | Common estate answer | This estate | If absent |
|---|---|---|---|
| Set-based query over structured records | widely available | satisfied | **blocking** — nothing about this product survives |
| **Predicate join across two identity authorities** on a nullable key | sometimes | satisfied — `crosswalk` PK is `internal_client_id`, `lei` nullable and `UNIQUE` | **degrades to LEI-only**, which silently drops the no-LEI population — the exact §C.3 failure |
| **Prefix match** of a principal's scope against an entity jurisdiction | sometimes | satisfied — `legal_jurisdiction` `US-DE` matches prefix `US` | degrades to exact-match, collapsing `US-DE`/`US-MD`/`US-NV` out of a `US` grant |
| Nullable-key uniqueness (many NULLs under one `UNIQUE`) | rare, and dialect-specific | satisfied | **blocking for row 2** — without it, one no-LEI client is the maximum |

**The fourth property is the one to notice, and it is not portable.** `crosswalk`
carries `UNIQUE(lei)` while holding 30 rows with `lei IS NULL`. That works because
this dialect treats NULLs as distinct under a unique constraint. An estate whose
engine treats NULLs as equal admits **exactly one** no-LEI client and reports success
— a capability failure that presents as a data shortage. **Interim posture if absent:**
serve LEI-registered entities only, ship as `v1.0.0-partial`, and return
`not_supported_at_tier` for an internal-client anchor rather than a `404` that reads
as "no such company."

### C.3 Correlation key, single-writer discipline, and identity authority

**Correlation key.** LEI spans every external element; `internal_client_id` keys the
bank-side overlay. **The crosswalk is the product** — nothing joins without it, and
its coverage and match confidence bound the correctness of every downstream product.

**Measured coverage, 2026-08-29:** `crosswalk` holds **83** rows — **53** carrying
`lei` + `internal_client_id` + `cik` together, and **30** carrying
`internal_client_id` with `lei IS NULL`. Every one of the 30 resolves to a row in
`internal_client`; **zero are orphaned**. **Match *confidence* is
`[TBC — ccf_dataprep]`** — coverage is a count and confidence is a measurement, and
this document will not report the first as though it were the second.

**Single-writer discipline.** LEI reference data writes external identity attributes;
the internal client master writes no-LEI identity and KYC state. **No element is
written by two systems.** The credit system writes grade — and grade is out of scope
here (§B.5), so no element of this product has a contested writer.

**Identity authority hierarchy — the Tier 1 design decision.**

Anchoring exclusively on LEI works for CIB counterparties and public Commercial
Banking obligors. **It does not work for the privately-held middle-market borrowers
who make up a large share of the Commercial Banking book and have no LEI at all. An
LEI-only anchor silently excludes them, and every downstream product inherits the
exclusion.**

| Entity class | Identity authority | Registration status source | Freshness ceiling | In this estate |
|---|---|---|---|---|
| LEI-registered (public, most CIB) | LEI reference data | vendor registration status and renewal date | **24 hours** | 156 in `legal_entity` |
| Private, no LEI | internal client master | internal KYC verification state | **KYC refresh cadence — months** | 30 in `internal_client` |
| Foreign private | internal client master + local registry where available | internal KYC verification state | **months** | included in the 30; not separately counted `[TBC — ccf_dataprep]` |

An entity resolved through rows two or three carries a **materially lower ceiling on
`F`**, and that asymmetry is **stated in the payload** rather than averaged into a
single freshness claim. A single "24 hours" over a mixed population is the exact error
the Standard's per-signal-class rule exists to prevent. The estate supports the claim:
`internal_client` carries `freshness_ceiling_days` at **180, 270 and 365** against the
vendor spine's 1. Proven by gate `CPR-G03`.

**Ontology typing — decided here and inherited catalog-wide.** `LegalEntity` is **not
a FIBO term**; it moved to the OMG Commons Ontology Library. Under a no-inference
store an entity is reachable only by the classes it is explicitly typed as, so every
party entity carries **all seven**:

`cmns-pts:Agent` · `cmns-pts:Party` · `cmns-org:Organization` ·
`cmns-org:FormalOrganization` · `cmns-org:LegalPerson` · `cmns-org:LegalEntity` ·
`fibo-be-le-cb:Corporation`

Source: the vault's `fibo-iri-binding` mirror, remediation decided 2026-08-17. **A
validator asserting that every type IRI begins with the FIBO namespace will reject
correct data.** Because every product in the catalog resolves its typing through this
one, a partial chain here propagates catalog-wide. Proven by gate `CPR-G06`.

### C.4 The traps — what the data does not support cleanly

Three, each with the binding chosen and what it costs. Standard §3.2's *"the partial
is the finding worth having."*

**Trap 1 — the address that did not say which address it was.**

§B names **two** addresses: headquarters and legal. Until 2026-08-28 the estate held
**one** triple, `address_country/_city/_region`, **with nothing recording which of the
two it was.** That ambiguity was the worse half of the defect: *a missing address
returns nothing and the consumer notices, while an unlabelled one returns Wilmington,
Delaware for a company run from Whippany, New Jersey.*

**Binding chosen:** the existing triple was renamed `legal_address_*` — which is what
it always was — and `hq_address_*` was added and loaded. **Measured 2026-08-29:** 153
of 156 entities carry both. **65 of 153 name a genuinely different place**, measured
with case and whitespace normalised.

**What it costs, and the measurement discipline it forced.** A raw string comparison
reports **69**, but **4 of those differ only in case** — `AMPHENOL CORP /DE/` carries
`WILMINGTON` against `Wilmington` in the same region — and are **one address typed
twice, not two addresses**. A distinguishability assertion written on raw inequality
scores those four as two addresses. The three entities without a headquarters address
are the synthetic ABS deal trusts; **the exclusion is derived from the LEI form rather
than from a list**, so a fourth is excluded automatically and a real LEI can never be
excluded by a stale list.

**Trap 2 — zero no-LEI entities, and the check that could not see it.**

The spec's own §C counterfactual — *"an LEI-only anchor silently excludes
privately-held middle-market borrowers"* — was **realised in the estate**:
`legal_entity` held **0 of 156** rows with a null LEI. The predecessor manifest marked
this element `COVERED`, **against crosswalk floors every one of which is an inner join
on `lei`** — structurally incapable of reporting the absence of entities that have
none, and reading a healthy 50 throughout.

**Binding chosen:** a **separate `internal_client` table**, not a nullable
`legal_entity.lei`. That column is the **primary key** with **nine** foreign keys on
it, so making it nullable is not a blast radius but a structural impossibility; and
§C's single-writer paragraph names the internal client master as a **different
authority**, so a separate table is what the discipline already implied. `lei IS NULL`
with **no `SYN-` placeholder** — a placeholder would resolve like a real anchor and
defeat §G's acceptance criterion.

**What it costs.** Two identity authorities means two resolution paths in `Resolve`
(§D.3) and two freshness ceilings in the payload. The alternative — one table, one
path — is what produced the exclusion.

**Trap 3 — the entitlement scope that had nothing to filter on.**

`principal` carried `side`, `perspective`, `sees_mnpi`, `sees_need_to_know`,
`sees_eu_person_data` — and **no jurisdiction at all**. So a count of principals
cleared any floor while the condition §B actually binds — *jurisdiction visibility per
calling principal* — **was not satisfiable by any query**, and the Policy Operator had
nothing to filter on.

**Binding chosen:** `principal_jurisdiction`, one row per `(principal, prefix)`, with
the filter applied as a **prefix match** so a `US` grant reaches `US-DE`, `US-MD` and
`US-NV`.

**What it costs, and the measurement it forced.** The obvious check — *do principals
have distinct visible-set sizes?* — **is wrong here**, and the estate proves it:
`PRIN-KYC-004` and `PRIN-TRD-003` each see **21** entities and **share none of them**.
Four distinct views, three distinct sizes. A gate comparing counts reports 3 and
passes a no-op. §D.7's `CPR-G02` therefore compares **sets**, and carries a negative
control.

> **The method these three traps share, and it belongs in the spec rather than in a
> post-mortem: a check whose population is not its question.** Each of the three was
> at some point measured by something that ran clean and answered something nobody
> asked — column presence read as element satisfaction; an LEI-keyed join asked
> whether entities without an LEI exist; a cardinality asked whether two sets differ.
> **Bound is not the same as materialized.** Later rungs will hit this again, so it is
> stated here as a stated method, not as history.

---

## Section D — Assembly recipe

### D.1 Client call

```
GET /context-products/reference/counterparty/5493001KJTIIGC8Y1R12
      ?intent=kyc-review&include_lapsed=false&debt_tolerance=0.25
```

The **forensic** case is not available at this tier: `as_of` is declared-but-inert
(§B.4), so the live call is the only one, and the `as_of` variant is shown at §D.7 as
the input to gate `CPR-G05` rather than as a client call.

### D.2 Operator step table

Numbered, **one operator per step**, with the Standard's seven columns and an
**eighth the Standard does not require: the SDK mechanism, named with its layer** —
following `CP-SPEC-000`'s precedent, so a name that differs between the Standard's
closed vocabulary and the SDK's four operator categories reads as a **mapping**
rather than as a gap in either direction.

| # | Operator | Capability class | Inputs | Emits (as it appears in lineage) | Failure behavior | p95 budget | **SDK mechanism (layer)** |
|---|---|---|---|---|---|---|---|
| 1 | **Resolve** | `relational` | `anchor` — an LEI **or** an internal client id | `entity_id`, the canonical attribute set, and **`identity_authority`** naming which of the two authorities resolved it | fail closed → **404**. An anchor resolving to nothing is never an empty payload. Crosswalk collision → **409** | `[TBC — this build, P6]` | `src/ccf/assembly/worker.py::SpecDrivenEntityResolution` under `::AssemblyWorker`, driven by `::EntityResolutionSpec` — **L2**, the single writer |
| 2 | **Policy** | `relational` | the assembled view; the principal's `principal_jurisdiction` grant set | `policy_version`, and the **principal-permissible subgraph substituted for the full graph** | fail closed → **403**, with no detail on what exists. Entitlement source unreachable → **503**, never a permissive default | `[TBC — this build, P6]` | `src/ccf/operators/categories.py::PolicyFilter` — **L4** |
| 3 | *contract assembly* — **not an operator** (Standard §10.2 retires `Compose`) | `in-memory` | outputs of 1–2, the declared lineage, the declared TTL and its anchor | the served `src/ccf/products/contract.py::ContextProductContract`, held inside a `ServableProduct`; `payload_hash`; `context_debt` | fail closed → **503** on any gate refusal, returned **as data** and never as a 200 with a warning. **409 is reserved for the debt gate** | `[TBC — this build, P6]` | `src/ccf/products/gates.py::run_gates` → `::ServableProduct` — **L6** |

**Budget total: `[TBC — this build, phase P6]` against a declared p95 envelope of
`[TBC — this build, phase P6]`.**

**Three things about those placeholders, and the third is the one that matters.**

1. **The Standard fixes no numeric latency envelope for Tier 1.** §13 gives cost
   *bands* (`×1` baseline) and §7 asks each product to publish its own p50/p95. Any
   envelope here is therefore **declared by this spec**, and recording that the
   Standard does not supply one is more useful than quoting a number it does not
   contain.
2. **A budget authored before a run is a design target, not a measurement.** Standard
   §5.1's discipline for `λ_c` — *"a value an engineer can challenge"* rather than one
   they assume was measured — applies to budgets identically. Rather than author three
   numbers that would be indistinguishable from measurements once written down, they
   are `[TBC — this build]` and registered at §F.2.
3. **Step 2 is the only realistic optimisation target and it must not be cached across
   principals.** `Policy` is per-principal by construction; a cache keyed without the
   principal returns one principal's visible set to another, which is a correctness
   defect that presents as an intermittent one (Standard §5.3). The cache key is stated
   at §E.3.

### D.3 Step detail

**Step 1 — `Resolve` carries two authorities, and which one answered is part of the
payload.**

The anchor is an LEI **or** an internal client id (§B.4), and the two resolve through
different tables to different freshness ceilings (§C.3). The step therefore emits
`identity_authority` **per resolution**, not as a product-level constant: a payload
that resolved through the internal client master and advertises the 24-hour vendor SLA
is making a currency claim its source cannot support. **Every identity attribute names
its authoring source** — an attribute with no authority is a defect, not a default
(gate `CPR-G07`).

**Crosswalk collision is a `409`, not a pick.** One LEI resolves to at most one
internal client id and vice versa. A many-to-one collision means merged entities or a
bad match; the step **fails closed rather than choosing one**, because choosing one
silently is how a wrong identity propagates to all 20 downstream products.

**Step 2 — Policy runs first, and at this tier it is load-bearing rather than
decorative.**

The Standard's recurring discipline is that *"Policy that appears to do nothing still
runs first"* — at Tier 1 the step is an entitlement check; at Tier 5 the same step is
what makes a restricted edge structurally absent, and the ordering is learned from the
first product or retrofitted painfully later.

**This rung is the test of whether that discipline is real, and the estate now
supports it.** Measured 2026-08-29 as **visible-set inequality**, not as column
presence:

| Principal | Grant set | Entities visible (of 156) |
|---|---|---|
| `PRIN-RES-002` research analyst | `US`, `CA`, `GB` | **102** |
| `PRIN-COV-001` coverage banker | `US` | **74** |
| `PRIN-KYC-004` EU KYC analyst | `AT BE DE ES HU IT LU NL SE` | **21** |
| `PRIN-TRD-003` trader | `GB HK JP SG` | **21** |

**All six pairs discriminate.** Two details a pass/fail verdict would have hidden, and
both justify the shape of gate `CPR-G02`:

- **`PRIN-COV-001` is a strict subset of `PRIN-RES-002`** — `|A\B| = 0`, `|B\A| = 28`.
  Containment, not disjointness. A gate demanding mutual exclusion would fail correct
  data.
- **`PRIN-KYC-004` and `PRIN-TRD-003` both see 21, and share none of them.** A
  cardinality comparison calls them equal. **Four distinct views, three distinct
  sizes.**

**The suppression rule is what makes the ordering structural.** Entities outside the
principal's grant set are **never materialized and then filtered** — the permissible
subgraph is substituted *for* the full graph, so there is nothing to leak a count
from. The payload carries no marker of what was withheld (§B.2), and gate `CPR-G04`
proves it by asserting that two principals' payloads differ in **content** and are
**indistinguishable in structure**.

> **A design finding, recorded rather than footnoted.** Until 2026-08-28 this step had
> nothing to filter on, and a rung 01 shipping that way would have put a decorative
> Policy step into the one example every later product inherits its shape from. The
> gap is closed and the step is demonstrably load-bearing — but the near-miss is why
> `CPR-G02` carries a **negative control**: a principal differenced against itself must
> report identical, so a `DISCRIMINATES` verdict is known to be capable of reading the
> other way. A gate that has never been seen to fail is not evidence.

**Step 3 — contract assembly is not an operator, and holding the product is the
evidence the gates ran.**

Standard §10.2 retires `Compose`; contract assembly is the terminal step and names no
operator. `ServableProduct` is not constructible outside `run_gates`, so **holding one
is itself the evidence** that the shipped gates executed — structural rather than
conventional. `[TBC — this build, phase P7]` confirms the mechanism holds for this
product.

**The four composition invariants (Standard §10.3), each stated against this
composition rather than asserted generally:**

| Invariant | Holds here because |
|---|---|
| **Policy before anything that reads graph state** | `Policy` is step 2 of 3, and step 3 is contract assembly — nothing reads graph state after it. Impermissible content is **never materialized and then filtered**; the permissible subgraph is substituted for the full graph (§D.3) |
| **Resolve before Traversal** | vacuously — **there is no Traversal step.** Stated rather than skipped: the invariant is about anchoring, and this product's `Resolve` is step 1, so any later rung that adds traversal over this anchor inherits a correct ordering |
| **Enrich is batched, always** | vacuously — **there is no Enrich step.** One query per source per step is satisfied trivially by a composition with one read per source |
| **Algorithmic substrate before any semantic stage** | vacuously and permanently — **Assembly Mode 1.** No LLM is invoked anywhere in the path, so there is no semantic stage to order. The substrate is the artifact-of-record and there is nothing else |

**Three of the four hold vacuously, and that is worth saying out loud rather than
ticking.** A reviewer who sees four checkmarks on a three-step Mode 1 product should
be suspicious; what makes them meaningful here is the **first** one, which is the only
invariant this composition can actually violate — and §D.2's ordering is what prevents
it.

### D.4 Determinism class and payload hash

**Determinism class: `deterministic`.** Same `anchor` + `policy_version` + graph
snapshot → **byte-identical payload**. Mode 1, no model anywhere in the path.

The hash is taken over the deterministic portion, **excluding `assembled_at`**.
Replay asserts **hash equality, not similarity**.

**Two inputs that must be inside the hash and one that must not:**

| Input | In the hash? | Why |
|---|---|---|
| the resolved entity's attributes at `graph_snapshot_at` | **yes** | it is the payload |
| `policy_version` **and the principal** | **yes** | two principals legitimately receive different payloads for the same anchor; a hash blind to the principal would report drift where there is none, or agreement where there is not |
| `assembled_at` | **no** | it changes on every call and would make every hash unique, which is the same as having no hash |

`payload_hash` value: `[TBC — this build, phase P6]`.

### D.5 Replay statement and replay test

**Replay statement.** The engine re-reads the entity at `graph_snapshot_at`, reloads
`policy_version`, re-runs `Resolve` and `Policy`, and **asserts hash equality**. No
model is invoked, so reproduction is exact. *"A similar product"* is a defect recorded
at §G, not a caveat.

**Falsifiable replay test.** A numbered procedure ending in an assertion that can fail:

1. Serve the product for a known anchor. Record `graph_snapshot_at` and `payload_hash`.
2. Land a change to that entity's `registration_status` in the source.
3. **Re-derive live.** The new status returns and the hash **differs**.
4. **Re-derive at the recorded `graph_snapshot_at`.** The original payload returns and
   the hash **matches**.

**If step 4 returns the new value, the snapshot is not load-bearing and
`graph_snapshot_at` is decorative.** A replay that cannot produce a differing hash is
not demonstrating replay — step 3 is as much a part of the test as step 4.

`[TBC — this build, phase P6]` — fixture `CPR-R01`, both hashes.

**One honest limit on this test at this tier.** `as_of` is inert (§B.4), so the
product carries **one** time axis, not two. The Standard's *"two filters on two axes
are two filters"* discipline has nothing to bite on here — there is no separate
observed-time axis to disagree with valid time. That is a tier property, not an
omission, and the first product carrying both is where the second test belongs.

### D.6 Emitted contract

The Standard's response envelope (§8 — cited as §10 in the Standard's own text; the
document's cross-references are stale in six places and resolve **by heading**),
populated with this product's payload schema, **with types**. This is what the
consuming agent team codes against and what CI validates. *Prose describing a payload
is not a payload.*

```jsonc
{
  "product": "reference.counterparty",              // string
  "semantic_version": "1.0.0",                      // string
  "payload": {
    "anchor":              "string",                // as supplied: LEI(20) or internal client id
    "entity_id":           "string",                // canonical URI
    "identity_authority":  "lei-reference-data" |   // WHICH authority resolved this entity
                           "internal-client-master",
    "legal_name":          "string",
    "legal_jurisdiction":  "string",                // ISO 3166-1/-2, e.g. "US-DE"
    "entity_status":       "string | null",         // null for internal-client-master resolutions
    "registration_status": "string | null",         // null for internal-client-master resolutions
    "legal_form":          "string | null",
    "legal_address":       { "country": "string", "city": "string|null", "region": "string|null" },
    "headquarters_address":{ "country": "string", "city": "string|null", "region": "string|null" },
    "type_chain":          ["string", "…"]          // the seven IRIs of §C.3, in order
  },
  "contract": {
    "assembled_at":     "iso8601",
    "expires_at":       "iso8601",
    "ttl_anchor":       "from_entity_freshness",
    "ttl_basis":        "string",                   // which observation the expiry was derived from
    "assembly_mode":    1,
    "determinism_class":"deterministic",
    "freshness": [
      { "signal_class": "vendor-identity" | "internal-kyc",
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

**Four things this shape commits to, each of which a reviewer can check:**

1. **`identity_authority` is in the payload, not the lineage.** It is a fact *about the
   answer* — which authority resolved this entity, and therefore which freshness
   ceiling applies — not a fact about how the assembly ran. A consumer must be able to
   branch on it without parsing lineage.
2. **`entity_status` and `registration_status` are nullable, and only for one
   authority.** GLEIF publishes them; an internal client master does not. A non-null
   default here would manufacture a registration status for an entity that has no
   registrar — worse than a null, because it looks answered.
3. **`headquarters_address` and `legal_address` are separate typed objects.** §C.4
   trap 1 is why: one unlabelled triple is what this shape exists to make impossible.
4. **`payload` is never returned without `contract`, `lineage` and `context_debt`.**
   *"A consumer that receives context with no debt signal cannot know what it is
   trusting."*

**`extra=forbid` is enforced as a build-time CI invariant.** A per-product subclass may
not silently add a field the base did not declare, and a pull request introducing a
drifted contract fails before it reaches a deployment surface.
`[TBC — this build, phase P6]` — the schema artifact and its CI binding.

### D.7 Validation gates

**The Standard names six universal gates. This SDK ships THREE** inside
`src/ccf/products/gates.py::run_gates`, and **`D-IMPL-102` limb 3 rules that no fourth
joins them.** What follows is what each of the six actually is here. **Nothing below
claims the SDK runs a gate it does not run** — a spec that implied otherwise would be
drift arriving from the specification side.

**The three that are shipped gates, in `run_gates`' own order:**

| # | Gate | SDK mechanism | What it refuses here |
|---|---|---|---|
| 1 | Empty-operator guard | `gates.py::_refuse_empty_operators` (INV-CH7-46) | a product whose `lineage.operators_invoked` is **empty** — a product computed by nothing |
| 2 | Lineage strict equality | the `declared != engine_resolved` comparison in `run_gates`, returning `::LineageMismatchRefusal` (INV-CH7-47) | any difference, **in either direction**, between `[Resolve, Policy]` as declared at §B.1 and the set the engine resolved |
| 3 | TTL bounds | `gates.py::_refuse_ttl` against the class's pinned `MAX_TTL` | `expires_at` outside `now < expires_at <= now + MAX_TTL` — see §B.1 element 3 for the two ways this product reaches it |

**The other three, each as it actually stands:**

- **Debt gate.** A **Control Plane posture**, not a shipped gate. `debt_tolerance` is a
  request parameter (§B.4) and the refusal is raised by the deployment, returning
  **`409` with the debt block** — *not* a `200` with a warning. `[TBC — this build,
  phase P7]`.
- **Suppression silence.** Not a shipped gate; realised **structurally** by the step
  ordering at §D.2 — the permissible subgraph is substituted for the full graph, so
  there is no withheld set to leak a count from. Proven by product-specific gate
  `CPR-G04` rather than asserted.
- **Classification containment.** Not a shipped gate. This product's declared
  classification is `internal` (§B.2) and **no `confidential` or `restricted` element
  is in scope**, so there is nothing above the ceiling that could appear. That is a
  consequence of the scope boundary (§B.5), and it is the reason this gate is cheap
  here and expensive at T5.

> **Gate 1 is not the Standard's gate 1, and the difference costs this product a gate
> of its own.** The Standard's empty-operator guard is *"no operator returns an empty
> set silently; empty is fail-closed or an explicit debt contribution."* The SDK's
> refuses a product that **declares no operators**. Two different assertions sharing
> one name. The gap is live here: a principal whose grant set matches no entity
> produces an empty **served** set while all three shipped gates pass. **Recorded for
> the gap register and not closed** (`D-04`); covered below by `CPR-G08`, which is the
> mechanism Standard §4.7 provides for precisely this.

**Product-specific gates.** Derived from the vault's §G acceptance criteria and from
the three §C.4 traps — each a testable assertion naming the defect it detects,
cross-referenced to a fixture ID.

| Gate | Assertion | Detects | Fixture |
|---|---|---|---|
| **CPR-G01** Address distinguishability | headquarters and legal address are separately populated and **compared case- and whitespace-normalised**; an entity carrying `WILMINGTON` against `Wilmington` counts as **one** address, not two | §C.4 trap 1 — an unlabelled address served as the wrong one; and a raw comparison inflating 65 to 69 | `CPR-G01` |
| **CPR-G02** Entitlement discriminates | the **visible entity SET** differs pairwise across principals, with at least one entity visible to A and not B. **Counts sets, never sizes.** Carries a **negative control**: a principal differenced against itself must report identical | §C.4 trap 3 — a Policy step that is a no-op, and a cardinality check that passes one | `CPR-G02` |
| **CPR-G03** Freshness ceiling | an entity resolved through the internal client master **must not** advertise the 24-hour vendor SLA; its `freshness.signal_class` is `internal-kyc` and its ceiling is months | §C.3 — one averaged freshness claim over a mixed population | `CPR-G03` |
| **CPR-G04** Suppression silence | two principals' payloads differ in **content** and are **indistinguishable in structure**; no count, marker, placeholder or notice indicates anything was withheld | §B.2 — a `"3 hidden"` marker that is itself a disclosure | `CPR-G04` |
| **CPR-G05** Inert parameter fails loudly | `as_of` returns **`400 not_supported_at_tier`** and **never** silently succeeds against current state | §B.4 — a parameter that appears to work and will be relied on in a dispute | `CPR-G05` |
| **CPR-G06** Type-chain completeness | all **seven** Commons/FIBO classes of §C.3 are asserted; a partial chain propagates catalog-wide | §C.3 — an entity unreachable by three roles it genuinely holds | `CPR-G06` |
| **CPR-G07** Authority disclosure | **every** identity attribute names its authoring source via `identity_authority`; an attribute with no authority is a defect, not a default | §D.3 — a payload that cannot say which authority answered | `CPR-G07` |
| **CPR-G08** Empty served set | a principal whose grant set matches no entity gets a **fail-closed refusal or an explicit debt contribution**, never a `200` with an empty list | the gap between the Standard's gate 1 and the SDK's, named above | `CPR-G08` |
| **CPR-G09** No-LEI entity is servable | a no-LEI entity **resolves and reports its lower freshness ceiling** (§G criterion 3) rather than being refused by the TTL lower bound. The gate is written to FAIL on the declaration as it stands, and it is expected to — that failure is the evidence the finding is taken back with | §B.1 element 3's measured consequence — a 24h TTL over a months-old KYC observation puts `expires_at` in the past for **30 of 30** internal-client entities | `CPR-G09` |

**Every gate has been made to fail deliberately once — DONE 2026-08-29, P7.** A gate
that has never been observed red is not evidence that it runs.

| Gate | Sabotage applied | Result |
|---|---|---|
| `CPR-G01` | the two addresses made identical in the fixture | RED |
| `CPR-G02` | the entitlement join made to admit every entity | RED |
| `CPR-G03` | an internal-client entity made to report the 24-hour vendor ceiling | RED |
| `CPR-G04` | a `"1 entity hidden"` notice leaked into the suppressed payload | RED |
| `CPR-G05` | `unsupported_arguments` emptied, so `as_of` is silently honoured | RED |
| `CPR-G06` | the type chain truncated to six classes | RED |
| `CPR-G07` | `identity_authority` dropped from the payload | RED |
| `CPR-G09` | `expires_at` switched to `from_decision`, making the no-LEI entity servable | RED |

**`CPR-G09`'s sabotage is the one worth reading twice.** Its test asserts a
REFUSAL — the defect §F.4 finding 8 records — so "sabotaging" it means FIXING the
defect, and the test correctly went red. That is the confirmation it is the
evidence the deviation is taken back with rather than a test that ratifies a bug:
**when the TTL declaration is corrected, this test goes red, and that redness is
the signal to close the finding.**

**`CPR-G08` is NOT in the table, and its absence is the finding.** It has no
instance in the data — every principal sees at least 21 entities, so the empty
served set it refuses cannot currently occur. Standard §6: *"a demonstrable
primitive with no instance in the data reads to reviewers as machinery without a
purpose."* Registered at §F.2 row 20, owned by `ccf_dataprep`, and it is a
one-row fixture rather than a data programme.

---

## Section E — Volatility, debt & materialization

### E.1 Half-life table

| Signal class | `λ_c` proposed | Calibration basis | Decay driver | Supersession event | Owner |
|---|---|---|---|---|---|
| Vendor identity attributes | ~24 h | **illustrative** | daily concatenated GLEIF file | next vendor file touching the entity | platform |
| Registration status | ~24 h | **illustrative** | the field that lapses | vendor status change | platform |
| Internal KYC state | **months** | **expert** — the estate carries 180 / 270 / 365-day cycles | KYC refresh cadence | internal KYC state change | client reference data |

**`λ_c` values are proposed here and fixed in Control Plane configuration — a spec does
not set them.** Saying so is the difference between a value an engineer can challenge
and a number they assume was measured.

> **`λ_c` and TTL are different quantities and this product now shows why.** Half-life
> describes how fast a signal *decays*; TTL declares how long a served product may be
> *acted on*. They were briefly conflated in the approved §B.1 — one 24-hour TTL over
> two signal classes whose half-lives differ by two orders of magnitude — and the
> amendment there splits the TTL to match the classes named in this table. **A product
> whose TTL ignores its own half-life table refuses its slowest-moving population on
> arrival**, which is the measured result: 30 of 30.

> **A caution carried deliberately, because the same class of error is documented in
> this catalog.** `spec_generation.md` §10.2 records that a vault article set `λ_c` to a
> **publication cadence** (24 h) where the underlying half-life was nearer a **year**,
> and that an inverted materialization posture followed from it. The two 24-hour rows
> above are the vendor **file cadence**, and this document does not claim they are
> measured half-lives. **Two of three rows are `illustrative`, so this product is not
> calibrated** — stating that plainly is more useful than implying otherwise.
> `[TBC — this build, phase P8]` measures decay against observed read frequency.

### E.2 Debt model and per-component debt table

**`D_c = 1 − (F · C · S)`** — multiplicative, so a collapsed dimension **forces
escalation** rather than being averaged away.

| Term | Meaning here |
|---|---|
| **F** | age of the authoring source against its class `λ_c`, **normalized over required signal classes, not over the classes present** — otherwise losing a source improves the score. The ceiling is reduced for internally-authored entities (§C.3) |
| **C** | fraction of contract-declared attributes populated |
| **S** | agreement between the vendor legal name/jurisdiction and the internal client master for the same entity — **the earliest warning of a bad crosswalk match** |

**Per-component debt table.** Debt is decomposed **per claim, never only per product**.

| Component | May be absent? | `D_c` contribution | Behavior when absent |
|---|---|---|---|
| LEI / legal name / jurisdiction | **no** | — | **fail closed → 404.** Without these there is no identity |
| Entity status · registration status | **yes** — null for internal-client-master resolutions | `[TBC — this build, P8]` | serve with the claim marked `NOT_EVALUABLE`; **not** a product-level failure |
| Legal form | yes | `[TBC — this build, P8]` | serve with flag |
| **Headquarters address** | yes — 3 of 156 lack one (§C.4 trap 1) | `[TBC — this build, P8]` | serve with the claim marked `NOT_EVALUABLE`; **never silently omitted** |
| Legal address | no | — | fail closed |
| **Entitlement scope** | **no** | — | **fail closed → 503.** An unreachable entitlement service is never a permissive default |
| Crosswalk row | yes, for an LEI-only entity | `[TBC — this build, P8]` | serve; `S` cannot be computed and contributes its full weight |

**A product with four claims where one input is missing returns three evaluated claims
and one marked unusable** — not a product-level failure, and never a silently-omitted
fourth. The gap is captured **before the decision is taken** and shapes it directly: a
decision input, not a log line.

**The scope boundary is what keeps this table short.** Grade and coverage are out of
scope (§B.5), so they are **not components** and contribute nothing. Under a table that
counted them, their absence would contribute `0.30` against a `0.25` tolerance and the
product would return `409` rather than serve — see §B.5. **A field that is out of scope
contributes no debt; a field that is in scope and missing contributes all of it.**

`debt_tolerance` default **0.25 — provisional and unbacked**, and it stays that way
until measured against crosswalk match confidence, which is itself
`[TBC — ccf_dataprep]` (§C.3). Certification is where `λ_c` and debt tolerance stop
being illustrative and become measured.

### E.3 Materialization posture

**`derived-on-demand`.** Cost band `×1`.

**The Standard's test is mechanical:** if the fastest-moving input's `λ_c` is shorter
than the intended cache window, materialization is wrong. The fastest input here is
registration status at ~24 h, so a cache window beyond a day is excluded on that test
alone.

**But the binding reason is the principal, not the clock.** `Policy` produces a
**per-principal** visible set (§D.3). A materialized product must therefore key on the
principal, and a cache key missing it returns one principal's entities to another —
a correctness defect that presents as an intermittent one, and on this product a
**disclosure**.

**Cache key, stated explicitly:** `(tenant, schema_name, anchor, principal_id,
policy_version, graph_snapshot_at)`. Note what is absent: `assembled_at` (§D.4) and
`debt_tolerance` — the latter changes whether the product is *served*, not what it
*contains*, so including it would fragment the cache without changing a payload.

### E.4 Supersession triggers

| Event | Local or cascading | Named downstream targets |
|---|---|---|
| Next vendor file touching the entity | **cascading** | every product in the catalog — §B.5 |
| Internal KYC state change | **cascading** | `kyc-refresh-beneficial-ownership` first; then any product whose `operators_invoked` touched the entity |
| `principal_jurisdiction` grant change | **local** to the affected principal's cached products | — |
| Crosswalk row added or corrected | **cascading** | every product joining on `internal_client_id` |

**Invalidation cascades to every product whose `operators_invoked` touched the
superseded entity, not only those named for it.** Given §B.5's consumer list, that is
close to the whole catalog — which is a property of building the anchor first, and the
reason `re-derivation is lazy`: invalidate for the next request, never re-materialize
eagerly, or a routine vendor publication becomes a thundering-herd event across 21
products.

---

## Section F — Source binding & readiness

### F.1 Element readiness

| Element | System of record | Interface & cadence | Available today | Gap owner | Blocker |
|---|---|---|---|---|---|
| LEI, legal name, jurisdiction, status, registration status, legal form | LEI reference data | GLEIF LEI-CDF Level 1, daily concatenated file | **yes** — 156 of 156 | — | — |
| Legal address | LEI reference data | same | **yes** — 153 of 156 | — | — |
| **Headquarters address** | LEI reference data | same | **partial** — 153 of 156; the 3 excluded are synthetic ABS trusts with no GLEIF record | — | not a blocker; §C.4 trap 1 |
| No-LEI internal identity | internal client master | internal, KYC cadence | **yes** — 30 rows | — | — |
| **KYC verification date and cycle** | internal client master | internal | **yes** — `kyc_last_refresh`, `kyc_cycle_days`, `kyc_next_due`, `freshness_ceiling_days` | — | — |
| Entitlement scope by jurisdiction | entitlement service | internal | **yes** — 17 grants over 4 principals | — | — |
| LEI ↔ internal client crosswalk | internal mapping | internal | **yes** — 83 rows; 53 with LEI, 30 without | — | — |
| **Crosswalk match confidence** | internal mapping | — | **no** | `ccf_dataprep` | measurement not performed; coverage ≠ confidence |

> **All three elements that were `GAP` on 2026-08-28 are now satisfied**, closed by
> `ccf_dataprep` at `465ba4d`, `39f373d` and `5b957af` (merged at `3257769`).
> `validators/spec_coverage.py --product counterparty-reference-snapshot` reports
> **4 of 4 catalog rows accounted for, zero `GAP`**, against **1 PASS / 3 GAP** at the
> start of that day. **Verified independently against the live estate on 2026-08-29 by
> read-only query**, not read off that repo's report — and the vault has confirmed it
> could not verify these itself, so **these rows are this document's to evidence.**

### F.2 Every `[TBC]` in this document, with an owner

| # | Marker | Section | Owner | Cleared at |
|---|---|---|---|---|
| 1 | Schema artifact `counterparty_reference.v1.json` | §B.1 | this build | P6 |
| 2 | Residency constraints | §B.2 | identity and access | — |
| 3 | Cross-border serving condition | §B.2 | identity and access | — |
| 4 | `debt_tolerance` calibration (provisional 0.25) | §B.4, §E.2 | product owner + `ccf_dataprep` | P8 / certification |
| 5 | Ontology IRI — entitlement scope | §C.1 | `ccf_dataprep` | — |
| 6 | Ontology IRI — crosswalk | §C.1 | `ccf_dataprep` | — |
| 7 | Crosswalk **match confidence** | §C.3, §F.1 | `ccf_dataprep` | — |
| 8 | Foreign-private entity count | §C.3 | `ccf_dataprep` | — |
| 9 | p95 budget, step 1 · step 2 · step 3 · total · envelope | §D.2 | this build | P6 |
| 10 | `ServableProduct` mechanism confirmation | §D.3 | this build | P7 |
| 11 | `payload_hash` value | §D.4 | this build | P6 |
| 12 | Replay fixture `CPR-R01`, both hashes | §D.5 | this build | P6 |
| 13 | Schema artifact + `extra=forbid` CI binding | §D.6 | this build | P6 |
| 14 | Debt-gate `409` behavior | §D.7 | this build | P7 |
| 15 | ~~Sabotage result for each of the eight gates~~ **CLEARED 2026-08-29** — seven of eight red; `CPR-G08` has no instance (row 20) | §D.7 | this build | **P7 — done** |
| 16 | `λ_c` measured against read frequency | §E.1 | this build | P8 |
| 17 | Per-component `D_c` contributions (5 rows) | §E.2 | this build | P8 |
| 18 | Counterfactual fixture `CPR-F01` | §A | this build | P7 |
| 19 | An entity whose registration **lapses** — the data condition `CPR-F01` acts on | §F.3 | `ccf_dataprep` | — |
| 20 | A principal whose grant set matches **no** entity — the condition `CPR-G08` acts on | §F.3 | `ccf_dataprep` | — |

> **Rows 19 and 20 were missing from this register when it was first written, and the
> omission is recorded rather than quietly fixed.** Both markers existed in §F.3's
> volumetrics table; neither reappeared here, against §0.2's own rule that *every*
> marker reappears at §F.2 with a named owner. Found by enumerating the markers and
> mapping each to a row — **not** by comparing totals, which would have read 43 body
> markers against 18 rows and proved nothing either way, since one row legitimately
> covers several markers. **A count is not a roster**, and this document's own §C.4
> names that as the method these traps share.
>
> Note also what rows 18 and 19 separate: the **fixture** is this build's to write, the
> **data condition it acts on** is `ccf_dataprep`'s to supply. Collapsing them into one
> row would have assigned an owner who cannot discharge it.

**Eleven are `this build` and clear at Gate 2. Six are `ccf_dataprep`'s. Two are
identity and access's. One is shared. Twenty in total.** *A spec with honest gaps is buildable; a spec
with invented system names is not.* **No `[TBC]` above is a guess wearing a marker** —
each names a measurement nobody has taken, not a value this document declined to
write down.

### F.3 Access path, identifiers, history, volumetrics

**Estate binding — where the data actually lives.**

The estate carries **five stores**. A developer reading `ccf_v2.legal_entity` cannot
tell from the name alone which of the five it is, so this table says it outright. §F is
the section for source binding, and this is the binding.

| Capability class | Store kind | Namespace this product reads | Connection |
|---|---|---|---|
| `relational` | **PostgreSQL** | schema **`ccf_v2`** — tables `legal_entity`, `internal_client`, `crosswalk`, `principal`, `principal_jurisdiction` | `backends.yaml` → an env-var **name**; no host, port or credential in this tree |

**The four stores this product does NOT read, and why — stated so their absence reads
as a decision rather than an oversight:**

| Store | Namespace | Why not here |
|---|---|---|
| **Fluree** (graph) | ledger `fibo-v2` | requires `graph-traversal`; this product has **no Traversal step** (§D.2) and the scope boundary excludes relationships (§B.5). The **first** product to read it is `corporate-family-tree` |
| **MongoDB** (documents) | database `fibo_v2` | requires `document-passage`; no element here is extracted from a document (§F.3, text-source boundary) |
| **SQLite** (departmental) | `data/departmental.sqlite` | no element of this product is departmental |
| **Neo4j** (optional) | — | not required by any capability class in §C.2 |

> **The seven-class typing chain at §C.3 is a Fluree-side concern that this product
> nonetheless decides.** The IRIs are asserted in the graph store, not in the relational
> one — but every product that later reads them inherits the chain chosen here, which is
> why §C.3 fixes it and `CPR-G06` proves it. A T1 product deciding a T2 store's typing
> is unusual and deliberate.

**Why this table exists.** Because this is an **SDK-level** specification (§0) — a
specific implementation artifact bound to one estate, not the implementation-independent
product specification the vault holds. Standard §10.1's *"product specs never name a
database"* governs that other level and is right there; at this level, omitting the
store would fail Standard §0's own test that a spec be *"complete enough that a data
engineer can identify the source systems, build the assembly path, register the product,
and operate it without a further design conversation."* **Identifying the source system
is the first item on that list**, and a table reference without its store does not
satisfy it.

So the store is named **per element at §C.1** and **collectively here**; the deployment
stays in `backends.yaml`. **Nothing about this is a correction owed to the vault** —
see §F.4 finding 7.

**Access path.** Existing feed. GLEIF Level 1 is already acquired and loaded; the
internal client master, crosswalk and entitlement grants are internally generated. **No
new build is required for rung 01** — a claim that distinguishes this rung from every
later one.

**Identifier reality.** The correlation key exists end to end. LEI covers 156 entities;
`internal_client_id` covers 30 more; the crosswalk joins them with **zero orphans**.
**Measured coverage is a count, not a confidence** — see §F.1's final row.

**History depth.** **None retained.** The source publishes a daily snapshot and this
estate holds current state only, which is why `as_of` is inert (§B.4). **This bounds
the replay test at §D.5:** step 4 re-derives at a recorded `graph_snapshot_at`, and
that requires the snapshot to exist. `[TBC — this build, phase P6]` establishes whether
the fabric's own snapshot satisfies it without source history. **History not captured
cannot be reconstructed later** — if a later rung needs source history, delta retention
starts now, not then.

**Text-source boundary.** Not applicable. No element of this product is extracted from
a document; capability class stays `relational` and the cost band stays `×1`.

**First-build volumetrics — the population every gate and counterfactual needs
something to act on:**

| Gate / test | Needs | Estate holds | Sufficient? |
|---|---|---|---|
| `CPR-G01` address distinguishability | ≥1 entity whose two addresses genuinely differ | **65 of 153** (normalised) | yes |
| `CPR-G02` entitlement discriminates | ≥2 principals with **different sets** | 4 principals, all 6 pairs differ | yes |
| `CPR-G02` negative control | 1 principal to difference against itself | 4 | yes |
| `CPR-G03` freshness ceiling | ≥1 no-LEI entity | **30** | yes |
| `CPR-G07` authority disclosure | ≥1 entity per authority | 156 + 30 | yes |
| `CPR-G08` empty served set | ≥1 principal whose grant set matches **no** entity | **0 — every principal sees ≥21** | **no** |
| `CPR-F01` counterfactual (TTL expiry) | an entity whose registration lapses | `[TBC — ccf_dataprep]` | unknown |
| `CPR-R01` replay | a mutable attribute + a snapshot | see History depth | `[TBC — this build]` |

> **Two rows above are the finding, and neither blocks Gate 1.** `CPR-G08` has **no
> instance in the data** — every principal sees at least 21 entities, so the empty
> served set the gate exists to refuse cannot currently occur. Standard §6 is explicit:
> *"Where a required case does not occur naturally in the sample, widen the sample
> until it does rather than proceeding without it; a demonstrable primitive with no
> instance in the data reads to reviewers as machinery without a purpose."* The
> cheapest widening is a **fifth principal with a grant set matching no entity in the
> estate** — a one-row fixture, not a data programme. `[TBC — ccf_dataprep]`, and it is
> a **fixture** request rather than an estate change.

### F.4 Recorded findings — not `[TBC]`, because none needs a decision to build

1. **The vault's §C carries a `Store` column holding the engine name** — `Postgres`, on
   all four rows — where Standard §10.1 puts estate binding in a platform-owned
   artifact. Corrected **narrowly**: the concrete tables move into `System of record`,
   where they are more useful to a builder, and the engine name is dropped. **Filed back
   to the vault** (§C.1). *This finding is about the engine column only.* An earlier
   draft of this section overreached and read as though §C should not identify data at
   all — corrected here, because a specification that will not say which table an
   element comes from is not an implementation specification. `CP-SPEC-000` is the
   precedent on both halves: concrete `ccf_v2.*` tables 12 times, engine name 0 times.
   **Not filed upstream** — §C element rows are `ccf_dataprep`'s term under
   `spec_generation.md` §1, not the vault's, so there is no vault-owned claim to
   correct. **None of the six findings in this section is a vault-owned term**; every
   one is an authoring decision on this side of the ownership line, which is why they
   are recorded here rather than returned.
2. **The vault's parameter surface omits `debt_tolerance` and `as_of`.** Both are
   universal under Standard §2.4. Added here (§B.4), with `as_of` declared inert rather
   than silently absent.
3. **The vault's `operators_invoked` is a list of bare names.** Lineage strict equality
   compares declared against engine-resolved; a comparison needs addresses on both
   sides. Bound to SDK mechanisms in §D.2's eighth column.
4. **Two of three `λ_c` rows are a file cadence, not a measured half-life** (§E.1), the
   error class `spec_generation.md` §10.2 documents. Marked `illustrative` rather than
   inherited as fact.
5. **The SDK's empty-operator guard is not the Standard's** (§D.7). Recorded for the
   gap register under `D-04`; covered by `CPR-G08`, not closed here.
6. **The exemplar at `public/reference/specifications/` declares four out-of-scope
   payload fields** (§B.5). It is a control for comparison, not an authority; the
   `409` its debt table implies does not arise under this specification.
8. **The 24-hour TTL and the months-long freshness ceiling do not compose, and the
   contradiction is measured rather than argued.** `ttl_anchor: from_entity_freshness`
   over an internal-client observation that is months old by design puts `expires_at`
   in the past for **30 of 30** no-LEI entities, so `_refuse_ttl` rejects on first call
   the whole population the identity authority hierarchy exists to include — while 27 of
   30 are live under their own declared ceiling. **The declaration stands at 24 hours**
   (§B.1 element 3); this is registered as a **build finding to be settled by a run**,
   not by machinery invented ahead of one. `CPR-G09` settles it. **A §11 return becomes
   owed once the run confirms it** — the vault's §B carries the same single TTL, and a
   build disproving a declared term is exactly what §11 asks to be sent back. Unlike
   finding 7 this would be a claim about the world that is wrong, not a rule applied at
   the wrong level.
7. **Standard §10.1 is not defective — it was mis-scoped, and the correction is
   recorded because the mis-scoping cost real time.** *"Product specs never name a
   database"* governs the **vault level**: an implementation-independent product
   specification, which should not bind to an estate. **This document is the SDK
   level** — a specific implementation artifact — where the store must be named or the
   table reference means nothing (§0, Dave's ruling 2026-08-29). Two levels, two
   correct answers, no conflict.
   **NO §11 RETURN IS OWED, and an earlier draft of this section wrongly said one was.**
   That draft treated §10.1 as a defect in a vault artifact. It is not; it is a rule
   about a different artifact class than the one it was being applied to. **None of the
   seven findings in this section is a vault-owned term.**
   **`CP-SPEC-000` was corrected on 2026-08-29 — this paragraph previously said it
   could not be.** It read that its §F.3 records removing its store name on the literal
   reading, that `D-07` forbade bringing completed work into line, and that aligning it
   was *"a separate, explicitly-scoped change if Dave wants one — recorded here, not
   performed."* **Dave wanted one** (*"fix D-07"*), `D-07` now distinguishes an
   unbounded **retrofit** from a bounded **correction** (`24-CONTEXT.md` `D-07.1`), and
   the store name is restored at `CP-SPEC-000` §F.3 with the two-level ruling recorded
   beside it. **Corrective edit under `D-07.2`, stated rather than made silently.**

---

## Section G — Operate & govern

### G.1 The expiry obligation, restated where an operator will look for it

**This product's reason to exist is the expiry** (§A). An operator reading only this
section must still find it: `expires_at` is derived from **when the source last spoke
about the entity**, not from when the question was asked, and a consumer that caches
past it is in exactly the state the counterfactual describes. The TTL is not a
performance hint. **A served product whose `expires_at` the consumer is not obliged to
honour has failed, whatever else it returned.**

| Entry | Content |
|---|---|
| **Accountable owner** | product: Wholesale Reference Data · data steward: client/entity reference data · policy owner: identity and access — **roles, not individuals** |
| **Service objectives** | p50 / p95 assembly latency, volume, concurrency ceiling, payload bound, absolute per-call cost: `[TBC — this build, phase P6]`. The **instrument** is named with the number when it lands — a number without its instrument is a number |
| **Degradation contract** | **Mandatory** (fail closed): identity attributes → `404`; entitlement scope → `503`. **Non-mandatory** (serve with elevated `D_c` + notice): headquarters address, entity/registration status for internal-client resolutions, legal form, crosswalk row |
| **Debt model** | §E.2. `debt_tolerance` default `0.25`, provisional |
| **Observability** | per-operator latency · `D_c` distribution · **gate-failure counts by gate, all eight** · cache hit rate · **entitlement denials** · degradation-branch frequency · supersession-triggered invalidations. This is also the evidence base for moving `λ_c` and `debt_tolerance` from illustrative to measured |
| **Retention & record of record** | LEI reference data is record of record for external identity; the internal client master for no-LEI identity and KYC state. **The fabric references them and does not replace them.** Replay-record retention tier: `[TBC — this build, phase P8]` |
| **Test fixtures** | `CPR-F01` counterfactual · `CPR-G01`…`CPR-G08` one per gate · `CPR-D01` degradation branch · `CPR-R01` replay hash assertion |
| **Lifecycle** | **`draft`** — Gate 1 authored 2026-08-29, reviewer **Dave, pending**. Certification requires every §F.2 row closed or accepted by a named owner |

### G.2 Acceptance criteria

Assertions specific to this product, each independently verifiable, **each phrased so
it can fail**. The universal definition of done is Standard §15; these are what *this*
product must additionally prove.

1. **The TTL refusal fires.** A consumer holding a product past `expires_at` refuses
   the cached row. `CPR-F01`.
2. **The replay test produces both a differing and a matching hash.** Live re-derivation
   after a source change differs; re-derivation at the recorded snapshot matches.
   `CPR-R01`. **A replay that cannot produce a differing hash is not demonstrating
   replay.**
3. **A no-LEI entity resolves and reports the lower freshness ceiling in the payload** —
   months, not 24 hours. `CPR-G03`.
4. **`payload_hash` is stable across identical requests** — same anchor, same principal,
   same `policy_version`, same snapshot.
5. **Two principals receive different entity sets and cannot tell.** Content differs;
   structure is indistinguishable; no marker of withheld content. `CPR-G02` + `CPR-G04`.
6. **Both addresses are separately populated and distinguishable**, compared
   case-normalised. `CPR-G01`.
7. **`as_of` returns `400 not_supported_at_tier`** and never a silent success.
   `CPR-G05`.
8. **All seven type-chain classes are asserted.** `CPR-G06`.
9. **Every identity attribute names its authority.** `CPR-G07`.
10. **Each of the eight gates has been observed RED at least once**, deliberately.

**Open decisions blocking build — named by their §F row:** **none.** Every §F.2 marker
is either `this build` (cleared by building) or owned by another agent and
non-blocking. The one that would become blocking at **certification**, not at build, is
row 7 — crosswalk match confidence — because `debt_tolerance` cannot stop being
provisional until it is measured.

### G.3 Catalog contribution

**What this product proves that no earlier product proved:**

- **`ttl_anchor: from_entity_freshness`** — an expiry derived from the source's last
  observation of the entity, per entity. `cp-00` anchors on a fixed reported period;
  this is the contrast (§A).
- **Two identity authorities behind one anchor parameter**, with the resolving authority
  and its freshness ceiling carried **in the payload**.
- **A Policy step that is load-bearing at Tier 1** — visible sets that genuinely differ,
  proven as sets rather than sizes, with a negative control.
- **Suppression silence as a structural property** of step ordering rather than as a
  filter applied afterwards.

**What it deliberately does not prove:**

- **No projection.** Π is not exercised; `projection_plan_id` is null. Different
  *populations* per principal, never different *assembly*. That arrives at T5.
- **No traversal, no temporal axis, no document passage, no similarity.** One capability
  class, `relational`.
- **No second time axis.** `as_of` is inert, so the Standard's *"two filters on two
  axes"* discipline has nothing to bite on (§D.5).
- **Nothing about exposure, grade or relationship** — the scope boundary (§B.5), and the
  first thing a reader will look for and not find.

---

## Gate 1 — status

**This specification is complete except for its `[TBC]` register at §F.2**, and is
submitted for approval per `spec_generation.md` §2.

**Nothing is implemented until Dave approves it.** At Gate 2 every
`[TBC — this build]` is cleared by a value the build measured, and **a Gate-2 value
that contradicts an approved Gate-1 decision is a deviation** — taken back for a
ruling, never absorbed silently.
