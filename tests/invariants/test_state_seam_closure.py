"""The D-20 state-seam closure, proven adversarially and counterfactually.

07-02 (PHASE_I3_GATE §5 prerequisite; D-08/D-09/D-10). Two proofs:

* **Adversarial** — actively attempt an unaudited write through every normal
  language means the public write surface offers, and observe each refused.
* **Counterfactual** — pin the structural facts (token on the Protocol
  signature; the audited writer as the sole minting path) so that reverting
  the closure turns this file red. The reverted-closure red output is
  captured verbatim in 07-02-SUMMARY.md for the gate document (D-10/D-25).

D-22 scope, stated once for the whole file: every claim here is about the
*public write surface and type contract*. Bypass via reflection or private
construction (importing the module-private sentinel, ``object.__new__``
games) is out of the claim's scope by design — those paths are lint- and
CI-covered, never denied.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest

from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.state import (
    AuditedStateWriter,
    ControlPlaneStateStore,
    InMemoryStateStore,
    StateWriteBypassError,
    StateWriteToken,
)

CLASS_A = "test.seam-closure"
WHEN = datetime(2026, 7, 30, tzinfo=timezone.utc)


def _event(key: str) -> AuditEvent:
    return AuditEvent(
        sequence=0,
        action="state_written",
        key=key,
        version="0.0.0",
        resolved=True,
        occurred_at=WHEN,
    )


class TestAdversarialBypass:
    """Unaudited writes attempted through the public surface, each refused.

    These are public-surface bypass attempts — direct call, forged kwargs,
    subclassing. Reflection and private-construction paths are out of the
    claim's D-22 scope by design (lint- and CI-covered).
    """

    def test_a_direct_call_without_a_token_cannot_succeed(self) -> None:
        store = InMemoryStateStore()
        with pytest.raises(TypeError):
            store.put(CLASS_A, "k", "v")  # type: ignore[call-arg]
        assert store.get(CLASS_A, "k") is None

    def test_a_forged_kwarg_token_cannot_succeed(self) -> None:
        store = InMemoryStateStore()
        with pytest.raises(StateWriteBypassError):
            store.put(CLASS_A, "k", "v", token=object())  # type: ignore[arg-type]
        assert store.get(CLASS_A, "k") is None

    def test_the_token_cannot_be_constructed_by_a_caller(self) -> None:
        with pytest.raises(StateWriteBypassError):
            StateWriteToken(object())

    def test_a_token_subclass_skipping_init_cannot_succeed(self) -> None:
        """isinstance is not the gate — the mint is verified at the write."""

        class Forged(StateWriteToken):
            def __init__(self) -> None:  # skips the sentinel demand
                pass

        store = InMemoryStateStore()
        with pytest.raises(StateWriteBypassError):
            store.put(CLASS_A, "k", "v", token=Forged())
        assert store.get(CLASS_A, "k") is None


class TestCounterfactualClosure:
    """The structural facts whose reversion makes this file go red (D-10)."""

    def test_the_protocol_put_requires_the_token(self) -> None:
        """Reverting the closure removes this parameter — red on revert."""
        for surface in (ControlPlaneStateStore, InMemoryStateStore):
            params = inspect.signature(surface.put).parameters
            assert "token" in params, (
                f"{surface.__name__}.put lost its token parameter — the"
                " D-20 closure has been reverted (07-02)"
            )
            assert params["token"].kind is inspect.Parameter.KEYWORD_ONLY
            assert params["token"].default is inspect.Parameter.empty

    def test_the_audited_writer_is_the_sole_minting_path(self) -> None:
        """A write through the audited surface succeeds and audits — while

        no public construction path yields a token (the adversarial class
        above). Together: the audited surface is the only public way to
        write, and every write carries exactly one caller-supplied event.
        """
        store = InMemoryStateStore()
        audit = AuditLog()
        writer = AuditedStateWriter(store=store, audit=audit)
        writer.write(CLASS_A, "k", "v", event=_event("k"))
        assert store.get(CLASS_A, "k") == "v"
        assert len(audit) == 1
        assert audit.events()[0].action == "state_written"

    def test_two_tenants_write_two_distinct_audited_records(self) -> None:
        """D-23 multi-principal: tenant-prefixed keys stay distinct end to

        end — two records in state, two events in the journal, no
        cross-tenant collision under one record class.
        """
        store = InMemoryStateStore()
        audit = AuditLog()
        writer = AuditedStateWriter(store=store, audit=audit)
        writer.write(
            CLASS_A, "tenant-a/g", "a-state", event=_event("tenant-a/g")
        )
        writer.write(
            CLASS_A, "tenant-b/g", "b-state", event=_event("tenant-b/g")
        )
        assert store.get(CLASS_A, "tenant-a/g") == "a-state"
        assert store.get(CLASS_A, "tenant-b/g") == "b-state"
        assert [e.key for e in audit.events()] == [
            "tenant-a/g",
            "tenant-b/g",
        ]
