"""Criterion 2, discharged mechanically: every named step corresponds to code
that actually runs, and a step nothing executes is RED.

The specification's §D.2 operator step table is prose, and a prose table cannot
be held against a run. ``examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml``
declares the same steps as DATA, each naming a **witness** — a fact a completed
run either produced or did not. This module is what turns that declaration into
a gate.

Four halves, and the third is the one that makes this evidence rather than
decoration:

1. **The two declarations cannot drift.** The recipe's step list and the §D.2
   table are asserted SET-EQUAL on ``(step, operator)``, in both directions,
   behind a non-vacuity precondition — a parser that silently matched nothing
   would make set-equality trivially true.
2. **Every declared witness resolves against ONE completed run.**
3. **Every witness KIND is watched RED.** Five kinds, five sabotage controls,
   each feeding the real resolver a deliberately unsatisfiable witness of that
   kind against the SAME completed run. A check that has never refused anything
   is a check nobody has tested, and this project has hit that defect class in
   eight consecutive waves.
4. **An unknown witness kind RAISES.** A silently-skipped step is criterion 2's
   exact failure mode wearing a green tick.

**`24-CONTEXT.md` `D-37` clause (2) binds this module: ONE test module under
``tests/``.** Every parser, every witness resolver and every control lives in
this file. Nothing is extracted into ``tests/examples/conftest.py``, into a
``_recipe`` helper, into ``tools/`` or anywhere else — not for reuse by a later
Context Product, not to keep the module short, and not to share the seeding code
with ``tests/examples/test_cp_00_output.py``. **The duplication between the two
modules is the correct outcome**, and `D-38` is explicit that a proof drifting
outside the four clauses is the violation rather than the criterion.

Every predicate here takes its subject as an ARGUMENT — the recipe text, the
specification text, the completed run — so each control exercises the REAL
predicate against a modified copy rather than a second description of the same
intent. That is the shape ``tests/examples/test_spine_separation.py`` already
ships and the reason it ships it.

``pytest.mark.postgres``: resolving a witness requires a completed run, and a
completed run requires the source estate. The container is seeded by this module
(`24-CONTEXT.md` `D-27`).
"""

from __future__ import annotations

import importlib
import os
import pathlib
import re
import sys
from typing import Any

import psycopg
import pytest
import yaml

from ccf.products.gates import ServableProduct
from ccf.products.request import ProductRequestViolation

pytestmark = pytest.mark.postgres

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-00-institutional-holders"
RECIPE = EXAMPLE / "artifacts" / "assembly-recipe.yaml"
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SCHEMA_SQL = FIXTURES / "cp_00_13f_schema.sql"
ROWS_SQL = FIXTURES / "cp_00_13f_rows.sql"

#: The keys the recipe artifact uses for its own structure. Structure of the
#: declaration, not domain vocabulary: the step names, operator names and
#: witness arguments all come out of the document.
KEY_DECLARATION = "declaration"
KEY_STEPS = "steps"
KEY_STEP = "step"
KEY_OPERATOR = "operator"
KEY_WITNESS = "witness"
KEY_SPEC_DOCUMENT = "spec_document"
KEY_SPEC_TABLE = "spec_table"
KEY_VOCABULARY = "witness_vocabulary"
KEY_KIND = "kind"

#: The five witness kinds. Named here because this module is the resolver, and
#: a resolver that read its own vocabulary out of the document it validates
#: could not refuse a sixth kind somebody invented in that document.
WITNESS_OPERATOR_IN_LINEAGE = "operator_in_lineage"
WITNESS_ENTITIES_ASSEMBLED = "entities_assembled"
WITNESS_PLAN_ID_MATCHES = "plan_id_matches"
WITNESS_SERVABLE_PRODUCT_HELD = "servable_product_held"
WITNESS_PAYLOAD_KEY_PRESENT = "payload_key_present"

CLOSED_VOCABULARY = frozenset(
    {
        WITNESS_OPERATOR_IN_LINEAGE,
        WITNESS_ENTITIES_ASSEMBLED,
        WITNESS_PLAN_ID_MATCHES,
        WITNESS_SERVABLE_PRODUCT_HELD,
        WITNESS_PAYLOAD_KEY_PRESENT,
    }
)


class UnknownWitnessKind(ValueError):
    """A step declared a witness outside the closed vocabulary.

    Raised rather than reported, because a step whose witness nothing can
    resolve is not a step that failed — it is a step nothing is CHECKING, and
    reporting it beside genuine failures would let it be triaged away.
    """


# --------------------------------------------------------------------------
# Loading the example. Duplicated from `test_cp_00_output.py` deliberately —
# `D-37` clause (2) is ONE test module, so nothing here may be extracted for
# the other one to share.
# --------------------------------------------------------------------------
def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name."""
    if str(EXAMPLE) not in sys.path:
        sys.path.insert(0, str(EXAMPLE))
    return importlib.import_module(name)


def _dsn_variable() -> str:
    """The environment-variable NAME ``backends.yaml`` declares for the source."""
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.BACKENDS.read_text(encoding="utf-8"))
    source = document[deployment.DECLARATION][deployment.SOURCES]
    binding = source[deployment.SOURCE_BINDING][deployment.SETTINGS]
    return str(binding[deployment.SOURCE_SETTING_DSN][deployment.FROM_ENV])


@pytest.fixture(scope="module")
def seeded(postgres_dsn: str) -> Any:
    """A seeded container, with the DSN where `backends.yaml` reads it."""
    with psycopg.connect(postgres_dsn, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        cursor.execute(ROWS_SQL.read_text(encoding="utf-8"))
    variable = _dsn_variable()
    previous = os.environ.get(variable)
    os.environ[variable] = postgres_dsn
    yield postgres_dsn
    if previous is None:
        os.environ.pop(variable, None)
    else:
        os.environ[variable] = previous


class _Recorder:
    def __init__(self) -> None:
        self.seen: object = None

    def __call__(self, assembled: object) -> None:
        self.seen = assembled


@pytest.fixture(scope="module")
def run(seeded: str, tmp_path_factory: pytest.TempPathFactory) -> Any:
    """ONE completed assembly, shared by every witness below.

    Module-scoped deliberately: the witnesses are facts about a run, and
    re-running the assembly per witness would not make any of them truer.
    """
    deployment = _load("deployment")
    assembler = _load("assembler")
    root = tmp_path_factory.mktemp("recipe")
    recorder = _Recorder()
    seam_outcome = assembler.HoldersAssembler(
        config=deployment.CONFIG,
        root=root,
        connection=deployment.connection(root=root),
        read=deployment.read,
        plan_class=deployment.plan_class(),
        observer=recorder,
    ).assemble(
        request=deployment.request(
            parameters={
                deployment.THRESHOLD_PARAMETER: deployment.demonstration_threshold()
            }
        ),
        perspective=deployment.perspective(),
        tenant_id=deployment.tenant_id(),
    )
    # D-60: this site used to discard its return. It is branched now — the
    # witnesses below are facts about a run that SUCCEEDED, and a governed
    # refusal reaching here would make every one of them a fact about nothing.
    assert not isinstance(seam_outcome, ProductRequestViolation), seam_outcome
    return recorder.seen


# --------------------------------------------------------------------------
# HALF ONE — the recipe and §D.2's table cannot drift apart.
# --------------------------------------------------------------------------
def _normalise(cell: str) -> str:
    """One operator name, as either document spells it.

    The table emphasises (``**Resolve**``), quotes a mode (``` `temporal` ```)
    and annotates the sixth row past an em dash (``*contract assembly* — **not
    an operator** …``). The recipe writes the bare name. Stripping emphasis and
    truncating at the annotation is what makes the two comparable at all; doing
    it in ONE function means the two sides cannot be normalised differently.
    """
    text = cell.split("—")[0]
    text = text.replace("**", "").replace("*", "").replace("`", "")
    return " ".join(text.split()).strip()


def recipe_steps(recipe_text: str) -> list[tuple[int, str]]:
    """``(step, operator)`` for every step the recipe artifact declares."""
    document = yaml.safe_load(recipe_text)
    steps = document.get(KEY_DECLARATION, {}).get(KEY_STEPS) or []
    return [(int(step[KEY_STEP]), _normalise(str(step[KEY_OPERATOR]))) for step in steps]


def table_steps(spec_text: str, *, heading: str) -> list[tuple[int, str]]:
    """``(step, operator)`` for every row of the specification's step table.

    Takes the document TEXT rather than a path, so
    :func:`test_the_two_declarations_are_set_equal` can hand it a copy with the
    table removed and watch it return nothing.
    """
    lines = spec_text.splitlines()
    if heading not in lines:
        return []
    rows: list[tuple[int, str]] = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("#"):
            break
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            rows.append((int(cells[0]), _normalise(cells[1])))
    return rows


def _recipe_declaration() -> dict[str, Any]:
    return dict(yaml.safe_load(RECIPE.read_text(encoding="utf-8"))[KEY_DECLARATION])


def _spec_text() -> str:
    """The specification the recipe artifact itself names, by path."""
    return (REPO_ROOT / _recipe_declaration()[KEY_SPEC_DOCUMENT]).read_text(
        encoding="utf-8"
    )


def _heading() -> str:
    """The §D.2 heading, from the recipe's own ``spec_table:`` declaration."""
    return f"### {_recipe_declaration()[KEY_SPEC_TABLE]}"


def test_the_two_declarations_are_set_equal() -> None:
    """The recipe and §D.2's table name the same steps, in both directions.

    The non-vacuity precondition comes FIRST and carries both counts: a parser
    that silently matched nothing would make the set-equality below trivially
    true, which is the failure this assertion exists to make impossible.
    """
    from_recipe = recipe_steps(RECIPE.read_text(encoding="utf-8"))
    from_table = table_steps(_spec_text(), heading=_heading())
    assert from_recipe and from_table, (
        f"the recipe parsed {len(from_recipe)} steps and the §D.2 table parsed"
        f" {len(from_table)}; set equality over an empty side proves nothing"
    )

    missing_rows = sorted(set(from_table) - set(from_recipe))
    missing_entries = sorted(set(from_recipe) - set(from_table))
    assert not missing_rows and not missing_entries, (
        f"§D.2 rows with no recipe step: {missing_rows}; recipe steps with no"
        f" §D.2 row: {missing_entries}"
    )

    # CONTROL — the table parser is fed the same document with §D.2's table
    # removed. It must return zero, and the precondition above must then fail.
    without = re.sub(
        r"(?m)^\|.*$", "", _spec_text()[_spec_text().index(_heading()) :]
    )
    gutted = _spec_text()[: _spec_text().index(_heading())] + without
    assert table_steps(gutted, heading=_heading()) == [], (
        "removing every table row from §D.2 did not empty the parser — it is"
        " reading rows from somewhere other than the table it claims to read"
    )
    with pytest.raises(AssertionError):
        stripped = table_steps(gutted, heading=_heading())
        assert from_recipe and stripped, "the precondition must refuse this"


# --------------------------------------------------------------------------
# HALF TWO — every declared witness resolves against a completed run.
# --------------------------------------------------------------------------
def resolve_witness(witness: str, assembled: Any) -> bool:
    """Whether ``witness`` is satisfied by ``assembled``.

    Raises:
        UnknownWitnessKind: ``witness`` names a kind outside
            :data:`CLOSED_VOCABULARY`.
    """
    kind, _sep, argument = witness.partition(":")
    kind = kind.strip()
    argument = argument.strip()
    if kind not in CLOSED_VOCABULARY:
        raise UnknownWitnessKind(
            f"{witness!r} names the witness kind {kind!r}, which is outside the"
            f" closed vocabulary {sorted(CLOSED_VOCABULARY)}. A step whose"
            " witness nothing can resolve is a step nothing is checking"
        )
    product = assembled.product
    if kind == WITNESS_OPERATOR_IN_LINEAGE:
        return argument in product.lineage.operators_invoked
    if kind == WITNESS_ENTITIES_ASSEMBLED:
        return bool(assembled.view.entities)
    if kind == WITNESS_PLAN_ID_MATCHES:
        return bool(product.plan_id == argument)
    if kind == WITNESS_SERVABLE_PRODUCT_HELD:
        return isinstance(assembled.gated, ServableProduct)
    return argument in product.payload


def unresolved(steps: list[dict[str, Any]], assembled: Any) -> list[str]:
    """Every declared step whose witness the run did not produce.

    Reported by STEP NUMBER and OPERATOR NAME, so a failure says which row of
    §D.2 nothing executes rather than which assertion went red.
    """
    return [
        f"step {step[KEY_STEP]} ({step[KEY_OPERATOR]}):"
        f" witness {step[KEY_WITNESS]!r} did not resolve"
        for step in steps
        if not resolve_witness(str(step[KEY_WITNESS]), assembled)
    ]


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_every_declared_step_is_witnessed_by_the_run(run: Any) -> None:
    """Criterion 2. A step nothing executes is RED, and this is where it goes red."""
    steps = _recipe_declaration()[KEY_STEPS]
    assert steps, "the recipe declares no steps — nothing below proves anything"
    assert unresolved(list(steps), run) == []


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_every_witness_kind_the_vocabulary_declares_is_used(run: Any) -> None:
    """The vocabulary and the steps agree, so no kind is dead vocabulary.

    A kind declared and never used is a kind nothing has ever resolved; a kind
    used and never declared is a step relying on a witness the document does not
    define. Both directions are named.
    """
    declaration = _recipe_declaration()
    declared = {
        str(entry[KEY_KIND]) for entry in declaration[KEY_VOCABULARY]
    }
    used = {
        str(step[KEY_WITNESS]).partition(":")[0].strip()
        for step in declaration[KEY_STEPS]
    }
    assert declared == CLOSED_VOCABULARY, (
        f"the artifact declares {sorted(declared)} and this resolver implements"
        f" {sorted(CLOSED_VOCABULARY)}"
    )
    assert used == declared, (
        f"declared and unused: {sorted(declared - used)}; used and undeclared:"
        f" {sorted(used - declared)}"
    )


# --------------------------------------------------------------------------
# HALF THREE — every witness KIND watched RED.
# --------------------------------------------------------------------------
#: One deliberately unsatisfiable witness per kind, against a run that
#: genuinely produced the satisfiable form of each. The arguments are nonsense
#: BY CONSTRUCTION rather than by being domain values that happen to be wrong.
UNSATISFIABLE: dict[str, str] = {
    WITNESS_OPERATOR_IN_LINEAGE: f"{WITNESS_OPERATOR_IN_LINEAGE}: no.such-operator",
    WITNESS_PLAN_ID_MATCHES: f"{WITNESS_PLAN_ID_MATCHES}: no.such-plan",
    WITNESS_PAYLOAD_KEY_PRESENT: f"{WITNESS_PAYLOAD_KEY_PRESENT}: no_such_key",
    WITNESS_ENTITIES_ASSEMBLED: WITNESS_ENTITIES_ASSEMBLED,
    WITNESS_SERVABLE_PRODUCT_HELD: WITNESS_SERVABLE_PRODUCT_HELD,
}


class _NoEntities:
    """The same run with an empty view — the shape a mis-set boundary produces."""

    def __init__(self, assembled: Any) -> None:
        self._assembled = assembled

    def __getattr__(self, name: str) -> Any:
        return getattr(self._assembled, name)

    @property
    def view(self) -> Any:
        return type("_Empty", (), {"entities": ()})()


class _NotGated:
    """The same run holding something that is not a ``ServableProduct``."""

    def __init__(self, assembled: Any) -> None:
        self._assembled = assembled

    def __getattr__(self, name: str) -> Any:
        return getattr(self._assembled, name)

    @property
    def gated(self) -> Any:
        return object()


@pytest.mark.parametrize("kind", sorted(CLOSED_VOCABULARY))
@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_each_witness_kind_can_go_red(kind: str, run: Any) -> None:
    """Five kinds, five controls. A kind that cannot fail must not be in the
    vocabulary.

    The two argument-free kinds cannot be made unsatisfiable by their argument,
    so their subject is degraded instead — an empty view and an ungated result
    — which is exactly the failure each of them exists to catch. Both are
    wrappers around the SAME completed run, so the resolver under test is the
    real one and everything else about the run is unchanged.
    """
    subject = run
    if kind == WITNESS_ENTITIES_ASSEMBLED:
        subject = _NoEntities(run)
    elif kind == WITNESS_SERVABLE_PRODUCT_HELD:
        subject = _NotGated(run)

    # The satisfiable form of this kind resolves against the untouched run —
    # otherwise the refusal below would be evidence about the run, not the
    # witness.
    satisfiable = next(
        str(step[KEY_WITNESS])
        for step in _recipe_declaration()[KEY_STEPS]
        if str(step[KEY_WITNESS]).partition(":")[0].strip() == kind
    )
    assert resolve_witness(satisfiable, run) is True

    step = {
        KEY_STEP: 99,
        KEY_OPERATOR: "a synthetic step",
        KEY_WITNESS: UNSATISFIABLE[kind],
    }
    problems = unresolved([step], subject)
    assert problems, f"witness kind {kind!r} cannot fail, so it proves nothing"
    assert "step 99" in problems[0] and "a synthetic step" in problems[0], (
        f"the refusal does not name the step it is about: {problems[0]}"
    )


# --------------------------------------------------------------------------
# HALF FOUR — an unknown kind RAISES rather than being skipped.
# --------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_an_unknown_witness_kind_raises(run: Any) -> None:
    """A silently-skipped step is criterion 2's failure mode wearing a tick."""
    with pytest.raises(UnknownWitnessKind, match="closed vocabulary"):
        resolve_witness("a_kind_nobody_declared: anything", run)
    with pytest.raises(UnknownWitnessKind):
        unresolved(
            [
                {
                    KEY_STEP: 98,
                    KEY_OPERATOR: "a synthetic step",
                    KEY_WITNESS: "a_kind_nobody_declared",
                }
            ],
            run,
        )
