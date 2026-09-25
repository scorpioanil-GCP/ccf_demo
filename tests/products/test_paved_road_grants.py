"""The paved road grants nothing (D-IMPL-353 §1.6; D-IMPL-354): a declared skill not in force is refused by name.

Until this lane, :func:`~ccf.products.product.open_product`'s derived consumer
chain requested one ``skill.grant`` per declared skill on the deployment's
behalf — the agent granting itself. A grant requires ``Authorized[SkillGrant]``,
a door kind ``mint_at_composition`` refuses, so the road now READS which
declared skills are bound to the agent and refuses when one is not.

Driven through :func:`~ccf.products.product._derive_consumer_chain` directly,
with the agent's key overridden to the ``{tenant}/{class}/{name}`` grammar the
registry enforces (the road's default derived keys are bare — a design gap
reported separately, not papered over here), so the control isolates the grant
question from the key-grammar question.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    PRODUCT_CLASS,
    ProductClassDeclaration,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.classes import resolve_artifact_class
from ccf.deployment.config import derive_deployment
from ccf.deployment.manifest import register_manifest_entries
from ccf.products.child_resolver import QuestionBoundChildResolver
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS, CHILD_QUESTION_CLASS
from ccf.products.product import GrantNotInForce, _derive_consumer_chain
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry
from ccf.skills.dispatch import McpSkillRegistry
from ccf.skills.grants import GrantLedger, RefusingApprovalSink, SkillGrant

from tests.composition import declaring_store
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import AGENT_NAME, CONSUMER_TENANT, SKILL
from tests.skills.authority import grant_capability

CLOCK = datetime(2026, 3, 2, 12, 7, tzinfo=UTC)


def _derived() -> Any:
    config = fixture.consumer_config(
        agent=fixture.agent_section(key=f"{CONSUMER_TENANT}/{AGENT_DEFINITION.class_id}/{AGENT_NAME}")
    )
    return derive_deployment(parse_artifact(config, DEPLOYMENT_CONFIG))  # type: ignore[arg-type]


def _chain(derived: Any, registry: ControlPlaneRegistry, store: Any) -> tuple[AgentDefinition, QuestionBoundChildResolver]:
    declaration = parse_artifact(derived.documents[derived.keys.product_class], PRODUCT_CLASS)
    assert isinstance(declaration, ProductClassDeclaration)
    return _derive_consumer_chain(
        derived,
        declaration=declaration,
        registry=registry,
        store=store,
        mcp_skills=McpSkillRegistry(audit_log=registry.audit_log, clock=lambda: CLOCK),
        questions=fixture.questions,
        clock=lambda: CLOCK,
        approval_sink=None,
    )


def _store(tmp_path: pathlib.Path) -> Any:
    return declaring_store(
        tmp_path / "artifacts", fixture.RECORD_CLASS, fixture.QUERY_PIN_CLASS,
        ADMITTED_CHILD_CONTRACT_CLASS, CHILD_QUESTION_CLASS,
    )


def test_a_declared_skill_nobody_granted_is_refused_by_name_and_no_grant_is_made(tmp_path: pathlib.Path) -> None:
    derived = _derived()
    registry = ControlPlaneRegistry()
    with pytest.raises(GrantNotInForce, match=SKILL):
        _chain(derived, registry, _store(tmp_path))
    # The road registered the declared artifacts (composition-time `Register`)
    # and requested NOTHING: no grant transition of any kind is on the log.
    actions = {e.action for e in registry.audit_events()}
    assert "composition" in actions
    assert not any(a.startswith("grant_") for a in actions), sorted(actions)


def test_a_skill_granted_through_the_ledger_by_an_authorized_principal_composes(tmp_path: pathlib.Path) -> None:
    derived = _derived()
    registry = ControlPlaneRegistry()
    keys = derived.keys
    wanted = frozenset({keys.policy_bundle, keys.agent, *keys.skills})
    parsed = {
        entry.key: parse_artifact(derived.documents[entry.key], resolve_artifact_class(entry.class_id))
        for entry in derived.manifest.artifacts
        if entry.key in wanted
    }
    register_manifest_entries(derived.manifest, parsed, registry=registry, only=wanted)
    agent = parsed[keys.agent]
    assert isinstance(agent, AgentDefinition)
    entry = parsed[keys.skills[0]]
    assert isinstance(entry, SkillCatalogEntry)
    ledger = GrantLedger(control_plane=registry, catalog=SkillCatalog(registry), sink=RefusingApprovalSink(), clock=lambda: CLOCK)
    # The grant is a DOOR action: the capability is minted the way the gate mints
    # it, from an allowed decision for the agent definition key — never by the road.
    outcome = ledger.request(
        grant_capability(agent, principal="an-authorized-operator"),
        SkillGrant(
            schema_version=entry.schema_version, artifact_version=entry.artifact_version,
            name=entry.name, tenant=entry.tenant, agent_definition_hash=content_hash(agent),
            skill_name=entry.name, skill_version=entry.artifact_version,
        ),
        definition=agent,
    )
    assert isinstance(outcome, str), outcome

    composed_agent, children = _chain(derived, registry, _store(tmp_path))
    assert composed_agent == agent
    assert isinstance(children, QuestionBoundChildResolver)
