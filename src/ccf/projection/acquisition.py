"""Decision-time content acquisition at L4/L5 — the seam, not the transport.

SDK-defined (CLAUDE.md §7.1, "MCP as ingress for content acquisition (L4–L5)");
whitepaper §6.6 (the search-inference recursion, where an interpretation needs
content the graph does not hold and goes and gets it). This module declares the
seam; :mod:`ccf.mcp.acquisition` is the reference implementation over the one
shared MCP client, and a deployment may supply any other.

**Why the seam is here and not on ``Operator``.** ``Operator.apply`` is pure by
contract — "no writes, no I/O against the graph, no clock reads"
(:mod:`ccf.operators.base`) — and that sentence is load-bearing for
composition-preservation. An operator that could fetch would make ``(A∘B)(G) =
A(B(G))`` false the moment a remote source moved. So acquisition is an *engine
stage* between the operator plan and Π, and the purity contract stays true.

**Why nothing here holds a graph handle.** Acquired content terminates in the
projection payload. It is not written, not merged into the view, and not
promoted to an entity. If a deployment wants acquired content in the graph, it
enters through L1/L2 like everything else — the single-writer invariant
(CLAUDE.md §10) is not negotiated at L5. That is why
:meth:`ContentAcquirer.acquire` *returns values*: a seam that returned nothing
and wrote instead would be a second writer.

**Why a request carries a key and never an address.** A projection plan is
deployment-authored data; if a plan could name a host, a plan (or a payload a
previous acquisition returned) would decide what this process connects to,
which is server-side request forgery with extra steps. ``ContentRequest``
carries a Control Plane *source key* and a resource *selector*; the acquirer
resolves the key to an address from configuration it was constructed with, and
no public method accepts a URL, host, or scheme at call time.

**Why acquisition is opaque.** Acquisition fetches; it does not interpret. Π
interprets, and Π is where the algorithmic⇄semantic alternation puts the
semantic stage (CLAUDE.md §11, whitepaper §7.6.6). This module is
``__ccf_mode__ = "algorithmic"`` and holds no LLM client; the lint enforces it.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

__ccf_mode__ = "algorithmic"

__all__ = [
    "AcquiredContent",
    "AcquirerNotConfigured",
    "AcquisitionError",
    "ContentAcquirer",
    "ContentAcquiringPlan",
    "ContentRequest",
    "ContentUnsatisfied",
    "UndeclaredAcquisition",
    "UnknownContentSource",
]


class AcquisitionError(Exception):
    """Base of the refusals the acquisition stage raises.

    Every failure below is a refusal, never a degraded success. A projection
    handed *absent* content it declared it needed would interpret a gap as a
    fact, which is precisely the debt-blind decision the fabric exists to
    prevent (whitepaper §7.7). There is no "proceed without it" path.
    """


class AcquirerNotConfigured(AcquisitionError):
    """The plan declares content and no acquirer was injected.

    Raised rather than skipping the stage: a plan that declared a requirement
    and silently got none would be served as if it had been satisfied.
    """


class UnknownContentSource(AcquisitionError, KeyError):
    """A request named a source key the acquirer holds no configuration for.

    Also a ``KeyError`` — this is a lookup miss in the Control Plane's source
    table, and a caller reading it as such is reading it correctly.
    """


class UndeclaredAcquisition(AcquisitionError):
    """The acquirer returned content the plan never declared.

    The declared set and the resolved set are compared rather than merged, for
    the same reason the lineage gate compares the declared and engine-resolved
    operator sets (INV-CH7-47): an acquirer that could inject an extra item
    would be feeding Π material with no declaration to audit it against.
    """


class ContentUnsatisfied(AcquisitionError):
    """A declared request came back unsatisfied."""


class ContentRequest(CCFContract):
    """A *reference* to content needed at decision time. Never an address.

    Attributes:
        request_key: The name the plan will look the result up under. Local to
            the plan, so two requests against one source stay distinguishable.
        source_key: Control Plane key of the source to resolve. The acquirer
            maps this to an address; this contract never carries one.
        selector: What to ask that source for — a resource selector expressed
            in the source's own vocabulary. ``{tenant}``, where present, is
            substituted by the acquirer at call time from the per-call tenant,
            never from constructor state (D-23).
    """

    request_key: str
    source_key: str
    selector: str


class AcquiredContent(CCFContract):
    """One fetched item, its content address, and the request that got it.

    Frozen and opaque. The ``content_hash`` is what makes replay determinism
    checkable: a replay re-feeds this recorded item rather than re-fetching a
    remote resource that may have moved (INV-CH7-31), and the hash is how a
    re-feed that carried different bytes is caught.
    """

    request: ContentRequest
    content: str
    content_hash: str

    @classmethod
    def of(cls, *, request: ContentRequest, content: str) -> AcquiredContent:
        """Build an entry, computing the content address canonically."""
        return cls(
            request=request,
            content=content,
            content_hash=content_hash(content),
        )

    def rehash(self) -> str:
        """The content address this item's bytes actually have now."""
        return content_hash(self.content)


@runtime_checkable
class ContentAcquirer(Protocol):
    """Resolves declared content requests into fetched items.

    Read-only by shape: it takes no graph handle and returns values, exactly as
    :class:`~ccf.operators.base.Operator` does. Nothing an acquirer returns can
    reach L3 except by being ingested through L1/L2 as new signal.
    """

    def acquire(
        self,
        *,
        requests: tuple[ContentRequest, ...],
        tenant_id: str,
    ) -> Mapping[str, AcquiredContent]:
        """Fetch ``requests`` for ``tenant_id``, keyed by ``request_key``.

        ``tenant_id`` is a **per-call** argument, not constructor state. One
        acquirer serves every principal in the process, so tenancy that lived
        on the instance would make two principals share a fetch scope (D-23).

        Raises:
            UnknownContentSource: a request named a source this acquirer holds
                no configuration for.
        """
        ...


@runtime_checkable
class ContentAcquiringPlan(Protocol):
    """A projection that declares content it needs acquired at decision time.

    A **separate** Protocol rather than a widened
    :class:`~ccf.projection.plan.ProjectionPlan`, so every projection written
    against the plain seam still conforms unchanged and the engine detects the
    capability structurally — the same argument ``plan.py`` makes for having no
    base class. The two are disjoint statically (this ``invoke`` takes an
    argument the other does not), which is what lets the engine narrow a union
    cleanly instead of guessing.

    **``required_content()`` is a declaration, not a request** — the identical
    discipline ``required_operators()`` carries. The plan names what it needs;
    the *engine* resolves it through the injected acquirer and records what was
    resolved. A plan that could fetch for itself would be its own provenance
    authority, and the record of what a decision read would be written by the
    thing being audited.
    """

    @property
    def plan_id(self) -> str:
        """Stable identity of this plan; binds a product to its Π."""
        ...

    def required_operators(self) -> tuple[str, ...]:
        """Registry keys of the operators this interpretation depends on."""
        ...

    def required_content(self) -> tuple[ContentRequest, ...]:
        """Content references this interpretation depends on.

        Order is the resolution order the engine records in
        ``ExecutionResult.acquisitions``.
        """
        ...

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
        acquired_content: Mapping[str, AcquiredContent],
    ) -> ProjectionOutput:
        """Interpret the operator-produced state plus the acquired content.

        Identical to :meth:`ccf.projection.plan.ProjectionPlan.invoke` but for
        the added ``acquired_content`` mapping, keyed by ``request_key``.

        ``GraphView`` is a frozen read value, not a handle: naming it here
        gives this module no capacity to write, and the writer type is absent
        from this module entirely (CLAUDE.md §10).
        """
        ...
