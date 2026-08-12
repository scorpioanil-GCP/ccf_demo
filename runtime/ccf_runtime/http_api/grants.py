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

from ccf_runtime.http_api.errors import ERROR_INVALID_GRANT, refusal_detail
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = ["grant_from_request"]


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
