"""The gate MINTS, and a handler holds a capability or holds nothing
(D-IMPL-353 §1.1, §1.3, §1.4, §3 — Lane CAP-GATE).

Written before the gate changed. What this file proves, drafted from what
would fail here:

==========================================  ==================================
Requirement                                 What would fail here
==========================================  ==================================
P1: a REAL credential opens the door         a ``TokenGrant`` minted through
                                            the real ``FileTokenSource`` —
                                            no subclass anywhere — would be
                                            refused, as every real credential
                                            was while the fixture subclass
                                            kept the suite green
the gate mints from an allow, only          a refusal would mint; an allow
                                            would mint for another action,
                                            tenant or principal; the
                                            capability would not name the
                                            allow event that authorized it
the gate selects the tenant, never picks    a multi-tenant grant on a route
                                            naming no tenant would be given
                                            one; a named non-member would
                                            supply one
a handler holds the capability or refuses   an absent, fabricated,
                                            retargeted or wrong-action object
                                            on ``request.state`` would be read
                                            as authority
the door acts under the capability's        an artifact would file, or a state
tenant                                      key would be built, under a tenant
                                            from anywhere else
``create_app`` refuses mismatched wiring    a recorder naming a governed class
                                            over a store that governs it,
                                            with no minting authority, would
                                            build and fail at its first
                                            denial instead of at boot
==========================================  ==================================

Every tenant name, scope, token and key below is test vocabulary (CINV-01).
"""

from __future__ import annotations

import inspect
import json
import pathlib
import re
from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from starlette.requests import Request

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import GovernedRecordClasses, GovernedWriteHandle
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
)
from ccf.authz.capability import (
    ArtifactWrite,
    Authorized,
    ConfigRegister,
    HealthRead,
    mint,
)
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf.authz.decision import AuthzDecision
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.authz.refusals import (
    ACTION_ARTIFACT_WRITE,
    ACTION_CONFIG_REGISTER,
    ACTION_HEALTH_READ,
)
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.errors import (
    ERROR_AMBIGUOUS_TENANT,
    ERROR_DECISION_UNMINTABLE,
    ERROR_NO_CAPABILITY,
    ERROR_REQUEST_UNAUTHORIZED,
    ERROR_UNTENANTED_GRANT,
)
from ccf_runtime.http_api.gate import (
    AuthorizationGate,
    UndeclaredRouteError,
    build_route_table,
)
from ccf_runtime.http_api.grants import authorized_from_request
from ccf_runtime.mcp.auth import FileTokenSource, StaticTokenSource, TokenGrant

from . import gate_fixtures
from .conftest import Fabric
from .gate_fixtures import (
    REPLAY_RECORD_CLASS,
    SCOPE_EVERYTHING,
    WIDE_RESOURCES,
    GateApp,
    probe,
    wide_authorizer,
)
from .test_product_declared_obligation_409 import _entitlement_registry, _recorder

#: Test vocabulary.
A = "cap-gate-tenant-a"
B = "cap-gate-tenant-b"
C = "cap-gate-tenant-c"
CLIENT = "cap-gate-caller"
SCOPE_ALL = "cap-gate:all"
SCOPE_NONE = "cap-gate:none"
TOKEN_A = "cap-gate-token-a"
TOKEN_AB = "cap-gate-token-ab"
TOKEN_NONE = "cap-gate-token-none"
MAPPING_KEY = "cap-gate/scope-mapping"
INSTANT = datetime(2026, 8, 11, tzinfo=UTC)
_RUNTIME = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "ccf_runtime"


def _grant(*tenants: str, scopes: tuple[str, ...] = (SCOPE_ALL,)) -> TokenGrant:
    return TokenGrant(client_id=CLIENT, scopes=scopes, tenants=frozenset(tenants))


class _Body(CCFContract):
    key: str


class _Echo:
    """A tiny app in front of the REAL gate, whose one job is to report what
    capability its handlers received. Nothing about the gate is stubbed:
    real ``StaticTokenSource``, real ``ControlPlaneTenantAuthorizer`` over a
    real pinned mapping, real ``build_route_table``."""

    def __init__(self, *, authorizer: Any | None = None) -> None:
        self.registry = ControlPlaneRegistry()
        version = self.registry.register_typed(
            MAPPING_KEY,
            ScopeMappingArtifact(
                semver="1.0.0",
                scopes={
                    SCOPE_ALL: ScopeEntry(
                        tenant_patterns=(A, B),
                        action_ids=(ACTION_HEALTH_READ, ACTION_CONFIG_REGISTER),
                        resource_patterns=WIDE_RESOURCES,
                    ),
                    SCOPE_NONE: ScopeEntry(
                        tenant_patterns=(A,),
                        action_ids=(),
                        resource_patterns=WIDE_RESOURCES,
                    ),
                },
            ),
            SCOPE_MAPPING,
        )
        assert isinstance(version, str)
        self.version = version
        self.authorizer = authorizer or ControlPlaneTenantAuthorizer(
            control_plane=self.registry,
            scope_mapping_key=MAPPING_KEY,
            scope_mapping_version=version,
            clock=lambda: INSTANT,
        )
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        router = APIRouter()

        def report(authorized: Authorized[Any]) -> dict[str, Any]:
            return {
                "action": authorized.kind.action_id,
                "tenant": authorized.tenant,
                "principal": authorized.principal,
                "resource": authorized.resource,
                "decision_id": authorized.decision_id,
            }

        @router.get("/probe")
        @authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
        def probe_route(request: Request) -> dict[str, Any]:
            return report(authorized_from_request(request, kind=HealthRead))

        @router.get("/tenanted/{tenant}")
        @authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
        def tenanted(tenant: str, request: Request) -> dict[str, Any]:
            return report(authorized_from_request(request, kind=HealthRead))

        @router.post("/register")
        @authorizes(ACTION_CONFIG_REGISTER, resource=ResourceBinding.body("key"))
        def register(body: _Body, request: Request) -> dict[str, Any]:
            return report(authorized_from_request(request, kind=ConfigRegister))

        @router.get("/untyped")
        @authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
        def untyped(request: Request) -> dict[str, Any]:
            return report(authorized_from_request(request))

        @router.get("/wrong-kind")
        @authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
        def wrong_kind(request: Request) -> dict[str, Any]:
            # The handler names an action this route does not perform.
            return report(authorized_from_request(request, kind=ConfigRegister))

        app.include_router(router)
        table = build_route_table(app)
        app.add_middleware(
            AuthorizationGate,
            auth=BearerTokenAuth(
                token_source=StaticTokenSource(
                    grants={
                        TOKEN_A: _grant(A),
                        TOKEN_AB: _grant(A, B),
                        TOKEN_NONE: _grant(A, scopes=(SCOPE_NONE,)),
                    }
                )
            ),
            authorizer=self.authorizer,
            table=table,
        )
        self.app = app

    def get(self, url: str, *, token: str) -> Any:
        return probe(self.app, "GET", url, headers={"Authorization": f"Bearer {token}"})

    def post(self, url: str, *, token: str, body: dict[str, Any]) -> Any:
        return probe(
            self.app,
            "POST",
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )

    def allows(self) -> tuple[AuthzDecisionAuditEvent, ...]:
        return tuple(
            event
            for event in self.registry.audit_events()
            if isinstance(event, AuthzDecisionAuditEvent) and event.resolved
        )

    def decisions(self) -> tuple[AuthzDecisionAuditEvent, ...]:
        return tuple(
            event
            for event in self.registry.audit_events()
            if isinstance(event, AuthzDecisionAuditEvent)
        )


@pytest.fixture(scope="module")
def echo() -> _Echo:
    return _Echo()


# --- P1: the real token source opens the real door -----------------------------


class TestP1TheRealCredentialOpensTheDoor:
    def _app(self, fabric: Fabric, root: pathlib.Path, *, tenants: list[str]) -> Any:
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.dependencies import ApiDependencies

        tenant = fabric.product_address.tenant
        path = root / "tokens.json"
        path.write_text(
            json.dumps(
                {
                    "real-token": {
                        "client_id": CLIENT,
                        "scopes": [SCOPE_EVERYTHING],
                        "tenants": tenants,
                    }
                }
            ),
            encoding="utf-8",
        )
        source = ControlPlaneProductEntitlementSource(
            control_plane=_entitlement_registry(fabric), clock=lambda: INSTANT
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
            # THE REAL DEV SOURCE, reading a file with `tenants`. No subclass.
            auth=BearerTokenAuth(token_source=FileTokenSource(path=path)),
            authorizer=wide_authorizer(tenant=tenant, key="cap-gate-p1/mapping"),
            product_entitlement=source,
            perspective_resolver=(
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role="cap-gate-role"
                )
            ),
            refusal_recorder=_recorder(fabric, root, source=source),
        )

    def test_a_file_token_source_grant_with_tenants_is_served(
        self, fabric: Fabric, tmp_path: pathlib.Path
    ) -> None:
        """The regression. Before D-IMPL-353 this exact request was refused
        ``untenanted-grant`` by every route, and no committed test noticed."""
        tenant = fabric.product_address.tenant
        app = self._app(fabric, tmp_path, tenants=[tenant])
        headers = {"Authorization": "Bearer real-token"}

        assert probe(app, "GET", "/health", headers=headers).status_code == 200
        keys = probe(
            app, "GET", "/config/keys", params={"class_id": "x"}, headers=headers
        )
        assert keys.status_code == 200
        filed = probe(
            app,
            "POST",
            "/artifact",
            headers=headers,
            json={"artifact_class": "cap-gate-blob", "name": "p1", "artifact": {"k": 1}},
        )
        assert filed.status_code == 200, filed.text
        assert filed.json()["uri"].startswith(f"ccf-artifact://{tenant}/")

    def test_the_same_file_without_tenants_is_refused_untenanted(
        self, fabric: Fabric, tmp_path: pathlib.Path
    ) -> None:
        """The control: it is the ``tenants`` line that opened the door."""
        app = self._app(fabric, tmp_path, tenants=[])
        refused = probe(
            app, "GET", "/health", headers={"Authorization": "Bearer real-token"}
        )
        assert refused.status_code == 403
        assert refused.json()["detail"]["error_code"] == ERROR_UNTENANTED_GRANT

    def test_the_fixture_mints_the_base_contract_and_nothing_else(self) -> None:
        """No subclass exists to fake it (design §9 (1)).

        Population: every public name in ``gate_fixtures`` and every grant
        its two helpers mint.
        """
        assert not hasattr(gate_fixtures, "TenantedTokenGrant")
        subclasses = [
            name
            for name, value in vars(gate_fixtures).items()
            if inspect.isclass(value)
            and issubclass(value, TokenGrant)
            and value is not TokenGrant
        ]
        assert subclasses == []
        source = gate_fixtures.tenanted_source(
            {"t": (CLIENT, (SCOPE_ALL,)), "u": (CLIENT, (SCOPE_ALL,), (A, B))},
            tenant=A,
        )
        assert isinstance(source, StaticTokenSource)
        for token, expected in (("t", {A}), ("u", {A, B})):
            minted = source.grant_for(token=token)
            assert minted is not None
            assert type(minted) is TokenGrant
            assert minted.tenants == frozenset(expected)
        direct = gate_fixtures.grant(CLIENT, (SCOPE_ALL,), (A,))
        assert type(direct) is TokenGrant

    def test_no_test_in_this_package_subclasses_the_grant(self) -> None:
        """Population: every ``.py`` under ``tests/http_api``. A subclass of
        ``TokenGrant`` anywhere here is the P1 shape coming back."""
        here = pathlib.Path(__file__).parent
        files = sorted(here.glob("*.py"))
        assert len(files) > 20
        offenders = [
            path.name
            for path in files
            if re.search(r"class\s+\w+\((?:\w+\.)?TokenGrant\)", path.read_text())
        ]
        assert offenders == []


# --- the gate mints from an allow, and only from an allow ----------------------


class TestTheGateMints:
    def test_an_allow_mints_for_the_routes_action_and_the_grants_tenant(
        self, echo: _Echo
    ) -> None:
        before = len(echo.allows())
        response = echo.get("/probe", token=TOKEN_A)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body == {
            "action": ACTION_HEALTH_READ,
            "tenant": A,
            "principal": CLIENT,
            "resource": ACTION_HEALTH_READ,
            "decision_id": body["decision_id"],
        }
        # §1.5(a): the decision_id IS the allow event, by content address.
        (event,) = echo.allows()[before:]
        assert body["decision_id"] == content_hash(event)
        assert event.authz_action_id == ACTION_HEALTH_READ
        assert event.key == A
        assert event.actor == CLIENT

    def test_the_decision_id_resolves_to_exactly_one_event(self, echo: _Echo) -> None:
        echo.get("/probe", token=TOKEN_A)
        echo.get("/probe", token=TOKEN_A)
        second = echo.get("/probe", token=TOKEN_A).json()["decision_id"]
        matching = [e for e in echo.decisions() if content_hash(e) == second]
        assert len(matching) == 1
        assert matching[0].resolved is True

    def test_a_body_sourced_resource_is_the_capabilitys_resource(
        self, echo: _Echo
    ) -> None:
        body = echo.post("/register", token=TOKEN_A, body={"key": "cap/one"}).json()
        assert body["action"] == ACTION_CONFIG_REGISTER
        assert body["resource"] == "cap/one"

    def test_a_refusal_mints_nothing(
        self, echo: _Echo, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import ccf_runtime.http_api.gate as gate_module

        minted: list[Any] = []
        real = gate_module.mint

        def counting(*args: Any, **kwargs: Any) -> Any:
            capability = real(*args, **kwargs)
            minted.append(capability)
            return capability

        monkeypatch.setattr(gate_module, "mint", counting)
        assert echo.get("/probe", token=TOKEN_NONE).status_code == 403
        assert echo.get("/no-such-route", token=TOKEN_A).status_code == 403
        assert echo.get("/probe", token="unknown").status_code == 401
        assert minted == []
        assert echo.get("/probe", token=TOKEN_A).status_code == 200
        assert len(minted) == 1

    def test_an_untyped_read_returns_the_same_capability(self, echo: _Echo) -> None:
        """``authorized_from_request(request)`` — the spec'd signature — is
        the same read, still verified against the route's own action."""
        body = echo.get("/untyped", token=TOKEN_A).json()
        assert body["action"] == ACTION_HEALTH_READ
        assert body["tenant"] == A


# --- the tenant is SELECTED; the gate does not pick ----------------------------


class TestTheGateSelectsTheTenant:
    def test_several_tenants_and_a_route_naming_none_is_ambiguous(
        self, echo: _Echo
    ) -> None:
        before = len(echo.decisions())
        refused = echo.get("/probe", token=TOKEN_AB)
        assert refused.status_code == 403
        assert refused.json()["detail"]["error_code"] == ERROR_AMBIGUOUS_TENANT
        # Refused before the authorizer is asked: no decision to record. The
        # honest edge, named rather than smoothed over.
        assert len(echo.decisions()) == before

    def test_a_named_member_is_the_one_decided_for(self, echo: _Echo) -> None:
        assert echo.get(f"/tenanted/{B}", token=TOKEN_AB).json()["tenant"] == B
        assert echo.get(f"/tenanted/{A}", token=TOKEN_AB).json()["tenant"] == A
        (latest,) = echo.allows()[-1:]
        assert latest.key == A

    def test_a_named_non_member_is_the_constant_denial(self, echo: _Echo) -> None:
        """Not ``ambiguous-tenant``: which tenants a credential is near is not
        a caller's to learn from a refusal."""
        crossed = echo.get(f"/tenanted/{C}", token=TOKEN_AB).json()["detail"]
        unmatched = echo.get("/no-such-route", token=TOKEN_AB).json()["detail"]
        assert crossed["error_code"] == ERROR_REQUEST_UNAUTHORIZED
        assert crossed == unmatched

    def test_exactly_one_tenant_and_a_route_naming_none_selects_it(
        self, echo: _Echo
    ) -> None:
        assert echo.get("/probe", token=TOKEN_A).json()["tenant"] == A

    def test_one_tenant_on_a_tenanted_route_must_still_agree(self, echo: _Echo) -> None:
        assert echo.get(f"/tenanted/{A}", token=TOKEN_A).status_code == 200
        assert echo.get(f"/tenanted/{B}", token=TOKEN_A).status_code == 403


# --- an allow the gate cannot mint from ---------------------------------------


class TestAnUnmintableAllow:
    @pytest.mark.parametrize(
        ("label", "decision_overrides"),
        [
            ("no decision id", {"decision_id": None}),
            ("another tenant", {"tenant": B}),
            ("another action", {"action_id": ACTION_CONFIG_REGISTER}),
            ("another resource", {"resource": "something-else"}),
        ],
    )
    def test_an_allow_that_answers_a_different_question_is_refused_503(
        self, label: str, decision_overrides: dict[str, Any]
    ) -> None:
        class _Stub:
            def authorize(
                self, *, grant: TokenGrant, tenant: str, action_id: str, resource: str
            ) -> AuthzDecision:
                fields: dict[str, Any] = {
                    "allowed": True,
                    "matched_scope_pattern": tenant,
                    "matched_resource_pattern": resource,
                    "artifact_version": "1",
                    "action_id": action_id,
                    "tenant": tenant,
                    "resource": resource,
                    "decision_id": "f" * 64,
                }
                fields.update(decision_overrides)
                return AuthzDecision(**fields)

        door = _Echo(authorizer=_Stub())
        refused = door.get("/probe", token=TOKEN_A)
        assert refused.status_code == 503, label
        assert refused.json()["detail"]["error_code"] == ERROR_DECISION_UNMINTABLE

    def test_the_sdk_authorizers_allow_is_always_mintable(self, echo: _Echo) -> None:
        """The positive control for the stub above."""
        assert echo.get("/probe", token=TOKEN_A).status_code == 200


# --- boot: an action with no kind cannot be mounted ----------------------------


def test_a_route_declaring_an_action_no_kind_exists_for_is_refused_at_boot() -> None:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    router = APIRouter()

    @router.get("/orphan")
    @authorizes("cap-gate.no-such-action", resource=ResourceBinding.route())
    def orphan() -> dict[str, str]:
        return {}

    app.include_router(router)
    with pytest.raises(UndeclaredRouteError, match="no-such-action"):
        build_route_table(app)


# --- a handler holds the capability or holds nothing ---------------------------


def _bare_request(*, endpoint: Any, state: dict[str, Any]) -> Request:
    """A request that reached a handler WITHOUT the gate."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "headers": [],
            "query_string": b"",
            "endpoint": endpoint,
            "state": state,
        }
    )


@authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
def _health_endpoint() -> None: ...


def _genuine(kind: Any = HealthRead, action: str = ACTION_HEALTH_READ) -> Any:
    return mint(
        kind,
        decision=AuthzDecision(
            allowed=True,
            matched_scope_pattern=A,
            matched_resource_pattern=action,
            artifact_version="1",
            action_id=action,
            tenant=A,
            resource=action,
        ),
        principal=CLIENT,
        decision_id="d" * 64,
    )


class TestAHandlerHoldsTheCapabilityOrNothing:
    def _refused(self, state: dict[str, Any], **kwargs: Any) -> HTTPException:
        with pytest.raises(HTTPException) as raised:
            authorized_from_request(
                _bare_request(endpoint=_health_endpoint, state=state), **kwargs
            )
        assert raised.value.status_code == 403
        detail = raised.value.detail
        assert isinstance(detail, dict)
        assert detail["error_code"] == ERROR_NO_CAPABILITY
        return raised.value

    def test_reached_without_the_gate_there_is_nothing_to_hold(self) -> None:
        self._refused({})
        self._refused({"token_grant": _grant(A)})  # a grant is not a capability

    def test_a_fabricated_object_is_refused(self) -> None:
        looks_right = Mock()
        looks_right.kind = HealthRead
        looks_right.tenant, looks_right.principal = A, CLIENT
        looks_right.resource, looks_right.decision_id = ACTION_HEALTH_READ, "d" * 64
        for planted in (object(), looks_right, Authorized.__new__(Authorized)):
            self._refused({"authorized": planted})

    def test_a_retargeted_genuine_capability_is_refused(self) -> None:
        for field, value in (("tenant", B), ("kind", ConfigRegister), ("principal", "x")):
            capability = _genuine()
            object.__setattr__(capability, field, value)
            self._refused({"authorized": capability})

    def test_a_capability_for_another_action_is_refused_by_the_route(self) -> None:
        """Minted genuinely, for artifact.write; planted on a request whose
        endpoint declares health.read. The gate authorized one route; it must
        not serve another."""
        self._refused({"authorized": _genuine(ArtifactWrite, ACTION_ARTIFACT_WRITE)})

    def test_a_genuine_capability_for_this_route_is_returned(self) -> None:
        capability = _genuine()
        request = _bare_request(endpoint=_health_endpoint, state={"authorized": capability})
        assert authorized_from_request(request) is capability
        assert authorized_from_request(request, kind=HealthRead) is capability

    def test_a_handler_naming_the_wrong_kind_is_refused(self, echo: _Echo) -> None:
        capability = _genuine()
        request = _bare_request(endpoint=_health_endpoint, state={"authorized": capability})
        with pytest.raises(HTTPException):
            authorized_from_request(request, kind=ConfigRegister)
        # And through the real gate: the route's own handler names the wrong kind.
        assert echo.get("/wrong-kind", token=TOKEN_A).status_code == 403

    def test_the_join_shim_has_exactly_one_caller_and_it_is_the_hitl_door(
        self,
    ) -> None:
        """``tenant_from_request`` survives ONLY as ``authorized.tenant`` for
        ``routes/hitl.py`` (Lane HITL-DOOR's file) until that lane migrates;
        it is deleted at join. Population: every ``.py`` under
        ``runtime/ccf_runtime``."""
        files = sorted(_RUNTIME.rglob("*.py"))
        assert len(files) > 50
        callers = sorted(
            str(path.relative_to(_RUNTIME))
            for path in files
            if "tenant_from_request(" in path.read_text(encoding="utf-8")
            and path.name != "grants.py"
        )
        assert callers == ["http_api/routes/hitl.py"]
        # And no route this lane owns reads a tenant from anything but the
        # capability: the old reader is gone from the tree entirely.
        readers = [
            str(path.relative_to(_RUNTIME))
            for path in files
            if "tenant_of_grant(" in path.read_text(encoding="utf-8")
        ]
        assert readers == []


# --- the door acts under the capability's tenant --------------------------------


class TestTheDoorActsUnderTheCapabilitysTenant:
    def test_an_artifact_files_under_the_selected_tenant(self, gate_app: GateApp) -> None:
        filed = probe(
            gate_app.app,
            "POST",
            "/artifact",
            headers=gate_app.auth(),
            json={"artifact_class": "cap-gate-blob", "name": "own", "artifact": {"k": 2}},
        )
        assert filed.status_code == 200, filed.text
        assert filed.json()["uri"].startswith(f"ccf-artifact://{gate_app.tenant}/")

    def test_a_multi_tenant_credential_cannot_file_because_the_route_names_none(
        self, gate_app: GateApp
    ) -> None:
        refused = probe(
            gate_app.app,
            "POST",
            "/artifact",
            headers=gate_app.auth(gate_app.token_multi_tenant),
            json={"artifact_class": "cap-gate-blob", "name": "which", "artifact": {}},
        )
        assert refused.status_code == 403
        assert refused.json()["detail"]["error_code"] == ERROR_AMBIGUOUS_TENANT

    def test_a_multi_tenant_credential_reaches_a_route_that_names_a_member(
        self, gate_app: GateApp, fabric: Fabric
    ) -> None:
        address = fabric.product_address
        own = probe(
            gate_app.app,
            "GET",
            f"/product/{gate_app.tenant}/{address.product_class}/{address.version}",
            headers=gate_app.auth(gate_app.token_multi_tenant),
        )
        assert own.status_code == 200, own.text
        stranger = probe(
            gate_app.app,
            "GET",
            f"/product/cap-gate-nobody/{address.product_class}/{address.version}",
            headers=gate_app.auth(gate_app.token_multi_tenant),
        )
        assert stranger.status_code == 403
        assert stranger.json()["detail"]["error_code"] == ERROR_REQUEST_UNAUTHORIZED

    def test_the_workflow_state_key_is_the_capabilitys_tenant(
        self, gate_app: GateApp
    ) -> None:
        absent = probe(
            gate_app.app,
            "GET",
            "/workflow/execution",
            params={"execution_id": "cap-gate-none"},
            headers=gate_app.auth(),
        )
        assert absent.status_code == 404
        assert f"{gate_app.tenant}/cap-gate-none" in absent.json()["detail"]

    def test_a_deny_on_the_real_door_says_what_it_denied(self, gate_app: GateApp) -> None:
        """§3, end to end: the audit event of a gate deny carries the
        resource and the failing axis."""
        before = len(gate_app.registry.audit_events())
        probe(gate_app.app, "GET", "/health", headers=gate_app.auth(gate_app.token_nothing))
        new = [
            event
            for event in gate_app.registry.audit_events()[before:]
            if isinstance(event, AuthzDecisionAuditEvent)
        ]
        assert len(new) == 1
        (deny,) = new
        assert deny.resolved is False
        assert deny.authz_resource == ACTION_HEALTH_READ
        assert deny.authz_failing_axis == "action"
        assert deny.authz_matched_resource_pattern is None


# --- create_app refuses mismatched wiring --------------------------------------


class TestCreateAppRefusesMismatchedWiring:
    def _seams(self, fabric: Fabric, root: pathlib.Path, recorder: Any) -> dict[str, Any]:
        source = ControlPlaneProductEntitlementSource(
            control_plane=_entitlement_registry(fabric), clock=lambda: INSTANT
        )
        return {
            "auth": BearerTokenAuth(
                token_source=StaticTokenSource(grants={TOKEN_A: _grant(A)})
            ),
            "authorizer": wide_authorizer(tenant=A, key="cap-gate-wiring/mapping"),
            "product_entitlement": source,
            "perspective_resolver": (
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role="cap-gate-role"
                )
            ),
            "refusal_recorder": recorder,
        }

    def _recorder_over(self, store: Any, fabric: Fabric) -> ReplayRefusalRecorder:
        return ReplayRefusalRecorder(
            artifact_store=store,
            replay_record_class=REPLAY_RECORD_CLASS,
            tenant_id=fabric.product_address.tenant,
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
        )

    def test_a_governed_class_with_no_minting_authority_is_refused_at_boot(
        self, fabric: Fabric, tmp_path: pathlib.Path
    ) -> None:
        from ccf_runtime.http_api.app import GovernedWiringError, create_app
        from ccf_runtime.http_api.dependencies import ApiDependencies

        governed = FileArtifactStore(
            root=tmp_path / "governed",
            governed=GovernedRecordClasses.declare(REPLAY_RECORD_CLASS),
        )
        deps = ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
        )
        with pytest.raises(GovernedWiringError, match=REPLAY_RECORD_CLASS):
            create_app(deps, **self._seams(fabric, tmp_path, self._recorder_over(governed, fabric)))

    def test_the_same_recorder_over_the_minting_handle_builds(
        self, fabric: Fabric, tmp_path: pathlib.Path
    ) -> None:
        """The positive control: the refusal is about authority, not class."""
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.dependencies import ApiDependencies

        governed = FileArtifactStore(
            root=tmp_path / "governed",
            governed=GovernedRecordClasses.declare(REPLAY_RECORD_CLASS),
        )
        deps = ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
        )
        app = create_app(
            deps,
            **self._seams(
                fabric, tmp_path, self._recorder_over(GovernedWriteHandle(governed), fabric)
            ),
        )
        assert app is not None
