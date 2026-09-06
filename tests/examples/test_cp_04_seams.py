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

## The three closing checks, which are about the roster and not about a gate

They stay in the tree after this phase and they are scoped to cp-04's own
`artifacts/gates.yaml`. **None of them is the Phase 24.5 coverage checker** —
`D-IMPL-224` rules that one Phase 24.5's, and a general-purpose cross-product
gate checker built here would be the scope creep criterion 49 exists to prevent.

1. **Criterion 42, as a ROSTER.** Every declared gate carries a non-null
   `observed_red`, compared as SETS in both directions and never as a
   cardinality — a count of sixteen with a wrong member audits clean forever
   (`D-13`). `CFT-G17` is refused by name if it ever rejoins, in EITHER set.
   **The two sets come from two places, and that is the close panel's finding
   2.** The first draft built the observed set by filtering the declared one, so
   `observed - declared` was empty by construction and one of the two directions
   the docstring promised could not fire. The observations are now read from the
   DOCUMENT by `tests/examples/test_cp_04_seams.py::observations_in` — every
   mapping anywhere in it carrying an `observed_red` — so an observation
   recorded beside the roster, or under the withdrawn id, is expressible as
   input and the limb is reachable.
2. **The `key_link` nothing checked.** Plans 10, 11 and 12 each declare *"each
   gate's test reference resolving to an executing function"* and no acceptance
   criterion anywhere verified it, so this phase could have shipped sixteen
   dangling `module::function` references while criterion 43 still held —
   criterion 43 only requires the ids be declared as data. Every `test:` value
   is resolved against a REAL `pytest --collect-only` run: not `hasattr`, not an
   import, because a function pytest does not collect does not run.
3. **The recipe hole plan 03 measured and could not commit**, because no plan
   owned a recipe-shape test. The cycle step's `operator: null` at `layer: L2`
   is asserted BOUND TO THAT STEP BY NAME. The obvious
   ``any(operator is None and layer == "L2")`` is VACUOUS — steps 4 and 8
   satisfy it too, so it stays true when the cycle step is reclassified under
   `Traversal`, which is exactly the `D-IMPL-223` vocabulary drift the
   declaration exists to prevent. Both instruments are run on one scratch copy
   so the difference between them is RECORDED rather than described.

Each of the three is proven able to fail, against a scratch copy of the real
artifact rather than against an invented one.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

import httpx
import psycopg
import pytest
import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import parse_artifact_uri
from ccf.products.constraints import ConstraintRefusal
from ccf.products.refusal import NO_REPLAY_REFERENCE, REFUSAL_KINDS
from ccf.products.provenance import EffectiveRequest
from ccf.replay.record import NO_PRODUCT_ADDRESS, NO_REQUEST_RESOLUTION
from ccf_runtime.mcp.egress import PRODUCT_URI_TEMPLATE, product_uri
from tools.lints import matches_module
from tools.lints.algorithmic import LLM_MODULES

from .cp_04_seed import FLUREE_FIXTURE, ledger_for, schema_for, seed
from .test_cp_04_two_callers import (
    RECORDS,
    SUBJECT_UNAVAILABLE_KIND,
    Refused,
    _record_behind,
    _shell_kind,
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


def declared_subtree_roster() -> frozenset[str]:
    """The anchor subtree's TWENTY-TWO members BY NAME, from `expected.yaml`.

    Assembled from the two rosters that document already carries, and neither
    is a count: `unresolved_subtree_members` names the twenty with no attribute
    row, and `census.anchor_subtree_store_split.the_two_resolving` names the two
    that resolve. Their union is the subtree, in the LOCAL NAMES the census
    convention uses.

    **This replaces a cardinality that stood where a roster was required**
    (close panel finding 5). `len(served) == census.anchor_subtree
    .reachable_nodes` is satisfied by twenty-two entirely different nodes, and
    the precondition guarding five headline gates is the last place that should
    be true — this module's own `roster_violations` says so about gate ids.
    """
    declaration = _yaml(EXPECTED)
    unresolved = {str(name) for name in declaration["unresolved_subtree_members"]}
    resolving = {
        str(member["uri"])
        for member in declaration["census"]["anchor_subtree_store_split"][
            "the_two_resolving"
        ]
    }
    return frozenset(unresolved | resolving)


def declared_subtree_leis() -> frozenset[str]:
    """The LEIs the subtree's members carry, BY VALUE, from `expected.yaml`."""
    return frozenset(
        str(member["lei"])
        for member in census()["anchor_subtree_store_split"]["the_two_resolving"]
    )


def fixture_lei_roster() -> frozenset[str]:
    """Every LEI the COMMITTED fixture carries, under the DECLARED predicate.

    **Why the fixture and not `expected.yaml`.** The LEI precondition guards
    `CFT-G11`'s scale limb, which drives the shipped resolver over the whole
    LEI-bearing population — and `expected.yaml` declares that population's SIZE
    (`census.lei_coverage.nodes_carrying_lei`) and never its members. A
    cardinality is what the close panel's finding 5 objected to, so the roster
    is read where the roster exists: `tests/examples/fixtures/cp_04_family_fluree.json`,
    the committed document `tests/examples/cp_04_seed.py::seed` loads. The
    predicate is not authored here either — it comes from
    `artifacts/source-vocabulary.yaml::graph.node_predicates.lei`.

    **The chain, and both edges are asserted.** The DECLARATION is held against
    the FIXTURE (the declared size must be this roster's), and the FIXTURE is
    held against what the graph leg SERVES (by name, both directions). So the
    figure `expected.yaml` declares still governs, and no member can be
    substituted for another underneath it.
    """
    document = json.loads(FLUREE_FIXTURE.read_text(encoding="utf-8"))
    predicate = lei_predicate()
    values: set[str] = set()
    for node in document["insert"]:
        carried = node.get(predicate)
        if carried is None:
            continue
        if isinstance(carried, (list, tuple)):
            values.update(str(value) for value in carried)
        else:
            values.add(str(carried))
    return frozenset(values)


def fixture_lei_bearing_nodes(document: Mapping[str, Any] | None = None) -> list[list[str]]:
    """Every LEI-bearing node of a fixture, as its list of carried LEI values.

    **The population `resolve_anchor` depends on.**
    ``examples/cp-04-corporate-family-tree/deployment.py::resolve_anchor``
    collects EVERY binding a `SELECT ?s WHERE { ?s <lei> "…" }` yields and
    refuses more than one as `AnchorAmbiguityRefusal` (`CFT-G18`), so two
    nodes carrying one LEI would turn the default question into a refusal —
    the anchor, and therefore the whole served tree, would not be served at
    all. What keeps the committed fixture on the served path is a property
    `expected.yaml` states in a COMMENT: *"1:1 — no node carries two, no LEI
    is shared"*.

    :func:`fixture_lei_roster` holds `census.lei_coverage.nodes_carrying_lei`
    against the distinct VALUES, which catches a duplicate that leaves the node
    population fixed and NOT one that adds a node — 182 nodes over 181 distinct
    values satisfies it exactly. So the nodes are counted too, and both halves
    of the declared 1:1 are asserted.

    Takes a document so a control can hand the shipped reading a divergent
    subject rather than mutating the committed fixture, which a sibling module's
    append-only ledger would then carry forever.
    """
    if document is None:
        document = json.loads(FLUREE_FIXTURE.read_text(encoding="utf-8"))
    predicate = lei_predicate()
    carried: list[list[str]] = []
    for node in document["insert"]:
        value = node.get(predicate)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            carried.append([str(entry) for entry in value])
        else:
            carried.append([str(value)])
    return carried


def lei_identity_violations(
    carried: Sequence[Sequence[str]],
    *,
    declared_nodes: int,
    declared_values: int,
) -> list[str]:
    """Every way an estate fails the declared 1:1 between nodes and LEIs."""
    violations: list[str] = []
    if not carried:
        return [
            "no node carries an LEI at all, so the declared 1:1 holds over the"
            " empty set and proves nothing"
        ]
    if len(carried) != declared_nodes:
        violations.append(
            f"{len(carried)} node(s) carry an LEI where"
            f" expected.yaml::census.lei_coverage declares {declared_nodes}"
        )
    values = [value for node in carried for value in node]
    if len(set(values)) != declared_values:
        violations.append(
            f"{len(set(values))} distinct LEI value(s) where"
            f" expected.yaml::census.lei_coverage declares {declared_values}"
        )
    multiple = sorted(node[0] for node in carried if len(node) > 1)
    if multiple:
        violations.append(
            f"{len(multiple)} node(s) carry MORE THAN ONE LEI, beginning"
            f" {multiple[:3]}. expected.yaml declares the mapping 1:1"
        )
    seen: dict[str, int] = {}
    for node in carried:
        for value in node:
            seen[value] = seen.get(value, 0) + 1
    shared = sorted(value for value, count in seen.items() if count > 1)
    if shared:
        violations.append(
            f"LEI(s) {shared[:3]} are carried by more than one node"
            f" ({len(shared)} in all). `resolve_anchor` refuses a shared LEI as"
            " `AnchorAmbiguityRefusal` (`CFT-G18`), so a shared LEI in the"
            " COMMITTED fixture would turn the default question into a refusal"
        )
    return violations


def declared_member_depths() -> Mapping[str, int]:
    """Which subtree member enters the walk at which depth, DECLARED.

    `artifacts/expected.yaml::census.anchor_subtree.depth_to`, by local name.
    `CFT-G13`'s roster limbs (iii) and (iv) hold the door's served roster
    against it, so the depth claim is measured against a document and not only
    against a second run of the same product.
    """
    return {
        str(name): int(depth)
        for name, depth in dict(census()["anchor_subtree"]["depth_to"]).items()
    }


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
    #: Every key value the statements BOUND, taken at the same connection.
    addressed_leis: tuple[str, ...]
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
            addressed_leis=tuple(resolution.addressed),
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
                },
            )
        # The record behind each refusal, read out of the door's own store
        # while the scratch root exists (`D-IMPL-260` P-C: the resource's
        # refusal is a recorded determination, and its stated reason lives on
        # the record rather than on the wire below `full`).
        results[RECORDS] = {
            ask: _record_behind(root, result) for ask, result in results.items()
        }
        return results


# ---------------------------------------------------------------------------
# PRECONDITIONS — what a green gate below is allowed to mean.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_the_seed_carries_what_these_five_gates_need(
    observed: Observed, estate: tuple[str, str]
) -> None:
    """Without this, a green gate below could be a true statement about nothing.

    Six ways that could happen: an empty node set, a subtree the seed does not
    reproduce, no member resolving in the attribute store at all (which would
    make `CFT-G10`'s provenance limb vacuous), a single-member LEI roster (which
    would make `CFT-G11`'s batching claim untestable), a declared source roster
    that is not two legs, and an empty attribute column roster.

    **EVERY POPULATION HERE IS ASSERTED AS A ROSTER, and that is the close
    panel's finding 5.** This test used to read

        assert len(observed.roster) == …["anchor_subtree"]["reachable_nodes"]
        assert len(roster) == …["lei_coverage"]["nodes_carrying_lei"]

    — two cardinalities, in the precondition that says what a green gate below
    is allowed to mean, in the same module whose `roster_violations` docstring
    says a count with a wrong member audits clean forever (`D-13`). A member of
    the subtree swapped for another valid node of this estate satisfies both
    lines exactly.

    The expectations are read from documents and never authored here: the
    subtree roster from `artifacts/expected.yaml`'s own two rosters, the LEI
    roster from the committed fixture under the DECLARED predicate, with the
    declared size held against that fixture so the figure `expected.yaml`
    carries still governs — see :func:`fixture_lei_roster`.
    """
    ledger, schema = estate
    declared = census()
    legs = declared_legs()
    vocabulary = attribute_vocabulary()

    assert observed.nodes, (
        "the demonstration ask served no nodes at all, so every per-node claim"
        " below would hold over the empty set"
    )

    declared_roster = declared_subtree_roster()
    served_roster = frozenset(local_name(uri) for uri in observed.roster)
    assert len(declared_roster) == int(
        declared["anchor_subtree"]["reachable_nodes"]
    ), (
        "expected.yaml disagrees with ITSELF: its subtree rosters name"
        f" {len(declared_roster)} members where census.anchor_subtree declares"
        f" {declared['anchor_subtree']['reachable_nodes']} reachable. One half"
        " of the document was edited without the other, so neither can be held"
        " against a run"
    )
    assert not declared_roster - served_roster, (
        "the seed did not serve"
        f" {sorted(declared_roster - served_roster)}, which expected.yaml"
        " declares in the anchor subtree. NOTE THE SIZES BESIDE THE ROSTERS —"
        f" served {len(served_roster)}, declared {len(declared_roster)}: a"
        " count-based precondition is satisfied whenever these agree, however"
        " the members differ"
    )
    assert not served_roster - declared_roster, (
        f"the seed served {sorted(served_roster - declared_roster)}, which"
        " expected.yaml does not declare in the anchor subtree. NOTE THE SIZES"
        f" — served {len(served_roster)}, declared {len(declared_roster)}"
    )

    split = declared["anchor_subtree_store_split"]
    assert split["the_two_resolving"], (
        "expected.yaml declares no subtree member resolving in the attribute"
        " store, so CFT-G10's provenance limb would have nothing to compare"
    )
    served_subtree_leis = frozenset(
        str(node["lei"]) for node in observed.nodes if node.get("lei")
    )
    assert served_subtree_leis == declared_subtree_leis(), (
        f"the subtree served the LEIs {sorted(served_subtree_leis)} where"
        " expected.yaml::census.anchor_subtree_store_split declares"
        f" {sorted(declared_subtree_leis())}. This roster is declared WHOLE, so"
        " it is compared whole"
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

    roster = frozenset(fluree_lei_roster(*_url_and_ledger(estate)))
    fixture = fixture_lei_roster()
    assert len(fixture) == int(declared["lei_coverage"]["nodes_carrying_lei"]), (
        f"the committed fixture carries {len(fixture)} LEIs under the declared"
        " predicate where expected.yaml::census.lei_coverage declares"
        f" {declared['lei_coverage']['nodes_carrying_lei']}. The DECLARATION and"
        " the ESTATE disagree, so neither can be held against the graph leg"
    )
    assert not fixture - roster, (
        f"the graph leg does not carry {sorted(fixture - roster)[:5]} —"
        f" {len(fixture - roster)} LEI(s) the committed fixture holds. The seed"
        " did not reproduce the estate"
    )
    assert not roster - fixture, (
        f"the graph leg carries {sorted(roster - fixture)[:5]} —"
        f" {len(roster - fixture)} LEI(s) the committed fixture does not hold."
        " A sibling module's ledger has leaked into this one, or the seed added"
        " something the fixture does not declare"
    )
    named = {str(declared["anchor"]["lei"])} | set(declared_subtree_leis())
    assert not named - roster, (
        f"the graph leg does not carry {sorted(named - roster)}, which"
        " expected.yaml names BY VALUE. The roster comparison above would be"
        " satisfied by a fixture and a store that agreed on the wrong estate"
    )
    assert len(roster) > 1, (
        "the graph leg carries at most one LEI, so ONE statement for the whole"
        " roster would not be a batching claim at all"
    )
    identity = lei_identity_violations(
        fixture_lei_bearing_nodes(),
        declared_nodes=int(declared["lei_coverage"]["nodes_carrying_lei"]),
        declared_values=int(declared["lei_coverage"]["distinct_lei_values"]),
    )
    assert not identity, "\n".join(identity)
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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
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
    *,
    statements: Sequence[str],
    requested: Sequence[str],
    addressed: Sequence[str],
    resolved: Sequence[str],
    subject: str,
) -> list[str]:
    """Every way one attribute resolution fails `CFT-G11`.

    **THE COUNT IS NOT THE CLAIM, AND THAT WAS THE CLOSE PANEL'S FINDING 4.**
    The first shape of this check had exactly two limbs — ``len(requested) < 2``
    and ``len(statements) != 1`` — and PRINTED the roster it resolved in the
    failure message without ever asserting it. One unparameterized ``SELECT``
    over the whole attribute table therefore satisfied the gate: one statement,
    every row, nothing addressed. Dave: *"assert set difference both ways; print
    is not an assertion."*

    So the one statement must be shown to have resolved the REQUESTED ROSTER,
    in both directions and by name (`D-13`):

    * **nothing requested went unaddressed** — every requested key appears among
      the values the statements BOUND, taken at the connection by
      ``examples/cp-04-corporate-family-tree/deployment.py::_counting_cursor``.
      An unparameterized statement binds nothing and fails here whatever its
      text says about itself;
    * **nothing was addressed that was not requested** — a bound key nobody
      asked for is a resolution answering a wider question than the one put;
    * **no ROW came back for a key nobody requested**. This limb reads the
      EFFECT rather than the binding, and it is what catches a whole-table read
      that binds nothing at all: the parameters are empty, and the rows are the
      table.

    A resolved roster SMALLER than the requested one is NOT a violation and must
    not become one. Measured on this estate, 181 LEIs resolve 142 rows in
    ``legal_entity``; a member with no row is a null resolution and never a
    dropped member (`D-16`, `CFT-G09`).
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
            f" First statements: {[text[:120] for text in statements[:3]]}"
        )

    wanted = set(requested)
    bound = set(addressed)
    unaddressed = sorted(wanted - bound)
    if unaddressed:
        violations.append(
            f"CFT-G11: {subject} asked for {len(wanted)} key(s) and the"
            f" statement(s) BOUND none of {unaddressed[:5]}"
            f"{' …' if len(unaddressed) > 5 else ''} —"
            f" {len(unaddressed)} requested key(s) went unaddressed. One"
            " statement that does not address the requested roster is not a"
            " batched resolution of it; an unparameterized read of the whole"
            " table is one statement and addresses nothing"
        )
    unrequested = sorted(bound - wanted)
    if unrequested:
        violations.append(
            f"CFT-G11: {subject} BOUND {unrequested[:5]}"
            f"{' …' if len(unrequested) > 5 else ''} —"
            f" {len(unrequested)} key(s) nobody asked for. The resolution"
            " answered a wider question than the one put to it"
        )
    stray = sorted(set(resolved) - wanted)
    if stray:
        violations.append(
            f"CFT-G11: {subject} was RETURNED rows for {stray[:5]}"
            f"{' …' if len(stray) > 5 else ''} —"
            f" {len(stray)} key(s) it never requested. Reading the whole"
            " attribute table in one statement is one statement and is not this"
            " gate's claim"
        )
    return violations


@dataclass(frozen=True)
class WholeEstateResolution:
    """The shipped resolver driven over EVERY LEI the graph leg carries."""

    requested: tuple[str, ...]
    statements: tuple[str, ...]
    addressed: tuple[str, ...]
    resolved: tuple[str, ...]


@pytest.fixture(scope="module")
def whole_estate_resolution(estate: tuple[str, str]) -> WholeEstateResolution:
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

    Returns the requested roster, the statements it took, the keys those
    statements BOUND and the keys they returned rows for.
    """
    deployment = _load("deployment")
    roster = fluree_lei_roster(*_url_and_ledger(estate))
    resolution = deployment.resolve_attributes(roster)
    return WholeEstateResolution(
        requested=tuple(resolution.requested),
        statements=tuple(resolution.statements),
        addressed=tuple(resolution.addressed),
        resolved=tuple(sorted(resolution.rows)),
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_cft_g11_attributes_resolve_in_one_batched_query(
    observed: Observed,
    whole_estate_resolution: WholeEstateResolution,
) -> None:
    """`CFT-G11` (criterion 35). ONE batched PostgreSQL query, at two scales.

    The statements are counted at the CONNECTION by
    ``deployment.py::AttributeResolution``'s cursor factory, so a query fired
    anywhere on that connection is counted even if it does not go through
    ``resolve_attributes``' own call site.

    Sabotaged by firing one query per node.
    """
    whole = whole_estate_resolution
    violations = batching_violations(
        statements=observed.statements,
        requested=observed.requested_leis,
        addressed=observed.addressed_leis,
        resolved=sorted(observed.rows),
        subject=f"the demonstration subtree ({len(observed.roster)} members)",
    )
    violations += batching_violations(
        statements=whole.statements,
        requested=whole.requested,
        addressed=whole.addressed,
        resolved=whole.resolved,
        subject="the whole LEI-bearing population",
    )
    assert not violations, "\n".join(violations)


def _compliant_batch() -> dict[str, Any]:
    """One batched resolution in which every limb holds, for controls to vary.

    Three requested keys, one statement binding all three, and rows back for
    two of them — because a resolved roster SMALLER than the requested one is
    the estate's normal case (`D-16`) and must stay compliant.
    """
    return {
        "statements": ["SELECT lei, ... FROM legal_entity WHERE lei = ANY(%s)"],
        "requested": ("a", "b", "c"),
        "addressed": ("a", "b", "c"),
        "resolved": ("a", "b"),
        "subject": "a batched resolution",
    }


def test_the_batching_check_accepts_the_compliant_shape() -> None:
    """**Control on the control.** The varied baseline must itself pass.

    Including the case that must NOT be a violation: two of three keys resolved.
    A limb requiring the rows to equal the request would forbid the null
    resolution `CFT-G09` exists to protect.
    """
    assert not batching_violations(**_compliant_batch())


def test_the_batching_check_refuses_a_per_node_fan_out() -> None:
    """**Sabotage control.** One query per node is what this gate forbids."""
    arguments = _compliant_batch()
    arguments["statements"] = [
        f"SELECT ... WHERE lei = '{n}'" for n in ("a", "b", "c")
    ]
    violations = batching_violations(**arguments)
    assert violations, "a three-statement fan-out was accepted as one batch"
    assert any("not 1" in entry for entry in violations), violations


def test_the_batching_check_refuses_one_statement_addressing_nothing() -> None:
    """**THE CLOSE PANEL'S FINDING 4, as a control.**

    An unparameterized `SELECT` over the whole attribute table: ONE statement,
    which the count limb accepts, binding nothing and returning the table. Both
    the binding limb and the effect limb fire, and the count limb stays silent —
    asserted, because that silence is the whole reason the roster limbs exist.
    """
    arguments = _compliant_batch()
    arguments["statements"] = ["SELECT lei, ... FROM legal_entity"]
    arguments["addressed"] = ()
    arguments["resolved"] = ("a", "b", "somebody-else", "another-one")
    violations = batching_violations(**arguments)
    assert violations, "one statement addressing nothing was accepted as a batch"
    assert any("went unaddressed" in entry for entry in violations), violations
    assert any("never requested" in entry for entry in violations), violations
    assert not any("not 1" in entry for entry in violations), (
        "the count limb fired, so this control is no longer measuring the shape"
        f" the finding names: {violations}"
    )


def test_the_batching_check_refuses_a_partially_addressed_roster() -> None:
    """**Sabotage control.** One statement addressing SOME of the request.

    A batch over the first key only is still one statement and still returns
    plausible rows. Only the both-ways roster comparison sees it.
    """
    arguments = _compliant_batch()
    arguments["addressed"] = ("a",)
    violations = batching_violations(**arguments)
    assert violations, "a statement addressing part of the roster was accepted"
    assert any("went unaddressed" in entry for entry in violations), violations
    assert any("'b'" in entry and "'c'" in entry for entry in violations), violations


def test_the_batching_check_refuses_keys_nobody_asked_for() -> None:
    """**Sabotage control.** The other direction — a wider question than the one put."""
    arguments = _compliant_batch()
    arguments["addressed"] = ("a", "b", "c", "d")
    violations = batching_violations(**arguments)
    assert violations, "a statement binding an unrequested key was accepted"
    assert any("nobody asked for" in entry for entry in violations), violations


def test_the_batching_check_refuses_a_single_key_roster() -> None:
    """**Vacuity control.** One statement for one key is not batching."""
    arguments = _compliant_batch()
    arguments["requested"] = ("only",)
    arguments["addressed"] = ("only",)
    arguments["resolved"] = ("only",)
    violations = batching_violations(**arguments)
    assert violations, "a single-key resolution was accepted as a batched one"
    assert any("fewer than two keys" in entry for entry in violations), violations


def test_the_batching_check_refuses_a_leg_that_issued_nothing() -> None:
    """**Vacuity control.** Zero statements is not one statement."""
    arguments = _compliant_batch()
    arguments["statements"] = []
    arguments["addressed"] = ()
    arguments["resolved"] = ()
    violations = batching_violations(**arguments)
    assert violations, "an attribute leg that issued no statement was accepted"
    assert any("not 1" in entry for entry in violations), violations
    assert any("went unaddressed" in entry for entry in violations), violations


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
    # Reported PER DECLARED CLIENT with a count and three examples, rather than
    # one violation per reached module: a single `import anthropic` pulls over a
    # hundred of its own submodules into the closure, and a hundred repetitions
    # of one finding is not a hundred findings.
    for client in sorted(LLM_MODULES):
        hits = sorted(
            name
            for name in set(reached)
            if matches_module(name, frozenset({client}))
        )
        if hits:
            violations.append(
                f"CFT-G12: the declared client {client!r} is REACHABLE from the"
                f" §D steps {list(roots)} — {len(hits)} module(s) in the"
                f" closure, e.g. {hits[:3]}. A model reachable from any step"
                " makes this Assembly Mode 2, and the declared 1 becomes false"
            )
    llm_imported = sorted(
        {(filename, name) for filename, name in sites if matches_module(name, LLM_MODULES)}
    )
    if llm_imported:
        violations.append(
            f"CFT-G12: {llm_imported} — a lazily-imported client is still a"
            " model call in the algorithmic path, which the closure limb cannot"
            " see until the function runs"
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
    assert any("'anthropic'" in entry for entry in violations), violations


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
    resource_recorded_detail: str | None,
    tool_refused: bool,
    tool_text: str,
    tool_payload: Mapping[str, Any] | None,
    default_payload: Mapping[str, Any] | None,
    asked_depth: int,
    declared_default_depth: int,
    declared_anchor: str,
    declared_depths: Mapping[str, int],
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
            " claiming a tool-only shape `build_egress_server` CAN express since"
            " `24.5-L-09` (`expose_product_resource=False`) and this door does"
            " not choose (`D-34` closed; the resource stays by ruling)"
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
    # `D-IMPL-260` P-C: the resolver's `ProductNotServable` is a governed
    # determination — recorded, and answered as the common shell. The stated
    # reason is read off the RECORD; the wire is held NOT to carry it at this
    # deployment's `minimal` level, which is the shell's whole point.
    if (
        resource_recorded_detail is None
        or "PARAMETERIZED class" not in resource_recorded_detail
    ):
        violations.append(
            "CFT-G13 (b): the resource read did not refuse for THIS"
            " deployment's stated reason. A refusal for an unrelated reason is"
            " not the refusal this gate asserts. Recorded:"
            f" {str(resource_recorded_detail)[:600]}"
        )
    if "PARAMETERIZED class" in resource_text:
        violations.append(
            "CFT-G13 (b): the deployment's stated reason crossed the wire at"
            " `minimal` — the internal determination leaked into the shell"
            f" (D-IMPL-260 P-C): {resource_text[:600]}"
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
        violations += _depth_roster_violations(
            planted_payload=tool_payload,
            default_payload=default_payload,
            asked_depth=asked_depth,
            declared_default_depth=declared_default_depth,
            declared_depths=declared_depths,
        )
    return violations


def _depth_roster_violations(
    *,
    planted_payload: Mapping[str, Any],
    default_payload: Mapping[str, Any] | None,
    asked_depth: int,
    declared_default_depth: int,
    declared_depths: Mapping[str, int],
) -> list[str]:
    """Limb (c)'s ROSTER half — what the door SERVED at each depth.

    **THIS IS THE CLOSE PANEL'S FINDING 3, and it is the limb the phase's
    headline rests on.** Limb (c) read `max_depth_applied` off the served
    payload and compared the anchor URI, and neither of those is the walk.
    `examples/cp-04-corporate-family-tree/projection.py` writes
    `max_depth_applied` from `scenario.max_depth` — the REQUEST — while the walk
    takes its bound from the operator parameter set
    `examples/cp-04-corporate-family-tree/deployment.py::traversal_parameters`
    binds. So a door that echoes the requested depth into the payload while
    walking the declared default passes the echo limb whole. That is not a
    hypothetical: it is `CFT-G05`'s own recorded sabotage, and it is the defect
    class this ladder has now met four times — a check reading a RECORD OF THE
    INTENT rather than the EFFECT.

    Dave: *"the door must compare **rosters across depths**, not echo
    `max_depth_applied` — that is `CFT-G13`."*

    Four limbs, all over ROSTERS and never over sizes (`D-13`):

    (i) the shallower ask's roster is a SUBSET of the deeper ask's — a member
    served at depth 1 and not at the default is a walk that is not nested;
    (ii) the deeper ask reached members the shallower one did not, so the two
    depths are two answers rather than one answer served twice;
    (iii) every member `expected.yaml::census.anchor_subtree.depth_to` declares
    at a depth GREATER than the ask is ABSENT, named;
    (iv) every member it declares at a depth within the ask is PRESENT, named.

    (iii) and (iv) are what make this a comparison against a DECLARATION rather
    than only between two runs. `depth_to` lives in a file no sabotage of the
    door touches.
    """
    violations: list[str] = []
    if default_payload is None:
        violations.append(
            "CFT-G13 (c): the door was not asked at the declared default depth,"
            " so there is no second roster to compare the caller's depth"
            " against and the depth claim holds over one run"
        )
        return violations

    planted = _served_local_names(planted_payload)
    default = _served_local_names(default_payload)
    if not planted or not default:
        violations.append(
            f"CFT-G13 (c): one of the two asks served no member — max_depth="
            f"{asked_depth} served {sorted(planted)}, the declared default"
            f" served {sorted(default)}. A roster comparison over an empty side"
            " is a comparison that cannot fail"
        )
        return violations

    default_applied = default_payload.get("max_depth_applied")
    if default_applied != declared_default_depth:
        violations.append(
            f"CFT-G13 (c): the second ask walked at {default_applied!r} rather"
            f" than the declared default {declared_default_depth}, so the two"
            " rosters below are not two depths"
        )

    unnested = sorted(planted - default)
    if unnested:
        violations.append(
            f"CFT-G13 (c): max_depth={asked_depth} served {unnested}, which the"
            f" declared default {declared_default_depth} did NOT serve. A"
            " shallower walk cannot reach what a deeper one misses"
        )
    reached_only_deeper = sorted(default - planted)
    if not reached_only_deeper:
        violations.append(
            f"CFT-G13 (c): max_depth={asked_depth} and the declared default"
            f" {declared_default_depth} served the IDENTICAL roster"
            f" {sorted(planted)}. The caller's depth reached the payload's label"
            " and not the walk — which is exactly what a door echoing"
            " `max_depth_applied` looks like from the echo limb, and why that"
            " limb cannot carry this claim"
        )

    beyond = sorted(
        name for name, depth in declared_depths.items() if int(depth) > asked_depth
    )
    intruders = sorted(name for name in beyond if name in planted)
    if intruders:
        violations.append(
            f"CFT-G13 (c): max_depth={asked_depth} served {intruders}, which"
            " expected.yaml::census.anchor_subtree.depth_to declares at"
            f" {[declared_depths[name] for name in intruders]} — deeper than the"
            " caller asked for"
        )
    within = sorted(
        name for name, depth in declared_depths.items() if int(depth) <= asked_depth
    )
    absent = sorted(name for name in within if name not in planted)
    if absent:
        violations.append(
            f"CFT-G13 (c): max_depth={asked_depth} did NOT serve {absent}, which"
            " expected.yaml::census.anchor_subtree.depth_to declares at"
            f" {[declared_depths[name] for name in absent]} — within the depth"
            " the caller asked for"
        )
    if not declared_depths:
        violations.append(
            "CFT-G13 (c): the declaration named no member at any depth, so"
            " limbs (iii) and (iv) hold over the empty set"
        )
    return violations


def local_name(iri: str) -> str:
    """The last segment of an IRI — the census vocabulary.

    `artifacts/expected.yaml` names members by LOCAL NAME and says why: *"the
    full IRIs are derived from the store's own answers; a prefix written here
    would be a domain value in an artifact AND a second place for the estate's
    namespace to be wrong."* So the comparison happens in local-name space, the
    same convention `tests/examples/test_cp_04_payload.py::local_name` uses.
    """
    return str(iri).rsplit("/", 1)[-1]


def _served_local_names(payload: Mapping[str, Any]) -> set[str]:
    """The member roster of one served payload, by local name."""
    return {local_name(str(node["uri"])) for node in payload.get("nodes") or ()}


@dataclass(frozen=True)
class DoorReading:
    """What one drive of the shipped door produced, reduced to the three limbs."""

    resources: tuple[str, ...]
    templates: tuple[str, ...]
    resource_served: bool
    resource_text: str
    #: The `detail` of the internal determination the resource refusal's
    #: replay record holds — where the deployment's stated reason lives.
    resource_recorded_detail: str | None
    tool_refused: bool
    tool_text: str
    tool_payload: Mapping[str, Any] | None
    #: What the SAME door served the SAME way at the DECLARED DEFAULT depth.
    #: Limb (c)'s roster comparison is between these two, and one ask cannot
    #: carry a claim about depth (close panel finding 3).
    default_payload: Mapping[str, Any] | None


def _tool_outcome(result: Any) -> tuple[bool, str, Mapping[str, Any] | None]:
    """One door tool ask, reduced to ``(refused, text, payload)``.

    A refusal is a value rather than a raise — the module's posture for the
    whole door — because a helper that raised would turn a door serving nothing
    into an ERROR rather than into the violation limb (c) names.
    """
    if isinstance(result, Refused):
        return True, result.reason, None
    is_error, text = result
    if is_error:
        return True, text, None
    outcome = json.loads(text)
    return False, text, dict(json.loads(outcome["product_json"])["payload"])


@pytest.fixture(scope="module")
def door_reading(surfaces: dict[str, Any]) -> DoorReading:
    """The shipped door's enumeration, resource read and BOTH tool asks."""
    listed = surfaces[ENUMERATE]
    assert not isinstance(listed, Refused), (
        f"the door could not be enumerated at all: {listed.reason[:1500]}"
    )
    resources, templates = listed

    read = surfaces[RESOURCE_READ]
    # The read SUCCEEDS with the common shell (`D-IMPL-260` P-C): "served"
    # means the body is not a governed refusal at all.
    resource_text = read.reason if isinstance(read, Refused) else str(read)
    resource_served = _shell_kind(resource_text) != SUBJECT_UNAVAILABLE_KIND
    record = surfaces[RECORDS].get(RESOURCE_READ) or {}
    internal = record.get("content_generation_path", {}).get("assembly_refusal")
    internal = json.loads(internal) if isinstance(internal, str) else internal
    resource_recorded_detail = (internal or {}).get("detail") if internal else None

    refused, text, payload = _tool_outcome(surfaces[PLANTED_ASK])
    _default_refused, _default_text, default_payload = _tool_outcome(
        surfaces[DEMONSTRATION_ASK]
    )
    return DoorReading(
        resources=tuple(resources),
        templates=tuple(templates),
        resource_served=resource_served,
        resource_text=resource_text,
        resource_recorded_detail=resource_recorded_detail,
        tool_refused=refused,
        tool_text=text,
        tool_payload=payload,
        default_payload=default_payload,
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
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
        resource_recorded_detail=door_reading.resource_recorded_detail,
        tool_refused=door_reading.tool_refused,
        tool_text=door_reading.tool_text,
        tool_payload=door_reading.tool_payload,
        default_payload=door_reading.default_payload,
        asked_depth=PLANTED_DEPTH,
        declared_default_depth=deployment.declared_depth_default(),
        declared_anchor=str(census()["anchor"]["uri"]),
        declared_depths=declared_member_depths(),
    )
    assert not violations, "\n".join(violations)


def _compliant_door_arguments() -> dict[str, Any]:
    """A door reading in which all three limbs hold, for the controls to vary."""
    return {
        "resources": [],
        "templates": [PRODUCT_URI_TEMPLATE],
        "resource_served": False,
        "resource_text": json.dumps(
            {"kind": "subject-unavailable", "disclosure": "minimal", "fields": {}}
        ),
        "resource_recorded_detail": (
            "this is a PARAMETERIZED class and this resource carries no"
            " parameters. Ask through the product TOOL"
        ),
        "tool_refused": False,
        "tool_text": "",
        "tool_payload": {
            "max_depth_applied": PLANTED_DEPTH,
            "anchor": {"uri": "x://anchor"},
            "nodes": [{"uri": "x://anchor"}, {"uri": "x://near"}],
        },
        "default_payload": {
            "max_depth_applied": 3,
            "anchor": {"uri": "x://anchor"},
            "nodes": [
                {"uri": "x://anchor"},
                {"uri": "x://near"},
                {"uri": "x://far"},
            ],
        },
        "asked_depth": PLANTED_DEPTH,
        "declared_default_depth": 3,
        "declared_anchor": "x://anchor",
        "declared_depths": {"near": PLANTED_DEPTH, "far": 3},
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
    """**Sabotage control.** The caller's depth must reach the walk.

    The substitution is visible in BOTH halves of limb (c) here — the echo says
    3 and the served roster is the deeper one — which is the case the echo limb
    was written for and the only case it catches.
    """
    arguments = _compliant_door_arguments()
    arguments["tool_payload"] = dict(arguments["default_payload"])
    violations = door_violations(**arguments)
    assert violations, "a door that ignored the caller's max_depth was accepted"
    assert any("did not reach the walk" in entry for entry in violations), violations
    assert any("substituted the declared default" in entry for entry in violations), (
        violations
    )


def test_the_door_check_refuses_a_walk_at_the_default_while_the_echo_says_the_ask() -> None:
    """**THE CLOSE PANEL'S FINDING 3, as a control — and the echo limb is
    proven insufficient here rather than argued.**

    The payload echoes the CALLER's depth and serves the DEEPER walk's roster.
    That is not a hypothetical shape: `max_depth_applied` is written from the
    REQUEST by
    `examples/cp-04-corporate-family-tree/projection.py::FamilyTreeProjection.invoke`
    while the walk's bound comes from the operator parameter set, so a door that
    stopped binding the caller's depth onto the walk produces exactly this.

    Both halves are asserted: the roster limbs FIRE, and NEITHER echo limb says
    anything. A gate carrying only the echo would have been green here.
    """
    arguments = _compliant_door_arguments()
    arguments["tool_payload"] = {
        **arguments["default_payload"],
        "max_depth_applied": PLANTED_DEPTH,
    }
    violations = door_violations(**arguments)
    assert violations, "a door walking the default while echoing the ask was accepted"
    assert any("served ['far']" in entry for entry in violations), violations
    assert any("deeper than the caller asked for" in entry for entry in violations), (
        violations
    )
    assert not any("did not reach the walk" in entry for entry in violations), (
        "the echo limb fired, so this control is no longer measuring what it"
        f" exists to measure: {violations}"
    )
    assert not any(
        "substituted the declared default" in entry for entry in violations
    ), violations


def test_the_door_check_refuses_two_depths_that_served_one_roster() -> None:
    """**Sabotage control.** Two depths, one answer, is one answer served twice.

    The declared roster limbs cannot see this on their own when the declaration
    names no member beyond the ask — so the between-runs limb is asserted with
    `declared_depths` emptied of the deeper member, and it still fires.
    """
    arguments = _compliant_door_arguments()
    arguments["tool_payload"] = {
        **arguments["default_payload"],
        "max_depth_applied": PLANTED_DEPTH,
    }
    arguments["declared_depths"] = {"near": PLANTED_DEPTH}
    violations = door_violations(**arguments)
    assert violations, "two depths serving one roster were accepted"
    assert any("IDENTICAL roster" in entry for entry in violations), violations


def test_the_door_check_refuses_a_shallow_ask_that_reached_further() -> None:
    """**Sabotage control.** A walk that is not nested is not a depth bound."""
    arguments = _compliant_door_arguments()
    arguments["tool_payload"] = {
        **arguments["tool_payload"],
        "nodes": [{"uri": "x://anchor"}, {"uri": "x://elsewhere"}],
    }
    violations = door_violations(**arguments)
    assert violations, "a shallower ask serving an unreached member was accepted"
    assert any("cannot reach what a deeper one misses" in entry for entry in violations), (
        violations
    )


def test_the_door_check_refuses_a_missing_member_the_declaration_puts_within_reach() -> None:
    """**Sabotage control.** Limb (iv) — the roster is short a declared member."""
    arguments = _compliant_door_arguments()
    arguments["tool_payload"] = {
        **arguments["tool_payload"],
        "nodes": [{"uri": "x://anchor"}],
    }
    violations = door_violations(**arguments)
    assert violations, "an ask missing a member declared within its depth was accepted"
    assert any("within the depth the caller asked for" in entry for entry in violations), (
        violations
    )


def test_the_door_check_refuses_a_single_depth_comparison() -> None:
    """**Vacuity control.** One ask cannot carry a claim about two depths."""
    arguments = _compliant_door_arguments()
    arguments["default_payload"] = None
    violations = door_violations(**arguments)
    assert violations, "a depth claim over one run was accepted"
    assert any("holds over one run" in entry for entry in violations), violations


def test_the_door_check_refuses_an_empty_declaration_of_member_depths() -> None:
    """**Vacuity control.** Limbs (iii) and (iv) need a declaration to read."""
    arguments = _compliant_door_arguments()
    arguments["declared_depths"] = {}
    violations = door_violations(**arguments)
    assert violations, "an empty depth declaration was accepted"
    assert any("hold over the empty set" in entry for entry in violations), violations


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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
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


# ---------------------------------------------------------------------------
# THE SIXTEEN-GATE ROSTER — criterion 42's machinery, and it stays in the tree.
# ---------------------------------------------------------------------------


def declared_gates() -> tuple[Mapping[str, Any], ...]:
    """Every gate `artifacts/gates.yaml` declares."""
    return tuple(dict(gate) for gate in _yaml(GATES)["gates"])


def gates_document() -> Any:
    """The WHOLE `artifacts/gates.yaml`, not just `declaration.gates`.

    :func:`observations_in` reads this rather than the parsed roster, and the
    difference is the whole content of the close panel's finding 2 — see there.
    """
    return yaml.safe_load(GATES.read_text(encoding="utf-8"))


#: What an observation recorded under no id at all is named as. It cannot be
#: attributed to a gate, so it is neither declared nor observable — it is its
#: own defect, and naming it keeps `observations_in` total.
UNATTRIBUTED_OBSERVATION = "<an observation carrying no id>"


def observations_in(document: Any) -> tuple[str, ...]:
    """Every id ANYWHERE in ``document`` that carries an `observed_red` record.

    **THIS IS THE INPUT CHANNEL THE CLOSE PANEL'S FINDING 2 FOUND MISSING**, and
    it is worth stating why it has to exist rather than being derived.

    The first draft built the observed set by FILTERING the declared one —
    ``{gate["id"] for gate in gates if gate.get("observed_red")}`` — so
    ``observed - declared`` was empty BY CONSTRUCTION and the limb beneath it
    was unreachable. The function's own docstring promised that *"recorded but
    not declared, and declared but not recorded, are two different defects"*,
    and one of the two could not fire. Dave: *"assert set difference both ways;
    print is not an assertion."*

    So the observations are read from the DOCUMENT and never from the roster.
    Every mapping anywhere in it that carries a truthy `observed_red` contributes
    its `id`, whether or not that mapping is a member of `declaration.gates` —
    which makes an observation recorded in a side block, under a withdrawn id, or
    beside the roster rather than in it, EXPRESSIBLE as input. In the shipped
    document the two sets coincide, and that coincidence is now an assertion
    rather than an identity.

    `docs/schemas/product-gates/cp.product-gates.json` closes this document, so a
    side block is also refused by
    `tests/examples/test_cp_04_gates_declaration.py`. Two independent defenses,
    and this one does not stand down because the other exists: a reader running
    this check alone is entitled to an answer, and the schema says nothing about
    which ids were observed.
    """
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            if node.get("observed_red"):
                identifier = node.get("id")
                found.append(
                    UNATTRIBUTED_OBSERVATION
                    if identifier is None
                    else str(identifier)
                )
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(document)
    return tuple(sorted(found))


def roster_violations(
    gates: Sequence[Mapping[str, Any]], *, observed: Sequence[str]
) -> list[str]:
    """Every way the gate roster fails criterion 42.

    **A ROSTER AND NEVER A CARDINALITY.** A count of sixteen with a wrong member
    audits clean forever, so the declared ids and the observed ids are compared
    as SETS and each direction is named separately — recorded but not declared,
    and declared but not recorded, are two different defects.

    ``observed`` is a SEPARATE INPUT rather than something derived from
    ``gates``, and it is required rather than defaulted. A default reconstructing
    it from the roster would rebuild the dead limb the close panel found: a set
    filtered out of ``declared`` cannot contain anything ``declared`` does not.
    Callers read it from the document with :func:`observations_in`.
    """
    violations: list[str] = []
    if not gates:
        violations.append(
            "the gate declaration is empty, so 'every declared gate has been"
            " observed RED' holds vacuously"
        )
        return violations

    declared = {str(gate["id"]) for gate in gates}
    recorded = {str(identifier) for identifier in observed}

    never_red = sorted(declared - recorded)
    if never_red:
        violations.append(
            f"these declared gates carry no `observed_red` record: {never_red}."
            " A gate never seen red is not evidence that it runs, and fourteen"
            " declared gates once sat idle on this ladder behind exactly that"
            " assumption"
        )
    unowned = sorted(recorded - declared)
    if unowned:
        violations.append(
            f"these ids carry an observation and are not declared: {unowned}."
            " An observation nothing declares is a gate nobody owes, recorded"
            " as evidence for an obligation the roster does not carry"
        )
    withdrawn = sorted({"CFT-G17"} & (declared | recorded))
    if withdrawn:
        violations.append(
            f"`CFT-G17` is {'declared' if 'CFT-G17' in declared else 'observed'}."
            " It was WITHDRAWN 2026-08-31 (Dave) with ontology role 1 and"
            " criterion 41 is withdrawn in place — the roster is SIXTEEN. Read"
            " from the DECLARED ids and the RECORDED ones alike, because an"
            " observation for it beside the roster is the same rejoining"
        )
    for gate in gates:
        record = gate.get("observed_red")
        if not record:
            continue
        for field in ("result", "date", "commit"):
            if not str(record.get(field, "")).strip():
                violations.append(
                    f"{gate['id']}'s `observed_red` carries no {field!r}."
                    " An empty field validates against the closed schema and"
                    " says nothing"
                )
    return violations


def test_every_declared_gate_has_been_observed_red() -> None:
    """Criterion 42, as a ROSTER over `artifacts/gates.yaml`.

    This is the check that stays in the tree after this phase. It is NOT the
    Phase 24.5 coverage checker — `D-IMPL-224` rules that one Phase 24.5's, and
    building a general-purpose cross-product checker here would be the scope
    creep criterion 49 exists to prevent. This is a one-phase self-check over
    cp-04's own declaration.
    """
    gates = declared_gates()
    recorded = observations_in(gates_document())
    violations = roster_violations(gates, observed=recorded)
    assert not violations, "\n".join(violations)

    # BOTH DIFFERENCES, ASSERTED SEPARATELY. `assert declared == observed` on two
    # sorted lists names neither direction when it fails, and the close panel's
    # finding 2 was precisely that one of the two directions could not arise at
    # all. Dave: *"assert set difference both ways; print is not an assertion."*
    declared = {str(gate["id"]) for gate in gates}
    observed = set(recorded)
    assert not declared - observed, (
        "declared and NEVER recorded anywhere in the document:"
        f" {sorted(declared - observed)}"
    )
    assert not observed - declared, (
        "recorded in the document and NEVER declared:"
        f" {sorted(observed - declared)}"
    )


def test_the_roster_check_refuses_a_gate_that_was_never_seen_red() -> None:
    """**Positive control.** One record nulled, and the check names that gate."""
    gates = [dict(gate) for gate in declared_gates()]
    assert gates, "there are no gates to null"
    victim = gates[-1]
    victim["observed_red"] = None
    violations = roster_violations(gates, observed=observations_in(gates))
    assert violations, "a roster with an unobserved gate was accepted"
    assert any(str(victim["id"]) in entry for entry in violations), violations


def _document_with_a_side_observation(identifier: str) -> Any:
    """A SCRATCH copy of the shipped document, plus one observation beside it.

    The declared roster is untouched; the observation is appended OUTSIDE
    `declaration.gates`, which is the shape `observations_in` exists to see and
    the shape the first draft of this check could not represent at all.
    """
    scratch = gates_document()
    scratch["observations_recorded_beside_the_roster"] = [
        {
            "id": identifier,
            "observed_red": {
                "result": "r",
                "date": "2026-09-01",
                "commit": "abc1234",
            },
        }
    ]
    return scratch


def test_the_roster_check_refuses_an_observation_for_an_undeclared_id() -> None:
    """**Positive control.** Recorded-but-not-declared is its own defect.

    **THIS CONTROL PREVIOUSLY PASSED FOR THE WRONG REASON**, which the close
    panel found: it appended `CFT-G99` carrying ``observed_red: None`` and then
    read the violation off the `never_red` limb. That is *declared but never
    red* — the OTHER defect — so the direction it claimed to control was still
    untested. It now feeds a document carrying an observation for an id the
    roster does not declare, and requires the `unowned` limb by its own words.
    """
    recorded = observations_in(_document_with_a_side_observation("CFT-G99"))
    assert "CFT-G99" in recorded, (
        "the observation channel did not see an observation recorded beside the"
        f" roster; it read {list(recorded)}. Without that this control tests"
        " nothing"
    )
    violations = roster_violations(declared_gates(), observed=recorded)
    assert violations, "an undeclared id carrying an observation was accepted"
    assert any("CFT-G99" in entry for entry in violations), violations
    assert any("not declared" in entry for entry in violations), violations


def test_the_roster_check_refuses_an_observation_for_the_withdrawn_id() -> None:
    """**Positive control.** The withdrawal reaches the OBSERVATIONS too.

    An `observed_red` recorded for `CFT-G17` beside the roster is the withdrawn
    id rejoining by the back door. Until finding 2 was fixed the withdrawal limb
    read the DECLARED ids alone, so this shape was invisible to it and to the
    `unowned` limb — which could not fire at all.
    """
    recorded = observations_in(_document_with_a_side_observation("CFT-G17"))
    violations = roster_violations(declared_gates(), observed=recorded)
    assert violations, "an observation for the withdrawn id was accepted"
    assert any("WITHDRAWN" in entry for entry in violations), violations
    assert any("not declared" in entry for entry in violations), violations


def test_the_roster_check_refuses_an_observation_carrying_no_id() -> None:
    """**Positive control.** An observation nothing can be attributed to."""
    scratch = gates_document()
    scratch["observations_recorded_beside_the_roster"] = [
        {"observed_red": {"result": "r", "date": "d", "commit": "c"}}
    ]
    recorded = observations_in(scratch)
    assert UNATTRIBUTED_OBSERVATION in recorded, list(recorded)
    violations = roster_violations(declared_gates(), observed=recorded)
    assert violations, "an observation attributable to no gate was accepted"
    assert any(UNATTRIBUTED_OBSERVATION in entry for entry in violations), violations


def test_the_observation_channel_reads_the_shipped_document_and_is_not_vacuous() -> None:
    """The channel READ the document, so a coincidence is evidence of agreement.

    Without this, `observations_in` could return `()` — a parser that silently
    found nothing — and the `unowned` limb would be green forever while
    `never_red` named all sixteen. The shipped document must yield exactly the
    declared roster, and the sentinel must be absent.
    """
    recorded = observations_in(gates_document())
    declared = sorted(str(gate["id"]) for gate in declared_gates())
    assert sorted(recorded) == declared, (
        f"observations {sorted(recorded)}\ndeclared     {declared}"
    )
    assert UNATTRIBUTED_OBSERVATION not in recorded, recorded


def test_the_roster_check_refuses_cft_g17() -> None:
    """**Positive control.** The withdrawn id must never rejoin the roster."""
    gates = [dict(gate) for gate in declared_gates()]
    gates.append(
        {
            "id": "CFT-G17",
            "observed_red": {"result": "r", "date": "d", "commit": "c"},
        }
    )
    violations = roster_violations(gates, observed=observations_in(gates))
    assert violations, "CFT-G17 was accepted onto the roster"
    assert any("WITHDRAWN" in entry for entry in violations), violations


def test_the_roster_check_refuses_an_empty_declaration() -> None:
    """**Vacuity control.** A roster over nothing is not a roster."""
    violations = roster_violations([], observed=())
    assert violations, "an empty declaration was accepted"
    assert any("vacuously" in entry for entry in violations), violations


def test_the_roster_check_refuses_a_record_with_an_empty_field() -> None:
    """**Positive control.** `result: ""` validates and says nothing."""
    gates = [dict(gate) for gate in declared_gates()]
    gates[0] = {
        **gates[0],
        "observed_red": {"result": "", "date": "2026-09-01", "commit": "abc1234"},
    }
    violations = roster_violations(gates, observed=observations_in(gates))
    assert violations, "a record with an empty `result` was accepted"
    assert any("says nothing" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# THE OTHER HALF OF THE ROSTER — every `test:` reference is COLLECTED.
# ---------------------------------------------------------------------------


def collected_node_ids() -> frozenset[str]:
    """Every pytest node id collected under `tests/examples/`.

    A REAL collection and never `hasattr`: a function pytest does not collect
    does not run, and a module that fails to import contributes no ids at all —
    both of which an attribute lookup on an already-imported module would miss.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/examples/",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        "collection over tests/examples/ failed, so this check cannot tell a"
        f" dangling reference from a broken tree:\n{completed.stdout[-3000:]}"
    )
    return frozenset(
        line.strip() for line in completed.stdout.splitlines() if "::" in line
    )


def dangling_references(
    gates: Sequence[Mapping[str, Any]], collected: frozenset[str]
) -> list[str]:
    """Every declared `test:` reference that is not a COLLECTED node id.

    `D-IMPL-224` defers the executing-test CHECKER to Phase 24.5, so without
    this half the phase could ship sixteen dangling `module::function`
    references while criterion 43 still held — criterion 43 only requires the
    ids be declared as data.

    **THE WHOLE PATH IS COMPARED, NOT THE BASENAME — the 2026-09-01 close
    panel's finding.** As written this resolved a declared reference by
    `(os.path.basename(module), function)`, so the DIRECTORY was discarded: a
    reference naming this module's FILE NAME under `tests/products/` — where no
    such file exists — resolved against the collected node id under
    `tests/examples/`. A reference naming a path that does not exist was
    therefore accepted, which is the same
    reader-stops-looking defect
    `examples/cp-04-corporate-family-tree/deployment.py::refuse_stale_vocabulary_pointer`
    exists for one document over. The comparison is now the literal node id.

    **A reference whose module does not end in `.py` is a violation rather than
    a value to repair.** The earlier form appended the suffix for the caller,
    which meant a malformed declaration resolved anyway; the closed schema
    `docs/schemas/product-gates/cp.product-gates.json` now requires the
    `path.py::Symbol` citation form (`D-IMPL-114`), so a repair here would be
    this check being more forgiving than the document it reads.
    """
    violations: list[str] = []
    if not gates:
        violations.append("no gate was checked, so no reference was resolved")
    if not collected:
        violations.append(
            "the collection read no node id at all, so every reference would"
            " resolve against an empty set and this check would report clean"
            " over an empty tree"
        )
        return violations
    resolvable: set[str] = set()
    for node in collected:
        module, _, function = node.rpartition("::")
        resolvable.add(f"{module}::{function}")
        # A parametrized id collects as `…::name[param]`; a declaration naming
        # the function itself is still a reference to something that runs.
        base, bracket, _params = function.partition("[")
        if bracket:
            resolvable.add(f"{module}::{base}")
    for gate in gates:
        reference = str(gate.get("test", ""))
        module, _, _function = reference.partition("::")
        if not module.endswith(".py"):
            violations.append(
                f"{gate['id']}'s `test:` reference {reference!r} does not name a"
                " `.py` module, so it is not a pytest node id at all"
            )
            continue
        if reference not in resolvable:
            violations.append(
                f"{gate['id']}'s `test:` reference {reference!r} is not a"
                " COLLECTED pytest node id — a function pytest does not collect"
                " does not run. The whole path is compared: a reference with the"
                " right file NAME under the wrong directory names a file that"
                " does not exist"
            )
    return violations


def test_every_gate_test_reference_is_a_collected_pytest_node_id() -> None:
    """Criterion 43's other half — the `key_link` nothing checked.

    Plans 10, 11 and 12 each declare a `key_link` reading *"each gate's test
    reference resolving to an executing function"* and no acceptance criterion
    anywhere verified it. Scoped to cp-04's own `gates.yaml`: this is not the
    Phase 24.5 cross-product checker.
    """
    violations = dangling_references(declared_gates(), collected_node_ids())
    assert not violations, "\n".join(violations)


def test_the_collection_check_refuses_the_right_basename_under_the_wrong_directory() -> None:
    """**Positive control** for the close panel's finding, in its own shape.

    The file name is right, the function is right and it is collected — under
    `tests/examples/`. The declared reference names `tests/products/`, where no
    such file exists. The basename comparison this replaced accepted it.
    """
    gates = [dict(gate) for gate in declared_gates()]
    assert gates, "there are no gates to point at nothing"
    victim = gates[0]
    real = str(victim["test"])
    module, _, function = real.partition("::")
    moved = f"tests/products/{os.path.basename(module)}::{function}"
    assert moved != real, "the control did not move the reference"
    assert not (REPO / f"tests/products/{os.path.basename(module)}").exists(), (
        "the control points at a path that exists, so it is not a dangling"
        " reference at all"
    )
    victim["test"] = moved
    violations = dangling_references(gates, collected_node_ids())
    assert violations, "a reference under a directory with no such file was accepted"
    assert any(moved in entry for entry in violations), violations


def test_the_collection_check_accepts_the_shipped_references() -> None:
    """**Compliance control.** A stricter limb must not refuse the real roster."""
    assert not dangling_references(declared_gates(), collected_node_ids())


def test_the_collection_check_refuses_a_dangling_reference() -> None:
    """**Positive control.** One reference pointed at a function that is not there."""
    gates = [dict(gate) for gate in declared_gates()]
    assert gates, "there are no gates to point at nothing"
    victim = gates[0]
    victim["test"] = "tests/examples/test_cp_04_seams.py::test_no_such_function"
    violations = dangling_references(gates, collected_node_ids())
    assert violations, "a reference to a non-existent function was accepted"
    assert any(str(victim["id"]) in entry for entry in violations), violations
    assert any("test_no_such_function" in entry for entry in violations), violations


def test_the_collection_check_refuses_an_empty_collection() -> None:
    """**Vacuity control.** Resolving against nothing reports clean forever."""
    violations = dangling_references(declared_gates(), frozenset())
    assert violations, "an empty collection was accepted"
    assert any("empty tree" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# THE RECIPE HOLE PLAN 03 MEASURED AND NO PLAN OWNED.
# ---------------------------------------------------------------------------


def cycle_step_violations(steps: Sequence[Mapping[str, Any]]) -> list[str]:
    """The cycle step declares `operator: null` at `layer: L2`, BOUND BY NAME.

    **The obvious form is VACUOUS.** ``any(operator is None and layer == "L2")``
    is satisfied by steps 4 and 8 as well, so it stays true even when the cycle
    step is reclassified under `Traversal` — which is exactly the `D-IMPL-223`
    vocabulary drift the declaration exists to prevent. Plan 03 measured that
    and could not commit a check because no plan owned a recipe-shape test.
    """
    violations: list[str] = []
    matching = [step for step in steps if str(step.get("name")) == CYCLE_STEP]
    if len(matching) != 1:
        violations.append(
            f"the recipe declares {len(matching)} step(s) named {CYCLE_STEP!r};"
            " this assertion is bound to that step BY NAME and cannot address"
            " it otherwise"
        )
        return violations
    step = matching[0]
    if step.get("operator") is not None:
        violations.append(
            f"the {CYCLE_STEP!r} step declares operator"
            f" {step['operator']!r}. `D-10` gives it `null` because it executes"
            " in the L2 assembler, and a Standard operator name here is the"
            " `D-IMPL-223` vocabulary drift this declaration exists to prevent"
        )
    if str(step.get("layer")) != "L2":
        violations.append(
            f"the {CYCLE_STEP!r} step declares layer {step.get('layer')!r},"
            " not 'L2'"
        )
    if not str(step.get("sdk_mechanism") or "").strip():
        violations.append(
            f"the {CYCLE_STEP!r} step names no `sdk_mechanism`, so `operator:"
            " null` records no alternative to the operator it declines"
        )
    return violations


def vacuous_cycle_step_form(steps: Sequence[Mapping[str, Any]]) -> bool:
    """The check this module refuses to ship, kept so the difference is RECORDED.

    ``any(operator is None and layer == "L2")`` — true of several steps, so it
    survives the reclassification the bound form catches. It is exercised beside
    the bound form rather than described, because a recorded difference is
    evidence and a described one is a claim.
    """
    return any(
        step.get("operator") is None and str(step.get("layer")) == "L2"
        for step in steps
    )


def test_the_cycle_step_declares_operator_null_at_l2() -> None:
    """`D-10` and criterion 46, bound to the cycle step BY NAME."""
    violations = cycle_step_violations(recipe_steps())
    assert not violations, "\n".join(violations)


def test_the_cycle_step_check_refuses_a_reclassified_step_where_the_vacuous_form_passes() -> None:
    """**Positive control, and the record of why the obvious form was refused.**

    One scratch copy, two instruments. The bound form goes RED naming the step;
    the vacuous `any(...)` form stays GREEN on the same subject. The difference
    between the two is recorded here rather than asserted in prose.
    """
    scratch = [dict(step) for step in recipe_steps()]
    reclassified = [
        {**step, "operator": "Traversal"}
        if str(step.get("name")) == CYCLE_STEP
        else step
        for step in scratch
    ]
    assert reclassified != scratch, "the scratch copy changed nothing"

    violations = cycle_step_violations(reclassified)
    assert violations, "a cycle step reclassified under Traversal was accepted"
    assert any(CYCLE_STEP in entry for entry in violations), violations
    assert any("vocabulary drift" in entry for entry in violations), violations

    assert vacuous_cycle_step_form(reclassified), (
        "the vacuous `any(...)` form was expected to PASS on the reclassified"
        " recipe — that is the whole reason the bound form exists, and if it"
        " now fails the two instruments are no longer distinguishable and this"
        " control has stopped recording anything"
    )


def test_the_cycle_step_check_refuses_a_recipe_with_no_such_step() -> None:
    """**Vacuity control.** A step-bound assertion needs its step."""
    violations = cycle_step_violations(
        [step for step in recipe_steps() if str(step.get("name")) != CYCLE_STEP]
    )
    assert violations, "a recipe with no cycle step was accepted"
    assert any("0 step(s)" in entry for entry in violations), violations


def test_the_lei_identity_check_refuses_a_shared_lei() -> None:
    """**Positive control.** Two nodes, one LEI — the anchor is ambiguous.

    ``examples/cp-04-corporate-family-tree/deployment.py::resolve_anchor``
    refuses a shared LEI as `AnchorAmbiguityRefusal` (`CFT-G18`), so a shared
    LEI in the committed fixture would turn the default question into a
    refusal. What keeps the fixture on the served path is an estate property,
    and the 2026-09-01 close panel found that nothing asserted it: the
    precondition compared distinct VALUES against the declared node count,
    which a duplicate ACCOMPANIED BY AN EXTRA NODE satisfies exactly.
    """
    carried = [["A"], ["B"], ["B"]]
    violations = lei_identity_violations(
        carried, declared_nodes=3, declared_values=2
    )
    assert violations, "a shared LEI was accepted"
    assert any("more than one node" in entry for entry in violations), violations
    assert not any("node(s) carry an LEI where" in entry for entry in violations), (
        "the node-count limb fired; the point of this control is that the counts"
        " AGREE with the declaration and the identity still does not hold"
    )


def test_the_lei_identity_check_refuses_a_node_carrying_two() -> None:
    """**Positive control.** One node, two LEIs — the other half of the 1:1."""
    violations = lei_identity_violations(
        [["A", "B"], ["C"]], declared_nodes=2, declared_values=3
    )
    assert violations, "a node carrying two LEIs was accepted"
    assert any("MORE THAN ONE LEI" in entry for entry in violations), violations


def test_the_lei_identity_check_refuses_an_estate_with_no_leis() -> None:
    """**Vacuity control.** A 1:1 over nothing is not a narrower claim."""
    violations = lei_identity_violations([], declared_nodes=0, declared_values=0)
    assert violations, "an estate carrying no LEI at all was accepted"
    assert any("proves nothing" in entry for entry in violations), violations


def test_the_lei_identity_check_accepts_the_compliant_shape() -> None:
    """**Compliance control.** A later limb cannot quietly forbid the real case."""
    assert not lei_identity_violations(
        [["A"], ["B"], ["C"]], declared_nodes=3, declared_values=3
    )


# ---------------------------------------------------------------------------
# C-20 — replay dimension 4 names WHICH BUILD made the decision, fulfilled or
# refused, and the refusal's reference RESOLVES.
# ---------------------------------------------------------------------------


def _resolved_record(root: pathlib.Path, reference: str) -> Mapping[str, Any]:
    """One replay record, out of the store `produce.py::_serve` writes.

    The SAME store, resolved by the reference the shell carries — never a
    directory walk. A test that scanned for *a* record would pass against a
    reference pointing nowhere, which is exactly the sentinel failure this
    check exists to catch.
    """
    deployment = _load("deployment")
    store = FileArtifactStore(root=root / deployment.ARTIFACT_STORE_DIRNAME)
    name = parse_artifact_uri(reference)
    return dict(
        json.loads(store.get(content_address=name.artifact_version).decode("utf-8"))
    )


def _refused_over_capability(
    root: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """One ask above the substrate's traversal capability, through the shipped caller.

    **NO STORE IS OPENED AND THAT IS THE POINT.** The effective request is
    resolved before the assembly starts, so a depth the substrate cannot walk
    is refused before either system of record is contacted — the two graph
    variables are set because the CAPABILITY names its leg by ledger, not
    because anything connects.
    """
    from ccf.client.client import ProductClient

    monkeypatch.setenv("CCF_CP_04_FLUREE_URL", "http://fluree.invalid")
    monkeypatch.setenv("CCF_CP_04_FLUREE_LEDGER", "unopened")
    deployment = _load("deployment")
    transport = _load("transport")
    over = deployment.traversal_depth_capability().max_traversal_depth + 1
    typed = deployment.demonstration_request(max_depth=over)
    parameters = {
        name: (value if isinstance(value, (str, int, bool)) else format(value, "f"))
        for name, value in typed.parameters.items()
    }
    client = ProductClient(
        product_id=transport.declared_product_id(),
        adapter=transport.FamilyTreeInProcessAdapter(root=root),
    )
    return client.ask(parameters, as_of=typed.asked_at)


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_a_refused_outcome_carries_the_assembler_identity_and_resolves(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-20's refused half. A refusal is a DECISION and it has a record.

    `D-IMPL-256` and criterion 36: *"every governed determination that crosses
    a CCF delivery boundary — fulfilled or refused — must reach the replay
    writer before the response is released."* So a refused consumer holds a
    reference that RESOLVES, in the store the served path writes, to a record
    whose dimension 4 names the build that refused them and whose dimension 5
    says positively that no product was produced.

    **The store half is the one worth reading.** A shell carrying a
    well-formed-looking reference that resolves to nothing is indistinguishable
    from a recorded one by inspection, which is why the record is fetched and
    read rather than the reference merely checked for shape.
    """
    assembler = _load("assembler")
    result = _refused_over_capability(tmp_path, monkeypatch)

    assert result.refused, f"the over-capability ask was SERVED: {result.payload}"
    shell = result.refusal
    assert shell.kind == REFUSAL_KINDS[ConstraintRefusal], shell.kind
    assert shell.replay_reference, "the shell carries no replay reference at all"
    assert shell.replay_reference != NO_REPLAY_REFERENCE, (
        "the shell carries the NO-RECORD sentinel, which is the positive claim"
        " that the seam that produced it recorded nothing — a governed"
        " determination crossed a delivery boundary with no audit behind it"
    )

    record = _resolved_record(tmp_path, shell.replay_reference)
    conditioning = record["perspective_conditioning"]
    assert conditioning["assembler_id"] == assembler.ASSEMBLER_ID, conditioning
    assert conditioning["assembler_version"] == assembler.ASSEMBLER_VERSION, (
        conditioning
    )
    path = record["content_generation_path"]
    assert path["product_content_address"] == NO_PRODUCT_ADDRESS, path[
        "product_content_address"
    ]
    internal = path.get("assembly_refusal")
    assert internal, f"the record names no refusal: {sorted(path)}"
    internal = json.loads(internal) if isinstance(internal, str) else internal
    assert internal["kind"] == REFUSAL_KINDS[ConstraintRefusal], internal


#: Every bare-named module of this example, evicted TOGETHER by the
#: scratch-shadow control below. **Found RED at the 24.6 close (F-C (iv)).**
#: The control used to evict five of the eight and leave `compose`, `serve`
#: and `run` cached; `compose` then held the assembler object the eviction had
#: discarded, and the next module's `_load("assembler")` re-imported a second
#: one — so `test_cp_04_two_callers.py::test_both_callers_resolve_to_the_same_assembler_module`
#: went red under the leg's collection order and green alone. The family is
#: the same eight names `_load` evicts, for the reason `_load` gives: evicting
#: one name at a time rebuilds the split-identity problem the eviction exists
#: to prevent.
_SCRATCH_SHADOW_FAMILY = (
    "deployment",
    "produce",
    "projection",
    "assembler",
    "transport",
    "run",
    "compose",
    "serve",
)


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_a_wrapper_that_skips_the_recorder_is_refused_at_the_door(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**Sabotage, on a scratch copy.** Skip the mint and the door refuses to release it.

    The scratch `transport.py` returns the assembler's refusal BARE — well
    formed, right kind, right key, right bound, and no record behind it. That
    is the shape the delivery-boundary checker found three times. Until
    `D-IMPL-260` P-A it crossed with the sentinel reference and only the
    assertion that read the reference could see it; now the door itself
    refuses the bare value as `ccf.products.door::UngovernedResolverResult`, so
    the sabotage is caught one layer earlier and nothing crosses at all.

    Edited in a SCRATCH COPY of the example rather than on the tree, so this
    control runs in CI forever without a shipped file ever being wrong.
    """
    from ccf.client.client import ProductClient
    from ccf.products.door import UngovernedResolverResult

    scratch = tmp_path / "example"
    shutil.copytree(EXAMPLE, scratch, ignore=shutil.ignore_patterns("__pycache__"))
    module = scratch / "transport.py"
    text = module.read_text(encoding="utf-8")
    needle = "        if type(outcome) in REFUSAL_KINDS:\n"
    assert text.count(needle) == 1, (
        "the shipped transport no longer has the branch this sabotage removes,"
        " so the control would be editing nothing"
    )
    module.write_text(
        text.replace(needle, "        if type(outcome) in REFUSAL_KINDS:\n            return outcome\n"),
        encoding="utf-8",
    )

    monkeypatch.setenv("CCF_CP_04_FLUREE_URL", "http://fluree.invalid")
    monkeypatch.setenv("CCF_CP_04_FLUREE_LEDGER", "unopened")
    monkeypatch.syspath_prepend(str(scratch / "server"))
    monkeypatch.syspath_prepend(str(scratch))
    for name in _SCRATCH_SHADOW_FAMILY:
        sys.modules.pop(name, None)
    try:
        import deployment as scratch_deployment  # noqa: PLC0415
        import transport as scratch_transport  # noqa: PLC0415

        assert pathlib.Path(scratch_transport.__file__).parent == scratch, (
            "the scratch copy did not shadow the shipped module, so this"
            " control would be sabotaging nothing"
        )
        over = (
            scratch_deployment.traversal_depth_capability().max_traversal_depth + 1
        )
        typed = scratch_deployment.demonstration_request(max_depth=over)
        parameters = {
            name: (
                value if isinstance(value, (str, int, bool)) else format(value, "f")
            )
            for name, value in typed.parameters.items()
        }
        client = ProductClient(
            product_id=scratch_transport.declared_product_id(),
            adapter=scratch_transport.FamilyTreeInProcessAdapter(
                root=tmp_path / "run"
            ),
        )
        with pytest.raises(UngovernedResolverResult, match="bare `ConstraintRefusal`"):
            client.ask(parameters, as_of=typed.asked_at)
    finally:
        for name in _SCRATCH_SHADOW_FAMILY:
            sys.modules.pop(name, None)


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_replay_carries_the_assembler_identity_for_fulfilled_and_refused(
    estate: tuple[str, str], tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-20 whole: ONE recorder, ONE store, the SAME pair on dimension 4.

    The two halves are asserted TOGETHER rather than in two modules, because
    the claim is not *a refusal has a record* and *a product has a record* — it
    is that they are the same audit plane. `D-IMPL-253` Q13, in Dave's words:
    *"Refusal is itself a decision and deserves the same five-dimensional
    replay model. Do not create second-class replay."* Two recorders that
    agreed today would satisfy each half separately and satisfy neither
    together.

    Both records are resolved out of the SAME `FileArtifactStore` — the one
    `produce.py::_serve` writes — under one scratch root, which is the concrete
    form of *"never a second store, or a denial and the product it was denied
    against would be filed in two places."*
    """
    from ccf.client.client import ProductClient

    deployment = _load("deployment")
    transport = _load("transport")
    assembler = _load("assembler")
    root = tmp_path / "one-store"
    root.mkdir()

    adapter = transport.FamilyTreeInProcessAdapter(root=root)
    client = ProductClient(
        product_id=transport.declared_product_id(), adapter=adapter
    )
    typed = deployment.demonstration_request()
    parameters = {
        name: (value if isinstance(value, (str, int, bool)) else format(value, "f"))
        for name, value in typed.parameters.items()
    }
    served = client.ask(parameters, as_of=typed.asked_at)
    assert not served.refused, f"the demonstration ask was refused: {served.refusal}"
    assert served.replay_ref, "the served product carries no replay reference"

    over = deployment.traversal_depth_capability().max_traversal_depth + 1
    refused = client.ask(
        {**parameters, deployment.PARAM_MAX_DEPTH: over}, as_of=typed.asked_at
    )
    assert refused.refused, "the over-capability ask was SERVED"

    fulfilled_record = _resolved_record(root, str(served.replay_ref))
    refused_record = _resolved_record(root, str(refused.refusal.replay_reference))

    for label, record in (
        ("fulfilled", fulfilled_record),
        ("refused", refused_record),
    ):
        conditioning = record["perspective_conditioning"]
        assert conditioning["assembler_id"] == assembler.ASSEMBLER_ID, (
            f"the {label} record's dimension 4 names assembler"
            f" {conditioning['assembler_id']!r}"
        )
        assert conditioning["assembler_version"] == assembler.ASSEMBLER_VERSION, (
            f"the {label} record's dimension 4 names version"
            f" {conditioning['assembler_version']!r} where the module is"
            f" {assembler.ASSEMBLER_VERSION!r}"
        )

    assert fulfilled_record["content_generation_path"][
        "product_content_address"
    ] not in (None, NO_PRODUCT_ADDRESS), fulfilled_record["content_generation_path"]
    assert (
        refused_record["content_generation_path"]["product_content_address"]
        == NO_PRODUCT_ADDRESS
    ), refused_record["content_generation_path"]

    # `D-IMPL-260` P-H: THE FULFILLED RECORD CARRIES THE EFFECTIVE-REQUEST
    # RESOLUTION on dimension 2 — which question was actually answered, with
    # the authority that established each value and the bound in force —
    # rather than the sentinel that says no resolution was recorded.
    resolution = fulfilled_record["policy_bindings"].get(
        "request_resolution", NO_REQUEST_RESOLUTION
    )
    assert resolution != NO_REQUEST_RESOLUTION, (
        "the fulfilled record carries no effective-request resolution; replay"
        " could re-ask the caller's question but not the one the fabric"
        " answered (D-IMPL-260 P-H)"
    )
    effective = EffectiveRequest.model_validate_json(resolution)
    depth = effective.parameter(deployment.PARAM_MAX_DEPTH)
    assert depth is not None, effective
    assert int(depth.value) == int(typed.parameters[deployment.PARAM_MAX_DEPTH])
    assert depth.bound is not None and depth.bound.authority == "technical", depth
    assert depth.bound.source.identity == (
        deployment.traversal_depth_capability().capability_identity
    )
    # The refused half was determined before any resolution existed, and its
    # record says so positively.
    assert (
        refused_record["policy_bindings"].get("request_resolution", NO_REQUEST_RESOLUTION)
        == NO_REQUEST_RESOLUTION
    )
