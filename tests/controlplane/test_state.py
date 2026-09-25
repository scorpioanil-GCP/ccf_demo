"""The Control Plane's mutable-state seam (D-IMPL-18/27; WR-05; D-20 closure; D-IMPL-353 §1.2).

Covers the Protocol's stated obligations directly, so a durable
implementation has a conformance target that does not depend on the grant
machine or the workflow engine that happen to be its consumers.

Two proofs travel on every write and they are different facts:

* ``token`` — the D-20 closure (07-02): the write travelled the audited path.
  Minted only by :class:`AuditedStateWriter`.
* ``authorized`` — D-IMPL-353 §1.2: the write is a consequence of an
  authorized action. Minted only by the gate (or, for ``ReplayMint``, at
  composition). The store takes the **tenant** from it and nothing else can
  supply one; the record's identity within that tenant (``record_id``) is the
  writing mechanism's — an execution id, a grant hash — and the key is derived
  by :func:`state_key` from the two.

The capability controls proper (wrong kind, wrong resource, fabrication,
retargeting, sabotage) live in ``test_state_capability_controls.py``.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest

from ccf.authz.capability import Execute, Register, Resume
from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import (
    AuditedStateWriter,
    ControlPlaneStateStore,
    InMemoryStateStore,
    StateKeyError,
    StateWriteBypassError,
    StateWriteToken,
    split_state_key,
    state_key,
)
from tests.controlplane.capabilities import capability, register_capability

CLASS_A = "test.record-class-a"
CLASS_B = "test.record-class-b"
TENANT = "tenant-a"
WORKFLOW_KEY = f"{TENANT}/ccf.workflow-definition/payment-release"

WHEN = datetime(2026, 7, 30, tzinfo=timezone.utc)


def _event(key: str, *, actor: str | None = None) -> AuditEvent:
    """A caller-domain audit event, as the audited surface requires."""
    return AuditEvent(
        sequence=0,
        action="state_written",
        key=key,
        version="0.0.0",
        resolved=True,
        occurred_at=WHEN,
        actor=actor,
    )


def _writer(store: ControlPlaneStateStore) -> tuple[AuditedStateWriter, AuditLog]:
    audit = AuditLog()
    return AuditedStateWriter(store=store, audit=audit), audit


def _put(
    store: ControlPlaneStateStore,
    record_class: str,
    record_id: str,
    record: object,
    *,
    tenant: str = TENANT,
) -> str:
    """Write through the audited surface under an ``Execute`` for ``tenant``; return the key."""
    writer, _ = _writer(store)
    authorized = capability(Execute, tenant=tenant, resource=WORKFLOW_KEY)
    writer.write(
        authorized, record_class, record, record_id=record_id, event=_event(record_id)
    )
    return state_key(tenant=tenant, record_id=record_id)


class TestStateKey:
    """The key is derived, injective, and splits back to what built it."""

    def test_the_key_is_tenant_then_record_id(self) -> None:
        assert state_key(tenant="acme", record_id="exec-1") == "acme/exec-1"

    def test_it_splits_back_exactly(self) -> None:
        assert split_state_key("acme/exec-1") == ("acme", "exec-1")

    def test_a_record_id_may_carry_the_separator_and_still_split_back(self) -> None:
        """Only the tenant is separator-free; that is enough for injectivity."""
        key = state_key(tenant="acme", record_id="a/b/c")
        assert split_state_key(key) == ("acme", "a/b/c")

    @pytest.mark.parametrize("tenant", ["", " acme", "acme ", "ac/me"])
    def test_a_tenant_that_would_make_the_key_ambiguous_is_refused(self, tenant: str) -> None:
        with pytest.raises(StateKeyError):
            state_key(tenant=tenant, record_id="exec-1")

    def test_an_empty_record_id_is_refused(self) -> None:
        with pytest.raises(StateKeyError):
            state_key(tenant="acme", record_id="")

    def test_a_key_with_no_tenant_segment_does_not_split(self) -> None:
        with pytest.raises(StateKeyError):
            split_state_key("no-separator")


class TestInMemoryStateStore:
    """The reference implementation honours the Protocol's obligations."""

    def test_it_conforms_to_the_protocol(self) -> None:
        assert isinstance(InMemoryStateStore(), ControlPlaneStateStore)

    def test_an_absent_record_is_none_rather_than_an_error(self) -> None:
        """Absence is a normal answer: a machine asks before it has written."""
        assert InMemoryStateStore().get(CLASS_A, "missing") is None

    def test_a_put_record_reads_back_under_the_derived_key(self) -> None:
        store = InMemoryStateStore()
        key = _put(store, CLASS_A, "k", "value")
        assert key == f"{TENANT}/k"
        assert store.get(CLASS_A, key) == "value"

    def test_a_put_replaces_rather_than_accumulates(self) -> None:
        """Mutable, deliberately — history lives in the audit log, not here."""
        store = InMemoryStateStore()
        _put(store, CLASS_A, "k", "first")
        key = _put(store, CLASS_A, "k", "second")
        assert store.get(CLASS_A, key) == "second"
        assert store.items(CLASS_A) == ((key, "second"),)

    def test_record_classes_do_not_collide_on_a_shared_key(self) -> None:
        """The namespace that lets grant state and workflow state co-exist."""
        store = InMemoryStateStore()
        _put(store, CLASS_A, "same", "a")
        key = _put(store, CLASS_B, "same", "b")
        assert store.get(CLASS_A, key) == "a"
        assert store.get(CLASS_B, key) == "b"
        assert store.items(CLASS_A) == ((key, "a"),)

    def test_items_are_key_sorted_regardless_of_arrival_order(self) -> None:
        """Replay-load-bearing: callers fold over this to compute identities."""
        store = InMemoryStateStore()
        for record_id in ("c", "a", "b"):
            _put(store, CLASS_A, record_id, record_id.upper())
        assert store.items(CLASS_A) == (
            (f"{TENANT}/a", "A"),
            (f"{TENANT}/b", "B"),
            (f"{TENANT}/c", "C"),
        )

    def test_an_empty_class_is_an_empty_tuple(self) -> None:
        assert InMemoryStateStore().items(CLASS_A) == ()

    def test_the_tenant_on_the_write_is_the_capabilitys_and_nothing_elses(self) -> None:
        """§1.3, at the seam: the same record id under two tenants' capabilities
        lands under two keys, and the caller supplied neither tenant."""
        store = InMemoryStateStore()
        a = _put(store, CLASS_A, "g", "a-state", tenant="tenant-a")
        b = _put(store, CLASS_A, "g", "b-state", tenant="tenant-b")
        assert (a, b) == ("tenant-a/g", "tenant-b/g")
        assert store.get(CLASS_A, a) == "a-state"
        assert store.get(CLASS_A, b) == "b-state"


class TestTokenGate:
    """The D-20 closure: ``put`` requires a token only the audited path mints."""

    def test_put_without_a_token_is_a_type_error(self) -> None:
        authorized = capability(Execute, tenant=TENANT, resource=WORKFLOW_KEY)
        with pytest.raises(TypeError):
            InMemoryStateStore().put(authorized, CLASS_A, "v", record_id="k")  # type: ignore[call-arg]

    def test_put_with_a_forged_token_is_refused(self) -> None:
        authorized = capability(Execute, tenant=TENANT, resource=WORKFLOW_KEY)
        with pytest.raises(StateWriteBypassError):
            InMemoryStateStore().put(
                authorized, CLASS_A, "v", record_id="k", token=object()  # type: ignore[arg-type]
            )

    def test_the_token_is_not_constructible_outside_the_module(self) -> None:
        with pytest.raises(StateWriteBypassError):
            StateWriteToken(object())

    def test_the_protocol_signature_carries_both_proofs(self) -> None:
        """The seam itself demands the token AND the capability, not just one
        implementation — and offers no ``key`` parameter at all."""
        for surface in (ControlPlaneStateStore, InMemoryStateStore):
            params = inspect.signature(surface.put).parameters
            assert list(params)[:2] == ["self", "authorized"]
            assert "token" in params
            assert params["token"].kind is inspect.Parameter.KEYWORD_ONLY
            assert params["record_id"].kind is inspect.Parameter.KEYWORD_ONLY
            assert "key" not in params
            assert params["authorized"].default is inspect.Parameter.empty


class TestAuditedStateWriter:
    """The ergonomic write surface: mints the token, appends the audit event."""

    def test_a_write_lands_the_record(self) -> None:
        store = InMemoryStateStore()
        key = _put(store, CLASS_A, "k", "v")
        assert store.get(CLASS_A, key) == "v"

    def test_exactly_one_event_per_write_and_it_is_the_callers(self) -> None:
        store = InMemoryStateStore()
        writer, audit = _writer(store)
        event = _event("k", actor="tester")
        authorized = capability(Resume, tenant=TENANT, resource="exec-1")
        writer.write(authorized, CLASS_A, "v", record_id="exec-1", event=event)
        assert len(audit) == 1
        (recorded,) = audit.events()
        assert recorded.action == event.action
        assert recorded.key == event.key
        assert recorded.version == event.version
        assert recorded.resolved is event.resolved
        assert recorded.occurred_at == event.occurred_at
        assert recorded.actor == "tester"

    def test_the_event_is_required(self) -> None:
        store = InMemoryStateStore()
        writer, _ = _writer(store)
        authorized = capability(Execute, tenant=TENANT, resource=WORKFLOW_KEY)
        with pytest.raises(TypeError):
            writer.write(authorized, CLASS_A, "v", record_id="k")  # type: ignore[call-arg]

    def test_the_writer_offers_no_key_parameter_either(self) -> None:
        params = inspect.signature(AuditedStateWriter.write).parameters
        assert list(params)[:2] == ["self", "authorized"]
        assert "key" not in params
        assert params["record_id"].kind is inspect.Parameter.KEYWORD_ONLY


class TestRegistrySeam:
    """The registry offers the seam, and it is injectable."""

    def test_the_default_registry_supplies_a_conforming_store(self) -> None:
        assert isinstance(
            ControlPlaneRegistry().state_store, ControlPlaneStateStore
        )

    def test_an_injected_store_is_the_one_used(self) -> None:
        store = InMemoryStateStore()
        registry = ControlPlaneRegistry(state_store=store)
        assert registry.state_store is store

    def test_two_registries_do_not_share_a_default_store(self) -> None:
        first = ControlPlaneRegistry()
        second = ControlPlaneRegistry()
        key = _put(first.state_store, CLASS_A, "k", "v")
        assert second.state_store.get(CLASS_A, key) is None

    def test_registered_artifacts_do_not_route_through_the_state_seam(self) -> None:
        """The mutability split, pinned (D-IMPL-27)."""
        registry = ControlPlaneRegistry()
        key = "acme/some.class/some-name"
        registry.register(register_capability(key, Register), {"a": 1})
        assert registry.state_store.items(key) == ()
