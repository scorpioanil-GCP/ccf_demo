"""TP-02's fail-closed sentinel and TP-05's prompt file cannot be planted (I-3, D-IMPL-361).

The whole-branch review's I-3: the carrier's ``cli_path`` sentinel lived inside
the per-call ``tempfile.mkdtemp()`` directory, whose name every child publishes
on its argv (``--system-prompt-file /tmp/tmpXXXX/system-prompt``). After
``remove_prompt_directories()`` that name is free in a world-writable sticky
directory, so a co-tenant could recreate it and plant (a) an executable at the
sentinel name — which the vendor's DEFAULT transport would then run with the
fabric's whole environment — and (b) a ``system-prompt`` the adapter's own
transport would hand the CLI.

The controller's ruling: the sentinel is a path BELOW ``os.devnull``, which can
never resolve to a file on any POSIX system (a character device has no
children), and ``adapter.transport(carrier)`` verifies, before connecting, that
the prompt file is a regular file owned by the effective uid with mode ``0600``
in a directory owned by the effective uid with mode ``0700``, refusing with a
typed error otherwise. Offline: nothing is spawned.
"""

from __future__ import annotations

import os
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


def _adapter_and_carrier() -> tuple[Any, Any]:
    harness_unavailable("claude_agent_sdk", LEG)
    from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

    values = _harness_fixture()[LEG]
    adapter = ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects="governed",
    )
    CLAUDE_ADAPTERS_BUILT.append(adapter)
    world = World()
    world.bind(world.grant_a, world.definition_a)
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    return adapter, carrier


def _prompt_file(carrier: Any) -> Path:
    return Path(carrier.system_prompt["path"])


def test_the_sentinel_is_below_os_devnull() -> None:
    """(a) The sentinel can never exist: its parent is the null device."""
    _, carrier = _adapter_and_carrier()

    sentinel = Path(str(carrier.cli_path))

    assert Path(os.devnull) in sentinel.parents, (
        f"the fail-closed cli_path {str(sentinel)!r} is not below {os.devnull!r};"
        " a path under a removable directory can be recreated and planted (I-3)"
    )


def test_recreating_the_removed_prompt_directory_cannot_plant_the_sentinel() -> None:
    """(a) The attack as the review worded it: recreate the freed directory, plant the name."""
    adapter, carrier = _adapter_and_carrier()
    prompt_directory = _prompt_file(carrier).parent
    # No sentinel at all is the TP-02 hole itself; never plant relative to cwd.
    assert carrier.cli_path is not None, "the carrier has no fail-closed cli_path (TP-02)"
    sentinel = Path(str(carrier.cli_path))
    assert sentinel.is_absolute(), sentinel

    adapter.remove_prompt_directories()
    assert not prompt_directory.exists()
    # What a co-tenant does with the name it read from ``ps``.
    os.makedirs(prompt_directory, exist_ok=True)
    try:
        try:
            os.makedirs(sentinel.parent, exist_ok=True)
            sentinel.write_bytes(b"#!/bin/sh\n")
        except OSError:
            pass
        assert not sentinel.exists(), (
            f"the sentinel {str(sentinel)!r} was planted after"
            " remove_prompt_directories(); the vendor's default transport would"
            " now execute it with the fabric's whole environment (I-3)"
        )
    finally:
        for leftover in sorted(prompt_directory.rglob("*"), reverse=True):
            leftover.unlink() if leftover.is_file() else leftover.rmdir()
        prompt_directory.rmdir()


def _assert_transport_refuses(adapter: Any, carrier: Any, why: str) -> None:
    """The transport refuses the carrier, with the typed error naming the ruling."""
    try:
        adapter.transport(carrier)
    except Exception as raised:  # noqa: BLE001 - the type is asserted below
        assert type(raised).__name__ == "PromptFileRefused", repr(raised)
        assert "D-IMPL-361" in str(raised), why
    else:
        pytest.fail(
            f"adapter.transport(carrier) admitted a carrier with a {why}; the CLI"
            " would read a prompt someone else could have authored (I-3)"
        )


def test_the_transport_refuses_a_prompt_file_wider_than_0600() -> None:
    """(b) A prompt file another user could read or write is refused."""
    adapter, carrier = _adapter_and_carrier()
    os.chmod(_prompt_file(carrier), 0o644)

    _assert_transport_refuses(adapter, carrier, "mode 0644 prompt file")


def test_the_transport_refuses_a_prompt_directory_wider_than_0700() -> None:
    """(b) A prompt directory others can enter or write is refused."""
    adapter, carrier = _adapter_and_carrier()
    os.chmod(_prompt_file(carrier).parent, 0o755)

    _assert_transport_refuses(adapter, carrier, "mode 0755 prompt directory")


def test_the_transport_refuses_a_removed_prompt_file() -> None:
    """(b) After ``remove_prompt_directories()`` the carrier cannot start a session."""
    adapter, carrier = _adapter_and_carrier()
    adapter.remove_prompt_directories()

    _assert_transport_refuses(adapter, carrier, "removed prompt file")


def test_the_transport_refuses_a_symlinked_prompt_file() -> None:
    """(b) A symlink at the prompt path is not a regular file, whatever it points at."""
    adapter, carrier = _adapter_and_carrier()
    prompt = _prompt_file(carrier)
    target = prompt.with_name("planted")
    prompt.rename(target)
    prompt.symlink_to(target)

    _assert_transport_refuses(adapter, carrier, "symlinked prompt file")


def test_the_transport_refuses_a_prompt_file_not_owned_by_the_effective_uid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(b) Ownership, SIMULATED: ``chown`` to another uid needs root, which this suite
    does not have, so the effective uid the adapter compares against is moved
    instead. The file and directory are then owned by "someone else" from the
    adapter's point of view, which is the comparison under test."""
    adapter, carrier = _adapter_and_carrier()
    real = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: real + 1)

    _assert_transport_refuses(adapter, carrier, "foreign owner")


def test_the_control_a_fresh_carrier_is_admitted() -> None:
    """The positive control: the carrier ``inject_context`` just built is admitted."""
    adapter, carrier = _adapter_and_carrier()

    transport = adapter.transport(carrier)

    assert transport is not None
