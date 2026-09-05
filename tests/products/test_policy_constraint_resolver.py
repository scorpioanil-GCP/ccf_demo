"""Effectivity at ``asked_at``, the override that needs an entitlement, and the pin.

Ledger row ``24.6-L-07``; ``D-IMPL-253`` Q6 (*"asked_at, absolutely. Otherwise
replay of the same historical decision can resolve a different policy."*), Q7
(*"Naming the policy is necessary but not sufficient authority to override it
... Otherwise anyone who knows a policy ID could bypass it."*) and Q8. The
subject is :class:`ccf.products.constraints.ReferencePolicyConstraintResolver`
and the seam that calls it.

Plan ``24.6-02`` proved the resolution *algorithm* against already-resolved
artifacts, with no registry anywhere. This module proves the half that reads:
which constraint the Control Plane holds in force **at the request's own
instant**, at which exact version, and whether the principal asking to override
one is entitled to.

What is proven, and by which test:

* **The window decides, and the instant is the request's.** Two constraint keys
  bound to one parameter over adjacent half-open windows: a request inside the
  first resolves the first and never the second, and a request at the boundary
  instant resolves the second. The versions in ``applied`` are the registry's
  own content addresses, exact.
* **"Latest" is never reached.** The registry's ``resolve_latest`` is
  monkeypatched to raise for the whole resolution, so a reach for it is a
  failure rather than a difference nobody notices.
* **Two versions in force at once is a failure, not a determination**
  (``ConstraintEffectivityConflict``): the Control Plane contradicts itself and
  the fabric cannot say which boundary governs.
* **An override needs a name AND an entitlement.** The same request, by two
  principals, resolves two different ways — and the unentitled attempt is
  *recorded*, with both halves separate, rather than dropped.
* **The sabotage**: a scratch copy of ``constraints.py`` whose entitlement check
  is replaced by ``entitled=True`` honors the name-only override, and the
  shipped assertion goes RED against it. The tree is never edited.
* **The pin reaches replay.** Through the booted governed resolver: the
  constraint's ``(key, version)`` is a dimension-2 binding, ``request_resolution``
  round-trips to an ``EffectiveRequest`` whose tolerance carries authority
  ``policy``, and the caller's own parameters survive on the request identity.

Every key, name, number and instant below is this module's own fixture
vocabulary (CINV-01 reaches ``tests/``): ``src/`` holds no tolerance, no policy
id and no principal.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import types
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import (
    POLICY_CONSTRAINT,
    ConstraintApplicability,
    PolicyConstraint,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products import constraints as constraints_module
from ccf.products.constraints import (
    ConstraintEffectivityConflict,
    ReferencePolicyConstraintResolver,
    constraints_in_force,
)
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.provenance import EffectiveRequest, ProvenanceSource
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.projection.plan import Perspective
from ccf.replay.record import NO_REQUEST_RESOLUTION
from ccf.replay.serve import ServedProduct
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

from tests.deployment.conftest import ARTIFACT_SET, PRODUCT_CLASS_KEY, TENANT
from tests.products.test_resolver_seam import (
    ASKED_AT,
    CEILING_DECLARED,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    REQUEST_CONTRACT_DOCUMENT,
    THRESHOLD_PARAMETER,
    _Booted,
    _ask,
    _boot,
    _request,
    _resolver,
)

CONSTRAINTS_PATH = pathlib.Path(constraints_module.__file__)
CONSTRAINTS_SOURCE = CONSTRAINTS_PATH.read_bytes()

# --- this module's own vocabulary -------------------------------------------

#: The two adjacent windows. ``T1`` is the boundary instant: the first
#: constraint's window is ``[T0, T1)`` and the second's is ``[T1, ∞)``, so
#: exactly one is in force at every instant and the two never overlap.
T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 6, 1, tzinfo=UTC)
BEFORE_T1 = T1 - timedelta(days=1)

#: The two Control Plane keys and the policy id each artifact carries. The key
#: is where the artifact lives; the policy id is what a caller would name in an
#: override. They are deliberately different strings, so a test that confused
#: them would fail rather than pass by coincidence.
KEY_A = "policy_constraints.a"
KEY_B = "policy_constraints.b"
POLICY_A = "a"
POLICY_B = "b"

#: The two tolerances the two constraints bound to, and what a caller asks for.
#: Fixture proportions; no number here lives in ``src/``.
MAXIMUM_EARLY = Decimal("0.20")
MAXIMUM_LATE = Decimal("0.10")
CALLER_ASKS = Decimal("0.30")

ROLE = "role-fixture"
ENTITLED_PRINCIPAL = "principal-entitled"
UNENTITLED_PRINCIPAL = "principal-unentitled"
UNREGISTERED_POLICY = "policy-nobody-registered"

ENTITLED = Perspective(principal_id=ENTITLED_PRINCIPAL, role=ROLE)
UNENTITLED = Perspective(principal_id=UNENTITLED_PRINCIPAL, role=ROLE)

#: The request contract's own pin, as the governed resolver mints it.
DECLARED_SOURCE = ProvenanceSource(
    kind="artifact", identity="fixture/request-contract", version="1"
)

#: The needle the C-10 sabotage cuts, and the marker that makes it findable.
ENTITLEMENT_NEEDLE = (
    "            # D-07: entitlement verified here\n"
    "            entitled = grant is not None and policy_id in grant.overridable_policies"
)
ENTITLEMENT_SABOTAGE = "            entitled = True"


# --- fixtures ----------------------------------------------------------------


def _contract() -> ProductRequestContract:
    """A class declaring the tolerance and one other parameter."""
    return ProductRequestContract(
        semver="1.0.0",
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        arguments=SkillArgumentSchema(
            properties={
                DEBT_TOLERANCE_PARAMETER: SkillArgumentProperty(
                    type="number", description="a fixture tolerance"
                ),
                THRESHOLD_PARAMETER: SkillArgumentProperty(
                    type="number", description="a fixture threshold"
                ),
            },
            required=(),
        ),
    )


CONTRACT = _contract()


def _constraint(
    *,
    policy_id: str,
    value: Decimal,
    effective_from: datetime,
    effective_until: datetime | None,
    overridable: bool = False,
) -> PolicyConstraint:
    """A ``maximum`` on the tolerance, applicable to everything in its window."""
    return PolicyConstraint(
        semver="1.0.0",
        policy_id=policy_id,
        applies_to=ConstraintApplicability(),
        parameter=DEBT_TOLERANCE_PARAMETER,
        operator="maximum",
        value=value,
        overridable=overridable,
        source_authority="fixture-authority",
        effective_from=effective_from,
        effective_until=effective_until,
        reason="a fixture reason",
    )


def _register_two_windows(
    registry: ControlPlaneRegistry, *, overridable: bool = False
) -> tuple[str, str]:
    """``a`` in force over ``[T0, T1)`` and ``b`` from ``T1``; their versions."""
    version_a = registry.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_EARLY,
            effective_from=T0,
            effective_until=T1,
            overridable=overridable,
        ),
        POLICY_CONSTRAINT,
    )
    version_b = registry.register_typed(
        KEY_B,
        _constraint(
            policy_id=POLICY_B,
            value=MAXIMUM_LATE,
            effective_from=T1,
            effective_until=None,
        ),
        POLICY_CONSTRAINT,
    )
    return version_a, version_b


def _register_entitlement(registry: ControlPlaneRegistry) -> str:
    """One tenant policy: the entitled principal may override ``a``, the other may not."""
    return registry.register_typed(
        product_entitlement_key(tenant_id=TENANT),
        ProductEntitlementPolicy(
            tenant_id=TENANT,
            policy_version="1.0.0",
            principals={
                ENTITLED_PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({PRODUCT_CLASS}),
                    permitted_roles=frozenset({ROLE}),
                    overridable_policies=frozenset({POLICY_A}),
                ),
                UNENTITLED_PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({PRODUCT_CLASS}),
                    permitted_roles=frozenset({ROLE}),
                ),
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


def _question(
    *, asked_at: datetime, overrides: tuple[str, ...] = ()
) -> ProductRequest:
    """The caller asks for more tolerance than either constraint allows."""
    return ProductRequest(
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        subject="fixture:subject/one",
        intent="fixture-intent",
        freshness="fixture-freshness",
        asked_at=asked_at,
        parameters={DEBT_TOLERANCE_PARAMETER: CALLER_ASKS},
        policy_overrides=overrides,
    )


def _resolve(
    registry: ControlPlaneRegistry,
    *,
    asked_at: datetime,
    perspective: Perspective = ENTITLED,
    overrides: tuple[str, ...] = (),
    entitlement_key: str | None = None,
    module: types.ModuleType | None = None,
) -> Any:
    """Resolve through the real reference resolver, or a scratch copy of it."""
    target = module or constraints_module
    resolver = target.ReferencePolicyConstraintResolver(
        control_plane=registry,
        entitlement_key=(
            product_entitlement_key(tenant_id=TENANT)
            if entitlement_key is None
            else entitlement_key
        ),
    )
    return resolver.resolve(
        product_class=PRODUCT_CLASS,
        request=_question(asked_at=asked_at, overrides=overrides),
        declared=CONTRACT,
        declared_source=DECLARED_SOURCE,
        perspective=perspective,
        intent="fixture-intent",
        tenant=TENANT,
        capabilities=(),
    )


def _constraint_pins(resolved: EffectiveRequest) -> tuple[tuple[str, str], ...]:
    """The ``(key, version)`` pairs in ``applied`` that are constraint keys.

    The request contract's own pin is in ``applied`` too — *"nothing applied"*
    is a claim that needs the same evidence as *"this applied"* — so the
    constraint half is selected by key rather than by counting.
    """
    return tuple(
        (source.identity, source.version or "")
        for source in resolved.applied
        if source.identity in {KEY_A, KEY_B}
    )


def _scratch_constraints(
    tmp_path: pathlib.Path, *, name: str, needle: str, replacement: str
) -> types.ModuleType:
    """A copy of ``constraints.py`` with one fragment rewritten, loaded by name.

    The count is asserted **before** the mutation, so a needle that has drifted
    fails loudly here instead of producing a copy identical to the original —
    which would make the control green for the wrong reason, and a green
    control is worse than none. The idiom, and the ``sys.modules`` entry the
    module's ``@dataclass`` needs, are ``test_policy_constraints.py``'s.
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
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


# --- (a) effectivity: the window decides, at the request's own instant --------


def test_a_request_inside_the_first_window_resolves_the_first_constraint(
    registry: ControlPlaneRegistry,
) -> None:
    """``D-IMPL-253`` Q6. The caller asks ``.30``; ``a`` bounds them to ``.20``."""
    version_a, _version_b = _register_two_windows(registry)

    resolved = _resolve(registry, asked_at=BEFORE_T1)

    assert isinstance(resolved, EffectiveRequest)
    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == MAXIMUM_EARLY
    assert tolerance.authority == "policy"
    assert _constraint_pins(resolved) == ((KEY_A, version_a),)


def test_a_request_at_the_boundary_instant_resolves_the_second(
    registry: ControlPlaneRegistry,
) -> None:
    """Half-open, so the instant one window ends is the instant the next begins.

    The same question, one instant later, resolves a **different policy** to a
    different number — which is exactly the property replay would lose if
    effectivity were evaluated at "now".
    """
    _version_a, version_b = _register_two_windows(registry)

    resolved = _resolve(registry, asked_at=T1)

    assert isinstance(resolved, EffectiveRequest)
    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == MAXIMUM_LATE
    assert _constraint_pins(resolved) == ((KEY_B, version_b),)


def test_the_two_windows_never_resolve_together(
    registry: ControlPlaneRegistry,
) -> None:
    """The control for both tests above: neither instant sees both constraints.

    Asserted as a roster rather than as a count — a resolution carrying one pin
    with the wrong key would satisfy "exactly one" forever.
    """
    _register_two_windows(registry)

    for instant in (T0, BEFORE_T1, T1, T1 + timedelta(days=365)):
        in_force = constraints_in_force(registry, asked_at=instant)
        assert len(in_force) == 1, instant
        expected = KEY_A if instant < T1 else KEY_B
        assert in_force[0].key == expected, instant


def test_the_pinned_versions_are_the_registrys_own_content_addresses(
    registry: ControlPlaneRegistry,
) -> None:
    """Exact, and re-resolvable: the version an examiner replays against."""
    version_a, _ = _register_two_windows(registry)
    resolved = _resolve(registry, asked_at=BEFORE_T1)

    assert isinstance(resolved, EffectiveRequest)
    ((key, version),) = _constraint_pins(resolved)
    assert (key, version) == (KEY_A, version_a)
    assert version == content_hash(registry.peek(KEY_A, version_a))
    assert registry.resolve(KEY_A, version) is not None


def test_the_resolution_never_reaches_for_the_latest_version(
    registry: ControlPlaneRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-24.6-10, made unable to pass by inspection.

    ``resolve_latest`` is replaced by a raise for the whole resolution: a reach
    for it is a test failure rather than a difference nobody notices at replay.
    """
    _register_two_windows(registry)

    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "the resolution reached for the most recently registered version;"
            " replay of the same historical decision would resolve a different"
            " policy (D-IMPL-253 Q6)"
        )

    monkeypatch.setattr(ControlPlaneRegistry, "resolve_latest", _refuse)
    resolved = _resolve(registry, asked_at=BEFORE_T1)

    assert isinstance(resolved, EffectiveRequest)


def test_the_latest_guard_can_fire(
    registry: ControlPlaneRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CONTROL — the monkeypatch above is capable of failing a test.

    Without this, a ``resolve_latest`` that had been renamed would make the
    guard silently unable to fire, and the test above would pass for the wrong
    reason.
    """
    _register_two_windows(registry)

    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("reached")

    monkeypatch.setattr(ControlPlaneRegistry, "resolve_latest", _refuse)
    with pytest.raises(AssertionError, match="reached"):
        registry.resolve_latest(KEY_A)


def test_two_versions_of_one_key_in_force_at_once_is_a_conflict(
    registry: ControlPlaneRegistry,
) -> None:
    """Dave's rule: two authoritative inputs contradict → a failure, not a "no".

    Both versions of ``a`` cover the instant, so the Control Plane says the
    tolerance is bounded two ways at once. Picking either would make one
    decision replayable two ways, so neither is picked.
    """
    first = registry.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_EARLY,
            effective_from=T0,
            effective_until=None,
        ),
        POLICY_CONSTRAINT,
    )
    second = registry.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_LATE,
            effective_from=T0,
            effective_until=None,
        ),
        POLICY_CONSTRAINT,
    )
    assert first != second

    with pytest.raises(ConstraintEffectivityConflict) as raised:
        constraints_in_force(registry, asked_at=BEFORE_T1)

    message = str(raised.value)
    assert KEY_A in message
    assert first in message and second in message


def test_a_superseded_version_of_one_key_is_not_a_conflict(
    registry: ControlPlaneRegistry,
) -> None:
    """The control: two versions under one key are ordinary history.

    What the conflict names is two versions **in force at one instant**, not
    two versions existing. A registry whose windows do not overlap resolves
    cleanly however many versions it holds.
    """
    registry.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_EARLY,
            effective_from=T0,
            effective_until=T1,
        ),
        POLICY_CONSTRAINT,
    )
    later = registry.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_LATE,
            effective_from=T1,
            effective_until=None,
        ),
        POLICY_CONSTRAINT,
    )

    in_force = constraints_in_force(registry, asked_at=T1)

    assert [(pin.key, pin.version) for pin in in_force] == [(KEY_A, later)]


# --- (b) the override: a name is not a password ------------------------------


def test_an_entitled_principal_overrides_the_constraint(
    registry: ControlPlaneRegistry,
) -> None:
    """``D-IMPL-253`` Q7. Named, entitled, and the artifact admits an exception."""
    _register_two_windows(registry, overridable=True)
    entitlement_version = _register_entitlement(registry)

    resolved = _resolve(
        registry, asked_at=BEFORE_T1, perspective=ENTITLED, overrides=(POLICY_A,)
    )

    assert isinstance(resolved, EffectiveRequest)
    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == CALLER_ASKS, "the constraint did not apply"
    assert tolerance.authority == "caller"
    (record,) = resolved.overrides
    assert (record.policy_id, record.entitled, record.honored) == (
        POLICY_A,
        True,
        True,
    )
    assert record.principal_id == ENTITLED_PRINCIPAL
    assert record.grant_source == ProvenanceSource(
        kind="artifact",
        identity=product_entitlement_key(tenant_id=TENANT),
        version=entitlement_version,
    )


def test_a_name_only_override_is_not_honored(
    registry: ControlPlaneRegistry,
) -> None:
    """C-10. The same request, by a principal whose grant does not list ``a``.

    Dave: *"Otherwise anyone who knows a policy ID could bypass it."* The
    constraint applies, the caller's ``.30`` is bounded to ``.20``, and the
    attempt is **recorded** with both halves false rather than dropped.
    """
    _register_two_windows(registry, overridable=True)
    _register_entitlement(registry)

    resolved = _resolve(
        registry, asked_at=BEFORE_T1, perspective=UNENTITLED, overrides=(POLICY_A,)
    )

    assert isinstance(resolved, EffectiveRequest)
    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == MAXIMUM_EARLY, "the constraint applied"
    assert tolerance.authority == "policy"
    (record,) = resolved.overrides
    assert (record.policy_id, record.entitled, record.honored) == (
        POLICY_A,
        False,
        False,
    )
    assert record.principal_id == UNENTITLED_PRINCIPAL
    assert record.grant_source is None


def test_an_override_of_a_policy_nobody_registered_is_recorded_and_not_honored(
    registry: ControlPlaneRegistry,
) -> None:
    """An attempt to override a policy that is not there is still an attempt.

    It carries the positive *no constraint in force under that name* lane
    rather than a lane invented for it, because
    :class:`~ccf.products.provenance.OverrideRecord` requires the version
    precisely so a nameless claim cannot be filed.
    """
    _register_two_windows(registry, overridable=True)
    _register_entitlement(registry)

    resolved = _resolve(
        registry,
        asked_at=BEFORE_T1,
        perspective=ENTITLED,
        overrides=(UNREGISTERED_POLICY,),
    )

    assert isinstance(resolved, EffectiveRequest)
    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == MAXIMUM_EARLY, "the applicable constraint still applied"
    (record,) = resolved.overrides
    assert (record.policy_id, record.entitled, record.honored) == (
        UNREGISTERED_POLICY,
        False,
        False,
    )
    assert record.policy_version != ""


def test_an_entitled_override_of_a_non_overridable_constraint_is_not_honored(
    registry: ControlPlaneRegistry,
) -> None:
    """Two declarations, and the exception exists only where both agree.

    The grant says this principal *may* exercise an exception to ``a``; the
    artifact says ``a`` admits none. The attempt is recorded as entitled and
    unhonored — which is the pair of facts an auditor needs, and which a single
    boolean would lose.
    """
    _register_two_windows(registry, overridable=False)
    _register_entitlement(registry)

    resolved = _resolve(
        registry, asked_at=BEFORE_T1, perspective=ENTITLED, overrides=(POLICY_A,)
    )

    assert isinstance(resolved, EffectiveRequest)
    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == MAXIMUM_EARLY
    (record,) = resolved.overrides
    assert (record.entitled, record.honored) == (True, False)


def test_with_no_entitlement_policy_registered_no_override_is_entitled(
    registry: ControlPlaneRegistry,
) -> None:
    """Deny-by-default: an absent policy grants nothing, and is not an error."""
    _register_two_windows(registry, overridable=True)

    resolved = _resolve(
        registry, asked_at=BEFORE_T1, perspective=ENTITLED, overrides=(POLICY_A,)
    )

    assert isinstance(resolved, EffectiveRequest)
    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == MAXIMUM_EARLY
    (record,) = resolved.overrides
    assert (record.entitled, record.honored) == (False, False)


def test_a_name_only_override_being_honored_is_red_sabotage(
    registry: ControlPlaneRegistry, tmp_path: pathlib.Path
) -> None:
    """The C-10 guard, watched firing on a copy where the check is gone.

    The sabotage replaces the entitlement comparison with ``entitled = True`` —
    the shape of the defect Q7 names, where knowing a policy id is enough. On
    that copy the unentitled request is served **without the bound**, and the
    assertion the shipped test makes fails.

    Only the copy under ``tmp_path`` is mutated; the real module's bytes are
    asserted unchanged by ``test_no_sabotage_edits_the_real_source_tree``.
    """
    _register_two_windows(registry, overridable=True)
    _register_entitlement(registry)
    scratch = _scratch_constraints(
        tmp_path,
        name="constraints_honoring_a_name_only_override",
        needle=ENTITLEMENT_NEEDLE,
        replacement=ENTITLEMENT_SABOTAGE,
    )

    sabotaged = _resolve(
        registry,
        asked_at=BEFORE_T1,
        perspective=UNENTITLED,
        overrides=(POLICY_A,),
        module=scratch,
    )

    assert isinstance(sabotaged, EffectiveRequest)
    tolerance = sabotaged.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.value == CALLER_ASKS, (
        "the sabotage did not take: the copy must honor the name-only override"
    )
    with pytest.raises(AssertionError):
        # The shipped assertion, verbatim, against the sabotaged resolution.
        assert tolerance.value == MAXIMUM_EARLY, "the constraint applied"
    (record,) = sabotaged.overrides
    assert (record.entitled, record.honored) == (True, True)


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """The controls mutate a copy; the module under test is byte-identical."""
    assert CONSTRAINTS_PATH.read_bytes() == CONSTRAINTS_SOURCE


# --- (c) through the booted resolver: the pin reaches replay -----------------


@pytest.fixture
def booted_with_tolerance(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The seam fixture's ceiling deployment, whose contract declares the tolerance.

    Imported rather than restated: a second copy of a fixture deployment is a
    second thing to keep in step, and what this module adds is the Control
    Plane content, not another manifest.
    """
    product_class = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    product_class["serve_obligations"] = {"debt_ceiling": CEILING_DECLARED}
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    request_contract["declaration"]["arguments"]["properties"][
        DEBT_TOLERANCE_PARAMETER
    ] = {"type": "number", "description": "Fixture tolerance; a proportion."}
    yield from _boot(
        tmp_path, product_class=product_class, request_contract=request_contract
    )


def _governed(booted: _Booted) -> Any:
    """The seam's own wiring, with the reference resolver over its registry."""
    return _resolver(
        booted,
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=booted.control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
    )


def _stored_record(booted: _Booted, outcome: ServedProduct) -> dict[str, Any]:
    """The replay record as it was written, read back from the artifact store."""
    raw = booted.store.get(content_address=outcome.replay_ref.content_address)
    stored: dict[str, Any] = json.loads(raw)
    return stored


def test_the_constraint_pin_and_the_resolution_reach_replay_dimension_two(
    booted_with_tolerance: _Booted,
) -> None:
    """C-09 through the door: the version in force is a binding, and the resolution is recorded.

    The constraint bounds the caller's ``.30`` to ``.20``; the served product's
    record names ``(policy_constraints.a, <content hash>)`` among its policy
    bindings, and ``request_resolution`` round-trips to the very
    ``EffectiveRequest`` that produced the answer.
    """
    version_a = booted_with_tolerance.control_plane.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_EARLY,
            effective_from=T0,
            effective_until=None,
        ),
        POLICY_CONSTRAINT,
    )

    outcome = _ask(
        _governed(booted_with_tolerance),
        _request(
            parameters={
                THRESHOLD_PARAMETER: 1000,
                DEBT_TOLERANCE_PARAMETER: CALLER_ASKS,
            }
        ),
    )

    assert isinstance(outcome, ServedProduct), outcome
    stored = _stored_record(booted_with_tolerance, outcome)
    bindings = {
        (row["key"], row["version"])
        for row in stored["policy_bindings"]["bindings"]
    }
    assert (KEY_A, version_a) in bindings

    # Read with the sentinel as the fallback rather than by direct index: the
    # field is hash-transparent, so a record that recorded NO resolution omits
    # the key entirely, and a `KeyError` would report the guard's own shape
    # instead of the property it guards.
    rendered = stored["policy_bindings"].get(
        "request_resolution", NO_REQUEST_RESOLUTION
    )
    assert rendered != NO_REQUEST_RESOLUTION, (
        "the record carries no resolution: what bounded this question, and on"
        " whose authority, is not recoverable from it (D-IMPL-254)"
    )
    resolution = EffectiveRequest.model_validate_json(rendered)
    assert canonical_bytes(resolution).decode("utf-8") == rendered
    tolerance = resolution.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    # `EffectiveParameter.value` is typed `Any`, and the canonical form renders
    # a `Decimal` as a quoted number (a float is not bit-stable, so the
    # canonicalizer refuses one) — so a value that round-trips through the
    # RECORD comes back as the string the record holds. The record is faithful:
    # the bytes are what replay compares. Read as a decimal here rather than
    # asserted as one, and stated rather than glossed.
    assert Decimal(str(tolerance.value)) == MAXIMUM_EARLY
    assert tolerance.authority == "policy"
    assert tolerance.bound is not None
    assert tolerance.bound.policy_id == POLICY_A
    assert resolution.asked_at == ASKED_AT


def test_the_recorded_question_is_the_callers_and_the_resolution_is_its_sibling(
    booted_with_tolerance: _Booted,
) -> None:
    """T-24.6-12 on the path where it can actually be lost: the served one.

    Dimension 5 records *the question a decision answered* and dimension 2
    records *what that question resolved to*. They are two facts, and the
    tempting shortcut — resolving in place and handing the engine's request
    onward — destroys the first: the record would say the caller asked for the
    policy's number, which is exactly the sentence ``D-IMPL-253`` Q1 exists to
    keep true (*"you asked for .30 and policy a bounds you to .20"*).

    Sabotage: rebind the caller's ``request`` to the effective one in
    ``GovernedResolver.__call__`` and this goes RED on the dimension-5
    assertion while every other test in this module stays green.
    """
    booted_with_tolerance.control_plane.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_EARLY,
            effective_from=T0,
            effective_until=None,
        ),
        POLICY_CONSTRAINT,
    )

    outcome = _ask(
        _governed(booted_with_tolerance),
        _request(
            parameters={
                THRESHOLD_PARAMETER: 1000,
                DEBT_TOLERANCE_PARAMETER: CALLER_ASKS,
            }
        ),
    )

    assert isinstance(outcome, ServedProduct), outcome
    stored = _stored_record(booted_with_tolerance, outcome)
    recorded = stored["content_generation_path"]["request"]["parameters"]
    assert Decimal(str(recorded[DEBT_TOLERANCE_PARAMETER])) == CALLER_ASKS, (
        "dimension 5 recorded the resolved value as the question: what the"
        " caller actually asked is no longer recoverable from the record"
    )

    resolution = EffectiveRequest.model_validate_json(
        stored["policy_bindings"]["request_resolution"]
    )
    tolerance = resolution.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert Decimal(str(tolerance.value)) == MAXIMUM_EARLY
    assert Decimal(str(recorded[DEBT_TOLERANCE_PARAMETER])) != Decimal(
        str(tolerance.value)
    ), "the control: the two facts must differ here, or this proves nothing"


def test_a_deployment_with_no_constraints_records_a_resolution_all_the_same(
    booted_with_tolerance: _Booted,
) -> None:
    """The control: *"nothing applied"* is a claim, and it carries its evidence.

    With no constraint registered the same question serves, the record still
    carries a resolution rather than the sentinel, and the tolerance is the
    caller's own — so the test above is measuring the constraint's effect and
    not merely the presence of a field.
    """
    outcome = _ask(
        _governed(booted_with_tolerance),
        _request(
            parameters={
                THRESHOLD_PARAMETER: 1000,
                DEBT_TOLERANCE_PARAMETER: Decimal("0.30"),
            }
        ),
    )

    assert isinstance(outcome, ServedProduct), outcome
    stored = _stored_record(booted_with_tolerance, outcome)
    rendered = stored["policy_bindings"].get(
        "request_resolution", NO_REQUEST_RESOLUTION
    )
    assert rendered != NO_REQUEST_RESOLUTION, (
        "a resolution with no applicable constraint is still a resolution, and"
        " 'nothing applied' is a claim that needs its evidence recorded"
    )
    resolution = EffectiveRequest.model_validate_json(rendered)
    tolerance = resolution.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert Decimal(str(tolerance.value)) == CALLER_ASKS
    assert tolerance.authority == "caller"
    assert not any(
        key in {KEY_A, KEY_B}
        for key, _version in (
            (row["key"], row["version"])
            for row in stored["policy_bindings"]["bindings"]
        )
    )


def test_a_refusal_carries_the_callers_parameters_not_the_effective_ones(
    booted_with_tolerance: _Booted,
) -> None:
    """T-24.6-12. The identity is what was ASKED; the resolution is what was decided.

    A caller asking for a tolerance outside ``[0, 1]`` is refused by name at the
    boundary — over the *effective* request, which is the sequence's whole
    point — and the envelope's identity still carries the number the caller
    supplied, so the refusal can say what was asked for.
    """
    booted_with_tolerance.control_plane.register_typed(
        KEY_A,
        _constraint(
            policy_id=POLICY_A,
            value=MAXIMUM_EARLY,
            effective_from=T0,
            effective_until=None,
        ),
        POLICY_CONSTRAINT,
    )
    asked = {THRESHOLD_PARAMETER: 1000, DEBT_TOLERANCE_PARAMETER: -1}

    outcome = _ask(_governed(booted_with_tolerance), _request(parameters=asked))

    assert isinstance(outcome, RefusalEnvelope), outcome
    assert outcome.kind == "product-request-violation"
    assert outcome.reason == "not-a-proportion"
    assert dict(outcome.request.parameters) == asked
    assert outcome.pre_assembly_lineage is None
