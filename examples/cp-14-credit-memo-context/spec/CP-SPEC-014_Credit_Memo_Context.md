---
product: credit-risk.credit-memo.v1
standard: v0-3
sdk_spec: cp-14
tier: 4
assembly_mode: 1
cost_band: "×8–15 derived-on-demand"
capability_classes: [relational, bitemporal-ledger, graph-traversal, document-passage, vector-index, in-memory]
prerequisites: [obligor-financial-spread, corporate-family-tree, credit-exposure-rollup,
  collateral-and-setoff-coverage, covenant-cross-reference]
build_order: 14
lifecycle: draft
accountable_owner: credit-risk-product-engineering
review_cadence: at every Control Plane change to the debt weighting, the memo section
  templates, or the credit-memo policy envelope; and no less than annually
topic: context-products
title: Credit Memo Context — Context Product Specification
generated: '2026-09-14'
---

# Credit Memo Context — Context Product Specification

**`CP-SPEC-014` · Tier 4 · `credit-risk.credit-memo.v1` · Assembly Mode 1**
**PostgreSQL for the peer frames, the templates and the relationship history · MongoDB for the narrative text and the passages · Fluree for the policy envelope and the definition chain**

> **What goes in the credit memo — and what is missing from it?**
>
> Not the narrative. The **substrate**: every section of the memo, the evidence
> under each section, and a measured statement of what could not be evidenced.
> The memo itself is written by an agent reading this product. This product's
> job is to be the last thing in the chain that is allowed to be wrong in a way
> anybody can check.

## 0 · What this document is

A build specification for the engineer who will assemble this Context Product
from the markets and credit data estate. **Every figure below was measured
against the live estate on 2026-09-14 before this revision was written**, and
the query that produced it is reproducible.

### 0.0 The child-content connection — required, and now supplied by the SDK

**The requirement was never withdrawn.** CP-14 consumes the five child Context
Products' **content and governing evidence**: the memo substrate's exposure,
financial, family, collateral and covenant material comes from those products'
served payloads; their debt, lineage, expiry and replay rows come from the same
admitted instances.

**Current SDK behavior, re-measured on `main` at `c635037f` (`D-GATE-339`).**
The connection exists. Children are acquired and admitted **once, before the
plan**; the plan receives their contracts as a read-only `ChildContractView`
through `CompositePlanFactoryProtocol.build_with_children`; the parent's
scorer receives the same view through
`ChildAwareDebtScorerProtocol.score_with_children`; `compose_children` runs
over the **same** acquired outcomes; a known blocking outcome refuses before
any child-dependent computation; each admitted contract is retained by content
address under `ADMITTED_CHILD_CONTRACT_CLASS`; and `replay()` rebuilds the view
from those bytes — never from a provider — before resolving the plan through
`CompositeReplayEnvironment.resolve_composite_plan`.

**Disposition: closed by `D-IMPL-339`.** The 2026-09-14 Gate-1 measurement
that found the gap — the plan built and executed before any child was
dispatched, and the admitted children dropped the moment composition returned —
is retained in `D-IMPL-339`'s decision entry and in §H.1 as the record of what
was proposed; it is no longer true of `main`. What this product owns and must
not rebuild is unchanged (§B.8): the atomic providers own their assembly, skills
acquire their products, and this composite owns the roll-up and the mapping
into memo sections.

### 0.0a Current status — what the 2026-09-17 delivery proves, and what it does not

**This delivery proves five-provider acquisition, admitted-content composition,
governed refusal, and reconstruction. It does not complete the full memo-assembly
specification.** It is accepted, if accepted, as the five-provider SDK composition and
reconstruction milestone — not as the completed implementation of the twenty-nine
gates this document declares.

What is proven, executably, against the five real producers in five other processes
(`tests/examples/test_cp_14_fourth_slice.py`; twelve `CMC-G` gates on the roster):
the governed question refuses with five rows and the first blocking producer's reason
retained; the labeled diagnostic admits all five children and serves a memo whose
five sections are read, member by member, off the admitted contracts; a controlled
child variant moves its section and nothing else; served and refused determinations
reconstruct with every producer exited; the same diagnostic question asked twice
yields one product address.

What is NOT built, and stays a planned obligation of this contract rather than a
passed one — **a scope status, not an engineered-estate limitation**: the memo's own
assembly beyond the obligor's identity and the five sections. Two kinds are kept
apart. *Optional memo enrichment* (product logic this consumer has not written):
template sections and `EvidenceRef[]` (§B.1, `CMC-G08`, `G09`), peer benchmarks and
thinness (`G10`, `G14`), the relationship summary, the suppression rule (`G11`), the
dated diagnostic comparison (`G05`), the declared-but-inert `peer_basis` (`G12`).
*Governed behavior this delivery does not yet exercise* (SDK guarantees the memo has
not put under test): the policy-version tolerance default and its date boundary
(`G07`, `G25`), the refusal's governing decomposition at the disclosure floor (`G13`),
policy-before-similarity on the memo's own trace (`G06`), the mixing floors (`G21`),
the empty-`sic` guard (`G24`), the empty-operator guard (`G01`), passage
resolvability (`G09`), determinism across independent processes beyond the bounded
in-session repeat (`G15`), TRAP 1a (`G16`). None is marked passed; none is deleted.

The request contract is aligned with what is implemented: `memo_type` admits
`annual-review` only (`argument_domains`); the other three templates §B.2 plans are
refused `not-in-domain` rather than carried as a label that selected nothing.

### 0.1 The governing question

> **Can a product report the shortfall in its own evidence — and can it still
> do that when the shortfall figure it was handed was measured against a
> different state of the estate?**

Rung 13 asked whether a claim could cite text it had actually checked. This
rung asks the question one layer out. Context Debt is not a property of a
product; it is a **measurement**, and a measurement is made against a
particular state of the world at a particular time. The estate ships a table of
per-obligor Context Debt — `ccf_v2.memo_context_debt`, 20 rows, `as_of`
**2026-08-22** — and a product could read `aggregate_debt` from it and serve a
governed-looking answer in one query.

**Measured 2026-09-14, that table and the current graph disagree — and the
disagreement is now located precisely.** Three of the table's four components
re-derive exactly from the estate today. The fourth has an exact-fit structural
explanation. **What does not re-derive is a pair of integers**:
`definition_refs_unverified` = **181** and `definition_refs_verified` = **90**,
summing to **271**. Against the current graph, **194 of 194** cross-references
reachable from the roster's facilities resolve — 193 to a declared
`ex:DefinedTerm`, 1 to a `Report`, **0** unresolved — and **44 of 44**
`ex:PassageAnchor` nodes read `anchorVerified`. The estate owner re-keyed the
covenant anchors on **2026-09-13**, three weeks after the table was computed.

**The stale thing is two counters, not an opaque curve.** That is a sharper
statement than the previous draft's, and it is the one the evidence supports.

**And the disagreement is robust to the passage of time.** Recomputing
`signal_staleness` today with the estate's own closed form adds a constant
`23/730 = 0.0315` to every row — every obligor's `max(period_end)` is fixed, so
all twenty drift identically — and `0.15 × 0.0315 = 0.0047` to every aggregate.
**Serve counts are unchanged: still 9 of 20 at tolerance 0.30 and 6 of 20 at
0.25.** Nobody crosses either boundary. So the divergence this rung is about
comes entirely from the anchor counters, and not from the table merely ageing.

**What is demonstrated, stated precisely.** The defect is **applying a
measurement taken against one state of the estate to a decision about
another** — not that the August figures were once right and have since gone
wrong. *This spec does not claim the August measurement was correct when it was
taken.* Its original correctness has **not** been established here, and an
`as_of` on a row is a claim about when it was written, never evidence that it
was right. Both readings — a correct measurement overtaken by a repair, and a
measurement that was always wrong — produce the same disagreement today, and
this rung does not need to distinguish them to make its point.

That is the rung. A product that **reads** its governing debt from a figure
measured against another estate state cannot know which of those two it is
publishing. A product that **computes** its debt from the primary evidence, at
request time, is answerable for the number it serves. The stored table does not
stop being useful — it becomes a **diagnostic comparison**, and the gap between
the two is a recorded finding rather than an embarrassment.

**And the evidence debt did not go away — it changed shape.** Rung 13's
distinction holds and is measured again here (§C.4 TRAP 1a): **a reference
resolving is not the same as a passage being auditable.** Repaired anchor
identities do not erase point-anchor or unverifiable-span debt — and there is
**no repair path**, because not one covenant-definition span is contained in,
or even overlaps, any verified passage anchor's span in the same document.

### 0.2 Placeholder discipline

No `[TBC]` except the p95 budgets and payload hashes, which cannot exist before
code does and close at Gate 2. Every one appears again in §F.4 with an owner.

### 0.3 Reads only — no write path anywhere in this product

Every leg is a read. The product acquires from PostgreSQL `ccf_v2`, MongoDB
`fibo_v2` and Fluree `fibo-v2` on the curated estate and writes to none of
them. Per `CLAUDE.md` §9 the curated estate is evidence, not a fixture; the
Fluree ledger is append-only and a seeded ledger is permanent.

### 0.4 The contract — seven decisions RULED, one new item for Dave

**RULED 2026-09-13, unchanged by this revision.**

| # | Decision | Ruled |
| --- | --- | --- |
| 1 | **Assembly Mode** | **Mode 1 — algorithmic evidence assembly.** The memo-writing skill sits outside the product. Composition does not force Mode 3 |
| 2 | **Debt model** | **The Standard's multiplicative model governs serving.** `D_c = 1 − (F · C · S)` |
| 3 | **The historical debt table** | **Comparison only, never the governing debt source** |
| 4 | **Cascade case** | **CION is the real missing-evidence case.** Do not repair the estate and do not attach the orphaned engineered node |
| 5 | **Passage claims** | **Similarity within the permitted corpus.** No unsupported Item 1A / Item 7 attribution |
| 6 | **ECOA flag** | **Recorded and explicitly inert in this example** — not claimed as enforcement |
| 7 | **Composition** | **Supplied by `D-IMPL-336`/`D-IMPL-337`, consumed here.** No local substitute |

**NEW, and it needs Dave: §0.0's missing SDK connection.** Every ruling above
survives it and **the requirement is unchanged** — what is missing is a
platform connection, and §H.1 proposes the smallest change that closes it.
Carried to §H as the one blocking item.

**Why Mode 1, against the canonical definitions.** The Standard's modes are:
**1** pure algorithmic · **2** algorithmic with LLM packaging · **3**
algorithmic orchestration with **agent-swarm assembly**. Mode 3 names the
swarm, and `D-IMPL-336` is a swarm pattern, so the reading that this product
must be Mode 3 is worth answering rather than dismissing.

It does not follow, because **the mode classifies what is in the product's
trust path, not how many processes contributed to it.** Every step this product
takes — including invoking child skills, admitting their governed products, and
composing them — is deterministic computation over typed state. **No model
appears anywhere in the chain.** A composite of five algorithmic children,
assembled algorithmically, is algorithmic; multiplying the number of
deterministic producers does not make the result non-deterministic. Mode 3's
distinguishing feature is *assembly whose output depends on agent reasoning*,
and nothing here reasons.

The consequences are the ones Mode 1 carries: `model_record` is **not
applicable**, §2.3's model-risk annotation does **not** apply, and second-line
model risk has no registration obligation.

### 0.5 The composition capability is SHIPPED, and this product consumes it

**The hold is lifted, and both SDK phases this rung waited on are merged.**
`D-IMPL-336` (composite Context Products) merged at `78a603bb`; `D-IMPL-337`
(guarded-path provenance) at `31dc12c3`; **`D-IMPL-338`** (child evidence on
every downstream refusal) at `4c77cc60`; **`D-IMPL-339`** (acquire once; child
contracts to the parent's computation) at `c635037f`. All are on `main`. The 2026-09-13 draft's *"awaiting implementation GO · CP-14
acquisition is on HOLD"* is superseded and has been removed.

**This product implements no composition.** It declares, registers and wires;
the SDK does the rest. The split is exact:

**Control Plane artifacts CP-14 authors — no code:**

| Artifact | Carries |
| --- | --- |
| `ProductClassDeclaration` (`requires:`) | the five `ChildRequirement` rows (§B.7) |
| 5 × `SkillCatalogEntry` | `produces = <child schema_name>`, plus each child's binding |
| 5 × `SkillGrant` | naming the composing agent's definition content hash |
| `AgentDefinition` | the composing agent, with its policy-regime reference |
| policy bundle | `skill_governance` — permitted scopes, whether a grant needs approval |

**Thin generic code CP-14 owns — and nothing more:**

- a `child_arguments` callable — *what each child is asked* is the deployment's
  to state and the SDK holds no domain value;
- construction of `GrantBoundChildResolver` and `CompositeAdmissionGate`;
- one keyword argument: `composite_children=` on `build_governed_resolver`;
- a **named** plan factory implementing `build_with_children` — the
  product-specific mapping from the five admitted contracts into memo sections
  (`D-IMPL-137` row C: never a lambda);
- a scorer implementing `score_with_children`, so this product's own `C` and
  `S` read the same admitted contracts per request (§E.2.1).

**A local substitute is forbidden** (`CLAUDE.md` §9). Concretely, this product
may not hand-roll child resolution from a requirement, child admission,
inherited-debt composition, or a per-child replay record — each is the SDK's,
and each is token-guarded so a hand-built stand-in cannot reach the composition
path at all. `CMC-G23` makes it checkable.

**What the shipped surface does for this product,** each cited to code:

| Concern | Shipped mechanism |
| --- | --- |
| Child resolution | `src/ccf/products/composite.py::resolve_producing_grant` — class→skill over the agent's live grants; two producers of one class **raise** |
| Child acquisition | `src/ccf/products/child_resolver.py::GrantBoundChildResolver` — grant → dispatch → the child's own governed door → admission |
| Child admission | `src/ccf/products/composite.py::CompositeAdmissionGate` — seven checks: tenant, class, version lane, reconstruction instant, **recomputed** content address, assessable debt, eligibility |
| Composition | `src/ccf/products/composite.py::compose_children` — walks the requirements in declaration order and applies all four laws |
| Inherited debt | `src/ccf/halflife/debt.py::compose_debt_factors` — per-factor **minimum** over strength factors |
| Lineage | `src/ccf/products/composition.py::compose_lineage` — N-way set-union |
| Expiry | `src/ccf/products/composition.py::compose_expiry` — the floor, as an unconditional third term |
| Mixing refusal | `src/ccf/products/composition.py::refuse_mixing` — a breached validity floor refuses assembly outright |
| Per-child replay | `src/ccf/replay/record.py::ChildResolution` — one row per requirement, on the served path and on **every refusal reached after acquisition** (`D-IMPL-338`): composition, universal gate, declared product gate, tolerance, and the pre-projection blocking refusal |
| Provenance | `D-IMPL-337` — the `AdmittedChild` boundary is `src/ccf/products/composite.py::resolve_child_outcomes`; a child that did not come through the gate is neither an absence nor a governed refusal; it is `unsupported-outcome`, and it refuses the composition |
| Blocking before projection | `resolve_child_outcomes` runs before the plan; a required child absent, an invoked child refused or rejected at admission, or no resolver wired refuses **before** any child-dependent computation, with every row the walk produced (`D-IMPL-339`) |
| Child content to the plan | `src/ccf/products/composite.py::ChildContractView` — the admitted contracts, read-only, keyed by declared class — handed to a factory implementing `CompositePlanFactoryProtocol.build_with_children` |
| Child-aware `C` / `S` | `ChildAwareDebtScorerProtocol.score_with_children` — the same view, at assessment time, per request |
| Retention | `src/ccf/products/composite.py::ADMITTED_CHILD_CONTRACT_CLASS` — each admitted contract filed by content address at decision time |
| Composite replay | `src/ccf/replay/engine.py::CompositeReplayEnvironment` — `replay()` rebuilds the view from the retained bytes, held to their address, before resolving the plan; no provider call |

**Everything else this product needs is already exercised by a shipped rung:**
multi-store acquisition (cp-04-canonical), governed refusal (cp-05),
passage-level evidence (cp-13), policy-version selection by `as_of` (cp-08),
per-attribute temporal validity (cp-03).

**Nesting is not an open question.** A composite serving as another composite's
child is proven three levels deep by four shipped tests
(`tests/products/test_composite_integration.py`), and CP-14 raises no finding
about it. What CP-14's record carries is exactly **five** child rows; any
grandchildren are reachable only through each child's own record.

### 0.6 What changed since the 2026-09-13 draft

Fourteen sentences in the prior draft were measured **false** and are corrected
in place; three gates were unfalsifiable and are replaced or repaired; seven
gates are added for the shipped composition surface; and §0.0 records a missing SDK
connection without narrowing the requirement. The full ledger is §F.2. **One prior correction is itself retracted:**
an intermediate measurement claimed `194 of 194` should read `209`. It should
not. **194 is the roster scope** (the 20 obligors' 24 facility documents → 40
covenant definitions → 194 cross-reference edges); 209 is the scope of *all 22
borrowers* in `ccf_v2.facility`. The draft was right and the correction was
wrong; both scopes are now stated explicitly so the ambiguity cannot recur.

### 0.7 The post-338/339 reconciliation — what changed, and only that

Re-measured on `main` at `c635037f`. Sections touched: §0.0 (the connection is
closed), §0.5 (the merged mechanisms and what this product now codes), §B.5
(downstream refusal rows), §D.4 (replay is mechanism; `CP14-F-09` fixed; a
blocking refusal records no execution), §D.5–§D.6 (`CMC-G17`'s boundary,
`CMC-G22` on every exit, `CMC-G28`/`G29` runnable), §E.2.1 (`C`/`S` per request
from the admitted contracts), §F.2 (`CP14-F-09` FIXED; the connection closed;
`F-10`–`F-13` still OPEN), §H (two ruling items resolved; item 2 remains — since RULED, §0.8). No
estate figure changed. No gate was removed. Nothing else was rewritten.

### 0.8 Gate-1 ruling, Gate-2 baseline, and the Item-attribution ruling

**Gate 1 APPROVED — Dave, 2026-09-14.** **Gate 2 is GO** on branch
`cp-14-gate-2` from `main` at **`c635037f`**.

**Shipped dependencies this product consumes as the platform contract:**
`D-IMPL-338` (child-resolution evidence on every refusal after acquisition —
`D-GATE-338`, `4c77cc60`) and `D-IMPL-339` (acquire once; the admitted child
contracts reach the parent's computation — `D-GATE-339`, `c635037f`). Neither
is pending; both are on `main`. `CMC-G28` and `CMC-G29` are **executable**
against the real product path and are held to it at this Gate.

**Item attribution — RULED (no new decision id).** The estate's derived
`section` label is **ingestion metadata**. It does **not** authorize an
*"Item 7"* / *"Item 1A"* / *"verified MD&A section"* source claim. Allowed:
`section_label = "mdna"`, or *"classified during ingestion as mdna"*. Not
allowed from that label alone: *"Item 7"*, *"SEC Item 7"*, *"verified MD&A
section"*. **No gate may silently strengthen the provenance claim.**

### 0.9 Gate 2 — measured blocker, HOLD on `D-IMPL-340`

**Nothing of the first slice was written.** Before the Control Plane artifacts,
the five prerequisite children were read as they are shipped and one of them
was **run and offered to the shipped composite admission** under a CP-14
tenant. It was refused at the gate's first check — `tenant-mismatch` — and the
same child was admitted once the gate's tenant was set to the child's own
(`CP14-F-16`). Five children, five tenants, one gate; and none of the three
skill transports can carry a question to a producer outside this fabric
(`CP14-F-17`). That is a missing SDK door or a ruling, not an estate
limitation, so per the Gate-2 instruction this product **stopped**: the
decision is recorded as **`D-IMPL-340` (OPEN)** with three readings and a
recommendation, and no example-local workaround was attempted.

Corrected in the same revision: §B.7's requirement rows (`CP14-F-18`). Also
recorded for the ruling: cp-05's pinned instant and withheld tolerance
(`CP14-F-19`), the two children that do not take the obligor anchor
(`CP14-F-20`), the exits that raise rather than refuse (`CP14-F-21`), and
the fact that cp-03 — the spread child — does not serve on the current SDK at
all, so the Gate-1 readiness claim *"all five reach a `ServedProduct`"* was
read off the trees, not run (`CP14-F-22`). A completeness pass over the
feasibility readings added three more: the composite's request never reaches
the child mapping (`CP14-F-23`, folded into `D-IMPL-340`), §D.3 scenario 3 is
unreachable while every slot is required (`CP14-F-24`), and `as_of` and the
children's instant are two clocks this spec must keep apart (`CP14-F-25`).

**Rulings (Dave, 2026-09-14).** The stop is accepted; Gate 2 is HOLD.
`D-IMPL-340` is ruled **direction B** and proceeds as design only, on its own
SDK branch (`docs/D-IMPL-340-DESIGN.md`). `CP14-F-20` is resolved by an
explicit `facility_id` in the request. `CP14-F-22` is a blocking prerequisite,
measured real. `CP14-F-19` stays an estate limitation, untuned. `CP14-F-21` is
a separate finding with its population measured. **Gate 2 resumes only
after:** `D-IMPL-340` is resolved and merged; the required spread product
actually serves; the explicit facility request is reflected in this contract;
and any `CP14-F-21` behavior that prevents a required child from serving has
been handled. No `ccf_config.yaml`, Control Plane artifact, resolver, scorer,
factory or `run.py` before then, and no example-local workaround.

---

## A · Decision frame

**Decision & trigger.** A credit analyst is drafting a memo for committee —
a new facility, an annual review, an amendment, or a workout. The memo draws
on five systems that do not talk to each other: the obligor's filed
financials, its corporate family, the bank's total exposure to that family,
what secures it, and what the covenants actually require.

**Consuming principal.** One role at this tier: the credit analyst assembling
the packet. The *"same memo, three products"* treatment — analyst, credit
officer, examiner — is Tier 5 and belongs to `mnpi-wall-enforcement` and
`ib-opportunity-synthesis`.

**Anchor.** `lei`, the obligor.

### A.1 Counterfactual — `Context Starved`, then something worse

The familiar failure is an analyst reconstructing context by hand across five
systems. Whatever they miss is simply absent from the memo, and nothing marks
the absence.

The failure this rung is actually about is what happens when an **agent** does
that job well. It produces a fluent memo in which the weakest claim reads
exactly like the strongest. A covenant whose definition could not be resolved,
a peer benchmark computed from **1** comparable rather than **594**, a section
with no evidence at all — none of these announce themselves in prose. Fluency
is not calibrated to evidence, and nothing in a well-written paragraph reveals
how thin the file under it was.

**Acceptance test, as a procedure.** Take the two obligors in §C.1 with **no
credit facility on the estate** — **CION Investment Corp**
(`549300XN70JLF94XKX80`) and **B&G Foods** (`549300TRW1LZMDJZAQ78`). Three of
the five required children — exposure, collateral, covenants — are invoked
against an obligor for which their sources hold nothing. Request the product
for each.

**Each of those three children may serve an absence-reporting determination
*or* refuse, and both are correct.** That is the child's contract's answer at
its own tolerance, not this product's to assume — `cp-05` in particular is the
ladder's first governed refusal. **Which happens is an observation this build
makes.** The test accepts either and rejects only silence:

- **Pass (child served absence):** the child is admitted normally, its own
  (weak) completeness factor enters the parent's per-factor minimum, the
  payload names each unevaluable section, and — where the composed aggregate
  exceeds tolerance — the product **refuses** rather than serving a memo whose
  gaps are invisible.
- **Pass (child refused):** the composite **refuses**, naming which required
  child refused and carrying that child's refusal unflattened.
- **Fail:** a served payload in which the absent sections are simply not
  present, and a reader cannot tell whether the section was omitted because
  there was nothing to say or because nothing was looked at.
- **Fail, and this one is worse:** a refused child wrapped as a served empty
  product so the composite can proceed.

**The fourth case is now impossible on the shipped SDK, and that is worth
stating rather than merely asserting.** `compose_children`'s refusal branch
calls `first(outcome)` with **no** `requirement.required` test, under the
comment *"a child that was INVOKED and refused, or produced and rejected,
refuses the composite — even for an optional slot. Optional means optional
ABSENCE, not optional governance… wrapping one as an empty served product is
forbidden."* `CMC-G18` asserts this example actually reaches that path.

**A required slot does not imply positive data.** The distinction the shipped
surface draws is between a child that *was never invoked* (no in-force grant
produces its class) and a child that *answered*. A child that answers
*"nothing here"* is a served determination: it is admitted, it carries its own
debt assessment, and its completeness factor is what a missing leg costs. Only
the never-invoked case is an absence, and **a required requirement has no
declared-absent case at all** — `ChildRequirement` refuses an
`absence_treatment` on a required slot, because such a treatment could never
fire. All five of CP-14's slots are required, so CP-14 declares no absence
treatment for any of them.

**A guard written `sic IS NULL` will not fire on CION.** Its `sic` is the
**empty string**, not `NULL` — measured: `sic IS NULL` is `False`, `sic = ''`
is `True`, `length(sic)` is `0`. The acceptance guard must be
`coalesce(sic,'') = ''`. This is `CMC-G24`.

**One correction to the frame's own arithmetic.** CION is *not* the
highest-debt obligor on the stored table: **Container Store Group is, at
0.4875**, with CION second at 0.4309 and Agilysys third at 0.4201. CION is the
*most completely* starved — the only obligor that is zero on all five legs —
which is a different and more useful property, and the one the cascade test
rests on.

### A.2 The second failure, which the article does not name

The article's counterfactual assumes the debt measurement is right and the
narrative hides it. This estate makes the prior failure visible: **the debt
measurement itself can be stale, and a stale debt measurement fails closed.**

A refusal is normally the safe direction. It is not safe when it is wrong: an
analyst who is told *"11 of your 20 obligors cannot be memo'd"* by a product
citing evidence gaps that were repaired three weeks ago will stop believing
the control, and a control nobody believes is worse than no control.
**Conservative bias under elevated `D_c` is only defensible if `D_c` is
measured now.**

---

## B · Contract

### B.1 The nine elements

| Element | Value |
| --- | --- |
| **Schema** | `credit_memo_context` — `MemoSection[]`, each carrying `EvidenceRef[]` (passage-anchored) or a `DebtEntry`; plus `PeerBenchmark[]`, `CovenantDefinitionRef[]`, `RelationshipSummary`, and a first-class `context_debt` block with per-component decomposition. Machine-readable artifact at `artifacts/expected.yaml` (Gate 2). |
| **Freshness SLA** | Per signal class, §E.1. Filed narrative: immutable. Peer frames: quarterly, and a full period behind (§C.4 TRAP 6). Observation signals: `ccf_v2.signal_event`. Policy envelope: on change. |
| **TTL** | **12 hours · `ttl_anchor: from_decision`**, and **floored by the stalest admitted child**. From the decision instant, not from source freshness: a memo packet is decision-scoped. Stated against §B.4's five clocks. |
| **Policy Binding** | `ex:credit-memo-policy-v1` / `-v2`, selected by `as_of` (§B.3). Carries `creditLimitEnvelopeUsd`, `debtToleranceDefault`, `regOInsiderThresholdUsd`, `ecoaReasoningPathRestricted`. Classification **confidential** (§B.6). |
| **Lineage** | `operators_invoked[]` — **this product's OWN operators only** (§D.1) — and the served lineage is the **union** of that with every admitted child's. Plus `graph_snapshot_at` (the **earliest** constituent's, §B.4), `policy_version`, `projection_plan_id`, passage anchors on every text-borne claim, `context_debt` **computed this request**, `payload_hash`, and **five `ChildResolution` rows**. `model_record`: **not applicable — Mode 1.** |
| **Semantic Version** | `v1.0.0`. No prior version; no migration window. Change classes per Standard §14. |
| **Discovery** | `credit-risk.credit-memo.v1` |
| **Addressability** | `/context-products/credit-risk/credit-memo/{lei}` |
| **Assembly Mode** | **1 — pure algorithmic.** §0.4. |

**The lineage row carries the load-bearing correction.** Gate 2 for a composite
is **two comparisons, in order, both strict**: first the parent's *declared*
operator set must equal the parent's *own engine-executed* set; only then is
the operand widened to `parent_executed ∪ admitted_child_operators` and
compared to the composite's union lineage. The resolver's own refusal text
states the rule — *"a composite's admitted children widen what the composition
resolved, never what the parent itself declared, so this half stays strict in
both directions."* **Therefore CP-14's registered class must declare ONLY its
own operators.** Naming a child's operator in the declaration makes this
product permanently unservable. `CMC-G02` is written against exactly that.

### B.2 Request parameter surface

| Parameter | Type | Moves | Default | Notes |
| --- | --- | --- | --- | --- |
| `lei` | string(20), required | **E** anchor | — | One of the 20 in §C.1 |
| `intent` | enum, required | **P** envelope | — | Intent registry |
| `memo_type` | enum `new-facility` \| `annual-review` \| `amendment` \| `workout` | payload shape | `annual-review` | Selects the section template, §C.1 |
| `sections` | list | payload shape | per `memo_type` | Subset of the template's sections |
| `peer_basis` | enum `sic` \| `sic-and-size` \| `named` | peer set | `sic` | **`sic-and-size` and `named` are declared-but-inert** — see below |
| `as_of` | date | **T** + **P** | today | Selects the policy version **and therefore the default tolerance** |
| `debt_tolerance` | float 0–1 | fail-closed bound | **from policy** | Explicit value overrides the policy default |
| `corpus_scope` | enum `filed` \| `filed-and-internal` | **P** envelope | `filed` | `filed-and-internal` admits the 40 internal memoranda |

**`peer_basis` is declared-but-inert except for `sic`.** `ccf_v2.peer_cohort`
is keyed on `(sic, tag, frame)` and carries no size band and no named-peer
list. Per Standard §2.4 the two unsupported values are declared and **fail
explicitly** with `not_supported_at_tier` rather than silently falling back to
`sic`. A parameter that appears to work and does not is worse than an absent
one.

**`debt_tolerance` defaults from the policy envelope, not from a constant.**
`as_of` selects the policy version, the policy version carries
`debtToleranceDefault`, and the same obligor with the same evidence serves
under one policy and refuses under the other (§D.3 scenario 2).

**The boundary convention is `<=` serves.** Measured against the stored table,
**no obligor sits exactly on either boundary**, so `<` and `<=` currently agree
— but the spec states it because the margin is thin: **Thermon Group Holdings
at 0.3003 is 0.0003 above 0.30**, and is the entire difference between nine
obligors serving and ten. Thermon is the named boundary specimen.

**`as_of` before 2024-01-01 has no governing policy and MUST refuse.** Measured:
the policy-selection query returns **0 rows** for `as_of = 2023-12-31`. A
product that falls back to a default tolerance there would be inventing a
governing value. Authority `technical`; `CMC-G25`.

**`as_of` does not move the window the children's evidence is judged in.**
Child admission is judged at the **runtime clock** (`admitted_at`), read once
per composition by the resolver. This is a real constraint, not a wrinkle: a
back-dated `as_of` selects an older policy but cannot make a child's evidence
age acceptable.

### B.3 The policy envelope is measured, and it is two versions

Measured in `fibo-v2`, 2026-09-14, and independently re-measured on a second
model:

| Policy version | `validFrom` | `validTo` | `debtToleranceDefault` | `creditLimitEnvelopeUsd` | `regOInsiderThresholdUsd` |
| --- | --- | --- | --- | --- | --- |
| `ex:credit-memo-policy-v1` | 2024-01-01 | 2025-06-30 | **0.3** | 750000000 | 500000 |
| `ex:credit-memo-policy-v2` | 2025-07-01 | *(absent)* | **0.25** | 600000000 | 250000 |

`v1` carries `ex:supersededBy → v2`; `v2` is terminal. Both carry
`ex:ecoaReasoningPathRestricted`. Both carry `ex:provenance "synthetic —
internal"` — these are engineered policy nodes, and any lineage surface must
label them as such rather than as sourced reference data.

**Three binding traps, all measured, all load-bearing:**

1. **There are 17 `ex:PolicyVersion` nodes, not 2.** The credit-memo pair is
   two of seventeen. **Bind on `ex:debtToleranceDefault`**, which — verified
   unscoped over the whole ledger — is carried by exactly those two nodes and
   nothing else. So are the other three envelope predicates.
2. **A naming decoy sits beside them.** `ex:credit-policy-v1.0` and
   `ex:credit-policy-v1.1` are also `ex:PolicyVersion`, are also a superseding
   pair, and cross a boundary **eight days** from the credit-memo boundary
   (`validTo 2025-06-23` / `validFrom 2025-06-24`). They carry **none** of the
   four envelope predicates, and `v1.0` has no `ex:supersededBy`, so the pair
   is not even linked. A spec binding *"the credit policy"* by name selects the
   wrong lane and gets no thresholds.
3. **Every value is a bare untyped literal.** No `xsd:date`, no `xsd:decimal`,
   no `xsd:boolean`. Dates compare **string-lexicographically**; numbers need a
   cast; `ecoaReasoningPathRestricted` is the four-character string `"true"`,
   and a boolean binding matches **zero** rows. `v2`'s open `validTo` is
   **predicate absence**, requiring `OPTIONAL` + `!BOUND` — not an empty string
   and not a sentinel.

**On the ECOA flag — declaration is not a door.** `ecoaReasoningPathRestricted`
is a bare string in the graph. Reading it and recording it in `policy_version`
would satisfy every test about the declaration while changing nothing the
product does. Per `D-IMPL-324`, a door never opened passes every test about its
declaration. So this spec commits to an **observable** effect or to none:

> **RULED (§0.4 item 6): recorded and explicitly inert.** The estate carries no
> protected-class attribute and no prohibited-basis feature, so there is no
> compositional path for an ECOA restriction to *close* here. This spec
> declares the flag as **recorded in lineage and inert in this product**, and
> says so in the payload rather than implying an enforcement that does not
> occur. The alternative — inventing a protected-class field to restrict —
> would be manufacturing a demonstration, which §9 forbids.

### B.4 Temporal semantics, enumerated

**Five clocks, kept apart.** The prior draft named four; composition adds one.

1. **`as_of`** — the decision instant. Selects the policy version; anchors the
   TTL; is the reference point for every staleness computation.
2. **`period_end` / `filed_date`** — what period a financial fact covers, and
   when it was filed. Peers are matched on **`period_end`**. These two are
   **different clocks and they reorder obligors**: measured over the 20,
   latest-`filed_date` age spans 33–684 days while the estate's own staleness
   curve runs on `period_end`, where the same obligors span 49–693 days.
3. **`graph_snapshot_at`** — the Fluree `t` at which the definition chain and
   the policy envelope were read. For a composite this is the **earliest** of
   the parent's and every admitted child's — a design choice in
   `compose_lineage`, not a derivation, and stated here because it is.
4. **`as_of` on estate tables** — when the *estate* last measured something.
   This is the clock §0.1 is about: `memo_context_debt.as_of` is
   **2026-08-22** and is not any of the others. The table carries **no other
   date column at all** — no `created_at`, no `computed_at` — so a reader
   cannot distinguish when a row was written from when its inputs were
   measured.
5. **`admitted_at`** — the runtime clock at which each child's admission is
   judged. Read once per composition. **`as_of` cannot move it** (§B.2).

**Clock 4 is never allowed to stand in for clock 1.** A debt figure carrying
clock 4 is a historical measurement, and this product does not serve it as a
current one.

### B.5 Context Debt and freshness

Debt is **computed this request** from primary evidence. The model, the F/C/S
definitions and the per-component behavior are §E.2 and §E.3. The
contract-level commitments:

- `context_debt` is a **first-class payload block**, never a log line.
- Debt is decomposed **per section and per claim**, not only per product. A
  memo with eight sections where one input is missing returns seven evaluated
  sections and one marked `NOT_EVALUABLE` — not a product-level failure, and
  never a silently-omitted eighth.
- **Inheritance is the per-factor minimum over strength factors**, never
  `max(child D_c)` (§E.2). A composed product is never fresher, never more
  complete and never more consistent than its weakest input on that axis.
- **Fail-closed happens at the delivery boundary, not at a validation gate.**
  `src/ccf/products/gates.py::refuse_over_tolerance` runs *after* the three
  gates have admitted the product; its own docstring says *"this is NOT a
  gate… a gate decides whether a product may exist; this decides whether an
  existing product is delivered."* The spec states it this way because calling
  it a gate would misdescribe where the control sits.
- **A refusal's `observed` is `None` when no assessment was produced** — a
  positive statement, never zero.
- **Every refusal reached after acquisition carries the five child rows**
  (`D-IMPL-338`) — including the tolerance refusal that is this product's
  headline behavior, and the pre-projection blocking refusal. Before
  acquisition a refusal carries none: nothing was considered.
- **What a caller actually sees on a child-admission refusal is narrower than
  what is recorded.** At the default `minimal` disclosure level the permitted
  field set for `composite-child-refusal` is `{product_class}` alone: the
  reason token and both content addresses are recorded in replay and
  **withheld from the caller**. Any acceptance criterion written against the
  caller's view must respect that floor (`CMC-G26`).

### B.6 Classification, barriers, residency

| Field | Value |
| --- | --- |
| Data classification | **confidential** — the 40 internal memoranda are `internal-confidential`; everything else is public or internal |
| Information barrier | **none** at this tier. MNPI-bearing interactions exist in `ccf_v2.interaction` and are **out of scope**, carried by `mnpi-wall-enforcement` (rung 17) |
| Residency | `US` on every memorandum measured; no cross-border constraint fires on this population |
| Cross-border serving | Not exercised at this tier |

**The suppression rule holds.** Where `corpus_scope=filed` excludes the
internal memoranda, the payload carries **no count, marker or placeholder**
indicating that anything was withheld. Excluded content is never materialized.
**And the gate needs its positive control**: under `filed-and-internal` the
memoranda must actually appear, or the rule passes vacuously on a product that
never reads them (`CMC-G11`). Note the population: **18 of 20** obligors have
at least one memorandum; **B&G Foods and CION have none**, so neither can carry
this gate.

### B.7 The five children, as declared requirements

**Prerequisites** (build order): `obligor-financial-spread` ·
`corporate-family-tree` · `credit-exposure-rollup` ·
`collateral-and-setoff-coverage` · `covenant-cross-reference`.

Declared in the `ProductClassDeclaration` artifact's `requires:` as five
`src/ccf/products/contract.py::ChildRequirement` rows. Each names a product
**class** by `schema_name` — never a skill, never an instance; which granted
skill satisfies it is resolved at assembly from the composing agent's in-force
grants.

| # | `product_class` | `required` | `compatible_from` | `absence_treatment` |
| --- | --- | --- | --- | --- |
| 1 | `credit-risk.spread` (cp-03) | `true` | `1.0.0` | **none — refused on a required slot** |
| 2 | `reference.corporate-family` (cp-04-canonical) | `true` | `2.0.0` | none |
| 3 | `credit-risk.exposure-rollup` (cp-05) | `true` | `1.0.0` | none |
| 4 | `credit-risk.collateral-coverage` (cp-06) | `true` | `1.0.0` | none |
| 5 | `credit-risk.covenant-cross-reference` (cp-13) | `true` | `1.0.0` | none |

*Reconciled at Gate 2 (2026-09-14) by reading each child's `ccf_config.yaml`
`product_class.schema_name` / `schema_version`. **The Gate-1 revision of this
table was wrong on three of five rows** — it named
`credit-risk.obligor-financial-spread`, `credit-risk.corporate-family-tree` @
`1.0.0` and `credit-risk.credit-exposure-rollup`, classes no child registers,
while claiming they were "the classes as the shipped trees declare them
today". The shipped gate measured it: with the tenant matched, the row-2
requirement as Gate 1 wrote it refused `class-mismatch` (`CP14-F-18`). The
lane on row 2 is `2.0.0` because `ChildRequirement.accepts` is same-major.*

Four properties of this table are the SDK's, not this spec's:

- **`required` has no default.** *"An author who does not say has not said
  `True`, and silence is not a declaration."* All five are stated explicitly.
- **A required requirement may not carry an `absence_treatment`** — the model
  validator refuses one, because a treatment for a case that cannot arise is a
  declaration that can never fire.
- **`compatible_from` is a floor, not a range.** The rule is caret-shaped and
  stated rather than parsed: same **major** lane, at or above, by semantic
  version precedence. There is no range grammar in the SDK and this spec does
  not invent one.
- **No duplicate `product_class`**, enforced at registration *and* again at
  execution.

**Exactly one in-force grant per class.** Zero granted producers of a required
class refuses the composite; **two or more raises**, with no tie-breaker by
ruling. Producer interchangeability, if demonstrated, is demonstrated by
**substitution** — grant A, serve; revoke A, grant B, serve — never by granting
both.

**Consumers:** the memo-drafting agent (outside the fabric);
`large-exposure-rwa-concentration` (rung 21) composes over this product.

**Deliberately out of scope**, with the product that carries each:

| Not here | Carried by |
| --- | --- |
| The memo narrative itself | The consuming agent — this is the Mode 1 boundary |
| Three role-shaped renderings of one memo | `mnpi-wall-enforcement`, `ib-opportunity-synthesis` (rungs 17, 18) |
| MNPI-bearing interaction content | `mnpi-wall-enforcement` (rung 17) |
| Beneficial-ownership walk to natural persons | `kyc-refresh-beneficial-ownership` (rung 15) |
| Peer sets by size band or named list | Not built — see `peer_basis` in §B.2 |

### B.8 What this product owns, and what it must not rebuild

**The boundary is ownership of evidence, not convenience of access.**

**CP-14 may acquire directly** the evidence it genuinely owns — material no
child product is responsible for:

| Owned by CP-14 | Source |
| --- | --- |
| Memo section templates by `memo_type` | `ccf_v2.memo_section_template` |
| Narrative passages and their anchors, for section evidence | `fibo_v2.passage`, `fibo_v2.document` |
| Peer cohorts and benchmarks | `ccf_v2.peer_cohort`, `peer_fact`, `peer_entity` |
| Relationship history | `ccf_v2.interaction` (through `interaction_id`) |
| Observation signals, for `F` | `ccf_v2.signal_event` |
| Adverse-media coverage, for `C` | `ccf_v2.gdelt_mention` |
| The credit-memo policy envelope | `fibo-v2` `ex:PolicyVersion` |
| Internal memoranda, under `corpus_scope` | `fibo_v2.memorandum` |

**CP-14 must NOT independently reconstruct** anything a required child already
supplies:

| Supplied by a child — CP-14 does not rebuild it | Child |
| --- | --- |
| Obligor financial spread | `obligor-financial-spread` |
| Corporate family / ownership structure | `corporate-family-tree` |
| Total exposure, cross-defaults, guarantee paths | `credit-exposure-rollup` |
| Collateral, haircuts, set-off, lien priority | `collateral-and-setoff-coverage` |
| Covenant definitions, cross-references, citations | `covenant-cross-reference` |

**The rule, stated so it can be checked.** The atomic providers retain
responsibility for assembling and serving those products. **CP-14 consumes
their contracts; it does not import their assemblers, reach their databases for
that material, or re-derive it from the estate.** A query in this product's
plan against `ccf_v2.facility`, `collateral_pledge`,
`corporate_ownership_record` or `financial_fact` **for child-owned material**
is the defect this boundary exists to prevent — it would duplicate the work,
bypass the child's governance, and produce a figure the child's debt assessment
does not cover.

**Why `financial_fact` still appears in §C.1.** It is read for **two
parent-owned purposes only**: the `period_end` clock behind the staleness
comparison in §C.4 TRAP 1, and the peer-matching period. The obligor's
*financial spread* — the figures a memo prints — is the child's.
`CMC-G27` checks the distinction.

**Acquiring a child's material directly is not an acceptable workaround for
§0.0.** It would make the product appear complete while the connection the
requirement depends on stayed missing, and it would put five products' worth of
assembly logic inside an example. The gap stays visible until it is closed.

---

## C · Data catalog

### C.1 What the estate holds, measured 2026-09-14

Estate: PostgreSQL `ccf_v2` (**116** base tables + **2** views = 118 relations)
· MongoDB `fibo_v2` (**6** collections) · Fluree `fibo-v2` (**95** typed
classes), all on `192.168.4.76`. Every figure below was measured twice, on two
models, blind to each other.

**Scope every denominator to the roster.** The 20 obligors are a minority slice
of the signal tables: `financial_fact` and `interaction` each span **50**
distinct LEIs, `gdelt_mention` **30**, `facility` **22** borrowers. A count
taken at table level overstates obligor coverage by 2.6–2.8×.

| Element | Provenance | Class | Store | `G` | Measured |
| --- | --- | --- | --- | --- | --- |
| Memo section templates | synthetic — internal | internal | `ccf_v2.memo_section_template` | schema | **31** rows · 4 memo types: `new-facility` 9, `annual-review` 8, `amendment` 7, `workout` 7 |
| Obligor roster | public | public | `ccf_v2.memo_context_debt` ⋈ `legal_entity` | `E` | **20** obligors, all resolving to a named entity |
| Debt component weights | synthetic — internal | internal | `ccf_v2.debt_weight` | `P` | **4** rows summing to **1.00**: anchor 0.3, peer 0.25, staleness 0.15, inherited 0.3 |
| Per-obligor debt (**diagnostic comparison, never the governing source**) | derived | internal | `ccf_v2.memo_context_debt` | — | **20** rows, `as_of` **2026-08-22**, the table's **only** date column. Carries `definition_refs_unverified` **181** and `definition_refs_verified` **90** — see §C.4 TRAP 1 |
| Peer cohorts | public | public | `ccf_v2.peer_cohort` | `E` | **324** rows = **18** SICs × **6** tags × **3** frames-per-tag. Columns are `expected_active` (3…612) and `sic_cohort_total` (32…1903); **`thinness` is stored**, `= 1 − actual/expected_active`. `actual` ranges **1 … 594** |
| Peer entities / facts | public | public | `ccf_v2.peer_entity`, `peer_fact` | `E` | **1,678** / **22,494**. **`peer_fact.filed_date` is NULL on all 22,494 rows** — see TRAP 7 |
| Obligor financial facts | public | public | `ccf_v2.financial_fact` | `E` | **15,055** rows over 50 LEIs; **20 of 20** obligors covered (182–395 each, 5,804 roster rows) |
| **Observation signals** | mixed | internal | `ccf_v2.signal_event` | `E`, `T` | **1,603** rows over 50 LEIs; **20 of 20** obligors covered (658 roster rows); `observed_at` 2024-08-19…2026-08-19; **20 distinct per-obligor ages, 28…593 days** — the estate's only fully discriminating freshness axis |
| Filed narrative text | public | public | `fibo_v2.document` | `L` | **145** documents under a narrative `form` — 10-K **45** (24 LEIs), 10-Q **30** (23), 8-K **70** (29). **This set already CONTAINS the EX-10 exhibits** — see TRAP 8 |
| …of which filing-body sections | public | public | `fibo_v2.document`, `source='SEC EDGAR Archives'` | `L` | **77** docs carrying an explicit `section` field: `mdna` 38, `risk_factors` 20, `exhibit_99` 19. Cover exactly the **20** roster LEIs |
| …of which credit-agreement exhibits | public | public | `fibo_v2.document`, `source='SEC EDGAR EX-10 exhibit'` | `L` | **68** (62 untagged + 6 `doc_type='credit_agreement_wave18'`); **24** distinct agreements reachable from the roster's facilities, all 24 resolving |
| Passages + embeddings | derived | public | `fibo_v2.passage` | `L` | **37,865** total, **21,148** over the 145. **23,576 carry an actual 1,536-dim vector**; 14,205 carry explicit `null`; 84 lack the key. Within the narrative subset: **21,136 vectors, 0 nulls, 12 absent** |
| Definition chain | public | public | `fibo-v2` `ex:CovenantDefinition`, `ex:DefinedTerm` | `L`, `E` | **49** definitions, **158** defined terms, **216** `crossReferences` assertions (215 from covdefs, 1 from the orphan `ex:DEBT-0001`) |
| Passage anchors | public | public | `fibo-v2` `ex:PassageAnchor` | `L` | **44** nodes; **44** carry `ex:anchorVerified` and **44** carry `ex:passageSha256` |
| Internal credit memoranda | synthetic — internal | **confidential** | `fibo_v2.memorandum` | `L` | **40** docs; `borrower_lei` / `facility_id` / `text_sha256` on **40/40**; **embedding on only 22/40**. 21 distinct `borrower_lei` covering **18 of 20** obligors |
| Research notes | synthetic — internal | internal | `fibo_v2.research_note` | `L` | **42** docs; `embargo_until` non-null on **9**, and **all 9 have lapsed** as of 2026-09-14 |
| Adverse media | public | public | `ccf_v2.gdelt_mention` | `E`, `T` | **951** rows over 30 LEIs; **11 of 20** obligors have ≥1, and two of them hold 337 of the 400 roster rows. A `down_weight_factor` column exists but **every one of its 49 rows belongs to a non-roster LEI** — inert here |
| Relationship history | synthetic — internal | internal | `ccf_v2.interaction`, `interaction_participant` | `E` | **2,050** / **8,032**; **20 of 20** obligors covered (35–41 each). **`interaction_participant` has no LEI column** — see §C.3 |
| Credit-memo policy envelope | synthetic — internal | internal | `fibo-v2` `ex:PolicyVersion` | `P`, `T` | **2** versions of **17** in the ledger, §B.3 |
| Facilities (exposure leg) | mixed | internal | `ccf_v2.facility` | `E` | **48** over the roster of a table holding **60** over **22** borrowers; **18 of 20** obligors have ≥1 |
| Ownership (family leg) | public | public | `ccf_v2.corporate_ownership_record` | `R` | 280 rows. **10 of 20** obligors appear, **always as parent, never as child**. Records double-count: 140 `IS_DIRECTLY_CONSOLIDATED_BY` + 140 `IS_ULTIMATELY_CONSOLIDATED_BY` over 184 distinct pairs |
| Collateral (security leg) | mixed | internal | `ccf_v2.collateral_pledge` ⋈ `facility` | `R` | 95 rows; **15 of 20** obligors have ≥1 pledge. The 5 without: Agilysys, B&G Foods, CION, Paychex, Pebblebrook |

**The acceptance population, exact.** `fac` = facilities; `own` = ownership
records as parent; `pledge` = pledges via facility; `gdelt` = adverse-media
mentions.

| LEI | Name | sic | fac | own | pledge | gdelt | stored `D_c` |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2549001IGRCG4F0RLD36 | BGC Group, Inc. | 6200 | 1 | 79 | 1 | 4 | 0.3652 |
| 5299001XWB5V3B5IPN93 | AGILYSYS INC | 7373 | 1 | 4 | 0 | 0 | 0.4201 |
| 529900E95812SYWMCE44 | AVIS BUDGET GROUP, INC. | 7510 | 4 | 0 | 9 | 28 | 0.2589 |
| 529900K900DW6SUBM174 | PAYCHEX INC | 8700 | 2 | 0 | 0 | 7 | 0.2639 |
| 529900L7KB2N9KXCDI76 | Container Store Group, Inc. | 5700 | 2 | 4 | 2 | 1 | **0.4875** |
| 529900VKCYZW8GZ4WW58 | Sabre Corp | 7370 | 1 | 6 | 1 | 0 | 0.3574 |
| 529900VN48L8QCMVPV36 | Viskase Holdings, Inc. | 2836 | 2 | 0 | 3 | 0 | 0.3512 |
| 529900ZNZBBLDE77MZ38 | Thermon Group Holdings, Inc. | 3620 | 3 | 0 | 3 | 0 | **0.3003** |
| 54930022CZO1N2UGVW07 | Super Micro Computer, Inc. | 3571 | 1 | 2 | 1 | 137 | 0.0765 |
| 5493002H8U24DJXQ4886 | RB GLOBAL INC. | 7389 | 2 | 9 | 6 | 0 | 0.2335 |
| 5493003J7157VP25NL57 | City Office REIT, Inc. | 6798 | 2 | 2 | 4 | 0 | 0.4143 |
| 5493004Q1NNH6JXCSI52 | Pebblebrook Hotel Trust | 6798 | 2 | 0 | 0 | 0 | 0.4182 |
| 54930096DB9LCLPN7H13 | XPO, Inc. | 4700 | 3 | 0 | 8 | 4 | 0.3417 |
| 549300EQD0ZXRSMG3549 | TransDigm Group INC | 3728 | 4 | 0 | 8 | 1 | 0.1404 |
| 549300KTTIRAOGXCRV69 | Vertiv Holdings Co | 3679 | 6 | 3 | 6 | 0 | 0.2840 |
| 549300TMDIT8WREDOF45 | MASTEC INC | 1623 | 1 | 0 | 1 | 3 | 0.1892 |
| 549300TRW1LZMDJZAQ78 | B&G Foods, Inc. | 2000 | **0** | 0 | **0** | 3 | 0.1705 |
| 549300WRECW11X94UB57 | EXTREME NETWORKS INC | 3576 | 3 | 2 | 6 | 200 | 0.3467 |
| 549300XN70JLF94XKX80 | CION Investment Corp | **`''`** | **0** | **0** | **0** | **0** | 0.4309 |
| B3BS7ACMDUWISF18KY76 | Bausch Health Companies Inc. | 2834 | 8 | 6 | 16 | 12 | 0.1603 |

Totals a test may assert as relationships: `fac` non-zero **18**, `own`
non-zero **10**, `pledge` non-zero **15**, `gdelt` non-zero **11**, non-empty
`sic` **19** over **18** distinct SICs (6798 shared by City Office and
Pebblebrook). **CION is the only obligor zero on all five legs.**

### C.2 Provenance, and what is public

Two thirds public (SEC EDGAR filings and XBRL `frames`, GDELT), one third
`synthetic — internal` — the bank-side material no public source can supply:
internal credit memoranda, relationship history, section templates, debt
weights, and the policy envelope. One element is `synthetic — engineered`, and
it is the subject of TRAP 3.

### C.3 Correlation key

**`LEI` throughout**, with two documented exceptions:

- **`interaction_participant` carries no LEI.** Its columns are
  `(interaction_id, party_kind, party_key, provenance)`; `party_key` is
  CIK-shaped for `person` (4,032 rows) and `BKRnnn` for `banker` (4,000). A
  `party_key = lei` join returns **zero** and reads as absence rather than as a
  wrong join. The obligor is reachable only through
  `interaction_id → interaction.lei`.
- **32 `passage.document_id` values resolve to `kyc_document`, not
  `document`.** A passage→document join silently drops the KYC corpus.
  Conversely 13 `document` rows have no passages, and `document.passage_count`
  sums to 37,307 against 37,865 actual passages.

**Passage anchors** as `{document_id, start_offset, end_offset}` with
`sha256`, resolved via `ex:evidencedBy` to a **named passage** — never by
re-deriving offsets, which is the rung-13 lesson.

**Agreement documents** join `ccf_v2.facility.(source_accession,
source_document)` to `ex:CovenantDefinition.ex:documentId` as
`"{accession}:{document}"`. **The roster's 48 facilities form 24 distinct join
keys and all 24 resolve.** The whole table's 60 facilities form 28 keys — and
the difference is load-bearing, see TRAP 1.

### C.4 The data traps

**TRAP 1 — the estate's Context Debt table was measured against a different
state of the estate. This is the product's subject, not an obstacle to it.**

`ccf_v2.memo_context_debt` carries 20 rows `as_of` **2026-08-22**, with
`aggregate_debt` and four components. `aggregate_debt` reproduces exactly as
the `debt_weight`-weighted sum on **20 of 20** rows (max residual 0.000045,
0.0000 at four decimals), so `debt_weight` is live control rather than
documentation.

**Three of the four components re-derive exactly. The prior draft said two.**

| Component | Re-derivable today? | Measured |
| --- | --- | --- |
| `peer_set_thinness` | **Yes, exactly** | **19 of 20** equal `avg(peer_cohort.thinness)` over the obligor's SIC to four decimals (max residual 0.0000444); all 19 have exactly 18 cohort rows. The 20th — CION — has **no SIC**, hence **0** cohort rows, and the stored value is **1.0**: the correct degenerate answer |
| `signal_staleness` | **Yes, exactly — and the curve IS publishable** | `= days(as_of − max(financial_fact.period_end)) / 730`, on **20 of 20**, max residual 0.0000397. All seven stored values hit exactly: 49d→0.0671, 53d→0.0726, 56d→0.0767, 83d→0.1137, 144d→0.1973, 326d→0.4466, 693d→0.9493. Against `filed_date` it reproduces **0 of 20** |
| `unresolved_passage_anchor` | **Yes, exactly — from the table's OWN counters** | `= unverified/(unverified+verified)`, 0/0 → 0, on **20 of 20** (max residual 0.0000429). **So the arithmetic is sound and the STALE THING IS THE PAIR OF INTEGERS**: 181 unverified + 90 verified = 271 |
| `inherited_prerequisite_debt` | **Reproduced, with a caveat** | `= 0.2·[0 facilities] + 0.2·[0 collateral pledges]` reproduces **all 20 rows with zero residual**. B&G and CION (0 facilities → 0 pledges) give 0.4; Agilysys, Paychex, Pebblebrook (facilities, 0 pledges) give 0.2; the other 15 give 0 |

**Two sentences from the prior draft are retracted here.** *"The exact curve is
the estate's and is not published"* — it is `days/730` on `period_end`, and the
730-day horizon is the same two-year relative default `D-IMPL-325` ruled for
cp-07. *"Nothing in the estate explains where these five numbers came from"* —
the facility and collateral-pledge tables reproduce all twenty. **The caveat on
the fourth row is stated rather than buried:** that is a three-level partition
fitted to three distinct outcomes over twenty points with co-linear predicates
(0 facilities implies 0 pledges). Zero residual on 20 of 20 defeats *"no source
exists"*; it is **not** proof of the generating job. Any test asserting it
asserts the **ordering of the three tiers**, never the constant 0.2.

**Two figures in the prior draft were attached to the wrong column.** Container
Store *"661 days"* and City Office *"288"* are `filed_date` ages; against the
driving column `period_end` they are **693** and **326**. And *"a floor of
0.0726"* is wrong — **B&G Foods stores 0.0671**. 0.0726 is the **modal** value
(11 of 20), the 53-day lag from a 2026-06-30 quarter end.

**Where the disagreement actually is.** Stored: 181 of 271 references
unverified. Current graph, **scoped to the roster's 24 facility documents**:
40 covenant definitions carrying **194** `ex:crossReferences` edges, of which
**193** resolve to a declared `ex:DefinedTerm`, **1** to a `Report`, and **0**
are unresolved; and **44 of 44** anchors carry `ex:anchorVerified`.

> **Scope matters and must be written down.** Against **all 22 borrowers** in
> `ccf_v2.facility` (28 documents, 46 covenant definitions) the same traversal
> yields **209** edges. 194 is the roster; 209 is the table. An intermediate
> measurement in this rung's own preparation reported 209 as a correction to
> 194 and was itself wrong. Both numbers are recorded so the ambiguity cannot
> recur.

**A measuring instrument to distrust, recorded because it produced that error.**
**Fluree's SPARQL `COUNT(*)` under a `GROUP BY` returns a distinct-SUBJECT
count on this ledger.** Asked for cross-references per document it returns a
tidy 19-row table summing to **46** when the true answer is 209 — a 4.5×
understatement that reads exactly like a clean result. Every graph figure in
this specification was produced by **materializing rows and counting them**,
never by a grouped aggregate. Ungrouped `COUNT(*)` is fine (216 total edges,
confirmed by materialization).

**What changed upstream, named.** The estate owner re-keyed the covenant
anchors on **2026-09-13** — 44 URIs for 44 covenants, 44 of 44 hashing
correctly. The debt table predates that change by three weeks and was never
recomputed.

**What this spec does NOT claim.** It does not claim the August table was
correct in August. Its original correctness has not been established here, and
this rung does not need it.

**The binding, and its cost.** The product **computes all four components at
request time** and **never reads `memo_context_debt` to determine the governing
debt**. Component four has no stored source, so it is computed the only honest
way: as the per-factor inheritance from the prerequisite products actually
invoked, which is what §B.5 and the shipped combinator already do.

**A separate, explicitly-labeled diagnostic comparison IS permitted** and is
required by `CMC-G05`: the product compares its computed figure against the
identified **2026-08-22 snapshot**, carrying that date and its provenance, and
records the divergence. The prohibition is on the table *governing*, never on
it being *consulted and reported*.

**If `ccf-dataprep` refreshes the table, equality may become the correct
result.** `CMC-G05` therefore asserts a **measured demonstration against a
dated snapshot**, not a permanent invariant that the two must differ. On an
upstream refresh: record the resolution, retain the historical finding as
`FIXED-upstream`, and **keep `CMC-G04`'s source-independence control active** —
that control is about where the governing number comes from and is unaffected
by whether the two agree.

**TRAP 1a — the anchor repair did not repay the evidence debt. It changed its
shape, and there is no repair path.**

A reference **resolving** is not the same as a passage being **auditable**.
Measured in `fibo-v2`, 2026-09-14, after the repair:

| Measured | Count |
| --- | ---: |
| Subjects carrying `ex:startOffset` | **262** |
| …of those, carrying `ex:endOffset` | **92** |
| **Point anchors — a start with no end** | **170** |
| Subjects carrying `ex:endOffset` with no start | **0** |
| `ex:PassageAnchor` nodes, all carrying `ex:passageSha256` | **44** |
| `ex:CovenantDefinition` nodes | **49** |
| …carrying `startOffset` **and** `endOffset` | **48** |
| …**carrying a hash of any kind** | **0** |
| Covdef spans **contained in** an anchor span in the same document | **0** |
| Covdef spans merely **overlapping** one | **0** |

Three limitations survive, and none is touched by the anchor re-keying:

- **170 point anchors.** A span with no end cannot be re-hashed and cannot be
  quoted with bounds. By class: `ex:DefinedTerm` 158, `ex:MeasurementPeriod`
  11, `ex:Covenant` 1.
- **Not one `ex:CovenantDefinition` carries a hash.** Forty-eight carry a
  quotable span and **zero** carry anything to check it against. This is
  rung 13's central finding — *48 extractable, 47 reading as genuine
  definitions, 0 auditable* — still true after the repair, because the repair
  fixed anchor **identity**, not definition **auditability**. Searched
  negative: of the ledger's **181** distinct predicates, exactly **one** has a
  local name containing `sha`/`hash`/`digest`, and it is carried by the 44
  anchors and by nothing else.
- **NEW, and it closes the obvious workaround: there is no span path to borrow
  a hash from.** Zero of the 48 covdef spans is contained in, or even overlaps,
  any anchor span in the same document — and 4 of the 20 covdef documents carry
  no anchor at all. *"Derive the hash from a nearby verified anchor"* is not
  available.

**A binding trap under the same subject.** `ex:anchorVerified` is a **bare
untyped string** `"true"`. The natural SPARQL binding `?s ex:anchorVerified
true` matches **0 of 44**; `"true"^^xsd:boolean` matches **0**; the four-
character string matches **44**. A silent false negative on the one predicate
that gates citability.

**The binding.** The `194 of 194` figure is about **cross-reference
resolution** — does the cited defined term exist. It is **not** a claim that
the underlying text is auditable, and this spec does not let the two be read as
one number. A covenant claim is emitted with a checked citation only where an
`ex:PassageAnchor` with a matching `passageSha256` backs it; a definition span
with no hash produces a `DebtEntry`, never a citation. `CMC-G09` enforces the
hash; `CMC-G16` keeps the two properties apart.

**TRAP 2 — the filings have no Item structure in their headings, and the
defect is worse than a wrong label.**

The prior draft said headings exist but name sections rather than Items. The
measurement is sharper: **the filing bodies have essentially no headings at
all.**

| Measured | Count |
| --- | ---: |
| Narrative passages | **21,148** |
| …carrying a non-empty `heading` | **2,414** |
| …of those, belonging to the **68 EX-10 exhibits** | **2,411** |
| …belonging to the **77 filing-body documents** | **3** (of 3,749 passages) |
| Headings anywhere in all 37,865 passages containing `item` | **0** |
| `Item 1A` in passage **text**, narrative-scoped | **48** ci / 44 cs |
| `Item 7` in passage **text**, narrative-scoped | **41** ci / 40 cs |

The three filing-body headings are `Section 382` (×2) and `Section 404` —
statute references, not document structure. The 15 most common headings are all
credit-agreement structure (`Section 2` ×137, `ARTICLE V` ×13), and **casing is
not normalized** (`Section 2` and `SECTION 2` are distinct values).

**A correction to the prior draft's own numbers:** `Item 1A` 51 and `Item 7` 46
are **corpus-wide** counts over all 37,865 passages, while the sentence
carrying them was scoped to the narrative 21,148. Narrative-scoped they are 48
and 41. The heading-side zeros are unconditionally true at both scopes and are
**stronger** than claimed.

**And the section identity does exist — just not in `heading`.** The 77
filing-body documents carry an explicit **`section` field on 77/77**, and a
structured `document_id` of the form `{form}-{accession}-{section}`, with
values `mdna` **38**, `risk_factors` **20**, `exhibit_99` **19**. Those 77
documents cover exactly the 20 roster LEIs.

**The binding — RULED at Gate-1 approval (§0.8).** The estate supports a
**document-level ingestion label** and nothing stronger. Memo sections bind to
evidence by **Similarity over passage embeddings within the policy-permitted
document set**; a claim cites `{document_id, offsets, sha256}`, the form type,
and — where the document carries one — `section_label` as ingestion metadata
(*"classified during ingestion as mdna"*). It never says *"Item 7"*, *"SEC
Item 7"* or *"verified MD&A section"* on the strength of that label, and no
gate may strengthen the claim silently.

**TRAP 3 — the engineered cascade case is orphaned and unreachable.**

`ex:covdef-engineered-unresolvable` exists, carrying
`ex:unresolvedTerm: "Adjusted Consolidated Working Capital"`.
`ex:COV-UNRESOLVED-DEFINITION` points at it via `ex:definedBy`; `ex:DEBT-0001`
via `ex:crossReferences`.

**Nothing points at `ex:COV-UNRESOLVED-DEFINITION`.** It, `ex:DEBT-0000` and
`ex:DEBT-0001` all verify at **in-degree 0** across all predicates. A product
traversing obligor → facility → agreement → covenant → definition will never
reach any of them. Corroborated on the relational leg too:
`ex:covdef-engineered-unresolvable` is the **one** covenant definition with no
`ex:documentId`, so it cannot join to a facility either.

**And the engineered marker is inconsistent.** Three of the four carry
`ex:provenance "synthetic — engineered"`; **`ex:DEBT-0000` does not** (its
whole out-edge set is four triples: type, `covenantType`, `sourceAccession`,
`reason`), so a provenance-based exclusion filter behaves asymmetrically across
the cascade.

**Unresolvedness has exactly one signal.** Every cross-reference object in the
ledger is typed — `FILTER NOT EXISTS { ?o a ?c }` returns **0** — so
type-absence cannot detect an unresolved definition. The only signal is
`ex:unresolvedTerm`, carried by exactly two subjects.

**The binding.** Ship the **real** cascade, which this estate supplies
honestly: **CION Investment Corp** has **0** facilities, **0** ownership
records, **0** collateral pledges, **0** adverse-media mentions and an **empty**
`sic` — the only obligor zero on all five legs. That is a genuine five-way
shortfall propagating through a composition, measured rather than engineered.
**Report the orphan upstream** to `ccf-dataprep` through the vault as a
`finding` with `measured_against` and `reproduce_with`; do not repair the
estate from here, and do not substitute a proxy silently.

**TRAP 4 — thinness varies by CONCEPT, not by cohort, and the prior draft's
demonstration compared two different obligors.**

Measured across the 324 cohort rows: `StockholdersEquity` for SIC 2834 /
CY2023Q4I returns **594** of **612** (thinness 0.0294) and `Assets` **589** of
612 (0.0376), while `Revenues` for SIC 5700 / CY2023 returns **1 of 5**
(0.80 — the table's global maximum) and SIC 1623 / CY2023 **2 of 7** (0.7143).
Per tag, mean thinness: **Revenues 0.5676** against OperatingIncomeLoss 0.1607,
Liabilities 0.1507, NetIncomeLoss 0.0993, StockholdersEquity 0.0843, Assets
0.0566. **Revenues is 3.5× the next-worst tag and its minimum exceeds the
median of five of the six.**

**Every one of the 18 SICs has a within-SIC thinness spread of at least 0.40**,
median about 0.65. So collapsing an obligor's 18 cells to one mean destroys at
least a 0.4 range for **every obligor in the roster** — the averaging defect is
universal here, not a special case.

**The prior draft's scenario 5 was internally contradictory** and is corrected.
It said *"same obligor"* and then named a SIC-5700 `Revenues` cohort of 1
beside a SIC-2834 `Assets` cohort of 589 — two different obligors. No single
obligor has both a >100 and a <5 cohort: the 66 rows with `actual > 100` sit in
4 SICs and the 43 with `actual < 5` in 6 disjoint SICs, and the intersection is
empty. **The correct single-obligor demonstration is Container Store Group
(SIC 5700):** `Assets`/CY2023Q4I **5 of 5, thinness 0.0** beside
`Revenues`/CY2023 **1 of 5, thinness 0.80** — a 0.80 spread inside one obligor,
the largest in the table.

**The binding.** Thinness is computed **per `(tag, frame)`**, never averaged to
one number per obligor before it reaches the payload. The obligor-level mean
exists only as an input to the aggregate, and the payload carries the
decomposition beside it.

**TRAP 5 — two obligors have no facility, one has no SIC, and the blank is not
a NULL.**

**18 of 20** obligors have at least one facility; CION and B&G Foods have none.
**10 of 20** have an ownership record, always as parent. **15 of 20** have a
collateral pledge. **11 of 20** have adverse-media coverage, and two of those
hold 337 of the 400 roster mentions.

**CION's `sic` is the EMPTY STRING, not NULL.** Measured: `sic IS NULL` →
`False`, `sic = ''` → `True`, `length(sic)` → `0`; `sic_description` likewise.
A no-peer-set guard written `WHERE sic IS NULL` **will not fire on CION** and
will instead join `peer_cohort` on `sic = ''` for 0 rows without ever raising
the condition. The guard must be `coalesce(sic,'') = ''`. `CMC-G24`.

**The binding.** These are not errors to filter out. They are the population on
which the product's central claim is tested, and they are §A.1's acceptance
test. Every absent leg produces a named `DebtEntry`, never a missing key.

**TRAP 6 — NEW. The peer cohorts are a full period behind the obligors.**

Peer frames span three period-ends: **2023-12-31, 2024-12-31, 2025-12-31**.
Obligor `financial_fact` reaches `period_end` **2026-07-04**. So the latest
available peer cohort is **257 days** older than the obligor figure a memo
would compare it to, and a benchmark that pairs a 2026 obligor number with a
CY2025 peer cohort is comparing **across periods**.

**The binding.** The payload carries the peer frame's period end **beside** the
obligor's, and never presents a cross-period comparison as a same-period one.
No half-life fixes this; it is a disclosure obligation. `CMC-G14`.

**TRAP 7 — NEW. `peer_fact.filed_date` is NULL on all 22,494 rows.**

The prior draft's `CMC-G14` asserted *"peers matched on `period_end`, never on
filing proximity"*. **There is no filing-proximity axis to match on.** The
column exists and is entirely null, so the sabotage that gate named could not
be performed and the gate could never go red. It is replaced by TRAP 6's gate.
Recorded, because a gate that cannot fail is the defect this project checks
for, and this one was caught by asking whether it could.

**TRAP 8 — NEW. The narrative set already contains the exhibits.**

`document.form` is the **parent filing's** form, not the document's own type.
All **68** EX-10 credit-agreement exhibits carry a narrative `form` (8-K 51,
10-Q 11, 10-K 6), so `|EX-10 ∩ narrative| = 68` and `|EX-10 − narrative| = 0`.
**145 = 77 filing-body sections + 68 contract exhibits.** The prior draft's
§C.1 listed *"145 narrative filings"* and *"62 EX-10 exhibits"* as separate
rows, which double-counts — and the 62 was itself the untagged subset of 68.
Any arithmetic adding the two is wrong.

---

## D · Assembly recipe

### D.1 Operator step table

Closed vocabulary only (Standard §10.2). The article's step list uses the
retired names `TemporalTraversal` and `Compose`; the mapping is noted.

**This table is the parent's OWN plan, and that is a hard constraint.** Gate 2
holds the declared set to the parent's own engine-executed set by strict
equality *before* widening the operand with the children's (§B.1). A child's
operator named here makes the product permanently unservable.

| # | Operator | Mode | Reads | Emits | Composition invariant |
| --- | --- | --- | --- | --- | --- |
| 1 | **Resolve** | — | relational | canonical obligor; the `memo_type` section template | Resolve before Traversal |
| 2 | **Policy** | — | bitemporal-ledger, relational | `policy_version` at `as_of`; `debtToleranceDefault`; permitted document set from `corpus_scope` | **Policy before anything that reads graph state** |
| 3 | **Traversal** | `temporal` | graph-traversal, bitemporal-ledger | the definition chain and anchors at `graph_snapshot_at` *(was `TemporalTraversal`)* | Within the step-2 permitted set only |
| 4 | **Enrich** | — | relational, document-passage | peer cohorts and facts per `(tag, frame)`; financial facts; observation signals; relationship summary; passage spans. **One query per source, batched** | Enrich is batched, always |
| 5 | **Similarity** | — | vector-index | ranked supporting passages per memo section, **within the step-2 permitted set** | **Policy before Similarity** |
| 6 | **Evaluate** | `aggregate` | in-memory | per-section evidence sets; per-`(tag, frame)` benchmarks | — |
| 7 | **Evaluate** | `score` | in-memory | this product's own F, C and S (§E.2) | Debt computed here, never read |

`operators_invoked` declared by the class is therefore
`[Resolve, Policy, Traversal, Enrich, Similarity, Evaluate]` — **six, none of
them a child's.**

**What is deliberately NOT a step:**

- **Child acquisition and composition.** They happen in the resolver after the
  projection completes (§0.0), are not operators, and contribute to the
  *served* lineage as `admitted_operators` — the union over the admitted
  children's own operator sets, which the SDK reads off each child's contract.
- **Contract assembly.** The Standard retired `Compose`; it is not an operator.

**Ordered, and asserted as ordered.** The evidence for the
Policy-before-Similarity gate is the replay record's **ordered step trace**
(`ContentGenerationPath.steps`), whose own docstring says *"`steps` carries the
executed order, not merely the set: a Policy-before-Similarity run and its
forbidden inverse invoke the same operators and are not the same decision."*
Not `operators_invoked`, which is a set — the rung-12 and rung-13 lesson that
an unordered collection cannot prove an order.

### D.2 The computation

**Peer benchmarks.** For the obligor's `sic`, retrieve every `(tag, frame)`
cohort — 18 rows per SIC. For each, compute the benchmark from `peer_fact` rows
matched on **`period_end`**. `thinness` is read from the column, not derived;
where it is derived it is `1 − actual/expected_active` (never
`sic_cohort_total`). Carry the peer frame's period end beside the obligor's
(TRAP 6). **An obligor with an empty `sic` has no cohort at all and its
completeness dimension is collapsed, not merely thin.**

**The definition chain.** For each of the **roster's** facilities, resolve
`{source_accession}:{source_document}` to its `ex:CovenantDefinition` nodes,
follow `ex:crossReferences` to `ex:DefinedTerm`, and resolve each anchor
through **`ex:evidencedBy` to a named passage**, re-hashing
`document.text[start:end]` against the passage's own `sha256`. A reference
whose term is never declared — detectable **only** via `ex:unresolvedTerm` —
or whose anchor fails its hash, is **unresolved** and produces a `DebtEntry`.
Materialize and count; never use a grouped SPARQL aggregate (TRAP 1).

**Section evidence.** For each section in the template, rank passages by
embedding similarity within the permitted document set, over passages holding
an **actual vector** (`$type: 'array'`, not `$exists`) — 21,136 of the 21,148
narrative passages qualify. A section reaching its evidence floor carries
`EvidenceRef[]`; a section that does not is marked `NOT_EVALUABLE` with the
reason.

**Debt.** §E.2. Computed this request, from primary evidence, and never read
from `memo_context_debt`.

**Composition.** Declared, not coded (§0.5 and §B.7). The SDK resolves each
requirement to a granted skill, dispatches it, admits the result through seven
checks, and applies the four laws: per-factor minimum, lineage set-union,
expiry floor, mixing refusal. **Mixing floors are keyed by signal type, and the
composite path passes the child's `schema_name` as that type** — so a
`ConstituentValidityFloors` declaration must key on the five child product
class names, or no mixing refusal can ever fire. A floor declared for nothing
is the "configuration nobody reads" defect (`D-GATE-cp-08`), and `CMC-G21`
checks the declaration binds.

**Serve or refuse.** Aggregate composed debt against the tolerance in force —
explicit parameter, else `debtToleranceDefault` from the policy version at
`as_of`. Above it, **the delivery boundary withholds** (`refuse_over_tolerance`,
not a gate), naming the contributing components. `as_of` before 2024-01-01
refuses with authority `technical` (§B.2).

### D.3 The scenarios this product must demonstrate

| # | Scenario | What it shows | Measured expectation |
| --- | --- | --- | --- |
| 1 | Baseline — TransDigm, `annual-review` | A memo substrate that serves | Low debt on every component; 8 sections evidenced |
| 2 | **Same obligor, `as_of` either side of 2025-07-01** | **The policy version changes the tolerance and therefore the answer** | Against the 2026-08-22 comparison snapshot: **9 of 20** serve at 0.30 (policy v1), **6 of 20** at 0.25 (policy v2). **Thermon at 0.3003 is the boundary specimen.** The computed figures will differ — that is TRAP 1 |
| 3 | **CION Investment Corp** | The real cascade — the only obligor zero on all five legs | `sic = ''` so **0** cohort rows and the completeness dimension collapses; exposure, collateral, covenant and family sections all `NOT_EVALUABLE`. Note CION is **second**-highest stored debt; Container Store is highest |
| 4 | **Computed vs stored debt** | TRAP 1 — the product disagrees with the estate's table, and says exactly where | Stored anchor counters: **181 unverified / 90 verified = 271**. Computed over the roster: **194 of 194** resolve, **44 of 44** anchors verified. The comparison is reported with the **2026-08-22** date and its provenance |
| 5 | **`Revenues` vs `Assets`, Container Store Group** | TRAP 4 — thinness is per concept, **within one obligor** | SIC 5700: `Assets`/CY2023Q4I **5 of 5, thinness 0.0** beside `Revenues`/CY2023 **1 of 5, thinness 0.80** |
| 6 | `corpus_scope=filed` vs `filed-and-internal` | The suppression rule, **with its positive control** | The 40 internal memoranda absent under `filed`, with **no marker**; and **present** under `filed-and-internal`. Run on an obligor that has one — not B&G or CION, which have none |
| 7 | `peer_basis=named` | Declared-but-inert fails loudly | `not_supported_at_tier`, never a silent fallback to `sic` |
| 8 | **A required child refuses** | §A.1's worst failure is unreachable | The composite refuses, names the child, and does **not** wrap the refusal as a served empty product |
| 9 | **`as_of` = 2023-12-31** | No governing policy exists before 2024-01-01 | Refusal, authority `technical` — never a fallback tolerance |
| **10** | **THE CONTENT-COMPOSITION PROOF** — two valid versions of one child whose business value differs, every other parent input held fixed | **That the parent's payload changed BECAUSE it read the child** | The parent's corresponding payload value **changes**, and changes **only** via the admitted child — not by querying that child's underlying source. Then the parent **reconstructs from retained child artifacts and recorded inputs, with no second call to any provider** |

Scenario 2 is the demonstration the ladder entry asks for and is the one to
lead the README with: **the same obligor, the same evidence, a different
governed answer, because the policy in force on the decision date is
different.**

### D.4 Determinism and replay

**Determinism class: deterministic.** Every step is a pure function of
(request, `graph_snapshot_at`, `policy_version`, estate state). No model, no
wall-clock read other than `as_of` and the admission clock. Identical inputs
against an identical snapshot produce an identical `payload_hash`.

**Replay statement.** A replay resolving the same `graph_snapshot_at`,
`policy_version` and request parameters reproduces the payload byte-for-byte.
Replay uses **retained child artifacts and recorded composition evidence**, not
fresh calls to the atomic providers — and on merged `main` that sentence is
mechanism rather than intent: each admitted child's contract is retained by
content address at decision time, and `replay()` rebuilds the
`ChildContractView` from those bytes — held to the address the row names —
**before** the child-dependent plan is resolved, through
`CompositeReplayEnvironment.resolve_composite_plan`. Each `ChildResolution` row
carries the child's own `operators_invoked`, `expires_at`, `admitted_at`, debt
**factors** (the F/C/S triple, not only the scalar) and content address, which
is what lets the composite's lineage, expiry and content address be rebuilt
from the record alone. The SDK's own proof — a fresh environment, a fresh store
instance, the provider one-shot — is `tests/products/test_d_impl_339_child_contract_view.py`.

**A refusal replays, but not as a served determination.** The prior draft said
*"a refusal is a served determination and replays as one."* That is wrong on
the shipped surface. A refused composite writes a **full five-dimension
record** in which `product_content_address` is `NO_PRODUCT_ADDRESS`, `steps` is
empty, and `assembly_refusal` carries the envelope; dimensions 2, 3 and 4 are
unchanged from what a fulfillment would have carried. A **blocking** refusal —
reached after acquisition and before projection — is recorded with no
execution at all: dimension 1 says positively that nothing was read, and the
child rows the walk produced are on it.

**`CP14-F-09` — FIXED by `D-IMPL-338` (`D-GATE-338`, `4c77cc60`).** At Gate 1
the child rows traveled on the served path and on a composition refusal only;
the gate, product-gate and **tolerance** paths recorded a refusal without them
— and a tolerance refusal is this product's headline behavior. On merged
`main` the rows travel on every refusal reached after acquisition: **seven
exits, two before acquisition passing no child evidence, five after it passing
the rows**, and the census is a shipped test.

**The known limit, carried forward from rung 13.** The Fluree instance accepts
a `t` parameter and ignores it, returning current state at every value
(`CP13-F-01`). Replay against a *past* graph state cannot be demonstrated on
this estate, and the replay assertion is scoped to the current snapshot. An
estate limitation, recorded as such.

**Content address vs determination identity.** Per `24.11-C-01`: two requests
producing the same bytes produce the same address, and that may be correct. The
identity of a *determination* is the request plus the snapshot plus the policy
version, and the payload carries all three.

### D.5 Validation gates — intentions, phrased so they can fail

Fixture ids land at Gate 2. **Every gate below was audited against one
question: can the mechanism it names actually diverge under sabotage?** Two
could not and were replaced; one contradicted the contract and was replaced;
seven were added for the shipped composition surface. The audit is §D.6.

| Gate | Asserts | Red when |
| --- | --- | --- |
| `CMC-G01` | Empty-operator guard | Any step emits an empty result that later steps consume as populated |
| `CMC-G02` | **Composite Gate 2, both halves.** The parent's declared operator set equals its own engine-executed set; and the composite's union lineage equals `parent_executed ∪ admitted_child_operators` | Either comparison fails. **Sabotage: name a child's operator in the class declaration** — the parent-own half must go red, and the union must not mask it |
| `CMC-G03` | TTL bounds **and the expiry floor** | Served TTL outside 12h, anchored anywhere but `from_decision`, or **later than the stalest admitted child's expiry** |
| `CMC-G04` | **The GOVERNING debt is computed, never read.** No value from `memo_context_debt` reaches the serve/refuse determination. Does **not** prohibit the labeled comparison `CMC-G05` requires — the two are distinguished by *which figure governs* | A value read from the table reaches the governing `D_c`. Sabotage: route the governing figure through the table |
| `CMC-G05` | **Diagnostic comparison against the identified snapshot.** Compares the computed figure against `memo_context_debt` **as of 2026-08-22**, carrying that date and provenance into the payload, and records the divergence and its direction. **A measured demonstration, not a permanent invariant** — on an upstream refresh equality may be correct, and the gate asserts *the comparison was made and reported* | The comparison is absent, or reported without the snapshot date and provenance, or the divergence is silently discarded |
| `CMC-G06` | **Policy-before-Similarity**, asserted against the **ordered** replay step trace | A passage outside the step-2 permitted set appears in any `EvidenceRef`, or the trace shows Similarity before Policy |
| `CMC-G07` | **Tolerance comes from the policy version** | Changing `as_of` across 2025-07-01 does not change the serve/refuse boundary. **Boundary convention `<=` serves; Thermon at 0.3003 is the specimen** |
| `CMC-G08` | Section coverage | A template section appears in neither `EvidenceRef[]` nor a `DebtEntry` |
| `CMC-G09` | Passage resolvability | An `EvidenceRef` whose `sha256` does not re-hash from `document.text[start:end]` |
| `CMC-G10` | **Per-`(tag, frame)` thinness** | Thinness reaches the payload as one obligor-level number with no decomposition |
| `CMC-G11` | Suppression rule, **with its positive control** | A count, marker or placeholder discloses withholding under `corpus_scope=filed` — **or** the memoranda fail to appear under `filed-and-internal`, which would make the rule vacuous |
| `CMC-G12` | Declared-but-inert | `peer_basis=named` or `sic-and-size` succeeds instead of raising `not_supported_at_tier` |
| `CMC-G13` | **REPLACED. A refusal carries the GOVERNING factor decomposition, kept distinct from the dated diagnostics, at the permitted disclosure level.** It names the contributing components as **F / C / S** — the decomposition that governed — and carries the tolerance in force with its source. The estate's four additive components appear only where `CMC-G05` puts them: **labeled, dated 2026-08-22, and marked non-governing**. What reaches the caller respects the disclosure floor (§B.5); the full evidence is retained in replay | The refusal presents the four historical components **as** its decomposition; or omits F/C/S, the tolerance, or the tolerance's source; or discloses to the caller more than the level permits |
| `CMC-G14` | **REPLACED. Cross-period peer disclosure.** The payload carries the peer frame's period end beside the obligor's, and does not present a cross-period comparison as same-period | A benchmark pairs a 2026 obligor figure with a CY2025 cohort without disclosing the gap |
| `CMC-G15` | Determinism | Two runs against one snapshot produce different `payload_hash` |
| `CMC-G16` | **Resolution and auditability are kept apart** (TRAP 1a) | A covenant claim is emitted as a checked citation on the strength of a resolved cross-reference with no `passageSha256` backing the span — or a point anchor is quoted with bounds |
| `CMC-G17` | **Guarded-path provenance** (`D-IMPL-337`; the boundary is `resolve_child_outcomes`) | A child that did not come through `CompositeAdmissionGate` is composed, or is read as an honest absence, rather than refusing the composition as `unsupported-outcome` |
| `CMC-G18` | **A refused child refuses the composite** | A refused child is wrapped as a served empty product, or the composite serves without it |
| `CMC-G19` | **Inherited debt is the per-factor minimum, not `max(child D_c)`** | Replacing the combinator with the scalar maximum leaves the answer unchanged. **Requires two children weak on DIFFERENT factors** — established at Gate 2 |
| `CMC-G20` | **Lineage set-union** | The composite's lineage omits any admitted child's operators or policy versions |
| `CMC-G21` | **Mixing floors bind** | `ConstituentValidityFloors` is declared against a signal type no child's `schema_name` matches, so the refusal can never fire |
| `CMC-G22` | **Five child replay rows, on every exit after acquisition** (`D-IMPL-338`) | Fewer than five `ChildResolution` rows on the served path or on **any** refusal reached after acquisition — composition, gate, product gate, tolerance, or the blocking refusal |
| `CMC-G23` | **No local substitute for composition** | Any hand-rolled child resolution, admission, inherited-debt composition or per-child replay appears under `examples/cp-14-credit-memo-context/` |
| `CMC-G24` | **The empty-string `sic` guard fires on CION** | A no-peer-set guard written `sic IS NULL` lets CION through with a silently empty cohort |
| `CMC-G25` | **No policy, no serve** | `as_of` before 2024-01-01 serves against a fallback tolerance instead of refusing with authority `technical` |
| `CMC-G26` | **The caller's view respects the disclosure floor** | An acceptance criterion asserts the caller sees a child refusal's reason token or content addresses, which at the default `minimal` level are withheld |
| `CMC-G27` | **No child-owned material is re-derived** (§B.8) | This product's plan queries `facility`, `collateral_pledge`, `corporate_ownership_record` or the obligor's financial spread for material a required child supplies |
| `CMC-G28` | **THE CONTENT-COMPOSITION PROOF.** Swapping the admitted child for a second valid version, every other input fixed, changes the parent's payload — **and the change is attributable to the child instance, not to a source re-query** | The payload is unchanged, **or** it changes while the child's source is independently queried (detectable: sever the child's source after admission and the parent must still produce the changed value from the admitted contract) |
| `CMC-G29` | **Reconstruction without the providers.** The parent rebuilds from retained child artifacts and recorded inputs | Reconstruction calls any provider again, or fails without one |

**Every gate gets sabotaged once**, per the standing practice: break the
mechanism the gate names and confirm red. A gate that stays green under
sabotage is a test defect, and rung 13 found four of them.

### D.6 The sabotage-divergence audit

Each gate was checked against: *is there a change to the product that this gate
would catch and nothing else would?* Three failed.

| Gate | Verdict | Note |
| --- | --- | --- |
| `CMC-G01`…`G03`, `G05`…`G12`, `G15`…`G27` | **Divergent** | The named mechanism can be broken and the gate goes red |
| `CMC-G13` (prior: *refusal shape-identity*) | **REPLACED — it contradicted §B.5** | §B.5 requires the refusal to **name** the contributing components; a gate demanding two refusals be indistinguishable in shape argues against it. Unlike cp-02 there is no confidentiality reason to hide which component failed — naming it is the product's value. Replaced with a gate on what the refusal must **carry** |
| `CMC-G14` (prior: *peers matched on `period_end`*) | **REPLACED — it was vacuous** | `peer_fact.filed_date` is NULL on all 22,494 rows, so *"matched on filing proximity"* is not a state the product can be sabotaged into. Replaced with TRAP 6's cross-period disclosure, which is real |
| `CMC-G07` | **Divergent, with a Gate-2 condition** | It can only fire if some obligor's **computed** debt lands in `(0.25, 0.30]`. Against the **stored** table three do. The product computes under a different (multiplicative) model, so **band membership must be re-established at Gate 2**; if no obligor lands in the band the gate is vacuous and must be re-cut |
| `CMC-G19` | **Divergent, with a Gate-2 condition** | `min` and `max(child D_c)` agree when every child is weak on the same factor. The gate needs **two children weak on different factors**, which must be measured at Gate 2. The SDK has **no direct test of `compose_debt_factors`** at all, so this is genuinely new coverage rather than a re-test |
| `CMC-G11` | **Divergent only with the positive control** | Without the `filed-and-internal` half it passes on a product that never reads the memoranda |
| `CMC-G28` / `CMC-G29` | **Divergent, and RUNNABLE** | They were unrunnable at Gate 1 because no path carried child content to the payload. `D-IMPL-339` shipped the path and proved both properties on the SDK's own fixture — the parent's payload changes because it read a different valid child, and a fresh environment reconstructs the exact address with the provider disabled. CP-14's gates re-prove them on the **real** five children at Gate 2 |

**Two vocabulary cautions, so a gate is not written against a dead token.** Of
the SDK's 20 closed child-refusal reasons, **`composition-unwired` and
`ambiguous-producer` are never emitted** — the unwired case emits
`no-producing-skill`, and ambiguity raises rather than refusing. The
`refused` outcome status is likewise declared and never mapped. A gate
asserting any of the three would be asserting a state the shipped code cannot
reach.

---

## E · Volatility, debt & materialization

### E.1 Half-life table — calibrated against the estate, and measured

**Illustrative calibration:** This example runs against a point-in-time
demonstration estate rather than continuously refreshed production data.
Freshness half-lives and related thresholds are calibrated to make the
governed behavior observable in that snapshot. They demonstrate how the SDK
applies these controls and should not be interpreted as recommended production
coverage-policy thresholds.

**And here the calibration was measured rather than guessed**, per `D-IMPL-323`
condition 1. Computing `exp(−ln2 · age / H)` over the 20 obligors' measured
latest-filing ages:

| `H` | fresh (factor > 0.5) | stale | comment |
| ---: | ---: | ---: | --- |
| 7 / 14 / 30 | **0** | **20** | **every obligor reads stale — the cp-08 failure exactly** |
| 45 | 7 | 13 | the control begins to discriminate |
| **90** | **14** | **6** | **widest usable separation; only one obligor fully decayed** |
| 180 | 18 | 2 | |
| 365 | 19 | 1 | |
| 730 | **20** | **0** | **the control fires for nobody** |

| Signal class | λ_c | Calibration basis | Decay driver | Supersession event |
| --- | --- | --- | --- | --- |
| Filed narrative text | **no decay** | measured | Immutable once filed | Restatement |
| Obligor financials | **90 days** | **illustrative, measured** | Quarterly reporting; 14-fresh/6-stale split | New filing |
| Peer benchmarks | **90 days** | illustrative | Quarterly cadence — but see TRAP 6: the cohort is a **full period** behind and no half-life repairs that | New `frames` period |
| Observation signals (`signal_event`) | **90 days** | **illustrative, measured** | 20 distinct ages, 28…593 days, smoothly distributed | New observation |
| Adverse media | **180 days** | illustrative | Covered obligors span 32…726 days — but **9 of 20 have no coverage at all**, which a half-life cannot express | — |
| Policy envelope | **on change** | expert | Not time-decayed; version-superseded | `supersededBy` |
| **Inherited from children** | **the per-factor minimum** | mechanism | — | Any prerequisite invalidation |

**Three rows carry a caution rather than a number.**

- **Adverse media discriminates on COVERAGE, not decay.** Nine of twenty
  obligors have zero mentions and a half-life cannot express *"no coverage at
  all"*. The spec needs a distinct **no-coverage** term alongside any decay
  term, and the two must not be collapsed.
- **Peers cannot be fixed by a half-life.** The latest cohort period end is
  257 days old by construction; any λ_c short enough to be meaningful fails
  every peer comparison closed. TRAP 6's disclosure is the control, not decay.
- **`signal_event` is the estate's only fully discriminating freshness axis** —
  20 obligors, 20 distinct ages, 20/20 coverage. `memo_context_debt.signal_
  staleness`, by contrast, takes **7 distinct values over 20 obligors**, with
  11 sharing one value. That is not a defect in the stored column — it is a
  faithful function of `period_end`, and those 11 obligors genuinely share the
  quarter end 2026-06-30 — but it means a freshness control built on
  quarter-quantized `period_end` cannot separate obligors inside a quarter-end
  cohort. **This product computes freshness from `signal_event.observed_at`**,
  and states why.

### E.2 Debt model, and this product's own F, C and S

**RULED (§0.4 item 2): the Standard's multiplicative model governs serving**,
and it is what the SDK ships. `context_debt` returns `D_c = 1 − (F · C · S)`;
its module states *"there is no weighted-additive alternative in this module to
fall back to"* and *"this module ships no weights and no additive path — not as
a default, at all."* F, C and S are **strength** factors in `[0, 1]`, Decimal
only, refused outside the interval rather than clipped, and a `float` is
refused at construction rather than coerced.

**The estate's additive four-component form is a DIAGNOSTIC beside the
governing figure — not its decomposition.** Calling it the decomposition would
assert a mapping into F, C and S that would then have to be checked. Under the
additive model CION's `peer_set_thinness` of **1.0** — *no peer set exists at
all* — contributes 0.25 and the obligor still serves at 0.4309. Under the
multiplicative model a collapsed dimension drives `D_c` toward 1 and forces the
escalation. The multiplicative model is the one that does what §7.7 says
Context Debt is for.

**Inheritance is the per-factor minimum over strength factors**, as shipped:

```
F_parent = min(own F, admitted children's F)
C_parent = min(own C, admitted children's C)
S_parent = min(own S, admitted children's S)
D_c      = 1 − F_parent × C_parent × S_parent
```

**Never `max(child D_c)`.** The shipped combinator's own docstring gives the
reason: *"a child weak only on F beside a child weak only on C each yield a
modest D_c, and taking the larger of the two would tell the parent it has one
modest problem when in truth both its freshness and its completeness are
impaired."* Zero new weights are introduced. **An empty children sequence is
legal** and raises nothing — only a `None` `own` raises, and that branch is
unreachable.

**Unknown child debt is not zero.** A child served without an assessable debt
decomposition never reaches the combinator: admission refuses it
`debt-unassessable`, because composing it would give the parent assumed-good
factors it has no evidence for.

#### E.2.1 CP-14's own F, C and S — authored here, as Dave ruled

Only **F** has an SDK reference scorer; **C and S are the product's to define
and are declared at boot**. `D-IMPL-336` Amendment 2 rules that *CP-14's own
F/C/S measurement definitions belong in its revised Gate-1 contract* — they are
CP-14's to author, not the SDK's to supply. This subsection discharges that.

**F — freshness.** Over the **required** signal classes, never the present ones
(Standard §5.2: *"or losing a source improves the freshness score"*). The
required classes for a memo substrate are: obligor financials, observation
signals, the definition chain, and the policy envelope. For each, the decay
factor `exp(−ln2 · age / λ_c)` at the λ_c in §E.1, with age measured from
`as_of`; `F` is the **minimum** across the four, not the mean — a mean lets a
current policy version mask a two-year-old filing. Filed narrative text does
not decay and does not enter. Adverse media is **not** a required class (9 of
20 obligors have none) and enters `C`, not `F`.

**C — completeness.** The fraction of the memo template's sections that carry
evidence at or above their floor, multiplied by the fraction of required legs
present. Concretely, for a template of `n` sections:

```
C = (sections_evidenced / n) × (legs_present / 5)
```

where `legs_present` counts the five prerequisite classes **whose admitted
child contract reported positive data** — read from the admitted contract this
request composed, never re-derived from the estate (§B.8, `CMC-G27`). This is
the per-request input path `C` depends on, and `D-IMPL-339` supplies it. **CION scores `legs_present = 0`, so `C = 0` and `D_c =
1` regardless of F and S** — which is the collapsed-dimension behavior §7.7
commits to, arrived at by measurement rather than by a special case.

**S — semantic consistency.** The fraction of text-borne claims that are
**auditable**, not merely resolvable — i.e. carry an `ex:PassageAnchor` whose
`passageSha256` re-hashes. Measured against this estate, covenant-definition
claims contribute **0** auditable claims out of 48 quotable spans (TRAP 1a), so
`S` is dominated by the passage-anchored section evidence. **This is the term
that makes rung 13's finding visible in a number** rather than a footnote.

**Per request, from the admitted contracts — not declared at boot.** `C` and
`S` are computed by this product's scorer implementing
`ChildAwareDebtScorerProtocol.score_with_children`, which receives the same
`ChildContractView` the plan received, so both read the five admitted
contracts of *this* request. A scorer implementing only the original seam is
asked as before and would have to declare `C` and `S` as constants; this
product does not. No prompt, no constant, no table in code.

### E.3 Per-component debt table

| Component | May be absent? | `D_c` contribution | Behavior when absent |
| --- | --- | --- | --- |
| Section template | **no** | — | Fail closed — no template, no product |
| Policy envelope at `as_of` | **no** | — | Fail closed, authority `technical`. Includes `as_of` < 2024-01-01 (§B.2) |
| Obligor financial facts | no | `F` | Fail closed — 20 of 20 covered, so absence means a resolution defect |
| Observation signals | no | `F` | Fail closed — 20 of 20 covered |
| Peer cohort for the SIC | **yes** | `C`, per `(tag, frame)` | Serve with thinness flagged; **no cohort at all → dimension collapsed** |
| Definition chain / anchors | **yes** | `C`, and `S` for auditability | Mark the covenant claim `NOT_EVALUABLE`; never emit an unverifiable citation |
| Each of the five children | **no — all required** | `F`, `C`, `S` by per-factor minimum | A required child that **refuses** refuses the composite; a required child that **reports absence** is admitted and its weak factor is inherited |
| Adverse media | **yes** | `C` (coverage), not `F` | Serve with flag — 9 of 20 have none and that is normal |
| Internal memoranda | **yes** | — | Out of scope under `corpus_scope=filed`; **absence is never marked** (§B.6) |
| Relationship history | yes | `C` | Serve with flag |

**The authority vocabulary is closed and has four members** — `default`,
`caller`, `policy`, `technical` — and it attaches to a **parameter or a
tolerance**, never to a gate refusal, which declares only its gate and detail.

### E.4 Materialization posture

**`derived-on-demand`.** The mechanical test: the fastest-moving required
input — observation signals at λ_c ≈ 90 days, and the composed expiry floored
by the stalest child — sits inside any useful cache window for a 12-hour TTL
product only if every child is simultaneously cacheable, which the expiry floor
makes unreliable. The product sits in the most expensive quadrant (×8–15) and
that is the correct posture, because the alternative is a stale committee
packet.

**Cache key:** `(tenant, schema_name, projection_plan_id, graph_snapshot_at,
policy_version, lei, memo_type, sections, peer_basis, as_of, debt_tolerance,
corpus_scope, principal)`. A key missing any parameter that changes the payload
is a correctness defect presenting as an intermittent one — `debt_tolerance`
and `as_of` both change the serve/refuse determination and both belong in it.

### E.5 Supersession triggers

| Event | Local / cascading | Effect |
| --- | --- | --- |
| Any prerequisite invalidation | **cascading** | Invalidate; the per-factor minimum recomputes |
| New filing for the obligor | local | Financials and narrative refresh |
| New observation in `signal_event` | local | `F` recomputes |
| New `frames` period published | local | Peer benchmarks recompute; thinness moves; the cross-period gap narrows |
| Policy version change | **cascading** | Tolerance changes → the serve/refuse boundary moves for every obligor |
| Anchor or definition repair upstream | local | The auditability term recomputes — **this is TRAP 1's event, and the estate did it on 2026-09-13** |
| Debt weight change | — | Affects the **diagnostic** comparison only; the governing figure carries no weights |

Re-derivation is **lazy** — invalidate for next request; never re-materialize
eagerly.

---

## F · Source binding & readiness

### F.1 What exists, what does not

| Manufacture-envelope item | Required | Measured | Status |
| --- | --- | --- | --- |
| ~20 obligors with memo-grade coverage | 20 | **20** rostered; 18 with a facility, 15 with a pledge, 10 with ownership | **PARTIAL — and deliberately so** (TRAP 5) |
| ~60 filed documents | 60 | **145** narrative documents = 77 filing sections + 68 EX-10 exhibits | **MET** |
| ~40 internal credit memoranda | 40 | **40**, covering 18 of 20 obligors | **MET** |
| Peer sets of varying size (≥1 rich 15+, ≥1 thin 3) | — | `actual` spans **1 … 594**; every SIC has a ≥0.40 within-SIC thinness spread | **EXCEEDED** |
| ≥1 obligor breaching `debt_tolerance` | 1 | **11** at 0.30, **14** at 0.25 (2026-08-22 comparison snapshot) | **MET** |
| **≥1 cascade case** | 1 | Engineered case **orphaned**; real five-way cascade available (CION) | **MET via substitution — see `CP14-F-02`** |
| 4 memo types with distinct templates | 4 | **4** (9/8/7/7 sections) | **MET** |
| ≥2 policy versions with distinct effective dates | 2 | **2** of 17 in the ledger | **MET** |
| **Five acquirable child products** | 5 | All five prerequisite trees reach a governed `ServedProduct` with a replay record | **NOT MET.** Four of five serve; **cp-03 does not serve on the current SDK** — refused at `ProductRequestContract`, 13 of its 17 output tests a `strict` xfail quarantine (`CP14-F-22`). And no child can be **admitted**: each serves under its own tenant and the shipped `CompositeAdmissionGate` admits one — measured at Gate 2, `CP14-F-16`; **HOLD on `D-IMPL-340`** |

### F.2 Named gaps, with owners

| Id | Gap | Owner | Proposed disposition |
| --- | --- | --- | --- |
| `CP14-F-01` | **`memo_context_debt` was measured against a superseded estate state** — `as_of` 2026-08-22, predating the 2026-09-13 anchor re-keying. **The stale element is the pair of counters** `definition_refs_unverified` 181 / `definition_refs_verified` 90; the other three components re-derive exactly. **No claim is made that the August figures were correct in August** | `ccf-dataprep` | Report through the vault as a `finding`. **Do not repair from here.** The product computes its own governing figure; the table is the dated comparison. On refresh: record it, retain as `FIXED-upstream`, keep `CMC-G04` active |
| `CP14-F-02` | **Engineered cascade case orphaned** — `ex:COV-UNRESOLVED-DEFINITION`, `ex:DEBT-0000` and `ex:DEBT-0001` all at in-degree 0; `ex:covdef-engineered-unresolvable` additionally has no `ex:documentId`, so it is unreachable on the relational leg too. **And the marker is inconsistent** — `ex:DEBT-0000` lacks `ex:provenance "synthetic — engineered"` | `ccf-dataprep` | Report. Ship the real CION cascade meanwhile |
| `CP14-F-03` | **`inherited_prerequisite_debt` has no stored source**, though `0.2·[no facility] + 0.2·[no pledge]` reproduces all 20 rows | `ccf-dataprep` | Report. The product computes it as the per-factor inheritance from the children actually invoked |
| `CP14-F-04` | **No Item-level passage headings** — 2,411 of 2,414 belong to the exhibits; the 77 filing bodies carry **3**, all statute references. A `section` field and a structured `document_id` DO carry the identity | estate / accepted | **ESTATE-LIMITATION** on headings. Whether the `section` label licenses an Item citation is §H item 2 |
| `CP14-F-05` | **`peer_basis` size-band and named-list unsupported** — `peer_cohort` is keyed `(sic, tag, frame)` only | accepted | Declared-but-inert, `not_supported_at_tier` |
| `CP14-F-06` | **ECOA flag is a declaration with no door** — no protected-class attribute exists to restrict on | accepted | Recorded in lineage, declared inert in the payload (§B.3) |
| `CP14-F-07` | **Ledger `t` is accepted and ignored** — inherited from `CP13-F-01` | estate | **ESTATE-LIMITATION.** Replay scoped to the current snapshot |
| `CP14-F-08` | **Resolution repaired, auditability not** (TRAP 1a) — 170 point anchors; **0 of 49** covenant definitions carry a hash while 48 carry a quotable span; and **0 of 48 spans is contained in or overlaps any anchor span**, so there is no repair path | `ccf-dataprep` / accepted | Report. Product emits a checked citation only where a `passageSha256` backs it (`CMC-G16`) |
| `CP14-F-09` | **SDK: a composite's child replay rows were lost on a downstream refusal** — the gate, product-gate and **tolerance** paths recorded a refusal without them, and a tolerance refusal is this product's headline behavior | **SDK** | **FIXED-`D-IMPL-338`** (`D-GATE-338`, merged `4c77cc60`). Rows travel on all seven exits after acquisition; the census is a shipped test; audit evidence stays apart from caller disclosure. Nothing was worked around here (`D-IMPL-261`) |
| `CP14-F-10` | **SDK: three declared refusal tokens are unreachable.** `composition-unwired` and `ambiguous-producer` are never emitted, and the `refused` outcome status is never mapped. Worse, the unwired-resolver case emits `no-producing-skill`, telling an operator *no skill produces this class* when the truth is *no resolver was bound* | **SDK** | Report. No gate is written against a dead token |
| `CP14-F-11` | **SDK: the external statement for a child refusal is wrong for optional slots.** `EXTERNAL_STATEMENTS["composite-child-refusal"]` says a **required** child failed admission, but a refused **optional** child refuses the composite too, and the refusal branch has no `required` test | **SDK** | Report |
| `CP14-F-12` | **SDK: `compose_debt_factors` has no direct test.** The min-vs-max distinction with two children weak on *different* factors — the exact case its docstring is written about — is untested | **SDK** | Report. `CMC-G19` is new coverage, not a re-test |
| `CP14-F-13` | **SDK: no cycle guard on composite requirements.** Nesting is proven three levels deep, but nothing refuses A-requires-B-requires-A | **SDK** | Report as a narrow gap. CP-14 does not exercise it |
| `CP14-F-14` | **`peer_fact.filed_date` is NULL on all 22,494 rows**, and the peer cohorts are a **full period behind** the obligors | estate | **ESTATE-LIMITATION.** Killed the prior `CMC-G14`; replaced by cross-period disclosure |
| `CP14-F-15` | **`gdelt_mention.down_weight_factor` is inert for this roster** — all 49 down-weighted rows belong to a single non-roster LEI | accepted | Recorded so no gate is written against it |
| `CP14-F-16` | **SDK ruling: no child can be admitted — five children, five tenants, one gate.** Measured on `main c635037f`: cp-04-canonical run for real, behind a real door, offered to a real `GrantBoundChildResolver` + `CompositeAdmissionGate` under a CP-14 tenant → `tenant-mismatch` at check 1. Control: same wiring with the gate set to the child's own tenant and the requirement corrected → `AdmittedChild`. The five tenants are `cp-03-demo`, `cp-04-canonical-demo`, `cp-05-demo`, `cp-06-demo`, `cp-13-crossref-demo`; no child exposes a tenant override; `D-IMPL-261` forbids editing them | **SDK / ruling** | **`D-IMPL-340` RULED — direction B, design only** (`docs/D-IMPL-340-DESIGN.md`); A and C rejected. Gate 2 HOLD until 340 is implemented and merged. No artifact, door or workaround written |
| `CP14-F-17` | **SDK: no shipped transport carries a question to a producer that is not this fabric.** `_invoke_local_callable` passes arguments but presumes this fabric's store and invalidation register; `_invoke_mcp` reads the one URI the binding registered and only *records* the arguments; `_invoke_peering` drains `transport.receive()` and only records them. Every child is parameterized. Egress already serves an addressed question (`…/q/{q}`, `request_context_product`) that composition cannot ask | **SDK** | **`D-IMPL-340` RULED** — capability A: the producer's existing `request_context_product` surface, arguments reach the producer, nothing interpolated into an address |
| `CP14-F-18` | **Spec defect at Gate 1: §B.7 named three classes no child registers**, under a note claiming they were the trees' own. Measured: `credit-risk.spread` @ 1.0.0, `reference.corporate-family` @ **2.0.0**, `credit-risk.exposure-rollup` @ 1.0.0; the two others were right | spec | **FIXED in this revision** — §B.7 corrected from the five `ccf_config.yaml` files; the false note replaced by the measurement |
| `CP14-F-19` | **cp-05 pins its reconstruction instant** (`artifacts/question.yaml` `2026-09-07T12:00:00+00:00`; a caller's `asked_at` is not forwarded; `as_of` refused by name), so the composite's one instant must equal that pin or the slot refuses `as-of-mismatch`. At that pin cp-05's `D_c` is **1.000** for every obligor (balances days old against a 4 h λ_c) and its class-default tolerance 0.25 **withholds** — a required slot refused for everyone unless cp-05 is asked with `debt_tolerance ≥ 1.0` | estate | **ESTATE-LIMITATION — RULED (Dave, 2026-09-14).** The pinned instant and the measured `D_c = 1.000` stay visible; the example is **not** tuned to make the child healthier. Instant fixed at `2026-09-07T12:00:00+00:00` |
| `CP14-F-20` | **Two children do not take the memo's anchor.** cp-06 answers **one facility per call** (`facility_id` + `borrower_scope` required; no LEI→facility lookup in its tree) and cp-13's subject is an `ex:PassageAnchor` URI set. The composition surface dispatches **once per requirement**, so per-obligor coverage over N facilities is inexpressible, and the LEI→facility / LEI→anchor derivation is parent-owned argument mapping this spec never stated at Gate 1 | spec / ruling | **RESOLVED for CP-14 — RULED (Dave, 2026-09-14): facility grain.** The request names the `facility_id` whose collateral context belongs in this memo, explicitly, beside the obligor; `child_arguments` passes it to the collateral skill. Not: the first facility, the largest, an implicit fan-out over all facilities, a raw-store reconstruction, or treating cp-06 as an obligor-level product. A consolidated multi-facility collateral context is a different product class (a roll-up skill over facility-level products); equipment finance may need a different collateral product entirely. **The contract (§B) gains the `facility_id` argument at the next revision** — before Gate 2 resumes |
| `CP14-F-21` | **Four of five children raise for a missing anchor instead of refusing.** cp-03 `AnchorUnresolvable` (bare), cp-04c / cp-05 / cp-06 `LookupError`, cp-13 `ValueError` / `UnknownCovenantSource` — none a disclosed, replay-referenced envelope, so `door_answer` cannot carry it and a raised child crosses the composite as a crash with no replay record. Only cp-04c's *zero-relationship* case serves (one-node family) | examples (frozen) | **SEPARATE behavioral finding — RULED (Dave, 2026-09-14): not folded into `D-IMPL-340`.** A missing anchor must produce a governed refusal where the contract requires refusal semantics. **Population measured** (AST census over non-test modules, `main c635037f`): **16 of 19** shipped trees raise for an unresolvable anchor or source — 12 of the 13 ladder rungs (all but cp-10): cp-04-canonical `acquisition.py:352` `LookupError`; cp-05 `assembler.py:111`, `produce.py:272`; cp-06 `acquisition.py:262`; cp-07 `acquisition.py:375`; cp-08 `UnknownFacility`; cp-09 `UnknownClient`; cp-11 `UnknownObligor`; cp-12 `UnknownTrade`; cp-13 `UnknownCovenantSource`, `deployment.py:95` `ValueError`; cp-01/02/03 `AssemblyRefused`; cp-00 `RuntimeError`. Handled separately if it blocks a CP-14 required scenario — which turns on `CP14-F-24` |
| `CP14-F-22` | **cp-03 (`credit-risk.spread`) does not serve on the current SDK.** `tests/examples/test_cp_03_output.py` carries 13 `xfail(strict=True)` quarantines over 17 tests: the frozen `ccf_config.yaml` declares `intent` under `arguments.properties` (refused at `ProductRequestContract`) and the frozen `produce.py` calls `build_replay_record` with no resolution state (`D-IMPL-264` D-01/F-2, D-10/D-13; *"un-quarantine and rerun unchanged after `D-GATE-24.7`"* — `24.7` is closed and the rerun was never done). Gate 1 asserted *"all five prerequisite trees reach a governed `ServedProduct`"*; it had read the trees, not run them | examples (frozen) / ruling | **BLOCKING PREREQUISITE — RULED (Dave, 2026-09-14).** A required child that cannot produce a governed `ServedProduct` is not a usable child: spread is **not** made optional, not hand-built, not read from raw stores, and the tree's existence is not evidence it serves. **Run independently on `main c635037f`** (cp-03's own `run.py`, demonstration anchor, curated estate): refused at `ProductRequestContract.from_declared` — *"the request contract for 'credit-risk.spread' at class lane '1.0.0' declares 'intent' under arguments.properties, which is a shadow of the top-level request field ProductRequest.intent … (D-IMPL-264 D-01, amendment 1 F-2)"*. **The quarantine is real, not stale.** The second quarantined defect (`build_replay_record` without `resolution`, `produce.py:408-423`) sits behind it and was not reachable. Disposition per ruling: repair in its own phase, or supply another real governed producer of the exact required class (`cp-04-canonical` is the precedent for a canonical sibling beside a frozen specimen). CP-14 resumes only when the spread slot has a serving producer. **And once repaired it serves few at the only instant cp-05 accepts:** its TTL is 30 days from the latest filing (`artifacts/ttl.yaml`, `now < expires_at <= now + MAX_TTL`), the estate's newest filing is 2026-08-13, so at `2026-09-07T12:00:00+00:00` only obligors filed on or after 2026-08-08 serve — the roster's youngest filing was 33 days old at 2026-09-14 (§B.4); the exact count is rung 3's to measure at its rerun, and its refusal is *raised* (`RuntimeError`), not returned |
| `CP14-F-23` | **SDK: the composite's request never reaches the child mapping.** `GovernedResolver` calls the child resolver with `requirements, asked_at, admitted_at, composition_invocation, consumer_lineage` — no request, no subject — and `ChildArguments` is `Callable[[ChildRequirement, datetime], Mapping[str, str]]`. A per-request anchor (this product's `lei`) can reach a child only by closing over per-request state outside the declared mapping (a resolver rebuilt per request, or a mutable cell — what the `D-IMPL-339` proofs did) | **SDK** | **`D-IMPL-340` RULED** — the design's `ChildQuestions` mapping receives the composite's effective request through a capability Protocol |
| `CP14-F-24` | **Spec: §D.3 scenario 3 is unreachable as written.** It serves CION with sections marked `NOT_EVALUABLE`; but all five slots are `required: true` (§B.7), a required slot may carry no `absence_treatment`, and for CION cp-06 refuses (`product-request-violation`, no facility to name), cp-13 raises (zero anchors) and cp-05 withholds at its default tolerance — so the composite **refuses** (scenario 8); it does not serve with absent sections. Only cp-04c serves absence (a one-node family) | spec / ruling | **OPEN.** Either the collateral and covenant slots become optional with a declared treatment, or scenario 3 is rewritten as a refusal. Not this spec's to choose |
| `CP14-F-25` | **Spec: `as_of` and the children's instant are two clocks, and §B.4 names only one.** cp-05 pins the composite's `asked_at` at `2026-09-07T12:00:00+00:00` on any transport (`CP14-F-19`), while §D.3 scenarios 2 and 9 vary `as_of` historically. The SDK already separates them: `decision_instant_parameter` moves `decided_at` (TTL anchor, gate instant) and `temporal_boundary` stays `request.asked_at`. This product must declare `as_of` as its decision-instant parameter and hold `asked_at` at the children's instant. Consequence of the expiry-floor law (`D-IMPL-31`): composed over cp-05's four-hour TTL the memo expires at `2026-09-07T16:00:00+00:00` — past at any wall clock; it serves only because the TTL gate's *now* is `decided_at` | spec | **Adopt at the next revision, after `D-IMPL-340`:** §B.4 gains the sixth clock (`asked_at`, the children's instant); §B.2 declares `as_of` as `decision_instant_parameter`; the four-hour expiry is disclosed as an illustrative consequence (`D-IMPL-323`) |

**The §0.0 connection — closed by `D-IMPL-339`** (`D-GATE-339`, merged
`c635037f`). Re-measured on that `main`: `CompositionOutcome` still carries no
child (the view is a separate value, by design); `ProductSource` still has no
consumer; `verify_child_admission_provenance` still has no production caller —
the door is the walk's `TypeGuard`, now in `resolve_child_outcomes`; and the
three dead refusal tokens (`CP14-F-10`) are still unemitted. `CP14-F-10`
through `CP14-F-13` remain OPEN SDK findings, untouched by 338 and 339.

### F.3 Environment

Reads only, against the curated estate. Connection material from
`ccf_dataprep/.env`; **namespaces are NOT in `.env`** — `.env` names the v1
estate and this product reads v2:

```
CCF_CP_14_POSTGRES_DSN      (host/credentials from ccf_dataprep/.env)
CCF_CP_14_POSTGRES_SCHEMA=ccf_v2
CCF_CP_14_FLUREE_URL=http://192.168.4.76:8090
CCF_CP_14_FLUREE_LEDGER=fibo-v2
CCF_CP_14_MONGO_URI=mongodb://192.168.4.76:27017
CCF_CP_14_MONGO_DB=fibo_v2
```

Never committed. Tests read the same estate and seed nothing; assertions are
relationships and identities, never pinned counts.

### F.4 `[TBC — this build]`

| Item | Section | Owner |
| --- | --- | --- |
| p95 latency budget per step | §D.1 | this build, P6 |
| `payload_hash` for each §D.3 scenario | §D.3, §D.4 | this build, P6 |
| Gate fixture ids and sabotage observations | §D.5 | this build, P7 |
| **Whether any obligor's COMPUTED debt lands in `(0.25, 0.30]`** — `CMC-G07`'s divergence condition | §D.6 | this build, P6 |
| **Two children weak on DIFFERENT factors** — `CMC-G19`'s divergence condition | §D.6 | this build, P6 |
| The five children's exact `schema_name` and version floors | §B.7 | this build, P5 |
| Final materialization posture confirmation | §E.4 | this build, P8 |
| Measured cost band against the ×8–15 estimate | front matter | this build, P8 |

---

## G · Operate & govern

**Accountable owner:** credit-risk product engineering.
**Second line:** model risk has **no** registration obligation here — Mode 1,
no model in the trust path — ruled, §0.4 item 1.

**SLOs.** Availability follows the weakest store, and the served expiry follows
the stalest child. p95 `[TBC — this build]`. Degradation is **fail-closed,
never degraded-serve**: a memo substrate that quietly drops a leg is the
failure the product exists to prevent.

**Observability.** Per request: `policy_version`, `graph_snapshot_at`, the
computed F/C/S triple and `D_c`, the four diagnostic components, the tolerance
in force **and its source**, the serve/refuse determination, per-section
evidence counts, and the five child rows with their acquisition kind and
eligibility basis. **The divergence between computed and stored debt is logged
every request**, because that divergence is the signal that the estate's table
has moved.

**Retention.** Replay records per the fabric's policy. The payload carries no
MNPI and no personal data beyond entity-level reference.

### G.1 Acceptance criteria — phrased so they can fail

1. The §A.1 counterfactual procedure runs on **CION** and **B&G Foods** and produces named unevaluable sections, not missing keys — and the CION guard fires on an **empty-string** `sic`, not on `NULL`.
2. Scenario 2 shows the serve/refuse boundary moving with `as_of` across 2025-07-01, with **Thermon at 0.3003** as the named boundary specimen.
3. Scenario 4 reports the diagnostic comparison against the dated **2026-08-22** snapshot, carrying that date and its provenance, with the divergence and its direction named in the payload — **asserting that the comparison was made and reported, never that the two must differ**.
4. Every one of `CMC-G01`…`CMC-G29` has an executing test whose docstring names its id, and every one is observed **red** under a sabotage of the mechanism it names.
5. No code path reads `memo_context_debt` as a source (`CMC-G04`).
6. Composition is performed by the shipped surface, and no local substitute for child resolution, admission, inherited-debt composition or per-child replay exists anywhere under `examples/cp-14-credit-memo-context/` (`CMC-G23`).
7. The registered class declares **only this product's own six operators**; the served lineage is the union with the children's (`CMC-G02`).
8. `make example-cp-14` runs from a cold shell, from the README, with no parameter required.
9. Every SDK finding `CP14-F-09`…`CP14-F-13` is reported upstream and **none is worked around in the example**; `CP14-F-09` is repaired under its own entry, `D-IMPL-338`.
10. **Scenario 10 passes** — the parent's payload changes because it read a different valid version of one child, and the parent then reconstructs from retained artifacts with no second provider call (`CMC-G28`, `CMC-G29`).
11. **No child-owned material is re-derived by this product's plan** (`CMC-G27`, §B.8).
12. **`C` and `S` have a real per-request input path from child evidence.** The per-factor minimum composes the children's *assessed* factors; the parent's own `C` additionally reads `legs_present` from the **admitted child contracts**, not from a source re-query (§E.2.1). A `legs_present` derived from the estate rather than from the children is the §B.8 defect wearing a debt-shaped mask.

### G.2 Catalog contribution

At Gate 2, return to the vault: the TRAP 1 staleness finding with its
two-counter localization, the TRAP 3 orphan and its inconsistent marker, the
`inherited_prerequisite_debt` sourcing result, and the Fluree grouped-`COUNT`
instrument failure — each as a `finding` with `measured_against` and
`reproduce_with`, per `CLAUDE.md` §11.

---

## H · Gate-1 summary — what is ruled, and what needs Dave

**Seven decisions remain RULED and are unchanged** (§0.4): Mode 1;
multiplicative debt; the historical table as comparison only; CION as the real
cascade; similarity within the permitted corpus; ECOA recorded and inert;
composition supplied by the SDK.

**The five children, all required.** `obligor-financial-spread` ·
`corporate-family-tree` · `credit-exposure-rollup` ·
`collateral-and-setoff-coverage` · `covenant-cross-reference`. No Relationship,
Peer or Filing rung is introduced. **A required child may legitimately report
absent data — and may legitimately refuse.** The composite honors whichever it
does, and the SDK makes wrapping a refusal as a served empty product
unspellable.

### H.1 · The missing connection — the proposal, as ruled and as built

**IMPLEMENTED as `D-IMPL-339` (`D-GATE-339`, `c635037f`).** What follows is the
proposal as it was put to Dave, kept as the record. As built, its three open
sub-questions were settled by the ruling: the plan receives the admitted
children's read-only contracts, no invented graph view; a known blocking
outcome refuses before projection; a payload computed before a later refusal is
provisional and never served. The binder stays between plan construction and
execution. The proposal's claim that the hoist *"crosses nothing that can
raise"* was withdrawn — called functions can fail without a literal `raise` —
and the changed order was tested rather than assumed. Line numbers in the block
below are as measured at `bff2ff17`.

#### Question 1 — can an existing supported interface supply the already-acquired, already-admitted child contracts to the parent's computation?

**No.** Four candidates were checked and each is ruled out on a stated ground.

| Candidate | Why it cannot carry this |
| --- | --- |
| **`ProductSource` / `mount_product_source`** — *"the tier-2 read path: an admitted Context Product as a queryable source"*, answering the same `GraphReader` every substrate answers, and attached to whitepaper §6.6, the recursive context-enrichment case | **The right conceptual seam, wrong on three counts.** (a) It accepts only `AdmittedProduct`, the type `PeeringAdmissionGate.admit` alone mints — a composite's `AdmittedChild` comes from a different gate. (b) It requires the payload to carry a top-level `graph_state` mapping of `EntityRecord` / `RelationshipRecord`; CP-14's children do not emit that shape. (c) Even with both solved, a source must be mounted **before** the plan is built, and composition runs after. Separately measured: it has **zero consumers** anywhere in `src/`, `runtime/` or `examples/` |
| **`plan_factory`** | Receives exactly `required: tuple[str, ...]` and `request: ProductRequest`. There is no parameter through which a child could arrive |
| **`CompositionOutcome`** | Six fields — `factors`, `resolutions`, `refusal`, `lineage`, `expires_at`, `admitted_operators`. **None is the admitted children.** The contracts are dropped at the composition boundary |
| **A second projection pass** | None exists. The plan is built at `resolver.py::GovernedResolver.__call__`, executed at `:1889`, and nothing re-enters projection after composition at `:1983` |

#### Question 2 — the smallest additive change

**Split the existing composite block at a seam it already has, and hoist only
the first half.** Composition does two separable things, and only the second
depends on the projection:

| Half | Needs | Depends on the projection? |
| --- | --- | --- |
| **Acquire + admit** — the `self.composite_children(...)` call | `requirements`, `asked_at`, `admitted_at`, `composition_invocation`, `consumer_lineage` | **No** |
| **Compose** — `compose_children(...)` | the above **plus `own_factors`**, from the debt scorer, which reads `execution.view` | **Yes** |

So:

```
acquire + admit children          <- hoisted above the plan
    -> plan_factory receives the admitted children
    -> projection builds the parent payload, reading child CONTENT
    -> compose_children(...)      <- UNCHANGED, same admitted instances
    -> gates, tolerance, replay   <- UNCHANGED
```

**Acquired once, used twice.** One `composite_children(...)` call; its result
is passed to the plan factory for content and to `compose_children` for
governing evidence. No second dispatch, no second admission, no second
content address.

**Measured preconditions, so the size of the change is not a guess:**

- **The hoist crosses no early exit.** Nothing between `:1878` and `:1983`
  returns, refuses or raises — verified. The two early exits in the enclosing
  block are both *above* `:1878` and would still run before any child is
  dispatched.
- **Three bindings move with it and none depends on the projection:**
  `policy_version` (`:1921`, reads a Control Plane pin), `own_lineage`
  (`:1948`, built from the declaration's `required`, the policy version and
  `request.asked_at`), and `invocation` / `admitted_at` (`:1958`, `:1962`).
- **`assessed` stays where it is** (`:1926`), because it reads `execution.view`
  — and so `compose_children` stays at `:1983`.

**The surface change, stated minimally.** `ProjectionPlanFactoryProtocol.__call__`
gains one optional keyword carrying a read-only view of the admitted children,
defaulted so every non-composite plan factory shipped to date is unaffected.
The resolver hoists the acquisition call and passes the same value to both
consumers.

**What this change explicitly does NOT introduce**, because the instruction is
that none of it belongs here: no generic memo logic; no scheduler (parallel
child invocation stays the harness's); no new authorization layer (the grant is
the authorization); no new provenance framework (`AdmittedChild` is already
token-guarded and `D-IMPL-337` already verifies it at the one door); no new
gate; no change to `run_gates`, to the four composition laws, or to the replay
record.

**Who owns what.** The SDK exposes the admitted child **contracts**. **CP-14
owns the product-specific mapping** from those contracts into memo sections,
in its own named `plan_factory` — never a lambda, per `D-IMPL-137` row C.

**Open sub-questions this proposal does not decide**, and should not:

1. Whether the plan factory receives the `AdmittedChild` values themselves or a
   narrowed read-only view exposing `.contract` alone.
2. Whether a child acquired for content but *later refused* at composition must
   invalidate a payload already built from it — the ordering makes this
   reachable, and it needs a rule.
3. Whether an early refusal that now follows acquisition should be moved above
   it, to avoid dispatching children for a request that refuses regardless.

### What was resolved — no ruling item remains

- **The §0.0 connection** — `D-IMPL-339`, merged at `c635037f`. Required
  behavior is supported; `CMC-G28` / `CMC-G29` are executable.
- **`CP14-F-09`** — `D-IMPL-338`, merged at `4c77cc60`. Child rows on every
  refusal after acquisition.
- **The hold release, on the record** — its scope is recorded in
  `D-IMPL-339`'s decision entry and in `D-GATE-338` / `D-GATE-339`.
- **Item attribution — RULED** (§0.8): the derived `section` label is
  ingestion metadata and authorizes no *"Item 7"* / *"Item 1A"* claim.
- **Gate 1 — APPROVED, 2026-09-14.** Gate 2 is GO from `main` at `c635037f`.

### What this revision changed

Fourteen measured falsehoods corrected; one correction of my own retracted
(the `194`/`209` scope, §0.6); three gates repaired or replaced for
unfalsifiability; ten gates added for the composition surface and the
content-composition proof; three new
estate traps; five new SDK findings; and §0.0 restated as a missing SDK
connection with the requirement intact, with §H.1's focused interface proposal
attached.
Every figure was measured on 2026-09-14 against the live estate, and every
load-bearing figure was measured twice, on two models, blind to each other.

**Gate 2 is GO** (2026-09-14), on `cp-14-gate-2` from `main` at `c635037f`.
At this commit nothing is implemented yet; the first slice is the wiring §0.5
names — artifacts, catalog entries, grants, agent definition, policy bundle,
child-argument mapping, `GrantBoundChildResolver`, `CompositeAdmissionGate`,
the named child-aware plan factory and the child-aware scorer. No raw source
leg stands in for child content, and none will.
