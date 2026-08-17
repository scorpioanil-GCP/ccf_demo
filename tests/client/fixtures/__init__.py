"""Where the client suite's fixture deployment and its server program live.

The deployment under ``deployment/`` is **data only** — ``D-IMPL-141``
Amendment A.3 grants it exactly one Python module, its projection, and
``tests/client/test_data_only_deployment.py`` refuses a second by name. So the
deployment's MCP server program sits **here**, one level up, and an
``mcp+stdio`` binding names the two separately.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["STDIO_SERVER"]

#: The fixture deployment's own MCP server program. Named once so the adapter
#: tests and the conformance binding launch the same thing.
STDIO_SERVER = Path(__file__).parent / "stdio_server.py"
