#!/usr/bin/env bash
# Copyright (c) 2026 David Castillo. All rights reserved.
# Launch ONE controlled bank instance of the CCF governed product door (Tuesday GO item 3, 2026-10-11).
# These are deployment controls, not claims that the unrestricted SDK is fixed.
#
# Usage: launch.sh <instance-root> <sdk-tree> [python]
#   <instance-root>  absolute, owned by the service account, mode 0700; holds secrets/instance.env (0600)
#   <sdk-tree>       the installed SDK source tree (the tested commit), read-only to the service account
set -euo pipefail
umask 077

ROOT=${1:?instance root}; TREE=${2:?sdk tree}; PY=${3:-python3}
refuse() { echo "REFUSED: $*" >&2; exit 2; }

[[ "$ROOT" = /* ]] || refuse "instance root must be absolute"
[[ -d "$ROOT" ]] || refuse "instance root $ROOT does not exist"
SECRETS="$ROOT/secrets/instance.env"
[[ -f "$SECRETS" ]] || refuse "missing $SECRETS (copy instance.env.example, fill in, chmod 0600)"

# 1. A dedicated service account, never root.
[[ "$(id -u)" != 0 ]] || refuse "never run as root"
ACCOUNT=$(sed -n 's/^CCF_SERVICE_ACCOUNT=//p' "$SECRETS")
[[ -n "$ACCOUNT" ]] || refuse "CCF_SERVICE_ACCOUNT is not set in $SECRETS"
[[ "$(id -un)" = "$ACCOUNT" ]] || refuse "running as $(id -un), this instance belongs to $ACCOUNT"

# 2. Private storage: instance root and secrets owned by the account and closed to everyone else.
mode_of() { stat -c '%a' "$1"; }; owner_of() { stat -c '%U' "$1"; }
[[ "$(owner_of "$ROOT")" = "$ACCOUNT" && "$(mode_of "$ROOT")" = 700 ]] || refuse "$ROOT must be owned by $ACCOUNT with mode 700"
[[ "$(owner_of "$SECRETS")" = "$ACCOUNT" && "$(mode_of "$SECRETS")" = 600 ]] || refuse "$SECRETS must be owned by $ACCOUNT with mode 600"
for d in scratch run logs; do install -d -m 700 "$ROOT/$d"; done

# 3. Trusted deployment code: the tree is the tested commit, unmodified.
COMMIT=$(git -C "$TREE" rev-parse HEAD 2>/dev/null || echo unknown)
if [[ -n "$(git -C "$TREE" status --porcelain --untracked-files=no 2>/dev/null)" ]]; then refuse "$TREE has local modifications"; fi

# 4. A closed environment: only the names this instance needs reach the process (no estate, cloud or model credentials).
set -a; source "$SECRETS"; set +a
[[ -n "${CCF_CP_06C_DOOR_TOKEN:-}" ]] || refuse "CCF_CP_06C_DOOR_TOKEN is not set"
EXAMPLE="$TREE/examples/cp-06-canonical-collateral-and-setoff-coverage"
env -i PATH=/usr/bin:/bin HOME="$ROOT" LANG=C.UTF-8 TMPDIR="$ROOT/scratch" \
    PYTHONPATH="$TREE/src:$TREE/runtime:$EXAMPLE" PYTHONDONTWRITEBYTECODE=1 \
    CCF_CP_06C_DOOR_TOKEN="$CCF_CP_06C_DOOR_TOKEN" \
    CCF_CP_06C_FLUREE_URL="$CCF_CP_06C_FLUREE_URL" CCF_CP_06C_FLUREE_LEDGER="$CCF_CP_06C_FLUREE_LEDGER" \
    CCF_CP_06C_POSTGRES_DSN="$CCF_CP_06C_POSTGRES_DSN" CCF_CP_06C_POSTGRES_SCHEMA="$CCF_CP_06C_POSTGRES_SCHEMA" \
    setsid "$PY" -B "$EXAMPLE/run.py" --door > "$ROOT/run/door.out" 2> "$ROOT/logs/door.err" < /dev/null &
PID=$!
echo "$PID" > "$ROOT/run/pid"; echo "$COMMIT" > "$ROOT/run/commit"

# 5. Wait for the door: an ephemeral port on 127.0.0.1 only (ProductDoor.serve_loopback), real bearer authentication.
for _ in $(seq 1 120); do
  if PORT=$(sed -n 's/^READY \([0-9]*\)$/\1/p' "$ROOT/run/door.out") && [[ -n "$PORT" ]]; then
    echo "$PORT" > "$ROOT/run/port"; echo "READY pid=$PID port=$PORT commit=$COMMIT"; exit 0
  fi
  kill -0 "$PID" 2>/dev/null || { cat "$ROOT/logs/door.err" >&2; refuse "the door exited before it was ready"; }
  sleep 1
done
kill "$PID"; refuse "the door was not ready in 120 s"
