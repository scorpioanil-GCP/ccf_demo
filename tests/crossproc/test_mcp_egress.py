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
=========================================  ===================================

Every domain value — tenant, product class, schema version — comes from
``tests/fixtures/banking/`` by way of the child's builder. Delete the fixtures
and this file has nothing to assert (CLAUDE.md §6.4 applied to fixture code).
"""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.settings import AuthSettings
from mcp.types import TextResourceContents
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
from ccf_runtime.mcp.egress import build_egress_server

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
LOCAL_UNGRANTED_ROLE = "local-role-ungranted"
LOCAL_POLICY_VERSION = "1.0.0"
LOCAL_AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)


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
) -> tuple[object, _RecordingEntitlement, ControlPlaneRegistry]:
    """An egress server over a stub resolver, plus its recording entitlement.

    ``forwarded`` collects every ``(perspective, request)`` pair the door
    handed the resolver, which is what lets a test assert the *value* the door
    forwarded rather than only that the parameter exists (D-IMPL-108).
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
    )
    return server, entitlement, registry


def _read_in_process(
    server: object, uri: str, *, token: str | None
) -> tuple[bool, str]:
    """Read one resource over the server's own ASGI app; return ``(ok, text)``.

    ``httpx.ASGITransport`` does not drive the ASGI lifespan and the FastMCP
    streamable-HTTP app starts its session manager *in* the lifespan, so the
    lifespan context is entered explicitly — exactly what uvicorn does for the
    cross-process siblings.

    A refusal is returned rather than raised, and the *reason* is returned
    with it. Two things make that the right shape here: an exception escaping
    the lifespan is re-wrapped by its task group into a ``BaseExceptionGroup``
    that says nothing about the door, and — more importantly — a refusal test
    that only asserts "it raised" would pass against a door refusing for a
    reason nobody intended. The returned text carries the typed
    ``error_code``, which is the assertion worth making.
    """
    app = server.streamable_http_app()  # type: ignore[attr-defined]

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    def client_factory() -> httpx.AsyncClient:
        headers = {} if token is None else {"Authorization": f"Bearer {token}"}
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=IN_PROCESS_BASE_URL,
            headers=headers,
        )

    async def with_lifespan() -> tuple[bool, str]:
        async with app.router.lifespan_context(app):  # type: ignore[attr-defined]
            try:
                return True, await run_with_session(
                    url=f"{IN_PROCESS_BASE_URL}/mcp",
                    operation=operation,
                    http_client_factory=client_factory,
                )
            except McpServerUnreachable as refused:
                return False, _flatten(refused)

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
