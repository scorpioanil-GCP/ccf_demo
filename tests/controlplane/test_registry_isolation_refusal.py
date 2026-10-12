# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""When the registry cannot reconstruct an artifact faithfully it refuses — leaving no partial registration, returning no shared state, reporting nothing missing (``D-IMPL-380``, sixth round).

Dave, 2026-10-10 15:50 MST: *"Do not fall back to the original object or a
shallow copy. Complete reconstruction and necessary validation before changing
registration state. If copying fails, leave no newly published version, class
binding or version-bump entry, and do not record a successful registration. On
retrieval failure, do not return shared state or report the artifact as
missing."*

These tests are committed with the repair, not before it: the refusal they
name, :class:`ccf.controlplane.registry.ArtifactIsolationRefused`, is the
repair's own. An artifact that exists but cannot be re-validated is built with
``model_construct`` (no validation) under a validator the test arms afterwards,
so the registry meets a real instance whose reconstruction raises.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import model_validator

from ccf.authz.capability import Authorized, Register
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import HALF_LIFE_TABLE, HalfLifeEntry, HalfLifeTable
from ccf.controlplane.registry import (
    ArtifactIsolationRefused,
    ControlPlaneMissing,
    ControlPlaneRegistry,
    RegistrationRefusal,
)
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from http_api.composition_authority import register_versioned_at_composition
from tests.controlplane.capabilities import register_capability
from tests.workflow.test_factory import _workflow_definition, _workflow_fixture

_POISON = {"armed": False}


def _refuse_when_armed(data: Any) -> Any:
    if _POISON["armed"]:
        raise ValueError("re-validation refused by the test")
    return data


class _PoisonedDocument(CCFContract):
    label: str

    @model_validator(mode="before")
    @classmethod
    def _gate(cls, data: Any) -> Any:
        return _refuse_when_armed(data)


class _PoisonedTable(HalfLifeTable):
    @model_validator(mode="before")
    @classmethod
    def _gate(cls, data: Any) -> Any:
        return _refuse_when_armed(data)


class _PoisonedDefinition(WorkflowDefinition):
    @model_validator(mode="before")
    @classmethod
    def _gate(cls, data: Any) -> Any:
        return _refuse_when_armed(data)


class _OtherDocument(CCFContract):
    label: str


_INTERNED: dict[str, "_Flyweight"] = {}


class _Flyweight(CCFContract):
    """A contract whose validation interns instances by content: ``model_validate``
    on its own canonical form returns the SAME object that was registered."""

    label: str
    attributes: Mapping[str, str] = {}

    @model_validator(mode="wrap")
    @classmethod
    def _intern(cls, data: Any, handler: Any) -> Any:
        built = handler(data)
        return _INTERNED.setdefault(content_hash(built), built)


@pytest.fixture(autouse=True)
def _disarmed() -> Any:
    _POISON["armed"] = False
    _INTERNED.clear()
    yield
    _POISON["armed"] = False
    _INTERNED.clear()


def _cap(key: str) -> Authorized[Register]:
    return register_capability(key, Register)


def _registry() -> ControlPlaneRegistry:
    start = datetime(2026, 10, 10, 16, 0, 0, tzinfo=UTC)
    ticks = iter(range(10_000))
    return ControlPlaneRegistry(clock=lambda: start + timedelta(seconds=next(ticks)))


#: The audit actions the three write doors record on success. A composition-minted
#: authority records a `composition` row for the key BEFORE registering; that row is
#: the authority's, not a registration.
_REGISTRATIONS = frozenset({"register", "register_typed", "register_versioned"})


def _successful_rows(registry: ControlPlaneRegistry, key: str) -> list[str]:
    return [
        e.action
        for e in registry.audit_events()
        if e.key == key and e.resolved and e.action in _REGISTRATIONS
    ]


def _entry() -> HalfLifeEntry:
    return HalfLifeEntry(
        half_life_seconds=86_400, decay_driver="market-movement",
        supersession_event="next-observation", decay_basis="valid-from",
    )


# --- the write doors: a refusal leaves nothing behind -------------------------


def test_register_refuses_an_artifact_it_cannot_reconstruct_and_leaves_no_registration() -> None:
    registry = _registry()
    key = "acme/document"
    poisoned = _PoisonedDocument.model_construct(label="poison")
    _POISON["armed"] = True

    with pytest.raises(ArtifactIsolationRefused) as caught:
        registry.register(_cap(key), poisoned)

    assert caught.value.door == "register" and caught.value.artifact_type == "_PoisonedDocument"
    assert "re-validation refused by the test" in caught.value.reason  # pydantic ValidationError, a ValueError
    assert registry.versions(key) == ()
    assert registry.artifact_class_of(key) is None
    assert _successful_rows(registry, key) == []
    # Nothing leaked: the key is free for another artifact, under another class.
    _POISON["armed"] = False
    version = registry.register(_cap(key), _OtherDocument(label="fine"))
    assert registry.resolve(key, version) == _OtherDocument(label="fine")


def test_register_typed_refuses_an_artifact_it_cannot_reconstruct_and_binds_no_class() -> None:
    registry = _registry()
    key = "acme/half-life"
    table = _PoisonedTable(semver="1.0.0", entries={"spread": _entry()})
    _POISON["armed"] = True

    with pytest.raises(ArtifactIsolationRefused) as caught:
        registry.register_typed(_cap(key), table, HALF_LIFE_TABLE)

    assert caught.value.door == "register_typed"
    assert registry.versions(key) == ()
    assert registry.artifact_class_of(key) is None, "a class binding leaked from a refused registration"
    assert _successful_rows(registry, key) == []
    _POISON["armed"] = False
    version = registry.register_typed(_cap(key), HalfLifeTable(semver="1.0.0", entries={"spread": _entry()}), HALF_LIFE_TABLE)
    assert content_hash(registry.resolve(key, version)) == version


def test_register_versioned_refuses_an_artifact_it_cannot_reconstruct_and_records_no_bump() -> None:
    registry = _registry()
    key = _workflow_fixture()["keys"]["workflow_definition"]
    definition = _PoisonedDefinition.model_validate(json.loads(canonical_bytes(_workflow_definition())))
    _POISON["armed"] = True

    with pytest.raises(ArtifactIsolationRefused) as caught:
        register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)

    assert caught.value.door == "register_versioned"
    assert registry.versions(key) == ()
    assert registry.artifact_class_of(key) is None
    assert _successful_rows(registry, key) == []
    # No bump entry leaked: the same declared artifact_version registers afterwards
    # with the same content hash and is not refused as an unbumped change.
    _POISON["armed"] = False
    outcome = register_versioned_at_composition(registry, key, _workflow_definition(), WORKFLOW_DEFINITION)
    assert isinstance(outcome, str), f"refused after a failed registration: {outcome!r}"
    assert not isinstance(outcome, RegistrationRefusal)


def test_a_refusal_names_the_type_the_door_and_the_guarantee() -> None:
    error = ArtifactIsolationRefused(artifact_type="Thing", door="peek", reason="why")
    assert isinstance(error, TypeError) and not isinstance(error, LookupError)
    assert (error.artifact_type, error.door, error.reason) == ("Thing", "peek", "why")
    assert "peek" in str(error) and "Thing" in str(error) and "why" in str(error)


# --- the read doors: a refusal returns nothing and reports nothing missing -----


def test_peek_and_resolve_refuse_rather_than_share_or_report_missing_when_reconstruction_fails() -> None:
    registry = _registry()
    key = "acme/document"
    version = registry.register(_cap(key), _PoisonedDocument(label="stored-fine"))
    resolves_before = len([e for e in registry.audit_events() if e.action == "resolve"])
    _POISON["armed"] = True

    for door, read in (("peek", registry.peek), ("resolve", registry.resolve)):
        with pytest.raises(ArtifactIsolationRefused) as caught:
            read(key, version)
        assert caught.value.door == door, caught.value
        assert not isinstance(caught.value, ControlPlaneMissing)

    # Not reported missing: the version is still registered.
    assert registry.versions(key) == (version,)
    # A refused read is audited as a failed resolve — the module promises every
    # resolve, including a failed one, is recorded (the Fable seat, sixth-round
    # delta review, F3) — and never as a success.
    resolves_after = [e for e in registry.audit_events() if e.action == "resolve"]
    assert len(resolves_after) == resolves_before + 1, "a refused resolve wrote no audit row"
    assert resolves_after[-1].resolved is False and resolves_after[-1].version == version
    assert not [e for e in resolves_after[resolves_before:] if e.resolved]
    _POISON["armed"] = False
    assert registry.resolve(key, version) == _PoisonedDocument(label="stored-fine")


def test_a_nested_type_drift_the_bytes_cannot_see_is_refused_not_served() -> None:
    """A plain mapping holding a Decimal renders as a string; bytes agree, values do not."""
    from decimal import Decimal

    registry = _registry()
    with pytest.raises(ArtifactIsolationRefused) as caught:
        registry.register(_cap("acme/amount"), {"amount": Decimal("1.50")})
    assert "not equal" in caught.value.reason
    assert registry.versions("acme/amount") == ()


# --- the sixth-round delta review's two findings (codex and gemini seats) --------


def test_register_versioned_leaves_no_bump_map_behind_when_reconstruction_is_refused() -> None:
    """Fail-safe placement, asserted on private state because no public surface
    exposes the bump map: a refused registration must leave ``_bumps`` without
    the key. Both CLI seats on the sixth-round delta review found
    ``self._bumps.setdefault(key, {})`` running ahead of the reconstruction.
    """
    registry = _registry()
    key = _workflow_fixture()["keys"]["workflow_definition"]
    definition = _PoisonedDefinition.model_validate(json.loads(canonical_bytes(_workflow_definition())))
    _POISON["armed"] = True
    with pytest.raises(ArtifactIsolationRefused):
        register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)
    assert key not in registry._bumps, "an empty bump map leaked from a refused registration"  # noqa: SLF001
    assert registry.versions(key) == () and registry.artifact_class_of(key) is None


def test_a_re_registration_whose_nested_types_drift_is_refused_even_when_the_bytes_are_known() -> None:
    """The drift refusal must not be bypassable through idempotency: a second
    registration whose canonical bytes are already known still has its own
    object reconstructed and checked, so ``{"amount": Decimal("1.50")}`` after
    ``{"amount": "1.50"}`` is refused rather than reported registered (the
    codex seat, sixth-round delta review, point 5).
    """
    from decimal import Decimal

    registry = _registry()
    key = "acme/amount"
    first = registry.register(_cap(key), {"amount": "1.50"})
    with pytest.raises(ArtifactIsolationRefused) as caught:
        registry.register(_cap(key), {"amount": Decimal("1.50")})
    assert "not equal" in caught.value.reason
    assert registry.versions(key) == (first,)
    assert registry.resolve(key, first) == {"amount": "1.50"}


def test_a_class_whose_validation_hands_back_the_original_is_refused_not_stored() -> None:
    """The three guarantees — type, canonical bytes, equality — are all satisfied by
    the original object itself. A contract that interns instances by content
    returns it from ``model_validate``, and the registry would store and serve
    the registrant's object (the Fable seat, sixth-round delta review, F2,
    executed). The fourth guarantee: the reconstruction is not the artifact.
    """
    registry = _registry()
    key = "acme/flyweight"
    original = _Flyweight(label="as-built", attributes={"k": "v"})
    with pytest.raises(ArtifactIsolationRefused) as caught:
        registry.register(_cap(key), original)
    assert "itself" in caught.value.reason
    assert registry.versions(key) == ()


def test_an_untyped_document_is_json_native_so_a_python_mode_dump_is_refused_and_the_model_or_json_dump_is_served() -> None:
    """``D-IMPL-380``, 2026-10-10 18:25 (blocker 2, option (a)): the restriction, pinned.

    An untyped ``register`` document may hold only what ``json.loads`` of its own
    canonical bytes gives back. A python-mode ``model_dump()`` of a ``DebtProfile``
    keeps three ``Decimal`` values and a tuple, so the parsed document differs in
    type at four paths and the registry refuses rather than coerces — leaving no
    version behind. The same profile as the typed model, or as
    ``model_dump(mode="json")``, is served as built. Found by the post-reboot full
    suite of ``57ec6c73`` (``tests/replay/test_engine_rehydration.py``).
    """
    from decimal import Decimal

    from ccf.controlplane.artifacts import DebtProfile
    from ccf.halflife.assessment import DebtSignal, SignalObligation

    profile = DebtProfile(
        semver="1.0.0",
        risk_sensitivity=Decimal("1.0"),
        forced_llm_threshold=Decimal("0.50"),
        fail_closed_threshold=Decimal("0.90"),
        signal_obligations=(
            SignalObligation(signal=DebtSignal.OK, obligation_ref="test-duty-alpha"),
        ),
    )
    registry = ControlPlaneRegistry()

    with pytest.raises(ArtifactIsolationRefused) as caught:
        registry.register(_cap("acme/profile-python-dump"), profile.model_dump())
    assert caught.value.door == "register"
    assert caught.value.artifact_type == "dict"
    assert registry.versions("acme/profile-python-dump") == ()

    typed_version = registry.register(_cap("acme/profile-typed"), profile)
    assert isinstance(registry.resolve("acme/profile-typed", typed_version), DebtProfile)

    json_document = profile.model_dump(mode="json")
    json_version = registry.register(_cap("acme/profile-json-dump"), json_document)
    served = registry.resolve("acme/profile-json-dump", json_version)
    assert served == json_document and served is not json_document
    assert typed_version == json_version, "the typed model and its JSON-mode dump share one canonical form"
