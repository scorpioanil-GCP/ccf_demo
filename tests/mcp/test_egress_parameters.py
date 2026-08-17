"""Both parameterised doors carry a client's parameters, and neither is wider.

``D-IMPL-133`` (Dave, 2026-08-14), implemented. The ruling is quoted rather
than paraphrased because its scope is the whole of this module: *"Ruled: both
doors carry ``parameters``. The MCP tool and the HTTP route both accept a
client-supplied mapping and pass it through unvalidated to the resolver.
**Both**, not one: the phase already recorded that a tool wider than the HTTP
door beside it would be the wrong asymmetry, and the same holds inverted."*

Why this module tests **two** doors
-----------------------------------
The MCP tool hard-wired ``parameters={}`` at ``egress.py:588`` and the HTTP
route hard-wired the identical thing at ``product.py:330``, for the identical
recorded reason. Those are the only two sites in ``runtime/`` that build a
:class:`~ccf.products.request.ProductRequest` for a door. Repairing one and not
the other would produce exactly the asymmetry ``D-IMPL-133`` forbids — so the
width-ceiling leg below runs **one shared case table against both real doors**
and holds them to the same verdict. A per-door table lets the two drift, which
is how the doors got here.

What a "verdict" is, and why it is this
----------------------------------------
``D-IMPL-133`` settles what a door's job is: *"A door therefore never needs the
class, because a door never validates. It needs only to carry the mapping
through to the resolver, which holds the class and runs the comparison where it
belongs."* So the thing to measure is **what the door handed the resolver**, put
through the one shared comparison — :func:`~ccf.products.request.refuse_request`
— rather than whatever a door might separately decide. :func:`_verdict` is that:
``"served"`` when the carried request conforms, and otherwise the violation's
own ``reason`` token.

Measuring it this way is what makes the two doors comparable at all. It also
means a door that *coerced* a caller's value would be visible here: the recorded
request would carry the coerced value, and the declared contract would accept it
where it should have refused ``type-mismatch``.

The non-vacuity guard, which is the load-bearing part
------------------------------------------------------
A table containing only *refusing* cases would have passed **before** either
repair: both doors carried ``{}``, so every case reached the resolver as the
same empty mapping and the two doors agreed perfectly while carrying nothing.
That is this repository's recurring defect — a check that stops checking without
going red — so :func:`assert_same_verdicts` **refuses a table in which no case
is served**. The guard is what makes the leg fail against the unrepaired doors
rather than pass vacuously.

The controls (``D-22``)
------------------------
Every assertion here is a function taking its subject as a parameter, and each
control calls *that same function* with a divergent subject — never a copy of
it, and never by editing ``runtime/`` and reverting. A control implemented as an
edit leaves nothing in the tree; a control implemented as a test runs on every
CI run forever.

Tenant, principal, role, class, parameter and token names are test deployment
vocabulary. The SDK holds none of them (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.settings import AuthSettings
from mcp.types import TextContent, TextResourceContents
from pydantic import AnyHttpUrl, AnyUrl

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    refuse_request,
)
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.mcp.auth import (
    FileTokenSource,
    SourceBackedTokenVerifier,
    TokenGrant,
)
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL, build_egress_server

from crossproc.servers.mcp_egress_child import ProductAddress, build_servable_product

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "egress-parameters-token"
PRINCIPAL = "egress-parameters-caller"
SCOPE = "ccf:egress-parameters"
ROLE = "egress-parameters-role"
SERVER_NAME = "ccf-egress-parameters"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 17, tzinfo=UTC)
TOOL_DESCRIPTION = "Ask this test deployment's product class a question."

#: The four §6.3 axes this module asks with, held constant so the only thing
#: moving between cases is the caller's parameter mapping.
SUBJECT = "egress-parameters-subject"
INTENT = "egress-parameters-intent"
FRESHNESS = "egress-parameters-freshness"
ASKED_AT = datetime(2026, 8, 17, 9, 30, tzinfo=UTC)

#: The one required parameter this module's class declares, and one optional
#: sibling. Two rather than one so *undeclared* and *missing* are distinct
#: failures rather than the same failure read twice.
REQUIRED_PARAMETER = "minimum_score"
OPTIONAL_PARAMETER = "region"
UNDECLARED_PARAMETER = "not_declared_by_this_class"

#: Loopback with an explicit port: FastMCP's DNS-rebinding protection allows
#: ``127.0.0.1:*`` even over ASGI, where no socket exists. Nothing binds it.
IN_PROCESS_BASE_URL = "http://127.0.0.1:8126"

#: ``"served"``, or a :data:`~ccf.products.request.ProductRequestViolationReason`.
Verdict = str

#: Answer one parameter case with a verdict. The unit both doors are compared
#: as, and the unit a control substitutes a divergent implementation of.
AskDoor = Callable[[Mapping[str, Any]], Verdict]

#: The verdict a conforming request produces. Named so the non-vacuity guard,
#: the case table and the controls all say the same string.
SERVED: Verdict = "served"


# ---------------------------------------------------------------------------
# The shipped assertions — functions over their subjects (D-22).
# ---------------------------------------------------------------------------


def assert_same_verdicts(
    cases: Sequence[Mapping[str, Any]],
    ask_mcp: AskDoor,
    ask_http: AskDoor,
) -> None:
    """Both doors reach the same verdict on every case in one shared table.

    ``D-IMPL-133``'s *"both, not one"*, executable. The table is shared rather
    than per-door because two tables are two things to keep in step, and the
    doors reached their current state by drifting apart one edit at a time.

    **The non-vacuity guard is the point.** A table whose every case refuses
    would pass against two doors that carried nothing at all — which is exactly
    what both doors did before ``D-IMPL-133`` was implemented, and exactly the
    "check that stops checking without going red" failure this repository has
    shipped repeatedly. So a table with no served case is refused by name.

    Args:
        cases: The parameter mappings, each asked of both doors.
        ask_mcp: The MCP tool, as a callable answering one case with a verdict.
        ask_http: The HTTP route, in the same shape.

    Raises:
        AssertionError: the table was empty, no case was served, or the two
            doors disagreed about any case.
    """
    if not cases:
        raise AssertionError(
            "the width-ceiling leg was handed no parameter cases — an empty"
            " table iterates to a silent success, which is a width gate"
            " reporting green while comparing nothing"
        )
    verdicts = [(case, ask_mcp(case), ask_http(case)) for case in cases]
    if not any(mcp == SERVED and http == SERVED for _case, mcp, http in verdicts):
        raise AssertionError(
            "no case in this table was served by either door, so the table"
            " would pass against two doors that discarded the caller's"
            " parameters entirely — which is precisely what both doors did"
            " before `D-IMPL-133` was implemented. A width table with no"
            " served case cannot fail for the reason it exists"
        )
    differences = [
        f"{dict(case)!r}: the MCP tool said {mcp!r} and the HTTP route"
        f" said {http!r}"
        for case, mcp, http in verdicts
        if mcp != http
    ]
    if differences:
        raise AssertionError(
            "the two parameterised doors disagreed — "
            + "; ".join(differences)
            + ". `D-IMPL-133` rules that both doors carry `parameters`, so a"
            " value one door refuses is a value the other refuses too;"
            " whichever is wider is the defect"
        )


def assert_type_mismatch_refused(
    cases: Sequence[Mapping[str, Any]], ask: AskDoor
) -> None:
    """A wrong-typed parameter is refused, never quietly coerced.

    The sibling of :func:`assert_same_verdicts`, in the same shape and for the
    same reason: a control passes a *coercing* door and this must fail.

    The recorded constraint on ``D-IMPL-133``'s repair is that the door must
    not guess at coercions. A door that turned a presented ``"11"`` into an
    ``11`` would serve, and the caller would never learn that the value they
    sent is not the value that was answered — which is ``D-08``'s *the fabric
    never silently degrades a caller's value*, one layer up.

    Args:
        cases: Parameter mappings whose values disagree in **type** with the
            class's declaration.
        ask: The door under test, as a callable answering one case.

    Raises:
        AssertionError: the table was empty, or any case reached a verdict
            other than ``type-mismatch``.
    """
    if not cases:
        raise AssertionError(
            "the coercion leg was handed no cases, so it would report a door"
            " that coerces every value as refusing every value"
        )
    coerced = [
        f"{dict(case)!r} reached {verdict!r}"
        for case, verdict in ((case, ask(case)) for case in cases)
        if verdict != "type-mismatch"
    ]
    if coerced:
        raise AssertionError(
            "a wrong-typed parameter was not refused as a `type-mismatch` — "
            + "; ".join(coerced)
            + ". The door is guessing at a coercion the class did not declare,"
            " which is the constraint `D-IMPL-133`'s repair had to honour"
        )


# ---------------------------------------------------------------------------
# The declared world both doors are measured against.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product, reused by every door below.

    Module-scoped because it boots a fabric: these tests vary the *question*,
    never the product, so paying for one assembly is honest.
    """
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-parameters")
        / "door.sqlite3"
    )


def _contract(address: ProductAddress) -> ProductRequestContract:
    """The request surface this module's class declares.

    One required integer and one optional string, so *undeclared*, *missing*
    and *mistyped* are three distinguishable verdicts rather than one.
    """
    return ProductRequestContract(
        semver="1.0.0",
        schema_name=address.product_class,
        schema_version=address.version,
        arguments=SkillArgumentSchema(
            properties={
                REQUIRED_PARAMETER: SkillArgumentProperty(
                    type="integer",
                    description="The declared threshold this class answers at.",
                ),
                OPTIONAL_PARAMETER: SkillArgumentProperty(
                    type="string",
                    description="A declared, optional narrowing.",
                ),
            },
            required=(REQUIRED_PARAMETER,),
        ),
    )


def _verdict(
    request: ProductRequest | None, *, declared: ProductRequestContract
) -> Verdict:
    """What the one shared comparison says about the request a door carried.

    ``None`` — a door that reached the resolver with no request at all — is
    reported as its own token rather than folded into a refusal, because
    "carried nothing" and "carried something the class refused" are different
    defects and an audit that could not tell them apart would be useless.
    """
    if request is None:
        return "no-request"
    violation = refuse_request(request=request, declared=declared)
    return SERVED if violation is None else violation.reason


# ---------------------------------------------------------------------------
# The MCP door.
# ---------------------------------------------------------------------------


def _token_file(root: Path) -> Path:
    path = root / "egress-parameters-tokens.json"
    path.write_text(
        json.dumps({TOKEN: {"client_id": PRINCIPAL, "scopes": [SCOPE]}}),
        encoding="utf-8",
    )
    return path


def _entitlement(address: ProductAddress) -> ControlPlaneProductEntitlementSource:
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version=POLICY_VERSION,
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )


def _recording_resolver(
    servable: object, carried: list[ProductRequest | None]
) -> Callable[..., object]:
    """A resolver that records the request the door handed it, then serves.

    It never refuses. The verdict is computed *outside* the door by
    :func:`_verdict`, so what is measured is what the door **carried** rather
    than what some deployment's resolver chose to do about it — which is the
    only half ``D-IMPL-133`` makes the door responsible for.
    """

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        carried.append(request)
        return servable

    return resolve


def _mcp_server(
    root: Path, *, servable: object, address: ProductAddress, carried: list[Any]
) -> Any:
    """The real egress door, tool exposed, over a recording resolver."""
    return build_egress_server(
        server_name=SERVER_NAME,
        resolver=_recording_resolver(servable, carried),  # type: ignore[arg-type]
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=_token_file(root))
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[SCOPE],
        ),
        entitlement_source=_entitlement(address),
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )


def _tool_arguments(
    address: ProductAddress, parameters: Mapping[str, Any] | None
) -> dict[str, Any]:
    """The three address segments, the four axes, and the caller's parameters."""
    arguments: dict[str, Any] = {
        "tenant": address.tenant,
        "product_class": address.product_class,
        "version": address.version,
        "subject": SUBJECT,
        "intent": INTENT,
        "freshness": FRESHNESS,
        "asked_at": ASKED_AT.isoformat(),
    }
    if parameters is not None:
        arguments["parameters"] = dict(parameters)
    return arguments


def _drive_mcp(
    server: Any,
    operation: Callable[[ClientSession], Awaitable[tuple[bool, str]]],
) -> tuple[bool, str]:
    """Run one operation against the server's own ASGI app, in one lifespan."""
    app = server.streamable_http_app()

    async def go() -> tuple[bool, str]:
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=IN_PROCESS_BASE_URL,
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            try:
                return await run_with_session(
                    url=f"{IN_PROCESS_BASE_URL}/mcp",
                    operation=operation,
                    http_client_factory=factory,
                )
            except McpServerUnreachable as refused:
                return True, str(refused)

    return asyncio.run(go())


def _tool_operation(
    arguments: dict[str, Any],
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
        return bool(result.isError), " | ".join(
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        )

    return operation


def _resource_operation(
    uri: str,
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.read_resource(AnyUrl(uri))
        return False, "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return operation


def _ask_mcp(assembled: Any, tmp_path: Path) -> AskDoor:
    """The real MCP tool, as a callable answering one parameter case."""
    declared = _contract(assembled.address)

    def ask(parameters: Mapping[str, Any]) -> Verdict:
        carried: list[ProductRequest | None] = []
        server = _mcp_server(
            tmp_path,
            servable=assembled.servable,
            address=assembled.address,
            carried=carried,
        )
        is_error, detail = _drive_mcp(
            server, _tool_operation(_tool_arguments(assembled.address, parameters))
        )
        if is_error:
            raise AssertionError(
                f"the MCP tool refused the parameter case {dict(parameters)!r}"
                f" at the door rather than carrying it: {detail}"
            )
        return _verdict(carried[-1] if carried else None, declared=declared)

    return ask


# ---------------------------------------------------------------------------
# The HTTP door.
# ---------------------------------------------------------------------------


def _http_app(
    root: Path, *, servable: object, address: ProductAddress, carried: list[Any]
) -> Any:
    """The real HTTP product door, authenticated and entitled."""
    return create_app(
        ApiDependencies(
            control_plane=ControlPlaneRegistry(),
            artifact_store=FileArtifactStore(root=root / "artifacts"),
            product_resolver=_recording_resolver(servable, carried),  # type: ignore[arg-type]
        ),
        auth=BearerTokenAuth(
            token_source=FileTokenSource(path=_token_file(root))
        ),
        product_entitlement=_entitlement(address),
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
    )


def _http_call(app: Any, url: str, params: Mapping[str, Any]) -> httpx.Response:
    async def go() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://fabric.invalid",
        ) as client:
            return await client.get(
                url,
                params=dict(params),
                headers={"Authorization": f"Bearer {TOKEN}"},
            )

    return asyncio.run(go())


def _ask_http(assembled: Any, tmp_path: Path) -> AskDoor:
    """The real HTTP route, as a callable answering one parameter case.

    The caller's mapping travels as **JSON text** in one query parameter rather
    than as flattened query keys. That is what lets the HTTP door be exactly as
    wide as the MCP tool and no wider: JSON is self-describing, so a presented
    ``3`` and a presented ``"3"`` stay distinguishable and the door never has to
    guess at a coercion — the constraint ``product.py``'s own docstring records
    against a flat, string-valued query surface.
    """
    address = assembled.address
    declared = _contract(address)
    root = tmp_path / "http"
    root.mkdir(exist_ok=True)

    def ask(parameters: Mapping[str, Any]) -> Verdict:
        carried: list[ProductRequest | None] = []
        app = _http_app(
            root,
            servable=assembled.servable,
            address=address,
            carried=carried,
        )
        response = _http_call(
            app,
            f"/product/{address.tenant}/{address.product_class}/{address.version}",
            {
                "subject": SUBJECT,
                "intent": INTENT,
                "freshness": FRESHNESS,
                "asked_at": ASKED_AT.isoformat(),
                "parameters": json.dumps(dict(parameters)),
            },
        )
        if response.status_code != 200:
            raise AssertionError(
                f"the HTTP route refused the parameter case"
                f" {dict(parameters)!r} at the door rather than carrying it:"
                f" {response.status_code} {response.text}"
            )
        return _verdict(carried[-1] if carried else None, declared=declared)

    return ask


# ---------------------------------------------------------------------------
# The shared case table.
# ---------------------------------------------------------------------------

#: Every parameter case both doors are held to, in one place. Five, spanning
#: the four verdicts the declared world can produce plus the empty mapping —
#: the case that says *this question needs nothing beyond its four axes* and
#: which, against a class declaring a required parameter, is a refusal.
PARAMETER_CASES: tuple[Mapping[str, Any], ...] = (
    {REQUIRED_PARAMETER: 11},
    {REQUIRED_PARAMETER: 11, OPTIONAL_PARAMETER: "north"},
    {},
    {REQUIRED_PARAMETER: 11, UNDECLARED_PARAMETER: "smuggled"},
    {REQUIRED_PARAMETER: "11"},
)

#: The wrong-typed cases the coercion leg runs. A string where an integer was
#: declared, and an integer where a string was.
COERCION_CASES: tuple[Mapping[str, Any], ...] = (
    {REQUIRED_PARAMETER: "11"},
    {REQUIRED_PARAMETER: 11, OPTIONAL_PARAMETER: 7},
)


# ---------------------------------------------------------------------------
# The six behaviours.
# ---------------------------------------------------------------------------


def test_a_supplied_parameter_reaches_the_resolver(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 1: the caller's value arrives in ``ProductRequest.parameters``.

    Asserted on the **carried value**, not on the served status: a door that
    accepted a ``parameters`` argument and dropped it would serve perfectly and
    fail only here. That is the ``:588`` defect restated as a measurement.
    """
    carried: list[ProductRequest | None] = []
    server = _mcp_server(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        carried=carried,
    )

    is_error, detail = _drive_mcp(
        server,
        _tool_operation(
            _tool_arguments(assembled.address, {REQUIRED_PARAMETER: 11})
        ),
    )

    assert is_error is False, detail
    assert carried and carried[-1] is not None
    assert dict(carried[-1].parameters) == {REQUIRED_PARAMETER: 11}


def test_an_undeclared_parameter_is_refused_by_name(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 2: the declared world is closed, and the refusal names the key."""
    declared = _contract(assembled.address)
    carried: list[ProductRequest | None] = []
    server = _mcp_server(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        carried=carried,
    )

    _drive_mcp(
        server,
        _tool_operation(
            _tool_arguments(
                assembled.address,
                {REQUIRED_PARAMETER: 11, UNDECLARED_PARAMETER: "smuggled"},
            )
        ),
    )

    assert carried and carried[-1] is not None
    violation = refuse_request(request=carried[-1], declared=declared)
    assert violation is not None
    assert violation.reason == "undeclared-parameter"
    assert violation.key == UNDECLARED_PARAMETER


def test_a_missing_required_parameter_is_refused_by_name(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 3: the docstring's prediction, now reachable rather than universal.

    Before ``D-IMPL-133`` this verdict was what *every* call through this tool
    produced, because the door carried nothing. It is now the verdict for the
    call that genuinely omitted the parameter, and the case above proves the
    difference.
    """
    declared = _contract(assembled.address)
    carried: list[ProductRequest | None] = []
    server = _mcp_server(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        carried=carried,
    )

    _drive_mcp(
        server, _tool_operation(_tool_arguments(assembled.address, {}))
    )

    assert carried and carried[-1] is not None
    violation = refuse_request(request=carried[-1], declared=declared)
    assert violation is not None
    assert violation.reason == "missing-required-parameter"
    assert violation.key == REQUIRED_PARAMETER


def test_a_wrong_typed_parameter_is_refused_rather_than_coerced(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 4: the door does not guess. Through the shipped assertion."""
    assert_type_mismatch_refused(COERCION_CASES, _ask_mcp(assembled, tmp_path))


def test_neither_door_is_wider_than_the_other(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 5: one shared table, both real doors, identical verdicts.

    ``D-IMPL-133``'s *"both, not one"*. The two doors are passed as callables so
    the controls below can substitute a divergent one into **this same**
    function rather than into a copy of it.
    """
    assert_same_verdicts(
        PARAMETER_CASES,
        _ask_mcp(assembled, tmp_path),
        _ask_http(assembled, tmp_path),
    )


def test_the_tool_body_is_byte_identical_to_the_resources(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 6: the tool is still not a second serialization.

    Compared on raw bytes rather than parsed JSON: a comparison of parsed
    objects would be blind to a re-encode, and a re-encode is exactly how a
    parameterised surface silently changes the content address of the one
    beside it.
    """
    carried: list[ProductRequest | None] = []
    server = _mcp_server(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        carried=carried,
    )
    app = server.streamable_http_app()

    async def both() -> tuple[str, str]:
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=IN_PROCESS_BASE_URL,
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            _resource_error, resource_text = await run_with_session(
                url=f"{IN_PROCESS_BASE_URL}/mcp",
                operation=_resource_operation(assembled.address.uri),
                http_client_factory=factory,
            )
            tool_error, tool_text = await run_with_session(
                url=f"{IN_PROCESS_BASE_URL}/mcp",
                operation=_tool_operation(
                    _tool_arguments(
                        assembled.address, {REQUIRED_PARAMETER: 11}
                    )
                ),
                http_client_factory=factory,
            )
            assert tool_error is False, tool_text
            return resource_text, tool_text

    resource_text, tool_text = asyncio.run(both())

    assert tool_text == resource_text
    assert tool_text == canonical_bytes(assembled.servable.product).decode("utf-8")


# ---------------------------------------------------------------------------
# The sabotage controls (D-22) — divergent subjects into the real assertions.
# ---------------------------------------------------------------------------


def test_the_width_assertion_fires_on_a_wider_mcp_door(
    assembled: Any, tmp_path: Path
) -> None:
    """A deliberately-wider fake tool is caught by the **real** width assertion.

    The fake accepts the undeclared parameter the class does not declare — the
    single most consequential way a door can be wider than the one beside it,
    because an undeclared parameter that reaches plan selection is an argument
    nobody governed.
    """
    honest = _ask_http(assembled, tmp_path)

    def wider(parameters: Mapping[str, Any]) -> Verdict:
        if UNDECLARED_PARAMETER in parameters:
            return SERVED
        return honest(parameters)

    with pytest.raises(AssertionError, match="wider"):
        assert_same_verdicts(PARAMETER_CASES, wider, honest)


def test_the_width_assertion_fires_on_a_table_that_never_serves() -> None:
    """The non-vacuity guard, exercised — this is the guard that had to exist.

    Both doors carried ``{}`` before ``D-IMPL-133`` was implemented, so a table
    of refusing cases would have found them in perfect agreement while neither
    carried anything. A table with no served case is therefore refused rather
    than reported green.
    """

    def never_serves(parameters: Mapping[str, Any]) -> Verdict:
        return "missing-required-parameter"

    with pytest.raises(AssertionError, match="no served case"):
        assert_same_verdicts(PARAMETER_CASES, never_serves, never_serves)


def test_the_coercion_assertion_fires_on_a_coercing_door() -> None:
    """A door that coerces instead of refusing fails the **real** assertion.

    The fake does what a door guessing at coercions would do: it reads the
    presented ``"11"`` as an ``11``, conforms, and serves. Nothing about the
    served response would tell the caller their value was rewritten.
    """

    def coercing(parameters: Mapping[str, Any]) -> Verdict:
        return SERVED

    with pytest.raises(AssertionError, match="type-mismatch"):
        assert_type_mismatch_refused(COERCION_CASES, coercing)
