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
the door echoes the question it was        a door that published nothing, or
asked, and the echo is the *whole*         published a projection of the
question (`C-09`)                          question, or published something a
                                           consumer could have reconstructed
                                           from its own state

**The third sibling joins here rather than displacing anything** (``C-09``).
``D-IMPL-126``'s ruling — *"each surface publishes the same sibling values
through whatever channel it actually has"* — is applied, not amended: this door
keeps its body as the vessel and gains a header, where the envelope-carrying
doors carry the same value inside the envelope. Every assertion above still
holds, and the ones below re-confirm the single-serialization property at the
point a third header was added, because a third header is exactly the kind of
edit that could have quietly introduced a second rendering of the body.

**Coverage limit, stated rather than implied.** There is no HTTP client
adapter, so the echo is verified **producer-side only** here. Nothing in this
module — or anywhere in this phase — claims client-side coverage on this
transport.

Tenant, principal, class and role names are test deployment vocabulary.
"""

from __future__ import annotations

import base64
import hashlib
import json
from tests.composition import declared_erasure_trust, no_erasures
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

from ccf.contracts.canonical import content_hash
from ccf.products.door import WireRequest
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
from ccf_runtime.http_api.routes import (
    CONTENT_ADDRESS_HEADER,
    REQUEST_ECHO_HEADER,
)
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

# One definition of how a governed HTTP door's refusal recorder is
# built, imported rather than copied (`24.6-09`).
from tests.http_api.test_product_declared_obligation_409 import _recorder

from http_api.conftest import Fabric, call
from http_api.composition_authority import (
    register_typed_at_composition,
)

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "content-address-token"
PRINCIPAL = "content-address-caller"
ROLE = "content-address-role"
SCOPE = "product"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 13, tzinfo=UTC)

#: The four §6.3 axes this module's echo legs ask with, plus the declared
#: remainder. Test deployment vocabulary; the SDK ships none of it.
SUBJECT = "content-address-subject"
INTENT = "content-address-intent"
FRESHNESS = "content-address-freshness"
BOUNDARY = datetime(2026, 3, 1, tzinfo=UTC)

#: One level of declared nesting (``D-IMPL-103``) — the shape a lossy wire
#: mangles first, which is why the round trip is asserted over it rather than
#: over a flat mapping that a string-valued transport would carry by accident.
PARAMETERS: dict[str, Any] = {
    "minimum_score": 11,
    "region": {"code": "north", "reviewed": True},
}


from .gate_fixtures import (  # noqa: E402
    SCOPE_EVERYTHING,
    wide_authorizer,
)


def _resolver(
    *, grant: TokenGrant, tenant: str, requested_role: str | None
) -> Perspective:
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


def _app(fabric: Fabric, tmp_path: Path) -> Any:
    from ccf_runtime.http_api.auth import BearerTokenAuth

    # The REAL dev token file, `tenants` included, read through the REAL
    # `FileTokenSource` (D-IMPL-353 §2 P1). This file used to be written and
    # then ignored in favour of a test-only grant subclass.
    token_file = tmp_path / "content-address-tokens.json"
    token_file.write_text(
        json.dumps(
            {
                TOKEN: {
                    "client_id": PRINCIPAL,
                    "scopes": [SCOPE_EVERYTHING],
                    "tenants": [fabric.product_address.tenant],
                }
            }
        ),
        encoding="utf-8",
    )
    address = fabric.product_address
    registry = ControlPlaneRegistry()
    register_typed_at_composition(registry, 
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
        ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        # `SEC-001`/`SEC-002`: every app binds an authorizer, and the
        # tenant is the credential's. This module's subject is elsewhere,
        # so the mapping is registered wide and visibly so.
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
        authorizer=wide_authorizer(
            tenant=fabric.product_address.tenant, key="content-address/mapping"
        ),
        product_entitlement=source,
        perspective_resolver=_resolver,
        # `24.6-09` / `D-IMPL-256` (2): an entitling door that cannot record a
        # denial is not built. This module only ever serves, so the recorder is
        # bound and never fires — one keyword, and nothing else here moves.
        refusal_recorder=_recorder(fabric, tmp_path, source=source),
        replay_record_product_class=None,
    )


def _get(app: Any, url: str) -> Any:
    return call(
        app, "GET", url, headers={"Authorization": f"Bearer {TOKEN}"}
    )


def _product_url(fabric: Fabric) -> str:
    address = fabric.product_address
    return f"/product/{address.tenant}/{address.product_class}/{address.version}"


def _asking_url(fabric: Fabric) -> str:
    """The same product URL, with a question on it — all four axes plus the
    class-declared remainder, which is what makes the echo non-empty."""
    return (
        f"{_product_url(fabric)}"
        f"?subject={quote(SUBJECT)}&intent={quote(INTENT)}"
        f"&freshness={quote(FRESHNESS)}"
        f"&asked_at={quote(BOUNDARY.isoformat())}"
        f"&parameters={quote(json.dumps(PARAMETERS))}"
    )


def _the_question(fabric: Fabric) -> WireRequest:
    """What the caller sent, built here from the caller's own values.

    Deliberately **not** read back off the response: a comparison against a
    value derived from the answer would be the object-compared-with-itself
    vacuity this whole phase exists to remove, one document over.
    """
    return WireRequest(
        product_id=fabric.product_address.product_class,
        parameters=PARAMETERS,
        temporal_boundary=BOUNDARY,
    )


# --- (5) the question comes back, and it is the whole question (C-09) --------


def assert_echoes_the_question(response: Any, *, sent: WireRequest) -> None:
    """The echo header decodes to exactly the question that was asked.

    A function over its subject rather than an inline assertion, so the control
    below can hand *this same function* a divergent question and observe it
    fail (``D-22``). A control implemented as a copy of the assertion proves
    only that the copy behaves like the copy.

    Total equality, never a projection (``C-03``): a comparison that checked
    only ``product_id`` would pass against a door that echoed the right class
    and the wrong question, which is precisely the crossing the echo exists to
    detect.
    """
    encoded = response.headers[REQUEST_ECHO_HEADER]
    echoed = WireRequest.model_validate_json(
        base64.urlsafe_b64decode(encoded.encode("ascii"))
    )
    assert echoed == sent


def test_the_door_publishes_the_question_it_was_asked(
    fabric: Fabric, tmp_path: Path
) -> None:
    """``C-09`` on the transport that has no envelope, only headers.

    The third sibling, carrying the same value the envelope-carrying doors now
    carry inside the envelope. Every field of it originates **producer-side**,
    from the query axes the route itself parsed — which is the property a
    future HTTP adapter depends on, and the reason a decoded header is not the
    same fact as the request the adapter happens to be holding.

    The content address is re-asserted in the same breath: adding a third
    header is exactly the edit that could have introduced a second rendering
    of the body, and the whole value of the address is that it cannot.
    """
    response = _get(_app(fabric, tmp_path), _asking_url(fabric))

    assert response.status_code == 200
    assert_echoes_the_question(response, sent=_the_question(fabric))
    assert (
        hashlib.sha256(response.content).hexdigest()
        == response.headers[CONTENT_ADDRESS_HEADER]
    )


def test_the_echo_comparison_fails_against_a_different_question(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The named sabotage control (``CLNT-12``, ``D-22``) for the leg above.

    Without this, ``assert_echoes_the_question`` would be satisfied by *any*
    well-formed header — including one a door stamped from a question nobody
    asked. The divergence is one parameter value, deliberately: a control that
    changed the product class would pass against a comparison that only
    checked the class, and would therefore not prove that the comparison is
    total.
    """
    response = _get(_app(fabric, tmp_path), _asking_url(fabric))
    crossed = _the_question(fabric).model_copy(
        update={"parameters": {**PARAMETERS, "minimum_score": 12}}
    )

    with pytest.raises(AssertionError):
        assert_echoes_the_question(response, sent=crossed)


# --- (6) a question that cannot be represented is refused, not half-served --


def _asking_url_with(fabric: Fabric, *, boundary: str, parameters: str) -> str:
    """The asking URL with either axis substituted, so the two refusal legs
    and their shared control differ in exactly one place each."""
    return (
        f"{_product_url(fabric)}"
        f"?subject={quote(SUBJECT)}&intent={quote(INTENT)}"
        f"&freshness={quote(FRESHNESS)}"
        f"&asked_at={quote(boundary)}&parameters={quote(parameters)}"
    )


def test_a_parameter_that_cannot_cross_the_wire_is_refused_by_name(
    fabric: Fabric, tmp_path: Path
) -> None:
    """A ``400`` naming the spelling that works — never a 500, never a 200.

    Measured before this leg existed: this door forwarded ``{"x": 1.5}``
    verbatim and served ``200``, while the MCP tool refuses the same value at
    :class:`~ccf.products.door.WireRequest` construction. The two doors
    disagreed on a class of value the shared width table in
    ``tests/mcp/test_egress_parameters.py`` happens not to contain, so nothing
    was red.

    Publishing no header for a question that cannot be represented was not an
    option — a sibling that silently disappears for some questions is the
    pattern ``C-10`` names — so the door refuses, and this door narrows to
    match the other rather than the other widening to match it.
    """
    response = _get(
        _app(fabric, tmp_path),
        _asking_url_with(
            fabric,
            boundary=BOUNDARY.isoformat(),
            parameters=json.dumps({"minimum_score": 1.5}),
        ),
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "product-parameters-malformed"
    # The guard's own message, carried rather than paraphrased: a caller told
    # only "malformed" would have to guess what to send instead.
    assert "does not survive the wire unchanged" in detail["message"]


def test_a_naive_asked_at_is_refused_rather_than_answered(
    fabric: Fabric, tmp_path: Path
) -> None:
    """``D-IMPL-38`` on this door, which until now was the door it was false of.

    :class:`~ccf.products.door.WireRequest`'s temporal guard states in terms
    that *"both product doors refuse a naive ``asked_at`` by name"*. Measured
    against the tree before this change: this one served ``200``. The instant a
    question is asked as-of is the boundary a replay resolves against, and a
    boundary whose offset is the host's local configuration replays differently
    on a different host — so the door refuses rather than filling the offset
    in, which is exactly what ``product-request-incomplete`` already records
    about a partially-supplied axis.
    """
    response = _get(
        _app(fabric, tmp_path),
        _asking_url_with(
            fabric,
            boundary="2026-03-01T00:00:00",
            parameters=json.dumps(PARAMETERS),
        ),
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "product-request-incomplete"
    assert "carries no UTC offset" in detail["message"]


def test_the_representable_form_of_both_still_serves(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The shared vacuity guard for the two refusals above.

    Without it, both would pass against a door that refused every question it
    was asked — which is a door that publishes no echo at all, and therefore
    passes a refusal leg for precisely the reason the phase exists to catch.
    One representable spelling of each refused value, served.
    """
    response = _get(
        _app(fabric, tmp_path),
        _asking_url_with(
            fabric,
            boundary=BOUNDARY.isoformat(),
            parameters=json.dumps({"minimum_score": 11}),
        ),
    )

    assert response.status_code == 200
    assert REQUEST_ECHO_HEADER in response.headers


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
