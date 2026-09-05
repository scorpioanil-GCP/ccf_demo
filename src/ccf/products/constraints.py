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
   declared for omission (``ProductRequestContract.defaults``), with authority
   ``default`` and the contract's own artifact pin as its source.
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
   governed :class:`PolicyResolutionConflict`, not a silent pick.
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

Pure over its arguments: **no clock, no registry lookup, no I/O; the instant is
a field of the request** (``request.asked_at``). A resolution that moved with
the time of day, or with what was registered elsewhere, would not be
reproducible at replay — which is the property every comparison in this package
is required to have, and the reason ``D-IMPL-253`` Q6 puts constraint
effectivity at ``asked_at``. The reference resolver that *reads* the Control
Plane for the constraint set is a separate seam; it fetches, and then it calls
this.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Final, Literal

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, content_hash
from ccf.controlplane.artifacts import PolicyConstraint
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
    refuse_request,
)
from ccf.projection.plan import Perspective

__ccf_mode__ = "algorithmic"

__all__ = [
    "CAPABILITY_TRAVERSAL_DEPTH",
    "ConstraintRefusal",
    "PinnedConstraint",
    "PolicyResolutionConflict",
    "TechnicalCapability",
    "applicable",
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
    ``allowed_set``, and for a ``required`` parameter still absent after
    defaults. **A returned value, never an exception** — the posture
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
    """

    reason: Literal["bound-exceeded", "not-in-allowed-set", "required-absent"]
    key: str
    detail: str
    bound: ParameterBound
    requested: Any


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
            "asked_at must be timezone-aware: constraint effectivity is"
            " evaluated at the request's own instant and there is no implicit"
            " UTC in this fabric (D-IMPL-98, D-IMPL-38)"
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
    asked_at: datetime,
) -> bool:
    """Does this constraint reach this request, at this instant?

    Two questions, both answered here so no caller answers half of one. The
    **axes**: every member of ``applies_to`` that is not ``None`` must equal
    the corresponding input, conjunctively — ``None`` means *any*, and a
    constraint that narrows nothing applies to everything. The **window**:
    ``effective_from <= asked_at`` and ``asked_at < effective_until`` when an
    end is stated, half-open so a constraint that ends at the instant another
    begins never applies twice.

    Evaluated at ``asked_at`` and never at "now" (``D-IMPL-253`` Q6, Dave:
    *"asked_at, absolutely. Otherwise replay of the same historical decision
    can resolve a different policy."*).

    Args:
        constraint: The artifact.
        product_class: The class the request addresses.
        tenant: The tenant the request is being resolved for.
        perspective_role: The Π role-conditioning in force.
        intent: The decision the product is being assembled for.
        asked_at: The request's own instant. Timezone-aware, always.

    Returns:
        Whether the constraint applies.

    Raises:
        TypeError: ``asked_at`` is zone-less. There is no implicit UTC in this
            fabric (``D-IMPL-98`` puts the instant on the request precisely so
            it is stated rather than assumed; ``D-IMPL-38`` refuses a zone-less
            timestamp at artifact load), and comparing a naive instant against
            an aware effectivity window would either raise deep inside a
            comparison or, worse, silently answer for the wrong hour.
    """
    _require_aware(asked_at)
    axes = (
        (constraint.applies_to.product_class, product_class),
        (constraint.applies_to.tenant, tenant),
        (constraint.applies_to.perspective_role, perspective_role),
        (constraint.applies_to.intent, intent),
    )
    for narrowed, presented in axes:
        if narrowed is not None and narrowed != presented:
            return False
    if constraint.effective_from > asked_at:
        return False
    return constraint.effective_until is None or asked_at < constraint.effective_until


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
) -> EffectiveRequest | ConstraintRefusal | PolicyResolutionConflict | ProductRequestViolation:
    """The one resolution: defaults, caller, policy, capability, validation.

    Whitepaper §7.8; SDK-defined per CLAUDE.md §11 (``D-IMPL-253`` Q4-Q8,
    ``D-IMPL-254``). The sequence and its reasons are in the module docstring.

    **Pure.** No clock, no registry, no I/O. ``constraints`` are already
    resolved artifacts and ``capabilities`` are already-read backend limits;
    the reference resolver that fetches both is a separate seam. Effectivity is
    evaluated at ``request.asked_at``, and this function re-checks
    :func:`applicable` over every constraint it is handed — so a caller cannot
    smuggle in a constraint for another tenant, another class or another
    century by passing it directly.

    **A hard constraint is never dropped because another outranks it**
    (``D-IMPL-253`` Q4). Priority orders which surviving bound is *reported* on
    the parameter; every applicable hard bound is still held against the value,
    and every applied constraint's pin lands in ``applied`` whether or not its
    bound was the one reported.

    **``preferred`` never refuses** (Q5). It folds to guidance and to nothing
    else, so there is no branch it can reach that returns a refusal.

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
        declared: The class's request contract, whose ``defaults`` say what
            omission means.
        declared_source: The contract's own artifact pin — the provenance a
            defaulted value is recorded under.
        constraints: The policy constraints applicable at ``request.asked_at``,
            each with the pin it was resolved by. Re-checked here.
        capabilities: The backend limits in force.
        capability_bindings: Parameter name to capability token. A binding
            naming a token no capability supplies is a wiring failure, not a
            governed determination.
        verified_overrides: Override attempts whose entitlement has already
            been established, entitled or not. Every one is recorded.
        perspective: Who is asking and in what capacity; its ``role`` is the
            applicability axis.
        tenant: The tenant this resolution is for.

    Returns:
        The :class:`~ccf.products.provenance.EffectiveRequest` — every
        parameter carrying ``(value, authority, source)`` and its bound, even
        when nothing constrained the request — or one of the three governed
        determinations: a :class:`ConstraintRefusal`, a
        :class:`PolicyResolutionConflict`, or the
        :class:`~ccf.products.request.ProductRequestViolation` the existing
        conformity comparison returns over the effective values.

    Raises:
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
    request_source = ProvenanceSource(
        kind="request", identity=content_hash(request), version=None
    )

    # 1. Defaults, then 2. the caller's overlay. A default is what omission
    #    means, not a competitor to a value the caller actually stated.
    effective: dict[str, EffectiveParameter] = {}
    for name, value in declared.defaults.items():
        if name in request.parameters:
            continue
        effective[name] = EffectiveParameter(
            name=name, value=value, authority="default", source=declared_source
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
            asked_at=request.asked_at,
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
    for key in sorted(by_parameter):
        folded = _fold(key=key, pinned=by_parameter[key])
        if isinstance(folded, PolicyResolutionConflict):
            return folded
        candidates, parameter_guidance = folded
        guidance.extend(parameter_guidance)

        presence = [c for c in candidates if c.fold == _PRESENCE]
        if presence and key not in effective:
            return ConstraintRefusal(
                reason="required-absent",
                key=key,
                detail=(
                    f"{key}: an applicable constraint requires this parameter"
                    " and the request neither supplies it nor does the class"
                    " declare a default for it, so there is no value to govern"
                ),
                bound=presence[0].bound,
                requested=None,
            )
        if key not in effective:
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
            return refusal
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
            return ConstraintRefusal(
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
            )
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
        return verdict

    resolved = EffectiveRequest(
        parameters=tuple(effective[name] for name in sorted(effective)),
        guidance=tuple(sorted(guidance, key=_guidance_key)),
        overrides=verified_overrides,
        applied=tuple(sorted(applied, key=_sort_key)),
        asked_at=request.asked_at,
    )
    # D-IMPL-254: the Authority layer's value is the record, never a scalar
    return resolved
