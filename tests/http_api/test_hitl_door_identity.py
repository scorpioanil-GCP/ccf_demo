"""HITL HTTP door: the approval record is server-attested (D-IMPL-353 §2 P6).

What ``POST /hitl/actions`` used to take was a complete
``HumanPrincipalBinding`` in the body — subject compared with the verified
identity (D-IMPL-67), everything else passed through verbatim. Under P6 the
body is :class:`~ccf.hitl.transport.HitlActionRequest` and the binding is
**minted by the door** from three things the caller does not write:

* the capability's principal (``authorized.principal``) — the subject;
* the verified grant's :class:`~ccf.hitl.principal.AuthenticationClaims` —
  identity provider, method, assurance level, session, verbatim;
* the deployment's injected clock — ``action_time``.

The controls, each §9's shape: a body that still carries any minted field is
a **422** (``extra=forbid`` — unrepresentable, not refused); the recorded
binding's assurance level **equals the token's claim** and a body cannot say
a higher one; a credential that states no authentication is refused typed
and nothing lands; the recorded action names the decision that authorized
it; the queue view reads the capability's tenant only; and the hardened path
still lands the verified subject on replay dimension 2.

Test values are deployment vocabulary chosen by this test-as-deployment,
following the ``tests/http_api/test_auth.py`` precedent. The credentials are
real :class:`~ccf_runtime.mcp.auth.TokenGrant`\\ s through the real
:class:`~ccf_runtime.mcp.auth.StaticTokenSource` — no subclass fakes a shape
production never mints (design §3).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.hitl.principal import AuthenticationClaims
from ccf_runtime.identity_binding import ERROR_AUTHENTICATION_UNATTESTED
from ccf_runtime.mcp.auth import StaticTokenSource, TokenGrant

from .conftest import Fabric, call

#: A syntactically valid lowercase sha256 hex digest (shape only).
_VALID_HASH = "b" * 64

#: The door's injected clock reading — what every minted binding's
#: ``action_time`` must equal, and what no body can set.
_CLOCK_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

_CLIENT_ID = "auditor-1"
_TENANT = "identity-door-tenant"
_SCOPE = "gate:everything"

#: One credential per tenant this suite keeps its tests apart with; the
#: suffix names the assurance level the credential's VERIFIER states (or
#: that it states nothing), which is the whole subject of this file.
_SUFFIXES = ("aal1", "aal3", "unattested", "hardened", "queue")


def _claims(level: str) -> AuthenticationClaims:
    return AuthenticationClaims(
        identity_provider_ref="idp://acme-bank/dev-token-file",
        method="bearer-token",
        assurance_level=level,
        session_ref=f"door-session-{level}",
    )


def _tenant(suffix: str) -> str:
    return f"{_TENANT}-{suffix}"


def _token_for(tenant: str) -> str:
    return f"door-token-{tenant.rsplit('-', 1)[-1]}"


def _grants() -> dict[str, TokenGrant]:
    """Real grants, built per call so a contract that lacks the field fails
    inside the test that needs it rather than at import."""
    levels = {"aal1": "aal1", "aal3": "aal3", "hardened": "aal2", "queue": "aal2"}
    grants = {
        _token_for(_tenant(suffix)): TokenGrant(
            client_id=_CLIENT_ID,
            scopes=(_SCOPE,),
            tenants=frozenset({_tenant(suffix)}),
            authentication=_claims(level),
        )
        for suffix, level in levels.items()
    }
    # The verifier said nothing about how this bearer authenticated.
    grants[_token_for(_tenant("unattested"))] = TokenGrant(
        client_id=_CLIENT_ID,
        scopes=(_SCOPE,),
        tenants=frozenset({_tenant("unattested")}),
    )
    return grants


def _deps(fabric: Fabric, *, transport: Any = None) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return ApiDependencies(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=fabric.hitl if transport is None else transport,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
        clock=lambda: _CLOCK_TIME,
    )


def _seams(fabric: Fabric, root: Path) -> dict[str, Any]:
    """Everything ``create_app`` requires, with this suite's credentials.

    The non-auth seams come from :func:`~http_api.gate_fixtures.authority`;
    the auth seam is overridden with the real ``StaticTokenSource`` over real
    ``TokenGrant``\\ s, because the grants here must carry ``authentication``.
    """
    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )
    from ccf_runtime.http_api.auth import BearerTokenAuth

    from .gate_fixtures import authority
    from .test_product_declared_obligation_409 import (
        _entitlement_registry,
        _recorder,
    )

    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric),
        clock=lambda: datetime(2026, 8, 11, tzinfo=UTC),
    )
    seams = authority(
        tenant=tuple(_tenant(suffix) for suffix in _SUFFIXES),
        key="hitl-door-identity/mapping",
        grants={"unused": (_CLIENT_ID, (_SCOPE,), _tenant("aal1"))},
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role="hitl-door-role"
            )
        ),
        refusal_recorder=_recorder(fabric, root, source=source),
    )
    seams["auth"] = BearerTokenAuth(
        token_source=StaticTokenSource(grants=_grants())
    )
    return seams


def _body(**extra: Any) -> dict[str, Any]:
    """What only the human can state — and, via ``extra``, what they may not."""
    body: dict[str, Any] = {
        "event_key": "door-event-1",
        "action": "approve",
        "product_content_hash": _VALID_HASH,
        "annotation": None,
    }
    body.update(extra)
    return body


def _post(app: Any, tenant: str, body: dict[str, Any]) -> Any:
    return call(
        app,
        "POST",
        "/hitl/actions",
        json=body,
        headers={"Authorization": f"Bearer {_token_for(tenant)}"},
    )


@pytest.fixture(scope="module")
def authed_app(fabric: Fabric, tmp_path_factory: pytest.TempPathFactory) -> Any:
    from ccf_runtime.http_api.app import create_app

    return create_app(
        _deps(fabric), **_seams(fabric, tmp_path_factory.mktemp("hitl-door"))
    )


class TestTheBodyCannotDescribeTheBinding:
    """§9: a body that still tries to send a minted field is a 422."""

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("assurance_level", "aal3"),
            ("subject_id", "someone-else"),
            ("identity_provider_ref", "idp://someone-elses-idp"),
            ("method", "hardware-key"),
            ("session_ref", "a-session-i-made-up"),
            ("action_time", _CLOCK_TIME.isoformat()),
            ("tenant", "TENANT"),
            (
                "principal",
                {
                    "approver": {
                        "subject_id": _CLIENT_ID,
                        "identity_provider_ref": "idp://acme-bank/dev-token-file",
                    },
                    "authentication": {
                        "method": "bearer-token",
                        "assurance_level": "aal3",
                        "session_ref": "s",
                    },
                    "action_time": _CLOCK_TIME.isoformat(),
                    "product_content_hash": _VALID_HASH,
                },
            ),
            ("authentication", {"method": "m", "assurance_level": "aal3", "session_ref": "s"}),
        ],
    )
    def test_a_minted_field_in_the_body_is_a_422_and_nothing_lands(
        self, authed_app: Any, fabric: Fabric, field: str, value: Any
    ) -> None:
        tenant = _tenant("aal1")
        before = len(fabric.hitl.submissions(tenant=tenant))
        response = _post(
            authed_app, tenant, _body(**{field: tenant if value == "TENANT" else value})
        )
        assert response.status_code == 422, response.text
        assert field in response.text  # the refusal names the extra field
        assert len(fabric.hitl.submissions(tenant=tenant)) == before


class TestTheDoorMintsTheBinding:
    def test_subject_claims_and_time_come_from_capability_token_and_clock(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        tenant = _tenant("aal3")
        body = _body()
        response = _post(authed_app, tenant, body)
        assert response.status_code == 200, response.text
        (recorded,) = fabric.hitl.submissions(tenant=tenant)
        principal = recorded.principal
        claims = _grants()[_token_for(tenant)].authentication
        assert claims is not None
        # Subject: the capability's principal (the verified client id).
        assert principal.approver.subject_id == _CLIENT_ID
        # Claims: the TOKEN's, verbatim — none of which the body carried.
        assert principal.approver.identity_provider_ref == claims.identity_provider_ref
        assert principal.authentication.method == claims.method
        assert principal.authentication.assurance_level == "aal3"
        assert principal.authentication.session_ref == claims.session_ref
        for minted in ("assurance_level", "subject_id", "session_ref", "action_time"):
            assert minted not in json.dumps(body)
        # Time: the injected clock, not the wall clock and not the body.
        assert principal.action_time == _CLOCK_TIME
        # The record names the decision that authorized it (§3).
        assert recorded.authorizing_decision_id
        # The receipt carries the RECORDED copy, stamps included.
        receipt = response.json()
        assert receipt["status"] == "submitted"
        assert receipt["submission"]["principal"]["authentication"]["assurance_level"] == "aal3"
        assert receipt["submission"]["authorizing_decision_id"] == recorded.authorizing_decision_id
        assert "tenant" not in receipt["submission"]

    def test_the_assurance_recorded_is_the_tokens_and_a_caller_cannot_raise_it(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        """§9 verbatim: the recorded binding's assurance_level equals the
        TOKEN's claim, not anything the body said — and the body cannot say."""
        tenant = _tenant("aal1")
        assert _post(authed_app, tenant, _body()).status_code == 200
        (recorded,) = fabric.hitl.submissions(tenant=tenant)
        assert recorded.principal.authentication.assurance_level == "aal1"
        # A step-up claim typed into the body is unrepresentable, and the one
        # record under this tenant still says what the verifier said.
        assert _post(authed_app, tenant, _body(assurance_level="aal3")).status_code == 422
        (still,) = fabric.hitl.submissions(tenant=tenant)
        assert still.principal.authentication.assurance_level == "aal1"

    def test_an_unattested_credential_is_refused_typed_and_nothing_lands(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        tenant = _tenant("unattested")
        response = _post(authed_app, tenant, _body())
        assert response.status_code == 403, response.text
        assert response.json()["detail"]["error_code"] == ERROR_AUTHENTICATION_UNATTESTED
        assert fabric.hitl.submissions(tenant=tenant) == ()


class TestThereIsNoUnboundDoor:
    def test_there_is_no_unbound_door(self, fabric: Fabric) -> None:
        from ccf_runtime.http_api.app import create_app

        with pytest.raises(TypeError):
            create_app(_deps(fabric))  # type: ignore[call-arg]


class TestQueueView:
    def test_the_queue_view_is_the_capabilitys_tenant_and_only_that(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        from ccf.hitl.transport import PendingHitlEvent

        tenant = _tenant("queue")
        mine = PendingHitlEvent(
            event_key="queue-event-mine",
            event_class="approval-gate",
            tenant=tenant,
            workflow_state_ref=f"{tenant}/exec-q",
            product_content_hash=_VALID_HASH,
        )
        theirs = mine.model_copy(
            update={"tenant": _tenant("aal3"), "event_key": "queue-event-theirs"}
        )
        fabric.hitl.enqueue(event=mine)
        fabric.hitl.enqueue(event=theirs)
        response = call(
            authed_app,
            "GET",
            "/hitl/queue",
            headers={"Authorization": f"Bearer {_token_for(tenant)}"},
        )
        assert response.status_code == 200, response.text
        keys = {event["event_key"] for event in response.json()}
        assert "queue-event-mine" in keys
        assert "queue-event-theirs" not in keys


class TestHardenedPath:
    """D-IMPL-67 item 3, under P6: door-minted principal reaches replay dim 2."""

    def test_hardened_path_verified_subject_reaches_replay_dim2(
        self, fabric: Fabric, tmp_path: Path
    ) -> None:
        from datetime import timedelta

        from ccf.contracts.canonical import canonical_bytes
        from ccf.controlplane.audit import AuditLog
        from ccf.graph.protocols import GraphView
        from ccf.hitl.approval_gate import ApprovalGate, GateResolution
        from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
        from ccf.products.contract import ContextProductContract, ProductLineage
        from ccf.projection.engine import ExecutionResult, ExecutionStep
        from ccf.projection.plan import Perspective, ProjectionOutput
        from ccf.replay.record import (
            PolicyBinding,
            ResolutionNotApplicable,
            build_replay_record,
        )
        from ccf_runtime.http_api.app import create_app

        from hitl.capabilities import submit_capability

        tenant = _tenant("hardened")
        transport = InMemoryHitlTransport()
        event = PendingHitlEvent(
            event_key="hardened-event-1",
            event_class="approval-gate",
            tenant=tenant,
            workflow_state_ref=f"{tenant}/exec-hardened",
            product_content_hash=_VALID_HASH,
        )
        transport.enqueue(event=event)
        app = create_app(_deps(fabric, transport=transport), **_seams(fabric, tmp_path))

        response = _post(app, tenant, _body(event_key=event.event_key))
        assert response.status_code == 200, response.text
        (recorded,) = transport.submissions(tenant=tenant)
        assert recorded.principal.approver.subject_id == _CLIENT_ID
        assert recorded.authorizing_decision_id

        gate = ApprovalGate(transport=transport, audit=AuditLog(), clock=lambda: _CLOCK_TIME)
        resolution = gate.resolve(
            submit_capability(tenant=tenant, principal=_CLIENT_ID, event_key=event.event_key),
            event_key=event.event_key,
            action="approve",
            principal=recorded.principal,
        )
        assert isinstance(resolution, GateResolution)
        assert resolution.record.submission.principal.approver.subject_id == _CLIENT_ID
        assert _CLIENT_ID in resolution.hitl_actions_block

        boundary = _CLOCK_TIME
        execution = ExecutionResult(
            plan_id=event.workflow_state_ref,
            operators_invoked=frozenset({"traversal.neighbors"}),
            steps=(
                ExecutionStep(
                    operator_key="traversal.neighbors",
                    category="traversal",
                    parameter_hash="d" * 64,
                ),
            ),
            provenance=None,
            projection=ProjectionOutput(
                plan_id=event.workflow_state_ref, payload={"event_key": event.event_key}
            ),
            view=GraphView(tenant_id=tenant, as_of=boundary),
        )
        product = ContextProductContract(
            schema_name="ccf.hitl-decision-context",
            schema_version="1.0.0",
            plan_id=event.workflow_state_ref,
            tenant_id=tenant,
            temporal_boundary=boundary,
            expires_at=boundary + timedelta(days=1),
            ttl_anchor="from_decision",
            lineage=ProductLineage(
                operators_invoked=frozenset({"traversal.neighbors"}),
                policy_bundle_versions=frozenset({"1.0.0"}),
                graph_snapshot_at=boundary,
            ),
            payload={"event_key": event.event_key},
        )
        record = build_replay_record(
            execution=execution,
            product=product,
            perspective=Perspective(principal_id=event.workflow_state_ref, role=event.event_class),
            policy_bindings=(PolicyBinding(key="policy.bundle", version="1.0.0"),),
            assembly_mode="algorithmic",
            recorded_at=recorded.principal.action_time,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            hitl_actions=resolution.hitl_actions_block,
        )
        assert _CLIENT_ID in record.policy_bindings.hitl_actions
        assert record.policy_bindings.hitl_actions == resolution.hitl_actions_block
        assert _CLIENT_ID in canonical_bytes(record).decode("utf-8")
