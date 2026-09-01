"""The circuits `cp-04` contains, and the eleven controls that keep them honest.

Phase 24.4 criteria 14 through 24. The estate is the committed fixture pair
`tests/examples/fixtures/`'s `cp_04_family_fluree.json` and the two SQL files,
seeded by `tests/examples/cp_04_seed.py` and by nothing else.

**THE DETECTOR UNDER TEST IS THE SHIPPED ONE, AND THAT IS THIS MODULE'S WHOLE
POSTURE.** `examples/cp-04-corporate-family-tree/deployment.py` carries the
per-predicate normalization and the application-side circuit detector; this
module imports both and drives them, and defines neither. Criterion 19 names
the shipped artifact by type — *yields NO `ownership_cycle` finding* — and
criterion 21's purpose clause is *so an un-normalized graph cannot look green*.
Both are false of the product if the thing under test is a detector written
inside a test module: the graph that could look green is the product's, not the
suite's. Every control here therefore feeds the SHIPPED code a deliberately
wrong INPUT — the raw triple set, an inverted arrow table, a mutated edge set —
rather than standing up a second implementation to be wrong on its behalf.

**ROSTERS, NEVER CARDINALITIES.** `D-13` rules that the gate asserts the
ROSTER and never the bare non-emptiness of `findings`; a detector reporting
*some circuit* stays RED. Criterion 23 makes the difference itself a control: the blind assertion is
run against a detector output carrying the right COUNT and a wrong MEMBER, and
the blind form passes on it while the roster form fails. That contrast is the
control's entire content.

**EVERY EXPECTATION IS READ FROM `artifacts/expected.yaml` AND NONE IS AUTHORED
HERE** (criterion 45). Both rosters, both closing edges, the class-chain
lengths, and all three wrong-method results come from that document. The
wrong-method numbers matter most: had this module authored them, criterion 24
would have become a test checking its own literals against its own literals,
which is the same vacuity as a check reading a token present in both the
compliant and the violating case. The rule has a mechanical gate — no figure of
criteria 14 through 18 appears as a bare numeral anywhere in this file, in code
or in prose — and that gate is worth something only because the artifact is a
REVIEWED document rather than a refreshed transcript.

**CRITERION 18 IS ASSERTED IN ITS SURVIVING HALF ONLY.** It was AMENDED
2026-08-31 (Dave): the trailing clause *"so a type-constrained walk demonstrably
behaves differently on each"* is STRUCK along with ontology role one, because
the second circuit has no external in-edge and no walk from an LEI-bearing
anchor reaches it. The measured seven-versus-five class-chain fact stands and is
asserted below. Nothing here asserts anything about walk behavior on either
circuit, and the withdrawn gate id is named nowhere in this file.

**"BOTH CIRCUITS" IS A CENSUS CLAIM OVER THE WHOLE GRAPH, NEVER A PAYLOAD
CLAIM.** The second circuit has no external in-edge, so its absence from any
anchor's subtree is the measured shape of this estate rather than a defect.

**MARKED FOR THE GRAPH LEG.** Every figure here — the circuits, the class
chains, the absent LEIs — is Fluree's. The attribute leg is seeded anyway
because `cp_04_seed.seed` is one routine that refuses to return until BOTH
stores read back what the fixture carries, and a module that seeded half of it
would be the first to leave a half-seeded fabric behind.

**THE LEDGER AND THE SCHEMA ARE PER-MODULE AND NOT FIXED.** `tests/conftest.py`
makes `fluree_url` session-scoped and env-driven — one server for the whole run
— and `postgres_dsn` says in as many words that isolation comes from a fresh
SCHEMA rather than a fresh server. Six cp-04 modules seed this one fixture, and
this one deliberately mutates edge sets for its controls. A fixed name would put
those mutations in a sibling's census; this repository has already shipped a red
`leg-postgres` on `main` from shared CI fixtures colliding by collection order.
"""

from __future__ import annotations

import ast
import importlib
import pathlib
import re
import sys
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Iterator, Mapping, Sequence

import pytest
import yaml

from .cp_04_seed import expected_counts, ledger_for, schema_for, seed

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
EXAMPLE = REPO / "examples" / "cp-04-corporate-family-tree"

#: The declared expectations, reached by path so PARAMETRIZATION can read the
#: roster of predicates at collection time, before any fixture has run. The
#: deployment's own `EXPECTED` constant is asserted equal to this path below, so
#: the artifact this module is held to and the artifact the product declares
#: cannot drift into being two files.
ARTIFACT = EXAMPLE / "artifacts" / "expected.yaml"

#: The predicate criterion 19 names. It is carried here rather than derived
#: because NOTHING in the artifact distinguishes it — three predicates give the
#: anchor exactly one child — so a derivation would be an invention wearing a
#: citation. It is not trusted either: the test below asserts it is in the
#: deployment's declared roster, that it is one of the acyclic predicates, and
#: that the anchor's walk over it reaches the number of children the artifact
#: declares. A misnamed predicate fails all three, and the third is the one that
#: matters — the measurement pass recorded that an earlier draft asserted this
#: walk was EMPTY, which would have made criterion 19 a control that cannot fail.
CONSOLIDATION_PREDICATE = "isDirectlyConsolidatedBy"

#: The local name of a node IRI, taken from the IRI the store answered with and
#: never composed from a prefix this module holds.
LOCAL_NAME = re.compile(r"[^/]+$")

#: The graph leg. See the module docstring for why the attribute leg is seeded
#: and not marked.
pytestmark = [pytest.mark.fluree]


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package and its modules
    import each other by bare name, while one pytest session runs over a tree
    holding several examples that each ship a `deployment`, a `produce` and a
    `run`. Whichever is imported first wins the name and the others then read
    its constants, so the cache is checked against THIS example's directory and
    the whole family is evicted together when it holds somebody else's. The
    shape is rung three's (`tests/examples/test_cp_03_output.py`).
    """
    if next(iter(sys.path), None) != str(EXAMPLE):
        while str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.path[:] = [str(EXAMPLE), *sys.path]
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


def document() -> Mapping[str, Any]:
    """The whole declaration block of `artifacts/expected.yaml`."""
    loaded: Mapping[str, Any] = yaml.safe_load(ARTIFACT.read_text(encoding="utf-8"))
    return loaded["declaration"]


def declared() -> Mapping[str, Any]:
    """The census block — this module's only source for criteria 14 through 18."""
    census: Mapping[str, Any] = document()["census"]
    return census


def wrong() -> Mapping[str, Any]:
    """The declared wrong methods — this module's only source for criteria 21 to 24.

    Read, never authored. The three `yields` are what make each control able to
    assert a SPECIFIC wrong result rather than only *something differed*, and a
    number stated here would be this module agreeing with itself about what a
    wrong method produces.
    """
    methods: Mapping[str, Any] = document()["wrong_methods"]
    return methods


def short(uri: str) -> str:
    """The local name of a node IRI."""
    found = LOCAL_NAME.search(uri)
    return found.group() if found else uri


def ring(members: Sequence[str]) -> tuple[tuple[str, str], ...]:
    """Every edge of one circuit, its closing edge included.

    A circuit is a SET PLUS THE EDGE THAT CLOSES IT (`D-12`), and the closing
    edge is precisely what a flattened representation loses — which is why
    `CFT-G07` is sabotaged by dropping it. This walks the members in the order
    the detector reported them and wraps back to the head.
    """
    head = next(iter(members))
    return tuple(pairwise((*members, head)))


def predicate_roster() -> tuple[str, ...]:
    """The six declared family predicates, from the artifact's own census keys."""
    counts = declared()["family_predicate_triples"]
    return tuple(sorted(set(counts) - {"criterion", "source"}))


def acyclic_roster() -> tuple[str, ...]:
    """The five predicates that carry no circuit — DERIVED, never authored.

    The circuits' own attribution is declared: both are `predicate: owns`. So
    the acyclic five are the declared family predicates less the one the
    circuits attribute to, and a predicate added to or removed from the family
    graph moves this roster without anybody editing a list here.
    """
    attributed = {
        declared()["cycle_1"]["predicate"],
        declared()["cycle_2"]["predicate"],
    }
    return tuple(sorted(set(predicate_roster()) - attributed))


@dataclass(frozen=True)
class Estate:
    """One whole-ledger read, shared by every test in this module.

    Module-scoped because the read is the expensive part and because every
    figure below must be measured against ONE state of the store. A per-test
    read would let the estate drift between two assertions and leave no way to
    say which figure was read against which state.
    """

    graph: Any
    triples: tuple[Any, ...]
    edges: Any
    findings: tuple[Any, ...]


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
def estate(seeded: tuple[str, str], fluree_url: str) -> Iterator[Estate]:
    """The whole family graph, read and detected through the SHIPPED deployment."""
    ledger, _ = seeded
    deployment = _load("deployment")
    graph = deployment.GraphSource(url=fluree_url.rstrip("/"), ledger=ledger)
    triples = deployment.enumerate_family_triples(graph)
    edges = deployment.normalize_edges(triples)
    yield Estate(
        graph=graph,
        triples=triples,
        edges=edges,
        findings=deployment.detect_cycles(edges),
    )


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_seeder_seeded(estate: Estate) -> None:
    """Without this, every assertion below could be true of an empty graph.

    The witness is `cp_04_seed.expected_counts()`, which reads the FIXTURE FILES
    rather than stating a number — so this is a comparison between what the
    committed fixture carries and what the container now holds.
    """
    fixture = expected_counts()
    assert len(estate.triples) == fixture["family_triples"], (
        f"the ledger holds {len(estate.triples)} family triples where the"
        f" committed fixture carries {fixture['family_triples']}. Every"
        " assertion below is measured against this population, so a short seed"
        " makes all of them true of the wrong thing."
    )


def test_the_ledger_and_the_schema_are_this_modules_own(
    seeded: tuple[str, str],
) -> None:
    """A shared name is how this module's deliberate mutations become a sibling's census.

    Fluree is append-only and refuses `create` on an existing ledger; the schema
    DDL leads with `DROP TABLE IF EXISTS ... CASCADE` and so CLOBBERS rather
    than raising. Both failures are ordering-dependent and neither names its
    cause, which is why the fix is a name nobody else can be using.
    """
    ledger, schema = seeded
    ledger_prefix, _, _ = ledger_for(__name__).rpartition("-")
    schema_prefix, _, _ = schema_for(__name__).rpartition("_")
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


def test_the_detector_and_the_arrow_table_are_the_shipped_ones(
    estate: Estate,
) -> None:
    """Criteria 19 and 21 are claims about the PRODUCT, not about this suite.

    Three things are established, and the third is the one a reader is most
    likely to assume rather than check. First, the artifact this module reads is
    the artifact the deployment declares. Second, the detector and the
    normalization are defined in the example's own module rather than shadowed
    by a sibling example that won the bare name. Third, THE DETECTOR ACTUALLY
    RAN: a count of nothing from a detector that never executed is
    indistinguishable from a clean graph, so the shipped detector is run over an
    EMPTY edge set as well and required to answer differently. A function that
    never executes cannot give two answers.
    """
    deployment = _load("deployment")
    assert deployment.EXPECTED == ARTIFACT, (
        f"this module reads {ARTIFACT} and the deployment declares"
        f" {deployment.EXPECTED}; the expectations and the product would be"
        " held to two different documents"
    )
    for shipped in (
        deployment.detect_cycles,
        deployment.normalize_edges,
        deployment.enumerate_family_triples,
    ):
        home = str(shipped.__globals__.get("__file__", ""))
        assert home.startswith(str(EXAMPLE)), (
            f"{shipped.__name__} was loaded from {home!r}, which is outside"
            f" {EXAMPLE}. The module under test is not this example's."
        )
    empty = deployment.detect_cycles(deployment.FamilyEdges.from_pairs(()))
    assert empty == (), (
        f"the shipped detector answered {empty!r} over an EMPTY edge set, so it"
        " is not a function of its input and no silence it produces below means"
        " anything"
    )
    assert estate.findings, (
        "the shipped detector produced nothing over the whole family graph."
        " Every roster assertion below would then be a statement about an empty"
        " tuple, which is a check that cannot fail."
    )


def test_this_module_defines_no_detector_of_its_own() -> None:
    """The helpers here are a declared ROSTER, so a smuggled detector is visible.

    A detector written in this file would make criterion 19's silence a fact
    about a fixture-side helper and criterion 21's purpose clause literally
    untrue. The rule is enforced two ways: a reader's grep for a definition
    naming a circuit or a normalization finds nothing, and this test pins the
    complete set of non-test definitions — so adding one is an edit somebody has
    to make deliberately and a reviewer can see.
    """
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    defined = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("test_")
    }
    assert defined == {
        "_load",
        "document",
        "declared",
        "wrong",
        "short",
        "ring",
        "predicate_roster",
        "acyclic_roster",
        "seeded",
        "estate",
    }, (
        f"this module defines {sorted(defined)} beside its tests. The roster is"
        " pinned because a helper that walked an adjacency structure would be a"
        " second detector, and every criterion below would then be a statement"
        " about it rather than about the shipped product."
    )


# ---------------------------------------------------------------------------
# Criterion 14 — the circuit set over the whole family graph.
# ---------------------------------------------------------------------------


def test_exactly_two_circuits_both_wholly_inside_the_declared_predicate(
    estate: Estate,
) -> None:
    """Criterion 14: the count, the attribution, and the edges underneath both.

    **A CENSUS CLAIM OVER THE WHOLE GRAPH.** The detector runs over every
    normalized edge in the estate, which is the only population in which *both*
    is a statement that can be made at all.

    The attribution is asserted at three depths rather than one. The count alone
    would pass on two wrong circuits; the detector's own `predicate` field alone
    would pass on a field that had stopped being derived; so every edge of every
    circuit is also checked to be present in the declared predicate's own
    enumeration read subject to object, and the number of circuit edges any
    OTHER predicate contributes is compared against the declared nothing.
    """
    expected = declared()["cycles"]
    attributed = declared()["cycle_1"]["predicate"]
    assert expected["all_wholly_inside_owns"] is True, (
        "the artifact no longer declares the circuits wholly inside one"
        " predicate, so this test is asserting something nobody declared"
    )
    assert len(estate.findings) == expected["distinct_cycles"], (
        f"the shipped detector reports {len(estate.findings)} distinct circuits"
        f" over the whole family graph, declared {expected['distinct_cycles']}:"
        f" {[[short(m) for m in f.members] for f in estate.findings]}"
    )
    assert [finding.predicate for finding in estate.findings] == [
        attributed for _ in estate.findings
    ], (
        f"the circuits attribute to {[f.predicate for f in estate.findings]},"
        f" declared {attributed!r} for both"
    )
    edges = [pair for finding in estate.findings for pair in ring(finding.members)]
    assert len(edges) == expected["cycle_edges"], (
        f"the circuits span {len(edges)} edges, declared"
        f" {expected['cycle_edges']}"
    )
    asserted_by = {
        (short(parent), short(child)): sorted(
            estate.edges.predicates_for((parent, child))
        )
        for parent, child in edges
    }
    assert all(names == [attributed] for names in asserted_by.values()), (
        f"a circuit edge is asserted by something other than {attributed!r}:"
        f" {asserted_by}"
    )
    raw = {
        (triple.subject, triple.object)
        for triple in estate.triples
        if triple.predicate == attributed
    }
    missing = sorted(
        (short(parent), short(child))
        for parent, child in edges
        if (parent, child) not in raw
    )
    assert missing == [], (
        f"{missing} is a circuit edge that is NOT present in the {attributed!r}"
        " enumeration read subject to object, so the circuit is not wholly"
        " inside that predicate however the finding is labelled"
    )
    others = sorted(
        (triple.predicate, short(triple.subject), short(triple.object))
        for triple in estate.triples
        if triple.predicate != attributed
        and (
            (triple.subject, triple.object) in set(edges)
            or (triple.object, triple.subject) in set(edges)
        )
    )
    assert len(others) == expected["cycle_edges_contributed_by_other_predicates"], (
        f"{others} contributes a circuit edge from outside {attributed!r},"
        " declared"
        f" {expected['cycle_edges_contributed_by_other_predicates']} such"
        " contributions in either direction"
    )


# ---------------------------------------------------------------------------
# Criterion 15 — the first circuit, as an EXACT roster.
# ---------------------------------------------------------------------------


def test_circuit_one_is_served_as_an_exact_roster_with_its_closing_edge(
    estate: Estate,
) -> None:
    """Criterion 15, asserted as the ORDERED roster and the closing edge.

    **`D-13` FORBIDS THE BARE NON-EMPTINESS FORM HERE, and the reason is not
    stylistic.**
    A right count with a wrong member audits clean forever; criterion 23 runs
    exactly that substitution and watches this form catch it where the blind
    form does not. The ordered form is only stable because the ordering
    convention is PINNED — the detector rotates every circuit to start at its
    lexicographically smallest member, and a correct detector using a different
    rotation would fail a correct assertion — so the convention the artifact
    declares is asserted beside the roster.

    The full member IRIs are asserted beside the local names because the local
    names are derived from the IRIs: a namespace that moved would leave every
    local name right and every node wrong.
    """
    expected = declared()["cycle_1"]
    convention = declared()["cycles"]["roster_order_convention"]
    assert convention.startswith("rotate_to_"), (
        f"the declared roster-order convention is {convention!r}; an ordered"
        " roster assertion is unstable without one"
    )
    assert len(estate.findings) == declared()["cycles"]["distinct_cycles"], (
        f"the detector reports {len(estate.findings)} circuits, declared"
        f" {declared()['cycles']['distinct_cycles']} — so WHICH finding this"
        " test then reads is not determined, and the roster below could be"
        " asserted against the wrong one"
    )
    found, _ = estate.findings
    assert [short(member) for member in found.members] == list(expected["members"]), (
        f"the first circuit's ordered roster is"
        f" {[short(m) for m in found.members]}, declared"
        f" {list(expected['members'])}"
    )
    assert list(found.members) == list(expected["member_iris"]), (
        f"the first circuit's member IRIs are {list(found.members)}, declared"
        f" {list(expected['member_iris'])}"
    )
    assert [short(node) for node in found.closing_edge] == list(
        expected["closing_edge"]
    ), (
        f"the first circuit's closing edge is"
        f" {[short(n) for n in found.closing_edge]}, declared"
        f" {list(expected['closing_edge'])}. A finding that lost it would keep"
        " every member right and stop saying which edge closes the circuit."
    )
    *_, wraps = ring(found.members)
    assert found.closing_edge == wraps, (
        f"the reported closing edge {found.closing_edge} is not the edge that"
        f" wraps the reported members {found.members}"
    )
    assert found.type == expected["type"], (
        f"the first circuit is served as type {found.type!r}, declared"
        f" {expected['type']!r}"
    )
    assert found.predicate == expected["predicate"], (
        f"the first circuit attributes to {found.predicate!r}, declared"
        f" {expected['predicate']!r}"
    )


# ---------------------------------------------------------------------------
# Criterion 16 — the second circuit, and why it is not the headline.
# ---------------------------------------------------------------------------


def test_circuit_two_is_an_exact_roster_and_carries_no_external_in_edge(
    estate: Estate,
) -> None:
    """Criterion 16: the roster, the closing edge, and the measured in-edge count.

    The in-edge count is the measured reason this circuit is not the headline —
    nothing outside it points into it, so no walk from any LEI-bearing anchor
    reaches it, and its absence from an anchor's subtree is the shape of this
    estate rather than a defect. The roster is asserted BEFORE the in-edge
    count, because *nothing points into these members* is trivially true of a
    set the detector failed to populate.
    """
    expected = declared()["cycle_2"]
    assert len(estate.findings) == declared()["cycles"]["distinct_cycles"], (
        f"the detector reports {len(estate.findings)} circuits, declared"
        f" {declared()['cycles']['distinct_cycles']} — so WHICH finding this"
        " test then reads is not determined"
    )
    _, found = estate.findings
    assert [short(member) for member in found.members] == list(expected["members"]), (
        f"the second circuit's ordered roster is"
        f" {[short(m) for m in found.members]}, declared"
        f" {list(expected['members'])}"
    )
    assert [short(node) for node in found.closing_edge] == list(
        expected["closing_edge"]
    ), (
        f"the second circuit's closing edge is"
        f" {[short(n) for n in found.closing_edge]}, declared"
        f" {list(expected['closing_edge'])}"
    )
    members = set(found.members)
    assert members, "the second circuit has no members, so the count below is vacuous"
    external = sorted(
        (short(parent), short(child))
        for parent, child in estate.edges.pairs
        if child in members and parent not in members
    )
    assert len(external) == expected["external_in_edges"], (
        f"{external} points into the second circuit from outside it, declared"
        f" {expected['external_in_edges']} such edges. This is the measured"
        " reason the circuit is unreachable from any LEI-bearing anchor."
    )
    assert external == [], (
        f"the roster of external in-edges is {external} and the declaration is"
        " that there are none"
    )


# ---------------------------------------------------------------------------
# Criterion 18 — the surviving half. NO struck clause is asserted anywhere.
# ---------------------------------------------------------------------------


def test_the_two_circuits_class_chains_differ_and_no_member_carries_an_lei(
    estate: Estate,
) -> None:
    """Criterion 18 as AMENDED 2026-08-31 (Dave) — the measured half only.

    The trailing clause about a type-constrained walk behaving differently on
    each circuit is STRUCK with ontology role one, and is asserted nowhere in
    this module: nothing here claims anything about admitted sets, class
    boundaries or a stopped-at node.

    What stands is measured and asserted three ways. The declared chain LENGTHS,
    per member. The class SETS, because a length comparison alone would pass on
    two wrong sets of the right sizes — and because the sets are the content the
    lengths only summarize. And the DIFFERENCE between the two circuits' sets,
    which is the fact the criterion turns on. The sets themselves are not
    declared anywhere, so they are asserted against each other rather than
    against a literal: each circuit's three members are required to carry ONE
    chain between them, and the two circuits' chains are required to differ.

    The roster of members is asserted before the LEI predicate, because *none of
    them carries an LEI* is trivially true of a set the detector failed to
    populate.
    """
    deployment = _load("deployment")
    expected = declared()["cycle_member_typing"]
    by_cycle = {
        declared()["cycle_1"]["criterion"]: declared()["cycle_1"]["members"],
        declared()["cycle_2"]["criterion"]: declared()["cycle_2"]["members"],
    }
    reported = sorted(
        {short(member) for finding in estate.findings for member in finding.members}
    )
    assert reported == sorted(expected["per_member"]), (
        f"the circuit members are {reported}; the declared roster is"
        f" {sorted(expected['per_member'])}"
    )
    by_short = {short(node): node for node in estate.edges.nodes}
    facts = deployment.read_node_facts(
        [by_short[name] for name in reported], source=estate.graph
    )
    assert sorted(short(uri) for uri in facts) == reported, (
        f"the graph leg returned facts for {sorted(short(u) for u in facts)} of"
        f" the {len(reported)} circuit members. `read_node_facts` DROPS a node"
        " the ledger holds no class chain for, so a short read is untyped nodes"
        " and not a smaller circuit."
    )
    carrying = {
        name: facts[by_short[name]].lei
        for name in reported
        if facts[by_short[name]].lei
    }
    assert expected["all_members_carry_no_lei"] is True, (
        "the artifact no longer declares that no circuit member carries an LEI,"
        " so this test is asserting something nobody declared"
    )
    assert carrying == {}, (
        f"{carrying} carries an LEI, and the declaration is that no circuit"
        " member does — so every one resolves to no attribute row and the"
        " circuit is invisible to an LEI-keyed view of the estate"
    )
    for name in reported:
        chain = facts[by_short[name]].type_chain
        assert len(chain) == expected["per_member"][name]["type_chain_length"], (
            f"{name} carries {len(chain)} FIBO classes, declared"
            f" {expected['per_member'][name]['type_chain_length']}"
        )
    chains = {}
    for criterion, members in by_cycle.items():
        distinct = {frozenset(facts[by_short[name]].type_chain) for name in members}
        witness = frozenset(facts[by_short[next(iter(members))]].type_chain)
        assert distinct == {witness}, (
            f"the members of the circuit declared under criterion {criterion} do"
            f" not share one class chain: {[sorted(s) for s in distinct]}. The"
            " declared per-member lengths are equal, so a difference here is"
            " two different chains of the same size."
        )
        chains[criterion] = witness
    first, second = (chains[key] for key in sorted(chains))
    assert first != second, (
        "both circuits carry the SAME set of FIBO classes, so the declared"
        " difference in chain length is describing something this estate no"
        " longer exhibits"
    )
    assert len(first) == expected["cycle_1_type_chain_length"], (
        f"the first circuit's shared chain holds {len(first)} classes, declared"
        f" {expected['cycle_1_type_chain_length']}"
    )
    assert len(second) == expected["cycle_2_type_chain_length"], (
        f"the second circuit's shared chain holds {len(second)} classes,"
        f" declared {expected['cycle_2_type_chain_length']}"
    )
