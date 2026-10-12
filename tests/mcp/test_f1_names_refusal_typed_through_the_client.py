# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Decision 1 (A), as ruled: a names refusal reaches the MCP client as a TYPED refusal, never as an outage.

Dave, 2026-10-09 06:21 MST (``D-IMPL-378``), verbatim: *"Names changes approved: approve the uniform “cannot
verify” erasure refusal and refusal instead of an empty names list. Do not mislabel that access refusal “server
unreachable.” Preserve a typed refusal through the MCP client. Amend the pinned tests accordingly."* SEC-020 stays
open: this module measures, it closes nothing.

The certified candidate (``lane-378h-names``) has the MCP artifact server's ``names`` resource answer an address the
caller's tenant never filed with the governed dereference's refusal shell, the answer a present governed address the
caller may not read gets (``tests/mcp/test_f1_names_present_governed_and_absent_alike.py``). The client,
``src/ccf/artifacts/mcp_store.py::McpArtifactStore.names_at``, parsed the names answer as a list and raised
``ccf.mcp.errors.McpServerUnreachable`` for anything else, so that access refusal reached every consumer labeled as an
outage. Measured here as the asker of the SEC-020 worlds (``tests/products/sec020_worlds.py``), through the shipped
``McpArtifactStore`` over streamable HTTP to the shipped artifact server, presenting the asker's bearer token:

* ``names_at`` at an address the asker's tenant never filed (nobody's, and another tenant's) and at a present
  governed non-record address (the executed-query pin the asker's own question filed) raises the read-side typed
  refusal ``ccf.artifacts.protocol.ArtifactReadRefused``, carrying the server's shell parsed as a
  ``ccf.products.refusal.RefusalEnvelope``. It is not ``McpServerUnreachable`` and not ``ArtifactNotFound``, by type;
* ``ccf.replay.provenance.filed_by_record_writer`` and ``require_filed_by_record_writer`` over that store propagate
  the typed refusal: never ``False``, never an outage, never the record-not-filed absence;
* the erasure door over the MCP-backed store refuses all three kinds of address ``class-unverifiable`` and chains the
  typed refusal as the cause;
* control: an answer that is neither a list of names nor a refusal envelope is still ``McpServerUnreachable``.

The transport is the deployment's: ``ccf.mcp.client.SyncMcpBridge``, ``ccf.mcp.client.run_with_session`` and the
streamable-HTTP client, against the built server's own ASGI app with its bearer middleware, in process (an
``httpx.ASGITransport`` stands where the socket would). Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import pathlib
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

import ccf.artifacts.protocol as artifact_protocol
from ccf.artifacts.file_store import FileArtifactStore
import ccf.artifacts.mcp_store as mcp_store_module
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import ArtifactName, ArtifactNotFound, ArtifactStoreError, WriteKinds
from ccf.authz.capability import ArtifactWrite, ReplayMint
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphQuery
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.provenance import (
    RecordNotFiledByRecordWriter,
    filed_by_record_writer,
    require_filed_by_record_writer,
)
from ccf.replay.serve import QueryPinWriter
from ccf_runtime.authz.delivery_boundary import DEREFERENCE_PRODUCT_ID
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT
from tests.controlplane.capabilities import capability
from tests.erasure import harness as h
from tests.erasure.test_replay_input_retention_provenance import _deployment, _refused, _request
from tests.http_api.composition_authority import composition_replay_mint
from tests.mcp import test_sec009_mcp_names_at as names_world
from tests.mcp.test_f1_names_present_governed_and_absent_alike import _filed_governed, _names, _pins
from tests.products import sec020_worlds as w

#: An address nobody filed in any world here.
NOBODYS = hashlib.sha256(b"decision 1 (A): an address nobody filed").hexdigest()

#: A tenant no world here serves: the owner of "another tenant's filing".
ELSEWHERE = "tenant-elsewhere"

#: A class no SEC-020 world declares: a tenant's client lane.
CLIENT_CLASS = "fixture.client-notes"

#: The class the erasure world's executed-query pin is filed under, declared ``ReplayMint`` there.
QUERY_PIN_CLASS = "fixture.graph-query"

#: The bearer ``tests/mcp/test_sec009_mcp_names_at.py::_server`` issues for its one grant.
NAMES_WORLD_TOKEN = "tok"

#: The shell members a refusal renders as canonical JSON (``RefusalEnvelope.fields``).
NONEXISTENT = canonical_bytes("nonexistent").decode("utf-8")
EVIDENCE_ABSENT = canonical_bytes(ERROR_EVIDENCE_ABSENT).decode("utf-8")

#: The bridge's deadline for every call here: generous, because an in-process server answers in milliseconds.
CALL_TIMEOUT_SECONDS = 60.0


@contextlib.contextmanager
def _store_over_http(server: Any, token: str, write_kinds: WriteKinds) -> Iterator[McpArtifactStore]:
    """The shipped ``McpArtifactStore``, over streamable HTTP to ``server``'s own ASGI app, presenting ``token``.

    The server's session manager runs once per server, inside its app's lifespan, and answers requests only on the
    loop that entered it. So the lifespan is entered by ONE task on the bridge's own loop and held open while the
    store is used; every store call runs on that loop through ``SyncMcpBridge.run``, as a deployment's would.
    """
    app = server.streamable_http_app()
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:

        async def start() -> tuple[asyncio.Task[None], asyncio.Event]:
            stop = asyncio.Event()
            ready = asyncio.Event()

            async def serve() -> None:
                async with app.router.lifespan_context(app):
                    ready.set()
                    await stop.wait()

            loop = asyncio.get_running_loop()
            serving = loop.create_task(serve())
            waiting = loop.create_task(ready.wait())
            await asyncio.wait({serving, waiting}, return_when=asyncio.FIRST_COMPLETED)
            if serving.done():
                waiting.cancel()
                serving.result()
                raise AssertionError("the server's lifespan ended before it served anything")
            return serving, stop

        serving, stop = bridge.run(start())

        def http_client() -> httpx.AsyncClient:
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url=w.MCP_BASE_URL,
                headers={"Authorization": f"Bearer {token}"},
            )

        try:
            yield McpArtifactStore(
                url=f"{w.MCP_BASE_URL}/mcp",
                bridge=bridge,
                write_kinds=write_kinds,
                http_client_factory=http_client,
            )
        finally:

            async def finish() -> None:
                stop.set()
                await serving

            bridge.run(finish())


def _read_refused() -> type[BaseException]:
    """The ruled read-side typed refusal, or a MISSING CONTRACT failure that names it."""
    found = getattr(artifact_protocol, "ArtifactReadRefused", None)
    if not (isinstance(found, type) and issubclass(found, BaseException)):
        pytest.fail(
            "MISSING CONTRACT: ccf.artifacts.protocol.ArtifactReadRefused, the read-side typed refusal"
            " decision 1 (A) requires (D-IMPL-378, 2026-10-09 06:21 MST), does not exist on this tree"
        )
    return found


def _raised_by(call: Callable[[], object], *, what: str) -> BaseException:
    """What ``call`` raised; a failure naming what it returned instead, if it returned."""
    try:
        returned = call()
    except Exception as raised:  # noqa: BLE001 - the raised type IS the observation
        return raised
    pytest.fail(f"{what}: returned {returned!r} where the server refused to name the address")


def _assert_the_typed_refusal(raised: BaseException | None, address: str, *, what: str) -> RefusalEnvelope:
    """The mechanism, by type: the read-side typed refusal carrying the governed dereference's shell for ``address``."""
    # The ruling's words: an access refusal is not "server unreachable".
    assert not isinstance(raised, McpServerUnreachable), (
        f"{what}: the server's access refusal reached the client labeled an outage —"
        f" {type(raised).__name__}: {str(raised)[:300]}"
    )
    refused = _read_refused()
    assert isinstance(raised, refused), f"{what}: {type(raised).__name__}: {str(raised)[:300]}"
    # A store's determination (the write side's family), and never an absence: option C was not chosen.
    assert isinstance(raised, ArtifactStoreError), type(raised).__mro__
    assert not isinstance(raised, ArtifactNotFound), type(raised).__mro__
    envelope = getattr(raised, "envelope", None)
    assert isinstance(envelope, RefusalEnvelope), f"{what}: the typed refusal carries {envelope!r}"
    assert envelope.kind == "subject-unavailable", envelope.kind
    assert envelope.request.product_id == DEREFERENCE_PRODUCT_ID, envelope.request
    assert dict(envelope.request.parameters) == {"reference": address}, envelope.request
    return envelope


def _without_presentation(answer: Any, address: str) -> Any:
    """``answer`` less what legitimately varies: the address the caller presented, and the refusal's own record."""
    reduced = json.loads(json.dumps(answer, sort_keys=True).replace(address, "<presented-address>"))
    reduced.pop("replay_reference", None)
    return reduced


def _as_json(envelope: RefusalEnvelope) -> Any:
    return json.loads(canonical_bytes(envelope))


@pytest.mark.parametrize("shape", [w.SUBJECT_KEYED, w.SIMILARITY])
def test_names_at_raises_the_typed_refusal_for_a_query_pin_and_for_addresses_its_tenant_never_filed(
    tmp_path: pathlib.Path, shape: str
) -> None:
    """As the asker, through the shipped client: ``names_at`` at the pin the asker's own question filed, at an address
    nobody filed and at another tenant's filing raises the typed refusal carrying the server's own shell — one answer
    for the three, the ``nonexistent`` shell — while the same store, transport and token name the asker tenant's own
    filing."""
    deployment = w.BUILDERS[shape](tmp_path / shape, anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        pin = _pins(deployment)[0]
        theirs = deployment.store.put(
            capability(ArtifactWrite, tenant=ELSEWHERE, resource=f"{CLIENT_CLASS}/theirs"), {"note": "elsewhere"}
        )
        own = deployment.store.put(
            capability(ArtifactWrite, tenant=deployment.tenant, resource=f"{CLIENT_CLASS}/own"), {"note": "own"}
        )
        # Positive controls on the addresses, read as an auditor: a present governed non-record filing of the asker's
        # tenant; nobody's; another tenant's only.
        assert _filed_governed(deployment, pin), deployment.store.names_at(content_address=pin)
        assert deployment.store.names_at(content_address=NOBODYS) == ()
        assert {n.tenant_id for n in deployment.store.names_at(content_address=theirs.content_address)} == {ELSEWHERE}
        addresses = {
            "the asker's own query pin": pin,
            "an address nobody filed": NOBODYS,
            "another tenant's filing": theirs.content_address,
        }
        envelopes: dict[str, RefusalEnvelope] = {}
        with _store_over_http(w.mcp_artifact_server(deployment), w.ASKER_TOKEN, deployment.store.write_kinds) as store:
            # The other side, held: this store, transport and token are answered names where the tenant filed.
            assert store.names_at(content_address=own.content_address) == (
                ArtifactName(
                    tenant_id=deployment.tenant,
                    artifact_class=CLIENT_CLASS,
                    name="own",
                    artifact_version=own.content_address,
                ),
            )
            for what, address in addresses.items():
                raised = _raised_by(lambda a=address: store.names_at(content_address=a), what=f"[{shape}] {what}")
                envelopes[what] = _assert_the_typed_refusal(raised, address, what=f"[{shape}] {what}")
        for what, envelope in envelopes.items():
            address = addresses[what]
            assert envelope.fields.get("cause") == NONEXISTENT, (what, envelope.fields)
            assert envelope.fields.get("error_code") == EVIDENCE_ABSENT, (what, envelope.fields)
            # The server's refusal, carried whole: what the names resource answers this asker, less its own record.
            assert _without_presentation(_as_json(envelope), address) == _without_presentation(
                _names(deployment, address), address
            ), what
        # F1-1 and I6 at the client: one answer for a present pin, nobody's address and another tenant's filing.
        assert len(
            {json.dumps(_without_presentation(_as_json(e), addresses[k]), sort_keys=True) for k, e in envelopes.items()}
        ) == 1, {k: _as_json(e) for k, e in envelopes.items()}
    finally:
        deployment.close()


def test_record_provenance_over_the_mcp_store_propagates_the_typed_refusal(tmp_path: pathlib.Path) -> None:
    """``filed_by_record_writer`` reads naming only; where the server refused to name the address it cannot answer
    ``False`` (that is "not filed by the record writer", a finding the refusal does not support) and it is not an
    outage: it propagates the typed refusal. ``require_filed_by_record_writer`` does too, and never turns it into
    ``RecordNotFiledByRecordWriter`` (an absence)."""
    deployment = w.BUILDERS[w.SIMILARITY](tmp_path / "provenance", anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        pin = _pins(deployment)[0]
        assert _filed_governed(deployment, pin), deployment.store.names_at(content_address=pin)
        with _store_over_http(w.mcp_artifact_server(deployment), w.ASKER_TOKEN, deployment.store.write_kinds) as store:
            for what, address in (("the asker's own query pin", pin), ("an address nobody filed", NOBODYS)):
                raised = _raised_by(
                    lambda a=address: filed_by_record_writer(store, content_address=a, tenant_id=deployment.tenant),
                    what=f"filed_by_record_writer at {what}",
                )
                _assert_the_typed_refusal(raised, address, what=f"filed_by_record_writer at {what}")
                raised = _raised_by(
                    lambda a=address: require_filed_by_record_writer(
                        store, content_address=a, tenant_id=deployment.tenant
                    ),
                    what=f"require_filed_by_record_writer at {what}",
                )
                assert not isinstance(raised, RecordNotFiledByRecordWriter), (what, type(raised).__mro__)
                _assert_the_typed_refusal(raised, address, what=f"require_filed_by_record_writer at {what}")
    finally:
        deployment.close()


#: The erasure world's three addresses its tenant's door cannot verify over MCP: two its tenant never filed, and a
#: present governed non-record filing of its own.
DOOR_ROWS = ("another tenant's filing", "nothing filed at the address", "a present query pin")


@pytest.mark.parametrize("row", DOOR_ROWS)
def test_the_erasure_door_over_the_mcp_store_refuses_class_unverifiable_because_of_the_typed_refusal(
    tmp_path: pathlib.Path, row: str
) -> None:
    """The erasure door over the MCP-backed store refuses each address ``class-unverifiable`` ("cannot verify"), and the
    refusal it raises is chained from the typed refusal carrying the server's shell — not from an outage."""
    plane, store = _deployment(tmp_path / "plane")
    # The same substrate (one root, one naming index), declaring the query-pin class governed beside the record class.
    substrate = FileArtifactStore(
        root=store.root,
        write_kinds=WriteKinds(
            {
                **{declared: store.write_kinds.for_class(declared) for declared in store.write_kinds.declared_classes},
                QUERY_PIN_CLASS: (ReplayMint,),
            }
        ),
    )
    if row == "another tenant's filing":
        address = names_world._put(substrate, names_world.FOREIGN, "theirs", {"customer": {"id": h.SUBJECT_ID}}).content_address
        assert {n.tenant_id for n in substrate.names_at(content_address=address)} == {names_world.FOREIGN}
    elif row == "nothing filed at the address":
        address = NOBODYS
        assert substrate.names_at(content_address=address) == ()
    else:
        query = GraphQuery(tenant_id=h.TENANT, as_of=datetime(2026, 7, 30, tzinfo=UTC))
        writer = QueryPinWriter(
            authorized=composition_replay_mint(ControlPlaneRegistry(), tenant=h.TENANT, artifact_class=QUERY_PIN_CLASS),
            store=substrate,
        )
        (filed,) = writer.write_query_bytes(queries=(query,))
        address = filed.content_address
        assert address == content_hash(query)
        assert {(n.tenant_id, n.artifact_class) for n in substrate.names_at(content_address=address)} == {
            (h.TENANT, QUERY_PIN_CLASS)
        }
    server = names_world._server(tmp_path / "server", substrate)
    with _store_over_http(server, NAMES_WORLD_TOKEN, substrate.write_kinds) as client:
        refused = _refused(h.door(plane, store=client), plane, _request(plane, address, h.DOC_CLASS))
    assert refused.reason_code == "class-unverifiable", refused.reason_code
    # Amended for design 1.3, Q1 (b) / Q3 (a) (Dave, 2026-10-09 10:54 MST): the door no longer reads the names
    # resource, so its cause is the door naming path's one refusal (the uniform "cannot verify"), declined by the
    # server and raised by the client as a decline, never an outage, an absence or the requester-facing refusal.
    cause = refused.__cause__
    assert isinstance(cause, ArtifactStoreError), f"the door's cause at {row}: {type(cause).__mro__}"
    assert not isinstance(cause, (McpServerUnreachable, ArtifactNotFound, _read_refused())), type(cause).__mro__
    assert str(cause) == mcp_store_module._DOOR_NAMING_DECLINED, f"the door's cause at {row}: {cause}"


#: Answers a names resource may give that are neither a list of names nor a refusal envelope.
MALFORMED = {
    "a presence answer": '{"found": true}',
    "not JSON": "this is not JSON",
    "a shell missing its members": '{"kind": "subject-unavailable"}',
    "a list of things that are not names": '[{"tenant_id": "tenant-fixture"}]',
    "a number": "42",
}


def test_an_answer_that_is_neither_names_nor_a_refusal_is_still_an_outage(tmp_path: pathlib.Path) -> None:
    """Control: the typed refusal is read only where the answer validates as a refusal envelope. A third-party server
    whose names resource answers anything else is not an artifact server, and that is still ``McpServerUnreachable``,
    raised by the client's own judgment of the answer (chained from the ``ValueError`` that judged it) rather than by
    a call that did not complete. Positive control: the same server, transport and store read a well-formed names
    answer as names."""
    server = FastMCP("names-control", stateless_http=True, json_response=True)
    well_formed = hashlib.sha256(b"decision 1 (A): a well-formed names answer").hexdigest()
    named = ArtifactName(tenant_id="tenant-fixture", artifact_class=CLIENT_CLASS, name="n", artifact_version=well_formed)
    answers = {hashlib.sha256(label.encode("utf-8")).hexdigest(): text for label, text in MALFORMED.items()}
    answers[well_formed] = canonical_bytes([named]).decode("utf-8")

    @server.resource("ccf-artifact-names://{content_address}", mime_type="application/json")
    def names(content_address: str) -> str:
        return answers[content_address]

    with _store_over_http(server, "a-token-this-server-ignores", WriteKinds({})) as store:
        assert store.names_at(content_address=well_formed) == (named,)
        for label in MALFORMED:
            address = hashlib.sha256(label.encode("utf-8")).hexdigest()
            raised = _raised_by(lambda a=address: store.names_at(content_address=a), what=label)
            assert type(raised) is McpServerUnreachable, (label, type(raised).__mro__, str(raised)[:300])
            assert isinstance(raised.__cause__, ValueError), (label, repr(raised.__cause__))
            refused = getattr(artifact_protocol, "ArtifactReadRefused", None)
            assert refused is None or not isinstance(raised, refused), (label, type(raised).__mro__)
