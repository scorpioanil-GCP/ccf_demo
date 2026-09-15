"""The MCP egress door: the governed spread, reached from another process.

[ADAPT] the values in ``door.yaml``. [MECHANISM] everything below.

**This door re-implements no part of the governed path.** ``produce.
assemble_and_serve`` already returns the one shape a door may release — a
``ServedProduct`` whose replay reference proves the record was appended, or a
``RefusalEnvelope`` as ``ReplayRefusalRecorder`` returns it: recorded,
disclosed, addressed. What is left for this module is translation (the wire's
decimal text into the typed question), the one refusal the door itself owns
(an address this door does not serve, refused by name and recorded), and the
identity the door ASSERTS on every outcome (`D-IMPL-340` ruling 2).

**Why the assertion, and why it authorizes nothing.** A consumer that acquires
this product as a composite child (`CP-SPEC-014`) holds the door's asserted
``producer_id`` and the served product's ``tenant_id`` to the
``ccf.mcp-producer`` registration IT governs. The assertion is a claim this
door makes about itself; the registration is what the consumer trusts.
Equality is a binding check, never an authorization — a door claiming another
producer's id is refused ``producer-mismatch`` on the consumer side, and a
door claiming the right one gains nothing it did not already have.

Two transports:

* ``serve`` — stdio, the entry point ``door.yaml`` declares.
* ``loopback`` — bind an ephemeral ``127.0.0.1`` port, announce it once the
  server is up, and serve streamable HTTP with REAL bearer authentication.
  Reached through ``run.py --door``, which prints the ``READY {port}`` line a
  harness reads; the cross-deployment proof spawns that and reaches the door
  only through the SDK's shared MCP client. Readiness is a handshake, never a
  sleep. This module itself writes to no terminal.

The bearer credential is minted per boot unless the parent that spawned this
process supplied one through ``CCF_CP_03C_DOOR_TOKEN`` — the one way a parent
learns this boot's credential without a side channel.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO_ROOT = EXAMPLE.parent.parent
# Spawned as bare `python serve.py`, none of pytest's or the Makefile's path
# setup applies; the door puts the SDK, the runtime and its own tree on the
# path itself so a subprocess boot cannot fail at import and surface through
# the handshake as "did not announce readiness".
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", EXAMPLE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.products.entitlement import (  # noqa: E402
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import RefusalEnvelope, RequestIdentity, envelope_for  # noqa: E402
from ccf.products.request import ProductRequest, ProductRequestViolation  # noqa: E402
from ccf.products.resolver import ReplayRefusalRecorder  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402
from ccf.replay.record import ResolutionNotApplicable  # noqa: E402
from ccf.replay.serve import ServedProduct  # noqa: E402
from ccf_runtime.authz.product_entitlement import (  # noqa: E402
    ControlPlaneProductEntitlementSource,
    TokenGrant,
)
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier  # noqa: E402
from ccf_runtime.mcp.egress import build_egress_server  # noqa: E402

import deployment  # noqa: E402
import produce  # noqa: E402

DOOR = HERE / "door.yaml"
TOKEN_FILE = "tokens.json"

#: The one environment variable a parent may set so it knows this boot's
#: bearer credential without a side channel. Unset -> minted per boot.
CREDENTIAL_ENV = "CCF_CP_03C_DOOR_TOKEN"

#: The record class the door's recorder files under — the same string
#: `produce.py` hands `build_governed_resolver`, so a refused and a served
#: decision land under one class rather than two.
REPLAY_RECORD_CLASS = "ccf.replay-record"

REQUIRED = (
    "tool_description", "required_scope", "issuer_url", "resource_server_url",
    "principal_id", "role", "serve_entrypoint", "producer_id",
)


def door_values() -> dict[str, Any]:
    """The door's governance values, from the document that owns them."""
    declared: dict[str, Any] = yaml.safe_load(DOOR.read_text(encoding="utf-8"))["declaration"]
    missing = sorted(k for k in REQUIRED if not str(declared.get(k, "")).strip())
    if missing:
        raise ValueError(
            f"{DOOR} states no {', '.join(missing)} — this door's governance"
            " values live in that document and the SDK holds no default for any"
            " of them (CINV-01)"
        )
    return declared


def _typed(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """The wire's parameters as the contract types them.

    Numbers cross the door as canonical decimal TEXT (`D-IMPL-302`); the typed
    question the governed path judges carries an integer period count, a
    Decimal tolerance and a boolean peer flag. Names this door does not know —
    `as_of` among them — pass through untouched so the CONTRACT refuses them by
    name, with a record, rather than the door.
    """
    typed = dict(parameters)
    if isinstance(typed.get(deployment.PERIODS), str):
        typed[deployment.PERIODS] = int(typed[deployment.PERIODS])
    if isinstance(typed.get(deployment.DEBT_TOLERANCE), (str, float, int)):
        typed[deployment.DEBT_TOLERANCE] = Decimal(str(typed[deployment.DEBT_TOLERANCE]))
    if isinstance(typed.get(deployment.INCLUDE_PEERS), str):
        typed[deployment.INCLUDE_PEERS] = typed[deployment.INCLUDE_PEERS].lower() == "true"
    return typed


def _wrong_address(product_class: str, version: str, declared: Mapping[str, Any]) -> ProductRequestViolation:
    """An address this door does not serve — `class-mismatch`, returned as data.

    The same family as an intent the class is not registered for: the caller
    addressed the wrong class or lane, and the door says which one it serves.
    """
    return ProductRequestViolation(
        reason="class-mismatch",
        key="schema_version" if product_class == declared["schema_name"] else "schema_name",
        declared_type=f"{declared['schema_name']}@{declared['schema_version']}",
        presented_type=f"{product_class}@{version}",
        declared_keys=frozenset(),
        presented_keys=frozenset(),
        detail=(
            f"this door serves {declared['schema_name']!r} at lane"
            f" {declared['schema_version']!r} and was addressed for"
            f" {product_class!r} at lane {version!r}"
        ),
    )


def build_resolver(*, config: Mapping[str, Any], assembly_root: Path, replay_root: Path) -> Any:
    """`ProductResolverProtocol` — translate and delegate, nothing more.

    The door refuses exactly one thing of its own: an address it does not
    serve, judged before any assembly and RECORDED the same way an assembled
    refusal is. Everything else — a missing `debt_tolerance`, an intent the
    class does not serve, a parameter out of its domain, an obligor the
    principal may not see, a spread outside its window, a debt above the
    tolerance — is the governed path's verdict, returned as data with a replay
    reference (`D-IMPL-289`: the door hand-builds no envelope).
    """
    declared = config["product_class"]
    contract = deployment.config()["request_contract"]

    def refused(envelope: RefusalEnvelope, *, perspective: Perspective) -> RefusalEnvelope:
        return ReplayRefusalRecorder(
            artifact_store=FileArtifactStore(root=replay_root),
            replay_record_class=REPLAY_RECORD_CLASS,
            tenant_id=str(config["tenant_id"]),
            assembly_mode=str(declared["assembly_mode"]),
        ).record(
            envelope,
            perspective=perspective,
            recorded_at=datetime.now(UTC),
            resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
        )

    def resolve(
        *, tenant: str, product_class: str, version: str, perspective: Perspective, request: Any
    ) -> ServedProduct | RefusalEnvelope:
        # `expose_product_resource=False` below, so `request` is never None on
        # the only surface this door opens: a parameterized class has no
        # standing answer.
        identity = RequestIdentity(
            product_id=product_class, product_version=version,
            parameters={} if request is None else request.parameters,
            temporal_boundary=None if request is None else request.asked_at,
        )
        if (product_class, version) != (declared["schema_name"], str(declared["schema_version"])):
            return refused(
                envelope_for(_wrong_address(product_class, version, declared), request=identity),
                perspective=perspective,
            )
        asked = ProductRequest(
            schema_name=request.schema_name,
            schema_version=request.schema_version,
            subject=request.subject,
            intent=request.intent,
            freshness=request.freshness,
            asked_at=request.asked_at,
            parameters=_typed(request.parameters),
        )
        # Serve under the VERIFIED caller's principal: the governed path reads
        # the request's own `jurisdictions` (or the class default) for the
        # policy envelope, and the perspective's principal is the caller's.
        outcome = produce.assemble_and_serve(
            asked=asked, root=assembly_root,
            principal_id=None if perspective.principal_id == deployment.perspective().principal_id else perspective.principal_id,
        )
        if isinstance(outcome, RefusalEnvelope):
            return outcome
        return outcome.served

    return resolve


@dataclass(frozen=True)
class Door:
    """One booted door, with the credential this boot is reached by."""

    server: Any
    credential: str
    principal_id: str
    scope: str
    tenant_id: str
    producer_id: str


@contextmanager
def door(*, root: Path) -> Iterator[Door]:
    """Register the entitlement, mint this boot's credential, build the door."""
    values = door_values()
    config = deployment.config()
    tenant = str(config["tenant_id"])
    scope, principal, role = str(values["required_scope"]), str(values["principal_id"]), str(values["role"])
    producer_id = str(values["producer_id"])

    control_plane = ControlPlaneRegistry()
    control_plane.register_typed(
        product_entitlement_key(tenant_id=tenant),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version=str(config["product_class"]["schema_version"]),
            principals={
                principal: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({str(config["product_class"]["schema_name"])}),
                    permitted_roles=frozenset({role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    # A DOOR DECISION HAPPENS WHEN IT HAPPENS: the entitlement clock is the
    # wall clock, deliberately, while the question's own instant travels in
    # the request.
    entitlement_source = ControlPlaneProductEntitlementSource(
        control_plane=control_plane, clock=lambda: datetime.now(UTC)
    )

    replay_root = root / "replay"
    replay_root.mkdir(parents=True, exist_ok=True)
    # Must exist BEFORE the first call: SQLite will not create a missing
    # parent, and the failure would surface as an opaque transport error.
    assembly_root = root / "assembly"
    assembly_root.mkdir(parents=True, exist_ok=True)

    tokens = root / TOKEN_FILE
    credential = os.environ.get(CREDENTIAL_ENV) or secrets.token_urlsafe(32)
    tokens.write_text(
        json.dumps({credential: {"client_id": principal, "scopes": [scope]}}), encoding="utf-8"
    )

    def resolve_perspective(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
        """Serve under the declared role, for the VERIFIED caller."""
        return Perspective(principal_id=grant.client_id, role=role)

    server = build_egress_server(
        server_name=tenant,
        resolver=build_resolver(config=config, assembly_root=assembly_root, replay_root=replay_root),
        token_verifier=SourceBackedTokenVerifier(source=FileTokenSource(path=tokens)),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(str(values["issuer_url"])),
            resource_server_url=AnyHttpUrl(str(values["resource_server_url"])),
            required_scopes=[scope],
        ),
        entitlement_source=entitlement_source,
        perspective_resolver=resolve_perspective,
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=FileArtifactStore(root=replay_root),
            replay_record_class=REPLAY_RECORD_CLASS,
            tenant_id=tenant,
            assembly_mode=str(config["product_class"]["assembly_mode"]),
            disclosure_level_for=entitlement_source.disclosure_level_for,
        ),
        # A parameterized class has no standing answer: TOOL-ONLY door.
        expose_product_resource=False,
        expose_product_tool=True,
        product_tool_description=str(values["tool_description"]),
        # `D-IMPL-340` ruling 2 — supplied TOGETHER or not at all. Every
        # DoorOutcome carries ProducerAssertion(producer_id, tenant_id).
        producer_id=producer_id,
        producer_tenant=tenant,
    )
    try:
        yield Door(
            server=server, credential=credential, principal_id=principal,
            scope=scope, tenant_id=tenant, producer_id=producer_id,
        )
    finally:
        tokens.unlink(missing_ok=True)


def serve() -> None:
    """Boot the door and serve it on stdio — the entry point `door.yaml` declares."""
    with tempfile.TemporaryDirectory(prefix="cp03c-door-") as scratch:
        with door(root=Path(scratch)) as opened:
            auth_context_var.set(
                AuthenticatedUser(
                    AccessToken(token=opened.credential, client_id=opened.principal_id, scopes=[opened.scope])
                )
            )
            opened.server.run(transport="stdio")


def loopback(*, announce: Callable[[int], None]) -> None:
    """Bind an ephemeral 127.0.0.1 port, announce it once the server is up, serve HTTP.

    Bearer auth is REAL on this transport (FastMCP's middleware is on the HTTP
    app), so `auth_context_var` is NOT pre-set: a caller without the boot's
    credential is refused by the door, not admitted by the harness.

    THE DOOR WRITES TO NO TERMINAL. Readiness is handed to ``announce`` — the
    one module of this example that drives a run and prints, ``run.py``, is
    what turns the port into the ``READY {port}`` line a harness reads — so
    the door stays a fabric-facing module with no presentation in it.
    """
    import anyio
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="cp03c-door-") as scratch:
        with door(root=Path(scratch)) as opened:
            bound = socket.socket()
            bound.bind(("127.0.0.1", 0))
            bound.listen(64)
            port = bound.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(opened.server.streamable_http_app(), log_level="error"))

            async def run() -> None:
                async def ready() -> None:
                    while not server.started:
                        await anyio.sleep(0.005)
                    announce(port)

                async with anyio.create_task_group() as group:
                    group.start_soon(ready)
                    await server.serve(sockets=[bound])

            anyio.run(run)


def main(argv: list[str] | None = None) -> None:
    """The entry point `door.yaml` declares: the door on stdio.

    The loopback harness mode is reached through ``run.py --door``, because
    announcing a port is a line on a terminal and this module writes none.
    """
    argparse.ArgumentParser(description="The canonical credit-risk.spread producer's MCP egress door (stdio).").parse_args(argv)
    serve()


if __name__ == "__main__":  # pragma: no cover
    main()
