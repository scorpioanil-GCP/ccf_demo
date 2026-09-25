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

import inspect
import pathlib
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
    ELIGIBILITY_PROVIDER_CONTROLS,
    ELIGIBILITY_PRODUCER_ATTESTED,
    AdmittedChild,
    AmbiguousProducerError,
    ChildAdmissionBypassError,
    ChildAdmissionRefusal,
    ChildCandidate,
    ChildInvocation,
    CompositeAdmissionGate,
    CompositionOutcome,
    ProvenanceForgeryError,
    ResolvedProducer,
    _REASON_TO_STATUS,
    compose_children,
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
from ccf.artifacts.file_store import FileArtifactStore
from ccf.replay.record import (
    CHILD_OUTCOME_STATUSES,
    ContentGenerationPath,
    ContextFabricSnapshot,
    DecisionReplayRecord,
    ModelVersionRecord,
    PerspectiveConditioning,
    PolicyBindingsSnapshot,
)
from ccf.agents.definitions import AgentDefinition
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.skills.catalog import (
    NO_PRODUCT_CLASS,
    LocalCallableBinding,
    McpBinding,
    PeeringBinding,
    SkillArgumentSchema,
    SkillCatalog,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.skills.dispatch import (
    McpInvocation,
    PeeringInvocation,
    SkillInvocation,
)
from ccf.skills.grants import BoundSkillView, GrantLedger, SkillGrant
from tests.composition import register_at_composition, register_typed_at_composition
from tests.composition import composition_register
from ccf.controlplane.invalidation import register_key
from tests.composition import register_skill_entry
from tests.skills.authority import grant_capability, revoke_capability

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

MAX_TTL_KEY = "tenant-fixture/composite/max-ttl"
OPERATORS = frozenset({"Resolve", "Traversal"})
POLICY_VERSION = "fixture-policy-v1"

_FULL = DebtFactors(
    freshness=Decimal(1), completeness=Decimal(1), semantic_consistency=Decimal(1)
)


# --- the estate: a registry, product classes, and real delivery --------------


@pytest.fixture()
def registry() -> ControlPlaneRegistry:
    """A bare Control Plane, and that is the Amendment 5 story in one fixture.

    Between `O1` and Amendment 5 this fixture booted a whole fabric and carried
    an artifact store, because a child could not be admitted without an
    attestor minted at boot and a persisted record to attest over. **That layer
    is gone.** A child is admitted on the strength of the grant that authorized
    its skill and the dispatch that ran it, so a unit test of composition needs
    a Control Plane and nothing else.
    """
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
        version = register_at_composition(registry, key, MaxTTL(seconds=86400))
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


_BINDING_FOR = {
    "local_callable": lambda n: LocalCallableBinding(callable_ref=f"ref::{n}"),
    "mcp": lambda n: McpBinding(server="fixture-server", resource="fixture-resource"),
    "peering": lambda n: PeeringBinding(endpoint="fixture-endpoint"),
}


def skill(
    name: str,
    *,
    produces: str = NO_PRODUCT_CLASS,
    skill_type: str = "local_callable",
) -> SkillCatalogEntry:
    return SkillCatalogEntry(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name=name,
        tenant=TENANT,
        skill_type=skill_type,
        description=f"{name} skill",
        argument_schema=SkillArgumentSchema(properties={}, required=frozenset()),
        binding=_BINDING_FOR[skill_type](name),
        requirements=SkillRequirements(
            required_scopes=frozenset(), required_context_products=frozenset()
        ),
        produces=produces,
    )


#: The agent whose grants these tests resolve against. Every field is a
#: test-side value: the SDK holds none of them (`D-IMPL-38`).
_AGENT = AgentDefinition(
    schema_version="1.0.0",
    artifact_version="1.0.0",
    name="composite-assembler",
    tenant=TENANT,
    archetypes=("context_assembly",),
    context_contract={
        "consumes": [{"product_class": FAMILY, "schema_version": "1.0.0"}]
    },
    perspective={"role": "assembler", "selection_params": {}},
    policy_regime={"ref": f"ccf-artifact://{TENANT}/policy-bundle/composite-auto@1.0.0"},
    halflife_debt_profile={
        "ref": f"ccf-artifact://{TENANT}/debt-profile/composite@1.0.0"
    },
    instruction_bindings=(),
)
_AGENT_HASH = content_hash(_AGENT)


def _ledger(registry: ControlPlaneRegistry) -> GrantLedger:
    """One real ledger per registry, with its policy regime registered once."""
    cache: dict[str, GrantLedger] = registry.__dict__.setdefault(
        "_composite_test_ledger", {}
    )
    if "ledger" not in cache:
        regime_class = declared_artifact_class("policy-bundle")
        register_typed_at_composition(registry, f"{TENANT}/policy-bundle/composite-auto",
            parse_artifact(
                {
                    "class_id": "policy-bundle",
                    "semver": "1.0.0",
                    "declaration": {
                        "regime": "composite-auto",
                        # No approval gate: what these tests are about is WHICH
                        # grant authorized a producer, not `D-IMPL-29`'s HITL
                        # path, which `tests/skills/test_grants.py` owns.
                        "skill_governance": {
                            "grant_requires_approval": False,
                            "permitted_scopes": [],
                        },
                    },
                },
                regime_class,
            ),
            regime_class,
        )
        cache["ledger"] = GrantLedger(
            control_plane=registry,
            catalog=SkillCatalog(registry),
            # Omitted deliberately: it defaults to the registry's own log, and
            # passing a second one is a SplitAuditPlaneError (INV-CH7-71).
            sink=None,
            clock=lambda: SERVED_AT,
        )
    return cache["ledger"]


def granted(
    registry: ControlPlaneRegistry,
    *producers: tuple[str, str],
    skill_type: str = "local_callable",
) -> BoundSkillView:
    """Put ``producers`` in force through the REAL grant machinery (**O2**).

    Registers each entry in a real :class:`~ccf.skills.catalog.SkillCatalog`
    and asks a real :class:`~ccf.skills.grants.GrantLedger` for each grant,
    then hands back the ledger's own
    :class:`~ccf.skills.grants.BoundSkillView`.

    **This is the point of O2 and it is why the helper exists at all.** The
    previous shape built a dict of entries and paired each with a
    ``f"grant::{name}"`` string, so every assertion about a recorded grant
    identity was an assertion about that f-string. Nothing here is authored:
    the grant hash a row carries is ``content_hash`` of a grant a ledger
    actually made effective, and revoking it stops the resolution.
    """
    ledger = _ledger(registry)
    for name, produces in producers:
        register_skill_entry(
            ledger._catalog,
            registry,
            skill(name, produces=produces, skill_type=skill_type)
        )
        outcome = ledger.request(
            grant_capability(_AGENT),
            SkillGrant(
                schema_version="1.0.0",
                artifact_version="1.0.0",
                name=f"grant-{name}",
                tenant=TENANT,
                agent_definition_hash=_AGENT_HASH,
                skill_name=name,
                skill_version="1.0.0",
            ),
            definition=_AGENT,
        )
        assert isinstance(outcome, str), outcome
    return ledger.bound_view(_AGENT_HASH)


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


#: The entry `skill_type` each acquisition kind must be granted against.
#: Held here because `invocation_from_dispatch` now refuses a mismatch — the
#: close panel showed a `local_callable` entry paired with an `McpInvocation`
#: recorded a remote product as locally produced.
_SKILL_TYPE_FOR = {"local": "local_callable", "mcp": "mcp", "peering": "peering"}


def _producer(
    registry: ControlPlaneRegistry,
    name: str,
    produces: str,
    *,
    skill_type: str = "local_callable",
) -> ResolvedProducer:
    """Resolve ``name`` through a real ledger, once per (registry, name).

    Cached on the registry object rather than in a module dict keyed on
    ``id(registry)`` — the same correction `_registered` records, for the same
    reason: CPython reuses an id and a later test inherits a cache entry naming
    a grant its own ledger never made.
    """
    cache: dict[str, ResolvedProducer] = registry.__dict__.setdefault(
        "_composite_test_producers", {}
    )
    if name not in cache:
        view = granted(registry, (name, produces), skill_type=skill_type)
        resolved = resolve_producing_grant(require(produces), view)
        assert resolved is not None, f"{name} was not put in force"
        cache[name] = resolved
    return cache[name]


def dispatched(skill_name: str = "family-skill", *, kind: str = "local") -> object:
    """A dispatch result, of the type the acquisition actually produces.

    `D-IMPL-336` **Amendment 5** reads the provider relationship off this
    object's **type** rather than off a caller's label, so a unit test that
    wants the MCP or peered branch builds the matching result. The proof that
    `dispatch_skill` really produces these — over a real callable, through a
    real door — is `tests/products/test_composite_integration.py`.
    """
    if kind == "mcp":
        return McpInvocation(
            skill_name=skill_name,
            skill_type="mcp",
            server="fixture-server",
            resource="fixture-resource",
            contents="{}",
            arguments={},
        )
    if kind == "peering":
        return PeeringInvocation(
            skill_name=skill_name,
            skill_type="peering",
            endpoint="fixture-endpoint",
            products=(),
            arguments={},
        )
    return SkillInvocation(
        skill_name=skill_name, skill_type="local_callable", output={}
    )


def candidate(
    registry: ControlPlaneRegistry,
    contract: ContextProductContract,
    requirement: ChildRequirement,
    *,
    skill_name: str = "family-skill",
    touched: tuple[str, ...] | None = (ENTITY_OBLIGOR,),
    address: str | None = None,
    kind: str = "local",
    admission: object | None = None,
) -> ChildCandidate:
    """One candidate, with evidence that a grant AND a dispatch both happened.

    **Amendment 5 removed the `provenance` argument.** There is no attestor and
    no peer envelope to hand in: what the gate reads is the invocation — the
    ledger's grant, the dispatch result's type — and, for a peered child
    alone, the peering gate's own `AdmittedProduct`.
    """
    result = dispatched(skill_name, kind=kind)
    return ChildCandidate(
        requirement=requirement,
        contract=contract,
        content_address=address or content_hash(contract),
        # `O2` + Amendment 5: the grant comes from a REAL in-force ledger
        # entry and the acquisition kind from the dispatch result, so neither
        # half is a string this file typed.
        invocation=invocation_from_dispatch(
            _producer(
                registry,
                skill_name,
                requirement.product_class,
                skill_type=_SKILL_TYPE_FOR[kind],
            ),
            result,
            touched_entities=touched if kind == "local" else None,
        ),
        admission=admission,  # type: ignore[arg-type]
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
        # The decision instant too, for the mixing law (`D-IMPL-341` review):
        # this fixture's decision instant IS `SERVED_AT`, so every floor
        # measurement below is exactly the one it made before the split.
        decided_at=SERVED_AT,
        validity_floors=floors,
    )


# --- the delivery path, and the evidence the gate now requires ---------------


def test_children_come_through_the_real_delivery_path(
    registry: ControlPlaneRegistry,
) -> None:
    """Asserted first, because every test below depends on it."""
    product = served(deliver(registry, _contract(schema=FAMILY)))
    assert product.schema_name == FAMILY
    assert content_hash(product) == content_hash(_contract(schema=FAMILY))


def test_the_invocation_record_cannot_be_authored_by_a_caller() -> None:
    """Amendment 3 root cause (a), as Amendment 5 leaves it.

    The panel's finding was that the gate verified the child and TRUSTED THE
    CONTEXT. Amendment 3 answered with three minted evidence types; Amendment 5
    collapsed them to **one**, because the other two were asking a second time
    whether an invocation the grant had already authorized was authorized.

    What must stay unwritable is the claim *"a grant made this skill effective
    and it actually ran"* — so this is the retired
    `test_provenance_and_invocation_cannot_be_authored_by_a_caller`, holding
    the control that survived rather than deleting it with the two that did not.
    """
    with pytest.raises(ProvenanceForgeryError):
        ChildInvocation(
            skill_name="s",
            entry_version="1.0.0",
            grant_hash="g",
            acquisition="local-dispatch",
            touched_entities=(),
            token=object(),
        )


def test_the_acquisition_kind_is_READ_from_the_dispatch_not_declared(
    registry: ControlPlaneRegistry,
) -> None:
    """Amendment 5's axis: the provider relationship, observed.

    `invocation_from_dispatch` takes no ``acquisition`` argument. It reads the
    dispatch result's type, so a caller cannot label an MCP read as a local
    production to reach the local register — which is the substitution Dave
    named: *"a local skill fetching a remote product must not relabel that
    product as locally produced to bypass its applicable checks."*
    """
    # A DISTINCT product class per kind: two in-force grants producing one
    # class is `AmbiguousProducerError`, which the SDK refuses on its own terms.
    for kind, produces, expected in (
        ("local", FAMILY, "local-dispatch"),
        ("mcp", EXPOSURE, "mcp"),
        ("peering", COVENANT, "peered"),
    ):
        producer = _producer(
            registry, f"skill-{kind}", produces, skill_type=_SKILL_TYPE_FOR[kind]
        )
        minted = invocation_from_dispatch(
            producer, dispatched(f"skill-{kind}", kind=kind)
        )
        assert minted.acquisition == expected
    assert "acquisition" not in inspect.signature(invocation_from_dispatch).parameters


def test_a_dispatch_of_ANOTHER_skill_cannot_carry_this_grants_authority(
    registry: ControlPlaneRegistry,
) -> None:
    """The pairing check Amendment 5 adds, and the reason it is needed.

    The grant and the dispatch are two records. Pairing one skill's authority
    with another skill's execution would produce a row naming a grant that
    authorized something else — the O2 defect, one level further out.
    """
    producer = _producer(registry, "family-skill", FAMILY)
    with pytest.raises(ProvenanceForgeryError) as raised:
        invocation_from_dispatch(producer, dispatched("a-different-skill"))
    assert "another skill's execution" in str(raised.value)


def test_a_TOOL_dispatch_produces_no_child(
    registry: ControlPlaneRegistry,
) -> None:
    """A tool dispatch is an effect-as-value this SDK never executes.

    Nothing was produced, so there is nothing to admit. Refused at the
    invocation rather than admitted as an empty child.
    """
    from ccf.skills.dispatch import ToolInvocation

    producer = _producer(registry, "family-skill", FAMILY)
    with pytest.raises(ProvenanceForgeryError) as raised:
        invocation_from_dispatch(
            producer,
            ToolInvocation(skill_name="family-skill", command="c", arguments={}),
        )
    assert "produces no Context Product" in str(raised.value)


def test_touched_entities_CANNOT_be_supplied_for_a_remote_child(
    registry: ControlPlaneRegistry,
) -> None:
    """`F3`, restated for the boundary Amendment 5 draws.

    F3's defect was omitting `touched_entities` and still recording that the
    local register had authorized the child. Amendment 3 closed it by making
    the value always present. **Amendment 5 closes it the other way**, because
    Dave ruled that a consumer must not be required to reach a remote
    provider's replay store: for an `mcp` or `peered` child the value is
    `None`, the register is not consulted, and the recorded BASIS says so.

    So the thing that must be impossible is no longer *absence* — it is
    **claiming entities for a child whose execution record this fabric does
    not hold**. Supplying them is refused rather than ignored.
    """
    for kind, produces in (("mcp", EXPOSURE), ("peering", COVENANT)):
        producer = _producer(
            registry, f"remote-{kind}", produces, skill_type=_SKILL_TYPE_FOR[kind]
        )
        with pytest.raises(ProvenanceForgeryError) as raised:
            invocation_from_dispatch(
                producer,
                dispatched(f"remote-{kind}", kind=kind),
                touched_entities=(ENTITY_OBLIGOR,),
            )
        assert "does not hold that provider's execution record" in str(raised.value)


def test_an_mcp_child_names_the_PROVIDERS_controls_not_the_local_register(
    registry: ControlPlaneRegistry,
) -> None:
    """`D-IMPL-59`: MCP is not peering, and it is not local production either.

    Dave's correction, verbatim: *"MCP is not automatically peering… Apply the
    existing controls for the actual provider relationship; do not require a
    new signed envelope merely because acquisition uses MCP."*

    So an MCP child is admitted on the provider's own authenticated access —
    and the row records `provider-controls`, which is a positive statement
    about which authority applied rather than a silence a reader could mistake
    for a local pass.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    out = admit(registry, candidate(registry, child, require(FAMILY), kind="mcp"))
    assert isinstance(out, AdmittedChild), out
    assert out.eligibility_basis == ELIGIBILITY_PROVIDER_CONTROLS


def test_a_peered_child_with_NO_peering_admission_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """`F16`, as Amendment 5 leaves it: composition consumes a verdict.

    The retired test asserted that a hand-built header could not become peer
    provenance. There is no such type now — so the control that replaces it is
    that a peered child WITHOUT the peering gate's own result is refused, which
    is the same claim made where the claim now lives: an assertion that was
    *present* is not an assertion that was *verified*.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    out = admit(registry, candidate(registry, child, require(FAMILY), kind="peering"))
    assert isinstance(out, ChildAdmissionRefusal), out
    assert out.reason == "provenance-unverified"
    assert "PeeringAdmissionGate" in out.detail


def test_a_local_child_that_read_NOTHING_is_a_verified_claim(
    registry: ControlPlaneRegistry,
) -> None:
    """`()` still means *the child read nothing*, and still is not `None`."""
    child = served(deliver(registry, _contract(schema=FAMILY)))
    out = admit(
        registry, candidate(registry, child, require(FAMILY), touched=())
    )
    assert isinstance(out, AdmittedChild), out
    assert out.eligibility_basis == ELIGIBILITY_LOCAL_REGISTER
    assert out.candidate.invocation.touched_entities == ()


def test_f3_a_superseded_child_is_now_refused_whatever_the_caller_omits(
    registry: ControlPlaneRegistry,
) -> None:
    """The F3 reproduction, re-run: the admitted case is gone.

    The panel measured `touched=None` admitting a superseded child AND
    recording `local-register`. That candidate can no longer be built, and the
    honest one refuses.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    ControlPlaneInvalidationSink(
        registry=registry, authorities=(composition_register(registry, register_key(TENANT)),)
    ).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )
    refusal = admit(registry, candidate(registry, child, require(FAMILY)))
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
    refusal = admit(registry, candidate(registry, foreign, require(FAMILY)))
    assert isinstance(refusal, ChildAdmissionRefusal)
    assert refusal.reason == "tenant-mismatch"


def test_f9_an_address_mismatch_keeps_the_two_addresses_apart(
    registry: ControlPlaneRegistry,
) -> None:
    """F9: the disproven value is never recorded as identity."""
    child = served(deliver(registry, _contract(schema=FAMILY)))
    refusal = admit(
        registry, candidate(registry, child, require(FAMILY), address="a-forged-address")
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


# --- composition: re-binding, the four laws, and the F1 ruling ---------------


def _admitted(
    registry: ControlPlaneRegistry, schema: str, req: ChildRequirement, **kw: object
) -> AdmittedChild:
    child = served(deliver(registry, _contract(schema=schema, **kw)))  # type: ignore[arg-type]
    out = admit(registry, candidate(registry, child, req))
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

    **Substitution is grant → REVOKE → grant, not two grants at once**
    (`D-IMPL-336` **O2**). The first version of this test held both producers
    effective simultaneously and paired each with an authored
    ``f"grant::{name}"`` string, so it asserted that two different strings
    differ. Against the real ledger that state is `AmbiguousProducerError` —
    which the test below covers — and the honest shape is the one a Control
    Plane operator actually performs.

    It therefore carries **two** proofs at once: the requirement, the
    admission path and the composed contract are unchanged across a producer
    swap, and a revoked grant stops producing immediately.
    """
    req = require(FAMILY)
    child = served(deliver(registry, _contract(schema=FAMILY)))
    ledger = _ledger(registry)

    rows = []
    for name in ("family-a", "family-b"):
        view = granted(registry, (name, FAMILY))
        resolved = resolve_producing_grant(req, view)
        assert resolved is not None
        out = admit(
            registry,
            ChildCandidate(
                requirement=req,
                contract=child,
                content_address=content_hash(child),
                invocation=invocation_from_dispatch(
                    resolved, dispatched(name), touched_entities=(ENTITY_OBLIGOR,)
                ),
            ),
        )
        assert isinstance(out, AdmittedChild)
        composed = compose([req], {FAMILY: out})
        assert composed.served
        rows.append(composed.resolutions[0])
        # ...and it goes out of force before the next one comes in, which is
        # what makes the second resolution unambiguous.
        ledger.revoke(revoke_capability(resolved.grant_hash, tenant=TENANT))
        assert resolve_producing_grant(req, view) is None

    assert rows[0].producing_skill_name != rows[1].producing_skill_name
    # The grant identities differ because the LEDGER made two different grants
    # effective, not because this file typed two different strings.
    assert rows[0].grant_hash != rows[1].grant_hash
    # everything governed is identical
    assert rows[0].child_content_address == rows[1].child_content_address
    assert rows[0].required_product_class == rows[1].required_product_class
    assert rows[0].child_debt_factors == rows[1].child_debt_factors


def test_o2_a_revoked_grant_cannot_initiate_a_child(
    registry: ControlPlaneRegistry,
) -> None:
    """`O2`, stated on its own: the ledger is read LIVE, not at wiring time.

    A `BoundSkillView` resolves from ledger state on every access, so a grant
    revoked after the view was obtained stops producing through that same
    view. Held as a separate test because the substitution control above would
    still pass if resolution were cached at first use.
    """
    view = granted(registry, ("family-live", FAMILY))
    resolved = resolve_producing_grant(require(FAMILY), view)
    assert resolved is not None
    _ledger(registry).revoke(revoke_capability(resolved.grant_hash, tenant=TENANT))
    assert resolve_producing_grant(require(FAMILY), view) is None


def test_o2_an_ungranted_entry_produces_nothing_however_real_it_is(
    registry: ControlPlaneRegistry,
) -> None:
    """The catalog is not authority; the grant is.

    A real, registered, `produces`-declaring catalog entry that no grant has
    made effective does not exist from the agent's view — so it cannot
    resolve, and there is no supported path to an invocation naming it.
    """
    ledger = _ledger(registry)
    register_skill_entry(ledger._catalog, registry, skill("family-ungranted", produces=FAMILY))
    view = ledger.bound_view(_AGENT_HASH)
    assert "family-ungranted" not in view
    assert resolve_producing_grant(require(FAMILY), view) is None


def test_o2_a_resolved_producer_cannot_be_authored(
    registry: ControlPlaneRegistry,
) -> None:
    """The capability discipline, applied to the thing O2 named.

    A plain frozen dataclass would have reproduced the defect exactly: a real
    entry beside a caller's grant hash. `ResolvedProducer` is minted only by
    `resolve_producing_grant`, so the pair travels from the ledger or not at
    all.
    """
    view = granted(registry, ("family-token", FAMILY))
    real = resolve_producing_grant(require(FAMILY), view)
    assert real is not None
    with pytest.raises(ProvenanceForgeryError):
        ResolvedProducer(
            entry=real.entry, grant_hash="grant::whatever", token=object()
        )


def test_ambiguous_producers_still_refuse_with_no_tie_breaker(
    registry: ControlPlaneRegistry,
) -> None:
    """Unchanged by the remediation, and re-asserted because F11 touched it.

    Now driven by two grants a real ledger made effective TOGETHER, which is
    the state a Control Plane can genuinely be in — the earlier dict of two
    entries could not distinguish "granted twice" from "never granted".
    """
    view = granted(registry, ("ambiguous-a", FAMILY), ("ambiguous-b", FAMILY))
    with pytest.raises(AmbiguousProducerError):
        resolve_producing_grant(require(FAMILY), view)


def test_a_skill_without_produces_still_cannot_satisfy_a_requirement(
    registry: ControlPlaneRegistry,
) -> None:
    """A granted skill that declares no product class produces none."""
    view = granted(registry, ("declares-nothing", NO_PRODUCT_CLASS))
    assert resolve_producing_grant(require(FAMILY), view) is None


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
    # `D-IMPL-336` **Amendment 5**: a LOCAL child names no producing fabric,
    # and that is correct rather than missing. Naming one would be this fabric
    # asserting an identity for a producer it never authenticated — which is
    # the whole class of claim the attestor layer was making and Amendment 5
    # removed. A PEERED child names the peer the peering gate verified, which
    # `tests/peering/test_child_eligibility.py` and the integration proof own.
    assert row.producing_fabric is None


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
        decided_at=ASKED_AT,
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
        decided_at=ASKED_AT + timedelta(minutes=5),
        validity_floors=NO_VALIDITY_FLOORS,
    )
    assert early.served and later.served
    assert early.expires_at is not None and later.expires_at is not None
    # The anchor moved by five minutes and the ceiling followed it. Before the
    # fix the function could not see the decision instant at all.
    assert later.expires_at > early.expires_at




def test_f3_REOPENED_a_local_child_with_no_execution_record_REFUSES(
    registry: ControlPlaneRegistry,
) -> None:
    """`F3`, re-opened by Amendment 5 and closed again at the close panel.

    **This is the regression, written as the test that would have caught it.**
    Amendment 3 closed F3 by making `touched_entities` always present.
    Amendment 5 made it optional — correctly, so a remote child need not force
    a read of its provider's replay store — and left the LOCAL leg admitting
    `None`: `refuse_dependency_invalidation` returns `None` immediately for
    `None`, so the register was never resolved, and the row still recorded
    `local-register` as the authority that had cleared it.

    Four independent reviewers found it and it was reproduced here before the
    fix, on a child whose entity really was superseded.

    The assertion is paired on purpose. A test that only checked the `None`
    case would pass against a register that refuses everything.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    ControlPlaneInvalidationSink(
        registry=registry, authorities=(composition_register(registry, register_key(TENANT)),)
    ).record(
        tenant_id=TENANT,
        entity_uri=ENTITY_OBLIGOR,
        invalidated_from=SUPERSEDED_AT,
        source="test",
        reason="superseded by a later observation",
    )
    req = require(FAMILY)

    # The control: the register is live and it refuses a superseded child.
    supplied = admit(registry, candidate(registry, child, req))
    assert isinstance(supplied, ChildAdmissionRefusal), supplied
    assert supplied.reason == "ineligible"

    # The finding: no execution record is *don't know*, never *pass*.
    absent = admit(registry, candidate(registry, child, req, touched=None))
    assert isinstance(absent, ChildAdmissionRefusal), (
        "a locally dispatched child with no execution record was ADMITTED, and"
        " the row would have claimed local-register as its authority"
    )
    assert absent.reason == "eligibility-evidence-missing"
    assert "not asked" in absent.detail


def test_f3_the_local_leg_is_the_ONLY_one_that_requires_an_execution_record(
    registry: ControlPlaneRegistry,
) -> None:
    """The boundary the fix must not overrun.

    Dave's ruling is explicit that a consumer must not be required to reach a
    remote provider's replay store. So the refusal above applies to
    `local-dispatch` and to nothing else: an MCP child with no entities is
    admitted on the provider's own controls, and says so.
    """
    child = served(deliver(registry, _contract(schema=FAMILY)))
    out = admit(registry, candidate(registry, child, require(FAMILY), kind="mcp"))
    assert isinstance(out, AdmittedChild), out
    assert out.eligibility_basis == ELIGIBILITY_PROVIDER_CONTROLS
    assert out.candidate.invocation.touched_entities is None


def test_a_remote_entry_CANNOT_be_relabelled_as_a_local_dispatch(
    registry: ControlPlaneRegistry,
) -> None:
    """The close panel's spoof, closed. Dave named this hazard by name.

    *"A local skill fetching a remote product must not relabel that product as
    locally produced to bypass its applicable checks."*

    The acquisition kind is read off the dispatch result's type. The dispatch
    RESULT types are ordinary public contracts — unlike `ChildInvocation` and
    `ResolvedProducer`, nothing mints them — so a hand-built `SkillInvocation`
    naming a genuinely MCP-bound entry used to yield `local-dispatch` **with
    caller-chosen touched entities**, which buys the local invalidation
    register's authority over a decision it never saw.

    Three facts are held to each other now: the result's TYPE, the `skill_type`
    the granted ENTRY declares, and the `skill_type` the dispatch stamps on its
    own result. A real dispatch cannot make them disagree.
    """
    mcp_producer = _producer(registry, "really-mcp", FAMILY, skill_type="mcp")

    # (1) an MCP-granted entry with a hand-built LOCAL result
    with pytest.raises(ProvenanceForgeryError) as relabel:
        invocation_from_dispatch(
            mcp_producer,
            SkillInvocation(
                skill_name="really-mcp", skill_type="local_callable", output={}
            ),
            touched_entities=(ENTITY_OBLIGOR,),
        )
    assert "relabelled as locally produced" in str(relabel.value)

    # (2) a result whose own two halves disagree — the right type, the wrong
    #     stamp. Caught even though the entry matches.
    local_producer = _producer(registry, "really-local", EXPOSURE)
    with pytest.raises(ProvenanceForgeryError) as stamped:
        invocation_from_dispatch(
            local_producer,
            SkillInvocation(skill_name="really-local", skill_type="mcp", output={}),
        )
    assert "two halves disagree" in str(stamped.value)

    # ...and the honest pairing still works, so this is a differential.
    assert (
        invocation_from_dispatch(
            local_producer, dispatched("really-local")
        ).acquisition
        == "local-dispatch"
    )


# --- the fourth composition law, and the fit checks: pinned by DELETION ------
#
# Close panel 2's completeness critic measured that removing the entire
# `refuse_mixing` call from `compose_children` left the suite at baseline. The
# fourth of the four laws the completion document lists as retained had NO
# execution coverage, because no test anywhere declared a non-default
# `ConstituentValidityFloors` — the only route to a breach.
#
# The same shape, found by fable in the same panel, covered four of the six fit
# checks: deleting them changed nothing. A check nothing would miss is a
# docstring with an `if` in front of it.


def test_the_MIXING_REFUSAL_law_actually_refuses(
    registry: ControlPlaneRegistry,
) -> None:
    """`D-IMPL-31`'s fourth law, with the floor that makes it reachable.

    *"A composite must not be built at all rather than built and labelled
    fresher than its stalest load-bearing constituent."* The refusal exists;
    until this test nothing declared a floor, so nothing ever breached one and
    the whole branch was dead code as far as the suite could tell.

    The child expires twelve hours after `ASKED_AT`; the floor demands a full
    day of remaining validity at the decision instant. It refuses.
    """
    req = require(FAMILY)
    adm = _admitted(registry, FAMILY, req)
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={FAMILY: 86400}
    )

    out = compose([req], {FAMILY: adm}, floors=floors)
    assert not out.served, "a constituent below its declared floor was composed"
    assert out.refusal is not None
    assert out.refusal.reason == "mixing-refused"
    # The rows survive the refusal, so a reader can see WHICH constituent.
    assert len(out.resolutions) == 1


def test_the_mixing_refusal_does_NOT_fire_when_the_floor_is_met(
    registry: ControlPlaneRegistry,
) -> None:
    """The control. Without it the test above would pass on a law that
    refused everything, which is a different defect wearing the same green."""
    req = require(FAMILY)
    adm = _admitted(registry, FAMILY, req)
    # One hour of required validity against twelve hours remaining.
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={FAMILY: 3600}
    )
    out = compose([req], {FAMILY: adm}, floors=floors)
    assert out.served, out.refusal


def test_a_floor_declared_for_ANOTHER_signal_type_does_not_bind_this_one(
    registry: ControlPlaneRegistry,
) -> None:
    """Floors are per signal type, and the lookup must actually key on it.

    A `refuse_mixing` that applied the first declared floor to every
    constituent would pass both tests above. This one moves only the key.
    """
    req = require(FAMILY)
    adm = _admitted(registry, FAMILY, req)
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={EXPOSURE: 86400}
    )
    out = compose([req], {FAMILY: adm}, floors=floors)
    assert out.served, "a floor declared for a different signal type bound this one"


@pytest.mark.parametrize(
    ("label", "kwargs", "reason"),
    [
        ("wrong class", {"schema": EXPOSURE}, "class-mismatch"),
        ("wrong instant", {"as_of": OTHER_AS_OF}, "as-of-mismatch"),
    ],
)
def test_each_FIT_CHECK_refuses_on_its_own(
    registry: ControlPlaneRegistry, label: str, kwargs: dict, reason: str
) -> None:
    """Each fit check, moved ALONE, with its own refusal reason.

    Close panel 2 measured that four of the six could be deleted with the
    suite still green: the tests that existed asserted only *that something
    refused*, which any surviving check satisfies. Naming the reason is what
    makes each check individually load-bearing.
    """
    req = require(FAMILY)
    child = served(deliver(registry, _contract(**{"schema": FAMILY, **kwargs})))
    out = admit(registry, candidate(registry, child, req))
    assert isinstance(out, ChildAdmissionRefusal), (label, out)
    assert out.reason == reason, label


def test_the_tenant_fit_check_refuses_on_its_own(
    registry: ControlPlaneRegistry,
) -> None:
    """Tenant, alone. `trust is per tenant` is the peering precedent."""
    foreign = _contract(schema=FAMILY).model_copy(update={"tenant_id": "other-bank"})
    out = admit(
        registry, candidate(registry, foreign, require(FAMILY))
    )
    assert isinstance(out, ChildAdmissionRefusal), out
    assert out.reason == "tenant-mismatch"


def test_the_ADDRESS_fit_check_refuses_on_its_own(
    registry: ControlPlaneRegistry,
) -> None:
    """The address is RECOMPUTED, so a reported one that disagrees refuses."""
    child = served(deliver(registry, _contract(schema=FAMILY)))
    out = admit(
        registry,
        candidate(registry, child, require(FAMILY), address="a-forged-address"),
    )
    assert isinstance(out, ChildAdmissionRefusal), out
    assert out.reason == "address-mismatch"


def test_the_DEBT_fit_check_refuses_on_its_own(
    registry: ControlPlaneRegistry,
) -> None:
    """*Unknown debt is not zero.* A child with none is unassessable."""
    child = served(deliver(registry, _contract(schema=FAMILY)))
    out = admit(
        registry,
        candidate(registry, child.model_copy(update={"debt": None}), require(FAMILY)),
    )
    assert isinstance(out, ChildAdmissionRefusal), out
    assert out.reason == "debt-unassessable"


def test_a_forged_PRODUCER_cannot_mint_an_invocation(
    registry: ControlPlaneRegistry,
) -> None:
    """Close panel 2's HIGH finding, and the most embarrassing kind.

    `ResolvedProducer` is token-minted so it cannot be forged — and its ONLY
    consumer never asked whether it had one. An object carrying `entry.name`,
    `entry.artifact_version`, `entry.skill_type` and `grant_hash` satisfied
    every dereference, so the minted `ChildInvocation` recorded a grant hash
    that was never in any ledger, while its own docstring called itself
    evidence that a real grant resolution ran.

    **The three-fact cross-check could not help**, and that is the lesson: with
    a forged producer all three facts are values the same caller authored, so
    they agree by construction. A capability token binds nothing unless the
    consumer demands the type.

    Reached through the public import with no reflection — `invocation_from_dispatch`,
    `ResolvedProducer` and `resolve_producing_grant` are all in `__all__`, and
    `CompositeChildResolverProtocol` is a documented extension point.
    """
    from types import SimpleNamespace

    forged = SimpleNamespace(
        entry=SimpleNamespace(
            name="fake-skill", artifact_version="1.0.0", skill_type="local_callable"
        ),
        grant_hash="not-from-any-ledger",
    )
    with pytest.raises(ProvenanceForgeryError) as raised:
        invocation_from_dispatch(
            forged,  # type: ignore[arg-type]
            SkillInvocation(
                skill_name="fake-skill", skill_type="local_callable", output={}
            ),
            touched_entities=(),
        )
    assert "grant hash nobody granted" in str(raised.value)

    # ...and the real one still works, so this is a differential.
    real = _producer(registry, "honest-skill", FAMILY)
    assert invocation_from_dispatch(real, dispatched("honest-skill")).grant_hash
