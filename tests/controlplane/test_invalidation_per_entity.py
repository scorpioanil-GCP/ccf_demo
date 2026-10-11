"""``D-IMPL-382`` option A — one invalidation record per (tenant, entity), red first.

Dave, 2026-10-11 07:32 MST, adopting Grok's ruling: *"Implement option A."* *"Verify that
updating or reading one entity no longer processes unrelated entities."* *"State that the
whole-register address disappears and each entity has its own version history."*

These tests use only behavior the sink, the serve gate and the registry already expose, so they
are red today on the property, not on a missing name:

1. recording one supersession renders an amount of canonical bytes that does not grow with the
   number of OTHER entities already superseded;
2. the serve gate's read for one touched entity parses an amount of bytes that does not grow
   with the number of other entities;
3. no Control Plane key's version history mixes entities: each entity has its own.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

import ccf.controlplane.registry as registry_module
from tests.products import test_dependency_invalidation as fixture

UNRELATED = 200
#: An entity's own record renders to a few hundred bytes; a register of 200 others is tens of kilobytes.
PER_ENTITY_BYTES_CEILING = 4096


def _superseded(registry: Any, count: int) -> None:
    for i in range(count):
        fixture._supersede(
            registry, tenant_id=fixture.TENANT_A, entity_uri=f"entity://unrelated-{i}",
            at=fixture.T2 + timedelta(seconds=i),
        )


def _largest_render_during(monkeypatch: pytest.MonkeyPatch, action: Any) -> int:
    seen: list[int] = []
    real = registry_module.canonical_bytes

    def counting(obj: object) -> bytes:
        rendered = real(obj)
        seen.append(len(rendered))
        return rendered

    monkeypatch.setattr(registry_module, "canonical_bytes", counting)
    action()
    monkeypatch.setattr(registry_module, "canonical_bytes", real)
    return max(seen, default=0)


def _largest_parse_during(monkeypatch: pytest.MonkeyPatch, action: Any) -> int:
    seen: list[int] = []
    real = registry_module.json.loads

    def counting(data: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(len(data))
        return real(data, *args, **kwargs)

    monkeypatch.setattr(registry_module.json, "loads", counting)
    try:
        action()
    finally:
        monkeypatch.setattr(registry_module.json, "loads", real)
    return max(seen, default=0)


def test_recording_one_supersession_does_not_render_unrelated_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = fixture.ControlPlaneRegistry()
    _superseded(registry, UNRELATED)
    largest = _largest_render_during(
        monkeypatch,
        lambda: fixture._supersede(registry, tenant_id=fixture.TENANT_A, entity_uri=fixture.ENTITY_X, at=fixture.T2),
    )
    assert 0 < largest <= PER_ENTITY_BYTES_CEILING, (
        f"recording one entity's boundary rendered {largest} bytes with {UNRELATED} unrelated entities on record"
    )


def test_reading_one_touched_entity_at_serve_does_not_parse_unrelated_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = fixture.ControlPlaneRegistry()
    registered = fixture._registered(registry)
    _superseded(registry, UNRELATED)
    fixture._supersede(registry, tenant_id=fixture.TENANT_A, entity_uri=fixture.ENTITY_X, at=fixture.T2)
    outcomes: list[object] = []
    largest = _largest_parse_during(
        monkeypatch,
        lambda: outcomes.append(fixture._serve(
            registry, registered, tenant_id=fixture.TENANT_A, snapshot=fixture.T1, touched=(fixture.ENTITY_X,)
        )),
    )
    assert type(outcomes[0]).__name__ == "DependencyInvalidationRefusal", outcomes
    assert 0 < largest <= PER_ENTITY_BYTES_CEILING, (
        f"the serve gate parsed {largest} bytes to read one entity with {UNRELATED} unrelated entities on record"
    )


def _entities_in(artifact: object) -> set[str]:
    entries = getattr(artifact, "entries", None)
    if entries is not None:
        return {e.entity_uri for e in entries}
    uri = getattr(artifact, "entity_uri", None)
    return {uri} if isinstance(uri, str) else set()


def test_each_entity_has_its_own_version_history() -> None:
    registry = fixture.ControlPlaneRegistry()
    fixture._supersede(registry, tenant_id=fixture.TENANT_A, entity_uri=fixture.ENTITY_X, at=fixture.T2)
    fixture._supersede(registry, tenant_id=fixture.TENANT_A, entity_uri=fixture.ENTITY_Y, at=fixture.T2)
    fixture._supersede(registry, tenant_id=fixture.TENANT_A, entity_uri=fixture.ENTITY_X, at=fixture.T3)
    keys = {e.key for e in registry.audit_events() if e.action.startswith("register") and e.resolved}
    histories: dict[str, list[set[str]]] = {
        key: [_entities_in(registry.peek(key, v)) for v in registry.versions(key)] for key in keys
    }
    mixed = {k: h for k, h in histories.items() if len(set().union(*h)) > 1}
    assert not mixed, f"a key's version history mixes entities: {mixed}"
    by_entity = {next(iter(set().union(*h))): len(h) for h in histories.values() if h and set().union(*h)}
    assert by_entity.get(fixture.ENTITY_X) == 2 and by_entity.get(fixture.ENTITY_Y) == 1, by_entity
