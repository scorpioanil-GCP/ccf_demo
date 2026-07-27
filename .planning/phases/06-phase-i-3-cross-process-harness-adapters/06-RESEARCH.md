# Phase 6: Phase I.3 — Cross-Process & Harness Adapters - Research

**Researched:** 2026-07-26
**Domain:** Cross-process transport (MCP, A2A), cryptographic product signing, agent-harness seam binding
**Confidence:** HIGH on the external SDK surfaces (every claim below was executed, not read); HIGH on the codebase findings; MEDIUM on LF A2A integration cost (spec verified at 1.0, CCF-specific binding not prototyped).

---

## Summary

This phase's stated largest unknown — "are the four `HarnessAdapterProtocol` seams
actually bindable against three real SDKs?" — **is resolved, favourably.** All three
harnesses were installed into a clean venv and driven end-to-end. Every seam has a
concrete binding point, every harness can be executed with **zero LLM calls**, and
installing all three together produces **no dependency conflict** and holds the repo's
`pydantic==2.13.4` and `pyyaml==6.0.3` pins exactly. D-08's "one documented command
installs and runs all three" is achievable.

The D-01 vertical slice — MCP egress at L6, served to a real MCP client in a separate
process — was **prototyped in full**: custom `ccf-product://` resource URI, ephemeral
port via `bind(0)`, stdout readiness handshake with no sleep, guaranteed teardown, whole
round trip in **0.68 s**. The same fixture shape was then proven for the MCP-backed
ArtifactStore, including byte-exact retrieval of non-ASCII canonical bytes.

Three things are materially harder than 06-CONTEXT.md assumes, and all three are called
out explicitly below rather than resolved silently:

1. **The CINV-02 lint currently forbids harness imports in `/runtime` — the exact
   directory D-04 puts the adapters in.** Demonstrated empirically. This is a blocking
   structural finding that must be fixed before wave (c) can compile.
2. **`a2a-sdk` 1.x is protobuf-based, not Pydantic.** The 0.x Pydantic types are gone.
   This does not threaten XPRC-02 — the CCF Context Product travels as an opaque
   payload inside an A2A `Artifact` and CCF validates it at the boundary — but it does
   mean the A2A leg brings `protobuf` + `google-api-core` into the tree and that the
   "typed contracts at every boundary" rule is satisfied by CCF's own validation, never
   by A2A's types.
3. **`ArtifactStoreProtocol` is synchronous; the MCP client is async.** A working sync
   facade is proven below, but the naive "hold one session open in a blocking portal"
   approach **hangs** — verified. The planner must specify the working pattern.

**Primary recommendation:** Build the slice against `mcp==1.28.1` `FastMCP` +
`streamablehttp_client` using the proven subprocess fixture; fix the CINV-02 lint scope
in wave 0 before any adapter work; resolve D-19 with the **registered-callable table**,
which is the mechanism the SDK already ships for operators (D-IMPL-37) and which makes
the RCE structurally unrepresentable rather than merely refused.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MCP client ingress (L1) | `ccf` library (`ccf.mcp.client`) | `ccf_runtime` | `SignalSourceProtocol` lives in `/src`; adapters run async in `/runtime` — the existing CDC precedent exactly (D-IMPL-04(b)) |
| MCP content acquisition (L4/L5) | `ccf` library | — | Same client library, different caller; D-IMPL-13 mandates one client lib |
| MCP egress server (L6) | `ccf_runtime` | — | Servers are runtime obligations, inherently concurrent (D-IMPL-04) |
| MCP ArtifactStore server | `ccf_runtime` (separate module from egress) | — | §7.1 + D-IMPL-13: distinct trust posture, never merged with egress |
| `ArtifactStoreProtocol` MCP-backed impl | `ccf` library (sync facade) | `ccf_runtime` (the server) | The Protocol and its conformance suite are sync; the client store must present sync |
| `WireProtocol` / `IdentityProvider` Protocol decls | `ccf` library | — | D-04; `/src` skill dispatch types against them |
| A2A transports (typed-HTTP, LF A2A) | `ccf_runtime.a2a` | — | D-04; transports are deployment-facing |
| A2A admission gate | `ccf` library (Control Plane) | — | D-12: the gate sits ahead of L2 in core, above every transport |
| `HarnessAdapterProtocol` decl | `ccf` library | — | Must be harness-free and lintable |
| Three reference adapters | `ccf_runtime.adapters.<harness>` | — | §7.3; the only place a harness import may exist |
| Detached-JWS signing | `ccf` library (`IdentityProvider` reference impl) | — | Pure algorithmic; no transport dependency |
| Cross-process test fixture | `/tests` | — | D-06/D-17; never `/src` or `/runtime` |

---

## Project Constraints (from CLAUDE.md)

Extracted as directives the planner must verify compliance against:

| # | Directive | Source | How this phase is exposed |
|---|-----------|--------|---------------------------|
| C1 | Zero harness imports in `/src`, CI-enforced | §7.3, §11 | Three adapters land this phase; **lint scope is currently wrong — see Blocking Finding B1** |
| C2 | No-Hardcoding: no prompt/instruction literals, no agent/task definitions, no thresholds or routing tables as code constants — in `/src`, `/runtime`, **or** `/examples` | §6.4, §11 | Adapter code passes *rendered artifacts*, never literals; MCP resource URI templates are mechanism, product/artifact names are values |
| C3 | Single-writer: only L2 holds a write handle to L3 | §10 | Must hold across A2A, adapter, and ArtifactStore boundaries (criterion 4) |
| C4 | Typed contracts at every boundary, Pydantic `extra=forbid`, validated at the boundary | §11 | A2A's protobuf types are **not** CCF contracts — CCF validates the payload itself |
| C5 | Protocols over inheritance; every Protocol ships a reference impl | §11 | `WireProtocol` ×2, `IdentityProvider` ×1 (dev), `HarnessAdapterProtocol` ×3, `ArtifactStoreProtocol` +1 |
| C6 | Mechanism, not domain values | §11 | Server names, resource names, peer identities, key ids are all deployment values |
| C7 | Docstring cites the whitepaper section, or **this document** where SDK-defined and marked as an extension | §11 | Every module in this phase is an SDK extension (§7.1–§7.4) |
| C8 | Surface gaps, do not paper over them — log `D-IMPL-NN`, stop, ask Dave | §15 | Applies to B1–B4 below |
| C9 | Refusals are typed values; misuse is an exception | Established pattern (06-CONTEXT.md) | A2A admission refusal is a returned value, not a raise |
| C10 | Whitepaper fidelity wins over speed; the whitepaper wins over Homecams | §1, §2.1 | — |

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Build sequencing & slice**

- **D-01:** **Vertical slice first**, continuing the I.1 and I.2 pattern. The slice is
  **MCP egress at L6**: serve one existing banking Context Product as an MCP Resource,
  consumed by an MCP client in a test. Chosen as the smallest honest cross-process proof —
  it exercises the L6 delivery contract that already exists, requires no harness and no
  identity/signing, and produces the client library plus server scaffolding that A2A and
  the ArtifactStore both reuse.
- **D-02:** Waves widen **transport → trust → harness**: (a) MCP client ingress at
  L1/L4/L5 + the MCP-backed ArtifactStore; (b) A2A wire + identity/signing + Control Plane
  admission; (c) `HarnessAdapterProtocol` + the three reference adapters; (d) gate wave.
  Each wave depends only on what precedes it, and the three external harness SDKs — the
  phase's largest unknown — land last, when the fabric-side seams are already proven.
- **D-03:** **One shared MCP client library** (per D-IMPL-13) plus **three role modules**:
  L6 egress, ArtifactStore, and ingress normalization. §7.1 requires the ArtifactStore role
  live in a module distinct from egress (Phase 6 criterion 1 states this explicitly);
  separate modules make the differing trust postures structural rather than conventional.
- **D-04:** **Protocols in `/src`, implementations in `/runtime`.**
  `HarnessAdapterProtocol`, `WireProtocol`, and `IdentityProvider` are Protocol
  declarations in `/src/ccf/` (harness-free and lintable); every concrete adapter and
  transport lives under `/runtime/ccf_runtime/adapters/<harness>/` and
  `/runtime/ccf_runtime/a2a/`, matching CLAUDE.md §7.3 and the existing
  `runtime/ccf_runtime/cdc/` precedent. `/src` skill dispatch types against the Protocols,
  so the declarations cannot move to `/runtime` without inverting the dependency.
- **D-05:** **Remote skill dispatch ships with its transport wave** — `mcp` dispatch in the
  MCP wave, `a2a` dispatch in the A2A wave, each arriving with its governance and audit
  capture. The catalog already declares both skill types with typed bindings
  (`catalog.py:63-131`) while `dispatch.py` executes only `local_callable`; closing that gap
  per-wave keeps every wave end-to-end and means the harness skill-exposure seam sees all
  four skill types working.
- **D-06:** **Test fixtures in I.3, polished examples in I.5.** Each wave builds its proof
  as a test fixture (cross-process exchange, adapter portability, ArtifactStore swap); the
  `/examples` directories with READMEs land in Phase 8. Follows the I.1→example-00 and
  I.2→example-01 precursor precedent, and avoids a domain/style mismatch with the other
  five examples.
- **D-07:** Within the harness wave, **one adapter deep, then two against the suite**:
  build the Claude Agent SDK adapter end-to-end to discover what the Protocol actually
  needs, harden `HarnessAdapterProtocol` and the conformance suite against it, then bring
  ADK and LangGraph up against that fixed suite. Matches the D-10 LangGraph intra-I.3
  staging recommendation carried from Phase F. Ordering only — D-IMPL-24 made all three
  equally v0.

**Harness dependency & test posture**

- **D-08:** **Composable optional extras, never core dependencies.** Three per-harness
  extras (`adk`, `claude-agent`, `langgraph`), an aggregate `harnesses` extra installing all
  three in one command, and `dev` including `harnesses` so CI and contributors get
  everything from `pip install -e .[dev]`. Follows the `chroma` precedent ("NEVER a core
  dependency"), but for a stronger reason than weight: harness neutrality is an install-time
  property as well as an import-time one. A LangGraph deployment must not be made to install
  Google's SDK. **Requirement: one documented command installs and runs all three.**
- **D-09:** **One shared conformance suite, run against the real SDKs.** A
  factory-parametrized `HarnessAdapterProtocol` conformance suite — the pattern
  `tests/conformance/test_approval_sink.py` already establishes — executed against all three
  real harnesses in CI, **with no LLM calls**. Adapters are seam bindings, so the suite
  drives context injection, skill exposure, and effect capture without the harness ever
  reaching a model. Doubles were rejected deliberately: a double written to the Protocol we
  designed can pass while the real SDK's surface disagrees, which is exactly the failure this
  phase exists to prevent (§7.3 — portability demonstrated, not asserted).
- **D-10:** **`effects: unsupported` must be declared *and* proven inert.** An adapter
  claiming it declares so in typed metadata *and* the suite drives an effect-producing path
  asserting nothing reached the graph and no write handle was obtainable. This is what makes
  D-IMPL-25's "conformance-verified absence" different from an opt-out.

**A2A wire and trust**

- **D-11:** **Typed-HTTP fallback first, then LF A2A.** Build the fallback to prove the
  `WireProtocol` abstraction and get Context Products crossing a real process boundary with
  admission verification working, then implement LF A2A against that same abstraction.
  **This is sequencing within D-IMPL-14, not a revision of it** — LF A2A remains the ruled v0
  default (same framing as the D-10 staging note recorded at `D-GATE-F`). Rationale: LF A2A
  is an emergent 2026 standard, and §7.2 states the Contract is the stable layer while the
  wire is replaceable, so building in that order means a disappointing LF A2A surface does
  not stall XPRC-02, admission verification, identity/signing, and the example-04 fixture
  behind it.
- **D-12:** **Admission is a Control Plane gate ahead of L2.** Every inbound A2A Context
  Product passes a typed admission gate before it can reach L2; since only L2 writes to L3,
  single-writer carries the guarantee structurally. Wire implementations hand products to the
  gate and never hold a path to L2. Placing the check inside each `WireProtocol`
  implementation was rejected — it duplicates the rule per transport and lets a future
  transport omit it, the same drift IN-01 found in the pinned-resolution logic.
- **D-13:** **Real detached-JWS signing, dev-grade key custody.** Genuine signing and
  verification of emitted and inbound products, with a file-backed dev key source behind the
  `IdentityProvider` Protocol. Signature verification is load-bearing for admission, so a
  stubbed signer would make the admission gate untestable; PKI/HSM custody is deployment
  infrastructure and stays out (§13). Full mTLS channel security is deployment topology, not
  v0 SDK scope.
- **D-14:** **Lineage set-union pinned by a Hypothesis property.** Assert the law over
  generated lineage pairs — producer entries always survive, consumer entries always survive,
  order never matters, re-admission is idempotent — rather than fixture round-trips that pin
  chosen examples. Extends existing machinery: the I.1 suite already runs Hypothesis, and
  lineage strict equality is an existing validation gate. Replacement instead of union must
  fail loudly.

**Cross-process test topology**

- **D-15:** **Real subprocesses over loopback.** Spawn genuine producer and consumer
  processes exchanging over real HTTP on loopback. The only topology where "two processes" is
  literally true — an in-process double shares a Python heap and therefore cannot prove the
  consumer lacks a write handle to the producer's graph, which is exactly what criterion 4
  asserts.
- **D-16:** **Ephemeral ports plus a readiness handshake.** Bind port 0 so the OS assigns a
  free port, have the child report its address, and gate on an explicit readiness probe —
  **never a sleep** — with a pytest fixture guaranteeing teardown on failure. Removes the
  three classic flake sources: port collisions, racing a not-yet-listening server, and
  orphaned processes poisoning later tests.
- **D-17:** **One shared cross-process fixture, built during the slice.** The same harness
  serves MCP egress, the MCP ArtifactStore, and A2A. The slice therefore delivers
  infrastructure the whole phase depends on, and the ephemeral-port/readiness discipline is
  written once. Example 07's ArtifactStore swap is a deployment-level claim and is weaker if
  the store never leaves the process.
- **D-18:** **Replay-record equivalence for portability = equal on governed fields,
  harness-specific fields isolated.** Assert exact equality on everything CCF governs —
  Context Product consumed, grant-set hash, agent definition hash, policy bundle version,
  lineage — while harness-attributable fields (model version, trace shape, token counts) are
  confined to a named sub-structure excluded from comparison. Full byte equality across three
  different SDKs would either fail always or force those fields out of the record entirely.

**Inherited constraints from the Phase I.2 retrospective review**

- **D-19 (from A1, unanimous HIGH):** the `local_callable` dispatch control is a **blocking
  checklist item in the A2A/MCP wave**, not a follow-up. No wave may admit a non-fixture
  catalog source until one of — registered-callable table, Control-Plane admission allowlist,
  or provenance/signature check — is selected and implemented. Ollama's concrete case: a
  third-party catalog entry naming `os.system`. This upgrades the §5 handoff note from "carry
  forward" to "gate".
- **D-20 (from A2, 3/4 + verifier ADV-02):** `ControlPlaneStateStore.put` neither audits nor
  requires a token; the audit pairing in `grants.py` is convention. **I.3 must not add a
  second consumer of that seam without an audit-bearing write path**, because I.4's workflow
  suspend/resume multiplies the call sites and one missed pair is silent state with no audit
  record (INV-CH7-71). If a wave here needs the state seam, closing this comes first.
- **D-21 (from A3, 4/4):** **scope invariant claims to their actual enforcement.** Write
  "lint-enforced in shipped surfaces" or "audited by the current implementation" rather than
  "no path" / "by construction", unless the state is genuinely unrepresentable. Applies to
  `HarnessAdapterProtocol` seam claims and the D-10 `effects: unsupported` verification
  wording especially — a conformance-verified absence is exactly the kind of claim that
  degrades into convention.
- **D-22 (from A6, codex + verifier ADV-03):** `test_consumption_discipline.py` is a
  **direct-import** check with no transitive closure, while the AGNT-01 claim it encodes is
  "no path from Agent to L1–L5". Adapter modules enter that import graph this phase. Any
  widening of `ALLOWED_CCF_PREFIXES` requires a transitive-closure argument, as the I.2
  `ccf.controlplane.resolution` widening received — never a precedent argument.
- **D-23 (from Cursor's divergent finding):** CR-01 was a **planning** defect, not an
  implementation bug — plan 05-06's must-haves specified `content_hash(frozenset(...))` with
  no per-agent filter, so no two-agent test was ever required. Constraint for this phase:
  **any set-identity, admission decision, or replay claim computed over shared Control Plane
  state must carry a multi-principal case in its plan's `must_haves`** — two tenants, two
  agents, two peers — not just the happy single-principal path. Directly relevant to A2A
  admission (D-12) and lineage set-union (D-14).
- **Process (from Cursor):** draft gate-checklist rows from *tests that fail under the broken
  implementation*, not from plan intent. I.2's initial gate prose overclaimed and had to be
  rewritten in 05-10.

### Claude's Discretion

- **Harness skip mechanism** (D-09 corollary): how a conformance leg behaves when a harness
  SDK is absent is planning's call, under one constraint — a skipped harness leg must always
  be **visible and self-explaining**, naming which harness and which extra enables it. The I.1
  precedent is the three CINV-04 deferral skips, each naming its activating phase. CI installs
  `[dev]`, so all three legs run there regardless.
- Module tree details below the D-03/D-04 boundaries.
- Exact extra names and composition mechanics, subject to D-08's one-command requirement.

### Deferred Ideas (OUT OF SCOPE)

- **Gray areas raised but not explored** (available to research if it finds them
  load-bearing): MCP client ingress normalization detail — how source-specific MCP responses
  become `SignalEnvelope`s; the ArtifactStore MCP resource contract shape under D-IMPL-26
  addressing; A2A trust-policy artifact declaration in the Control Plane. None are blocked;
  they were judged researcher territory rather than user decisions.
  *(All three are addressed in this research — see Architecture Patterns 2, 4, and 6.)*
- **Full mTLS channel security** — D-IMPL-15 names it, but D-13 scopes v0 to detached JWS.
  mTLS is deployment topology (§13); revisit if a deployment requires it.
- **PKI/HSM key custody** — behind the `IdentityProvider` Protocol from day one, so a real
  custody backend is an implementation, not a redesign.
- **LangGraph as an orchestrator** (as opposed to as a harness) — explicitly a distinct
  `OrchestrationProtocol` integration under D-IMPL-17, and Phase 7 (I.4) scope. Do not
  conflate with the LangGraph adapter built here.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **XPRC-01** | Bidirectional MCP — client at L1/L4/L5/Experience, server at L6 and ArtifactStore (§7.1) | Standard Stack (`mcp==1.28.1`); Patterns 1–4; Code Examples 1–3; the full egress + ArtifactStore round trip is prototyped and byte-exact |
| **XPRC-02** | A2A federation — `WireProtocol` abstraction, identity/signing primitives, Control Plane admission verification (§7.2) | Patterns 5–7; `a2a-sdk==1.1.2` surface mapped (protobuf, LF A2A 1.0); `joserfc==1.7.4` detached-JWS sign/verify/tamper-refusal proven in Code Example 4; Pitfall 5 (proto types are not CCF contracts) |
| **XPRC-03** | `HarnessAdapterProtocol` + reference adapters per D-IMPL-24, binding all four seams (§7.3) | Standard Stack (all three harnesses installed, no conflict); the Four-Seam Binding Matrix maps every seam to a concrete, verified API on each of the three SDKs; no-LLM execution proven for all three; Blocking Finding B1 (lint scope) |
</phase_requirements>

---

## Blocking Findings — surfaced, not resolved (CLAUDE.md §15)

These are gaps where a decision in 06-CONTEXT.md is infeasible or materially more
expensive than it looks against the real surfaces. Per §15 they are stated, not silently
worked around. **B1 is a hard blocker for wave (c).**

### B1 — The CINV-02 lint forbids harness imports in `/runtime`, which is where D-04 puts the adapters. `[VERIFIED: executed]`

`tools/lints/__main__.py` sets `LINTED_TREES = ("src", "runtime", "examples")`.
`tools/lints/harness_imports.py` denies `google.adk`, `langgraph`, `claude_agent_sdk`
across every linted tree, and its own docstring says: *"Neither rule takes an allowlist.
Import restrictions have no legitimate exceptions."*

Empirically demonstrated by placing a probe module at `runtime/ccf_runtime/_probe_adapter.py`:

```
runtime/ccf_runtime/_probe_adapter.py:3 cinv02-harness harness import 'claude_agent_sdk'
  is forbidden in core (CLAUDE.md §7.3); bind harnesses in runtime/adapters/<harness>/ instead
runtime/ccf_runtime/_probe_adapter.py:4 cinv02-harness harness import 'langgraph' ...
runtime/ccf_runtime/_probe_adapter.py:5 cinv02-harness harness import 'google.adk.agents' ...
```

The message tells you to bind harnesses in exactly the directory it then blocks.

**Why this is not a trivial config edit.** CLAUDE.md §7.3 says "Zero harness imports in
**core**" and "adapters live in `/runtime/adapters/<harness>/`". The current lint over-applies
the rule to all of `/runtime`. The fix must be *structural*, not an allowlist entry —
CINV-02 taking an allowlist would void the invariant, and D-21 forbids weakening an
enforcement while keeping the claim.

**Recommended shape (planner's call, but the precedent is already in the file):**
`harness_imports.py` already carries `LLM_ADAPTER_MODULES` — a structural, module-path
carve-out for the one place a vendor LLM SDK is legitimate. Mirror it exactly:

```python
#: The only module paths where a harness import is the module's whole purpose
#: (CLAUDE.md §7.3: adapters live in /runtime/adapters/<harness>/).
HARNESS_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf_runtime.adapters"})
```

with the deny check reading `... and not matches_module(module_name, HARNESS_ADAPTER_MODULES)`,
identical to the `in_llm_adapter` branch. This keeps `/src` at zero-harness-imports
absolutely, keeps the rest of `/runtime` clean, and puts the carve-out in versioned code
under review rather than in a data allowlist. It is a *narrowing of the rule's stated
scope to match CLAUDE.md*, not an exception to it — and the honest D-21-compliant claim
becomes: *"lint-enforced: no module outside `ccf_runtime.adapters.*` may import a harness
package."*

**Additionally:** a negative test must pin the carve-out's boundary — a harness import in
`ccf_runtime.a2a` or `ccf_runtime.cdc` must still fail. Without it, the carve-out is a
prefix match nobody guards.

### B2 — `/runtime` is not type-checked at all. `[VERIFIED: pyproject.toml]`

`[tool.mypy] files = ["src"]`. Every adapter, every transport, and both MCP servers land
in `/runtime` this phase — i.e. the majority of the phase's new code would ship with zero
static checking, while the D-GATE-I.1 and I.2 gate evidence both cite "mypy --strict clean"
as a verification row. Extending `files` to `["src", "runtime"]` is the obvious move but is
**not free**: `google-adk`, `langgraph`, and `a2a-sdk` type-completeness is unverified, and
protobuf-generated `a2a_pb2` types are notoriously mypy-hostile without `types-protobuf` +
per-module overrides. The planner should scope this deliberately (likely: extend `files`,
add per-module `ignore_missing_imports` overrides for the three harnesses and `a2a`, in the
same shape as the existing `yaml` override — which is already precedented and already
documented with a justification comment).

### B3 — `ArtifactStoreProtocol` is sync; the MCP client is async; the obvious bridge deadlocks. `[VERIFIED: executed]`

Criterion 5 requires the MCP-backed store to pass **the same** conformance suite as
`FileArtifactStore`. That suite is synchronous (`tests/conformance/test_artifactstore.py`,
parametrized factory pattern). The `mcp` client is async-only.

The intuitive bridge — `anyio.from_thread.start_blocking_portal()` holding one
`ClientSession` open across calls — **hung indefinitely** (timed out at 120 s in testing).
`ClientSession` owns anyio task groups whose lifetime does not survive being entered from a
portal thread and held.

**The pattern that works** (verified, ~48 ms per call, Code Example 3): a dedicated
background event-loop thread owned for the store's lifetime, plus **one session per call**
against a `stateless_http=True` server. Session-per-call is what makes it robust; the
stateless server is what makes it cheap. This must be specified in the plan, not
rediscovered.

### B4 — DESIGN.md §8.9 assigns the harness adapters to Phase I.4, contradicting ROADMAP/REQUIREMENTS. `[VERIFIED: docs/DESIGN.md:745]`

> *"Phase I.4 (harness + experience) implements against §6 and §8.3: the three reference
> adapters and their conformance suite..."*

ROADMAP Phase 6 criterion 3, REQUIREMENTS XPRC-03, and 06-CONTEXT.md all place the adapters
in I.3. DESIGN.md is the stale document. This is a docs-consistency defect of the same class
as the Phase F B1–B3 findings and should be corrected in-phase (a one-line amendment noting
the reallocation), not carried into the gate where a reviewer will find it.

---

## Standard Stack

Every version below was resolved against PyPI **and** installed together into a clean
Python 3.12 venv on 2026-07-26. `pip check` reports **no broken requirements**, and the
repo's `pydantic==2.13.4` and `pyyaml==6.0.3` pins are held exactly by all three harnesses
plus MCP plus A2A. Total installed tree: **82 packages**.

### Core (new runtime dependency)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | 1.28.1 | MCP client + server, both roles, all five §7.1 edges | The official Model Context Protocol Python SDK. Ships `FastMCP` (server), `ClientSession`, and `streamablehttp_client`/`stdio_client`. No credible alternative. `[VERIFIED: pip index + executed]` |

### Supporting — A2A wave

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `joserfc` | 1.7.4 | Detached-JWS sign/verify for the `IdentityProvider` reference impl (D-13) | **Recommended over PyJWT.** First-class `jws.detach_json_content()` / RFC-7515 JSON serialization; proven sign→detach→reattach→verify and tamper-refusal below. PyJWT requires hand-rolled base64url detachment (which is what `a2a.utils.signing` does). `[VERIFIED: executed]` |
| `a2a-sdk` | 1.1.2 | LF A2A `WireProtocol` implementation (D-IMPL-14 default) | The official LF A2A Python SDK. Install as `a2a-sdk[signing]` if Agent Card signing is needed (pulls `PyJWT`). `[VERIFIED: pip index + executed]` |
| `httpx` | 0.28.1 | Typed-HTTP fallback transport client (D-11 leg 1) | Already transitively present via `mcp` and `a2a-sdk` — not a new tree |
| `uvicorn` | 0.51.0 | ASGI host for the MCP egress server, MCP ArtifactStore server, and typed-HTTP A2A server | Already transitively present via `mcp`; needed explicitly for the `sockets=[...]` ephemeral-port pattern (D-16) |
| `starlette` | 1.3.1 | `FastMCP.streamable_http_app()` returns a `Starlette` app | Transitive via `mcp`; named here because the fixture mounts it |

### Supporting — harness extras (never core, D-08)

| Library | Version | Extra | Notes |
|---------|---------|-------|-------|
| `claude-agent-sdk` | 0.2.128 | `claude-agent` | Thin: requires only `anyio`, `mcp`, `sniffio`. **Requires the `claude` CLI binary on PATH to *run* a query** (`CLINotFoundError`), but **not** to construct options, build SDK-MCP servers, or invoke tool handlers — which is all the D-09 no-LLM suite needs. `[VERIFIED: executed]` |
| `google-adk` | 2.5.0 | `adk` | Heaviest: pulls `fastapi`, `google-genai`, `opentelemetry-*`, `graphviz`, `watchdog`, `websockets`, `authlib`. Runs with no LLM via a `BaseAgent` subclass + real `Runner`. `[VERIFIED: executed]` |
| `langgraph` | 1.2.9 | `langgraph` | Pulls `langchain-core` 1.5.1, `langgraph-checkpoint`, `langgraph-prebuilt`, `langgraph-sdk`, `xxhash`. Runs with no LLM via plain-function `StateGraph` nodes. `[VERIFIED: executed]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `joserfc` | `PyJWT` 2.13.0 | PyJWT arrives anyway via `a2a-sdk[signing]`. But detached JWS is manual base64url surgery (see `a2a/utils/signing.py`), and D-13 makes signature verification load-bearing for admission — a hand-rolled detachment is exactly where a subtle verification bug hides. Use `joserfc` for CCF product signing; let PyJWT do Agent Card signing inside `a2a-sdk` where it already lives. |
| `joserfc` | `authlib` 1.7.2 | Same author, but `joserfc` is the focused successor to `authlib.jose` and is what the author now recommends for new JOSE work. `authlib` also arrives transitively via `google-adk`. |
| `pytest-asyncio` / `anyio` pytest plugin | plain `asyncio.run()` inside sync tests | **Recommend plain `asyncio.run()`.** The repo already does exactly this (`tests/integration/test_cdc_slice.py:182`) and adds no async plugin. Keeps the conformance suites synchronous, which the sync `ArtifactStoreProtocol` suite requires anyway. Adding a plugin would fork test style for no gain. |
| `mcp` `stdio` transport | `streamable-http` transport | **Recommend `streamable-http` for the fixture.** stdio would work for a subprocess child, but D-15's "real HTTP on loopback" and D-16's ephemeral-port discipline both want a socket, and the same server code then serves example 04/07 unchanged. |
| ES256 (P-256) signing | EdDSA (Ed25519) | **Recommend ES256.** `joserfc` refuses EdDSA by default (`UnsupportedAlgorithmError: Algorithm of 'EdDSA' is not recommended`) and emits `SecurityWarning: EdDSA is deprecated via RFC 9864` even with an explicit registry. ES256 works out of the box. `[VERIFIED: executed]` |

**Installation:**

```bash
# core additions
pip install "mcp==1.28.1" "joserfc==1.7.4" "a2a-sdk==1.1.2"

# D-08 one-command requirement (the aggregate extra)
pip install -e ".[dev]"        # dev includes harnesses
pip install -e ".[harnesses]"  # adk + claude-agent + langgraph
```

Suggested `pyproject.toml` shape honouring D-08's composability requirement:

```toml
[project.optional-dependencies]
adk           = ["google-adk==2.5.0"]
claude-agent  = ["claude-agent-sdk==0.2.128"]
langgraph     = ["langgraph==1.2.9"]
harnesses     = ["ccf[adk,claude-agent,langgraph]"]
dev           = ["ccf[harnesses]", "pytest==9.1.1", ...]
```

Self-referential extras (`ccf[adk,...]`) are supported by `setuptools>=77` (the repo's
build requirement) and PEP 508. `[ASSUMED]` — verify the self-reference resolves under the
project's exact setuptools version during wave 0.

---

## Package Legitimacy Audit

`slopcheck 0.6.1` run 2026-07-26 against all thirteen candidates. **13 OK, 0 SUS, 0 SLOP.**

| Package | Registry | Downloads/Repo signal | slopcheck | Disposition |
|---------|----------|----------------------|-----------|-------------|
| `mcp` | PyPI 1.28.1 | github.com/modelcontextprotocol/python-sdk | `[OK]` | Approved |
| `claude-agent-sdk` | PyPI 0.2.128 | github.com/anthropics/claude-agent-sdk-python | `[OK]` (noted: "name ends with `-sdk` — LLM naming pattern, but package is established") | Approved |
| `google-adk` | PyPI 2.5.0 | github.com/google/adk-python | `[OK]` | Approved |
| `langgraph` | PyPI 1.2.9 | github.com/langchain-ai/langgraph | `[OK]` | Approved |
| `a2a-sdk` | PyPI 1.1.2 | github.com/a2aproject/a2a-python | `[OK]` (same `-sdk` note) | Approved |
| `joserfc` | PyPI 1.7.4 | github.com/authlib/joserfc | `[OK]` | Approved |
| `authlib` | PyPI 1.7.2 | — | `[OK]` | Approved (transitive via adk) |
| `jwcrypto` | PyPI 1.5.8 | — | `[OK]` | Not selected |
| `cryptography` | PyPI 49.0.0 | — | `[OK]` | Approved (transitive) |
| `pytest-asyncio` | PyPI 1.4.0 | — | `[OK]` | Not selected (see Alternatives) |
| `httpx` | PyPI 0.28.1 | — | `[OK]` | Approved (transitive) |
| `uvicorn` | PyPI 0.51.0 | — | `[OK]` | Approved |
| `starlette` | PyPI 1.3.1 | — | `[OK]` | Approved (transitive) |

**Packages removed due to slopcheck `[SLOP]`:** none.
**Packages flagged `[SUS]`:** none.

Postinstall-script check is N/A for PyPI wheels; all thirteen install as wheels with no
build step observed.

**Provenance caveat per the package-name rule:** `mcp`, `claude-agent-sdk`, `google-adk`,
and `langgraph` were named in 06-CONTEXT.md / D-IMPL-24 by Dave's own ruling and confirmed
by successful import of their documented public APIs — these are `[VERIFIED: PyPI + executed]`.
`joserfc` and `a2a-sdk` were discovered by search and confirmed by execution; `a2a-sdk` is
additionally corroborated as the official SDK by the Linux Foundation A2A 1.0 announcement.
`joserfc`'s selection is a **recommendation, not a locked decision** — flag for confirmation.

---

## Architecture Patterns

### System Architecture Diagram

```
              ┌──────────────── External world ────────────────┐
              │                                                │
   MCP source servers                        Peer CCF fabric (org B)
   (calendar, docs, txn stores)                      │
              │                                       │ LF A2A / typed-HTTP
              │ MCP client (ingress)                  │ (signed Context Product)
              ▼                                       ▼
   ┌──────────────────────┐              ┌─────────────────────────┐
   │ MCPSourceAdapter     │              │ WireProtocol impl        │
   │ → SignalEnvelope     │              │ (ccf_runtime.a2a.*)      │
   │ (SignalSourceProtocol)│             │ NO path to L2            │
   └──────────┬───────────┘              └───────────┬─────────────┘
              │                                       │ inbound product (opaque)
              │                                       ▼
              │                          ┌─────────────────────────┐
              │                          │ A2A Admission Gate       │◄── IdentityProvider
              │                          │ (Control Plane, /src)    │    (detached-JWS verify)
              │                          │ sig → policy → contract  │
              │                          │     → lineage integrity  │
              │                          └───────────┬─────────────┘
              │                            refuse ◄──┤ (typed AdmissionRefusal
              │                            + audit   │  value, C9) 
              │                                      │ admit
              ▼                                      ▼
        ┌────────────────────── L2 Context Assembly ──────────────────────┐
        │  THE ONLY WRITER. Lineage set-union on admitted products (D-14) │
        └───────────────────────────────┬─────────────────────────────────┘
                                        ▼
                                  L3 Context Graph
                                        │ (read only)
                     ┌──────────────────┴───────────────────┐
                     ▼                                      ▼
              L4 Operators ──► L5 Projection ──► L6 Context Products
                     │  ▲                                   │
       MCP client    │  │ (content acquisition, §6.6)       │
       (acquisition) ┘  └────────────────────────────────────┤
                                                             │
        ┌────────────────────────────────────────────────────┼──────────────┐
        ▼                                                    ▼              ▼
  MCP Egress Server                     HarnessAdapterProtocol      ArtifactStore
  (ccf_runtime.mcp.egress)              (/src decl; impls in        ┌──────────────┐
  resource family 1: products           ccf_runtime.adapters.<h>)   │ file (dev)   │
  resource family 2: experience          seam1 ctx ──► harness      │ MCP-backed   │
        │                                seam2 skills ─► harness    └──────┬───────┘
        ▼                                seam3 effects ◄─ harness          │ MCP client
  external MCP consumers                        └──► L2 (governed)   ┌─────▼────────┐
  (untrusted, Π/Policy-bound)           seam4 replay ──► record      │ Artifact MCP │
                                                                     │ server       │
                                        harness NEVER holds a        │ (SEPARATE    │
                                        GraphWriter (criterion 4)    │  module)     │
                                                                     └──────────────┘
```

Three edges deliberately do **not** exist and their absence is the phase's structural claim:
`WireProtocol → L2`, `harness adapter → GraphWriter`, `ArtifactStore → L3`.

### Recommended Project Structure

```
src/ccf/
├── mcp/                     # ONE shared client library (D-03, D-IMPL-13)
│   ├── client.py            #   session lifecycle, transport selection, typed errors
│   └── errors.py            #   McpError → typed CCF failures (see Pitfall 2)
├── signal/
│   └── mcp_source.py        #   MCPSourceAdapter: MCP response → SignalEnvelope (L1 role)
├── artifacts/
│   └── mcp_store.py         #   MCP-backed ArtifactStoreProtocol impl (sync facade, B3)
├── a2a/
│   ├── wire.py              #   WireProtocol declaration (D-04)
│   ├── identity.py          #   IdentityProvider Protocol + detached-JWS reference impl
│   └── admission.py         #   The Control Plane admission gate (D-12) — ahead of L2
├── harness/
│   └── protocol.py          #   HarnessAdapterProtocol + typed seam/capability contracts
└── skills/
    └── dispatch.py          #   gains mcp + a2a paths (D-05); local_callable control (D-19)

runtime/ccf_runtime/
├── mcp/
│   ├── egress.py            #   L6 + Experience server (resource families 1 & 2)
│   └── artifact_server.py   #   SEPARATE server (§7.1, D-03) — different trust posture
├── a2a/
│   ├── typed_http.py        #   WireProtocol impl #1 (D-11 leg 1)
│   └── lf_a2a.py            #   WireProtocol impl #2 (D-IMPL-14 default; a2a-sdk)
└── adapters/                #   ★ the ONLY place a harness import may appear (B1)
    ├── claude_agent/adapter.py
    ├── adk/adapter.py
    └── langgraph/adapter.py

tests/
├── crossproc/conftest.py    #   THE shared fixture (D-17) — built during the slice
└── conformance/
    ├── test_artifactstore.py   #   + mcp-backed param (criterion 5)
    └── test_harness_adapter.py #   factory-parametrized ×3 real SDKs (D-09)
```

### Pattern 1: FastMCP egress with a CCF-scheme resource URI

**What:** Serve an L6 Context Product as an MCP Resource under a CCF-owned URI scheme.
**When to use:** The D-01 slice, and the L6 egress role generally.

Custom URI schemes work — `ccf-product://` and `ccf-artifact-blob://` were both registered
and read successfully. Templated resources (`{content_address}`) work and give the
ArtifactStore its address-keyed read.

```python
# Source: mcp==1.28.1, executed 2026-07-26
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ccf-egress", stateless_http=True, json_response=True)

@mcp.resource("ccf-product://{tenant}/{product_class}/{version}",
              mime_type="application/json")
def product(tenant: str, product_class: str, version: str) -> str:
    ...  # returns canonical JSON of the ContextProductContract
```

`stateless_http=True` is load-bearing: it is what makes the session-per-call sync facade
(B3) cheap and what keeps the fixture free of session-affinity flakes.

### Pattern 2: MCP ingress → `SignalEnvelope` (resolves a Deferred gray area)

**What:** How a source-specific MCP response becomes an L1 envelope.
**When to use:** The `MCPSourceAdapter` in wave (a).

`ClientSession.read_resource()` returns `ReadResourceResult.contents: list[TextResourceContents
| BlobResourceContents]`. The mapping is mechanical and — critically — carries **no
interpretation**, which is what keeps "L1 does not interpret" structural:

| MCP field | `SignalEnvelope` field | Note |
|-----------|------------------------|------|
| deployment-declared `system_id` for the server | `source.system_id` | Identity, never the URL (INV-CH8-01) — the server URL is location and must **not** land here |
| adapter clock | `ingestion_timestamp` | Injected, per the CDC precedent |
| — | `observed_time` | `None`. MCP has no observed-time concept; guessing one would be L1 interpreting |
| `contents[i].text` parsed as JSON, or `{"blob": <b64>}` | `raw_payload` | Opaque. The source's vocabulary |
| `{"uri", "mimeType", "resource_name", "_meta"}` | `source_metadata` | The MCP-shaped facts, quarantined from payload |
| deployment config | `tenant_id` | kw-only, per `SignalSourceProtocol.envelopes` |
| SDK-assigned | `envelope_id` | Adapter mints it, per CDC precedent |

`MCPSourceAdapter` implements `SignalSourceProtocol` and therefore *structurally* has
nowhere to put a graph handle — the same property `CDCSourceAdapter` relies on.

### Pattern 3: The ArtifactStore MCP resource contract (resolves a Deferred gray area)

**What:** The D-IMPL-26-compliant MCP surface for the artifact server.
**When to use:** Wave (a), criterion 5.

`ArtifactStoreProtocol` has four operations with different MCP shapes. The split is not
cosmetic — **`put` must be a Tool, because Resources are read-only**:

| Protocol method | MCP surface | URI / name | Why |
|---|---|---|---|
| `get(content_address) -> bytes` | **Resource** (templated) | `ccf-artifact-blob://{content_address}` | Returning `bytes` from the handler yields `BlobResourceContents` (base64) — **byte-exact fidelity verified** including non-ASCII. A `str` handler yields `TextResourceContents` and would corrupt non-UTF-8 canonical bytes. |
| `resolve_uri(uri) -> str` | **Resource** (templated) | `ccf-artifact://{tenant}/{class}/{name}@{version}` returning the address | Keeps naming and identity as two calls, exactly as the Protocol docstring insists |
| `exists(content_address) -> bool` | **Resource** or Tool | `ccf-artifact-meta://{content_address}` | The D-IMPL-26 "typed metadata resource per artifact" |
| `put(...) -> ArtifactRef` | **Tool** | `put_artifact` | Resources cannot mutate. Payload as base64 `canonical_b64` |

Round trip verified: put → address → templated blob read → `sha256(back) == addr` and
`back == RAW`.

**Structured tool output:** a plain `-> dict` handler returned `structuredContent = None`;
the client had to parse `content[0].text`. Declare a Pydantic return model on the tool to
get `structuredContent` populated. `[VERIFIED: executed]`

### Pattern 4: Cross-process fixture — ephemeral port + stdout readiness handshake (D-15/D-16)

**What:** The one shared fixture (D-17) the whole phase reuses.
**When to use:** MCP egress, MCP ArtifactStore, both A2A transports.

The key trick: **bind the socket in the child yourself**, so the OS-assigned port is known
*before* the server starts, then hand the bound socket to uvicorn. The child announces
readiness on stdout only once `server.started` flips. The parent's blocking
`readline()` **is** the readiness gate — no sleep, no retry loop, no poll.

```python
# Source: uvicorn 0.51.0 + mcp 1.28.1, executed 2026-07-26 — full round trip in 0.68 s
# --- child ---
import anyio, socket, uvicorn
async def main() -> None:
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); sock.listen(64)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(mcp.streamable_http_app(), log_level="error"))
    async def announce() -> None:
        while not server.started:
            await anyio.sleep(0.005)      # internal to the child, NOT a readiness sleep
        print(f"READY {port}", flush=True)
    async with anyio.create_task_group() as tg:
        tg.start_soon(announce)
        await server.serve(sockets=[sock])
anyio.run(main)
```

```python
# --- parent (pytest fixture) ---
proc = subprocess.Popen([sys.executable, child], stdout=subprocess.PIPE, text=True)
try:
    line = proc.stdout.readline().strip()     # blocks until ready — the handshake
    assert line.startswith("READY "), line
    port = int(line.split()[1])
    yield port
finally:
    proc.terminate(); proc.wait(timeout=10)   # guaranteed teardown, D-16
```

**Note on the `while not server.started` loop.** It is a 5 ms poll *inside the child*
observing its own server object — not a parent-side sleep-and-hope. D-16 prohibits the
latter. If the planner wants zero polling, `uvicorn.Server.startup()` can be awaited
directly; the loop above is simply the shorter version and was the one verified.

Add a hardening step the prototype did not need but the suite will: if `readline()` returns
empty (child died at import), fail with the child's stderr rather than an opaque
`int('')` error.

### Pattern 5: `WireProtocol` — what belongs above and below it

**What:** The abstraction D-11 builds twice.
**When to use:** Both A2A transports.

Because `a2a-sdk` 1.x is protobuf-based, the `WireProtocol` boundary must sit **above**
both transports' native types. The Protocol trades in CCF types only:

```python
@runtime_checkable
class WireProtocol(Protocol):
    """Carry a signed Context Product across a process boundary.

    Implementations hold NO path to L2 (D-12): a received product is handed to
    the admission gate, which is the only thing that can reach the assembly path.
    """
    def emit(self, *, peer: PeerRef, signed: SignedContextProduct) -> EmitReceipt: ...
    def receive(self) -> Iterator[InboundProduct]: ...
```

`SignedContextProduct` = the canonical bytes + the detached-JWS members. `InboundProduct`
carries those plus the peer's transport-observed identity. Nothing protobuf-shaped and
nothing JSON-RPC-shaped crosses this line.

**LF A2A payload placement.** `a2a.types.Part` has fields
`['text', 'raw', 'url', 'data', 'metadata', 'filename', 'media_type']`, and `Artifact` has
`['artifact_id', 'name', 'description', 'parts', 'metadata', 'extensions']`. The CCF
Context Product goes in `Part.raw` (bytes — preserves canonical serialization exactly) with
`media_type="application/ccf-product+json"`, and the detached-JWS members go in
`Part.metadata` or `Artifact.metadata`. Putting the product in `Part.data` (a protobuf
`Struct`) would round-trip through Struct's JSON model and **break canonical byte
equality**, which would break the signature. `[VERIFIED: field list executed]` /
`[ASSUMED]` on the `raw` vs `data` recommendation — prototype this in the LF A2A leg before
committing.

### Pattern 6: A2A trust-policy artifact (resolves a Deferred gray area)

**What:** How D-IMPL-16's "peer trust tiers configure only *what* is admissible, never
verification skips" becomes a Control Plane artifact.
**When to use:** Wave (b), consumed by the admission gate.

Follow the `MaxTTL` / `EntityResolutionSpec` precedent exactly — a typed, versioned
Control Plane artifact class, resolved by pinned `(key, version)`, with **no SDK defaults**
(D-IMPL-38 discipline). Shape (mechanism only; every value is the deployment's):

- peer identity → set of public JWKs (by `kid`) that peer may sign with
- peer → set of `producer_agent_definition_hash` values it may assert
- peer → set of `schema_name` product classes it may send
- peer → set of policy-regime identifiers it may claim

The gate reads this artifact and refuses anything outside it. Crucially it contains **no
"skip verification" field** — that field's absence is what makes D-IMPL-16 structural rather
than configured. Per D-21 the honest claim is: *"the trust-policy contract has no field
that could express a verification skip."* That one **is** genuinely unrepresentable, so the
strong wording is earned.

### Pattern 7: Detached JWS over the canonical product

**What:** D-13's signing, using the SDK's existing canonical serializer.
**When to use:** Emission and admission.

The payload signed is `ccf.contracts.canonical.canonical_bytes(product)` — the same bytes
the content address is computed over. That coupling is what lets the admission gate verify
the signature and the content address against one artifact. See Code Example 4.

### Anti-Patterns to Avoid

- **Putting the admission check inside a `WireProtocol` implementation.** Explicitly
  rejected by D-12. Two transports ship this phase and a third could ship later; the rule
  belongs above all of them. This is the IN-01 drift pattern.
- **Giving the harness adapter the `Agent` object plus anything else.** The adapter's
  fabric-side input is `Agent` (which already has `consume`/`invoke_skill`/`emit_effect`
  and provably no path to L1–L5) and nothing more. Handing it a `FabricHandle`, a
  `ControlPlaneRegistry`, or a reader would defeat criterion 4 at the seam.
- **Re-resolving prompt artifacts in the adapter.** `PHASE_I2_GATE.md` §5 is explicit: the
  factory already pins prompt artifacts onto the agent; the context-injection seam
  *consumes* them. Re-resolution would make two decisions under "the same" agent version
  render different instructions.
- **Tagging adapter modules `__ccf_mode__ = "algorithmic"`.** Adapters bind a harness that
  reaches a model — they are the semantic boundary, not an algorithmic module. The CINV-03
  lint denies `anthropic`/`openai`/etc. in algorithmic modules; a harness adapter has no
  business claiming that tag.
- **Using `Part.data` for the Context Product payload.** Struct round-trip breaks canonical
  byte equality and therefore the signature (Pattern 5).
- **A single long-lived MCP `ClientSession` behind a blocking portal.** Deadlocks (B3).

---

## The Four-Seam Binding Matrix (XPRC-03) `[VERIFIED: executed against all three SDKs]`

This is the phase's headline unknown, and it is answered. Every cell below names a real,
executed API on the installed SDK.

| Seam (D-IMPL-25) | Claude Agent SDK 0.2.128 | Google ADK 2.5.0 | LangGraph 1.2.9 |
|---|---|---|---|
| **1. Context injection** (mandatory) | `ClaudeAgentOptions.system_prompt` (str \| preset \| file) — carries the rendered prompt artifact + serialized Context Product. Also `agents={name: AgentDefinition(prompt=...)}` | `LlmAgent.instruction` / `.static_instruction` — `str` **or** `Callable[[ReadonlyContext], str \| Awaitable[str]]`, so injection can be a closure over the pinned product. Plus `Runner` session state | State-channel value on the compiled `StateGraph` (typed `TypedDict` schema), or `create_react_agent(prompt=...)`. The adapter owns the graph topology |
| **2. Skill exposure** (mandatory iff skill-set non-empty) | `create_sdk_mcp_server(name, version, tools=[...])` + `@tool(name, desc, schema)` → in-process `McpSdkServerConfig`; bound via `mcp_servers={}` and gated by `allowed_tools`/`disallowed_tools`. **Handlers directly `await`-able for the no-LLM suite** | `LlmAgent.tools=[FunctionTool(func, require_confirmation=...)]` | `langchain_core.tools.StructuredTool.from_function(...)` → `langgraph.prebuilt.ToolNode([...])`; `tool.args_schema.model_json_schema()` exposes the schema, `tool.invoke({...})` executes it |
| **3. Effect capture** (mandatory, may be `unsupported`) | `can_use_tool: Callable[..., PermissionResult]` returning `PermissionResultAllow`/`PermissionResultDeny`; plus `hooks={'PreToolUse'/'PostToolUse': [HookMatcher(...)]}`; `permission_mode` | `before_tool_callback` / `after_tool_callback` / `after_model_callback` — **returning a dict short-circuits the call**, which is exactly a governed refusal; `on_tool_error_callback` | Adapter-owned node: the CCF adapter builds the graph, so the effect node returns a typed value and never writes. Wrap or replace `ToolNode` |
| **4. Replay hooks** (mandatory) | `ResultMessage` fields: `model_usage`, `usage`, `session_id`, `num_turns`, `total_cost_usd`, `stop_reason`, `permission_denials`, `uuid`; `ClaudeAgentOptions.model` | `before_model_callback(LlmRequest)` exposes model name; `Runner.run_async` yields `Event` stream; `after_model_callback` for the response | `RunnableConfig` keys `{tags, metadata, callbacks, run_name, run_id, configurable}` — verified `metadata={"ccf_agent_hash": ...}` flows through `.stream()`; plus the checkpointer |

### No-LLM execution — proven for all three (D-09's hardest requirement)

| Harness | Proven no-LLM path |
|---|---|
| Claude Agent SDK | Construct `ClaudeAgentOptions` + `create_sdk_mcp_server` + invoke `tool.handler({...})` directly. **No `claude` CLI needed, no network.** Verified: `create_sdk_mcp_server` returned `{'type':'sdk','name':'ccf','instance': <mcp.server.lowlevel.server.Server>}` and `await echo.handler({"x":"hi"})` returned the payload |
| Google ADK | Subclass `BaseAgent`, implement `_run_async_impl` yielding `Event`s, drive with a **real** `Runner(agent=..., session_service=InMemorySessionService(), auto_create_session=True)`. Verified: `run_async` yielded `EVENT: ccf effect` with no model configured |
| LangGraph | `StateGraph` with plain-function nodes, `.compile()`, `.invoke()` / `.stream()`. Verified: both, plus `RunnableConfig` metadata propagation and real `StructuredTool`/`ToolNode` exercise |

**Consequence for D-09:** the conformance suite drives *real SDK objects executing real SDK
code paths* with no model — precisely what D-09 asked for and doubles could not give. The
"skip mechanism" (Claude's Discretion) becomes a simple `pytest.importorskip` per param,
with a message naming the harness and its extra.

### Consequence for D-10 (`effects: unsupported` proven inert)

All three harnesses give a *refusal* hook, not merely an absent write path — Claude's
`PermissionResultDeny`, ADK's short-circuiting `before_tool_callback`, LangGraph's
adapter-owned node. So the D-10 assertion has teeth: drive an effect-producing path, assert
(a) the declared metadata says `unsupported`, (b) the refusal fired, (c) nothing reached
L3, and (d) no `GraphWriter` is reachable from the adapter's public surface (reuse the
`WRITE_SURFACE_NAMES` technique from `test_consumption_discipline.py`).

### Note on LangGraph's asymmetry

Claude and ADK expose *callbacks into a loop they own*. LangGraph does not have a loop to
hook — **the adapter builds the graph**. This is the deepest difference between the three
and is why D-07's "one adapter deep first" is right, but also why **Claude may be the wrong
first adapter**: it is the most callback-shaped and therefore the least likely to surface
LangGraph's topology-ownership requirement in the Protocol. Consider hardening the Protocol
against *both* Claude and LangGraph before locking the conformance suite. `[ASSUMED]` —
a sequencing observation, not a contradiction of D-07's ordering.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP wire framing, session init, capability negotiation | A JSON-RPC client | `mcp` `ClientSession` + `streamablehttp_client` | Protocol versioning, `_meta` handling, SSE resumption, and pagination are all handled |
| Detached JWS construction | base64url slicing of a compact JWS | `joserfc.jws.detach_json_content()` | The one function; hand-rolled detachment is where verification bugs hide |
| A2A JSON-RPC dispatch, Agent Card discovery, task lifecycle | A REST endpoint pair | `a2a-sdk` `DefaultRequestHandler` + `A2ACardResolver` + `create_jsonrpc_routes` | LF A2A 1.0 is a real spec with 5 language SDKs; reimplementing it forfeits the interop that is the whole point |
| Ephemeral-port discovery | Scanning for a free port | `socket.bind(("127.0.0.1", 0))` + hand the socket to uvicorn via `sockets=[sock]` | Scan-then-bind is a TOCTOU race and the classic CI flake |
| Server readiness detection | `time.sleep(1)` | stdout handshake gated on `uvicorn.Server.started` | D-16 forbids the sleep, and the handshake is both faster and correct |
| Byte-exact artifact transport over MCP | Text resources + encoding guesswork | `bytes`-returning resource handler → `BlobResourceContents` | Verified byte-exact on non-ASCII; a `str` handler silently mangles non-UTF-8 canonical bytes |
| Async→sync bridging for the ArtifactStore | `asyncio.run()` per call, or a held portal session | Dedicated background loop thread + session-per-call against `stateless_http=True` | `asyncio.run` per call cannot reuse the loop; the held portal deadlocks (B3) |
| Tool JSON Schema generation | Hand-written schema dicts | `@tool(..., input_schema=<pydantic model>)` (Claude), `FunctionTool` signature introspection (ADK), `StructuredTool.from_function(infer_schema=True)` (LangGraph) | Every harness derives it; hand-writing three variants of one CCF skill's schema is three chances to drift |

**Key insight:** every one of these has an *exactly one* right answer in the ecosystem, and
each hand-rolled alternative fails in a way that looks like a flaky test rather than a bug.
This phase's risk is not "can we build it" — it is "will the proofs be trustworthy," and
every row above is a place a weak proof would hide.

---

## The D-19 `local_callable` control — comparison and recommendation `[BLOCKING gate item]`

`PHASE_I2_GATE.md` §5 / IN-06 names three candidates. Compared against this codebase:

| Control | Mechanism | Does it stop `os.system`? | Cost | Codebase precedent |
|---|---|---|---|---|
| **(a) Registered-callable table** | `callable_ref` stops being a dotted module path and becomes a **key into a boot-time registry** populated by explicit `register_callable(key, fn)` calls at the composition root. `importlib` disappears from `dispatch.py` entirely | **Yes, structurally.** A remote catalog entry naming `os.system` resolves to *no registered key* and is refused. There is no free-form path left to exploit | Low. ~40 lines + a `DuplicateCallableKey` error + composition-root wiring | **Strong and exact.** `src/ccf/operators/registry.py` is this mechanism already, ruled under D-IMPL-37: *"explicit boot-time registration, never import side effects... a duplicate key is fatal at boot"* |
| (b) Control-Plane admission allowlist | Keep `importlib`; check the module prefix against an allowlisted set | Partially. Blocks `os.system`, but an allowlisted package's `__init__` still executes on import, and shadowing/namespace-package tricks remain. The allowlist is a *value* that must be maintained per deployment | Medium. Plus ongoing allowlist maintenance | The CINV-01 allowlist exists but is explicitly the *only* sanctioned allowlist, and CINV-02's docstring argues import restrictions with exceptions are not invariants |
| (c) Provenance / signature check | Verify the catalog artifact's signature before honouring `callable_ref` | No. A *legitimately signed* entry from a compromised or hostile-but-trusted peer still gets arbitrary import. It authenticates the sender, not the payload's safety | High — extends D-13 signing to cover artifacts, not just products | Would reuse `IdentityProvider`, but solves a different threat (spoofing, not code execution) |

**Recommendation: (a), the registered-callable table.** Three reasons, in order:

1. **It makes the threat unrepresentable rather than refused.** This is the only one of the
   three that earns strong D-21 wording: *"no dotted module path reaches `importlib` from
   dispatch, because dispatch no longer imports anything."* (b) and (c) both leave a
   refusal that can be misconfigured.
2. **It is a mechanism the SDK already ships and Dave already ruled on.** D-IMPL-37 chose
   explicit boot-time registration over import side-effects for operators, for the closely
   related reason that import-order-dependent population is non-deterministic. Applying the
   identical shape to callables is consistency, not invention.
3. **It costs the least and needs no new values.** No allowlist artifact, no key
   distribution, no per-deployment maintenance surface.

**Sketch:**

```python
# src/ccf/skills/callables.py — algorithmic module
class DuplicateCallableKey(ValueError): ...
class CallableNotRegistered(LookupError):
    """A catalog entry names a callable this deployment never registered.

    Refused, never imported: the SDK resolves callable keys against what the
    composition root registered, so a catalog entry arriving over MCP or A2A
    (CLAUDE.md §7.2/§7.4) can name nothing this process did not already choose
    to offer (IN-06 / D-19; the T-05-18 precondition is replaced by a property).
    """

class CallableRegistry:
    def register(self, key: str, fn: Callable[[Mapping[str,str]], Mapping[str,str]]) -> None: ...
    def resolve(self, key: str) -> Callable[...]: ...   # raises CallableNotRegistered
```

`LocalCallableBinding.callable_ref` keeps its name and type (`str`) — only its *meaning*
changes from "dotted import path" to "registry key" — so no artifact schema version breaks.
The docstring in `catalog.py` that currently says "a dotted callable reference" must change,
as must `dispatch.py`'s module docstring and the `_invoke_local_callable` accepted-risk block.

**Migration cost:** `tests/fixtures/banking/skills/*.yaml` currently carry dotted refs; those
become keys, registered in `tests/conftest.py`. This is a small, contained change — do it in
wave (a), *before* any MCP/A2A artifact source exists, per D-19's "no wave may admit a
non-fixture catalog source until…".

**Related, and easy to miss:** the same IN-06 paragraph pairs `local_callable` with the
**Jinja2 SSTI deferral**. `prompts.py` is parse-only today and states "there is no `render`
call in this module or anywhere in `/src`" — the harness wave's context-injection seam is
the first `render(...)`. The render context must be built from the pinned
`InstructionBinding.parameters` only, with a `jinja2.sandbox.SandboxedEnvironment`, and
**no remote-influenced value may enter the context**. Put this in the same wave-(c)
threat-model checklist row as D-19.

---

## Common Pitfalls

### Pitfall 1: The harness-import lint blocks the adapter directory
**What goes wrong:** Wave (c) cannot compile; `python -m tools.lints` exits nonzero the
moment the first adapter imports its SDK.
**Why:** `LINTED_TREES` includes `runtime` and `HARNESS_DENY` has no module carve-out.
**How to avoid:** Fix in wave 0 (B1). Mirror `LLM_ADAPTER_MODULES`.
**Warning signs:** Any plan that schedules adapter work before a lint-scope task.

### Pitfall 2: `McpError` collapses "not found" into "unreachable"
**What goes wrong:** The MCP-backed store cannot honour `ArtifactStoreProtocol`'s explicit
distinction — its docstring says the two "demand opposite responses, and a replay that
conflated them would report a missing record as an outage."
**Why:** A missing templated resource surfaced as
`McpError: Error creating resource from template: 'deadbeef'` — a stringified server-side
`KeyError`, with no typed code. `[VERIFIED: executed]`
**How to avoid:** The artifact **server** must return a structured error the client can
discriminate — either a declared MCP error code, or (simpler and testable) an `exists`
metadata resource the store consults, or a typed `{"found": false}` structured tool result.
Do **not** string-match the message.
**Warning signs:** `except McpError` with substring matching anywhere in `mcp_store.py`.

### Pitfall 3: The held-session async bridge deadlocks
**What goes wrong:** The conformance suite hangs with no output; CI times out.
**Why:** `ClientSession` owns anyio task groups; entering it in a blocking portal and
holding it across sync calls never returns. `[VERIFIED: 120 s timeout]`
**How to avoid:** Code Example 3's pattern — dedicated loop thread, session per call,
`stateless_http=True` server.
**Warning signs:** `start_blocking_portal` + `wrap_async_context_manager` in the same file.

### Pitfall 4: Text resources silently mangle canonical bytes
**What goes wrong:** The MCP-backed store passes the conformance suite on ASCII fixtures
and fails on any real artifact — or worse, passes and stores a different content address.
**Why:** A `-> str` resource handler produces `TextResourceContents`; canonical bytes are
not guaranteed to be valid UTF-8 text round-trippable through JSON.
**How to avoid:** `-> bytes` handler → `BlobResourceContents` → `base64.b64decode(c.blob)`.
Put a non-ASCII artifact in the conformance fixture so this fails loudly if regressed.
**Warning signs:** A conformance fixture whose only artifacts are ASCII JSON.

### Pitfall 5: Treating A2A protobuf types as the typed boundary
**What goes wrong:** C4 ("typed contracts at every boundary, `extra=forbid`") is quietly
violated — protobuf messages have neither Pydantic validation nor `extra=forbid` semantics,
and unknown proto fields are silently preserved rather than refused.
**Why:** `a2a-sdk` 1.x moved from Pydantic (0.x) to protobuf (`a2a_pb2`). Anyone recalling
the 0.x API will assume Pydantic types.
**How to avoid:** The A2A message is *transport*. The CCF Context Product is validated by
`ContextProductContract` at the admission gate, from the raw canonical bytes, before
anything else happens. State this explicitly in the gate's docstring.
**Warning signs:** Any `/src` module importing `a2a.types`.

### Pitfall 6: `google-adk` drags a large tree into the default install
**What goes wrong:** A LangGraph-only deployment installs FastAPI, OpenTelemetry, graphviz,
watchdog, and `google-genai` — violating D-08's stated rationale that harness neutrality is
an install-time property.
**How to avoid:** Verify with a clean-venv test per extra: `pip install -e ".[langgraph]"`
then assert `importlib.util.find_spec("google.adk") is None`. This is a *testable* claim and
should be a conformance row, not a README sentence.
**Warning signs:** `google-adk` appearing anywhere but the `adk` extra.

### Pitfall 7: `ALLOWED_CCF_PREFIXES` widened by precedent instead of argument
**What goes wrong:** D-22's exact scenario. The adapter needs the agent's bound skills and
its pinned prompt artifacts; the temptation is to widen the agents-package allowlist.
**How to avoid:** **The adapter does not live in `ccf.agents` and should not need the
allowlist widened at all.** Adapters live in `ccf_runtime.adapters.*`, which
`test_consumption_discipline.py` does not scan. If a plan proposes widening
`ALLOWED_CCF_PREFIXES` this phase, that is a signal the adapter seam has been placed inside
`/src/ccf/agents` by mistake. If a widening genuinely is needed, D-22 requires a
transitive-closure argument in writing.
**Warning signs:** A diff touching `ALLOWED_CCF_PREFIXES` in a harness-wave plan.

### Pitfall 8: Adding a second `ControlPlaneStateStore` consumer without closing D-20
**What goes wrong:** A2A peer state or MCP session state gets parked on the state seam;
the audit pairing stays convention; I.4 multiplies the call sites.
**How to avoid:** **Prefer not to need it.** Nothing this phase requires is mutable-until-
terminal Control Plane state — trust policy is a versioned artifact (Pattern 6), keys are an
`IdentityProvider` concern, MCP sessions are per-call. If a plan reaches for
`ControlPlaneStateStore`, D-20 makes closing the audit-bearing-write-path gap a prerequisite
task in that same wave.
**Warning signs:** `state_store` appearing in an I.3 plan's must-haves.

### Pitfall 9: `EdDSA` chosen for signing
**What goes wrong:** `joserfc` refuses it by default (`UnsupportedAlgorithmError`) and warns
`SecurityWarning: EdDSA is deprecated via RFC 9864` even with an explicit registry.
**How to avoid:** ES256 (P-256). Verified working with no warnings. `[VERIFIED: executed]`

### Pitfall 10: Single-principal proofs for admission and lineage (D-23)
**What goes wrong:** Exactly CR-01 again — a set-identity or admission claim that passes
with one peer and is wrong with two.
**How to avoid:** D-23 makes this a `must_haves` obligation. Concretely, the plans need:
two **peers** with different keys for admission (peer A's signature must not admit peer B's
product); two **tenants** for the trust-policy artifact; two **agents** for any replay
equivalence claim; and D-14's Hypothesis property already generalises the lineage case.

---

## Code Examples

### 1. The D-01 slice, end to end (verified: 0.68 s, real subprocess)

```python
# Source: mcp==1.28.1, executed 2026-07-26
# --- consumer side (the test) ---
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import AnyUrl

async def read_product(port: int) -> str:
    async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp") as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            listed = await session.list_resources()
            # -> [('product', 'ccf-product://acme/covenant/v1', 'application/json')]
            got = await session.read_resource(AnyUrl("ccf-product://acme/covenant/v1"))
            return got.contents[0].text
```

Actual verified output:
`{"schema_name":"covenant","tenant_id":"acme"} | application/json`

### 2. Skill exposure across all three harnesses (one CCF skill, three bindings)

```python
# Source: executed against claude-agent-sdk 0.2.128 / google-adk 2.5.0 / langgraph 1.2.9

# --- Claude Agent SDK ---
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions
@tool("ccf_skill", "<from the catalog entry's description>", {"x": str})
async def bound(args): ...        # closure over Agent.invoke_skill
server = create_sdk_mcp_server(name="ccf", version="0.1", tools=[bound])
opts = ClaudeAgentOptions(mcp_servers={"ccf": server},
                          allowed_tools=["mcp__ccf__ccf_skill"])   # exactly the bound set

# --- Google ADK ---
from google.adk.tools import FunctionTool
from google.adk.agents import LlmAgent
agent = LlmAgent(name="ccf", tools=[FunctionTool(bound_fn)],
                 before_tool_callback=governed_refusal)            # seam 3

# --- LangGraph ---
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import ToolNode
t = StructuredTool.from_function(func=bound_fn, name="ccf_skill", description="...")
node = ToolNode([t])          # verified: tools_by_name -> {'ccf_skill': ...}
```

### 3. Sync `ArtifactStoreProtocol` facade over the async MCP client (verified working)

```python
# Source: mcp==1.28.1, executed 2026-07-26 — 3 sync calls in 145 ms
import asyncio, threading, base64
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import AnyUrl

class _Loop:
    """One background event loop, owned for the store's lifetime."""
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(30)
    def close(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop); self.thread.join(5)

class McpArtifactStore:
    """Sync ArtifactStoreProtocol impl. One session per call — the server is
    stateless_http, and a held session deadlocks (B3)."""
    def __init__(self, *, url: str) -> None:
        self._url, self._loop = url, _Loop()
    async def _with_session(self, fn):
        async with streamablehttp_client(self._url) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                return await fn(s)
    def get(self, *, content_address: str) -> bytes:
        async def f(s): return await s.read_resource(
            AnyUrl(f"ccf-artifact-blob://{content_address}"))
        return base64.b64decode(self._loop.run(self._with_session(f)).contents[0].blob)
```

Verified: `put` → address, `get` byte-exact on non-ASCII, `put` idempotent (same address).

### 4. Detached JWS: sign, detach, verify, refuse tampering (verified)

```python
# Source: joserfc==1.7.4, executed 2026-07-26
from joserfc import jws
from joserfc.jwk import ECKey

key = ECKey.generate_key("P-256", parameters={"kid": "ccf-dev-1"})
payload = canonical_bytes(product)            # the SAME bytes the content address uses

full = jws.serialize_json(
    {"protected": {"alg": "ES256", "kid": key.kid,
                   "typ": "application/ccf-product+json"}},
    payload, key,
)
detached = jws.detach_json_content(full)      # -> {'signature': ..., 'protected': ...}

# --- consumer side (admission gate) ---
public = ECKey.import_key(key.as_dict(private=False))
reattached = {**detached, "payload": base64url(payload_received)}
obj = jws.deserialize_json(reattached, public)
assert obj.payload == payload_received
```

Verified behaviours:
- detached members are exactly `{'signature', 'protected'}` — payload travels separately
- verification returns the payload and the decoded protected header
  `{'alg': 'ES256', 'kid': 'ccf-dev-1', 'typ': 'application/ccf-product+json'}`
- a tampered payload raises `joserfc.errors.BadSignatureError` — **verified**, not assumed

The `kid` in the protected header is what the trust-policy artifact (Pattern 6) keys on.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact on this phase |
|---|---|---|---|
| A2A as an "emergent 2026 standard" (D-11's framing) | **LF A2A reached 1.0** under Linux Foundation governance; 150+ organizations; production enterprise use; 5 official language SDKs (Python, JS, Java, Go, .NET) | 2026 | **D-11's premise is weaker than stated.** LF A2A is more credible than "emergent" suggests. The typed-HTTP-first sequencing is still sound risk management (it de-risks the `WireProtocol` abstraction independent of any wire), but the planner should not size the LF A2A leg as speculative |
| `a2a-sdk` 0.x Pydantic models | `a2a-sdk` 1.x **protobuf** (`a2a_pb2`) + JSON Schema 2020-12 publication; `a2a.compat.v0_3` shim exists but is empty on inspection | 1.0 milestone, 2026 | Pitfall 5. Also brings `protobuf` + `google-api-core` + `json-rpc` + `culsans` into the tree |
| MCP SSE transport | **Streamable HTTP** is the current transport; SSE retained for compatibility (`run_sse_async`, `sse_app` still present) | mcp 1.x | Use `streamablehttp_client` / `streamable_http_app()` |
| A2A Agent Cards unsigned | **Signed Agent Cards** — `AgentCardSignature{protected, signature, header}`, i.e. detached JWS, via `a2a-sdk[signing]` (PyJWT) | 1.0 | Independently corroborates D-13's detached-JWS choice: the standard itself uses the same construction |
| `anthropic-claude-sdk` / older names | `claude-agent-sdk` (0.2.128) | — | Confirmed installed name |

**Deprecated / outdated:**
- **EdDSA for JWS** — deprecated via RFC 9864; `joserfc` refuses by default. Use ES256.
- **`a2a-sdk` Pydantic types** — gone in 1.x.
- **Any expectation that `langgraph` exports a top-level surface** — `dir(langgraph)` is
  empty; everything is under `langgraph.graph`, `langgraph.prebuilt`, `langgraph.runtime`.

---

## Environment Availability

Probed 2026-07-26 in a clean Python 3.12 venv at `/tmp/hv`.

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python | everything | ✓ | 3.12 | — |
| `mcp` | XPRC-01, criterion 5 | ✓ | 1.28.1 | none needed |
| `claude-agent-sdk` | XPRC-03 leg 1 | ✓ | 0.2.128 | — |
| `google-adk` | XPRC-03 leg 2 | ✓ | 2.5.0 | — |
| `langgraph` | XPRC-03 leg 3 | ✓ | 1.2.9 | — |
| `a2a-sdk` | XPRC-02 (D-IMPL-14 default) | ✓ | 1.1.2 | typed-HTTP fallback ships first anyway (D-11) |
| `joserfc` | XPRC-02 (D-13) | ✓ | 1.7.4 | PyJWT (arrives via `a2a-sdk[signing]`) |
| `uvicorn` / `starlette` / `httpx` | cross-process fixture | ✓ | 0.51.0 / 1.3.1 / 0.28.1 | — |
| `claude` CLI (Node) | **running** a Claude Agent SDK query | ✗ (not probed on the dev box) | — | **Not needed.** D-09 forbids LLM calls; all four seams are bindable and assertable without the CLI (verified) |
| Docker | existing Postgres leg only | (unchanged) | — | `CCF_TEST_POSTGRES_DSN` |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** the `claude` CLI — and the fallback is that this
phase does not need it. Worth an explicit note in the gate doc so a reviewer does not read
"Claude Agent SDK adapter, no CLI installed" as a gap.

**Install-conflict verification:** `pip check` → *"No broken requirements found."*
`pydantic` resolved to **2.13.4** and `PyYAML` to **6.0.3** with all three harnesses + MCP +
A2A present — i.e. the repo's exact pins survive. This retires the largest D-08 risk.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest==9.1.1` (+ `hypothesis==6.161.5`), already wired |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Async style | **plain `asyncio.run()` inside sync tests** — the existing repo pattern (`tests/integration/test_cdc_slice.py:182`); no async plugin to add |
| Quick run command | `python -m pytest tests/<area> -x -q` |
| Full suite command | `python -m pytest -q && python -m tools.lints --all && python -m mypy` |
| New markers needed | `crossproc` (spawns subprocesses), `harness` (requires a harness extra) — add to `[tool.pytest.ini_options] markers`, matching the existing `postgres`/`chroma`/`conformance` precedent |

### Phase Requirements → Test Map

| Req | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| XPRC-01 | L6 product served as an MCP Resource, read by a client in **another process** | integration (crossproc) | `pytest tests/crossproc/test_mcp_egress.py -x` | ❌ Wave 0/slice |
| XPRC-01 | MCP responses normalize to a valid `SignalEnvelope`; adapter satisfies `SignalSourceProtocol` and has no graph handle | unit | `pytest tests/signal/test_mcp_source.py -x` | ❌ Wave a |
| XPRC-01 | The ArtifactStore MCP role lives in a module distinct from egress | invariant (AST) | `pytest tests/invariants/test_mcp_role_separation.py -x` | ❌ Wave a |
| XPRC-01 | `mcp` skill dispatch executes and is audited (D-05) | unit | `pytest tests/skills/test_dispatch.py -k mcp -x` | ⚠️ exists, asserts `NotYetBound` — flips |
| XPRC-02 | Typed Context Product crosses a **real process boundary** and is admitted | integration (crossproc) | `pytest tests/crossproc/test_a2a_exchange.py -x` | ❌ Wave b |
| XPRC-02 | Detached-JWS sign → verify round trip; **tampered payload refused**; **peer A's key does not admit peer B's product** (D-23) | unit | `pytest tests/a2a/test_identity.py -x` | ❌ Wave b |
| XPRC-02 | Admission verifies signature + policy bindings + contract + lineage on **every** product; refusal is a typed value **and lands in the audit journal with `resolved=False`** | unit | `pytest tests/a2a/test_admission.py -x` | ❌ Wave b |
| XPRC-02 | Lineage set-union law (producer survives, consumer survives, order-independent, re-admission idempotent) | property (Hypothesis) | `pytest tests/properties/test_lineage_union.py -x` | ❌ Wave b |
| XPRC-02 | `a2a` skill dispatch executes and is audited (D-05) | unit | `pytest tests/skills/test_dispatch.py -k a2a -x` | ⚠️ exists, flips |
| XPRC-03 | All four seams bind, against **all three real SDKs**, **no LLM calls** | conformance (parametrized ×3) | `pytest tests/conformance/test_harness_adapter.py -x` | ❌ Wave c |
| XPRC-03 | `effects: unsupported` is declared **and** the effect path is driven and proven inert (D-10) | conformance | `pytest tests/conformance/test_harness_adapter.py -k effects_unsupported -x` | ❌ Wave c |
| XPRC-03 | Skill exposure equals **exactly** the currently-bound set — an ungranted skill is invisible to the harness | conformance | `pytest tests/conformance/test_harness_adapter.py -k skill_exposure -x` | ❌ Wave c |
| XPRC-03 | Zero harness imports outside `ccf_runtime.adapters.*` | lint (CINV-02) | `python -m tools.lints --harness-imports` | ⚠️ exists, **scope wrong (B1)** |
| Criterion 5 | MCP-backed store passes the **same** `ArtifactStoreProtocol` conformance suite, **with no test-body change** | conformance (param added) | `pytest tests/conformance/test_artifactstore.py -x` | ⚠️ exists — add param |

### Success-criteria coverage (the five ROADMAP rows)

**Criterion 4 — single-writer across three boundaries.** This is the criterion most likely
to be claimed rather than proven, and D-21 forbids that. One observable per boundary:

| Boundary | Observation | Mechanism |
|---|---|---|
| **A2A** | The consumer process, running a real fabric, admits a product from a *separate* producer process. Assert (a) the graph changed only via `AssemblyWorker`, (b) `WireProtocol` implementations hold no `GraphWriter` — AST + attribute scan over `ccf_runtime.a2a.*`, reusing the `WRITE_SURFACE_NAMES` technique, (c) a **refused** product left L3 unchanged | D-15's real subprocess is what makes this non-vacuous: two heaps, so "the consumer lacks a handle to the producer's graph" is literally true |
| **Adapter** | Drive an effect through each of the three harnesses; assert nothing reached L3 except through `emit_effect` → L2; assert no attribute on the adapter's public surface is or names a `GraphWriter`/`GraphStore`/`AssemblyWorker` | Same technique as `test_consumption_discipline.py` claim 2 |
| **ArtifactStore** | With the MCP-backed store active, assert the graph is untouched by any store operation, and that `ccf.artifacts.*` and `ccf_runtime.mcp.artifact_server` import nothing from `ccf.graph` | AST import scan + a fabric-state-unchanged assertion |

Plus the existing `tests/invariants/test_single_writer_boot.py` and the CINV-02
`cinv02-graph-writer` rule, which already hold and must stay green.

**Criterion 3 / D-18 — replay-record equivalence, split.** The comparison is not
byte-equality. Concretely:

```python
GOVERNED = ("context_fabric_snapshot", "policy_bindings",
            "perspective_conditioning")   # incl. agent_definition_hash, grant_set_hash
HARNESS_ATTRIBUTABLE = "harness_trace"    # NEW named sub-structure (D-18)

# one agent definition, three adapters, three records
assert {r.model_dump(include=set(GOVERNED)) for r in records} |> len == 1
assert all(r.harness_trace.harness_id == expected[i] for i, r in enumerate(records))
```

This requires a **new typed sub-structure on the replay record** — model version, trace
reference (the D-IMPL-45 `TraceCorrelationHook` shape), token counts — excluded from the
governed comparison. That is a `/src` `ccf.replay.record` change and should be an explicit
task, not an incidental one. Note `ModelVersionRecord` already exists as its own dimension;
the planner must decide whether `harness_trace` extends it or sits beside it. **Flag: this
is a replay-record schema change in a phase whose scope statement does not mention one.**

**Criteria 1, 2, 5** are covered row-by-row in the map above.

### Sampling rate

- **Per task commit:** `pytest tests/<area> -x -q` + `python -m tools.lints --all`
- **Per wave merge:** `pytest -q` (full) + `mypy` + lints, all three green
- **Phase gate:** full suite green, including all three harness legs actually running
  (not skipping — assert this the way `CCF_REQUIRE_POSTGRES` asserts the Postgres leg;
  a silently-skipped harness leg is a green build that proved nothing)

### Wave 0 gaps

- [ ] **`tools/lints/harness_imports.py`** — `HARNESS_ADAPTER_MODULES` carve-out (**B1, blocking**)
- [ ] `tools/lints/tests/` — negative test: harness import in `ccf_runtime.a2a` still fails
- [ ] `pyproject.toml` — three harness extras + `harnesses` aggregate + `dev` inclusion (D-08)
- [ ] `pyproject.toml` — `[tool.mypy] files = ["src", "runtime"]` + per-module overrides (**B2**)
- [ ] `pyproject.toml` — `crossproc` and `harness` pytest markers
- [ ] `tests/crossproc/conftest.py` — **the** shared fixture (D-17; built in the slice)
- [ ] `src/ccf/skills/callables.py` + fixture migration — the D-19 control (**blocking**)
- [ ] `docs/DESIGN.md` §8.9 — correct the I.3/I.4 adapter allocation (**B4**)
- [ ] CI workflow — a leg that fails (not skips) if a harness extra is missing

---

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json`, so this section
applies.

### Applicable ASVS categories

| ASVS Category | Applies | Standard control in this phase |
|---|---|---|
| V2 Authentication | yes | A2A peer authentication via detached-JWS `kid` → trust-policy artifact (Pattern 6). MCP artifact server is "inside the tenant boundary but authenticated" (§7.4) — v0 dev posture is loopback-only; **document the gap rather than claim auth** |
| V3 Session Management | partial | MCP `stateless_http=True` deliberately holds no session state; nothing to hijack |
| V4 Access Control | yes | Skill exposure = exactly the bound set (T-02-27); trust-policy artifact bounds what a peer may assert; egress entitlement is Π/Policy's job, unchanged |
| V5 Input Validation | **yes, critically** | Every inbound A2A product is validated as a `ContextProductContract` (`extra=forbid`) at the admission gate **before** anything else. MCP responses land in `raw_payload` as opaque — L1 does not interpret |
| V6 Cryptography | **yes** | `joserfc` ES256 detached JWS. **Never hand-roll.** Keys via `IdentityProvider`; dev keys file-backed and never committed |
| V7 Error Handling / Logging | yes | Refusals audited with `resolved=False` (T-05-16 precedent); rejection is first-class, never a partial admission |
| V12 Files / Resources | yes | Artifact bytes are content-addressed; a tampered artifact fails its own address |
| V14 Configuration | yes | Trust policy, peer keys, and MAX_TTL are Control Plane artifacts with no SDK defaults (D-IMPL-38) |

### Known threat patterns for this stack

| Pattern | STRIDE | Standard mitigation | Status entering this phase |
|---|---|---|---|
| **Remote code execution via `callable_ref`** (IN-06 / D-19) | Elevation | Registered-callable table — no dotted path reaches `importlib` | **OPEN — blocking gate item.** Recommendation above |
| **Jinja2 SSTI at the first `render(...)`** | Elevation | `SandboxedEnvironment` + render context built only from pinned `InstructionBinding.parameters`; no remote-influenced value in the context | **OPEN — arrives with the harness wave.** Paired with D-19 in `PHASE_I2_GATE.md` §5 |
| A2A producer spoofing (T-02-25) | Spoofing | Detached-JWS verify + trust-policy `kid` binding; **verified tamper-refusal** | Mitigated by design; implement in wave b |
| Second writer via store or harness (T-02-26) | Tampering | No store→L3 edge, no harness write handle; D-IMPL-41 stack | Structural; prove per criterion 4 |
| Harness skill over-exposure (T-02-27) | Elevation | Exactly-the-bound-set; `allowed_tools` on Claude, tool list on ADK/LangGraph | Conformance row |
| **SSRF via MCP ingress server URL** | Info disclosure | MCP source server endpoints come from Control Plane config, never from decision-time input or from a fetched payload | **NEW this phase** — name it in the wave-a threat register |
| **Zip-bomb / oversized inbound product** | DoS | Size ceiling on inbound A2A payloads before canonicalization | **NEW this phase** — cheap, and the gate is the natural place |
| Replay of a validly-signed stale product | Tampering | Contract TTL gate already refuses expired products (`expires_at`, INV-CH6-05); the admission gate must run it | Existing mechanism — **wire it in**, do not reimplement |
| Dependency confusion on the harness extras | Tampering | slopcheck audit above; pinned `==` versions per the existing repo convention | Done |

---

## Assumptions Log

Claims below are `[ASSUMED]` — training knowledge or reasoning, not executed or cited this
session. Per the researcher contract they need confirmation before becoming locked plan
decisions.

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Self-referential extras (`harnesses = ["ccf[adk,claude-agent,langgraph]"]`) resolve correctly under the project's setuptools | Standard Stack | D-08's one-command requirement needs a different composition mechanic (e.g. duplicating the three lists). Low risk, trivially verified in wave 0 |
| A2 | `Part.raw` (bytes) rather than `Part.data` (Struct) preserves canonical byte equality for the LF A2A payload | Pattern 5 | If wrong, signatures break over LF A2A. Field list is verified; the *choice* is not. Prototype in the LF A2A leg |
| A3 | Extending mypy to `/runtime` needs only `ignore_missing_imports` overrides for the three harnesses + `a2a` | B2 | Could be materially more work if protobuf stubs are required. Time-box it in wave 0 |
| A4 | Hardening the `HarnessAdapterProtocol` against LangGraph *as well as* Claude before locking the conformance suite would reduce rework | Four-Seam matrix | Only a sequencing suggestion; D-07's ruled order stands unless Dave says otherwise. Worst case: some Protocol churn in wave c |
| A5 | The `claude` CLI is genuinely never needed for the D-09 suite | Environment | If some seam turns out to require a live session, the Claude leg needs a CLI in CI. Construction/handler-invocation paths were verified CLI-free; a *full* query was not attempted (correctly — D-09 forbids it) |
| A6 | `joserfc` (rather than PyJWT, which arrives transitively) is the right `IdentityProvider` dependency | Standard Stack | A second JOSE library in the tree. Both work; `joserfc`'s detached API is materially cleaner and was proven end-to-end |
| A7 | Nothing in this phase needs `ControlPlaneStateStore`, so D-20 does not gate any wave | Pitfall 8 | If a wave does need it, D-20 makes closing the audit-bearing-write-path a prerequisite — a real, unbudgeted task |

---

## Open Questions

1. **Does the replay record gain a `harness_trace` sub-structure this phase?**
   - *What we know:* D-18 requires harness-attributable fields "confined to a named
     sub-structure excluded from comparison." `ModelVersionRecord` exists as dimension 3;
     `ContentGenerationPath` exists as dimension 5. Neither has a harness slot today.
     D-IMPL-45's `TraceCorrelationHook` is designed to attach at exactly this seam.
   - *What's unclear:* whether the new structure extends `ModelVersionRecord`, extends
     `ContentGenerationPath`, or is a sixth named block; and whether that counts as scope
     creep against a phase brief that does not mention a replay-schema change.
   - *Recommendation:* surface as an explicit planning decision with a `D-IMPL-NN` if the
     answer is not obvious from D-IMPL-45. It is a `/src` contract change and should not
     arrive incidentally.

2. **How is the MCP artifact server authenticated in v0?**
   - *What we know:* §7.4 says "inside the tenant trust boundary but **authenticated**."
     `FastMCP` accepts `auth: AuthSettings` / `token_verifier: TokenVerifier`.
   - *What's unclear:* whether v0 ships a real token verifier or documents loopback-only
     as the dev posture. D-13 scoped *channel* security out, but that ruling was about mTLS
     for A2A, not about the artifact server.
   - *Recommendation:* if the answer is "loopback only in v0," say so in the docstring in
     D-21 language ("the reference server is unauthenticated and is a development
     implementation") rather than letting §7.4's "authenticated" stand as an unbacked claim.

3. **Does `mcp` skill dispatch reuse the shared client library or open its own session?**
   - *What we know:* D-03 mandates one shared client library; `McpBinding` carries
     `{server, resource}`; the sync/async bridge (B3) is per-store today.
   - *What's unclear:* dispatch is called from `Agent.invoke_skill`, which is synchronous.
     So `mcp` dispatch needs the same sync facade — meaning the facade is a *shared* concern,
     not an ArtifactStore-local one.
   - *Recommendation:* factor the loop-thread + session-per-call bridge into
     `ccf.mcp.client` in the slice, so the ArtifactStore and skill dispatch share it. This is
     a small change to the D-03 module shape and worth deciding before wave (a).

4. **Is `ccf-product://` the right egress scheme, and who owns the namespace?**
   - *What we know:* custom schemes work (verified). D-IMPL-26 already defines
     `ccf-artifact://` for artifacts.
   - *What's unclear:* whether egress products get a parallel `ccf-product://` scheme or
     reuse `ccf-artifact://` for products-at-rest (which D-IMPL-27 routes through the store).
   - *Recommendation:* two schemes. Egress serves *live* products (assembled now, TTL-bound);
     the artifact store serves products *at rest* (immutable, content-addressed). Conflating
     them would put a live-assembly URI into a replay record.

---

## Sources

### Primary (HIGH confidence — executed in this session, 2026-07-26)

- `mcp==1.28.1` — `FastMCP` construction, `@resource`/`@tool` decorators, templated
  resources, `streamable_http_app()`, `ClientSession` full method surface,
  `streamablehttp_client`, `ReadResourceResult`/`TextResourceContents`/`BlobResourceContents`
  field shapes, custom URI schemes, byte-exact blob round trip, `McpError` on missing resource
- `claude-agent-sdk==0.2.128` — full `ClaudeAgentOptions` field list (44 fields),
  `create_sdk_mcp_server`, `@tool`, `AgentDefinition`, `ResultMessage`, `SdkMcpTool`,
  `HookMatcher`; direct handler invocation with no CLI
- `google-adk==2.5.0` — `LlmAgent`/`BaseAgent` field lists, `FunctionTool`, `Runner`,
  `before_tool_callback` signature, `instruction` callable form; **no-LLM `Runner.run_async`
  executed successfully**
- `langgraph==1.2.9` / `langchain-core==1.5.1` — `StateGraph`, `.compile()`, `.invoke()`,
  `.stream()` with `RunnableConfig` metadata, `StructuredTool.from_function`, `ToolNode`,
  `create_react_agent` signature; **no-LLM graph executed**
- `a2a-sdk==1.1.2` — protobuf-based `a2a.types` (60 types), `Artifact`/`Part`/`Message`/
  `AgentCard`/`AgentCardSignature` field lists, `AgentExecutor`, `DefaultRequestHandler`,
  `ClientFactory`, `A2ACardResolver`, `a2a.utils.signing` source (PyJWT-based)
- `joserfc==1.7.4` — `jws.serialize_json`, `detach_json_content`, `deserialize_json`;
  ES256 sign→detach→verify proven; **`BadSignatureError` on tamper proven**; EdDSA refusal
  and RFC 9864 deprecation warning observed
- `uvicorn==0.51.0` — `Config(sockets=[...])`, `Server.started`; the ephemeral-port +
  readiness handshake fixture, executed end to end in 0.68 s
- `pip check` — no broken requirements with all of the above co-installed;
  `pydantic 2.13.4` / `PyYAML 6.0.3` pins held
- `slopcheck 0.6.1` — 13/13 OK
- Repository, read directly: `CLAUDE.md`, `docs/DECISIONS.md`, `docs/DESIGN.md` §8,
  `docs/PHASE_I2_GATE.md` §5, `docs/diagrams/seam-harness-adapter.mmd`,
  `docs/diagrams/seq-a2a-admission.mmd`, `.planning/ROADMAP.md` Phase 6,
  `.planning/REQUIREMENTS.md`, `06-CONTEXT.md`, `src/ccf/artifacts/{protocol,file_store}.py`,
  `src/ccf/skills/{catalog,dispatch}.py`, `src/ccf/agents/{agent,prompts}.py`,
  `src/ccf/signal/{envelope,source}.py`, `src/ccf/controlplane/state.py`,
  `src/ccf/operators/registry.py`, `src/ccf/boot.py`, `src/ccf/replay/record.py`,
  `src/ccf/products/contract.py`, `runtime/ccf_runtime/cdc/adapter.py`,
  `tools/lints/{__main__,harness_imports,algorithmic,no_hardcoding,allowlist.yaml}`,
  `tests/conftest.py`, `tests/conformance/test_approval_sink.py`,
  `tests/agents/test_consumption_discipline.py`, `pyproject.toml`
- **CINV-02 lint probe** — B1 demonstrated by executing `python -m tools.lints
  --harness-imports` against a probe module in `runtime/ccf_runtime/` (probe removed after)

### Secondary (MEDIUM confidence — search, corroborated by the executed SDK)

- Linux Foundation press release: A2A surpasses 150 organizations, enterprise production use
  — https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year
- A2A 1.0 milestone and backward-compatibility testing (Google Cloud Community) —
  https://medium.com/google-cloud/the-a2a-1-0-milestone-ensuring-and-testing-backward-compatibility-4aadb007c49b
- A2A architecture and technical specification (three-layer model, protobuf + JSON Schema
  2020-12) — https://tyk.io/learning-center/a2a-protocol-architecture-and-technical-specification/
- Agent2Agent overview — https://en.wikipedia.org/wiki/Agent2Agent

  These four corroborate the "LF A2A is at 1.0, not emergent" finding, which the installed
  `a2a-sdk==1.1.2` protobuf surface independently confirms.

### Tertiary (LOW confidence — flagged for validation)

- None. Every stack recommendation in this document was executed rather than read.

**Note:** Context7 MCP tools were unavailable in this environment and `ctx7` was not
installed. Rather than degrade to unverified documentation, every external claim was
verified by installing the package and executing its API. This is a stronger evidence
standard than Context7 would have provided.

---

## Metadata

**Confidence breakdown:**

- **Standard stack:** HIGH — every version resolved on PyPI, installed together, `pip check`
  clean, repo pins held, slopcheck 13/13.
- **Harness seams (XPRC-03):** HIGH — all four seams located on all three real SDKs, all
  three driven with no LLM. This retires the phase's stated largest unknown.
- **MCP (XPRC-01):** HIGH — the slice, the ArtifactStore round trip, and the sync facade are
  all working code, not designs.
- **A2A (XPRC-02):** MEDIUM-HIGH — signing is proven end-to-end including tamper refusal;
  LF A2A's type and server surfaces are mapped but a CCF product has not yet been carried
  over an actual `a2a-sdk` exchange (A2 is the open assumption).
- **Codebase findings:** HIGH — read directly; B1 demonstrated by execution.
- **Pitfalls:** HIGH — pitfalls 2, 3, 4, 9 were each observed as an actual failure, not
  anticipated.

**Research date:** 2026-07-26
**Valid until:** ~2026-08-25 (30 days). Shorten to ~14 days for `a2a-sdk` and
`claude-agent-sdk` specifically — both are pre-2.0/0.x and moving fast; re-verify their
versions at the start of waves (b) and (c).
