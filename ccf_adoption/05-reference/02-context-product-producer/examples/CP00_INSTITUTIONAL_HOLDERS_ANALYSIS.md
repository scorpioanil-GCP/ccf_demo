> **Current operations:** use [the refreshed implementation walkthrough](CP00_INSTITUTIONAL_HOLDERS.md) and Fluree **4.2.4** where required. The embedded specification remains historical evidence at its stated pin.

> **Reading copy:** [HTML edition](CP00_INSTITUTIONAL_HOLDERS_ANALYSIS.html), with rendered tables and sources included in this file.

# CP-00 — Institutional Holders — Analysis

**Audience:** banking SME and Information Architect. **Purpose:** reconstruct the journey from the business problem to this example’s final specification.

**Final specification:** `examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`, read directly from `drcastillo/ccf_code` at `37ac3055fd64ed64d78c6fd5555d79e451859153`. [Open the included final spec](#source-spec). Its recorded decisions, corrections, findings and placeholders are the destination of this walkthrough. The [Standard v0.3](#source-standard) supplies the template and the [generation recipe](#source-recipe) explains the ownership and evidence sequence.

The figures below are the final spec’s teaching-estate measurements or declared design values. They are not new runtime measurements. Once the design journey is understood, continue with the [implementation walkthrough](#source-implementation).

## Start with the banker's concentration question

A covering analyst wants to know whether an issuer's institutional register is concentrated in a few managers and which managers hold positions above a meaningful dollar size. The SME must supply that size: a threshold guessed by the product would answer a different question. The issuer is the anchor, the manager is the holder, and the security is the instrument being held. Confusing those roles before writing the spec makes every subsequent aggregate suspect.

Final-spec §A identifies `temporally-incoherent` as the primary counterfactual and `context-starved` as the second. An issuer-only holdings query combines periods and securities. The recorded estate contains 46 reported periods, and the example's issuer has six CUSIPs in the pinned period. Counting rows would also confuse positions with distinct managers. The analysis therefore begins by defining **one issuer, one reported period, one resolved security**, then applying the caller's position threshold.

## Populate the frame and contract — Standard §0–§B → final §0–§B

The product is algorithmic Mode 1: resolve, filter and aggregate filed numbers. The analyst needs a declared perspective and governed evidence, but this example does not vary assembled content by principal. Its source regime is public disclosure; the spec deliberately declines to invent a jurisdictional entitlement partition over public filings.

The following final-spec table captures the exact schema, 365-day TTL, registry, address, policy and lineage choices. The SME supplies the meaning of the position and period; the Information Architect gives them this contract form.

| # | Element | Value |
| --- | --- | --- |
| 1 | **Schema** | Payload type `institutional_holders_over_threshold`. Entities: **Issuer** (one, the anchor) and **InstitutionalManager** (many). Relationship: *manager reports a position in issuer*. Measures per manager: reported position value in USD, reported share count. Per-row signals: the resolved security, the reported period, the issuer-match band and score, the row's provenance class. **Artifact, not prose** — the machine-readable declaration is the `product_class:` and `resolution:` sections of `examples/cp-00-institutional-holders/ccf_config.yaml`, authored in the next wave; the payload schema key and version are `[TBC]` until it exists, and the marker reappears in §F |
| 2 | **Freshness SLA** | **Per signal class, not one value for the product**, and the SDK's shape is the same: `src/ccf/products/contract.py::FreshnessSLA` carries `max_age_seconds_by_signal`. Two classes. *Reported position* — **137 days** (a calendar quarter plus the 45-day filing deadline the source's own reporting rule sets): a position more than one full filing cycle old is not the current statement of the register. *Issuer identity* (legal name, from the reference table) — cadence **`[TBC]`**: the archive publishes no refresh interval for it and guessing one would be the §0.2 defect. Marker reappears in §F |
| 3 | **TTL** | **365 days · `ttl_anchor: from_entity_freshness`**, anchored on the **reported quarter end** — `to_date(report_period, 'DD-MON-YYYY')`, which for the pinned period resolves to exactly one date, `2026-03-31` (20,487 of 20,487 rows parse; Wave 1 measured it against a must-match control, not an `is null` control). See the note below: this is the most easily mis-read line in the document |
| 4 | **Policy Binding** | Regime: **public disclosure** — the source is a public regulatory filing. Version id: the deployment's policy bundle, `[TBC]` until the artifact is authored (§F, marker 5); its **version** rides the served product's lineage regardless of which bundle it is. **Entitlement scope: none is asserted, deliberately.** Every element in §C measures `provenance = 'public'` (22,476 of 22,476 rows in the holdings table, 156 of 156 in the reference table), so the highest classification of any element is `public` and there is no jurisdictional or entitlement partition to bind. Standard §2.1's named common error is *"asserting 'entitlement scope' with nothing behind it"*; a decorative scope on public-filing data is exactly that error, so this product asserts none and says why. `policy_version` is still emitted, so the ordering is established from the first product rather than retrofitted |
| 5 | **Lineage** | Six members, all present. See the mapping table below — including the two the Standard lists that this product deliberately does **not** carry, whose rows are stated rather than dropped |
| 6 | **Semantic Version** | **v1.0.0.** No prior supported version; migration window **n/a — this is the first version**. Change classes per Standard §12: adding a payload field or a new optional parameter is MINOR; changing `ttl_anchor`, changing the Assembly Mode, retyping or removing a field, or changing the required parameter's default (it has none — see §B.4) is **MAJOR** and requires a migration window with both versions served |
| 7 | **Discovery** | `holdings.institutional-holders.v1`. SDK surface: `src/ccf/products/contract.py::ProductDiscovery` (domain · intents · capabilities · audiences). **Not registered yet** — §G is unwritten, and Standard §2.1 names registering before §G is complete as the common error |
| 8 | **Addressability** | `/context-products/holdings/institutional-holders/{issuer-lei}` — anchored on the **issuer LEI**, a publicly resolvable identifier, and **not** on an internal surrogate key, which is §2.1's named error for this element. The anchor resolves: 48 of 48 distinct issuer LEIs in the pinned period join to the reference table, against a salted-join control that matched 0 of 48. SDK surface: `src/ccf/products/contract.py::ProductAddress` |
| 9 | **Assembly Mode** | **1 — pure algorithmic.** Rationale, one sentence as §2.1 requires: the answer is a filtered, resolved, aggregated set of filed numbers, so a model in the path would add cost and non-determinism and could only paraphrase what the substrate already states exactly. Fixed by `24-CONTEXT.md` `D-14`. **Assembly Mode is a registration-time commitment**, not an emergent runtime property; changing it is a MAJOR change |

The TTL is anchored on the **reported quarter end**, not on a missing row-update timestamp. At the pinned `31-MAR-2026` period, expiry is **2027-03-31**. The 365-day duration is the declared amended-filing window. A newer quarter's arrival and an amendment to this quarter are different events; the source is an archive, not a live holdings feed.

| Parameter | Type | Moves | Default | Notes |
| --- | --- | --- | --- | --- |
| `subject` | string, required | **E anchor** | — | The issuer LEI. An address field on `src/ccf/products/request.py::ProductRequest`, not a class-declared parameter |
| `intent` | string, required | **P envelope** | — | Address field on the same type. The intent **registry** Standard §11.1 requires is `[TBC]` — it does not exist in this deployment, so the accepted values are declared on the product class rather than resolved against a governed registry, and the marker reappears in §F |
| `freshness` | string, required | **T / P** | — | Address field: the currency the caller requires |
| `asked_at` | datetime, required | **T** | — | Supplied by the door, not by the caller's hand |
| **`minimum_position_usd`** | number, **required** | **a measure** | **none, deliberately** | The one caller parameter. Reported position value at or above which a manager appears. **No default:** a request omitting it is refused by `src/ccf/products/request.py::refuse_request` as `missing-required-parameter`, returned as a `src/ccf/products/request.py::ProductRequestViolation` — **data, not an exception** — *before the graph is touched* |

Preserve `minimum_position_usd` as required with no default, and its inclusive **`>=`** comparison. Percent-of-class concentration cannot be derived from this estate, and cross-period trends would require another temporal scope. Naming those exclusions in §B.5 protects the banking meaning of the answer.

## Bind the question to the data — Standard §C → final §C

The SDK spec reads `ccf_v2.institutional_holder`, with `ccf_v2.legal_entity` supplying the issuer's registered name. Here `lei` means **issuer LEI**, not manager identity. Managers are identified by CIK. The architect records the upstream issuer-match score/band as provenance quality and keeps it with each served position.

Three source findings decide the specification. First, an archive with many periods requires an explicit period pin; otherwise old and amended filings become one apparent current answer. Second, one issuer fans out to several securities, so the product **resolves the dominant CUSIP for `(issuer, period)`** rather than hardcoding a CUSIP or summing every instrument. Third, a weak issuer match is a disclosed quality signal, not permission to erase a holder. The spec serves both match bands. Its measured strong-only filter would remove 115 managers while removing none of the wrong-security rows; those rows were already strong. Security resolution and match quality solve different problems.

Section C's ontology placeholders remain owned gaps. Public provenance does not make an unsupported IRI binding available. The artifact carries the measured teaching-estate figures with their controls; this companion does not infer live-market holdings from them.

## Construct the recipe and temporal evidence — Standard §D → final §D

The final recipe separates the two meanings of Resolve. A source-boundary operator resolves the dominant security through a group-and-rank. The L2 assembly worker resolves canonical issuer/manager entities and their typed edges. Policy admits the permissible graph, TemporalAsOf establishes the as-of view, and projection shapes/ranks/aggregates the selected positions before contract validation.

This sequence comes from the analytical decisions: choose the security before counting holders; represent identities before reading their relationship; apply policy before projection; retain temporal meaning before presenting the result. The declared recipe and observed operator set must match in both directions. No model is needed to restate filed numbers.

The SME must distinguish **the reported quarter** from **when the fabric learned the claim**. The quarter anchors TTL; an as-of boundary earlier than ingestion can remove every observed claim. The spec's IH-G05 therefore requires an admitted assembled set at a valid as-of boundary. It also distinguishes an empty assembly, which fails closed, from a valid assembly with no position above the caller's threshold, which is an empty successful answer.

The hash/replay procedure changes underlying state, demonstrates a new live result, then reproduces the recorded result at its snapshot. A second temporal test uses an amended filing so the two time axes disagree. Without that discriminating case, a dropped time filter could look correct.

## Turn the findings into acceptance evidence

| Product gate | Why the banking analysis requires it |
|---|---|
| IH-G01 | Every served row belongs to the resolved CUSIP. |
| IH-G02 | Every served row belongs to the pinned reported period. |
| IH-G03 | Match quality travels with the position. |
| IH-G04 | A position exactly equal to the threshold is included. |
| IH-G05 | Temporal filtering leaves the expected assembled evidence before projection. |
| IH-G06 | Every declared entity class supplies the classification attribute policy requires. |
| IH-G07 | Empty assembly and empty threshold result have different outcomes. |
| IH-G08 | The payload reveals no count of rows read. |

These gates derive from concrete failure modes, and the final §G.2 requires each to fail on a seeded violation. A successful contract alone would not prove that the wrong period, security or comparator was excluded.

## Specify debt, readiness and operation — Standard §E–§G → final §E–§G

The architect connects source age, completeness and match quality to the debt model rather than treating every non-null row as perfect evidence. Signal calibration and issuer-identity refresh cadence retain their stated evidence status. The product is derived on demand; the final spec records observed latency separately from its initial step budgets, including the dominant L2 ingestion cost. An unachieved budget is not rewritten as a measurement.

Two TTL refusals require different operating explanations. When the reported period is older than 365 days, its lower-bound refusal follows the declared validity limit. If the deployment's `MAX_TTL` is too short, the upper-bound refusal is a configuration mismatch; the spec requires at least **31,536,000 seconds**. Those are distinguishable findings, not grounds to re-anchor expiry on request time.

Section F assigns source, ontology, artifact and operating measurements to named owners, retaining the evidence for markers closed during the build. Section G closes the journey with twelve criteria covering the governed contract and refusal branch, recipe/witness equality, strict lineage, all eight product gates, required threshold, equality boundary, exact replay, discriminating time axes, absence of model calls, printed spec/result and artifact-owned domain values. The final artifact explains both the answer and what evidence would falsify it; the implementation guide then realizes that specification.


## Included source snapshots

Exact retrieved source texts, with their original historical statuses and internal links retained as source text. Tables quoted within the walkthrough come directly from the final spec; Markdown pipe escaping is normalized for display.

<a id="source-spec"></a>

<details>
<summary>Final example specification — ccf_code@37ac3055</summary>

Path: `examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`

``````text
# Institutional Holders Over a Position Threshold — Context Product Specification

**CP-SPEC-000** · Authored to Specification Standard v0.3
(`references/Context_Product_Specification_Standard_v0-3.md`) · build order
`cp-00`, the first rung of the Context Production ladder.

---

> ## READ THIS BEFORE YOU READ A NUMBER
>
> **These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.**
>
> Every count, threshold and dollar amount in this document is here to show how a specification binds to
> a real store, and for no other reason.
>
> The surrounding data estate carries **deliberately engineered names and relationships** — measured estate-wide, 30,365 rows marked
> `synthetic — engineered`, 13,840 `synthetic — internal` and 20 `derived` —
> even though the two tables this product reads carry none of them
> (`ccf_v2.institutional_holder` 22,476 of 22,476 rows and `ccf_v2.legal_entity`
> 156 of 156 rows are `provenance = 'public'`). `ccf_v2.engineered_entity`
> carries no `lei` column at all, so no engineered entity can collide with an
> issuer LEI by construction.
>
> **No number here is a fact about any real company.**
>
> What the reader is actually looking at is **one quarterly archive spanning many periods** — 46 of them — and not a live feed, and issuer matching that is **~22.5% `weak`
> BY DESIGN** rather than by defect (§C.4 trap 3).
>
> The same four statements are repeated beside each figure cluster below,
> deliberately, rather than being left here as a header a reader scrolls past.

---

## 0 · What this document is

A specification of **one** Context Product — `holdings.institutional-holders.v1`
— written to the v0.3 format contract, for a product reading exactly **one
store and one system of record**.

**This spec is written BEFORE the assembly it specifies.** That is the point of
it. `24-CONTEXT.md` `D-01` rules that the Standard *"defines what needs to be
implemented in the SDK"* — it is a requirements source, not an authoring
convention — and `D-03` that these examples exist to **pressure test** the SDK.
A spec written after the code would describe the SDK; written before it, it
states what must be buildable and lets the later waves find out whether it is.
Where the SDK cannot express something this document orders, the gap is
**recorded and not closed** (`D-04`); closing it is a separate phase.

### 0.1 Do you need a Context Product? — the four-question test

| # | Question | Answer |
| --- | --- | --- |
| 1 | Does the answer change with who is asking, beyond formatting? | **No** — one principal at this tier; Π is registered but not exercised |
| 2 | Does the answer have a validity window after which acting on it is wrong? | **Yes** — the reported quarter is superseded by amendment, and the window is anchored on the quarter, not on the request |
| 3 | Must the answer be reconstructible after the fact, with the policy and freshness state that produced it? | **Yes** — every served answer carries a replay record |
| 4 | Is it composed at runtime from sources no schema author pre-joined? | **Partial** — one source table, plus an issuer-name join and a security resolution neither of which is pre-joined in the store |

**Two yeses, one no, one partial — and it is admitted on that stated basis.**
This product does not qualify on assembly merit; it qualifies on the TTL and
replay obligations, and on being the ladder's first rung. Recording the
qualified answer is the Standard's requirement (§0.1: *"A qualified yes is a
legitimate answer, but it must be written down as one"*), and a reviewer is
entitled to challenge the admission on exactly this basis.

### 0.2 Placeholder discipline

Items marked `[TBC]` require a decision or a measurement and have deliberately
**not** been guessed. Every marker reappears in §F with a named owner — **all eighteen of them,
in §F.2, as a table that can be diffed against the document.** Per the Standard, an unmarked assumption is the more serious defect: a
marked gap gets closed and an invented one gets built.

### 0.3 Section skeleton

**All seven sections appear, in order, and all seven are written.** §0.3's
rule is that an absent section reads as an oversight and a short one reads as a
decision, so where this product has little to say — §B.3's model-risk
annotation, §D.3's `Enrich` invariant — it says so in one line under its own
heading rather than omitting the heading.

| § | Section | In this document | State |
| --- | --- | --- | --- |
| A | Decision frame | `## Section A` | written |
| B | Contract | `## Section B` | written |
| C | Data catalog | `## Section C` | written |
| D | Assembly recipe | `## Section D` | written |
| E | Volatility, debt & materialization | `## Section E` | written |
| F | Source binding & readiness | `## Section F` | written |
| G | Operate & govern | `## Section G` | written |

### 0.4 Front matter

| Field | Value |
| --- | --- |
| Registry name | `holdings.institutional-holders.v1` — the `domain.product.vN` form Standard §12 requires. The approved **domain list** the standard assumes does not exist in this deployment; `holdings` is proposed, marker `[TBC]` for its approval, and it reappears in §F |
| Tier | **1** — `relational` only (§C.2). Tiers describe assembly complexity, not maturity and not build order |
| Assembly Mode | **1 — pure algorithmic.** `24-CONTEXT.md` `D-14`: *"an in process deterministic operator to assemble the context product"*. No model anywhere in the assembly path |
| Cost band | **×1**, the Tier-1 baseline. Standard §10.4's estimate resolves to the baseline here: no traversal (fan-out term 1), one enrich source, on-demand rather than materialized (factor 1), Mode-1 multiplier 1 |
| Lifecycle state | **draft** — not registered, not certified. Standard §2.1 Discovery: registering before §G is complete is the named common error; §G is now written, and what still holds this product in `draft` is §13's certification evidence — marker 15's cost half (§F.2) |
| Accountable owner | The CCF SDK examples maintainer. **This is a teaching artifact, not a production catalog entry**, so the product-owner / data-steward / policy-owner triad a real entry carries is `[TBC]` and reappears in §F. Naming a bank function here would be inventing an organisation, which §0.2 rates the worse defect |
| Last review date | 2026-08-26 |
| What the product resolves | Resolves one issuer, named by LEI, to the set of institutional managers reporting a position in that issuer above a threshold **the caller chooses**, for one reported filing period. It is the smallest product that still has to pin a period, resolve a security and carry a match-quality signal — which is why it is first |
| Four-question build test | No · Yes · Yes · Partial — recorded basis at §0.1 |
| Build-order note | **First.** `cp-00`'s `NN` is BUILD ORDER, never tier and never spec id (`24-CONTEXT.md` `D-18`/`D-19`); the spec id is `CP-SPEC-000` and the two are deliberately not the same numbering |

**Capability gate.** **None.** This product needs only the `relational`
capability class and is deliverable against any estate that can serve a
set-based query with a group-and-rank. It names no database: the Standard's
§10.1 rule is that *"Product specs never name a database"*, and the estate
binding — which schema, which table — lives in §C's system-of-record column and
in the deployment's own connection artifact, never in this document as a host,
port or credential.

---

## Section A — Decision frame

*(Standard §1.)*

**Decision & trigger.** An analyst covering an issuer needs to know **who owns
it and how much**, before an engagement, an event read, or a liquidity
judgement. The trigger is a **quarterly 13F filing window closing**: within 45
days of a calendar quarter end, institutional managers over the reporting
threshold file their positions, and the analyst's picture of the register is
stale until they do. The decision the product supports is a position-
concentration read on one issuer — *is this register concentrated in a handful
of managers, and who are they above the size that matters to me?*

The **size that matters** is the caller's, not the product's. That is the one
declared parameter (§B.4), and it is required with no default, because a
threshold nobody supplied is not a question this product answers.

**Consuming principals.** One role at this tier: the covering analyst. Every
authorised caller receives the same assembled content. Π is bound — the product
is served under a declared perspective — but it is **not exercised**: no
principal receives materially different content. A second principal needing
different content is a new version with a projection plan, not a formatting
change, and Standard §11.2 is explicit that a plan whose difference is
presentational is rejected.

**Counterfactual failure — `temporally-incoherent`, primarily, and
`context-starved` second.** The conventional answer to this decision is a
`SELECT` against the holdings table filtered by issuer. It returns rows. What
it does not return is a period boundary, a resolved security, an expiry, or a
match-quality signal, and the first two of those are not stylistic omissions —
they change the answer:

| Figure | Value |
| --- | --- |
| Distinct `report_period` in the table | **46**, spanning `31-DEC-2014` → `31-MAR-2026` |
| Rows in the pinned period `31-MAR-2026` | **20,487** of 22,476 |
| Distinct CUSIPs under the anchor issuer, pinned period | **6** |
| Rows vs distinct managers under the anchor, all 6 CUSIPs | **1,763 rows / 1,753 managers** — 10 rows of over-count |
| Managers whose only position is on a security that is **not** the resolved one | **5** |

> **Beside these figures, and not in a footer:**
>
> These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.
>
> The surrounding data estate carries **deliberately engineered names and relationships**; the two tables this product reads carry none of them, and every row of both measures `provenance = 'public'`.
>
> **No number here is a fact about any real company.** This is one quarterly archive spanning many periods, not a live feed, and its issuer matching is ~22.5% `weak` by design.

Every figure above is a Wave-1 measurement recorded with its positive control
in `.planning/phases/24.1-the-first-context-product-one-store-one-source-a-determinist/24.1-DATA-PROBE.md`;
none is re-derived in this document.

**Counterfactual acceptance test.** Written so it can fail, and so a reviewer
can run it against the built product rather than accept it on assertion.

| Step | Action |
| --- | --- |
| 1 | Ask the naive question: every row for the anchor LEI at or above the threshold, no period pin, no security resolution, counted by manager |
| 2 | Ask the product the same question, same threshold, same anchor |
| 3 | **The two answers must differ** whenever the anchor carries rows in more than one `report_period`, or on more than one CUSIP |
| 4 | Specifically: the naive answer admits the **5** managers holding only a non-resolved security, and double-counts the **9** managers appearing on more than one CUSIP (measured: 10 surplus rows over 1,753 managers). The product's answer admits neither |
| 5 | Where the two answers **agree**, the product is not doing the work this counterfactual claims for it, and this section is wrong rather than the test |

Step 3's condition is a condition, not a prediction: the estate carries 1,989
rows outside the pinned period (22,476 − 20,487, arithmetic on two measured
counts), so the out-of-pin population is non-empty estate-wide, but whether the
anchor itself carries such rows was not measured at spec time and the test does
not assume it. The CUSIP half of the test **is** anchor-specific and measured.

**What breaks without it, in a product owner's terms.** Nothing throws. The
analyst gets a plausible register, reads a manager into it who has not held the
name since a period restated from 2014, sizes a conversation on a number that
double-counts a manager filing across two CUSIPs, and has no way to tell,
afterwards, which of those things happened — because the answer carried no
period, no resolution and no expiry. **The failure is silent, and silence is
the reason this is a Context Product rather than a view.**

**Primitive taught.** Two, and they are the reason this product is first:

1. **Resolution before retrieval.** The security is **resolved** from
   `(issuer LEI, period)` to the dominant CUSIP — a `Resolve`, at the layers §D.3 works out — not pinned
   as a literal (`24-CONTEXT.md` `D-39`, Dave 2026-08-26). Standard §10.3's
   second composition invariant says traversal from an unresolved anchor
   *"answers plausibly about the wrong entity"*, and the five off-security
   managers above are that sentence with a number attached.
2. **A declared TTL anchor that is not a row timestamp.** `ttl_anchor` is
   `from_entity_freshness` anchored on the reported quarter, per
   `24-CONTEXT.md` `D-22`. See §B.1 element 3, which is the most easily
   mis-read line in this document.

**Contrast pointer.** `examples/s1-00-companies-over-revenue` makes the
opposite choice on the TTL axis — its Control Plane document declares
`ttl_anchor: from_decision` for the same shape of product (a caller-chosen
numeric threshold applied at Π over rows read from a relational store). The two
read together teach the anchor better than either does alone: one product's
validity starts when you ask, the other's started when the source reported.

---

## Section B — Contract

*(Standard §2. All nine elements of §2.1 are written; none is omitted, and
where an element's row is empty the emptiness is stated as a decision.)*

### B.1 The nine elements

| # | Element | Value |
| --- | --- | --- |
| 1 | **Schema** | Payload type `institutional_holders_over_threshold`. Entities: **Issuer** (one, the anchor) and **InstitutionalManager** (many). Relationship: *manager reports a position in issuer*. Measures per manager: reported position value in USD, reported share count. Per-row signals: the resolved security, the reported period, the issuer-match band and score, the row's provenance class. **Artifact, not prose** — the machine-readable declaration is the `product_class:` and `resolution:` sections of `examples/cp-00-institutional-holders/ccf_config.yaml`, authored in the next wave; the payload schema key and version are `[TBC]` until it exists, and the marker reappears in §F |
| 2 | **Freshness SLA** | **Per signal class, not one value for the product**, and the SDK's shape is the same: `src/ccf/products/contract.py::FreshnessSLA` carries `max_age_seconds_by_signal`. Two classes. *Reported position* — **137 days** (a calendar quarter plus the 45-day filing deadline the source's own reporting rule sets): a position more than one full filing cycle old is not the current statement of the register. *Issuer identity* (legal name, from the reference table) — cadence **`[TBC]`**: the archive publishes no refresh interval for it and guessing one would be the §0.2 defect. Marker reappears in §F |
| 3 | **TTL** | **365 days · `ttl_anchor: from_entity_freshness`**, anchored on the **reported quarter end** — `to_date(report_period, 'DD-MON-YYYY')`, which for the pinned period resolves to exactly one date, `2026-03-31` (20,487 of 20,487 rows parse; Wave 1 measured it against a must-match control, not an `is null` control). See the note below: this is the most easily mis-read line in the document |
| 4 | **Policy Binding** | Regime: **public disclosure** — the source is a public regulatory filing. Version id: the deployment's policy bundle, `[TBC]` until the artifact is authored (§F, marker 5); its **version** rides the served product's lineage regardless of which bundle it is. **Entitlement scope: none is asserted, deliberately.** Every element in §C measures `provenance = 'public'` (22,476 of 22,476 rows in the holdings table, 156 of 156 in the reference table), so the highest classification of any element is `public` and there is no jurisdictional or entitlement partition to bind. Standard §2.1's named common error is *"asserting 'entitlement scope' with nothing behind it"*; a decorative scope on public-filing data is exactly that error, so this product asserts none and says why. `policy_version` is still emitted, so the ordering is established from the first product rather than retrofitted |
| 5 | **Lineage** | Six members, all present. See the mapping table below — including the two the Standard lists that this product deliberately does **not** carry, whose rows are stated rather than dropped |
| 6 | **Semantic Version** | **v1.0.0.** No prior supported version; migration window **n/a — this is the first version**. Change classes per Standard §12: adding a payload field or a new optional parameter is MINOR; changing `ttl_anchor`, changing the Assembly Mode, retyping or removing a field, or changing the required parameter's default (it has none — see §B.4) is **MAJOR** and requires a migration window with both versions served |
| 7 | **Discovery** | `holdings.institutional-holders.v1`. SDK surface: `src/ccf/products/contract.py::ProductDiscovery` (domain · intents · capabilities · audiences). **Not registered yet** — §G is unwritten, and Standard §2.1 names registering before §G is complete as the common error |
| 8 | **Addressability** | `/context-products/holdings/institutional-holders/{issuer-lei}` — anchored on the **issuer LEI**, a publicly resolvable identifier, and **not** on an internal surrogate key, which is §2.1's named error for this element. The anchor resolves: 48 of 48 distinct issuer LEIs in the pinned period join to the reference table, against a salted-join control that matched 0 of 48. SDK surface: `src/ccf/products/contract.py::ProductAddress` |
| 9 | **Assembly Mode** | **1 — pure algorithmic.** Rationale, one sentence as §2.1 requires: the answer is a filtered, resolved, aggregated set of filed numbers, so a model in the path would add cost and non-determinism and could only paraphrase what the substrate already states exactly. Fixed by `24-CONTEXT.md` `D-14`. **Assembly Mode is a registration-time commitment**, not an emergent runtime property; changing it is a MAJOR change |

> **Beside the figures in this table** — the provenance counts at element 4, the join coverage at element 8:
>
> These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.
>
> The surrounding data estate carries **deliberately engineered names and relationships**; these two tables carry none, which is why the provenance counts read as they do.
>
> **No number here is a fact about any real company.** This is one quarterly archive spanning many periods, and its issuer matching is ~22.5% `weak` by design.

**On the TTL, because it is the point most easily mis-read** (`24-CONTEXT.md`
`D-22`). The SDK takes the anchor the spec **declares**:
`src/ccf/products/contract.py::TTLAnchor` is
`Literal["from_decision", "from_entity_freshness"]`, and nothing in it requires
a row timestamp. *"There should be a timestamp and there isn't"* is a data
defect; *"the dataset reports per period and the spec anchors on that period"*
is a normal freshness declaration. **This product is the second sentence.**
There is no gap here and no defect, and a later reader who finds one has read
the absent `last_updated` column rather than this declaration.

**Two consequences of that anchor, both structural, both owed to the waves that
build against this spec:**

1. `expires_at` = reported quarter end + 365 days = **2027-03-31** for the
   pinned period. The declared duration is the amendment window, not the filing
   cycle: this source is an amended-filing archive in which a period is
   restated years later (§C.4 trap 1), so what makes the answer wrong is a
   restatement of *that* period, not the arrival of the next one.
2. Because the anchor is the reported quarter and not the request instant,
   **the product's servability decays with the archive's age.** TTL bounds —
   `src/ccf/products/gates.py::run_gates` gate 3 — require
   `now < expires_at <= now + MAX_TTL`. Once the pinned period is more than 365
   days old, the gate **refuses to serve**, and that refusal is the mechanism
   working, not a bug to route around. It also fixes a Control Plane
   obligation: the class's `MAX_TTL` artifact
   (`src/ccf/products/contract.py::MaxTTL`) must declare at least
   **31,536,000 seconds**, or the same gate refuses at the upper bound instead.

**Lineage, member by member, against the SDK surface that carries it.**

| Standard member | Where it lands | Note |
| --- | --- | --- |
| `operators_invoked[]` | `src/ccf/products/contract.py::ProductLineage` field `operators_invoked` | Compared for **strict equality** against the engine-resolved set by gate 2 |
| `graph_snapshot_at` | `ProductLineage` field `graph_snapshot_at` | The temporal boundary the graph was read at |
| `policy_version` | `ProductLineage` field `policy_bundle_versions` | Plural in the SDK: the versions actually bound into the assembled state |
| `projection_plan_id` | `src/ccf/products/contract.py::ContextProductContract` field `plan_id` | On the vessel, not on the lineage sub-object |
| **`context_debt`** | `ContextProductContract` fields `debt` and `debt_evidence` | **Not optional.** Standard §2.1 names omitting it as *the* common error for this element, and the SDK produces it on every assembly and carries it **inside** the delivered bytes |
| `payload_hash` | `src/ccf/contracts/canonical.py::content_hash` over the vessel's canonical bytes; recorded as `product_content_address` by `src/ccf/replay/record.py::build_replay_record` | **A derived address, not a field on the contract.** Stated as it is rather than claimed as a field the type does not have |
| *passage anchors* | **Absent, by decision** | No claim in this payload rests on text. Nothing is extracted from a document, so there is no passage to anchor to; the row is stated rather than dropped |
| *`model_record`* | **Absent, by decision** | Mode 1. There is no model in the trust path, so there is no model to record |

### B.2 Classification and residency

| Field | Value |
| --- | --- |
| Data classification | **public** — the highest classification of any element in §C, and measured rather than assumed: both source tables are 100% `provenance = 'public'` |
| Information barrier | **none.** Filed institutional positions are public disclosure. If a future version joined internal coverage, pipeline or order data, it would become MNPI-bearing and move tier — that is a different product, not a bigger version of this one |
| Residency constraints | **none.** Public filings of a single national regulator |
| Cross-border serving | **permitted**, unconditionally, on the classification above |

**The suppression rule.** It has nothing to suppress here — no element is
withheld from any principal — but the product still obeys it structurally: the
payload carries **no count, marker or placeholder** of anything filtered out.
That matters for the threshold, which is a caller-chosen filter and not a
policy exclusion: the answer says what is above the line and is silent about
what is below it, rather than reporting *"n managers below threshold"*.

### B.3 Model-risk annotation

**Not applicable — no model in the trust path.** The heading is kept rather
than omitted, per Standard §0.3: *"A product with nothing to say in a section
writes one line explaining why."* Mode 1 is fixed by `24-CONTEXT.md` `D-14`,
and §2.3's annotation is required of Modes 2 and 3 only.

### B.4 Request parameter surface

**Exactly one declared class parameter** (`24-CONTEXT.md` `D-12` fixes the
caller surface at one), alongside the four address fields the SDK's request
type carries in its own right.

| Parameter | Type | Moves | Default | Notes |
| --- | --- | --- | --- | --- |
| `subject` | string, required | **E anchor** | — | The issuer LEI. An address field on `src/ccf/products/request.py::ProductRequest`, not a class-declared parameter |
| `intent` | string, required | **P envelope** | — | Address field on the same type. The intent **registry** Standard §11.1 requires is `[TBC]` — it does not exist in this deployment, so the accepted values are declared on the product class rather than resolved against a governed registry, and the marker reappears in §F |
| `freshness` | string, required | **T / P** | — | Address field: the currency the caller requires |
| `asked_at` | datetime, required | **T** | — | Supplied by the door, not by the caller's hand |
| **`minimum_position_usd`** | number, **required** | **a measure** | **none, deliberately** | The one caller parameter. Reported position value at or above which a manager appears. **No default:** a request omitting it is refused by `src/ccf/products/request.py::refuse_request` as `missing-required-parameter`, returned as a `src/ccf/products/request.py::ProductRequestViolation` — **data, not an exception** — *before the graph is touched* |

**Why the threshold is a dollar value and not percent-of-class, which is the
quantity a reader will expect.** Because percent-of-class is **not derivable
from this estate**, and that is a measurement rather than a preference:
`ccf_v2.financial_fact` carries 21 distinct XBRL tags, and `tag ilike
'%Shares%'` returns **[]** — against a positive control of `tag ilike
'%Revenue%'` returning **four** tags. There is no shares-outstanding fact, so
there is no denominator. A spec that quietly chose `value_usd` without saying
the other quantity was unavailable would be hiding a source-binding fact, and
this one belongs in §F as a source gap rather than in the reader's head as a
design preference.

**Two Standard requirements this surface does not meet, stated as divergences
rather than absorbed.** Standard §2.4 requires `intent` and `debt_tolerance` on
every product, and provides `not_supported_at_tier` for declared-but-inert
parameters. Measured against the SDK:

| Standard requirement | This SDK | Consequence for this spec |
| --- | --- | --- |
| `debt_tolerance` is a request parameter | The bands are **Control Plane state**, not caller state: `src/ccf/controlplane/artifacts.py::DebtProfile` carries `forced_llm_threshold` and `fail_closed_threshold`, version-pinned per class and landing in replay | **Not declared as a parameter, and that is the right call on the merits** — a caller who can move its own fail-closed band at request time can decide to be served context the deployment ruled too stale to decide on. Recorded as a Standard-vs-SDK divergence for the phase's gap register; **not closed here** (`D-04`) |
| Declared-but-inert parameters fail as `not_supported_at_tier` | An undeclared parameter is refused as `undeclared-parameter` by `refuse_request` | No inert parameter is declared (`D-12` fixes the surface at one), so nothing here silently succeeds. An `as_of` sent anyway **is** refused explicitly — the Standard's requirement — under a different reason name than its taxonomy uses. Recorded, not closed |

### B.5 Prerequisites, consumers and scope boundary

**Prerequisites.** None. `cp-00` is the first rung: it composes over no other
Context Product, and that is deliberate — a first product that needed a second
one to exist could not be the first thing a reader builds.

**Consumers.** None today. The later rungs of the Context Production ladder are
the intended consumers, and a MAJOR version here will need a notification list
the moment the second one exists. Recorded now so §E's supersession cascade has
somewhere to read a reverse dependency list from, rather than discovering it is
missing later.

**Deliberately out of scope**, each with where it goes — *coming next*, not
gaps:

- **More than one store or more than one system of record.** `cp-00` is one
  and one, by `24-CONTEXT.md` `D-13`; multi-source assembly is the next
  example's point rather than this one's obstacle.
- **Percent-of-class concentration.** Not derivable from the estate (§B.4). A
  source gap, recorded in §F.
- **Cross-period trend.** One reported period, pinned. Comparing two periods is
  a different question with a different temporal shape.
- **A live feed.** This is an archive. §C.4 trap 1 says what that costs.
- **Assembly Modes 2 and 3, products built off products, and the A2A leg.**
  Later rungs.

---

## Section C — Data catalog

*(Standard §3.)*

**One system of record: SEC Form 13F**, as loaded into
`ccf_v2.institutional_holder`, with `ccf_v2.legal_entity` supplying the anchor
company's registered name and nothing else. Schema and table only — no host,
no port, no credential appears in this document, and none may enter the example
tree.

### C.1 Element table

One row per element, not per column.

| Element | System of record | Provenance class | Classification | Capability class | G | Ontology IRI |
| --- | --- | --- | --- | --- | --- | --- |
| Issuer identity — the anchor company (`lei`) | SEC Form 13F (`ccf_v2.institutional_holder`) | public-filing | public | relational | **E** | `cmns-org:LegalEntity` |
| Issuer registered name | Entity reference (`ccf_v2.legal_entity`) | public-filing | public | relational | **E** | `cmns-org:LegalEntity` |
| Institutional manager identity (`manager_cik`, `manager_name`) | SEC Form 13F | public-filing | public | relational | **E** | `cmns-org:LegalEntity` |
| Held security (`cusip`) | SEC Form 13F | public-filing | public | relational | **E** | `[TBC]` — no bound term for a security identifier exists in this estate's IRI binding contract; §F |
| Reported position value (`value_usd`) and share count (`shares`) | SEC Form 13F | public-filing | public | relational | **E** (attributes of the reported position) | `[TBC]` — §F |
| Reported period (`report_period`) | SEC Form 13F | public-filing | public | relational | **T** | `[TBC]` — §F |
| Issuer-match score and band (`issuer_match_score`, `issuer_match_band`) | **Derived upstream** by the source system's issuer-name normalisation, **not** by this assembly | derived (upstream) | public | relational | **L** (a quality signal on the row's provenance) | `[TBC]` — §F |
| Row provenance flag (`provenance`) | SEC Form 13F loader | public-filing | public | relational | **L** | `[TBC]` — §F |
| **Resolved dominant security** for `(issuer, period)` | **Derived by this assembly** — the `Resolve` of §D.2 step 1. Written here as *L2* before §D was authored; measured, that half of the resolve is a group-and-rank at the source read and sits at **L1**, with the canonical-entity half at L2 — §D.3 | derived | public | relational | **E** | `[TBC]` — §F |

**On the `lei` column, because it reads backwards.** In this table `lei` is the
**ISSUER's** LEI — the company **held** — not the holder's. The holders are
identified by SEC CIK. So the product's anchor is the *held* entity, which is
the opposite of what a column called `lei` on a table called
`institutional_holder` suggests, and it is worth stating once in prose because
every query in §D depends on it.

**On two `derived` rows, and the Standard's rule about them.** Standard §3.1
says *"derived requires the derivation to appear in §D."* Only one of the two
can honour that: the **resolved dominant security** is derived by this
assembly's `Resolve` step and appears in §D as a step
(`24-CONTEXT.md` `D-39`/`D-41`). The **issuer-match score and band** are
derived by the *source system's* loader before this product ever reads the row,
so no §D step produces them and none will be invented to satisfy the rule. The
derivation's owner is the source system; the marker goes to §F. Stating this is
more useful than a §D step that describes work this assembly does not do.

**Primary key of the source row:**
`(lei, manager_cik, cusip, report_period)`.

> **Beside this table:**
>
> These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.
>
> The surrounding estate carries **deliberately engineered names and relationships**; these two tables do not, and `ccf_v2.engineered_entity` carries no `lei` column at all, so an engineered entity cannot collide with an issuer LEI by construction.
>
> **No number here is a fact about any real company.** This is one quarterly archive spanning many periods, and its issuer matching is ~22.5% `weak` by design.

### C.2 Capability decomposition

One capability class is required — `relational` — which is why this is Tier 1.
The decomposition is written anyway, because §3.2's point is that an estate
rarely fails a capability wholesale: it satisfies some properties and fails
others, and *that* is the finding worth having.

| Property | Common estate answer | If absent |
| --- | --- | --- |
| Set-based retrieval of one issuer's holder rows in a single round trip | Widely available | Degrades to per-manager fan-out; §D's budget becomes unachievable and the product's cost band is no longer ×1 |
| A reporting period that can be pinned and ordered deterministically | Widely available | **Blocking.** Without a pinnable period the product cannot answer about one quarter at all, and §C.4 trap 1 is unavoidable rather than handled |
| Group-and-rank in the source, to resolve the dominant security for an issuer and period | Sometimes — many estates can group but will not rank inside a read | Degrades to a **named partial**: the security moves from a resolved value to a second caller parameter, which restores the fan-out over-count the resolve step exists to remove. Interim posture below |
| Per-row quality signals (match band, provenance) carried through to the payload rather than dropped at the source boundary | Rare | Degrades to a named partial: the band survives only as an input to §E's debt model and stops travelling with the row, so a consumer can no longer see *which* rows are weakly matched — only how much debt the set carries |

**Interim posture, for the one property likely to be partial.** If the estate
cannot rank inside a read, the deliverable product is: the same anchor and the
same threshold, with the security supplied by the caller as a second required
parameter; the resolve step drops out of §D; the payload declares
`security_resolution: caller-supplied`; and the version ships as
**`v1.0.0-partial`** rather than as `v1.0.0`. Shipping a partial as though it
were complete is the failure §3.2 exists to prevent, and a version string that
does not say so is how it happens.

### C.3 Correlation key, single-writer discipline, and identity authority

**Correlation key.** Two, at different grains, and it matters which is which:

| Key | Grain | Role |
| --- | --- | --- |
| `(lei, report_period)` | issuer + quarter | **The resolution key.** The `Resolve` step reads it and emits the dominant security |
| `(lei, manager_cik, cusip, report_period)` | one filed position | The source row key — the table's primary key |

**Measured crosswalk coverage**, which §3.3 requires rather than a footnote:
the issuer-identity crosswalk from the holdings table to the reference table
matched **48 of 48** distinct issuer LEIs in the pinned period. Positive
control: the same join with a salted key matched **0 of 48**, so the instrument
distinguishes rather than always agreeing.

**Single-writer discipline.** Two statements, one about the source estate and
one about CCF, and they are different claims:

- *In the source estate*, one system is authoritative per element: the 13F
  loader writes the position elements, the entity reference table writes the
  issuer's registered name. No element is written by two.
- *In CCF*, only L2 holds a write handle to L3 (`CLAUDE.md` §10, and it is
  architectural rather than advisory). Every row this product reads enters the
  graph **through the assembly worker's ingest and through nothing else**. The
  product's two substrates are visibly different — the CCF graph is a per-run
  local file, the system of record is a read-only relational source — so no CCF
  write path reaches the source estate at all. Nothing this product runs writes
  to the store it reads.

**Identity authority hierarchy.**

| Entity class | Identity authority | Status source | Freshness ceiling |
| --- | --- | --- | --- |
| Issuer (the anchor) | LEI, as carried by the filing | The reference table's registered name | The reported quarter — §B.1 element 3 |
| Institutional manager | SEC CIK (`manager_cik`) | The filing's own submission record | The reported quarter |

**One caveat on the manager authority, because it is a real property of the
source and not a hypothetical.** `manager_cik` was once derived from the
filing-agent prefix of the accession number, which collapsed distinct managers
onto one identifier — the source's own record reports 63 of 2,450 CIK values
mapping to more than one manager name, one across 290 managers. It was **found
and fixed** by joining the submission record for the real manager CIK
(`ccf_dataprep/docs/known-issues.md` §8.3), and the post-fix reading is 0 CIK
values mapping to more than one name. The product therefore anchors managers on
CIK **and** carries `manager_name` in the payload, so a consumer can see the
identity rather than trust it silently.

### C.4 The three data traps, each with the binding chosen and what it costs

Each trap below was measured at Wave 1 with a positive control recorded beside
the figure in `24.1-DATA-PROBE.md`. The bindings are **rulings** and are not
re-opened here.

> **Beside every figure in this section:**
>
> These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.
>
> **No number here is a fact about any real company.** This is one quarterly archive spanning many periods, and its issuer matching is ~22.5% `weak` by design — the deliberately engineered names and relationships of the wider estate are not in these two tables.

#### Trap 1 — `report_period` is a spread, not a quarter

`report_period` carries **46 distinct values** spanning `31-DEC-2014` →
`31-MAR-2026`, because one filing window carries amended filings restating
historical periods. The distribution is dominated by one quarter —
`31-MAR-2026` holds **20,487 of 22,476 rows**, 91% — with a long tail behind
it.

**A query that does not pin the period silently mixes a decade of positions
into one answer.** Nothing errors; the answer is simply about a different
question than the one asked.

| The binding | Where it is applied | What it costs |
| --- | --- | --- |
| **Pin `report_period` to `31-MAR-2026`** | In the L1 read, at the source boundary — so the out-of-period rows never become signals, are never assembled, and never reach Π | **1,989 rows** estate-wide are outside the pin and are not served. That is the intended cost: they are other quarters' answers, not this one's |

The pinned period is also the TTL anchor (§B.1 element 3): one date,
`2026-03-31`, and 20,487 of 20,487 rows in the pin parse to it.

#### Trap 2 — one issuer LEI fans out across many CUSIPs

The anchor carries **6 distinct CUSIPs** in the pinned period; the widest
fan-out the Wave-1 probe measured is **one LEI reaching 51** (`RB GLOBAL INC.`,
`24.1-DATA-PROBE.md`). No estate-wide maximum across all periods was
measured, so none is claimed here. The fan-out under the anchor, measured
(control: the same query on a nonexistent CUSIP returned 0):

| CUSIP | band | rows | `issuer_match_score` |
| --- | --- | --- | --- |
| `032095101` | strong | 1,633 | 1.0000 |
| `032095101` | weak | 115 | 0.8000 – 0.8889 |
| `032095901` | strong | 7 | 1.0000 |
| `032095951` | strong | 5 | 1.0000 |
| `81369Y506` | strong | 1 | 1.0000 |
| `8033009TT` | strong | 1 | 1.0000 |
| `002159795` | strong | 1 | 1.0000 |

Aggregating a manager's position across every CUSIP under an LEI **over-counts**:
1,763 rows over 1,753 distinct managers, 9 managers appearing on more than one
CUSIP, and **5 managers whose only position is on a security that is not the
issuer's dominant one** (control: the reciprocal set — managers only on the
dominant security — returned 1,742, a different number, so the set difference
is measuring in both directions).

| The binding | What it is | What it costs |
| --- | --- | --- |
| **RESOLVE the security from `(lei, report_period)` to the dominant CUSIP** — a `Resolve` step; §D.3 works out which layer each half of it sits at. **Not a pinned literal** | `24-CONTEXT.md` `D-39`/`D-40`/`D-41` (Dave, 2026-08-26). Three reasons on the record: the resolve step **is** the `Resolve` this phase's operator-mapping hypothesis must place at a layer, so pinning would skip the pressure test the phase exists to run; a pinned CUSIP is a **domain value** and would have to live in an artifact anyway under the No-Hardcoding Rule (`CLAUDE.md` §6.4); and one LEI fanning out to 51 securities is handled by resolving and hidden by pinning | An extra §D step, **accepted**. And the five off-security managers are not served — which is the point, not the cost |

**A framing this spec explicitly does not inherit.** It would be natural to
read the off-security CUSIPs as admitted by a fuzzy issuer-name match, and the
phase's own research said so. **Measured, it is false:** all five off-security
CUSIPs are band `strong` at `issuer_match_score = 1.0000`, and the `weak` rows
sit **entirely on the correct security**. The band and the fan-out are two
different problems, and the band is the remedy for neither — see trap 3.

#### Trap 3 — `issuer_match_band = 'weak'` is 22.5% of rows, and it is deliberate

Estate-wide: **`strong` 17,410 / `weak` 5,066** of 22,476 rows — **22.5%
`weak`**. This is a **retained match-quality signal, not a defect left in by
accident**. The estate's design rule is that some joins are deliberately
imperfect so that resolution logic is testable at all, and the band column
exists precisely so the imperfection is **visible** rather than hidden; the one
issuer-matching defect that genuinely inflated the band — an unstripped state
suffix that mis-scored ~1,700 rows — was found and fixed
(`ccf_dataprep/docs/known-issues.md` §8.15), so what remains is the tuned
residual and not the bug.

**A weak band is a completeness signal, not a defect to filter away silently.**

| The binding | What it is | What the alternative costs |
| --- | --- | --- |
| **NO band filter.** Both bands are served, and the band travels with the row as a per-row signal | Ruled at Wave 1 against the measurement, not against the inherited framing | Filtering to `strong` costs **115 managers (6.6%)**, 115 rows and **$2.77bn of reported position (2.4%)** at threshold 0 — and removes **zero** wrong-security rows, because every off-security row is already `strong`. Dropping 115 real holders to remove nothing is a bad trade |

**This is a completeness fact and §E's debt model must account for it.** The
115 weakly-matched rows under the anchor are served, so the product's C factor
is not 1.0 merely because every row arrived: a consumer is entitled to know how
much of the answer rests on a weak issuer match. §E carries the accounting; §C
carries the figure and the ruling.

### C.5 What this data is — stated once more, because it is the point

`24-CONTEXT.md` `D-33`, in Dave's words: *"it's about how to engineer and
construct a context product using the CCFSDK."* The source estate's own README
says the same thing: ***"Use this to learn the assembly patterns, not the
numbers."***

Four statements, and they are the honest ones for **this** product rather than
a recital:

1. **These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — and not the figures.**
2. The surrounding data estate carries **deliberately engineered names and relationships** — 30,365 rows `synthetic — engineered`, 13,840
   `synthetic — internal`, 20 `derived`, measured across the 99 tables in the
   estate that carry a provenance column — even though **this product's two
   tables carry none of them**: 22,476 of 22,476 and 156 of 156 rows are
   `provenance = 'public'`.
3. **No number here is a fact about any real company.**
4. What the reader is actually looking at: **one quarterly archive spanning many periods** — 46, one of them pinned — and **not** a live feed; and
   issuer matching that is **~22.5% `weak` BY DESIGN**, not by defect.

**And what is deliberately not said here.** These rows are public filings, and
the honest statement is the four above — not a claim that the behavior in them
is fabricated. Being inaccurate in the cautious direction is the same class of
error as being inaccurate in the confident one, and both mislead a reader about
what they are holding.

---

## Section D — Assembly recipe

*(Standard §4.)*

### D.1 Client call

One call, one required class parameter (§B.4), and the forensic case shown
because it exercises more of the surface than the live one:

```
GET /context-products/holdings/institutional-holders/549300D3L3G0R4U4VT04
    ?intent=position-concentration
    &freshness=reported-quarter
    &minimum_position_usd=1000000000
```

`subject`, `intent`, `freshness` and `asked_at` are the address fields
`src/ccf/products/request.py::ProductRequest` carries in its own right;
`minimum_position_usd` is the one class-declared parameter and it has **no
default**. A request that omits it is refused as data —
`src/ccf/products/request.py::refuse_request` returns a
`::ProductRequestViolation` — *before the graph is touched*, which is why step
1 below is not where a missing parameter is discovered.

> **Beside the anchor above:**
>
> These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.
>
> The surrounding data estate carries **deliberately engineered names and relationships**; these two tables carry none.
>
> **No number here is a fact about any real company.** This is one quarterly archive spanning many periods, and its issuer matching is ~22.5% `weak` by design.

### D.2 Operator step table

Numbered, **one operator per step**, with the Standard's seven columns and an
**eighth the Standard does not require: the SDK mechanism, named with its
layer**. The eighth column is this phase's operator-mapping verdict written
where a reader actually meets it, so a name that differs between the two
vocabularies reads as a **mapping** rather than as a gap in either direction.

| # | Operator | Capability class | Inputs | Emits (as it appears in lineage) | Failure behavior | p95 budget | **SDK mechanism (layer)** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Resolve** | relational | the anchor `subject` (issuer LEI); the pinned `report_period` | `resolved_security` — the dominant CUSIP for `(lei, report_period)`, with the number of candidates considered | fail closed → **404**. An anchor that resolves to no security in the pinned period is never an empty payload | 120 ms | `examples/cp-00-institutional-holders/deployment.py::DominantSecurityResolution` — an **example-supplied `src/ccf/operators/base.py::Operator`** declaring the canonical category `traversal`, registered into and resolved back out of this deployment's own `src/ccf/operators/registry.py::OperatorRegistry`, and applied to the source read's group-and-rank (§C.2, capability property 3) — **L1**, the source boundary. `24-CONTEXT.md` `D-47`/`D-48` (Dave, 2026-08-26): a step must name an operator, and this row previously named none. `OperatorCategory` stays the closed four; a new operator NAME under an existing category is additive. §D.3 states why this half of the resolve is not at L2, and why the operator reaches a registry of the deployment's own |
| 2 | **Resolve** | relational | one `SignalEnvelope` per filed position, each already carrying the pinned period and the resolved security | canonical entity URIs for the issuer and for each reporting manager, the typed edge between them, and `graph_snapshot_at` | fail closed → **503**, naming the failed source class | 380 ms | `src/ccf/assembly/worker.py::SpecDrivenEntityResolution` under `src/ccf/assembly/worker.py::AssemblyWorker`, driven by `src/ccf/assembly/worker.py::EntityResolutionSpec` — **L2**, the single writer |
| 3 | **Policy** | relational | the assembled view; the principal's permitted classifications and permitted policy-bundle versions | `policy_version` — landing in `src/ccf/products/contract.py::ProductLineage` field `policy_bundle_versions` — and the principal-permissible subgraph substituted for the full graph | fail closed → **403**, with no detail on what exists | 15 ms | `src/ccf/operators/categories.py::PolicyFilter`, key `policy.principal-subgraph` — **L4** |
| 4 | **Traversal (mode: `temporal`)** | bitemporal-ledger *(supplied by the fabric, not required of the estate — §D.3)* | the permissible subgraph; the as-of boundary taken off the request | the as-of-consistent node and edge set; `graph_snapshot_at` | fail closed → **503** on an empty **assembled** set, which is not the same emptiness as an empty **served** set — §D.7 | 60 ms | `src/ccf/operators/categories.py::TemporalAsOf`, key `temporal.as-of-boundary` — **L4**, and a separate SDK *category* that the Standard folds into a Traversal *mode*. The inverse asymmetry: here the SDK has the name the Standard does not |
| 5 | **Projection** | in-memory *(the Standard's §10.2 row says `relational`; nothing in this step touches a store — §D.3)* | the as-of view; `minimum_position_usd`; the perspective | `projection_plan_id` — landing on `src/ccf/products/contract.py::ContextProductContract` field `plan_id` — and the typed payload of §D.6 | degrade with debt: a row missing a non-mandatory attribute is served with that field `NOT_EVALUABLE` and an elevated `D_c` (§E.2), never dropped silently | 25 ms | `src/ccf/projection/plan.py::ProjectionPlan.invoke`, executed by `src/ccf/projection/engine.py::ProjectionEngine` — **L5**. The Standard's `Evaluate` (modes `rank` and `aggregate`) has **no separate SDK mechanism** and lands here too — §D.3 |
| 6 | *contract assembly* — **not an operator** (§10.2 retires `Compose`) | in-memory | the projection output, the declared lineage, the declared TTL and its anchor | the served `src/ccf/products/contract.py::ContextProductContract`, held inside a `src/ccf/products/gates.py::ServableProduct` | fail closed → **503** on any gate refusal, returned **as data** (`src/ccf/products/gates.py::GateRefusal`) and never as a 200 with a warning. **409 is reserved for the debt posture** (§9) and is raised by the deployment, not by `run_gates` | 20 ms | `src/ccf/products/gates.py::run_gates` → `src/ccf/products/gates.py::ServableProduct` — **L6** |

**Budget total: 620 ms against a declared p95 envelope of 1,000 ms — 62%.**

Three things about that number, and the third is the one that matters.

1. **These were declared budgets, not measurements — and they have now been
   measured, which is how the amendment below arises.** This specification was
   authored *before* the assembly it specifies (§0), so every cell in the
   `p95 budget` column began as a design target an engineer is invited to
   challenge, in exactly the sense Standard §5.1 means when it says an initial
   calibration is *"a value an engineer can challenge"* rather than one they
   assume was measured. **AMENDED 2026-08-27** under `24-CONTEXT.md` `D-64`,
   in the marked form rather than by rewriting the column: **OLD CLAUSE** —
   *"Nothing has been run"*, which was true when it was written. **NEW
   CLAUSE** — the assembly has been run 40 times against the live estate and
   the measured figures are in the amendment below; the `p95 budget` column is
   left as authored, because a budget an engineer challenged and lost to is
   more useful beside the measurement than quietly replaced by it.
2. **The Standard fixes no numeric latency envelope for Tier 1.** §13 gives
   cost *bands* (×1 baseline) and §7 asks each product to publish its own
   p50/p95. The 1,000 ms envelope is therefore **declared by this spec**, in
   §G, and §D is measured against that declaration. Recording that the
   Standard does not supply one is more useful than quoting a number it does
   not contain.
3. **Step 2 dominates, at 61% of the total, and the first optimisation is
   not to make it faster.** The L2 ingest carries every filed position for
   the anchor and period through resolution and persistence — 1,748 rows at
   the pinned period (Wave 1's figure; see `24.1-DATA-PROBE.md` for the
   control beside it). That work is **identical for every threshold**,
   because the threshold is applied at Π and never in the graph query
   (§D.3). So the first optimisation is to **materialize the assembled state
   per `(issuer, report_period)`** and let every threshold read it —
   which §E.3's mechanical test permits, since the fastest-moving input's
   λ_c is a quarter and no sane cache window comes near it. The posture
   shipped at `v1.0.0` is nonetheless `derived-on-demand`, and §E.3 says
   why.

**MEASURED 2026-08-27 — and the declared envelope is contradicted by an order
of magnitude.** `24-CONTEXT.md` `D-64` put this in the wave that runs the
assembly rather than leaving it open into certification: *"An honest gap is for
things you cannot measure; this one you can."* The instrument is named in §G's
service-objectives entry, because a number without its instrument is a number
that looks like proof. The reading, against the live estate at the
demonstration threshold:

| Figure | Declared here | **Measured** | Ratio |
| --- | --- | --- | --- |
| p50 | 400 ms (§G target) | **10,141 ms** | **25.4×** |
| p95 | 1,000 ms (§G envelope) | **11,786 ms** | **11.8×** |
| step total | 620 ms | **10,279 ms** mean | **16.6×** |

**Where it goes, by step, so the contradiction is attributed rather than merely
reported.** The same clock, with the deployment's own `read` callable wrapped
at the seam that already injects it — nothing in this example or in `src/` was
modified to obtain the split:

| Step | Declared | Measured | Verdict |
| --- | --- | --- | --- |
| fabric boot (not a step; inside the call) | — | **63 ms** mean | not budgeted, and small |
| 1 · Resolve at the source read | 120 ms | **101 ms** p50 (mean 125 ms) | **the budget HOLDS** |
| 2 · Resolve at L2 | 380 ms | **9,896 ms** mean — 1,748 envelopes at **5.66 ms each** | **exceeded ≈26×** |
| 3–6 · Policy, Temporal, Π, gates | 120 ms | **258 ms** by subtraction: 10,279 − 125 − 9,896 | over, and immaterial beside step 2 |

**Point 3 above was right in kind and wrong in magnitude, and both halves
matter.** It said step 2 dominates *"at 61% of the total"*; step 2 is in fact
**≈95%** of a total sixteen times larger. Its diagnosis — that the L2 ingest
carries every filed position for the anchor and period through resolution and
persistence, identically for every threshold, because the threshold is applied
at Π and never in the graph query — is exactly what the measurement shows.
**Its remedy is therefore the right remedy** and is now supported by evidence
rather than by reasoning: materialize the assembled state per
`(issuer, report_period)` and let every threshold read it.

**The threshold-independence claim was tested rather than assumed.** Three
populations, same instrument:

| Threshold | Rows served | N | p50 | p95 |
| --- | --- | --- | --- | --- |
| 1,000,000,000 | 21 | 40 | **10,141 ms** | **11,786 ms** |
| 500,000,000 | 39 | 10 | 10,397 ms | 10,932 ms |
| 0 | 1,748 | 10 | 10,634 ms | 11,715 ms |

Serving **83× more rows costs about 5% more time**. That is the strongest
available evidence that the cost is in the ingest and not in the projection,
and it is a *control* rather than a restatement: had Π been the driver, the
threshold-0 population would have separated from the others and it did not.

**What this does NOT establish.** These are single-caller, cold-boot,
same-LAN readings from one machine. No concurrency was tested, no warm-cache
posture was tested, and the source estate is a shared host with no per-query
accounting. The envelope in §G is therefore **contradicted, not replaced** —
choosing a new one is a decision, and §F marker 15's cost half stays open for
the same reason.

### D.3 Step detail

**The two disciplines the Standard says recur, both of which are live here.**

**Policy that appears to do nothing still runs first — and here it does not
merely appear to do nothing, it can empty the answer.** This product asserts
no entitlement scope (§B.1 element 4): every element measures
`provenance = 'public'`, so there is no partition to bind and step 3 excludes
nobody. It runs first anyway, because that is where the ordering is learned:
`src/ccf/operators/base.py::CATEGORY_ORDER` is
`("policy", "similarity", "temporal", "traversal")` and encodes INV-CH7-26,
and `src/ccf/operators/categories.py::PolicyFilter`'s own docstring says it
*"runs first in every plan so that no later stage can observe inadmissible
state."* The load-bearing part for a builder is this:
`src/ccf/operators/categories.py::PolicyFilter._admits` **excludes any entity
whose class has no classification attribute declared**, not merely one whose
classification is impermissible. So both entity classes this product declares
must carry a classification attribute and both must be named in
`classification_attribute_by_class`, or step 3 returns an empty view and
steps 4–6 answer about nothing. §D.7 carries the gate that catches it.

**Two filters on two axes are two filters.** The `report_period` pin and the
`minimum_position_usd` threshold are two different axes and are separately
parameterised and separately testable: the pin is fixed by the spec and
applied at the source read (§C.4 trap 1), the threshold is chosen by the
caller and applied at Π. Applying one and calling it the other answers a
different question in silence. A third axis is deliberately **not** filtered:
`issuer_match_band` travels with the row and is not filtered anywhere
(§C.4 trap 3), which is a ruling and not an omission.

**Where the threshold is applied, and why it is not in the query.** At Π, in
`src/ccf/projection/plan.py::ProjectionPlan.invoke`, never in the graph
query — the same choice
`examples/s1-00-companies-over-revenue/deployment.py::OverThresholdProjection`
documents, in its words: *"every threshold compiles to the same pinned query,
so what the caller's number changes is the payload — and therefore the
product's content address — rather than what was read."* Two consequences
follow and both are load-bearing here. Freshness is measured over what the
fabric **read**, not over what survived the caller's line (§E.2), which is
only coherent because the read is threshold-independent. And the assembled
state is identical across callers, which is what makes §D.2's materialization
optimisation available at all.

**The comparison is `>=`, not `>`.** §B.4 declares the parameter as *"the
reported position value **at or above** which a manager appears."* A manager
whose position equals the caller's number is served. `s1-00`'s projection uses
a strict `>`; this product deliberately does not inherit it, and §D.7's gate
`IH-G04` exists because copying that line is the obvious way to get this
wrong.

**Why the resolve is in two steps, and why the first is not at L2.**
`24-CONTEXT.md` `D-39` (Dave, 2026-08-26) rules the security **resolved and
not pinned**, and `D-41` accepts the extra step that costs. Measured against
the mechanism, the resolve separates into two halves that sit at two layers:

- The **canonical-entity** half is at L2 exactly as the mapping predicts.
  `src/ccf/assembly/worker.py::EntityResolutionStrategy.resolve` takes
  `(*, envelope)` — **one envelope at a time** — and returns the entities that
  envelope asserts, in declaration order. That is step 2.
- The **dominant-security** half is a *group-and-rank over many rows*, and a
  per-envelope seam structurally cannot compute it: a strategy would have to
  accumulate state across envelopes and become order-dependent, which is the
  determinism §D.4 depends on. So it runs where the estate can already do it
  — as a group-and-rank at the source read, the capability §C.2 lists as its
  third property and names as the one most likely to be partial. That is
  step 1, at **L1**.

**And it is an operator, named.** `24-CONTEXT.md` `D-47`/`D-48`: *"You must
specify an operator — deterministic, etc. — you cannot not have an operator."*
Step 1 is `examples/cp-00-institutional-holders/deployment.py::DominantSecurityResolution`,
which conforms to `src/ccf/operators/base.py::Operator` structurally, declares
the canonical category `traversal`, and is registered into an
`src/ccf/operators/registry.py::OperatorRegistry` and resolved back out of it
before it is applied — so the registry's duplicate-key and category checks run
over it rather than being asserted about it. Being deterministic was never an
obstacle: the base says realization is unconstrained and *"the algebra is the
determinism surface."* The one shape `apply` fixes is the RESULT's — a view,
so no scalar — and *which security is dominant* is a **selection**, which is a
view by construction: the operator returns the winning security, the edges
reaching it and the managers on those edges.

**Which registry, and the seam that is recorded rather than worked around.**
The operator is registered into **this deployment's own** registry, not into
the one the projection plan resolves against.
`src/ccf/deployment/operators.py::build_operator_registry` — the builder the
spine calls — dispatches on the *declared artifact type* against the SDK's own
operator classes and raises for anything it does not recognise, so a
deployment's own operator has no path into it. **The registry is open; the
composition path in front of it is not.** Recorded under `24-CONTEXT.md` `D-04`
and ruled `D-59` **record-only for phase 24.1**: the local L1 registration is
the right path for this product, and closing the seam was additive SDK work for
a later phase (`D-58`). **That phase has since run — `D-59` is CLOSED in 24.1.1**,
and `build_operator_registry` now takes a defaulted `deployment_operators`
keyword. The record-only ruling is left standing above as what governed THIS
document's build; the local path remains correct here because this product's
operator runs at the source boundary, which the projection plan does not reach. The consequence for this table is nil in both
directions — the served `lineage.operators_invoked` names exactly the two
operators the product class declares, so §D.7's gate 2 strict equality is
untouched, and step 1's runtime witness is the payload's `resolved_security`
block rather than a lineage key.

**Nothing about `D-39`'s substance changes**: no literal CUSIP is pinned, no
domain value enters code, the fan-out is handled rather than hidden, and the
`Resolve` name is placed at a layer — which is what criterion 11 asks for.
**What differs from the ruling's words is the layer of one half**, and it is
recorded here rather than absorbed. If the estate turns out not to rank inside
a read, §C.2's interim posture takes over: the security becomes a second
caller parameter, step 1 drops out of this table, and the product ships as
`v1.0.0-partial`.

**Where the Standard's `Evaluate` went.** Nowhere separate: it is step 5.
The Standard lists `Evaluate` (modes `aggregate · score · reconcile · rank`,
capability class `in-memory`) as its own operator; the SDK has no operator
that can be it, and the reason is structural rather than an omission.
`src/ccf/operators/base.py::Operator.apply` returns
`src/ccf/operators/base.py::OperatorOutput`, which is a `GraphView` plus an
`OperatorProvenance` — **an operator cannot emit a number.** Deterministic
computation that produces measures rather than graph state therefore lives at
Π, which is where this product's ranking and thresholding run. This spec does
**not** carry `Evaluate` as a separate row in §D.2, because a step whose
mechanism, layer and runtime witness are all identical to step 5's is a step
nothing can independently prove ran — and an unprovable step is exactly what
criterion 2 calls RED. Naming it in this paragraph is the honest form.

**Where the capability classes come from, and the tier consequence.** Two
cells in §D.2 differ from what a first reading of §10.1 would give, and both
are deliberate:

- Step 4 requires `bitemporal-ledger`, and §13 puts `bitemporal-ledger` at
  **Tier 3**. This product remains **Tier 1**. The reason: capability classes
  describe what the **estate** must supply — §10.1's own rule is that estate
  binding lives in one platform-owned artifact and *"product specs never name
  a database."* The bitemporal read here is against **CCF's own L3**, whose
  valid-time / observed-time axes are fabric mechanism supplied by
  construction, not something the source estate must have. This product does
  **not** reconstruct what the *source* knew at a past instant; it reads one
  archive at one pinned reported period. Read the other way — every step's
  class taken as an estate requirement — **no CCF product could ever be Tier
  1**, because every CCF product reads a bitemporal graph and computes at Π.
  That reductio is why the estate reading is the right one, and the ambiguity
  is recorded as a finding in §F rather than resolved on this product's
  authority alone.
- Step 5 is named `in-memory` where §10.2's `Projection` row says
  `relational`. Nothing in step 5 touches a store; it computes over already
  assembled state, which is precisely §10.1's definition of `in-memory`.
  Recorded rather than silently picked.

**The four composition invariants (§10.3), checked.** (1) Policy runs before
anything that reads graph state — step 3 precedes steps 4 and 5, enforced by
`CATEGORY_ORDER` and not merely by this table's ordering. (2) Resolve precedes
Traversal — steps 1 and 2 precede step 4. (3) Enrich is batched, always —
**not applicable**: there is no Enrich step, because every attribute of a
filed position arrives in the same source row as the position. (4) Algorithmic
substrate before any semantic stage — **vacuously true and asserted anyway**:
Assembly Mode 1 puts no model in the path at all, and criterion 4 makes the
absence a walked assertion rather than a claim.

### D.4 Determinism class and payload hash

**Determinism class: `deterministic`** (Standard §4.4, Mode 1). Same anchor +
as_of + `policy_version` + graph snapshot → byte-identical payload.

**Payload hash.** The Standard requires *a payload hash over the deterministic
portion, excluding `assembled_at`*. The SDK's realization is
`src/ccf/contracts/canonical.py::content_hash` over the served vessel's
canonical bytes, recorded as `product_content_address` by
`src/ccf/replay/record.py::build_replay_record`. **Replay asserts hash
EQUALITY, not similarity** — a product that replays to *a similar product* is
a defect recorded in §G, not a caveat.

**One divergence, stated rather than absorbed.** CCF hashes the **whole
vessel**, not a deterministic subset of it, and the vessel carries
`temporal_boundary` — which this deployment takes off the request
(`request.asked_at`), never off a clock, so that replay can feed it back.
There is no `assembled_at` field to exclude, and `temporal_boundary` occupies
its position. The consequences are exact:

- Under **replay** the assertion holds unchanged, because replay resolves the
  recorded request and therefore the same boundary.
- Under **two live calls a second apart**, the same answer has two content
  addresses. A consumer diffing addresses to decide whether an answer changed
  will see a change that did not happen.

Recorded for the phase's gap register (`D-04` — recorded, not closed). It is
not a defect in either document: the SDK's value is an address of *the served
answer*, the Standard's is a hash of *the payload*, and they are different
useful things that happen to share a name.

**Why the as-of boundary cannot be the reported quarter end**, which is the
trap a reader of §B.1 element 3 will walk straight into.
`src/ccf/assembly/worker.py::AssemblyWorker._stitch` sets a claim's
`observed_at` to the envelope's **ingestion timestamp** — when *the fabric*
learned the claim — and `src/ccf/operators/categories.py::TemporalAsOf`'s
first cut drops every claim whose `observed_at` is later than the boundary.
Set the boundary to `2026-03-31` and **every row is dropped**: the view is
empty, the three shipped gates all pass (§D.7), and the product serves an
empty holder list with a clean bill of health. The boundary must therefore be
at or after the run's ingest instant. The TTL anchor is the reported quarter
(§B.1 element 3); the **as-of boundary is not**, and conflating them is the
single most expensive available mistake in this recipe. §D.7's gate `IH-G05`
is the assertion that catches it.

### D.5 Replay statement and replay test

**Replay statement.** Replay re-executes steps 3 through 6 against the
**recorded** graph snapshot, resolving from the record: the request (including
`asked_at`, and therefore the temporal boundary), the perspective and its
principal, the policy-bundle version bound at ingest, the resolution-spec
version, the projection `plan_id` and the operator plan. It re-produces the
identical `ContextProductContract` and therefore the identical
`product_content_address`. Steps 1 and 2 are **not** re-executed: they are the
write path, and re-running them would rebuild the graph rather than replay
against it.

**Falsifiable replay test.** Numbered, runnable, ending in an assertion that
can fail:

1. Serve the product at the anchor with `minimum_position_usd = 1000000000`.
   Record `product_content_address`, `graph_snapshot_at` and the request.
2. Ingest an **amending filing**: the same manager, the same security, the
   same `report_period`, a materially different `value_usd`.
3. Re-derive **live**. Assert the served value is the **new** one. *If it is
   not, the supersession path is not working and step 2 of this test proved
   nothing.*
4. Re-derive **at the recorded snapshot**. Assert the served value is the
   **original** one and `product_content_address` is byte-identical to step
   1's. **If step 4 returns the new value, `graph_snapshot_at` is decorative
   and the snapshot is not load-bearing.**

**Second test — the two time axes must disagree.** This product carries
valid-time (`valid_from`, the reported quarter end) and observed-time
(`observed_at`, the fabric's ingest instant), and an amended filing is the
case that separates them: it is *about* `31-MAR-2026` and was *learned*
months later.

5. With the amendment ingested, read as-of a boundary **before** the
   amendment's ingest instant and assert the **original** figure returns; read
   as-of a boundary **after** it and assert the **restated** figure returns.
   **If the two agree, the observed-time cut was dropped** and the product
   cannot distinguish what was true from what was known.

### D.6 Emitted contract

The §8 response envelope, populated with this product's payload schema, **with
types**. Prose describing a payload is not a payload.

`payload`:

| Field | Type | Notes |
| --- | --- | --- |
| `issuer.lei` | string | The anchor, echoed |
| `issuer.registered_name` | string \| `NOT_EVALUABLE` | From `ccf_v2.legal_entity`; non-mandatory (§E.2) |
| `report_period` | string | The pinned period, spelled as the source spells it: `31-MAR-2026` |
| `resolved_security.cusip` | string | Step 1's output |
| `resolved_security.resolution_basis` | string | `dominant-by-position-count` |
| `resolved_security.candidates_considered` | integer | How many CUSIPs the anchor fanned out to — 6 at the anchor (Wave 1) |
| `threshold.minimum_position_usd` | string | Decimal **as a string**. A float in canonical bytes is not canonically serializable |
| `threshold.comparison` | string | `>=` — declared in the payload so a consumer never has to infer it (§D.3) |
| `perspective_role` | string | The Π role the answer was conditioned for |
| `count` | integer | Managers served |
| `holders[]` | array of object | Sorted by `value_usd` descending, then `manager_cik` ascending, so the order is total and the bytes are stable |
| `holders[].manager_cik` | string | Identity authority (§C.3) |
| `holders[].manager_name` | string \| `NOT_EVALUABLE` | Carried so a consumer can see the identity rather than trust it |
| `holders[].value_usd` | string | Decimal as string |
| `holders[].shares` | string \| `NOT_EVALUABLE` | Decimal as string |
| `holders[].issuer_match_band` | string | `strong` \| `weak`. Travels with the row — §C.4 trap 3 |
| `holders[].issuer_match_score` | string | Decimal as string |
| `holders[].last_updated` | string | ISO-8601, from the claim's `valid_from` — the source's instant, not this run's |

`contract`, `lineage` and `context_debt` are never omitted: a consumer that
receives context with no debt signal cannot know what it is trusting. Their
member-by-member mapping onto the SDK's types is §B.1 element 5 and is not
repeated here.

**One field this payload deliberately does not carry, and it is the one
`s1-00` does.** `s1-00`'s payload carries `assembled` — the count of rows the
fabric read. This product omits it. §B.2 commits this product to being
**silent about what fell below the caller's line**, and a read count published
beside a served count *is* that number by subtraction. The assembled count is
still needed, as F's denominator (§E.2); it lives in the debt block, which is
a governed disclosure of what the fabric read rather than a description of the
answer's shape. Nothing here is policy-withheld at all (§B.2), so the
discipline is being observed structurally rather than because anything is
hidden — which is the only reason it is cheap to observe now and expensive to
retrofit later.

**`extra=forbid` is enforced as a build-time CI invariant**, per Standard
§4.6: a per-product subclass may not silently add a field the base did not
declare.

**Error taxonomy, mapped to the step that raises it** (Standard §9 requires
§D to name which step raises which):

| Condition | Response | Raised at |
| --- | --- | --- |
| Anchor unresolvable | **404** — never an empty payload | Step 1 |
| Principal not entitled | **403**, no detail on what exists | Step 3 |
| Parameter unsupported | **400** | **Before step 1**, at the door, by `src/ccf/products/request.py::refuse_request`. **The SDK names this `undeclared-parameter`, not the Standard's `not_supported_at_tier`** — the §B.4 divergence, restated here because §D is where a builder meets it |
| Debt gate exceeded | **409** with the debt block | **Not `run_gates`** — the Control Plane posture of §D.7, acted on by the deployment |
| Mandatory input unavailable | **503**, naming the failed source class | Step 2 (and step 1 for the source read) |
| Non-mandatory input unavailable | **200** with `notices` and elevated `D_c` | Step 5 |

The HTTP surface these render through is
`runtime/ccf_runtime/http_api/errors.py::refusal_detail`.

### D.7 Validation gates

**The Standard names six universal gates. This SDK ships THREE inside
`src/ccf/products/gates.py::run_gates`, and `D-IMPL-102` limb 3 rules that no
fourth joins them.** What follows is what each of the six actually is here.
Nothing below claims the SDK runs a gate it does not run — a spec that implied
otherwise would be the drift criterion 12 exists to catch, arriving from the
specification side.

**The three that are shipped gates, in `run_gates`' own order:**

| # | Gate | SDK mechanism | What it refuses |
| --- | --- | --- | --- |
| 1 | Empty-operator guard | `src/ccf/products/gates.py::_refuse_empty_operators` (INV-CH7-46) | A product whose `lineage.operators_invoked` is **empty** — *a product computed by nothing* |
| 2 | Lineage strict equality | the `declared != engine_resolved` comparison in `src/ccf/products/gates.py::run_gates`, returning `src/ccf/products/gates.py::LineageMismatchRefusal` (INV-CH7-47) | Any difference, **in either direction**, between the operator set the producer declares and the set the engine resolved |
| 3 | TTL bounds | `src/ccf/products/gates.py::_refuse_ttl` against the class's pinned `MAX_TTL` | `expires_at` outside `now < expires_at <= now + MAX_TTL` — see §B.1 element 3 for the two ways this product can hit it |

A fourth refusal sits in the same sequence and is **not** a fourth universal
gate: `refuse_attestation` is conditional and passes unconditionally when
`source_attestation` is `None`, which is this product's case. Naming it as a
gate would overstate what runs.

**Holding a `ServableProduct` IS the evidence the three gates ran.**
`src/ccf/products/gates.py::ServableProduct` is not constructible outside
`run_gates` — the metaclass refuses with
`src/ccf/products/gates.py::GateBypassError` (INV-CH7-52). That is what makes
criterion 6's *"recorded rather than assumed"* structural rather than a
convention, and it is the witness `assembly-recipe.yaml` declares for step 6.

**Gate 1 is not the Standard's gate 1, and the difference costs this product a
gate of its own.** The Standard's empty-operator guard is *"no operator returns
an empty set silently; empty is fail-closed or an explicit debt
contribution."* The SDK's refuses a product that **declares no operators**.
These are two different assertions sharing one name, and the gap between them
is exactly the failure §D.4 describes: a mis-set as-of boundary empties the
view, all three shipped gates pass, and a 200 with an empty holder list is
served. **Recorded for the gap register and not closed** (`D-04`); covered
here by a product-specific gate, which is the mechanism Standard §4.7 provides
for precisely this.

**The other three, each as it actually stands:**

- **Debt gate.** Present as a **Control Plane posture, not as a gate.**
  `src/ccf/halflife/debt.py` computes `D_c` and
  `src/ccf/controlplane/artifacts.py::DebtProfile` carries
  `forced_llm_threshold` and `fail_closed_threshold`; the deployment reads
  the resulting posture and declines. The SDK supplies the assessment and the
  bands; **the refusal is the deployment's own code**, and `run_gates` never
  sees it. §E.2 sets this product's bands and §G's degradation contract says
  what it does with them.
- **Classification containment.** Present, and realized **structurally at L4
  rather than as a post-assembly gate** —
  `src/ccf/operators/params.py::PolicyFilterParameters` carries
  `classification_attribute_by_class` and `permitted_classifications`, and
  `src/ccf/operators/categories.py::PolicyFilter._admits` excludes any record
  whose classification is not permitted *and* any record whose class declares
  no classification attribute at all. An element above the declared
  classification is therefore **never materialized**, which is stronger than
  containment checked afterwards. This is composition invariant 1 doing the
  work a gate would otherwise do.
- **Suppression silence.** Holds **by construction, and is not exercised by
  this product.** Because step 3 removes inadmissible records from the view
  before Π ever sees them, the payload structurally cannot carry a marker of
  withheld content: Π is not given the thing to mark. Nothing is withheld here
  in any case (§B.2). The Standard's *post-assembly* form of this gate and of
  classification containment is therefore owed by neither this product nor
  this SDK, and whether the Standard should say so is a **finding for the
  phase's gap register**, recorded in §F — not a `[TBC]` on this build.

**Product-specific gates**, each a testable assertion naming the defect it
detects, with a fixture ID:

| ID | Assertion | The defect it detects |
| --- | --- | --- |
| **IH-G01** | Every served row's `cusip` equals `resolved_security.cusip` | Step 1's output was not applied to the read, and the CUSIP fan-out over-count returned. The anchor has 5 managers whose only position is off the dominant security (Wave 1), so this gate has something to catch |
| **IH-G02** | Every served row's `report_period` equals the pinned period | The period pin was dropped and a decade of positions merged into one answer. 1,989 rows estate-wide sit outside the pin |
| **IH-G03** | Every served row carries a non-null `issuer_match_band` | The quality signal was dropped at the source boundary — §C.2's rare capability property degraded — and a consumer can no longer see which rows rest on a weak match |
| **IH-G04** | A manager whose `value_usd` **equals** `minimum_position_usd` **is served** | The comparison was written `>` instead of `>=`, contradicting §B.4. This is the defect a line copied from `s1-00` produces |
| **IH-G05** | The as-of boundary is at or after the run's ingest instant, **and** a non-empty assembled set is observed before Π runs | The boundary was set to the reported quarter end, `TemporalAsOf` dropped every claim on `observed_at`, and the three shipped gates passed an empty answer (§D.4) |
| **IH-G06** | Every entity class this product declares is named in `classification_attribute_by_class` and carries that attribute | `PolicyFilter._admits` silently empties the view for any class with no classification attribute declared (§D.3) |
| **IH-G07** | An **empty assembled set** fails closed; an **empty served set** (threshold above every position) returns 200 | The two emptinesses were conflated. Only one of them is an answer, and the SDK's gate 1 catches neither |
| **IH-G08** | The product's `payload` carries no count of rows read | §B.2's suppression discipline was dropped by inheriting `s1-00`'s `assembled` field (§D.6) |

## Section E — Volatility, debt & materialization

*(Standard §5.)*

### E.1 Half-life table

One row per signal class. **These are initial calibration proposals, not
measurements** — Standard §5.1's own distinction, and stating it plainly is
what makes them values an engineer can challenge rather than numbers they
assume were derived from data.

| Signal class | λ_c (half-life) | Calibration basis | Decay driver | Supersession event | Owner |
| --- | --- | --- | --- | --- | --- |
| Reported position | **11,836,800 s — 137 days** | **illustrative** | The **quarterly 13F reporting cycle**: one calendar quarter (92 days) plus the 45-day filing deadline the source's own reporting rule sets. Relevance halves by the moment the next filing is due, which is the point at which the register is expected to have moved | **A later filing restating the same manager's position in the same security for the same reported period.** An amendment, not the arrival of the next quarter | CCF SDK examples maintainer |
| Issuer identity (registered name) | `[TBC]` — the archive publishes no refresh interval and guessing one would be the §0.2 defect (§B.1 element 2) | — | Reference-data maintenance, not the filing cycle | A reference-data update to the registered name | `[TBC]` — §F |

**λ_c is Control Plane configuration per observation type**, not a per-row
attribute: it lives in the deployment's half-life table artifact, and a
conflict between two specs resolves centrally rather than in either document.
Review cadence: annually, or on any change to the supersession pattern.

**The decay anchor is `report_period`, a quarter-end date up to 90 days
coarse, and the coarseness is a property of 13F rather than a data defect**
(`24-CONTEXT.md` `D-22`). A position filed for `31-MAR-2026` is dated to that
quarter end whether the manager took it in January or in March. The
distinction §B.1 element 3 draws applies here for the second time: *"there
should be a timestamp and there isn't"* is a data defect, *"the dataset
reports per period and the spec decays from that period"* is a normal
declaration, and this product is the second sentence. The cost is real and
should be read as a cost: **no answer this product gives can be fresher than
the quarter it reports.**

**An arithmetic illustration, and it is not a prediction of what the SDK will
compute.** Read on 2026-08-26, the pinned period's positions are 148 days old
against a 137-day half-life, so the raw decay term is
`2^(−148/137) ≈ 0.47`. That is arithmetic on the declared λ_c alone.
`src/ccf/halflife/debt.py::FreshnessScorer` also applies the debt profile's
`risk_sensitivity`, which this spec has **not** set (§F, marker 16), so the
scorer's actual output is not this number and nothing here should be read as
predicting it.

### E.2 Debt model and per-component debt table

`D_c = 1 − (F · C · S)` — **multiplicative**, so a collapsed dimension forces
escalation rather than being averaged away.

**F — freshness, and it is measured over the rows ASSEMBLED, not the rows
SELECTED.** This is a decision, not an accident of where the call sits.
`src/ccf/halflife/debt.py::FreshnessScorer` refuses an empty sequence by
design, so scoring the survivors would make a threshold that admits nobody
**raise** instead of answering — a caller who sets an impossibly high number
would get an exception where the honest answer is *"nobody."* Freshness
therefore describes what the fabric **read**; completeness describes what
survived being read. The shape is
`examples/s1-00-companies-over-revenue/deployment.py::RevenueScenario`'s and
it is adopted here for its reasons, not by inheritance. It is also only
coherent because the read is threshold-independent (§D.3): every threshold
compiles to the same pinned query, so *"the rows assembled"* is one
well-defined set rather than a per-caller one.

**F is normalized over required signal classes, not over the classes actually
present** (Standard §5.2), or losing a source improves the freshness score.

**Decay is measured from `valid_from`, not from `observed_at`.** CCF's T axis
is bitemporal and the two members are different facts:
`src/ccf/assembly/worker.py::AssemblyWorker._stitch` sets `observed_at` to the
envelope's **ingestion timestamp** — when the *fabric* learned the claim — and
`valid_from` to the source's own instant, here the reported quarter end.
Scoring `observed_at` would measure the age of **this run**: a two-year-old
filing re-read a moment ago would score as perfectly fresh, which is a source
outage laundered into a low-debt reading, and it is the precise failure the
fail-closed posture exists to prevent. This is the same reading §D.4 depends
on for a different purpose, and getting it wrong breaks both.

**C — completeness, decomposed into two components, because this product has
two different incompletenesses and multiplying them into one number would hide
both.**

- **C_attributes** — the fraction of assembled rows carrying every attribute
  the resolution spec declares. The identity key is not among them: a row
  missing `manager_cik` produced no entity to count. **Measured at the anchor,
  from the shipped run: 1,748 of 1,748 assembled rows carry every declared
  attribute — `C_attributes` = 1.** §F marker 13 is **CLOSED**. Controls
  recorded beside it: an attribute the resolution spec does not declare is
  carried by 0 rows, and rows whose band is neither `strong` nor `weak`
  number 0. A value of exactly 1 is the honest reading of this estate and not
  a default — the source's own loader makes every column but three NOT NULL,
  and the three that are nullable are non-null for this anchor.
- **C_match** — the fraction of assembled rows whose `issuer_match_band` is
  `strong`. At the anchor, at threshold 0: **1,633 strong of 1,748 assembled
  = 0.9342** (Wave 1's figures, with the control recorded beside them in
  `24.1-DATA-PROBE.md`; not re-derived here).

`C = C_attributes × C_match`, so the model's shape is unchanged.

**Which of the two the weak rows are, because §C.4 trap 3 requires this
document to pick one and say which.** The 115 weakly-matched rows under the
anchor are a **completeness shortfall this product declares — not a scope
boundary it draws.** The reason is that the rows are **served**: a product
drawing a boundary excludes them and owes the consumer nothing about them,
whereas this product includes them and therefore owes the consumer a number
saying how much of the answer rests on a weaker issuer match. Filtering to
`strong` would cost 115 real holders and $2.77bn of reported position and
remove zero wrong-security rows (§C.4 trap 3), so the boundary reading is not
available even if it were preferable.

**S — semantic consistency — is 1, and the reason is stated rather than left
as a magic constant.** There is exactly one source here and **a single source
cannot disagree with itself.** This is the honest setup for a later example
where debt only becomes interesting once assembly spans sources that *do*
disagree; declaring `1` with no reason is how a constant survives into a
product where it is false.

**Per-component debt table.** Debt is decomposed **per claim** — each holder
row is a claim — and never only per product: a row missing a non-mandatory
attribute is served with that field marked `NOT_EVALUABLE`, not dropped and
not turned into a product-level failure.

| Component | May be absent? | D_c contribution | Behavior when absent |
| --- | --- | --- | --- |
| Reported position value (`value_usd`) | **no** | drives F and C_attributes | **Fail closed → 503.** The threshold is a comparison against it; without it there is no question to answer |
| Reported period (`report_period`) | **no** | none — it is the pin, not a factor | **Fail closed → 503**, naming the failed source class. An unpinned read is a different question (§C.4 trap 1) |
| Resolved dominant security | **no** | none — it is the resolve output | **Fail closed → 404.** An anchor that resolves to no security in the period is never an empty payload |
| Manager identity (`manager_cik`) | **no** | C_attributes | **Fail closed** for that row: a position with no identified holder is not a holder |
| Manager name | yes | C_attributes | **Serve with flag** — the row stands on the CIK; the field is marked `NOT_EVALUABLE` |
| Issuer registered name | yes | C_attributes | **Serve with flag** — `issuer.registered_name` marked `NOT_EVALUABLE`; the LEI still identifies |
| Share count (`shares`) | yes | C_attributes | **Serve with flag** — the threshold is on `value_usd`, not on `shares` |
| Issuer match band | yes | **C_match** | **Serve with flag, and C_match is marked `NOT_EVALUABLE` rather than assumed 1.0.** If the band is dropped at the source boundary (§C.2's rare capability property degrading), the completeness this product declares cannot be computed, and assuming it is 1.0 would report a *better* completeness for having lost the signal that measures it |

**The debt gate is a Control Plane posture, not a validation gate** (§D.7).
`src/ccf/controlplane/artifacts.py::DebtProfile` carries
`forced_llm_threshold` and `fail_closed_threshold`; the deployment reads the
posture `src/ccf/halflife/debt.py` produces and declines.

**This product's bands are CONFIRMED and §F marker 16 is CLOSED**
(`24-CONTEXT.md` `D-52`, Dave, 2026-08-26). They are declared in
`examples/cp-00-institutional-holders/ccf_config.yaml`'s `debt_profile:`
section, which is where a band belongs — Control Plane state, never a
constant in code:

| Band | Value | The demonstration question crosses it at |
| --- | --- | --- |
| `risk_sensitivity` | **1.0** | — — λ_c is already declared as a decision-relevance half-life, so a multiplier other than 1 would restate it in a second document |
| `forced_llm_threshold` | **0.60** | **day 168** after the reported quarter end |
| `fail_closed_threshold` | **0.77** | **day 278** after the reported quarter end |

**They were set *together with* λ_c, which is the whole point of the pairing.**
The demonstration question is asked 148 days after the pinned reported quarter
end against a 137-day λ_c, so `F` = 0.4729 and, with `C` = 0.9342 and `S` = 1,
the delivered **`D_c` = 0.558** — comfortably below `forced_llm` and nowhere
near `fail_closed`. Both crossings above were found by search over the same
arithmetic rather than asserted: at day 167 `D_c` is 0.5987 and at 168 it is
0.6007; at day 277 it is 0.7700 and at 278 it is 0.7711. A
`fail_closed_threshold` chosen without reference to the half-life would refuse
this product on its first call — that is not a defect in either number, it is
what happens when a freshness declaration and a tolerance are set by two people
who did not talk, and it is why these two are declared in one document.

The figure is **nominal and stable** rather than a property of the day CI runs,
because `now` is the fixed `asked_at` the question artifact declares and never
a clock read.

### E.3 Materialization posture

**`derived-on-demand`**, at `v1.0.0`.

**The mechanical test, applied honestly.** Standard §5.3: *"if the
fastest-moving input's λ_c is shorter than the intended cache window,
materialization is wrong."* Here the fastest-moving input's λ_c is **137
days**, and no cache window comes near it — so materialization is **not
wrong**, it is permitted, and §D.2 names it as the first optimisation the
budget would reach for. The posture shipped at `v1.0.0` is nonetheless
on-demand, and the reason is pedagogic rather than technical: this product is
the ladder's first rung and a cache in front of it would hide the assembly the
example exists to show. **Recording that the test permits what the spec
declines is more useful than implying the test forbade it.**

**Cache key, stated explicitly** — because a cache key missing a parameter
that changes the payload is a correctness defect that presents as an
intermittent one:

```
tenant_id · schema_name · schema_version · plan_id
          · graph_snapshot_at (the as-of boundary)
          · report_period (the pin)
          · resolved_security.cusip
          · minimum_position_usd          ← the caller's number
          · perspective principal and role
          · policy bundle version
```

`minimum_position_usd` is in the key and its presence is load-bearing. Because
the threshold is applied at Π and never in the query (§D.3), **the assembled
state is identical across callers and only the payload differs** — which is
precisely the shape in which a key omitting the threshold serves the first
caller's answer to the second, intermittently, and only under concurrency.

### E.4 Supersession triggers

| Event | Local or cascading | Note |
| --- | --- | --- |
| A later filing restating the same manager's position in the same security for the same period | **local** | The row supersedes. This is the amendment case §D.5's replay test is built on, and it is the normal event for this source, not an exception |
| A reference-data update to the issuer's registered name | **local** | A payload field changes; nothing about the positions does |
| A change to the resolution spec (`src/ccf/assembly/worker.py::EntityResolutionSpec` `semver`) | **cascading** | It changes what the graph *means*, so it invalidates every product whose `operators_invoked` touched these entities — **not only the products named as consumers.** Named downstream products today: **none** (§B.5) |
| A policy-bundle version change | **cascading** | Same reach, same reason. Named downstream products today: **none** |
| The pinned period passing `expires_at` | **local, and not an invalidation** | An expiry. §E.5 |

**Re-derivation is lazy** — invalidate for next request; do not re-materialize
eagerly. A quarterly 13F publication touches tens of thousands of rows at
once, so eager re-derivation would turn a routine upstream publication into a
thundering-herd event across the catalog.

### E.5 The expiry, and the two refusals it can produce

*(`24-CONTEXT.md` `D-43`, Dave 2026-08-26. This subsection exists so that a
reader who meets a refusal can tell in one reading which of two very different
things they are looking at.)*

**The declaration.** TTL **365 days**, `ttl_anchor: from_entity_freshness`,
anchored on the **reported quarter end** (§B.1 element 3). For the pinned
period that resolves to `2026-03-31`, so:

> **`expires_at` = 2027-03-31.**

**Refusal one — after 2027-03-31, and it is the gate working.**
`src/ccf/products/gates.py::_refuse_ttl` requires
`now < expires_at <= now + MAX_TTL`. Once the pinned period is more than 365
days old, `now < expires_at` is false and the product is **refused**. That is
**correct behavior, not a defect and not an example bug.** The declared
duration is the amendment window: what makes this answer wrong is a
restatement of *that* period (§E.4), and after a year the probability that an
unrestated reading is still the register's current statement is not one this
spec is willing to assert. **The example has a shelf life and it is written
down here rather than discovered by a red CI run in 2027.** Whether the
answer at that point is a longer duration, a moving pin, or an accepted
end-of-life is a decision for whoever holds the example then — §F, marker 18.

**Refusal two — today, on a deployment whose `MAX_TTL` default is too short,
and it is a CONFIGURATION mismatch.** The same gate's **upper** bound
requires `expires_at <= now + MAX_TTL`. This product's TTL is 365 days, so:

> **Control Plane obligation: the class's `MAX_TTL` artifact
> (`src/ccf/products/contract.py::MaxTTL`) must declare at least
> 31,536,000 seconds (365 days).**

A deployment whose default is shorter — an hour, a day, a week — refuses this
product **on its very first call**, before the archive has aged at all. **That
refusal is a mis-configured deployment, not a broken example**, and the two
are trivial to confuse because they come out of the same gate.

**How to tell them apart in one reading:**

| What you observe | Which refusal | What to do |
| --- | --- | --- |
| The refusal names the **lower** bound — `expires_at` is in the past — and today's date is after 2027-03-31 | **Refusal one.** The gate working | Nothing is broken. Read §F marker 18 and decide the product's future |
| The refusal names the **upper** bound — `expires_at` exceeds `now + MAX_TTL` — and today's date is before 2027-03-31 | **Refusal two.** A configuration mismatch | Raise the deployment's `MAX_TTL` to ≥ 31,536,000 s. Do not shorten this product's TTL to fit a default nobody chose |

---

## Section F — Source binding & readiness

*(Standard §6.)*

**Schema and table only. No host, no port and no credential appears in this
document, and none may enter the example tree.** The connection reaches the
deployment through a **declared environment-variable NAME** and through
nothing else — the shape
`examples/s1-00-companies-over-revenue/backends.yaml` uses, whose own comment
puts the reason exactly: *"a DSN in a content-hashed artifact is a DSN
persisted into the audit plane forever."*

### F.1 Element readiness

| Element | System of record | Interface & cadence | Available today | Gap owner | Blocker |
| --- | --- | --- | --- | --- | --- |
| Issuer identity (`lei`) | SEC Form 13F → `ccf_v2.institutional_holder` | Set-based read; archive, refreshed on load | **yes** | — | — |
| Issuer registered name | Entity reference → `ccf_v2.legal_entity` | Set-based read; **cadence unpublished** | **partial** — the value is present for 48 of 48 anchors in the pinned period; the *refresh cadence* is not published | CCF SDK examples maintainer | The archive publishes no refresh interval (marker 4) |
| Manager identity (`manager_cik`, `manager_name`) | SEC Form 13F | Set-based read | **yes** | — | — |
| Held security (`cusip`) | SEC Form 13F | Set-based read | **yes** | — | — |
| Reported position value (`value_usd`), share count (`shares`) | SEC Form 13F | Set-based read | **yes** | — | — |
| Reported period (`report_period`) | SEC Form 13F | Set-based read | **yes** | — | — |
| Issuer-match score and band | SEC Form 13F loader — **derived upstream, not by this assembly** | Computed at load | **yes** | Source-system owner (the loader) | — |
| Row provenance flag | SEC Form 13F loader | Computed at load | **yes** | — | — |
| Resolved dominant security | **This assembly** — §D.2 step 1 | Group-and-rank at the source read | **partial** — the capability §C.2 names as most likely to be absent. Where the estate cannot rank inside a read, §C.2's interim posture takes over and the product ships as `v1.0.0-partial` | CCF SDK examples maintainer | Estate capability, unmeasured against the target estate |
| **Percent-of-class concentration** | **none** | — | **no** | CCF SDK examples maintainer | **Not derivable from this estate.** `ccf_v2.financial_fact` carries 21 distinct XBRL tags and `tag ilike '%Shares%'` returns `[]`, against a `%Revenue%` control returning four (§B.4). There is no shares-outstanding fact, so there is no denominator |

### F.2 Every `[TBC]` in this document, with an owner

**Eighteen markers. Every one raised anywhere above reappears here** — that is
Standard §0.2, and it is what makes a spec with honest gaps buildable. *No
spec passes review with an unowned gap; "does not exist yet" is a valid state,
unattributed is not.*

**Stated as a ROSTER rather than as a count, per `24-CONTEXT.md` `D-65`** —
*"`assert n == 4` tests arithmetic; `assert set(ids) == {E1, E2, E3, E4}` tests
whether you still know what you counted."* Of the eighteen:

- **CLOSED — `{13, 14, 16}`**, three markers.
- **HALF-CLOSED — `{15}`**, one marker. Its **latency** half is closed on a
  measured run (§D.2, §G); its **per-call cost** half stays open, with an
  owner, because this deployment has no billing meter and `D-64` is explicit
  that the fallback is a split and not a licence to estimate: *"don't invent
  dollars."*
- **OPEN — `{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 17, 18}`**, fourteen
  markers.

3 + 1 + 14 = 18, and the three sets are disjoint. A closed marker keeps its row
rather than being deleted: the row is where a reader learns what the value is
and what closed it, and a marker that vanished would leave the sentence that
raised it pointing at nothing.

| # | Marker | Raised at | Owner | What closes it |
| --- | --- | --- | --- | --- |
| 1 | The approved **domain list** the registry name assumes | front matter | Platform / catalog owner | An approved domain taxonomy; `holdings` is proposed against it |
| 2 | The **accountable-owner triad** — product owner, data steward, policy owner | front matter, §G | Whoever adopts this product outside the examples suite | A real catalog entry. Naming a bank function for a teaching artifact would be inventing an organisation |
| 3 | The **payload schema** key and version | §B.1 element 1 | The wave that authors `ccf_config.yaml` | The artifact existing. **§D fixes the value it must carry**: `schema_name: holdings.institutional-holders`, `schema_version: 1.0.0`, and therefore `plan_id: holdings.institutional-holders` — the `s1-00` precedent, where `plan_id` is `product_class.schema_name`. The marker is on the *artifact*, not on the value |
| 4 | The **issuer-identity refresh cadence** | §B.1 element 2, §E.1 | Source-estate owner | The archive publishing one |
| 5 | The **policy bundle** version id | §B.1 element 4 | The wave that authors the policy bundle | The artifact existing |
| 6 | The **intent registry** (Standard §11.1) | §B.4 | Platform | An intent registry existing in this deployment. Until then the accepted values are declared on the product class rather than resolved against a governed registry |
| 7 | Ontology IRI — **held security** | §C.1 | Ontology owner | A bound term for a security identifier in this estate's IRI binding contract |
| 8 | Ontology IRI — **reported position value and share count** | §C.1 | Ontology owner | As above |
| 9 | Ontology IRI — **reported period** | §C.1 | Ontology owner | As above |
| 10 | Ontology IRI — **issuer-match score and band** | §C.1 | Ontology owner | As above |
| 11 | Ontology IRI — **row provenance flag** | §C.1 | Ontology owner | As above |
| 12 | Ontology IRI — **resolved dominant security** | §C.1 | Ontology owner | As above |
| ~~13~~ | **`C_attributes` measured value** at the anchor | §E.2 | The wave that runs the assembly | **CLOSED.** The shipped run measured **1,748 of 1,748 = 1** at the anchor, with two controls recorded at §E.2. It was a measurement and not a decision, exactly as this row said |
| ~~14~~ | **A row exactly at a threshold value** in the CI fixture | §F.3 volumetrics | The wave that authors the seeded CI fixture (`24-CONTEXT.md` `D-25`/`D-27`) | **CLOSED.** `tests/examples/fixtures/cp_00_13f_rows.sql` designates one by construction, and `tests/examples/test_cp_00_output.py::test_a_row_exactly_at_the_threshold_is_served` asks at exactly that value and requires the inclusive read to return exactly one row more than the strict one. Measured RED against a threshold nudged one unit off every seeded value |
| **15** | **Measured p50 / p95 latency and per-call cost** — **HALF-CLOSED 2026-08-27** | §D.2, §G | **Latency:** the wave that ran the assembly (`24-CONTEXT.md` `D-64`) — DISCHARGED. **Cost, in money:** whoever operates this product on a metered substrate — the same owner class as marker 2, and named that way rather than assigned to a teaching artifact's maintainer who has no meter to read | **LATENCY CLOSED.** 40 calls against the live estate: **p50 10,141 ms, p95 11,786 ms**, instrument named in §G. **COST STILL OPEN, and deliberately not invented.** What *is* measured and is not a dollar figure: **0 model tokens per call** — Assembly Mode 1 is algorithmic end to end and the tree carries no LLM client, gated by `tests/examples/test_cp_00_is_algorithmic.py` and watched RED on an injected import — and **2.93 client CPU-seconds per call**, 28.5% of wall time, against a meter control that reports 300.0 ms for a 300 ms spin and 0.1 ms for a 300 ms sleep. What is NOT measured: the source estate's own compute, which runs on a shared host with no per-query accounting, and any monetary rate at all. §13's certification evidence still wants the cost half before this product leaves `draft` |
| ~~16~~ | **`debt_tolerance` bands** — `forced_llm_threshold`, `fail_closed_threshold` — and `risk_sensitivity` | §E.1, §E.2, §G | The wave that authors the debt profile | **CLOSED** by `24-CONTEXT.md` `D-52`. `ccf_config.yaml`'s `debt_profile:` declares **1.0 / 0.60 / 0.77**, set together with λ_c as this row required; §E.2 carries the bands, the crossings (days **168** and **278**) and the demonstration `D_c` of **0.558** |
| **17** | **Replay-record retention tier** — full-fidelity, compressed or tombstoned — and the severity rule assigning it | §G | Platform / records owner | A retention policy for this deployment |
| **18** | **What happens to this product after 2027-03-31** — longer duration, moving pin, or accepted end-of-life | §E.5 | Whoever holds the example then | A decision. Flagged now rather than met as a red CI run |

### F.3 Access path, identifiers, history, text and volumetrics

**Access path.** An **existing read-only relational feed** — a set-based query
against schema `ccf_v2` of **PostgreSQL**, the source estate's relational store.
Not CDC, not an event stream, not a new build.

> **The store name was removed here once, and is restored — a correction, with
> its reason, rather than a silent re-edit.** An earlier revision struck the
> database's name on the literal reading of Standard §10.1, *"product specs
> never name a database."* **Dave ruled on 2026-08-29 that §10.1 governs the
> vault level** — the implementation-independent product specification — and
> **not** the SDK level, which this document occupies. At this level the rule
> inverts: *"If the database is unknown how can we even reference the tables?"*
> In a five-store estate `ccf_v2.institutional_holder` does not say whether that
> is the relational store, the graph ledger, the document store or the
> departmental file, and this is the first example a developer reads.
> `CP-SPEC-001` §0 and `spec_generation.md` §1.1 carry the full frame.
> **Deployment — host, port, credential, instance — stays out at both levels**,
> and remains in `backends.yaml` as an environment-variable name.

Locally the example points at the real store; in CI the same code
path runs against a **CI-provisioned service container the test seeds itself**
from a small 13F fixture (`24-CONTEXT.md` `D-25`/`D-27`), because CI cannot
reach the host the estate runs on and no database secret belongs in a CI
configuration.

**Identifier reality.** The correlation keys exist end to end. `(lei,
report_period)` is the resolution key; `(lei, manager_cik, cusip,
report_period)` is the source row key and the table's primary key. Measured
crosswalk coverage from the holdings table to the reference table: **48 of 48**
distinct issuer LEIs in the pinned period, against a salted-key control
matching **0 of 48** (§C.3). The crosswalk is owned by the source estate's
loader, not by this product.

**History depth.** The source reconstructs back to `31-DEC-2014` — 46 distinct
`report_period` values across a decade (§C.4 trap 1). That bounds any `as_of`
this contract could advertise; it advertises none, because the period is
pinned by the spec rather than chosen by the caller. **The archive already
retains history**, so §6's *"start retaining deltas now"* rule does not bite
here — which is worth stating, because it does bite for most sources and a
reader should not generalise this product's comfort.

**Text-source boundary.** **None.** No claim in this payload rests on text,
nothing is extracted from a document, and no operator reaches into one at
runtime. The capability class and cost band are unchanged by this row, and
§B.1 element 5's absent passage anchors follow from it.

**First-build volumetrics** — the population the first build must contain for
every gate and counterfactual to have something to act on. All figures are
Wave 1's, cited rather than re-derived:

| Required case | Why it is required | Present? |
| --- | --- | --- |
| An issuer whose `(lei, period)` fans out to ≥ 2 CUSIPs | `IH-G01` has nothing to catch without it | **yes** — the anchor fans out to **6** |
| ≥ 1 manager whose only position is on a non-dominant security | It is what `IH-G01` must exclude | **yes** — **5** |
| ≥ 1 `weak`-band row on the dominant security | `IH-G03` and C_match are both vacuous without one | **yes** — **115** |
| ≥ 1 row outside the pinned period | `IH-G02` has nothing to catch without it | **yes** — **1,989** estate-wide |
| A threshold with a non-empty and a non-full answer | Otherwise the caller's parameter is decorative | **yes** — the sweep runs **1,748 → 21** across $0 → $1bn |
| ≥ 1 entity class with no classification attribute, in a negative fixture | `IH-G06` must be watched RED | **not yet** — the fixture is authored, so this is a construction obligation rather than a data gap |
| **A row whose `value_usd` exactly equals a threshold value** | **`IH-G04` cannot fail without one, and a gate that cannot fail proves nothing** | **yes**, by construction — `tests/examples/fixtures/cp_00_13f_rows.sql` designates one, chosen so that seeded rows sit both above and below it, and `tests/examples/test_cp_00_output.py` asks at exactly that value and requires the `>=` read to return exactly one row more than the `>` read. Marker 14 is CLOSED |

### F.4 Recorded findings — not `[TBC]`, because none of them needs a decision to build

Each of these is a **Standard-versus-SDK observation** for this phase's gap
register, recorded under `24-CONTEXT.md` `D-04` and **not closed here**;
closing any of them would be an SDK extension, which is a separate phase.

1. **`debt_tolerance` is not a request parameter in this SDK.** The bands are
   Control Plane state (`src/ccf/controlplane/artifacts.py::DebtProfile`),
   which is the better design on the merits — a caller who can move its own
   fail-closed band can decide to be served context the deployment ruled too
   stale to decide on (§B.4).
2. **An undeclared parameter is refused as `undeclared-parameter`, not under
   the Standard's `not_supported_at_tier` name** (§B.4, §D.6).
3. **Percent-of-class is not derivable from this estate** (§B.4, §F.1).
4. **The empty-operator gate is two different assertions sharing one name.**
   The SDK's refuses a product that *declares* no operators; the Standard's
   refuses an operator that *returns* an empty set. Covered here by product
   gates `IH-G05` and `IH-G07` (§D.7).
5. **The content address covers the whole vessel, not a deterministic subset.**
   Two live calls a second apart produce two addresses for one answer; replay
   is unaffected (§D.4).
6. **Classification containment and suppression silence are realized
   structurally at L4, not as post-assembly gates**
   (`src/ccf/operators/categories.py::PolicyFilter._admits`). Whether the
   Standard should say so is the finding; neither this product nor this SDK
   owes a post-assembly form (§D.7).
7. **The tier ladder charges `bitemporal-ledger` at Tier 3, but every CCF
   product reads a bitemporal graph by construction.** Unless capability
   classes are read as **estate** requirements, no CCF product could be Tier 1
   (§D.3).
8. **`Resolve` separates across two layers.** The canonical-entity half is at
   L2 as the mapping predicts; the dominant-security half is a group-and-rank
   the per-envelope L2 seam structurally cannot perform, and it runs at the
   source read (§D.3).
9. **The Standard fixes no numeric latency envelope for any tier**, so §D.2's
   budget is measured against an envelope this spec declares in §G.
10. **`python -m tools.lints.citations` exits 0 on a seeded broken citation
    and on a fabricated symbol; `python -m tools.lints --all` exits 1 and
    names both.** Recorded per `24-CONTEXT.md` `D-42` and **deliberately not
    fixed** — fixing a shipped tool is a build.

---

## Section G — Operate & govern

*(Standard §7.)*

| Entry | Content |
| --- | --- |
| **Accountable owner** | The CCF SDK examples maintainer operates this product. The product-owner / data-steward / policy-owner **triad** a real catalog entry carries is `[TBC]` — §F marker 2. This is a teaching artifact, and naming a bank function for it would be inventing an organisation |
| **Service objectives** | **DECLARED: p95 assembly latency envelope 1,000 ms**, declared here because the Standard fixes none per tier (§D.2); **p50 target 400 ms**; §D.2's step budgets sum to **620 ms — 62% of the envelope**, and every one of those cells is still a **declared budget, not a measurement**. **MEASURED 2026-08-27 (`24-CONTEXT.md` `D-64`) — and the declaration is contradicted: p50 10,141 ms, p95 11,786 ms**, which is **25.4×** the p50 target and **11.8×** the p95 envelope. The declaration is left standing beside the measurement rather than replaced by it, because choosing a new envelope is a decision and this row is not where it gets made; §D.2 attributes the whole excess to step 2's L2 ingest. **THE INSTRUMENT, named beside the numbers, because a number without its instrument is a number that looks like proof.** **How many calls:** 40 at the demonstration threshold, plus 10 each at two other thresholds as controls. 40 rather than 20 because at 20 the p95 is the maximum and rests on a single observation; at 40 the nearest-rank p95 is the 38th of 40 with **three** observations at or above it. Not 60+, because at ~10 s per call that exceeds the foreground budget this example's phase is bound to and the interval narrows little for the cost. **What clock:** `time.perf_counter_ns()` — MONOTONIC, nanosecond resolution, never a wall clock, so a time step cannot appear as latency; control, the same clock over a 300 ms sleep reported 250.5, 250.1, 250.1 and 250.5 ms across the four populations for its 250 ms probe. **Percentile method:** nearest rank on the sorted sample, `p_k = sorted[ceil(k/100 · N) − 1]`, no interpolation. **What a call is BOUNDED as:** exactly one `examples/cp-00-institutional-holders/assembler.py::HoldersAssembler` `assemble`, which is §D.2 steps **1 through 6** — INCLUDING the psycopg connection to the source estate, which opens inside `examples/cp-00-institutional-holders/deployment.py::read`, and the per-run fabric boot, which happens inside `src/ccf/deployment/config.py::load_config_and_boot` — and EXCLUDING process start, module import, this document being read and printed, temp-directory creation and `examples/cp-00-institutional-holders/deployment.py::connection`. A fresh scratch root per call, created OUTSIDE the timed region, because the fabric boots a fresh per-run graph inside the call and a reused root would accumulate state a served call never sees. **What "cost" MEANS here, and what it does not.** Measured: **0 model tokens per call**, structurally — Assembly Mode 1 acquires no content at decision time and the tree carries no LLM client, gated by `tests/examples/test_cp_00_is_algorithmic.py` and watched RED on an injected import — and **2.93 client CPU-seconds per call** (28.5% of wall), against a meter control reporting 300.0 ms for a 300 ms spin and 0.1 ms for a 300 ms sleep. NOT measured, and not estimated: the source estate's own compute, which runs on a shared host with no per-query accounting, and any monetary rate whatever. **Absolute per-call cost in money therefore stays `[TBC]` — §F marker 15's open half** — alongside the relative band (**×1**, Tier-1 baseline). Expected volume: **example scale**, single-digit calls per run, no concurrency ceiling asserted because none has been tested — and the measurement above is single-caller and cold-boot throughout, so it says nothing about either. Payload bound: the anchor at threshold 0 serves **1,748 holder rows**; a caller passing 0 gets the whole register, which is a legitimate and deliberately un-capped answer — and costs about **5%** more than the 21-row answer, which is the control that puts the cost in the ingest rather than in Π |
| **Degradation contract** | **Mandatory classes, named explicitly:** reported position value, reported period, and the resolved dominant security. Any of the three unavailable → **fail closed** (503, or 404 where the anchor resolves to no security) — never a partial payload. **Non-mandatory:** manager name, issuer registered name, share count, issuer match band → **partial payload with the field marked `NOT_EVALUABLE`, `notices` populated, and `D_c` elevated** (§E.2). The band is the one to watch: losing it makes `C_match` itself `NOT_EVALUABLE` rather than 1.0 |
| **Debt model** | `D_c = 1 − (F · C · S)` with `C = C_attributes × C_match`. **F** is driven by the reported position's age from `valid_from` against a 137-day λ_c, over rows **assembled**. **C** is driven by declared-attribute presence and by `issuer_match_band`. **S** is 1 — one source cannot disagree with itself. `debt_tolerance`: **`risk_sensitivity` 1.0, `forced_llm_threshold` 0.60, `fail_closed_threshold` 0.77**, declared in `ccf_config.yaml`'s `debt_profile:` and **set together with λ_c** (`24-CONTEXT.md` `D-52`; §F marker 16 CLOSED). Its basis is the pairing itself: a 148-day-old pinned period against a 137-day half-life delivers `D_c` **0.558**, and the bands are crossed at days **168** and **278** — a tolerance chosen in ignorance of the half-life would have refused the product on its first call |
| **Observability** | Per-operator latency (steps 3–5 individually, since step 2 dominates and is the one an optimisation would target) · the `D_c` distribution, not only its mean · gate-failure counts **by gate**, so a TTL refusal is never read as a lineage refusal (§E.5 turns on exactly that distinction) · cache hit rate (currently n/a — `derived-on-demand`) · entitlement denials (expected: **zero**, and a non-zero count is itself the signal) · degradation-branch frequency per non-mandatory input · supersession-triggered invalidations, split local versus cascading. **This is also the evidence base that moves λ_c from `illustrative` to `measured`.** Marker 16's bands are closed already (`D-52`), which is a different thing from λ_c being measured, and the two must not be read as one. **AMENDED 2026-08-27, marked rather than rewritten. OLD CLAUSE:** *"marker 15 closes from here and nowhere else."* **It was wrong, and it is worth saying why rather than deleting it.** It bound a latency figure to an operational evidence base that does not exist yet, and so made a measurable thing look unmeasurable — which is precisely what `D-64` refuses: *"An honest gap is for things you cannot measure; this one you can."* **NEW CLAUSE:** marker 15's **latency** half closed from a direct measured run of the assembly, recorded in the service-objectives row above and in §D.2, and it did not need this row at all. What this row still owes is the **cost** half in an operated deployment with a meter, and the λ_c move, which are two different obligations and were being read as one |
| **Retention & record of record** | The **record of record is the source estate**, per element and without exception: `ccf_v2.institutional_holder` for every position element, `ccf_v2.legal_entity` for the issuer's registered name. **The fabric references it and does not replace it** — nothing this product runs writes to the store it reads (§C.3), and the CCF graph is a per-run local file. Replay-record retention tier — full-fidelity, compressed or tombstoned — and the severity rule assigning it: `[TBC]` — §F marker 17 |
| **Test fixtures** | Happy path: the anchor at a threshold inside the sweep. One fixture per product gate, `IH-G01` through `IH-G08` (§D.7), each **watched RED** against a seeded violation before it is trusted — a gate that has never failed has not been tested. One fixture per degradation branch, one per mandatory-input failure. And a **replay hash assertion**: §D.5's four-step test, ending on byte-identical `product_content_address` |
| **Lifecycle** | **`draft`**, 2026-08-26, reviewer `[TBC]` — §F marker 2. Not registered and not certified: §2.1 names registering before §G is complete as the common error, and §13's certification evidence is **partly** on file. **UPDATED 2026-08-27 (`24-CONTEXT.md` `D-64`).** Markers 13 and 16 are closed; **marker 15 is HALF-CLOSED** — its measured **p50 (10,141 ms) and p95 (11,786 ms) are on file with their instrument named**, and its **per-call cost in money is the one certification evidence still owed**, held open with an owner rather than invented. **A second thing is now owed that was not owed before, and it is owed BECAUSE of the measurement:** the measured p95 is **11.8×** this section's declared 1,000 ms envelope, so either the envelope is re-declared against evidence or the ingest is materialized per §D.2's point 3 — and until one of those happens this product would be certified against a service objective it does not meet. That is a decision, and it belongs to whoever adopts this product, so it is named here rather than settled here. **Deprecation, when it comes, requires:** consumer notification from §B.5 — the list is **empty today**, so the obligation is currently vacuous and will stop being vacuous the moment the second rung of the ladder consumes this one; a sunset date at least one migration window out; and a named successor **or an explicit statement that none exists** |

### G.1 The expiry obligation, restated where an operator will look for it

*(`24-CONTEXT.md` `D-43`. The full treatment is §E.5; this row exists so that
an operator reading §G alone does not miss it.)*

- **This product's `expires_at` is `2027-03-31`.** After that date
  `src/ccf/products/gates.py::_refuse_ttl` refuses it. **That is the gate
  working, not a defect** — see §F marker 18 for who decides what happens
  next.
- **The deployment's `MAX_TTL` must declare at least 31,536,000 seconds
  (365 days).** A shorter default refuses this product **on its first call**,
  today, at the gate's **upper** bound. **That is a configuration mismatch,
  not an example bug**, and the remedy is to raise `MAX_TTL` — never to
  shorten this product's declared TTL to fit a default nobody chose.
- §E.5 carries the two-row table that tells the two refusals apart from the
  refusal message alone.

### G.2 Acceptance criteria

Each assertion below is **specific to this product**, independently
verifiable, and **phrased so that it can fail**. The universal definition of
done is Standard §15; these are what this product must additionally prove.

1. The served payload validates against
   `src/ccf/products/contract.py::ContextProductContract`, and
   `src/ccf/products/gates.py::run_gates` returns a
   `src/ccf/products/gates.py::ServableProduct` rather than a
   `::GateRefusal` — **with the refusal branch also exercised**, because a
   `ServableProduct` is evidence only if the alternative is reachable.
2. Every step in §D.2 has a row in
   `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml`, and
   every row has a step — **set equality in both directions**, not
   containment.
3. Every witness declared in that document is **observed on a completed run**,
   and **each witness kind is watched RED** against a run in which the fact it
   names is absent. A witness that cannot fail proves nothing.
4. `lineage.operators_invoked` equals the engine-resolved set exactly, in both
   directions, and contains `policy.principal-subgraph` and
   `temporal.as-of-boundary` and nothing else.
5. `IH-G01` … `IH-G08` (§D.7) each pass on the happy path **and each fail on a
   seeded violation.**
6. A request omitting `minimum_position_usd` is **refused as data** by
   `src/ccf/products/request.py::refuse_request` — not defaulted, not
   accepted, and not raised as an exception.
7. A manager whose `value_usd` **equals** the threshold **is served** (`>=`,
   §D.3).
8. §D.5's replay test returns a **byte-identical** `product_content_address`
   at the recorded snapshot after the underlying state has demonstrably
   moved — and step 3 of that test confirms the live re-derivation returned
   the **new** value, so step 4's success is not vacuous.
9. §D.5's second test shows the two time axes **disagreeing** under an
   amended filing. Agreement means a filter was dropped.
10. No module in the example tree imports an LLM client, asserted by a walk
    over every module and **watched RED on an injected import** (criterion 4).
11. The example prints its **specification** and its **resulting JSON**, both
    non-empty, with the JSON validating against the declared contract.
12. Every domain-specific value — the anchor, the pinned period, the
    threshold's absence of a default, the policy bundle, the half-life table —
    lives in a **definition artifact**, and the example's code still fails
    meaningfully with those artifacts deleted (the No-Hardcoding Rule,
    `CLAUDE.md` §6.4).

**Open decisions blocking build, named by their §F row.** None of the
eighteen markers blocks the build. Three shaped it and had to be settled before
the assembly could be run end to end rather than merely written. **All three
are now CLOSED (§F.2), and the assembly has been run** — so this list is a
record of what gated the build, not a list of what is still owed:

- **Marker 3** — the payload schema artifact. §D fixes the value it must
  carry; the artifact must exist before anything runs. **CLOSED.**
- **Marker 16** — the debt bands. A band set without reference to λ_c refuses
  the product on its first call (§E.2). **CLOSED** by `24-CONTEXT.md` `D-52`.
- **Marker 14** — a row exactly at a threshold value in the seeded fixture.
  Without it `IH-G04` cannot fail, and a gate that cannot fail is not a gate.
  **CLOSED.**

Markers 13 and 15 are **measurements the build produces**, not decisions that
gate it. The remaining thirteen are external dependencies — catalog, ontology
and platform decisions — none of which prevents this product from being
assembled, served and replayed.

### G.3 Catalog contribution

**What this product proves that no earlier product proved.** It is the first
Context Product in this repository specified to the **full** Standard before
the assembly it specifies exists — so it tests the **authoring** path, not
only the assembly path. It is the first to place `Resolve` at a layer, and the
first to find that the name does not sit at one layer. It is the first to
carry a specification's `[TBC]` markers all the way through to an owner table
rather than into a build.

**What it deliberately does not prove.** Multi-source assembly, and therefore
`S ≠ 1` and any semantic disagreement at all. `Enrich`, which it has no
occasion to use because every attribute arrives in the same row as the
position. Any Assembly Mode above 1. Products built off products. Federation
across an A2A boundary. Entitlement partitioning with something real behind
it — this product's `policy` step excludes nobody and says so. **None of these
is a tier boundary read as an oversight; each is the next rung's point.**

``````

</details>

<a id="source-standard"></a>

<details>
<summary>Specification Standard v0.3 — ccf_code@37ac3055</summary>

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
<summary>Specification generation recipe — ccf_code@37ac3055</summary>

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

<a id="source-implementation"></a>

<details>
<summary>Implementation walkthrough — refreshed 18 October 2026, SDK v1.0.2</summary>

Path: `05-reference/02-context-product-producer/examples/CP00_INSTITUTIONAL_HOLDERS.md`

``````text
# CP-00 — Institutional Holders

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-00-institutional-holders/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP00_INSTITUTIONAL_HOLDERS_ANALYSIS.md) · [HTML reading edition](CP00_INSTITUTIONAL_HOLDERS_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-00-institutional-holders/README.md`  
**Qualified specification:** `examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`  
**Qualified source:** `examples/cp-00-institutional-holders`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`

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

The warm-up Context Product: one source store, one system of record, one decision question. It proves that a Context Product starts with an approved specification and returns governed evidence beyond what a SELECT can provide. It also exercises the producer/assembler seam explicitly.

## The question

> Which institutional holders meet the caller's position threshold, and what governed evidence makes that answer safe to use?

## What to understand before you run it

- A Context Product is specified before it is coded.
- The source system is read-only; fabric state and product evidence are separate from the system of record.
- Assembly Mode 1 is pure algorithmic—no model participates in the trust path.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_00_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-00-institutional-holders/spec/` | The approved implementation specification; read first. |
| `examples/cp-00-institutional-holders/artifacts/` | Machine-readable recipe/question/expected evidence. |
| `examples/cp-00-institutional-holders/assembler.py` | The product's explicit ContextAssemblerProtocol implementation. |
| `examples/cp-00-institutional-holders/produce.py` | The governed product construction path. |
| `examples/cp-00-institutional-holders/run.py` | The demonstration caller/presentation. |
| `examples/cp-00-institutional-holders/README.md` | Qualified source narrative and run contract. |

## Run it

```bash
make venv
make example-cp-00
make example-cp-00 MIN_POSITION=500000000
make example-cp-00 SPEC=brief
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- A served product listing holders above the threshold.
- Context Debt, TTL/expiry, lineage/content identity and replay evidence accompanying the business answer.
- The threshold changes the governed answer rather than merely changing presentation.

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
| Raise/lower position threshold | `make example-cp-00 MIN_POSITION=500000000` | Membership and content address change. |
| Brief spec rendering | `make example-cp-00 SPEC=brief` | Only the displayed specification changes; product semantics do not. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_00_output.py tests/examples/test_cp_00_recipe_steps.py tests/examples/test_cp_00_is_algorithmic.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Spec-first product construction.
- Producer/assembler seam is real and structurally exercised.
- Pure algorithmic Context Product can still carry Debt, lineage, TTL and content identity.

## What it does not prove

- That this early source-tree shape is the preferred code-generation pattern for new products; use a canonical paved-road example such as CP-03C for that.
- Production calibration of thresholds or half-lives.

## Spec → code lesson for Cowork

Use CP-00 primarily for specification discipline and the smallest honest product. Do not copy its older explicit producer plumbing when the new product can use the paved-road facade.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.
``````

</details>

