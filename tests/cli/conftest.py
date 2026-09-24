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

from pathlib import Path

import pytest

from http_api.conftest import Fabric
from ccf.products.disclosure import DISCLOSURE_MINIMAL
from http_api.gate_fixtures import SCOPE_EVERYTHING

#: The CLI suite's tenant and its per-boot credential. Deployment values in a
#: test's clothing: named here once so no CLI test invents a second one.
CLI_TENANT = "acme-bank"
CLI_TOKEN = "cli-token"
CLI_TOKENS: dict[str, tuple[Any, ...]] = {
    CLI_TOKEN: ("cli-caller", (SCOPE_EVERYTHING,))
}


@pytest.fixture(scope="module")
def fabric(tmp_path_factory: pytest.TempPathFactory) -> Fabric:
    global _FABRIC_ROOT
    _FABRIC_ROOT = tmp_path_factory.mktemp("cli-fabric")
    return Fabric(_FABRIC_ROOT)


@pytest.fixture(scope="module")
def deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    global _AUTHORITY
    if _AUTHORITY is None:
        _AUTHORITY = cli_authority(fabric, _FABRIC_ROOT)

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


#: Built once by the `deps` fixture from the same Fabric `deps` wraps, so
#: `run_cli` can bind a REAL authority without every call site passing one.
_AUTHORITY: Any = None
_FABRIC_ROOT: Any = None


def cli_authority(fabric: Fabric, root: Path) -> Any:
    """The five seams ``create_app`` requires, for the CLI's in-process leg.

    Every seam is the REAL one — the same `authority` bundle every gate suite
    builds, over this suite's own Fabric. Not a bypass and not a stub: the
    app the CLI drives in-process is built exactly the way every other app
    is, which is the point of `SEC-002`. Assembling doubles here was tried
    and abandoned; each one needed another member of a contract it was
    pretending to satisfy, which is the shape of a test that has started
    lying.
    """
    from datetime import UTC, datetime

    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    from http_api.gate_fixtures import authority
    from http_api.test_product_declared_obligation_409 import (
        _entitlement_registry,
        _recorder,
    )

    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric),
        clock=lambda: datetime(2026, 8, 11, tzinfo=UTC),
    )
    return authority(
        tenant=CLI_TENANT,
        key="cli/mapping",
        grants=CLI_TOKENS,
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role="cli-role"
            )
        ),
        refusal_recorder=_recorder(fabric, root, source=source),
    )


def run_cli(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    *,
    dependencies: Any = None,
    authority: Any = None,
) -> tuple[int, str, str]:
    """One CLI invocation; returns (exit_code, stdout, stderr).

    ``authority`` is the five-seam bundle ``create_app`` requires on the
    in-process leg (SEC-002). It defaults to the suite's own permissive
    bundle rather than to ``None``, because ``None`` would make every CLI
    test measure the refusal instead of the command — but it is a REAL
    authority, not a bypass: the app the CLI drives is built the same way
    every other app is.
    """
    from ccf_runtime.cli.main import main

    from pydantic import SecretStr

    credential = None
    if dependencies is not None:
        if authority is None:
            authority = _AUTHORITY
        # The in-process leg presents a real credential, because the gate is
        # total and an in-process request is a request (SEC-002).
        credential = SecretStr(CLI_TOKEN)
    code = main(
        argv,
        dependencies=dependencies,
        authority=authority,
        credential=credential,
    )
    captured = capsys.readouterr()
    return code, captured.out, captured.err
