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
from pydantic import ValidationError

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
    CHILD_REFUSAL_REASONS,
    ELIGIBILITY_LOCAL_REGISTER,
    ELIGIBILITY_PRODUCER_ATTESTED,
    AdmittedChild,
    AmbiguousProducerError,
    ChildAdmissionBypassError,
    ChildAdmissionRefusal,
    ChildCandidate,
    CompositeAdmissionGate,
    CompositionOutcome,
    EligibilityEvidencePolicy,
    LocalFabricAttestor,
    LocalProvenance,
    ProvenanceForgeryError,
    VerifiedPeerProvenance,
    _REASON_TO_STATUS,
    compose_children,
    eligibility_evidence_policy_key,
    invocation_from_dispatch,
    resolve_producing_grant,
)
from ccf.products.composition import ConstituentValidityFloors
from ccf.products.contract import (
    NO_VALIDITY_FLOORS,
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


#: The boot-bound authority a deployment obtains by having booted. Tests mint
#: local provenance through it exactly as the composition root would — there
#: is no other supported way to assert "this fabric produced it".
ATTESTOR = LocalFabricAttestor(attestor_id="fabric://test-boot")


def candidate(
    contract: ContextProductContract,
    requirement: ChildRequirement,
    *,
    provenance: object | None = None,
    skill_name: str = "family-skill",
    touched: tuple[str, ...] = (ENTITY_OBLIGOR,),
    address: str | None = None,
) -> ChildCandidate:
    return ChildCandidate(
        requirement=requirement,
        contract=contract,
        content_address=address or content_hash(contract),
        provenance=provenance or ATTESTOR.attest(touched_entities=touched),
        invocation=invocation_from_dispatch(
            skill(skill_name, produces=requirement.product_class),
            grant_hash=f"grant::{skill_name}",
        ),
    )


def gate(registry: ControlPlaneRegistry) -> CompositeAdmissionGate:
    return CompositeAdmissionGate(
        tenant_id=TENANT, consumer_scope=CONSUMER_SCOPE, registry=registry
    )


def admit(
    registry: ControlPlaneRegistry,
    cand: ChildCandidate,
    *,
    at: datetime = ASKED_AT,
    admitted_at: datetime = SERVED_AT,
    invocation: str = INVOCATION,
) -> object:
    return gate(registry).admit(
        candidate=cand,
        asked_at=at,
        admitted_at=admitted_at,
        composition_invocation=invocation,
    )


def compose(
    requirements: list[ChildRequirement],
    outcomes: dict[str, object],
    *,
    own: DebtFactors | None = None,
    at: datetime = ASKED_AT,
    invocation: str = INVOCATION,
    floors: ConstituentValidityFloors = NO_VALIDITY_FLOORS,
) -> CompositionOutcome:
    """Drive the real composition with the parent context it now requires."""
    return compose_children(
        own_factors=own or _FULL,
        requirements=requirements,
        outcomes=outcomes,
        asked_at=at,
        composition_invocation=invocation,
        own_lineage=ProductLineage(
            operators_invoked=OPERATORS,
            policy_bundle_versions=(POLICY_VERSION,),
            graph_snapshot_at=at,
        ),
        max_ttl=MaxTTL(seconds=86400),
        # The DECISION instant, distinct from  (the reconstruction one).
        # R6: passing the reconstruction instant here is what collided two
        # governed answers onto one content address.
        ttl_anchor_at=SERVED_AT,
        validity_floors=floors,
    )


def declare_evidence_policy(
    registry: ControlPlaneRegistry, *, max_age: int = 3600, skew: int = 60
) -> None:
    """A tenant that admits peered children declares its evidence bound (F7)."""
    registry.register(
        eligibility_evidence_policy_key(tenant_id=TENANT),
        EligibilityEvidencePolicy(
            max_evidence_age_seconds=max_age, permitted_clock_skew_seconds=skew
        ),
    )




# --- the delivery path, and the evidence the gate now requires ---------------


def test_children_come_through_the_real_delivery_path(
    registry: ControlPlaneRegistry,
) -> None:
    """Asserted first, because every test below depends on it."""
    product = served(deliver(registry, _contract(schema=FAMILY)))
    assert product.schema_name == FAMILY
    assert content_hash(product) == content_hash(_contract(schema=FAMILY))


def test_provenance_and_invocation_cannot_be_authored_by_a_caller() -> None:
    """`D-IMPL-336` Am. 3, root cause (a): the gate's INPUTS are evidence now.

    The panel's finding was that the gate verified the child and trusted the
    context. These three constructors are the context, and a caller reaching
    any of them directly is refused — so *"produced here"*, *"a peer signed
    this"* and *"this grant produced it"* are claims only an authority can
    make.
    """
    with pytest.raises(ProvenanceForgeryError):
        LocalProvenance(attestor_id="a", touched_entities=(), token=object())
    with pytest.raises(ProvenanceForgeryError):
        VerifiedPeerProvenance(
            peer_id="p", producer="q", header={}, touched_entities=(), token=object()
        )
    from ccf.products.composite import ChildInvocation

    with pytest.raises(ProvenanceForgeryError):
        ChildInvocation(
            skill_name="s", entry_version="1.0.0", grant_hash="g", token=object()
        )


def test_a_hand_built_header_cannot_become_peer_provenance() -> None:
    """F16: the type a caller must supply is one only the peering gate mints.

    There is no constructor a deployment can reach that turns a dictionary
    into verified peer provenance — which is the whole difference between
    *"an assertion was present"* and *"an assertion was verified"*.
    """
    with pytest.raises(ProvenanceForgeryError):
        VerifiedPeerProvenance(
            peer_id="fabric://peer",
            producer="whoever",
            header={"ccf-child-eligibility": "{}"},
            touched_entities=(),
            token=object(),
        )


def test_touched_entities_has_no_absent_state(
    registry: ControlPlaneRegistry,
) -> None:
    """F3: the omission that skipped the register no longer has a spelling.

    `touched_entities` moved onto the provenance evidence and is a tuple, so
    ``()`` is the *verified* claim that the child read nothing and there is no
    way to express *"I did not look"* — the state the register cannot answer
    for and that used to be recorded as `local-register` anyway.
    """
    assert ATTESTOR.attest(touched_entities=()).touched_entities == ()
    with pytest.raises(TypeError):
        ChildCandidate(  # type: ignore[call-arg]
            requirement=require(FAMILY),
            contract=_contract(schema=FAMILY),
            content_address="x",
            provenance=ATTESTOR.attest(touched_entities=()),
        )


def test_f3_a_superseded_child_is_now_refused_whatever_the_caller_omits(
    registry: ControlPlaneRegistry,
) -> None:
    """The F3 reproduction, re-run: the admitted case is gone.

    The panel measured `touched=None` admitting a superseded child AND
    recording `local-register`. That candidate can no longer be built, and the
    honest one refuses.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    ControlPlaneInvalidationSink(registry=registry).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )
    refusal = admit(registry, candidate(child, require(FAMILY)))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "ineligible"


def test_f5_a_foreign_tenant_child_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """F5: the same bytes relabelled no longer escape this tenant's register.

    The panel measured REFUSED as tenant-alpha and ADMITTED as tenant-bravo.
    The gate now compares the child's tenant to its own first, copying the
    peering precedent, so the relabel is the thing that refuses.
    """
    foreign = _contract(schema=FAMILY).model_copy(update={"tenant_id": "tenant-other"})
    refusal = admit(registry, candidate(foreign, require(FAMILY)))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "tenant-mismatch"


def test_f9_an_address_mismatch_keeps_the_two_addresses_apart(
    registry: ControlPlaneRegistry,
) -> None:
    """F9: the disproven value is never recorded as identity."""
    child = served(deliver(registry, _contract(schema=FAMILY)))
    refusal = admit(
        registry, candidate(child, require(FAMILY), address="a-forged-address")
    )
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "address-mismatch"
    assert refusal.reported_content_address == "a-forged-address"
    assert refusal.verified_content_address is None


def test_f11_a_misspelled_reason_cannot_be_constructed() -> None:
    """F11: the collapse depended on a spelling, so the spelling is closed."""
    from ccf.products.composite import GATE_CHILD_ADMISSION

    with pytest.raises(ValidationError):
        ChildAdmissionRefusal(
            gate=GATE_CHILD_ADMISSION,
            detail="d",
            product_class="X",
            reason="unauthorised",  # type: ignore[arg-type]
        )


def test_f11_the_status_map_is_exhaustive_and_raises_on_the_unknown() -> None:
    """V2's repair: an EXHAUSTIVE check, not a subset one.

    The earlier assertion was ``statuses <= CHILD_OUTCOME_STATUSES``, which can
    never notice a reserved token nothing emits. This holds the two rosters to
    each other by equality, and asserts the fallback is gone.
    """
    from ccf.products.composite import _status_for

    assert set(_REASON_TO_STATUS) == CHILD_REFUSAL_REASONS
    with pytest.raises(ValueError, match="closed vocabulary"):
        _status_for("unauthorised")


# --- F7: evidence age, held to a DECLARED bound ------------------------------


def _peer_provenance(
    contract: ContextProductContract,
    *,
    checked_at: datetime,
    producer: str = "producer-hash",
    consumer: str = CONSUMER_SCOPE,
    invocation: str = INVOCATION,
    eligible: bool = True,
    touched: tuple[str, ...] = (ENTITY_OBLIGOR,),
) -> VerifiedPeerProvenance:
    """Mint peer provenance the way the peering seam does — through the token.

    Tests reach the private token deliberately and say so: the point of F16 is
    that DEPLOYMENT code cannot, and a test standing in for the peering gate is
    the one caller that legitimately holds its authority.
    """
    from ccf.peering.admission import PRODUCER_ASSERTION_HEADER
    from ccf.products.composite import _PEER_PROVENANCE_TOKEN

    assertion = mint_eligibility_assertion(
        child_content_address=content_hash(contract),
        requested_as_of=contract.temporal_boundary,
        producer=producer,
        consumer_scope=consumer,
        checked_at=checked_at,
        composition_invocation=invocation,
        eligible=eligible,
    )
    return VerifiedPeerProvenance(
        peer_id="peer-1",
        producer=producer,
        header={
            PRODUCER_ASSERTION_HEADER: producer,
            ELIGIBILITY_ASSERTION_HEADER: encode_eligibility_assertion(assertion),
        },
        touched_entities=touched,
        token=_PEER_PROVENANCE_TOKEN,
    )


def test_f7_a_stale_producer_check_is_refused_against_a_declared_bound(
    registry: ControlPlaneRegistry,
) -> None:
    """F7: 1970 and 2999 both admitted before. Both refuse now.

    Measured against **admission time**, not against `asked_at` — the
    distinction the ruling turns on.
    """
    declare_evidence_policy(registry, max_age=3600, skew=60)
    child = served(deliver(registry, _contract(schema=FAMILY)))

    fresh = admit(
        registry,
        candidate(child, require(FAMILY), provenance=_peer_provenance(child, checked_at=SERVED_AT)),
    )
    assert isinstance(fresh, AdmittedChild)
    assert fresh.eligibility_basis == ELIGIBILITY_PRODUCER_ATTESTED

    for label, when in [
        ("56y stale", datetime(1970, 1, 1, tzinfo=UTC)),
        ("973y future", datetime(2999, 12, 31, tzinfo=UTC)),
    ]:
        out = admit(
            registry,
            candidate(
                child, require(FAMILY), provenance=_peer_provenance(child, checked_at=when)
            ),
        )
        assert isinstance(out, ChildAdmissionRefusal), label
        assert out.reason == "eligibility-evidence-stale", label


def test_f7_a_historical_asked_at_does_NOT_make_honest_evidence_stale(
    registry: ControlPlaneRegistry,
) -> None:
    """The ruling's load-bearing half, and the one an ordering check breaks.

    A producer checks eligibility TODAY for a reconstruction request about the
    past. `checked_at` is legitimately far later than `asked_at`, and comparing
    the two would refuse every honest peered answer about history.
    """
    declare_evidence_policy(registry, max_age=3600, skew=60)
    historical = datetime(2020, 1, 1, tzinfo=UTC)
    child = served(
        run_gates(
            _contract(schema=FAMILY, as_of=historical),
            engine_resolved=OPERATORS,
            # Served at its own time, so the TTL gate is not the thing under
            # test here — the child is genuinely a historical answer.
            now=historical + timedelta(minutes=1),
            registry=registry,
            product_class=_registered(registry, FAMILY),
            touched_entities=(ENTITY_OBLIGOR,),
        )
    )
    admitted = admit(
        registry,
        candidate(
            child, require(FAMILY), provenance=_peer_provenance(child, checked_at=SERVED_AT)
        ),
        at=historical,
    )
    assert isinstance(admitted, AdmittedChild)
    assert admitted.eligibility_evidence is not None
    assert admitted.eligibility_evidence.checked_at == SERVED_AT


def test_f7_an_undeclared_bound_refuses_rather_than_defaulting(
    registry: ControlPlaneRegistry,
) -> None:
    """No hardcoded duration, no numeric default: missing config fails loudly."""
    child = served(deliver(registry, _contract(schema=FAMILY)))
    out = admit(
        registry,
        candidate(child, require(FAMILY), provenance=_peer_provenance(child, checked_at=SERVED_AT)),
    )
    assert isinstance(out, ChildAdmissionRefusal)
    # Its OWN reason, not "stale" (found by the repair's own review panel):
    # a tenant that declared no bound has a CONFIGURATION error, and telling
    # the operator their peer's evidence is stale would name the wrong party.
    assert out.reason == "eligibility-bound-undeclared"
    assert "declared no eligibility-evidence bound" in out.detail


def test_f7_the_verified_assertion_reaches_replay(
    registry: ControlPlaneRegistry,
) -> None:
    """The other half of F7: replay can name WHICH evidence authorized it."""
    declare_evidence_policy(registry)
    child = served(deliver(registry, _contract(schema=FAMILY)))
    req = require(FAMILY)
    admitted = admit(
        registry,
        candidate(child, req, provenance=_peer_provenance(child, checked_at=SERVED_AT)),
    )
    assert isinstance(admitted, AdmittedChild)
    row = compose([req], {FAMILY: admitted}).resolutions[0]
    assert row.child_eligibility_checked_at == SERVED_AT
    assert row.child_eligibility_assertion_address is not None
    assert row.producing_fabric == "peer-1"


# --- composition: re-binding, the four laws, and the F1 ruling ---------------


def _admitted(
    registry: ControlPlaneRegistry, schema: str, req: ChildRequirement, **kw: object
) -> AdmittedChild:
    child = served(deliver(registry, _contract(schema=schema, **kw)))  # type: ignore[arg-type]
    out = admit(registry, candidate(child, req))
    assert isinstance(out, AdmittedChild), out
    return out


def test_f2_a_child_cannot_satisfy_a_slot_it_was_not_admitted_against(
    registry: ControlPlaneRegistry,
) -> None:
    """F2: the panel filed a class-A child under key B and it composed."""
    adm = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(EXPOSURE)], {EXPOSURE: adm})
    assert not out.served
    assert out.refusal is not None
    assert out.refusal.reason == "requirement-mismatch"


def test_f2_a_looser_admission_cannot_satisfy_a_tighter_slot(
    registry: ControlPlaneRegistry,
) -> None:
    """The version half of F2: admitted at 1.0.0, composed against 1.2.0."""
    adm = _admitted(registry, FAMILY, require(FAMILY, floor="1.0.0"))
    out = compose([require(FAMILY, floor="1.2.0")], {FAMILY: adm})
    assert not out.served
    assert out.refusal is not None


def test_f15_children_from_two_instants_do_not_combine(
    registry: ControlPlaneRegistry,
) -> None:
    """F15: the one-`as_of` invariant is now checkable where it is asserted."""
    adm = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(FAMILY)], {FAMILY: adm}, at=OTHER_AS_OF)
    assert not out.served
    assert out.refusal is not None
    assert out.refusal.reason == "as-of-mismatch"


def test_f15_a_child_from_another_invocation_does_not_combine(
    registry: ControlPlaneRegistry,
) -> None:
    """F8/F15: the binding is to ONE invocation, and it survives composition."""
    adm = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(FAMILY)], {FAMILY: adm}, invocation="composition://other")
    assert not out.served
    assert out.refusal is not None


def test_f17_an_undeclared_outcome_key_is_refused_not_dropped(
    registry: ControlPlaneRegistry,
) -> None:
    """F17: a child under a key naming no slot vanished from record and debt."""
    adm = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(FAMILY)], {FAMILY: adm, EXPOSURE: adm})
    assert not out.served
    assert out.refusal is not None
    assert out.refusal.reason == "undeclared-outcome"


def test_f13_an_unadmitted_object_is_refused_for_an_OPTIONAL_slot_too(
    registry: ControlPlaneRegistry,
) -> None:
    """F13: the old code read a raw contract as *nothing was produced*.

    Under an optional slot that composed it at the declared absence cost. The
    panel's own test covered only the required slot; this covers the one that
    was broken.
    """
    raw = served(deliver(registry, _contract(schema=PEERS)))
    out = compose([require(PEERS, required=False, absent_c="0.3")], {PEERS: raw})
    assert not out.served
    assert out.refusal is not None
    assert out.refusal.reason == "unsupported-outcome"


def test_f12_duplicate_requirements_are_refused_at_execution(
    registry: ControlPlaneRegistry,
) -> None:
    """F12: registration enforced coherence; execution did not."""
    req = require(FAMILY)
    out = compose([req, req], {})
    assert not out.served
    assert out.refusal is not None
    assert out.refusal.reason == "requirement-mismatch"


def test_f1_optional_absence_is_priced_and_optional_REFUSAL_is_not(
    registry: ControlPlaneRegistry,
) -> None:
    """F1 RULED: optional means optional ABSENCE, not optional governance.

    The panel measured a rejected optional child at ``D_c = 0`` while an
    honestly absent one cost ``0.8`` — a governance failure arithmetically
    BETTER than a data gap. Under the ruling the two are no longer comparable:
    only an honest ``no-producing-skill`` is priced, and anything invoked and
    refused refuses the composite.
    """
    req = require(PEERS, required=False, absent_c="0.2")

    absent = compose([req], {})
    assert absent.served
    assert absent.factors is not None
    assert absent.factors.completeness == Decimal("0.2")
    assert absent.resolutions[0].outcome_status == "optional-absent"

    from ccf.products.composite import GATE_CHILD_ADMISSION

    rejected = compose(
        [req],
        {
            PEERS: ChildAdmissionRefusal(
                gate=GATE_CHILD_ADMISSION,
                detail="superseded",
                product_class=PEERS,
                reason="ineligible",
                reported_content_address="a" * 64,
                verified_content_address="a" * 64,
            )
        },
    )
    assert not rejected.served
    assert rejected.factors is None
    assert rejected.resolutions[0].outcome_status == "ineligible"
    # ...and the rejected product's identity is retained, per Amendment 2.
    assert rejected.resolutions[0].child_content_address == "a" * 64


def test_f14_the_expiry_floor_is_a_property_of_THIS_path(
    registry: ControlPlaneRegistry,
) -> None:
    """V3's repair, and F14's proof.

    The earlier test called `compose_expiry` with two literal datetimes and
    would have stayed green if `compose_children` were deleted. This drives the
    real composition and asserts the composite is no fresher than its stalest
    admitted child.
    """
    early = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(FAMILY)], {FAMILY: early})
    assert out.served
    assert out.expires_at is not None
    assert out.expires_at <= early.contract.expires_at
    # ...and the lineage is the N-way union, not the parent's alone.
    assert out.lineage is not None
    assert OPERATORS <= out.lineage.operators_invoked


def test_f14_all_four_laws_are_present_on_a_served_composition(
    registry: ControlPlaneRegistry,
) -> None:
    """The outcome carries every ruled law, not one.

    A caller using the API as designed could not previously compute the floor
    at all; `CompositionOutcome` carried only ``factors``.
    """
    adm = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(FAMILY)], {FAMILY: adm})
    assert out.factors is not None  # D-IMPL-104
    assert out.lineage is not None  # D-IMPL-31 union
    assert out.expires_at is not None  # D-IMPL-31 floor
    assert out.refusal is None  # D-IMPL-31 mixing refusal did not fire


# --- V1's repair: the four absences, with a REAL unauthorized outcome --------


def test_v1_the_four_absences_stay_distinct_INCLUDING_unauthorized(
    registry: ControlPlaneRegistry,
) -> None:
    """V1's repair. The earlier test named `unauthorized` and asserted
    `no-producing-skill`, so design criterion 21 was never discharged.

    All four governed absences are produced here and asserted by **equality**,
    and `unauthorized` is among them — reached the way a real deployment
    reaches it, by translating a child door's own authorization refusal.
    """
    from ccf.products.composite import GATE_CHILD_ADMISSION

    def refusal(reason: str) -> ChildAdmissionRefusal:
        return ChildAdmissionRefusal(
            gate=GATE_CHILD_ADMISSION,
            detail=f"child door returned {reason}",
            product_class=FAMILY,
            reason=reason,  # type: ignore[arg-type]
        )

    statuses = {
        # 1. declared absence — the ONLY priced one
        compose([require(PEERS, required=False, absent_c="0.5")], {})
        .resolutions[0]
        .outcome_status,
        # 2. a governed refusal at admission
        compose([require(FAMILY)], {FAMILY: refusal("as-of-mismatch")})
        .resolutions[0]
        .outcome_status,
        # 3. an eligibility failure
        compose([require(FAMILY)], {FAMILY: refusal("ineligible")})
        .resolutions[0]
        .outcome_status,
        # 4. an AUTHORIZATION failure — the one the old test never produced
        compose([require(FAMILY)], {FAMILY: refusal("unauthorized")})
        .resolutions[0]
        .outcome_status,
        # 5. nothing produced it at all
        compose([require(EXPOSURE)], {}).resolutions[0].outcome_status,
    }
    assert statuses == {
        "optional-absent",
        "rejected-at-admission",
        "ineligible",
        "unauthorized",
        "no-producing-skill",
    }


def test_v1_an_eligibility_evidence_failure_is_an_ELIGIBILITY_failure(
    registry: ControlPlaneRegistry,
) -> None:
    """The panel found all three evidence failures folded into a generic
    rejection, so an auditor counting eligibility failures under-counted."""
    from ccf.products.composite import _status_for

    for reason in (
        "eligibility-evidence-missing",
        "eligibility-evidence-mismatch",
        "eligibility-evidence-stale",
    ):
        assert _status_for(reason) == "ineligible"


# --- positive controls -------------------------------------------------------


def test_positive_control_a_healthy_composition_serves(
    registry: ControlPlaneRegistry,
) -> None:
    """The control that makes every refusal above mean something.

    Without it, a `compose_children` that refused unconditionally would pass
    each negative test in this module.
    """
    reqs = [require(FAMILY), require(EXPOSURE), require(COVENANT)]
    outcomes = {r.product_class: _admitted(registry, r.product_class, r) for r in reqs}
    out = compose(reqs, outcomes)

    assert out.served
    assert out.refusal is None
    assert [r.required_product_class for r in out.resolutions] == [
        FAMILY,
        EXPOSURE,
        COVENANT,
    ]
    assert all(r.outcome_status == "admitted" for r in out.resolutions)
    assert all(r.child_asked_at == ASKED_AT for r in out.resolutions)


def test_positive_control_producer_substitution_leaves_the_contract_alone(
    registry: ControlPlaneRegistry,
) -> None:
    """A valid substitution SUCCEEDS — it is a control, never a sabotage.

    Two grants producing one class, used one at a time. The requirement, the
    admission path and the composed contract are unchanged; only the recorded
    producing identity differs, which is the whole claim of the pattern.
    """
    req = require(FAMILY)
    child = served(deliver(registry, _contract(schema=FAMILY)))

    rows = []
    for name in ("family-a", "family-b"):
        out = admit(registry, candidate(child, req, skill_name=name))
        assert isinstance(out, AdmittedChild)
        composed = compose([req], {FAMILY: out})
        assert composed.served
        rows.append(composed.resolutions[0])

    assert rows[0].producing_skill_name != rows[1].producing_skill_name
    assert rows[0].grant_hash != rows[1].grant_hash
    # everything governed is identical
    assert rows[0].child_content_address == rows[1].child_content_address
    assert rows[0].required_product_class == rows[1].required_product_class
    assert rows[0].child_debt_factors == rows[1].child_debt_factors


def test_ambiguous_producers_still_refuse_with_no_tie_breaker() -> None:
    """Unchanged by the remediation, and re-asserted because F11 touched it."""
    bound = {
        "a": skill("a", produces=FAMILY),
        "b": skill("b", produces=FAMILY),
    }
    with pytest.raises(AmbiguousProducerError):
        resolve_producing_grant(require(FAMILY), bound)


def test_a_skill_without_produces_still_cannot_satisfy_a_requirement() -> None:
    assert resolve_producing_grant(require(FAMILY), {"s": skill("s")}) is None


# --- findings the panel raised against the REPAIR itself ---------------------


def test_the_authenticated_header_cannot_be_mutated_after_admission() -> None:
    """Raised against the repair, CRITICAL, and confirmed by execution.

    `AdmittedProduct` stored the verified header by reference, so a holder
    could swap `ccf-child-eligibility` for an assertion the peering gate never
    checked — after verification. "Authenticated header" would then have meant
    *"a header that was authenticated at some point, and is whatever it is
    now"*.
    """
    from ccf.peering.admission import _ADMISSION_TOKEN, AdmittedProduct

    header = {"ccf-child-eligibility": "the-verified-one"}
    admitted = AdmittedProduct(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        _ADMISSION_TOKEN,
        protected_header=header,
        content_address="addr",
    )
    # the source mapping moving does not move the admitted one
    header["ccf-child-eligibility"] = "swapped-after-verification"
    assert admitted.protected_header is not None
    assert admitted.protected_header["ccf-child-eligibility"] == "the-verified-one"
    with pytest.raises(TypeError):
        admitted.protected_header["ccf-child-eligibility"] = "swapped"  # type: ignore[index]


def test_an_undeclared_evidence_bound_is_not_reported_as_stale_evidence(
    registry: ControlPlaneRegistry,
) -> None:
    """Raised against the repair. Two different facts, two different remedies.

    Conflating them told an operator their peer's attestation was stale when
    the truth was that this tenant never said how stale is too stale — and the
    two are fixed by different people.
    """
    from ccf.products.composite import _status_for

    assert _status_for("eligibility-bound-undeclared") == "unauthorized"
    assert _status_for("eligibility-evidence-stale") == "ineligible"


def test_an_undeclared_outcome_key_does_not_wipe_the_audit_trace(
    registry: ControlPlaneRegistry,
) -> None:
    """Raised against the repair. Refusing is right; erasing is not.

    The first version returned immediately with `resolutions=()`, losing the
    disposition of every validly produced child for that decision — more
    evidence destroyed than the defect being refused.
    """
    adm = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(FAMILY)], {FAMILY: adm, EXPOSURE: adm})

    assert not out.served
    assert out.refusal is not None
    assert out.refusal.reason == "undeclared-outcome"
    # ...and the declared requirement still has its row.
    assert [r.required_product_class for r in out.resolutions] == [FAMILY]
    assert out.resolutions[0].outcome_status == "admitted"


def test_a_rebinding_failure_keeps_the_VERIFIED_identity(
    registry: ControlPlaneRegistry,
) -> None:
    """Raised against the repair. Admission established the identity.

    Only an address the gate DISPROVED is withheld from the verified field; a
    child rejected for being offered to the wrong slot has a perfectly good
    one, and dropping it loses the rejected product's identity that
    Amendment 2 requires be retained.
    """
    adm = _admitted(registry, FAMILY, require(FAMILY))
    out = compose([require(EXPOSURE)], {EXPOSURE: adm})

    assert not out.served
    row = out.resolutions[0]
    assert row.child_content_address == adm.verified_content_address
    assert row.producing_fabric == "fabric://test-boot"


def test_r6_the_ttl_anchor_is_the_DECISION_instant_not_the_request_one(
    registry: ControlPlaneRegistry,
) -> None:
    """`R6`: the composite path silently reverted `D-IMPL-308`.

    It anchored expiry at `asked_at` while the non-composite branch anchored
    at `decided_at`, so declaring a child requirement SHORTENED a product's
    window by the decision lag — and the measured consequence was two distinct
    governed answers landing on one content address.

    Asserted by moving only the anchor: the composed expiry must follow it.
    """
    req = require(FAMILY)
    adm = _admitted(registry, FAMILY, req)

    early = compose_children(
        own_factors=_FULL,
        requirements=[req],
        outcomes={FAMILY: adm},
        asked_at=ASKED_AT,
        composition_invocation=INVOCATION,
        own_lineage=ProductLineage(
            operators_invoked=OPERATORS,
            policy_bundle_versions=(POLICY_VERSION,),
            graph_snapshot_at=ASKED_AT,
        ),
        max_ttl=MaxTTL(seconds=60),
        ttl_anchor_at=ASKED_AT,
        validity_floors=NO_VALIDITY_FLOORS,
    )
    later = compose_children(
        own_factors=_FULL,
        requirements=[req],
        outcomes={FAMILY: adm},
        asked_at=ASKED_AT,
        composition_invocation=INVOCATION,
        own_lineage=ProductLineage(
            operators_invoked=OPERATORS,
            policy_bundle_versions=(POLICY_VERSION,),
            graph_snapshot_at=ASKED_AT,
        ),
        max_ttl=MaxTTL(seconds=60),
        ttl_anchor_at=ASKED_AT + timedelta(minutes=5),
        validity_floors=NO_VALIDITY_FLOORS,
    )
    assert early.served and later.served
    assert early.expires_at is not None and later.expires_at is not None
    # The anchor moved by five minutes and the ceiling followed it. Before the
    # fix the function could not see the decision instant at all.
    assert later.expires_at > early.expires_at
