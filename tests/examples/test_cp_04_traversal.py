"""Five of cp-04's sixteen gates — the traversal set and the depth-identity set.

`CFT-G01`, `CFT-G02`, `CFT-G03`, `CFT-G04` and `CFT-G05`, discharging locked
ROADMAP criteria 25 through 29. Each one is written so that the sabotage
`artifacts/gates.yaml` declares against it turns THIS module red, under THAT
gate's own name — which is the whole content of criterion 42. A gate never seen
red is not evidence that it runs, and fourteen declared gates once sat idle on
this ladder behind exactly that assumption.

## What this module refuses to be

**A check that reads a token present in BOTH the compliant and the violating
case measures vocabulary rather than content.** Phase 24.3 shipped three gates
that passed their first sabotage for precisely that reason, and the finding was
written down after the first and still shipped twice more in the same sitting.
Every gate below therefore reads what the product DID — the served node roster,
the served predicate set, whether a tree came back at all — and never a word the
product uses about itself.

The clearest case is `CFT-G05`. **Measured against the shipped product, an
address-only reading of that gate PASSES its own sabotage.** With
``examples/cp-04-corporate-family-tree/deployment.py::traversal_parameters``
stripped of its depth substitution, the walk runs at the declared ceiling for
every request and the served roster stops moving — yet the two addresses still
differ, because ``max_depth_applied`` is echoed into the payload and the payload
is what is sealed. So the gate asserts
the ROSTERS move as well as the addresses, and the roster limb is the one that
discriminates. The same reasoning puts a roster limb inside `CFT-G04`.

## Where every expected figure comes from

`artifacts/expected.yaml`, and nowhere else. A number authored here would be
this module agreeing with itself about what the estate holds — which is the
vacuity criterion 45 forbids for the census figures and which is no better for
a gate. The two rosters this module reads are the declared FIBO class
vocabulary (`census.anchor.type_chain`) and the six family predicates
(`census.family_predicate_triples`), and the seven predicates the estate carries
and this product deliberately excludes
(`census.predicates_deliberately_excluded.names`) are read too, so that the
six are shown to be a real selection rather than everything available.

**The declared DEPTH values are read from `ccf_config.yaml` through
``deployment.py``, and that is not an exception to the rule — it is the
subject.** `CFT-G03` and `CFT-G04` are assertions ABOUT the declaration: that
above the declared ceiling is refused by name, and that a missing argument takes
the DECLARED default. Reading those two numbers from anywhere but the
declaration would be asserting a coincidence instead of a dependency. What makes
the reading non-circular is that `CFT-G04` changes the declaration in a scratch
copy and requires the walk to FOLLOW it.

## What is deliberately NOT here

**`CFT-G17` does not exist and no test below asserts a type-constrained stop.**
Criterion 41 was WITHDRAWN IN PLACE on 2026-08-31 (Dave) together with ontology
role 1, for two independently measured reasons either of which is sufficient: no
LEI-bearing anchor in this estate reaches a node outside the 7-class profile
within depth 3 (the estate gap), and the Traversal family types the walk on
EDGES only, so a node-class admission filter has no SDK expression at all (the
mechanism gap). It is **not** replaced by a positive-property restatement —
*"every admitted node's class is in the declared set"* was refused BY NAME as a
tautology over a class-homogeneous population. Criterion 41 is discharged by the
id's ABSENCE from the roster, not by a gate.

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

## Vacuity

A precondition test runs first and asserts the seed carries what these gates
need: a non-empty node set, a non-empty edge set, a declared class vocabulary
and a declared predicate roster that the deployment's own configuration agrees
with, and a depth range whose floor, default and ceiling are three distinct
values. Without it a green gate could be a true statement about nothing.

Every gate is expressed as a function returning the ways an observation FAILS,
so a control can hand the **shipped** check a divergent subject and be watched
refusing it. A check that can only ever be handed the passing subject is a check
nobody has watched fail.
"""

from __future__ import annotations

import importlib
import pathlib
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

import pytest
import yaml

from ccf.agents.errors import AssemblyRefused

from .cp_04_seed import ledger_for, schema_for, seed

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-04-corporate-family-tree"
EXPECTED = EXAMPLE / "artifacts" / "expected.yaml"

#: Both stores. `.github/workflows/ci.yml` exports both legs' variables at JOB
#: level and runs `leg-postgres` and `leg-fluree` as two steps of that one job,
#: so a doubly-marked module is selected twice and runs whole both times.
pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

#: The two keys EVERY `census:` block in `expected.yaml` carries beside its
#: figures. Named as the document's own convention rather than left implicit,
#: and :func:`declared_family_predicates` ASSERTS both are present before
#: subtracting them — so a document that stopped carrying them fails loudly
#: instead of quietly admitting a metadata key into a predicate roster.
CENSUS_METADATA_KEYS = ("criterion", "source")

#: The parameter this whole module is about, as `ccf_config.yaml` names it.
#: Read through `deployment.PARAM_MAX_DEPTH` wherever the deployment is loaded;
#: spelled here only for the wire dictionaries the controls build by hand.
MAX_DEPTH = "max_depth"


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package and its modules
    import each other by bare name, while one pytest session runs over a tree
    holding several `deployment`/`produce`/`run` triples. So the cache is
    checked against THIS example's directory and the whole family is evicted
    together when it holds somebody else's — evicting one name at a time would
    rebuild the split-identity problem the eviction prevents. The shape is
    `tests/examples/test_cp_04_debt.py::_load`.
    """
    if sys.path[:1] != [str(EXAMPLE)]:
        while str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.path.insert(0, str(EXAMPLE))
    family = ("deployment", "produce", "projection", "assembler", "transport", "run")
    for cached_name in family:
        cached = sys.modules.get(cached_name)
        if cached is None:
            continue
        if not str(getattr(cached, "__file__", "")).startswith(str(EXAMPLE)):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
    return importlib.import_module(name)


# ---------------------------------------------------------------------------
# The declared expectations, read from the artifact and never authored here.
# ---------------------------------------------------------------------------


def declared() -> Mapping[str, Any]:
    """`artifacts/expected.yaml`'s declaration block."""
    return dict(yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))["declaration"])


def declared_class_vocabulary() -> frozenset[str]:
    """The FIBO classes a served family member may carry, by LOCAL name.

    From `census.anchor.type_chain`, which is the measured chain of this
    estate's anchor. **The population is class-homogeneous and that is measured,
    not assumed** — `expected.yaml` records that all 22 SMCI-subtree members
    carry the IDENTICAL 7-class chain, which is the same property that withdrew
    ontology role 1 — so the anchor's chain IS the vocabulary the served set
    draws from.

    Compared by LOCAL name because the payload carries full IRIs and this
    document carries the census vocabulary; the derivation is
    ``examples/cp-04-corporate-family-tree/deployment.py::class_axis_local_name``'s,
    and :func:`local_name` asserts it is total rather than assuming it.
    """
    return frozenset(str(name) for name in declared()["census"]["anchor"]["type_chain"])


def declared_family_predicates() -> frozenset[str]:
    """The six family predicates, from the census block that counts them.

    The block's figures are keyed by predicate short name and carry the two
    metadata keys every census block carries. Both are asserted present before
    they are subtracted, so a document that stopped carrying them fails here
    rather than silently contributing ``criterion`` to a predicate roster.
    """
    block = declared()["census"]["family_predicate_triples"]
    missing = [key for key in CENSUS_METADATA_KEYS if key not in block]
    if missing:
        raise AssertionError(
            "`census.family_predicate_triples` carries no "
            f"{missing} key, so the predicate roster cannot be separated from"
            " the block's metadata by this module's declared convention"
        )
    return frozenset(str(key) for key in block if key not in CENSUS_METADATA_KEYS)


def deliberately_excluded_predicates() -> frozenset[str]:
    """The seven relationship predicates this estate holds and this product excludes.

    Read so the six are visibly a SELECTION rather than everything available,
    and so `CFT-G02`'s sabotage — admit a seventh — has a declared population to
    draw its name from rather than an invented token.
    """
    block = declared()["census"]["predicates_deliberately_excluded"]
    return frozenset(str(name) for name in block["names"])


def local_name(iri: str) -> str:
    """The local name of one class IRI — `deployment.py`'s own derivation."""
    return iri.rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
# One ask, reduced to what these five gates read.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Asked:
    """What one ask produced: a served product, or a refusal, never both.

    A value rather than a raise, so `CFT-G03` can inspect BOTH limbs of its
    question — *was it refused* and *was a tree returned anyway* — in one
    function. A gate that only caught the exception could not tell a refusal
    from a clamp, because a clamp raises nothing and returns a perfectly
    well-formed tree.
    """

    #: How it was asked, carried into every failure message so a disagreement
    #: names its subject rather than leaving it to be inferred.
    asked_as: str
    #: The served payload, or ``None`` when nothing was served.
    payload: Mapping[str, Any] | None
    #: `sha256` over the vessel's canonical bytes, computed producer-side.
    content_address: str | None
    #: The refusal text, or ``None`` when the ask was answered.
    refusal: str | None

    @property
    def nodes(self) -> tuple[Mapping[str, Any], ...]:
        if self.payload is None:
            return ()
        return tuple(dict(node) for node in self.payload["nodes"])

    @property
    def edges(self) -> tuple[Mapping[str, Any], ...]:
        if self.payload is None:
            return ()
        return tuple(dict(edge) for edge in self.payload["edges"])

    @property
    def roster(self) -> tuple[str, ...]:
        """The served member ROSTER, sorted. Never a count.

        `D-13`: a right count with a wrong member audits clean forever. Two of
        the gates below compare rosters between asks precisely because the
        counts would agree in one of the sabotages they must catch.
        """
        return tuple(sorted(str(node["uri"]) for node in self.nodes))

    @property
    def depth_applied(self) -> Any:
        return None if self.payload is None else self.payload["max_depth_applied"]


def ask(
    *,
    asked_as: str,
    max_depth: int | None = None,
    omit_max_depth: bool = False,
) -> Asked:
    """Ask this deployment one question through the shipped in-process caller.

    Not a reimplementation of the product: the same
    ``ProductClient(product_id=…, adapter=…)`` constructor `run.py` builds
    (`D-IMPL-225` amendment 2), over the same
    ``examples/cp-04-corporate-family-tree/transport.py::FamilyTreeInProcessAdapter``,
    carrying the question
    ``examples/cp-04-corporate-family-tree/deployment.py::demonstration_request``
    composes for both callers.

    ``omit_max_depth`` drops the argument from the wire entirely, which is what
    `CFT-G04` needs and what the bundled demonstration cannot supply:
    `artifacts/question.yaml` carries ``max_depth: 3`` under ``parameters:``, so
    the demonstration question always names its depth and the DECLARED DEFAULT
    is never reached along that path.

    A refusal the assembler RAISES is caught and returned as data —
    ``AssemblyRefused`` is not in ``ccf.products.refusal::REFUSAL_KINDS`` and has
    no envelope, which `transport.py`'s own docstring records as a gap rather
    than papering over. A refusal it RETURNS arrives on the `Result`.
    """
    from ccf.client.client import ProductClient

    deployment = _load("deployment")
    transport = _load("transport")

    typed = deployment.demonstration_request(max_depth=max_depth)
    parameters = {
        name: (value if isinstance(value, (str, int, bool)) else format(value, "f"))
        for name, value in typed.parameters.items()
    }
    if omit_max_depth:
        parameters.pop(deployment.PARAM_MAX_DEPTH, None)

    with tempfile.TemporaryDirectory(prefix="cp04-traversal-") as scratch:
        client = ProductClient(
            product_id=transport.declared_product_id(),
            adapter=transport.FamilyTreeInProcessAdapter(root=pathlib.Path(scratch)),
        )
        try:
            result = client.ask(parameters, as_of=typed.asked_at)
        except AssemblyRefused as refused:
            return Asked(
                asked_as=asked_as, payload=None, content_address=None,
                refusal=f"{type(refused).__name__}: {refused}",
            )
    if result.refused:
        return Asked(
            asked_as=asked_as, payload=None, content_address=None,
            refusal=str(result.refusal),
        )
    return Asked(
        asked_as=asked_as,
        payload=dict(result.payload),
        content_address=str(result.content_address),
        refusal=None,
    )


# ---------------------------------------------------------------------------
# The estate, and the environment the deployment reads it through.
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


@pytest.fixture(scope="module")
def at_the_declared_default(estate: tuple[str, str]) -> Asked:
    """One ask with `max_depth` ABSENT from the wire — the declared default."""
    return ask(asked_as="max_depth absent (the declared default)", omit_max_depth=True)


@pytest.fixture(scope="module")
def at_the_declared_default_again(estate: tuple[str, str]) -> Asked:
    """The SAME question a second time, in a second scratch fabric.

    Two temporary directories, two per-run SQLite files, two file-backed
    artifact stores. `CFT-G05`'s same-depth limb is only worth anything if the
    repeat is genuinely a second run rather than a cached first one.
    """
    return ask(
        asked_as="max_depth absent (repeated in a second fabric)",
        omit_max_depth=True,
    )


@pytest.fixture(scope="module")
def at_the_declared_floor(estate: tuple[str, str]) -> Asked:
    """One ask at the declared FLOOR — a second, shallower question.

    The floor rather than an interesting-looking number: it is read from the
    declaration, and it is the depth furthest from the default, which is what
    makes the two served rosters differ rather than merely the two echoes.
    """
    deployment = _load("deployment")
    floor = deployment.declared_depth_floor()
    return ask(asked_as=f"max_depth={floor} (the declared floor)", max_depth=floor)


@pytest.fixture(scope="module")
def above_the_declared_ceiling(estate: tuple[str, str]) -> Asked:
    """One ask ABOVE the declared ceiling — the request that must be refused."""
    deployment = _load("deployment")
    over = deployment.declared_depth_ceiling() + 1
    return ask(
        asked_as=f"max_depth={over} (above the declared ceiling)", max_depth=over
    )


def redeclared_default(text: str, *, want: int) -> tuple[str, int]:
    """Rewrite `ccf_config.yaml`'s declared `max_depth` default, in TEXT.

    A text rewrite and never a parse-and-dump, because the config's COMMENTS are
    load-bearing:
    ``examples/cp-04-corporate-family-tree/deployment.py::refuse_stale_vocabulary_pointer``
    scans this document's comment BLOCKS for the sentence naming where the six
    predicate IRIs live, and a round-tripped YAML document would lose it and
    refuse the whole assembly for a reason that has nothing to do with the gate.

    Returns the rewritten text and how many lines it changed, so the caller can
    refuse a rewrite that hit nothing — a scratch copy identical to the original
    would make `CFT-G04`'s control a check that cannot fail.
    """
    rewritten: list[str] = []
    inside = False
    hits = 0
    for line in text.splitlines(keepends=True):
        if re.match(r"^\s{2}argument_defaults:\s*$", line):
            inside = True
            rewritten.append(line)
            continue
        if inside and re.match(r"^\s{4}max_depth:\s*\d+\s*$", line):
            rewritten.append(re.sub(r"(max_depth:\s*)\d+", rf"\g<1>{want}", line))
            hits += 1
            inside = False
            continue
        if inside and line.strip() and not line.startswith("    "):
            inside = False
        rewritten.append(line)
    return "".join(rewritten), hits


@pytest.fixture(scope="module")
def under_a_redeclared_default(
    estate: tuple[str, str], tmp_path_factory: pytest.TempPathFactory
) -> Asked:
    """The same absent-`max_depth` question, against a REDECLARED default.

    **This is `CFT-G04`'s positive control and not its sabotage.** The gate's
    content is that the default FOLLOWS the declaration, and the only way to
    show following rather than coincidence is to move the declaration and watch
    the walk move with it. The sabotage is a separate, later act on the
    product's own Python.

    The scratch copy changes exactly one line and nothing else, and the fixture
    refuses to proceed unless the reloaded declaration reports the new value —
    a scratch config that did not take effect would make the control silently
    vacuous.
    """
    deployment = _load("deployment")
    want = deployment.declared_depth_floor()
    text, hits = redeclared_default(
        deployment.CONFIG.read_text(encoding="utf-8"), want=want
    )
    assert hits == 1, (
        f"the scratch rewrite changed {hits} lines of ccf_config.yaml, not 1;"
        " CFT-G04's control cannot prove the default follows a declaration it"
        " did not actually move"
    )
    scratch = tmp_path_factory.mktemp("cp04-redeclared") / "ccf_config.yaml"
    scratch.write_text(text, encoding="utf-8")

    patch = pytest.MonkeyPatch()
    patch.setattr(deployment, "CONFIG", scratch)
    try:
        assert deployment.declared_depth_default() == want, (
            "the scratch ccf_config.yaml does not declare the rewritten default"
        )
        return ask(
            asked_as=f"max_depth absent (declared default redeclared as {want})",
            omit_max_depth=True,
        )
    finally:
        patch.undo()


# ---------------------------------------------------------------------------
# PRECONDITIONS — what a green gate below is allowed to mean.
# ---------------------------------------------------------------------------


def test_the_seed_carries_what_these_five_gates_need(
    at_the_declared_default: Asked, at_the_declared_floor: Asked
) -> None:
    """Without this, a green gate could be a true statement about nothing.

    Six things, each one a way a gate below could pass while measuring nothing:
    an empty node set, an empty edge set, an empty class vocabulary, an empty
    predicate roster, a predicate roster that is not a real selection, and a
    depth range whose floor, default and ceiling are not three distinct values.
    """
    deployment = _load("deployment")
    vocabulary = declared_class_vocabulary()
    predicates = declared_family_predicates()
    excluded = deliberately_excluded_predicates()

    assert at_the_declared_default.nodes, (
        "the ask at the declared default served no nodes at all, so every"
        " per-node gate below would be a true statement about the empty set"
    )
    assert at_the_declared_default.edges, (
        "the ask at the declared default served no edges at all, so CFT-G02"
        " would be satisfied vacuously"
    )
    assert vocabulary, "expected.yaml declares an empty class vocabulary"
    assert predicates, "expected.yaml declares an empty family-predicate roster"
    assert not (predicates & excluded), (
        "the declared six and the deliberately-excluded seven overlap on"
        f" {sorted(predicates & excluded)}, so the six are not a selection and"
        " CFT-G02's sabotage has no name to draw on"
    )
    assert excluded, (
        "expected.yaml declares no deliberately-excluded predicates, so nothing"
        " records that the six were chosen rather than exhaustive"
    )
    assert predicates == frozenset(deployment.declared_relationship_types()), (
        "expected.yaml and ccf_config.yaml disagree about which predicates this"
        f" product walks: expected {sorted(predicates)},"
        f" configured {sorted(deployment.declared_relationship_types())}"
    )

    floor = deployment.declared_depth_floor()
    default = deployment.declared_depth_default()
    ceiling = deployment.declared_depth_ceiling()
    assert floor < default < ceiling, (
        f"the declared depth range is floor={floor} default={default}"
        f" ceiling={ceiling}; CFT-G03, CFT-G04 and CFT-G05 each need three"
        " distinct values to be able to tell their subjects apart"
    )
    assert at_the_declared_floor.roster != at_the_declared_default.roster, (
        "the ask at the declared floor and the ask at the declared default"
        " served the SAME member roster, so CFT-G05's content limb could not"
        " distinguish a walk that reads max_depth from one that ignores it"
    )
    served_classes = {
        klass for node in at_the_declared_default.nodes for klass in node["type_chain"]
    }
    for iri in served_classes:
        assert local_name(iri), (
            f"no local name derives from the served class IRI {iri!r}"
        )


# ---------------------------------------------------------------------------
# CFT-G01 — every returned node carries a KNOWN FIBO class.
# ---------------------------------------------------------------------------


def class_violations(
    nodes: Sequence[Mapping[str, Any]], vocabulary: frozenset[str]
) -> list[str]:
    """Every way a served node set fails `CFT-G01`.

    Two independent failures and one vacuity guard, because the gate's statement
    has two halves — *untyped* and *off-ontology* — and a check that only
    asserted non-emptiness would accept any string at all, measuring presence
    rather than knowledge.
    """
    violations: list[str] = []
    if not nodes:
        return [
            "CFT-G01: no node was served, so the predicate holds over the empty"
            " set and proves nothing"
        ]
    for node in nodes:
        chain = tuple(str(entry) for entry in node["type_chain"])
        if not chain:
            violations.append(
                f"CFT-G01: node {node['uri']!r} was served UNTYPED — an empty"
                " type_chain. Section D.6 makes type_chain non-nullable and an"
                " untyped node admitted quietly is what this gate exists to"
                " catch"
            )
            continue
        unknown = sorted({local_name(entry) for entry in chain} - vocabulary)
        if unknown:
            violations.append(
                f"CFT-G01: node {node['uri']!r} carries class(es) {unknown},"
                f" which are outside the declared vocabulary {sorted(vocabulary)}"
            )
    return violations


def test_cft_g01_every_returned_node_carries_a_known_fibo_class(
    at_the_declared_default: Asked,
) -> None:
    """`CFT-G01` (criterion 25). Every returned node carries a KNOWN FIBO class.

    Asserted over the WHOLE returned node set and against MEMBERSHIP in the
    declared vocabulary — never against non-emptiness alone, which would accept
    any string and measure presence rather than knowledge.

    Sabotaged by admitting an untyped node into the returned set.
    """
    violations = class_violations(
        at_the_declared_default.nodes, declared_class_vocabulary()
    )
    assert not violations, (
        f"CFT-G01 failed against {at_the_declared_default.asked_as}:\n"
        + "\n".join(violations)
    )


def test_the_class_check_refuses_an_untyped_node() -> None:
    """**Positive control.** An untyped node is what the sabotage admits."""
    vocabulary = declared_class_vocabulary()
    served = [{"uri": "x://untyped", "type_chain": []}]
    violations = class_violations(served, vocabulary)
    assert violations, "an untyped node was reported as carrying a known class"
    assert any("UNTYPED" in entry for entry in violations), violations


def test_the_class_check_refuses_an_off_ontology_class() -> None:
    """**Positive control.** A check that accepts any string measures presence."""
    vocabulary = declared_class_vocabulary()
    served = [{"uri": "x://off", "type_chain": ["http://example.invalid/Anything"]}]
    violations = class_violations(served, vocabulary)
    assert violations, "an off-ontology class was reported as a known FIBO class"
    assert any("outside the declared vocabulary" in entry for entry in violations), (
        violations
    )


def test_the_class_check_refuses_an_empty_node_set() -> None:
    """**Vacuity control.** A predicate over nothing is not a gate."""
    violations = class_violations([], declared_class_vocabulary())
    assert violations, "an empty node set was reported as satisfying CFT-G01"
    assert any("proves nothing" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G02 — every returned edge is one of the six declared predicates.
# ---------------------------------------------------------------------------


def predicate_violations(
    edges: Sequence[Mapping[str, Any]], declared_six: frozenset[str]
) -> list[str]:
    """Every way a served edge set fails `CFT-G02`.

    A NON-EMPTY SUBSET, both halves asserted. Subset because the six are what
    the product is allowed to serve, and non-empty because a tree with no edges
    satisfies the subset half vacuously — and an edgeless family tree is a
    failure this suite should report rather than accept.

    **Equality is deliberately NOT asserted.** Measured against the committed
    fixture at the declared default, the served set is four of the six —
    `controls` and `hasDomesticUltimateParent` assert no edge inside this
    anchor's subtree — so an equality check would be red against a correct
    product.
    """
    if not edges:
        return [
            "CFT-G02: the tree carried no edges at all, so the subset property"
            " holds vacuously and a family tree with no relationships was"
            " served"
        ]
    served = {str(edge["predicate"]) for edge in edges}
    if not served:
        return ["CFT-G02: no edge carried a predicate at all"]
    intruders = sorted(served - declared_six)
    if intruders:
        return [
            f"CFT-G02: the served edge set carries {intruders}, which are not"
            f" among the six declared family predicates {sorted(declared_six)}"
        ]
    return []


def test_cft_g02_every_returned_edge_is_one_of_the_six_declared_predicates(
    at_the_declared_default: Asked,
) -> None:
    """`CFT-G02` (criterion 26). Every returned edge is one of the six.

    A NON-EMPTY SUBSET of the six declared family predicates, so an edgeless
    tree cannot satisfy the gate by carrying nothing.

    Sabotaged by admitting a seventh predicate into the edge set.
    """
    violations = predicate_violations(
        at_the_declared_default.edges, declared_family_predicates()
    )
    assert not violations, (
        f"CFT-G02 failed against {at_the_declared_default.asked_as}:\n"
        + "\n".join(violations)
    )


def test_the_predicate_check_refuses_a_seventh_predicate() -> None:
    """**Positive control**, on a name drawn from the declared excluded roster.

    The seventh is not invented: `expected.yaml` records seven relationship
    predicates this estate carries and this product deliberately excludes, and
    the control draws its name from that roster so the refusal is about a real
    exclusion rather than about a token nobody would ever see.
    """
    seventh = sorted(deliberately_excluded_predicates())[0]
    served = [
        {
            "parent": "a",
            "child": "b",
            "predicate": sorted(declared_family_predicates())[0],
        },
        {"parent": "a", "child": "c", "predicate": seventh},
    ]
    violations = predicate_violations(served, declared_family_predicates())
    assert violations, f"a seventh predicate {seventh!r} was reported as declared"
    assert any(seventh in entry for entry in violations), violations


def test_the_predicate_check_refuses_an_edgeless_tree() -> None:
    """**Vacuity control.** An empty subset is a subset."""
    violations = predicate_violations([], declared_family_predicates())
    assert violations, "an edgeless tree was reported as satisfying CFT-G02"
    assert any("vacuously" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G03 — above the declared ceiling is REFUSED BY NAME, never clamped.
# ---------------------------------------------------------------------------


def refusal_violations(
    asked: Asked, *, requested: int, ceiling: int, floor: int
) -> list[str]:
    """Every way an over-ceiling ask fails `CFT-G03`.

    **Both limbs, and the second is the one a count-based check cannot see.** A
    clamp raises nothing and returns a perfectly well-formed tree: the request
    says 7, the walk does 6, the payload looks fine and the content address
    greens. So the gate asserts that NO tree came back at all, and names the
    clamp explicitly when the tree it got was walked at the ceiling.
    """
    violations: list[str] = []
    if asked.payload is not None:
        violations.append(
            f"CFT-G03: max_depth={requested} was ANSWERED rather than refused —"
            f" a tree came back, walked at max_depth_applied="
            f"{asked.depth_applied!r} over {len(asked.nodes)} members"
        )
        if asked.depth_applied == ceiling:
            violations.append(
                f"CFT-G03: and the answer was CLAMPED to the declared ceiling"
                f" {ceiling}. A clamp is a different program rather than a"
                " nearby one: it answers a question nobody asked, with no error"
            )
        return violations
    if not asked.refusal:
        violations.append(
            f"CFT-G03: max_depth={requested} produced neither a tree nor a"
            " refusal, so nothing was observed at all"
        )
        return violations
    if str(ceiling) not in asked.refusal:
        violations.append(
            f"CFT-G03: the refusal does not name the declared ceiling"
            f" {ceiling} — {asked.refusal!r}. A refusal that does not name what"
            " it refused against cannot be told from a refusal for another"
            " reason"
        )
    if str(requested) not in asked.refusal:
        violations.append(
            f"CFT-G03: the refusal does not name the requested depth"
            f" {requested} — {asked.refusal!r}, so it is not demonstrably about"
            " this request"
        )
    if str(floor) not in asked.refusal:
        violations.append(
            f"CFT-G03: the refusal does not name the declared floor {floor} —"
            f" {asked.refusal!r}; the bounds are a range and a refusal naming"
            " half of it names half of the contract"
        )
    return violations


def test_cft_g03_max_depth_above_the_ceiling_is_refused_by_name(
    above_the_declared_ceiling: Asked,
) -> None:
    """`CFT-G03` (criterion 27). Above the declared ceiling is REFUSED BY NAME.

    Two limbs held together: the refusal happened and it names the declared
    bounds, AND no tree was returned. The second limb is what distinguishes a
    refusal from a silent clamp — a check that only inspected the returned tree
    could not tell them apart, because a clamp returns a tree that looks right.

    Sabotaged by replacing the refusal with a silent clamp to the ceiling.
    """
    deployment = _load("deployment")
    ceiling = deployment.declared_depth_ceiling()
    violations = refusal_violations(
        above_the_declared_ceiling,
        requested=ceiling + 1,
        ceiling=ceiling,
        floor=deployment.declared_depth_floor(),
    )
    assert not violations, (
        f"CFT-G03 failed against {above_the_declared_ceiling.asked_as}:\n"
        + "\n".join(violations)
    )


def test_the_refusal_check_refuses_a_silent_clamp() -> None:
    """**Positive control.** A clamp is the sabotage, and it returns a tree."""
    clamped = Asked(
        asked_as="a clamped answer",
        payload={
            "nodes": [{"uri": "x://a", "type_chain": []}],
            "edges": [],
            "max_depth_applied": 6,
        },
        content_address="deadbeef",
        refusal=None,
    )
    violations = refusal_violations(clamped, requested=7, ceiling=6, floor=1)
    assert violations, "a clamped answer was reported as a refusal"
    assert any("CLAMPED" in entry for entry in violations), violations


def test_the_refusal_check_refuses_a_refusal_that_names_nothing() -> None:
    """**Positive control.** *It raised* is not *it refused by name*."""
    vague = Asked(
        asked_as="a refusal naming nothing",
        payload=None,
        content_address=None,
        refusal="AssemblyRefused: something went wrong",
    )
    violations = refusal_violations(vague, requested=7, ceiling=6, floor=1)
    assert violations, "a refusal naming neither bound was accepted as by-name"
    assert any("does not name the declared ceiling" in entry for entry in violations), (
        violations
    )


# ---------------------------------------------------------------------------
# CFT-G04 — a missing max_depth takes the DECLARED default.
# ---------------------------------------------------------------------------


def default_violations(
    *,
    absent: Asked,
    redeclared: Asked,
    declared_default: int,
    scratch_default: int,
) -> list[str]:
    """Every way the declared-default behavior fails `CFT-G04`.

    **The gate is that the default FOLLOWS the declaration, not that it equals
    3.** A check asserting only the number would pass against a serve-time
    literal that happens to be the declared value, which is precisely the
    sabotage. So the artifact's declared default is moved in a scratch copy and
    the walk is required to move with it — in the ECHO and in the served ROSTER
    both, because an echo that follows a declaration the walk ignores is a
    product that reports a depth it did not walk.
    """
    violations: list[str] = []
    if declared_default == scratch_default:
        return [
            "CFT-G04: the scratch declaration repeats the shipped default"
            f" {declared_default}, so the control cannot show following rather"
            " than coincidence"
        ]
    if absent.payload is None:
        return [f"CFT-G04: the absent-max_depth ask was refused — {absent.refusal!r}"]
    if redeclared.payload is None:
        return [
            "CFT-G04: the ask under the redeclared default was refused —"
            f" {redeclared.refusal!r}"
        ]
    if absent.depth_applied != declared_default:
        violations.append(
            f"CFT-G04: a missing max_depth walked at {absent.depth_applied!r}"
            f" where ccf_config.yaml declares the default {declared_default}"
        )
    if redeclared.depth_applied != scratch_default:
        violations.append(
            f"CFT-G04: with the declared default moved to {scratch_default}, a"
            f" missing max_depth still walked at {redeclared.depth_applied!r}."
            " The default did not FOLLOW the declaration, which is what a"
            " serve-time default looks like"
        )
    if absent.roster == redeclared.roster:
        violations.append(
            "CFT-G04: moving the declared default served the IDENTICAL member"
            f" roster ({len(absent.roster)} members). The declaration reached"
            " the echo but not the walk, so the reported depth is a label"
            " rather than the depth the product walked"
        )
    return violations


def test_cft_g04_a_missing_max_depth_takes_the_declared_default(
    at_the_declared_default: Asked, under_a_redeclared_default: Asked
) -> None:
    """`CFT-G04` (criterion 28). A missing `max_depth` takes the DECLARED default.

    Proven by MOVING the declaration in a scratch copy of `ccf_config.yaml` and
    requiring the walk to follow it — in what the payload reports and in which
    members it served. Asserting the number alone would pass against a
    serve-time literal that happens to equal the declared value, which is this
    gate's declared sabotage.
    """
    deployment = _load("deployment")
    violations = default_violations(
        absent=at_the_declared_default,
        redeclared=under_a_redeclared_default,
        declared_default=deployment.declared_depth_default(),
        scratch_default=deployment.declared_depth_floor(),
    )
    assert not violations, "CFT-G04 failed:\n" + "\n".join(violations)


def test_the_default_check_refuses_a_serve_time_default() -> None:
    """**Positive control.** A default that ignores a moved declaration."""
    shipped = Asked(
        asked_as="absent, shipped declaration",
        payload={"nodes": [{"uri": "x://a"}, {"uri": "x://b"}], "edges": [],
                 "max_depth_applied": 3},
        content_address="a", refusal=None,
    )
    unmoved = Asked(
        asked_as="absent, moved declaration",
        payload={"nodes": [{"uri": "x://a"}, {"uri": "x://b"}], "edges": [],
                 "max_depth_applied": 3},
        content_address="a", refusal=None,
    )
    violations = default_violations(
        absent=shipped, redeclared=unmoved, declared_default=3, scratch_default=1
    )
    assert violations, "a serve-time default was reported as following the declaration"
    assert any("did not FOLLOW the declaration" in entry for entry in violations), (
        violations
    )


def test_the_default_check_refuses_an_echo_the_walk_did_not_follow() -> None:
    """**Positive control.** A reported depth the served roster does not support."""
    shipped = Asked(
        asked_as="absent, shipped declaration",
        payload={"nodes": [{"uri": "x://a"}, {"uri": "x://b"}], "edges": [],
                 "max_depth_applied": 3},
        content_address="a", refusal=None,
    )
    echoed = Asked(
        asked_as="absent, moved declaration, echo only",
        payload={"nodes": [{"uri": "x://a"}, {"uri": "x://b"}], "edges": [],
                 "max_depth_applied": 1},
        content_address="b", refusal=None,
    )
    violations = default_violations(
        absent=shipped, redeclared=echoed, declared_default=3, scratch_default=1
    )
    assert violations, "an echo the walk ignored was reported as following"
    assert any("IDENTICAL member roster" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G05 — depth is part of product identity.
# ---------------------------------------------------------------------------


def identity_violations(*, shallow: Asked, deep: Asked, repeat: Asked) -> list[str]:
    """Every way depth fails to be part of product identity — `CFT-G05`.

    **Three limbs, and the ROSTER limb is the only one that measures content.**
    Measured against the shipped product: with
    ``examples/cp-04-corporate-family-tree/deployment.py::traversal_parameters``
    stripped of its depth substitution, the walk runs at the declared ceiling
    for every request — and the two
    content addresses STILL DIFFER, because ``max_depth_applied`` is echoed into
    the payload and the payload is what is sealed. An address-only gate passes
    that sabotage. The roster limb does not.

    The third limb — the same depth twice sealing to the SAME address — is what
    stops the gate being satisfied by an address that varies with anything at
    all, a clock or a scratch path included.
    """
    violations: list[str] = []
    for asked in (shallow, deep, repeat):
        if asked.payload is None:
            return [f"CFT-G05: `{asked.asked_as}` was refused — {asked.refusal!r}"]
        if not asked.content_address:
            return [f"CFT-G05: `{asked.asked_as}` carries no content address"]
        if not asked.roster:
            return [f"CFT-G05: `{asked.asked_as}` served no members"]
    if shallow.content_address == deep.content_address:
        violations.append(
            f"CFT-G05: `{shallow.asked_as}` and `{deep.asked_as}` sealed to the"
            f" SAME content address {shallow.content_address} — two depths are"
            " two different answers and must be two products"
        )
    if shallow.roster == deep.roster:
        violations.append(
            f"CFT-G05: `{shallow.asked_as}` and `{deep.asked_as}` served the"
            f" IDENTICAL member roster ({len(deep.roster)} members), so"
            " max_depth reached the payload's label but not the walk. The"
            " addresses can still differ on the echoed parameter alone, which"
            " is why this limb exists"
        )
    if deep.content_address != repeat.content_address:
        violations.append(
            f"CFT-G05: the same question asked twice sealed to two addresses —"
            f" {deep.content_address} and {repeat.content_address}. An address"
            " that varies with anything cannot say what depth changed"
        )
    if deep.roster != repeat.roster:
        violations.append(
            "CFT-G05: the same question asked twice served two different member"
            " rosters, so nothing about the walk is reproducible"
        )
    return violations


def test_cft_g05_depth_is_part_of_product_identity(
    at_the_declared_floor: Asked,
    at_the_declared_default: Asked,
    at_the_declared_default_again: Asked,
) -> None:
    """`CFT-G05` (criterion 29). Depth is part of product identity.

    Two depths are two content addresses AND two member rosters; one depth twice
    is one address and one roster. The roster limbs are what make the gate read
    content rather than the echoed parameter.

    Sabotaged by making `max_depth` not change the content address.
    """
    violations = identity_violations(
        shallow=at_the_declared_floor,
        deep=at_the_declared_default,
        repeat=at_the_declared_default_again,
    )
    assert not violations, "CFT-G05 failed:\n" + "\n".join(violations)


def test_the_identity_check_refuses_an_address_that_never_moves() -> None:
    """**Positive control.** One address for two depths is one product."""
    one = Asked(
        asked_as="depth 1", content_address="same", refusal=None,
        payload={"nodes": [{"uri": "x://a"}], "edges": [], "max_depth_applied": 1},
    )
    three = Asked(
        asked_as="depth 3", content_address="same", refusal=None,
        payload={"nodes": [{"uri": "x://a"}, {"uri": "x://b"}], "edges": [],
                 "max_depth_applied": 3},
    )
    violations = identity_violations(shallow=one, deep=three, repeat=three)
    assert violations, "two depths sharing one address were reported as two products"
    assert any("SAME content address" in entry for entry in violations), violations


def test_the_identity_check_refuses_a_roster_that_never_moves() -> None:
    """**Positive control**, and the one that mirrors the shipped sabotage.

    Two different addresses over an IDENTICAL roster is exactly what the
    declared sabotage produces: the walk stops reading `max_depth` while the
    payload keeps echoing it, so the seal still moves and the family does not.
    """
    roster = [{"uri": "x://a"}, {"uri": "x://b"}]
    one = Asked(
        asked_as="depth 1", content_address="aaa", refusal=None,
        payload={"nodes": roster, "edges": [], "max_depth_applied": 1},
    )
    three = Asked(
        asked_as="depth 3", content_address="bbb", refusal=None,
        payload={"nodes": roster, "edges": [], "max_depth_applied": 3},
    )
    violations = identity_violations(shallow=one, deep=three, repeat=three)
    assert violations, "an unmoved roster was reported as two different products"
    assert any("IDENTICAL member roster" in entry for entry in violations), violations


def test_the_identity_check_refuses_an_address_that_never_repeats() -> None:
    """**Vacuity control.** An address varying with everything says nothing."""
    one = Asked(
        asked_as="depth 1", content_address="aaa", refusal=None,
        payload={"nodes": [{"uri": "x://a"}], "edges": [], "max_depth_applied": 1},
    )
    three = Asked(
        asked_as="depth 3", content_address="bbb", refusal=None,
        payload={"nodes": [{"uri": "x://a"}, {"uri": "x://b"}], "edges": [],
                 "max_depth_applied": 3},
    )
    again = Asked(
        asked_as="depth 3 repeated", content_address="ccc", refusal=None,
        payload={"nodes": [{"uri": "x://a"}, {"uri": "x://b"}], "edges": [],
                 "max_depth_applied": 3},
    )
    violations = identity_violations(shallow=one, deep=three, repeat=again)
    assert violations, "an address that never repeats was accepted as identity"
    assert any("sealed to two addresses" in entry for entry in violations), violations
