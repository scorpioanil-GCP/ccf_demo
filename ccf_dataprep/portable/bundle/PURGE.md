# Purging a restored estate, by hand

For re-running a restore from a genuinely clean state.

**There is deliberately no `purge_all.sh`.** Every other step in this bundle is
a script; this one is not, and that is the point. A purge script is a loaded
gun that reads its target from the environment, and the environment is exactly
what goes wrong.

---

## 1 · Read this before you type anything

**The laptop's Postgres database and the live estate's Postgres database have
the same name.** Both are called `parkavedb`. Both hold a schema called
`ccf_v2`. The *only* thing that distinguishes them is the host.

So this command is either harmless or catastrophic depending on one variable
you cannot see in it:

```bash
dropdb parkavedb          # laptop: fine.  With PGHOST set: destroys the estate.
```

And `PGHOST` is set to the estate for anyone who has sourced the `ccf_dataprep`
repository's `.env`, which contains:

```
PGHOST=192.168.4.76
PGDATABASE=parkavedb
MONGO_URI=mongodb://192.168.4.76:27017
NEO4J_URI='bolt://192.168.4.76:7687'
```

That file exists to point at the estate. Nothing about it is wrong. It is
simply the last thing that should be in scope while you are deleting databases
by name.

**Use a shell that has never sourced it.** A fresh terminal, not the one you
were working in.

---

## 2 · Pre-flight — paste this first, every time

It prints one line per target and refuses to say `ALL LOCAL` if anything points
off-box. Run it in the same shell you are about to purge from.

```bash
ccf_preflight() {
  local bad=0 h
  h="${PGHOST:-<unset — local socket>}"
  case "${PGHOST:-}" in
    ""|localhost|127.0.0.1|::1) echo "  postgres  $h" ;;
    *) echo "  postgres  $h   <-- NOT LOCAL"; bad=1 ;;
  esac
  for v in CCF_MONGO_URI MONGO_URI NEO4J_URI CCF_FLUREE_URL FLUREE_URL \
           CO_LENDER_MONGO_URI CO_LENDER_FLUREE_URL; do
    case "${!v:-}" in
      "") ;;
      *localhost*|*127.0.0.1*|*'[::1]'*) echo "  $v  ${!v}" ;;
      *) echo "  $v  ${!v}   <-- NOT LOCAL"; bad=1 ;;
    esac
  done
  echo "  sqlite    ${CCF_SQLITE_PATH:-$HOME/ccf-data/departmental.sqlite}"
  echo "  fluree    ${CCF_FLUREE_HOME:-$HOME/ccf-fluree}"
  if [ "$bad" -ne 0 ]; then
    echo; echo "REFUSING: something above points off this machine." >&2
    echo "Open a shell that has not sourced ccf_dataprep/.env." >&2
    return 1
  fi
  echo; echo "ALL LOCAL — safe to purge."
}
ccf_preflight
```

**If it does not print `ALL LOCAL`, stop.** Do not "just unset the one
variable" in the shell you are in — open a new one. The variable you did not
think to check is the one that costs you the estate.

A second, cruder confirmation that costs nothing:

```bash
hostname          # must be your laptop, not the estate host
```

---

## 3 · Purge, per store

Run these only after the pre-flight passes.

### Postgres — the two databases

```bash
dropdb --if-exists parkavedb
dropdb --if-exists bofa_syndicated
```

The restore recreates both with `createdb`. If you changed
`CCF_PGDATABASE` / `CCF_CO_LENDER_PGDATABASE` on the restore, drop those names
instead.

### MongoDB — three named databases, never a wildcard

```bash
mongosh --quiet --eval 'db.getSiblingDB("fibo_v2").dropDatabase()'
mongosh --quiet --eval 'db.getSiblingDB("fibo").dropDatabase()'
mongosh --quiet --eval 'db.getSiblingDB("bofa_syndicated").dropDatabase()'
```

Name each one. Never iterate `db.adminCommand("listDatabases")` — on the estate
host that same loop reaches an unrelated production system with millions of
documents, and a habit formed on the laptop is a habit you will repeat there.

### Fluree — the whole project directory

```bash
rm -rf "${CCF_FLUREE_HOME:-$HOME/ccf-fluree}"
```

This removes the marker file `.fluree/.ccf-b1-restore-target` along with the
ledgers, which is correct: the marker is how `restore_fluree.sh` knows the
directory is *its* to overwrite. A directory holding a Fluree project without
that marker is refused as a restore target, so a half-deleted one will block
the next restore rather than silently mix two estates.

Stop the Fluree server first if one is running, or it will rewrite files
underneath you.

### SQLite — one file

```bash
rm -f "${CCF_SQLITE_PATH:-$HOME/ccf-data/departmental.sqlite}"
```

### Neo4j — all nodes

```bash
cypher-shell -a "${NEO4J_URI:-bolt://127.0.0.1:7687}" \
  -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASSWORD" \
  'MATCH (n) DETACH DELETE n;'
```

This empties the default database entirely. On the laptop that is the estate
and nothing else. **Do not run it against any Neo4j you did not restore.**

---

## 4 · What you do NOT need to purge

Most of the restore already replaces rather than merges, so a plain re-run is
usually enough. Purging matters when you want to prove a restore works **from
empty** — which is a different claim, and the one worth testing before a demo.

| Store | Re-run behaviour | Purge needed for a from-empty test? |
|---|---|---|
| Postgres | `pg_restore --clean --if-exists` | yes, to test `createdb` too |
| MongoDB | `mongorestore --drop` | yes |
| Fluree | `fluree drop` then `create` | yes, to test `fluree init` too |
| SQLite | file is overwritten by `cp` | no real difference |
| Neo4j | restore Cypher opens with `MATCH (n) DETACH DELETE n` | no real difference |

The two rows where purging genuinely changes what is tested are Postgres and
Fluree: only an absent database exercises `createdb`, and only an absent
directory exercises `fluree init` and the marker logic.

---

## 5 · Never on the estate host

Nothing in this file should ever be run on the machine at `192.168.4.76`. It
holds the live estate, the co-lender fabric, and an unrelated production
MongoDB. There is no laptop-shaped reason to be logged into it.

If you are unsure which machine you are on, you are on the wrong one.
