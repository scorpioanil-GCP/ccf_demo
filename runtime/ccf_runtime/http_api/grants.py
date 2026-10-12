# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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
actor. The join-time shim ``tenant_from_request`` is gone: every route reads
its tenant from the capability and nothing reads a tenant off a grant.

**The one other thing a handler may hold is the gate's deny, and only where its
route declared it answers one** (R5-CP17-F01; Dave 2026-10-11 21:19 MST, "Do
(a)"). On a route declaring
:attr:`~ccf_runtime.authz.route_declaration.RouteAuthorization.answers_denial`,
the gate hands the authorizer's deny to the route as a :class:`GateDenial`
instead of refusing ``403`` itself, and mints nothing. :func:`denial_from_request`
is how the handler reads it. A deny grants nothing: the handler holding one
holds no capability, reaches no handle, and can only record and answer the
refusal — so the reader checks the type and the route's declaration and nothing
more, because a fabricated deny can only make a handler refuse.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, cast, overload

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

__all__ = [
    "GateDenial",
    "absent",
    "authorized_from_request",
    "denial_from_request",
    "grant_from_request",
    "within_tenant",
]

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


@dataclass(frozen=True, kw_only=True)
class GateDenial:
    """The authorizer's deny, handed by the gate to a route that answers its own.

    **SDK-defined** (CLAUDE.md §8.3, §11). Finding R5-CP17-F01; Dave, 2026-10-11
    21:19 MST, verbatim *"Do (a)"*, carried from the MCP door to this one: an
    entitled caller asking for a product class the scope mapping names nowhere
    was refused ``403`` by the gate, while an unentitled caller asking for a real
    class got the governed ``404`` refusal — a status-level answer to *"does
    this class exist?"*. On a route declaring
    :attr:`~ccf_runtime.authz.route_declaration.RouteAuthorization.answers_denial`
    the gate parks this on ``request.state.scope_denial`` instead of refusing,
    and the route records it through
    :func:`~ccf_runtime.authz.delivery_boundary.govern_scope_denial` — the same
    recorder and emission site as an entitlement denial.

    It is a deny, never a grant: the gate minted no capability for the request,
    and nothing here can be exchanged for one.

    Attributes:
        grant: The verified grant the gate decided about — the principal the
            refusal is recorded and disclosed for.
        tenant: The tenant the gate selected from the grant and decided under.
        statement: The deny's internal truth — action, resource, tenant and the
            authorizer's decision id. It lands on the replay record only; what
            crosses the wire is what Disclosure decides for the principal.
    """

    grant: TokenGrant
    tenant: str
    statement: str


def denial_from_request(request: Request) -> GateDenial | None:
    """The gate's deny for this request, or ``None`` when the gate allowed it.

    R5-CP17-F01. Read only by a route that declared
    :attr:`~ccf_runtime.authz.route_declaration.RouteAuthorization.answers_denial`;
    ``None`` is the gate's allow, after which the handler reads its capability
    with :func:`authorized_from_request` exactly as before.

    Raises:
        HTTPException: 403 with :data:`~ccf_runtime.http_api.errors
            .ERROR_NO_CAPABILITY` when something is stashed that is not a
            :class:`GateDenial`, or when a deny is stashed for a route that did
            not declare it answers one. Both are fail-closed: the handler acts
            on nothing.
    """
    found: object = getattr(request.state, "scope_denial", None)
    if found is None:
        return None
    if not isinstance(found, GateDenial) or not isinstance(found.grant, TokenGrant):
        raise _no_capability("the stashed deny is not the gate's GateDenial")
    declaration = route_authorization(request.scope.get("endpoint"))
    if declaration is None or not declaration.answers_denial:
        raise _no_capability(
            "a deny was handed to a route that does not declare it answers one"
        )
    return found


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


def authorized_from_request(request: Request, *, kind: type[A]) -> Authorized[A]:
    """The capability the gate minted for this request — verified, or refuse.

    Args:
        request: The live request. The capability is read from
            ``request.state.authorized``; the route's declared action is read
            from the endpoint the router resolved (``scope["endpoint"]``).
        kind: The kind this handler performs — REQUIRED. The capability must be
            of exactly that kind (by identity) and the return is typed to it, so
            every handle call after this line is held by ``mypy --strict``
            (§1.4). There is no kind-less form: a tenant-scoped governed read
            is not callable without naming its operation (pre-merge check,
            2026-09-25, residual R6 closed by construction), and the route's
            declared action is enforced as well.

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
    if claimed_kind is not kind:
        raise _no_capability(
            f"the handler performs {kind.__name__} and the capability is for"
            f" {claimed_kind.__name__}"
        )
    return cast(Authorized[A], found)


def within_tenant(*, tenant: str, key: str) -> bool:
    """Whether ``key`` is under ``tenant`` — the first segment of the Control Plane grammar.

    The read routes apply this with the CAPABILITY's tenant (panel F-READ-01..04
    at the D-IMPL-353 join): a list shows the capability's tenant's keys and no
    other tenant's, and a keyed read of another tenant's key reads as absent.
    A key with no segment belongs to nobody and is never within a tenant.
    """
    segment, separator, _ = key.partition("/")
    return bool(separator) and segment == tenant


def absent(key: str, version: str) -> HTTPException:
    """The 404 an absent registration gets, spelled once.

    A key under another tenant is refused with THIS response, byte-identical to
    the one a key that does not exist gets, so a read door is not an existence
    oracle across tenants (the same reasoning as ``WorkflowTenantMismatchError``
    → 404). The phrase is the registry's own
    (:class:`~ccf.controlplane.registry.ControlPlaneMissing`), and the door's
    test holds the two bodies equal.
    """
    return HTTPException(
        status_code=404,
        detail=f"no Control Plane artifact registered as ({key!r}, {version!r})",
    )
