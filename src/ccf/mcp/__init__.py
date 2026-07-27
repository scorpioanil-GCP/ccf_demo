"""``ccf.mcp`` — the one shared MCP client surface (D-03, D-IMPL-13).

SDK-defined (CLAUDE.md §7.1, "MCP as a bidirectional integration surface");
whitepaper §8.3 Pattern 3 ("Context Product export"), which the SDK widens from
export-only to a surface used at L1 ingress, L4/L5 content acquisition, L6
egress, the Experience Layer, and artifact persistence.

**One client library, not one per edge.** The five §7.1 edges differ in trust
posture and in what they carry, not in how a session is opened. Giving each
edge its own client would mean five places to get the session lifetime wrong,
and the session lifetime is precisely where this gets subtle (see
:mod:`ccf.mcp.client`).

**Client only.** Servers are runtime concerns and live in ``ccf_runtime`` —
``/src`` never binds a port.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
