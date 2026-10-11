# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Cross-process latency suite (PERF-03; Phase 11 D-15/D-18/D-20).

Real subprocess over localhost: MCP egress and A2A/peering round-trips,
startup and warm-up excluded, gated with the looser 25% crossproc suite
default from ``perf/thresholds.toml``.
"""
