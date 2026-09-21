"""The two doors of `examples/cp-19-aml-typology-match`, exercised.

**These tests claim NO declared gate.** `CP-SPEC-019` §G.1 declares fourteen
gates and none of them is about a door: the specification was written for the
product, and the door was built because the tree ships one. A shipped door
that nothing opens passes every test there is (`D-IMPL-324`), so the
measurement is kept executable here rather than left as a README claim.
Recorded as `ATM-F-14`.

Three credentials reach ONE standard MCP door and receive three perspectives,
three content addresses and three shapes; the fourth credential is recognized,
granted nothing, and refused with the minimal shell. Over HTTP the same opened
product serves the one behavior MCP cannot expose — a REQUESTED perspective,
refused rather than downgraded when the grant does not permit it.

**Reads the estate, seeds nothing** (CLAUDE.md §9). No credential value is
printed and nothing here pins an estate figure.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import httpx
import pytest
import yaml
from ccf.contracts.canonical import canonical_bytes
from ccf.mcp.client import run_with_session
from ccf.products.door import WireRequest
from ccf.products.product import OpenedProduct
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL
from mcp import ClientSession
from mcp.types import TextContent

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-19-aml-typology-match"

ESTATE_VARIABLES = (
    "CCF_CP_19_SQLITE_PATH", "CCF_CP_19_POSTGRES_DSN", "CCF_CP_19_POSTGRES_SCHEMA",
    "CCF_CP_19_FLUREE_URL", "CCF_CP_19_FLUREE_LEDGER", "CCF_CP_19_MONGO_URI",
    "CCF_CP_19_MONGO_DB", "CCF_CP_19_TOKEN_L1", "CCF_CP_19_TOKEN_L2",
    "CCF_CP_19_TOKEN_EXAMINER", "CCF_CP_19_TOKEN_UNGRANTED",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
PARAMETERS = {"as_of": QUESTION["instants"]["AS_OF_LATE"], "network_depth": "2"}

#: The loopback base the in-process ASGI transport is addressed at. No socket
#: is bound; the transport dispatches straight into the app.
BASE = "http://127.0.0.1:8129"
GRANTED = ("PRIN-AML-L1", "PRIN-AML-L2", "PRIN-AML-EXAM")
UNGRANTED = "PRIN-AML-XXX"


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate and the four credentials, read-only."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-19 estate or its credentials are not configured: {', '.join(missing)} unset"
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import produce  # noqa: PLC0415
        from server import serve  # noqa: PLC0415

        assert pathlib.Path(produce.__file__).parent == tree, "the eviction did not hold"
        yield {"produce": produce, "serve": serve}
    finally:
        sys.path.remove(str(tree))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


@pytest.fixture(scope="module")
def modules() -> Iterator[dict[str, Any]]:
    with _tree_modules(EXAMPLE) as loaded:
        yield loaded


@pytest.fixture(scope="module")
def opened(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> Iterator[OpenedProduct]:
    """One opened product, serving BOTH doors — which is the point of the pair."""
    with modules["produce"].product(tmp_path_factory.mktemp("cp19-door")) as product:
        yield product


@pytest.fixture(scope="module")
def tokens(opened: OpenedProduct) -> dict[str, str]:
    """`principal_id` → its bearer credential, read from the deployment's own
    source map so no credential is named by environment variable here."""
    import deployment  # noqa: PLC0415

    grants = deployment.credential_grants(opened.sources)
    by_principal = {principal: token for token, principal in grants.items()}
    assert set(by_principal) == {*GRANTED, UNGRANTED}, sorted(by_principal)
    return by_principal


def _arguments(opened: OpenedProduct) -> dict[str, Any]:
    wire = WireRequest(
        product_id=opened.declaration.schema_name, parameters=PARAMETERS, temporal_boundary=ASKED_AT
    )
    return {
        "tenant": opened.tenant_id, "product_class": opened.declaration.schema_name,
        "version": opened.declaration.schema_version,
        "request": canonical_bytes(wire).decode("utf-8"), "subject": SUBJECT,
        "intent": INTENT, "freshness": FRESHNESS, "asked_at": ASKED_AT.isoformat(),
        "parameters": PARAMETERS,
    }


def _through_the_mcp_door(server: Any, tokens: dict[str, str], arguments: dict[str, Any]) -> dict[str, Any]:
    """One tool call per credential against one running door; outcomes as data."""
    app = server.streamable_http_app()

    async def call(session: ClientSession) -> str:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, dict(arguments))
        return " | ".join(part.text for part in result.content if isinstance(part, TextContent))

    async def go() -> dict[str, Any]:
        outcomes: dict[str, Any] = {}
        async with app.router.lifespan_context(app):
            for principal, token in tokens.items():
                def factory(token: str = token) -> httpx.AsyncClient:
                    return httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app), base_url=BASE,
                        headers={"Authorization": f"Bearer {token}"},
                    )

                outcomes[principal] = json.loads(
                    await run_with_session(url=f"{BASE}/mcp", operation=call, http_client_factory=factory)
                )
        return outcomes

    return asyncio.run(go())


def _http(app: Any, opened: OpenedProduct, token: str, *, role: str | None = None) -> httpx.Response:
    url = f"/product/{opened.tenant_id}/{opened.declaration.schema_name}/{opened.declaration.schema_version}"
    query: dict[str, str] = {
        "subject": SUBJECT, "intent": INTENT, "freshness": FRESHNESS,
        "asked_at": ASKED_AT.isoformat(), "parameters": json.dumps(PARAMETERS),
    }
    if role is not None:
        query["role"] = role

    async def go() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://fabric.invalid"
        ) as client:
            return await client.get(url, params=query, headers={"Authorization": f"Bearer {token}"})

    return asyncio.run(go())


@pytest.fixture(scope="module")
def served(modules: dict[str, Any], opened: OpenedProduct, tokens: dict[str, str]) -> dict[str, Any]:
    door = modules["serve"].open_aml_door(opened)
    server = door.server(issuer_url="https://issuer.example", resource_server_url="https://door.example/mcp")
    return _through_the_mcp_door(server, tokens, _arguments(opened))


# --- no gate: four credentials, one door -------------------------------------------


def test_four_credentials_reach_one_door_and_three_receive_their_own_product(
    modules: dict[str, Any], served: dict[str, Any]
) -> None:
    """Three grants, three perspectives, three addresses; the fourth is refused.

    Claims no gate (`ATM-F-14`). The assertions are relationships between the
    four answers one door gave — the addresses differ, the shapes differ, the
    SAR member follows the perspective, and the ungranted credential's shell
    names nothing it was not entitled to.
    """
    PERSPECTIVE_BY_PRINCIPAL = modules["serve"].PERSPECTIVE_BY_PRINCIPAL
    addresses: dict[str, str] = {}
    shapes: dict[str, frozenset[str]] = {}
    for principal in GRANTED:
        outcome = served[principal]
        assert outcome.get("product_json"), outcome
        product = json.loads(outcome["product_json"])
        addresses[principal] = outcome["content_address"]
        shapes[principal] = frozenset(product["payload"])
        # The perspective is the DOOR's, decided from the verified credential.
        # The request named none, and the deployment's declared mapping is the
        # authority — read here rather than restated as a literal.
        assert product["payload"]["perspective"] == PERSPECTIVE_BY_PRINCIPAL[principal]
    assert len(set(addresses.values())) == len(GRANTED), addresses
    assert len(set(shapes.values())) == len(GRANTED), {k: sorted(v) for k, v in shapes.items()}
    # The SAR member follows the perspective across the wire, exactly as it does
    # in process: absent for the L1 analyst, present for the other two.
    assert "sar_filing_history" not in shapes["PRIN-AML-L1"]
    assert all("sar_filing_history" in shapes[p] for p in ("PRIN-AML-L2", "PRIN-AML-EXAM"))

    refused = served[UNGRANTED]
    assert not refused.get("product_json"), "a credential with no grant was served"
    shell = refused["refusal"]
    assert shell["kind"] == "subject-unavailable" and shell["disclosure"] == "minimal"
    assert shell.get("replay_reference"), "the refusal carries no replay reference"
    rendered = json.dumps(refused)
    for leaked in (UNGRANTED, "no-projection-plan", "unmapped"):
        assert leaked not in rendered, f"the wire shell names `{leaked}`"


# --- no gate: the HTTP door, and the one behavior MCP cannot expose -------------------


def test_a_requested_perspective_outside_the_grant_is_refused_not_downgraded(
    modules: dict[str, Any], opened: OpenedProduct, tokens: dict[str, str], served: dict[str, Any]
) -> None:
    """Over HTTP a caller may ASK for a role. A role its grant does not permit
    is refused with the same minimal shell a nonexistent product would get —
    never silently served at the role the credential does hold.

    Claims no gate (`ATM-F-14`). The positive control is the same credential
    asking for its own role: served, and byte-identical to what the MCP door
    returned for the same question — one opened product, two doors, one answer.
    """
    app = modules["serve"].http_app(opened)
    analyst = tokens["PRIN-AML-L1"]

    reaching_up = _http(app, opened, analyst, role="examiner")
    assert reaching_up.status_code == 404, reaching_up.text
    body = reaching_up.json()
    assert body["kind"] == "subject-unavailable"
    assert body["refusal"]["disclosure"] == "minimal"
    assert "examiner" not in reaching_up.text, "the refusal echoes the role it refused"

    own = _http(app, opened, analyst, role="l1")
    assert own.status_code == 200, own.text
    assert own.content == served["PRIN-AML-L1"]["product_json"].encode("utf-8"), (
        "the HTTP door and the MCP door disagree on the bytes of one answer"
    )

    ungranted = _http(app, opened, tokens[UNGRANTED])
    assert ungranted.status_code == 404, ungranted.text
    assert ungranted.json()["kind"] == "subject-unavailable"

    unknown = _http(app, opened, "not-a-credential-this-door-knows")
    assert unknown.status_code == 401, unknown.text
    assert "unauthenticated" in unknown.text
