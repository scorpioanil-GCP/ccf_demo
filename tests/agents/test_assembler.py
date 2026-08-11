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
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.errors import AssemblyRefused
from ccf.agents.factory import AgentFactory
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.projection.acquisition import AcquiredContent, ContentRequest
from ccf.projection.plan import Perspective, ProjectionOutput
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
