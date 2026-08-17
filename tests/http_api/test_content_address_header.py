"""A zero-CCF consumer can verify what it received, in one stdlib line.

``D-IMPL-126`` item (4) (Dave, 2026-08-13). ``canonical_response``'s docstring
has always claimed that *"a consumer that hashes what it received gets the
address the producer would"* — and that claim was true and **unverifiable from
outside**: checking it required already owning a CCF canonicalizer, which is
precisely what a consumer reaching for an HTTP door does not have. The address
now travels on the response, so the check is
``hashlib.sha256(response.content).hexdigest() == response.headers[HEADER]``
and needs nothing but the standard library.

**Every assertion here is over the wire, on raw bytes.** ``response.content``
and never the parsed-JSON view: re-serializing the parsed body would compare the
header against *a* serialization rather than against the bytes that actually
crossed the connection, which is the one thing this test exists to pin. Key
order, separator whitespace and unicode escaping are all part of what is
hashed.

=========================================  ===================================
Claim                                      What would fail here
=========================================  ===================================
the header is present and correct          the header would be absent, or set
                                           from a second serialization that
                                           disagreed with the body
it is the **fabric's** address              the header would be a digest of
                                           some bytes rather than the
                                           `D-IMPL-26` content address the
                                           ArtifactStore and replay pin against
it is not only the product door            a per-route implementation would
                                           leave four of the five call sites
                                           unheadered
refusals carry no header                   middleware stamping every response
                                           would pass every assertion above
                                           while making the header meaningless

Tenant, principal, class and role names are test deployment vocabulary.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.contracts.canonical import content_hash
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
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import CONTENT_ADDRESS_HEADER
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

from http_api.conftest import Fabric, call

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "content-address-token"
PRINCIPAL = "content-address-caller"
ROLE = "content-address-role"
SCOPE = "product"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 13, tzinfo=UTC)


def _resolver(
    *, grant: TokenGrant, tenant: str, requested_role: str | None
) -> Perspective:
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


def _app(fabric: Fabric, tmp_path: Path) -> Any:
    from ccf_runtime.http_api.auth import BearerTokenAuth

    token_file = tmp_path / "content-address-tokens.json"
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
    return create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
        product_entitlement=ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: AUDIT_INSTANT
        ),
        perspective_resolver=_resolver,
    )


def _get(app: Any, url: str) -> Any:
    return call(
        app, "GET", url, headers={"Authorization": f"Bearer {TOKEN}"}
    )


def _product_url(fabric: Fabric) -> str:
    address = fabric.product_address
    return f"/product/{address.tenant}/{address.product_class}/{address.version}"


# --- (1) the byte-level identity, over the wire -----------------------------


def test_sha256_of_the_product_body_equals_the_header(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The whole point, asserted exactly as a zero-CCF consumer would.

    ``response.content`` is the raw bytes off the connection. A test that
    hashed a re-serialization of the *parsed* body would be asserting something
    about its own serializer rather than about what crossed the connection.
    """
    response = _get(_app(fabric, tmp_path), _product_url(fabric))

    assert response.status_code == 200
    header = response.headers[CONTENT_ADDRESS_HEADER]
    assert hashlib.sha256(response.content).hexdigest() == header


def test_the_header_is_the_fabrics_own_content_address(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Pinned to :func:`~ccf.contracts.canonical.content_hash`, not to a digest.

    Without this the header could be ``sha256`` of *some* bytes and every
    assertion above would still pass. This is what makes it the ``D-IMPL-26``
    address the ArtifactStore resolves and replay pins against — computed
    in-process, from the fabric's own serialization, and compared to what the
    door published.
    """
    response = _get(_app(fabric, tmp_path), _product_url(fabric))

    assert (
        response.headers[CONTENT_ADDRESS_HEADER]
        == content_hash(fabric.product_servable.product)
    )


# --- (2) not one route — the shared helper ----------------------------------


def test_a_non_product_canonical_route_carries_it_too(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The header lives in ``canonical_response``, so all five sites have it.

    A per-route implementation would leave four of the five unheadered, and a
    test that only drove the product door would never say so. ``GET /config``
    is a different router reaching the same helper.
    """
    app = _app(fabric, tmp_path)

    response = _get(
        app,
        "/config/resolution"
        f"?key={fabric.auto_agent_key}&version={fabric.auto_agent_version}",
    )

    assert response.status_code == 200
    assert (
        hashlib.sha256(response.content).hexdigest()
        == response.headers[CONTENT_ADDRESS_HEADER]
    )


# --- (3) the negative control -----------------------------------------------


def test_a_refusal_carries_no_content_address(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Without this, middleware stamping every response would pass the suite.

    A refusal is not a content-addressed artifact — nothing resolves it from
    the ArtifactStore and nothing pins it in replay — so publishing an address
    for one would make the header mean "here is a digest" rather than "here is
    this object's identity".
    """
    app = _app(fabric, tmp_path)
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}",
    )

    assert response.status_code >= 400
    assert CONTENT_ADDRESS_HEADER not in response.headers


# --- (4) the ETag ruling is recorded where it was made ----------------------


def test_the_etag_alternative_is_ruled_against_in_writing() -> None:
    """The rejection lives in the docstring, and no header is set under it."""
    import inspect

    import ccf_runtime.http_api.routes as routes

    doc = routes.canonical_response.__doc__
    assert doc is not None
    assert "ETag" in doc

    source = inspect.getsource(routes)
    # Prose only: the string never reaches a header mapping.
    assert '"ETag"' not in source
    assert "'ETag'" not in source
