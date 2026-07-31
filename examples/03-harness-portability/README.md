# examples/03-harness-portability — one agent, three harnesses (EXAM-04)

The harness-neutrality proof (CLAUDE.md §7.3, mission success condition 3):
**one** agent definition — `artifacts/agents/order_insights.yaml`, loaded
once, producing one `Agent` object — executed unmodified under all three
D-IMPL-24 reference adapters (Claude Agent SDK, Google ADK, LangGraph), with
byte-level equivalence asserted across the legs. *Portability is
demonstrated, not asserted.*

Domain: e-commerce (orders / catalog / customers), authored fresh
(D-IMPL-52).

## Run it

```sh
make example-03          # deterministic base leg — no network, no keys
```

Exit 0 means every assertion held. The live legs
(`make example-03-live-ollama` / `make example-03-live-anthropic`) land in
plan 08-11; until then `--mode live` exits 2 with a pointer.

## What this demonstrates

| Invariant | What would fail here |
| --- | --- |
| One definition, three harnesses (§6.5, §7.3) | A definition that named a harness, or three near-identical definitions posing as one — the same `Agent` object is handed to every adapter |
| Consumed product byte-identical (D-02) | An adapter that rewrote, interpolated, or truncated what it delivered — the product is *recovered out of each harness-native carrier*, not compared against itself |
| Governed replay fields exactly equal (D-18) | A harness-attributable value reaching a field CCF governs — the divergent field names itself |
| Harness attribution isolated and distinct | Three traces that collapsed to one, a dropped trace, or a trace claiming another harness's run |
| Real loop machinery, no model (D-02) | A hand-built execution result: the Claude leg runs a real `ClaudeSDKClient` session over a custom `Transport` (the `ResultMessage` is SDK-constructed — advisory A3's example-side evidence), the ADK leg a real `Runner`, the LangGraph leg a real compiled graph. A socket guard fails the run on any network attempt |
| Five dimensions, live (INV-CH7-80) | A record that lost or grew a dimension |
| No-Hardcoding (§6.4) | Any domain or deployment value in code — every model id, server name, session id, threshold, and query lives in `artifacts/*.yaml`; deleting `artifacts/` leaves the code nothing to run |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §7.4–§7.6 (operators, projection, product contract), §7.10.1
(five-dimension replay record). CLAUDE.md §6.1/§6.2 (archetype/agent
separation, six axes), §6.5 (agents name no harness), §7.3 (the four
adapter seams; the neutral seams are the stable layer), §9 (this example's
charter), §6.4 (No-Hardcoding).

## What to change first

`artifacts/` is the specialization surface. Point
`artifacts/agents/order_insights.yaml` at your own product class and policy
regime, swap the ontology/events for your domain, and put your deployment's
model identifiers and session vocabulary in `artifacts/harnesses.yaml` —
the code in `run.py` and `legs/` is mechanism and should not need editing.
