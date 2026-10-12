# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""``ccf_runtime.mcp`` — the SDK's MCP *server* roles (CLAUDE.md §7.1).

SDK-defined; whitepaper §8.3 Pattern 3. Servers bind ports and therefore live
in the runtime host package, never in ``/src``: the library is what a caller
imports, and importing a library must not be able to start listening.

The server roles are deliberately separate modules with separate trust
postures — L6 egress serves gate-admitted Context Products to consumers outside
the fabric, while artifact persistence serves immutable artifacts inside the
tenant boundary. Collapsing them into one server would give one bind address
two trust postures.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
