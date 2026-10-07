"""Every mounted route declares an action, and boot refuses if one does not.

``SEC-001``, Task 2. The load-bearing claim is the **order**: the refusal is in
:func:`~ccf_runtime.http_api.app.create_app`, so an application containing an
undeclared route is never returned. The sweep in this file is the *backup* —
it reads the same table — because a construction path that skipped a CI
sweeper would skip the check, whereas nothing can mount a route without
building the application that raises.

Drafted from what would fail here:

==========================================  ==================================
Requirement                                 What would fail here
==========================================  ==================================
boot-time refusal, not a lint               a router with an undeclared route
                                            would build and serve
every mounted route is covered              a route added without
                                            ``@authorizes`` would be gated by
                                            nothing, or by whatever the
                                            unmatched-route branch decides
the enumeration sees included routers       ``app.routes`` alone finds five
                                            routes on this FastAPI and misses
                                            twenty-five behind lazy
                                            ``_IncludedRouter`` objects
action ids come from the vocabulary         a route would invent a string no
                                            scope mapping could name
a PATH resource names a real parameter      the gate would read ``None`` and
                                            deny every request to that route,
                                            silently
the tenant assertion is exercised           no route would carry ``{tenant}``
                                            and the derived assertion would
                                            be dead code nobody noticed
==========================================  ==================================
"""

from __future__ import annotations

from tests.composition import no_erasures
from typing import Any

import pytest
from fastapi import APIRouter

import ccf_runtime.authz.refusals as refusals
from ccf_runtime.authz.route_declaration import (
    TENANT_PATH_PARAM,
    ResourceSource,
    route_authorization,
)
from ccf_runtime.http_api.gate import (
    UndeclaredRouteError,
    build_route_table,
    mounted_routes,
)

from .conftest import Fabric

#: Every action identifier the SDK declares, read off the module.
VOCABULARY = frozenset(getattr(refusals, name) for name in refusals.__all__)


class TestTheSweep:
    def test_every_mounted_route_carries_a_declaration(self, app: Any) -> None:
        undeclared = [
            f"{sorted(getattr(route, 'methods', ()) or ['*'])} {template}"
            for template, route in mounted_routes(app)
            if route_authorization(getattr(route, "endpoint", None)) is None
        ]
        assert undeclared == []

    def test_the_enumeration_finds_more_than_app_routes_does(
        self, app: Any
    ) -> None:
        """The measurement that makes the sweep non-vacuous.

        On this repository's ``fastapi==0.140.0``, ``include_router`` no longer
        copies routes into ``app.routes``: it appends one opaque
        ``_IncludedRouter`` per include. A sweep that read ``app.routes`` would
        find the four generated documentation routes plus ``/health``, declare
        itself green, and never look at a single ruled-noun route.
        """
        shallow = [
            route
            for route in app.routes
            if getattr(route, "endpoint", None) is not None
        ]
        deep = list(mounted_routes(app))

        assert len(shallow) == 5
        assert len(deep) > 20

    def test_the_route_population_is_the_ruled_noun_set(
        self, app: Any
    ) -> None:
        """The roster, not the count (a right count with a wrong member
        audits clean forever)."""
        prefixes = {
            template.split("/")[1] for template, _ in mounted_routes(app)
        }
        assert prefixes == {
            "agent",
            "artifact",
            "backends",
            "config",
            "docs",
            "health",
            "hitl",
            "openapi.json",
            "product",
            "redoc",
            "replay",
            "schema",
            "skill",
            "workflow",
        }

    def test_every_declared_action_is_in_the_vocabulary(
        self, app: Any
    ) -> None:
        """No route invents a string no scope mapping could name (D-02)."""
        declared = {
            route_authorization(route.endpoint).action_id  # type: ignore[union-attr]
            for _template, route in mounted_routes(app)
        }
        assert declared <= VOCABULARY
        assert len(declared) >= 25

    def test_a_path_sourced_resource_names_a_parameter_the_route_has(
        self, app: Any
    ) -> None:
        """Otherwise the gate reads ``None`` and denies every request, quietly.

        ``build_route_table`` refuses such a route at boot; this asserts that
        the shipped set has none, and the sabotage below asserts the refusal
        fires.
        """
        broken = [
            template
            for template, route in mounted_routes(app)
            if (declaration := route_authorization(route.endpoint)) is not None
            and declaration.resource.source is ResourceSource.PATH
            and "{" + declaration.resource.name + "}" not in template
        ]
        assert broken == []

    def test_at_least_one_route_is_tenant_addressed(self, app: Any) -> None:
        """The positive control for the derived tenant assertion.

        The gate holds ``path[tenant]`` to a member of the grant's ``tenants``
        set — and selects it as the acting tenant — for any route whose
        template names the segment. If no route named it, that code would be
        dead and every *"a path segment may never supply the tenant"* claim in
        this remediation would be unexercised.
        """
        carrying = [
            template
            for template, _route in mounted_routes(app)
            if "{" + TENANT_PATH_PARAM + "}" in template
        ]
        assert carrying == ["/product/{tenant}/{product_class}/{version}"]


class TestTheBootRefusal:
    """The gate on the declaration rule is ``create_app`` itself."""

    def test_a_router_with_an_undeclared_route_is_not_built(
        self, fabric: Fabric, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """Live sabotage: mount one undeclared handler and watch boot refuse.

        The sabotage is a *replacement builder*, not an edit to a shipped
        module — nothing on disk is touched — and it adds exactly one route
        carrying no ``@authorizes``, which is precisely the mistake the rule
        exists to catch.
        """
        import ccf_runtime.http_api.app as app_module
        import ccf_runtime.http_api.routes.backends as backends

        def _undeclared(_deps: Any) -> APIRouter:
            router = APIRouter()

            @router.get("", summary="sabotaged: no declaration")
            def forgotten() -> dict[str, str]:
                return {"status": "reachable"}

            return router

        monkeypatch.setattr(backends, "build_router", _undeclared)

        with pytest.raises(UndeclaredRouteError) as refused:
            app_module.create_app(_deps(fabric), **_seams(fabric, tmp_path))

        # The message names the offending route, so an operator fixes the
        # route rather than bisecting the mount order.
        assert "/backends" in str(refused.value)
        assert "@authorizes" in str(refused.value)

    def test_the_control_leg_builds(self, app: Any) -> None:
        """Without it, the sabotage above could be passing for another reason."""
        assert app is not None

    def test_the_table_refuses_a_path_resource_the_template_lacks(
        self,
    ) -> None:
        """The second boot refusal: a declaration that can never resolve."""
        from ccf_runtime.authz.route_declaration import (
            ResourceBinding,
            authorizes,
        )

        router = APIRouter()

        @router.get("/{present}")
        @authorizes(
            refusals.ACTION_SCHEMA_READ,
            resource=ResourceBinding.path("absent"),
        )
        def handler(present: str) -> dict[str, str]:
            return {}

        from fastapi import FastAPI

        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        app.include_router(router, prefix="/thing")

        with pytest.raises(UndeclaredRouteError, match="does not carry"):
            build_route_table(app)


def _deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return ApiDependencies(erasure_index=no_erasures(), 
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
    )


def _seams(fabric: Fabric, root: Any) -> dict[str, Any]:
    from datetime import UTC, datetime

    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    from .gate_fixtures import authority
    from .test_product_declared_obligation_409 import (
        _entitlement_registry,
        _recorder,
    )

    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric),
        clock=lambda: datetime(2026, 8, 11, tzinfo=UTC),
    )
    return authority(
        tenant=fabric.product_address.tenant,
        key="route-declarations/mapping",
        grants={},
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role="declaration-role"
            )
        ),
        refusal_recorder=_recorder(fabric, root, source=source),
    )


class TestTheTableCannotDisagreeWithTheRouter:
    """The gate matches from its own table; the router matches from its own.

    Two matchers over the same templates is a divergence risk: a request the
    gate authorizes as route A and the router serves as route B would be
    authorized under the wrong action. Two things close it, and both are
    asserted rather than argued.
    """

    def test_no_two_routes_can_match_the_same_request_line(
        self, app: Any
    ) -> None:
        """Unambiguous templates make "first match" the *only* match.

        Both matchers scan in mount order and take the first hit, so identical
        templates plus no overlap means neither can pick differently — the
        ordering question stops having a subject. What would fail here: a new
        route overlapping an existing one (``/artifact/index`` beside
        ``/artifact/{content_address}``, say), which is the shape that would
        make mount order load-bearing.
        """
        from ccf_runtime.http_api.gate import build_route_table

        table = build_route_table(app)
        assert len(table) > 20

        overlaps: list[str] = []
        for entry in table:
            concrete = entry.template
            for parameter in entry.parameters:
                concrete = concrete.replace("{" + parameter + "}", "x")
            for other in table:
                if other is entry or not (other.methods & entry.methods):
                    continue
                if other.matcher.match(concrete) is not None:
                    overlaps.append(f"{entry.template} <> {other.template}")
        assert overlaps == []

    def test_the_low_priority_list_is_walked_and_is_empty_here(
        self, app: Any
    ) -> None:
        """A route can live in a second list; measured empty, walked anyway.

        ``fastapi==0.140`` keeps frontend/static mounts in
        ``router._low_priority_routes``, which ``app.routes`` does not
        contain. A route living only there would be invisible to the boot
        refusal — undeclared, absent from the table, and denied at every
        request for a reason nobody could locate.
        """
        assert app.router._low_priority_routes == []

    def test_the_gate_and_the_router_derive_the_same_path(self) -> None:
        """``root_path`` stripping is restated, not imported — so pin it.

        ``starlette.routing`` does not export the helper it uses, and a
        private import would make the gate's matching depend on an internal
        name. The restatement is held equal to Starlette's own here, so a
        change in either goes red rather than silently letting the gate match
        a different string from the one the router matches.
        """
        from starlette.routing import get_route_path

        from ccf_runtime.http_api.gate import _route_path

        cases = [
            {"path": "/product/a/b/c", "root_path": ""},
            {"path": "/api/product/a", "root_path": "/api"},
            {"path": "/api", "root_path": "/api"},
            {"path": "/apifoo/x", "root_path": "/api"},
            {"path": "/product", "root_path": "/other"},
        ]
        for scope in cases:
            assert _route_path(dict(scope)) == get_route_path(dict(scope)), scope
