"""The operator contract: pure view→view functions carrying their provenance.

Whitepaper §7.4 (INV-CH7-22 typed, side-effect-free, read-only-sync operators;
INV-CH7-23 composition-preservation with per-intermediate provenance);
DESIGN.md §2B.1.

Three shape decisions here are load-bearing, and each exists to make an
invariant structural rather than remembered:

**An operator takes a** :class:`~ccf.graph.protocols.GraphView` **and returns a
view.** Not a ``GraphReader``, not a store handle — a *value*. The engine
performs the single as-of read; every operator downstream of it transforms an
immutable value into another immutable value. That is what makes
``(A∘B)(G) = A(B(G))`` assertable bit-for-bit: there is no state underneath an
operator that could differ between the two orderings, because an operator has
no access to any.

**``temporal_boundary`` is an argument, never a clock read.** No operator may
read the wall clock. Time is an input to the fabric, so a replay two years
later feeds the boundary it feeds and gets the answer it got (whitepaper
§7.10, INV-CH7-31 function-determinism).

**Every output carries its own provenance sub-chain.** An intermediate is
individually replayable only if it can say which operator produced it, under
which parameter set, over which upstream intermediates (INV-CH7-23). The
parameter set is identified by ``content_hash`` of its canonical form, so a
parameter change is visible as an identity change rather than as an invisible
behavioral one.

Operator parameters are declared, versioned Control Plane artifacts under
D-IMPL-38: this module declares the *base* and holds no thresholds, no
materiality floors, and no defaults (CLAUDE.md §11, CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView, QueryFragment

__ccf_mode__ = "algorithmic"

__all__ = [
    "CATEGORY_ORDER",
    "Operator",
    "OperatorCategory",
    "OperatorOutput",
    "OperatorParameters",
    "OperatorProvenance",
    "PushableOperator",
    "mint_provenance",
    "read_intent_of",
]

OperatorCategory = Literal["policy", "similarity", "temporal", "traversal"]

#: Planner dependency order (whitepaper §7.4, INV-CH7-28).
#:
#: Policy first because Similarity must rank only over the principal-permissible
#: subgraph: admissibility is settled up front, so inadmissible content is never
#: retrieved and no post-retrieval filter is required (INV-CH7-26). Temporal
#: before Traversal because a walk should expand over temporally reconciled
#: state, not over claims the boundary excludes.
CATEGORY_ORDER: tuple[OperatorCategory, ...] = (
    "policy",
    "similarity",
    "temporal",
    "traversal",
)


class OperatorParameters(CCFContract):
    """Base of a declared operator parameter set (D-IMPL-38).

    Subclasses declare *fields*, never defaults: a missing operator parameter
    is a Control Plane registration error surfaced at the point of use, not a
    number the SDK picked on the deployment's behalf. Frozen and
    canonically serializable, because the parameter set's ``content_hash`` is
    what pins the operator's behavior into the provenance chain.
    """


class OperatorProvenance(CCFContract):
    """The provenance sub-chain one operator invocation contributes.

    INV-CH7-23: every intermediate is lineage-complete on its own, so a cached
    intermediate is by construction the value replay would produce.

    Attributes:
        operator_key: Registry identity of the operator that ran.
        category: Its canonical category.
        parameter_hash: ``content_hash`` of the parameter set in force.
        index_version: Pinned similarity-index version, where the operator
            consulted one (INV-CH7-27). ``None`` for operators that do not —
            not an empty string, because "did not consult an index" and
            "consulted an unnamed index" are different facts.
        upstream: The provenance of the intermediates this invocation consumed,
            in execution order. Recursive by design: the chain *is* the plan.
    """

    operator_key: str
    category: OperatorCategory
    parameter_hash: str
    index_version: str | None = None
    upstream: tuple["OperatorProvenance", ...] = ()


class OperatorOutput(CCFContract):
    """One operator's intermediate: a graph view plus how it came to be."""

    view: GraphView
    provenance: OperatorProvenance


@runtime_checkable
class Operator(Protocol):
    """A typed, pure, read-only computation over one graph view.

    Realization is unconstrained (INV-CH7-32): code, SQL-backed, or swarm — the
    algebra is the determinism surface, and conformance to this Protocol is the
    whole obligation.
    """

    @property
    def key(self) -> str:
        """Registry identity, unique within a fabric (INV-CH7-29)."""
        ...

    @property
    def category(self) -> OperatorCategory:
        """Which canonical category this operator belongs to."""
        ...

    @property
    def parameters(self) -> OperatorParameters:
        """The declared parameter set in force for this instance."""
        ...

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Return the intermediate this operator computes over ``view``.

        Must be pure: no writes, no I/O against the graph, no clock reads. The
        returned view is a new value; ``view`` is never mutated (it cannot be —
        it is frozen).
        """
        ...


@runtime_checkable
class PushableOperator(Protocol):
    """The optional pushability capability of an operator (D-03) — SDK-defined.

    An SDK extension beyond the whitepaper, labeled per CLAUDE.md §11: the
    whitepaper commits to operators as typed, pure computations (§7.4); the
    convention by which an operator *declares* the substrate question its
    ``apply()`` renders is Phase 15.2 mechanism — the `D-IMPL-87` at
    docs/DECISIONS.md:294 resolution's operator seam.

    This is deliberately a *separate* Protocol rather than a new member of
    :class:`Operator`: an existing third-party operator that never heard of
    pushdown still satisfies :class:`Operator` unchanged, still registers, and
    still executes — it simply contributes no fragment, and the engine
    materializes for its segment instead. :func:`read_intent_of` is the one
    sanctioned way to ask, so no caller ever hand-rolls the ``hasattr`` probe.
    """

    def read_intent(self) -> QueryFragment | None:
        """The fragment this operator's ``apply()`` renders, or ``None``.

        Must be computed from ``self.parameters`` alone — no view, no data, no
        clock (D-03): pushability is a property of the *declared intent*, so
        the segment structure stays a pure function of the plan (`GQ-14` at
        docs/GRAPH_QUERY_SEMANTICS.md:289). ``None`` means not pushable — a
        positive statement, never a failure. A fragment carries at most one
        predicate family and never seeds or ``allowed_entities`` (`GQ-06` at
        docs/GRAPH_QUERY_SEMANTICS.md:132). The named hazard of this seam —
        ``read_intent()`` and ``apply()`` diverging — is pinned by the
        per-operator equivalence property in
        ``tests/conformance/test_substrate_properties.py``.
        """
        ...


def read_intent_of(operator: Operator) -> QueryFragment | None:
    """Return ``operator``'s declared read intent, or ``None`` (D-03).

    The one place the optional-capability probe lives: an operator that
    implements :class:`PushableOperator` answers for itself; one that does not
    is not pushable, which is an answer, not an error. Centralized for the
    same reason :func:`mint_provenance` is — two probes could disagree about
    what "declares pushability" means, and the segment split (`GQ-14` at
    docs/GRAPH_QUERY_SEMANTICS.md:289) must be one function of the plan.
    """
    if isinstance(operator, PushableOperator):
        return operator.read_intent()
    return None


def mint_provenance(
    operator: Operator,
    *,
    upstream: tuple[OperatorProvenance, ...],
    index_version: str | None = None,
) -> OperatorProvenance:
    """Build the provenance entry for one invocation of ``operator``.

    Centralized so every operator hashes its parameters the same way — a
    second hashing convention would silently make two provenance chains
    incomparable, which is the one thing replay cannot survive.
    """
    return OperatorProvenance(
        operator_key=operator.key,
        category=operator.category,
        parameter_hash=content_hash(operator.parameters),
        index_version=index_version,
        upstream=upstream,
    )
