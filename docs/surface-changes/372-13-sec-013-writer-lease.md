# 372-13 — SEC-013: the single-writer boot takes a writer lease that declares its scope

`D-IMPL-372` (and `D-IMPL-368`..`D-IMPL-371`), row SEC-013, ruling Q7 (a) as
refined in the row of
`docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md`. Measured
before this entry: the live-writer table `ccf.graph._writer._LIVE_WRITERS` is
module state, so two processes booting one SQLite file each minted a writer and
both booted through `ccf.boot.boot`. The exploit test is
`tests/graph/test_single_writer_across_processes.py`.

**SEC-013 is PARTIAL, not complete.** The SQLite and Postgres reference stores
now take a cross-process lease. The fluree, mongo and neo4j stores declare
`process` scope. That is a disclosure, not enforcement: the single-writer
invariant is NOT enforced across processes on those substrates, and the row
stays open for them. The memory store and the demo fixture also declare
`process` scope, which is exact there because no second process can reach
their graph.

## ccf.graph.protocols.WriterLease

- Surface: ccf.graph.protocols.WriterLease
- Public surface: true
- Change type: added
- Before: absent. Nothing represented a writer's hold on its graph beyond this process's live-writer table.
- After: a Protocol for a held writer lease. It has `scope` (a `WriterLeaseScope`), `mechanism` (the lease kind and resource, credential-free), an idempotent `release()`, and context-manager entry and exit.
- Why: SEC-013. The mint holds the lease for the writer's life and gives it back on `BaseGraphWriter.close` or on boot's failure path.
- Migration: none for a deployment. An adapter author returns one from `writer_lease()`.

## ccf.graph.protocols.WriterLeaseScope

- Surface: ccf.graph.protocols.WriterLeaseScope
- Public surface: true
- Change type: added
- Before: absent.
- After: `Literal["cross-process", "process"]`. `"cross-process"` means the substrate refuses a second holder in any process. `"process"` is a disclosure, not enforcement: the only exclusion is this process's live-writer table.
- Why: SEC-013. Each lease names its own scope, so nobody has to infer whether cross-process exclusion holds.
- Migration: none.

## ccf.graph.protocols.WRITER_LEASE_SCOPES

- Surface: ccf.graph.protocols.WRITER_LEASE_SCOPES
- Public surface: true
- Change type: added
- Before: absent.
- After: the two `WriterLeaseScope` values as a tuple. The mint refuses a lease that declares anything else, with a `TypeError`.
- Why: SEC-013. The vocabulary is closed and checked at the mint.
- Migration: none.

## ccf.graph.protocols.WriterLeaseHeld

- Surface: ccf.graph.protocols.WriterLeaseHeld
- Public surface: true
- Change type: added
- Before: absent.
- After: a `RuntimeError` a store's `writer_lease()` raises when another holder has the lease. The mint turns it into the same `SingleWriterViolation` ("already exists") that an in-process second boot raises, naming the lease it could not take.
- Why: SEC-013. A backend store may not import `ccf.graph._writer` (CINV-02), so the store needs its own type for refusing.
- Migration: none for a deployment. A deployment that catches `SingleWriterViolation` at boot now also sees the cross-process refusal there.

## ccf.graph.protocols.ProcessScopedWriterLease

- Surface: ccf.graph.protocols.ProcessScopedWriterLease
- Public surface: true
- Change type: added
- Before: absent.
- After: the `"process"`-scope lease, `ProcessScopedWriterLease(*, substrate)`. Acquiring and releasing it do nothing. The memory, fluree, mongo and neo4j reference stores and the demo fixture return it.
- Why: SEC-013. This is a disclosure, not enforcement. On the persistent network stores the single-writer invariant is NOT enforced across processes, and SEC-013 stays open for them. A native lease for mongo (a lease document under a unique index) and neo4j (a unique lock node) is an executor proposal, unapproved (SEC-013-P1). Fluree is append-only and has no native lock, so what the invariant means on a shared ledger needs a ruling.
- Migration: an out-of-tree adapter with no cross-process lock returns `ProcessScopedWriterLease(substrate="<adapter name>")` from `writer_lease()`.

## ccf.graph.registry.BackendStore

- Surface: ccf.graph.registry.BackendStore
- Public surface: true
- Change type: reshaped
- Before: three members, `graph_identity`, `reader` and `close()`.
- After: a fourth, required member, `writer_lease() -> WriterLease`. Only the boot mint calls it, after the in-process check passes and before a token exists. It is never called at store open, because a read-only store over a live graph is legitimate. The SQLite reference store's lease is an exclusive `fcntl.flock` (never `lockf`) on `<resolved database path>.ccf-writer.lock`, opened with mode `0o600`. The Postgres reference store's lease is a session `pg_try_advisory_lock(hashtextextended(current_schema(), 0))`, never the blocking form. Both are `"cross-process"`. A store without the member is refused at boot by name, with a `TypeError`.
- Why: SEC-013. The single-writer guard was process-local, so two processes over one SQLite file or one Postgres schema each booted a writer.
- Migration: every out-of-tree adapter must add `writer_lease()` (see `public/how-to/write-a-graph-backend-adapter.md`). After this change, two processes that each boot one SQLite or Postgres deployment, such as two in-process client adapters or two MCP egress servers on one deployment root, exclude each other, and the second boot is refused. The `public/how-to/security-and-deployment.md` section on processes sharing a graph discloses the per-store scope, the local-filesystem requirement for SQLite, and the session-pooling requirement and silent lease loss on a dropped connection for Postgres.

## ccf.graph._writer.mint_boot_token

- Surface: ccf.graph._writer.mint_boot_token
- Public surface: false
- Change type: reshaped
- Before: `mint_boot_token(*, graph_identity: str)`. It checked this process's live-writer table only.
- After: `mint_boot_token(*, store)`. It checks the live-writer table first, so the in-process refusal text is byte-identical to the old one. Then it acquires `store.writer_lease()`, records the lease beside the table, and records the lease scope on the token (`BootToken.lease_scope`). There is no parameter that skips the lease. `BaseGraphWriter.close` and `release_boot_token` drop the table entry first and then release the lease.
- Why: SEC-013. The lease is bound to the writer mint rather than to store open, and whether a lease applies is the store's declaration, never the caller's.
- Migration: none outside the SDK. The module is private, and `ccf.boot.boot` is its only caller.
