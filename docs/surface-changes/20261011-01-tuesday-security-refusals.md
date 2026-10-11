# 20261011-01 — the Tuesday security refusals: the SQLite identity lock, unsupported approval-queue sharing, and typed registration over an untyped version

Dave, 2026-10-11 14:51 MST (the Tuesday delivery GO, item 4), verbatim: *"Approval: implement the refusal of
unsupported queue/store sharing; prove a permitted approval still completes exactly once; state the scope
precisely."* *"SQLite: require the existing identity lock AND wire the standard product boot to supply the agreed
lock directory. Do not ship a refusal that breaks the ordinary product path. Reuse the existing design and
prototype; the one-file restriction is withdrawn."* *"D-IMPL-381: implement the already-selected refusal before class
binding or registration state changes. No replacement semantics or broader registry redesign."* Each change was
built red test first, with a severing. **SEC-001, SEC-013 and SEC-020 stay OPEN**; nothing here closes a SEC row.

## ccf.graph.backends.sqlite.SqliteGraphStore

- Surface: ccf.graph.backends.sqlite.SqliteGraphStore
- Public surface: true
- Change type: behavior
- Before: a file database with no declared writer lease minted a writer under the path-only sidecar lock, which a writer reaching the same live file through a new name (a rename) escaped.
- After: `writer_lease()` on a file database with no declared lease raises `WriterLeaseRequired` from `acquire_declared_writer_lease`, the same refusal every network store gives; there is no fallback to the sidecar. An in-memory database keeps its process-scoped declaration. A declared lease is unchanged: the sidecar, then the identity lock, then the name count.
- Why: P1 (a) (`D-IMPL-378`, Dave 2026-10-09 06:06 and 06:21; the Tuesday GO item 4). Design: `records/2026-10-09-d-impl-378-designs/designs/gamma/DESIGN-P1a-sqlite-identity-lock.md` on `dl-378-record`. Red test: `tests/graph/test_sqlite_writer_requires_identity_lock.py`.
- Migration: every direct SQLite writer boot (`boot`, `load_and_boot`, `load_config_and_boot`, the in-process adapter, a hand-built `SqliteGraphStore`) declares `writer_lease_lock_dir` in its connection settings, or `writer_lease=` on the store: an absolute, private (mode `0o700`) directory every writer of that file shares. The standard product boot (`open_product`) needs nothing; it supplies the directory itself.

## ccf.graph.leases.LOCK_DIRECTORY_SETTING

- Surface: ccf.graph.leases.LOCK_DIRECTORY_SETTING
- Public surface: true
- Change type: added
- Before: absent; the setting's name was the private `_LOCK_DIRECTORY_SETTING`, which is kept as its alias.
- After: the public name of the lock-directory connection setting, `"writer_lease_lock_dir"`.
- Why: the standard product boot and deployments name the setting without reaching into a private constant.
- Migration: none.

## ccf.graph.leases.SDK_MANAGED_LOCK_DIRECTORY

- Surface: ccf.graph.leases.SDK_MANAGED_LOCK_DIRECTORY
- Public surface: true
- Change type: added
- Before: absent.
- After: `".ccf-writer-locks"`, the directory under a deployment's scratch root where the standard product boot keeps its identity locks.
- Why: P1 (a), design §6.2.
- Migration: none.

## ccf.graph.leases.sdk_managed_lock_directory

- Surface: ccf.graph.leases.sdk_managed_lock_directory
- Public surface: true
- Change type: added
- Before: absent.
- After: returns `<base>/.ccf-writer-locks`, creating it with mode `0o700` if absent. It refuses with `WriterLeaseRequired`, naming the setting to declare instead, when `base` is not an absolute real path, when the filesystem holding it is not a local one whose `flock` the SDK trusts (ext2, ext3, ext4, xfs, btrfs, tmpfs, f2fs, zfs, read from `/proc/self/mountinfo`; anything else, and a platform without it, is refused), or when an existing directory is not private to this user. An existing directory is judged, never re-moded.
- Why: P1 (a), design §6.2: every process that boots through one scratch root takes the same identity lock for one database file, whatever name it reached the file by.
- Migration: none.

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: behavior
- Before: the per-question boot handed the adapter only the minted substrate path, so its SQLite writer took the path-only sidecar lock.
- After: when the declared adapter's connection contract takes `writer_lease_lock_dir`, the product computes the SDK-managed lock directory under its scratch root once, at open (`writer_lock_directory`), so an unusable one refuses before any question; every per-question boot declares it. An adapter without the setting gets nothing.
- Why: P1 (a) and the Tuesday GO: *"Do not ship a refusal that breaks the ordinary product path."*
- Migration: none for the standard product boot. A scratch root on a network or overlay filesystem is now refused at open; put scratch on a local filesystem.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: the engine refused a shared state store paired with a non-shared HITL transport, but admitted a shared transport beside a process-scoped store, and one process-scoped transport serving several independent store objects. Each was measured to let one approval release an execution twice (`DESIGN-2b-store-identity.md` §2, probes `p_b09` and `p2b_restart`).
- After: both are refused at construction with `WorkflowWiringError`. A process-scoped transport is bound to the first process-scoped store object it is built with, for the life of the process, and a different store object is refused even after the first is gone. Rebuilding an engine over the same store and transport is admitted, as are replicas whose shared transport serves shared store views. A permitted approval still runs the step after the gate exactly once (`tests/workflow/test_engine_refuses_unsupported_sharing.py`). **Scope:** this check sees one Python process. Independent shared stores behind one shared queue in different processes are not detected; the controlled bank configuration excludes them (one engine, state store and approval queue per instance).
- Why: the Tuesday GO item 4.
- Migration: build every engine over one transport with the same state store, or give each store its own transport. A shared transport needs a shared store.

## ccf.controlplane.registry.ControlPlaneRegistry

- Surface: ccf.controlplane.registry.ControlPlaneRegistry
- Public surface: true
- Change type: behavior
- Before: `register_typed` and `register_versioned`, finding the content hash already stored by the untyped `register` door, took the idempotent path, bound the class to the key and left the stored mapping, so `resolve` served a `dict` under a class-bound key (`D-IMPL-381`).
- After: both raise `TypeError` before validation, class binding, bump or audit state changes. Nothing is replaced. A typed idempotent re-registration is unchanged.
- Why: `D-IMPL-381`, the refusal Dave selected; the Tuesday GO item 4. Red test: `tests/controlplane/test_registry_refuses_typed_over_untyped.py`.
- Migration: register a key through one door: typed from the start, or untyped throughout.
