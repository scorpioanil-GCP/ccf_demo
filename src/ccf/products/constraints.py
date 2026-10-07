"""Resolving one request's parameters against every authority that bounds them.

**SDK-defined, not whitepaper-derived.** Whitepaper §7.8 makes the Control
Plane the place where the fabric's permitted behavior is declared and the plane
decisions are audited against; it does not say how a *product default*, a
*caller's value*, a *governed boundary* and a *backend's technical capability*
combine into the one value an operator plan is built from. ``D-IMPL-253``
Q4-Q8 and ``D-IMPL-254`` do. :mod:`ccf.products.provenance` is the *shape* a
resolution has to be able to say; this module is the resolution itself, and it
says that shape by returning it (CLAUDE.md §11).

The sequence, and it is fixed
-----------------------------

1. **Apply defaults.** A parameter the caller omitted takes what the class
   declared for omission, with authority ``default`` and the declaring
   document's own artifact pin as its source. Two documents may declare one:
   the product CLASS's characteristics (``ServeObligations``, reaching this
   function as ``class_defaults`` — today only the default debt tolerance,
   ``24.6-L-04``) and the request CONTRACT's own ``defaults``, which win for
   the same name because they speak about that one parameter of that one
   surface. The contract may also declare a default RELATIVELY — as an offset
   from ``request.asked_at`` rather than as a literal (``relative_defaults``,
   ``D-IMPL-325``) — which resolves in this same step, against the instant of
   the question and never against a clock. What is recorded is the resolved
   literal; the offset never reaches the replay record.
2. **Overlay caller values.** A parameter the caller stated takes the caller's
   value with authority ``caller`` and the request's identity as its source.
   The caller's own values are never rewritten in place — they survive on
   ``RequestIdentity.parameters``, which is what lets a refusal say *"you asked
   for X and policy P bounds you to Y"* rather than *"you asked for Y"*.
3. **Resolve policy constraints by comparability.** Restrictiveness folds only
   *within* a comparable family — two ceilings to the smaller, two floors to
   the larger, two admitted sets to their intersection (``D-IMPL-253`` Q4).
   Priority orders which surviving bound is *reported*; it never makes an
   applicable hard constraint disappear. Irreconcilable constraints are a
   governed :class:`PolicyResolutionConflict`, not a silent pick. A hard
   constraint reaching a parameter that has no value after steps 1 and 2 is
   refused ``required-absent``, never skipped (``SEC-019``, ``D-IMPL-356``
   D11).
4. **Bound by technical capability.** A backend's limit is an authority of its
   own, with a capability identity rather than an artifact pin
   (``D-IMPL-253`` amendment 2 (1): *"Do not create fake artifacts just to
   satisfy a uniform provenance schema."*).
5. **Validate the effective request.** The existing address -> tier -> payload
   -> interval comparison (:func:`~ccf.products.request.refuse_request`) runs
   over the *effective* parameters, so a default or a policy value is held to
   exactly the declaration a caller's value is.

Nothing here clamps. A value outside a bound is a governed
:class:`ConstraintRefusal` carrying the bound that refused it and the authority
that set it — never a substituted number, because a substituted number answers
a question nobody asked. The single exception the ruling names is worked case 3
and it is spelled out at :func:`resolve_effective_request`.

Pure over its arguments: **no clock, no registry lookup, no I/O; every instant
arrives as an argument.** Two instants, two jobs (`D-IMPL-358` step 5 ruling B,
amending ``D-IMPL-253`` Q6; `D-IMPL-364` SEC-010 E1): policy EFFECTIVITY —
which constraint is in force — is judged at ``served_at``, the trusted live
instant the resolver read once for this serve and hands in as a required
keyword; the AS-OF boundary of the graph read, and the base of a relative
default, stays ``request.asked_at``. A resolution that moved with the time of
day, or with what was registered elsewhere, would not be reproducible at
replay — which is the property every comparison in this package is required to
have, and the reason the record carries ``served_at`` (``D-IMPL-98``) rather
than this module reading a clock. The reference resolver that *reads* the
Control Plane for the constraint set is a separate seam; it fetches, and then
it calls this.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Final, Literal, Protocol, runtime_checkable

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, content_hash
from ccf.controlplane.artifacts import POLICY_CONSTRAINT, PolicyConstraint
from ccf.products.entitlement import (
    PrincipalNotEntitled,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
)
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.provenance import (
    EffectiveParameter,
    EffectiveRequest,
    OverrideRecord,
    ParameterBound,
    ProvenanceSource,
)
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
    decode_declared_request,
    refuse_request,
)
from ccf.projection.plan import Perspective

__ccf_mode__ = "algorithmic"

__all__ = [
    "CAPABILITY_TRAVERSAL_DEPTH",
    "REFERENCE_CONSTRAINT_RESOLVER_ID",
    "REFERENCE_CONSTRAINT_RESOLVER_VERSION",
    "ConstraintEffectivityConflict",
    "ConstraintRefusal",
    "PinnedConstraint",
    "PolicyConstraintResolver",
    "PolicyResolutionConflict",
    "ReferencePolicyConstraintResolver",
    "ResolutionOutcome",
    "TechnicalCapability",
    "applicable",
    "constraints_in_force",
    "resolve_effective_request",
]


#: The one capability token v0 ships (``D-IMPL-253`` Q21, ``D-IMPL-251`` C5).
#:
#: A **mechanism name and never a value**: it names *which* capability a
#: parameter is bounded by, and the bound itself — 100, or 8, or anything else
#: — is the backend's, supplied at run time as a :class:`TechnicalCapability`
#: (CLAUDE.md §6.4, CINV-01). The graph seam deliberately has no refusal path
#: of its own: an over-ceiling depth there makes the translation decline and
#: the memory-bounded fallback answer. Refusing a depth **by name** is this
#: layer's job, with authority ``technical``, because only here is there a
#: governed response to put the refusal in.
CAPABILITY_TRAVERSAL_DEPTH: Final[str] = "traversal-depth"

#: The capability vocabulary, closed by value — one member at v0.
#:
#: Module-private deliberately: the public names this layer ships are fixed by
#: plan ``24.6-03``, and a second public spelling of a one-member vocabulary
#: would be one more name the drift manifest tracks for no reader's benefit.
#: :class:`~ccf.products.request.ProductRequestContract` reads it through a
#: function-local import when it validates ``capability_bindings`` — the
#: ``refuse_payload`` precedent in that module — so a binding onto a token the
#: SDK does not define is refused at the declaration rather than discovered at
#: resolution.
_CAPABILITY_TOKENS: Final[frozenset[str]] = frozenset({CAPABILITY_TRAVERSAL_DEPTH})

#: Identity and lane of the SDK's reference constraint resolver, on the
#: :data:`~ccf.halflife.debt.FRESHNESS_SCORER_ID` precedent: the resolver *in
#: force* is pinnable, because a resolution is only reproducible alongside the
#: thing that produced it (``D-IMPL-253`` Q8).
REFERENCE_CONSTRAINT_RESOLVER_ID: Final[str] = "ccf.reference.policy-constraint-resolver"
REFERENCE_CONSTRAINT_RESOLVER_VERSION: Final[str] = "1.0.0"


#: The fold family each operator in the Control Plane's vocabulary belongs to.
#:
#: Restrictiveness is a comparison *within* a family and never across the
#: vocabulary (``D-IMPL-253`` Q4), so the family is what the fold is keyed on
#: rather than the operator name. ``preferred`` folds to guidance and to
#: **nothing else**, which is Q5's *"preferred must remain non-refusing
#: guidance"* made structural: there is no branch below a guidance bound can
#: reach, so it cannot refuse however the value compares.
#:
#: Held equal to :data:`~ccf.controlplane.artifacts.CONSTRAINT_OPERATORS` by
#: ``tests/products/test_policy_constraints.py``, so a sixth operator added to
#: the vocabulary is a red build here rather than a constraint this module
#: silently ignores.
_CEILING: Final[str] = "ceiling"
_FLOOR: Final[str] = "floor"
_MEMBERSHIP: Final[str] = "membership"
_PRESENCE: Final[str] = "presence"
_GUIDANCE: Final[str] = "guidance"

_FOLDS: Final[Mapping[str, str]] = {
    "maximum": _CEILING,
    "minimum": _FLOOR,
    "allowed_set": _MEMBERSHIP,
    "required": _PRESENCE,
    # D-05: preferred folds to guidance
    "preferred": _GUIDANCE,
}


#: *No value was supplied* for a keyword whose value may legitimately be
#: ``None``. A module-private object rather than ``None`` because an
#: ``allowed_set`` folds to a tuple and a ``required`` constraint's value **is**
#: ``None``, so ``None`` cannot also mean "unstated" here.
_UNSET: Final[object] = object()


class PinnedConstraint(CCFContract):
    """One policy constraint together with the pin it was resolved by.

    SDK-defined (CLAUDE.md §11), whitepaper §7.4: replay resolves an *exact*
    version and never "latest", so a constraint that reached a resolution
    without its ``(key, version)`` cannot be re-resolved by an examiner. The
    artifact itself carries its ``semver`` lane but not the registry key it
    lives under, and the key is half of the pin — hence this pairing rather
    than the bare artifact.

    Attributes:
        key: The Control Plane key the constraint was resolved from.
        version: The version resolved at, verbatim. Not re-derived from the
            artifact: what an examiner replays against is the version the
            resolution *asked for*.
        constraint: The artifact.
    """

    key: str
    version: str
    constraint: PolicyConstraint


class TechnicalCapability(CCFContract):
    """A backend's own limit on one capability — an authority, not a policy.

    SDK-defined (CLAUDE.md §11); ``D-IMPL-253`` Q21, in Dave's words: *"6 is
    measurement/default history; 100 is the genuine technical capability
    boundary."* A capability limit is a property of the substrate the fabric is
    executing on, so its provenance is a **backend identity and never an
    artifact pin** — amendment 2 (1) forbids minting a version for it, and
    :class:`~ccf.products.provenance.ProvenanceSource` refuses one structurally.

    Attributes:
        capability: Which capability is bounded — the SDK's own mechanism
            token, e.g. :data:`CAPABILITY_TRAVERSAL_DEPTH`.
        maximum: The limit. A :class:`~decimal.Decimal` because a float is not
            canonically encodable and this number reaches a replay record.
        identity: The backend's credential-free identity — the value a
            ``BackendStore`` answers as ``graph_identity``. It is what an
            examiner resolves the bound's source by.
    """

    capability: str
    maximum: Decimal
    identity: str


class ConstraintRefusal(CCFContract):
    """A value the fabric may not act on, and the bound that says so.

    SDK-defined (CLAUDE.md §11); whitepaper §7.8. The governed shell for a
    caller or defaulted value outside an applicable ``maximum``, ``minimum`` or
    ``allowed_set``, and for a parameter still absent after defaults on which
    a ``required`` constraint or a bounding one (``maximum``, ``minimum``,
    ``allowed_set``) applies. An absent bounded parameter is refused, never
    skipped (``SEC-019``; ``D-IMPL-356`` D11, amending the realization of
    ``D-IMPL-253`` Q5). **A returned value, never an exception** — the posture
    :mod:`ccf.products.gates` states at its own head, and the posture
    ``D-IMPL-253`` Q13 requires of every governed determination: a refusal is
    itself a decision and deserves the same replay treatment as a served
    product.

    **Nothing is clamped.** ``D-IMPL-251`` C5 survives here for genuine limits:
    a request over a bound is refused with the bound attached, so the consumer
    learns *what they asked for* and *what the boundary was*, rather than
    receiving an answer to a narrower question they never asked.

    The bound travels whole, which is what lets a technical limit be refused
    **by name**: :attr:`bound` carries ``authority == "technical"`` and a
    ``capability`` source, and a policy bound carries ``authority == "policy"``
    with the artifact pin and ``policy_id``. Which HTTP status or MCP shape
    that becomes is a door's decision; this module knows nothing of transports.

    Attributes:
        reason: Which of the three ways the value missed. ``bound-exceeded``
            covers both numeric directions, because the direction is already
            in ``bound.operator`` and stating it twice invites the two to
            disagree.
        key: The parameter, by the name the request contract declares.
        detail: The human-readable statement, for an operator reading a log.
            The typed members are the machine-readable version.
        bound: The boundary that refused, with its own authority and source.
        requested: What was presented — the caller's value, or the class's
            default when the caller omitted the parameter. ``None`` for
            ``required-absent``, which is the positive statement *nothing was
            presented*.
        overrides: Every override the request attempted, with its entitlement
            result — the same :class:`~ccf.products.provenance.OverrideRecord`
            tuple a fulfilled resolution carries on
            :attr:`~ccf.products.provenance.EffectiveRequest.overrides`. A
            refused request is still a request that asked for an exception,
            and the attempt and its verdict belong to the determination
            whichever way it went (``D-IMPL-260`` P-I, criterion 10). Empty
            when nothing was attempted; hash-transparent at the empty tuple.
    """

    reason: Literal["bound-exceeded", "not-in-allowed-set", "required-absent"]
    key: str
    detail: str
    bound: ParameterBound
    requested: Any
    overrides: tuple[OverrideRecord, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class PolicyResolutionConflict(CCFContract):
    """Two applicable constraints that cannot both be satisfied.

    SDK-defined (CLAUDE.md §11); whitepaper §7.8. ``D-IMPL-253`` Q4, in Dave's
    words: *"If constraints are irreconcilable, return a governed shell
    identifying a policy-resolution conflict, subject to disclosure."*

    **This is the shell that exists so priority never has to erase anything.**
    The tempting resolution — let the higher-priority constraint win — is
    exactly what Q4 forbids: *"Never use priority to make an applicable hard
    constraint disappear."* A ceiling below a floor, or admitted sets that
    share no member, is a **governance defect in the deployment's own policy
    set**, and the fabric's honest answer is to say so with both sides named
    rather than to pick one and serve a question nobody governed.

    Attributes:
        reason: The single member of this shell's vocabulary. It exists as a
            field rather than only as the kind, so a consumer branching on
            ``envelope.reason`` reads it uniformly with every other governed
            refusal.
        key: The parameter whose constraints disagree.
        detail: The human-readable statement naming both sides.
        overrides: Every override the request attempted, with its entitlement
            result, as on :class:`ConstraintRefusal` (``D-IMPL-260`` P-I).
        conflicting: The sources of every constraint that took part in the
            disagreement, so an examiner resolves each by ``(key, version)``
            rather than reconstructing the set from prose.
    """

    reason: Literal["policy-resolution-conflict"] = Field(
        default="policy-resolution-conflict",
        json_schema_extra={HASH_TRANSPARENT_KEY: False},
    )
    key: str
    detail: str
    conflicting: tuple[ProvenanceSource, ...]
    overrides: tuple[OverrideRecord, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class ResolutionOutcome(CCFContract):
    """One resolution's answer — completed request or governed refusal — with the evidence accumulated so far.

    **SDK-defined, not whitepaper-derived (CLAUDE.md §11).** The ruling of
    record is ``docs/DECISIONS.md`` **D-IMPL-264** D-08 (Dave, 2026-09-05,
    ``24.7-RULINGS.md`` §3 Q8), verbatim: *"Return the refusal paired with the
    partial resolution. Keep refusal vocabulary separate from resolution
    provenance rather than cloning resolution fields into multiple refusal
    classes. I would think of this as a common resolution outcome shape:
    completed request or governed refusal, both with the resolution evidence
    accumulated so far."* What the whitepaper commits to is the hook this
    shape serves: §7.8 audits every plane decision against the Control Plane
    that permitted it, and §7.10's five-dimension record is complete only when
    dimension 2 carries what resolution established — including what it
    established on the way to a refusal (D-07, Dave: *"'It failed before
    producing an effective request' must not erase what resolution already
    established."*).

    **Two members, both required, and the two vocabularies stay apart.**
    :attr:`evidence` is the :class:`~ccf.products.provenance.EffectiveRequest`
    as it stood when the resolution exited — complete on success, partial on a
    refusal — and it is the SAME type either way, so replay dimension 2 and
    :attr:`~ccf.products.refusal.RefusalEnvelope.provenance` read one shape
    whichever way the determination went. :attr:`refusal` is the governed
    determination that stands instead of a completed request, or ``None``; the
    three refusal classes gain no cloned resolution field, which is the half of
    Q8 that keeps a refusal a refusal. Neither member is defaulted: the
    completion says ``refusal=None`` out loud, on ``D-IMPL-264`` P-2's rule
    that absence is stated and never inferred from omission.

    Unlike :class:`~ccf.products.door.DoorOutcome`, which carries exactly one
    of its halves, this shape ALWAYS carries the evidence: the resolution step
    ran, so there is always something it established — at minimum the contract
    pin it consulted. Pydantic's own validation is therefore the whole guard.

    Attributes:
        evidence: What resolution established before it exited — every
            parameter resolved so far with ``(value, authority, source)`` and
            any bound attached, the guidance folded so far, every override
            attempt verified, and every source consulted.
        refusal: The governed refusal, when the resolution did not complete;
            ``None`` when :attr:`evidence` is the completed effective request.
    """

    evidence: EffectiveRequest
    refusal: (
        ConstraintRefusal | PolicyResolutionConflict | ProductRequestViolation | None
    )

    @property
    def completed(self) -> bool:
        """``True`` when the resolution produced an effective request."""
        return self.refusal is None


@dataclass(frozen=True)
class _Candidate:
    """One folded hard bound, with the ordering keys priority resolves by.

    Private: the fold's working shape, never a surface. ``policy_id`` and
    ``key`` are carried because a tie on ``priority`` has to break the same way
    on every run — a resolution that depended on mapping order would be a
    replay that reproduced a different bound.
    """

    fold: str
    bound: ParameterBound
    priority: int
    policy_id: str
    key: str


def _order(candidate: _Candidate) -> tuple[int, str, str]:
    """Highest priority first, then by policy id, then by artifact key."""
    return (-candidate.priority, candidate.policy_id, candidate.key)


def _source_of(pinned: PinnedConstraint) -> ProvenanceSource:
    """The artifact pin a constraint is replayed by."""
    return ProvenanceSource(
        kind="artifact", identity=pinned.key, version=pinned.version
    )


def _bound_of(pinned: PinnedConstraint, *, value: Any = _UNSET) -> ParameterBound:
    """The constraint as a bound, carrying its authority and its pin.

    ``value`` overrides the artifact's own value for the one case that needs
    it — an ``allowed_set`` folded to an intersection, whose value belongs to
    no single artifact.
    """
    constraint = pinned.constraint
    return ParameterBound(
        operator=constraint.operator,
        value=constraint.value if value is _UNSET else value,
        authority="policy",
        source=_source_of(pinned),
        policy_id=constraint.policy_id,
        reason=constraint.reason,
    )


def _sort_key(source: ProvenanceSource) -> tuple[str, str, str]:
    """A total order over sources, so ``applied`` renders one way."""
    return (source.kind, source.identity, source.version or "")


def _guidance_key(bound: ParameterBound) -> tuple[str, str, str, str]:
    """A total order over guidance bounds, for the same reason."""
    return (
        bound.authority,
        bound.operator,
        bound.policy_id or "",
        bound.source.identity,
    )


def _as_number(value: object) -> Decimal | None:
    """``value`` as a decimal when it is one of this fabric's numeric forms.

    ``bool`` is an ``int`` to Python and is not a number to a bound, so it is
    excluded by name. ``None`` is returned for everything else — a numeric
    bound over a non-numeric value is not a comparison this function invents a
    verdict for; :func:`~ccf.products.request.refuse_request` names the type
    mismatch at step 5, where the declaration is the authority on types.
    """
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return None
    return Decimal(value)


def _require_aware(asked_at: datetime) -> None:
    """Refuse a zone-less instant, in one place for both callers.

    :func:`applicable` needs it because comparing a naive instant against an
    aware effectivity window either raises deep inside a comparison or silently
    answers for the wrong hour. :func:`resolve_effective_request` needs it for
    the case ``applicable`` cannot cover: a request with **no** applicable
    constraints never reaches that comparison, and a resolution recorded at a
    zone-less ``asked_at`` would then be replayed against a window nobody can
    resolve. One reading, so the two cannot drift into two answers about what
    an instant is (``D-IMPL-98`` puts the instant on the request precisely so
    it is stated rather than assumed; ``D-IMPL-38`` refuses a zone-less
    timestamp at artifact load).
    """
    if asked_at.tzinfo is None or asked_at.utcoffset() is None:
        raise TypeError(
            "the instant must be timezone-aware: constraint effectivity is"
            " judged at served_at and the as-of boundary at asked_at, and"
            " there is no implicit UTC in this fabric (D-IMPL-98, D-IMPL-38)"
        )


def _numeric_key(entry: PinnedConstraint) -> tuple[Decimal, str]:
    """A ceiling's or floor's value, with the artifact key as the tiebreak.

    The artifact's own validator has already refused a non-decimal value under
    ``maximum``/``minimum`` **by name**, so the ``None`` branch is unreachable
    through :func:`~ccf.controlplane.artifacts.load_artifact`. It is still
    stated rather than assumed, because this function is also reachable from a
    contract built in Python — and a silent ``None`` here would sort a bound
    into the wrong place instead of failing.
    """
    number = _as_number(entry.constraint.value)
    if number is None:
        raise ValueError(
            f"constraint {entry.key!r} declares operator"
            f" {entry.constraint.operator!r} with a non-numeric value"
            f" {entry.constraint.value!r}; a bound on a numeric axis has a"
            " number or it is not a bound"
        )
    return (number, entry.key)


def applicable(
    constraint: PolicyConstraint,
    *,
    product_class: str,
    tenant: str,
    perspective_role: str,
    intent: str,
    served_at: datetime,
) -> bool:
    """Does this constraint reach this request, at this instant?

    Two questions, both answered here so no caller answers half of one. The
    **axes**: every member of ``applies_to`` that is not ``None`` must equal
    the corresponding input, conjunctively — ``None`` means *any*, and a
    constraint that narrows nothing applies to everything. The **window**:
    ``effective_from <= served_at`` and ``served_at < effective_until`` when an
    end is stated, half-open so a constraint that ends at the instant another
    begins never applies twice.

    **AMENDED by `D-IMPL-358` step 5 ruling B: evaluated at ``served_at``, the
    trusted live instant, and not at ``asked_at``.** The superseded reasoning is
    kept because it names the risk that had to be answered — ``D-IMPL-253`` Q6,
    Dave: *"asked_at, absolutely. Otherwise replay of the same historical
    decision can resolve a different policy."*

    That risk is real and is closed by a DIFFERENT mechanism, which is why the
    instant could move. Replay never re-derives effectivity at all: it resolves
    each binding at the version the record pinned
    (`ccf/replay/engine.py::_resolve_bindings`), `ReplayResolver` has no
    ``resolve_latest`` method to reach for, and nothing under `ccf/replay/`
    imports this module. So a historical decision replays against the constraint
    that governed it because the RECORD says which one did — not because this
    function would select the same one again.

    What the change buys is the live half: a constraint that became effective
    after a question was asked but before it was answered now governs the answer.
    A tenant that tightens a bound at noon has it in force at noon, rather than
    from whenever the oldest in-flight question happened to be asked.

    **The two axes stay separate.** This is the POLICY reading. The graph is
    still read at ``request.asked_at``, which is what keeps a question about last
    quarter a question about last quarter.

    Args:
        constraint: The artifact.
        product_class: The class the request addresses.
        tenant: The tenant the request is being resolved for.
        perspective_role: The Π role-conditioning in force.
        intent: The decision the product is being assembled for.
        served_at: The trusted serve instant, read once per serve. Timezone-aware.

    Returns:
        Whether the constraint applies.

    Raises:
        TypeError: ``served_at`` is zone-less. There is no implicit UTC in this
            fabric (``D-IMPL-98`` puts the instant on the request precisely so
            it is stated rather than assumed; ``D-IMPL-38`` refuses a zone-less
            timestamp at artifact load), and comparing a naive instant against
            an aware effectivity window would either raise deep inside a
            comparison or, worse, silently answer for the wrong hour.
    """
    # `D-IMPL-358` step 5: the guard follows the instant. There is no implicit
    # UTC in this fabric, and comparing a naive instant against an aware
    # effectivity window would answer for the wrong hour rather than raise.
    _require_aware(served_at)
    axes = (
        (constraint.applies_to.product_class, product_class),
        (constraint.applies_to.tenant, tenant),
        (constraint.applies_to.perspective_role, perspective_role),
        (constraint.applies_to.intent, intent),
    )
    for narrowed, presented in axes:
        if narrowed is not None and narrowed != presented:
            return False
    return _in_window(constraint, served_at=served_at)


def _in_window(constraint: PolicyConstraint, *, served_at: datetime) -> bool:
    """Is ``served_at`` inside this constraint's effectivity window?

    Half-open — ``effective_from <= served_at < effective_until`` — so a
    constraint that ends at the instant another begins never applies twice.

    One reading, called from both :func:`applicable` (which also holds the four
    axes) and :func:`constraints_in_force` (which selects by the window alone,
    before any axis is known). Two copies of a comparison this small are how a
    fabric comes to answer *"which policy was in force?"* two different ways at
    two different layers — and `D-IMPL-358` step 5 makes that reason sharper, not
    weaker: the instant this reads changed, and it changed in ONE place.
    """
    if constraint.effective_from > served_at:
        return False
    return constraint.effective_until is None or served_at < constraint.effective_until


def _fold(
    *, key: str, pinned: Sequence[PinnedConstraint]
) -> tuple[list[_Candidate], list[ParameterBound]] | PolicyResolutionConflict:
    """Fold one parameter's applicable constraints by comparability.

    Two ceilings fold to the smaller, two floors to the larger, two admitted
    sets to their intersection — because within a family the more restrictive
    statement *implies* the other, so nothing is lost by keeping it alone. A
    ceiling and an admitted set are **not** comparable and neither is dropped:
    both come back as candidates and both are checked.

    Returns the hard candidates and the guidance bounds, or the governed
    conflict when the folded statements cannot all hold.
    """
    families: dict[str, list[PinnedConstraint]] = {}
    guidance: list[ParameterBound] = []
    for entry in pinned:
        fold = _FOLDS[entry.constraint.operator]
        if fold == _GUIDANCE:
            guidance.append(_bound_of(entry))
            continue
        families.setdefault(fold, []).append(entry)

    candidates: list[_Candidate] = []

    ceilings = families.get(_CEILING, [])
    if ceilings:
        candidates.append(_candidate(_CEILING, min(ceilings, key=_numeric_key)))

    floors = families.get(_FLOOR, [])
    if floors:
        candidates.append(_candidate(_FLOOR, max(floors, key=_numeric_key)))

    if ceilings and floors:
        ceiling = _numeric_key(min(ceilings, key=_numeric_key))[0]
        floor = _numeric_key(max(floors, key=_numeric_key))[0]
        if ceiling < floor:
            return PolicyResolutionConflict(
                key=key,
                detail=(
                    f"{key}: the applicable ceiling {ceiling} lies below the"
                    f" applicable floor {floor}; the two are comparable and no"
                    " value satisfies both, so neither is dropped and the"
                    " conflict is returned (D-IMPL-253 Q4)"
                ),
                conflicting=tuple(
                    sorted(
                        (_source_of(entry) for entry in (*ceilings, *floors)),
                        key=_sort_key,
                    )
                ),
            )

    sets = families.get(_MEMBERSHIP, [])
    if sets:
        admitted: set[str] | None = None
        for entry in sets:
            # The artifact's own validator has already refused an
            # `allowed_set` whose value is not a non-empty tuple of names, so
            # the narrowing here restates that guarantee for the type checker
            # rather than adding a second reading of it.
            declared_set = entry.constraint.value
            members = set(declared_set) if isinstance(declared_set, tuple) else set()
            admitted = members if admitted is None else admitted & members
        if not admitted:
            return PolicyResolutionConflict(
                key=key,
                detail=(
                    f"{key}: the applicable admitted sets share no member, so"
                    " no value satisfies all of them; the intersection is the"
                    " comparable fold and an empty one is irreconcilable"
                    " rather than a set that admits nothing (D-IMPL-253 Q4)"
                ),
                conflicting=tuple(
                    sorted((_source_of(entry) for entry in sets), key=_sort_key)
                ),
            )
        # The intersection belongs to no single artifact, so the bound reports
        # the highest-priority contributor as its source and carries the folded
        # value. Every contributor is still in `applied`.
        reported = min(sets, key=lambda entry: (-entry.constraint.priority, entry.key))
        candidates.append(
            _candidate(
                _MEMBERSHIP, reported, value=tuple(sorted(admitted))
            )
        )

    for entry in families.get(_PRESENCE, []):
        candidates.append(_candidate(_PRESENCE, entry))

    return candidates, guidance


def _candidate(
    fold: str, pinned: PinnedConstraint, *, value: Any = _UNSET
) -> _Candidate:
    """One folded constraint, with its ordering keys."""
    return _Candidate(
        fold=fold,
        bound=_bound_of(pinned, value=value),
        priority=pinned.constraint.priority,
        policy_id=pinned.constraint.policy_id,
        key=pinned.key,
    )


def _refuse_against(
    *, key: str, value: Any, candidate: _Candidate
) -> ConstraintRefusal | None:
    """Hold one value to one folded bound. ``None`` when it holds."""
    bound = candidate.bound
    if candidate.fold == _CEILING:
        presented, limit = _as_number(value), _as_number(bound.value)
        if presented is None or limit is None or presented <= limit:
            return None
        return ConstraintRefusal(
            reason="bound-exceeded",
            key=key,
            detail=(
                f"{key}: {presented} exceeds the applicable maximum {limit}"
                f" established by authority {bound.authority!r}; the request is"
                " refused rather than narrowed, because a narrowed request"
                " answers a question nobody asked (D-IMPL-251 C5)"
            ),
            bound=bound,
            requested=value,
        )
    if candidate.fold == _FLOOR:
        presented, limit = _as_number(value), _as_number(bound.value)
        if presented is None or limit is None or presented >= limit:
            return None
        return ConstraintRefusal(
            reason="bound-exceeded",
            key=key,
            detail=(
                f"{key}: {presented} lies below the applicable minimum {limit}"
                f" established by authority {bound.authority!r}; the request is"
                " refused rather than raised to the floor (D-IMPL-251 C5)"
            ),
            bound=bound,
            requested=value,
        )
    if candidate.fold == _MEMBERSHIP:
        admitted = tuple(bound.value or ())
        if value in admitted:
            return None
        return ConstraintRefusal(
            reason="not-in-allowed-set",
            key=key,
            detail=(
                f"{key}: {value!r} is not one of {list(admitted)}, the set the"
                " applicable constraints admit between them"
            ),
            bound=bound,
            requested=value,
        )
    return None


def _with_overrides(
    refusal: ConstraintRefusal | PolicyResolutionConflict | ProductRequestViolation,
    verified_overrides: tuple[OverrideRecord, ...],
) -> ConstraintRefusal | PolicyResolutionConflict | ProductRequestViolation:
    """The refusal, carrying every override the request attempted.

    ``D-IMPL-260`` P-I (criterion 10): *"the refusal path must preserve the
    attempted override and the entitlement result in replay."* The attempts
    were verified before any bound was held against a value, so every refusal
    this function's caller returns was reached with them in hand; this puts
    them on the determination rather than losing them with the resolution
    that never was. A copy rather than a mutation, because the refusal types
    are frozen contracts, and a no-op at the empty tuple, where the member is
    hash-transparent and the refusal's bytes must not move.
    """
    if not verified_overrides:
        return refusal
    return refusal.model_copy(update={"overrides": verified_overrides})


def _evidence_so_far(
    *,
    effective: Mapping[str, EffectiveParameter],
    guidance: Sequence[ParameterBound],
    applied: set[ProvenanceSource],
    verified_overrides: tuple[OverrideRecord, ...],
    asked_at: datetime,
) -> EffectiveRequest:
    """The resolution as it stands at one exit, rendered the one way.

    ``D-IMPL-264`` D-07/D-08. Called at every exit of
    :func:`resolve_effective_request` — the six refusal exits and the one
    completion — over the same locals, so a partial record and a completed one
    are the same construction sorted the same way, and dimension 2 cannot
    render one resolution as a family of blocks depending on where it exited.
    """
    return EffectiveRequest(
        parameters=tuple(effective[name] for name in sorted(effective)),
        guidance=tuple(sorted(guidance, key=_guidance_key)),
        overrides=verified_overrides,
        applied=tuple(sorted(applied, key=_sort_key)),
        asked_at=asked_at,
    )


def resolve_effective_request(
    *,
    request: ProductRequest,
    declared: ProductRequestContract,
    declared_source: ProvenanceSource,
    constraints: tuple[PinnedConstraint, ...],
    capabilities: tuple[TechnicalCapability, ...],
    capability_bindings: Mapping[str, str],
    verified_overrides: tuple[OverrideRecord, ...],
    perspective: Perspective,
    tenant: str,
    served_at: datetime,
    class_defaults: Mapping[str, Any] | None = None,
    class_source: ProvenanceSource | None = None,
) -> ResolutionOutcome:
    """The one resolution: defaults, caller, policy, capability, validation.

    ``served_at`` is a REQUIRED keyword with no default (`D-IMPL-358` step 5
    ruling B). It is the instant policy EFFECTIVITY is judged at, and it arrives
    as an argument because this function is pure and reads no clock. The re-check
    below is why a default would have been dangerous: this function independently
    re-evaluates applicability, so a selection made at ``served_at`` upstream
    would have been silently re-filtered at ``request.asked_at`` here, and the
    two layers would answer *"which policy was in force?"* two different ways.

    Whitepaper §7.8; SDK-defined per CLAUDE.md §11 (``D-IMPL-253`` Q4-Q8,
    ``D-IMPL-254``). The sequence and its reasons are in the module docstring.

    **Pure.** No clock, no registry, no I/O. ``constraints`` are already
    resolved artifacts and ``capabilities`` are already-read backend limits;
    the reference resolver that fetches both is a separate seam. Effectivity is
    evaluated at ``served_at`` (never ``request.asked_at``), and this function
    re-checks :func:`applicable` over every constraint it is handed — so a
    caller cannot
    smuggle in a constraint for another tenant, another class or another
    century by passing it directly.

    **A hard constraint is never dropped because another outranks it**
    (``D-IMPL-253`` Q4). Priority orders which surviving bound is *reported* on
    the parameter; every applicable hard bound is still held against the value,
    and every applied constraint's pin lands in ``applied`` whether or not its
    bound was the one reported.

    **``preferred`` never refuses** (Q5). It folds to guidance and to nothing
    else, so there is no branch it can reach that returns a refusal.

    **An absent bounded parameter is refused, never skipped** (``SEC-019``;
    ``D-IMPL-356`` D11, amending the realization of ``D-IMPL-253`` Q5, under
    which only ``required`` refused absence). A ``maximum``, ``minimum`` or
    ``allowed_set`` that reaches a parameter the caller omitted and no default
    filled is a ``required-absent`` :class:`ConstraintRefusal` carrying the
    highest-priority such bound, exactly as a ``required`` constraint's is.
    There is no value to hold to the bound, and skipping it served the request
    as though the bound did not exist — for
    :data:`~ccf.products.gates.DEBT_TOLERANCE_PARAMETER`, at any Debt. A
    parameter no registered policy constraint bounds keeps its behavior:
    guidance alone completes, and a technical capability's bound on an absent
    parameter (step 4) is still not a refusal. No value is invented for the
    absent parameter (CINV-01).

    **Worked case 3 is the one exception to "nothing is clamped."** A
    ``maximum`` on :data:`~ccf.products.gates.DEBT_TOLERANCE_PARAMETER` does
    not refuse a caller who asked for more tolerance than policy allows: the
    effective value becomes the policy's, with authority ``policy``, and the
    comparison that can still refuse — observed Debt against that tolerance —
    happens after assembly, where the observation exists. This is the module's
    **only** parameter-name-keyed branch and it keys on the SDK's own mechanism
    token, never on a deployment's vocabulary (CINV-01).

    **Overrides are honored only when verified.** An ``overridable`` constraint
    whose ``policy_id`` appears in ``verified_overrides`` with both ``entitled``
    and ``honored`` is not applied. Naming a policy is not authority to
    override it (Q7, Dave: *"Otherwise anyone who knows a policy ID could
    bypass it"*), and establishing entitlement is the caller's job — this
    function reads the verified record and never mints one.

    Args:
        request: The question, as asked.
        declared: The class's request contract, whose ``defaults`` and
            ``relative_defaults`` say what omission means — a literal value
            for the first, and an offset from ``request.asked_at`` for the
            second (``D-IMPL-325``).
        declared_source: The contract's own artifact pin — the provenance a
            defaulted value is recorded under.
        constraints: The policy constraints applicable at ``served_at``, each
            with the pin it was resolved by. Re-checked here at ``served_at``.
        capabilities: The backend limits in force.
        capability_bindings: Parameter name to capability token. A binding
            naming a token no capability supplies is a wiring failure, not a
            governed determination.
        verified_overrides: Override attempts whose entitlement has already
            been established, entitled or not. Every one is recorded.
        perspective: Who is asking and in what capacity; its ``role`` is the
            applicability axis.
        tenant: The tenant this resolution is for.
        class_defaults: Defaults the **product class** declares rather than the
            request contract — today exactly one, the class's
            :attr:`~ccf.products.contract.ServeObligations.default_debt_tolerance`
            (``24.6-L-04``, ``D-IMPL-251`` C1=A: a class figure is a default
            characteristic and never a policy boundary). Optional, defaulting
            to ``None``, which normalizes to an empty mapping — never a mutable
            default — so every call site written before this pair existed
            resolves exactly as it did. The **request contract's** defaults win
            for the same name: a contract that states what omission means for a
            parameter has said it more specifically than a class-wide
            characteristic.
        class_source: The pin those defaults were read from. Required whenever
            ``class_defaults`` is non-empty: a value with no provenance is the
            collapse ``D-IMPL-253`` Q1 forbids, and a default nobody can
            resolve later is worse than no default.

    Returns:
        A :class:`ResolutionOutcome` (``D-IMPL-264`` D-08). Its ``evidence``
        is ALWAYS present — the
        :class:`~ccf.products.provenance.EffectiveRequest` as it stood at the
        exit, every parameter resolved so far carrying ``(value, authority,
        source)`` and its bound, even when nothing constrained the request.
        Its ``refusal`` is ``None`` when the resolution completed, or one of
        the three governed determinations that stand instead: a
        :class:`ConstraintRefusal`, a :class:`PolicyResolutionConflict`, or
        the :class:`~ccf.products.request.ProductRequestViolation` the
        existing conformity comparison returns over the effective values. A
        refusal reached halfway through carries the half that ran (D-07):
        *"that partial work is still governed truth and belongs in replay."*

    Raises:
        ValueError: ``class_defaults`` is non-empty and ``class_source`` is
            ``None`` — a declared default with no artifact behind it — or it
            names a parameter ``declared`` does not declare as an argument,
            which would be a class-imposed ceiling rather than a default. The
            second is **unreachable through the SDK's own wiring** since
            ``D-IMPL-258`` (5) moved that refusal to registration and boot
            (:func:`~ccf.products.request.refuse_undeclared_class_default`);
            it is retained here as an invariant guard for callers of this pure
            function, which cannot be assumed to have booted through either.
        LookupError: ``capability_bindings`` names a capability token no member
            of ``capabilities`` supplies. Under ``D-IMPL-253`` amendment 2 (3)
            this is a configuration failure — the fabric cannot reach a valid
            governed determination — so it raises rather than returning data.
        TypeError: ``request.asked_at`` is zone-less. Checked here as well as
            inside :func:`applicable`, because a request with no applicable
            constraints never reaches that comparison and would otherwise
            record a resolution at an instant nobody can resolve a window
            against.
    """
    _require_aware(request.asked_at)
    # `D-IMPL-302`: the contract-aware typed decode, and it is FIRST so that
    # everything below computes over a number rather than over its lexical
    # form. A declared `number` that crossed the wire as canonical decimal text
    # becomes an exact `Decimal` here; every other value passes through
    # untouched. The caller's own request object is not mutated — the lexical
    # form stays available to the transport boundary, whose echo cross-check
    # runs against it.
    #
    # Decoding BEFORE resolution rather than beside the validation below is
    # what makes the bounds comparison, the policy constraints and the
    # effective value recorded in replay all numeric. Validating a decoded
    # value while comparing an undecoded one would be two readings of one
    # question.
    request = decode_declared_request(request, declared)
    class_declared: Mapping[str, Any] = (
        {} if class_defaults is None else class_defaults
    )
    if class_declared and class_source is None:
        raise ValueError(
            "class_defaults were supplied with no class_source: a default the"
            " fabric applies must name the artifact that declared it, or the"
            f" resolution records a value ({sorted(class_declared)}) nobody"
            " can resolve later (D-IMPL-253 Q1, amendment 2 (1))"
        )
    request_source = ProvenanceSource(
        kind="request", identity=content_hash(request), version=None
    )

    # 1. Defaults, then 2. the caller's overlay. A default is what omission
    #    means, not a competitor to a value the caller actually stated.
    #
    #    Two declarations of what omission means, and they are ordered: the
    #    product CLASS's characteristic first (`24.6-L-04`), then the request
    #    CONTRACT's, which wins for the same name because a contract speaks
    #    about one parameter of one class's surface and a class characteristic
    #    speaks about the class. Each carries its own pin, so the resolution
    #    says which document a defaulted value came out of.
    effective: dict[str, EffectiveParameter] = {}
    for name, value in class_declared.items():
        if name not in declared.arguments.properties:
            # A class characteristic the caller has no way to state is not a
            # default — it is a ceiling wearing a default's name, which is
            # exactly what `D-IMPL-251` C1=A took away from a product class.
            # It is also unanswerable: step 5 holds every effective value to
            # the declared surface, so folding it in would refuse the request
            # as `undeclared-parameter` and report a caller's mistake for a
            # deployment's. Raised rather than returned, on the
            # `capability_bindings` precedent: the fabric cannot reach a valid
            # governed determination (`D-IMPL-253` amendment 2 (3)).
            #
            # **UNREACHABLE through the SDK's own wiring since `D-IMPL-258`
            # (5), and retained deliberately.** Dave moved the refusal to
            # declaration time: `ccf.products.request.refuse_undeclared_class_default`
            # runs at registration
            # (`ccf.products.contract.register_product_class`) and at boot
            # (`ccf.products.resolver.build_governed_resolver`), so a class
            # that contradicts its own contract never becomes servable and
            # this branch never sees one. It stays because THIS function is a
            # pure, public function over its arguments — it cannot assume its
            # caller booted through either seam, and a silent fold-in for a
            # caller that did not would be the silent repair this codebase
            # refuses everywhere. It is the last line, not the line.
            raise ValueError(
                f"the product class declares a default for {name!r}, which"
                f" its request contract ({declared.schema_name}"
                f" @{declared.schema_version}) does not declare as an"
                " argument; a caller who cannot state the parameter cannot"
                " accept a product the default would withhold, so the default"
                " would be a class-imposed ceiling (D-IMPL-251 C1=A). Declare"
                " the argument on the request contract, or remove the class"
                " default"
            )
        if name in request.parameters:
            continue
        assert class_source is not None  # guarded above; narrows for mypy
        effective[name] = EffectiveParameter(
            name=name, value=value, authority="default", source=class_source
        )
    for name, value in declared.defaults.items():
        if name in request.parameters:
            continue
        effective[name] = EffectiveParameter(
            name=name, value=value, authority="default", source=declared_source
        )
    # The same declaration in the other register: a default expressed as an
    # offset from the request's own instant rather than as a literal
    # (`D-IMPL-325`). It resolves HERE, beside the literal defaults, for two
    # reasons. It is still a default — what omission means — so the caller's
    # overlay below must still win over it. And `request.asked_at` is the
    # instant this whole function already evaluates effectivity at, so the
    # value is a function of the QUESTION and never of a clock; the function
    # stays pure.
    #
    # **What is recorded is the resolved literal, never the offset.** A rule
    # carried into the replay record would be re-evaluated at replay time and
    # would answer one decision differently on two days.
    for name, relative in declared.relative_defaults.items():
        if name in request.parameters:
            continue
        effective[name] = EffectiveParameter(
            name=name,
            value=relative.resolve(request.asked_at),
            authority="default",
            source=declared_source,
        )
    for name, value in request.parameters.items():
        effective[name] = EffectiveParameter(
            name=name, value=value, authority="caller", source=request_source
        )

    # `applied` is present even when nothing constrained the request, because
    # "nothing applied" is a claim that needs the same evidence as "this
    # applied": the contract WAS consulted, and its pin is what an examiner
    # resolves that claim against.
    applied: set[ProvenanceSource] = {declared_source}
    if class_declared:
        # The class declaration was consulted, so its pin is evidence whether
        # or not the caller left the parameter for it to fill.
        assert class_source is not None  # guarded above; narrows for mypy
        applied.add(class_source)

    # 3. Policy constraints. Re-checked for applicability here, so the purity
    #    of this function is not also a trust assumption about its caller.
    honored = {
        record.policy_id
        for record in verified_overrides
        if record.entitled and record.honored
    }
    active: list[PinnedConstraint] = []
    for pinned in constraints:
        if not applicable(
            pinned.constraint,
            product_class=request.schema_name,
            tenant=tenant,
            perspective_role=perspective.role,
            intent=request.intent,
            # `D-IMPL-358` step 5 ruling B: the SAME instant the selection used.
            served_at=served_at,
        ):
            continue
        if pinned.constraint.overridable and pinned.constraint.policy_id in honored:
            continue
        active.append(pinned)

    by_parameter: dict[str, list[PinnedConstraint]] = {}
    for pinned in active:
        applied.add(_source_of(pinned))
        by_parameter.setdefault(pinned.constraint.parameter, []).append(pinned)

    guidance: list[ParameterBound] = []

    def evidence_so_far() -> EffectiveRequest:
        # What this resolution has established at the moment it is called —
        # read off the accumulators as they stand, so a refusal three lines
        # below carries exactly what was resolved above it (D-IMPL-264 D-07).
        return _evidence_so_far(
            effective=effective,
            guidance=guidance,
            applied=applied,
            verified_overrides=verified_overrides,
            asked_at=request.asked_at,
        )

    for key in sorted(by_parameter):
        folded = _fold(key=key, pinned=by_parameter[key])
        if isinstance(folded, PolicyResolutionConflict):
            return ResolutionOutcome(
                evidence=evidence_so_far(),
                refusal=_with_overrides(folded, verified_overrides),
            )
        candidates, parameter_guidance = folded
        guidance.extend(parameter_guidance)

        presence = [c for c in candidates if c.fold == _PRESENCE]
        if presence and key not in effective:
            absent = ConstraintRefusal(
                reason="required-absent",
                key=key,
                detail=(
                    f"{key}: an applicable constraint requires this parameter"
                    " and the request neither supplies it nor does the class"
                    " declare a default for it, so there is no value to govern"
                ),
                bound=presence[0].bound,
                requested=None,
                overrides=verified_overrides,
            )
            return ResolutionOutcome(evidence=evidence_so_far(), refusal=absent)
        if key not in effective:
            # SEC-019 (`D-IMPL-356` D11, amending the realization of
            # `D-IMPL-253` Q5): a BOUNDING constraint on a parameter with no
            # value is refused exactly as `required` is, never skipped. There
            # is no value to hold to the bound, and skipping it served the
            # request as though the bound did not exist — for
            # `debt_tolerance`, at any Debt. The bound reported is the
            # highest-priority one; every applied pin is already in `applied`.
            bounding = sorted(
                (c for c in candidates if c.fold != _PRESENCE), key=_order
            )
            if bounding:
                unheld = ConstraintRefusal(
                    reason="required-absent",
                    key=key,
                    detail=(
                        f"{key}: an applicable {bounding[0].bound.operator}"
                        " constraint bounds this parameter and the request"
                        " neither supplies it nor does the class declare a"
                        " default for it, so there is no value to hold to the"
                        " bound; an absent bounded parameter is refused, not"
                        " skipped (SEC-019, D-IMPL-356 D11)"
                    ),
                    bound=bounding[0].bound,
                    requested=None,
                    overrides=verified_overrides,
                )
                return ResolutionOutcome(evidence=evidence_so_far(), refusal=unheld)
            # Guidance alone (`preferred`) never refuses (Q5), absent or not.
            continue

        ordered = sorted(
            (c for c in candidates if c.fold != _PRESENCE), key=_order
        )
        # D-04: every applied constraint holds
        checked = ordered
        for candidate in checked:
            refusal = _refuse_against(
                key=key, value=effective[key].value, candidate=candidate
            )
            if refusal is None:
                continue
            if candidate.fold == _CEILING and key == DEBT_TOLERANCE_PARAMETER:
                # Worked case 3, the one exception to "nothing is clamped": the
                # tolerance becomes the policy's rather than the caller's, and
                # the comparison that can still refuse runs after assembly,
                # against observed Debt, where the observation exists.
                effective[key] = EffectiveParameter(
                    name=key,
                    value=candidate.bound.value,
                    authority="policy",
                    source=candidate.bound.source,
                    bound=candidate.bound,
                )
                continue
            return ResolutionOutcome(
                evidence=evidence_so_far(),
                refusal=_with_overrides(refusal, verified_overrides),
            )
        if ordered and effective[key].bound is None:
            effective[key] = effective[key].model_copy(
                update={"bound": ordered[0].bound}
            )

    # 4. Technical capability. Its provenance is a backend identity and never
    #    an artifact pin (amendment 2 (1)).
    supplied = {capability.capability: capability for capability in capabilities}
    for name in sorted(capability_bindings):
        token = capability_bindings[name]
        capability = supplied.get(token)
        if capability is None:
            raise LookupError(
                f"capability binding for parameter {name!r} names"
                f" {token!r}, which no supplied capability provides; a binding"
                " onto a capability the backend does not declare is a wiring"
                " failure and cannot be answered as a governed determination"
                " (D-IMPL-253 amendment 2 (3))"
            )
        technical = ParameterBound(
            operator="maximum",
            value=capability.maximum,
            authority="technical",
            source=ProvenanceSource(
                kind="capability", identity=capability.identity, version=None
            ),
        )
        applied.add(technical.source)
        if name not in effective:
            continue
        presented = _as_number(effective[name].value)
        if presented is not None and presented > capability.maximum:
            exceeded = ConstraintRefusal(
                reason="bound-exceeded",
                key=name,
                detail=(
                    f"{name}: {presented} exceeds the technical maximum"
                    f" {capability.maximum} of capability {token!r} on"
                    f" {capability.identity!r}; the limit is the substrate's"
                    " and is refused by name rather than silently narrowed"
                    " (D-IMPL-253 Q21)"
                ),
                bound=technical,
                requested=effective[name].value,
                overrides=verified_overrides,
            )
            return ResolutionOutcome(evidence=evidence_so_far(), refusal=exceeded)
        if effective[name].bound is None:
            effective[name] = effective[name].model_copy(
                update={"bound": technical}
            )

    # 5. Validation, over the EFFECTIVE values. A default and a policy value
    #    are held to exactly the declaration a caller's value is.
    values = {name: parameter.value for name, parameter in effective.items()}
    verdict = refuse_request(
        request=request.model_copy(update={"parameters": values}), declared=declared
    )
    if verdict is not None:
        # The whole effective set was resolved; only conformity refused it.
        return ResolutionOutcome(
            evidence=evidence_so_far(),
            refusal=_with_overrides(verdict, verified_overrides),
        )

    resolved = ResolutionOutcome(
        evidence=evidence_so_far(),
        # Stated, not defaulted: the completion says there is no refusal
        # rather than leaving absence to be inferred (D-IMPL-264 P-2).
        refusal=None,
    )
    # D-IMPL-254: the Authority layer's value is the record, never a scalar
    return resolved


# --- the seam: reading the Control Plane at the request's own instant --------


class ConstraintEffectivityConflict(ValueError):
    """Two authoritative statements are in force at once and disagree.

    SDK-defined (CLAUDE.md §11); whitepaper §7.8. Raised, never returned, and
    the distinction is Dave's rule for the phase: a governed *"no"* is a
    determination the fabric reached, while two contradicting authoritative
    inputs are a state in which the fabric **cannot determine what is true** —
    which is a configuration failure of the deployment's own Control Plane and
    is reported as one (``D-IMPL-253`` Q15: *"retain exceptions for actual
    configuration/invariant contradictions"*).

    Two shapes reach it, and they are the same defect:

    * two *versions of one constraint key* whose effectivity windows both
      contain ``asked_at`` — the Control Plane says the parameter is bounded
      two ways at one instant, and picking either would make replay of the
      same historical decision resolvable two ways;
    * two *versions of the entitlement policy* registered under one key, when
      a request names an override — an entitlement artifact carries no
      effectivity window, so with more than one version there is no fact of
      the matter about which grant is in force, and honoring an override under
      an undetermined grant is exactly the elevation ``D-IMPL-253`` Q7
      forbids.

    The message names the key and every version, because the fix is a Control
    Plane edit and the operator making it needs both sides.
    """


@runtime_checkable
class _ConstraintSource(Protocol):
    """The Control Plane read surface a constraint set is resolved through.

    Module-private, and stated rather than reached for as a concrete registry:
    :class:`~ccf.controlplane.resolution.ControlPlaneResolution` — the shipped
    read-only Protocol — carries ``resolve``, ``versions``, ``peek`` and
    ``artifact_class_of`` but **not** ``keys_of_class``, and discovering which
    keys hold constraints is exactly what this seam has to do. So the shape
    named here is the registry's read surface plus that one method.

    Private because plan ``24.6-03`` fixes this module's public names; a
    deployment substituting a remote Control Plane conforms to
    :class:`~ccf.controlplane.registry.ControlPlaneProtocol` and to
    ``keys_of_class``, both of which already exist on that surface.

    The registry's *latest* read is deliberately absent from this surface: a
    resolution that reached for the most recently registered version would
    resolve a different policy at replay than at decision time (``D-IMPL-253``
    Q6), and a method that is not on the surface cannot be reached by mistake —
    the :class:`~ccf.controlplane.registry.ReplayResolver` argument, applied
    here.
    """

    def keys_of_class(self, class_id: str) -> tuple[str, ...]:
        """Every key bound to ``class_id``."""
        ...

    def versions(self, key: str) -> tuple[str, ...]:
        """Every version registered under ``key``, oldest first."""
        ...

    def peek(self, key: str, version: str) -> object:
        """The artifact at ``(key, version)``, unaudited."""
        ...

    def resolve(self, key: str, version: str) -> object:
        """The exact artifact at ``(key, version)`` — audited."""
        ...


def constraints_in_force(
    control_plane: _ConstraintSource, *, served_at: datetime
) -> tuple[PinnedConstraint, ...]:
    """Every policy constraint the Control Plane holds in force at ``served_at``.

    `D-IMPL-358` step 5 ruling B: the TRUSTED serve instant, not the question's.
    See :func:`applicable` for why the instant moved and why replay is unaffected.

    SDK-defined (CLAUDE.md §11); whitepaper §7.8, and ``D-IMPL-253`` Q6 below.
    The superseded reasoning, kept because it names the risk that had to be
    answered before the instant could move — Dave's words: *"asked_at,
    absolutely. Otherwise replay of the same
    historical decision can resolve a different policy."*

    The walk is four steps and each is the one it is for a reason:
    :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.keys_of_class` finds
    the keys bound to :data:`~ccf.controlplane.artifacts.POLICY_CONSTRAINT`
    (registry state is the single store — IN-03 — so nothing here keeps a
    second index); ``versions`` enumerates the contents under each;
    :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.peek` examines them
    **unaudited**, because examining a version to find the one in force is not
    a resolution and auditing it would record reads that never happened (the
    ``WR-08`` argument, verbatim); and ``resolve`` then reads back *exactly*
    the one version selected, which is the read that is audited and the read an
    examiner replays.

    The registry's *latest* read is never called and cannot be: it is not on
    :class:`_ConstraintSource`.

    Args:
        control_plane: The Control Plane's read surface.
        served_at: The TRUSTED serve instant (`D-IMPL-358` step 5 ruling B),
            supplied by the caller that read the fabric clock once. Timezone-aware, always.

    Returns:
        One :class:`PinnedConstraint` per key in force, ordered by key so two
        runs over one registry produce one ordering. Applicability — the four
        axes — is **not** evaluated here: this answers *what is in force*, and
        :func:`applicable` answers *what reaches this request*.

    Raises:
        ConstraintEffectivityConflict: two versions of one key are both in
            force at ``served_at``.
        TypeError: ``served_at`` is zone-less, or a key bound to the constraint
            class holds something that is not a
            :class:`~ccf.controlplane.artifacts.PolicyConstraint` — a
            registration that bypassed the typed path, and a broken deployment
            rather than a governed determination.
    """
    _require_aware(served_at)
    pinned: list[PinnedConstraint] = []
    for key in sorted(control_plane.keys_of_class(POLICY_CONSTRAINT.class_id)):
        in_force: list[tuple[str, PolicyConstraint]] = []
        for version in control_plane.versions(key):
            candidate = control_plane.peek(key, version)
            if not isinstance(candidate, PolicyConstraint):
                raise TypeError(
                    f"Control Plane key {key!r} is bound to"
                    f" {POLICY_CONSTRAINT.class_id!r} but version {version!r}"
                    f" holds {type(candidate).__name__}; a constraint set is"
                    " read as constraints or it is not read"
                )
            if _in_window(candidate, served_at=served_at):
                in_force.append((version, candidate))
        if not in_force:
            continue
        if len(in_force) > 1:
            raise ConstraintEffectivityConflict(
                f"two versions of Control Plane key {key!r} are both in force"
                f" at {served_at.isoformat()}:"
                f" {', '.join(repr(version) for version, _ in in_force)}; the"
                " effectivity windows overlap, so which boundary governs this"
                " request has no answer — the fabric refuses to pick one"
                " rather than resolve a decision two ways at replay"
                " (D-IMPL-253 Q6)"
            )
        version, _examined = in_force[0]
        # The read that is audited, and the read an examiner replays: exact,
        # never "latest", and never the object `peek` handed back.
        resolved = control_plane.resolve(key, version)
        if not isinstance(resolved, PolicyConstraint):  # pragma: no cover - see peek
            raise TypeError(
                f"Control Plane key {key!r} resolved {type(resolved).__name__}"
                f" at version {version!r} after peeking a PolicyConstraint"
            )
        pinned.append(
            PinnedConstraint(key=key, version=version, constraint=resolved)
        )
    return tuple(pinned)


@runtime_checkable
class PolicyConstraintResolver(Protocol):
    """The seam between one question and every authority that bounds it.

    SDK-defined (CLAUDE.md §11); ``D-IMPL-253`` Q8, in Dave's words: *"Protocol
    plus reference implementation. This is an SDK seam likely to acquire
    different Control Plane backends."*

    A Protocol rather than a base class, on
    :class:`~ccf.halflife.debt.DebtFactorScorerProtocol`'s reasoning: a
    deployment whose policy lives in an external governance system substitutes
    by **conforming**, and the SDK's reference carries no privileged status.

    ``resolver_id`` and ``resolver_version`` are on the surface for that
    Protocol's reason too — *the resolver in force must be pinnable into
    replay*, because an effective request is only reproducible alongside the
    resolution that produced it.

    Keyword-only throughout: five of the inputs are strings, and a
    transposition would resolve a different tenant's policy without failing.

    **A conforming resolver refuses an absent bounded parameter** (``SEC-019``,
    ``D-IMPL-356`` D11), as :func:`resolve_effective_request` does. The
    governed resolver hands the tolerance step only what a COMPLETED
    resolution established, and a completed resolution with no tolerance is
    its statement that no policy bound applies to one; a resolver that skipped
    an absent bounded tolerance would be served at any Debt.
    """

    @property
    def resolver_id(self) -> str:
        """Stable identity of this resolver."""
        ...

    @property
    def resolver_version(self) -> str:
        """Version of this resolver's resolution."""
        ...

    def resolve(
        self,
        *,
        product_class: str,
        request: ProductRequest,
        declared: ProductRequestContract,
        declared_source: ProvenanceSource,
        perspective: Perspective,
        intent: str,
        tenant: str,
        capabilities: tuple[TechnicalCapability, ...],
        served_at: datetime,
        class_defaults: Mapping[str, Any] | None = None,
        class_source: ProvenanceSource | None = None,
    ) -> ResolutionOutcome:
        """Resolve ``request`` into its effective values, or refuse it.

        The instant policy effectivity is judged at is ``served_at`` — the
        trusted live instant the resolver read once for this serve and hands
        in — and no longer ``request.asked_at`` (`D-IMPL-358` step 5 ruling B,
        amending ``D-IMPL-253`` Q6; `D-IMPL-364` SEC-010 E1). ``asked_at``
        remains the as-of boundary of the graph read. A resolver that read a
        clock of its own would resolve a different policy at replay than at
        decision time (``D-IMPL-98``); the one instant it may use is the
        ``served_at`` it is handed, which the record carries.

        Args:
            product_class: The class the request addresses.
            request: The question, as asked.
            declared: The class's request contract — the ``defaults`` and
                ``relative_defaults`` that say what omission means, and the
                ``capability_bindings`` that say which declared parameter a
                technical limit bounds.
            declared_source: That contract's own artifact pin.
            perspective: Who is asking and in what capacity.
            intent: The decision the product is being assembled for.
            tenant: The tenant this resolution is for.
            capabilities: The backend limits in force, read off the substrate
                by the caller — this seam reads no store.
            class_defaults: Defaults the product CLASS declares, with
                ``class_source`` as their pin. Optional and ``None``-defaulted
                so a caller that has no class declaration in hand resolves
                exactly as before; see
                :func:`resolve_effective_request` for the ordering against the
                request contract's own defaults (``24.6-L-04``).
            class_source: The artifact pin ``class_defaults`` were read from.

        Returns:
            The :class:`ResolutionOutcome` (``D-IMPL-264`` D-08): the completed
            :class:`~ccf.products.provenance.EffectiveRequest`, or the governed
            determination that stands instead of one — and, either way, the
            evidence the resolution accumulated before it exited.
        """
        ...


#: An override attempt naming a policy no constraint in force carries. A
#: positive sentinel in the :data:`~ccf.replay.record.NO_HITL_ACTIONS` voice
#: rather than an empty string: *"the fabric found no constraint under that
#: name"* is a fact about the attempt and lands in the replay record as one,
#: and :class:`~ccf.products.provenance.OverrideRecord` requires the lane
#: precisely so that a nameless claim cannot be filed.
_NO_CONSTRAINT_IN_FORCE: Final[str] = "no-constraint-in-force"


@dataclass(frozen=True)
class ReferencePolicyConstraintResolver:
    """The SDK's reference resolver: the Control Plane in force at ``served_at``.

    SDK-defined (CLAUDE.md §11); ``D-IMPL-253`` Q6/Q7/Q8. Ships alongside the
    Protocol per CLAUDE.md §11, and is **the v0 default, not a placeholder for
    one** — the Control Plane is itself in-process (CLAUDE.md §13), so the
    constraints resolved here are exactly as durable as the registry they are
    read from. A Control Plane backend that governs policy elsewhere is an
    alternative implementation of the same Protocol, substituted without
    touching a consumer.

    **It fetches, and then it calls the pure function.** The seam is split
    deliberately: :func:`constraints_in_force` and the entitlement read are the
    only I/O, and :func:`resolve_effective_request` — which decides everything
    — is pure over its arguments and testable against the four worked cases
    with no registry at all.

    **Naming a policy is not authority to override it** (Q7, Dave: *"Otherwise
    anyone who knows a policy ID could bypass it"*). Every name in
    ``request.policy_overrides`` is verified against the principal's own
    :class:`~ccf.products.entitlement.ProductEntitlementGrant`, and both facts
    — entitled, and honored — are recorded whichever way they came out. An
    unentitled attempt is a thing that happened.

    Attributes:
        control_plane: The Control Plane's read surface. The concrete
            :class:`~ccf.controlplane.registry.ControlPlaneRegistry` conforms;
            so does a remote plane offering the same four reads.
        entitlement_key: The key this tenant's
            :class:`~ccf.products.entitlement.ProductEntitlementPolicy` is
            registered under
            (:func:`~ccf.products.entitlement.product_entitlement_key`), or
            ``None`` when the deployment declares none. ``None`` and an absent
            policy mean the same thing and are treated the same way: **no
            override is entitled**, which is deny-by-default rather than an
            error, on the posture the delivery door already takes.
    """

    control_plane: _ConstraintSource
    entitlement_key: str | None

    @property
    def resolver_id(self) -> str:
        return REFERENCE_CONSTRAINT_RESOLVER_ID

    @property
    def resolver_version(self) -> str:
        return REFERENCE_CONSTRAINT_RESOLVER_VERSION

    def resolve(
        self,
        *,
        product_class: str,
        request: ProductRequest,
        declared: ProductRequestContract,
        declared_source: ProvenanceSource,
        perspective: Perspective,
        intent: str,
        tenant: str,
        capabilities: tuple[TechnicalCapability, ...],
        served_at: datetime,
        class_defaults: Mapping[str, Any] | None = None,
        class_source: ProvenanceSource | None = None,
    ) -> ResolutionOutcome:
        """Read what is in force, verify the overrides, resolve. See the Protocol.

        Raises:
            ConstraintEffectivityConflict: the Control Plane holds two
                versions of one constraint key in force at ``served_at``,
                or two versions of the entitlement policy under one key while
                the request names an override.
            LookupError: ``declared.capability_bindings`` names a capability
                token no member of ``capabilities`` supplies — a wiring
                failure, raised by :func:`resolve_effective_request`.
            TypeError: ``request.asked_at`` or ``served_at`` is zone-less, or a
                Control Plane key holds an artifact of the wrong class.
        """
        # `D-IMPL-358` step 5 ruling B: effectivity at the TRUSTED serve instant.
        # The graph is still read at `request.asked_at` — the caller's question
        # keeps its own boundary and only the POLICY reading moved.
        in_force = constraints_in_force(self.control_plane, served_at=served_at)
        reaching = tuple(
            pinned
            for pinned in in_force
            if applicable(
                pinned.constraint,
                product_class=product_class,
                tenant=tenant,
                perspective_role=perspective.role,
                intent=intent,
                served_at=served_at,
            )
        )
        return resolve_effective_request(
            served_at=served_at,
            request=request,
            declared=declared,
            declared_source=declared_source,
            constraints=reaching,
            capabilities=capabilities,
            capability_bindings=declared.capability_bindings,
            verified_overrides=self._verified_overrides(
                request=request,
                perspective=perspective,
                reaching=reaching,
                tenant=tenant,
            ),
            perspective=perspective,
            tenant=tenant,
            class_defaults=class_defaults,
            class_source=class_source,
        )

    # --- the override half (D-IMPL-253 Q7) ---------------------------------

    def _verified_overrides(
        self,
        *,
        request: ProductRequest,
        perspective: Perspective,
        reaching: tuple[PinnedConstraint, ...],
        tenant: str,
    ) -> tuple[OverrideRecord, ...]:
        """One record per (named policy, constraint it names), entitled or not.

        A record per *constraint* rather than per name, because
        :class:`~ccf.products.provenance.OverrideRecord` carries the version of
        the artifact the attempt was made against and two constraints sharing a
        ``policy_id`` are two lanes. A name no constraint in force carries
        still produces a record — at :data:`_NO_CONSTRAINT_IN_FORCE`, and
        ``honored=False`` — because an attempt to override a policy that is not
        there is a thing an examiner should be able to see.
        """
        if not request.policy_overrides:
            return ()
        grant, grant_source = self._entitlement(
            perspective=perspective, tenant=tenant
        )
        records: list[OverrideRecord] = []
        for policy_id in request.policy_overrides:
            # D-07: entitlement verified here
            entitled = grant is not None and policy_id in grant.overridable_policies
            named = tuple(
                pinned
                for pinned in reaching
                if pinned.constraint.policy_id == policy_id
            )
            if not named:
                records.append(
                    OverrideRecord(
                        policy_id=policy_id,
                        policy_version=_NO_CONSTRAINT_IN_FORCE,
                        principal_id=perspective.principal_id,
                        entitled=entitled,
                        honored=False,
                        grant_source=grant_source if entitled else None,
                    )
                )
                continue
            for pinned in named:
                records.append(
                    OverrideRecord(
                        policy_id=policy_id,
                        policy_version=pinned.version,
                        principal_id=perspective.principal_id,
                        entitled=entitled,
                        # A constraint the deployment declared non-overridable
                        # is not overridable by an entitled principal either:
                        # `overridable` is the artifact's own statement about
                        # whether the boundary admits an exception at all.
                        honored=entitled and pinned.constraint.overridable,
                        grant_source=grant_source if entitled else None,
                    )
                )
        return tuple(records)

    def _entitlement(
        self, *, perspective: Perspective, tenant: str
    ) -> tuple[ProductEntitlementGrant | None, ProvenanceSource | None]:
        """This principal's grant, read exactly — or the absence of one.

        Read the way replay reads: ``versions`` enumerates, ``peek`` examines
        unaudited, and ``resolve`` reads back the one version selected.
        The registry's *latest* read is unreachable from
        :class:`_ConstraintSource`, which is the point — an override honored
        under "whatever was registered most recently" would replay against a
        different grant than the one that decided it.

        **Absent is deny, not error.** No key, no versions, or a policy naming
        no entry for this principal all yield ``(None, None)`` and therefore an
        unentitled attempt: the deny-by-default posture the delivery door
        already takes (*"a door whose governance configuration is absent must
        not become servable"*).

        Args:
            perspective: The :class:`~ccf.projection.plan.Perspective` the
                calling surface resolved at the door; only its ``principal_id``
                is read here, and never a claim carried in the request body.
                The whole perspective travels rather than a bare
                ``principal_id`` parameter because entitlement is decided at
                the door and the engine receives it already resolved
                (``tests/invariants/test_mcp_role_separation.py``, Pitfall 3).
            tenant: The tenant this resolution is for, held against the
                policy's own ``tenant_id``.

        Returns:
            The grant this principal holds and the artifact pin the
            entitlement was established from, or ``(None, None)``.

        Raises:
            ConstraintEffectivityConflict: more than one version is registered
                under the entitlement key. The artifact carries no effectivity
                window, so there is no fact of the matter about which grant is
                in force, and an override honored under an undetermined grant
                is the elevation Q7 forbids.
            TypeError: the key holds something that is not a
                :class:`~ccf.products.entitlement.ProductEntitlementPolicy`, or
                one whose own ``tenant_id`` is not the tenant whose key it was
                found under. A near-miss is refused, never interpreted — the
                ``15.5-CLOSE-REVIEWS.md`` finding P1 check, at this seam.
        """
        if self.entitlement_key is None:
            return None, None
        key = self.entitlement_key
        versions = self.control_plane.versions(key)
        if not versions:
            return None, None
        if len(versions) > 1:
            raise ConstraintEffectivityConflict(
                f"{len(versions)} versions of the entitlement policy are"
                f" registered under {key!r}:"
                f" {', '.join(repr(version) for version in versions)}; the"
                " artifact carries no effectivity window, so which grant is in"
                " force has no answer — and an override honored under an"
                " undetermined grant is exactly the elevation naming a policy"
                " must not achieve (D-IMPL-253 Q7)"
            )
        version = versions[0]
        examined = self.control_plane.peek(key, version)
        if not isinstance(examined, ProductEntitlementPolicy):
            raise TypeError(
                f"artifact under {key!r} is not a ProductEntitlementPolicy"
                f" (got {type(examined).__name__}); an override is verified"
                " against a declared grant or it is not verified"
            )
        if examined.tenant_id != tenant:
            raise TypeError(
                f"policy under {key!r} declares tenant"
                f" {examined.tenant_id!r}, not {tenant!r}; the key and the"
                " artifact's own tenant are supplied independently, and a"
                " near-miss is refused rather than interpreted"
            )
        # The audited read of the exact version examined above.
        self.control_plane.resolve(key, version)
        try:
            grant = examined.grant_for(principal_id=perspective.principal_id)
        except PrincipalNotEntitled:
            return None, None
        return grant, ProvenanceSource(
            kind="artifact", identity=key, version=version
        )
