# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The perf battery's benchmark suites (Phase 11; PERF-01/PERF-02).

Collected only via ``make perf-*`` / ``pytest perf/`` (D-04 — the always-on
run pins ``testpaths = ["tests"]``). No module in this tree makes a timing
judgment: every threshold comparison lives in ``perf/gate.py`` (D-02).
"""
