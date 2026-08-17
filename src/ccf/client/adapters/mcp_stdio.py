"""The second wire — a real process boundary, spoken over MCP stdio.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§3 (``D-06``), §5 (``D-11``, ``D-12``) and §9 (``D-24``). Framed by CLAUDE.md
§7.1: MCP is the SDK's own bidirectional integration surface, so a client
reaching a deployment through it is the egress role read from the far side.

What the address names: a program, and the deployment it serves
----------------------------------------------------------------
``mcp+stdio:<program> <root>`` — two whitespace-separated tokens, parsed with
:func:`shlex.split` so a path containing a space can be quoted. Both are needed
and neither can be inferred from the other:

* **stdio means the client launches the server.** There is no endpoint to
  connect to; ``stdio_client`` spawns a child process and speaks to its pipes.
  A client that starts a deployment necessarily knows where that deployment is,
  so reading its declared question vocabulary from ``<root>`` is a consequence
  of the transport rather than a privilege taken over it. A networked MCP
  binding would learn those facts from the wire, which is why this scheme names
  the transport in its own name.
* **The SDK ships no server program and must not.**
  ``ccf_runtime.mcp.egress::build_egress_server`` requires a server name, a
  token verifier, auth settings, an entitlement source and a perspective
  resolver — five deployment values in their entirety (CINV-01). So the program
  is the deployment's, and this module launches it without knowing what is in
  it.
* **The program may not live in the deployment root.** ``D-IMPL-141``
  Amendment A.3 grants a deployment root exactly **one** Python module, the
  projection, and ``tests/client/test_data_only_deployment.py`` refuses a second
  by name. A one-token address that inferred the root from the program's own
  directory was written first and that gate caught it — recorded here because
  the two-token form looks like a redundancy until you know why it is not.

``ccf.client.binding`` and ``ccf.client.client`` have spelled this scheme
``mcp+stdio:./server.py`` since ``D-06`` was written. The program still leads
the address; what this module adds is the root behind it.

What is asked, and where each argument comes from
--------------------------------------------------
:data:`~ccf.products.door.PRODUCT_REQUEST_TOOL` takes eight arguments and a
:class:`~ccf.client.wire.WireRequest` carries three, which is not a mismatch to
paper over — it is the ``D-04`` boundary showing through. The client's question
is *what class, which parameters, as of when*; the rest is the deployment's own
vocabulary, and the in-process adapter reads exactly the same values from
exactly the same two documents:

===================  =========================================================
Tool argument        Where it comes from
===================  =========================================================
``product_class``    the caller's ``WireRequest.product_id``
``parameters``       the caller's ``WireRequest.parameters``, verbatim
``asked_at``         the caller's boundary, or **now** when it deferred
                     (``D-04``: ``None`` means the decision instant)
``tenant``           the deployment root's ``ccf_config.yaml`` ``tenant_id``
``version``          ``ccf_config.yaml``'s registered ``product_class`` lane —
                     never the caller's, because ``WireRequest`` deliberately
                     carries no version (a client pinning one is a client
                     maintaining a copy of the deployment's registry)
``subject``          ``binding.yaml``'s declared ``question``
``intent``           the same
``freshness``        the same
===================  =========================================================

Sync at the surface, async bridged inside (``D-24``)
-----------------------------------------------------
:meth:`McpStdioAdapter.ask` is synchronous and has no asynchronous twin. One
:func:`asyncio.run` per call opens the
transport, initializes the session, calls the tool and closes both — the
**session-per-call** rule :mod:`ccf.mcp.client` records at length, for the
measured reason that a held ``ClientSession`` driven from a blocking bridge
deadlocks.

:class:`~ccf.mcp.client.SyncMcpBridge` is deliberately **not** reused here, and
the reason is a value the SDK may not choose: it requires
``call_timeout_seconds`` with no default (``D-IMPL-38``), and an address is one
string with no deadline in it. ``T-17-41`` dispositions a stdio server that
never answers as **accept** for v0 — no timeout, no retry, no backoff — so this
module invents none rather than picking a number nobody authored.

A broken wire is never a refusal (``D-07``, ``D-10``)
------------------------------------------------------
Every way this transport can fail to produce a governed answer raises
:class:`~ccf.client.errors.TransportError`: a program that will not start, a
pipe that closes, bytes that are not a :class:`~ccf.products.door.DoorOutcome`,
and a tool that answered ``isError`` — which is what a **raised** exception at
the door becomes on the wire, including the governance refusal the door raises
by ruling. That last one is not a governed "no" and is not reported as one:
:mod:`ccf.client.errors` already places an authentication failure under
*the wire never spoke*, because from where the caller stands no answer arrived.

This module builds **no** :class:`~ccf.client.result.Result` (``D-12``). It
returns a :class:`~ccf.client.wire.WireOutcome` and
:meth:`~ccf.client.client.ProductClient._result_from` does the rest, so shape
identity across transports stays a code path this adapter cannot avoid.

This module is algorithmic (CINV-03): it launches a process, exchanges typed
messages and re-shapes an outcome. No LLM dependency on this path, ever.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent
from pydantic import ValidationError

from ccf.client.adapters.binding_document import (
    BindingDocument,
    load_binding_document,
)
from ccf.client.binding import SCHEME_REGISTRY
from ccf.client.errors import BindingError, TransportError
from ccf.client.wire import WireOutcome, WireRequest
from ccf.controlplane.artifacts import DEPLOYMENT_CONFIG, DeploymentConfig
from ccf.controlplane.artifacts import load_artifact as load_control_plane_artifact
from ccf.products.door import PRODUCT_REQUEST_TOOL, DoorOutcome

__ccf_mode__ = "algorithmic"

__all__ = ["SCHEME", "McpStdioAdapter"]


#: The scheme this adapter answers to. Written once, so the registry entry, the
#: refusal messages and the tests all say the same string.
SCHEME = "mcp+stdio"

#: The section of ``ccf_config.yaml`` naming the class this deployment serves.
#: An SDK-owned section name (``D-IMPL-136``, *"the section name IS the
#: class"*) and therefore mechanism, not a deployment's vocabulary.
_SCHEMA_VERSION = "schema_version"


@dataclass(frozen=True)
class _Declared:
    """Everything the far side's question needs that the caller does not carry.

    Read per :meth:`McpStdioAdapter.ask` rather than cached, because a stdio
    server is spawned per call anyway: there is no boot to amortise here, and a
    cache would be a second place this deployment's identity is decided.
    """

    program: Path
    document: BindingDocument
    tenant: str
    version: str


class McpStdioAdapter:
    """Carry a question to a deployment in another process, over MCP stdio.

    Conforms to :class:`~ccf.client.wire.TransportAdapter` structurally; it is
    registered for the ``mcp+stdio`` scheme at import of this module, which is
    the whole of how a scheme reaches the registry (``D-05`` — no plugin lookup
    and no discovery chain).

    Args:
        address: The remainder of the binding after its scheme prefix — the
            path to the deployment's server program. Not resolved here:
            resolution happens on :meth:`ask`, so a client constructed against
            a program that does not exist yet fails when it asks rather than
            when it is built, which is the posture
            :class:`~ccf.client.adapters.inprocess.InProcessAdapter` already
            takes for a root.
    """

    __slots__ = ("_address",)

    def __init__(self, address: str) -> None:
        self._address = address

    def ask(self, request: WireRequest) -> WireOutcome:
        """Launch the deployment's server, ask it one question, and re-shape it.

        Raises:
            ccf.client.errors.BindingError: the address names no server
                program, or the deployment beside it is unusable. A
                :class:`~ccf.client.errors.TransportError` by inheritance, so
                one ``except`` clause still covers every way the wire never
                spoke.
            ccf.client.errors.TransportError: the program would not start, the
                pipe closed, the tool answered with an error rather than an
                outcome, or what came back is not a well-formed
                :class:`~ccf.products.door.DoorOutcome`.
        """
        declared = self._declared()
        question = declared.document.question
        arguments: dict[str, object] = {
            "tenant": declared.tenant,
            "product_class": request.product_id,
            "version": declared.version,
            "subject": question.subject,
            "intent": question.intent,
            "freshness": question.freshness,
            # `D-04`: `None` is the positive assertion *answer against the
            # decision instant*, and the in-process adapter resolves it the
            # same way and in the same place. Resolving it here rather than
            # leaving the argument out is forced by the tool's own shape —
            # all four §6.3 axes are required, which makes a partial address
            # unrepresentable rather than merely refused.
            "asked_at": (
                request.temporal_boundary or datetime.now(UTC)
            ).isoformat(),
            # Verbatim, exactly as the door forwards them: MCP carries tool
            # arguments as JSON, so `D-IMPL-103`'s one level of declared
            # nesting crosses intact and there is nothing to coerce. The
            # declared world is closed at the resolver (`D-IMPL-121`).
            "parameters": dict(request.parameters),
        }
        return self._decode(
            asyncio.run(
                self._call(declared.program, declared.document.root, arguments)
            ),
            request=request,
        )

    def _declared(self) -> _Declared:
        """Split the address, then read what its deployment declares.

        Each half is refused **by name** rather than half-resolved: a binding
        naming one token, or a program that is not a file, is an ordinary
        authoring mistake, and it is cheaper to diagnose here than as a missing
        ``binding.yaml`` two layers down.
        """
        try:
            tokens = shlex.split(self._address)
        except ValueError as unparsable:
            raise BindingError(
                f"`{self._address}` is not a usable `{SCHEME}` address —"
                f" {unparsable}. It is the server program and the deployment"
                " root it serves, separated by a space, with either quoted if it"
                " contains one"
            ) from unparsable
        if len(tokens) != 2:
            raise BindingError(
                f"`{self._address}` states {len(tokens)} tokens; an `{SCHEME}`"
                " address states exactly two — the server program to launch and"
                " the deployment root it serves, as in"
                " `mcp+stdio:./server.py ./deployment`. Neither is inferable"
                " from the other: the SDK ships no server program, and a"
                " deployment root holds exactly one Python module by"
                " `D-IMPL-141` Amendment A.3, which is its projection"
            )
        program = Path(tokens[0]).expanduser().resolve()
        if not program.is_file():
            raise BindingError(
                f"`{tokens[0]}` names no server program — it resolves to"
                f" {program}, which is not a file. An `{SCHEME}` binding launches"
                " the deployment's own MCP server program, because the SDK ships"
                " none and cannot"
            )
        document = load_binding_document(tokens[1])
        config = load_control_plane_artifact(
            document.config.read_text(encoding="utf-8"), DEPLOYMENT_CONFIG
        )
        if not isinstance(config, DeploymentConfig):  # pragma: no cover - typed
            raise BindingError(
                f"{document.config} did not parse as a deployment config"
            )
        if config.tenant_id is None:
            raise BindingError(
                f"{document.config} names no `tenant_id`, so there is no tenant"
                f" to address a product to. An `{SCHEME}` client asks across a"
                " process boundary and cannot infer the tenant the way an"
                " in-process boot reads it off the fabric it just booted"
            )
        version = config.product_class.get(_SCHEMA_VERSION)
        if version is None or not str(version).strip():
            raise BindingError(
                f"`product_class:` in {document.config} omits"
                f" `{_SCHEMA_VERSION}`, so there is no registered lane to ask"
                " against. The version is the deployment's to state and never"
                " the caller's — `WireRequest` carries none by `D-04`"
            )
        return _Declared(
            program=program,
            document=document,
            tenant=config.tenant_id,
            version=str(version),
        )

    @staticmethod
    async def _call(
        program: Path, root: Path, arguments: dict[str, object]
    ) -> str:
        """Spawn the server, call the tool once, and return what it said.

        The whole session lifetime is this coroutine's ``async with`` stack,
        which is :mod:`ccf.mcp.client`'s session-per-call rule obeyed rather
        than restated: the session is created, initialized, used and torn down
        inside one task, so no task group outlives the task that entered it.

        **The child runs under this interpreter, in this working directory,
        with this environment**, and all three are deliberate. A deployment's
        server program is the deployment's own code reaching the same SDK, the
        same substrate settings and the same credentials the client resolved;
        it is not a third-party server whose environment should be curated.

        The environment is passed explicitly because it would otherwise be
        **filtered**: ``mcp.client.stdio.get_default_environment()`` hands a
        child only ``HOME``, ``LOGNAME``, ``PATH``, ``SHELL``, ``TERM`` and
        ``USER``. That default is right for a server you did not write and
        wrong here, and getting it wrong is silent rather than loud — measured
        during this plan, a child stripped of ``PYTHONPATH`` imported a
        *different checkout's* ``ccf`` through the environment's editable
        install and answered every question perfectly, from code the client
        under test was not running.

        Raises:
            ccf.client.errors.TransportError: the program would not start, the
                pipe closed, the tool answered with an error, or it answered
                with something other than one piece of text.
        """
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(program), str(root)],
            env=dict(os.environ),
        )
        try:
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    answered = await session.call_tool(
                        PRODUCT_REQUEST_TOOL, arguments
                    )
        except asyncio.CancelledError:
            raise
        except Exception as unreachable:
            raise TransportError(
                f"the `{SCHEME}` server at {program} did not answer:"
                f" {type(unreachable).__name__}: {unreachable}"
            ) from unreachable

        spoken = [
            block.text
            for block in answered.content
            if isinstance(block, TextContent)
        ]
        if answered.isError:
            raise TransportError(
                f"the `{SCHEME}` server at {program} answered the product tool"
                f" with an error rather than an outcome — {' '.join(spoken)}."
                " A door that raises reaches a client as an error with the"
                " server's own wording in front of it, so there is no governed"
                " answer here to branch on; a refusal the fabric actually made"
                " arrives as a value inside the outcome"
            )
        if len(spoken) != 1:
            raise TransportError(
                f"the `{SCHEME}` server at {program} answered with"
                f" {len(spoken)} pieces of text where a door emits exactly one"
                " — the canonical bytes of its outcome, and never a second"
                " rendering beside them"
            )
        return spoken[0]

    @staticmethod
    def _decode(text: str, *, request: WireRequest) -> WireOutcome:
        """Re-shape the door's outcome as the one shape a client sees.

        Nothing is re-serialized and nothing is re-decided.
        :attr:`~ccf.products.door.DoorOutcome.product_json` is the producer's
        canonical **text**, so it crosses to
        :attr:`~ccf.client.wire.WireOutcome.product_json` unchanged and its
        address is ``sha256`` of exactly those bytes — the same one stdlib line
        the in-process adapter computes over the same rendering, which is why
        :func:`~ccf.client.codec.verify_content_address` can hold the two to
        each other. The refusal and the replay reference cross untouched.

        The address is computed here rather than carried because the door does
        not publish one: this surface has an envelope but no header, and an
        address carried *inside* the vessel would change the bytes it claims to
        describe (:func:`~ccf_runtime.http_api.routes.canonical_response`).

        Raises:
            ccf.client.errors.TransportError: the text is not a well-formed
                outcome. A malformed wire is a broken wire and never a refusal.
        """
        try:
            outcome = DoorOutcome.model_validate_json(text)
        except ValidationError as malformed:
            raise TransportError(
                f"the `{SCHEME}` server answered with bytes that are not a"
                " well-formed door outcome, so the wire carried no governed"
                " answer at all — a malformed wire is a broken wire and never a"
                " refusal"
            ) from malformed
        if outcome.product_json is None:
            return WireOutcome(
                request=request,
                product_json=None,
                content_address=None,
                replay_ref=None,
                refusal=outcome.refusal,
            )
        return WireOutcome(
            request=request,
            product_json=outcome.product_json,
            content_address=hashlib.sha256(
                outcome.product_json.encode("utf-8")
            ).hexdigest(),
            replay_ref=outcome.replay_ref,
            refusal=None,
        )


SCHEME_REGISTRY[SCHEME] = McpStdioAdapter
