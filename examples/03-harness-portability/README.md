# examples/03-harness-portability — one agent, three harnesses (EXAM-04)

The harness-neutrality proof (CLAUDE.md §7.3, mission success condition 3):
**one** agent definition — `artifacts/agents/order_insights.yaml`, loaded
once, producing one `Agent` object — executed unmodified under all three
D-IMPL-24 reference adapters (Claude Agent SDK, Google ADK, LangGraph).
*Portability is demonstrated, not asserted.*

Domain: e-commerce (orders / catalog / customers), authored fresh
(D-IMPL-52 — the suite is a horizontal mix of domains; this example's
domain deliberately differs from the banking quickstart).

## Run it — two modes, three commands

```sh
make example-03                 # deterministic — no network, no keys (CI leg)
make example-03-live-ollama     # live, keyless local Ollama (opt-in)
make example-03-live-anthropic  # live, Anthropic — gated on ANTHROPIC_API_KEY
```

Exit 0 means every assertion held. Exit 2 is a refusal with a diagnostic —
provider unreachable, key absent, or live budget exhausted — never a
silent skip.

### Deterministic mode (D-01/D-02)

Real harness loop machinery over scripted/no-model transports: a real
`ClaudeSDKClient` session over a custom `Transport`, a real ADK `Runner`,
a real compiled LangGraph graph. A process-global socket guard fails the
run on any network attempt. **Equivalence is byte-level**: the Context
Product recovered out of each harness-native carrier is byte-identical
across the three legs and to what the fabric admitted, and the governed
replay fields (D-18) are exactly equal field by field.

### Live mode (D-03/D-04)

The same fabric, the same agent, the same adapters — but each harness's
own model seam is bound to a live provider:

| Harness | Model seam binding |
| --- | --- |
| Claude Agent SDK | **Native endpoint** (outcome A): the real CLI session targets the provider directly — Anthropic natively, or Ollama through its Anthropic-compatible `/v1/messages` via `ANTHROPIC_BASE_URL` on `ClaudeAgentOptions.env` |
| Google ADK | ADK's own model-binding surface at 2.5.0: a `BaseLlm` registered on `LLMRegistry` for the configured model name, wrapping the provider client; the adapter's real `LlmAgent` is driven by a real `Runner` |
| LangGraph | A deployment-injected model callable (LangGraph owns no loop): it consumes exactly the carrier's injected state, and provider-reported values travel through the adapter's real compiled graph on LangChain's own tracing keys |

**Equivalence in live mode is structural, never byte-equal (D-04).** Live
model output varies by construction, so the assertions live on what CCF
governs: each leg consumed the *same Context Product* (same product class,
version, and lineage identity, recovered out of each carrier); each replay
record carries *exactly five typed dimensions* with the agent version,
model version record (this harness's own live trace — reported model,
trace id, token counts, all populated), and skill-set in force; and every
effect passed through *governed emission*. Nothing asserts what the model
said. This is deliberately weaker than the deterministic mode's byte
equality — and that distinction is the point of having both modes.

### Provider configuration (all values env or artifact, never code)

| Variable | Meaning | Default |
| --- | --- | --- |
| `CCF_OLLAMA_BASE_URL` | Ollama endpoint | `providers.ollama.default_base_url` in `artifacts/live.yaml` |
| `CCF_OLLAMA_MODEL` | Ollama model | `providers.ollama.default_model` in `artifacts/live.yaml` |
| `CCF_LIVE_TIMEOUT_SECONDS` | Per-call provider timeout | `runner.default_timeout_seconds` in `artifacts/live.yaml` |
| `ANTHROPIC_API_KEY` | Anthropic key (required for the anthropic provider) | none — absence is a refusal, the key is never stored or logged |

The whole live run is additionally bounded by `runner.budget_seconds`
(`artifacts/live.yaml`); a breached budget exits 2 with a diagnostic.

> **Locality note (RESEARCH Pitfall 2).** Ollama serves `*-cloud` models
> by relaying to ollama.com — whether a live-ollama run is genuinely local
> depends on the model you configure. The default in `artifacts/live.yaml`
> is a locally pulled model; check `ollama list` if locality matters.

## What this demonstrates

| Invariant | What would fail here |
| --- | --- |
| One definition, three harnesses (§6.5, §7.3) | A definition that named a harness, or three near-identical definitions posing as one — the same `Agent` object is handed to every adapter, in both modes |
| Consumed product byte-identical (D-02, deterministic) | An adapter that rewrote, interpolated, or truncated what it delivered — the product is *recovered out of each harness-native carrier*, not compared against itself |
| Same product class/lineage identity (D-04, live) | A live leg consuming a different product, or a carrier that corrupted lineage — structural identity is asserted per leg |
| Governed replay fields exactly equal (D-18) | A harness-attributable value reaching a field CCF governs — the divergent field names itself |
| Harness attribution isolated and distinct | Three traces that collapsed to one, a dropped trace, or a trace claiming another harness's run |
| Real loop machinery (D-02/D-03) | A hand-built execution result: deterministic legs run real SDK sessions over scripted wires (the Claude `ResultMessage` is SDK-constructed — advisory A3's example-side evidence); live legs run the same loops against a live model |
| All four adapter seams under live legs | A live leg that bypassed context injection, skill exposure, effect capture, or replay hooks — each is asserted per leg |
| Five dimensions, live (INV-CH7-80) | A record that lost or grew a dimension |
| No-Hardcoding (§6.4) | Any domain or deployment value in code — every model id, endpoint, timeout, budget, session id, and drive turn lives in `artifacts/*.yaml` or the environment; deleting `artifacts/` leaves the code nothing to run |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §7.4–§7.6 (operators, projection, product contract), §7.10.1
(five-dimension replay record). CLAUDE.md §6.1/§6.2 (archetype/agent
separation, six axes), §6.5 (agents name no harness), §7.3 (the four
adapter seams; the neutral seams are the stable layer), §9 (this example's
charter), §6.4 (No-Hardcoding).

## What to change first

`artifacts/` is the specialization surface. Point
`artifacts/agents/order_insights.yaml` at your own product class and policy
regime, swap the ontology/events for your domain, put your deployment's
model identifiers and session vocabulary in `artifacts/harnesses.yaml`,
and your live providers, timeouts, and budget in `artifacts/live.yaml` —
the code in `run.py` and `legs/` is mechanism and should not need editing.
