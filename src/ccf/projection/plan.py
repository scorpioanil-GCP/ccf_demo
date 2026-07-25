"""``ProjectionPlan`` — the structural interface of Π (INV-CH7-41).

Whitepaper §7.5; DESIGN.md §2B.2 and the D-IMPL-49 signature ruling.

**Structural, not nominal.** Any type exposing ``required_operators()`` and
``invoke()`` is a projection. There is no base class to inherit and no registry
decorator to remember, because a deployment's projections are *its* code — the
SDK's business is the shape of the seam, not the ancestry of what plugs into
it. ``typing.Protocol`` is exactly this commitment expressed in the type
system.

**``required_operators()`` is a declaration, not a request.** The plan names
which operators its interpretation depends on; the engine resolves and orders
them (INV-CH7-28) and records what it actually ran. The declared set and the
engine-resolved set are then compared by the lineage strict-equality gate
(INV-CH7-47) — which is only a meaningful check because the two are produced
independently. A plan that could reach into the engine and assert what ran
would turn that gate into a tautology.

**Perspective is an input to invocation, not a state of the plan.** The tuple
``(perspective, context_product_class, selection_params)`` deterministically
selects a plan (D-IMPL-49); the perspective then conditions the interpretation.
Projection is stateless by invariant — no write locks, no in-process cache
(INV-CH7-73(b)).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput

__ccf_mode__ = "algorithmic"

__all__ = ["Perspective", "ProjectionOutput", "ProjectionPlan"]


class Perspective(CCFContract):
    """The role-conditioning tuple Π interprets under.

    Whitepaper §7.5 (role-shaped views condition at runtime, INV-CH7-43);
    specialization axis 3 in CLAUDE.md §6.2, which is why this type is small
    and stable: the agent framework binds *to* it in I.2 rather than replacing
    it.

    ``principal_id`` is who is asking and ``role`` is in what capacity. Both
    land verbatim in replay dimension 4 (Perspective Conditioning), so a
    decision can be re-read against the viewpoint that produced it rather than
    against today's.
    """

    principal_id: str
    role: str


class ProjectionOutput(CCFContract):
    """What a projection produced, before it becomes a servable product.

    Deliberately not a ``ContextProductContract``: the gates (L6) are the only
    construction path of a servable product, so Π returns the *payload plus its
    plan identity* and the delivery layer decides whether it may be served.
    A projection that could mint its own servable product would be its own
    validator.
    """

    plan_id: str
    payload: Mapping[str, Any]


@runtime_checkable
class ProjectionPlan(Protocol):
    """A registered projection: what it needs, and what it makes of it."""

    @property
    def plan_id(self) -> str:
        """Stable identity of this plan; binds a product to its Π."""
        ...

    def required_operators(self) -> tuple[str, ...]:
        """Registry keys of the operators this interpretation depends on.

        Order is not significant — the engine imposes the dependency order
        (Policy → Similarity → Temporal → Traversal). Declaring an order here
        would let a plan reorder Policy after Similarity, which is the one
        ordering the fabric may never permit (INV-CH7-26).
        """
        ...

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        """Interpret the operator-produced state for ``perspective``.

        ``view`` is the final composed view; ``operator_outputs`` gives access
        to individual intermediates and their provenance, which is what lets a
        projection read operator-produced metadata during invocation
        (INV-CH7-42) without re-running anything.
        """
        ...
