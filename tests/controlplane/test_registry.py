"""Control Plane registry tests (FABR-07; DESIGN.md §7; D-IMPL-38).

The registry is the one config surface every later subsystem reads through, so
its three load-bearing properties are pinned here before anything depends on
them: append-only versioning, explicit-pin resolution, and no-silent-default.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import (
    ControlPlaneMissing,
    ControlPlaneProtocol,
    ControlPlaneRegistry,
)


class _Bundle(CCFContract):
    label: str


def _clock() -> object:
    start = datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC)
    ticks = iter(range(1000))

    def now() -> datetime:
        return start + timedelta(seconds=next(ticks))

    return now


def _registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry(clock=_clock())  # type: ignore[arg-type]


def test_register_returns_a_version_and_resolves_exactly() -> None:
    registry = _registry()
    version = registry.register("policy", _Bundle(label="a"))
    assert registry.resolve("policy", version) == _Bundle(label="a")


def test_registration_is_append_only() -> None:
    registry = _registry()
    v1 = registry.register("policy", _Bundle(label="a"))
    v2 = registry.register("policy", _Bundle(label="b"))
    assert v1 != v2
    assert registry.versions("policy") == (v1, v2)
    # The first version survives the second registration byte-identically.
    assert canonical_bytes(registry.resolve("policy", v1)) == canonical_bytes(
        _Bundle(label="a")
    )


def test_reregistering_identical_content_is_idempotent() -> None:
    registry = _registry()
    v1 = registry.register("policy", _Bundle(label="a"))
    v2 = registry.register("policy", _Bundle(label="a"))
    assert v1 == v2
    assert registry.versions("policy") == (v1,)


def test_missing_key_raises_typed_error() -> None:
    registry = _registry()
    with pytest.raises(ControlPlaneMissing):
        registry.resolve("absent", "deadbeef")


def test_missing_version_raises_typed_error() -> None:
    registry = _registry()
    registry.register("policy", _Bundle(label="a"))
    with pytest.raises(ControlPlaneMissing):
        registry.resolve("policy", "not-a-version")


def test_latest_requires_the_explicitly_named_method() -> None:
    registry = _registry()
    assert not hasattr(registry.resolve, "default_version")
    v1 = registry.register("policy", _Bundle(label="a"))
    v2 = registry.register("policy", _Bundle(label="b"))
    assert registry.resolve_latest("policy") == (v2, _Bundle(label="b"))
    assert registry.resolve("policy", v1) == _Bundle(label="a")


def test_latest_on_missing_key_raises_typed_error() -> None:
    with pytest.raises(ControlPlaneMissing):
        _registry().resolve_latest("absent")


def test_every_register_and_resolve_is_audited() -> None:
    registry = _registry()
    version = registry.register("policy", _Bundle(label="a"))
    registry.resolve("policy", version)
    registry.resolve_latest("policy")
    events = registry.audit_events()
    assert len(events) == 3
    assert [e.action for e in events] == ["register", "resolve", "resolve_latest"]
    assert [e.sequence for e in events] == [0, 1, 2]
    assert all(e.key == "policy" and e.version == version for e in events)
    assert events[0].occurred_at < events[1].occurred_at


def test_failed_resolution_is_audited_too() -> None:
    registry = _registry()
    with pytest.raises(ControlPlaneMissing):
        registry.resolve("absent", "x")
    events = registry.audit_events()
    assert len(events) == 1
    assert events[0].action == "resolve"
    assert events[0].resolved is False


def test_uncanonicalizable_artifact_is_refused() -> None:
    registry = _registry()
    with pytest.raises(TypeError):
        registry.register("policy", {"rate": 1.5})


def test_registry_satisfies_the_control_plane_protocol() -> None:
    assert isinstance(_registry(), ControlPlaneProtocol)


def test_module_is_tagged_algorithmic() -> None:
    import ccf.controlplane.registry as registry_mod

    assert registry_mod.__ccf_mode__ == "algorithmic"
