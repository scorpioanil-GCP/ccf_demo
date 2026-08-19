"""The fixture deployment's own MCP server program, spoken over stdio.

**A deployment's program, not the SDK's, and that is the point.**
``ccf_runtime.mcp.egress::build_egress_server`` requires a server name, a token
verifier, auth settings, an entitlement source and a perspective resolver —
five deployment values in their entirety (CINV-01), which is exactly why the
SDK ships no server entry point and why
:mod:`ccf.client.adapters.mcp_stdio` launches a program it knows nothing about.

**It sits beside the deployment rather than inside it**, and that is a shipped
invariant rather than a filing preference: ``D-IMPL-141`` Amendment A.3 grants
the deployment root **one** Python module — the projection — and
``tests/client/test_data_only_deployment.py`` refuses a second by name. The
first draft of this program lived in the root and that gate caught it, which is
why ``binding.yaml``'s ``server:`` key resolves against the directory *holding*
the deployment rather than against the root (``D-10``). The deployment states
where its program is; an ``mcp+stdio`` address names the root and reads it from
there.

**It boots through the same function the in-process adapter boots through.**
``ccf.client.adapters.inprocess::_boot`` composes this deployment's governed
resolver from its two documents, and this program calls it rather than
composing a second one. That is what makes the conformance suite's parity legs
a claim about *two transports*: if this program built its own resolver, a
passing leg would only show that two compositions happened to agree — and a
resolver returning the narrower ``ServableProduct`` would emit
``replay_ref=None`` over MCP and disagree with the in-process leg on a field
``assert_served_parity`` compares.

**The private reach is deliberate here and is deliberately not the adopter's
path.** ``_boot`` is private, and a review of ``D-IMPL-150`` (Dave, 2026-08-17)
asked whether a fixture should be reaching for it. The answer kept it, on the
grounds above: this file's job is to make *the SDK's* parity gate a statement
about transports, and sharing the composition is what buys that. The
adoptability question the finding was really about is answered where it
matters — ``examples/hw1-companies-over-revenue/server/serve.py`` stands the
same door up through the **public** seams only (``load_config_and_boot``,
``build_governed_resolver``, ``load_binding_document``) and is exercised on
every push by ``tests/examples/test_hw1_two_transports.py``. So the public path
is demonstrated and measured; this fixture buys something else.

Identity over stdio, stated rather than smuggled
-------------------------------------------------
**MCP stdio carries no authentication channel.** ``FastMCP`` installs its
bearer middleware on the HTTP app and there is no HTTP app here, so
``get_access_token()`` inside the door's handler finds nothing and the door
refuses every caller as unverified. The transport's own security boundary is
process ownership: this server is a child that this deployment's client
spawned, under the same user, on the same host, with no socket anywhere.

So this deployment states who its stdio caller is, once, before serving. That
is a **deployment's** decision about its own trust boundary, and the
deployment's own program is the only place it may be written. The verifier and
auth settings below are supplied because the builder requires them together
(``D-03``) and because this same deployment is reachable over HTTP with them in
force; over stdio they are inert.

Every value that identifies this deployment is read from its own documents
rather than spelled — the No-Hardcoding Rule (CLAUDE.md §6.4) scopes to
``tests`` through ``tools/lints/__main__.py::RULE_TREE_SCOPE``.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from ccf.client.adapters.binding_document import load_binding_document
from ccf.client.adapters.inprocess import _boot
from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    TokenGrant,
)
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import build_egress_server

#: The prose this deployment's tool advertises — a deployment value the SDK
#: holds no default for, and the one string here this deployment must write.
TOOL_DESCRIPTION = "Answer this deployment's declared question, over stdio."

#: The scope this deployment's HTTP posture requires. Inert over stdio, where
#: there is no bearer token to carry it.
SCOPE = "ccf.product.read"

#: Where the verifier reads its token table — written per boot into the
#: deployment's own private copy, and never committed.
TOKEN_FILE = "stdio-tokens.json"


def serve(root: Path) -> None:
    """Boot the deployment at ``root``, expose its product door, serve on stdio."""
    document = load_binding_document(root)
    booted = _boot(document)
    perspective = document.perspective
    declaration = booted.fabric.artifacts[document.product_class_key]
    if not isinstance(declaration, ProductClassDeclaration):  # pragma: no cover
        raise TypeError(
            f"`{document.product_class_key}` is not a product class declaration"
        )

    # The clock is this deployment's DECLARED instant, not a wall-clock read.
    # The entitlement source stamps an audit event per decision, and a fixture
    # whose audit trail moved every run would make its own state a moving
    # target for anything that reads it back.
    stamped = document.question.asked_at or datetime.now(UTC)

    booted.control_plane.register_typed(
        product_entitlement_key(tenant_id=booted.fabric.tenant_id),
        ProductEntitlementPolicy(
            tenant_id=booted.fabric.tenant_id,
            policy_version=declaration.schema_version,
            principals={
                perspective.principal_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({declaration.schema_name}),
                    permitted_roles=frozenset({perspective.role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """Serve under the role this deployment declared, for the verified caller."""
        return Perspective(principal_id=grant.client_id, role=perspective.role)

    tokens = root / TOKEN_FILE
    tokens.write_text(
        json.dumps(
            {"stdio": {"client_id": perspective.principal_id, "scopes": [SCOPE]}}
        ),
        encoding="utf-8",
    )

    server = build_egress_server(
        server_name=booted.fabric.tenant_id,
        resolver=booted.resolver,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=tokens)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://stdio.invalid"),
            resource_server_url=AnyHttpUrl("https://stdio.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        entitlement_source=ControlPlaneProductEntitlementSource(
            control_plane=booted.control_plane, clock=lambda: stamped
        ),
        perspective_resolver=resolve_perspective,
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )

    # The stdio caller's identity, established once before anything is served.
    # See the module docstring: stdio carries no bearer channel, and a
    # deployment that left this unstated would refuse every caller as
    # unverified rather than serve the process that spawned it.
    auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="stdio",
                client_id=perspective.principal_id,
                scopes=[SCOPE],
            )
        )
    )
    server.run(transport="stdio")


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
