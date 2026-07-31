"""The Control Plane's mutable-state seam (D-IMPL-18/27; WR-05; D-20 closure).

Covers the Protocol's stated obligations directly, so a durable
implementation added in I.4 has a conformance target that does not depend on
the grant machine that happens to be its first consumer.

Since the D-20 closure (07-02), ``put`` requires a :class:`StateWriteToken`
that only the audited write path mints, so every direct-store test here
writes through :class:`AuditedStateWriter`. The closure claim is D-22-scoped:
unaudited writes are unrepresentable through the *public write surface*;
reflection and private-construction bypasses are lint- and CI-covered, not
impossible.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import (
    AuditedStateWriter,
    ControlPlaneStateStore,
    InMemoryStateStore,
    StateWriteBypassError,
    StateWriteToken,
)

CLASS_A = "test.record-class-a"
CLASS_B = "test.record-class-b"

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


def _put(store: ControlPlaneStateStore, record_class: str, key: str, record: object) -> None:
    writer, _ = _writer(store)
    writer.write(record_class, key, record, event=_event(key))


class TestInMemoryStateStore:
    """The reference implementation honours the Protocol's obligations."""

    def test_it_conforms_to_the_protocol(self) -> None:
        assert isinstance(InMemoryStateStore(), ControlPlaneStateStore)

    def test_an_absent_record_is_none_rather_than_an_error(self) -> None:
        """Absence is a normal answer: a machine asks before it has written."""
        assert InMemoryStateStore().get(CLASS_A, "missing") is None

    def test_a_put_record_reads_back(self) -> None:
        store = InMemoryStateStore()
        _put(store, CLASS_A, "k", "value")
        assert store.get(CLASS_A, "k") == "value"

    def test_a_put_replaces_rather_than_accumulates(self) -> None:
        """Mutable, deliberately — history lives in the audit log, not here.

        The contrast with the registry is the D-IMPL-27 mutability split
        working: artifacts accumulate versions, state does not.
        """
        store = InMemoryStateStore()
        _put(store, CLASS_A, "k", "first")
        _put(store, CLASS_A, "k", "second")
        assert store.get(CLASS_A, "k") == "second"
        assert store.items(CLASS_A) == (("k", "second"),)

    def test_record_classes_do_not_collide_on_a_shared_key(self) -> None:
        """The namespace that lets grant state and workflow state co-exist."""
        store = InMemoryStateStore()
        _put(store, CLASS_A, "same", "a")
        _put(store, CLASS_B, "same", "b")
        assert store.get(CLASS_A, "same") == "a"
        assert store.get(CLASS_B, "same") == "b"
        assert store.items(CLASS_A) == (("same", "a"),)

    def test_items_are_key_sorted_regardless_of_arrival_order(self) -> None:
        """Replay-load-bearing: callers fold over this to compute identities.

        ``GrantLedger.grant_set_hash`` walks this traversal, so an
        arrival-order-dependent walk would make a skill-set identity depend
        on the order grants happened to arrive in.
        """
        store = InMemoryStateStore()
        for key in ("c", "a", "b"):
            _put(store, CLASS_A, key, key.upper())
        assert store.items(CLASS_A) == (("a", "A"), ("b", "B"), ("c", "C"))

    def test_an_empty_class_is_an_empty_tuple(self) -> None:
        assert InMemoryStateStore().items(CLASS_A) == ()


class TestTokenGate:
    """The D-20 closure: ``put`` requires a token only the audited path mints.

    D-22 scope: these assert the *public write surface* — the ``put``
    signature and the token's type contract. Reflection or private
    construction is out of the claim's scope, covered by lint and CI.
    """

    def test_put_without_a_token_is_a_type_error(self) -> None:
        with pytest.raises(TypeError):
            InMemoryStateStore().put(CLASS_A, "k", "v")  # type: ignore[call-arg]

    def test_put_with_a_forged_object_is_refused(self) -> None:
        with pytest.raises(StateWriteBypassError):
            InMemoryStateStore().put(
                CLASS_A, "k", "v", token=object()  # type: ignore[arg-type]
            )

    def test_the_token_is_not_constructible_outside_the_module(self) -> None:
        with pytest.raises(StateWriteBypassError):
            StateWriteToken(object())

    def test_the_protocol_signature_carries_the_token(self) -> None:
        """The seam itself demands the token, not just one implementation."""
        import inspect

        for surface in (ControlPlaneStateStore, InMemoryStateStore):
            params = inspect.signature(surface.put).parameters
            assert "token" in params
            assert params["token"].kind is inspect.Parameter.KEYWORD_ONLY


class TestAuditedStateWriter:
    """The ergonomic write surface: mints the token, appends the audit event."""

    def test_a_write_lands_the_record(self) -> None:
        store = InMemoryStateStore()
        writer, _ = _writer(store)
        writer.write(CLASS_A, "k", "v", event=_event("k"))
        assert store.get(CLASS_A, "k") == "v"

    def test_exactly_one_event_per_write_and_it_is_the_callers(self) -> None:
        """The fixed audit policy (INV-CH7-71): the caller's domain event,

        once — no doubled entries, no lost transition evidence. The log
        assigns the sequence; every other field is the caller's.
        """
        store = InMemoryStateStore()
        writer, audit = _writer(store)
        event = _event("k", actor="tester")
        writer.write(CLASS_A, "k", "v", event=event)
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
        with pytest.raises(TypeError):
            writer.write(CLASS_A, "k", "v")  # type: ignore[call-arg]

    def test_two_tenants_do_not_collide(self) -> None:
        """D-23: two tenants' records under one record class stay distinct.

        Keys are tenant-prefixed by their consumers (the
        ``{tenant}/{class}/{name}`` convention); the store and the audited
        surface preserve the separation end to end.
        """
        store = InMemoryStateStore()
        writer, audit = _writer(store)
        writer.write(
            CLASS_A, "tenant-a/g", "a-state", event=_event("tenant-a/g")
        )
        writer.write(
            CLASS_A, "tenant-b/g", "b-state", event=_event("tenant-b/g")
        )
        assert store.get(CLASS_A, "tenant-a/g") == "a-state"
        assert store.get(CLASS_A, "tenant-b/g") == "b-state"
        keys = [event.key for event in audit.events()]
        assert keys == ["tenant-a/g", "tenant-b/g"]


class TestRegistrySeam:
    """The registry offers the seam, and it is injectable."""

    def test_the_default_registry_supplies_a_conforming_store(self) -> None:
        assert isinstance(
            ControlPlaneRegistry().state_store, ControlPlaneStateStore
        )

    def test_an_injected_store_is_the_one_used(self) -> None:
        """The seam a deployment substitutes to make state durable."""
        store = InMemoryStateStore()
        registry = ControlPlaneRegistry(state_store=store)
        assert registry.state_store is store

    def test_two_registries_do_not_share_a_default_store(self) -> None:
        """No class-level state — the agreement property is per-plane.

        Readers over *one* Control Plane must agree; readers over two
        must not, or a test deployment would see production's grants.
        """
        first = ControlPlaneRegistry()
        second = ControlPlaneRegistry()
        _put(first.state_store, CLASS_A, "k", "v")
        assert second.state_store.get(CLASS_A, "k") is None

    def test_registered_artifacts_do_not_route_through_the_state_seam(
        self,
    ) -> None:
        """The mutability split, pinned (D-IMPL-27).

        An artifact is immutable and versioned; it belongs on the
        append-only path, never in mutable state.
        """
        registry = ControlPlaneRegistry()
        registry.register("some.key", {"a": 1})
        assert registry.state_store.items("some.key") == ()
