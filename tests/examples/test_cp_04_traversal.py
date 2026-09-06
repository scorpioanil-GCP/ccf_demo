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
import json
import pathlib
import re
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Final, Iterator, Mapping, Sequence

import pytest
import yaml

from ccf.agents.errors import AssemblyRefused
from ccf.halflife.assessment import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.constraints import ConstraintRefusal
from ccf.products.refusal import REFUSAL_KINDS

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


def declared_debt_by_depth() -> Mapping[str, Mapping[str, Any]]:
    """`declaration.debt_by_depth` — the two `D_c` pins, from the artifact.

    **READ FROM THE DOCUMENT AND NEVER AUTHORED HERE**, and on this limb that
    discipline is load-bearing rather than habitual: the sabotage this limb
    exists to catch is an edit to
    ``examples/cp-04-corporate-family-tree/produce.py::_agreement``, and a pin
    living in this module would sit in a file the same author edits in the same
    breath. Two files, and the pin's file is not the mutated one.

    The metadata key every declared block carries is stripped by the same
    convention :data:`CENSUS_METADATA_KEYS` names, and its presence is asserted
    rather than assumed — a document that stopped carrying it would otherwise
    contribute ``criterion`` to the roster of depths.
    """
    block = dict(declared()["debt_by_depth"])
    if "criterion" not in block:
        raise AssertionError(
            "`debt_by_depth` carries no `criterion` key, so the declared depths"
            " cannot be separated from the block's metadata by this document's"
            " own convention"
        )
    return {
        str(name): dict(values)
        for name, values in block.items()
        if name not in CENSUS_METADATA_KEYS
    }


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


#: A SHALLOWER question than the declared default, chosen by the CALLER.
#:
#: It is written here rather than read from a declaration because since
#: `24.6-L-01` there is nothing to read: `D-IMPL-253` Q21 deleted the request
#: contract's depth bounds, and what depth a caller asks for is the caller's.
#: One hop is the shallowest walk that is still a walk, and it is far enough
#: from the declared default of 3 that the two served ROSTERS differ rather
#: than only the two echoes — which is what `CFT-G05`'s content limb needs.
SHALLOW_DEPTH: Final[int] = 1

#: A depth DEEPER THAN ANY TREE IN THIS ESTATE, and therefore the request
#: `D-IMPL-251` C5 is about: under the deleted bound of 6 it was refused for
#: exhibiting nothing; it is SERVED now, with `depth_reached` reporting what
#: the walk actually found. Measured: the deepest tree in this estate is 6
#: (seven roots attain it), and the demonstration anchor's component is
#: exhausted at 3.
UNEXHIBITED_DEPTH: Final[int] = 8

#: The SDK's own kind token, read from the vocabulary rather than spelled
#: twice: a test that typed the string would agree with itself about the
#: vocabulary while disagreeing with the fabric.
CONSTRAINT_REFUSAL_KIND: Final[str] = REFUSAL_KINDS[ConstraintRefusal]

#: The two provenance words `ProvenanceSource` and `ParameterBound` declare as
#: `Literal`s. They are spelled here because a `Literal`'s members are not
#: enumerable as values without reaching into `typing`, and each is asserted
#: against the shipped annotation by
#: :func:`test_the_provenance_vocabulary_this_module_spells_is_the_shipped_one`
#: — so a rename is a red build here rather than a check that stops matching.
CAPABILITY_SOURCE_KIND: Final[str] = "capability"
TECHNICAL_AUTHORITY: Final[str] = "technical"

#: The parameter and finding type this module reads, both from the deployment
#: that declares them. Loaded lazily inside the functions that need them,
#: because importing the example at module scope needs its environment.


def traversal_finding(asked: "Asked") -> Mapping[str, Any]:
    """The `D-23` row of one served payload's finding roster.

    Read out of the payload the consumer received, never recomputed: the whole
    point of putting depth and cost in the findings is that they are part of
    the answer rather than something a reader has to reconstruct.
    """
    assert asked.payload is not None, f"{asked.asked_as} served no payload"
    rows = [
        dict(row)
        for row in asked.payload["findings"]
        if row["type"] == _load("projection").FINDING_TRAVERSAL
    ]
    assert len(rows) == 1, (
        f"{asked.asked_as} carries {len(rows)} traversal findings, not 1 —"
        f" the roster is {[row['type'] for row in asked.payload['findings']]}"
    )
    return rows[0]


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

    #: The measured `D_c` this ask served, off
    #: ``ccf.client.result.Result.debt`` — the same seam a consuming agent
    #: reads it through, never recomputed here.
    #:
    #: Sentinel-defaulted to ``None`` so the hand-built ``Asked`` values the
    #: positive controls below construct stay constructible. A control asserting
    #: a limb FIRES has no business supplying a real debt, and a required field
    #: would force each of them to author one — which is the shape that makes a
    #: control agree with the thing it is controlling.
    debt: DebtAssessment | None = None

    #: The refusal ENVELOPE itself, when one came back. Carried beside the text
    #: because `24.6-L-01` made the refusal a typed governed determination: the
    #: bound that refused, its AUTHORITY and the capability identity behind it
    #: are typed members, and a check reading only the rendered string would be
    #: asserting a sentence rather than a decision.
    #:
    #: Sentinel-defaulted for the same reason `debt` is: the hand-built values
    #: the positive controls construct have no envelope to supply, and a
    #: required field would force each control to author one.
    envelope: Any | None = None

    #: The INTERNAL determination the refusal's replay record holds — the
    #: `assembly_refusal` of the record the shell's `replay_reference` names,
    #: read out of the same file store `produce.py::_serve` writes, before the
    #: scratch root is torn down. `D-IMPL-260` P-F: below `full` the shell's
    #: bound crosses without its `source`, so WHICH substrate refused is read
    #: here rather than off the wire. ``None`` when nothing was refused, the
    #: reference did not resolve, or a positive control built the value by hand.
    recorded: Any | None = None

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


def _recorded_determination(root: pathlib.Path, shell: Any) -> Mapping[str, Any] | None:
    """The internal determination behind one shell, out of the door's own store.

    By the `replay_reference` the shell carries — never a directory walk — from
    the `FileArtifactStore` under ``root / ARTIFACT_STORE_DIRNAME``, which is
    the store `produce.py::_serve` writes. ``None`` rather than a raise when
    the reference is the sentinel or does not resolve: the gate reading it
    reports *no record* as its own finding.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.artifacts.protocol import parse_artifact_uri
    from ccf.products.refusal import NO_REPLAY_REFERENCE

    reference = str(getattr(shell, "replay_reference", "") or "")
    if not reference or reference == NO_REPLAY_REFERENCE:
        return None
    deployment = _load("deployment")
    store = FileArtifactStore(root=root / deployment.ARTIFACT_STORE_DIRNAME)
    try:
        name = parse_artifact_uri(reference)
        record = json.loads(store.get(content_address=name.artifact_version).decode("utf-8"))
        internal = record["content_generation_path"]["assembly_refusal"]
    except Exception:  # noqa: BLE001 — an unresolvable reference is the gate's finding
        return None
    return dict(json.loads(internal)) if isinstance(internal, str) else dict(internal)


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

    Every governed determination this rung reaches arrives on the `Result` as
    a typed envelope (`24.6-L-01`, `24.6-L-02`). A raised
    ``ccf.agents.errors::AssemblyRefused`` is still caught and rendered as
    text, and its meaning is now narrow: an INVARIANT FAILURE inside the
    deployment, never a verdict about the question. Catching it here keeps one
    broken assembly from taking the module down with it, so the gate that
    failed reports rather than erroring.
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
                refusal=str(result.refusal), envelope=result.refusal,
                recorded=_recorded_determination(pathlib.Path(scratch), result.refusal),
            )
    return Asked(
        asked_as=asked_as,
        payload=dict(result.payload),
        content_address=str(result.content_address),
        refusal=None,
        # OFF THE CLIENT RESULT, which is the seam a consuming agent reads
        # `D_c` through. Recomputing it here would be this module reimplementing
        # `examples/cp-04-corporate-family-tree/produce.py::measure_debt` and
        # then asserting the two agree.
        debt=result.debt,
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
def at_the_shallow_depth(estate: tuple[str, str]) -> Asked:
    """One ask at :data:`SHALLOW_DEPTH` — a second, shallower question.

    SUPERSEDED 2026-09-04 (`24.6-L-01`): this fixture asked at the DECLARED FLOOR, read from the request contract's `argument_bounds`.
    There is no declared floor any more — `D-IMPL-253` Q21 deleted the bound —
    and a caller's depth was never the declaration's to fix. The value is the
    caller's now, and it is named at :data:`SHALLOW_DEPTH` with its reason.
    """
    return ask(
        asked_as=f"max_depth={SHALLOW_DEPTH} (a shallower question)",
        max_depth=SHALLOW_DEPTH,
    )


@pytest.fixture(scope="module")
def above_the_technical_capability(estate: tuple[str, str]) -> Asked:
    """One ask ABOVE the substrate's own traversal capability.

    The request that must be refused BY NAME, and the ONE depth on this rung
    that still is. The number is read off the capability the deployment
    reports rather than written here, so a substrate with a different bound
    moves this fixture with it.
    """
    deployment = _load("deployment")
    over = deployment.traversal_depth_capability().max_traversal_depth + 1
    return ask(
        asked_as=f"max_depth={over} (above the technical capability)",
        max_depth=over,
    )


@pytest.fixture(scope="module")
def at_a_depth_the_estate_cannot_exhibit(estate: tuple[str, str]) -> Asked:
    """One ask at :data:`UNEXHIBITED_DEPTH` — SERVED, not refused.

    The whole content of `D-IMPL-251` C5 in one fixture. This depth is deeper
    than any tree in this estate, and under the deleted bound of 6 it was a
    refusal; the walk simply reaches what it reaches and the payload reports
    both numbers.
    """
    return ask(
        asked_as=f"max_depth={UNEXHIBITED_DEPTH} (deeper than this estate goes)",
        max_depth=UNEXHIBITED_DEPTH,
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
        if re.match(r"^\s{2}defaults:\s*$", line):
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
    want = SHALLOW_DEPTH
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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_the_seed_carries_what_these_five_gates_need(
    at_the_declared_default: Asked, at_the_shallow_depth: Asked
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

    default = deployment.declared_depth_default()
    capability = deployment.traversal_depth_capability().max_traversal_depth
    assert SHALLOW_DEPTH < default < UNEXHIBITED_DEPTH < capability, (
        f"the four depths these gates read are shallow={SHALLOW_DEPTH}"
        f" default={default} unexhibited={UNEXHIBITED_DEPTH}"
        f" capability={capability}, and they must be strictly increasing:"
        " CFT-G03 needs a depth ABOVE the capability that is not merely deep,"
        " the served-deep limb needs a depth deeper than this estate goes but"
        " still WITHIN the capability, and CFT-G04 and CFT-G05 each need to"
        " tell the default apart from both"
    )
    assert at_the_shallow_depth.roster != at_the_declared_default.roster, (
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
# The vocabulary pointer, and what "carries the IRIs" means.
#
# NOT A GATE and no id is minted. `refuse_stale_vocabulary_pointer` runs on
# every assembly, so it is exercised in the COMPLIANT direction constantly and
# had never been watched refuse anything. The 2026-09-01 close panel found the
# reason it could not refuse the case it was written for.
# ---------------------------------------------------------------------------


def commented_out_vocabulary(text: str) -> tuple[str, int]:
    """Move every declared `iri:` VALUE into a comment, keeping the text.

    The document still MENTIONS all six — `grep` finds them, and so did the
    shipped `iri not in target.read_text()` — while carrying none of them as a
    value a machine can read. That is the compliant-and-violating-in-one-token
    shape this phase has now met nine times.

    Returns the rewritten text and how many lines moved, so a control cannot
    pass over a rewrite that hit nothing.
    """
    rewritten: list[str] = []
    hits = 0
    for line in text.splitlines(keepends=True):
        match = re.match(r"^(\s*)iri:\s*(https://\S+)\s*$", line)
        if match:
            indent, iri = match.groups()
            rewritten.append(f"{indent}iri: TBC   # was {iri}\n")
            hits += 1
            continue
        rewritten.append(line)
    return "".join(rewritten), hits


def test_the_vocabulary_pointer_refuses_a_document_that_only_mentions_the_iris(
    tmp_path: pathlib.Path,
) -> None:
    """**Positive control**, and the close panel's finding in its own shape.

    `ccf_config.yaml` points a reader at `source-vocabulary.yaml` for the six
    family predicate IRIs. The scratch copy MENTIONS all six in comments and
    declares none as a value. The shipped check read the file's raw text and
    accepted it; the check now parses the document and looks among its values.

    **ONLY `ARTIFACTS` IS MOVED, AND THAT IS THE POINT.** The IRIs are read from
    `SOURCE_VOCABULARY` — the document the INTERPRETER uses — while the document
    the CONFIG points a reader at is resolved under `ARTIFACTS`. Moving both
    would make the check compare the scratch document against itself and pass
    for a reason that has nothing to do with the finding; see
    `test_the_vocabulary_pointer_cannot_fail_over_its_own_source_document`,
    which asserts that self-comparison as the measured property it is.
    """
    deployment = _load("deployment")
    text, hits = commented_out_vocabulary(
        deployment.SOURCE_VOCABULARY.read_text(encoding="utf-8")
    )
    assert hits >= 6, (
        f"the scratch rewrite moved {hits} `iri:` values, fewer than the six"
        " family predicates; a control over a document it did not change is a"
        " control that cannot fail"
    )
    scratch_dir = tmp_path / "artifacts"
    scratch_dir.mkdir()
    scratch = scratch_dir / deployment.SOURCE_VOCABULARY.name
    scratch.write_text(text, encoding="utf-8")

    for iri in deployment.family_predicate_iris().values():
        assert iri in text, (
            "the scratch document does not even MENTION the six, so this control"
            " would refuse for the wrong reason"
        )

    patch = pytest.MonkeyPatch()
    patch.setattr(deployment, "ARTIFACTS", scratch_dir)
    try:
        with pytest.raises(SystemExit) as refused:
            deployment.refuse_stale_vocabulary_pointer()
    finally:
        patch.undo()
    assert "VALUES carry none of" in str(refused.value), refused.value
    assert "mention in a comment" in str(refused.value), refused.value


def test_the_vocabulary_pointer_cannot_fail_over_its_own_source_document(
    tmp_path: pathlib.Path,
) -> None:
    """**The measured limit of the check, asserted rather than described.**

    Found on 2026-09-01 while building the control above. The set of IRIs the
    check looks for is
    `examples/cp-04-corporate-family-tree/deployment.py::family_predicate_iris`,
    which reads `SOURCE_VOCABULARY` — so for THAT document the second condition
    compares a file against itself and cannot fail, whatever the values are.
    Its force is over any ADDITIONAL document `ccf_config.yaml` names, and the
    fourth condition is what stops the config naming only such a document.

    Asserted here, in the shape that demonstrates it: with the interpreter's
    document and the named document moved TOGETHER to a copy declaring `TBC`
    for every IRI, the check still passes.
    """
    deployment = _load("deployment")
    text, hits = commented_out_vocabulary(
        deployment.SOURCE_VOCABULARY.read_text(encoding="utf-8")
    )
    assert hits >= 6, hits
    scratch_dir = tmp_path / "artifacts"
    scratch_dir.mkdir()
    scratch = scratch_dir / deployment.SOURCE_VOCABULARY.name
    scratch.write_text(text, encoding="utf-8")

    patch = pytest.MonkeyPatch()
    patch.setattr(deployment, "ARTIFACTS", scratch_dir)
    patch.setattr(deployment, "SOURCE_VOCABULARY", scratch)
    try:
        named = deployment.refuse_stale_vocabulary_pointer()
        wanted = set(deployment.family_predicate_iris().values())
    finally:
        patch.undo()
    assert named == (scratch.name,), named
    assert wanted == {"TBC"}, (
        "the scratch document does not declare a single placeholder for every"
        f" predicate, so this is not the self-comparison case: {sorted(wanted)}"
    )


def test_the_vocabulary_pointer_accepts_the_shipped_document() -> None:
    """**Compliance control.** A stricter reading must not refuse the real tree."""
    deployment = _load("deployment")
    named = deployment.refuse_stale_vocabulary_pointer()
    assert deployment.SOURCE_VOCABULARY.name in named, named


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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
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
# CFT-G03 — above the substrate's TECHNICAL capability is REFUSED BY NAME.
#
# SUPERSEDED 2026-09-04 (`24.6-L-01`, `D-IMPL-251` C5): this heading read "above the declared ceiling is REFUSED BY NAME, never clamped".
# The bound it named was a measurement of how deep this estate goes and is
# deleted; what is refused now is a depth above the SUBSTRATE's own capability,
# with authority `technical`, and the promise not to answer a narrower question
# than the one asked survives whole.
# ---------------------------------------------------------------------------


def _bound(asked: Asked) -> Mapping[str, Any]:
    """The refusing bound off the envelope, as a mapping. Empty when absent."""
    if asked.envelope is None:
        return {}
    raw = dict(getattr(asked.envelope, "fields", {}) or {}).get("bound")
    if raw is None:
        return {}
    return dict(json.loads(raw)) if isinstance(raw, str) else dict(raw)


def _recorded_bound(asked: Asked) -> Mapping[str, Any]:
    """The refusing bound off the RECORD's internal determination. Empty when absent."""
    if not asked.recorded:
        return {}
    raw = dict(asked.recorded.get("fields") or {}).get("bound")
    if raw is None:
        return {}
    return dict(json.loads(raw)) if isinstance(raw, str) else dict(raw)


def refusal_violations(
    asked: Asked, *, requested: int, capability: int, identity: str
) -> list[str]:
    """Every way an over-capability ask fails `CFT-G03`.

    **Three limbs, and the second is the one a count-based check cannot see.**
    A clamp raises nothing and returns a perfectly well-formed tree: the
    request says 101, the walk does 100, the payload looks fine and the content
    address greens. So the gate asserts that NO tree came back at all, and
    names the clamp explicitly when the tree it got was walked at the
    capability.

    **The third limb is the one `24.6-L-01` adds.** A refusal is not enough:
    the fabric has to say WHICH AUTHORITY refused and on what evidence, because
    a policy bound and a substrate bound are different facts about a request
    and a consumer that cannot tell them apart cannot act on either. So the
    bound is read as a typed member — `authority`, `value` and the capability
    identity its `source` names — rather than out of a rendered sentence.
    """
    violations: list[str] = []
    if asked.payload is not None:
        violations.append(
            f"CFT-G03: max_depth={requested} was ANSWERED rather than refused —"
            f" a tree came back, walked at max_depth_applied="
            f"{asked.depth_applied!r} over {len(asked.nodes)} members"
        )
        if asked.depth_applied == capability:
            violations.append(
                f"CFT-G03: and the answer was CLAMPED to the technical"
                f" capability {capability}. A clamp is a different program"
                " rather than a nearby one: it answers a question nobody"
                " asked, with no error"
            )
        return violations
    if not asked.refusal:
        violations.append(
            f"CFT-G03: max_depth={requested} produced neither a tree nor a"
            " refusal, so nothing was observed at all"
        )
        return violations
    kind = getattr(asked.envelope, "kind", None)
    if kind != CONSTRAINT_REFUSAL_KIND:
        violations.append(
            f"CFT-G03: the refusal came back as {kind!r} rather than"
            f" {CONSTRAINT_REFUSAL_KIND!r}. A refusal in the wrong vocabulary"
            " reports the wrong reason, which is the flattening the closed"
            " envelope exists to prevent"
        )
    max_depth = _load("deployment").PARAM_MAX_DEPTH
    if getattr(asked.envelope, "key", None) != max_depth:
        violations.append(
            f"CFT-G03: the refusal names key"
            f" {getattr(asked.envelope, 'key', None)!r} rather than"
            f" {max_depth!r}, so it is not demonstrably about the depth"
        )
    bound = _bound(asked)
    if not bound:
        violations.append(
            "CFT-G03: the refusal carries NO bound at all, so a consumer"
            " learns that they were refused and not what the boundary was"
        )
        return violations
    if bound.get("authority") != TECHNICAL_AUTHORITY:
        violations.append(
            f"CFT-G03: the bound claims authority {bound.get('authority')!r}"
            f" rather than {TECHNICAL_AUTHORITY!r}. A substrate limit reported"
            " as policy would have the deployment answering for a decision it"
            " did not make"
        )
    if str(bound.get("value")) != str(capability):
        violations.append(
            f"CFT-G03: the bound's value is {bound.get('value')!r} where the"
            f" substrate reports {capability}; the refusal is held against a"
            " number nothing measured"
        )
    # WHICH substrate refused is read off the RECORD, not the wire. `D-IMPL-260`
    # P-F: below `full` the shell's bound crosses without its `source`, and
    # this deployment discloses at `minimal`; the internal determination the
    # replay record holds keeps it, and an examiner resolves it from there.
    if "source" in bound and getattr(asked.envelope, "disclosure", None) != "full":
        violations.append(
            "CFT-G03: the bound's `source` crossed the door below `full`;"
            " which substrate refused is fabric state (D-IMPL-260 P-F)"
        )
    recorded = _recorded_bound(asked)
    if not recorded:
        violations.append(
            "CFT-G03: the refusal's replay record carries no bound, so an"
            " examiner cannot resolve WHICH substrate refused"
        )
        return violations
    source = dict(recorded.get("source") or {})
    if source.get("identity") != identity:
        violations.append(
            f"CFT-G03: the recorded bound's source identity is"
            f" {source.get('identity')!r} rather than {identity!r}, so an"
            " examiner cannot resolve WHICH substrate refused"
        )
    if source.get("kind") != CAPABILITY_SOURCE_KIND:
        violations.append(
            f"CFT-G03: the recorded bound's source kind is {source.get('kind')!r}"
            f" rather than {CAPABILITY_SOURCE_KIND!r} — a capability minted as"
            " an artifact is the manufactured provenance D-IMPL-253"
            " amendment 2 (1) refuses"
        )
    return violations


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_cft_g03_max_depth_above_the_technical_ceiling_is_refused_by_name(
    above_the_technical_capability: Asked,
) -> None:
    """`CFT-G03` (criterion 27). Above the TECHNICAL capability is REFUSED BY NAME.

    Three limbs held together: the refusal happened as a `constraint-refusal`
    naming `max_depth`, it carries the bound that refused it with authority
    `technical` and the substrate identity behind it, AND no tree was returned.
    The last limb is what distinguishes a refusal from a silent clamp — a check
    that only inspected the returned tree could not tell them apart, because a
    clamp returns a tree that looks right.

    Sabotaged by replacing the refusal with a silent clamp to the capability.
    """
    deployment = _load("deployment")
    capability = deployment.traversal_depth_capability()
    violations = refusal_violations(
        above_the_technical_capability,
        requested=capability.max_traversal_depth + 1,
        capability=capability.max_traversal_depth,
        identity=capability.capability_identity,
    )
    assert not violations, (
        f"CFT-G03 failed against {above_the_technical_capability.asked_as}:\n"
        + "\n".join(violations)
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_a_depth_the_estate_cannot_exhibit_is_served(
    at_a_depth_the_estate_cannot_exhibit: Asked,
) -> None:
    """`D-IMPL-251` C5's other half, and the one that used to be a refusal.

    A depth deeper than any tree in this estate is an ORDINARY QUESTION with an
    ordinary answer. Under the deleted bound of 6 this request was refused for
    exhibiting nothing, which is a statement about the estate wearing the shape
    of a statement about the request. It is served now, and the two numbers
    that make it legible — what was asked and what was reached — travel in the
    payload rather than being left to be inferred from a member count.
    """
    asked = at_a_depth_the_estate_cannot_exhibit
    assert asked.payload is not None, (
        f"a depth of {UNEXHIBITED_DEPTH} was REFUSED — {asked.refusal!r}. That"
        " is the bound `D-IMPL-251` C5 deleted returning under another name"
    )
    assert asked.depth_applied == UNEXHIBITED_DEPTH, (
        f"the payload reports max_depth_applied={asked.depth_applied!r} for a"
        f" request at {UNEXHIBITED_DEPTH}; a served depth that does not echo"
        " the asked depth is a clamp with the error suppressed"
    )
    finding = traversal_finding(asked)
    assert finding["requested_depth"] == UNEXHIBITED_DEPTH, finding
    assert 0 < finding["depth_reached"] <= UNEXHIBITED_DEPTH, (
        f"depth_reached={finding['depth_reached']!r} is not a depth this walk"
        f" could have reached at {UNEXHIBITED_DEPTH}"
    )
    assert finding["depth_reached"] < UNEXHIBITED_DEPTH, (
        "the estate exhibited the full requested depth, so this ask is no"
        " longer the 'deeper than anything here' case it exists to be —"
        " raise UNEXHIBITED_DEPTH and re-measure"
    )
    assert asked.roster, "a served answer with no members proves nothing"


def test_the_refusal_check_refuses_a_silent_clamp() -> None:
    """**Positive control.** A clamp is the sabotage, and it returns a tree."""
    clamped = Asked(
        asked_as="a clamped answer",
        payload={
            "nodes": [{"uri": "x://a", "type_chain": []}],
            "edges": [],
            "max_depth_applied": 100,
        },
        content_address="deadbeef",
        refusal=None,
    )
    violations = refusal_violations(
        clamped, requested=101, capability=100, identity="fluree/x"
    )
    assert violations, "a clamped answer was reported as a refusal"
    assert any("CLAMPED" in entry for entry in violations), violations


def test_the_refusal_check_refuses_a_refusal_that_names_no_authority() -> None:
    """**Positive control.** *It refused* is not *this authority refused*.

    The shell below is well formed, carries the right kind and the right key,
    and states a bound — and claims the bound was POLICY's. A deployment
    reporting a substrate limit as a policy decision would have an examiner
    looking for a Control Plane artifact that never existed, so the check has
    to read the authority rather than the presence of a bound.
    """
    mislabeled = Asked(
        asked_as="a refusal claiming the wrong authority",
        payload=None,
        content_address=None,
        refusal="constraint-refusal",
        envelope=SimpleNamespace(
            kind="constraint-refusal",
            key="max_depth",
            disclosure="minimal",
            fields={
                "bound": json.dumps(
                    {"authority": "policy", "operator": "maximum", "value": "100"}
                )
            },
        ),
        recorded={
            "kind": "constraint-refusal",
            "fields": {
                "bound": json.dumps(
                    {
                        "authority": "policy",
                        "operator": "maximum",
                        "value": "100",
                        "source": {
                            "kind": "artifact",
                            "identity": "some-policy",
                            "version": "1.0.0",
                        },
                    }
                )
            },
        },
    )
    violations = refusal_violations(
        mislabeled, requested=101, capability=100, identity="fluree/x"
    )
    assert violations, "a policy-labelled substrate bound was accepted"
    assert any("claims authority" in entry for entry in violations), violations
    assert any("source kind" in entry for entry in violations), violations


def test_the_refusal_check_refuses_a_refusal_that_carries_no_bound() -> None:
    """**Positive control.** A refusal with no bound tells a consumer nothing."""
    bare = Asked(
        asked_as="a refusal naming no bound",
        payload=None,
        content_address=None,
        refusal="constraint-refusal",
        envelope=SimpleNamespace(
            kind="constraint-refusal", key="max_depth", fields={}
        ),
    )
    violations = refusal_violations(
        bare, requested=101, capability=100, identity="fluree/x"
    )
    assert violations, "a bound-less refusal was accepted as by-name"
    assert any("NO bound at all" in entry for entry in violations), violations


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


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
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
        scratch_default=SHALLOW_DEPTH,
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


def debt_movement_violations(
    *, asks: Mapping[str, Asked], pinned: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Every way `D_c` fails to be a function of the depth asked — `CFT-G05`.

    **THE LIMB THE 2026-09-01 CLOSE PANEL'S FINDING 1 BOUGHT.** Depth was
    already part of product identity by roster and by seal; it was NOT part of
    the measured debt, because
    ``examples/cp-04-corporate-family-tree/produce.py::_agreement`` took `S`
    over ``scenario.facts`` — the deployment's SOURCE READ, bounded by the
    declared ceiling — while its own docstring said *served*. So `D_c` read
    `0.0909` at depth 1, depth 2 and depth 3 alike. Dave: *"a scalar that cannot
    fail through the door… a wrong denominator."*

    **NO NEW GATE ID.** The roster stays sixteen. This is a third limb of
    `CFT-G05`, whose statement — *depth is part of product identity* — is
    exactly what it holds; the two limbs beside it read the seal and the served
    roster, and this one reads the measured debt. All three fail under the same
    id.

    **THE PINS ARE COMPARED EXACTLY, AND THEIR DISTINCTNESS IS ASSERTED RATHER
    THAN ASSUMED.** An equality-only reading is satisfiable by a frozen scalar
    if the document happens to carry one value twice — which is the defect
    wearing the check's own clothes. So the declared pair must differ in the
    DOCUMENT and the observed pair must differ in the RUN, and either collapse
    is a violation. This is the same trap `perspective_content_addresses`
    records for `CFT-G16`, met from the other side.

    Compared as ``Decimal`` over the declared STRING: the fabric computes a
    28-digit `Decimal`, and a YAML float would make the comparison either false
    or true-by-rounding.
    """
    violations: list[str] = []

    missing = sorted(set(pinned) - set(asks))
    unpinned = sorted(set(asks) - set(pinned))
    if missing or unpinned:
        return [
            "CFT-G05: the declared depth pins and the asks do not correspond —"
            f" pinned-with-no-ask {missing}, asked-with-no-pin {unpinned}. A"
            " pin nothing asks is a pin nothing can fail, and an ask no pin"
            " covers is a depth this limb is silent about"
        ]

    observed: dict[str, Decimal] = {}
    for name in sorted(pinned):
        asked = asks[name]
        expectation = pinned[name]
        if asked.payload is None or asked.debt is None:
            violations.append(
                f"CFT-G05: `{asked.asked_as}` served no measured debt —"
                f" {asked.refusal!r}. `D_c` cannot be held against a depth that"
                " produced no product"
            )
            continue
        if asked.depth_applied != expectation["max_depth_applied"]:
            violations.append(
                f"CFT-G05: `{asked.asked_as}` applied depth"
                f" {asked.depth_applied!r} where `debt_by_depth.{name}` pins"
                f" {expectation['max_depth_applied']!r}, so the pin and the ask"
                " are about two different questions and the debt comparison"
                " below would be meaningless"
            )
            continue
        debt = Decimal(str(asked.debt.debt))
        agreement = Decimal(str(asked.debt.factors.semantic_consistency))
        observed[name] = debt
        if debt != Decimal(expectation["context_debt"]):
            violations.append(
                f"CFT-G05: `{asked.asked_as}` served D_c {debt} where"
                f" `debt_by_depth.{name}.context_debt` declares"
                f" {expectation['context_debt']}. On this estate F and C are"
                " both 1, so S is the whole of the variation and S is taken"
                " over the members this payload SERVED — if the denominator"
                " moved back to the deployment's source read, this is where it"
                " shows"
            )
        if agreement != Decimal(expectation["semantic_consistency"]):
            violations.append(
                f"CFT-G05: `{asked.asked_as}` served S {agreement} where"
                f" `debt_by_depth.{name}.semantic_consistency` declares"
                f" {expectation['semantic_consistency']}. S and D_c are pinned"
                " separately so a change to the debt profile's weights is not"
                " read as a change to the denominator, or the reverse"
            )

    declared_values = {
        name: Decimal(values["context_debt"]) for name, values in pinned.items()
    }
    if len(set(declared_values.values())) < len(declared_values):
        violations.append(
            "CFT-G05: `debt_by_depth` declares the SAME D_c for two different"
            f" depths ({dict((k, str(v)) for k, v in declared_values.items())}),"
            " so the equality limbs above would be satisfied by exactly the"
            " frozen scalar this limb exists to refuse"
        )
    if len(observed) == len(pinned) and len(set(observed.values())) < len(observed):
        violations.append(
            "CFT-G05: two different depths served the SAME D_c"
            f" ({dict((k, str(v)) for k, v in observed.items())}). Depth reached"
            " the payload and not the measured debt — the wrong-denominator"
            " defect the 2026-09-01 close panel found, arriving again"
        )
    return violations


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_cft_g05_depth_is_part_of_product_identity(
    at_the_shallow_depth: Asked,
    at_the_declared_default: Asked,
    at_the_declared_default_again: Asked,
) -> None:
    """`CFT-G05` (criterion 29). Depth is part of product identity.

    Two depths are two content addresses AND two member rosters AND two measured
    debts; one depth twice is one address and one roster. The roster limb and
    the debt limb are what make the gate read content rather than the echoed
    parameter.

    Sabotaged by making `max_depth` not change the content address — and, for
    the debt limb added 2026-09-01, by restoring the source-read denominator in
    ``examples/cp-04-corporate-family-tree/produce.py::_agreement``.
    """
    violations = identity_violations(
        shallow=at_the_shallow_depth,
        deep=at_the_declared_default,
        repeat=at_the_declared_default_again,
    ) + debt_movement_violations(
        asks={
            "at_the_shallow_depth": at_the_shallow_depth,
            "at_the_declared_default": at_the_declared_default,
        },
        pinned=declared_debt_by_depth(),
    )
    assert not violations, "CFT-G05 failed:\n" + "\n".join(violations)


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_requested_depth_is_identity_even_where_it_changes_nothing_served(
    at_the_declared_default: Asked,
    at_a_depth_the_estate_cannot_exhibit: Asked,
) -> None:
    """`CFT-G05`, extended by `24.6-L-01` to the case that used to be a refusal.

    **THE SHARPEST FORM OF `D-09` THIS ESTATE CAN EXHIBIT.** Depth 3 and depth 8
    serve the SAME members — the anchor's component is exhausted at 3 — and they
    are still TWO PRODUCTS, because they answer two different questions and the
    requested depth is part of what was asked. A build that sealed them
    identically would be saying *you asked about 8 and I am giving you the
    answer to 3*, which is the clamp with the request thrown away instead of
    the answer.

    It is only assertable at all because depth 8 is served: under the deleted
    bound of 6 there was no second product to compare.
    """
    default = at_the_declared_default
    deep = at_a_depth_the_estate_cannot_exhibit
    assert default.payload is not None and deep.payload is not None, (
        f"one of the two asks was refused — {default.refusal!r} /"
        f" {deep.refusal!r}"
    )
    assert default.roster == deep.roster, (
        "the two asks served DIFFERENT rosters, so this test is no longer"
        " about the case it exists for (identical content, different"
        " question). Re-measure: the estate may have grown deeper"
    )
    assert default.content_address != deep.content_address, (
        f"depth {default.depth_applied!r} and depth {deep.depth_applied!r}"
        f" served the SAME content address {default.content_address!r} over an"
        " identical roster. Requested depth left the product's identity, so a"
        " consumer holding this seal cannot tell which question it answers"
    )
    assert (
        traversal_finding(default)["requested_depth"]
        != traversal_finding(deep)["requested_depth"]
    ), "the two payloads report the same requested depth"


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_cft_g19_findings_carry_depth_and_structural_cost_and_no_clock(
    at_the_declared_default: Asked,
) -> None:
    """`CFT-G19` (Phase 24.6 criterion 33, `D-23`). Depth and cost are in the FINDINGS, and neither is a duration.

    Four numbers — requested depth, depth reached, nodes visited, edges walked
    — each a structural count of a walk that already ran. **And the negative
    half is the one that matters for a content-addressed payload**: a wall
    clock in addressed content makes every run a different product, so the
    canonical bytes are greped for a duration token and for any RFC3339 instant
    outside the three fields that legitimately carry one.

    Sabotaged by putting an elapsed time in the cost block: the payload still
    looks informative and the seal stops reproducing.
    """
    from ccf.contracts.canonical import canonical_bytes

    asked = at_the_declared_default
    finding = traversal_finding(asked)
    for key in ("requested_depth", "depth_reached"):
        assert isinstance(finding[key], int), f"{key} is {finding[key]!r}"
    cost = dict(finding["cost"])
    assert sorted(cost) == ["edges_walked", "nodes_visited"], cost
    for key, value in cost.items():
        assert isinstance(value, int) and value > 0, f"{key} is {value!r}"
    assert cost["nodes_visited"] >= len(asked.roster), (
        f"the walk reports visiting {cost['nodes_visited']} nodes while"
        f" serving {len(asked.roster)}; the ingest is the superset of what is"
        " served, so a cost below the served count is not this walk's"
    )

    assert asked.payload is not None
    text = canonical_bytes(asked.payload).decode("utf-8")
    for token in ("elapsed", "duration", "seconds", "perf_counter", "took_ms"):
        assert token not in text.casefold(), (
            f"the addressed payload carries {token!r}. A wall-clock figure in"
            " content-addressed bytes makes every run a different product,"
            " which is what D-23 rules out by asking for STRUCTURAL cost"
        )
    instants = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", text)
    assert not instants, (
        f"the addressed payload carries the instant(s) {instants}; this"
        " product's payload names none, and the three fields that do carry"
        " instants — graph_snapshot_at, temporal_boundary, expires_at — are on"
        " the VESSEL rather than inside the payload"
    )


def test_the_missing_jurisdiction_raise_is_tied_to_the_declared_requirement(
    tmp_path: pathlib.Path,
) -> None:
    """`D-33`, site #25 — and what the ruling explicitly does NOT say.

    Dave, `D-IMPL-255` (5): *"Required jurisdiction missing from served data ->
    Invariant/configuration failure -> raise"* — and the criterion is tied to
    the DECLARED requirement, **never** to *"missing jurisdiction always
    raises"*. The two readings are indistinguishable from the raise alone, so
    both branches are asserted here:

    * with the SHIPPED declaration and a served set whose members carry no
      jurisdiction, the guard RAISES — a declared closed world held against an
      empty observation is the vacuous pass it exists to refuse;
    * with a scratch `artifacts/source-vocabulary.yaml` declaring an EMPTY
      served set, the SAME served data reaches ``SystemExit`` instead, on the
      guard ABOVE — the authoring error, whose subject is the document rather
      than the request, and which no request can trigger.

    So the raise is a consequence of a requirement this deployment DECLARED,
    and a deployment that declared none would never reach it. That is what
    makes *"missing jurisdiction always raises"* provably not what the code
    says.
    """
    deployment = _load("deployment")

    served_without_jurisdictions = {"x://a": None, "x://b": None}

    with pytest.raises(AssemblyRefused) as raised:
        deployment.refuse_open_jurisdiction_world(served_without_jurisdictions)
    assert "NONE carries a" in str(raised.value), str(raised.value)
    declared = list(deployment.declared_served_jurisdictions())
    assert declared, "the shipped document declares no served set at all"
    assert str(sorted(declared)) in str(raised.value), (
        "the refusal does not name the DECLARED set it was held against, so it"
        f" does not show the requirement it depends on — {raised.value}"
    )

    document = yaml.safe_load(
        deployment.SOURCE_VOCABULARY.read_text(encoding="utf-8")
    )
    block = document["declaration"][deployment.VOCAB_ENTITLEMENT]
    assert block[deployment.VOCAB_SERVED_JURISDICTIONS] == declared, (
        "the scratch rewrite is about to empty a key it did not find carrying"
        " the shipped values, so the control would prove nothing"
    )
    block[deployment.VOCAB_SERVED_JURISDICTIONS] = []
    scratch = tmp_path / "source-vocabulary.yaml"
    scratch.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    patch = pytest.MonkeyPatch()
    patch.setattr(deployment, "SOURCE_VOCABULARY", scratch)
    try:
        assert deployment.declared_served_jurisdictions() == (), (
            "the scratch document still declares a served set"
        )
        with pytest.raises(SystemExit) as exited:
            deployment.refuse_open_jurisdiction_world(served_without_jurisdictions)
        assert "EMPTY served" in str(exited.value), str(exited.value)
    finally:
        patch.undo()


def test_the_jurisdiction_determinations_are_returned_not_raised() -> None:
    """`D-33`'s other two rows at site #24 and #27 — both RETURN.

    An empty served set is *the walk resolved no member*, and a declared
    jurisdiction no member of THIS family serves is *this family exhibits fewer
    values than the estate declares*. Neither is a contradiction between
    authoritative inputs, so neither raises: each comes back as the observed
    tuple plus a finding that NAMES what it found. The roster rather than a
    count, on `D-13`'s discipline — a count could not say WHICH row was idle.
    """
    deployment = _load("deployment")
    declared = deployment.declared_served_jurisdictions()
    assert len(declared) >= 2, (
        "this control needs at least two declared values so one can be idle"
        " while another fires"
    )

    observed, findings = deployment.refuse_open_jurisdiction_world({})
    assert observed == ()
    assert [row.type for row in findings] == [
        deployment.FINDING_COMPUTED_EMPTY_WALK
    ], findings

    fires, idle = declared[0], declared[1]
    observed, findings = deployment.refuse_open_jurisdiction_world(
        {"x://a": fires, "x://b": None}
    )
    assert observed == (fires,)
    assert [row.type for row in findings] == [
        deployment.FINDING_IDLE_JURISDICTIONS
    ], findings
    assert findings[0].members == tuple(sorted(set(declared) - {fires})), (
        "the idle finding does not name the declared rows this family did not"
        f" exhibit — it carries {findings[0].members}"
    )
    assert idle in findings[0].members


def test_the_unminted_membership_split_follows_d_33() -> None:
    """`D-33` at sites #22 and #23 — one determination, one failure.

    An empty node set is an ANSWER (the walk reached nothing) and comes back as
    a computed-empty finding. A node the walk ADMITTED that this deployment's
    own minting step did not cover is a CONTRADICTION between two authoritative
    inputs, and raises. Both directions, because the raise alone cannot show
    that the other branch is not one.
    """
    deployment = _load("deployment")

    findings = deployment.refuse_unminted_membership({}, nodes=())
    assert [row.type for row in findings] == [
        deployment.FINDING_COMPUTED_EMPTY_WALK
    ], findings

    assert deployment.refuse_unminted_membership(
        {"x://a": "fam"}, nodes=("x://a",)
    ) == ()

    with pytest.raises(AssemblyRefused) as raised:
        deployment.refuse_unminted_membership({"x://a": "fam"}, nodes=("x://a", "x://b"))
    assert "carry no" in str(raised.value), str(raised.value)


def test_the_provenance_vocabulary_this_module_spells_is_the_shipped_one() -> None:
    """**Control.** The two spelled provenance words are the fabric's own.

    `CAPABILITY_SOURCE_KIND` and `TECHNICAL_AUTHORITY` are string literals in
    this module because their types are `Literal`s rather than enumerable
    values. A literal that stopped matching the shipped annotation would make
    `CFT-G03`'s authority limb pass against anything, so the annotations are
    read back and the two words asserted to be members.
    """
    import typing

    from ccf.products.provenance import ParameterBound, ProvenanceSource

    kinds = typing.get_args(ProvenanceSource.model_fields["kind"].annotation)
    assert CAPABILITY_SOURCE_KIND in kinds, (
        f"{CAPABILITY_SOURCE_KIND!r} is not one of ProvenanceSource's declared"
        f" kinds {kinds}"
    )
    authorities = typing.get_args(
        ParameterBound.model_fields["authority"].annotation
    )
    assert authorities, "ParameterBound.authority is not a Literal any more"
    assert TECHNICAL_AUTHORITY in authorities, (
        f"{TECHNICAL_AUTHORITY!r} is not one of {authorities}"
    )


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


# ---------------------------------------------------------------------------
# CFT-G05's debt limb — controls. Every one hands the SHIPPED check a subject
# it must refuse; none of them reimplements the check.
# ---------------------------------------------------------------------------


def _asked_with_debt(*, asked_as: str, depth: int, debt: str, agreement: str) -> Asked:
    """One hand-built ask carrying a measured debt, for the controls only.

    Built through the shipped :class:`~ccf.halflife.assessment.DebtAssessment`
    rather than a stand-in with the same attribute names, so a control cannot go
    on passing against a type the product stopped serving. `Decimal` from a
    string: the contract refuses a ``float`` at construction.
    """
    return Asked(
        asked_as=asked_as,
        payload={"nodes": [{"uri": "x://a"}], "edges": [], "max_depth_applied": depth},
        content_address=f"addr-{depth}",
        refusal=None,
        debt=DebtAssessment(
            debt=Decimal(debt),
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal(1),
                completeness=Decimal(1),
                semantic_consistency=Decimal(agreement),
            ),
        ),
    )


#: The two pins, as the shipped document carries them, for the controls to
#: perturb one at a time. Read from `expected.yaml` rather than authored, so a
#: control cannot drift into asserting against a shape the artifact abandoned.
def _control_pins() -> dict[str, dict[str, Any]]:
    return {name: dict(values) for name, values in declared_debt_by_depth().items()}


def test_the_debt_limb_refuses_a_scalar_that_never_moves() -> None:
    """**Positive control, and the one that mirrors the shipped defect.**

    Both depths serving the SAME `D_c` is precisely what
    ``examples/cp-04-corporate-family-tree/produce.py::_agreement`` produced
    while its denominator was ``scenario.facts``: the roster moved, the seal
    moved, and the debt did not.
    """
    pins = _control_pins()
    frozen = pins["at_the_declared_default"]["context_debt"]
    asks = {
        name: _asked_with_debt(
            asked_as=name,
            depth=int(values["max_depth_applied"]),
            debt=frozen,
            agreement=pins["at_the_declared_default"]["semantic_consistency"],
        )
        for name, values in pins.items()
    }
    violations = debt_movement_violations(asks=asks, pinned=pins)
    assert violations, "a D_c identical at two depths was accepted as movement"
    assert any("served the SAME D_c" in entry for entry in violations), violations


def test_the_debt_limb_refuses_a_document_that_pins_one_value_twice() -> None:
    """**Vacuity control.** Equality against a collapsed pin proves nothing.

    A document carrying one figure under both depths would make the equality
    limbs green for a product whose debt never moves — the defect wearing the
    check's own clothes. Perturbing the DOCUMENT rather than the run is the
    point: this is the half a run-only control cannot reach.
    """
    pins = _control_pins()
    collapsed = {
        name: dict(values, **{
            "context_debt": pins["at_the_declared_default"]["context_debt"],
            "semantic_consistency": (
                pins["at_the_declared_default"]["semantic_consistency"]
            ),
        })
        for name, values in pins.items()
    }
    asks = {
        name: _asked_with_debt(
            asked_as=name,
            depth=int(values["max_depth_applied"]),
            debt=str(values["context_debt"]),
            agreement=str(values["semantic_consistency"]),
        )
        for name, values in collapsed.items()
    }
    violations = debt_movement_violations(asks=asks, pinned=collapsed)
    assert violations, "a document pinning one D_c to two depths was accepted"
    assert any("declares the SAME D_c" in entry for entry in violations), violations


def test_the_debt_limb_refuses_a_value_off_its_pin() -> None:
    """**Positive control.** The equality itself fires, and names the depth."""
    pins = _control_pins()
    asks = {
        name: _asked_with_debt(
            asked_as=name,
            depth=int(values["max_depth_applied"]),
            debt=str(values["context_debt"]),
            agreement=str(values["semantic_consistency"]),
        )
        for name, values in pins.items()
    }
    moved = pins["at_the_shallow_depth"]
    asks["at_the_shallow_depth"] = _asked_with_debt(
        asked_as="at_the_shallow_depth",
        depth=int(moved["max_depth_applied"]),
        debt=str(Decimal(moved["context_debt"]) / 2),
        agreement=str(moved["semantic_consistency"]),
    )
    violations = debt_movement_violations(asks=asks, pinned=pins)
    assert violations, "a D_c off its declared pin was accepted"
    assert any("context_debt` declares" in entry for entry in violations), violations


def test_the_debt_limb_refuses_a_pin_held_against_the_wrong_depth() -> None:
    """**Positive control.** A pin and an ask about two different questions.

    Without this limb the two equalities could be satisfied by asking the SAME
    depth twice and comparing each answer to a different pin — which would make
    the whole check a statement about one question.
    """
    pins = _control_pins()
    depth = int(pins["at_the_declared_default"]["max_depth_applied"])
    asks = {
        name: _asked_with_debt(
            asked_as=name,
            depth=depth,
            debt=str(values["context_debt"]),
            agreement=str(values["semantic_consistency"]),
        )
        for name, values in pins.items()
    }
    violations = debt_movement_violations(asks=asks, pinned=pins)
    assert violations, "a pin held against the wrong depth was accepted"
    assert any("are about two different questions" in entry for entry in violations), (
        violations
    )


def test_the_debt_limb_refuses_a_pin_nothing_asks() -> None:
    """**Coverage control.** A declared depth with no ask is silence, not a pass."""
    pins = _control_pins()
    asks = {
        "at_the_declared_default": _asked_with_debt(
            asked_as="at_the_declared_default",
            depth=int(pins["at_the_declared_default"]["max_depth_applied"]),
            debt=str(pins["at_the_declared_default"]["context_debt"]),
            agreement=str(pins["at_the_declared_default"]["semantic_consistency"]),
        )
    }
    violations = debt_movement_violations(asks=asks, pinned=pins)
    assert violations, "a declared depth nothing asked was accepted as covered"
    assert any("do not correspond" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# WR-05 — the reporter renders the `NOT_EVALUABLE` depth sentinel, never crashes.
# ---------------------------------------------------------------------------


def _report_payload(deepest_depth: Any) -> dict[str, Any]:
    """A minimal served payload for `run.py::_report`, one node at ``deepest_depth``.

    The second node carries the depth field's `NOT_EVALUABLE` sentinel — a
    DECLARED member of that field's vocabulary (`projection.py::_node`,
    §C.4 trap 5) — so the reporter is fed exactly the value a payload is
    ALLOWED to emit.
    """
    return {
        "anchor": {
            "lei": "54930022CZO1N2UGVW07",
            "label": "Super Micro Computer, Inc.",
            "type_chain": ["https://www.omg.org/spec/Commons/Organizations/LegalEntity"],
        },
        "nodes": [
            {"depth": deepest_depth, "attributes": {"legal_jurisdiction": "US-DE"}},
            {"depth": _load("projection").NOT_EVALUABLE, "attributes": {}},
        ],
        "findings": [],
        "max_depth_applied": 3,
        "jurisdictions": ["US-DE"],
        "perspective_role": "credit-officer",
        "class_axis": "Corporation",
        "detailed_members": ["a", "b"],
    }


def _report_result(payload: Mapping[str, Any]) -> Any:
    """A stand-in `ccf.client.result.Result` for `_report` — it only READS."""
    from datetime import UTC, datetime
    from types import SimpleNamespace

    return SimpleNamespace(
        payload=payload,
        debt=None,
        lineage=SimpleNamespace(
            operators_invoked={"traversal.typed-neighborhood", "policy.principal-subgraph"},
            policy_bundle_versions={"pv-1"},
        ),
        expires_at=datetime(2026, 9, 1, tzinfo=UTC),
        content_address="sha256:demo",
        replay_ref="replay:demo",
    )


def test_report_renders_a_not_evaluable_depth_without_crashing() -> None:
    """**WR-05.** A payload carrying `NOT_EVALUABLE` in a depth field is reported.

    Dave: *"`_report` must not crash on `NOT_EVALUABLE`. Print the sentinel /
    skip the block. A finding the product is allowed to emit cannot take down
    the example."* Before the fix, `_report` did `int(node["depth"])` over every
    node and raised `ValueError` on the string sentinel AFTER the JSON already
    printed. Now the sentinel is skipped for the deepest-node figure and its
    count is surfaced instead.

    Sabotage: restoring `int(node["depth"])` over every node makes this raise
    `ValueError` — watched RED when the reporter was reverted.
    """
    from types import SimpleNamespace
    from datetime import UTC, datetime
    import io
    from contextlib import redirect_stdout

    run = _load("run")
    result = _report_result(_report_payload(deepest_depth=2))
    args = SimpleNamespace(max_depth=3)
    captured = io.StringIO()
    # Must not raise — the whole subject of WR-05.
    with redirect_stdout(captured):
        run._report(result, args=args, asked_at=datetime(2026, 9, 1, tzinfo=UTC))
    out = captured.getvalue()

    # The gap is made VISIBLE, not swallowed: the sentinel node is counted and
    # the deepest-node figure comes from the one integer depth (2), never a 0
    # coerced from the sentinel.
    assert "NOT_EVALUABLE" in out, out
    assert "1 node(s)" in out, out
    assert "deepest node       2 hop(s)" in out, out


def test_report_reads_the_deepest_integer_depth_not_the_sentinel() -> None:
    """**Control.** The deepest figure tracks the integer depths, and only those.

    A reporter that quietly read the sentinel as `0` would report a deepest node
    of `0` on a payload whose only integer depth is `5`. Fed exactly that, the
    figure must be `5` — proving the sentinel is excluded rather than coerced.
    """
    from types import SimpleNamespace
    from datetime import UTC, datetime
    import io
    from contextlib import redirect_stdout

    run = _load("run")
    result = _report_result(_report_payload(deepest_depth=5))
    args = SimpleNamespace(max_depth=6)
    captured = io.StringIO()
    with redirect_stdout(captured):
        run._report(result, args=args, asked_at=datetime(2026, 9, 1, tzinfo=UTC))
    out = captured.getvalue()
    assert "deepest node       5 hop(s)" in out, out


# ---------------------------------------------------------------------------
# The declared floor — `D-IMPL-259` (Dave, 2026-09-05), plan 24.6-14.
# ---------------------------------------------------------------------------
# *"cp-04 `max_depth` has a declared request-contract minimum of 1 … Requests
# below 1 … are governed request-validity refusals returned as data; values
# 1–100 are valid …"* The floor is the parameter's valid
# DOMAIN on the request contract (`ccf_config.yaml::request_contract.
# argument_domains`), held by the SDK's own `refuse_request` — not a policy
# constraint, not a capability, and not the deleted example-local bounds check.
# Two boundary controls, as ruled: `0` refuses, `1` serves.


def test_the_floor_is_the_sdks_verdict_over_the_declaration_and_needs_no_store() -> None:
    """The declaration says 1; the SDK refuses 0 and admits 1; nothing here reads a store.

    Sabotaged by deleting `argument_domains` from `ccf_config.yaml`: the
    contract then declares no domain and `0` is admitted — which is exactly
    the served one-node family measured on 2026-09-05 before the ruling.
    """
    from ccf.products.request import refuse_request

    deployment = _load("deployment")
    declared = deployment.request_contract()
    domain = declared.argument_domains.get(deployment.PARAM_MAX_DEPTH)
    assert domain is not None, "cp-04 declares no domain for max_depth (D-IMPL-259)"
    assert domain.minimum == 1
    assert domain.maximum is None, (
        "the maximum is the backend's technical capability, never a declared "
        "number (D-IMPL-253 Q21)"
    )
    below = refuse_request(
        request=deployment.demonstration_request(max_depth=0), declared=declared
    )
    assert below is not None
    assert below.reason == "below-minimum"
    assert below.key == deployment.PARAM_MAX_DEPTH
    assert (
        refuse_request(
            request=deployment.demonstration_request(max_depth=1), declared=declared
        )
        is None
    )


@pytest.fixture(scope="module")
def below_the_declared_floor(estate: tuple[str, str]) -> Asked:
    """One ask BELOW the declared floor — `max_depth=0`, the boundary's outside."""
    return ask(asked_as="max_depth=0 (below the declared floor)", max_depth=0)


@pytest.fixture(scope="module")
def at_the_declared_floor(estate: tuple[str, str]) -> Asked:
    """One ask AT the declared floor — `max_depth=1`, inclusive."""
    return ask(asked_as="max_depth=1 (at the declared floor)", max_depth=1)


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_below_the_declared_floor_is_refused_as_data_and_no_tree_is_returned(
    below_the_declared_floor: Asked,
) -> None:
    """`0` refuses — through the shipped caller, as a typed envelope, with no tree."""
    asked = below_the_declared_floor
    assert asked.payload is None, (
        f"{asked.asked_as} was SERVED — a one-node family came back, which is the"
        " pre-ruling behavior measured on 2026-09-05"
    )
    assert asked.envelope is not None, asked.refusal
    assert asked.envelope.kind == "product-request-violation", asked.envelope
    assert asked.envelope.reason == "below-minimum", asked.envelope
    assert asked.envelope.key == _load("deployment").PARAM_MAX_DEPTH


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_at_the_declared_floor_is_served(at_the_declared_floor: Asked) -> None:
    """`1` serves — inclusive, as *"values 1–100 are valid"* reads."""
    asked = at_the_declared_floor
    assert asked.payload is not None, f"{asked.asked_as} was REFUSED: {asked.refusal!r}"
    assert asked.depth_applied == 1
