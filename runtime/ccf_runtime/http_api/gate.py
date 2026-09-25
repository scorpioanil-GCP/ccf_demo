"""One total gate in front of the whole application (``SEC-001``/``SEC-002``).

SDK-defined (CLAUDE.md §8.3). Every request that reaches this ASGI
application is authenticated and authorized here, before routing, before body
validation, and before any handler exists — and there is **no path carve-out
of any kind**.

**Why a middleware and not** ``FastAPI(dependencies=[Depends(guard)])``.
Measured on this repository's own ``fastapi==0.140.0`` / ``starlette==1.3.1``
and re-measured by ``tests/http_api/test_total_gate.py`` as an executable
negative control rather than quoted from memory: an app-level dependency ran
on **1 of 7** probe shapes. It did not run for a malformed JSON body (422,
decided by body validation *before* the dependency), for ``GET
/openapi.json`` (200, full API document served), for ``GET /docs`` (200), for
a 404, for a trailing-slash redirect, or for a route mounted after
construction. A middleware in front of the whole app ran on **7 of 7**.

**Why no carve-outs.** A carve-out list is a branch whose condition is the
path, and the path is the caller's — the same shape as *a guard whose
applicability the caller decides*, which this remediation has already found
twice. ``/health``, ``/docs``, ``/openapi.json`` and ``/redoc`` are therefore
gated like everything else: each **declares an action id of its own**
(:mod:`ccf_runtime.authz.refusals`) and the deployment's versioned scope
mapping decides. The operational consequence is real and is stated rather
than discovered — a liveness probe carries a credential — and the grant that
opens it is one visible line in an artifact rather than an invisible branch in
SDK code.

**The boot-time refusal is the gate; the sweep test is the backup**
(:func:`build_route_table`). A route mounted without a declaration cannot be
reached, because an application containing one is never built. A CI sweep that
walked the routes afterwards would be skippable by any construction path that
did not run the sweeper, which is the same class of hole one level up.

**What the caller can decide, exhaustively.** The caller chooses the method,
the path, the query string, the headers and the body. Every one of those
choices leads to the check running: an unmatched request line denies, an
unreadable resource denies, a grant with no tenant denies, a grant spanning
several tenants on a route that names none denies, and a tenant segment
naming a tenant the grant does not hold denies. There is no value a caller
can send, omit or malform that makes the gate not run, and no value a caller
supplies that the gate compares *against itself* — the tenant is **selected
from the grant's set** (:mod:`ccf_runtime.authz.tenancy`; D-IMPL-353 §1.3)
and the patterns come from a registered artifact.

**The gate MINTS** (D-IMPL-353 §1.1). After the authorizer returns *allowed*
— and only then — the gate calls :func:`~ccf_runtime.authz.capability.mint`
for the route's declared action, the selected tenant, the verified principal,
the resolved resource and the id of the allow's own audit event, and parks
the result on ``request.state.authorized``. That capability is the only thing
a handler can hold (:func:`~ccf_runtime.http_api.grants.authorized_from_request`)
and the only thing a handle will accept (§1.2). On every refusal the gate mints
nothing, so a handler that runs holds proof, and a handler that holds no proof
did not run behind this gate. This is one of the two mint sites in the tree;
the other is the MCP ``TenantGuardedServer`` wrapper.

**An action no kind exists for cannot be mounted.** :func:`build_route_table`
resolves every declared action id to its capability kind at boot and refuses
the application otherwise, so the gate can never reach an allow it has no kind
to mint.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
import re
from collections.abc import (
    Awaitable,
    Callable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import parse_qs

from starlette.responses import JSONResponse

from ccf.authz.capability import (
    CapabilityBypassError,
    kind_for_action,
    mint,
)
from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
from ccf_runtime.authz.route_declaration import (
    TENANT_PATH_PARAM,
    ResourceSource,
    RouteAuthorization,
    composed_fields,
    route_authorization,
)
from ccf_runtime.authz.tenancy import (
    AmbiguousTenantRefused,
    TenantNotGrantedRefused,
    UntenantedGrantRefused,
    acting_tenant,
    tenants_of_grant,
)
from ccf_runtime.http_api.auth import HttpAuthProtocol
from ccf_runtime.http_api.errors import (
    ERROR_AMBIGUOUS_TENANT,
    ERROR_DECISION_UNMINTABLE,
    ERROR_INVALID_GRANT,
    ERROR_REQUEST_UNAUTHORIZED,
    ERROR_UNAUTHENTICATED,
    ERROR_UNTENANTED_GRANT,
    refusal_detail,
)
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "AuthorizationGate",
    "RouteEntry",
    "UndeclaredRouteError",
    "build_route_table",
    "mounted_routes",
]

_Scope = MutableMapping[str, Any]
_Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
_Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
_ASGIApp = Callable[[_Scope, _Receive, _Send], Awaitable[None]]


def _route_path(scope: _Scope) -> str:
    """The path with ``root_path`` stripped — Starlette's own rule, restated.

    Eight lines rather than an import, because ``starlette.routing`` does not
    export the helper it uses for this and a private import would make the
    gate's matching depend on an internal name. Restating it keeps the gate
    and the router reading the **same** string: a gate that matched a
    differently-derived path from the one the router matches is a gate that
    can authorize one route and serve another.
    """
    path = str(scope.get("path", ""))
    root = str(scope.get("root_path", ""))
    if not root or not path.startswith(root):
        return path
    if path == root:
        return ""
    if path[len(root)] == "/":
        return path[len(root) :]
    return path

#: The one sentence every gate denial carries, whichever of the five internal
#: reasons produced it. Constant so that no branch can make it differ, which
#: is what keeps the denials observationally identical (``D-IMPL-253``
#: amendment 2 (4), applied to the authorization boundary).
_DENIED: Final[str] = (
    "the verified grant does not authorize this request. The decision is made"
    " on (grant, tenant, action, resource) against the deployment's pinned"
    " scope mapping, and the full tuple — including which axis refused — is on"
    " the Control Plane audit log rather than in this response (SEC-001;"
    " SEC-002)"
)

_UNAUTHENTICATED: Final[str] = (
    "the request carries no credential the bound auth hook recognises"
)

#: The hook returned something that is not the verified type. The same
#: fail-closed reading :func:`~ccf_runtime.http_api.grants.grant_from_request`
#: has always had, moved to the earliest point it can be taken: a near-miss
#: object must never reach a tenant read or an authorization call, because the
#: only other thing a gate could do with one is believe its attributes.
_IMPOSTOR: Final[str] = (
    "the bound auth hook returned an object that is not a TokenGrant; the"
    " gate refuses rather than reading a tenant or an identity off something"
    " it cannot trust"
)

#: The bound authorizer said *allowed* and the gate cannot mint from it: the
#: decision names no audit record, or it answers a different (tenant, action,
#: resource) from the one asked (D-IMPL-353 §1.5a). A deployment fault, so a
#: 503 — the SDK's own authorizer cannot produce it.
_UNMINTABLE: Final[str] = (
    "the bound authorizer returned an allow the gate cannot mint a capability"
    " from: it carries no decision id, or it decides about a tenant, action or"
    " resource other than the one this request asked about. No capability is"
    " minted from a partial or misdirected decision; fix the authorizer"
    " (D-IMPL-353 §1.5a)"
)

#: ``{name}`` or ``{name:converter}`` inside a route path template.
_PARAMETER = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-zA-Z_]+))?}")


class UndeclaredRouteError(RuntimeError):
    """A mounted route declares no action id, so the app is not built.

    Raised by :func:`build_route_table` and therefore by
    :func:`~ccf_runtime.http_api.app.create_app`. It names **every** offending
    route rather than the first, because an operator who has just added three
    handlers should fix three, not discover them one build at a time.
    """


@dataclass(frozen=True, kw_only=True)
class RouteEntry:
    """One mounted route, as the gate needs to see it.

    Attributes:
        template: The full mounted path template, prefixes applied —
            ``/product/{tenant}/{product_class}/{version}``.
        methods: The HTTP methods the route answers, upper-cased.
        declaration: What the route declared about authorizing itself.
        matcher: The compiled template. Named-group captures are the path
            parameters; the pattern is anchored at both ends, so a
            trailing-slash variant does **not** match and is denied rather
            than redirected past the gate.
        parameters: The path parameter names the template carries.
    """

    template: str
    methods: frozenset[str]
    declaration: RouteAuthorization
    matcher: re.Pattern[str]
    parameters: frozenset[str]


def _compile(template: str) -> tuple[re.Pattern[str], frozenset[str]]:
    """Compile one path template into an anchored regex and its parameters.

    Two convertors are recognised, matching Starlette's defaults for the
    templates this API actually mounts: the unnamed default, which spans one
    segment, and ``path``, which spans several. An unknown convertor is
    compiled as the single-segment default — the **narrower** reading, so an
    unrecognised spelling can only ever match less than the router does and
    therefore only ever denies more.
    """
    parameters: list[str] = []
    pattern: list[str] = []
    index = 0
    for found in _PARAMETER.finditer(template):
        pattern.append(re.escape(template[index : found.start()]))
        name, convertor = found.group(1), found.group(2)
        parameters.append(name)
        span = ".+" if convertor == "path" else "[^/]+"
        pattern.append(f"(?P<{name}>{span})")
        index = found.end()
    pattern.append(re.escape(template[index:]))
    return re.compile("^" + "".join(pattern) + "$"), frozenset(parameters)


def mounted_routes(app: object) -> Iterator[tuple[str, object]]:
    """Every route actually mounted on ``app``, with its full path template.

    Walks three shapes so the enumeration does not depend on one FastAPI
    version's internals:

    * a route wrapping an included router (``fastapi>=0.140``'s lazy
      ``_IncludedRouter``, which keeps the original router and the prefix it
      was included under rather than copying routes into ``app.routes``);
    * anything else carrying ``.routes`` — a ``Mount``, a sub-application, or
      an earlier FastAPI's flattened router;
    * a leaf route, which is yielded.

    A router's ``_low_priority_routes`` are walked too where the attribute
    exists. They are a *second* list a route can live in — ``fastapi==0.140``
    puts its frontend/static mount there, and this application uses none — and
    a route living only there would otherwise be invisible to the boot
    refusal: not declared, not in the table, and therefore denied at every
    request for a reason nobody could find. Measured empty on this app; walked
    anyway, because *measured empty today* is not *cannot be non-empty*.

    The first branch is the one that matters for correctness here: on this
    repository's ``fastapi==0.140.0``, ``app.routes`` holds ten opaque
    ``_IncludedRouter`` objects and **not one** of the ruled noun routes, so an
    enumeration that read ``app.routes`` alone would find five routes, declare
    the sweep green, and miss twenty-five.
    """
    yield from _walk(getattr(app, "routes", ()), "")
    router = getattr(app, "router", None)
    if router is not None:
        yield from _walk(getattr(router, "_low_priority_routes", ()), "")


def _walk(routes: Sequence[object], prefix: str) -> Iterator[tuple[str, object]]:
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            child = prefix + str(getattr(context, "prefix", ""))
            yield from _walk(getattr(included, "routes", ()), child)
            yield from _walk(
                getattr(included, "_low_priority_routes", ()), child
            )
            continue
        children = getattr(route, "routes", None)
        if children is not None:
            yield from _walk(children, prefix + str(getattr(route, "path", "")))
            continue
        yield prefix + str(getattr(route, "path", "")), route


def build_route_table(app: object) -> tuple[RouteEntry, ...]:
    """Every mounted route's declaration, or refuse to have an application.

    Args:
        app: The built application, after every router is mounted.

    Returns:
        One :class:`RouteEntry` per mounted route.

    Raises:
        UndeclaredRouteError: one or more mounted routes declare no action id.
            The message names all of them. This is **the** gate on the
            declaration rule: a CI sweep over the source would be a backup,
            because a construction path that skipped the sweeper would skip
            the check, whereas nothing can mount a route without building the
            application that raises here.
    """
    entries: list[RouteEntry] = []
    undeclared: list[str] = []
    for template, route in mounted_routes(app):
        endpoint = getattr(route, "endpoint", None)
        declaration = route_authorization(endpoint)
        methods = frozenset(
            str(method).upper() for method in getattr(route, "methods", ()) or ()
        )
        if declaration is None:
            undeclared.append(f"{sorted(methods) or ['*']} {template}")
            continue
        matcher, parameters = _compile(template)
        try:
            # The gate mints for this action after an allow; an action with
            # no kind is an allow the gate could not mint from, and that is
            # decided here, once, rather than on the first allowed request.
            kind_for_action(declaration.action_id)
        except CapabilityBypassError as no_kind:
            undeclared.append(
                f"{sorted(methods) or ['*']} {template} declares action"
                f" {declaration.action_id!r}, for which no capability kind"
                f" exists: {no_kind}"
            )
            continue
        if (
            declaration.resource.source is ResourceSource.PATH
            and declaration.resource.name not in parameters
        ):
            undeclared.append(
                f"{sorted(methods) or ['*']} {template} declares its resource"
                f" as path parameter {declaration.resource.name!r}, which this"
                " template does not carry"
            )
            continue
        entries.append(
            RouteEntry(
                template=template,
                methods=methods,
                declaration=declaration,
                matcher=matcher,
                parameters=parameters,
            )
        )
    if undeclared:
        listed = "\n  ".join(undeclared)
        raise UndeclaredRouteError(
            "these mounted routes declare no usable authorization, so the"
            " application is not built:\n  "
            f"{listed}\n"
            "Every route declares its action id and its resource at its own"
            " definition, with @authorizes(...) from"
            " ccf_runtime.authz.route_declaration, and every action id names"
            " a capability kind (ccf_runtime.authz.capability). A route with"
            " no usable declaration would be a route the gate could only deny"
            " or only allow, and both of those are decided by whoever forgot"
            " (SEC-001; D-IMPL-353 §1.1)"
        )
    return tuple(entries)


class AuthorizationGate:
    """The one total ASGI gate: authenticate, resolve, authorize, or refuse.

    Installed with ``app.add_middleware(AuthorizationGate, ...)``, which puts
    it outside the router — so it runs for documentation routes, 404s,
    redirects, malformed bodies and routes mounted after construction alike.

    Args:
        app: The downstream ASGI application. Positional, because that is the
            contract ``add_middleware`` calls with.
        auth: The bound authentication hook. **Required**: there is no arm of
            this class in which authentication is skipped.
        authorizer: The bound authorizer. **Required**, for the same reason.
        table: The declarations, built by :func:`build_route_table` from the
            fully-mounted application.
    """

    def __init__(
        self,
        app: _ASGIApp,
        *,
        auth: HttpAuthProtocol,
        authorizer: TenantAuthorizerProtocol,
        table: tuple[RouteEntry, ...],
    ) -> None:
        self._app = app
        self._auth = auth
        self._authorizer = authorizer
        self._table = table

    async def __call__(
        self, scope: _Scope, receive: _Receive, send: _Send
    ) -> None:
        """Gate one connection. Non-HTTP scopes pass through unexamined.

        ``lifespan`` and ``websocket`` scopes carry no request to authorize —
        this application mounts no websocket route, and an application that
        grew one would reach :func:`build_route_table`'s refusal first, since
        a websocket route declares no action id either.
        """
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return
        # Typed ``object`` deliberately. The hook's declared return is
        # ``TokenGrant | None``, but a *deployment's* hook is its own code and
        # may return anything at all — and the one thing a gate must never do
        # with a near-miss is read a tenant or an identity off it. Narrowing
        # here rather than trusting the annotation is the same fail-closed
        # reading :func:`~ccf_runtime.http_api.grants.grant_from_request`
        # already takes one layer down, moved to the earliest point it can be
        # taken.
        grant: object = self._auth.grant_for_request(
            authorization_header=_header(scope, b"authorization")
        )
        if grant is None:
            await _refuse(
                scope, receive, send, 401, ERROR_UNAUTHENTICATED, _UNAUTHENTICATED
            )
            return
        if not isinstance(grant, TokenGrant):
            await _refuse(
                scope, receive, send, 403, ERROR_INVALID_GRANT, _IMPOSTOR
            )
            return
        try:
            tenants = tenants_of_grant(grant)
        except UntenantedGrantRefused as untenanted:
            await _refuse(
                scope,
                receive,
                send,
                403,
                ERROR_UNTENANTED_GRANT,
                str(untenanted),
            )
            return
        matched = self._match(scope)
        if matched is None:
            # No declaration covers this request line. Denying rather than
            # passing through is what makes the table's completeness
            # load-bearing: a route that exists but is unmatchable here is
            # unreachable, which is the direction a disagreement between this
            # matcher and the router has to fail in.
            await _refuse(scope, receive, send, 403, ERROR_REQUEST_UNAUTHORIZED, _DENIED)
            return
        entry, path_parameters = matched
        # The route names a tenant only through its own template (SEC-002):
        # a segment may AGREE with the credential and may never supply a
        # tenant it lacks. The query string and the body are not sources.
        named = (
            path_parameters.get(TENANT_PATH_PARAM)
            if TENANT_PATH_PARAM in entry.parameters
            else None
        )
        try:
            # D-IMPL-353 §1.3: one decision is about one tenant, SELECTED from
            # the grant's set — named and held, or the only one held. Several
            # held and none named is refused; the gate does not pick.
            tenant = acting_tenant(tenants=tenants, named=named)
        except TenantNotGrantedRefused:
            # The constant denial, not its own code: which tenants a
            # credential is near is not a caller's to learn from a refusal.
            await _refuse(
                scope, receive, send, 403, ERROR_REQUEST_UNAUTHORIZED, _DENIED
            )
            return
        except AmbiguousTenantRefused as ambiguous:
            await _refuse(
                scope, receive, send, 403, ERROR_AMBIGUOUS_TENANT, str(ambiguous)
            )
            return
        except UntenantedGrantRefused as untenanted:
            await _refuse(
                scope, receive, send, 403, ERROR_UNTENANTED_GRANT, str(untenanted)
            )
            return
        resource, replay = await self._resource(
            scope, receive, entry=entry, path_parameters=path_parameters
        )
        if resource is None:
            await _refuse(
                scope, replay or receive, send, 403, ERROR_REQUEST_UNAUTHORIZED, _DENIED
            )
            return
        action_id = entry.declaration.action_id
        decision = self._authorizer.authorize(
            grant=grant,
            tenant=tenant,
            action_id=action_id,
            resource=resource,
        )
        if not decision.allowed:
            await _refuse(
                scope, replay or receive, send, 403, ERROR_REQUEST_UNAUTHORIZED, _DENIED
            )
            return
        # §1.5(a): the mint binds the authorizer's WHOLE decision, and the
        # decision must be the answer to the question this gate asked. An
        # allow that names no record, or decides about some other tenant,
        # action or resource, is not minted from — it is a deployment fault.
        if (
            decision.decision_id is None
            or decision.tenant != tenant
            or decision.action_id != action_id
            or decision.resource != resource
        ):
            await _refuse(
                scope, replay or receive, send, 503, ERROR_DECISION_UNMINTABLE, _UNMINTABLE
            )
            return
        # THE mint (§1.1). The kind is the route's declared action's — resolved
        # at boot by `build_route_table`, so this cannot fail on the kind — and
        # every other field is the decision's. Nothing here is the caller's.
        authorized = mint(
            kind_for_action(action_id),
            decision=decision,
            principal=grant.client_id,
            decision_id=decision.decision_id,
        )
        # `request.state` is backed by `scope["state"]`. The capability is
        # what a handler holds (`authorized_from_request`); the verified grant
        # stays stashed beside it for the handles that still take `grant=`
        # until the §1.2 signatures land (a join item, listed by the lane).
        state = scope.setdefault("state", {})
        state["authorized"] = authorized
        state["token_grant"] = grant
        await self._app(scope, replay or receive, send)

    def _match(
        self, scope: _Scope
    ) -> tuple[RouteEntry, dict[str, str]] | None:
        """The declaration covering this request line, or ``None``.

        Method-aware: a path that matches a template whose methods exclude
        this request's is **not** a match, and the request is denied rather
        than reaching the router's 405. What a 405 discloses is that the path
        exists, which is a fact an unauthorized caller has not earned.
        """
        path = _route_path(scope)
        method = str(scope.get("method", "")).upper()
        for entry in self._table:
            found = entry.matcher.match(path)
            if found is None or method not in entry.methods:
                continue
            return entry, found.groupdict()
        return None

    async def _resource(
        self,
        scope: _Scope,
        receive: _Receive,
        *,
        entry: RouteEntry,
        path_parameters: Mapping[str, str],
    ) -> tuple[str | None, _Receive | None]:
        """The resource this request acts on, and the receive to pass on.

        Returns ``(None, ...)`` — a deny — wherever the declared source
        carries nothing usable. Every such case is a caller's choice about
        what to send, and every one of them leads to the check running and
        refusing rather than to the check being skipped.

        The second member is a replay of a body this method had to consume,
        or ``None`` when it consumed none. Only a ``BODY``-sourced route reads
        the body at all, and **which routes those are is the route's own
        declaration**, never anything the caller can influence — so no request
        can choose whether it is buffered.
        """
        binding = entry.declaration.resource
        if binding.source is ResourceSource.ROUTE:
            # A door that acts on no addressable subject is still authorized:
            # its own action id is the resource, so a deployment can say "this
            # scope reaches liveness and nothing else" in the same grammar.
            return entry.declaration.action_id, None
        if binding.source is ResourceSource.PATH:
            return path_parameters.get(binding.name), None
        if binding.source is ResourceSource.QUERY:
            values = parse_qs(
                str(scope.get("query_string", b"").decode("latin-1")),
                keep_blank_values=True,
            ).get(binding.name, [])
            # Exactly one, or deny. Two values would let a caller present one
            # for the gate to authorize and leave the router free to read the
            # other — parameter pollution as a bypass — and refusing closes
            # the divergence rather than betting on which end reads which.
            if len(values) != 1 or not values[0]:
                return None, None
            return values[0], None
        body, replay = await _buffer(receive)
        if body is None:
            return None, replay
        try:
            decoded = json.loads(body)
        except ValueError:
            return None, replay
        if not isinstance(decoded, dict):
            return None, replay
        if binding.source is ResourceSource.BODY_COMPOSED:
            # The resource is spelled from several body fields (the artifact
            # store's "<class>/<name>"). Every named field must be a non-empty
            # string, or the resource cannot be spelled and the deny stands;
            # the template is formatted over exactly the declared names, so a
            # field the declaration did not name cannot reach the resource.
            fields: dict[str, str] = {}
            for name in composed_fields(binding.name):
                part = decoded.get(name)
                if not isinstance(part, str) or not part:
                    return None, replay
                fields[name] = part
            if not fields:
                return None, replay
            return binding.name.format(**fields), replay
        value = decoded.get(binding.name)
        if not isinstance(value, str) or not value:
            return None, replay
        return value, replay


async def _buffer(receive: _Receive) -> tuple[bytes | None, _Receive]:
    """Read the whole request body, and return a receive that replays it.

    Buffering is the price of authorizing on a body field, and the
    ``SEC-002`` door is exactly such a field — the Control Plane key a
    registration overwrites. The cost is bounded by the deployment's own
    server: this reads what the server delivers and adds no limit of its own,
    because a byte ceiling here would be a deployment value living in SDK code
    (CINV-01).
    """
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message.get("type") == "http.disconnect":
            return None, _replaying(None)
        body = message.get("body", b"")
        chunks.append(bytes(body) if body else b"")
        if not message.get("more_body", False):
            break
    buffered = b"".join(chunks)
    return buffered, _replaying(buffered)


def _replaying(body: bytes | None) -> _Receive:
    """A receive channel that yields ``body`` once, then disconnects."""
    delivered = False

    async def receive() -> MutableMapping[str, Any]:
        nonlocal delivered
        if body is None or delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _header(scope: _Scope, name: bytes) -> str | None:
    """One request header by lower-cased name, or ``None``."""
    for key, value in scope.get("headers", ()):
        if bytes(key).lower() == name:
            return bytes(value).decode("latin-1")
    return None


async def _refuse(
    scope: _Scope,
    receive: _Receive,
    send: _Send,
    status: int,
    error_code: str,
    message: str,
) -> None:
    """Emit one refusal in the API's existing typed shape.

    ``{"detail": {"error_code": ..., "message": ...}}`` — the same body
    :func:`~ccf_runtime.http_api.errors.refusal_detail` produces under
    FastAPI's ``HTTPException``, so a client parses a gate refusal exactly as
    it parses every other refusal on this surface.
    """
    response = JSONResponse(
        status_code=status,
        content={
            "detail": refusal_detail(error_code=error_code, message=message)
        },
    )
    await response(scope, receive, send)
