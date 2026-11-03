# Deployment and backend design

**SDK source:** `ccf_code/main@f07e558ed04c81154687d7efcc6312591e7f6f7d` · **Inspected:** 2026-10-09.

[Design index](README.md) · [Source inventory and verification scope](10_SOURCE_INVENTORY.md)

## Declaration, environment and composition

`ccf_config.yaml` states the product's semantic configuration: its class, request contract, operators, resolution rules, policy, debt/half-life declarations and supported bindings. `ccf_environment.yaml`, where the product uses the facade, describes environmental settings and source/endpoint references. The application supplies the domain callables and authority objects.

```mermaid
flowchart TD
    C["DeploymentConfig"] --> D["derive_deployment"]
    D --> M["DeploymentManifest and documents"]
    M --> L["load_and_boot"]
    CP["Control Plane registry"] --> L
    E["Connection and secret references"] --> L
    L --> B["boot"]
    B --> H["BootedFabric and FabricHandle"]
```

Derivation constructs documents; registration and validation belong to the loading/booting path. `load_config_and_boot` connects those operations. Explicit manifest entries enumerate the artifacts rather than finding them with a glob. The resulting pins say what configuration was actually bound.

A producer should not copy the SDK's config interpreter into its own `deployment.py`. That file should bind domain behavior and source settings. Conversely, a manifest or environment file cannot implement a bank-specific projection by itself.


Sources: [src/ccf/controlplane/artifacts.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/controlplane/artifacts.py); [src/ccf/deployment/config.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/deployment/config.py); [src/ccf/deployment/manifest.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/deployment/manifest.py); [src/ccf/deployment/environment.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/deployment/environment.py).

## Backend extension seam

```mermaid
classDiagram
    direction TB
    class BackendRegistration {
        +name
        +open_store
        +make_writer
    }
    class BackendStore {
        <<interface>>
        +graph_identity
        +reader
        +writer_lease()
        +close()
    }
    class GraphReader {
        <<interface>>
        +as_of()
        +query()
        +attestation
        +entity_history()
        +relationship_history()
    }
    class GraphWriter {
        <<interface>>
        +upsert_entity()
        +upsert_relationship()
        +close()
    }
    BackendRegistration --> BackendStore : open_store result
    BackendRegistration --> GraphWriter : make_writer result
    BackendStore --> GraphReader : supplies reader
```

The backend registry discovers declarations, resolves the requested backend, validates its connection settings and pins its identity/version. `boot` obtains the reader and the single-writer capability through that resolved registration. The registry is an extension seam; the diagram is not an inheritance tree of database adapters.

| Backend | Store | Reader | Implementation |
| --- | --- | --- | --- |
| memory | `MemoryGraphStore` | `MemoryGraphReader` | [memory.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/backends/memory.py) |
| sqlite | `SqliteGraphStore` | `SqliteGraphReader` | [sqlite.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/backends/sqlite.py) |
| postgres | `PostgresGraphStore` | `PostgresGraphReader` | [postgres.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/backends/postgres.py) |
| fluree | `FlureeGraphStore` | `FlureeGraphReader` | [fluree.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/backends/fluree.py) |
| mongo | `MongoGraphStore` | `MongoGraphReader` | [mongo.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/backends/mongo.py) |
| neo4j | `Neo4jGraphStore` | `Neo4jGraphReader` | [neo4j.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/backends/neo4j.py) |


Writer implementations live in the corresponding `*_write.py` modules. `SnapshotPinnable` is a separate capability; a shared read interface does not establish identical historical snapshot guarantees for every backend. Validate attestation, pin behavior and lease requirements for the selected adapter.


Sources: [src/ccf/graph/registry.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/registry.py); [src/ccf/graph/protocols.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/protocols.py); [src/ccf/boot.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/boot.py).

## Writer lifecycle

```mermaid
sequenceDiagram
    participant D as Deployment loader
    participant B as boot
    participant R as Backend registry
    participant S as Backend store
    participant W as Assembly worker
    D->>B: Pinned bindings and connection
    B->>R: Resolve registration and validate settings
    R-->>B: Registration and adapter pin
    B->>S: Connect
    alt Read-only boot
        B->>B: Build governed reader, no writable worker authority
        B-->>D: Read-only FabricHandle
    else Writer boot
        B->>S: Acquire declared writer lease
        B->>B: Mint boot token and create writer
        B->>W: Compose worker with writer
        B-->>D: FabricHandle with reader and worker
    end
    D->>B: Close handle when finished
    B->>S: Release owned resources
```

`FabricHandle` exposes ingestion through its worker, not a public graph writer handle. A read-only boot avoids a writer lease and uses a refusing write path. This is important for replay beside a live writer. Lease scope is explicit: process-local exclusion is not cross-process exclusion; a network deployment must supply the supported declared lease arrangement.

## Example distinction: source estate versus fabric

```mermaid
flowchart TD
    PG["Read-only PostgreSQL counterparty source"] --> A["CP01 acquisition and identity resolution"]
    A --> SE["SignalEnvelope values"]
    SE --> W["SDK worker"]
    W --> SQ["SQLite working fabric"]
    SQ --> P["Counterparty projection"]
    P --> O["Governed counterparty snapshot"]
```

CP01's `source_dsn` and `connection` deliberately read different bindings. A change to the upstream reference database is not the same operation as replacing SQLite with another fabric backend. Network addresses and credentials remain deployment settings and are not copied into these documents.


Sources: [examples/cp-01-counterparty-reference-snapshot/deployment.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/examples/cp-01-counterparty-reference-snapshot/deployment.py); [examples/cp-01-counterparty-reference-snapshot/produce.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/examples/cp-01-counterparty-reference-snapshot/produce.py); [src/ccf/graph/leases.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/graph/leases.py); [src/ccf/boot.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/boot.py).
