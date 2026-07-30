"""The Claude Agent SDK harness adapter (CLAUDE.md §7.3; D-IMPL-24).

One of the v0 reference bindings of
:class:`~ccf.harness.protocol.HarnessAdapterProtocol`. See
:mod:`ccf_runtime.adapters.claude_agent.adapter` for the four-seam binding and
for what this adapter deliberately cannot do.

Importing this package imports ``claude_agent_sdk``. That is legal exactly
here and nowhere else outside ``ccf_runtime.adapters.*`` (``cinv02-harness``,
D-IMPL-53), and it is why the conformance leg for this harness is guarded by
the ``claude-agent`` extra rather than assumed present.
"""

from __future__ import annotations

from ccf_runtime.adapters.claude_agent.adapter import (
    HARNESS_ID,
    ClaudeAgentAdapter,
)

__all__ = ["HARNESS_ID", "ClaudeAgentAdapter"]
