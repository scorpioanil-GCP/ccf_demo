# Context Product Ruling Evidence — measured costs for Q1–Q8

**This document is evidence, not a proposal.** It costs the eight options
already in front of Dave in `docs/CONTEXT_PRODUCT_REVISION.md` §9 and
`.planning/phases/15.5-…/15.5-RESEARCH.md` § Open Questions, and it adds nothing
new to decide. No option here is recommended, ranked, defaulted or preferred —
the document deliberately declines to do that, and the only sentence in it
containing that word is this one.

Every figure below was **measured against this tree** at `3df4e91`
(`chore(15.5): mark phase execution started`), by
`tests/spikes/test_contract_field_addition_cost.py`. Nothing here is a grep
estimate, a projection, or an inference from a docstring. Where a cost could
not be measured, the cell says so and names why; **no cell is blank**.

**Measured:** 2026-08-11. **Plan:** `15.5-01`.

---

## How to read the Measured Cost column

| Marker | Meaning |
|---|---|
| a number | counted by AST walk or read off a benchmark result file |
| a hash | an observed `content_hash` of a stand-in the spike module owns |
| **NOT MEASURABLE** | the surface the cost would land on does not exist yet; the cell names what would have to exist first |

**Call-site counts are AST call-site counts, not `grep -rl` file counts.** A
module that constructs the same type nine times is nine repair sites. The walk
covers `src/`, `runtime/`, `tests/`, `perf/`, `examples/` and `tools/`,
excluding `.venv`, `__pycache__` and `tests/spikes/` (the instrument does not
count itself).

### The blast-radius baseline every Q1–Q8 cost is quoted against

| Symbol | Call sites | Distinct files |
|---|---:|---:|
| `ContextProductContract` | **42** | 38 |
| `ProductLineage` | **50** | 42 |
| `run_gates` | **43** | 22 |
| `build_replay_record` | **31** | 27 |
| `register_product_class` | **29** | 26 |
| `Perspective` | **26** | 24 |
| `serve(` — the governed delivery seam, bare-name calls only | **18** | 12 |
| `DebtFactors` | 11 | 8 |
| `union_lineage` | 10 | 3 |
| `assess_debt` | 9 | 3 |
| `DebtAssessment` | 6 | 6 |
| `def rehydrate_product` — **implementations**, not calls | **7** | 6 |
| `build_egress_server` | 2 | 2 |

`ContextProductContract`'s 42 sites break down as: 13 in `examples/`
(every one of `00`–`08`, `s1-01`, and `examples/external`), 26 in `tests/`
(7 in `tests/replay`, 4 in `tests/peering`, 3 in `tests/gates`, 2 each in
`tests/crossproc/servers`, `tests/http_api`, `tests/workflow`, and 1 each in
`tests/agents`, `tests/conformance`, `tests/examples`, `tests/hitl`,
`tests/integration`, `tests/products`), and 3 in `perf/suites/`.

RESEARCH.md assumption **A2** — that only a *required-with-no-default* field
breaks those sites — is discharged in the affirmative by the second limb below.

### The sentinel alternative is intact (asserted, not merely observed)

All five shipped positive-sentinel defaults named in `15.5-PATTERNS.md`
§ Pattern 9 still exist and are still defaults, asserted by the spike module:

| Sentinel | Default of | Value |
|---|---|---|
| `MODE_1_MODEL_VERSION` | `ModelVersionRecord.model_version` | `"none"` |
| `NO_HITL_ACTIONS` | `PolicyBindingsSnapshot.hitl_actions` | `"no-hitl-actions"` |
| `NO_GRAPH_QUERIES` | `ContentGenerationPath.graph_query_sequence` | `()` |
| — | `ContextFabricSnapshot.source_attestation` | `None` |
| — (15.2-08) | `serve(query_pin_writer=…, executed_queries=…)` | `None`, `()` |

**Consequence for every field question below (Q1, Q2, Q3, Q8):** a field added
with a positive sentinel default costs **0 of the 42 `ContextProductContract`
call sites**; the same field added as required-with-no-default costs **42**.
That is the single number the field-addition strategy turns on, and it is the
same number for every question that adds a field.

---

## Q1 — Is the request surface a typed request contract per product class? *(gating)*

Whitepaper backing, quoted rather than paraphrased
(`docs/CCF_Whitepaper_1-2.md:1465`): *"Addressability gives every product a
well-defined interface the agent queries with intent, role, and freshness
parameters… the address pattern
`/context-products/credit-risk/counterparty/{counterparty-id}?intent=lending-decision&freshness=intraday`
encodes exactly what the agent needs."* And: *"Structured queries enable
decision-time assembly rather than pre-aggregated retrieval."*

| Option | Consequence (from RESEARCH) | **Measured Cost** |
|---|---|---|
| **(a)** Typed request contract per class, declared as a Control Plane artifact in the `SkillArgumentSchema` shape | Collapses the fixed-subject and fixed-instant defects into one design; makes a product **callable**; gives Discovery a capability manifest to publish and Addressability a realization | One new artifact class + one new `docs/schemas/*.json` (bytes-equality drift gate, `Makefile:253`); the declaration threads through **29** `register_product_class` call sites across 26 files and **18** governed `serve(` sites across 12 files; door-side validation lands on the **3** delivery paths enumerated under Q3. Payload-schema nesting cost is Q5's table, measured. Adds **0** `ContextProductContract` call-site repairs if the request surface stays off the vessel. |
| **(b)** No request contract; subject and instant become explicit parameters of the existing serve path | Much smaller; fixes the two literals but leaves the product configurable rather than callable, and leaves Discovery and Addressability with nothing to declare | **18** governed `serve(` sites across 12 files, of which **9** are in `examples/` across 8 files (`00`, `01`, `02`, `06`×2, `07`, `08`, `external/00`, `s1-01`). Zero new artifact classes, zero committed-schema regeneration. Whitepaper §6.3 Discovery (`:1463`) and Addressability (`:1465`) remain unrepresented in code, which is 2 of the 3 elements `docs/CONTEXT_PRODUCT_REVISION.md` §1.2 measured as absent. |
| **(c)** Defer the contract; add the parameters now, formalize in Phase 17 | Two patches instead of one design | (b)'s **18** sites now, plus (a)'s full population again later. The two populations overlap at the 12 `serve(` files, so those 12 files are edited twice. |

**Sub-question if (a):** does the request schema reuse `SkillArgumentSchema`
(one level deep, by ruling) or need nesting? That is Q5's table, and its costs
are measured there.

---

## Q2 — Debt's shape on the wire

| Option | Consequence (from RESEARCH) | **Measured Cost** |
|---|---|---|
| **Scalar `D_c` only** | Cheapest; loses which of F/C/S collapsed, which `DebtAssessment`'s own docstring argues against | One `Decimal` field, wherever Q3 puts it. Q3's placement cost is the whole cost; the shape adds nothing. |
| **Per-factor** (the shipped `DebtAssessment`: `debt` + `signal` + F/C/S) | Free — the type exists and is already `Decimal`-safe for replay | The type already ships (`src/ccf/halflife/assessment.py::DebtAssessment`) with **6** construction sites in 6 files and **9** `assess_debt` sites in 3 files. Adding it to a contract costs Q3's placement cost and **0** new type work. |
| **Per-subject recency** in addition | Expresses Dave's Acme case | **NOT MEASURABLE from this tree** — no per-entity last-observed structure exists to count against. `Observation` (`src/ccf/halflife/decay.py::Observation`) carried `(observation_type, observed_at)` and **no entity identity** when this was measured, so the per-subject key did not exist anywhere on the debt path. (Closed later: plan `15.6-05` added the optional `subject` identity under `D-IMPL-120`. The measurement stands as the record of what was true at ruling time; the line-anchored citation is re-cited by symbol per `DI-15.5-08`.) This is the same missing link A3 reports under Q4; building it is a precondition, and its cost is Q4 option (c)'s cost. |
| **Per-claim** | Maximum fidelity, maximum size | **NOT MEASURABLE from this tree** — same missing link as per-subject, at finer grain. |

**Sub-question — are recency and salience one field or two?** Mechanically
distinct and measured as such: recency is computable today by
`FreshnessScorer.score(observations, *, now)`
(`src/ccf/halflife/debt.py::FreshnessScorer`, signature measured); salience has **no
producer anywhere in `src/` or `runtime/`** — see Q4.

---

## Q3 — Where does debt land?

**This is the section the hard determinism constraint governs.**
`ReplayEnvironment.rehydrate_product`
(`src/ccf/replay/engine.py::ReplayEnvironment.rehydrate_product`)
rebuilds the delivered product from `(record, re-executed projection)`, and the
engine hash-checks the result inside `src/ccf/replay/engine.py::replay`, raising
`ReplayDivergence`. `ProjectionOutput` carries exactly `plan_id` and `payload`
(`src/ccf/projection/plan.py::ProjectionOutput`).

**Measured baseline content address of the spike's stand-in vessel:**
`14217148e333aee2004640a66f5bdcfff609cbd808753c49ce9fa94af6c50372`.

**Measured tripwire result at `3df4e91`, before any change:**
`pytest tests/replay/test_engine_rehydration.py -q` → **13 passed in 1.07s**,
exit code 0. That is the baseline the placements are read against.

### The three delivery paths — enumerated because criterion 1 says *no delivery path drops it*

A ruling priced against one door understates the cost by two. All three
serialize `servable.product`, and **none of them touches
`ServedProduct.replay_ref`** — measured by reading all three:

| # | Path | `file:line` | What it serializes |
|---|---|---|---|
| 1 | Fabric-internal MCP egress resource | `runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol` | `canonical_bytes(servable.product)` |
| 2 | HTTP API `retrieve` route | `runtime/ccf_runtime/http_api/routes/product.py::build_router` | `canonical_response(servable.product)` |
| 3 | **External front door** — Experience server `context_product` resource | `runtime/ccf_runtime/mcp/experience.py::build_experience_server` | `canonical_bytes(servable.product)` |

Paths 1 and 3 carry the identical three-string signature
`context_product(tenant, product_class, version)` and the identical body. Path 3
is the surface external agent runtimes reach the fabric through, which is why
pricing against path 1 alone is the specific error this table exists to prevent.

### The four placements, priced against all three paths

| Option | Viable? | **Measured Cost** | Reaches path 1 (MCP egress) | Reaches path 2 (HTTP) | Reaches path 3 (external MCP) | Reaches in-process callers |
|---|---|---|---|---|---|---|
| **Product only** | **NO — not viable** | **Observed hash divergence:** the stand-in vessel carrying a `Decimal` debt field hashes to `012f542e…f4f4904` against the baseline `14217148…c50372`. `canonical_bytes` walks a model field-by-field over `type(value).model_fields` (`src/ccf/contracts/canonical.py:102-111`), so the field is in the bytes and therefore in the address. The record carries nothing to reconstruct it from, so all **7** `rehydrate_product` implementations across 6 files would return a product the engine's check rejects. **Not an inference — the divergence is the observed measurement.** | yes | yes | yes | yes |
| **Replay record only** | yes | Product address **unchanged** (`14217148…c50372`, observed). **0** of the 42 `ContextProductContract` sites move; **0** recorded example expectations move; the tripwire's 13 tests stay green as measured. Cost lands on `DecisionReplayRecord` and on the **31** `build_replay_record` sites across 27 files, or on **0** of them under a positive sentinel default. Fails ROADMAP criterion 1 and whitepaper `:2696`. | no | no | no | no |
| **Both** | yes | Address moves exactly as product-only (`012f542e…f4f4904`, observed) **and is reconstructible**: a rehydrator reading debt back off the record reproduces the identical bytes (observed equality). Cost = product-only's address move **plus** record-only's record work **plus** a signature change to `ReplayEnvironment.rehydrate_product`, a public Protocol with **7** implementations in 6 files (`src/ccf/replay/engine.py`, `tests/replay/test_engine_rehydration.py`, `tests/replay/test_query_sequence_pin.py`, `perf/suites/replay/conftest.py`, `examples/06-decision-replay/run.py`, `examples/external/00-hello-context/run.py`) — plus a `docs/surface-changes/` fragment. | yes | yes | yes | yes |
| **`ServedProduct` beside the product** *(see note)* | yes | Product address **unchanged** (`14217148…c50372`, observed). `ServedProduct` has exactly **1** construction site (`src/ccf/replay/serve.py`, inside `DeliveryCapability.deliver`), so the whole change is one type and one line. **0** content addresses, A2A signatures or recorded example expectations move. **The measured cost is what it does not reach:** none of the three delivery paths serializes `ServedProduct`, so debt reaches **0 of 3** wire consumers. The population it *does* reach is the **18** governed `serve(` call sites across 12 files, of which **9** are in `examples/` across 8 files. | **no** | **no** | **no** | yes (18 sites) |

**Note on the fourth option.** It was **derived during research from the tree
and is absent from `docs/CONTEXT_PRODUCT_REVISION.md` §9**, whose enumeration
offers only product / record / both. It is recorded here as an option that
exists, with its cost measured, and with no preference expressed.

---

## Q4 — What does "a material event transpired" mean mechanically, without domain values in the core?

| Option | Consequence (from RESEARCH) | **Measured Cost** |
|---|---|---|
| **(a)** Opaque salience identifiers declared per class, compared structurally, never interpreted | The shipped `SkillRequirements` precedent (D-IMPL-29) | One declaration field on the product class or the debt profile; the fabric compares strings. `register_product_class` has **29** call sites / 26 files, or **0** under a default. No new producer needed — the deployment supplies the identifiers. |
| **(b)** A `SalienceScorerProtocol` alongside `DebtFactorScorerProtocol` | Consistent with D-IMPL-47's pattern for C and S | One new Protocol beside the shipped one (`src/ccf/halflife/debt.py::FreshnessScorer`, which already carries `scorer_id`/`scorer_version` for replay pinning). **No reference implementation ships for C or S today**, so a third unimplemented scorer is consistent with the tree; the reference example must supply one. Touches **0** existing `assess_debt` call sites if the factor is optional. |
| **(c)** Supersession-as-Policy-event, reusing the §7.7 mechanism | Most whitepaper-faithful | **This option is larger than it looks, and the missing link is now named.** See below. |
| **(d)** Defer salience entirely to Phase 17; ship recency only | Halves the debt work | **0** — recency is already computable by `FreshnessScorer.score`, whose signature was read: `(self, observations: Sequence[Observation], *, now: datetime) -> Decimal`. |

### A3 discharged — supersession is **not** reachable from the debt computation path

RESEARCH.md rated A3 MEDIUM-HIGH and explicitly did not trace it. Traced now:

| Measurement | Value |
|---|---|
| Verdict | **No — not reachable** |
| The missing link | `src/ccf/halflife/decay.py::Observation` — carried exactly `("observation_type", "observed_at")` when measured. **No claim id, no entity URI, no join key.** (Closed later by plan `15.6-05`'s optional `subject` under `D-IMPL-120`.) |
| The consumer that would need it | `src/ccf/halflife/debt.py::FreshnessScorer` — `FreshnessScorer.score(self, observations: Sequence[Observation], *, now: datetime) -> Decimal` |
| Where supersession actually lives | `src/ccf/graph/protocols.py::EntityRecord` and `src/ccf/graph/protocols.py::RelationshipRecord` — `superseded_by` / `superseded_at` on each. (This row named `ClaimRecord`; `git log -S` confirms no such class has ever existed in that module, so the type name was wrong when written while the cited lines were right.) |
| Occurrences of `supersed` in `src/ccf/halflife/` | **0** |
| Occurrences in `src/ccf/projection/` | **0** |
| Occurrences in `src/ccf/products/` | **0** |
| Occurrences in `src/ccf/graph/` | 348 |
| `Observation(...)` constructor call sites in `src/` or `runtime/` | **0** — no SDK code constructs one at all |

**Measured cost of option (c):** an identity field on `Observation` (or a
parallel event sequence beside it), **plus** a producer that reads
`superseded_by` / `superseded_at` off the graph and joins the two, **plus** a
way for that producer to reach the debt path — none of which exists. It is not
a wiring task.

**This verdict is reported, not asserted, in the spike module**, because plan
`15.5-11` task 1 edits `src/ccf/halflife/debt.py` under whatever Q4 ruling
lands. If Q4 rules supersession in scope, `15.5-11` makes the link exist —
correct work that an asserted "not reachable" would turn red. The verdict has
to survive here, in the evidence, not in a gate.

---

## Q5 — Payload validation: a fourth gate, or a bind at class registration?

| Option | Consequence (from RESEARCH) | **Measured Cost** |
|---|---|---|
| **(a)** A fourth validation gate in `run_gates` | Follows the shipped additive-gate posture; every product checked on the governed path | `run_gates` has **43** call sites across 22 files, but the `source_attestation` precedent (`src/ccf/products/gates.py::run_gates`, keyword-only, `None`-passes) means a keyword-only defaulted parameter moves **0** of them. Serve-time cost lands on the three `test_gates.py` micro benchmarks — margins measured below. |
| **(b)** A bind at class registration | Cheaper at serve time; validates a capability, not an instance | **29** `register_product_class` call sites / 26 files, or **0** under a default (the `accepted_policy_binding_modes` precedent on `src/ccf/products/contract.py::RegisteredProductClass` is exactly this). **0** serve-time benchmark cost. |
| **(c)** Both | Registration catches misconfiguration at wiring time; the gate catches drift at serve time | The sum of (a) and (b): **0** forced call-site repairs under defaults on both sides, and (a)'s serve-time benchmark cost. |

### The unavoidable sub-question — one-level schema vs. the reference payload

`SkillArgumentProperty` declares `("type", "description")`;
`SkillArgumentSchema` declares `("properties", "required")`. Depth is **1**, by
ruling at `src/ccf/skills/catalog.py::SkillArgumentSchema`.

| Branch | **Measured Cost** |
|---|---|
| **(i)** Extend `SkillArgumentProperty` with an `items` / nested-`properties` slot | **3** `to_input_schema()` call sites move (`src/ccf/skills/toolsurface.py`, `tests/skills/test_catalog.py`, `tests/skills/test_tool_surface.py`); **9** files mention `argument_schema` and are in the blast radius (the three harness adapters `adk`/`claude_agent`/`langgraph`, `cli/commands/skill_import.py`, `src/ccf/skills/catalog.py`, `src/ccf/skills/toolsurface.py`, and 3 test modules); **1** committed schema regenerates (`docs/schemas/ccf.skill-catalog-entry.json`, bytes-equality gate); **1** `docs/surface-changes/` fragment required. |
| **(ii)** A nesting-capable sibling (`ProductPayloadSchema`) | **5** symbols duplicated (`JsonSchemaType`, `SkillArgumentProperty`, `SkillArgumentSchema`, `to_input_schema`, the required-names-exist validator); **1** new `docs/schemas/*.json`; **0** existing call sites move; **1** `docs/surface-changes/` fragment required. |
| **(iii)** Flatten v0 payloads to one level | **Does not survive without loss.** Measured against `examples/s1-01-hello-context-product/artifacts/expected.yaml`: **3** declared fields lose a typed fact — `ownership_percent_by_party` (object keyed by party URI), `beneficial_owners` (array of two-field objects), `entity_count_by_class` (object keyed by entity class). Flattening `beneficial_owners` into parallel `party_refs` / `aggregate_ownership_percents` arrays preserves the values but degrades the pairing to an index convention the schema cannot state. **0** files move, **0** schemas regenerate. |

---

## Q6 — Debt composition weighting for aggregate products

| Option | Consequence (from RESEARCH) | **Measured Cost** |
|---|---|---|
| **(a)** The class declares which components are decision-critical; debt weights accordingly | Keeps values in artifacts | **NOT MEASURABLE from this tree** — no aggregate-product surface exists to count against. What *does* exist and would be reused: `union_lineage` with **10** call sites across 3 files (`src/ccf/peering`, `tests/peering`, `tests/properties`, already property-tested). The declaration itself lands on `register_product_class` (**29** sites / 26 files, or **0** under a default). |
| **(b)** Conjunctive over critical components (worst debt among the class's critical set) | Consistent with the multiplicative-conjunctive F·C·S commitment (INV-CH7-62/63) | **NOT MEASURABLE** — same reason. Adds **0** new weights, so it does not touch the foreclosure of the additive form stated in `src/ccf/halflife/debt.py`'s module docstring. Combinator cost is one pure function beside `context_debt`. |
| **(c)** Multiplicative over all components | An aggregate of ten components drives `D_c`→1 mechanically | **NOT MEASURABLE** — same reason. Same zero-weight property as (b). |
| **(d)** Defer aggregates' debt to Phase 17; ship lineage union + TTL floor + SLA refusal only | ROADMAP criterion 8 as written does not mention debt composition | **0** for the debt limb. The three named limbs of criterion 8 reuse `union_lineage` (**10** sites / 3 files) and the `refuse_operator_set_divergence` bind-time-refusal posture (`src/ccf/deployment/binder.py::refuse_operator_set_divergence`). |

**Why the three are NOT MEASURABLE and what would make them measurable:** an
aggregate product — a `ContextProductContract` composed from constituent
products — has no representation in this tree. `union_lineage` composes a
*producer/consumer pair* across the peering boundary, not an N-way sibling set,
and its own docstring records that order-independence is *"a law about the two
set axes"* only, leaving "whose `graph_snapshot_at`" undefined for N siblings.
Until the aggregate surface exists there is nothing to count. Stating that is
the honest cell; an estimate would not be.

---

## Q7 — Is debt per-(product, principal)?

| Option | Consequence (from RESEARCH) | **Measured Cost** |
|---|---|---|
| **(a)** Yes — debt is computed against the effective entitlement set | Most faithful to entitlement-formative (`:1529`, `:1342`); assembler must record permitted vs refused consultations | **NOT MEASURABLE from this tree** — no per-principal entitlement surface exists at any door. `build_egress_server` binds **no** authorizer and has **2** call sites in 2 files; the `TenantAuthorizerProtocol` action tuple is `(grant, tenant, action_id)` with **no product-class dimension**. `assess_debt` (**9** sites / 3 files) is pure over `(factors, profile)`; adding an entitlement argument changes that signature. The cost is bounded below by criterion 5's own work and cannot be separated from it until that lands. |
| **(b)** No — a refused consultation is simply not part of `C_required` for this principal | Dissolves the coupling rather than resolving it | **0** measured cost. `assess_debt`'s signature is unchanged, all **9** call sites are unchanged, and debt stays one computation per assembled product. |
| **(c)** Yes, and debt carries both figures | Most informative, most disclosure-risk | **NOT MEASURABLE** — (a)'s cost plus one more field, on a surface that does not exist. The disclosure question (a caller inferring what they may not see from a completeness figure) is a ruling, not a measurement. |

---

## Q8 — Where does `freshness_sla` live? *(surfaced by research, not in CONTEXT.md)*

**The two whitepaper enumerations, quoted side by side.** Per CLAUDE.md §15's
ambiguous-passage discipline — quote the passage, propose readings with
consequences, ask.

> **`docs/CCF_Whitepaper_1-2.md:2381`** (the sidebar enumeration):
> *"The seven contract fields enumerated below are the same seven fields
> Fig-CH07-13 renders as the Context Product Spec sidebar (schema, **freshness
> SLA**, TTL policy, policy binding, lineage graph, semantic version,
> payload) — the prose specification and the visual sidebar commit to the same
> contract surface."*

> **`docs/CCF_Whitepaper_1-2.md:2381-2405`** (the prose enumeration that
> immediately follows, unpacked field by field): `schema_name`,
> `schema_version` (`:2385-2387`), **`plan_id`** (`:2391`), `expires_at`
> (`:2393`), `ttl_anchor` (`:2395`), `lineage` (`:2401`), `payload` (`:2405`).

The two enumerations of *"the same seven fields"* differ by **exactly one
element**: the sidebar names **freshness SLA** where the prose names
**`plan_id`**. `D-IMPL-30` separately rules that the Fig-CH07-13 seven-field
typed base is *"a different artifact"* from the §6.3 specification elements.

| Option | Consequence (from RESEARCH) | **Measured Cost** |
|---|---|---|
| **(a)** Instance field on `ContextProductContract` | Matches the figure's sidebar; a product carries the SLA it was assembled under | **42** `ContextProductContract` call sites across 38 files if required-with-no-default; **0** under a positive sentinel default. Replay-safe either way: unlike debt, it *is* reconstructible from the registered product class, so it satisfies the `rehydrate_product` constraint — **but the address still moves**, exactly as the Q3 product-only measurement shows for any added hashed field. |
| **(b)** Class-level on `RegisteredProductClass` | Matches the docstring's intent and D-IMPL-30's "different artifact" framing; makes the false docstring true | **29** `register_product_class` call sites / 26 files if required; **0** under a default (the `accepted_policy_binding_modes` precedent). **0** content addresses move. Cheapest measured option. §6.3's *"Freshness SLA varies by signal and by decision"* (`:1453`) suggests a per-signal structure rather than a scalar; the structure's own cost is not separable until its shape is ruled. |
| **(c)** Both — class declares the promise, instance reports what was achieved | Turns the SLA into something checkable at delivery | (a) + (b): **0** forced call-site repairs under defaults on both sides, plus the address move of (a), plus a comparison function. |

**This is also the resolution point for the criterion-2 count.** ROADMAP
criterion 2 says "eight elements"; under `D-IMPL-30` the executable enumeration
should assert **nine**. That is a one-line ruling, raised rather than silently
widened.

---

## Already ruled — not questions

A ruling package that re-opens a standing ruling wastes the one thing this
checkpoint spends. These three are **settled** and are listed so no reader
mistakes them for open items:

| Ruling | Date | What it settled |
|---|---|---|
| **`D-IMPL-30`** | 2026-07-25 | The §6.3 contract has **nine** elements, Assembly Mode included. Every "eight" reference — CLAUDE.md §5's among them — is **editorial drift the ruling explicitly authorizes treating as drift**. The Fig-CH07-13 seven-field typed base is a *different artifact* from the specification elements. |
| **`D-IMPL-31`** | 2026-07-25 | TTL exists at two granularities with a declared per-class derivation rule, **and** product classes may declare **constituent-validity floors whose breach refuses assembly** rather than emitting a product fresher-labeled than its stalest load-bearing constituent — the mixing-refusal rule, formally footed. **Ruled 2026-07-25 and never implemented:** no floor field exists on `ProductClassDeclaration` or `RegisteredProductClass`. Criterion 8's refusal should realize this ruling, not invent a parallel rule. |
| **`D-IMPL-96`** | 2026-08-10 | *"No fabric changed"* is **revoked**, along with `D-13`'s docstring carve-out, `D-14`'s two-limb bound, and plan 16-19's `gate_16.py` allowlist. What still binds is the four CI-enforced anti-leakage lints. The fabric may and must change in this phase. |

`D-IMPL-97` (the vessel and the assembler) and `D-IMPL-95` (systems of record
are read-only) are likewise ruled; they are the premises Q1–Q8 sit on rather
than items in this table.

---

## Provenance

Every figure in this document came from
**`tests/spikes/test_contract_field_addition_cost.py`**, committed at plan
`15.5-01` and run against this tree at `3df4e91` on 2026-08-11. The module
prints its whole figure set as JSON under `pytest -s`, and writes it to a file
when `CCF_SPIKE_REPORT` is set — so a reader in a year can re-run it and see
which figures moved. The perf figures additionally required one deliberate
`make perf-micro` run, because that battery is outside `make ci` by design.

**The module reports rather than asserts every tree-derived count, and reports
rather than asserts the A3 verdict.** The reason is structural: `tests/spikes/`
sits inside `testpaths = ["tests"]` and therefore inside `make ci-core`, which
must stay green from wave 1 onward. Plans `15.5-03`, `07`, `08`, `09`, `10`,
`11`, `12` and `13` each add or move the call sites counted here, and `15.5-11`
may make the A3 link exist. A module that asserted those numbers would go red on
*correct* work by a later plan in its own phase, and the only available repair
would be to edit the evidence. What the module *does* assert is only what no
plan in this phase can falsify: properties of the content-addressing function
applied to stand-ins the module itself owns, and the five shipped positive
sentinels (`15.5-11` adds one; none is removed).

**Retiring owner: plan `15.5-14`, task 1.** The module is a measurement
instrument with a phase-length life. `15.5-14`'s sweep either retires it or
re-points it at the post-ruling tree, and accounts for the choice in the gate
package.

### A8 — the perf headroom, measured before any field or gate lands

`make perf-micro CCF_PERF_RUNNER_CLASS=local`, against
`perf/thresholds.toml [suite.micro] default = 0.10` and
`perf/baselines/local.json`:

| Benchmark | Median | Baseline | Δ | Absolute margin to the 10% ceiling | Verdict |
|---|---:|---:|---:|---:|---|
| `test_gates.py::test_gate_empty_operator_guard` | 8.000e-07 s | 8.000e-07 s | +0.00% | **8.00e-08 s (80 ns)** | PASS |
| `test_gates.py::test_gate_lineage_strict_equality` | 1.776e-06 s | 1.824e-06 s | −2.63% | **2.30e-07 s (230 ns)** | PASS |
| `test_gates.py::test_gate_ttl_bounds` | 4.544e-06 s | 4.592e-06 s | −1.04% | **5.07e-07 s (507 ns)** | PASS |

Those three are the benchmarks a fourth validation gate (Q5) or a new vessel
field (Q3, Q8) would move: `perf/suites/micro/test_gates.py` runs the canonical
`run_gates` sequence over prepared `ContextProductContract` candidates. **All
three pass with headroom, and the headroom is an absolute number of nanoseconds
rather than a claim.**

**A finding that must travel with these figures.** `make perf-micro` **already
exits 1 at this phase's base commit**, on two benchmarks that are **not** on the
Context Product surface:

| Benchmark | Median | Baseline | Δ |
|---|---:|---:|---:|
| `test_dispatch.py::test_run_coroutine_sync_overhead` | 3.264e-05 s | 2.928e-05 s | **+11.48%** |
| `test_operators.py::test_composed_chain` | 1.22429 s | 0.368903 s | **+231.87%** |

Both predate this phase and neither was caused by it — plan `15.5-01` changed
no `src/`, `runtime/`, `examples/` or `perf/` file. Recorded as `DI-15.5-01` in
`.planning/phases/15.5-…/deferred-items.md`. **Consequence for the ruling:** a
plan that measures its perf impact by `make perf-micro` exiting 0 will never
pass on this machine; the per-benchmark `test_gates.py::*` verdicts above are
the figures to read.
