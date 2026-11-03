# Fluree 4.2 migration — design

**Status:** steps 0–5 complete 2026-10-15 — migrated, battery green, cut over
as Repoint (post-cutover suite 856/856), bundle rebuilt from 4.2 and
from-scratch Ubuntu restore validated (verifier 20/20, damage suite 4/4
named failures, baseline green; live estate untouched). The macOS half of
B2 remains open, as before.
**Origin:** Dave's request, 2026-10-13 — upgrade Fluree to 4.2 with the same
data, no data change, without disrupting the current implementation.
**2026-10-15:** Dave confirmed "latest 4.2.x" as the target — that is 4.2.4,
which went stable 2026-10-14. Dave also confirmed the bofa/syndicate peer
represents another bank's data estate, so it migrates as its own fabric.

## Spec review, 2026-10-15

Reviewed the 4.2.x release notes (GitHub `fluree/db` releases, per-version
notes for 4.2.1–4.2.4). Findings the plan builds on:

1. **4.2.4 is stable** (2026-10-14), resolving this doc's "avoid 4.2.4-beta"
   caveat. A 5.0.0-alpha.1 pre-release exists — do **not** float to `latest`.
2. **4.1.x → 4.2 archive compatibility is undocumented** in any release note
   consulted. The step-1 spike remains the central unknown, exactly as placed.
3. **Typed ledger IDs (4.2.2, #1958)** — "parse ledger ids once at the edge and
   key everything by a typed id". The notes carry no statement about hyphen
   or slash names (`fibo-v2`, `bofa/syndicate`), so the ledger-name check
   stays first in the battery.
4. **Time-pinned reads (4.2.2)** — `@time:` is the canonical selector
   (`@iso:` an alias), a time pin is accepted in the `/query` ledger path, and
   `at: 'time:'` branches from a point in time. This gives the §51 as-of
   re-test a concrete API surface instead of a hope.
5. **Index storage growth is fixed in 4.2.4** (#2018 stats-sketch GC, disk
   cache, blob drop; #2020 sparse binary + zstd sketches, 15-minute GC
   default). Not needed for the migration — import rebuilds one fresh index —
   but it strengthens the deferred B1 reclaim case on the live host.
6. **xsd:integer preservation (#2012) and xsd:double indexability (#2044)**
   landed in 4.2.4; nothing mentions `xsd:date`. The §19.4 typed-date re-test
   stays, and the estate's all-strings discipline stays either way.
7. **Peer container runs image tag `fluree/server:latest`** (currently
   4.1.6). The 4.2 peer must be created with a **pinned** tag
   (`fluree/server:4.2.4`), never `latest`.

Live estate measurements taken during the review (primary :8090 4.1.4; peer
:8091 container):

| Ledger | Fabric | t (2026-10-15) | Notes |
|---|---|---|---|
| `fibo-v2` | primary | 6,065 | triples 89,148 (landmark, known-issues §58 for `t`) |
| `fibo` | primary | 5 | v1 |
| `bofa/syndicate` | peer | 16 | the other bank's estate |
| `ccf` | primary | 1,608 (+ cp04-* branches) | **ccf-sdk's fixture ledger, not one of our three.** Lives on the same host binary and project; cutover scope for it is open — the Repoint option leaves 4.1.4 serving it untouched. |

The §5.1 hazard (explicit `FROM` required) reproduces live on 4.1.4 today —
a count query without `FROM` returns
`Missing dataset specification in SPARQL connection query (no FROM / FROM NAMED)`.

## Goal

Move both Fluree fabrics from 4.1.x to 4.2.x with **zero data change**, so that
after cutover the ledgers hold exactly the triples and commit history they hold
today. The current estate must keep serving until the new install is fully
verified, so the migration runs **side-by-side and cuts over last**.

This is the Fluree-upgrade slice only. The FIBO starter pack, FRED/other new
data, and any new engineered data are the v3-estate work this may later feed
into, and are **out of scope** here (see "Out of scope").

## Current state (as of 2026-10-13)

| Fabric | Binary | Where | Ledgers |
|---|---|---|---|
| Primary (db1 host) | **4.1.4** | `/home/parkave/bin/fluree`, storage `/data/fluree` | `fibo-v2` (v2), `fibo` (v1, untouched) |
| Co-lender peer | **4.1.6** | docker container `fluree-demo`, project bind-mounted from `/data/fluree-demo` | `bofa/syndicate` |

Note: "currently using 4.1.6" is true of the peer container only; the primary
host binary is 4.1.4. The migration upgrades **both**.

Measured facts the plan builds on:

- `fibo-v2` holds **89,148 triples**; `/data/fluree/fibo-v2` is ~47 GB, almost
  all of it ~1,421 accumulated index generations (`reindex_min_bytes = 100`,
  recorded in the B1 design, not acted on).
- `portable/dump/dump_fluree.sh` already exports all three ledgers as
  `.flpack` (`fluree export --format ledger`) plus a commit-count sidecar
  (`.ledger-t.json`), from **copies** of live storage, never the live path.
- `fluree export` announces its archive **on stderr**; the sidecar parser
  treats an unparseable announcement as fatal.
- 4.1.4 archives import cleanly into 4.1.6 (verified 2026-08-27).
  **4.1.x → 4.2 has never been exercised.**
- All 27,607 literals in `fibo-v2` are plain strings; `dump_fluree.py` exits
  non-zero if a typed literal ever enters the ledger (the §19.4 guard).

## Decisions taken

| Question | Ruling | Who |
|---|---|---|
| Migration path | Export → fresh 4.2 install → import; **not** an in-place binary swap | Dave, 2026-10-13 outline |
| Isolation | 4.2 runs alongside; live 4.1.x untouched until cutover | Dave |
| Data change | None — import only; no new loads, no re-generations | Dave |
| Target version | **4.2.4 stable** (2026-10-14) — pinned, never a floating tag; confirmed by Dave 2026-10-15 | spec review 2026-10-15 |
| Cutover | Only after the full verification battery passes; cutover itself is Dave's call | Dave, 2026-10-13 outline |

Why export→import over an in-place swap: `.flpack` restore is Fluree's
documented portability path — content-addressed, per-frame hash-verified,
atomic rollback on failure — and an in-place swap would let a changed on-disk
format touch the authoritative ledgers on the first run, which is exactly the
irreversible risk the B1 work was built to avoid.

## Steps

### 0 · Snapshot (rollback insurance, already scripted)

Run `portable/dump/dump_fluree.sh` against the live estate. This produces the
three `.flpack` archives and the commit-count sidecar the verification battery
asserts against. Timing note: the repo's validator suite advances `fibo-v2`'s
`t` by ~46 per run while triples stay fixed (known-issues §58), so the sidecar
— not any hardcoded number — is the source of truth, and the snapshot should be
taken at a quiet moment.

### 1 · First spike: does a 4.1.x `.flpack` import into 4.2?

Before any other work: install the 4.2 binary in a scratch project, import
`fibo-v2.flpack`, count triples. This is the central unknown. If it fails, the
fallback is a two-hop import (4.1.x pack → 4.1.6 intermediate → re-export →
4.2) or Fluree's own migration guidance, and the plan changes materially —
which is why it is step 1 and not a footnote.

### 2 · Install 4.2 alongside

- Primary: 4.2 binary at a new path (e.g. `/home/parkave/bin/fluree-42`),
  serving on a **new port**, pointed at a fresh project directory. The live
  4.1.4 on :8090 keeps running untouched.
- Peer: a new container from the 4.2 image (e.g. `fluree-demo-42`), also on a
  new port. `fluree-demo` (4.1.6) keeps running.

Nothing in the estate repoints until step 4.

### 3 · Import and verify

Import all three ledgers from the `.flpack`s into the 4.2 instances
(`fluree create <name> --from <pack>`; rename-on-restore is supported).

**Ledger-name check first:** names in play are `fibo-v2` (hyphen), `fibo`
(plain), and `bofa/syndicate` (slash). 4.2.2 shipped a breaking
"typed ledger IDs" change — confirm each name parses and restores to the exact
same ID before trusting anything else.

Verification battery, in order:

1. **Counts.** `fibo-v2` triples = 89,148; commit counts match the sidecar for
   all three ledgers; co-lender and v1 `fibo` counts match.
2. **Validator suite.** Full pytest run (`uv run --with pytest pytest`) with
   env vars pointed at the 4.2 instances. Read the summary line —
   `| tail` returns tail's exit code. Expect ~787 pass. The suite will add
   its ~46 commits to the 4.2 copy of `fibo-v2`; that is expected, not drift.
3. **Hazard re-tests** — each a named check with a known-present expectation:
   - **§5.1 SPARQL endpoint forms** — explicit `FROM` requirement, update
     endpoint + `Fluree-Ledger` header. If 4.2 changed the API surface, the
     loaders and validators say so here.
   - **§19.4 typed-date corruption** — insert a typed `xsd:date`, read it
     back. 4.2.3 shipped "typed literal preservation fixes," so this is
     plausibly fixed, but treat it as unknown until measured. Either way the
     estate's all-strings discipline and the `dump_fluree.py` guard stay.
   - **§51 as-of queries** — on 4.1.4/4.1.6, `/v1/fluree/history` 404s and the
     JSON-LD `t` parameter is silently ignored. 4.2 advertises time-pinned
     reads; test whether an as-of query now returns the true historical
     answer. If yes, this is a **capability gain**, not just a hazard
     removal, and it should be recorded in `docs/ccf_dataprep_v2.md`.
   - **Export announcement parse** — take one fresh export from 4.2 and
     confirm `record_ledger_t` still reads the commit count. 4.2.1 changed
     export's default output (faithful round-trip, RDF 1.2 edge annotations);
     the parser fails loudly by design, but the fix belongs in this wave.
4. **Reindex note** — 4.2.3 says ledgers with typed literals may need
   reindexing. We hold zero typed literals (guarded), so expect N/A; verify
   the typed-literal count is still 0 rather than assuming.

### 4 · Cutover (Dave's go/no-go)

With the battery green, choose one:

- **Repoint:** set `FLUREE_URL` / `CO_LENDER_FLUREE_URL` to the 4.2 instances
  and leave 4.1.x running as an instant-rollback fallback. Simplest; the
  stores' connection config is env-var driven (`ccf/config.py`).
- **Replace:** stop 4.1.x, move the 4.2 instances to the canonical ports/paths.

Either way, the 4.1.x storage directories and the pre-migration `.flpack`
snapshots are retained until the post-cutover bundle validates.

### 5 · Post-cutover: rebuild the bundle from 4.2

`dump_fluree.sh` runs against the 4.2 estate, producing a **new-format**
bundle. `MANIFEST.json` is rebuilt, and a from-scratch restore validation is
run (Ubuntu proven path; the macOS half of B2 remains open as before).

## Step 3 results, 2026-10-15 (recorded as run)

**Import spike (step 1) — PASSED.** A 4.1.4 `.flpack` imports directly into
4.2.4: `fibo-v2` → 6,065 commits, 101 index artifacts, **89,148 triples,
exact landmark match**. `fibo` (5 commits) and `bofa/syndicate` (16 commits,
slash name included) import and address identically. No two-hop fallback
needed.

**Side-by-side install (step 2) — DONE.** Live estate untouched throughout
(4.1.4 :8090 and 4.1.6 :8091 still serving; `t` and ledgers unchanged).

| Instance | Version | Address | Ledgers |
|---|---|---|---|
| 4.2 primary | 4.2.4 host binary `~/bin/fluree-42` | `192.168.4.76:8092` | `fibo-v2`, `fibo` |
| 4.2 peer | `fluree/server:4.2.4` (pinned) container `fluree-demo-42` | `192.168.4.76:8093` | `bofa/syndicate` |
| 4.2 scratch | 4.2.4 CLI project `/home/parkave/mig42/spike42` (moved out of the bundle root 2026-10-15 — scratch must not inflate `/data/laptop`, which `du -shL` bills to the bundle) | local only | spike copies |

4.2 storage layout: project at `~/fluree-42/project` (primary) and
`~/fluree-42/peer` (peer, bind-mounted at `/var/lib/fluree`). Both moved to
`/data/fluree-42/{storage,peer}` on 2026-10-15 — see Step 7.

**Verification battery (step 3):**

1. **Counts — PASS.** `fibo-v2` 89,148 triples; t values match the snapshot
   sidecar (6,065 / 5 / 16) as imported.
2. **Validator suite — PASS: 856/856, 0 failed** (exit 0, 2m55s), run with
   `FLUREE_URL=http://192.168.4.76:8092` and
   `CO_LENDER_FLUREE_URL=http://192.168.4.76:8093`. Post-suite state: 4.2
   `fibo-v2` at t=6,111 (+46, exactly the §58 prediction), triples still
   89,148; peer `bofa/syndicate` 10 triples, identical to live. The live
   4.1.4 instance was untouched by the run (t=6,065 before and after).
3. **Hazard re-tests:**
   - **§5.1 SPARQL endpoint forms — UNCHANGED.** An explicit `FROM` is still
     required on `/v1/fluree/query`; the same 500 error text returns. Loaders
     and validators need no change.
   - **§19.4 typed-date corruption — FIXED in 4.2.4.** Three `xsd:date`
     values inserted into a scratch ledger round-tripped exactly (on 4.1.4
     every one returned a wrong date). Plain strings still bind without a
     `datatype` field, so the `dump_fluree.py` guard's logic still holds.
     The estate's all-strings discipline stays anyway — no data change this
     wave — but the hazard is no longer prospective on 4.2.
   - **§51 as-of queries — CAPABILITY GAIN.** `fluree query --at t:1`
     returns the true historical value (impossible on 4.1.x, where `t` was
     silently ignored). Caveat: on the legacy `/v1/fluree/*` HTTP surface the
     time pin is still silently ignored (`Fluree-Ledger: <name>@time:1`,
     `?at=t:1`), and the 4.2.2 `/query/<ledger>` ledger-path form 404s on the
     default server config. The working path observed was the CLI routing
     through the 4.2 server. **ccf-sdk follow-up:** pin the supported HTTP
     form before building on as-of reads.
   - **Export announcement parse — UNCHANGED.** `fluree export --format
     ledger` announces `(N commits, … txn blobs, … index artifacts)` on
     stderr exactly as 4.1.4 did; `record_ledger_t` parses it unchanged. The
     4.2.1 "export default output" change did not touch this path.
4. **Typed-literal count — 0** in the migrated `fibo-v2` (SPARQL
   `datatype(?o) != xsd:string` count), as expected; verified, not assumed.

**Two 4.2 behaviours the cutover plan must respect (new findings):**

- **`--storage-path` semantics changed.** In 4.1.4 it named the project root
  (`/data/fluree`); in 4.2.4 it names the **storage directory**
  (`<project>/.fluree/storage`). Pointing it at a project root yields a server
  that starts, logs normally, and reports **zero ledgers** — no error. The
  systemd unit for a 4.2 primary must use the storage-dir form.
- **The CLI/server daemon state is shared per-user, not per-version.** Both
  the 4.1.4 and 4.2.4 binaries read `~/.fluree/server.pid`; `fluree-42 server
  start` refuses while the live 4.1.4 runs, and `fluree-42 server stop` would
  stop the **live** server. `FLUREE_HOME` does not relocate the pid check. The
  4.2 primary therefore runs detached (`setsid nohup … server run`) until
  cutover; at cutover Dave's systemd unit replaces both. Never run
  `fluree-42 server start|stop|restart` on db1 while 4.1.4 is the live
  server.

## Cutover (step 4), 2026-10-15 — executed as Repoint

Dave's rulings, 2026-10-15: cutover now; the bofa/syndicate peer is included
(it is the other bank's Fluree estate; its Postgres/Mongo are not Fluree and
stay untouched); migrate the `ccf` fixture ledger too.

**`ccf` migration.** Copy-first export (all 28 branch commit dirs + `ns@v2`
metadata copied to scratch, stale live `*.index.json` excluded, each branch
re-indexed fresh — 8.4 MB of commits) → `ccf.flpack` (1,608 commits) →
imported into the 4.2 primary. `ccf` main: **43,464 triples, exact match**
with live.

**Branch caveat — open with ccf-sdk.** A 4.1.4 `--format ledger` export
carries **main only**; the 28 `cp04-*` branches (each a single frozen
fixture-rebuild snapshot, 6,666 flakes, timestamps matching known-issues
§63.1) did not transfer, and 4.2's `fluree branch list ccf` confirms only
`main`. They remain fully reachable on the 4.1.4 fallback server (:8090,
which keeps running). ccf-sdk was asked via the board whether those snapshot
branches must live on 4.2; if yes, each can be re-materialised as a 4.2
branch from its RDF export.

**Repoint.** New endpoints everywhere the estate is configured:
`FLUREE_URL=http://192.168.4.76:8092` (repo `.env`, `.env.example`,
`ccf/config.py` default, CLAUDE.md store table, `~/.bashrc`
`FLUREE_URL`+`FLUREE_HOST`) and
`CO_LENDER_FLUREE_URL=http://192.168.4.76:8093` (`~/.bashrc` on the
workstation, v2 reference doc). `docs/ccf_dataprep_v2.md` records the change
per the store-assignment rule. The `~/.bashrc` `FLUREE_URL`/`FLUREE_HOST`
lines were initially missed (the co-lender line had been repointed, these two
had not) — caught by Dave's question 2026-10-15 and fixed; exported vars
override the repo `.env`, so the miss would have sent every new terminal to
the old server.

**Stale-environment hazard (near miss, caught).** Values exported into a
login shell before the cutover keep overriding the files: `load_dotenv` does
not clobber an existing env var, and `.bashrc` is not re-read by running
shells. A validator-suite run launched from this session's pre-cutover shell
therefore targeted the OLD servers — caught during pytest startup, before
any Fluree write (live t unchanged at 6,065/16), and killed. The same
stale-env suite re-run explicitly against :8092/:8093 is the post-cutover
gate recorded below. **Rule: any shell opened before the cutover must be
restarted before it touches Fluree; a stale shell silently writes to the
old servers and forks the estate.**

**Post-cutover gate — PASS.** Full suite re-run with explicit
`FLUREE_URL=http://192.168.4.76:8092` and
`CO_LENDER_FLUREE_URL=http://192.168.4.76:8093`: **856/856 passed, 0 failed**
(exit 0, 2m52s). Post-suite 4.2 `fibo-v2` t=6,157 (+46 from 6,111 — the §58
signature again, triples unchanged); live 4.1.4 fallback untouched
(`fibo-v2` t=6,065, peer t=16, all 28 `ccf` cp04-* branches still listed).

**Durability.** The peer container `fluree-demo-42` carries
`restart=unless-stopped`, same as the old peer. The 4.2 primary ran under
`nohup` during the cutover afternoon; **Dave installed
`loaders/fluree-42.service` at 18:48 MST on 2026-10-15** (unit active and
enabled, nohup instance killed — clean handover, all three ledgers serving).
A db1 reboot now brings up both 4.2 servers; the reboot gap below is CLOSED.
The 4.1.4 `fluree.service` is still enabled too, so a reboot resurrects BOTH
the fallback (:8090) and the new primary — harmless while the fallback is
kept, but disable it when the fallback is finally retired. The
`fluree-mcp-server` unit (:3100 → :8090) is inactive and not-found by
systemd as configured; if it is ever revived it must be repointed.

**Rollback posture.** The 4.1.4 (:8090), 4.1.6 (:8091) and their storage are
untouched and keep running; the pre-migration snapshot packs sit in
`/home/parkave/mig42/snapshot`. Rollback = point the config back at
:8090/:8091. Nothing should write to the old instances anymore.

## Step 5 — bundle rebuild from 4.2 (complete, recorded 2026-10-15)

The plan section as originally written claimed the 4.2 command set has no
`fluree index` subcommand. **That claim was wrong** — the spike proved
`fluree-42 index --help` exists. The real 4.2 differences the rework hit:
`--direct` is gone (export/list/query read project storage directly), and
live 4.2 storage already holds exactly one current index, so the dump copies
the whole ledger dir and no index rebuild is needed.

What was done, in order:

- **`dump_fluree.sh` reworked** for the 4.2 CLI (no `--direct`; staging copies
  `storage/<ledger>` + `storage/ns@v2/<ledger>` into a fresh `fluree init`
  project, stale `*.lock` files deleted). Validated by three spikes before
  the real run: primary export from copy (6,157 commits / 103 index
  artifacts), round-trip import (89,148 triples exact), peer-container export
  (16 commits). The export announcement format is unchanged from 4.1, so
  `record_ledger_t` parsed as before.
- **Full `dump_all.sh` run green**: fresh 19-artifact bundle at `/data/laptop`
  (387 MB; fibo-v2 flpack 82 MB, PG dumps 119 MB, Mongo 186 MB+). Sidecar
  ledger t = {fibo-v2: 6157, fibo: 5, bofa/syndicate: 16}. The earlier
  1.2 GB anomaly was migration scratch (`/data/laptop/.mig42`) sitting
  inside the bundle root — moved to `/home/parkave/mig42`, which is also
  where the pre-migration snapshot packs live.
- **Restore-side scripts and install docs repinned to 4.2.4**:
  `restore_fluree.sh` (drop/create without `--direct`, `server run` form),
  `restore_all.sh` server hint, `INSTALL-ubuntu.md` and `INSTALL-macos.md`
  (installer URL 4.2.4, Docker tag pinned 4.2.4, storage-path semantics
  warning). Digest check: repo ≡ bundle for all shipped scripts.
- **`damaged_restore.sh` harness rot fixed** before the rehearsal: expected
  snippets were stale since Wave 20 ("required 113, got 112" / "required
  53" vs the verifier's current 116 / 83), and the Fluree denylist predated
  the cutover (no :8092/:8093). Added `CCF_B1CHK_PG_PORT` because this
  rehearsal could not reuse B1's host-postgres scratch: the postgres-role
  credential (`~/.pgpass_b1chk`) no longer exists on db1 and cannot be
  recreated without sudo, so the scratch server ran as a throwaway
  postgres:16 Docker container on 5499 instead. The port changes which
  SERVER, never which DATABASE — every b1chk dbname rule still applies.
- **From-scratch Ubuntu rehearsal (B1 Task 9 procedure), all green:**
  the bundle's own shipped `restore_fluree.sh` ran clean on db1 with all
  assertions passing (t 6157/5/16, triples 89,148/10); scratch PG
  (b1chk_pg/b1chk_peer_pg in the container) + scratch mongod (:27777) +
  local SQLite copy restored; `verify_install.py` from the workstation:
  **20 passed, 0 failed** (Neo4j skipped by design — DETACH DELETE would
  destroy the live v1 graph); `damaged_restore.sh`: all four damages
  produced the specific named failure (116→115, 38,238→37,989, 8→1,
  83→78) and the baseline came back green after the restores. Live
  estate re-checked after teardown: service active, peer container
  healthy, host PG 156/83, live fibo-v2 t=6157 unchanged.

One rehearsal-infrastructure bug worth recording: the recreated
`~/.pgpass_b1chk` line was written with **six** fields
(`host:port:db:*:user:password`) instead of the required **five**
(`host:port:db:user:password`). libpq parsed the wildcard user as a match
and sent `postgres:<password>` as the password, so every scratch-PG call
failed "password authentication failed" while the same bytes succeeded
via `PGPASSWORD`. Byte-level comparisons (cmp, sha256 windows) could not
catch it because they were built from the same wrong template the file
was written from. Diagnosed by narrowing a catch-all entry
(`*:*:*:*:pw` worked where the specific line failed), fixed by writing
`127.0.0.1:5499:*:postgres:pw`. A format note now lives in the
`damaged_restore.sh` header comment.

## Step 6 — old servers retired, 2026-10-15 (evening)

Dave's decision, 22:03 MST: no rollback servers; the estate runs on 4.2.4 only.

- **Primary 4.1.4 (:8090) stopped.** It was an orphaned `fluree server
  child` (parent PID 1, started 2026-09-05), not under systemd, so it was
  stopped with `kill`. After the kill nothing listens on :8090, and 4.2.4 on
  :8092 answers live `fibo-v2`, `fibo` and `ccf` queries.
- **`fluree.service` and `fluree-mcp.service` are still enabled** and must be
  disabled (`sudo systemctl disable fluree.service fluree-mcp.service`).
  `fluree-mcp` points at `127.0.0.1:8090` and declares `Requires=fluree.service`,
  so leaving it enabled would restart the 4.1.4 server on the next boot.
  It has not run since 2026-08-08.
- **Peer 4.1.6 container `fluree-demo` (:8091)**: `bofa/syndicate` main t=16
  there and on `fluree-demo-42` (:8093) alike. It was stopped and set to
  `--restart=no` (done by Dave, Step 7). The container and its volume are kept.
- **What this removes.** The 28 `ccf` `cp04-*` snapshot branches existed only
  on 4.1.4 (see "Branch caveat" above). They are now unserved. ccf-sdk was told
  the server is being upgraded. The commit and index files remain at
  `/data/fluree/ccf/cp04-*`, so a branch can still be rebuilt on 4.2 from that
  copy if ccf-sdk asks.
- **Rollback is now a restart, not a running server**: storage at `/data/fluree`
  (4.1.4) is untouched; `/home/parkave/bin/fluree server run --storage-path
  /data/fluree --listen-addr 0.0.0.0:8090` brings it back.

## Step 7 — 4.2 storage moved to the data partition, 2026-10-15 (late evening)

Dave: the 4.2 data must sit on the same partition as the 4.1.4 data
(`/dev/nvme1n1p1`, mounted at `/data/mongodb`); the cutover had left both
4.2 trees on the system disk under `~/fluree-42/`.

`loaders/move_fluree42_to_data.sh` (run by Dave on db1, needs sudo):

1. stops both servers, then copies the two trees to `/data/mongodb/fluree-42/{storage,peer}`;
2. adds the symlink `/data/fluree-42`, the same pattern as `/data/fluree`;
3. `diff -r`s each copy against its source;
4. repoints the unit's `--storage-path` and recreates `fluree-demo-42` on the new bind mount;
5. requires every ledger's t to match before and after.

Old trees are renamed `*.pre-move` and the old container
`fluree-demo-42.pre-move`. Nothing is deleted by the script.

**First run failed safe, and exposed two bugs in the script.**

- **Order-sensitive check.** The before/after check compared `fluree list`
  output as an exact string. After the restart the same three ledgers came
  back in a different order (`ccf, fibo-v2, fibo` → `fibo, fibo-v2, ccf`,
  identical t), so the check failed and rollback ran. The comparison now sorts.
- **Incomplete rollback.** Rollback then ran `systemctl start`, which does
  nothing on a running unit. The primary was left serving the new tree under
  the reverted unit, so the unit and the process disagreed. Both trees were
  verified identical (`diff -r`), so nothing diverged. Rollback now uses
  `restart`.

The first run's copy is kept as `/data/mongodb/fluree-42.failed-run1`.

**Second run: green.**

- The unit and the running process both name `/data/fluree-42/storage`.
- The process has no open files under `~/fluree-42`.
- The peer is mounted on `/data/fluree-42/peer`.
- The storage tree is `diff -r` identical to `storage.pre-move`.
- Ledgers: `fibo` 5, `fibo-v2` 6157, `ccf` 1608, `bofa/syndicate` 16. Live
  queries answer on :8092 and :8093.

`portable/dump/dump_fluree.sh` `LIVE_STORAGE` now defaults to the new path.

**Integrity, after the move.** `fluree verify --direct` was run against a
byte-identical scratch copy of the live storage. It checked all 6,157 /
5 / 1,608 commits of `fibo-v2` / `fibo` / `ccf`, and the peer's 16 commits
in-container. All four ledgers came back healthy, with no problems, and the
index t equals the head t on each. Live triple counts: `fibo-v2` 89,148,
`ccf` 43,464, `bofa/syndicate` 10, all matching the recorded figures. `fibo`
(v1) has 151 triples; no figure was recorded for it to compare against.

**Bare `fluree` on db1 was still 4.1.4.** `~/bin/fluree` was the 4.1.4
binary, and the cutover had installed 4.2.4 beside it as `~/bin/fluree-42`.
Now `~/bin/fluree` is a symlink to `fluree-42`, and the old binary is kept
as `~/bin/fluree-4.1.4`. `fluree.service` and `fluree-mcp.service` are
disabled (Dave), but their unit files remain. `fluree.service` still execs
`~/bin/fluree` against `/data/fluree`, so a manual start would now run 4.2.4
over the 4.1.4 storage. Delete both unit files rather than start them.

**Final state, checked 2026-10-16 ~05:25 UTC.**

- Dave deleted both old unit files (`systemctl` reports `not-found`). The
  4.1.6 peer container `fluree-demo` is stopped with `--restart=no`.
- Nothing listens on :8090, :8091 or :3100.
- Only `fluree-42.service` (:8092) and `fluree-demo-42` (:8093) run, both
  4.2.4, both on `/dev/nvme1n1p1`.
- `.pre-move` copies, `fluree-demo-42.pre-move`, and `fluree-42.failed-run1`
  were all removed by Dave.
- ccf-sdk was told on the board:
  `contrib/ccf-dataprep/fluree-estate-on-424-only-final-state.md`. It
  supersedes `fluree-41-servers-retired.md`.

## Step 8 — bundle rebuilt after the storage move, restore re-proven on 4.2.4 (2026-10-16 ~05:35 UTC)

**Rebuild.** `dump_all.sh` was re-run so that `dump_fluree.sh`'s new
`LIVE_STORAGE=/data/fluree-42/storage` default ran for real. The result: 19
artifacts, 387 MB, and ledger_t {fibo-v2: 6157, fibo: 5, bofa/syndicate: 16}.

Manifest diff against the Step 5 bundle (built 01:55 UTC, before the move):

- **All three `.flpack` files are sha256-identical.** The move changed no
  Fluree content.
- The Mongo, SQLite, Neo4j and shipped-script artifacts are also identical.
- The three `pg_dump -Fc` files differ in sha but not in byte count.
  `pg_dump -Fc` embeds the dump's own timestamp in its header.

**Restore, two independent 4.2.4 targets.**

1. **db1 host binary.** The bundle's shipped `restore_fluree.sh` restored into
   a scratch project (`~/b1chk_fluree42`), and all five of its assertions
   passed. Found t matched the manifest's 6157/5/16; triples were 89,148 and
   10. `fluree verify` then checked the restored copy (6,157 / 5 / 16
   commits) and found it healthy, with 0 problems. The scratch was removed.
2. **A clean `fluree/server:4.2.4` container** (`--rm`, bundle mounted
   read-only, no ports). This is the image `INSTALL-macos.md` uses. The three
   packs imported cleanly; triples were 89,148 / 151 / 10, and all three
   ledgers verified healthy.

The live estate was unchanged afterwards (t 6157/5/1608 on :8092).
Postgres, Mongo and SQLite restores were not re-rehearsed here: their
scripts and the restore path are unchanged since Step 5's green rehearsal,
and only the pg dumps' timestamps moved.

## Named risks

| Risk | Handling |
|---|---|
| 4.1.x pack does not import into 4.2 | Step 1 spikes it first; two-hop import fallback |
| Export announcement format changed (4.2.1) | Parser fails loudly; fix is in this wave's scope |
| Ledger-ID parsing changed (4.2.2) | Name check before any count check |
| Other 4.2 API surface changes | The validator suite is the regression net; §5.1 re-test names the known surface |
| 47 GB live index bloat follows the ledger | It does not: import rebuilds one current index (~47 MB). Live-directory reclaim remains Dave's call, unchanged from B1 |

## Out of scope

- FIBO starter pack load, any ontology extension, binding-table changes.
- New public data (FRED or otherwise) and any engineered data — the wider
  v3 estate discussed 2026-10-13.
- Reclaiming the 47 GB on the live 4.1.4 host.
- Neo4j/Postgres/Mongo — untouched by this wave.

## Effort

| Step | Estimate |
|---|---|
| 0–1 Snapshot + import spike | 0.5 day |
| 2 Side-by-side install (host + container) | 0.5 day |
| 3 Import + verification battery | 0.5–1 day |
| 4 Cutover | 0.5 day |
| 5 Bundle rebuild + restore validation | 0.5–1 day |
| **Total** | **2–3 days** |

Rollback is free at every step before cutover: the live instances and their
storage are never modified, and the step-0 `.flpack`s predate all of it.