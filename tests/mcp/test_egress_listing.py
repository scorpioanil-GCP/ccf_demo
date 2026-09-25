"""Both listings, both configurations, at a REAL client — and the address answers the tool's bytes.

Ledger rows ``24.5-L-08`` and ``24.5-L-09``, criterion 10 of Phase 24.5.
Before this phase ``runtime/ccf_runtime/mcp/egress.py::build_egress_server``
registered its product resource **unconditionally** and gated only the tool,
so a TOOL-ONLY door was not expressible (``24.4-D-30``, ``D-34``; cp-04's
``server/compose.py`` docstring says so in the example's own words), and a
parameterized class had no URI a client could cite: ``PRODUCT_URI_TEMPLATE``
is three path segments with no query surface.

What this module measures, and at what strength
------------------------------------------------
Every listing assertion is made at a real ``ClientSession`` over the door's
own ASGI app — ``resources/list`` and ``resources/templates/list`` as a
consumer sees them — never by reading a decorator. The two analogs composed
here are ``tests/examples/test_cp_04_two_callers.py::enumeration`` +
``::listing_violations`` (the operation and the predicate) and
``tests/mcp/test_egress_refusal_envelope.py::_mcp_server`` + ``::_drive_mcp``
(the in-process door and its driver).

**Each configuration is sabotaged each way, twice.** The predicate is fed a
divergent listing (a door that hid the resource under the on flag; a door that
kept it under the off flag) and must go RED naming the template. Then the same
two defects are built LIVE: a scratch copy of ``egress.py`` with its guard
patched to ``if True:`` / ``if False:`` is imported from a temporary directory,
a door is built from the copy, enumerated at the real client, and the predicate
must go RED on what the client saw. The shipped module is proven untouched by
byte-comparing its source before and after.

**The address is proven to answer the tool's bytes, on a served answer AND on
a governed refusal.** ``read_resource(product_address(...))`` and
``call_tool(PRODUCT_REQUEST_TOOL, ...)`` for the same question must return
byte-identical text — the cp-04 two-callers equivalence, now at the runtime
door, where ``_answer_question`` is the one body both surfaces end in.

**Disjointness is proven against the real** ``ResourceTemplate.matches``,
**not a replica, in both directions and both configurations**, with a NEGATIVE
CONTROL that shows the rejected ``?q=`` form being captured by the product
template with ``version`` holding the query — so the test is seen to be able
to see the defect it guards.

Tenant, principal, role, class, parameter and token names are test deployment
vocabulary. The SDK holds none of them (CINV-01).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import tempfile
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.settings import AuthSettings
from mcp.types import TextContent, TextResourceContents
from pydantic import AnyHttpUrl, AnyUrl

from ccf.contracts.canonical import canonical_bytes
from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.replay.record import ResolutionNotApplicable
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.door import DoorOutcome, WireRequest, door_question
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
from ccf.products.refusal import RequestIdentity, envelope_for
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.mcp import egress as shipped_egress
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import (
    PRODUCT_ADDRESS_TEMPLATE,
    PRODUCT_REQUEST_TOOL,
    PRODUCT_URI_TEMPLATE,
    AddressedQuestion,
    build_egress_server,
    parse_product_address,
    product_address,
    product_uri,
)
from tests.mcp.guarded_servers import wide_authorizer

from crossproc.servers.mcp_egress_child import ProductAddress, build_servable_product
from ccf.controlplane.registry import ControlPlaneRegistry
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

#: Test deployment vocabulary; the SDK ships none of it.
REPLAY_ARTIFACT_CLASS = "egress-listing-replay-record"
TOKEN = "egress-listing-token"
PRINCIPAL = "egress-listing-caller"
SCOPE = "ccf:egress-listing"
ROLE = "egress-listing-role"
SERVER_NAME = "ccf-egress-listing"

#: The artifact class this module's doors file a denial under. Nothing here
#: denies, but a door that entitles binds a recorder (`D-IMPL-256` (2)).
REPLAY_RECORD_CLASS = "egress-fixture.replay-record"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 9, 2, tzinfo=UTC)
TOOL_DESCRIPTION = "Ask this test deployment's product class a question."

#: The four §6.3 axes, held constant so the only thing moving between the
#: tool call and the address read is the surface.
SUBJECT = "egress-listing-subject"
INTENT = "egress-listing-intent"
FRESHNESS = "egress-listing-freshness"
ASKED_AT = datetime(2026, 9, 2, 9, 30, tzinfo=UTC)

#: The declared surface this module's class carries, and the mapping a caller
#: sends against it — one required parameter, so a governed refusal is
#: reachable by OMITTING it rather than by hand-building a verdict.
REQUIRED_PARAMETER = "minimum_score"
CALLER_PARAMETERS: Mapping[str, Any] = {REQUIRED_PARAMETER: 11}

#: Loopback with an explicit port: FastMCP's DNS-rebinding protection allows
#: ``127.0.0.1:*`` even over ASGI, where no socket exists. Nothing binds it.
IN_PROCESS_BASE_URL = "http://127.0.0.1:8129"

#: The shipped module, as a file, for the live sabotages. Resolved from this
#: file rather than from the import so a scratch copy is a copy of THIS tree.
REPO_ROOT = Path(__file__).resolve().parents[2]
EGRESS_SOURCE = REPO_ROOT / "runtime" / "ccf_runtime" / "mcp" / "egress.py"

#: The one line the live sabotages patch. Exactly one occurrence, asserted.
RESOURCE_GUARD = "    if expose_product_resource:\n"

#: The operation names the driver runs in one lifespan.
ENUMERATE = "enumerate"
READ_ADDRESS = "read-address"
READ_PRODUCT = "read-product"
CALL_TOOL = "call-tool"


@dataclass(frozen=True)
class Refused:
    """A raised refusal, captured so one lifespan can observe every surface."""

    reason: str


Operation = Callable[[ClientSession], Awaitable[Any]]


# ---------------------------------------------------------------------------
# The predicate (the cp-04 analog, widened to both configurations).
# ---------------------------------------------------------------------------


def listing_violations(
    *, resources: list[str], templates: list[str], expect_resource: bool
) -> list[str]:
    """Every way a door's enumeration fails criterion 10, per template.

    ``resources`` must be ``[]`` in BOTH configurations — a parameterized
    class has no standing, parameter-free answer, so a concrete entry would
    advertise an instance nothing can serve. ``PRODUCT_URI_TEMPLATE`` must be
    present exactly when the resource is exposed. ``PRODUCT_ADDRESS_TEMPLATE``
    must be present whenever the tool is, and every door this module builds
    has the tool on.
    """
    violations: list[str] = []
    if resources:
        violations.append(
            f"`resources/list` carries {resources} — a parameterized class"
            " has no standing, parameter-free answer, so a concrete resource"
            " entry advertises an instance nothing can serve"
        )
    present = PRODUCT_URI_TEMPLATE in templates
    if expect_resource and not present:
        violations.append(
            f"the product resource template {PRODUCT_URI_TEMPLATE!r} is not"
            f" enumerable under expose_product_resource=True — templates are"
            f" {templates}; a door built with the default flag that hid its"
            " resource has changed every existing deployment (24.5-L-09)"
        )
    if not expect_resource and present:
        violations.append(
            f"the product resource template {PRODUCT_URI_TEMPLATE!r} IS"
            f" enumerable under expose_product_resource=False — templates are"
            f" {templates}; a tool-only door that still registers its resource"
            " is not tool-only (24.5-L-09)"
        )
    if PRODUCT_ADDRESS_TEMPLATE not in templates:
        violations.append(
            f"the product address template {PRODUCT_ADDRESS_TEMPLATE!r} is"
            f" not enumerable — templates are {templates}; the tool is on, so"
            " a parameterized product must be addressable (24.5-L-08)"
        )
    return violations


# ---------------------------------------------------------------------------
# The declared world.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product, reused by every door below."""
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-listing") / "door.sqlite3"
    )


def _contract(address: ProductAddress) -> ProductRequestContract:
    return ProductRequestContract(
        semver="1.0.0",
        schema_name=address.product_class,
        schema_version=address.version,
        arguments=SkillArgumentSchema(
            properties={
                REQUIRED_PARAMETER: SkillArgumentProperty(
                    type="integer",
                    description="The declared threshold this class answers at.",
                )
            },
            required=(REQUIRED_PARAMETER,),
        ),
    )


def _answering(outcome: object) -> Callable[..., object]:
    """A resolver that answers every call with ``outcome``."""

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        return outcome

    return resolve


def _refusing(declared: ProductRequestContract) -> Callable[..., object]:
    """A resolver that runs the one shared comparison and RECORDS its verdict.

    `D-IMPL-260` P-A: a door releases only the shell the recorder returned, so
    the verdict is handed through the one minting seam over a per-resolver
    store, exactly as the SDK's own resolver does on every refusal branch.
    """
    store = deployment_store(
        Path(tempfile.mkdtemp(prefix="egress-listing-refusing-")) / "artifacts",
        REPLAY_ARTIFACT_CLASS,
    )
    composition = ControlPlaneRegistry()

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        assert request is not None
        violation = refuse_request(request=request, declared=declared)
        assert violation is not None, (
            "this leg's caller was built to violate the declared surface and"
            " did not; the fixture, not the door, is what failed"
        )
        recorder = refusal_recorder(
            composition,
            store=store,
            tenant=tenant,
            replay_record_class=REPLAY_ARTIFACT_CLASS,
            assembly_mode="algorithmic",
        )
        return recorder.record(
            envelope_for(
                violation,
                request=RequestIdentity(
                    product_id=product_class,
                    product_version=version,
                    parameters=request.parameters,
                    temporal_boundary=request.asked_at,
                ),
            ),
            perspective=perspective,
            recorded_at=request.asked_at,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            request=request,
        )

    return resolve


# ---------------------------------------------------------------------------
# The door and its driver.
# ---------------------------------------------------------------------------


def _token_file(root: Path, *, tenant: str) -> Path:
    """The door's token file, whose one credential is scoped to ``tenant``.

    ``tenant`` is required rather than defaulted (``SEC-018``): a credential
    that names no tenant reaches nothing, so a fixture that forgot it would
    fail loudly instead of quietly minting the unscoped bearer this finding is
    about.
    """
    path = root / "egress-listing-tokens.json"
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
    register_typed_at_composition(registry, 
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


def _recorder(root: Path, *, tenant: str) -> ReplayRefusalRecorder:
    """The ONE minting seam this module's doors bind (`D-IMPL-256` (2)).

    Built with the keyword list `ccf.products.resolver::build_governed_resolver`
    uses for its own, so a door's recorder and a resolver's are the same shape
    over one store. Copied rather than imported from a sibling test module: two
    suites that answer different questions should not be coupled by a fixture.
    Nothing here denies — these doors serve — but a door that entitles does not
    build without somewhere to record a denial, and that is the point.
    """
    return refusal_recorder(
        ControlPlaneRegistry(),
        store=deployment_store(root / "artifacts", REPLAY_RECORD_CLASS),
        tenant=tenant,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
    )


def _server(
    root: Path,
    *,
    address: ProductAddress,
    resolver: Callable[..., object],
    expose_resource: bool,
    builder: Callable[..., Any] = build_egress_server,
) -> Any:
    """The real egress door, tool exposed, resource per ``expose_resource``.

    ``builder`` is the shipped :func:`build_egress_server` unless a live
    sabotage passes the builder off a scratch copy of the module.
    """
    return builder(
        server_name=SERVER_NAME,
        resolver=resolver,
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
        expose_product_resource=expose_resource,
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )


def _flatten(exc: BaseException) -> str:
    """Every message in one exception tree, joined — the door's own reason."""
    parts = [f"{type(exc).__name__}: {exc}"]
    for sub in getattr(exc, "exceptions", ()) or ():
        parts.append(_flatten(sub))
    for related in (exc.__cause__, exc.__context__):
        if related is not None and related is not exc:
            parts.append(_flatten(related))
    return " || ".join(parts)


def _drive(server: Any, operations: Mapping[str, Operation]) -> dict[str, Any]:
    """Run every operation against the server's own ASGI app, in ONE lifespan.

    One lifespan is a hard requirement rather than an optimization —
    ``tests/crossproc/test_mcp_egress.py::_both_surfaces_in_process`` records
    that ``StreamableHTTPSessionManager.run()`` refuses a second call per
    instance. Each operation gets its own session; a raised refusal is caught
    and returned as :class:`Refused` so the rest still run.
    """
    app = server.streamable_http_app()

    async def go() -> dict[str, Any]:
        results: dict[str, Any] = {}
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=IN_PROCESS_BASE_URL,
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            for name, operation in operations.items():
                try:
                    results[name] = await run_with_session(
                        url=f"{IN_PROCESS_BASE_URL}/mcp",
                        operation=operation,
                        http_client_factory=factory,
                    )
                except McpServerUnreachable as refused:
                    results[name] = Refused(reason=_flatten(refused))
        return results

    return asyncio.run(go())


def enumeration() -> Operation:
    """Both listings, as a client sees them."""

    async def operation(session: ClientSession) -> tuple[list[str], list[str]]:
        listed = await session.list_resources()
        templated = await session.list_resource_templates()
        return (
            [str(entry.uri) for entry in listed.resources],
            [entry.uriTemplate for entry in templated.resourceTemplates],
        )

    return operation


def resource_read(uri: str) -> Operation:
    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return operation


def tool_call(arguments: dict[str, Any]) -> Operation:
    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
        return bool(result.isError), "".join(
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        )

    return operation


def _question(address: ProductAddress, parameters: Mapping[str, Any]) -> WireRequest:
    """One question, with a CONCRETE boundary so the C-18 check runs on both surfaces."""
    return WireRequest(
        product_id=address.product_class,
        parameters=dict(parameters),
        temporal_boundary=ASKED_AT,
    )


def _address(address: ProductAddress, question: WireRequest) -> str:
    return product_address(
        tenant=address.tenant,
        product_class=address.product_class,
        version=address.version,
        question=question,
        subject=SUBJECT,
        intent=INTENT,
        freshness=FRESHNESS,
        asked_at=ASKED_AT,
    )


def _tool_arguments(address: ProductAddress, question: WireRequest) -> dict[str, Any]:
    return {
        "tenant": address.tenant,
        "product_class": address.product_class,
        "version": address.version,
        "request": canonical_bytes(question).decode("utf-8"),
        "subject": SUBJECT,
        "intent": INTENT,
        "freshness": FRESHNESS,
        "asked_at": ASKED_AT.isoformat(),
        "parameters": dict(question.parameters),
    }


def _enumerate(
    tmp_path: Path, assembled: Any, *, expose_resource: bool, builder: Any = None
) -> tuple[list[str], list[str]]:
    door = _server(
        tmp_path,
        address=assembled.address,
        resolver=_answering(assembled.served),
        expose_resource=expose_resource,
        **({} if builder is None else {"builder": builder}),
    )
    listed = _drive(door, {ENUMERATE: enumeration()})[ENUMERATE]
    assert not isinstance(listed, Refused), listed.reason[:1500]
    resources, templates = listed
    return resources, templates


# ---------------------------------------------------------------------------
# Criterion 10 — both listings, both configurations, at a real client.
# ---------------------------------------------------------------------------


def test_the_default_door_lists_the_product_template_and_the_address_template(
    assembled: Any, tmp_path: Path
) -> None:
    """Resource on: both templates are enumerable; `resources/list` is empty."""
    resources, templates = _enumerate(tmp_path, assembled, expose_resource=True)
    assert PRODUCT_URI_TEMPLATE in templates, templates
    assert PRODUCT_ADDRESS_TEMPLATE in templates, templates
    violations = listing_violations(
        resources=resources, templates=templates, expect_resource=True
    )
    assert not violations, "\n".join(violations)


def test_the_tool_only_door_lists_the_address_template_and_not_the_product_template(
    assembled: Any, tmp_path: Path
) -> None:
    """Resource off: ONLY the address template is enumerable (24.5-L-09)."""
    resources, templates = _enumerate(tmp_path, assembled, expose_resource=False)
    assert PRODUCT_URI_TEMPLATE not in templates, templates
    assert templates == [PRODUCT_ADDRESS_TEMPLATE], templates
    violations = listing_violations(
        resources=resources, templates=templates, expect_resource=False
    )
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("expose_resource", [True, False])
def test_resources_list_is_empty_in_both_configurations(
    assembled: Any, tmp_path: Path, expose_resource: bool
) -> None:
    resources, _ = _enumerate(tmp_path, assembled, expose_resource=expose_resource)
    assert resources == [], resources


# ---------------------------------------------------------------------------
# The sabotages — the predicate, then the live door.
# ---------------------------------------------------------------------------


def test_the_listing_check_refuses_a_tool_only_door_that_still_registers_the_resource() -> None:
    """**Sabotage control.** The resource present under the off flag is RED, naming it."""
    violations = listing_violations(
        resources=[],
        templates=[PRODUCT_URI_TEMPLATE, PRODUCT_ADDRESS_TEMPLATE],
        expect_resource=False,
    )
    assert violations, "a tool-only door that kept its resource was accepted"
    assert any(
        PRODUCT_URI_TEMPLATE in entry and "IS enumerable" in entry
        for entry in violations
    ), violations


def test_the_listing_check_refuses_a_default_door_that_hid_the_resource() -> None:
    """**Sabotage control.** The resource absent under the on flag is RED, naming it."""
    violations = listing_violations(
        resources=[], templates=[PRODUCT_ADDRESS_TEMPLATE], expect_resource=True
    )
    assert violations, "a default door that hid its resource was accepted"
    assert any(
        PRODUCT_URI_TEMPLATE in entry and "is not" in entry for entry in violations
    ), violations


def _sabotaged_builder(
    tmp_path_factory: pytest.TempPathFactory, *, guard_becomes: str, name: str
) -> Any:
    """A scratch copy of ``egress.py`` with its resource guard patched.

    The copy lives under the session scratch root, is imported under a unique
    module name, and is never written back. The caller byte-compares the
    shipped source before and after.
    """
    source = EGRESS_SOURCE.read_text(encoding="utf-8")
    assert source.count(RESOURCE_GUARD) == 1, (
        f"expected exactly one {RESOURCE_GUARD!r} in the shipped module;"
        f" found {source.count(RESOURCE_GUARD)}"
    )
    patched = source.replace(RESOURCE_GUARD, guard_becomes)
    assert patched != source
    scratch = tmp_path_factory.mktemp("egress-sabotage") / f"egress_{name}.py"
    scratch.write_text(patched, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"egress_sabotaged_{name}", scratch)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_egress_server


def test_a_live_door_that_registers_the_resource_under_the_off_flag_is_refused(
    assembled: Any, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """**Live sabotage.** Guard patched to ``if True:``; the real client sees the resource; RED."""
    before = EGRESS_SOURCE.read_bytes()
    builder = _sabotaged_builder(
        tmp_path_factory, guard_becomes="    if True:\n", name="always_registers"
    )
    resources, templates = _enumerate(
        tmp_path, assembled, expose_resource=False, builder=builder
    )
    assert PRODUCT_URI_TEMPLATE in templates, (
        "the sabotage did not take: the patched copy hid its resource"
    )
    violations = listing_violations(
        resources=resources, templates=templates, expect_resource=False
    )
    assert violations, "a live tool-only door that kept its resource was accepted"
    assert any(PRODUCT_URI_TEMPLATE in entry for entry in violations), violations
    assert EGRESS_SOURCE.read_bytes() == before, "the shipped module was touched"
    assert shipped_egress.__file__ == str(EGRESS_SOURCE)


def test_a_live_door_that_hides_the_resource_under_the_on_flag_is_refused(
    assembled: Any, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """**Live sabotage.** Guard patched to ``if False:``; the real client sees no resource; RED."""
    before = EGRESS_SOURCE.read_bytes()
    builder = _sabotaged_builder(
        tmp_path_factory, guard_becomes="    if False:\n", name="never_registers"
    )
    resources, templates = _enumerate(
        tmp_path, assembled, expose_resource=True, builder=builder
    )
    assert PRODUCT_URI_TEMPLATE not in templates, (
        "the sabotage did not take: the patched copy still registered its resource"
    )
    violations = listing_violations(
        resources=resources, templates=templates, expect_resource=True
    )
    assert violations, "a live default door that hid its resource was accepted"
    assert any(PRODUCT_URI_TEMPLATE in entry for entry in violations), violations
    assert EGRESS_SOURCE.read_bytes() == before, "the shipped module was touched"


def test_a_surface_less_door_is_refused(assembled: Any, tmp_path: Path) -> None:
    """Neither the resource nor the tool: refused at construction, in the D-03 voice."""
    with pytest.raises(ValueError, match="D-03") as refused:
        build_egress_server(
            server_name=SERVER_NAME,
            resolver=_answering(assembled.served),  # type: ignore[arg-type]
            token_verifier=SourceBackedTokenVerifier(
                source=FileTokenSource(path=_token_file(tmp_path, tenant=assembled.address.tenant))
            ),
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl("https://issuer.invalid"),
                resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
                required_scopes=[SCOPE],
            ),
            authorizer=wide_authorizer(scopes=(SCOPE,)),
            entitlement_source=_entitlement(assembled.address),
            perspective_resolver=(
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role=ROLE
                )
            ),
            # Bound so the D-03 refusal below is the one under test. Since
            # `D-IMPL-256` (2) the recorder check runs FIRST — deliberately, so
            # that a door which could deny unrecorded never reaches the point
            # of having surfaces to argue about — and an unbound door would
            # raise the wrong `ValueError` here.
            refusal_recorder=_recorder(tmp_path, tenant=assembled.address.tenant),
            expose_product_resource=False,
            expose_product_tool=False,
        )
    assert "neither surface" in str(refused.value)


# ---------------------------------------------------------------------------
# 24.5-L-08 — the address answers the tool's bytes.
# ---------------------------------------------------------------------------


def _resolver_for(assembled: Any, leg: str) -> tuple[Callable[..., object], Mapping[str, Any]]:
    """The served leg and the refused leg: one resolver each, and the parameters that reach it."""
    if leg == "served":
        return _answering(assembled.served), CALLER_PARAMETERS
    # Omit the required parameter, so the resolver's own comparison refuses.
    return _refusing(_contract(assembled.address)), {}


@pytest.mark.parametrize("leg", ["served", "refused"])
@pytest.mark.parametrize("expose_resource", [True, False])
def test_reading_the_product_address_answers_the_tool_s_bytes(
    assembled: Any, tmp_path: Path, expose_resource: bool, leg: str
) -> None:
    """`read_resource(product_address(q))` == `call_tool(q)`, byte for byte, on both legs."""
    address = assembled.address
    resolver, parameters = _resolver_for(assembled, leg)
    question = _question(address, parameters)
    door = _server(
        tmp_path, address=address, resolver=resolver, expose_resource=expose_resource
    )
    results = _drive(
        door,
        {
            READ_ADDRESS: resource_read(_address(address, question)),
            CALL_TOOL: tool_call(_tool_arguments(address, question)),
        },
    )
    read = results[READ_ADDRESS]
    assert not isinstance(read, Refused), read.reason[:1500]
    called = results[CALL_TOOL]
    assert not isinstance(called, Refused), called.reason[:1500]
    is_error, tool_text = called
    assert is_error is False, tool_text[:1500]

    assert read == tool_text, (
        "the address and the tool answered the same question differently:\n"
        f"address: {read[:800]}\ntool:    {tool_text[:800]}"
    )
    outcome = DoorOutcome.model_validate_json(read)
    assert outcome.request == question
    if leg == "served":
        assert outcome.refusal is None
        assert outcome.product_json == canonical_bytes(assembled.servable.product).decode(
            "utf-8"
        )
    else:
        assert outcome.product_json is None
        assert outcome.refusal is not None
        assert outcome.refusal.reason == "missing-required-parameter"
        assert outcome.refusal.key == REQUIRED_PARAMETER


def test_the_address_round_trips_and_its_segment_is_drawn_from_the_unpadded_alphabet(
    assembled: Any,
) -> None:
    """`parse_product_address(product_address(...))` inverts; `q` holds only `A-Z a-z 0-9 - _`."""
    address = assembled.address
    question = _question(address, CALLER_PARAMETERS)
    uri = _address(address, question)
    q = uri.rsplit("/", 1)[1]
    assert uri.startswith(product_uri(**address._asdict()) + "/q/")
    assert set(q) <= set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    ), q
    for forbidden in "=/+?%":
        assert forbidden not in q

    tenant, product_class, version, addressed = parse_product_address(uri)
    assert (tenant, product_class, version) == tuple(address)
    assert isinstance(addressed, AddressedQuestion)
    assert door_question(addressed.request) == question
    assert (addressed.subject, addressed.intent, addressed.freshness) == (
        SUBJECT,
        INTENT,
        FRESHNESS,
    )
    assert addressed.asked_at == ASKED_AT
    # Canonical: two equal questions give one address.
    assert _address(address, _question(address, dict(CALLER_PARAMETERS))) == uri


def test_an_address_with_a_naive_instant_cannot_be_minted(assembled: Any) -> None:
    """The tool's first refusal, at mint time: an unanswerable address is never made."""
    address = assembled.address
    with pytest.raises(ValueError, match="D-IMPL-38"):
        product_address(
            tenant=address.tenant,
            product_class=address.product_class,
            version=address.version,
            question=_question(address, CALLER_PARAMETERS),
            subject=SUBJECT,
            intent=INTENT,
            freshness=FRESHNESS,
            asked_at=ASKED_AT.replace(tzinfo=None),
        )


def test_a_tampered_address_is_refused_by_name(assembled: Any, tmp_path: Path) -> None:
    """A flipped `q`, a padded `q`, a four-segment URI, a fourth segment that is not `q`.

    Each is refused by the parser naming the segment, and each is refused at
    the REAL client without ever returning the tool's bytes. The flipped
    character is the FIRST of `q`: it lands in the JSON opening brace, so the
    tamper is guaranteed to break the body rather than to land inside a string
    value and answer a different question as though it were the caller's.
    """
    address = assembled.address
    question = _question(address, CALLER_PARAMETERS)
    honest = _address(address, question)
    plain, q = honest.rsplit("/q/", 1)
    flipped_first = ("f" if q[0] != "f" else "g") + q[1:]

    cases = {
        "flipped": f"{plain}/q/{flipped_first}",
        "padded": f"{honest}=",
        "four-segment": f"{plain}/{q}",
        "fourth-not-q": f"{plain}/query/{q}",
    }
    for name, uri in cases.items():
        with pytest.raises(ValueError, match="`q`") as refused:
            parse_product_address(uri)
        assert "`q`" in str(refused.value), (name, refused.value)

    # The four-segment and fourth-not-q forms match neither template, so at
    # the client they are unknown resources; the flipped and padded forms match
    # the ADDRESS template and are refused inside the parser, by name.
    door = _server(
        tmp_path,
        address=address,
        resolver=_answering(assembled.served),
        expose_resource=True,
    )
    results = _drive(
        door,
        {
            CALL_TOOL: tool_call(_tool_arguments(address, question)),
            **{name: resource_read(uri) for name, uri in cases.items()},
        },
    )
    _, tool_text = results[CALL_TOOL]
    for name in cases:
        outcome = results[name]
        assert isinstance(outcome, Refused), (
            f"the {name} address was ANSWERED: {str(outcome)[:600]}"
        )
        assert tool_text not in outcome.reason
        if name in ("flipped", "padded"):
            assert "segment `q`" in outcome.reason, (name, outcome.reason[:1500])
        else:
            assert "Unknown resource" in outcome.reason, (name, outcome.reason[:1500])


# ---------------------------------------------------------------------------
# Disjointness — against the real ResourceTemplate.matches, both directions.
# ---------------------------------------------------------------------------


def _templates_of(door: Any) -> dict[str, Any]:
    """The registered templates — the same objects `resources/templates/list` reports."""
    return {
        template.uri_template: template
        for template in door._resource_manager.list_templates()
    }


@pytest.mark.parametrize("expose_resource", [True, False])
def test_a_plain_product_uri_does_not_match_the_address_template(
    assembled: Any, tmp_path: Path, expose_resource: bool
) -> None:
    """Both directions, on the real matcher — with the rejected `?q=` form shown captured."""
    address = assembled.address
    question = _question(address, CALLER_PARAMETERS)
    plain = product_uri(**address._asdict())
    addressed = _address(address, question)
    door = _server(
        tmp_path,
        address=address,
        resolver=_answering(assembled.served),
        expose_resource=expose_resource,
    )
    templates = _templates_of(door)

    address_template = templates[PRODUCT_ADDRESS_TEMPLATE]
    assert address_template.matches(plain) is None, (
        "a plain three-segment product URI matched the five-segment address"
        " template"
    )
    matched = address_template.matches(addressed)
    assert matched is not None and matched["q"] == addressed.rsplit("/", 1)[1]

    if expose_resource:
        product_template = templates[PRODUCT_URI_TEMPLATE]
        assert product_template.matches(addressed) is None, (
            "an address matched the product template — a placeholder crossed"
            " a slash"
        )
        # NEGATIVE CONTROL: the rejected query-string form IS captured by the
        # product template, with `version` holding the whole query. This is
        # the defect the path-segment form exists to avoid, seen on the real
        # matcher rather than described.
        rejected_form = f"{plain}?q=eyJhIjoxfQ"
        captured = product_template.matches(rejected_form)
        assert captured is not None, "the negative control did not capture"
        assert captured["version"] == f"{address.version}?q=eyJhIjoxfQ", captured
    else:
        assert PRODUCT_URI_TEMPLATE not in templates


@pytest.mark.parametrize("expose_resource", [True, False])
def test_an_address_uri_does_not_reach_the_product_handler(
    assembled: Any, tmp_path: Path, expose_resource: bool
) -> None:
    """At the real client: the address returns the TOOL's bytes; the plain URI never does."""
    address = assembled.address
    question = _question(address, CALLER_PARAMETERS)
    plain = product_uri(**address._asdict())
    door = _server(
        tmp_path,
        address=address,
        resolver=_answering(assembled.served),
        expose_resource=expose_resource,
    )
    results = _drive(
        door,
        {
            READ_ADDRESS: resource_read(_address(address, question)),
            READ_PRODUCT: resource_read(plain),
            CALL_TOOL: tool_call(_tool_arguments(address, question)),
        },
    )
    _, tool_text = results[CALL_TOOL]
    read_address = results[READ_ADDRESS]
    assert not isinstance(read_address, Refused), read_address.reason[:1500]
    assert read_address == tool_text

    read_product = results[READ_PRODUCT]
    vessel = canonical_bytes(assembled.servable.product).decode("utf-8")
    if expose_resource:
        # The resource's bytes are the bare vessel, never the tool's envelope.
        assert read_product == vessel
        assert read_product != tool_text
    else:
        assert isinstance(read_product, Refused), (
            f"a tool-only door ANSWERED the plain product URI: {str(read_product)[:600]}"
        )
        assert "Unknown resource" in read_product.reason, read_product.reason[:1500]
        assert tool_text not in read_product.reason
        assert vessel not in read_product.reason
