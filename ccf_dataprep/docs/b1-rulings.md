# B1 execution rulings

Decisions taken during the execution of `docs/b1-portable-dump-plan.md`
(2026-08-27/28) without asking the user, and the findings deferred at close.

**Provenance, stated plainly.** These were recorded live in the execution
ledger at `.superpowers/sdd/b1-portable-dump-plan/progress.md`. That
directory is git-ignored scratch and **the controller deleted it at close**,
per the execution skill's instruction, before noticing that this repository's
own precedent — `docs/wave19-rulings.md` — is to preserve exactly this
material under `docs/`. The rulings below are reconstructed from the session
transcript and are believed complete, because each was reported to the user
as it was made. **The deferred-minor list is PARTIAL**: it is reconstructed
from the same transcript and some short entries may be missing. Where a
figure appears it was measured; where something is uncertain it says so.

Compare `docs/wave19-rulings.md`, which was preserved correctly and is the
model this file should have followed from the start.

---

## Rulings, in the order they were made

Each carries what it costs if wrong.

### C1 · `ccf_log` is deliberately defined twice

In both `portable/dump/common.sh` and `portable/restore/platform.sh`. Not
duplication to factor out: `platform.sh` ships inside the bundle to end users
and must not depend on a repo-side file.
**Cost if wrong:** two four-line functions drift; both only print.

### C2 · The laptop runs ONE Fluree server holding all three ledgers

Not two instances. Fluree ledgers are isolated namespaces and
`ccf/config.py::assert_distinct_fabrics` keys on ledger *name*, not server
URL, so its own guard still passes; the Postgres separation (`parkavedb` vs
`bofa_syndicated`) is preserved, and that is the boundary carrying real data.
**Cost if wrong:** the laptop demonstrates a namespace-level fabric boundary
rather than a network-level one — a fidelity loss for
`syndicated-lending-co-lender` demos, recoverable by running a second Fluree
on another port.

### C3 · The verifier asserts peer reachability and distinctness, not partition

It does not re-implement `validators/partition.py`'s 60 checks; that is a
wave of work, not an evening's.
**Cost if wrong:** a restored laptop could hold a partition violation the
verifier misses. Mitigated because the dump copies the estate verbatim, so
any violation predates the dump. **Caveat the final review added and it is
worth keeping:** the verifier's landmarks are counts, and a partial restore
that hits every count while dropping the wrong rows is exactly what counts
cannot see. Acceptable for one evening; not a permanent substitute.

### C4 · `verify_install.py` gains `CCF_SKIP_STORES`

The build-host rehearsal could not restore Neo4j (its Cypher opens
`MATCH (n) DETACH DELETE n` and the only Neo4j on the network is live), so
the rehearsal needed a way to exit 0 legitimately. Guarded against abuse:
skipped stores print loudly, and the verifier must NOT print "Estate
verified" when anything was skipped. Zero checks for any reason exits 1.
**Cost if wrong:** someone hides a real failure behind the flag. Mitigated by
the loud print, by the suppressed wording, and by the laptop run skipping
nothing. The final review confirmed the suppression is enforced in code
(`render_report`) and covered by tests asserting both wordings.

### C5 · Add `portable/__init__.py`

`from portable.manifest import ...` works as a namespace package only when
the repo root is on `sys.path`; an explicit package removes the dependence on
pytest's rootdir inference.
**Cost if wrong:** none, it is four bytes.

### C6 · The damage suite invokes the verifier with `uv run`, not bare `python3`

The verifier declares PEP 723 dependencies that bare `python3` lacks.
**Cost if wrong:** the damage suite fails on `ImportError` and that reads as a
successfully detected failure — a false green inside the tool built to
prevent false greens.

### C7 · `dump_all.sh` is the single entry point, re-run after `dump_sqlite.sh`

Rather than gaining a separate manifest command. It is already idempotent.
The SQLite artifact is absent on a first run by design.
**Cost if wrong:** a bundle shipped after one run has no SQLite entry —
caught by the expected artifact count.

### C8 · The peer Fluree export runs with `docker exec -w /var/lib/fluree`

The plan ran it as `sh -c 'cd /tmp && fluree export ...'`, which fails with
"no .fluree/ directory found": the container's project directory is its
WorkingDir `/var/lib/fluree`, bind-mounted from host `/data/fluree-demo`.
**Cost if wrong:** none; measured both ways. **This ruling later caused a
Critical** — see the note after C11.

### C9 · SQLite is 8 tables, not 5

The plan and `CLAUDE.md` both said 5; measured live it is 8
(`_schema_meta`, `covenant_tracker`, `large_exposure_limit_workbook`,
`prospect_note`, `restricted_list`, `risk_limit_workbook`,
`sar_classification`, `syndicate_desk_tracker`).
**Cost if wrong:** the verifier fails on a correct restore, on the laptop,
with no way to tell a stale landmark from a real defect — the worst failure
available to this deliverable.

### C10 · The Postgres version probe connects to `template1`, not `postgres`

Homebrew's `postgresql@16` on macOS creates a database named after the local
user and does not reliably create `postgres`. `template1` exists in every
PostgreSQL cluster by definition.
**Cost if wrong:** the restore aborts on the Mac at its first step with a
confusing "database postgres does not exist".

### C11 · The repo is not on db1, and `uv` is not installed there

db1 has bare `python3` 3.12.3 only. The plan's Task 4 guard and Task 8
orchestrator both read `/home/parkave/ccf_dataprep`, which does not exist
there. Resolution: every dump run rsyncs `portable/` to
`/data/laptop/.scripts/portable/` and defaults `REPO` to that;
`portable/manifest.py` is pure stdlib so bare python3 runs it;
`dump_neo4j.py` runs on the workstation because it needs the bolt driver;
`dump_all.sh` becomes a workstation-side orchestrator.
**Cost if wrong:** none — measured. Uncaught, Tasks 4 and 8 would each have
failed at first execution with an ImportError that looks like a code defect
rather than a missing checkout.

> **A ruling that caused a defect.** C8 fixed a peer-export command that could
> not run, but pointed it at the container's LIVE project directory, breaking
> the copy-first safety rule the same script states in its own comment and the
> primary path obeys. The task review caught it as Critical. Measured impact:
> with a 311-file baseline taken inside the container, `fluree export` leaves
> live peer storage byte-identical — no data was harmed. But the property held
> by accident of Fluree's implementation rather than by design. Fixed by
> copying inside the container first.

### C12 · The verifier is invoked as `uv run --no-project`

Bare `uv run` inside a directory containing a `pyproject.toml` adopts that
project's environment instead of resolving the script's inline dependencies.
**Cost if wrong:** ImportError on a correct restore — the same false-red class
as C9.

### C13 · Postgres table counts filter on `table_type='BASE TABLE'`

The plan's verifier counted `information_schema.tables` unfiltered and
asserted 113. Unfiltered the answer is **115** — `ccf_v2` also holds 2 views.
**Cost if wrong:** identical to C9, a red check on a correct restore.

### C14 · Task 9 stands up a throwaway Neo4j container

The plan said to SKIP the Neo4j restore in the rehearsal, leaving
`restore_neo4j.sh` the only restore path nothing had ever executed. Amended to
run it against a disposable container on non-default ports, then remove the
container, volume and image.
**Cost if wrong:** a ~600 MB image pull and ten minutes on a host with 1.7 TB
free. The final review called this the single best call in the ledger.

### Rulings on review findings

- **Task 1, reviewer warn "cannot verify TDD order":** not a gap. Whether tests
  were written before the code cannot be established from a diff.
- **Task 3, reviewer warn on a temp `.sql` file:** not a gap. The
  no-inline-ssh constraint protects repeatable shipped scripts; a file executed
  by path is the sanctioned workaround.
- **Task 3, Important UPHELD AND WIDENED:** the brief deferred restore
  verification to the verifier, but the verifier only connected to the primary
  DSN — so the peer Postgres restore was verified by nothing, anywhere. Fixed
  in both places.
- **Task 4, reviewer recommended deferring two Importants; OVERRIDDEN.** One was
  the estate's signature defect: on an idempotent re-run against a populated
  target, a missing dump directory was skipped silently and the count assertion
  then re-measured the stale data and PASSED. Fixed rather than deferred.
- **Task 6, out-of-scope residual FIXED rather than deferred:** `check_neo4j`
  still funnelled all queries through one handler reporting `unreachable`, the
  same defect just established as Critical elsewhere in the same file.
- **Task 9, sha256 claim asserted rather than shown:** required the paired
  digests be recorded, and had the implementer re-measure independently rather
  than transcribe supplied values.

### A standard the controller relaxed, recorded because it was enforced elsewhere

For Task 4 the controller required a bug be **reproduced before being fixed**,
then accepted a fix evidenced only by its corrected behaviour. Reasoning: the
re-review traced the old code's hole independently, and the new code was
observed hard-failing in the exact scenario on both a fresh and an
already-populated target. Reverting working code on shared infrastructure to
re-stage a fixed bug was judged the worse trade. The final review agreed and
named the closing move: **a unit test constructing a bundle directory with
`mongo-fibo_v2/` removed, asserting `restore_mongo.sh` exits 2.** That test
does not exist yet and would retire this asterisk.

---

## Deferred minors — PARTIAL, reconstructed

Thirteen were recorded; the following are those recoverable from the
transcript. Treat absence from this list as "possibly missed", not "none".

| Area | Finding |
|---|---|
| Task 1 | `ALLOWED_MONGO_DBS` is a second source of truth alongside `ccf/config.py`'s protected/writable sets (deliberately different scopes, but able to drift) |
| Task 1 | No automated coverage of `platform.sh`'s `ccf_need` / `ccf_sha256` / OS branch — and that file carries the entire macOS branch. The final review flagged this as the one worth closing: a ~20-line test under a faked `uname` |
| Task 2 | The peer scratch copy `/tmp/peerwork` is not cleaned if the export aborts mid-way; the next run's leading `rm -rf` clears it |
| Task 2 | A crash between `fluree init` and the marker write stamps a legitimate restore target as "foreign" forever — fail-safe, but strands the user |
| Task 5 | `dump_neo4j.py` does not escape a backtick inside a property key, label or relationship type, and Neo4j temporal/spatial/byte values fall through to `str()`. Verified non-triggering on the current 14-node graph; disclosed in the module docstring |
| Task 6 | Peer Postgres is neither checked nor reported unreachable when the primary DSN fails |
| Task 7 | A top-of-file comment named `resolve_hostport_or_refuse()`, a function that never existed — **fixed in the final wave** |
| Task 8 | `MANIFEST.json` covered only data artifacts, not scripts — **fixed in the final wave**, now 19 entries |
| Task 10 | `known-issues.md` §50 uses raw file counts rather than the "~1,421 generations" framing |
| Post-merge | Dev-side `portable/README.md` still says "11 artifacts total… reports 10" — stale now the manifest is 19. Not shipped in the bundle, so it cannot strand an operator |

## Defects found in this branch's own safety machinery

Kept because they are the most instructive part of the exercise. Every one was
found by review or by testing a guard, never by the code failing in use.

1. **A verifier that crashed rather than reported** on its most plausible input
   — a missing table. Only the initial connection was guarded; every later
   query was not, so `run_all` died before printing anything.
2. **A restore that passed on a restore that never ran.** With a missing dump
   directory and an already-populated target, the skip was silent and the count
   assertion re-measured stale data.
3. **A guard that inspected a proxy.** `damaged_restore.sh` validated
   `CCF_PG_DSN` while every destructive command targeted an unvalidated
   `CCF_B1CHK_PG_DBNAME` — a live route to `DROP TABLE` against production,
   with the verifier reading untouched scratch and reporting green.
4. **A denylist that failed open.** The same file blocked `:27017` literally;
   MongoDB defaults to 27017 when a URI omits the port.
5. **A guard that printed "REFUSED" and then proceeded.** `refuse()` calls
   `exit`, but was invoked inside a command substitution, where `exit` kills
   only the subshell. Found only because a later round added an
   unresolvable-hostname test.
6. **Tests that tested nothing** — constructing result objects with hand-copied
   literals instead of calling the code, twice, both times in tests written
   specifically to close a gap.
