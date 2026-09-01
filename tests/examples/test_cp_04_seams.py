"""The last five of cp-04's sixteen gates — the store, door and assembler seams.

`CFT-G10`, `CFT-G11`, `CFT-G12`, `CFT-G13` and `CFT-G14`, discharging locked
ROADMAP criteria 34 through 38. These five carry the phase's HEADLINE CLAIMS:
*"first multi-store product"*, *"the ladder's first MCP door"* and *"one
standalone assembler"* are asserted here and nowhere else, and the headline
change is the one most likely to ship ungated.

Each is written so that the sabotage `artifacts/gates.yaml` declares against it
turns THIS module red, under THAT gate's own name — which is the whole content
of criterion 42. A gate never seen red is not evidence that it runs.

## The defect waves 8 and 9 each found in their own new gates

**`CFT-G05` and `CFT-G16` each PASSED their own sabotage when written exactly
as their criterion worded it.** `CFT-G05` because `max_depth_applied` is echoed
into the sealed payload, so two content addresses differ even when the walk has
stopped reading depth; `CFT-G16` because a hand-written role map served the
IDENTICAL outcome — 22 detailed and 0, the same class named, every
`carries_class_axis` still agreeing with its own chain. Both needed a second
limb asserting the CONTENT beside the address or outcome limb.

**`CFT-G10` below has that shape and it is named rather than left to be found.**
``examples/cp-04-corporate-family-tree/deployment.py::source_read`` records
``stores_opened`` as a literal pair at the point the two connections are made,
so the opened-store SET DOES NOT MOVE when the attribute leg is made to read
Fluree instead of PostgreSQL. A gate asserting only *"both stores were opened"*
therefore passes its own declared sabotage. The set limb is kept because
criterion 34 asks for it and because it is what catches a leg that stops opening
at all — but it is deliberately NOT the discriminating limb. What discriminates
is (b) the attribute leg issuing statements against the DECLARED attribute table,
and (c) the PROVENANCE of the served attributes: every served value is compared
against a DIRECT `SELECT` this module issues itself, and the served jurisdiction
is shown to appear NOWHERE among the objects Fluree asserts about that node — so
Fluree could not have supplied it.

## What this module refuses to be

**A check that reads a token present in BOTH the compliant and the violating
case measures vocabulary rather than content.** Seven occurrences in this phase.
Every gate below reads what the product DID — which statements ran, which values
were served, which modules the import actually reached, whether a tree came back
— and never a word the product uses about itself.

## Where every expected figure comes from

`artifacts/expected.yaml`, `artifacts/source-vocabulary.yaml`, `backends.yaml`
and `artifacts/assembly-recipe.yaml` — declarations, and never a figure authored
here. Criterion 45 is discharged: the two resolving members and their LEIs come
from `census.anchor_subtree_store_split`, the subtree size from
`census.anchor_subtree`, the LEI-bearing population from `census.lei_coverage`,
the anchor from `census.anchor`.

**The declared STORE ROSTER is read from `backends.yaml::declaration.sources`
and the ROLE of each leg is read from which settings it declares** — a source
declaring `url` and `ledger` is the graph leg, one declaring `dsn` and `schema`
is the relational leg. That is an assertion ABOUT the declaration, the same
posture wave 8 recorded for `CFT-G03` and `CFT-G04`'s depth bounds. What makes
it non-circular is limb (c), which compares served values against a store read
that shares no code with the product.

**The LLM-client roster is `tools/lints/algorithmic.py::LLM_MODULES`** — the
SDK's own, matched with its own
`tools/lints/__init__.py::matches_module`. A roster authored here would be this
module agreeing with itself about what a model client is.

## What is deliberately NOT here

**`CFT-G17` does not exist.** Criterion 41 was WITHDRAWN IN PLACE on 2026-08-31
(Dave) together with ontology role 1, and it is **not** replaced by a
positive-property restatement — that was refused BY NAME as a tautology over a
class-homogeneous population. The roster is SIXTEEN.

**Criterion 37's wording is not touched.** It says the resource is *"enumerable
in `resources/list`"*; measured at an MCP client,
`resources/templates/list` carries the URI template and `resources/list` returns
`[]`, because a URI with placeholders registers as a resource TEMPLATE. That is
an open wording question for Dave (`24.4-09`'s deferred item 7) and this module
does not resolve it: `CFT-G13` asserts BOTH listings as shipped, so neither the
template vanishing nor a concrete entry appearing goes unseen.

## Isolation

Per-module ledger and schema names from `tests/examples/cp_04_seed.py`, for the
reason that module records: `tests/conftest.py::fluree_url` is session-scoped and
env-driven — one server, no per-module container — and six cp-04 modules transact
this one fixture. A fixed ledger name means whichever module ran second cannot
seed at all (`409 err:db/LedgerExists`), and a shared one means a sibling
module's deliberate sabotage leaks into this module's figures permanently,
because Fluree is append-only. Shared CI fixtures colliding by collection order
have already left `leg-postgres` red on `main` in this repository once.

## Why the door driver is imported rather than copied

`CFT-G13` and `CFT-G14` need a real MCP client against the shipped door, and
`tests/examples/test_cp_04_two_callers.py` already holds that driver — one door,
one lifespan, every surface, for the measured reason recorded there
(`StreamableHTTPSessionManager.run()` refuses a second call per instance). This
module imports the DRIVER and writes its own CHECKS: the gate's content belongs
in the gate's module, and a second copy of the driver would be an odd thing to
ship in the module whose subject is *one* implementation serving two callers.

## Vacuity

A precondition test runs first and asserts the seed carries what these gates
need. Every gate is expressed as a function returning the ways an observation
FAILS, so a control can hand the **shipped** check a divergent subject and be
watched refusing it.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

import httpx
import psycopg
import pytest
import yaml

from ccf_runtime.mcp.egress import PRODUCT_URI_TEMPLATE, product_uri
from tools.lints import matches_module
from tools.lints.algorithmic import LLM_MODULES

from .cp_04_seed import ledger_for, schema_for, seed
from .test_cp_04_two_callers import (
    Refused,
    drive,
    enumeration,
    resource_read,
    tool_answer,
    tool_arguments,
    tool_call,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-04-corporate-family-tree"
SERVER = EXAMPLE / "server"
ARTIFACTS = EXAMPLE / "artifacts"
EXPECTED = ARTIFACTS / "expected.yaml"
GATES = ARTIFACTS / "gates.yaml"
RECIPE = ARTIFACTS / "assembly-recipe.yaml"
VOCABULARY = ARTIFACTS / "source-vocabulary.yaml"
BACKENDS = EXAMPLE / "backends.yaml"

#: Both stores. `.github/workflows/ci.yml` exports both legs' variables at JOB
#: level and runs `leg-postgres` and `leg-fluree` as two steps of that one job,
#: so a doubly-marked module is selected twice and runs whole both times.
pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

#: A depth the demonstration does not use, for `CFT-G13` limb (c). Read as an
#: ADDRESS into the declared bounds rather than as a figure: the assertion is
#: that the CALLER's depth reached the walk, never that it had a size.
PLANTED_DEPTH = 1

#: The names this module's four door surfaces are driven under, in one lifespan.
ENUMERATE = "enumerate"
RESOURCE_READ = "resource-read"
DEMONSTRATION_ASK = "mcp-tool(demonstration depth)"
PLANTED_ASK = f"mcp-tool(max_depth={PLANTED_DEPTH})"

#: How the two source legs are told apart, from what each DECLARES rather than
#: from its name. `backends.yaml` gives the graph leg a `url` and a `ledger` and
#: the relational leg a `dsn` and a `schema`; a roster keyed on the literal
#: names would be this module restating `deployment.py`'s constants.
GRAPH_LEG_SETTINGS = frozenset({"url", "ledger"})
RELATIONAL_LEG_SETTINGS = frozenset({"dsn", "schema"})

#: The step whose recipe declaration plan 03 measured and no plan owned a check
#: for. Named, because binding the assertion to the step BY NAME is the whole
#: difference between this check and the vacuous `any(...)` form.
CYCLE_STEP = "Detect cycles"


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package and its modules
    import each other by bare name, while one pytest session runs over a tree
    holding several `deployment`/`produce`/`run` triples. So the cache is checked
    against THIS example's directories and the whole family is evicted together
    when it holds somebody else's — evicting one name at a time would rebuild the
    split-identity problem the eviction prevents. The shape is
    `tests/examples/test_cp_04_two_callers.py::_load`, including its two
    `server/` modules.
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
# The declarations these gates read. None of them is a file a sabotage touches.
# ---------------------------------------------------------------------------


def _yaml(path: pathlib.Path) -> Mapping[str, Any]:
    return dict(yaml.safe_load(path.read_text(encoding="utf-8"))["declaration"])


def census() -> Mapping[str, Any]:
    """`artifacts/expected.yaml`'s census block."""
    return dict(_yaml(EXPECTED)["census"])


def attribute_vocabulary() -> Mapping[str, Any]:
    """The declared attribute table, its key column and what it serves."""
    return dict(_yaml(VOCABULARY)["attributes"])


def lei_predicate() -> str:
    """The IRI the graph carries an LEI under — a DECLARED node predicate."""
    return str(_yaml(VOCABULARY)["graph"]["node_predicates"]["lei"])


@dataclass(frozen=True)
class DeclaredLegs:
    """Which source names this deployment declares, and what role each has."""

    all_sources: frozenset[str]
    graph: str
    relational: str


def declared_legs() -> DeclaredLegs:
    """The two source legs, read from `backends.yaml` by WHAT EACH DECLARES.

    A source declaring a `url` and a `ledger` is the graph leg; one declaring a
    `dsn` and a `schema` is the relational leg. Reading the roles from the
    settings rather than from the literal names keeps this module from
    restating `deployment.py::SOURCE_GRAPH`, which is the file the `CFT-G10`
    sabotage mutates.
    """
    sources = dict(_yaml(BACKENDS)["sources"])
    graph = [
        name
        for name, block in sources.items()
        if GRAPH_LEG_SETTINGS <= frozenset(block["settings"])
    ]
    relational = [
        name
        for name, block in sources.items()
        if RELATIONAL_LEG_SETTINGS <= frozenset(block["settings"])
    ]
    assert len(graph) == 1 and len(relational) == 1, (
        f"backends.yaml declares graph legs {graph} and relational legs"
        f" {relational}; CFT-G10 needs exactly one of each to be able to name"
        " the role split at all"
    )
    assert graph[0] != relational[0], (
        f"one source {graph[0]!r} declares both a ledger and a DSN, so the two"
        " roles cannot be told apart from the declaration"
    )
    return DeclaredLegs(
        all_sources=frozenset(sources), graph=graph[0], relational=relational[0]
    )


# ---------------------------------------------------------------------------
# The estate, and one ask through the shipped in-process caller — OBSERVED.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def estate(fluree_url: str, postgres_dsn: str) -> Iterator[tuple[str, str]]:
    """The committed fixture pair, under names nobody else holds."""
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


@dataclass(frozen=True)
class Observed:
    """One ask, plus what the ASSEMBLY itself recorded while making it.

    The evidence for `CFT-G10` and `CFT-G11` is taken off the `Assembled` the
    shipped adapter observed — `assembler.py::FamilyTreeAssembler.observer`,
    the seam whose own docstring says it exists so `CFT-G10` can see which
    stores THE ASSEMBLY opened rather than which stores a runner opened
    (criterion 34, as clarified by Dave at Gate 1).
    """

    asked_as: str
    payload: Mapping[str, Any]
    content_address: str
    #: What `deployment.py::source_read` recorded where the connections are made.
    stores_opened: tuple[str, ...]
    #: Every statement executed on the attribute connection, counted at the
    #: CONNECTION by `deployment.py::AttributeResolution`'s cursor factory.
    statements: tuple[str, ...]
    #: The LEI roster the attribute leg was asked to resolve.
    requested_leis: tuple[str, ...]
    #: The rows it resolved, keyed by LEI.
    rows: Mapping[str, Mapping[str, Any]]

    @property
    def nodes(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(dict(node) for node in self.payload["nodes"])

    @property
    def roster(self) -> tuple[str, ...]:
        """The served member ROSTER, sorted. Never a count (`D-13`)."""
        return tuple(sorted(str(node["uri"]) for node in self.nodes))

    def node_by_lei(self, lei: str) -> Mapping[str, Any] | None:
        for node in self.nodes:
            if node.get("lei") == lei:
                return node
        return None


def ask_observed(*, asked_as: str, max_depth: int | None = None) -> Observed:
    """Ask through the shipped in-process caller, and keep what the assembly saw.

    Not a reimplementation of the product: the same
    ``ProductClient(product_id=…, adapter=…)`` constructor `run.py` builds
    (`D-IMPL-225` amendment 2), over the same
    ``examples/cp-04-corporate-family-tree/transport.py::FamilyTreeInProcessAdapter``,
    carrying the question
    ``examples/cp-04-corporate-family-tree/deployment.py::demonstration_request``
    composes for both callers.

    The adapter's own ``seen`` list is the observation channel — it is where
    `transport.py` already routes every ``Assembled`` — so nothing here reaches
    around the shipped seam to instrument the run.
    """
    from ccf.client.client import ProductClient

    deployment = _load("deployment")
    transport = _load("transport")

    typed = deployment.demonstration_request(max_depth=max_depth)
    parameters = {
        name: (value if isinstance(value, (str, int, bool)) else format(value, "f"))
        for name, value in typed.parameters.items()
    }
    with tempfile.TemporaryDirectory(prefix="cp04-seams-") as scratch:
        adapter = transport.FamilyTreeInProcessAdapter(root=pathlib.Path(scratch))
        client = ProductClient(
            product_id=transport.declared_product_id(), adapter=adapter
        )
        result = client.ask(parameters, as_of=typed.asked_at)
        assert not result.refused, f"the ask was refused: {result.refusal}"
        assert adapter.seen, (
            "the shipped adapter observed no assembly at all, so CFT-G10 and"
            " CFT-G11 would be reading an empty record rather than a run"
        )
        assembled = adapter.seen[-1]
        resolution = assembled.scenario.attributes
        return Observed(
            asked_as=asked_as,
            payload=dict(result.payload),
            content_address=str(result.content_address),
            stores_opened=tuple(assembled.stores_opened),
            statements=tuple(resolution.statements),
            requested_leis=tuple(resolution.requested),
            rows={key: dict(value) for key, value in resolution.rows.items()},
        )


@pytest.fixture(scope="module")
def observed(estate: tuple[str, str]) -> Observed:
    """One ask at the demonstration depth, with the assembly observed."""
    return ask_observed(asked_as="in-process, the demonstration question")


# ---------------------------------------------------------------------------
# Two DIRECT store reads, sharing no code with the product.
# ---------------------------------------------------------------------------


def direct_attribute_row(
    dsn: str, schema: str, lei: str
) -> Mapping[str, Any] | None:
    """One row from the declared attribute table, read by THIS module.

    `CFT-G10`'s provenance limb compares the SERVED attributes against this. The
    connection, the SQL and the decoding are all written here rather than
    borrowed from `deployment.py`, because `deployment.py` is the file the
    sabotage mutates — an expectation resolving from the mutated file moves with
    it, and the gate then passes its own sabotage.
    """
    declared = attribute_vocabulary()
    table = str(declared["table"])
    key_column = str(declared["key_column"])
    columns = [str(name) for name in declared["served_columns"]]
    with psycopg.connect(dsn) as handle:
        with handle.cursor() as cursor:
            cursor.execute(
                f'SELECT {", ".join(columns)} FROM "{schema}".{table}'
                f" WHERE {key_column} = %s",
                (lei,),
            )
            record = cursor.fetchone()
    if record is None:
        return None
    return {name: record[index] for index, name in enumerate(columns)}


def fluree_objects_for(url: str, ledger: str, subject: str) -> tuple[str, ...]:
    """Every object Fluree asserts about one subject, as text.

    Used to show that a served attribute could NOT have come from the graph
    leg: if the value the payload carries appears nowhere among these, Fluree
    did not supply it, whatever the code says about itself.
    """
    query = f"SELECT ?p ?o FROM <{ledger}> WHERE {{ <{subject}> ?p ?o }}"
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{url.rstrip('/')}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=query.encode("utf-8"),
        )
        response.raise_for_status()
        bindings = response.json()["results"]["bindings"]
    return tuple(str(row["o"]["value"]) for row in bindings if "o" in row)


def fluree_lei_roster(url: str, ledger: str) -> tuple[str, ...]:
    """Every LEI the graph leg carries, read by THIS module.

    `CFT-G11`'s scale limb hands this roster to the shipped
    ``deployment.py::resolve_attributes`` and asserts it still takes ONE
    statement. The demonstration subtree cannot carry that claim on its own —
    only two of its twenty-two members hold an LEI — so a per-node fan-out over
    it would issue two statements rather than the hundreds the gate exists to
    forbid.
    """
    query = (
        f"SELECT ?s ?o FROM <{ledger}> WHERE {{ ?s <{lei_predicate()}> ?o }}"
    )
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{url.rstrip('/')}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=query.encode("utf-8"),
        )
        response.raise_for_status()
        bindings = response.json()["results"]["bindings"]
    return tuple(sorted({str(row["o"]["value"]) for row in bindings if "o" in row}))


# ---------------------------------------------------------------------------
# The door — ONE door, ONE lifespan, every surface these two gates read.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def surfaces(estate: tuple[str, str]) -> dict[str, Any]:
    """The SHIPPED door, built by the SHIPPED program, driven once.

    `serve.py::door` is a context manager returning the configured server rather
    than running it, so the construction a reader spawns on stdio is the
    construction driven here. Every surface is driven against ONE door because
    it has to be: measured against `mcp==1.28.1`,
    `StreamableHTTPSessionManager.run()` refuses a second call per instance and
    `FastMCP` holds one manager per server — see
    `tests/examples/test_cp_04_two_callers.py::drive`.
    """
    deployment = _load("deployment")
    serve = _load("serve")
    tenant = deployment.tenant_id()
    demonstration = deployment.demonstration_request()
    planted = deployment.demonstration_request(max_depth=PLANTED_DEPTH)
    uri = product_uri(
        tenant=tenant,
        product_class=demonstration.schema_name,
        version=demonstration.schema_version,
    )
    with tempfile.TemporaryDirectory(prefix="cp04-seams-door-") as scratch:
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
                },
            )


# ---------------------------------------------------------------------------
# PRECONDITIONS — what a green gate below is allowed to mean.
# ---------------------------------------------------------------------------


def test_the_seed_carries_what_these_five_gates_need(
    observed: Observed, estate: tuple[str, str]
) -> None:
    """Without this, a green gate below could be a true statement about nothing.

    Six ways that could happen: an empty node set, a subtree whose declared size
    the seed does not reproduce, no member resolving in the attribute store at
    all (which would make `CFT-G10`'s provenance limb vacuous), a single-member
    LEI roster (which would make `CFT-G11`'s batching claim untestable), a
    declared source roster that is not two legs, and an empty attribute column
    roster.
    """
    ledger, schema = estate
    declared = census()
    legs = declared_legs()
    vocabulary = attribute_vocabulary()

    assert observed.nodes, (
        "the demonstration ask served no nodes at all, so every per-node claim"
        " below would hold over the empty set"
    )
    assert len(observed.roster) == int(declared["anchor_subtree"]["reachable_nodes"]), (
        f"the seed served {len(observed.roster)} members where"
        f" expected.yaml::census.anchor_subtree declares"
        f" {declared['anchor_subtree']['reachable_nodes']}"
    )
    split = declared["anchor_subtree_store_split"]
    assert split["the_two_resolving"], (
        "expected.yaml declares no subtree member resolving in the attribute"
        " store, so CFT-G10's provenance limb would have nothing to compare"
    )
    assert len(legs.all_sources) == 2, (
        f"backends.yaml declares {sorted(legs.all_sources)}; criterion 34 is"
        " about TWO stores and this deployment declares"
        f" {len(legs.all_sources)}"
    )
    assert vocabulary["served_columns"], (
        "source-vocabulary.yaml declares no served attribute columns, so a"
        " provenance comparison would compare two empty mappings"
    )

    roster = fluree_lei_roster(*_url_and_ledger(estate))
    assert len(roster) == int(declared["lei_coverage"]["nodes_carrying_lei"]), (
        f"the graph leg carries {len(roster)} LEIs where"
        f" expected.yaml::census.lei_coverage declares"
        f" {declared['lei_coverage']['nodes_carrying_lei']}"
    )
    assert len(roster) > 1, (
        "the graph leg carries at most one LEI, so ONE statement for the whole"
        " roster would not be a batching claim at all"
    )
    assert schema and ledger, "the estate fixture named no schema or no ledger"


def _url_and_ledger(estate: tuple[str, str]) -> tuple[str, str]:
    """The graph leg's URL and ledger, from the environment the fixture set."""
    ledger, _schema = estate
    return os.environ["CCF_CP_04_FLUREE_URL"], ledger


# ---------------------------------------------------------------------------
# CFT-G10 — BOTH stores opened, each for its declared role.
# ---------------------------------------------------------------------------


def store_violations(
    *,
    opened: Sequence[str],
    legs: DeclaredLegs,
    statements: Sequence[str],
    attribute_table: str,
    provenance: Sequence["Provenance"],
) -> list[str]:
    """Every way one run fails `CFT-G10`.

    Three limbs, and only two of them can discriminate the declared sabotage.

    **Limb (a) — the opened-store SET.** Criterion 34 asks for it and it is what
    catches a leg that stops opening at all. It CANNOT catch the declared
    sabotage: ``deployment.py::source_read`` records the pair as a literal where
    the connections are made, so serving attributes out of Fluree leaves it
    unchanged. Stated here rather than left to be discovered, because
    `CFT-G05` and `CFT-G16` each shipped a first draft with exactly this shape.

    **Limb (b) — the ROLE split.** The attribute leg must have issued at least
    one statement, and every statement it issued must name the DECLARED
    attribute table. A run that read attributes out of the graph leg issues none.

    **Limb (c) — PROVENANCE, per served member.** Every served attribute value
    is compared against a direct `SELECT` this module issued itself, and the
    served jurisdiction is required to appear NOWHERE among the objects the
    graph leg asserts about that node. This is the limb that says the value
    could only have come from the relational leg.
    """
    violations: list[str] = []

    missing = sorted(legs.all_sources - set(opened))
    if missing:
        violations.append(
            f"CFT-G10: the assembly opened {sorted(opened)} and never opened"
            f" {missing}. backends.yaml declares {sorted(legs.all_sources)}, and"
            " criterion 34 is that THE ASSEMBLY opened both — a fixture that"
            " pre-opened them and handed the product a populated graph does not"
            " satisfy it"
        )
    intruders = sorted(set(opened) - legs.all_sources)
    if intruders:
        violations.append(
            f"CFT-G10: the assembly opened {intruders}, which backends.yaml"
            " does not declare as a source of this product"
        )

    if not statements:
        violations.append(
            f"CFT-G10: the relational leg {legs.relational!r} issued NO"
            " statement, so the attributes on the served payload came from"
            " somewhere other than the store declared to hold them"
        )
    off_table = sorted(
        {text for text in statements if attribute_table not in text}
    )
    if off_table:
        violations.append(
            f"CFT-G10: the relational leg issued {len(off_table)} statement(s)"
            f" naming no {attribute_table!r}: {[text[:120] for text in off_table]}"
        )

    if not provenance:
        violations.append(
            "CFT-G10: no served member's attributes were checked for"
            " provenance, so the role split holds over the empty set"
        )
    for entry in provenance:
        if entry.served is None:
            violations.append(
                f"CFT-G10: member {entry.uri!r} was served NO attributes at all,"
                f" while the relational leg holds a row for {entry.lei!r} — a"
                " served payload that dropped what the declared store answered"
            )
            continue
        if entry.direct is None:
            violations.append(
                f"CFT-G10: expected.yaml declares {entry.lei!r} resolving in"
                f" {attribute_table!r} and a direct SELECT found no row, so this"
                " gate cannot tell where the served value came from"
            )
            continue
        disagreeing = sorted(
            name
            for name, value in entry.direct.items()
            if entry.served.get(name) != value
        )
        if disagreeing:
            violations.append(
                f"CFT-G10: member {entry.uri!r} was served"
                f" {[(name, entry.served.get(name)) for name in disagreeing]}"
                f" where a DIRECT read of {attribute_table!r} holds"
                f" {[(name, entry.direct[name]) for name in disagreeing]}. The"
                " attributes on the payload are not the ones the declared"
                " attribute store holds"
            )
        if entry.jurisdiction is None:
            violations.append(
                f"CFT-G10: {entry.uri!r} carries no value in the declared"
                " jurisdiction column, so this member cannot carry the"
                " provenance claim"
            )
        elif entry.jurisdiction in entry.graph_objects:
            violations.append(
                f"CFT-G10: the graph leg {legs.graph!r} itself asserts"
                f" {entry.jurisdiction!r} about {entry.uri!r}, so the served"
                " value could have come from either store and this limb proves"
                " nothing about which one supplied it"
            )
    return violations


@dataclass(frozen=True)
class Provenance:
    """One served member's attributes, beside what each store actually holds."""

    uri: str
    lei: str
    #: What the payload served for this member.
    served: Mapping[str, Any] | None
    #: What a DIRECT `SELECT` this module issued returned.
    direct: Mapping[str, Any] | None
    #: The value the declared jurisdiction column holds.
    jurisdiction: Any
    #: Every object the graph leg asserts about this member.
    graph_objects: tuple[str, ...]


@pytest.fixture(scope="module")
def provenance(
    observed: Observed, estate: tuple[str, str], postgres_dsn: str
) -> tuple[Provenance, ...]:
    """The declared resolving members, with both stores read directly.

    A ROSTER and never a sample: `expected.yaml` declares which members resolve,
    and every one of them is checked. `D-13` — a right count with a wrong member
    audits clean forever.
    """
    _ledger, schema = estate
    url, ledger = _url_and_ledger(estate)
    jurisdiction_column = str(attribute_vocabulary()["jurisdiction_column"])
    entries: list[Provenance] = []
    for declared in census()["anchor_subtree_store_split"]["the_two_resolving"]:
        lei = str(declared["lei"])
        node = observed.node_by_lei(lei)
        assert node is not None, (
            f"expected.yaml declares {declared['uri']!r} in the subtree and no"
            f" served member carries its LEI {lei!r}"
        )
        uri = str(node["uri"])
        direct = direct_attribute_row(postgres_dsn, schema, lei)
        entries.append(
            Provenance(
                uri=uri,
                lei=lei,
                served=(
                    None if node.get("attributes") is None else dict(node["attributes"])
                ),
                direct=direct,
                jurisdiction=(
                    None if direct is None else direct.get(jurisdiction_column)
                ),
                graph_objects=fluree_objects_for(url, ledger, uri),
            )
        )
    return tuple(entries)


def test_cft_g10_the_assembly_opened_both_stores(
    observed: Observed, provenance: tuple[Provenance, ...]
) -> None:
    """`CFT-G10` (criterion 34). Both stores, each for its declared role.

    Fluree for the edges and the ontology, PostgreSQL for the attributes, and
    the ASSEMBLY is the subject rather than the runner — Dave's Gate 1
    clarification, which `assembler.py::stores_opened` records where the
    connections are made.

    Sabotaged by serving attributes from Fluree. **That sabotage does not move
    the opened-store set**, which is why the role and provenance limbs exist.
    """
    violations = store_violations(
        opened=observed.stores_opened,
        legs=declared_legs(),
        statements=observed.statements,
        attribute_table=str(attribute_vocabulary()["table"]),
        provenance=provenance,
    )
    assert not violations, (
        f"CFT-G10 failed against {observed.asked_as}:\n" + "\n".join(violations)
    )


def test_the_store_check_refuses_a_run_that_opened_one_store() -> None:
    """**Vacuity control.** One store is not two stores."""
    legs = declared_legs()
    violations = store_violations(
        opened=[legs.graph],
        legs=legs,
        statements=["SELECT lei FROM legal_entity"],
        attribute_table="legal_entity",
        provenance=[_compliant_provenance()],
    )
    assert violations, "a run that opened one store was accepted"
    assert any("never opened" in entry for entry in violations), violations


def test_the_store_check_refuses_an_attribute_leg_that_issued_nothing() -> None:
    """**Sabotage control.** Attributes served from the graph leg issue no SQL."""
    legs = declared_legs()
    violations = store_violations(
        opened=[legs.graph, legs.relational],
        legs=legs,
        statements=[],
        attribute_table="legal_entity",
        provenance=[_compliant_provenance()],
    )
    assert violations, "an attribute leg that issued no statement was accepted"
    assert any("issued NO" in entry for entry in violations), violations


def test_the_store_check_refuses_a_served_value_the_attribute_store_disagrees_with() -> None:
    """**Sabotage control, and this is the discriminating limb.**

    The opened-store set is compliant and the SQL is compliant; only the served
    value differs from what a direct read of the declared store holds. That is
    what serving an attribute out of the graph leg looks like from the payload.
    """
    legs = declared_legs()
    compliant = _compliant_provenance()
    violations = store_violations(
        opened=[legs.graph, legs.relational],
        legs=legs,
        statements=["SELECT lei, legal_jurisdiction FROM legal_entity"],
        attribute_table="legal_entity",
        provenance=[
            Provenance(
                uri=compliant.uri,
                lei=compliant.lei,
                served={"legal_jurisdiction": "SOMEWHERE ELSE"},
                direct={"legal_jurisdiction": "US-DE"},
                jurisdiction="US-DE",
                graph_objects=compliant.graph_objects,
            )
        ],
    )
    assert violations, "a served value the attribute store disagrees with was accepted"
    assert any("DIRECT read" in entry for entry in violations), violations


def test_the_store_check_refuses_a_value_the_graph_leg_could_also_have_supplied() -> None:
    """**Provenance control.** A value both stores hold proves nothing.

    If the graph leg asserted the served jurisdiction too, then agreement with
    PostgreSQL would not say which store supplied it — the check must refuse to
    call that provenance.
    """
    legs = declared_legs()
    violations = store_violations(
        opened=[legs.graph, legs.relational],
        legs=legs,
        statements=["SELECT lei, legal_jurisdiction FROM legal_entity"],
        attribute_table="legal_entity",
        provenance=[
            Provenance(
                uri="x://member",
                lei="LEI",
                served={"legal_jurisdiction": "US-DE"},
                direct={"legal_jurisdiction": "US-DE"},
                jurisdiction="US-DE",
                graph_objects=("US-DE", "Some Label"),
            )
        ],
    )
    assert violations, "a value both stores hold was accepted as provenance"
    assert any("could have come from either store" in entry for entry in violations), (
        violations
    )


def test_the_store_check_refuses_an_empty_provenance_roster() -> None:
    """**Vacuity control.** A provenance claim over no member is not a claim."""
    legs = declared_legs()
    violations = store_violations(
        opened=[legs.graph, legs.relational],
        legs=legs,
        statements=["SELECT lei FROM legal_entity"],
        attribute_table="legal_entity",
        provenance=[],
    )
    assert violations, "an empty provenance roster was accepted"
    assert any("holds over the empty set" in entry for entry in violations), violations


def _compliant_provenance() -> Provenance:
    """One member whose provenance is in order, for the controls to vary."""
    return Provenance(
        uri="x://member",
        lei="LEI",
        served={"legal_jurisdiction": "US-DE"},
        direct={"legal_jurisdiction": "US-DE"},
        jurisdiction="US-DE",
        graph_objects=("Some Label",),
    )


# ---------------------------------------------------------------------------
# CFT-G11 — the node set resolves to attributes in ONE batched query.
# ---------------------------------------------------------------------------


def batching_violations(
    *, statements: Sequence[str], requested: Sequence[str], subject: str
) -> list[str]:
    """Every way one attribute resolution fails `CFT-G11`.

    A COUNT OF EXACTLY ONE, with the roster it resolved beside it. "Few" is not
    one, and one statement for one key is not batching — so the roster is
    required to carry more than a single member before the count means anything.
    """
    violations: list[str] = []
    if len(requested) < 2:
        violations.append(
            f"CFT-G11: {subject} asked the attribute leg for {list(requested)},"
            " which is fewer than two keys. One statement for one key is not a"
            " batched resolution and this gate would be satisfied by a fan-out"
        )
    if len(statements) != 1:
        violations.append(
            f"CFT-G11: {subject} resolved {len(requested)} key(s) in"
            f" {len(statements)} statement(s), not 1. A per-node fan-out works"
            " at depth 2 and collapses at depth 4, which is the failure the"
            " whitepaper's DataLoader-style resolution exists to prevent."
            f" Statements: {[text[:120] for text in statements]}"
        )
    return violations


@pytest.fixture(scope="module")
def whole_estate_resolution(estate: tuple[str, str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The SHIPPED resolver, driven over EVERY LEI the graph leg carries.

    **This is `CFT-G11`'s scale limb and it is not decoration.** Measured
    against the committed fixture, only two of the demonstration subtree's
    twenty-two members carry an LEI, so a per-node fan-out over the subtree
    issues TWO statements rather than the hundreds the gate's own declared
    sabotage describes. The claim *"one batched query"* is only worth anything
    at a roster big enough for a fan-out to be visible, so the shipped
    ``deployment.py::resolve_attributes`` is driven over the whole LEI-bearing
    population — read out of the graph leg by this module — and required to
    still take one statement.

    Returns the requested roster and the statements it took.
    """
    deployment = _load("deployment")
    roster = fluree_lei_roster(*_url_and_ledger(estate))
    resolution = deployment.resolve_attributes(roster)
    return tuple(resolution.requested), tuple(resolution.statements)


def test_cft_g11_attributes_resolve_in_one_batched_query(
    observed: Observed,
    whole_estate_resolution: tuple[tuple[str, ...], tuple[str, ...]],
) -> None:
    """`CFT-G11` (criterion 35). ONE batched PostgreSQL query, at two scales.

    The statements are counted at the CONNECTION by
    ``deployment.py::AttributeResolution``'s cursor factory, so a query fired
    anywhere on that connection is counted even if it does not go through
    ``resolve_attributes``' own call site.

    Sabotaged by firing one query per node.
    """
    requested, statements = whole_estate_resolution
    violations = batching_violations(
        statements=observed.statements,
        requested=observed.requested_leis,
        subject=f"the demonstration subtree ({len(observed.roster)} members)",
    )
    violations += batching_violations(
        statements=statements,
        requested=requested,
        subject="the whole LEI-bearing population",
    )
    assert not violations, "\n".join(violations)


def test_the_batching_check_refuses_a_per_node_fan_out() -> None:
    """**Sabotage control.** One query per node is what this gate forbids."""
    violations = batching_violations(
        statements=[f"SELECT ... WHERE lei = '{n}'" for n in ("a", "b", "c")],
        requested=("a", "b", "c"),
        subject="a fan-out",
    )
    assert violations, "a three-statement fan-out was accepted as one batch"
    assert any("not 1" in entry for entry in violations), violations


def test_the_batching_check_refuses_a_single_key_roster() -> None:
    """**Vacuity control.** One statement for one key is not batching."""
    violations = batching_violations(
        statements=["SELECT ... = ANY(...)"], requested=("only",), subject="one key"
    )
    assert violations, "a single-key resolution was accepted as a batched one"
    assert any("fewer than two keys" in entry for entry in violations), violations


def test_the_batching_check_refuses_a_leg_that_issued_nothing() -> None:
    """**Vacuity control.** Zero statements is not one statement."""
    violations = batching_violations(
        statements=[], requested=("a", "b"), subject="a leg that ran nothing"
    )
    assert violations, "an attribute leg that issued no statement was accepted"
    assert any("not 1" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G12 — no LLM client is reachable from any section D step.
# ---------------------------------------------------------------------------


def recipe_steps() -> tuple[Mapping[str, Any], ...]:
    """`artifacts/assembly-recipe.yaml`'s declared steps."""
    return tuple(dict(step) for step in _yaml(RECIPE)["steps"])


def step_modules() -> tuple[str, ...]:
    """The importable module each §D step's `sdk_mechanism` names.

    Read from the DECLARATION, so the roots of the reachability walk are the
    steps the product says it runs rather than a list authored here. Two shapes
    appear in that field — `src/ccf/<path>.py::Symbol` and
    `examples/cp-04-corporate-family-tree/<name>.py::Symbol` — plus trailing
    prose after an em dash, which is stripped by taking the text up to `.py`.
    """
    names: list[str] = []
    for step in recipe_steps():
        mechanism = str(step.get("sdk_mechanism") or "")
        head, marker, _rest = mechanism.partition(".py")
        if not marker:
            continue
        path = head.split()[-1] if head.split() else ""
        if path.startswith("src/"):
            names.append(path[len("src/") :].replace("/", "."))
        elif path.startswith("examples/cp-04-corporate-family-tree/"):
            names.append(pathlib.Path(path).stem)
    # The assembler and the spine host every step whether or not the recipe
    # names their files, so both are walked too — a §D step reached through
    # `produce.py` is still a §D step.
    names.extend(["assembler", "produce"])
    return tuple(sorted(set(names)))


def reached_modules(roots: Sequence[str]) -> tuple[str, ...]:
    """The IMPORT CLOSURE of ``roots``, measured in a fresh interpreter.

    Not an AST scan of the roots' own import statements: a model client reached
    three modules deep is still reachable, and a scan of the example's own
    source would never see it. The closure is the difference in ``sys.modules``
    across the imports, taken in a subprocess so this session's own imports —
    pytest's, this module's — cannot contribute to it.
    """
    program = (
        "import json, sys\n"
        "base = set(sys.modules)\n"
        f"for name in {list(roots)!r}:\n"
        "    __import__(name)\n"
        "print(json.dumps(sorted(set(sys.modules) - base)))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(EXAMPLE), str(SERVER), os.environ.get("PYTHONPATH", "")]
            ),
        },
        check=False,
    )
    assert completed.returncode == 0, (
        "the import closure could not be measured — the assembly path did not"
        f" import at all:\n{completed.stderr[-3000:]}"
    )
    return tuple(json.loads(completed.stdout))


def import_sites(paths: Sequence[pathlib.Path]) -> tuple[tuple[str, str], ...]:
    """Every module name imported anywhere in ``paths``, at ANY nesting depth.

    Function-level and conditional imports included, because a lazily-imported
    client is still a model call in the algorithmic path — the reason
    `tools/lints/algorithmic.py` gives for reading deferred imports too. Read
    from the AST rather than by grepping the text: these modules name
    `anthropic` and `openai` in PROSE, and a text search would find the claim
    and read it as the violation.
    """
    found: list[tuple[str, str]] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.extend((path.name, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append((path.name, node.module))
                found.extend(
                    (path.name, f"{node.module}.{alias.name}") for alias in node.names
                )
    return tuple(found)


def llm_violations(
    *,
    roots: Sequence[str],
    reached: Sequence[str],
    sites: Sequence[tuple[str, str]],
) -> list[str]:
    """Every way the assembly path fails `CFT-G12`.

    The roster is the SDK's own ``tools/lints/algorithmic.py::LLM_MODULES`` and
    the match is its own ``tools/lints/__init__.py::matches_module``, which
    resolves the parent-named spelling (`from ccf import llm`) as well as the
    dotted one — the hole that lint's own docstring records having survived a
    suite that tested only the vendor spellings.
    """
    violations: list[str] = []
    if not roots:
        violations.append(
            "CFT-G12: the recipe named no §D step module at all, so the"
            " reachability walk had no root and proves nothing"
        )
    if not reached:
        violations.append(
            "CFT-G12: the import closure is empty, so the walk read nothing and"
            " a clean result would be a report over an empty tree"
        )
    if not sites:
        violations.append(
            "CFT-G12: no import statement was parsed out of the example, so the"
            " deferred-import half of this gate asserted nothing"
        )
    for name in sorted(set(reached)):
        if matches_module(name, LLM_MODULES):
            violations.append(
                f"CFT-G12: {name!r} is REACHABLE from the §D steps"
                f" {list(roots)}. A model reachable from any step makes this"
                " Assembly Mode 2, and the declared 1 becomes false"
            )
    for filename, name in sites:
        if matches_module(name, LLM_MODULES):
            violations.append(
                f"CFT-G12: {filename} imports {name!r}. A lazily-imported client"
                " is still a model call in the algorithmic path"
            )
    return violations


@pytest.fixture(scope="module")
def assembly_path_closure() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The §D step roots and their measured import closure."""
    roots = step_modules()
    return roots, reached_modules(roots)


def test_cft_g12_no_llm_client_is_reachable_from_any_step(
    assembly_path_closure: tuple[tuple[str, ...], tuple[str, ...]],
) -> None:
    """`CFT-G12` (criterion 36). No LLM client is reachable from any §D step.

    Assembly Mode 1 is a registration-time commitment that no step calls a
    model. This gate makes it checkable rather than asserted, in two halves: the
    measured import CLOSURE of every module the recipe names as a step, and
    every import statement in the example's own Python at any nesting depth.

    Sabotaged by making one reachable from a §D step.
    """
    roots, reached = assembly_path_closure
    sites = import_sites(sorted(EXAMPLE.glob("*.py")) + sorted(SERVER.glob("*.py")))
    violations = llm_violations(roots=roots, reached=reached, sites=sites)
    assert not violations, "\n".join(violations)


def test_the_llm_check_refuses_a_reachable_client() -> None:
    """**Sabotage control.** A vendor SDK anywhere in the closure."""
    violations = llm_violations(
        roots=("deployment",),
        reached=("json", "anthropic", "httpx"),
        sites=(("deployment.py", "httpx"),),
    )
    assert violations, "a reachable vendor client was accepted"
    assert any("REACHABLE" in entry for entry in violations), violations


def test_the_llm_check_refuses_a_deferred_import() -> None:
    """**Sabotage control.** A client imported inside a function.

    The closure limb cannot see this one until the function runs, which is why
    the AST limb exists beside it.
    """
    violations = llm_violations(
        roots=("projection",),
        reached=("json", "httpx"),
        sites=(("projection.py", "openai"),),
    )
    assert violations, "a deferred vendor import was accepted"
    assert any("lazily-imported" in entry for entry in violations), violations


def test_the_llm_check_refuses_the_parent_named_spelling() -> None:
    """**Sabotage control.** `from ccf import llm` is the SDK's own seam.

    That spelling is the hole `tools/lints/algorithmic.py`'s docstring records
    having survived a suite testing only the single-segment vendor names.
    """
    violations = llm_violations(
        roots=("produce",),
        reached=("json", "ccf.llm"),
        sites=(("produce.py", "json"),),
    )
    assert violations, "the SDK's own LLM seam was accepted in the closure"
    assert any("ccf.llm" in entry for entry in violations), violations


def test_the_llm_check_refuses_an_empty_walk() -> None:
    """**Vacuity control.** A clean report over nothing is not a clean report."""
    violations = llm_violations(roots=(), reached=(), sites=())
    assert violations, "an empty walk was reported as satisfying CFT-G12"
    assert any("no root" in entry for entry in violations), violations
    assert any("read nothing" in entry for entry in violations), violations


def test_the_step_modules_come_from_the_recipe_and_are_not_authored_here() -> None:
    """The roots are the DECLARED steps, and both kinds are present.

    Without this, `step_modules` could silently return only the example's two
    fallback names and `CFT-G12` would be walking a much smaller closure than it
    reports.
    """
    roots = step_modules()
    assert any(name.startswith("ccf.") for name in roots), (
        f"the recipe named no `src/ccf` step module; roots are {list(roots)}"
    )
    local = {name for name in roots if "." not in name}
    assert len(local) >= 3, (
        f"the recipe named too few of the example's own step modules: {sorted(local)}"
    )
    declared = {str(step["name"]) for step in recipe_steps()}
    assert len(declared) == len(recipe_steps()), (
        "two recipe steps share a name, so a per-step assertion cannot address"
        " one of them"
    )


# ---------------------------------------------------------------------------
# CFT-G13 — the tool serves; the registered product resource refuses.
# ---------------------------------------------------------------------------


def door_violations(
    *,
    resources: Sequence[str],
    templates: Sequence[str],
    resource_served: bool,
    resource_text: str,
    tool_refused: bool,
    tool_text: str,
    tool_payload: Mapping[str, Any] | None,
    asked_depth: int,
    declared_default_depth: int,
    declared_anchor: str,
) -> list[str]:
    """Every way this door fails `CFT-G13`.

    Three limbs, asserted TOGETHER because each alone is satisfiable by a broken
    door. A gate asserting only the refusal passes on a door where nothing
    works at all; a gate asserting only the tool passes on a door that also
    serves a standing answer.

    **(a) The resource is registered and enumerable.** BOTH listings are read.
    The TEMPLATE must be there — that is where a parameterized product URI
    actually surfaces. `resources/list` must stay EMPTY, because a concrete
    entry there would advertise a standing instance of a class with no standing
    answer. Criterion 37's amended wording names `resources/list`; measured at a
    client the product enumerates in `resources/templates/list`. **That wording
    question is open with Dave and is not resolved here** — asserting both
    listings means neither the template vanishing nor a concrete entry appearing
    goes unseen, whichever way the wording lands.

    **(b) A read of it refuses BY NAME and never serves a tree.** Three separate
    things: that it did not serve; that it refused for THIS deployment's stated
    reason rather than some unrelated failure; and that no tree vocabulary came
    back.

    **(c) The TOOL is the path that serves, on the CALLER's arguments.** The
    depth the caller asked for has to reach the walk, so the assertion is
    against the planted depth and not the declared default — the two are
    different numbers precisely so a door substituting its own default is
    visible.
    """
    violations: list[str] = []

    if PRODUCT_URI_TEMPLATE not in templates:
        violations.append(
            f"CFT-G13 (a): the product resource template {PRODUCT_URI_TEMPLATE!r}"
            f" is not enumerable — templates are {list(templates)}. The resource"
            " IS registered and IS enumerable; a door that hid it would be"
            " claiming a tool-only shape `build_egress_server` cannot express"
            " (`D-34`)"
        )
    if resources:
        violations.append(
            f"CFT-G13 (a): `resources/list` carries {list(resources)} — this"
            " class is parameterized and has no standing, parameter-free"
            " answer, so a concrete resource entry advertises an instance"
            " nothing can serve"
        )

    if resource_served:
        violations.append(
            "CFT-G13 (b): the product RESOURCE served. A resolve or read of it"
            " returns the refusal type and NEVER a tree — this class is"
            " parameterized and a resource read supplies no anchor and no"
            " depth, so anything it returned would answer a question nobody"
            " asked"
        )
    if "PARAMETERIZED class" not in resource_text:
        violations.append(
            "CFT-G13 (b): the resource read did not refuse for THIS"
            " deployment's stated reason. A refusal for an unrelated reason is"
            f" not the refusal this gate asserts. Got: {resource_text[:600]}"
        )
    for token in ('"nodes"', '"anchor"', '"findings"', "type_chain"):
        if token in resource_text:
            violations.append(
                f"CFT-G13 (b): a resource read returned {token} — that is a"
                " TREE, and the one thing this surface must never produce"
            )

    if tool_refused or tool_payload is None:
        violations.append(
            "CFT-G13 (c): the product TOOL did not serve, so the door has no"
            f" path that answers at all. Got: {tool_text[:600]}"
        )
    else:
        applied = tool_payload.get("max_depth_applied")
        if applied != asked_depth:
            violations.append(
                f"CFT-G13 (c): the tool was asked at max_depth={asked_depth} and"
                f" walked at {applied!r}. The caller's depth did not reach the"
                " walk"
            )
        if applied == declared_default_depth and asked_depth != declared_default_depth:
            violations.append(
                f"CFT-G13 (c): the tool substituted the declared default"
                f" {declared_default_depth} for the caller's {asked_depth}"
            )
        served_anchor = (tool_payload.get("anchor") or {}).get("uri")
        if served_anchor != declared_anchor:
            violations.append(
                f"CFT-G13 (c): the tool served anchor {served_anchor!r} where"
                f" the caller named {declared_anchor!r}"
            )
    return violations


@dataclass(frozen=True)
class DoorReading:
    """What one drive of the shipped door produced, reduced to the three limbs."""

    resources: tuple[str, ...]
    templates: tuple[str, ...]
    resource_served: bool
    resource_text: str
    tool_refused: bool
    tool_text: str
    tool_payload: Mapping[str, Any] | None


@pytest.fixture(scope="module")
def door_reading(surfaces: dict[str, Any]) -> DoorReading:
    """The shipped door's enumeration, resource read and planted-depth tool ask."""
    listed = surfaces[ENUMERATE]
    assert not isinstance(listed, Refused), (
        f"the door could not be enumerated at all: {listed.reason[:1500]}"
    )
    resources, templates = listed

    read = surfaces[RESOURCE_READ]
    resource_served = not isinstance(read, Refused)
    resource_text = str(read if resource_served else read.reason)

    planted = surfaces[PLANTED_ASK]
    if isinstance(planted, Refused):
        return DoorReading(
            resources=tuple(resources),
            templates=tuple(templates),
            resource_served=resource_served,
            resource_text=resource_text,
            tool_refused=True,
            tool_text=planted.reason,
            tool_payload=None,
        )
    is_error, text = planted
    payload: Mapping[str, Any] | None = None
    if not is_error:
        outcome = json.loads(text)
        payload = dict(json.loads(outcome["product_json"])["payload"])
    return DoorReading(
        resources=tuple(resources),
        templates=tuple(templates),
        resource_served=resource_served,
        resource_text=resource_text,
        tool_refused=bool(is_error),
        tool_text=text,
        tool_payload=payload,
    )


def test_cft_g13_the_tool_serves_and_the_registered_resource_refuses(
    door_reading: DoorReading,
) -> None:
    """`CFT-G13` (criterion 37). All three limbs, driven at a real MCP client.

    Sabotaged by making the resolver return a payload — a resource read that
    yields a tree instead of refusing. A resolver docstring saying it refuses is
    not the resolver refusing and a refusal type merely imported is not a
    refusal raised, so this gate drives a real resource read and a real tool ask.
    """
    deployment = _load("deployment")
    violations = door_violations(
        resources=door_reading.resources,
        templates=door_reading.templates,
        resource_served=door_reading.resource_served,
        resource_text=door_reading.resource_text,
        tool_refused=door_reading.tool_refused,
        tool_text=door_reading.tool_text,
        tool_payload=door_reading.tool_payload,
        asked_depth=PLANTED_DEPTH,
        declared_default_depth=deployment.declared_depth_default(),
        declared_anchor=str(census()["anchor"]["uri"]),
    )
    assert not violations, "\n".join(violations)


def _compliant_door_arguments() -> dict[str, Any]:
    """A door reading in which all three limbs hold, for the controls to vary."""
    return {
        "resources": [],
        "templates": [PRODUCT_URI_TEMPLATE],
        "resource_served": False,
        "resource_text": (
            "this is a PARAMETERIZED class and this resource carries no"
            " parameters. Ask through the product TOOL"
        ),
        "tool_refused": False,
        "tool_text": "",
        "tool_payload": {
            "max_depth_applied": PLANTED_DEPTH,
            "anchor": {"uri": "x://anchor"},
        },
        "asked_depth": PLANTED_DEPTH,
        "declared_default_depth": 3,
        "declared_anchor": "x://anchor",
    }


def test_the_door_check_accepts_the_compliant_shape() -> None:
    """**Control on the control.** The varied baseline must itself pass.

    Without this, every control below could be reporting the baseline's own
    defect rather than the variation it introduced.
    """
    assert not door_violations(**_compliant_door_arguments())


def test_the_door_check_refuses_a_resolver_that_returned_a_payload() -> None:
    """**THE SABOTAGE `D-IMPL-225` NAMES.** A resource read that serves a tree."""
    arguments = _compliant_door_arguments()
    arguments["resource_served"] = True
    arguments["resource_text"] = json.dumps(
        {"anchor": {"uri": "x://anchor"}, "nodes": [{"type_chain": []}], "findings": []}
    )
    violations = door_violations(**arguments)
    assert violations, "a resource read that SERVED A TREE was accepted"
    assert any("RESOURCE served" in entry for entry in violations), violations
    assert any("must never produce" in entry for entry in violations), violations


def test_the_door_check_refuses_a_door_where_nothing_serves() -> None:
    """**Vacuity control.** A refusal limb alone passes on a broken door."""
    arguments = _compliant_door_arguments()
    arguments["tool_refused"] = True
    arguments["tool_payload"] = None
    arguments["tool_text"] = "everything is broken"
    violations = door_violations(**arguments)
    assert violations, "a door whose tool serves nothing was accepted"
    assert any("no path that answers" in entry for entry in violations), violations


def test_the_door_check_refuses_a_door_that_hid_the_resource() -> None:
    """**Sabotage control.** The template gone is limb (a) broken."""
    arguments = _compliant_door_arguments()
    arguments["templates"] = []
    violations = door_violations(**arguments)
    assert violations, "a door advertising no product resource was accepted"
    assert any(PRODUCT_URI_TEMPLATE in entry for entry in violations), violations


def test_the_door_check_refuses_a_concrete_product_resource() -> None:
    """**Sabotage control.** A standing instance appearing in `resources/list`."""
    arguments = _compliant_door_arguments()
    arguments["resources"] = ["ccf-product://t/reference.corporate-family/1.0.0"]
    violations = door_violations(**arguments)
    assert violations, "a concrete product resource entry was accepted"
    assert any("carries" in entry for entry in violations), violations


def test_the_door_check_refuses_a_tool_that_substituted_its_own_default() -> None:
    """**Sabotage control.** The caller's depth must reach the walk."""
    arguments = _compliant_door_arguments()
    arguments["tool_payload"] = {
        "max_depth_applied": 3,
        "anchor": {"uri": "x://anchor"},
    }
    violations = door_violations(**arguments)
    assert violations, "a door that ignored the caller's max_depth was accepted"
    assert any("did not reach the walk" in entry for entry in violations), violations
    assert any("substituted the declared default" in entry for entry in violations), (
        violations
    )


# ---------------------------------------------------------------------------
# CFT-G14 — ONE standalone assembler serves BOTH callers.
# ---------------------------------------------------------------------------


def assembly_entry_points(tree_root: pathlib.Path) -> list[str]:
    """Every construction of the standalone assembler under ``tree_root``.

    A function over a directory rather than a bare assert on the shipped one, so
    the controls can hand the **shipped** check a divergent subject. Read from
    the AST rather than by grepping the text: the modules' own docstrings name
    `FamilyTreeAssembler` in prose, and a text search would find the claim and
    read it as the violation.
    """
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


def standalone_violations(
    *,
    entry_points: Sequence[str],
    modules_held: Mapping[str, Any],
    assembler_module: Any,
    in_process_roster: Sequence[str],
    mcp_roster: Sequence[str],
) -> list[str]:
    """Every way this example fails `CFT-G14`.

    **The property is DEMONSTRATED by two callers sharing one module, not
    asserted**, so both callers are driven and their served rosters compared —
    an import graph alone would be a description. Three limbs: the two callers
    answered and answered the same family; both resolvers hold the SAME
    `assembler` module object; and `server/` holds exactly ONE construction of
    it.
    """
    violations: list[str] = []

    if not in_process_roster or not mcp_roster:
        violations.append(
            f"CFT-G14: one of the two callers served nothing — in-process"
            f" {len(in_process_roster)} member(s), MCP {len(mcp_roster)}."
            " Two callers sharing one assembler is only demonstrated by two"
            " callers that both ran"
        )
    elif tuple(in_process_roster) != tuple(mcp_roster):
        only_in_process = sorted(set(in_process_roster) - set(mcp_roster))
        only_mcp = sorted(set(mcp_roster) - set(in_process_roster))
        violations.append(
            "CFT-G14: the two callers served DIFFERENT families for one"
            f" question — in-process only {only_in_process}, MCP only"
            f" {only_mcp}. A second assembly path is exactly what that looks"
            " like from outside"
        )

    for caller, held in modules_held.items():
        if held is not assembler_module:
            violations.append(
                f"CFT-G14: {caller} holds an `assembler` module that is not this"
                f" example's — {getattr(held, '__file__', None)!r} rather than"
                f" {getattr(assembler_module, '__file__', None)!r}"
            )
    if len(modules_held) < 2:
        violations.append(
            f"CFT-G14: only {len(modules_held)} caller's resolver was checked,"
            " so 'both callers' holds over one caller"
        )

    if list(entry_points) != ["compose.py"]:
        violations.append(
            f"CFT-G14: `server/` holds {list(entry_points)} as its assembly"
            " entry point(s). `D-21` gives it exactly one, in `compose.py`, and"
            " a door that assembled for itself would make both callers green"
            " while proving nothing"
        )
    return violations


def test_cft_g14_one_standalone_assembler_serves_both_callers(
    observed: Observed, surfaces: dict[str, Any]
) -> None:
    """`CFT-G14` (criterion 38). One standalone assembler, two thin callers.

    Both paths are EXERCISED — the in-process `ProductClient` ask and the MCP
    tool ask, on the same question — and their served rosters compared, beside
    the module identity and the single entry point. `assembler.py` knows nothing
    about MCP, and the direction is the whole content of the standalone claim.

    Sabotaged by giving `server/serve.py` its own assembly path.
    """
    transport = _load("transport")
    compose = _load("compose")
    assembler = _load("assembler")

    answer = tool_answer(DEMONSTRATION_ASK, surfaces[DEMONSTRATION_ASK])
    mcp_roster = tuple(sorted(str(node["uri"]) for node in answer.payload["nodes"]))

    violations = standalone_violations(
        entry_points=assembly_entry_points(SERVER),
        modules_held={
            "`transport.py` (the in-process caller)": transport.assembler,
            "`server/compose.py` (the MCP caller)": compose.assembler,
        },
        assembler_module=assembler,
        in_process_roster=observed.roster,
        mcp_roster=mcp_roster,
    )
    assert not violations, "\n".join(violations)
    assert pathlib.Path(assembler.__file__).resolve() == EXAMPLE / "assembler.py", (
        assembler.__file__
    )


def test_the_standalone_check_refuses_a_second_assembly_path(
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
    found = assembly_entry_points(subject)
    assert sorted(found) == ["compose.py", "serve.py"], found

    marker = object()
    violations = standalone_violations(
        entry_points=found,
        modules_held={"a": marker, "b": marker},
        assembler_module=marker,
        in_process_roster=("x://one",),
        mcp_roster=("x://one",),
    )
    assert violations, "a second assembly path under `server/` was accepted"
    assert any("entry point" in entry for entry in violations), violations


def test_the_standalone_check_refuses_a_server_with_no_assembler_at_all(
    tmp_path: pathlib.Path,
) -> None:
    """**Vacuity control.** Zero entry points is not one entry point."""
    empty = tmp_path / "no-assembler"
    empty.mkdir()
    assert assembly_entry_points(empty) == []
    marker = object()
    violations = standalone_violations(
        entry_points=assembly_entry_points(empty),
        modules_held={"a": marker, "b": marker},
        assembler_module=marker,
        in_process_roster=("x://one",),
        mcp_roster=("x://one",),
    )
    assert violations, "a `server/` with no assembler at all was accepted"


def test_the_standalone_check_refuses_two_different_assembler_modules() -> None:
    """**Sabotage control.** Two modules of the same name, from two paths."""
    one, other = object(), object()
    violations = standalone_violations(
        entry_points=["compose.py"],
        modules_held={"caller one": one, "caller two": other},
        assembler_module=one,
        in_process_roster=("x://one",),
        mcp_roster=("x://one",),
    )
    assert violations, "two different assembler modules were accepted as one"
    assert any("not this example's" in entry for entry in violations), violations


def test_the_standalone_check_refuses_two_callers_serving_different_families() -> None:
    """**Sabotage control.** A second assembly path, seen from the payload."""
    marker = object()
    violations = standalone_violations(
        entry_points=["compose.py"],
        modules_held={"a": marker, "b": marker},
        assembler_module=marker,
        in_process_roster=("x://one", "x://two"),
        mcp_roster=("x://one",),
    )
    assert violations, "two callers serving different families were accepted"
    assert any("DIFFERENT families" in entry for entry in violations), violations


def test_the_standalone_check_refuses_a_caller_that_served_nothing() -> None:
    """**Vacuity control.** One caller that ran is not two callers."""
    marker = object()
    violations = standalone_violations(
        entry_points=["compose.py"],
        modules_held={"a": marker, "b": marker},
        assembler_module=marker,
        in_process_roster=("x://one",),
        mcp_roster=(),
    )
    assert violations, "a caller that served nothing was accepted"
    assert any("both ran" in entry for entry in violations), violations


def test_the_assembler_knows_nothing_about_the_door() -> None:
    """The direction is the whole content of the standalone claim.

    `server/compose.py` imports `assembler`; `assembler.py` imports neither the
    door nor the transport nor anything MCP-shaped. Read from the module's
    IMPORTS rather than by grepping its text — the file's own docstring states
    the claim in prose, and a text search would find the claim and read it as
    the violation.
    """
    imported = {name for _file, name in import_sites([EXAMPLE / "assembler.py"])}
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

