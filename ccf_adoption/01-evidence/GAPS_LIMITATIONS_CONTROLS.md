# Phase 1C.3 — Gaps, Limitations, and Controls / Governance Review

> **Historical evidence:** the program status and capability labels below describe the stated source pin. Current main includes CP-00–CP-24 and SK-01; see [SDK update status](../SDK_UPDATE_STATUS.md) and [current example configuration](../examples/CONFIGURATION.md).

## Purpose

This document is the adoption-facing control on what `ccf_adoption` may claim from the approved CP-00 through CP-12 evidence baseline. It separates four classes that must never be blurred:

1. **Demonstration-data limitation** — the public/reproducible estate intentionally substitutes engineered or synthetic-internal data for production-only information.
2. **SDK scope / capability limitation** — the approved SDK baseline deliberately does not provide a behavior, or the behavior is deferred to later rungs.
3. **Backend / substrate limitation** — a concrete database/runtime quirk affects how an example is implemented without changing the CCF semantic requirement.
4. **Process / metadata-governance limitation** — the evidence itself carries historical status, retrospective authoring, canonical-successor, or other governance conditions that must be interpreted correctly.

The register is **adoption-facing, not an exhaustive defect log**. Source specifications, gate records, READMEs, and `ccf_dataprep` known-issues material remain authoritative for rung-specific TBCs and detailed implementation findings.

## Evidence baseline

- Vault: `drcastillo/obsidian-vault/main@e10add2edc85efe8e355844edfecc492bcf9fa65`
- Dataprep: `drcastillo/ccf_dataprep/main@fcf7dddf79c7f443300d745e90bf39510ef12ab7`
- SDK: `drcastillo/ccf_code/main@1a04e565504f712350b51777cfe398be46d5e157`
- Latest approved rung on this baseline: **CP-12**

A control demonstrated by one of these examples is **evidence of the mechanism**, not a production certification of IAM, data quality, residency, model risk, operational resilience, or security for an adopting institution.

---

## 1. Cross-cutting findings

### F-01 — Demonstration values are not production facts

The CP ladder intentionally mixes public data with `synthetic — internal`, `synthetic — engineered`, and derived facts so that conditions unavailable in public banking data can be reproduced. Later use-case pages must preserve that provenance and must never present counts, balances, limits, ratings, thresholds, relationship graphs, booking lags, clock offsets, or policy values as facts about a real institution.

**Publication rule:** every Financial Services page requires a visible **Data Reality & Deliberate Limitations** section with `public`, `synthetic-internal`, `engineered`, and `derived` distinctions where they matter.

### F-02 — A demonstration-data limitation is not an SDK limitation

Examples frequently engineer the condition needed to falsify the naive approach: booking lags, cross-shareholding cycles, intraday paths, clock offsets, break classes, no-LEI clients, guarantee/cross-default edges, and similar fixtures. The mechanism remains valid even though the values are synthetic.

**Publication rule:** use wording such as *"engineered to exercise the temporal/control condition"*, never *"the SDK cannot use real data"* unless the actual SDK or source limitation says so.

### F-03 — Historical spec status is not release authority

Several SDK specifications preserve their workflow state at authoring time (`draft`, `awaiting Gate 1`, pre-build wording, etc.) even though their completed examples later merged into the approved CP-12 baseline.

**Publication rule:** current adoption release authority is the pinned approved `ccf_code/main` baseline. Historical spec frontmatter remains evidence of the development process, not the authoritative release-status field.

**Follow-up:** Phase 2/5 should define an adoption-facing metadata model with at least `evidence_baseline`, `example_release_state`, `spec_authored_state`, and `superseded_by` so these concepts are not collapsed into one `status` field.

### F-04 — CP-00 has no Vault lineage

CP-00 is an SDK/specification warm-up that predates the Vault's 21-product ladder.

**Publication rule:** do not manufacture a whitepaper/Vault origin for CP-00. Present it as a learning rung that pressure-tests the method.

### F-05 — CP-04 is canonical-only

The adoption implementation is `examples/cp-04-canonical-corporate-family-tree`. The frozen predecessor is historical evidence only.

**Publication rule:** no public navigation, tutorial, reproduction guide, or code pointer may send an adopter to the retired CP-04 implementation.

### F-06 — CP-00 through CP-12 are algorithmic evidence, not model-risk evidence

The approved ladder through CP-12 uses Assembly Mode 1 examples. It exercises deterministic assembly, policy, temporal semantics, graph traversal, freshness, Debt, replay, refusal, and invalidation, but it does **not** establish the adoption story for Assembly Mode 2/3 model use.

**Publication rule:** do not infer prompt/model governance, model-validation, model-version pinning, or semantic smoothing controls from CP-00–12. Those controls require later approved evidence.

### F-07 — Synthetic entitlement/policy fixtures prove control behavior, not enterprise integration

Identity, entitlement, need-to-know, jurisdiction, limits, haircuts, mandates, and related policy records are often synthetic-internal because public sources cannot provide a bank's private control plane.

**Publication rule:** say the examples prove the policy-bound behavior and fail-closed semantics; do not claim integration with a real enterprise IAM, entitlement service, policy engine, or records system.

### F-08 — Read-only source posture is part of the evidence model

The curated data estate is treated as evidence. Later rungs explicitly read source systems without mutating them; scratch/derived fabric state is separate.

**Publication rule:** reproduction instructions must preserve source immutability. A demo that mutates source evidence to manufacture the expected result invalidates the lesson.

### F-09 — Backend quirks must remain backend quirks

CP-06/07 expose concrete Fluree behavior around typed dates and query/count handling. The examples work around those conditions while preserving the CCF contract.

**Publication rule:** document the workaround in Sample Databases / backend notes, not as a universal CCF semantic requirement.

### F-10 — The current baseline has explicit control boundaries

Some controls are intentionally deferred or bounded: full MNPI-wall behavior is later than CP-07; CP-11 prevents re-serving obsolete products but does not recall a copy already held by a consumer; its invalidation rule is not an A2A rule in v1; production workflow/HITL/runtime surfaces remain provisional for adoption docs.

**Publication rule:** boundary statements belong next to the success claim, not in a footnote.

### F-11 — Licensed / unavailable market data creates honest source substitutions

CP-10 explicitly uses no agency ratings and no TRACE. CP-11 inherits the no-TRACE boundary and also lacks reliable per-mention sentiment and dated Item 4.02 events in the demonstration window.

**Publication rule:** never rename engineered/decomposed spread data as TRACE or synthetic internal grades as agency ratings. A reproducible example must preserve source legality and provenance even when a proprietary production estate would contain richer data.

### F-12 — Control evidence is not security assurance

The ladder demonstrates entitlement, suppression, policy binding, replay, lineage, invalidation, and fail-closed behaviors. That is not a vulnerability assessment, penetration test, threat model, or secure-deployment certification.

**Publication rule:** Security & Assurance must assess a named later SDK release/commit under its own methodology. No Phase 1C evidence should be promoted into an unqualified security claim.

---

## 2. Controls / governance coverage on the approved ladder

| Control domain | Evidence on CP-00–12 | Coverage posture | Adoption interpretation |
|---|---|---|---|
| **Provenance / lineage** | All rungs; especially CP-00–03 and CP-08–12 | **Demonstrated repeatedly** | Safe to teach as a central Context Product property; exact surface remains version-pinned. |
| **Decision Replay / reconstructibility** | Broadly across the ladder | **Demonstrated repeatedly** | Teach replay as evidence reconstruction, not as a model trace. |
| **Temporal validity / freshness** | CP-00–03, CP-08–12 | **Strongly demonstrated** | Includes period/instrument/claim-level validity, bitemporal cuts, multi-clock signals, supersession. |
| **Entitlement / suppression / policy shaping** | CP-01, CP-05–07 and product-gate evidence | **Demonstrated, enterprise integration not proven** | Mechanism can be taught; real IAM/control-plane integration remains adopter-specific. |
| **Bounded graph traversal / fan-out** | CP-04–07 | **Demonstrated** | Bounds are correctness and operational controls, not performance-only tuning. |
| **Context Debt / incomplete context disclosure** | CP-04 and later control-bearing rungs | **Demonstrated, exact scoring remains change-sensitive** | Teach concept and fail/degrade behavior; keep exact scorer contract pinned. |
| **Policy versioning / intent-conditioned answers** | CP-05, CP-06, CP-09–12 | **Demonstrated** | Values belong in versioned artifacts, not hard-coded SDK prose. |
| **Source immutability / read-only evidence** | Explicit in CP-08–12; project-wide evidence posture | **Demonstrated as example discipline** | Preserve in reproduction and assurance guidance. |
| **Supersession / dependency invalidation** | CP-11 | **Validated-current, deliberately bounded** | Prevents future re-serving of obsolete products; no push recall; no v1 A2A invalidation rule. |
| **Observation-time reconstruction / clock alignment** | CP-12 | **Demonstrated** | Strong markets/operations example; engineered break cases must remain disclosed. |
| **Information barriers / full MNPI wall** | Partial precursors in CP-07 | **Deferred on this baseline** | Do not claim full information-barrier coverage from CP-00–12. |
| **Assembly Mode 2/3 model-risk controls** | None in approved CP-00–12 ladder | **Not evidenced here** | Must wait for later approved examples before publication as demonstrated behavior. |
| **Production workflow / HITL orchestration** | SDK surface exists but Phase 1B classifies it provisional for adoption docs | **Provisional** | Keep out of the foundational CP-ladder claims until later stabilization. |
| **Security assurance / vulnerability posture** | Not performed by CP ladder | **Separate future phase** | Requires named release, threat model, VA methodology, findings and remediation record. |

---

## 3. Per-rung adoption limitations and control boundaries

| Rung | Demonstration-data limitation | SDK / control boundary | Backend / process boundary | Required adoption disclosure |
|---|---|---|---|---|
| **CP-00** | Quarterly 13F archive; deliberately weak issuer matches; broader estate includes engineered populations | Low-complexity single-store warm-up; not evidence for multi-store composition | No Vault/whitepaper origin | Label as pre-ladder SDK warm-up; no figures as real-company facts. |
| **CP-01** | Internal client master, crosswalk and principal/jurisdiction records are synthetic-internal; no-LEI population is engineered | Proves suppression / identity-authority behavior, not production IAM | Historical spec metadata may not equal current release state | Explain population exclusion and synthetic control-plane data. |
| **CP-02** | Balances, undrawn availability, ratings, pricing margins and internal crosswalk are synthetic; known extraction defects are retained | Does not prove production loan-system correctness | Spec captures pre-build workflow state | Separate filed terms from invented internal state. |
| **CP-03** | Internal spreading convention / adjustments are engineered or synthetic | Policy/perspective leg intentionally near-inert | One-store Tier-1 example | Use it to teach per-claim temporal validity, not production credit methodology. |
| **CP-04** | Thin graph/relational attribute coverage; engineered cycle/bridging conditions | Debt exposes missing coverage; does not imply complete corporate-family truth | **Canonical successor only**; predecessor retired for adoption | Point only to canonical example and disclose sparse/engineered graph conditions. |
| **CP-05** | Balances, limits and parts of guarantee/cross-default topology are synthetic/engineered | Proves graph-aware aggregation and intent-bound counting, not production exposure values | Spec frontmatter may preserve historical workflow state | Show gross vs adjusted side-by-side and disclose what is engineered. |
| **CP-06** | Valuations, set-off/netting, haircuts and enforceability are substantially synthetic/internal | Does not certify legal enforceability for a real jurisdiction | Fluree typed-date / count caveats; **spec authored after build** | Keep backend quirks and process deviation explicit; do not generalize either. |
| **CP-07** | Bank-side people, interactions, assignments and deals are synthetic | Need-to-know and fan-out are exercised; full MNPI wall is later | Uses backend date workaround inherited from estate | State that `limit` / `since` are correctness bounds; no claim of full information-barrier implementation. |
| **CP-08** | Booking lags are engineered; facility/drawdown/internal policy data synthetic | Bitemporal amendment mechanism is proven, but covenant **terms are not historically versioned** in this estate | Read-only source posture is explicit | Distinguish legal-effective time from institution-known time; label unversioned terms. |
| **CP-09** | Intraday rate/FX paths engineered from public daily anchors; balances, limits and mandates synthetic | Per-signal temporal semantics proven; holdings leg lacks an observed timestamp in the estate | Demonstration half-lives/calibration are illustrative | Do not describe synthetic ticks as observed market feed; surface missing freshness evidence rather than inventing it. |
| **CP-10** | Issuer-specific spread, instruments and internal grade history engineered/synthetic | No agency-rating or TRACE evidence | Licensing/provenance boundary is intentional | Never label decomposed spread as TRACE or internal grade as agency rating. |
| **CP-11** | Some signal chains and prior-observation anchors synthetic; no per-mention sentiment; no dated Item 4.02 event in window | Serve-time invalidation prevents re-serving obsolete products; **no push recall**, **no A2A invalidation in v1** | Gap was closed by SDK change; wording must reflect final approved mechanism, not superseded pre-gap prose | Put the recall/A2A boundary immediately beside the invalidation claim. |
| **CP-12** | Timing/genuine-break cases and clock offsets are engineered; Part 43 patterns structure rather than supplying designed cases | No new SDK gap on this rung; does not prove production clock-quality controls | Historical/current-state comparison is an explicit request axis | Explain that magnitude cannot classify the break; provenance of the engineered cases is part of the evidence. |

---

## 4. Adoption publication contract derived from 1C.3

Every substantial Financial Services use-case page built from this ladder must obey all of the following:

1. **Pin the evidence baseline** used for the page.
2. **Identify the canonical implementation path** and any superseded path.
3. **State the business decision before the SDK mechanism.**
4. **Separate public, synthetic-internal, engineered, and derived data.**
5. **Name the control mechanism actually demonstrated.**
6. **State what the control does not cover.**
7. **Distinguish data limitations from SDK limitations and backend limitations.**
8. **Show what the example proves and what it does not prove.**
9. **Treat historical specification status as workflow evidence, not current release authority.**
10. **Do not promote mechanism evidence into production certification.**
11. **Do not claim model-risk coverage from CP-00–12.**
12. **Do not claim security assurance from the CP ladder.**
13. **Carry known limitations next to the relevant success claim**, not only in a final caveats section.
14. **Prefer refusal, TBC, or explicit absence over invented completeness.**

## 5. Phase handoff implications

### Phase 2 — Portal architecture / Product Design

The page system needs visible, reusable treatments for:

- `Data Reality`
- `Control demonstrated`
- `Boundary / not proven`
- `Evidence baseline`
- `Canonical implementation`
- `Known limitation`

These should be first-class page components rather than prose conventions.

### Phase 4 — Using the SDK

Tutorials may reuse mechanisms from the CP ladder, but should use smaller learning examples where possible. Do not force a beginner through banking-specific engineered data merely to learn a generic SDK primitive.

### Phase 5 — Reference Manual

Reference material must stay pinned to an SDK baseline and preserve the maturity classifications from Phase 1B. Historical spec metadata must not become API lifecycle metadata.

### Phase 6 — Financial Services Use Cases

`CP00_CP12_LINEAGE_MATRIX.md`, `CP00_CP12_LINEAGE.yaml`, this review, and the source manifests together form the evidence backbone. A use-case page should be writeable from those artifacts without inventing the business problem, data provenance, limitation, or control claim.

### Security & Assurance

Security work remains a separate named-release assessment. This review supplies control inventory and known scope boundaries; it is not the security assessment itself.
