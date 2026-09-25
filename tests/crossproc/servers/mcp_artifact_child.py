"""Child process: an authenticated MCP artifact server over a file substrate.

Run as ``python tests/crossproc/servers/mcp_artifact_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — the readiness
handshake ``tests/crossproc/conftest.py`` blocks on (D-16). Nothing on the
parent's path to that line sleeps.

**The substrate is a real ``FileArtifactStore``, in this process.** That is what
makes the conformance run a cross-process proof rather than a mock exercise:
the bytes, the naming index, and the write-once behaviour are the file store's,
and everything the parent asserts about them has crossed a socket to get there.
It is also why two ``McpArtifactStore``s built against one of these servers see
one index — the server owns it, the clients hold none.

**The authenticated path is the one the suite exercises** (D-26). The child
writes a token file into its own workspace and the parent attaches the same
token; an unauthenticated conformance run would leave §7.4's "authenticated"
exactly as unproven as it was before the verifier existed.
:data:`DEV_TOKEN` is a per-run test credential that never leaves this
repository's test tree and authorizes nothing but a temporary directory.

**The credential is shared with the parent on purpose.**
:func:`authorized_http_client` is imported by the conformance suite, so the
token the client presents and the token the server recognises cannot drift into
two values that agree only until someone edits one of them — the same
discipline ``mcp_egress_child.build_servable_product`` follows for the product.
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# The child is spawned as a bare `python <file>`, so it gets none of pytest's
# sys.path work. Resolving the roots from __file__ is what makes it runnable
# from anywhere, which the fixture depends on.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import httpx  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402

from crossproc.servers.wide_authorizer import wide_authorizer  # noqa: E402
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.products.entitlement import (  # noqa: E402
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.resolver import ReplayRefusalRecorder  # noqa: E402
from ccf_runtime.authz.product_entitlement import (  # noqa: E402
    ControlPlaneProductEntitlementSource,
)

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf_runtime.mcp.artifact_server import build_artifact_server  # noqa: E402
from ccf_runtime.mcp.auth import (  # noqa: E402
    FileTokenSource,
    SourceBackedTokenVerifier,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

#: The one credential this test server recognises. A test value, generated
#: nowhere and meaningful nowhere else; the SDK ships no token of its own.
DEV_TOKEN = "ccf-conformance-dev-token"

#: A token the source will not recognise. Its whole job is to be refused.
REJECTED_TOKEN = "ccf-conformance-not-a-token"

#: Deployment vocabulary, chosen here because a test *is* the deployment.
CLIENT_ID = "ccf-conformance-client"

#: The one tenant this child serves. Its credential is scoped to exactly
#: this (``SEC-018``), and `tests/conformance/test_artifactstore.py` imports
#: it rather than keeping a second copy of the same literal — two spellings
#: of one deployment value is how a fixture drifts from the server it drives.
TENANT = "tenant-conformance"
SCOPE = "ccf:artifact"
SERVER_NAME = "ccf-artifact-conformance"

#: Issuer and resource-server identity. Metadata only — nothing dials these;
#: ``FastMCP`` renders them into its ``WWW-Authenticate`` challenge. The
#: ``.invalid`` TLD is reserved precisely so a stray resolution cannot succeed.
ISSUER_URL = "https://issuer.invalid"
RESOURCE_SERVER_URL = "https://artifact-server.invalid/mcp"

TOKEN_FILENAME = "tokens.json"
ARTIFACTS_DIRNAME = "artifacts"


def authorized_http_client(token: str = DEV_TOKEN) -> httpx.AsyncClient:
    """An HTTP client presenting ``token`` as a bearer credential.

    The shape ``ccf.mcp.client.HttpClientFactory`` asks for. ``streamable_http_client``
    takes no headers of its own, so this is where authentication enters the
    client side — and the parametrized default is what lets the suite present a
    rejected token by passing one argument.
    """
    return httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"})


def rejected_http_client() -> httpx.AsyncClient:
    """A client presenting a credential the server's source does not know."""
    return authorized_http_client(REJECTED_TOKEN)


def write_token_file(*, workspace: Path, tenant: str = TENANT) -> Path:
    """Write the child's token file and return its path.

    The credential is scoped to the one tenant this child serves
    (``SEC-018``); an unscoped grant reaches nothing.
    """
    token_file = workspace / TOKEN_FILENAME
    token_file.write_text(
        json.dumps(
            {
                DEV_TOKEN: {
                    "client_id": CLIENT_ID,
                    "scopes": [SCOPE],
                    "tenants": [tenant],
                }
            }
        ),
        encoding="utf-8",
    )
    return token_file


def build_server(*, workspace: Path) -> FastMCP:
    """Build the authenticated, authorized artifact server over a file substrate.

    ``D-IMPL-353`` §2 P5: the blob and presence resources read through the
    governed dereference, so the builder composes the dereference's three
    seams — an entitlement source, a disclosing recorder over the same
    store, and the Control Plane audit log — beside the authorizer every
    MCP builder now takes.
    """
    store = FileArtifactStore(root=workspace / ARTIFACTS_DIRNAME)
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=TENANT),
        ProductEntitlementPolicy(
            tenant_id=TENANT,
            policy_version="1.0.0",
            principals={
                CLIENT_ID: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({"artifact-child-class"}),
                    permitted_roles=frozenset({"artifact-child-role"}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: datetime.now(UTC)
    )
    return build_artifact_server(
        server_name=SERVER_NAME,
        store=store,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=write_token_file(workspace=workspace))
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(ISSUER_URL),
            resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
            required_scopes=[SCOPE],
        ),
        authorizer=wide_authorizer(scopes=(SCOPE,)),
        entitlement_source=source,
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=store,
            replay_record_class="ccf.decision-replay-record",
            tenant_id=TENANT,
            assembly_mode="algorithmic",
            disclosure_level_for=source.disclosure_level_for,
        ),
        audit_log=registry.audit_log,
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
                # A 5 ms poll of *this process's own* server object — it
                # observes a real state flag rather than guessing a duration,
                # and the parent learns nothing until the flag flips.
                while not server.started:
                    await anyio.sleep(0.005)
                print(f"READY {port}", flush=True)

            async with anyio.create_task_group() as group:
                group.start_soon(announce)
                await server.serve(sockets=[bound])

        anyio.run(serve)


if __name__ == "__main__":
    main()
