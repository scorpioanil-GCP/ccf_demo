"""The third exposed product door asks the same question as the other two.

15.5-06. ``GET /product/{tenant}/{product_class}/{version}`` is one of three
places this tree serves a Context Product, and the phase's criterion is *every*
exposed door. This file asserts that this one refuses what the MCP doors
refuse, refuses it with the *same typed constants*, and reaches the same
decision through the same imported code rather than a second reading of what
"entitled" means.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
one definition, three doors                this route would re-declare the
                                           seams or re-implement the order,
                                           and the HTTP door would drift from
                                           the MCP doors one edit at a time
T-15.5-20 (per-class disclosure)           an authenticated caller would
                                           receive a class its grant does not
                                           name
T-15.5-19 (caller-asserted role)           ``?role=`` would be threaded to the
                                           engine without meeting the grant
T-15.5-21 (dead configuration)             entitlement seams could be bound
                                           with no auth hook, enforcing
                                           nothing, with no signal
D-08 (one vocabulary, two renderings)      the refusal would carry free text a
                                           client had to parse
=========================================  ===================================

Tenant, principal, role and class names are test deployment vocabulary.
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api.app import (
    CcfDeadEntitlementWarning,
    CcfInsecureDefaultWarning,
    create_app,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
    ERROR_PRODUCT_DOOR_UNGOVERNED,
    ERROR_PRODUCT_REQUEST_INCOMPLETE,
    ERROR_PRODUCT_ROLE_UNGRANTED,
)
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

from http_api.conftest import Fabric, call

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "product-door-token"
STRANGER_TOKEN = "product-door-stranger-token"
PRINCIPAL = "product-door-caller"
STRANGER = "product-door-stranger"
ROLE = "product-door-role"
UNGRANTED_ROLE = "product-door-role-ungranted"
SCOPE = "product"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)


def _deps(fabric: Fabric) -> ApiDependencies:
    return ApiDependencies(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=fabric.hitl,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
    )


def _resolver(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
    """This deployment's role derivation: the verified subject, declared role."""
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


def _entitled_app(
    fabric: Fabric,
    tmp_path: Path,
    *,
    permitted_classes: frozenset[str] | None = None,
    permitted_roles: frozenset[str] | None = None,
) -> Any:
    """An app whose product door is authenticated *and* entitled."""
    from ccf_runtime.http_api.auth import BearerTokenAuth

    token_file = tmp_path / "product-tokens.json"
    token_file.write_text(
        json.dumps(
            {
                TOKEN: {"client_id": PRINCIPAL, "scopes": [SCOPE]},
                STRANGER_TOKEN: {"client_id": STRANGER, "scopes": [SCOPE]},
            }
        ),
        encoding="utf-8",
    )
    address = fabric.product_address
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version=POLICY_VERSION,
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=(
                        frozenset({address.product_class})
                        if permitted_classes is None
                        else permitted_classes
                    ),
                    permitted_roles=(
                        frozenset({ROLE})
                        if permitted_roles is None
                        else permitted_roles
                    ),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return create_app(
        _deps(fabric),
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
        product_entitlement=ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: AUDIT_INSTANT
        ),
        perspective_resolver=_resolver,
    )


def _get(app: Any, fabric: Fabric, *, token: str, role: str | None = None) -> Any:
    address = fabric.product_address
    url = f"/product/{address.tenant}/{address.product_class}/{address.version}"
    if role is not None:
        url = f"{url}?role={role}"
    return call(app, "GET", url, headers={"Authorization": f"Bearer {token}"})


# --- one definition, three doors -------------------------------------------


def test_the_route_imports_the_seams_rather_than_re_declaring_them() -> None:
    """Three doors, one reading of "entitled" — asserted, not reviewed.

    What would fail here: this module growing its own
    ``PerspectiveResolverProtocol`` or its own check order. The two would
    agree on the day they were written and diverge on the first edit, and the
    HTTP door is the one an operator is most likely to reach first.
    """
    import ccf_runtime.http_api.routes.product as route

    source = inspect.getsource(route)
    assert "from ccf_runtime.authz.product_entitlement import" in source
    assert "entitled_perspective" in source
    # Nothing is re-declared here: the Protocols are imported names, never
    # class statements in this module.
    assert "class PerspectiveResolverProtocol" not in source
    assert "class ProductEntitlementSourceProtocol" not in source
    # And the order itself is not re-implemented — the two raising checks are
    # reached through the shared function, never called here.
    assert "require_schema" not in source
    assert "require_role" not in source


# --- the refusals ----------------------------------------------------------


def test_an_entitled_caller_is_served(fabric: Fabric, tmp_path: Path) -> None:
    """The happy path, so every refusal below refuses something real.

    The canonical-bytes assertion moved here from the ungoverned
    retrieval test in ``test_routes.py`` when D-IMPL-108 made that posture
    refuse: the claim *this route serves the fabric's own product, byte for
    byte* is still worth making, and the governed configuration is now the
    only place it can be made.
    """
    app = _entitled_app(fabric, tmp_path)

    response = _get(app, fabric, token=TOKEN)

    assert response.status_code == 200
    assert response.content == canonical_bytes(
        fabric.product_servable.product
    )


def test_an_absent_product_is_a_404_behind_the_governed_door(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Absence is still absence — moved here with the happy path above.

    What would fail here: a door whose new governance turned every miss into a
    503, which would make an unregistered lane indistinguishable from an
    unconfigured deployment. The perspective refusal and the product refusal
    are different facts and stay different status codes.
    """
    app = _entitled_app(fabric, tmp_path)
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/9.9.9",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 404


def test_the_door_forwards_the_perspective_it_authorized(
    fabric: Fabric, tmp_path: Path
) -> None:
    """DI-15.5-03, closed — asserted on the VALUE, not on the parameter.

    A test that only checked the resolver *has* a ``perspective`` parameter
    would pass against a door that forwarded a freshly-constructed one, which
    is precisely the state this plan exists to end. So this observes what the
    resolver actually received and compares it against what
    ``_resolver`` — this deployment's perspective seam — returned for the same
    grant.

    What would fail here: a door that re-derived the perspective after the
    entitlement decided, or forwarded one belonging to a different principal,
    or served the product before the decision ran.
    """
    app = _entitled_app(fabric, tmp_path)
    before = len(fabric.resolver_calls)

    response = _get(app, fabric, token=TOKEN, role=ROLE)

    assert response.status_code == 200
    forwarded, _request = fabric.resolver_calls[before]
    assert forwarded == Perspective(principal_id=PRINCIPAL, role=ROLE)


def test_a_refused_caller_reaches_no_resolver_at_all(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The refusal leg, stated as an absence of forwarding.

    The companion to the test above: forwarding the authorized perspective is
    only a security property if an *unauthorized* caller never reaches the
    seam. What would fail here: a door that resolved first and decided after.
    """
    app = _entitled_app(fabric, tmp_path)
    before = len(fabric.resolver_calls)

    response = _get(app, fabric, token=STRANGER_TOKEN)

    assert response.status_code == 403
    assert len(fabric.resolver_calls) == before


def test_the_request_axes_are_assembled_at_the_door(
    fabric: Fabric, tmp_path: Path
) -> None:
    """D-IMPL-98's request surface, validated where it crosses the door.

    The four §6.3 axes arrive as query parameters — the whitepaper's own
    ``?intent=…&freshness=…`` shape — and the door assembles them into a typed
    :class:`~ccf.products.request.ProductRequest` whose ``schema_name`` and
    ``schema_version`` come from the **path it resolved**, never from the
    caller. What would fail here: a request reaching the resolver addressed to
    a class other than the one being served, which this arrangement makes
    unrepresentable rather than merely refused.
    """
    app = _entitled_app(fabric, tmp_path)
    address = fabric.product_address
    before = len(fabric.resolver_calls)

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}"
        f"?subject=acme-bank%2Fcounterparty%2Fnorthwind"
        f"&intent=credit-review&freshness=intraday"
        f"&asked_at=2026-03-01T00%3A00%3A00%2B00%3A00",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 200
    _perspective, asked = fabric.resolver_calls[before]
    assert asked is not None
    assert asked.schema_name == address.product_class
    assert asked.schema_version == address.version
    assert asked.subject == "acme-bank/counterparty/northwind"
    assert asked.intent == "credit-review"
    assert asked.freshness == "intraday"
    assert asked.asked_at == datetime(2026, 3, 1, tzinfo=UTC)
    assert asked.parameters == {}


def test_a_partial_request_address_is_refused(
    fabric: Fabric, tmp_path: Path
) -> None:
    """A defaulted axis is a question nobody asked, answered anyway.

    What would fail here: the door filling in the three axes a caller omitted,
    which would put a literal back where D-IMPL-98 removed one.
    """
    app = _entitled_app(fabric, tmp_path)
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}"
        f"?intent=credit-review",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]["error_code"]
        == ERROR_PRODUCT_REQUEST_INCOMPLETE
    )


def test_a_caller_that_asks_nothing_forwards_no_request(
    fabric: Fabric, tmp_path: Path
) -> None:
    """``None`` is the honest absence, never a manufactured question."""
    app = _entitled_app(fabric, tmp_path)
    before = len(fabric.resolver_calls)

    assert _get(app, fabric, token=TOKEN).status_code == 200

    _perspective, asked = fabric.resolver_calls[before]
    assert asked is None


def test_an_undeclared_principal_is_refused_with_a_typed_code(
    fabric: Fabric, tmp_path: Path
) -> None:
    """A real token is not a grant: authentication is not entitlement."""
    app = _entitled_app(fabric, tmp_path)

    response = _get(app, fabric, token=STRANGER_TOKEN)

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == ERROR_PRINCIPAL_NOT_ENTITLED


def test_an_unentitled_class_is_refused_with_a_typed_code(
    fabric: Fabric, tmp_path: Path
) -> None:
    """T-15.5-20 on the HTTP door, with the same constant the MCP doors carry."""
    app = _entitled_app(
        fabric,
        tmp_path,
        permitted_classes=frozenset(
            {f"{fabric.product_address.product_class}-not-this-one"}
        ),
    )

    response = _get(app, fabric, token=TOKEN)

    assert response.status_code == 403
    body = response.json()["detail"]
    assert body["error_code"] == ERROR_PRODUCT_CLASS_UNENTITLED
    assert fabric.product_address.product_class in body["message"]


def test_an_ungranted_requested_role_is_refused_with_a_typed_code(
    fabric: Fabric, tmp_path: Path
) -> None:
    """T-15.5-19: ``?role=`` is a request, and asking is not receiving."""
    app = _entitled_app(fabric, tmp_path)

    response = _get(app, fabric, token=TOKEN, role=UNGRANTED_ROLE)

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == ERROR_PRODUCT_ROLE_UNGRANTED


def test_a_granted_requested_role_is_served(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The mirror case: without it, a door that refused every role would pass.

    A refusal test alone is satisfied by a door that refuses everything, which
    is a different defect wearing the same green tick.
    """
    app = _entitled_app(fabric, tmp_path)

    response = _get(app, fabric, token=TOKEN, role=ROLE)

    assert response.status_code == 200


def test_the_refusal_body_is_the_one_shape_and_never_free_text(
    fabric: Fabric, tmp_path: Path
) -> None:
    """D-08: the code is the contract, the prose is human context."""
    app = _entitled_app(fabric, tmp_path)

    body = _get(app, fabric, token=STRANGER_TOKEN).json()["detail"]

    assert sorted(body) == ["error_code", "message"]
    assert isinstance(body["error_code"], str)
    assert isinstance(body["message"], str)


# --- the dead configurations -----------------------------------------------


def test_entitlement_without_an_auth_hook_warns_loudly(
    fabric: Fabric, tmp_path: Path
) -> None:
    """T-15.5-21: intent to gate plus zero enforcement must not be silent.

    What would fail here: the seams accepted with no auth hook and no signal.
    The deployment then serves every class to every caller while believing it
    is gated — the WR-05 failure, on a wider surface.
    """
    with pytest.warns(CcfDeadEntitlementWarning):
        with pytest.warns(CcfInsecureDefaultWarning):
            create_app(
                _deps(fabric),
                product_entitlement=ControlPlaneProductEntitlementSource(
                    control_plane=ControlPlaneRegistry(),
                    clock=lambda: AUDIT_INSTANT,
                ),
                perspective_resolver=_resolver,
            )


def test_half_a_governance_pair_is_refused_at_build_time(
    fabric: Fabric,
) -> None:
    """An entitlement with nothing to decide about is not a configuration.

    What would fail here: one seam accepted alone, producing a door that looks
    governed in the composition root and enforces half a decision — or none.
    """
    import ccf_runtime.http_api.routes.product as route

    with pytest.raises(ValueError, match="together"):
        route.build_router(_deps(fabric), perspective_resolver=_resolver)

    with pytest.raises(ValueError, match="together"):
        route.build_router(
            _deps(fabric),
            entitlement_source=ControlPlaneProductEntitlementSource(
                control_plane=ControlPlaneRegistry(),
                clock=lambda: AUDIT_INSTANT,
            ),
        )


def test_the_unbound_posture_no_longer_serves_and_says_which_seam_is_missing(
    fabric: Fabric,
) -> None:
    """The T-07-24 preservation is **superseded by D-IMPL-108**, deliberately.

    This test previously asserted 200: with no seams bound, ``GET /product``
    served a gate-admitted product to anyone who asked, on the reasoning that
    the acknowledged insecure posture (D-IMPL-73) is a supported one and a
    required seam would make it unbuildable. That reasoning still holds for
    ``create_app`` — the app builds, and every other noun answers exactly as
    it did — but it no longer reaches the product door, because the resolver
    seam now requires the authorized
    :class:`~ccf.projection.plan.Perspective`.

    The trade is stated plainly rather than smuggled: the ungoverned posture
    gives up **one route**, and gains the property that no product this fabric
    serves over HTTP was ever shaped under a perspective nobody named. The
    optional-here / required-on-MCP split survives at the level it was about —
    ``create_app`` still accepts no seams and still builds.

    What would fail here: a default sneaking back onto the perspective
    argument, or the route quietly reverting to serving without one.
    """
    app = create_app(_deps(fabric), acknowledge_insecure_default=True)
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}",
    )

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["error_code"] == ERROR_PRODUCT_DOOR_UNGOVERNED
    # The prose names the seam to bind — an operator reading a refusal should
    # not have to read the source to learn what to configure (D-08's shape).
    assert "product_entitlement=" in body["message"]
