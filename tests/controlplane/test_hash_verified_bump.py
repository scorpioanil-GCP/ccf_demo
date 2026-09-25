"""D-05 hash-verified version bump at registration (CLAUDE.md §6.4; D-IMPL-26).

Written before the implementation per the TDD discipline. The four-outcome
table under test:

===========================  ======================  =========================
content vs bound hash        artifact_version        outcome
===========================  ======================  =========================
identical                    unchanged               idempotent no-op (version)
changed                      unchanged               ``RefuseUnbumpedChange``
identical                    bumped                  ``RefuseEmptyBump``
changed                      bumped                  appended new version
===========================  ======================  =========================

Refusals are **returned typed values** in the ``GateRefusal`` style, never
exceptions — and every outcome, refusals included, lands in the audit log
(``resolved=False`` for refusals; T-05-04). ``ControlPlaneMissing`` behavior
is unchanged.

The versioned artifact exercised here is the banking fixture agent definition;
its content lives in YAML, not in this module (No-Hardcoding Rule, §6.4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import (
    ControlPlaneMissing,
    ControlPlaneRegistry,
    RefuseEmptyBump,
    RefuseUnbumpedChange,
)
from ccf.authz.capability import Authorized, Register
from tests.controlplane.capabilities import register_capability

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "banking"
    / "agents"
    / "covenant_analytics.yaml"
)

KEY = "acme-bank/agents/covenant-analytics"



def _cap(key: str) -> Authorized[Register]:
    """A ``config.register`` capability for ``key``, minted as the gate would."""
    return register_capability(key, Register)

def _definition(**overrides: Any) -> AgentDefinition:
    loaded = yaml.safe_load(FIXTURE.read_text())
    definition = parse_artifact(loaded["agent_definition"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    if overrides:
        definition = definition.model_copy(update=overrides)
    return definition


# --- the four outcomes -------------------------------------------------------


def test_same_content_same_version_is_idempotent() -> None:
    registry = ControlPlaneRegistry()
    definition = _definition()
    first = registry.register_versioned(_cap(KEY), definition, AGENT_DEFINITION)
    second = registry.register_versioned(_cap(KEY), definition, AGENT_DEFINITION)
    assert first == content_hash(definition)
    assert second == first
    assert registry.versions(KEY) == (first,)


def test_changed_content_without_a_bump_is_refused() -> None:
    registry = ControlPlaneRegistry()
    original = _definition()
    registry.register_versioned(_cap(KEY), original, AGENT_DEFINITION)
    drifted = _definition(name="covenant-analytics-drifted")
    refusal = registry.register_versioned(_cap(KEY), drifted, AGENT_DEFINITION)
    assert isinstance(refusal, RefuseUnbumpedChange)
    assert refusal.key == KEY
    assert refusal.artifact_version == original.artifact_version
    assert refusal.existing_hash == content_hash(original)
    assert refusal.incoming_hash == content_hash(drifted)
    # nothing was appended
    assert registry.versions(KEY) == (content_hash(original),)


def test_a_bump_without_a_content_change_is_refused() -> None:
    registry = ControlPlaneRegistry()
    original = _definition()
    registry.register_versioned(_cap(KEY), original, AGENT_DEFINITION)
    rebadged = _definition(artifact_version="1.1.0")
    refusal = registry.register_versioned(_cap(KEY), rebadged, AGENT_DEFINITION)
    assert isinstance(refusal, RefuseEmptyBump)
    assert refusal.key == KEY
    assert refusal.artifact_version == "1.1.0"
    assert refusal.existing_version == original.artifact_version
    assert registry.versions(KEY) == (content_hash(original),)


def test_changed_content_with_a_bump_appends_a_new_version() -> None:
    registry = ControlPlaneRegistry()
    original = _definition()
    first = registry.register_versioned(_cap(KEY), original, AGENT_DEFINITION)
    revised = _definition(
        name="covenant-analytics-v2", artifact_version="1.1.0"
    )
    second = registry.register_versioned(_cap(KEY), revised, AGENT_DEFINITION)
    assert second == content_hash(revised)
    assert registry.versions(KEY) == (first, second)
    assert registry.resolve(KEY, second) == revised


# --- refusals are values, and everything is audited ---------------------------


def test_refusals_are_contract_values_not_exceptions() -> None:
    registry = ControlPlaneRegistry()
    registry.register_versioned(_cap(KEY), _definition(), AGENT_DEFINITION)
    outcome = registry.register_versioned(_cap(KEY), _definition(name="drift"), AGENT_DEFINITION
    )
    assert isinstance(outcome, CCFContract)
    assert not isinstance(outcome, Exception)


def test_every_outcome_is_audited_including_refusals() -> None:
    registry = ControlPlaneRegistry()
    registry.register_versioned(_cap(KEY), _definition(), AGENT_DEFINITION)  # append
    registry.register_versioned(_cap(KEY), _definition(), AGENT_DEFINITION)  # no-op
    registry.register_versioned(_cap(KEY), _definition(name="drift"), AGENT_DEFINITION
    )  # RefuseUnbumpedChange
    registry.register_versioned(_cap(KEY), _definition(artifact_version="2.0.0"), AGENT_DEFINITION
    )  # RefuseEmptyBump
    events = [
        event
        for event in registry.audit_events()
        if event.action == "register_versioned"
    ]
    assert len(events) == 4
    assert [event.resolved for event in events] == [True, True, False, False]


def test_control_plane_missing_behavior_is_unchanged() -> None:
    registry = ControlPlaneRegistry()
    with pytest.raises(ControlPlaneMissing):
        registry.resolve(KEY, "0" * 64)
    with pytest.raises(ControlPlaneMissing):
        registry.resolve_latest(KEY)
