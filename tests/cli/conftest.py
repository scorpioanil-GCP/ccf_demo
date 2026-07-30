"""Shared fabric for the `ccf` CLI tests (07-11; EXPR-02; D-IMPL-22).

Reuses the HTTP API test fabric wholesale: the CLI is a thin client over
that surface, so the correct test substrate is *the same* injected
``ApiDependencies`` bundle the HTTP tests drive — sharing the fabric is
itself part of the claim (zero privileged paths: nothing the CLI reaches
exists outside the bundle both front doors hold).

Every CLI invocation here goes through ``ccf_runtime.cli.main.main`` with
the bundle injected (in-process ASGI transport — no server hosted), except
the one equivalence test that deliberately hosts uvicorn on loopback to
prove the HTTP path and the injected path produce identical output.
"""

from __future__ import annotations

from typing import Any

import pytest

from http_api.conftest import Fabric


@pytest.fixture(scope="module")
def fabric(tmp_path_factory: pytest.TempPathFactory) -> Fabric:
    return Fabric(tmp_path_factory.mktemp("cli-fabric"))


@pytest.fixture(scope="module")
def deps(fabric: Fabric) -> Any:
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


def run_cli(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    *,
    dependencies: Any = None,
) -> tuple[int, str, str]:
    """One CLI invocation; returns (exit_code, stdout, stderr)."""
    from ccf_runtime.cli.main import main

    code = main(argv, dependencies=dependencies)
    captured = capsys.readouterr()
    return code, captured.out, captured.err
