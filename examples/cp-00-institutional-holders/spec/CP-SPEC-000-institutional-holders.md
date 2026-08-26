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
**not** been guessed. Every marker reappears in §F with a named owner (§F is
authored in the next wave; the markers are listed at §B and §C where they
arise). Per the Standard, an unmarked assumption is the more serious defect: a
marked gap gets closed and an invented one gets built.

### 0.3 Section skeleton

All seven sections appear, in order. Sections D–G are authored in the wave
following this one; their headings are not omitted here, they simply are not
yet written, and a reader meeting this document mid-phase should know which is
which.

| § | Section | In this document | State |
| --- | --- | --- | --- |
| A | Decision frame | `## Section A` | written |
| B | Contract | `## Section B` | written |
| C | Data catalog | `## Section C` | written |
| D | Assembly recipe | `## Section D` | next wave |
| E | Volatility, debt & materialization | `## Section E` | next wave |
| F | Source binding & readiness | `## Section F` | next wave |
| G | Operate & govern | `## Section G` | next wave |

### 0.4 Front matter

| Field | Value |
| --- | --- |
| Registry name | `holdings.institutional-holders.v1` — the `domain.product.vN` form Standard §12 requires. The approved **domain list** the standard assumes does not exist in this deployment; `holdings` is proposed, marker `[TBC]` for its approval, and it reappears in §F |
| Tier | **1** — `relational` only (§C.2). Tiers describe assembly complexity, not maturity and not build order |
| Assembly Mode | **1 — pure algorithmic.** `24-CONTEXT.md` `D-14`: *"an in process deterministic operator to assemble the context product"*. No model anywhere in the assembly path |
| Cost band | **×1**, the Tier-1 baseline. Standard §10.4's estimate resolves to the baseline here: no traversal (fan-out term 1), one enrich source, on-demand rather than materialized (factor 1), Mode-1 multiplier 1 |
| Lifecycle state | **draft** — not registered, not certified. Standard §2.1 Discovery: registering before §G is complete is the named common error, and §G is not yet written |
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
   `(issuer LEI, period)` to the dominant CUSIP — an L2 `Resolve` — not pinned
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
| 4 | **Policy Binding** | Regime: **public disclosure** — the source is a public regulatory filing. Version id: the deployment's policy bundle, `[TBC]` until the next wave authors it; its **version** rides the served product's lineage regardless of which bundle it is. **Entitlement scope: none is asserted, deliberately.** Every element in §C measures `provenance = 'public'` (22,476 of 22,476 rows in the holdings table, 156 of 156 in the reference table), so the highest classification of any element is `public` and there is no jurisdictional or entitlement partition to bind. Standard §2.1's named common error is *"asserting 'entitlement scope' with nothing behind it"*; a decorative scope on public-filing data is exactly that error, so this product asserts none and says why. `policy_version` is still emitted, so the ordering is established from the first product rather than retrofitted |
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
| **Resolved dominant security** for `(issuer, period)` | **Derived by this assembly** — the L2 `Resolve` step | derived | public | relational | **E** | `[TBC]` — §F |

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

The anchor carries **6 distinct CUSIPs** in the pinned period; estate-wide the
worst case is **one LEI reaching 52**. The fan-out under the anchor, measured
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
| **RESOLVE the security from `(lei, report_period)` to the dominant CUSIP** — an L2 `Resolve` step. **Not a pinned literal** | `24-CONTEXT.md` `D-39`/`D-40`/`D-41` (Dave, 2026-08-26). Three reasons on the record: the resolve step **is** the `Resolve` this phase's operator-mapping hypothesis must place at a layer, so pinning would skip the pressure test the phase exists to run; a pinned CUSIP is a **domain value** and would have to live in an artifact anyway under the No-Hardcoding Rule (`CLAUDE.md` §6.4); and one LEI fanning out to 52 securities is handled by resolving and hidden by pinning | An extra §D step, **accepted**. And the five off-security managers are not served — which is the point, not the cost |

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

*Authored in the next wave.* The operator step table, its per-step runtime
witnesses, the determinism class, the replay statement, the emitted contract
and the validation gates land here. Two things this section already owes: the
`Resolve` step of §C.4 trap 2, and the statement that the Standard's §4.7 debt
gate exists in this SDK as a **Control Plane posture** rather than as a fourth
gate inside `src/ccf/products/gates.py::run_gates` — the three shipped gates
stay at three.

## Section E — Volatility, debt & materialization

*Authored in the next wave.* Owed by §C.4 trap 3: the completeness accounting
for the served `weak` rows.

## Section F — Source binding & readiness

*Authored in the next wave.* Every `[TBC]` marker raised above reappears here
with a named owner, including: the approved domain list; the payload schema
artifact; the issuer-identity refresh cadence; the policy bundle version; the
intent registry; the ontology IRI bindings for security, position, period,
match band and provenance; the absence of a shares-outstanding fact; and the
two Standard-vs-SDK divergences recorded at §B.4.

## Section G — Operate & govern

*Authored in the next wave.* Registration is deliberately deferred until it is
written (§B.1 element 7).
