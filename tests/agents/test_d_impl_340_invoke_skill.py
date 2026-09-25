"""`D-IMPL-340` — an agent's tool-style invocation cannot ask a producer.

An `mcp_product` skill is invoked by a composite's child resolver, which
carries the composite's effective request as a `ProductQuestion`; an agent's
`invoke_skill(name, arguments)` carries a string mapping and can pose no
question. The refusal is by name, before dispatch, so a harness that exposes a
granted `mcp_product` skill as a tool sees a typed refusal naming the reason
rather than dispatch's generic missing-question error.
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION
from ccf.agents.factory import AgentFactory
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.grants import GrantLedger, SkillGrant

from tests.skills.sinks import ScriptedApprovalSink
from tests.controlplane.composition import compose_register_versioned
from tests.agents.test_assembler import (  # noqa: F401 — `registry` is a fixture
    ASKED_AT,
    FIXTURES,
    _assembler_fixture,
    _definition,
    _fixture,
    _wide_regime_document,
    registry,
)


def _mcp_product_entry() -> SkillCatalogEntry:
    document: dict[str, Any] = yaml.safe_load(
        (FIXTURES.parent / "banking" / "skills" / "exposure_rollup_mcp_product.yaml").read_text()
    )
    entry = parse_artifact(document["entry"], SKILL_CATALOG_ENTRY)
    assert isinstance(entry, SkillCatalogEntry)
    return entry


def test_invoke_skill_refuses_an_mcp_product_entry_by_name(
    registry: ControlPlaneRegistry,
) -> None:
    granted_values = _fixture("covenant_analytics.yaml")["slice"]["granted_skill"]
    definition = _definition(_wide_regime_document(artifact_version="2.9.0"))
    key = _assembler_fixture()["keys"]["agent_definition"]
    version = compose_register_versioned(registry, key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    catalog = SkillCatalog(registry)
    entry = _mcp_product_entry()
    assert isinstance(catalog.register(entry), str)
    ledger = GrantLedger(
        control_plane=registry,
        catalog=catalog,
        audit=registry.audit_log,
        sink=ScriptedApprovalSink(approve=True, approver_id=granted_values["approver_id"]),
        clock=lambda: ASKED_AT,
    )
    definition_hash = content_hash(definition)
    grant_hash = ledger.request(
        SkillGrant(
            schema_version="1.0.0",
            artifact_version="1.0.0",
            name="covenant-analytics-exposure-rollup-ask",
            tenant=entry.tenant,
            agent_definition_hash=definition_hash,
            skill_name=entry.name,
            skill_version=entry.artifact_version,
        ),
        definition=definition,
        actor=granted_values["requesting_actor"],
    )
    assert isinstance(grant_hash, str), grant_hash
    agent = AgentFactory(control_plane=registry).construct(
        definition_key=key,
        definition_version=version,
        bound_skills=ledger.bound_view(definition_hash),
    )
    # Bound and visible — the harness would list it.
    assert agent.invoke_skill(entry.name) is entry or agent.invoke_skill(entry.name) == entry
    # Invoked with arguments: refused by name, before any dispatch.
    with pytest.raises(TypeError, match="mcp_product"):
        agent.invoke_skill(entry.name, arguments={"requested_by": "covenant-analyst"})
