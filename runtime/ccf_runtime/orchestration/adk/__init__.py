"""The Google ADK `OrchestrationProtocol` driver leg (D-IMPL-60 leg 2).

Lives under ``ccf_runtime/orchestration/adk/`` — never under
``ccf_runtime/adapters/adk/`` — per the D-06 module-tree split; the
``d06-orchestration-split`` lint enforces the boundary bidirectionally.
"""

from __future__ import annotations

from ccf_runtime.orchestration.adk.driver import AdkWorkflowDriver

__all__ = ["AdkWorkflowDriver"]
