# Inventory Fragment — Chapter 7 slice C (§7.8–§7.10)

**Canonical authority:** `docs/CCF_Whitepaper_1-2.md` — the whitepaper `.md` is
authoritative; every citation below references its sections, never the PDF
(locked D-01). Extraction gated on `fragments/spotcheck-report.md`
`VERDICT: PASS` (locked D-03).

Key range: `INV-CH7-70` upward (mechanism-core slice three: Control Plane vs
Data Plane, Closed-Loop Self-Learning, Decision Replay). Seven-field entry
contract per `01-PATTERNS.md`; open questions are quoted and UNNUMBERED —
`D-IMPL-NN` numbers are assigned only by the synthesis task.

---

### INV-CH7-70 — Control Plane / Data Plane separation as first-class primitives

- **Whitepaper section:** §7.8, §7.8.1
- **Commitment (paraphrase):** The fabric commits to a structural separation
  between the Control Plane — the plane that defines what the fabric is
  allowed to do at runtime (policies, operator behavior parameters,
  projection rules, entitlements, D_c thresholds, λ_c values,
  materialization rules) — and the Data Plane — the plane that executes
  against those definitions (assembly engines, operator runtimes, projection
  computations, context-product serving, decision-replay record writers).
  The pattern is adopted from the service-mesh ancestry (Istio/Envoy); CCF
  claims novelty only in the cargo: the Control Plane carries Policy
  definitions, Operator behavior rules, Projection rules and Entitlements,
  per-decision-class D_c thresholds, per-observation-type λ_c, and
  Materialization policy; the Data Plane carries the assembly runtime,
  operator execution engine, projection computation engine, product serving
  tier, and replay-record writers.
- **Type signature:** none given (architectural separation; cargo classes
  enumerated in prose).
- **Invariants:** Control Plane holds definitional authority; Data Plane
  engines execute against Control Plane definitions without owning them.
  Configuration propagates to the Data Plane "under controlled handoff
  protocols."
- **Dependencies:** λ_c table (§7.7, slice B entries), D_c thresholds
  (§7.7), operator behavior (§7.4), projection rules (§7.5),
  materialization/cache tier (§7.6). Governance D-40 (service-mesh
  ancestor).
- **Figure refs:** Fig-CH07-21 (planes with CCF-specific cargo; named
  load-bearing — §7.8 refers back to it for the audit-plane property, the
  configuration surface, and the invariant-enforcement boundary).
- **Open question:** none.

### INV-CH7-71 — The Control Plane is also the audit plane

- **Whitepaper section:** §7.8.2
- **Commitment (paraphrase):** "The control plane is also the audit plane."
  Every Operator invocation, Projection computation, and Context Product
  assembly is observable from the Control Plane for replay — as a
  first-class architectural property of the Control Plane itself, not a
  sidecar observability concern. Every configuration change the Control
  Plane applies (policy version, operator-parameter adjustment,
  projection-rule refinement) is versioned, timestamped, and retained
  against the decisions made under the version in force at the time. The
  audit question — what did the agent know, under what policies, with what
  perspective conditioning, producing what content — is answered by
  reconstructing Control Plane state at decision time and replaying Data
  Plane execution under it (resolved in full by the §7.10 five-dimension
  record).
- **Type signature:** none given.
- **Invariants:** Every runtime decision auditable against the exact
  rule-state in force at decision time; every policy update is a versioned
  event with its own audit entry, and Data Plane invalidation flows as a
  published event, not a direct side-effect on cache state (Fig-CH07-22);
  every policy update traverses that sequence exactly once.
- **Dependencies:** INV-CH7-70 (plane separation); §7.10 replay record
  (INV-CH7-81); §7.6 cache state machine (Fig-CH07-14
  InvalidatedBySupersession). Governance D-41 (control-plane-is-audit-plane).
  Regulatory anchors named: SR 11-7, OCC consent-order re-tracing, EU AI Act.
- **Figure refs:** Fig-CH07-22 (Control Plane ⇄ Data Plane message exchange
  sequence; load-bearing — renders versioned-audit-entry and event-published
  invalidation; named as runtime enactment of D-40, D-41, D-42, D-44).
- **Open question:** none.

### INV-CH7-72 — Control Plane configuration surface enumeration

- **Whitepaper section:** §7.8.3
- **Commitment (paraphrase):** A production Control Plane carries, at
  minimum, six versioned, auditable, controlled-handoff configuration
  classes: (1) Policy definitions (regulatory constraints, internal risk
  thresholds, jurisdictional applicability rules); (2) Operator behavior
  rules (traversal-depth limits, materiality thresholds, temporal-boundary
  rules, similarity-threshold contracts); (3) Projection logic
  (role-to-intent-to-plan lookup tables, projection rules, entitlement
  matrices); (4) D_c thresholds per decision class; (5) λ_c per observation
  type (the §7.7 table, stored as Control Plane configuration so calibration
  updates propagate consistently); (6) Materialization policy per
  Context-Product class. Worked example: a regulatory exposure-limit change
  flows as a single Control Plane update — no graph state, engine code, or
  agent logic changes — the "instant-and-consistent adaptation" property.
- **Type signature:** none given (configuration classes enumerated; the
  specific values are domain calibrations, not SDK content).
- **Invariants:** All six classes versioned and auditable; a calibration
  update propagates consistently across every consumer of the configuration
  without rewriting graph state.
- **Dependencies:** INV-CH7-70/71; operator entries (§7.4), projection
  entries (§7.5), λ_c/D_c entries (§7.7). Governance D-42 (config surface
  enumeration). SDK note (CLAUDE.md §5, §10 — SDK-defined mapping): in the
  SDK, agent definitions, task definitions, prompt artifacts, and skill
  grants are additional Control Plane artifact classes — an SDK extension,
  not a whitepaper commitment.
- **Figure refs:** Fig-CH07-22 (policy-update sequence).
- **Open question:** none.

### INV-CH7-73 — Five architectural invariants, CI-tested at the plane boundary

- **Whitepaper section:** §7.8.4
- **Commitment (paraphrase):** Architectural invariants are "CI-tested, not
  conventional" — the bypass structurally does not exist. Five invariants
  are committed at the Control Plane / Data Plane boundary: (a)
  Single-writer for graph state — only the Assembly worker writes to
  enrichment-surface collections; read-path services receive no
  write-capable handles, enforced by dependency injection at boot and the
  type system at build time; (b) Projection stateless by invariant — the
  Projection engine holds no write locks and no in-process cache;
  materialization lives in a separately gated tier under explicit policy;
  (c) Lineage strict equality — `operators_invoked` must equal the set of
  operators actually resolved during assembly, validated at the stage-3a
  gate, else the product is not served; (d) TTL bounds — every product has
  `expires_at ∈ (now, now + MAX_TTL]` validated at stage-3b, CI-tested at
  both boundaries; (e) Tenant-scoped by kw-only argument — every `execute()`
  call on the assembly engine requires `tenant_id` as a keyword-only
  argument. All five are CI-tested in a reference implementation; conscious
  disablement is a governance event the audit trail captures.
- **Type signature:** partial — `operators_invoked` set equality;
  `expires_at ∈ (now, now + MAX_TTL]`; `execute(*, tenant_id=...)` kw-only.
- **Invariants:** This entry IS the invariant register for the plane
  boundary: single-writer, stateless projection, lineage strict equality,
  TTL bounds, tenant scoping — each enforced structurally (DI, type system,
  function signature, CI gate), never by convention.
- **Dependencies:** §7.3 single-writer graph mechanism; §7.5 projection
  purity; §7.6 validation gates (stage-3a/3b) — cross-links to slice A/B
  entries. Governance D-43 (invariants as first-class commitments).
- **Figure refs:** Fig-CH07-21 (invariant-enforcement boundary).
- **Open question (quoted, unnumbered):** "The invariant is enforced by
  dependency injection at boot time — the read-path services' DI containers
  simply do not receive write-capable handles… and the compilation of those
  services against write-capable interfaces is prevented by the type system
  at build time." — The whitepaper assumes a compiled/typed enforcement
  substrate; how the SDK realizes build-time prevention in the target
  language(s) depends on D-IMPL-01 (language target) and is a design
  question for Phase D.

### INV-CH7-74 — Data Plane determinism

- **Whitepaper section:** §7.8.5
- **Commitment (paraphrase):** Given the same graph state, the same Control
  Plane configuration, and the same temporal boundary, the Data Plane
  produces a bit-for-bit identical Context Product on every execution — the
  §7.4 operator-composition determinism claim restated at the plane level
  across assembly, operator execution, projection computation, and
  materialization. No sampling, no temperature-based variation in
  structural-reasoning stages, no hidden randomness in retrieval or
  extraction paths; any admitted randomness (e.g., embedding
  non-determinism under GPU parallelism) is isolated to boundaries the
  replay record can reproduce exactly (same model, same seed, same batch
  shape). This determinism is the architectural foundation that makes
  Decision Replay evidentiary rather than best-effort.
- **Type signature:** none given (determinism property over fixed inputs).
- **Invariants:** Bit-for-bit output identity under fixed (graph state,
  Control Plane config, temporal boundary); randomness isolation at
  reproducible boundaries.
- **Dependencies:** §7.4 composition-preservation (slice B);
  INV-CH7-81 (five-dimension record consumes this property).
  Governance D-44 (Data Plane determinism).
- **Figure refs:** none directly (referenced by Fig-CH07-27's
  bit-for-bit reassembly note).
- **Open question:** none.

### INV-CH7-75 — Closed loop: graph write-back through the Control Plane

- **Whitepaper section:** §7.9, §7.9.1
- **Commitment (paraphrase):** Closed-loop learning flows exclusively
  through the Control Plane as graph write-back — never as direct runtime
  modification of operators, projection, or policy, and never as model
  retraining. The three-stage pattern: (1) outcome observation becomes a
  typed OutcomeSignal carrying Provenance, `observed_at`, and its own λ_c
  (outcome signals are first-class context entities whose evidential weight
  decays); (2) the Control Plane interprets the signal and, where
  warranted, issues a versioned update (operator definition change, policy
  calibration, projection logic refinement, or half-life adjustment) — the
  interpretation step is where business judgment, statistical significance,
  and regulatory calibration constraints enter; (3) Data Plane propagation
  is downstream of the versioned update, with `projection_plan_id` +
  `contract_version` attribution in replay records so historical decisions
  remain re-traceable against the version in force when made. Graph
  write-back is logical, not destructive: outcome evidence appends typed
  outcome edges with their own lineage and temporal binding; prior state
  remains available for replay.
- **Type signature:** pseudocode given —
  `processOutcomeSignal(outcome: TypedOutcome, provenance: Provenance,
  half_life_lambda_c: Duration) -> ControlPlaneUpdate`, with
  `OutcomeSignal(outcome, provenance, observed_at, lambda_c)` and
  `versioned(update)` return.
- **Invariants:** No silent behavioral change: every change to agent-visible
  behavior is a versioned, auditable Control Plane event; write-back is
  append-only/logical; next-agent invocation reads refined graph state, not
  retrained weights.
- **Dependencies:** INV-CH7-70/71 (governance planes); §7.10 record
  (evidence persisted per decision); §7.3 append-only graph (slice A).
  Governance D-45 (write-back pseudocode), D-47 (loop-is-in-the-graph).
- **Figure refs:** Fig-CH07-23 (closed-loop graph write-back sequence;
  load-bearing — renders "the loop is in the graph" operationally).
- **Open question:** none.

### INV-CH7-76 — Three categories of learning signal

- **Whitepaper section:** §7.9.2
- **Commitment (paraphrase):** The Control Plane distinguishes three
  learning-signal categories, each with distinct interpretation logic and
  write-back target: (i) Outcome signals — direct ground truth (repaid /
  defaulted, fraud confirmed / cleared, SAR substantiated / closed), driving
  policy-calibration updates because they measure false-positive/negative
  rates; (ii) Context validity signals — λ_c feedback (was context within
  effective half-life at decision time), driving λ_c adjustments and
  freshness-budget recalibration; (iii) Audit/lineage signals — meta-signals
  separating context failure (incomplete/stale/inconsistent context →
  graph-level updates) from model failure (correct context, poor reasoning →
  model-level intervention outside Control Plane scope). Exactly one
  handler processes any given evidence event; each handler's graph-write
  target is structurally distinct (outcome edge with decision-class
  attribution; correction edge with pre/post-decision state; metadata
  refinement to P and Π dimensions). Every category writes to graph state,
  never to weights.
- **Type signature:** none given (routing semantics rendered in
  Fig-CH07-24's alt/else branches).
- **Invariants:** One-event-one-handler routing; graph-write targets
  structurally distinct per category; no gradient descent, no model
  parameter update, no retrained checkpoint in the CCF loop.
- **Dependencies:** INV-CH7-75 (write-back channel); λ_c entries (§7.7).
  Governance D-46 (three categories). Note: Fig-CH07-24 names the handlers
  Outcome / Correction / Metadata while §7.9.2 prose names the categories
  outcome / context-validity / audit-lineage — informational naming
  divergence within the whitepaper itself.
- **Figure refs:** Fig-CH07-24 (signal categorization; load-bearing —
  three-category routing as graph-level, not gradient-descent, operation).
- **Open question (quoted, unnumbered):** The categorization mechanism's
  naming differs between prose ("Outcome signals… Context validity
  signals… Audit/lineage signals") and figure caption ("Outcome Signal
  Handler… Correction Signal Handler… Metadata Signal Handler") — the SDK
  must pick one canonical taxonomy for the learning-signal type; synthesis
  should log this for design.

### INV-CH7-77 — Four refinement targets; "the loop is in the graph, not the model"

- **Whitepaper section:** §7.9.3
- **Commitment (paraphrase):** The three signal categories drive updates to
  exactly four Control-Plane-owned refinement targets: (1) Operator
  refinement (traversal depth, similarity thresholds, temporal boundaries);
  (2) Projection optimization (which signals are primary, subordinated,
  emphasized, compressed per principal view); (3) Policy calibration
  (detection thresholds, exposure limits, D_c class thresholds, entitlement
  boundaries); (4) Half-life adjustment (λ_c and freshness budgets per
  observation type). Canonical statement captured verbatim: "Agents appear
  to improve in production without retraining because the context they
  consume is improving." And: "The loop is in the graph, not the model."
  The model-retraining and prompt-refinement paradigms are explicitly
  orthogonal — the fabric does not prevent or replace them; the CCF's own
  loop operates at the graph and policy layer, so improvements compound
  across decision classes, are auditable at the Control Plane, and do not
  couple governance to any model's lifecycle.
- **Type signature:** none given (four target classes enumerated).
- **Invariants:** Refinement operates only on the four Control-Plane-owned
  targets; improvement lives in the context substrate, never in weights or
  prompts within the CCF loop.
- **Dependencies:** INV-CH7-75/76; operator parameters (§7.4), projection
  weighting (§7.5), policy/D_c thresholds (§7.7/§7.8.3), λ_c (§7.7).
  Governance D-47. External validation cited: Agentic Context Engineering
  (arXiv:2510.04618) — cited by the whitepaper as convergent evidence, with
  the CCF's distinction being the governed Control Plane surface.
- **Figure refs:** none directly (Fig-CH07-25 renders the full cycle —
  see INV-CH7-78).
- **Open question:** none.

### INV-CH7-78 — Learning as governance, not around it

- **Whitepaper section:** §7.9.4, §7.9.5
- **Commitment (paraphrase):** Learning strengthens governance rather than
  bypassing it: every closed-loop Control Plane update is versioned and
  auditable under the same discipline as any policy definition, and the
  improvement history is itself part of the audit trail. Three committed
  consequences: (1) consistency — an update propagates to every decision
  class consuming the configuration surface (Control Plane as single source
  of truth; asymmetry only by explicit commitment); (2) versioned
  auditability — "why was this threshold set at this value on the day of
  the decision" is answerable with update version, outcome-signal analysis,
  and approval workflow; (3) controlled evolution — approval workflows,
  staged propagation, and rollback apply to closed-loop updates exactly as
  to initial definitions. §7.9.5's fraud-detection worked example
  instantiates the full cycle (replay reconstruction → three contributing
  factors → three versioned Control Plane updates: λ_c 60→20 min,
  projection signal elevation, TTL 30→5 min), and notes the mechanism is
  invariant across decision classes — only the outcome signal's own λ_c and
  the statistical-significance threshold differ.
- **Type signature:** none given.
- **Invariants:** Closed-loop updates run through the same governance regime
  (versioning, approval, staged propagation, rollback) as initial
  configuration; no separate learning regime exists.
- **Dependencies:** INV-CH7-71 (audit plane), INV-CH7-75..77; §7.10 replay
  (reconstruction step of the cycle). Governance D-48
  (learning-as-governance).
- **Figure refs:** Fig-CH07-25 (closed-loop feedback cycle; supplementary —
  mechanism fully specified in prose per the whitepaper's own note).
- **Open question:** none.

### INV-CH7-79 — Decision Replay: forensic reconstruction as first-class commitment

- **Whitepaper section:** §7.10 (intro)
- **Commitment (paraphrase):** Every decision the fabric participates in is
  forensically reconstructible, years after the fact, against the exact
  state of the fabric at the moment of the decision — enforced at the
  moment of assembly, at the boundary of every Context Product, and at the
  Control Plane / Data Plane interface, not bolted on as post-hoc
  observability. §7.10 commits: the five-dimension record, environment
  replay (distinct from model trace), Anthropic Citations as the
  passage-level lineage component primitive, the Evidence Chain
  (Fig-CH07-28), three-tier compression with severity exemption, the AML
  SAR triage worked example, and three-audiences/three-renderings.
- **Type signature:** none given (chapter-level commitment; mechanism in
  the entries below).
- **Invariants:** Replay-readiness enforced at write time (assembly), not
  retrofitted.
- **Dependencies:** INV-CH7-74 (Data Plane determinism is the foundation);
  INV-CH7-71 (audit plane); lineage strict equality (INV-CH7-73(c)).
- **Figure refs:** Fig-CH07-26, Fig-CH07-27, Fig-CH07-28 (detailed in the
  entries below).
- **Open question:** none.

### INV-CH7-80 — The five-dimension replay record (enumeration)

- **Whitepaper section:** §7.10.1
- **Commitment (paraphrase):** A decision is reconstructible only if five
  dimensions of state at decision time t can each be reproduced exactly —
  "drop any one and a class of audit question becomes unanswerable." The
  five dimensions, by name: (1) **Context Fabric Snapshot**; (2) **Policy
  Bindings Snapshot**; (3) **Model Version Record**; (4) **Perspective
  Conditioning**; (5) **Content Generation Path**. The dimensions are
  orthogonal (each answers a different audit-question class) and
  collectively exhaustive for decision reconstruction. All five are
  captured, versioned, and retained together, indexed by the decision's
  temporal boundary and decision class, and available through the replay
  interface at any future audit time. Retention is subject to three-tier
  compression (INV-CH7-88), "but the five-dimension structure itself is
  inviolate." Patent Claim 13 covers the record as reduced-to-practice.
- **Type signature:** none given (record structure enumerated; field-level
  contracts per dimension in INV-CH7-81..85).
- **Invariants:** Five-dimension structure inviolate; captured/versioned/
  retained together; indexed by temporal boundary + decision class.
- **Dependencies:** INV-CH7-74 (determinism), INV-CH7-71 (audit plane).
  Governance D-51 (five-dimension record). SDK-defined extensions
  (CLAUDE.md, not whitepaper commitments): HITL actions and workflow
  traces extend dimensions (2) and (4) per CLAUDE.md §8.2/§8.1; agent
  version, configuration, and skill-set in force extend dimension (4) per
  CLAUDE.md §6.2.
- **Figure refs:** Fig-CH07-26 (five input nodes → single indexed
  replay-record node → five audit-question classes; canonical visual for
  §7.10); Fig-CH07-27 (examiner re-trace sequence: five parallel reads
  reconciled into deterministic reproduction).
- **Open question (quoted, unnumbered):** "made available through the
  replay interface at any future time the audit obligation requires" —
  snapshot storage strategy that makes replay tractable at year-scale is
  under-specified; interacts with D-IMPL-06 (snapshot management) and
  D-IMPL-26 (artifact addressing/versioning).

### INV-CH7-81 — Dimension 1: Context Fabric Snapshot

- **Whitepaper section:** §7.10.1 item (1)
- **Commitment (paraphrase):** The complete `G(E, R, T, P, Π, L)` at
  decision time — every entity the decision touched, every relation, the
  temporal binding active at t, the policy regime in force, the projection
  applied, and the lineage for every assertion. Answers "what did the agent
  know?" — the first examiner re-tracing question; dropping it breaks
  SR 11-7 model validation.
- **Type signature:** `G(E, R, T, P, Π, L)` substate at t.
- **Invariants:** Completeness over the decision's touched substate;
  snapshot immutable once written.
- **Dependencies:** Context Graph six-tuple (§7.3, slice A entries);
  INV-CH7-74 (deterministic re-read).
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Context Graph historical read).
- **Open question (quoted, unnumbered):** Full-fidelity graph substate per
  decision at "millions of decisions each day" scale — the whitepaper
  defers cost to compression (§7.10.5) but leaves the snapshot substrate
  open; interacts with D-IMPL-06.

### INV-CH7-82 — Dimension 2: Policy Bindings Snapshot

- **Whitepaper section:** §7.10.1 item (2)
- **Commitment (paraphrase):** The version identifier and serialized
  parameters of all active policies at decision time: the regulatory policy
  bundle governing the decision, internal risk-threshold policies above
  regulatory floors, operator-behavior policies in force, and the
  projection and entitlement policies that shaped the Context Product.
  Answers "what rules applied?" — establishes governance compliance;
  dropping it breaks FinCEN examiner review.
- **Type signature:** version identifier + serialized parameters (shape not
  further formalized).
- **Invariants:** Snapshot binds the exact policy versions in force at t.
- **Dependencies:** INV-CH7-71/72 (Control Plane versioning is the source).
  SDK-defined extension (CLAUDE.md §8.2, not a whitepaper commitment):
  HITL actions (approver identity, time, Context Product seen, annotations)
  extend this dimension.
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Policy Store historical read).
- **Open question:** none.

### INV-CH7-83 — Dimension 3: Model Version Record

- **Whitepaper section:** §7.10.1 item (3)
- **Commitment (paraphrase):** Identifiers of every model the decision
  pipeline invoked: detection models producing risk signals, classification
  models producing typology matches, embedding models producing similarity
  scores, and the LLM model and version that reasoned over the assembled
  Context Product. Answers "what software reasoned?" — separates model
  failure from context failure; indispensable for SR 11-7 model-validation
  review; "none"/"N/A" for pure-algorithmic Mode 1 (§7.10.4).
- **Type signature:** model identifiers per pipeline stage; Mode 2 record
  refines to `model_version_string`
  (vendor + family + version + revision pin) per §7.10.4.
- **Invariants:** Every invoked model captured; version pinning sufficient
  for re-invocation at replay.
- **Dependencies:** INV-CH7-74 (randomness isolation: same model, same
  seed, same batch shape); INV-CH7-87 (per-mode record contents).
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Model Registry read).
- **Open question:** none.

### INV-CH7-84 — Dimension 4: Perspective Conditioning

- **Whitepaper section:** §7.10.1 item (4)
- **Commitment (paraphrase):** The agent identity, the role definition the
  agent executed under, the tools the agent had available, and the
  delegation chain that led to the agent being invoked for this decision.
  Answers "for whom, with what authority?" — establishes that the right
  principal acted under the right delegation.
- **Type signature:** none given (agent identity, role, tool inventory,
  delegation chain).
- **Invariants:** Delegation chain complete from originating principal to
  acting agent.
- **Dependencies:** Projection/perspective conditioning (§7.5, slice B).
  SDK-defined extensions (not whitepaper commitments): workflow execution
  traces (calling agent chain) extend this dimension per CLAUDE.md §8.1;
  agent version and skill-set in force extend it per CLAUDE.md §6.2.
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Projection stage applies
  Dim 4).
- **Open question:** none.

### INV-CH7-85 — Dimension 5: Content Generation Path

- **Whitepaper section:** §7.10.1 item (5)
- **Commitment (paraphrase):** The input-data identifiers for every source
  that contributed, the reasoning trace the agent produced (for
  deterministic algorithmic decisions the trace is the operator/projection
  trace, not an LLM rationale), and the structured output produced.
  Answers "how did it get from input to output?" — source-to-conclusion
  traceability; dropping it breaks BCBS 239 data-lineage requirements.
- **Type signature:** none given (input identifiers + reasoning trace +
  structured output).
- **Invariants:** Trace covers input→output end to end; algorithmic-mode
  trace is the operator/projection trace by definition.
- **Dependencies:** Lineage strict equality (INV-CH7-73(c)); passage-level
  lineage (INV-CH7-86). SDK-defined extension (CLAUDE.md §8.1): workflow
  step sequences extend this dimension.
- **Figure refs:** Fig-CH07-26; Fig-CH07-27.
- **Open question:** none.

### INV-CH7-86 — Environment replay, not model trace

- **Whitepaper section:** §7.10.2
- **Commitment (paraphrase):** "LLM observability captures the model's
  trace; CCF reconstructs the decision environment." The model trace
  (LangSmith / W&B Weave: prompt, intermediate reasoning, token outputs,
  tool invocations, latency) is silent on the fabric's side — the exact
  Context Product consumed, entitlement boundaries, temporal binding,
  policy bindings, λ_c configuration, projection applied. Given the
  environment (CCF) plus the model's own trace (captured by a separate
  tool), reconstruction is deterministic, bit-for-bit, on the Data Plane
  determinism foundation. The two layers are complementary; the model
  trace is necessary but not sufficient; the environment replay is the
  sufficient condition the CCF contributes. Named regulatory obligations
  satisfied by the composition: SR 11-7 post-hoc independent validation,
  OCC model-risk-management reconstruction, FinCEN examiner re-tracing.
- **Type signature:** none given.
- **Invariants:** Environment reconstruction deterministic (bit-for-bit)
  from the five-dimension record; model trace explicitly out of CCF scope.
- **Dependencies:** INV-CH7-74, INV-CH7-80. Governance D-52 (environment
  replay vs model trace).
- **Figure refs:** Fig-CH07-27 (bit-for-bit reassembly Note-over).
- **Open question:** none.

### INV-CH7-87 — Passage-level Lineage via the Anthropic Citations API

- **Whitepaper section:** §7.10.3
- **Commitment (paraphrase):** The L dimension must extend to the passage
  level for unstructured content: an unstructured claim must be traceable
  to the specific passage (document, passage, and where applicable
  page/bounding-box), not the document as a whole. The CCF builds on the
  Anthropic Citations API (GA January 2025) as "the canonical component
  primitive on which CCF's passage-level Lineage L for unstructured content
  builds": passage-level references produced at inference time as part of
  generation are persisted as Lineage entries attached to each claim in the
  Context Product. The Evidence Chain — Context Product claim →
  passage-level Lineage → Citations source reference → specific
  passage/page/bounding-box in the WORM/durable source — is the forward
  chain; the audit direction re-traces it in reverse. Explicitly
  decoupled: "Anthropic Citations is a component primitive the CCF uses,
  not a feature the CCF is" — the architectural commitment is that
  passage-level Lineage is a first-class L field populated by whatever
  component primitive the deployment selects and persisted in the replay
  record.
- **Type signature:** citation reference = (source document, passage,
  page/bounding-box where applicable).
- **Invariants:** Every unstructured-derived claim carries passage-level
  Lineage; Evidence Chain reconstructible at audit time; primitive is
  pluggable (not Anthropic-coupled).
- **Dependencies:** L dimension (§7.3); INV-CH7-85 (Dim 5); XC-05
  unstructured-as-first-class commitment (§7.3/§7.4, slices A/B).
  Governance D-53 (Citations API as component primitive). Interacts with
  D-IMPL-09 (LLM access for semantic stages / Citations API).
- **Figure refs:** Fig-CH07-28 (Evidence Chain; load-bearing — the XC-05
  commitment carried through to the audit surface).
- **Open question:** none.

### INV-CH7-88 — Replay across assembly modes (Modes 1/2/3 record contents)

- **Whitepaper section:** §7.10.4
- **Commitment (paraphrase):** The five-dimension record is the canonical
  Mode 1 artifact and the baseline Modes 2 and 3 extend without modifying.
  Mode 1: the five dimensions exactly, model version "none"/"N/A", content
  path = operator/projection trace. Mode 2 adds four LLM-rendering
  primitives: `model_version_string`, `temperature_float`,
  `full_prompt_text_or_hash` (inline or content-addressed hash with body in
  the WORM tier), `llm_output_hash`; the algorithmic substrate hash anchors
  the artifact-of-record. Mode 3 adds three orchestration primitives:
  `orchestration_plan_id` (content-addressed), `per_agent_version_manifest`
  (agent identity, framework version, prompt version, tool inventory), and
  `per_agent_contribution_boundary_markers`; per-agent contributions are
  themselves Mode 1/2/3 records (recursive composition). Compression and
  severity exemption operate on every per-mode record without distinction —
  replay is mode-invariant on one record format.
- **Type signature:** the Mode 2/3 field names above are given verbatim in
  the whitepaper.
- **Invariants:** Modes extend, never modify, the five-dimension baseline;
  recursive composition of per-agent records; mode-invariant replay
  infrastructure.
- **Dependencies:** §7.6 assembly modes and D-15/D-16 (slice B);
  INV-CH7-80, INV-CH7-89.
- **Figure refs:** none specific to this H3.
- **Open question:** none.

### INV-CH7-89 — Three-tier compression with severity exemption

- **Whitepaper section:** §7.10.5
- **Commitment (paraphrase):** Retention cost over year/decade horizons is
  bounded by three tiers: Full fidelity (all fields of all five dimensions;
  configurable per-decision-class window, typically weeks–months);
  Compressed (essential metrics only — threat level, entity counts/ids,
  composite D_c, coverage percentage, summary statistics — with the graph
  substate reduced to a deterministic hash re-hydratable from the cold
  source archive); Tombstoned (metadata only — timestamp, threat level,
  cycle id, decision class; applied per regulatory retention minima). The
  severity exemption: instances at or above a configurable,
  decision-class-specific severity threshold are never compressed or
  tombstoned — "Significant decisions retain full fidelity permanently."
  Every compressed/tombstoned record carries a structural
  `retention-reason` field. In a reference implementation the compression
  is an architectural invariant: deterministic algorithm, CI-tested
  severity exemption, structural retention-reason — bypassing is not
  silent on either the cost or the audit side. Patent Claim 14 covers the
  primitive.
- **Type signature:** partial — tier field lists and `retention-reason`
  field named.
- **Invariants:** Severity exemption never compressible/tombstonable;
  deterministic compression; retention-reason structural; five-dimension
  structure inviolate under compression (INV-CH7-80).
- **Dependencies:** INV-CH7-80; D_c (§7.7). Governance D-54 (implied by
  sequence D-51..D-56; three-tier compression). Severity thresholds and
  retention windows are Control Plane configuration (domain values, not
  SDK content).
- **Figure refs:** none.
- **Open question (quoted, unnumbered):** "The graph substate itself is
  reduced to a deterministic hash of the five-dimension record, so that
  the exact substate can be re-hydrated if ever needed from a
  source-record archive" — the cold-archive substrate and re-hydration
  contract are unspecified; interacts with D-IMPL-06 and D-IMPL-27
  (substrate split).

### INV-CH7-90 — AML SAR triage worked example (replay end-to-end)

- **Whitepaper section:** §7.10.6
- **Commitment (paraphrase):** The canonical worked example composing the
  five-dimension record, Evidence Chain, and compression policy: an
  investigator's SAR filing decision captures all five dimensions
  (including passage-level Lineage for Bloomberg IB chat, wire narrative,
  and adverse-media passages via Anthropic Citations); years later an OCC
  examiner re-traces the Evidence Chain of Fig-CH07-28 in reverse for
  every narrative claim. The SAR filing is severity-exempt (Full fidelity
  permanently); routine non-filing typology-match cycles take the
  compressed/tombstoned tiers. Resolves the §7.6 D-30 anticipation via
  D-55; anchor example for the XC-05 load-bearing commitment.
- **Type signature:** none (worked example).
- **Invariants:** Defensibility is exactly coextensive with every claim
  having a traceable Evidence Chain.
- **Dependencies:** INV-CH7-80..89; §7.6 D-30 (slice B); Chapter 8 §8.9
  carries the regulatory payoff. Governance D-55.
- **Figure refs:** Fig-CH07-27 (re-trace sequence), Fig-CH07-28 (Evidence
  Chain).
- **Open question:** none.

### INV-CH7-91 — Three audiences, three renderings

- **Whitepaper section:** §7.10.7
- **Commitment (paraphrase):** The same underlying replay record serves
  three audiences through three renderings that are "three Projections of
  the same record," not three separate records: auditors/examiners get the
  Full-fidelity five-dimension trace with passage-level Evidence Chain;
  risk-and-compliance get a policy-adherence rendering emphasizing the
  Policy Bindings Snapshot, D_c/severity summaries, and Perspective
  Conditioning; management gets an executive pattern-detection summary
  aggregated over the record corpus. Mechanism: the recursive application
  of the §7.5 Projection primitive Π at the replay layer — audit-time
  consumption inherits the same principal-conditioning, entitlement, and
  role-shaped semantics as runtime consumption. "One primitive,
  recursively applied, serves every consumption surface."
- **Type signature:** none given (Π applied to the replay record).
- **Invariants:** One record, three projections — never three records;
  replay rendering reuses the Projection primitive, no separate mechanism.
- **Dependencies:** Projection Π (§7.5, slice B); INV-CH7-80.
  Governance D-56 (three audiences / three renderings).
- **Figure refs:** Fig-CH07-27 (alt/else audience branches).
- **Open question:** none.

---

## Open Questions (unnumbered)

Quoted, unnumbered per Pattern 2 discipline — `D-IMPL-NN` numbers are
assigned only by the synthesis task (starting at D-IMPL-30).

1. **Build-time invariant enforcement substrate (§7.8.4).** "the
   compilation of those services against write-capable interfaces is
   prevented by the type system at build time" — how the SDK realizes
   compile-time single-writer prevention depends on D-IMPL-01 (language
   target); in Python, structural typing + DI can approximate but not
   equal build-time prevention.
2. **Learning-signal taxonomy naming (§7.9.2 vs Fig-CH07-24).** Prose
   categories (outcome / context-validity / audit-lineage) vs figure
   handler names (Outcome / Correction / Metadata) diverge; the SDK's
   typed learning-signal enum must pick one canonical taxonomy.
3. **Control Plane interpretation step (§7.9.1).** "The interpretation
   step is where business judgment, statistical significance, and
   regulatory calibration constraints enter the loop" — the whitepaper
   does not specify whether interpretation is automated, human-gated, or
   configurable; interacts with the SDK's HITL primitives (CLAUDE.md
   §8.2, SDK-defined) and D-IMPL-29-adjacent governance depth.
4. **Snapshot tractability at year-scale (§7.10.1, §7.10.5).** Replay
   "at any future time the audit obligation requires" plus per-decision
   graph substate at millions-of-decisions/day scale — snapshot storage,
   hash-based re-hydration, and the cold-archive contract are
   unspecified; interacts with D-IMPL-06 (snapshot management),
   D-IMPL-26 (artifact addressing), and D-IMPL-27 (substrate split).
5. **Model-trace composition seam (§7.10.2).** The whitepaper assumes a
   mature deployment composes CCF environment replay with an external
   model-trace tool (LangSmith/Weave) but specifies no interface for the
   composition; the SDK's replay-hook seam (CLAUDE.md §7.3 seam 4,
   SDK-defined) is the natural attachment point — a design question for
   Phase D.
6. **Citations-primitive pluggability contract (§7.10.3).** "populated by
   whatever component primitive the deployment has selected" — the
   Protocol shape for a pluggable passage-citation provider (and its
   relationship to D-IMPL-09 LLM access) is unspecified.

