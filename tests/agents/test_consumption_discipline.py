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
4. **Bounded per-module widenings.** A module that has been argued a
   narrower extra prefix (:data:`MODULE_CCF_PREFIXES`) names **no
   capability symbol** from the modules it was admitted to — see that
   entry, and :data:`FABRIC_CAPABILITY_NAMES` for the list.

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
    # D-IMPL-77 (15-07): `validate_semver`, `VersionedArtifact` and
    # `ArtifactClass` moved out of `ccf.controlplane.artifacts` into this module
    # to break an import cycle. Admitting it *narrows* the consumption surface
    # rather than widening it: `artifact_base` imports nothing from `ccf` except
    # `ccf.contracts.base` — a constraint stated in its own module docstring and
    # the property it exists to hold — so it is strictly more constrained than
    # the `ccf.controlplane.artifacts` entry directly above, and reaches no
    # fabric layer at all.
    "ccf.controlplane.artifact_base",
    "ccf.controlplane.registry",
    # IN-01 (05-11): the shared pinned-resolution helper and the read-surface
    # Protocol it is typed against. Same tier as `ccf.controlplane.registry`
    # above — a read-only, exact-version Control Plane resolution surface
    # reaching no fabric layer, so binding it opens no path from Agent to
    # L1–L5. It exists so the factory and the grant ledger apply *one*
    # pinned-resolution rule rather than two copies that drift.
    "ccf.controlplane.resolution",
    "ccf.products.contract",
    "ccf.replay.record",
    # D-19 (06-03): the callable registry the factory injects and the agent
    # carries. Same tier as catalog/dispatch below — a boot-time key->callable
    # table with no fabric import of its own (its entire `ccf` import surface
    # is empty), so binding it opens no path from Agent to L1–L5. It is on
    # this list precisely *because* dispatch no longer resolves callables by
    # importing whatever a ref names.
    "ccf.skills.callables",
    # Channel 2 (05-06): the skill catalog/dispatch surface is Control Plane
    # mechanism above L6, not a fabric layer — binding it opens no path from
    # Agent to L1–L5 (CLAUDE.md §6.2; D-08).
    "ccf.skills.catalog",
    "ccf.skills.dispatch",
    # WR-03 (05-09): the typed bound_skills seam — BoundSkillView, whose only
    # producer is GrantLedger.bound_view. Grants are Control Plane skilling
    # mechanism above L6, same class as catalog/dispatch; binding it opens no
    # path from Agent to L1–L5.
    "ccf.skills.grants",
)

#: Per-module widenings of the surface above, argued **one module at a time**
#: rather than added to :data:`ALLOWED_CCF_PREFIXES`, so a prefix admitted for
#: one module does not silently become admissible for the whole package.
#:
#: ``assembler.py`` (plan ``15.5-10``; ``docs/DECISIONS.md`` D-IMPL-97 ruling 2)
#: is the producer seam: an assembler is a Protocol whose implementation is a
#: declared agent, so the surface has to be typed in the fabric's own value
#: vocabulary or it cannot state what it produces. Three prefixes, and the
#: argument is the same for each — **every symbol the module actually binds
#: from them is a frozen value contract, never a capability**:
#:
#: * ``ccf.projection.plan`` supplies :class:`Perspective`, which is
#:   specialization axis 3 itself — its own docstring says *"the agent
#:   framework binds to it in I.2 rather than replacing it"* — and
#:   ``ProjectionOutput``, a ``plan_id`` plus a payload.
#: * ``ccf.projection.acquisition`` supplies ``AcquiredContent``, the frozen
#:   content-addressed item that is the **only** route an enlisted agent's
#:   output may travel back into an assembly (whitepaper §7.6.6). The
#:   Alternation claim cannot be made without naming this exact type.
#: * ``ccf.products.request`` supplies ``ProductRequest`` (D-IMPL-98), which
#:   reaches no fabric layer at all: its own ``ccf`` imports are the products
#:   contract, the payload comparison, the skill argument schema and the
#:   Control Plane registry — every one of them already at or above L6.
#: * ``ccf.products.refusal`` supplies ``SubjectUnavailableRefusal``
#:   (``24.6-L-02`` / ``24.6-L-21``, ``D-IMPL-253`` amendment 2 (3)), and it is
#:   bound under ``TYPE_CHECKING`` only. ``D-IMPL-253`` narrowed
#:   ``AssemblyRefused`` to invariant failures, which means the Protocol's
#:   return annotation has to name the refusal VALUES the seam may return —
#:   LC-02's own complaint — and one of them lives in the delivery-contract
#:   module. The symbol bound is a frozen ``CCFContract`` with three scalar
#:   fields and no capability, exactly as the three above; claim 4 below still
#:   asserts this module names none of
#:   :data:`FABRIC_CAPABILITY_NAMES`, so admitting the module that holds the
#:   refusal vocabulary does not admit reaching for anything it imports.
#:
#: The widening is bounded rather than trusted: claim 4 asserts these modules
#: name none of :data:`FABRIC_CAPABILITY_NAMES`, so admitting the module that
#: *holds* ``ContentAcquirer`` and ``ProjectionPlan`` does not admit reaching
#: for either. A capability arriving through one of these doors is a red build.
MODULE_CCF_PREFIXES: dict[str, tuple[str, ...]] = {
    "assembler.py": (
        "ccf.projection.acquisition",
        "ccf.projection.plan",
        "ccf.products.refusal",
        "ccf.products.request",
    ),
}

#: The capability symbols reachable *from* the modules :data:`MODULE_CCF_PREFIXES`
#: admits, which a widened module must not name. ``ContentAcquirer`` fetches,
#: ``ContentAcquiringPlan`` and ``ProjectionPlan`` interpret a ``GraphView``,
#: and ``GraphView``/``OperatorOutput`` are the L3/L4 values Π is handed. None
#: of them may be named inside ``ccf.agents``: an assembler emits a value and
#: never drives the stage that produced it.
FABRIC_CAPABILITY_NAMES = frozenset(
    {
        "ContentAcquirer",
        "ContentAcquiringPlan",
        "GraphView",
        "OperatorOutput",
        "ProjectionEngine",
        "ProjectionPlan",
    }
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
    permitted = ALLOWED_CCF_PREFIXES + MODULE_CCF_PREFIXES.get(module_path.name, ())
    for module in sorted(_ccf_imports(module_path.read_text())):
        assert module.startswith(permitted), (
            f"{module_path} imports {module!r}, which is outside the agents"
            " package's permitted consumption surface — no path from Agent"
            " to L1–L5 (AGNT-01; CLAUDE.md §10; DESIGN.md §3.1)"
        )


@pytest.mark.parametrize(
    "module_path",
    sorted(AGENTS_PACKAGE.glob("*.py")),
    ids=lambda p: p.name,
)
def test_a_widened_module_names_no_fabric_capability(module_path: Path) -> None:
    """Claim 4: a per-module widening admits values, never capabilities.

    ``MODULE_CCF_PREFIXES`` admits the modules that *hold* ``ContentAcquirer``
    and ``ProjectionPlan`` because the frozen value contracts an assembler has
    to name live beside them. This is what keeps that from being a door: the
    widened module may not name a capability from behind it, and the check runs
    over every module in the package so the boundary cannot be crossed
    elsewhere either (AGNT-01).

    **Three node kinds, not one.** ``ast.Name`` alone was the shipped shape and
    it is not sufficient, because ``MODULE_CCF_PREFIXES`` admits *module*
    imports: ``import ccf.projection.acquisition as acquisition`` is permitted
    for ``assembler.py``, and ``acquisition.ContentAcquirer`` after it is an
    ``ast.Attribute`` that no ``ast.Name`` scan sees. ``getattr(acquisition,
    "ContentAcquirer")`` is a third spelling of the same reach, invisible to
    both. All three are collected here.

    The ``getattr`` leg is deliberately narrow — only the literal second
    argument of a ``getattr`` call, never every string constant in the module.
    A module-wide constant scan would match this suite's own prose and the
    capability names in :data:`FABRIC_CAPABILITY_NAMES`'s doc comment, which
    would make the check fire on its own documentation rather than on a reach.

    Found by the Phase 15.5 close-time cross-AI panel, independently by two
    reviewers (`15.5-CLOSE-REVIEWS.md`, findings P2/C2). Plan `15.5-10`'s own
    executor flagged this widening as the change deserving a reviewer's eye;
    the widening stands and the check behind it is what changed.
    """
    tree = ast.parse(module_path.read_text())
    named = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        alias.asname or alias.name.rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } | {
        node.args[1].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    }
    reached = sorted(named & FABRIC_CAPABILITY_NAMES)
    assert reached == [], (
        f"{module_path} names fabric capability symbol(s) {reached!r}; the"
        " agents package binds L5 *values* and never the stage that produced"
        " them — an assembler emits a value, it does not drive Π"
        " (AGNT-01; CLAUDE.md §10; DESIGN.md §3.1)"
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
