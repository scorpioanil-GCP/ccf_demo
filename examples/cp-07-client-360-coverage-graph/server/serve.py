"""cp-07's MCP egress door — a translation layer, and nothing more.

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

from ccf.controlplane.artifacts import (
    PRODUCT_CLASS,
    EgressDoorBinding,
    ProductClassDeclaration,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry, namespaced_key
from ccf.deployment import EnvironmentDocument, load_config_and_boot, load_environment_document
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.request import ProductRequest
from ccf.products.resolver import declared_refusal_recorder
from ccf.replay.record import PolicyBinding
from ccf.projection.plan import Perspective
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
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
    """cp-07's `ProductResolverProtocol` — the adapter.

    It translates and delegates. The governed determination, the three L6
    gates, this product's declared truncation-disclosure gate, the
    five-dimension replay record and the refusal path are all
    `assemble_and_serve`'s, reached unchanged.

    **A bound the caller omits is omitted here too**, so the class default in
    `ccf_config.yaml` resolves for the MCP caller exactly as it does in
    process. Restating a default in this adapter would give the door a second
    governance authority, and the two would drift.
    """
    def resolve(*, tenant: str, product_class: str, version: str,
                perspective: Any, request: Any) -> Any:
        parameters = {} if request is None else dict(request.parameters)
        lei = parameters.get(deployment.LEI)
        scope = parameters.get(deployment.PRINCIPAL_SCOPE)
        limit = parameters.get(deployment.LIMIT)
        # **THE DOOR REFUSES NOTHING OF ITS OWN.** `lei` and `principal_scope`
        # are `required` in the request contract, so a question missing either
        # is refused by the CONTROL PLANE — with a kind from the SDK's own
        # vocabulary, the key that was missing, and a replay record. An earlier
        # revision of this function hand-rolled that refusal here; it could not
        # construct a valid `RefusalEnvelope` and turned a governed "no" into an
        # `ccf-runtime-failure` at the transport, which is indistinguishable
        # from a producer that never booted. See `FINDINGS.md`.
        asked = deployment.request(
            lei=None if lei is None else str(lei),
            principal_scope=None if scope is None else [str(s) for s in scope],
            asked_at=(request.asked_at if request is not None
                      else datetime.now(UTC)),
            since=parameters.get(deployment.SINCE),
            limit=None if limit is None else int(limit),
            include_family=parameters.get(deployment.INCLUDE_FAMILY),
            include_need_to_know=parameters.get(deployment.INCLUDE_NTK),
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
    #: The standard door this boot opened (AMENDED 2026-10-11, round 3).
    product_door: Any = None


class CoverageProducer:
    """cp-07's governed path, presented to the SDK's standard door (``ServesProducts``).

    AMENDED 2026-10-11 (round 3, examples/AMENDMENTS-2026-10-11.md). This door
    used to call ``build_egress_server`` itself and register its entitlement
    policy by hand. Since D-IMPL-353 neither is available to a deployment: the
    registry takes a capability only SDK composition code mints
    (``CapabilityBypassError``), and ``build_egress_server`` now requires an
    ``authorizer`` decided over a registered scope mapping that no deployment
    can register or declare. The supported path for a deployment that composes
    its product by hand is this one — the nine members ``ServesProducts`` names,
    handed to :func:`~ccf_runtime.mcp.product_door.open_door_with_verifier`,
    which derives the scope mapping and the pinned authorizer itself
    (door-cp-05 and hw1 are the precedents).

    **The principals are DECLARED** (``ccf_config.yaml::product_entitlement:``,
    G4-F-04) and the SDK's own boot registers them into this Control Plane,
    under its composition recipe; the door composes over them and registers
    no default of its own. The boot is the deployment's ordinary one, over an
    owned scratch L3 nothing reads, closed at once; its policy pin is the pin
    the refusal recorder records.
    """

    def __init__(self, *, root: Path, values: Any) -> None:
        config = deployment.config()
        self._tenant = str(config["tenant_id"])
        declaration = parse_artifact(
            {"semver": config["semver"], **config["product_class"]}, PRODUCT_CLASS)
        assert isinstance(declaration, ProductClassDeclaration)  # PRODUCT_CLASS's contract
        self._declaration = declaration
        self._perspective = Perspective(
            principal_id=str(values["principal_id"]), role=str(values["role"]))
        self._control_plane = ControlPlaneRegistry()
        boot_root = root / "door-boot"
        boot_root.mkdir(parents=True, exist_ok=True)
        booted = load_config_and_boot(
            EXAMPLE / "ccf_config.yaml", registry=self._control_plane,
            connection=deployment.connection(root=boot_root))
        try:
            policy_key = namespaced_key(tenant=self._tenant, key="policy")
            policy_pin = next(pin for pin in booted.pins.entries if pin.key == policy_key)
        finally:
            booted.handle.close()
        replay_root = root / "replay"
        # Owner-only (SEC-014, D-IMPL-369): the store refuses a wider root it did not create.
        replay_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        # A DOOR THAT CANNOT RECORD A REFUSAL IS NOT A GOVERNED DOOR
        # (`D-IMPL-256` (2)). The SDK's `declared_refusal_recorder` — the
        # composition `open_product` uses — reads its disclosure posture off
        # this Control Plane, so a denial and its shell are decided under one
        # reading of the one declared policy.
        self.replay_store = FileArtifactStore(root=replay_root, write_kinds=WriteKinds.declare({"ccf.replay-record": (ReplayMint,), "ccf.graph-query": (ReplayMint,), ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,)}))
        self._recorder = declared_refusal_recorder(
            control_plane=self._control_plane,
            artifact_store=self.replay_store,
            replay_record_class="ccf.replay-record",
            tenant_id=self._tenant,
            assembly_mode=declaration.assembly_mode,
            policy_bundle_pin=PolicyBinding(key=policy_pin.key, version=policy_pin.version),
        )
        self._door = EgressDoorBinding.model_validate({
            "semver": "1.0.0",
            "producer_id": str(values["producer_id"]),
            "producer_tenant": self._tenant,
            "tool_description": str(values["tool_description"]),
            "required_scope": str(values["required_scope"]),
        })
        self._environment = load_environment_document(EXAMPLE)
        # THE ASSEMBLY ROOT HAS TO EXIST BEFORE THE FIRST CALL, not after it.
        # `deployment.connection` hands SQLite a path INSIDE this directory and
        # SQLite will not create a missing parent, so a door that only named the
        # directory answers its first request with `unable to open database file` —
        # an MCP transport error, which is how a producer that never booted looks
        # from the outside. Found by driving this door; recorded in `FINDINGS.md`.
        assembly_root = root / "assembly"
        assembly_root.mkdir(parents=True, exist_ok=True)
        self._resolve = build_resolver(root=assembly_root)

    @property
    def tenant_id(self) -> str:
        return self._tenant

    @property
    def declaration(self) -> ProductClassDeclaration:
        return self._declaration

    @property
    def default_perspective(self) -> Perspective:
        return self._perspective

    @property
    def control_plane(self) -> ControlPlaneRegistry:
        return self._control_plane

    @property
    def refusal_recorder(self) -> Any:
        return self._recorder

    @property
    def door(self) -> EgressDoorBinding:
        return self._door

    @property
    def environment(self) -> EnvironmentDocument:
        return self._environment

    def resolve(self, *, tenant: str, product_class: str, version: str,
                perspective: Perspective, request: ProductRequest | None) -> Any:
        """Delegate to ``produce.assemble_and_serve`` through `build_resolver`."""
        return self._resolve(tenant=tenant, product_class=product_class,
                             version=version, perspective=perspective, request=request)


@contextmanager
def door(*, root: Path) -> Iterator[Door]:
    """Compose the producer, open the SDK's standard door over it, write this boot's credential."""
    values = door_values()
    producer = CoverageProducer(root=root, values=values)
    scope, role = str(values["required_scope"]), str(values["role"])

    def resolve_perspective(*, grant: Any, tenant: str,
                            requested_role: str | None) -> Perspective:
        """Serve under the declared role, for the VERIFIED caller.

        The subject is the verified `client_id`, never a value the caller
        supplied, and the role is derived from the declaration rather than
        asked for. Whether that principal may be served AT ALL is the declared
        entitlement's decision, made by the door before this runs.
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
    tokens.write_text(json.dumps({opened.credential: {
        "client_id": opened.principal_id, "scopes": [scope],
        "tenants": [producer.tenant_id]}}), encoding="utf-8")
    try:
        yield Door(
            server=opened.server(issuer_url=str(values["issuer_url"]),
                                 resource_server_url=str(values["resource_server_url"])),
            credential=opened.credential, principal_id=opened.principal_id,
            scope=scope, tenant_id=producer.tenant_id, product_door=opened)
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
    with tempfile.TemporaryDirectory(prefix="cp07-door-") as scratch:
        with door(root=Path(scratch)) as opened:
            auth_context_var.set(AuthenticatedUser(ambient_stdio_identity(
                credential=opened.credential, principal_id=opened.principal_id,
                scope=opened.scope, tenant=opened.tenant_id)))
            opened.server.run(transport="stdio")

if __name__ == "__main__":  # pragma: no cover
    serve()
