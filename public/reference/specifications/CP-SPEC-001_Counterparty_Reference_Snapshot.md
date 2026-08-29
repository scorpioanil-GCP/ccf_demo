# Counterparty Reference Snapshot — Context Product Specification

**CP-SPEC-001** · Authored to Specification Standard v0.3

**Tier 1** · `reference.counterparty.v1` · Assembly Mode 1 · cost band ×1
(baseline)

**Lifecycle:** draft · **Product owner:** Wholesale Reference Data ·
**Data steward:** Client / entity reference data · **Policy owner:**
Identity and access · **Last review:** 2026-08-21

Resolves a single counterparty to a typed, contract-bound identity snapshot.
The minimum viable Context Product: its job is to prove the contract fires,
not to demonstrate context assembly.

**Build test.** Role-dependent content **no** (jurisdiction visibility
only) · validity window **yes** · must be reconstructible **yes** · composed
at runtime **partial** (two sources, one join). Two clear yeses, one
qualified. This product is admitted as the catalog's contract-machinery
entry point rather than on its own assembly merit — an honest reading of the
test, and the reason it qualifies is the TTL and the replay obligation, not
the composition.

**Build this first.** Every other product resolves its anchor through this
one and inherits its contract machinery, typing decisions, and identity
authority hierarchy. A shortcut here propagates to all of them.

**Capability gate.** None. This product requires only the `relational`
capability class and is deliverable against any estate that can serve a
set-based query and an entitlement call. It is the only product in the
catalog with no capability risk, which is a second reason to build it first:
it proves the contract machinery before any platform decision is contested.

**Placeholders.** Items marked `[TBC]` require a decision or a measurement
and have deliberately not been guessed. Every marker appears again in §F
with a named owner.

---

## A · Decision frame

**Decision & trigger.** A relationship manager or credit officer opens a
counterparty record, or any downstream agent needs a canonical identity
before it can do anything else. This product is the resolution step of every
other product in the catalog.

**Consuming principals.** Single role at this tier. Π is not exercised —
every authorized caller receives the same assembled shape, differing only in
whether the entity is visible at all under jurisdiction entitlement. A
second principal requiring different content is a new version with a
projection plan, not a formatting change.

**Counterfactual failure — evidence-free, and narrowly so.** The
counterfactual here is narrower than the rest of the catalog and worth
stating precisely rather than inflating. A reference-data lookup returns the
same fields. What it does not return is an expiry. The consumer caches the
row indefinitely and keeps reasoning against an entity whose registration
has since lapsed — nobody has revalidated that it still exists as described
— or whose internal risk grade was downgraded two quarters ago. **The
failure is not a missing signal, it is a missing TTL**, and it is silent by
construction.

**Counterfactual acceptance test.**

1. Serve the product for an entity whose registration status is about to
   lapse. Record `expires_at`.
2. Hold the served contract past `expires_at` and request it again from
   cache. **The delivery layer must refuse to serve without
   re-derivation.**
3. Land the next vendor file, in which the entity's registration status has
   moved to lapsed.
4. Re-derive. The status must flip, and under `include_lapsed=false` the
   record must be excluded entirely rather than returned unflagged.

If step 2 serves from cache, the TTL is advisory rather than enforced and
the product has not addressed its own counterfactual.

**Primitive taught.** The contract itself, and specifically
`ttl_anchor: from_entity_freshness` computed from source publication rather
than request time.

**Contrast pointer.** `credit-risk.exposure-rollup.v1` flips the anchor to
`from_decision` on the same axis. Read the two together.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
| --- | --- |
| Schema | counterparty_reference — entity: LegalEntity; attributes: identity keys, legal name, jurisdiction, entity status, registration status and renewal date, legal form, legal and headquarters address, industry classification, fiscal year end, internal obligor grade, coverage assignment. No relationships — the ownership graph arrives at reference.corporate-family.v1. Artifact: `schemas/counterparty_reference.v1.json` |
| Freshness SLA | 24 hours for externally-authored identity attributes (daily vendor publication); 1 business day for the internal overlay |
| TTL | 24 hours · ttl_anchor: from_entity_freshness — expires_at derives from the source file's publication timestamp, not request time. A 23:00 request against an 06:00 file gets 7 hours of validity, not 24 |
| Policy Binding | Entitlement scope only — jurisdiction visibility per calling principal, resolved against the enterprise entitlement service. No regulatory overlay at this tier. policy_version is still emitted so the ordering is established from the first product rather than retrofitted |
| Lineage | operators_invoked: [Resolve, Policy] · graph_snapshot_at · policy_version · identity_authority (authoring source per attribute) · context_debt · payload_hash · model_record: null |
| Semantic Version | v1.0.0 · no prior version · migration window n/a |
| Discovery | reference.counterparty.v1 |
| Addressability | `/context-products/reference/counterparty/{entity-id}` — LEI or internal client identifier; see the dual-anchor note at §C.4 |
| Assembly Mode | 1 — pure algorithmic. Two operators, no computation, no narrative requirement. This is the reference implementation of Mode 1: if any part of the identity path ever needs a model, the identity model is broken, not the mode choice |

**Model-risk annotation.** Not applicable — no model in the trust path.

### B.2 Classification and residency

| Field | Value |
| --- | --- |
| Data classification | internal — vendor identity attributes are public; the internal overlay (obligor grade, coverage) is internal. The product carries the higher of the two |
| Information barrier | none. Coverage assignment is not restricted-list information; if a future version adds deal or pipeline context it becomes MNPI-bearing and moves tier |
| Residency constraints | Entity records for jurisdictions with local data-residency obligations must not be served outside the permitted region. Applies to the internal overlay in particular, where the vendor attributes are public and the internal grade is not |
| Cross-border serving | Conditional — public identity attributes yes; internal overlay only where the principal's region is permitted for that entity's domicile |

### B.3 Request parameter surface

| Parameter | Type | Moves | Default | Notes |
| --- | --- | --- | --- | --- |
| entity_id | string, required | E anchor | — | LEI (20 char) or internal client id |
| intent | enum (intent registry), required | P envelope | — | relationship-review · credit-review · onboarding-check |
| include_lapsed | bool | filter | false | when false, a lapsed entity is excluded entirely, not returned unflagged |
| include_internal_overlay | bool | payload shape | true | false suppresses every confidential-class element |
| debt_tolerance | float 0–1 | fail-closed bound | 0.25 | provisional; see §G debt model |
| as_of | datetime | T reconstruction | now | declared but inert at this tier — returns 400 not_supported_at_tier |

**On as_of.** The parameter is declared so the request surface is uniform
across the catalog and consumers do not learn a second calling convention at
Tier 3. It must **fail explicitly**, never silently succeed against current
state. Identity reconstruction as it stood on a past date requires the
bitemporal ledger and arrives at Tier 3.

### B.4 Prerequisites, consumers and scope boundary

**Prerequisites.** None. This is the entry point.

**Consumers.** reference.corporate-family.v1 · reference.facility.v1 ·
credit-risk.exposure-rollup.v1 · credit-risk.collateral-coverage.v1 ·
coverage.client-360.v1 — and transitively every product above them. **Every
product in the catalog is a consumer.** A MAJOR version here is a
catalog-wide migration, which is the strongest argument for getting the
schema and the anchor right before anything else is certified.

**Deliberately out of scope.** No ownership or family structure
(reference.corporate-family.v1). No exposure or facility data. No as_of
reconstruction of identity (Tier 3). All three are the tier boundary
working; flag them to consumers as *coming next*, not as gaps.

---

## C · Data catalog

### C.1 Elements

| Element | System of record | Provenance | Classification | Capability class | G | Ontology IRI |
| --- | --- | --- | --- | --- | --- | --- |
| LEI, legal name, legal jurisdiction | LEI reference data (Level 1) | vendor | public | relational | E | cmns-org:LegalEntity |
| Entity status · registration status · renewal date | LEI reference data (Level 1) | vendor | public | relational | E | ex:registrationStatus |
| Entity legal form (ELF code) | LEI reference data (Level 1) | vendor | public | relational | E | cmns-org:FormalOrganization |
| Legal address · headquarters address | LEI reference data (Level 1) | vendor | public | relational | E | fibo-fnd-plc-adr:PhysicalAddress |
| Industry classification · fiscal year end | Public filings reference | public-filing | public | relational | E | ex:industryClassification |
| Legal name, jurisdiction, status — no-LEI entities | Internal client master | internal-SOR | internal | relational | E | cmns-org:LegalEntity |
| Internal client id ↔ LEI crosswalk | Internal client master | internal-SOR | internal | relational | E | ex:identifierCrosswalk |
| KYC verification state and date | Internal client master | internal-SOR | confidential | relational | T | ex:kycVerificationState |
| Internal obligor risk grade | Internal credit system | internal-SOR | confidential | relational | E | ex:internalRiskGrade |
| Coverage assignment (RM, team, LOB) | CRM | internal-SOR | internal | relational | E | ex:coverageAssignment |
| Principal entitlement scope | Enterprise entitlement service | internal-SOR | internal | relational | P | ex:entitlementScope |

### C.2 Capability decomposition

Only `relational` is required, and it decomposes into three properties an
estate almost certainly satisfies. The decomposition is stated anyway,
because it is the template every later product inherits and because one
property is less universal than it appears.

| Property | Common estate answer | If absent |
| --- | --- | --- |
| Set-based retrieval of an entity's attributes in a single round trip | Widely available | Degrades to per-attribute fan-out; the p95 budget in §D.2 is unachievable |
| Entitlement read resolving before data retrieval | Sometimes — many estates filter after | Blocking. Policy-after-retrieval is the failure the architecture exists to prevent, and retrofitting the ordering at Tier 5 is not possible |
| Type query against the full class chain without inference | Rare in relational estates | Degrades to application-side type expansion; acceptable at Tier 1, revisit before Tier 2 |

**Not required here, required later.** bitemporal-ledger from Tier 3,
document-passage and vector-index from Tier 4, federated-external at Tier 5.
Confirming those estate answers is not a Tier 1 obligation, but raising them
at Tier 1 review is — a capability discovered missing at Tier 3 has already
consumed two tiers of schedule.

### C.3 Correlation key and single-writer discipline

**Correlation key.** LEI spans every external element; internal client id
keys the bank-side overlay. **The crosswalk is the product.** Nothing joins
without it, and its coverage and match confidence bound the correctness of
every downstream product. Measured coverage: **unknown — see §F**.

**Single-writer discipline.** LEI reference data is the writer for external
identity attributes; the internal client master is the writer for no-LEI
identity and KYC state; the internal credit system is the writer for grade.
**No element is written by two systems.** Where an attribute exists in both
a client master and a downstream warehouse today, the client master is the
authority and the warehouse becomes a read replica — a prerequisite to
build, not a follow-up.

### C.4 Identity authority hierarchy — the Tier 1 design decision

Anchoring exclusively on LEI works for CIB counterparties and public
Commercial Banking obligors. It does not work for the privately-held
middle-market borrowers who make up a large share of the Commercial Banking
book and have no LEI at all. **An LEI-only anchor silently excludes them,
and every downstream product inherits the exclusion.** The product therefore
accepts either identifier and carries an explicit authority hierarchy:

| Entity class | Identity authority | Registration status source | Freshness ceiling |
| --- | --- | --- | --- |
| LEI-registered (public, most CIB) | LEI reference data | Vendor registration status and renewal date | 24 hours |
| Private, no LEI | Internal client master | Internal KYC verification state | KYC refresh cadence — months |
| Foreign private | Internal client master + local registry where available | Internal KYC verification state | KYC refresh cadence — months |

An entity resolved through rows two or three carries a materially lower
ceiling on F, and **that asymmetry is stated in the payload rather than
averaged into a single freshness claim.**

### C.5 Typing decision — it propagates catalog-wide

LegalEntity, Agent, Party and FormalOrganization bind to the OMG Commons
namespace, **not FIBO**; only Corporation stays in FIBO. LegalEntity has two
parents — FormalOrganization and LegalPerson — and reaches Party only
through them, with no direct axiom. Under a no-inference store, typing an
entity Party + LegalEntity + Corporation leaves it unreachable by a query
for FormalOrganization, Organization, or LegalPerson, three roles it
genuinely holds.

**Type against the full seven-class chain** from the shared ontology
binding: Agent, Party, Organization, FormalOrganization, LegalPerson,
LegalEntity, Corporation. A validator asserting that every type IRI begins
with the FIBO namespace will reject correct data. Because every product
resolves its typing through this one, a partial chain here propagates
catalog-wide.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/reference/counterparty/5493001KJTIIGC8Y1R12
    ?intent=relationship-review
    &include_internal_overlay=true
    &debt_tolerance=0.25
```

### D.2 Operator steps

| # | Operator | Capability class | Inputs | Emits | Failure behaviour | p95 budget |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Resolve | relational | entity_id | entity_id, canonical attributes, identity_authority per attribute, source publication timestamps | fail closed → 404; crosswalk collision → 409 | 15 ms |
| 2 | Policy | relational | principal, intent, entity jurisdiction | policy_version, permitted jurisdiction set | fail closed → 403 not entitled, 503 service unreachable | 40 ms |
| 3 | Contract assembly | in-memory | outputs of 1–2 | CounterpartyReferenceContract@v1.0.0, payload_hash | validation gates §D.6 | 20 ms |

**Total p95 budget: 75 ms** against a Tier 1 envelope of 250 ms. The
headroom is deliberate: this is the denominator of the entire cost model and
every other product's budget is read against it. Step 2 dominates and is the
only realistic optimisation target — but it must not be cached across
principals.

### D.3 Step detail

**Step 1 — Resolve.** Classify entity_id as LEI or internal client id.
Validate LEI check digits at the boundary before any store access; an
invalid LEI must fail as a malformed anchor, not as a missed lookup. Look up
the canonical entity and, where the anchor is an internal id, resolve the
LEI through the crosswalk where one exists. Retrieve the entity row and the
internal overlay in a **single query joined on the crosswalk** — not two.

Capture the **source publication timestamp of every element**, not merely
its value; expires_at in step 3 has nothing to compute from otherwise.

A crosswalk **miss** on a no-LEI entity is not a failure — it is the
expected path for that entity class and sets identity_authority to the
internal client master. A crosswalk **collision** is a failure: fail closed
rather than pick one.

**Step 2 — Policy.** Load the calling principal's entitlement scope; confirm
jurisdiction visibility and residency permission for the resolved entity.
Emit policy_version.

**Why Policy runs here despite doing almost no work.** The ordering —
*policy before assembly* — is the discipline every later product depends on,
and it is learned from the first example or retrofitted painfully later. At
Tier 5 this same step is what makes an MNPI-bearing edge structurally absent
rather than filtered. **Do not optimise it away here.** A 403 carries no
detail on what exists: existence is itself disclosure.

**Step 3 — Contract assembly.** Build CounterpartyReferenceContract@v1.0.0.
Populate operators_invoked with **typed operator references** (not names),
graph_snapshot_at, policy_version, identity_authority, context_debt,
payload_hash, and expires_at from the source publication timestamp plus 24h
per from_entity_freshness.

Where the entity resolves through the internal client master, expires_at
derives instead from the KYC verification date and its own cadence — a
materially longer window the payload states explicitly rather than
advertising the vendor SLA it cannot meet.

**No LLM inference at any step. The entire product is algorithmic.**

### D.4 Determinism class

**deterministic.** The hash covers the full payload plus the contract block,
excluding assembled_at. Same anchor, same graph snapshot, same policy
version → byte-identical payload.

### D.5 Replay statement and replay test

**Replay statement.** Given the lineage record, the replay engine re-reads
the entity at graph_snapshot_at, reloads the recorded policy_version,
re-runs both operators, and **asserts hash equality**. No model is invoked
and no computation is performed, so reproduction is exact. **This is the
product against which the replay harness itself should be tested**, before
any product with real assembly logic depends on it.

**Falsifiable replay test.**

1. Serve the product. Record graph_snapshot_at and payload_hash.
2. Land the next vendor file, changing the entity's registration status.
3. Re-derive live → the **new** status returns, and the hash differs.
4. Re-derive at the recorded graph_snapshot_at → the **original** status
   returns and the hash **matches byte-for-byte**.

If step 4 returns the new status, the snapshot is not load-bearing and
graph_snapshot_at is decorative. Because every other product's replay is
validated through the same harness, this test failing here invalidates the
replay claim catalog-wide.

### D.6 Emitted contract

```json
{
  "product": "reference.counterparty.v1",
  "semantic_version": "1.0.0",
  "payload": {
    "entity_id": "5493001KJTIIGC8Y1R12",
    "anchor_type": "LEI | INTERNAL_CLIENT_ID",
    "lei": "string(20)|null",
    "internal_client_id": "string|null",
    "legal_name": "string",
    "legal_jurisdiction": "ISO 3166-2",
    "entity_status": "ACTIVE | INACTIVE",
    "registration_status": "ISSUED | LAPSED | PENDING_TRANSFER | RETIRED",
    "next_renewal_date": "date|null",
    "entity_legal_form_code": "string|null",
    "legal_address": {
      "line1": "string", "city": "string", "region": "string",
      "country": "ISO 3166-1", "postal_code": "string"
    },
    "headquarters_address": { "...": "same shape" },
    "industry_classification": "string|null",
    "fiscal_year_end": "MM-DD|null",
    "internal_overlay": {
      "included": true,
      "internal_risk_grade": "string|null",
      "coverage_rm_id": "string|null",
      "coverage_team": "string|null",
      "coverage_lob": "string|null",
      "kyc_verification_state": "VERIFIED | DUE | OVERDUE|null",
      "kyc_verified_date": "date|null"
    },
    "ontology_types": [
      "cmns-org:Agent", "cmns-org:Party", "cmns-org:Organization",
      "cmns-org:FormalOrganization", "cmns-org:LegalPerson",
      "cmns-org:LegalEntity", "fibo-be-le-cb:Corporation"
    ],
    "identity_authority": {
      "legal_name": "LEI_REFERENCE_DATA",
      "legal_jurisdiction": "LEI_REFERENCE_DATA",
      "registration_status": "LEI_REFERENCE_DATA",
      "internal_risk_grade": "INTERNAL_CREDIT_SYSTEM",
      "coverage_rm_id": "CRM"
    },
    "freshness_ceiling_class": "VENDOR_24H | INTERNAL_KYC_CADENCE"
  },
  "contract": {
    "assembled_at": "<iso8601>",
    "expires_at": "<source publication + 24h, or KYC date + cadence>",
    "ttl_anchor": "from_entity_freshness",
    "ttl_basis": "VENDOR_PUBLICATION | KYC_VERIFICATION",
    "assembly_mode": 1,
    "determinism_class": "deterministic",
    "freshness": [
      { "signal_class": "vendor_identity", "observed_at": "<iso8601>",
        "lambda_c_hours": 8760, "relevance": 1.0 },
      { "signal_class": "registration_status", "observed_at": "<iso8601>",
        "lambda_c_hours": 720, "relevance": 0.97 },
      { "signal_class": "internal_risk_grade", "observed_at": "<iso8601>",
        "lambda_c_hours": 2160, "relevance": 0.91 }
    ]
  },
  "lineage": {
    "operators_invoked": [
      "ResolveOperator@entity-master.v1.0",
      "PolicyOperator@entitlement-jurisdiction.v1.0"
    ],
    "graph_snapshot_at": "<iso8601>",
    "policy_version": "<version>",
    "projection_plan_id": null,
    "model_record": null,
    "payload_hash": "<sha256 over payload + contract, excluding assembled_at>",
    "claim_sources": {
      "vendor_identity": ["lei-reference:<file-date>"],
      "public_filing_reference": ["filings-reference:<file-date>"],
      "internal_overlay": ["<sor>:<record-id>"]
    }
  },
  "context_debt": {
    "F": 0.97, "C": 1.0, "S": 1.0, "D_c": 0.03,
    "contributions": [
      { "component": "registration_status", "dimension": "F", "value": 0.97,
        "reason": "vendor file age 9h against lambda_c 720h" }
    ]
  },
  "notices": []
}
```

`extra=forbid` is enforced as a build-time CI invariant.

### D.7 Validation gates

**Universal.** Empty-operator guard · lineage strict equality · TTL bounds ·
debt gate · suppression silence · classification containment.

**Product-specific.**

| Gate | Assertion | Fixture |
| --- | --- | --- |
| Registration disclosure | An entity whose registration is lapsed, or whose KYC verification is past its refresh due date, is returned with the status as a first-class field, never as a normal-looking record. Under include_lapsed=false the record is excluded entirely rather than returned unflagged | CPR-G01 |
| Crosswalk uniqueness | One LEI resolves to at most one internal client id and vice versa. A many-to-one collision means merged entities or a bad match; fail closed rather than pick one | CPR-G02 |
| Jurisdiction containment | An entity outside the principal's permitted jurisdiction set never materializes, and the payload carries no count, marker or placeholder indicating anything was withheld | CPR-G03 |
| Authority disclosure | Every identity attribute names its authoring source in identity_authority. An attribute with no authority is a defect, not a default | CPR-G04 |
| Freshness ceiling | An entity resolved through the internal client master must not advertise the 24-hour vendor freshness SLA | CPR-G05 |
| Overlay classification | Where include_internal_overlay=false, no confidential-class element appears anywhere in the payload, including in notices | CPR-G06 |
| Type-chain completeness | All seven Commons/FIBO classes are asserted; a partial chain propagates catalog-wide | CPR-G07 |

### D.8 Error mapping

| Condition | Raised at | Response |
| --- | --- | --- |
| Anchor unresolvable | Step 1 | 404 |
| Malformed LEI | Step 1, pre-store | 400 |
| Crosswalk collision | Step 1 | 409 |
| as_of supplied | Parameter validation | 400 not_supported_at_tier |
| Principal not entitled | Step 2 | 403, no detail on what exists |
| Entitlement service unreachable | Step 2 | 503, source class named |
| Debt gate exceeded | Step 3 | 409 with the debt block |
| Internal overlay unavailable | Step 1 | 200 with notices, C reduced |

---

## E · Volatility, debt & materialization

### E.1 Half-life table

| Signal class | λ_c | Calibration basis | Decay driver | Supersession event | Owner |
| --- | --- | --- | --- | --- | --- |
| Legal name, jurisdiction, legal form | ~365 days | illustrative | Reorganization only | Vendor delta; client-master amendment | [TBC] |
| Addresses | ~180 days | illustrative | Relocation | Vendor delta; KYC address re-verification | [TBC] |
| Registration status / renewal date | ~30 days | expert — driven by the annual renewal cycle | Renewal cadence | Vendor delta (cascading) | [TBC] |
| KYC verification state | ~180 days | expert — refresh cycle is risk-rating driven, so this is a blended figure and should be split by rating band once measured | Refresh cycle | KYC refresh completion | [TBC] |
| Internal obligor risk grade | ~90 days | expert — quarterly rerating, off-cycle on trigger | Rerating cadence | Rerating event (cascading) | [TBC] |
| Coverage assignment | ~180 days | illustrative | Coverage reorganization | CRM assignment change | [TBC] |

**No row is measured.** That is the honest state at draft, and the
observability set in §G is what moves them. These values are a calibration
proposal; the binding values live on the Control Plane as versioned Policy
configuration.

### E.2 Debt model and per-component debt

`D_c = 1 − (F · C · S)`, multiplicative.

- **F** — age of the authoring source against its class λ_c, **normalized
  over required classes**, with the ceiling reduced for internally-authored
  entities per §C.4
- **C** — fraction of contract-declared attributes populated, weighted by
  whether the overlay was requested
- **S** — agreement between vendor legal name / jurisdiction and internal
  client master for the same entity. A name-variant or jurisdiction mismatch
  is the Tier 1 semantic-consistency check and **the earliest warning of a
  bad crosswalk match**

`debt_tolerance` default **0.25 — provisional and unbacked**; set against
measured crosswalk match confidence before certification.

| Component | May be absent? | D_c contribution | Behaviour when absent |
| --- | --- | --- | --- |
| Vendor identity attributes | No | — | Fail closed → 404 |
| Entitlement decision | No | — | Fail closed → 503 |
| Registration status / renewal date | No | — | Fail closed — an identity with no status is not a snapshot |
| Public filings reference (industry, FYE) | Yes | 0.10 | Serve with flag; downstream filing-based products escalate |
| Internal overlay — grade, coverage | Yes | 0.30 | Serve, overlay fields named absent, C reduced |
| KYC verification date | Yes | 0.25 | Freshness ceiling becomes unassertable — serve with freshness_ceiling_class unresolved and F reduced |
| Crosswalk entry for an internal-id anchor | Yes | 0.00 | Expected path for no-LEI entities; sets identity_authority, contributes no debt |

The last row matters: a crosswalk miss on a private borrower is **not** a
degradation, and scoring it as one would penalise the entire Commercial
Banking population for a structural property of the anchor.

### E.3 Materialization posture

**Materialized.** Slow decay against the highest read frequency in the
catalog. The 30-day registration-status row is the fastest mover and sits
far outside the 24-hour TTL, so no field needs carving out. Revisit if a
faster identity signal is added.

**Cache key:** tenant + schema name + entity_id + anchor_type +
graph_snapshot_at + principal binding + include_internal_overlay. The
overlay flag is part of the key: omitting it would serve a confidential
payload to a caller that asked for it to be suppressed.

### E.4 Supersession triggers

| Trigger | Scope | Downstream |
| --- | --- | --- |
| Vendor file delta on the entity | cascading | Every consumer in §B.4 — a lapsed registration invalidates every product that resolved through this identity |
| Internal rerating | cascading | credit-risk.* |
| KYC refresh completion | cascading | compliance.*, plus local |
| Coverage assignment change | local | — |

Re-derivation is **lazy**: mark invalid for next request. Eager
re-materialization on a daily vendor delta would re-derive the entire
catalog every morning.

---

## F · Source binding & readiness

| Element | System of record | Interface & cadence | Available today | Gap owner | Blocker |
| --- | --- | --- | --- | --- | --- |
| LEI Level 1 attributes | LEI reference data | Daily concatenated file | yes | — | Confirm licensed distribution path into the fabric |
| Registration status / renewal | LEI reference data | Daily file | yes | — | — |
| Public filings reference | Public filings feed | Daily | yes | — | Coverage limited to registrants |
| Legal identity, no-LEI entities | Internal client master | [TBC] batch vs CDC | partial | Client data owner | Attribute completeness and verification-date availability unknown |
| Client id ↔ LEI crosswalk | Internal client master | [TBC] | partial | Reference data owner | Coverage and match confidence unmeasured — the largest correctness risk in the catalog |
| KYC verification state | Internal client master | [TBC] | partial | Financial crimes data owner | State may be available without the verification date; the date is what the freshness ceiling needs |
| Internal obligor risk grade | Internal credit system | [TBC] | yes | — | Confirm rerating event availability, not just current state |
| Coverage assignment | CRM | [TBC] | yes | — | — |
| Principal entitlement scope | Enterprise entitlement service | Runtime call | partial | Identity and access owner | Jurisdiction-level scoping may not exist at the required granularity |
| Ontology / IRI binding artifact | Data architecture | Published artifact | yes | — | Commons namespace must load alongside FIBO |
| ex: extension namespace | — | — | no | Data architecture | Governance and owner not established; inherited by every product |

**Access path.** No new source system required. Every open item is
interface, cadence, or granularity — **not existence**.

**Identifier reality.** The gating question for the whole catalog, to be
answered before any Tier 2 spec is finalized. Three measurements:

- LEI coverage as a share of the active CB/CIB obligor book
- Crosswalk match-confidence distribution
- Count of many-to-one collisions in the current crosswalk

If Commercial Banking LEI coverage is materially below the CIB rate — the
expected result — the dual anchor is **mandatory rather than defensive**,
and the identity authority hierarchy becomes a governed artifact rather than
a table in this spec.

**History depth.** No as_of advertised at Tier 1. The daily vendor file is a
snapshot with no native history, so any future Tier 3 reconstruction depends
on the fabric retaining deltas from ingestion forward. **Retention has not
started. Start it now** — history not captured cannot be reconstructed
later, and this is a decision that costs almost nothing today and is
unrecoverable if deferred.

**Text-source boundary.** None. Every element arrives structured — the only
product in the catalog with no text-origin element, and part of why it is
the right first build.

**First-build volumetrics.** ~500 legal entities filtered to a workable
corporate set · ~50 anchor obligors carrying the full internal overlay,
being the entities every other product builds on · ≥5 entities in lapsed
registration status so CPR-G01 and the counterfactual test have something to
act on · **≥10 no-LEI entities resolving through the internal client
master**, so the identity authority hierarchy and the freshness-ceiling gate
are exercised rather than described · ≥1 deliberate crosswalk collision in a
test fixture for CPR-G02 · ≥3 principals with differing jurisdiction
entitlement so step 2 is not a no-op · ≥1 name-variant mismatch between
vendor and client master to drive S.

---

## G · Operate & govern

| Entry | Value |
| --- | --- |
| Accountable owner | Product owner: Wholesale Reference Data · data steward: Client / entity reference data · policy owner: Identity and access |
| Service objectives | p50 <80 ms · p95 <250 ms · volume sized for the sum of every downstream product's resolution step, not for direct consumption · concurrency 200+ · payload <20 KB · absolute cost per call must be measured before any other band means anything — ×1 here is the denominator of the entire cost model |
| Degradation contract | Vendor file stale (delta not landed) → serve last-good, reduce F, surface the publication timestamp in notices; never silently re-stamp freshness. Internal overlay unavailable → 200, overlay fields named absent, C reduced. Entitlement service unavailable → fail closed, 503 — identity without an entitlement decision is not servable. Crosswalk collision → fail closed, 409. Mandatory classes: entity record, registration status, entitlement decision |
| Debt model | See §E.2. debt_tolerance 0.25, provisional and unbacked |
| Observability | Per-operator latency · D_c distribution · gate failures by gate, with CPR-G02 collisions alerting rather than counting · cache hit rate · entitlement denials by jurisdiction · degradation-branch frequency · vendor-delta invalidation volume · share of resolutions taking the no-LEI path, which is the running measurement of the §F identifier question |
| Retention & record of record | Record of record: LEI reference data for external identity attributes; internal client master for no-LEI identity and KYC state; internal credit system for grade. The fabric references and does not replace them. Replay records: compressed tier by default — this product's decisions are resolutions, not adjudications — with full-fidelity retention where the resolution fed a decision later escalated |
| Test fixtures | CPR-F01 LEI anchor, full overlay · CPR-F02 internal-id anchor, no LEI · CPR-G01–G07 gate fixtures · CPR-D01 stale vendor file · CPR-D02 entitlement service down, fail closed · CPR-D03 name-variant mismatch driving S · CPR-R01 replay hash assertion |
| Lifecycle | draft — blocked on the three identifier measurements in §F. Certification of this product is a hard prerequisite for certifying any other product in the catalog · reviewer: platform architecture · no successor |

### G.1 Acceptance criteria

- Contract validates against extra=forbid in CI
- All six universal gates and all seven product-specific gates fire on
  deliberately malformed contracts
- expires_at derives from source publication, never request time — verify
  with a late-day request against an early-morning file
- An internal-client-master entity advertises the KYC cadence ceiling, not
  the 24-hour vendor SLA (CPR-G05)
- Replay test §D.5 step 4 returns the original status and a matching hash
- Counterfactual test §A step 2 refuses to serve past expires_at
- include_internal_overlay=false produces a payload with zero
  confidential-class elements, notices included
- A jurisdiction-excluded entity produces no marker of any kind (CPR-G03)
- All seven ontology classes asserted (CPR-G07)
- as_of returns 400 not_supported_at_tier, never a silent current-state
  answer
- Crosswalk miss on a no-LEI entity contributes zero debt; collision fails
  closed
- p95 ≤ 75 ms at expected read volume, measured under the summed downstream
  resolution load
- Every [TBC] in §F closed with a named owner

**Open decisions blocking build:** crosswalk coverage and match confidence
(largest catalog risk) · KYC verification **date** availability, which the
freshness ceiling depends on · entitlement service jurisdiction granularity
· ex: extension namespace governance.

### G.2 Catalog contribution

**What this product proves that nothing earlier proves:** the contract fires
with nine elements populated, three gates passing and a structured rejection
on failure · TTL exists and is enforced at read time · Policy runs before
assembly even when it does almost nothing · lineage strict equality holds ·
the seven-class type chain is asserted correctly · the replay harness itself
works, against the simplest possible case.

**What it deliberately does not prove:** traversal (Tier 2) · bitemporality
and as_of reconstruction (Tier 3) · passage-level lineage and debt cascade
(Tier 4) · projection Π and federation (Tier 5).
