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
the substrate it speaks to (``D-22``). The grammar controls at the foot of the
file reach that same adapter through ``CCF_BINDING`` and
:meth:`~ccf.client.client.ProductClient.for_product` — the environment is the
only door ``D-04`` leaves open, and ``monkeypatch.setenv`` sets a variable
rather than patching anything, so the sentence above still holds of them.

**The second taxonomy, added by ``18.1-02``.** Since ``D-05`` an ``mcp+stdio``
address is one token and the program comes from the deployment's own
``server:``, which gives an adopter six new ways to be wrong. Each is refused
by a message naming *that* mistake, the six are asserted pairwise distinct, and
a healthy ask runs through the identical harness — because six refusals
measured against a baseline that refuses everything measure nothing.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

import ccf
from ccf.client.adapters.mcp_stdio import SCHEME, McpStdioAdapter
from ccf.client.binding import SCHEME_REGISTRY
from tests.client.fixtures import SERVED_AT_ENV
from ccf.client.client import ProductClient
from ccf.client.errors import BindingError, TransportError
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import PRODUCT_REQUEST_TOOL, WireRequest

from ccf.client.adapters.binding_document import (
    BINDING_DOCUMENT_NAME,
    load_binding_document,
)

from tests.client.conftest import FIXTURE_DEPLOYMENT, config_document, seed
from tests.client.fixtures import STDIO_SERVER, declare_server

pytestmark = pytest.mark.crossproc

#: The deployment's own documents, read once — never spelled (CLAUDE.md §6.4).
_CONFIG = config_document(FIXTURE_DEPLOYMENT)
PRODUCT_ID = str(_CONFIG["product_class"]["schema_name"])
PARAMETER = str(_CONFIG["request_contract"]["arguments"]["required"][0])

#: A pinned instant, so nothing here depends on when it ran.
PINNED = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _compose_against_the_pinned_instant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every adapter this module resolves through the registry reads :data:`PINNED`.

    `D-IMPL-358` step 5 section H. Three legs here reach a client through
    `CCF_BINDING` rather than by handing one an adapter, so the registry is where
    their composition happens. Without the pin they ask at `PINNED` and serve at
    the real clock, and Gate 3 — which measures its window from the moment of
    service — refuses a March-anchored product today.
    """
    monkeypatch.setitem(
        SCHEME_REGISTRY,
        SCHEME,
        lambda address: McpStdioAdapter(address, clock=lambda: PINNED),
    )
    # And the CHILD, which is where the serving actually happens. The client's
    # clock governs only its own `as_of=None` read; the instant a separate
    # process serves at is that process's own, so it crosses through the
    # environment — the one channel a child inherits, and the same one the
    # conformance package exports.
    monkeypatch.setenv(SERVED_AT_ENV, PINNED.isoformat())

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
    # Accepted and ignored. `C-16` made the encoded question a required tool
    # argument, and a stub whose signature omitted it would be a stub the real
    # adapter could not call — these programs exist to return malformed text,
    # and what the adapter does with malformed text is unchanged.
    request: str,
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
        product_id=PRODUCT_ID,
        # `D-IMPL-358` step 5 section H: composed against this module's own
        # pinned instant, so `as_of=PINNED` and the serving instant agree. A
        # product anchored on a pinned March decision cannot be served today.
        adapter=McpStdioAdapter(str(root), clock=lambda: PINNED),
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
                # Required since `C-16`. This leg drives `_call` directly to
                # read the child's own `ccf.__file__`, so the stub never looks
                # at it — but the tool signature it must satisfy does.
                "request": canonical_bytes(
                    WireRequest(
                        product_id=PRODUCT_ID,
                        parameters={},
                        temporal_boundary=None,
                    )
                ).decode("utf-8"),
                "subject": "s",
                "intent": "i",
                "freshness": "f",
                "asked_at": PINNED.isoformat(),
                "parameters": {},
            },
        )
    )
    assert Path(spoken).resolve() == Path(ccf.__file__).resolve()


# ---------------------------------------------------------------------------
# The grammar, and the six ways an adopter can get it wrong.
#
# `D-05` made the address one token; `D-06`, `D-07` and `D-08` gave the three
# ways of missing that a refusal that names the mistake, and the close review of
# this phase added a fourth — an unquoted path whose spaces the parser reads as
# two tokens, which `D-07`'s branch used to answer with advice that destroyed it. Every control below is
# driven END TO END — `CCF_BINDING` in the environment, `ProductClient.for_product`,
# `.ask` — and not one of them reaches into the adapter's private declaration
# helper. A refusal that fires in a loader and is never reached by a client is a
# gate wired to nothing, which is the defect this project has now met seven
# times.
# ---------------------------------------------------------------------------

#: The address the example's README documented **before** `18.1-02`, verbatim
#: but for the scheme, which is interpolated where it is used rather than
#: spelled (`SCHEME`'s own comment: written once, so the registry entry, the
#: refusal messages and the tests all say the same string). The migration branch
#: is measured against the string an adopter would actually have typed — a
#: control inventing its own two-token string would be measuring an invented
#: mistake rather than the one being migrated away from.
PRE_MIGRATION_REMAINDER = (
    "examples/hw1-companies-over-revenue/server/serve.py"
    " examples/hw1-companies-over-revenue/deployment"
)

#: The clause each grammar refusal owns — the words that name *that* mistake
#: and no other. Held in one place because both the individual controls and the
#: distinctness leg below assert against it, and two copies would be two places
#: the message's contract is decided.
#:
#: **Distinctness is asserted over these phrases, not over whole messages, and
#: that is a measured correction rather than a stylistic one.** Every refusal
#: interpolates the offending address, so two branches emitting *byte-identical
#: template text* still render differently — measured during this plan by giving
#: the two-token branch the generic branch's message verbatim, at which point a
#: whole-message `len(set(...)) == len(...)` leg still passed. A check that
#: cannot fail is worse than no check. What must be distinct is the clause that
#: names the mistake, so the leg asserts each phrase appears in **exactly one**
#: of the six.
SIGNATURES: dict[str, str] = {
    "D-06 — the deployment declares no `server:`": "declares no `server:`",
    "D-07 — the pre-migration two-token address": "states two tokens",
    "D-08 — the token resolves to a program": "names a program",
    "an unquoted path containing whitespace": "names one directory that exists",
    "the generic wrong token count": "states exactly one",
    "the declared program is not there": "names no server program",
}

#: The advice `D-07` gives, quoted from the shipped message because the control
#: below asserts its **ABSENCE**. A spaced path told to drop a token loses the
#: half of itself after the space, so this phrase appearing in the whitespace
#: refusal is the defect, not a wording preference.
TOKEN_DROPPING_ADVICE = "drop it from the address"

#: `load_binding_document`'s fall-through report for a root it cannot find a
#: document in. Quoted from the shipped message rather than paraphrased, because
#: V-10 asserts its ABSENCE and a paraphrase would make that assertion pass on a
#: message that still says it.
FALL_THROUGH = f"carries no `{BINDING_DOCUMENT_NAME}`"

#: The other fall-through, and the one a token naming a program would actually
#: have reached: `load_binding_document` reports a root that is not a directory
#: before it ever looks for a document. `D-08` exists to fire first.
NOT_A_DIRECTORY = "is not a deployment root"


def _body(root: Path) -> dict[str, Any]:
    """The copied deployment's binding document, as a mutable mapping."""
    return dict(
        yaml.safe_load((root / BINDING_DOCUMENT_NAME).read_text(encoding="utf-8"))
    )


def _rewrite(root: Path, body: dict[str, Any]) -> None:
    """Put a doctored document back, so the loader reads what the control meant."""
    (root / BINDING_DOCUMENT_NAME).write_text(
        yaml.safe_dump(body), encoding="utf-8"
    )


def _without_a_server(tmp_path: Path, name: str) -> Path:
    """A copied deployment whose `server:` key has been DELETED.

    Deleted rather than never-written: the committed fixture declares one, so a
    control that simply used a deployment without the key would be asserting
    against a fixture nobody doctored. The pop is asserted to have removed
    something — the sabotage-control idiom, applied to the control itself, so a
    fixture that quietly stopped declaring a server cannot make this pass for
    the wrong reason.
    """
    root = _root(tmp_path, name, program=STDIO_SERVER)
    body = _body(root)
    assert body.pop("server", None) is not None, (
        "the copied deployment declared no `server:` to delete, so this control"
        " would refuse for the very reason it exists to distinguish from"
    )
    _rewrite(root, body)
    assert _body(root).get("server") is None, "the doctoring did not take"
    return root


def _refusal_message() -> str:
    """Ask at the client seam, and return the refusal an adopter would read.

    ``CCF_BINDING`` is already in the environment when this is called. The
    environment rather than ``binding=`` on purpose: ``D-04`` makes the scheme
    prefix the only place a transport is named and puts it in the environment,
    so a control that passed the address in code would be exercising a path an
    adopter does not take.
    """
    with pytest.raises(BindingError) as refused:
        ProductClient.for_product(PRODUCT_ID).ask(
            parameters={PARAMETER: 11}, as_of=PINNED
        )
    return str(refused.value)


def test_a_deployment_declaring_no_server_is_refused_and_the_transport_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`D-06` / V-07 — the key the loader leaves optional, this transport requires.

    The loader cannot know which transport is asking and an in-process
    deployment will never declare one, so `server:` stays optional there and the
    requirement lands here. The message therefore has to name the transport, or
    an adopter reads it as a document that is simply malformed.
    """
    root = _without_a_server(tmp_path, "no-server")
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{root}")

    message = _refusal_message()

    assert SCHEME in message, "the refusal does not name the transport asking"
    assert "`server:`" in message, "nor the key to add"
    assert SIGNATURES["D-06 — the deployment declares no `server:`"] in message


def test_the_pre_migration_two_token_address_is_refused_with_the_migration(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """`D-07` / V-08 — the permanent migration branch, on the real old string.

    The address is the one the example's README documented the day before this
    phase, so what is measured is the migration an adopter is actually making.
    """
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{PRE_MIGRATION_REMAINDER}")

    message = _refusal_message()

    assert SIGNATURES["D-07 — the pre-migration two-token address"] in message
    assert TOKEN_DROPPING_ADVICE in message, (
        "the message names the count but not the migration, which leaves an"
        " adopter guessing where the program went"
    )
    assert "`server:`" in message
    assert SIGNATURES["an unquoted path containing whitespace"] not in message, (
        "the whitespace branch added by the close review swallowed the genuine"
        " migration — an adopter moving off the two-token grammar must still be"
        " told where their program went, so the filesystem check must not"
        " capture an address whose first token is a program"
    )


def test_a_root_path_containing_a_space_is_not_told_to_drop_a_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`18.1-CLOSE-REVIEWS` finding 2 — the refusal that named the wrong mistake.

    A deployment root under a directory whose name has a space parses as two
    tokens, and by COUNT alone it is the pre-migration address. It used to land
    in `D-07`'s branch and be told *"drop it from the address and name the root
    alone"*, which turns `/tmp/My Deployments/deployment` into `/tmp/My` — the
    adopter is handed something strictly worse than what they typed. Spaces in
    paths are ordinary on macOS and Windows, and the module docstring has said
    since `18.1-02` that quoting is the remedy, but no message an adopter reads
    said so.

    This is the `B0b` report-quality class in the phase whose own `D-08` cites
    it. The absence assertion is the load-bearing one: a message that merely
    *adds* quoting advice while keeping the token-dropping sentence has not
    fixed anything, because the destructive instruction is still on the screen.
    """
    root = _root(tmp_path, "My Deployments", program=STDIO_SERVER)
    assert " " in str(root), "the control is not exercising a spaced path at all"
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{root}")

    message = _refusal_message()

    assert SIGNATURES["an unquoted path containing whitespace"] in message
    assert TOKEN_DROPPING_ADVICE not in message, (
        "the spaced path is still being told to drop a token, which deletes"
        f" everything after the space: {message}"
    )
    assert SIGNATURES["D-07 — the pre-migration two-token address"] not in message, (
        "and it is still being diagnosed as the pre-migration address, which is"
        " a mistake this adopter did not make"
    )
    assert f"`{SCHEME}:'{root}'`" in message, (
        "the remedy is shown, whole and quoted, rather than described — a"
        " refusal that says `quote it` without spelling the string leaves the"
        " adopter to guess which half needed the quotes"
    )


def test_the_quoting_the_spaced_refusal_prescribes_actually_gets_past_the_grammar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The non-vacuity leg for the remedy — advice nobody ran is a guess.

    The refusal above tells an adopter to quote the path. If quoting did not in
    fact carry a spaced root through :func:`shlex.split` and into the loader,
    the message would be sending them somewhere no better than the token-drop
    it replaced. So the quoted form is driven through the same client seam and
    asserted to answer a real question.
    """
    root = _root(tmp_path, "My Deployments", populated=True, program=STDIO_SERVER)
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:'{root}'")

    result = ProductClient.for_product(PRODUCT_ID).ask(
        parameters={PARAMETER: 11}, as_of=PINNED
    )

    assert not result.refused, "the quoted spaced root did not reach the door"
    assert result.content_address, (
        "and a served result carries the content address, so what the quoted"
        " form reached was a real assembly rather than an empty pass"
    )


def test_a_token_resolving_to_a_program_is_refused_by_the_mistake_it_names(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """`D-08` / V-09 and V-10 — the half-migration, told what it actually did.

    One token that resolves to a **file** is the shape an adopter reaches by
    deleting the wrong half of the old address. Refused here rather than two
    layers down, and V-10 asserts the two fall-through reports are absent: a
    message describing a missing document, or a root that is not a directory,
    would describe something other than the mistake made. That is the `B0b`
    class, in the phase whose own `D-08` cites it.
    """
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{STDIO_SERVER}")

    message = _refusal_message()

    assert SIGNATURES["D-08 — the token resolves to a program"] in message
    assert "deployment root" in message
    assert FALL_THROUGH not in message, (
        f"the refusal fell through to `{FALL_THROUGH}` — `D-08` exists precisely"
        " to keep a missing-document report from standing in for a program in"
        f" the address: {message}"
    )
    assert NOT_A_DIRECTORY not in message, (
        f"the refusal fell through to `{NOT_A_DIRECTORY}`, which is the report a"
        " token naming NOTHING should get and is the wrong one for a token"
        f" naming a program: {message}"
    )


def test_any_other_token_count_is_refused_with_the_shape_it_wanted(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The generic branch — and it shows the shape rather than naming it."""
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:a b c")

    message = _refusal_message()

    assert SIGNATURES["the generic wrong token count"] in message
    assert "deployment root" in message
    assert f"`{SCHEME}:./deployment`" in message, (
        "the message names the shape it wanted without showing it, which"
        " `tests/client/test_binding.py` refuses by name for the sibling refusal"
    )


def test_a_declared_program_that_is_not_there_names_the_key_and_the_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The relocated existence check — the same failure, a different author.

    Before `18.1-02` a missing program was named by the address. It is now named
    by the document, so the refusal names the key and the file that states it
    rather than a token the adopter typed.
    """
    root = _root(tmp_path, "declared-nowhere")
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{root}")

    message = _refusal_message()

    assert SIGNATURES["the declared program is not there"] in message
    assert "`server:`" in message
    assert BINDING_DOCUMENT_NAME in message, (
        "the refusal does not say which document declared the path that is"
        " wrong, which is the whole of what moved when the declaration did"
    )


def test_the_same_harness_completes_a_real_ask_over_a_healthy_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**V-06 / V-12 — the non-vacuity leg for the taxonomy above.**

    Six refusals measured against a baseline that refuses everything measure
    nothing, and `D-06`'s deleted-key control in particular would then be
    indistinguishable from a broken harness. So the identical harness — same
    environment variable, same `for_product`, same `.ask` — is asserted to
    complete a real ask over a healthy one-token address and produce a governed
    **value**. The question omits the fixture class's required parameter, so the
    shipped door refuses it before the graph is touched: a `Result`, not a
    raise.
    """
    root = _root(tmp_path, "answers", populated=True, program=STDIO_SERVER)
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{root}")

    result = ProductClient.for_product(PRODUCT_ID).ask(parameters={}, as_of=PINNED)

    assert result.refused
    assert result.refusal is not None
    assert result.refusal.reason


def test_the_six_grammar_refusals_are_six_different_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`V-11` / CLNT-12 — one copy-pasted message would pass every control above.

    Each control asserts the clause its own message owns, and a single generic
    refusal carrying all six clauses would satisfy all six. So each clause is
    asserted to appear in **exactly one** of the six, which catches both
    collapses: a phrase in two messages (one branch copy-pasted onto another)
    and a phrase in none (a branch that stopped naming its mistake). The whole
    messages are compared too, and every failure interpolates the colliding
    text, so a reader is told *which* two collapsed rather than only that two
    did.

    Whole-message comparison alone is **not** sufficient here and this is
    measured, not asserted: see :data:`SIGNATURES`.

    The healthy leg contributes no message — it returns a value. The
    ``shlex.split`` quoting branch is deliberately out of the set: a quoting
    error is not a grammar mistake, and it carries the parser's own words.
    """
    remainders = {
        "D-06 — the deployment declares no `server:`": str(
            _without_a_server(tmp_path, "distinct-no-server")
        ),
        "D-07 — the pre-migration two-token address": PRE_MIGRATION_REMAINDER,
        "D-08 — the token resolves to a program": str(STDIO_SERVER),
        "an unquoted path containing whitespace": str(
            _root(tmp_path, "distinct-My Deployments")
        ),
        "the generic wrong token count": "a b c",
        "the declared program is not there": str(
            _root(tmp_path, "distinct-nowhere")
        ),
    }

    messages: dict[str, str] = {}
    for label, remainder in remainders.items():
        monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{remainder}")
        messages[label] = _refusal_message()

    assert set(messages) == set(SIGNATURES), (
        "the distinctness leg and the signature register disagree about which"
        " refusals exist, so one of them is measuring a set nobody maintains"
    )

    for owner, phrase in SIGNATURES.items():
        carriers = [label for label, text in messages.items() if phrase in text]
        assert carriers == [owner], (
            f"`{phrase}` should name exactly one mistake — {owner}. It appears"
            f" in {carriers or 'NO refusal at all'}.\n"
            + "\n".join(f"--- {label} ---\n    {messages[label]}" for label in messages)
        )

    labels = list(messages)
    collisions = [
        (left, right)
        for index, left in enumerate(labels)
        for right in labels[index + 1 :]
        if messages[left] == messages[right]
    ]
    assert not collisions, "\n".join(
        f"{left} and {right} produce the SAME refusal:\n    {messages[left]}"
        for left, right in collisions
    )
