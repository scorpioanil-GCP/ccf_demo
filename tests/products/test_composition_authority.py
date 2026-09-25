"""The composition roots mint for their own writes; the callers hold what they were handed (D-IMPL-353 §1.6, D-IMPL-354).

Controls over what Lane J-SRC added to ``ccf.products`` when the handles began
to REQUIRE a capability:

* :class:`~ccf.products.resolver.GovernedResolver` composes itself: at
  construction it refuses a store that does not declare the three classes it
  files under ``ReplayMint`` (fail closed at boot, never at the first write),
  and mints — through the recipe, audited on the Control Plane — the five
  capabilities it holds for its life. No construction site gained a
  parameter, and the clock the serve path reads once per admission is not
  consumed at composition.
* :class:`~ccf.products.resolver.ReplayRefusalRecorder` holds ONE
  ``ReplayMint``: verified at construction, its class and tenant read off the
  capability and nowhere else, the store held to declaring the class.
* :class:`~ccf.products.child_resolver.QuestionBoundChildResolver` is not a
  root: it receives the child-question capability, verifies it against the
  one class it files, and holds its tenant equal to the gate's once.

Every negative control here asserts on the store and the registry AFTER the
refusal — nothing filed, nothing registered — never only on the exception.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import COMPOSITION_PRINCIPAL, CapabilityBypassError, ReplayMint
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.child_resolver import (
    QuestionBoundChildResolver,
    QuestionRetentionUnauthorized,
)
from ccf.products.composite import (
    ADMITTED_CHILD_CONTRACT_CLASS,
    CHILD_QUESTION_CLASS,
    CompositeAdmissionGate,
)
from ccf.products.resolver import (
    GovernedResolver,
    ReplayRefusalRecorder,
    UndeclaredMechanismClass,
)
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger

from tests.composition import composition_replay_mint, declaring_store
from tests.controlplane.capabilities import fabrications
from tests.products.test_resolver_seam import (  # noqa: F401 — `booted` is a fixture
    QUERY_PIN_CLASS,
    REPLAY_RECORD_CLASS,
    TENANT,
    _arguments,
    booted,
)

THE_THREE = (REPLAY_RECORD_CLASS, QUERY_PIN_CLASS, ADMITTED_CHILD_CONTRACT_CLASS)


def _store_missing(root: pathlib.Path, missing: str) -> FileArtifactStore:
    return declaring_store(root, *(c for c in THE_THREE if c != missing))


def _composition_events(registry: ControlPlaneRegistry) -> list[Any]:
    return [e for e in registry.audit_events() if e.action == "composition"]


# --- GovernedResolver composes itself -----------------------------------------------


@pytest.mark.parametrize("missing", THE_THREE)
def test_a_resolver_refuses_at_construction_a_store_that_does_not_declare_a_class_it_files(
    booted: Any, tmp_path: pathlib.Path, missing: str
) -> None:
    """Fail closed at boot: the refusal names the class, and nothing was minted."""
    arguments = {**_arguments(booted), "artifact_store": _store_missing(tmp_path / "s", missing)}
    before = len(_composition_events(booted.control_plane))
    with pytest.raises(UndeclaredMechanismClass, match=missing):
        GovernedResolver(**arguments)
    # The declaration check runs BEFORE any mint, so a refused composition
    # leaves no `composition` event behind it.
    assert len(_composition_events(booted.control_plane)) == before


def test_a_resolver_refuses_a_store_that_exposes_no_declaration_at_all(
    booted: Any, tmp_path: pathlib.Path
) -> None:
    """*Don't know* is not *pass*: a store with no `write_kinds` cannot be shown to admit the writer."""

    class _Undeclared:
        def put(self, authorized: object, artifact: object) -> object:  # pragma: no cover — never reached
            raise AssertionError("a refused composition must not reach the store")

        def get(self, *, content_address: str) -> bytes:
            raise KeyError(content_address)

        def exists(self, *, content_address: str) -> bool:
            return False

        def resolve_uri(self, *, uri: str) -> str:
            raise LookupError(uri)

    with pytest.raises(UndeclaredMechanismClass, match="write_kinds"):
        GovernedResolver(**{**_arguments(booted), "artifact_store": _Undeclared()})


def test_a_resolver_mints_exactly_its_five_authorities_at_composition_and_audits_each(
    booted: Any,
) -> None:
    """Three `ReplayMint` (one per class it files) and two `Register` (one per key it opens),
    each recorded as a `composition` event by the composition principal — and the
    admission clock, which the serve path reads once per admission, untouched."""
    reads: list[int] = []

    def counting() -> datetime:
        reads.append(1)
        return datetime(2026, 3, 2, 12, 7, tzinfo=UTC)

    arguments = {**_arguments(booted), "admission_clock": counting}  # mints the recorder's own capability
    before = _composition_events(booted.control_plane)
    resolver = GovernedResolver(**arguments)
    minted = _composition_events(booted.control_plane)[len(before):]

    assert reads == [], "composition consumed the admission clock"
    assert {e.actor for e in minted} == {COMPOSITION_PRINCIPAL}
    assert sorted((e.key, e.version) for e in minted) == sorted(
        [
            (REPLAY_RECORD_CLASS, ReplayMint.action_id),
            (QUERY_PIN_CLASS, ReplayMint.action_id),
            (ADMITTED_CHILD_CONTRACT_CLASS, ReplayMint.action_id),
            (resolver.request_contract_key, "composition.register"),
            (resolver._declaration().max_ttl_key, "composition.register"),
        ]
    )
    held = resolver._authorities
    assert held.replay.resource == REPLAY_RECORD_CLASS and held.replay.tenant == booted.fabric.tenant_id
    assert held.query_pin.resource == QUERY_PIN_CLASS
    assert held.admitted_child.resource == ADMITTED_CHILD_CONTRACT_CLASS
    assert held.request_contract.resource == resolver.request_contract_key
    # Every decision id is the content address of one of those events, so a
    # capability is traceable to the record that authorized it.
    decision_ids = {c.decision_id for c in (held.replay, held.query_pin, held.admitted_child, held.max_ttl, held.request_contract)}
    assert len(decision_ids) == 5


def test_the_register_step_refuses_a_declaration_naming_another_ceiling_key(booted: Any) -> None:
    """The registry files under the CAPABILITY's key; a declaration handed in with a
    different `max_ttl_key` would otherwise land silently under the minted one."""
    resolver = GovernedResolver(**_arguments(booted))
    declaration = resolver._declaration().model_copy(update={"max_ttl_key": f"{TENANT}/other/max-ttl"})
    with pytest.raises(TypeError, match="max_ttl_key"):
        resolver._register(declaration)


# --- ReplayRefusalRecorder holds one capability ---------------------------------------


def _recorder_arguments(booted: Any, store: Any) -> dict[str, Any]:
    return {"artifact_store": store, "assembly_mode": "algorithmic"}


def test_a_recorder_reads_its_class_and_tenant_off_the_capability(booted: Any, tmp_path: pathlib.Path) -> None:
    store = declaring_store(tmp_path / "r", REPLAY_RECORD_CLASS)
    recorder = ReplayRefusalRecorder(
        authorized=composition_replay_mint(booted.control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS),
        **_recorder_arguments(booted, store),
    )
    assert (recorder.replay_record_class, recorder.tenant_id) == (REPLAY_RECORD_CLASS, TENANT)


def test_a_recorder_refuses_every_fabrication_at_construction(booted: Any, tmp_path: pathlib.Path) -> None:
    store = declaring_store(tmp_path / "r", REPLAY_RECORD_CLASS)
    for label, forged in fabrications(ReplayMint, tenant=TENANT, resource=REPLAY_RECORD_CLASS):
        with pytest.raises(CapabilityBypassError):
            ReplayRefusalRecorder(authorized=forged, **_recorder_arguments(booted, store))  # type: ignore[arg-type]
        assert not any((tmp_path / "r").glob("[0-9a-f]" * 64)), label


def test_a_recorder_refuses_a_store_that_does_not_declare_its_class(booted: Any, tmp_path: pathlib.Path) -> None:
    with pytest.raises(UndeclaredMechanismClass, match=REPLAY_RECORD_CLASS):
        ReplayRefusalRecorder(
            authorized=composition_replay_mint(booted.control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS),
            **_recorder_arguments(booted, declaring_store(tmp_path / "r")),
        )


# --- QuestionBoundChildResolver receives, never mints --------------------------------


def _child_resolver_arguments(registry: ControlPlaneRegistry, store: Any, *, gate_tenant: str) -> dict[str, Any]:
    ledger = GrantLedger(
        control_plane=registry,
        catalog=SkillCatalog(registry),
        sink=None,  # type: ignore[arg-type]
        clock=lambda: datetime(2026, 3, 2, 12, 7, tzinfo=UTC),
    )
    return {
        "ledger": ledger,
        "agent_definition_hash": "0" * 64,
        "gate": CompositeAdmissionGate(tenant_id=gate_tenant, consumer_scope="consumer://control", registry=registry),
        "child_questions": lambda requirement, request: None,
        "callable_registry": CallableRegistry(),
        "artifact_store": store,
    }


def test_a_child_resolver_takes_a_capability_for_exactly_the_child_question_class(tmp_path: pathlib.Path) -> None:
    registry = ControlPlaneRegistry()
    store = declaring_store(tmp_path / "q", CHILD_QUESTION_CLASS)
    arguments = _child_resolver_arguments(registry, store, gate_tenant=TENANT)
    with pytest.raises(CapabilityBypassError, match="resource"):
        QuestionBoundChildResolver(
            authorized=composition_replay_mint(registry, tenant=TENANT, artifact_class=ADMITTED_CHILD_CONTRACT_CLASS),
            **arguments,
        )
    for label, forged in fabrications(ReplayMint, tenant=TENANT, resource=CHILD_QUESTION_CLASS):
        with pytest.raises(CapabilityBypassError):
            QuestionBoundChildResolver(authorized=forged, **arguments)  # type: ignore[arg-type]
    QuestionBoundChildResolver(
        authorized=composition_replay_mint(registry, tenant=TENANT, artifact_class=CHILD_QUESTION_CLASS),
        **arguments,
    )


def test_a_child_resolver_holds_its_capabilitys_tenant_equal_to_the_gates_once(tmp_path: pathlib.Path) -> None:
    registry = ControlPlaneRegistry()
    store = declaring_store(tmp_path / "q", CHILD_QUESTION_CLASS)
    with pytest.raises(QuestionRetentionUnauthorized, match="other-bank"):
        QuestionBoundChildResolver(
            authorized=composition_replay_mint(registry, tenant="other-bank", artifact_class=CHILD_QUESTION_CLASS),
            **_child_resolver_arguments(registry, store, gate_tenant=TENANT),
        )


def test_write_kinds_is_the_declaration_the_resolver_checks(tmp_path: pathlib.Path) -> None:
    """The positive half of the declaration check, on the store's own surface."""
    store = FileArtifactStore(
        root=tmp_path / "w", write_kinds=WriteKinds.declare({REPLAY_RECORD_CLASS: (ReplayMint,)})
    )
    assert store.write_kinds.is_declared(REPLAY_RECORD_CLASS)
    assert not store.write_kinds.is_declared(QUERY_PIN_CLASS)
