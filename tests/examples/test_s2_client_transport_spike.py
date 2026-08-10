"""The two new Section-2 client legs, driven against a real MCP server (16-03).

**This module is a spike, and plan 16-09 retires it.** It exists because
`16-RESEARCH.md` FINDING F-2 measured the tree and found no LangGraph client leg
anywhere in it, and only a near analog for the Claude Agent SDK
(`client_anthropic.py` drives the raw `anthropic` SDK, which is a different
harness binding). Risk R-4's mitigation was to spike both legs early, against
the **existing** `examples/external/00-hello-context` server, so a transport
surprise surfaces in wave 2 rather than in wave 4. What it proves that a later
assertion would not: that these two legs reach a Context Product over MCP
*before* the Section-2 fabric they will eventually be pointed at exists. Once
16-09 stands that fabric up and its `run.py` drives all four legs, this module's
live drive is redundant and should be deleted with it.

Read-only against `examples/external/00-hello-context/`. Those files are the
shipped external example; `tests/examples/test_ext00_hardening.py` and
`docs/SURFACE-AUDIT.md` §2.3 rest on their client legs being byte-unchanged, so
this module spawns that server and reads those artifacts without writing one
byte into that tree — and asserts as much.

Determinism and keys
--------------------

Both legs run keyless and offline:

* `client_langgraph.py` reaches no model at all, so pointing it at the server is
  the whole of its configuration.
* `client_claude_agent.py` drives the Claude Code CLI that `claude-agent-sdk`
  bundles, and the CLI is what connects to the MCP server and what reaches the
  model API. It is determinized the way `client_anthropic.py` is — by
  `ANTHROPIC_BASE_URL` — pointed at the scripted Anthropic-shaped stand-in
  below. The stand-in is **scripted, not captured**: this is a spike, and
  capturing reviewed fixtures is 16-09's task. See
  `docs/surface/examples/SECTION-2-TRANSPORT.md`.

Neither leg carries a CI/live branch, and no key value appears in either.
"""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import uvicorn
import yaml
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from tools.lints import imported_module_names, submodule_import_names

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LEG_DIR = REPO_ROOT / "examples" / "s2-01-external-consumers"
LANGGRAPH_LEG = LEG_DIR / "client_langgraph.py"
CLAUDE_LEG = LEG_DIR / "client_claude_agent.py"
EXT00_DIR = REPO_ROOT / "examples" / "external" / "00-hello-context"

#: The MCP namespace the Claude Agent SDK session binds the CCF door under.
#: A test-harness value: it names nothing in the fabric, only the prefix the
#: harness composes into `mcp__{server}__{tool}`.
MCP_SERVER_NAME = "ccf"

#: Bound on the whole Claude leg, whose transport is a CLI subprocess. Finite
#: so a stalled CLI fails the build with a diagnostic rather than hanging it.
LEG_TIMEOUT_SECONDS = 300.0

#: Bound on the wait for the in-thread stand-in to bind. Same discipline as
#: `run.py`'s `READY_TIMEOUT_SECONDS`: generous for a loaded runner, finite so
#: a server that never binds fails the build instead of hanging it.
READY_TIMEOUT_SECONDS = 60.0


# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# --------------------------------------------------------------------------


def test_both_leg_files_exist() -> None:
    """Without this, a rename turns every assertion below green over nothing."""
    assert LANGGRAPH_LEG.is_file(), f"missing leg: {LANGGRAPH_LEG}"
    assert CLAUDE_LEG.is_file(), f"missing leg: {CLAUDE_LEG}"


def test_the_spiked_against_example_is_present() -> None:
    """The server this spike is driven against is the shipped external one."""
    assert (EXT00_DIR / "serve.py").is_file(), f"missing server: {EXT00_DIR}"
    assert (EXT00_DIR / "run.py").is_file(), f"missing harness: {EXT00_DIR}"


# --------------------------------------------------------------------------
# The zero-CCF guard, over the shared lint helpers rather than a fresh regex.
# --------------------------------------------------------------------------

#: Roots a client leg may not reach, in any spelling.
FORBIDDEN_ROOTS = ("ccf", "ccf_runtime")

#: Callables that import by name at runtime, which an AST walk over
#: `Import`/`ImportFrom` nodes alone cannot see. `tests/agents/
#: test_consumption_discipline.py`'s local `_ccf_imports` misses these and
#: inherits the Phase 15.4 CR-02 hole besides; this module widens on both axes
#: and the parametrized negative control below proves each widening.
DYNAMIC_IMPORTERS = ("import_module", "__import__")


def _is_forbidden(name: str) -> bool:
    """Whether a dotted module name is rooted at a forbidden package."""
    return name.split(".", 1)[0] in FORBIDDEN_ROOTS


def _dynamic_import_argument(node: ast.Call) -> str | None:
    """The literal module name a dynamic-import call names, if it names one."""
    function = node.func
    if isinstance(function, ast.Attribute):
        called = function.attr
    elif isinstance(function, ast.Name):
        called = function.id
    else:  # pragma: no cover - defensive
        return None
    if called not in DYNAMIC_IMPORTERS or not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def ccf_imports(source: str) -> list[str]:
    """Every CCF-rooted module name a source file reaches, statically.

    Static import statements are resolved with `tools/lints/__init__.py`'s own
    helpers — `imported_module_names` for what an `Import`/`ImportFrom` binds,
    and `submodule_import_names` for the `from ccf.graph import _writer`
    spelling the former reports only as `ccf.graph` (review finding CR-02).
    Their union is what the lint package's deny loops read, so this guard and
    the shipped invariant lints agree by construction rather than by
    coincidence.

    Dynamic imports are added on top, because `importlib.import_module("ccf")`
    binds the package just as surely and is invisible to both helpers.

    The walk is unindented-agnostic: `ast.walk` reaches an import nested inside
    a function or a `try` exactly as it reaches a top-level one, which the
    `^(import|from) (ccf|ccf_runtime)` regex the shipped example uses does not.
    """
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            reached = set(imported_module_names(node)) | set(
                submodule_import_names(node)
            )
            found.extend(name for name in sorted(reached) if _is_forbidden(name))
        elif isinstance(node, ast.Call):
            named = _dynamic_import_argument(node)
            if named is not None and _is_forbidden(named):
                found.append(named)
    return sorted(set(found))


def assert_zero_ccf_imports(legs: tuple[pathlib.Path, ...]) -> None:
    """Refuse any leg reaching `ccf` or `ccf_runtime`, naming the offenders."""
    offenders = {
        leg.name: reached
        for leg in legs
        if (reached := ccf_imports(leg.read_text(encoding="utf-8")))
    }
    if offenders:
        raise AssertionError(f"CCF imports found in client legs: {offenders}")


def test_the_committed_legs_import_no_ccf() -> None:
    """The Section-2 charter, over the two shipped legs (D-06, criterion 3)."""
    assert_zero_ccf_imports((LANGGRAPH_LEG, CLAUDE_LEG))


@pytest.mark.parametrize(
    "injected",
    [
        pytest.param("from ccf.boot import boot\n", id="from-ccf-submodule"),
        pytest.param("import ccf_runtime\n", id="import-ccf-runtime"),
        pytest.param(
            'import importlib\nimportlib.import_module("ccf")\n', id="dynamic-import"
        ),
        pytest.param(
            "def _late() -> None:\n    from ccf.graph import _writer\n",
            id="indented-submodule-import",
        ),
    ],
)
@pytest.mark.parametrize("leg", [LANGGRAPH_LEG, CLAUDE_LEG], ids=lambda p: p.stem)
def test_the_zero_import_guard_refuses_each_spelling(
    tmp_path: pathlib.Path, injected: str, leg: pathlib.Path
) -> None:
    """The guard is verified to REFUSE, not merely to pass.

    A widened matcher with an unwidened control is a widening nobody proved, so
    all four spellings are driven — including the two the shipped example's
    line-anchored regex would miss (`importlib.import_module`, and an import
    indented inside a function). The legs are copied to `tmp_path` and the real
    guard runs over the copies, so the function under test is the real one.
    """
    for source in (LANGGRAPH_LEG, CLAUDE_LEG):
        shutil.copy(source, tmp_path / source.name)
    copies = tuple(sorted(tmp_path.glob("client_*.py")))
    assert len(copies) == 2

    # The copies alone still pass — so the failure below is the injection.
    assert_zero_ccf_imports(copies)

    target = tmp_path / leg.name
    target.write_text(injected + target.read_text(encoding="utf-8"), "utf-8")
    with pytest.raises(AssertionError) as excinfo:
        assert_zero_ccf_imports(copies)
    assert leg.name in str(excinfo.value)


# --------------------------------------------------------------------------
# The deployment values, read straight off the shipped example's artifacts.
# --------------------------------------------------------------------------


def _declaration(name: str) -> dict[str, Any]:
    document = yaml.safe_load(
        (EXT00_DIR / "artifacts" / f"{name}.yaml").read_text(encoding="utf-8")
    )
    return dict(document["declaration"])


@pytest.fixture(scope="module")
def deployment_values() -> dict[str, str]:
    """Tenant, entity and the active bearer token, from the example's own YAML.

    Read rather than recomputed: booting a replica here would double this
    module's runtime to learn three strings the artifacts already state.
    """
    manifest = yaml.safe_load(
        (EXT00_DIR / "artifacts" / "manifest.yaml").read_text(encoding="utf-8")
    )
    tokens = _declaration("tokens")["tokens"]
    active = next(entry for entry in tokens if entry["status"] == "active")
    return {
        "tenant": str(manifest["tenant_id"]),
        "entity": str(_declaration("focus")["entity_ref"]),
        "token": str(active["token"]),
    }


# --------------------------------------------------------------------------
# The live server, spawned through the shipped harness's own READY handshake.
# --------------------------------------------------------------------------


def _load_run_module() -> Any:
    """Load the shipped example's `run.py` by path (the dir is no package).

    Follows `tests/examples/test_ext00_serve_output.py`: the module is
    registered in `sys.modules` before `exec_module` because the example
    modules defer their annotations. Loaded for its `_spawn`/`_terminate`
    only, so the READY handshake and the kill-fallback teardown exercised here
    are the harness's real ones rather than a copy that can drift from them.
    """
    spec = importlib.util.spec_from_file_location(
        "s2_spike_ext00_run", EXT00_DIR / "run.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["s2_spike_ext00_run"] = module
    if str(EXT00_DIR) not in sys.path:
        sys.path.insert(0, str(EXT00_DIR))
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mcp_url() -> Iterator[str]:
    """One `serve.py` for the whole module, torn down with a kill fallback."""
    run_module = _load_run_module()
    with tempfile.TemporaryDirectory(prefix="ccf-s2-spike-") as scratch:
        proc, port = run_module._spawn("serve.py", pathlib.Path(scratch))
        try:
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            run_module._terminate(proc)


# --------------------------------------------------------------------------
# The scripted Anthropic-shaped stand-in the bundled CLI is pointed at.
# --------------------------------------------------------------------------


def _sse(blocks: tuple[dict[str, Any], ...], stop_reason: str) -> str:
    """One Messages-API streaming response, as server-sent events.

    The CLI always sends `"stream": true`, so a JSON body is not an acceptable
    answer — which is the single most consequential difference between this
    stand-in and the shipped `replay_server.py`, and why 16-09 cannot reuse
    that file unchanged for this leg.
    """
    frames: list[tuple[str, dict[str, Any]]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_spike",
                    "type": "message",
                    "role": "assistant",
                    "model": "spike-model",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
            },
        )
    ]
    for index, block in enumerate(blocks):
        if block["type"] == "text":
            frames.append(
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": index,
                        "content_block": {"type": "text", "text": ""},
                    },
                )
            )
            frames.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "text_delta", "text": block["text"]},
                    },
                )
            )
        else:
            frames.append(
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": index,
                        "content_block": {
                            "type": "tool_use",
                            "id": block["id"],
                            "name": block["name"],
                            "input": {},
                        },
                    },
                )
            )
            frames.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": json.dumps(block["input"]),
                        },
                    },
                )
            )
        frames.append(
            ("content_block_stop", {"type": "content_block_stop", "index": index})
        )
    frames.append(
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
        )
    )
    frames.append(("message_stop", {"type": "message_stop"}))
    return "".join(
        f"event: {event}\ndata: {json.dumps(data)}\n\n" for event, data in frames
    )


def _scripted_app(values: dict[str, str], seen: list[dict[str, Any]]) -> Starlette:
    """A Messages-API stand-in that calls `get_context` once, then stops.

    Scripted rather than captured, deliberately: this is a spike, and the
    reviewed-fixture capture is 16-09's task. The script is one decision — if
    the request advertises a `get_context` tool and no tool result has come
    back yet, call it with the deployment's own tenant and entity; otherwise
    answer with text — so what it proves is exactly that the harness carried a
    CCF tool call to the CCF server and carried the answer back.
    """

    async def messages(request: Request) -> Response:
        body = await request.json()
        tools = sorted(
            str(tool.get("name", "")) for tool in (body.get("tools") or [])
        )
        history = body.get("messages") or []
        seen.append({"tools": tools, "messages": len(history)})

        target = next((name for name in tools if name.endswith("get_context")), None)
        answered = any(
            isinstance(block, dict) and block.get("type") == "tool_result"
            for message in history
            for block in (
                message.get("content")
                if isinstance(message.get("content"), list)
                else []
            )
        )
        if target is not None and not answered:
            blocks = (
                {
                    "type": "tool_use",
                    "id": "toolu_spike_1",
                    "name": target,
                    "input": {
                        "tenant": values["tenant"],
                        "entity": values["entity"],
                    },
                },
            )
            stop_reason = "tool_use"
        else:
            blocks = ({"type": "text", "text": "spike-complete"},)
            stop_reason = "end_turn"

        return StreamingResponse(
            iter([_sse(blocks, stop_reason).encode("utf-8")]),
            media_type="text/event-stream",
        )

    async def unrouted(request: Request) -> Response:
        # The CLI probes its base URL before it talks to it. Answered rather
        # than crashed on, and recorded so the transport note can say so.
        seen.append({"unrouted": f"{request.method} {request.url.path}"})
        return JSONResponse({"error": "unrouted"}, status_code=404)

    return Starlette(
        routes=[
            Route("/v1/messages", messages, methods=["POST"]),
            Route(
                "/{rest:path}",
                unrouted,
                methods=["GET", "HEAD", "POST", "PUT", "DELETE"],
            ),
        ]
    )


@pytest.fixture(scope="module")
def scripted_model(deployment_values: dict[str, str]) -> Iterator[tuple[str, list]]:
    """Host the stand-in on loopback for the life of the module."""
    seen: list[dict[str, Any]] = []
    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(_scripted_app(deployment_values, seen), log_level="error")
    )
    thread = threading.Thread(
        target=lambda: server.run(sockets=[bound]), daemon=True
    )
    thread.start()
    try:
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while not server.started:
            assert time.monotonic() < deadline, "the scripted model never started"
            time.sleep(0.01)
        yield f"http://127.0.0.1:{port}", seen
    finally:
        server.should_exit = True
        thread.join(timeout=30)
        with contextlib.suppress(OSError):
            bound.close()


def _run_leg(
    leg: pathlib.Path, *, env: dict[str, str], arguments: tuple[str, ...] = ()
) -> str:
    """Run one client leg as a subprocess and return its stdout."""
    completed = subprocess.run(
        [sys.executable, str(leg), *arguments],
        env=env,
        capture_output=True,
        text=True,
        timeout=LEG_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, (
        f"{leg.name} exited {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    return completed.stdout


def _labelled(stdout: str) -> dict[str, str]:
    """Parse the legs' shared `[label] body` stdout contract."""
    received: dict[str, str] = {}
    for line in stdout.splitlines():
        if line.startswith("[") and "] " in line:
            label, _, body = line[1:].partition("] ")
            received[label] = body
    return received


def _assert_is_a_context_product(body: str, values: dict[str, str]) -> None:
    """The parsed document is a Context Product for this deployment.

    Parsed and field-checked rather than grepped: a truncated or
    differently-shaped document satisfies a substring search and would leave
    the spike claiming a transport works when it delivered nothing usable.
    """
    document = json.loads(body)
    assert document["tenant_id"] == values["tenant"], document.get("tenant_id")
    assert document["schema_name"], document
    assert document["lineage"]["operators_invoked"], document["lineage"]
    assert document["payload"]["entity_count"] > 0, document["payload"]


# --------------------------------------------------------------------------
# The live drives — both legs, against the running server.
# --------------------------------------------------------------------------


def test_the_langgraph_leg_reads_a_context_product_over_mcp(
    mcp_url: str, deployment_values: dict[str, str]
) -> None:
    """A LangGraph node drives an MCP session and gets the typed product back.

    RESEARCH F-2's NO-ANALOG gap, closed against a real server: no fixture, no
    model, no new dependency — the node opens the session, binds the server's
    advertised tools as LangChain tools, and calls them.
    """
    stdout = _run_leg(
        LANGGRAPH_LEG,
        env={
            **os.environ,
            "CCF_MCP_URL": mcp_url,
            "CCF_TOKEN": deployment_values["token"],
        },
        arguments=(
            f"tenant={deployment_values['tenant']}",
            f"entity={deployment_values['entity']}",
        ),
    )
    received = _labelled(stdout)
    assert "get_context" in received, sorted(received)
    _assert_is_a_context_product(received["get_context"], deployment_values)


@pytest.fixture(scope="module")
def claude_leg_run(
    mcp_url: str,
    deployment_values: dict[str, str],
    scripted_model: tuple[str, list],
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """One drive of the Claude leg, and everything both tests read off it.

    A fixture rather than a first test whose successor reads its leftovers:
    the tool-surface assertion below is about the same run as the product
    assertion, and either test selected alone must still drive it. One spawn
    for the module; the CLI's whole conversation is loopback.
    """
    base_url, seen = scripted_model
    home = tmp_path_factory.mktemp("claude-home")
    stdout = _run_leg(
        CLAUDE_LEG,
        env={
            **os.environ,
            "CCF_MCP_URL": mcp_url,
            "CCF_TOKEN": deployment_values["token"],
            "CCF_EXAMPLE_SERVER": MCP_SERVER_NAME,
            "CCF_EXAMPLE_MODEL": "spike-model",
            "CCF_EXAMPLE_QUESTION": (
                "Retrieve the governed context with the available tools."
            ),
            # The determinism seam: the bundled CLI's model API, redirected.
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_AUTH_TOKEN": "spike",
            # Keep the CLI's state, telemetry and updater out of the run.
            "HOME": str(home),
            "CLAUDE_CONFIG_DIR": str(home / "config"),
            "CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK": "1",
            "DISABLE_TELEMETRY": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
        },
    )
    return _labelled(stdout), seen


def test_the_claude_agent_leg_reads_a_context_product_over_mcp(
    claude_leg_run: tuple[dict[str, str], list[dict[str, Any]]],
    deployment_values: dict[str, str],
) -> None:
    """A Claude Agent SDK session binds the CCF door and gets the product back.

    The Context Product asserted on here arrived as a `ToolResultBlock` on the
    harness's own message stream — the harness connected to the MCP server,
    called `get_context`, and carried the answer back into the model's context.
    The leg never fetched it itself.

    The tool result is the MCP call's own envelope (`{"result": "<document>"}`),
    so the product is unwrapped once before it is checked.
    """
    received, _ = claude_leg_run
    assert "result" in received, sorted(received)
    product = next(
        (body for label, body in received.items() if label.endswith("get_context")),
        None,
    )
    assert product is not None, sorted(received)
    _assert_is_a_context_product(json.loads(product)["result"], deployment_values)


def test_the_claude_agent_leg_saw_only_ccf_tools(
    claude_leg_run: tuple[dict[str, str], list[dict[str, Any]]],
) -> None:
    """The harness's whole tool surface was the CCF door's own tools.

    Recorded on the model side, which is the only place it is observable: what
    reached the model is what the harness would have let it call. `tools=[]`,
    `skills=[]`, `setting_sources=[]` and `strict_mcp_config=True` on the leg
    are what withdraw every built-in and every ambient MCP server, and this is
    the assertion that proves they did.
    """
    _, seen = claude_leg_run
    advertised = {
        name for record in seen for name in record.get("tools", []) if name
    }
    assert advertised, "the scripted model was never asked with a tool surface"
    assert all(
        name.startswith(f"mcp__{MCP_SERVER_NAME}__") for name in advertised
    ), sorted(advertised)


# --------------------------------------------------------------------------
# The shipped external example is untouched (T-16-03-04).
# --------------------------------------------------------------------------


def test_the_shipped_external_example_is_untouched() -> None:
    """`git status --porcelain` over `examples/external/00-hello-context/`.

    EXAM-04/ERGO-15 and `tests/examples/test_ext00_*.py` all rest on those
    files being byte-unchanged, and this module both spawns that server and
    reads its artifacts. Asserted rather than assumed.
    """
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", str(EXT00_DIR)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == "", completed.stdout
