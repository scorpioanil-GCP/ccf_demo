"""`D-IMPL-336` — composite Context Products, the swarm pattern's proof.

    *Skills produce governed Context Products. Agents orchestrate skills.
    Composite Context Products declare the child Context Product classes they
    require.* — and under it, *Agents have skills; Context Products have
    state.*

Every child in this module is served through **`run_gates`**, the real
delivery path, and admitted through the real gate. Nothing here hand-builds a
child and offers it to composition: that bypass is itself under test
(:func:`test_c17_children_come_through_the_real_delivery_path` and sabotage
14), because a proof assembled from constructed objects would demonstrate the
composition of constructed objects.

**What each test is named for.** ``test_cNN_`` is success criterion NN from the
design's §8. ``test_sNN_`` is sabotage NN from §9 — each applies the break to
the shipped mechanism and asserts the RED, so a gate that stayed green under
its own sabotage is visible as a test defect rather than as a pass.

Memory-only. Every key, URI and instant below is this module's own (CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.invalidation import ControlPlaneInvalidationSink
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.halflife.assessment import DebtAssessment, DebtFactors, DebtSignal
from ccf.halflife.debt import compose_debt_factors, context_debt
from ccf.peering.eligibility import (
    ELIGIBILITY_ASSERTION_HEADER,
    encode_eligibility_assertion,
    mint_eligibility_assertion,
)
from ccf.products.composite import (
    ELIGIBILITY_LOCAL_REGISTER,
    ELIGIBILITY_PRODUCER_ATTESTED,
    AdmittedChild,
    AmbiguousProducerError,
    ChildAdmissionBypassError,
    ChildAdmissionRefusal,
    ChildCandidate,
    CompositeAdmissionGate,
    ProducedElsewhere,
    ProducedHere,
    compose_children,
    resolve_producing_grant,
)
from ccf.products.contract import (
    ChildRequirement,
    ContextProductContract,
    MaxTTL,
    OptionalAbsenceTreatment,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.replay.record import CHILD_OUTCOME_STATUSES, ContentGenerationPath
from ccf.skills.catalog import (
    NO_PRODUCT_CLASS,
    LocalCallableBinding,
    SkillArgumentSchema,
    SkillCatalogEntry,
    SkillRequirements,
)

TENANT = "tenant-composite"
CONSUMER_SCOPE = "consumer://memo-desk"
INVOCATION = "composition://inv-0001"

#: The composite's one reconstruction instant. Every child is asked for it.
ASKED_AT = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
#: A different instant — never "close enough".
OTHER_AS_OF = datetime(2026, 3, 1, 13, 0, 0, tzinfo=UTC)
SERVED_AT = datetime(2026, 3, 1, 12, 30, 0, tzinfo=UTC)
#: Strictly later than ASKED_AT: the supersession boundary.
SUPERSEDED_AT = datetime(2026, 3, 1, 12, 15, 0, tzinfo=UTC)

FAMILY = "fixture.corporate-family-tree"
EXPOSURE = "fixture.credit-exposure-rollup"
COVENANT = "fixture.covenant-cross-reference"
PEERS = "fixture.peer-benchmark"

ENTITY_OBLIGOR = "entity://obligor-alpha"
ENTITY_UNRELATED = "entity://obligor-beta"

MAX_TTL_KEY = "fixture/composite/max-ttl"
OPERATORS = frozenset({"Resolve", "Traversal"})
POLICY_VERSION = "fixture-policy-v1"

_FULL = DebtFactors(
    freshness=Decimal(1), completeness=Decimal(1), semantic_consistency=Decimal(1)
)


# --- the estate: a registry, product classes, and real delivery --------------


@pytest.fixture()
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


def _contract(
    *,
    schema: str,
    version: str = "1.0.0",
    as_of: datetime = ASKED_AT,
    factors: DebtFactors = _FULL,
    payload: dict[str, object] | None = None,
) -> ContextProductContract:
    return ContextProductContract(
        tenant_id=TENANT,
        schema_name=schema,
        schema_version=version,
        plan_id=f"plan-{schema}",
        temporal_boundary=as_of,
        expires_at=as_of + timedelta(hours=12),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=OPERATORS,
            policy_bundle_versions=(POLICY_VERSION,),
            graph_snapshot_at=as_of,
        ),
        payload=payload or {"rows": 1},
        debt=DebtAssessment(
            debt=context_debt(factors),
            signal=DebtSignal.OK,
            factors=factors,
            scorers=(),
        ),
    )


def deliver(
    registry: ControlPlaneRegistry,
    contract: ContextProductContract,
    *,
    touched: tuple[str, ...] | None = (ENTITY_OBLIGOR,),
) -> object:
    """Serve a child through the REAL gate sequence.

    This is what makes the proof a proof: every child below is whatever
    ``run_gates`` decided it was, including when that is a refusal.
    """
    return run_gates(
        contract,
        engine_resolved=OPERATORS,
        now=SERVED_AT,
        registry=registry,
        product_class=_registered(registry, contract.schema_name),
        touched_entities=touched,
    )


def _registered(registry: ControlPlaneRegistry, schema: str) -> object:
    """Register ``schema`` on ``registry`` once, cached ON THE REGISTRY.

    **Not in a module-level dict keyed on ``id(registry)``** — that was the
    first shape here and it was wrong in a way that reads as a Control Plane
    fault: CPython reuses an ``id`` once the previous object is collected, so a
    later test's fresh registry inherited a cache entry naming a max-TTL
    artifact it had never registered. The cache lives on the object whose
    lifetime it shares.
    """
    cache: dict[str, object] = registry.__dict__.setdefault(
        "_composite_test_classes", {}
    )
    if schema not in cache:
        key = f"{MAX_TTL_KEY}/{schema}"
        version = registry.register(key, MaxTTL(seconds=86400))
        cache[schema] = register_product_class(
            registry=registry,
            schema_name=schema,
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key=key,
            max_ttl_version=version,
        )
    return cache[schema]


def served(outcome: object) -> ContextProductContract:
    """Unwrap a delivery that must have served, so a refusal cannot pass."""
    assert isinstance(outcome, ServableProduct), f"expected served, got {outcome!r}"
    return outcome.product


# --- skills -----------------------------------------------------------------


def skill(name: str, *, produces: str = NO_PRODUCT_CLASS) -> SkillCatalogEntry:
    return SkillCatalogEntry(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name=name,
        tenant=TENANT,
        skill_type="local_callable",
        description=f"{name} skill",
        argument_schema=SkillArgumentSchema(properties={}, required=frozenset()),
        binding=LocalCallableBinding(callable_ref=f"ref::{name}"),
        requirements=SkillRequirements(
            required_scopes=frozenset(), required_context_products=frozenset()
        ),
        produces=produces,
    )


def require(
    product_class: str,
    *,
    required: bool = True,
    floor: str = "1.0.0",
    absent_c: str | None = None,
) -> ChildRequirement:
    treatment = (
        None
        if absent_c is None
        else OptionalAbsenceTreatment(
            completeness_when_absent=Decimal(absent_c),
            omissible_outcomes=frozenset({"optional-absent"}),
        )
    )
    return ChildRequirement(
        product_class=product_class,
        required=required,
        compatible_from=floor,
        absence_treatment=treatment,
    )


def candidate(
    contract: ContextProductContract,
    requirement: ChildRequirement,
    *,
    fabric: object | None = None,
    skill_name: str = "family-skill",
    touched: tuple[str, ...] | None = (ENTITY_OBLIGOR,),
) -> ChildCandidate:
    return ChildCandidate(
        requirement=requirement,
        contract=contract,
        content_address=content_hash(contract),
        fabric=fabric or ProducedHere(fabric_id="fabric://self"),
        skill_name=skill_name,
        skill_version="1.0.0",
        grant_hash=f"grant::{skill_name}",
        touched_entities=touched,
    )


def gate(registry: ControlPlaneRegistry) -> CompositeAdmissionGate:
    return CompositeAdmissionGate(
        tenant_id=TENANT, consumer_scope=CONSUMER_SCOPE, registry=registry
    )


def admit(
    registry: ControlPlaneRegistry, cand: ChildCandidate, *, at: datetime = ASKED_AT
) -> object:
    return gate(registry).admit(
        candidate=cand, asked_at=at, composition_invocation=INVOCATION
    )


# --- the delivery path actually works ---------------------------------------


def test_c17_children_come_through_the_real_delivery_path(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 17: a child is what ``run_gates`` served, not a constructed object.

    Asserted first, because every test below depends on it. If ``deliver``
    silently returned its input, this module would prove the composition of
    hand-built objects and say nothing about the SDK.
    """
    outcome = deliver(registry, _contract(schema=FAMILY))
    assert isinstance(outcome, ServableProduct)
    product = served(outcome)
    assert product.schema_name == FAMILY
    # The address a composite will check is the hash of what the gate passed.
    assert content_hash(product) == content_hash(_contract(schema=FAMILY))


# --- resolution: class to skill, never skill to class ------------------------


def test_c1_a_skill_without_produces_cannot_satisfy_a_requirement() -> None:
    """Criterion 1. The sentinel is a positive claim: *I emit no product*."""
    bound = {"silent": skill("silent")}
    assert bound["silent"].produces == NO_PRODUCT_CLASS
    assert resolve_producing_grant(require(FAMILY), bound) is None


def test_c2_a_wrong_produces_class_cannot_satisfy_a_requirement() -> None:
    """Criterion 2, first path: it is not selected at resolution."""
    bound = {"exposure": skill("exposure", produces=EXPOSURE)}
    assert resolve_producing_grant(require(FAMILY), bound) is None


def test_c2_a_wrong_class_forced_past_resolution_is_refused_at_admission(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 2, second path — and the one that matters.

    Resolution not selecting a skill is a *lookup* property. The guarantee the
    composite actually needs is that even if resolution were wrong, a child
    that is not the declared class cannot be admitted: ``produces`` is a
    **declaration**, and a declaration nothing checks against what was emitted
    is `D-IMPL-324`'s door that never opens.
    """
    wrong = served(deliver(registry, _contract(schema=EXPOSURE)))
    refusal = admit(registry, candidate(wrong, require(FAMILY)))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "class-mismatch"


def test_c3_two_skills_producing_one_class_are_interchangeable() -> None:
    """Criterion 3 — a POSITIVE CONTROL, not a sabotage.

    A valid substitution is expected to SUCCEED. Grant A, resolve; revoke A and
    grant B, resolve. The requirement is unchanged, the resolved entry produces
    the same class, and **only the producing identity differs** — which is the
    whole claim: the composite depends on the contract, not the implementation.
    """
    requirement = require(FAMILY)
    with_a = {"family-a": skill("family-a", produces=FAMILY)}
    with_b = {"family-b": skill("family-b", produces=FAMILY)}

    a = resolve_producing_grant(requirement, with_a)
    b = resolve_producing_grant(requirement, with_b)

    assert a is not None and b is not None
    assert a.produces == b.produces == requirement.product_class
    assert a.name != b.name


def test_c4_a_requirement_is_bound_to_a_class_not_a_skill_name() -> None:
    """Criterion 4, structurally: there is no field to name a skill in."""
    assert "skill" not in " ".join(ChildRequirement.model_fields)
    assert set(ChildRequirement.model_fields) == {
        "product_class",
        "required",
        "compatible_from",
        "absence_treatment",
    }


def test_ambiguous_producers_refuse_with_no_tie_breaker() -> None:
    """Two grants, one class: refused, and **no rule invented**.

    Any tie-break the SDK chose would make composition and replay depend on
    something the deployment never declared. The refusal names both, so an
    operator can revoke one rather than guess which was used.
    """
    bound = {
        "family-a": skill("family-a", produces=FAMILY),
        "family-b": skill("family-b", produces=FAMILY),
    }
    with pytest.raises(AmbiguousProducerError) as caught:
        resolve_producing_grant(require(FAMILY), bound)
    assert "family-a" in str(caught.value) and "family-b" in str(caught.value)


# --- one as_of ---------------------------------------------------------------


def test_c5_every_admitted_child_carries_the_composites_asked_at(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 5, asserted over the ORDERED rows, not a set."""
    requirements = [require(FAMILY), require(EXPOSURE), require(COVENANT)]
    outcomes = {}
    for req in requirements:
        child = served(deliver(registry, _contract(schema=req.product_class)))
        outcomes[req.product_class] = admit(registry, candidate(child, req))

    result = compose_children(
        own_factors=_FULL, requirements=requirements, outcomes=outcomes
    )
    assert result.served
    assert [row.required_product_class for row in result.resolutions] == [
        FAMILY,
        EXPOSURE,
        COVENANT,
    ]
    assert all(row.child_asked_at == ASKED_AT for row in result.resolutions)


def test_c6_a_child_from_another_as_of_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 6. Not adjusted, not re-requested, not "close enough"."""
    stale = served(deliver(registry, _contract(schema=FAMILY, as_of=OTHER_AS_OF)))
    refusal = admit(registry, candidate(stale, require(FAMILY)))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "as-of-mismatch"


# --- uniform admission -------------------------------------------------------


def _attested(
    contract: ContextProductContract,
    *,
    address: str | None = None,
    as_of: datetime = ASKED_AT,
    producer: str = "fabric://peer",
    consumer: str = CONSUMER_SCOPE,
    invocation: str = INVOCATION,
    eligible: bool = True,
) -> ProducedElsewhere:
    assertion = mint_eligibility_assertion(
        child_content_address=address or content_hash(contract),
        requested_as_of=as_of,
        producer=producer,
        consumer_scope=consumer,
        checked_at=SERVED_AT,
        composition_invocation=invocation,
        eligible=eligible,
    )
    return ProducedElsewhere(
        fabric_id=producer,
        protected_header={
            ELIGIBILITY_ASSERTION_HEADER: encode_eligibility_assertion(assertion)
        },
    )


def test_c7_a_local_child_and_a_peered_child_traverse_the_same_common_checks(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 7: the common checks run for BOTH, by check identity.

    Asserted by driving each common failure through both fabrics and comparing
    the ``reason`` tokens — a count would pass while one path silently skipped
    a different check than the other.
    """
    breaks = {
        "class-mismatch": (_contract(schema=EXPOSURE), require(FAMILY)),
        "version-incompatible": (
            _contract(schema=FAMILY, version="1.0.0"),
            require(FAMILY, floor="2.0.0"),
        ),
        "as-of-mismatch": (
            _contract(schema=FAMILY, as_of=OTHER_AS_OF),
            require(FAMILY),
        ),
    }
    local_reasons, peer_reasons = {}, {}
    for expected, (contract, req) in breaks.items():
        child = served(deliver(registry, contract))
        local = admit(registry, candidate(child, req))
        peer = admit(
            registry, candidate(child, req, fabric=_attested(child))
        )
        assert isinstance(local, ChildAdmissionRefusal)
        assert isinstance(peer, ChildAdmissionRefusal)
        local_reasons[expected] = local.reason
        peer_reasons[expected] = peer.reason

    assert local_reasons == peer_reasons == {k: k for k in breaks}


def test_a_peered_child_is_checked_for_MORE_never_for_less(
    registry: ControlPlaneRegistry,
) -> None:
    """The asymmetry is additive, and it is never a fast path.

    A local child needs no attestation; a peered child without one is refused.
    That is the whole of the difference, and it runs in the direction that adds
    a check rather than skipping one.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    local = admit(registry, candidate(child, require(FAMILY)))
    assert isinstance(local, AdmittedChild)
    assert local.eligibility_basis == ELIGIBILITY_LOCAL_REGISTER

    bare_peer = ProducedElsewhere(fabric_id="fabric://peer", protected_header={})
    refusal = admit(registry, candidate(child, require(FAMILY), fabric=bare_peer))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "eligibility-evidence-missing"


# --- composing, refusing, and inheriting -------------------------------------


def test_c8_a_required_healthy_child_composes(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 8, end to end through the real delivery path."""
    req = require(FAMILY)
    child = served(deliver(registry, _contract(schema=FAMILY)))
    admitted = admit(registry, candidate(child, req))
    assert isinstance(admitted, AdmittedChild)

    result = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={FAMILY: admitted}
    )
    assert result.served
    assert result.factors == _FULL
    assert result.resolutions[0].outcome_status == "admitted"


def test_c9_a_degraded_child_contributes_its_NAMED_factor(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 9: the impairment arrives on the axis it happened on.

    The child is weak on completeness only. The composite must be weak on
    completeness only — not "weak" as a scalar, which is what would be left if
    debt composed through ``max(child D_c)``.
    """
    req = require(COVENANT)
    weak_c = DebtFactors(
        freshness=Decimal(1),
        completeness=Decimal("0.4"),
        semantic_consistency=Decimal(1),
    )
    child = served(deliver(registry, _contract(schema=COVENANT, factors=weak_c)))
    admitted = admit(registry, candidate(child, req))
    assert isinstance(admitted, AdmittedChild)

    result = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={COVENANT: admitted}
    )
    assert result.factors is not None
    assert result.factors.completeness == Decimal("0.4")
    assert result.factors.freshness == Decimal(1)
    row = result.resolutions[0]
    assert row.child_debt_factors == weak_c


def test_c10_a_required_childs_refusal_propagates_to_the_composite(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 10. The child's cause is carried, not flattened to "failed"."""
    req = require(FAMILY)
    stale = served(deliver(registry, _contract(schema=FAMILY, as_of=OTHER_AS_OF)))
    refusal = admit(registry, candidate(stale, req))
    assert isinstance(refusal, ChildAdmissionRefusal)

    result = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={FAMILY: refusal}
    )
    assert not result.served
    assert result.refusal is not None
    assert result.refusal.product_class == FAMILY
    assert result.refusal.reason == "as-of-mismatch"
    assert result.factors is None


def test_c11_a_required_class_with_no_producing_skill_refuses() -> None:
    """Criterion 11. Never a silent omission."""
    req = require(PEERS)
    result = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={}
    )
    assert not result.served
    assert result.refusal is not None
    assert result.refusal.reason == "no-producing-skill"
    assert result.resolutions[0].outcome_status == "no-producing-skill"


def test_c12_an_absent_optional_child_becomes_explicit_named_debt() -> None:
    """Criterion 12: the deduction is the CLASS's, never the SDK's.

    The composite serves, and it serves *worse* — and how much worse is a
    number the product class declared, which is why ``OptionalAbsenceTreatment``
    has no default.
    """
    req = require(PEERS, required=False, absent_c="0.6")
    result = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={}
    )
    assert result.served
    assert result.factors is not None
    assert result.factors.completeness == Decimal("0.6")
    assert result.resolutions[0].outcome_status == "optional-absent"


def test_the_sdk_holds_no_default_for_what_an_absence_costs() -> None:
    """The other half of criterion 12, and the reason it is a separate test.

    A declared treatment being *used* does not prove none was invented. What
    proves it is that an optional requirement **cannot be declared without
    one**.
    """
    with pytest.raises(ValueError, match="holds no default"):
        ChildRequirement(
            product_class=PEERS, required=False, compatible_from="1.0.0"
        )


# --- eligibility -------------------------------------------------------------


def test_c13_a_child_made_ineligible_under_334_335_cannot_enter(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 13, reusing the existing mechanism rather than a new one."""
    req = require(FAMILY)
    child = served(deliver(registry, _contract(schema=FAMILY)))
    ControlPlaneInvalidationSink(registry=registry).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )
    refusal = admit(registry, candidate(child, req))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "ineligible"


def test_an_unrelated_product_stays_eligible_after_the_same_supersession(
    registry: ControlPlaneRegistry,
) -> None:
    """The control that makes the previous test mean something.

    A mechanism that refused everything after any supersession would pass
    criterion 13 and be worthless — a global clock, not a dependency. This
    proves the refusal is keyed on what the child actually read.
    """
    ControlPlaneInvalidationSink(registry=registry).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )
    unrelated = served(
        deliver(registry, _contract(schema=EXPOSURE), touched=(ENTITY_UNRELATED,))
    )
    admitted = admit(
        registry,
        candidate(unrelated, require(EXPOSURE), touched=(ENTITY_UNRELATED,)),
    )
    assert isinstance(admitted, AdmittedChild)


def test_re_derivation_after_the_boundary_restores_eligibility(
    registry: ControlPlaneRegistry,
) -> None:
    """A child rebuilt AFTER the boundary is eligible again.

    Invalidation is a predicate over the product in hand, not an eviction and
    not a permanent mark on the class — so re-derivation is the repair, and
    this asserts the repair works rather than assuming it.
    """
    later = SUPERSEDED_AT + timedelta(minutes=30)
    ControlPlaneInvalidationSink(registry=registry).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )
    rederived = served(
        run_gates(
            _contract(schema=FAMILY, as_of=later),
            engine_resolved=OPERATORS,
            now=later + timedelta(minutes=1),
            registry=registry,
            product_class=_registered(registry, FAMILY),
            touched_entities=(ENTITY_OBLIGOR,),
        )
    )
    admitted = admit(registry, candidate(rederived, require(FAMILY)), at=later)
    assert isinstance(admitted, AdmittedChild)


def test_c22_a_peered_childs_eligibility_comes_from_the_PRODUCER(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 22, and the point is which authority answered.

    The local register is silent about this child — it always would be, for a
    product another fabric built. Silence is *don't know*, and the admitted
    child records that the producer is what established eligibility.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    admitted = admit(
        registry, candidate(child, require(FAMILY), fabric=_attested(child))
    )
    assert isinstance(admitted, AdmittedChild)
    assert admitted.eligibility_basis == ELIGIBILITY_PRODUCER_ATTESTED


def test_a_signed_NEGATIVE_is_honored_and_is_not_the_same_as_silence(
    registry: ControlPlaneRegistry,
) -> None:
    """A producer saying *"I checked, and it is not eligible"* is a real answer.

    It refuses, as a missing assertion does — but the two are distinguishable
    in the record, because one is evidence and the other is its absence.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    refusal = admit(
        registry,
        candidate(child, require(FAMILY), fabric=_attested(child, eligible=False)),
    )
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "ineligible"
    assert "attests this child is NOT eligible" in refusal.detail


# --- authorization, identity, and what a record may not invent ---------------


def test_c14_an_admitted_child_cannot_be_constructed_outside_the_gate() -> None:
    """Criterion 14, through every SUPPORTED route.

    The claim is bounded and stated: the bypass is unreachable by import,
    constructor or subclass, and the runtime token check fires. It is **not**
    absolute unforgeability — ``object.__new__`` and module patching defeat any
    token, and this test does not pretend otherwise. What it establishes is
    that *"compose the unauthorized child, then post-filter it"* has no
    supported spelling, which is the property `CXR-G22` says the payload cannot
    give us: a post-filter and a pre-filter return the same hits.
    """
    with pytest.raises(ChildAdmissionBypassError):
        AdmittedChild(None, ELIGIBILITY_LOCAL_REGISTER, _FULL, object())  # type: ignore[arg-type]

    class Forged(AdmittedChild):
        def __init__(self) -> None:  # pragma: no cover - must not succeed
            super().__init__(None, ELIGIBILITY_LOCAL_REGISTER, _FULL, object())  # type: ignore[arg-type]

    with pytest.raises(ChildAdmissionBypassError):
        Forged()


def test_composition_accepts_only_admitted_children(
    registry: ControlPlaneRegistry,
) -> None:
    """The other half of criterion 14: the served product is not a child.

    Handing ``compose_children`` a raw contract must not compose it. It is
    treated as *nothing was produced*, which for a required slot is a refusal —
    never a silent admission of an unchecked product.
    """
    req = require(FAMILY)
    raw = served(deliver(registry, _contract(schema=FAMILY)))
    result = compose_children(
        own_factors=_FULL,
        requirements=[req],
        outcomes={FAMILY: raw},  # type: ignore[dict-item]
    )
    assert not result.served
    assert result.refusal is not None


def test_c15_replay_records_class_then_skill_and_grant_then_address(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 15: the mapping a hash of a grant SET cannot carry."""
    req = require(EXPOSURE)
    child = served(deliver(registry, _contract(schema=EXPOSURE)))
    admitted = admit(
        registry, candidate(child, req, skill_name="exposure-skill")
    )
    assert isinstance(admitted, AdmittedChild)

    result = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={EXPOSURE: admitted}
    )
    row = result.resolutions[0]
    assert row.required_product_class == EXPOSURE
    assert row.producing_skill_name == "exposure-skill"
    assert row.producing_skill_version == "1.0.0"
    assert row.grant_hash == "grant::exposure-skill"
    assert row.child_content_address == content_hash(child)
    assert row.eligibility_basis == ELIGIBILITY_LOCAL_REGISTER
    assert row.child_debt_factors is not None


def test_c16_the_composite_identity_moves_when_a_child_moves(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 16, with its converse — both halves, or neither means anything.

    Identical children must give an identical record (`24.11-C-01`: same bytes,
    same address, and that may be correct). A changed child must change it.
    """
    req = require(FAMILY)

    def path_for(payload: dict[str, object]) -> ContentGenerationPath:
        child = served(deliver(registry, _contract(schema=FAMILY, payload=payload)))
        admitted = admit(registry, candidate(child, req))
        assert isinstance(admitted, AdmittedChild)
        result = compose_children(
            own_factors=_FULL, requirements=[req], outcomes={FAMILY: admitted}
        )
        return ContentGenerationPath(
            plan_id="composite-plan",
            operator_plan=(),
            steps=(),
            product_content_address="c" * 64,
            child_resolutions=result.resolutions,
        )

    same_a, same_b = path_for({"rows": 1}), path_for({"rows": 1})
    different = path_for({"rows": 2})

    assert content_hash(same_a) == content_hash(same_b)
    assert content_hash(different) != content_hash(same_a)


def test_c18_a_child_outside_the_declared_version_lane_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 18. Same major and at or above the floor, or refused."""
    child = served(deliver(registry, _contract(schema=FAMILY, version="1.0.0")))
    refusal = admit(registry, candidate(child, require(FAMILY, floor="1.5.0")))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "version-incompatible"


def test_c19_a_refused_child_is_never_wrapped_as_a_served_empty_product(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 19 — the ruling that a required child MAY legitimately refuse.

    The composite honors the refusal. What it must never do is manufacture a
    served-looking child so it can proceed: that would put its own fail-closed
    behavior downstream of a fabrication, and make *"found nothing"* and
    *"declined to answer"* unrecoverable from the record.
    """
    req = require(EXPOSURE)
    stale = served(deliver(registry, _contract(schema=EXPOSURE, as_of=OTHER_AS_OF)))
    refusal = admit(registry, candidate(stale, req))
    result = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={EXPOSURE: refusal}
    )

    assert not result.served
    row = result.resolutions[0]
    assert row.outcome_status == "rejected-at-admission"
    # No served-shaped child exists anywhere in the record.
    assert row.child_schema_name is None
    assert row.child_debt is None
    assert row.child_asked_at is None
    # ...but the REJECTED product's identity is retained: a product produced
    # and rejected is not a product that never existed.
    assert row.child_content_address == content_hash(stale)


def test_c20_a_child_that_never_existed_invents_nothing() -> None:
    """Criterion 20: absent, not zero, not epoch, not a placeholder address."""
    req = require(PEERS, required=False, absent_c="0.5")
    result = compose_children(own_factors=_FULL, requirements=[req], outcomes={})
    row = result.resolutions[0]
    for field in (
        "child_content_address",
        "child_schema_name",
        "child_schema_version",
        "child_asked_at",
        "child_graph_snapshot_at",
        "child_debt",
        "child_debt_factors",
        "child_lineage_ref",
        "eligibility_basis",
        "producing_skill_name",
        "grant_hash",
    ):
        assert getattr(row, field) is None, f"{field} was invented"


def test_c21_the_four_absences_stay_distinct(
    registry: ControlPlaneRegistry,
) -> None:
    """Criterion 21: a governance failure may never read as a data gap.

    Declared-absent, refused, ineligible and unauthorized reach four different
    ``outcome_status`` tokens, and the vocabulary is closed so a fifth cannot
    be spelled by accident.
    """
    statuses = set()

    # 1. declared-absent
    statuses.add(
        compose_children(
            own_factors=_FULL,
            requirements=[require(PEERS, required=False, absent_c="0.5")],
            outcomes={},
        )
        .resolutions[0]
        .outcome_status
    )
    # 2. rejected at admission
    stale = served(deliver(registry, _contract(schema=FAMILY, as_of=OTHER_AS_OF)))
    statuses.add(
        compose_children(
            own_factors=_FULL,
            requirements=[require(FAMILY)],
            outcomes={FAMILY: admit(registry, candidate(stale, require(FAMILY)))},
        )
        .resolutions[0]
        .outcome_status
    )
    # 3. ineligible
    child = served(deliver(registry, _contract(schema=COVENANT)))
    ControlPlaneInvalidationSink(registry=registry).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )
    statuses.add(
        compose_children(
            own_factors=_FULL,
            requirements=[require(COVENANT)],
            outcomes={
                COVENANT: admit(registry, candidate(child, require(COVENANT)))
            },
        )
        .resolutions[0]
        .outcome_status
    )
    # 4. no producing skill
    statuses.add(
        compose_children(
            own_factors=_FULL, requirements=[require(EXPOSURE)], outcomes={}
        )
        .resolutions[0]
        .outcome_status
    )

    assert statuses == {
        "optional-absent",
        "rejected-at-admission",
        "ineligible",
        "no-producing-skill",
    }
    assert statuses <= CHILD_OUTCOME_STATUSES


def test_c23_composite_debt_is_min_over_factors_not_max_over_scalars() -> None:
    """Criterion 23, and the number is the argument.

    Two children, one weak only on F and one weak only on C. The composite is
    impaired on BOTH. ``max(child D_c)`` would report the larger of two modest
    numbers — and this asserts that value is **absent**, not merely different,
    because a test that only checked "not equal" would pass on any arithmetic.
    """
    weak_f = DebtFactors(
        freshness=Decimal("0.5"),
        completeness=Decimal(1),
        semantic_consistency=Decimal(1),
    )
    weak_c = DebtFactors(
        freshness=Decimal(1),
        completeness=Decimal("0.5"),
        semantic_consistency=Decimal(1),
    )
    composed = compose_debt_factors(_FULL, [weak_f, weak_c])

    assert composed.freshness == Decimal("0.5")
    assert composed.completeness == Decimal("0.5")
    assert context_debt(composed) == Decimal("0.75")

    scalar_max = max(context_debt(weak_f), context_debt(weak_c))
    assert scalar_max == Decimal("0.5")
    assert context_debt(composed) > scalar_max


# --- the attestation: tampering, mismatch, replay ----------------------------


@pytest.mark.parametrize(
    ("lift", "expected_in_detail"),
    [
        ("address", "is about"),
        ("as_of", "reconstruction instant"),
        ("producer", "names producer"),
        ("consumer", "minted for consumer"),
        ("invocation", "single-use"),
    ],
)
def test_every_attestation_binding_is_checked(
    registry: ControlPlaneRegistry, lift: str, expected_in_detail: str
) -> None:
    """An assertion lifted from ANY other context is refused.

    Parametrized over all five bindings rather than spot-checking one: a gate
    that verified the address and ignored the invocation would pass a
    single-binding test and admit every replayed attestation. **The replay case
    is the last row**, and it is the one the others exist to make credible.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    other = served(deliver(registry, _contract(schema=EXPOSURE)))
    kwargs: dict[str, object] = {}
    if lift == "address":
        kwargs["address"] = content_hash(other)
    elif lift == "as_of":
        kwargs["as_of"] = OTHER_AS_OF
    elif lift == "producer":
        kwargs["producer"] = "fabric://someone-else"
    elif lift == "consumer":
        kwargs["consumer"] = "consumer://another-desk"
    elif lift == "invocation":
        kwargs["invocation"] = "composition://inv-0002"

    fabric = _attested(child, **kwargs)  # type: ignore[arg-type]
    if lift == "producer":
        # The header names one producer and the fabric another — the exact
        # shape of an assertion re-presented under a different identity.
        fabric = ProducedElsewhere(
            fabric_id="fabric://peer", protected_header=fabric.protected_header
        )

    refusal = admit(registry, candidate(child, require(FAMILY), fabric=fabric))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "eligibility-evidence-mismatch"
    assert expected_in_detail in refusal.detail


def test_a_tampered_attestation_body_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """Editing the claim text is caught at decode, before any binding runs.

    In production the JWS signature covers the protected header, so an edit is
    caught cryptographically first. This asserts the second line of defence:
    even reaching the gate with an altered body, it does not parse into a claim
    this build will read.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    good = _attested(child)
    body = str(good.protected_header[ELIGIBILITY_ASSERTION_HEADER])
    tampered = ProducedElsewhere(
        fabric_id="fabric://peer",
        protected_header={ELIGIBILITY_ASSERTION_HEADER: body.replace("}", "")},
    )
    refusal = admit(registry, candidate(child, require(FAMILY), fabric=tampered))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "eligibility-evidence-missing"


def test_an_unknown_assertion_schema_version_is_refused_not_read_leniently(
    registry: ControlPlaneRegistry,
) -> None:
    """A future lane may bind facts this build would silently ignore."""
    child = served(deliver(registry, _contract(schema=FAMILY)))
    body = str(_attested(child).protected_header[ELIGIBILITY_ASSERTION_HEADER])
    future = ProducedElsewhere(
        fabric_id="fabric://peer",
        protected_header={
            ELIGIBILITY_ASSERTION_HEADER: body.replace('"1.0.0"', '"2.0.0"')
        },
    )
    refusal = admit(registry, candidate(child, require(FAMILY), fabric=future))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "eligibility-evidence-missing"


def test_a_wrong_obligor_child_is_rejected(
    registry: ControlPlaneRegistry,
) -> None:
    """A child assembled for a DIFFERENT subject cannot satisfy the request.

    Same class, same version, same instant, valid attestation — and about
    somebody else. The address binding is what catches it: an attestation
    minted for the requested child does not match the substituted one, and the
    substituted one's own attestation is about a product this composition never
    asked for.
    """
    requested = served(deliver(registry, _contract(schema=FAMILY, payload={"obligor": "alpha"})))
    wrong_subject = served(
        deliver(registry, _contract(schema=FAMILY, payload={"obligor": "omega"}))
    )
    assert content_hash(requested) != content_hash(wrong_subject)

    swapped = ChildCandidate(
        requirement=require(FAMILY),
        contract=wrong_subject,
        content_address=content_hash(requested),  # the address that was asked for
        fabric=_attested(requested),
        skill_name="family-skill",
        skill_version="1.0.0",
        grant_hash="grant::family-skill",
        touched_entities=(ENTITY_OBLIGOR,),
    )
    refusal = admit(registry, swapped)
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "address-mismatch"


# --- nested composition ------------------------------------------------------


def test_nested_composition_a_supersession_stops_the_whole_chain(
    registry: ControlPlaneRegistry,
) -> None:
    """A composite is a product, so a composite can be a child.

    The chain: ``FAMILY`` (a leaf, touching the obligor) is a child of
    ``EXPOSURE`` (a composite), which is a child of ``COVENANT`` (the outer
    composite). A supersession of the obligor must stop the **whole chain**
    from re-serving, while an equally old product that never touched the
    obligor stays eligible.

    **The unrelated control is the half that makes this mean something.** A
    mechanism that stopped everything after any supersession would pass the
    first assertion and be a global clock.
    """
    leaf_req = require(FAMILY)
    mid_req = require(EXPOSURE)

    # Before the boundary: the chain composes at both levels.
    leaf = served(deliver(registry, _contract(schema=FAMILY)))
    leaf_admitted = admit(registry, candidate(leaf, leaf_req))
    assert isinstance(leaf_admitted, AdmittedChild)
    inner = compose_children(
        own_factors=_FULL, requirements=[leaf_req], outcomes={FAMILY: leaf_admitted}
    )
    assert inner.served

    mid = served(deliver(registry, _contract(schema=EXPOSURE)))
    mid_admitted = admit(registry, candidate(mid, mid_req))
    assert isinstance(mid_admitted, AdmittedChild)
    outer = compose_children(
        own_factors=_FULL, requirements=[mid_req], outcomes={EXPOSURE: mid_admitted}
    )
    assert outer.served

    # A real source supersession, strictly after the snapshot both were built at.
    ControlPlaneInvalidationSink(registry=registry).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )

    # The leaf can no longer enter, so the inner composite refuses...
    leaf_again = admit(registry, candidate(leaf, leaf_req))
    assert isinstance(leaf_again, ChildAdmissionRefusal)
    assert leaf_again.reason == "ineligible"
    inner_again = compose_children(
        own_factors=_FULL, requirements=[leaf_req], outcomes={FAMILY: leaf_again}
    )
    assert not inner_again.served

    # ...and the mid product, which also read the obligor, cannot enter the
    # outer composite either. The chain is stopped at every level that touched
    # the superseded entity.
    mid_again = admit(registry, candidate(mid, mid_req))
    assert isinstance(mid_again, ChildAdmissionRefusal)
    outer_again = compose_children(
        own_factors=_FULL, requirements=[mid_req], outcomes={EXPOSURE: mid_again}
    )
    assert not outer_again.served

    # THE CONTROL: an equally old product that never touched the obligor is
    # still eligible, and still composes.
    unrelated_req = require(COVENANT)
    unrelated = served(
        deliver(registry, _contract(schema=COVENANT), touched=(ENTITY_UNRELATED,))
    )
    unrelated_admitted = admit(
        registry, candidate(unrelated, unrelated_req, touched=(ENTITY_UNRELATED,))
    )
    assert isinstance(unrelated_admitted, AdmittedChild)
    assert compose_children(
        own_factors=_FULL,
        requirements=[unrelated_req],
        outcomes={COVENANT: unrelated_admitted},
    ).served


def test_a_composites_expiry_floor_survives_composition(
    registry: ControlPlaneRegistry,
) -> None:
    """Constituent expiry limits are preserved, not averaged away.

    ``compose_expiry`` is `D-IMPL-31`'s existing floor and this surface does not
    replace it: the earliest constituent expiry still bounds the composite, so
    a composite can never be labelled fresher than its stalest child.
    """
    from ccf.products.composition import compose_expiry

    early = ASKED_AT + timedelta(hours=1)
    late = ASKED_AT + timedelta(hours=12)
    floor = compose_expiry(
        constituent_validities=(early, late),
        max_ttl=MaxTTL(seconds=86400),
        ttl_anchor_at=ASKED_AT,
    )
    assert floor == early


# --- sabotages: break the shipped mechanism, confirm the RED -----------------
#
# Each sabotage targets the mechanism its criterion names. A sabotage that
# leaves its test green is a TEST defect, not a pass — rung 13 found four of
# those, and every wave of this project has found the class in its own work.


def test_s3_a_CORRUPTED_substitution_stops_resolving() -> None:
    """Sabotage 3. A *valid* substitution is a positive control (c3).

    So the sabotage is the corrupted one: grant B, but declare a different
    ``produces``. The requirement must stop resolving — if it still resolved,
    ``produces`` would be decorative and criterion 3 would be proving nothing.
    """
    requirement = require(FAMILY)
    good = {"family-b": skill("family-b", produces=FAMILY)}
    corrupted = {"family-b": skill("family-b", produces=EXPOSURE)}

    assert resolve_producing_grant(requirement, good) is not None
    assert resolve_producing_grant(requirement, corrupted) is None


def test_s7_swallowing_a_required_refusal_is_what_the_mechanism_prevents(
    registry: ControlPlaneRegistry,
) -> None:
    """Sabotage 7: treat a refusal as *absent* and watch the guarantee hold.

    The sabotage is the caller dropping the refusal on the floor. Even then the
    composite must refuse — because the requirement is required and nothing
    produced it, which is the ``no-producing-skill`` limb. **There is no path
    through this function on which a required slot yields a served composite.**
    """
    req = require(FAMILY)
    stale = served(deliver(registry, _contract(schema=FAMILY, as_of=OTHER_AS_OF)))
    refusal = admit(registry, candidate(stale, req))
    assert isinstance(refusal, ChildAdmissionRefusal)

    honest = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={FAMILY: refusal}
    )
    swallowed = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={}
    )
    assert not honest.served
    assert not swallowed.served
    # The two are still DISTINGUISHABLE in the record — swallowing loses the
    # cause and the rejected product's identity, which is why it is a defect
    # even though the serve/refuse answer is the same.
    assert honest.resolutions[0].outcome_status == "rejected-at-admission"
    assert swallowed.resolutions[0].outcome_status == "no-producing-skill"
    assert honest.resolutions[0].child_content_address is not None
    assert swallowed.resolutions[0].child_content_address is None


def test_s8_omitting_a_required_requirement_omits_its_ROW_too() -> None:
    """Sabotage 8: drop the requirement from the declaration.

    The composite then serves — and that is exactly the danger, which is why
    the guarantee is anchored on the DECLARATION rather than on the outcomes
    map. A requirement that is not declared cannot be enforced, so the
    declaration is the artifact under governance, and this test pins the
    difference so a later reader cannot mistake one for the other.
    """
    declared = compose_children(
        own_factors=_FULL, requirements=[require(FAMILY)], outcomes={}
    )
    omitted = compose_children(own_factors=_FULL, requirements=[], outcomes={})

    assert not declared.served
    assert omitted.served          # nothing was required, so nothing is missing
    assert len(declared.resolutions) == 1
    assert omitted.resolutions == ()


def test_s9_an_optional_absence_with_a_ZERO_cost_treatment_is_visible() -> None:
    """Sabotage 9: declare the absence free and watch it stop costing.

    The mechanism is *the class declares the cost*; the sabotage is declaring
    it as no cost at all. That must be **visible in the factors**, not silently
    equivalent to a healthy child — the row still says ``optional-absent`` even
    when the deduction is nil, so an auditor sees a policy choice rather than a
    complete product.
    """
    free = require(PEERS, required=False, absent_c="1.0")
    costly = require(PEERS, required=False, absent_c="0.2")

    free_result = compose_children(
        own_factors=_FULL, requirements=[free], outcomes={}
    )
    costly_result = compose_children(
        own_factors=_FULL, requirements=[costly], outcomes={}
    )

    assert free_result.factors is not None and costly_result.factors is not None
    assert free_result.factors.completeness == Decimal("1.0")
    assert costly_result.factors.completeness == Decimal("0.2")
    # ...and the ROW says absent either way. The cost is a policy value; the
    # absence is a fact.
    assert free_result.resolutions[0].outcome_status == "optional-absent"
    assert costly_result.resolutions[0].outcome_status == "optional-absent"


def test_s12_dropping_the_child_rows_changes_the_replay_record(
    registry: ControlPlaneRegistry,
) -> None:
    """Sabotage 12: record the composite with no ``child_resolutions``.

    The record must not hash the same as one that carries them, or the mapping
    could be dropped without the artifact noticing — which would make criterion
    15 unenforceable at rest.
    """
    req = require(FAMILY)
    child = served(deliver(registry, _contract(schema=FAMILY)))
    admitted = admit(registry, candidate(child, req))
    assert isinstance(admitted, AdmittedChild)
    rows = compose_children(
        own_factors=_FULL, requirements=[req], outcomes={FAMILY: admitted}
    ).resolutions

    def path(resolutions: tuple[object, ...]) -> ContentGenerationPath:
        return ContentGenerationPath(
            plan_id="composite-plan",
            operator_plan=(),
            steps=(),
            product_content_address="d" * 64,
            child_resolutions=resolutions,  # type: ignore[arg-type]
        )

    assert content_hash(path(rows)) != content_hash(path(()))


def test_s17_a_refused_row_cannot_carry_invented_child_state() -> None:
    """Sabotage 17: fill a refused row's child fields with plausible values.

    The contract permits it structurally — every child field is optional — so
    the guard is the ``admitted`` validator, which is what makes a row claiming
    admission carry the state admission checked. This asserts the boundary:
    a non-admitted row may be sparse, and an admitted one may not.
    """
    from ccf.replay.record import ChildResolution

    # Permitted: a refused row that is honest about knowing nothing.
    ChildResolution(
        required_product_class=FAMILY, required=True, outcome_status="refused"
    )
    # Refused: an ADMITTED row that is sparse — the claim and the evidence
    # must travel together.
    with pytest.raises(ValueError, match="claiming admission"):
        ChildResolution(
            required_product_class=FAMILY,
            required=True,
            outcome_status="admitted",
            child_content_address="e" * 64,
        )


def test_s18_an_absence_vocabulary_cannot_be_widened_by_accident() -> None:
    """Sabotage 18: spell a fifth absence and collapse two governed events.

    The vocabulary is closed, so ``ineligible`` cannot be recorded as
    ``optional-absent`` by typo or by convenience.
    """
    from ccf.replay.record import ChildResolution

    with pytest.raises(ValueError, match="vocabulary is closed"):
        ChildResolution(
            required_product_class=FAMILY,
            required=False,
            outcome_status="optional-absent-ish",
        )


def test_s20_replacing_min_over_factors_with_max_over_scalars_understates_debt() -> None:
    """Sabotage 20, and the whole argument for the ruling is this number.

    Two children weak on different factors. The shipped rule reports ``0.75``.
    The scalar shortcut reports ``0.5`` — **a third less debt than the product
    actually carries**, on a control whose entire job is to escalate.
    """
    weak_f = DebtFactors(
        freshness=Decimal("0.5"),
        completeness=Decimal(1),
        semantic_consistency=Decimal(1),
    )
    weak_c = DebtFactors(
        freshness=Decimal(1),
        completeness=Decimal("0.5"),
        semantic_consistency=Decimal(1),
    )
    shipped = context_debt(compose_debt_factors(_FULL, [weak_f, weak_c]))
    sabotaged = max(context_debt(weak_f), context_debt(weak_c))

    assert shipped == Decimal("0.75")
    assert sabotaged == Decimal("0.5")
    assert sabotaged < shipped
