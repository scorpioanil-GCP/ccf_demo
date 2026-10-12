# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""On the HTTP product door, an undeclared class reads exactly as an unentitled caller (R5-CP17-F01).

**SDK-defined** (CLAUDE.md §8.3, §11). Finding R5-CP17-F01 was ruled for the
standard MCP door (Dave, 2026-10-11 21:19 MST, verbatim *"Do (a)"*) and its
acceptance (21:44) said: *"Compare the complete public refusal response,
including status and structured fields — not just its message"*, prove the
undeclared-class case reveals no additional existence information while a
declared, entitled class still serves, and keep truthful audit events. The
HTTP door carried the same oracle, recorded as measured and open (fragment
20261011-14; ``packaging/bank-controlled/BANK-PACKET.md`` §5): the gate answered
the scope mapping's deny ``403 request-unauthorized`` while an unentitled caller
asking for a real class got the governed ``404 subject-unavailable`` shell, so
the status code answered *"does this class exist?"*.

Held here over the real application — the real gate, the real authorizer over a
registered scope mapping that names the one class this deployment serves, the
real entitlement source and the SDK's own refusal recorder:

* the permitted case serves: a declared class, an entitled caller, ``200``;
* the unentitled caller (real class) and the entitled caller (a class declared
  nowhere) get one reply — status, the headers a client reads, and the whole
  JSON body — but for the per-answer record reference and the echo of the
  caller's own class;
* the authorizer's deny for the undeclared class is on the audit log, as a deny
  on the resource axis;
* the record behind the undeclared-class reply names why
  (``tenant-unauthorized``), and the wire does not.

Tenant, principal, scope, role and class names are test deployment vocabulary.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import httpx
import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeEntry, ScopeMappingArtifact
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.authz.refusals import ACTION_PRODUCT_RETRIEVE
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.mcp.auth import StaticTokenSource, TokenGrant
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)
from tests.composition import declared_erasure_trust, no_erasures

from .conftest import Fabric
from .gate_fixtures import probe

#: Test deployment vocabulary.
ENTITLED = "undeclared-http-entitled"
UNENTITLED = "undeclared-http-unentitled"
TOKEN_ENTITLED = "undeclared-http-token-entitled"
TOKEN_UNENTITLED = "undeclared-http-token-unentitled"
SCOPE = "undeclared-http:product"
ROLE = "undeclared-http-role"
MAPPING_KEY = "undeclared-http/scope-mapping"
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"
INSTANT = datetime(2026, 8, 11, tzinfo=UTC)
ASKED_AT = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)

#: The one header whose value is a function of the body's length and nothing
#: else; the bodies differ by exactly the per-question members, so it is held
#: to the body rather than across the two replies.
_LENGTH_HEADER = "content-length"


def _app(fabric: Fabric, root: Path) -> tuple[Any, ControlPlaneRegistry, Any]:
    """The door, its scope-mapping registry (the audit plane) and its recorder."""
    address = fabric.product_address
    tenant = address.tenant
    tokens = StaticTokenSource(
        grants={
            TOKEN_ENTITLED: TokenGrant(client_id=ENTITLED, scopes=(SCOPE,), tenants=frozenset({tenant})),
            TOKEN_UNENTITLED: TokenGrant(client_id=UNENTITLED, scopes=(SCOPE,), tenants=frozenset({tenant})),
        }
    )
    # The deployment DECLARES the classes its product scope reaches: exactly the
    # one class it serves. A class absent from this list is "declared nowhere".
    mappings = ControlPlaneRegistry()
    version = register_typed_at_composition(
        mappings,
        MAPPING_KEY,
        ScopeMappingArtifact(
            semver="1.0.0",
            scopes={
                SCOPE: ScopeEntry(
                    tenant_patterns=(tenant,),
                    action_ids=(ACTION_PRODUCT_RETRIEVE,),
                    resource_patterns=(address.product_class,),
                )
            },
        ),
        SCOPE_MAPPING,
    )
    assert isinstance(version, str)
    authorizer = ControlPlaneTenantAuthorizer(
        control_plane=mappings,
        scope_mapping_key=MAPPING_KEY,
        scope_mapping_version=version,
        clock=lambda: INSTANT,
    )
    # ENTITLED may receive the class; UNENTITLED holds a valid credential for
    # the same scope and is in no entitlement grant.
    entitlements = ControlPlaneRegistry()
    register_typed_at_composition(
        entitlements,
        product_entitlement_key(tenant_id=tenant),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version="1.0.0",
            principals={
                ENTITLED: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(control_plane=entitlements, clock=lambda: INSTANT)
    recorder = refusal_recorder(
        entitlements,
        store=deployment_store(root / "artifacts", REPLAY_RECORD_CLASS),
        tenant=tenant,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )

    def perspective_resolver(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
        return Perspective(principal_id=grant.client_id, role=requested_role if requested_role is not None else ROLE)

    app = create_app(
        ApiDependencies(
            erasure_index=no_erasures(),
            erasure_trust=declared_erasure_trust(),
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        auth=BearerTokenAuth(token_source=tokens),
        authorizer=authorizer,
        product_entitlement=source,
        perspective_resolver=perspective_resolver,
        refusal_recorder=recorder,
        replay_record_product_class=None,
    )
    return app, mappings, recorder


#: Two shapes of request: the class's standing answer (no question), and a
#: whole §6.3 question with its declared remainder. Both are compared.
_QUESTIONS: dict[str, dict[str, str] | None] = {
    "standing": None,
    "question": {
        "subject": "acct-1",
        "intent": "fixture-intent",
        "freshness": "fixture-freshness",
        "asked_at": ASKED_AT.isoformat(),
        "parameters": json.dumps({}),
    },
}


def _get(app: Any, *, token: str, product_class: str, version: str, tenant: str, query: Mapping[str, str] | None) -> httpx.Response:
    return probe(
        app,
        "GET",
        f"/product/{tenant}/{product_class}/{version}",
        params=dict(query or {}),
        headers={"Authorization": f"Bearer {token}"},
    )


def _public(response: httpx.Response, *, asked_class: str) -> dict[str, Any]:
    """The complete public reply with exactly the per-question members normalized.

    Status, every header but the body's own length, and the whole JSON body.
    Normalized, and nothing else: the record reference (issued per answer) and
    the echo of the caller's OWN class. The class name is replaced only where it
    is that echo; anywhere else it stays, so a door statement naming it differs.
    """

    def scrub(value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {k: scrub(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [scrub(v) for v in value]
        if key in ("replay_reference", "replay_ref"):
            return "<per-answer record>"
        if key == "product_id" and value == asked_class:
            return "<the caller's class>"
        return value

    assert response.headers[_LENGTH_HEADER] == str(len(response.content))
    return {
        "status": response.status_code,
        "headers": sorted((k, v) for k, v in response.headers.items() if k != _LENGTH_HEADER),
        "body": scrub(response.json()),
    }


@pytest.mark.parametrize("shape", sorted(_QUESTIONS))
def test_an_undeclared_class_and_an_unentitled_caller_get_one_reply_over_http(
    fabric: Fabric, tmp_path: Path, shape: str
) -> None:
    address = fabric.product_address
    nowhere = f"{address.product_class}-declared-nowhere"
    query = _QUESTIONS[shape]
    app, mappings, recorder = _app(fabric, tmp_path)
    ask = dict(tenant=address.tenant, version=address.version, query=query)

    permitted = _get(app, token=TOKEN_ENTITLED, product_class=address.product_class, **ask)
    unentitled = _get(app, token=TOKEN_UNENTITLED, product_class=address.product_class, **ask)
    reads_before = len(fabric.resolver_calls)
    undeclared = _get(app, token=TOKEN_ENTITLED, product_class=nowhere, **ask)
    # The deny stays a deny: nothing was read for the undeclared class.
    assert len(fabric.resolver_calls) == reads_before

    # Permitted: a declared class, an entitled caller — served.
    assert permitted.status_code == 200, permitted.text[:400]
    if query is None:
        assert permitted.content == canonical_bytes(fabric.product_servable.product)

    # Refused, both, and indistinguishable: the WHOLE public reply — status,
    # headers, every body member — once the per-question members are normalized.
    assert unentitled.status_code != 200, unentitled.text[:400]
    assert _public(undeclared, asked_class=nowhere) == _public(unentitled, asked_class=address.product_class), (
        undeclared.status_code,
        undeclared.text[:600],
        unentitled.status_code,
        unentitled.text[:600],
    )
    a, b = unentitled.json(), undeclared.json()
    assert a["refusal"]["replay_reference"] != b["refusal"]["replay_reference"]
    assert b["refusal"]["request"]["product_id"] == nowhere, "the echo is the caller's own question"
    stated = {k: v for k, v in b["refusal"].items() if k not in ("replay_reference", "request")}
    assert nowhere not in json.dumps(stated), "the door's statement names the undeclared class"
    assert nowhere not in json.dumps({k: v for k, v in b.items() if k != "refusal"})
    for reason in ("tenant-unauthorized", "request-unauthorized"):
        assert reason not in undeclared.text, f"the internal reason {reason!r} crossed the wire"

    # TRUTHFUL AUDIT (Dave, 21:44: "Keep truthful audit events"): the
    # authorizer's deny for the undeclared class is on the log, as a deny, with
    # the resource axis failing — answered differently, decided the same.
    decisions = [e for e in mappings.audit_events() if isinstance(e, AuthzDecisionAuditEvent)]
    on_nowhere = [e for e in decisions if e.actor == ENTITLED and e.authz_resource == nowhere]
    assert on_nowhere, [(e.actor, e.authz_resource) for e in decisions]
    assert all(not e.resolved and e.authz_failing_axis == "resource" for e in on_nowhere)

    # The internal truth is on the record behind the reply, never on the wire.
    store = recorder.artifact_store
    record = DecisionReplayRecord.model_validate_json(
        store.get(content_address=store.resolve_uri(uri=b["refusal"]["replay_reference"]))
    )
    assert "tenant-unauthorized" in record.content_generation_path.assembly_refusal
    assert nowhere in record.content_generation_path.assembly_refusal, "the record names the class it refused"


# --- the reader fails closed -------------------------------------------------


def _request(*, state: dict[str, Any], endpoint: Any) -> Any:
    from starlette.requests import Request

    return Request({"type": "http", "method": "GET", "path": "/", "headers": [], "state": state, "endpoint": endpoint})


def _declared(*, answers_denial: bool) -> Any:
    from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes

    @authorizes(ACTION_PRODUCT_RETRIEVE, resource=ResourceBinding.path("product_class"), answers_denial=answers_denial)
    def endpoint() -> None:
        return None

    return endpoint


def _deny() -> Any:
    from ccf_runtime.http_api.grants import GateDenial

    return GateDenial(
        grant=TokenGrant(client_id=ENTITLED, scopes=(SCOPE,), tenants=frozenset({"t"})), tenant="t", statement="s"
    )


def test_the_reader_returns_the_deny_only_to_a_route_that_declared_it_answers_one() -> None:
    """``None`` after an allow; the deny on a declaring route; a 403 anywhere else."""
    from fastapi import HTTPException

    from ccf_runtime.http_api.errors import ERROR_NO_CAPABILITY
    from ccf_runtime.http_api.grants import denial_from_request

    deny = _deny()
    assert denial_from_request(_request(state={}, endpoint=_declared(answers_denial=True))) is None
    assert denial_from_request(_request(state={"scope_denial": deny}, endpoint=_declared(answers_denial=True))) is deny

    refused = []
    for state, endpoint in (
        # A deny handed to a route that answers none of its own.
        ({"scope_denial": deny}, _declared(answers_denial=False)),
        # Something stashed that is not the gate's deny.
        ({"scope_denial": {"grant": "forged"}}, _declared(answers_denial=True)),
        # A route with no declaration at all.
        ({"scope_denial": deny}, lambda: None),
    ):
        with pytest.raises(HTTPException) as raised:
            denial_from_request(_request(state=state, endpoint=endpoint))
        refused.append((raised.value.status_code, raised.value.detail["error_code"]))
    assert refused == [(403, ERROR_NO_CAPABILITY)] * 3
