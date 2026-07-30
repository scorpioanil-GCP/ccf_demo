"""The LangGraph `OrchestrationProtocol` driver leg (D-IMPL-60 leg 1).

Lives under ``ccf_runtime/orchestration/langgraph/`` — never under
``ccf_runtime/adapters/langgraph/`` — per the D-06 module-tree split; the
``d06-orchestration-split`` lint enforces the boundary bidirectionally.
"""

from __future__ import annotations

from ccf_runtime.orchestration.langgraph.driver import LangGraphWorkflowDriver

__all__ = ["LangGraphWorkflowDriver"]
