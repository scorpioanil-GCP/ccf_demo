"""The perf battery's benchmark suites (Phase 11; PERF-01/PERF-02).

Collected only via ``make perf-*`` / ``pytest perf/`` (D-04 — the always-on
run pins ``testpaths = ["tests"]``). No module in this tree makes a timing
judgment: every threshold comparison lives in ``perf/gate.py`` (D-02).
"""
