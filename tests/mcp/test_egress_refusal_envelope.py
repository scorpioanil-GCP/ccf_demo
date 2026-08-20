"""The MCP door says "no" in the one shape, and both doors name the record.

``D-IMPL-148`` (Dave, 2026-08-17) **as amended by Addendum A the same day**.
Two rulings are executed here and they arrived as one change because they need
the same one:

* **The refusal is the tool's return value, never a raise.** Measured against
  ``mcp==1.28.1``, a FastMCP tool that raises reaches the client as
  ``isError=True`` carrying ``ToolError: Error executing tool <name>:
  <message>`` — so a client wanting the governed answer would have to strip a
  server's wording. String-parsing prose for an audited verdict is not a
  channel, and that is why the shape moved.
* **Both doors carry the replay reference.** ``Result.replay_ref`` is in
  ``GUARDED_FIELDS`` and ``assert_served_parity`` compares every declared field,
  so an adapter bound against a door that emits none would fail parity on it.
  The base entry scoped the fix to the MCP door; Dave superseded that with
  *both, not one* — the principle ``D-IMPL-133`` applied to ``parameters``.

Because the tool's return had to become a structure for the refusal, the
reference rides that same change rather than forcing a second one. The HTTP door
has a header channel, so it publishes the identical string there and its body
stays the vessel.

What this module measures, and at what strength
------------------------------------------------
The unit under test is **what a door emits**, decoded the way a client decodes
it — :meth:`~ccf.products.door.DoorOutcome.model_validate_json` over the tool's
text, and the response header over HTTP. It is deliberately not a source
reading: a door that imported the envelope and never emitted one would pass a
grep and fail every assertion below.

**Served and refused are discriminated structurally.** Every leg validates the
tool's text as a :class:`~ccf.products.door.DoorOutcome` and reads the member;
nothing here sniffs for a key or matches a string. The two halves are exclusive
by a model validator, and underneath that
:class:`~ccf.products.refusal.RefusalEnvelope` and the vessel are both
``extra=forbid`` with disjoint required fields, so neither can validate as the
other.

The controls (``D-22``)
------------------------
Every assertion is a function taking its subject as a parameter, and each
control calls *that same function* with a divergent subject — never a copy of
it, and never by editing ``runtime/`` and reverting. A control implemented as an
edit leaves nothing in the tree; a control implemented as a test runs on every
CI run forever. This is the discipline plan ``17-10`` Task 1 already shipped in
``tests/mcp/test_egress_parameters.py``.

Tenant, principal, role, class, parameter, artifact and token names are test
deployment vocabulary. The SDK holds none of them (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.settings import AuthSettings
from mcp.types import TextContent
from pydantic import AnyHttpUrl, ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.door import DoorOutcome, door_refusal
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.gates import TTLRefusal
from ccf.products.refusal import RefusalEnvelope, RequestIdentity
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    refuse_request,
)
from ccf.projection.plan import Perspective
from ccf.replay.serve import ServedProduct
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    ProductEntitlementRefused,
)
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import REPLAY_REF_HEADER
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL, build_egress_server

from crossproc.servers.mcp_egress_child import ProductAddress, build_servable_product

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "egress-refusal-token"
PRINCIPAL = "egress-refusal-caller"
SCOPE = "ccf:egress-refusal"
ROLE = "egress-refusal-role"
SERVER_NAME = "ccf-egress-refusal"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 17, tzinfo=UTC)
TOOL_DESCRIPTION = "Ask this test deployment's product class a question."
REPLAY_ARTIFACT_CLASS = "egress-refusal-replay-record"
REPLAY_ARTIFACT_NAME = "egress-refusal-snapshot"

#: The four §6.3 axes, held constant so the only thing moving between legs is
#: what the deployment's resolver answered with.
SUBJECT = "egress-refusal-subject"
INTENT = "egress-refusal-intent"
FRESHNESS = "egress-refusal-freshness"
ASKED_AT = datetime(2026, 8, 17, 9, 30, tzinfo=UTC)

#: The declared surface this module's class carries, and the mapping a caller
#: sends against it. One required parameter, so a request violation is
#: reachable by *omitting* it rather than by hand-building a verdict.
REQUIRED_PARAMETER = "minimum_score"
UNDECLARED_PARAMETER = "not_declared_by_this_class"
CALLER_PARAMETERS: Mapping[str, Any] = {REQUIRED_PARAMETER: 11}

#: Loopback with an explicit port: FastMCP's DNS-rebinding protection allows
#: ``127.0.0.1:*`` even over ASGI, where no socket exists. Nothing binds it.
IN_PROCESS_BASE_URL = "http://127.0.0.1:8127"

#: What a door answers with, as a callable — the unit the replay-reference
#: assertion compares two doors as, and the unit a control substitutes.
AskRef = Callable[[], str | None]

#: What a door does with a refusal it was handed. The subject of the
#: governance-boundary assertion; a control passes a divergent one.
Renderer = Callable[[ProductEntitlementRefused], RefusalEnvelope | None]


# ---------------------------------------------------------------------------
# The shipped assertions — functions over their subjects (D-22).
# ---------------------------------------------------------------------------


def assert_refusals_identical(
    first: RefusalEnvelope, second: RefusalEnvelope
) -> None:
    """Two decoded refusals agree on **every declared field**.

    The D-15(b) leg in miniature, and written the way
    ``tests/client/conformance/suite.py`` writes its own: the field list is
    **derived from the type**, never transcribed. A member added to
    :class:`~ccf.products.refusal.RefusalEnvelope` next year is compared here
    without an edit, which is what stops this assertion from quietly narrowing
    as the contract widens.

    Comparing whole objects with ``==`` would be shorter and strictly worse: it
    reports *"they differ"* and names nothing, so the first real failure would
    send a reader diffing two multi-page envelopes by eye.

    Args:
        first: One decoded refusal.
        second: The other, for the same question.

    Raises:
        AssertionError: any declared field disagreed.
    """
    differences = [
        f"{name}: {getattr(first, name)!r} != {getattr(second, name)!r}"
        for name in RefusalEnvelope.model_fields
        if getattr(first, name) != getattr(second, name)
    ]
    if differences:
        raise AssertionError(
            "two refusals for the same question disagreed — "
            + "; ".join(differences)
            + ". A refusal that changes shape at a transport is a refusal a"
            " cross-adapter parity suite cannot compare, which is what"
            " `D-IMPL-148` refused to work around by exempting the field"
        )


def assert_governance_stays_a_raise(render: Renderer) -> None:
    """A governance refusal is never rendered as a fabric refusal envelope.

    The boundary is a **decision**, and this is where it is drawn rather than
    merely omitted. ``ProductEntitlementRefused`` is decided before the resolver
    is reached, and contract-level entitlement at the client seam is on the v0
    not-list (``D-IMPL-129``); an envelope for it would report *"the fabric
    answered no"* about a caller the fabric never answered at all — an audit
    record of a decision that was not made.

    The subject is the **renderer**, not the door, so the control below can pass
    a divergent one into this same function.

    Args:
        render: What a door does with a governance refusal. The shipped subject
            is :func:`~ccf.products.door.door_refusal`, which returns ``None``
            because the type is outside the envelope's vocabulary.

    Raises:
        AssertionError: the renderer produced an envelope.
    """
    rendered = render(
        ProductEntitlementRefused(
            error_code="ERROR_TEST_PRINCIPAL_NOT_ENTITLED",
            message="this principal is not entitled to this class",
        )
    )
    if rendered is not None:
        raise AssertionError(
            "a governance refusal was rendered as a fabric refusal envelope"
            f" (kind {rendered.kind!r}); 'not entitled' and 'the fabric said no'"
            " are different decisions, and a consumer that could not tell them"
            " apart would record an audited fabric refusal that never happened"
        )


def assert_both_doors_carry_the_replay_ref(
    ask_mcp: AskRef, ask_http: AskRef
) -> None:
    """Both doors name the same replay record for the same served product.

    ``D-IMPL-148`` **Addendum A**'s *"both, not one"*, executable — the shape
    ``assert_same_verdicts`` already has in
    ``tests/mcp/test_egress_parameters.py``, for the same reason: one shared
    subject asked of both real doors is what keeps them from drifting apart one
    edit at a time.

    **Absence is checked before equality, and that ordering is the point.** Two
    doors that both emitted ``None`` would agree perfectly while carrying
    nothing — the vacuous pass this repository ships repeatedly — so a ``None``
    from either side is refused by name rather than compared.

    Args:
        ask_mcp: The MCP tool, as a callable returning the reference it emitted.
        ask_http: The HTTP route, in the same shape.

    Raises:
        AssertionError: either door emitted no reference, or the two disagreed.
    """
    mcp_ref = ask_mcp()
    http_ref = ask_http()
    absent = [
        name
        for name, ref in (("the MCP tool", mcp_ref), ("the HTTP route", http_ref))
        if ref is None
    ]
    if absent:
        raise AssertionError(
            f"{' and '.join(absent)} emitted no replay reference for a product"
            " whose resolver produced one. Two doors that both emit nothing"
            " agree perfectly while carrying nothing, which is why absence is"
            " refused here rather than compared — and it is the exact state"
            " `D-IMPL-148` was raised about"
        )
    if mcp_ref != http_ref:
        raise AssertionError(
            f"the MCP tool named {mcp_ref!r} and the HTTP route named"
            f" {http_ref!r} for the same served product; the reference is a"
            " property of the decision, not of the transport that reported it"
        )


# ---------------------------------------------------------------------------
# The declared world both doors are measured against.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product, reused by every door below."""
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-refusal") / "door.sqlite3"
    )


def _contract(address: ProductAddress) -> ProductRequestContract:
    """The request surface this module's class declares — one required integer."""
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


def _replay_ref(address: ProductAddress) -> ArtifactRef:
    """The reference a deployment's replay append would have produced."""
    return ArtifactRef(
        content_address="a" * 64,
        uri=f"ccf-artifact://{address.tenant}/{REPLAY_ARTIFACT_CLASS}/1",
        tenant_id=address.tenant,
        artifact_class=REPLAY_ARTIFACT_CLASS,
        name=REPLAY_ARTIFACT_NAME,
    )


def _identity(address: ProductAddress) -> RequestIdentity:
    """The question, as the door carried it."""
    return RequestIdentity(
        product_id=address.product_class,
        product_version=address.version,
        parameters=dict(CALLER_PARAMETERS),
        temporal_boundary=ASKED_AT,
    )


def _ttl_refusal() -> TTLRefusal:
    """One gate refusal with fields of its own beyond ``gate`` and ``detail``."""
    return TTLRefusal(
        gate="ttl",
        detail="expires_at fell outside (now, now + MAX_TTL]",
        expires_at=ASKED_AT + timedelta(days=400),
        now=ASKED_AT,
        max_ttl_seconds=3600,
    )


def _answering(outcome: object) -> Callable[..., object]:
    """A resolver that answers every call with ``outcome``, whatever it is.

    The seam is typed to ``ServableProduct`` and this returns a wider set on
    purpose: the whole subject of this module is what a door does with the
    shapes a deployment's resolver actually returns (``D-IMPL-148``
    Addendum A), and a fixture narrowed to the declared type could not present
    any of them.
    """

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
    """A resolver that runs the one shared comparison and returns its verdict.

    It calls :func:`~ccf.products.request.refuse_request` — the obligation
    ``ProductResolverProtocol`` puts on every resolver — so the violation these
    legs carry is one the fabric genuinely produced rather than one this module
    hand-built to the shape it wanted to see.
    """

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
        return violation

    return resolve


# ---------------------------------------------------------------------------
# The MCP door.
# ---------------------------------------------------------------------------


def _token_file(root: Path) -> Path:
    path = root / "egress-refusal-tokens.json"
    path.write_text(
        json.dumps({TOKEN: {"client_id": PRINCIPAL, "scopes": [SCOPE]}}),
        encoding="utf-8",
    )
    return path


def _entitlement(
    address: ProductAddress, *, classes: frozenset[str] | None = None
) -> ControlPlaneProductEntitlementSource:
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version=POLICY_VERSION,
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=(
                        frozenset({address.product_class})
                        if classes is None
                        else classes
                    ),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )


def _mcp_server(
    root: Path,
    *,
    address: ProductAddress,
    resolver: Callable[..., object],
    classes: frozenset[str] | None = None,
) -> Any:
    """The real egress door, tool exposed, over the supplied resolver."""
    return build_egress_server(
        server_name=SERVER_NAME,
        resolver=resolver,  # type: ignore[arg-type]
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=_token_file(root))
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[SCOPE],
        ),
        entitlement_source=_entitlement(address, classes=classes),
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )


def _tool_arguments(
    address: ProductAddress, parameters: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "tenant": address.tenant,
        "product_class": address.product_class,
        "version": address.version,
        # The caller's own question, encoded (`C-16`). Built from the same
        # values the address arguments beside it carry, because the door
        # refuses a call that encodes one question and addresses another.
        "request": canonical_bytes(
            WireRequest(
                product_id=address.product_class,
                parameters=dict(parameters),
                temporal_boundary=None,
            )
        ).decode("utf-8"),
        "subject": SUBJECT,
        "intent": INTENT,
        "freshness": FRESHNESS,
        "asked_at": ASKED_AT.isoformat(),
        "parameters": dict(parameters),
    }


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


def _ask_mcp_door(
    root: Path,
    *,
    address: ProductAddress,
    resolver: Callable[..., object],
    parameters: Mapping[str, Any] = CALLER_PARAMETERS,
    classes: frozenset[str] | None = None,
) -> tuple[bool, str]:
    """Ask the real MCP tool one question; return ``(is_error, text)``."""
    return _drive_mcp(
        _mcp_server(root, address=address, resolver=resolver, classes=classes),
        _tool_operation(_tool_arguments(address, parameters)),
    )


def _decode(text: str) -> DoorOutcome:
    """What a client does with the tool's text — validate it, never sniff it.

    :class:`~ccf.products.door.DoorOutcome` is ``extra=forbid``, so a door that
    emitted the bare vessel or an ad-hoc dict fails here rather than being
    read as an outcome with missing halves.
    """
    return DoorOutcome.model_validate_json(text)


# ---------------------------------------------------------------------------
# The HTTP door.
# ---------------------------------------------------------------------------


def _http_app(
    root: Path, *, address: ProductAddress, resolver: Callable[..., object]
) -> Any:
    return create_app(
        ApiDependencies(
            control_plane=ControlPlaneRegistry(),
            artifact_store=FileArtifactStore(root=root / "artifacts"),
            product_resolver=resolver,  # type: ignore[arg-type]
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


def _ask_http_door(
    root: Path, *, address: ProductAddress, resolver: Callable[..., object]
) -> httpx.Response:
    """Ask the real HTTP route the same question, with the same parameters."""
    app = _http_app(root, address=address, resolver=resolver)

    async def go() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://fabric.invalid",
        ) as client:
            return await client.get(
                f"/product/{address.tenant}/{address.product_class}"
                f"/{address.version}",
                params={
                    "subject": SUBJECT,
                    "intent": INTENT,
                    "freshness": FRESHNESS,
                    "asked_at": ASKED_AT.isoformat(),
                    "parameters": json.dumps(dict(CALLER_PARAMETERS)),
                },
                headers={"Authorization": f"Bearer {TOKEN}"},
            )

    return asyncio.run(go())


# ---------------------------------------------------------------------------
# The behaviours.
# ---------------------------------------------------------------------------


def test_a_request_the_class_does_not_answer_returns_an_envelope(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 1: a refusal is a **return value**, and its kind names it.

    What would fail here: the door letting the refusal reach the client as a
    raised ``ToolError``. That is not a hypothetical shape — it is what
    ``mcp==1.28.1`` does with any exception a tool body lets escape, prose
    prefix and all, and it is the measurement that decided this design.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_refusing(_contract(address)),
        parameters={},
    )

    assert is_error is False, (
        f"the tool refused at the protocol level rather than returning the"
        f" governed refusal: {text}"
    )
    outcome = _decode(text)
    assert outcome.product_json is None
    assert outcome.refusal is not None
    assert outcome.refusal.kind == "product-request-violation"
    assert outcome.refusal.reason == "missing-required-parameter"
    assert outcome.refusal.key == REQUIRED_PARAMETER


def test_a_gate_refusal_carries_its_own_typed_fields(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 2: nothing the refusal type declared is flattened out.

    What would fail here: a door that promoted ``gate`` and ``detail`` and
    dropped the rest. The three fields a ``TTLRefusal`` declares of its own are
    exactly what a consumer needs to tell *how far* outside the window the
    product fell, and a refusal reduced to a token cannot be audited.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path, address=address, resolver=_answering(_ttl_refusal())
    )

    assert is_error is False, text
    refusal = _decode(text).refusal
    assert refusal is not None
    assert refusal.kind == "ttl-refusal"
    # The gate token wins the `reason` promotion for the whole gate family.
    assert refusal.reason == "ttl"
    assert set(refusal.fields) == {"expires_at", "now", "max_ttl_seconds"}
    assert refusal.fields["max_ttl_seconds"] == "3600"


def test_the_envelope_carries_the_pre_assembly_request_identity(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 3: the question travels with the refusal — and no door emitted it.

    Constraint (b) of the envelope's own ruling. ``parameters`` is the member
    worth asserting by value: it is the half plan ``17-10`` Task 1 taught the
    door to carry, and a refusal that named the class but not the arguments
    would be an audit record of *which* question was refused with the question
    left out.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path, address=address, resolver=_answering(_ttl_refusal())
    )

    assert is_error is False, text
    refusal = _decode(text).refusal
    assert refusal is not None
    assert refusal.request == _identity(address)
    assert dict(refusal.request.parameters) == dict(CALLER_PARAMETERS)
    assert refusal.request.temporal_boundary == ASKED_AT


def test_a_governance_refusal_still_raises_and_is_not_enveloped(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 4: the boundary, drawn rather than missed.

    Both halves are asserted because neither implies the other: on the wire an
    unentitled caller gets the protocol-native error and **no** ``DoorOutcome``
    at all, and in the translation the shipped renderer produces no envelope
    for the type. A door could get the first right by accident — the exception
    is raised before the resolver — and still acquire a translation later.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_answering(assembled.servable),
        classes=frozenset({"a-class-this-caller-was-never-granted"}),
    )

    assert is_error is True
    with pytest.raises(ValidationError):
        _decode(text)

    assert_governance_stays_a_raise(
        lambda refused: door_refusal(
            refused,
            asked=None,
            product_class=address.product_class,
            version=address.version,
        )
    )


def test_the_mcp_refusal_is_field_identical_to_the_in_process_one(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 5: the crossing loses nothing — the leg D-15(b) will consume.

    One resolver, driven two ways. In process a caller holds the envelope the
    resolver returned; over MCP the *same* envelope is canonically serialized,
    carried, and re-validated. Field-identity is therefore a statement about
    the **crossing** rather than about two implementations happening to agree,
    which is the only form of it a parity suite can lean on.
    """
    address = assembled.address
    declared = _contract(address)
    resolver = _refusing(declared)

    in_process = resolver(
        tenant=address.tenant,
        product_class=address.product_class,
        version=address.version,
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        request=ProductRequest(
            schema_name=address.product_class,
            schema_version=address.version,
            subject=SUBJECT,
            intent=INTENT,
            freshness=FRESHNESS,
            asked_at=ASKED_AT,
            parameters={},
        ),
    )
    is_error, text = _ask_mcp_door(
        tmp_path, address=address, resolver=resolver, parameters={}
    )

    assert is_error is False, text
    over_the_wire = _decode(text).refusal
    assert over_the_wire is not None
    assert_refusals_identical(
        door_refusal(
            in_process,
            asked=ProductRequest(
                schema_name=address.product_class,
                schema_version=address.version,
                subject=SUBJECT,
                intent=INTENT,
                freshness=FRESHNESS,
                asked_at=ASKED_AT,
                parameters={},
            ),
            product_class=address.product_class,
            version=address.version,
        )
        or pytest.fail("the in-process leg produced no refusal"),
        over_the_wire,
    )


def test_the_mcp_door_carries_the_replay_reference(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 6: ``D-IMPL-148``'s own subject, on the door it was raised about.

    What would fail here: the door serving the vessel and discarding the
    reference beside it, which is what all three shipped doors did and what
    ``WireOutcome.replay_ref`` had already called *"a defect the client seam
    exists to fix"*.

    The vessel is asserted too, and byte-for-byte: the envelope is a frame
    around the producer's bytes, never a re-rendering of them.
    """
    address = assembled.address
    ref = _replay_ref(address)
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_answering(
            ServedProduct(product=assembled.servable.product, replay_ref=ref)
        ),
    )

    assert is_error is False, text
    outcome = _decode(text)
    assert outcome.refusal is None
    assert outcome.replay_ref == ref.uri
    assert outcome.product_json == canonical_bytes(
        assembled.servable.product
    ).decode("utf-8")


def test_both_doors_carry_the_same_replay_reference(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 7: Addendum A's *"both, not one"*, through the real assertion.

    The two doors are passed as callables so the control below substitutes a
    divergent one into **this same** function rather than into a copy of it.
    """
    address = assembled.address
    ref = _replay_ref(address)
    served = ServedProduct(product=assembled.servable.product, replay_ref=ref)
    http_root = tmp_path / "http"
    http_root.mkdir()

    def ask_mcp() -> str | None:
        is_error, text = _ask_mcp_door(
            tmp_path, address=address, resolver=_answering(served)
        )
        assert is_error is False, text
        return _decode(text).replay_ref

    def ask_http() -> str | None:
        response = _ask_http_door(
            http_root, address=address, resolver=_answering(served)
        )
        assert response.status_code == 200, response.text
        return response.headers.get(REPLAY_REF_HEADER)

    assert_both_doors_carry_the_replay_ref(ask_mcp, ask_http)


def test_a_resolver_that_carries_no_reference_reports_its_absence(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 8: ``None`` means *the resolver produced none*, on both doors.

    The narrower ``ServableProduct`` carries no reference, so a door answering
    from one has nothing to name. Both doors say so by **omission** rather than
    by an empty value: an empty header and an empty string would make "no
    record was named" and "the record is named by nothing" the same
    observation, and only one of those is a wiring defect.
    """
    address = assembled.address
    http_root = tmp_path / "http-absent"
    http_root.mkdir()

    is_error, text = _ask_mcp_door(
        tmp_path, address=address, resolver=_answering(assembled.servable)
    )
    response = _ask_http_door(
        http_root, address=address, resolver=_answering(assembled.servable)
    )

    assert is_error is False, text
    assert _decode(text).replay_ref is None
    assert response.status_code == 200, response.text
    assert REPLAY_REF_HEADER not in response.headers
    # The served half is untouched by the reference being absent.
    assert response.content == canonical_bytes(assembled.servable.product)


def test_the_served_and_refused_shapes_cannot_validate_as_each_other(
    assembled: Any,
) -> None:
    """Behaviour 9: discrimination is **structural**, and never a sniff.

    The ruling's own words. Three checks, and the conjunction is the claim:
    the bare vessel is not a ``DoorOutcome``, so a door that emitted one would
    be caught rather than read as an outcome with missing halves; and the
    vessel and the envelope cannot validate as each other, because both are
    ``extra=forbid`` with disjoint required fields.

    Without this a consumer would have to branch on the presence of a key —
    which is a sniff, and which silently starts answering differently the day
    either contract gains a member.
    """
    vessel = canonical_bytes(assembled.servable.product).decode("utf-8")
    envelope = RefusalEnvelope(
        kind="ttl-refusal",
        reason="ttl",
        key=None,
        detail="expires_at fell outside the window",
        fields={},
        request=_identity(assembled.address),
        pre_assembly_lineage=None,
    )

    with pytest.raises(ValidationError):
        DoorOutcome.model_validate_json(vessel)
    with pytest.raises(ValidationError):
        RefusalEnvelope.model_validate_json(vessel)
    with pytest.raises(ValidationError):
        type(assembled.servable.product).model_validate_json(
            canonical_bytes(envelope).decode("utf-8")
        )


# ---------------------------------------------------------------------------
# The sabotage controls (D-22) — divergent subjects into the real assertions.
# ---------------------------------------------------------------------------


def test_the_identity_assertion_fires_on_a_dropped_kind(
    assembled: Any, tmp_path: Path
) -> None:
    """A refusal that lost its ``kind`` is caught by the **real** assertion.

    ``kind`` is the single most consequential field to lose: constraint (a) of
    the envelope's ruling exists because a consumer that cannot name the kind
    cannot audit the refusal, and a flattened refusal is otherwise a perfectly
    well-formed object.
    """
    address = assembled.address
    honest = RefusalEnvelope(
        kind="ttl-refusal",
        reason="ttl",
        key=None,
        detail="expires_at fell outside the window",
        fields={"max_ttl_seconds": "3600"},
        request=_identity(address),
        pre_assembly_lineage=None,
    )
    flattened = honest.model_copy(update={"kind": "gate-refusal"})

    with pytest.raises(AssertionError, match="kind"):
        assert_refusals_identical(honest, flattened)


def test_the_boundary_assertion_fires_on_a_renderer_that_envelopes_governance(
    assembled: Any,
) -> None:
    """A renderer that envelopes a governance refusal fails the **real** assertion.

    The fake does exactly what a door conflating the two would do: it produces
    a well-formed envelope naming a gate that never ran. Nothing about the
    envelope's shape would tell a consumer the fabric was never asked.
    """
    identity = _identity(assembled.address)

    def enveloping(refused: ProductEntitlementRefused) -> RefusalEnvelope:
        return RefusalEnvelope(
            kind="gate-refusal",
            reason="entitlement",
            key=None,
            detail=refused.message,
            fields={},
            request=identity,
            pre_assembly_lineage=None,
        )

    with pytest.raises(AssertionError, match="governance refusal"):
        assert_governance_stays_a_raise(enveloping)


def test_the_replay_ref_assertion_fires_on_a_door_that_drops_it() -> None:
    """A door that discards the reference fails the **real** assertion.

    Two halves, because the two failures are different and the second is the
    one that ships silently: a door that emits nothing is caught by the absence
    leg, and two doors that emit *different* references — which is a door
    naming a record that is not the one that authorized the delivery — is
    caught by the equality leg.
    """
    honest = "ccf-artifact://tenant/replay/1"

    with pytest.raises(AssertionError, match="no replay reference"):
        assert_both_doors_carry_the_replay_ref(lambda: honest, lambda: None)

    with pytest.raises(AssertionError, match="property of the decision"):
        assert_both_doors_carry_the_replay_ref(
            lambda: honest, lambda: "ccf-artifact://tenant/replay/2"
        )
