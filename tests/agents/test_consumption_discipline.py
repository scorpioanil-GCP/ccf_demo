"""The AGNT-01 "no path from Agent to L1–L5" invariant test.

The negative test of the agent surface (CLAUDE.md §10 single-writer;
DESIGN.md §3.1: *"the agent framework's obligation is the negative one —
no path from `Agent` to L1–L5 exists"*; INV-CH6-05: agents consume
context, never data). Three claims, held mechanically:

1. **Import allowlist.** The ``ccf.agents`` package modules import nothing
   from the graph-write or L1–L5 internal surfaces. The allowed ``ccf``
   import surface is exactly: contracts (base + canonical), Control Plane
   resolution/artifacts, the artifacts protocol, the replay record, and
   the products contract. Asserted by AST inspection over the package
   source, so a graph-writer import cannot land without failing here.
2. **No write-surface attribute.** The constructed fixture agent's public
   surface exposes no attribute or method whose value is (or whose type
   names) a graph store, an L2 writer, or an operator engine.
3. **Consumption-only inputs.** The only fabric input an ``Agent`` method
   accepts is the typed Context Product contract — asserted over the
   method signatures of the public surface.

If a future change needs a new fabric import inside ``ccf.agents``, it
must be argued into the allowlist below, in review — never slipped in.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.agents.factory import AgentFactory
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import ContextProductContract

AGENTS_PACKAGE = Path("src/ccf/agents")
FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"

#: The complete permitted ``ccf`` import surface of the agents package.
#: Everything else in ``ccf.*`` — graph, assembly (L2), signal (L1),
#: operators (L4), projection (L5), halflife, similarity, llm, boot — is
#: fabric machinery the agent surface must not reach.
ALLOWED_CCF_PREFIXES = (
    "ccf.agents",
    "ccf.artifacts.protocol",
    "ccf.contracts",
    "ccf.controlplane.artifacts",
    "ccf.controlplane.registry",
    "ccf.products.contract",
    "ccf.replay.record",
    # Channel 2 (05-06): the skill catalog/dispatch surface is Control Plane
    # mechanism above L6, not a fabric layer — binding it opens no path from
    # Agent to L1–L5 (CLAUDE.md §6.2; D-08).
    "ccf.skills.catalog",
    "ccf.skills.dispatch",
)

#: I.1 write-surface / fabric-internal type names that must be unreachable
#: from the Agent public surface (src/ccf/graph/_writer.py,
#: src/ccf/assembly/worker.py, src/ccf/operators/).
WRITE_SURFACE_NAMES = frozenset(
    {
        "AssemblyWorker",
        "BaseGraphWriter",
        "BootToken",
        "GraphStore",
        "GraphWriter",
        "OperatorEngine",
        "OperatorPlanner",
    }
)


def _ccf_imports(source: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name for alias in node.names
                if alias.name.startswith("ccf")
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("ccf"):
                imported.add(node.module)
    return imported


@pytest.mark.parametrize(
    "module_path",
    sorted(AGENTS_PACKAGE.glob("*.py")),
    ids=lambda p: p.name,
)
def test_agents_modules_import_only_the_consumption_surface(
    module_path: Path,
) -> None:
    for module in sorted(_ccf_imports(module_path.read_text())):
        assert module.startswith(ALLOWED_CCF_PREFIXES), (
            f"{module_path} imports {module!r}, which is outside the agents"
            " package's permitted consumption surface — no path from Agent"
            " to L1–L5 (AGNT-01; CLAUDE.md §10; DESIGN.md §3.1)"
        )


def _constructed_fixture_agent() -> Agent:
    """The slice agent, constructed via the factory from fixtures only."""
    plane = ControlPlaneRegistry()
    prompt_fixture: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "prompts" / "covenant_summary.yaml").read_text()
    )
    plane.register_typed(
        prompt_fixture["keys"]["prompt_artifact"],
        parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT),
        PROMPT_ARTIFACT,
    )
    agent_fixture: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "agents" / "covenant_analytics.yaml").read_text()
    )
    for reference in agent_fixture["referenced_artifacts"].values():
        artifact_class = declared_artifact_class(reference["class_id"])
        plane.register_typed(
            reference["key"],
            parse_artifact(
                {
                    "class_id": reference["class_id"],
                    "semver": reference["semver"],
                    "declaration": reference["declaration"],
                },
                artifact_class,
            ),
            artifact_class,
        )
    definition = parse_artifact(
        agent_fixture["agent_definition"], AGENT_DEFINITION
    )
    assert isinstance(definition, AgentDefinition)
    key = agent_fixture["keys"]["agent_definition"]
    version = plane.register_versioned(key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    return AgentFactory(control_plane=plane).construct(
        definition_key=key, definition_version=version
    )


def test_the_agent_public_surface_holds_no_write_surface_object() -> None:
    agent = _constructed_fixture_agent()
    for name in dir(agent):
        if name.startswith("_"):
            continue
        member = getattr(agent, name)
        member_type = type(member).__name__
        assert member_type not in WRITE_SURFACE_NAMES, (
            f"Agent.{name} holds a {member_type} — a fabric write surface"
            " reachable from the agent boundary (CLAUDE.md §10)"
        )
        if callable(member) and not inspect.ismethod(member):
            continue
        # Returned/held values must not name write surfaces either.
        assert not any(
            surface in repr(type(member)) for surface in WRITE_SURFACE_NAMES
        ), name


def test_agent_methods_accept_only_typed_context_products() -> None:
    """The one fabric input across the public surface is the typed Context
    Product contract (INV-CH6-05: consume context, never data)."""
    fabric_typed_params: list[tuple[str, str, Any]] = []
    for name, member in inspect.getmembers(Agent, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        for parameter in inspect.signature(member).parameters.values():
            annotation = str(parameter.annotation)
            if "ccf." in annotation or annotation in (
                "ContextProductContract",
                "GraphView",
                "SignalEnvelope",
            ):
                fabric_typed_params.append((name, parameter.name, annotation))
    assert fabric_typed_params == [
        ("consume", "product", "ContextProductContract")
    ], fabric_typed_params
    agent = _constructed_fixture_agent()
    assert (
        inspect.signature(Agent.consume).parameters["product"].annotation
        == "ContextProductContract"
    )
    assert isinstance(agent, Agent)
    # And the contract type really is the L6 delivery contract, not a lookalike.
    assert ContextProductContract.__module__ == "ccf.products.contract"
