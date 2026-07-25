# Design Fragment — Experience Layer Pillar + Cross-Process Seams

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

**Owned inventory entries (per `fragments/entry-ownership.md`):** INV-CH6-06, INV-CH7-91, INV-CH8-07, INV-CH8-08, INV-CH8-21, INV-CH8-24. Every ruling embodied here is RESOLVED in `docs/DECISIONS.md`; no PROVISIONAL flags apply to this fragment's owned decisions.

**SDK-extension labeling:** the Experience Layer, bidirectional MCP, A2A-as-first-class, the HarnessAdapterProtocol, and the ArtifactStore are SDK-defined extensions per CLAUDE.md §1, §7.1–§7.4, §8.3 — not whitepaper-derived, and labeled as such throughout.

---

## 1. Experience Layer Pillar (SDK-defined, CLAUDE.md §8.3)

The Experience Layer is the front door: three v0 surfaces, nothing more. It adds delivery, authentication hooks, and serialization over the fabric — never new semantics, never a second write path. Diagram: `docs/diagrams/pillar-experience.mmd`.

### 1.1 MCP server (egress front door)

- **Responsibility:** Expose L6 Context Products as MCP Resources and permitted agent invocations as MCP Tools. This is the whitepaper's Pattern 3 unchanged (INV-CH8-07, §8.3): the fabric is *served via* MCP, not *defined by* MCP — the Context Product carries its semantic contract (§6.3) at the application layer, transport-independent.
- **Protocol/type signatures:** One `ccf-runtime` MCP egress server, two resource families — Context Products (L6 egress) and Experience access (agent invocation Tools) — per the D-IMPL-13 ruling. L6 egress and Experience access are one server, two resource families; the ArtifactStore MCP contract is a *separate* server, never merged with egress (D-IMPL-13).
- **Invariants enforced:** MCP never manages state, enforces temporal logic, applies policy, or constructs context (INV-CH6-06, §6.5.1): MCP is the access layer, CCF is the construction layer. Canonical request path: Agent → MCP Interface → Context Assembly Runtime → Context Graph → Context Product → Agent. One construction layer, one invariant set, one audit substrate regardless of the consuming framework.
- **Seams:** External agent runtimes (Claude products, third-party frameworks) reach Context Products through the same egress used by internal consumers (CLAUDE.md §7.1); the D-IMPL-20 HITL reference transport also rides this server — HITL queues as Resources, actions as Tools.
- **D-IMPL rulings embodied:** D-IMPL-13 (role allocation), D-IMPL-23 (the HTTP surface mirrors, never bypasses, the same factories/Control Plane actions).

### 1.2 `ccf` CLI (per D-IMPL-22 ruling)

- **Responsibility:** Interactive front door: noun-verb subcommand structure `ccf <noun> <verb>` over exactly the §8.3 enumerated surfaces, with the ruled noun set: `agent`, `skill`, `workflow`, `hitl`, `replay`, `artifact`, `product`, `config`.
- **Protocol/type signatures:** Thin client over the HTTP API (D-IMPL-23), plus a `--local` direct-library mode for the SQLite/file-backed dev quickstart (examples 00–02, CLAUDE.md §9).
- **Invariants enforced:** Every mutating verb routes through the same factories and Control Plane actions as any other client — `ccf agent declare` takes an artifact file, never inline definition flags (No-Hardcoding Rule, CLAUDE.md §6.4). The CLI adds zero privileged paths: one authorization surface, one audit surface (D-IMPL-22).
- **Seams:** `ccf replay` verbs consume the three-rendering surface of INV-CH7-91 (§7.10.7): auditors, risk/compliance, and management renderings are three Π projections of the *same* replay record, never three records — the CLI selects a rendering by requesting a Π role-conditioning, reusing the §7.5 Projection primitive recursively at the replay layer. `ccf artifact` verbs resolve both D-IMPL-26 address forms (content hash and versioned URI).
- **D-IMPL rulings embodied:** D-IMPL-22, D-IMPL-23, D-IMPL-26.

### 1.3 HTTP API skeleton (per D-IMPL-23 ruling)

- **Responsibility:** Minimal v0 REST skeleton mirroring the CLI noun set: product retrieval; agent declare/list/show/versions; skill grants/catalog; workflow invocations/status/resume; HITL queues/actions; replay decisions/resolve; artifact get/put; health + OpenAPI.
- **Protocol/type signatures:** OpenAPI generated from the Pydantic `extra=forbid` contracts the SDK already defines — the API adds serialization, auth hooks, and routing; no new semantics (D-IMPL-23).
- **Invariants enforced:** **L1 ingestion is deliberately NOT on the v0 HTTP surface.** Ingress is CDC/MCP-adapter territory (D-IMPL-13, D-IMPL-33); a generic write endpoint would invite a second writer path, violating the single-writer invariant (CLAUDE.md §10).
- **Seams:** The primary surface for service integration and user-built UX layers.
- **D-IMPL rulings embodied:** D-IMPL-23, D-IMPL-22 (CLI-over-HTTP layering).

### 1.4 Non-goals (v0)

Per CLAUDE.md §8.3/§13: no mobile SDK, no chat adapter, no web UI, no human-task inbox — users build these on the HTTP API against the shipped OpenAPI spec. The **Conversational Reporting Layer is out of v0 SDK scope** (INV-CH8-21, §8.10; CLAUDE.md §13 explicit out-of-scope list): it is inventoried, not designed — its underlying primitives (Π, D_c gating, replay) are in scope individually, and a future conversational surface is a user-built reference integration over the same three front doors. This boundary is the design condition INV-CH8-24 (§8.13) restates: **coexistence, not replacement** — the Experience Layer layers onto whatever estate exists; heterogeneity is the condition the architecture was designed for, and source moves re-bind at the ingestion layer, never as front-door rework.

---

## 2. Seams Chapter — Cross-Process Surfaces

The four seams below are where trust postures change. Each is a distinct module with a distinct trust posture; none creates a second writer to L3.

### 2.1 MCP role allocation (per D-IMPL-13 ruling)

MCP is allocated to exactly the five CLAUDE.md §7.1 edges — an SDK-defined extension of the whitepaper's export-only Pattern 3 (INV-CH8-07):

| Role | Direction | Layer | Module | Trust posture |
|------|-----------|-------|--------|---------------|
| Signal ingress | client | L1 | `ccf` MCP client library via `MCPSourceAdapter` → D-IMPL-33 `SignalEnvelope` | Outbound to source systems; results are untrusted signal, normalized at L1, interpreted at L2 |
| Content acquisition | client | L4–L5 | same `ccf` MCP client library | Decision-time acquisition (§6.6 search-inference recursion); results reach L3 only via L2 |
| Product egress | server | L6 | `ccf-runtime` MCP egress server (resource family 1) | Serves policy-bound, role-projected products; consumers untrusted, entitlement enforced by Π/Policy |
| Experience access | server | above L6 | same egress server (resource family 2: agent Tools, HITL queues per D-IMPL-20) | Authenticated front door; zero privileged paths |
| Artifact persistence | server | Control Plane substrate | separate ArtifactStore MCP server contract (§7.4) | Inside tenant trust boundary, authenticated; never merged with egress |

- **Invariants enforced:** SDK-as-MCP-client and SDK-as-MCP-server live in different modules (CLAUDE.md §7.1); single-writer unaffected — acquisition results reach L3 only via L2 (D-IMPL-13). MCP provides discovery, request, and standardized invocation and nothing more (INV-CH6-06).
- **Packaging:** follows D-IMPL-04 (client library in `ccf`, servers in `ccf-runtime`).

### 2.2 A2A federation (per D-IMPL-14/15/16 rulings)

SDK-defined elevation of Pattern 4 (INV-CH8-08, §8.3) to a v0 commitment per CLAUDE.md §7.2. Diagram: `docs/diagrams/seq-a2a-admission.mmd`.

- **Responsibility:** Cross-process, cross-organization Context Product exchange. The Context Product Contract is the stable layer; the wire is replaceable.
- **Protocol/type signatures:** `WireProtocol` abstraction with the Linux Foundation A2A protocol (JSON-RPC over HTTPS, Agent Card discovery, task/artifact model) as the v0 default implementation, carrying the typed Context Product as the artifact payload; mTLS via deployment configuration; a plain typed-HTTP fallback transport as the second reference implementation (D-IMPL-14).
- **Identity and signing (D-IMPL-15):** `IdentityProvider` Protocol, two-layer model — workload/transport identity via mTLS (X.509) as deployment configuration; product-level signing via detached JWS over the canonical serialized Context Product (producer agent identity + version + key id), verified at the consumer's Control Plane during admission. Reference implementations: static-keypair JWS (dev) and certificate-backed keys (production posture). SPIFFE/SPIRE is a conforming implementation, not required.
- **Admission verification (D-IMPL-16):** Verify **every** inbound A2A Context Product — full Control Plane verification (signature, Policy bindings, contract validation, lineage integrity) on every admission, no fast path in v0. Peer trust tiers configure only *what* is admissible (producers, product classes, policy regimes a peer may assert), never verification skips. Post-v0 relief via verification caching memoized on immutable artifact identity, preserving verify-everything semantics.
- **Invariants enforced (structural, INV-CH8-08 + CLAUDE.md §10):** An inbound A2A Context Product is **not admissible to L3 until the consuming Control Plane validates its Policy bindings; admission then flows only through L2** — the single-writer invariant holds across the federation boundary. **Lineage continuity via set-union:** inbound L *extends*, never replaces, the consumer's L — the producer's operator plan, graph snapshot reference, and policy version are all preserved across the boundary, with passage-level L preserved (Mode 3 assembly, §7.6). Rejection is a first-class outcome: a failed verification produces an audited rejection record, never a partial admission.
- **D-IMPL rulings embodied:** D-IMPL-14, D-IMPL-15, D-IMPL-16 (and D-IMPL-13 for the transport-role boundary with MCP).

### 2.3 HarnessAdapterProtocol (per D-IMPL-24/25 rulings)

The load-bearing neutrality seam (CLAUDE.md §7.3): CCF layers onto any harness as the trust-and-control plane; it never absorbs the agent loop and does not ship one. Diagram: `docs/diagrams/seam-harness-adapter.mmd`.

- **Responsibility:** Bind an agent definition (a Control Plane artifact, §6.1) to a concrete harness at runtime across exactly four seams:
  1. **Context injection** — typed Context Products into the harness's context/memory/prompt-assembly surface; the harness never touches L3 or raw signal.
  2. **Skill exposure** — exactly the agent's *currently-bound* skill-set (§6.2 channel 2) surfaced as the harness's tools; ungranted skills do not exist from the harness's point of view (threat T-02-27 mitigation: no over-exposure by construction).
  3. **Effect capture** — harness outputs routed back through governed emission (typed Context Product) or L2 write-back; a harness never acquires a write handle to the graph — the single-writer invariant holds across the adapter boundary.
  4. **Replay hooks** — model version, prompt-artifact version, and execution trace captured into the five-dimension Decision Replay record; the D-IMPL-45 `TraceCorrelationHook` attaches here.
- **Seam scope (D-IMPL-25):** Three seams mandatory for every conforming adapter — context injection, replay hooks, and effect capture *as governed refusal*; skill exposure conditionally mandatory (required iff the bound agent has a non-empty skill-set). A read-only consumer adapter may declare `effects: unsupported`, in which case the absence of any write-back path is a *declared capability verified by the conformance suite* — never a merely-unimplemented seam.
- **Reference targets (D-IMPL-24, Dave's own ruling):** ALL THREE harnesses ship reference adapters in v0 — Google ADK + Claude Agent SDK (must-haves) + LangGraph. Accepted consequences recorded in the ruling: a third adapter, third CI leg, and third example-03 variant enter v0 scope. The LangGraph two-seam disambiguation (per D-IMPL-17): the LangGraph *harness adapter* binds only the §7.3 agent-loop seams; LangGraph *as an orchestrator* of CCF agents is a distinct, optional OrchestrationProtocol integration — one tool, two seams, never conflated.
- **Invariants enforced:** **Zero harness imports in core** — no module in `/src` imports any harness package; adapters live in `/runtime/adapters/<harness>/`; CI import lint enforces (same machinery as the `@algorithmic` lint). Shown structurally in the seam diagram: the CCF-core subgraph contains no harness node, and the only edges crossing the boundary are the four typed seams. Cross-reference: Invariant Preservation chapter (plan 02-10 synthesis), zero-harness-imports row.
- **D-IMPL rulings embodied:** D-IMPL-24, D-IMPL-25 (plus D-IMPL-45 at the replay-hooks seam).

### 2.4 ArtifactStore seam (per D-IMPL-26/27 rulings)

SDK-defined persistence surface (CLAUDE.md §7.4). Diagram: `docs/diagrams/seam-artifact-store.mmd`.

- **Responsibility:** Persist CCF artifacts through an `ArtifactStoreProtocol` with an MCP-backed reference implementation (the separate D-IMPL-13 artifact server contract) and a file-backed dev implementation, so users point at their own persistent store by implementing the Protocol or standing up a conforming MCP server.
- **Artifact classes in scope (per the D-IMPL-27 mutability split):** Immutable, versioned, replay-relevant artifacts route through the store — Decision Replay records with all extensions (HITL, workflow, skill-set, agent-version), materialized graph-substate and similarity-index snapshots (D-IMPL-06), Context Products at rest, Control Plane bundles (policy bundles, λ_c tables, workflow definitions, HITL policies, A2A trust policy), and all No-Hardcoding artifacts (agent/task definitions, prompt artifacts, skill catalog entries and grants). Hot mutable state stays on native Protocols: live Context Graph on GraphStore (D-IMPL-02), live similarity index (D-IMPL-03), operator-plan intermediate caches (D-IMPL-36), suspended workflow execution state (D-IMPL-18) — mutable until terminal, whose terminal trace then lands in the store. The mutability criterion is a single structural rule.
- **Addressing (D-IMPL-26):** Hybrid — content-addressed canonical identity (`sha256` of canonical serialization; tampering fails the artifact's own address) plus versioned-URI naming (`ccf-artifact://{tenant}/{artifact_class}/{name}@{artifact_version}`) resolved through an append-only Control Plane mapping (a version once bound to a hash is never rebound). `@latest` is permitted only at authoring/Control Plane surfaces — never in a replay record or lineage entry, which store the hash. The reference artifact MCP server exposes both address forms with a typed metadata resource per artifact. Replay resolves *exact* versions, never "latest."
- **Invariants enforced:** **Never a second writer** (threat T-02-26): the ArtifactStore is a persistence substrate reached *through* L2 and Control Plane mechanism; nothing enters the graph except through L2, including artifacts retrieved from the store — the seam diagram shows no store→L3 edge. Trust posture: inside the tenant boundary but authenticated; artifacts arriving from *outside* the boundary are A2A's problem (§2.2 above), never the store's. The D-IMPL-50 fidelity-lifecycle engine (compression tiers, severity exemption, retention-reason) executes *above* the Protocol, so any conforming store gets the lifecycle for free (see-also INV-CH7-89, owned by design-data-context-b.md).
- **D-IMPL rulings embodied:** D-IMPL-26, D-IMPL-27 (with D-IMPL-06, D-IMPL-18, D-IMPL-50 interactions noted).

---

## 2.5 CLI noun-verb surface (contract altitude, per D-IMPL-22)

| Noun | Representative verbs | Backing surface |
|------|----------------------|-----------------|
| `agent` | declare (artifact file), list, show, versions | Agent Factory / Control Plane (§6.4) |
| `skill` | register, grant, revoke, catalog | D-IMPL-12 catalog + D-IMPL-29 governance |
| `workflow` | invoke, status, resume, list | Workflow primitive (D-IMPL-17), state per D-IMPL-18 |
| `hitl` | queues, approve, reject, override, annotate | D-IMPL-20 typed queue transport |
| `replay` | show, resolve, render (audience Π per INV-CH7-91) | Replay engine + ArtifactStore resolution |
| `artifact` | get, put, inspect, resolve (hash ↔ URI per D-IMPL-26) | ArtifactStoreProtocol |
| `product` | get, list, classes | L6 delivery contract |
| `config` | show, set, bundle operations | Control Plane registry |

Every mutating verb is a Control Plane action; every action is audited; no verb accepts inline definitions (No-Hardcoding, CLAUDE.md §6.4). The verb inventory is illustrative at contract altitude — the exact flag surface is Phase I detail; the noun set and the artifact-file-only rule are the design commitments.

## 2.6 Replay contributions of the Experience pillar

Per CLAUDE.md §4, every pillar contributes to Decision Replay. The Experience Layer's contribution is the **calling surface**: which front door (MCP egress, CLI, HTTP), which authenticated principal, and which rendering (for replay-record consumption per INV-CH7-91) are captured on the relevant replay dimensions. HITL actions arriving through the MCP HITL surface (D-IMPL-20) carry the D-IMPL-21 `HumanPrincipalBinding` regardless of front door — notification and authority are separated so audit-by-construction cannot be bypassed from any Experience surface.

## 2.6a Seam-to-seam boundary notes

Three boundaries between the seams themselves are worth stating so Phase I does not blur them:

- **MCP egress vs A2A.** Both can carry a Context Product across a process boundary. The design rule: MCP egress serves consumers *inside* the trust boundary (or authenticated externals consuming read-only, entitlement-enforced by Π/Policy); A2A serves *cross-organizational* exchange where the product must be admitted into another fabric's graph — which is why admission verification (D-IMPL-16) exists on the A2A path and not on the egress path. A product read over MCP egress never enters another fabric's L3 through that read alone.
- **ArtifactStore MCP server vs egress MCP server.** Distinct server contracts, never merged (D-IMPL-13): egress serves live products and Experience access to consumers; the artifact server serves versioned artifacts to the fabric's own mechanism (and to replay tooling). Merging them would put replay substrate and consumer delivery on one trust surface.
- **Harness adapter vs OrchestrationProtocol.** Ruled under D-IMPL-17/D-IMPL-24: a harness adapter binds the agent-loop seams for one agent execution; an OrchestrationProtocol integration coordinates *many* agent executions. LangGraph appears on both lists as two separate integrations — the DESIGN.md synthesis carries the explicit boundary statement the D-IMPL-17 ruling requires.

## 2.7 Threat dispositions carried by this design (from the plan threat model)

- **T-02-25 (Spoofing, A2A producer identity) — mitigated by design:** detached-JWS product signing + consumer-side Control Plane verification per D-IMPL-15/D-IMPL-16; shown as the verification step and reject branch in `seq-a2a-admission.mmd`.
- **T-02-26 (Tampering, second writer via store or harness) — mitigated by design:** no store→L3 edge (§2.4) and no harness write handle (§2.3 seam 3); both constraints are visually enforced in the two seam diagrams and structurally enforced by the D-IMPL-41 stack.
- **T-02-27 (Elevation of privilege, harness skill over-exposure) — mitigated by design:** skill exposure is *exactly* the currently-bound skill-set (§2.3 seam 2); the D-IMPL-29 tier-1 compatibility check bounds what can ever be bound.

---

## 3. Coverage Notes

| INV key | Where designed | Disposition |
|---------|----------------|-------------|
| INV-CH6-06 | §1.1, §2.1 | mapped — MCP access-layer / CCF construction-layer boundary is structural in the role-allocation table |
| INV-CH7-91 | §1.2 | mapped — three renderings as recursive Π at the replay layer, surfaced via `ccf replay` and the HTTP replay endpoints |
| INV-CH8-07 | §1.1, §2.1 | mapped — Pattern 3 unchanged at L6; SDK bidirectional extension explicitly labeled |
| INV-CH8-08 | §2.2 | mapped — Pattern 4 first-class in v0; admission-through-L2, set-union lineage structural |
| INV-CH8-21 | §1.4 | deferred: Conversational Reporting Layer out of v0 scope per CLAUDE.md §13 (settled ruling); underlying primitives in scope individually |
| INV-CH8-24 | §1.4 | mapped — coexistence posture carried as the Experience Layer's non-goals boundary and ingestion-layer re-binding stance |

See-also entries touched here but owned elsewhere: INV-CH7-55/56 (Mode 3, design-orch-hitl.md), INV-CH7-80/86/89 (design-data-context-b.md), INV-CH6-05 (design-agent-types.md).

## 4. Phase I hand-off

Phase I.3 (cross-process) implements against §2.1–§2.2 and §2.4: the MCP client library and both server contracts, the WireProtocol default + fallback transports, the IdentityProvider reference implementations, and the ArtifactStoreProtocol with both reference stores. Phase I.4 (harness + experience) implements against §1 and §2.3: the three reference adapters and their conformance suite (including the `effects: unsupported` declared-capability check), the CLI, and the HTTP skeleton with generated OpenAPI. Every implementation module cites the D-IMPL ruling and the whitepaper or CLAUDE.md section it realizes, per CLAUDE.md §11 docstring discipline.
