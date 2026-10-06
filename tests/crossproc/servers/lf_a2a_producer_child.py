"""Child process: the same producer as ``a2a_producer_child``, over LF A2A.

Run as ``python tests/crossproc/servers/lf_a2a_producer_child.py``. Every input
is read from the environment the parent set before spawning, using the *same*
variable names :mod:`crossproc.servers.a2a_producer_child` declares — imported
from it rather than restated, so the two children cannot disagree about a name
and the parent needs one code path to configure either leg.

**This module is deliberately thin, and that is the finding.** The assembly, the
signing, the tamper construction and the emit-then-announce ordering are all
reused from the typed-HTTP child unchanged; what differs is the four lines that
build a :class:`~ccf_runtime.peering.lf_a2a.LfA2AWire` instead of a
:class:`~ccf_runtime.peering.typed_http.TypedHttpWire`, and the ASGI app that mounts
its routes. If this file had had to do more than that, the ``PeeringProtocol``
boundary would not have been the stable layer CLAUDE.md §7.2 claims it is.

**The parent's URL is a base URL here, not an endpoint.** LF A2A discovers a
peer through its Agent Card at the well-known path, so the child hands the base
URL to :class:`~ccf_runtime.peering.lf_a2a.PeerCardResolver` and
:class:`a2a.client.A2ACardResolver` fetches the consumer's real card from it.
The typed-HTTP child is handed a full receive URL instead. That difference is
the transport's, and it stops at the transport: the two products, the two
signatures and the consumer's assertions over them are identical.

**Order: emit, then announce.** ``READY {port}`` is printed only after both
carriages have been accepted, so the parent's blocking ``readline()`` is also
the gate on the exchange having happened. Nothing here is sleep-gated on the
parent's side.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import Any

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# The child is spawned as a bare `python <file>`, so it gets none of pytest's
# sys.path work. Resolving the three roots from __file__ is what makes the child
# runnable from anywhere, which the fixture depends on.
# The repo root too (last on the path): the shared test helpers import as
# `tests.composition`, which resolves only from there (D-IMPL-354).
for _root in (_REPO_ROOT, _REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import httpx  # noqa: E402
import yaml  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from ccf.peering.admission import PRODUCER_ASSERTION_HEADER  # noqa: E402
from ccf.peering.identity import (  # noqa: E402
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
)
from ccf.peering.protocol import PeerRef  # noqa: E402

from ccf_runtime.peering.lf_a2a import LfA2AWire, build_agent_card  # noqa: E402

from crossproc.servers.a2a_producer_child import (  # noqa: E402
    CONSUMER_URL_VAR,
    KEY_DIR_VAR,
    KEY_ID_VAR,
    PEER_ID_VAR,
    PRODUCER_HASH_VAR,
    TENANT_VAR,
    _required,
    _tampered,
)

FIXTURES = _TESTS_ROOT / "fixtures" / "banking"

__all__ = [
    "CONSUMER_URL_VAR",
    "KEY_DIR_VAR",
    "KEY_ID_VAR",
    "PEER_ID_VAR",
    "PRODUCER_HASH_VAR",
    "TENANT_VAR",
    "main",
]


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def main() -> None:
    """Assemble, sign, emit both messages over LF A2A, then serve this peer."""
    import tempfile  # noqa: PLC0415

    import anyio  # noqa: PLC0415
    import uvicorn  # noqa: PLC0415

    from crossproc.servers.mcp_egress_child import (  # noqa: PLC0415
        build_servable_product,
    )

    consumer_base_url = _required(CONSUMER_URL_VAR)
    peer_id = _required(PEER_ID_VAR)
    key_id = _required(KEY_ID_VAR)
    producer_hash = _required(PRODUCER_HASH_VAR)
    tenant_id = _required(TENANT_VAR)
    key_dir = Path(_required(KEY_DIR_VAR))

    federation = _fixture("a2a.yaml")
    consumer_values = federation["consumer"]
    lf_values = federation["lf_a2a"]

    with tempfile.TemporaryDirectory() as workspace:
        assembled = build_servable_product(
            database_path=Path(workspace) / "lf-a2a-producer-child.sqlite3"
        )
        product = assembled.servable.product

        provider = DetachedJwsIdentityProvider(
            key_source=FileBackedKeySource(directory=key_dir)
        )
        # `SEC-022`: every envelope carries its issuance claims, issued at the
        # fixture's PINNED decision instant — the one the consumer admits at —
        # and never `datetime.now()`, which would refuse every admission as
        # `stale-issuance`. Each signing mints its own nonce.
        from tests.peering.issuance_fixture import issuance_member

        genuine = provider.sign(
            product=product,
            key_id=key_id,
            assertions={
                PRODUCER_ASSERTION_HEADER: producer_hash,
                **issuance_member(product=product, issued_at=assembled.now),
            },
        )
        # A second, genuinely different product, signed the same way, purely so
        # its payload member exists to be spliced onto the genuine signature.
        other = provider.sign(
            product=product.model_copy(
                update={"payload": {**product.payload, "entity_count": -1}}
            ),
            key_id=key_id,
            assertions={
                PRODUCER_ASSERTION_HEADER: producer_hash,
                **issuance_member(product=product, issued_at=assembled.now),
            },
        )

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]

        card = build_agent_card(
            name=f"{lf_values['card']['name']}-{peer_id}",
            version=lf_values["card"]["version"],
            description=lf_values["card"]["description"],
            rpc_url=f"http://127.0.0.1:{port}{lf_values['rpc_path']}",
        )
        wire = LfA2AWire(
            local_peer_id=peer_id,
            agent_card=card,
            cards=lambda *, peer: consumer_base_url,
            http_client_factory=lambda: httpx.AsyncClient(timeout=30.0),
            clock=lambda: assembled.servable.product.temporal_boundary,
            rpc_path=lf_values["rpc_path"],
            max_message_bytes=consumer_values["max_request_bytes"],
            max_pending=consumer_values["max_pending"],
        )

        peer = PeerRef(tenant_id=tenant_id, peer_id=consumer_values["peer_id"])
        wire.emit(peer=peer, signed=genuine)
        wire.emit(peer=peer, signed=_tampered(genuine, other))

        app = FastAPI()
        for route in wire.routes():
            app.router.routes.append(route)

        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))

        async def serve() -> None:
            async def announce() -> None:
                # A 5 ms poll of *this process's own* server object — not the
                # parent-side sleep-and-hope D-16 prohibits.
                while not server.started:
                    await anyio.sleep(0.005)
                print(f"READY {port}", flush=True)

            async with anyio.create_task_group() as group:
                group.start_soon(announce)
                await server.serve(sockets=[bound])

        anyio.run(serve)


if __name__ == "__main__":
    main()
