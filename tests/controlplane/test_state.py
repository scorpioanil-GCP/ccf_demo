"""The Control Plane's mutable-state seam (D-IMPL-18/27; WR-05).

Covers the Protocol's stated obligations directly, so a durable
implementation added in I.4 has a conformance target that does not depend on
the grant machine that happens to be its first consumer.
"""

from __future__ import annotations

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import ControlPlaneStateStore, InMemoryStateStore

CLASS_A = "test.record-class-a"
CLASS_B = "test.record-class-b"


class TestInMemoryStateStore:
    """The reference implementation honours the Protocol's obligations."""

    def test_it_conforms_to_the_protocol(self) -> None:
        assert isinstance(InMemoryStateStore(), ControlPlaneStateStore)

    def test_an_absent_record_is_none_rather_than_an_error(self) -> None:
        """Absence is a normal answer: a machine asks before it has written."""
        assert InMemoryStateStore().get(CLASS_A, "missing") is None

    def test_a_put_record_reads_back(self) -> None:
        store = InMemoryStateStore()
        store.put(CLASS_A, "k", "value")
        assert store.get(CLASS_A, "k") == "value"

    def test_a_put_replaces_rather_than_accumulates(self) -> None:
        """Mutable, deliberately — history lives in the audit log, not here.

        The contrast with the registry is the D-IMPL-27 mutability split
        working: artifacts accumulate versions, state does not.
        """
        store = InMemoryStateStore()
        store.put(CLASS_A, "k", "first")
        store.put(CLASS_A, "k", "second")
        assert store.get(CLASS_A, "k") == "second"
        assert store.items(CLASS_A) == (("k", "second"),)

    def test_record_classes_do_not_collide_on_a_shared_key(self) -> None:
        """The namespace that lets grant state and workflow state co-exist."""
        store = InMemoryStateStore()
        store.put(CLASS_A, "same", "a")
        store.put(CLASS_B, "same", "b")
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
            store.put(CLASS_A, key, key.upper())
        assert store.items(CLASS_A) == (("a", "A"), ("b", "B"), ("c", "C"))

    def test_an_empty_class_is_an_empty_tuple(self) -> None:
        assert InMemoryStateStore().items(CLASS_A) == ()


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
        first.state_store.put(CLASS_A, "k", "v")
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
