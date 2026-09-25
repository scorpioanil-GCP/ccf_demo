"""The ``artifact`` noun — get/put against the injected store (D-IMPL-23).

**Get is a governed dereference and is records-only** (``D-IMPL-345`` R-3).
The route authenticates through the app's own dependency, reads the verified
grant, calls
:func:`~ccf_runtime.authz.delivery_boundary.govern_dereference` and encodes
what it returns: the exact stored bytes of a governed record the caller is
entitled to read, or an already-recorded, already-disclosed refusal shell.
Bytes that are not a Decision Replay record — a graph-query pin, an admitted
child contract, a child question, an admission record, a workflow trace, the
store's own naming index, anything a caller filed itself — are withheld, and
withheld as the same absence as a nonexistent address. The reason is the write
path below: while ``put`` is forgeable (the named ``D-IMPL-73`` limitation), a
rule that authorized arbitrary blobs by following a record that names them
would trust records a caller can write. Dave's words: *"Do not authorize
arbitrary blobs by following a record reference while artifact PUT remains
forgeable."*

Before ``D-IMPL-345`` this handler returned the raw bytes at any address to
any recognized bearer, which made it the unguarded twin of the replay routes —
a record refused at ``/replay/decisions`` was readable here at the same
address — and, because the store performed no shape check, a read path for the
store's naming index and for paths outside it (`S-02`, closed in
:func:`~ccf.artifacts.protocol.held_content_address`).

Put stores through the same content-addressed, idempotent
:class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` any client uses, under
the capability the gate minted (``D-IMPL-353`` §1.2): the route's declared
resource is the store's own target, ``"{artifact_class}/{name}"`` composed
from the body, so the authorizer decides on exactly the string the store files
under and ``put(authorized, artifact)`` takes class, name and tenant from the
capability alone. The store is a persistence substrate behind mechanism, never
a second writer to the graph (CLAUDE.md §7.4).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from starlette.requests import Request

from ccf.artifacts.protocol import ArtifactRef
from ccf.authz.capability import ArtifactRead, ArtifactWrite
from ccf.contracts.base import CCFContract
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_HTTP_ARTIFACT_READ,
    DereferenceRequest,
    DisclosingRecorderProtocol,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import (
    ProductEntitlementSourceProtocol,
)
from ccf_runtime.authz.refusals import ACTION_ARTIFACT_READ, ACTION_ARTIFACT_WRITE
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.grants import authorized_from_request
from ccf_runtime.http_api.routes import (
    CONTENT_ADDRESS_HEADER,
    governed_refusal_response,
)

__ccf_mode__ = "algorithmic"

__all__ = ["ARTIFACT_WRITE_RESOURCE", "ArtifactPutRequest", "build_router"]

_JSON = "application/json"

#: The resource an artifact write is decided on: the store's own target,
#: ``"<class>/<name>"`` — the same segments the naming key uses and the same
#: template the MCP artifact server's ``put_artifact`` composes (``D-IMPL-353``
#: §1.2), so a scope mapping names artifacts in one vocabulary at both doors.
ARTIFACT_WRITE_RESOURCE = "{artifact_class}/{name}"


def _route_path(request: Request, reference: str) -> str:
    """The ROUTE the caller reached, never the string it asked for.

    ``/artifact/{content_address}`` rather than ``/artifact/<the address>``:
    the reference a caller supplied is echoed in exactly ONE place, its
    refusal's ``request.parameters``, so every other member of the shell is
    constant across asks and a control comparing two refusals is comparing
    the determination rather than the two strings that provoked it.
    """
    path = request.url.path
    template = str(getattr(request.scope.get("route"), "path", ""))
    if template.endswith("}") and path.endswith(reference):
        return path[: -len(reference)] + template[template.rfind("{") :]
    return path


class ArtifactPutRequest(CCFContract):
    """One put: the addressing facts and the canonicalizable payload.

    **There is no ``tenant_id`` here, and its absence is the contract**
    (``SEC-002``). The field used to be the caller's, which made the tenant an
    artifact was filed under a thing the caller wrote — so a recognized bearer
    could file into any tenant's namespace and the store faithfully obliged.
    The tenant is the **capability's** — selected by the gate from the
    verified grant's set and read here as ``authorized.tenant``
    (:func:`~ccf_runtime.http_api.grants.authorized_from_request`; D-IMPL-353
    §1.3) — and comes from nothing else. Deleted rather than kept-and-checked:
    a field that must equal a value the door already holds is a field with no
    readings left, and every one it could still have is wrong.

    Attributes:
        artifact_class: The class the bytes are filed under.
        name: The artifact's name within that class. Together with
            ``artifact_class`` it spells this route's **authorization
            resource**, :data:`ARTIFACT_WRITE_RESOURCE`, so a deployment states
            which classes and names a scope may write rather than granting the
            write verb whole — and the store files under exactly the string
            the authorizer decided on.
        artifact: The canonicalizable payload.
    """

    artifact_class: str
    name: str
    artifact: dict[str, object]


def build_router(
    deps: ApiDependencies,
    *,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: DisclosingRecorderProtocol,
) -> APIRouter:
    """The artifact router over the injected store and governance seams.

    Args:
        deps: The named provider bundle carrying the artifact store and the
            Control Plane whose audit log every dereference appends to.
        entitlement_source: The deployment's entitlement seam. **Required**
            (``SEC-001``): there is no longer a configuration of
            ``create_app`` that omits it, so the rule ``D-IMPL-345`` R-1 used
            to hold with a per-request ``503`` is held by the signature.
        refusal_recorder: The ONE minting seam, which also states the
            disclosure level. **Required**, same reason.
    """
    router = APIRouter()

    @router.post(
        "",
        response_model=ArtifactRef,
        summary="Artifact put (D-IMPL-23)",
    )
    @authorizes(
        ACTION_ARTIFACT_WRITE,
        resource=ResourceBinding.body_composed(ARTIFACT_WRITE_RESOURCE),
    )
    def put(body: ArtifactPutRequest, request: Request) -> ArtifactRef:
        # D-IMPL-353 §1.4: `Authorized[ArtifactWrite]` for THIS "<class>/<name>",
        # or nothing. §1.2: the store takes the tenant, the class and the name
        # from the capability — the handler hands it the payload and nothing
        # about where it lands.
        authorized = authorized_from_request(request, kind=ArtifactWrite)
        return deps.artifact_store.put(authorized, body.artifact)

    @router.get("/{content_address}", summary="Artifact get (D-IMPL-23)")
    @authorizes(
        ACTION_ARTIFACT_READ, resource=ResourceBinding.path("content_address")
    )
    def get(content_address: str, request: Request) -> Response:
        # D-IMPL-353 §1.4: `Authorized[ArtifactRead]` for THIS address, or
        # nothing — and the governed step verifies it again, bound to the
        # reference, before its first real statement (§1.2).
        decided = govern_dereference(
            authorized_from_request(request, kind=ArtifactRead),
            reference=DereferenceRequest(
                reference=content_address, by_uri=False, wants_bytes=True
            ),
            store=deps.artifact_store,
            entitlement_source=entitlement_source,
            refusal_recorder=refusal_recorder,
            audit_log=deps.control_plane.audit_log,
            surface=SURFACE_HTTP_ARTIFACT_READ,
            address=_route_path(request, content_address),
        )
        if isinstance(decided, RefusalEnvelope):
            return governed_refusal_response(decided)
        assert decided.payload is not None  # a bytes ask always carries them
        return Response(
            content=decided.payload,
            media_type=_JSON,
            # The address the caller asked for and the bytes it received, so a
            # zero-`ccf` client can verify one against the other in a stdlib
            # line — the same claim `canonical_response` publishes.
            headers={CONTENT_ADDRESS_HEADER: decided.content_address},
        )

    return router
