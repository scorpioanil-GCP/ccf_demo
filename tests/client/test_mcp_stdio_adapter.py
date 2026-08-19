"""The `mcp+stdio` adapter — what it carries, and what it refuses to call an answer.

``D-07``/``D-10``/``D-15(d)``. The property under test is the one inversion the
whole client taxonomy exists to prevent: **a wire that never spoke must never
arrive as a governed "no".** Four ways this transport can fail to produce an
answer are exercised here, each failing at a different place — before the child
is launched, at the pipe, at the door, and in the bytes — and every one of them
raises :class:`~ccf.client.errors.TransportError` with **no**
:class:`~ccf.client.result.Result` produced at all.

**The refusal leg is what stops the other four proving nothing.** A transport
that raised on everything would pass every ``pytest.raises`` above it, so a
question the real deployment refuses is asserted to produce a *value* — a
refused ``Result``, no exception. Without that leg "it raises" is not evidence
of discrimination.

**The last leg guards a hazard this plan measured rather than imagined.**
``mcp.client.stdio`` hands a child a *filtered* environment by default — six
variables, ``PYTHONPATH`` not among them — so a child launched with it resolves
``ccf`` through whatever editable install the interpreter's environment points
at. In a worktree that is a **different checkout**, and it answers every
question perfectly while testing code the client under test is not running.

Every stub server below is a **real child process** speaking real MCP over real
pipes. None of them monkeypatches the adapter, and none substitutes an object
for the one the healthy path builds: the subject of every assertion is
:class:`~ccf.client.adapters.mcp_stdio.McpStdioAdapter` itself, damaged only in
the substrate it speaks to (``D-22``).
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

import ccf
from ccf.client.adapters.mcp_stdio import McpStdioAdapter
from ccf.client.client import ProductClient
from ccf.client.errors import BindingError, TransportError
from ccf.products.door import PRODUCT_REQUEST_TOOL

from ccf.client.adapters.binding_document import load_binding_document

from tests.client.conftest import FIXTURE_DEPLOYMENT, config_document, seed
from tests.client.fixtures import STDIO_SERVER, declare_server

pytestmark = pytest.mark.crossproc

#: The deployment's own documents, read once — never spelled (CLAUDE.md §6.4).
_CONFIG = config_document(FIXTURE_DEPLOYMENT)
PRODUCT_ID = str(_CONFIG["product_class"]["schema_name"])
PARAMETER = str(_CONFIG["request_contract"]["arguments"]["required"][0])

#: A pinned instant, so nothing here depends on when it ran.
PINNED = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)

#: A stub MCP server answering the product tool with ``BODY``. The eight
#: arguments are declared because the shipped tool declares them: a stub with a
#: narrower signature would be answering a different call than the real door.
_STUB = '''
from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

server = FastMCP("stub")


@server.tool(name="{tool}", description="stub")
def answer(
    tenant: str,
    product_class: str,
    version: str,
    subject: str,
    intent: str,
    freshness: str,
    asked_at: datetime,
    parameters: dict[str, Any] | None = None,
) -> str:
    {body}


server.run(transport="stdio")
'''


def _root(
    tmp_path: Path,
    name: str,
    *,
    populated: bool = False,
    program: Path | None = None,
) -> Path:
    """A private, data-only copy of the committed fixture deployment.

    When ``program`` is given it is copied into the copied root's **parent**
    and declared, because that is where ``binding.yaml``'s ``server:`` key
    resolves (``D-10``). The committed fixture ships that relationship; a copy
    that took only ``deployment/`` would inherit a declaration pointing at
    nothing, and every leg here would then fail for a reason no test is about.

    ``program`` defaults to ``None`` for exactly one caller — the test about an
    address naming a program that is not there, whose subject *is* a
    declaration that resolves nowhere.
    """
    root = tmp_path / name / "deployment"
    shutil.copytree(FIXTURE_DEPLOYMENT, root)
    if program is not None:
        shutil.copy2(program, root.parent)
        declare_server(root, root.parent / program.name)
    if populated:
        seed(root)
    return root


def _stub_program(tmp_path: Path, name: str, body: str) -> Path:
    """A stub server program, beside the deployment and never inside it."""
    program = tmp_path / name / "stub_server.py"
    program.parent.mkdir(parents=True, exist_ok=True)
    program.write_text(
        _STUB.format(tool=PRODUCT_REQUEST_TOOL, body=body), encoding="utf-8"
    )
    return program


def _ask(root: Path, parameters: dict[str, object] | None = None) -> object:
    """Ask through a real `mcp+stdio` client, at the client seam.

    The root alone, because that is the whole address (``D-05``). Which program
    the child runs is the copied deployment's own declaration, written by
    :func:`~tests.client.fixtures.declare_server` through ``_root``.
    """
    return ProductClient(
        product_id=PRODUCT_ID, adapter=McpStdioAdapter(str(root))
    ).ask(
        parameters={PARAMETER: 11} if parameters is None else parameters,
        as_of=PINNED,
    )


def test_a_provisioned_root_declares_a_server_that_actually_resolves(
    tmp_path: Path,
) -> None:
    """`T-18.1-13` — the provisioning site hands out a root that RESOLVES.

    A site left unprovisioned hands out a deployment whose `server:` points at
    nothing. Nothing reads that value yet, so the omission would sit here
    silently until the grammar flip in `18.1-02`, at which point the healthy
    leg below breaks — and a broken healthy leg cannot be told apart from
    `D-06`'s key-absent refusal, so that control would pass for the wrong
    reason. Asserted now, while the two are still distinguishable.
    """
    root = _root(tmp_path, "declared", program=STDIO_SERVER)

    document = load_binding_document(root)

    assert document.server is not None
    assert document.server.is_file(), "the declaration names a program that is there"
    assert document.server.parent == root.parent.resolve(), (
        "and it sits in the copied root's PARENT, which is where `server:` looks"
    )


def test_a_root_provisioned_with_no_program_declares_one_that_is_not_there(
    tmp_path: Path,
) -> None:
    """The DELIBERATE exception, kept rather than lost.

    ``test_a_declaration_naming_no_program_raises_before_anything_is_launched``
    below is about a program that is missing, so its root must keep a
    declaration that resolves nowhere. Provisioning every root uniformly would
    have quietly deleted that test's subject.
    """
    document = load_binding_document(_root(tmp_path, "absent-declared"))

    assert document.server is not None, "the committed fixture's value is inherited"
    assert not document.server.exists(), "and there is deliberately nothing there"


def test_a_declaration_naming_no_program_raises_before_anything_is_launched(
    tmp_path: Path,
) -> None:
    """Failure mode 1 — there is nothing to start, so nothing was ever asked.

    The missing program is now named by the **document** rather than by the
    address: ``_root`` is called with no ``program``, so the copied deployment
    inherits ``server: stdio_server.py`` and that value resolves nowhere. The
    failure mode is the one this leg has always covered; what moved is who
    stated the path that turned out to be wrong.
    """
    root = _root(tmp_path, "absent")
    with pytest.raises(BindingError) as refused:
        _ask(root)
    assert "names no server program" in str(refused.value)
    # A `BindingError` is a `TransportError` by inheritance, so the one clause a
    # caller writes for *the wire never spoke* covers this too.
    assert isinstance(refused.value, TransportError)


def test_a_server_that_exits_at_once_raises_rather_than_refusing(
    tmp_path: Path,
) -> None:
    """Failure mode 2 — the child dies and the pipe closes mid-handshake."""
    program = _stub_program(tmp_path, "exits", "")
    program.write_text("raise SystemExit(1)\n", encoding="utf-8")
    with pytest.raises(TransportError) as refused:
        _ask(_root(tmp_path, "exits-root", program=program))
    assert "did not answer" in str(refused.value)


def test_a_door_that_raises_arrives_as_a_broken_wire_and_not_as_a_no(
    tmp_path: Path,
) -> None:
    """Failure mode 3 — the tool answered ``isError``, which is not a verdict.

    This is the shape a **governance** refusal takes on this wire: the shipped
    door raises ``ProductEntitlementRefused`` by ruling (``D-IMPL-148``
    Addendum A), and FastMCP delivers a raised tool exception as ``isError``
    with its own prose in front of it. A client reading that as a refusal would
    be string-parsing a server's wording for an audited verdict, so it is
    reported as what it is: no governed answer arrived.
    """
    program = _stub_program(
        tmp_path, "raises", 'raise RuntimeError("the door raised")'
    )
    with pytest.raises(TransportError) as refused:
        _ask(_root(tmp_path, "raises-root", program=program))
    assert "error rather than an outcome" in str(refused.value)


def test_a_server_answering_something_other_than_an_outcome_raises(
    tmp_path: Path,
) -> None:
    """Failure mode 4 — well-formed transport, bytes that are not an outcome.

    A malformed wire is a broken wire. Converting it into a refusal is the
    ``except Exception: return refusal`` inversion :mod:`ccf.client.errors`
    exists to forbid, and it is unrecoverable downstream because both shapes
    look well-formed to everything that reads them.
    """
    program = _stub_program(tmp_path, "garbage", 'return "{}"')
    with pytest.raises(TransportError) as refused:
        _ask(_root(tmp_path, "garbage-root", program=program))
    assert "never a refusal" in str(refused.value)


def test_a_governed_refusal_is_a_value_and_does_not_raise(tmp_path: Path) -> None:
    """The non-vacuity leg: a transport that raised on everything fails here.

    The refusal is produced by the **real** deployment through the **real**
    door — the fixture class declares its parameter required, so a question
    omitting it is refused before the graph is touched. Nothing is stubbed,
    which is what makes this a statement about the shipped path.
    """
    result = _ask(
        _root(tmp_path, "refuses", populated=True, program=STDIO_SERVER),
        parameters={},
    )
    assert result.refused
    assert result.refusal is not None
    assert result.refusal.reason


def test_the_child_resolves_the_same_ccf_this_client_is_running(
    tmp_path: Path,
) -> None:
    """The environment reaches the child, and a stripped one is caught here.

    ``mcp.client.stdio``'s default environment is six variables and
    ``PYTHONPATH`` is not among them, so a child launched with it resolves
    ``ccf`` through the interpreter's editable install — which in a worktree is
    **another checkout**, answering every question correctly from code under
    test by nobody. Measured during plan ``17-10``; asserted here so it stays
    measured.

    :meth:`~ccf.client.adapters.mcp_stdio.McpStdioAdapter._call` is driven
    directly because it returns the server's raw text: the check needs a fact
    about the child rather than a governed answer, and routing it through the
    decoder would only prove the text is not an outcome.
    """
    program = _stub_program(
        tmp_path, "where", "import ccf\n    return ccf.__file__"
    )
    spoken = asyncio.run(
        McpStdioAdapter._call(
            program,
            _root(tmp_path, "where-root", program=program),
            {
                "tenant": "t",
                "product_class": PRODUCT_ID,
                "version": "1.0.0",
                "subject": "s",
                "intent": "i",
                "freshness": "f",
                "asked_at": PINNED.isoformat(),
                "parameters": {},
            },
        )
    )
    assert Path(spoken).resolve() == Path(ccf.__file__).resolve()
