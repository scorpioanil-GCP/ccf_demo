"""HW-1's own MCP server program — the far side of `mcp+stdio:`.

The two documents this program reads
--------------------------------------
``../deployment/binding.yaml`` — the deployment's wiring, read through
:func:`compose.compose` next door.

``egress-door.yaml`` beside this file — the door's own four governance values.
Both are data; these two modules are their interpreter (CLAUDE.md §6.4). Delete
either and this program has nothing to serve.

Identity over stdio, stated rather than smuggled
--------------------------------------------------
**MCP stdio carries no authentication channel.** ``FastMCP`` installs its bearer
middleware on the HTTP app and there is no HTTP app here, so
``get_access_token()`` inside the door's handler finds nothing and the door
refuses every caller as unverified. The transport's own security boundary is
process ownership: this server is a child that this deployment's client
spawned, under the same user, on the same host, with no socket anywhere.

So this deployment states who its stdio caller is, once, before serving. That is
a **deployment's** decision about its own trust boundary, and the deployment's
own program is the only place it may be written. The verifier and auth settings
are supplied because the builder requires them together (``D-03``) and because
this same deployment is reachable over HTTP with them in force; over stdio they
are inert.

Nothing is committed as data (``D-32``)
-----------------------------------------
The token table is minted per boot into a temporary directory that is deleted on
exit, exactly as ``examples/04-cross-process`` mints its signing key; the graph
this boots against is whatever ``binding.yaml`` points at, populated or not.
"""

from __future__ import annotations

import json
import secrets
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from ccf.client.adapters.binding_document import (
    BindingDocument,
    load_binding_document,
)
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    TokenGrant,
)
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import build_egress_server

# The boot next door. This program is spawned as a bare `python <this file>`,
# so its own directory is already on `sys.path` and the sibling module imports
# by name.
from compose import compose

#: The door's own document, beside this file — the four governance values
#: this program interprets and never spells (CLAUDE.md §6.4).
EGRESS_DOOR = Path(__file__).resolve().parent / "egress-door.yaml"

#: What the minted token table is called inside the per-boot temporary
#: directory. A filename is mechanism; the credential in it is generated.
TOKEN_FILE = "stdio-tokens.json"


def door_values() -> dict[str, Any]:
    """The four governance values this door needs, from the document that owns them.

    Read rather than spelled, and read **strictly**: a document missing a key is
    an authoring mistake worth naming here rather than discovering as a
    ``KeyError`` inside a builder three frames down.
    """
    parsed = yaml.safe_load(EGRESS_DOOR.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise TypeError(f"{EGRESS_DOOR} is not a mapping of names to values")
    missing = sorted(
        key
        for key in (
            "tool_description",
            "required_scope",
            "issuer_url",
            "resource_server_url",
        )
        if not str(parsed.get(key, "")).strip()
    )
    if missing:
        raise ValueError(
            f"{EGRESS_DOOR} states no {', '.join(missing)} — this door's"
            " governance values live in that document and the SDK holds no"
            " default for any of them (CINV-01)"
        )
    return parsed


def serve(root: Path) -> None:
    """Boot the deployment at ``root``, expose its product door, serve on stdio.

    What this function does is the door: read the four governance values the
    door's own document holds, mint the credential this boot will be reached
    with, hand the composed resolver to
    :func:`~ccf_runtime.mcp.egress.build_egress_server`, state who the stdio
    caller is, and run. Booting the deployment and building that resolver is
    :func:`compose.compose`'s work, next door.
    """
    document: BindingDocument = load_binding_document(root)
    door = door_values()

    composed = compose(document)
    perspective = document.perspective

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """Serve under the role this deployment declared, for the verified caller.

        The subject is the **verified** ``client_id``, never a value the caller
        supplied. Whatever this returns is still checked against the principal's
        entitlement grant before a product is resolved, so widening it here
        would not widen the door.
        """
        return Perspective(principal_id=grant.client_id, role=perspective.role)

    scope = str(door["required_scope"])
    with tempfile.TemporaryDirectory(prefix="ccf-hw1-stdio-") as scratch:
        tokens = Path(scratch) / TOKEN_FILE
        credential = secrets.token_urlsafe(32)
        tokens.write_text(
            json.dumps(
                {
                    credential: {
                        "client_id": perspective.principal_id,
                        "scopes": [scope],
                    }
                }
            ),
            encoding="utf-8",
        )

        server = build_egress_server(
            # The server's name is this deployment's tenant, off the fabric it
            # booted — a server name written here would be a domain value in code.
            server_name=composed.fabric.tenant_id,
            resolver=composed.resolver,
            token_verifier=SourceBackedTokenVerifier(
                source=FileTokenSource(path=tokens)
            ),
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl(str(door["issuer_url"])),
                resource_server_url=AnyHttpUrl(str(door["resource_server_url"])),
                required_scopes=[scope],
            ),
            entitlement_source=ControlPlaneProductEntitlementSource(
                # A door decision happens when it happens: the audit timestamp
                # is a wall-clock read, never `question.asked_at`. A declared
                # instant here would have the audit plane state that every
                # decision this deployment ever made happened at one moment.
                control_plane=composed.control_plane,
                clock=lambda: datetime.now(UTC),
            ),
            perspective_resolver=resolve_perspective,
            expose_product_tool=True,
            product_tool_description=str(door["tool_description"]),
        )

        # The stdio caller's identity, established once before anything is
        # served. See the module docstring: stdio carries no bearer channel, and
        # a deployment that left this unstated would refuse every caller as
        # unverified rather than serve the process that spawned it.
        auth_context_var.set(
            AuthenticatedUser(
                AccessToken(
                    token=credential,
                    client_id=perspective.principal_id,
                    scopes=[scope],
                )
            )
        )
        try:
            server.run(transport="stdio")
        finally:
            composed.fabric.handle.close()


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
