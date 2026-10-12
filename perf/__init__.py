# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""``perf`` — the CCF performance battery tree (Phase 11, D-04/D-06).

Fully separate from the always-on ``tests/`` tree: benchmarks run only via
``make perf`` and the opt-in workflow. This package exists so the synthetic
dataset generator (``perf.synth``) is importable by the perf suites, by the
always-on determinism tests in ``tests/perf_synth``, and by Phase 12.
"""
