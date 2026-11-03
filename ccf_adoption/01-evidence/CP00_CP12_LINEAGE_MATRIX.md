# CP-00 through CP-12 — approved-lineage map

## Purpose

This document applies the Phase 1C lineage model to the approved Context Product ladder through CP-12. It is the evidence map that later Financial Services pages will use; it is not the finished public-facing use-case prose.

The evidence chain is:

`business problem / Vault → Dataprep data reality → SDK implementation specification → executable example/tests → adoption narrative`

## Release authority and status rule

For this map, the released SDK evidence baseline is:

- `drcastillo/ccf_code/main@1a04e565504f712350b51777cfe398be46d5e157`
- CP-12 is the latest approved rung on that baseline.
- Examples 13–24 are outside this map and remain part of the ongoing pressure-test program.

The `lifecycle`, `Gate 1`, or similar wording inside an individual specification is **historical workflow metadata captured when that specification was authored**. Some specifications still say `draft`, `awaiting Gate 1`, or describe a pre-build state even though the completed example later merged into the approved CP-12 baseline. Those fields are not used here as current release authority. The mismatch is preserved as a Phase 1C.3 metadata-governance finding rather than silently edited.

## Source snapshots

- Vault: `drcastillo/obsidian-vault/main@e10add2edc85efe8e355844edfecc492bcf9fa65`
- Dataprep: `drcastillo/ccf_dataprep/main@fcf7dddf79c7f443300d745e90bf39510ef12ab7`
- SDK: `drcastillo/ccf_code/main@1a04e565504f712350b51777cfe398be46d5e157`
- CCF concepts/whitepaper source: pinned separately in `CCF_SOURCE_MANIFEST.yaml`

## Ladder summary

| Rung | Context Product | Primary business question | Dataprep evidence | SDK specification | Controls / governance emphasis | Principal demonstration limit |
|---|---|---|---|---|---|---|
| **CP-00** | Institutional Holders | Who owns this issuer above the threshold that matters to the analyst? | `store-catalog.*`; measured 13F estate | `CP-SPEC-000-institutional-holders.md` | period pinning, provenance, match quality, replay | SDK warm-up, not a Vault/whitepaper-derived product; quarterly archive, not live ownership |
| **CP-01** | Counterparty Reference Snapshot | Who is this counterparty under the institution's identity authority hierarchy? | Wave 1 identity spine / crosswalk | `CP-SPEC-001_Counterparty_Reference_Snapshot.md` | entitlement/suppression, identity authority, replay | internal client master and entitlements are synthetic; no-LEI population is demonstrative |
| **CP-02** | Facility Terms Snapshot | What are the facility terms as signed/amended for this facility? | Wave 4 EX-10 facility extraction | `CP-SPEC-002_Facility_Terms_Snapshot.md` | temporal validity, source provenance, instrument freshness | internal balances/ratings/pricing/crosswalk are synthetic; demonstration estate has extraction defects explicitly called out |
| **CP-03** | Obligor Financial Spread | What financials and ratios describe this obligor at comparable periods? | Wave 2 XBRL facts / peer set | `CP-SPEC-003_Obligor_Financial_Spread.md` | per-claim freshness, filing lineage, restatement basis | one-store Tier-1 example; internal spreading conventions/adjustments are synthetic |
| **CP-04** | Corporate Family Tree — **canonical** | Which legal entities belong to the corporate family? | Wave 3 ownership graph + later corrections | `CP-SPEC-004C_Corporate_Family_Tree_Canonical.md` | bounded traversal, Debt, policy set, replay, source read-only posture | graph/relational coverage is intentionally thin; engineered cycle; canonical successor spec is retrospective |
| **CP-05** | Credit Exposure Rollup | What is the real group exposure after guarantees and cross-default structure? | Wave 9 + `spec-digest.md` | `CP-SPEC-005_Credit_Exposure_Rollup.md` | policy-defined counting, gross-vs-adjusted evidence, lineage | balances/limits and parts of topology are engineered; figures are demonstration values |
| **CP-06** | Collateral & Set-off Coverage | What actually secures this exposure and what can be applied against it? | Wave 9 + later UCC/public-register enrichment + known issues | `CP-SPEC-006_Collateral_And_Setoff_Coverage.md` | lien priority, enforceability, haircuts, read-only evidence | substantial internal/engineered valuations and enforceability; Fluree date/count caveats; spec authored after build |
| **CP-07** | Client 360 / Coverage Graph | Who at the bank knows whom at the client, through what, and how recently? | Wave 10 | `CP-SPEC-007_Client_360_Coverage_Graph.md` | need-to-know before traversal, bounded fan-out, truncation disclosure | bank-side people/interactions/deals are synthetic; full MNPI wall behavior belongs to later rung |
| **CP-08** | Covenant-in-Force As-Of | What was legally in force, and what did the institution know, at the decision date? | Wave 5 temporal covenant layer | `CP-SPEC-008_Covenant_In_Force_As_Of.md` | bitemporal correctness, replay, source immutability | booking lag is engineered; covenant terms are not historically versioned in this estate |
| **CP-09** | Treasury Liquidity Position | What is the client's cash/rate posture now, under the policy then in force? | Wave 12 treasury leg | `CP-SPEC-009_Treasury_Liquidity_Position.md` | per-signal freshness, policy completeness, Debt, replay | intraday rates/FX are engineered from daily public anchors; balances/limits/mandates are synthetic |
| **CP-10** | Rating & Spread Migration | Is this obligor deteriorating, and did the market move before the credit file? | Wave 11a | `CP-SPEC-010_Rating_And_Spread_Migration.md` | licensing/provenance boundaries, multi-clock divergence, freshness | no agency ratings and no TRACE; issuer-specific spread/instruments and internal grade history are engineered/synthetic |
| **CP-11** | Credit Surveillance / Early Warning | What changed since the last review, and does it matter? | Wave 11b | `CP-SPEC-011_Credit_Surveillance_Early_Warning.md` | supersession invalidation, stale-serve refusal, auditability | no push recall, no A2A invalidation in v1; no TRACE/per-mention sentiment; some signal chains synthetic |
| **CP-12** | FX Post-Trade Reconciliation | Is this break a timing artifact or a genuine error? | Wave 12 FX leg | `CP-SPEC-012_FX_Post_Trade_Reconciliation.md` | observation-time reconstruction, clock alignment, historical break replay | central timing/genuine-break conditions are engineered; public Part 43 is used to pattern structure, not supply the designed cases |

---

# Per-rung lineage

## CP-00 — Institutional Holders

**Canonical implementation**

- Example: `examples/cp-00-institutional-holders`
- Spec: `examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`
- Registry: `holdings.institutional-holders.v1`
- Position in learning model: **SDK warm-up before the Vault's 21-product ladder**.

**Business problem.** An analyst covering an issuer wants to know which institutional managers report positions above a caller-selected threshold, after a quarterly 13F reporting window closes. The threshold belongs to the caller; freezing one into the product would turn a question into configuration.

**Lineage posture.** CP-00 is intentionally different from CP-01–12: it was created to pressure-test the specification and SDK method and does **not** originate as a Vault product extracted from the whitepaper. The adoption site must say so rather than manufacture a Vault lineage that does not exist.

**Data reality.** The product itself reads public 13F/issuer data. The broader estate contains large engineered and synthetic populations, and the spec repeatedly warns that no displayed number should be treated as a fact about a real company. The archive covers many reported periods but is not a live holdings feed; issuer matching includes deliberately weak cases to exercise match-quality behavior.

**Controls / governance lens.** Filing-period pinning, provenance, match quality, caller-owned threshold, TTL/freshness, content identity, and Decision Replay.

**Proves.** A spec-first, Mode-1, relational Context Product can still carry governed validity, lineage and replay even when its assembly complexity is intentionally low.

**Does not prove.** Live beneficial ownership, complete institutional ownership of an issuer, multi-store composition, or production-quality matching coverage.

---

## CP-01 — Counterparty Reference Snapshot

**Canonical implementation**

- Vault: `wiki/context-products/content/counterparty-reference-snapshot.md`
- Example: `examples/cp-01-counterparty-reference-snapshot`
- Spec: `examples/cp-01-counterparty-reference-snapshot/spec/CP-SPEC-001_Counterparty_Reference_Snapshot.md`
- Registry: `reference.counterparty.v1`
- Dataprep: Wave 1 identity spine and crosswalk.

**Business problem.** Every downstream product needs a stable answer to *who is this counterparty?* before it can reason about exposure, risk, KYC or relationships. An LEI-only design silently drops privately held and middle-market borrowers with no LEI, so the failure is a population-exclusion problem rather than a bad join.

**Data reality.** `legal_entity` is public. The institution's `internal_client`, crosswalk and principal-jurisdiction records are synthetic-internal because public sources cannot provide a bank's client master or entitlement service. The no-LEI borrower population is deliberately engineered to demonstrate the exclusion failure.

**Controls / governance lens.** Identity authority ordering, entitlement/jurisdiction filtering, the suppression rule (excluded content must not leak a count or placeholder), lineage, freshness and replay.

**Proves.** A Context Product can make identity resolution and visibility rules explicit, typed and replayable before higher-level products consume the entity.

**Does not prove.** Any real institution's client master, real entitlement assignments, or the prevalence of no-LEI borrowers in a production portfolio.

---

## CP-02 — Facility Terms Snapshot

**Canonical implementation**

- Vault: `wiki/context-products/content/facility-terms-snapshot.md`
- Example: `examples/cp-02-facility-terms-snapshot`
- Spec: `examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md`
- Registry: `reference.facility.v1`
- Dataprep: Wave 4 facility extraction from filed credit agreements / 8-K amendments.

**Business problem.** Before exposure, collateral or covenant reasoning, a credit user needs the terms of the actual facility as signed and amended. A warehouse row overwritten to the latest terms can answer a historical drawdown with today's spread, maturity or commitment and still look perfectly valid.

**Data reality.** Filed EX-10 agreements provide public facility type, commitment, currency, effective/maturity dates and administrative-agent facts. Outstanding balances, undrawn availability, internal risk rating, pricing-grid margins and the facility-to-borrower internal crosswalk are synthetic-internal. The spec also records known demonstration extraction defects rather than smoothing them away.

**Controls / governance lens.** Instrument-level authority, effective-date semantics, source provenance, TTL anchored to entity/instrument freshness, explicit scope boundaries, and refusal rather than fabricated defaults.

**Proves.** A Context Product can anchor on an instrument rather than a legal entity and make the instrument's validity window part of the served contract.

**Does not prove.** A real bank's loan-system balances, internal ratings, pricing state, or error-free extraction across all credit agreements.

---

## CP-03 — Obligor Financial Spread

**Canonical implementation**

- Vault: `wiki/context-products/content/obligor-financial-spread.md`
- Example: `examples/cp-03-obligor-financial-spread`
- Spec: `examples/cp-03-obligor-financial-spread/spec/CP-SPEC-003_Obligor_Financial_Spread.md`
- Registry: `credit-risk.spread.v1`
- Dataprep: Wave 2 XBRL facts and period-aligned peer set.

**Business problem.** A credit officer sizing a facility or preparing a rerating needs standardized financials and ratios whose periods are actually comparable. Period end, filing date and retrieval date are different temporal facts; collapsing them into one "current" number makes a correct calculation operate on a stale frame.

**Data reality.** Public SEC XBRL supplies company facts, filing dates and restatement chains. The spreading convention, ratio definitions and internal adjustments are synthetic-internal/engineered where needed. The product is intentionally single-store and policy-light so attribute-level temporal validity is visible before graph complexity arrives.

**Controls / governance lens.** Per-attribute freshness, filing/accession lineage, explicit `basis` for as-reported versus restated values, replay, and honest treatment of the near-inert policy/perspective leg.

**Proves.** Temporal validity belongs to individual claims, not merely to a whole product.

**Does not prove.** A production spreading methodology, internal credit adjustments, or MNPI-conditioned financial statements.

---

## CP-04 — Corporate Family Tree — CANONICAL

Use `CP04_CANONICAL_LINEAGE.md` as the detailed exemplar. This matrix intentionally does not duplicate it.

**Only canonical path:** `examples/cp-04-canonical-corporate-family-tree`.

The frozen `examples/cp-04-corporate-family-tree` is historical evidence only and must never be the adoption implementation.

**Business problem.** Credit concentration and KYC decisions need the actual corporate family, not the immediate parent stored in a CRM field.

**Data reality.** Public FIBO/GLEIF/EDGAR structure is combined with deliberately engineered conditions such as a cross-shareholding cycle and synthetic bridging entities. Attribute coverage is intentionally incomplete and Context Debt reports the thinness rather than hiding it.

**Controls / governance lens.** Bounded acquisition, policy-authorized family set, Debt based on what was actually served, replay, read-only source posture, and explicit canonical-vs-historical implementation governance.

---

## CP-05 — Credit Exposure Rollup

**Canonical implementation**

- Vault: `wiki/context-products/content/credit-exposure-rollup.md`
- Example: `examples/cp-05-credit-exposure-rollup`
- Spec: `examples/cp-05-credit-exposure-rollup/spec/CP-SPEC-005_Credit_Exposure_Rollup.md`
- Registry: `credit-risk.exposure-rollup.v1`
- Dataprep: Wave 9 plus `docs/spec-digest.md`.

**Business problem.** A credit officer or portfolio manager testing a proposed facility against a group limit needs the risk connected through ownership, guarantees and cross-defaults—not a borrower-keyed sum. A flat sum can be wrong in both directions: double-counting guaranteed exposure and under-counting entities pulled into risk by a cross-default despite holding no facility themselves.

**Data reality.** Public EX-10 guarantor schedules and debt disclosures provide part of the structure. Balances, borrower-of edges, limit definitions and policy values are synthetic/internal; guarantee and cross-default topology is engineered where public extraction is too thin. Dataprep uses reconciliation to public XBRL debt as a credibility check rather than pretending synthetic commitments are observed bank balances.

**Controls / governance lens.** Versioned intent/policy determines whether guarantees and undrawn commitments count; gross and adjusted values are served side by side so the policy effect is visible. Cross-store lineage and replay preserve the path behind the number.

**Proves.** Graph traversal and deterministic aggregation can materially change an exposure answer while keeping the adjustment explainable.

**Does not prove.** Production exposure amounts, actual institutional limits, or complete guarantee/cross-default coverage for a real portfolio.

---

## CP-06 — Collateral & Set-off Coverage

**Canonical implementation**

- Vault: `wiki/context-products/content/collateral-and-setoff-coverage.md`
- Example: `examples/cp-06-collateral-and-setoff-coverage`
- Spec: `examples/cp-06-collateral-and-setoff-coverage/spec/CP-SPEC-006_Collateral_And_Setoff_Coverage.md`
- Registry: `credit-risk.collateral-coverage.v1`
- Dataprep: Wave 9, subsequent public-register enrichment, `known-issues.md`.

**Business problem.** A credit officer or workout team needs to know what actually secures an exposure, who else claims the same asset, at what priority, and which deposits are legally available for set-off. A facility-level `secured=true` field makes first- and second-lien positions look equivalent and omits competing claims and enforceability.

**Data reality.** Public credit-agreement collateral schedules and public filing/register evidence ground parts of the graph. Valuations, deposit balances, set-off/netting relationships, haircut schedules, enforceability rules and deliberately shared collateral cases are synthetic/internal or engineered. The implementation spec also records substrate-specific caveats: typed `xsd:date` writes are not relied upon in this Fluree build and certain counts are computed client-side because the backend count behavior is unreliable for the relevant pattern.

**Specification-process disclosure.** CP-06's implementation preceded its v0.3 specification. The spec states this as a deviation and was authored retrospectively. Adoption material should use it to explain why spec-first is preferred, not hide the exception.

**Controls / governance lens.** Lien priority, jurisdictional enforceability, haircut policy, provenance of public notices, Debt/freshness, read-only evidence, and explicit substrate limitations.

**Proves.** Relationship properties that belong to a pair—priority, pledge, set-off—need governed graph structure rather than a facility column.

**Does not prove.** Real bank collateral valuations, legal enforceability opinions, or universal public-lien coverage.

---

## CP-07 — Client 360 / Coverage Graph

**Canonical implementation**

- Vault: `wiki/context-products/content/client-360-coverage-graph.md`
- Example: `examples/cp-07-client-360-coverage-graph`
- Spec: `examples/cp-07-client-360-coverage-graph/spec/CP-SPEC-007_Client_360_Coverage_Graph.md`
- Registry: `coverage.client-360.v1`
- Dataprep: Wave 10.

**Business problem.** A banker preparing for a client meeting—or a coverage head examining relationship gaps—needs to know who at the bank has actually interacted with which client people, how, and how recently. CRM can usually answer "who covers the client?" but not the relationship path or which senior client officers nobody has met.

**Data reality.** Client-side officers come from public DEF 14A/Form 3/4/5/8-K sources. The bank side—bankers, coverage assignments, interactions, deals, scoring weights—is necessarily synthetic. Dataprep deliberately includes name variants, coverage gaps, need-to-know interactions and high-fan-out cases.

**Controls / governance lens.** Need-to-know shaping occurs before traversal, not as cosmetic redaction after assembly. `limit` and `since` are correctness controls because measured fan-out can exceed the declared bound. Full MNPI-wall semantics are not claimed here; that is a later ladder concern.

**Proves.** Relationship context is a bounded, policy-shaped path problem, not a CRM field lookup.

**Does not prove.** A real bank's CRM/HR/interaction estate, production relationship-strength scoring, or complete MNPI-wall enforcement.

---

## CP-08 — Covenant-in-Force As-Of

**Canonical implementation**

- Vault: `wiki/context-products/content/covenant-in-force-as-of.md`
- Example: `examples/cp-08-covenant-in-force-as-of`
- Spec: `examples/cp-08-covenant-in-force-as-of/spec/CP-SPEC-008_Covenant_In_Force_As_Of.md`
- Measurement note: `examples/cp-08-covenant-in-force-as-of/spec/MEASUREMENT-NOTE.md`
- Registry: `credit-risk.covenant-in-force.v1`
- Dataprep: Wave 5 temporal covenant layer.

**Business problem.** Credit, workout, audit and counsel may all ask about one historical drawdown but mean different things: what was legally in force then, and what had the institution actually booked/known then. Current-state storage answers both questions with today's state and gives no warning that it answered the wrong question.

**Data reality.** Covenant terms and amendment effective dates are grounded in public credit agreements and 8-K/EX-10 amendments. Facility/drawdown state and internal policy are synthetic. The crucial booking lag is deliberately engineered because an institution's booking date is internal and is not disclosed publicly; without that lag, valid-time and assertion-time answers would collapse into one another.

**Important limitation.** Amendment history is bitemporal, but covenant-term values themselves are not historically versioned in this demonstration estate. The product labels the served terms as unversioned rather than implying a historical reconstruction it cannot support. Half-life values are illustrative controls for the snapshot, not production recommendations.

**Controls / governance lens.** Two-clock reconstruction, forensic versus dispute views, replay, immutable/read-only sources, policy versioning, and explicit labeling of unavailable historical term versions.

**Proves.** Bitemporal context can distinguish what was true from what was known at the time of a decision.

**Does not prove.** Full historical reconstruction of covenant-term values or real institutional booking latency.

---

## CP-09 — Treasury Liquidity Position

**Canonical implementation**

- Vault: `wiki/context-products/content/treasury-liquidity-position.md`
- Example: `examples/cp-09-treasury-liquidity-position`
- Spec: `examples/cp-09-treasury-liquidity-position/spec/CP-SPEC-009_Treasury_Liquidity_Position.md`
- Registry: `treasury.liquidity-position.v1`
- Dataprep: Wave 12 treasury leg (`docs/wave12-design.md`, `docs/wave12-plan.md`).

**Business problem.** A treasury specialist advising a corporate client intraday needs the client's cash/rate posture under the policy in force at that instant. A healthy daily market-data pipeline can be perfectly compliant with its own refresh contract and still be wrong for an intraday decision; incomplete concentration-limit coverage can also make a confident "compliant" answer policy-blind.

**Data reality.** Public Treasury/FRED/SOFR/FX series and XBRL cash facts provide observed anchors. Intraday rate and FX ticks are deliberately engineered from real daily observations because the public sources are daily; every engineered tick is labeled accordingly. Client balances, positions, limits, mandates, regulatory posture and the stale-signal fixture are synthetic/internal or engineered.

**Controls / governance lens.** Different signal classes keep different temporal semantics and freshness; missing policy coverage must remain visible; Debt reflects partial/stale context; replay pins the decision boundary. The product is read-only against source stores.

**Proves.** One decision can legitimately combine several kinds of time and freshness without flattening them into one product timestamp.

**Does not prove.** Observed intraday market microstructure, real corporate treasury balances, real concentration policies, or recommended production half-lives/thresholds.

---

## CP-10 — Rating & Spread Migration

**Canonical implementation**

- Vault: `wiki/context-products/content/rating-and-spread-migration.md`
- Example: `examples/cp-10-rating-and-spread-migration`
- Spec: `examples/cp-10-rating-and-spread-migration/spec/CP-SPEC-010_Rating_And_Spread_Migration.md`
- Registry: `credit-risk.rating-migration.v1`
- Dataprep: Wave 11a (`docs/wave11a-design.md`, `docs/wave11a-plan.md`).

**Business problem.** A portfolio manager or credit officer wants to know whether an obligor is deteriorating and whether the market moved before the internal credit file. The signal is often the disagreement among series with different clocks; averaging them into a single quality score destroys the thing being detected.

**Data reality.** Public Treasury/FRED benchmark data and public ICE BofA OAS series supply market components. The issuer-specific spread residual and instrument reference are engineered; internal grade history and rating scale are synthetic-internal. The implementation consumes **no licensed agency ratings and no FINRA TRACE data**. The spec says so explicitly to prevent an adopter from mistaking a modeled demonstration leg for a redistributed licensed feed.

**Controls / governance lens.** Licensing/provenance boundaries, signal-specific freshness, bitemporal grade history, replay, deterministic decomposition, and versioned divergence thresholds.

**Proves.** A Context Product can preserve disagreement across signals and clocks and make the divergence itself the decision-relevant context.

**Does not prove.** Agency-rating integration, bond-level TRACE history, or production internal-grade processes.

---

## CP-11 — Credit Surveillance / Early Warning

**Canonical implementation**

- Vault: `wiki/context-products/content/credit-surveillance-early-warning.md`
- Example: `examples/cp-11-credit-surveillance-early-warning`
- Spec: `examples/cp-11-credit-surveillance-early-warning/spec/CP-SPEC-011_Credit_Surveillance_Early_Warning.md`
- Registry: `credit-risk.early-warning.v1`
- Dataprep: Wave 11b (`docs/wave11b-design.md`, `docs/wave11b-plan.md`).

**Business problem.** A portfolio-surveillance function needs to answer *what changed since we last looked, and does it matter?* without drowning in every historical event or aging away a fact whose relevance ends by supersession rather than time.

**Data reality.** Public SEC 8-K events, state WARN notices, GDELT mentions and XBRL deltas are combined with the engineered spread leg inherited from CP-10 and synthetic internal weights, thresholds, prior-observation anchors and supersession chains. The estate has no TRACE, no usable per-mention GDELT sentiment, and no dated Item 4.02 events in the target window; the spec names each limitation rather than filling it in.

**SDK-pressure-test result.** This rung exposed a real SDK gap: the original invalidation mechanism did not exist. `D-IMPL-334` added serve-time dependency invalidation so a product whose touched entity crossed a later supersession boundary becomes ineligible for future serving.

**Controls / governance lens.** Supersession/invalidation, touched-entity lineage, stale-serve refusal, signal-specific decay, replay and threshold governance.

**Important boundary.** Invalidation prevents **re-serving** an obsolete product. It cannot recall a copy a consumer already holds; there is no push notification/subscription/recall. A2A invalidation is also out of scope for v1.

**Proves.** Example pressure testing can expose a missing platform mechanism and drive a governed SDK capability rather than embedding a local workaround in the example.

**Does not prove.** Push recall, peer/A2A invalidation, per-mention media sentiment, or a production surveillance model.

---

## CP-12 — FX Post-Trade Reconciliation

**Canonical implementation**

- Vault: `wiki/context-products/content/fx-post-trade-reconciliation.md`
- Example: `examples/cp-12-fx-post-trade-reconciliation`
- Spec: `examples/cp-12-fx-post-trade-reconciliation/spec/CP-SPEC-012_FX_Post_Trade_Reconciliation.md`
- Registry: `markets.fx-reconciliation.v1`
- Dataprep: Wave 12 FX leg (`docs/wave12-design.md`, `docs/wave12-plan.md`).

**Business problem.** A middle-office analyst or control function sees two systems disagree about the same FX trade and must determine whether the difference is a timing artifact or a genuine error. Magnitude is insufficient: in the engineered estate, timing and genuine breaks deliberately overlap in size, so the answer comes from reconstructing each system's true observation instant and clock offset.

**Data reality.** Wave 12 uses a public DTCC Part 43 sample to pattern trade structure/timing and public FRED/H.10 FX reference data, but the central test conditions are deliberately engineered because no public source contains the needed paired institutional observations and clock-error cases. The designed timing and genuine breaks, system observations, amendment state and clock offsets exist to make the classification falsifiable. Public data shapes the scenario; it does not magically make the synthetic institutional systems real.

**Controls / governance lens.** Observation-time reconstruction, clock-offset governance, explicit comparison instant (`amendment-0` versus `latest`), materiality policy, replay and refusal-as-data. Both source stores are read-only.

**Second counterfactual.** Current state can not only create false timing breaks; it can **hide a real historical break** after later amendments reconcile the systems. The product preserves both the break state and the latest state as explicit request choices.

**Proves.** Temporal reconstruction can distinguish two discrepancy classes whose magnitudes overlap, and historical replay can preserve a break that current state has erased.

**Does not prove.** Real bank trading/settlement/risk-system observations, real clock skews, or production reconciliation thresholds.

---

# Cross-ladder findings to carry into Phase 1C.3

1. **Specification lifecycle metadata is not consistently current.** Several specs preserve `draft`, pre-build or Gate-1-era wording after the example later reached the approved baseline. Release state must come from the approved SDK baseline/gate history, not from one frontmatter field.
2. **Spec-first is the preferred process, but the ladder contains disclosed historical deviations.** CP-04 canonical and CP-06 are retrospective specifications. That history is useful adoption material because it shows why the process was tightened.
3. **Data limitation disclosure becomes more important as the ladder gets richer.** CP-08–12 explicitly distinguish public observation, internal synthetic data, engineered conditions, unavailable licensed feeds and demonstration-only calibration.
4. **Controls become architectural, not documentary.** The ladder progresses from provenance/replay to policy-shaped traversal, bitemporal reconstruction, Debt, invalidation, licensing boundaries and temporal reconciliation.
5. **The examples genuinely pressure-test the SDK.** CP-11 is a clear instance where the use case exposed a missing mechanism and the SDK was changed rather than the example inventing a private substitute.
6. **CP-00 must remain a warm-up, not be rewritten as a whitepaper-derived use case.** Its lack of Vault lineage is intentional and should remain visible.
7. **CP-04 is canonical only at `examples/cp-04-canonical-corporate-family-tree`.** The frozen sibling remains historical evidence only.

These findings are inputs to the 1C.3 gap/controls review; they are not yet final remediation decisions.