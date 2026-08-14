"""The Experience-surface MCP edge (EXPR-01): products + agents, one front door.

CLAUDE.md §8.3 ("MCP server — Context Products and agents exposed as MCP
Resources and MCP Tools") and §7.1 (the Experience Layer access surface) —
the D-GATE-I.3 named deferral, discharged. The child runs the authenticated
experience server over a real assembled banking product and a factory-built
fixture agent; this process reaches both across a real process boundary.

Every assertion below is drafted from *what would fail here*:

==========================================  ==================================
Invariant / requirement                     What would fail here
==========================================  ==================================
role separation (§7.1, T-07-22)             the experience module would import
                                            the egress or artifact role, or
                                            hold their schemes
zero privileged paths (T-07-20)             the experience module would import
                                            the Agent Factory, the Control
                                            Plane, or the agent package and
                                            hold a construction path of its
                                            own instead of an injected seam
shared derivation (D-IMPL-56, CINV-01)      the server would author tool prose
                                            of its own instead of rendering
                                            the ``ccf.skills`` derivation
replay integration (CLAUDE.md §4)           an agent invocation through the
                                            front door would not land in a
                                            Decision Replay record
tenant addressing (T-07-21)                 an agent or product would be
                                            served under a tenant it does not
                                            belong to
==========================================  ==================================

Every domain value — tenant, agent definition, skill entry, arguments —
comes from ``tests/fixtures/banking/`` by way of the child's shared builders.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from mcp.client.session import ClientSession
from mcp.types import TextResourceContents
from pydantic import AnyUrl

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.mcp.client import SyncMcpBridge, run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.skills.toolsurface import render_tool_surface
from ccf_runtime.http_api.errors import ERROR_PRODUCT_POLICY_ABSENT

from crossproc.servers.mcp_experience_child import (
    DEV_TOKEN,
    authorized_http_client,
    build_servable_product,
    build_world,
)

pytestmark = pytest.mark.crossproc

CHILD = Path(__file__).resolve().parent / "servers" / "mcp_experience_child.py"

CALL_TIMEOUT_SECONDS = 30.0

with_child = pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    """One bounded sync bridge per test, closed on teardown."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield bridge


def _read_text(bridge: SyncMcpBridge, url: str, uri: str) -> str:
    """Read one resource as text over the authenticated transport."""

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return bridge.run(
        run_with_session(
            url=url,
            operation=operation,
            http_client_factory=authorized_http_client,
        )
    )


def _read_resource_outcome(
    bridge: SyncMcpBridge,
    url: str,
    *,
    tenant: str,
    product_class: str,
    version: str,
    token: str = DEV_TOKEN,
) -> tuple[bool, str]:
    """Read the product resource; return ``(refused, detail-or-body)``.

    The tool leg reports a refusal as ``isError`` with the message in the
    content, the resource leg reports it by raising through the transport.
    Normalising the two here is what lets one parametrization drive both
    surfaces on one scenario; without it a parity test would be comparing two
    shapes rather than two decisions.
    """
    from ccf_runtime.mcp.experience import experience_product_uri

    uri = experience_product_uri(
        tenant=tenant, product_class=product_class, version=version
    )

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    try:
        return False, bridge.run(
            run_with_session(
                url=url,
                operation=operation,
                http_client_factory=lambda: authorized_http_client(token),
            )
        )
    except McpServerUnreachable as refused:
        return True, _causes(refused)


def _list_tool_names(bridge: SyncMcpBridge, url: str) -> set[str]:
    """The tool names ``tools/list`` advertises over the wire."""

    async def operation(session: ClientSession) -> set[str]:
        result = await session.list_tools()
        return {tool.name for tool in result.tools}

    return bridge.run(
        run_with_session(
            url=url,
            operation=operation,
            http_client_factory=authorized_http_client,
        )
    )


def _call_tool(
    bridge: SyncMcpBridge,
    url: str,
    name: str,
    arguments: dict[str, Any],
    token: str = DEV_TOKEN,
) -> tuple[bool, str]:
    """Call one tool; return ``(is_error, first text content)``.

    ``token`` defaults to the entitled credential, so every pre-existing
    caller is unaffected. It exists because 16-24 has to drive the *same*
    tool with a second, genuinely-recognised credential the tenant's policy
    does not declare: authentication and entitlement are two decisions, and a
    helper that could only present one credential could not tell them apart.
    """

    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(name, arguments)
        texts = [
            content.text
            for content in result.content
            if hasattr(content, "text")
        ]
        return bool(result.isError), texts[0] if texts else ""

    return bridge.run(
        run_with_session(
            url=url,
            operation=operation,
            http_client_factory=lambda: authorized_http_client(token),
        )
    )


# --- the structural claims the module docstring makes -----------------------


def test_the_experience_module_holds_no_privileged_path() -> None:
    """T-07-20: the tool leg is an injected seam, never a construction path.

    Asserted against the module's source because that is where the claim is
    falsifiable: an import of the factory, the Control Plane, the agents
    package, or the graph would be the first step of a privileged path.
    """
    import ccf_runtime.mcp.experience as experience

    source = inspect.getsource(experience)
    for forbidden in (
        "ccf.agents",
        "ccf.controlplane",
        "ccf.graph",
        "AgentFactory",
        "GraphWriter",
        "GraphReader",
    ):
        assert forbidden not in source, (
            f"{forbidden} appears in the experience server's source; the"
            " agent leg reaches agents only through injected Protocol"
            " callables (T-07-20; CLAUDE.md §6.4)"
        )


def test_the_experience_scheme_is_its_own() -> None:
    """T-07-22: the front door does not mint egress or artifact addresses."""
    from ccf.artifacts.protocol import ARTIFACT_URI_SCHEME
    from ccf_runtime.mcp.egress import PRODUCT_URI_SCHEME
    from ccf_runtime.mcp.experience import EXPERIENCE_PRODUCT_URI_SCHEME

    assert EXPERIENCE_PRODUCT_URI_SCHEME != PRODUCT_URI_SCHEME
    assert EXPERIENCE_PRODUCT_URI_SCHEME != ARTIFACT_URI_SCHEME


# --- the promoted default-ON tools and the allowlist (D-IMPL-74) ------------


@with_child
def test_a_default_built_server_advertises_the_promoted_tools(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-IMPL-74: the three external-consumption tools register by default.

    Asserted over the wire against the default-built child, because
    ``tools/list`` is exactly what an external consumer sees: nothing was
    opted into, and the front door serves external consumption out of the
    box (Dave, 2026-08-02).
    """
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        GET_REPLAY_RECORD_TOOL,
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
    )

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    advertised = _list_tool_names(bridge, url)

    assert {
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        GET_REPLAY_RECORD_TOOL,
        LIST_AGENTS_TOOL,
        INVOKE_AGENT_TOOL,
    } <= advertised


def test_an_allowlist_excluded_tool_is_never_registered(
    tmp_path: Path,
) -> None:
    """D-05 via D-IMPL-74: omission happens at registration time.

    A server built with an allowlist that excludes ``invoke_agent`` does not
    advertise it — the tool was never registered, so no post-hoc filter is
    involved and the model physically cannot call it. Asserted in-process on
    the same ``build_server`` composition the child runs, so the only
    difference from the default-built server is the allowlist itself.
    """
    import anyio

    from ccf_runtime.mcp.experience import (
        EXPERIENCE_TOOLS,
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        GET_REPLAY_RECORD_TOOL,
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
    )

    from crossproc.servers.mcp_experience_child import build_server

    server = build_server(
        workspace=tmp_path,
        tool_allowlist=EXPERIENCE_TOOLS - {INVOKE_AGENT_TOOL},
    )

    advertised = {tool.name for tool in anyio.run(server.list_tools)}

    assert INVOKE_AGENT_TOOL not in advertised
    assert {
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        GET_REPLAY_RECORD_TOOL,
        LIST_AGENTS_TOOL,
    } <= advertised


# --- builder fail-fast validation (D-01/D-03/D-05; Dave, 2026-08-02) --------


def _builder_kwargs(tmp_path: Path) -> dict[str, Any]:
    """Minimal valid arguments for :func:`build_experience_server`.

    Only the unconditionally-required seams are supplied. The
    conditionally-required provider/description pairs (D-03) are each test's
    business, which is the point: what is required now depends on what the
    allowlist admits, not on the signature.
    """
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )
    from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier

    from crossproc.servers.mcp_experience_child import (
        AUDIT_INSTANT as ENTITLEMENT_AUDIT_INSTANT,
    )
    from crossproc.servers.mcp_experience_child import (
        ISSUER_URL,
        RESOURCE_SERVER_URL,
        SCOPE,
        SERVER_NAME,
        write_token_file,
    )

    def unreachable(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("a construction-time test calls no seam")

    return {
        "server_name": SERVER_NAME,
        # `product_resolver` alone: it backs the templated product
        # resource, which is not allowlist-gated and so always registers.
        # The agent seams are conditional like every other provider (D-03).
        "product_resolver": unreachable,
        "token_verifier": SourceBackedTokenVerifier(
            source=FileTokenSource(path=write_token_file(workspace=tmp_path))
        ),
        "auth_settings": AuthSettings(
            issuer_url=AnyHttpUrl(ISSUER_URL),
            resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
            required_scopes=[SCOPE],
        ),
        # Unconditionally required from 15.5-06 on, like the auth pair and
        # for the same reason: the product resource is not allowlist-gated,
        # so its governance seams are never dead configuration. These are
        # deliberately not `unreachable` — a construction-time test never
        # reaches them either, but a builder that quietly accepted `None`
        # here would produce a front door answering every verified caller.
        "entitlement_source": ControlPlaneProductEntitlementSource(
            control_plane=ControlPlaneRegistry(),
            clock=lambda: ENTITLEMENT_AUDIT_INSTANT,
        ),
        "perspective_resolver": unreachable,
    }


# --- the in-process door: legs the wire cannot carry ------------------------
#
# Three of 16-24's proofs cannot be driven over the process boundary and are
# driven here instead, each for a stated reason rather than for convenience:
# a call counter inside the child cannot be read from this process without
# inventing an IPC channel the fixture does not have; the class-outside-the-
# grant scenario has no wire representation on a tool whose class is
# deployment-declared; and the role-mismatch leg needs a policy granting two
# roles, where the shipped child grants exactly one and widening it would
# disturb every other leg. The door is composed from the same
# `_builder_kwargs` the construction-time tests use, so the only difference
# from the child is what each test is about.


def _in_process_door(
    tmp_path: Path,
    *,
    context_provider: Any,
    tenant: str,
    entitled_product_class: str,
    permitted_schema_names: frozenset[str],
    permitted_roles: frozenset[str],
    proposed_role: str,
) -> Any:
    """A gated ``get_context`` door with a policy this test chose."""
    from ccf.controlplane.registry import ControlPlaneRegistry
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
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        build_experience_server,
    )

    from crossproc.servers.mcp_experience_child import (
        AUDIT_INSTANT,
        CLIENT_ID,
        ENTITLEMENT_POLICY_VERSION,
    )

    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=tenant),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version=ENTITLEMENT_POLICY_VERSION,
            principals={
                CLIENT_ID: ProductEntitlementGrant(
                    permitted_schema_names=permitted_schema_names,
                    permitted_roles=permitted_roles,
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )

    def resolve_perspective(
        *, grant: Any, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(
            principal_id=grant.client_id, role=proposed_role
        )

    kwargs = _builder_kwargs(tmp_path)
    kwargs["entitlement_source"] = ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )
    kwargs["perspective_resolver"] = resolve_perspective
    return build_experience_server(
        tool_allowlist=frozenset({GET_CONTEXT_TOOL}),
        context_provider=context_provider,
        get_context_description="served for this test only",
        entitled_product_class=entitled_product_class,
        **kwargs,
    )


def _call_in_process(server: Any, arguments: dict[str, Any]) -> str:
    """Call ``get_context`` on an in-process server as the verified client.

    The bearer middleware is what normally populates the auth contextvar, and
    an in-process call has no request to carry a header. Setting the same
    contextvar the middleware sets is standing in for it exactly — not
    bypassing a check, since what is under test here is the *entitlement*
    decision, which runs on the verified identity however it arrived.
    """
    import anyio
    from mcp.server.auth.middleware.auth_context import auth_context_var
    from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
    from mcp.server.auth.provider import AccessToken

    from ccf_runtime.mcp.experience import GET_CONTEXT_TOOL

    from crossproc.servers.mcp_experience_child import CLIENT_ID, SCOPE

    reset = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process", client_id=CLIENT_ID, scopes=[SCOPE]
            )
        )
    )
    try:
        result = anyio.run(server.call_tool, GET_CONTEXT_TOOL, arguments)
    finally:
        auth_context_var.reset(reset)
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, dict):
        return json.dumps(result)
    return "".join(
        block.text for block in result if hasattr(block, "text")
    )


def test_an_unknown_allowlist_entry_is_refused(tmp_path: Path) -> None:
    """D-01 (Dave, 2026-08-02): the allowlist fails closed, never fails open.

    An allowlist naming a tool the SDK does not have used to register nothing
    and say nothing, so the surface the deployment intended and the surface
    actually served diverged in silence. The builder now refuses, naming the
    entry it could not resolve.
    """
    from ccf_runtime.mcp.experience import build_experience_server

    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({"not_a_tool"}),
            **_builder_kwargs(tmp_path),
        )

    assert "not_a_tool" in str(raised.value)


def test_an_allowlisted_tool_without_its_provider_is_refused(
    tmp_path: Path,
) -> None:
    """D-03 (Dave, 2026-08-02): allowlisted implies provider *and* description.

    The providers are Optional now (D-04), so requiredness had to move
    somewhere; registration time is where it can be conditional on the
    allowlist. A tool admitted with no seam behind it would advertise itself
    and then fail on first call — the failure belongs at build time.

    ``entitled_product_class`` is supplied so this keeps failing for **its
    own** reason: 16-24 added a second conditional refusal to the same block,
    and a test whose input trips both can no longer tell which one it is
    testing. The assertion below names the provider leg for the same reason —
    a future refactor folding the two conditions together would satisfy the
    tool-name assertion alone.
    """
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        build_experience_server,
    )

    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({GET_CONTEXT_TOOL}),
            context_provider=None,
            get_context_description="served for this test only",
            entitled_product_class="served-for-this-test-only",
            **_builder_kwargs(tmp_path),
        )

    assert GET_CONTEXT_TOOL in str(raised.value)
    assert "provider or description" in str(raised.value)
    assert "entitled_product_class" not in str(raised.value)


def test_an_allowlisted_agent_tool_without_its_provider_is_refused(
    tmp_path: Path,
) -> None:
    """D-03 reaches the agent seams too: requiredness follows exposure.

    They were unconditionally required, so a deployment allowlisting only
    the consumption tools still had to hand in dead `agent_directory` /
    `agent_invoker` callables to satisfy the signature — precisely the
    shape D-03 exists to remove.
    """
    from ccf_runtime.mcp.experience import (
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
        build_experience_server,
    )

    for tool in (LIST_AGENTS_TOOL, INVOKE_AGENT_TOOL):
        with pytest.raises(ValueError) as raised:
            build_experience_server(
                tool_allowlist=frozenset({tool}),
                **_builder_kwargs(tmp_path),
            )
        assert tool in str(raised.value)


def test_a_server_exposing_no_agent_tools_needs_no_agent_seams(
    tmp_path: Path,
) -> None:
    """The other half of D-03: omission is legal when nothing is exposed.

    The two ``entitled_product_class`` / ``lineage_tenant`` keywords appear
    here because ``get_lineage`` **is** exposed on this server, and 16-24
    gated it: its declared address is required exactly when the tool is
    admitted. The test's own claim — that omitting the *agent* seams is legal
    when no agent tool is exposed — is untouched.
    """
    from ccf_runtime.mcp.experience import (
        GET_LINEAGE_TOOL,
        build_experience_server,
    )

    def provide_lineage() -> str:  # pragma: no cover - never called
        raise AssertionError("a construction-time test calls no seam")

    build_experience_server(
        tool_allowlist=frozenset({GET_LINEAGE_TOOL}),
        lineage_provider=provide_lineage,
        get_lineage_description="served for this test only",
        entitled_product_class="served-for-this-test-only",
        lineage_tenant="served-for-this-test-only",
        **_builder_kwargs(tmp_path),
    )


def test_an_allowlisted_tool_without_its_description_is_refused(
    tmp_path: Path,
) -> None:
    """D-03: the description leg is required on the same terms as the provider.

    Asymmetric with the agent tools on purpose (D-13): the consumption tools
    author no prose of their own (CINV-01), so an absent description is a
    missing deployment value, not a defaultable one.

    ``entitled_product_class`` is supplied, and the assertion names the leg,
    for the reason given on the provider twin above: 16-24 put a second
    conditional refusal in this block, and neither test may be allowed to
    pass off the other one's check.
    """
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        build_experience_server,
    )

    def provide_context(
        *, tenant: str, entity: str, perspective: Any
    ) -> str:  # pragma: no cover
        raise AssertionError("a construction-time test calls no seam")

    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({GET_CONTEXT_TOOL}),
            context_provider=provide_context,
            get_context_description=None,
            entitled_product_class="served-for-this-test-only",
            **_builder_kwargs(tmp_path),
        )

    assert GET_CONTEXT_TOOL in str(raised.value)
    assert "provider or description" in str(raised.value)
    assert "entitled_product_class" not in str(raised.value)


def test_the_agent_tools_advertise_the_sdk_default_descriptions(
    tmp_path: Path,
) -> None:
    """D-12/D-13 (Dave, 2026-08-02): the agent tools are parameterized too.

    They used to fall through to their inner functions' docstrings, which is
    exactly the CINV-01 unevenness the promoted tools do not have. They now
    carry ``description=`` like every sibling, defaulting to SDK constants
    when the deployment supplies none — the deliberate asymmetry D-13 rules.
    """
    import anyio

    from ccf_runtime.mcp.experience import (
        DEFAULT_INVOKE_AGENT_DESCRIPTION,
        DEFAULT_LIST_AGENTS_DESCRIPTION,
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
    )

    from crossproc.servers.mcp_experience_child import build_server

    server = build_server(workspace=tmp_path)
    advertised = {
        tool.name: tool.description for tool in anyio.run(server.list_tools)
    }

    assert advertised[LIST_AGENTS_TOOL] == DEFAULT_LIST_AGENTS_DESCRIPTION
    assert advertised[INVOKE_AGENT_TOOL] == DEFAULT_INVOKE_AGENT_DESCRIPTION


# --- the cross-process round trips ------------------------------------------


@with_child
def test_a_context_product_is_served_on_the_experience_edge(
    child_server_port: int, bridge: SyncMcpBridge, tmp_path: Path
) -> None:
    """The front door serves the fabric's own product, byte for byte.

    Recomputed here rather than trusted from the wire — assembly is
    deterministic for a fixed boundary, so the two processes must agree on
    canonical bytes exactly.
    """
    from ccf_runtime.mcp.experience import experience_product_uri

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    assembled = build_servable_product(
        database_path=tmp_path / "experience-parent.sqlite3"
    )
    expected = canonical_bytes(assembled.servable.product).decode("utf-8")

    received = _read_text(
        bridge,
        url,
        experience_product_uri(
            tenant=assembled.address.tenant,
            product_class=assembled.address.product_class,
            version=assembled.address.version,
        ),
    )

    assert received == expected


@with_child
def test_agents_are_listed_with_the_shared_tool_surface_derivation(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """Agent Tools derive from registered definitions via the 07-03 derivation.

    The expected surfaces are rendered *here* by
    :func:`ccf.skills.toolsurface.render_tool_surface` over the same fixture
    catalog entries the child bound — so a server that authored prose of its
    own, or drifted from the shared derivation, fails byte for byte
    (D-IMPL-56; CINV-01).
    """
    from ccf_runtime.mcp.experience import LIST_AGENTS_TOOL

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    world = build_world()

    is_error, body = _call_tool(
        bridge, url, LIST_AGENTS_TOOL, {"tenant": world.tenant}
    )

    assert not is_error, body
    catalog = json.loads(body)
    assert catalog["tenant"] == world.tenant
    (listing,) = catalog["agents"]
    assert listing["definition_key"] == world.definition_key
    assert listing["definition_version"] == world.definition_version
    assert listing["name"] == world.definition.name
    assert listing["archetypes"] == list(world.definition.archetypes)

    expected_surface = render_tool_surface(world.skill_entry)
    (tool,) = listing["tools"]
    assert tool["skill"] == world.skill_entry.name
    assert tool["description"] == expected_surface.description
    assert tool["input_schema"] == expected_surface.input_schema


@with_child
def test_a_foreign_tenant_sees_no_agents(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """T-07-21: tenancy is resolved per call, and the wrong tenant gets nothing."""
    from ccf_runtime.mcp.experience import LIST_AGENTS_TOOL

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    world = build_world()

    is_error, body = _call_tool(
        bridge,
        url,
        LIST_AGENTS_TOOL,
        {"tenant": f"{world.tenant}-not-this-one"},
    )

    assert not is_error, body
    assert json.loads(body)["agents"] == []


@with_child
def test_invoking_an_agent_goes_through_the_factory_and_lands_in_replay(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """The Tool leg is the in-process path: factory-built agent, replayed decision.

    Three facts are asserted from the wire alone: the invocation dispatched
    the governed bound skill (the fixture callable's deterministic output);
    the replay record's dimension 4 carries the factory-computed agent
    identity — the content hash this process independently derives from the
    same definition artifact; and the record's content hash equals the
    address the child's ArtifactStore filed it under, so the decision is
    resolvable at an exact address (D-IMPL-26).
    """
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    world = build_world()
    tool_fixture = world.skill_entry
    arguments = {"entity_name": "hollis-industrial"}

    is_error, body = _call_tool(
        bridge,
        url,
        INVOKE_AGENT_TOOL,
        {
            "tenant": world.tenant,
            "definition_key": world.definition_key,
            "definition_version": world.definition_version,
            "skill": tool_fixture.name,
            "arguments": arguments,
        },
    )

    assert not is_error, body
    payload = json.loads(body)
    assert payload["invocation"] == {
        "invoked": "covenant-metrics",
        **arguments,
    }

    record = json.loads(payload["replay_record"])
    conditioning = record["perspective_conditioning"]
    assert conditioning["agent_definition_hash"] == content_hash(
        world.definition
    )
    assert conditioning["archetype_composition"] == list(
        world.definition.archetypes
    )
    # The decision landed at an exact, content-derived address.
    assert payload["replay_ref"]["content_address"] == content_hash(
        json.loads(payload["replay_record"])
    )


@with_child
def test_an_unrecognised_credential_is_refused(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """The experience edge is authenticated (D-26; auth.py posture)."""
    import httpx

    url = f"http://127.0.0.1:{child_server_port}/mcp"

    async def operation(session: ClientSession) -> None:  # pragma: no cover
        raise AssertionError("the handshake should have been refused")

    with pytest.raises(McpServerUnreachable):
        bridge.run(
            run_with_session(
                url=url,
                operation=operation,
                http_client_factory=lambda: httpx.AsyncClient(
                    headers={"Authorization": "Bearer ccf-not-a-token"}
                ),
            )
        )


# --- the front door is entitled, not merely authenticated (15.5-06) ---------
#
# Deliberately asserted here rather than by importing the egress suite: the
# two files assert the same property about two different servers, and they
# must be able to fail independently. A shared test module would report one
# failure for two doors and hide which one regressed.


def test_the_front_door_imports_the_seams_rather_than_re_declaring_them() -> None:
    """One definition of "entitled", three doors — asserted, not reviewed.

    What would fail here: this module growing its own
    ``PerspectiveResolverProtocol``, or its own ordering of the two raising
    checks. Two readings of the phase's central security property would then
    exist, and the one that drifted would be the one nobody was watching.

    Note the *shape* of the shared home. The seams live in
    :mod:`ccf_runtime.authz.product_entitlement` — a package neither MCP role
    owns — rather than in one door imported by the other, because
    ``tests/invariants/test_mcp_role_separation.py`` asserts that these
    modules import none of their siblings. Sharing through a third module is
    the resolution :mod:`ccf_runtime.authz.protocol` already models for the
    two HITL doors.
    """
    import ccf_runtime.mcp.experience as experience

    source = inspect.getsource(experience)
    assert "from ccf_runtime.authz.product_entitlement import" in source
    assert "entitled_perspective" in source
    assert "class PerspectiveResolverProtocol" not in source
    assert "class ProductEntitlementSourceProtocol" not in source
    assert "require_schema" not in source
    assert "require_role" not in source
    # And it did not reach the shared home by importing a sibling role. The
    # assertion is on *import statements* rather than on the text, because a
    # docstring may name a sibling's type in a cross-reference — naming is
    # not importing, and the role-separation invariant is about the latter.
    assert "from ccf_runtime.mcp.egress import" not in source
    assert "import ccf_runtime.mcp.egress" not in source


def test_the_front_door_refuses_to_build_without_its_governance_seams(
    tmp_path: Path,
) -> None:
    """T-15.5-21: no inert configuration, on the same terms as the egress door.

    What would fail here: either seam acquiring a ``None`` default "for
    compatibility", which would let the SDK's *external* front door ship
    answering every verified caller with every class its resolver holds.
    """
    from ccf_runtime.mcp.experience import build_experience_server

    for omitted in ("entitlement_source", "perspective_resolver"):
        kwargs = _builder_kwargs(tmp_path)
        del kwargs[omitted]
        with pytest.raises(TypeError, match=omitted):
            build_experience_server(**kwargs)


@with_child
def test_a_verified_but_undeclared_principal_is_refused_at_the_front_door(
    child_server_port: int, bridge: SyncMcpBridge, tmp_path: Path
) -> None:
    """Authentication is not entitlement, on the surface that matters most.

    The credential is genuinely recognised — the handshake succeeds and the
    caller is verified — and the principal is simply not one the tenant's
    policy declares. Without this case the round-trip test above would pass
    against a door that gated on nothing at all.
    """
    import httpx

    from ccf_runtime.http_api.errors import ERROR_PRINCIPAL_NOT_ENTITLED
    from ccf_runtime.mcp.experience import experience_product_uri

    from crossproc.servers.mcp_experience_child import UNENTITLED_TOKEN

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    assembled = build_servable_product(
        database_path=tmp_path / "experience-unentitled.sqlite3"
    )
    uri = experience_product_uri(
        tenant=assembled.address.tenant,
        product_class=assembled.address.product_class,
        version=assembled.address.version,
    )

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    with pytest.raises(McpServerUnreachable) as refused:
        bridge.run(
            run_with_session(
                url=url,
                operation=operation,
                http_client_factory=lambda: httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {UNENTITLED_TOKEN}"}
                ),
            )
        )

    # The typed constant, not the prose: the same vocabulary the HTTP door
    # renders as a 403 body (D-08 — one vocabulary, two renderings).
    assert ERROR_PRINCIPAL_NOT_ENTITLED in _causes(refused.value)


@with_child
def test_a_class_outside_the_grant_is_refused_at_the_front_door(
    child_server_port: int, bridge: SyncMcpBridge, tmp_path: Path
) -> None:
    """T-15.5-20 on the external surface: entitlement is per class.

    The entitled principal asks for a class the child's policy does not name.
    What would fail here: a door that checked only that the principal exists,
    which is authentication wearing an entitlement's name.
    """
    import httpx

    from ccf_runtime.http_api.errors import ERROR_PRODUCT_CLASS_UNENTITLED
    from ccf_runtime.mcp.experience import experience_product_uri

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    assembled = build_servable_product(
        database_path=tmp_path / "experience-other-class.sqlite3"
    )
    uri = experience_product_uri(
        tenant=assembled.address.tenant,
        product_class=f"{assembled.address.product_class}-not-this-one",
        version=assembled.address.version,
    )

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    with pytest.raises(McpServerUnreachable) as refused:
        bridge.run(
            run_with_session(
                url=url,
                operation=operation,
                http_client_factory=authorized_http_client,
            )
        )

    detail = _causes(refused.value)
    assert ERROR_PRODUCT_CLASS_UNENTITLED in detail
    # The refusal names the class, and it is the entitlement speaking rather
    # than the resolver: an unentitled class must never reach the resolver's
    # own "no such product" path.
    assert "-not-this-one" in detail


# --- the tools are entitled too, not merely authenticated (D-IMPL-128) ------
#
# The resource above was gated by 15.5-06 and the tool beside it was not, so
# every assertion in this section is about the *tool's own* surface. A source
# assertion cannot see a check bypassed on one branch; these go over the wire.


@with_child
def test_a_verified_but_undeclared_principal_is_refused_by_the_context_tool(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-IMPL-128 limb 1, the headline: the tool refuses what the resource refuses.

    The credential is genuinely recognised — the handshake succeeds — and the
    principal is simply not one the tenant's policy declares. What would fail
    here is the handler this plan replaced: ``return context_seam(tenant=
    tenant, entity=entity)``, which reached Context Product assembly with no
    grant check at all and served this caller a product.

    The typed constant, not the prose (D-08): the refusal has to be the
    entitlement's, in the same vocabulary the resource path and the HTTP door
    already speak.
    """
    from ccf_runtime.http_api.errors import ERROR_PRINCIPAL_NOT_ENTITLED
    from ccf_runtime.mcp.experience import GET_CONTEXT_TOOL

    from crossproc.servers.mcp_experience_child import UNENTITLED_TOKEN

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    world = build_world()

    is_error, body = _call_tool(
        bridge,
        url,
        GET_CONTEXT_TOOL,
        {"tenant": world.tenant, "entity": "hollis-industrial"},
        token=UNENTITLED_TOKEN,
    )

    assert is_error, body
    assert ERROR_PRINCIPAL_NOT_ENTITLED in body


@with_child
def test_a_foreign_tenant_is_refused_by_the_context_tool(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-IMPL-128's sharper half: the client-supplied tenant is decided against.

    The credential here is the **entitled** one. What is foreign is the
    ``tenant`` argument, and the door now resolves the policy under
    ``product_entitlement_key(tenant_id=<that argument>)`` — so naming a
    tenant means being decided against *that* tenant's policy, and no policy
    is registered under it.

    **This leg carries a vacuity trap and the assertion is written against
    it.** The child's ``provide_context`` already raises
    ``ExperienceProductNotServable`` for a foreign tenant, so a test asserting
    only "it errored" would pass identically before and after the gate
    existed and would prove nothing. The discriminator is **which** typed
    refusal: ``ERROR_PRODUCT_POLICY_ABSENT`` is the entitlement's
    deny-by-default path (``product_entitlement.py:285-302``) and a bare
    ``LookupError`` from the provider cannot produce it. The companion
    discriminator — that the provider was never entered at all — is asserted
    in the counter test below.
    """
    from ccf_runtime.http_api.errors import ERROR_PRODUCT_POLICY_ABSENT
    from ccf_runtime.mcp.experience import GET_CONTEXT_TOOL

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    world = build_world()

    is_error, body = _call_tool(
        bridge,
        url,
        GET_CONTEXT_TOOL,
        {
            "tenant": f"{world.tenant}-not-this-one",
            "entity": "hollis-industrial",
        },
    )

    assert is_error, body
    assert ERROR_PRODUCT_POLICY_ABSENT in body
    # And it is the entitlement speaking, not the provider: the provider's
    # own refusal is an ExperienceProductNotServable and says neither of
    # these things.
    assert "ExperienceProductNotServable" not in body


@with_child
def test_the_lineage_tool_is_entitled_against_its_declared_address(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-IMPL-129: a tool with no wire arguments is still decided, not served.

    Absence of a client parameter reduces steerability, never disclosure. At
    the phase base this tool returned a tenant's product lineage to every
    verified caller; it is now decided against the address the deployment
    declared, and the same undeclared principal the context tool refuses is
    refused here.

    Both legs in one test on purpose: a refusal assertion with no companion
    serve assertion is satisfied by a door that refuses everyone.
    """
    from ccf_runtime.http_api.errors import ERROR_PRINCIPAL_NOT_ENTITLED
    from ccf_runtime.mcp.experience import GET_LINEAGE_TOOL

    from crossproc.servers.mcp_experience_child import UNENTITLED_TOKEN

    url = f"http://127.0.0.1:{child_server_port}/mcp"

    is_error, body = _call_tool(
        bridge, url, GET_LINEAGE_TOOL, {}, token=UNENTITLED_TOKEN
    )
    assert is_error, body
    assert ERROR_PRINCIPAL_NOT_ENTITLED in body

    is_error, served = _call_tool(bridge, url, GET_LINEAGE_TOOL, {})
    assert not is_error, served
    assert json.loads(served)["operators_invoked"]


@pytest.mark.parametrize(
    "scenario",
    ["an-entitled-caller", "an-undeclared-principal", "a-foreign-tenant"],
)
@pytest.mark.parametrize("surface", ["the-resource", "the-get-context-tool"])
@with_child
def test_the_tool_and_the_resource_decide_one_scenario_alike(
    surface: str,
    scenario: str,
    child_server_port: int,
    bridge: SyncMcpBridge,
    tmp_path: Path,
) -> None:
    """One child, one policy, one grant — and two doors that must now agree.

    The defect ``D-IMPL-128`` ruled was precisely a disagreement between
    these two surfaces on the same server: the resource refused what the tool
    served. Driving both from one child through one parametrization is what
    makes a future divergence a failure rather than an observation, and both
    surfaces take ``tenant`` from the client so every scenario below has a
    wire representation on each.

    The class-outside-the-grant scenario is deliberately **not** here: the
    tool takes its class from the deployment, so that scenario has no wire
    representation on it and is driven in-process below against the operand
    the tool actually carries.
    """
    from ccf_runtime.http_api.errors import (
        ERROR_PRINCIPAL_NOT_ENTITLED,
        ERROR_PRODUCT_POLICY_ABSENT,
    )
    from ccf_runtime.mcp.experience import GET_CONTEXT_TOOL

    from crossproc.servers.mcp_experience_child import UNENTITLED_TOKEN

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    assembled = build_servable_product(
        database_path=tmp_path / f"parity-{surface}-{scenario}.sqlite3"
    )
    token = DEV_TOKEN
    tenant = assembled.address.tenant
    expected: str | None = None
    if scenario == "an-undeclared-principal":
        token = UNENTITLED_TOKEN
        expected = ERROR_PRINCIPAL_NOT_ENTITLED
    elif scenario == "a-foreign-tenant":
        tenant = f"{assembled.address.tenant}-not-this-one"
        expected = ERROR_PRODUCT_POLICY_ABSENT

    if surface == "the-get-context-tool":
        refused, detail = _call_tool(
            bridge,
            url,
            GET_CONTEXT_TOOL,
            {"tenant": tenant, "entity": "hollis-industrial"},
            token=token,
        )
    else:
        refused, detail = _read_resource_outcome(
            bridge,
            url,
            tenant=tenant,
            product_class=assembled.address.product_class,
            version=assembled.address.version,
            token=token,
        )

    if expected is None:
        assert not refused, detail
        # Served-vs-served is asserted on the bytes, not on the absence of an
        # error: two doors onto one assembled product must deliver the same
        # product, or "they agree" would mean only that both said yes.
        assert detail == canonical_bytes(assembled.servable.product).decode(
            "utf-8"
        )
    else:
        assert refused, detail
        assert expected in detail


@with_child
def test_the_agent_and_replay_tools_are_authenticated_but_not_entitled_open_gap(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-IMPL-129: a known gap, pinned open by an assertion rather than prose.

    **This is not a property the SDK wants.** ``list_agents``,
    ``invoke_agent`` and ``get_replay_record`` are served to a verified caller
    the tenant's entitlement policy does not declare — the same credential the
    two gated tools refuse three tests above. Each of the three asserts
    verified identity and decides nothing.

    Why they are not gated: the artifact they would be decided against is
    ``ProductEntitlementPolicy``, whose grants are ``permitted_schema_names``
    and ``permitted_roles``
    (``runtime/ccf_runtime/authz/product_entitlement.py:198-212``) and which
    says nothing about agents and nothing about replay records. Gating
    ``invoke_agent`` on it would assert that entitlement to receive a product
    class implies permission to invoke any agent in the tenant — a semantic
    the SDK would be inventing, which CLAUDE.md §11 forbids in those words.
    Closing it needs
    :class:`~ccf_runtime.authz.protocol.TenantAuthorizerProtocol` plus new
    action ids, which ``D-IMPL-129`` ruled out of this plan's scope and
    assigned to no owner.

    **The signature of the fix is that this test inverts.** Whoever closes the
    gap will find these three assertions failing; that is the intended
    collision, and flipping them to refusals is the correct repair. A gap held
    open by an executable assertion cannot rot the way a paragraph in a
    deferred-items file can.
    """
    from ccf_runtime.mcp.experience import (
        GET_REPLAY_RECORD_TOOL,
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
    )

    from crossproc.servers.mcp_experience_child import UNENTITLED_TOKEN

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    world = build_world()

    is_error, body = _call_tool(
        bridge,
        url,
        LIST_AGENTS_TOOL,
        {"tenant": world.tenant},
        token=UNENTITLED_TOKEN,
    )
    assert not is_error, body
    # Not merely "it returned": the undeclared caller received the tenant's
    # actual agent population, versions and bound skill surfaces.
    (listing,) = json.loads(body)["agents"]
    assert listing["definition_key"] == world.definition_key
    assert listing["tools"], listing

    is_error, body = _call_tool(
        bridge,
        url,
        INVOKE_AGENT_TOOL,
        {
            "tenant": world.tenant,
            "definition_key": world.definition_key,
            "definition_version": world.definition_version,
            "skill": world.skill_entry.name,
            "arguments": {"entity_name": "hollis-industrial"},
        },
        token=UNENTITLED_TOKEN,
    )
    assert not is_error, body
    # The undeclared caller dispatched a governed bound skill.
    assert json.loads(body)["invocation"]["invoked"] == "covenant-metrics"

    is_error, body = _call_tool(
        bridge,
        url,
        GET_REPLAY_RECORD_TOOL,
        {},
        token=UNENTITLED_TOKEN,
    )
    assert not is_error, body
    # And read back the five-dimension record of a decision, dimension 4
    # included — the widest disclosure on this server.
    assert json.loads(body)["perspective_conditioning"]


def test_a_refused_context_call_never_reaches_the_provider(
    tmp_path: Path,
) -> None:
    """The refusal is the entitlement's, and the provider is never entered.

    This is the assertion that closes the vacuity hazard on the foreign-tenant
    leg. The child's own provider raises for a foreign tenant, so "it errored"
    is compatible with a door that gates on nothing and lets the provider do
    the refusing — the difference is whether a refused caller moved any
    fabric.

    **Both directions in one test, deliberately.** A counter asserted only to
    be *unchanged* across a refusal is satisfied by a counter that never moves
    at all — including one wired to nothing. So the same counter is asserted
    to move across a served call in the same test, which is what makes the
    unchanged assertion mean something.
    """
    from ccf.projection.plan import Perspective

    world = build_world()
    consumed = world.definition.context_contract.consumes[0]
    role = world.definition.perspective.role
    calls: list[Perspective] = []

    def counting_provider(
        *, tenant: str, entity: str, perspective: Perspective
    ) -> str:
        calls.append(perspective)
        return json.dumps({"tenant": tenant, "entity": entity})

    server = _in_process_door(
        tmp_path,
        context_provider=counting_provider,
        tenant=world.tenant,
        entitled_product_class=consumed.product_class,
        permitted_schema_names=frozenset({consumed.product_class}),
        permitted_roles=frozenset({role}),
        proposed_role=role,
    )

    before = len(calls)
    with pytest.raises(Exception) as refused:
        _call_in_process(
            server,
            {"tenant": f"{world.tenant}-not-this-one", "entity": "any"},
        )
    assert ERROR_PRODUCT_POLICY_ABSENT in _causes(refused.value)
    assert len(calls) == before, "a refused call reached the provider"

    _call_in_process(server, {"tenant": world.tenant, "entity": "any"})
    assert len(calls) == before + 1, (
        "the counter never moves, so the unchanged assertion above proves"
        " nothing"
    )


def test_the_authorized_perspective_arrives_at_the_provider(
    tmp_path: Path,
) -> None:
    """D-IMPL-108 at the tool leg, asserted by value rather than by pattern.

    A grep for ``perspective=perspective`` in the door's source would pass
    against a door forwarding the wrong perspective, or one the entitlement
    never approved. What is asserted here is the object the provider actually
    received: its subject is the **verified** client id — never a caller's
    claim (D-IMPL-67) — and its role is the one the entitlement authorized.
    """
    from ccf.projection.plan import Perspective

    from crossproc.servers.mcp_experience_child import CLIENT_ID

    world = build_world()
    consumed = world.definition.context_contract.consumes[0]
    role = world.definition.perspective.role
    received: list[Perspective] = []

    def recording_provider(
        *, tenant: str, entity: str, perspective: Perspective
    ) -> str:
        received.append(perspective)
        return json.dumps({"served": entity})

    server = _in_process_door(
        tmp_path,
        context_provider=recording_provider,
        tenant=world.tenant,
        entitled_product_class=consumed.product_class,
        permitted_schema_names=frozenset({consumed.product_class}),
        permitted_roles=frozenset({role}),
        proposed_role=role,
    )

    _call_in_process(server, {"tenant": world.tenant, "entity": "any"})

    (arrived,) = received
    assert arrived.principal_id == CLIENT_ID
    assert arrived.role == role


def test_a_provider_handed_a_role_its_product_was_not_assembled_under_refuses(
    tmp_path: Path,
) -> None:
    """The second half of T-16-24-05: accepting the conditioning is not using it.

    The policy here grants **two** roles, and the deployment's resolver
    proposes the one the product was not assembled under — so the entitlement
    passes and the perspective that arrives is legitimately authorized, yet
    wrong for this product. A provider that accepted the argument and served
    anyway would ship ``DI-15.5-03`` one layer down with nothing on the wire
    to show it.

    Its own composition rather than the child's: the shipped child grants
    exactly one role, and widening its policy to two would change the
    scenario every other leg in this file runs under.
    """
    from ccf.projection.plan import Perspective

    from ccf_runtime.mcp.experience import ExperienceProductNotServable

    world = build_world()
    consumed = world.definition.context_contract.consumes[0]
    assembled_role = world.definition.perspective.role
    other_role = f"{assembled_role}-not-this-one"

    def checking_provider(
        *, tenant: str, entity: str, perspective: Perspective
    ) -> str:
        if perspective.role != assembled_role:
            raise ExperienceProductNotServable(
                f"assembled for {assembled_role!r}, the door authorized"
                f" {perspective.role!r}"
            )
        return json.dumps({"served": entity})

    server = _in_process_door(
        tmp_path,
        context_provider=checking_provider,
        tenant=world.tenant,
        entitled_product_class=consumed.product_class,
        permitted_schema_names=frozenset({consumed.product_class}),
        permitted_roles=frozenset({assembled_role, other_role}),
        proposed_role=other_role,
    )

    with pytest.raises(Exception) as refused:
        _call_in_process(server, {"tenant": world.tenant, "entity": "any"})

    detail = _causes(refused.value)
    assert assembled_role in detail
    assert other_role in detail


def test_a_deployment_declared_class_outside_the_grant_is_refused(
    tmp_path: Path,
) -> None:
    """T-15.5-20's scenario, against the operand this surface actually carries.

    The resource takes its class from the client, so the shipped resource test
    expresses this by asking for a class the policy does not name. The tool
    takes its class from the **deployment**, so the same scenario is a door
    built against a class outside the grant. Expressing it that way rather
    than substituting a weaker check is the point: each surface is driven on
    the operand it really has.
    """
    from ccf.projection.plan import Perspective
    from ccf_runtime.http_api.errors import ERROR_PRODUCT_CLASS_UNENTITLED

    world = build_world()
    consumed = world.definition.context_contract.consumes[0]
    role = world.definition.perspective.role

    def never_reached(
        *, tenant: str, entity: str, perspective: Perspective
    ) -> str:  # pragma: no cover - the whole point is that it is not
        raise AssertionError("an unentitled class reached the provider")

    server = _in_process_door(
        tmp_path,
        context_provider=never_reached,
        tenant=world.tenant,
        entitled_product_class=f"{consumed.product_class}-not-this-one",
        permitted_schema_names=frozenset({consumed.product_class}),
        permitted_roles=frozenset({role}),
        proposed_role=role,
    )

    with pytest.raises(Exception) as refused:
        _call_in_process(server, {"tenant": world.tenant, "entity": "any"})

    detail = _causes(refused.value)
    assert ERROR_PRODUCT_CLASS_UNENTITLED in detail
    assert "-not-this-one" in detail


def test_a_gated_tool_without_its_declared_address_is_refused(
    tmp_path: Path,
) -> None:
    """Requiredness follows exposure for the governance values too (D-03's rule).

    A deployment upgrading into the gate must not be able to lose its front
    door silently, nor to leave the entitlement deciding against a class
    nobody named. The refusal names the tool **and** the missing parameter,
    which is what keeps it distinguishable from the provider/description
    refusal the same block raises first.
    """
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        build_experience_server,
    )

    def provide_context(*, tenant: str, entity: str, perspective: Any) -> str:
        raise AssertionError("a construction-time test calls no seam")

    def provide_lineage() -> str:  # pragma: no cover - never called
        raise AssertionError("a construction-time test calls no seam")

    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({GET_CONTEXT_TOOL}),
            context_provider=provide_context,
            get_context_description="served for this test only",
            **_builder_kwargs(tmp_path),
        )
    assert GET_CONTEXT_TOOL in str(raised.value)
    assert "entitled_product_class" in str(raised.value)

    # The lineage tool needs both halves of its declared address, and the
    # tenant half is the one it cannot take from the wire.
    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({GET_LINEAGE_TOOL}),
            lineage_provider=provide_lineage,
            get_lineage_description="served for this test only",
            entitled_product_class="served-for-this-test-only",
            **_builder_kwargs(tmp_path),
        )
    assert GET_LINEAGE_TOOL in str(raised.value)
    assert "lineage_tenant" in str(raised.value)


def test_a_declared_address_for_an_unexposed_tool_is_refused(
    tmp_path: Path,
) -> None:
    """The other direction: inert governance configuration is refused too.

    A deployment that supplied a declared address believing a door was open,
    when the allowlist never admitted it, would otherwise learn nothing — the
    same failure mode D-01 removed for a misspelled tool name.
    """
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        LIST_AGENTS_TOOL,
        build_experience_server,
    )

    def directory(*, tenant: str) -> tuple[Any, ...]:  # pragma: no cover
        raise AssertionError("a construction-time test calls no seam")

    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({LIST_AGENTS_TOOL}),
            agent_directory=directory,
            entitled_product_class="served-for-this-test-only",
            **_builder_kwargs(tmp_path),
        )
    assert "entitled_product_class" in str(raised.value)
    assert GET_CONTEXT_TOOL in str(raised.value)

    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({LIST_AGENTS_TOOL}),
            agent_directory=directory,
            lineage_tenant="served-for-this-test-only",
            **_builder_kwargs(tmp_path),
        )
    assert "lineage_tenant" in str(raised.value)
    assert GET_LINEAGE_TOOL in str(raised.value)


def _causes(error: BaseException, _seen: frozenset[int] = frozenset()) -> str:
    """Every message in an exception's cause chain and group tree, joined.

    ``run_with_session`` renders whatever the transport raised, and anyio
    renders a task group's failure as ``unhandled errors in a TaskGroup`` with
    the real cause nested below. Asserting on the top-level string would
    assert on anyio's wording rather than on the door's refusal — the
    difference between "it failed" and "it refused for the stated reason".
    """
    if id(error) in _seen:
        return ""
    seen = _seen | {id(error)}
    parts = [f"{type(error).__name__}: {error}"]
    if isinstance(error, BaseExceptionGroup):
        parts.extend(_causes(inner, seen) for inner in error.exceptions)
    for chained in (error.__cause__, error.__context__):
        if chained is not None:
            parts.append(_causes(chained, seen))
    return " | ".join(part for part in parts if part)
