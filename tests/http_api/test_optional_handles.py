"""A deployment that exposes one noun does not have to wire eight handles.

``D-IMPL-126`` item (3) (Dave, 2026-08-13). The spike measured a first-time
adopter serving a single Context Product over HTTP and finding that
:class:`~ccf_runtime.http_api.dependencies.ApiDependencies` required a workflow
factory, a workflow engine, a HITL transport, a skill catalog and a grant
ledger before ``GET /product/...`` would answer — five handles for routes that
deployment never intends to expose. Fabricating five stubs to serve one noun is
a papercut that sends a reader into SDK source, and it is closed **before** the
Hello World examples are written so that no example teaches the workaround.

**What this module asserts, and what would fail here.**

=========================================  ===================================
Claim                                      What would fail here
=========================================  ===================================
three handles construct                    the dataclass would still demand
                                           eight and raise ``TypeError``
a three-handle bundle *serves*             a bundle that constructs but 500s
                                           on every route would pass a
                                           construction-only test; this one
                                           compares the served **body bytes**
                                           against the eight-handle fixture
an unwired route refuses, typed            an absent handle would surface as
                                           ``AttributeError`` on ``None`` and
                                           an opaque 500 with a stack trace
the eight-handle bundle is unchanged       the narrowing would have altered
                                           behaviour for every existing
                                           deployment
the docstring names the routes             a reader would still have to read
                                           three route modules to learn which
                                           handle gates what

**The posture change is deliberate and is not free.** Before this, a deployment
that forgot a handle failed at *boot* with a ``TypeError``; after it, the
failure moves to *first call* as a typed 503. What keeps the diagnostic from
being lost is that the 503 names the absent field and the exact ``create_app``
argument to supply — the ``ERROR_PRODUCT_DOOR_UNGOVERNED`` voice. That tradeoff
is asserted here rather than described: the 503 body is checked for the field
name.

Tenant, principal, class and role names are test deployment vocabulary.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

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
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import ERROR_ROUTE_HANDLE_ABSENT
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

# The recorder builder, imported rather than copied: one definition of *how a
# door's refusal recorder is built* across every governed HTTP door in the
# suite (`24.6-09`).
from tests.http_api.test_product_declared_obligation_409 import _recorder

from http_api.conftest import Fabric, call

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "optional-handles-token"
PRINCIPAL = "optional-handles-caller"
ROLE = "optional-handles-role"
SCOPE = "product"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 13, tzinfo=UTC)
TENANT = "optional-handles-tenant"
EXECUTION_ID = "optional-handles-execution"

#: The three handles a product-only deployment genuinely has. Measured against
#: the consumer table in ``16-22-PLAN.md``: ``control_plane`` is read by four
#: routers, ``artifact_store`` by two and ``product_resolver`` by one, and no
#: useful app omits any of them.
REQUIRED_FIELDS = ("control_plane", "artifact_store", "product_resolver")

#: The five that default to ``None``. ``None`` is the positive assertion *this
#: deployment exposes no such route*, not an omission.
OPTIONAL_FIELDS = (
    "workflow_factory",
    "workflow_engine",
    "hitl_transport",
    "skill_catalog",
    "grant_ledger",
)

#: Each of the eight fields against the router module that consumes it. This
#: replaces a ``grep -c "route"`` over the docstring, which already returns 7 at
#: HEAD and would prove almost nothing.
FIELD_TO_ROUTER = {
    "control_plane": ("agent", "config", "skill", "workflow"),
    "artifact_store": ("replay", "artifact"),
    "product_resolver": ("product",),
    "workflow_factory": ("workflow",),
    "workflow_engine": ("workflow",),
    "hitl_transport": ("hitl",),
    "skill_catalog": ("skill",),
    "grant_ledger": ("skill",),
}


def _full_deps(fabric: Fabric) -> ApiDependencies:
    """The eight-handle bundle every existing deployment constructs."""
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


def _partial_deps(fabric: Fabric) -> ApiDependencies:
    """The three-handle bundle a product-only deployment can now construct."""
    return ApiDependencies(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
    )


from .gate_fixtures import (  # noqa: E402
    SCOPE_EVERYTHING,
    tenanted_source,
    wide_authorizer,
)


def _resolver(
    *, grant: TokenGrant, tenant: str, requested_role: str | None
) -> Perspective:
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


def _app(fabric: Fabric, tmp_path: Path, deps: ApiDependencies) -> Any:
    """A governed app over whichever bundle it is handed.

    The *same* builder for both bundles, deliberately: a comparison between two
    apps built two ways would prove nothing about the bundle.
    """
    from ccf_runtime.http_api.auth import BearerTokenAuth

    tmp_path.mkdir(parents=True, exist_ok=True)
    token_file = tmp_path / "optional-handles-tokens.json"
    token_file.write_text(
        json.dumps({TOKEN: {"client_id": PRINCIPAL, "scopes": [SCOPE]}}),
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
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )
    return create_app(
        deps,
        # `SEC-001`/`SEC-002`: every app binds an authorizer, and the
        # tenant is the credential's. This module's subject is elsewhere,
        # so the mapping is registered wide and visibly so.
        auth=BearerTokenAuth(
            token_source=tenanted_source(
                {TOKEN: (PRINCIPAL, (SCOPE_EVERYTHING,))},
                tenant=fabric.product_address.tenant,
            )
        ),
        authorizer=wide_authorizer(
            tenant=fabric.product_address.tenant, key="optional-handles/mapping"
        ),
        product_entitlement=source,
        perspective_resolver=_resolver,
        # `24.6-09` / `D-IMPL-256` (2): from this wave an entitling door that
        # cannot record a denial is not built. This module only ever serves, so
        # the recorder is bound and never fires — one keyword, and nothing else
        # here moves.
        refusal_recorder=_recorder(fabric, tmp_path, source=source),
    )


def _authorized(app: Any, method: str, url: str, **kwargs: Any) -> Any:
    return call(
        app,
        method,
        url,
        headers={"Authorization": f"Bearer {TOKEN}"},
        **kwargs,
    )


def _product_url(fabric: Fabric) -> str:
    address = fabric.product_address
    return f"/product/{address.tenant}/{address.product_class}/{address.version}"


#: One route per affected family, with the body each needs. Driven from a table
#: so a family that gained a handle but no narrowing cannot be forgotten.
UNWIRED_ROUTES = (
    (
        "workflow_factory",
        "POST",
        "/workflow/invocations",
        {
            "definition_key": "absent",
            "definition_version": "1.0.0",
            "execution_id": EXECUTION_ID,
        },
    ),
    ("skill_catalog", "GET", "/skill/catalog", None),
    ("hitl_transport", "GET", f"/hitl/queue?tenant={TENANT}", None),
)


# --- (1) the bundle constructs ----------------------------------------------


def test_three_handles_construct_without_a_type_error() -> None:
    """The signature claim, proved on the signature alone.

    ``None`` here proves the *signature*, never the behaviour — the behaviour
    claim is the byte-comparison below, which is why both exist.
    """
    bundle = ApiDependencies(
        control_plane=None,  # type: ignore[arg-type]
        artifact_store=None,  # type: ignore[arg-type]
        product_resolver=None,  # type: ignore[arg-type]
    )
    for field in OPTIONAL_FIELDS:
        assert getattr(bundle, field) is None


# --- (2) it serves — the non-vacuity assertion ------------------------------


def test_a_three_handle_bundle_serves_the_same_product_bytes(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Same status, same **body bytes**, from three handles as from eight.

    A test that only checked construction would pass against a bundle that
    500s on every route, which is exactly the regression this is aimed at.
    Bytes rather than parsed JSON, because the product door serves canonical
    bytes and a re-serialization comparison would hide a difference.
    """
    url = _product_url(fabric)

    full = _authorized(_app(fabric, tmp_path / "full", _full_deps(fabric)), "GET", url)
    partial = _authorized(
        _app(fabric, tmp_path / "partial", _partial_deps(fabric)), "GET", url
    )

    assert full.status_code == 200
    assert partial.status_code == full.status_code
    assert partial.content == full.content


# --- (3) an unwired route refuses, typed ------------------------------------


@pytest.mark.parametrize(
    ("field", "method", "url", "body"),
    UNWIRED_ROUTES,
    ids=[route[0] for route in UNWIRED_ROUTES],
)
def test_an_unwired_route_refuses_with_a_typed_503_naming_its_field(
    fabric: Fabric,
    tmp_path: Path,
    field: str,
    method: str,
    url: str,
    body: dict[str, str] | None,
) -> None:
    """503 and not 500, and the absent field named in the message.

    503 because the fault is the *deployment's*, not the caller's — the
    ``ERROR_PRODUCT_DOOR_UNGOVERNED`` reasoning in
    ``runtime/ccf_runtime/http_api/routes/product.py::build_router``, applied to
    the same class of state. Telling
    a caller they are forbidden would misattribute it.
    """
    app = _app(fabric, tmp_path, _partial_deps(fabric))

    kwargs: dict[str, Any] = {} if body is None else {"json": body}
    response = _authorized(app, method, url, **kwargs)

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error_code"] == ERROR_ROUTE_HANDLE_ABSENT
    assert field in detail["message"]


# --- (4) the eight-handle bundle is unchanged -------------------------------


@pytest.mark.parametrize(
    ("field", "method", "url", "body"),
    UNWIRED_ROUTES,
    ids=[route[0] for route in UNWIRED_ROUTES],
)
def test_a_fully_wired_bundle_reaches_the_route_it_always_reached(
    fabric: Fabric,
    tmp_path: Path,
    field: str,
    method: str,
    url: str,
    body: dict[str, str] | None,
) -> None:
    """The narrowing is transparent when the handle is present.

    The statuses are written into the test rather than inferred from a second
    run: 404 for a workflow definition that is not registered, 200 for the
    catalog read and 200 for the queue view. A narrowing that fired on a bound
    handle would show here as a 503.
    """
    expected = {
        "workflow_factory": 404,
        "skill_catalog": 200,
        "hitl_transport": 200,
    }
    app = _app(fabric, tmp_path, _full_deps(fabric))

    kwargs: dict[str, Any] = {} if body is None else {"json": body}
    response = _authorized(app, method, url, **kwargs)

    assert response.status_code == expected[field]


# --- (5) the docstring earns its keep ---------------------------------------


def test_the_class_docstring_names_every_field_and_the_router_it_gates() -> None:
    """Eight fields, and for each one the router module that consumes it."""
    doc = ApiDependencies.__doc__
    assert doc is not None
    for field, routers in FIELD_TO_ROUTER.items():
        assert field in doc, field
        for router in routers:
            assert router in doc, (field, router)


def test_the_module_docstring_no_longer_claims_every_handle_is_required() -> None:
    """The falsified sentence is gone, and what replaced it is true.

    The module docstring of
    ``runtime/ccf_runtime/http_api/dependencies.py`` claimed *"no default for
    anything (CINV-01): construction requires every handle"*. That sentence became false the moment
    five defaults landed, and a module docstring that contradicts its own
    module is worse than no docstring.
    """
    import ccf_runtime.http_api.dependencies as module

    doc = module.__doc__
    assert doc is not None
    assert "no default for anything" not in doc
    # CINV-01 itself is undisturbed and the docstring should still say why.
    assert "CINV-01" in doc


def test_the_optional_fields_are_exactly_the_five_measured() -> None:
    """Neither more nor fewer defaults than the ruling admits.

    ``control_plane``, ``artifact_store`` and ``product_resolver`` stay
    required: every useful app has them, and defaulting them would move a real
    wiring error from boot to first call for no adopter benefit.
    """
    import dataclasses

    fields = {f.name: f for f in dataclasses.fields(ApiDependencies)}
    assert set(fields) == set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    for name in REQUIRED_FIELDS:
        assert fields[name].default is dataclasses.MISSING, name
    for name in OPTIONAL_FIELDS:
        assert fields[name].default is None, name
