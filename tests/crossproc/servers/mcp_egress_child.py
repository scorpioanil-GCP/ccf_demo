"""Child process: assemble a banking Context Product and serve it over MCP.

Run as ``python tests/crossproc/servers/mcp_egress_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — that line is the
readiness handshake the parent fixture blocks on (D-16). There is no sleep
anywhere in the parent's path to this line.

**The product is assembled, not fabricated.** The whole L1→L6 slice runs here:
boot a fabric over a throwaway SQLite file, ingest the fixture envelopes
through L2, execute the four-category operator chain, project, and run the
three gates. Only a :class:`~ccf.products.gates.ServableProduct` reaches the
resolver, which is what makes the cross-process read a read of *the fabric's*
product rather than of a hand-built dict shaped like one.

**The builder is shared with the parent on purpose.**
:func:`build_servable_product` is imported by ``test_mcp_egress.py`` to compute
the value it expects to receive. Two copies of the assembly — one serving, one
asserting — would agree right up until someone changed one of them, and the
test would then be proving that two stale copies match.

**Every domain value comes from ``tests/fixtures/banking/``** — tenant, product
class, schema version, operator parameters, MAX_TTL, the server's own name.
Delete the fixtures and this file has nothing to serve (CLAUDE.md §6.4 applied
to fixture code).
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# The child is spawned as a bare `python <file>`, so it gets none of pytest's
# sys.path work and cannot rely on a relative PYTHONPATH surviving a cwd
# change. Resolving the three roots from __file__ is what makes the child
# runnable from anywhere, which is a property the fixture depends on.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import httpx  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.products.resolver import ReplayRefusalRecorder  # noqa: E402
from ccf.products.entitlement import (  # noqa: E402
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    RegisteredProductClass,
)
from ccf.products.gates import ServableProduct, run_gates  # noqa: E402
from ccf.products.request import (  # noqa: E402
    ProductRequest,
    ProductRequestContract,
    refuse_request,
)
from ccf.projection.plan import Perspective  # noqa: E402
from ccf.replay.record import (  # noqa: E402
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, ServedProduct, serve  # noqa: E402
from ccf_runtime.authz.product_entitlement import (  # noqa: E402
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.mcp.auth import (  # noqa: E402
    FileTokenSource,
    SourceBackedTokenVerifier,
    TokenGrant,
)
from ccf_runtime.mcp.egress import (  # noqa: E402
    ProductNotServable,
    build_egress_server,
    product_uri,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

#: The one credential this test server recognises. A test value, meaningful
#: nowhere else; the SDK ships no token of its own.
DEV_TOKEN = "ccf-egress-dev-token"

#: Deployment vocabulary, chosen here because a test *is* the deployment. The
#: scope and the issuer are this server's; the *principal* is not chosen here
#: — it is the banking fixture's declared perspective principal, so the token
#: identity, the entitlement policy, and the product the fabric assembles all
#: name the same caller (CLAUDE.md §6.4 applied to fixture code).
SCOPE = "ccf:egress"
ISSUER_URL = "https://issuer.invalid"
RESOURCE_SERVER_URL = "https://egress-server.invalid/mcp"

TOKEN_FILENAME = "tokens.json"

#: The entitlement policy's own version lane. A fixture value.
POLICY_VERSION = "1.0.0"

#: The instant the child's audit events carry. Injected, never read from a
#: wall clock — the audit-module discipline, and it keeps the child's log
#: reproducible.
AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)

#: Where this child's denials land, and the class they are filed under. A
#: denial at this door is a recorded decision (`D-IMPL-253` Q13,
#: `D-IMPL-256` (2)) and this fixture writes it to its own workspace.
REPLAY_RECORD_CLASS = "egress-child.replay-record"
ARTIFACT_STORE_DIRNAME = "artifacts"

#: The prose this deployment's parameterised Tool advertises. A test value:
#: the SDK ships no default description, because the words an adopter's
#: consumers read are the deployment's (CINV-01), and here the test is the
#: deployment.
TOOL_DESCRIPTION = (
    "Ask this fixture deployment's one product class a §6.3-addressed"
    " question."
)

#: This class's declared request surface, and it declares **no required
#: parameter** — deliberately, and it is the constraint plan 16-23 records as
#: residual (b). Both parameterised doors send ``parameters={}``, so a class
#: declaring any required request parameter is unreachable through either of
#: them and ``refuse_request`` says so by name
#: (``missing-required-parameter``).
REQUEST_CONTRACT_SEMVER = "1.0.0"


def authorized_http_client(token: str = DEV_TOKEN) -> httpx.AsyncClient:
    """An HTTP client presenting ``token`` as a bearer credential."""
    return httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"})


def write_token_file(
    *, workspace: Path, client_id: str, tenants: frozenset[str]
) -> Path:
    """Write the child's token file for ``client_id``, scoped to ``tenant``.

    The tenant is required (``SEC-018``): an unscoped grant reaches nothing.
    """
    token_file = workspace / TOKEN_FILENAME
    token_file.write_text(
        json.dumps(
            {
                DEV_TOKEN: {
                    "client_id": client_id,
                    "scopes": [SCOPE],
                    "tenants": sorted(tenants),
                }
            }
        ),
        encoding="utf-8",
    )
    return token_file


class ProductAddress(NamedTuple):
    """The three segments that name a product on the egress surface."""

    tenant: str
    product_class: str
    version: str

    @property
    def uri(self) -> str:
        """The ``ccf-product://`` URI this address renders to."""
        return product_uri(
            tenant=self.tenant,
            product_class=self.product_class,
            version=self.version,
        )


class AssembledProduct(NamedTuple):
    """A gated product, the address it is served at, and who may receive it.

    The last four members are the inputs :func:`~ccf.products.gates.run_gates`
    needs to gate a *second* candidate for the same class. They exist because
    a resolver that answers a question must be able to produce the product
    that answers *that* question, and a ``ServableProduct`` is deliberately
    unconstructible outside the gate path (INV-CH7-52) — so varying the answer
    means re-gating, never hand-building.
    """

    servable: ServableProduct
    #: The SAME vessel, served: its decision record appended through
    #: `replay_writer` and the reference carried beside it — the only served
    #: shape a door releases (`D-IMPL-260` P-A).
    served: ServedProduct
    #: The writer every answer this fixture serves is recorded through, over a
    #: file store beside the throwaway graph.
    replay_writer: ReplayWriter
    #: What the decision record is built from, kept so `answer_for` can record
    #: a per-question answer the same way the standing one was recorded.
    execution: Any
    policy_binding: PolicyBinding
    tenant_id: str
    address: ProductAddress
    server_name: str
    principal_id: str
    role: str
    registry: ControlPlaneRegistry
    product_class: RegisteredProductClass
    operators: frozenset[str]
    now: datetime


def build_servable_product(*, database_path: Path) -> AssembledProduct:
    """Run the banking slice end to end and gate the result.

    The slice's wiring — resolution spec, envelopes, operator parameters,
    projection plan, product-class registration, gate invocation — is reused
    from the proto-quickstart integration module rather than re-implemented.
    That module is the repository's one worked example of assembling a product
    the way a deployment would, and a second implementation here would be a
    second thing to keep correct.

    Args:
        database_path: Where this process's throwaway graph lives. Supplied by
            the caller so the parent and the child cannot collide on a file.

    Returns:
        The gated product plus the address it is served at.
    """
    from integration.test_proto_quickstart import (  # noqa: PLC0415
        _Fabric,
        _candidate,
        _execute,
        _envelopes,
        _load,
        _product_class,
        _resolution_spec,
    )

    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    ontology: Any = _load("ontology.yaml")
    control: Any = _load("controlplane.yaml")
    events: Any = _load("events.yaml")

    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(keys["policy_bundle"], control["policy_bundle"])
    handle = boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        fabric = _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
        execution = _execute(fabric)
        product_class = _product_class(fabric)
        gated = run_gates(
            _candidate(fabric, execution, product_class),
            engine_resolved=execution.operators_invoked,
            now=fabric.now,
            registry=fabric.registry,
            product_class=product_class,
        )
    finally:
        handle.close()

    if not isinstance(gated, ServableProduct):
        raise AssertionError(
            f"the fixture product did not pass the gates: {gated}"
        )
    replay_writer = ReplayWriter(
        store=FileArtifactStore(root=database_path.parent / "fixture-replay"),
        artifact_class=REPLAY_RECORD_CLASS,
    )
    policy_binding = PolicyBinding(key=keys["policy_bundle"], version=policy_version)
    served = _served(
        gated,
        execution=execution,
        principal_id=control["perspective"]["principal_id"],
        role=control["perspective"]["role"],
        policy_binding=policy_binding,
        recorded_at=fabric.now,
        tenant_id=fabric.tenant_id,
        replay_writer=replay_writer,
    )
    return AssembledProduct(
        servable=gated,
        served=served,
        replay_writer=replay_writer,
        execution=execution,
        policy_binding=policy_binding,
        tenant_id=fabric.tenant_id,
        address=ProductAddress(
            tenant=fabric.tenant_id,
            product_class=product_class.schema_name,
            version=product_class.schema_version,
        ),
        # Deployment identity, taken from the fixture that owns it rather than
        # written here — a server name in code is a domain value in code.
        server_name=control["product_class"]["plan_id"],
        # The caller this deployment declares, and the capacity it may ask in.
        # Both come from the same fixture the assembly path conditions on, so
        # the token identity, the entitlement policy and the product agree by
        # construction rather than by coincidence.
        principal_id=control["perspective"]["principal_id"],
        role=control["perspective"]["role"],
        registry=registry,
        product_class=product_class,
        operators=execution.operators_invoked,
        now=fabric.now,
    )


def declared_request_contract(
    assembled: AssembledProduct,
) -> ProductRequestContract:
    """This class's declared request surface — four axes and nothing else.

    ``arguments`` declares no property and requires none, which is what makes
    the class reachable through a parameterised door at all: both doors send
    ``parameters={}``, so a class declaring any *required* request parameter
    would be refused by :func:`~ccf.products.request.refuse_request` before
    anything was assembled.
    """
    return ProductRequestContract(
        semver=REQUEST_CONTRACT_SEMVER,
        schema_name=assembled.address.product_class,
        schema_version=assembled.address.version,
        arguments={"properties": {}, "required": []},
    )


def _served(
    gated: ServableProduct,
    *,
    execution: Any,
    principal_id: str,
    role: str,
    policy_binding: PolicyBinding,
    recorded_at: datetime,
    tenant_id: str,
    replay_writer: ReplayWriter,
) -> ServedProduct:
    """Record the decision, then deliver — the shipped seam, not a stand-in.

    `D-IMPL-260` P-A: a door releases only a `ServedProduct`, whose replay
    reference proves the record was appended. So this fixture serves the way
    a deployment does: the record is built from what the execution and the
    gated product already know and appended by `ccf.replay.serve.serve`
    before the vessel is handed back.
    """
    # `tenant_id` is read off the product when there is one; passing it too
    # is two sources for one fact and the builder refuses it.
    record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=Perspective(principal_id=principal_id, role=role),
        policy_bindings=(policy_binding,),
        assembly_mode="algorithmic",
        recorded_at=recorded_at,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    return serve(product=gated, record=record, replay_writer=replay_writer)


def answer_for(
    assembled: AssembledProduct, request: ProductRequest
) -> ServedProduct:
    """Gate the product that answers *this* question.

    The whole point of the parameterised door is that the answer depends on
    the question, so this fixture makes it depend visibly: the asked-about
    subject and the instant it was asked as-of are carried into the payload,
    and the result goes back through :func:`~ccf.products.gates.run_gates`
    rather than being hand-built — a ``ServableProduct`` is evidence the gates
    ran and there is no other way to hold one.

    ``D-IMPL-126`` records the trap this avoids: a naive projection reading
    ``view.relationships`` wholesale produced *identical* content addresses for
    two different subjects, because seeds narrow only when a segment fragment
    declares a ``traverse``. A fixture that failed to differentiate would make
    the two-subjects assertion pass for the wrong reason — or fail while the
    door was blameless.
    """
    candidate: ContextProductContract = assembled.servable.product.model_copy(
        update={
            "payload": {
                **assembled.servable.product.payload,
                "asked_subject": request.subject,
                "asked_as_of": request.asked_at.isoformat(),
            }
        }
    )
    gated = run_gates(
        candidate,
        engine_resolved=assembled.operators,
        now=assembled.now,
        registry=assembled.registry,
        product_class=assembled.product_class,
    )
    if not isinstance(gated, ServableProduct):
        raise AssertionError(f"the answered product did not gate: {gated}")
    return _served(
        gated,
        execution=assembled.execution,
        principal_id=assembled.principal_id,
        role=assembled.role,
        policy_binding=assembled.policy_binding,
        recorded_at=assembled.now,
        tenant_id=assembled.tenant_id,
        replay_writer=assembled.replay_writer,
    )


def build_entitlement_registry(assembled: AssembledProduct) -> ControlPlaneRegistry:
    """Register this deployment's product entitlement policy.

    Registration is adopter code: no deployment manifest can name
    ``ccf.product-entitlement-policy`` (15.5-03's placement), so the door's
    composition root registers it against the real contract — which is what
    makes a near-miss a validation failure here rather than a refusal at the
    first served call.
    """
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=assembled.address.tenant),
        ProductEntitlementPolicy(
            tenant_id=assembled.address.tenant,
            policy_version=POLICY_VERSION,
            principals={
                assembled.principal_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset(
                        {assembled.address.product_class}
                    ),
                    permitted_roles=frozenset({assembled.role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return registry


def _recorder(root: Path, *, tenant: str) -> ReplayRefusalRecorder:
    """The ONE minting seam this child's door binds.

    Built with the keyword list `ccf.products.resolver::build_governed_resolver`
    uses for its own, so a door's recorder and a resolver's are the same shape
    over one store — *one writer, one record form*. This fixture composes no
    `GovernedResolver`, so there is none to take the recorder off; the tenant
    and the record class come from the values the fixture already holds.
    """
    return ReplayRefusalRecorder(
        artifact_store=FileArtifactStore(root=root / ARTIFACT_STORE_DIRNAME),
        replay_record_class=REPLAY_RECORD_CLASS,
        tenant_id=tenant,
        assembly_mode="algorithmic",
    )


def build_server(*, workspace: Path) -> FastMCP:
    """Assemble the product and wrap it in the authenticated egress server."""
    assembled = build_servable_product(
        database_path=workspace / "egress-child.sqlite3"
    )
    registry = build_entitlement_registry(assembled)
    declared = declared_request_contract(assembled)

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ServedProduct:
        """Serve exactly the one assembled address; refuse anything else.

        The refusal matters as much as the hit: a resolver that returned its
        single product for any URI would make the scheme-separation assertion
        in the parent test pass for the wrong reason.

        **Two answers, because there are two doors.** ``request is None`` is
        the resource asking for the class's standing answer; a request is the
        tool asking a question, and a question gets the product that answers
        it. The request is compared against the class's declared surface
        first — the ``refuse_request`` obligation
        :class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` places on
        every resolver and no shipped door discharges (``D-IMPL-113``).
        """
        requested = ProductAddress(
            tenant=tenant, product_class=product_class, version=version
        )
        if requested != assembled.address:
            raise ProductNotServable(str(requested))
        if request is None:
            return assembled.served
        violation = refuse_request(request=request, declared=declared)
        if violation is not None:
            raise ValueError(f"request refused: {violation.detail}")
        return answer_for(assembled, request)

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """Derive the caller's capacity from its verified identity.

        This deployment's statement, not the SDK's: the role comes from the
        fixture's declared perspective, and the subject is the verified
        ``client_id`` — never a value the caller supplied. Whatever this
        returns is still checked against the principal's grant before a
        product is resolved, so widening it here would not widen the door.
        """
        return Perspective(
            principal_id=grant.client_id,
            role=requested_role if requested_role is not None else assembled.role,
        )

    return build_egress_server(
        server_name=assembled.server_name,
        resolver=resolve,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(
                path=write_token_file(
                    workspace=workspace,
                    client_id=assembled.principal_id,
                    # The neighbour is included DELIBERATELY: the parent
                    # asserts what the ENTITLEMENT decides about a foreign
                    # address the caller can reach. The tenancy floor is
                    # proven separately (`SEC-018`).
                    tenants=frozenset(
                        {
                            assembled.tenant_id,
                            f"{assembled.tenant_id}-not-this-one",
                            f"{assembled.tenant_id}-no-policy",
                        }
                    ),
                )
            )
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(ISSUER_URL),
            resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
            required_scopes=[SCOPE],
        ),
        entitlement_source=ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: AUDIT_INSTANT
        ),
        perspective_resolver=resolve_perspective,
        # `D-IMPL-256` (2): this door entitles, so it does not build without a
        # recorder. The workspace is the scratch root the token file already
        # lives in.
        refusal_recorder=_recorder(workspace, tenant=assembled.address.tenant),
        # This deployment opts in, because the assertion it exists to support
        # is that a client can ask its own question over a real wire. A
        # deployment that says nothing gets no tool at all.
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import anyio
    import uvicorn

    with tempfile.TemporaryDirectory() as workspace:
        server_app = build_server(workspace=Path(workspace))

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(server_app.streamable_http_app(), log_level="error")
        )

        async def serve() -> None:
            async def announce() -> None:
                # A 5 ms poll of *this process's own* server object, which is
                # not the parent-side sleep-and-hope D-16 prohibits: it
                # observes a real state flag rather than guessing a duration,
                # and the parent still learns nothing until the flag flips.
                while not server.started:
                    await anyio.sleep(0.005)
                print(f"READY {port}", flush=True)

            async with anyio.create_task_group() as group:
                group.start_soon(announce)
                await server.serve(sockets=[bound])

        anyio.run(serve)


if __name__ == "__main__":
    main()
