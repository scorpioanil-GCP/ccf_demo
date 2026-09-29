"""The second wire — a real process boundary, spoken over MCP stdio.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§3 (``D-06``), §5 (``D-11``, ``D-12``) and §9 (``D-24``). Framed by CLAUDE.md
§7.1: MCP is the SDK's own bidirectional integration surface, so a client
reaching a deployment through it is the egress role read from the far side.

What the address names: the deployment, and nothing else
---------------------------------------------------------
``mcp+stdio:<root>`` — one token, the deployment root, parsed with
:func:`shlex.split` so a path containing a space can still be quoted. The
program this transport launches is **not** in the address and cannot be put
there:

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
  is the deployment's — which is why the *deployment* declares it, under
  ``server:`` in its own ``binding.yaml``, and this module launches it without
  knowing what is in it.
* **Where that program sits is the deployment's business, not the address's.**
  ``server:`` resolves against the directory *holding* the deployment
  (``D-10``), and a deployment reached at an endpoint rather than launched
  declares no ``server:`` at all. The address carried the program until
  ``18.1-02``; it read as the *client's* business at exactly the point a
  reader was learning what a client does, and it is not.

Four ways of getting this wrong are refused **by name** rather than
half-resolved — a second token, an unquoted path whose spaces the parser reads
as several tokens, a token that resolves to a program, and a deployment that
declares no ``server:`` — because each is an ordinary authoring mistake and each
is cheaper to diagnose here than as a missing document two layers down. The
whitespace case is separated from the second-token case by asking whether the
whole address names a directory that exists, because the two are identical by
token count and the second-token advice — drop it — would destroy a real path.

What is asked, and where each argument comes from
--------------------------------------------------
:data:`~ccf.products.door.PRODUCT_REQUEST_TOOL` takes nine arguments and a
:class:`~ccf.client.wire.WireRequest` carries three, which is not a mismatch to
paper over — it is the ``D-04`` boundary showing through. The client's question
is *what class, which parameters, as of when*; the rest is the deployment's own
vocabulary, and the in-process adapter reads exactly the same values from
exactly the same two documents:

===================  =========================================================
Tool argument        Where it comes from
===================  =========================================================
``product_class``    the caller's ``WireRequest.product_id``
``request``          the caller's whole ``WireRequest``, canonically encoded.
                     The door parses **this** and echoes what it parsed, so
                     the echo is the producer's statement rather than a value
                     re-sourced from client state (``C-01``). Required, and
                     cross-checked at the door against ``product_class``,
                     ``parameters`` and — when it carries a concrete boundary
                     — ``asked_at`` (``C-16``, ``C-18``)
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

**Amended by ``C-05``/``C-06``/``C-08`` (Phase 19), and the sentence above is
kept because what it was defending is now stronger.** This module builds no
:class:`~ccf.client.wire.WireOutcome` **either**: :meth:`McpStdioAdapter.ask`
returns the door's own text encoded to ``bytes``, and the private ``_decode``
that used to turn it into an outcome object is **deleted**. The point is the
absence of a transcoding step, not its correctness — a transcoding step is
exactly where an adapter re-sources the echo from client state, which is what
``D-IMPL-151`` finding ``B0`` measured. What this adapter can build has gone
from *one shape* to *nothing*, so "shape identity across transports is a code
path this adapter cannot avoid" is now a property of the seam's type.

This module is algorithmic (CINV-03): it launches a process, exchanges typed
messages and re-shapes an outcome. No LLM dependency on this path, ever.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import sys
from dataclasses import dataclass
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from ccf.client.adapters.binding_document import (
    BINDING_DOCUMENT_NAME,
    BindingDocument,
    load_binding_document,
)
from ccf.client.binding import SCHEME_REGISTRY
from ccf.client.errors import BindingError, TransportError

#: The fabric's own clock, IMPORTED rather than restated — the same rule the
#: in-process adapter states: one right value, and it lives in the resolver.
from ccf.products.resolver import _utc_now as _FABRIC_CLOCK
from ccf.client.wire import WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import DEPLOYMENT_CONFIG, DeploymentConfig
from ccf.controlplane.artifacts import load_artifact as load_control_plane_artifact
from ccf.products.door import PRODUCT_REQUEST_TOOL

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
            path to the deployment root, and nothing else. Not resolved here:
            resolution happens on :meth:`ask`, so a client constructed against
            a deployment that does not exist yet fails when it asks rather than
            when it is built, which is the posture
            :class:`~ccf.client.adapters.inprocess.InProcessAdapter` already
            takes for a root.
    """

    __slots__ = ("_address", "_clock")

    def __init__(
        self, address: str, *, clock: Callable[[], datetime] = _FABRIC_CLOCK
    ) -> None:
        """Point at ``address``; ``clock`` is this composition's fabric clock.

        `D-IMPL-358` step 5 section H. The same seam
        :class:`~ccf.client.adapters.inprocess.InProcessAdapter` carries, and for
        the same reason: this adapter resolves ``as_of=None`` client-side, so an
        ambient read here would leave `asked_at` live while a pinned deployment
        served at its own instant. The default is the fabric's own clock, so
        nothing that does not care is affected.

        The clock does NOT cross to the child process — the child composes its
        own, and a deployment that needs the two to agree says so in the program
        it ships. What this governs is the instant this CLIENT resolves.
        """
        self._address = address
        self._clock = clock

    def ask(self, request: WireRequest) -> bytes:
        """Launch the deployment's server, ask it one question, and carry its bytes.

        Nothing is re-shaped here (``C-06``, Phase 19). The door's text crosses
        to the client encoded and **unexamined** — the UTF-8 of it and nothing
        else — because a transcoding step is precisely where an adapter can
        re-source the echo from client state rather than from the wire. The
        wire between the door and this adapter stays *text* because raw bytes
        cannot be an MCP tool result without base64, and a base64 envelope
        would be a second rendering of the vessel; encoding text this adapter
        never inspects is a pass-through, not a transcoding.

        Raises:
            ccf.client.errors.BindingError: the address is not one token, it
                names a program rather than a root, or the deployment it names
                declares no usable server program. A
                :class:`~ccf.client.errors.TransportError` by inheritance, so
                one ``except`` clause still covers every way the wire never
                spoke.
            ccf.client.errors.TransportError: the program would not start, the
                pipe closed, or the tool answered with an error rather than an
                outcome. Whether what came back is a **well-formed** outcome is
                no longer decided here: it is decided by
                :func:`~ccf.client.codec.decode_outcome` at the client, which is
                where the check belongs once this adapter no longer parses.
        """
        declared = self._declared()
        question = declared.document.question
        arguments: dict[str, object] = {
            "tenant": declared.tenant,
            "product_class": request.product_id,
            "version": declared.version,
            # The caller's own question, canonically encoded. The door parses
            # this and echoes what it parsed (`C-01`), which is what gives the
            # decoder's cross-check an operand that did not come from here.
            "request": canonical_bytes(request).decode("utf-8"),
            "subject": question.subject,
            "intent": question.intent,
            "freshness": question.freshness,
            # `D-04`: `None` is the positive assertion *answer against the
            # decision instant*, and the in-process adapter resolves it the
            # same way and in the same place. Resolving it here rather than
            # leaving the argument out is forced by the tool's own shape —
            # all four §6.3 axes are required, which makes a partial address
            # unrepresentable rather than merely refused.
            # `D-IMPL-358` step 5 section H: this composition's clock, not an
            # ambient read — see the constructor.
            "asked_at": (
                request.temporal_boundary or self._clock()
            ).isoformat(),
            # Verbatim, exactly as the door forwards them: MCP carries tool
            # arguments as JSON, so `D-IMPL-103`'s one level of declared
            # nesting crosses intact and there is nothing to coerce. The
            # declared world is closed at the resolver (`D-IMPL-121`).
            "parameters": dict(request.parameters),
        }
        return asyncio.run(
            self._call(declared.program, declared.document.root, arguments)
        ).encode("utf-8")

    def _declared(self) -> _Declared:
        """Read the deployment the address names, and the program it declares.

        The address is **one** token and the program is not in it: where the
        program sits is decided once, by the deployment, under ``server:`` in
        its own ``binding.yaml`` (``D-05``, ``D-10``). Each way of getting that
        wrong is refused **by name** rather than half-resolved, because each is
        an ordinary authoring mistake and a report about a *missing document*
        two layers down would describe something other than the mistake made.

        **The order of the branches is load-bearing.** Every targeted refusal
        fires before
        :func:`~ccf.client.adapters.binding_document.load_binding_document` is
        given the chance to answer — otherwise a token naming a program would be
        reported as a root that is not a directory (``D-08``). A token naming
        nothing at all is left to fall through, because that report is then the
        right one. Inside the wrong-count group the whitespace check comes
        first, because a count of two is what an unquoted spaced path and the
        pre-migration address have in common and only the filesystem tells them
        apart.
        """
        try:
            tokens = shlex.split(self._address)
        except ValueError as unparsable:
            raise BindingError(
                f"`{self._address}` is not a usable `{SCHEME}` address —"
                f" {unparsable}. It is the deployment root, one token, quoted if"
                " it contains a space"
            ) from unparsable
        if len(tokens) != 1:
            # A path containing whitespace is ONE token the parser cannot see
            # as one, and by token COUNT alone it is indistinguishable from the
            # pre-migration two-token address. So ask the filesystem before
            # concluding which mistake was made: an address naming a directory
            # that is *there* is a root that needed quoting, never a program
            # plus a root — and the migration's advice, drop the second token,
            # would hand back `mcp+stdio:/tmp/My` and destroy the path the
            # adopter typed. Spaces in paths are ordinary on macOS and Windows,
            # so this is not an exotic case, and a refusal naming the wrong
            # mistake is the `B0b` report-quality class `D-08` cites.
            #
            # `os.path.isdir` rather than `Path.is_dir` deliberately: it answers
            # False for a string the platform cannot use instead of raising, and
            # a grammar branch must not become a new way out of `BindingError`.
            # The emptiness guard is load-bearing too — `Path("")` is `Path(".")`,
            # which is a directory, so a blank address would otherwise be told
            # to quote the current working directory.
            written = self._address.strip()
            if written and os.path.isdir(os.path.expanduser(written)):
                raise BindingError(
                    f"`{self._address}` parses as {len(tokens)} tokens because"
                    " it contains whitespace, and it names one directory that"
                    f" exists. An `{SCHEME}` address is a single token — the"
                    " deployment root — so quote the path rather than dropping"
                    f" part of it: `{SCHEME}:'{written}'`. This is not the"
                    " pre-`18.1-02` address, whose second token was a server"
                    " program; there is nothing here to drop"
                )
            if len(tokens) == 2:
                raise BindingError(
                    f"`{self._address}` states two tokens; an `{SCHEME}` address"
                    " states one — the deployment root, as in"
                    f" `{SCHEME}:./deployment`. If that is one path containing a"
                    f" space, quote it: `{SCHEME}:'/path/with a"
                    " space/deployment'`. Otherwise the second token was the"
                    " server program, and that program is now the deployment's"
                    f" own `server:` key in its `{BINDING_DOCUMENT_NAME}`, so"
                    " drop it from the address and name the root alone"
                )
            raise BindingError(
                f"`{self._address}` states {len(tokens)} tokens; an `{SCHEME}`"
                " address states exactly one — the deployment root, as in"
                f" `{SCHEME}:./deployment`, quoted if its path contains a space."
                " The program to launch is the deployment's, declared under"
                f" `server:` in its `{BINDING_DOCUMENT_NAME}`, because the SDK"
                " ships no server program and cannot"
            )
        resolved = Path(tokens[0]).expanduser().resolve()
        if resolved.is_file():
            raise BindingError(
                f"`{tokens[0]}` names a program — it resolves to {resolved},"
                f" which is a file. An `{SCHEME}` address names the deployment"
                " root that declares the program, never the program itself, and"
                " the program is that deployment's `server:` key in its"
                f" `{BINDING_DOCUMENT_NAME}`"
            )
        document = load_binding_document(tokens[0])
        if document.server is None:
            raise BindingError(
                f"{document.root / BINDING_DOCUMENT_NAME} declares no `server:`,"
                " so this deployment states no program to launch and cannot be"
                f" reached over `{SCHEME}`. Add `server:` naming its MCP server"
                " program, relative to the directory holding this deployment."
                " The key is optional because a deployment reached in process"
                " launches nothing and one reached at an endpoint is already"
                " running — the requirement belongs to this transport rather"
                " than to the document"
            )
        if not document.server.is_file():
            raise BindingError(
                f"`server:` in {document.root / BINDING_DOCUMENT_NAME} names no"
                f" server program — it resolves to {document.server}, which is"
                f" not a file. An `{SCHEME}` binding launches the deployment's"
                " own MCP server program, because the SDK ships none and cannot"
            )
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
            program=document.server,
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


SCHEME_REGISTRY[SCHEME] = McpStdioAdapter
