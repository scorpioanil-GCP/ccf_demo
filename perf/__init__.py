"""``perf`` — the CCF performance battery tree (Phase 11, D-04/D-06).

Fully separate from the always-on ``tests/`` tree: benchmarks run only via
``make perf`` and the opt-in workflow. This package exists so the synthetic
dataset generator (``perf.synth``) is importable by the perf suites, by the
always-on determinism tests in ``tests/perf_synth``, and by Phase 12.
"""
