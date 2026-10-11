# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""PERF-02 fabric-scale curves: assembly + projection over the rung ladder.

Exactly two curve families (D-26), pedantic mode with explicit rounds
(RESEARCH Pattern 2 / Pitfall 3 — seconds-long callables are never
auto-calibrated). Timing judgments live only in ``perf/gate.py`` (D-02).
"""
