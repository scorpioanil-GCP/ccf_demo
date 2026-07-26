"""Two-stage execution: the operator plan, then Π (INV-CH7-42).

Whitepaper §7.4–§7.5; DESIGN.md §2B.1 (planner) and §2B.2 (two-stage
execution).

**Stage 1 — what is true.** The engine performs the fabric's single as-of read
and hands the plan's declared operator keys to
:func:`ccf.operators.planner.build_operator_plan`, which resolves them against
the registry and imposes the canonical dependency order. The engine then runs
that sequence through a per-execution
:class:`~ccf.operators.planner.IntermediateCache`, threading each intermediate
into the next and accumulating the provenance chain. This stage is
principal-agnostic, which is exactly why memoizing it is sound (D-IMPL-36, I.1
scope: per-execution only).

The registry, the ordering rule, and the composite-operator algebra live in
:mod:`ccf.operators` rather than here. The engine is the thing that *runs* a
plan; it is not the thing that decides what a plan is, and keeping the two
apart is what lets the composition-preservation harness assert against the
same composition path the engine takes.

**Stage 2 — what that truth means here.** Π is invoked over the composed view
with the intermediates and the perspective. Principal-conditioned, stateless.

**The engine-resolved operator set is the engine's own record of what ran.** It
is built from execution, not copied from the plan's declaration, which is what
makes the L6 lineage strict-equality gate a real comparison rather than a
tautology (INV-CH7-47).

The registry is populated by explicit boot-time ``register`` calls at the
composition root (D-IMPL-37 — no import-side-effect registration in v0), and a
duplicate key is a boot failure rather than a runtime surprise (INV-CH7-29).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphReader, GraphView
from ccf.operators.base import OperatorOutput, OperatorProvenance
from ccf.operators.planner import IntermediateCache, build_operator_plan
from ccf.operators.registry import (
    DuplicateOperatorKey,
    OperatorRegistry,
    UnregisteredOperator,
)
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan

__ccf_mode__ = "algorithmic"

__all__ = [
    "DuplicateOperatorKey",
    "ExecutionResult",
    "ExecutionStep",
    "OperatorRegistry",
    "ProjectionEngine",
    "UnregisteredOperator",
]


class ExecutionStep(CCFContract):
    """One executed stage of the operator plan, in execution order.

    Lands verbatim in replay dimension 5 (Content Generation Path): the
    sequence of steps *is* how the product came to be, and a record that named
    only the operators without their order could not distinguish a
    Policy-before-Similarity run from the forbidden inverse.
    """

    operator_key: str
    category: str
    parameter_hash: str


class ExecutionResult(CCFContract):
    """Everything one two-stage execution produced.

    Attributes:
        plan_id: Identity of the projection that ran.
        operators_invoked: The **engine-resolved** operator set — what ran, as
            observed by the thing that ran it.
        steps: Execution order, for replay dimension 5.
        provenance: Provenance chain of the final intermediate, or ``None``
            when the plan declared no operators. ``None`` rather than an empty
            chain: the empty-operator guard exists precisely to refuse this
            case at L6, and papering over it here would remove its subject.
        projection: Π's output.
        view: The final composed view. Retained because the snapshot watermark
            and touched-substate manifest of replay dimension 1 are computed
            from it (D-IMPL-06 — a logical snapshot, never a physical copy).
    """

    plan_id: str
    operators_invoked: frozenset[str]
    steps: tuple[ExecutionStep, ...]
    provenance: OperatorProvenance | None
    projection: ProjectionOutput
    view: GraphView

    def touched_entities(self) -> tuple[str, ...]:
        """Entity URIs the execution actually touched, sorted."""
        return tuple(sorted(record.claim.entity_uri for record in self.view.entities))

    def touched_relationships(self) -> tuple[str, ...]:
        """Relationship keys the execution actually touched, sorted."""
        return tuple(sorted(edge.relationship_key for edge in self.view.relationships))

    def state_watermark(self) -> str:
        """Content address of the composed view — the store-state watermark.

        D-IMPL-06: the snapshot is logical. This hash plus the tenant, the
        temporal boundary, and the touched-substate manifest identify the graph
        state a decision was made against, without copying a byte of it.
        """
        return content_hash(self.view)


class ProjectionEngine:
    """Runs the operator plan and then Π, in that order, once.

    Args:
        reader: Read-only graph access. There is no writer parameter on this
            constructor, and that absence is the point — L4/L5 are structurally
            incapable of writing (INV-CH7-11, single-writer per CLAUDE.md §10).
        registry: The boot-populated operator registry.
    """

    def __init__(self, *, reader: GraphReader, registry: OperatorRegistry) -> None:
        self._reader = reader
        self._registry = registry

    def execute(
        self,
        *,
        plan: ProjectionPlan,
        perspective: Perspective,
        tenant_id: str,
        temporal_boundary: datetime,
    ) -> ExecutionResult:
        """Execute ``plan`` for ``perspective`` as of ``temporal_boundary``.

        ``temporal_boundary`` is supplied by the caller and threaded into every
        operator. Nothing in this path reads a clock (04-RESEARCH.md
        anti-patterns): a replay feeds the boundary the original decision used
        and gets the original answer.

        Raises:
            UnregisteredOperator: the plan declared a key the registry does not
                hold.
        """
        view = self._reader.as_of(tenant_id=tenant_id, at=temporal_boundary)
        operator_plan = build_operator_plan(
            registry=self._registry, required_operators=plan.required_operators()
        )
        cache = IntermediateCache()
        outputs: dict[str, OperatorOutput] = {}
        steps: list[ExecutionStep] = []
        chain: tuple[OperatorProvenance, ...] = ()

        for operator in operator_plan.operators:
            output = cache.run(
                operator,
                view=view,
                tenant_id=tenant_id,
                temporal_boundary=temporal_boundary,
                upstream=chain,
            )
            view = output.view
            outputs[operator.key] = output
            chain = (output.provenance,)
            steps.append(
                ExecutionStep(
                    operator_key=operator.key,
                    category=operator.category,
                    parameter_hash=output.provenance.parameter_hash,
                )
            )

        projection = plan.invoke(
            view=view,
            operator_outputs=outputs,
            perspective=perspective,
            temporal_boundary=temporal_boundary,
        )
        return ExecutionResult(
            plan_id=plan.plan_id,
            operators_invoked=frozenset(outputs),
            steps=tuple(steps),
            provenance=chain[0] if chain else None,
            projection=projection,
            view=view,
        )
