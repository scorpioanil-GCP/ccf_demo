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
    bridge: SyncMcpBridge, url: str, name: str, arguments: dict[str, Any]
) -> tuple[bool, str]:
    """Call one tool; return ``(is_error, first text content)``."""

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
            http_client_factory=authorized_http_client,
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
