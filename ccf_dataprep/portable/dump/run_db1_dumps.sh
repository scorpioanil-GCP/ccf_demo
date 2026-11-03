#!/usr/bin/env bash
# Run the three db1-side dumps in order, after sourcing forwarded
# credentials. Runs ON DB1, invoked by dump_all.sh over ssh as a single
# `bash <staged-path>` call -- never an inlined multi-line script.
#
# Arg 1: path to a credentials env file (written by dump_all.sh, sourced
#        here, and removed by dump_all.sh immediately after this returns).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CREDS="${1:?usage: run_db1_dumps.sh <creds-file>}"
. "$CREDS"

bash "$HERE/dump_fluree.sh"
bash "$HERE/dump_postgres.sh"
bash "$HERE/dump_mongo.sh"
