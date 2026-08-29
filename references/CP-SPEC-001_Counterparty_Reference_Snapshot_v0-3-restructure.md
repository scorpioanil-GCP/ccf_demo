> **PROVENANCE AND SUPERSESSION — READ BEFORE USING THIS FILE.**
>
> This is a verbatim copy, taken 2026-08-29, of the vault article
> `wiki/context-products/content/counterparty-reference-snapshot.md`, which is
> `CP-SPEC-001` **restructured 2026-08-24 from the v0.2/Q019 form** and authored
> to `Context_Product_Specification_Standard_v0-3.md`.
>
> **IT SUPERSEDES `references/CP-SPEC-001_Counterparty_Reference_Snapshot_v2.md`**
> (last review 2026-08-21), which remains in this directory as the earlier form
> and MUST NOT be read as the current spec. The two differ materially: the older
> form carries 11 §C element rows across five systems of record and seven
> product-specific gates with fixture IDs (CPR-G01…G07); this restructure carries
> 4 §C rows across three systems of record and names only the six universal gates.
>
> **WHY THE COPY EXISTS.** `ccf_dataprep`'s `validators/spec_coverage.py` reads the
> vault path, which is OUTSIDE this repository's version control. Without this
> file, nothing in the repo records the text cp-01 was built against, and an edit
> to the vault would silently strand the build's referent. This copy is the
> audit anchor; the vault remains the authoring home.
>
> **THIS FILE IS NOT THE SHIPPED SPEC.** The shipped spec is authored to full
> depth against the Standard's §15 Definition of Done and lives in the example
> tree, as `CP-SPEC-000` does for cp-00. Measured against §15 this document is
> incomplete: no product-specific gates with fixture IDs, no §4.6 emitted
> contract with types, no §5.2 per-component debt table, no §8 envelope
> instance, and no §G observability, fixtures or lifecycle entries.

---

# Counterparty Reference Snapshot — Context Product Specification

**CP-SPEC-001** · authored to [[spec-standard-v0-3]] · restructured 2026-08-24 from the v0.2/Q019 form.

## Front matter

| Field | Value |
|---|---|
| Registry name | `reference.counterparty.v1` |
| Tier | 1 |
| **Assembly Mode** | **1 — pure algorithmic** |
| Cost band | ×1 (the baseline) |
| Lifecycle state | draft |
| Accountable owner | product: Wholesale Reference Data · data steward: client/entity reference data · policy: identity and access |
| Last review | 2026-08-21 |
| What it resolves | A single counterparty to a typed, contract-bound identity snapshot. The minimum viable Context Product: its job is to prove the contract fires, not to demonstrate context assembly. |
| Build order | **First.** Every other product resolves its anchor through this one and inherits its contract machinery, typing decisions and identity authority hierarchy. |

**Capability gate:** none. This is the entry point.

## The four-question test — and the honest result

| # | Question | Answer |
|---|---|---|
| 1 | Does the answer change with **who is asking**, beyond formatting? | **No** — jurisdiction visibility only |
| 2 | Does it have a **validity window** after which acting on it is wrong? | **Yes** |
| 3 | Must it be **reconstructible** with the policy and freshness state that produced it? | **Yes** |
| 4 | Is it **composed at runtime** from sources no schema author pre-joined? | **Partial** — two sources, one join |

> **Two clear yeses, one partial, one no — against a standard that says build only if all four are yes.** The product is admitted **as the catalog's contract-machinery entry point rather than on its own assembly merit**, and it qualifies on the TTL and the replay obligation, not on the composition. That basis is written down so a reviewer can challenge it, which is what the standard asks of a qualified admission. It is worth noticing that the catalog's flagship example is the one product that does not pass its own entry test cleanly.

---

## A · Decision frame

**Decision & trigger.** A relationship manager or credit officer opens a counterparty record and the agent needs a canonical identity before it can do anything else. Every downstream product resolves through this one.

**Consuming principals.** Single role at this tier. Projection `Π` is not exercised — that arrives at T5. The product returns the same shape to every authorized caller.

**Counterfactual failure — contract, not context.** Narrower than the rest of the catalog, and worth stating precisely rather than inflating. A CRM lookup returns the same fields. What it does not return is a **TTL**. The consumer therefore caches the row indefinitely and continues reasoning against an entity whose GLEIF registration status has since lapsed to `LAPSED` — meaning nobody has revalidated that the entity still exists as described. **The failure is not a missing signal; it is a missing expiry.** That is the entire lesson of T1.

**Counterfactual acceptance test.** Serve the product, let the TTL expire, and assert the consumer refuses the cached row. A counterfactual that cannot fail is a rationale, not a test.

---

## B · Contract

| Element | Value |
|---|---|
| **Schema** | `counterparty_reference` — entity: `LegalEntity`; attributes: LEI, legal name, jurisdiction, entity status, registration status, legal form, headquarters and legal address |
| **Freshness SLA** | 24 hours for LEI-registered entities; **KYC refresh cadence — months** for entities resolved through the internal client master. Per signal class, never averaged |
| **TTL** | 24 hours · `ttl_anchor: from_entity_freshness` |
| **Policy Binding** | Entitlement scope only — jurisdiction visibility per calling principal. No regulatory overlay at this tier |
| **Lineage** | `operators_invoked: [Resolve, Policy]` · `graph_snapshot_at` · `policy_version` · `payload_hash` · `context_debt` |
| **Semantic Version** | `v1.0.0` |
| **Discovery** | `reference.counterparty.v1` |
| **Addressability** | `/context-products/reference/counterparty/{anchor}` |
| **Assembly Mode** | **1 — pure algorithmic.** No model is invoked anywhere in the path, which is what makes exact replay possible and makes this the product the replay harness itself should be tested against |

Mode 1 means **§2.3 model-risk annotation does not apply.** That is a consequence of the declaration, not an omission.

> **Schema binding correction — and it propagates.** `LegalEntity` is **not a FIBO term**. It moved to the OMG Commons Ontology Library and binds to **`cmns-org:LegalEntity`**; so do `Agent`, `Party`, and `FormalOrganization`. Only `Corporation` stays in FIBO, as `fibo-be-le-cb:Corporation`. A validator asserting that every type IRI starts with `spec.edmcouncil.org` will reject correct data.
>
> The chain is also not the single line previously published. `LegalEntity` has **two parents** — `FormalOrganization` *and* `LegalPerson` — and reaches `Party` only through them, with no direct axiom. Under Fluree's default no-inference, typing an entity `Party` + `LegalEntity` + `Corporation` leaves it unreachable by a query for `FormalOrganization`, `Organization`, or `LegalPerson`, three roles it genuinely holds. **Type against the full chain in [[fibo-iri-binding]].** Every product in this catalog resolves through this one, so the typing decided here is the typing they all inherit.
>
> **Currency, per term.** Remediation landed 2026-08-17; verified against ledger `fibo-v2` at 16:55. All five party types now carry **500 assertions each on the corrected IRIs** — `Agent`, `Party`, `LegalEntity`, and `FormalOrganization` under Commons, `Corporation` under `fibo-be-le-cb:`. The earlier caveat that the estate still asserts pre-Commons IRIs is **withdrawn**: bind against this article and expect the estate to agree.
>
> **The target is decided (2026-08-17):** Commons loads as a second T-Box and every party entity is typed against the **full seven-class chain** — `Agent`, `Party`, `Organization`, `FormalOrganization`, `LegalPerson`, `LegalEntity`, `Corporation` — because under no-inference each is a separate query key. Writing this product to the interim shape would propagate the gap catalog-wide.

**Request parameter surface**

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `anchor` | LEI string(20) **or** internal client id, required | anchor — see §C identity authority | — |
| `intent` | enum, required | selects policy envelope | — |
| `include_lapsed` | bool | filter | `false` |

No parameter is declared-but-inert. **A parameter that appears to work and does not will be relied on in a dispute.**

**Prerequisites.** None. **Consumers:** every other product in this catalog. **Scope boundary:** identity only — no exposure, no grade, no relationship.

---

## C · Data Catalog

| Element | Provenance | Class | Store | `G` |
|---|---|---|---|---|
| LEI, legal name, jurisdiction, entity status, registration status, legal form, addresses | GLEIF **LEI-CDF Level 1** | public | Postgres | `E` |
| Internal client identity for no-LEI entities | internal client master | **synthetic — internal** | Postgres | `E` |
| Entitlement scope by jurisdiction | entitlement service | **synthetic — internal** | Postgres | `P` |
| LEI ↔ internal client crosswalk | internal mapping | **synthetic — internal** | Postgres | `E` |

**Correlation key.** LEI spans every external element; internal client id keys the bank-side overlay. **The crosswalk is the product** — nothing joins without it, and its coverage and match confidence bound the correctness of every downstream product. Measured coverage: **`[TBC]` — owner: client reference data.**

**Single-writer discipline.** LEI reference data writes external identity attributes; the internal client master writes no-LEI identity and KYC state; the internal credit system writes grade. **No element is written by two systems.** Where an attribute exists in both a client master and a downstream warehouse, the client master is authority and the warehouse becomes a read replica — **a prerequisite to build, not a follow-up.**

### Identity authority hierarchy — the Tier 1 design decision

Anchoring exclusively on LEI works for CIB counterparties and public Commercial Banking obligors. **It does not work for the privately-held middle-market borrowers who make up a large share of the Commercial Banking book and have no LEI at all. An LEI-only anchor silently excludes them, and every downstream product inherits the exclusion.**

| Entity class | Identity authority | Registration status source | Freshness ceiling |
|---|---|---|---|
| LEI-registered (public, most CIB) | LEI reference data | vendor registration status and renewal date | 24 hours |
| Private, no LEI | internal client master | internal KYC verification state | KYC refresh cadence — **months** |
| Foreign private | internal client master + local registry where available | internal KYC verification state | KYC refresh cadence — **months** |

An entity resolved through rows two or three carries a materially lower ceiling on `F`, and **that asymmetry is stated in the payload rather than averaged into a single freshness claim.** A single "24 hours" over a mixed population is the exact error the standard's per-signal-class rule exists to prevent.

---

## D · Assembly Recipe

**Client call**

```
GET /context-products/reference/counterparty/5493001KJTIIGC8Y1R12
      ?intent=kyc-review&include_lapsed=false
```

| # | Operator | Store | Emits | Failure |
|---|---|---|---|---|
| 1 | **Resolve** | Postgres | `entity_id`, identity authority class | fail closed → `404` |
| 2 | **Policy** | Postgres | `policy_version`, entitlement decision | fail closed → `503` |
| 3 | Contract assembly | — | payload, lineage, `payload_hash`, `context_debt` | — |

Two operators from the closed vocabulary plus contract assembly. **No bespoke logic in any step** — a spec describing bespoke logic instead of an operator composition has moved cost from the platform to the product.

**Determinism class:** fully deterministic. **Replay:** the engine re-reads the entity at `graph_snapshot_at`, reloads `policy_version`, re-runs both operators and **asserts hash equality**. No model is invoked, so reproduction is exact.

**Falsifiable replay test.** Serve the product and record `graph_snapshot_at` and `payload_hash`. Land the next vendor file changing the entity's registration status. Re-derive **live** → the new status returns and the hash differs. Re-derive **at the recorded snapshot** → the original payload returns and the hash matches. A replay that cannot produce a differing hash is not demonstrating replay.

**Validation gates.** Empty-operator guard · lineage strict equality · TTL bounds · debt gate · suppression silence · classification containment.

---

> **Section note for consumers parsing §-headings.** This is the first spec authored to [[spec-standard-v0-3]], whose skeleton differs from the twenty specs still on the Q019 form. **§A–§D match** (`Decision frame`, `Contract`, `Data Catalog`, `Assembly Recipe`). **§E, §F and §G do not:** v0.3 widens §E to *Volatility, debt & materialization*, **repurposes §F** from *Manufacture envelope* to *Source binding & readiness*, and **adds §G, Operate & govern**, which the older form has no equivalent of. §F is the one to watch — same letter, different meaning, so a consumer reading §F for an envelope will silently get readiness instead.

## E · Volatility, debt & materialization

| Signal class | `λ_c` | Note |
|---|---|---|
| Vendor identity attributes | ~24 h | daily concatenated file |
| Registration status | ~24 h | the field that lapses |
| Internal KYC state | months | sets the ceiling for no-LEI entities |

λ_c values are **proposed here and fixed in Control Plane configuration** — a spec does not set them.

**Debt model.** `D_c = 1 − (F · C · S)`, multiplicative.

- **F** — age of the authoring source against its class λ_c, normalized over required classes, **with the ceiling reduced for internally-authored entities**
- **C** — fraction of contract-declared attributes populated, weighted by whether the overlay was requested
- **S** — agreement between vendor legal name/jurisdiction and the internal client master for the same entity. **The earliest warning of a bad crosswalk match**

`debt_tolerance` default **0.25 — provisional and unbacked**; set it against measured crosswalk match confidence before certification. Per the standard, certification is where λ_c and debt tolerance stop being illustrative and become measured.

**Materialization posture:** derived on demand. Cost band ×1. **Supersession:** next vendor file touching the entity; internal KYC state change.

---

## F · Source binding & readiness

| Item | Status | Owner |
|---|---|---|
| Crosswalk coverage and match confidence | `[TBC]` | client reference data |
| `debt_tolerance` calibration | `[TBC]` — provisional 0.25 | product owner |
| Warehouse → client-master read-replica conversion | prerequisite to build | data engineering |

Every `[TBC]` above carries a named owner. **A spec with honest gaps is buildable; a spec with invented system names is not.**

---

## G · Operate & govern

**Acceptance criteria.** The TTL refusal fires; the replay test produces both a differing and a matching hash; a no-LEI entity resolves and reports the lower freshness ceiling in the payload; `payload_hash` is stable across identical requests.

**Degradation.** Entitlement service unavailable → `503`, never a permissive default. Vendor file late → serve with elevated `D_c` and an explicit staleness marker, or refuse above `debt_tolerance`.

---

## Key Takeaways

- **Assembly Mode 1, declared.** No model touches the path, which is what makes exact replay possible — and makes this the product the replay harness itself should be tested against before any product with real assembly logic depends on it.
- **The failure this product exists to prevent is a missing expiry, not a missing signal.** A CRM lookup returns the same fields without a TTL, so the consumer caches an entity whose registration has since lapsed.
- **An LEI-only anchor silently excludes privately-held middle-market borrowers**, and every downstream product inherits the exclusion. The identity authority hierarchy is the Tier 1 design decision.
- **Freshness is 24 hours or months depending on which authority resolved the entity**, and the asymmetry is carried in the payload rather than averaged into one claim.
- **The crosswalk is the product.** Its coverage and match confidence bound every downstream product's correctness, and both are currently `[TBC]`.
- **It does not pass its own entry test cleanly** — one no, one partial — and is admitted on a written basis: contract machinery, not assembly merit.
- **`debt_tolerance` 0.25 is provisional and unbacked**, and stays that way until measured against crosswalk confidence.

## Related

- [[spec-standard-v0-3]] — the format contract this spec instantiates
- [[ccf-sdk-de-requirements]] — the SDK requirements this worked example tests
- [[fibo-iri-binding]] — the seven-class typing chain §B binds against
- [[corporate-family-tree]] · [[kyc-refresh-beneficial-ownership]] — the first products to resolve through this anchor
- [[../../cognitive-context-fabric/content/context-as-product]] — the contract this instantiates
