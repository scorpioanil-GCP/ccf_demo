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
from ccf.agents.archetypes import ReplayObligation, context_assembly
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    EMITS_NOTHING,
    PROMPT_ARTIFACT,
    AgentDefinition,
    EmittedProduct,
    PromptArtifact,
)
from ccf.agents.errors import AgentDefinitionError, AssemblyRefused
from ccf.agents.factory import AgentFactory
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.projection.acquisition import AcquiredContent, ContentRequest
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.products.contract import RegisteredProductClass
from ccf.products.request import ProductRequest

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
    """A plane holding everything the assembler fixture references."""
    plane = ControlPlaneRegistry()
    prompt_fixture = _prompt_fixture()
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    assert isinstance(prompt, PromptArtifact)
    plane.register_typed(
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    for reference in _assembler_fixture()["referenced_artifacts"].values():
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
    # that a deployment's could not reproduce (the DebtFactorScorerProtocol
    # posture at src/ccf/halflife/debt.py:115-127).
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
    agent = _construct(
        registry, document, _assembler_fixture()["keys"]["agent_definition"]
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
