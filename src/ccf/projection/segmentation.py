"""Plan segmentation: the alternation of pushed and in-process segments.

Whitepaper §7.4 (operators as declared, replayable intent — the algebra whose
composition preservation is what entitles a plan to be split without changing
its answer). The normative segmentation clauses are `GQ-14` at
docs/GRAPH_QUERY_SEMANTICS.md:289 through `GQ-19` at
docs/GRAPH_QUERY_SEMANTICS.md:356, transcribing the `D-IMPL-87` at
docs/DECISIONS.md resolution — this module implements them; it does not
re-derive them.

**The segment structure is a pure function of the plan** (`GQ-14` at
docs/GRAPH_QUERY_SEMANTICS.md:289). Maximal runs of fragment-declaring
operators form pushable segments; maximal runs of ``None``-intent operators
form in-process segments. What the substrate is can never influence the split
(D-04 — adapters always answer, `GQ-29` at docs/GRAPH_QUERY_SEMANTICS.md:554),
and neither can data or configuration *here*: which post-in-process segments
actually push additionally depends on the survivor count against the Control
Plane cap value (`GQ-18` at docs/GRAPH_QUERY_SEMANTICS.md:342), and that
decision is deliberately represented in the engine's loop, not in this module
— :func:`segment_plan` stays clock-, data-, and config-free, so its output for
a given plan is one value, identical across calls, processes, and replays.

**The degenerate opening segment.** A plan that begins with a ``None``-intent
operator — the all-``None``-intent plan included — still owes its first
in-process operator a view, and the compilation target of "nothing is
pushable" is the everything-question (`GQ-05` at
docs/GRAPH_QUERY_SEMANTICS.md:122). :func:`segment_plan` therefore opens every
such alternation with an implicit degenerate :class:`PushableSegment` — no
operators, no fragments — whose compiled query carries only the mandatory
fields. The invariant downstream code may rely on: **segments always open
with a pushable segment and strictly alternate thereafter.**

Segment values hold operator *keys*, not operators: the segmentation is a
statement about the plan's structure, and the engine — which already holds
the resolved :class:`~ccf.operators.planner.OperatorPlan` — is the thing that
runs them.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ccf.graph.protocols import GraphQuery, QueryFragment, TraversalSpec
from ccf.operators.base import Operator, read_intent_of

__ccf_mode__ = "algorithmic"

__all__ = [
    "FragmentFamilyConflict",
    "InProcessSegment",
    "PushableSegment",
    "SegmentedPlan",
    "compile_segment_query",
    "segment_plan",
]


class FragmentFamilyConflict(ValueError):
    """Two fragments in one segment claim the same predicate family.

    A broken plan, refused at plan compilation per `GQ-06` at
    docs/GRAPH_QUERY_SEMANTICS.md:132 — never merged, because a merge rule
    would silently decide which operator's parameters win, and a
    decided-by-accident parameter set cannot be replayed against an intent.
    An exception rather than a returned refusal, per the house line: a
    refused *product* is an expected outcome; a plan whose declared intents
    collide is a broken deployment.
    """


def _family_of(fragment: QueryFragment) -> str | None:
    """Which of the three `GQ-02` families this fragment carries, if any.

    A fragment carries at most one family by construction
    (:class:`~ccf.graph.protocols.QueryFragment` refuses more at validation),
    and a present policy family is whole (`GQ-02` at
    docs/GRAPH_QUERY_SEMANTICS.md:64), so probing one field per family is
    exact. ``None`` means the fragment constrains nothing — a legal, empty
    contribution.
    """
    if fragment.permitted_policy_bundle_versions is not None:
        return "policy"
    if fragment.require_valid_at_boundary is not None:
        return "temporal"
    if fragment.traverse is not None:
        return "traverse"
    return None


@dataclass(frozen=True)
class PushableSegment:
    """One maximal run of fragment-declaring operators — one substrate query.

    Attributes:
        operator_keys: The run's operator keys, in canonical execution order.
            The engine re-applies exactly these operators over the segment's
            answer — sound because the answer is a fixed point of its own
            operators (`GQ-19` at docs/GRAPH_QUERY_SEMANTICS.md:356).
        fragments: The operators' declared contributions, positionally
            aligned with ``operator_keys``. At most one fragment per family
            (`GQ-06` at docs/GRAPH_QUERY_SEMANTICS.md:132), enforced at
            construction time by :func:`segment_plan`. Empty on the implicit
            degenerate opening segment, whose compiled query is the
            everything-question (`GQ-05` at
            docs/GRAPH_QUERY_SEMANTICS.md:122).
    """

    operator_keys: tuple[str, ...]
    fragments: tuple[QueryFragment, ...]


@dataclass(frozen=True)
class InProcessSegment:
    """One maximal run of ``None``-intent operators — no substrate query.

    The engine runs these over the current view exactly as the pre-segmented
    path did; the entity URIs of the view they leave behind are the
    survivors the next pushed segment carries as ``allowed_entities``
    (`GQ-17` at docs/GRAPH_QUERY_SEMANTICS.md:330).
    """

    operator_keys: tuple[str, ...]


@dataclass(frozen=True)
class SegmentedPlan:
    """The ordered alternation :func:`segment_plan` produces.

    Invariant: ``segments`` is never empty, opens with a
    :class:`PushableSegment` (possibly the degenerate one), and strictly
    alternates between the two segment kinds thereafter.
    """

    segments: tuple[PushableSegment | InProcessSegment, ...]


def segment_plan(operators: Sequence[Operator]) -> SegmentedPlan:
    """Split an ordered operator sequence at its non-pushable boundaries.

    The `GQ-14` at docs/GRAPH_QUERY_SEMANTICS.md:289 split, as structure:
    ``operators`` arrives already in canonical dependency order (the
    planner's job — this function imposes no order of its own), and each
    operator lands in a pushable or in-process run according to
    :func:`~ccf.operators.base.read_intent_of` alone. Pure: no reader, no
    clock, no I/O — the structure is the same value on every call.

    An empty plan and an all-``None``-intent plan both open with the
    implicit degenerate pushable segment (the everything-question, `GQ-05`
    at docs/GRAPH_QUERY_SEMANTICS.md:122), so the engine's loop needs no
    special case to acquire its first view.

    Raises:
        FragmentFamilyConflict: two operators in one pushable run declare
            the same predicate family (`GQ-06` at
            docs/GRAPH_QUERY_SEMANTICS.md:132 — refused, never merged).
    """
    segments: list[PushableSegment | InProcessSegment] = []
    pushed_keys: list[str] = []
    pushed_fragments: list[QueryFragment] = []
    claimed_families: dict[str, str] = {}
    in_process_keys: list[str] = []

    def flush_pushable() -> None:
        if pushed_keys:
            segments.append(
                PushableSegment(
                    operator_keys=tuple(pushed_keys),
                    fragments=tuple(pushed_fragments),
                )
            )
            pushed_keys.clear()
            pushed_fragments.clear()
            claimed_families.clear()

    def flush_in_process() -> None:
        if in_process_keys:
            segments.append(
                InProcessSegment(operator_keys=tuple(in_process_keys))
            )
            in_process_keys.clear()

    for operator in operators:
        fragment = read_intent_of(operator)
        if fragment is not None:
            flush_in_process()
            family = _family_of(fragment)
            if family is not None:
                already = claimed_families.get(family)
                if already is not None:
                    raise FragmentFamilyConflict(
                        f"operators {already!r} and {operator.key!r} both "
                        f"declare the {family} family in one segment; a "
                        "same-family conflict is a broken plan and is "
                        "refused, never merged"
                        " (`GQ-06` in docs/GRAPH_QUERY_SEMANTICS.md)"
                    )
                claimed_families[family] = operator.key
            pushed_keys.append(operator.key)
            pushed_fragments.append(fragment)
        else:
            flush_pushable()
            in_process_keys.append(operator.key)

    flush_pushable()
    flush_in_process()

    if not segments or isinstance(segments[0], InProcessSegment):
        segments.insert(0, PushableSegment(operator_keys=(), fragments=()))
    return SegmentedPlan(segments=tuple(segments))


def compile_segment_query(
    segment: PushableSegment,
    *,
    tenant_id: str,
    as_of: datetime,
    seeds: frozenset[str] | None,
    allowed_entities: frozenset[str] | None,
) -> GraphQuery:
    """Union one segment's fragments field-wise into its ``GraphQuery``.

    The `GQ-06` at docs/GRAPH_QUERY_SEMANTICS.md:132 union: at most one
    fragment per family (enforced at :func:`segment_plan` time), so the
    union is a field-wise copy with no merge rule to decide. The degenerate
    segment compiles to the everything-question (`GQ-05` at
    docs/GRAPH_QUERY_SEMANTICS.md:122).

    ``seeds`` and ``allowed_entities`` are **engine-authored
    segment-boundary data**, never an operator's contribution (`GQ-04` at
    docs/GRAPH_QUERY_SEMANTICS.md:98): both are ``None`` for the first
    segment and for every segment of a fully-pushable plan. For a segment
    after an in-process segment, the engine passes the survivor set as
    ``allowed_entities`` under the uniform rule (`GQ-15` at
    docs/GRAPH_QUERY_SEMANTICS.md:300); walk starting points are computed
    *within* the set by the answerer — ``seed_entity_classes`` select within
    ``allowed_entities``, and explicit ``seeds`` intersect with it (`GQ-17`
    at docs/GRAPH_QUERY_SEMANTICS.md:330) — so the engine authors no
    explicit seeds of its own: seeds say where walks start, not which nodes
    they may cross, and a survivor promoted to a walk start would widen the
    walk beyond what the segment's own operators compute. The contract
    refuses ``seeds`` without a traverse family (`GQ-03` at
    docs/GRAPH_QUERY_SEMANTICS.md:87); this function passes the caller's
    values through and adds nothing.
    """
    policy_versions: frozenset[str] | None = None
    attribute_by_class: Mapping[str, str] | None = None
    classifications: frozenset[str] | None = None
    require_valid: bool | None = None
    traverse: TraversalSpec | None = None
    for fragment in segment.fragments:
        if fragment.permitted_policy_bundle_versions is not None:
            policy_versions = fragment.permitted_policy_bundle_versions
            attribute_by_class = fragment.classification_attribute_by_class
            classifications = fragment.permitted_classifications
        if fragment.require_valid_at_boundary is not None:
            require_valid = fragment.require_valid_at_boundary
        if fragment.traverse is not None:
            traverse = fragment.traverse
    return GraphQuery(
        tenant_id=tenant_id,
        as_of=as_of,
        permitted_policy_bundle_versions=policy_versions,
        classification_attribute_by_class=attribute_by_class,
        permitted_classifications=classifications,
        require_valid_at_boundary=require_valid,
        traverse=traverse,
        seeds=seeds,
        allowed_entities=allowed_entities,
    )
