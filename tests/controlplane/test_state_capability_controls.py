"""§9 controls for ``ControlPlaneStateStore.put`` — D-IMPL-353 §1.2, the derived-writes rule.

A state write is a *consequence* of a decision — the run an ``Execute``
started, the transition a ``SkillGrant`` performed — so the capability it
requires is the one that authorized that action, and the store takes the
tenant from it. What this file proves, control by control:

* **wrong kind** — a genuine ``Register`` capability handed to ``put`` dies at
  ``verify`` before the store's dict is touched;
* **fabrication** — the four §9 fabrications die at ``verify`` (the stub
  sentinel, ``Mock``, ``object()``, a subclass skipping ``__init__``);
* **retargeting** (§1.5g) — a genuine ``Execute`` retargeted by
  ``object.__setattr__`` on every field is unusable, and nothing lands under
  the original tenant or the retargeted one;
* **positive** — every kind in :data:`STATE_WRITE_KINDS` writes, under
  ``authorized.tenant`` only, and a kind outside the set does not;
* **the token is the other proof** — a genuine capability with a forged token
  still dies, on the token.

The static tooth for this handle is measured by
``tests/controlplane/test_static_controls.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import pytest

from ccf.authz.capability import (
    ActionKind,
    ArtifactWrite,
    CapabilityBypassError,
    Execute,
    HitlSubmit,
    Register,
    ReplayMint,
    Resume,
    SkillGrant,
    SkillRevoke,
)
from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.state import (
    STATE_WRITE_KINDS,
    AuditedStateWriter,
    InMemoryStateStore,
    StateTenantMismatch,
    StateWriteBypassError,
    state_key,
)
from tests.controlplane.capabilities import (
    RETARGETS,
    capability,
    fabrications,
    replay_mint,
    retarget,
)

RECORD_CLASS = "test.workflow-state"
TENANT = "acme-bank"
WORKFLOW_KEY = f"{TENANT}/ccf.workflow-definition/payment-release"
EXECUTION = "exec-0001"
WHEN = datetime(2026, 9, 24, tzinfo=timezone.utc)


def _event() -> AuditEvent:
    return AuditEvent(
        sequence=0, action="state_written", key=EXECUTION, version="0.0.0",
        resolved=True, occurred_at=WHEN, actor=None,
    )


def _write(store: InMemoryStateStore, authorized: object) -> None:
    """Through the only supported path, with a genuine token."""
    AuditedStateWriter(store=store, audit=AuditLog()).write(
        cast(Any, authorized), RECORD_CLASS, "record", record_id=EXECUTION, event=_event()
    )


def _nothing_written(store: InMemoryStateStore) -> None:
    assert store.items(RECORD_CLASS) == ()


# --- positive -------------------------------------------------------------------


class TestPositive:
    def test_the_state_write_kinds_are_exactly_the_four_derived_writers(self) -> None:
        """Named population: the two engine kinds and the two ledger kinds."""
        assert STATE_WRITE_KINDS == (Execute, Resume, SkillGrant, SkillRevoke)

    @pytest.mark.parametrize("kind", STATE_WRITE_KINDS)
    def test_every_state_write_kind_files_under_the_capabilitys_tenant(
        self, kind: type[ActionKind]
    ) -> None:
        store = InMemoryStateStore()
        _write(store, capability(kind, tenant=TENANT, resource=WORKFLOW_KEY))
        assert store.items(RECORD_CLASS) == (
            (state_key(tenant=TENANT, record_id=EXECUTION), "record"),
        )

    def test_a_record_declaring_another_tenant_is_refused_before_the_write(self) -> None:
        """Records are opaque, with the one exception §1.3 requires."""
        from types import SimpleNamespace

        store = InMemoryStateStore()
        foreign = SimpleNamespace(tenant="other-bank", execution_id=EXECUTION)
        with pytest.raises(StateTenantMismatch):
            AuditedStateWriter(store=store, audit=AuditLog()).write(
                capability(Execute, tenant=TENANT, resource=WORKFLOW_KEY),
                RECORD_CLASS, foreign, record_id=EXECUTION, event=_event(),
            )
        _nothing_written(store)

    def test_a_record_declaring_the_capabilitys_tenant_is_filed(self) -> None:
        from types import SimpleNamespace

        store = InMemoryStateStore()
        own = SimpleNamespace(tenant=TENANT, execution_id=EXECUTION)
        AuditedStateWriter(store=store, audit=AuditLog()).write(
            capability(Execute, tenant=TENANT, resource=WORKFLOW_KEY),
            RECORD_CLASS, own, record_id=EXECUTION, event=_event(),
        )
        assert store.get(RECORD_CLASS, state_key(tenant=TENANT, record_id=EXECUTION)) is own

    def test_the_tenant_comes_from_the_capability_not_from_any_argument(self) -> None:
        store = InMemoryStateStore()
        _write(store, capability(Execute, tenant="other-bank", resource=WORKFLOW_KEY))
        (key, _), = store.items(RECORD_CLASS)
        assert key.startswith("other-bank/")
        assert store.get(RECORD_CLASS, state_key(tenant=TENANT, record_id=EXECUTION)) is None


# --- wrong kind -------------------------------------------------------------------


class TestWrongKind:
    @pytest.mark.parametrize("wrong", [Register, ArtifactWrite, HitlSubmit])
    def test_a_door_kind_that_does_not_write_state_dies_at_verify(
        self, wrong: type[ActionKind]
    ) -> None:
        store = InMemoryStateStore()
        with pytest.raises(CapabilityBypassError, match="kind"):
            _write(store, capability(wrong, tenant=TENANT, resource=WORKFLOW_KEY))
        _nothing_written(store)

    def test_replay_mint_writes_artifacts_not_state(self) -> None:
        """The composition kind is for governed *artifact* classes (§2 P3); it
        is not a state-write wand."""
        store = InMemoryStateStore()
        with pytest.raises(CapabilityBypassError, match="kind"):
            _write(store, replay_mint(tenant=TENANT, artifact_class="ccf.replay-record"))
        _nothing_written(store)

    def test_the_kind_is_checked_by_identity_not_by_subclass(self) -> None:
        class LooksLikeExecute(Execute):
            pass

        store = InMemoryStateStore()
        with pytest.raises(CapabilityBypassError):
            _write(store, capability(LooksLikeExecute, tenant=TENANT, resource=WORKFLOW_KEY))
        _nothing_written(store)


# --- fabrication ----------------------------------------------------------------


class TestFabrication:
    @pytest.mark.parametrize(
        "label,fake",
        list(fabrications(Execute, tenant=TENANT, resource=WORKFLOW_KEY)),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_every_fabrication_dies_at_verify_before_the_write(
        self, label: str, fake: object
    ) -> None:
        store = InMemoryStateStore()
        with pytest.raises(CapabilityBypassError):
            _write(store, fake)
        _nothing_written(store)

    def test_a_genuine_capability_with_a_forged_token_dies_on_the_token(self) -> None:
        """Two proofs, two facts: the capability passes and the token does not."""
        store = InMemoryStateStore()
        with pytest.raises(StateWriteBypassError):
            store.put(
                capability(Execute, tenant=TENANT, resource=WORKFLOW_KEY),
                RECORD_CLASS,
                "record",
                record_id=EXECUTION,
                token=cast(Any, object()),
            )
        _nothing_written(store)


# --- retargeting (§1.5g) ----------------------------------------------------------


class TestRetargeting:
    @pytest.mark.parametrize("field", sorted(RETARGETS))
    def test_a_forced_retarget_writes_nothing_under_either_tenant(self, field: str) -> None:
        store = InMemoryStateStore()
        cap = capability(Execute, tenant=TENANT, resource=WORKFLOW_KEY)
        retarget(cap, field, RETARGETS[field])
        with pytest.raises(CapabilityBypassError):
            _write(store, cap)
        _nothing_written(store)

    def test_a_kind_retargeted_to_a_state_write_kind_confers_nothing(self) -> None:
        """Valid sentinel, ``kind`` reassigned to the legitimate ``Execute``
        identity — the naive sentinel-plus-current-kind check would pass."""
        store = InMemoryStateStore()
        cap = capability(Register, tenant=TENANT, resource=WORKFLOW_KEY)
        retarget(cap, "kind", Execute)
        assert getattr(cap, "kind") is Execute  # the naive check WOULD pass
        with pytest.raises(CapabilityBypassError):
            _write(store, cap)
        _nothing_written(store)
