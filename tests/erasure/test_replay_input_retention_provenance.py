"""Record retention applies only to records the fabric's record writer filed (``D-IMPL-378``; Dave, 2026-10-07 21:11 MST).

**The hole, as measured by lane 378-provenance.** The erasure door verifies
every address a request names
(``runtime/ccf_runtime/erasure/door.py::ErasureDoor._verify_addresses``), and
its last check refused ``replay-input`` when the subject appeared in a
replay-input field (``ccf.erasure.REPLAY_INPUT_PATHS``) of the stored bytes —
ANY stored bytes, a principal's own client-lane filing included. So a tenant
could make its own client file un-erasable by shaping it like a Decision Replay
record. ``tests/erasure/test_sec009_address_verification.py`` pinned that as if
it were intended.

**Dave's ruling (21:11 MST, "yes fix both now").** Apply record-retention rules
only to records the fabric itself filed, decided by the one provenance check,
``src/ccf/replay/provenance.py::filed_by_record_writer``: the store's naming
shows the address filed under a class its ``WriteKinds`` declares under
``ReplayMint`` (a kind no door can mint) under the requesting tenant.

What this module holds, each test asserting the mechanism by name:

* bytes that validate as a ``DecisionReplayRecord``, filed on the tenant's client
  lane, are erased like any client artifact in process (the record-shaped case
  beside the pinned test's resemblance);
* the CONTROL — the same record, filed by the fabric's record writer
  (``ccf.replay.serve.ReplayWriter``), is still refused ``replay-input``;
* a store that cannot say who filed an address is refused by name,
  ``class-unverifiable``, never judged as a client artifact on the bytes' word:
  one that declares no ``WriteKinds`` (cause:
  ``ccf.replay.provenance.UnattributableRecordStore``), raw or composed with the
  erasure consult, and an erasure-consulting composition whose substrate answers
  no ``names_at``;
* the MCP-backed door (``ccf.artifacts.mcp_store.McpArtifactStore``): a client
  filing the record validator refuses is erasable through it; one the validator
  accepts is still not, because the artifact server does not serve those bytes
  on the client lane (lane 378-clientlane), so the door cannot read them to
  verify the subject — the residual, kept executable as a strict expected
  failure rather than pinned as if intended.

Tenant, principal, class and name strings are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import ccf.artifacts.mcp_store as mcp_store_module
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ArtifactErase, Execute, ReplayMint, Resume
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import compose_erasure_consult
from ccf.replay.provenance import UnattributableRecordStore, filed_by_record_writer
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.erasure import ErasureRefused
from ccf_runtime.workflow.engine import WorkflowSuspended
from tests.composition import register_typed_at_composition
from tests.erasure import harness as h
from tests.erasure.test_sec009_address_verification import _readdress
from tests.http_api.composition_authority import WORKFLOW_TRACE_CLASS
from tests.mcp import test_sec009_mcp_names_at as names_world
from tests.mcp.guarded_servers import REPLAY_RECORD_CLASS
from tests.mcp.test_c2_tenant_hold_mcp import _record
from tests.replay.authority import replay_writer
from tests.replay.test_record_provenance import _WithoutNaming

#: A subject key path a strictly valid record can carry a value at, and that
#: reaches no replay input (so the declaration accepts it, U2).
RECORD_KEY_PATH = "content_generation_path.plan_id"
#: The subject declaration that also lists the record class and the path above.
DECLARATION_URI = f"ccf-artifact://{h.TENANT}/ccf.erasure-subject-declaration/subjects@1.1.0"
#: A client document carrying the subject at its declared key path and in a
#: replay-input field — the pinned test's document.
RESEMBLANCE = {"customer": {"id": h.SUBJECT_ID}, "perspective_conditioning": {"principal_id": h.SUBJECT_ID}}


def _declaration() -> Any:
    """``h.declaration()``, plus the record class and :data:`RECORD_KEY_PATH`, at 1.1.0."""
    (base,) = h.declaration().subjects
    return h.erasure("ErasureSubjectDeclaration")(
        semver="1.1.0",
        tenant_id=h.TENANT,
        subjects=(
            h.erasure("ErasureSubjectClass")(
                class_id=base.class_id,
                key_paths=(*base.key_paths, RECORD_KEY_PATH),
                artifact_classes=(h.DOC_CLASS, REPLAY_RECORD_CLASS),
                identifier_kind=base.identifier_kind,
                subject_ref_salt=base.subject_ref_salt,
            ),
        ),
    )


def _retention() -> Any:
    """``h.retention()``, with the record class erasable beside the client class.

    So a request naming a record is refused for the record's provenance or not
    at all: with the provenance check removed, the genuine record is admitted.
    """
    terms = {"erasable": True, "reasons": ("customer-request",), "holds": (), "minimum_age": None}
    return h.erasure("RetentionHoldPolicy")(
        semver="1.0.0",
        tenant_id=h.TENANT,
        classes={
            h.DOC_CLASS: h.erasure("ClassRetention")(**terms),
            REPLAY_RECORD_CLASS: h.erasure("ClassRetention")(**terms),
        },
    )


def _deployment(tmp_path: Path) -> tuple[h.Plane, FileArtifactStore]:
    """The harness plane, and its store as a deployment whose record writer files
    :data:`REPLAY_RECORD_CLASS` under ``ReplayMint`` declares it."""
    plane = h.compose(tmp_path, policy=_retention())
    register_typed_at_composition(
        plane.registry, h.DECL_KEY, _declaration(), h.erasure("ERASURE_SUBJECT_DECLARATION")
    )
    store = FileArtifactStore(
        root=plane.store.root,
        write_kinds=WriteKinds(
            {
                WORKFLOW_TRACE_CLASS: (Execute, Resume),
                h.ERASURE_RECORD_CLASS: (ArtifactErase,),
                h.ERASURE_APPROVAL_CLASS: (ArtifactErase,),
                REPLAY_RECORD_CLASS: (ReplayMint,),
            }
        ),
    )
    return plane, store


def _record_naming_the_subject() -> DecisionReplayRecord:
    """A strictly valid record carrying the subject at :data:`RECORD_KEY_PATH`
    and in a replay-input field (``perspective_conditioning.principal_id``)."""
    base = _record(tenant=h.TENANT, principal=h.SUBJECT_ID, subject="erasure-provenance")
    record = base.model_copy(
        update={"content_generation_path": base.content_generation_path.model_copy(update={"plan_id": h.SUBJECT_ID})}
    )
    assert DecisionReplayRecord.model_validate_json(canonical_bytes(record)) == record
    return record


def _request(plane: h.Plane, address: str, artifact_class: str) -> Any:
    """The harness request, naming ``address`` under ``artifact_class``, under the 1.1.0 declaration."""
    base = h.request(plane)
    (named,) = base.addresses
    return type(base).model_validate(
        {
            **base.model_dump(),
            "subject_declaration_ref": DECLARATION_URI,
            "addresses": [
                named.model_copy(update={"content_address": address, "artifact_class": artifact_class}).model_dump()
            ],
        }
    )


def _ask(door: Any, plane: h.Plane, request: Any) -> Any:
    return h.run(
        door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request))
    )


def _erase(door: Any, plane: h.Plane, request: Any) -> Any:
    """Request, approve and complete ``request`` through ``door``; return the erasure record."""
    suspended = _ask(door, plane, request)
    assert isinstance(suspended, WorkflowSuspended), suspended
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    return h.run(
        door.complete(
            h.resume_cap(), definition_version=plane.definition_version, request=request,
            resolution=resolution, erase=h.erase_cap(request),
        )
    )


def _refused(door: Any, plane: h.Plane, request: Any) -> ErasureRefused:
    with pytest.raises(ErasureRefused) as refused:
        _ask(door, plane, request)
    assert not plane.transport.pending(tenant=h.TENANT), "a refused request starts no approval"
    return refused.value


def _mcp_client(tmp_path: Path, store: Any, monkeypatch: pytest.MonkeyPatch) -> McpArtifactStore:
    """The shipped MCP-backed store, its sessions answered in process by the shipped server over ``store``."""
    session = names_world._InProcessSession(names_world._server(tmp_path, store))

    async def run_with_session(*, url: str, operation: Any, http_client_factory: Any) -> Any:
        return await operation(session)

    monkeypatch.setattr(mcp_store_module, "run_with_session", run_with_session)
    return McpArtifactStore(url="http://artifact.invalid/mcp", bridge=names_world._Run(), write_kinds=store.write_kinds)  # type: ignore[arg-type]


# --- in process --------------------------------------------------------------------


def test_a_record_shaped_client_filing_is_erased_like_any_client_artifact(tmp_path: Path) -> None:
    """Bytes that validate as a Decision Replay record, filed by a principal on
    the tenant's client lane, carrying the subject in a replay-input field, are
    a client artifact: the door erases them like any other. Before the ruling it
    refused them ``replay-input``."""
    plane, store = _deployment(tmp_path)
    record = _record_naming_the_subject()
    filed = h.client_put(store, name="record-copy", document=json.loads(canonical_bytes(record)))
    assert DecisionReplayRecord.model_validate_json(store.get(content_address=filed.content_address)) == record
    assert filed_by_record_writer(store, content_address=filed.content_address, tenant_id=h.TENANT) is False

    request = _request(plane, filed.content_address, h.DOC_CLASS)
    erased = _erase(h.door(plane, store=store), plane, request)
    assert isinstance(erased, h.erasure("ErasureRecord")), erased
    assert [a.content_address for a in erased.addresses] == [filed.content_address]
    assert erased.retention_decision.verdict == "admit"


def test_a_record_the_fabrics_record_writer_filed_still_refuses_replay_input(tmp_path: Path) -> None:
    """The control: the same record, filed by the fabric's record writer under
    the tenant, is a Decision Replay record, and the subject in its replay-input
    field still refuses the erasure ``replay-input``, with the retention decision
    naming the code. Retention would admit the class (``_retention``), so the
    refusal is the record's provenance and nothing else."""
    plane, store = _deployment(tmp_path)
    record = _record_naming_the_subject()
    replay_writer(store, tenant=h.TENANT, artifact_class=REPLAY_RECORD_CLASS).write_replay_record(record=record)
    address = content_hash(record)
    assert {(n.tenant_id, n.artifact_class) for n in store.names_at(content_address=address)} == {
        (h.TENANT, REPLAY_RECORD_CLASS)
    }
    assert filed_by_record_writer(store, content_address=address, tenant_id=h.TENANT) is True

    refused = _refused(h.door(plane, store=store), plane, _request(plane, address, REPLAY_RECORD_CLASS))
    assert refused.reason_code == "replay-input"
    assert refused.decision is not None
    assert (refused.decision.reason_code, refused.decision.verdict, refused.decision.address) == (
        "replay-input",
        "refuse",
        address,
    )


# --- a store that cannot attribute a filing -----------------------------------------


@pytest.mark.parametrize("composition", ["raw", "composed"])
def test_a_store_that_declares_no_write_kinds_refuses_rather_than_judge_a_record_shaped_filing(
    tmp_path: Path, composition: str
) -> None:
    """Fail closed, consistent with ``UnattributableRecordStore``: a store that
    answers ``names_at`` but declares no ``WriteKinds`` cannot say whether the
    fabric's record writer filed an address, so where the answer matters — the
    subject is in a replay-input field — the door refuses by name,
    ``class-unverifiable``, with the provenance check's refusal as the cause,
    and starts nothing. It never takes the bytes for a client artifact on their
    own word. Where the answer does not matter — the plain client document,
    whose replay-input fields carry no subject — the same door erases as
    before: the question is never asked."""
    plane = h.compose(tmp_path)
    ref = h.client_put(plane.store, name="pre-validator", document=RESEMBLANCE)
    unattributing = _WithoutNaming(plane.store, drop="write_kinds")
    store = unattributing if composition == "raw" else compose_erasure_consult(
        unattributing,
        index=h.index_of(plane),
        audit_log=ControlPlaneRegistry().audit_log,
        clock=h.fabric_clock,
        control_plane=plane.registry,
        erasure_trust=h.trust(plane),
    )
    door = h.door(plane, store=store)

    refused = _refused(door, plane, _readdress(h.request(plane), ref.content_address))
    assert refused.reason_code == "class-unverifiable"
    assert isinstance(refused.__cause__, UnattributableRecordStore), refused.__cause__

    assert isinstance(_ask(door, plane, h.request(plane)), WorkflowSuspended)


def test_an_erasure_consulting_store_over_a_substrate_with_no_naming_refuses_class_unverifiable(
    tmp_path: Path,
) -> None:
    """The other reading attribution needs. A raw store with no ``names_at`` is
    refused ``class-unverifiable`` before any address is read
    (``tests/erasure/test_sec009_address_verification.py::test_a_store_that_answers_no_naming_cannot_verify_a_class_and_refuses``).
    Composed with the erasure consult, the decorator answers ``names_at`` by
    delegating, and the substrate's missing naming surfaced as an unmapped
    ``AttributeError`` — measured on the base of this lane — although the
    decorator documents that the door refuses it ``class-unverifiable``. Now it
    is refused by name, before anything starts."""
    plane = h.compose(tmp_path)
    composed = compose_erasure_consult(
        _WithoutNaming(plane.store, drop="names_at"),
        index=h.index_of(plane),
        audit_log=ControlPlaneRegistry().audit_log,
        clock=h.fabric_clock,
        control_plane=plane.registry,
        erasure_trust=h.trust(plane),
    )
    refused = _refused(h.door(plane, store=composed), plane, h.request(plane))
    assert refused.reason_code == "class-unverifiable"
    assert isinstance(refused.__cause__, AttributeError), refused.__cause__


# --- over the MCP-backed store --------------------------------------------------------


def test_over_the_mcp_backed_store_a_client_filing_with_the_subject_in_a_replay_input_field_is_erasable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pinned test's document, through the MCP-backed door. The record
    validator refuses it, so the artifact server serves it on the client lane
    and the door reads it; the provenance check reads the store's naming over the
    server's names resource, scoped to the tenant, and finds the client lane.
    Before the ruling the door refused it ``replay-input`` here too."""
    plane = h.compose(tmp_path)
    ref = h.client_put(plane.store, name="pre-validator", document=RESEMBLANCE)
    client = _mcp_client(tmp_path, plane.store, monkeypatch)
    assert filed_by_record_writer(client, content_address=ref.content_address, tenant_id=h.TENANT) is False

    suspended = _ask(h.door(plane, store=client), plane, _readdress(h.request(plane), ref.content_address))
    assert isinstance(suspended, WorkflowSuspended), suspended


class _StillUnverifiable(AssertionError):
    """The MCP-backed door refused ``subject-unverifiable`` — the measured residual."""


@pytest.mark.xfail(
    strict=True,
    raises=_StillUnverifiable,
    reason=(
        "RESIDUAL (lane 378c-d3, reported, not redesigned): the MCP artifact server does not serve"
        " client-lane bytes the record validator accepts (lane 378-clientlane), so the MCP-backed"
        " erasure door cannot read them to verify the subject and refuses subject-unverifiable;"
        " in process the same filing is erased"
    ),
)
def test_over_the_mcp_backed_store_a_record_shaped_client_filing_is_erased_like_any_client_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the ruling asks of a record-shaped client filing, through the
    MCP-backed door. It does not hold: the door reads the address through the
    artifact server, which answers record-shaped client-lane bytes exactly as a
    missing address, so the subject cannot be verified. Kept executable: the day
    the MCP path can verify such a filing, this XPASSes and fails the run."""
    plane, store = _deployment(tmp_path)
    record = _record_naming_the_subject()
    filed = h.client_put(store, name="record-copy", document=json.loads(canonical_bytes(record)))
    client = _mcp_client(tmp_path, store, monkeypatch)
    request = _request(plane, filed.content_address, h.DOC_CLASS)
    try:
        suspended = _ask(h.door(plane, store=client), plane, request)
    except ErasureRefused as refused:
        if refused.reason_code == "subject-unverifiable":
            raise _StillUnverifiable(refused.reason_code) from refused
        raise
    assert isinstance(suspended, WorkflowSuspended), suspended
