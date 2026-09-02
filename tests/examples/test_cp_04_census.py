"""The census `cp-04` must re-derive, from two stores, at gate time.

Phase 24.4 criteria 3 through 13, plus the census halves of 17 and 18. The
estate is the committed fixture pair — `tests/examples/fixtures/`'s
`cp_04_family_fluree.json` for the graph leg and `cp_04_family_schema.sql` +
`cp_04_family_rows.sql` for the attribute leg — seeded by
`tests/examples/cp_04_seed.py` and by nothing else.

**WHY THIS MODULE IS WEIGHTED THE WAY IT IS.** Rung 03's census module records
the lesson this rung inherits: *every serious defect found while specifying it
was a MEASUREMENT defect*. A wrong method here produces **a plausible number and
no error**, which is the failure that survives review. So the census is gated as
heavily as the assembly.

**EVERY EXPECTATION IS READ FROM `artifacts/expected.yaml` AND NONE IS AUTHORED
HERE** (criterion 45). A figure this module stated would be the module agreeing
with itself about what the estate holds. The rule has a mechanical gate — a grep
for the census figures over this file must find nothing — and that gate is only
worth anything because the artifact is a REVIEWED document rather than a
refreshed transcript.

**EVERY FIGURE IS DERIVED BY QUERY AGAINST THE SEEDED CONTAINERS, THROUGH THE
SHIPPED CODE.** `examples/cp-04-corporate-family-tree/deployment.py` does the
reading, the normalization and the detection; this module drives it and compares.
A census computed by a query written inside a test proves something about the
test. The one place that discipline bites hardest is the direction controls: they
flip an arrow in the table the SHIPPED normalizer reads, and watch the shipped
normalizer's own root count move.

**MARKED FOR BOTH LEGS, AND THE JOB SUPPORTS IT.** `.github/workflows/ci.yml`
exports `CCF_TEST_POSTGRES_DSN`, `CCF_REQUIRE_POSTGRES`, `CCF_TEST_FLUREE_URL`
and `CCF_REQUIRE_FLUREE` at JOB level and runs `make leg-postgres` and
`make leg-fluree` as two steps of that one job, so both service containers are
reachable from either leg. A doubly-marked module is therefore selected twice and
runs whole both times — verified by running both legs, not by reading the marker.

**THE LEDGER AND THE SCHEMA ARE PER-MODULE AND NOT FIXED.** `tests/conftest.py`
makes `fluree_url` session-scoped and env-driven — one server for the whole run,
no per-module container — and `postgres_dsn` says in as many words that isolation
comes from a fresh SCHEMA rather than a fresh server. Six cp-04 modules seed this
one fixture; a fixed name would put them in one ledger and one schema, where a
sibling module's deliberate sabotage leaks into this module's census. This
repository has already shipped a red `leg-postgres` on `main` from shared CI
fixtures colliding by collection order.
"""

from __future__ import annotations

import importlib
import pathlib
import re
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

import psycopg
import pytest
import yaml

from .cp_04_seed import ATTRIBUTE_TABLE, expected_counts, ledger_for, schema_for, seed

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-04-corporate-family-tree"

#: Both stores. See the module docstring for why one job can serve both legs.
pytestmark = [pytest.mark.fluree, pytest.mark.postgres]


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package, and its modules
    import each other by bare name. Five examples on the ladder now ship a
    ``deployment``, a ``produce`` and a ``run`` while one pytest session runs
    over the whole tree — whichever is imported first wins the name, and the
    others then read its constants. So the cache is checked against THIS
    example's directory and the whole family is evicted together when it holds
    somebody else's. Evicting one name at a time would rebuild the split-identity
    problem the eviction prevents. The shape is rung 03's
    (`tests/examples/test_cp_03_output.py`).
    """
    if sys.path[:1] != [str(EXAMPLE)]:
        while str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.path.insert(0, str(EXAMPLE))
    family = ("deployment", "produce", "assembler", "run")
    for cached_name in family:
        cached = sys.modules.get(cached_name)
        if cached is None:
            continue
        if not str(getattr(cached, "__file__", "")).startswith(str(EXAMPLE)):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
    return importlib.import_module(name)


def declared() -> Mapping[str, Any]:
    """The census block of `artifacts/expected.yaml` — this module's ONLY source.

    Reached through the shipped deployment's own path constant, so the artifact
    this module is held to and the artifact the product declares cannot become
    two files.
    """
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.EXPECTED.read_text(encoding="utf-8"))
    census: Mapping[str, Any] = document[deployment.DECLARATION]["census"]
    return census


def short(uri: str) -> str:
    """The local name of a node IRI.

    Derived from the IRI the store answered with, never composed from a prefix
    this module holds. `artifacts/expected.yaml` writes its rosters as local
    names; a prefix authored here would be a domain value in code AND a second
    place for the estate's namespace to be wrong.
    """
    return uri.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Estate:
    """One whole-ledger read, shared by every test in this module.

    Module-scoped because the read is the expensive part and because every
    figure below must be measured against ONE state of the store. A per-test
    read would let the estate drift between two assertions and leave no way to
    say which figure was read against which state — the same reasoning that made
    the measurement pass read `ledger_t` once at its start.
    """

    graph: Any
    attributes: Any
    triples: tuple[Any, ...]
    edges: Any
    facts: Mapping[str, Any]


@pytest.fixture(scope="module")
def seeded(fluree_url: str, postgres_dsn: str) -> Iterator[tuple[str, str]]:
    """One ledger and one schema nobody else can be using, seeded and verified.

    `seed` refuses to return until both stores read back what the fixture
    carries: the server accepts a transaction body with an unrecognized
    top-level key at HTTP 200 and a real commit receipt, so a 200 is not
    evidence that anything was written.
    """
    ledger = ledger_for(__name__)
    schema = schema_for(__name__)
    seed(fluree_url, ledger, postgres_dsn, schema)
    yield ledger, schema


@pytest.fixture(scope="module")
def estate(
    seeded: tuple[str, str], fluree_url: str, postgres_dsn: str
) -> Iterator[Estate]:
    """The whole family graph, read once through the SHIPPED deployment."""
    ledger, schema = seeded
    deployment = _load("deployment")
    graph = deployment.GraphSource(url=fluree_url.rstrip("/"), ledger=ledger)
    attributes = deployment.AttributeSource(dsn=postgres_dsn, schema=schema)
    triples = deployment.enumerate_family_triples(graph)
    edges = deployment.normalize_edges(triples)
    facts = deployment.read_node_facts(sorted(edges.nodes), source=graph)
    yield Estate(
        graph=graph,
        attributes=attributes,
        triples=triples,
        edges=edges,
        facts=facts,
    )


# ---------------------------------------------------------------------------
# Precondition — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_seeder_seeded(seeded: tuple[str, str], estate: Estate) -> None:
    """Without this, every count below could be a true statement about nothing.

    The witness is `cp_04_seed.expected_counts()`, which reads the FIXTURE FILES
    rather than stating a number — so this precondition is a comparison between
    what the committed fixture carries and what the containers now hold, and it
    passes only if the transaction and the two SQL files actually landed.
    """
    _, schema = seeded
    fixture = expected_counts()
    assert len(estate.triples) == fixture["family_triples"], (
        f"the ledger holds {len(estate.triples)} family triples where the"
        f" committed fixture carries {fixture['family_triples']}. Every census"
        " assertion below is measured against this population, so a short seed"
        " makes all of them true of the wrong thing."
    )
    with psycopg.connect(estate.attributes.dsn) as db, db.cursor() as cursor:
        cursor.execute(f'SELECT count(*) FROM "{schema}".{ATTRIBUTE_TABLE}')
        row = cursor.fetchone()
    assert row is not None and int(row[0]) == fixture[f"{ATTRIBUTE_TABLE}_rows"], (
        f"schema {schema!r} does not hold the fixture's {ATTRIBUTE_TABLE} rows;"
        " the attribute leg of every store-split figure below would be measured"
        " against a population nobody loaded."
    )


def test_the_ledger_and_the_schema_are_this_modules_own(
    seeded: tuple[str, str],
) -> None:
    """A shared name is how a sibling module's sabotage becomes this one's census.

    Fluree is append-only and refuses `create` on an existing ledger; the schema
    DDL leads with `DROP TABLE IF EXISTS ... CASCADE` and so CLOBBERS rather
    than raising. Both failures are ordering-dependent and neither names its
    cause, which is why the fix is a name nobody else can be using.
    """
    ledger, schema = seeded
    ledger_prefix = ledger_for(__name__).rsplit("-", 1)[0]
    schema_prefix = schema_for(__name__).rsplit("_", 1)[0]
    assert ledger.startswith(ledger_prefix), (
        f"{ledger!r} did not come from ledger_for(__name__), whose names begin"
        f" {ledger_prefix!r}"
    )
    assert schema.startswith(schema_prefix), (
        f"{schema!r} did not come from schema_for(__name__), whose names begin"
        f" {schema_prefix!r}"
    )
    assert ledger_for(__name__) != ledger_for(__name__), (
        "two calls returned the SAME ledger name, so the suffix is not unique"
        " and six modules could still land in one append-only ledger"
    )
    assert schema_for(__name__) != schema_for(__name__), (
        "two calls returned the SAME schema name, so the second module to seed"
        " would silently rebuild the first module's table underneath it"
    )


# ---------------------------------------------------------------------------
# Criterion 3 — the declared predicates, as a MAPPING.
# ---------------------------------------------------------------------------


def test_the_predicate_counts(estate: Estate) -> None:
    """Criterion 3, asserted as a mapping so a vanished predicate is caught.

    A total would absorb a predicate that stopped contributing: another
    predicate gaining exactly as many triples as this one lost keeps the sum
    right. The mapping cannot be satisfied that way.

    Counted over ENUMERATED rows, never an aggregate. Over this ledger the
    aggregate forms invent phantoms — `COUNT(DISTINCT ?p)` and `GROUP BY ?p`
    each answer something other than `SELECT DISTINCT ?p` — which is why
    `enumerate_family_triples` issues one query per predicate and counts in
    Python.
    """
    expected = declared()["family_predicate_triples"]
    wanted = {name: count for name, count in expected.items() if name != "criterion"}
    wanted.pop("source", None)
    found = dict(Counter(triple.predicate for triple in estate.triples))
    assert found == wanted, (
        f"the per-predicate census is {found}, declared {wanted}. A predicate"
        " missing from the left-hand side contributed no triples at all, which"
        " presents as a predicate that legitimately holds none."
    )


def test_no_predicate_outside_the_declared_roster_is_admitted(estate: Estate) -> None:
    """Criterion 3's other half — *exactly* these, and none of the excluded.

    The artifact declares the relationship predicates this ledger holds that the
    family graph deliberately EXCLUDES. Asserting the roster rather than the
    cardinality is what catches an excluded predicate admitted in place of a
    declared one: same count, different graph.
    """
    deployment = _load("deployment")
    expected = declared()
    wanted = {
        name
        for name in expected["family_predicate_triples"]
        if name not in ("criterion", "source")
    }
    admitted = set(deployment.family_predicate_iris())
    assert admitted == wanted, (
        f"the deployment reads {sorted(admitted)}; the artifact declares"
        f" {sorted(wanted)}"
    )
    excluded = set(expected["predicates_deliberately_excluded"]["names"])
    assert admitted & excluded == set(), (
        f"{sorted(admitted & excluded)} is declared EXCLUDED from the family"
        " graph and is being read into it"
    )
    assert set(triple.predicate for triple in estate.triples) == wanted, (
        "the triples read carry a predicate the roster does not name"
    )


# ---------------------------------------------------------------------------
# Criterion 4 — the collapse, reported rather than hidden.
# ---------------------------------------------------------------------------


def test_the_raw_total_the_normalized_edges_and_the_collapse(estate: Estate) -> None:
    """Criterion 4, all three figures AND the arithmetic relating them.

    The raw triple total counts ASSERTIONS; the normalized edge set counts
    RELATIONSHIPS. Several predicates routinely assert the same parent-child
    pair, so a build reporting the raw total is reporting assertions and calling
    them relationships — an error that looks larger and more complete rather
    than smaller and more suspicious.

    The arithmetic is asserted beside the three figures because two numbers that
    drifted together would otherwise agree with each other.
    """
    deployment = _load("deployment")
    expected = declared()["normalization"]
    raw = len(estate.triples)
    normalized = len(estate.edges.by_pair)
    collapsed = deployment.collapse(estate.triples, estate.edges)
    assert raw == expected["raw_family_triples"], (
        f"raw family triples {raw}, declared {expected['raw_family_triples']}"
    )
    assert normalized == expected["distinct_normalized_edges"], (
        f"distinct normalized parent->child edges {normalized}, declared"
        f" {expected['distinct_normalized_edges']}"
    )
    assert collapsed == expected["collapse"], (
        f"the collapse is {collapsed}, declared {expected['collapse']}"
    )
    assert raw - normalized == collapsed, (
        f"{raw} raw minus {normalized} normalized is {raw - normalized}, not the"
        f" {collapsed} the build reports. The three are ONE statement, and a"
        " build whose collapse does not reconcile is reporting a difference it"
        " did not compute."
    )


# ---------------------------------------------------------------------------
# Criterion 5 — the node and root counts.
# ---------------------------------------------------------------------------


def test_the_node_and_root_counts(estate: Estate) -> None:
    """Criterion 5. The root count is the figure the arrow is asserted against."""
    expected = declared()["graph"]
    nodes = len(estate.edges.nodes)
    roots = len(estate.edges.roots)
    assert nodes == expected["distinct_nodes"], (
        f"the family graph holds {nodes} distinct nodes, declared"
        f" {expected['distinct_nodes']}"
    )
    assert roots == expected["roots"], (
        f"the family graph holds {roots} roots, declared {expected['roots']}."
        " A root is a node that is nobody's child, so this figure moves the"
        " moment a single predicate's arrow is read backwards."
    )


# ---------------------------------------------------------------------------
# Criterion 6 — direction, per predicate, with the reversal controls.
# ---------------------------------------------------------------------------


def test_the_declared_direction_of_each_predicate(estate: Estate) -> None:
    """Criterion 6's claim: each predicate's arrow, asserted by name.

    The deployment reads the table from `artifacts/source-vocabulary.yaml` and a
    predicate with no declared arrow fails closed rather than defaulting to
    either reading — a guessed arrow is an arrow nobody chose, and it presents
    as a perfectly clean edge count.
    """
    deployment = _load("deployment")
    expected = declared()["edge_direction"]["reading"]
    found = dict(deployment.family_predicate_directions())
    assert found == dict(expected), (
        f"the shipped direction table is {found}, declared {dict(expected)}"
    )


def test_reversing_any_one_direction_moves_the_root_count(estate: Estate) -> None:
    """Criterion 6's control: all reversals run, one per predicate.

    **A BARE COUNT CANNOT STAND IN FOR AN ARROW.** A product that reported the
    right edge total and the right root total with one arrow backwards would
    look right on both figures — so the claim is made falsifiable by flipping
    each predicate in turn, in the table the SHIPPED normalizer reads, and
    asserting the normalizer's own output moves.

    Every reversal is asserted twice: against its declared flipped figures, and
    against the correct root count it must NOT equal. The first alone would pass
    on a table that had stopped being consulted; the second alone would pass on
    any wrong number at all.
    """
    deployment = _load("deployment")
    expected = declared()
    flipped_table = expected["edge_direction_flipped"]
    correct_roots = expected["graph"]["roots"]
    reverse = {
        deployment.DIRECTION_SUBJECT_TO_OBJECT: deployment.DIRECTION_OBJECT_TO_SUBJECT,
        deployment.DIRECTION_OBJECT_TO_SUBJECT: deployment.DIRECTION_SUBJECT_TO_OBJECT,
    }
    directions = dict(deployment.family_predicate_directions())
    ran: list[str] = []
    for name in sorted(directions):
        sabotaged = dict(directions)
        sabotaged[name] = reverse[sabotaged[name]]
        moved = deployment.normalize_edges(estate.triples, directions=sabotaged)
        declared_flip = flipped_table[name]
        assert len(moved.by_pair) == declared_flip["edges"], (
            f"reversing {name!r} gives {len(moved.by_pair)} edges, declared"
            f" {declared_flip['edges']}"
        )
        assert len(moved.roots) == declared_flip["roots"], (
            f"reversing {name!r} gives {len(moved.roots)} roots, declared"
            f" {declared_flip['roots']}"
        )
        assert len(moved.roots) != correct_roots, (
            f"reversing {name!r} leaves the root count at {correct_roots}, so"
            " that predicate's arrow is INVISIBLE to the root count and the"
            " census cannot tell a correct reading from a backwards one."
        )
        ran.append(name)
    assert set(ran) == set(flipped_table) - {"criterion", "source"}, (
        f"the reversal controls ran for {sorted(ran)}; the artifact declares a"
        f" flipped reading for {sorted(set(flipped_table) - {'criterion', 'source'})}."
        " A predicate with no reversal control is a predicate whose arrow is"
        " asserted and never tested."
    )


# ---------------------------------------------------------------------------
# Criterion 7 — LEI coverage, and the population it is measured against.
# ---------------------------------------------------------------------------


def test_lei_coverage_over_the_family_graph(estate: Estate) -> None:
    """Criterion 7, resolved in the declared attribute table and named as such.

    **THE TABLE IS NAMED IN THE QUERY AND IN THE FAILURE MESSAGE.** The
    substitution this estate has already produced once is the decoy table: the
    same LEIs measured against it give a real number about the wrong thing,
    which survives re-checking. Naming the table in the message is what makes a
    red here say *which population answered* rather than only *the number was
    wrong*.
    """
    deployment = _load("deployment")
    expected = declared()["lei_coverage"]
    assert len(estate.facts) == expected["family_nodes"], (
        f"node facts were read for {len(estate.facts)} of the family graph's"
        f" {expected['family_nodes']} nodes. `read_node_facts` DROPS a node the"
        " ledger holds no class chain for, so a short count here is untyped"
        " nodes and not a smaller graph."
    )
    carrying = [facts.lei for facts in estate.facts.values() if facts.lei]
    assert len(carrying) == expected["nodes_carrying_lei"], (
        f"{len(carrying)} of {len(estate.facts)} nodes carry an LEI, declared"
        f" {expected['nodes_carrying_lei']}"
    )
    assert len(set(carrying)) == expected["distinct_lei_values"], (
        f"{len(set(carrying))} distinct LEI values across {len(carrying)}"
        " carriers; the declared relation is one-to-one, so a shortfall means"
        " an LEI is shared and every per-node resolution below is ambiguous"
    )
    resolution = deployment.resolve_attributes(carrying, source=estate.attributes)
    assert len(resolution.rows) == expected["resolving_in_legal_entity"], (
        f"{len(resolution.rows)} of {len(carrying)} LEIs resolve in"
        f' "{estate.attributes.schema}".{ATTRIBUTE_TABLE}, declared'
        f" {expected['resolving_in_legal_entity']}. If this number is far below"
        f" the declaration, check WHICH TABLE answered — the declared table is"
        f" {expected['correct_table']!r} and the decoy is"
        f" {expected['decoy_table']!r}."
    )
    assert all(
        ATTRIBUTE_TABLE in statement for statement in resolution.statements
    ), (
        f"the attribute leg issued {list(resolution.statements)}, and not every"
        f" statement names {ATTRIBUTE_TABLE}"
    )


def test_the_attribute_table_is_the_declared_one_and_not_the_decoy() -> None:
    """Criterion 7's population control, asserted on the shipped vocabulary.

    The resolution figure alone cannot carry this: a build reading the decoy
    would report a number, and a reader with no declaration in front of them
    would have no way to tell a wrong population from a wrong count. So the
    table the deployment actually reads is compared to the artifact's declared
    correct table AND to its declared decoy, by name.
    """
    deployment = _load("deployment")
    expected = declared()["lei_coverage"]
    vocabulary = deployment.source_vocabulary()[deployment.VOCAB_ATTRIBUTES]
    table = str(vocabulary[deployment.VOCAB_TABLE])
    assert table == expected["correct_table"], (
        f"the deployment resolves attributes out of {table!r}; the declared"
        f" table is {expected['correct_table']!r}"
    )
    assert table != expected["decoy_table"], (
        f"the deployment resolves attributes out of the DECOY table"
        f" {expected['decoy_table']!r} — a real number about the wrong thing"
    )
    assert ATTRIBUTE_TABLE == expected["correct_table"], (
        "the seeder and the deployment disagree about which table the fixture"
        " loads, so the census would be measured against a table nobody seeded"
    )


# ---------------------------------------------------------------------------
# Criterion 8 — the anchor.
# ---------------------------------------------------------------------------


def test_the_anchor(estate: Estate) -> None:
    """Criterion 8, by MEMBERS and by length.

    A chain LENGTH alone would pass on a wrong chain — any other class list of
    the same size satisfies it — so the members are asserted beside it. The
    chain is the one fact on this product that comes from nowhere else: nothing
    in the request, nothing in the attribute store and nothing the assembler
    computes carries a FIBO class chain.

    The anchor is REACHED rather than composed: the request's subject is an LEI
    and the walk's anchor is an IRI, and the step between them is a read. A test
    that built the IRI out of the LEI would be minting node identity from a
    string, and would keep passing after the store stopped holding the node.
    """
    deployment = _load("deployment")
    expected = declared()["anchor"]
    asked = deployment.demonstration_anchor()
    assert asked == expected["lei"], (
        f"the bundled demonstration asks about {asked!r}; the declared anchor"
        f" carries {expected['lei']!r}, so the census below would be measured"
        " against a company nobody declared"
    )
    uri = deployment.resolve_anchor(asked, source=estate.graph)
    assert uri == expected["uri"], (
        f"the LEI {asked!r} resolves to {uri!r}, declared {expected['uri']!r}"
    )
    facts = estate.facts[uri]
    assert facts.lei == expected["lei"], f"anchor LEI {facts.lei!r}"
    assert facts.label == expected["label"], f"anchor label {facts.label!r}"
    assert len(facts.type_chain) == expected["type_chain_length"], (
        f"the anchor's class chain is {len(facts.type_chain)} long, declared"
        f" {expected['type_chain_length']}"
    )
    assert sorted(short(entry) for entry in facts.type_chain) == sorted(
        expected["type_chain"]
    ), (
        f"the anchor's class chain is"
        f" {sorted(short(entry) for entry in facts.type_chain)}, declared"
        f" {sorted(expected['type_chain'])}. The LENGTH agreeing is not the"
        " claim; a different chain of the same size would satisfy it."
    )


# ---------------------------------------------------------------------------
# Criterion 9 — the direct children, as a ROSTER.
# ---------------------------------------------------------------------------


def test_the_anchors_direct_children_as_a_roster(estate: Estate) -> None:
    """Criterion 9. A right count with a wrong member audits clean forever.

    **THE DISCUSS SITTING RECORDED A DIFFERENT SPLIT** — one more Exhibit-21
    stub and one fewer non-stub child than the estate holds. The split asserted
    here is the MEASURED correction the ROADMAP carries, and the total was right
    in both readings, which is precisely why a total cannot stand for a roster.

    **THE CLASSIFIER IS ROSTER MEMBERSHIP AND NOT A PREFIX RULE.** The artifact
    records why: two of the stubs carry a lower-case `micro`, so a rule matching
    the longer capitalized prefix finds fewer than the roster and reports a
    clean-looking count. Membership in a declared roster cannot go wrong that
    way, and it is also what catches a stub renamed into the other group.
    """
    expected = declared()["anchor_direct_children"]
    anchor = declared()["anchor"]["uri"]
    children = {short(child) for child in estate.edges.children[anchor]}
    stubs = set(expected["exhibit_21_stubs"])
    others = set(expected["non_stub_children"])
    assert children == stubs | others, (
        f"the anchor's direct children are {sorted(children)}; the declared"
        f" roster is {sorted(stubs | others)}."
        f" Missing: {sorted(stubs | others - children)}."
        f" Unexpected: {sorted(children - (stubs | others))}."
    )
    assert len(children) == expected["total"], (
        f"{len(children)} direct children, declared {expected['total']}"
    )
    assert stubs & others == set(), (
        f"{sorted(stubs & others)} is declared in BOTH groups, so the split is"
        " not a partition and the two counts below cannot both be checks"
    )
    assert len(children & stubs) == expected["exhibit_21_stub_count"], (
        f"{len(children & stubs)} of the children are declared Exhibit-21"
        f" stubs, declared {expected['exhibit_21_stub_count']}"
    )
    assert len(children & others) == expected["total"] - expected[
        "exhibit_21_stub_count"
    ], (
        f"{len(children & others)} of the children are declared non-stubs; the"
        " declared total and stub count leave"
        f" {expected['total'] - expected['exhibit_21_stub_count']}"
    )


def test_the_anchors_children_by_predicate(estate: Estate) -> None:
    """Criterion 9's per-predicate attribution, and the correction inside it.

    Filed under criterion 9 in the artifact because one of these figures is the
    whole reason a later control is a real control: the anchor has a NON-ZERO
    consolidation edge, where an earlier draft asserted none — written from the
    shape of the argument rather than from a query. Had that stood, the control
    built on it would have been an empty walk asserting no cycle, which is a
    control that cannot fail.
    """
    expected = declared()["anchor_children_by_predicate"]
    anchor = declared()["anchor"]["uri"]
    wanted = {
        name: count
        for name, count in expected.items()
        if name not in ("criterion", "source")
    }
    found = {
        name: sum(
            1
            for child in estate.edges.children[anchor]
            if name in estate.edges.predicates_for((anchor, child))
        )
        for name in wanted
    }
    assert found == wanted, (
        f"the anchor's per-predicate child counts are {found}, declared"
        f" {wanted}. A predicate dropping to zero here is a walk that would"
        " traverse nothing and assert cleanly about it."
    )


# ---------------------------------------------------------------------------
# Criterion 10, census half — the same company entered twice.
# ---------------------------------------------------------------------------


def test_the_same_company_is_entered_twice_one_hop_from_the_anchor(
    estate: Estate,
) -> None:
    """Criterion 10's CENSUS half: the estate CONTAINS the pair.

    **THE PRODUCT HALF IS PLAN 11's** — that the served product SURFACES the
    pair as a finding rather than silently serving both as distinct
    subsidiaries. Stated so the split is deliberate rather than an omission: a
    family that double-counts a subsidiary is a concentration denominator wrong
    in the safe-looking direction, and that is a claim about what is SERVED,
    which this module does not assemble.

    What is asserted here is what the estate holds: both nodes exist, both are
    DIRECT children of the anchor, their LEI presence DIFFERS — so an LEI-keyed
    comparison finds nothing — and their labels differ only by punctuation and
    case, so an equality comparison finds nothing either. Those two facts
    together are why the shipped comparison folds the label.
    """
    expected = declared()["duplicate_entity_pair"]["members"]
    anchor = declared()["anchor"]["uri"]
    children = {short(child) for child in estate.edges.children[anchor]}
    by_short = {short(uri): uri for uri in estate.edges.nodes}
    labels: list[str] = []
    for member in expected:
        name = member["uri"]
        assert name in by_short, f"{name!r} is not a node of the family graph"
        assert name in children, (
            f"{name!r} is not a DIRECT child of the anchor, so the pair is not"
            " one hop away and the duplicate is not the one declared"
        )
        facts = estate.facts[by_short[name]]
        assert facts.lei == member["lei"], (
            f"{name!r} carries LEI {facts.lei!r}, declared {member['lei']!r}"
        )
        assert facts.label == member["label"], (
            f"{name!r} carries label {facts.label!r}, declared"
            f" {member['label']!r}"
        )
        assert len(facts.type_chain) == member["type_chain_length"], (
            f"{name!r} carries a class chain of {len(facts.type_chain)},"
            f" declared {member['type_chain_length']}"
        )
        labels.append(str(facts.label))
    carried = [member["lei"] for member in expected]
    assert len([lei for lei in carried if lei]) == 1, (
        f"the declared pair carries {carried}; the point of the pair is that"
        " EXACTLY ONE member has an LEI, so an LEI-keyed comparison of the two"
        " finds nothing. A pair where both carry one, or neither does, is a"
        " different pair and would be caught by a comparison this product does"
        " not make."
    )
    assert labels[0] != labels[1], (
        f"the two labels are identical ({labels[0]!r}), so an equality"
        " comparison would already find the pair and the fold would be"
        " unnecessary"
    )

    def folded(label: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", label.casefold()).split())

    assert folded(labels[0]) == folded(labels[1]), (
        f"{labels[0]!r} and {labels[1]!r} do not agree once case and"
        " punctuation are folded away, so they differ by more than the"
        " declaration says and the pair is not the declared one"
    )


# ---------------------------------------------------------------------------
# Criterion 11 — the anchor's subtree.
# ---------------------------------------------------------------------------


def test_the_anchor_subtree(estate: Estate) -> None:
    """Criterion 11: the subtree's size, its maximum depth, and named depths.

    **THE WALK IS UNBOUNDED HERE, DELIBERATELY.** Bounding it at the declared
    maximum and then asserting the maximum came out at the bound would be the
    test agreeing with itself. The bound used is the node count of the whole
    family graph, which no simple path can exceed; the walk is cycle-safe by
    construction — a node already assigned a depth is never re-queued — so it
    terminates inside the cycle it reaches rather than running forever.

    The three named per-node depths are asserted individually rather than only
    the maximum, because the maximum is attained by exactly one of them and the
    other two would be invisible to it.
    """
    expected = declared()["anchor_subtree"]
    anchor = declared()["anchor"]["uri"]
    reached = estate.edges.reach(anchor, depth_limit=len(estate.edges.nodes))
    assert len(reached) == expected["reachable_nodes"], (
        f"the anchor's subtree reaches {len(reached)} nodes (the anchor"
        f" included), declared {expected['reachable_nodes']}"
    )
    assert max(reached.values()) == expected["maximum_depth"], (
        f"the subtree's maximum depth is {max(reached.values())}, declared"
        f" {expected['maximum_depth']}"
    )
    by_short = {short(uri): depth for uri, depth in reached.items()}
    for name, depth in expected["depth_to"].items():
        assert name in by_short, (
            f"{name!r} is not reachable from the anchor at all, so its declared"
            " depth is a claim about a node this walk never visits"
        )
        assert by_short[name] == depth, (
            f"{name!r} sits at depth {by_short[name]}, declared {depth}"
        )
    cumulative = {
        depth: sum(1 for value in reached.values() if value <= depth)
        for depth in set(value for value in reached.values())
    }
    for entry in expected["nodes_reached_by_depth"]:
        assert cumulative[entry["depth"]] == entry["nodes"], (
            f"depth {entry['depth']} reaches {cumulative[entry['depth']]}"
            f" nodes, declared {entry['nodes']}. Each depth is a DIFFERENT"
            " answer, which is what makes a depth-varying content address"
            " material rather than decorative."
        )


# ---------------------------------------------------------------------------
# Criterion 12 — the subtree's store split.
# ---------------------------------------------------------------------------


def test_the_anchor_subtree_store_split(estate: Estate) -> None:
    """Criterion 12: the multi-store split made visible on one small subtree.

    The tree is the graph store's and the attributes are the attribute store's,
    and most of this subtree has no attribute row at all. **A member with no row
    is a member** — a build that quietly served only the resolvable ones would
    return a smaller, tidier, WRONG family, with no error.

    All three figures are asserted, plus the arithmetic relating them, so a
    drifted pair cannot agree with each other.
    """
    deployment = _load("deployment")
    expected = declared()["anchor_subtree_store_split"]
    anchor = declared()["anchor"]["uri"]
    reached = estate.edges.reach(anchor, depth_limit=len(estate.edges.nodes))
    assert len(reached) == expected["subtree_nodes"], (
        f"the subtree holds {len(reached)} nodes, declared"
        f" {expected['subtree_nodes']}"
    )
    carrying = {
        short(uri): estate.facts[uri].lei
        for uri in reached
        if estate.facts[uri].lei
    }
    assert len(carrying) == expected["nodes_carrying_lei"], (
        f"{len(carrying)} of the subtree's nodes carry an LEI, declared"
        f" {expected['nodes_carrying_lei']}"
    )
    assert carrying == {
        entry["uri"]: entry["lei"] for entry in expected["the_two_resolving"]
    }, (
        f"the LEI-carrying members are {carrying}; the declared roster is"
        f" {{{', '.join(repr(entry['uri']) for entry in expected['the_two_resolving'])}}}."
        " A right count with a wrong member audits clean forever."
    )
    resolution = deployment.resolve_attributes(
        sorted(carrying.values()), source=estate.attributes
    )
    assert len(resolution.rows) == expected["of_those_resolving_in_legal_entity"], (
        f"{len(resolution.rows)} of the subtree's LEIs resolve in"
        f' "{estate.attributes.schema}".{ATTRIBUTE_TABLE}, declared'
        f" {expected['of_those_resolving_in_legal_entity']}"
    )
    without = len(reached) - len(resolution.rows)
    assert without == expected["nodes_with_no_postgres_row"], (
        f"{without} of the subtree's members resolve to no attribute row,"
        f" declared {expected['nodes_with_no_postgres_row']}"
    )
    assert len(resolution.rows) + without == expected["subtree_nodes"], (
        f"{len(resolution.rows)} resolved plus {without} unresolved is"
        f" {len(resolution.rows) + without}, not the"
        f" {expected['subtree_nodes']} the subtree holds. These are not"
        " independent counts, and a fixture where they fail to reconcile has"
        " drifted inconsistently."
    )


# ---------------------------------------------------------------------------
# Criterion 13 — the deepest tree anywhere in the estate.
# ---------------------------------------------------------------------------


def test_the_deepest_tree_in_the_estate(estate: Estate) -> None:
    """Criterion 13, phrased as *the depth, WHICH this root attains*.

    **NEVER AS "THE DEEPEST ROOT IS ..."** — that asserts a uniqueness this
    estate does not carry. Several roots attain the maximum, nothing
    distinguishes the named one among them, and it is not even the largest tree
    of the set. So the roster of every root attaining the maximum is asserted,
    the named root is asserted to be A MEMBER of it, and the non-uniqueness is
    asserted in as many words — an assertion that the named root is the ONLY one
    would be RED against the estate, which is the point.

    This is the measurement the declared ceiling rests on, so the whole root
    depth distribution is asserted beside the maximum: a distribution that moved
    while its maximum stayed put would leave the ceiling resting on a different
    estate.
    """
    expected = declared()["deepest_tree"]
    bound = len(estate.edges.nodes)
    deepest = {
        root: max(estate.edges.reach(root, depth_limit=bound).values())
        for root in estate.edges.roots
    }
    maximum = max(deepest.values())
    assert maximum == expected["maximum_depth_anywhere"], (
        f"the deepest tree anywhere in the estate runs to depth {maximum},"
        f" declared {expected['maximum_depth_anywhere']}"
    )
    attaining = sorted(short(root) for root, depth in deepest.items() if depth == maximum)
    assert attaining == sorted(expected["roots_attaining_it_roster"]), (
        f"the roots attaining that depth are {attaining}; the declared roster"
        f" is {sorted(expected['roots_attaining_it_roster'])}"
    )
    assert len(attaining) == expected["roots_attaining_it"], (
        f"{len(attaining)} roots attain it, declared"
        f" {expected['roots_attaining_it']}"
    )
    # WHICH root the criterion names is read out of the ARTIFACT'S OWN KEY —
    # `<root>_attains_it` — and matched back to the roster case-insensitively.
    # A root name authored here would be a domain value in code AND a second
    # place for the criterion's subject to be wrong.
    attains_key = next(key for key in expected if key.endswith("_attains_it"))
    stem = attains_key[: -len("_attains_it")]
    unique_key = f"{stem}_is_unique"
    named = next(
        root
        for root in expected["roots_attaining_it_roster"]
        if re.sub(r"[^a-z0-9]+", "_", root.casefold()) == stem
    )
    assert expected[attains_key] is True, (
        f"the artifact no longer declares that {named} attains the maximum, so"
        " this test is asserting something nobody declared"
    )
    assert named in attaining, (
        f"{named} does not attain the maximum depth; the roots that do are"
        f" {attaining}"
    )
    assert expected[unique_key] is False, (
        f"the artifact now declares {named} UNIQUE among the attaining roots."
        " The estate does not carry that uniqueness, and this criterion must"
        f" never be phrased as *the deepest root IS* {named} — only as *the"
        f" maximum depth, which {named} attains*."
    )
    assert len(attaining) > 1, (
        f"only {attaining} attains the maximum depth. The declaration says the"
        " maximum is attained by more than one root, and a phrasing that named"
        " a single deepest root would be asserting a uniqueness the estate does"
        " not have."
    )
    distribution = Counter(deepest.values())
    for entry in expected["root_depth_distribution"]:
        assert distribution[entry["depth"]] == entry["roots"], (
            f"depth {entry['depth']} is attained by"
            f" {distribution[entry['depth']]} roots, declared {entry['roots']}"
        )
    assert sum(distribution.values()) == declared()["graph"]["roots"], (
        f"the distribution covers {sum(distribution.values())} roots where the"
        f" graph holds {declared()['graph']['roots']}, so some root was not"
        " measured and the maximum could sit outside the population"
    )


# ---------------------------------------------------------------------------
# Criteria 17 and 18 — the census halves.
# ---------------------------------------------------------------------------


def test_exactly_one_external_edge_into_any_cycle(estate: Estate) -> None:
    """Criterion 17's census half: EXACTLY one, not one of several.

    **THIS IS A CENSUS CLAIM OVER THE WHOLE GRAPH, NOT A PAYLOAD CLAIM.** The
    detector runs over every normalized edge in the estate, which is the only
    population in which *the only such path* is a statement that can be made.
    One of the two circuits has NO external in-edge at all and is unreachable
    from any LEI-bearing anchor, so its absence from any anchor's subtree is the
    measured shape of this estate rather than a defect.

    The edge itself is asserted beside the count. A count of one with a
    different edge would be the same defect class as a right cycle count with a
    wrong roster.
    """
    deployment = _load("deployment")
    expected = declared()["external_edges_into_any_cycle"]
    findings = deployment.detect_cycles(estate.edges)
    members = {member for finding in findings for member in finding.members}
    assert members, (
        "the detector found no cycle members at all, so the count below would"
        " be zero external edges into an empty set — a check that cannot fail"
    )
    external = sorted(
        (short(parent), short(child))
        for parent, child in estate.edges.pairs
        if child in members and parent not in members
    )
    assert len(external) == expected["count"], (
        f"there are {len(external)} external edges into a cycle — {external} —"
        f" declared {expected['count']}"
    )
    assert external == [(expected["edge"]["parent"], expected["edge"]["child"])], (
        f"the external edge into a cycle is {external}, declared"
        f" {[(expected['edge']['parent'], expected['edge']['child'])]}"
    )


def test_no_cycle_member_carries_an_lei(estate: Estate) -> None:
    """Criterion 18's anchor-side half: every cycle member is unresolvable.

    **THE TYPE-CHAIN-LENGTH HALF OF CRITERION 18 BELONGS WITH THE CYCLE WORK IN
    PLAN 05**, where the two circuits' class chains are compared. Said here so
    the split is deliberate rather than an omission.

    The criterion's own trailing clause — about a type-constrained walk behaving
    differently on each circuit — was STRUCK on 2026-08-31 along with the
    ontology role it belonged to, and is asserted nowhere.

    The roster of members is asserted before the LEI predicate, because *all of
    them carry no LEI* is trivially true of a set the detector failed to
    populate.
    """
    deployment = _load("deployment")
    expected = declared()["cycle_member_typing"]
    findings = deployment.detect_cycles(estate.edges)
    members = sorted(
        {short(member) for finding in findings for member in finding.members}
    )
    assert members == sorted(expected["per_member"]), (
        f"the cycle members are {members}; the declared roster is"
        f" {sorted(expected['per_member'])}"
    )
    by_short = {short(uri): uri for uri in estate.edges.nodes}
    carrying = {
        name: estate.facts[by_short[name]].lei
        for name in members
        if estate.facts[by_short[name]].lei
    }
    assert carrying == {}, (
        f"{carrying} carries an LEI, and the declaration is that no cycle"
        " member does — so every one of them resolves to no attribute row and"
        " the cycle is invisible to an LEI-keyed view of the estate"
    )
    assert expected["all_members_carry_no_lei"] is True, (
        "the artifact no longer declares that no cycle member carries an LEI,"
        " so this test is asserting something nobody declared"
    )
