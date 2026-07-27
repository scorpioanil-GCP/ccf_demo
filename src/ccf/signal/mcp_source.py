"""`MCPSourceAdapter` — the L1 MCP client ingress (XPRC-01).

SDK-defined (CLAUDE.md §7.1 — "MCP as ingress (L1)": the SDK ships an MCP
client that consumes external MCP servers and normalizes their outputs into
the L1 event envelope; CDC and MCP-ingress are complementary, CDC for
transactional capture, MCP for query-based acquisition of content-rich
systems). Whitepaper §8.3 Pattern 3 is the integration edge this extends —
the whitepaper commits Pattern 3 in the *export* direction only, so ingress
is CCF-SDK scope and is labelled as such rather than cited to the whitepaper
(CLAUDE.md §11).

**What this adapter is not.** It is not an MCP transport. It opens no session,
owns no event loop, and reimplements no part of the wire: every call goes
through the one shared client library, :mod:`ccf.mcp.client` (D-IMPL-13). A
second client in the SDK would be a second place for the session-lifetime
deadlock recorded in that module to be reintroduced.

**What this adapter cannot do.** It cannot write, and it cannot read the
graph either: this object holds no graph handle of any kind. That is a
property of the seam rather than of anyone's discipline —
``SignalSourceProtocol`` declares no such handle, so there is structurally
nowhere to put one (see the argument in
:mod:`ccf.signal.source`, which :class:`~ccf_runtime.cdc.adapter.CDCSourceAdapter`
relies on identically). Envelopes go to the caller, the caller hands them to
the L2 :class:`~ccf.assembly.worker.AssemblyWorker`, and that is the only
route into L3 (INV-CH7-10, single-writer, CLAUDE.md §10).

**The SSRF control (T-06-24).** Every address this adapter contacts is fixed
at construction, from Control Plane configuration: the server endpoint lives
on the injected :class:`~ccf.mcp.client.McpResourceClient`, and the resource
URIs come from the ``resources`` mapping the deployment supplies. Neither is
ever read from a decision-time argument or from a payload a previous read
returned. This is enforced by *shape* rather than by validation:
:meth:`envelopes` takes ``tenant_id`` and nothing else, and no public method
on this class accepts a URL, host, endpoint, or server. A fetched payload
cannot steer the next fetch because there is no parameter through which it
could.

This module holds no server address, no resource name, and no tenant
(CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping
from datetime import UTC, datetime

from mcp import ClientSession
from mcp.types import ReadResourceResult
from pydantic import AnyUrl

from ccf.mcp.client import McpResourceClient, run_with_session
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.signal.mcp_envelope_map import (
    McpMappingError,
    ResourceContents,
    to_envelope,
)

__ccf_mode__ = "algorithmic"

__all__ = ["MCPSourceAdapter"]


def _utc_now() -> datetime:
    """Wall-clock ingestion time, always tz-aware.

    The clock is an injected seam (see :class:`MCPSourceAdapter`) so a replayed
    acquisition produces identical envelopes; this is the default a deployment
    gets when it has no reason to override.
    """
    return datetime.now(UTC)


class MCPSourceAdapter:
    """Async :class:`~ccf.signal.source.SignalSourceProtocol` over MCP.

    Args:
        system_id: Logical identity of the source system this MCP server
            fronts. Identity, never location (INV-CH8-01) — the server's URL
            belongs to the injected client, and putting it here would bind the
            fabric's lineage to a deployment topology.
        client: The shared :class:`~ccf.mcp.client.McpResourceClient` for that
            server, constructed at the composition root against a Control
            Plane endpoint. Injected rather than built here, both because the
            SDK holds no URL (CINV-01) and because the endpoint must be fixed
            before any read (T-06-24).
        resources: The deployment's resource selection, mapping its own name
            for a resource to the URI to read. Fixed at construction for the
            same reason.
        clock: Ingestion-time source. Injected so a replayed acquisition
            produces identical envelopes; defaults to the UTC wall clock.

    Raises:
        ValueError: ``resources`` is empty. An adapter that would read nothing
            is a wiring mistake presented as a working ingress, and guessing
            a default selection is the silent default D-IMPL-38 forbids.

    Note:
        There is no ``tenant_id`` on the constructor: tenancy is an argument of
        :meth:`envelopes`, keyword-only, so one adapter over a shared MCP
        source cannot leak an emission into the wrong tenant by positional
        accident (INV-CH7-16, T-06-26, D-23 multi-principal).
    """

    def __init__(
        self,
        *,
        system_id: str,
        client: McpResourceClient,
        resources: Mapping[str, str],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not resources:
            raise ValueError(
                "MCPSourceAdapter needs at least one resource to read; the "
                "selection is deployment configuration and the SDK does not "
                "invent one"
            )
        self._system_id = system_id
        self._client = client
        self._resources = dict(resources)
        self._clock = clock or _utc_now

    def source_identity(self) -> SourceIdentity:
        """The logical identity of the system this adapter reads."""
        return SourceIdentity(system_id=self._system_id)

    async def _read(self, uri: str) -> ReadResourceResult:
        """Read one configured resource through the shared client library.

        The session is opened, initialized, used and closed inside
        :func:`~ccf.mcp.client.run_with_session` — this adapter constructs
        none of that itself. ``uri`` is always a value from
        ``self._resources``; it is never a caller's argument.
        """

        async def operation(session: ClientSession) -> ReadResourceResult:
            return await session.read_resource(AnyUrl(uri))

        return await run_with_session(url=self._client.url, operation=operation)

    async def envelopes(self, *, tenant_id: str) -> AsyncIterator[SignalEnvelope]:
        """Yield one validated envelope per content item, for ``tenant_id``.

        Resources are read in the deployment's declared order, and each item of
        each result becomes one envelope. A content item that fails to
        normalize raises :class:`~ccf.signal.mcp_envelope_map.McpMappingError`
        carrying which resource and which item failed: content the fabric
        cannot represent stops the acquisition rather than leaving a hole in
        the graph nobody can see (T-06-25).

        Args:
            tenant_id: Tenant scope for this drain. Keyword-only, per-call, and
                the *only* argument — see the SSRF note in the module
                docstring.

        Raises:
            McpMappingError: a delivered content item is malformed.
            ccf.mcp.errors.McpServerUnreachable: the read did not complete.
        """
        for resource_name, uri in self._resources.items():
            result = await self._read(uri)
            for position, contents in enumerate(result.contents):
                item: ResourceContents = contents
                try:
                    yield to_envelope(
                        item,
                        tenant_id=tenant_id,
                        system_id=self._system_id,
                        resource_name=resource_name,
                        ingestion_timestamp=self._clock(),
                    )
                except McpMappingError as error:
                    raise McpMappingError(
                        f"resource {resource_name!r}, content item "
                        f"{position}: {error}"
                    ) from error
