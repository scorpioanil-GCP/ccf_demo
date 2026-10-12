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

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.controlplane.artifacts import EgressDoorBinding
from ccf.projection.plan import Perspective
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.composed_product import compose_for_door
from ccf_runtime.mcp.product_door import open_door_with_verifier
from ccf_runtime.mcp.tenancy import ambient_stdio_identity

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
REQUIRED = ("producer_id", "tool_description", "required_scope", "issuer_url",
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

    **The door refuses nothing of its own.** An earlier revision checked here
    for a missing anchor and returned a hand-built `RefusalEnvelope` carrying
    `reason`/`key`/`detail` — fields that contract does not declare. It requires
    `kind` (from the SDK's own `REFUSAL_KINDS` vocabulary), `fields`, `request`
    and `pre_assembly_lineage`, so the constructor raised, the egress layer
    caught it as a runtime failure, and a governed "no" reached the caller as
    `ccf-runtime-failure:<id>` — which the SDK reserves for *"CCF or its runtime
    failed"* and promises a governed determination never arrives as (`CP07-F-09`).

    It was also unnecessary. `facility_id` and `borrower_scope` are `required`
    in the request contract, so the CONTROL PLANE already refuses a question
    missing either, and does it properly: `product-request-violation`, the
    declared and presented key sets, and a replay reference. The check is
    DELETED rather than repaired — code that reconstructs what was already
    declared dies with the declaration (`D-IMPL-289`).
    """
    def resolve(*, tenant: str, product_class: str, version: str,
                perspective: Any, request: Any) -> Any:
        parameters = {} if request is None else dict(request.parameters)
        facility = parameters.get(deployment.FACILITY)
        scope = parameters.get(deployment.BORROWER_SCOPE)
        asked = deployment.request(
            facility_id=None if facility is None else str(facility),
            borrower_scope=None if scope is None else [str(s) for s in scope],
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
    """Compose the producer, open the SDK's standard door over it, write this boot's credential.

    AMENDED 2026-10-11 (round 5, examples/AMENDMENTS-2026-10-11.md). This door
    registered its entitlement policy itself and called ``build_egress_server``
    directly. Since ``D-IMPL-353`` neither is available to a deployment: the
    registry takes a registration only under a capability SDK composition
    mints (``CapabilityBypassError``), and the builder requires an
    ``authorizer`` decided over a scope mapping only SDK composition can
    register. The supported path is the SDK's shared adapter,
    :func:`~ccf_runtime.mcp.composed_product.compose_for_door`, under the
    standard door, :func:`~ccf_runtime.mcp.product_door.open_door_with_verifier`,
    which derives the scope mapping and the pinned authorizer itself and
    registers the one-principal entitlement this door always served — the
    declared perspective's principal under its declared role — because this
    deployment declares no ``product_entitlement:``. ``door.yaml`` gained the
    producer identity the standard door asserts on every outcome, and the tree
    gained ``ccf_environment.yaml``, which names the credential variable.
    Nothing below decides anything: ``resolve`` is :func:`build_resolver`,
    unchanged.
    """
    values = door_values()
    config = deployment.config()
    tenant = str(config["tenant_id"])
    scope, principal = str(values["required_scope"]), str(values["principal_id"])
    role = str(values["role"])

    boot_root = root / "door-boot"
    boot_root.mkdir(parents=True, exist_ok=True)
    replay_root = root / "replay"
    # Owner-only (SEC-014, D-IMPL-369): the store refuses a wider root it did not create.
    replay_root.mkdir(mode=0o700, parents=True, exist_ok=True)

    # THE ASSEMBLY ROOT HAS TO EXIST BEFORE THE FIRST CALL, not after it.
    # `deployment.connection` hands SQLite a path INSIDE this directory and
    # SQLite will not create a missing parent, so a door that only named the
    # directory answered its first request with `unable to open database file` —
    # an MCP transport error, which is how a producer that never booted looks
    # from the outside. This door shipped that way at `D-GATE-cp-06`; nothing
    # ever booted it, because the only test written about it read `door.yaml`
    # and asserted that an entry point was DECLARED (`CP07-F-08`).
    assembly_root = root / "assembly"
    assembly_root.mkdir(parents=True, exist_ok=True)

    producer = compose_for_door(
        EXAMPLE / "ccf_config.yaml",
        boot_connection=deployment.connection(root=boot_root),
        environment_root=EXAMPLE,
        door=EgressDoorBinding.model_validate({
            "semver": "1.0.0",
            "producer_id": str(values["producer_id"]),
            "producer_tenant": tenant,
            "tool_description": str(values["tool_description"]),
            "required_scope": scope,
        }),
        # A DOOR THAT CANNOT RECORD A REFUSAL IS NOT A GOVERNED DOOR
        # (`D-IMPL-256` (2)), and the SDK refuses to build one. A determination
        # the fabric declined is still a determination: it is recorded,
        # disclosed at the caller's level, and addressed, exactly as a fulfilled
        # one is.
        replay_store=FileArtifactStore(
            root=replay_root,
            write_kinds=WriteKinds.declare({"ccf.replay-record": (ReplayMint,)}),
        ),
        replay_record_class="ccf.replay-record",
        resolver=build_resolver(root=assembly_root),
        default_perspective=Perspective(principal_id=principal, role=role),
    )

    def resolve_perspective(*, grant: Any, tenant: str,
                            requested_role: str | None) -> Perspective:
        """Serve under the declared role, for the VERIFIED caller.

        The subject is the verified `client_id`, never a value the caller
        supplied, and the role is derived from the declaration rather than
        asked for.
        """
        return Perspective(principal_id=grant.client_id, role=role)

    tokens = root / TOKEN_FILE
    opened = open_door_with_verifier(
        producer,
        token_verifier=SourceBackedTokenVerifier(source=FileTokenSource(path=tokens)),
        perspective_resolver=resolve_perspective,
    )
    # This boot's ONE credential (read from the variable `ccf_environment.yaml`
    # names, or minted per boot), recognized for the declared principal on this
    # tenant only (SEC-018) — written after the door is composed; the file is
    # read on every lookup.
    tokens.write_text(
        json.dumps({opened.credential: {
            "client_id": principal, "scopes": [scope], "tenants": [tenant]}}),
        encoding="utf-8")
    try:
        yield Door(
            server=opened.server(issuer_url=str(values["issuer_url"]),
                                 resource_server_url=str(values["resource_server_url"])),
            credential=opened.credential, principal_id=principal,
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
            auth_context_var.set(AuthenticatedUser(ambient_stdio_identity(
                credential=opened.credential, principal_id=opened.principal_id,
                scope=opened.scope, tenant=opened.tenant_id)))
            opened.server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    serve()
