# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""``perf.synth`` — deterministic, domain-neutral synthetic dataset generator.

PERF-02 substrate (Phase 11 decisions D-06..D-09, D-27..D-30). Importable so
Phase 12 can reuse or copy the package; ``/src`` stays free of fixture
machinery (D-06).
"""

from perf.synth.generator import (
    PERF_SEED,
    RUNGS,
    decision_stream,
    generate_events,
    rung_checksum,
    rung_shape,
)

__all__ = [
    "PERF_SEED",
    "RUNGS",
    "decision_stream",
    "generate_events",
    "rung_checksum",
    "rung_shape",
]
