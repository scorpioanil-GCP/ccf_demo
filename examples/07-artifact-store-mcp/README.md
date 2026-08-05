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
Exit code 0 means the spine ran under both stores; any failure prints the
store child's captured stderr and exits nonzero.

The **assertions** live in `tests/examples/test_artifact_store_output.py`
and are run by `pytest` (D-09), because `make examples` proves a spine runs
and a test runner proves it is correct:

```
PYTHONPATH=src:runtime pytest tests/examples/test_artifact_store_output.py
```

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `pytest tests/examples/test_artifact_store_output.py`,
> review what it reports, then deliberately edit `artifacts/expected.yaml`
> to match what you reviewed — regeneration is a reviewed event, landed
> in the same commit as the enrichment, with the commit body summarizing
> what changed in the output and why. No `make regen-*` targets exist,
> and none will be added.

## The story

`run.py` holds exactly one `workload()` function and one store factory
keyed by the config artifact's declared `type` — the only place in the
file a backend is named. The workload is called twice, with only the
store-config artifact name differing; that is the structural form of
"nothing else in the deployment changes", and it is defended in three
ways rather than asserted:

1. `workload()` takes exactly **one** parameter, so there is nothing else
   that *could* vary between the two calls. A standing test reads the
   example's AST and refuses a second one.
2. Both runs boot from the **same** `artifacts/manifest.yaml`, named as a
   module constant rather than passed in — so there is no way for the two
   runs to load different Control Plane state, and a standing test
   compares the two runs' parsed artifact sets key for key.
3. The manifest names **no artifact store**. A substrate is a deployment
   environment choice, exactly as a database DSN is (D-08); one named in a
   registered, content-hashed artifact would land in replay dimension 2
   and would make the two runs genuinely differ in what was in force. A
   standing test walks the parsed manifest and refuses a store field under
   any spelling.

**The workload.** The fabric boots in one `load_and_boot` call from
`artifacts/manifest.yaml`, which enumerates the logistics vocabulary
(`resolution-spec.yaml` — shipments, routes, depots), the four operator
parameter documents, the policy bundle, the perspective, the product class
and its governance values; and it ingests the five L1 envelopes in
`artifacts/events.yaml`. The stream is small but not
flat: the same shipment arrives from two source systems (lineage
accumulates by set-union), a second shipment shares the rail route (real
multi-entity traversal), a sea route exists for the similarity operator
to rank out, and a `restricted` bonded depot exists for the policy
operator to withhold. The four-category operator chain and the
projection run with the parameters declared in the four
`artifacts/operator-parameters-*.yaml` documents, the product
passes the delivery gates, and the decision's five-dimension replay
record is built. Then the only store-touching lines execute: the replay
record, the served product, and the Control Plane policy bundle are
persisted through whichever store the config artifact declared.

**Run 1** uses `artifacts/store_file.yaml` (`type: file`, root templated
from an environment variable — no absolute path committed).

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
| `artifacts/manifest.yaml` | The one document naming every artifact in force, its Control Plane key, its class, and its `role` (D-IMPL-80) — **loaded unmodified by both runs**, and naming no store | `[ADAPT]`: keys, paths, deployment class ids. `[MECHANISM]`: field names, `ccf.`-prefixed class ids, `role` values |
| `artifacts/resolution-spec.yaml` | Entity classes, relationship types, resolution rules | `[ADAPT]`: all vocabulary. `[MECHANISM]`: rule field names (`match_key`, `identity_keys`, …) |
| `artifacts/events.yaml` | The five L1 signal envelopes the fabric ingests | `[ADAPT]`: payloads, sources, instants. `[MECHANISM]`: envelope field names |
| `artifacts/policy-bundle.yaml` | The policy bundle in force — also one of the three artifact classes persisted through the store seam | `[ADAPT]`: `class_id` and everything under `declaration:`. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/operator-parameters-*.yaml` | One document per operator category (traversal, temporal, policy, similarity), each carrying the attribute map its own operator reads | `[ADAPT]`: queries, thresholds, class and attribute names. `[MECHANISM]`: field names |
| `artifacts/perspective.yaml` | The Π role-conditioning the product is served under | `[ADAPT]`: principal id, role. `[MECHANISM]`: `principal_id`, `role` |
| `artifacts/product-class.yaml` | The served class, its TTL anchor, its MAX_TTL key, and `required_operator_keys` — the authored declared side of Gate 2 | `[ADAPT]`: names and operator keys. `[MECHANISM]`: field names and enum values |
| `artifacts/product-governance.yaml` | The TTL ceiling, the product TTL, the corpus version identity, the plan id, and the artifact classes/names the stores are told | `[ADAPT]`: every value. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/decision.yaml` | This run's instants — `role: load`, never in replay dimension 2, so both runs replay the identical decision | `[ADAPT]`: every value. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/expected.yaml` | What the served product should contain, and which artifact roles this deployment files through the store seam | `[ADAPT]`: every value. `[MECHANISM]`: `semver`, `class_id`, `declaration` |
| `artifacts/store_file.yaml` | The file-backed store selection and its env-templated root. **Not a manifest entry** — a substrate is an environment choice | `[ADAPT]`: `root_env` name. `[MECHANISM]`: `type` and its value vocabulary (`file`) |
| `artifacts/store_mcp.yaml` | The MCP-backed store selection, endpoint templating, and the auth block both sides interpret. **Not a manifest entry** | `[ADAPT]`: `endpoint_env`, the whole `auth` block (token, ids, URLs). `[MECHANISM]`: `type` (`mcp`) and the `auth` key names the server/client factories read |

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

Second: `artifacts/resolution-spec.yaml` + `artifacts/events.yaml` — your
own domain vocabulary and signal stream; then update
`artifacts/expected.yaml` (entity classes, relationship types,
`entity_count`) via the reviewed-regeneration workflow above. The artifact
classes and names your deployment files things under live in
`artifacts/product-governance.yaml`. Every document in force is enumerated
by `artifacts/manifest.yaml`, so a new artifact is not in force until it is
named there.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| The store is a Protocol seam, not a code path (CLAUDE.md §7.4) | A workload that branched on backend — there is exactly one `workload()` function, called twice with only the store-config artifact name differing |
| The substrate is invisible to the fabric | The served Context Product's canonical bytes differing between the file run and the MCP run — asserted byte-for-byte |
| Artifacts are immutable and versioned, resolved to *exact* versions, never "latest" (§7.4, D-IMPL-26) | A URI recorded by the MCP run failing to resolve from a **fresh** client to its exact content address, or the bytes behind it differing |
| The equivalence covers Control Plane bundles, not just outputs (§7.4 artifact classes) | The persisted policy bundle landing at a different URI or content address on either store — all three refs are asserted pairwise |
| Store choice is configuration (CLAUDE.md §6.4) | A backend named anywhere but `artifacts/store_file.yaml` / `artifacts/store_mcp.yaml` — the driver holds a factory keyed by the artifact's declared `type`, and the endpoint/root are env-templated deployment values |
| Store choice is a call-site binding, never Control Plane state (D-08) | A `store:` field appearing on `artifacts/manifest.yaml` — a substrate in a content-hashed artifact would land in replay dimension 2, and the two runs would then genuinely differ in what was in force |
| Nothing else could vary between the two runs | A second parameter on `workload()`, or the two runs booting from different manifests — both are asserted from the example's own source and from the two runs' parsed artifact sets |
| The store is never a second writer (CLAUDE.md §7.4, §10) | Anything entering the graph through the store — the workload's single-writer boot check remains in force; the store persists products, records and bundles, and touches L3 never |
| The MCP reference server is authenticated by construction | The server child and the client factory reading *different* credential values — both interpret the same `store_mcp.yaml` auth block |
| No fixed ports, no sleeps | The child binds an ephemeral port and prints `READY {port}`; the parent then health-checks the store (up to 5 attempts, 1 s apart) before running the workload, so a child that never becomes healthy is a clear startup error, not a masked connection failure |
