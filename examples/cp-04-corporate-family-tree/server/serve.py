"""cp-04's MCP door — the LADDER'S FIRST, and the second of the two thin callers.

[ADAPT] all of it. [MECHANISM] `build_egress_server` and the four governance
seams it requires.

**NO `cp-*` RUNG HAS EVER TOUCHED MCP.** Rungs 00 through 03 all serve
in-process and none of them imports anything MCP-shaped. This is the ladder's
first door, and it stands in front of a far more demanding product than the one
`hw1-companies-over-revenue` serves: two systems of record opened per ask, a
walk whose depth the caller chooses, and findings that travel beside the tree.

The two documents this program reads
--------------------------------------
`../ccf_config.yaml` and the artifacts beside it — the deployment's own
declarations, reached through `deployment.py` and composed next door in
`compose.py`.

`egress-door.yaml` beside this file — the door's own four governance values.
Both are data; these two modules are their interpreter (CLAUDE.md §6.4). Delete
either and this program has nothing to serve.

The door is TOOL-ONLY in the only sense this SDK can express
--------------------------------------------------------------
**`CFT-G13` asserts three things together and this program is where all three
are true.** (a) The product RESOURCE **is** registered and enumerable. (b) A
read of it returns `runtime/ccf_runtime/mcp/egress.py::ProductNotServable` and
**never a tree**. (c) The **TOOL is the only path that serves**, taking a
client-supplied `lei` and `max_depth`.

Limb (a), MEASURED at a client rather than read off the registration call: the
resource is enumerable in `resources/templates/list` as
`ccf-product://{tenant}/{product_class}/{version}`, and `resources/list` is
EMPTY — a parameterized URI registers as a resource TEMPLATE. Criterion 37's
amended wording names `resources/list`; the substance is unchanged and `D-34` is
unchanged, and `compose.py` records the refinement in full.

The first limb is not a choice this deployment made.
`runtime/ccf_runtime/mcp/egress.py::build_egress_server` registers its product
resource **unconditionally** and gates only the tool behind
`expose_product_tool`, so that builder can be resource-only or
resource-plus-tool and **cannot be tool-only**. Dave ruled it at Gate 1, in as
many words: *"A listing that includes the resource is the SDK. Criterion 37 as
written ('no resource is exposed') is false against this tree."* The criterion
was amended to say what is true rather than left asserting something false, and
the gap is **`D-34`** — RECORDED, not closed (`D-IMPL-225` amendment 1). `D-04`
of `24-CONTEXT.md` governs: a minor phase records SDK gaps, and **no file under
`src/` or `runtime/` is touched by this plan** (criterion 49).

What the door does control is limb (b), and `compose.py::build_resolver` is
where it lives: `request is None` is the resource path, and the resolver refuses
it BY NAME rather than inventing an anchor, inventing a depth, or serving a
standing answer that does not exist for a parameterized class (`D-18`).

Identity over stdio, stated rather than smuggled
--------------------------------------------------
**MCP stdio carries no authentication channel.** `FastMCP` installs its bearer
middleware on the HTTP app and there is no HTTP app here, so the door's handlers
find no verified identity and refuse every caller as unverified. The transport's
own security boundary is process ownership: this server is a child that this
deployment's client spawned, under the same user, on the same host, with no
socket anywhere.

So this deployment states who its stdio caller is, once, before serving. That is
a **deployment's** decision about its own trust boundary, and the deployment's
own program is the only place it may be written. The verifier and auth settings
are supplied because the builder requires them together (`D-03`) and because
this same deployment is reachable over HTTP with them in force; over stdio they
are inert.

Nothing is committed as data (`D-32`)
---------------------------------------
The token table is minted per boot into a temporary directory that is deleted on
exit, exactly as `hw1-companies-over-revenue/server/serve.py` mints its own; the
two estates this reads are whatever `backends.yaml`'s environment variables
name, and no host, port, path or credential appears in any document here.
"""

from __future__ import annotations

import json
import secrets
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import yaml
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    TokenGrant,
)
from ccf.projection.plan import Perspective
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import build_egress_server

HERE = Path(__file__).resolve().parent
# The example root, so the sibling modules this door composes over import by
# name. This program is spawned as a bare `python <this file>`, so `server/` is
# already on `sys.path` and `compose` resolves; the example root is not.
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from compose import ComposedDoor, compose  # noqa: E402

#: The door's own document, beside this file — the four governance values this
#: program interprets and never spells (CLAUDE.md §6.4).
EGRESS_DOOR = HERE / "egress-door.yaml"

#: The four keys that document must carry. Read STRICTLY: a document missing one
#: is an authoring mistake worth naming here rather than discovering as a
#: `KeyError` inside a builder three frames down.
DOOR_KEYS = (
    "tool_description",
    "required_scope",
    "issuer_url",
    "resource_server_url",
)

#: What the minted token table is called inside the per-boot temporary
#: directory. A filename is mechanism; the credential in it is generated.
TOKEN_FILE = "stdio-tokens.json"


def door_values() -> dict[str, Any]:
    """The four governance values this door needs, from the document that owns them."""
    parsed = yaml.safe_load(EGRESS_DOOR.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise TypeError(f"{EGRESS_DOOR} is not a mapping of names to values")
    missing = sorted(
        key for key in DOOR_KEYS if not str(parsed.get(key, "")).strip()
    )
    if missing:
        raise ValueError(
            f"{EGRESS_DOOR} states no {', '.join(missing)} — this door's"
            " governance values live in that document and the SDK holds no"
            " default for any of them (CINV-01)"
        )
    return parsed


@dataclass(frozen=True)
class Door:
    """One booted door, with the credential this boot is reached by.

    Returned rather than run, so the same construction a reader spawns on stdio
    is the construction `tests/examples/test_cp_04_two_callers.py` drives over
    the server's own ASGI app. A door only reachable by spawning a subprocess
    would be a door whose behavior is asserted at one remove from the program
    that has it.
    """

    #: The configured `FastMCP`. Deliberately not started — hosting is the
    #: deployment's decision, and this module makes it in :func:`serve`.
    server: Any
    #: This boot's throwaway bearer credential.
    credential: str
    #: What was composed behind the door: the tenant, the principal, the role,
    #: the Control Plane and the one resolver.
    composed: ComposedDoor
    #: The scope the door requires and the credential carries.
    scope: str


@contextmanager
def door(*, root: Path) -> Iterator[Door]:
    """Compose the deployment, mint this boot's credential, and build the door.

    ``root`` is scratch space: this boot's token table sits in it, and every
    assembly's per-run SQLite L3 and file-backed artifact store are minted
    beneath it. A context manager because the credential's lifetime is the
    boot's lifetime — a token that outlived the process it was minted for would
    be a standing credential written by a program that promised not to write
    one.
    """
    values = door_values()
    scope = str(values["required_scope"])
    composed = compose(root=root)

    tokens = root / TOKEN_FILE
    credential = secrets.token_urlsafe(32)
    tokens.write_text(
        json.dumps(
            {
                credential: {
                    "client_id": composed.principal_id,
                    "scopes": [scope],
                }
            }
        ),
        encoding="utf-8",
    )

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """Serve under the role this deployment declared, for the verified caller.

        The subject is the **verified** `client_id`, never a value the caller
        supplied. Whatever this returns is still checked against the principal's
        entitlement grant before a product is resolved, so widening it here
        would not widen the door.

        `requested_role` is always ``None`` on both of this door's surfaces —
        the resource URI carries no role segment and the product tool carries no
        `role` argument — so the role is DERIVED from the grant rather than
        asked for. That is what keeps the tool from being wider than the
        resource beside it.
        """
        return Perspective(principal_id=grant.client_id, role=composed.role)

    server = build_egress_server(
        # The server's name is this deployment's tenant, off its own
        # declaration — a server name written here would be a domain value in
        # code.
        server_name=composed.tenant_id,
        resolver=composed.resolver,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=tokens)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(str(values["issuer_url"])),
            resource_server_url=AnyHttpUrl(str(values["resource_server_url"])),
            required_scopes=[scope],
        ),
        entitlement_source=ControlPlaneProductEntitlementSource(
            control_plane=composed.control_plane,
            # A door decision happens when it happens: the audit timestamp is a
            # wall-clock read, never `question.asked_at`. This deployment's
            # demonstration instant is PINNED, so binding the audit plane to it
            # would have every decision this door ever made stamped 2026-08-31.
            clock=lambda: datetime.now(UTC),
        ),
        perspective_resolver=resolve_perspective,
        # THE SECOND SURFACE, AND THE ONLY ONE THAT SERVES. The resource beside
        # it is registered unconditionally by the builder and refuses in
        # `compose.py::build_resolver`.
        expose_product_tool=True,
        product_tool_description=str(values["tool_description"]),
    )
    try:
        yield Door(
            server=server,
            credential=credential,
            composed=composed,
            scope=scope,
        )
    finally:
        tokens.unlink(missing_ok=True)


def serve() -> None:
    """Boot the door and serve it on stdio.

    The stdio caller's identity is established once before anything is served.
    See the module docstring: stdio carries no bearer channel, and a deployment
    that left this unstated would refuse every caller as unverified rather than
    serve the process that spawned it.
    """
    with tempfile.TemporaryDirectory(prefix="cp04-door-") as scratch:
        with door(root=Path(scratch)) as opened:
            auth_context_var.set(
                AuthenticatedUser(
                    AccessToken(
                        token=opened.credential,
                        client_id=opened.composed.principal_id,
                        scopes=[opened.scope],
                    )
                )
            )
            opened.server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    serve()
