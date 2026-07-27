"""Child process: assemble a banking Context Product and serve it over MCP.

Run as ``python tests/crossproc/servers/mcp_egress_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — that line is the
readiness handshake the parent fixture blocks on (D-16). There is no sleep
anywhere in the parent's path to this line.

**The product is assembled, not fabricated.** The whole L1→L6 slice runs here:
boot a fabric over a throwaway SQLite file, ingest the fixture envelopes
through L2, execute the four-category operator chain, project, and run the
three gates. Only a :class:`~ccf.products.gates.ServableProduct` reaches the
resolver, which is what makes the cross-process read a read of *the fabric's*
product rather than of a hand-built dict shaped like one.

**The builder is shared with the parent on purpose.**
:func:`build_servable_product` is imported by ``test_mcp_egress.py`` to compute
the value it expects to receive. Two copies of the assembly — one serving, one
asserting — would agree right up until someone changed one of them, and the
test would then be proving that two stale copies match.

**Every domain value comes from ``tests/fixtures/banking/``** — tenant, product
class, schema version, operator parameters, MAX_TTL, the server's own name.
Delete the fixtures and this file has nothing to serve (CLAUDE.md §6.4 applied
to fixture code).
"""

from __future__ import annotations

import socket
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# The child is spawned as a bare `python <file>`, so it gets none of pytest's
# sys.path work and cannot rely on a relative PYTHONPATH surviving a cwd
# change. Resolving the three roots from __file__ is what makes the child
# runnable from anywhere, which is a property the fixture depends on.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from ccf.products.gates import ServableProduct, run_gates  # noqa: E402
from ccf_runtime.mcp.egress import (  # noqa: E402
    ProductNotServable,
    build_egress_server,
    product_uri,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class ProductAddress(NamedTuple):
    """The three segments that name a product on the egress surface."""

    tenant: str
    product_class: str
    version: str

    @property
    def uri(self) -> str:
        """The ``ccf-product://`` URI this address renders to."""
        return product_uri(
            tenant=self.tenant,
            product_class=self.product_class,
            version=self.version,
        )


class AssembledProduct(NamedTuple):
    """A gated product and the address it is served at."""

    servable: ServableProduct
    address: ProductAddress
    server_name: str


def build_servable_product(*, database_path: Path) -> AssembledProduct:
    """Run the banking slice end to end and gate the result.

    The slice's wiring — resolution spec, envelopes, operator parameters,
    projection plan, product-class registration, gate invocation — is reused
    from the proto-quickstart integration module rather than re-implemented.
    That module is the repository's one worked example of assembling a product
    the way a deployment would, and a second implementation here would be a
    second thing to keep correct.

    Args:
        database_path: Where this process's throwaway graph lives. Supplied by
            the caller so the parent and the child cannot collide on a file.

    Returns:
        The gated product plus the address it is served at.
    """
    from integration.test_proto_quickstart import (  # noqa: PLC0415
        _Fabric,
        _candidate,
        _execute,
        _envelopes,
        _load,
        _product_class,
        _resolution_spec,
    )

    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    ontology: Any = _load("ontology.yaml")
    control: Any = _load("controlplane.yaml")
    events: Any = _load("events.yaml")

    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(keys["policy_bundle"], control["policy_bundle"])
    handle = boot(
        database_path=database_path,
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        fabric = _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
        execution = _execute(fabric)
        product_class = _product_class(fabric)
        gated = run_gates(
            _candidate(fabric, execution, product_class),
            engine_resolved=execution.operators_invoked,
            now=fabric.now,
            registry=fabric.registry,
            product_class=product_class,
        )
    finally:
        handle.close()

    if not isinstance(gated, ServableProduct):
        raise AssertionError(
            f"the fixture product did not pass the gates: {gated}"
        )
    return AssembledProduct(
        servable=gated,
        address=ProductAddress(
            tenant=fabric.tenant_id,
            product_class=product_class.schema_name,
            version=product_class.schema_version,
        ),
        # Deployment identity, taken from the fixture that owns it rather than
        # written here — a server name in code is a domain value in code.
        server_name=control["product_class"]["plan_id"],
    )


def build_server(*, database_path: Path) -> FastMCP:
    """Assemble the product and wrap it in the L6 egress server."""
    assembled = build_servable_product(database_path=database_path)

    def resolve(*, tenant: str, product_class: str, version: str) -> ServableProduct:
        """Serve exactly the one assembled address; refuse anything else.

        The refusal matters as much as the hit: a resolver that returned its
        single product for any URI would make the scheme-separation assertion
        in the parent test pass for the wrong reason.
        """
        requested = ProductAddress(
            tenant=tenant, product_class=product_class, version=version
        )
        if requested != assembled.address:
            raise ProductNotServable(str(requested))
        return assembled.servable

    return build_egress_server(
        server_name=assembled.server_name, resolver=resolve
    )


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import anyio
    import uvicorn

    with tempfile.TemporaryDirectory() as workspace:
        server_app = build_server(
            database_path=Path(workspace) / "egress-child.sqlite3"
        )

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(server_app.streamable_http_app(), log_level="error")
        )

        async def serve() -> None:
            async def announce() -> None:
                # A 5 ms poll of *this process's own* server object, which is
                # not the parent-side sleep-and-hope D-16 prohibits: it
                # observes a real state flag rather than guessing a duration,
                # and the parent still learns nothing until the flag flips.
                while not server.started:
                    await anyio.sleep(0.005)
                print(f"READY {port}", flush=True)

            async with anyio.create_task_group() as group:
                group.start_soon(announce)
                await server.serve(sockets=[bound])

        anyio.run(serve)


if __name__ == "__main__":
    main()
