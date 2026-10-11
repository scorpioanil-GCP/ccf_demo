# Example amendments, 2026-10-11 — the SQLite identity lock (P1 (a))

Authority: Dave, 2026-10-11 14:51 MST (the Tuesday delivery GO): *"Compatibility repairs to example configuration,
clients, launchers and README commands are authorized, including previously frozen runnable specimens. Record the
amendment and preserve historical evidence. Do not weaken security assertions or change intended business results to
manufacture a pass."*

Cause: from the commit that made a SQLite file writer mint only under a declared identity lock
(`SqliteGraphStore.writer_lease`, P1 (a), `D-IMPL-378`), every direct SQLite boot that declared no lock directory is
refused `WriterLeaseRequired`. Examples that boot through the standard product boot (`open_product`, a
`ccf_environment.yaml`) need nothing: the SDK supplies its managed directory. Each example below booted SQLite
directly, so it now declares a private (`0o700`) per-run lock directory. No business result, threshold, query or
assertion changed. The history of each example before this amendment is in git, unchanged.

| Example | What changed |
| --- | --- |
| cp-00, cp-01, cp-02 | `backends.yaml` declares `writer_lease_lock_dir: {lock_directory: .ccf-writer-locks}`; `deployment.py::connection` composes it as a private directory under the run root. |
| cp-03, cp-04 | The same, as a new value source beside `from_env` and `per_run: path`. |
| cp-05 | The same, in `deployment.py::connection`. |
| cp-06 through cp-13 (cp-06, cp-07, cp-08, cp-09, cp-10, cp-11, cp-12, cp-13) | The same, in `deployment.py::connection`. |
| s1-01 | `artifacts/backends.yaml` declares `writer_lease_lock_dir: {per_run: lock_directory, filename: .ccf-writer-locks}`; `deployment.py::_per_run` interprets the new rule. |
| dr-01 | `replay.py` reopens the question's substrate with the product's own SDK-managed directory (`OpenedProduct.writer_lock_directory`). |
| hw1-companies-over-revenue | `deployment/binding.yaml` declares `writer_lease_lock_dir: {path: .ccf-writer-locks}`; `runner/seed.py` and `server/compose.py` create it; `.gitignore` lists it. |
| hw1-harness-clients | `runner/drive.py` creates the copied deployment's lock directory before seeding, and does not copy one. |

**Frozen specimens with a diff gate.** cp-03, cp-04, cp-05, cp-06 and cp-13 are pinned by `tests/examples/specimen_base.py`
gates that require no diff against the branch point (`CFC-G09` and its siblings). The gates are not disabled. They read
red on a branch carrying these amendments and read the specimen as untouched once the amendment is on `main`.
