# ccf_dataprep — portable estate bundle

This bundle is a full offline copy of the ccf_dataprep data estate: two FIBO
fabrics (a v1 sample and the v2 estate) plus a small co-lender peer, spread
across five datastores. It restores onto a laptop with no network access to
the original servers.

**Pick your platform guide and follow it top to bottom, in order:**

- macOS: `INSTALL-macos.md`
- Ubuntu: `INSTALL-ubuntu.md`

Both guides end the same way: `bash restore.sh`, which checks the bundle,
restores every store, starts Fluree and runs the verifier in one go. That is deliberate — one restore code path serves both platforms;
only tool installation and service control differ, and `restore/platform.sh`
is the only file that knows which OS it is on.

## Changes in this bundle

**2026-10-10: a contamination removed.** Bundles built from 2026-09-10 to
2026-10-09 carried a Postgres table `public.companies` with **10 fabricated
rows** (`Northwind Traders`, `Contoso Manufacturing`, …). It was never
estate data. A test run of a separate project wrote it into the live
database on 2026-09-08, and the bundle then shipped it as part of the v1
sample. If you restored an earlier bundle, drop that table, or ignore it:
nothing in the estate refers to it.

The same rebuild restores primary keys, foreign keys and two views on eight
`ccf_v2` tables, which bundles from 2026-09-13 lacked. It also adds 823
role types to the Fluree graph (89,148 triples). No row of estate data
changed. Details: `docs/known-issues.md` §62–§63.2 in the `ccf_dataprep`
repository.

## What's in here

```
MANIFEST.json           every artifact: store, fabric, method, bytes, sha256
verify_install.py        the acceptance test — run this last
v1/                       a small starter fabric
  fluree-fibo.flpack
  postgres-public.dump
  mongo-fibo/
  neo4j-v1.cypher
v2/
  primary/                the main v2 estate
    fluree-fibo-v2.flpack
    postgres-ccf_v2.dump
    mongo-fibo_v2/
    departmental.sqlite
  colender/                a second, independent fabric (a co-lender peer)
    fluree-bofa-syndicate.flpack
    postgres-colender.dump
    mongo-bofa_syndicated/  (present but EMPTY — that database itself is
     empty on the source peer; the dump step always creates its output
     directory, so this exists with no *.bson.gz inside it, not omitted.
     MANIFEST.json records "empty": true for it, which is not the same as
     a failed dump)
restore.sh                 run this — check, restore, start Fluree, verify
verify_bundle.sh           the integrity check restore.sh runs first
restore/
  restore_all.sh           the five restores below, in order (no verify)
  restore_fluree.sh  restore_postgres.sh  restore_mongo.sh
  restore_sqlite.sh  restore_neo4j.sh
  platform.sh              the ONLY file that branches on macOS vs Ubuntu
```

**19 artifacts** are listed in `MANIFEST.json`: the 11 data artifacts above
(the peer MongoDB database counts as the 11th, recorded `"empty": true`
rather than omitted — its directory exists, per the note above) plus the 8
shipped scripts (`restore/*.sh` and `verify_install.py`) — a truncated
script in transit is otherwise invisible, and it is the one thing standing
between you and a working restore.

## Restore order

**Fluree → Postgres → MongoDB → SQLite → Neo4j**, then the verifier.
`restore_all.sh` runs them in exactly this order. The five stores are
independent of each other, but the verifier's cross-store join checks need
Postgres and Fluree both present — so restore everything before you verify
anything.

## Checking the manifest yourself

Every artifact's sha256 is in `MANIFEST.json`. If you want to confirm a file
was not damaged in transit before you spend an evening restoring from it:

```bash
python3 -c "
import json, hashlib, pathlib
d = json.load(open('MANIFEST.json'))
bad = 0
for a in d['artifacts']:
    p = pathlib.Path(a['path'])
    if a.get('empty'):
        continue
    h = hashlib.sha256()
    if p.is_file():
        h.update(p.read_bytes())
    else:
        for c in sorted(x for x in p.rglob('*') if x.is_file()):
            h.update(c.relative_to(p).as_posix().encode()); h.update(b'\0'); h.update(c.read_bytes())
    if h.hexdigest() != a['sha256']:
        print('MISMATCH', a['path']); bad += 1
print('artifacts', len(d['artifacts']), 'mismatched', bad)
"
```

Expect `mismatched 0`.

## If the verifier fails

`verify_install.py` exits:

- **0** — every check that ran passed. If it also skipped or excludes a
  store, it says so explicitly rather than claiming a full "Estate verified."
- **1** — at least one check failed, or (this matters) *zero* checks ran at
  all. A verifier that checked nothing is not a pass.
- **2** — a store could not be reached. **This is an install problem, not a
  data problem** — the data in this bundle is fine; something about the
  install (a service not started, a wrong port, a missing password) is not.
  The report names which store(s) it could not reach.

Re-read the platform guide's step for whichever store it names before
assuming the bundle itself is at fault.
