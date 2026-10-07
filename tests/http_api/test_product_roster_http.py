"""SEC-017 fix round 1 on the HTTP door: the roster binds product and replay routes.

``D-IMPL-374`` (2), coordinator ruling IMPORTANT 1: the same
:class:`~ccf_runtime.mcp.auth.TokenGrant` backs the HTTP door, so the roster on
:attr:`~ccf_runtime.mcp.auth.TokenGrant.products` binds its product route (the
class is the path's ``product_class``) and its replay routes (the class is the
app's declared ``replay_record_product_class``; none declared and a rostered
caller is refused). IMPORTANT 2: the refusal comes BEFORE the authorizer, so no
``authz_decision`` allow is recorded for it.

=========================================  ===================================
Invariant / finding                        What would fail here
=========================================  ===================================
the product route honors the roster        a rostered bearer receives an
                                           off-roster class over HTTP
the replay routes honor the roster         a rostered bearer reads a replay
                                           record the deployment declared no
                                           class for
no allow for a refused request             the audit trail records an allow
                                           for a request the roster refused
=========================================  ===================================

Tenant, principal, scope and class names are test deployment vocabulary.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf_runtime.mcp.auth import TokenGrant

from .gate_fixtures import CLIENT_ID, SCOPE_EVERYTHING, build_gate_app, grant, probe

TOKEN_ROSTERED = "gate-token-rostered-elsewhere"
ROSTERED = "class-roster-elsewhere"


def _rostered(tenant: str) -> TokenGrant:
    return grant(CLIENT_ID, (SCOPE_EVERYTHING,), (tenant,)).model_copy(
        update={"products": frozenset({ROSTERED})}
    )


@pytest.fixture(scope="module")
def roster_app(fabric: Any, tmp_path_factory: pytest.TempPathFactory) -> Any:
    tenant = str(fabric.product_address.tenant)
    return build_gate_app(
        fabric,
        tmp_path_factory.mktemp("http-roster"),
        extra_grants={TOKEN_ROSTERED: _rostered(tenant)},
    )


def _allows(gate: Any) -> int:
    return sum(
        1
        for event in gate.registry.audit_log.events()
        if getattr(event, "action", None) == "authz_decision"
        and getattr(event, "resolved", None) is True
    )


def _requests(fabric: Any) -> dict[str, tuple[str, dict[str, Any]]]:
    address = fabric.product_address
    return {
        "product": (
            f"/product/{address.tenant}/{address.product_class}/{address.version}",
            {},
        ),
        "replay-decisions": (
            "/replay/decisions",
            {"params": {"content_address": fabric.replay_ref.content_address}},
        ),
        "replay-resolutions": (
            "/replay/resolutions",
            {"params": {"uri": fabric.replay_ref.uri}},
        ),
    }


ROUTES = ("product", "replay-decisions", "replay-resolutions")


@pytest.mark.parametrize("route", ROUTES)
def test_a_rostered_bearer_is_refused_an_off_roster_class_over_http(
    route: str, roster_app: Any, fabric: Any
) -> None:
    url, extra = _requests(fabric)[route]
    before = _allows(roster_app)
    response = probe(roster_app.app, "GET", url, headers=roster_app.auth(TOKEN_ROSTERED), **extra)
    assert response.status_code == 403, (
        f"{route}: a rostered bearer was answered {response.status_code}:"
        f" {response.text[:300]}"
    )
    assert response.json()["detail"]["error_code"] == "product-outside-roster"
    assert _allows(roster_app) == before, "an allow was recorded for a refused request"


@pytest.mark.parametrize("route", ROUTES)
def test_the_same_request_without_a_roster_is_answered(
    route: str, roster_app: Any, fabric: Any
) -> None:
    """The control: the standing tenant-wide bearer, same request — admitted.

    Admitted means the gate's authorizer allowed it and the route ran. The
    product route serves (200); the replay routes reach their own governed
    dereference, whose answer for this fixture's record class is the route's
    business, not the gate's — so for them the evidence is the recorded allow.
    """
    url, extra = _requests(fabric)[route]
    before = _allows(roster_app)
    response = probe(roster_app.app, "GET", url, headers=roster_app.auth(), **extra)
    assert _allows(roster_app) == before + 1, response.text[:300]
    if route == "product":
        assert response.status_code == 200, response.text[:300]
    assert response.status_code != 403, response.text[:300]


# --- the mechanism's edges (written with the fix) ---------------------------


@pytest.fixture(scope="module")
def declared_app(fabric: Any, tmp_path_factory: pytest.TempPathFactory) -> Any:
    tenant = str(fabric.product_address.tenant)
    return build_gate_app(
        fabric,
        tmp_path_factory.mktemp("http-roster-declared"),
        extra_grants={
            TOKEN_ROSTERED: _rostered(tenant),
            "gate-token-rostered-replay": grant(
                CLIENT_ID, (SCOPE_EVERYTHING,), (tenant,)
            ).model_copy(update={"products": frozenset({"class-replay-declared"})}),
        },
        app_options={"replay_record_product_class": "class-replay-declared"},
    )


@pytest.mark.parametrize("route", ("replay-decisions", "replay-resolutions"))
def test_the_replay_routes_follow_the_declared_class(
    route: str, declared_app: Any, fabric: Any
) -> None:
    """Declared and on the roster: admitted. Declared and off it: refused by name."""
    url, extra = _requests(fabric)[route]
    before = _allows(declared_app)
    admitted = probe(
        declared_app.app,
        "GET",
        url,
        headers=declared_app.auth("gate-token-rostered-replay"),
        **extra,
    )
    assert admitted.status_code != 403, admitted.text[:300]
    assert _allows(declared_app) == before + 1
    refused = probe(
        declared_app.app, "GET", url, headers=declared_app.auth(TOKEN_ROSTERED), **extra
    )
    assert refused.status_code == 403
    detail = refused.json()["detail"]
    assert detail["error_code"] == "product-outside-roster"
    assert "class-replay-declared" in detail["message"]
    assert _allows(declared_app) == before + 1


def test_an_on_roster_product_is_served(declared_app: Any, fabric: Any) -> None:
    address = fabric.product_address
    tenant = str(address.tenant)
    token = "gate-token-rostered-on"
    app = build_gate_app(
        fabric,
        __import__("pathlib").Path(
            __import__("tempfile").mkdtemp(prefix="http-roster-on-")
        ),
        extra_grants={
            token: grant(CLIENT_ID, (SCOPE_EVERYTHING,), (tenant,)).model_copy(
                update={"products": frozenset({str(address.product_class)})}
            )
        },
    )
    url, extra = _requests(fabric)["product"]
    response = probe(app.app, "GET", url, headers=app.auth(token), **extra)
    assert response.status_code == 200, response.text[:300]


def test_the_product_and_replay_routes_declare_their_product_class(
    roster_app: Any,
) -> None:
    """One rule, held at the declaration: the routes that know a class say so.

    Read off the gate's own route table for the built application, so a
    product or replay route added without the declaration reddens this.
    """
    from ccf_runtime.authz.route_declaration import ProductClassSource
    from ccf_runtime.http_api.gate import build_route_table

    table = build_route_table(roster_app.app)
    product_routes = [e for e in table if e.template.startswith("/product/")]
    replay_routes = [e for e in table if e.template.startswith("/replay/")]
    assert product_routes and replay_routes
    for entry in product_routes:
        binding = entry.declaration.products
        assert binding is not None, entry.template
        assert binding.source is ProductClassSource.PATH
        assert binding.name == "product_class"
    for entry in replay_routes:
        binding = entry.declaration.products
        assert binding is not None, entry.template
        assert binding.source is ProductClassSource.REPLAY_DECLARED
