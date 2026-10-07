"""What a door declares about its own authorization, at its own definition.

SDK-defined (CLAUDE.md §8.3; the HARD-04 authorizer seam extended for
``SEC-001``/``SEC-002``). A route declares three facts about itself and
nothing else decides them:

* **which action** it performs — the door-declared identifier
  :mod:`ccf_runtime.authz.refusals` holds the vocabulary of (D-02), and
* **where the resource it acts on comes from** — a request part named at the
  route's own definition, never a part the caller chooses, and
* implicitly, **whether it is tenant-addressed** — derived from the route's
  own path template rather than declared, so there is nothing to forget
  (:data:`TENANT_PATH_PARAM`).

**Why the declaration lives on the endpoint rather than in a table beside the
router.** A table is a second place a route can exist in, and a route absent
from it is a route with no declaration — which is the shape the
boot-time refusal in :mod:`ccf_runtime.http_api.gate` exists to make
impossible. Attaching the declaration to the endpoint callable means the
declaration and the handler are the same edit, and a handler added without one
cannot be mounted at all.

**The resource axis, and what it is for (``SEC-002``).** Before it, the
authorizer decided on ``(grant, tenant, action)``. That decides *who counts as
recognized*, not *what recognition permits*: the finding's stated harm — *any
recognized bearer can rewrite the prompt artifact an underwriting agent runs
on* — merely became *any bearer holding the config-register action can rewrite
it*. Two reviewers called a tenant-only fix a no-op for that reason. With the
resource axis, a scope mapping says which **keys, addresses and classes** an
action reaches, in the same trailing-``*`` grammar
(:func:`~ccf_runtime.authz.artifact.pattern_matches`) the tenant axis already
used, so the two axes read alike in one artifact.

No action identifier, resource name or pattern value appears in this module:
it holds the grammar and the attachment mechanism (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from string import Formatter
from typing import Any, Callable, Final, TypeVar

__ccf_mode__ = "algorithmic"

__all__ = [
    "ROUTE_AUTHORIZATION_ATTRIBUTE",
    "TENANT_PATH_PARAM",
    "ProductClassBinding",
    "ProductClassSource",
    "ResourceBinding",
    "ResourceSource",
    "RouteAuthorization",
    "authorizes",
    "composed_fields",
    "route_authorization",
]

#: The path parameter the SDK addresses a tenant by, wherever a route is
#: tenant-addressed. **Derived, never declared**: the gate holds
#: ``path[TENANT_PATH_PARAM]`` to a member of the verified grant's ``tenants``
#: set for every route whose template names it, and selects that member as the
#: acting tenant (D-IMPL-353 §1.3) — so a tenant-addressed route cannot be
#: mounted having forgotten the assertion; there is no per-route switch to
#: omit.
#:
#: The segment remains part of the product address (it is what a URI *means* on
#: a surface whose MCP siblings address the same three facts); what changed is
#: that it may only **agree** with the verified grant, never supply the value.
TENANT_PATH_PARAM: Final[str] = "tenant"

#: Where :func:`authorizes` parks a declaration on the endpoint it decorates.
#: Named rather than spelled at the two reading sites so a rename is one edit.
ROUTE_AUTHORIZATION_ATTRIBUTE: Final[str] = "__ccf_route_authorization__"


class ResourceSource(Enum):
    """Which part of the request supplies the resource a route acts on.

    Five members; the fourth keeps the axis total and the fifth names a
    resource spelled from more than one body field:

    * :attr:`PATH` — a named path parameter (an artifact's content address, a
      product's class). Present by construction once the route matched.
    * :attr:`QUERY` — a named query parameter (a Control Plane key).
    * :attr:`BODY` — a named top-level field of the JSON request body. The
      ``SEC-002`` case is here: the artifact key a registration rewrites is a
      body field, so a gate that could only read the request line could not
      name the thing being overwritten.
    * :attr:`ROUTE` — the route itself is the subject; the resource is the
      route's own action identifier. A door that acts on no addressable thing
      (liveness, the installed-adapter list, the API's own description) is
      still authorized against a pattern, so the axis has no exempt member and
      a deployment can still say *this scope reaches liveness and nothing
      else*.
    * :attr:`BODY_COMPOSED` — a ``str.format`` template over named top-level
      body fields, for a resource the handle acts on that is spelled from
      several of them: the artifact store's ``"{artifact_class}/{name}"``
      (D-IMPL-353 §1.2 — the store takes class and name from the capability's
      resource, so the gate must decide on exactly that string). The MCP
      wrapper's ``resource_composed`` reading, on the HTTP side. Every field
      the template names must be a non-empty string in the body, or the
      extraction is a deny.

    An extraction that cannot produce a value — an absent query parameter, a
    body that is not a JSON object, a field that is not a string — is a
    **deny**, never a skip. That is the whole discipline: the caller chooses
    what to send, and every choice leads to the check running.
    """

    PATH = "path"
    QUERY = "query"
    BODY = "body"
    ROUTE = "route"
    BODY_COMPOSED = "body-composed"


@dataclass(frozen=True, kw_only=True)
class ResourceBinding:
    """One route's statement of where its resource comes from.

    Attributes:
        source: The request part that carries it.
        name: The parameter or field name within that part; the empty string
            for :attr:`ResourceSource.ROUTE`, which names no part; the
            ``str.format`` template for :attr:`ResourceSource.BODY_COMPOSED`.
    """

    source: ResourceSource
    name: str

    def __post_init__(self) -> None:
        if self.source is ResourceSource.ROUTE:
            if self.name:
                raise ValueError(
                    "a ROUTE-sourced resource names no request part, so it"
                    f" carries no name; got {self.name!r}"
                )
            return
        if self.source is ResourceSource.BODY_COMPOSED:
            if not composed_fields(self.name):
                raise ValueError(
                    "a BODY_COMPOSED resource is a str.format template naming"
                    " at least one top-level body field, each by name; got"
                    f" {self.name!r} — a template naming nothing would let the"
                    " request pick the resource (SEC-002)"
                )
            return
        if not self.name:
            raise ValueError(
                f"a {self.source.value}-sourced resource must name the"
                " parameter or field it is read from: an unnamed source is a"
                " source the request gets to pick"
            )

    @classmethod
    def path(cls, name: str) -> ResourceBinding:
        """The resource is the named path parameter."""
        return cls(source=ResourceSource.PATH, name=name)

    @classmethod
    def query(cls, name: str) -> ResourceBinding:
        """The resource is the named query parameter."""
        return cls(source=ResourceSource.QUERY, name=name)

    @classmethod
    def body(cls, name: str) -> ResourceBinding:
        """The resource is the named top-level JSON body field."""
        return cls(source=ResourceSource.BODY, name=name)

    @classmethod
    def route(cls) -> ResourceBinding:
        """The route itself is the resource; its action id names it."""
        return cls(source=ResourceSource.ROUTE, name="")

    @classmethod
    def body_composed(cls, template: str) -> ResourceBinding:
        """The resource is ``template`` formatted over named top-level body fields."""
        return cls(source=ResourceSource.BODY_COMPOSED, name=template)


class ProductClassSource(Enum):
    """Where a route's Context Product class comes from (``SEC-017``).

    ``D-IMPL-374`` (2), fix round 1: a grant's declared product roster
    (:attr:`~ccf_runtime.mcp.auth.TokenGrant.products`) is held by the gate to
    every route where a class is known at the call, before the authorizer.

    * :attr:`PATH` — a named path parameter (the product route's
      ``product_class``).
    * :attr:`REPLAY_DECLARED` — the class the deployment declared for the
      replay records it serves (``create_app``'s
      ``replay_record_product_class``); none declared and a rostered caller is
      refused, because an undeclared record is on no roster.
    """

    PATH = "path"
    REPLAY_DECLARED = "replay-declared"


@dataclass(frozen=True, kw_only=True)
class ProductClassBinding:
    """One route's statement of which product class a request reaches (``SEC-017``).

    Attributes:
        source: Where the class comes from.
        name: The path parameter for :attr:`ProductClassSource.PATH`; empty for
            :attr:`ProductClassSource.REPLAY_DECLARED`.
    """

    source: ProductClassSource
    name: str = ""

    def __post_init__(self) -> None:
        if (self.source is ProductClassSource.PATH) != bool(self.name):
            raise ValueError(
                "a PATH product class names its path parameter, and only a"
                " PATH product class names one (SEC-017)"
            )

    @classmethod
    def path(cls, name: str) -> ProductClassBinding:
        """The product class is the named path parameter."""
        return cls(source=ProductClassSource.PATH, name=name)

    @classmethod
    def replay_declared(cls) -> ProductClassBinding:
        """The product class is the app's declared ``replay_record_product_class``."""
        return cls(source=ProductClassSource.REPLAY_DECLARED)


def composed_fields(template: str) -> tuple[str, ...]:
    """The body fields a :attr:`ResourceSource.BODY_COMPOSED` template names, in order.

    Empty — the refusal signal — when the template names no field, names a
    positional (``{}``) or indexed (``{0}``) field, reaches into a field
    (``{a.b}``, ``{a[0]}``), or is not a template at all. The gate formats the
    template over exactly these names and nothing else, so a name this
    function does not return is a name the request cannot influence.
    """
    try:
        parsed = tuple(Formatter().parse(template))
    except ValueError:
        return ()
    names: list[str] = []
    for _literal, field_name, _spec, _conversion in parsed:
        if field_name is None:
            continue
        if (
            not field_name
            or not field_name.isidentifier()
        ):
            return ()
        names.append(field_name)
    return tuple(names)


@dataclass(frozen=True, kw_only=True)
class RouteAuthorization:
    """Everything one door declares about authorizing itself.

    Attributes:
        action_id: The door-declared action (D-02), from
            :mod:`ccf_runtime.authz.refusals`.
        resource: Where the thing being acted on comes from.
        products: Which Context Product class a request reaches, where one is
            known at the call (``SEC-017``); ``None`` for a route that knows
            none — the roster is not consulted on it.
    """

    action_id: str
    resource: ResourceBinding
    products: ProductClassBinding | None = None

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError(
                "a route declares a non-empty action id or it declares"
                " nothing; the empty string would authorize under a name no"
                " scope mapping can spell (D-02)"
            )


_Endpoint = TypeVar("_Endpoint", bound=Callable[..., Any])


def authorizes(
    action_id: str,
    *,
    resource: ResourceBinding,
    products: ProductClassBinding | None = None,
) -> Callable[[_Endpoint], _Endpoint]:
    """Declare a handler's action and resource, at the handler.

    Applied **inside** the routing decorator so the declaration travels with
    the endpoint callable the router registers::

        @router.get("/versions", summary="...")
        @authorizes(ACTION_AGENT_VERSIONS, resource=ResourceBinding.query("key"))
        def versions(key: str) -> list[str]: ...

    The decorator returns the endpoint unchanged — it wraps nothing and costs
    nothing per request. What it does is make the absence of a declaration
    detectable at boot, which is where
    :func:`~ccf_runtime.http_api.gate.build_route_table` turns it into a
    refusal to build.

    Args:
        action_id: The door-declared action identifier.
        resource: Where this route's resource is read from.
        products: Which product class a request reaches (``SEC-017``), where
            the route knows one at the call.

    Returns:
        The identity decorator that parks the declaration.
    """
    declaration = RouteAuthorization(
        action_id=action_id, resource=resource, products=products
    )

    def attach(endpoint: _Endpoint) -> _Endpoint:
        setattr(endpoint, ROUTE_AUTHORIZATION_ATTRIBUTE, declaration)
        return endpoint

    return attach


def route_authorization(endpoint: object) -> RouteAuthorization | None:
    """The declaration parked on ``endpoint``, or ``None`` if it carries none.

    ``None`` is never *permitted* anywhere: the one caller
    (:func:`~ccf_runtime.http_api.gate.build_route_table`) refuses to build an
    application containing it. Returning it rather than raising keeps the
    refusal's message at the site that can name every offending route at once,
    instead of stopping at the first.
    """
    found = getattr(endpoint, ROUTE_AUTHORIZATION_ATTRIBUTE, None)
    if isinstance(found, RouteAuthorization):
        return found
    return None
