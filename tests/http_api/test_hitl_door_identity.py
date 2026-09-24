"""HITL HTTP door identity composition (07-20; D-IMPL-67 items 1 and 3).

The 7.1 mechanisms exist separately: ``principal_from_token_grant`` derives
a binding whose subject is the *verified* ``TokenGrant.client_id`` (07-16),
and ``create_app``'s optional auth hook stashes the verified grant on
``request.state.token_grant``. D-IMPL-67 rules that the HITL action door
must *compose* them: with a hook bound, the audited submission's subject IS
the verified identity — a conflicting caller-typed subject is a typed 403
refusal that never touches the transport — and with no hook bound the
recorded T-07-24 posture is byte-for-byte unchanged.

Test values are deployment vocabulary chosen by this test-as-deployment,
following the ``tests/http_api/test_auth.py`` precedent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf_runtime.mcp.auth import FileTokenSource

from .conftest import Fabric, call

#: A syntactically valid lowercase sha256 hex digest (shape only).
_VALID_HASH = "b" * 64

_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

#: The one credential this test deployment recognises, and the identity it
#: verifies to. Test values, meaningful nowhere else.
_TOKEN = "door-token"
_CLIENT_ID = "auditor-1"

_TENANT = "identity-door-tenant"


def _deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

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


def _submission_body(*, subject_id: str, tenant: str = _TENANT) -> dict[str, Any]:
    return {
        "event_key": "door-event-1",
        "tenant": tenant,
        "action": "approve",
        "principal": {
            "approver": {
                "subject_id": subject_id,
                "identity_provider_ref": "idp://acme-bank/dev-token-file",
            },
            "authentication": {
                "method": "bearer-token",
                "assurance_level": "dev",
                "session_ref": "door-session-1",
            },
            "action_time": _AWARE_TIME.isoformat(),
            "product_content_hash": _VALID_HASH,
        },
        "annotation": None,
    }


@pytest.fixture(scope="module")
def token_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("hitl-door-auth") / "tokens.json"
    path.write_text(
        json.dumps({_TOKEN: {"client_id": _CLIENT_ID, "scopes": ["hitl"]}}),
        encoding="utf-8",
    )
    return path


#: The tenants this suite keeps its tests apart with, and one credential per
#: tenant: ``tenant := grant.tenant`` (``SEC-002``) means a credential names
#: exactly one, so isolating by tenant isolates by token too.
_SUFFIXES = ("conflict", "derive", "unbound", "hardened")
_TOKENS = {
    f"{_TOKEN}-{suffix}": (_CLIENT_ID, ("gate:everything",), f"{_TENANT}-{suffix}")
    for suffix in _SUFFIXES
}


def _token_for(tenant: str) -> str:
    return f"{_TOKEN}-{tenant.rsplit('-', 1)[-1]}"


def _seams(fabric: Fabric, root: Path) -> dict[str, Any]:
    """Everything ``create_app`` requires, with this suite's credentials."""
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
        tenant=tuple(f"{_TENANT}-{suffix}" for suffix in _SUFFIXES),
        key="hitl-door-identity/mapping",
        grants=_TOKENS,
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role="hitl-door-role"
            )
        ),
        refusal_recorder=_recorder(fabric, root, source=source),
    )


@pytest.fixture(scope="module")
def authed_app(
    fabric: Fabric, tmp_path_factory: pytest.TempPathFactory
) -> Any:
    from ccf_runtime.http_api.app import create_app

    return create_app(
        _deps(fabric), **_seams(fabric, tmp_path_factory.mktemp("hitl-door"))
    )


class TestConflictRefusal:
    """Test A: a conflicting body subject is a typed 403, transport untouched."""

    def test_a_conflicting_subject_is_403_and_nothing_lands(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        tenant = f"{_TENANT}-conflict"
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="someone-else", tenant=tenant),
            headers={"Authorization": f"Bearer {_token_for(tenant)}"},
        )
        assert response.status_code == 403
        # The refusal is the typed subject-conflict code (no prose parsing),
        # and it never echoes the token.
        from ccf_runtime.http_api.errors import ERROR_SUBJECT_CONFLICT

        assert (
            response.json()["detail"]["error_code"] == ERROR_SUBJECT_CONFLICT
        )
        assert _TOKEN not in response.text
        # Nothing was enqueued or recorded on the refused path.
        assert fabric.hitl.submissions(tenant=tenant) == ()


class TestDerivation:
    """Test B: the accepted submission's subject IS the verified client_id."""

    def test_b_accepted_subject_is_derived_from_the_grant(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        tenant = f"{_TENANT}-derive"
        body = _submission_body(subject_id=_CLIENT_ID, tenant=tenant)
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json=body,
            headers={"Authorization": f"Bearer {_token_for(tenant)}"},
        )
        assert response.status_code == 200
        receipt = response.json()
        assert receipt["status"] == "submitted"
        assert (
            receipt["submission"]["principal"]["approver"]["subject_id"]
            == _CLIENT_ID
        )
        (recorded,) = fabric.hitl.submissions(tenant=tenant)
        principal = recorded.principal
        assert principal.approver.subject_id == _CLIENT_ID
        # Everything else the body stated travels verbatim.
        assert (
            principal.approver.identity_provider_ref
            == body["principal"]["approver"]["identity_provider_ref"]
        )
        assert (
            principal.authentication.method
            == body["principal"]["authentication"]["method"]
        )
        assert (
            principal.authentication.assurance_level
            == body["principal"]["authentication"]["assurance_level"]
        )
        assert (
            principal.authentication.session_ref
            == body["principal"]["authentication"]["session_ref"]
        )
        assert principal.action_time == _AWARE_TIME
        assert principal.product_content_hash == _VALID_HASH


class TestTheUnboundPostureIsGone:
    """Test C, inverted by ``SEC-001``.

    It read ``TestUnboundPostureUnchanged`` and proved that a door built with
    no auth hook accepted ``subject_id="anyone-at-all"`` and recorded it —
    the T-07-24 posture, preserved deliberately. There is no hookless door to
    build now, and an arbitrary subject is refused on the door that exists,
    which is the two halves of the same claim.
    """

    def test_c_there_is_no_unbound_door(self, fabric: Fabric) -> None:
        from ccf_runtime.http_api.app import create_app

        with pytest.raises(TypeError):
            create_app(_deps(fabric))  # type: ignore[call-arg]

    def test_c_an_arbitrary_subject_is_refused_and_nothing_lands(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        tenant = f"{_TENANT}-unbound"
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="anyone-at-all", tenant=tenant),
            headers={"Authorization": f"Bearer {_token_for(tenant)}"},
        )
        assert response.status_code == 403
        assert fabric.hitl.submissions(tenant=tenant) == ()


class TestHardenedPath:
    """D-IMPL-67 item 3: auth bound => derived principal => replay dim 2."""

    def test_hardened_path_verified_subject_reaches_replay_dim2(
        self, fabric: Fabric, tmp_path: Path
    ) -> None:
        from datetime import timedelta

        from ccf.contracts.canonical import canonical_bytes
        from ccf.controlplane.audit import AuditLog
        from ccf.graph.protocols import GraphView
        from ccf.hitl.approval_gate import ApprovalGate, GateResolution
        from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
        from ccf.products.contract import (
            ContextProductContract,
            ProductLineage,
        )
        from ccf.projection.engine import ExecutionResult, ExecutionStep
        from ccf.projection.plan import Perspective, ProjectionOutput
        from ccf.replay.record import (
            PolicyBinding,
            ResolutionNotApplicable,
            build_replay_record,
        )
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.auth import BearerTokenAuth
        from ccf_runtime.http_api.dependencies import ApiDependencies

        tenant = f"{_TENANT}-hardened"
        transport = InMemoryHitlTransport()
        event = PendingHitlEvent(
            event_key="hardened-event-1",
            event_class="approval-gate",
            tenant=tenant,
            workflow_state_ref=f"{tenant}/exec-hardened",
            product_content_hash=_VALID_HASH,
        )
        transport.enqueue(event=event)

        deps = ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=transport,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        )
        app = create_app(deps, **_seams(fabric, tmp_path))

        # 2. The authenticated POST, subject matching the verified identity.
        response = call(
            app,
            "POST",
            "/hitl/actions",
            json={
                **_submission_body(subject_id=_CLIENT_ID, tenant=tenant),
                "event_key": event.event_key,
            },
            headers={"Authorization": f"Bearer {_token_for(tenant)}"},
        )
        assert response.status_code == 200

        # 3. Resolve the gate from the recorded submission.
        (recorded,) = transport.submissions(tenant=tenant)
        assert recorded.principal.approver.subject_id == _CLIENT_ID

        def clock() -> datetime:
            return _AWARE_TIME

        gate = ApprovalGate(transport=transport, audit=AuditLog(), clock=clock)
        resolution = gate.resolve(
            tenant=tenant,
            event_key=event.event_key,
            action="approve",
            principal=recorded.principal,
        )

        # 4. The verified subject lands in the record, the dim-2 block, and
        # the built replay record's hitl_actions field.
        assert isinstance(resolution, GateResolution)
        assert (
            resolution.record.submission.principal.approver.subject_id
            == _CLIENT_ID
        )
        assert _CLIENT_ID in resolution.hitl_actions_block

        boundary = _AWARE_TIME
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
                plan_id=event.workflow_state_ref,
                payload={"event_key": event.event_key},
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
            perspective=Perspective(
                principal_id=event.workflow_state_ref, role=event.event_class
            ),
            policy_bindings=(
                PolicyBinding(key="policy.bundle", version="1.0.0"),
            ),
            assembly_mode="algorithmic",
            recorded_at=recorded.principal.action_time,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            hitl_actions=resolution.hitl_actions_block,
        )
        assert _CLIENT_ID in record.policy_bindings.hitl_actions
        # The block travels verbatim onto dimension 2.
        assert (
            record.policy_bindings.hitl_actions
            == resolution.hitl_actions_block
        )
        assert _CLIENT_ID in canonical_bytes(record).decode("utf-8")
