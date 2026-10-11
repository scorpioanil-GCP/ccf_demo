# 378-45 — SEC-013 option (C): a declared lock directory makes the SQLite writer lease follow the database file

`D-IMPL-378`, lane `378g-c8`; Dave, 2026-10-08 21:24 MST: *"B now, with the rename gap and hard-link backup restriction
explicitly disclosed. Keep the affected SEC-013 closure open pending C; start C in parallel."* Option (C): a lock keyed
on the database file's device and inode in a declared directory, on the network stores' `writer_lease_lock_dir`
precedent. Option (B) is kept. SEC-013's status is unchanged by this entry: its closure is Dave's to rule.

Measured before this entry: while one process held the writer, a second process booted a writer through the new name
of the renamed live file (and, with (B), was refused through a hard link only by the name count). Red before and green
after: `tests/graph/test_sqlite_writer_lease_file_identity.py::test_a_second_process_is_refused_through_the_new_name_of_the_renamed_live_file`
and the hard-link test that entry `378-52` (P2 (b)) has since renamed
`tests/graph/test_sqlite_writer_lease_file_identity.py::test_a_second_process_through_a_hard_link_is_refused_when_its_store_opens_before_the_file_lease`,
because a hard link is now refused when the second process's store opens, before the file lease.
**What it does not close, measured** in `tests/graph/test_sqlite_writer_lease_file_identity_limits.py`: writers that
declare different directories, or none; a renamed live file's uncheckpointed commits, which SQLite strands under the
old name whatever any lock does; and the store's own setup, which runs at open, before the lease is taken at the mint,
so a process the lease refuses (or a read-only boot) through a hard link still leaves a log that later rolls back the
holder's committed data. The security page states these in §4.6.

## ccf.graph.backends.sqlite_write.SqliteConnection

- Surface: ccf.graph.backends.sqlite_write.SqliteConnection
- Public surface: true
- Change type: reshaped
- Before: one setting, `database_path`.
- After: an optional `writer_lease_lock_dir: AbsoluteLockDirectory | None` (hash-transparent, so a connection without it hashes as before), validated exactly as the network stores' setting: a relative path, a path through a symbolic link, a missing directory, one another user owns, or a group- or world-writable one is refused by name. When set, the boot hands the store the lock-directory lease over it; a read-only boot sets it aside unvalidated (N-2).
- Why: SEC-013, option (C). The sidecar lease is keyed on the resolved path, so a writer through another name of the same file, a hard link or the new name of a renamed live file, takes another lock.
- Migration: none required: a connection that declares no directory boots exactly as before (the sidecar and the name count; a renamed live file's new name is not excluded). To have the lease follow the file, declare the same absolute, private directory for every process that writes it.

## ccf.graph.backends.sqlite.SqliteGraphStore

- Surface: ccf.graph.backends.sqlite.SqliteGraphStore
- Public surface: true
- Change type: reshaped
- Before: `SqliteGraphStore(*, database_path)`; `writer_lease()` took the sidecar `flock` and refused a file with more than one name.
- After: `SqliteGraphStore(*, database_path, writer_lease: WriterLeaseSource | None = None)`. With a lease declared, the store reads the database file's device and inode right after SQLite opens it, and refuses with `ValueError` when there is no file (`":memory:"`, `""`); `writer_lease()` then takes the sidecar, the declared lease for that identity (through `acquire_declared_writer_lease`, so a lease that does not exclude other processes is refused with `WriterLeaseRequired`), and the name count, and returns both locks held together, its `mechanism` naming both. Another holder of the file's lease is refused with `WriterLeaseHeld` naming the file, its identity and the held lock, which the boot mint reports as `SingleWriterViolation`. Without `writer_lease=` nothing changes, the `mechanism` text included.
- Why: SEC-013, option (C): every name of one file has the same device and inode, so every writer of the file that declares the same directory asks for the same lock.
- Migration: none for a store built without `writer_lease=`. Never rename or move a live database file, and never open one through a second name, even read-only: neither is made safe by any lock.
