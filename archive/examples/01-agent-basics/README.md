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
declared: for every axis there is a checked output the run would lose if
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

`run.py` is the **call spine** and nothing else — it asserts nothing and
prints nothing. Exit code 0 means the spine executed. Its correctness
guarantee lives in `tests/examples/test_agent_basics_output.py`, where a
test runner can fail a build (D-09); that module's docstring maps every
relocated assertion to the pre-rewrite line it came from, and says which
assertions are independent expectations and which are propagation checks.

Check the assertions:

```sh
PYTHONPATH=src:runtime python -m pytest tests/examples/test_agent_basics_output.py
```

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run the test module, review the failures, then deliberately
> edit `artifacts/expected.yaml` to match what you reviewed —
> regeneration is a reviewed event, landed in the same commit as the
> enrichment, with the commit body summarizing what changed and why. No
> `make regen-*` targets exist, and none will be added. (The reviewed debt
> outcome lives in `artifacts/debt-evaluation.yaml`, key
> `declaration.expected_signal`.)

## The story

A dispatch analyst's agent needs decision context on an urgent
refrigeration work order. The **Control Plane / Data Plane** split — the
Control Plane declares what the fabric may do (versioned config, policy,
artifacts — also the audit plane); the Data Plane executes within those
constraints (whitepaper §7.8) — carries everything, and
`artifacts/manifest.yaml` is the one document naming what is in force.

1. **A small fabric serves a product.** Events in `artifacts/events.yaml`
   build a technician, two work orders and a *restricted* defence-sector
   site; the four-category operator chain ranks out the routine work
   order (similarity), substitutes away the restricted site and its
   `located_at` edge (policy), and the gated product is checked against
   `artifacts/expected.yaml` — including the perspective role and the
   by-name exclusion:

   ```yaml
   role: dispatch-analyst
   excluded_entity_classes:
     - site
   ```

2. **The Agent Factory constructs the agent.** `run.py` never
   instantiates `Agent` directly — the factory resolves
   `artifacts/agent-definition.yaml` and every referenced artifact through
   Control Plane resolution at pinned versions, per the **No-Hardcoding
   Rule** — no prompts, agent definitions, thresholds, or routing values
   in code — code is interpreters and factories; everything specific lives
   in versioned artifacts, CI-lint enforced (CLAUDE.md §6.4 — SDK
   extension).
3. **Each axis leaves a mark on the output.** Axis 1's archetype
   composition lands in replay dimension 4. Axis 2's contract admission is
   checked against the product class the contract names. Axis 3's Π role
   is the served payload's `role` field — **Projection (Π)** being the
   role-conditioned transformation that turns graph state into the view a
   given consumer is entitled to see (whitepaper §7.5). Axis 4's regime
   keeps the `site` class out of the view by name. Axis 6's prompt
   artifact resolves with exactly its declared parameters.
4. **Axis 5 gates, visibly.** The **Context Half-life (λ_c)** — a
   per-observation-type decay rate declaring how fast context goes stale —
   a Control Plane value, never code (whitepaper §7.7) — table in
   `artifacts/half-life-table.yaml` scores an aged work-order-status
   observation (37 minutes old against a one-hour half-life, inflated by
   the profile's 1.2 risk sensitivity), and the resulting **Context Debt
   (D_c)** — the quantified shortfall when freshness or completeness drops
   below threshold; elevated debt gates Forced-LLM and Fail-Closed
   behavior (whitepaper §7.7 ("`D_c` Formulas")) — crosses the
   `forced_llm_threshold: "0.30"` the agent's own axis-5 profile declares
   in `artifacts/agent-debt-profile.yaml`. The test module checks the
   routing signal equals the reviewed `expected_signal: forced_llm`.
5. **Everything lands in replay.** The record — agent definition hash,
   versioned URI, archetype composition, conditioning role, delegation
   chain — round-trips through the **ArtifactStore** — the Protocol-based
   persistence surface for CCF artifacts (snapshots, products at rest,
   replay records, Control Plane bundles), with file-backed and
   MCP-backed reference implementations (CLAUDE.md §7.4 — SDK extension).

## Two registration paths, and why

Most artifacts here are named by `artifacts/manifest.yaml` and registered
by the single `load_and_boot` call that boots the fabric. Two are not:
`agent-definition.yaml` and `prompt-artifact.yaml` carry D-IMPL-28
two-field versioning and register through `register_versioned`, which
holds the author's `artifact_version` claim against content identity — the
D-05 bump check. `load_and_boot` registers through `register_typed`, which
does not run that check, so routing those two through the manifest would
drop it silently. `artifacts/agent-registration.yaml` names the Control
Plane keys they register under.

## Artifact-by-artifact

Every document is exactly one artifact class and carries a
`# yaml-language-server: $schema=` header naming the schema that validates
it (`make schema-headers DIR=examples/01-agent-basics/artifacts`).

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/manifest.yaml` | The one document naming what this deployment puts in force: tenant, backend kind, and every artifact with its key, class and `role` | `[ADAPT]`: `tenant_id`, keys, paths, deployment class ids. `[MECHANISM]`: `backend`, `resolution_spec_key`, `policy_bundle_key`, `artifacts`, `path`, `key`, `class_id`, `role` |
| `artifacts/agent-definition.yaml` | The agent definition: all six channel-1 axes, and nothing else | `[ADAPT]`: agent name, tenant, role, region, URIs, parameter names. `[MECHANISM]`: the six axis keys (`archetypes`, `context_contract`, `perspective`, `policy_regime`, `halflife_debt_profile`, `instruction_bindings`), `schema_version`, `artifact_version`, `ref` |
| `artifacts/agent-policy-regime.yaml` | The agent's axis-4 regime — distinct from the fabric's `policy-bundle.yaml` | `[ADAPT]`: `class_id`, everything under `declaration:`. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/agent-debt-profile.yaml` | The agent's axis-5 tolerance: risk sensitivity and the two D_c bands | `[ADAPT]`: `class_id`, every calibrated value. `[MECHANISM]`: `risk_sensitivity`, `forced_llm_threshold`, `fail_closed_threshold` |
| `artifacts/prompt-artifact.yaml` | The axis-6 prompt artifact: template text and declared parameters | `[ADAPT]`: name, tenant, template text, parameter names. `[MECHANISM]`: `declared_parameters`, `template` |
| `artifacts/agent-registration.yaml` | The Control Plane keys the author-versioned artifacts register under | `[ADAPT]`: every key path. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/resolution-spec.yaml` | Entity classes, identity keys, relationship rules | `[ADAPT]`: class names, match keys, attribute names, relationship types. `[MECHANISM]`: `entity_rules`, `match_key`, `identity_keys`, `relationship_rules` |
| `artifacts/policy-bundle.yaml` | The policy bundle the *fabric* boots under | `[ADAPT]`: `class_id`, regime, jurisdiction, classifications. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/operator-parameters-*.yaml` | One document per operator category: traversal bounds, temporal axes, policy classification map, similarity query and corpus map | `[ADAPT]`: every class name, attribute name, query and numeric value. `[MECHANISM]`: the parameter field names |
| `artifacts/product-class.yaml` | The served class: schema lane, TTL anchor, assembly mode, MAX_TTL key, and the authored `required_operator_keys` Gate 2 compares against | `[ADAPT]`: schema name, lane, MAX_TTL key, operator key names. `[MECHANISM]`: every field name and the two enum values |
| `artifacts/product-governance.yaml` | MAX_TTL seconds, product TTL, similarity index version, plan id, replay record class | `[ADAPT]`: `class_id`, every value. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/perspective.yaml` | The Π role-conditioning the product is served under | `[ADAPT]`: principal id, role. `[MECHANISM]`: `principal_id`, `role` |
| `artifacts/half-life-table.yaml` | λ_c calibrations per observation type | `[ADAPT]`: observation-type names, calibrations. `[MECHANISM]`: `half_life_seconds`, `decay_driver`, `supersession_event` |
| `artifacts/debt-evaluation.yaml` | The observations to score, the C/S factors, and the reviewed `expected_signal` | `[ADAPT]`: `class_id`, observation types, dates, factor values, `expected_signal`. `[MECHANISM]`: `observations`, `completeness`, `semantic_consistency`, `expected_signal` |
| `artifacts/events.yaml` | The L1 signal stream, in the SDK's envelope vocabulary with the source systems' payload keys | `[ADAPT]`: everything under `raw_payload:`, source system ids. `[MECHANISM]`: `envelope_id`, `tenant_id`, `source`, `system_id`, `ingestion_timestamp`, `observed_time`, `raw_payload` |
| `artifacts/decision.yaml` | This run's temporal boundary and decision instant | `[ADAPT]`: `class_id`, both instants. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/expected.yaml` | What the served product should contain, plus the axis-3 role and the axis-4 exclusion | `[ADAPT]`: `class_id`, every value. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/analysis-output.yaml` | The scripted analyst's model identifier and canned output records | `[ADAPT]`: `class_id`, model identifier, output fields and values. `[MECHANISM]`: `model_version`, `outputs` |

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

`artifacts/agent-definition.yaml` is the axis surface. To rebind the agent
for a new domain, edit these exact keys and expect these observable
changes:

1. `archetypes` (axis 1) — the composition in replay dimension 4 changes
   with the list.
2. `context_contract.consumes[0].product_class` (axis 2) — must match
   `schema_name` in `product-class.yaml`, or the contract-admission checks
   fail.
3. `perspective.role` (axis 3) — must match `role` in `perspective.yaml`
   and `declaration.role` in `expected.yaml`; the served payload's `role`
   field follows it.
4. `agent-policy-regime.yaml` (axis 4) — your regime's classifications;
   update `declaration.excluded_entity_classes` in `expected.yaml` to
   whatever your regime excludes.
5. `agent-debt-profile.yaml` (axis 5) — your thresholds; then recalibrate
   `half-life-table.yaml` and `debt-evaluation.yaml` and re-review
   `expected_signal`.
6. `instruction_bindings` (axis 6) — point at your prompt artifact in
   `prompt-artifact.yaml`; parameters must match its
   `declared_parameters`.

Then rename the domain vocabulary in `resolution-spec.yaml`/`events.yaml`,
run the test module, review the failures, and deliberately update
`expected.yaml` — that reviewed edit is the workflow, not a bug.

## What would fail

One concrete row per specialization axis, plus the fabric invariants the
example inherits:

| Invariant | What would fail here |
| --- | --- |
| axis 1 — archetype binding | remove or reorder `archetypes:` and the composition checks against replay dimension 4 and `agent.components` fail — identity derives from the definition, never from code |
| axis 2 — context contract | rename `context_contract.consumes[0].product_class` and the contract-admission checks fail: the agent would be consuming a product class it never declared |
| axis 3 — perspective | rebind `perspective.role` in one of the two documents that name it and the served payload's `role` no longer equals the definition's Π role — the view is conditioned for someone else |
| axis 4 — policy regime | admit `restricted` into the operator's permitted classifications and the defence-sector `site` survives into the served view, tripping the by-name `excluded_entity_classes` check |
| axis 5 — half-life/debt profile | raise `forced_llm_threshold` above the computed D_c and the routing signal drops to `ok`, contradicting the reviewed `expected_signal: forced_llm` — the gate visibly stops gating |
| axis 6 — instruction bindings | change the prompt's `declared_parameters` without changing the binding's `parameters` (or vice versa) and the parameter-equality check fails; an inline prompt string in `run.py` instead would trip the No-Hardcoding lint |
| factory-only construction | instantiating `Agent` directly in code bypasses Control Plane resolution — nothing in this directory does, and the lint keeps it that way |
| Gate 2 — lineage strict equality | `required_operator_keys` in `product-class.yaml` is the authored declared side; a plan built from the operator registry's own keys would make the gate compare a value against itself |
| replay dimension 4 | the definition hash, versioned URI, archetype composition and grant-set hash must survive the ArtifactStore round trip byte-identically |
