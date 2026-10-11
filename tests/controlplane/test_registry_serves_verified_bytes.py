"""The read doors parse the write-verified bytes and verify the result against the protected
stored reconstruction — ``D-IMPL-380``, 2026-10-11 00:28 MST GO on the corrected GROK-BRIEF-8.

Dave's five points (00:15), each a test here:

1. A successful parse is insufficient: a validator that behaves at registration and returns
   changed content on retrieval without raising is refused by name at all three read doors.
2. Type and value are verified after the parse, against the stored reconstruction, without a
   render.
3. Identity and nested isolation are kept (the ten sixth-round tests, unchanged, plus the
   identity leg here).
4. One record holds the reconstruction and its verified bytes; a missing or inconsistent
   half is ``RegistryIntegrityFailure``, audited, never ``ControlPlaneMissing``; a failed
   write publishes neither half.
5. "A read never renders" is a cost assertion only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import BaseModel, model_validator

import ccf.controlplane.registry as registry_module
from ccf.authz.capability import Authorized, Register
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import HALF_LIFE_TABLE, HalfLifeEntry, HalfLifeTable
from ccf.controlplane.registry import (
    ArtifactIsolationRefused,
    ControlPlaneMissing,
    ControlPlaneRegistry,
)
from tests.controlplane.capabilities import register_capability

READ_DOORS = ("peek", "resolve", "resolve_latest")


def _cap(key: str) -> Authorized[Register]:
    return register_capability(key, Register)


def _clock() -> Any:
    start = datetime(2026, 10, 11, 0, 28, 0, tzinfo=UTC)
    ticks = iter(range(1_000_000))

    def now() -> datetime:
        return start + timedelta(seconds=next(ticks))

    return now


def _registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry(clock=_clock())


def _table(semver: str = "1.0.0") -> HalfLifeTable:
    return HalfLifeTable(
        semver=semver,
        entries={
            "spread": HalfLifeEntry(
                half_life_seconds=86_400,
                decay_driver="market-movement",
                supersession_event="next-observation",
            )
        },
    )


def _read(registry: ControlPlaneRegistry, door: str, key: str, version: str) -> object:
    if door == "peek":
        return registry.peek(key, version)
    if door == "resolve":
        return registry.resolve(key, version)
    served_version, served = registry.resolve_latest(key)
    assert served_version == version
    return served


def _audited_reads(registry: ControlPlaneRegistry, door: str) -> list[Any]:
    return [e for e in registry.audit_events() if e.action == door]


# --- 1. a successful parse is insufficient ---------------------------------------------

_DRIFT = {"armed": False}


class _DriftsOnRetrieval(CCFContract):
    """Behaves at registration; once armed, every later validation returns changed content."""

    label: str

    @model_validator(mode="after")
    def _drift(self) -> "_DriftsOnRetrieval":
        if _DRIFT["armed"]:
            object.__setattr__(self, "label", self.label + "-drifted")
        return self


def test_a_validator_that_returns_changed_content_on_retrieval_without_raising_is_refused_by_name_at_every_read_door() -> None:
    """Point 1. The parse succeeds; the value check against the stored reconstruction refuses."""
    _DRIFT["armed"] = False
    registry = _registry()
    key = "acme/drift"
    version = registry.register(_cap(key), _DriftsOnRetrieval(label="as-registered"))
    assert registry.resolve(key, version) == _DriftsOnRetrieval(label="as-registered")
    _DRIFT["armed"] = True
    try:
        for door in READ_DOORS:
            before = len(_audited_reads(registry, door))
            with pytest.raises(ArtifactIsolationRefused) as caught:
                _read(registry, door, key, version)
            assert caught.value.door == door
            assert "not equal" in caught.value.reason, caught.value.reason
            assert not isinstance(caught.value, ControlPlaneMissing)
            if door != "peek":
                rows = _audited_reads(registry, door)
                assert len(rows) == before + 1 and rows[-1].resolved is False
    finally:
        _DRIFT["armed"] = False
    # The stored reconstruction was never touched by the drift.
    assert registry.resolve(key, version) == _DriftsOnRetrieval(label="as-registered")


# --- 2. type and value, verified against the stored reconstruction, no render --------------


def test_a_parse_that_returns_a_different_value_is_refused_by_the_value_check_not_by_a_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Point 2. The reason names the stored reconstruction; no canonical render happens on read."""
    registry = _registry()
    key = "acme/table"
    version = registry.register_typed(_cap(key), _table(), HALF_LIFE_TABLE)
    real = HalfLifeTable.model_validate

    def rewritten(document: Any, *args: Any, **kwargs: Any) -> HalfLifeTable:
        built = real(document, *args, **kwargs)
        return built.model_construct(**{**built.__dict__, "semver": "9.9.9"})

    monkeypatch.setattr(HalfLifeTable, "model_validate", classmethod(lambda cls, d, *a, **k: rewritten(d, *a, **k)))

    def no_render(_: object) -> bytes:
        raise AssertionError("a read door rendered")

    monkeypatch.setattr(registry_module, "canonical_bytes", no_render)
    for door in READ_DOORS:
        with pytest.raises(ArtifactIsolationRefused) as caught:
            _read(registry, door, key, version)
        assert caught.value.door == door
        assert "stored reconstruction" in caught.value.reason, caught.value.reason


def test_a_parse_that_returns_a_subclass_is_refused_by_the_type_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point 2. Type is checked against the stored reconstruction's type, by name."""

    class _Narrower(HalfLifeTable):
        pass

    registry = _registry()
    key = "acme/table"
    version = registry.register_typed(_cap(key), _table(), HALF_LIFE_TABLE)
    unpatched = BaseModel.model_validate.__func__  # type: ignore[attr-defined]
    monkeypatch.setattr(HalfLifeTable, "model_validate", classmethod(lambda cls, d, *a, **k: unpatched(_Narrower, d)))
    for door in READ_DOORS:
        with pytest.raises(ArtifactIsolationRefused) as caught:
            _read(registry, door, key, version)
        assert caught.value.door == door
        assert "type" in caught.value.reason, caught.value.reason


# --- 3. identity --------------------------------------------------------------------------


def test_a_parse_that_hands_back_the_stored_reconstruction_itself_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point 3. An interning validator can return a cached instance from a parse; refused by name."""
    registry = _registry()
    key = "acme/table"
    version = registry.register_typed(_cap(key), _table(), HALF_LIFE_TABLE)
    held = registry._artifacts[(key, version)]
    stored = getattr(held, "artifact", held)
    monkeypatch.setattr(HalfLifeTable, "model_validate", classmethod(lambda cls, d, *a, **k: stored))
    for door in READ_DOORS:
        with pytest.raises(ArtifactIsolationRefused) as caught:
            _read(registry, door, key, version)
        assert caught.value.door == door
        assert "itself" in caught.value.reason, caught.value.reason


# --- 4. one record, both halves, integrity ------------------------------------------------


def test_the_registry_exports_the_integrity_failure_by_name() -> None:
    assert "RegistryIntegrityFailure" in registry_module.__all__


def test_bytes_that_do_not_hash_to_their_version_are_an_integrity_failure_not_missing() -> None:
    """Point 4. Inconsistent byte storage under an existing (key, version)."""
    failure = getattr(registry_module, "RegistryIntegrityFailure", None)
    assert failure is not None, "RegistryIntegrityFailure is not defined"
    registry = _registry()
    key = "acme/table"
    version = registry.register_typed(_cap(key), _table(), HALF_LIFE_TABLE)
    held = registry._artifacts[(key, version)]
    assert hasattr(held, "artifact") and hasattr(held, "rendered"), "one record must hold both halves"
    assert hashlib.sha256(held.rendered).hexdigest() == version
    registry._artifacts[(key, version)] = type(held)(artifact=held.artifact, rendered=canonical_bytes(_table("2.0.0")))
    for door in READ_DOORS:
        before = len(_audited_reads(registry, door))
        with pytest.raises(failure) as caught:
            _read(registry, door, key, version)
        assert not isinstance(caught.value, ControlPlaneMissing)
        assert caught.value.key == key and caught.value.version == version and caught.value.door == door
        if door != "peek":
            rows = _audited_reads(registry, door)
            assert len(rows) == before + 1 and rows[-1].resolved is False


def test_a_missing_half_is_an_integrity_failure_not_missing() -> None:
    """Point 4. The pre-change shape — a bare artifact with no verified bytes — is refused, not served."""
    failure = getattr(registry_module, "RegistryIntegrityFailure", None)
    assert failure is not None, "RegistryIntegrityFailure is not defined"
    registry = _registry()
    key = "acme/table"
    version = registry.register_typed(_cap(key), _table(), HALF_LIFE_TABLE)
    registry._artifacts[(key, version)] = _table()  # a bare artifact: one half only
    for door in READ_DOORS:
        with pytest.raises(failure) as caught:
            _read(registry, door, key, version)
        assert not isinstance(caught.value, ControlPlaneMissing)
    with pytest.raises(ControlPlaneMissing):
        registry.resolve(key, "0" * 64)  # a version never registered is still missing, not integrity


_POISON = {"armed": False}


class _PoisonedTable(HalfLifeTable):
    @model_validator(mode="before")
    @classmethod
    def _gate(cls, data: Any) -> Any:
        if _POISON["armed"]:
            raise ValueError("re-validation refused by the test")
        return data


def test_a_failed_write_publishes_neither_half() -> None:
    """Point 4. After a refused registration there is no record at all under the key."""
    registry = _registry()
    key = "acme/poisoned"
    table = _PoisonedTable.model_validate(_table().model_dump(mode="json"))
    _POISON["armed"] = True
    try:
        with pytest.raises(ArtifactIsolationRefused):
            registry.register(_cap(key), table)
    finally:
        _POISON["armed"] = False
    assert registry.versions(key) == ()
    assert not [k for k in registry._artifacts if k[0] == key], "a refused write left a record behind"
    assert not [e for e in registry.audit_events() if e.key == key and e.resolved]


def test_what_a_read_serves_renders_to_the_verified_bytes_and_hashes_to_the_version() -> None:
    """Point 4. The two halves agree, and what is served is the registered content — model and plain document."""
    registry = _registry()
    cases = {
        "acme/table": registry.register_typed(_cap("acme/table"), _table(), HALF_LIFE_TABLE),
        "acme/doc": registry.register(_cap("acme/doc"), {"a": [1, 2, {"b": "c"}], "n": None}),
    }
    for key, version in cases.items():
        held = registry._artifacts[(key, version)]
        for door in READ_DOORS:
            served = _read(registry, door, key, version)
            assert canonical_bytes(served) == held.rendered
            assert content_hash(served) == version
            assert served == held.artifact and served is not held.artifact


# --- 5. cost: a read does not render (an assertion about cost, not about value) ------------


def test_a_read_door_does_not_render_the_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point 5, demoted. With the registry's render replaced by a raiser, every read door still serves."""
    registry = _registry()
    key_t, key_d = "acme/table", "acme/doc"
    v_t = registry.register_typed(_cap(key_t), _table(), HALF_LIFE_TABLE)
    v_d = registry.register(_cap(key_d), {"a": [1, 2, {"b": "c"}]})

    def no_render(_: object) -> bytes:
        raise AssertionError("a read door rendered")

    monkeypatch.setattr(registry_module, "canonical_bytes", no_render)
    monkeypatch.setattr(registry_module, "content_hash", lambda _: (_ for _ in ()).throw(AssertionError("a read door hashed by rendering")))
    for door in READ_DOORS:
        assert _read(registry, door, key_t, v_t) == _table()
        assert _read(registry, door, key_d, v_d) == {"a": [1, 2, {"b": "c"}]}
