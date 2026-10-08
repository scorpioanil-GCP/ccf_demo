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
them (INV-CH7-28) and records what it ran. Under design E2 that name set comes
from the plan's own Control Plane artifact,
:class:`~ccf.controlplane.artifacts.ProjectionRequirements`, and the product
class's ``required_operator_keys`` is a second, separately authored document;
a disagreement between the two fails at
:func:`~ccf.deployment.binder.refuse_operator_set_divergence` before the engine
runs, which is where **authorable** drift is caught. What the lineage
strict-equality gate (INV-CH7-47) compares downstream is the transcribed claim
against the engine's execution record — **assembly-path integrity** — because
the engine is a faithful transcriber of the plan rather than an independent
witness of it: it builds its invoked set and its steps in one loop over the
same operator plan. This paragraph previously said the two sets were "produced
independently"; the ruling of record correcting that is ``docs/DECISIONS.md``
**D-IMPL-86** (Dave, 2026-08-05), and CLAUDE.md §11 requires an SDK extension
to cite this project's own decision record rather than the whitepaper. What
holds without qualification: a plan that could reach into the engine and assert
what ran would turn that gate into a tautology, which is why nothing on this
Protocol offers it.

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

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
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

    **The withheld signal** (SEC-020; ``D-IMPL-370`` Q12 (a) constant-fill;
    SDK-defined, CLAUDE.md §11 and §8.2's indistinguishability posture). A
    projection conditioned on the perspective (whitepaper §7.5, INV-CH7-43)
    may decide that the principal asking must not be told about the subject at
    all. It says so with ``withheld=True`` and returns, as ``payload``, exactly
    what it returns for a subject it cannot see. The governed resolver then
    renders the product's debt, empty finding and TTL anchor from the SAME
    plan re-executed WITHOUT THE REQUEST SEED over the fabric as it stood
    BEFORE this request's acquisition — the plan's class seeds alone, the walk
    of an identifier that names nothing
    (``src/ccf/products/resolver.py::GovernedResolver``,
    ``src/ccf/projection/engine.py::ProjectionEngine.execute_without_request_seed``;
    the fabric before acquisition is ``D-IMPL-376`` (3), route A).

    **What that makes equal, and what it does not: SEC-020 is OPEN.** It is
    not a guarantee that a withheld subject cannot be told from a nonexistent
    one. Measured on the paved road's test fixture, the served product then
    matches a nonexistent subject's on both TTL anchors, for an acquisition
    keyed on the subject, on a fabric booted for the question, with no
    composite child about the subject. The re-run's operator registry is built
    from the same read before acquisition, so a similarity operator scores it
    against the corpus text before acquisition (``D-IMPL-378``); with an
    acquisition that refreshed the subject's similarity text, the two products
    were measured equal on a test fixture. Measured as still telling them
    apart: the answer's replay reference, whose record name hashes the real
    read; the record's dimension 1; composite children, which are not
    re-rendered; a fabric that outlives the question; and an acquisition not
    keyed on the subject. The security how-to, section 4.12, describes each.

    The signal is the ONLY way into that branch. An empty payload without it
    is a legitimately empty answer and keeps the debt and the finding its real
    view earned (``D-IMPL-242`` amendment 1: the finding is a positive
    statement about the view), so a withhold is never inferred from what Π
    returned.

    Hash-transparent at ``False`` (``D-IMPL-243``): every output written
    before the field existed is byte-identical.
    """

    plan_id: str
    payload: Mapping[str, Any]
    withheld: bool = Field(
        default=False, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


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

        A projection that must not tell ``perspective`` about the subject at
        all returns ``ProjectionOutput(withheld=True)`` with the payload it
        returns for a subject it cannot see; the product is then rendered as
        the same plan renders without the request seed, over the fabric as it
        stood before this request's acquisition (SEC-020, ``D-IMPL-371`` Q12
        (a), ``D-IMPL-376`` (3); :class:`ProjectionOutput`). Returning an empty payload
        without the signal is a legitimately empty answer, never a withhold.
        """
        ...
