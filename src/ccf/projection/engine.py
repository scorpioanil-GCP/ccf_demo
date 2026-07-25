"""Two-stage execution: the operator plan, then Π (INV-CH7-42).

Whitepaper §7.4–§7.5; DESIGN.md §2B.1 (planner) and §2B.2 (two-stage
execution).

**Stage 1 — what is true.** The engine performs the fabric's single as-of read,
resolves the plan's declared operator keys against the registry, orders them
into the canonical dependency order, and runs them in sequence, threading each
intermediate into the next and accumulating the provenance chain. This stage is
principal-agnostic and therefore memoizable (the deterministic intermediate
cache of D-IMPL-36 attaches here in a later plan).

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
from ccf.operators.base import (
    CATEGORY_ORDER,
    Operator,
    OperatorOutput,
    OperatorProvenance,
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


class DuplicateOperatorKey(ValueError):
    """An operator key was registered twice (INV-CH7-29 — a boot failure)."""


class UnregisteredOperator(LookupError):
    """A plan declared an operator key the registry does not hold."""


class OperatorRegistry:
    """Boot-time operator registry with fail-fast duplicate detection.

    D-IMPL-37: registration is an explicit call at the composition root. No
    entry points, no decorators, no import side effects — a registry populated
    by imports has a population that depends on import order, and an operator
    plan is only deterministic if the registry it resolves against is.
    """

    def __init__(self) -> None:
        self._operators: dict[str, Operator] = {}

    def register(self, operator: Operator) -> None:
        """Register ``operator`` under its own key.

        Raises:
            DuplicateOperatorKey: the key is already registered. Deliberately
                fatal: two operators answering to one key means every plan
                naming it is ambiguous, and silently keeping one of them makes
                the ambiguity invisible.
        """
        if operator.key in self._operators:
            raise DuplicateOperatorKey(
                f"operator key {operator.key!r} is already registered"
            )
        self._operators[operator.key] = operator

    def resolve(self, key: str) -> Operator:
        """Return the operator registered under ``key``.

        Raises:
            UnregisteredOperator: nothing is registered under ``key``.
        """
        try:
            return self._operators[key]
        except KeyError:
            raise UnregisteredOperator(
                f"no operator registered under {key!r}"
            ) from None

    def keys(self) -> tuple[str, ...]:
        """Every registered key, sorted — introspection for the CLI and tests."""
        return tuple(sorted(self._operators))


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

    def _ordered(self, plan: ProjectionPlan) -> tuple[Operator, ...]:
        """Resolve the plan's declared keys into dependency order.

        Sorting by category index and then by key gives a total order, so two
        operators of the same category run in a stable sequence rather than in
        whatever order the plan happened to list them.

        Raises:
            UnregisteredOperator: a declared key is not registered.
        """
        operators = [self._registry.resolve(key) for key in plan.required_operators()]
        return tuple(
            sorted(
                operators,
                key=lambda op: (CATEGORY_ORDER.index(op.category), op.key),
            )
        )

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
        """
        view = self._reader.as_of(tenant_id=tenant_id, at=temporal_boundary)
        outputs: dict[str, OperatorOutput] = {}
        steps: list[ExecutionStep] = []
        chain: tuple[OperatorProvenance, ...] = ()

        for operator in self._ordered(plan):
            output = operator.apply(
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
