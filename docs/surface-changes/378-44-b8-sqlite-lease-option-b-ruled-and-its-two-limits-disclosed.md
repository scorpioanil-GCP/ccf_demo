# 378-44 — option (B) for the SQLite writer lease, ruled, with its two limits disclosed: the rename gap and the hard-link backup restriction

`D-IMPL-378`, lane `378g-b8s9`, item 8 of the owed rulings. Dave ruled on 2026-10-08 at 21:24 MST (recorded on `main`
at `f84786b5`), verbatim: *"B now, with the rename gap and hard-link backup restriction explicitly disclosed. Keep the
affected SEC-013 closure open pending C; start C in parallel."* **SEC-013 stays OPEN.** Option (C), a lock keyed on the
database file's device and inode in a declared directory, is being built to close the rename gap. Nothing in this
entry closes a SEC row.

**Option (B) itself** is the behavior change entry `378-43-proposal-sqlite-lease-refuses-a-second-name` describes,
brought in unchanged (commits `19283e07` and `ba42fe9d`). That entry was written as a proposal; this is the ruling that
takes it. `ccf.graph.backends.sqlite.SqliteGraphStore`'s `writer_lease()` refuses a database file with more than one
name, through any of its names, with `WriterLeaseHeld`, and a boot through either name is refused with
`SingleWriterViolation`. Re-measured on this branch: red at `19283e07` (2 failed, 4 passed), green after the merge, and
the `names > 1` refusal severed turns both refusal tests red again.

**The two disclosures**, each in `ccf.graph.backends.sqlite.SqliteWriterLease`'s docstring, in `SqliteGraphStore`'s
`writer_lease` docstring, and on the security page, §4.6, and each measured by
`tests/graph/test_sqlite_writer_lease_disclosed_limits.py`, which skips nothing and marks nothing expected to fail:

1. **The rename gap: do not move a live database file.** A file moved to a new name while a writer holds it keeps one
   name, so (B) does not refuse it, and a writer booted through the new name in a second process is not refused while
   the first is live
   (`tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_boots_a_writer_through_the_new_name_of_a_moved_live_file`).
   SQLite leaves the live write-ahead log beside the old name, so the new name does not see what the writer committed.
   Once both names have been written through and closed, what was committed through the old name is gone, and SQLite's
   integrity check still reports `ok`
   (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_moved_live_file_leaves_its_write_ahead_log_behind_and_its_commits_are_lost`).
   What to do instead: stop every process that has the file open, then move it. A file moved while closed is one graph
   under its new name, and its lease refuses a second writer
   (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_database_file_moved_while_no_process_has_it_open_is_leased_under_its_new_name`).
2. **The hard-link backup restriction.** A backup that links the database file instead of copying it gives the file a
   second name. Until that name is removed, every writer boot of the graph, in any process and through either name, is
   refused with `SingleWriterViolation`, even with no writer live. The message opens "a GraphWriter already exists",
   although none is, and then names the file's two names
   (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_hard_link_backup_refuses_every_writer_boot_until_it_is_removed`).
   What to do instead: back the file up with a copy SQLite writes itself, its online backup API
   (`sqlite3.Connection.backup`) or `VACUUM INTO`. Either can run while a writer is live, and the database file keeps
   one name
   (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_copy_sqlite_makes_while_the_writer_is_live_leaves_the_file_one_name`).

Documentation only beyond the merge. The manifest `make surface` writes is unchanged, because it records signatures
rather than docstring text, and no signature changed. The behavior change itself is recorded once, in the `378-43`
proposal entry; the entry below records the disclosures, so that they reach the assembled log.

## ccf.graph.backends.sqlite.SqliteGraphStore

- Surface: ccf.graph.backends.sqlite.SqliteGraphStore
- Public surface: true
- Change type: behavior
- Before: the docstrings of `writer_lease` and of `SqliteWriterLease` stated option (B)'s refusal of a second name and noted that a live file moved to a new name escapes it, but neither said what the refusal costs a deployment that takes hard-link backups, what a move of a live file loses, or how to move or back up a database file safely.
- After: documentation only; the behavior is option (B)'s, unchanged. Both docstrings and the security page's §4.6 disclose the rename gap (a live database file moved to a new name escapes the lease; SQLite's write-ahead log stays beside the old name, so what was committed through it can be lost with no integrity error; stop every process that has the file open before moving it; `SEC-013` stays open pending option (C)) and the hard-link backup restriction (a hard link to the database file refuses every writer boot until it is removed, even with no writer live; back up with SQLite's online backup API or `VACUUM INTO` instead).
- Why: Dave's ruling on item 8 (`D-IMPL-378`, 2026-10-08 21:24 MST): "B now, with the rename gap and hard-link backup restriction explicitly disclosed."
- Migration: a deployment that backs up a SQLite graph by hard-linking its database file, or that moves a live database file, changes how it does both, as above.
