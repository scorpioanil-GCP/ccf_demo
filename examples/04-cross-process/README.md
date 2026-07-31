# examples/04-cross-process — assembler ↔ consumer over MCP and A2A (EXAM-05)

One typed Context Product crosses a **real process boundary** twice: an
assembler agent (the §6.3 `ContextAssemblyAgent` case) runs in its own OS
subprocess and serves its product over **MCP egress** and over **A2A
federation**; the consumer — this process — reads it over both wires and
runs **Control Plane admission verification** before anything reaches its
graph, including a working refusal path for a tampered envelope.

Together with `examples/05-workflow-hitl`, this example composes into the
suite's full end-to-end deployment (CLAUDE.md §9).

Run it:

```
make example-04
```

(or `PYTHONPATH=src:runtime python examples/04-cross-process/run.py`).
Exit code 0 means every assertion held — including the negative admission
case. Keyless and model-free (D-12): signing keys are generated per run
into a temp directory and never committed; no model is called anywhere.

## What it demonstrates

| Invariant / commitment | What would fail here |
| --- | --- |
| Process separation | An in-process double would share a heap, and "the consumer holds no write handle to the producer's graph" would be vacuous. Here it is literally true: two fabrics, two SQLite files, two Control Planes, two heaps. |
| READY handshake, never sleep-and-hope | The child binds ephemeral ports itself and prints `READY {mcp_port} {a2a_port}` only once both servers report started **and** both A2A emissions were accepted; the parent's blocking `readline()` is the gate. A sleep-gated exchange passes against a server that never started. |
| MCP egress (whitepaper §8.3 Pattern 3; CLAUDE.md §7.1) | The product arrives as an MCP Resource and its typed contract validates; any re-encode en route would break the byte-equality with the A2A leg below. |
| One product, two front doors | The MCP bytes are asserted byte-equal to the payload the A2A signature was made over — the two transports serve one canonical product, not two look-alikes. |
| A2A admission before L3 (Pattern 4; CLAUDE.md §7.2; D-IMPL-16) | An inbound product is admitted only after signature verification against the peer's own trust-policy entry and the Control Plane policy-binding checks. Skipping the gate would put a peer's claims in the graph on the peer's say-so. |
| Immutable `AdmissionRecord` at an exact version | The audit verdict points at the record by content address, the ArtifactStore holds it, and the record's content hashes back to that address — no "latest", no overwrite path (D-IMPL-26/58). |
| Lineage continuity by set-union (CLAUDE.md §7.2) | The merged lineage is asserted to be exactly `producer ∪ consumer` on both operator and policy axes; replacement in either direction fails. |
| Admission only through L2 (single-writer, CLAUDE.md §10) | The graph digest moves only when `ingest_admitted` — typed to accept only gate-produced `AdmittedProduct` values — runs. No other write path exists to demonstrate. |
| The refusal path is real | A tampered envelope (a genuine signature spliced onto different payload bytes, emitted over the real socket) is refused as a value, the refusal is audited, and the consumer's L3 substrate is byte-identical before and after. |
| Factory-only agent construction (CLAUDE.md §6.4) | The assembler is constructed by the Agent Factory from `artifacts/agent.yaml`; no agent exists in code in this directory. |
| No-Hardcoding (CLAUDE.md §6.4) | Every tenant, entity class, peer identity, ceiling, endpoint path and threshold lives in `artifacts/*.yaml`. Delete the artifacts and both drivers have nothing to run. |

## Why property intelligence (D-09)

Multi-source situational assembly — properties, zones, sensor observations,
occupancy signals from four source systems, fused into one decision-ready
situational product and served to consumers in other processes — is the
archetypal cross-process assembler case. It deliberately mirrors the
*shape* of the Homecams property-intelligence deployment that validated
CCF's claims, with **zero of its code**: per D-07/D-08, every artifact in
this directory (`larkfield-estates` — its ontology, events, peers, keys,
ceilings and thresholds) was authored 100% fresh for this example, and
nothing was ported, copied, or adapted from `/home/parkave/homecams_v2`.
The SDK covering Homecams' ground with none of its code is the
general-purposeness claim (CLAUDE.md §1) made demonstrable.

## What it exercises

- Whitepaper §8.3 Patterns 3 and 4 (MCP integration; A2A federation)
- CLAUDE.md §7.1 (MCP as egress), §7.2 (A2A first-class: trust-boundary
  verification, lineage continuity), §6.1/§6.3/§6.4 (archetype/agent
  separation, `ContextAssemblyAgent`, factory-only construction,
  No-Hardcoding), §10 (single-writer)
- D-IMPL-14/15/16 (typed-HTTP wire, detached-JWS identity, verify every
  inbound product), D-IMPL-26/58 (content-addressed admission records)

## Files

- `run.py` — the consumer: hosts the A2A endpoint, spawns the child
  (`start_new_session=True`, stderr captured, whole-process-group teardown
  via `killpg`), consumes over MCP, drives admission, asserts the refusal.
- `producer_child.py` — the assembler subprocess: boots its own fabric from
  the artifacts, factory-constructs the assembler agent, signs, emits the
  genuine and the tampered envelope, serves MCP egress and its own A2A
  endpoint on ephemeral ports.
- `artifacts/` — the deployment: ontology, events, Control Plane bundle,
  A2A federation values, agent definition, prompt artifact. **This is the
  specialization surface** — change these first to adapt the example.

## What to change first

Everything domain-specific is in `artifacts/`. Rename the tenant, swap the
entity classes and relationship vocabulary, change the peer identities and
ceilings in `a2a.yaml` — neither driver changes, which is the point.
