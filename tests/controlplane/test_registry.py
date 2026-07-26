"""Control Plane registry tests (FABR-07; DESIGN.md §7; D-IMPL-38).

The registry is the one config surface every later subsystem reads through, so
its load-bearing properties are pinned here before anything depends on them:
append-only versioning, explicit-pin resolution, no-silent-default, typed
registration against declared artifact classes, and an audit plane that records
reads as well as writes (INV-CH7-71).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    HALF_LIFE_TABLE,
    ArtifactLoadError,
    DebtProfile,
    DeclaredArtifact,
    HalfLifeEntry,
    HalfLifeTable,
    declared_artifact_class,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import (
    ControlPlaneMissing,
    ControlPlaneProtocol,
    ControlPlaneRegistry,
    ReplayResolver,
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


# --- typed registration ----------------------------------------------------


def _half_life_table() -> HalfLifeTable:
    """A one-row λ_c table. The row's values are this test's, not the SDK's."""
    return HalfLifeTable(
        semver="1.0.0",
        entries={
            "kyc-sanctions-match": HalfLifeEntry(
                half_life_seconds=3600,
                decay_driver="real-time sanctions feed",
                supersession_event="new match or clearance",
            )
        },
    )


def _debt_profile() -> DebtProfile:
    return DebtProfile(
        semver="1.0.0",
        risk_sensitivity=Decimal("0.5"),
        forced_llm_threshold=Decimal("0.4"),
        fail_closed_threshold=Decimal("0.9"),
    )


def test_typed_registration_stores_and_records_the_class() -> None:
    registry = _registry()
    key = "acme-bank/half-life/wholesale"
    version = registry.register_typed(key, _half_life_table(), HALF_LIFE_TABLE)
    assert registry.resolve(key, version) == _half_life_table()
    assert registry.artifact_class_of(key) == HALF_LIFE_TABLE.class_id
    assert registry.audit_events()[0].artifact_class == HALF_LIFE_TABLE.class_id


def test_typed_registration_rejects_an_artifact_of_the_wrong_class() -> None:
    registry = _registry()
    with pytest.raises(TypeError):
        registry.register_typed("acme/half-life", _debt_profile(), HALF_LIFE_TABLE)


def test_typed_registration_rejects_an_untyped_mapping() -> None:
    registry = _registry()
    with pytest.raises(TypeError):
        registry.register_typed("acme/half-life", {"entries": {}}, HALF_LIFE_TABLE)


def test_a_key_cannot_be_rebound_to_a_different_artifact_class() -> None:
    registry = _registry()
    key = "acme/config"
    registry.register_typed(key, _half_life_table(), HALF_LIFE_TABLE)
    with pytest.raises(TypeError):
        registry.register_typed(key, _debt_profile(), DEBT_PROFILE)


def test_typed_registration_is_append_only_like_the_untyped_path() -> None:
    registry = _registry()
    key = "acme/half-life"
    v1 = registry.register_typed(key, _half_life_table(), HALF_LIFE_TABLE)
    widened = _half_life_table().model_copy(update={"semver": "1.1.0"})
    v2 = registry.register_typed(key, widened, HALF_LIFE_TABLE)
    assert registry.versions(key) == (v1, v2)
    assert registry.resolve(key, v1) == _half_life_table()


def test_a_user_declared_artifact_class_is_registrable() -> None:
    """Policy bundles and operator parameter sets have deployment schemas."""
    registry = _registry()
    policy = declared_artifact_class("acme-bank.policy-bundle")
    artifact = DeclaredArtifact(
        semver="2.0.0",
        class_id=policy.class_id,
        declaration={"regime": "acme-bank-credit", "jurisdiction": "NL"},
    )
    version = registry.register_typed("acme/policy", artifact, policy)
    assert registry.resolve("acme/policy", version) == artifact


# --- artifact contracts and loading ---------------------------------------


def test_an_artifact_without_a_semver_lane_is_refused() -> None:
    with pytest.raises(ValueError):
        HalfLifeTable.model_validate({"entries": {}})


def test_a_malformed_semver_lane_is_refused() -> None:
    declared = _half_life_table().model_dump()
    declared["semver"] = "one"
    with pytest.raises(ValueError):
        HalfLifeTable.model_validate(declared)


def test_an_empty_half_life_table_is_refused() -> None:
    """A deployment that declared no calibration gets an error, not a default."""
    with pytest.raises(ValueError):
        HalfLifeTable.model_validate({"semver": "1.0.0", "entries": {}})


def test_loading_a_float_valued_artifact_is_refused() -> None:
    text = "\n".join(
        (
            "semver: '1.0.0'",
            "risk_sensitivity: 0.5",
            "forced_llm_threshold: '0.4'",
            "fail_closed_threshold: '0.9'",
        )
    )
    with pytest.raises(ArtifactLoadError):
        load_artifact(text, DEBT_PROFILE)


def test_loading_a_quoted_decimal_artifact_succeeds() -> None:
    text = "\n".join(
        (
            "semver: '1.0.0'",
            "risk_sensitivity: '0.5'",
            "forced_llm_threshold: '0.4'",
            "fail_closed_threshold: '0.9'",
        )
    )
    loaded = load_artifact(text, DEBT_PROFILE)
    assert loaded == _debt_profile()


def test_loading_a_document_of_the_wrong_shape_is_refused() -> None:
    with pytest.raises(ArtifactLoadError):
        parse_artifact({"semver": "1.0.0"}, DEBT_PROFILE)


def test_a_loaded_artifact_registers_and_content_addresses_identically() -> None:
    registry = _registry()
    text = "\n".join(
        (
            "semver: '1.0.0'",
            "risk_sensitivity: '0.5'",
            "forced_llm_threshold: '0.4'",
            "fail_closed_threshold: '0.9'",
        )
    )
    loaded = load_artifact(text, DEBT_PROFILE)
    from_code = registry.register_typed("acme/debt", _debt_profile(), DEBT_PROFILE)
    from_yaml = registry.register_typed("acme/debt", loaded, DEBT_PROFILE)
    assert from_code == from_yaml


# --- the audit plane -------------------------------------------------------


def test_the_audit_log_grows_on_every_register_and_resolve() -> None:
    registry = _registry()
    before = len(registry.audit_events())
    version = registry.register_typed(
        "acme/half-life", _half_life_table(), HALF_LIFE_TABLE
    )
    after_register = len(registry.audit_events())
    registry.resolve("acme/half-life", version)
    after_resolve = len(registry.audit_events())
    assert before < after_register < after_resolve


def test_an_actor_is_recorded_when_stated_and_never_invented() -> None:
    registry = _registry()
    registry.register("acme/policy", _Bundle(label="a"), actor="ops@acme-bank")
    registry.register("acme/policy", _Bundle(label="b"))
    events = registry.audit_events()
    assert events[0].actor == "ops@acme-bank"
    assert events[1].actor is None


def test_the_audit_log_is_append_only() -> None:
    log = AuditLog()
    log.append(
        action="register",
        key="k",
        version="v",
        resolved=True,
        occurred_at=datetime(2026, 7, 25, tzinfo=UTC),
    )
    assert isinstance(log.events(), tuple)
    assert not hasattr(log, "clear")
    assert not hasattr(log, "remove")


def test_audit_sequence_numbers_are_assigned_by_the_log() -> None:
    log = AuditLog()
    for _ in range(3):
        log.append(
            action="resolve",
            key="k",
            version="v",
            resolved=False,
            occurred_at=datetime(2026, 7, 25, tzinfo=UTC),
        )
    assert [event.sequence for event in log.events()] == [0, 1, 2]


# --- the replay path -------------------------------------------------------


def test_the_replay_resolver_cannot_reach_latest() -> None:
    registry = _registry()
    version = registry.register("acme/policy", _Bundle(label="a"))
    resolver = ReplayResolver(registry)
    assert resolver.resolve("acme/policy", version) == _Bundle(label="a")
    assert not hasattr(resolver, "resolve_latest")


def test_the_replay_resolver_propagates_a_missing_version() -> None:
    resolver = ReplayResolver(_registry())
    with pytest.raises(ControlPlaneMissing):
        resolver.resolve("acme/policy", "not-a-version")


# --- introspection surfaces backing WR-08 / IN-03 ----------------------------


def test_peek_returns_the_artifact_without_auditing() -> None:
    """Declared-version probes are not resolutions (WR-08 side effect)."""
    registry = _registry()
    version = registry.register("acme/policy", _Bundle(label="a"))
    before = len(registry.audit_events())
    assert registry.peek("acme/policy", version) == _Bundle(label="a")
    assert len(registry.audit_events()) == before


def test_peek_of_a_missing_version_raises_without_auditing() -> None:
    registry = _registry()
    before = len(registry.audit_events())
    with pytest.raises(ControlPlaneMissing):
        registry.peek("acme/policy", "not-a-version")
    assert len(registry.audit_events()) == before


def test_keys_of_class_lists_only_keys_bound_to_that_class() -> None:
    """Discovery membership derives from registry state, not a second index."""
    registry = _registry()
    bundle_class = declared_artifact_class("policy-bundle")
    other_class = declared_artifact_class("debt-profile")
    bundle = DeclaredArtifact(
        class_id="policy-bundle", semver="1.0.0", declaration={"x": 1}
    )
    other = DeclaredArtifact(
        class_id="debt-profile", semver="1.0.0", declaration={"y": 2}
    )
    registry.register_typed("acme/policy-bundle/a", bundle, bundle_class)
    registry.register_typed("acme/debt-profile/b", other, other_class)
    registry.register("acme/untyped", _Bundle(label="a"))
    assert registry.keys_of_class(bundle_class.class_id) == (
        "acme/policy-bundle/a",
    )
    assert registry.keys_of_class(other_class.class_id) == (
        "acme/debt-profile/b",
    )
    assert registry.keys_of_class("ccf.never-registered") == ()
