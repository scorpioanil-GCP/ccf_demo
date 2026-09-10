"""cp-06's MCP egress door — a translation layer, and nothing more.

**This module re-implements no part of the governed path.**
``produce.assemble_and_serve`` already returns the one shape a door may
release: a :class:`~ccf.replay.serve.ServedProduct` whose replay reference
proves the record was appended, or a
:class:`~ccf.products.refusal.RefusalEnvelope` — recorded, disclosed and
addressed. What is left here is translating an MCP call into a
:class:`~ccf.products.request.ProductRequest` and handing back what the fabric
decided.

**Every governance value comes from ``door.yaml``**, which owns them. The SDK
holds a default for none (CINV-01), so an absent value raises rather than
resolving to something nobody chose.

**A consumer asks for a Context Product; it does not learn how the producer
starts.** ``door.yaml`` names the entry point as ``module:callable``, not as a
filesystem path — a client carrying ``python examples/…/serve.py`` would be
bound to this deployment's directory layout, interpreter and language, none of
which is part of the product contract.

**The estate is read-only.** This door opens the same two source stores the
in-process path opens, through the same ``acquisition`` module, which holds no
write path to either (CLAUDE.md §9).
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

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.artifacts.file_store import FileArtifactStore
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import build_egress_server

HERE = Path(__file__).parent
EXAMPLE = HERE.parent
if str(EXAMPLE) not in sys.path:  # the deployment's own modules are siblings
    sys.path.insert(0, str(EXAMPLE))

import deployment  # noqa: E402
import produce  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402
from ccf.replay.serve import ServedProduct  # noqa: E402

TOKEN_FILE = "tokens.json"

#: Every value `door.yaml` must state. Named here so an absent one is reported
#: by name rather than surfacing as an empty string three frames later.
REQUIRED = ("tool_description", "required_scope", "issuer_url",
            "resource_server_url", "principal_id", "role", "serve_entrypoint")


def door_values() -> dict[str, Any]:
    """The door's governance values, from the document that owns them."""
    declared: dict[str, Any] = yaml.safe_load(
        (HERE / "door.yaml").read_text(encoding="utf-8"))["declaration"]
    missing = sorted(k for k in REQUIRED if not str(declared.get(k, "")).strip())
    if missing:
        raise ValueError(
            f"server/door.yaml states no {', '.join(missing)} — this door's"
            " governance values live in that document and the SDK holds no"
            " default for any of them (CINV-01)"
        )
    return declared


def build_resolver(*, root: Path) -> Any:
    """cp-06's `ProductResolverProtocol` — the adapter.

    It translates and delegates. The governed determination, the three L6
    gates, this product's declared over-allocation gate, the five-dimension
    replay record and the refusal path are all `assemble_and_serve`'s, reached
    unchanged.
    """
    def resolve(*, tenant: str, product_class: str, version: str,
                perspective: Any, request: Any) -> Any:
        parameters = {} if request is None else dict(request.parameters)
        facility = parameters.get(deployment.FACILITY)
        scope = parameters.get(deployment.BORROWER_SCOPE)
        if not facility or not scope:
            # The door's ONE refusal: a question with no anchor is not a
            # question this class answers, and there is nothing to govern.
            return RefusalEnvelope(
                reason="missing-required-argument",
                key=deployment.FACILITY if not facility else deployment.BORROWER_SCOPE,
                detail="both `facility_id` and `borrower_scope` are required",
            )
        asked = deployment.request(
            facility_id=str(facility),
            borrower_scope=[str(s) for s in scope],
            asked_at=(request.asked_at if request is not None
                      else datetime.now(UTC)),
            apply_haircuts=parameters.get(deployment.APPLY_HAIRCUTS),
            include_setoff=parameters.get(deployment.INCLUDE_SETOFF),
            jurisdiction_basis=parameters.get(deployment.JURISDICTION_BASIS),
            shared_collateral=parameters.get(deployment.SHARED_COLLATERAL),
        )
        outcome = produce.assemble_and_serve(asked=asked, root=root)
        if isinstance(outcome, RefusalEnvelope):
            return outcome
        return outcome.served

    return resolve


@dataclass(frozen=True)
class Door:
    """One booted door, and the credential this boot is reached by."""

    server: Any
    credential: str
    principal_id: str
    scope: str
    tenant_id: str


@contextmanager
def door(*, root: Path) -> Iterator[Door]:
    """Register the entitlement, mint this boot's credential, build the door."""
    values = door_values()
    config = deployment.config()
    tenant = str(config["tenant_id"])
    scope, principal = str(values["required_scope"]), str(values["principal_id"])
    role = str(values["role"])

    control_plane = ControlPlaneRegistry()
    control_plane.register_typed(
        product_entitlement_key(tenant_id=tenant),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version=str(config["product_class"]["schema_version"]),
            principals={principal: ProductEntitlementGrant(
                permitted_schema_names=frozenset(
                    {str(config["product_class"]["schema_name"])}),
                permitted_roles=frozenset({role}))},
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    # A DOOR DECISION HAPPENS WHEN IT HAPPENS. Binding the audit plane to the
    # demonstration instant would stamp every decision this door ever made with
    # one date.
    entitlement_source = ControlPlaneProductEntitlementSource(
        control_plane=control_plane, clock=lambda: datetime.now(UTC))

    replay_root = root / "replay"
    replay_root.mkdir(parents=True, exist_ok=True)

    tokens = root / TOKEN_FILE
    credential = secrets.token_urlsafe(32)
    tokens.write_text(
        json.dumps({credential: {"client_id": principal, "scopes": [scope]}}),
        encoding="utf-8")

    def resolve_perspective(*, grant: Any, tenant: str,
                            requested_role: str | None) -> Perspective:
        """Serve under the declared role, for the VERIFIED caller.

        The subject is the verified `client_id`, never a value the caller
        supplied, and the role is derived from the declaration rather than
        asked for.
        """
        return Perspective(principal_id=grant.client_id, role=role)

    server = build_egress_server(
        server_name=tenant,
        resolver=build_resolver(root=root / "assembly"),
        token_verifier=SourceBackedTokenVerifier(source=FileTokenSource(path=tokens)),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(str(values["issuer_url"])),
            resource_server_url=AnyHttpUrl(str(values["resource_server_url"])),
            required_scopes=[scope],
        ),
        entitlement_source=entitlement_source,
        perspective_resolver=resolve_perspective,
        # A DOOR THAT CANNOT RECORD A REFUSAL IS NOT A GOVERNED DOOR
        # (`D-IMPL-256` (2)), and the SDK refuses to build one. A determination
        # the fabric declined is still a determination: it is recorded,
        # disclosed at the caller's level, and addressed, exactly as a fulfilled
        # one is.
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=FileArtifactStore(root=replay_root),
            replay_record_class="ccf.replay-record",
            tenant_id=tenant,
            assembly_mode=str(config["product_class"]["assembly_mode"]),
            disclosure_level_for=entitlement_source.disclosure_level_for,
        ),
        expose_product_tool=True,
        product_tool_description=str(values["tool_description"]),
    )
    try:
        yield Door(server=server, credential=credential, principal_id=principal,
                   scope=scope, tenant_id=tenant)
    finally:
        tokens.unlink(missing_ok=True)


def serve() -> None:
    """Boot the door and serve it on stdio.

    **MCP stdio carries no authentication channel** — `FastMCP` installs its
    bearer middleware on the HTTP app and there is no HTTP app here — so this
    deployment states who its stdio caller is, once, before serving. The
    transport's security boundary is process ownership: this server is a child
    the client spawned, under the same user, with no socket anywhere.
    """
    with tempfile.TemporaryDirectory(prefix="cp06-door-") as scratch:
        with door(root=Path(scratch)) as opened:
            auth_context_var.set(AuthenticatedUser(AccessToken(
                token=opened.credential, client_id=opened.principal_id,
                scopes=[opened.scope])))
            opened.server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    serve()
