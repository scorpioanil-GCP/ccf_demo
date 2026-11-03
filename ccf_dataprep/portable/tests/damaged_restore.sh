#!/usr/bin/env bash
# Proves portable/verify_install.py actually detects damage: applies one
# damage at a time to a SCRATCH restore, confirms the verifier reports the
# SPECIFIC named check that broke (never just a generic non-zero exit), then
# restores that store's baseline before the next damage -- every damage is
# judged against a clean start, never against an already-damaged one.
#
# The guard block below is the most important part of this file: it refuses
# to run unless every ACTUAL destructive target -- not a stand-in for it --
# is unmistakably a scratch namespace, BEFORE any damage happens.
#
# Fix round 1 (two critical findings):
#
#   1. The Postgres guard used to check CCF_PG_DSN only, but every
#      destructive call (createdb/dropdb/pg_restore in restore_pg(), and the
#      DROP TABLE / DELETE damages below) targets CCF_B1CHK_PG_DBNAME /
#      CCF_B1CHK_PEER_DBNAME -- two INDEPENDENT variables nothing kept in
#      sync. A stale env or a typo (CCF_B1CHK_PG_DBNAME=parkavedb next to a
#      CCF_PG_DSN that still said dbname=b1chk_pg) would pass the old guard
#      and then destroy the live database while the verifier, reading the
#      untouched scratch DSN, reported green. Fixed: CCF_B1CHK_PG_DBNAME /
#      CCF_B1CHK_PEER_DBNAME are now validated directly (must contain
#      "b1chk"), and each is asserted to EQUAL the dbname actually named in
#      its corresponding DSN. Disagreement refuses.
#
#   2. The Mongo/Fluree guard was a denylist of literal substrings
#      ("...:27017...", "...:8090..."). MongoDB defaults to port 27017 when
#      a URI omits it, so `mongodb://192.168.4.76` (no port) matched none of
#      those patterns and would have sailed straight through onto the live
#      database. Fixed: both now require an explicit, separately-declared
#      scratch endpoint (CCF_B1CHK_MONGO_URI / CCF_B1CHK_FLUREE_URL) and
#      assert the operational variable equals it EXACTLY -- an allowlist,
#      not a denylist, so an endpoint nobody declared is refused rather than
#      admitted. The old denylist is kept underneath as a second layer, now
#      normalizing host:port (defaulting the port when the URI omits it)
#      before comparing, so it can no longer be dodged by omission either.
#
# Fix round 2 (two residual bypasses in that same denylist):
#
#   3. The denylist was case-sensitive (`case` in bash does not fold case),
#      so "LOCALHOST:27017" did not match the lowercase "localhost:27017"
#      pattern -- an operator could declare that spelling as BOTH the
#      operational and the declared-scratch endpoint, pass the allowlist,
#      and still reach the live host. Fixed: normalize_hostport() now
#      lowercases the host before any comparison.
#
#   4. Only literal strings (192.168.4.76 / 127.0.0.1 / localhost) were
#      denylisted -- a DNS name or /etc/hosts alias resolving to the same
#      machine (e.g. "db1") was invisible to a spelling-only check. Fixed:
#      resolve_hostport() resolves the host via python3's
#      socket.gethostbyname (identical on Linux/macOS) and the denylist is
#      also checked against the RESOLVED address, via a refuse() call at
#      each top-level call site (resolve_hostport itself never calls
#      refuse()/exit -- see the note above its definition below). A host
#      that fails to resolve is refused outright -- unresolvable is not the
#      same as safe.
#
# Two stores (Mongo, Fluree) cannot carry a "b1chk" marker in the thing this
# script would damage: verify_install.py hardcodes the database/ledger names
# it inspects (Mongo: "fibo_v2"/"fibo"; Fluree: "fibo-v2"/"fibo"/
# "bofa/syndicate") -- a scratch database literally named "b1chk_mongo" would
# never be looked at by the real verifier, which would defeat the entire
# point of this script. For those two, the scratch boundary is a SEPARATE
# throwaway server instance on its own port, named explicitly via
# CCF_B1CHK_MONGO_URI / CCF_B1CHK_FLUREE_URL (see above).
#
# Env vars this script consumes:
#   CCF_PG_DSN             required. Scratch postgres DSN; dbname MUST
#                          contain "b1chk" AND must equal CCF_B1CHK_PG_DBNAME.
#                          Also passed straight through to verify_install.py.
#   CCF_PEER_PG_DSN        optional. Same rule, against CCF_B1CHK_PEER_DBNAME.
#   CCF_SQLITE_PATH        required. LOCAL scratch sqlite copy path; MUST
#                          contain "b1chk".
#   CCF_MONGO_URI          required. Must equal CCF_B1CHK_MONGO_URI exactly.
#   CCF_B1CHK_MONGO_URI    required. The declared scratch mongo endpoint --
#                          no default; nothing unnamed is ever admitted.
#   CCF_FLUREE_URL         optional. If set, must equal CCF_B1CHK_FLUREE_URL
#                          exactly.
#   CCF_B1CHK_FLUREE_URL   required IFF CCF_FLUREE_URL is set. The declared
#                          scratch fluree endpoint.
#   CCF_SKIP_STORES        passed through to verify_install.py as-is
#                          (default here: "neo4j" -- see task-7-report.md for
#                          why Neo4j damage is not exercised by this script).
#   CCF_B1CHK_SSH          host that holds the restore tooling + bundle
#                          (default parkave@192.168.4.76).
#   CCF_B1CHK_BUNDLE       bundle root on that host (default /data/data_bundle).
#   CCF_B1CHK_PG_DBNAME    scratch db name on CCF_B1CHK_SSH (default b1chk_pg)
#                          -- this is the ACTUAL destructive target; must
#                          contain "b1chk" and must equal CCF_PG_DSN's dbname.
#   CCF_B1CHK_PEER_DBNAME  scratch peer db name (default b1chk_peer_pg) --
#                          same rule, always validated (restore_pg() always
#                          touches this db regardless of CCF_PEER_PG_DSN).
#   CCF_B1CHK_MONGO_DB     db name inside the scratch mongo instance that
#                          verify_install.py actually checks -- restricted to
#                          exactly "fibo_v2" or "fibo" (the only two names
#                          verify_install.py hardcodes); a "b1chk" marker is
#                          not possible here, so an allowlist of the two real
#                          names stands in for it.
#   CCF_B1CHK_PGPASSFILE   path (on CCF_B1CHK_SSH) to a .pgpass for the
#                          postgres role used to administer scratch dbs
#                          (default ~/.pgpass_b1chk -- parkave/colender lack
#                          CREATEDB on this host). Each line is FIVE fields,
#                          host:port:database:username:password -- 2026-10-15:
#                          a line written with six fields (an extra wildcard
#                          before the username) matched via the "*" user and
#                          sent "postgres:<password>" as the password, and
#                          every scratch call failed "password authentication
#                          failed" while the same bytes worked via PGPASSWORD.
#                          Byte-comparing the file cannot catch this; count
#                          the colons.
#   CCF_B1CHK_PG_PORT      port the scratch postgres listens on (default
#                          5432). Set this when the scratch server is a
#                          throwaway container alongside the live one --
#                          the 2026-10-15 rehearsal ran postgres:16 in
#                          Docker on 5499 because the host postgres-role
#                          password B1 set up (the ~/.pgpass_b1chk file)
#                          no longer exists and cannot be recreated
#                          without sudo. The b1chk dbname rules above are
#                          unaffected: the port changes WHICH SERVER,
#                          never WHICH DATABASE.
set -uo pipefail

# ---- resolve every variable that reaches a destructive call BEFORE any
# guard runs, so the guard checks the values actually in force ----
: "${CCF_B1CHK_SSH:=parkave@192.168.4.76}"
: "${CCF_B1CHK_BUNDLE:=/data/data_bundle}"
: "${CCF_B1CHK_PG_DBNAME:=b1chk_pg}"
: "${CCF_B1CHK_PEER_DBNAME:=b1chk_peer_pg}"
: "${CCF_B1CHK_MONGO_DB:=fibo_v2}"
: "${CCF_B1CHK_PGPASSFILE:=\$HOME/.pgpass_b1chk}"
: "${CCF_B1CHK_PG_PORT:=5432}"

: "${CCF_PG_DSN:?set this to the scratch postgres DSN, e.g. 'host=... dbname=b1chk_pg user=postgres password=...'}"
: "${CCF_SQLITE_PATH:?set this to the LOCAL scratch sqlite copy}"
: "${CCF_MONGO_URI:?set this to the scratch mongo endpoint}"

refuse() { echo "refusing: $*" >&2; exit 2; }

# Extract the dbname from a libpq keyword/value DSN ("host=... dbname=X
# ...") or a postgres:// URI. These are the only two forms used anywhere in
# this repo's scratch tooling.
pg_dsn_dbname() {
  local dsn="$1" rest
  case "$dsn" in
    postgres://*|postgresql://*)
      rest="${dsn%%\?*}"
      echo "${rest##*/}"
      ;;
    *)
      rest="${dsn#*dbname=}"
      if [ "$rest" = "$dsn" ]; then echo ""; else echo "${rest%% *}"; fi
      ;;
  esac
}

# Normalize a mongodb:// or http(s):// URL down to host:port, defaulting the
# port when the URL omits it (mongodb:// defaults to 27017; this estate's
# fluree URLs always spell theirs out, but default to 8090 for symmetry) and
# LOWERCASING the host -- hostnames are case-insensitive by definition, and
# bash `case` matching is not, so "LOCALHOST:27017" must fold to
# "localhost:27017" or it would slip past a lowercase-only denylist. This is
# what lets the denylist below catch an omitted-port or oddly-cased URI
# instead of being dodged by either.
normalize_hostport() {
  local url="$1" default_port="$2" hp host port
  hp="$(printf '%s' "$url" | sed -E 's#^[a-zA-Z][a-zA-Z0-9+.-]*://##; s#^[^@/]*@##; s#[/?].*$##')"
  case "$hp" in
    *:*) host="${hp%:*}"; port="${hp##*:}" ;;
    *) host="$hp"; port="$default_port" ;;
  esac
  host="$(printf '%s' "$host" | tr '[:upper:]' '[:lower:]')"
  printf '%s:%s' "$host" "$port"
}

# Resolve a "host:port" pair's host to an IP address and print "ip:port" on
# stdout, or print NOTHING and exit non-zero if the host will not resolve.
# python3's socket.gethostbyname is used because it behaves identically on
# Linux and macOS, unlike `getent hosts` (Linux only).
#
# IMPORTANT: this function must never call refuse()/exit itself. It is
# always invoked as `x="$(resolve_hostport ...)" || refuse ...` -- command
# substitution runs in a SUBSHELL, so an exit() inside a function called
# from within `$(...)` only terminates that subshell; the parent script
# would print the refusal message (stderr is inherited, not captured) and
# then continue running with the variable simply empty, silently past the
# very refusal it just printed. (This exact bug was caught live during
# testing: an unresolvable-host test correctly printed "refusing: ..." and
# then proceeded to run real damage commands anyway.) The refuse() call
# belongs at each TOP-LEVEL call site, gated on this function's exit status.
resolve_hostport() {
  local hp="$1" host port ip
  host="${hp%:*}"
  port="${hp##*:}"
  ip="$(python3 -c '
import socket, sys
try:
    print(socket.gethostbyname(sys.argv[1]))
except Exception:
    sys.exit(1)
' "$host" 2>/dev/null)" || return 1
  printf '%s:%s' "$ip" "$port"
}

# ---- Postgres: validate the ACTUAL destructive target, not a proxy for it,
# and assert it agrees with the DSN verify_install.py will read back ----
case "$CCF_PG_DSN" in *b1chk*) ;; *) refuse "CCF_PG_DSN does not name a b1chk scratch database" ;; esac
case "$CCF_B1CHK_PG_DBNAME" in
  *b1chk*) ;;
  *) refuse "CCF_B1CHK_PG_DBNAME ('$CCF_B1CHK_PG_DBNAME') does not contain 'b1chk' -- this is the database dropdb/createdb/pg_restore/DROP TABLE/DELETE actually touch" ;;
esac
case "$CCF_B1CHK_PEER_DBNAME" in
  *b1chk*) ;;
  *) refuse "CCF_B1CHK_PEER_DBNAME ('$CCF_B1CHK_PEER_DBNAME') does not contain 'b1chk'" ;;
esac

dsn_db="$(pg_dsn_dbname "$CCF_PG_DSN")"
[ "$dsn_db" = "$CCF_B1CHK_PG_DBNAME" ] || refuse "CCF_PG_DSN names database '$dsn_db' but the destructive target CCF_B1CHK_PG_DBNAME is '$CCF_B1CHK_PG_DBNAME' -- these must be the SAME database"

if [ -n "${CCF_PEER_PG_DSN:-}" ]; then
  case "$CCF_PEER_PG_DSN" in *b1chk*) ;; *) refuse "CCF_PEER_PG_DSN does not name a b1chk scratch database" ;; esac
  peer_dsn_db="$(pg_dsn_dbname "$CCF_PEER_PG_DSN")"
  [ "$peer_dsn_db" = "$CCF_B1CHK_PEER_DBNAME" ] || refuse "CCF_PEER_PG_DSN names database '$peer_dsn_db' but the destructive target CCF_B1CHK_PEER_DBNAME is '$CCF_B1CHK_PEER_DBNAME' -- these must be the SAME database"
fi

case "$CCF_SQLITE_PATH" in *b1chk*) ;; *) refuse "CCF_SQLITE_PATH does not look like a b1chk scratch file" ;; esac

case "$CCF_B1CHK_MONGO_DB" in
  fibo_v2|fibo) ;;
  *) refuse "CCF_B1CHK_MONGO_DB ('$CCF_B1CHK_MONGO_DB') must be exactly 'fibo_v2' or 'fibo' -- the only two names verify_install.py actually inspects" ;;
esac

# ---- Mongo/Fluree: allowlist the declared scratch ENDPOINT (exact match),
# denylist the known-live endpoint underneath, both port-omission-proof ----
: "${CCF_B1CHK_MONGO_URI:?set this to the declared scratch mongo endpoint -- must equal CCF_MONGO_URI exactly}"
[ "$CCF_MONGO_URI" = "$CCF_B1CHK_MONGO_URI" ] || refuse "CCF_MONGO_URI ('$CCF_MONGO_URI') does not exactly equal the declared scratch endpoint CCF_B1CHK_MONGO_URI ('$CCF_B1CHK_MONGO_URI')"

mongo_hostport="$(normalize_hostport "$CCF_MONGO_URI" 27017)"
case "$mongo_hostport" in
  192.168.4.76:27017|127.0.0.1:27017|localhost:27017)
    refuse "CCF_MONGO_URI normalizes to '$mongo_hostport', the LIVE mongo endpoint -- even if it matched CCF_B1CHK_MONGO_URI, that declaration itself would be wrong" ;;
esac
mongo_resolved="$(resolve_hostport "$mongo_hostport")" \
  || refuse "CCF_MONGO_URI host '${mongo_hostport%:*}' does not resolve -- refusing rather than assuming it is safe"
case "$mongo_resolved" in
  192.168.4.76:27017|127.0.0.1:27017)
    refuse "CCF_MONGO_URI resolves to '$mongo_resolved' (host '${mongo_hostport%:*}'), the LIVE mongo endpoint by address -- even if the spelling matched CCF_B1CHK_MONGO_URI, that declaration itself would be wrong" ;;
esac

if [ -n "${CCF_FLUREE_URL:-}" ]; then
  : "${CCF_B1CHK_FLUREE_URL:?CCF_FLUREE_URL is set -- also set CCF_B1CHK_FLUREE_URL, the declared scratch endpoint it must equal exactly}"
  [ "$CCF_FLUREE_URL" = "$CCF_B1CHK_FLUREE_URL" ] || refuse "CCF_FLUREE_URL ('$CCF_FLUREE_URL') does not exactly equal the declared scratch endpoint CCF_B1CHK_FLUREE_URL ('$CCF_B1CHK_FLUREE_URL')"

  fluree_hostport="$(normalize_hostport "$CCF_FLUREE_URL" 8090)"
  case "$fluree_hostport" in
    192.168.4.76:8090|192.168.4.76:8091|192.168.4.76:8092|192.168.4.76:8093|127.0.0.1:8090|127.0.0.1:8091|127.0.0.1:8092|127.0.0.1:8093|localhost:8090|localhost:8091|localhost:8092|localhost:8093)
      refuse "CCF_FLUREE_URL normalizes to '$fluree_hostport', a LIVE fluree endpoint -- even if it matched CCF_B1CHK_FLUREE_URL, that declaration itself would be wrong" ;;
  esac
  fluree_resolved="$(resolve_hostport "$fluree_hostport")" \
    || refuse "CCF_FLUREE_URL host '${fluree_hostport%:*}' does not resolve -- refusing rather than assuming it is safe"
  case "$fluree_resolved" in
    192.168.4.76:8090|192.168.4.76:8091|192.168.4.76:8092|192.168.4.76:8093|127.0.0.1:8090|127.0.0.1:8091|127.0.0.1:8092|127.0.0.1:8093)
      refuse "CCF_FLUREE_URL resolves to '$fluree_resolved' (host '${fluree_hostport%:*}'), a LIVE fluree endpoint by address -- even if the spelling matched CCF_B1CHK_FLUREE_URL, that declaration itself would be wrong" ;;
  esac
fi

export CCF_PG_DSN CCF_SQLITE_PATH CCF_MONGO_URI
[ -n "${CCF_PEER_PG_DSN:-}" ] && export CCF_PEER_PG_DSN
[ -n "${CCF_FLUREE_URL:-}" ] && export CCF_FLUREE_URL
: "${CCF_SKIP_STORES:=neo4j}"
export CCF_SKIP_STORES

HERE="$(cd "$(dirname "$0")" && pwd)"
VERIFIER="$HERE/../verify_install.py"

run_verify() {
  uv run --no-project "$VERIFIER"
}

restore_pg() {
  ssh "$CCF_B1CHK_SSH" "export PGPASSFILE=$CCF_B1CHK_PGPASSFILE; PGH='-h 127.0.0.1 -p $CCF_B1CHK_PG_PORT -U postgres'; \
    dropdb \$PGH --if-exists $CCF_B1CHK_PG_DBNAME >/dev/null; \
    dropdb \$PGH --if-exists $CCF_B1CHK_PEER_DBNAME >/dev/null; \
    createdb \$PGH $CCF_B1CHK_PG_DBNAME; \
    createdb \$PGH $CCF_B1CHK_PEER_DBNAME; \
    pg_restore \$PGH --no-owner --no-privileges --dbname=$CCF_B1CHK_PG_DBNAME '$CCF_B1CHK_BUNDLE/v2/primary/postgres-ccf_v2.dump' >/dev/null 2>&1 || true; \
    pg_restore \$PGH --no-owner --no-privileges --dbname=$CCF_B1CHK_PG_DBNAME '$CCF_B1CHK_BUNDLE/v1/postgres-public.dump' >/dev/null 2>&1 || true; \
    pg_restore \$PGH --no-owner --no-privileges --dbname=$CCF_B1CHK_PEER_DBNAME '$CCF_B1CHK_BUNDLE/v2/colender/postgres-colender.dump' >/dev/null 2>&1 || true" \
    >/dev/null
}

restore_mongo() {
  ssh "$CCF_B1CHK_SSH" "mongorestore --uri='$CCF_MONGO_URI' --db=$CCF_B1CHK_MONGO_DB --gzip --drop --quiet '$CCF_B1CHK_BUNDLE/v2/primary/mongo-fibo_v2/fibo_v2'" >/dev/null
}

restore_sqlite() {
  rsync -a "$CCF_B1CHK_SSH:$CCF_B1CHK_BUNDLE/v2/primary/departmental.sqlite" "$CCF_SQLITE_PATH"
}

# expect_fail LABEL EXPECT_SNIPPET  CMD...
# Runs CMD (the damage) then the verifier. PASSES only when the verifier
# exits 1 (a real, checked, DATA failure -- never 0, and never 2, which
# would mean connectivity broke rather than data) AND the FAILED section
# contains EXPECT_SNIPPET verbatim -- a generic red is not good enough.
expect_fail() {
  local label="$1" expect_snippet="$2"; shift 2
  echo "== $label"
  "$@"
  local out
  out="$(run_verify 2>&1)"
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "   DEFECT: verifier PASSED (exit 0) on a damaged restore"
    return 1
  fi
  if [ "$rc" -eq 2 ]; then
    echo "   DEFECT: exit 2 (a store was unreachable) -- this broke connectivity,"
    echo "           not data; it proves nothing about the check under test."
    echo "$out" | sed -n '/COULD NOT REACH/,+2p' | sed 's/^/   /'
    return 1
  fi
  echo "   exit $rc"
  if echo "$out" | grep -F -q "$expect_snippet"; then
    echo "$out" | grep -F "$expect_snippet" | sed 's/^/   named failure: /'
  else
    echo "   DEFECT: expected a FAILED line containing:"
    echo "       $expect_snippet"
    echo "   but it was not there. Full FAILED section:"
    echo "$out" | sed -n '/FAILED:/,$p' | sed 's/^/   /'
    return 1
  fi
}

fail=0

expect_fail "dropped a Postgres table (ccf_v2.legal_entity, CASCADE)" \
  "postgres ccf_v2 base tables: required 116, got 115" \
  ssh "$CCF_B1CHK_SSH" "PGPASSFILE=$CCF_B1CHK_PGPASSFILE psql -h 127.0.0.1 -p $CCF_B1CHK_PG_PORT -U postgres -d $CCF_B1CHK_PG_DBNAME -c 'DROP TABLE ccf_v2.legal_entity CASCADE'" \
  || fail=1
restore_pg

expect_fail "truncated a Mongo collection (fibo_v2.document, emptied)" \
  "mongo fibo_v2 documents: required 38238" \
  ssh "$CCF_B1CHK_SSH" "mongosh --quiet --eval \"db.getSiblingDB('$CCF_B1CHK_MONGO_DB').document.deleteMany({})\" '$CCF_MONGO_URI'" \
  || fail=1
restore_mongo

expect_fail "swapped the SQLite file for an empty one" \
  "sqlite departmental tables: required 8, got 1" \
  bash -c "rm -f '$CCF_SQLITE_PATH' && sqlite3 '$CCF_SQLITE_PATH' 'create table x(a)'" \
  || fail=1
restore_sqlite

expect_fail "Postgres restore missing ROWS, not a whole table (5 crosswalk rows deleted)" \
  "postgres crosswalk rows: required 83" \
  ssh "$CCF_B1CHK_SSH" "PGPASSFILE=$CCF_B1CHK_PGPASSFILE psql -h 127.0.0.1 -p $CCF_B1CHK_PG_PORT -U postgres -d $CCF_B1CHK_PG_DBNAME -c \"DELETE FROM ccf_v2.crosswalk WHERE lei IN (SELECT lei FROM ccf_v2.crosswalk LIMIT 5)\"" \
  || fail=1
restore_pg

# NOT exercised here: a truncated Fluree archive (fewer commits). The CLI
# refuses on the ledger-archive path -- `fluree export --format ledger`
# explicitly rejects `--at` ("archives capture the current head; use a
# TimeTravel restore on import instead."), and there is no import-side flag
# either; the only remaining route is hand-editing the content-addressed
# commit-chain/HEAD-pointer files under .fluree/storage, an undocumented
# on-disk format, which risks corrupting the scratch project rather than
# producing a clean, reviewable truncation. See task-7-report.md.

echo
echo "== rebuilding the full baseline once more and confirming green =="
if out="$(run_verify 2>&1)"; then
  echo "$out" | tail -5
  echo "Baseline is green again -- the damages above were the cause, not this harness."
else
  echo "$out"
  echo "DEFECT: baseline did not come back green after the restores above."
  fail=1
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "All damages produced a specific, named failure."
else
  echo "DEFECT: at least one damage did not fail as expected -- see above."
fi
exit "$fail"
