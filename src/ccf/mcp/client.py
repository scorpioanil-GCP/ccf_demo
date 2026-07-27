"""The one shared MCP client (D-03, D-IMPL-13) and its sync bridge.

SDK-defined (CLAUDE.md §7.1 — MCP as a bidirectional surface); whitepaper §8.3
Pattern 3. Every §7.1 client edge goes through this module: L1 ingress, L4/L5
content acquisition, the ``mcp`` skill dispatch an agent invokes, and the
MCP-backed :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol`.

**One session per call, never a held session.** This is the load-bearing
decision and it is counter-intuitive, so it is recorded here with its reason.
The obvious design — open one ``ClientSession`` at construction, hold it, and
reuse it — was prototyped and **deadlocks**: ``ClientSession`` owns anyio task
groups whose lifetime does not survive being entered from ``anyio``'s
blocking-portal bridge (``anyio.from_thread``) and held across calls. The
prototype hung indefinitely and was killed at a 120 s timeout (06-RESEARCH.md
B3 / Pitfall 3). What works, and what this module does, is open the transport
and the session inside each call and close both on the way out. Against a
server configured ``stateless_http=True`` that is cheap (~48 ms measured), and
it removes session affinity as a failure mode entirely. ``anyio.from_thread``
is not imported here, and adding it would be reintroducing the deadlock.

**The sync bridge lives here, not in any one consumer.** ``ArtifactStoreProtocol``
is synchronous and so is ``Agent.invoke_skill``; both need the same async→sync
bridge, so it is a shared concern rather than the ArtifactStore's private
workaround (06-RESEARCH.md open question 3). The bridge owns exactly one
background event-loop thread for its lifetime and hands work to it with
``asyncio.run_coroutine_threadsafe``, which is what lets a synchronous caller
drive an async client without either blocking a running loop or paying a fresh
loop per call.

**Every call is bounded.** ``call_timeout_seconds`` is required — there is no
default, because a silently-chosen deadline is exactly the kind of value the
SDK does not get to pick (D-IMPL-38), and an unbounded ``.result()`` turns a
wedged server into a wedged caller.

The server URL is a deployment value supplied by the caller. This module holds
no URL, no host, and no port (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from collections.abc import Awaitable, Callable, Coroutine
from types import TracebackType
from typing import Any, TypeVar

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextResourceContents
from pydantic import AnyUrl

from ccf.mcp.errors import McpServerUnreachable, McpTimeout

__ccf_mode__ = "algorithmic"

__all__ = [
    "McpResourceClient",
    "SyncMcpBridge",
    "run_with_session",
]

T = TypeVar("T")

#: One caller-supplied unit of work against an initialized session.
SessionOperation = Callable[[ClientSession], Awaitable[T]]


async def run_with_session(
    *, url: str, operation: SessionOperation[T]
) -> T:
    """Open a session against ``url``, run ``operation``, close everything.

    The whole session lifetime is this function's ``async with`` stack, which
    is the point: the session is created, initialized, used, and torn down
    inside one task, so no task group outlives the task that entered it.

    Args:
        url: The MCP server's streamable-HTTP endpoint. A deployment value.
        operation: Receives an initialized session and returns its result.

    Returns:
        Whatever ``operation`` returned.

    Raises:
        McpServerUnreachable: the transport, handshake, or protocol exchange
            failed. Deliberately not narrowed by inspecting the message text —
            see :mod:`ccf.mcp.errors`.
    """
    try:
        async with streamablehttp_client(url) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await operation(session)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        raise McpServerUnreachable(
            f"MCP call against {url!r} did not complete: "
            f"{type(error).__name__}: {error}"
        ) from error


class SyncMcpBridge:
    """One background event loop, owned for the bridge's lifetime.

    The synchronous half of the sync↔async seam. Construct one per consumer
    (an ArtifactStore, a skill dispatcher), use it for that consumer's whole
    life, and :meth:`close` it — a bridge per call would pay thread startup on
    every request, and a process-global bridge would make two consumers share a
    failure.

    Args:
        call_timeout_seconds: The deadline every :meth:`run` enforces. Required:
            the SDK does not choose deadlines (D-IMPL-38).

    Note:
        Usable as a context manager, which is the shape that survives an
        exception in the caller's body without leaking the thread.
    """

    def __init__(self, *, call_timeout_seconds: float) -> None:
        self._call_timeout_seconds = call_timeout_seconds
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever,
            name="ccf-mcp-bridge",
            daemon=True,
        )
        self._thread.start()

    @property
    def call_timeout_seconds(self) -> float:
        """The deadline this bridge enforces on every call."""
        return self._call_timeout_seconds

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run ``coro`` on the background loop and return its result.

        Raises:
            McpTimeout: the call exceeded ``call_timeout_seconds``. Raised as a
                typed CCF failure rather than a bare
                ``concurrent.futures.TimeoutError`` so a caller catching the
                MCP error hierarchy catches this too.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(self._call_timeout_seconds)
        except concurrent.futures.TimeoutError as error:
            future.cancel()
            raise McpTimeout(
                f"MCP call exceeded its {self._call_timeout_seconds}s deadline"
            ) from error

    def close(self) -> None:
        """Stop the loop and join its thread. Idempotent."""
        if not self._thread.is_alive():
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(self._call_timeout_seconds)

    def __enter__(self) -> SyncMcpBridge:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class McpResourceClient:
    """Read MCP Resources from one server, synchronously or asynchronously.

    The consumer-facing surface of this module. Both halves are offered because
    both callers exist: the fabric core is synchronous (D-IMPL-04(b)) while
    ingestion and the runtime servers are not, and forcing either to wrap the
    other is how a nested-loop bug gets written.

    Args:
        url: The server's streamable-HTTP endpoint — a deployment value.
        bridge: The sync bridge :meth:`read_text` and :meth:`resource_uris`
            drive. Optional: an async-only consumer never needs one, and
            constructing a thread it will not use is waste. Not owned — the
            constructor of the bridge closes it.
    """

    def __init__(self, *, url: str, bridge: SyncMcpBridge | None = None) -> None:
        self._url = url
        self._bridge = bridge

    @property
    def url(self) -> str:
        """The endpoint this client reads from."""
        return self._url

    def _require_bridge(self) -> SyncMcpBridge:
        if self._bridge is None:
            raise McpServerUnreachable(
                f"synchronous access to {self._url!r} needs a SyncMcpBridge; "
                "this client was constructed without one, and manufacturing a "
                "background loop on demand would hide the thread's lifetime "
                "from the caller that has to close it"
            )
        return self._bridge

    async def read_text_async(self, uri: str) -> str:
        """Return the text contents of ``uri``, concatenated in server order.

        Text, not bytes: this is the reader for JSON-shaped resources such as
        the L6 egress product surface. A byte-exact reader belongs with the
        consumer that needs blob fidelity (06-RESEARCH.md Pitfall 4), because
        the decode is where the fidelity is won or lost and it should sit next
        to the contract that cares.

        Raises:
            McpServerUnreachable: the call did not complete.
        """

        async def operation(session: ClientSession) -> str:
            result = await session.read_resource(AnyUrl(uri))
            return "".join(
                contents.text
                for contents in result.contents
                if isinstance(contents, TextResourceContents)
            )

        return await run_with_session(url=self._url, operation=operation)

    async def resource_uris_async(self) -> tuple[str, ...]:
        """Return the URIs the server advertises, in server order.

        Raises:
            McpServerUnreachable: the call did not complete.
        """

        async def operation(session: ClientSession) -> tuple[str, ...]:
            listing = await session.list_resources()
            return tuple(str(resource.uri) for resource in listing.resources)

        return await run_with_session(url=self._url, operation=operation)

    def read_text(self, uri: str) -> str:
        """Synchronous :meth:`read_text_async`, bounded by the bridge deadline.

        Raises:
            McpServerUnreachable: no bridge was supplied, or the call failed.
            McpTimeout: the call exceeded the bridge's deadline.
        """
        return self._require_bridge().run(self.read_text_async(uri))

    def resource_uris(self) -> tuple[str, ...]:
        """Synchronous :meth:`resource_uris_async`, bounded the same way."""
        return self._require_bridge().run(self.resource_uris_async())
