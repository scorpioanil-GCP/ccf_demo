# 374-01 — SEC-013: a persistent network store mints a writer only under a declared, held lease

`D-IMPL-374` (1), ruling (a), on the batch-5 base (`D-IMPL-372`'s
`372-13-sec-013-writer-lease.md`), as amended by fix round 1. Measured before
this entry: the fluree, mongo and neo4j stores returned
`ProcessScopedWriterLease`, so a second process minted a writer for the same
network graph (the hole as worded: the live-writer table is process-local).
The exploit tests are `tests/graph/test_network_store_writer_lease.py`.

Now a persistent network store takes a deployment-declared lease and REFUSES to
mint without one (`WriterLeaseRequired`). Through connection settings a
deployment declares an ABSOLUTE lock directory (`writer_lease_lock_dir`); the
SDK derives the lock file `<dir>/<sha256(graph identity)>.lock` and holds an
exclusive `flock` on it. **A file lease excludes only writers that share that
filesystem with real `flock` semantics. Across hosts it enforces nothing,
unless the directory is on a shared filesystem whose locks work across hosts,
and two writers that declare different directories are not excluded.** The
reference advisory-lock lease (`ccf.graph.backends.postgres.PostgresWriterLease`,
a session and a lease schema the deployment names) is reachable only by
constructing the store directly with `writer_lease=`: the connection contracts
carry no credential by environment name, so `ccf.boot.boot` cannot declare it.

**Declare one spelling of the server address across every writer of a graph**
(the final fix wave, FW-4). The lock file is derived from the graph identity,
which is the server address as spelled (host and port, with letter case and an
omitted default port normalized) plus the ledger or database and the
partition: `http://localhost:8090` and `http://127.0.0.1:8090` give one Fluree
ledger two lock files and two writers, and the same holds for a hostname
against its IP address on MongoDB and Neo4j, for a MongoDB host list in another
order or a `mongodb+srv://` seed name against its expanded list, and for two
routing addresses of one Neo4j cluster. Normalizing the spelling is carried,
not built. A MongoDB host list with a port on any host but the last (the usual
replica-set form) does not parse as an identity, and the store refuses it with
a `ValueError` at construction — measured, pre-existing, carried.

**The declared directory is its own real path, private to the writers' user**
(the final fix wave, PC3; panel C3). The directory was resolved at each
acquisition, so a symbolic link retargeted between two writers' acquisitions
gave one graph two lock files and both writers minted. Connection validation
now refuses a directory reached through a link (naming the real path to
declare), a missing or non-directory path, one not owned by the effective user,
and one that is group- or world-writable; direct construction refuses the link
and every acquisition re-checks it. The entries are in
`374-05-final-fix-wave.md`.

## ccf.graph.protocols.WriterLeaseSource

- Surface: ccf.graph.protocols.WriterLeaseSource
- Public surface: true
- Change type: added
- Before: absent.
- After: `Callable[[str], WriterLease]`: a declared, not-yet-held writer lease. A persistent network store calls it with its own credential-free graph identity, only from `writer_lease()`, which only the boot mint calls.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: none for a deployment that declares `writer_lease_lock_dir`. A deployment that wants another lease passes a callable taking the identity as the store's `writer_lease=`.

## ccf.graph.protocols.WriterLeaseRequired

- Surface: ccf.graph.protocols.WriterLeaseRequired
- Public surface: true
- Change type: added
- Before: absent.
- After: a `RuntimeError` a persistent network store's `writer_lease()` raises, on the boot mint (`ccf.graph._writer.mint_boot_token`), when no lease was declared or the declared lease's scope is not `"cross-process"`. It reaches the caller of `ccf.boot.boot` unchanged, before any token exists, so nothing is marked live and a corrected, leased retry boots. The message names the substrate and the credential-free graph identity and cites SEC-013 and D-IMPL-374.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment booting a network store declares a lease, or the boot is refused.

## ccf.graph.protocols.acquire_declared_writer_lease

- Surface: ccf.graph.protocols.acquire_declared_writer_lease
- Public surface: true
- Change type: added
- Before: absent.
- After: `acquire_declared_writer_lease(source, *, substrate, graph_identity) -> WriterLease`. Refuses with `WriterLeaseRequired` when `source` is `None`; calls `source(graph_identity)`; lets `WriterLeaseHeld` propagate; releases and refuses a lease whose scope is not `"cross-process"`.
- Why: SEC-013. One implementation every network store delegates to, so the refusal cannot drift between adapters.
- Migration: none. An out-of-tree adapter over a store a second process can reach may delegate its `writer_lease()` to it.

## ccf.graph.leases.LockFileWriterLease

- Surface: ccf.graph.leases.LockFileWriterLease
- Public surface: true
- Change type: added
- Before: absent; the module is new.
- After: `LockFileWriterLease(*, path)`: an exclusive non-blocking `flock` on `path`, opened `O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW` with mode `0o600`, scope `"cross-process"`, `mechanism` `flock on '<path>'`. A held lock, a file this user cannot open, or a file another user owns refuses as `WriterLeaseHeld`; a symbolic link at the path is refused by name (`RuntimeError`), never followed.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: none.

## ccf.graph.leases.lock_directory_writer_lease

- Surface: ccf.graph.leases.lock_directory_writer_lease
- Public surface: true
- Change type: added
- Before: absent; the module is new.
- After: `lock_directory_writer_lease(lock_dir) -> WriterLeaseSource`: refuses a relative `lock_dir` (`ValueError`); the source acquires `LockFileWriterLease` on `<resolved lock_dir>/<lock_file_name(identity)>`.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: none.

## ccf.graph.leases.declared_lock_directory_lease

- Surface: ccf.graph.leases.declared_lock_directory_lease
- Public surface: true
- Change type: added
- Before: absent; the module is new.
- After: `declared_lock_directory_lease(lock_dir: str | None) -> WriterLeaseSource | None`: the one helper every network adapter's `_open_store` calls with its `writer_lease_lock_dir` setting.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: none.

## ccf.graph.leases.lock_file_name

- Surface: ccf.graph.leases.lock_file_name
- Public surface: true
- Change type: added
- Before: absent; the module is new.
- After: `lock_file_name(graph_identity) -> str`: the SHA-256 hex of the identity plus `LOCK_FILE_SUFFIX`.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: none.

## ccf.graph.leases.LOCK_FILE_SUFFIX

- Surface: ccf.graph.leases.LOCK_FILE_SUFFIX
- Public surface: true
- Change type: added
- Before: absent; the module is new.
- After: `".lock"`.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: none.

## ccf.graph.leases.require_absolute_lock_directory

- Surface: ccf.graph.leases.require_absolute_lock_directory
- Public surface: true
- Change type: added
- Before: absent; the module is new.
- After: `require_absolute_lock_directory(value) -> str`: returns an absolute path, refuses a relative one by name (`ValueError`, naming `writer_lease_lock_dir`).
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: none.

## ccf.graph.leases.AbsoluteLockDirectory

- Surface: ccf.graph.leases.AbsoluteLockDirectory
- Public surface: true
- Change type: added
- Before: absent; the module is new.
- After: `Annotated[str, AfterValidator(require_absolute_lock_directory)]`, the connection-settings type of `writer_lease_lock_dir`.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: none.

## ccf.graph.backends.fluree.FlureeGraphStore

- Surface: ccf.graph.backends.fluree.FlureeGraphStore
- Public surface: true
- Change type: reshaped
- Before: `writer_lease()` returned `ProcessScopedWriterLease`, a disclosure that excluded nothing across processes.
- After: the constructor takes `writer_lease: WriterLeaseSource | None = None`, and `writer_lease()` acquires it through `acquire_declared_writer_lease` with the store's graph identity. With none declared the boot mint is refused with `WriterLeaseRequired`. The lease is never taken at open, so a read-only store needs none.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment that boots a writer over this store declares `writer_lease_lock_dir` in its connection settings, or passes `writer_lease=` when constructing the store directly; otherwise the boot is refused.

## ccf.graph.backends.mongo.MongoGraphStore

- Surface: ccf.graph.backends.mongo.MongoGraphStore
- Public surface: true
- Change type: reshaped
- Before: `writer_lease()` returned `ProcessScopedWriterLease`, a disclosure that excluded nothing across processes.
- After: the constructor takes `writer_lease: WriterLeaseSource | None = None`, and `writer_lease()` acquires it through `acquire_declared_writer_lease` with the store's graph identity. With none declared the boot mint is refused with `WriterLeaseRequired`. The lease is never taken at open, so a read-only store needs none.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment that boots a writer over this store declares `writer_lease_lock_dir` in its connection settings, or passes `writer_lease=` when constructing the store directly; otherwise the boot is refused.

## ccf.graph.backends.neo4j.Neo4jGraphStore

- Surface: ccf.graph.backends.neo4j.Neo4jGraphStore
- Public surface: true
- Change type: reshaped
- Before: `writer_lease()` returned `ProcessScopedWriterLease`, a disclosure that excluded nothing across processes.
- After: the constructor takes `writer_lease: WriterLeaseSource | None = None`, and `writer_lease()` acquires it through `acquire_declared_writer_lease` with the store's graph identity. With none declared the boot mint is refused with `WriterLeaseRequired`. The lease is never taken at open, so a read-only store needs none.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: a deployment that boots a writer over this store declares `writer_lease_lock_dir` in its connection settings, or passes `writer_lease=` when constructing the store directly; otherwise the boot is refused.

## ccf.graph.backends.fluree_write.FlureeConnection

- Surface: ccf.graph.backends.fluree_write.FlureeConnection
- Public surface: true
- Change type: reshaped
- Before: no lease setting.
- After: an optional `writer_lease_lock_dir: AbsoluteLockDirectory | None` (hash-transparent, so an omitted value hashes as before). A relative path is refused at validation, by name. When set, the store's lease is the lock-directory lease over it: the file is `<dir>/<sha256(graph identity)>.lock`, derived, never chosen.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: add `writer_lease_lock_dir` (absolute) to the connection settings of every deployment that boots a writer over this store, the same directory for every process that may write the graph. Across hosts this excludes nothing unless the directory is a shared, lock-capable filesystem.

## ccf.graph.backends.mongo_write.MongoConnection

- Surface: ccf.graph.backends.mongo_write.MongoConnection
- Public surface: true
- Change type: reshaped
- Before: no lease setting.
- After: an optional `writer_lease_lock_dir: AbsoluteLockDirectory | None` (hash-transparent, so an omitted value hashes as before). A relative path is refused at validation, by name. When set, the store's lease is the lock-directory lease over it: the file is `<dir>/<sha256(graph identity)>.lock`, derived, never chosen.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: add `writer_lease_lock_dir` (absolute) to the connection settings of every deployment that boots a writer over this store, the same directory for every process that may write the graph. Across hosts this excludes nothing unless the directory is a shared, lock-capable filesystem.

## ccf.graph.backends.neo4j_write.Neo4jConnection

- Surface: ccf.graph.backends.neo4j_write.Neo4jConnection
- Public surface: true
- Change type: reshaped
- Before: no lease setting.
- After: an optional `writer_lease_lock_dir: AbsoluteLockDirectory | None` (hash-transparent, so an omitted value hashes as before). A relative path is refused at validation, by name. When set, the store's lease is the lock-directory lease over it: the file is `<dir>/<sha256(graph identity)>.lock`, derived, never chosen.
- Why: SEC-013, `D-IMPL-374` (1), fix round 1. The lease file is derived from the graph identity by mechanism, never chosen by the deployment, so two writers of one graph that declare one directory always contend for one file.
- Migration: add `writer_lease_lock_dir` (absolute) to the connection settings of every deployment that boots a writer over this store, the same directory for every process that may write the graph. Across hosts this excludes nothing unless the directory is a shared, lock-capable filesystem.

## ccf.boot.FabricHandle

- Surface: ccf.boot.FabricHandle
- Public surface: true
- Change type: reshaped
- Before: no report of the writer lease in force; `BootToken.lease_scope` had no reader (SEC-013-C-03).
- After: two attributes read off the boot token at boot, `lease_scope` (`"cross-process"` or `"process"`) and `lease_mechanism` (the lease kind and resource, credential-free), both keyword arguments defaulting to `None`. Deliberately not part of `adapter`, so the replay pin is unchanged.
- Why: SEC-013-C-03. The lease the writer holds is now readable by the deployment that booted it.
- Migration: none.

## ccf.graph._writer.BootToken

- Surface: ccf.graph._writer.BootToken
- Public surface: false
- Change type: reshaped
- Before: the token recorded `lease_scope` only.
- After: the token also records `lease_mechanism`, the held lease's `mechanism`, at the mint. `ccf.boot.boot` copies both onto `FabricHandle`.
- Why: SEC-013-C-03.
- Migration: none. The module is private.

## ccf.graph._writer.mint_boot_token

- Surface: ccf.graph._writer.mint_boot_token
- Public surface: false
- Change type: behavior
- Before: a network store's `writer_lease()` returned the `"process"` disclosure, so the mint always succeeded past the in-process table.
- After: the mint's lease acquisition now raises `WriterLeaseRequired` from a persistent network store with no held cross-process lease declared, before any token exists, and records the lease's `mechanism` on the token.
- Why: SEC-013, `D-IMPL-374` (1). A second process could reach the graph, so the `"process"` disclosure excluded nothing across processes.
- Migration: none outside the SDK.
