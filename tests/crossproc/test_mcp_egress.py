"""The D-01 slice: a Context Product crosses a real process boundary (XPRC-01).

Whitepaper §8.3 Pattern 3; CLAUDE.md §7.1 (MCP egress) and §8.3 (the MCP server
as a v0 front door). The child assembles a banking product through the whole
L1→L6 path and serves it as an MCP Resource; this process reads it back over
loopback HTTP with :mod:`ccf.mcp.client`. Nothing is shared but the wire.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
single-writer (INV-CH7-10, CLAUDE.md §10)  the egress module would name a graph
                                           write or read handle, or import the
                                           graph package, and so have a route
                                           into L3 to hand a consumer
scheme separation (T-06-16)                an artifact-scheme URI would resolve
                                           at the egress server, making a
                                           live-assembly address look like an
                                           immutable one in a replay record
readiness discipline (D-16)                a sleep-gated fixture would pass
                                           against a server that never started;
                                           here the read happens only after the
                                           child's own stdout handshake
byte fidelity                              the product would arrive re-encoded,
                                           and a consumer hashing what it got
                                           would compute a different address
tenant addressing (T-06-13)                a product would be served under a
                                           tenant it was not assembled for
sync bridge liveness (B3, T-06-15)         a regression to the held-session
                                           bridge would hang; the bounded call
                                           fails fast instead
authentication (T-15.5-19b, 15.5-06)       the door would answer a caller with
                                           no bearer token at all, and the
                                           entitlement check downstream would
                                           be asking "may this principal?"
                                           about a principal nobody verified
entitlement (T-15.5-20, 15.5-06)           a verified caller would receive a
                                           product class its grant does not
                                           name, or be conditioned under a
                                           role nobody granted it
refuse-to-build (T-15.5-21, 15.5-06)       the builder would produce an inert
                                           door when a governance seam was
                                           omitted, making deny-by-default a
                                           deployment's choice
tool parity (T-16-23-02, D-IMPL-126)       the parameterised tool would be the
                                           weaker of the door's two surfaces —
                                           served where the resource refused,
                                           or refused for a different reason
forwarded perspective (T-16-23-03)         the tool would entitle correctly and
                                           then hand the resolver a perspective
                                           it invented, which is DI-15.5-03
                                           reopened on a new door
=========================================  ===================================

**What "the tool is not the weaker path" means here, operationally.** It is a
**behavioural matrix**, not a source reading: one ``_local_world`` server, one
policy and one grant per scenario, both surfaces driven, outcomes compared. A
source assertion that both handler bodies call ``entitled_perspective`` cannot
see an argument passed differently, and outcome parity in turn cannot see a
perspective resolved and discarded — which is why the matrix and
``test_the_tool_forwards_the_perspective_it_resolved`` are separate assertions
and neither substitutes for the other.

**The resource is pinned twice, and the two pins prove different things.**
``test_a_verified_entitled_caller_is_served_and_the_allow_is_audited`` is the
**HEAD pin**: it is unmodified from before the tool existed, so it is what
proves the resource's served bytes did not move between commits.
``test_registering_the_tool_does_not_move_what_the_resource_serves`` is the
**tool-presence pin**: two servers built from the same fixture at *this*
commit, one with the tool and one without, compared on raw bytes — that is
what proves registering a tool does not alter what the resource returns, which
is ``D-IMPL-126``'s explicit constraint. Neither implies the other.

Every domain value — tenant, product class, schema version — comes from
``tests/fixtures/banking/`` by way of the child's builder. Delete the fixtures
and this file has nothing to assert (CLAUDE.md §6.4 applied to fixture code).
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
from collections.abc import Awaitable, Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import anyio
import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.settings import AuthSettings
from mcp.types import TextContent, TextResourceContents
from pydantic import AnyHttpUrl, AnyUrl

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import McpResourceClient, SyncMcpBridge, run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
    ERROR_PRODUCT_POLICY_ABSENT,
    ERROR_PRODUCT_ROLE_UNGRANTED,
)
from ccf_runtime.mcp.auth import (
    FileTokenSource,
    SourceBackedTokenVerifier,
    TokenGrant,
)
from ccf_runtime.mcp.egress import (
    PRODUCT_REQUEST_TOOL,
    build_egress_server,
    product_uri,
)

from crossproc.servers.mcp_egress_child import (
    ProductAddress,
    authorized_http_client,
    build_servable_product,
)

pytestmark = pytest.mark.crossproc

CHILD = Path(__file__).resolve().parent / "servers" / "mcp_egress_child.py"

#: Deadline every synchronous call is bounded by. Generous enough for a cold
#: child, short enough that the deadlocking bridge fails the suite in seconds
#: instead of hanging CI until its own timeout (06-RESEARCH.md B3).
CALL_TIMEOUT_SECONDS = 20.0

with_child = pytest.mark.parametrize(
    "child_server_port", [CHILD], indirect=True
)


@pytest.fixture
def expected(tmp_path: Path) -> tuple[str, ProductAddress]:
    """The product this process independently assembles, and its address.

    Recomputed here rather than trusted from the wire: comparing what arrived
    against what the fabric produces is the only version of this assertion that
    can fail for the right reason. Assembly is deterministic for a fixed
    boundary (proved in ``test_proto_quickstart``), so the two processes must
    agree byte for byte.
    """
    assembled = build_servable_product(
        database_path=tmp_path / "egress-parent.sqlite3"
    )
    return canonical_bytes(assembled.servable.product).decode("utf-8"), (
        assembled.address
    )


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    """One bounded sync bridge per test, closed on teardown."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield bridge


# --- the structural claim the module docstring makes -----------------------


def test_the_egress_module_holds_no_route_into_the_graph() -> None:
    """Single-writer across the seam: there is no handle here to hand out.

    Asserted against the module's source because that is where the claim is
    falsifiable. A field, an import, or a parameter naming a graph handle would
    show up here before it could ever show up in behaviour.
    """
    import ccf_runtime.mcp.egress as egress

    source = inspect.getsource(egress)
    for forbidden in ("GraphWriter", "GraphReader", "ccf.graph"):
        assert forbidden not in source, (
            f"{forbidden} appears in the egress server's source; the L6 egress "
            "seam must hold no route into L2 or L3 (INV-CH7-10, T-06-12)"
        )


def test_the_egress_scheme_is_not_the_artifact_scheme() -> None:
    """Live products and artifacts at rest are addressed differently (T-06-16).

    A shared scheme would let a TTL-bound, assembled-now URI be recorded as if
    it named a content-addressed artifact — a replay would then resolve
    something that no longer exists, or worse, something different.
    """
    from ccf.artifacts.protocol import ARTIFACT_URI_SCHEME
    from ccf_runtime.mcp.egress import PRODUCT_URI_SCHEME

    assert PRODUCT_URI_SCHEME != ARTIFACT_URI_SCHEME


# --- the cross-process round trip ------------------------------------------


@with_child
def test_the_product_crosses_the_process_boundary_intact(
    loopback_url: str, expected: tuple[str, ProductAddress], bridge: SyncMcpBridge
) -> None:
    """A separate OS process serves the product; this one reads it back.

    The comparison is on canonical bytes, so a re-encode anywhere on the path —
    key reordering, float reformatting, a timestamp losing its offset — fails
    here rather than surfacing later as a content address that does not match.
    """
    canonical, address = expected
    client = McpResourceClient(
        url=loopback_url,
        bridge=bridge,
        http_client_factory=authorized_http_client,
    )

    received = client.read_text(address.uri)

    assert received == canonical
    # And it is a real product, not an opaque blob that happens to match.
    payload = json.loads(received)
    assert payload["tenant_id"] == address.tenant
    assert payload["schema_name"] == address.product_class
    assert payload["lineage"]["operators_invoked"]


@with_child
def test_the_server_advertises_the_product_resource(
    loopback_url: str, expected: tuple[str, ProductAddress], bridge: SyncMcpBridge
) -> None:
    """Discovery works over the wire and speaks the CCF scheme.

    A consumer that cannot list is a consumer that must be told the URI out of
    band, which defeats Pattern 3's "without knowing anything about the
    fabric's internals".
    """
    from ccf_runtime.mcp.egress import PRODUCT_URI_TEMPLATE, PRODUCT_URI_SCHEME

    _canonical, _address = expected
    client = McpResourceClient(
        url=loopback_url,
        bridge=bridge,
        http_client_factory=authorized_http_client,
    )

    templates = client.resource_templates()

    # Templated, not enumerated: the fabric advertises the shape of what it can
    # assemble, because listing every product it *could* assemble would mean
    # assembling them, and a discovery call must not run the fabric.
    assert PRODUCT_URI_TEMPLATE in templates
    assert all(uri.startswith(f"{PRODUCT_URI_SCHEME}://") for uri in templates)
    assert client.resource_uris() == ()


@with_child
def test_a_foreign_address_is_refused_rather_than_served(
    loopback_url: str, expected: tuple[str, ProductAddress], bridge: SyncMcpBridge
) -> None:
    """The wrong tenant does not get the right product (T-06-13).

    Without this the round-trip test would pass against a resolver that ignored
    its arguments entirely, and cross-tenant leakage would be untested.
    """
    _canonical, address = expected
    foreign = ProductAddress(
        tenant=f"{address.tenant}-not-this-one",
        product_class=address.product_class,
        version=address.version,
    )
    client = McpResourceClient(
        url=loopback_url,
        bridge=bridge,
        http_client_factory=authorized_http_client,
    )

    with pytest.raises(McpServerUnreachable):
        client.read_text(foreign.uri)


@with_child
def test_the_sync_bridge_completes_from_a_synchronous_test_body(
    loopback_url: str, expected: tuple[str, ProductAddress]
) -> None:
    """Three bounded sync calls, no event loop in sight, no hang (B3).

    Every call above already goes through the bridge; this one exists to make
    the *repeat* case explicit. The held-session bridge that deadlocks survived
    a single call in prototyping and hung on reuse, so one call is not the
    assertion that would have caught it.
    """
    canonical, address = expected
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        client = McpResourceClient(
            url=loopback_url,
            bridge=bridge,
            http_client_factory=authorized_http_client,
        )
        results = [client.read_text(address.uri) for _ in range(3)]
    assert results == [canonical] * 3


def test_a_sync_client_without_a_bridge_refuses_rather_than_improvises() -> None:
    """No background thread is manufactured behind the caller's back.

    A client that spun up its own loop on demand would own a thread nobody
    closes, which is how a test suite ends with more threads than tests.
    """
    client = McpResourceClient(url="http://127.0.0.1:1/mcp")
    with pytest.raises(McpServerUnreachable):
        client.resource_uris()


# --- authentication and entitlement at the door (15.5-06) ------------------
#
# These run in-process against the very builder the child uses, over the
# server's own ASGI app. In-process is deliberate and it is the A1 spike's
# precedent: what is under test is request-scoped middleware state and the
# handler's own ordering, and whether the socket is loopback or ASGI is
# irrelevant to either. What it buys is the ability to issue a *tokenless*
# call, which no authenticated cross-process client in this suite can do.


#: Loopback with an explicit port, because FastMCP's DNS-rebinding protection
#: allows ``127.0.0.1:*`` (host **with** a port) even over ASGI where no
#: socket exists. The number is arbitrary; nothing binds it.
IN_PROCESS_BASE_URL = "http://127.0.0.1:8124"

#: Test deployment vocabulary for the in-process door. Meaningful nowhere
#: else, and deliberately distinct from the banking fixture's values so a
#: leak between the two would be visible rather than silently consistent.
LOCAL_TOKEN = "ccf-egress-local-token"
LOCAL_PRINCIPAL = "local-caller"
LOCAL_STRANGER = "local-caller-undeclared"
LOCAL_STRANGER_TOKEN = "ccf-egress-local-stranger-token"
LOCAL_SCOPE = "ccf:egress-local"
LOCAL_SERVER_NAME = "ccf-egress-local"
LOCAL_ROLE = "local-role"
LOCAL_SECOND_ROLE = "local-role-second"
LOCAL_UNGRANTED_ROLE = "local-role-ungranted"
LOCAL_POLICY_VERSION = "1.0.0"
LOCAL_AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)

#: A credential the token source has never heard of. Distinct from *no* token:
#: both are 401s, and a matrix that tested only one would leave the other
#: surface's behaviour on an unknown bearer entirely unasserted.
LOCAL_UNKNOWN_TOKEN = "ccf-egress-local-token-nobody-issued"

#: The prose this test deployment's tool advertises, and the four §6.3 axes it
#: is asked with. Test values: the SDK holds no default for any of them, which
#: is the whole of CINV-01 on this surface.
LOCAL_TOOL_DESCRIPTION = "Ask this test deployment's product class a question."
LOCAL_SUBJECT = "local-subject"
LOCAL_OTHER_SUBJECT = "local-subject-other"
LOCAL_INTENT = "local-intent"
LOCAL_FRESHNESS = "local-freshness"
LOCAL_ASKED_AT = datetime(2026, 8, 13, 9, 30, tzinfo=UTC)

#: The seven names the tool's input schema advertises, asserted by **equality**
#: rather than containment: containment would pass against a tool that also
#: accepted ``role``, which is precisely the widening the tool must not have.
EXPECTED_TOOL_ARGUMENTS = frozenset(
    {
        "tenant",
        "product_class",
        "version",
        "subject",
        "intent",
        "freshness",
        "asked_at",
    }
)


def _tool_arguments(
    address: ProductAddress,
    *,
    subject: str = LOCAL_SUBJECT,
    asked_at: str | None = None,
) -> dict[str, Any]:
    """The four §6.3 axes plus the three address segments, as wire arguments."""
    return {
        "tenant": address.tenant,
        "product_class": address.product_class,
        "version": address.version,
        "subject": subject,
        "intent": LOCAL_INTENT,
        "freshness": LOCAL_FRESHNESS,
        "asked_at": (
            LOCAL_ASKED_AT.isoformat() if asked_at is None else asked_at
        ),
    }


class _RecordingEntitlement:
    """Wraps a source and records every call, so "never reached" is provable.

    A test that only asserted the *order of two lines of source* would pass
    against a server whose auth middleware was never installed — which is
    precisely the defect this door's authentication fixes. Counting real
    invocations is the assertion that cannot pass for that wrong reason.
    """

    def __init__(self, inner: object) -> None:
        self.inner = inner
        self.calls: list[str] = []

    def authorize(
        self, *, grant: object, tenant: str, product_class: str, role: str
    ) -> object:
        self.calls.append(getattr(grant, "client_id", ""))
        return self.inner.authorize(  # type: ignore[attr-defined]
            grant=grant, tenant=tenant, product_class=product_class, role=role
        )


def _local_world(
    tmp_path: Path,
    *,
    servable: object,
    address: ProductAddress,
    permitted_classes: frozenset[str] | None = None,
    permitted_roles: frozenset[str] | None = None,
    resolved_role: str = LOCAL_ROLE,
    forwarded: list[tuple[Perspective, object]] | None = None,
    expose_product_tool: bool = False,
    product_tool_description: str | None = None,
) -> tuple[object, _RecordingEntitlement, ControlPlaneRegistry]:
    """An egress server over a stub resolver, plus its recording entitlement.

    ``forwarded`` collects every ``(perspective, request)`` pair the door
    handed the resolver, which is what lets a test assert the *value* the door
    forwarded rather than only that the parameter exists (D-IMPL-108).

    The two tool arguments are a straight pass-through, defaulting closed, so
    every caller written before the tool existed is unchanged and the
    supplied-together rule stays the builder's to enforce rather than being
    papered over here.
    """
    forwarded = [] if forwarded is None else forwarded
    token_file = tmp_path / "local-tokens.json"
    token_file.write_text(
        json.dumps(
            {
                LOCAL_TOKEN: {
                    "client_id": LOCAL_PRINCIPAL,
                    "scopes": [LOCAL_SCOPE],
                },
                LOCAL_STRANGER_TOKEN: {
                    "client_id": LOCAL_STRANGER,
                    "scopes": [LOCAL_SCOPE],
                },
            }
        ),
        encoding="utf-8",
    )
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version=LOCAL_POLICY_VERSION,
            principals={
                LOCAL_PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=(
                        frozenset({address.product_class})
                        if permitted_classes is None
                        else permitted_classes
                    ),
                    permitted_roles=(
                        frozenset({LOCAL_ROLE})
                        if permitted_roles is None
                        else permitted_roles
                    ),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    entitlement = _RecordingEntitlement(
        ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: LOCAL_AUDIT_INSTANT
        )
    )

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: object,
    ) -> object:
        # Record what the door forwarded, so a test can assert on the VALUE
        # and not merely on the parameter's existence (D-IMPL-108).
        forwarded.append((perspective, request))
        return servable

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(principal_id=grant.client_id, role=resolved_role)

    server = build_egress_server(
        server_name=LOCAL_SERVER_NAME,
        resolver=resolve,  # type: ignore[arg-type]
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=token_file)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[LOCAL_SCOPE],
        ),
        entitlement_source=entitlement,  # type: ignore[arg-type]
        perspective_resolver=resolve_perspective,
        expose_product_tool=expose_product_tool,
        product_tool_description=product_tool_description,
    )
    return server, entitlement, registry


def _open_world(
    tmp_path: Path,
    *,
    servable: object,
    address: ProductAddress,
    **kwargs: Any,
) -> tuple[object, _RecordingEntitlement, ControlPlaneRegistry]:
    """:func:`_local_world` with the tool exposed — one server, two surfaces.

    Both tool arguments together, always: that a description accompanies the
    boolean is the builder's rule and this helper honours it rather than
    working around it.
    """
    return _local_world(
        tmp_path,
        servable=servable,
        address=address,
        expose_product_tool=True,
        product_tool_description=LOCAL_TOOL_DESCRIPTION,
        **kwargs,
    )


def _client_factory(
    app: Any, token: str | None
) -> Callable[[], httpx.AsyncClient]:
    """A client over the server's own ASGI app, Bearer-headed when asked."""

    def factory() -> httpx.AsyncClient:
        headers = {} if token is None else {"Authorization": f"Bearer {token}"}
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=IN_PROCESS_BASE_URL,
            headers=headers,
        )

    return factory


def _resource_operation(
    uri: str,
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    """Read one resource; report ``(refused, text)`` — never refused here."""

    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.read_resource(AnyUrl(uri))
        return False, "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return operation


def _tool_operation(
    name: str, arguments: dict[str, Any]
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    """Call one tool; report ``(isError, joined text)``.

    The one place the two surfaces genuinely differ as *clients*: a resource
    refusal arrives as a transport error, while a tool refusal arrives as a
    perfectly successful response carrying ``isError`` — so a helper that
    watched only for exceptions would read every tool refusal as a serve.
    """

    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(name, arguments)
        texts = [
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        ]
        return bool(result.isError), " | ".join(texts)

    return operation


async def _attempt(
    app: Any,
    operation: Callable[[ClientSession], Awaitable[tuple[bool, str]]],
    token: str | None,
) -> tuple[bool, str]:
    """Run one operation in its own session; return ``(refused, text)``.

    A refusal is returned rather than raised, and the *reason* is returned
    with it. Two things make that the right shape here: an exception escaping
    the lifespan is re-wrapped by its task group into a ``BaseExceptionGroup``
    that says nothing about the door, and — more importantly — a refusal test
    that only asserts "it raised" would pass against a door refusing for a
    reason nobody intended. The returned text carries the typed
    ``error_code``, which is the assertion worth making.
    """
    try:
        return await run_with_session(
            url=f"{IN_PROCESS_BASE_URL}/mcp",
            operation=operation,
            http_client_factory=_client_factory(app, token),
        )
    except McpServerUnreachable as refused:
        return True, _flatten(refused)


def _read_in_process(
    server: object, uri: str, *, token: str | None
) -> tuple[bool, str]:
    """Read one resource over the server's own ASGI app; return ``(ok, text)``.

    ``httpx.ASGITransport`` does not drive the ASGI lifespan and the FastMCP
    streamable-HTTP app starts its session manager *in* the lifespan, so the
    lifespan context is entered explicitly — exactly what uvicorn does for the
    cross-process siblings.

    Refusal handling lives in :func:`_attempt`, which this and its tool twin
    share; the returned shape here — ``ok`` first, so ``True`` means served —
    is unchanged from before the tool existed.
    """
    app = server.streamable_http_app()  # type: ignore[attr-defined]

    async def with_lifespan() -> tuple[bool, str]:
        async with app.router.lifespan_context(app):  # type: ignore[attr-defined]
            refused, text = await _attempt(app, _resource_operation(uri), token)
            return not refused, text

    return asyncio.run(with_lifespan())


def _call_tool_in_process(
    server: object,
    name: str,
    arguments: dict[str, Any],
    *,
    token: str | None,
) -> tuple[bool, str]:
    """Call one tool over the server's own ASGI app; return ``(is_error, text)``.

    The twin of :func:`_read_in_process`, deliberately written to look like it:
    the same ``streamable_http_app()``, the same explicit ``lifespan_context``
    entry, the same Bearer-header client factory and the same ``_attempt``.
    It differs in the operation it runs and in returning the refusal flag the
    way a tool client sees it — ``is_error`` first, because both of a tool's
    two refusal channels (``isError`` on a successful response, and a
    transport error when the auth middleware refused before any handler ran)
    are refusals.
    """
    app = server.streamable_http_app()  # type: ignore[attr-defined]

    async def with_lifespan() -> tuple[bool, str]:
        async with app.router.lifespan_context(app):  # type: ignore[attr-defined]
            return await _attempt(app, _tool_operation(name, arguments), token)

    return asyncio.run(with_lifespan())


def _both_surfaces_in_process(
    server: object,
    *,
    uri: str,
    tool_arguments: dict[str, Any],
    token: str | None,
) -> tuple[tuple[bool, str], tuple[bool, str]]:
    """Drive **both** surfaces of one server, in one lifespan, on one credential.

    Returns ``((ok, resource_text), (is_error, tool_text))``.

    One lifespan is a hard requirement rather than an optimization:
    ``StreamableHTTPSessionManager.run()`` refuses a second call per instance,
    and ``FastMCP`` holds one manager per server — so a matrix that entered the
    lifespan twice would be forced onto two servers, and would then be
    comparing two deployments rather than the two surfaces of one door. One
    server, one policy, one grant is the whole point of the comparison
    (T-16-23-02).
    """
    app = server.streamable_http_app()  # type: ignore[attr-defined]

    async def with_lifespan() -> tuple[tuple[bool, str], tuple[bool, str]]:
        async with app.router.lifespan_context(app):  # type: ignore[attr-defined]
            refused, resource_text = await _attempt(
                app, _resource_operation(uri), token
            )
            tool = await _attempt(
                app,
                _tool_operation(PRODUCT_REQUEST_TOOL, tool_arguments),
                token,
            )
            return (not refused, resource_text), tool

    return asyncio.run(with_lifespan())


def _flatten(error: BaseException, _seen: frozenset[int] = frozenset()) -> str:
    """Every message in an exception's cause chain and group tree, joined.

    ``run_with_session`` renders whatever the transport raised, and anyio
    renders a task group's failure as ``unhandled errors in a TaskGroup`` with
    the real cause nested one or more levels down. Asserting on the top-level
    string would therefore assert on anyio's wording rather than on the
    door's refusal, which is the difference between "it failed" and "it
    refused for the stated reason".
    """
    if id(error) in _seen:  # a __context__ cycle is rare but not impossible
        return ""
    seen = _seen | {id(error)}
    parts: list[str] = [f"{type(error).__name__}: {error}"]
    if isinstance(error, BaseExceptionGroup):
        parts.extend(_flatten(inner, seen) for inner in error.exceptions)
    for chained in (error.__cause__, error.__context__):
        if chained is not None:
            parts.append(_flatten(chained, seen))
    return " | ".join(part for part in parts if part)


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> object:
    """One assembled banking product, reused by the in-process door tests.

    Module-scoped because it boots a fabric: the door tests below vary the
    *governance*, never the product, so paying for one assembly is honest and
    paying for six would only be slow.
    """
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-door") / "door.sqlite3"
    )


@pytest.mark.parametrize(
    "omitted",
    [
        "token_verifier",
        "auth_settings",
        "entitlement_source",
        "perspective_resolver",
    ],
)
def test_the_builder_refuses_to_build_without_any_governance_seam(
    omitted: str, assembled: Any, tmp_path: Path
) -> None:
    """T-15.5-21: there is no inert configuration of this door.

    What would fail here: any of the four seams acquiring a ``None`` default
    "for compatibility". A door built without a verifier answers everyone; a
    door built without an entitlement source answers everyone it verified;
    both are the gap §11.2 measured, and both would ship green.
    """
    kwargs: dict[str, Any] = {
        "server_name": LOCAL_SERVER_NAME,
        "resolver": lambda *, tenant, product_class, version: assembled.servable,
        "token_verifier": SourceBackedTokenVerifier(
            source=FileTokenSource(path=tmp_path / "absent.json")
        ),
        "auth_settings": AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[LOCAL_SCOPE],
        ),
        "entitlement_source": ControlPlaneProductEntitlementSource(
            control_plane=ControlPlaneRegistry(),
            clock=lambda: LOCAL_AUDIT_INSTANT,
        ),
        "perspective_resolver": (
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=LOCAL_ROLE
            )
        ),
    }
    del kwargs[omitted]

    with pytest.raises(TypeError, match=omitted):
        build_egress_server(**kwargs)


def test_the_constructor_carries_the_authentication_pair() -> None:
    """The verifier and the settings reach ``FastMCP``, not just the signature.

    Asserted on the source because ``FastMCP`` installs its middleware only
    when both are present: a builder that accepted the pair and dropped it on
    the floor would satisfy every signature test in this file and authenticate
    nothing.
    """
    import ccf_runtime.mcp.egress as egress

    source = inspect.getsource(egress.build_egress_server)
    assert "token_verifier=token_verifier" in source
    assert "auth=auth_settings" in source


def test_a_tokenless_call_never_reaches_the_entitlement_check(
    assembled: Any, tmp_path: Path
) -> None:
    """T-15.5-19b: authentication runs first, and it runs at all.

    The recorder is the assertion. A door whose auth middleware was never
    installed would let the tokenless call through to the entitlement source,
    which would then refuse an *unverified* principal — a refusal that looks
    identical in a log and means something entirely different.
    """
    server, entitlement, _registry = _local_world(
        tmp_path, servable=assembled.servable, address=assembled.address
    )

    served, detail = _read_in_process(
        server, assembled.address.uri, token=None
    )

    assert served is False
    assert "401" in detail
    assert entitlement.calls == []


def test_a_verified_entitled_caller_is_served_and_the_allow_is_audited(
    assembled: Any, tmp_path: Path
) -> None:
    """The happy path, so every refusal below is a refusal of something real."""
    server, entitlement, registry = _local_world(
        tmp_path, servable=assembled.servable, address=assembled.address
    )

    served, received = _read_in_process(
        server, assembled.address.uri, token=LOCAL_TOKEN
    )

    assert served is True
    assert received == canonical_bytes(assembled.servable.product).decode("utf-8")
    assert entitlement.calls == [LOCAL_PRINCIPAL]
    events = [
        event
        for event in registry.audit_log.events()
        if isinstance(event, AuthzDecisionAuditEvent)
    ]
    assert [event.resolved for event in events] == [True]
    assert events[0].actor == LOCAL_PRINCIPAL


def test_a_verified_but_undeclared_principal_is_refused(
    assembled: Any, tmp_path: Path
) -> None:
    """Authentication is not entitlement: a real token is not a grant."""
    server, entitlement, registry = _local_world(
        tmp_path, servable=assembled.servable, address=assembled.address
    )

    served, detail = _read_in_process(
        server, assembled.address.uri, token=LOCAL_STRANGER_TOKEN
    )

    assert served is False
    assert ERROR_PRINCIPAL_NOT_ENTITLED in detail
    assert entitlement.calls == [LOCAL_STRANGER]
    events = [
        event
        for event in registry.audit_log.events()
        if isinstance(event, AuthzDecisionAuditEvent)
    ]
    assert [event.resolved for event in events] == [False]


def test_a_principal_entitled_to_another_class_is_refused_at_the_door(
    assembled: Any, tmp_path: Path
) -> None:
    """T-15.5-20: ``P`` at delivery is per class, at the door, per call."""
    other_class = f"{assembled.address.product_class}-not-this-one"
    server, _entitlement, registry = _local_world(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        permitted_classes=frozenset({other_class}),
    )

    served, detail = _read_in_process(
        server, assembled.address.uri, token=LOCAL_TOKEN
    )

    assert served is False
    assert ERROR_PRODUCT_CLASS_UNENTITLED in detail
    assert assembled.address.product_class in detail
    events = [
        event
        for event in registry.audit_log.events()
        if isinstance(event, AuthzDecisionAuditEvent)
    ]
    assert [event.resolved for event in events] == [False]


def test_a_role_the_grant_does_not_permit_is_refused_at_the_door(
    assembled: Any, tmp_path: Path
) -> None:
    """T-15.5-19: the resolver proposes, the grant decides.

    The resolver here returns a role outside the grant, which is what a
    deployment bug — or a compromised resolver — looks like. Checking the
    *resolved* role rather than only a requested one is what makes this fail.
    """
    server, _entitlement, registry = _local_world(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        resolved_role=LOCAL_UNGRANTED_ROLE,
    )

    served, detail = _read_in_process(
        server, assembled.address.uri, token=LOCAL_TOKEN
    )

    assert served is False
    assert ERROR_PRODUCT_ROLE_UNGRANTED in detail
    events = [
        event
        for event in registry.audit_log.events()
        if isinstance(event, AuthzDecisionAuditEvent)
    ]
    assert [event.resolved for event in events] == [False]


def test_a_tenant_with_no_registered_policy_is_refused_not_served(
    assembled: Any, tmp_path: Path
) -> None:
    """A door with no policy in force refuses rather than serving (T-15.5-21).

    The seam is bound and the caller is verified; what is missing is the
    deployment's declaration. A source that read that as "nothing to enforce"
    is how a misconfigured deployment ships wide open.
    """
    token_file = tmp_path / "empty-policy-tokens.json"
    token_file.write_text(
        json.dumps(
            {LOCAL_TOKEN: {"client_id": LOCAL_PRINCIPAL, "scopes": [LOCAL_SCOPE]}}
        ),
        encoding="utf-8",
    )
    registry = ControlPlaneRegistry()
    server = build_egress_server(
        server_name=LOCAL_SERVER_NAME,
        resolver=lambda *, tenant, product_class, version: assembled.servable,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=token_file)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[LOCAL_SCOPE],
        ),
        entitlement_source=ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: LOCAL_AUDIT_INSTANT
        ),
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=LOCAL_ROLE
            )
        ),
    )

    served, detail = _read_in_process(
        server, assembled.address.uri, token=LOCAL_TOKEN
    )

    assert served is False
    assert ERROR_PRODUCT_POLICY_ABSENT in detail
    events = [
        event
        for event in registry.audit_log.events()
        if isinstance(event, AuthzDecisionAuditEvent)
    ]
    assert [event.resolved for event in events] == [False]


# --- the parameterised tool: the door's second surface (D-IMPL-126) --------


class _Governance(NamedTuple):
    """One governance scenario, as both surfaces must see it."""

    world: dict[str, Any]
    token: str | None
    address: ProductAddress
    marker: str | None  # ``None`` means *served*


#: Every governance scenario this door has, so the matrix below covers the
#: whole of it rather than the subset a new surface happens to pass. It is a
#: parametrization precisely so that a governance case added later grows
#: **both** legs automatically instead of the resource leg only.
GOVERNANCE_SCENARIOS = (
    "entitled",
    "tokenless",
    "unknown-token",
    "undeclared-principal",
    "class-unentitled",
    "role-ungranted",
    "policy-absent",
)


def _governance(scenario: str, assembled: Any) -> _Governance:
    """The world, credential, address and expected outcome for one scenario."""
    address = assembled.address
    if scenario == "entitled":
        return _Governance({}, LOCAL_TOKEN, address, None)
    if scenario == "tokenless":
        return _Governance({}, None, address, "401")
    if scenario == "unknown-token":
        return _Governance({}, LOCAL_UNKNOWN_TOKEN, address, "401")
    if scenario == "undeclared-principal":
        return _Governance(
            {}, LOCAL_STRANGER_TOKEN, address, ERROR_PRINCIPAL_NOT_ENTITLED
        )
    if scenario == "class-unentitled":
        return _Governance(
            {
                "permitted_classes": frozenset(
                    {f"{address.product_class}-not-this-one"}
                )
            },
            LOCAL_TOKEN,
            address,
            ERROR_PRODUCT_CLASS_UNENTITLED,
        )
    if scenario == "role-ungranted":
        return _Governance(
            {"resolved_role": LOCAL_UNGRANTED_ROLE},
            LOCAL_TOKEN,
            address,
            ERROR_PRODUCT_ROLE_UNGRANTED,
        )
    if scenario == "policy-absent":
        return _Governance(
            {},
            LOCAL_TOKEN,
            ProductAddress(
                tenant=f"{address.tenant}-no-policy",
                product_class=address.product_class,
                version=address.version,
            ),
            ERROR_PRODUCT_POLICY_ABSENT,
        )
    raise AssertionError(f"unknown governance scenario {scenario!r}")


@pytest.mark.parametrize("scenario", GOVERNANCE_SCENARIOS)
def test_the_tool_is_never_the_weaker_path(
    scenario: str, assembled: Any, tmp_path: Path
) -> None:
    """T-16-23-02: one server, one policy, one grant, two surfaces, one verdict.

    What would fail here: the tool acquiring a wider surface than the resource
    beside it — served where the resource refused, or refused for a *different*
    reason, which in an audit log is a different decision. Driving both legs
    against the **same** ``_local_world`` is what makes the comparison mean
    something: a matrix built over two separately-configured servers would be
    comparing two policies, not two doors.

    A source assertion that both bodies call ``entitled_perspective`` could not
    see an argument passed differently. This can.
    """
    plan = _governance(scenario, assembled)
    server, _entitlement, _registry = _open_world(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        **plan.world,
    )

    (served, resource_text), (tool_error, tool_text) = (
        _both_surfaces_in_process(
            server,
            uri=plan.address.uri,
            tool_arguments=_tool_arguments(plan.address),
            token=plan.token,
        )
    )

    assert served is not tool_error, (
        f"{scenario}: the resource {'served' if served else 'refused'} and the"
        f" tool {'refused' if tool_error else 'served'}; the two surfaces of"
        " one door must agree (T-16-23-02)"
    )
    if plan.marker is None:
        expected = canonical_bytes(assembled.servable.product).decode("utf-8")
        assert resource_text == expected
        assert tool_text == expected
    else:
        assert plan.marker in resource_text, resource_text
        assert plan.marker in tool_text, tool_text


def test_a_tokenless_tool_call_never_reaches_the_entitlement_check(
    assembled: Any, tmp_path: Path
) -> None:
    """T-16-23-01: the ``:588`` shape, repeated for the tool leg.

    The recorder is the assertion, for the reason it was on the resource leg:
    a tool whose auth middleware never ran would reach the entitlement source,
    which would then refuse an *unverified* principal — a refusal that looks
    identical in a log and means something entirely different.
    """
    server, entitlement, _registry = _open_world(
        tmp_path, servable=assembled.servable, address=assembled.address
    )

    is_error, detail = _call_tool_in_process(
        server,
        PRODUCT_REQUEST_TOOL,
        _tool_arguments(assembled.address),
        token=None,
    )

    assert is_error is True
    assert "401" in detail
    assert entitlement.calls == []


@pytest.mark.parametrize("role", [LOCAL_ROLE, LOCAL_SECOND_ROLE])
def test_the_tool_forwards_the_perspective_it_resolved(
    role: str, assembled: Any, tmp_path: Path
) -> None:
    """T-16-23-03: ``DI-15.5-03``, and outcome parity is blind to it.

    A handler that calls ``entitled_perspective`` correctly, **discards the
    return**, and hands the resolver a ``Perspective`` of its own passes every
    row of the matrix above: the stub resolver serves the same product either
    way, so served-vs-served and error-code parity see nothing. That is the
    defect this module's resource was repaired for — *"resolved an entitled
    Perspective and then discarded it"* — reachable again on a new door, which
    is why the assertion here is on the forwarded **value**.

    The role is parametrized so a perspective hard-coded in the handler fails
    rather than coincides: with two granted roles in play, only a handler that
    forwards what the entitlement returned can match both.

    The request asymmetry is asserted too, and it is the mechanical proof the
    two surfaces stayed semantically distinct: the resource forwards ``None``
    (it has no way to ask) and the tool forwards a typed ``ProductRequest``.
    """
    forwarded: list[tuple[Perspective, object]] = []
    server, _entitlement, _registry = _open_world(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        permitted_roles=frozenset({role}),
        resolved_role=role,
        forwarded=forwarded,
    )

    (served, _resource_text), (tool_error, tool_text) = (
        _both_surfaces_in_process(
            server,
            uri=assembled.address.uri,
            tool_arguments=_tool_arguments(assembled.address),
            token=LOCAL_TOKEN,
        )
    )

    assert served is True
    assert tool_error is False, tool_text
    assert len(forwarded) == 2, forwarded
    (resource_perspective, resource_request) = forwarded[0]
    (tool_perspective, tool_request) = forwarded[1]

    # What the entitlement returned, derived from the scenario rather than
    # read back off the door — so a door that invented a perspective and a
    # door that forwarded one are distinguishable here.
    entitled = Perspective(principal_id=LOCAL_PRINCIPAL, role=role)
    assert resource_perspective == entitled
    assert tool_perspective == entitled
    assert tool_perspective == resource_perspective

    assert resource_request is None
    assert isinstance(tool_request, ProductRequest)
    assert tool_request.subject == LOCAL_SUBJECT
    assert tool_request.intent == LOCAL_INTENT
    assert tool_request.freshness == LOCAL_FRESHNESS
    assert tool_request.asked_at == LOCAL_ASKED_AT
    # The address is the door's, never the caller's: unrepresentable, not
    # merely refused (T-16-23-04).
    assert tool_request.schema_name == assembled.address.product_class
    assert tool_request.schema_version == assembled.address.version
    assert dict(tool_request.parameters) == {}


def test_a_server_built_without_the_tool_arguments_advertises_no_tool(
    assembled: Any, tmp_path: Path
) -> None:
    """T-16-23-11: the regression guard on ``D-IMPL-126``'s measured ``TOOLS: []``.

    What would fail here: the tool acquiring an on-by-default registration. A
    deployment that reviewed and approved a resource-only door must not gain a
    parameterised authorization surface it never assessed merely by upgrading.
    """
    server, _entitlement, _registry = _local_world(
        tmp_path, servable=assembled.servable, address=assembled.address
    )

    assert anyio.run(server.list_tools) == []  # type: ignore[attr-defined]


def test_the_tool_advertises_exactly_the_seven_argument_names(
    assembled: Any, tmp_path: Path
) -> None:
    """What a *client* sees — the wire contract, not the Python signature.

    ``required`` is the only place "all four axes together" is observable to a
    client, and ``properties`` the only place "no ``role``, no ``schema_name``,
    no ``parameters``" is. Both are compared by **equality**: containment would
    pass against a tool that also accepted ``role``, which is exactly the
    widening a second door must not have (T-16-23-04).
    """
    server, _entitlement, _registry = _open_world(
        tmp_path, servable=assembled.servable, address=assembled.address
    )

    tools = anyio.run(server.list_tools)  # type: ignore[attr-defined]

    assert [tool.name for tool in tools] == [PRODUCT_REQUEST_TOOL]
    schema = tools[0].inputSchema
    assert set(schema["properties"]) == set(EXPECTED_TOOL_ARGUMENTS)
    assert set(schema["required"]) == set(EXPECTED_TOOL_ARGUMENTS)
    # A required, zone-carrying instant, advertised as such rather than as a
    # bare string a client has to guess the shape of.
    assert schema["properties"]["asked_at"]["format"] == "date-time"
    assert tools[0].description == LOCAL_TOOL_DESCRIPTION


def test_the_tool_handler_takes_no_role_and_no_caller_supplied_address(
    assembled: Any, tmp_path: Path
) -> None:
    """Asserted by signature, deliberately, and not by grepping the source.

    The handler's docstring legitimately contains the words ``schema_name`` and
    ``parameters`` — it has to, because it explains where they come from — so a
    grep would pass or fail for reasons unrelated to the surface. The registered
    function's signature is the falsifiable form.
    """
    server, _entitlement, _registry = _open_world(
        tmp_path, servable=assembled.servable, address=assembled.address
    )

    registered = server._tool_manager.get_tool(  # type: ignore[attr-defined]
        PRODUCT_REQUEST_TOOL
    )
    parameters = set(inspect.signature(registered.fn).parameters)

    assert parameters == set(EXPECTED_TOOL_ARGUMENTS)
    for absent in ("role", "schema_name", "schema_version", "parameters"):
        assert absent not in parameters


@pytest.mark.parametrize(
    "supplied",
    [
        {"expose_product_tool": True},
        {"product_tool_description": LOCAL_TOOL_DESCRIPTION},
    ],
)
def test_the_tool_exposure_pair_is_supplied_together_or_not_at_all(
    supplied: dict[str, Any], assembled: Any, tmp_path: Path
) -> None:
    """D-03 requiredness-conditional-on-exposure, on the exposure switch itself.

    Two arguments rather than one so *is this door open?* is answerable by
    grepping for a boolean. Half the pair is a configuration whose intent
    cannot be read, and it raises rather than resolving to a guess.
    """
    with pytest.raises(ValueError, match="expose_product_tool"):
        _local_world(
            tmp_path,
            servable=assembled.servable,
            address=assembled.address,
            **supplied,
        )


def test_registering_the_tool_does_not_move_what_the_resource_serves(
    assembled: Any, tmp_path: Path
) -> None:
    """The **tool-presence pin** — and it is not the HEAD pin (module docstring).

    Two servers from the same fixture at this commit, one with the tool and one
    without, read at the same address and compared on **raw bytes** rather than
    parsed JSON: a comparison of parsed objects would be blind to a re-encode,
    and a re-encode is exactly how a second surface silently changes the
    content address of the first. ``D-IMPL-126`` makes leaving the resource
    untouched an explicit constraint; this is that constraint, executable.
    """
    closed_root = tmp_path / "closed"
    opened_root = tmp_path / "opened"
    closed_root.mkdir()
    opened_root.mkdir()
    closed, _e1, _r1 = _local_world(
        closed_root,
        servable=assembled.servable,
        address=assembled.address,
    )
    opened, _e2, _r2 = _open_world(
        opened_root,
        servable=assembled.servable,
        address=assembled.address,
    )

    from_closed = _read_in_process(
        closed, assembled.address.uri, token=LOCAL_TOKEN
    )
    from_opened = _read_in_process(
        opened, assembled.address.uri, token=LOCAL_TOKEN
    )

    assert from_closed[0] is True
    assert from_opened[0] is True
    assert from_opened[1] == from_closed[1]


def test_a_naive_asked_at_is_refused_before_the_resolver_is_reached(
    assembled: Any, tmp_path: Path
) -> None:
    """T-16-23-06: a malformed instant is refused at the door, not downstream.

    ``ProductRequest`` *accepts* a naive ``asked_at`` and the failure surfaces
    later inside ``canonical_bytes`` (D-IMPL-38), which would turn a client's
    malformed argument into an opaque server error and an unpinnable replay
    record. The empty ``forwarded`` list is what proves the refusal happened
    **before** the resolver, and the empty ``calls`` list that it happened
    before the governance seam — it is a bad argument, not a decision about a
    caller.
    """
    forwarded: list[tuple[Perspective, object]] = []
    server, entitlement, _registry = _open_world(
        tmp_path,
        servable=assembled.servable,
        address=assembled.address,
        forwarded=forwarded,
    )

    is_error, detail = _call_tool_in_process(
        server,
        PRODUCT_REQUEST_TOOL,
        _tool_arguments(assembled.address, asked_at="2026-08-13T09:30:00"),
        token=LOCAL_TOKEN,
    )

    assert is_error is True
    assert "D-IMPL-38" in detail, detail
    assert forwarded == []
    assert entitlement.calls == []


# --- the tool over a real wire: two subjects, two answers ------------------


def _call_tool_over_the_wire(
    bridge: SyncMcpBridge, url: str, arguments: dict[str, Any]
) -> tuple[bool, str]:
    """Call the child's product tool; return ``(is_error, joined text)``."""

    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
        texts = [
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        ]
        return bool(result.isError), " | ".join(texts)

    return bridge.run(
        run_with_session(
            url=url,
            operation=operation,
            http_client_factory=authorized_http_client,
        )
    )


@with_child
@pytest.mark.parametrize("axis", ["subject", "asked_at"])
def test_two_questions_reach_two_content_addresses(
    axis: str,
    loopback_url: str,
    expected: tuple[str, ProductAddress],
    bridge: SyncMcpBridge,
) -> None:
    """The refutation: a Context Product is not a precalculated static object.

    ``D-IMPL-126``'s decisive finding is that a resource-only door cannot
    refute that reading, because which question gets answered is entirely the
    server's choice when the caller has no way to ask one. Two calls differing
    in exactly one axis, over a real process boundary, returning two different
    ``sha256`` digests, is that refutation in executable form.

    **This proves the door, not the projection**, and the distinction matters:
    ``D-IMPL-126`` records that a naive projection reading ``view.relationships``
    wholesale produced *identical* addresses for two different subjects, because
    seeds narrow only when a segment fragment declares a ``traverse``
    (``src/ccf/projection/engine.py``). The child's resolver therefore
    differentiates deliberately — see ``mcp_egress_child.answer_for`` — so that
    a failure here is a failure of the door to carry the question through,
    which is the only thing this test is entitled to claim.
    """
    _canonical, address = expected
    varied: dict[str, Any] = (
        {"subject": LOCAL_OTHER_SUBJECT}
        if axis == "subject"
        else {
            "asked_at": (
                LOCAL_ASKED_AT.replace(hour=11, minute=45).isoformat()
            )
        }
    )

    first_error, first = _call_tool_over_the_wire(
        bridge, loopback_url, _tool_arguments(address)
    )
    second_error, second = _call_tool_over_the_wire(
        bridge, loopback_url, _tool_arguments(address, **varied)
    )

    assert first_error is False, first
    assert second_error is False, second
    assert hashlib.sha256(first.encode("utf-8")).hexdigest() != hashlib.sha256(
        second.encode("utf-8")
    ).hexdigest(), (
        f"two calls differing only in {axis} returned the same content"
        " address; the door is not carrying the caller's question through to"
        " the resolver (D-IMPL-126)"
    )
    # And neither is the class's standing answer: the tool answered the
    # question rather than re-serving what the resource serves.
    assert first != _canonical
    assert second != _canonical


# --- the fixture's own failure mode ----------------------------------------


def test_a_child_that_dies_at_import_fails_with_its_stderr(tmp_path: Path) -> None:
    """A crashing child produces a diagnosis, not ``int('')`` (fixture hardening).

    This is the fixture's own regression test: the readiness gate is a blocking
    ``readline()``, and the empty-line case is exactly where a naive
    implementation raises something that says nothing about the child.
    """
    from crossproc.conftest import spawn_child_server

    broken = tmp_path / "broken_child.py"
    broken.write_text("raise SystemExit('deliberate child import failure')\n")

    with pytest.raises(AssertionError, match="deliberate child import failure"):
        with spawn_child_server(broken):
            pass
