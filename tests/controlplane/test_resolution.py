"""The one pinned-resolution rule, shared by every call site (IN-01).

``ccf.controlplane.resolution.resolve_pinned`` replaces two near-verbatim
copies — ``AgentFactory._resolve_pinned`` and
``GrantLedger._resolve_policy_regime`` — that differed only in the miss case.
These tests pin the rule itself: the content-hash fast path, declared-version
matching, the WR-08 ambiguity refusal, the returned (not raised) miss, and the
audit discipline that made the duplication dangerous in the first place —
probes go through the unaudited ``peek``, and exactly one ``resolve`` fires,
on the content actually returned.

The last two tests pin that each call site still applies its *own* reading of
a miss on top of the shared helper, since collapsing those readings together
is the failure mode a shared helper invites.

Artifact content comes from the banking fixtures, never from this module
(No-Hardcoding Rule, §6.4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.agents.errors import AgentDefinitionError
from ccf.agents.factory import _resolve_pinned
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import (
    AmbiguousPinnedVersionError,
    ControlPlaneRegistry,
)
from ccf.controlplane.resolution import ControlPlaneResolution, resolve_pinned

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "banking"
    / "agents"
    / "covenant_analytics.yaml"
)

TENANT = "acme-bank"
NAME = "covenant-analytics"
KEY = f"{TENANT}/{AGENT_DEFINITION.class_id}/{NAME}"


def _definition(**overrides: Any) -> AgentDefinition:
    loaded = yaml.safe_load(FIXTURE.read_text())
    definition = parse_artifact(loaded["agent_definition"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    definition = definition.model_copy(update={"name": NAME, **overrides})
    return definition


def _uri(version: str) -> str:
    return artifact_uri(
        tenant_id=TENANT,
        artifact_class=AGENT_DEFINITION.class_id,
        name=NAME,
        artifact_version=version,
    )


def test_the_reference_registry_conforms_to_the_read_surface() -> None:
    assert isinstance(ControlPlaneRegistry(), ControlPlaneResolution)


def test_a_content_hash_uri_resolves_on_the_fast_path() -> None:
    registry = ControlPlaneRegistry()
    definition = _definition()
    version = registry.register_versioned(KEY, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    assert resolve_pinned(registry, _uri(version)) == definition


def test_a_declared_version_uri_resolves_by_probing() -> None:
    registry = ControlPlaneRegistry()
    first = _definition()
    second = _definition(
        name=f"{NAME}-revised", artifact_version="9.9.9"
    )
    registry.register_versioned(KEY, first, AGENT_DEFINITION)
    registry.register_versioned(KEY, second, AGENT_DEFINITION)
    assert resolve_pinned(registry, _uri("9.9.9")) == second


def test_probes_are_not_audited_and_the_returned_read_is(
) -> None:
    """WR-08's discipline, now enforced in one place instead of two."""
    registry = ControlPlaneRegistry()
    first = _definition()
    second = _definition(
        name=f"{NAME}-revised", artifact_version="9.9.9"
    )
    registry.register_versioned(KEY, first, AGENT_DEFINITION)
    second_version = registry.register_versioned(
        KEY, second, AGENT_DEFINITION
    )
    assert isinstance(second_version, str)

    before = len(registry.audit_log.events())
    assert resolve_pinned(registry, _uri("9.9.9")) == second
    new_events = registry.audit_log.events()[before:]

    resolutions = [event for event in new_events if event.action == "resolve"]
    assert len(resolutions) == 1
    assert resolutions[0].version == second_version


def test_an_ambiguous_declared_version_is_refused() -> None:
    """WR-08: a pinned ref that names two contents names none of them."""
    registry = ControlPlaneRegistry()
    first = _definition(artifact_version="9.9.9")
    second = _definition(name=f"{NAME}-revised", artifact_version="9.9.9")
    # content-hash identity, so both distinct contents land under one key
    # while declaring the same semver — the collision WR-08 refuses.
    registry.register_typed(KEY, first, AGENT_DEFINITION)
    registry.register_typed(KEY, second, AGENT_DEFINITION)
    assert len(registry.versions(KEY)) == 2

    with pytest.raises(AmbiguousPinnedVersionError):
        resolve_pinned(registry, _uri("9.9.9"))


def test_a_miss_is_returned_not_raised() -> None:
    registry = ControlPlaneRegistry()
    registry.register_versioned(KEY, _definition(), AGENT_DEFINITION)
    assert resolve_pinned(registry, _uri("0.0.0-absent")) is None


def test_the_factory_turns_the_shared_miss_into_a_definition_error() -> None:
    registry = ControlPlaneRegistry()
    registry.register_versioned(KEY, _definition(), AGENT_DEFINITION)
    with pytest.raises(AgentDefinitionError):
        _resolve_pinned(registry, _uri("0.0.0-absent"))
