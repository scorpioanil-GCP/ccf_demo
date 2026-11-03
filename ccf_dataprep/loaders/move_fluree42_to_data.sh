#!/usr/bin/env bash
# move_fluree42_to_data.sh -- move both Fluree 4.2.4 storage trees off the
# system disk onto the /data/mongodb partition, beside the retired 4.1.4 data.
#
# Run ON db1 as parkave:   sudo -v && bash move_fluree42_to_data.sh
#
#   primary  :8092  /home/parkave/fluree-42/project/.fluree/storage -> /data/fluree-42/storage
#   peer     :8093  /home/parkave/fluree-42/peer                    -> /data/fluree-42/peer
#
# /data/fluree-42 is a symlink to /data/mongodb/fluree-42, the same pattern as
# /data/fluree and /data/fluree-demo. Both servers are stopped for the copy so
# the trees are quiescent; downtime is the copy time (~400 MB).
#
# Nothing is deleted. The old trees are renamed *.pre-move and the old peer
# container is renamed fluree-demo-42.pre-move (stopped, restart=no). Once the
# new layout has run cleanly, remove them by hand.
#
# Verification is by content, not by "it started": the copies are diffed
# byte-for-byte while both servers are down, and every ledger's t must match
# before and after.
set -euo pipefail

SRC_PRIMARY=/home/parkave/fluree-42/project/.fluree/storage
SRC_PEER=/home/parkave/fluree-42/peer
DEST_REAL=/data/mongodb/fluree-42
DEST=/data/fluree-42
UNIT=/etc/systemd/system/fluree-42.service
FLUREE42=/home/parkave/bin/fluree-42
PEER=fluree-demo-42
PEER_IMAGE=fluree/server:4.2.4

say() { printf '\n== %s\n' "$*"; }
die() { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }

# Sorted: `fluree list` order is not stable across a restart (first run of this
# script failed on fibo/fibo-v2/ccf vs ccf/fibo-v2/fibo with identical t).
ledgers_primary() { (cd /home/parkave/fluree-42/project && "$FLUREE42" list 2>/dev/null) | grep -E '^\| [a-z]' | tr -s ' ' | sort; }
ledgers_peer()    { docker exec "$PEER" fluree list 2>/dev/null | grep -E '^\| [a-z]' | tr -s ' ' | sort; }
wait_http() {  # url
  for _ in $(seq 1 30); do curl -fsS -o /dev/null "$1" && return 0; sleep 1; done
  return 1
}

# --- preflight ---------------------------------------------------------------
say "preflight"
[ "$(id -un)" = parkave ] || die "run as parkave (sudo is used per step)"
sudo -n true 2>/dev/null || die "run 'sudo -v' first so sudo does not prompt mid-move"
[ -d "$SRC_PRIMARY/ns@v2" ] || die "$SRC_PRIMARY is not a 4.2 storage dir (already moved?)"
[ -d "$SRC_PEER/.fluree/storage" ] || die "$SRC_PEER has no .fluree/storage (already moved?)"
[ ! -e "$DEST" ] && [ ! -e "$DEST_REAL" ] || die "$DEST or $DEST_REAL already exists (a failed run's copy? after confirming the primary serves $SRC_PRIMARY: sudo mv $DEST_REAL $DEST_REAL.failed-\$(date +%s) && sudo rm $DEST)"
docker ps -a --format '{{.Names}}' | grep -qx "$PEER.pre-move" && die "container $PEER.pre-move already exists"
grep -q -- "--storage-path $SRC_PRIMARY" "$UNIT" || die "$UNIT does not name $SRC_PRIMARY"

BEFORE_PRIMARY="$(ledgers_primary)"; BEFORE_PEER="$(ledgers_peer)"
[ -n "$BEFORE_PRIMARY" ] && [ -n "$BEFORE_PEER" ] || die "could not list ledgers before the move"
echo "primary:"; echo "$BEFORE_PRIMARY"; echo "peer:"; echo "$BEFORE_PEER"

# --- stop both servers --------------------------------------------------------
say "stopping fluree-42.service and $PEER"
sudo systemctl stop fluree-42
docker stop "$PEER" >/dev/null

restore_on_failure() {
  [ "$?" -eq 0 ] && return 0
  printf '\nRolling back: old unit and old peer container back in service.\n' >&2
  [ -f "$UNIT.pre-move" ] && sudo cp "$UNIT.pre-move" "$UNIT" && sudo systemctl daemon-reload
  [ -d "$SRC_PRIMARY.pre-move" ] && [ ! -e "$SRC_PRIMARY" ] && mv "$SRC_PRIMARY.pre-move" "$SRC_PRIMARY"
  [ -d "$SRC_PEER.pre-move" ] && [ ! -e "$SRC_PEER" ] && mv "$SRC_PEER.pre-move" "$SRC_PEER"
  if docker ps -a --format '{{.Names}}' | grep -qx "$PEER.pre-move"; then
    docker rm -f "$PEER" >/dev/null 2>&1 || true
    docker rename "$PEER.pre-move" "$PEER"
    docker update --restart=unless-stopped "$PEER" >/dev/null
  fi
  # restart, not start: start is a no-op on a running unit and would leave
  # the primary serving the new tree under the reverted unit (first run did).
  sudo systemctl restart fluree-42 || true
  docker start "$PEER" >/dev/null || true
  printf 'The partial copy at %s is left for inspection.\n' "$DEST_REAL" >&2
}
# EXIT, not ERR: die() exits deliberately, and ERR never fires for that.
trap restore_on_failure EXIT

# --- copy and verify ----------------------------------------------------------
say "copying to $DEST_REAL"
sudo mkdir "$DEST_REAL"
sudo chown parkave:parkave "$DEST_REAL"
sudo ln -s "$DEST_REAL" "$DEST"
cp -a "$SRC_PRIMARY" "$DEST_REAL/storage"
cp -a "$SRC_PEER" "$DEST_REAL/peer"
diff -r "$SRC_PRIMARY" "$DEST_REAL/storage" >/dev/null || die "primary copy differs"
diff -r "$SRC_PEER" "$DEST_REAL/peer" >/dev/null || die "peer copy differs"
du -sh "$DEST_REAL/storage" "$DEST_REAL/peer"
df -h "$DEST_REAL" | sed 1d

# Rename the old trees so nothing can silently keep using them.
mv "$SRC_PRIMARY" "$SRC_PRIMARY.pre-move"
mv "$SRC_PEER" "$SRC_PEER.pre-move"

# --- repoint primary ----------------------------------------------------------
say "repointing $UNIT"
sudo cp "$UNIT" "$UNIT.pre-move"
sudo sed -i "s#--storage-path $SRC_PRIMARY#--storage-path $DEST/storage#" "$UNIT"
grep -q -- "--storage-path $DEST/storage" "$UNIT" || die "unit edit did not apply"
sudo systemctl daemon-reload
sudo systemctl start fluree-42
wait_http http://127.0.0.1:8092/health || die "primary did not come back on :8092"

# --- recreate peer on the new mount -------------------------------------------
say "recreating $PEER on $DEST/peer"
docker update --restart=no "$PEER" >/dev/null
docker rename "$PEER" "$PEER.pre-move"
docker run -d --name "$PEER" --restart unless-stopped \
  -p 8093:8090 -v "$DEST/peer:/var/lib/fluree" "$PEER_IMAGE" >/dev/null
wait_http http://127.0.0.1:8093/health || die "peer did not come back on :8093"

# --- prove nothing changed ----------------------------------------------------
say "verifying ledgers"
AFTER_PRIMARY="$(ledgers_primary)"; AFTER_PEER="$(ledgers_peer)"
[ "$AFTER_PRIMARY" = "$BEFORE_PRIMARY" ] || { echo "$AFTER_PRIMARY"; die "primary ledgers differ after move"; }
[ "$AFTER_PEER" = "$BEFORE_PEER" ] || { echo "$AFTER_PEER"; die "peer ledgers differ after move"; }
grep -q fibo-v2 <<<"$AFTER_PRIMARY" || die "fibo-v2 missing on primary"
grep -q bofa/syndicate <<<"$AFTER_PEER" || die "bofa/syndicate missing on peer"
trap - EXIT

say "done"
echo "primary:"; echo "$AFTER_PRIMARY"; echo "peer:"; echo "$AFTER_PEER"
cat <<EOF

Both servers now store on $(df --output=source "$DEST_REAL" | tail -1) ($DEST_REAL).
Kept for rollback (remove when satisfied):
  $SRC_PRIMARY.pre-move
  $SRC_PEER.pre-move
  $UNIT.pre-move
  container $PEER.pre-move
EOF
