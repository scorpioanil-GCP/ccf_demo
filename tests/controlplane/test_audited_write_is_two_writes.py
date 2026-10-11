"""``AuditedStateWriter.write_if`` is two writes, not one (decision 7 of ``D-IMPL-378``).

Dave, 2026-10-09 06:06 MST, confirmed at 06:21: *"(b), with the documentation
correction now. Make a committed transition without its audit row detectable
and recoverable. Do not claim atomicity that does not exist."* The final
panel's G-ONEWRITE measured the window this module pins
(``records/2026-10-09-d-impl-378-final-panel/panel/probes/p_b10_write_if_window.py``
on the ``dl-378-record`` branch):
``src/ccf/controlplane/state.py::AuditedStateWriter.write_if`` runs the store's
conditional write and THEN appends the audit event, so an append that fails
after the write landed leaves the record moved with no event for it.

The test asserts that window as it stands. It is not a fix: making such a
transition detectable and recoverable (7 (b)) is being designed, not built.
When that design changes the behavior, this test goes red and
``public/how-to/security-and-deployment.md`` §4.13, which states the window,
must change with it.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.state import AuditedStateWriter, InMemoryStateStore
from tests.invariants.test_state_seam_closure import (
    CLASS_A,
    RECORD_ID,
    _authorized,
    _event,
    _key,
)

#: What the stand-in audit log raises, so the assertion names its own failure.
UNAVAILABLE = "audit log unavailable between the two writes"


class _AppendFailsAfterLooking(AuditLog):
    """An audit log whose append fails, after noting what the store held then.

    What it notes is the order of the two writes: the record's state at the
    moment the event's append was attempted.
    """

    def __init__(self, store: InMemoryStateStore, key: str) -> None:
        super().__init__()
        self._store = store
        self._key = key
        self.seen_at_append: list[tuple[object | None, int]] = []

    def append(self, **kwargs: Any) -> AuditEvent:
        self.seen_at_append.append(self._store.get_versioned(CLASS_A, self._key))
        raise OSError(UNAVAILABLE)


def test_limit_an_append_that_fails_after_the_conditional_write_leaves_the_record_moved_with_no_event() -> None:
    store = InMemoryStateStore()
    key = _key()
    audit = _AppendFailsAfterLooking(store, key)
    writer = AuditedStateWriter(store=store, audit=audit)
    assert store.get_versioned(CLASS_A, key) == (None, 0)

    with pytest.raises(OSError, match=UNAVAILABLE):
        writer.write_if(
            _authorized(),
            CLASS_A,
            "moved",
            record_id=RECORD_ID,
            event=_event(key),
            expected_version=0,
        )

    # Two writes, in this order: when the append was attempted, the
    # conditional write had already landed.
    assert audit.seen_at_append == [("moved", 1)]
    # The first write stands after the second failed: the record moved and its
    # version advanced, and no event evidences the transition.
    assert store.get_versioned(CLASS_A, key) == ("moved", 1)
    assert len(audit) == 0
