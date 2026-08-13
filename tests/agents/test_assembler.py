"""The assembler surface — a Protocol whose implementation is a declared agent.

Written before the implementation per the TDD discipline. The ruling of record
is ``docs/DECISIONS.md`` **D-IMPL-97** ruling 2 (Dave, 2026-08-10): *"the
assembler, which I agree should be a Protocol, is what makes the ContextProduct
a KYC_ContextProduct"*, and *"agent becomes the implementation protocol."*

Every agent here is constructed **through the Agent Factory from the banking
fixture artifacts** (CLAUDE.md §6.4); no test constructs one any other way, and
mutant definitions are fixture mutations registered under their own keys, never
inline documents. The fixture in use is ``deal_monitor_assembler``, which
already declares the ``context_assembly`` archetype.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.agent import Agent
from ccf.agents.assembler import (
    NO_CONSULTATIONS,
    AssemblyOutcome,
    ConsultationRecord,
    ContextAssemblerProtocol,
    DeterministicAssembler,
)
from ccf.agents.archetypes import ARCHETYPES, ReplayObligation, context_assembly
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    ASSEMBLY_ARCHETYPE_ID,
    EMITS_NOTHING,
    PROMPT_ARTIFACT,
    AgentDefinition,
    EmittedProduct,
    PromptArtifact,
)
from ccf.agents.errors import (
    AgentDefinitionError,
    AssemblyRefused,
    SkillNotBound,
)
from ccf.agents.factory import AgentFactory
from ccf.artifacts.protocol import parse_artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.resolution import resolve_pinned
from ccf.projection.acquisition import AcquiredContent, ContentRequest
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.products.contract import RegisteredProductClass
from ccf.products.request import ProductRequest
from ccf.skills.catalog import (
    SKILL_CATALOG_ENTRY,
    SkillCatalog,
    SkillCatalogEntry,
)
from ccf.skills.grants import (
    GOVERNANCE_FIELD,
    GrantLedger,
    PolicyRegimeGovernance,
    SkillGrant,
)
from skills.sinks import ScriptedApprovalSink

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


def _fixture(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "agents" / name).read_text()
    )
    return loaded


def _prompt_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "prompts" / "covenant_summary.yaml").read_text()
    )
    return loaded


def _assembler_fixture() -> dict[str, Any]:
    return _fixture("deal_monitor_assembler.yaml")


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    """A plane holding what both banking agent fixtures reference.

    Both, because the axis-4 claim needs two policy regimes that differ in
    what they permit, and the tree already ships exactly two: the assembler
    fixture's regime declares no skilling envelope, and the analytics
    fixture's declares one. Using the shipped pair keeps the difference a
    *fixture* statement rather than a value invented in test code (§6.4).
    """
    plane = ControlPlaneRegistry()
    prompt_fixture = _prompt_fixture()
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    assert isinstance(prompt, PromptArtifact)
    plane.register_typed(
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    for name in ("deal_monitor_assembler.yaml", "covenant_analytics.yaml"):
        for reference in _fixture(name)["referenced_artifacts"].values():
            artifact_class = declared_artifact_class(reference["class_id"])
            declared = parse_artifact(
                {
                    "class_id": reference["class_id"],
                    "semver": reference["semver"],
                    "declaration": reference["declaration"],
                },
                artifact_class,
            )
            plane.register_typed(reference["key"], declared, artifact_class)
    return plane


def _definition(document: dict[str, Any]) -> AgentDefinition:
    definition = parse_artifact(document, AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    return definition


def _construct(
    plane: ControlPlaneRegistry, document: dict[str, Any], key: str
) -> Agent:
    """Build one agent the only supported way — through the factory (§6.4)."""
    definition = _definition(document)
    version = plane.register_versioned(key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    return AgentFactory(control_plane=plane).construct(
        definition_key=key, definition_version=version
    )


def _construct_with_classes(
    plane: ControlPlaneRegistry,
    document: dict[str, Any],
    key: str,
    product_classes: dict[str, RegisteredProductClass],
) -> Agent:
    """The same supported path, with the deployment's registered classes wired."""
    definition = _definition(document)
    version = plane.register_versioned(key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    return AgentFactory(
        control_plane=plane, product_classes=product_classes
    ).construct(definition_key=key, definition_version=version)


def _assembler_agent(plane: ControlPlaneRegistry) -> Agent:
    fixture = _assembler_fixture()
    return _construct(
        plane, fixture["agent_definition"], fixture["keys"]["agent_definition"]
    )


def _projection() -> ProjectionOutput:
    """A Π output whose payload the reference assembler must not touch."""
    fixture = _assembler_fixture()["agent_definition"]
    consumed = fixture["context_contract"]["consumes"][0]
    return ProjectionOutput(
        plan_id=fixture["name"],
        payload={consumed["product_class"]: consumed["schema_version"]},
    )


#: The instant a test caller asks as of. A test-harness value, not a domain one:
#: the request surface takes the instant from its caller precisely so nothing on
#: this path reads a clock, and a test is a caller like any other.
ASKED_AT = datetime(2026, 8, 11, tzinfo=timezone.utc)


def _request(agent: Agent) -> ProductRequest:
    """A question addressed to the class the fixture names — fixture values only."""
    consumed = agent.definition.context_contract.consumes[0]
    perspective = agent.definition.perspective
    return ProductRequest(
        schema_name=consumed.product_class,
        schema_version=consumed.schema_version,
        subject=agent.definition.name,
        intent=perspective.role,
        freshness=perspective.selection_params["watch"],
        asked_at=ASKED_AT,
        parameters={},
    )


def _perspective(agent: Agent) -> Perspective:
    return Perspective(
        principal_id=agent.definition.tenant, role=agent.definition.perspective.role
    )


# --- the Protocol -------------------------------------------------------------


def test_the_reference_implementation_conforms_structurally(
    registry: ControlPlaneRegistry,
) -> None:
    """A deployment substitutes an assembler by conforming, never by inheriting."""
    agent = _assembler_agent(registry)
    assembler = DeterministicAssembler(agent=agent, projection=_projection())
    assert isinstance(assembler, ContextAssemblerProtocol)
    # Structural, never nominal: the reference implementation inherits nothing
    # from the Protocol, so the SDK's own assembler carries no privileged status
    # that a deployment's could not reproduce (the
    # src/ccf/halflife/debt.py::DebtFactorScorerProtocol posture).
    assert ContextAssemblerProtocol not in DeterministicAssembler.__mro__


def test_assemble_is_keyword_only(registry: ControlPlaneRegistry) -> None:
    """A three-value signature cannot be called with its arguments transposed."""
    for owner in (ContextAssemblerProtocol, DeterministicAssembler):
        signature = inspect.signature(owner.assemble)
        positional = [
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.name != "self"
            and parameter.kind is not inspect.Parameter.KEYWORD_ONLY
        ]
        assert positional == [], (owner, positional)


def test_the_protocol_carries_a_pinnable_identity(
    registry: ControlPlaneRegistry,
) -> None:
    """The assembler in force is part of what a decision replays against."""
    agent = _assembler_agent(registry)
    assembler = DeterministicAssembler(agent=agent, projection=_projection())
    assert assembler.assembler_id
    assert assembler.assembler_version
    outcome = assembler.assemble(
        request=_request(agent),
        perspective=_perspective(agent),
        tenant_id=agent.definition.tenant,
    )
    assert outcome.assembler_id == assembler.assembler_id
    assert outcome.assembler_version == assembler.assembler_version


# --- Alternation: enlisted output has exactly one route -----------------------


def test_the_outcome_has_one_route_for_enlisted_content(
    registry: ControlPlaneRegistry,
) -> None:
    """§7.6.6: model-produced content re-enters algorithmically, never as payload.

    Field enumeration rather than a docstring, in the
    ``tests/products/test_request_contract.py`` shape: a docstring cannot fail
    when somebody adds ``generated_narrative``.
    """
    assert set(AssemblyOutcome.model_fields) == {
        "payload",
        "consultations",
        "acquisitions",
        "assembler_id",
        "assembler_version",
        "skill_set_in_force",
        "halflife_debt_profile",
    }
    annotations = {
        name: str(field.annotation)
        for name, field in AssemblyOutcome.model_fields.items()
    }
    carrying = [
        name
        for name, annotation in annotations.items()
        if AcquiredContent.__name__ in annotation
    ]
    assert carrying == ["acquisitions"]


def test_acquired_content_travels_with_its_content_address(
    registry: ControlPlaneRegistry,
) -> None:
    """The acquired-content slot carries content addresses, so a replay re-feeds."""
    agent = _assembler_agent(registry)
    request = ContentRequest(
        request_key=agent.definition.name,
        source_key=agent.definition.perspective.selection_params["portfolio"],
        selector=agent.definition.perspective.role,
    )
    acquired = AcquiredContent.of(request=request, content=agent.definition.name)
    assembler = DeterministicAssembler(
        agent=agent, projection=_projection(), acquisitions=(acquired,)
    )
    outcome = assembler.assemble(
        request=_request(agent),
        perspective=_perspective(agent),
        tenant_id=agent.definition.tenant,
    )
    assert outcome.acquisitions == (acquired,)
    assert outcome.acquisitions[0].content_hash == acquired.rehash()


# --- the reference implementation is mechanism --------------------------------


def test_the_reference_assembler_consults_nothing(
    registry: ControlPlaneRegistry,
) -> None:
    agent = _assembler_agent(registry)
    assembler = DeterministicAssembler(agent=agent, projection=_projection())
    outcome = assembler.assemble(
        request=_request(agent),
        perspective=_perspective(agent),
        tenant_id=agent.definition.tenant,
    )
    assert outcome.consultations == NO_CONSULTATIONS
    assert outcome.consultations.permitted == ()
    assert outcome.consultations.refused == ()


def test_the_reference_assembler_returns_the_projection_payload_unchanged(
    registry: ControlPlaneRegistry,
) -> None:
    agent = _assembler_agent(registry)
    projection = _projection()
    assembler = DeterministicAssembler(agent=agent, projection=projection)
    outcome = assembler.assemble(
        request=_request(agent),
        perspective=_perspective(agent),
        tenant_id=agent.definition.tenant,
    )
    assert outcome.payload == projection.payload


def test_a_consultation_record_is_deterministic_and_disjoint() -> None:
    """Permitted and refused participate in content identity, so both are ordered."""
    with pytest.raises(ValueError):
        ConsultationRecord(permitted=("b", "a"), refused=())
    with pytest.raises(ValueError):
        ConsultationRecord(permitted=("a", "a"), refused=())
    with pytest.raises(ValueError):
        ConsultationRecord(permitted=("a",), refused=("a",))


# --- single-writer holds across the seam --------------------------------------


def test_the_outcome_is_a_returned_value_not_a_write(
    registry: ControlPlaneRegistry,
) -> None:
    """No path from the assembler surface reaches a graph write handle."""
    source = (Path(__file__).parent.parent.parent / "src/ccf/agents/assembler.py").read_text()
    for forbidden in ("GraphWriter", "write_handle", "def write", "upsert"):
        assert forbidden not in source, forbidden


def test_the_assembler_refuses_a_tenant_that_is_not_its_own(
    registry: ControlPlaneRegistry,
) -> None:
    agent = _assembler_agent(registry)
    assembler = DeterministicAssembler(agent=agent, projection=_projection())
    with pytest.raises(AssemblyRefused) as refusal:
        assembler.assemble(
            request=_request(agent),
            perspective=_perspective(agent),
            tenant_id=agent.definition.perspective.role,
        )
    assert agent.definition.tenant in str(refusal.value)
    assert agent.definition.perspective.role in str(refusal.value)


def test_the_assembler_refuses_a_perspective_it_was_not_declared_under(
    registry: ControlPlaneRegistry,
) -> None:
    agent = _assembler_agent(registry)
    assembler = DeterministicAssembler(agent=agent, projection=_projection())
    foreign = Perspective(
        principal_id=agent.definition.tenant, role=agent.definition.name
    )
    with pytest.raises(AssemblyRefused) as refusal:
        assembler.assemble(
            request=_request(agent),
            perspective=foreign,
            tenant_id=agent.definition.tenant,
        )
    assert agent.definition.perspective.role in str(refusal.value)
    assert agent.definition.name in str(refusal.value)


# --- axis 2's emission side ---------------------------------------------------


def _emitting_document(
    *, archetypes: tuple[str, ...] | None = None, artifact_version: str
) -> dict[str, Any]:
    """The fixture definition, mutated to declare an emission binding.

    A fixture mutation registered under its own key, never an inline document
    (the convention ``tests/agents/test_factory.py`` states). The emitted class
    is the one the fixture already names under ``consumes``, so no product
    identity is invented in test code (No-Hardcoding Rule §6.4).
    """
    document = dict(_assembler_fixture()["agent_definition"])
    consumed = document["context_contract"]["consumes"][0]
    document["context_contract"] = {
        "consumes": document["context_contract"]["consumes"],
        "emits": [
            {
                "product_class": consumed["product_class"],
                "schema_version": consumed["schema_version"],
            }
        ],
    }
    if archetypes is not None:
        document["archetypes"] = list(archetypes)
    document["artifact_version"] = artifact_version
    return document


def _registered_class(document: dict[str, Any]) -> RegisteredProductClass:
    """The deployment's registration of the class the mutant emits to."""
    emitted = document["context_contract"]["emits"][0]
    return RegisteredProductClass(
        schema_name=emitted["product_class"],
        schema_version=emitted["schema_version"],
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=emitted["product_class"],
        max_ttl_version=emitted["schema_version"],
    )


def test_an_agent_declares_no_emission_by_default(
    registry: ControlPlaneRegistry,
) -> None:
    """*This agent emits nothing* is a claim, not an absence."""
    agent = _assembler_agent(registry)
    assert agent.definition.context_contract.emits == EMITS_NOTHING
    assert EMITS_NOTHING == ()


def test_the_emission_binding_lives_on_the_context_contract(
    registry: ControlPlaneRegistry,
) -> None:
    """Axis 2 grew the side its own docstring said it was designed to grow."""
    document = _emitting_document(artifact_version="1.1.0")
    emitted = document["context_contract"]["emits"][0]
    registered = _registered_class(document)
    agent = _construct_with_classes(
        registry,
        document,
        _assembler_fixture()["keys"]["agent_definition"],
        {registered.schema_name: registered},
    )
    assert agent.definition.context_contract.emits == (
        EmittedProduct(
            product_class=emitted["product_class"],
            schema_version=emitted["schema_version"],
        ),
    )
    # The consuming side is untouched: additive means additive.
    assert agent.definition.context_contract.consumes == (
        _definition(_assembler_fixture()["agent_definition"])
        .context_contract.consumes
    )


def test_the_factory_refuses_an_emitter_that_is_not_an_assembler(
    registry: ControlPlaneRegistry,
) -> None:
    """Naming both sides, and not repairing either."""
    fixture = _assembler_fixture()["agent_definition"]
    monitoring_only = tuple(
        a for a in fixture["archetypes"] if a != "context_assembly"
    )
    document = _emitting_document(
        archetypes=monitoring_only, artifact_version="1.2.0"
    )
    with pytest.raises(AgentDefinitionError) as refusal:
        _construct(
            registry,
            document,
            _assembler_fixture()["keys"]["agent_definition"],
        )
    message = str(refusal.value)
    assert "context_assembly" in message
    assert repr(monitoring_only) in message or monitoring_only[0] in message


def test_the_factory_refuses_an_emission_to_an_unregistered_class(
    registry: ControlPlaneRegistry,
) -> None:
    """A deployment finds out while wiring the fabric, not in front of a caller."""
    document = _emitting_document(artifact_version="1.3.0")
    emitted = document["context_contract"]["emits"][0]
    with pytest.raises(AgentDefinitionError) as refusal:
        _construct(
            registry,
            document,
            _assembler_fixture()["keys"]["agent_definition"],
        )
    message = str(refusal.value)
    assert emitted["product_class"] in message
    assert emitted["schema_version"] in message


def test_the_factory_refuses_an_emission_to_another_lane(
    registry: ControlPlaneRegistry,
) -> None:
    """Lanes are per class and never compared across classes (INV-CH7-49)."""
    document = _emitting_document(artifact_version="1.4.0")
    registered = _registered_class(document)
    other_lane = registered.model_copy(update={"schema_version": "9.0.0"})
    with pytest.raises(AgentDefinitionError) as refusal:
        _construct_with_classes(
            registry,
            document,
            _assembler_fixture()["keys"]["agent_definition"],
            {other_lane.schema_name: other_lane},
        )
    assert "9.0.0" in str(refusal.value)


def test_the_factory_accepts_a_registered_emission(
    registry: ControlPlaneRegistry,
) -> None:
    document = _emitting_document(artifact_version="1.5.0")
    registered = _registered_class(document)
    agent = _construct_with_classes(
        registry,
        document,
        _assembler_fixture()["keys"]["agent_definition"],
        {registered.schema_name: registered},
    )
    assert agent.definition.context_contract.emits[0].product_class == (
        registered.schema_name
    )


# --- the archetype the Protocol attaches to is unchanged ----------------------


def test_the_context_assembly_archetype_declares_what_it_always_declared() -> None:
    """The Protocol attaches to the archetype's obligations, never replaces them."""
    assert context_assembly.archetype_id == "context_assembly"
    assert context_assembly.fabric_interaction_pattern() == "typed-product-emission"
    assert context_assembly.replay_obligations() == (
        ReplayObligation(
            name="emitted-product-replay-envelope",
            obligation=(
                "the emitted product is itself a replayable artifact"
                " bound to the five-dimension envelope, distinct from"
                " any consumer's inference trace; emission routes"
                " through the single-writer assembly mechanism"
            ),
        ),
        ReplayObligation(
            name="policy-before-similarity",
            obligation=(
                "policy composes before similarity at every assembly"
                " step the archetype takes"
            ),
        ),
    )
    assert context_assembly.configuration_defaults() == ()


# --- the implementation is a declared agent, not code -------------------------


def test_the_assembler_is_a_declared_agent_and_its_identity_is_the_artifact(
    registry: ControlPlaneRegistry,
) -> None:
    """D-IMPL-97 ruling 2, as a property rather than a slogan.

    Nothing here asserts the CINV-01c factory-bypass lint — that is CI's job.
    What it demonstrates is the path: the thing implementing the Protocol is a
    Control Plane artifact, and the running assembler's identity is the
    *content identity of that artifact*, so replay answers "which assembler"
    by answering "which agent version" (D-06, D-IMPL-26).
    """
    agent = _assembler_agent(registry)
    assembler = DeterministicAssembler(agent=agent, projection=_projection())
    assert isinstance(assembler, ContextAssemblerProtocol)
    assert assembler.agent.identity.definition_hash == content_hash(
        agent.definition
    )
    # And there is no assembler in /src that is an agent: the archetype
    # registry holds mechanism, and the definition it was built from is a
    # document under tests/fixtures, not a Python class (CLAUDE.md §6.1).
    assert ASSEMBLY_ARCHETYPE_ID in agent.definition.archetypes
    assert ASSEMBLY_ARCHETYPE_ID in ARCHETYPES


# --- axis 4 bounds what an assembler may consult ------------------------------


@dataclass(frozen=True)
class _RegimeBoundedAssembler:
    """A conforming assembler whose consultations are bounded by axis 4.

    A *test* implementation, and its existence is half the point: the SDK
    ships a Protocol, so a deployment that needs consultation behaviour writes
    one of these rather than subclassing or patching anything in ``/src``.

    Its identity is the declared agent's own — ``assembler_id`` is the agent's
    name and ``assembler_version`` its artifact version — which is what
    D-IMPL-97 ruling 2 means by *"agent becomes the implementation protocol"*.

    The permitted envelope is read from the agent's resolved policy regime
    through the SDK's own :class:`~ccf.skills.grants.PolicyRegimeGovernance`,
    so no governance key name is spelled in test code.
    """

    agent: Agent
    projection: ProjectionOutput
    control_plane: ControlPlaneRegistry
    requested: tuple[str, ...]

    @property
    def assembler_id(self) -> str:
        return self.agent.definition.name

    @property
    def assembler_version(self) -> str:
        return self.agent.definition.artifact_version

    def _permitted_scopes(self) -> frozenset[str]:
        regime = resolve_pinned(
            self.control_plane, self.agent.definition.policy_regime.ref
        )
        declaration = getattr(regime, "declaration", None)
        block = (
            declaration.get(GOVERNANCE_FIELD)
            if isinstance(declaration, Mapping)
            else None
        )
        if block is None:
            # A regime silent about skilling has permitted nothing (D-IMPL-38).
            return frozenset()
        return PolicyRegimeGovernance.model_validate(block).permitted_scopes

    def assemble(
        self,
        *,
        request: ProductRequest,
        perspective: Perspective,
        tenant_id: str,
    ) -> AssemblyOutcome:
        permitted = self._permitted_scopes()
        return AssemblyOutcome(
            payload=self.projection.payload,
            consultations=ConsultationRecord(
                permitted=tuple(sorted(t for t in self.requested if t in permitted)),
                refused=tuple(
                    sorted(t for t in self.requested if t not in permitted)
                ),
            ),
            acquisitions=(),
            assembler_id=self.assembler_id,
            assembler_version=self.assembler_version,
            skill_set_in_force=self.agent.bound_skill_names,
            halflife_debt_profile=self.agent.definition.halflife_debt_profile.ref,
        )


def _wide_regime_document(*, artifact_version: str) -> dict[str, Any]:
    """The assembler definition, re-pinned to the regime that permits a scope.

    Differs from the shipped fixture in **axis 4 alone** — a fixture mutation
    registered under its own key, with both refs taken from fixtures.
    """
    document = dict(_assembler_fixture()["agent_definition"])
    document["policy_regime"] = dict(
        _fixture("covenant_analytics.yaml")["agent_definition"]["policy_regime"]
    )
    document["artifact_version"] = artifact_version
    return document


def _requested_targets() -> tuple[str, ...]:
    """The consultation targets the two regimes disagree about.

    Sourced from the wide regime's own declared envelope, so the test asks
    about exactly what a deployment said, and invents no identifier.
    """
    declaration = _fixture("covenant_analytics.yaml")["referenced_artifacts"][
        "policy_regime"
    ]["declaration"]
    return tuple(sorted(declaration[GOVERNANCE_FIELD]["permitted_scopes"]))


def test_axis_4_bounds_what_an_assembler_may_consult(
    registry: ControlPlaneRegistry,
) -> None:
    """Two definitions differing only in policy regime consult differently."""
    requested = _requested_targets()
    assert requested, "the wide regime declares at least one permitted scope"

    narrow = _assembler_agent(registry)
    wide = _construct(
        registry,
        _wide_regime_document(artifact_version="2.0.0"),
        _assembler_fixture()["keys"]["agent_definition"],
    )
    assert narrow.definition.policy_regime != wide.definition.policy_regime
    # Everything else about the two definitions is identical — axis 4 alone.
    assert narrow.definition.archetypes == wide.definition.archetypes
    assert narrow.definition.context_contract == wide.definition.context_contract
    assert narrow.definition.perspective == wide.definition.perspective

    outcomes = {
        role: _RegimeBoundedAssembler(
            agent=agent,
            projection=_projection(),
            control_plane=registry,
            requested=requested,
        ).assemble(
            request=_request(agent),
            perspective=_perspective(agent),
            tenant_id=agent.definition.tenant,
        )
        for role, agent in (("narrow", narrow), ("wide", wide))
    }
    assert outcomes["wide"].consultations.permitted == requested
    assert outcomes["wide"].consultations.refused == ()
    assert outcomes["narrow"].consultations.permitted == ()
    assert outcomes["narrow"].consultations.refused == requested
    assert (
        outcomes["narrow"].consultations != outcomes["wide"].consultations
    )


# --- axis 5 is already required, and is honoured ------------------------------


def test_axis_5_is_pinned_resolved_at_construction_and_reported(
    registry: ControlPlaneRegistry,
) -> None:
    """The home for a product's debt configuration already exists, on the agent.

    Three claims, and the middle one is why D-IMPL-97 calls the agent's fit
    *confirmation rather than convenience*: the profile ref is pinned (never
    ``@latest``), the factory refuses a definition whose profile does not
    resolve, and the assembler reports the exact ref it ran under.

    The shipped fixture registers its profile as a *declared* artifact class
    (``debt-profile``, the deployment's own envelope) rather than the SDK's
    ``ccf.debt-profile``, so the assertion here is that the pin resolves at
    its pinned version — not that the resolved value is a
    :class:`~ccf.controlplane.artifacts.DebtProfile` instance. Overstating it
    would be the test asserting something the fixture does not say.
    """
    agent = _assembler_agent(registry)
    ref = agent.definition.halflife_debt_profile.ref
    name = parse_artifact_uri(ref)
    assert name.artifact_version and name.artifact_version != "latest"
    assert resolve_pinned(registry, ref) is not None

    outcome = DeterministicAssembler(
        agent=agent, projection=_projection()
    ).assemble(
        request=_request(agent),
        perspective=_perspective(agent),
        tenant_id=agent.definition.tenant,
    )
    assert outcome.halflife_debt_profile == ref

    # And the factory refuses a definition whose axis-5 pin resolves to
    # nothing — the deployment finds out while wiring the fabric.
    document = dict(_assembler_fixture()["agent_definition"])
    document["halflife_debt_profile"] = {
        "ref": ref.rsplit("@", 1)[0] + "@9.9.9"
    }
    document["artifact_version"] = "3.0.0"
    with pytest.raises(AgentDefinitionError):
        _construct(
            registry, document, _assembler_fixture()["keys"]["agent_definition"]
        )


# --- channel 2 governs enlistment ---------------------------------------------


def _skill_entry() -> SkillCatalogEntry:
    tool_fixture: dict[str, Any] = yaml.safe_load(
        (FIXTURES.parent / "banking" / "skills" / "covenant_metrics_tool.yaml")
        .read_text()
    )
    entry = parse_artifact(tool_fixture["entry"], SKILL_CATALOG_ENTRY)
    assert isinstance(entry, SkillCatalogEntry)
    return entry


def test_channel_2_governs_enlistment_and_the_outcome_records_it(
    registry: ControlPlaneRegistry,
) -> None:
    """A decision replays against the skills the agent *had*, not the ones it has.

    The claim the plan asks for in full: grant, assemble, revoke, assemble
    again — and the **first** outcome still records the skill-set that was in
    force when it ran. That is the difference between a record and a live
    query, and it is what makes the skill-set answerable from replay alone
    (CLAUDE.md §6.2; D-07).
    """
    granted_values = _fixture("covenant_analytics.yaml")["slice"]["granted_skill"]
    document = _wide_regime_document(artifact_version="2.1.0")
    definition = _definition(document)
    key = _assembler_fixture()["keys"]["agent_definition"]
    version = registry.register_versioned(key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)

    catalog = SkillCatalog(registry)
    assert isinstance(catalog.register(_skill_entry()), str)
    ledger = GrantLedger(
        control_plane=registry,
        catalog=catalog,
        audit=registry.audit_log,
        sink=ScriptedApprovalSink(
            approve=True, approver_id=granted_values["approver_id"]
        ),
        clock=lambda: ASKED_AT,
    )
    definition_hash = content_hash(definition)
    grant = SkillGrant(
        agent_definition_hash=definition_hash, **granted_values["grant"]
    )
    grant_hash = ledger.request(
        grant, definition=definition, actor=granted_values["requesting_actor"]
    )
    assert isinstance(grant_hash, str), grant_hash

    agent = AgentFactory(control_plane=registry).construct(
        definition_key=key,
        definition_version=version,
        bound_skills=ledger.bound_view(definition_hash),
    )
    assembler = DeterministicAssembler(agent=agent, projection=_projection())

    granted_outcome = assembler.assemble(
        request=_request(agent),
        perspective=_perspective(agent),
        tenant_id=agent.definition.tenant,
    )
    assert grant.skill_name in granted_outcome.skill_set_in_force
    # The agent can enlist it while it is bound.
    assert agent.invoke_skill(grant.skill_name) is not None

    ledger.revoke(grant_hash, actor=granted_values["requesting_actor"])

    revoked_outcome = assembler.assemble(
        request=_request(agent),
        perspective=_perspective(agent),
        tenant_id=agent.definition.tenant,
    )
    assert grant.skill_name not in revoked_outcome.skill_set_in_force
    with pytest.raises(SkillNotBound):
        agent.invoke_skill(grant.skill_name)

    # The decisive assertion: the first outcome is unchanged by the revocation.
    assert granted_outcome.skill_set_in_force == (grant.skill_name,)
    assert revoked_outcome.skill_set_in_force == ()

    # Both governance actions are in the audit log, and the agent's identity
    # never moved across either (D-07).
    actions = [event.action for event in registry.audit_log.events()]
    assert any("grant" in action for action in actions), actions
    assert any("revoke" in action for action in actions), actions
    assert agent.identity.definition_hash == definition_hash
