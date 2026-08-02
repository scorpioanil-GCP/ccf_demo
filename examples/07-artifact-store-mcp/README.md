# examples/07-artifact-store-mcp — swap the store, nothing else changes (EXAM-08)

## What this demonstrates

The **ArtifactStore** (the Protocol-based persistence surface for CCF
artifacts — snapshots, products at rest, replay records, Control Plane
bundles — with file-backed and MCP-backed reference implementations;
CLAUDE.md §7.4 — SDK extension) is a pluggable seam, and this example is
the §9 charter's proof of it: one fabric workload runs twice — once
against the file-backed store, once against the MCP-backed reference
store in a real subprocess — and every output is asserted identical.
**MCP integration** (Model Context Protocol as an integration surface —
Pattern 3 in the whitepaper; bidirectional (ingress and egress) in the
SDK; whitepaper §8.3 (Pattern 3); CLAUDE.md §7.1 (SDK extension:
bidirectional)) appears here in its *artifact persistence transport*
role, distinct from the L6 egress role example 04 demonstrates.

Three §7.4 artifact classes cross the store seam in each run — the
decision replay record, the **Context Product** (a typed, validated,
replay-ready unit of decision context the fabric derives and serves — a
contract, not a stored record; whitepaper §6.3 (specification), §7.6
(delivery)) at rest, and the **Control Plane** (the Control Plane
declares what the fabric may do (versioned config, policy, artifacts —
also the audit plane); the Data Plane executes within those constraints;
whitepaper §7.8) policy bundle that governed the decision. All three
land at the same versioned URIs and content addresses on both stores,
and every URI resolves from a *fresh* MCP client at its exact version —
never "latest".

## Run it

```
make example-07
```

Raw fallback: `PYTHONPATH=src:runtime python examples/07-artifact-store-mcp/run.py`.
Exit code 0 means every assertion held; any failure prints the store
child's captured stderr and exits nonzero.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-07`, review the assertion output, then
> deliberately edit the `expected:` block in `artifacts/controlplane.yaml`
> to match what you reviewed — regeneration is a reviewed event, landed
> in the same commit as the enrichment, with the commit body summarizing
> what changed in the output and why. No `make regen-*` targets exist,
> and none will be added.

## The story

`run.py` holds exactly one `workload()` function and one store factory
keyed by the config artifact's declared `store.type` — the only place in
the file a backend is named. The workload is called twice, with only the
store-config artifact name differing; that is the structural form of
"nothing else in the deployment changes".

**The workload.** The fabric boots from `artifacts/ontology.yaml`
(logistics vocabulary — shipments, routes, depots) and ingests the five
L1 envelopes in `artifacts/events.yaml`. The stream is small but not
flat: the same shipment arrives from two source systems (lineage
accumulates by set-union), a second shipment shares the rail route (real
multi-entity traversal), a sea route exists for the similarity operator
to rank out, and a `restricted` bonded depot exists for the policy
operator to withhold. The four-category operator chain and the
projection run with the parameters declared in
`artifacts/controlplane.yaml` (key `operator_parameters`), the product
passes the delivery gates, and the decision's five-dimension replay
record is built. Then the only store-touching lines execute: the replay
record, the served product, and the Control Plane policy bundle are
persisted through whichever store the config artifact declared.

**Run 1** uses `artifacts/store_file.yaml` (`store.type: file`, root
templated from an environment variable — no absolute path committed).

**Run 2** spawns `mcp_store_child.py` — a real authenticated MCP
artifact server on an ephemeral loopback port, announcing `READY {port}`
only when its server object reports started (no fixed ports, no sleeps);
the parent health-checks the store before running the identical workload
against `artifacts/store_mcp.yaml`. Both the server child and the client
factory read the *same* auth block from that artifact, so the credential
cannot drift into two values.

**The assertions.** (1) The served product's canonical bytes are
byte-identical across the two runs. (2) All three artifact refs match
pairwise — same versioned URIs, same content addresses — so the
equivalence covers a Control Plane bundle, not just decision outputs.
(3) Every URI the MCP run recorded resolves from a fresh client to its
exact content address, and the product fetched back over the wire is
byte-equal to the file run's.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/ontology.yaml` | Entity classes, relationship types, resolution rules, tenant, classification/corpus attribute maps | `[ADAPT]`: all vocabulary. `[MECHANISM]`: rule field names (`match_key`, `identity_keys`, …) |
| `artifacts/events.yaml` | The five L1 signal envelopes the fabric ingests | `[ADAPT]`: payloads, sources, instants. `[MECHANISM]`: envelope field names |
| `artifacts/controlplane.yaml` | Policy bundle, operator parameters, product class, artifact classes/names, decision instants, `expected:` block | `[ADAPT]`: every value, incl. `expected:` and the artifact-class names. `[MECHANISM]`: `keys`, `artifacts`, parameter key names |
| `artifacts/store_file.yaml` | The file-backed store selection and its env-templated root | `[ADAPT]`: `root_env` name. `[MECHANISM]`: `store.type` and its value vocabulary (`file`) |
| `artifacts/store_mcp.yaml` | The MCP-backed store selection, endpoint templating, and the auth block both sides interpret | `[ADAPT]`: `endpoint_env`, the whole `auth` block (token, ids, URLs). `[MECHANISM]`: `store.type` (`mcp`) and the `auth` key names the server/client factories read |

## Whitepaper / CLAUDE.md sections exercised

- CLAUDE.md §7.4 (ArtifactStore Protocol, MCP-backed reference
  implementation, immutability and exact-version resolution, the
  never-a-second-writer constraint) — SDK extension
- whitepaper §8.3 (Pattern 3 — MCP integration); CLAUDE.md §7.1 (the
  artifact-persistence MCP role, distinct from L6 egress) — SDK
  extension
- whitepaper §7.3–§7.6 (graph, operators, projection, gated product —
  the workload the two stores must serve identically)
- CLAUDE.md §6.4 (No-Hardcoding Rule — store choice, credentials, and
  every domain value live in `artifacts/*.yaml`; the code is an
  interpreter and a factory) — SDK extension
- CLAUDE.md §10 (single-writer invariant across the store boundary)

## What to change first

`artifacts/store_mcp.yaml` — point `endpoint_env` (or replace the env
templating with your own endpoint value) at an artifact MCP server of
your own that implements the artifact resource contract, and supply your
deployment's credentials in the `auth` block. Nothing in `run.py`
changes: that is the §7.4 promise, and this example is its
demonstration. On the next run, expect the same three URIs printed with
your server behind them, and the same byte-identical product.

Second: `artifacts/ontology.yaml` + `artifacts/events.yaml` — your own
domain vocabulary and signal stream; then update the `expected:` block
in `artifacts/controlplane.yaml` (entity classes, relationship types,
`entity_count`) via the reviewed-regeneration workflow above. The
artifact classes and names your deployment files things under live in
`artifacts/controlplane.yaml`, key `artifacts`.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| The store is a Protocol seam, not a code path (CLAUDE.md §7.4) | A workload that branched on backend — there is exactly one `workload()` function, called twice with only the store-config artifact name differing |
| The substrate is invisible to the fabric | The served Context Product's canonical bytes differing between the file run and the MCP run — asserted byte-for-byte |
| Artifacts are immutable and versioned, resolved to *exact* versions, never "latest" (§7.4, D-IMPL-26) | A URI recorded by the MCP run failing to resolve from a **fresh** client to its exact content address, or the bytes behind it differing |
| The equivalence covers Control Plane bundles, not just outputs (§7.4 artifact classes) | The persisted policy bundle landing at a different URI or content address on either store — all three refs are asserted pairwise |
| Store choice is configuration (CLAUDE.md §6.4) | A backend named anywhere but `artifacts/store_file.yaml` / `artifacts/store_mcp.yaml` — the driver holds a factory keyed by the artifact's declared `store.type`, and the endpoint/root are env-templated deployment values |
| The store is never a second writer (CLAUDE.md §7.4, §10) | Anything entering the graph through the store — the workload's single-writer boot check remains in force; the store persists products, records and bundles, and touches L3 never |
| The MCP reference server is authenticated by construction | The server child and the client factory reading *different* credential values — both interpret the same `store_mcp.yaml` auth block |
| No fixed ports, no sleeps | The child binds an ephemeral port and prints `READY {port}`; the parent then health-checks the store (up to 5 attempts, 1 s apart) before running the workload, so a child that never becomes healthy is a clear startup error, not a masked connection failure |
