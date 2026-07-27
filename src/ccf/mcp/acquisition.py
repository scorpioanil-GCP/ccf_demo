"""``McpContentAcquirer`` — the L4/L5 client role of the one shared MCP client.

SDK-defined (CLAUDE.md §7.1, bullet 2: "MCP as ingress for content acquisition
(L4–L5)"); whitepaper §6.6 (search-inference recursion). This is the reference
:class:`~ccf.projection.acquisition.ContentAcquirer`.

**Three client roles, one client library (D-03, D-IMPL-13).** This module is the
*decision-time acquisition* role. It is deliberately not the L1 ingress role
(which normalizes an external response into a ``SignalEnvelope`` for L2 to
write) and not the ArtifactStore role (which resolves versioned artifacts by
exact address). The roles differ in trust posture and in destination: what this
module fetches terminates in a projection payload and enters the graph nowhere.
They share :mod:`ccf.mcp.client` and nothing else.

**No session, no loop, no bridge of its own.** Sessions are opened per call by
:func:`ccf.mcp.client.run_with_session`, and the sync bridge is constructed by
the deployment and handed in through the clients. A second bridge here would be
a second background loop for the same process, and the held-session variant
deadlocks (06-RESEARCH.md B3).

**Addresses come from construction; selectors come from the plan.** The
constructor takes resolved Control Plane sources — one already-addressed client
per source key. No public method accepts a URL, a host, or a scheme at call
time, so a projection plan (or a payload a previous acquisition returned)
cannot steer this process at a network address it was not configured for. The
SSRF posture is a property of the shape, not of a validation step someone could
forget to call.

**Tenancy is a per-call argument.** ``{tenant}`` in a selector is substituted
from the ``tenant_id`` passed to :meth:`acquire`, never from constructor state,
so one acquirer serving two principals cannot cross them (D-23).

**This module interprets nothing it fetches.** It returns opaque text with a
content address. Meaning is Π's job, and Π is the semantic stage
(CLAUDE.md §11). No LLM client is imported here and the lint enforces it.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from ccf.mcp.client import McpResourceClient
from ccf.projection.acquisition import (
    AcquiredContent,
    ContentRequest,
    UnknownContentSource,
)

__ccf_mode__ = "algorithmic"

__all__ = ["McpContentAcquirer", "TENANT_PLACEHOLDER"]

#: The one substitution a selector may carry. Mechanism, not a domain value:
#: which resources a source exposes and how they are named is the deployment's
#: vocabulary, and this is only how the per-call tenant reaches it.
TENANT_PLACEHOLDER = "{tenant}"


class McpContentAcquirer:
    """Acquires declared content from configured MCP sources at decision time.

    Args:
        sources: Control Plane source key → an already-addressed
            :class:`~ccf.mcp.client.McpResourceClient`. Each client must carry
            a :class:`~ccf.mcp.client.SyncMcpBridge`, because the fabric core
            is synchronous (D-IMPL-04(b)) and this seam is called from inside
            the projection engine's synchronous execution. The bridge is owned
            by whoever built it; this class does not close it.
    """

    def __init__(self, *, sources: Mapping[str, McpResourceClient]) -> None:
        self._sources = dict(sources)

    @property
    def source_keys(self) -> tuple[str, ...]:
        """The Control Plane source keys this acquirer can resolve, sorted."""
        return tuple(sorted(self._sources))

    def acquire(
        self,
        *,
        requests: tuple[ContentRequest, ...],
        tenant_id: str,
    ) -> Mapping[str, AcquiredContent]:
        """Fetch every request, keyed by ``request_key``, in declaration order.

        Raises:
            UnknownContentSource: a request named a source key this acquirer
                holds no client for. Refused rather than skipped — see
                :class:`~ccf.projection.acquisition.AcquisitionError`.
            ccf.mcp.errors.McpServerUnreachable: the call did not complete.
            ccf.mcp.errors.McpTimeout: the call outran the bridge's deadline.
        """
        acquired: dict[str, AcquiredContent] = {}
        for request in requests:
            client = self._sources.get(request.source_key)
            if client is None:
                raise UnknownContentSource(
                    f"request {request.request_key!r} names source "
                    f"{request.source_key!r}, which this acquirer holds no "
                    f"configuration for; it knows {self.source_keys}"
                )
            selector = request.selector.replace(TENANT_PLACEHOLDER, tenant_id)
            acquired[request.request_key] = AcquiredContent.of(
                request=request,
                content=client.read_text(selector),
            )
        return acquired
