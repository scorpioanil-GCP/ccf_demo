"""The D-01 agent vertical slice: YAML definition → factory → Agent → fabric → replay.

The I.2 counterpart of the proto-quickstart: one banking agent definition
(``covenant_analytics.yaml``, D-02) registered through the Control Plane,
constructed via ``AgentFactory`` (the only path, CLAUDE.md §6.4), driven
against the real I.1 banking fabric by the D-03 test-double harness — one
Context Product consumption, one skill-invocation attempt against the empty
bound set, one effect emission as a returned typed value — with replay
dimension 4 carrying the complete D-06 field set.

Per invariant, what would fail here:

=================================================  ===========================
Invariant                                          What would fail here
=================================================  ===========================
factory-only construction (CLAUDE.md §6.4, D-12)   the agent below exists only
                                                   through the factory from
                                                   fixture artifacts
agent identity = content hash (D-05/D-06)          dimension 4 would disagree
                                                   with content_hash(definition)
single-writer across the agent seam (§10)          the emitted effect is a
                                                   value; no write handle exists
consumption discipline (INV-CH6-05)                an out-of-contract or
                                                   expired product would pass
no shipped loop (CLAUDE.md §7.3, D-03)             the double's source would
                                                   contain a turn loop or a
                                                   harness import
=================================================  ===========================

All domain values live in ``tests/fixtures/banking/*.yaml``; the fabric
wiring helpers are reused from the proto-quickstart module rather than
re-implemented.
"""

from __future__ import annotations

import ast
import inspect
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator

import pytest
import yaml

from agents import harness_double
from agents.harness_double import drive_slice
from ccf.agents.agent import Agent, EmittedEffect
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.agents.errors import FalseGrantClaimError, SkillNotBound
from ccf.agents.factory import AgentFactory
from ccf.artifacts.protocol import artifact_uri
from ccf.boot import boot
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.gates import ServableProduct, run_gates
from ccf.replay.record import (
    NO_GRANTS_SET_HASH,
    PolicyBinding,
    build_replay_record,
)
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.dispatch import (
    McpInvocation,
    McpSkillRegistry,
    McpSkillUnregistered,
    ToolInvocation,
)
from ccf.skills.grants import GrantLedger, SkillGrant
from skills.sinks import ScriptedApprovalSink
from skills.test_dispatch import _RecordingClient
from integration.test_proto_quickstart import (
    _Fabric,
    _candidate,
    _envelopes,
    _execute,
    _instant,
    _load,
    _product_class,
    _resolution_spec,
)
from ccf.projection.plan import Perspective

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _agent_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "agents" / "covenant_analytics.yaml").read_text()
    )
    return loaded


def _prompt_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "prompts" / "covenant_summary.yaml").read_text()
    )
    return loaded


@pytest.fixture(scope="module")
def ontology() -> Any:
    return _load("ontology.yaml")


@pytest.fixture(scope="module")
def control() -> Any:
    return _load("controlplane.yaml")


@pytest.fixture(scope="module")
def events() -> Any:
    return _load("events.yaml")


@pytest.fixture
def fabric(
    tmp_path: Path, ontology: Any, control: Any, events: Any
) -> Iterator[_Fabric]:
    """The I.1 banking fabric, booted and ingested exactly as in I.1."""
    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(
        keys["policy_bundle"], control["policy_bundle"]
    )
    handle = boot(
        database_path=tmp_path / "acme-bank.sqlite3",
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        yield _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
    finally:
        handle.close()


def _register_agent_artifacts(fabric: _Fabric) -> tuple[str, str, AgentDefinition]:
    """Register definition, prompt, and referenced artifacts; return key/version."""
    agent_fixture = _agent_fixture()
    prompt_fixture = _prompt_fixture()
    registry = fabric.registry
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    registry.register_typed(
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    for reference in agent_fixture["referenced_artifacts"].values():
        artifact_class = declared_artifact_class(reference["class_id"])
        declared = parse_artifact(
            {
                "class_id": reference["class_id"],
                "semver": reference["semver"],
                "declaration": reference["declaration"],
            },
            artifact_class,
        )
        registry.register_typed(reference["key"], declared, artifact_class)
    definition = parse_artifact(
        agent_fixture["agent_definition"], AGENT_DEFINITION
    )
    assert isinstance(definition, AgentDefinition)
    key = agent_fixture["keys"]["agent_definition"]
    version = registry.register_versioned(key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    return key, version, definition


def _constructed_agent(fabric: _Fabric) -> tuple[Agent, AgentDefinition]:
    key, version, definition = _register_agent_artifacts(fabric)
    factory = AgentFactory(control_plane=fabric.registry)
    return (
        factory.construct(definition_key=key, definition_version=version),
        definition,
    )


def _servable(fabric: _Fabric) -> ServableProduct:
    execution = _execute(fabric)
    product_class = _product_class(fabric)
    gated = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)
    return gated


# --- the slice runs end to end --------------------------------------------------


def test_the_fixture_agent_runs_the_three_seams_against_the_fabric(
    fabric: _Fabric,
) -> None:
    agent, definition = _constructed_agent(fabric)
    gated = _servable(fabric)
    slice_values = _agent_fixture()["slice"]
    consumed, unbound, effect = drive_slice(
        agent=agent,
        product=gated.product,
        now=fabric.now,
        skill_name=slice_values["skill_name"],
        effect_payload=dict(slice_values["effect_payload"]),
    )
    assert consumed is gated.product
    assert isinstance(unbound, SkillNotBound)  # ungranted name — the negative
    assert isinstance(effect, EmittedEffect)
    assert effect.agent_definition_hash == content_hash(definition)
    assert effect.payload == slice_values["effect_payload"]


def test_an_expired_product_is_refused_at_the_consumption_seam(
    fabric: _Fabric,
) -> None:
    """INV-CH6-05 against the real fabric: expired means contract-invalid."""
    agent, _definition = _constructed_agent(fabric)
    gated = _servable(fabric)
    late = gated.product.expires_at + timedelta(seconds=1)
    with pytest.raises(Exception) as excinfo:
        agent.consume(gated.product, now=late)
    assert type(excinfo.value).__name__ == "ConsumptionRefused"


# --- replay dimension 4 (D-06) ---------------------------------------------------


def test_dimension_4_carries_the_complete_d06_field_set(fabric: _Fabric) -> None:
    agent, definition = _constructed_agent(fabric)
    gated = _servable(fabric)
    execution = _execute(fabric)
    perspective_values = fabric.control["perspective"]
    principal_id = perspective_values["principal_id"]
    record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=Perspective(
            principal_id=principal_id, role=perspective_values["role"]
        ),
        policy_bindings=(
            PolicyBinding(
                key=fabric.control["keys"]["policy_bundle"],
                version=fabric.policy_version,
            ),
        ),
        assembly_mode=fabric.control["product_class"]["assembly_mode"],
        recorded_at=fabric.now,
        agent_conditioning=agent.perspective_conditioning(
            principal_id=principal_id, grant_set_hash=NO_GRANTS_SET_HASH
        ),
    )
    conditioning = record.perspective_conditioning
    assert conditioning.principal_id == principal_id
    assert conditioning.role == definition.perspective.role
    assert conditioning.agent_definition_hash == content_hash(definition)
    assert conditioning.agent_definition_uri == artifact_uri(
        tenant_id=definition.tenant,
        artifact_class=AGENT_DEFINITION.class_id,
        name=definition.name,
        artifact_version=definition.artifact_version,
    )
    assert conditioning.archetype_composition == ("analytics_insights",)
    assert conditioning.grant_set_hash == NO_GRANTS_SET_HASH
    assert conditioning.delegation_chain == (principal_id,)


# --- channel 2: a real granted skill through the seam (05-06; D-07/D-08) ----------


def _granted_agent(
    fabric: _Fabric,
) -> tuple[Agent, AgentDefinition, GrantLedger, dict[str, Any]]:
    """Grant the fixture tool skill to the fixture agent through the ledger."""
    key, version, definition = _register_agent_artifacts(fabric)
    granted_values: dict[str, Any] = _agent_fixture()["slice"]["granted_skill"]
    catalog = SkillCatalog(fabric.registry)
    tool_fixture: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "skills" / "covenant_metrics_tool.yaml").read_text()
    )
    entry = parse_artifact(tool_fixture["entry"], SKILL_CATALOG_ENTRY)
    assert isinstance(entry, SkillCatalogEntry)
    assert isinstance(catalog.register(entry), str)
    ledger = GrantLedger(
        control_plane=fabric.registry,
        catalog=catalog,
        # The registry's own log, shared (WR-07): one audit plane, one
        # sequence, across registration and grant lifecycle.
        audit=fabric.registry.audit_log,
        sink=ScriptedApprovalSink(
            approve=True, approver_id=granted_values["approver_id"]
        ),
        clock=lambda: fabric.now,
    )
    grant = SkillGrant(
        agent_definition_hash=content_hash(definition),
        **granted_values["grant"],
    )
    outcome = ledger.request(
        grant, definition=definition, actor=granted_values["requesting_actor"]
    )
    assert isinstance(outcome, str)
    factory = AgentFactory(control_plane=fabric.registry)
    agent = factory.construct(
        definition_key=key,
        definition_version=version,
        bound_skills=ledger.bound_view(content_hash(definition)),
    )
    return agent, definition, ledger, granted_values


def _mcp_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "skills" / "document_fetch_mcp.yaml").read_text()
    )
    return loaded


def _mcp_granted_agent(
    fabric: _Fabric, *, wire_registry: bool
) -> tuple[Agent, _RecordingClient, dict[str, Any]]:
    """Grant the in-scope ``mcp`` fixture entry and construct through the factory.

    ``wire_registry`` is the whole experiment: the *same* grant, the same
    catalog entry and the same agent definition, with the registry threaded or
    not. Everything else being equal is what makes the pair an inversion rather
    than two unrelated observations.

    The client is a double rather than a live server because what is under test
    is the *wiring* — that the registry the composition root gave the factory
    reaches dispatch. The live MCP read is proved in
    ``tests/crossproc/test_mcp_ingress.py``.
    """
    key, version, definition = _register_agent_artifacts(fabric)
    mcp = _mcp_fixture()
    declared: dict[str, Any] = mcp["agent_invocable"]
    client = _RecordingClient(contents=mcp["dispatch"]["contents"])
    registry = McpSkillRegistry(
        audit_log=fabric.registry.audit_log, clock=lambda: fabric.now
    )
    registry.register(
        server=mcp["deployment"]["server"],
        client=client,
        resources=mcp["deployment"]["resources"],
    )

    catalog = SkillCatalog(fabric.registry)
    entry = parse_artifact(declared["entry"], SKILL_CATALOG_ENTRY)
    assert isinstance(entry, SkillCatalogEntry)
    assert isinstance(catalog.register(entry), str)
    ledger = GrantLedger(
        control_plane=fabric.registry,
        catalog=catalog,
        audit=fabric.registry.audit_log,
        sink=ScriptedApprovalSink(
            approve=True, approver_id=declared["approver_id"]
        ),
        clock=lambda: fabric.now,
    )
    grant = SkillGrant(
        agent_definition_hash=content_hash(definition), **declared["grant"]
    )
    outcome = ledger.request(
        grant, definition=definition, actor=declared["requesting_actor"]
    )
    assert isinstance(outcome, str), outcome

    factory = AgentFactory(
        control_plane=fabric.registry,
        mcp_skills=registry if wire_registry else None,
    )
    agent = factory.construct(
        definition_key=key,
        definition_version=version,
        bound_skills=ledger.bound_view(content_hash(definition)),
    )
    return agent, client, declared


def test_a_granted_mcp_skill_is_invocable_through_the_agent_seam(
    fabric: _Fabric,
) -> None:
    """Dave, 2026-07-27: the registry reaches dispatch from the factory.

    Harness skill exposure (CLAUDE.md §7.3 seam 2) surfaces the agent's
    currently-bound skill-set as the harness's tools, which is only meaningful
    if an exposed skill is actually invocable. Before the threading, an ``mcp``
    skill invoked through an ``Agent`` refused with ``McpSkillUnregistered``
    however the deployment was wired.

    What would fail here: dropping ``mcp_skills`` anywhere along
    ``AgentFactory`` → ``Agent`` → ``dispatch_skill``. The read landing on the
    URI the *deployment* registered — never anything spelled in the artifact —
    is also asserted, so a threading that arrived by fabricating an endpoint
    would fail here too (T-06-24).
    """
    agent, client, declared = _mcp_granted_agent(fabric, wire_registry=True)
    mcp = _mcp_fixture()

    invocation = agent.invoke_skill(
        declared["grant"]["skill_name"], arguments=declared["arguments"]
    )

    assert isinstance(invocation, McpInvocation)
    assert invocation.skill_name == declared["entry"]["name"]
    assert invocation.server == declared["entry"]["binding"]["server"]
    assert invocation.contents == mcp["dispatch"]["contents"]
    assert dict(invocation.arguments) == declared["arguments"]
    assert client.reads == [
        mcp["deployment"]["resources"][declared["entry"]["binding"]["resource"]]
    ]


def test_an_unwired_deployment_still_refuses_an_mcp_skill_by_name(
    fabric: _Fabric,
) -> None:
    """The inversion, and the fail-closed half of the same ruling.

    Same grant, same entry, same agent — only the registry withheld. What would
    fail here: an ``Agent`` that manufactured a client of its own when the
    deployment wired none, which would be the SDK choosing an endpoint
    (CINV-01). Without this case the test above would pass equally well against
    an implementation that had stopped fail-closing.
    """
    agent, client, declared = _mcp_granted_agent(fabric, wire_registry=False)

    with pytest.raises(McpSkillUnregistered):
        agent.invoke_skill(
            declared["grant"]["skill_name"], arguments=declared["arguments"]
        )
    assert client.reads == []


def test_a_granted_skill_dispatches_through_the_agent_seam(
    fabric: _Fabric,
) -> None:
    """Channel 2 live: the granted tool exists from the agent's view and
    dispatches; an ungranted name still does not exist (CLAUDE.md §6.2)."""
    agent, _definition, _ledger, granted_values = _granted_agent(fabric)
    invocation = agent.invoke_skill(
        granted_values["grant"]["skill_name"],
        arguments=granted_values["arguments"],
    )
    assert isinstance(invocation, ToolInvocation)
    assert dict(invocation.arguments) == granted_values["arguments"]
    with pytest.raises(SkillNotBound):
        agent.invoke_skill(_agent_fixture()["slice"]["skill_name"])


def test_a_granted_decision_captures_the_grant_set_hash_in_dimension_4(
    fabric: _Fabric,
) -> None:
    """CINV-04 skill-set-capture, active form (D-10): the in-force D-07
    grant-set hash lands in replay dimension 4 by construction, and a
    post-revocation decision carries the updated (no-grants) claim —
    while the agent's definition hash never moves (channel separation)."""
    agent, definition, ledger, granted_values = _granted_agent(fabric)
    gated = _servable(fabric)
    execution = _execute(fabric)
    perspective_values = fabric.control["perspective"]
    principal_id = perspective_values["principal_id"]

    def _record() -> Any:
        return build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=Perspective(
                principal_id=principal_id, role=perspective_values["role"]
            ),
            policy_bindings=(
                PolicyBinding(
                    key=fabric.control["keys"]["policy_bundle"],
                    version=fabric.policy_version,
                ),
            ),
            assembly_mode=fabric.control["product_class"]["assembly_mode"],
            recorded_at=fabric.now,
            agent_conditioning=agent.perspective_conditioning(
                principal_id=principal_id,
                grant_set_hash=ledger.grant_set_hash(content_hash(definition)),
            ),
        )

    granted_record = _record()
    in_force = ledger.grant_set_hash(content_hash(definition))
    assert in_force != NO_GRANTS_SET_HASH
    assert granted_record.perspective_conditioning.grant_set_hash == in_force
    assert granted_record.perspective_conditioning.agent_definition_hash == (
        content_hash(definition)
    )

    grant = SkillGrant(
        agent_definition_hash=content_hash(definition),
        **granted_values["grant"],
    )
    ledger.revoke(content_hash(grant), actor=granted_values["requesting_actor"])
    revoked_record = _record()
    assert revoked_record.perspective_conditioning.grant_set_hash == (
        NO_GRANTS_SET_HASH
    )
    assert revoked_record.perspective_conditioning.agent_definition_hash == (
        content_hash(definition)
    )


def test_a_false_zero_grants_claim_is_refused_on_a_skilled_agent(
    fabric: _Fabric,
) -> None:
    """WR-01: an agent with a non-empty bound skill-set refuses the positive
    zero-grants claim — no supported path records a false dimension-4 record."""
    agent, _definition, _ledger, _granted_values = _granted_agent(fabric)
    perspective_values = fabric.control["perspective"]
    with pytest.raises(FalseGrantClaimError):
        agent.perspective_conditioning(
            principal_id=perspective_values["principal_id"],
            grant_set_hash=NO_GRANTS_SET_HASH,
        )


def test_the_double_drives_a_granted_skill_without_the_typed_error(
    fabric: _Fabric,
) -> None:
    """The double's granted path (IN-02): with a governed grant in force the
    bound name exists from the agent's view, so ``unbound`` is ``None``."""
    agent, definition, _ledger, granted_values = _granted_agent(fabric)
    gated = _servable(fabric)
    slice_values = _agent_fixture()["slice"]
    consumed, unbound, effect = drive_slice(
        agent=agent,
        product=gated.product,
        now=fabric.now,
        skill_name=granted_values["grant"]["skill_name"],
        effect_payload=dict(slice_values["effect_payload"]),
    )
    assert consumed is gated.product
    assert unbound is None
    assert effect.agent_definition_hash == content_hash(definition)


# --- the double stays a linear script (D-03) --------------------------------------


def test_the_double_is_linear_and_imports_no_harness() -> None:
    source = inspect.getsource(harness_double)
    tree = ast.parse(source)
    loops = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.While, ast.For, ast.AsyncFor))
    ]
    assert not loops, "the D-03 double must never loop over agent turns"
    for forbidden in ("import adk", "import langgraph", "claude_agent"):
        assert forbidden not in source
