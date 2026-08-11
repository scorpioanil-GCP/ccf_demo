# Context Product — decisions, defects and whitepaper deltas

**Status:** working record, 2026-08-10. Produced during Phase 16 wave 3, from
Dave's review of `examples/s1-01-hello-context-product`.

**Purpose.** Enumerate everything decided or discovered in that review, organized
so a whitepaper revision can be worked section by section. Three kinds of entry
appear below and they are deliberately not blended:

| Marker | Meaning |
| --- | --- |
| **RULED** | Dave's decision. Authority per CLAUDE.md §2. Already binding. |
| **MEASURED** | Checked against the tree at `b771468`. Evidence, not opinion. |
| **DERIVED** | Claude's interpretation of a ruling's consequence. **Needs Dave's confirmation** before it binds. |

---

## 1. What a Context Product is

### 1.1 The vessel model — **RULED**

> *"The true ContextProduct is nothing more than a vessel that has been assembled
> to represent a unique capability for the calling agent to consume. Kind of like
> MCP — a standard ContextProduct doesn't really need to subclass, it just needs
> to have certain operations and payloads which we have already determined via
> the whitepaper."*

A Context Product is **one standardised vessel**, not a class hierarchy. What
makes a vessel a `KYC_ContextProduct` is **how it was assembled**, not its type.
Class identity is data — a `schema_name` resolved through the Control Plane
registry — plus a **declared payload schema** the class registers.

**Whitepaper delta — §7.6.** The current wording is explicit about inheritance:

> *"The Contract base is the typed scaffold every per-product subclass inherits
> and extends; the per-product subclasses carry the domain-specific payload."*

This should be restated as vessel + declared payload schema. **DERIVED:** the
*intent* of that sentence — domain payload is typed, cross-cutting invariants
live once on the base — is preserved, not reversed. A declared JSON Schema
delivers a typed payload and keeps invariants on the base without Python
inheritance. Recommend recording it as a **wording correction**, not a change of
position, unless Dave reads it otherwise.

**Why the vessel is the stronger model** (arguments that survived scrutiny):

1. **Debt by construction.** Debt on the base vessel means every product carries
   it. Under subclassing every subclass is a place to forget — and *debt computed
   and discarded* is precisely the defect this review found.
2. **Language neutrality.** A subclass is a Python artifact. A product crossing
   A2A to a Java or TypeScript consumer cannot inherit a Pydantic class. CCF
   commits to federation across organizational boundaries; a Python-shaped type
   does not belong at that seam.
3. **No-Hardcoding (CLAUDE.md §6.4).** A `KYC_ContextProduct` class in code makes
   the product taxonomy code. `schema_name` plus a declared schema makes it
   configuration. *Code contains interpreters, never the things interpreted.*
4. **MEASURED — the code already works this way.** `schema_name` is documented
   verbatim as *"Class identity."* It is a string resolved through a registry.
   Subclassing would layer a hierarchy over a registry that already does the job.

**Where the MCP analogy stops — DERIVED.** MCP deliberately carries no governance
semantics; it is a capability and transport standard. A Context Product's reason
for existing is that it *does* carry governance — policy versions in force,
lineage that must strictly equal what ran, a freshness SLA, debt, and a replay
record that must exist before delivery. Accurate statement: **MCP-shaped in its
typing discipline, with a governance envelope MCP has no equivalent for.** Worth
saying explicitly in the revision so the analogy is not over-applied downstream.

### 1.2 The eight-element contract is shipping as five — **MEASURED**

§6.3 commits eight elements. Checked field by field against
`src/ccf/products/contract.py` and `RegisteredProductClass`:

| Element | Status |
| --- | --- |
| schema | present — `schema_name` |
| semantic versioning | present — `schema_version` |
| TTL | present — `expires_at`, `ttl_anchor`, `max_ttl_key` |
| policy binding | present — `lineage.policy_bundle_versions` |
| lineage | present — `ProductLineage` |
| **freshness SLA** | **absent** |
| **discovery** | **absent** |
| **addressability** | **absent** |

Worse than absent: `contract.py` states *"Freshness SLA, Discovery,
Addressability, and Assembly Mode are class-level registration properties…
`RegisteredProductClass` is where they live."* `RegisteredProductClass` carries
`schema_name`, `schema_version`, `ttl_anchor`, `assembly_mode`, `max_ttl_key`,
`max_ttl_version`, `accepted_policy_binding_modes`, `accepted_lineage_modes`.
**Of the four it claims, only `assembly_mode` is there.** The code documents
three committed elements as living somewhere they do not exist.

This is a fidelity defect against CLAUDE.md §1 success condition 1, not an
ergonomic gap.

### 1.3 The payload is unvalidated — **MEASURED**

`register_product_class(...)` accepts no payload schema, so `payload:
Mapping[str, Any]` is an unchecked dict. Under the vessel model this is the
substantive gap: the vessel's discipline *is* the declared schema, and there is
nowhere to declare one.

Machinery exists and is proven — the SDK already exports and validates declared
JSON Schemas for at least eight artifact classes (`ccf.agent-definition.json`,
`ccf.debt-profile.json`, `ccf.deployment-manifest.json`, …). It has simply never
been applied to product payloads.

---

## 2. Context Debt

### 2.1 Debt must reach the consuming agent — **RULED**

**MEASURED:** `DebtAssessment` — carrying `debt`, `signal`, and `factors`
(`freshness`, `completeness`, `semantic_consistency`) — is computed by
`ccf.halflife.debt`, exercised in five shipped examples, and appears on
**neither** `ContextProductContract` **nor** `DecisionReplayRecord`. It is
calculated and discarded.

Whitepaper §7.7.4–§7.7.8 makes `D_c` gate Forced LLM and Fail-Closed, so a
delivered product carrying no debt is a fidelity defect.

**The consequence that matters.** Five of the six axes reach the wire — `E`/`R`
as payload, `T` as `temporal_boundary`/`expires_at`/`ttl_anchor`, `P` as
`policy_bundle_versions`, `Π` as `plan_id`, `L` as
`operators_invoked`/`graph_snapshot_at`. The sixth signal — the one that says how
much to trust the other five — does not. An agent asking about Acme cannot tell
whether the ownership data was refreshed this morning or eighteen months ago.

### 2.2 Debt is constitutive, not an annotation — **RULED**

> *"Last time records were updated are one signal for sure, but other information
> that KYC is interested in together with the last record update is what makes the
> KYC_ContextProduct — it combines multiple signals into a comprehensive product
> that includes ContextDebt by design. It can work for any number of parameters
> that the product allows."*

Correcting an earlier Claude framing that treated debt as a per-entity annotation
on an answer. It is not. The product **is** the composite; debt is computed across
that composite by design, over whatever parameter set the class declares.

Dave's worked shape:

> *"The response for ACME could return something that stated the last time ACME
> key investor data was updated — or if an event had transpired with one of the
> key shareholders that should be considered by the consuming agent."*

**DERIVED:** that is two distinct signals, and neither is the existing scalar —
**recency** (per-subject last-observed, not a product-level average, since
averaging hides that Acme is 3 days old and Omega Securities 14 months) and
**salience** (a material event on a party in the chain, which can fire while
everything is perfectly fresh). Needs confirmation that both are in scope.

---

## 3. The assembler

### 3.1 The assembler is a Protocol — **RULED**

> *"The assembler, which I agree should be a Protocol, is what makes the
> ContextProduct a KYC_ContextProduct."*

Split confirmed: **Protocol for the producer, standardised vessel for the
produced.** The assembler is behaviour — where the data lives, how to reach it,
what to do with it for any request within the parameters it supports.

### 3.2 What the assembler owns — **RULED**

- It knows where its data lives and how to get it.
- It talks to the six backends directly, so that adapter work is not lost.
- It creates or uses **tools** to gather what else it needs.
- It may **enlist other agents** to produce content for inclusion — or stay
  wholly deterministic.
- It may keep its own KG in whichever of the six stores is simplest.
- The calling agent invokes the product, not an MCP server in front of a
  database; the orchestration mess is handled inside.

### 3.3 The archetype exists on paper only — **MEASURED**

CLAUDE.md §6.3 already commits `ContextAssemblyAgent`: *"assembler agent producing
Context Products for consumption by other agents… the recursive context enrichment
case."* **It does not exist in `src/`.** The producer side has a designated home
and the home is empty.

### 3.4 The assembler declaration as an artifact — **RULED (provisional)**

Dave: *"I think so"* — to the proposal that the assembler's declaration lives as
a versioned, content-hashed Control Plane artifact, with the Protocol
implementation as its interpreter.

**DERIVED consequence, needs confirmation:** a product's identity becomes
auditable. Replay answers not only *what it returned* but *what it was permitted
to consult* — which sources, which tools, which agents, and what freshness it
claimed it could promise.

### 3.5 Agent enlistment is constrained by Algorithmic ⇄ Semantic Alternation — **DERIVED**

§7.6.6 is a CI-enforced structural invariant: LLMs never see raw signal. So an
enlisted agent's output cannot drop straight into the payload — it re-enters
through an algorithmic stage, as acquired content rather than as payload. Part of
that seam exists: `ProjectionEngine.execute` already accepts
`recorded_acquisitions: tuple[AcquiredContent, ...]`.

Not a blocker; a shape constraint the revision should state, because the obvious
implementation violates it.

---

## 4. Aggregation

### 4.1 Products may aggregate products — **RULED (question posed and affirmed)**

**MEASURED:** more machinery exists than expected. `union_lineage` is implemented
in `src/ccf/peering/admission.py` for A2A admission, with a property test behind
it — *"the inbound lineage extends the consumer's by set-union: producer entries
survive."* Directly reusable for composition.

### 4.2 Three composition rules — **DERIVED**

1. **Lineage unions.** Already law, already tested. A composite's lineage is the
   union of its components', so every source signal stays resolvable.
2. **TTL floors.** A composite is no fresher than its stalest component:
   `expires_at = min(components)`. Mechanical.
3. **Freshness SLA becomes a bind-time refusal.** If a class declares a 24-hour
   SLA but a component can only offer 30 days, the composite cannot honour its own
   declaration — and that is checkable at **class registration**, before any
   product of that class exists. Same shape as the existing
   `refuse_operator_set_divergence` binder. This turns freshness from a runtime
   surprise into a structural refusal, and is the most valuable of the three.

**Debt composition is the open one.** It cannot be a max or a mean: components
matter differently to the decision, and stale adverse-media may be tolerable
where stale ownership is not. Likely resolution — the class declares which
components are decision-critical, and debt weights accordingly. **Not decided.**

### 4.3 Products may be front-ended by MCP servers — **RULED**

Already committed as whitepaper Pattern 3 and CLAUDE.md §7.1 (MCP as L6 egress),
and partially built. The shift the revision should make explicit: the MCP server
fronts a **product that assembles**, not a store that answers.

---

## 5. Deployment separation

### 5.1 Systems of record are read-only — **RULED** (recorded as `D-IMPL-95`)

> *"Create your own db so there is no collision — I want the existing stores to
> provide the proxy for the enterprise data stores. This is what the CCF reads
> (never updates or modifies). The CCF can use the same backend to store its own
> KG for the Context Product. Let's make sure we do not contaminate the source
> data."*

L1 reads the systems of record and never writes them. CCF's Context Graph is
CCF-owned, lives in a separate ledger or database **on the same substrate**, and
is written only through L2.

**DERIVED:** this is the complementary half of an invariant the project already
holds. CLAUDE.md §10 forbids anyone but L2 writing L3; this forbids L1 writing
the source at all. Together they make the fabric non-destructive to the
enterprise *by construction* — the property that decides whether an institution
can adopt it, since none grants a new platform write access to its book of
record. Whitepaper Ch 8 §8.3 Pattern 1 assumes non-destructive ingestion without
stating the prohibition; the revision should state it.

---

## 6. Scope discipline

### 6.1 "No fabric changed" is revoked — **RULED** (recorded as `D-IMPL-96`)

> *"The condition 'no fabric changed' needs to be revoked. It was established to
> prevent external adapters leaking into the core CCF product… And yes the fabric
> MUST change to do this the right way. Going forward I don't want to use the 'not
> fabric change' because it has been used out of context."*

**The failure mode, worth recording so it does not recur.** The rule was sound as
*anti-leakage* — keep substrate adapters, harness bindings and domain values out
of the core, which four CI lints already enforce. What it became was *"do not
change anything,"* policed by a `git diff --stat` that cannot distinguish an
adapter leaking in from a genuine defect being fixed. A diff-based gate measures
**volume**; the invariant it stood in for is about **direction**. Once those
diverge the cheap proxy wins, because it is the mechanically checkable one.

The tell was visible in hindsight: the phase had to build bespoke escape hatches
— an enumerated docstring exception, a two-limb bookkeeping bound, an allowlist
of one symbol in one file — for correct work to proceed. **A constraint needing
carve-outs to permit correct work is measuring the wrong thing.**

Withdrawn with it: `D-13`'s carve-out, `D-14`'s two-limb bound, plan 16-19's
`gate_16.py` allowlist. Work committed under them stands.

---

## 7. Assembled, not aggregated

### 7.1 The example contradicts the whitepaper's own thesis — **MEASURED**

`examples/s1-01-hello-context-product` pins three literals in artifacts:

```yaml
subject_entity_ref: "http://example.org/fibo/AcmeCorp"   # ubo-question.yaml
temporal_boundary:  2026-08-01T00:00:00Z                 # decision.yaml
now:                2026-08-01T00:05:00Z                 # decision.yaml
```

One company, one frozen instant, one answer. Against Chapter 1:

> *"Assembled at decision time, not precomputed against design-time queries… the
> specific composition of those sources depends on the client, the ask, and the
> moment. **It is not knowable at design time; it is shaped by the decision.**"*

> *"The difference between the two is the difference between the verb **aggregate**
> and the verb **assemble**."*

By the whitepaper's own vocabulary the example aggregates. It does not assemble.

### 7.2 The as-of mechanism is right; its use is wrong — **DERIVED**

Worth defending narrowly in the revision, because the fix should not overshoot.
The engine reads no clock, deliberately: the caller passes `now` at serve time and
the *original* boundary at replay time, and the same code path yields the same
answer. If the fabric read a clock internally, replay would be impossible. **The
caller supplying the instant is correct design; the instant being a literal in a
YAML file is the defect.**

### 7.3 The example does not pin which question it answered — **MEASURED**

`serve()` is called with no `query_pin_writer` and no `executed_queries`, so it
sits on the pre-15.2-08 default posture. Dimension 5's `graph_query_sequence`
exists precisely to pin one `content_hash` per issued `GraphQuery`, with canonical
bytes persisted by `QueryPinWriter` — the mechanism that makes a **runtime**
subject fully replayable. It is built and unused.

---

## 8. Smaller defects found on the way — **MEASURED**

| # | Defect | Status |
| --- | --- | --- |
| 1 | `DeploymentBinding` — a Protocol the example invented, calls *"the adoption checklist"*, and CCF does not ship. All eight examples call `load_and_boot` identically; seven differ only in a filename. It abstracts over a call that was already uniform | open, fix is deletion |
| 2 | `spine.py` opens by explaining its role in the docs architecture, never stating what the program does — so it reads as purposeless without the README | open |
| 3 | Retirement sweep read gitignored paths; 301 of 509 rows came from `.pytest_cache`, making the inventory a function of the last pytest run | **fixed** at `b9cfe27` |
| 4 | Neo4j and PostgreSQL source loaders silently dropped per-edge `ownershipPercent` | **fixed**, verified 16 rels / 9 percentages on all three |
| 5 | Fluree has no loader at all — `fluree_to_mongo.py` is export-only. Not a missing line: RDF has nowhere to hang a qualifier on a triple, which is *why* the source modelled `ownershipPercent` on the Party. CCF's own adapter solves it with interposed-edge reification | open |
| 6 | `compare_backends.py` reports owner/company pairs only, so it cannot distinguish a faithful mirror from a lossy one — which is why a full load cycle passed while three of four stores dropped the percentage | open (Dave's harness) |

---

## 9. Open questions requiring Dave's ruling

1. **Debt's shape on the wire** — scalar, per-factor, per-subject, or per-claim;
   and whether recency and salience are two fields or one composite.
2. **Where debt lands** — `ContextProductContract`, `DecisionReplayRecord`, or
   both, and what replay determinism requires of each.
3. **What "a material event transpired" means mechanically**, without encoding
   domain values in the core. This is the hardest line in the whole design.
4. **Whether the three validation gates become four** (payload-against-declared-schema),
   or whether that binds at class registration instead.
5. **Whether the assembler Protocol lands as the `ContextAssemblyAgent`
   archetype** — building an archetype committed since §6.3 and never built.
6. **Whether the request surface is a typed request contract per class** —
   Dave's *"company name and top investors above 25%"*. This is what makes a
   product **callable** rather than configurable, and it is what turns the fixed
   subject and fixed instant into runtime arguments.
7. **Debt composition weighting** for aggregate products (§4.2).
8. **Sequencing** — whether this runs as a Phase D mini-cycle now, before Phase 16
   waves 4–12 document the fabric, or after.

---

## 10. Whitepaper sections the revision touches

| Section | Change |
| --- | --- |
| Ch 1 (assemble vs aggregate) | no change — it already states the thesis the implementation drifted from; possibly cite it as the governing test |
| Ch 6 §6.3 (eight-element contract) | freshness SLA / discovery / addressability need to be stated as *instance-or-class* explicitly, since the implementation lost them in the gap |
| Ch 7 §7.6 (Products as Delivery) | **subclass → vessel + declared payload schema**; state the MCP-shaped-but-governed framing; state that payload validation is by declared schema |
| Ch 7 §7.6.6 (Alternation) | state the constraint on enlisted-agent content — acquired content, not payload |
| Ch 7 §7.7 (Debt / Half-life) | debt is **delivered**, not only computed; constitutive of the product; recency and salience |
| Ch 7 §7.10 (Decision Replay) | whether debt is recorded as well as delivered |
| Ch 8 §8.3 Pattern 1 (CDC→G) | state the L1-read-only prohibition explicitly (`D-IMPL-95`) |
| Ch 8 §8.3 Pattern 3 (MCP) | MCP fronts a product that assembles, not a store that answers |
| New or extended | product aggregation: lineage union, TTL floor, freshness-SLA bind-time refusal, debt composition |
| New or extended | the assembler: Protocol, declared as an artifact, owns sources/tools/agents/KG placement |
