> **Current operations:** use [the refreshed implementation walkthrough](CP02_FACILITY_TERMS_SNAPSHOT.md) and Fluree **4.2.4** where required. The embedded specification remains historical evidence at its stated pin.

> **Reading copy:** use [the HTML edition](CP02_FACILITY_TERMS_SNAPSHOT_ANALYSIS.html) for reliably rendered tables. Sources are included below, so reviewing them does not require opening GitHub.

# CP-02 — Facility Terms Snapshot — Analysis

**From the banking problem to CP-SPEC-002**  
**Audience:** Subject Matter Expert (SME) and Information Architect  
**Status:** approved by the user; persisted to `ccf_adoption/main` on 2026-10-08

The destination of this journey is the example's own final specification: **`examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md`** in `drcastillo/ccf_code`. Every design choice below is traced to that document. The Standard supplies the template; CP-SPEC-002 supplies the completed example of the reasoning we are learning to perform.

The SDK sources were checked at **`4494b93621bb252154f2fd7dc304a71290394ee8`**. The final spec includes its original authoring record, later corrections, explicit findings and unresolved placeholders. Those remain part of the account; this companion does not replace them with newly chosen requirements. The banking context comes from the supporting Vault article. Exact source snapshots are included in this file so they can be read without following a GitHub link.

## 1. Start with the decision a banker must make

A credit officer receives a drawdown request, reviews an amendment, or prepares an annual renewal. Before assessing the request, the officer needs the economic and structural terms of **the particular credit facility**: its type, commitment, currency, effective date, maturity, pricing grid, administrative agent and borrower. These terms usually originate in a credit agreement, but the consuming application needs a typed answer it can use consistently.

The first discussion between the SME and Information Architect establishes the unit of work. The bank may have several facilities for one borrower. Resolving the borrower alone does not identify which agreement, commitment or pricing schedule governs this request. The SME therefore identifies the **facility** as the decision's anchor. The architect retains `borrower_lei` as a separate link to the legal entity. That distinction produces the internal `facility_id` anchor in **§C.3** and the facility-specific address in **§B.1**.

The next question is temporal: *what makes this answer valid, and which event starts its validity window?* Repeating the same question later must not give unchanged agreement terms a new expiry. The specification therefore teaches `ttl_anchor: from_entity_freshness`, with expiry derived from the facility's dated source. The exact basis selected in CP-SPEC-002 is **`effective_date` plus 90 days**. Its consequences and the unavailable amendment-date alternative are deliberately recorded in the spec.

The product supplies terms and evidence for the officer's decision. Scope remains one facility's snapshot; exposure aggregation, covenant history and collateral analysis belong to other products. This gives the SME a concrete boundary to explain before the architect starts filling the template. [Final spec: §A, §B.5 and §C.3](#source-spec)

## 2. Establish the specification frame — Standard §0 → CP-SPEC-002 §0

The SME contributes the decision, consumer, scope and business meaning. The Information Architect joins that account to the actual data estate and turns it into a contract engineers can implement. CP-SPEC-002 is the **SDK-level specification**, so it names PostgreSQL, schema and tables. Deployment hosts, ports and credentials belong in environment configuration rather than the spec.

This follows the [generation recipe's distinction between the two specification levels](#source-recipe): the Vault explains what the product is; the example's SDK spec explains how that product is specified against a particular estate. Use both, while keeping the example spec as the destination of this walkthrough.

| Template entry | How the banking discussion becomes the final entry |
|---|---|
| Registry, tier and cost | A single facility snapshot over structured records becomes `reference.facility.v1`, Tier 1, cost band ×1. |
| Assembly mode | Lookup, policy evaluation and arithmetic require no model: **Mode 1 — pure algorithmic**. |
| Accountable owners | Wholesale Lending owns the product; loan operations / agency stewards the data; identity and access owns policy. |
| Capability | One runtime capability class, `relational`, with date arithmetic available in the read path or assembler. |
| Prerequisite | `counterparty-reference-snapshot`: the borrower LEI must resolve. |
| Admission record | The final spec's §0.1 retains `[TBC — vault]` for the four-question test and registers it in §F.2 row 1. It explains why this did not block the example's build. |

The spec labels its estate honestly. Public agreement terms coexist with synthetic internal balances, ratings, pricing margins and identifier crosswalks. The figures used below are the spec's recorded measurements of that teaching estate, principally dated **2026-08-29**; they are not claims about an actual bank's loan book and were not rerun for this companion. [Final spec: opening data banner and §0.4](#source-spec)

## 3. Write the decision frame — Standard §A → CP-SPEC-002 §A

The SME now writes a sentence with a decision, trigger and consumer: **a credit officer reviewing a drawdown, amendment or annual renewal needs the facility's current terms as a typed object**. This becomes the final spec's decision frame.

Then ask what could go wrong even if every term were populated. The answer is the wrong TTL anchor. A validity window derived from when the question was asked changes as the question moves. CP-SPEC-002 instead attaches expiry to the instrument's source date. Its proposed taxonomy label is `temporally-incoherent`; the spec retains the original `[TBC — vault]` ruling marker in §A and §F.2 row 2.

The architect turns that narrative into a comparison the build can test:

| Part of the counterfactual | Final specification entry |
|---|---|
| Query | A facility request with `intent=drawdown-review`. |
| Baseline answer | Terms from a document lookup or loan-system screen. |
| Context Product answer | Those terms plus `expires_at`, `ttl_anchor`, `ttl_basis`, lineage and context debt. |
| Controlled change | Ask for the same facility at two different `asked_at` instants while source state remains fixed. |
| Failure condition | `expires_at` moves when only `asked_at` moves. |
| Evidence to produce | Counterfactual fixture **FTS-F01**, also defended by **FTS-G01**. |

This is why the spec needs more than a field list. The analyst has identified a banking failure and converted it into an assertion that can fail. Caller entitlement changes which facilities are visible; the product does not introduce role-specific projection at this tier. [Final spec: §A](#source-spec)

## 4. Turn the decision into a contract — Standard §B → CP-SPEC-002 §B

### 4.1 Fill the nine contract elements

For each element, connect a consumer need to the exact value chosen in the final spec.

| Element | Reasoning from the banking need | Final spec §B.1 |
|---|---|---|
| Schema | The officer needs one facility's economic and structural terms, tied to its borrower. | `facility_terms`, entity `CreditFacility`; facility type, commitment, currency, effective and maturity dates, pricing grid, administrative agent, borrower LEI and amendment number; no relationships. Schema artifact: `docs/schemas/facility_terms.v1.json`. |
| Freshness SLA | Amendments can supersede agreement terms. | Amendment-driven; the inability to evidence amendment dates is recorded in §C.4. |
| TTL | The validity window belongs to source state. | **90 days**, `from_entity_freshness`; the chosen basis is developed in §D and §E.5. |
| Policy binding | Jurisdiction permission alone does not establish facility need-to-know. | Borrower jurisdiction visibility **and** facility-level need-to-know. |
| Lineage | A consumer needs to trace the answer to the assembly and policy state. | `[Resolve, Policy]`, `graph_snapshot_at`, `policy_version`, `payload_hash`, `context_debt`; `projection_plan_id` and `model_record` are null. |
| Semantic version | Consumers need an explicit contract version. | `v1.0.0`. |
| Discovery | The product must be addressable by its registered name. | `reference.facility.v1`. |
| Addressability | The request identifies one facility. | `/context-products/reference/facility/{facility-id}`. |
| Assembly mode | The derivation is algorithmic. | **1**; §B.3 states that model-risk annotation is not applicable. |

The schema artifact is a build-owned placeholder in the spec. The value and location are specified before the artifact is produced. This teaches the distinction between agreeing a contract and supplying evidence that the build implements it. [Final spec: §B.1–§B.3](#source-spec)

### 4.2 Specify what the caller may ask

The architect maps each request parameter to what it changes. CP-SPEC-002 contains **five parameters**, including one that must reject use at this tier.

| Parameter | Final type and requirement | Meaning and final behavior |
|---|---|---|
| `facility_id` | String, required | Moves the entity anchor **E**; no default. |
| `intent` | Enum, required | Selects the policy envelope **P**; no default. The worked call uses `drawdown-review`. |
| `debt_tolerance` | Float, required in the declared surface | Sets the request's debt tolerance; the listed default **0.25** is expressly provisional and unbacked, assigned to P8 calibration. |
| `include_pricing_grid` | Boolean | Changes payload shape; default **true**. False omits the grid entirely. |
| `as_of` | Timestamp, declared but inert | A historical request must return **`400 not_supported_at_tier`**; it cannot silently return current terms. |

The reasoning for `as_of` is specific to this example. Amendment counts show that a history exists, but they do not supply the dates or retained states needed to answer a historical question. The uniform surface therefore declares the parameter and specifies explicit failure. [Final spec: §B.4](#source-spec)

### 4.3 State access, classification and scope

The SME and policy owner distinguish public agreement terms from internal bank overlays. The final product classification is **`internal`**; pricing thresholds are public but the example's margins are synthetic internal values. The information-barrier entry is **`none`** at this tier. Residency and cross-border serving remain `[TBC — identity and access]`. Jurisdiction visibility alone does not settle where a caller may be located.

In §B.5, scope exclusions point readers to the appropriate later product: historical terms and covenants to `covenant-in-force-as-of`; agreement passages to `covenant-cross-reference`; collateral to `collateral-and-setoff-coverage`; exposure rollups to `credit-exposure-rollup`; syndicate composition to `syndicated-lending-co-lender`. A `syndicated` flag in this snapshot does not expand it into a syndicate analysis. [Final spec: §B.2 and §B.5](#source-spec)

## 5. Find the evidence for each claim — Standard §C → CP-SPEC-002 §C

### 5.1 Build the element catalog against the estate

The architect works with the data steward to bind each business fact to its authoritative source and concrete location. In this example, agreement text has already been extracted to structured rows. Runtime assembly reads PostgreSQL; document parsing is a build-time data-preparation step.

| Banking fact or control | Binding recorded in §C.1 | Consequence for authoring |
|---|---|---|
| Type, commitment, currency, effective date, maturity | EX-10 agreement → PostgreSQL `ccf_v2.facility` | Public provenance; date fields also contribute the temporal dimension. |
| Pricing grid | `ccf_v2.facility.pricing_grid`, JSONB | Public tier thresholds plus synthetic internal margins; classify as internal and preserve structure. |
| Administrative agent | `ccf_v2.facility.administrative_agent` | Bind the EX-10 preamble's identity; retain the unresolved ontology marker. |
| Debt reconciliation | 10-K footnote → `ccf_v2.debt_reconciliation` | Supplies the source-agreement dimension of context debt. |
| Amendment number | `facility.amendment_count`, `is_amended_restated` | Counts are available; amendment effective dates receive a separate absent row **7b**. |
| Borrower crosswalk | `facility.borrower_lei` → `ccf_v2.legal_entity` | Synthetic internal crosswalk; 60 facilities resolve across 22 borrowers, zero orphans in the recorded measurement. |
| Balance and undrawn availability | `ccf_v2.facility`, with `balance_as_of` | Internal loan-system signals have their own observation date. |
| Internal rating | `facility.internal_risk_rating` | Synthetic internal overlay, separate from public agreement terms. |
| Entitlement | `ccf_v2.principal`, `ccf_v2.principal_jurisdiction` | An explicit policy source row is necessary for the Policy step to have something to read. |
| Facility taxonomy | FIBO typing in Fluree `fibo-v2`, **not read by CP-02** | The binding vocabulary includes `fibo-fbc-dae-dbt:CreditFacility` in `FBC/DebtAndEquities/Debt/`; do not add a graph dependency to this Tier-1 runtime. |

The final catalog also records provenance, classification, capability class, graph dimension and ontology IRI. Where an IRI is unestablished, the spec uses `[TBC — ccf_dataprep]`; it does not invent a binding. The facility identifier is internally authoritative and unique in the measured estate. There is no external facility registry to resolve an unknown ID. [Final spec: §C.1 and §C.3](#source-spec)

### 5.2 Ask whether the store can preserve the meaning

The capability decomposition in §C.2 asks five concrete questions: can the estate query sets, perform date arithmetic, prefix-match jurisdiction grants, preserve the nested pricing-grid structure, and represent null dates and amounts? This converts “relational support” into properties the implementation can check.

For example, a `US` grant must match borrower codes such as `US-DE`. Exact matching would drop facilities the intended prefix grant includes. A pricing grid stored as a scalar would discard the leverage conditions that determine the margin. The specified interim posture for an unavailable structured grid is a `NOT_EVALUABLE` claim, rather than a substitute headline margin.

### 5.3 Use the four data traps to finish the design

These are the discoveries that make CP-02's journey specific. Each measurement changes what the spec promises.

| Discovery in §C.4 | SME interpretation | Choice carried into the final spec |
|---|---|---|
| Four facilities have maturity before effective date; all share one source accession. | A common extraction defect does not establish a negative loan tenor. | Preserve the source dates; `tenor_days` is null and `NOT_EVALUABLE`. **FTS-G08**. |
| Forty-three facilities carry amendments, but `ccf_v2` contains amendment counters and no amendment effective dates. | A count cannot establish when changed terms took effect. | Serve `amendment_count`; claim no amendment date. Name `effective_date` as `ttl_basis` and record the freshness consequence. **§E.5, §F.4 findings 1–2**. |
| Source accession, document and offsets exist on all 60 facility rows. | Available data does not automatically belong in the product's scope. | Exclude these fields from payload and lineage; document passages remain a later capability. **FTS-G06**. |
| `pricing_grid` is an object containing `tiers`, not an array itself. | Checking the outer object would falsely report missing tiers. | Read `pricing_grid->'tiers'`; serve `basis` plus the typed tier list. All 59 populated grids have at least three tiers. **FTS-G07**. |

The method is to ask whether the measurement answers the business question. Column presence does not prove amendment chronology; a populated numeric value does not prove a valid tenor; and a populated grid column does not prove the pricing conditions survived. [Final spec: §C.2–§C.4](#source-spec)

## 6. Describe how the answer is assembled — Standard §D → CP-SPEC-002 §D

### 6.1 Write the call and ordered recipe

The completed client call in §D.1 is:

```text
GET /context-products/reference/facility/FAC-08D5BB
    ?intent=drawdown-review&include_pricing_grid=true&debt_tolerance=0.25
```

The SME explains the consequences of a missing facility, denied access or unusable terms. The architect expresses the derivation as two operators followed by contract assembly:

| Step | Inputs and output in the final spec | Why it is needed |
|---|---|---|
| 1 — Resolve | Internal `facility_id` → facility terms, `borrower_lei`, `ttl_basis` | Establish the instrument and name the source date before computing validity. Unknown facility fails closed. |
| 2 — Policy | Borrower jurisdiction grants and `sees_need_to_know` → permissible facility set and `policy_version` | Both conditions determine access; entitlement unavailability cannot become permission. |
| 3 — Contract assembly | Resolved, permitted terms plus declared TTL and lineage → contract, expiry, hash and debt | Compute and validate the consumer's answer. This terminal step is not a `Compose` operator. |

The final operator table adds an SDK-mechanism column to the Standard's seven-column form. It maps Resolve to the L2 assembly worker/entity-resolution machinery, Policy to L4 `PolicyFilter`, and contract validation to L6 `run_gates`. Latency budgets remain build-owned placeholders. Those mappings are the handoff to the [implementation walkthrough](#source-implementation).

Policy illustrates why one test is insufficient. The research principal has jurisdiction visibility over all 60 facilities but no need-to-know. A jurisdiction-only implementation would look discriminating while granting unintended access. **FTS-G03** therefore removes the need-to-know condition and requires the served set to change. With both conditions applied, three principals have empty sets and **three of six principal pairs differ**, as corrected in §D.7. The gate requires at least one differing pair and a same-principal negative control; it does not require every pair to differ. [Final spec: §D.1–§D.3 and §D.7](#source-spec)

### 6.2 Make the expiry derivation visible

CP-SPEC-002 chooses the following calculation:

```text
ttl_basis       = "effective_date"
ttl_basis_value = facility.effective_date
expires_at      = ttl_basis_value + 90 days
```

The contract exposes both the basis name and value so the consumer can check the arithmetic. `asked_at` and extraction `retrieved_at` are not substitutes. The recorded date spread makes **10 of 60** facilities live under that calculation at the pinned 2026-08-29 instant; **50 refuse** on TTL bounds.

This result is part of the final spec's reasoning, not a number to improve while authoring the companion. §E.5 compares `effective_date` with the single extraction date shared by all rows. Using the extraction date would make all 60 live while changing what freshness means. The spec also identifies amendment effective dates as the semantically appropriate alternative that this relational estate cannot supply. It keeps Basis A and records the consequence through **FTS-G09** and §F.4. [Final spec: §B.1, §D.3 and §E.5](#source-spec)

### 6.3 Specify the emitted contract and reproducibility

The architect now turns business meaning into the typed envelope in §D.6. The field placement matters:

| Envelope member | Content the final spec places there |
|---|---|
| Top level | `product: reference.facility`, `semantic_version: 1.0.0`. |
| `payload` | Facility and borrower IDs; type, commitment, currency, effective date, maturity, nullable tenor and agent; amendment count and amended/restated flag; syndicated flag; optional structured pricing grid; balance, undrawn availability, `balance_as_of` and rating. |
| `contract` | Assembly and expiry timestamps, `ttl_anchor`, basis name and value, assembly mode, determinism class, per-signal freshness. |
| `lineage` | Resolve/Policy references, graph snapshot, policy version, null projection/model records, payload hash. |
| `context_debt` and `notices` | F, C, S, D_c, per-claim contributions and the accompanying notices. |

Three dates have three meanings: `ttl_basis_value` dates the agreement basis, `balance_as_of` dates the loan-system signal, and `assembled_at` dates assembly. Keeping them distinct prevents a newly assembled answer from making an old balance appear newly observed.

The hash covers deterministic content, including principal and policy, payload shape and expiry; it excludes `asked_at` and `assembled_at`. The spec's replay procedure **FTS-R01** then requires: serve and record; change commitment; obtain a different live hash; reproduce the original hash from the recorded snapshot; and preserve hash and expiry on a later unchanged live request. The later unchanged request is compared with the preceding live result. Retained history is a named data condition for that test, not an assumption. [Final spec: §D.4–§D.6 and §F.2 row 20](#source-spec)

### 6.4 Derive the nine gates from the decisions

| Gate in §D.7 | Decision it turns into a falsifiable requirement |
|---|---|
| **FTS-G01** | Same facility/source state, different request times: identical expiry. |
| **FTS-G02** | At least one pair of principals has different visible facility sets; same-principal comparison is identical. |
| **FTS-G03** | Removing need-to-know changes the served set. |
| **FTS-G04** | No withheld-content markers; empty entitlement and missing-facility refusals are indistinguishable as specified by the gate. |
| **FTS-G05** | `as_of` returns `400 not_supported_at_tier`. |
| **FTS-G06** | No source accession, document identifier or offsets leak into payload or lineage. |
| **FTS-G07** | Grid remains `basis` plus at least three tiers; no scalar substitution. |
| **FTS-G08** | Inverted dates produce null, non-evaluable tenor. |
| **FTS-G09** | A facility outside the 90-day window refuses on `ttl-bounds`, naming its basis; correcting that declared behavior must make this historical assertion red. |

The spec requires each gate to be deliberately observed failing once. It also distinguishes the three core `run_gates` checks it describes—empty operators, lineage equality and TTL bounds—from other obligations and product-specific proofs. Its later debt-handling amendment must be read with the original debt paragraph; an old `409` statement alone is incomplete. [Final spec: §D.7](#source-spec)

## 7. Explain freshness, debt and caching — Standard §E → CP-SPEC-002 §E

The SME distinguishes what changes on an amendment, a drawdown or a risk review. The architect records separate signal classes rather than assigning one age to the whole payload.

| Signal | Final §E.1 half-life proposal | Basis and design use |
|---|---|---|
| Structural terms | ~540 days | Expert estimate; agreement amendments supersede terms. |
| Pricing grid | ~365 days | Expert estimate; amendment or refinancing can reprice it. |
| Outstanding balance | ~1 day | Expert estimate; drawdown and repayment events change it. |
| Internal rating | ~90 days | Illustrative value; rating actions supersede it. |

The proposals require calibration. They are distinct from the **90-day contract TTL**. The chosen materialization posture is **materialized terms with outstanding balance carved out as on-demand**. The cache key in §E.3 is `(tenant, schema_name, facility_id, principal_id, policy_version, graph_snapshot_at, include_pricing_grid)`. It includes access and shape determinants and omits request time.

Context debt is specified as **`D_c = 1 − (F × C × S)`**. F accounts for signal age against each class's half-life, normalized over required classes; C accounts for populated contract attributes; S uses the declared facility/debt reconciliation. §E.2 decomposes the consequences per claim:

| Evidence condition | Final spec treatment |
|---|---|
| Missing identity/type/borrower, currency, effective date or entitlement | Fail closed according to the mandatory-field and policy rules. |
| Missing commitment, maturity or pricing grid | Permit the specified degraded answer with non-evaluable claims rather than invented values. |
| Incoherent date pair | Preserve dates; tenor is non-evaluable and contributes debt. |
| Missing balance or undrawn availability | Degrade with a flag; balance freshness uses the one-day signal class. |
| Missing reconciliation for eight of the 22 borrowers | S cannot be computed and contributes its full weight as declared. |
| Amendment date absent from the declared payload | No invented date or additional payload claim; the freshness cost is recorded against the original effective-date basis. |

The tolerance **0.25** and numeric per-component contributions remain provisional/build-owned in the final spec. The analyst carries their ownership into §F instead of presenting estimates as calibrated facts.

Finally, §E.4 names invalidations: amendment filing cascades to named dependent products; drawdown/repayment affects the balance locally; borrower identity supersession invalidates joined facilities; entitlement changes affect that principal's cached products. The inability to observe facility-mapped amendment dates remains a recorded source gap. [Final spec: §E.1–§E.5](#source-spec)

## 8. Record readiness and owners — Standard §F → CP-SPEC-002 §F

The question now becomes: *can every declared behavior be built and demonstrated from the evidence available?* Section F answers at element and fixture level. It records 59 of 60 populated commitments and grids, 53 maturities with four further inversions, resolved borrower identities for all 60 facilities, partial debt reconciliation and absent amendment dates. Existing structured data supplies this build; the missing amendment dates are a finding rather than newly assigned acquisition work for CP-02.

The placeholder roster in §F.2 retains **20 numbered entries**. For this journey, the important links are:

| Final roster entries | Why the process produces them |
|---|---|
| Rows 1–2 | The admission test and failure taxonomy are owned by the Vault, so their original pending terms are named. |
| Rows 3–5 | Ontology bindings, residency and cross-border terms require their respective owners. |
| Row 6 | Debt-tolerance calibration belongs to the product owner and data preparation; §G.2 identifies it as a certification condition. |
| Rows 7–16 | Schema, latency, hashes, replay, gate observations, counterfactual results and calibration evidence must be supplied by the build, with the supersession note on row 12 preserved. |
| Rows 17–19 | Amendment dates, a coverage manifest and missing reconciliation rows are specific data requests. |
| Row 20 | Replay needs both a test and a mutable source attribute with retained state; the build and data owner share the obligation. |

This shows how to finish a spec without concealing unavailable evidence. The final §G.2 explicitly reports **no open decision blocking build**; the companion preserves that disposition. It does not turn the recorded findings into new build prerequisites. [Final spec: §F.1–§F.4 and §G.2](#source-spec)

## 9. Finish with operating commitments — Standard §G → CP-SPEC-002 §G

The SME identifies who remains accountable after assembly works. The architect names the observations needed to detect broken commitments: operator latency, debt distribution, all nine gate-failure counts, cache hits, denials split by jurisdiction and need-to-know, TTL refusals and supersession invalidations. Service objectives and retention measurements remain assigned to the build. Public filings and internal loan systems remain the records of record.

The final spec closes with **twelve acceptance criteria**, all derived from earlier decisions:

| §G.2 criterion | What the reviewer must be able to verify |
|---|---|
| 1 | Expiry does not move when only request time moves. |
| 2 | Basis name/value are present and expiry arithmetic checks. |
| 3 | Replay produces a differing hash, a matching historical hash, and a matching later live hash with no source change. |
| 4 | Incoherent dates are preserved while tenor is null and non-evaluable. |
| 5 | Pricing arrives as at least three tiers. |
| 6 | No document identifiers or offsets appear in payload or lineage. |
| 7 | Principal-visible content differs without a structural marker of withheld content. |
| 8 | A zero-entitlement refusal is indistinguishable from the missing-facility refusal. |
| 9 | Need-to-know independently changes the served set. |
| 10 | `as_of` fails explicitly with `400 not_supported_at_tier`. |
| 11 | An expired effective-date basis produces the specified TTL refusal; FTS-G09 turns red when its recorded finding is settled. |
| 12 | Each of the nine gates has been deliberately observed red. |

The spec is now the output of the journey: banking need → facility anchor → contract → source bindings → assembly → freshness and debt → readiness → acceptance evidence. The [implementation companion](#source-implementation) starts from that artifact and follows the SDK realization. [Final spec: §G.1–§G.3](#source-spec)

## Reading the final spec's retained history

Three source-reading notes preserve accuracy without changing the journey:

- The final spec retains Gate-1 lifecycle and `[TBC]` text alongside later corrections. This companion explains those entries and their owners; their presence alone is not a fresh assessment of implementation readiness.
- **§D.3 and FTS-G04/§G.2 are not fully aligned on missing versus withheld response details.** §D.3 describes a missing-facility 404 and withheld 403, while the acceptance gate requires indistinguishable refusals. Both statements are preserved in the included spec. The walkthrough teaches the acceptance requirement without inventing a reconciled HTTP mapping. Likewise, the detailed §E.2 and aggregate §G.1 differ on the status for missing effective date; their common requirement is fail closed.
- The supporting Vault article contains a later correction favoring amendment effective dates and supplies the admission/taxonomy answers. CP-SPEC-002 still explicitly chooses `effective_date` in §E.5 and carries its recorded findings. This companion follows that final example spec; the Vault's later prose is supporting history rather than an unrecorded rewrite of CP-SPEC-002.

## Included references

- [CP-SPEC-002 — the final example specification](#source-spec): the destination and primary authority for this walkthrough.
- [Context Product Specification Standard v0.3](#source-standard): the template being populated.
- [Specification generation recipe](#source-recipe): ownership, authoring and evidence sequence.
- [Vault Facility Terms Snapshot](#source-vault): supporting banking problem and product context, pinned at `df5d8dea5c8b12e4d75662105388306467cd7592`.
- [CP-02 README](#source-readme) and [summary explanations](#source-summary): supporting implementation and teaching context.
- [Adoption CP-02 implementation guide](#source-implementation): the next part of the learning path, retaining its own qualified SDK revision.


## Included source snapshots

These are the exact retrieved source texts at the recorded commits, retained for review. Their historical statuses and internal links have not been edited.

<a id="source-standard"></a>

<details>
<summary>Standard v0.3 — ccf_code@4494b936</summary>

Path: `public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`

``````text
# Context Product Specification Standard

**v0.3** — authoring standard for CB/CIB Context Products

**Status:** draft for Data Engineering review · **Basis:** CCF Whitepaper
v1.1, Ch 6 §§6.2–6.5 and Ch 7 §§7.4–7.10 · **Supersedes:** v0.2
(seven-section skeleton retained; twelve additions listed at §16)

Table of contents (updates when the document opens)

---

## 0 · What this document is

This is the **format contract** for a Context Product specification — not a
specification of any one product. A spec written to this standard is complete
enough that a data engineer can identify the source systems, build the
assembly path, register the product, and operate it without a further design
conversation.

Five rules govern the whole document.

- **A Context Product is not a dataset.** It is a unit of meaning — typed,
  governed, and fit to act on — assembled at request time for one intent, one
  perspective, one moment and one policy envelope.
- **The contract is nine elements, not eight.** Schema, Freshness SLA, TTL,
  Policy Binding, Lineage, Semantic Version, Discovery, Addressability,
  Assembly Mode.
- **Assembly is a composition of named operators over capability classes.**
  A spec describing bespoke logic instead of an operator composition has
  moved cost from the platform to the product, which is the failure mode
  this architecture exists to prevent.
- **The wire format is part of the standard.** Every product returns the
  same response envelope (§10). A consumer that must special-case a
  product's response shape does not have a contract, it has an integration.
- **Every claim in a spec is falsifiable or it is decoration.** *(new in
  v0.3)* A counterfactual, a replay guarantee, a determinism class and a
  validation gate are each stated as a test someone can run and watch fail.
  A spec whose assertions cannot be disproved has documented an intention,
  not a design.

### 0.1 Do you need a Context Product? — the four-question test

Build one only if the answer to **all four** is yes. If any is no, build the
data product and move on; the fabric is expensive precisely because it
carries guarantees a data product does not.

| # | Question | If no |
| --- | --- | --- |
| 1 | Does the answer change with who is asking, beyond formatting? | Build a view |
| 2 | Does the answer have a validity window after which acting on it is wrong? | Build a table with a refresh schedule |
| 3 | Must the answer be reconstructible after the fact, with the policy and freshness state that produced it? | Build a report and archive the output |
| 4 | Is it composed at runtime from sources no schema author pre-joined? | Build the join |

A qualified yes is a legitimate answer, but it must be written down as one.
A product admitted on two clear yeses and two partials is admitted on a
stated basis that a reviewer can challenge.

### 0.2 Placeholder discipline (new in v0.3)

Every unresolved item carries an explicit marker — `[TBC]` — and every
marker appears again in §F with a named owner. **A spec with honest gaps is
buildable; a spec with invented system names is not.** Reviewers should
treat an unmarked assumption as the more serious defect, because a marked
gap gets closed and an invented one gets built.

### 0.3 Section skeleton

| § | Section | Answers | Primary audience |
| --- | --- | --- | --- |
| A | Decision frame | What decision, for whom, and what breaks without it | Product owner, business sponsor |
| B | Contract | The nine elements and the request parameter surface | Consuming agent teams |
| C | Data catalog | Every element, its system of record, and where it lands in G | Data engineering |
| D | Assembly recipe | The operator composition, step by step, with emits, budgets and gates | Data engineering |
| E | Volatility & materialization | Per-signal half-life, debt model, supersession, caching posture | Platform, FinOps |
| F | Source binding & readiness | What exists today, what does not, who owns the gap | Data engineering, source owners |
| G | Operate & govern | Owner, SLOs, degradation, observability, retention, lifecycle | Platform, second line |

The seven sections appear in order, always. A product with nothing to say in
a section writes one line explaining why, rather than omitting the heading —
an absent section reads as an oversight and a short one reads as a decision.

### 0.4 Front matter (new in v0.3)

Before §A, every spec carries: registry name · tier · Assembly Mode · cost
band · lifecycle state · accountable owner · last review date · a
two-sentence statement of what the product resolves · the four-question
build test result · build-order note.

**Capability gate.** Where a product cannot be built at all without a
capability the estate may not have, that fact is stated **above §A**, not
discovered in §C. This is a scheduling decision, not a build detail: a spec
whose blocking dependency is buried is a spec that gets scheduled and then
stalls.

---

## 1 · Section A — Decision frame

**Decision & trigger.** The decision, the role taking it, and the event that
triggers the request, in language a business sponsor recognizes. Where a
product serves several distinct triggers that ask genuinely different
questions, tabulate them and name which axis each exercises — the forensic
and the live case are not the same request wearing different parameters.

**Consuming principals.** Every role that will call the product, and whether
each receives **materially different assembled content** — not different
formatting. Different content means a projection plan (§13.2); different
formatting belongs to the consuming application.

**Counterfactual failure.** What a conventional data product returns for
this decision and why it is wrong. Name the failure mode from the closed
taxonomy: **context-starved · temporally-incoherent · perspective-flat ·
policy-blind · evidence-free**. If you cannot write a counterfactual a
skeptical engineer accepts, the product does not belong in the catalog yet.

**Counterfactual acceptance test** *(new in v0.3)*. The counterfactual is
written as an executable test, not a narrative. State the query, the two
answers, and the condition under which they must differ. Where they agree,
the product is not doing the work the counterfactual claims for it — and
this is exactly the check a reviewer should be able to run on the built
product rather than accept on assertion.

**Primitive taught** *(optional, catalog coherence)*. Where the product is
the clearest instance of one architectural primitive, name it — the catalog
is also a teaching sequence, and a product that teaches nothing new is a
candidate for merger with its neighbour.

**Contrast pointer** *(optional)*. Where a sibling product makes the
opposite design choice on the same axis, name it and the axis. Two products
with opposite `ttl_anchor` values teach the anchor better than either does
alone.

---

## 2 · Section B — Contract

### 2.1 The nine elements

| Element | What to write | Common error |
| --- | --- | --- |
| Schema | Named payload type; entities, relationships, attributes and measures, each bound to an ontology IRI. Link the machine-readable schema artifact. | Prose in a table cell with no artifact. Prose is not a contract. |
| Freshness SLA | Per signal class, not one value for the product. | One "intraday" over a payload mixing intraday and annual signals. |
| TTL | Duration plus ttl_anchor: from_decision or from_entity_freshness. Where the product carries a dual TTL, state both branches and the condition that selects them. | Anchoring by habit rather than by decision shape. |
| Policy Binding | Every regime and internal policy constraining construction, each with a resolvable version id; entitlement scope bound to the actual entitlement service; data classification and residency constraints (§2.2). Where policy must be pinned to a past date, say so here and enforce it in §D. | Asserting "entitlement scope" with nothing behind it. |
| Lineage | operators_invoked[] · graph_snapshot_at · policy_version · projection_plan_id · passage anchors where any claim rests on text · context_debt · payload_hash · model_record for Mode 2/3. | Omitting context_debt; it is an output of every assembly. |
| Semantic Version | vMAJOR.MINOR.PATCH, prior supported version, migration window, and the change class rules at §14. | A version with no stated migration window. |
| Discovery | domain.product.vN. | Registering before §G is complete. |
| Addressability | URL pattern with a resolvable anchor identifier. | Anchoring on an internal surrogate key. |
| Assembly Mode | 1 pure algorithmic · 2 algorithmic with LLM packaging · 3 algorithmic orchestration with agent-swarm assembly, with a one-sentence cost/quality/determinism rationale. Modes 2 and 3 additionally require the model-risk annotation at §2.3. | Omitted entirely. |

**Assembly Mode is a registration-time commitment.** The product owner settles
it, with a stated rationale, when the product class is registered. **It is not
something the assembling agent works out for itself, and it cannot vary between
calls.** Changing it is a MAJOR change (§14).

### 2.2 Classification and residency

State, inside Policy Binding:

| Field | Values |
| --- | --- |
| Data classification | public · internal · confidential · restricted — highest classification of any element in §C |
| Information barrier | none · control-room restricted · MNPI-bearing |
| Residency constraints | Jurisdictions whose data may not leave, and the effect on assembly |
| Cross-border serving | May this product be served to a principal outside the data's jurisdiction, and under what condition |

**The suppression rule.** Where policy excludes content, the payload must
carry **no count, marker, or placeholder** indicating that anything was
withheld. Restricted content is never materialized and filtered — a "3 items
hidden" marker is itself a disclosure, and on an information-barrier product
it is a reportable one.

### 2.3 Model-risk annotation — Mode 2 and Mode 3 only

An LLM in the delivery path is a model, and model governance applies.
Record:

- Model identifier and version, pinned; temperature pinned; prompt template
  versioned and logged
- Model-risk registration reference and validation status
- **The substrate/presentation boundary** — which fields are algorithmic
  artifact-of-record and which are model-rendered presentation
- **The smoothing control** — how the design prevents the model reconciling
  a conflict the substrate deliberately surfaced. A product whose substrate
  reports two sources disagreeing and whose narrative reads as settled has
  failed, and this is the failure mode Mode 2 is most prone to

Mode 1 products state "not applicable — no model in the trust path," which
is the reason to prefer Mode 1 wherever the decision does not need
narrative.

### 2.4 Request parameter surface

A table of every parameter with a **"Moves"** column naming which dimension
it moves: E anchor, R scope, T reconstruction, P envelope, Π perspective, or
a measure. A parameter that moves nothing is a formatting flag; push it to
the consumer.

Required on every product: an anchor identifier, `intent` (from the intent
registry, §13.1), and `debt_tolerance`.

**Declared-but-inert parameters** *(new in v0.3)*. Where a parameter is part
of the uniform surface but unsupported at this product's tier, declare it
and have it **fail explicitly** — `not_supported_at_tier`. It must never
silently succeed against current state. A parameter that appears to work and
does not is worse than an absent one: it will be relied on in a dispute.

### 2.5 Prerequisites, consumers and scope boundary

- **Prerequisites** — products this one composes over, by registry name.
  This is the build order.
- **Consumers** — products and applications that depend on this one.
  Required because §E supersession cascades need a reverse dependency list,
  and because a MAJOR version change needs a notification list.
- **Deliberately out of scope** — capabilities a reader will expect and not
  find, and which product carries them. Flag these to consumers as *coming
  next*, not as gaps.

---

## 3 · Section C — Data catalog

### 3.1 Element table

One row per data element:

| Column | Content | Rule |
| --- | --- | --- |
| Element | The fact or signal, in business language | One row per element, not per table |
| System of record | The authoritative source system | A named system; "internal" is not a system |
| Provenance class | internal-SOR · vendor · public-filing · derived · inherited | derived requires the derivation to appear in §D |
| Classification | public · internal · confidential · restricted | Drives §2.2 |
| Capability class | The store capability required (§11.1) | Never a product name |
| G dimension | E · R · T · P · Π · L · schema | Every element lands somewhere in the graph or it is not context |
| Ontology IRI | Bound class or property from the shared ontology contract | Unbound elements block registration |

### 3.2 Capability decomposition (new in v0.3)

Where a product depends on a capability the estate may not have, **decompose
the capability into its separable properties** and state what is deliverable
if each is absent. An estate rarely fails a capability wholesale; it
satisfies two of four properties and fails the rest, and that is the finding
worth having.

| Column | Content |
| --- | --- |
| Property | The separable sub-capability |
| Common estate answer | Widely available · sometimes · rare |
| If absent | Blocking · degrades to a named partial · workaround with a stated cost |

Where the decomposition yields a partial, name the **interim posture** —
which triggers are deliverable, what the unsupported parameter returns, and
what version string the partial ships under. Shipping a partial as though it
were complete is the failure this section exists to prevent.

### 3.3 Correlation key and single-writer discipline

Close with the **correlation key** — the identifier(s) every element joins
on, where the crosswalk lives, and its **measured coverage**. An unmeasured
crosswalk is a stated risk, not a footnote.

**Single-writer discipline.** One system is authoritative per element; no
element is written by two. Where an element exists today in two systems,
name the authority and make the other a read replica. This is a prerequisite
to build, not a follow-up.

**Identity authority hierarchy** *(new in v0.3)*. Where an anchor identifier
does not exist for every entity the product must serve, tabulate the entity
classes, the identity authority for each, the source of record-status for
each, and the **freshness ceiling each class implies**. An anchor that
silently excludes a population is inherited by every downstream product, and
the asymmetry belongs in the payload rather than averaged into a single
freshness claim.

---

## 4 · Section D — Assembly recipe

### 4.1 Client call

The literal request with parameters populated. Where the product has a
forensic and a live case, show the forensic one — it exercises more of the
surface.

### 4.2 Operator step table (expanded in v0.3)

Numbered, **one operator per step**, as a table:

| Column | Content |
| --- | --- |
| # | Step order |
| Operator | One name from the closed vocabulary (§11.2) |
| Capability class | From §11.1 — never a product name |
| Inputs | What the step consumes |
| Emits | What the step produces, named as it appears in lineage |
| Failure behavior | fail closed → HTTP code · degrade with debt · skip |
| p95 budget | Milliseconds, summing to a stated total against the tier envelope |

The final step is always contract assembly. **State the budget total and the
envelope it is measured against.** A total at 97% of the envelope is a
design finding, not a rounding detail — say which step dominates and what
the first optimisation would be.

### 4.3 Step detail

Below the table, prose for any step carrying a non-obvious discipline. This
is where an engineer learns *why* an ordering exists, and it is the part
that prevents a well-meaning optimisation from removing a load-bearing step.

Two disciplines recur and should be written out wherever they apply:

- **Policy that appears to do nothing still runs first.** At Tier 1 the
  step is an entitlement check; at Tier 5 the same step is what makes a
  restricted edge structurally absent. The ordering is learned from the
  first product or retrofitted painfully later.
- **Two filters on two axes are two filters.** Where a product reconstructs
  both what was true and what was known, both filters are separately
  parameterised and separately testable. Applying one silently answers a
  different question, and the silence is the defect.

### 4.4 Determinism class and payload hash

| Class | Meaning | Applies to |
| --- | --- | --- |
| deterministic | Same anchor + as_of + policy_version + graph snapshot → byte-identical payload | Mode 1 |
| substrate-deterministic | Algorithmic substrate byte-identical; presentation reproducible only under pinned model, temperature and prompt | Mode 2, Mode 3 |

Every product publishes a **payload hash** over the deterministic portion,
excluding `assembled_at`. **Replay asserts hash equality, not similarity.**

### 4.5 Replay statement and replay test

**Replay statement.** What exactly the replay engine re-executes to return
the identical product. "A similar product" is a defect recorded in §G, not a
caveat.

**Falsifiable replay test** *(new in v0.3)*. A numbered procedure a reviewer
can run against the built product, ending in an assertion that can fail. The
pattern: serve and record the snapshot · mutate the underlying state ·
re-derive live and confirm the new value · re-derive at the recorded
snapshot and confirm the **original** value returns. If the final step
returns the new value, the snapshot is not load-bearing and
`graph_snapshot_at` is decorative.

Where the product carries two time axes, add a second test asserting the
axes **disagree** under a case constructed to separate them. Agreement means
a filter was dropped.

### 4.6 Emitted contract

The response envelope of §10, populated with this product's payload schema,
**with types**. This is what the consuming agent team codes against and what
CI validates. Prose describing a payload is not a payload.

`extra=forbid` is enforced as a build-time CI invariant: a per-product
subclass cannot quietly introduce a field absent from the base declaration, and
a pull request carrying a drifted contract fails before it reaches a deployment
surface.

### 4.7 Validation gates

**Universal**, applying to every product without re-argument:

- **Empty-operator guard** — no operator returns an empty set silently;
  empty is fail-closed or an explicit debt contribution
- **Lineage strict equality** — operators_invoked equals the operators
  executed
- **TTL bounds** — expires_at consistent with the declared TTL and anchor;
  where the TTL is dual, the branch matches the condition
- **Debt gate** — assembly halts and returns the debt signal where D_c
  exceeds debt_tolerance
- **Suppression silence** — payload carries no marker of withheld content
  (§2.2)
- **Classification containment** — no element above the declared
  classification appears in the payload

Then **product-specific gates**, each a testable assertion naming the defect
it detects, cross-referenced to a fixture ID:

> "reconciliation guard — gross exposure must be ≥ guarantee-adjusted
> exposure; a violation means the dedup logic double-subtracted. → fixture
> EXP-G01"

---

## 5 · Section E — Volatility, debt & materialization

### 5.1 Half-life table

One row per signal class: λ_c · **calibration basis** · decay driver ·
supersession event · owner.

λ_c is **Control Plane configuration per observation type**, not a
per-document attribute; conflicts between two specs resolve centrally. The
table in a spec is an **initial calibration proposal**, and saying so is the
difference between a value an engineer can challenge and a number they
assume was measured.

**Calibration basis** is one of: **illustrative** (a starting assumption) ·
**expert** (business judgment, named function) · **measured** (observed
decision-reversal or restatement data). A catalog whose λ_c values are all
illustrative is not calibrated, and stating that plainly is more useful than
implying otherwise. Review cadence: annually, or on any
supersession-pattern change.

### 5.2 Debt model and per-component debt table (expanded in v0.3)

`D_c = 1 − (F · C · S)` — **multiplicative**, so a collapsed dimension
forces escalation rather than being averaged away. **Normalize F over
required signal classes, not over the classes actually present**, or losing
a source improves the freshness score.

Beyond the model, every spec carries a **per-component debt table**:

| Column | Content |
| --- | --- |
| Component | The input or claim |
| May be absent? | yes · no |
| D_c contribution | The weight |
| Behavior when absent | Fail closed · serve with flag · mark the affected claim NOT_EVALUABLE |

**Debt is decomposed per claim, never only per product.** A product with
four claims where one input is missing returns three evaluated claims and
one marked unusable — not a product-level failure, and never a
silently-omitted fourth. The gap is captured **before** the decision is
taken and shapes it directly: it is a decision input, not a log line.

### 5.3 Materialization posture

`materialized` · `derived-on-demand` · `split` (state which fields and
why). The test is mechanical: **if the fastest-moving input's λ_c is shorter
than the intended cache window, materialization is wrong.**

State the **cache key** explicitly — tenant, schema name, plan id, snapshot,
any time-axis parameters, and principal binding. A cache key missing a
parameter that changes the payload is a correctness defect that presents as
an intermittent one.

### 5.4 Supersession triggers

Each event marked **local** or **cascading**, and for cascading, the named
downstream products from §2.5. Invalidation cascades to every product whose
`operators_invoked` touched the superseded entity, not only those named for
it.

Re-derivation is **lazy** — invalidate for next request; do not
re-materialize eagerly, or a routine upstream publication becomes a
thundering-herd event across the catalog.

---

## 6 · Section F — Source binding & readiness

| Element | System of record | Interface & cadence | Available today | Gap owner | Blocker |
| --- | --- | --- | --- | --- | --- |

**Available today** is yes · partial (name the fields) · no. Every partial
or no carries a named gap owner and a stated blocker. Close with:

- **Access path** — existing feed, CDC, API, event stream, or new build
- **Identifier reality** — does the correlation key exist end to end; who
  owns the crosswalk; measured coverage
- **History depth** — how far back the source reconstructs, which bounds
  any as_of the contract advertises. Where the source publishes snapshots
  without history, **start retaining deltas now**; history not captured
  cannot be reconstructed later
- **Text-source boundary** — build-time extraction or runtime operator. A
  spec reaching into a document at runtime has changed capability class and
  cost band
- **First-build volumetrics** *(new in v0.3)* — the population the first
  build must contain for every gate and counterfactual to have something to
  act on. Where a required case does not occur naturally in the sample,
  **widen the sample until it does** rather than proceeding without it; a
  demonstrable primitive with no instance in the data reads to reviewers as
  machinery without a purpose

**No spec passes review with an unowned gap.** "Does not exist yet" is a
valid state; unattributed is not.

---

## 7 · Section G — Operate & govern

| Entry | Content |
| --- | --- |
| Accountable owner | Product owner, data steward, policy owner — roles, not individuals |
| Service objectives | p50 / p95 assembly latency, expected volume, concurrency ceiling, payload bound, absolute per-call cost estimate alongside the relative band |
| Degradation contract | Per input class: partial payload with elevated D_c, or fail closed. Mandatory classes named explicitly |
| Debt model | Which inputs drive F, C and S; debt_tolerance default and its basis (§5.2) |
| Observability | Per-operator latency · D_c distribution · gate-failure counts by gate · cache hit rate · entitlement denials · degradation-branch frequency · supersession-triggered invalidations. This is also the evidence base for moving λ_c and debt_tolerance from illustrative to measured |
| Retention & record of record | Which system is the record of record for each element; the fabric references it and does not replace it. Replay-record retention tier — full-fidelity, compressed, or tombstoned — and the severity rule that assigns it |
| Test fixtures | Named fixtures for the happy path, each gate, each degradation branch, and a replay hash assertion |
| Lifecycle | draft · in-build · certified · deprecated, with date and reviewer. Deprecation requires: consumer notification from §2.5, a sunset date at least one migration window out, and a named successor or an explicit statement that none exists |

### 7.1 Acceptance criteria (new in v0.3)

Every spec closes with a checklist of assertions **specific to this
product**, each independently verifiable, each phrased so it can fail. The
universal definition of done is at §15; §7.1 is what this product must
additionally prove. Close with the **open decisions blocking build**, named
by their §F row.

### 7.2 Catalog contribution (new in v0.3, optional)

Where the catalog is also a teaching sequence: what this product proves that
no earlier product proved, and what it deliberately does not prove. A
product that proves nothing new is a merge candidate; a product whose
exclusions are unstated invites a reviewer to read a tier boundary as an
oversight.

---

## 8 · Response envelope

Every product returns the same envelope. This is a wire contract, not a
style guide.

```json
{
  "product": "credit-risk.exposure-rollup",
  "semantic_version": "1.0.0",
  "payload": { },
  "contract": {
    "assembled_at": "...",
    "expires_at": "...",
    "ttl_anchor": "from_decision",
    "ttl_basis": "...",
    "assembly_mode": 1,
    "determinism_class": "deterministic",
    "freshness": [
      { "signal_class": "...", "observed_at": "...",
        "lambda_c_hours": 4, "relevance": 0.87 }
    ]
  },
  "lineage": {
    "operators_invoked": [ ],
    "graph_snapshot_at": "...",
    "policy_version": "...",
    "projection_plan_id": "...",
    "model_record": null,
    "payload_hash": "..."
  },
  "context_debt": {
    "F": 0.91, "C": 1.0, "S": 1.0, "D_c": 0.09,
    "contributions": [ ]
  },
  "notices": [
    { "type": "degraded-input", "signal_class": "...", "effect": "..." }
  ]
}
```

Rules:

- `payload` is never returned without `contract`, `lineage` and
  `context_debt`. A consumer that receives context with no debt signal
  cannot know what it is trusting.
- `notices` **is for degradation the consumer must see**, not for logging.
  Anything policy suppressed never appears here (§2.2).

---

## 9 · Error semantics

Every product returns one of these, and §D names which step raises which.

| Condition | Response | Notes |
| --- | --- | --- |
| Anchor unresolvable | 404 | Never an empty payload |
| Principal not entitled | 403, no detail on what exists | Existence is itself disclosure |
| Parameter unsupported at tier | 400 not_supported_at_tier | Never a silent success against current state |
| Debt gate exceeded | 409 with the debt block | Not a 200 with a warning |
| Mandatory input unavailable | 503 with the failed source class named | Silence is not a negative answer — an unretrieved screening source is not a clean screen |
| Non-mandatory input unavailable | 200 with notices and elevated D_c | The degradation contract in §G governs which inputs are which |

---

## 10 · Operators and capability classes

### 10.1 Capability classes

| Class | Capability required | Typical use |
| --- | --- | --- |
| relational | Set-based query over structured records at scale | Resolve, Enrich, reference lookup |
| bitemporal-ledger | Append-only state with valid-time and observed-time, queryable at a past point | Traversal mode temporal, supersession chains |
| graph-traversal | Multi-hop typed edge traversal with predicate filters | Ownership, guarantee, cross-default |
| document-passage | Document storage with passage-level addressing | Passage lineage, evidence chains |
| vector-index | Similarity retrieval over embeddings | Typology and pattern matching |
| federated-external | Contract-bounded request outside the institution's trust boundary | Cross-organizational products |
| in-memory | Deterministic computation over assembled state | Evaluate in all modes |

Estate binding lives in one artifact owned by the platform team. **Product
specs never name a database.**

### 10.2 Closed operator vocabulary

| Operator | Purpose | Reads | Emits | Cost driver |
| --- | --- | --- | --- | --- |
| Resolve | Anchor to canonical entity | relational | canonical entity, principal perspective | O(1) |
| Policy | Load the envelope in force; compute permitted sets | relational, bitemporal-ledger | policy_version, permitted party / document / action sets | O(1); gates everything downstream |
| Projection | Resolve and apply the Π plan | relational | projection_plan_id, projection shape | O(1) |
| Traversal | Walk typed edges. Modes: current · temporal | graph-traversal, bitemporal-ledger | node set, edge set, graph_snapshot_at | fan-out × depth — dominant cost |
| Enrich | Resolve nodes to attributes. Always batched | relational, document-passage | attribute sets, passage spans | entity × attribute fan-out |
| Similarity | Rank candidates within the permitted set | vector-index | ranked candidates with scores | candidate-set size |
| Evaluate | Deterministic computation. Modes: aggregate · score · reconcile · rank | in-memory | measures, scores, variances | negligible |
| Federate | Contract-bounded request to an external fabric | federated-external | remote attested payload, attestation record | network + negotiation |

Retired names: Batch Enrich (batch is mandatory, not a variant), Temporal
Traversal (a Traversal mode), Aggregate / Score / Reconcile / Rank (Evaluate
modes), Compose (contract assembly, not an operator).

### 10.3 Composition invariants

1. **Policy before anything that reads graph state.** Impermissible content
   is never materialized, not filtered afterwards.
2. **Resolve before Traversal.** Traversal from an unresolved anchor
   answers plausibly about the wrong entity.
3. **Enrich is batched, always.** One query per source per step.
4. **Algorithmic substrate before any semantic stage.** Every LLM
   invocation reads only the typed substrate a preceding algorithmic
   operator produced, and the substrate remains artifact-of-record.

### 10.4 Cost estimation

Cost bands are relative multiples of the Tier-1 baseline and are
placeholders until measured. Estimate before building:

```
est_cost = baseline
         × (1 + traversal_fanout^depth / fanout_reference)
         × (1 + enrich_sources)
         × mode_multiplier          # Mode 1 = 1 · Mode 2 ≈ 3–5 · Mode 3 ≈ 15
         × materialization_factor   # materialized = 1/hit_rate · on-demand = 1
```

Record the assumed fan-out, depth and hit rate. The commonest cost surprise
is a traversal whose fan-out was estimated on the median entity and paid on
the tail — **state the p95 fan-out, not the mean**.

---

## 11 · Shared contracts

Six artifacts referenced by every spec. Only the first exists today; the
rest block certification, not build.

| Artifact | Owner | Purpose | State |
| --- | --- | --- | --- |
| Ontology / IRI binding | Data architecture | Class and property IRIs every schema binds to | exists |
| Intent registry | Product owners + second line | Enumerated intent values and the envelope each selects | missing |
| Projection plan registry | Product owners | Named Π plans and what each assembles differently | missing |
| Policy version registry | Second line / compliance | Versioned envelopes with effective dates, resolvable at replay | missing |
| Half-life calibration table | Platform | λ_c per observation type with calibration basis | missing |
| Capability binding | Platform | Capability class to estate system, per environment | missing |

**Extension namespace** *(new in v0.3)*. Where a schema needs a class or
property the shared ontology does not carry, it is minted in the `ex:`
extension namespace — **registered centrally with an owner, once**, not ad
hoc per product. Three products minting their own covenant model
independently is three incompatible covenant models, and the divergence is
discovered at integration rather than at design.

### 11.1 Intent registry record

`intent` is required on every product and selects the policy envelope, which
makes it a governed object. Each record carries: intent id · plain-language
decision · the policy envelope selected · permitted principals · products
accepting it · owner · effective date and version · deprecation status.

### 11.2 Projection plan record

Each plan carries: plan id · principal(s) · **what is assembled
differently** (not displayed differently) · entitlement precondition ·
suppression behavior confirming the silence rule · owner · version. A plan
whose difference is presentational is rejected — that is a consumer concern.

---

## 12 · Naming, versioning and change classes

| Convention | Rule |
| --- | --- |
| Registry name | domain.product.vN — domain from the approved list, product in kebab-case, N = MAJOR only |
| Address | /context-products/{domain}/{product}/{anchor-id} |
| Schema artifact | schemas/{payload_type}.v{MAJOR}.json |
| Fixture id | {PREFIX}-{F/G/D/R}{nn} — happy path, gate, degradation, replay |
| Spec document id | CP-SPEC-{nnn} — stable across versions of the same product |

Change classes:

| Class | Examples | Consumer impact |
| --- | --- | --- |
| PATCH | Gate added, telemetry added, documentation | None |
| MINOR | Additive payload field, new optional parameter, new projection plan, λ_c recalibration | Backward compatible; notify consumers |
| MAJOR | Field removed or retyped, parameter default changed, ttl_anchor changed, Assembly Mode changed, policy envelope semantics changed | Migration window required; both versions served |

A λ_c or debt_tolerance change is **MINOR by type and material by effect** —
it changes outputs without changing shape. Announce these to consumers
explicitly rather than letting them surface as unexplained behavior change.

---

## 13 · Tiers, review and certification

| Tier | Capability classes | Cost band | Required review |
| --- | --- | --- | --- |
| 1 | relational | ×1 baseline | Product owner |
| 2 | + graph-traversal | ×1–2 | Product owner + platform |
| 3 | + bitemporal-ledger | ×2–4 | + second line where P is regulatory |
| 4 | + document-passage, vector-index | ×3–5 materialized, ×8–15 on demand | + second line, evidence-chain review |
| 5 | + federated-external, multi-principal Π | ×8–15 | + legal / control room |

Tiers describe assembly complexity, not maturity, and **not build order** —
build order comes from the prerequisite graph.

**Certification evidence.** Moving to certified requires, on file: schema
artifact published; all fixtures passing including the replay hash
assertion; measured p95 latency and per-call cost; debt_tolerance justified
against observed data; every §F gap closed or accepted by a named owner;
and, for Mode 2/3, model-risk registration complete.

---

## 14 · Review checklist for the reviewer (new in v0.3)

A reviewer reads for six things, in this order. The first three reject a
spec; the last three return it with comments.

- **Is the counterfactual falsifiable?** Can I run the test in §A and watch
  it fail? If not, the product's reason to exist is an assertion.
- **Is every capability stated as a capability, not a product?** A named
  database in §C means the spec is bound to a platform decision that has
  not been made.
- **Does every gap have an owner?** An unowned [TBC] is an unassigned risk
  that will surface during build.
- **Does each §D step name one operator from the closed vocabulary?**
  Bespoke logic in a step means cost moved from platform to product.
- **Is debt decomposed per claim?** A single product-level D_c forces
  all-or-nothing escalation and wastes the primitive.
- **Does the payload carry types?** Prose describing a payload is not a
  payload.

---

## 15 · Definition of done

- All seven sections present, in order, with front matter and capability
  gate
- Four-question build test answered, including honest partials
- Nine contract elements populated, including Assembly Mode with rationale
- Classification, residency and information-barrier fields complete
- Model-risk annotation complete for Mode 2/3, or "not applicable" for
  Mode 1
- Every §C element has a system of record, provenance class,
  classification, capability class, G dimension and ontology IRI
- Capability decomposition present where the estate answer is unknown, with
  interim posture named
- Correlation key stated with measured coverage, or the measurement named
  as a §F gap
- Every §D step names one operator from the closed vocabulary, its
  capability class, its emits, its failure behavior and its budget
- The four composition invariants hold
- Determinism class stated and a payload hash defined
- Replay statement plus a numbered, falsifiable replay test
- Emitted contract shown with types, conformant to the §8 envelope; error
  taxonomy mapped to steps
- Product-specific gates written as testable assertions with fixture IDs
- Half-life table carries a calibration basis and an owner per row
- Per-component debt table present, with behavior-when-absent per
  component
- Every no or partial in §F has a named gap owner; first-build volumetrics
  stated
- §G complete, including degradation contract, debt model, observability,
  retention and lifecycle
- Consumers list populated and cascading supersession targets named
- Acceptance criteria written as failable assertions; open blocking
  decisions named

---

## 16 · What changed from v0.2

| # | Addition | Why |
| --- | --- | --- |
| 1 | Rule 5 — every claim falsifiable | v0.2 required a counterfactual and a replay statement but allowed both to be narrative; a reviewer had no test to run |
| 2 | §0.2 placeholder discipline | An invented system name is a more serious defect than a marked gap, and v0.2 had no convention for marking one |
| 3 | §0.4 front matter and the capability gate | A blocking platform dependency discovered in §C is discovered after scheduling |
| 4 | §1 counterfactual acceptance test | Turns the counterfactual from a rationale into an executable check on the built product |
| 5 | §2.4 declared-but-inert parameters | A parameter that appears to work and does not will be relied on in a dispute |
| 6 | §3.2 capability decomposition and interim posture | Estates fail capabilities partially, not wholesale; the partial is the useful finding |
| 7 | §3.3 identity authority hierarchy | An anchor that silently excludes a population propagates the exclusion catalog-wide |
| 8 | §4.2 operator step table with emits and budgets | v0.2 prescribed prose steps; engineers need inputs, outputs and a latency budget per step |
| 9 | §4.5 falsifiable replay test | v0.2 defined hash equality but gave no procedure to demonstrate it |
| 10 | §4.6 emitted contract with types | The largest remaining gap between an architecture document and a buildable one |
| 11 | §5.2 per-component debt table | Product-level D_c forces all-or-nothing escalation; per-claim decomposition is what makes the primitive useful |
| 12 | §7.1–7.2 acceptance criteria and catalog contribution; §14 reviewer checklist | v0.2 could be written but not reviewed consistently |

Two v0.2 disciplines were reinforced rather than changed: λ_c remains
Control Plane configuration that a spec proposes rather than fixes, and the
suppression silence rule is now also a universal validation gate rather than
a prose rule.

``````

</details>

<a id="source-recipe"></a>

<details>
<summary>Specification generation recipe — ccf_code@4494b936</summary>

Path: `public/reference/specifications/spec_generation.md`

``````text
# Generating a Context Product Specification — recipe for SDK Claude

**Audience:** the Claude session working in `ccf_code`.
**Output of this recipe:** one `CP-SPEC-NNN_<Product_Name>.md` in
**`examples/cp-NN-<slug>/spec/`** — inside the example it governs, never in a
docs folder (§7.1) — authored as the **first step** of that example project,
**approved by Dave before any implementation**, and closed out against a build
that proves it.
**Status:** authoring instruction, not a specification. Written 2026-08-29 by
the vault Claude at Dave's direction.

**Owner: the vault.** Proposed by `ccf-sdk` and sent through the §11 return path
2026-08-29; reverse it here if the vault rules otherwise. The reason is this
document's own §1 — most of what follows states **what the vault and
`ccf_dataprep` owe `ccf_code`**, and an agent that owns the document stating its
own entitlements is writing another agent's term, which is the failure §0
records. So: **`ccf_code` proposes changes here through the return path rather than
editing freely** — with one narrow exception, and a test for it.

**§7 describes `ccf_code`'s own tree**, so `ccf_code` may edit §7 directly and
report back when the edit **records what the tree already is**: a path, a
filename, a directory that exists, a layout the examples already follow. That
is what happened to §7.2 on 2026-08-29 — the diagram predated `page/` and
`summary_explanations.md`, and a session following it would have built an
example missing both.

**The test: could this edit be wrong tomorrow without any file moving?** If it
could, it is a rule and not an observation, and it goes through the §11 return
path — even when it sits inside §7, even when the tree already disagrees with
it, and even when every example already does what the edit says. A requirement
that something be published, a gate ordering, an approval, any *shall* or
*must* or *never*: rules. Observing that no CP-SPEC is published is an
observation. **Deleting the requirement to publish one is a rule change.**

Recorded rather than implied: §7.1's publication requirement was deleted
directly at `a9c4e28b` on 2026-09-12 and reported through `contrib/ccf-sdk/`.
**The vault ruled the outcome correct and the route wrong.** The edit stands and
is not precedent for the next one. The report was complete and honest, which is
why this is a wording change here rather than a reversal there.

**The companion document is `ccf_code`'s.**
[How an example is delivered](example_delivery.md) covers everything after the
spec is approved — the `make` target, the venv, the README run block, the
documentation page mechanics, the banker-facing summary, the verbatim-output
discipline and a delivery definition of done. Nothing in it is another agent's
term, so it is owned, edited and gated by `ccf_code` without a return path.
**Where the two documents disagree about `ccf_code`'s tree, the companion
wins**; where they disagree about what a specification must contain, this one
does.

---

## 0 · What this document is

There are 21 Context Products described in the obsidian vault. None of them has
an SDK specification yet except `counterparty-reference-snapshot`, and that one
is on the older CP-SPEC-001 form. This document is the recipe for producing the
rest.

A Context Product specification here is assembled from **three inputs owned by
three different agents**, it is **the first step in building a Context Product
example**, and **it does not proceed to implementation until Dave has approved
it** (§2).

The single most important rule in this document is that **you may not write
another agent's term.**

That rule exists because it has already failed once. The vault wrote a scope
sentence — *"identity only — no exposure, no grade, no relationship"* —
with no implementation to check it against. `ccf_dataprep` read it, correctly
treated the vault as the requirements authority, and generated an estate with
**no risk grade and no coverage assignment**. Meanwhile CP-SPEC-001's emitted
contract declares `internal_risk_grade`, `coverage_rm_id`, `coverage_team` and
`coverage_lob`, and its §E.2 assigns the absent overlay a **0.30 `D_c`
contribution against a 0.25 `debt_tolerance`** — which trips the debt gate and
returns `409`. Three agents, no malice, one unservable product.

Everything below is designed so that cannot happen twenty more times.

---

## 1 · The law: three owners, one term each

| Term of the equation | Owner | Authoritative for | Published as |
|---|---|---|---|
| **why it exists** | **vault**<br>`obsidian-vault/wiki/context-products/content/` | Decision frame · trigger · consuming principals · counterfactual and its closed-taxonomy failure mode · four-question build test result *with honest partials* · tier · build order · prerequisites · **scope boundary** · primitive taught · contrast pointer · the seven-class Commons/FIBO typing chain | The vault article, prose. §A and the front matter of your spec derive from it |
| **what data exists** | **ccf_dataprep**<br>`/home/parkave/ccf_dataprep` | §C element rows — system of record · provenance class · classification · capability class · `G` dimension · **ontology IRI** · §F readiness and *measured* coverage · §E calibration evidence · first-build volumetrics · every count, threshold and match rate | Their repo: `docs/spec-digest.md`, `docs/data-acquisition-plan.md`, `docs/known-issues.md`, `validators/spec_coverage.py`, `ontology/`, and the live `ccf_v2.*` schema |
| **what it does** | **ccf_code (you)** | §B.1 element values the runtime enforces · parameter surface · §D operator steps, budgets and witnesses · determinism class · replay test · emitted contract · validation gates and fixtures · error mapping · §E materialization and debt · §G operations — **and the merge itself** | `examples/cp-NN-<slug>/` — spec, artifacts and code together |

**The rule.** When a term you need is missing from its owner, you write
`[TBC — <owner>]` and name what you asked for. **You never guess it.** A guessed
term is indistinguishable from an authoritative one once it is written down, and
that is precisely how the grade/coverage break happened.

This is the standard's own placeholder discipline (§0.2) applied *across* agents
rather than within a document: *"a marked gap gets closed and an invented one
gets built."*

### 1.1 · Two levels of specification — and you are writing the second

**Ruled by Dave, 2026-08-29:**

> *"We must distinguish between the specification at the vault level versus the
> SDK level. The vault level is an **implementation independent** product
> specification whereas the SDK is a **specific implementation artifact** for
> developing the context product."*

Both documents are legitimately called `CP-SPEC-001`. They are different
artifact classes answering different questions, and **neither supersedes the
other.**

| | **Vault level** | **SDK level — what you write** |
|---|---|---|
| Document | `wiki/context-products/content/<slug>.md` | `examples/cp-NN-<slug>/spec/CP-SPEC-NNN_….md` |
| Answers | **what the product is** | **how it is built** |
| Posture | implementation-independent | a specific implementation artifact, bound to one estate |
| **Names a store** | **no** | **yes — or a table reference means nothing** |

**The Standard's §10.1 — *"product specs never name a database"* — is written
for the vault level.** Applying it to an implementation artifact strips out the
one thing a developer needs: *"As a context product developer how do I know
where the data being referenced lives?"* (Dave). In a five-store estate
`ccf_v2.legal_entity` does not say whether that is the relational store, the
graph ledger, the document store or the departmental file.

**Three levels. Only the middle one moves:**

| Level | Example | Vault level | SDK level |
|---|---|---|---|
| Capability class — what the store must *do* | `relational` | yes | yes |
| **Store · schema · table — where the element *is*** | `PostgreSQL ccf_v2.legal_entity` | **no** | **yes** |
| Deployment — host, port, credential, instance | — | **never** | **never** |

**Deployment never appears in a specification of either kind.** It lives in
`backends.yaml` as an environment-variable *name*. A sweep of `examples/`,
`public/`, `src/` and `runtime/` for the estate's host address must return
nothing, and no credential enters the tree.

> **This distinction cost a working session before it was written down, and it
> produced two errors in opposite directions.** Read side by side without it,
> the vault article and the repo's `CP-SPEC-001` look like rival drafts of one
> document — 11 §C rows against 4 — and the apparent task is to adjudicate which
> wins. There was no conflict. Then the same gap, applied the other way, stripped
> store identification out of an implementation spec on the literal reading of a
> rule written for the other level. Carry the frame, not just the rules.

---

## 2 · The sequencing law: spec first, approved, then build

**Every specification must be approved by Dave, and the approved specification
is the first step in creating a Context Product example.** Nothing is
implemented before that approval. There are two gates.

### Gate 1 — the authored spec (blocking)

A CP-SPEC is **not** written for the whole catalog in advance. It is written as
**step one of one example project**, when that product comes up the ladder. At
Gate 1 you author everything knowable before code exists:

- §0 and the data banner · front matter · capability gate
- §A in full, including the counterfactual acceptance test as a procedure
- §B.1–B.5 — the nine elements, parameter surface, scope boundary
- §C in full — every element bound to a real table and IRI, coverage measured,
  traps named
- §D.1–D.3 — client call, the operator step table, step detail
- §D.7 gates and §G.2 acceptance criteria, **as intentions phrased so they can
  fail**
- §E.1–E.5 and §F.1–F.4 — with measured data reality from `ccf_dataprep`
- Everything not yet measurable marked **`[TBC — this build, phase Pn]`**

**Send it to Dave. Do not write implementation code until he approves it.** He
is approving the *design*: scope, decision frame, contract elements, operator
composition, and what the product will be held to. That is the cheapest moment
to catch a wrong product, and the grade/coverage break in §10.1 is what an
unreviewed scope boundary costs downstream.

### Gate 2 — the completed spec (close-out)

During and after the build, the measurable terms land: p95 budgets, payload
hashes, witnesses, replay results, gate-failure observations, final
materialization posture. You fill them in and clear every `[TBC — this build]`.

Gate 2 is **not** a second design review. It is a close-out: the approved design
is now discharged by something that runs.

**Nothing at Gate 2 may silently change a Gate-1 decision.** If the build
disproves an approved term — a λ_c, an operator step, a scope boundary — that is
a **deviation**: stop, state it, and take it back to Dave. Do not edit the
approved design to match what you built.

### An approved spec IS editable — classify the edit, not the document

**Ruled by Dave, 2026-08-29.** Approval does not freeze the file. It freezes
**what was approved**, which is not the same thing. Three classes:

| Class | Examples | What to do |
|---|---|---|
| **Editorial** | spelling, a heading brought into line with the Standard, formatting, a broken link, a typo | **Just edit it.** No notice, no approval. Name it in the commit message |
| **Corrective** | a factual error in something approved — a wrong table name, a miscounted row, a stale path | **Edit it, then say what changed and why.** No re-approval; visibility is the obligation |
| **Substantive** | a contract element value · scope boundary · operator step · λ_c · a gate · a parameter · anything that changes what the approval was *about* | **Still a deviation.** Stop, state it, take it back. Unchanged by this ruling |

The test is not *"is the document approved?"* — it always is. The test is
**"would Dave's approval have been different if the document had said this
originally?"** If no, edit. If yes, escalate.

Regenerating a published page after an editorial edit is part of the edit, not a
separate approval.

### Why the claims must still be discharged by a run

Approval makes the design binding; it does not make the claims true. That is
what `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml`
holds you to:

> *"**THE §D OPERATOR STEP TABLE, AS DATA** — so that criterion 2 is discharged
> by a test rather than by a reading... **A prose table cannot be held against a
> run.** This document declares the same steps with, per step, a WITNESS — a fact
> a completed run either produced or did not... **a step nothing executes is
> RED.**"*

So: the spec is approved first and proven second. A section whose content cannot
be known before the build is `[TBC — this build]` at Gate 1, never a plausible
guess — a guessed budget that survives review becomes a number someone plans
against.

## 3 · Build order: the ladder is the vault's, not yours

Priority is **increasing complexity**, and the vault establishes it. Do not
reorder for convenience. Each rung teaches a primitive the next rung assumes,
and the catalog is a teaching sequence as much as an inventory.

`cp-00-institutional-holders` sits below the ladder as your own warm-up rung and
is already built. The vault's 21 follow:

| Rung | Tier | Product | What it exists to prove |
|---|---|---|---|
| 01 | **T1** | `counterparty-reference-snapshot` | The contract fires. Identity authority hierarchy. The replay harness itself |
| 02 | T1 | `facility-terms-snapshot` | Anchoring on something other than a legal entity; `from_entity_freshness` against a document-dated source |
| 03 | T1 | `obligor-financial-spread` | Attribute-level temporal validity before any graph exists |
| 04 | **T2** | `corporate-family-tree` | First multi-store product. Multi-hop traversal, cross-shareholding cycles as findings |
| 05 | T2 | `credit-exposure-rollup` | Traversal + aggregation; the concentration denominator a flat product gets wrong |
| 06 | T2 | `collateral-and-setoff-coverage` | Typed edge vocabulary; coverage as a graph question |
| 07 | T2 | `client-360-coverage-graph` | High fan-out; where traversal cost becomes a design constraint |
| 08 | **T3** | `covenant-in-force-as-of` | **Flagship.** Ledger time-travel, supersession preserved |
| 09 | T3 | `treasury-liquidity-position` | Fast `λ_c` forcing on-demand derivation |
| 10 | T3 | `rating-and-spread-migration` | Per-signal decay curves |
| 11 | T3 | `credit-surveillance-early-warning` | Supersession cascading across downstream products |
| 12 | T3 | `fx-post-trade-reconciliation` | Two time axes that must be separately parameterised |
| 13 | **T4** | `covenant-cross-reference` | Passage-level lineage across documents |
| 14 | T4 | `credit-memo-context` | Algorithmic/semantic stage alternation; debt across a multi-agent handoff |
| 15 | T4 | `kyc-refresh-beneficial-ownership` | Entity resolution; ownership to person level |
| 16 | T4 | `abs-securitization-surveillance` | Loan-level fan-out; forces the materialization decision |
| 17 | **T5** | `mnpi-wall-enforcement` | Entitlement as formative constraint — the edge never materializes |
| 18 | T5 | `ib-opportunity-synthesis` | Projection `Π` across three principals |
| 19 | T5 | `aml-typology-match` | Policy-before-Similarity. **Synthetic obligor only, never a named real company** |
| 20 | T5 | `syndicated-lending-co-lender` | Cross-organizational federation under a negotiated envelope |
| 21 | T5 | `large-exposure-rwa-concentration` | Composes every primitive below it |

**Tier is not build order within a tier** — the vault's index order above is.
Where a product's `Prerequisites` name another product, that dependency
overrides the list.

---

## 4 · Phase 0 — gather, before you write a line *(Gate 1)*

For product `<slug>`:

**4.1 Read the vault article in full.**
`/home/parkave/obsidian-vault/wiki/context-products/content/<slug>.md`
Or `get_article("context-products", "<slug>")` over MCP.

Extract and hold separately — these are the vault's terms and you will not
alter them:
- decision & trigger, consuming principals
- counterfactual failure + which closed-taxonomy mode it names
  (`context-starved · temporally-incoherent · perspective-flat · policy-blind · evidence-free`)
- the four-question test result, **including partials and nos**
- tier, build order note, prerequisites, consumers
- **scope boundary** — record it verbatim; see §10 warning
- primitive taught, contrast pointer

> ⚠️ **Twenty of the 21 vault articles are on the older Q019 form**, where **§F
> means *Manufacture envelope*, not *Source binding & readiness*.** Only
> `counterparty-reference-snapshot` is on v0.3. Resolve vault sections **by
> heading name, never by letter.**

**4.2 Pull the data reality from ccf_dataprep.**

| Need | Where |
|---|---|
| §C rows as dataprep holds them | `validators/spec_coverage.py` — `read_catalog()` and the per-product manifests |
| §C/§F as dataprep read the vault | `docs/spec-digest.md` |
| Obligor cast, waves, acquisition decisions | `docs/data-acquisition-plan.md` |
| Known defects and limits | `docs/known-issues.md` |
| Ontology IRI bindings | `ontology/`, plus the vault's `fibo-iri-binding` mirror |
| Anchor-cast satisfaction | `validators/cast_audit.py` |
| Live estate | the `ccf_v2.*` schema |

**Measure, do not assume.** Every count, coverage figure and match rate in your
spec must come from a query you ran or a dataprep artifact you can cite.
`bound is not the same as materialized` — an IRI documented in the binding
mirror does not mean rows exist against it.

**4.3 Re-read the Standard.**
`public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`

Known errata — the document's own cross-references are stale in six places, so
resolve by heading, not by the number cited: response envelope is **§8** (cited
as §10, twice); intent registry **§11.1** (cited §13.1); projection plans
**§11.2** (cited §13.2); change classes **§12** (cited §14, twice); capability
classes and operator vocabulary **§10.1/§10.2** (cited §11.1/§11.2).

**4.4 Use CP-SPEC-000 as your template, not CP-SPEC-001.**
`examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`

CP-SPEC-001 predates the current form. CP-SPEC-000 carries the embedded §0, the
B.1–B.5 / C.1–C.5 / D.1–D.7 / **E.1–E.5** / F.1–F.4 / G.1–G.3 structure, the
`[TBC]`-with-owner register at F.2, and the mandatory data banner. Match it.

---

## 5 · Phase map — Gate 1, then build, then Gate 2

| Phase | Gate | What you do | Spec sections |
|---|---|---|---|
| **P1 · Frame** | 1 | Read vault article; confirm the product is real and belongs | §0, banner, front matter, §A, §B.5 |
| **P2 · Bind** | 1 | Map every element to a real table/column and IRI; measure coverage | §C.1–C.3, §F.1, §F.3 |
| **P3 · Trap** | 1 | Find what the data does *not* support cleanly; choose bindings, record their cost | **§C.4**, §C.2, §F.4 |
| **P4 · Design** | 1 | Contract elements, parameter surface, operator composition, intended gates and criteria | §B.1–B.4, §D.1–D.3, §D.7, §E.1–E.5, §G.2 *(budgets and measured values `[TBC — this build]`)* |
| **▶ GATE 1** | — | **Send to Dave. Stop. No implementation until approved.** | Spec complete except `[TBC — this build]` |
| **P5 · Assemble** | 2 | `assembler.py`, `produce.py`, `deployment.py`, `ccf_config.yaml`, `backends.yaml` | code; `artifacts/*.yaml` |
| **P6 · Run** | 2 | Execute; capture budgets, hashes, witnesses | §D.2 budgets, §D.4, §D.5, §D.6 |
| **P7 · Gate** | 2 | Fixtures; make each gate fail deliberately once | §D.7 fixture IDs, §G.2 results |
| **P8 · Operate** | 2 | Measure decay against read frequency; confirm posture | §E.1 basis, §E.3 posture, §G.1, §G.3 |
| **▶ GATE 2** | — | Clear every `[TBC — this build]`; file returns to vault and dataprep | §F.2 register closed |

A Gate-1 section written from imagination is the failure this map exists to
prevent. A Gate-2 value that contradicts an approved Gate-1 decision is a
**deviation** — see §2.

## 6 · Section-by-section recipe

Throughout: **SOURCE** = whose term it is · **NEVER INVENT** = the failure mode
· **DISCHARGED BY** = what proves it.

### §0 · What this document is

Restate the standard's five rules, the four-question test, placeholder
discipline, the section skeleton and front matter — as CP-SPEC-000 does. This is
deliberate duplication so the spec is readable standalone.

**Then the banner. It is mandatory and it is not boilerplate.**

CP-SPEC-000 opens with `READ THIS BEFORE YOU READ A NUMBER`, stating that the
examples **teach method, not figures**, with that product's own *measured*
provenance counts. Reproduce this with **your product's measured numbers**, and
follow CP-SPEC-000's discipline of repeating the statement **beside each figure
cluster** rather than leaving it as a header a reader scrolls past.

For `aml-typology-match` (rung 19) the vault adds a hard constraint: **synthetic
obligor only, never a named real company.** Carry it into the banner.

### Front matter

**SOURCE:** vault (registry name, tier, build order, what it resolves) ·
you (Assembly Mode, cost band, lifecycle).

Registry name is `domain.product.vN`. **Assembly Mode is a registration-time
commitment** — a documented decision with a one-sentence cost/quality/determinism
rationale, not a description of how you happened to build it. Modes 2 and 3
require §B.3.

**Capability gate above §A** where the product cannot be built without a
capability the estate may not have. This is a scheduling statement.

### §A · Decision frame

**SOURCE: vault, entirely.**
**NEVER INVENT:** the counterfactual, the failure-taxonomy mode, or the
four-question result. If the vault's four-question result carries a `no` or a
`partial`, **carry it through unchanged** — `counterparty-reference-snapshot` is
admitted on one no and one partial, stated openly, and that honesty is the
standard working.

**You add one thing:** the **counterfactual acceptance test** — the vault's
narrative counterfactual rewritten as a numbered procedure ending in an
assertion that can fail. State the query, both answers, and the condition under
which they must differ.

**DISCHARGED BY:** a test in the example that runs the counterfactual and fails
if the two answers agree.

### §B · Contract

**B.1 — the nine elements.** Schema · Freshness SLA · TTL · Policy Binding ·
Lineage · Semantic Version · Discovery · Addressability · **Assembly Mode**.

**SOURCE: you.** The vault's element values are theoretical and have been
measurably wrong — its `counterparty-reference-snapshot` set `λ_c ≈ 24h` where
the real half-life is ~365 days, having substituted publication cadence for
decay. Take element *intent* from the vault; take *values* from your runtime.

Rules that are not negotiable:
- **Schema** binds every entity, relationship, attribute and measure to an
  **ontology IRI**, and links a machine-readable artifact at
  `schemas/{payload_type}.v{MAJOR}.json`. *Prose in a table cell is not a
  contract.*
- **Freshness SLA** is **per signal class**, never one value over a mixed payload.
- **TTL** carries `ttl_anchor` **and states how `expires_at` is computed.** For
  `from_entity_freshness` that is source publication time, not request time —
  *a 23:00 request against an 06:00 file gets 7 hours of validity, not 24.*
  **Nine vault specs declare this anchor and none define the computation.** You
  must.
- **Lineage** is the full list: `operators_invoked[]` · `graph_snapshot_at` ·
  `policy_version` · `projection_plan_id` · passage anchors where a claim rests
  on text · `context_debt` · `payload_hash` · `model_record`. Plus any
  product-specific authority field. `operators_invoked` carries **typed operator
  references** — `ResolveOperator@entity-master.v1.0` — **not bare names**,
  because lineage strict equality compares them.
- **Discovery** is registered only after §G is complete.

**B.2 — classification and residency.** Data classification (highest of any §C
element) · information barrier · residency · cross-border serving. **The
suppression rule:** where policy excludes content the payload carries **no
count, marker or placeholder**. A "3 items hidden" marker is itself a
disclosure.

**B.3 — model-risk annotation.** Modes 2/3 only: pinned model and version,
pinned temperature, versioned prompt, model-risk registration, the
**substrate/presentation boundary**, and the **smoothing control** — how the
design stops the model reconciling a conflict the substrate deliberately
surfaced. Mode 1 states *"not applicable — no model in the trust path."*

**B.4 — request parameter surface.** Every parameter with a **Moves** column
naming which dimension it moves (`E` anchor · `R` scope · `T` reconstruction ·
`P` envelope · `Π` perspective · a measure). A parameter that moves nothing is a
formatting flag — push it to the consumer.

Required on every product: an anchor identifier, `intent`, `debt_tolerance`.

**Declared-but-inert parameters** must be declared and **fail explicitly** with
`not_supported_at_tier`, never silently succeed. This keeps the request surface
uniform so consumers do not learn a second calling convention at a higher tier.

**B.5 — prerequisites, consumers, scope boundary.**
**SOURCE: vault** for prerequisites and consumers (it owns build order).
Consumers must be **named individually** — supersession cascades and MAJOR
version notification both need a reverse dependency list, and *"every other
product"* cannot serve as one.

> ⚠️ **Scope boundary — treat with suspicion.** This is the field that broke.
> Copy the vault's sentence verbatim, then **check it against your §C and your
> payload.** If your payload declares a field the vault's scope excludes, you
> have found a live conflict: **do not silently resolve it.** Record it, raise
> it (§11), and mark the field `[TBC — ruling]` until it is settled.

### §C · Data catalog

**SOURCE: ccf_dataprep, entirely.**

**C.1 — element table.** One row per element, *not per table*:

`Element · System of record · Provenance class · Classification · Capability class · G dimension · Ontology IRI`

- **Provenance class** is the closed list: `internal-SOR · vendor ·
  public-filing · derived · inherited`. `synthetic` is **not** a provenance
  class — it is a property of the estate and belongs in the §0 banner or its own
  column. The vault conflates these; do not copy that.
- **Capability class** — never a product name. `relational ·
  bitemporal-ledger · graph-traversal · document-passage · vector-index ·
  federated-external · in-memory`. This column says what the store must *do*.
- **Store · schema · table — name it.** Per §1.1 you are writing the
  implementation artifact, so §C.1 carries a store column alongside capability
  class, and §F.3 states the estate binding collectively — including **which
  stores this product does not read, and why.** The vault article's store
  assignment is a **proposal** to confirm against the real estate, not residue
  to discard and not an authority to copy. **Deployment detail — host, port,
  credential — never appears.**
- **G dimension** — every element lands in `E · R · T · P · Π · L · schema`, or
  it is not context.
- **Ontology IRI** — unbound elements block registration. Foundational party
  terms are in **OMG Commons** (`cmns-org:`), not FIBO; only `Corporation` stays
  as `fibo-be-le-cb:Corporation`. A validator asserting every IRI begins
  `spec.edmcouncil.org` will reject correct data.

**C.2 — capability decomposition.** Decompose each required capability into
separable properties with `Widely available · sometimes · rare` and what is
deliverable if each is absent. State the **interim posture** where the answer is
partial. Estates fail capabilities partially, and the partial is the finding.

**C.3 — correlation key, single-writer, identity authority.** The join key,
where the crosswalk lives, its **measured** coverage. One authoritative writer
per element. Where an anchor does not exist for every entity the product serves,
tabulate entity classes, identity authority, and the **freshness ceiling each
implies** — an anchor that silently excludes a population propagates the
exclusion catalog-wide.

**C.4 — the data traps.** CP-SPEC-000's most valuable section and the one with
no vault equivalent. **Where the data does not cleanly support what the spec
wants, name the trap, the binding you chose, and what that choice costs.**
CP-SPEC-000 records ~22.5% weak issuer matching **by design** rather than as a
defect. A spec with no traps section has either a perfect estate or an
unexamined one.

**C.5 — what this data is.** Restate the synthetic/engineered posture beside the
figures, per the banner discipline.

### §D · Assembly recipe

**SOURCE: you, entirely. This section is code before it is prose.**

**D.1 — client call.** The literal request, parameters populated. Where the
product has a forensic and a live case, show the **forensic** one — it exercises
more surface.

**D.2 — operator step table.** One operator per step:

`# · Operator · Capability class · Inputs · Emits · Failure behavior · p95 budget`

Operators come from the closed vocabulary only: **Resolve · Policy · Projection
· Traversal · Enrich · Similarity · Evaluate · Federate**. Retired names —
Batch Enrich, Temporal Traversal, Aggregate/Score/Reconcile/Rank, Compose — are
not operators. Final step is always contract assembly.

**State the budget total and the envelope it is measured against.** A total at
97% of envelope is a design finding: say which step dominates and what the first
optimization would be.

**Mirror this table into `artifacts/assembly-recipe.yaml` with a WITNESS per
step.** A step nothing executes is RED.

**D.3 — step detail.** Prose only where a step carries a non-obvious discipline.
Two recur and must be written wherever they apply:
- **Policy runs first even when it appears to do nothing.** At T1 it is an
  entitlement check; at T5 it is what makes a restricted edge structurally
  absent. Learned from the first product or retrofitted painfully.
- **Two filters on two axes are two filters.** Separately parameterised,
  separately testable. Applying one silently answers a different question.

**D.4 — determinism class and payload hash.** `deterministic` (Mode 1) or
`substrate-deterministic` (Modes 2/3) — those exact enum strings; they ship in
the envelope. Publish a hash over the deterministic portion excluding
`assembled_at`. **Replay asserts hash equality, not similarity.**

**D.5 — replay statement and falsifiable replay test.** A numbered procedure
ending in an assertion that can fail: serve and record · mutate state ·
re-derive live and confirm the new value · re-derive at the recorded snapshot
and confirm the **original** returns. If the last step returns the new value,
`graph_snapshot_at` is decorative.

Two time axes ⇒ a second test asserting the axes **disagree** under a
constructed case. Agreement means a filter was dropped.

**D.6 — emitted contract.** The §8 envelope populated **with types**. This is
what consuming teams code against and what CI validates. `extra=forbid` is a
build-time invariant. *Prose describing a payload is not a payload.*

**D.7 — validation gates.** Six universal, without re-argument: empty-operator
guard · lineage strict equality · TTL bounds · debt gate · suppression silence ·
classification containment. Then **product-specific gates**, each a testable
assertion naming the defect it detects, cross-referenced to a fixture ID.

**Error mapping** — condition → raising step → response. `404` unresolvable ·
`403` not entitled, no detail on what exists · `400 not_supported_at_tier` ·
`409` debt gate with the debt block · `503` mandatory input unavailable, source
class named · `200` with notices for non-mandatory. **Silence is not a negative
answer** — an unretrieved screening source is not a clean screen.

### §E · Volatility, debt & materialization

**SOURCE: dataprep for calibration evidence, you for the model and posture.**

**E.1 — half-life table.** Per signal class: `λ_c` · **calibration basis** ·
decay driver · supersession event · owner.

> **λ_c is a half-life, not a refresh cadence.** A daily file does not make a
> legal name decay daily. This is the single most consequential error in the
> vault's version and it must not propagate.

Calibration basis is `illustrative · expert · measured`. **State plainly where
no row is measured.** λ_c is Control Plane configuration; your table is a
proposal.

**E.2 — debt model and per-component debt.** `D_c = 1 − (F · C · S)`,
multiplicative so a collapsed dimension forces escalation. **Normalize F over
required signal classes, not over classes present**, or losing a source improves
the score.

Then the per-component table: `Component · May be absent? · D_c contribution ·
Behavior when absent`. **Debt decomposes per claim, never only per product** —
four claims with one input missing returns three evaluated and one
`NOT_EVALUABLE`, not a product-level failure.

Check your contributions against `debt_tolerance`. A single optional component
contributing more than the default tolerance means the product refuses to serve
whenever it is absent — that is a design finding, not an accident.

**E.3 — materialization posture.** `materialized · derived-on-demand · split`.
The test is mechanical: **if the fastest-moving input's λ_c is shorter than the
intended cache window, materialization is wrong.** Feed it a real λ_c — fed a
cadence, it returns the wrong architecture while looking correctly applied.

State the **cache key** explicitly: tenant · schema · plan id · snapshot · time
parameters · principal binding · every parameter that changes the payload. A
missing key parameter is a correctness defect presenting as an intermittent one.

**E.4 — supersession triggers.** Each **local** or **cascading**; for cascading,
the named downstream products. Re-derivation is **lazy** — invalidate for next
request, never re-materialize eagerly.

**E.5 — the expiry and its refusals.** Per CP-SPEC-000: state what expiry
actually produces at the delivery boundary and which refusals it can raise.

### §F · Source binding & readiness

**SOURCE: dataprep, entirely.**

**F.1** — per element: system of record · interface & cadence · **available
today** (`yes · partial (name the fields) · no`) · gap owner · blocker.

**F.2** — **every `[TBC]` in the document, with an owner.** This is the register
that makes the cross-agent discipline auditable. Each row names the term, the
owning agent, and what was asked. **No spec passes review with an unowned gap.**
*"Does not exist yet" is a valid state; unattributed is not.*

**F.3** — access path · **identifier reality** (does the key exist end to end,
who owns the crosswalk, measured coverage) · **history depth** (where the source
publishes snapshots without history, say *start retaining deltas now* — history
not captured cannot be reconstructed later) · text-source boundary ·
**first-build volumetrics**: the population the first build needs for every gate
and counterfactual to have something to act on. Where a required case does not
occur naturally, **widen the sample until it does**.

**F.4** — **recorded findings that are not `[TBC]`**, because they need no
decision to build. Keep this distinct from F.2; conflating a finding with a
blocker inflates the blocker list and hides the real ones.

### §G · Operate & govern

**SOURCE: you.**

Accountable owner (roles, not individuals) · service objectives (p50/p95,
volume, concurrency, payload bound, **absolute** per-call cost alongside the
relative band) · degradation contract per input class with **mandatory classes
named** · debt model · observability (per-operator latency, `D_c` distribution,
gate failures by gate, cache hit rate, entitlement denials, degradation-branch
frequency, supersession invalidations — this is the evidence base that moves
λ_c from illustrative to measured) · retention and record of record · test
fixtures · lifecycle (`draft · in-build · certified · deprecated`).

**G.1** — restate the expiry obligation where an operator will look for it.

**G.2 — acceptance criteria.** Assertions **specific to this product**, each
independently verifiable, each phrased so it can fail. Close with the **open
decisions blocking build**, named by their §F.2 row.

**G.3 — catalog contribution.** What this product proves that nothing earlier
proved, and what it deliberately does not prove. The vault's *primitive taught*
is your input. A product that proves nothing new is a merge candidate; a product
whose exclusions are unstated invites a reviewer to read a tier boundary as an
oversight.

---

## 7 · Where the spec lives, and the artifacts around it

### 7.1 · The spec lives in the example, not in the docs tree

**A product spec belongs at `examples/cp-NN-<slug>/spec/CP-SPEC-NNN_<Name>.md`,
and is created there at Gate 1.** It is never authored in
`public/reference/specifications/`.

This follows from §2 rather than from filing preference. A spec whose §D steps
are discharged by witnesses in `artifacts/assembly-recipe.yaml`, and whose
emitted contract is validated by CI against code in the same directory, has to
be **versioned with the thing that proves it**. Move it into a documentation
tree and the claims and their evidence can drift in separate commits — which is
the entire failure this recipe exists to prevent.

The two trees have different jobs:

| Path | Holds | Example |
|---|---|---|
| `examples/cp-NN-<slug>/spec/` | **product specifications** — one per example, co-versioned with the code that discharges them | `CP-SPEC-000-institutional-holders.md` |
| `public/reference/specifications/` | **reference documents** — things that govern specs but describe no product | `Context_Product_Specification_Standard_v0-3.md`, this recipe |

**ONE CANONICAL SPEC, AND NO SECOND COPY THAT CAN DRIFT.** A product
specification lives in its example's `spec/` directory and **is not duplicated
into `public/`**. There is no second location and no per-spec nav entry.

| | Where |
|---|---|
| **Canonical, and the only copy** | `examples/cp-NN-<slug>/spec/`, from Gate 1 onward — versioned with the artifacts and code that discharge it |
| **`public/reference/specifications/`** | reference documents that **govern** specs and describe no product: the authoring standard, this recipe, the delivery companion |

Public documentation **may reference or summarize** a CP-SPEC — link to it,
quote a clause, explain what a rung proves. It must not create a second copy of
the document.

**This corrects what this section used to say, and the correction is a
documentation-rule fix rather than any product's deviation** (Dave,
2026-09-12). The previous text directed a copy into
`public/reference/specifications/` with a nav entry after Gate 2, and cited
`mkdocs.yml` for it. `mkdocs.yml` says the opposite, in a ruling of the same
author dated 2026-08-29:

> *"Individual CP-SPECs do NOT live here. A specification lives in its own
> example's `spec/` directory, beside the artifacts and code it governs.
> `CP-SPEC-001` sat here only to bootstrap the authoring process and was deleted
> at `59831ea5` once it had served that purpose — by then it had drifted to 640
> lines against a 1,355-line canonical source, silently dropping every section
> that recorded an open question."*

**The precedent is unanimous and was measured before this edit: no CP-SPEC for
`cp-00` through `cp-08` is published under `public/` at all.** Eight gates
closed without it. The surviving instruction here was stale, and it was caught
at rung 9's Gate 2 by an executor who stopped rather than following it.

**Why the deleted copy is the argument.** A specification is proven by the
artifacts and tests beside it; a copy somewhere else is proven by nothing, and
the first thing it loses is the sections recording open questions — which is
exactly what happened, and it happened silently, because a stale copy renders
perfectly well.

> ⚠️ `public/` has a strict docs build. **Any file you add under `public/`
> without a nav entry fails `mkdocs build --strict`.** That still holds for the
> reference documents this directory does carry.

> **`CP-SPEC-001_Counterparty_Reference_Snapshot.md` is a deliberately placed
> exemplar — *"what a spec would look like for counterparty reference"* (Dave,
> 2026-08-29) — and it is a **control, not a source.**
>
> The plan for rung 01 is that you author the spec **fresh from this recipe**,
> and Dave then compares your output against that file **by hand**. That
> comparison is a test of the recipe as much as of your spec, and it only works
> if you have not read CP-SPEC-001 as an input. **Deltas are expected and are
> the point.** Where your spec differs, the difference is the finding.
>
> So: author at `examples/cp-01-counterparty-reference-snapshot/spec/`. Do not
> copy from CP-SPEC-001, do not reconcile against it, and do not treat its
> values as authoritative — it predates the example-based structure, has no
> `artifacts/`, no witnesses, and the error classes cataloged in §10.2.

### 7.2 · The example layout

The spec is one file in a runnable example. Match `cp-01`'s layout:

```
examples/cp-NN-<slug>/
├── spec/CP-SPEC-NNN_<Product_Name>.md
├── artifacts/
│   ├── assembly-recipe.yaml   ← §D.2 as data, with a WITNESS per step
│   ├── expected.yaml          ← what the served product should contain
│   ├── question.yaml          ← the caller's vocabulary, read-side
│   └── ttl.yaml               ← the class TTL and its ceiling
├── assembler.py  produce.py  run.py  deployment.py
├── backends.yaml  ccf_config.yaml
├── page/                      ← build_page.py + template.html committed, render is not
├── README.md
└── summary_explanations.md    ← the banker-facing document
```

**The `page/` directory and `summary_explanations.md` are not optional**, and
what goes in them, plus the `example-cp-NN` target, the venv discipline and
the validation pass, are governed by
[How an example is delivered](example_delivery.md) — which is authoritative for
everything downstream of this section. This diagram is the summary; that
document is the recipe.

All `artifacts/*.yaml` validate against
`docs/schemas/ccf.declared-artifact.json`.

Follow `cp-00`'s `expected.yaml` discipline: **it derives nothing from a run.**
When artifacts change, run the suite, review the failure, and deliberately edit
the file in the same commit — so an expected-output change is an edit to a
reviewed artifact rather than a refreshed transcript.

---

## 8 · Definition of done — the specification

Ship when all of these hold. This is the standard's §15, plus what this pipeline
adds.

**These are the SPECIFICATION's conditions and they are half the deliverable.**
The example's conditions — the `make` target, the venv, the README run block,
the documentation page, the banker summary, the verbatim-output check and the
validation pass — are [How an example is delivered](example_delivery.md) §11.
Both lists must hold before anything is presented to Dave.

- **The spec was approved by Dave at Gate 1 before any implementation code was
  written**, and every Gate-2 deviation from the approved design was taken back
  to him rather than absorbed
- All seven sections present in order, with §0, front matter, capability gate
  and the data banner
- Four-question result carried from the vault **including partials**
- Nine contract elements populated, Assembly Mode with rationale
- Classification, residency, information-barrier complete; model-risk complete
  for Modes 2/3 or "not applicable" for Mode 1
- Every §C element has SOR, provenance class, classification, capability class,
  G dimension and ontology IRI — and **no §C row names a database**
- Capability decomposition present where the estate answer is unknown, with
  interim posture
- Correlation key stated with **measured** coverage, or the measurement named as
  an F.2 gap
- Every §D step names one closed-vocabulary operator with capability class,
  emits, failure behavior and budget — **and has a witness in
  `assembly-recipe.yaml`**
- The four composition invariants hold: Policy before any graph read · Resolve
  before Traversal · Enrich always batched · algorithmic substrate before any
  semantic stage
- Determinism class stated with an enum value; payload hash defined
- Replay statement plus a numbered falsifiable replay test that has been **run
  and observed to fail** when the snapshot is bypassed
- Emitted contract shown with types, conformant to the §8 envelope, passing
  `extra=forbid` in CI; error taxonomy mapped to steps
- Six universal gates plus product-specific gates with fixture IDs, **each made
  to fail deliberately at least once**
- Half-life table carries calibration basis and owner per row, and **no λ_c is a
  publication cadence**
- Per-component debt table present; contributions checked against
  `debt_tolerance`
- Materialization posture derived from measured λ_c against read frequency;
  cache key complete
- Every `no` or `partial` in §F has a named gap owner; volumetrics stated
- §G complete; consumers named individually; cascading supersession targets named
- **F.2 register complete — every `[TBC]` carries an owning agent**
- Acceptance criteria are failable assertions; blocking decisions named

---

## 9 · Cross-agent placeholder discipline

| Situation | Write |
|---|---|
| Vault has not framed something you need | `[TBC — vault]` + what you asked |
| Data reality unknown or unmeasured | `[TBC — ccf_dataprep]` + the measurement needed |
| Vault framing and build evidence conflict | `[TBC — ruling]` + both readings, verbatim |
| You have not built it yet | `[TBC — this build, phase Pn]` |

Never `[TBC]` bare. An unowned marker is an unassigned risk, and the F.2
register is what makes it collectable.

---

## 10 · Known conflicts — do not resolve these silently

**10.1 · `counterparty-reference-snapshot` grade and coverage — NOT blocking.
Author to the vault.**

The vault's scope boundary says *"identity only — no exposure, **no grade**, no
relationship."* CP-SPEC-001's payload declares `internal_risk_grade`,
`coverage_rm_id`, `coverage_team`, `coverage_lob` and an `internal_risk_grade`
freshness class. `ccf_dataprep` built to the vault's reading and carries **none**
of those fields.

**This is not a conflict between two authorities.** Scope boundary is the
**vault's term** under §1, and CP-SPEC-001 is an exemplar for later comparison
(§7.1), not a source. So:

- **Author to the vault's scope.** No internal overlay in rung 01.
- The overlay is then **not a debt component at all**, so CP-SPEC-001's
  0.30-against-0.25 `debt_tolerance` collision — and the `409` it implies —
  **does not arise.** That failure exists only under a per-component table
  counting a field the spec does not carry.
- **`ccf_dataprep` is already aligned.** Nothing needs regenerating.

If your build disproves the vault's scope, that is a §11 return, not a reason to
stop.

> **A ruling that was inferred rather than made.** On 2026-08-29 Dave pasted
> **both** documents — the vault's `counterparty-reference-snapshot` article at
> 03:23 MST with *"this is the one we need to build to"*, and the authoring
> Standard nine minutes later. Together that is the framing input and the
> structural basis: **the direction was unambiguous.**
>
> What it was not is a decision on the grade/coverage conflict, which §10.1 had
> marked blocking. **A document handover settles what you build to; it does not
> close a named conflict.** Those are closed by an explicit decision, named, or
> not at all — so **ask for one by name and wait.** Declining to close it alone
> was correct, and the inference pointed the right way.

**10.2 · Vault articles carry theoretical values that have been measurably
wrong.** Documented cases in `counterparty-reference-snapshot`: λ_c set to
publication cadence (24h vs ~365d); materialization posture inverted as a
consequence; `operators_invoked` as bare names; missing `payload_hash`,
`model_record` and the per-attribute authority field; a parameter surface
missing `debt_tolerance` and the inert `as_of`. **Assume the same class of error
in the other twenty.** Take framing from the vault; take values from your build.

**10.3 · The `references/` copies are history, not sources.**
`references/CP-SPEC-001_..._v2.md` and
`references/CP-SPEC-001_..._v0-3-restructure.md` are prior drafts. Read them for
audit history; author nothing from them. Same standing as CP-SPEC-001 itself
(§7.1).

**10.4 · Twenty vault articles are on the Q019 form** where §F means
*Manufacture envelope*. Resolve by heading name.

**10.5 · The vault's catalog count is stale** — it says 22 product specs in two
places; the measured figure is **21**, of which **20** declare no Assembly Mode.

---

## 11 · The return path

When your build contradicts an input, **send it back** — the failure this
pipeline exists to prevent is a correction that stalls at the boundary.

- **To the vault:** write into `~/.agent-exchange/<your-agent-id>/outbox/` as
  `<YYYY-MM-DDTHH-MM-SSZ>-<slug>.tmp/` containing `message.md` plus attachments,
  **then rename to drop `.tmp`** — the rename is what publishes it. A message
  left as `.tmp` never arrives, and this has already happened once: dataprep's
  2026-08-28 consumer signal sat unpublished until it was found by hand. State
  what your document **removes**, not only what it adds.
- **To ccf_dataprep:** same channel, their box is `ccf-dataprep`.
- **Your box is `ccf-sdk`** — `/home/parkave/.agent-exchange/ccf-sdk/`, with
  `inbox/`, `outbox/` and `_archive/`. Use that id, not a new one: a duplicate
  under a different id splits you into two agents.

Send back at minimum: any scope-boundary conflict, any λ_c the build disproves,
any element the vault names that the estate cannot supply, and any capability
the estate fails.

---

## 12 · Summary

1. Read the vault article — take **framing**, never values.
2. Pull the data reality from `ccf_dataprep` — **measure**, never assume.
3. Structure to the **Standard v0.3**, templated on **CP-SPEC-000**.
4. **Author the spec first, at `examples/cp-NN-<slug>/spec/`** — it is step one
   of the example project, and it lives with the code that will prove it. Mark
   what only the build can know as `[TBC — this build]`.
5. **▶ Send it to Dave. Stop. Nothing is implemented until he approves it.**
6. Build the example; fill the measured terms; clear every `[TBC]`. A build that
   disproves an approved term is a **deviation** — take it back, do not absorb it.
7. Never write another agent's term. `[TBC — owner]` instead.
8. Every claim discharged by something that runs; every gate made to fail once.
9. Send contradictions back, and **remember the rename**.
10. Work the ladder in order. Complexity is the vault's call, not yours.

``````

</details>

<a id="source-vault"></a>

<details>
<summary>Vault CP-02 banking specification — obsidian-vault@df5d8dea</summary>

Path: `wiki/context-products/content/facility-terms-snapshot.md`

``````text
---
product: reference.facility.v1
standard: q019
owner: ccf_code
sdk_spec: examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md
tier: 1
cost_band: "×1 (baseline)"
assembly_mode: null
capability_classes: [relational]
out_of_scope: [as_of-reconstruction, source-agreement-pointer]
prerequisites: [counterparty-reference-snapshot]
topic: context-products
title: Facility Terms Snapshot — Context Product Specification
summary: '**T1 · Postgres** — How does a product anchor on something other than a legal entity? A single credit facility''s terms, demonstrating the `from_entity_freshness` TTL anchor against a document-dated source.'
answers: '**T1 · Postgres** — How does a product anchor on something other than a legal entity? A single credit facility''s terms, demonstrating the `from_entity_freshness` TTL anchor against a document-dated source.'
generated: '2026-08-15T20:44:00-07:00'
sources: unknown
---
# Facility Terms Snapshot — Context Product Specification

**Tier 1** · Postgres only · `reference.facility.v1` · cost band ×1 (baseline)

> A single credit facility's economic and structural terms. Anchors on a facility rather than a legal entity, which is what makes it worth building separately from [[counterparty-reference-snapshot]].

---

## The four-question test — and the honest result

*Added 2026-08-30 at ccf-sdk's request; this article predates the section.*

| # | Question | Answer |
|---|---|---|
| 1 | Does the answer change with **who is asking**, beyond formatting? | **No** — jurisdiction and facility-level need-to-know change *visibility*, not assembled content. Same shape to every authorized caller. `Π` arrives at T5 |
| 2 | Does it have a **validity window** after which acting on it is wrong? | **Yes** — and it is the reason this product exists. Acting on superseded facility terms misprices a credit decision |
| 3 | Must it be **reconstructible** with the policy and freshness state that produced it? | **Yes** for the served contract. **No** for past state — `as_of` reconstruction is out of scope at T1 and arrives at [[covenant-in-force-as-of]] |
| 4 | Is it **composed at runtime** from sources no schema author pre-joined? | **Partial** — facility terms plus a borrower-LEI resolution and an entitlement decision. Two sources, one join |

> **One no, one partial, two yes** — the same honest shape as [[counterparty-reference-snapshot]], and admitted on the same kind of stated basis. This product is in the catalog **to teach `ttl_anchor`**, not on its composition merit. A reviewer is entitled to challenge that.

---

## A · Decision frame

**Decision & trigger.** A credit officer is reviewing a drawdown request, an amendment, or an annual renewal and needs the facility's current terms as a typed object rather than a PDF.

**Consuming principals.** Single role at this tier.

**Counterfactual failure — `temporally-incoherent`.** *(Taxonomy mode ruled 2026-08-30 at ccf-sdk's request; their proposal was correct. Every field is present and the defect is entirely on the time axis.)* **The wrong TTL anchor.** This product exists in the catalog to teach `ttl_anchor`. A facility's terms do not decay on a clock; they are valid until the agreement is amended. Anchoring its TTL `from_decision` — expiring it when the review window closes — collapses the cache for no reason. Anchoring `from_entity_freshness` keeps it live until the underlying agreement is superseded, which may be quarters away. §7.6 states the consequence plainly: get the anchor wrong and cache coherency breaks in one direction or the other. Here it breaks toward wasted derivation; in [[treasury-liquidity-position]] the same mistake breaks toward stale context driving a live decision.

---

## B · Contract

| Element | Value |
|---|---|
| **Schema** | `facility_terms` — entity: `CreditFacility`; attributes: facility type, commitment amount, currency, effective date, maturity date, pricing grid, administrative agent, borrower LEI, amendment number. No relationships. |
| **Freshness SLA** | Amendment-driven. Terms are current until an amendment files. |
| **TTL** | 90 days · `ttl_anchor: from_entity_freshness` |
| **Policy Binding** | Entitlement scope; facility-level need-to-know. |
| **Lineage** | `operators_invoked: [Resolve, Policy]` · `graph_snapshot_at` · `policy_version` |
| **Semantic Version** | `v1.0.0` |
| **Discovery** | `reference.facility.v1` |
| **Addressability** | `/context-products/reference/facility/{facility-id}` |

**Request parameter surface**

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `facility_id` | string, required | anchor | — |
| `intent` | enum, required | selects policy envelope | — |
| `include_pricing_grid` | bool | payload shape | `true` |

**Prerequisites.** [[counterparty-reference-snapshot]] — the borrower LEI must resolve.

**Deliberately out of scope at this tier.** No `as_of` parameter. Reconstructing terms as they stood on a past date requires ledger time-travel and arrives at [[covenant-in-force-as-of]]. No pointer to the source agreement text — passage-level lineage arrives at [[covenant-cross-reference]]. Both omissions are the tier boundary doing its job, and both are worth flagging to the SDK reader as *coming next* rather than as gaps.

---

## C · Data Catalog

| Element | Provenance | Class | Store | `G` |
|---|---|---|---|---|
| Facility type · commitment amount · currency | EDGAR **EX-10 credit agreement**, header and Article II — *extracted to structured rows* | public | Postgres | `E` |
| Effective date · maturity date | EX-10 credit agreement | public | Postgres | `E` |
| Pricing grid — margin by leverage tier | EX-10 pricing schedule | public | Postgres | `E` |
| Administrative agent identity | EX-10 preamble | public | Postgres | `E` |
| Facility type taxonomy (revolver, term A, term B, delayed draw) | FIBO — `CreditFacility` / `RevolvingLineOfCredit` in `FBC/DebtAndEquities/Debt/`, **not Loans**; see [[fibo-iri-binding]] | public | Postgres | schema |
| Aggregate debt reconciliation | 10-K debt footnote | public | Postgres | `E` |
| Amendment **number** (count of amendments on record) | 8-K **Item 1.01** filings | public | Postgres | `E` |
| Amendment **effective date** — when each amendment took effect | 8-K **Item 1.01** filings | public | Postgres | `E` |
| `facility_id` ↔ borrower LEI crosswalk | internal | **synthetic — internal** | Postgres | `E` |
| Outstanding balance · undrawn availability | internal loan system | **synthetic — internal** | Postgres | `E` |
| Internal facility risk rating | internal | **synthetic — internal** | Postgres | `E` |
| Entitlement scope — jurisdiction and facility-level need-to-know | entitlement service | **synthetic — internal** | Postgres | `P` |

**Extraction note for the assembly project.** The public elements here originate in *text*, not in a structured feed. At T1 they arrive pre-extracted as Postgres rows — the parsing is a build-time step performed once during data assembly, not a runtime operator. The source document itself is not addressable until MongoDB enters at T4. Keeping this boundary crisp matters: a T1 example that reaches into a document has silently become a T4 example.

**Correlation key.** `facility_id` internally; borrower `LEI` to join the entity side.

---

## D · Assembly Recipe

**Client call**

```
GET /context-products/reference/facility/FAC-000117
      ?intent=drawdown-review&include_pricing_grid=true
```

**Steps**

1. **Resolve Operator** → *Postgres.* `facility_id` → facility row. Fail closed if absent.
2. **Policy Operator** → *Postgres.* Entitlement check on the facility and its borrower. Emits `policy_version`.
3. **Contract assembly.** Build `FacilityTermsContract@v1.0.0`. `expires_at` derives from the **most recent observation of the facility's state** plus the 90-day window — **not** from request time, and **not** from origination. This is the step where `from_entity_freshness` becomes concrete rather than a field value.

> **Corrected 2026-08-30, and the correction is the point of the product.** This step previously read *"derives from the agreement's effective date plus the 90-day window"*, which contradicted §B's own *"amendment-driven — terms are current until an amendment files"* and §E's supersession trigger. Two bases, one article.
>
> **`effective_date` cannot be a freshness anchor, because it never advances.** A freshness anchor must be an *observation timestamp that moves* — `counterparty-reference-snapshot` anchors on vendor publication or KYC verification date, and both are re-observed. An origination date is fixed for the life of the agreement, so `effective_date + 90d` is not a refresh cadence: once passed it is **permanent expiry, and re-derivation cannot clear it.** That is a category error in the anchor, not a tight window.
>
> **The basis is the amendment record**: the latest 8-K Item 1.01 effective date where one exists, falling back to `effective_date` only for a facility with no amendment on record. **The estate holds amendment *counts* and not amendment *dates*** — see §F — so for any facility with `amendment_count > 0` the product **cannot evidence currency and must refuse.** `ccf-sdk` measured this on 2026-08-29: **50 of 60 facilities refuse, and all 43 carrying an amendment history are among them.**
>
> **The refusal is correct behaviour, not the failure §A names.** §A warns against expiring *"for no reason"*; here the reason is measured and stated — we know the agreement was amended and cannot say when. Serving those terms as current would assert a currency the estate cannot support. **The 90-day window stays** — against a ~540-day `λ_c` it is deliberately conservative, and the window was never the defect.

**Validation gates.** Empty-operator guard · lineage strict equality · TTL bounds.

---

## E · Volatility

| Signal class | `λ_c` | Notes |
|---|---|---|
| Structural terms — type, commitment, maturity | ~540 days | Amendment-driven, not clock-driven |
| Pricing grid | ~365 days | Repriced on amendment or refinancing |
| Outstanding balance | ~1 day | Moves on every drawdown and repayment |
| Internal facility rating | ~90 days | |

**Materialization posture: materialized**, with the outstanding balance carved out as an on-demand field. A product whose payload mixes a 540-day signal and a 1-day signal without surfacing the asymmetry is precisely what §6.4 Temporal Validation refuses to assemble — the split is not an optimization, it is the contract behaving correctly.

**Supersession triggers.** 8-K Item 1.01 amendment filing; internal drawdown event.

---

## Source binding gap — amendment effective dates

| Item | Status | Owner |
|---|---|---|
| **Amendment effective dates** | **`no` — the estate holds `facility.amendment_count`, `drawdown.amendment_number` and `system_trade_record.amendment_seq`: three counters and no date.** Dates that exist are synthetic and live in Fluree, a Tier-2 store this product must not read (`ccf_dataprep` `known-issues.md` §1.1) | ccf_dataprep |
| Consequence | Without them the freshness anchor falls back to origination, and 50 of 60 facilities refuse — see §D step 3 | — |
| Surfaced early | [[covenant-in-force-as-of]] (rung 08) exists to time-travel over exactly this event, and inherits this gap | — |

**This gap does not block the build.** It is stated, owned, and its consequence is served as a refusal rather than as a silent stale answer — which is the standard's position on an honest gap.

---

## F · Manufacture envelope

- **~40 facilities** across the ~50 anchor obligors, spanning revolver, term A, term B, and delayed-draw types
- **~8 facilities carrying at least one amendment**, so the amendment-number field is exercised and [[covenant-in-force-as-of]] has material to time-travel over
- **~4 facilities with a syndicated structure**, seeding [[syndicated-lending-co-lender]]
- Pricing grids with **at least 3 leverage tiers**, so the grid is a structure rather than a scalar

**Engineered, not fetched.** Outstanding balances, undrawn availability, internal ratings, and the facility-to-LEI crosswalk.

``````

</details>

<a id="source-spec"></a>

<details>
<summary>SDK CP-SPEC-002 — ccf_code@4494b936</summary>

Path: `examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md`

``````text
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
  `24.5-L-14` shipped the mechanism: the `effective_debt_ceiling` helper then in `src/ccf/products/gates.py` (DELETED 2026-09-04 by Phase 24.6 plans 03/04 under `D-IMPL-251` C1=A — a class may not hold a ceiling; what governs now: the class declares at most a DEFAULT, `default_debt_tolerance` on `src/ccf/products/contract.py::ServeObligations`, filling an omission only; the caller's `debt_tolerance` is honored as requested; the one fold is `src/ccf/products/constraints.py::resolve_effective_request`; a breach withholds fulfillment as the `tolerance-exceeded` shell from `src/ccf/products/gates.py::refuse_over_tolerance`, carrying the authority that set the tolerance; the debt half of `DeclaredObligationRefusal` and its `409` are retired, the new kind's HTTP status being assigned by class at the door in 24.6 plan 09 — `D-IMPL-257`)
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
| 12 | Debt-gate `409` behavior — **SUPERSEDED 2026-09-03** (Phase 24.5.1, `D-IMPL-245` (3)): the mechanism exists since `24.5-L-14` (the `effective_debt_ceiling` helper then in `src/ccf/products/gates.py` (DELETED 2026-09-04 by Phase 24.6 plans 03/04 under `D-IMPL-251` C1=A — a class may not hold a ceiling; what governs now: the class declares at most a DEFAULT, `default_debt_tolerance` on `src/ccf/products/contract.py::ServeObligations`, filling an omission only; the caller's `debt_tolerance` is honored as requested; the one fold is `src/ccf/products/constraints.py::resolve_effective_request`; a breach withholds fulfillment as the `tolerance-exceeded` shell from `src/ccf/products/gates.py::refuse_over_tolerance`, carrying the authority that set the tolerance; the debt half of `DeclaredObligationRefusal` and its `409` are retired, the new kind's HTTP status being assigned by class at the door in 24.6 plan 09 — `D-IMPL-257`); `DeclaredObligationRefusal` → HTTP 409 at `runtime/ccf_runtime/http_api/routes/product.py::build_router`); cp-02 declares no ceiling, so its behavior is unchanged — see §D.7's debt-gate note | §D.7 | this build | P7 |
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

``````

</details>

<a id="source-readme"></a>

<details>
<summary>SDK CP-02 README — ccf_code@4494b936</summary>

Path: `examples/cp-02-facility-terms-snapshot/README.md`

``````text
# examples/cp-02-facility-terms-snapshot — an expiry that belongs to the instrument, not to the question

Rung 02 of the vault's 21-product ladder, and the first product on it that
**anchors on something that is not a legal entity**. A credit facility is an
instrument: its identifier is internal, no external registry stands behind it,
and its terms do not decay on a clock — they are valid until the agreement is
amended.

That makes it the right place to make one primitive concrete.
`ttl_anchor: from_entity_freshness` means **`expires_at` is a function of the
facility, never of the request**. Ask the same facility twice, a fortnight
apart, and the expiry does not move. Rung 01 introduced the anchor; this is
where getting it wrong becomes visible, and where getting it right costs
something.

Specification: [`spec/CP-SPEC-002_Facility_Terms_Snapshot.md`](spec/CP-SPEC-002_Facility_Terms_Snapshot.md).
Gate 1 approved 2026-08-29.

## What this demonstrates

- **An expiry derived from a filed date.** `contract.expires_at` is the EX-10
  credit agreement's own *"dated as of"* clause plus 90 days. `asked_at` appears
  nowhere in the computation, and the payload carries `ttl_basis` so a consumer
  can check the arithmetic without reading the specification.
- **A policy step with two conditions**, where only one of them would have
  passed the obvious test. Facility-level need-to-know is a property of the
  *principal*; jurisdiction visibility is a property of the *borrower*. Three of
  the four principals in the estate see nothing at all.
- **A refusal you cannot probe.** A facility withheld by policy and a facility
  that does not exist produce byte-identical refusals. The distinction survives
  only in the replay record.
- **Three data traps, each served honestly rather than repaired**: four
  facilities whose maturity date precedes their effective date, seven with no
  maturity date at all, and 43 carrying an amendment count that the estate has
  no amendment *date* to go with.
- **A shipped finding, asserted by a gate that goes red when it is fixed.**
  50 of the 60 facilities are refused on `ttl-bounds` at the pinned instant.

## Run it

```bash
# 1. A fresh clone has no interpreter yet. This creates .venv/.
make venv

# 2. The read-only connection string for the facility estate.
#    The role needs SELECT and nothing else: nothing this example runs writes to
#    the store it reads, and a role that could write would make that a promise
#    rather than a guarantee.
#
#    Both libpq spellings work and neither is preferred:
#      export CCF_CP_02_POSTGRES_DSN='host=… port=… dbname=… user=… password=…'
#      export CCF_CP_02_POSTGRES_DSN='postgresql://user:pass@host:5432/dbname'
#    libpq also reads PGHOST/PGPORT/PGUSER/PGPASSWORD from the environment on
#    its own, so the variable's contents can be as short as `dbname=<database>`.
export CCF_CP_02_POSTGRES_DSN='dbname=<database>'

# 3. The one documented command. `-s` suppresses make's echo of the recipe,
#    which is the only thing that differs between this output and the
#    transcript published on the documentation page.
make -s example-cp-02
```

Without `make`, spelling the interpreter explicitly:

```bash
.venv/bin/python examples/cp-02-facility-terms-snapshot/run.py
```

**Variations that change the answer, not the formatting.** Each is a `make`
invocation because each is a request parameter, and a request parameter belongs
on the command line rather than in configuration:

```bash
# The same facility asked seventeen days later. `expires at` MUST NOT MOVE.
# This is the whole product in one comparison.
make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00

# A maturity date 196 days BEFORE the effective date. Serves, and refuses to
# compute a tenor. Its borrower is cp-01's own demonstration anchor.
make -s example-cp-02 FACILITY=FAC-66B83D

# No maturity date at all.
make -s example-cp-02 FACILITY=FAC-517638

# Drop the pricing grid. Changes the payload's SHAPE, so the content address
# changes with it.
make -s example-cp-02 NO_PRICING_GRID=1
```

**Variations that exit non-zero, and that is correct.** A refusal is not a
crash, but it is also not a success, so `make` reports `Error 1` and the shell
sees a non-zero status:

```bash
# ELEVEN amendments, effective 2026-05-29 — outside the 90-day window.
# Refused on `ttl-bounds`. This is 50 of the 60 facilities in the estate.
make -s example-cp-02 FACILITY=FAC-1FF50C

# A principal granted every jurisdiction in the estate and NO facility-level
# need-to-know. Refused, indistinguishably from a facility that does not exist.
make -s example-cp-02 PRINCIPAL=PRIN-RES-002

# A parameter this tier declares and always refuses.
make -s example-cp-02 AS_OF=2026-01-01T00:00:00+00:00
```

## The story

A credit officer opens a drawdown request. They need the facility's terms — the
commitment, the currency, the maturity, the pricing grid — as a typed object
rather than a PDF.

A loan-system screen returns all of that. What it cannot return is **a statement
of when believing it stops being safe.** So the officer reads terms that were
filed in 2021, and nothing on the screen says whether the agreement has been
amended eleven times since.

This product returns the same terms **plus** an `expires_at` derived from the
agreement's own date, a `ttl_basis` naming which date that was, a `context_debt`
score on the answer, and a refusal when the terms are older than the window
allows. The default run:

```
   asked as of        2026-08-29T12:00:00+00:00
   ttl basis          2026-07-29   (effective_date, the agreement's own date)
   expires at         2026-10-27T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   ...which does NOT move when `asked as of` moves — that is the anchor
   context debt D_c   0.0396  ->  ok
```

*Three lines lifted from the summary block of the default run; the full
transcript is in `page/run-transcript.txt`.* Its last line is `assembled by`:

The `assembled by` line names the assembler implementation that produced this run (`cp-02.facility-terms-snapshot@1.0.1`) — transcript evidence, read off the program's own stdout.

Replay carriage of that identity is a Phase 24.6 ledger row (`D-IMPL-245` amendment 1); the transcript is the evidence the example can carry today.

**What changed in this example on 2026-09-03.** The assembler's unreachable
compatibility branch — kept for a refusal the SDK could not, at the time, return
as data — was removed after the SDK gained the tier refusal (`24.5-L-12`/`L-13`),
so the implementation identity moved to `1.0.1` while the product stayed `1.0.0`,
because the served bytes and the contract did not change (`D-IMPL-245` (1)).

**The uncomfortable half is the point.** At the pinned instant, 50 of the 60
facilities in this estate are **refused** — their agreements are older than 90
days and the fabric will not vouch for terms whose currency it cannot establish.
The 43 that carry an amendment history are all in that 50. That is recorded as a
finding and taken back to the vault, not smoothed away: the specification's
§E.5 sets out both candidate anchor bases with the measurement that separates
them, and the one that would make every facility serve turns out to have a
single distinct value across all 60 rows — which is a product-level TTL wearing
a per-entity label.

## Artifact-by-artifact

| File | | What it carries |
|---|---|---|
| `spec/CP-SPEC-002_…md` | `[READ FIRST]` | The specification. Gate 1 approved; everything below derives from it |
| `ccf_config.yaml` | `[ADAPT]` | The Control Plane document — product class, the operator's parameters, the resolution rules, four λ_c classes, the debt bands, the policy regime and the default perspective |
| `backends.yaml` | `[ADAPT]` | How the graph's settings are composed and how the system of record is reached. A variable **name**, never a value |
| `artifacts/question.yaml` | `[ADAPT]` | The caller's vocabulary — anchor, intent, freshness, debt tolerance, and the pinned `asked_at` |
| `artifacts/ttl.yaml` | `[ADAPT]` | The 90-day window and its ceiling, with the measurement that constrains them |
| `artifacts/assembly-recipe.yaml` | `[ADAPT]` | §D.2's operator table **as data**, with a witness per step. A step nothing executes is red |
| `artifacts/expected.yaml` | `[ADAPT]` | What the served product must contain. Derives nothing from a run |
| `deployment.py` | `[ADAPT]` | The interpreter. Reads the documents above and answers what the spine asks |
| `produce.py` | `[MECHANISM]` | The spine — the fabric's call path, carrying the seven canonical regions |
| `assembler.py` | `[ADAPT]` | The governed seam, conforming to `ContextAssemblerProtocol` |
| `run.py` | `[ADAPT]` | The client |
| `summary_explanations.md` | | The same product explained to a banker rather than an engineer |

## Whitepaper / CLAUDE.md sections exercised

- **Whitepaper §7.6** — the Context Product Contract and its TTL anchor; §7.7
  half-life and Context Debt; §7.10 Decision Replay.
- **CLAUDE.md §6.4** — the No-Hardcoding Rule. Delete `artifacts/` and
  `ccf_config.yaml` and this example has nothing left to run.
- **CLAUDE.md §10** — single-writer: `booted.handle.worker` is the only write
  handle to L3 in the process, and the source estate is unreachable from it.
- **Standard §2.4** — the declared-but-inert parameter; §6.4 Temporal
  Validation, which is why §E.3's materialization posture needs a carve-out.

## What to change first

Point it at your own store. `backends.yaml` names one environment variable and
`ccf_config.yaml`'s `resolution:` block names the columns; between them they are
the whole binding. Then:

1. **Change the anchor** in `artifacts/question.yaml` to a facility of yours.
2. **Change the TTL** in `artifacts/ttl.yaml` — and read the note at the bottom
   of that file first, because the window and the *basis* are separate decisions
   and conflating them is how a cache collapses.
3. **Change the policy attribute** in `ccf_config.yaml` if your facilities carry
   their own jurisdiction rather than inheriting the borrower's.
4. **Add a signal class** to `half_life:` if your payload mixes cadences the way
   this one does — 540 days beside 1 day, in the same record.

## What would fail

**The published transcript reproduces against a named snapshot.** The default
run above was produced at commit `HEAD` of this example against the estate as
loaded on `2026-08-25`, asking as of the pinned
`asked_at: 2026-08-29T12:00:00+00:00`, and its content address is
`708a4a3f1a8486b125fdcbcbb848c3a43ae7cda81066ad3ee832aafe749d8b0c`. A reader
whose address differs has re-derived rather than replayed.

Things that would break, and how you would know:

- **Asking as of "now."** Every facility whose agreement is more than 90 days
  old refuses on `ttl-bounds`. That is 50 of 60 today and it grows. It is the
  fabric working, not a broken example.
- **Anchoring the TTL on `retrieved_at`** to make that go away. Every facility
  would then expire at the same instant, because that column carries **one**
  distinct value across all 60 rows. The gates would pass and the primitive
  would be gone.
- **Flattening the pricing grid** to a headline margin. Nothing fails loudly: a
  margin comes back, and the leverage tiers it depends on are simply absent.
  `FTS-G07` is what catches it.
- **Naming entitlement in a refusal.** `"you are not entitled to see it"`
  discloses that the facility exists. `FTS-G04` compares the two refusals for
  byte equality.
- **Reading `source_offsets`.** They are populated on 60 of 60 rows and sit in
  the same row as the terms. A T1 example that reaches into a document has
  silently become a T4 example.

``````

</details>

<a id="source-summary"></a>

<details>
<summary>SDK CP-02 summary — ccf_code@4494b936</summary>

Path: `examples/cp-02-facility-terms-snapshot/summary_explanations.md`

``````text
# Facility Terms Snapshot — what it is, what it is worth, and how it works

**Five questions about one credit facility, asked of one database, at one
instant.** This document records what came back, **what an ordinary query or
loan-system screen would have missed**, and **which mechanism produced the
difference.**

**Written for three readers at once.** A credit or lending subject-matter expert
should be able to read the consequence and skip the mechanism; an engineer
should be able to read the mechanism and find the file; a product manager should
be able to read both and know what is real, what is declared, and what is still
open. Each run carries the same three parts in the same order: **the output**,
**what you'd have missed**, and **how it works**.

Every figure below came out of a live run. None is illustrative. *"Why you can
trust these numbers"* says how to reproduce them, and *"Where each claim is
enforced"* maps every claim to the test that fails if it stops being true.

---

## The argument, in one paragraph

A report tells you what the data says. **A Context Product tells you what you
may rely on** — who may rely on it, how long it stays good, how complete it is,
and it refuses rather than guessing. The difference shows up on the day the
answer is wrong: a report hands you 2021 terms with today's date on the screen
and no way to tell; this product hands you the same terms with an expiry derived
from **the agreement's own date**, and declines to serve when it cannot vouch
for them.

**The one-line version of what is new at this rung:** the expiry is a property
of the instrument, not of the request. Ask twice, a fortnight apart, and it does
not move.

## Vocabulary

Each term twice: what it means to somebody reading the answer, and what it is in
the system.

| Term | What it means here | What it is |
|---|---|---|
| **Content address** | A tamper-evident seal on **one answer**. It only reproduces if every input did — the facility, the entitlements, the completeness score, the expiry. | `sha256` over the canonical bytes of the served product, excluding `assembled_at` |
| **Context debt** (`D_c`) | A completeness-and-freshness score **on that answer**, not a data-quality score on a table. Low is good. | `D_c = 1 − (F · C · S)`, multiplicative, so a collapsed dimension forces escalation instead of averaging away |
| **Principal** | Who is asking, and what they are permitted to see. | A row in `ccf_v2.principal` plus its jurisdiction grants; reaches the assembly as `Perspective` |
| **TTL anchor** | Which **event** the shelf life is measured from. The whole subject of this product. | `ttl_anchor: from_entity_freshness`; the basis is named in the payload as `ttl_basis` |
| **Facility** | One credit line — a revolver, a term loan — under one agreement. | The anchor: an internal identifier with **no external registry** behind it |

**The three steps, in the order the fabric runs them.** Every difference between
the runs below comes from one of these:

| Step | What it does | Where |
|---|---|---|
| **Resolve** | turns a facility id into a record, and names the date the expiry will hang off | L2, the single writer |
| **Policy** | substitutes the caller's permissible set *for* the full one | L4, before anything reads graph state |
| **Contract assembly** | computes the expiry and the debt, runs the gates, seals the answer | L6, and it is not an operator |

---

## Run 1 — the ordinary case, and the field a screen cannot show you

```bash
make -s example-cp-02
```

The reply carries the terms a credit officer expects — borrower, type,
commitment, currency, effective and maturity dates, the pricing grid with its
five leverage tiers, the outstanding balance and the internal rating. Then:

```
   asked as of        2026-08-29T12:00:00+00:00
   ttl basis          2026-07-29   (effective_date, the agreement's own date)
   expires at         2026-10-27T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   context debt D_c   0.0396  ->  ok
   content address    708a4a3f1a8486b125fdcbcbb848c3a43ae7cda81066ad3ee832aafe749d8b0c
```

*Five lines lifted from the run's summary block.*

| The line | What a banker reads |
|---|---|
| `ttl basis` | The expiry was measured from **the agreement's own signature date**, and the reply says so rather than leaving you to assume |
| `expires at` | After 27 October, acting on this without re-reading is not safe |
| `context debt D_c 0.0396` | This answer is 96% complete and fresh against its own standard |
| `content address` | Seal this reply, quote it in a memo, and anyone can prove later that it is the answer you were given |

**What you'd have missed.** A loan-system screen shows the same terms and no
expiry. So the officer caches the row — in a spreadsheet, in a memo, in their
head — and keeps reasoning against it. **The lift is not that the fabric is
clever. It is that the ordinary tool has no way to tell you the answer has gone
off, so nobody ever finds out that it did.**

### How it works

`deployment.py::expires_at` is one line: the facility's `effective_date` plus
`declared_ttl_seconds` from `artifacts/ttl.yaml`. **`asked_at` is not a
parameter of that function and cannot be** — which is the whole design, expressed
as a signature rather than as a comment.

The rest of the summary block:

| The line | What produced it |
|---|---|
| `ttl basis` | emitted by `Resolve` as a named date, not left for contract assembly to pick. The estate holds two dates a reader could plausibly believe the expiry uses — the agreement's `effective_date` and the extraction's `retrieved_at` — and they mean entirely different things |
| `context debt D_c 0.0396` | `FreshnessScorer` against the **structural-terms** half-life (~540 days), scored from the claim's `valid_from`. Which of the four half-life classes `F` is taken against is a decision, not an average: scoring against the 1-day balance would report a seven-year-stable object as perpetually stale |
| `amendments 1` | a **count**, and the payload claims no amendment *date* — the estate holds none anywhere, so nothing is asserted that cannot be evidenced |
| `operators invoked` | held to strict equality against what the engine resolved. A declared operator that did not run, or one that ran undeclared, is a refusal in either direction |

The last line of the block, `assembled by`, is new at `1.0.1`:

The `assembled by` line names the assembler implementation that produced this run (`cp-02.facility-terms-snapshot@1.0.1`) — transcript evidence, read off the program's own stdout.

Replay carriage of that identity is a Phase 24.6 ledger row (`D-IMPL-245` amendment 1); the transcript is the evidence the example can carry today.

## Run 2 — the same facility, seventeen days later

```bash
make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00
```

```
   asked as of        2026-09-15T23:45:00+00:00
   ttl basis          2026-07-29   (effective_date, the agreement's own date)
   expires at         2026-10-27T00:00:00+00:00   (ttl_anchor from_entity_freshness)
```

**The question moved. The expiry did not.**

**What you'd have missed, and this is the one worth pausing on.** The obvious way
to build an expiry is *"good for 90 days from when you asked."* It is also
wrong, and wrong in a way that costs money quietly: every time anyone asks, the
clock resets, so a facility whose agreement has not been touched since 2021 looks
freshly validated every single morning. **A staleness control that resets on
being read is not a control.** Here the expiry belongs to the instrument, so
asking about it more often does not make it any more current.

### How it works

Nothing here is a cache setting. `expires_at` is derived once, from a filed
date, and the derivation has no access to the clock. The seal *does* change
between the two runs — the request's temporal boundary is part of the answer —
which is why the gate asserting this compares **expiries** rather than seals. An
assertion that both must be equal would be false; one that both must differ
would be false too.

**Why the alternative was rejected, in one measurement.** Anchoring on
`retrieved_at` — when the extraction ran — makes every facility serve. That
column carries **one distinct value across all 60 rows**, so every facility
would expire at the same instant: a product-level TTL, behaviorally
indistinguishable from measuring off the request. The number that settles it is
1, not 60.

## Run 3 — a facility the product refuses to serve

```bash
make -s example-cp-02 FACILITY=FAC-1FF50C
```

This facility carries **eleven amendments**. Its agreement was signed on
2026-05-29 — outside the 90-day window. The product declines:

```
gate='ttl-bounds' detail='expires_at 2026-08-27T00:00:00+00:00 is outside (now, now + MAX_TTL] = (2026-08-29T12:00:00+00:00, 2026-11-27T12:00:00+00:00] (INV-CH7-48)'
```

*One line, lifted from the refusal.* The command exits non-zero, which is
correct: a refusal is not a crash, but it is not a success either.

**What you'd have missed.** Eleven amendments, and this bank's records contain
**no date for any of them** — the amendment filings were never mapped to the
facilities they amend. So nothing can establish that the terms on file are the
terms in force. A screen would have shown the 2026-05-29 terms with no caveat at
all. **The lift is a refusal you can act on instead of an answer you cannot
audit** — and the honest scale of it: at this instant, **50 of the 60 facilities
in this estate refuse**, and all 43 that carry an amendment history are among
them. That is a finding about the bank's data, surfaced by the product rather
than absorbed by it.

### How it works

`gates.py::_refuse_ttl` requires `now < expires_at <= now + MAX_TTL`, both
bounds from `artifacts/ttl.yaml`. This facility's agreement is older than the
window, so the lower bound rejects.

**The declaration was not widened to make this go away.** Both the 90-day window
and the anchor are the specification's terms; changing either to improve the
demonstration would be adjusting the measurement to fit the result. So the
number stands, the run produces the refusal, and gate `FTS-G09` asserts it —
**written so that it turns RED when the declaration is corrected.** That
inversion is deliberate: the test is not ratifying a defect, it is the evidence
the deviation gets taken back with, and nobody can quietly declare the problem
solved.

## Run 4 — terms that cannot be arithmetic

```bash
make -s example-cp-02 FACILITY=FAC-66B83D
```

```
    "borrower_legal_name": "AVIS BUDGET GROUP, INC.",
    "effective_date": "2026-06-29",
    "maturity_date": "2025-12-15",
    "tenor_days": "NOT_EVALUABLE",
```

*Four fields lifted from the reply.*

The maturity date **precedes** the effective date by 196 days. The product
serves both dates exactly as filed, and refuses to compute the tenor.

**What you'd have missed.** A tenor is a subtraction, and a subtraction always
returns something. A report would have shown **−196 days**, or `-0.5 years`, or
silently sorted this facility into the shortest-dated bucket of a maturity
ladder. **The lift is that a number which cannot be true is never presented as
though it were** — and that four facilities, all extracted from the same filing,
are flagged as one extraction problem rather than four independent oddities.

### How it works

`tenor_days` is the only **derived** field in the payload, and the only one that
could report arithmetic as a term. `_tenor_days` returns `None` for two
different findings that share one representation — an absent maturity date
(7 facilities) and an inverted pair (4) — and the payload distinguishes them
while the score does not, because `D_c` is one dimension and the notice is where
the difference belongs.

Both dates are still served exactly as filed. **Repairing them was available and
refused**: an invented maturity would enter a payload that claims `public`
provenance on that field, which is worse than an unusable claim, because it
looks answered.

## Run 5 — a question that is refused without telling you why

```bash
make -s example-cp-02 PRINCIPAL=PRIN-RES-002
```

This principal is granted every jurisdiction in the estate and holds **no
facility-level need-to-know**. The reply:

```
assembly refused: facility 'FAC-36D0CC' is not available (404); §D.2 fails closed rather than returning an empty payload. A facility_id has no external registry behind it, so an empty payload would read as 'this facility has no terms'
```

That is **the same sentence, to the byte**, that a request for a facility which
does not exist returns.

**What you'd have missed.** The natural message is *"you are not entitled to see
this facility."* It is also a disclosure: it confirms the facility **exists**.
Someone without permission could walk a list of identifiers and learn which ones
are real — the client list, recovered one refusal at a time. **The lift is that
'no' and 'not for you' are indistinguishable to the caller**, while the audit
record still holds exactly which principal asked and what was withheld.

### How it works

One shared function, `assembler.py::_not_available`, produces both refusals —
because the suppression rule is a statement about what a caller can
**distinguish**, and two separately-worded messages drift apart the moment
either is edited.

**This was a defect in the first build, and the run is what found it.** A
suppressed facility returned `200` with `facility: null` while a missing one
raised `404`. The payload carried no marker of what was withheld — and the
**status** carried it instead, which is the same disclosure arriving through a
channel the rule never named.

The two policy conditions compose in one place: the deployment computes the
permitted set as the principal's expanded jurisdiction grants **if** the
principal carries facility-level need-to-know, and the **empty tuple** if it does
not. So the suppression case is reached *through* the shipped operator rather
than around it — and gate `FTS-G03` exists because a two-condition policy where
one condition is inert passes every set-difference check.

## Why you can trust these numbers

Every figure above came from a run, and the run reproduces. The published
transcript was produced against the estate as loaded on **2026-08-25**, asking
as of a pinned **2026-08-29T12:00:00+00:00**, with content address
`708a4a3f1a8486b125fdcbcbb848c3a43ae7cda81066ad3ee832aafe749d8b0c`. Anyone with
read access can re-run the command in the README and compare that address; if it
matches, they have the same answer, not a similar one. The transcript was
re-captured on 2026-09-03 with that address unchanged.

**What changed in this example on 2026-09-03.** The assembler's unreachable
compatibility branch — kept for a refusal the SDK could not, at the time, return
as data — was removed after the SDK gained the tier refusal (`24.5-L-12`/`L-13`),
so the implementation identity moved to `1.0.1` while the product stayed `1.0.0`,
because the served bytes and the contract did not change (`D-IMPL-245` (1)).

The product's own checks are stronger than its documentation. Eleven of them
were **deliberately broken one at a time** to confirm each actually fails when
its subject is wrong — a check nobody has seen fail is not evidence that it runs.

## Where each claim is enforced

Every claim above is held up by a test that fails if it stops being true. This is
the table to read if the question is *"what stops this from regressing?"*

| The claim | The mechanism | The gate |
|---|---|---|
| The expiry does not move with the question | `expires_at` takes no request parameter | `FTS-G01` |
| Entitlement discriminates, as sets rather than sizes | `PolicyFilter` substitutes the permissible set at L4 | `FTS-G02`, with a negative control |
| Need-to-know does real work, not just jurisdiction | the two conditions compose into one allowlist | `FTS-G03` — removes the condition and requires the served set to change |
| Withheld and absent are indistinguishable | one shared refusal string | `FTS-G04` |
| `as_of` is refused, never silently honored | `unsupported_arguments:` in `ccf_config.yaml` | `FTS-G05` |
| No document pointer reaches the payload | the offsets are never read into the graph | `FTS-G06` — with a control asserting the columns **are** populated, so the gate is not proving that nothing leaked from a column that does not exist |
| The pricing grid is a tier structure, never a scalar | served as `basis` + a tier list | `FTS-G07` |
| An impossible tenor is withheld, not computed | `NOT_EVALUABLE`, never a negative number | `FTS-G08` |
| Terms older than the window are refused | `_refuse_ttl` | `FTS-G09` — **written to go RED when the declaration is corrected** |

**Eleven gates were deliberately broken one at a time and observed to fail**
before any of them was trusted. A check nobody has seen fail is not evidence that
it runs.

Two of those sabotages are worth naming. `FTS-G01`'s — repointing the expiry at
the clock — **passes every other test in the module** and fails only that one,
which is why it exists. And `FTS-G09`'s sabotage is *fixing* the defect, which
correctly turned it red.

---

## What these runs do NOT show

- **They are not a claim about any real company's borrowings.** The filed terms
  come from public credit agreements; the balances, availabilities, internal
  ratings and pricing margins are engineered for demonstration. No number here
  describes a real loan book.
- **No history.** This product answers *what are the terms now*. Reconstructing
  the terms as they stood on a past date needs capability that arrives later in
  the catalog, and asking for it here is refused explicitly rather than answered
  approximately.
- **No covenants, no collateral, no exposure aggregation, no syndicate detail.**
  Each belongs to a different product and each is deliberately out of scope.
- **The freshness figures are not calibrated.** The decay rates are expert
  judgment, not measurement, and the specification says so on every row. They
  are values an engineer can challenge rather than numbers anyone should assume
  were derived.
- **The 50-of-60 refusal rate is a property of this data**, not a prediction
  about a real portfolio. What generalizes is the shape: where amendment dates
  are not captured, currency cannot be established, and a fabric that says so is
  more useful than one that does not.

Where regulatory framing matters — trade reporting regimes that require an
active identifier, or supervisory expectations on model and data lineage — this
document deliberately stays general rather than citing a rule number that has
not been verified.

---

## The whole thing in one sentence

A loan-system screen returns terms. **A Context Product returns the same terms,
plus who may rely on them, plus an expiry measured from the agreement rather
than from the question, plus how complete the answer is, plus a seal that proves
it reproduces — and it refuses, indistinguishably, rather than confirming what a
caller is not entitled to know.**

And the engineering claim underneath it: **none of that is written in code.** The
window is an artifact, the four half-lives are an artifact, the entitlements are
a table, the operator plan is a document carrying a witness per step. What ships
in `/src` is the machinery that interprets them — which is why this product and
the one before it share a fabric without a line of it changing between them.

``````

</details>

<a id="source-implementation"></a>

<details>
<summary>Implementation walkthrough — refreshed 18 October 2026, SDK v1.0.2</summary>

Path: `05-reference/02-context-product-producer/examples/CP02_FACILITY_TERMS_SNAPSHOT.md`

``````text
# CP-02 — Facility Terms Snapshot

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-02-facility-terms-snapshot/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

> **Design companion (draft for review):** [Banking problem and specification analysis](CP02_FACILITY_TERMS_SNAPSHOT_ANALYSIS.md) · [HTML review edition](CP02_FACILITY_TERMS_SNAPSHOT_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-02-facility-terms-snapshot/README.md`  
**Qualified specification:** `examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md`  
**Qualified source:** `examples/cp-02-facility-terms-snapshot`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md`

Read it in this order before opening the Python:

| Spec section | What to learn | Where it lands |
|---|---|---|
| §A | decision, consumer, counterfactual, scope | README + acceptance tests |
| §B | product contract, request, TTL, policy/perspective | `ccf_config.yaml` + payload |
| §C | sources, identity, ontology, data traps | acquisition + environment/source declarations |
| §D | operators, projection, gates | `acquisition.py`, `deployment.py`, `projection.py`, `produce.py` |
| §E | half-life, Context Debt, materialization | config + assessment code |
| §F | source readiness and limitations | environment/source artifacts + findings |
| §G | acceptance and operational evidence | tests, gates, run evidence |

As you read the code, ask: **which approved spec term is this implementing?**

## Why this example exists

Shows a product whose lifetime belongs to the underlying instrument/document rather than to the request. It also teaches honest handling of source defects—impossible dates, missing maturity and incomplete amendment history—without repairing them in code.

## The question

> What facility terms are valid for this principal, when does that answer expire based on the agreement itself, and which source defects must remain visible?

## What to understand before you run it

- `from_entity_freshness` can anchor to a filed/effective instrument date.
- Need-to-know and jurisdiction are separate policy conditions.
- Bad source facts are served or refused honestly; they are not silently normalized into plausible values.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_02_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-02-facility-terms-snapshot/spec/` | The instrument-anchored contract and source traps. |
| `examples/cp-02-facility-terms-snapshot/artifacts/` | Question, recipe, TTL and expected behavior. |
| `examples/cp-02-facility-terms-snapshot/deployment.py` | Source-to-envelope and TTL/debt rules. |
| `examples/cp-02-facility-terms-snapshot/produce.py` | Governed assembly path. |
| `examples/cp-02-facility-terms-snapshot/run.py` | Documented variations. |
| `tests/examples/test_cp_02_output.py` | Behavioral/gate evidence. |

## Run it

```bash
make venv
make -s example-cp-02
make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00
make -s example-cp-02 FACILITY=FAC-66B83D
make -s example-cp-02 FACILITY=FAC-517638
make -s example-cp-02 NO_PRICING_GRID=1
make -s example-cp-02 FACILITY=FAC-1FF50C
make -s example-cp-02 PRINCIPAL=PRIN-RES-002
make -s example-cp-02 AS_OF=2026-01-01T00:00:00+00:00
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- Moving asked_at does not move expiry when the facility's own effective date anchors TTL.
- Malformed/missing maturity data remains explicit rather than being converted into a fabricated tenor.
- An old facility can refuse on TTL bounds.
- A principal with jurisdiction visibility but no facility-level need-to-know is refused.
- Dropping the pricing grid changes payload shape and therefore content identity.

Do not compare volatile content addresses or timestamps with prose unless the qualified SDK example itself publishes a pinned transcript. For exact byte-level claims, use the example's committed tests/transcript.

## How the example works

The general path is:

```
source estate (read only)
        ↓
acquisition / source interpretation
        ↓
SignalEnvelope(s)
        ↓
L2 assembly into governed L3 state
        ↓
L4 operators
        ↓
L5 projection Π over GraphView
        ↓
L6 Context Product gates / fulfillment
        ↓
served product OR governed refusal
```

The product-specific files above show where this rung changes that pattern.

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Move decision time | `make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00` | Expiry remains anchored to the facility date. |
| Impossible maturity | `make -s example-cp-02 FACILITY=FAC-66B83D` | Serves source defect honestly; does not invent tenor. |
| Expired facility | `make -s example-cp-02 FACILITY=FAC-1FF50C` | TTL refusal. |
| Need-to-know denied | `make -s example-cp-02 PRINCIPAL=PRIN-RES-002` | Governed refusal. |
| Unsupported parameter | `make -s example-cp-02 AS_OF=2026-01-01T00:00:00+00:00` | Explicit request-contract refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_02_output.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Instrument/source-date anchored TTL.
- Two-condition policy behavior.
- Refusal prevents probing suppressed existence.
- Data traps can be first-class documented findings.

## What it does not prove

- That the engineered source defects are production defect rates.
- That a 90-day TTL is a recommended policy.

## Spec → code lesson for Cowork

Copy the discipline: source anomalies belong in §C/§F and tests; do not 'clean' them in generated code unless the approved spec explicitly defines a governed transformation.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.
``````

</details>

