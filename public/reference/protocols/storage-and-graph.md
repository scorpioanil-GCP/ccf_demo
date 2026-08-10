# Storage and Context Graph Protocols

The Context Graph is reached through two deliberately asymmetric surfaces. `GraphReader` is
handed out freely; `GraphWriter` is the single-writer seam, and only the Context Assembly layer
ever holds one. The Control Plane surfaces sit beside them because graph state is only
interpretable under a pinned Control Plane resolution.

::: ccf.graph.protocols.GraphReader

::: ccf.graph.protocols.GraphWriter

::: ccf.controlplane.state.ControlPlaneStateStore

::: ccf.controlplane.registry.ControlPlaneProtocol

## The query seam

`GraphReader.query()` takes one frozen `GraphQuery` and returns one `GraphView`. Tenant
scope and the as-of instant travel *inside* the `GraphQuery`, so no answerer reads a clock
and none takes tenant as a separate argument.

What a `GraphQuery` **means** is defined normatively in `docs/GRAPH_QUERY_SEMANTICS.md`, whose
clauses carry `GQ-NN` ids. That document is the authority: the reference implementation in
`ccf.graph.fallback` implements it, adapters agree with it under the differential
conformance suite, and semantic changes arrive as versioned amendments rather than as silent
drift. The clauses are not restated here — cite them, do not paraphrase them.

Two properties are worth stating on this page because they shape every implementation:

- **There is no capability negotiation and no refusal path.** A conformant answerer answers
  any well-formed query, degrading internally to scan-and-filter where it holds no native
  translation. An empty answer is a legitimate value, never an error.
- **The content hash of each issued query is the per-round-trip replay pin**, recorded in
  execution order — what ran, never what the plan predicted. The canonical query bytes land
  in the ArtifactStore keyed by those hashes, so an auditor resolves the literal question
  asked without re-running anything. That is why the query value is frozen and carries no
  version field of its own.

::: ccf.graph.protocols.GraphQuery

::: ccf.graph.protocols.GraphView

## The adapter registry

Which substrate sits behind the graph is a **name a deployment writes down**, resolved at
boot. The registry is that resolution, and it is the seam a graph backend adapter attaches
to — including an adapter shipped as a separate installable distribution.

Two discovery sources feed one name set. Adapters the SDK ships are found by reading module
names off the adapter package's directory — a disk read, never an import, and no packaging
metadata is involved. Adapters from elsewhere are found through the `ccf.graph_backends`
entry-point group. `declared_names()` unions the two and imports nothing; `resolve()` imports
exactly one adapter, the one that was named.

`declared_names()` is fail-closed: a duplicated, reserved or malformed name declared by any
installed distribution refuses the whole call rather than just the offending name, because an
environment whose answer to "which code does this name select" is ambiguous has not earned a
boot. The same names are readable at runtime — `ccf backends list` travels `GET /backends`,
which returns the sorted names, or a `503` carrying the registry's own refusal when the
installed adapters conflict.

The six adapters this SDK ships:

| Name | Config model | Config fields | Credential fields |
| --- | --- | --- | --- |
| `sqlite` | `SqliteConnection` | `database_path` | — |
| `memory` | `MemoryConnection` | *(none)* | — |
| `postgres` | `PostgresConnection` | `dsn`, `schema_name` | — |
| `neo4j` | `Neo4jConnection` | `uri`, `partition` | — |
| `mongo` | `MongoConnection` | `uri`, `partition` | — |
| `fluree` | `FlureeConnection` | `url`, `partition` | `bearer_token` |

Writing a seventh is [a how-to](../../how-to/write-a-graph-backend-adapter.md), and the
manifest side — how a deployment names the adapter and supplies its settings — is on
[the deployment manifest](../artifacts/deployment-manifest.md).

::: ccf.graph.registry.BackendRegistration

::: ccf.graph.registry.BackendStore

::: ccf.graph.registry.declared_names

::: ccf.graph.registry.resolve

::: ccf.graph.registry.ResolvedBackend

::: ccf.graph.registry.validate_connection

::: ccf.graph.registry.ResolvedSecret

::: ccf.graph.registry.AdapterPin
