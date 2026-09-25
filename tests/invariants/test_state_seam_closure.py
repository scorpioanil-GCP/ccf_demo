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

from ccf.authz.capability import Authorized, Execute
from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.state import (
    AuditedStateWriter,
    ControlPlaneStateStore,
    InMemoryStateStore,
    StateWriteBypassError,
    StateWriteToken,
    state_key,
)
from tests.controlplane.capabilities import capability

CLASS_A = "test.seam-closure"
WHEN = datetime(2026, 7, 30, tzinfo=timezone.utc)

#: The tenant every state write below is authorized for, and the record id
#: the write files under: ``put`` derives the key from the CAPABILITY's
#: tenant and this id (D-IMPL-353 §1.3), never from a caller-supplied key.
TENANT_A = "tenant-a"
RECORD_ID = "k"


def _authorized(tenant: str = TENANT_A) -> Authorized[Execute]:
    """A genuine ``Execute`` capability — the kind a state write is a consequence
    of (``STATE_WRITE_KINDS``) — minted through the real ``mint`` from an
    allowed decision, exactly as the door does. The token seam under test is
    the D-20 one; the capability is what D-IMPL-353 §1.2 added in front of it,
    so every write here holds a real one and the token is the only thing that
    varies."""
    return capability(Execute, tenant=tenant, resource=f"{tenant}/workflow/seam-probe")


def _key(tenant: str = TENANT_A, record_id: str = RECORD_ID) -> str:
    return state_key(tenant=tenant, record_id=record_id)


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
            store.put(_authorized(), CLASS_A, "v", record_id=RECORD_ID)  # type: ignore[call-arg]
        assert store.get(CLASS_A, _key()) is None

    def test_a_forged_kwarg_token_cannot_succeed(self) -> None:
        """A genuine capability does not excuse a forged token: the two proofs
        are two proofs (D-IMPL-353 §1.5e), and the D-20 one still refuses."""
        store = InMemoryStateStore()
        with pytest.raises(StateWriteBypassError):
            store.put(
                _authorized(), CLASS_A, "v", record_id=RECORD_ID, token=object()  # type: ignore[arg-type]
            )
        assert store.get(CLASS_A, _key()) is None

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
            store.put(_authorized(), CLASS_A, "v", record_id=RECORD_ID, token=Forged())
        assert store.get(CLASS_A, _key()) is None


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
        writer.write(
            _authorized(), CLASS_A, "v", record_id=RECORD_ID, event=_event(_key())
        )
        assert store.get(CLASS_A, _key()) == "v"
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
        # The tenant prefix is no longer something a caller writes into the
        # key: it is the capability's tenant, and two capabilities for two
        # tenants file the same record id under two keys (D-IMPL-353 §1.3).
        writer.write(
            _authorized("tenant-a"),
            CLASS_A,
            "a-state",
            record_id="g",
            event=_event("tenant-a/g"),
        )
        writer.write(
            _authorized("tenant-b"),
            CLASS_A,
            "b-state",
            record_id="g",
            event=_event("tenant-b/g"),
        )
        assert store.get(CLASS_A, "tenant-a/g") == "a-state"
        assert store.get(CLASS_A, "tenant-b/g") == "b-state"
        assert [e.key for e in audit.events()] == [
            "tenant-a/g",
            "tenant-b/g",
        ]
