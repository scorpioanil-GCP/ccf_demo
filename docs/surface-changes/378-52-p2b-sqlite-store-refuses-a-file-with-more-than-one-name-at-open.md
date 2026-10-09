# 378-52 — SEC-013, P2 (b): the SQLite store refuses a database file with more than one name when it opens, before any setup, readers included

`D-IMPL-378`, lane `378i-p2b`. Dave's list of 2026-10-09 06:06 MST, item 10, confirmed at 06:21 MST as "P1(a),
P2(b)", verbatim: *"Refuse undeclared identity-lock configuration; reject multi-name files before any setup writes,
including reader setup. Verify the identity lock still blocks the renamed-file second writer. Do not fall back silently
to the old path lock."* This entry is P2 (b) only. P1 (a), what a boot that declares no lock directory does, is
design-first and unchanged here. SEC-013's status is unchanged by this entry: its closure is Dave's to rule.

Measured before this entry, on the base `a539c215`: a second open through a hard link while a holder was live and had
committed (a writer, a writer declaring the lock directory, a read-only reader; each in another process) left `-wal`
and `-shm` beside the link before any refusal, the read-only reader was not refused at all, and once both had closed
and the file was opened through the link again, the holder's committed row was gone through both names with
`integrity_check` reporting `ok`. Red before and green after:
`tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py::test_a_second_open_through_a_hard_link_is_refused_before_it_writes_anything_and_the_holder_keeps_its_commit`
and the module's three single-process tests. The renamed-file second writer is still refused by the identity lock
(`tests/graph/test_sqlite_writer_lease_file_identity.py::test_a_second_process_is_refused_through_the_new_name_of_the_renamed_live_file`),
and a declared writer boot whose identity lock cannot be taken is refused rather than leased on the path lock alone
(`tests/graph/test_sqlite_declared_lock_never_falls_back_to_the_path_lock.py::test_a_declared_writer_boot_whose_identity_lock_cannot_be_taken_is_refused_and_never_falls_back_to_the_path_lock`,
which passes on the base too: the code did not fall back before this entry either). The security page states the
change in §4.6, including the N-6 statement.

## ccf.graph.backends.sqlite.SqliteGraphStore

- Surface: ccf.graph.backends.sqlite.SqliteGraphStore
- Public surface: true
- Change type: behavior
- Before: the store ran its setup (the write-ahead-log pragma and the schema) when it was opened, whatever the database file's number of names. A file with more than one name was refused only at the boot mint, after that setup had written: by `writer_lease()`'s name count (option (B)) or, with a lock directory declared, by the file lease (option (C)), reported as `SingleWriterViolation`. A read-only boot of such a file was not refused at all.
- After: the constructor counts the names of the regular file the path names before `sqlite3.connect` and again after it, before the setup's first statement, and refuses a file with more than one name with `WriterLeaseHeld`, whose message names the file and its number of names and says the store refuses to open it, readers included, before any connection or setup; a connection opened between the two counts is closed unused, and nothing is written through any name. A writer boot through such a file therefore raises `WriterLeaseHeld` from the store's open, before the mint, and so does a read-only boot. A path that names no file, `":memory:"` and `""` open as before. `writer_lease()`'s name count is unchanged and now refuses a second name made after the store opened.
- Why: SEC-013, P2 (b) (Dave, 2026-10-09): "reject multi-name files before any setup writes, including reader setup."
- Migration: every open of a SQLite database file that has more than one name, to write or to read, is refused until the other names are removed, so an examiner cannot open a file that has a hard-link backup; back the file up with a copy SQLite writes itself instead. A caller that caught `SingleWriterViolation` for a boot through a hard link catches `WriterLeaseHeld` instead. What the two counts do not see is stated on the class: a name made in the instant between the second count and the setup, a file swapped in under the path between SQLite's open and the second count, and an open made with SQLite directly.

## ccf.graph.protocols.WriterLeaseHeld

- Surface: ccf.graph.protocols.WriterLeaseHeld
- Public surface: true
- Change type: behavior
- Before: raised by a store's `writer_lease()` and translated by the boot mint into `SingleWriterViolation`.
- After: also raised by `ccf.graph.backends.sqlite.SqliteGraphStore`'s constructor for a database file with more than one name, for every open, readers included. That refusal comes before any lease and before the mint, so no mint translates it: `ccf.boot.boot` re-raises it unchanged for a writer boot and a read-only boot alike. The type is unchanged.
- Why: SEC-013, P2 (b): the refusal has to come before the store's setup writes, and the setup runs when the store opens.
- Migration: none beyond the store's entry above.

## ccf.boot.boot

- Surface: ccf.boot.boot
- Public surface: true
- Change type: behavior
- Before: the `read_only` argument's N-6 statement said a read-only boot still runs the store's own open-time setup, as a writer boot's open does.
- After: documentation only; the function re-raises what the adapter's store constructor raises, as before. The N-6 statement now adds that the SQLite store refuses a database file with more than one name before that setup, for a read-only boot as for a writer boot, with `WriterLeaseHeld`, so an examiner cannot open a SQLite file that has a hard-link backup.
- Why: the option ruled says it "changes N-6 for that case".
- Migration: none.
