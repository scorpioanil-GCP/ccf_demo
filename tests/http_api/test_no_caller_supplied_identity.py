"""No route takes a tenant or an actor from the caller (``SEC-002``, Task 4).

The tenant is selected from the verified grant's ``tenants`` set
(D-IMPL-353 §1.3), and nothing else is a source. A path segment may **assert**
a tenant the grant holds — the segment is part of a product's address and a
URI has to keep meaning what it meant — but it may never **supply** one the
grant lacks. The same holds for the acting principal: the
audited author of a ledger transition is the verified caller, never a string in
the body (the ``D-IMPL-67`` derivation precedent, applied to the two skill
verbs).

This file is the sweep, and it is deliberately **structural**: it reads the
mounted routes' own signatures rather than a list somebody maintains, so a
route added tomorrow with an ``actor`` field is caught by the same assertion
that caught the three deleted today.

Drafted from what would fail here:

==========================================  ==================================
Requirement                                 What would fail here
==========================================  ==================================
no tenant-bearing body field                ``ArtifactPutRequest.tenant_id``
                                            would come back, and a recognized
                                            bearer would file into any
                                            tenant's namespace by typing it
no caller-typed actor                       ``GrantRequest.actor`` /
                                            ``GrantRevocationRequest.actor``
                                            would come back, and the audited
                                            author of a grant would be a
                                            value the caller wrote
no tenant query parameter                   ``/hitl/queue?tenant=`` and
                                            ``/workflow/execution?tenant=``
                                            would come back, and a bearer
                                            would read any tenant's queue or
                                            execution state
the sweep has something to sweep            the population would be empty and
                                            the assertions vacuous
==========================================  ==================================

The one place a tenant **may** appear is a path parameter, and that exception
is asserted rather than assumed: the gate holds such a segment equal to the
grant's tenant (``tests/http_api/test_tenant_authz.py``), so it can agree and
cannot supply.

**Two body fields are excepted by name, and the exception is not a free pass.**
:class:`~ccf.hitl.transport.HitlActionSubmission` and
:class:`~ccf.skills.catalog.SkillCatalogEntry` each declare a ``tenant``, and
both contracts live in ``src/ccf/`` — a different tree from the one this work
owns, so the fields are **owed** there rather than deletable here. Each is
listed in :data:`EXCEPTED` with the route that receives it, and
:class:`TestEveryExceptionIsEnforcedAtItsDoor` asserts that route refuses a
value that disagrees with the verified grant. An exception nobody could add a
third entry to without noticing, and none that is merely tolerated.
"""

from __future__ import annotations

import inspect
from typing import Any, get_type_hints

import pytest
from pydantic import BaseModel

from ccf.contracts.base import CCFContract

from ccf_runtime.authz.route_declaration import TENANT_PATH_PARAM
from ccf_runtime.http_api.gate import mounted_routes

#: A field or parameter name is refused when it *starts with* ``tenant`` or is
#: exactly ``actor``. The prefix rather than an equality: ``tenant_id``,
#: ``tenant_name`` and ``tenants`` are the same defect under three spellings,
#: and the one that ships is always the spelling the check did not list.
def _is_identity_name(name: str) -> bool:
    return name.startswith("tenant") or name == "actor"


#: ``(route template, contract, field)`` for the tenant-bearing body fields
#: declared **outside** this tree. Named one by one, never by wildcard: a
#: third contract growing one is a red test, which is the whole point.
EXCEPTED: tuple[tuple[str, str, str], ...] = (
    ("/skill/catalog", "SkillCatalogEntry", "tenant"),
)

_EXCUSED = frozenset(
    f"{template}: body field {field!r}" for template, _contract, field in EXCEPTED
)


def _path_parameters(template: str) -> frozenset[str]:
    """The names this template captures, so path params can be excused."""
    found: set[str] = set()
    rest = template
    while "{" in rest:
        rest = rest.split("{", 1)[1]
        name, _, rest = rest.partition("}")
        found.add(name.split(":", 1)[0])
    return frozenset(found)


def _offences(app: Any) -> list[str]:
    """Every query parameter and body field naming a tenant or an actor."""
    found: list[str] = []
    for template, route in mounted_routes(app):
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        path_parameters = _path_parameters(template)
        try:
            hints = get_type_hints(endpoint)
        except Exception:  # pragma: no cover - a handler with an exotic hint
            hints = {}
        for name, parameter in inspect.signature(endpoint).parameters.items():
            annotation = hints.get(name, parameter.annotation)
            if isinstance(annotation, type) and issubclass(
                annotation, BaseModel
            ):
                found.extend(
                    f"{template}: body field {field!r}"
                    for field in annotation.model_fields
                    if _is_identity_name(field)
                )
                continue
            if name in path_parameters:
                # The one permitted appearance, held equal by the gate.
                continue
            if _is_identity_name(name):
                found.append(f"{template}: parameter {name!r}")
    return found


class _PlantedBody(CCFContract):
    """The negative control's body model.

    **Module scope on purpose.** ``from __future__ import annotations`` makes
    every annotation a string, and ``get_type_hints`` resolves a handler's
    against its *module* globals — so a model defined inside the test function
    does not resolve, the sweep sees a string instead of a type, and the
    control silently measures nothing. Measured: with the class local, the
    planted body field went undetected while the planted query parameter was
    found, and the control read as a half-pass.
    """

    tenant_id: str
    name: str


class TestTheSweep:
    def test_no_route_takes_a_tenant_or_an_actor_from_the_caller(
        self, app: Any
    ) -> None:
        assert sorted(set(_offences(app)) - _EXCUSED) == []

    def test_every_exception_is_actually_present(self, app: Any) -> None:
        """An exception for a field that no longer exists is a stale excuse.

        It would also hide the next one: an unused entry makes the set look
        maintained while the real population drifts underneath it.
        """
        assert _EXCUSED <= set(_offences(app))

    def test_the_sweep_has_a_population(self, app: Any) -> None:
        """Never a count without its positive control.

        An empty route list, a broken enumeration or a signature reader that
        silently returned nothing would all make the assertion above pass
        while measuring nothing.
        """
        endpoints = [
            route
            for _template, route in mounted_routes(app)
            if getattr(route, "endpoint", None) is not None
        ]
        assert len(endpoints) > 20
        parameters = sum(
            len(inspect.signature(route.endpoint).parameters)
            for route in endpoints
        )
        assert parameters > 30

    def test_the_sweep_catches_a_planted_offence(self, app: Any) -> None:
        """The negative control: the detector fires on the defect it names.

        A sweep that returns ``[]`` because it looks in the wrong place is the
        most expensive kind of green. This plants one of each shape — a body
        field and a query parameter — on a throwaway app and asserts both are
        found.
        """
        from fastapi import APIRouter, FastAPI

        from ccf_runtime.authz.refusals import ACTION_HEALTH_READ
        from ccf_runtime.authz.route_declaration import (
            ResourceBinding,
            authorizes,
        )

        router = APIRouter()

        @router.post("/planted-body")
        @authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
        def planted_body(body: _PlantedBody) -> dict[str, str]:
            return {}

        @router.get("/planted-query")
        @authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
        def planted_query(actor: str) -> dict[str, str]:
            return {}

        planted = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        planted.include_router(router, prefix="/sabotage")

        offences = _offences(planted)

        assert len(offences) == 2
        assert any("tenant_id" in offence for offence in offences)
        assert any("actor" in offence for offence in offences)


class TestTheDeletedFieldsStayDeleted:
    @pytest.mark.parametrize(
        ("module", "contract", "field"),
        [
            ("routes.artifact", "ArtifactPutRequest", "tenant_id"),
            ("routes.skill", "GrantRequest", "actor"),
            ("routes.skill", "GrantRevocationRequest", "actor"),
        ],
    )
    def test_the_contract_no_longer_declares_it(
        self, module: str, contract: str, field: str
    ) -> None:
        """Named one by one, because each was a separate finding.

        The sweep above would catch a reintroduction; these say **which**
        field, so a failure reads as *"the artifact tenant came back"* rather
        than as a list.
        """
        import importlib

        loaded = importlib.import_module(f"ccf_runtime.http_api.{module}")
        assert field not in getattr(loaded, contract).model_fields

    def test_the_contract_still_declares_what_it_should(self) -> None:
        """The positive control: the contracts were narrowed, not emptied."""
        from ccf_runtime.http_api.routes.artifact import ArtifactPutRequest
        from ccf_runtime.http_api.routes.skill import (
            GrantRequest,
            GrantRevocationRequest,
        )

        assert set(ArtifactPutRequest.model_fields) == {
            "artifact_class",
            "name",
            "artifact",
        }
        assert set(GrantRequest.model_fields) == {
            "grant",
            "definition_key",
            "definition_version",
        }
        assert set(GrantRevocationRequest.model_fields) == {"grant_hash"}


class TestEveryExceptionIsEnforcedAtItsDoor:
    """A field this tree cannot delete is a field this tree refuses to obey."""

    def test_a_hitl_submission_naming_another_tenant_is_refused(
        self, gate_app: Any, fabric: Fabric
    ) -> None:
        from .gate_fixtures import probe

        response = probe(
            gate_app.app,
            "POST",
            "/hitl/actions",
            headers=gate_app.auth(),
            json={
                "event_key": "sweep-event",
                "tenant": "some-other-tenant",
                "action": "approve",
                "principal": {
                    "approver": {
                        "subject_id": "gate-caller",
                        "identity_provider_ref": "idp://sweep",
                    },
                    "authentication": {
                        "method": "bearer-token",
                        "assurance_level": "dev",
                        "session_ref": "sweep-1",
                    },
                    "action_time": "2026-07-30T12:00:00+00:00",
                    "product_content_hash": "0" * 64,
                },
                "annotation": None,
            },
        )
        # D-IMPL-353 §1.3: the body has no tenant field at all (the tenant is
        # the capability's), so naming one is a malformed body that names the
        # field — refused before any comparison, and nothing lands.
        assert response.status_code == 422
        assert "tenant" in response.text
        assert fabric.hitl.submissions(tenant="some-other-tenant") == ()

    def test_a_catalog_entry_naming_another_tenant_is_refused(
        self, gate_app: Any, fabric: Fabric
    ) -> None:
        from ccf.contracts.canonical import canonical_bytes

        from .gate_fixtures import probe

        entry = next(iter(fabric.catalog.discover()))
        foreign = entry.model_copy(update={"tenant": "some-other-tenant"})
        response = probe(
            gate_app.app,
            "POST",
            "/skill/catalog",
            content=canonical_bytes(foreign),
            headers={
                **gate_app.auth(),
                "content-type": "application/json",
            },
        )
        assert response.status_code == 403

    def test_the_same_entry_under_its_own_tenant_is_not_refused(
        self, gate_app: Any, fabric: Fabric
    ) -> None:
        """The positive control: the refusal is about the tenant, not the shape."""
        from ccf.contracts.canonical import canonical_bytes

        from .gate_fixtures import probe

        entry = next(iter(fabric.catalog.discover()))
        own = entry.model_copy(update={"tenant": gate_app.tenant})
        response = probe(
            gate_app.app,
            "POST",
            "/skill/catalog",
            content=canonical_bytes(own),
            headers={
                **gate_app.auth(),
                "content-type": "application/json",
            },
        )
        assert response.status_code != 403, response.text


class TestThePermittedAppearance:
    def test_the_only_tenant_name_left_is_a_path_segment(
        self, app: Any
    ) -> None:
        """And it is the product address's, which the gate holds to the grant."""
        carrying = [
            template
            for template, _route in mounted_routes(app)
            if TENANT_PATH_PARAM in _path_parameters(template)
        ]
        assert carrying == ["/product/{tenant}/{product_class}/{version}"]
