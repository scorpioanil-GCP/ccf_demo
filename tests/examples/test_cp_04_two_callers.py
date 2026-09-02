"""ONE request, TWO callers, ONE payload — and the comparison is proven able to disagree.

**What this module is for.** `D-21` rules cp-04's assembler standalone with two
thin callers, and `24.4-09` is the wave that gives it the second one. Criterion
47 asks that *"the MCP tool ask returns an equivalent payload for the same
request"*; criterion 38 (`CFT-G14`) asks that *"one standalone assembler serves
both callers"*. Neither is checkable until both callers exist, and neither is
worth anything unless the comparison behind it can be made to fail — so every
positive statement below has a control that feeds the **shipped** comparison a
divergent subject and watches it refuse.

**This module is the POSITIVE STATEMENT plan `24.4-12` sabotages against.**
`artifacts/gates.yaml` names `tests/examples/test_cp_04_seams.py` as the home of
`CFT-G13` and `CFT-G14`; that module is plan 12's and does not exist yet. What is
here is the behavior those two gates will assert, exercised against the shipped
door so that the gate plan inherits a measured subject rather than a described
one.

## What "equivalent" means here — and what it does NOT mean

The two callers reach the same assembler over **different transports**, and the
transports carry different frames. So the comparison is over:

* the **served payload** — the `payload` object inside the vessel, member for
  member; and
* the **content address** — `sha256` over the vessel's canonical bytes, computed
  producer-side on both paths by `ccf.products.door.py::door_answer`.

and it is deliberately **NOT** over:

* the **whole envelope byte for byte.** The in-process caller receives a
  `ccf.client.result.py::Result` decoded by `ccf.client.codec.py::decode_outcome`;
  the MCP caller receives a `ccf.products.door.py::DoorOutcome` inside an MCP
  tool response with its own `isError` flag and content framing. Comparing those
  would fail on a framing change that means nothing.
* the **replay reference.** Both callers write a decision record, to two
  different file-backed artifact stores under two different scratch roots. The
  reference is compared **and reported** below rather than asserted, because
  what it proves is a property of content addressing rather than of these two
  callers.
* **timing, process identity and store paths.** Two runs, two temporary
  directories, two per-run SQLite files — `deployment.py::connection` mints a
  fresh filename per run precisely so that two asks of one question build two
  separate graphs from the same two estates and must still agree anyway.

A reader must not mistake the narrowed comparison for a total one, which is why
the exclusions are named rather than left to be inferred from the code.

## `CFT-G13`'s three limbs, and one measured correction to how limb (a) reads

Criterion 37 was AMENDED at Gate 1 (`D-IMPL-225` amendment 1) because its
original wording — *"no resource is exposed"* — is false against this tree:
`runtime/ccf_runtime/mcp/egress.py::build_egress_server` registers its product
resource **unconditionally** and gates only the tool. The amended criterion
asserts three things together: **(a)** the resource IS registered and
enumerable; **(b)** a read of it returns
`runtime/ccf_runtime/mcp/egress.py::ProductNotServable` and NEVER a tree; and
**(c)** the TOOL is the only path that serves, on a client-supplied `lei` and
`max_depth`.

**MEASURED, AND IT REFINES LIMB (a).** `PRODUCT_URI_TEMPLATE` carries `{tenant}`,
`{product_class}` and `{version}` placeholders, so `FastMCP` registers it as a
**resource TEMPLATE**. Against this door, `resources/list` returns **an empty
list** and `resources/templates/list` returns exactly
`ccf-product://{tenant}/{product_class}/{version}`. The substance of limb (a)
holds — the door advertises the resource to every client that enumerates, cp-04
cannot omit it, and `D-34` is unchanged — but *"enumerable in `resources/list`"*
names the wrong listing, and the SDK's own
`tests/crossproc/test_mcp_egress.py` never enumerated either one, so the
criterion's wording was inferred from the registration call rather than measured
at a client. :func:`listing_violations` asserts **both** listings, so neither the
template disappearing nor a concrete entry silently appearing goes unseen.

## Isolation

Per-module ledger and schema names from `tests/examples/cp_04_seed.py`, for the
reason that module records: `tests/conftest.py::fluree_url` is session-scoped and
env-driven — one server, no per-module container — and six cp-04 modules transact
this one fixture. A fixed ledger name means whichever module ran second cannot
seed at all (`409 err:db/LedgerExists`), and a shared one means a sibling
module's deliberate sabotage leaks into this module's content addresses
permanently, because Fluree is append-only. Shared CI fixtures colliding by
collection order have already left `leg-postgres` red on `main` in this
repository once.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterator, Mapping

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.types import TextContent, TextResourceContents
from pydantic import AnyUrl

from ccf.contracts.canonical import canonical_bytes
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.door import PRODUCT_REQUEST_TOOL, WireRequest
from ccf_runtime.mcp.egress import PRODUCT_URI_TEMPLATE, product_uri

from .cp_04_seed import ledger_for, schema_for, seed

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-04-corporate-family-tree"
SERVER = EXAMPLE / "server"

#: Both stores. `.github/workflows/ci.yml` exports both legs' variables at JOB
#: level and runs `leg-postgres` and `leg-fluree` as two steps of that one job,
#: so a doubly-marked module is selected twice and runs whole both times.
pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

#: The base the ASGI client addresses. A loopback authority rather than a
#: `.invalid` name because `FastMCP` installs a `Host` header guard that rejects
#: anything else with `421 Misdirected Request` — measured, and it turns every
#: call into an unreachable-server refusal that looks exactly like a door
#: refusing. The shipped door's own advertised `resource_server_url` is a
#: `.invalid` name and stays one; this is the client's view of the ASGI app.
BASE_URL = "http://127.0.0.1:8124"

#: How long one leg may take. Generous — each ask opens two systems of record,
#: performs an L1 ingest and runs the whole L1..L6 spine — but bounded, because
#: a hung door is a failure this suite should report rather than inherit.
TIMEOUT_SECONDS = 600

#: A depth the demonstration does not use, for the planted difference. Read as
#: an ADDRESS into the declared bounds rather than as a figure: the assertion is
#: that two depths are two answers, never that either has a particular size.
PLANTED_DEPTH = 1


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package and its modules
    import each other by bare name, while one pytest session runs over a tree
    holding several `deployment`/`produce`/`run` triples. So the cache is checked
    against THIS example's directories and the whole family is evicted together
    when it holds somebody else's — evicting one name at a time would rebuild the
    split-identity problem the eviction prevents. The shape is
    `tests/examples/test_cp_04_debt.py::_load`, extended with the two `server/`
    modules this plan adds.
    """
    wanted = [str(EXAMPLE), str(SERVER)]
    if sys.path[:2] != wanted:
        for entry in wanted:
            while entry in sys.path:
                sys.path.remove(entry)
        for entry in reversed(wanted):
            sys.path.insert(0, entry)
    family = (
        "deployment",
        "produce",
        "projection",
        "assembler",
        "transport",
        "run",
        "compose",
        "serve",
    )
    roots = (str(EXAMPLE), str(SERVER))
    for cached_name in family:
        cached = sys.modules.get(cached_name)
        if cached is None:
            continue
        if not str(getattr(cached, "__file__", "")).startswith(roots):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
    return importlib.import_module(name)


# ---------------------------------------------------------------------------
# One answer, however it was asked.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """What one caller got back, reduced to what the comparison is over."""

    #: How it was asked. Reported in every failure message, so a disagreement
    #: names which two callers disagreed rather than leaving it to be inferred.
    caller: str
    #: The served payload, as decoded.
    payload: Mapping[str, Any]
    #: `sha256` over the vessel's canonical bytes, computed producer-side.
    content_address: str
    #: The decision record this answer was authorized by. Reported, not
    #: asserted — see the module docstring.
    replay_ref: str | None


def answer_violations(answers: Mapping[str, Answer]) -> list[str]:
    """Every way a set of per-caller answers fails to be the same answer.

    A function of the answers rather than a bare `assert`, so the controls can
    feed the **shipped** comparison a divergent pair and be watched failing. A
    comparison that can only ever be handed the passing pair is a comparison
    nobody has watched fail. The shape is
    `tests/examples/test_hw1_two_transports.py::parity_violations`, one example
    over.
    """
    violations: list[str] = []
    if len(answers) < 2:
        return [
            "fewer than two callers answered, so nothing was compared —"
            f" {sorted(answers)}"
        ]
    for caller, answer in answers.items():
        if not answer.content_address:
            violations.append(
                f"`{caller}` carries no content address, so its answer carries"
                " nothing to agree about"
            )
        if not answer.payload:
            violations.append(
                f"`{caller}` served an empty payload — two empty answers are"
                " not the same answer"
            )
    if violations:
        return violations

    addresses = {answer.content_address for answer in answers.values()}
    if len(addresses) != 1:
        violations.append(
            "the callers sealed to different content addresses: "
            + ", ".join(
                f"{caller}={answer.content_address}"
                for caller, answer in sorted(answers.items())
            )
        )
    payloads = {
        caller: canonical_bytes(answer.payload)
        for caller, answer in answers.items()
    }
    if len(set(payloads.values())) != 1:
        left, right = sorted(answers)
        violations.append(
            "the callers served different payloads.\n"
            f"--- {left} ---\n{payloads[left].decode('utf-8')[:2000]}\n"
            f"--- {right} ---\n{payloads[right].decode('utf-8')[:2000]}"
        )
    return violations


# ---------------------------------------------------------------------------
# The estate, and the environment the deployment reads it through.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def estate(fluree_url: str, postgres_dsn: str) -> Iterator[tuple[str, str]]:
    """The committed fixture pair, under names nobody else holds.

    The environment variables are set for the whole module rather than per test:
    every ask in this module runs against ONE estate, because the claim is *the
    same deployment reached two ways* and two estates would soften it into *two
    deployments that agree*.
    """
    ledger = ledger_for(__name__)
    schema = schema_for(__name__)
    seed(fluree_url, ledger, postgres_dsn, schema)

    patch = pytest.MonkeyPatch()
    for variable, value in (
        ("CCF_CP_04_FLUREE_URL", fluree_url.rstrip("/")),
        ("CCF_CP_04_FLUREE_LEDGER", ledger),
        ("CCF_CP_04_POSTGRES_DSN", postgres_dsn),
        ("CCF_CP_04_POSTGRES_SCHEMA", schema),
    ):
        patch.setenv(variable, value)
    try:
        yield ledger, schema
    finally:
        patch.undo()


# ---------------------------------------------------------------------------
# Caller 1 — in process, exactly as `run.py` asks.
# ---------------------------------------------------------------------------


def _wire_parameters(typed: Any) -> dict[str, Any]:
    """The question as WIRE-STABLE values — `run.py::_wire_parameters`'s rule.

    `WireRequest` refuses a `Decimal`, because canonical JSON renders one as text
    and the decoded echo would then differ from what was sent, reporting a
    transport failure on a healthy wire. Both callers below therefore put the
    same text on their wire and both convert it back at their door.
    """
    return {
        name: (value if isinstance(value, (str, int, bool)) else format(value, "f"))
        for name, value in typed.parameters.items()
    }


def ask_in_process(*, max_depth: int | None, role: str | None = None) -> Answer:
    """Ask through `ProductClient` over the in-process adapter — `run.py`'s path.

    Not a reimplementation: the same `ProductClient(product_id=…, adapter=…)`
    constructor `run.py` builds (`D-IMPL-225` amendment 2), over the same
    `transport.py::FamilyTreeInProcessAdapter`, carrying the same question
    `deployment.py::demonstration_request` composes for both callers.
    """
    from ccf.client.client import ProductClient

    deployment = _load("deployment")
    transport = _load("transport")

    typed = deployment.demonstration_request(max_depth=max_depth)
    parameters = _wire_parameters(typed)
    with tempfile.TemporaryDirectory(prefix="cp04-two-callers-inproc-") as tmp:
        client = ProductClient(
            product_id=transport.declared_product_id(),
            adapter=transport.FamilyTreeInProcessAdapter(
                root=pathlib.Path(tmp), role=role
            ),
        )
        result = client.ask(parameters, as_of=typed.asked_at)
    assert not result.refused, f"the in-process ask was refused: {result.refusal}"
    return Answer(
        caller="in-process",
        payload=dict(result.payload),
        content_address=str(result.content_address),
        replay_ref=None if result.replay_ref is None else str(result.replay_ref),
    )


# ---------------------------------------------------------------------------
# Caller 2 — the MCP door, driven over its own ASGI app.
# ---------------------------------------------------------------------------


def _client_factory(app: Any, token: str | None) -> Callable[[], httpx.AsyncClient]:
    """A client over the door's own ASGI app, Bearer-headed when asked."""

    def factory() -> httpx.AsyncClient:
        headers = {} if token is None else {"Authorization": f"Bearer {token}"}
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=BASE_URL,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )

    return factory


def drive(
    door: Any,
    operations: Mapping[str, Callable[[ClientSession], Awaitable[Any]]],
) -> dict[str, Any]:
    """Drive EVERY surface of ONE door, in ONE lifespan, on ONE credential.

    **One lifespan is a hard requirement rather than an optimization**, and it
    is the SDK's own recorded reason at
    `tests/crossproc/test_mcp_egress.py::_both_surfaces_in_process`: measured
    against `mcp==1.28.1`, `StreamableHTTPSessionManager.run()` refuses a second
    call per instance and `FastMCP` holds one manager per server. A module that
    entered the lifespan twice would be forced onto two servers, and would then
    be comparing two deployments rather than the surfaces of one door.

    `httpx.ASGITransport` does not drive the ASGI lifespan and the FastMCP
    streamable-HTTP app starts its session manager IN the lifespan, so the
    lifespan context is entered explicitly — exactly what uvicorn does for the
    cross-process siblings.

    Each operation gets its own session, and a raised refusal is CAUGHT and
    returned rather than allowed to abort the rest: the resource surface refuses
    by raising and the tool surface refuses by returning, and a driver that let
    the first take down the second would make the two unobservable together.

    Returns:
        One entry per operation — its return value, or, when it refused,
        ``Refused`` carrying the door's own flattened reason.
    """
    app = door.server.streamable_http_app()

    async def go() -> dict[str, Any]:
        results: dict[str, Any] = {}
        async with app.router.lifespan_context(app):
            for name, operation in operations.items():
                try:
                    results[name] = await run_with_session(
                        url=f"{BASE_URL}/mcp",
                        operation=operation,
                        http_client_factory=_client_factory(app, door.credential),
                    )
                except McpServerUnreachable as refused:
                    results[name] = Refused(reason=_flatten(refused))
                except BaseException as refused:  # noqa: BLE001 — flattened below
                    results[name] = Refused(reason=_flatten(refused))
        return results

    return asyncio.run(go())


@dataclass(frozen=True)
class Refused:
    """One surface that did not answer, with the door's own reason.

    A value rather than a raise, and the REASON rather than the fact: a refusal
    test that only asserted *it raised* would pass against a door refusing for a
    reason nobody intended.
    """

    reason: str


def tool_arguments(*, tenant: str, typed: Any) -> dict[str, Any]:
    """The product tool's arguments for one typed question.

    **The four §6.3 axes are required together**, so a partial address is
    unrepresentable on this surface rather than refused; `request` carries the
    caller's own question canonically encoded (`C-16`), and the door refuses BY
    NAME any disagreement between it and the address arguments beside it. This
    function is the one place the two copies are composed, from one source, so a
    test cannot accidentally send one question and address another.
    """
    parameters = _wire_parameters(typed)
    wire = WireRequest(
        product_id=typed.schema_name,
        parameters=parameters,
        temporal_boundary=typed.asked_at,
    )
    return {
        "tenant": tenant,
        "product_class": typed.schema_name,
        "version": typed.schema_version,
        "request": canonical_bytes(wire).decode("utf-8"),
        "subject": typed.subject,
        "intent": typed.intent,
        "freshness": typed.freshness,
        "asked_at": typed.asked_at.isoformat(),
        "parameters": parameters,
    }


def tool_call(
    arguments: Mapping[str, Any],
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    """Call the product tool; report ``(isError, joined text)``.

    A tool refusal arrives as a perfectly successful response carrying
    `isError`, so a helper that watched only for exceptions would read every
    refusal as a serve — `tests/crossproc/test_mcp_egress.py::_tool_operation`
    records the same trap.
    """

    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, dict(arguments))
        return bool(result.isError), " | ".join(
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        )

    return operation


def resource_read(
    uri: str,
) -> Callable[[ClientSession], Awaitable[str]]:
    """Read the product resource; return the served text, or refuse.

    The door's resource handler raises rather than returning a refusal envelope
    — it has no envelope channel, which
    `runtime/ccf_runtime/mcp/egress.py::build_egress_server` records as a
    deliberate asymmetry between its two surfaces — so a refusal reaches the
    client as `ccf.mcp.errors.py::McpServerUnreachable` wrapping the door's own
    reason, and :func:`drive` turns that into a :class:`Refused`.
    """

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return operation


def enumeration() -> Callable[[ClientSession], Awaitable[tuple[list[str], list[str]]]]:
    """What a client that enumerates this door actually sees — both listings."""

    async def operation(session: ClientSession) -> tuple[list[str], list[str]]:
        listed = await session.list_resources()
        templated = await session.list_resource_templates()
        return (
            [str(entry.uri) for entry in listed.resources],
            [entry.uriTemplate for entry in templated.resourceTemplates],
        )

    return operation


def _flatten(exc: BaseException) -> str:
    """Every message in one exception tree, joined.

    An exception escaping a `TaskGroup` is re-wrapped as a `BaseExceptionGroup`
    that says nothing about the door, so the tree is walked and the door's own
    reason recovered from it. A refusal test that only asserted *it raised* would
    pass against a door refusing for a reason nobody intended.
    """
    parts = [f"{type(exc).__name__}: {exc}"]
    for sub in getattr(exc, "exceptions", ()) or ():
        parts.append(_flatten(sub))
    for related in (exc.__cause__, exc.__context__):
        if related is not None and related is not exc:
            parts.append(_flatten(related))
    return " || ".join(parts)


def tool_answer(name: str, result: Any) -> Answer:
    """One `DoorOutcome` off the wire, reduced to what the comparison is over."""
    assert not isinstance(result, Refused), (
        f"the `{name}` tool ask did not answer at all: {result.reason[:1500]}"
    )
    is_error, text = result
    assert not is_error, f"the `{name}` tool ask was refused: {text[:1500]}"
    outcome = json.loads(text)
    vessel = json.loads(outcome["product_json"])
    return Answer(
        caller=name,
        payload=dict(vessel["payload"]),
        content_address=str(outcome["content_address"]),
        replay_ref=(
            None
            if outcome.get("replay_ref") is None
            else str(outcome["replay_ref"])
        ),
    )


#: The names the door's five surfaces are driven under, in one lifespan.
DEMONSTRATION_ASK = "mcp-tool(demonstration depth)"
PLANTED_ASK = f"mcp-tool(max_depth={PLANTED_DEPTH})"
OVER_CEILING_ASK = "mcp-tool(over the ceiling)"
RESOURCE_READ = "resource-read"
ENUMERATE = "enumerate"


@pytest.fixture(scope="module")
def surfaces(estate: tuple[str, str]) -> dict[str, Any]:
    """ONE door, ONE lifespan, every surface this module asserts about.

    The SHIPPED door, built by the SHIPPED program: `serve.py::door` is a
    context manager returning the configured server rather than running it, so
    the construction a reader spawns on stdio is the construction driven here. A
    module that built its own `build_egress_server` call would be asserting
    something about itself.

    Every surface is driven against ONE door because a door rebuilt between
    surfaces would make each assertion true of a different server — and because
    it has to be: `StreamableHTTPSessionManager.run()` refuses a second call per
    instance. See :func:`drive`.
    """
    deployment = _load("deployment")
    serve = _load("serve")
    tenant = deployment.tenant_id()
    demonstration = deployment.demonstration_request()
    planted = deployment.demonstration_request(max_depth=PLANTED_DEPTH)
    over = deployment.demonstration_request(
        max_depth=deployment.declared_depth_ceiling() + 1
    )
    uri = product_uri(
        tenant=tenant,
        product_class=demonstration.schema_name,
        version=demonstration.schema_version,
    )
    with tempfile.TemporaryDirectory(prefix="cp04-two-callers-door-") as scratch:
        with serve.door(root=pathlib.Path(scratch)) as opened:
            return drive(
                opened,
                {
                    ENUMERATE: enumeration(),
                    RESOURCE_READ: resource_read(uri),
                    DEMONSTRATION_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=demonstration)
                    ),
                    PLANTED_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=planted)
                    ),
                    OVER_CEILING_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=over)
                    ),
                },
            )


@pytest.fixture(scope="module")
def in_process_answer(estate: tuple[str, str]) -> Answer:
    """One in-process ask at the demonstration depth."""
    return ask_in_process(max_depth=None)


@pytest.fixture(scope="module")
def mcp_answer(surfaces: dict[str, Any]) -> Answer:
    """The SAME question, over the MCP tool."""
    return tool_answer(DEMONSTRATION_ASK, surfaces[DEMONSTRATION_ASK])


@pytest.fixture(scope="module")
def mcp_answer_at_a_planted_depth(surfaces: dict[str, Any]) -> Answer:
    """A DIFFERENT question, over the same tool — the planted difference."""
    return tool_answer(PLANTED_ASK, surfaces[PLANTED_ASK])


# ---------------------------------------------------------------------------
# Criterion 47 — one request, two callers, one payload.
# ---------------------------------------------------------------------------


def test_the_two_callers_answer_one_request_equivalently(
    in_process_answer: Answer, mcp_answer: Answer
) -> None:
    """Criterion 47. The in-process ask and the MCP tool ask agree.

    Over the served payload and the content address, and over nothing else —
    the module docstring names every exclusion and why each is excluded.
    """
    answers = {
        in_process_answer.caller: in_process_answer,
        mcp_answer.caller: mcp_answer,
    }
    assert not answer_violations(answers), "\n".join(answer_violations(answers))


def test_the_comparison_refuses_a_planted_difference(
    in_process_answer: Answer, mcp_answer_at_a_planted_depth: Answer
) -> None:
    """**Positive control.** A comparison that cannot disagree is not a comparison.

    The difference is planted in the QUESTION rather than in the answer: the MCP
    side is asked at a different `max_depth`, which `CFT-G05` already holds to be
    a different product with a different content address. So this control also
    states, from the door's side, that the client's `max_depth` reaches the walk
    — a door that ignored it would make this control fail to fail.
    """
    answers = {
        in_process_answer.caller: in_process_answer,
        mcp_answer_at_a_planted_depth.caller: mcp_answer_at_a_planted_depth,
    }
    violations = answer_violations(answers)
    assert violations, (
        "two answers to two different questions were reported as equivalent —"
        f" both sealed to {in_process_answer.content_address}, which would mean"
        f" the door ignored the caller's max_depth={PLANTED_DEPTH}"
    )
    assert any("different content addresses" in entry for entry in violations), (
        violations
    )


def test_the_comparison_refuses_an_answer_carrying_nothing() -> None:
    """**Vacuity control.** Two empty answers are not the same answer."""
    empty = Answer(caller="x", payload={}, content_address="", replay_ref=None)
    violations = answer_violations({"a": empty, "b": empty})
    assert violations, "two empty answers were reported as agreement"
    assert any("nothing to agree about" in entry for entry in violations), violations


def test_the_comparison_refuses_a_single_caller(in_process_answer: Answer) -> None:
    """**Vacuity control.** One caller that ran is not two callers that agreed."""
    violations = answer_violations({in_process_answer.caller: in_process_answer})
    assert violations, "one answer was reported as an equivalence result"
    assert any("nothing was compared" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# Criterion 38 / `CFT-G14` — one standalone assembler, two callers.
# ---------------------------------------------------------------------------


def test_both_callers_resolve_to_the_same_assembler_module() -> None:
    """`CFT-G14`'s subject, as a module identity rather than as a description.

    `transport.py` and `server/compose.py` are the two callers' resolvers, and
    both must hold the SAME `assembler` module object — not two modules of the
    same name loaded from two paths, which is exactly what a directory of
    bare-named modules makes possible in one pytest session.
    """
    transport = _load("transport")
    compose = _load("compose")
    assembler = _load("assembler")

    assert transport.assembler is assembler, (
        "`transport.py` holds an `assembler` module that is not this example's"
        f" — {getattr(transport.assembler, '__file__', None)}"
    )
    assert compose.assembler is assembler, (
        "`server/compose.py` holds an `assembler` module that is not this"
        f" example's — {getattr(compose.assembler, '__file__', None)}"
    )
    assert (
        pathlib.Path(assembler.__file__).resolve() == (EXAMPLE / "assembler.py")
    ), assembler.__file__


def test_the_assembler_knows_nothing_about_the_door() -> None:
    """The direction is the whole content of the standalone claim.

    `server/compose.py` imports `assembler`; `assembler.py` imports neither the
    door nor the transport nor anything MCP-shaped. Read from the module's
    IMPORTS rather than by grepping its text — the file's own docstring states
    the claim in prose, and a text search would find the claim and read it as the
    violation, which is the defect plan `24.4-08` recorded against two of its own
    greps.
    """
    import ast

    tree = ast.parse((EXAMPLE / "assembler.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = sorted(
        name
        for name in imported
        if name in {"compose", "serve", "transport", "run"}
        or name.startswith(("mcp", "ccf_runtime", "ccf.client"))
    )
    assert not forbidden, (
        "`assembler.py` imports " + ", ".join(forbidden) + " — the standalone"
        " claim is only demonstrable while the arrow points the other way"
    )


def assembly_entry_points(tree_root: pathlib.Path) -> list[str]:
    """Every construction of the standalone assembler under ``tree_root``.

    A function over a directory rather than a bare assert on the shipped one, so
    the controls can hand the **shipped** check a divergent subject and be
    watched failing. Read from the AST rather than by grepping the text: the
    modules' own docstrings name `FamilyTreeAssembler` in prose, and a text
    search would find the claim and read it as the violation — the defect plan
    `24.4-08` recorded against two of its own greps.
    """
    import ast

    found: list[str] = []
    for module in sorted(tree_root.glob("*.py")):
        parsed = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(parsed):
            if not isinstance(node, ast.Call):
                continue
            target = node.func
            name = (
                target.attr
                if isinstance(target, ast.Attribute)
                else target.id
                if isinstance(target, ast.Name)
                else None
            )
            if name == "FamilyTreeAssembler":
                found.append(module.name)
    return found


def test_the_server_has_exactly_one_assembly_entry_point() -> None:
    """A second assembly path under `server/` is `CFT-G14`'s named sabotage.

    Exactly one construction of `FamilyTreeAssembler`, and it is in
    `compose.py`. A door that assembled for itself would make both callers green
    while proving nothing.
    """
    assert assembly_entry_points(SERVER) == ["compose.py"], (
        f"`server/` holds {assembly_entry_points(SERVER)} as its assembly entry"
        " point(s). `D-21` gives it exactly one, in `compose.py`, and it is"
        " `assembler.py::FamilyTreeAssembler`"
    )


def test_the_entry_point_check_refuses_a_second_assembly_path(
    tmp_path: pathlib.Path,
) -> None:
    """**Sabotage control.** `server/serve.py` given an assembly path of its own."""
    import shutil

    subject = tmp_path / "second-path"
    shutil.copytree(SERVER, subject, ignore=shutil.ignore_patterns("__pycache__"))
    door_program = subject / "serve.py"
    door_program.write_text(
        door_program.read_text(encoding="utf-8")
        + "\n\ndef _its_own_path(**kwargs):\n"
        "    return assembler.FamilyTreeAssembler(**kwargs)\n",
        encoding="utf-8",
    )
    assert assembly_entry_points(subject) != ["compose.py"], (
        "the second-path control did not change what the check sees"
    )
    assert sorted(assembly_entry_points(subject)) == ["compose.py", "serve.py"], (
        assembly_entry_points(subject)
    )


def test_the_entry_point_check_refuses_a_server_with_no_assembler_at_all(
    tmp_path: pathlib.Path,
) -> None:
    """**Vacuity control.** Zero entry points is not one entry point.

    Compared with `==` rather than `<=` for exactly this: a `server/` that had
    lost its assembler entirely would satisfy `<= 1` forever.
    """
    empty = tmp_path / "no-assembler"
    empty.mkdir()
    assert assembly_entry_points(empty) == [], assembly_entry_points(empty)
    assert assembly_entry_points(empty) != ["compose.py"]


# ---------------------------------------------------------------------------
# Criterion 37 / `CFT-G13` — the tool serves, the registered resource refuses.
# ---------------------------------------------------------------------------


def listing_violations(
    *, resources: list[str], templates: list[str]
) -> list[str]:
    """Every way this door's enumeration fails `CFT-G13` limb (a).

    Both listings are asserted, and each for its own reason. The TEMPLATE must
    be there, because that is where a parameterized product URI actually
    surfaces and it is what makes the resource enumerable at all. `resources/list`
    must stay EMPTY, because a concrete entry appearing there would mean the door
    had begun advertising a standing instance of a class that has no standing
    answer — the opposite of what limb (b) refuses.
    """
    violations: list[str] = []
    if PRODUCT_URI_TEMPLATE not in templates:
        violations.append(
            f"the product resource template {PRODUCT_URI_TEMPLATE!r} is not"
            f" enumerable — templates are {templates}. `CFT-G13` limb (a) says"
            " the resource IS registered and IS enumerable; a door that hid it"
            " would be claiming a tool-only shape `build_egress_server` cannot"
            " express (`D-34`)"
        )
    if resources:
        violations.append(
            f"`resources/list` carries {resources} — this class is"
            " parameterized and has no standing, parameter-free answer, so a"
            " concrete resource entry would advertise an instance nothing can"
            " serve"
        )
    return violations


def test_cft_g13_a_the_product_resource_is_registered_and_enumerable(
    surfaces: dict[str, Any],
) -> None:
    """`CFT-G13` limb (a), measured at a client rather than read off a decorator."""
    listed = surfaces[ENUMERATE]
    assert not isinstance(listed, Refused), listed.reason[:1500]
    resources, templates = listed
    violations = listing_violations(resources=resources, templates=templates)
    assert not violations, "\n".join(violations)


def test_the_listing_check_refuses_a_door_that_hid_the_resource() -> None:
    """**Sabotage control.** The template gone is limb (a) broken."""
    violations = listing_violations(resources=[], templates=[])
    assert violations, "a door advertising no product resource was accepted"
    assert any("is not" in entry for entry in violations), violations
    assert any(PRODUCT_URI_TEMPLATE in entry for entry in violations), violations


def test_the_listing_check_refuses_a_concrete_product_resource() -> None:
    """**Sabotage control.** A standing instance appearing in `resources/list`."""
    violations = listing_violations(
        resources=["ccf-product://cp-04-demo/reference.corporate-family/1.0.0"],
        templates=[PRODUCT_URI_TEMPLATE],
    )
    assert violations, "a concrete product resource entry was accepted"
    assert any("resources/list` carries" in entry for entry in violations), violations


def refusal_violations(*, served: bool, text: str) -> list[str]:
    """Every way a resource read fails `CFT-G13` limb (b).

    THE THREE THINGS THIS CHECKS ARE DIFFERENT THINGS. That the read did not
    serve; that the refusal names the SDK's own `ProductNotServable` reason
    rather than failing for some unrelated reason; and that **no tree came
    back** — the last one asserted against the payload's own vocabulary, because
    a check that only asserted *"it refused"* would be satisfied by a door that
    was broken for a reason nobody intended, and a check that only asserted *"no
    exception text mentions a tree"* would be satisfied by a door that served one
    silently.
    """
    violations: list[str] = []
    if served:
        violations.append(
            "the product RESOURCE served. `CFT-G13` limb (b): a resolve or read"
            " of it returns the refusal type and NEVER a tree — this class is"
            " parameterized and a resource read supplies no anchor and no depth,"
            " so anything it returned would answer a question nobody asked"
        )
    if "PARAMETERIZED class" not in text:
        violations.append(
            "the resource read did not refuse for THIS deployment's stated"
            " reason. A refusal for an unrelated reason is not the refusal"
            f" `CFT-G13` asserts. Got: {text[:600]}"
        )
    for token in ("\"nodes\"", "\"anchor\"", "\"findings\"", "type_chain"):
        if token in text:
            violations.append(
                f"a resource read returned {token} — that is a TREE, and the"
                " one thing this surface must never produce"
            )
    return violations


def test_cft_g13_b_a_read_of_the_product_resource_refuses_and_never_serves_a_tree(
    surfaces: dict[str, Any],
) -> None:
    """`CFT-G13` limb (b). The registered resource refuses BY NAME."""
    read = surfaces[RESOURCE_READ]
    served = not isinstance(read, Refused)
    text = read if served else read.reason
    violations = refusal_violations(served=served, text=str(text))
    assert not violations, (
        "\n".join(violations) + f"\n--- the read returned ---\n{str(text)[:2000]}"
    )


def test_the_refusal_check_refuses_a_resolver_that_returned_a_payload(
    in_process_answer: Answer,
) -> None:
    """**THE SABOTAGE `D-IMPL-225` NAMES, as a shipped control.**

    Dave, at Gate 1: *"Sabotage: make the resolver return a payload and the gate
    must go RED."* The subject fed to the shipped check is a real served payload
    — the one the in-process caller actually got — rendered as the resource read
    would have rendered it, so this control cannot pass by being fed a string
    that merely looks wrong.
    """
    served_text = canonical_bytes(in_process_answer.payload).decode("utf-8")
    violations = refusal_violations(served=True, text=served_text)
    assert violations, "a resource read that SERVED A TREE was accepted as a refusal"
    assert any("must never produce" in entry for entry in violations), violations
    assert any("served" in entry for entry in violations), violations


def test_cft_g13_c_the_tool_serves_on_a_client_supplied_lei_and_max_depth(
    mcp_answer_at_a_planted_depth: Answer,
) -> None:
    """`CFT-G13` limb (c). The tool is the path that serves, and the CALLER chooses.

    The anchor and the depth both come off the caller's own arguments, and the
    payload reports back the depth it applied — so a door that had substituted a
    depth of its own, or clamped one, is visible here rather than only in a
    content address a reader cannot decompose.
    """
    deployment = _load("deployment")
    payload = mcp_answer_at_a_planted_depth.payload
    assert payload["anchor"]["lei"] == deployment.demonstration_anchor(), (
        "the tool served a different anchor than the caller named:"
        f" {payload['anchor']['lei']!r}"
    )
    assert int(payload["max_depth_applied"]) == PLANTED_DEPTH, (
        f"the caller asked max_depth={PLANTED_DEPTH} and the door applied"
        f" {payload['max_depth_applied']} — a depth the caller did not choose is"
        " a question nobody asked"
    )


def test_the_tool_refuses_an_over_ceiling_depth_rather_than_clamping_it(
    surfaces: dict[str, Any],
) -> None:
    """`CFT-G03`, over the door. The second surface must not be the weaker one.

    Above the declared ceiling is refused BY NAME on the in-process caller, and
    a door that clamped instead would be a serving path with a different
    contract behind it — the request says 8, the walk does 6, the payload looks
    fine and the address greens.
    """
    deployment = _load("deployment")
    ceiling = deployment.declared_depth_ceiling()
    result = surfaces[OVER_CEILING_ASK]
    text = result.reason if isinstance(result, Refused) else result[1]
    refused = isinstance(result, Refused) or bool(result[0])
    assert refused, (
        f"the door served an over-ceiling max_depth={ceiling + 1} instead of"
        f" refusing it: {str(text)[:1500]}"
    )
    assert "never clamped" in str(text), (
        "the door refused for some other reason than the declared bounds:"
        f" {str(text)[:1000]}"
    )


# ---------------------------------------------------------------------------
# CR-01 — a serve-path refusal is a GOVERNED error, and the door survives it.
# ---------------------------------------------------------------------------

#: A real estate anchor whose family serves a jurisdiction OUTSIDE the declared
#: closed set `{NL, US-DE}` (`AgilysysInc`, US-OH). Asking about it trips
#: `deployment.py::refuse_open_jurisdiction_world` on the serve path — the exact
#: per-request refusal CR-01 is about. Read as an ADDRESS into the estate, not
#: as a figure: what matters is that its observed set is not the declared one.
REFUSING_ANCHOR = "5299001XWB5V3B5IPN93"
REFUSING_ASK = "mcp-tool(a refusing anchor)"
POST_REFUSAL_ASK = "mcp-tool(a valid ask after a refusal)"


def _refusing_request(deployment: Any, lei: str) -> Any:
    """The demonstration question re-aimed at a non-demonstration anchor.

    The anchor travels as the declared `lei` argument AND as the subject, kept
    equal so the door does not refuse for a subject/argument disagreement before
    the serve-path guard it is meant to reach ever runs.
    """
    typed = deployment.demonstration_request()
    parameters = dict(typed.parameters)
    parameters[deployment.PARAM_LEI] = lei
    return typed.model_copy(update={"subject": lei, "parameters": parameters})


def test_a_serve_path_refusal_is_a_governed_error_and_the_door_survives(
    estate: tuple[str, str],
) -> None:
    """**CR-01 (2026-09-01).** A per-request refusal returns `isError=True`, and
    the door answers the next call.

    Dave: *"Per-request refusals on the serve path must not raise `SystemExit`.
    That is a process-lifetime signal. FastMCP only turns `Exception` into
    `isError`."* `SystemExit` is a `BaseException`, so before the fix a refusing
    anchor escaped the FastMCP tool wrapper and tore the session/server down
    rather than answering the caller — and the very next call in the same
    lifespan then found an unreachable server.

    So both observations are driven in ONE lifespan: the refusing anchor, then a
    valid demonstration ask AFTER it. The refusal must arrive as a governed tool
    error (`isError=True`, NOT a torn-down door), and the door must still serve
    the subsequent call. The sabotage this asserts against is the shipped defect
    itself: reverting `refuse_open_jurisdiction_world` to `raise SystemExit`
    turns the first assertion RED (the refusing anchor takes the door down, so
    the ask is a `Refused` rather than an `isError` answer) and the second RED
    too (the door does not survive to answer the post-refusal ask).
    """
    deployment = _load("deployment")
    serve = _load("serve")
    tenant = deployment.tenant_id()
    refusing = _refusing_request(deployment, REFUSING_ANCHOR)
    demonstration = deployment.demonstration_request()

    with tempfile.TemporaryDirectory(prefix="cp04-serve-refusal-") as scratch:
        with serve.door(root=pathlib.Path(scratch)) as opened:
            results = drive(
                opened,
                {
                    REFUSING_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=refusing)
                    ),
                    POST_REFUSAL_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=demonstration)
                    ),
                },
            )

    refused = results[REFUSING_ASK]
    # A GOVERNED tool error, not a torn-down door. `Refused` here means the call
    # raised out of the session — which is exactly the SystemExit-escapes-FastMCP
    # symptom CR-01 fixes.
    assert not isinstance(refused, Refused), (
        "the refusing anchor took the door DOWN instead of returning a governed"
        " error — a serve-path `SystemExit` escapes the FastMCP tool wrapper as a"
        f" `BaseException` (CR-01): {refused.reason[:1000]}"
    )
    is_error, text = refused
    assert is_error, (
        "a family serving a jurisdiction outside the declared closed set was"
        f" SERVED rather than refused: {text[:1000]}"
    )

    # THE DOOR STAYED UP. The next call, in the SAME lifespan, serves — which it
    # cannot do if the prior refusal had torn the session/server down.
    after = results[POST_REFUSAL_ASK]
    assert not isinstance(after, Refused), (
        "the door did not answer a valid demonstration ask AFTER a refusal — it"
        f" did not stay up: {after.reason[:1000]}"
    )
    is_error_after, text_after = after
    assert not is_error_after, (
        "the door refused a valid demonstration ask after a prior refusal:"
        f" {text_after[:1000]}"
    )


# ---------------------------------------------------------------------------
# The door's own threat register — `T-24.4-27` and `T-24.4-28`.
# ---------------------------------------------------------------------------


def test_an_unverified_caller_reaches_neither_surface(
    estate: tuple[str, str],
) -> None:
    """`T-24.4-27`. No credential, no product — on BOTH surfaces.

    A fresh door, driven with **no** bearer token. `FastMCP` installs its
    authentication middleware on the HTTP app at construction, so an unverified
    caller is refused before either handler body runs — and this asserts it
    happens rather than trusting that the builder was handed a verifier.

    Both surfaces, deliberately: the tool is the one that serves, so a door that
    authenticated its resource and not its tool would be exactly wrong.
    """
    deployment = _load("deployment")
    serve = _load("serve")
    tenant = deployment.tenant_id()
    typed = deployment.demonstration_request()
    uri = product_uri(
        tenant=tenant,
        product_class=typed.schema_name,
        version=typed.schema_version,
    )
    with tempfile.TemporaryDirectory(prefix="cp04-unverified-") as scratch:
        with serve.door(root=pathlib.Path(scratch)) as opened:
            app = opened.server.streamable_http_app()

            async def go() -> dict[str, Any]:
                results: dict[str, Any] = {}
                async with app.router.lifespan_context(app):
                    for name, operation in (
                        (RESOURCE_READ, resource_read(uri)),
                        (
                            DEMONSTRATION_ASK,
                            tool_call(tool_arguments(tenant=tenant, typed=typed)),
                        ),
                    ):
                        try:
                            results[name] = await run_with_session(
                                url=f"{BASE_URL}/mcp",
                                operation=operation,
                                # NO TOKEN. The whole subject of this test.
                                http_client_factory=_client_factory(app, None),
                            )
                        except BaseException as refused:  # noqa: BLE001
                            results[name] = Refused(reason=_flatten(refused))
                return results

            anonymous = asyncio.run(go())

    for name, result in anonymous.items():
        assert isinstance(result, Refused), (
            f"the `{name}` surface answered a caller carrying no credential:"
            f" {str(result)[:800]}"
        )


def test_the_resolver_assembles_under_the_perspective_it_was_handed(
    estate: tuple[str, str],
) -> None:
    """`T-24.4-28` / `DI-15.5-03`. The entitled perspective is FORWARDED.

    The door resolves and entitles a perspective and then hands it to the
    resolver. A resolver that called `deployment.perspective()` again would
    entitle one role and assemble under another — and against THIS deployment
    that substitution is invisible at the door, because the door grants only the
    declared default role and a re-derivation returns exactly that.

    So the seam is driven directly with the **non-default** role and the served
    payload is read for which role it was conditioned under. That is the one
    subject on which forwarding and re-deriving give different answers, and it is
    why this is asserted here rather than left to outcome parity — which is the
    precise blindness `DI-15.5-03` was recorded for.
    """
    deployment = _load("deployment")
    compose = _load("compose")

    default = deployment.perspective().role
    other = next(role for role in deployment.declared_roles() if role != default)

    with tempfile.TemporaryDirectory(prefix="cp04-forwarded-") as scratch:
        resolver = compose.build_resolver(root=pathlib.Path(scratch))
        typed = deployment.demonstration_request()
        served = resolver(
            tenant=deployment.tenant_id(),
            product_class=typed.schema_name,
            version=typed.schema_version,
            perspective=deployment.perspective(other),
            request=typed,
        )
    role_served = served.product.payload["perspective_role"]
    assert role_served == other, (
        f"the resolver was handed role {other!r} and assembled under"
        f" {role_served!r} — the door's entitled perspective was re-derived"
        " rather than forwarded, which is `DI-15.5-03` reopened on a new door"
    )
    assert role_served != default, (
        "the control is inert: the role it forwards is the declared default, so"
        " a re-derivation would have produced the same answer"
    )


# ---------------------------------------------------------------------------
# `D-IMPL-231` part 3 — a switch that cannot fail is not a smaller feature.
# ---------------------------------------------------------------------------


def test_the_two_declared_roles_seal_to_different_content_addresses(
    estate: tuple[str, str],
) -> None:
    """`--role` survives only because a role change is OBSERVED to change what is sealed.

    Dave, ruling `D-IMPL-231` part 3: *"A flag that changes nothing is
    `D-IMPL-228` again"* — the nine-row fiction in argv form — and *"don't leave
    a switch that cannot fail."* `--principal` is unshipped on exactly those
    grounds (plan `24.4-08` deviation 3), and `--role` may only ship if the two
    declared roles produce a different **content address**, which is what seals
    the served document. A role that reordered a payload or relabelled a field
    without moving the address would have changed nothing that survives.

    Asserted on the ADDRESS rather than on `detailed_members`, deliberately: the
    address is the thing a consumer can hold the producer to, and a difference
    the address does not seal is not a difference for this purpose.
    """
    deployment = _load("deployment")
    roles = deployment.declared_roles()
    assert len(roles) == 2, (
        f"this deployment conditions on {list(roles)}; the flag's whole subject"
        " is that TWO roles see one family differently"
    )
    sealed = {role: ask_in_process(max_depth=None, role=role) for role in roles}
    addresses = {role: answer.content_address for role, answer in sealed.items()}
    assert len(set(addresses.values())) == len(roles), (
        "the two declared roles sealed to the SAME content address"
        f" — {addresses}. Under `D-IMPL-231` that means `--role` changed nothing"
        " that survives and the flag must be DROPPED, not kept for later"
    )
