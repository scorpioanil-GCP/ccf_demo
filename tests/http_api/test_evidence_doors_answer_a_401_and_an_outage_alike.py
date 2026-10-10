"""The HTTP evidence doors answer a 401 and an outage with one ``500``: repair 2.5 (a)'s distinction stops at the door.

Lane ``378j-fixup`` item F: the "j" batch panel's F-J2-2 (Fable seat J2), confirmed by an independent verifier on
``dl-378-integ`` @ ``6cd6023e`` and identical at ``fe25536c`` (not a regression). Dave's repair 2.5 (a), 2026-10-09
10:54 MST (``D-IMPL-378``), verbatim: *"Return a typed authentication refusal for 401, preserving its distinction from
authorization denial and transport outage."* In process, a read the artifact server's guard answers 401 is the typed
authentication refusal ``ArtifactReadUnauthenticated``, and the erasure door refuses it with that cause. The three
HTTP evidence routes, ``GET /replay/decisions``, ``GET /replay/resolutions`` and ``GET /artifact/{address}``, have no
handler for it, nor for the outage ``McpServerUnreachable``: both escape the route, and the app answers each with the
framework's own ``500 Internal Server Error``, the same status, headers and body bytes. Nothing is recorded for either.

Pinned here as the behavior as built, never as an expected failure:

* the escaped exceptions still differ by type, so the distinction holds in process;
* each door's answer to the 401 is byte-identical to its answer to the outage, a ``500``;
* no decision record is filed for either, measured over a store whose reads fail and whose writes land where they can
  be counted;
* control: over the world's own store, each door serves the record.

Dave's decision 21 (a), 2026-10-09 16:38 MST (``D-IMPL-378``; the text is Grok's recommendation, which Dave adopted),
verbatim: *"(a) A typed 5xx, so a rejected credential and an outage are not the same response."* (the 16:38 MST
amendment in ``docs/DECISIONS.md``, recorded on ``main`` @ ``c470416f``). It is ruled and not yet built: until it is,
the doors answer as this module pins. When it is built, this test turns red, since it asserts that the two answers
match and the ruling makes them differ, and it is rewritten to pin the typed answer.
SEC-020 stays open: this module measures, it closes nothing. The world is
``tests/http_api/test_evidence_dereference.py``'s; the failing stores are
``tests/mcp/test_auth_401_typed_through_the_client.py``'s (a bearer token the server's verifier does not know; a
loopback port nothing listens on), declaring the fabric's write kinds. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from ccf.artifacts.protocol import ArtifactReadUnauthenticated
from ccf.mcp.errors import McpServerUnreachable
from http_api import test_evidence_dereference as ed
from http_api.conftest import Fabric
from tests.mcp.test_auth_401_typed_through_the_client import UNKNOWN, World, store_at_nothing, store_over_http

#: The three HTTP evidence routes, by label (:func:`_request` builds each one's path and query).
_ROUTES = ("GET /replay/decisions", "GET /replay/resolutions", "GET /artifact/{address}")


@dataclass(frozen=True)
class _Answer:
    """What a client is handed, and what escaped the route when the app was asked to raise it."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    escaped: type[BaseException] | None


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


def test_the_http_evidence_doors_answer_a_401_and_an_outage_with_one_500_and_record_nothing(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Each evidence door: the 401 and the outage escape as two types, are answered as one 500, and file no record."""
    governed = ed._governed(fabric, tmp_path / "control")
    address = ed._served_record(governed, principal=ed.A)
    uri = ed._uri_for(governed, address)
    control = _ask(governed.app, address, uri)
    for route, answer in control.items():
        assert (answer.status, answer.escaped) == (200, None), f"[{route}] control: the door must serve the record: {answer}"
    records = ed._decision_records(governed)
    write_kinds = fabric.store.write_kinds
    world = World(tmp_path / "world")
    seen: dict[str, dict[str, _Answer]] = {}
    with store_over_http(world.server(), UNKNOWN, write_kinds=write_kinds) as refused:
        seen["401"] = _ask(ed._governed(_over(fabric, refused), tmp_path / "401").app, address, uri)
        landing = _ReadsFailWritesLand(reads=refused, writes=fabric.store)
        seen["401, writes landing"] = _ask(ed._governed(_over(fabric, landing), tmp_path / "401-w").app, address, uri)
    with store_at_nothing(write_kinds) as nothing:
        seen["outage"] = _ask(ed._governed(_over(fabric, nothing), tmp_path / "outage").app, address, uri)
        landing = _ReadsFailWritesLand(reads=nothing, writes=fabric.store)
        seen["outage, writes landing"] = _ask(ed._governed(_over(fabric, landing), tmp_path / "outage-w").app, address, uri)
    for route in _ROUTES:
        for case, escaped in (
            ("401", ArtifactReadUnauthenticated),
            ("401, writes landing", ArtifactReadUnauthenticated),
            ("outage", McpServerUnreachable),
            ("outage, writes landing", McpServerUnreachable),
        ):
            assert seen[case][route].escaped is escaped, (
                f"[{route}, {case}] in process the read must escape as {escaped.__name__}: {seen[case][route].escaped}"
            )
        refused_answer, outage_answer = seen["401"][route], seen["outage"][route]
        assert refused_answer.status == 500, f"[{route}] the 401 is answered {refused_answer.status}, not the 500 disclosed"
        assert (refused_answer.status, refused_answer.headers, refused_answer.body) == (
            outage_answer.status, outage_answer.headers, outage_answer.body
        ), f"[{route}] the door answers the 401 and the outage differently: {refused_answer} / {outage_answer}"
        for case in ("401, writes landing", "outage, writes landing"):
            assert (seen[case][route].status, seen[case][route].body) == (refused_answer.status, refused_answer.body), (
                f"[{route}, {case}] answered otherwise than with the store failing alike: {seen[case][route]}"
            )
    assert ed._decision_records(governed) == records, (
        f"a decision record was filed for a 401 or an outage: {records} before, {ed._decision_records(governed)} after"
    )
