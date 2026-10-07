"""`ClaudeAgentAdapter` — the Claude Agent SDK binding of the four seams (XPRC-03).

SDK-defined extension (CLAUDE.md §7.3; D-IMPL-24, D-IMPL-25). The whitepaper
specifies no harness binding; §7.3 does, and this is its first reference
implementation. Structural conformance to
:class:`~ccf.harness.protocol.HarnessAdapterProtocol` is the contract; the
factory-parametrized suite in ``tests/conformance/test_harness_adapter.py`` is
the acceptance bar, and it drives the real SDK with no model (D-09).

**What this adapter is.** A translator. Each seam takes CCF values and returns
whatever the Claude Agent SDK natively wants — ``ClaudeAgentOptions`` carrying
an in-process MCP server for seam 1/2, a ``PermissionResult`` decision for the
harness's own permission hook, an :class:`~ccf.agents.agent.EmittedEffect` for
seam 3, a :class:`~ccf.replay.record.HarnessTrace` for seam 4. Nothing here
registers itself into a loop, because the loop is the harness's (CLAUDE.md
§7.3, §6.5). There is no ``run``, ``step``, or ``plan`` on this object.

**What this adapter cannot do.** It cannot write to the graph. It holds no
graph write handle, no graph read handle, no graph store, no fabric boot
handle, and no Control Plane registry — none of them is a constructor
parameter, an attribute, or a name anywhere in this module, which the
conformance suite pins by source scan in the same discipline
``tests/harness/test_protocol.py`` applies to the seam itself: a fabric surface
named in a comment or a docstring is a surface someone was thinking about
handing to an adapter (T-06-61). Effects reach L2 only as the value
:meth:`ClaudeAgentAdapter.capture_effect` returns, produced by
:meth:`ccf.agents.agent.Agent.emit_effect`; carrying that value into L3 is L2's
job and nobody else's (single-writer, CLAUDE.md §10, §7.3 seam 3).

Scoped claims, not architectural boasts (D-21). Three mechanisms hold the lines
above, each at the scope of its actual enforcement:

* **Protocol-shape-enforced.** No method on
  :class:`~ccf.harness.protocol.HarnessAdapterProtocol` accepts a fabric object
  other than :class:`~ccf.agents.agent.Agent`, so an adapter typed against it
  cannot receive one. This adapter's constructor takes deployment configuration
  only and holds no fabric object at all.
* **Lint-enforced.** ``cinv02-harness`` denies ``claude_agent_sdk`` in every
  module outside ``ccf_runtime.adapters.*`` (D-IMPL-53). This module is inside
  that carve-out; moving it anywhere else makes the import below a lint
  failure, which the acceptance criteria re-verify by relocation. The
  companion ``cinv02-graph-writer`` rule independently denies naming the
  concrete writer module from here.
* **Conformance-enforced.** The suite asserts set equality between the exposed
  tool names and ``agent.bound_skill_names`` across a grant/revoke round trip
  and across two agents (T-06-66), scans this object's public surface against
  the shared write-surface name list (T-06-67), and drives the ``unsupported``
  effect branch to prove the refusal fires (D-10).

**Prompt artifacts are consumed, never re-resolved.** ``instructions`` arrive
at seam 1 already rendered by :func:`ccf.agents.prompts.render_instruction`
from the artifacts the Agent Factory pinned. This module resolves no URI,
reads no template, and calls no renderer — re-resolution would let two
decisions under the same agent version render different instructions, which
makes the agent version a lie (T-06-64; ``PHASE_I2_GATE.md`` §5).

**This module claims no algorithmic-mode tag, deliberately.** Adapters bind a
harness that reaches a model, so they are the semantic boundary of the
Algorithmic ⇄ Semantic Alternation, not an algorithmic module — and CINV-03
would deny their imports if they claimed otherwise.

Citation: CLAUDE.md §7.3 (SDK-defined extension), §6.2 channel 2 (skill
exposure), §10 (single-writer); D-IMPL-24 (Claude Agent SDK as a v0 reference
target); D-IMPL-25 (seam scope); D-IMPL-53 (the lint carve-out); D-IMPL-55 (the
replay slot seam 4 writes into).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from pathlib import Path
from subprocess import PIPE
from typing import Any

import anyio
from anyio.streams.text import TextReceiveStream, TextSendStream
from claude_agent_sdk import (
    ClaudeAgentOptions,
    CLIConnectionError,
    CLINotFoundError,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    __version__ as _VENDOR_VERSION,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk._internal._task_compat import spawn_detached
from claude_agent_sdk.types import SystemPromptFile
from claude_agent_sdk._internal.transport.subprocess_cli import (
    _ACTIVE_CHILDREN,
    SubprocessCLITransport,
)

from ccf.agents.agent import Agent, EmittedEffect
from ccf.contracts.canonical import canonical_bytes
from ccf.harness.protocol import EffectCapability, EffectRefusal, HarnessCapabilities
from ccf.products.contract import ContextProductContract
from ccf.replay.record import NO_HARNESS, HarnessTrace
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.toolsurface import HARNESS_EXPOSABLE_SKILL_TYPES, render_tool_surface
from ccf.skills.wire_arguments import ArgumentRefused

__all__ = [
    "DEFAULT_CHILD_ENVIRONMENT",
    "HARNESS_ID",
    "AllowlistedEnvironmentTransport",
    "ClaudeAgentAdapter",
]

#: This adapter's stable harness identity. Lands verbatim in
#: :attr:`~ccf.harness.protocol.HarnessCapabilities.harness_id` and in
#: :attr:`~ccf.replay.record.HarnessTrace.harness_id`, so it is the value a
#: replay reads to answer "which harness ran this". A mechanism identifier
#: naming the package this module binds — not a deployment value, which is why
#: it is a constant here and every genuinely deployment-owned value
#: (model, server name, effect capability) is a constructor argument instead.
HARNESS_ID = "claude-agent-sdk"

#: The variable NAMES the ``claude`` child receives, by value read from the
#: fabric's own environment, when the deployment declares no
#: ``child_environment`` (TP-02, D-IMPL-361; the controller's ruling). Names
#: only — never values — so this is mechanism, not a deployment value; every
#: other variable reaches the child only when the deployment names it.
DEFAULT_CHILD_ENVIRONMENT: tuple[str, ...] = ("PATH", "HOME")

#: Mechanism variables the vendor's own transport always sets on the child
#: (claude-agent-sdk 0.2.128, ``subprocess_cli.py:690-694``). Reproduced so the
#: allowlisted child sees the same SDK identity the vendor's spawn would give
#: it; neither carries a fabric value.
_VENDOR_ENTRYPOINT_VARIABLE = "CLAUDE_CODE_ENTRYPOINT"
_VENDOR_ENTRYPOINT = "sdk-py"
_VENDOR_VERSION_VARIABLE = "CLAUDE_AGENT_SDK_VERSION"
_VENDOR_CHECKPOINTING_VARIABLE = "CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING"

#: The vendor client's permission-prompt routing value. ``ClaudeSDKClient`` and
#: ``query`` set it on *their own* copy of the options when ``can_use_tool`` is
#: bound, and a pre-built transport never sees that copy — so a transport built
#: from the carrier must carry it itself, or the CLI never consults the gate.
_PERMISSION_PROMPT_OVER_STDIO = "stdio"

#: Owner-only modes for the per-call system-prompt directory and file (TP-05,
#: D-IMPL-361; the controller's ruling). ``tempfile.mkdtemp`` already creates
#: the directory ``0700``; the file is created ``0600`` and re-asserted with
#: ``fchmod`` so a permissive umask cannot widen it.
_PROMPT_FILE_MODE = 0o600
_PROMPT_FILE_NAME = "system-prompt"

#: The name of a file that is never created, inside the per-call ``0700``
#: prompt directory. ``inject_context`` points the carrier's ``cli_path`` at it
#: so the vendor's **default** transport — the one an adopter gets by omitting
#: :meth:`ClaudeAgentAdapter.transport` — cannot start the CLI and fails with
#: ``CLINotFoundError`` instead of spawning it with the fabric's whole
#: environment (TP-02 fails closed, D-IMPL-361). Only the fabric's own user
#: could create it, because the directory is owner-only.
_NO_CLI_SENTINEL = "no-cli-use-the-adapter-transport"


def _write_prompt_file(prompt: str) -> Path:
    """Write ``prompt`` to a fresh ``0600`` file in a fresh ``0700`` directory.

    The directory is created per call by ``tempfile.mkdtemp`` (owner-only by
    construction) and the file with ``O_EXCL``, so no other carrier's prompt
    file is ever reused or overwritten.
    """
    directory = Path(tempfile.mkdtemp())
    path = directory / _PROMPT_FILE_NAME
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _PROMPT_FILE_MODE
    )
    with os.fdopen(descriptor, "wb") as handle:
        os.fchmod(handle.fileno(), _PROMPT_FILE_MODE)
        handle.write(prompt.encode("utf-8"))
    return path

def _qualified_tool_name(server_name: str, skill_name: str) -> str:
    """The name the harness sees for an in-process MCP tool.

    The Claude Agent SDK namespaces SDK-MCP tools as
    ``mcp__{server}__{tool}``, and ``allowed_tools`` is matched against that
    namespaced form. Composed here rather than spelled at each call site so
    the exposure gate and the permission gate cannot drift apart — the whole
    point of seam 2 is that those two agree exactly.
    """
    return f"mcp__{server_name}__{skill_name}"


def _refused(reason: str) -> dict[str, Any]:
    """An in-process MCP tool result that refuses, carrying ``reason`` (TP-01).

    ``is_error`` is the key the vendor's ``create_sdk_mcp_server`` wrapper
    reads into ``CallToolResult.isError`` (claude-agent-sdk 0.2.128,
    ``claude_agent_sdk/__init__.py:521``); an ``isError`` key would be dropped
    there and the refusal would reach the harness as a success.
    """
    return {"content": [{"type": "text", "text": reason}], "is_error": True}


class AllowlistedEnvironmentTransport(SubprocessCLITransport):
    """The vendor's subprocess transport, spawning the child from an allowlist (TP-02).

    SDK-defined (CLAUDE.md §7.3; TP-02, D-IMPL-361). Measured in
    claude-agent-sdk 0.2.128 (``_internal/transport/subprocess_cli.py``):
    ``connect()`` builds the child environment as ``{**os.environ, ...,
    **options.env, ...}`` (lines 689-694) and passes it to
    ``anyio.open_process`` (line 739), so ``ClaudeAgentOptions.env`` merges
    **over** the fabric's whole environment and cannot subtract from it; the
    version probe (``_check_claude_version``, lines 1031-1035) spawns the same
    binary with no ``env`` at all. This subclass replaces ``connect()`` so the
    child's environment is **exactly** :meth:`child_environment` — the
    carrier's ``env`` plus the vendor's own mechanism variables — and nothing
    inherited.

    Differences from the vendor's ``connect()``, each deliberate: the version
    probe is not run (it would hand the binary the full environment, and it
    only ever logs a warning); OpenTelemetry trace propagation from the
    fabric's environment is not performed (a deployment that wants it declares
    the variables in ``child_environment``). Everything else — CLI resolution,
    the Windows batch-file refusal, argv, working directory, stderr callback,
    child tracking — follows the vendor's own code path.

    This subclasses a **private** vendor module, which the spec records as the
    cost of the env half of TP-02 (§7.1 fact (d)); a vendor upgrade that
    changes ``connect()`` must be re-measured against it.
    """

    def child_environment(self) -> dict[str, str]:
        """The complete environment the ``claude`` child is spawned with (TP-02).

        Exactly the carrier's ``env`` — the deployment-declared allowlist, or
        :data:`DEFAULT_CHILD_ENVIRONMENT` — plus the vendor's own mechanism
        variables; nothing is read from the fabric's environment here
        (D-IMPL-361).
        """
        environment = {
            _VENDOR_ENTRYPOINT_VARIABLE: _VENDOR_ENTRYPOINT,
            **self._options.env,
            _VENDOR_VERSION_VARIABLE: _VENDOR_VERSION,
        }
        if self._options.enable_file_checkpointing:
            environment[_VENDOR_CHECKPOINTING_VARIABLE] = "true"
        if self._cwd:
            environment["PWD"] = self._cwd
        return environment

    async def connect(self) -> None:
        """Start the child with :meth:`child_environment` and nothing inherited (TP-02).

        Replaces the vendor's ``connect()``, which merges ``os.environ`` into
        the child and runs a version probe that inherits it whole
        (D-IMPL-361).
        """
        if self._process:
            return
        if self._cli_path is None:
            self._cli_path = await anyio.to_thread.run_sync(self._find_cli)
        self._reject_windows_batch_cli(self._cli_path)
        command = self._build_command()
        stderr_dest = PIPE if self._options.stderr is not None else None
        try:
            self._process = await anyio.open_process(
                command,
                stdin=PIPE,
                stdout=PIPE,
                stderr=stderr_dest,
                cwd=self._cwd,
                env=self.child_environment(),
                user=self._options.user,
            )
            _ACTIVE_CHILDREN.add(self._process)
            if self._process.stdout:
                self._stdout_stream = TextReceiveStream(self._process.stdout)
            if stderr_dest is PIPE and self._process.stderr:
                self._stderr_stream = TextReceiveStream(self._process.stderr)
                self._stderr_task = spawn_detached(self._handle_stderr())
            if self._process.stdin:
                self._stdin_stream = TextSendStream(self._process.stdin)
            self._ready = True
        except FileNotFoundError as error:
            failure: Exception
            if self._cwd and not Path(self._cwd).exists():
                failure = CLIConnectionError(
                    f"Working directory does not exist: {self._cwd}"
                )
            else:
                failure = CLINotFoundError(f"Claude Code not found at: {self._cli_path}")
            self._exit_error = failure
            raise failure from error
        except Exception as error:
            failure = CLIConnectionError(f"Failed to start Claude Code: {error}")
            self._exit_error = failure
            raise failure from error


class ClaudeAgentAdapter:
    """The Claude Agent SDK's binding of the four seams (CLAUDE.md §7.3).

    Structurally conforms to
    :class:`~ccf.harness.protocol.HarnessAdapterProtocol`; declared by shape,
    not by inheritance, in the SDK's Protocol-over-inheritance discipline
    (CLAUDE.md §11).

    **The bound agent arrives per seam call, and is not held.** Every Protocol
    method takes ``agent`` as a keyword argument, so one adapter instance
    serves any number of agents and each call resolves that agent's own
    currently-bound skill-set from the ledger-backed view the factory injected
    (D-07, D-23). Holding an agent *as well* would create two answers to
    "whose skills are these" and let a per-adapter cache outlive a revocation —
    which is precisely the over-exposure T-06-66 registers.

    Args:
        model: The model identifier this deployment binds, placed on
            :attr:`ClaudeAgentOptions.model`. Injected because it is a
            deployment value; the SDK ships no model name.
        mcp_server_name: The in-process MCP server's name. Determines the
            ``mcp__{server}__{tool}`` namespace the harness sees, so it is
            part of the deployment's tool vocabulary, not the SDK's.
        mcp_server_version: The in-process MCP server's declared version.
        effects: This adapter's declared effect-capture capability
            (D-IMPL-25, D-10). Required with no default: a defaulted
            capability would let an adapter inherit a claim about effect
            capture it never made. Injected rather than fixed so a deployment
            can bind the same harness read-only, and so the conformance suite
            can drive both branches of the capability space.
        child_environment: The complete environment, names and values, the
            ``claude`` child receives (TP-02, D-IMPL-361) — deployment-declared.
            ``None`` (the default) gives the child only
            :data:`DEFAULT_CHILD_ENVIRONMENT`'s names, valued from the fabric's
            environment; every other variable is opt-in by name. Placed on
            ``ClaudeAgentOptions.env`` and enforced by the transport from
            :meth:`transport`, because the vendor's default transport merges
            ``env`` over the fabric's whole environment.
    """

    def __init__(
        self,
        *,
        model: str,
        mcp_server_name: str,
        mcp_server_version: str,
        effects: EffectCapability,
        child_environment: Mapping[str, str] | None = None,
    ) -> None:
        self._model = model
        self._mcp_server_name = mcp_server_name
        self._mcp_server_version = mcp_server_version
        self._effects: EffectCapability = effects
        self._declared_child_environment: dict[str, str] | None = (
            None if child_environment is None else dict(child_environment)
        )
        self._prompt_directories: list[str] = []

    @property
    def prompt_directories(self) -> tuple[str, ...]:
        """Every per-call system-prompt directory this adapter created (TP-05).

        :meth:`inject_context` writes the assembled prompt to a ``0600`` file
        in a new ``0700`` directory on each call, because the vendor would
        otherwise put the prompt on the ``claude`` argv (D-IMPL-361). The
        directories are **the adopter's to remove** once the session that
        used the carrier has ended, with :meth:`remove_prompt_directories` —
        this adapter runs no background cleaner, because it cannot know when
        the harness has finished reading the file.
        """
        return tuple(self._prompt_directories)

    def remove_prompt_directories(self) -> None:
        """Remove every recorded system-prompt directory and forget it (TP-05).

        Synchronous and idempotent: a directory already gone is skipped, and
        :attr:`prompt_directories` is empty afterwards. Each directory holds
        the full assembled prompt — rendered instructions and the canonical
        serialization of every product the carrier delivered — at rest, so a
        long-lived adapter should call this once the sessions that used its
        carriers have ended (D-IMPL-361). A carrier whose directory has been
        removed can no longer start a session.
        """
        while self._prompt_directories:
            shutil.rmtree(self._prompt_directories.pop(), ignore_errors=True)

    # --- seam 0: what this adapter declares about itself ---------------------

    def capabilities(self) -> HarnessCapabilities:
        """Declare this adapter's harness identity and effect capability."""
        return HarnessCapabilities(harness_id=HARNESS_ID, effects=self._effects)

    # --- seam 2 helpers ------------------------------------------------------

    def _bound_entry(self, agent: Agent, skill_name: str) -> SkillCatalogEntry:
        """The catalog entry currently bound under ``skill_name``.

        Resolution goes through :meth:`~ccf.agents.agent.Agent.invoke_skill`
        with no arguments — the introspection form — so a name the agent is
        not currently granted raises
        :class:`~ccf.agents.errors.SkillNotBound` here rather than becoming a
        tool the harness can see.
        """
        entry = agent.invoke_skill(skill_name)
        if not isinstance(entry, SkillCatalogEntry):  # pragma: no cover - defensive
            raise TypeError(
                f"introspecting skill {skill_name!r} returned"
                f" {type(entry).__name__}, not a catalog entry"
            )
        return entry

    def _skill_tool(self, agent: Agent, skill_name: str) -> Any:
        """One in-process MCP tool closing over this agent's skill seam.

        The handler calls :meth:`~ccf.agents.agent.Agent.invoke_skill` and
        returns the typed invocation's canonical bytes as the tool result.
        Dispatch is therefore the fabric's, every time the harness calls the
        tool: binding is re-resolved from the ledger-backed view at each
        invocation, so a revocation between two harness turns takes effect on
        the second one without the agent's identity changing (D-07).

        **The handler is the adapter-owned control (TP-01, D-IMPL-361).** The
        vendor routes a CLI ``tools/call`` straight to this handler with no
        Python-side permission check (claude-agent-sdk 0.2.128,
        ``_internal/query.py:679-688``); ``allowed_tools`` and
        ``can_use_tool`` are enforced by the semi-trusted CLI and are defense
        in depth only. So the handler re-applies both of the permission gate's
        conditions itself, **before** :meth:`~ccf.agents.agent.Agent.invoke_skill`
        is reached: a binding that declared ``effects`` other than
        ``governed`` refuses every call, and a skill not in
        ``agent.bound_skill_names`` *at call time* refuses. A refusal is an
        MCP error result (the vendor's ``is_error`` key, which it carries to
        ``CallToolResult.isError`` at ``claude_agent_sdk/__init__.py:521``)
        whose text is this adapter's own reason.

        **The argument rule is the seam's** (``TP-04`` follow-on,
        ``D-IMPL-361``). The harness's arguments are handed to
        :meth:`~ccf.agents.agent.Agent.invoke_skill` as they arrived — not
        pre-stringified — and the seam refuses an undeclared key, a missing
        required argument or a wrong-typed value before dispatch, as the
        :class:`~ccf.skills.wire_arguments.ArgumentRefused` family. The handler
        renders that refusal as the same ``is_error`` result, so nothing is
        dispatched or audited for a call the declared schema does not admit.
        """
        entry = self._bound_entry(agent, skill_name)
        surface = render_tool_surface(entry)

        @tool(entry.name, surface.description, surface.input_schema)
        async def handler(args: Mapping[str, Any]) -> dict[str, Any]:
            if self._effects != "governed":
                return _refused(self._refusal_reason())
            if skill_name not in agent.bound_skill_names:
                return _refused(
                    self._unbound_reason(
                        _qualified_tool_name(self._mcp_server_name, skill_name)
                    )
                )
            try:
                invocation = agent.invoke_skill(skill_name, arguments=dict(args))
            except ArgumentRefused as refused:
                return _refused(str(refused))
            payload = canonical_bytes(invocation).decode("utf-8")
            return {"content": [{"type": "text", "text": payload}]}

        return handler

    def _tools(self, agent: Agent) -> tuple[Any, ...]:
        """The harness-native tools for exactly this agent's bound skill-set.

        Built from ``agent.bound_skill_names`` and nothing else — never from
        the skill catalog, which holds every entry the deployment registered
        rather than the ones this agent was granted. Computing exposure over a
        shared catalog is the over-exposure defect T-06-66 registers, and it
        is invisible with one agent in the suite; the D-23 two-agent case is
        what makes it visible.

        Filtered by :data:`~ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES`
        before rendering (``TP-03``, ``D-IMPL-361``): a bound ``peering``,
        ``mcp_product`` or ``procedure`` skill is skipped — never rendered and
        never raised on — so the agent's exposable skills still reach the
        harness.
        """
        return tuple(
            self._skill_tool(agent, skill_name)
            for skill_name in agent.bound_skill_names
            if self._bound_entry(agent, skill_name).skill_type
            in HARNESS_EXPOSABLE_SKILL_TYPES
        )

    def expose_skills(self, *, agent: Agent) -> tuple[str, ...]:
        """Seam 2 — exactly the currently-bound skill-set, as harness tools.

        Returns the skill names actually exposed, sorted, so the conformance
        suite compares them against
        :attr:`~ccf.agents.agent.Agent.bound_skill_names` structurally rather
        than by reading this code (CLAUDE.md §6.2 channel 2, §7.3 seam 2). A
        skill the agent has not been granted does not exist from the harness's
        point of view: it is not built into a tool, it is not attached to the
        MCP server, it is absent from ``allowed_tools``, and the permission
        gate would deny it if the harness named it anyway.

        Every exposed tool's description and argument schema come from the
        one shared derivation
        (:func:`ccf.skills.toolsurface.render_tool_surface`) over the entry's
        own declared ``description`` and ``argument_schema`` (D-IMPL-56) —
        never adapter-authored, so all three reference adapters render the
        identical surface for the same entry (D-17).
        """
        return tuple(sorted(handler.name for handler in self._tools(agent)))

    # --- seam 1 --------------------------------------------------------------

    def inject_context(
        self,
        *,
        agent: Agent,
        products: tuple[ContextProductContract, ...],
        instructions: tuple[str, ...],
    ) -> object:
        """Seam 1 — typed context into the harness's own context surface.

        Returns a ``ClaudeAgentOptions`` — the harness-native carrier — with
        the already-rendered instructions and the canonical serialization of
        each already-admitted Context Product joined into the system prompt,
        this agent's tools on an in-process MCP server, ``allowed_tools`` set
        to exactly those tools, and the permission gate bound.

        **The system prompt reaches the CLI by file, never by argv (TP-05,
        D-IMPL-361).** A string ``system_prompt`` is placed on the ``claude``
        command line as ``--system-prompt <text>`` (claude-agent-sdk 0.2.128,
        ``subprocess_cli.py:467-468``), where every local process and any
        central process audit can read it. So the joined prompt is written to
        a ``0600`` file in a new ``0700`` directory per call, and
        ``system_prompt`` carries the vendor's typed file form
        (``{"type": "file", "path": ...}``), which the vendor renders as the
        single option ``--system-prompt-file <path>`` (lines 469-473). The
        directory is recorded on :attr:`prompt_directories` for the adopter to
        remove (:meth:`remove_prompt_directories`).

        **The carrier fails closed without the adapter's transport (TP-02,
        D-IMPL-361).** The carrier's ``cli_path`` names a file that does not
        exist inside that owner-only directory. Handing the carrier to
        ``ClaudeSDKClient(options=carrier)`` or ``query(options=carrier)``
        **without** ``transport=adapter.transport(carrier)`` therefore raises
        ``CLINotFoundError`` at connect and starts nothing — because the
        vendor's default transport would spawn the CLI with the fabric's whole
        environment merged in. :meth:`transport` clears the sentinel so the
        vendor resolves the real CLI, and spawns it from the allowlist only.

        ``products`` are products the agent already admitted through
        :meth:`~ccf.agents.agent.Agent.consume`; they are serialized
        canonically so what the harness sees is byte-identical to what replay
        records. The harness touches no L3 handle and no raw signal, because
        nothing on this seam can reach either.

        ``instructions`` are rendered strings. This method resolves no
        artifact and renders no template (T-06-64).
        """
        tools = self._tools(agent)
        server = create_sdk_mcp_server(
            name=self._mcp_server_name,
            version=self._mcp_server_version,
            tools=list(tools),
        )
        serialized_products = tuple(
            canonical_bytes(product).decode("utf-8") for product in products
        )
        prompt_file = _write_prompt_file("\n".join((*instructions, *serialized_products)))
        self._prompt_directories.append(str(prompt_file.parent))
        system_prompt: SystemPromptFile = {"type": "file", "path": str(prompt_file)}
        carrier: object = ClaudeAgentOptions(
            model=self._model,
            system_prompt=system_prompt,
            mcp_servers={self._mcp_server_name: server},
            allowed_tools=[
                _qualified_tool_name(self._mcp_server_name, handler.name)
                for handler in tools
            ],
            can_use_tool=self._permission_gate(agent),
            env=self._child_environment(),
            cli_path=prompt_file.parent / _NO_CLI_SENTINEL,
        )
        return carrier

    def _child_environment(self) -> dict[str, str]:
        """The ``claude`` child's environment for this deployment (TP-02).

        The declared ``child_environment`` verbatim when there is one;
        otherwise :data:`DEFAULT_CHILD_ENVIRONMENT`'s names, valued from the
        fabric's environment at carrier-build time, skipping a name the fabric
        does not have.
        """
        if self._declared_child_environment is not None:
            return dict(self._declared_child_environment)
        return {
            name: os.environ[name]
            for name in DEFAULT_CHILD_ENVIRONMENT
            if name in os.environ
        }

    def transport(self, carrier: object) -> AllowlistedEnvironmentTransport:
        """The transport an adopter must hand the vendor with ``carrier`` (TP-02).

        Pass it as ``ClaudeSDKClient(options=carrier, transport=...)`` or
        ``query(prompt=..., options=carrier, transport=...)``. Without it the
        vendor's default transport spawns ``claude`` with the fabric's whole
        environment, whatever ``carrier.env`` says — ``env`` merges over
        ``os.environ`` and cannot subtract (D-IMPL-361).

        The carrier's own ``cli_path`` is a fail-closed sentinel; the
        transport is built with it cleared, so the vendor's CLI resolution
        applies here and nowhere else. The transport is built from
        ``carrier`` with the permission prompt
        routed over stdio when a ``can_use_tool`` gate is bound, because the
        vendor client applies that routing only to the options *it* would have
        built a transport from; a pre-built transport that lacked it would
        leave the CLI never consulting the gate.

        Raises:
            TypeError: ``carrier`` is not a ``ClaudeAgentOptions``.
        """
        if not isinstance(carrier, ClaudeAgentOptions):
            raise TypeError(
                f"transport expected the ClaudeAgentOptions inject_context"
                f" returned, got {type(carrier).__name__}"
            )
        # Clear the fail-closed sentinel ``inject_context`` set, so the vendor
        # resolves the real CLI (bundled, then PATH) for this transport only.
        options = replace(carrier, cli_path=None)
        if options.can_use_tool is not None and options.permission_prompt_tool_name is None:
            options = replace(
                options, permission_prompt_tool_name=_PERMISSION_PROMPT_OVER_STDIO
            )
        return AllowlistedEnvironmentTransport(prompt="", options=options)

    # --- seam 3 --------------------------------------------------------------

    def _permission_gate(
        self, agent: Agent
    ) -> Callable[[str, dict[str, Any], Any], Awaitable[Any]]:
        """The harness's own permission hook, closed over this agent's grants.

        The Claude Agent SDK asks ``can_use_tool`` before a tool runs and
        honours ``PermissionResultDeny``. Bound here so the refusal is
        something this adapter can positively assert rather than something it
        can only decline to implement — an absent write path and a fired
        refusal are not the same evidence (D-10).

        Two conditions deny: a tool outside this agent's currently-bound
        EXPOSABLE skill-set, and — when this adapter declared ``effects:
        unsupported`` — every tool, because a read-only binding must not let
        the harness reach a dispatch path at all.

        **Permitted means bound AND harness-exposable** (``TP-03`` follow-on,
        ``D-IMPL-361``): a bound ``peering``, ``mcp_product`` or ``procedure``
        skill is never rendered as a tool (:meth:`_tools`), so the gate denies
        it too, with the same unbound-reason message — a harness that names a
        tool it was never shown is refused, not admitted.
        """

        async def can_use_tool(
            tool_name: str, tool_input: dict[str, Any], context: Any
        ) -> Any:
            if self._effects != "governed":
                return PermissionResultDeny(message=self._refusal_reason())
            permitted = {
                _qualified_tool_name(self._mcp_server_name, name)
                for name in agent.bound_skill_names
                if self._bound_entry(agent, name).skill_type
                in HARNESS_EXPOSABLE_SKILL_TYPES
            }
            if tool_name not in permitted:
                return PermissionResultDeny(message=self._unbound_reason(tool_name))
            return PermissionResultAllow()

        return can_use_tool

    def _refusal_reason(self) -> str:
        """Why a read-only binding refuses, in this adapter's own words."""
        return f"{HARNESS_ID} declared effects={self._effects!r}"

    def _unbound_reason(self, tool_name: str) -> str:
        """Why a tool outside the bound skill-set is denied."""
        return f"{tool_name!r} is not in the agent's bound skill-set"

    def capture_effect(
        self, *, agent: Agent, output: Mapping[str, Any]
    ) -> EmittedEffect | EffectRefusal:
        """Seam 3 — a harness output back through governed emission.

        Implemented for both declared capabilities, which is what makes the
        ``unsupported`` case conformance-verifiable rather than merely
        unimplemented (D-10). Under ``governed`` the output goes through
        :meth:`~ccf.agents.agent.Agent.emit_effect` and comes back as a typed
        :class:`~ccf.agents.agent.EmittedEffect`; under ``unsupported`` every
        output comes back as a typed
        :class:`~ccf.harness.protocol.EffectRefusal`.

        Either way the return value is the entire effect. This adapter holds
        no write handle and constructs none, so nothing reaches L3 here —
        carrying an admitted effect into the graph is L2's job (CLAUDE.md §10,
        §7.3 seam 3).
        """
        if self._effects != "governed":
            return EffectRefusal(
                harness_id=HARNESS_ID,
                agent_definition_hash=agent.identity.definition_hash,
                reason=self._refusal_reason(),
            )
        return agent.emit_effect(output)

    # --- seam 4 --------------------------------------------------------------

    def replay_trace(self, *, execution: object) -> HarnessTrace:
        """Seam 4 — the harness's execution into replay dimension 3.

        Translates the SDK's ``ResultMessage`` into the
        :class:`~ccf.replay.record.HarnessTrace` block that
        :func:`~ccf.replay.record.build_replay_record` records verbatim under
        ``model_version.harness_trace`` (D-25, D-IMPL-55).

        Only harness-attributable values are read: the model the *harness*
        reported running (its ``model_usage`` keys, not this adapter's
        configured ``model`` — the fabric records what it invoked and the
        harness records what it invoked, and conflating the two is how a
        harness overwrites a governed field, T-06-62), its session id as the
        trace reference, and its own token counts.

        A field the ``ResultMessage`` did not report is left at its positive
        :data:`~ccf.replay.record.NO_HARNESS` sentinel rather than guessed: an
        absent trace and a dropped one must not be the same artifact
        (T-06-63).

        Raises:
            TypeError: ``execution`` is not a Claude Agent SDK
                ``ResultMessage``. Typed ``object`` on the Protocol because a
                harness-native execution result is harness-shaped by
                definition; narrowing it is this adapter's job.
        """
        if not isinstance(execution, ResultMessage):
            raise TypeError(
                f"replay_trace expected a ResultMessage, got"
                f" {type(execution).__name__}"
            )
        usage: Mapping[str, Any] = execution.usage or {}
        reported_models = tuple(sorted(execution.model_usage or {}))
        return HarnessTrace(
            harness_id=HARNESS_ID,
            model_version=",".join(reported_models) if reported_models else NO_HARNESS,
            trace_provider=HARNESS_ID,
            trace_id=execution.session_id or NO_HARNESS,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )
