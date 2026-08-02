# examples/01-agent-basics — one declared agent, six axes, each one observable

## What this demonstrates

The **archetype vs agent** separation — an archetype is a functional
template the SDK ships as code; an agent is a declared, versioned Control
Plane artifact the Agent Factory produces from one (CLAUDE.md §6.1 — SDK
extension) — and all six channel-1 **specialization axes / skilling** axes
— channel 1 fixes who the agent is (six axes: archetype, context contract,
perspective, policy regime, half-life/debt profile, instruction bindings);
channel 2 — skilling — governs what it can currently do (CLAUDE.md §6.2 —
SDK extension). The point is that each axis is *exercised*, not merely
declared: for every axis there is an asserted output the run would lose if
that axis were removed or rebound (see the per-axis table under "What
would fail").

The agent (`response-time-analytics`, a field-service dispatch analyst)
consumes a real, gated **Context Product** — a typed, validated,
replay-ready unit of decision context the fabric derives and serves — a
contract, not a stored record (whitepaper §6.3 (specification), §7.6
(delivery)) — and its identity, version, archetype composition and
conditioning land in the five-dimension **Decision Replay record** — the
record (fabric snapshot, policy bindings, model version, perspective
conditioning, generation path) that lets a decision be reproduced exactly
(whitepaper §7.10 ("The Five-Dimension Replay Record")).

## Run it

```sh
make example-01
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/01-agent-basics/run.py
```

The driver is an asserted program: exit code 0 means every axis witness
and every fabric invariant held; any failure exits nonzero, and CI treats
nonzero as red.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-01`, review the assertion output, then
> deliberately edit the `expected:` block in `artifacts/controlplane.yaml`
> to match what you reviewed — regeneration is a reviewed event, landed in
> the same commit as the enrichment, with the commit body summarizing what
> changed in the output and why. No `make regen-*` targets exist, and none
> will be added. (The reviewed debt outcome lives in
> `artifacts/halflife.yaml`, key `debt_evaluation.expected_signal`.)

## The story

A dispatch analyst's agent needs decision context on an urgent
refrigeration work order. The **Control Plane / Data Plane** split — the
Control Plane declares what the fabric may do (versioned config, policy,
artifacts — also the audit plane); the Data Plane executes within those
constraints (whitepaper §7.8) — carries everything: the fabric bundle in
`artifacts/controlplane.yaml`, the agent definition in
`artifacts/agent.yaml`, the prompt in `artifacts/prompt.yaml`.

1. **A small fabric serves a product.** Events in `artifacts/events.yaml`
   build a technician, two work orders and a *restricted* defence-sector
   site; the four-category operator chain ranks out the routine work
   order (similarity), substitutes away the restricted site and its
   `located_at` edge (policy), and the gated product is asserted against
   the `expected:` block — including, new in this upgrade, the
   perspective role and the by-name exclusion:

   ```yaml
   role: dispatch-analyst
   excluded_entity_classes:
     - site
   ```

2. **The Agent Factory constructs the agent.** `run.py` never
   instantiates `Agent` directly — the factory resolves
   `artifacts/agent.yaml` and every referenced artifact through Control
   Plane resolution at pinned versions, per the **No-Hardcoding Rule** —
   no prompts, agent definitions, thresholds, or routing values in code —
   code is interpreters and factories; everything specific lives in
   versioned artifacts, CI-lint enforced (CLAUDE.md §6.4 — SDK
   extension).
3. **Each axis leaves a mark on the output.** Axis 1's archetype
   composition is printed and lands in replay dimension 4. Axis 2's
   contract admission is asserted against the product class the contract
   names. Axis 3's Π role is the served payload's `role` field —
   **Projection (Π)** being the role-conditioned transformation that
   turns graph state into the view a given consumer is entitled to see
   (whitepaper §7.5). Axis 4's regime keeps the `site` class out of the
   view by name. Axis 6's prompt artifact resolves with exactly its
   declared parameters.
4. **Axis 5 gates, visibly.** New in this upgrade: the **Context
   Half-life (λ_c)** — a per-observation-type decay rate declaring how
   fast context goes stale — a Control Plane value, never code
   (whitepaper §7.7) — table in `artifacts/halflife.yaml` scores an aged
   work-order-status observation (37 minutes old against a one-hour
   half-life, inflated by the profile's 1.2 risk sensitivity), and the
   resulting **Context Debt (D_c)** — the quantified shortfall when
   freshness or completeness drops below threshold; elevated debt gates
   Forced-LLM and Fail-Closed behavior (whitepaper §7.7 ("`D_c`
   Formulas")) — crosses the `forced_llm_threshold: "0.30"` the agent's
   axis-5 profile declares in `agent.yaml`. The run prints the computed
   D_c and asserts the routing signal equals the reviewed
   `expected_signal: forced_llm` in `halflife.yaml`.
5. **Everything lands in replay.** The record — agent definition hash,
   versioned URI, archetype composition, conditioning role, delegation
   chain — round-trips through the **ArtifactStore** — the Protocol-based
   persistence surface for CCF artifacts (snapshots, products at rest,
   replay records, Control Plane bundles), with file-backed and
   MCP-backed reference implementations (CLAUDE.md §7.4 — SDK extension).

The demo got richer — a whole new gating behavior, two new expected
fields, a new artifact — and `run.py` changed only where new artifact
fields needed interpreting: artifact-dict reads and assertions, no domain
value, threshold or prompt text in code.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/agent.yaml` | The agent definition: all six channel-1 axes, plus the referenced policy-regime and debt-profile declarations | `[ADAPT]`: agent name, tenant, role, region, URIs, threshold values, parameter names. `[MECHANISM]`: the six axis keys (`archetypes`, `context_contract`, `perspective`, `policy_regime`, `halflife_debt_profile`, `instruction_bindings`) and the framing keys (`referenced_artifacts`, `agent_definition`, `ref`, `semver`, `class_id`, `declaration`) |
| `artifacts/controlplane.yaml` | The fabric's bundle: policy, operator parameters, product class, perspective, decision instants, `expected:` block | `[ADAPT]`: key names, bundle values, parameter values, schema name, expected values. `[MECHANISM]`: `keys`, `policy_bundle`, `operator_parameters`, `product_class`, `perspective`, `decision`, `expected` and their sub-keys |
| `artifacts/ontology.yaml` | Entity classes, identity keys, relationship rules, classification and similarity-corpus attributes | `[ADAPT]`: class names, match keys, attribute names, relationship types. `[MECHANISM]`: `entity_rules`, `match_key`, `identity_keys`, `relationship_rules`, `classification_attribute_by_class`, `similarity_corpus_attribute_by_class` |
| `artifacts/events.yaml` | The L1 signal stream, in the source systems' vocabulary | `[ADAPT]`: everything under `payload:`, source system ids. `[MECHANISM]`: `envelope_id`, `source_system_id`, `ingestion_timestamp`, `observed_time`, `payload` |
| `artifacts/halflife.yaml` | λ_c calibrations, the observations to score, the C/S factors and the reviewed `expected_signal` | `[ADAPT]`: observation-type names, calibrations, factor values, `expected_signal`. `[MECHANISM]`: `half_life_seconds`, `decay_driver`, `supersession_event`, `observations`, `completeness`, `semantic_consistency`, `expected_signal` |
| `artifacts/prompt.yaml` | The axis-6 prompt artifact: template text and declared parameters | `[ADAPT]`: name, tenant, template text, parameter names. `[MECHANISM]`: `prompt_artifact`, `declared_parameters`, `template` |
| `artifacts/analysis_output.yaml` | The scripted analyst's model identifier and canned output records | `[ADAPT]`: model identifier, output fields and values. `[MECHANISM]`: `model_version`, `outputs` |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §7.4 / §7.5 — operator chain and projection Π behind the
  consumed product
- whitepaper §7.6 — the Context Product Contract the agent's axis-2
  contract admits
- whitepaper §7.7 — half-life decay, the D_c formula, and CAR routing
  (the Forced-LLM band)
- whitepaper §7.10 — replay dimension 4: agent identity, version,
  archetype composition, conditioning
- CLAUDE.md §6.1 — archetype/agent separation (SDK extension)
- CLAUDE.md §6.2 — the six channel-1 specialization axes (SDK extension)
- CLAUDE.md §6.4 — the Agent & Task Factory and the No-Hardcoding Rule
  (SDK extension)

## What to change first

`artifacts/agent.yaml` is the axis surface. To rebind the agent for a new
domain, edit these exact keys and expect these observable changes:

1. `agent_definition.archetypes` (axis 1) — the printed composition and
   replay dimension 4 change with the list.
2. `agent_definition.context_contract.consumes[0].product_class` (axis 2)
   — must match `product_class.schema_name` in `controlplane.yaml`, or
   the contract-admission assertions fail.
3. `agent_definition.perspective.role` (axis 3) — must match the fabric
   `perspective.role` and `expected.role` in `controlplane.yaml`; the
   served payload's `role` field follows it.
4. `referenced_artifacts.policy_regime.declaration` (axis 4) — your
   regime's classifications; update `expected.excluded_entity_classes`
   in `controlplane.yaml` to whatever your regime excludes.
5. `referenced_artifacts.halflife_debt_profile.declaration` (axis 5) —
   your thresholds; then recalibrate `artifacts/halflife.yaml` (table
   rows, observations, factors) and re-review `expected_signal`.
6. `agent_definition.instruction_bindings` (axis 6) — point at your
   prompt artifact in `artifacts/prompt.yaml`; parameters must match its
   `declared_parameters`.

Then rename the domain vocabulary in `ontology.yaml`/`events.yaml`, run
`make example-01`, review the assertion output, and deliberately update
the `expected:` block — that reviewed edit is the workflow, not a bug.

## What would fail

One concrete row per specialization axis, plus the fabric invariants the
example inherits:

| Invariant | What would fail here |
| --- | --- |
| axis 1 — archetype binding | remove or reorder `archetypes:` in `agent.yaml` and the composition assertions against replay dimension 4 and `agent.components` fail — identity derives from the definition, never from code |
| axis 2 — context contract | rename `context_contract.consumes[0].product_class` and the contract-admission assertions fail: the agent would be consuming a product class it never declared |
| axis 3 — perspective | rebind `perspective.role` and the served payload's `role` field no longer equals the definition's Π role (or `expected.role`) — the view is conditioned for someone else |
| axis 4 — policy regime | admit `restricted` into the regime's classifications and the defence-sector `site` survives into the served view, tripping the by-name `excluded_entity_classes` assertion |
| axis 5 — half-life/debt profile | raise `forced_llm_threshold` above the computed D_c (≈0.356) and the routing signal drops to `ok`, contradicting the reviewed `expected_signal: forced_llm` in `halflife.yaml` — the gate visibly stops gating |
| axis 6 — instruction bindings | change the prompt's `declared_parameters` without changing the binding's `parameters` (or vice versa) and the parameter-equality assertion fails; an inline prompt string in `run.py` instead would trip the No-Hardcoding lint |
| factory-only construction | instantiating `Agent` directly in code bypasses Control Plane resolution — nothing in this directory does, and the lint keeps it that way |
| replay dimension 4 | the definition hash, versioned URI, archetype composition and grant-set hash must survive the ArtifactStore round trip byte-identically |
