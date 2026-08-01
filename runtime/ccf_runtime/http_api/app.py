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

import logging
import warnings
from typing import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response, params

from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
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

__all__ = ["AUTH_POSTURE_SENTENCE", "CcfInsecureDefaultWarning", "create_app"]


class CcfInsecureDefaultWarning(UserWarning):
    """The app was built on the insecure default posture (D-IMPL-73).

    Emitted by :func:`create_app` when no auth hook is bound and the
    caller has not passed ``acknowledge_insecure_default=True`` — the
    single suppression surface (no environment variable, by ruling).
    Exported so CI can escalate it (``-W error::…``) and tests can
    target it (``pytest.warns``). SDK-defined mechanism per CLAUDE.md
    §8.3; the warning text is a security-posture signal, not a domain
    value (No-Hardcoding boundary note in the D-IMPL-73 ruling).
    """


#: One message for both ruled emission points (warnings.warn at
#: construction; logging WARNING at first request) — the D-IMPL-73
#: "two emission points to keep consistent" consequence, kept
#: consistent by sharing the string.
_INSECURE_DEFAULT_MESSAGE = (
    "create_app was called with no auth hook: this application performs"
    " no authentication or authorization and every request acts with the"
    " full authority of the injected fabric handles. Bind auth=, or pass"
    " acknowledge_insecure_default=True to accept this posture"
    " explicitly (D-IMPL-73)."
)

_LOGGER = logging.getLogger("ccf_runtime.http_api")

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
    deps: ApiDependencies,
    *,
    auth: HttpAuthProtocol | None = None,
    authorizer: TenantAuthorizerProtocol | None = None,
    acknowledge_insecure_default: bool = False,
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
        authorizer: Optional HARD-04 tenant authorizer (D-IMPL-68; 10-03).
            When provided *and* the request carries a verified
            ``TokenGrant`` (i.e. ``auth`` is also bound — D-06), the two
            HITL routes enforce per-tenant authorization inside their
            handlers with the door-declared action IDs, refusing a deny
            with the typed 403 ``ERROR_TENANT_UNAUTHORIZED`` body.
            When ``None`` — the default — the HITL routes are
            byte-identical to the unauthorized-posture routes.
        acknowledge_insecure_default: Explicit acceptance of the
            unauthenticated posture (D-IMPL-73). When ``auth`` is
            ``None`` and this is ``False`` — the default — the SDK
            emits a :class:`CcfInsecureDefaultWarning` at construction
            and one logging WARNING at the first served request. This
            kwarg is the single suppression surface: no environment
            variable is consulted, so the acceptance is greppable in
            the caller's code. Irrelevant once ``auth`` is bound.

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

    if auth is None and not acknowledge_insecure_default:
        # D-IMPL-73 emission point 1: construction-time warning aimed at
        # the caller (stacklevel=2 points at the create_app call site).
        warnings.warn(
            CcfInsecureDefaultWarning(_INSECURE_DEFAULT_MESSAGE),
            stacklevel=2,
        )

        # D-IMPL-73 emission point 2: once-only logging WARNING at the
        # first served request, covering the operator loop. Same message
        # as the construction warning (the ruling's consistency
        # consequence). The flag is per-app, so each unacknowledged app
        # logs exactly once.
        logged = False

        @app.middleware("http")
        async def _log_insecure_default_once(
            request: Request,
            call_next: Callable[[Request], Awaitable[Response]],
        ) -> Response:
            nonlocal logged
            if not logged:
                logged = True
                _LOGGER.warning(_INSECURE_DEFAULT_MESSAGE)
            return await call_next(request)

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
        hitl.build_router(deps, authorizer=authorizer),
        prefix="/hitl",
        dependencies=guarded,
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
