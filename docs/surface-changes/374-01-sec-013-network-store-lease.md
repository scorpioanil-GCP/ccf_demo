# 374-01 — SEC-013: a persistent network store mints a writer only under a declared, held lease

`D-IMPL-374` (1), ruling (a), on the batch-5 base (`D-IMPL-372`'s
`372-13-sec-013-writer-lease.md`). Measured before this entry: the fluree,
mongo and neo4j stores returned `ProcessScopedWriterLease`, so a second process
minted a writer for the same network graph (the hole as worded: the live-writer
table is process-local). The exploit tests are
`tests/graph/test_network_store_writer_lease.py`.

Now a persistent network store takes a deployment-declared lease and REFUSES to
mint without one (`WriterLeaseRequired`). The reference leases are the existing
lock-file lease (`ccf.graph.backends.sqlite.SqliteWriterLease`, any path the
deployment names) and the advisory-lock lease
(`ccf.graph.backends.postgres.PostgresWriterLease`, a session and a lease
schema the deployment names). The connection contracts carry the lock-file
lease only; the advisory-lock lease is declared through the store's
`writer_lease=` argument.

## ccf.graph.protocols.WriterLeaseSource

- Surface: ccf.graph.protocols.WriterLeaseSource
- Public surface: true
- Change type: added
- Before: absent.
- After: `Callable[[], WriterLease]`: a declared, not-yet-held writer lease. Calling it acquires the lease. A persistent network store calls it only from `writer_lease()`, which only the boot mint calls.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: none for a deployment that declares the lock-file lease through its connection settings; a deployment that wants another lease passes a `functools.partial` over a reference lease as `writer_lease=`.

## ccf.graph.protocols.WriterLeaseRequired

- Surface: ccf.graph.protocols.WriterLeaseRequired
- Public surface: true
- Change type: added
- Before: absent.
- After: a `RuntimeError` a persistent network store's `writer_lease()` raises when no lease was declared, or the declared lease's scope is not `"cross-process"`. It reaches the caller of `ccf.boot.boot` unchanged, before any token exists, so nothing is marked live and a corrected, leased retry boots. The message names the substrate and the credential-free graph identity and cites SEC-013 and D-IMPL-374.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment booting a network store declares a lease, or the boot is refused.

## ccf.graph.protocols.acquire_declared_writer_lease

- Surface: ccf.graph.protocols.acquire_declared_writer_lease
- Public surface: true
- Change type: added
- Before: absent.
- After: `acquire_declared_writer_lease(source, *, substrate, graph_identity) -> WriterLease`. Refuses with `WriterLeaseRequired` when `source` is `None`; lets `WriterLeaseHeld` propagate; releases and refuses a lease whose scope is not `"cross-process"`.
- Why: SEC-013. One implementation every network store delegates to, so the refusal cannot drift between adapters.
- Migration: none. An out-of-tree adapter over a store a second process can reach may delegate its `writer_lease()` to it.

## ccf.graph.backends.fluree.FlureeGraphStore

- Surface: ccf.graph.backends.fluree.FlureeGraphStore
- Public surface: true
- Change type: reshaped
- Before: `writer_lease()` returned `ProcessScopedWriterLease`, a disclosure that excluded nothing across processes.
- After: the constructor takes `writer_lease: WriterLeaseSource | None = None`, and `writer_lease()` acquires it through `acquire_declared_writer_lease`. With none declared the boot mint is refused with `WriterLeaseRequired`. The lease is never taken at open, so a read-only store needs none.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment that boots a writer over this store declares a lease (see the connection contract), or the boot is refused.

## ccf.graph.backends.mongo.MongoGraphStore

- Surface: ccf.graph.backends.mongo.MongoGraphStore
- Public surface: true
- Change type: reshaped
- Before: `writer_lease()` returned `ProcessScopedWriterLease`, a disclosure that excluded nothing across processes.
- After: the constructor takes `writer_lease: WriterLeaseSource | None = None`, and `writer_lease()` acquires it through `acquire_declared_writer_lease`. With none declared the boot mint is refused with `WriterLeaseRequired`. The lease is never taken at open, so a read-only store needs none.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment that boots a writer over this store declares a lease (see the connection contract), or the boot is refused.

## ccf.graph.backends.neo4j.Neo4jGraphStore

- Surface: ccf.graph.backends.neo4j.Neo4jGraphStore
- Public surface: true
- Change type: reshaped
- Before: `writer_lease()` returned `ProcessScopedWriterLease`, a disclosure that excluded nothing across processes.
- After: the constructor takes `writer_lease: WriterLeaseSource | None = None`, and `writer_lease()` acquires it through `acquire_declared_writer_lease`. With none declared the boot mint is refused with `WriterLeaseRequired`. The lease is never taken at open, so a read-only store needs none.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment that boots a writer over this store declares a lease (see the connection contract), or the boot is refused.

## ccf.graph.backends.fluree_write.FlureeConnection

- Surface: ccf.graph.backends.fluree_write.FlureeConnection
- Public surface: true
- Change type: reshaped
- Before: no lease setting.
- After: an optional `writer_lease_lock_file: str | None` (hash-transparent, so an omitted value hashes as before). When set it declares the reference lock-file lease (an exclusive `flock` on that file) as the graph's writer lease. Every process that may write the graph must name the same file on a filesystem they share with working `flock`.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: add `writer_lease_lock_file` to the connection settings of every deployment that boots a writer over this store. A deployment spread across hosts needs a shared lock service rather than a local file; it declares the advisory-lock lease through the store's `writer_lease=` argument.

## ccf.graph.backends.mongo_write.MongoConnection

- Surface: ccf.graph.backends.mongo_write.MongoConnection
- Public surface: true
- Change type: reshaped
- Before: no lease setting.
- After: an optional `writer_lease_lock_file: str | None` (hash-transparent, so an omitted value hashes as before). When set it declares the reference lock-file lease (an exclusive `flock` on that file) as the graph's writer lease. Every process that may write the graph must name the same file on a filesystem they share with working `flock`.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: add `writer_lease_lock_file` to the connection settings of every deployment that boots a writer over this store. A deployment spread across hosts needs a shared lock service rather than a local file; it declares the advisory-lock lease through the store's `writer_lease=` argument.

## ccf.graph.backends.neo4j_write.Neo4jConnection

- Surface: ccf.graph.backends.neo4j_write.Neo4jConnection
- Public surface: true
- Change type: reshaped
- Before: no lease setting.
- After: an optional `writer_lease_lock_file: str | None` (hash-transparent, so an omitted value hashes as before). When set it declares the reference lock-file lease (an exclusive `flock` on that file) as the graph's writer lease. Every process that may write the graph must name the same file on a filesystem they share with working `flock`.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: add `writer_lease_lock_file` to the connection settings of every deployment that boots a writer over this store. A deployment spread across hosts needs a shared lock service rather than a local file; it declares the advisory-lock lease through the store's `writer_lease=` argument.
