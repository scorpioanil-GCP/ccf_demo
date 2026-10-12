# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Design 1.3: the erasure door's naming path creates no subject or existence oracle for any other caller.

``D-IMPL-378``. OWED-RULINGS-3 item 5 (B) (Dave, 2026-10-09 06:21 MST, "5(B)"): *"Extend it under the same three
authorizations (full parity; needs a second new door-authorized path)."* The ruling it extends, Dave 2026-10-08 16:40
MST item 5: *"Build the narrowly authorized server-side subject-match path without serving the bytes. Test that it
creates no unauthorized subject/existence oracle."* Design 1.3, 10:54 MST: *"Q1 (b). Keep the 06:21 uniform “cannot
verify.” The door-only path must not tell the door the truth again. Q2 (a), two tools. Q3 (a), no fallback. Q4 (a),
the existing permission."*

The second path is the MCP artifact server's ``name_artifact_for_erasure`` tool. Every caller that is not the erasure
door of the caller's tenant asks both door paths about every cell — worlds that differ in what is filed (a record the
record writer filed and governed non-record evidence; client filings, record-shaped and not; another tenant's record;
nothing), every address, the subject matching or not — and gets one byte-identical answer per path, and the server
reads nothing of its substrate. Each test first runs the door itself over the same cells and requires distinct answers
and substrate reads, so a blind instrument cannot pass it.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.erasure import harness as h
from tests.mcp import test_erasure_subject_match as sm
from tests.mcp.guarded_servers import REPLAY_RECORD_CLASS
from tests.replay.authority import mechanism_put, replay_writer

#: A canary inside the governed record's stored bytes: the naming path must never carry it.
CANARY = "d3b-naming-path-canary-7c21"

KINDS = ("governed", "client", "other-tenant-governed", "empty")


def _record() -> Any:
    return sm._record_shaped(CANARY)


def _addresses() -> list[str]:
    return [
        content_hash(_record()),
        content_hash(sm.GOVERNED_DOC),
        content_hash(sm.ORDINARY),
        content_hash(sm._record_shaped_document()),
    ]


def _world(root: pathlib.Path, kind: str) -> sm._World:
    root.mkdir(parents=True, exist_ok=True)
    store: FileArtifactStore = sm._governed_store(root / "artifacts")
    if kind == "governed":
        replay_writer(store, tenant=sm.TENANT, artifact_class=REPLAY_RECORD_CLASS).write_replay_record(record=_record())
        mechanism_put(
            store, tenant=sm.TENANT, artifact_class=sm.GOVERNED, name=content_hash(sm.GOVERNED_DOC), artifact=sm.GOVERNED_DOC
        )
    elif kind == "client":
        h.client_put(store, name="ordinary", document=sm.ORDINARY)
        h.client_put(store, name="record-shaped", document=sm._record_shaped_document())
    elif kind == "other-tenant-governed":
        replay_writer(store, tenant=sm.FOREIGN, artifact_class=REPLAY_RECORD_CLASS).write_replay_record(
            record=sm._record(tenant=sm.FOREIGN, principal="p", subject="other")
        )
    spy = sm._Spy(store)
    audit_log = ControlPlaneRegistry().audit_log
    server = sm._server(root, spy, authorizer=sm._authorizer(sm._subject_match_action()), audit_log=audit_log)
    return sm._World(spy=spy, server=server, audit_log=audit_log)


def _worlds(tmp_path: pathlib.Path) -> dict[str, sm._World]:
    return {kind: _world(tmp_path / kind, kind) for kind in KINDS}


def _cells() -> list[tuple[str, str]]:
    refs = [sm._ref(h.SUBJECT_ID), sm._ref(sm.OTHER_SUBJECT)]
    return [(address, ref) for address in _addresses() for ref in refs]


def _match(world: sm._World, grant: Any, address: str, ref: str, signature: str) -> sm._Answer:
    return sm._ask_door_tool(world, grant, sm._subject_match_tool(), sm._arguments(address, ref, signature))


def _naming(world: sm._World, grant: Any, address: str, signature: str) -> sm._Answer:
    return sm._ask_door_tool(world, grant, sm._door_naming_tool(), sm._naming_arguments(address, signature))


def _door_control(worlds: dict[str, sm._World]) -> None:
    """The positive control: the door, genuinely signed, on both paths, over every world and cell, sees differences."""
    matches = {
        (kind, address, ref): _match(world, sm.DOOR, address, ref, sm._door_signature(sm._query(sm.TENANT, address, ref)))
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    namings = {
        (kind, address): _naming(world, sm.DOOR, address, sm._naming_signature(address))
        for kind, world in worlds.items()
        for address in _addresses()
    }
    verdicts = {canonical_bytes(answer.result.structuredContent) for answer in matches.values()}
    named = {answer.text for answer in namings.values()}
    assert len(verdicts) >= 3, verdicts
    assert len(named) >= 3, named
    assert sum(sum(answer.reads.values()) for answer in [*matches.values(), *namings.values()]) > 0
    governed_record = namings[("governed", content_hash(_record()))].result.structuredContent
    assert governed_record["filed_by_record_writer"] is True, governed_record


def _assert_one_answer_and_no_reads(answers: dict[Any, sm._Answer]) -> None:
    texts = {answer.text for answer in answers.values()}
    assert len(texts) == 1, "the answer depends on the world, the address or the arguments:\n" + "\n".join(
        f"{key}: {answer.call[:240]}" for key, answer in list(answers.items())[:12]
    )
    sample = next(iter(answers.values()))
    assert sample.result.isError is True, sample.call
    read = {key: dict(answer.reads) for key, answer in answers.items() if answer.reads}
    assert read == {}, f"the server read its substrate for a caller that is not the door: {read}"


def _every_cell_on_both_paths(worlds: dict[str, sm._World], grant: Any, tenant: str = sm.TENANT) -> dict[Any, sm._Answer]:
    answers: dict[Any, sm._Answer] = {}
    for kind, world in worlds.items():
        for address, ref in _cells():
            answers[("match", kind, address, ref)] = _match(
                world, grant, address, ref, sm._door_signature(sm._query(tenant, address, ref))
            )
            answers[("naming", kind, address, ref)] = _naming(
                world, grant, address, sm._naming_signature(address, tenant=tenant)
            )
    return answers


def _per_path(answers: dict[Any, sm._Answer], path: str) -> dict[Any, sm._Answer]:
    return {key: answer for key, answer in answers.items() if key[0] == path}


def test_no_identity_gets_one_answer_on_both_door_paths_and_the_server_reads_nothing(tmp_path: pathlib.Path) -> None:
    """No identity at all (the door's genuine signature presented without a credential): one answer per path, no
    substrate read. Control: the door."""
    worlds = _worlds(tmp_path)
    _door_control(worlds)
    answers = _every_cell_on_both_paths(worlds, None)
    for path in ("match", "naming"):
        _assert_one_answer_and_no_reads(_per_path(answers, path))


def test_another_tenants_bearer_gets_one_answer_on_both_door_paths_and_the_server_reads_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """A reader of another tenant presenting the door's genuine signatures: one answer per path, no substrate read."""
    worlds = _worlds(tmp_path)
    _door_control(worlds)
    answers = _every_cell_on_both_paths(worlds, sm._grant("a-reader", sm.READER_SCOPE, sm.FOREIGN))
    for path in ("match", "naming"):
        _assert_one_answer_and_no_reads(_per_path(answers, path))


def test_a_reader_of_this_tenant_without_the_grant_gets_one_answer_on_both_door_paths(tmp_path: pathlib.Path) -> None:
    """This tenant's reader, not granted ``artifact.subject.match``, with the door's genuine signatures: one answer per
    path, no substrate read (the guard refuses before either body)."""
    worlds = _worlds(tmp_path)
    _door_control(worlds)
    answers = _every_cell_on_both_paths(worlds, sm.READER)
    for path in ("match", "naming"):
        _assert_one_answer_and_no_reads(_per_path(answers, path))


#: What a principal holding the grant but not the door key can present to the naming path.
NAMING_FORGERIES = (
    "unsigned",
    "garbage",
    "another-key-under-the-door-key-id",
    "the-approvers-key",
    "the-door-key-asserting-the-record-class",
    "the-door-key-asserting-the-probe-class",
    "the-doors-subject-match-signature-replayed-as-a-naming-signature",
    "the-doors-naming-signature-over-another-address",
    "the-doors-naming-signature-for-another-tenant",
)


def _forged_naming(variant: str, address: str, ref: str) -> str:
    if variant == "unsigned":
        return ""
    if variant == "garbage":
        return "not..a-signature"
    if variant == "the-doors-subject-match-signature-replayed-as-a-naming-signature":
        return sm._door_signature(sm._query(sm.TENANT, address, ref))
    if variant == "the-doors-naming-signature-over-another-address":
        return sm._naming_signature(next(other for other in _addresses() if other != address))
    if variant == "the-doors-naming-signature-for-another-tenant":
        return sm._naming_signature(address, tenant=sm.FOREIGN)
    return sm._forged(variant, address, ref)


def test_a_principal_holding_the_grant_but_not_the_door_key_gets_one_answer_on_the_naming_path(
    tmp_path: pathlib.Path,
) -> None:
    """The strongest caller that is not the door: this tenant's agent, granted ``artifact.subject.match``, presenting
    everything but the door's signature over exactly its naming query — nothing, garbage, another key under the door's
    key id, the approvers' key, the door's key asserting the record or the probe class, the door's subject-match
    signature, the door's naming signature over another address or for another tenant. Every variant over every world
    and cell gets the one constant refusal, byte-identical, and the substrate is never read. Severing
    ``verify_door_naming_query`` turns this red: the answers then differ by world."""
    worlds = _worlds(tmp_path)
    _door_control(worlds)
    answers = {
        (variant, kind, address, ref): _naming(world, sm.AGENT, address, _forged_naming(variant, address, ref))
        for variant in NAMING_FORGERIES
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    _assert_one_answer_and_no_reads(answers)
    assert sm._refused_constant() in next(iter(answers.values())).result.content[0].text


def test_each_door_paths_signature_is_refused_on_the_other_path(tmp_path: pathlib.Path) -> None:
    """Domain separation (``DOOR_NAMING_CLASS`` against ``SUBJECT_MATCH_CLASS``): the door's own genuine naming
    signature presented to the subject match, and its genuine subject-match signature presented to the naming path,
    each get the one refusal over every world and cell, with no substrate read."""
    worlds = _worlds(tmp_path)
    _door_control(worlds)
    on_match = {
        (kind, address, ref): _match(world, sm.DOOR, address, ref, sm._naming_signature(address))
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    on_naming = {
        (kind, address, ref): _naming(world, sm.DOOR, address, sm._door_signature(sm._query(sm.TENANT, address, ref)))
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    _assert_one_answer_and_no_reads(on_match)
    _assert_one_answer_and_no_reads(on_naming)


def test_another_tenants_own_door_learns_nothing_about_this_tenants_addresses_on_the_naming_path(
    tmp_path: pathlib.Path,
) -> None:
    """Another tenant's erasure door, authorized for its own tenant and signing its own naming queries, asking about
    this tenant's addresses: one answer, the uniform refusal (design 1.3, Q1 (b)), and no substrate bytes read."""
    worlds = {kind: world for kind, world in _worlds(tmp_path).items() if kind != "other-tenant-governed"}
    answers = {
        (kind, address): _naming(world, sm.FOREIGN_DOOR, address, sm._naming_signature(address, tenant=sm.FOREIGN))
        for kind, world in worlds.items()
        for address in _addresses()
    }
    assert len({answer.text for answer in answers.values()}) == 1, {k: a.call[:200] for k, a in answers.items()}
    assert next(iter(answers.values())).result.isError is True
    assert all(answer.reads["get"] == 0 for answer in answers.values()), {k: dict(a.reads) for k, a in answers.items()}


def test_an_address_the_tenant_never_filed_is_the_uniform_refusal_to_the_door_itself(tmp_path: pathlib.Path) -> None:
    """Design 1.3, Q1 (b) (Dave, 10:54: *"Keep the 06:21 uniform “cannot verify.” The door-only path must not tell
    the door the truth again"*): the door's genuine naming query about an address its tenant never filed — another
    tenant's record, or nothing — gets the same one refusal an unauthorized caller gets, never an empty answer
    (``address-not-in-tenant`` is not told over MCP)."""
    worlds = _worlds(tmp_path)
    foreign_record = content_hash(sm._record(tenant=sm.FOREIGN, principal="p", subject="other"))
    # Positive controls: the first address really is another tenant's record, and nothing is filed in the empty world.
    filed = worlds["other-tenant-governed"].spy._inner.names_at(content_address=foreign_record)
    assert {named.tenant_id for named in filed} == {sm.FOREIGN}, filed
    assert worlds["empty"].spy._inner.names_at(content_address=foreign_record) == ()
    answers = {
        "another tenant's record": _naming(
            worlds["other-tenant-governed"], sm.DOOR, foreign_record, sm._naming_signature(foreign_record)
        ),
        "nothing filed": _naming(worlds["empty"], sm.DOOR, foreign_record, sm._naming_signature(foreign_record)),
        "an unauthorized caller": _naming(worlds["empty"], sm.AGENT, foreign_record, ""),
    }
    assert len({answer.text for answer in answers.values()}) == 1, {k: a.call[:200] for k, a in answers.items()}
    assert sm._refused_constant() in answers["nothing filed"].result.content[0].text


def test_the_naming_answer_carries_names_and_never_the_bytes(tmp_path: pathlib.Path) -> None:
    """Transport: the door's naming answer for a record the record writer filed carries the record's names and the
    provenance bit, and in every message of the exchange, both directions, neither the record's canonical bytes nor the
    canary inside them appear. Control: the canary is in the stored bytes."""
    world = _world(tmp_path / "governed", "governed")
    address = content_hash(_record())
    stored = world.spy._inner.get(content_address=address)
    assert CANARY.encode() in stored
    answer = _naming(world, sm.DOOR, address, sm._naming_signature(address))
    assert answer.result.isError is False, answer.call
    assert answer.result.structuredContent["filed_by_record_writer"] is True
    assert CANARY not in answer.text and CANARY not in answer.call
    assert stored.decode("utf-8") not in answer.text


def test_every_naming_answer_and_every_naming_refusal_past_the_guard_is_audited(tmp_path: pathlib.Path) -> None:
    """The server's audit log takes one ``authz_decision`` event per naming call that reaches the body: an answer
    keyed by the address, ``resolved`` true; a refusal — a forged signature, or an address the tenant never filed —
    keyed by the tenant, ``resolved`` false. Each names the caller and the subject-match action (Q4 (a))."""
    action = sm._subject_match_action()
    world = _world(tmp_path / "governed", "governed")
    address = content_hash(_record())

    def audited(grant: Any, at: str, signature: str) -> tuple[sm._Answer, list[Any]]:
        since = len(world.audit_log.events())
        answer = _naming(world, grant, at, signature)
        events = [e for e in world.audit_log.events()[since:] if isinstance(e, AuthzDecisionAuditEvent)]
        return answer, [(e.key, e.resolved, e.actor, e.authz_action_id) for e in events]

    answered, events = audited(sm.DOOR, address, sm._naming_signature(address))
    assert answered.result.isError is False, answered.call
    assert events == [(address, True, sm.DOOR.client_id, action)], events

    nobodys = "0" * 64
    unfiled, events = audited(sm.DOOR, nobodys, sm._naming_signature(nobodys))
    assert unfiled.result.isError is True, unfiled.call
    assert events == [(sm.TENANT, False, sm.DOOR.client_id, action)], events

    forged, events = audited(sm.AGENT, address, "")
    assert forged.result.isError is True, forged.call
    assert events == [(sm.TENANT, False, sm.AGENT.client_id, action)], events
