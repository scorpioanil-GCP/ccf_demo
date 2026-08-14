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
            **_builder_kwargs(tmp_path),
        )

    assert GET_CONTEXT_TOOL in str(raised.value)


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
    """
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        build_experience_server,
    )

    def provide_context(*, tenant: str, entity: str) -> str:  # pragma: no cover
        raise AssertionError("a construction-time test calls no seam")

    with pytest.raises(ValueError) as raised:
        build_experience_server(
            tool_allowlist=frozenset({GET_CONTEXT_TOOL}),
            context_provider=provide_context,
            get_context_description=None,
            **_builder_kwargs(tmp_path),
        )

    assert GET_CONTEXT_TOOL in str(raised.value)


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
