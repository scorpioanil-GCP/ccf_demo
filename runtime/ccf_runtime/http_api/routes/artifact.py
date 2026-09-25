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

Put is unchanged and remains ungoverned by grant: it stores through the same
content-addressed, idempotent
:class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` any client uses. The
store is a persistence substrate behind mechanism, never a second writer to
the graph (CLAUDE.md §7.4).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
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
from ccf_runtime.http_api.errors import (
    ERROR_PRODUCT_DOOR_UNGOVERNED,
    refusal_detail,
)
from ccf_runtime.http_api.grants import authorized_from_request, grant_from_request
from ccf_runtime.http_api.routes import (
    CONTENT_ADDRESS_HEADER,
    governed_refusal_response,
)

__ccf_mode__ = "algorithmic"

__all__ = ["ArtifactPutRequest", "build_router"]

_JSON = "application/json"


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
        name: The artifact's name within that class. It is also this route's
            **authorization resource**, so a deployment states which names a
            scope may write rather than granting the write verb whole.
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
    @authorizes(ACTION_ARTIFACT_WRITE, resource=ResourceBinding.body("name"))
    def put(body: ArtifactPutRequest, request: Request) -> ArtifactRef:
        # D-IMPL-353 §1.4: `Authorized[ArtifactWrite]` for THIS name, or
        # nothing. The gate resolved the resource from the body's `name`.
        authorized = authorized_from_request(request, kind=ArtifactWrite)
        assert authorized.resource == body.name
        # JOIN (§1.2, Lane HANDLES): `put(authorized, artifact)` — `tenant_id`,
        # `artifact_class` and `name` are deleted from the store's signature;
        # class and name become `authorized.resource` ("<class>/<name>"). Left
        # on today's signature; the tenant is already the capability's.
        return deps.artifact_store.put(
            tenant_id=authorized.tenant,
            artifact_class=body.artifact_class,
            name=body.name,
            artifact=body.artifact,
        )

    @router.get("/{content_address}", summary="Artifact get (D-IMPL-23)")
    @authorizes(
        ACTION_ARTIFACT_READ, resource=ResourceBinding.path("content_address")
    )
    def get(content_address: str, request: Request) -> Response:
        # D-IMPL-353 §1.4: the capability for THIS action, or nothing.
        authorized_from_request(request, kind=ArtifactRead)
        # JOIN (§1.2, Lane HANDLES/MCP): `govern_dereference(authorized, ...)`
        # replaces `grant=`; until then the governed step takes the verified
        # grant the gate stashed beside the capability.
        grant = grant_from_request(request)
        if grant is None:
            # Unreachable behind the total gate (401 before any handler);
            # kept for a handler reached some other way, where refusing beats
            # dereferencing governed evidence for nobody.
            raise HTTPException(
                status_code=503,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_DOOR_UNGOVERNED,
                    message=(
                        "this door dereferences governed evidence and no"
                        " verified caller accompanies the call; it refuses"
                        " rather than reading ungoverned (D-IMPL-345 R-1)"
                    ),
                ),
            )
        decided = govern_dereference(
            grant=grant,
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
