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
