"""TP-05 — the assembled system prompt must not reach the ``claude`` argv (D-IMPL-361).

Measured in the vendor (claude-agent-sdk 0.2.128,
``_internal/transport/subprocess_cli.py``): ``_build_command`` puts a string
``system_prompt`` on argv as ``--system-prompt <text>`` (lines 467-468) and a
``{"type": "file", "path": ...}`` one as ``--system-prompt-file <path>``
(lines 469-473); the bundled CLI (2.1.220) accepts ``--system-prompt-file``
and refuses it only when a truthy ``--system-prompt`` accompanies it. argv is
visible to every local process and to central process auditing — the bank
case the spec rates HIGH.

The test builds the carrier from real instructions and a real admitted product,
asks the adapter's transport for the exact argv the vendor would spawn (no
process is started), and asserts the prompt text is nowhere on it, while the
file option names a ``0600`` file in a ``0700`` directory whose bytes are the
prompt exactly as ``inject_context`` assembles it.
"""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from conftest import harness_unavailable
from conformance.test_harness_adapter import (
    BOUNDARY,
    World,
    _harness_fixture,
    _product,
    CLAUDE_ADAPTERS_BUILT,
    no_model_reachable,  # noqa: F401 - autouse socket guard, reused not copied
    remove_claude_prompt_directories,  # noqa: F401 - autouse teardown, reused
)

pytestmark = [pytest.mark.harness]

LEG = "claude-agent"
FILE_OPTION = "--system-prompt-file"


def _adapter() -> Any:
    harness_unavailable("claude_agent_sdk", LEG)
    from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

    values = _harness_fixture()[LEG]
    built = ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects="governed",
    )
    CLAUDE_ADAPTERS_BUILT.append(built)
    return built


def _argv(adapter: Any, carrier: Any) -> list[str]:
    """The argv the vendor would spawn ``claude`` with, built and not run."""
    transport = adapter.transport(carrier)
    transport._cli_path = "/nonexistent/ccf-tp05/claude"
    argv: list[str] = transport._build_command()
    return argv


def test_the_assembled_system_prompt_is_not_on_the_claude_argv() -> None:
    """TP-05 as worded: the prompt reaches the CLI by a 0600 file, not argv."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    product = world.agent_a.consume(_product(world.definition_a), now=BOUNDARY)
    instructions = world.instructions()
    serialized = canonical_bytes(product).decode("utf-8")
    assembled = "\n".join((*instructions, serialized))
    adapter = _adapter()

    carrier = adapter.inject_context(
        agent=world.agent_a, products=(product,), instructions=instructions
    )
    argv = _argv(adapter, carrier)

    on_argv = [
        index
        for index, token in enumerate(argv)
        if instructions[0] in token or serialized in token
    ]
    assert on_argv == [], (
        f"the assembled system prompt is on the claude argv at positions"
        f" {on_argv} (TP-05)"
    )
    assert not isinstance(carrier.system_prompt, str), (
        "the carrier holds the assembled prompt as a string, which the vendor"
        " places on argv as --system-prompt (TP-05)"
    )

    assert argv.count(FILE_OPTION) == 1, f"{FILE_OPTION} is not on argv exactly once"
    prompt_file = Path(argv[argv.index(FILE_OPTION) + 1])
    assert prompt_file.is_absolute() and prompt_file.is_file()
    assert stat.S_IMODE(prompt_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(prompt_file.parent.stat().st_mode) == 0o700
    assert prompt_file.read_bytes() == assembled.encode("utf-8")
    assert str(prompt_file.parent) in adapter.prompt_directories, (
        "the per-call prompt directory is not recorded on the adapter for the"
        " adopter to remove"
    )


def test_each_inject_context_call_gets_its_own_prompt_directory() -> None:
    """Two carriers never share (and so never overwrite) one prompt file."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    adapter = _adapter()
    first = _argv(
        adapter,
        adapter.inject_context(
            agent=world.agent_a, products=(), instructions=world.instructions()
        ),
    )
    second = _argv(
        adapter,
        adapter.inject_context(agent=world.agent_a, products=(), instructions=()),
    )
    first_file = Path(first[first.index(FILE_OPTION) + 1])
    second_file = Path(second[second.index(FILE_OPTION) + 1])
    assert first_file.parent != second_file.parent
    assert first_file.read_bytes() == world.instructions()[0].encode("utf-8")
    assert second_file.read_bytes() == b""
    assert {str(first_file.parent), str(second_file.parent)} <= set(
        adapter.prompt_directories
    )


def test_remove_prompt_directories_removes_every_recorded_directory() -> None:
    """The adopter's removal helper leaves no prompt payload at rest (TP-05)."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    product = world.agent_a.consume(_product(world.definition_a), now=BOUNDARY)
    adapter = _adapter()
    for _ in range(2):
        adapter.inject_context(
            agent=world.agent_a, products=(product,), instructions=world.instructions()
        )
    recorded = adapter.prompt_directories
    assert len(recorded) == 2 and all(Path(path).is_dir() for path in recorded)

    adapter.remove_prompt_directories()

    assert adapter.prompt_directories == ()
    assert not any(Path(path).exists() for path in recorded)
    adapter.remove_prompt_directories()  # idempotent
