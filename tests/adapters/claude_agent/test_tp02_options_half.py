"""TP-02's options half — the carrier isolates the CLI from host settings (I-4, D-IMPL-361).

The whole-branch review's I-4: spec §7.1 fact (d) lists TP-02's options half
(``tools=[]``, ``setting_sources=[]``, ``strict_mcp_config=True``, ``cwd``,
``max_turns``) and the carrier set none of them. Measured in claude-agent-sdk
0.2.128 (``_internal/transport/subprocess_cli.py``):

* ``tools=None`` emits no ``--tools`` (lines 478-488), so the CLI keeps its
  default built-in tool set (Bash, the file tools); ``tools=[]`` emits
  ``--tools ""`` (lines 482-483), "disable all built-in tools"
  (``types.py`` ``ClaudeAgentOptions.tools``).
* ``setting_sources=None`` emits no ``--setting-sources`` (lines 599-600), so
  the CLI loads every filesystem settings source — the default allowlist
  passes ``HOME``, so ``~/.claude/settings.json`` (allow-rules, hooks, MCP
  servers) would apply; ``[]`` emits ``--setting-sources=`` (SDK isolation mode).
* ``strict_mcp_config=True`` emits ``--strict-mcp-config`` (lines 587-588):
  only the carrier's ``mcp_servers`` are used.
* ``cwd`` becomes the child's working directory (lines 135, 727-728, 738);
  ``None`` is the fabric's own working directory.
* ``max_turns`` emits ``--max-turns`` only when truthy (lines 497-498).

The controller's ruling: the three isolation options are set unconditionally;
``cwd`` is the per-call ``0700`` directory unless the adopter declares one on
the adapter; ``max_turns`` is declared on the constructor (``None`` = the
vendor default) and is a budget, not a boundary. Offline: argv is built, not run.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import pytest

from conftest import harness_unavailable
from conformance.test_harness_adapter import (
    World,
    _harness_fixture,
    CLAUDE_ADAPTERS_BUILT,
    no_model_reachable,  # noqa: F401 - autouse socket guard, reused not copied
    remove_claude_prompt_directories,  # noqa: F401 - autouse teardown, reused
)

pytestmark = [pytest.mark.harness]

LEG = "claude-agent"


def _carrier(**kwargs: Any) -> tuple[Any, Any]:
    harness_unavailable("claude_agent_sdk", LEG)
    from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

    values = _harness_fixture()[LEG]
    adapter = ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects="governed",
        **kwargs,
    )
    CLAUDE_ADAPTERS_BUILT.append(adapter)
    world = World()
    world.bind(world.grant_a, world.definition_a)
    return adapter, adapter.inject_context(
        agent=world.agent_a, products=(), instructions=()
    )


def _argv(adapter: Any, carrier: Any) -> list[str]:
    transport = adapter.transport(carrier)
    transport._cli_path = "/nonexistent/ccf-tp02-options/claude"
    argv: list[str] = transport._build_command()
    return argv


def test_the_carrier_disables_built_in_tools_host_settings_and_foreign_mcp() -> None:
    """The three isolation options, on the carrier and on the argv they produce."""
    adapter, carrier = _carrier()

    assert carrier.tools == [], f"built-in tools not disabled: {carrier.tools!r} (I-4)"
    assert carrier.setting_sources == [], (
        f"host settings sources not disabled: {carrier.setting_sources!r} (I-4)"
    )
    assert carrier.strict_mcp_config is True, "foreign MCP config not excluded (I-4)"
    argv = _argv(adapter, carrier)
    assert argv[argv.index("--tools") + 1] == ""
    assert "--setting-sources=" in argv
    assert "--strict-mcp-config" in argv


def test_the_child_works_in_the_per_call_owner_only_directory() -> None:
    """``cwd`` defaults to the per-call ``0700`` directory, not the fabric's own."""
    _, carrier = _carrier()

    working = Path(str(carrier.cwd)) if carrier.cwd else None

    assert working is not None and working != Path(os.getcwd()), (
        f"the child would run in {carrier.cwd!r}, not a per-call directory (I-4)"
    )
    assert working == Path(carrier.system_prompt["path"]).parent
    assert stat.S_IMODE(os.lstat(working).st_mode) == 0o700


def test_a_declared_cwd_and_max_turns_reach_the_carrier(tmp_path: Path) -> None:
    """The adopter's declarations, verbatim; ``max_turns`` reaches the argv."""
    adapter, carrier = _carrier(cwd=tmp_path, max_turns=3)

    assert Path(str(carrier.cwd)) == tmp_path
    assert carrier.max_turns == 3
    argv = _argv(adapter, carrier)
    assert argv[argv.index("--max-turns") + 1] == "3"


def test_an_undeclared_max_turns_is_the_vendor_default() -> None:
    """``None`` emits no ``--max-turns``: a budget the adopter declares, never a default."""
    adapter, carrier = _carrier(max_turns=None)

    assert carrier.max_turns is None
    assert "--max-turns" not in _argv(adapter, carrier)
