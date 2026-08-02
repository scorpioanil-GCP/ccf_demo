# examples/04-cross-process — one product, two wires, and a gate the peer cannot talk past

## What this demonstrates

One typed Context Product (a typed, validated, replay-ready unit of
decision context the fabric derives and serves — a contract, not a
stored record; whitepaper §6.3, §7.6) crosses a **real process
boundary** twice: an assembler agent (the `ContextAssemblyAgent`
archetype — CLAUDE.md §6.3, SDK extension) runs in its own OS
subprocess and serves its product over **MCP integration** (Model
Context Protocol as an integration surface — Pattern 3 in the
whitepaper; bidirectional in the SDK; whitepaper §8.3, CLAUDE.md §7.1
SDK extension) and over **A2A federation** (Agent-to-Agent exchange of
Context Products across process or organizational boundaries, with
Control Plane admission verification on the consumer side; whitepaper
§8.3 Pattern 4, CLAUDE.md §7.2 SDK extension). The consumer — this
process — reads it over both wires and runs Control Plane admission
verification before anything reaches its Context Graph (the fabric's
typed state `G(E, R, T, P, Π, L)`; whitepaper §5.2, §7.3), including a
working refusal path for a tampered envelope.

Together with `examples/05-workflow-hitl`, this example composes into
the suite's full end-to-end deployment (CLAUDE.md §9).

Domain rationale: multi-source property situational assembly is the
archetypal cross-process assembler case. It deliberately mirrors the
*shape* of the property-intelligence deployment that validated CCF's
claims, with **zero of its code** — every artifact in this directory
(`larkfield-estates`) was authored 100% fresh, and nothing was ported
from any prior system. The SDK covering that ground with none of its
code is the general-purposeness claim (CLAUDE.md §1) made demonstrable.

## Run it

```sh
make example-04
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/04-cross-process/run.py
```

Exit code 0 means every assertion held — including the negative
admission case. Keyless and model-free: signing keys are generated per
run into a temp directory and never committed; every identity and
trust value in `artifacts/a2a.yaml` is obviously synthetic; no model is
called anywhere.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-04`, review the assertion output, then
> deliberately edit the `expected:` block in
> `artifacts/controlplane.yaml` to match what you reviewed —
> regeneration is a reviewed event, landed in the same commit as the
> enrichment, with the commit body summarizing what changed in the
> output and why. No `make regen-*` targets exist, and none will be
> added.

## The story

The producer child (`producer_child.py`) boots its own fabric from the
artifacts — its own SQLite file, its own Control Plane, its own heap —
factory-constructs the assembler agent from `artifacts/agent.yaml`,
ingests the events in `artifacts/events.yaml` (a property asserted by
two source systems converging on one node; two perimeter sensors the
similarity operator must keep and one greenhouse sensor it must rank
out; a restricted occupancy signal the policy operator must substitute
out), and serves the gated four-entity product on two ephemeral-port
front doors. It prints `READY {mcp_port} {a2a_port}` only once both
servers report started **and** both A2A emissions were accepted; the
parent's blocking `readline()` is the gate — no fixed ports, no
sleep-and-hope.

The consumer then works through three movements:

1. **MCP egress.** The product arrives as an MCP Resource and its
   typed contract validates. The MCP bytes are asserted byte-equal to
   the payload the A2A signature was made over — two front doors, one
   canonical product, not two look-alikes.
2. **A2A admission — the Pattern-4 teaching moment.** The genuine
   signed envelope is admitted only after signature verification
   against the peer's trust-policy entry (built from
   `artifacts/a2a.yaml`, key `producer` — peer id, key id, permitted
   producer hash, permitted schema names, permitted policy regimes)
   and the Control Plane policy-binding checks. An immutable
   `AdmissionRecord` is persisted at an exact content address before
   anything is reported admitted. The merged lineage is asserted to be
   exactly `producer ∪ consumer` on both operator and policy axes —
   and both sides contribute operators the other lacks (see
   `artifacts/a2a.yaml`, key `consumer.lineage.operators_invoked`), so
   the printed union is evidence of set-union continuity, not of
   replacement in either direction. Only then does the admitted value
   pass through L2's typed federated door — the single writer — and
   the graph digest moves.
3. **The refusal path is real.** A tampered envelope — a genuine
   signature spliced onto different payload bytes, emitted over the
   real socket — is refused as a value (`SignatureRefusal` naming the
   peer), the refusal is audited, and the consumer's L3 substrate is
   byte-identical before and after. Unverified bindings never reach
   L3; the peer's say-so is not admission.

The federated entities resolve into the consumer's own declared
`federated_entity` class rather than merging into its vocabulary
(see `artifacts/a2a.yaml`, key `federation.entity_rule`): a peer's
claims are claims about *another fabric's graph*, and merging them
would assert the consumer had independently observed them.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/a2a.yaml` | The federation exchange: consumer identity, ceilings, endpoint path, consumer's own lineage; producer peer id / key id / producer hash; how admitted products become L1 signal | `[ADAPT]` peer ids, ceilings, path, lineage values, federation vocabulary; `[MECHANISM]` `consumer`/`producer`/`federation` field names |
| `artifacts/agent.yaml` | The assembler agent definition — six specialization axes, `context_assembly` archetype | `[ADAPT]` tenant, names, thresholds; `[MECHANISM]` the six axis field names, `referenced_artifacts` structure |
| `artifacts/controlplane.yaml` | Fabric bundle: keys, policy bundle, operator parameters (incl. the perimeter similarity query), product class, decision instants, the `expected:` block | `[ADAPT]` all values including `expected:`; `[MECHANISM]` every field name |
| `artifacts/ontology.yaml` | The producer's vocabulary: four entity classes, three typed edges, classification and similarity-corpus maps | `[ADAPT]` classes, types, attribute names; `[MECHANISM]` rule-block field names |
| `artifacts/events.yaml` | The L1 signal envelopes: lineage pair, two kept sensors, one ranked-out sensor, one restricted signal | `[ADAPT]` all payload content; `[MECHANISM]` envelope field names |
| `artifacts/prompt.yaml` | The axis-6 prompt artifact — template and declared parameters | `[ADAPT]` template text, parameter names; `[MECHANISM]` `declared_parameters`, `template` |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §8.3 Pattern 3 — MCP integration (Context Product export)
- whitepaper §8.3 Pattern 4 — A2A federation and trust-boundary
  verification
- CLAUDE.md §7.1 — MCP as egress (SDK extension: bidirectional)
- CLAUDE.md §7.2 — A2A first-class: admission before L3, lineage
  continuity by set-union (SDK extension)
- CLAUDE.md §6.1/§6.3/§6.4 — archetype/agent separation,
  `ContextAssemblyAgent`, factory-only construction, No-Hardcoding
  (SDK extensions)
- CLAUDE.md §10 — the single-writer invariant, held across the
  federation boundary

## What to change first

Everything domain-specific is in `artifacts/`. Start with
`artifacts/a2a.yaml`: change `producer.peer_id`, `producer.key_id` and
`producer.producer_hash` to your own peer's identity, and the
`consumer` block's ceilings (`inbound_payload_ceiling_bytes`,
`max_request_bytes`) and `receive_path` to your deployment's numbers
and URL space. Then rename the tenant and swap the entity classes in
`artifacts/ontology.yaml` and the payloads in `artifacts/events.yaml`.
On the next run, expect the served product and the merged lineage to
change — review the output and update `artifacts/controlplane.yaml`'s
`expected:` block in the same commit. Neither driver changes, which is
the point.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| Process separation | An in-process double would share a heap, and "the consumer holds no write handle to the producer's graph" would be vacuous. Here it is literally true: two fabrics, two SQLite files, two Control Planes, two heaps. |
| READY handshake, never sleep-and-hope | The child prints `READY` only once both servers started **and** both A2A emissions were accepted; a sleep-gated exchange passes against a server that never started. |
| MCP egress (whitepaper §8.3 Pattern 3) | The product arrives as an MCP Resource and its typed contract validates; any re-encode en route would break the byte-equality with the A2A leg. |
| One product, two front doors | The MCP bytes are asserted byte-equal to the payload the A2A signature was made over. |
| A2A admission before L3 (Pattern 4; CLAUDE.md §7.2) | An inbound product is admitted only after signature verification against the peer's trust-policy entry and the Control Plane policy-binding checks. Skipping the gate would put a peer's claims in the graph on the peer's say-so. |
| Immutable `AdmissionRecord` at an exact version | The audit verdict points at the record by content address, the ArtifactStore holds it, and the record's content hashes back to that address — no "latest", no overwrite path. |
| Lineage continuity by set-union (CLAUDE.md §7.2) | The merged lineage is asserted to be exactly `producer ∪ consumer` on both axes, with both sides contributing distinct members; replacement in either direction fails. |
| Admission only through L2 (single-writer, CLAUDE.md §10) | The graph digest moves only when `ingest_admitted` — typed to accept only gate-produced `AdmittedProduct` values — runs. No other write path exists to demonstrate. |
| The refusal path is real | A tampered envelope (a genuine signature spliced onto different payload bytes, over the real socket) is refused as a value, the refusal is audited, and the consumer's L3 substrate is byte-identical before and after. |
| Factory-only agent construction (CLAUDE.md §6.4) | The assembler is constructed by the Agent Factory from `artifacts/agent.yaml`; no agent exists in code in this directory. |
| No-Hardcoding (CLAUDE.md §6.4) | Every tenant, entity class, peer identity, ceiling, endpoint path and threshold lives in `artifacts/*.yaml`. Delete the artifacts and both drivers have nothing to run. |
