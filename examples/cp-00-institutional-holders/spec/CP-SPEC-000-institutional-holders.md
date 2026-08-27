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
the honest statement is the four above — not a claim that the behaviour in them
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
and ruled `D-59` **record-only**: the local L1 registration is the right path
for this product, and closing the seam is additive SDK work for a later phase
(`D-58`), not for this one. The consequence for this table is nil in both
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

| Component | May be absent? | D_c contribution | Behaviour when absent |
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
**correct behaviour, not a defect and not an example bug.** The declared
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
against the `ccf_v2` schema of the source estate. Not CDC, not an event stream,
not a new build. (The database's own NAME was here and is removed: Standard
§10.1's rule is that *"product specs never name a database"*, and §0.4's
capability-gate note says this document names none. Schema and table stay,
because §F is where estate binding belongs.) Locally the example points at the real store; in CI the same code
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
