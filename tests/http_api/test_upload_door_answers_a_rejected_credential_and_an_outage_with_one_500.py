# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""``POST /artifact`` answers a write whose store credential is rejected exactly as it answers an outage: one ``500``.

The disclosed limit of decision 21 (a) (``D-IMPL-378``). Decision 21 (a) typed the answer at the three HTTP evidence
doors only — ``GET /replay/decisions``, ``GET /replay/resolutions`` and ``GET /artifact/{address}`` answer a credential
the artifact store's server rejects ``503`` with ``error_code`` ``artifact-store-unauthenticated``, and an outage with
the framework's ``500`` (``tests/http_api/test_evidence_doors_answer_a_401_and_an_outage_apart.py``). The upload door,
``POST /artifact``, was not changed. Its store's ``put`` raises the typed authentication refusal
``ArtifactStoreUnauthenticated`` when the server's guard answers HTTP 401 (decision 10 (b)), and the outage
``McpServerUnreachable`` when nothing answers. The route catches neither, so the framework answers both with its own
``500 Internal Server Error``: the same status, headers and body bytes.

``D-IMPL-378``, ruled by Dave on 2026-10-09 at 20:23 MST, P-1 (b): this is disclosed rather than changed — only the
three evidence doors tell a rejected credential from an outage (SP §4.10) — and this door's ``500`` is pinned by a
test. This module is that test: the limit as built, pinned, never an expected failure. A later ruled change that types
this door turns it red, and it is rewritten then to pin the typed answer. SEC-020 stays open: this module measures, it
closes nothing.

Held here:

* in process, the two still differ by type: ``ArtifactStoreUnauthenticated`` and ``McpServerUnreachable`` escape the
  route;
* the door answers both with one ``500``, the same status, headers and body bytes;
* nothing is filed: the artifact is in neither the fabric's store nor the artifact server's, and no decision record is
  filed;
* control: over the fabric's own store, the same door files the artifact and answers ``200`` with its reference.

The world is ``tests/http_api/test_evidence_dereference.py``'s; the failing stores are
``tests/mcp/test_auth_401_typed_through_the_client.py``'s (a bearer token the server's verifier does not know; a
loopback port nothing listens on), declaring the fabric's write kinds. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import hashlib
import json
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from ccf.artifacts.protocol import ArtifactStoreUnauthenticated
from ccf.contracts.canonical import canonical_bytes
from ccf.mcp.errors import McpServerUnreachable
from http_api import test_evidence_dereference as ed
from http_api.conftest import Fabric
from tests.mcp.test_auth_401_typed_through_the_client import UNKNOWN, World, store_at_nothing, store_over_http

#: A client-lane class no world here declares mechanism-written, so the capability the gate mints may write it.
_UPLOAD_CLASS = "fixture.upload-door-notes"


@dataclass(frozen=True)
class _Answer:
    """What a client is handed, and what escaped the route when the app was asked to raise it."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    escaped: type[BaseException] | None


def _upload(app: Any, name: str, payload: dict[str, object]) -> _Answer:
    """``POST /artifact`` by the entitled examiner: once as a client sees it, once with the route's exception raised."""
    request = {"json": {"artifact_class": _UPLOAD_CLASS, "name": name, "artifact": payload},
               "headers": {"Authorization": f"Bearer {ed.A_TOKEN}"}}
    served = TestClient(app, raise_server_exceptions=False).post("/artifact", **request)
    escaped: type[BaseException] | None = None
    try:
        TestClient(app, raise_server_exceptions=True).post("/artifact", **request)
    except Exception as error:  # noqa: BLE001 — the escaped type is the observation
        escaped = type(error)
    return _Answer(
        status=served.status_code,
        headers=tuple(sorted((key.lower(), value) for key, value in served.headers.items())),
        body=served.content,
        escaped=escaped,
    )


def _over(fabric: Fabric, store: Any) -> Any:
    """The fabric as ``_governed`` reads it, its store replaced by ``store``."""
    return types.SimpleNamespace(
        store=store, product_address=fabric.product_address, product_resolver=fabric.product_resolver
    )


def _address(payload: dict[str, object]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def test_post_artifact_answers_a_rejected_store_credential_and_an_outage_with_one_500_and_files_nothing(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The upload door: the 401 and the outage escape as two types, are answered as one 500, and file nothing."""
    governed = ed._governed(fabric, tmp_path / "control")
    filed = {"note": "the upload door files this over the fabric's own store"}
    control = _upload(governed.app, "filed", filed)
    assert (control.status, control.escaped) == (200, None), f"control: the door must file the artifact: {control}"
    assert json.loads(control.body)["content_address"] == _address(filed), control.body
    assert fabric.store.exists(content_address=_address(filed)), "control: the artifact was not filed"
    records = ed._decision_records(governed)

    refused_payload = {"note": "a write whose credential the artifact server's guard rejects"}
    outage_payload = {"note": "a write nothing answers"}
    write_kinds = fabric.store.write_kinds
    world = World(tmp_path / "world")
    with store_over_http(world.server(), UNKNOWN, write_kinds=write_kinds) as refused:
        rejected = _upload(ed._governed(_over(fabric, refused), tmp_path / "401").app, "refused", refused_payload)
    with store_at_nothing(write_kinds) as nothing:
        outage = _upload(ed._governed(_over(fabric, nothing), tmp_path / "outage").app, "outage", outage_payload)

    assert (rejected.status, rejected.body) == (500, b"Internal Server Error"), (
        f"the upload door no longer answers a rejected credential with the framework's 500: {rejected}"
    )
    assert (rejected.status, rejected.headers, rejected.body) == (outage.status, outage.headers, outage.body), (
        f"the upload door answers a rejected credential and an outage differently: {rejected} / {outage}"
    )
    assert rejected.escaped is ArtifactStoreUnauthenticated, (
        f"in process the rejected credential must escape as ArtifactStoreUnauthenticated: {rejected.escaped}"
    )
    assert outage.escaped is McpServerUnreachable, f"in process the outage must escape as McpServerUnreachable: {outage.escaped}"
    for payload in (refused_payload, outage_payload):
        assert not fabric.store.exists(content_address=_address(payload)), f"filed in the fabric's store: {payload}"
        assert not world.store.exists(content_address=_address(payload)), f"filed by the artifact server: {payload}"
    assert ed._decision_records(governed) == records, (
        f"a decision record was filed: {records} before, {ed._decision_records(governed)} after"
    )
