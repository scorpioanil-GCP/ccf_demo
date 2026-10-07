"""The planner: declared operator keys in, a totally-ordered plan out.

Whitepaper §7.4 (INV-CH7-28 dependency ordering; INV-CH7-23
composition-preservation with per-intermediate provenance); DESIGN.md §2B.1;
D-IMPL-36 (intermediate results).

**The order is the planner's, never the plan's.** A projection declares a
*set* of operators (:mod:`ccf.projection.plan`); this module resolves that set
against the registry and imposes ``Policy → Similarity → Temporal → Traversal``.
Policy first so that Similarity ranks only over the principal-permissible
subgraph: §7.4 puts admissibility upstream of retrieval precisely so there is
never inadmissible content to filter out afterwards (INV-CH7-26). Temporal
before Traversal so a walk expands over temporally reconciled state rather
than over claims the boundary excludes. A
projection cannot express the forbidden order because it never expresses an
order at all.

**Intra-category order is by key.** Two operators of the same category need a
tiebreak, and "whichever the plan listed first" is not one — it makes the
product a function of an authoring accident. Sorting by key gives a total
order that is stable across processes, across plans, and across replays.

**The intermediate cache is per-execution and keyed by everything that could
change the answer** (D-IMPL-36, scoped to I.1). Its key includes the input
view's content hash, the operator's parameter hash, and the upstream provenance
chain — so a cache hit is by construction the value a recomputation would
produce, including its provenance. A cache keyed by operator identity alone
would return an intermediate computed over a *different* input, which is how a
memoized fabric quietly stops being replayable.

**Composition is production code, not a test helper.** :func:`compose` builds
the composite operator ``A∘B`` that the composition-preservation property
asserts against sequential application (``(A∘B)(G) = A(B(G))``, whitepaper
§7.4). Building it here means the property harness exercises the same
composition path the engine runs, rather than a re-implementation that could
agree with itself while disagreeing with the fabric.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView
from ccf.operators.base import (
    CATEGORY_ORDER,
    Operator,
    OperatorCategory,
    OperatorOutput,
    OperatorParameters,
    OperatorProvenance,
)
from ccf.operators.registry import OperatorRegistry

__ccf_mode__ = "algorithmic"

__all__ = [
    "ComposedOperator",
    "IntermediateCache",
    "OperatorPlan",
    "PlannedStep",
    "build_operator_plan",
    "compose",
]


class PlannedStep(CCFContract):
    """One position in a built plan, before anything has run.

    The declarative face of the plan: enough to show a reviewer (or a CLI, or a
    Control Plane audit) what *would* run and in what order, without executing
    it. The executed counterpart is ``ccf.projection.engine.ExecutionStep``, and
    the two are deliberately distinct types — "what we planned" and "what ran"
    must stay comparable rather than collapse into one record that cannot
    disagree with itself.
    """

    position: int
    operator_key: str
    category: OperatorCategory
    parameter_hash: str


@dataclass(frozen=True)
class OperatorPlan:
    """A resolved, totally-ordered operator sequence ready for execution.

    Attributes:
        operators: The operators in canonical dependency order.
    """

    operators: tuple[Operator, ...]

    def keys(self) -> tuple[str, ...]:
        """The operator keys in execution order."""
        return tuple(operator.key for operator in self.operators)

    def steps(self) -> tuple[PlannedStep, ...]:
        """The declarative step sequence this plan would execute."""
        return tuple(
            PlannedStep(
                position=index,
                operator_key=operator.key,
                category=operator.category,
                parameter_hash=content_hash(operator.parameters),
            )
            for index, operator in enumerate(self.operators)
        )

    def __len__(self) -> int:
        return len(self.operators)


def build_operator_plan(
    *, registry: OperatorRegistry, required_operators: Sequence[str]
) -> OperatorPlan:
    """Resolve ``required_operators`` into canonical dependency order.

    A key declared more than once yields one step: a plan naming an operator
    twice is naming the same pure function twice, and running it twice would
    change the provenance chain without changing the state.

    Raises:
        UnregisteredOperator: a declared key is not registered.
    """
    resolved = {key: registry.resolve(key) for key in required_operators}
    return OperatorPlan(
        operators=tuple(
            sorted(
                resolved.values(),
                key=lambda operator: (
                    CATEGORY_ORDER.index(operator.category),
                    operator.key,
                ),
            )
        )
    )


@dataclass
class _Deferred:
    """An intermediate held before its key has been materialized.

    Everything :meth:`IntermediateCache._key` needs, kept so the key can be
    built later — at the first moment a lookup for the same operator could
    hit — rather than at the moment the intermediate was produced.

    **What this costs in memory, measured rather than characterised.** The
    deferral retains the *input* ``view`` for the life of the cache. It does
    **not** introduce view retention where there was none: ``output`` is an
    :class:`~ccf.operators.base.OperatorOutput`, whose ``view`` field the eager
    scheme already retained per entry, and which
    :meth:`ComposedOperator.apply` reads back as ``inner.view``. So the delta is
    **one additional view per deferred operator**, not "views retained where
    none were before" — a materially smaller number than the close-time panel's
    advisory recorded, corrected by the single-agent pass that read
    ``OperatorOutput``. Recorded here so that a re-baselining of
    ``perf/baselines/local.json`` measures against the right expectation. The
    direction is still up.
    """

    tenant_id: str
    operator: Operator
    view: GraphView
    upstream: tuple[OperatorProvenance, ...]
    output: OperatorOutput


class IntermediateCache:
    """Per-execution memo of operator intermediates (D-IMPL-36, I.1 scope).

    Deliberately *not* a process-lifetime cache. An intermediate is only
    reusable while the graph state it was computed over is pinned, and within
    one execution it demonstrably is: the engine takes a single as-of read and
    every downstream value derives from it. A longer-lived cache needs the
    invalidation story D-IMPL-36 defers, and a cache without one is a replay
    defect waiting for a write.

    Cache identity is ``(tenant, operator key, parameter hash, input view
    hash, upstream chain hash)`` — everything :meth:`Operator.apply` can
    observe, ``tenant_id`` argument included. A hit therefore returns the value
    recomputation would produce, provenance included.

    **Tenant is the first component, as D-IMPL-36 rules it** (``docs/DECISIONS.md``
    D-IMPL-36: *"keyed on (tenant, operator_key, parameter_set_version,
    input_intermediate_keys, graph_snapshot_id)"*). The view hash already
    differs across tenants, because ``GraphView.tenant_id`` is a hashed field;
    what it does not cover is :meth:`run`'s separate ``tenant_id`` argument,
    which :meth:`Operator.apply` observes. Before LOW-03 (D-IMPL-372) the key
    was a 4-tuple without it, so one view object run under two tenant
    arguments hit and served the first tenant's intermediate to the second.

    **The key's composition is D-IMPL-36's; *when* it is computed is not.**
    What this class does not do is build that key on *every* invocation. An
    intermediate is held un-keyed (:class:`_Deferred`, which carries the
    ``tenant_id`` it was computed under) until a later call arrives for the
    same ``operator.key``, which is the first moment a lookup could hit:
    ``operator.key`` is a component of the key tuple, so an operator with no
    stored intermediate cannot match one.
    Hashing a graph view is the dominant cost of building the key, and
    ``ProjectionEngine.execute`` invokes each operator key exactly once — so
    on the shipped engine path every one of those hashes was being computed
    for a lookup that could not happen (``DI-15.5-04``).

    **What narrows, precisely.** Until now the key was computed on every
    invocation, so the property *"the key is a total function of everything*
    :meth:`Operator.apply` *can observe"* was witnessed by execution on every
    call. Under the deferred scheme the property is **true by construction but
    no longer witnessed on every call**: the key is materialized only where it
    is consulted. The final value a caller receives is identical and the hit
    accounting is identical; what changes is the *evidence class*. Its
    remaining witness is ``tests/operators/test_planner.py``, whose two cache
    tests exercise the reachable path — a repeat invocation that hits, and two
    distinct upstream chains that must not collapse. D-IMPL-36's ruled text
    says nothing about *when* the key is computed, so this narrows the
    guarantee's witness, not the guarantee.

    One consequence follows from the same narrowing and is stated rather than
    discovered: a view that has no canonical rendering
    (:class:`~ccf.contracts.canonical.CanonicalizationError`) used to surface
    on its first pass through this cache. It now surfaces only where the key
    is actually built. The deferral changed only when the key is built; LOW-03
    changed what it holds (the tenant, restored as D-IMPL-36's first
    component).
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str, str, str], OperatorOutput] = {}
        self._deferred: dict[str, list[_Deferred]] = {}
        self._hits = 0

    @property
    def hits(self) -> int:
        """How many invocations were answered from the memo.

        Exposed for tests and for the CLI: a cache whose effect is unobservable
        cannot be shown to be sound, and "it was never consulted" is the
        explanation a green property suite would otherwise hide.
        """
        return self._hits

    @staticmethod
    def _key(
        *,
        tenant_id: str,
        operator: Operator,
        view: GraphView,
        upstream: tuple[OperatorProvenance, ...],
    ) -> tuple[str, str, str, str, str]:
        """D-IMPL-36's key: tenant first, then operator, parameters, view, upstream."""
        return (
            tenant_id,
            operator.key,
            content_hash(operator.parameters),
            content_hash(view),
            content_hash(upstream),
        )

    def run(
        self,
        operator: Operator,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Return ``operator``'s intermediate, computing it at most once.

        The key is built only when a lookup could hit — that is, when this
        cache already holds an intermediate for the same ``operator.key``.
        See the class docstring for what that narrows in D-IMPL-36.
        """
        held = self._deferred.get(operator.key)
        if held is None:
            # First sighting of this operator in this execution. ``operator.key``
            # is a component of the key tuple, so nothing already stored can
            # match: there is no lookup to build a key for. The intermediate is
            # held un-keyed until a second call for this operator makes one
            # necessary.
            output = operator.apply(
                view=view,
                tenant_id=tenant_id,
                temporal_boundary=temporal_boundary,
                upstream=upstream,
            )
            self._deferred[operator.key] = [
                _Deferred(
                    tenant_id=tenant_id,
                    operator=operator,
                    view=view,
                    upstream=upstream,
                    output=output,
                )
            ]
            return output
        # A lookup could hit. Materialize the keys of anything held un-keyed for
        # this operator, then probe on the key this call would have built all
        # along.
        for deferred in held:
            self._entries[
                self._key(
                    tenant_id=deferred.tenant_id,
                    operator=deferred.operator,
                    view=deferred.view,
                    upstream=deferred.upstream,
                )
            ] = deferred.output
        held.clear()
        key = self._key(
            tenant_id=tenant_id, operator=operator, view=view, upstream=upstream
        )
        cached = self._entries.get(key)
        if cached is not None:
            self._hits += 1
            return cached
        output = operator.apply(
            view=view,
            tenant_id=tenant_id,
            temporal_boundary=temporal_boundary,
            upstream=upstream,
        )
        self._entries[key] = output
        return output


class ComposedOperator:
    """The composite ``outer ∘ inner``: one operator that runs two in sequence.

    Whitepaper §7.4: the algebra's composition-preservation guarantee is
    ``(A∘B)(G) = A(B(G))``. This type is the left-hand side, and it is
    production code precisely so the property harness can assert against the
    real one.

    The composite is a conforming :class:`~ccf.operators.base.Operator`, so it
    composes further — ``compose(A, compose(B, C))`` is well-formed and, because
    each stage threads the previous intermediate's provenance into the next, the
    chain it produces is the chain sequential application produces.

    A composite is **not registrable**: its key is derived rather than assigned,
    and the registry holds the operators a deployment declared, not the
    compositions the planner happens to form.
    """

    def __init__(
        self,
        *,
        outer: Operator,
        inner: Operator,
        cache: IntermediateCache | None = None,
    ) -> None:
        self._outer = outer
        self._inner = inner
        self._cache = cache

    @property
    def key(self) -> str:
        """Derived identity, in the whitepaper's own ``A∘B`` notation."""
        return f"{self._outer.key}∘{self._inner.key}"

    @property
    def category(self) -> OperatorCategory:
        """The outer operator's category — the composite's own last effect."""
        return self._outer.category

    @property
    def parameters(self) -> OperatorParameters:
        """The outer operator's parameters.

        The inner operator's parameters are not lost: they are pinned into the
        provenance sub-chain the composite returns, which is where a replay
        reads them from.
        """
        return self._outer.parameters

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Apply the inner operator, then the outer one, over its result."""
        inner = self._run(
            self._inner,
            view=view,
            tenant_id=tenant_id,
            temporal_boundary=temporal_boundary,
            upstream=upstream,
        )
        return self._run(
            self._outer,
            view=inner.view,
            tenant_id=tenant_id,
            temporal_boundary=temporal_boundary,
            upstream=(inner.provenance,),
        )

    def _run(
        self,
        operator: Operator,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        if self._cache is not None:
            return self._cache.run(
                operator,
                view=view,
                tenant_id=tenant_id,
                temporal_boundary=temporal_boundary,
                upstream=upstream,
            )
        return operator.apply(
            view=view,
            tenant_id=tenant_id,
            temporal_boundary=temporal_boundary,
            upstream=upstream,
        )


def compose(
    outer: Operator, inner: Operator, *, cache: IntermediateCache | None = None
) -> ComposedOperator:
    """Return the composite operator ``outer ∘ inner``.

    Args:
        outer: The operator applied second (``A`` in ``A∘B``).
        inner: The operator applied first (``B`` in ``A∘B``).
        cache: Optional per-execution intermediate memo. Supplying one exercises
            the memoized path; omitting it recomputes. Both must produce
            identical bytes, which is what the composition property asserts.
    """
    return ComposedOperator(outer=outer, inner=inner, cache=cache)


# Structural conformance at import time: a composite that stopped being an
# operator would break composition associativity at the definition site rather
# than in whichever suite happened to nest two of them.
_CONFORMANCE: tuple[type[Operator], ...] = (ComposedOperator,)
