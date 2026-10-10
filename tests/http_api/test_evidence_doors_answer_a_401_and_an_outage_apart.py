"""The HTTP evidence doors answer a 401 with a typed ``503`` and an outage with the framework's ``500`` (decision 21 (a)).

Decision 21 (a), 2026-10-09 16:38 MST (``D-IMPL-378``; the text is Grok's recommendation, which Dave adopted),
verbatim: *"(a) A typed 5xx, so a rejected credential and an outage are not the same response."* Before it, the three
HTTP evidence routes, ``GET /replay/decisions``, ``GET /replay/resolutions`` and ``GET /artifact/{address}``, had no
handler for the typed authentication refusal or for the outage ``McpServerUnreachable``: both escaped the route and
each was answered with the framework's own ``500 Internal Server Error``, the same status, headers and body bytes (the
"j" batch panel's F-J2-2, confirmed by an independent verifier on ``dl-378-integ`` @ ``6cd6023e`` and identical at
``fe25536c``). This module, as lane ``378j-fixup`` item F wrote it, pinned that, and said that it would be rewritten
to pin the typed answer once the ruling was built. This is that rewrite. SEC-020 stays open: this module measures, it
closes nothing.

The typed answer follows the HTTP door's precedent for a fault that is the deployment's and not the caller's
(``runtime/ccf_runtime/http_api/routes/__init__.py::_required_handle``, ``503`` with ``route-handle-absent``): here the
deployment's artifact store presented a credential its server's guard did not authenticate (HTTP 401). The outage's
answer is not the ruling's to change and is not changed. Held here, by status, by the refusal body's ``error_code``
and by bytes, never by message prose:

* each door answers the 401 ``503`` with the shared refusal body: ``error_code`` ``artifact-store-unauthenticated``
  (``ccf_runtime.http_api.errors.ERROR_ARTIFACT_STORE_UNAUTHENTICATED``) and a message;
* each door answers the outage as before: the framework's ``500``, ``text/plain``, ``Internal Server Error``, with
  ``McpServerUnreachable`` escaping the route;
* the two answers differ, in status and in body;
* the 401's answer is the same bytes at every door and for every ask — the served record's address and an address
  nobody filed, the record's URI and a URI naming nothing — so it tells a caller nothing about what was asked, and it
  names no address, URI, tenant, subject or store location;
* no decision record is filed for either, measured over a store whose reads fail and whose writes land where they can
  be counted;
* control: over the world's own store, each door serves the record; and the 401 store itself raises the typed
  authentication refusal for a read, so the door is answering that refusal.

The world is ``tests/http_api/test_evidence_dereference.py``'s; the failing stores are
``tests/mcp/test_auth_401_typed_through_the_client.py``'s (a bearer token the server's verifier does not know; a
loopback port nothing listens on), declaring the fabric's write kinds. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import json
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from ccf.artifacts.protocol import artifact_uri
from ccf.mcp.errors import McpServerUnreachable
from http_api import test_evidence_dereference as ed
from http_api.conftest import Fabric
from tests.mcp.test_auth_401_typed_through_the_client import (
    NOBODYS,
    UNKNOWN,
    World,
    assert_the_authentication_refusal,
    raised_by,
    store_at_nothing,
    store_over_http,
)

#: The three HTTP evidence routes, by label (:func:`_request` builds each one's path and query).
_ROUTES = ("GET /replay/decisions", "GET /replay/resolutions", "GET /artifact/{address}")

#: The code the ruling's typed answer carries, by its constant's name in ``ccf_runtime.http_api.errors``.
_CODE_NAME = "ERROR_ARTIFACT_STORE_UNAUTHENTICATED"

#: What the framework answers an exception that escapes a route: the outage's answer, which the ruling leaves as it is.
_OPAQUE_500 = (500, "text/plain; charset=utf-8", b"Internal Server Error")


@dataclass(frozen=True)
class _Answer:
    """What a client is handed, and what escaped the route when the app was asked to raise it."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    escaped: type[BaseException] | None

    @property
    def content_type(self) -> str:
        return dict(self.headers).get("content-type", "")


def _code() -> str:
    """The named constant the typed answer's ``error_code`` must equal; a MISSING CONTRACT failure if absent."""
    from ccf_runtime.http_api import errors

    code = getattr(errors, _CODE_NAME, None)
    if not isinstance(code, str) or not code:
        pytest.fail(
            f"MISSING CONTRACT: ccf_runtime.http_api.errors.{_CODE_NAME}, the typed 5xx decision 21 (a) requires"
            f" (D-IMPL-378, 2026-10-09 16:38 MST; the text is Grok's recommendation, which Dave adopted), is {code!r} on this tree"
        )
    return code


def _request(route: str, address: str, uri: str) -> tuple[str, dict[str, Any]]:
    if route == "GET /replay/decisions":
        return "/replay/decisions", {"params": {"content_address": address}}
    if route == "GET /replay/resolutions":
        return "/replay/resolutions", {"params": {"uri": uri}}
    return f"/artifact/{address}", {}


def _ask(app: Any, address: str, uri: str) -> dict[str, _Answer]:
    """Each route asked by the entitled examiner: once as a client sees it, once with the route's exception raised."""
    headers = {"Authorization": f"Bearer {ed.A_TOKEN}"}
    answers: dict[str, _Answer] = {}
    for route in _ROUTES:
        path, kwargs = _request(route, address, uri)
        served = TestClient(app, raise_server_exceptions=False).get(path, headers=headers, **kwargs)
        escaped: type[BaseException] | None = None
        try:
            TestClient(app, raise_server_exceptions=True).get(path, headers=headers, **kwargs)
        except Exception as error:  # noqa: BLE001 — the escaped type is the observation
            escaped = type(error)
        answers[route] = _Answer(
            status=served.status_code,
            headers=tuple(sorted((key.lower(), value) for key, value in served.headers.items())),
            body=served.content,
            escaped=escaped,
        )
    return answers


def _over(fabric: Fabric, store: Any) -> Any:
    """The fabric as ``_governed`` reads it, its store replaced by ``store``."""
    return types.SimpleNamespace(
        store=store, product_address=fabric.product_address, product_resolver=fabric.product_resolver
    )


class _ReadsFailWritesLand:
    """Reads from a failing store; writes to the world's own, so a record the door files is counted."""

    def __init__(self, *, reads: Any, writes: Any) -> None:
        self._reads = reads
        self._writes = writes
        self.root = getattr(writes, "root", None)
        self.write_kinds = getattr(writes, "write_kinds", None)

    def put(self, authorized: Any, artifact: object) -> Any:
        return self._writes.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        return self._reads.get(content_address=content_address)  # type: ignore[no-any-return]

    def exists(self, *, content_address: str) -> bool:
        return self._reads.exists(content_address=content_address)  # type: ignore[no-any-return]

    def resolve_uri(self, *, uri: str) -> str:
        return self._reads.resolve_uri(uri=uri)  # type: ignore[no-any-return]

    def names_at(self, *, content_address: str) -> Any:
        return self._reads.names_at(content_address=content_address)

    def match_subject(self, *args: Any, **kwargs: Any) -> Any:
        return self._reads.match_subject(*args, **kwargs)


def test_the_http_evidence_doors_answer_a_401_with_a_typed_503_and_an_outage_with_the_500_and_record_nothing(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Each evidence door: the 401 is answered a typed 503, the outage the framework's 500; nothing is recorded."""
    governed = ed._governed(fabric, tmp_path / "control")
    address = ed._served_record(governed, principal=ed.A)
    uri = ed._uri_for(governed, address)
    nobodys_uri = artifact_uri(
        tenant_id=governed.tenant, artifact_class=ed.REPLAY_RECORD_CLASS, name=NOBODYS, artifact_version=NOBODYS
    )
    asks = {"the served record": (address, uri), "nothing filed": (NOBODYS, nobodys_uri)}
    control = _ask(governed.app, address, uri)
    for route, answer in control.items():
        assert (answer.status, answer.escaped) == (200, None), f"[{route}] control: the door must serve the record: {answer}"
    records = ed._decision_records(governed)
    write_kinds = fabric.store.write_kinds
    world = World(tmp_path / "world")
    seen: dict[tuple[str, str], dict[str, _Answer]] = {}
    with store_over_http(world.server(), UNKNOWN, write_kinds=write_kinds) as refused:
        # Construction check, asserted last: this store's read IS the typed authentication refusal, so a door
        # answering it is answering that refusal.
        read_refusal = raised_by(lambda: refused.get(content_address=address), what="the 401 store's read")
        store_location = refused.url
        landing = _ReadsFailWritesLand(reads=refused, writes=fabric.store)
        for case, store in (("401", refused), ("401, writes landing", landing)):
            app = ed._governed(_over(fabric, store), tmp_path / case.replace(", ", "-").replace(" ", "-")).app
            for ask, (asked_address, asked_uri) in asks.items():
                seen[(case, ask)] = _ask(app, asked_address, asked_uri)
    with store_at_nothing(write_kinds) as nothing:
        landing = _ReadsFailWritesLand(reads=nothing, writes=fabric.store)
        for case, store in (("outage", nothing), ("outage, writes landing", landing)):
            app = ed._governed(_over(fabric, store), tmp_path / case.replace(", ", "-").replace(" ", "-")).app
            seen[(case, "the served record")] = _ask(app, address, uri)

    typed_bodies: set[bytes] = set()
    for route in _ROUTES:
        for case in ("401", "401, writes landing"):
            for ask in asks:
                answer = seen[(case, ask)][route]
                where = f"[{route}, {case}, {ask}]"
                assert answer.status == 503, f"{where} the 401 is answered {answer.status}, not the typed 503: {answer}"
                assert answer.escaped is None, f"{where} the 401 escaped the route as {answer.escaped}"
                assert answer.content_type == "application/json", f"{where} {answer.content_type!r}"
                detail = json.loads(answer.body)["detail"]
                assert set(detail) == {"error_code", "message"}, f"{where} not the shared refusal body: {detail}"
                assert detail["error_code"] == _code(), f"{where} {detail}"
                typed_bodies.add(answer.body)
        for case in ("outage", "outage, writes landing"):
            answer = seen[(case, "the served record")][route]
            where = f"[{route}, {case}]"
            assert (answer.status, answer.content_type, answer.body) == _OPAQUE_500, (
                f"{where} the outage is no longer answered as the framework's 500: {answer}"
            )
            assert answer.escaped is McpServerUnreachable, f"{where} in process the outage must escape: {answer.escaped}"
        refused_answer, outage_answer = seen[("401", "the served record")][route], seen[("outage", "the served record")][route]
        assert (refused_answer.status, refused_answer.body) != (outage_answer.status, outage_answer.body), (
            f"[{route}] the door answers the 401 and the outage alike: {refused_answer} / {outage_answer}"
        )
    assert len(typed_bodies) == 1, f"the typed 503's body differs between doors or asks: {sorted(typed_bodies)}"
    (body,) = typed_bodies
    for named in (address, uri, NOBODYS, nobodys_uri, store_location, governed.tenant, "subject-1"):
        assert named.encode() not in body, f"the typed 503 names {named!r}: {body!r}"
    assert ed._decision_records(governed) == records, (
        f"a decision record was filed for a 401 or an outage: {records} before, {ed._decision_records(governed)} after"
    )
    assert_the_authentication_refusal(read_refusal, what="the 401 store's read")
