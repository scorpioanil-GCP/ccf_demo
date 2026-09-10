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
`runtime/ccf_runtime/mcp/egress.py::build_egress_server` then registered its
product resource **unconditionally** and gated only the tool (since `24.5-L-09`
it takes `expose_product_resource`, default `True`; this door keeps the resource
by ruling and passes no flag). The amended criterion
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
holds — the door advertises the resource to every client that enumerates, and
cp-04 keeps it by ruling (`D-34` was closed by `24.5-L-09`) — but *"enumerable in `resources/list`"*
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
import re
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
from ccf.products.constraints import ConstraintRefusal
from ccf.products.door import PRODUCT_REQUEST_TOOL, WireRequest
from ccf.products.refusal import REFUSAL_KINDS, SubjectUnavailableRefusal
from ccf.products.request import ProductRequestViolation
from ccf_runtime.mcp.egress import (
    CCF_FAILURE_PREFIX,
    PRODUCT_URI_TEMPLATE,
    product_uri,
)

from .cp_04_seed import live_estate

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

#: A depth deeper than any tree in this estate — the request `D-IMPL-251` C5
#: turned from a refusal into a product. Measured: the deepest tree anywhere in
#: this estate is 6, and the demonstration anchor's component is exhausted at 3.
UNEXHIBITED_DEPTH = 8

#: The SDK's own kind tokens, read from the closed vocabulary rather than
#: spelled here: a test that typed them would agree with itself about the
#: vocabulary while disagreeing with the fabric.
CONSTRAINT_REFUSAL_KIND = REFUSAL_KINDS[ConstraintRefusal]
PRODUCT_REQUEST_VIOLATION_KIND = REFUSAL_KINDS[ProductRequestViolation]
SUBJECT_UNAVAILABLE_KIND = REFUSAL_KINDS[SubjectUnavailableRefusal]


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
def estate() -> tuple[str, str]:
    """The CURATED estate, read-only, seeding nothing (`D-IMPL-318`).

    Was: mint a Fluree ledger and a PostgreSQL schema, seed the committed
    fixture into both, and point cp-04 at them. Every run left a ledger behind
    that Fluree, being append-only, can never remove.

    Now: read whatever estate the operator exported. The module asserts the
    same things about the same product; only where the data comes from moved.
    """
    return live_estate()


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
    *,
    credential: str | None = None,
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

    ``credential`` drives the door as somebody OTHER than the principal this
    boot minted for. Defaulted to the boot's own credential so every existing
    caller is unchanged; supplied, it is how an ENTITLEMENT denial is observed
    at all, because a door driven only by the one principal its grant names can
    never reach the deny branch.

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
                        http_client_factory=_client_factory(
                            app, door.credential if credential is None else credential
                        ),
                    )
                except McpServerUnreachable as refused:
                    results[name] = Refused(reason=_flatten(refused))
                except BaseException as refused:  # noqa: BLE001 — flattened below
                    results[name] = Refused(reason=_flatten(refused))
        return results

    return asyncio.run(go())


def _refusal_of(text: str) -> Mapping[str, Any]:
    """The refusal SHELL out of one door outcome, as a mapping.

    The product tool answers with the door's own outcome document — a served
    product under `product_json`, a governed determination under `refusal` —
    and reading the shell through this one function rather than off the top
    level is what keeps a kind assertion from passing over a served answer that
    simply has no `kind` key.
    """
    outcome = json.loads(text)
    refusal = outcome.get("refusal")
    assert refusal is not None, (
        f"the door outcome carries no refusal at all: {text[:1000]}"
    )
    return dict(refusal)


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
    """Read the product resource; return its text, or refuse.

    The text is the served vessel or a refusal SHELL — the resource body IS
    the shell, with `kind` and `replay_reference` at its top level. Since
    `D-IMPL-260` P-C the resolver's `ProductNotServable` is a governed
    determination the door records and answers this way too, so a read of this
    parameterized class's resource succeeds with a `subject-unavailable` shell
    rather than failing at the transport. A transport failure still reaches
    the client as `ccf.mcp.errors.py::McpServerUnreachable`, which
    :func:`drive` turns into a :class:`Refused`.
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
# SUPERSEDED 2026-09-04 (`24.6-L-01`): the constant below was `OVER_CEILING_ASK` and it named an ask aimed at the declared ceiling of 6.
#: The one depth this rung still refuses — above the SUBSTRATE's traversal
#: capability, with authority `technical`.
OVER_CAPABILITY_ASK = "mcp-tool(over the technical capability)"

#: A depth DEEPER THAN ANY TREE IN THIS ESTATE, asked over the DOOR. Under the
#: deleted bound it was refused; it is served now, and the door must be the
#: same contract as the in-process caller about that.
UNEXHIBITED_ASK = f"mcp-tool(max_depth={UNEXHIBITED_DEPTH})"
RESOURCE_READ = "resource-read"
ENUMERATE = "enumerate"
#: The replay record behind each surface's refusal, resolved from the door's
#: OWN store by the `replay_reference` the shell carries — read inside the
#: fixture, while the scratch root still exists. `None` where the surface
#: served, refused at the transport, or carried no resolvable reference.
RECORDS = "__records__"


def _shell_kind(text: str) -> str | None:
    """The `kind` of a resource body that IS a refusal shell; ``None`` otherwise."""
    try:
        body = json.loads(text)
    except ValueError:
        return None
    return body.get("kind") if isinstance(body, dict) else None


def _record_behind(root: pathlib.Path, result: Any) -> Mapping[str, Any] | None:
    """The replay record one door outcome's `replay_reference` resolves to.

    Out of the `FileArtifactStore` under ``root`` — the store `serve.door`
    composes and `produce.py::_serve` writes — by the reference the shell
    carries, never a directory walk. ``None`` rather than a raise: the test
    reading it says *no record* as its own finding.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.artifacts.protocol import parse_artifact_uri
    from ccf.products.refusal import NO_REPLAY_REFERENCE

    if isinstance(result, Refused):
        return None
    # The tool answers `(is_error, text)`; the resource read answers its text.
    text = result[1] if isinstance(result, tuple) else result
    if not isinstance(text, str):
        return None
    # Two wire shapes: the tool nests the shell under `refusal`; the resource
    # body IS the shell, reference at the top level.
    try:
        body = json.loads(text)
        shell = body.get("refusal") if isinstance(body.get("refusal"), dict) else body
        reference = str(shell["replay_reference"])
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    if not reference or reference == NO_REPLAY_REFERENCE:
        return None
    deployment = _load("deployment")
    store = FileArtifactStore(root=root / deployment.ARTIFACT_STORE_DIRNAME)
    try:
        name = parse_artifact_uri(reference)
        return dict(
            json.loads(store.get(content_address=name.artifact_version).decode("utf-8"))
        )
    except Exception:  # noqa: BLE001 — an unresolvable reference is the test's finding
        return None


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
        max_depth=deployment.traversal_depth_capability().max_traversal_depth + 1
    )
    deep = deployment.demonstration_request(max_depth=UNEXHIBITED_DEPTH)
    uri = product_uri(
        tenant=tenant,
        product_class=demonstration.schema_name,
        version=demonstration.schema_version,
    )
    with tempfile.TemporaryDirectory(prefix="cp04-two-callers-door-") as scratch:
        root = pathlib.Path(scratch)
        with serve.door(root=root) as opened:
            results = drive(
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
                    OVER_CAPABILITY_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=over)
                    ),
                    UNEXHIBITED_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=deep)
                    ),
                },
            )
        results[RECORDS] = {
            ask: _record_behind(root, result) for ask, result in results.items()
        }
        return results


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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
)
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
            " would be claiming a tool-only shape `build_egress_server` CAN"
            " express since `24.5-L-09` (`expose_product_resource=False`) and"
            " this door does not choose (`D-34` closed; the resource stays by"
            " ruling)"
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


def refusal_violations(
    *, served: bool, text: str, recorded_detail: str | None
) -> list[str]:
    """Every way a resource read fails `CFT-G13` limb (b).

    THE THREE THINGS THIS CHECKS ARE DIFFERENT THINGS. That the read did not
    serve; that the refusal is for THIS deployment's stated reason rather than
    some unrelated failure; and that **no tree came back** — the last one
    asserted against the payload's own vocabulary, because a check that only
    asserted *"it refused"* would be satisfied by a door that was broken for a
    reason nobody intended, and a check that only asserted *"no exception text
    mentions a tree"* would be satisfied by a door that served one silently.

    **Where the stated reason is read, since `D-IMPL-260` P-C.** The
    resolver's `ProductNotServable` is a governed determination now — the
    door records it and answers the common `subject-unavailable` shell, whose
    `detail` at this deployment's `minimal` level is the external statement.
    So the reason is read off the RECORD the shell's reference names
    (`recorded_detail`), and the wire is held to NOT carry it: a stated reason
    crossing at `minimal` would be the disclosure leak the shell exists to
    close.
    """
    violations: list[str] = []
    if served:
        violations.append(
            "the product RESOURCE served. `CFT-G13` limb (b): a resolve or read"
            " of it returns the refusal type and NEVER a tree — this class is"
            " parameterized and a resource read supplies no anchor and no depth,"
            " so anything it returned would answer a question nobody asked"
        )
    if recorded_detail is None or "PARAMETERIZED class" not in recorded_detail:
        violations.append(
            "the resource read did not refuse for THIS deployment's stated"
            " reason. A refusal for an unrelated reason is not the refusal"
            f" `CFT-G13` asserts. Recorded: {str(recorded_detail)[:600]}"
        )
    if "PARAMETERIZED class" in text:
        violations.append(
            "the deployment's stated reason crossed the wire at `minimal` — the"
            " internal determination leaked into the shell (D-IMPL-260 P-C):"
            f" {text[:600]}"
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
    # The read SUCCEEDS with the common shell (`D-IMPL-260` P-C); "served"
    # means the body is not a governed refusal at all.
    text = read.reason if isinstance(read, Refused) else str(read)
    served = _shell_kind(text) != SUBJECT_UNAVAILABLE_KIND
    record = surfaces[RECORDS].get(RESOURCE_READ)
    internal = (record or {}).get("content_generation_path", {}).get("assembly_refusal")
    internal = json.loads(internal) if isinstance(internal, str) else internal
    violations = refusal_violations(
        served=served,
        text=text,
        recorded_detail=(internal or {}).get("detail") if internal else None,
    )
    assert not violations, (
        "\n".join(violations) + f"\n--- the read returned ---\n{text[:2000]}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
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
    violations = refusal_violations(
        served=True, text=served_text, recorded_detail=None
    )
    assert violations, "a resource read that SERVED A TREE was accepted as a refusal"
    assert any("must never produce" in entry for entry in violations), violations
    assert any("served" in entry for entry in violations), violations


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
)
def test_the_tool_refuses_an_over_capability_depth_rather_than_clamping_it(
    surfaces: dict[str, Any],
) -> None:
    """`CFT-G03`, over the door. The second surface must not be the weaker one.

    Above the substrate's traversal capability is refused BY NAME on the
    in-process caller, and a door that clamped instead would be a serving path
    with a different contract behind it — the request says 101, the walk does
    100, the payload looks fine and the address greens.

    **AND THE REFUSAL IS AN ANSWER, NOT AN ERROR** (`24.6-L-02`, `D-20`). A
    governed determination never reaches an MCP client as a tool error:
    `isError` is `False` and the body carries the `constraint-refusal` shell
    with the bound that refused it. `ToolError` is reserved for a CCF runtime
    failure and carries an opaque id.
    """
    deployment = _load("deployment")
    capability = deployment.traversal_depth_capability()
    result = surfaces[OVER_CAPABILITY_ASK]
    assert not isinstance(result, Refused), (
        "the over-capability ask took the door DOWN rather than answering:"
        f" {result.reason[:1000]}"
    )
    is_error, text = result
    assert not is_error, (
        "a governed refusal reached the client as a TOOL ERROR. `D-20`:"
        " ToolError is reserved for CCF/runtime failure, and a determination"
        f" the fabric made is an answer: {text[:1000]}"
    )
    # THE TOOL ANSWERS WITH A DOOR OUTCOME AND THE SHELL SITS UNDER `refusal`.
    # Read through the envelope rather than off the top level: a check that
    # matched the top-level document would pass over a served product too.
    body = _refusal_of(text)
    assert body.get("kind") == CONSTRAINT_REFUSAL_KIND, (
        f"the door answered with kind {body.get('kind')!r} rather than"
        f" {CONSTRAINT_REFUSAL_KIND!r}: {text[:1000]}"
    )
    assert body.get("key") == deployment.PARAM_MAX_DEPTH, body
    bound = body.get("fields", {}).get("bound")
    bound = json.loads(bound) if isinstance(bound, str) else bound
    assert bound, f"the door's refusal carries no bound at all: {text[:1000]}"
    assert bound["authority"] == "technical", bound
    assert str(bound["value"]) == str(capability.max_traversal_depth), bound
    # `D-IMPL-260` P-F: below `full` the bound crosses WITHOUT its provenance —
    # which substrate set it is fabric state, in the register of the policy
    # bindings — and the RECORD keeps it. This deployment discloses at
    # `minimal` (`ccf_config.yaml`), so the shell has no `source` and the
    # capability identity is read off the record the shell's reference names.
    assert body.get("disclosure") == "minimal", body.get("disclosure")
    assert set(bound) == {"authority", "operator", "value"}, (
        "the shell's bound carries members beyond the actionable three below"
        f" `full`: {sorted(bound)}"
    )
    assert capability.capability_identity not in text, (
        "the substrate identity crossed the boundary at `minimal`:"
        f" {text[:1000]}"
    )
    record = surfaces[RECORDS].get(OVER_CAPABILITY_ASK)
    assert record, (
        "the refusal's replay reference resolves to no record in the door's"
        " own store; a determination crossed with nothing behind it"
    )
    internal = record["content_generation_path"].get("assembly_refusal")
    internal = json.loads(internal) if isinstance(internal, str) else internal
    recorded = (internal or {}).get("fields", {}).get("bound")
    recorded = json.loads(recorded) if isinstance(recorded, str) else recorded
    assert recorded and recorded["source"]["identity"] == capability.capability_identity, (
        "the RECORD does not name the substrate that set the bound; internal"
        f" truth was destroyed to achieve external silence: {recorded}"
    )
    assert "nodes" not in text, (
        "a tree came back beside the refusal, which is what a clamp looks like"
        f" when the error is left in: {text[:1000]}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
)
def test_the_tool_serves_a_depth_the_estate_cannot_exhibit(
    surfaces: dict[str, Any],
) -> None:
    """`D-IMPL-251` C5 over the DOOR — the second surface is not the stricter one.

    A depth deeper than any tree here is an ordinary question. The door serves
    it, echoes the depth asked, and carries the depth actually reached in the
    findings — so a consumer who asked for 8 and got a 3-deep tree can see that
    the estate, and not the fabric, is what stopped there.
    """
    result = surfaces[UNEXHIBITED_ASK]
    assert not isinstance(result, Refused), (
        f"the deep ask took the door down: {result.reason[:1000]}"
    )
    is_error, text = result
    assert not is_error, (
        f"the door REFUSED max_depth={UNEXHIBITED_DEPTH}, which is the bound"
        f" `D-IMPL-251` C5 deleted returning under another name: {text[:1000]}"
    )
    payload = json.loads(json.loads(text)["product_json"])["payload"]
    assert int(payload["max_depth_applied"]) == UNEXHIBITED_DEPTH, payload[
        "max_depth_applied"
    ]
    projection = _load("projection")
    rows = [
        row
        for row in payload["findings"]
        if row["type"] == projection.FINDING_TRAVERSAL
    ]
    assert len(rows) == 1, [row["type"] for row in payload["findings"]]
    assert rows[0]["requested_depth"] == UNEXHIBITED_DEPTH, rows[0]
    assert 0 < rows[0]["depth_reached"] < UNEXHIBITED_DEPTH, rows[0]


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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
)
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
    # AND IT IS AN INVARIANT FAILURE, NOT A GOVERNED DETERMINATION
    # (`24.6-L-02`, `D-33`, plan `24.6-10`). Two authoritative pieces of fabric
    # state disagree — the estate serves a value the declared closed world does
    # not carry — so there is no valid governed answer to return, and the door
    # says exactly that: an OPAQUE failure id and no prose. A consumer who
    # could read the contradiction's text would be reading the estate's shape
    # off an error message.
    # `Error executing tool <name>: ` is FastMCP's OWN prefix on a wrapped
    # `ToolError` (measured against `mcp==1.28.1`, `Tool.run` re-raises every
    # handler exception under that text), and the SDK's own gate over this
    # door — `tests/mcp/test_egress_refusal_channels.py` — asserts exactly
    # that shape: the transport's prefix naming the tool the caller invoked,
    # then OUR opaque id, then nothing. **Found RED at the 24.6 close (F-C
    # (iii))**: this limb asserted the bare id, which is the pre-phase form.
    # The prefix is optional here so a transport that stops wrapping still
    # passes; prose AFTER the id never does.
    assert re.fullmatch(
        rf"(Error executing tool [^:\s]+: )?{CCF_FAILURE_PREFIX}:[0-9a-f]{{32}}",
        text.strip(),
    ), (
        "an invariant failure reached the client as something other than"
        f" [FastMCP's tool prefix +] {CCF_FAILURE_PREFIX}:<id>: {text[:1000]}"
    )
    assert "jurisdiction" not in text, (
        f"the opaque failure leaked the contradiction's prose: {text[:1000]}"
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
# WR-01 — a non-integer max_depth from a caller is refused BY NAME, not coerced.
# ---------------------------------------------------------------------------

NON_INTEGER_ASK = "mcp-tool(max_depth=a non-integer)"


def _non_integer_depth_request(deployment: Any, value: Any) -> Any:
    """The demonstration question with a non-integer `max_depth` on the wire."""
    typed = deployment.demonstration_request()
    parameters = dict(typed.parameters)
    parameters[deployment.PARAM_MAX_DEPTH] = value
    return typed.model_copy(update={"parameters": parameters})


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
)
def test_a_non_integer_max_depth_is_refused_by_name_and_the_door_survives(
    estate: tuple[str, str],
) -> None:
    """**WR-01 (2026-09-01), re-derived by `24.6-L-01`.** A non-integer
    `max_depth` is refused BY NAME, as an ANSWER.

    The original defect: the deployment's own depth resolver did
    `int(parameters[max_depth])`, which raised an uncaught `ValueError` on
    `"six"` for a non-CLI caller and silently coerced `6.9 -> 6` / `True -> 1`.
    `run.py`'s argparse types `--max-depth` as `int`, so the CLI is shielded;
    the MCP door's JSON arguments are not.

    SUPERSEDED 2026-09-04: WR-01's fix was a type guard in the deployment raising `AssemblyRefused`, which the door surfaced as `isError=True` prose a consumer had to string-parse.
    That guard is deleted with the rest of the deployment's depth resolution.
    The SDK's own request step
    (`src/ccf/products/request.py::refuse_request`) already returns a
    `ProductRequestViolation(reason="type-mismatch")` as DATA for exactly this
    condition, so the refusal is now a typed shell with `isError=False` — the
    second, narrower spelling of one rule is gone rather than kept in parallel.

    Sabotage: coercing the value before the request reaches the contract makes
    the door SERVE a walk at a depth the caller did not ask for, which the
    `is_error`/kind assertions below refuse.
    """
    deployment = _load("deployment")
    serve = _load("serve")
    tenant = deployment.tenant_id()
    non_integer = _non_integer_depth_request(deployment, "six")
    demonstration = deployment.demonstration_request()

    with tempfile.TemporaryDirectory(prefix="cp04-non-int-depth-") as scratch:
        with serve.door(root=pathlib.Path(scratch)) as opened:
            results = drive(
                opened,
                {
                    NON_INTEGER_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=non_integer)
                    ),
                    POST_REFUSAL_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=demonstration)
                    ),
                },
            )

    refused = results[NON_INTEGER_ASK]
    assert not isinstance(refused, Refused), (
        "a non-integer max_depth took the door DOWN instead of returning a"
        f" governed error (WR-01): {refused.reason[:1000]}"
    )
    is_error, text = refused
    assert not is_error, (
        "a governed refusal reached the client as a TOOL ERROR (`D-20`):"
        f" {text[:1000]}"
    )
    body = _refusal_of(text)
    assert body.get("kind") == PRODUCT_REQUEST_VIOLATION_KIND, (
        f"the door answered with kind {body.get('kind')!r} rather than"
        f" {PRODUCT_REQUEST_VIOLATION_KIND!r}: {text[:1000]}"
    )
    assert body.get("reason") == "type-mismatch", (
        "the door refused a non-integer max_depth for some other reason than"
        f" its type — WR-01 asks for a refusal that names it: {text[:1000]}"
    )
    assert body.get("key") == deployment.PARAM_MAX_DEPTH, (
        f"the refusal names key {body.get('key')!r} rather than the depth"
        f" parameter: {text[:1000]}"
    )
    assert "nodes" not in text, (
        "a tree came back beside the refusal, which is what a coercion looks"
        f" like when the refusal is left in: {text[:1000]}"
    )

    after = results[POST_REFUSAL_ASK]
    assert not isinstance(after, Refused), (
        f"the door did not stay up after a non-integer max_depth: {after.reason[:1000]}"
    )
    assert not after[0], f"the door refused a valid ask after a non-integer depth: {after[1][:1000]}"


# ---------------------------------------------------------------------------
# The DOOR's entitlement denial — recorded, disclosed, and not an error.
# ---------------------------------------------------------------------------

UNENTITLED_ASK = "mcp-tool(a verified but unentitled principal)"

#: A principal this deployment's entitlement policy does not name. Verified —
#: it holds a real credential this boot minted — and entitled to nothing, which
#: is the ONLY way the deny branch is reachable: an unverified caller is
#: refused by the authentication middleware before a handler body runs, and the
#: boot's own principal is entitled to everything the door serves.
UNENTITLED_PRINCIPAL = "PRIN-NOT-GRANTED"


def test_an_unentitled_principal_gets_a_recorded_shell_and_not_an_error() -> None:
    """`D-34`/`D-IMPL-256` (1) and criterion 36, at cp-04's OWN door.

    Three things together, and each is a different failure if it is missing:

    * the denial is an ANSWER (`is_error` False) carrying the ONE canonical
      `subject-unavailable` shell that a nonexistent subject and an
      unauthorized principal share (`D-27`) — a tool error would make the
      denial distinguishable on the wire from a served-then-refused product;
    * the shell carries a REFERENCE that is not the sentinel — *"no fulfilled
      Context Product does not mean no Decision Replay"*;
    * that reference RESOLVES, in the store `produce.py::_serve` writes, to a
      record whose dimension-1 resource identity names the `mcp-tool` surface
      and this tenant. A well-formed response with nothing behind it is what
      the checker found three times.

    **NO STORE IS TOUCHED AND THAT IS WHY THIS TEST HAS NO LEG MARKER.** The
    entitlement decision happens at the delivery boundary, before the resolver
    runs, so neither system of record is opened — which is itself part of the
    claim: a caller who may not have the product does not cause a read of the
    estate.

    The binding this rests on is plan `24.6-10`'s (`serve.py` passes
    `refusal_recorder=composed.refusal_recorder`); the test lands here because
    this module is the one that drives cp-04's own door.
    """
    import json as _json

    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.artifacts.protocol import parse_artifact_uri
    from ccf.products.refusal import NO_REPLAY_REFERENCE
    from ccf.replay.record import NO_PRODUCT_ADDRESS
    from ccf_runtime.authz.delivery_boundary import SURFACE_MCP_TOOL

    deployment = _load("deployment")
    serve = _load("serve")
    tenant = deployment.tenant_id()
    typed = deployment.demonstration_request()

    with tempfile.TemporaryDirectory(prefix="cp04-unentitled-") as scratch:
        root = pathlib.Path(scratch)
        with serve.door(root=root) as opened:
            # A SECOND VERIFIED CREDENTIAL, for a principal the grant does not
            # name. `FileTokenSource` re-reads on every lookup precisely so a
            # test can add one between calls, which its own docstring says.
            tokens = root / serve.TOKEN_FILE
            table = _json.loads(tokens.read_text(encoding="utf-8"))
            stranger = "stranger-" + "0" * 24
            table[stranger] = {
                "client_id": UNENTITLED_PRINCIPAL,
                "scopes": [opened.scope],
            }
            tokens.write_text(_json.dumps(table), encoding="utf-8")

            results = drive(
                opened,
                {
                    UNENTITLED_ASK: tool_call(
                        tool_arguments(tenant=tenant, typed=typed)
                    )
                },
                credential=stranger,
            )

        answered = results[UNENTITLED_ASK]
        assert not isinstance(answered, Refused), (
            "the unentitled ask took the door DOWN rather than answering it:"
            f" {answered.reason[:1000]}"
        )
        is_error, text = answered
        assert not is_error, (
            "a governed denial reached the client as a TOOL ERROR (`D-20`):"
            f" {text[:1000]}"
        )
        body = _refusal_of(text)
        assert body.get("kind") == SUBJECT_UNAVAILABLE_KIND, (
            f"the door denied with kind {body.get('kind')!r} rather than the"
            f" shared {SUBJECT_UNAVAILABLE_KIND!r}: {text[:1000]}"
        )
        reference = body.get("replay_reference")
        assert reference and reference != NO_REPLAY_REFERENCE, (
            "the denial carries no replay reference, so a decision crossed the"
            f" boundary with no record behind it: {text[:1000]}"
        )

        store = FileArtifactStore(root=root / deployment.ARTIFACT_STORE_DIRNAME)
        name = parse_artifact_uri(reference)
        record = _json.loads(
            store.get(content_address=name.artifact_version).decode("utf-8")
        )
        assert record["tenant_id"] == tenant, record["tenant_id"]
        path = record["content_generation_path"]
        assert path["product_content_address"] == NO_PRODUCT_ADDRESS, path[
            "product_content_address"
        ]
        internal = path.get("assembly_refusal")
        assert internal, (
            "the record carries no refusal at all, so it says a decision"
            f" happened without saying what it was: {sorted(path)}"
        )
        internal = _json.loads(internal) if isinstance(internal, str) else internal
        # THE RECORD HOLDS THE INTERNAL DETERMINATION, NOT THE SHELL. The
        # consumer saw `cause: undisclosed`; the audit plane sees what the
        # fabric actually determined, which is `D-IMPL-253` Q27's *"don't
        # destroy audit truth merely to achieve external suppression silence."*
        fields = internal.get("fields") or {}
        cause = fields.get("cause")
        cause = _json.loads(cause) if isinstance(cause, str) else cause
        assert cause == "unauthorized", (
            f"the RECORD discloses cause {cause!r}; a record that kept only the"
            " shell's `undisclosed` would have destroyed the audit truth the"
            " disclosure step exists to preserve"
        )
        resource = internal.get("resource")
        resource = (
            _json.loads(resource) if isinstance(resource, str) else resource
        )
        assert resource, (
            "the record names no resource-request identity, so it cannot say"
            f" WHAT was asked for by whom: {sorted(internal)}"
        )
        assert resource.get("surface") == SURFACE_MCP_TOOL, resource
        assert resource.get("tenant_id") == tenant, resource
        assert resource.get("address"), resource
        assert resource.get("determined_at"), (
            "the resource identity names no instant, so the denial cannot be"
            f" placed in time: {resource}"
        )
        # BY WHOM is dimension 4's, not the resource identity's — the resource
        # says WHAT was asked for and on which surface, and the perspective
        # says who asked. Read where each actually lives rather than expecting
        # one block to carry both.
        assert (
            record["perspective_conditioning"]["principal_id"]
            == UNENTITLED_PRINCIPAL
        ), record["perspective_conditioning"]


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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
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
        # The resolver `compose` built, over the ONE recorder `compose`
        # constructed (`D-IMPL-256` (2), `24.6-10`): `build_resolver` takes
        # the recorder as a required keyword since that row, and the door
        # (`serve.py`) hands it the same one. **Found RED at the 24.6 close
        # (F-C (v))** — this call predated the keyword.
        resolver = compose.compose(root=pathlib.Path(scratch)).resolver
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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
)
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
