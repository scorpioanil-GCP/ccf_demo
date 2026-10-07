"""PC2 (panel C2): ``invoke_agent`` gives a rostered caller no existence oracle (SEC-017; `D-IMPL-374`).

The cross-AI panel measured it (probe ``probe_b5_invoke_oracle.py``). For a
caller whose grant declares a product roster, ``invoke_agent``'s reach is read
from the deployment's agent directory BEFORE the authorizer (fix round 1), and
every directory outcome — an agent missing, off the roster, or unresolvable —
refuses with ONE opaque reason (fix round 2, I-NEW-1). But an agent that EXISTS
and is ON the roster passed that hold and reached the authorizer, whose deny
said ``tenant-unauthorized``. A rostered principal WITHOUT invoke permission
could therefore probe ``key@version`` guesses and learn which agents exist and
are on its roster: the opaque refusal held for three outcomes and not the
fourth (and the five were byte-identical only transitively).

Ruled: for a rostered caller on ``invoke_agent`` the authorizer's denial renders
as the SAME opaque pre-authorization refusal, byte-identical, the specific
reason logged server-side only; the unrostered path is unchanged. The one test
below compares EVERY outcome with every other, pairwise — no transitive
reasoning.
"""

from __future__ import annotations

import itertools
import pathlib
from typing import Any

from ccf.authz.actions import ACTION_WORKFLOW_INVOKE
from tests.mcp.guarded_servers import (
    ALL_ACTIONS,
    _auth,
    _entitlement_world,
    _perspective,
    _verifier,
    authorizer_granting,
)
from tests.mcp.test_product_roster import (
    AGENT_OFF,
    AGENT_ON,
    OFF_ROSTER,
    ON_ROSTER,
    _agent,
    _as_caller,
    _invoke_args,
)

#: Every action the doors declare except the one invoke_agent decides on.
WITHOUT_INVOKE = tuple(action for action in ALL_ACTIONS if action != ACTION_WORKFLOW_INVOKE)


def _server(tmp_path: pathlib.Path, *, directory: Any, actions: tuple[str, ...] = WITHOUT_INVOKE) -> Any:
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL, build_experience_server

    source, recorder = _entitlement_world(tmp_path)
    arguments: dict[str, Any] = dict(
        server_name="pc2-oracle",
        product_resolver=lambda **kw: None,
        agent_invoker=lambda **kw: "{}",
        invoke_agent_description="pc2 fixture",
        tool_allowlist=frozenset({INVOKE_AGENT_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(actions=actions),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )
    if directory is not None:
        arguments["agent_directory"] = directory
    return build_experience_server(**arguments)


def _refusal_text(server: Any, roster: frozenset[str] | None, key: str) -> tuple[str, str]:
    """``(type name, text)`` of what the caller receives — the whole of what crosses."""
    import anyio
    from mcp.server.auth.middleware.auth_context import auth_context_var

    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL

    reset = _as_caller(roster)
    try:
        try:
            anyio.run(server.call_tool, INVOKE_AGENT_TOOL, _invoke_args(key))
        except Exception as raised:  # noqa: BLE001 - the outcome is the subject
            return type(raised).__name__, str(raised)
    finally:
        auth_context_var.reset(reset)
    raise AssertionError(f"invoke_agent served {key!r} to a caller without invoke permission")


def _undeclared() -> Any:
    from ccf_runtime.mcp.experience import ExposedAgent

    return ExposedAgent(
        definition_key="agent-undeclared", definition_version="1.0.0", name="agent-undeclared",
        artifact_version="1.0.0", archetypes=("analytics_insights",), skills=(),
    )


def _failing_directory(*, tenant: str) -> Any:
    raise RuntimeError("the deployment's directory failed")


def test_pc2_every_rostered_invoke_refusal_is_byte_identical_pairwise(tmp_path: pathlib.Path, caplog: Any) -> None:
    caplog.set_level("INFO", logger="ccf_runtime.mcp.tenancy")
    agents = (_agent(AGENT_ON, frozenset({ON_ROSTER})), _agent(AGENT_OFF, frozenset({ON_ROSTER, OFF_ROSTER})), _undeclared())
    listed = _server(tmp_path / "listed", directory=lambda *, tenant: agents)
    roster = frozenset({ON_ROSTER})
    outcomes = {
        "on-roster-and-existing-but-unauthorized": _refusal_text(listed, roster, AGENT_ON),
        "off-roster": _refusal_text(listed, roster, AGENT_OFF),
        "absent": _refusal_text(listed, roster, "agent-absent"),
        "no-derived-classes": _refusal_text(listed, roster, "agent-undeclared"),
        "directory-failed": _refusal_text(_server(tmp_path / "failing", directory=_failing_directory), roster, AGENT_ON),
        "no-directory": _refusal_text(_server(tmp_path / "none", directory=None), roster, AGENT_ON),
    }
    for (left, left_text), (right, right_text) in itertools.combinations(outcomes.items(), 2):
        assert left_text == right_text, (
            f"a rostered caller can tell {left!r} from {right!r}:\n  {left_text}\n  {right_text}"
        )
    # The specific reason for the existing, on-roster agent reaches the log only.
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "authoriz" in logged.lower() and AGENT_ON in logged, logged


def test_pc2_control_the_unrostered_caller_still_reads_tenant_unauthorized(tmp_path: pathlib.Path) -> None:
    agents = (_agent(AGENT_ON, frozenset({ON_ROSTER})),)
    server = _server(tmp_path, directory=lambda *, tenant: agents)
    kind, text = _refusal_text(server, None, AGENT_ON)
    assert "tenant-unauthorized" in text, text
