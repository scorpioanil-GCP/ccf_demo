"""Child process: assemble a banking Context Product, sign it, emit it over A2A.

Run as ``python tests/crossproc/servers/a2a_producer_child.py``. Every input is
read from the environment the parent set before spawning, because
:func:`crossproc.conftest.spawn_child_server` passes no arguments — and the
environment is inherited, so nothing about the shared fixture needs changing to
add a child that needs configuration.

**A separate OS process, which is the entire point.** The producer's fabric,
its graph file, its Control Plane registry and its private key live in this
heap; the consumer's live in the parent's. "The consumer holds no write handle
to the producer's graph" is therefore literally true here rather than argued —
an in-process double would share a heap and make the claim vacuous (D-15).

**The product is assembled, not fabricated.** The whole L1→L6 slice runs here,
reusing :func:`crossproc.servers.mcp_egress_child.build_servable_product`
rather than re-implementing it: two copies of the assembly would agree right up
until someone changed one of them.

**Two messages cross the wire, and the second is deliberately broken.** The
first is the genuine signed envelope. The second splices the genuine protected
header and signature onto a *different* product's payload — so a real tampered
envelope traverses a real socket, rather than the parent mutating a value it
already holds. Both members are library-produced base64url; nothing here slices
or re-encodes anything.

**Order: emit, then announce.** ``READY {port}`` is printed only after both
carriages have been accepted, so the parent's blocking ``readline()`` is also
the gate on the exchange having happened. A child that failed to emit dies
before announcing and surfaces its stderr through the fixture (D-16). The port
it then serves hosts this peer's own inbound endpoint — the transport is
symmetric, so a producer is a peer, not a special case.

**Every domain value comes from ``tests/fixtures/banking/``** — the tenant, the
product class, the operator parameters, the peer identifiers, the endpoint
path, the body ceiling. The environment carries only which of those declared
identities *this* child is running as.
"""

from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# The child is spawned as a bare `python <file>`, so it gets none of pytest's
# sys.path work. Resolving the three roots from __file__ is what makes the
# child runnable from anywhere, which the fixture depends on.
# The repo root too (last on the path): the shared test helpers import as
# `tests.composition`, which resolves only from there (D-IMPL-354).
for _root in (_REPO_ROOT, _REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import httpx  # noqa: E402
import yaml  # noqa: E402

from ccf.peering.admission import PRODUCER_ASSERTION_HEADER  # noqa: E402
from ccf.peering.identity import (  # noqa: E402
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    SignedContextProduct,
)
from ccf.peering.protocol import PeerRef  # noqa: E402

from ccf_runtime.peering.typed_http import TypedHttpWire  # noqa: E402

#: Environment variables the parent sets. Test-side protocol vocabulary, shared
#: by this module and ``test_peering_exchange.py`` so the two cannot disagree about
#: a name.
CONSUMER_URL_VAR = "CCF_A2A_CONSUMER_URL"
PEER_ID_VAR = "CCF_A2A_PEER_ID"
KEY_DIR_VAR = "CCF_A2A_KEY_DIR"
KEY_ID_VAR = "CCF_A2A_KEY_ID"
PRODUCER_HASH_VAR = "CCF_A2A_PRODUCER_HASH"
TENANT_VAR = "CCF_A2A_TENANT"

FIXTURES = _TESTS_ROOT / "fixtures" / "banking"


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def _required(name: str) -> str:
    """Read one required environment value, or fail loudly.

    Loudly, because a child that defaulted a missing peer identity would emit
    under the wrong principal and the parent's admission assertions would then
    be testing the fixture's guess rather than the deployment's statement.
    """
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set; the parent must supply it")
    return value


def _tampered(
    genuine: SignedContextProduct, other: SignedContextProduct
) -> SignedContextProduct:
    """Splice ``genuine``'s signature onto ``other``'s payload.

    The result is well-formed — both members were produced by the JOSE library
    — and does not verify, which is precisely the shape a consumer must refuse.
    Constructed by recombining two real envelopes rather than by editing bytes,
    so nothing here hand-rolls base64url.
    """
    return SignedContextProduct(
        payload=other.payload,
        protected=genuine.protected,
        signature=genuine.signature,
    )


def main() -> None:
    """Assemble, sign, emit both messages, then serve this peer's endpoint."""
    import anyio
    import uvicorn

    from crossproc.servers.mcp_egress_child import build_servable_product

    consumer_url = _required(CONSUMER_URL_VAR)
    peer_id = _required(PEER_ID_VAR)
    key_id = _required(KEY_ID_VAR)
    producer_hash = _required(PRODUCER_HASH_VAR)
    tenant_id = _required(TENANT_VAR)
    key_dir = Path(_required(KEY_DIR_VAR))

    federation = _fixture("a2a.yaml")
    consumer_values = federation["consumer"]

    with tempfile.TemporaryDirectory() as workspace:
        assembled = build_servable_product(
            database_path=Path(workspace) / "a2a-producer-child.sqlite3"
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

        peer = PeerRef(
            tenant_id=tenant_id, peer_id=consumer_values["peer_id"]
        )
        with httpx.Client(timeout=30.0) as client:
            wire = TypedHttpWire(
                local_peer_id=peer_id,
                endpoints=lambda *, peer: consumer_url,
                http_client=client,
                clock=lambda: assembled.servable.product.temporal_boundary,
                receive_path=consumer_values["receive_path"],
                max_request_bytes=consumer_values["max_request_bytes"],
                max_pending=consumer_values["max_pending"],
            )
            wire.emit(peer=peer, signed=genuine)
            wire.emit(peer=peer, signed=_tampered(genuine, other))

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(wire.asgi_app(), log_level="error")
        )

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
