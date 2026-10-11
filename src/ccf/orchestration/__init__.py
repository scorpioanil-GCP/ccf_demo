# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The Orchestration seam — `OrchestrationProtocol` (CLAUDE.md §8.1; D-IMPL-17/60).

SDK-defined extension. The Protocol lives here in ``/src``; drivers and the
in-SDK reference adapter live under ``runtime/ccf_runtime/orchestration/``.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.orchestration.protocol import OrchestrationProtocol

__ccf_mode__ = "algorithmic"

__all__ = ["OrchestrationProtocol"]
