"""HW-1's own MCP server program — the far side of `mcp+stdio:`.

**A deployment's program, not the SDK's, and that is the whole point.**
``ccf_runtime.mcp.egress::build_egress_server`` requires a server name, a token
verifier, auth settings, an entitlement source and a perspective resolver —
five deployment values in their entirety (CINV-01), which is exactly why the
SDK ships no server entry point and why
``ccf.client.adapters.mcp_stdio`` launches a program it knows nothing about.
An ``mcp+stdio`` binding names **this file** and the deployment root beside it,
and this file is what an adopter writes.

Why it is here rather than beside ``consume.py``
--------------------------------------------------
Two shipped gates decide the filing, and between them they leave exactly one
place:

* ``D-IMPL-141`` Amendment A.3 grants ``../deployment/`` **one** Python module —
  the projection — and ``tests/client/test_data_only_deployment.py`` refuses a
  second by name. So this is not a deployment-root file.
* ``tests/examples/test_client_example_purity.py`` treats every ``.py`` sitting
  directly in the example root as **reader-visible consumer code**, permitted to
  import ``ccf.client`` and the standard library and nothing else. A server
  program is the producer's world — it imports ``ccf.deployment``,
  ``ccf.products`` and ``ccf_runtime`` — so putting it there would put the
  producer inside the consumer's reading surface, which is the separation
  ``D-02`` exists to draw.

So: a sibling directory. ``consume.py`` stays the entire example a reader
studies, and this file is what they open when they want to know how the second
door is stood up.

**It composes through the SDK's public seams and nothing private.** Every name
imported below is exported from its package. There is a private
``ccf.client.adapters.inprocess::_boot`` that does the composition in the first
eleven lines of :func:`serve`, and it is deliberately not used: a demonstration
of adoptability that reached into the SDK's private surface would demonstrate
the opposite. What this file does with public names, an adopter can do.

The two documents this program reads
--------------------------------------
``../deployment/binding.yaml`` — the deployment's wiring, the same document the
in-process adapter reads, so both transports compose the *same* governed
resolver from the *same* declared values. That is what makes "the same answer
over two transports" a property rather than a coincidence.

``egress-door.yaml`` beside this file — the door's own four governance values.
Both are data; this module is their interpreter (CLAUDE.md §6.4). Delete either
and this program has nothing to serve.

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

Nothing here is committed as data (``D-32``). The token table is minted per boot
into a temporary directory that is deleted on exit, exactly as
``examples/04-cross-process`` mints its signing key; the graph this boots
against is whatever ``binding.yaml`` points at, populated or not.
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

from ccf.artifacts.file_store import FileArtifactStore
from ccf.client.adapters.binding_document import (
    BindingDocument,
    conforming_plan_factory,
    load_binding_document,
    load_reference,
)
from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_config_and_boot
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    TokenGrant,
)
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import build_egress_server

#: The door's own document, beside this file rather than inside the deployment
#: root — see the module docstring for the two gates that decide the filing.
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

    The composition below is the public path, step for step: read the wiring,
    boot the fabric, resolve the one permitted projection reference, and hand
    all of it to :func:`~ccf.products.resolver.build_governed_resolver`, which
    is where the SDK selects its own reference debt scorer so a deployment
    supplying only data never has to know the Protocol exists.
    """
    document: BindingDocument = load_binding_document(root)
    door = door_values()

    control_plane = ControlPlaneRegistry()
    fabric = load_config_and_boot(
        document.config, registry=control_plane, connection=document.connection
    )
    resolver = build_governed_resolver(
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=document.product_class_key,
        request_contract_key=document.request_contract_key,
        operator_parameter_keys=document.operator_parameter_keys,
        policy_bundle_key=document.policy_bundle_key,
        plan_factory=conforming_plan_factory(
            load_reference(document.plan, root=document.root, key="plan"),
            reference=document.plan,
            root=document.root,
        ),
        artifact_store=FileArtifactStore(root=document.artifact_store),
        replay_record_class=document.replay_record_class,
        query_pin_class=document.query_pin_class,
        max_ttl_seconds=document.max_ttl_seconds,
        product_ttl_seconds=document.product_ttl_seconds,
        half_life_key=document.debt.half_life_key,
        debt_profile_key=document.debt.debt_profile_key,
        declared_completeness=document.debt.completeness,
        declared_semantic_consistency=document.debt.semantic_consistency,
    )

    declaration = fabric.artifacts[document.product_class_key]
    if not isinstance(declaration, ProductClassDeclaration):
        raise TypeError(
            f"`{document.product_class_key}` in {document.config} is not a"
            " product class declaration"
        )

    # The permitted class and the permitted role are the ones this deployment
    # actually serves and assembles under — taken from the registered class and
    # from `binding.yaml`'s `perspective:`, never restated here, so an
    # entitlement cannot name a class this fabric does not serve.
    perspective = document.perspective
    control_plane.register_typed(
        product_entitlement_key(tenant_id=fabric.tenant_id),
        ProductEntitlementPolicy(
            tenant_id=fabric.tenant_id,
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
            server_name=fabric.tenant_id,
            resolver=resolver,
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
                control_plane=control_plane,
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
            fabric.handle.close()


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
