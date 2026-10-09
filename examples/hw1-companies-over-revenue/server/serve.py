"""HW-1's own MCP server program: the far side of `mcp+stdio:`, on the SDK's standard door.

The three documents this program reads
--------------------------------------
``../deployment/binding.yaml``: the deployment's wiring, composed by
:func:`compose.compose` next door.

``egress-door.yaml`` beside this file: the door's identity and prose, which is
the producer identity it asserts on every outcome, the tenant that assertion
names, the scope it requires and the prose its tool advertises (the
``ccf.egress-door`` class, ``D-IMPL-343``).

``ccf_environment.yaml`` beside this file: the NAME of the environment
variable the door's credential is read from, never its value (Dave,
``D-IMPL-343``: *"Do not put URLs or tokens in configuration."*).

All three are data; these two modules are their interpreter (CLAUDE.md §6.4).
Delete any of them and this program has nothing to serve.

The door is the SDK's
---------------------
:func:`~ccf_runtime.mcp.product_door.open_door` composes the door over what
:func:`compose.compose` holds: the entitlement policy for the declared principal
and role, the scope mapping its authorizer decides every call under, pinned at
the version its registration returns (``D-IMPL-353``), a credential minted per
boot when the environment names none, and the egress server, which asserts the
declared producer identity on every outcome (``D-IMPL-340``). This file writes
none of that.

Identity over stdio, stated rather than smuggled
--------------------------------------------------
**MCP stdio carries no authentication channel.** ``FastMCP`` installs its bearer
middleware on the HTTP app and there is no HTTP app here, so the door would
refuse every caller as unverified. The transport's own security boundary is
process ownership: this server is a child that this deployment's client
spawned, under the same user, on the same host, with no socket anywhere.

So this program states who its stdio caller is, once, before serving, and the
door states none of its own (``D-IMPL-361`` §7.3). The identity is built by
:func:`~ccf_runtime.mcp.tenancy.ambient_stdio_identity`, which scopes it to
exactly the tenant the door serves and marks it ambient, which is what makes
every *mutating* surface refuse it (``SEC-018``). That is a deployment's
decision about its own trust boundary, and the deployment's own program is the
only place it may be written.

The two addresses an HTTP door advertises for OAuth discovery do nothing on
stdio, for the same reason, and the SDK's stdio transport supplies its own
(``D-IMPL-378``, ruling C2-A (b)). Both names are optional (C2-A2 (a)), so
``ccf_environment.yaml`` names neither, and nothing that spawns this program has
to carry a door variable: the credential, unset, is minted per boot.

Nothing is committed as data (``D-32``)
-----------------------------------------
The credential is minted per boot and lives only in this process; the graph
this boots against is whatever ``binding.yaml`` points at, populated or not.
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser

from ccf.client.adapters.binding_document import load_binding_document
from ccf.controlplane.artifacts import EGRESS_DOOR, EgressDoorBinding, load_artifact
from ccf.deployment import load_environment_document
from ccf_runtime.mcp.product_door import open_door
from ccf_runtime.mcp.tenancy import ambient_stdio_identity

# The boot next door. This program is spawned as a bare `python <this file>`,
# so its own directory is already on `sys.path` and the sibling module imports
# by name.
from compose import compose

#: This file's directory, which holds the door's two documents.
HERE = Path(__file__).resolve().parent

#: The door's own document, beside this file: the four values the standard
#: door asserts and advertises, which this program interprets and never spells
#: (CLAUDE.md §6.4).
EGRESS_DOOR_DOCUMENT = HERE / "egress-door.yaml"


def door_binding() -> EgressDoorBinding:
    """The door's identity and prose, through the SDK's own artifact loader.

    Loaded as the ``ccf.egress-door`` class, so a principal, a role, a URL or a
    credential written into the document is refused by name here rather than
    carried into the door.
    """
    binding = load_artifact(
        EGRESS_DOOR_DOCUMENT.read_text(encoding="utf-8"), EGRESS_DOOR
    )
    if not isinstance(binding, EgressDoorBinding):
        raise TypeError(
            f"{EGRESS_DOOR_DOCUMENT} did not load as {EGRESS_DOOR.class_id}"
        )
    return binding


def serve(root: Path) -> None:
    """Boot the deployment at ``root``, open the standard door, serve on stdio.

    Booting the deployment and building its resolver is
    :func:`compose.compose`'s work, next door. What this function does is the
    door: hand the composed deployment to
    :func:`~ccf_runtime.mcp.product_door.open_door`, state who the stdio caller
    is, and run.
    """
    deployment = compose(
        load_binding_document(root),
        door=door_binding(),
        environment=load_environment_document(HERE),
    )
    try:
        door = open_door(deployment)
        door.serve_stdio(
            identity=AuthenticatedUser(
                ambient_stdio_identity(
                    credential=door.credential,
                    principal_id=door.principal_id,
                    scope=door.scope,
                    tenant=door.tenant_id,
                )
            )
        )
    finally:
        deployment.fabric.handle.close()


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
