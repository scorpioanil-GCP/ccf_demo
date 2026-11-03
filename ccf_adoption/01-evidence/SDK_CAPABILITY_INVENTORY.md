# CCF SDK capability inventory — Phase 1B

> **Historical evidence:** the program status and capability labels below describe the stated source pin. Current main includes CP-00–CP-24 and SK-01; see [SDK update status](../SDK_UPDATE_STATUS.md) and [current example configuration](../examples/CONFIGURATION.md).

## Purpose

This is an adoption-facing inventory of the CCF SDK at an exact approved baseline. It is **not** a dump of every Python module and it is **not** a declaration that the SDK is frozen. It identifies the capabilities an adopter needs to understand, where their implementation evidence lives, how strongly the completed pressure-test program currently supports them, and where they should appear in `ccf_adoption`.

Read this together with `SDK_MATURITY_AND_BASELINE.md`.

## Evidence baseline

- source repository: `drcastillo/ccf_code` — **read only**
- source branch: `main`
- pinned commit: `1a04e565504f712350b51777cfe398be46d5e157`
- latest approved Context Product rung on this baseline: **CP-12 — FX Post-Trade Reconciliation**
- broader pressure-test program: **currently working through example 13 of 24**; examples after the approved baseline remain unfinished and may still change SDK behavior

The repository's configured default branch is not used as adoption authority. Searches or work-in-progress branches are evidence only after they are reconciled to an approved `main` baseline.

## Maturity labels

- **STABILIZED** — repeatedly exercised, deliberately bounded as a public seam, backed by tests/gates, and not known to be under redesign at this baseline.
- **VALIDATED-CURRENT** — implemented and exercised by approved evidence, but later examples may still change adjacent behavior or exact surface shape.
- **PROVISIONAL** — implemented but not yet sufficiently exercised by the approved example ladder to teach as a settled contract.
- **INTERNAL** — implementation mechanism; adoption material may explain the concept but should not teach the module as a normal adopter API.
- **DEPRECATED / SUPERSEDED** — historical evidence only.

These labels describe documentation confidence, not code quality.

---

## 1. The two adopter surfaces

The implementation strongly supports the two-persona documentation model already approved for this project.

### Consumer surface

A consumer wants to ask a Context Product a question and handle the governed answer. The SDK deliberately hides producer mechanics from this audience.

`ccf.client` is the clearest expression of that contract. Its root exports exactly four names:

- `ProductClient`
- `Result`
- `TransportError`
- `BindingError`

A governed refusal is data on `Result`; it is not a transport exception. Control Plane, deployment, manifest and producer types do not cross the consumer boundary.

The external-harness example goes further: a consumer reaching the product through its MCP door can use Google ADK, Claude Agent SDK, LangGraph, or a reference MCP client **without importing CCF at all**. The product is constant; the harness is the variable.

### Assembler surface

An assembler owns the problem of constructing a governed Context Product. Their surface is broader and includes:

- deployment/configuration
- signal acquisition
- graph resolution and backends
- operators and plans
- projection
- Context Product contracts and requests
- product gates
- half-life and Context Debt
- Control Plane artifacts
- replay
- serving/runtime integration

The assembler should learn these as composable responsibilities, not as a tour of internal source files.

---

## 2. Capability matrix

| Capability | Primary evidence | Maturity | Audience | Adoption destination | Documentation posture |
|---|---|---|---|---|---|
| **Consume a Context Product through `ProductClient`** | `src/ccf/client/` + `tests/client/` | **STABILIZED** | Consumer | Using SDK → Consume → in-process/bound client; Reference Manual | Teach the four-name root API first. Keep producer machinery invisible. |
| **Result / governed refusal semantics** | `ccf.client.result`, client tests, product examples | **STABILIZED** | Consumer | Using SDK → Handling results and refusals; Reference Manual | Refusal is a governed answer, not an exception. Transport/caller failures remain exceptions. |
| **Binding resolution / transport-neutral client seam** | `ccf.client.binding`, `ccf.client.wire`, `ccf.client.codec` | **VALIDATED-CURRENT** | Consumer / adapter author | Using SDK → Binding; Reference Manual → Client internals/adapters | Teach normal callers the binding concept; reserve wire/codec details for adapter authors. |
| **Harness-independent MCP consumption** | `examples/hw1-harness-clients/`, purity/budget tests | **STABILIZED** | Consumer | Using SDK → MCP → ADK / Claude / LangGraph | Key lesson: an MCP-speaking consumer does not need to know CCF internals. |
| **Signal acquisition boundary** | `src/ccf/signal/` | **VALIDATED-CURRENT** | Assembler | Using SDK → Assemble → Sources | Teach `SignalEnvelope` + `SignalSourceProtocol` as the L1 boundary; concrete acquisition adapters are secondary. |
| **Context Assembly responsibility** | `src/ccf/assembly/`, assembly tests | **VALIDATED-CURRENT** | Assembler / Architect | Using SDK → Assemble → Assembly; Architecture | Teach responsibility and invariants; do not teach private writer mechanics as adopter API. |
| **Context Graph read/write seam** | `src/ccf/graph/`, conformance/back-end tests | **VALIDATED-CURRENT** | Assembler / Architect | Using SDK → Assemble → Graph; Reference Manual | Emphasize read/write Protocol split and sole-writer invariant. Concrete writer is intentionally private. |
| **Pluggable graph/back-end posture** | graph backends + deployment config + examples | **VALIDATED-CURRENT** | Assembler | Using SDK → Backends; Sample Databases | Teach configuration and conformance, not backend-specific assumptions. |
| **Context Operators / operator algebra** | `src/ccf/operators/`, operator tests, CP ladder | **VALIDATED-CURRENT** | Assembler | Using SDK → Operators; Reference Manual | Teach canonical categories, declared params, registry, planning and composition. No domain values live in SDK. |
| **Context Projection (Π)** | `src/ccf/projection/`, projection tests, role-shaped examples | **VALIDATED-CURRENT** | Assembler / Architect | Using SDK → Projection; Governance & Controls | Teach typed transformation / role-conditioned meaning; explicitly distinguish from RBAC filtering. |
| **Context Product contract / delivery** | `src/ccf/products/`, product tests, CP ladder | **VALIDATED-CURRENT** | Assembler + Consumer | Using SDK → Product contract; Reference Manual | Central surface. Preserve distinction among contract, payload schema, request contract and gates. |
| **Typed `ProductRequest` / callable product** | `ccf.products.request`, `s1-01-hello-context-product` | **VALIDATED-CURRENT** | Consumer + Assembler | Using SDK → First Context Product | Strong candidate for the core tutorial: subject and instant are caller arguments, not frozen config. |
| **Three delivery gates** | `ccf.products.gates`, product tests, CP gates | **VALIDATED-CURRENT** | Assembler / Controls | Using SDK → Validation; Governance & Controls | Do not invent a fourth gate. Payload/request conformance and composition refusals are separate mechanisms. |
| **Entitlement at delivery** | `ccf.products.entitlement`, authz/runtime evidence | **VALIDATED-CURRENT** | Assembler / Controls | Governance & Controls; Reference Manual | Explain how product entitlement complements policy shaping during assembly. |
| **Context Product composition** | `ccf.products.composition` + approved rulings | **VALIDATED-CURRENT** | Advanced assembler | Architecture & Patterns | Document only implemented composition rules; aggregate debt remains intentionally deferred until a surface exists. |
| **Context Half-life (λ_c)** | `src/ccf/halflife/decay`, CP examples | **VALIDATED-CURRENT** | Assembler / Controls | Using SDK → Freshness; Governance & Controls | Teach formal decay, not TTL. Values come from versioned Control Plane artifacts; no SDK defaults. |
| **Context Debt (D_c)** | `src/ccf/halflife/debt`, product debt scorer, CP ladder | **VALIDATED-CURRENT** | Assembler / Consumer / Controls | Using SDK → Context Debt; Governance & Controls | Treat exact scoring/routing shape as especially change-sensitive until more examples complete. |
| **Control Plane artifacts / versioned resolution** | `src/ccf/controlplane/`, tests/controlplane | **VALIDATED-CURRENT** | Assembler / Platform / Controls | Using SDK → Control Plane; Governance & Controls; Reference Manual | Teach versioned artifact model, audit plane, pinned resolution. Exact artifact set may continue to expand. |
| **Deployment from `ccf_config.yaml`** | `src/ccf/deployment/`, tests/deployment, modern CP examples | **VALIDATED-CURRENT** | Assembler | Using SDK → Install/Configure/Boot | Primary adopter-facing assembly/wiring surface. High value but still subject to example-driven refinement. |
| **Deployment manifest / boot** | `ccf.deployment.manifest`, `boot.py` | **VALIDATED-CURRENT** | Assembler / Platform | Using SDK → Boot; Reference Manual | Config and manifest are sibling front doors; document the supported path, not incidental boot internals. |
| **Decision Replay** | `src/ccf/replay/`, replay tests, CP evidence | **VALIDATED-CURRENT** | Assembler / Controls / Security | Governance & Controls; Operations; Reference Manual | Teach five-dimension baseline and extension model. Do not describe replay as model trace. |
| **Similarity substrate seam** | `src/ccf/similarity/`, conformance tests | **STABILIZED** | Assembler | Using SDK → Similarity; Architecture & Patterns | Backend-neutral Protocol; implementations must satisfy common conformance suite. |
| **MCP server roles / L6 egress** | `runtime/ccf_runtime/mcp/` | **VALIDATED-CURRENT** | Platform / Consumer integration | Using SDK → MCP; Operations | Separate egress trust posture from artifact/HITL server roles. Runtime host, not import-time library behavior. |
| **Harness adapters** | `runtime/ccf_runtime/adapters/{adk,claude_agent,langgraph}` | **VALIDATED-CURRENT** | Agent developer | Advanced → Harness integration | SDK extension beyond whitepaper. Adapter ≠ agent loop; CCF remains harness-neutral. |
| **A2A / LF-A2A peering** | `runtime/ccf_runtime/peering/lf_a2a.py` | **VALIDATED-CURRENT** | Platform / advanced assembler | Advanced → Federation / A2A | Transport carries signed product; admission decision remains above transport. |
| **Typed HTTP peering** | `runtime/ccf_runtime/peering/typed_http.py` | **VALIDATED-CURRENT** | Platform | Advanced → Federation / HTTP | Reference transport; keep transport vs fabric semantics explicit. |
| **HTTP API front door** | `runtime/ccf_runtime/http_api/` | **PROVISIONAL** | Platform | Operations / Advanced | Code calls this a v0 skeleton; do not center the early learning path on it. |
| **Agent Specialization Framework** | `src/ccf/agents/`, tests/agents | **VALIDATED-CURRENT**, advanced | Agent/platform developer | Advanced Patterns | Explicit SDK extension beyond whitepaper. Keep secondary to Context Product adoption story. |
| **Workflow / HITL / runtime orchestration** | `runtime/ccf_runtime/{workflow,orchestration}`, related tests | **PROVISIONAL for adoption docs** | Platform / advanced | Advanced / Operations | Inventory later at finer grain; not required to teach Context Product basics. |
| **Runtime authz / identity binding / CDC / CLI** | `runtime/ccf_runtime/{authz,cdc,cli}`, `identity_binding.py` | **PROVISIONAL for adoption docs** | Platform / operations | Operations; Sample environments | Important production surface, but should be documented after core assembler path stabilizes. |
| **Artifact stores** | `src/ccf/artifacts/` + MCP artifact server | **VALIDATED-CURRENT** | Platform / assembler | Operations / Reference Manual | Explain persistence seam and trust boundary; avoid conflating immutable artifacts with Context Products. |

---

## 3. Public-surface rules derived from the implementation

### Rule A — Do not document `ccf` package root as a convenience API

`src/ccf/__init__.py` deliberately exports nothing. Public APIs live at subsystem boundaries. Adoption examples should therefore use the supported subsystem import paths rather than inventing a flat convenience namespace.

### Rule B — Consumer documentation starts with the product, not the fabric

The consumer path should begin with a question and a `Result`, then reveal binding/transport only when needed. It should **not** start by teaching graph, operators, Control Plane or deployment.

### Rule C — Producer convenience must not erase invariants

The deployment package explicitly refuses to collapse authored claims and independently observed execution into one value. Adoption tutorials must preserve that posture: ergonomics are allowed; tautological validation is not.

### Rule D — Runtime bindings are not architectural semantics

MCP, LF-A2A, typed HTTP and harness adapters carry governed values across boundaries. They do not redefine Context Product semantics. The manual must keep transport sections downstream of the typed contract.

### Rule E — No domain values in SDK prose

The SDK packages repeatedly enforce the no-hardcoding rule: thresholds, half-life rates, policy values and domain vocabulary come from versioned deployment artifacts. Tutorials should teach where values are authored, not smuggle recommended banking values into SDK documentation.

---

## 4. Example evidence model

### 4.1 Pressure-test ladder — financial-services evidence

Approved `main` contains the current CP ladder through CP-12:

- CP-00 — Institutional Holders
- CP-01 — Counterparty Reference Snapshot
- CP-02 — Facility Terms Snapshot
- CP-03 — Obligor Financial Spread
- CP-04 — Corporate Family Tree material (more than one path exists on the current tree; adoption content must resolve the canonical path before publication)
- CP-05 — Credit Exposure Rollup
- CP-06 — Collateral and Set-off Coverage
- CP-07 — Client 360 Coverage Graph
- CP-08 — Covenant-in-Force As-Of
- CP-09 — Treasury Liquidity Position
- CP-10 — Rating and Spread Migration
- CP-11 — Credit Surveillance Early Warning
- CP-12 — FX Post-Trade Reconciliation

These are **evidence generators and flagship use-case candidates**, not the right order for a beginner tutorial. They should feed Section 07 Financial Services Use Cases after their lineage is joined to Vault + Dataprep in Phase 1C.

Example 13 of the 24-example program is currently in progress outside this pinned approved baseline. It must not be presented as released evidence until it reaches the project's normal approval/merge discipline.

### 4.2 Simple learning examples

Two existing examples are especially promising for Section 04 Using the SDK:

**`s1-01-hello-context-product`**

- demonstrates that a Context Product is called, not configured
- makes subject and temporal instant caller inputs
- shows one product class answering multiple questions from one graph
- runs the fabric end-to-end without an agent
- visibly separates the generic CCF spine from deployment/domain code
- carries debt, lineage, content address and replay with the answer

This is a strong candidate for the assembler-side "first Context Product" tutorial, although its Fluree prerequisite may justify an even smaller local tutorial before it.

**`hw1-harness-clients`**

- same product, same MCP door, three harnesses
- Google ADK, Claude Agent SDK and LangGraph
- consumer programs import no `ccf`
- demonstrates harness neutrality and transport/application separation

This is a strong candidate for the consumer-side "use CCF from your agent framework" tutorial.

### 4.3 Historical and retirement-sensitive examples

The repository contains modernization and retirement machinery. Any adoption page that points to an older example path must first check the retirement/coupling inventory. We will not create adoption links by directory-name intuition alone.

---

## 5. Documentation sequencing implied by SDK maturity

### Safe to advance early

- CCF consumer mental model
- `ProductClient` / `Result` / refusal semantics
- harness-neutral MCP consumption
- first Context Product conceptual spine
- signal / graph / operators / projection / product responsibility model
- deployment/configuration at pattern level
- decision replay concept
- transport-vs-contract distinction

### Advance, but keep exact surface version-pinned

- `ccf_config.yaml` schema and deployment helpers
- Context Debt scorer and routing details
- Control Plane artifact catalog
- product request / payload declarations
- exact gate signatures
- backend wiring
- peering and runtime host surfaces

### Defer final-reference freeze

- complete API enumeration
- exact long-term import guarantees beyond deliberately bounded surfaces
- complete artifact-class catalog
- full workflow/HITL/agent-framework reference
- vulnerability/security claims against the implementation

The final Reference Manual should receive a distinct **SDK baseline freeze checkpoint** after enough of examples 13–24 have completed to make that freeze credible.

---

## 6. Proposed documentation hierarchy from this inventory

### Consumer track

1. What is a Context Product?
2. Ask one in-process / through `ProductClient`
3. Understand `Result`, debt, lineage and refusal
4. Consume through MCP
5. Consume from ADK / Claude Agent SDK / LangGraph without learning producer internals
6. Advanced binding and adapter authoring

### Assembler track

1. Start from a decision and product contract
2. Author deployment/config artifacts
3. Acquire signals through the L1 seam
4. Resolve/store graph state
5. Declare operator requirements and plans
6. Project for a principal
7. Bind request/payload/product contracts
8. Run delivery gates
9. Measure half-life and Context Debt
10. Record replay
11. Expose the product through a door/runtime transport
12. Validate with product gates and example-specific sabotage tests

### Reference Manual

Organize primarily by these adopter-visible responsibilities, with exact classes/functions nested inside them. Do **not** mirror the source tree blindly.

---

## 7. Checkpoint 1B recommendation

Approve this SDK evidence posture with three explicit constraints:

1. `ccf_code/main@1a04e565504f712350b51777cfe398be46d5e157` is the Phase 1B evidence baseline, not a frozen forever-version.
2. Later approved SDK-changing examples trigger an evidence refresh before affected adoption content is declared current.
3. The final Reference Manual surface receives a later explicit freeze checkpoint; it is not frozen by completion of Phase 1B.
