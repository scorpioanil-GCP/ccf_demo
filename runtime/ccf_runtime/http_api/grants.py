"""Reading the verified grant off a request, failing closed — once, for every route.

SDK-defined (CLAUDE.md §8.3). When :func:`~ccf_runtime.http_api.app.create_app`
binds an auth hook, the verified
:class:`~ccf_runtime.mcp.auth.TokenGrant` is stashed on
``request.state.token_grant``. Every route composition that authorizes on
identity has to read it back, and every one of them has to fail closed on a
near-miss — an object that is not the verified type must never fall through to
an authorization path or to a principal derivation (the Codex fail-closed
finding, 07-REVIEWS round 2).

That was one helper inside ``routes/hitl.py`` while exactly one router needed
it. The product route needs it too, so it lives here rather than being typed a
second time: two doors reading the same stash with two readings of "not a
``TokenGrant``" is the drift ``run_gates``/``run_federated_gates`` share their
comparison functions specifically to prevent, and the copy that drifted would
be the one nobody was watching.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from ccf_runtime.authz.tenancy import UntenantedGrantRefused, tenant_of_grant
from ccf_runtime.http_api.errors import (
    ERROR_INVALID_GRANT,
    ERROR_UNTENANTED_GRANT,
    refusal_detail,
)
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = ["grant_from_request", "tenant_from_request"]


def grant_from_request(request: Request) -> TokenGrant | None:
    """The stashed verified grant, or ``None`` when no auth hook is bound.

    Raises:
        HTTPException: 403 with :data:`~ccf_runtime.http_api.errors
            .ERROR_INVALID_GRANT` when something *is* stashed but is not a
            :class:`~ccf_runtime.mcp.auth.TokenGrant`. Refusing beats falling
            back to the caller-supplied identity, which is the only other
            thing a door could do with an object it cannot trust.
    """
    grant = getattr(request.state, "token_grant", None)
    if grant is not None and not isinstance(grant, TokenGrant):
        raise HTTPException(
            status_code=403,
            detail=refusal_detail(
                error_code=ERROR_INVALID_GRANT,
                message=(
                    "the stashed grant object is not a TokenGrant; the door"
                    " refuses rather than fall back to the caller-supplied"
                    " identity"
                ),
            ),
        )
    return grant


def tenant_from_request(request: Request) -> str:
    """The tenant this request acts under — the verified grant's, only.

    ``SEC-002``. Every route that used to take a tenant from a path segment, a
    query parameter or a request body reads it here instead, so there is one
    source in the tree and a handler cannot accidentally acquire a second by
    adding a parameter.

    Structurally, this cannot refuse behind the gate: no request reaches a
    handler without :class:`~ccf_runtime.http_api.gate.AuthorizationGate`
    having stashed a grant whose tenant it already read. The refusal exists
    for the handler called directly — in a test, or by a future in-process
    composition — where failing closed beats returning a tenant nobody
    verified.

    Raises:
        HTTPException: 403 carrying
            :data:`~ccf_runtime.http_api.errors.ERROR_INVALID_GRANT` when no
            verified grant is stashed, or
            :data:`~ccf_runtime.http_api.errors.ERROR_UNTENANTED_GRANT` when
            the stashed grant names no tenant.
    """
    grant = grant_from_request(request)
    if grant is None:
        raise HTTPException(
            status_code=403,
            detail=refusal_detail(
                error_code=ERROR_INVALID_GRANT,
                message=(
                    "no verified grant accompanies this call, so there is no"
                    " tenant to act under; the tenant is never read from the"
                    " path, the query string or the body (SEC-002)"
                ),
            ),
        )
    try:
        return tenant_of_grant(grant)
    except UntenantedGrantRefused as untenanted:
        raise HTTPException(
            status_code=403,
            detail=refusal_detail(
                error_code=ERROR_UNTENANTED_GRANT, message=str(untenanted)
            ),
        ) from untenanted
