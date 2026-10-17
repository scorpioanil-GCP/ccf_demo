# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Dimension 4 names the composing agent and the skill-set it held (`D-IMPL-385`; Dave, 2026-10-16 15:25, option C).

CLAUDE.md §6.2: *"which agent, which version, which configuration, which
skill-set made this decision is answerable from replay alone."* Before this, a
paved composite whose agent held grants in force recorded ``no-agent`` and
``no-grants`` in dimension 4, because nothing handed the record builder the
agent (gap 2 of the skills feasibility probe, 2026-10-16).

Held here, over the paved consumer fixture (a composite asking a local
producer subprocess; no estate):

* a served decision's dimension 4 carries the agent definition's content hash,
  its versioned URI, its archetypes, and the grant-set hash the ledger reports —
  never the zero-grants claim while a grant is in force;
* principal and role stay the CALLER's: replay rebuilds the caller's viewpoint
  from them;
* after a revocation, the next decision records the new skill-set (here, none)
  and still names the agent; the earlier record keeps the set it had;
* a decision with no agent (a non-composite product) keeps the no-agent claims;
* a child resolver handed an agent that is not the one it resolves grants for
  is refused at construction.
"""

from __future__ import annotations

import pathlib

import pytest

from ccf.agents.definitions import AGENT_DEFINITION
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.child_resolver import GrantBoundChildResolver
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import NO_AGENT_DEFINITION, NO_GRANTS_SET_HASH
from ccf.replay.serve import ServedProduct
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger, RefusingApprovalSink

from tests.composition import declare_wide_temporal_boundary
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import SKILL
from tests.products.test_paved_consumer import (  # noqa: F401 - `producer_url` is a fixture
    _open,
    _question,
    _tree,
    producer_url,
)
from tests.skills.authority import revoke_capability


def _plane() -> ControlPlaneRegistry:
    registry = ControlPlaneRegistry()
    declare_wide_temporal_boundary(registry, tenant_id=fixture.CONSUMER_TENANT)
    return registry


def _ledger(opened) -> GrantLedger:  # type: ignore[no-untyped-def]
    return GrantLedger(
        control_plane=opened.control_plane,
        catalog=SkillCatalog(opened.control_plane),
        sink=RefusingApprovalSink(),
        clock=lambda: fixture.ADMITTED_AT,
    )


def _opened(tmp_path: pathlib.Path, url: str):  # type: ignore[no-untyped-def]
    config = fixture.consumer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER, grants=[SKILL])
    return _open(_tree(tmp_path, config=config), tmp_path / "scratch", url, control_plane=_plane())


def test_a_served_composite_decision_names_its_agent_and_the_skill_set_in_force(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    with _opened(tmp_path, producer_url) as opened:
        agent = opened.agent
        assert agent is not None
        in_force = _ledger(opened).grant_set_hash(content_hash(agent))
        assert in_force != NO_GRANTS_SET_HASH, "the fixture's declared grant is not in force"

        caller = opened.default_perspective
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        conditioning = opened.record_of(served).perspective_conditioning

    assert conditioning.agent_definition_hash == content_hash(agent)
    assert conditioning.agent_definition_uri == artifact_uri(
        tenant_id=agent.tenant,
        artifact_class=AGENT_DEFINITION.class_id,
        name=agent.name,
        artifact_version=agent.artifact_version,
    )
    assert conditioning.archetype_composition == agent.archetypes
    assert conditioning.grant_set_hash == in_force
    # The caller's viewpoint, unchanged: replay conditions on these two.
    assert (conditioning.principal_id, conditioning.role) == (caller.principal_id, caller.role)
    assert conditioning.delegation_chain == (caller.principal_id,)


def test_after_a_revocation_the_next_decision_records_the_new_skill_set_and_the_old_keeps_its_own(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    with _opened(tmp_path, producer_url) as opened:
        agent = opened.agent
        assert agent is not None
        agent_hash = content_hash(agent)
        ledger = _ledger(opened)
        before = ledger.grant_set_hash(agent_hash)

        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)

        grant_hash = ledger.bound_view(agent_hash).grant_hash_for(SKILL)
        ledger.revoke(revoke_capability(grant_hash, tenant=agent.tenant))
        assert ledger.grant_set_hash(agent_hash) == NO_GRANTS_SET_HASH

        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        after = opened.record_of(refused).perspective_conditioning
        earlier = opened.record_of(served).perspective_conditioning

    assert after.agent_definition_hash == agent_hash, "the agent still made the decision"
    assert after.grant_set_hash == NO_GRANTS_SET_HASH, "it held no grant when it made it"
    assert earlier.grant_set_hash == before != NO_GRANTS_SET_HASH, "the earlier record keeps its own set"


def test_a_decision_with_no_agent_keeps_the_no_agent_claims(tmp_path: pathlib.Path) -> None:
    """Control: a non-composite paved product has no agent, and says so."""
    from tests.replay.test_replay_evidence_383 import _open_run
    from tests.products.test_paved_road import _question as _plain_question
    from tests.products.test_paved_road import _write_tree

    with _open_run(_write_tree(tmp_path), tmp_path / "evidence") as opened:
        assert opened.agent is None
        served = opened.answer(_plain_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        conditioning = opened.record_of(served).perspective_conditioning
    assert conditioning.agent_definition_hash == NO_AGENT_DEFINITION
    assert conditioning.grant_set_hash == NO_GRANTS_SET_HASH
    assert conditioning.archetype_composition == ()


def test_a_child_resolver_handed_another_agent_is_refused_at_construction(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    with _opened(tmp_path, producer_url) as opened:
        agent = opened.agent
        assert agent is not None
        with pytest.raises(ValueError, match="agent_definition_hash"):
            GrantBoundChildResolver(
                ledger=_ledger(opened),
                agent_definition_hash="0" * 64,
                agent=agent,
                gate=None,  # type: ignore[arg-type] - refused before it is read
                child_arguments=lambda requirement, request: {},  # type: ignore[arg-type,misc]
                callable_registry=None,  # type: ignore[arg-type]
                artifact_store=None,  # type: ignore[arg-type]
            )
