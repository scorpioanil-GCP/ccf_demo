#!/usr/bin/env bash
# Run by clean_ubuntu_restore.sh inside a fresh ubuntu:24.04: follow INSTALL-ubuntu.md steps 0-4 as user "tester"
# (systemctl swapped for direct starts: no systemd in a container), then restore.sh.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq sudo >/dev/null
useradd -m -s /bin/bash tester && echo 'tester ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/t
cp /dist/* /home/tester/ && chown tester: /home/tester/*
sudo -iu tester bash -euxo pipefail <<'U'
sha256sum -c SHA256SUMS
tar xf ccf-estate-bundle.tar
cd ccf-estate-bundle
# step 0
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl ca-certificates gnupg lsb-release xz-utils sqlite3 python3-venv >/dev/null
# step 1
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
# step 2
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/fluree/db/releases/download/v4.2.4/fluree-db-cli-installer.sh | sh
source "$HOME/bin/env"
fluree --version
# step 3
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql-common >/dev/null
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y >/dev/null
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql-16 postgresql-client-16 >/dev/null
sudo pg_ctlcluster 16 main start
psql --version
sudo -u postgres createuser --superuser "$(whoami)"
# step 4
curl -fsSL https://pgp.mongodb.com/server-8.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-8.0.gpg
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/8.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mongodb-org mongodb-mongosh mongodb-database-tools >/dev/null
sudo -u mongodb mongod --config /etc/mongod.conf --fork --logpath /var/log/mongodb/mongod.log
mongorestore --version | head -1
# step 6: THE ONE COMMAND (no NEO4J_PASSWORD -> Neo4j skipped)
set +e
bash restore.sh; rc=$?
[ "$rc" -eq 0 ] || exit "$rc"
echo "RESTORE_RC=$rc"
# re-run: must be idempotent and must stop/restart its own Fluree server
bash restore.sh > /tmp/second.log 2>&1; rc2=$?
tail -25 /tmp/second.log
echo "RESTORE_RC_SECOND=$rc2"
exit "$rc2"
U
