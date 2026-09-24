"""A REAL producer door in ANOTHER PROCESS, for `D-IMPL-340`'s proofs.

Boots the fixture child product (`tests/products/provider_boot.py`'s deployment)
under its **own tenant** — `PRODUCER_TENANT`, not the consumer's — holds the
fabric open for the process lifetime, and serves it through the SDK's own
authenticated, entitled L6 egress door with the parameterized product tool
exposed (`build_egress_server(expose_product_tool=True)`). The door stamps a
:class:`~ccf.products.door.ProducerAssertion` naming `PRODUCER_ID` and
`PRODUCER_TENANT` — the values a consumer's `ccf.mcp-producer` registration
is expected to hold the answer to.

**No consumer imports this module.** The consumer process holds a client, a
registration and a gate; the assembler, the fabric and the store all live here,
which is what proof 2 (*no producer assembler in the consumer process*)
measures.

Spawned by `tests/crossproc/conftest.py::spawn_child_server` as a bare
``python <this file>``: binds an ephemeral loopback port, prints
``READY {port}`` on stdout once listening, serves streamable-HTTP MCP at
``/mcp``, and exits on SIGTERM. The bearer credential is the fixed test token
`DEV_TOKEN`, the shipped `mcp_egress_child.py` posture, so the parent presents
it without a side channel.

**Sabotage knobs, read from the environment the parent spawned this process
with.** They exist so the *consumer's* admission can be shown to refuse a door
that claims the wrong thing, without a second server module per claim:

* ``CCF_TEST_PRODUCER_ASSERT_ID`` — assert this producer id instead of
  `PRODUCER_ID` (proof 5: wrong producer refuses).
* ``CCF_TEST_PRODUCER_ASSERT_TENANT`` — assert this tenant instead of
  `PRODUCER_TENANT` (proof 6: wrong producer tenant refuses, on the
  assertion leg).
* ``CCF_TEST_PRODUCER_NO_ASSERTION=1`` — build the door with no producer
  identity at all (the `producer-unasserted` refusal).

The product itself is governed the same way under every knob; only the door's
claim about itself moves.
"""

from __future__ import annotations

import copy
import json
import os
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# Spawned as a bare `python <file>`, so none of pytest's sys.path work applies.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT, _REPO_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

from tests.crossproc.servers.product_producer_identity import (  # noqa: E402
    DEV_TOKEN,
    PRODUCER_ID,
    PRODUCER_TENANT,
    PRODUCT_CLASS,
)
PRINCIPAL = "principal-fixture"
ROLE = "role-fixture"
SCOPE = "ccf:egress"
ISSUER_URL = "https://issuer.invalid"
RESOURCE_SERVER_URL = "https://child-producer.invalid/mcp"
TOOL_DESCRIPTION = "Ask fixture.child-product a §6.3-addressed question."
TOKEN_FILENAME = "tokens.json"


def _retenanted(document: Any, *, from_tenant: str, to_tenant: str) -> Any:
    """The fixture documents with every occurrence of the tenant re-homed.

    The producer is a separate deployment; its fabric, its policy keys and its
    entitlement policy all carry ITS tenant. A recursive replace over the
    fixture documents is the cheapest honest way to make that so without a
    second artifact set.
    """
    if isinstance(document, str):
        return document.replace(from_tenant, to_tenant)
    if isinstance(document, dict):
        return {
            _retenanted(key, from_tenant=from_tenant, to_tenant=to_tenant): _retenanted(
                value, from_tenant=from_tenant, to_tenant=to_tenant
            )
            for key, value in document.items()
        }
    if isinstance(document, list):
        return [
            _retenanted(item, from_tenant=from_tenant, to_tenant=to_tenant)
            for item in document
        ]
    return document


def build_server(workspace: Path) -> FastMCP:
    """Boot the child fabric under `PRODUCER_TENANT` and put the SDK door over it."""
    from mcp.server.auth.settings import AuthSettings  # noqa: PLC0415
    from pydantic import AnyHttpUrl  # noqa: PLC0415

    from ccf.artifacts.file_store import FileArtifactStore  # noqa: PLC0415
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415
    from ccf.deployment import load_and_boot  # noqa: PLC0415
    from ccf.products.entitlement import (  # noqa: PLC0415
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf.products.resolver import (  # noqa: PLC0415
        GovernedResolver,
        ReferencePolicyConstraintResolver,
        ReplayRefusalRecorder,
    )
    from ccf.projection.plan import Perspective  # noqa: PLC0415
    from ccf_runtime.authz.product_entitlement import (  # noqa: PLC0415
        ControlPlaneProductEntitlementSource,
        TokenGrant,
    )
    from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier  # noqa: PLC0415
    from ccf_runtime.mcp.egress import build_egress_server  # noqa: PLC0415

    from tests.deployment.conftest import (  # noqa: PLC0415
        ARTIFACT_SET,
        SIGNAL_BATCH_KEY,
        SIMILARITY_KEY,
        TENANT,
        manifest_document,
        write_artifact,
    )
    from tests.products.provider_boot import (  # noqa: PLC0415
        CHILD_CLASS_KEY,
        CHILD_REQUEST_CONTRACT_KEY,
        child_product_class,
        child_request_contract,
    )
    from tests.products.test_resolver_seam import (  # noqa: PLC0415
        DEBT_PROFILE_KEY,
        OBLIGATION_ON_OK,
        REPLAY_RECORD_CLASS,
        REQUEST_CONTRACT_CLASS_ID,
        _Booted,
        _arguments,
    )

    def retenant(document: Any) -> Any:
        return _retenanted(document, from_tenant=TENANT, to_tenant=PRODUCER_TENANT)

    root = workspace / "deployment"
    root.mkdir(parents=True, exist_ok=True)
    for _key, filename, _cid, _role, _reg, document in ARTIFACT_SET:
        write_artifact(root, filename, retenant(copy.deepcopy(document)))
    write_artifact(root, "product-class-child.yaml", retenant(child_product_class()))
    write_artifact(
        root, "request-contract-child.yaml", retenant(child_request_contract())
    )
    write_artifact(
        root,
        "debt-profile.yaml",
        {
            "semver": "1.0.0",
            "risk_sensitivity": "1",
            "forced_llm_threshold": "0.30",
            "fail_closed_threshold": "0.70",
            "signal_obligations": [{"signal": "ok", "obligation_ref": OBLIGATION_ON_OK}],
        },
    )
    body = retenant(manifest_document())
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "product-class-child.yaml",
            "key": CHILD_CLASS_KEY,
            "class_id": "ccf.product-class",
            "role": "register",
            "registration": "typed",
        },
        {
            "path": "request-contract-child.yaml",
            "key": CHILD_REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
        {
            "path": "debt-profile.yaml",
            "key": DEBT_PROFILE_KEY,
            "class_id": "ccf.debt-profile",
            "role": "register",
            "registration": "typed",
        },
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(workspace / "producer.sqlite3")},
    )
    for envelope in fabric.artifacts[SIGNAL_BATCH_KEY].envelopes:
        fabric.handle.worker.ingest(envelope)
    store = FileArtifactStore(root=workspace / "artifacts")
    booted = _Booted(fabric=fabric, control_plane=control_plane, store=store, root=root)

    # The fixture resolver wiring, with the two tenant-bound members re-homed.
    arguments = _arguments(booted)
    arguments.update(
        product_class_key=CHILD_CLASS_KEY,
        request_contract_key=CHILD_REQUEST_CONTRACT_KEY,
        operator_parameter_keys=(SIMILARITY_KEY,),
        composite_children=None,
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=control_plane,
            entitlement_key=product_entitlement_key(tenant_id=PRODUCER_TENANT),
        ),
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=store,
            replay_record_class=REPLAY_RECORD_CLASS,
            tenant_id=PRODUCER_TENANT,
            assembly_mode="algorithmic",
        ),
    )
    resolver = GovernedResolver(**arguments)

    control_plane.register_typed(
        product_entitlement_key(tenant_id=PRODUCER_TENANT),
        ProductEntitlementPolicy(
            tenant_id=PRODUCER_TENANT,
            policy_version="1.0.0",
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({PRODUCT_CLASS}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    entitlement_source = ControlPlaneProductEntitlementSource(
        control_plane=control_plane, clock=lambda: datetime.now(UTC)
    )
    tokens = workspace / TOKEN_FILENAME
    tokens.write_text(
        json.dumps(
            {
                DEV_TOKEN: {
                    "client_id": PRINCIPAL,
                    "scopes": [SCOPE],
                    # The producer's OWN tenant, plus the two neighbours this
                    # suite addresses to prove what the door refuses about
                    # them. The tenancy floor would otherwise stop those calls
                    # first and the door's own refusals would go untested; the
                    # floor is proven in `tests/mcp/test_tenant_guard.py`
                    # (`SEC-018`).
                    "tenants": sorted(
                        {PRODUCER_TENANT, TENANT, "some-other-tenant"}
                    ),
                }
            }
        ),
        encoding="utf-8",
    )

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(principal_id=grant.client_id, role=ROLE)

    if os.environ.get("CCF_TEST_PRODUCER_NO_ASSERTION") == "1":
        identity: dict[str, str] = {}
    else:
        identity = {
            "producer_id": os.environ.get("CCF_TEST_PRODUCER_ASSERT_ID", PRODUCER_ID),
            "producer_tenant": os.environ.get(
                "CCF_TEST_PRODUCER_ASSERT_TENANT", PRODUCER_TENANT
            ),
        }
    return build_egress_server(
        server_name=PRODUCER_TENANT,
        resolver=resolver,
        token_verifier=SourceBackedTokenVerifier(source=FileTokenSource(path=tokens)),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(ISSUER_URL),
            resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
            required_scopes=[SCOPE],
        ),
        entitlement_source=entitlement_source,
        perspective_resolver=resolve_perspective,
        refusal_recorder=arguments["refusal_recorder"],
        expose_product_resource=False,
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
        **identity,
    )


def main() -> None:
    import tempfile  # noqa: PLC0415

    import anyio  # noqa: PLC0415
    import uvicorn  # noqa: PLC0415

    workspace = Path(tempfile.mkdtemp(prefix="child-product-producer-"))
    server_app = build_server(workspace)

    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(server_app.streamable_http_app(), log_level="error")
    )

    async def serve() -> None:
        async def announce() -> None:
            while not server.started:
                await anyio.sleep(0.005)
            print(f"READY {port}", flush=True)

        async with anyio.create_task_group() as group:
            group.start_soon(announce)
            await server.serve(sockets=[bound])

    anyio.run(serve)


if __name__ == "__main__":
    main()
