# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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
