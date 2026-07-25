"""Shared pytest configuration for the CCF SDK test suite.

The one thing this module exists to guarantee: **tests get a graph handle only
by running the real composition root.** There is no test-only writer, no
in-memory fake store, and no convenience helper that constructs
``ccf.graph._writer`` directly. A test double that could write to L3 would
defeat layer 1 of the D-IMPL-41 stack more thoroughly than any production
mistake, because it would ship as the *example* of how to touch the graph
(04-RESEARCH.md anti-patterns; Pitfall 7).

So :func:`fabric_boot` boots an actual fabric over a temp SQLite database, and
everything downstream — the conformance suite, later operator and projection
suites — asks it for a handle.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

# Control Plane keys used by the test fabric. They live here, in test code,
# rather than in `/src`: key names are deployment vocabulary, and the SDK
# enumerating them would be exactly the hardcoding CINV-01 forbids.
RESOLUTION_SPEC_KEY = "test/entity-resolution-spec"
POLICY_BUNDLE_KEY = "test/policy-bundle"


def _resolution_spec() -> Any:
    """The fixture ontology mapping: source payload vocabulary -> E and R.

    A deliberately multi-type, banking-shaped spec (D-02's realism bar): two
    entity classes correlated on different native identifiers, plus a typed
    edge between them. Everything here is *values* and therefore lives in test
    fixtures, never in `/src`.
    """
    from ccf.assembly.worker import (
        EntityResolutionRule,
        EntityResolutionSpec,
        RelationshipResolutionRule,
    )

    return EntityResolutionSpec(
        entity_rules=(
            EntityResolutionRule(
                match_key="counterparty_lei",
                entity_class="counterparty",
                identity_keys=("counterparty_lei",),
                attribute_keys=("counterparty_name", "jurisdiction"),
            ),
            EntityResolutionRule(
                match_key="facility_id",
                entity_class="facility",
                identity_keys=("facility_id",),
                attribute_keys=("facility_type", "currency"),
            ),
        ),
        relationship_rules=(
            RelationshipResolutionRule(
                relationship_type="obligor_of",
                subject_entity_class="counterparty",
                object_entity_class="facility",
            ),
        ),
    )


def _policy_bundle() -> dict[str, str]:
    """A minimal stand-in policy bundle artifact for the slice.

    Its *content* is irrelevant to this plan — what matters is that a version
    of it is resolved from the Control Plane and stamped onto every claim, so
    the policy-binding stage is exercised rather than stubbed. The real bundle
    schema arrives with the policy subsystem plan.
    """
    return {"regime": "test-fixture"}


@pytest.fixture
def fabric_boot(tmp_path: Path) -> Iterator[Callable[..., "FabricHandle"]]:
    """Yield a factory that boots a fresh fabric over its own temp database.

    Returns a *factory* rather than a handle so a test can boot twice and
    assert what happens (the single-writer boot check needs exactly that).
    Every handle is closed on teardown.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    handles: list[FabricHandle] = []
    counter = {"n": 0}

    def factory(*, database_path: Path | None = None) -> "FabricHandle":
        counter["n"] += 1
        registry = ControlPlaneRegistry()
        spec_version = registry.register(RESOLUTION_SPEC_KEY, _resolution_spec())
        policy_version = registry.register(POLICY_BUNDLE_KEY, _policy_bundle())
        handle = boot(
            database_path=database_path
            or tmp_path / f"fabric-{counter['n']}.sqlite3",
            registry=registry,
            resolution_spec_key=RESOLUTION_SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            policy_bundle_version=policy_version,
        )
        handles.append(handle)
        return handle

    try:
        yield factory
    finally:
        for handle in reversed(handles):
            handle.close()


@pytest.fixture
def fabric(fabric_boot: Callable[..., "FabricHandle"]) -> "FabricHandle":
    """A single booted fabric — the common case."""
    return fabric_boot()
