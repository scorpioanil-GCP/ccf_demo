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

A refusal *at the door* is a verdict, because a table that cannot say so is blind
--------------------------------------------------------------------------------
``D-IMPL-151`` finding ``B2``. Until it was found, the two door callables below
**raised** when a door refused before reaching the resolver, and every case in
the table was a well-formed JSON object — so a door disagreement that took the
form *one door refuses this payload and the other serves it* was outside what
the table could represent. That is exactly what ``"parameters": null`` was: the
MCP tool read it as the empty mapping and served, while the HTTP route returned
``400 ERROR_PRODUCT_PARAMETERS_MALFORMED``. A width table that cannot express a
width difference is the table's defect as much as the door's, so
:data:`REFUSED_AT_DOOR` is now a verdict like any other and
:data:`EXPLICIT_NULL` is a case like any other.

Nothing is weakened by that. A door that began refusing a well-formed case would
now disagree with the door beside it and fail the width leg by name, where
before it failed only its own callable; and a pair of doors refusing *everything*
is still refused, by the non-vacuity guard, which asks for a **served** case
rather than merely a non-empty table.

**Which door was right, and why.** The HTTP route's refusal. ``D-08`` is that the
fabric never silently degrades a caller's value, and the empty mapping is not a
neutral zero here — both doors' own docstrings record it as the *positive*
statement ``this question needs nothing beyond its four axes``. Reading a
supplied ``null`` as that statement invents an assertion the caller never made,
and does it on the argument the resolver selects a plan from. Omission remains
the empty mapping on both doors, which is the case that genuinely *is* that
statement. So the MCP tool narrowed to match rather than the HTTP route widening
to match, and ``D-IMPL-133``'s *"no wider than the other door"* is satisfied in
the direction that does not add a silent default.

**A JSON array was never reachable**, and is now asserted never to be. The
finding raised the possibility that ``dict(parameters)`` over a sequence of pairs
would coerce ``[["a", 1]]`` into a mapping the HTTP door would have refused.
Measured: pydantic refuses a list for a ``dict[str, Any]``-annotated tool
argument under both the old annotation and the new one, so the coercion is
unreachable through FastMCP. It was unreachable by accident of the argument
model, not by anything this door did, which is why
:func:`test_neither_door_accepts_a_json_array_as_parameters` now holds it there.

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
from datetime import UTC, datetime, timedelta
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
from ccf.products.door import DoorOutcome
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.resolver import ReplayRefusalRecorder
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
from ccf_runtime.http_api.dependencies import ApiDependencies

from http_api.gate_fixtures import SCOPE_EVERYTHING, authority
from ccf_runtime.mcp.auth import (
    FileTokenSource,
    SourceBackedTokenVerifier,
    TokenGrant,
)
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL, build_egress_server
from tests.mcp.guarded_servers import wide_authorizer

from crossproc.servers.mcp_egress_child import ProductAddress, build_servable_product

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "egress-parameters-token"
PRINCIPAL = "egress-parameters-caller"
SCOPE = "ccf:egress-parameters"
ROLE = "egress-parameters-role"
#: This suite's own scope-mapping key. The authorizer pins one version at
#: one key, so a key of its own is what keeps another suite's mapping from
#: deciding about this suite's vocabulary.
MAPPING_KEY = "egress-parameters/scope-mapping"
SERVER_NAME = "ccf-egress-parameters"

#: The artifact class this module's doors file a denial under. Nothing here
#: denies, but a door that entitles binds a recorder (`D-IMPL-256` (2)).
REPLAY_RECORD_CLASS = "egress-fixture.replay-record"
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

#: ``"served"``, a :data:`~ccf.products.request.ProductRequestViolationReason`,
#: or :data:`REFUSED_AT_DOOR`.
Verdict = str


class ExplicitNull:
    """The caller supplied ``parameters`` and supplied JSON ``null`` for it.

    A distinct case from *omitted*, and the distinction is the whole of
    ``D-IMPL-151`` finding ``B2``: omission is the positive statement *this
    question needs nothing beyond its four axes*, and a supplied ``null`` is a
    value the caller sent. A sentinel rather than ``None``, because ``None``
    already means "omit the argument" inside :func:`_tool_arguments` and one
    spelling for two meanings is how a table stops saying what it means.
    """

    def __repr__(self) -> str:
        return "parameters=null"


#: The one instance. Compared by identity, never by value.
EXPLICIT_NULL = ExplicitNull()

#: One row of the shared table: a caller's mapping, or the supplied ``null``.
ParameterCase = Mapping[str, Any] | ExplicitNull

#: Answer one parameter case with a verdict. The unit both doors are compared
#: as, and the unit a control substitutes a divergent implementation of.
AskDoor = Callable[[ParameterCase], Verdict]

#: The verdict a conforming request produces. Named so the non-vacuity guard,
#: the case table and the controls all say the same string.
SERVED: Verdict = "served"

#: The verdict for a door that refused before the resolver was reached — the
#: MCP tool answering ``isError``, or the HTTP route answering non-``200``. A
#: verdict rather than a raise, so a door disagreement of the form *one refuses,
#: the other serves* is representable in the shared table (``D-IMPL-151`` ``B2``).
REFUSED_AT_DOOR: Verdict = "refused-at-door"


# ---------------------------------------------------------------------------
# The shipped assertions — functions over their subjects (D-22).
# ---------------------------------------------------------------------------


def _spell(case: ParameterCase) -> str:
    """How a case is named in a failure — a mapping as itself, the sentinel as
    the wire spelling a reader would have typed."""
    return repr(case) if isinstance(case, ExplicitNull) else repr(dict(case))


def assert_same_verdicts(
    cases: Sequence[ParameterCase],
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
        f"{_spell(case)}: the MCP tool said {mcp!r} and the HTTP route"
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


def _token_file(root: Path, *, tenant: str) -> Path:
    """The door's token file, whose one credential is scoped to ``tenant``.

    ``tenant`` is required rather than defaulted (``SEC-018``): a credential
    that names no tenant reaches nothing, so a fixture that forgot it would
    fail loudly instead of quietly minting the unscoped bearer this finding is
    about.
    """
    path = root / "egress-parameters-tokens.json"
    path.write_text(
        json.dumps(
            {
                TOKEN: {
                    "client_id": PRINCIPAL,
                    "scopes": [SCOPE],
                    "tenants": [tenant],
                }
            }
        ),
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


def _recorder(root: Path, *, tenant: str) -> ReplayRefusalRecorder:
    """The ONE minting seam this module's doors bind (`D-IMPL-256` (2)).

    Built with the keyword list `ccf.products.resolver::build_governed_resolver`
    uses for its own, so a door's recorder and a resolver's are the same shape
    over one store. Copied rather than imported from a sibling test module: two
    suites that answer different questions should not be coupled by a fixture.
    Nothing here denies — these doors serve — but a door that entitles does not
    build without somewhere to record a denial, and that is the point.
    """
    return ReplayRefusalRecorder(
        artifact_store=FileArtifactStore(root=root / "artifacts"),
        replay_record_class=REPLAY_RECORD_CLASS,
        tenant_id=tenant,
        assembly_mode="algorithmic",
    )


def _mcp_server(
    root: Path, *, servable: object, address: ProductAddress, carried: list[Any]
) -> Any:
    """The real egress door, tool exposed, over a recording resolver."""
    return build_egress_server(
        server_name=SERVER_NAME,
        resolver=_recording_resolver(servable, carried),  # type: ignore[arg-type]
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=_token_file(root, tenant=address.tenant))
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=wide_authorizer(scopes=(SCOPE,)),
        entitlement_source=_entitlement(address),
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        refusal_recorder=_recorder(root, tenant=address.tenant),
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )


def _tool_arguments(
    address: ProductAddress, parameters: ParameterCase | None
) -> dict[str, Any]:
    """The three address segments, the four axes, and the caller's parameters.

    Three spellings, and they are three: ``None`` omits the argument,
    :data:`EXPLICIT_NULL` supplies it as JSON ``null``, and a mapping supplies
    itself. Collapsing the first two is what let ``B2`` through.
    """
    encoded: Mapping[str, Any] = (
        {} if parameters is None or isinstance(parameters, ExplicitNull)
        else dict(parameters)
    )
    arguments: dict[str, Any] = {
        "tenant": address.tenant,
        "product_class": address.product_class,
        "version": address.version,
        # The caller's own question, encoded from **this case's** values, so
        # the MCP leg and the HTTP leg are still driven by one table rather
        # than two (`C-16`). `temporal_boundary` is `None` here for the reason
        # `C-02` gives — a caller deferring to the decision instant sends
        # `None` — which also keeps the door's temporal cross-check out of a
        # table whose subject is the declared remainder.
        "request": canonical_bytes(
            WireRequest(
                product_id=address.product_class,
                parameters=encoded,
                temporal_boundary=None,
            )
        ).decode("utf-8"),
        "subject": SUBJECT,
        "intent": INTENT,
        "freshness": FRESHNESS,
        "asked_at": ASKED_AT.isoformat(),
    }
    if isinstance(parameters, ExplicitNull):
        arguments["parameters"] = None
    elif parameters is not None:
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
    """The real MCP tool, as a callable answering one parameter case.

    A door refusal is :data:`REFUSED_AT_DOOR` rather than a raise, so the shared
    table can hold a case one door refuses and the other serves — the shape
    ``D-IMPL-151`` finding ``B2`` took and the table could not express.
    """
    declared = _contract(assembled.address)

    def ask(parameters: ParameterCase) -> Verdict:
        carried: list[ProductRequest | None] = []
        server = _mcp_server(
            tmp_path,
            servable=assembled.served,
            address=assembled.address,
            carried=carried,
        )
        is_error, _detail = _drive_mcp(
            server, _tool_operation(_tool_arguments(assembled.address, parameters))
        )
        if is_error:
            return REFUSED_AT_DOOR
        return _verdict(carried[-1] if carried else None, declared=declared)

    return ask


# ---------------------------------------------------------------------------
# The HTTP door.
# ---------------------------------------------------------------------------


def _http_app(
    root: Path, *, servable: object, address: ProductAddress, carried: list[Any]
) -> Any:
    """The real HTTP product door, authenticated, authorized and entitled.

    The five authority seams come from
    :func:`~http_api.gate_fixtures.authority` as one bundle. None of them is
    this module's subject — it compares the width of two doors — and building
    five seams by hand in a module that is about something else is five
    chances to build a permissive one.

    The credential is the tenanted one that helper mints, not the dev
    ``FileTokenSource`` beside it: that source mints a grant with no scalar
    ``tenant``, and the HTTP door refuses it (``SEC-002``). The MCP leg keeps
    the token file, because the MCP tenancy floor reads the plural ``tenants``
    claim instead — the two doors read different shapes of the same fact, and
    that asymmetry is the SDK's, not this fixture's.
    """
    return create_app(
        ApiDependencies(
            control_plane=ControlPlaneRegistry(),
            artifact_store=FileArtifactStore(root=root / "artifacts"),
            product_resolver=_recording_resolver(servable, carried),  # type: ignore[arg-type]
        ),
        **authority(
            tenant=address.tenant,
            key=MAPPING_KEY,
            grants={TOKEN: (PRINCIPAL, (SCOPE_EVERYTHING,), address.tenant)},
            product_entitlement=_entitlement(address),
            perspective_resolver=(
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role=ROLE
                )
            ),
            # The HTTP twin binds the same seam on the same rule
            # (`D-IMPL-256` (2)). `create_app`'s own keyword and its
            # construction-time check are plan `24.6-09`'s, in this same wave;
            # this call site is plan `24.6-10`'s.
            refusal_recorder=_recorder(root, tenant=address.tenant),
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

    def ask(parameters: ParameterCase) -> Verdict:
        carried: list[ProductRequest | None] = []
        app = _http_app(
            root,
            servable=assembled.served,
            address=address,
            carried=carried,
        )
        supplied = (
            "null"
            if isinstance(parameters, ExplicitNull)
            else json.dumps(dict(parameters))
        )
        response = _http_call(
            app,
            f"/product/{address.tenant}/{address.product_class}/{address.version}",
            {
                "subject": SUBJECT,
                "intent": INTENT,
                "freshness": FRESHNESS,
                "asked_at": ASKED_AT.isoformat(),
                "parameters": supplied,
            },
        )
        if response.status_code != 200:
            return REFUSED_AT_DOOR
        return _verdict(carried[-1] if carried else None, declared=declared)

    return ask


# ---------------------------------------------------------------------------
# The shared case table.
# ---------------------------------------------------------------------------

#: Every parameter case both doors are held to, in one place. Six, spanning the
#: four verdicts the declared world can produce, the empty mapping — the case
#: that says *this question needs nothing beyond its four axes* and which,
#: against a class declaring a required parameter, is a refusal — and, since
#: ``D-IMPL-151`` finding ``B2``, a supplied JSON ``null``.
#:
#: The sixth is the one every earlier case was blind to: the five before it are
#: all well-formed JSON objects, so a door reading some *other* JSON value as
#: the empty mapping was outside what this table could see. It was measured
#: doing exactly that — served on MCP, ``400`` on HTTP.
PARAMETER_CASES: tuple[ParameterCase, ...] = (
    {REQUIRED_PARAMETER: 11},
    {REQUIRED_PARAMETER: 11, OPTIONAL_PARAMETER: "north"},
    {},
    {REQUIRED_PARAMETER: 11, UNDECLARED_PARAMETER: "smuggled"},
    {REQUIRED_PARAMETER: "11"},
    EXPLICIT_NULL,
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
        servable=assembled.served,
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
        servable=assembled.served,
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
        servable=assembled.served,
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


def test_a_supplied_null_is_refused_and_an_omission_is_the_empty_mapping(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 7: the two spellings the MCP tool used to collapse into one.

    ``D-IMPL-151`` finding ``B2``, stated on the door directly rather than only
    through the width table, because the two facts are different: the table says
    *the doors agree*, and this says *what they agree on*. Two doors could agree
    by both reading ``null`` as the empty mapping, and that is the outcome
    ``D-08`` forbids — the empty mapping is the positive statement *this question
    needs nothing beyond its four axes*, and inventing it from a supplied value
    is degrading a caller's value silently on the argument the resolver selects
    a plan from.

    Omission keeps meaning the empty mapping, which is what makes this a
    narrowing rather than a breaking change for a deployment that adopted the
    tool before ``D-IMPL-133``.
    """
    ask = _ask_mcp(assembled, tmp_path)

    assert ask(EXPLICIT_NULL) == REFUSED_AT_DOOR
    assert ask({}) == "missing-required-parameter"


def test_neither_door_accepts_a_json_array_as_parameters(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 8: the coercion the close review asked about is unreachable.

    ``dict([["a", 1]])`` is a mapping in Python, so a door spelling its forward
    as ``dict(parameters)`` *reads* as though a JSON array could be coerced into
    one while the HTTP route would refuse it. Measured: pydantic refuses a list
    for the tool's ``dict[str, Any]``-annotated argument, so the array never
    reaches the handler body at all — under the old annotation as well as the
    new one. Unreachable by the argument model rather than by anything the door
    does, which is why it is asserted here instead of assumed.

    Asked at the door rather than through :func:`_ask_mcp` because a raw
    argument map is the only way to present a shape the case table's type does
    not admit.
    """
    carried: list[ProductRequest | None] = []
    server = _mcp_server(
        tmp_path,
        servable=assembled.served,
        address=assembled.address,
        carried=carried,
    )
    arguments = _tool_arguments(assembled.address, {REQUIRED_PARAMETER: 11})
    arguments["parameters"] = [[REQUIRED_PARAMETER, 11]]

    is_error, detail = _drive_mcp(server, _tool_operation(arguments))

    assert is_error is True, (
        "a JSON array reached the MCP tool — if the handler coerced it into a"
        f" mapping the HTTP route would have refused, that is a width"
        f" difference `D-IMPL-133` forbids. Detail: {detail}"
    )
    assert carried == [], (
        "the array was refused but the handler ran anyway, so the refusal is"
        " not the argument model's and this test is measuring something else"
    )


def test_the_tool_carries_the_resources_bytes_without_re_serializing_them(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 6: the tool is still not a second serialization.

    **This assertion was restated by ``D-IMPL-148`` Addendum A, and the
    restatement is recorded rather than quietly applied.** It read
    ``tool_text == resource_text`` — the tool's *whole return* was the vessel,
    byte for byte. The tool now answers in a
    :class:`~ccf.products.door.DoorOutcome`, because a refusal cannot be raised
    over FastMCP without a prose prefix and because the replay reference has no
    sibling channel on a bare body. So the comparison moved to the member that
    carries the vessel.

    **Why the new claim is not weaker.** The claim this test exists to make is
    *the parameterised surface is not a second serialization of the product* —
    a re-encode there would silently change the content address of the resource
    beside it. That claim is asserted here at full strength and on raw text: the
    carried bytes are the resource's bytes and the canonical serializer's
    output, character for character. What is no longer asserted is that the
    tool's return has *no frame around* those bytes, which is exactly and only
    what the ruling changed. The test is also **stronger** in one respect it was
    not before: the text must validate as a ``DoorOutcome``, so a door emitting
    an ad-hoc shape fails here rather than being read as a vessel.

    Compared on raw text rather than parsed JSON, for the original reason: a
    comparison of parsed objects would be blind to a re-encode.
    """
    carried: list[ProductRequest | None] = []
    server = _mcp_server(
        tmp_path,
        servable=assembled.served,
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

    carried = DoorOutcome.model_validate_json(tool_text).product_json
    assert carried == resource_text
    assert carried == canonical_bytes(assembled.servable.product).decode("utf-8")


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

    def wider(parameters: ParameterCase) -> Verdict:
        if (
            not isinstance(parameters, ExplicitNull)
            and UNDECLARED_PARAMETER in parameters
        ):
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

    def never_serves(parameters: ParameterCase) -> Verdict:
        return "missing-required-parameter"

    with pytest.raises(AssertionError, match="no served case"):
        assert_same_verdicts(PARAMETER_CASES, never_serves, never_serves)


def test_the_coercion_assertion_fires_on_a_coercing_door() -> None:
    """A door that coerces instead of refusing fails the **real** assertion.

    The fake does what a door guessing at coercions would do: it reads the
    presented ``"11"`` as an ``11``, conforms, and serves. Nothing about the
    served response would tell the caller their value was rewritten.
    """

    def coercing(parameters: ParameterCase) -> Verdict:
        return SERVED

    with pytest.raises(AssertionError, match="type-mismatch"):
        assert_type_mismatch_refused(COERCION_CASES, coercing)


# ---------------------------------------------------------------------------
# The address cross-check (`C-01`, `C-16`, `C-18`).
#
# Two independent sources for one fact is the bypass one level up. A caller
# could encode question A, supply address arguments for question B, and have A
# echoed while B is answered — a consumer's total three-axis comparison would
# pass on an answer to a question nobody asked. So the door refuses the
# disagreement by name on each axis where a second copy of the fact exists, and
# names the one axis where it does not.
# ---------------------------------------------------------------------------


def _call_with(
    assembled: Any,
    tmp_path: Path,
    *,
    parameters: Mapping[str, Any],
    encoded: WireRequest | None = None,
    asked_at: datetime | None = None,
) -> tuple[bool, str]:
    """Drive the real tool, optionally disagreeing with itself on one axis.

    ``encoded`` and ``asked_at`` default to the agreeing values
    :func:`_tool_arguments` builds, so a leg that overrides neither is the
    vacuity guard for every leg that overrides one.
    """
    carried: list[ProductRequest | None] = []
    server = _mcp_server(
        tmp_path,
        servable=assembled.served,
        address=assembled.address,
        carried=carried,
    )
    arguments = _tool_arguments(assembled.address, parameters)
    if encoded is not None:
        arguments["request"] = canonical_bytes(encoded).decode("utf-8")
    if asked_at is not None:
        arguments["asked_at"] = asked_at.isoformat()
    return _drive_mcp(server, _tool_operation(arguments))


def test_an_encoded_question_naming_another_class_is_refused_by_name(
    assembled: Any, tmp_path: Path
) -> None:
    """`C-01`: the door refuses to echo one question while answering another."""
    other = f"{assembled.address.product_class}-elsewhere"

    is_error, detail = _call_with(
        assembled,
        tmp_path,
        parameters={REQUIRED_PARAMETER: 11},
        encoded=WireRequest(
            product_id=other,
            parameters={REQUIRED_PARAMETER: 11},
            temporal_boundary=None,
        ),
    )

    assert is_error is True, detail
    assert other in detail, detail
    assert assembled.address.product_class in detail, detail

    # The vacuity guard: the same call, agreeing, is answered. Without it the
    # assertion above would pass against a door that refused every call.
    agreed_error, agreed = _call_with(
        assembled, tmp_path, parameters={REQUIRED_PARAMETER: 11}
    )
    assert agreed_error is False, agreed
    assert DoorOutcome.model_validate_json(agreed).product_json is not None


def test_an_encoded_question_declaring_other_parameters_is_refused_by_name(
    assembled: Any, tmp_path: Path
) -> None:
    """`C-01`, one axis over: the declared remainder is crossed the same way."""
    is_error, detail = _call_with(
        assembled,
        tmp_path,
        parameters={REQUIRED_PARAMETER: 11},
        encoded=WireRequest(
            product_id=assembled.address.product_class,
            parameters={REQUIRED_PARAMETER: 12},
            temporal_boundary=None,
        ),
    )

    assert is_error is True, detail
    assert "11" in detail and "12" in detail, detail

    agreed_error, agreed = _call_with(
        assembled, tmp_path, parameters={REQUIRED_PARAMETER: 11}
    )
    assert agreed_error is False, agreed
    assert DoorOutcome.model_validate_json(agreed).product_json is not None


def test_a_concrete_boundary_disagreeing_with_asked_at_is_refused_by_name(
    assembled: Any, tmp_path: Path
) -> None:
    """`C-18` part (a): the third axis, where a second copy of the fact exists.

    ``C-15`` keeps the clock client-side, so a **concrete** ``as_of`` crosses
    this pipe twice — inside the encoded question that becomes the echo, and as
    the ``asked_at`` argument the door answers against. A transport altering
    only the second produces a perfectly matching echo for an answer computed
    at a different instant, which is ``B0``'s own failure mode surviving on the
    third axis of a comparison ``C-03`` calls total.

    The disagreement here is **one microsecond**, deliberately: nothing else
    about the answer moves, so a green result could only mean the axis is
    unchecked.
    """
    drifted = ASKED_AT + timedelta(microseconds=1)

    is_error, detail = _call_with(
        assembled,
        tmp_path,
        parameters={REQUIRED_PARAMETER: 11},
        encoded=WireRequest(
            product_id=assembled.address.product_class,
            parameters={REQUIRED_PARAMETER: 11},
            temporal_boundary=drifted,
        ),
        asked_at=ASKED_AT,
    )

    assert is_error is True, detail
    assert drifted.isoformat() in detail, detail
    assert ASKED_AT.isoformat() in detail, detail


def test_a_concrete_boundary_agreeing_with_asked_at_is_answered(
    assembled: Any, tmp_path: Path
) -> None:
    """`C-18` part (b), the vacuity guard: agreement is not a refusal.

    Without this leg the assertion above would be satisfied by a door that
    refused every call carrying a concrete boundary at all.
    """
    is_error, detail = _call_with(
        assembled,
        tmp_path,
        parameters={REQUIRED_PARAMETER: 11},
        encoded=WireRequest(
            product_id=assembled.address.product_class,
            parameters={REQUIRED_PARAMETER: 11},
            temporal_boundary=ASKED_AT,
        ),
        asked_at=ASKED_AT,
    )

    assert is_error is False, detail
    parsed = DoorOutcome.model_validate_json(detail)
    assert parsed.product_json is not None
    assert parsed.request.temporal_boundary == ASKED_AT


def test_an_absent_boundary_is_never_compared_against_asked_at(
    assembled: Any, tmp_path: Path
) -> None:
    """`C-18` part (c) — the guard, and the residual it declares.

    A caller sending ``as_of=None`` gets ``temporal_boundary=None`` on the
    encoded question and a client-resolved ``asked_at`` beside it (``C-02``,
    ``C-15``). There is **no second copy of the instant**, so the comparison is
    impossible and is not attempted: an unguarded comparison would refuse every
    default call, and every conformance leg over ``mcp+stdio`` would go red.

    **This is a passing test over a named residual, not a proof of safety.** On
    this path a transport altering ``asked_at`` alone is undetected, which is
    ``C-18``'s declared limit and belongs in ``C-10``'s undetected list — it is
    not closed here, because the only way to close it would be to reconstruct a
    second operand, which is the bypass this repair exists to shut.
    """
    is_error, detail = _call_with(
        assembled,
        tmp_path,
        parameters={REQUIRED_PARAMETER: 11},
        encoded=WireRequest(
            product_id=assembled.address.product_class,
            parameters={REQUIRED_PARAMETER: 11},
            temporal_boundary=None,
        ),
        asked_at=ASKED_AT + timedelta(hours=3),
    )

    assert is_error is False, detail
    parsed = DoorOutcome.model_validate_json(detail)
    assert parsed.product_json is not None
    # And the echo is as asked: `None` in, `None` out, with the door's own
    # resolved instant nowhere in it (`C-02`).
    assert parsed.request.temporal_boundary is None
