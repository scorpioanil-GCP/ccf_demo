#!/usr/bin/env bash
# Copyright (c) 2026 David Castillo. All rights reserved.
# Stop the controlled instance by the pid launch.sh recorded. Usage: stop.sh <instance-root>
set -euo pipefail
ROOT=${1:?instance root}; PID=$(cat "$ROOT/run/pid")
kill "$PID" 2>/dev/null && echo "stopped $PID" || echo "not running ($PID)"
rm -f "$ROOT/run/port"
