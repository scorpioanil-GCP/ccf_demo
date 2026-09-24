"""The gate is TOTAL: every request reaches it, whatever its shape (SEC-001).

TDD RED for Lane HTTP Task 1. The measurement that forced this shape, taken
against this repository's own ``fastapi==0.140.0`` / ``starlette==1.3.1`` and
reproduced by :func:`test_an_app_level_dependency_is_not_total` below:

* a ``FastAPI(dependencies=[Depends(guard)])`` gate ran on **1 of 7** probes —
  it never ran for a malformed JSON body (422 from body validation, decided
  *before* the dependency), for ``GET /openapi.json`` (200, the full API
  document), for ``GET /docs`` (200), for a 404, for a trailing-slash redirect,
  or for a route mounted after construction;
* a middleware in front of the whole application ran on **7 of 7**.

So the gate is a middleware, and it has **no path carve-outs**. A carve-out
list is another applicability switch of exactly the class this remediation has
already found twice: whoever chooses the path chooses whether the check runs.
``/health``, ``/docs``, ``/openapi.json`` and ``/redoc`` are therefore not
exempt — they each **declare an action id of their own** and the deployment's
scope mapping decides, which is a statement in a versioned artifact rather than
a branch in SDK code.

The consequence is stated rather than discovered: a liveness probe must carry a
credential the deployment recognises, and a deployment that wants an open
liveness endpoint grants that action to the probe's scope. The alternative is a
carve-out, and a carve-out is a switch.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from .gate_fixtures import GateApp, probe


class _ProbeBody(BaseModel):
    """A body model for the negative control below.

    **Module scope on purpose.** ``from __future__ import annotations`` makes
    every annotation a string, and FastAPI resolves a handler's annotations
    against its *module* globals — so a body model defined inside the test
    function does not resolve, the parameter is read as a query parameter
    instead of a body, and the control then measures a route with no body
    validation at all. Measured: the same negative control reported the
    dependency firing on a malformed body (401) with the class local, and not
    firing (422) with it here. A control that quietly changes its own subject
    is worse than no control.
    """

    x: int

#: The seven request shapes the measurement covers. Each is a shape that an
#: in-router gate has been observed to miss, plus the two plain ones as the
#: positive control that the probe set is not all-negative.
PROBES: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("GET", "/health", {}),
    ("GET", "/hitl/queue", {}),
    (
        "POST",
        "/hitl/actions",
        {
            "content": b"{not json",
            "headers": {"content-type": "application/json"},
        },
    ),
    ("GET", "/openapi.json", {}),
    ("GET", "/docs", {}),
    ("GET", "/no-such-route", {}),
    ("GET", "/hitl/queue/", {}),
)


class TestTotality:
    def test_every_probe_is_refused_without_a_credential(
        self, gate_app: GateApp
    ) -> None:
        """No shape of request reaches a handler unauthenticated."""
        reached = [
            (method, url)
            for method, url, kwargs in PROBES
            if probe(gate_app.app, method, url, **kwargs).status_code != 401
        ]
        assert reached == [], (
            "these request shapes reached past the gate unauthenticated"
        )

    def test_every_probe_is_refused_for_an_unauthorized_grant(
        self, gate_app: GateApp
    ) -> None:
        """A recognised credential that authorizes nothing reaches nothing."""
        reached = [
            (method, url)
            for method, url, kwargs in PROBES
            if probe(
                gate_app.app,
                method,
                url,
                **{
                    **{k: v for k, v in kwargs.items() if k != "headers"},
                    "headers": {
                        **kwargs.get("headers", {}),
                        "Authorization": (
                            f"Bearer {gate_app.token_nothing}"
                        ),
                    },
                },
            ).status_code
            != 403
        ]
        assert reached == [], (
            "these request shapes reached past the gate unauthorized"
        )

    def test_the_openapi_document_is_not_served_unauthenticated(
        self, gate_app: GateApp
    ) -> None:
        """The API's own description is a disclosure, and it is gated."""
        response = probe(gate_app.app, "GET", "/openapi.json")
        assert response.status_code == 401
        assert "paths" not in response.text

    def test_a_malformed_body_is_refused_before_validation(
        self, gate_app: GateApp
    ) -> None:
        """422 means body validation ran first, which means the gate did not."""
        response = probe(
            gate_app.app,
            "POST",
            "/hitl/actions",
            content=b"{not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 401


class TestTheMeasurementThatForcedTheShape:
    """The negative control, executable rather than quoted."""

    def test_an_app_level_dependency_is_not_total(self) -> None:
        import asyncio

        import httpx
        from fastapi import APIRouter, Depends, FastAPI, HTTPException

        fired: list[str] = []

        def guard() -> None:
            fired.append("dep")
            raise HTTPException(status_code=401, detail="guard")

        app = FastAPI(dependencies=[Depends(guard)])
        router = APIRouter()

        @router.post("/thing")
        def thing(body: _ProbeBody) -> dict[str, str]:
            return {"ok": "yes"}

        app.include_router(router, prefix="/n")

        async def go() -> list[int]:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://probe.invalid"
            ) as client:
                statuses = []
                for method, url, kwargs in (
                    (
                        "POST",
                        "/n/thing",
                        {
                            "content": b"{not json",
                            "headers": {"content-type": "application/json"},
                        },
                    ),
                    ("GET", "/openapi.json", {}),
                    ("GET", "/docs", {}),
                ):
                    fired.clear()
                    response = await client.request(method, url, **kwargs)
                    statuses.append(response.status_code)
                    assert fired == [], f"{method} {url} ran the dependency"
                return statuses

        assert asyncio.run(go()) == [422, 200, 200]


class TestNothingTheCallerSendsDecidesWhetherTheCheckRuns:
    """The applicability question, asked of every input a caller controls.

    *A guard whose applicability the caller decides is not a guard.* This
    class is the systematic version of that sentence: for each thing a caller
    chooses — the method, the path shape, a duplicated parameter, a missing
    one, an unparseable body — the check still runs and the answer is a
    refusal rather than a pass-through.
    """

    def test_a_duplicated_query_parameter_is_refused(
        self, gate_app: GateApp
    ) -> None:
        """Parameter pollution is a bypass shape, and it is closed by refusing.

        Two values for the declared resource parameter would let a caller
        present one for the gate to authorize and leave the router free to
        read the other. Which end reads which is a property of two libraries'
        parsing, so the gate refuses rather than betting on it.

        What would fail here: the gate taking ``values[0]`` or ``values[-1]``.
        """
        one = probe(
            gate_app.app,
            "GET",
            "/agent/versions?key=gate-authorized",
            headers=gate_app.auth(),
        )
        two = probe(
            gate_app.app,
            "GET",
            "/agent/versions?key=gate-authorized&key=something-else",
            headers=gate_app.auth(),
        )

        assert one.status_code == 200
        assert two.status_code == 403

    def test_an_absent_declared_query_parameter_is_refused(
        self, gate_app: GateApp
    ) -> None:
        """Omitting the resource does not omit the check."""
        assert (
            probe(
                gate_app.app, "GET", "/agent/versions", headers=gate_app.auth()
            ).status_code
            == 403
        )

    def test_an_unparseable_body_is_refused_before_the_handler(
        self, gate_app: GateApp
    ) -> None:
        """Not 422: the gate decides before any schema is consulted."""
        assert (
            probe(
                gate_app.app,
                "POST",
                "/config/registrations",
                content=b"{not json",
                headers={
                    **gate_app.auth(),
                    "content-type": "application/json",
                },
            ).status_code
            == 403
        )

    def test_a_wrong_method_on_a_real_path_is_refused_not_405(
        self, gate_app: GateApp
    ) -> None:
        """A 405 would disclose that the path exists to a caller with no claim."""
        assert (
            probe(
                gate_app.app, "DELETE", "/health", headers=gate_app.auth()
            ).status_code
            == 403
        )

    def test_a_buffered_body_still_reaches_the_handler_intact(
        self, gate_app: GateApp
    ) -> None:
        """The gate reads bodies to authorize on them; it must not consume them.

        What would fail here: the replayed receive channel dropping the body,
        at which point every ``BODY``-sourced route would 422 on an empty
        payload — a failure that looks like a schema problem and is not.
        """
        response = probe(
            gate_app.app,
            "POST",
            "/config/registrations",
            headers=gate_app.auth(),
            json={
                "key": "gate-buffered-key",
                "class_id": "ccf.prompt-artifact",
                "artifact": {"not": "a valid prompt artifact"},
            },
        )
        # 422 from the *artifact parser*, which only runs if the body arrived.
        assert response.status_code == 422
        assert "gate-buffered-key" not in response.text
