"""The four worked cases as SDK tests, and the three defect classes they rule out.

Ledger row ``24.6-L-07``; ``D-IMPL-253`` Q4/Q5/Q7/Q21 and ``D-IMPL-254``. The
subject is :func:`ccf.products.constraints.resolve_effective_request`.

**The four cases are Dave's, quoted from** ``24.6-RULINGS.md`` **§1**::

    Product default debt tolerance: .25   Caller: .30   Policy: none
    → effective caller tolerance .30
    Product default:                .25   Caller: omitted   Policy: none
    → effective tolerance .25
    Product default:                .25   Caller: .30   Policy maximum: .20
    → policy boundary .20
    Product default depth:            6   Caller: 8   Technical maximum: 100
    → depth 8 is valid

They are *illustration*, never calibration. Every number below is this module's
own fixture vocabulary; ``src/`` holds no tolerance, no depth and no ceiling
(CLAUDE.md §6.4, CINV-01).

What is proven here, and by which test
--------------------------------------

* **Each of the four cases resolves to the ruled ``(value, authority)``**, and
  each carries a **flip control**: the same assertion with the authority
  changed, watched failing under ``pytest.raises(AssertionError)``. A case test
  with no control proves only that today's answer is today's answer.
* **Comparability governs conflicts** (``D-IMPL-253`` Q4). Two ceilings fold to
  the smaller, two floors to the larger, two admitted sets to their
  intersection. A ceiling below a floor and an empty intersection are
  :class:`~ccf.products.constraints.PolicyResolutionConflict`, naming every
  side. A ceiling beside an admitted set is **not** one comparison: both apply
  and priority only orders which is *reported*.
* **Three sabotages, each on a scratch COPY of** ``constraints.py`` under
  ``tmp_path`` — never the tree — with ``source.count(needle)`` asserted before
  every mutation and the real module's bytes asserted unchanged afterward:
  priority erasing a hard constraint (Q4), ``preferred`` refusing (Q5), and the
  resolution collapsing to a bare mapping (``D-IMPL-254``, the ``min()`` defect
  in new clothes). Each is GREEN on the tree and RED on the copy.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    CONSTRAINT_OPERATORS,
    ConstraintApplicability,
    PolicyConstraint,
)
from ccf.products import constraints as constraints_module
from ccf.contracts.canonical import canonical_bytes
from ccf.products.constraints import (
    CAPABILITY_TRAVERSAL_DEPTH,
    ConstraintRefusal,
    PinnedConstraint,
    PolicyResolutionConflict,
    ResolutionOutcome,
    TechnicalCapability,
    applicable,
)
from ccf.products.provenance import (
    EffectiveRequest,
    OverrideRecord,
    ProvenanceSource,
)
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
)
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

CONSTRAINTS_PATH = pathlib.Path(constraints_module.__file__)
CONSTRAINTS_SOURCE = CONSTRAINTS_PATH.read_bytes()

INSTANT = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
WINDOW_OPENS = INSTANT - timedelta(days=30)

CLASS_NAME = "fixture.product"
CLASS_VERSION = "1.0.0"
TENANT = "fixture-tenant"
ROLE = "fixture-role"
INTENT = "fixture-intent"

TOLERANCE = "debt_tolerance"
DEPTH = "depth"
TIER = "tier"

#: The request contract's own pin — an artifact source, so it carries a lane.
DECLARED_SOURCE = ProvenanceSource(
    kind="artifact", identity="contract-key", version="v"
)

#: The backend limit of case 4. Its provenance is a capability identity and
#: never an artifact pin (``D-IMPL-253`` amendment 2 (1)).
CAPABILITY = TechnicalCapability(
    capability=CAPABILITY_TRAVERSAL_DEPTH,
    maximum=Decimal(100),
    identity="fixture-store",
)

PERSPECTIVE = Perspective(principal_id="fixture-principal", role=ROLE)


# --- fixtures ----------------------------------------------------------------


def _contract(**overrides: Any) -> ProductRequestContract:
    """A class declaring a tolerance, a depth and a tier, with two defaults."""
    fields: dict[str, Any] = {
        "semver": "1.0.0",
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "arguments": SkillArgumentSchema(
            properties={
                TOLERANCE: SkillArgumentProperty(
                    type="number", description="a fixture tolerance"
                ),
                DEPTH: SkillArgumentProperty(
                    type="integer", description="a fixture depth"
                ),
                TIER: SkillArgumentProperty(
                    type="string", description="a fixture tier name"
                ),
            },
            required=(),
        ),
        "defaults": {TOLERANCE: Decimal(".25"), DEPTH: 6},
    }
    fields.update(overrides)
    return ProductRequestContract(**fields)


CONTRACT = _contract()


def _request(**parameters: Any) -> ProductRequest:
    return ProductRequest(
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        subject="fixture:subject/one",
        intent=INTENT,
        freshness="fixture-freshness",
        asked_at=INSTANT,
        parameters=parameters,
    )


def _pinned(
    *,
    parameter: str,
    operator: str,
    value: Any,
    key: str = "constraint-key",
    version: str = "1.0.0",
    policy_id: str = "fixture-policy",
    priority: int = 0,
    overridable: bool = False,
    applies_to: ConstraintApplicability | None = None,
    effective_from: datetime = WINDOW_OPENS,
    effective_until: datetime | None = None,
) -> PinnedConstraint:
    """One policy constraint with the pin it was resolved by."""
    return PinnedConstraint(
        key=key,
        version=version,
        constraint=PolicyConstraint(
            semver="1.0.0",
            policy_id=policy_id,
            applies_to=applies_to or ConstraintApplicability(),
            parameter=parameter,
            operator=operator,
            value=value,
            overridable=overridable,
            source_authority="fixture-authority",
            effective_from=effective_from,
            effective_until=effective_until,
            reason="a fixture reason",
            priority=priority,
        ),
    )


def _resolve(
    request: ProductRequest,
    *,
    constraints: tuple[PinnedConstraint, ...] = (),
    overrides: tuple[OverrideRecord, ...] = (),
    module: types.ModuleType | None = None,
    capability_bindings: dict[str, str] | None = None,
    capabilities: tuple[TechnicalCapability, ...] | None = None,
) -> Any:
    """Resolve through the real module, or through a scratch copy of it.

    ``module`` is the seam the three sabotage controls use: the copy's own
    ``resolve_effective_request`` is called with the very same arguments the
    shipped assertions use, so a control proves something about the algorithm
    rather than about a second copy of the call.
    """
    target = module or constraints_module
    return target.resolve_effective_request(
        request=request,
        declared=CONTRACT,
        declared_source=DECLARED_SOURCE,
        constraints=constraints,
        capabilities=(CAPABILITY,) if capabilities is None else capabilities,
        capability_bindings=(
            {DEPTH: CAPABILITY_TRAVERSAL_DEPTH}
            if capability_bindings is None
            else capability_bindings
        ),
        verified_overrides=overrides,
        perspective=PERSPECTIVE,
        tenant=TENANT,
        served_at=request.asked_at,
    )


def _scratch_constraints(
    tmp_path: pathlib.Path, *, name: str, needle: str, replacement: str
) -> types.ModuleType:
    """A copy of ``constraints.py`` with one fragment rewritten, loaded by name.

    The count is asserted **before** the mutation, so a needle that has drifted
    fails loudly here instead of producing a copy identical to the original —
    which would make the control green for the wrong reason, and a green
    control is worse than none.
    """
    source = CONSTRAINTS_SOURCE.decode("utf-8")
    assert source.count(needle) == 1, f"the needle must appear exactly once: {needle!r}"
    mutated = source.replace(needle, replacement, 1)
    assert mutated != source
    path = tmp_path / f"{name}.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution and removed after: the module declares a
    # ``@dataclass`` whose annotations are strings (``from __future__ import
    # annotations``), and :mod:`dataclasses` resolves those through
    # ``sys.modules[cls.__module__]``. Without the entry the copy fails to
    # import at all, which would make the control fail for a reason that has
    # nothing to do with the sabotage. The name is unique per control and is
    # not under ``ccf.``, so nothing that walks the SDK's own packages sees it.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


# --- (a) the four worked cases, each with a flip control ----------------------


def test_case_1_caller_value_over_default() -> None:
    """``.25`` declared, ``.30`` asked, no policy → ``(.30, caller)``.

    A default is what omission means, not a competitor to a value the caller
    actually stated.
    """
    resolved = _resolve(_request(**{TOLERANCE: Decimal(".30")}))

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(TOLERANCE)
    assert parameter is not None
    assert parameter.value == Decimal(".30")
    assert parameter.authority == "caller"
    assert parameter.source.kind == "request"
    assert parameter.source.version is None

    # Control: the same record read as a default is FALSE, and watched failing.
    with pytest.raises(AssertionError):
        assert parameter.authority == "default"


def test_case_2_omission_takes_the_default() -> None:
    """``.25`` declared, omitted, no policy → ``(.25, default)`` at the pin.

    The source is the request contract's own artifact pin, which is why a
    default lives on the contract rather than in code: omission has to mean
    something a deployment declared and an examiner can resolve.
    """
    resolved = _resolve(_request())

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(TOLERANCE)
    assert parameter is not None
    assert parameter.value == Decimal(".25")
    assert parameter.authority == "default"
    assert parameter.source == DECLARED_SOURCE

    with pytest.raises(AssertionError):
        assert parameter.authority == "caller"


def test_case_3_policy_maximum_bounds_the_caller() -> None:
    """``.25`` declared, ``.30`` asked, policy maximum ``.20`` → ``(.20, policy)``.

    The caller's ``.30`` is **not** among the effective values — it survives on
    the request identity, which this function never rewrites — and the bound
    names the policy that set it.
    """
    pinned = _pinned(
        parameter=TOLERANCE,
        operator="maximum",
        value=Decimal(".20"),
        key="tolerance-ceiling",
        version="3.0.0",
    )
    resolved = _resolve(
        _request(**{TOLERANCE: Decimal(".30")}), constraints=(pinned,)
    )

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(TOLERANCE)
    assert parameter is not None
    assert parameter.value == Decimal(".20")
    assert parameter.authority == "policy"
    assert parameter.bound is not None
    assert parameter.bound.policy_id == "fixture-policy"
    assert parameter.bound.authority == "policy"
    # `D-IMPL-260` P-G: the constraint's declared reason rides on the bound it
    # established, so the resolution's provenance says why the bound was there.
    assert parameter.bound.reason == "a fixture reason"
    assert Decimal(".30") not in set(resolved.values().values())
    assert (
        ProvenanceSource(
            kind="artifact", identity="tolerance-ceiling", version="3.0.0"
        )
        in resolved.applied
    )

    with pytest.raises(AssertionError):
        assert parameter.authority == "caller"


def test_case_4_depth_within_the_technical_limit_is_valid() -> None:
    """``6`` declared, ``8`` asked, technical maximum ``100`` → ``(8, caller)``.

    Two authorities at once: the value is the caller's and the bound that
    admitted it is the backend's. The bound's source is a **capability
    identity** with no version lane — amendment 2 (1)'s *"do not create fake
    artifacts"* made structural.
    """
    resolved = _resolve(_request(**{DEPTH: 8}))

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(DEPTH)
    assert parameter is not None
    assert parameter.value == 8
    assert parameter.authority == "caller"
    assert parameter.bound is not None
    assert parameter.bound.authority == "technical"
    assert parameter.bound.source.kind == "capability"
    assert parameter.bound.source.identity == "fixture-store"
    assert parameter.bound.source.version is None
    assert parameter.bound.policy_id is None
    # A technical bound is read off a substrate and declares no reason.
    assert parameter.bound.reason is None

    with pytest.raises(AssertionError):
        assert parameter.bound.authority == "policy"


_ATTEMPTED = (
    OverrideRecord(
        policy_id="fixture-policy",
        policy_version="1.0.0",
        principal_id="fixture-principal",
        entitled=False,
        honored=False,
    ),
)


def test_a_refused_request_keeps_the_override_it_attempted() -> None:
    """``D-IMPL-260`` P-I (criterion 10): the attempt survives the refusal.

    Dave: *"the refusal path must preserve the attempted override and the
    entitlement result in replay."* The verified records are handed to the
    resolution before any bound is held against a value, so every refusal it
    can return was reached with them in hand. Three of the four refusal exits
    measured — the technical ceiling, a policy ceiling, and a resolution
    conflict — each carrying exactly the attempts it was handed, unentitled
    and unhonored as they were verified. The fourth exit (validation over the
    effective values) is the same one-line carriage and is measured through
    the envelope in ``test_refusal_envelope.py``.

    What would fail here: a refusal constructed at any exit without the
    attempts, which is the shape the close review measured — an examiner
    replaying a refused request could not see that an override was asked for
    or that it was refused as unentitled.
    """
    technical = _resolve(_request(**{DEPTH: 101}), overrides=_ATTEMPTED)
    assert isinstance(technical.refusal, ConstraintRefusal), technical
    technical = technical.refusal
    assert technical.overrides == _ATTEMPTED

    policy = _resolve(
        _request(**{DEPTH: 10}),
        constraints=(_pinned(parameter=DEPTH, operator="maximum", value=Decimal(5)),),
        overrides=_ATTEMPTED,
    )
    assert isinstance(policy.refusal, ConstraintRefusal), policy
    policy = policy.refusal
    assert policy.reason == "bound-exceeded" and policy.bound.authority == "policy"
    assert policy.overrides == _ATTEMPTED

    conflict = _resolve(
        _request(**{DEPTH: 4}),
        constraints=(
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(3), key="c"),
            _pinned(parameter=DEPTH, operator="minimum", value=Decimal(9), key="f"),
        ),
        overrides=_ATTEMPTED,
    )
    assert isinstance(conflict.refusal, PolicyResolutionConflict), conflict
    conflict = conflict.refusal
    assert conflict.overrides == _ATTEMPTED

    # And nothing attempted is the empty tuple — hash-transparent, so a
    # refusal written before the member existed renders as it did.
    bare = _resolve(_request(**{DEPTH: 101}))
    assert isinstance(bare.refusal, ConstraintRefusal), bare
    bare = bare.refusal
    assert bare.overrides == ()
    assert b"overrides" not in canonical_bytes(bare)


def test_a_depth_over_the_technical_limit_is_refused_by_name() -> None:
    """``101`` over a technical maximum of ``100`` is refused, not narrowed.

    The graph seam has no refusal path of its own — an over-ceiling depth there
    makes the translation decline and the fallback answer. Refusing by name is
    this layer's job, because only here is there a governed response to put the
    refusal in (``D-IMPL-253`` Q21).
    """
    refused = _resolve(_request(**{DEPTH: 101}))

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.reason == "bound-exceeded"
    assert refused.key == DEPTH
    assert refused.requested == 101
    assert refused.bound.authority == "technical"
    assert refused.bound.value == Decimal(100)
    assert refused.bound.source.identity == "fixture-store"
    assert refused.bound.reason is None


def test_the_technical_bound_never_clamps_the_request() -> None:
    """T-24.6-08: case 4 resolves to 8, and never to the declared 6 or the limit."""
    resolved = _resolve(_request(**{DEPTH: 8}))

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    assert resolved.values()[DEPTH] == 8
    assert resolved.values()[DEPTH] != 6
    assert resolved.values()[DEPTH] != Decimal(100)


# --- (b) comparability --------------------------------------------------------


def test_two_ceilings_fold_to_the_smaller() -> None:
    """Within one family the more restrictive statement implies the other."""
    resolved = _resolve(
        _request(**{DEPTH: 4}),
        constraints=(
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(20), key="a"),
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(5), key="b"),
        ),
    )

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(DEPTH)
    assert parameter is not None
    assert parameter.bound is not None
    assert parameter.bound.value == Decimal(5)


def test_a_value_over_the_smaller_of_two_ceilings_is_refused() -> None:
    """The fold is not a widening: 10 clears the 20 and misses the 5."""
    refused = _resolve(
        _request(**{DEPTH: 10}),
        constraints=(
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(20), key="a"),
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(5), key="b"),
        ),
    )

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.reason == "bound-exceeded"
    assert refused.bound.value == Decimal(5)


def test_two_floors_fold_to_the_larger() -> None:
    """The mirror of the ceiling fold, on the other end of the axis."""
    refused = _resolve(
        _request(**{DEPTH: 6}),
        constraints=(
            _pinned(parameter=DEPTH, operator="minimum", value=Decimal(2), key="a"),
            _pinned(parameter=DEPTH, operator="minimum", value=Decimal(8), key="b"),
        ),
    )

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.reason == "bound-exceeded"
    assert refused.bound.value == Decimal(8)
    assert refused.bound.operator == "minimum"


def test_two_allowed_sets_fold_to_their_intersection() -> None:
    """Set restrictiveness is intersection, and the folded bound carries it."""
    resolved = _resolve(
        _request(**{TIER: "silver"}),
        constraints=(
            _pinned(
                parameter=TIER,
                operator="allowed_set",
                value=("gold", "silver"),
                key="a",
            ),
            _pinned(
                parameter=TIER,
                operator="allowed_set",
                value=("silver", "bronze"),
                key="b",
            ),
        ),
    )

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(TIER)
    assert parameter is not None
    assert parameter.bound is not None
    assert parameter.bound.value == ("silver",)


def test_a_value_outside_the_intersection_is_not_in_allowed_set() -> None:
    """``gold`` is in one declared set and not in the folded one."""
    refused = _resolve(
        _request(**{TIER: "gold"}),
        constraints=(
            _pinned(
                parameter=TIER,
                operator="allowed_set",
                value=("gold", "silver"),
                key="a",
            ),
            _pinned(
                parameter=TIER,
                operator="allowed_set",
                value=("silver", "bronze"),
                key="b",
            ),
        ),
    )

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.reason == "not-in-allowed-set"
    assert refused.key == TIER
    assert refused.requested == "gold"


def test_a_ceiling_below_a_floor_is_a_policy_resolution_conflict() -> None:
    """Comparable and irreconcilable: neither is dropped, both are named."""
    conflict = _resolve(
        _request(**{DEPTH: 6}),
        constraints=(
            _pinned(
                parameter=DEPTH,
                operator="maximum",
                value=Decimal(3),
                key="ceiling-key",
                version="1.0.0",
            ),
            _pinned(
                parameter=DEPTH,
                operator="minimum",
                value=Decimal(9),
                key="floor-key",
                version="2.0.0",
            ),
        ),
    )

    assert isinstance(conflict.refusal, PolicyResolutionConflict), conflict

    conflict = conflict.refusal
    assert conflict.reason == "policy-resolution-conflict"
    assert conflict.key == DEPTH
    assert conflict.conflicting == (
        ProvenanceSource(kind="artifact", identity="ceiling-key", version="1.0.0"),
        ProvenanceSource(kind="artifact", identity="floor-key", version="2.0.0"),
    )


def test_an_empty_intersection_is_a_policy_resolution_conflict() -> None:
    """Two admitted sets sharing no member admit nothing, and say so by pin."""
    conflict = _resolve(
        _request(**{TIER: "gold"}),
        constraints=(
            _pinned(
                parameter=TIER,
                operator="allowed_set",
                value=("gold",),
                key="gold-key",
                version="1.0.0",
            ),
            _pinned(
                parameter=TIER,
                operator="allowed_set",
                value=("bronze",),
                key="bronze-key",
                version="2.0.0",
            ),
        ),
    )

    assert isinstance(conflict.refusal, PolicyResolutionConflict), conflict

    conflict = conflict.refusal
    assert conflict.key == TIER
    assert conflict.conflicting == (
        ProvenanceSource(kind="artifact", identity="bronze-key", version="2.0.0"),
        ProvenanceSource(kind="artifact", identity="gold-key", version="1.0.0"),
    )


def _non_comparable_pair() -> tuple[PinnedConstraint, ...]:
    """A ceiling at priority 10 beside a floor at priority 1, on one parameter.

    The two do not fold into each other — they are separate candidates — so
    both are held against the value, and priority decides only which one the
    served record *reports*. This is the pair the priority sabotage below runs
    against.
    """
    return (
        _pinned(
            parameter=DEPTH,
            operator="maximum",
            value=Decimal(50),
            key="ranking-ceiling",
            priority=10,
        ),
        _pinned(
            parameter=DEPTH,
            operator="minimum",
            value=Decimal(4),
            key="outranked-floor",
            priority=1,
        ),
    )


def test_priority_orders_the_reported_bound_and_nothing_else() -> None:
    """8 clears both; the reported bound is the higher-priority ceiling."""
    resolved = _resolve(_request(**{DEPTH: 8}), constraints=_non_comparable_pair())

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(DEPTH)
    assert parameter is not None
    assert parameter.bound is not None
    assert parameter.bound.operator == "maximum"
    assert parameter.bound.value == Decimal(50)
    # Both pins are in `applied` — the outranked one applied, it just was not
    # the bound reported.
    assert {source.identity for source in resolved.applied} >= {
        "ranking-ceiling",
        "outranked-floor",
    }


def test_a_value_violating_the_lower_priority_bound_is_refused() -> None:
    """2 clears the ceiling that outranks and misses the floor that does not."""
    refused = _resolve(_request(**{DEPTH: 2}), constraints=_non_comparable_pair())

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.reason == "bound-exceeded"
    assert refused.bound.operator == "minimum"
    assert refused.bound.value == Decimal(4)


def test_a_ceiling_beside_an_allowed_set_both_apply() -> None:
    """Two families that share no axis are two candidates, not one comparison."""
    refused = _resolve(
        _request(**{TIER: "bronze"}),
        constraints=(
            _pinned(
                parameter=TIER,
                operator="maximum",
                value=Decimal(10),
                key="tier-ceiling",
                priority=10,
            ),
            _pinned(
                parameter=TIER,
                operator="allowed_set",
                value=("gold", "silver"),
                key="tier-set",
                priority=1,
            ),
        ),
    )

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.reason == "not-in-allowed-set"
    assert refused.bound.operator == "allowed_set"


def test_the_fold_table_covers_the_whole_constraint_vocabulary() -> None:
    """A sixth operator is a red build here, not a constraint silently ignored."""
    assert set(constraints_module._FOLDS) == CONSTRAINT_OPERATORS


# --- (c) required, overrides, applicability -----------------------------------


def test_a_required_parameter_absent_after_defaults_is_refused() -> None:
    """``required`` constrains presence, and the class declares no ``tier``."""
    refused = _resolve(
        _request(),
        constraints=(_pinned(parameter=TIER, operator="required", value=None),),
    )

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.reason == "required-absent"
    assert refused.key == TIER
    assert refused.requested is None
    assert refused.bound.operator == "required"


def test_a_required_parameter_a_default_supplies_is_not_refused() -> None:
    """A declared default satisfies presence — omission means the default."""
    resolved = _resolve(
        _request(),
        constraints=(_pinned(parameter=DEPTH, operator="required", value=None),),
    )

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    parameter = resolved.parameter(DEPTH)
    assert parameter is not None
    assert parameter.authority == "default"


def test_a_verified_entitled_override_is_honored() -> None:
    """Q7: an overridable constraint yields to a VERIFIED entitled override."""
    resolved = _resolve(
        _request(**{DEPTH: 60}),
        constraints=(
            _pinned(
                parameter=DEPTH,
                operator="maximum",
                value=Decimal(50),
                overridable=True,
            ),
        ),
        overrides=(
            OverrideRecord(
                policy_id="fixture-policy",
                policy_version="1.0.0",
                principal_id="fixture-principal",
                entitled=True,
                honored=True,
            ),
        ),
    )

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    assert resolved.values()[DEPTH] == 60
    assert resolved.overrides[0].entitled is True


def test_an_unentitled_override_changes_nothing_and_is_still_recorded() -> None:
    """*"Naming the policy is not sufficient authority to override it."*

    The attempt is a thing that happened and is recorded with
    ``entitled=False``; the constraint still refuses.
    """
    refused = _resolve(
        _request(**{DEPTH: 60}),
        constraints=(
            _pinned(
                parameter=DEPTH,
                operator="maximum",
                value=Decimal(50),
                overridable=True,
            ),
        ),
        overrides=(
            OverrideRecord(
                policy_id="fixture-policy",
                policy_version="1.0.0",
                principal_id="fixture-principal",
                entitled=False,
                honored=False,
            ),
        ),
    )

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.bound.value == Decimal(50)


def test_a_non_overridable_constraint_is_not_yielded_to() -> None:
    """``overridable=False`` is the safe default and an override does not move it."""
    refused = _resolve(
        _request(**{DEPTH: 60}),
        constraints=(
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(50)),
        ),
        overrides=(
            OverrideRecord(
                policy_id="fixture-policy",
                policy_version="1.0.0",
                principal_id="fixture-principal",
                entitled=True,
                honored=True,
            ),
        ),
    )

    assert isinstance(refused.refusal, ConstraintRefusal), refused

    refused = refused.refusal
    assert refused.bound.value == Decimal(50)


def test_an_inapplicable_constraint_passed_in_is_ignored() -> None:
    """T-24.6-06: applicability is re-checked inside the pure function.

    Two ways to be inapplicable — the wrong tenant, and a window that has not
    opened — and neither reaches the value. A caller cannot smuggle a
    constraint in by passing it directly.
    """
    wrong_tenant = _pinned(
        parameter=DEPTH,
        operator="maximum",
        value=Decimal(2),
        key="wrong-tenant",
        applies_to=ConstraintApplicability(tenant="another-tenant"),
    )
    not_yet_effective = _pinned(
        parameter=DEPTH,
        operator="maximum",
        value=Decimal(2),
        key="not-yet",
        effective_from=INSTANT + timedelta(days=1),
    )
    expired = _pinned(
        parameter=DEPTH,
        operator="maximum",
        value=Decimal(2),
        key="expired",
        effective_until=INSTANT - timedelta(days=1),
    )

    resolved = _resolve(
        _request(**{DEPTH: 8}),
        constraints=(wrong_tenant, not_yet_effective, expired),
    )

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    assert resolved.values()[DEPTH] == 8
    assert {source.identity for source in resolved.applied}.isdisjoint(
        {"wrong-tenant", "not-yet", "expired"}
    )


def test_the_effectivity_window_is_half_open_at_its_end() -> None:
    """A constraint ending at the asked instant does not apply at that instant."""
    constraint = _pinned(
        parameter=DEPTH,
        operator="maximum",
        value=Decimal(2),
        effective_until=INSTANT,
    ).constraint

    assert not applicable(
        constraint,
        product_class=CLASS_NAME,
        tenant=TENANT,
        perspective_role=ROLE,
        intent=INTENT,
        served_at=INSTANT,
    )
    assert applicable(
        constraint,
        product_class=CLASS_NAME,
        tenant=TENANT,
        perspective_role=ROLE,
        intent=INTENT,
        served_at=INSTANT - timedelta(seconds=1),
    )


def test_a_naive_asked_at_is_refused() -> None:
    """No implicit UTC, at both entry points.

    ``applicable`` is one; ``resolve_effective_request`` is the other, and it
    is checked separately because a request with **no** applicable constraints
    never reaches the first.
    """
    naive = INSTANT.replace(tzinfo=None)
    with pytest.raises(TypeError, match="timezone-aware"):
        applicable(
            _pinned(
                parameter=DEPTH, operator="maximum", value=Decimal(2)
            ).constraint,
            product_class=CLASS_NAME,
            tenant=TENANT,
            perspective_role=ROLE,
            intent=INTENT,
            served_at=naive,
        )

    request = _request(**{DEPTH: 8}).model_copy(update={"asked_at": naive})
    with pytest.raises(TypeError, match="timezone-aware"):
        _resolve(request)


def test_a_binding_naming_an_unsupplied_capability_raises() -> None:
    """A wiring failure raises; it is not answered as a governed determination."""
    with pytest.raises(LookupError, match="no-such-capability"):
        _resolve(
            _request(**{DEPTH: 8}),
            capability_bindings={DEPTH: "no-such-capability"},
        )


def test_provenance_is_recorded_even_when_nothing_constrained_the_request() -> None:
    """C-06: *"nothing applied"* is a claim, and it carries the same evidence.

    Every parameter still carries ``(value, authority, source)``, and
    ``applied`` still names the contract pin the resolution was performed
    against.
    """
    resolved = _resolve(_request())

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    for parameter in resolved.parameters:
        assert parameter.authority
        assert parameter.source.identity
    assert DECLARED_SOURCE in resolved.applied


# --- (d) `preferred` never refuses, and the sabotage that makes it -------------

PREFERRED_NEEDLE = '    "preferred": _GUIDANCE,\n'
PREFERRED_SABOTAGE = '    "preferred": _CEILING,\n'


def test_preferred_never_refuses() -> None:
    """Q5: guidance the request violates is recorded, and the request is served."""
    resolved = _resolve(
        _request(**{DEPTH: 8}),
        constraints=(
            _pinned(parameter=DEPTH, operator="preferred", value=Decimal(4)),
        ),
    )

    assert resolved.refusal is None, resolved.refusal

    resolved = resolved.evidence
    assert resolved.values()[DEPTH] == 8
    assert len(resolved.guidance) == 1
    assert resolved.guidance[0].operator == "preferred"
    assert resolved.guidance[0].value == Decimal(4)
    # Guidance is carried BESIDE the parameters, so a reader cannot mistake it
    # for a boundary that decided anything.
    parameter = resolved.parameter(DEPTH)
    assert parameter is not None
    assert parameter.bound is not None
    assert parameter.bound.operator != "preferred"


def test_preferred_refusing_is_red_sabotage(tmp_path: pathlib.Path) -> None:
    """C-04. Fold ``preferred`` as a ceiling on a copy and the request is refused.

    The predicate the shipped test makes — *this resolves* — fails on the copy,
    which is the whole content of *"preferred must remain non-refusing
    guidance"* being a property rather than a sentence.
    """
    scratch = _scratch_constraints(
        tmp_path,
        name="constraints_with_preferred_as_a_ceiling",
        needle=PREFERRED_NEEDLE,
        replacement=PREFERRED_SABOTAGE,
    )
    constraints = (
        _pinned(parameter=DEPTH, operator="preferred", value=Decimal(4)),
    )
    request = _request(**{DEPTH: 8})

    sabotaged = _resolve(request, constraints=constraints, module=scratch)

    assert type(sabotaged.refusal).__name__ == "ConstraintRefusal"
    with pytest.raises(AssertionError):
        assert sabotaged.refusal is None
    # And the real module serves the same request.
    assert _resolve(request, constraints=constraints).refusal is None


# --- (e) priority never erases a hard constraint ------------------------------

PRIORITY_MARKER = "    # D-04: every applied constraint holds\n"
PRIORITY_NEEDLE = PRIORITY_MARKER + "        checked = ordered\n"
PRIORITY_SABOTAGE = PRIORITY_MARKER + "        checked = ordered[:1]\n"


def test_priority_never_erases_a_hard_constraint_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """C-08. Keep only the highest-priority bound on a copy and the value is SERVED.

    ``D-IMPL-253`` Q4: *"Never use priority to make an applicable hard
    constraint disappear."* The copy checks ``ordered[:1]`` — the ceiling that
    outranks — so a depth of 2 that misses the outranked floor sails through.
    """
    source = CONSTRAINTS_SOURCE.decode("utf-8")
    assert source.count(PRIORITY_MARKER) == 1

    scratch = _scratch_constraints(
        tmp_path,
        name="constraints_with_priority_erasing",
        needle=PRIORITY_NEEDLE,
        replacement=PRIORITY_SABOTAGE,
    )
    request = _request(**{DEPTH: 2})
    constraints = _non_comparable_pair()

    sabotaged = _resolve(request, constraints=constraints, module=scratch)

    assert sabotaged.refusal is None
    with pytest.raises(AssertionError):
        assert type(sabotaged.refusal).__name__ == "ConstraintRefusal"
    # And the real module refuses it, naming the outranked floor.
    refused = _resolve(request, constraints=constraints)
    assert isinstance(refused.refusal, ConstraintRefusal), refused
    refused = refused.refusal
    assert refused.bound.operator == "minimum"


# --- (f) the resolution is a record, never a scalar ---------------------------

COLLAPSE_NEEDLE = "    return resolved\n"
COLLAPSE_SABOTAGE = (
    "    return resolved.evidence.values()  # type: ignore[return-value]\n"
)


def _assert_provenance_survives(resolved: Any) -> None:
    """The predicate under control: ask the resolution which authority set a value.

    The ``AttributeError`` a collapsed resolution raises is caught and re-raised
    as a named assertion, because an uncaught one reads as a broken test rather
    than as a watched control — and the whole point of the control is that the
    failure is legible.
    """
    try:
        authority = resolved.parameter(TOLERANCE).authority
    except AttributeError as error:
        raise AssertionError(
            "the resolution cannot be asked which authority set a value —"
            f" provenance did not survive the return ({error})"
        ) from error
    assert authority == "caller"


def test_provenance_is_never_a_scalar_sabotage(tmp_path: pathlib.Path) -> None:
    """C-06, ``D-IMPL-254``. Return the mapping view and the provenance is gone.

    *"Any post-resolution scalar is that same defect in new clothes."* The copy
    returns exactly what an engine wants — name to value — and every fact about
    *why* a value is that value is gone with it. The predicate above is watched
    failing on the copy and passing on the tree, which is the difference
    between a collapsed form being discouraged and being unrepresentable.
    """
    scratch = _scratch_constraints(
        tmp_path,
        name="constraints_collapsing_to_values",
        needle=COLLAPSE_NEEDLE,
        replacement=COLLAPSE_SABOTAGE,
    )
    request = _request(**{TOLERANCE: Decimal(".30")})

    collapsed = _resolve(request, module=scratch)

    # The copy answers the engine's question perfectly well. That is what makes
    # this defect class survive review: nothing about the returned value looks
    # wrong until an examiner asks the one question it can no longer answer.
    assert collapsed == {TOLERANCE: Decimal(".30"), DEPTH: 6}
    with pytest.raises(AssertionError, match="provenance did not survive"):
        _assert_provenance_survives(collapsed)

    # And the real module answers it.
    resolved = _resolve(request)
    assert resolved.refusal is None, resolved.refusal
    resolved = resolved.evidence
    _assert_provenance_survives(resolved)


# --- (g) the controls edited nothing ------------------------------------------


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """Every control above mutates a copy under ``tmp_path``.

    ``constraints.py`` on disk is byte-identical to what this module read at
    import, and all three needles are still present — a needle that drifted
    would make its control green for the wrong reason.
    """
    assert CONSTRAINTS_PATH.read_bytes() == CONSTRAINTS_SOURCE
    source = CONSTRAINTS_SOURCE.decode("utf-8")
    assert source.count(PREFERRED_NEEDLE) == 1
    assert source.count(PRIORITY_NEEDLE) == 1
    assert source.count(COLLAPSE_NEEDLE) == 1
    assert "never dropped because another outranks it" in source


# --- (h) the paired outcome: every exit carries what resolution established ----
#
# `D-IMPL-264` D-08 (Dave, `24.7-RULINGS.md` §3 Q8): *"a common resolution
# outcome shape: completed request or governed refusal, both with the
# resolution evidence accumulated so far."* One test per exit of
# `resolve_effective_request`, in the order the exits occur in the function;
# what each asserts is the evidence RESEARCH § Measurement 8 measured to be in
# scope at that exit. Criterion 12.

#: The three refusal classes' field rosters as measured at the phase base
#: (`9a2e4bcf`) by `sorted(C.model_fields)`. Criterion 12: the paired outcome
#: adds the evidence BESIDE the refusal, never as a field cloned into it — so
#: these rosters must not grow. Spelled as the fixture's own constants rather
#: than read off the classes, because a roster read off the thing it guards
#: guards nothing.
CONSTRAINT_REFUSAL_FIELDS = frozenset(
    {"bound", "detail", "key", "overrides", "reason", "requested"}
)
POLICY_RESOLUTION_CONFLICT_FIELDS = frozenset(
    {"conflicting", "detail", "key", "overrides", "reason"}
)
PRODUCT_REQUEST_VIOLATION_FIELDS = frozenset(
    {
        "declared_keys",
        "declared_type",
        "detail",
        "key",
        "overrides",
        "presented_keys",
        "presented_type",
        "reason",
    }
)

#: The fixture capability's provenance, as the resolution records it — a
#: capability identity and never an artifact pin.
CAPABILITY_SOURCE = ProvenanceSource(
    kind="capability", identity=CAPABILITY.identity, version=None
)


def _constraint_source(key: str, version: str = "1.0.0") -> ProvenanceSource:
    """The pin a `_pinned` constraint is recorded under in `applied`."""
    return ProvenanceSource(kind="artifact", identity=key, version=version)


def test_the_conflict_exit_carries_the_evidence_accumulated_so_far() -> None:
    """Exit 1: the fold found a contradiction — and both defaults, the caller's
    value, every consulted pin and the override attempts are on the evidence."""
    outcome = _resolve(
        _request(**{DEPTH: 4}),
        constraints=(
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(3), key="c"),
            _pinned(parameter=DEPTH, operator="minimum", value=Decimal(9), key="f"),
        ),
        overrides=_ATTEMPTED,
    )

    assert isinstance(outcome, ResolutionOutcome)
    assert isinstance(outcome.refusal, PolicyResolutionConflict), outcome
    assert outcome.completed is False
    evidence = outcome.evidence
    assert isinstance(evidence, EffectiveRequest)
    assert evidence.values() == {TOLERANCE: Decimal(".25"), DEPTH: 4}
    depth = evidence.parameter(DEPTH)
    assert depth is not None and depth.authority == "caller"
    tolerance = evidence.parameter(TOLERANCE)
    assert tolerance is not None and tolerance.authority == "default"
    assert DECLARED_SOURCE in evidence.applied
    assert _constraint_source("c") in evidence.applied
    assert _constraint_source("f") in evidence.applied
    assert evidence.overrides == _ATTEMPTED
    assert evidence.asked_at == INSTANT


def test_the_required_absent_exit_carries_the_evidence_accumulated_so_far() -> None:
    """Exit 2: presence refused — the defaults resolved before it are on the
    evidence, the requiring constraint's pin is in `applied`, and the absent
    key has no record (the positive statement *nothing was presented*)."""
    outcome = _resolve(
        _request(),
        constraints=(
            _pinned(parameter=TIER, operator="required", value=None, key="presence"),
        ),
    )

    assert isinstance(outcome.refusal, ConstraintRefusal), outcome
    assert outcome.refusal.reason == "required-absent"
    evidence = outcome.evidence
    assert evidence.values() == {TOLERANCE: Decimal(".25"), DEPTH: 6}
    assert evidence.parameter(TIER) is None
    assert DECLARED_SOURCE in evidence.applied
    assert _constraint_source("presence") in evidence.applied


def test_the_bound_refusal_exit_carries_the_bounds_attached_to_earlier_keys() -> None:
    """Exit 3: a policy ceiling refused the depth — and the tolerance ceiling
    that folded FIRST (worked case 3, the one clamp) is on the evidence with
    authority `policy` and its bound attached, exactly as it was resolved."""
    outcome = _resolve(
        _request(**{TOLERANCE: Decimal(".30"), DEPTH: 10}),
        constraints=(
            _pinned(parameter=TOLERANCE, operator="maximum", value=Decimal(".20"), key="t"),
            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(5), key="d"),
        ),
    )

    refusal = outcome.refusal
    assert isinstance(refusal, ConstraintRefusal), outcome
    assert refusal.key == DEPTH and refusal.bound.authority == "policy"
    tolerance = outcome.evidence.parameter(TOLERANCE)
    assert tolerance is not None
    assert tolerance.authority == "policy" and tolerance.value == Decimal(".20")
    assert tolerance.bound is not None
    assert tolerance.bound.source == _constraint_source("t")
    # The refused value is still the caller's on the evidence: nothing clamped.
    depth = outcome.evidence.parameter(DEPTH)
    assert depth is not None and depth.value == 10 and depth.authority == "caller"
    assert _constraint_source("t") in outcome.evidence.applied
    assert _constraint_source("d") in outcome.evidence.applied


def test_the_capability_exit_carries_the_technical_bounds_attached_so_far() -> None:
    """Exit 4: the technical ceiling refused the depth — and the technical bound
    already attached to the parameter bound before it is on the evidence, with
    the capability's own provenance in `applied`."""
    outcome = _resolve(
        _request(**{DEPTH: 101}),
        capability_bindings={
            TOLERANCE: CAPABILITY_TRAVERSAL_DEPTH,
            DEPTH: CAPABILITY_TRAVERSAL_DEPTH,
        },
    )

    refusal = outcome.refusal
    assert isinstance(refusal, ConstraintRefusal), outcome
    assert refusal.key == DEPTH and refusal.bound.authority == "technical"
    tolerance = outcome.evidence.parameter(TOLERANCE)
    assert tolerance is not None and tolerance.bound is not None
    assert tolerance.bound.authority == "technical"
    assert tolerance.bound.source == CAPABILITY_SOURCE
    assert CAPABILITY_SOURCE in outcome.evidence.applied
    assert DECLARED_SOURCE in outcome.evidence.applied


def test_the_validation_exit_carries_the_full_effective_set_and_the_overrides() -> None:
    """Exit 5: conformity refused an effective value — the WHOLE effective set
    was resolved (defaults, caller, capability consulted) and rides with the
    refusal, as do the override attempts, on both halves."""
    outcome = _resolve(_request(**{"undeclared": 1}), overrides=_ATTEMPTED)

    refusal = outcome.refusal
    assert isinstance(refusal, ProductRequestViolation), outcome
    assert refusal.reason == "undeclared-parameter"
    assert refusal.overrides == _ATTEMPTED
    evidence = outcome.evidence
    assert evidence.values() == {TOLERANCE: Decimal(".25"), DEPTH: 6, "undeclared": 1}
    assert evidence.overrides == _ATTEMPTED
    assert CAPABILITY_SOURCE in evidence.applied
    assert DECLARED_SOURCE in evidence.applied


def test_the_completion_exit_evidence_is_the_effective_request_as_before() -> None:
    """Exit 6: completed — `refusal` is stated `None`, and `evidence` is exactly
    the `EffectiveRequest` the function returned bare before D-08."""
    outcome = _resolve(_request(**{TOLERANCE: Decimal(".30")}))

    assert outcome.refusal is None
    assert outcome.completed is True
    assert isinstance(outcome.evidence, EffectiveRequest)
    assert outcome.evidence.values() == {TOLERANCE: Decimal(".30"), DEPTH: 6}
    assert outcome.evidence.applied == (DECLARED_SOURCE, CAPABILITY_SOURCE)
    assert outcome.evidence.overrides == ()
    assert outcome.evidence.guidance == ()


def test_the_three_refusal_classes_gained_no_resolution_field() -> None:
    """Criterion 12 — Q8's second sentence, measured against the phase-base
    rosters: *"rather than cloning resolution fields into multiple refusal
    classes."* The outcome has exactly its two members."""
    assert set(ConstraintRefusal.model_fields) == CONSTRAINT_REFUSAL_FIELDS
    assert set(PolicyResolutionConflict.model_fields) == POLICY_RESOLUTION_CONFLICT_FIELDS
    assert set(ProductRequestViolation.model_fields) == PRODUCT_REQUEST_VIOLATION_FIELDS
    assert set(ResolutionOutcome.model_fields) == {"evidence", "refusal"}


def test_the_outcome_requires_both_members_stated() -> None:
    """Neither member is defaulted (`D-IMPL-264` P-2: absence is stated, never
    inferred from omission). Omitting either is refused at construction."""
    evidence = _resolve(_request()).evidence

    with pytest.raises(ValueError, match="refusal"):
        ResolutionOutcome(evidence=evidence)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="evidence"):
        ResolutionOutcome(refusal=None)  # type: ignore[call-arg]
    assert ResolutionOutcome(evidence=evidence, refusal=None).completed is True
