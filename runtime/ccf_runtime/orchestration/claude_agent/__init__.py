"""The Claude Agent SDK `OrchestrationProtocol` driver leg (D-IMPL-60 leg 3).

Lives under ``ccf_runtime/orchestration/claude_agent/`` — never under the
harness-adapter tree — per the D-06 module-tree split; the
``d06-orchestration-split`` lint enforces the boundary bidirectionally.
"""

from __future__ import annotations

from ccf_runtime.orchestration.claude_agent.driver import (
    ClaudeAgentWorkflowDriver,
)

__all__ = ["ClaudeAgentWorkflowDriver"]
