"""The Orchestration seam — `OrchestrationProtocol` (CLAUDE.md §8.1; D-IMPL-17/60).

SDK-defined extension. The Protocol lives here in ``/src``; drivers and the
in-SDK reference adapter live under ``runtime/ccf_runtime/orchestration/``.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.orchestration.protocol import OrchestrationProtocol

__ccf_mode__ = "algorithmic"

__all__ = ["OrchestrationProtocol"]
