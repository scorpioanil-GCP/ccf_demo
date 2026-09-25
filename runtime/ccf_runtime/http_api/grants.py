"""What a handler may hold: the capability the gate minted — once, for every route.

SDK-defined (CLAUDE.md §8.3; D-IMPL-353 §1.4). :class:`~ccf_runtime.http_api
.gate.AuthorizationGate` decides every request before any handler exists and,
on an allow, mints one :class:`~ccf_runtime.authz.capability.Authorized` for
that request's action, tenant, principal and resource, parked on
``request.state.authorized``. :func:`authorized_from_request` is how a
handler picks it up, and it is the **only** thing a handler picks up: the
tenant a door acts under is ``authorized.tenant``, the audited actor is
``authorized.principal``, the target is ``authorized.resource``, and every
handle the door calls takes the capability itself (§1.2).

**The reader verifies; it does not trust the stash.** ``request.state`` is a
dictionary anyone holding the scope can write to, and a handler can be called
outside the gate — by a test, by a future in-process composition. So the read
runs :func:`~ccf_runtime.authz.capability.verify` on what it finds, exactly as
a handle would: the mint by identity, the fields against the minted tuple, and
the kind against **this route's own declared action**, read off the endpoint
the router resolved. An absent, fabricated, retargeted or wrong-action object
is refused 403 with one code, because there is nothing useful for a caller to
learn from which. Reached behind the gate, none of this can fire; it exists so
that a handler reached any other way holds proof or holds nothing.

**Why the route's action, and not only the handler's word.** A handler may
also name the kind it performs (``kind=Register``), which is the static
statement §1.4 wants a handler to make and which ``mypy --strict`` then holds
at every handle call. But a handler's word is a second source, and this
project's rule for second sources is that they may agree and never supply: the
declaration on the endpoint is what the gate minted for, so the reader holds
the capability to it and refuses a handler that names anything else.

:func:`grant_from_request` remains for the handles that still take ``grant=``
(the governed dereference, the entitlement determination, the HITL identity
derivation) until their §1.2 signatures land; it derives no tenant and no
actor. :func:`tenant_from_request` is ``authorized.tenant`` and nothing else,
kept under its old name only for ``routes/hitl.py`` until that door migrates;
it is deleted at join.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Any, TypeVar, cast, overload

from fastapi import HTTPException, Request

from ccf.authz.capability import (
    ActionKind,
    Authorized,
    CapabilityBypassError,
    kind_for_action,
    verify,
)
from ccf_runtime.authz.route_declaration import route_authorization
from ccf_runtime.http_api.errors import (
    ERROR_INVALID_GRANT,
    ERROR_NO_CAPABILITY,
    refusal_detail,
)
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = ["authorized_from_request", "grant_from_request", "tenant_from_request"]

A = TypeVar("A", bound=ActionKind)


def grant_from_request(request: Request) -> TokenGrant | None:
    """The stashed verified grant, or ``None`` when none is stashed.

    For the handles that still take ``grant=`` (§1.2 join items). It derives
    nothing: no tenant, no actor. Those are the capability's.

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


def _no_capability(why: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail=refusal_detail(
            error_code=ERROR_NO_CAPABILITY,
            message=(
                "no genuine capability for this route's action accompanies"
                f" this call ({why}); a handler holds the capability the gate"
                " minted or it holds nothing, and it acts on nothing"
                " (D-IMPL-353 §1.4)"
            ),
        ),
    )


@overload
def authorized_from_request(request: Request) -> Authorized[ActionKind]: ...


@overload
def authorized_from_request(request: Request, *, kind: type[A]) -> Authorized[A]: ...


def authorized_from_request(
    request: Request, *, kind: type[ActionKind] | None = None
) -> Authorized[Any]:
    """The capability the gate minted for this request — verified, or refuse.

    Args:
        request: The live request. The capability is read from
            ``request.state.authorized``; the route's declared action is read
            from the endpoint the router resolved (``scope["endpoint"]``).
        kind: Optionally, the kind this handler performs. When given, the
            capability must be of exactly that kind (by identity) and the
            return is typed to it, so every handle call after this line is
            held by ``mypy --strict`` (§1.4). When omitted the return is typed
            to the marker base; the route's declared action is still enforced.

    Returns:
        The capability, unchanged. Never a copy: the object a handle later
        verifies is the object the gate minted.

    Raises:
        HTTPException: 403 with :data:`~ccf_runtime.http_api.errors
            .ERROR_NO_CAPABILITY` when nothing is stashed, when what is stashed
            is not a genuine unretargeted capability, when its kind is not the
            kind this route's endpoint declares, or when it is not the kind
            the handler named. One code for all four.
    """
    found: object = getattr(request.state, "authorized", None)
    if found is None:
        raise _no_capability("nothing was minted for this request")
    claimed_kind = getattr(found, "kind", None)
    claimed_resource = getattr(found, "resource", None)
    if (
        not isinstance(claimed_kind, type)
        or not issubclass(claimed_kind, ActionKind)
        or not isinstance(claimed_resource, str)
    ):
        raise _no_capability("the object present is not a capability")
    try:
        # The runtime tooth, applied at the reader as a handle applies it: the
        # mint by identity and every field against what was minted (§1.5c, g).
        verify(found, kind=claimed_kind, resource=claimed_resource)
    except CapabilityBypassError as bypass:
        raise _no_capability(str(bypass)) from bypass
    declaration = route_authorization(request.scope.get("endpoint"))
    if declaration is not None:
        # The gate minted for THIS route's declared action. A capability of
        # any other kind arriving here means the gate authorized one route
        # and something is serving another; refuse.
        try:
            expected = kind_for_action(declaration.action_id)
        except CapabilityBypassError as no_kind:
            raise _no_capability(str(no_kind)) from no_kind
        if claimed_kind is not expected:
            raise _no_capability(
                f"the capability is for {claimed_kind.__name__} and this route"
                f" declares {expected.__name__}"
            )
    if kind is not None and claimed_kind is not kind:
        raise _no_capability(
            f"the handler performs {kind.__name__} and the capability is for"
            f" {claimed_kind.__name__}"
        )
    return cast(Authorized[Any], found)


