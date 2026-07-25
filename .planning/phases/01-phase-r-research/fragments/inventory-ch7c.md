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
