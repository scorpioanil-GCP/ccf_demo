"""Typed MCP client failures — absence is not an outage.

SDK-defined (CLAUDE.md §7.1); whitepaper §8.3 Pattern 3. The hierarchy mirrors
:mod:`ccf.artifacts.protocol`'s deliberately, because the argument is the same
one: a caller must be able to distinguish "the resource this decision was
recorded against is not present at that server" from "that server is
unreachable". **The two demand opposite responses, and a replay that conflated
them would report a missing record as an outage** — the first is a fact about
the decision under replay, the second is a fact about today's network.

**Discrimination comes from a structured signal, never from a message.**
``McpError``'s text is a stringified server-side exception with no typed code
(06-RESEARCH.md Pitfall 2: a missing templated resource surfaced as
``Error creating resource from template: 'deadbeef'``). String-matching it
would bind CCF's absent/unreachable distinction to another project's
exception-formatting, so a server that reworded its error would silently start
reporting missing artifacts as outages. A caller raising
:class:`McpResourceAbsent` must therefore have a structured basis for it — a
declared MCP error code, a typed metadata resource, or a typed structured tool
result. This module ships no message parser and no ``except McpError`` handler,
so there is nothing here to reach for instead.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__ = [
    "McpClientError",
    "McpResourceAbsent",
    "McpServerUnreachable",
    "McpTimeout",
    "McpToolFailed",
]


class McpClientError(Exception):
    """Base of the MCP client's typed failures.

    Typed rather than bare so the two questions a caller actually has —
    "is the thing there?" and "can I reach the server?" — are answered by the
    exception's *type*, which survives a vendor rewording its message text.
    """


class McpResourceAbsent(McpClientError, KeyError):
    """The server is reachable and reports no such resource.

    Also a ``KeyError``, matching :class:`ccf.artifacts.protocol.ArtifactNotFound`
    so a caller written against the mapping-shaped reading of a lookup keeps
    working across both substrates.

    Raise this only on a structured signal. If all that is known is that a call
    failed, that is :class:`McpServerUnreachable` — over-reporting absence is
    the dangerous direction, because absence is the answer a replay records as
    a fact about the past.
    """


class McpServerUnreachable(McpClientError):
    """The call did not complete: transport, handshake, or protocol failure.

    Deliberately the fallback. An error the client cannot classify is an
    outage, not an absence, because an outage invites a retry while a
    misreported absence gets written down.
    """


class McpTimeout(McpServerUnreachable, TimeoutError):
    """A call exceeded its caller-supplied deadline.

    A subclass of :class:`McpServerUnreachable` — a call that did not come back
    in time did not come back — and of the builtin ``TimeoutError``. Named
    separately because the sync facade bounds every call with an explicit
    timeout (see :mod:`ccf.mcp.client`), and a test asserting that the bound
    fires needs to say so without also accepting a connection refusal.
    """


class McpToolFailed(McpClientError):
    """The server ran a tool call and reported it as an error (`D-IMPL-340`).

    Distinct from :class:`McpServerUnreachable`: the call *completed* — the
    session was opened, the tool ran — and the server chose to answer with
    ``isError``. For the SDK's own product door that text is an opaque
    ``ccf-runtime-failure:<id>`` or a protocol-native entitlement denial
    (``D-IMPL-253`` Q20); this exception carries it verbatim as ``text`` so a
    consumer can record *which* failure without parsing prose it was never
    meant to read.
    """

    def __init__(self, tool: str, text: str) -> None:
        super().__init__(f"tool {tool!r} reported an error: {text}")
        self.tool = tool
        self.text = text
