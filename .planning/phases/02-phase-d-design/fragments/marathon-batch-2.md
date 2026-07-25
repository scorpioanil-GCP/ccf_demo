# Decision Marathon — Batch 2 Briefs (Agent Framework, Harness, Cross-Process/Trust)

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

Scope: agent framework — D-IMPL-11, 12, 19, 28, 29, 49; harness — D-IMPL-24, 25; cross-process/trust — D-IMPL-13, 14, 15, 16, 45, 46. Fourteen decisions; four on the Phase I gating list (11, 14, 24, 28). Presentation per locked D-02: recommendation first with rationale, then alternatives with consequences. Dave is the sole decision authority (CLAUDE.md §2); nothing here is a ruling. Homecams observations are triangulation data points, never defaults (CLAUDE.md §2.1).

**Batch-1 conditioning.** Every signature-level recommendation below assumes the batch-1 rulings now RESOLVED in docs/DECISIONS.md — above all **D-IMPL-01 (Python 3.12+ sole target, Pydantic v2 `extra=forbid`, Protocol-based seams)**, plus D-IMPL-04 (ccf + ccf-runtime packages, async-first runtime), D-IMPL-05 (multi-tenant first-class), D-IMPL-09 (LLMClientProtocol + Anthropic Citations adapter — interacts with D-IMPL-46 below), and D-IMPL-38 (typed, versioned Control Plane parameter artifacts, no silent defaults — the resolution shape several briefs below reuse).

Ordering rationale: gating decisions first — **D-IMPL-28** (definition artifact format; gates the Agent & Task Factory and therefore most of the agent surface), **11** (agent base shape; interacts with 19), **24** (harness targets; example 03 depends on it), **14** (A2A wire) — then 12, 19, 25, 29, 13, 15, 16, 45, 46, 49. Interactions noted inline: 12↔29 (skill catalog model vs skilling governance depth), 46↔09 (passage-citation provider vs LLM client Protocol).

---

## D-IMPL-28 — Definition artifact format (GATING)

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §6.4 (Agent & Task Factory and the No-Hardcoding Rule). Gates the factory and therefore most of the agent surface.

**Recommendation: YAML definition artifacts validated by Pydantic-native schemas with exported JSON Schema; Jinja2-templated prompt artifacts referenced by versioned URI; per-artifact-class independent semver lanes.** Concretely:

- **Schema language:** each definition artifact class (agent definition, task definition, workflow definition, skill catalog entry, skill grant) is a Pydantic v2 model (`extra=forbid`) in `/src` — the *interpreter* side of CLAUDE.md §6.4's "code contains interpreters and factories, never the things interpreted." The SDK exports JSON Schema from those models so non-Python tooling (editors, CI validators, external control planes) can validate artifacts without importing the SDK. Authoring format is YAML (JSON accepted — YAML is a superset for our purposes).
- **Prompt artifacts:** standalone files (markdown/text with Jinja2 templating for parameter slots), referenced from agent/task definitions by versioned URI (specialization axis 6, CLAUDE.md §6.2 channel 1) — never inline text in a definition, never a string literal in code. Template *parameters* are declared in the referencing definition so the factory validates the binding at construction time, not render time.
- **Versioning:** every artifact carries `schema_version` (the SDK's schema for that artifact class) and `artifact_version` (the artifact's own semver lane). Per CLAUDE.md §6.1, any change to a channel-1 axis is a new agent version. Artifact addressing/storage is D-IMPL-26's question (batch 3); this decision fixes the format and lane structure only.

Rationale:
- Pydantic-native schemas follow directly from the D-IMPL-01 ruling (Pydantic v2 `extra=forbid` as the typed-contract substrate) and CLAUDE.md §11 ("typed contracts at every boundary; validation at the boundary, never deferred") — the factory validates an artifact into a typed model before construction, giving the No-Hardcoding Rule (CLAUDE.md §6.4) a single typed choke point and giving the CI lint a crisp target ("agent construction that bypasses the factory" = construction not routed through the artifact model).
- Definition artifacts are Control Plane artifacts (INV-CH7-72 — agent/task/prompt/skill artifacts as additional Control Plane classes, SDK-defined; SPEC_INVENTORY "Agent & Task Factory + No-Hardcoding Rule" extension row), and agent version + skill-set in force land in replay dimension 4 (INV-CH7-84) — which is only tractable if versioning is structural in the artifact format, hence the two-field version discipline.
- Exported JSON Schema keeps the format harness- and language-neutral at the seam (success condition 3): an external control plane or a TS-based artifact editor can validate without Python.
- YAML agent/task definitions + Jinja2 prompt templates with a CI grep guard are a Homecams data point (not a default) for exactly this shape — recorded against D-IMPL-28 in docs/DECISIONS.md at Phase R.

**Alternative A — pure JSON Schema-first (schemas authored as JSON Schema; Pydantic generated or bypassed).** Consequence: maximally language-neutral authoring, but the factory's validation model and the schema drift apart unless code generation is added to the toolchain; Pydantic-native with *exported* JSON Schema gets the same neutrality with one source of truth.

**Alternative B — Python-native definitions (artifacts as Python modules/dataclasses).** Consequence: no schema/parser layer at all; but definitions become code, collapsing the CLAUDE.md §6.1 "agents are data, not code" separation — an agent in a `.py` file is a defect of the same class as a hard-coded half-life table, and the artifact can no longer live in an ArtifactStore or cross the A2A/Control Plane boundary as data.

**Alternative C — TOML or custom DSL.** Consequence: TOML handles nesting poorly for workflow/task graphs; a custom DSL is invention with a parser to maintain and no ecosystem tooling — disproportionate when YAML+JSON Schema is the industry-legible default.

---

## D-IMPL-11 — Agent base shape (GATING)

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §6 (interacts with the §6.1 archetype/agent separation and with D-IMPL-19 — whatever the shape, archetypes stay in code and agents stay in artifacts).

**Recommendation: a single concrete `Agent` runtime class (the factory's output type), specialized entirely by its definition artifact, with archetypes as composable behavior bundles (Protocol-typed capability mixins) attached by declaration — not a class hierarchy, and not archetype subclassing by users.** Concretely:

- The Agent Factory (§6.4) reads a definition artifact and produces an `Agent` instance carrying: identity + version, the six channel-1 specialization axes (CLAUDE.md §6.2), and the currently-bound skill-set (channel 2). There is one runtime class; "which kind of agent this is" is data, resolved from the artifact's archetype binding.
- Each of the six archetypes (CLAUDE.md §6.3) is SDK code shipping a bundle of mechanism patterns — execution shape, fabric-interaction pattern, replay obligations — expressed as Protocol-typed components the `Agent` composes at construction per the artifact's archetype list. Composition (a monitoring agent that is also an assembler) is the natural case: the artifact declares both archetypes; the factory attaches both bundles. (The composition semantics — conflict rules, ordering — are D-IMPL-19's question, below.)
- Users never subclass. CLAUDE.md §4 is explicit: "specialization... never through subclassing." Extension points are Protocols (skills, harness adapters, archetype components), consistent with CLAUDE.md §11 "prefer Protocols over inheritance."

Rationale:
- The archetype/agent separation (CLAUDE.md §6.1) is only structurally safe if there is nothing to subclass: a class hierarchy invites users to put agent identity in code, precisely the defect §6.1 names ("any agent found in library code is a defect"). A single configurable class makes "agents are artifacts" true by construction — the runtime type carries no per-agent behavior.
- Replay dimension 4 requires answering "which agent, which version, which configuration, which skill-set" from the record alone (INV-CH7-84; CLAUDE.md §6.1). A data-resolved agent makes that capture mechanical: everything that distinguishes agents is already serialized in the artifact. A hierarchy would scatter identity across types.
- The whitepaper's archetype grounding is functional, not taxonomic: INV-CH8-22 frames archetypes as a mapping framework of *patterns of agentic work*, and CLAUDE.md §6.3 states "archetypes are functional categories, not exclusive categories." Composition-by-declaration matches that; deep hierarchies cannot express "monitoring + assembler" without diamond problems.
- Harness neutrality (§6.5): the agent object is the SDK-side representation the Harness Adapter maps onto whatever loop executes it; a single class with a declared capability surface gives adapters one stable shape to bind, instead of N archetype classes × M harnesses.

**Alternative A — class hierarchy (`Agent` base, six archetype subclasses, users configure instances).** Consequence: familiar OO shape and per-archetype typing for free; but archetype composition needs multiple inheritance, users will subclass (the path exists), and the artifact/code boundary erodes — the factory would have to map artifacts onto a type taxonomy rather than a capability set.

**Alternative B — pure Protocol, no shipped runtime class (SDK defines `AgentProtocol`; deployments supply the class).** Consequence: maximal flexibility; but then the SDK ships no working agent surface, every deployment reinvents replay capture and skill binding, and the factory has no construction target — adoptability (success condition 4) and the §9 examples suite both fail out of the box.

**Alternative C — six independent concrete classes, no shared base.** Consequence: simplest per-archetype code; but cross-archetype composition becomes impossible and shared obligations (replay capture, skill governance, context-contract enforcement) get six implementations to keep in sync.

---

## D-IMPL-24 — Harness adapter targets for v0 (GATING)

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.3. Example 03 (harness portability) and the adapter surface cannot be built without it.

**Recommendation: confirm the presumptive pair — Google ADK and the Claude Agent SDK — as the two v0 reference adapters; LangGraph waits for post-v0 (tracked as the named third candidate), with the `HarnessAdapterProtocol` designed against all three so the deferral costs nothing structurally.**

Rationale:
- CLAUDE.md §7.3 already names ADK + Claude Agent SDK as the presumptive pair; both are Python-native, which the D-IMPL-01 ruling makes the deciding tiebreak — adapters and example 03 are cheapest and most credible in-language.
- Two is the minimum that proves the claim: harness neutrality is "demonstrated, not asserted" (CLAUDE.md §7.3), and example 03's portability assertion (one agent definition, two harnesses, equivalent Context Product consumption and replay records) needs exactly two conforming adapters. A third adapter adds cost without adding proof.
- The pair is well-chosen adversarially: ADK and the Claude Agent SDK differ meaningfully in tool-exposure model, context injection surface, and trace shape — if the four seams (context injection, skill exposure, effect capture, replay hooks) bind cleanly to both, the Protocol is unlikely to be secretly shaped like either. Designing the Protocol with LangGraph's graph-of-nodes model also on the whiteboard (without shipping the adapter) guards against a two-point overfit.
- Zero-harness-imports-in-core (CLAUDE.md §1, §7.3, §11; SPEC_INVENTORY invariant table) is unaffected by target count — adapters live in `/runtime/adapters/<harness>/` regardless — but each shipped adapter is a CI matrix entry; two keeps the v0 CI surface proportionate.

**Alternative A — ship all three (ADK, Claude Agent SDK, LangGraph) in v0.** Consequence: broader launch appeal; but a third adapter + third CI leg + third example-03 variant is real v0 cost, and LangGraph's orchestration-flavored model overlaps confusingly with the SDK's own Workflow primitive (§8.1) — better resolved after the OrchestrationProtocol (D-IMPL-17) settles.

**Alternative B — one adapter (Claude Agent SDK only) plus a bespoke-loop demo.** Consequence: cheapest; but a bespoke loop written by us is not an independent harness — example 03's portability claim degrades to a self-assertion, and success condition 3 loses its demonstration.

**Alternative C — swap LangGraph in for ADK.** Consequence: viable pair; but ADK exercises a materially different vendor ecosystem (and A2A adjacency, given Google's role in A2A standardization — relevant to D-IMPL-14), which makes ADK the stronger neutrality witness.

---

## D-IMPL-14 — A2A wire protocol (GATING)

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.2. WireProtocol abstraction is already committed; this rules the v0 default transport.

**Recommendation: adopt the Linux Foundation A2A protocol (the Google-originated, LF-governed Agent2Agent standard: JSON-RPC over HTTPS with the Agent Card discovery and task/artifact model) as the v0 default `WireProtocol` implementation, carrying the typed Context Product as the artifact payload; mTLS via deployment configuration; a plain typed-HTTP fallback transport ships as the second reference impl for environments that reject the A2A dependency.**

Rationale:
- CLAUDE.md §7.2's own posture: "a `WireProtocol` abstraction with the most production-credible primitive as the v0 default." At 2026 state, the LF A2A protocol is the only multi-vendor, foundation-governed candidate with real ecosystem adoption — "A2A" in the whitepaper (INV-CH8-08 names A2A standards as industry-emergent) now has a concrete industry referent, and aligning the SDK's federation surface with it is the credibility-maximizing default.
- The stable layer is preserved by construction: INV-CH8-07/CLAUDE.md §7.2 commit that "the Context Product Contract is the stable layer; the wire is replaceable." The Contract travels as a typed payload inside the A2A artifact; consumer-side Control Plane verification of Policy bindings before graph admission (INV-CH8-08's structural invariant; CLAUDE.md §7.2, §10) happens above the transport, so swapping wires never touches trust mechanics.
- The fallback typed-HTTP transport keeps the WireProtocol abstraction honest (two impls, per the CLAUDE.md §11 reference-impl discipline) and serves closed deployments; it also gives the composition-preservation of lineage continuity (inbound L set-union extension) a transport-independent test.
- Interaction: D-IMPL-15 (identity/signing) layers on whichever wire is chosen; the LF A2A choice biases toward its native auth surface but does not decide 15.

**Alternative A — custom typed RPC over HTTP/2 + mTLS.** Consequence: full control of the wire schema and no external-spec tracking; but the SDK then owns a federation protocol nobody else speaks — cross-*organizational* exchange (the whole point of Pattern 4) requires the counterparty to install our stack, and the emergent-standard alignment CLAUDE.md §7.2 gestures at is abandoned.

**Alternative B — MCP-as-the-A2A-wire (Context Products as MCP Resources across org boundaries).** Consequence: one protocol surface for everything (§7.1 already makes us an MCP server); but MCP is a resource/tool access protocol, not an agent-task federation protocol — no native task lifecycle, discovery, or counterparty attestation model, so identity/admission (D-IMPL-15/16) would be entirely bolted on. Fine as an *additional* egress (it already exists at L6); wrong as the federation default.

**Alternative C — defer the default (ship WireProtocol + in-process loopback only).** Consequence: no external dependency risk; but A2A federation is a v0 commitment, "not a v1 deferral" (CLAUDE.md §7.2), and example 04 requires a real cross-process wire — deferral fails the plan's own scope.

---

## D-IMPL-12 — Skill catalog model

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §6. Interacts with D-IMPL-29 (skilling governance depth — 29 rules how deep the grant-time governance goes; this rules what the catalog *is*).

**Recommendation: a Control Plane skill catalog with dynamic registration — skills registered as typed, versioned Control Plane artifacts (per the D-IMPL-28 artifact format) at boot *or* at runtime through an audited Control Plane action; MCP Resources/Tools are one skill *type* among four, not the unified mechanism.** Concretely: the catalog entry schema declares skill identity + version, type (local callable | MCP resource/tool | A2A endpoint | tool), and its *requirements declaration* (what policy scope, context-contract access, and egress the skill needs) — the input to the D-IMPL-29 compatibility check. Grants/revocations are separate artifacts referencing catalog entries by version.

Rationale:
- CLAUDE.md §6.2 already commits the load-bearing properties: skills are "typed, governed capabilities registered in the skill catalog," binding "by reference," attachable/revocable "over the agent's life through the Control Plane without re-declaring the agent," with every grant/revocation an audited Control Plane action captured in replay. A static boot-time-only registry cannot honor "over the agent's life"; dynamic-through-Control-Plane is the minimal model that can.
- The four skill types are CLAUDE.md §6.2's own enumeration ("tools, MCP resources, A2A endpoints exposing remote Context Products, or local callables"); collapsing all skills into MCP-Resources-as-skills would force local callables and A2A endpoints through an MCP indirection for uniformity's sake — protocol-shaped mechanism where a typed catalog entry suffices, and a violation of the "MCP is transport, not semantics" posture (INV-CH8-07).
- Requirements declaration in the catalog entry is what makes the §6.2 governance check mechanical ("the Control Plane refuses a skill bind whose declared requirements exceed the agent's policy regime or context contract") — without a declared-requirements schema the check has nothing to evaluate. The schema itself is shared with D-IMPL-29.
- Skill-set-in-force lands in replay dimension 4 (INV-CH7-84; CLAUDE.md §6.2) — versioned catalog entries + versioned grants make "the skills the agent actually had" resolvable by reference, the same discipline as D-IMPL-38's parameter versioning.

**Alternative A — static registry at boot only.** Consequence: simpler and fully deterministic; but revocation mid-life requires a restart, "upgraded, or revoked over the agent's life" (§6.2) becomes false, and example 02 (grant → exercise → revoke on a running agent) cannot run as specified.

**Alternative B — MCP-Resources-as-skills as the unified mechanism.** Consequence: one discovery/invocation surface and free interop with MCP-speaking harnesses; but every local callable needs an MCP wrapper, the governance metadata (requirements declaration, grant lineage) has no native home in MCP's resource model, and the catalog's trust posture gets conflated with the egress server's (§7.1 warns the roles differ).

---

## D-IMPL-19 — Agent archetype expression

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §6.3. Pairs with D-IMPL-11 (this rules *how* archetype behavior bundles compose; 11 rules the base shape they attach to).

**Recommendation: composition over mixins — archetypes are Protocol-typed component bundles the factory attaches to the single `Agent` class per the artifact's declared archetype list; multi-archetype agents are ordered composition with explicit conflict rules (identical obligation contributed twice → deduplicated; conflicting configuration defaults → declaration order wins, factory warns; hard contradictions → factory construction error).**

Rationale:
- Follows the D-IMPL-11 recommendation structurally: with a single runtime class and no user subclassing, Python mixins (MRO-based) have no user-facing class to mix into — composition-by-declaration is the shape that keeps archetype semantics in data-interpreted-by-factory rather than in an inheritance graph.
- CLAUDE.md §6.3 names the requirement directly: "archetype composition as mixins-or-composition... rather than as a deep hierarchy," with the monitoring-agent-that-is-also-an-assembler as the canonical composite. Component bundles express that as a list; MRO would express it as a linearization users must reason about.
- Archetype obligations are additive in the common case — a `MonitoringSurveillanceAgent` + `ContextAssemblyAgent` composite has the trigger-driven execution pattern *and* the product-emission obligation (INV-CH7-32's assembler-swarm grounding; INV-CH8-22's archetype mapping framework treats the categories as overlapping patterns of work, not partitions). Explicit conflict rules make the non-additive edge deterministic and factory-validated instead of MRO-accidental.
- Replay: the composed archetype list is part of the agent's channel-1 identity (axis 1, CLAUDE.md §6.2) and lands in dimension 4 — a declarative list serializes; an MRO does not.

**Alternative A — Python mixin classes (archetypes as mixins, factory synthesizes a type per combination).** Consequence: idiomatic-looking and per-combination isinstance checks for free; but dynamic type synthesis complicates pickling/replay/introspection, conflict resolution becomes MRO linearization (opaque to artifact authors), and the synthesized types leak toward the subclassing path D-IMPL-11 closes.

**Alternative B — templates (each combination pre-shipped as its own archetype).** Consequence: no composition machinery at all; but combinations explode (6 archetypes → 63 non-empty subsets), the SDK ends up shipping combination code users didn't ask for, and novel combinations require SDK releases — the opposite of specialization-without-forking (CLAUDE.md §4).

**Alternative C — single archetype per agent, composition via multi-agent workflows instead.** Consequence: simplest factory; but forces a workflow (and a process/orchestration hop) where the whitepaper's own examples describe one agent doing both kinds of work — a fidelity mismatch with §6.3's explicit composite case.

---

## D-IMPL-25 — HarnessAdapterProtocol seam scope

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.3 (the four seams: context injection, skill exposure, effect capture, replay hooks).

**Recommendation: three seams mandatory for every conforming adapter — context injection, replay hooks, and effect capture *as governed refusal* — with skill exposure conditionally mandatory (required iff the bound agent has a non-empty skill-set). Concretely, a read-only consumer adapter may declare `effects: unsupported`, in which case the adapter must structurally guarantee no write-back path exists (declared capability, verified by the conformance suite), not merely leave the seam unimplemented.**

Rationale:
- Context injection and replay hooks are the two seams that carry CCF's non-negotiables. Without context injection the adapter isn't delivering the fabric at all; without replay hooks, dimension capture (model version, prompt-artifact version, execution trace — INV-CH7-84, CLAUDE.md §7.3 seam 4) breaks audit-by-construction, which is a CI-enforced invariant (SPEC_INVENTORY invariant table), not an optional feature. Neither can be optional for a *conforming* adapter.
- Effect capture is where the open question bites ("is effect capture optional for read-only consumers?"). The single-writer invariant must "hold across the adapter boundary" (CLAUDE.md §7.3 seam 3; §10 extends single-writer across harness effect capture). The safe resolution is that the *seam contract* is mandatory but satisfiable by a verified-absent capability: an adapter either routes effects through governed emission/L2 write-back, or proves it exposes no effect path. What must never exist is a middle state — an adapter that executes effects outside governance because the seam was "optional."
- Skill exposure conditional-on-skill-set follows from §6.2/§7.3: "skills the agent has not been granted do not exist from the harness's point of view" — for a skill-less agent (pure consumer of a Context Product), there is nothing to expose, and mandating a no-op seam adds conformance cost without governance value. If the agent has skills, exposure is mandatory: partial exposure would silently narrow the agent's declared capability set, corrupting replay's "skills in force."
- Conformance is testable: the Protocol carries a capability declaration; the adapter conformance suite (the thing example 03's equivalence assertion runs on) exercises each declared seam and asserts the absence guarantees for undeclared ones.

**Alternative A — all four seams unconditionally mandatory.** Consequence: simplest conformance story; but read-only consumption adapters (the CLAUDE.md §7.3 case: "a harness that already speaks MCP needs no adapter for consumption") get saddled with dead seams, and the ecosystem answer becomes "don't write an adapter" — shrinking the surface the Protocol governs.

**Alternative B — only context injection mandatory; the rest optional.** Consequence: maximal adapter adoption; but optional replay hooks break audit-by-construction for any decision executed under such an adapter, and optional effect capture opens the exact ungoverned-write path §10 structurally excludes — both are invariant defects, not flexibility.

---

## D-IMPL-29 — Skilling governance depth

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §6.2. Interacts with D-IMPL-12 (the requirements-declaration schema lives in the catalog entry) and D-IMPL-20 (HITL transport, batch 3).

**Recommendation: two-tier governance, both mechanism — tier 1, the automatic policy-compatibility check (always on, non-waivable: the Control Plane refuses a bind whose declared requirements exceed the agent's policy regime or context contract); tier 2, policy regimes may *declare* that grants (all, or matching declared criteria — e.g., skill type A2A-endpoint, or egress-bearing skills) additionally require an ApprovalGate before taking effect. Whether tier 2 is engaged, and for which grants, is Control Plane configuration — values, not SDK policy. Skill requirements declaration schema: the typed requirements block on the D-IMPL-12 catalog entry (policy scope required, context-contract access, egress declaration), validated per D-IMPL-28's artifact discipline.**

Rationale:
- Tier 1 is already committed verbatim by CLAUDE.md §6.2 ("The Control Plane refuses a skill bind whose declared requirements exceed the agent's policy regime... This compatibility check is mechanism, shipped with the SDK") — not actually open; the open part is whether governance can go deeper.
- Tier 2 as *configurable* is the mechanism/values split applied to governance depth: whether a deployment requires human approval on grants is domain/regulatory judgment (SR 11-7-style change control is exactly the regulated-enterprise case the whitepaper serves), so the SDK ships the capability and the deployment declares the policy — the same resolution shape as D-IMPL-38/39/40 in batch 1.
- The HITL machinery already exists to serve it: ApprovalGate (CLAUDE.md §8.2) with audit-by-construction means an approval-gated grant lands in replay with approver identity for free; D-IMPL-43 (closed-loop interpretation, batch 3) notes the same HITL-configurability interaction, so this posture keeps the governance surfaces uniform.
- Replay: grant, approval (if gated), and effective-time all land in the audit record (§6.2: "a skill grant or revocation is itself an audited Control Plane action") — two-tier changes nothing about capture, only about when a grant becomes effective.

**Alternative A — automatic check only, no approval workflow on grants.** Consequence: simpler v0 and faster grants; but regulated deployments that require human change-control on capability changes must build it outside the SDK, and the HITL pillar's own machinery sits unused at the one Control Plane action CLAUDE.md §6.2 singles out as governance-critical.

**Alternative B — approval workflow always required on every grant.** Consequence: maximal control; but it is SDK-imposed policy (a value), makes example 02's grant/revoke cycle require a human in the loop for a demo, and punishes low-risk local-callable grants identically with cross-org A2A grants.

---

## D-IMPL-13 — MCP role allocation

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.1 (five MCP roles: L1 ingress, L4–L5 content acquisition, L6 egress, Experience access, ArtifactStore transport).

**Recommendation: allocate MCP to exactly the five CLAUDE.md §7.1 edges, realized as two shared libraries and three server/config surfaces — (1) one `ccf` MCP *client* library used in two roles: L1 ingress (client sessions wrapped by a source adapter normalizing into the D-IMPL-33 `SignalEnvelope`) and L4–L5 content acquisition (client sessions invoked by operators/projections, results entering the fabric only through the sanctioned acquisition path); (2) one `ccf-runtime` MCP *egress server* serving Context Products as MCP Resources and permitted agent invocations as MCP Tools (L6 + Experience access are one server, two resource families); (3) a *separate* ArtifactStore MCP server contract (the §7.4 persistence transport), never merged with egress. Per-role API: `MCPSourceAdapter` (ingress config artifact declaring server, resources, mapping), acquisition client Protocol for L4–L5, egress server configuration as Control Plane artifacts, ArtifactStore per D-IMPL-26/27 (batch 3).**

Rationale:
- The five edges are already committed by CLAUDE.md §7.1; the genuinely open part is the module/API allocation, and §7.1 constrains it: "SDK-as-MCP-client and SDK-as-MCP-server live in different modules; their contracts and trust postures differ, and the artifact-persistence role is distinct from the egress role." Two client roles sharing one client library is safe (same trust posture: we consume external servers); egress and artifact-store servers must stay distinct (public-ish decision surface vs inside-the-tenant-boundary persistence — different authn posture per §7.4).
- Packaging follows D-IMPL-04: client library usable from the fabric core path lives with `ccf`; servers are runtime concerns in `ccf-runtime`. This keeps L6 egress honoring INV-CH8-07's transport-independence (the Contract is the application layer; MCP is one serving choice) and INV-CH6-06 (MCP as access layer; fabric internals opaque).
- L4–L5 acquisition through the same client surface as L1 (different call sites, same library) realizes the §6.6 search-inference recursion placement (INV-CH6-07 hook) without a second MCP stack; single-writer is unaffected because acquisition results reach L3 only via L2 (CLAUDE.md §10).

**Alternative A — MCP everywhere-by-default (also inter-layer transport internally, skills-as-MCP per D-IMPL-12-alt).** Consequence: one protocol to rule everything; but internal layer boundaries are in-process typed contracts (INV-CH7-09/10), and inserting a wire protocol between L4 and L5 is pure overhead plus a serialization seam where the algebra requires typed composition.

**Alternative B — minimal MCP (egress only, per the whitepaper's Pattern 3; ingress via CDC/file adapters only).** Consequence: closest to the whitepaper's literal commitment; but abandons the SDK's own §7.1 bidirectional extension — content-rich query-based sources (document repos, comms archives) then need bespoke adapters per source, and the ArtifactStore reference implementation (§7.4, committed) has no transport.

---

## D-IMPL-15 — Agent identity and signing

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.2 (identity and attestation: agent identity, signing of emitted products, verification of inbound signatures).

**Recommendation: an `IdentityProvider` Protocol with a two-layer model — workload/transport identity via mTLS (X.509) as deployment configuration, and product-level signing via JWS (detached JSON Web Signature over the canonical serialized Context Product, carrying producer agent identity + version + key id) verified at the consumer's Control Plane during A2A admission. Reference impl: static-keypair JWS signer/verifier (dev) + certificate-backed keys (production posture); SPIFFE/SPIRE explicitly supported as an *implementation* of the Protocol, not required by it.**

Rationale:
- The invariant to serve is consumer-side verification before admission (INV-CH8-08; CLAUDE.md §7.2): the consuming Control Plane must verify *who produced this product and that its Policy bindings are intact* — that is a payload-level signature question, not just a channel question, because the product may be persisted/relayed after transport ends (lineage continuity keeps the producer's plan/snapshot/policy version attached; the signature must cover them). Hence signing at the product layer, with transport identity as the outer layer.
- JWS over the typed product aligns with the D-IMPL-14 recommendation (LF A2A is JSON-RPC-native; JOSE is its ecosystem's signing idiom) and with D-IMPL-01 (mature Python JOSE tooling); X.509/mTLS for the channel is the boring, universally deployable choice.
- Protocolizing identity (rather than mandating SPIFFE) keeps deployment topology out of SDK scope (CLAUDE.md §13: production deployment topology is "not the SDK's problem"); SPIFFE/SPIRE-based identity slots in as a conforming provider for mesh deployments.
- Interaction noted for batch 3: D-IMPL-21 (HITL approver identity binding) asks whether human identity rides the same PKI — the Protocol shape here is designed to admit that reuse without deciding it.

**Alternative A — SPIFFE/SPIRE as the mandated identity substrate.** Consequence: best-in-class workload identity with rotation for free; but mandates infrastructure many deployments (and the §9 quickstart) don't run — a deployment-topology mandate §13 excludes.

**Alternative B — JWT bearer tokens only (no product signing).** Consequence: simplest; but a bearer token authenticates the *session*, not the *artifact* — a relayed or stored product loses its provenance proof, weakening the INV-CH8-08 admission check to "trust whoever handed it to me."

**Alternative C — custom signature scheme over a bespoke canonical form.** Consequence: full control; but crypto invention with no interop payoff — JOSE canonicalization pain is real but solved, and a bespoke scheme fails the emergent-standards alignment argument that carried D-IMPL-14.

---

## D-IMPL-16 — Control Plane scope at A2A boundary

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.2.

**Recommendation: verify every inbound A2A Context Product — full Control Plane verification (signature, Policy bindings, contract validation, lineage integrity) on every admission, no fast path in v0. Peer trust tiers exist only as *configuration of what is admissible* (which producers, which product classes, which policy regimes a peer may assert), never as verification skips. Performance relief, if ever needed, comes post-v0 from verification *caching* (memoized checks keyed on immutable artifact identity) — which preserves the verify-everything semantics — not from trust-tier bypasses.**

Rationale:
- The whitepaper's commitment is structural, not advisory: Policy bindings "verified at the consumer's Control Plane **before admission** into the consuming fabric's graph" (INV-CH8-08), and CLAUDE.md §7.2 restates it as a structural commitment ("an inbound A2A Context Product is not admissible to L3 until the consuming Control Plane validates its Policy bindings"). A high-trust fast path is precisely a conditional code path around an invariant — the same defect class the tenancy ruling (D-IMPL-05) refused.
- Fail-closed posture (INV-CH7-67: conservative bias; uncertainty surfaced, never smoothed) extends naturally to the trust boundary: the absence of verification is not evidence of validity. A trust tier that skips verification converts a peer compromise into silent graph contamination — the exact "silent correctness failure" §7.7.9 rejects.
- Single-writer discipline already routes every admission through L2 (CLAUDE.md §10); verification-before-L2 is one call site, so the mechanism cost of verify-everything is a single choke point, not a scattered tax. Admission verification results (and the policy version verified against) land in lineage — replay of a cross-org decision can show the admission check that let the product in.
- Trust *configuration* (not verification skips) still gives high-trust peers real value: broader admissible product classes, larger payload/rate envelopes — governance expressed as what is allowed, not as what is unchecked.

**Alternative A — fast-path admissions for designated high-trust peers (verify signature only; skip policy/contract validation).** Consequence: lower admission latency; but creates the conditional-bypass path around a whitepaper structural invariant, and the trust designation itself becomes the attack surface. Fidelity defect.

**Alternative B — asynchronous verification (admit provisionally, verify in background, evict on failure).** Consequence: best latency under load; but "provisionally admitted" state in L3 violates admission-before-graph-entry outright, and eviction of already-consumed context is not a coherent operation under append-only lineage.

---

## D-IMPL-45 — Model-trace composition seam

**Origin:** docs/DECISIONS.md D-IMPL-45; whitepaper §7.10.2 (INV-CH7-86).

**Recommendation: a `TraceCorrelationHook` on replay dimension 5 (Content Generation Path), attached at the Harness Adapter's replay-hooks seam (CLAUDE.md §7.3 seam 4) — the CCF replay record stores a typed *external trace reference* `{trace_provider, trace_id, trace_url?, capture_time}` per LLM invocation, and the SDK ships an `ExternalTraceProviderProtocol` (correlate: emit the reference at call time; resolve: fetch/link at replay time) with a no-op reference impl and one worked integration in the examples/docs. CCF owns environment replay; the external tool owns model-internals tracing; the seam is a stored correlation, not an ingestion.**

Rationale:
- §7.10.2's posture (INV-CH7-86) is compositional: a mature deployment *composes* CCF environment replay with an external model-trace tool (LangSmith/Weave) — the whitepaper never asks CCF to absorb model-internal traces, so the fidelity-preserving seam is a correlation id, not trace storage. Storing a reference keeps the five-dimension record complete-by-construction (dimension 5 knows an external trace exists and where) without importing another tool's data model.
- The adapter's replay-hooks seam is the natural attachment (the entry's own observation): the harness executes the model call, so the harness adapter is the only component positioned to capture both the CCF-side invocation identity and the external tool's trace id in the same instant.
- Protocol + no-op reference keeps the whole thing optional-by-configuration: deployments without a trace tool lose nothing; the replay record's own guarantees (INV-CH7-80's "what did the agent know" test) never depend on the external tool's availability or retention.

**Alternative A — ingest external traces into the ArtifactStore (CCF stores trace payloads).** Consequence: replay is self-contained even if the trace vendor purges data; but CCF takes on another tool's schema churn and storage volume, and the boundary CLAUDE.md §13 draws (harness-internal behavior is not CCF's problem) blurs — model-internals become our retention obligation.

**Alternative B — no seam; deployments correlate by timestamp out of band.** Consequence: zero SDK surface; but correlation-by-timestamp is exactly the brittle manual join §7.10.2's composition framing exists to avoid, and dimension 5 stays silently incomplete for LLM-invoking paths.

---

## D-IMPL-46 — Passage-citation provider Protocol

**Origin:** docs/DECISIONS.md D-IMPL-46; whitepaper §7.10.3 (INV-CH7-87). Interacts with D-IMPL-09 (ruled: `LLMClientProtocol` with citations as an optional capability surface; this entry owns the passage-citation provider shape specifically).

**Recommendation: a `PassageCitationProvider` Protocol *separate from* `LLMClientProtocol`, defined by its output contract — generated claims each carrying zero-or-more typed passage anchors in the whitepaper's L-anchor forms (`{document, page, paragraph, offset_span}` / `{transcript_id, timestamp, text_span}` per INV-CH7-19), with a provider-identity+version field for replay. Two reference impls: (1) the Anthropic Citations adapter (thin bridge over the D-IMPL-09 client's citation capability — the first-class path); (2) a deterministic post-hoc span-matcher (aligns generated claims to source passages algorithmically) as the vendor-neutral fallback and CI-testable impl. The ReviewQueue (§8.2) and ContentGenerationAgent archetype consume the Protocol, never a vendor API.**

Rationale:
- The whitepaper's own language dictates a Protocol: passage citations are "populated by whatever component primitive the deployment has selected" (INV-CH7-87) — the commitment is to the *anchor contract on the output*, not to a provider. Defining the Protocol by its typed output (L-anchor forms already committed at INV-CH7-19) keeps every downstream consumer (per-claim lineage, ReviewQueue's claim-to-anchor display, INV-CH7-68's per-claim debt decomposition) provider-independent.
- Separation from `LLMClientProtocol` respects the D-IMPL-09 ruling's own structure: the ruling made citations an *optional capability* of the client and explicitly deferred the provider Protocol here. A capability-bearing client backs the best provider impl; a client without the capability still gets citations via the post-hoc matcher — capability variance stays behind the provider seam instead of leaking into every call site.
- The deterministic fallback is test-strategy infrastructure (same rationale as D-IMPL-07's local embedder): CI can assert passage-anchoring invariants ("every claim passage-anchored," INV-CH8-12 Synthesis) without network access, and the fallback honestly reports lower anchor confidence — surfaced, not smoothed.
- Provider identity + version in the output feeds replay dimension 5 (which primitive produced these anchors is part of the content generation path).

**Alternative A — citations stay a capability flag on `LLMClientProtocol` only (no separate provider Protocol).** Consequence: one less Protocol; but every consumer must branch on capability presence, non-citing vendors have no citation path at all, and the §7.10.3 "whatever component the deployment selected" pluggability is unrealized.

**Alternative B — SDK mandates the Anthropic Citations API as the citation mechanism.** Consequence: strongest anchors with least code; but hard-binds a vendor into a whitepaper-committed mechanism surface — the same breach Alternative A of D-IMPL-09 was rejected for.

---

## D-IMPL-49 — Projection-plan selection signature

**Origin:** docs/DECISIONS.md D-IMPL-49; whitepaper §7.5 (silent on selection inputs); homecams-patterns appendix (data point only, never a default).

**Recommendation: canonical selection signature `(perspective, context_product_class, selection_params)` — the projection plan is selected from the requesting principal's perspective (the Π role-conditioning that is already channel-1 axis 3 of the agent definition) plus the requested Context Product class, with an optional typed `selection_params` block (declared per product class in the Control Plane, per the D-IMPL-38 parameter discipline). Explicit *intent modeling* — inferring decision intent from the request — is out of v0 scope; where a deployment's plan selection varies by intent, intent is expressed as a declared enum-valued selection parameter on the product class, i.e., configuration, not inference.**

Rationale:
- The two non-optional inputs are already whitepaper-committed: Π is role/perspective conditioning (INV-CH5-03/04's Π dimension; §7.5's projection engine), and the product cache identity is keyed on schema name + ProjectionPlan identifier + principal binding (INV-CH7-52) — so perspective and product class *must* parameterize selection for the delivery layer's identity model to cohere. The recommendation commits exactly those, plus a governed escape hatch.
- The Homecams triple `(agent role, decision intent, product contract)` is a data point confirming role and contract as selectors; its third element, free intent modeling, is the part that would drag an unspecified inference problem (what is "intent," who computes it, how is it replayed?) into a whitepaper-silent surface — invention against the §15 discipline. Declared `selection_params` capture the same variability as typed, versioned, replay-captured configuration.
- Replay: `(perspective, product_class, selection_params, plan_version)` fully determines the selected plan — deterministic selection is what lets §7.10 replay re-resolve the identical ProjectionPlan; an inferred-intent input would need its own capture-and-replay story.
- Agent integration is free: the agent definition already binds perspective (axis 3) and context contract (axis 2), so an agent's product requests carry the signature without new declaration surface.

**Alternative A — adopt the Homecams triple including decision intent as a first-class SDK concept.** Consequence: richer selection out of the box; but the SDK must then define an intent model the whitepaper never specifies (invention), and intent inference at request time injects nondeterminism into a replay-critical path.

**Alternative B — perspective-only selection (one plan per perspective).** Consequence: simplest; but a perspective serving multiple product classes (the normal case — one role, many products) has no way to vary the plan per product, contradicting INV-CH7-52's per-product plan identity.

**Alternative C — free-form selection context (untyped dict passed through).** Consequence: maximal flexibility; but untyped selection inputs cannot be validated at the boundary (CLAUDE.md §11) or meaningfully replay-captured — the D-IMPL-38 no-silent-shapes posture applies.

---

*End of batch 2 briefs. 14 decisions — gating: D-IMPL-28, 11, 24, 14; then 12, 19, 25, 29, 13, 15, 16, 45, 46, 49. Ruling session (Task 2) presents these one at a time in that order; every ruling logs to docs/DECISIONS.md immediately per locked D-01/D-04. Dave rules; deferral adopts the recommendation as PROVISIONAL pending confirmation at D-GATE-D.*
