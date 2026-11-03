# Context Graph and Storage

**Primary package:** `ccf.graph`  
**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

## Core contracts

Public graph contracts include:

- `GraphReader`;
- `GraphWriter`;
- `GraphView`;
- `GraphQuery`;
- `EntityRecord`;
- `RelationshipRecord`;
- traversal/temporal types;
- source/store attestation;
- writer-lease protocols.

## Read/write asymmetry

The graph boundary is intentionally asymmetric:

- `GraphReader` is the normal read seam;
- `GraphWriter` is the single-writer seam minted by boot/assembly.

Projection receives a governed/read-only view. Product logic should not acquire its own graph writer.

## Reference backends

Current public adapters include SQLite, PostgreSQL, MongoDB, Neo4j, Fluree and in-memory implementations.

Specifications should name required capabilities/semantics, not depend on one backend's accidental behavior.

## Writer leases

Writer boot acquires the backend's writer lease before minting the writer.

| Store | Current exclusion mechanism | Deployment rule |
| --- | --- | --- |
| Memory | process scope | no cross-process shared store exists |
| PostgreSQL | session advisory lock | keep lease session alive and understand pool/session failure behavior |
| Fluree / MongoDB / Neo4j | declared cross-process lease | use one absolute/private shared `writer_lease_lock_dir` or explicit lease implementation |
| SQLite | path sidecar plus optional file-identity lease; multi-name open refusal | do not rename/live-hard-link DBs; declare the same private identity-lock directory for all writers |

A file lock is not a distributed lock service unless every writer reaches the same lock substrate.

## SQLite identity coordination

Current SQLite behavior is materially stronger than the Oct-9 design snapshot.

### Multi-name refusal at open

`SqliteGraphStore` refuses a regular database file with more than one filesystem name **before connecting/setup**, for readers and writers.

A hard-link backup therefore prevents the SDK from opening that file. Use a SQLite-safe copy/backup mechanism instead.

### Declared file-identity lease

`SqliteConnection.writer_lease_lock_dir` is optional.

When declared, the store derives a lease from the opened database file's device/inode and acquires it from the declared private directory in addition to the sidecar/path checks. A second writer reaching the same file through another name converges on the same identity lock **when both processes use the same directory**.

Limits remain:

- different/no lock directories do not coordinate through that identity lease;
- a live rename is not made safe and can strand WAL state;
- SQLite/direct filesystem access outside the SDK can bypass the mechanism;
- setup/open behavior and writer-leasing are distinct boundaries.

## Read-only boot

`boot(..., read_only=True)`, `load_and_boot(..., read_only=True)`, and `load_config_and_boot(..., read_only=True)` mint a governed reader without a writer.

Read-only does not mean "zero substrate setup" for every backend. SQLite's multi-name check runs before setup and applies to read-only opens too.

## Store creation/verification

The deployment store path also has a creation/verification protocol:

- a two-phase marker distinguishes pending from verified creation;
- failed boots remove the marker they own;
- a new store is checked before being marked verified;
- stale-marker/no-store cases are replaced and verified afresh;
- store creation is serialized by a separate creation lock.

`store_creation_lock_wait_seconds` is optional and has **no SDK default**:

- absent → a held creation lock refuses immediately with `DeploymentStoreNotVerified(reason="lock-held")`;
- present → the boot waits up to the declared positive number of seconds, then refuses if still held.

This is deployment-store coordination, not the graph writer lease itself.

## Classification authority

Classification used for access remains bound to the pinned resolution specification.

Boot mints the governed classification authority; raw/unstamped classification reads fail closed. Custom readers/operators that bypass the reference paths must preserve the same authority contract.

## Product-source graph integration

Governed Context Products can be used as declared product/source inputs where the architecture calls for it. Do not deserialize a product and treat it as ungoverned graph rows.

## Source vs fabric graph

The system of record is not automatically the Context Graph.

A common paved road is:

```text
source stores (read only)
        ↓ acquisition
SignalEnvelope
        ↓ L2
per-question / governed L3 fabric state
        ↓ operators
GraphView
        ↓ projection
Context Product
```

## Exact current shapes

Use the [Fabric API](api/fabric.md) and [Governance API](api/governance.md).

## Current Fluree pin and retained graphs

The SDK pins **`fluree/server:4.2.4`** in CI and checks that exact version in the differential leg. The relationship-property probe now receives HTTP 400 at Cypher lowering instead of null values; the adapter's interposed-node layout remains unchanged. Use an explicitly configured endpoint and port. Source: [CI pin](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/.github/workflows/ci.yml), [differential test](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/tests/graph/test_fluree_backend.py). Per-question replay graphs can now live under durable `evidence_root` and are hash-checked before read-only reconstruction; see [Decision Replay](DECISION_REPLAY.md).
