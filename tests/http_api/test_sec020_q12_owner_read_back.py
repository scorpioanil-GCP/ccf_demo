"""SEC-020 channel 3 under Dave's Q12 ruling: owner read-back is default-deny on every path.

Dave, 2026-10-07 19:31 MST, Q12: *"(a) Default-deny owner read-back, with an
explicit tenant class allowlist. Reject withholding classes—including affected
composites—and apply the restriction to existing records and every read/replay
path."*

A Decision Replay record's dimension 1 is the REAL read (``D-IMPL-371``), so the
record behind a withheld answer names what the answer hid; ``D-IMPL-345`` let
its owner at ``full`` read it back. These controls hold the owner's read-back to
default-deny on every path that can deliver a record: the HTTP replay reads by
content address and by URI, the HTTP artifact read, the MCP artifact server's
blob resource, and the MCP Experience door's argument-less ``get_replay_record``.
The owner is entitled to the class and discloses at ``full`` throughout, so a
refusal here is the read-back rule and nothing else; the refusal's mechanism is
asserted by name once the read is refused.

The guard at the end holds the other side: a read-refusal record — the evidence
read's own determination, which carries no product determination and no read of
any subject — still reads back for its owner (Dave's Q3; ``D-IMPL-345`` C20).

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import anyio
import httpx
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from http_api.conftest import call
from tests.http_api.test_sec020_withheld_record_dereference import (
    OWNER_TOKEN,
    PAVED_WITHHELD,
    _ask,
    _door,
    _reference,
)
from tests.mcp.test_c2_tenant_hold_mcp import (
    PRINCIPAL as MCP_PRINCIPAL,
)
from tests.mcp.test_c2_tenant_hold_mcp import (
    TENANT as MCP_TENANT,
)
from tests.mcp.test_c2_tenant_hold_mcp import _file, _read, _record, _world
from tests.products.test_withheld_is_indistinguishable_from_absent import (
    FROM_DECISION,
    FROM_ENTITY_FRESHNESS,
)

import pytest


def _internal_error_code(store: Any, reference: str) -> str:
    """The INTERNAL error code behind a disclosed refusal, read from its own record."""
    address = store.resolve_uri(uri=reference) if reference.startswith("ccf-artifact://") else reference
    record = DecisionReplayRecord.model_validate_json(store.get(content_address=address))
    internal = RefusalEnvelope.model_validate_json(record.content_generation_path.assembly_refusal)
    return str(json.loads(internal.fields["error_code"]))


def _owner_get(door: Any, path: str, **params: str) -> httpx.Response:
    return call(
        door.app,
        "GET",
        path,
        params=params or None,
        headers={"Authorization": f"Bearer {OWNER_TOKEN}"},
    )


@pytest.mark.parametrize("route", ["decisions", "resolutions", "artifact"])
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_q12_the_owner_cannot_read_back_a_product_record_of_a_class_the_tenant_has_not_listed(
    tmp_path: pathlib.Path, anchor: str, route: str
) -> None:
    """HTTP: the owner, granted the class at ``full``, presents the reference its
    own answer handed it — the record behind a withheld answer — to each evidence
    route. Default-deny: no class is listed, so the record does not cross."""
    with _door(tmp_path, "q12-http", anchor=anchor, holds_subject=True) as door:
        reference = _reference(_ask(door, PAVED_WITHHELD))
        store = door.opened.artifact_store
        address = store.resolve_uri(uri=reference)
        if route == "decisions":
            read = _owner_get(door, "/replay/decisions", content_address=address)
        elif route == "resolutions":
            read = _owner_get(door, "/replay/resolutions", uri=reference)
        else:
            read = _owner_get(door, f"/artifact/{address}")
        assert read.status_code != int(httpx.codes.OK), (
            f"[{anchor}, {route}] the owner read back its own product record"
            f" (status 200) although no class is listed: {read.text[:200]}"
        )
        from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415

        shell_reference = read.json()["refusal"]["replay_reference"]
        assert _internal_error_code(store, shell_reference) == ERROR_EVIDENCE_CLASS_SEALED


def test_q12_the_owner_cannot_read_back_a_product_record_through_the_mcp_artifact_blob(
    tmp_path: pathlib.Path,
) -> None:
    """MCP artifact server: the owner at ``full`` reads its own record's bytes by
    content address through the blob resource. Default-deny refuses."""
    world = _world(tmp_path)
    address = _file(world, _record(tenant=MCP_TENANT, principal=MCP_PRINCIPAL, subject="subject-q12"))
    answer = _read(world, "blob", address)
    assert answer != world.store.get(content_address=address), (
        "the owner read back its own product record's bytes through the MCP"
        " artifact blob resource although no class is listed"
    )
    shell = RefusalEnvelope.model_validate_json(answer)
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415

    assert _internal_error_code(world.recorded, shell.replay_reference) == ERROR_EVIDENCE_CLASS_SEALED


# --- the MCP Experience door's argument-less replay read ---------------------------


def _experience_server(tmp_path: pathlib.Path, *, record_json: str, reads: list[str]) -> Any:
    """The Experience door exposing only ``get_replay_record``, over a seam handing out ``record_json``."""
    from ccf_runtime.mcp.experience import GET_REPLAY_RECORD_TOOL, build_experience_server  # noqa: PLC0415
    from tests.mcp.guarded_servers import (  # noqa: PLC0415
        TENANT,
        _auth,
        _entitlement_world,
        _perspective,
        _verifier,
        authorizer_granting,
    )

    def reader() -> str:
        reads.append("read")
        return record_json

    source, recorder = _entitlement_world(tmp_path)
    return build_experience_server(
        server_name="q12-experience",
        product_resolver=lambda **kw: None,
        replay_record_reader=reader,
        get_replay_record_description="q12 fixture",
        replay_record_tenant=TENANT,
        tool_allowlist=frozenset({GET_REPLAY_RECORD_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )


def _call_replay_tool(server: Any) -> tuple[str | None, BaseException | None]:
    from ccf_runtime.mcp.experience import GET_REPLAY_RECORD_TOOL  # noqa: PLC0415
    from tests.mcp.test_product_roster import TENANTS_CLAIM_WIRE_NAME  # noqa: PLC0415
    from tests.mcp.guarded_servers import PRINCIPAL, SCOPE, TENANT  # noqa: PLC0415

    reset = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process",
                client_id=PRINCIPAL,
                scopes=[SCOPE],
                claims={TENANTS_CLAIM_WIRE_NAME: [TENANT]},
            )
        )
    )
    try:
        try:
            _, structured = anyio.run(server.call_tool, GET_REPLAY_RECORD_TOOL, {})
        except BaseException as raised:  # noqa: BLE001 — the subject under test
            return None, raised
    finally:
        auth_context_var.reset(reset)
    return str(structured["result"]), None


def test_q12_the_experience_door_does_not_serve_the_record_behind_a_withheld_answer(
    tmp_path: pathlib.Path,
) -> None:
    """MCP Experience door: ``get_replay_record`` hands any verified caller of the
    declared tenant whatever record the deployment's seam returns — here the
    record behind a withheld answer, whose dimension 1 names the acquired
    subject. Q12 requires the read-back rule on every path; this one names no
    address, so no provenance can be shown for what it would serve."""
    with _door(tmp_path, "q12-experience-source", anchor=FROM_DECISION, holds_subject=True) as door:
        reference = _reference(_ask(door, PAVED_WITHHELD))
        store = door.opened.artifact_store
        record_json = store.get(content_address=store.resolve_uri(uri=reference)).decode("utf-8")
    assert PAVED_WITHHELD in record_json, "the case was not constructed: the record does not name the subject"
    reads: list[str] = []
    served, raised = _call_replay_tool(_experience_server(tmp_path, record_json=record_json, reads=reads))
    assert served is None or PAVED_WITHHELD not in served, (
        "the Experience door served the record behind a withheld answer, the"
        " withheld subject named in its dimension 1"
    )
    assert reads == [], "the door read the record before refusing it"
    from ccf_runtime.mcp.experience import ExperienceReplayReadRefused  # noqa: PLC0415

    chain: list[BaseException] = []
    current: BaseException | None = raised
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    assert any(isinstance(link, ExperienceReplayReadRefused) for link in chain), repr(raised)


# --- the guard: a read-refusal record still reads back for its owner -----------------


def test_q12_guard_the_owner_still_reads_back_its_own_read_refusal_record(tmp_path: pathlib.Path) -> None:
    """Q3 / ``D-IMPL-345`` C20, held through Q12: a read-refusal record carries no
    product determination and no read of any subject, so the class allowlist does
    not apply to it — the owner at ``full`` reads its own refusal chain back with
    no class listed."""
    with _door(tmp_path, "q12-guard", anchor=FROM_DECISION, holds_subject=True) as door:
        refused = _owner_get(door, "/replay/decisions", content_address="e" * 64)
        assert refused.status_code != int(httpx.codes.OK), refused.text[:200]
        chain = refused.json()["refusal"]["replay_reference"]
        back = _owner_get(door, "/replay/resolutions", uri=chain)
        assert back.status_code == int(httpx.codes.OK), back.text[:300]
        record = DecisionReplayRecord.model_validate_json(back.content)
        assert record.perspective_conditioning.principal_id == "sec020-owner"
