"""``create_app`` — the v0 HTTP API skeleton (EXPR-03; D-IMPL-22/23).

SDK-defined framing per CLAUDE.md §8.3 (the HTTP API as one of the three
v0 Experience Layer front doors). The app mirrors the D-IMPL-22/23 ruled
noun set exactly — ``agent``, ``skill``, ``workflow``, ``hitl``,
``replay``, ``artifact``, ``product``, ``config`` — plus health and the
generated OpenAPI document; the routes take and return the SDK's existing
``extra=forbid`` contracts directly, so ``app.openapi()`` *is* the contract
schema, with serialization and routing added and no new semantics.

**What this server cannot do.** It cannot write to the graph: it holds no
graph handle of any kind, and neither does the
:class:`~ccf_runtime.http_api.dependencies.ApiDependencies` bundle it is
built over — there is no field anywhere on this surface that could hold a
route into L2 or L3, and L1 ingestion is deliberately absent from the noun
set by ruling (D-IMPL-23: a generic write endpoint would invite a second
writer path). It cannot mint authority either: every route delegates to
the same factories and Control Plane actions any in-process client uses,
so nothing is reachable over HTTP that is not reachable — identically
governed and identically audited — without it (T-07-25). And it does not
host itself: :func:`create_app` returns an application, never a server —
no bind address, tenant, or threshold exists in this package, and choosing
an interface would be choosing an exposure surface (T-06-14; CINV-01).

**The v0 auth posture, stated honestly (D-22).** The exact sentence lives
in :data:`AUTH_POSTURE_SENTENCE`, is carried verbatim in the OpenAPI
``info.description``, and is asserted by test as the string it is. The
posture is a residual deployment risk recorded at the phase gate: HITL and
agent invocation are authority-bearing surfaces, and the deployment must
keep this app inside its trust boundary.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, params

from ccf_runtime.http_api.auth import HttpAuthProtocol
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import ERROR_UNAUTHENTICATED, refusal_detail
from ccf_runtime.http_api.routes import (
    agent,
    artifact,
    config,
    hitl,
    product,
    replay,
    skill,
    workflow,
)

__ccf_mode__ = "algorithmic"

__all__ = ["AUTH_POSTURE_SENTENCE", "create_app"]

#: The exact, testable v0 auth-posture sentence (D-22 honesty; 07-10 Task 2).
#: One constant so the served document and the test assert the same string.
AUTH_POSTURE_SENTENCE = (
    "This API performs no authentication or authorization in v0: every"
    " request acts with the full authority of the injected fabric handles,"
    " it must be deployed inside the tenant trust boundary, and any future"
    " authentication is a new contract, not a configuration of this one."
)

#: What the surface is, mechanism only (CINV-01 — no deployment vocabulary).
_MECHANISM_LINE = (
    "Typed HTTP front door over the fabric's existing extra=forbid"
    " contracts, mirroring the D-IMPL-22/23 ruled noun set (CLAUDE.md"
    " §8.3; EXPR-03)."
)


#: One optional-hook sentence beside the constant, kept out of it so the
#: test-asserted D-22 posture string stays byte-identical (07-16;
#: D-IMPL-66(a)).
_AUTH_HOOK_LINE = (
    "A deployment may bind an optional bearer-auth hook at create_app"
    " (ccf_runtime.http_api.auth); when no hook is bound, the sentence"
    " above is the posture in force."
)


def create_app(
    deps: ApiDependencies, *, auth: HttpAuthProtocol | None = None
) -> FastAPI:
    """Build the skeleton over ``deps`` — built, never hosted.

    Args:
        deps: The named provider bundle carrying every injected fabric
            handle (the same type the CLI's ``--local`` mode constructs).
        auth: Optional D-IMPL-66(a) auth hook. When provided, every
            mounted router except ``/health`` (liveness carries no
            authority) refuses requests whose credentials the hook does
            not recognise with 401, and the verified grant is stashed on
            ``request.state.token_grant`` for route compositions. When
            ``None`` — the default — nothing is registered and the
            recorded T-07-24 posture is unchanged.

    Returns:
        A configured ``FastAPI`` application. Deliberately not started and
        bound to nothing — hosting is the deployment's decision.
    """
    app = FastAPI(
        title="CCF HTTP API",
        description=(
            f"{_MECHANISM_LINE} {AUTH_POSTURE_SENTENCE} {_AUTH_HOOK_LINE}"
        ),
    )

    guarded: list[params.Depends] = []
    if auth is not None:
        hook = auth

        def _require_grant(request: Request) -> None:
            grant = hook.grant_for_request(
                authorization_header=request.headers.get("Authorization")
            )
            if grant is None:
                raise HTTPException(
                    status_code=401,
                    detail=refusal_detail(
                        error_code=ERROR_UNAUTHENTICATED,
                        message=(
                            "the request carries no credential the bound"
                            " auth hook recognises"
                        ),
                    ),
                )
            request.state.token_grant = grant

        guarded = [Depends(_require_grant)]

    app.include_router(
        agent.build_router(deps), prefix="/agent", dependencies=guarded
    )
    app.include_router(
        skill.build_router(deps), prefix="/skill", dependencies=guarded
    )
    app.include_router(
        workflow.build_router(deps), prefix="/workflow", dependencies=guarded
    )
    app.include_router(
        hitl.build_router(deps), prefix="/hitl", dependencies=guarded
    )
    app.include_router(
        replay.build_router(deps), prefix="/replay", dependencies=guarded
    )
    app.include_router(
        artifact.build_router(deps), prefix="/artifact", dependencies=guarded
    )
    app.include_router(
        product.build_router(deps), prefix="/product", dependencies=guarded
    )
    app.include_router(
        config.build_router(deps), prefix="/config", dependencies=guarded
    )

    @app.get("/health", summary="Liveness (D-IMPL-23)")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
