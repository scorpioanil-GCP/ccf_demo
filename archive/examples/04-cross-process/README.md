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

Domain rationale: **syndicated lending covenant cross-reference** is the
whitepaper's own canonical Pattern 4 exemplar (§8.3 Pattern 4, and the
Mode 3 assembly that composes against it at §7.6). A syndicated
facility's covenant package is partitioned across the parties to the
syndicate — the lead arranger holds the structuring covenants, the
administrative agent reconciles the borrower's periodic compliance
certificates, and each participant holds only the slice its
confidentiality envelope permits. No single party's fabric ingests the
full covenant graph in trust-clean form, so the boundary the product
crosses here is genuinely cross-organizational rather than merely
cross-process. That is exactly the trust boundary Pattern 4 names, and
it is why this is the example the suite re-domains to banking: the
scenario is drawn from the whitepaper rather than invented.

In this example the **producer is the lead arranger**
(`harborline-syndications`, peer `harborline-lead-arranger`) assembling
the covenant slice it is permitted to surface; the **consumer is a
participant bank** (peer `hollis-participant-bank`) admitting that
slice into its own fabric only after verifying the policy bindings it
carries. Every identity, identifier and value is obviously synthetic.

The rest of the suite keeps its horizontal domain mix (D-IMPL-52); only
this example moves.

## Run it

```sh
make example-04
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/04-cross-process/run.py
```

Exit code 0 means the spine ran, including the negative admission case.
The assertions live in `tests/examples/test_cross_process_output.py`,
under a runner that can fail a build (D-09):

```sh
PYTHONPATH=src:runtime python -m pytest tests/examples/test_cross_process_output.py
```

Keyless and model-free: signing keys are generated per run into a temp
directory and never committed; every identity and trust value in
`artifacts/producer-peering.yaml` and `artifacts/peering-trust.yaml` is
obviously synthetic; no model is called anywhere.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-04`, review the test output, then
> deliberately edit `artifacts/expected.yaml` to match what you
> reviewed — regeneration is a reviewed event, landed in the same
> commit as the enrichment, with the commit body summarizing what
> changed in the output and why. No `make regen-*` targets exist, and
> none will be added.

## Two deployments, two manifests

Producer and consumer are separate deployments with separate Control
Planes, separate graphs, and separate replay dimension 2. Each boots
from its own manifest — `artifacts/producer-manifest.yaml` and
`artifacts/consumer-manifest.yaml` — which is what D-06 means by the
artifact set in force being answerable from one document *per
deployment*.

Three of the consumer's documents are content-identical to a producer
document and are still separate files: `consumer-policy-bundle.yaml`,
`consumer-product-class.yaml`, and the ceiling in
`consumer-product-governance.yaml`. That is deliberate. Each states, on
the consumer's own authority, what it will admit; the agreement between
the two sides is what admission checks, and an agreement stated once
and read by both sides could not fail. Edit either alone and the
inbound product's asserted regime falls outside the consumer's
entitlement — admission refuses, which is the check working.

## The story

The producer child (`producer_child.py`) boots its own fabric from
`artifacts/producer-manifest.yaml` — its own SQLite file, its own
Control Plane, its own heap — factory-constructs the assembler agent
from `artifacts/agent-definition.yaml`,
ingests the events in `artifacts/events.yaml` (a facility asserted by
two source systems converging on one node; two covenant-relevant
compliance certificates the similarity operator must keep and one
insurance-evidence filing it must rank out; a restricted borrower
disclosure the policy operator must substitute out under the
syndicate's confidentiality envelope), and serves the gated
four-entity product on two ephemeral-port
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
   `artifacts/peering-trust.yaml` — peer ids, key id, permitted
   producer hash, permitted schema names, permitted policy regimes)
   and the Control Plane policy-binding checks. `gate.admit` returns a
   refusal *value* rather than raising, so the spine matches on the
   admitted case: a driver that ignored the result would proceed with
   nothing admitted. An immutable `AdmissionRecord` is persisted at an
   exact content address before anything is reported admitted. The
   merged lineage is asserted to be exactly `producer ∪ consumer` on
   both operator and policy axes — and both sides contribute operators
   the other lacks (see `artifacts/consumer-lineage.yaml`), so the
   union is evidence of set-union continuity, not of replacement in
   either direction. Only then does the admitted value pass through
   L2's typed federated door — the single writer — and the graph
   digest moves.
3. **The refusal path is real.** A tampered envelope — a genuine
   signature spliced onto different payload bytes, emitted over the
   real socket — is refused as a value (`SignatureRefusal` naming the
   peer), the refusal is audited, and the consumer's L3 substrate is
   byte-identical before and after. Unverified bindings never reach
   L3; the peer's say-so is not admission.

The federated entities resolve into the consumer's own declared
`syndicate_contribution` class rather than merging into its vocabulary
(see `artifacts/consumer-resolution-spec.yaml` and
`artifacts/federation-ingest.yaml`): a peer's claims are claims about
*another fabric's graph*, and merging them would assert the consumer
had independently observed them.

## Artifact-by-artifact

Every document below carries a `$schema` header naming the class that
validates it. SDK-owned classes point at their own committed schema;
deployment-authored ones point at the `DeclaredArtifact` envelope and
declare their own `class_id`.

**The producer's deployment** (`artifacts/producer-manifest.yaml`):

| Artifact | What it declares |
| --- | --- |
| `resolution-spec.yaml` | Four entity classes and three typed edges — resolution rules only |
| `policy-bundle.yaml` | The regime the fabric boots under and stamps onto every claim |
| `operator-parameters-{traversal,temporal,policy,similarity}.yaml` | The four operator parameter sets, each with the maps its own operator reads |
| `perspective.yaml` | The Π role-conditioning the product is served under |
| `product-class.yaml` | Schema name/version, TTL anchor, TTL key, and the declared `required_operator_keys` |
| `product-governance.yaml` | TTL ceiling, product TTL, similarity index version, plan id |
| `producer-peering.yaml` | Who this peer is on the wire and where it emits |
| `events.yaml` | The L1 signal batch: lineage pair, two kept certificates, one ranked-out filing, one restricted borrower disclosure |
| `decision.yaml`, `expected.yaml`, `agent-registration.yaml` | This run's instants, the declared expectation, and the two Control Plane keys — all `role: load` |
| `agent-policy-regime.yaml`, `agent-debt-profile.yaml` | The agent's axis-4 and axis-5 targets, registered under the keys its refs resolve to |

Two producer documents are **absent from the manifest on purpose**:
`agent-definition.yaml` and `prompt-artifact.yaml` are author-versioned
and register through `register_versioned`, whose D-05 bump check
`load_and_boot` does not run.

**The consumer's deployment** (`artifacts/consumer-manifest.yaml`):

| Artifact | What it declares |
| --- | --- |
| `consumer-resolution-spec.yaml` | The federation-ingress entity rule — a peer's entities land in their own class |
| `consumer-policy-bundle.yaml` | The regime the consumer entitles the producer to claim |
| `consumer-product-class.yaml` | The class the consumer will admit |
| `consumer-product-governance.yaml` | The consumer's own TTL ceiling |
| `peering-trust.yaml` | The trust-policy request: peer ids, key id, permitted producer hash, ceilings, receive path |
| `federation-ingest.yaml` | How an admitted product's payload becomes L1 signal |
| `consumer-decision.yaml`, `consumer-lineage.yaml` | The admission instant and the consumer's own lineage — both `role: load` |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §8.3 Pattern 3 — MCP integration (Context Product export)
- whitepaper §8.3 Pattern 4 — A2A federation and trust-boundary
  verification, and its **syndicated lending covenant cross-reference**
  Wholesale exemplar, which is this example's scenario
- whitepaper §7.6 Mode 3 — the assembly mode that consumes Pattern 4's
  federation surface across a structural trust-boundary partition
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
`artifacts/producer-peering.yaml` and `artifacts/peering-trust.yaml`:
change the peer ids, key id and producer hash to your own peer's
identity, and the ceilings (`inbound_payload_ceiling_bytes`,
`max_request_bytes`) and `receive_path` to your deployment's numbers
and URL space. The two documents state one federation relationship from
both sides — change them together, or admission will refuse. Then
rename the tenant in both manifests and swap the entity classes in
`artifacts/resolution-spec.yaml` and the payloads in
`artifacts/events.yaml`. On the next run, expect the served product and
the merged lineage to change — review the output and update
`artifacts/expected.yaml` in the same commit. Neither driver changes,
which is the point.

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
| Cross-deployment agreement is falsifiable | The consumer's policy bundle, product class and TTL ceiling are its own documents, not the producer's. Sharing one file would make the entitlement check pass for a reason unrelated to trust. |
| Factory-only agent construction (CLAUDE.md §6.4) | The assembler is constructed by the Agent Factory from `artifacts/agent-definition.yaml`; no agent exists in code in this directory. |
| No-Hardcoding (CLAUDE.md §6.4) | Every tenant, entity class, peer identity, ceiling, endpoint path and threshold lives in `artifacts/*.yaml`. Delete the artifacts and both drivers have nothing to run. |
