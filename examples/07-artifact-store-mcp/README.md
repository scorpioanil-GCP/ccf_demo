# examples/07-artifact-store-mcp — the ArtifactStore swap (EXAM-08)

Swap the file-backed `ArtifactStore` for the MCP-backed reference store;
**nothing else in the deployment changes**. This is the §9 charter's
pluggability proof for the ArtifactStore seam (CLAUDE.md §7.4), running one
fabric workload twice — once per store — and asserting the outputs are
identical.

Run it:

```
make example-07
```

(or `PYTHONPATH=src:runtime python examples/07-artifact-store-mcp/run.py`).
Exit 0 means every assertion held; any failure prints the store child's
captured stderr and exits nonzero.

## What this demonstrates

| Invariant | What would fail here |
| --- | --- |
| The store is a Protocol seam, not a code path (CLAUDE.md §7.4) | A workload that branched on backend — there is exactly one `workload()` function, called twice with only the store-config artifact name differing |
| The substrate is invisible to the fabric | The served Context Product's canonical bytes differing between the file run and the MCP run — asserted byte-for-byte |
| Artifacts are immutable and versioned, resolved to *exact* versions, never "latest" (§7.4, D-IMPL-26) | A URI recorded by the MCP run failing to resolve from a **fresh** client to its exact content address, or the bytes behind it differing |
| Store choice is configuration (CLAUDE.md §6.4) | A backend named anywhere but `artifacts/store_file.yaml` / `artifacts/store_mcp.yaml` — the driver holds a factory keyed by the artifact's declared `store.type`, and the endpoint/root are env-templated deployment values |
| The store is never a second writer (CLAUDE.md §7.4, §10) | Anything entering the graph through the store — the workload's single-writer boot check remains in force; the store persists products and replay records, and touches L3 never |
| The MCP reference server is authenticated by construction | The server child and the client factory reading *different* credential values — both interpret the same `store_mcp.yaml` auth block |
| No fixed ports, no sleeps | The child binds an ephemeral port and prints `READY {port}`; the parent then health-checks the store (up to 5 attempts, 1 s apart) before running the workload, so a child that never becomes healthy is a clear startup error, not a masked connection failure |

## Whitepaper and CLAUDE.md citations

* **CLAUDE.md §7.4** — the ArtifactStore Protocol, the MCP-backed reference
  implementation, immutability/exact-version resolution, and the
  never-a-second-writer constraint this example exercises end to end.
* **Whitepaper §8.3 Pattern 3** — MCP integration; here MCP is the artifact
  persistence transport (the SDK extension CLAUDE.md §7.1 names), distinct
  from the L6 egress role example 04 demonstrates.
* **CLAUDE.md §6.4** — the No-Hardcoding Rule: every domain value, store
  parameter and credential lives in `artifacts/*.yaml`; the code is an
  interpreter and a factory.

## Domain rationale (D-09)

The domain is **logistics** — a non-adjacent reuse of example 01's domain
family. The swap is the point and the domain is scenery: a store change
demonstrated on a domain-light workload keeps every eye on the one line
that differs, and all shipment/route/depot values live in artifacts, never
in example code.

## What to change first

`artifacts/store_mcp.yaml` — point `endpoint_env` (or replace the env
templating with your own endpoint value) at an artifact MCP server of your
own that implements the artifact resource contract, and supply your
deployment's credentials in the `auth` block. Nothing in `run.py` changes:
that is the §7.4 promise, and this example is its demonstration.
