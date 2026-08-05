# examples/03-harness-portability — one agent, three harnesses, byte-identical context

## What this demonstrates

The harness-neutrality proof (CLAUDE.md §7.3, mission success condition
3): **one** agent definition — `artifacts/agents/order_insights.yaml`,
loaded once, producing one `Agent` object — executed unmodified under
all three D-IMPL-24 reference adapters (Claude Agent SDK, Google ADK,
LangGraph). *Portability is demonstrated, not asserted.* An agent here
is a declared, versioned artifact, not code (Archetype vs agent: an
archetype is a functional template the SDK ships as code; an agent is a
declared, versioned Control Plane artifact the Agent Factory produces
from one — CLAUDE.md §6.1, SDK extension); what every harness consumes
is a Context Product (a typed, validated, replay-ready unit of decision
context the fabric derives and serves — a contract, not a stored
record; whitepaper §6.3, §7.6), and what every run leaves behind is a
Decision Replay record (the five-dimension record — fabric snapshot,
policy bindings, model version, perspective conditioning, generation
path — that lets a decision be reproduced exactly; whitepaper §7.10).

Domain: e-commerce (orders / catalog / customers / shipments), authored
fresh (D-IMPL-52 — the suite is a horizontal mix of domains; this
example's domain deliberately differs from the banking quickstart).

## Run it

```sh
make example-03
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/03-harness-portability/run.py --mode deterministic
```

Exit code 0 means the deterministic spine ran across all three harness
legs. Its **assertions** — including the two-harness equivalence assertion
this example exists for — live in
`tests/examples/test_harness_portability_output.py` and are run by `pytest`
(D-09), because `make examples` proves a spine runs and a test runner proves
it is correct. The live legs keep their assertions in `run.py`: they are
excluded from `make ci` by design, so a runner that could fail them does not
exist. Exit 2 is a refusal with a diagnostic — never a silent skip.

Two **opt-in live legs** exist and are *never run in CI*:

```sh
make example-03-live-ollama     # live, keyless local Ollama (opt-in)
make example-03-live-anthropic  # live, Anthropic — gated on ANTHROPIC_API_KEY
```

Live-leg provider endpoints, models, timeouts, and the run budget live
in `artifacts/live.yaml` and the environment (`CCF_OLLAMA_BASE_URL`,
`CCF_OLLAMA_MODEL`, `CCF_LIVE_TIMEOUT_SECONDS`, `ANTHROPIC_API_KEY` —
the key is never stored or logged; absence is a refusal). A locality
note: Ollama serves `*-cloud` models by relaying to ollama.com — check
`ollama list` if locality matters.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `pytest tests/examples/test_harness_portability_output.py`,
> review what it reports, then deliberately edit
> `artifacts/expected.yaml` to match what you reviewed —
> regeneration is a reviewed event, landed in the same commit as the
> enrichment, with the commit body summarizing what changed in the
> output and why. No `make regen-*` targets exist, and none will be
> added.

## The story

### Deterministic mode (the CI leg)

Real harness loop machinery over scripted/no-model transports: a real
`ClaudeSDKClient` session over a custom `Transport`, a real ADK
`Runner`, a real compiled LangGraph graph. A process-global socket
guard fails the run on any network attempt — and `run.py` refuses to
proceed unless the guard actually fires, so the "no network" claim is
established rather than assumed.

The fabric boots from `artifacts/manifest.yaml` in one `load_and_boot`
call, ingests the events in
`artifacts/events.yaml` — a customer asserted by two source systems
(one node, lineage by set-union), a second order the similarity
operator must rank out, a restricted age-gated catalog item the policy
operator must substitute out, and a stalled shipment attached to the
delayed order via the `shipped_via` edge — and serves one gated
product: three entity classes (`customer`, `order`, `shipment`), two
surviving relationship types, per `artifacts/expected.yaml`.

**Equivalence is byte-level.** The Context Product recovered out of
each harness-native carrier is byte-identical across the three legs and
to what the fabric admitted; the governed replay fields are exactly
equal field by field; the governed emission is one effect whichever
harness drove it; and the three harness traces stay distinct and
isolated from every governed field. The shipment enrichment widens
exactly this surface: more entities, more typed edges, the same
byte-for-byte agreement.

### Live mode (opt-in, never CI)

The same fabric, the same agent, the same adapters — but each harness's
own model seam is bound to a live provider:

| Harness | Model seam binding |
| --- | --- |
| Claude Agent SDK | **Native endpoint**: the real CLI session targets the provider directly — Anthropic natively, or Ollama through its Anthropic-compatible `/v1/messages` via `ANTHROPIC_BASE_URL` on `ClaudeAgentOptions.env` |
| Google ADK | ADK's own model-binding surface: a `BaseLlm` registered on `LLMRegistry` for the configured model name, wrapping the provider client; the adapter's real `LlmAgent` is driven by a real `Runner` |
| LangGraph | A deployment-injected model callable (LangGraph owns no loop): it consumes exactly the carrier's injected state, and provider-reported values travel through the adapter's real compiled graph on LangChain's own tracing keys |

**Equivalence in live mode is structural, never byte-equal.** Live
model output varies by construction, so the assertions live on what CCF
governs: each leg consumed the *same Context Product* (same product
class, version, and lineage identity, recovered out of each carrier);
each replay record carries *exactly five typed dimensions* with the
agent version, model version record (this harness's own live trace —
reported model, trace id, token counts, all populated), and skill-set
in force; and every effect passed through *governed emission*. Nothing
asserts what the model said. This is deliberately weaker than the
deterministic mode's byte equality — and that distinction is the point
of having both modes.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/agents/order_insights.yaml` | THE one agent definition all three legs share — six specialization axes, naming no harness | `[ADAPT]` tenant, names, roles, thresholds; `[MECHANISM]` the six axis field names, `referenced_artifacts` structure, `ref` URI scheme |
| `artifacts/manifest.yaml` | The one document naming every fabric artifact in force, its Control Plane key, its class, and its `role` (D-IMPL-80) | `[ADAPT]` keys, paths, deployment class ids; `[MECHANISM]` field names, `ccf.`-prefixed class ids, `role` values |
| `artifacts/resolution-spec.yaml` | The deployment vocabulary: four entity classes, three typed edges | `[ADAPT]` classes, types, attribute names; `[MECHANISM]` rule-block field names |
| `artifacts/policy-bundle.yaml` | The policy bundle the *fabric* boots under — distinct from the agent's axis-4 regime | `[ADAPT]` `class_id` and everything under `declaration:`; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/operator-parameters-{traversal,temporal,policy,similarity}.yaml` | One document per operator category, each carrying the attribute map its own operator reads | `[ADAPT]` queries, thresholds, class and attribute names; `[MECHANISM]` field names |
| `artifacts/perspective.yaml` | The Π role-conditioning the product is served under | `[ADAPT]` principal id, role; `[MECHANISM]` `principal_id`, `role` |
| `artifacts/product-class.yaml` | The served class, its TTL anchor, its MAX_TTL key, and `required_operator_keys` — the authored declared side of Gate 2 | `[ADAPT]` names and operator keys; `[MECHANISM]` field names and enum values |
| `artifacts/product-governance.yaml` | The governance numbers the SDK declines to own: the TTL ceiling, the product TTL, the corpus version identity, the plan id | `[ADAPT]` every value; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/decision.yaml` | This run's instants and the axis-6 instruction parameter values — `role: load`, never in replay dimension 2 | `[ADAPT]` every value; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/expected.yaml` | What the served product should contain, and how many harness legs this deployment stands up | `[ADAPT]` every value; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/events.yaml` | The L1 signal envelopes: lineage pair, rank-out order, restricted item, stalled shipment | `[ADAPT]` all payload content; `[MECHANISM]` envelope field names |
| `artifacts/prompt.yaml` | The axis-6 prompt artifact — template and declared parameters, rendered once by the fabric | `[ADAPT]` template text, parameter names; `[MECHANISM]` `declared_parameters`, `template` |
| `artifacts/harnesses.yaml` | Per-harness deployment values (session vocabulary, reported models) for the deterministic legs | `[ADAPT]` model ids, session values; `[MECHANISM]` the per-harness block names the legs read |
| `artifacts/live.yaml` | Live-leg providers, endpoints, timeouts, run budget (opt-in legs only, never CI) | `[ADAPT]` providers, models, budgets; `[MECHANISM]` `providers`/`runner` block field names |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §7.4–§7.6 — operators, projection, product contract
- whitepaper §7.10 — the five-dimension replay record
- CLAUDE.md §6.1/§6.2 — archetype/agent separation, six axes (SDK
  extension)
- CLAUDE.md §6.5 — agents name no harness (SDK extension)
- CLAUDE.md §7.3 — the four adapter seams; the neutral seams are the
  stable layer (SDK extension)
- CLAUDE.md §6.4 — No-Hardcoding (SDK extension)
- CLAUDE.md §9 — this example's charter: the harness-neutrality proof

## What to change first

`artifacts/` is the specialization surface. Point
`artifacts/agents/order_insights.yaml` (keys
`agent_definition.context_contract.consumes[0].product_class` and
`policy_regime.ref`) at your own product class and policy regime, swap
`artifacts/resolution-spec.yaml` and `artifacts/events.yaml` for your domain,
put your deployment's model identifiers and session vocabulary in
`artifacts/harnesses.yaml`, and your live providers, timeouts, and
budget in `artifacts/live.yaml`. Every document in force is enumerated by
`artifacts/manifest.yaml`, so a new artifact is not in force until it is
named there. On the next run, expect the served payload to change — review
it and update `artifacts/expected.yaml` in the same commit. The code in
`run.py` and `legs/` is mechanism and should not need editing.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| One definition, three harnesses (CLAUDE.md §6.5, §7.3) | A definition that named a harness, or three near-identical definitions posing as one — the same `Agent` object is handed to every adapter, in both modes |
| Consumed product byte-identical (deterministic) | An adapter that rewrote, interpolated, or truncated what it delivered — the product is *recovered out of each harness-native carrier*, not compared against itself |
| Same product class/lineage identity (live) | A live leg consuming a different product, or a carrier that corrupted lineage — structural identity is asserted per leg |
| Governed replay fields exactly equal | A harness-attributable value reaching a field CCF governs — the divergent field names itself |
| Harness attribution isolated and distinct | Three traces that collapsed to one, a dropped trace, or a trace claiming another harness's run |
| Real loop machinery | A hand-built execution result: deterministic legs run real SDK sessions over scripted wires; live legs run the same loops against a live model |
| All four adapter seams under live legs | A live leg that bypassed context injection, skill exposure, effect capture, or replay hooks — each is asserted per leg |
| Five dimensions, live | A record that lost or grew a dimension |
| Zero harness imports in core (CLAUDE.md §7.3) | A harness package imported anywhere in `/src` — the harness-import lint in `make lint` rejects it; adapters live only under `/runtime/adapters/` |
| No-Hardcoding (CLAUDE.md §6.4) | Any domain or deployment value in code — every model id, endpoint, timeout, budget, session id, and drive turn lives in `artifacts/*.yaml` or the environment; deleting `artifacts/` leaves the code nothing to run |
