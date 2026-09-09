"""cp-05's MCP door — the governed path, exposed. Nothing is re-implemented here.

[ADAPT] the wiring. [MECHANISM] `build_egress_server` and the five governance
seams it requires.

**THE MEASUREMENT THIS FILE EXISTS TO TAKE.** Rung 4 asked whether MCP exposure
is disproportionately expensive and answered it with 260 executable lines across
two modules. This door is written to find out how much of that was the DOOR and
how much was the GOVERNED PATH BEHIND IT — because rung 4 had to build its
assemble-and-gate path inside `server/compose.py`, and cp-05 already has one in
`produce.py::produce_governed`. The count at the bottom of this module's own
`README` is the answer.

What this program adds to what already existed
------------------------------------------------
1. **A resolver adapter.** `ProductResolverProtocol` hands five arguments —
   tenant, class, version, perspective, request — and wants back the one typed
   governed result. `produce_governed` already returns exactly that shape, so
   the adapter's real work is translating a `ProductRequest`'s parameters into
   the call, and discharging the ONE obligation the door names and does not
   perform: `refuse_request`.
2. **An entitlement policy**, registered so the door has something to authorize
   against.
3. **A per-boot bearer credential**, because stdio carries no auth channel.

Everything else — the assembly, the operators, the projection, the gates, the
debt assessment, the tolerance comparison, the replay record on both branches —
is behind `produce_governed` and this file does not touch it.

TWO REFUSALS THE DOOR DOES NOT CALL, AND THIS RESOLVER MUST
-------------------------------------------------------------
`runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol` states it plainly:
a resolver that does not call `ccf.products.request::refuse_request` **serves
against an unchecked request**, and one that does not call
`ccf.products.bind::refuse_bound_payload` serves an unvalidated payload against
its own declared schema. That is a ruling (`D-IMPL-113`, extended by
`D-IMPL-121`), not an omission: this door never holds the
`RegisteredProductClass` both comparisons need as their second operand.

**cp-05 discharges the first and not the second, and the reason is stated rather
than left to be inferred**: this class declares no `payload_schema_key`, so
there is no declared payload schema for `refuse_bound_payload` to compare
against and calling it would be ceremony. If cp-05 ever declares one, this is
the file that owes the call.

Nothing is committed as data
------------------------------
The token table is minted per boot into a temporary directory deleted on exit.
The estates are whatever `backends.yaml`'s environment variables name. No host,
port, path or credential appears in any document here.
"""

from __future__ import annotations

import json
import secrets
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

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
from ccf.products.refusal import RequestIdentity, envelope_for
from ccf.products.request import refuse_request
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    TokenGrant,
)
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import build_egress_server

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import deployment as dep  # noqa: E402
import produce as prod  # noqa: E402

#: The door's own document, beside this file.
DOOR = HERE / "door.yaml"

#: What the minted token table is called. A filename is mechanism; the
#: credential inside it is generated per boot.
TOKEN_FILE = "stdio-tokens.json"


def door_values() -> dict[str, Any]:
    """The door's governance values, from the document that owns them."""
    declared = dep.load(DOOR)[dep.DECLARATION]
    missing = sorted(
        k for k in ("tool_description", "required_scope", "issuer_url",
                    "resource_server_url", "principal_id", "role")
        if not str(declared.get(k, "")).strip()
    )
    if missing:
        raise ValueError(
            f"{DOOR} states no {', '.join(missing)} — this door's governance"
            " values live in that document and the SDK holds no default for any"
            " of them (CINV-01)"
        )
    return declared


def build_resolver(*, config: dict[str, Any], replay_root: Path):
    """cp-05's `ProductResolverProtocol` — the adapter, and nothing more.

    **It re-implements no part of the governed path.** `produce_governed`
    already returns the one shape a door may release: a `ServedProduct` whose
    replay reference proves the record was appended, or a `RefusalEnvelope` as
    `ReplayRefusalRecorder` returns it — recorded, disclosed, addressed. What
    is left for this function is translation and the one refusal the door
    delegates.
    """
    declared = config["product_class"]
    contract = dep.request_contract(config)

    def resolve(*, tenant: str, product_class: str, version: str,
                perspective: Perspective, request):
        identity = RequestIdentity(
            product_id=product_class, product_version=version,
            parameters={} if request is None else request.parameters,
            temporal_boundary=None if request is None else request.asked_at,
        )
        if (product_class, version) != (declared["schema_name"],
                                        str(declared["schema_version"])):
            return _refused(
                envelope_for(
                    refuse_request(request=request, declared=contract)
                    or _wrong_address(product_class, version, declared),
                    request=identity),
                perspective=perspective, replay_root=replay_root, config=config)
        # THE RESOURCE PATH. A parameterized class has no standing,
        # parameter-free answer, so a resource read is refused BY NAME rather
        # than served an invented anchor at an invented threshold.
        if request is None:
            return _refused(
                envelope_for(_no_standing_answer(declared), request=identity),
                perspective=perspective, replay_root=replay_root, config=config)
        # THE CONFORMITY DECISION IS THE RESOLVER'S, AND THE DOOR NO LONGER
        # PREEMPTS IT (`D-IMPL-303`).
        #
        # A `refuse_request(request, contract)` pre-check stood here. It made
        # the SDK's contract-aware numeric decode UNREACHABLE from MCP: a
        # declared `number` crosses the wire as canonical decimal TEXT
        # (`D-IMPL-302`), and this call judged the raw lexical value against
        # the declared type before anything could type it — so `"0.05"` was
        # refused `type-mismatch` and the resolver never saw the question.
        #
        # `D-IMPL-113` is the ruling the old comment cited, and read closely it
        # says the opposite of what the call did: *"the SDK ships the
        # mechanism; the deployment's own RESOLVER calls it"*, and *"the door
        # never holds the registered class ... wiring a call at the door would
        # require the door to acquire the registered class."* The obligation is
        # discharged where the declaration, the decoding rules, the defaults,
        # the policy constraints and the effective-request machinery are all in
        # one place — inside `GovernedResolver`, which calls `refuse_request`
        # itself over the DECODED, EFFECTIVE values.
        #
        # What stays door-owned is above: the wrong product address, and the
        # resource surface's absent standing answer. Answering *"is this
        # addressed to the product I expose?"* needs no product contract.
        # Answering *"does materiality='0.05' satisfy `number`?"* does.
        supplied = dict(request.parameters)
        _, governed = prod.produce_governed(
            anchor=request.subject, intent=request.intent,
            depth=supplied.get("depth"),
            materiality=_text(supplied.get("materiality")),
            debt_tolerance=_text(supplied.get("debt_tolerance")),
            basis=supplied.get("basis"),
            follow_guarantees=supplied.get("follow_guarantees"),
            follow_cross_default=supplied.get("follow_cross_default"),
            as_of=supplied.get("as_of"),
            replay_root=replay_root,
        )
        return governed

    return resolve


def _text(value: Any) -> str | None:
    """A number reaches `produce_governed` as text, never as a float."""
    return None if value is None else str(value)


def _wrong_address(product_class: str, version: str, declared: dict[str, Any]):
    from ccf.products.request import ProductRequestViolation

    return ProductRequestViolation(
        parameter="schema_name", reason="not_supported_at_tier",
        detail=(f"this door serves {declared['schema_name']!r} at lane"
                f" {declared['schema_version']!r} and was addressed for"
                f" {product_class!r} at lane {version!r}"),
    )


def _no_standing_answer(declared: dict[str, Any]):
    from ccf.products.request import ProductRequestViolation

    return ProductRequestViolation(
        parameter="lei", reason="missing",
        detail=(f"{declared['schema_name']} is parameterized — an exposure"
                " rollup is a fact about a QUESTION asked at an instant, not a"
                " standing answer — so a resource read carrying no request has"
                " no anchor, no intent and no threshold to serve"),
    )


def _refused(envelope, *, perspective, replay_root: Path, config: dict[str, Any]):
    """Record a pre-assembly refusal the same way an assembled one is recorded."""
    store, _writer, _pins = dep.replay_writers(replay_root)
    from ccf.replay.record import ResolutionNotApplicable

    return ReplayRefusalRecorder(
        artifact_store=store,
        replay_record_class=dep.load(dep.REPLAY)[dep.DECLARATION]["record_class"],
        tenant_id=config["tenant_id"],
        assembly_mode=config["product_class"]["assembly_mode"],
    ).record(
        envelope, perspective=perspective, recorded_at=datetime.now(UTC),
        resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
    )


@dataclass(frozen=True)
class Door:
    """One booted door, with the credential this boot is reached by."""

    server: Any
    credential: str
    principal_id: str
    scope: str
    tenant_id: str


@contextmanager
def door(*, root: Path) -> Iterator[Door]:
    """Register the entitlement, mint this boot's credential, build the door."""
    values = door_values()
    config = dep.load(dep.CONFIG)
    tenant = config["tenant_id"]
    scope = str(values["required_scope"])
    principal, role = str(values["principal_id"]), str(values["role"])

    control_plane = ControlPlaneRegistry()
    control_plane.register_typed(
        product_entitlement_key(tenant_id=tenant),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version=str(config["product_class"]["schema_version"]),
            principals={
                principal: ProductEntitlementGrant(
                    permitted_schema_names=frozenset(
                        {str(config["product_class"]["schema_name"])}),
                    permitted_roles=frozenset({role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    # A DOOR DECISION HAPPENS WHEN IT HAPPENS. The demonstration instant is
    # pinned; binding the AUDIT plane to it would stamp every decision this door
    # ever made 2026-09-07.
    entitlement_source = ControlPlaneProductEntitlementSource(
        control_plane=control_plane, clock=lambda: datetime.now(UTC)
    )
    replay_root = root / "replay"

    tokens = root / TOKEN_FILE
    credential = secrets.token_urlsafe(32)
    tokens.write_text(
        json.dumps({credential: {"client_id": principal, "scopes": [scope]}}),
        encoding="utf-8")

    def resolve_perspective(*, grant: TokenGrant, tenant: str,
                            requested_role: str | None) -> Perspective:
        """Serve under the declared role, for the VERIFIED caller.

        The subject is the verified `client_id`, never a value the caller
        supplied, and `requested_role` is always `None` here — neither surface
        carries a role segment — so the role is derived rather than asked for.
        """
        return Perspective(principal_id=grant.client_id, role=role)

    server = build_egress_server(
        server_name=tenant,
        resolver=build_resolver(config=config, replay_root=replay_root),
        token_verifier=SourceBackedTokenVerifier(source=FileTokenSource(path=tokens)),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(str(values["issuer_url"])),
            resource_server_url=AnyHttpUrl(str(values["resource_server_url"])),
            required_scopes=[scope],
        ),
        entitlement_source=entitlement_source,
        perspective_resolver=resolve_perspective,
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=dep.replay_writers(replay_root)[0],
            replay_record_class=dep.load(dep.REPLAY)[dep.DECLARATION]["record_class"],
            tenant_id=tenant,
            assembly_mode=config["product_class"]["assembly_mode"],
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
    transport's own security boundary is process ownership: this server is a
    child the deployment's client spawned, under the same user, with no socket
    anywhere.
    """
    with tempfile.TemporaryDirectory(prefix="cp05-door-") as scratch:
        with door(root=Path(scratch)) as opened:
            auth_context_var.set(
                AuthenticatedUser(AccessToken(
                    token=opened.credential, client_id=opened.principal_id,
                    scopes=[opened.scope])))
            opened.server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    serve()
