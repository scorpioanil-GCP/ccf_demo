"""TP-02 — the ``claude`` child must not inherit the fabric's environment (D-IMPL-361).

Measured in the vendor (claude-agent-sdk 0.2.128,
``claude_agent_sdk/_internal/transport/subprocess_cli.py``):
``SubprocessCLITransport.connect`` builds the child environment as
``{**os.environ (minus CLAUDECODE), "CLAUDE_CODE_ENTRYPOINT": ..., **options.env,
"CLAUDE_AGENT_SDK_VERSION": ...}`` (lines 689-694) and hands it to
``anyio.open_process(..., env=process_env)`` (line 739). ``options.env`` merges
**over** the inherited environment and cannot subtract. The version probe
(``_check_claude_version``, lines 1031-1035) spawns the same binary with no
``env=`` at all, so it inherits everything too.

So the test asserts on what is actually handed to the spawn: it replaces
``anyio.open_process`` with a recorder that refuses to start anything, drives
``connect()`` on the transport the adapter supplies (on a tree that supplies
none, the vendor default — the one an adopter gets by not passing a
transport), and checks every recorded spawn. An unrelated secret in
``os.environ`` must be absent; the ruled default allowlist (``PATH``,
``HOME``) must be present. Offline: nothing is spawned.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any

import pytest

from conftest import harness_unavailable
from conformance.test_harness_adapter import (
    World,
    _harness_fixture,
    no_model_reachable,  # noqa: F401 - autouse socket guard, reused not copied
)

pytestmark = [pytest.mark.harness]

LEG = "claude-agent"

#: An unrelated variable in the fabric's own environment. Its name is test
#: vocabulary; its value is a marker, never a real credential.
SECRET_NAME = "CCF_TEST_SECRET"
SECRET_VALUE = "tp02-marker-must-not-reach-the-child"

#: The controller's ruling for the undeclared case (plan, Global Constraint 7).
RULED_DEFAULT = ("PATH", "HOME")


class _Refused(Exception):
    """Raised by the recorder so ``connect()`` never starts a process."""


def _spawns(monkeypatch: pytest.MonkeyPatch) -> list[Mapping[str, Any]]:
    import anyio

    recorded: list[Mapping[str, Any]] = []

    async def recorder(command: Any, **kwargs: Any) -> Any:
        recorded.append({"command": list(command), **kwargs})
        raise _Refused(command)

    monkeypatch.setattr(anyio, "open_process", recorder)
    return recorded


def _adapter(**kwargs: Any) -> Any:
    harness_unavailable("claude_agent_sdk", LEG)
    from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

    values = _harness_fixture()[LEG]
    return ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects="governed",
        **kwargs,
    )


def _drive_connect(adapter: Any, carrier: Any) -> None:
    """Run ``connect()`` on the transport an adopter would hand the vendor."""
    from dataclasses import replace

    from claude_agent_sdk._internal.transport.subprocess_cli import (
        SubprocessCLITransport,
    )

    # A path that resolves no binary: ``_find_cli`` is skipped, nothing runs.
    carrier = replace(carrier, cli_path="/nonexistent/ccf-tp02/claude")
    build = getattr(adapter, "transport", None)
    transport = (
        build(carrier)
        if build is not None
        else SubprocessCLITransport(prompt="", options=carrier)
    )
    with pytest.raises(Exception):
        asyncio.run(transport.connect())


def _child_environments(
    spawns: list[Mapping[str, Any]],
) -> list[tuple[str, Mapping[str, str]]]:
    """Each spawn's argv tail and environment; ``env=None`` means full inheritance.

    The argv tail names the spawn (the version probe is ``-v``) without
    printing the environment: an assertion message must never dump the
    fabric's variables into a test log.
    """
    return [
        (
            " ".join(spawn["command"][1:2]),
            spawn.get("env") if spawn.get("env") is not None else dict(os.environ),
        )
        for spawn in spawns
    ]


def test_an_unrelated_fabric_variable_does_not_reach_the_claude_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TP-02 as worded: the fabric's environment does not reach the child."""
    monkeypatch.setenv(SECRET_NAME, SECRET_VALUE)
    for name in RULED_DEFAULT:
        monkeypatch.setenv(name, os.environ.get(name) or f"/tp02/{name.lower()}")
    spawns = _spawns(monkeypatch)
    world = World()
    world.bind(world.grant_a, world.definition_a)
    adapter = _adapter()
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())

    _drive_connect(adapter, carrier)

    assert spawns, "connect() reached no spawn, so nothing was measured"
    for spawn, environment in _child_environments(spawns):
        leaked = SECRET_NAME in environment
        assert not leaked, (
            f"{SECRET_NAME} from the fabric's environment reached the claude"
            f" child spawned with {spawn!r} — options.env merges over os.environ"
            " and cannot subtract (TP-02)"
        )
        assert not any(value == SECRET_VALUE for value in environment.values())
        for name in RULED_DEFAULT:
            assert environment.get(name) == os.environ[name], name


def test_a_declared_child_environment_is_exactly_what_the_child_receives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deployment-declared names and values pass; nothing else from the fabric does."""
    monkeypatch.setenv(SECRET_NAME, SECRET_VALUE)
    spawns = _spawns(monkeypatch)
    world = World()
    world.bind(world.grant_a, world.definition_a)
    declared = {"PATH": "/tp02/declared/bin", "CCF_TP02_DECLARED": "declared-value"}
    adapter = _adapter(child_environment=declared)
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    assert dict(carrier.env) == declared

    _drive_connect(adapter, carrier)

    assert spawns
    for spawn, environment in _child_environments(spawns):
        leaked = SECRET_NAME in environment
        assert not leaked, f"{SECRET_NAME} reached the child spawned with {spawn!r}"
        inherited_home = "HOME" in environment and "HOME" not in declared
        assert not inherited_home, "an undeclared HOME reached the child"
        for name, value in declared.items():
            assert environment.get(name) == value, name


def test_the_vendor_default_transport_built_from_the_carrier_cannot_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TP-02 fails closed on the default path, not open.

    An adopter who hands the carrier to ``ClaudeSDKClient(options=carrier)`` or
    ``query(options=carrier)`` without ``adapter.transport(carrier)`` gets the
    vendor's own ``SubprocessCLITransport``, which merges the fabric's whole
    environment into the child. That path must not be able to start the CLI at
    all. The recorder below behaves like the OS: a command naming no existing
    file raises ``FileNotFoundError``; a command naming a real binary is
    recorded as a spawn that *would have happened* and is then refused.
    """
    import anyio
    from claude_agent_sdk import CLINotFoundError
    from claude_agent_sdk._internal.transport.subprocess_cli import (
        SubprocessCLITransport,
    )

    would_spawn: list[str] = []

    async def like_the_os(command: Any, **kwargs: Any) -> Any:
        executable = str(list(command)[0])
        if not os.path.isfile(executable):
            raise FileNotFoundError(executable)
        would_spawn.append(" ".join(list(command)[1:2]))
        raise _Refused(command)

    monkeypatch.setattr(anyio, "open_process", like_the_os)
    world = World()
    world.bind(world.grant_a, world.definition_a)
    adapter = _adapter()
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())

    vendor_default = SubprocessCLITransport(prompt="", options=carrier)
    with pytest.raises(Exception) as raised:
        asyncio.run(vendor_default.connect())

    assert would_spawn == [], (
        f"the vendor's default transport built from the carrier spawned the"
        f" claude CLI ({would_spawn!r}) with the fabric's whole environment —"
        " TP-02 fails open on the path an adopter takes by omitting"
        " adapter.transport(carrier)"
    )
    assert isinstance(raised.value, CLINotFoundError), type(raised.value).__name__

    # The adapter's own transport is the one that can find the CLI.
    governed = adapter.transport(carrier)
    resolved = governed._options.cli_path or governed._find_cli()
    assert os.path.isfile(str(resolved)), resolved
