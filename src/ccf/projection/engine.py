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

from collections.abc import Mapping
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
from ccf.projection.acquisition import (
    AcquiredContent,
    AcquirerNotConfigured,
    ContentAcquirer,
    ContentAcquiringPlan,
    ContentUnsatisfied,
    UndeclaredAcquisition,
)
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan

__ccf_mode__ = "algorithmic"

__all__ = [
    "AcquirerNotConfigured",
    "ContentUnsatisfied",
    "DuplicateOperatorKey",
    "ExecutionResult",
    "ExecutionStep",
    "OperatorRegistry",
    "ProjectionEngine",
    "UndeclaredAcquisition",
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
        acquisitions: Content acquired at decision time, in resolution order,
            each with its content address. Empty for a plan that declared none.
            This is replay dimension 5's record of what the interpretation read
            from outside the graph: **a replay re-feeds these recorded items
            rather than re-acquiring** (INV-CH7-31), because a remote resource
            that moved between the decision and the replay would otherwise make
            the replay a new decision wearing the old one's identifier.
    """

    plan_id: str
    operators_invoked: frozenset[str]
    steps: tuple[ExecutionStep, ...]
    provenance: OperatorProvenance | None
    projection: ProjectionOutput
    view: GraphView
    acquisitions: tuple[AcquiredContent, ...] = ()

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
    """Runs the operator plan, then decision-time acquisition, then Π.

    Args:
        reader: Read-only graph access. There is no writer parameter on this
            constructor, and that absence is the point — L4/L5 are structurally
            incapable of writing (INV-CH7-11, single-writer per CLAUDE.md §10).
            Adding an acquirer does not change this: an acquirer holds no graph
            handle either, and what it fetches terminates in the projection
            payload rather than entering L3.
        registry: The boot-populated operator registry.
        acquirer: Resolves the content a :class:`ContentAcquiringPlan` declares
            (CLAUDE.md §7.1, whitepaper §6.6). Optional, and its optionality is
            structural rather than convenient: **a replay constructs the engine
            without one** and re-feeds the recorded acquisitions, so an engine
            that could always reach the network would make replay a live call.
    """

    def __init__(
        self,
        *,
        reader: GraphReader,
        registry: OperatorRegistry,
        acquirer: ContentAcquirer | None = None,
    ) -> None:
        self._reader = reader
        self._registry = registry
        self._acquirer = acquirer

    def _resolve_content(
        self,
        *,
        plan: ContentAcquiringPlan,
        tenant_id: str,
        recorded_acquisitions: tuple[AcquiredContent, ...] | None,
    ) -> tuple[AcquiredContent, ...]:
        """Resolve the plan's declared content, or refuse.

        Three refusals, no fallback. "Proceed without the content" is never one
        of the outcomes: a projection silently interpreting absent content it
        declared it needed is the debt-blind decision the fabric exists to
        prevent (whitepaper §7.7).
        """
        requests = plan.required_content()
        if recorded_acquisitions is not None:
            resolved: Mapping[str, AcquiredContent] = {
                acquired.request.request_key: acquired
                for acquired in recorded_acquisitions
            }
        elif self._acquirer is None:
            raise AcquirerNotConfigured(
                f"plan {plan.plan_id!r} declares "
                f"{len(requests)} content request(s) and this engine was "
                "constructed without an acquirer"
            )
        else:
            resolved = self._acquirer.acquire(
                requests=requests, tenant_id=tenant_id
            )

        declared = {request.request_key for request in requests}
        undeclared = sorted(set(resolved) - declared)
        if undeclared:
            raise UndeclaredAcquisition(
                f"plan {plan.plan_id!r} did not declare {undeclared}; the "
                "declared set and the resolved set are compared, never merged"
            )
        missing = sorted(declared - set(resolved))
        if missing:
            raise ContentUnsatisfied(
                f"plan {plan.plan_id!r} declared {missing}, which came back "
                "unsatisfied"
            )
        acquisitions = tuple(resolved[request.request_key] for request in requests)
        for acquired in acquisitions:
            if acquired.content_hash != acquired.rehash():
                raise ContentUnsatisfied(
                    f"content for {acquired.request.request_key!r} does not "
                    "match its recorded content address"
                )
        return acquisitions

    def execute(
        self,
        *,
        plan: ProjectionPlan | ContentAcquiringPlan,
        perspective: Perspective,
        tenant_id: str,
        temporal_boundary: datetime,
        recorded_acquisitions: tuple[AcquiredContent, ...] | None = None,
    ) -> ExecutionResult:
        """Execute ``plan`` for ``perspective`` as of ``temporal_boundary``.

        ``temporal_boundary`` is supplied by the caller and threaded into every
        operator. Nothing in this path reads a clock (04-RESEARCH.md
        anti-patterns): a replay feeds the boundary the original decision used
        and gets the original answer.

        **Stage order is load-bearing.** Acquisition runs *after* the operator
        plan and *before* Π. Policy is an operator, so by the time anything is
        fetched the view has already been constrained for this principal, and
        nothing is acquired on behalf of a principal Policy excluded — the
        INV-CH7-26 ordering argument applied to acquisition. Running the fetch
        first would be cheaper and would be exactly wrong.

        Args:
            recorded_acquisitions: Content a prior execution recorded. Supplied
                by a replay, which re-feeds rather than re-acquires
                (INV-CH7-31); when present the acquirer is not called at all.

        Raises:
            UnregisteredOperator: the plan declared a key the registry does not
                hold.
            AcquirerNotConfigured: the plan declares content and neither an
                acquirer nor recorded acquisitions were supplied.
            UndeclaredAcquisition: content came back that the plan never
                declared.
            ContentUnsatisfied: a declared request came back unsatisfied, or a
                re-fed item does not match its recorded content address.
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

        acquisitions: tuple[AcquiredContent, ...] = ()
        if isinstance(plan, ContentAcquiringPlan):
            acquisitions = self._resolve_content(
                plan=plan,
                tenant_id=tenant_id,
                recorded_acquisitions=recorded_acquisitions,
            )
            projection = plan.invoke(
                view=view,
                operator_outputs=outputs,
                perspective=perspective,
                temporal_boundary=temporal_boundary,
                acquired_content={
                    acquired.request.request_key: acquired
                    for acquired in acquisitions
                },
            )
        else:
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
            acquisitions=acquisitions,
        )
