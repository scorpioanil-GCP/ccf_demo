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

import json
import socket
import sys
import tempfile
from datetime import UTC, datetime
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

import httpx  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402

from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.products.entitlement import (  # noqa: E402
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.gates import ServableProduct, run_gates  # noqa: E402
from ccf.products.request import ProductRequest  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402
from ccf_runtime.authz.product_entitlement import (  # noqa: E402
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.mcp.auth import (  # noqa: E402
    FileTokenSource,
    SourceBackedTokenVerifier,
    TokenGrant,
)
from ccf_runtime.mcp.egress import (  # noqa: E402
    ProductNotServable,
    build_egress_server,
    product_uri,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

#: The one credential this test server recognises. A test value, meaningful
#: nowhere else; the SDK ships no token of its own.
DEV_TOKEN = "ccf-egress-dev-token"

#: Deployment vocabulary, chosen here because a test *is* the deployment. The
#: scope and the issuer are this server's; the *principal* is not chosen here
#: — it is the banking fixture's declared perspective principal, so the token
#: identity, the entitlement policy, and the product the fabric assembles all
#: name the same caller (CLAUDE.md §6.4 applied to fixture code).
SCOPE = "ccf:egress"
ISSUER_URL = "https://issuer.invalid"
RESOURCE_SERVER_URL = "https://egress-server.invalid/mcp"

TOKEN_FILENAME = "tokens.json"

#: The entitlement policy's own version lane. A fixture value.
POLICY_VERSION = "1.0.0"

#: The instant the child's audit events carry. Injected, never read from a
#: wall clock — the audit-module discipline, and it keeps the child's log
#: reproducible.
AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)


def authorized_http_client(token: str = DEV_TOKEN) -> httpx.AsyncClient:
    """An HTTP client presenting ``token`` as a bearer credential."""
    return httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"})


def write_token_file(*, workspace: Path, client_id: str) -> Path:
    """Write the child's token file for ``client_id`` and return its path."""
    token_file = workspace / TOKEN_FILENAME
    token_file.write_text(
        json.dumps({DEV_TOKEN: {"client_id": client_id, "scopes": [SCOPE]}}),
        encoding="utf-8",
    )
    return token_file


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
    """A gated product, the address it is served at, and who may receive it."""

    servable: ServableProduct
    address: ProductAddress
    server_name: str
    principal_id: str
    role: str


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
        backend="sqlite",
        connection={"database_path": database_path},
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
        # The caller this deployment declares, and the capacity it may ask in.
        # Both come from the same fixture the assembly path conditions on, so
        # the token identity, the entitlement policy and the product agree by
        # construction rather than by coincidence.
        principal_id=control["perspective"]["principal_id"],
        role=control["perspective"]["role"],
    )


def build_entitlement_registry(assembled: AssembledProduct) -> ControlPlaneRegistry:
    """Register this deployment's product entitlement policy.

    Registration is adopter code: no deployment manifest can name
    ``ccf.product-entitlement-policy`` (15.5-03's placement), so the door's
    composition root registers it against the real contract — which is what
    makes a near-miss a validation failure here rather than a refusal at the
    first served call.
    """
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=assembled.address.tenant),
        ProductEntitlementPolicy(
            tenant_id=assembled.address.tenant,
            policy_version=POLICY_VERSION,
            principals={
                assembled.principal_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset(
                        {assembled.address.product_class}
                    ),
                    permitted_roles=frozenset({assembled.role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return registry


def build_server(*, workspace: Path) -> FastMCP:
    """Assemble the product and wrap it in the authenticated egress server."""
    assembled = build_servable_product(
        database_path=workspace / "egress-child.sqlite3"
    )
    registry = build_entitlement_registry(assembled)

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ServableProduct:
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

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """Derive the caller's capacity from its verified identity.

        This deployment's statement, not the SDK's: the role comes from the
        fixture's declared perspective, and the subject is the verified
        ``client_id`` — never a value the caller supplied. Whatever this
        returns is still checked against the principal's grant before a
        product is resolved, so widening it here would not widen the door.
        """
        return Perspective(
            principal_id=grant.client_id,
            role=requested_role if requested_role is not None else assembled.role,
        )

    return build_egress_server(
        server_name=assembled.server_name,
        resolver=resolve,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(
                path=write_token_file(
                    workspace=workspace, client_id=assembled.principal_id
                )
            )
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(ISSUER_URL),
            resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
            required_scopes=[SCOPE],
        ),
        entitlement_source=ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: AUDIT_INSTANT
        ),
        perspective_resolver=resolve_perspective,
    )


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import anyio
    import uvicorn

    with tempfile.TemporaryDirectory() as workspace:
        server_app = build_server(workspace=Path(workspace))

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
