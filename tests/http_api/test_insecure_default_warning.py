"""D-IMPL-73 — ``CcfInsecureDefaultWarning`` behavior (Phase 10, D-15).

The ruled mechanism, asserted exactly:

- ``create_app`` with ``auth=None`` and no acknowledgment emits a
  ``CcfInsecureDefaultWarning`` (a ``UserWarning`` subclass, exported so
  ``pytest.warns`` and ``-W error::…`` can target it) at construction,
  plus a once-only ``logging`` WARNING record at the first served
  request.
- The single suppression surface is the explicit
  ``acknowledge_insecure_default=True`` kwarg — no environment variable.
- ``auth`` bound => neither emission, regardless of the kwarg.
- ``AUTH_POSTURE_SENTENCE`` stays byte-identical (07-10 Task 2 pin).
"""

from __future__ import annotations

import asyncio
import logging
import warnings
from pathlib import Path
from typing import Any

import httpx
import pytest

from ccf_runtime.http_api.app import (
    AUTH_POSTURE_SENTENCE,
    CcfInsecureDefaultWarning,
    create_app,
)
from ccf_runtime.http_api.dependencies import ApiDependencies

from .conftest import Fabric


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


def call(app: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(go())


class TestConstructionWarning:
    def test_bare_construction_warns(self, fabric: Fabric) -> None:
        with pytest.warns(CcfInsecureDefaultWarning):
            create_app(_deps(fabric))

    def test_category_is_user_warning_subclass(self) -> None:
        assert issubclass(CcfInsecureDefaultWarning, UserWarning)

    def test_acknowledgment_kwarg_suppresses(self, fabric: Fabric) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", CcfInsecureDefaultWarning)
            create_app(_deps(fabric), acknowledge_insecure_default=True)

    def test_auth_bound_never_warns(
        self, fabric: Fabric, tmp_path: Path
    ) -> None:
        import json

        from ccf_runtime.http_api.auth import BearerTokenAuth
        from ccf_runtime.mcp.auth import FileTokenSource

        token_file = tmp_path / "tokens.json"
        token_file.write_text(
            json.dumps({"t": {"client_id": "a", "scopes": ["hitl"]}}),
            encoding="utf-8",
        )
        auth = BearerTokenAuth(token_source=FileTokenSource(path=token_file))
        with warnings.catch_warnings():
            warnings.simplefilter("error", CcfInsecureDefaultWarning)
            create_app(_deps(fabric), auth=auth)
            # The kwarg is irrelevant once auth is bound.
            create_app(
                _deps(fabric), auth=auth, acknowledge_insecure_default=False
            )


class TestFirstRequestLogRecord:
    def test_exactly_one_warning_record_across_two_requests(
        self, fabric: Fabric, caplog: pytest.LogCaptureFixture
    ) -> None:
        with pytest.warns(CcfInsecureDefaultWarning):
            app = create_app(_deps(fabric))
        with caplog.at_level(logging.WARNING, logger="ccf_runtime.http_api"):
            assert call(app, "GET", "/health").status_code == 200
            assert call(app, "GET", "/health").status_code == 200
        records = [
            r
            for r in caplog.records
            if r.name == "ccf_runtime.http_api"
            and r.levelno == logging.WARNING
        ]
        assert len(records) == 1

    def test_zero_records_after_acknowledgment(
        self, fabric: Fabric, caplog: pytest.LogCaptureFixture
    ) -> None:
        app = create_app(_deps(fabric), acknowledge_insecure_default=True)
        with caplog.at_level(logging.WARNING, logger="ccf_runtime.http_api"):
            assert call(app, "GET", "/health").status_code == 200
            assert call(app, "GET", "/health").status_code == 200
        records = [
            r
            for r in caplog.records
            if r.name == "ccf_runtime.http_api"
            and r.levelno == logging.WARNING
        ]
        assert records == []


class TestPostureSentenceUnchanged:
    def test_auth_posture_sentence_is_byte_identical(self) -> None:
        assert AUTH_POSTURE_SENTENCE == (
            "This API performs no authentication or authorization in v0:"
            " every request acts with the full authority of the injected"
            " fabric handles, it must be deployed inside the tenant trust"
            " boundary, and any future authentication is a new contract,"
            " not a configuration of this one."
        )
