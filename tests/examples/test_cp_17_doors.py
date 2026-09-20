"""The doors of `examples/cp-17-mnpi-wall-enforcement` — `MWE-G14`, `MWE-G15`, `MWE-G18`.

Four credentials behind ONE standard MCP door, and the same opened product
over HTTP, driven in-process the way `run.py --door` serves them: the door's
own ASGI app under one lifespan, one `run_with_session` per credential, and
`httpx.ASGITransport` for the HTTP route. Nothing here reads a token value
at import — the credentials come off the opened product's environment, by
the names `ccf_environment.yaml` declares, inside a fixture.

What the module writes down are relationships: the unconfigured principal's
wire shell equals the shell an entitled credential gets for a product that
does not exist, while the record behind it carries the typed code; a role
asked for over HTTP outside the grant is refused rather than served at the
grant's role, and a granted role's HTTP bytes equal the MCP vessel; two door
calls and the in-process run hash to one address. No estate count and no
date is pinned (CLAUDE.md §9); the instants come from `artifacts/question.yaml`.

**Reads the estate, seeds nothing.**
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import pytest
import yaml
from mcp import ClientSession
from mcp.types import TextContent

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.mcp.client import run_with_session
from ccf.products.disclosure import DISCLOSURE_MINIMAL, WITHHELD
from ccf.products.door import WireRequest
from ccf.products.product import OpenedProduct
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope, SubjectUnavailableRefusal
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_ROLE_UNGRANTED,
    ERROR_UNAUTHENTICATED,
)
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND
from ccf_runtime.http_api.routes import REPLAY_REF_HEADER
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-17-mnpi-wall-enforcement"

ESTATE_VARIABLES = (
    "CCF_CP_17_SQLITE_PATH",
    "CCF_CP_17_POSTGRES_DSN", "CCF_CP_17_POSTGRES_SCHEMA",
    "CCF_CP_17_FLUREE_URL", "CCF_CP_17_FLUREE_LEDGER",
    "CCF_CP_17_MONGO_URI", "CCF_CP_17_MONGO_DB",
    "CCF_CP_17_TOKEN_COVERAGE", "CCF_CP_17_TOKEN_RESEARCH",
    "CCF_CP_17_TOKEN_TRADER", "CCF_CP_17_TOKEN_KYC",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server", "server.serve")

#: The four principals `ccf_v2.principal` declares (`CP-SPEC-017` §C.1); the
#: fourth holds a credential and no grant. Their roles are READ off the estate.
COVERAGE = "PRIN-COV-001"
RESEARCH = "PRIN-RES-002"
TRADER = "PRIN-TRD-003"
KYC = "PRIN-KYC-004"
ENTITLED = (COVERAGE, RESEARCH, TRADER)

#: The demonstration question — the caller's vocabulary, from the artifact.
QUESTION: Mapping[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
T1 = datetime.fromisoformat(QUESTION["instants"]["T1"])

#: Inert in-process: FastMCP's DNS-rebinding guard admits `127.0.0.1:*`.
IN_PROCESS_BASE_URL = "http://127.0.0.1:8126"
HTTP_BASE_URL = "http://fabric.invalid"
ISSUER = {"issuer_url": "https://issuer.example", "resource_server_url": "https://door.example/mcp"}

SUBJECT_UNAVAILABLE = REFUSAL_KINDS[SubjectUnavailableRefusal]
HTTP_UNAUTHORIZED = int(httpx.codes.UNAUTHORIZED)


# --- fixtures and helpers -----------------------------------------------------------


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    """One example tree's modules, whatever ran before — evicted in and out."""
    saved = {n: sys.modules.pop(n, None) for n in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415
        from server import serve  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        assert pathlib.Path(serve.__file__).parent.parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment, "produce": produce, "projection": projection, "serve": serve}
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
    """The declared product, opened ONCE; every question mints its own substrate."""
    with modules["produce"].product(tmp_path_factory.mktemp("doors")) as product:
        yield product


@pytest.fixture(scope="module")
def tokens(estate: None, modules: dict[str, Any], opened: OpenedProduct) -> Mapping[str, str]:
    """`principal_id` → bearer credential, off the opened product's environment."""
    credentials: Mapping[str, str] = opened.sources[modules["deployment"].SOURCE_CREDENTIALS]
    assert set(credentials) == {*ENTITLED, KYC}, sorted(credentials)
    return dict(credentials)


@pytest.fixture(scope="module")
def roles(estate: None, modules: dict[str, Any], opened: OpenedProduct) -> Mapping[str, str]:
    """`principal_id` → declared perspective, from `ccf_v2.principal`."""
    relational = opened.sources[modules["deployment"].SOURCE_RELATIONAL]
    declared: Mapping[str, str] = modules["acquisition"].principal_roles(relational_settings=relational)
    assert set(declared) >= {*ENTITLED, KYC}, sorted(declared)
    assert len({declared[p] for p in ENTITLED}) == len(ENTITLED), "two entitled principals share a role"
    return declared


def _question(opened: OpenedProduct, *, subject: str = SUBJECT, asked_at: datetime = T1, **params: Any) -> Any:
    parameters = {name: value for name, value in params.items() if value is not None}
    return opened.question(subject=subject, asked_at=asked_at, intent=INTENT, freshness=FRESHNESS, parameters=parameters)


def _arguments(
    opened: OpenedProduct, *, subject: str = SUBJECT, asked_at: datetime = T1,
    product_class: str | None = None, **params: Any,
) -> dict[str, Any]:
    """The product tool's arguments for one question: the address and the encoded request, from one source."""
    parameters = {name: value for name, value in params.items() if value is not None}
    schema_name = product_class if product_class is not None else opened.declaration.schema_name
    wire = WireRequest(product_id=schema_name, parameters=parameters, temporal_boundary=asked_at)
    return {
        "tenant": opened.tenant_id, "product_class": schema_name, "version": opened.declaration.schema_version,
        "request": canonical_bytes(wire).decode("utf-8"), "subject": subject, "intent": INTENT,
        "freshness": FRESHNESS, "asked_at": asked_at.isoformat(), "parameters": parameters,
    }


@dataclass(frozen=True)
class _Wire:
    """One MCP answer: the tool's error flag, the text as it crossed, and the outcome it decodes to."""

    is_error: bool
    text: str

    @property
    def outcome(self) -> Mapping[str, Any]:
        return json.loads(self.text)

    @property
    def refusal(self) -> Mapping[str, Any]:
        shell = self.outcome.get("refusal")
        assert shell is not None, f"no refusal on the door outcome: `{self.text[:200]}`"
        return dict(shell)


def _tool_call(arguments: Mapping[str, Any]) -> Callable[[ClientSession], Awaitable[_Wire]]:
    async def operation(session: ClientSession) -> _Wire:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, dict(arguments))
        return _Wire(bool(result.isError), " | ".join(c.text for c in result.content if isinstance(c, TextContent)))

    return operation


def _drive(server: Any, calls: Mapping[str, tuple[str, Mapping[str, Any]]]) -> dict[str, _Wire]:
    """Every call against the door's own ASGI app, in ONE lifespan, one session per credential."""
    app = server.streamable_http_app()

    async def go() -> dict[str, _Wire]:
        out: dict[str, _Wire] = {}
        async with app.router.lifespan_context(app):
            for name, (token, arguments) in calls.items():
                def factory(token: str = token) -> httpx.AsyncClient:
                    return httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app), base_url=IN_PROCESS_BASE_URL,
                        headers={"Authorization": f"Bearer {token}"},
                    )

                out[name] = await run_with_session(url=f"{IN_PROCESS_BASE_URL}/mcp", operation=_tool_call(arguments), http_client_factory=factory)
        return out

    return asyncio.run(go())


@pytest.fixture(scope="module")
def mcp(estate: None, modules: dict[str, Any], opened: OpenedProduct, tokens: Mapping[str, str]) -> Mapping[str, _Wire]:
    """The demonstration question under every credential through the standard
    door — the banker twice, and once for a product class that does not exist."""
    door = modules["serve"].open_wall_door(opened)
    server = door.server(**ISSUER)
    asked = _arguments(opened)
    absent = _arguments(opened, product_class=f"{opened.declaration.schema_name}-declared-nowhere")
    return _drive(server, {
        "coverage": (tokens[COVERAGE], asked),
        "coverage-again": (tokens[COVERAGE], asked),
        "research": (tokens[RESEARCH], asked),
        "trader": (tokens[TRADER], asked),
        "kyc": (tokens[KYC], asked),
        "coverage-no-such-product": (tokens[COVERAGE], absent),
    })


@pytest.fixture(scope="module")
def http(estate: None, modules: dict[str, Any], opened: OpenedProduct) -> Any:
    """The HTTP door over the SAME opened product, tokens and recorder."""
    return modules["serve"].http_app(opened)


def _get(app: Any, opened: OpenedProduct, *, token: str, role: str | None = None, subject: str = SUBJECT) -> httpx.Response:
    url = f"/product/{opened.tenant_id}/{opened.declaration.schema_name}/{opened.declaration.schema_version}"
    query: dict[str, str] = {"subject": subject, "intent": INTENT, "freshness": FRESHNESS, "asked_at": T1.isoformat(), "parameters": "{}"}
    if role is not None:
        query["role"] = role

    async def go() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=HTTP_BASE_URL) as client:
            return await client.get(url, params=query, headers={"Authorization": f"Bearer {token}"})

    return asyncio.run(go())


def _record(opened: OpenedProduct, reference: str) -> DecisionReplayRecord:
    """The decision record a replay reference names, read from the ONE store."""
    address = reference if not reference.startswith("ccf-artifact://") else opened.artifact_store.resolve_uri(uri=reference)
    return DecisionReplayRecord.model_validate_json(opened.artifact_store.get(content_address=address))


def _internal(opened: OpenedProduct, reference: str) -> RefusalEnvelope:
    """The INTERNAL determination behind a disclosed shell's reference."""
    return RefusalEnvelope.model_validate_json(_record(opened, reference).content_generation_path.assembly_refusal)


def _value(rendered: Any) -> Any:
    """A disclosed field value, JSON-rendered on the wire or already plain."""
    try:
        return json.loads(rendered) if isinstance(rendered, str) else rendered
    except ValueError:
        return rendered


def _shell(refusal: Mapping[str, Any]) -> tuple[Any, ...]:
    """What a consumer can observe of a refusal: kind, detail, the field set and
    values, the key set, the disclosure level — never the record reference."""
    fields = refusal.get("fields") or {}
    return (
        refusal["kind"], refusal["detail"], refusal.get("disclosure"),
        tuple(sorted((k, _value(v)) for k, v in fields.items())),
        tuple(sorted(k for k in refusal if k != "replay_reference")),
        tuple(sorted(k for k, v in refusal.items() if v is None)),
    )


# --- G14: the unconfigured principal ---------------------------------------------------


def test_the_unconfigured_principal_is_refused_like_a_nonexistent_product(
    mcp: Mapping[str, _Wire], http: Any, opened: OpenedProduct, tokens: Mapping[str, str]
) -> None:
    """`PRIN-KYC-004` holds a credential and no grant: over MCP the tool answers
    without error, the shell is `subject-unavailable` at minimal disclosure with
    both fields withheld, the deny is on the Control Plane's audit log, and the
    record behind the reference carries `principal-not-entitled` — a code no
    byte of the wire names. The shell is the one an entitled credential gets for
    a product class declared nowhere, and the same credential over HTTP gets the
    unavailable status with the one uniform body.

    Declared product gate `MWE-G14` (`CP-SPEC-017` §G.1).
    """
    kyc = mcp["kyc"]
    assert kyc.is_error is False, kyc.text[:300]
    assert kyc.outcome["product_json"] is None and kyc.outcome["content_address"] is None
    shell = kyc.refusal
    assert shell["kind"] == SUBJECT_UNAVAILABLE and shell["disclosure"] == DISCLOSURE_MINIMAL
    assert set(shell["fields"]) == {"cause", "error_code"}
    assert {_value(v) for v in shell["fields"].values()} == {WITHHELD}
    assert shell["replay_reference"], "the refusal carries no record reference"
    for undisclosed in (ERROR_PRINCIPAL_NOT_ENTITLED, "unauthorized", KYC):
        assert undisclosed not in kyc.text, f"the wire names `{undisclosed}`"

    internal = _internal(opened, shell["replay_reference"])
    assert _value(internal.fields["error_code"]) == ERROR_PRINCIPAL_NOT_ENTITLED
    assert _value(internal.fields["cause"]) == "unauthorized"
    assert KYC in internal.detail

    decisions = [e for e in opened.control_plane.audit_events() if isinstance(e, AuthzDecisionAuditEvent) and e.actor == KYC]
    assert decisions, "no `authz_decision` was audited for the unconfigured principal"
    assert not any(e.resolved for e in decisions), "the unconfigured principal was allowed once"

    comparator = mcp["coverage-no-such-product"]
    assert comparator.is_error is False, comparator.text[:300]
    assert _shell(comparator.refusal) == _shell(shell)
    assert comparator.refusal["replay_reference"] != shell["replay_reference"]

    response = _get(http, opened, token=tokens[KYC])
    assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    body = response.json()
    assert set(body) == {"kind", "refusal_type", "refusal"}
    assert body["kind"] == SUBJECT_UNAVAILABLE and body["refusal_type"] == SubjectUnavailableRefusal.__name__
    assert _shell(body["refusal"]) == _shell(shell)
    assert _value(_internal(opened, body["refusal"]["replay_reference"]).fields["error_code"]) == ERROR_PRINCIPAL_NOT_ENTITLED


# --- G15: the requested role over HTTP ---------------------------------------------------


def test_a_requested_role_outside_the_grant_is_refused_never_downgraded(
    mcp: Mapping[str, _Wire], http: Any, opened: OpenedProduct, tokens: Mapping[str, str], roles: Mapping[str, str]
) -> None:
    """`?role=` is a request, and asking is not receiving: the research credential
    asking for the banker's role, and the coverage credential asking for the
    trader's, are refused with the unavailable status — the record carries
    `product-role-ungranted` under the role that was ASKED, never a 200 at the
    grant's own role. Each credential asking for its own role is served, and
    the body is byte-equal to the MCP vessel for the same question. A bearer
    the door does not recognize is unauthenticated before any of this.

    Declared product gate `MWE-G15` (`CP-SPEC-017` §G.1).
    """
    for asker, borrowed in ((RESEARCH, COVERAGE), (COVERAGE, TRADER)):
        assert roles[borrowed] != roles[asker]
        response = _get(http, opened, token=tokens[asker], role=roles[borrowed])
        assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE], response.text[:300]
        body = response.json()
        assert body["kind"] == SUBJECT_UNAVAILABLE and set(body) == {"kind", "refusal_type", "refusal"}
        assert {_value(v) for v in body["refusal"]["fields"].values()} == {WITHHELD}
        reference = body["refusal"]["replay_reference"]
        assert _value(_internal(opened, reference).fields["error_code"]) == ERROR_PRODUCT_ROLE_UNGRANTED
        record = _record(opened, reference)
        assert record.perspective_conditioning.principal_id == asker
        assert record.perspective_conditioning.role == roles[borrowed]

    for asker, wire in ((RESEARCH, mcp["research"]), (TRADER, mcp["trader"])):
        assert wire.is_error is False and wire.outcome["product_json"], wire.text[:300]
        response = _get(http, opened, token=tokens[asker], role=roles[asker])
        assert response.status_code == int(httpx.codes.OK), response.text[:300]
        assert response.content == wire.outcome["product_json"].encode("utf-8")
        served = json.loads(response.content)
        assert served["payload"]["role"] == roles[asker]
        record = _record(opened, response.headers[REPLAY_REF_HEADER])
        assert (record.perspective_conditioning.principal_id, record.perspective_conditioning.role) == (asker, roles[asker])

    stranger = _get(http, opened, token="not-a-credential-this-door-holds")
    assert stranger.status_code == HTTP_UNAUTHORIZED
    assert stranger.json()["detail"]["error_code"] == ERROR_UNAUTHENTICATED


# --- G18: determinism ----------------------------------------------------------------


def test_two_door_calls_and_the_in_process_run_hash_to_one_address(
    mcp: Mapping[str, _Wire], opened: OpenedProduct, roles: Mapping[str, str]
) -> None:
    """Two calls with one credential and one question give one content address,
    one vessel and one record; the banker's MCP vessel equals, member for member, the
    canonical JSON of the vessel this process serves in-process under the same
    perspective at the same instant, and hashes to the door's address.

    Declared product gate `MWE-G18` (`CP-SPEC-017` §G.1).
    """
    first, again = mcp["coverage"], mcp["coverage-again"]
    assert first.is_error is False and again.is_error is False, first.text[:300]
    assert first.outcome["content_address"] and first.outcome["content_address"] == again.outcome["content_address"]
    assert first.outcome["product_json"] == again.outcome["product_json"]
    # content-addressed: two identical decisions reproduce ONE record
    assert first.outcome["replay_ref"] == again.outcome["replay_ref"]

    outcome = opened.answer(_question(opened), perspective=Perspective(principal_id=COVERAGE, role=roles[COVERAGE]))
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
    assert json.loads(canonical_bytes(outcome.product)) == json.loads(first.outcome["product_json"])
    assert content_hash(outcome.product) == first.outcome["content_address"]
    # the equality is not vacuous: another credential's vessel hashes elsewhere
    assert mcp["research"].outcome["content_address"] != first.outcome["content_address"]
