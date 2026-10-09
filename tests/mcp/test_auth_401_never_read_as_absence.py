"""Repair 2.5 (a) at the SDK's consumers: the typed authentication refusal is never read as absence.

Dave, 2026-10-09 10:54 MST (``D-IMPL-378``), verbatim: *"Return a typed authentication refusal for 401, preserving
its distinction from authorization denial and transport outage."* SEC-020 stays open: this module measures, it closes
nothing.

The typed refusal, ``ccf.artifacts.protocol.ArtifactReadUnauthenticated``, is an ``ArtifactStoreError``. Several
consumers read an ``ArtifactStoreError`` from a store read as ABSENCE: the replay engine's resolvers answer
``ReplayUnresolvable`` ("no ... is stored at"), and the erasure consult's record check answers an entry
``index-unsupported`` and audits ``erasure_index_unsupported``. On the base (``fe25536c``) the guard's 401 reached each
of them as ``McpServerUnreachable``, which none of them catches, so it escaped as an outage. Were the typed refusal
read as absence there, a store whose credential the server refused would make every recorded artifact look missing —
a replay would report it, and the erasure consult would audit a finding about its index that a credential caused.
Held here, through the shipped ``McpArtifactStore`` over streamable HTTP to the shipped artifact server:

* ``ccf.replay.engine.resolve_artifact`` and ``resolve_artifact_at_uri`` raise the typed refusal, never
  ``ReplayUnresolvable``;
* ``ccf.erasure.compose_erasure_consult`` raises it while checking an entry's record, and audits no
  ``erasure_index_unsupported``;
* the erasure door still refuses ``class-unverifiable``, now with the typed refusal as the cause.

Each has a positive control through the same server presenting the token its verifier knows, so the difference is
the credential's. The governed evidence read is held in ``tests/http_api/test_auth_401_never_a_recorded_absence.py``.
Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

import pytest

from ccf.artifacts.protocol import WriteKinds, artifact_uri
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import compose_erasure_consult
from ccf.erasure.index import ErasureIndexEntry
from ccf.replay.engine import ReplayUnresolvable, resolve_artifact, resolve_artifact_at_uri
from ccf.replay.record import DecisionReplayRecord
from tests.composition import declared_erasure_trust, no_erasures
from tests.erasure import harness as h
from tests.erasure.composed import _erase_capability
from tests.erasure.test_replay_input_retention_provenance import _deployment, _refused, _request
from tests.mcp.guarded_servers import TENANT
from tests.mcp.test_auth_401_typed_through_the_client import (
    KNOWN_TOKEN,
    NOBODYS,
    UNKNOWN,
    World,
    assert_the_authentication_refusal,
    raised_by,
    store_over_http,
)

#: The record class the replay resolvers are asked about; test vocabulary.
RECORD_CLASS = "fixture.auth-401-record"

#: The audit instant the erasure consult stamps; test vocabulary.
INSTANT = datetime(2026, 10, 9, tzinfo=UTC)

KNOWN = {"Authorization": f"Bearer {KNOWN_TOKEN}"}


def _resolve(how: str, store: object) -> object:
    if how == "by address":
        return resolve_artifact(store=store, content_address=NOBODYS, contract=DecisionReplayRecord)  # type: ignore[arg-type]
    return resolve_artifact_at_uri(
        store=store,  # type: ignore[arg-type]
        uri=artifact_uri(tenant_id=TENANT, artifact_class=RECORD_CLASS, name=NOBODYS, artifact_version=NOBODYS),
        contract=DecisionReplayRecord,
    )


@pytest.mark.parametrize("how", ["by address", "by URI"])
def test_replay_resolution_reports_a_401_as_the_authentication_refusal_never_as_unresolvable(
    tmp_path: pathlib.Path, how: str
) -> None:
    """``resolve_artifact`` / ``resolve_artifact_at_uri`` over a store whose credential the guard refused.

    Positive control: through the same server presenting the token it knows, nothing is filed at the address, and
    the resolver reports that as ``ReplayUnresolvable`` — the absence the server answered. With the credential
    refused the server answered nothing about the address, so the resolver must not report an absence."""
    world = World(tmp_path)
    with store_over_http(world.server(), KNOWN) as known:
        absent = raised_by(lambda: _resolve(how, known), what=f"{how}, authenticated")
        assert isinstance(absent, ReplayUnresolvable), f"{type(absent).__name__}: {str(absent)[:300]}"
    with store_over_http(world.server(), UNKNOWN) as refused:
        raised = raised_by(lambda: _resolve(how, refused), what=f"{how}, credential refused")
    assert not isinstance(raised, ReplayUnresolvable), (
        f"{how}: the guard's 401 was reported as a missing artifact — {type(raised).__name__}: {str(raised)[:300]}"
    )
    assert_the_authentication_refusal(raised, what=f"replay resolution {how}")


def _one_entry_index() -> object:
    """A declared erasure index holding one entry of ``TENANT`` whose record address nobody filed."""
    index = no_erasures()
    entry = ErasureIndexEntry(
        tenant_id=TENANT,
        content_address="ab" * 32,
        erasure_record_address="cd" * 32,
        subject_class="customer",
        request_id="r-auth-401",
        subject_ref="ef" * 32,
        approval_ref="01" * 32,
        reason="customer-request",
        erased_at=INSTANT,
        door_signature="x..y",
        door_key_id="door-1",
    )
    index.append(_erase_capability(TENANT, "customer/r-auth-401"), entry)
    return index


def test_the_erasure_consult_reports_a_401_reading_a_record_as_the_authentication_refusal_never_as_unsupported(
    tmp_path: pathlib.Path,
) -> None:
    """``compose_erasure_consult`` checks every entry against its record, read through the store it wraps.

    Positive control: through the same server presenting the token it knows, the entry's record is not filed there,
    so the entry is ``index-unsupported`` and audited ``erasure_index_unsupported`` once — the finding the consult
    makes when the store answered. With the credential refused the store answered nothing about the record, so the
    composition raises the typed refusal and audits no such finding."""
    world = World(tmp_path)
    with store_over_http(world.server(), KNOWN) as known:
        registry = ControlPlaneRegistry()
        compose_erasure_consult(
            known,
            index=_one_entry_index(),  # type: ignore[arg-type]
            audit_log=registry.audit_log,
            clock=lambda: INSTANT,
            control_plane=registry,
            erasure_trust=declared_erasure_trust(TENANT),
        )
        assert [e.action for e in registry.audit_log.events() if e.action == "erasure_index_unsupported"] == [
            "erasure_index_unsupported"
        ]
    with store_over_http(world.server(), UNKNOWN) as refused:
        registry = ControlPlaneRegistry()
        raised = raised_by(
            lambda: compose_erasure_consult(
                refused,
                index=_one_entry_index(),  # type: ignore[arg-type]
                audit_log=registry.audit_log,
                clock=lambda: INSTANT,
                control_plane=registry,
                erasure_trust=declared_erasure_trust(TENANT),
            ),
            what="the erasure consult, credential refused",
        )
        unsupported = [e for e in registry.audit_log.events() if e.action == "erasure_index_unsupported"]
    assert not unsupported, f"the guard's 401 was audited as an unsupported erasure entry: {unsupported!r}"
    assert_the_authentication_refusal(raised, what="the erasure consult's record check")


def test_the_erasure_door_over_a_store_whose_credential_is_refused_refuses_class_unverifiable_with_the_typed_cause(
    tmp_path: pathlib.Path,
) -> None:
    """The door's outcome is unchanged — ``class-unverifiable``, "cannot verify" — and the refusal it chains is now
    the typed authentication refusal, not an outage (the 401 row of SP §4.10's names-read bullet)."""
    plane, store = _deployment(tmp_path / "plane")
    world = World(tmp_path / "world")
    write_kinds = WriteKinds(
        {declared: store.write_kinds.for_class(declared) for declared in store.write_kinds.declared_classes}
    )
    with store_over_http(world.server(), UNKNOWN, write_kinds) as client:
        refused = _refused(h.door(plane, store=client), plane, _request(plane, plane.document.content_address, h.DOC_CLASS))
    assert refused.reason_code == "class-unverifiable", refused.reason_code
    assert_the_authentication_refusal(refused.__cause__, what="the door's cause")  # type: ignore[arg-type]

