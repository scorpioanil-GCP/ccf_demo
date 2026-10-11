# 378-43 — PROPOSAL, not ruled (option B): the SQLite writer lease refuses a database file with more than one name

`D-IMPL-378`, lane `378f-small2`, issue 2. **A proposal for Dave, not a ruled change.** The lane's brief said: key the
lease on the file's identity, or, if that is unsound on a platform the SDK supports, stop at a proposal. Locking the
database file itself is unsound: closing that descriptor drops the record locks SQLite holds in the same process
(measured on Linux, in the lane report). So the two commits that carry this are labeled `proposal(...)`, and they can
be dropped as a pair. SEC-013's status is unchanged.

`ccf.graph.backends.sqlite.SqliteGraphStore`'s `writer_lease()` takes the sidecar's `flock` as before, then counts the
database file's names (`st_nlink`). A file with more than one name is refused with `WriterLeaseHeld` ("the database
file ... has N names (hard links) ..."), through either name, and the boot's mint reports that as
`SingleWriterViolation`. Measured red before and green after by
`tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_cannot_boot_a_writer_through_a_hard_link_to_a_held_graph`
and `tests/graph/test_sqlite_writer_lease_hard_link.py::test_the_lease_refuses_a_database_file_with_a_second_name_through_either_name`.
**Not closed, and measured:** a live file moved to a new name keeps one name, so a writer booted through the new name
in a second process is not refused
(`tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_boots_a_writer_through_the_new_name_of_a_moved_live_file`).

## ccf.graph.backends.sqlite.SqliteGraphStore

- Surface: ccf.graph.backends.sqlite.SqliteGraphStore
- Public surface: true
- Change type: behavior
- Before: `writer_lease()` took the `flock` beside the resolved path and returned it, whatever other names the database file had, so a writer through a hard link took a different lock and was not refused.
- After: `writer_lease()` refuses a database file with more than one name (a hard link), through any of its names, with `WriterLeaseHeld`, after releasing the lock it took; a boot through either name is refused with `SingleWriterViolation`. A file with one name, and an in-memory database, are leased as before.
- Why: SEC-013 (CLAUDE.md §10): a lock beside one name cannot exclude a writer through another, and SQLite names its write-ahead log after the path too, so a second name reads another log and misses what the first committed.
- Migration: keep one name for a live database file. A hard link to it, including one a hard-link backup makes inside the same filesystem, refuses every writer boot until it is removed.
