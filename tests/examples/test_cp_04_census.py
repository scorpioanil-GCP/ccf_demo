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
