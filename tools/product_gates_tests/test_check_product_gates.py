"""The product-gate checker's own tests: three sabotages RED naming the id (`24.5-L-10`, `L-18`).

Every judgment here is made by ``tools/check_product_gates.py::check_tree``
over a SCRATCH tree under ``tmp_path`` with an INJECTED ``collected`` set —
never by pytest's own machinery, and never against the real tree, which no
test edits (asserted last, in the voice of
``tests/products/test_refusal_envelope.py::test_no_control_edits_the_real_source_tree``).

The three criterion-11 faults, each watched RED under the sabotaged id:

* a declared id whose ``test:`` pytest did not collect — "did not collect";
* a test naming an id the roster does not declare — "does not declare";
* a roster declaring ZERO ids, and a tree with no roster at all.

And what the checker must IGNORE, each with its own positive control so a
pass is not vacuous: a module docstring (the ``OFS-G14`` shape), a function
docstring under the name form (the ``tests/examples/test_cp_04_seams.py``
shape — ``CFT-G99`` and ``CFT-G17`` live in meta-test docstrings there and
are NOT observations under cp-04's declared name form), and the recipe
witness string (`L-18`), which is proven unread by recording every file the
checker opens.

The one real-tree assertion is the control that the instrument fires on
real ids: cp-04 measures clean under a REAL collection, all seventeen
``CFT-G`` ids (``G01..G16`` and ``G18``; 17 withdrawn) resolve by function name, and the two phantoms are visible
only when the docstring form is deliberately applied to the seams file.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import textwrap

import pytest
import yaml

from tools.check_product_gates import (
    GATE_ID_TOKEN,
    CONVENTION_DOCSTRING_FORM,
    CONVENTION_NAME_FORM,
    SCHEMA_RELATIVE,
    check,
    check_tree,
    collect_node_ids,
    declared_convention,
    load_roster,
    load_schema,
    named_ids,
    product_trees,
)
# Aliased: a `test_`-prefixed name in this module's namespace would be
# collected by pytest as a test of its own.
from tools.check_product_gates import test_modules_for as modules_for_rung

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / SCHEMA_RELATIVE
CP04_TREE = REPO_ROOT / "examples" / "cp-04-corporate-family-tree"
CP04_ROSTER = CP04_TREE / "artifacts" / "gates.yaml"
CP04_SEAMS = REPO_ROOT / "tests" / "examples" / "test_cp_04_seams.py"

#: The scratch rung. Named ``cp-04-…`` so :func:`test_modules_for` maps it
#: onto ``tests/examples/test_cp_04_*.py`` exactly as it maps the real rung.
SCRATCH_TREE = "examples/cp-04-scratch"
SCRATCH_ROSTER = f"{SCRATCH_TREE}/artifacts/gates.yaml"
SCRATCH_MODULE = "tests/examples/test_cp_04_scratch.py"

#: Where the scratch rung keeps its own specification, relative to the tree.
#: A `spec_clause` citation is tree-relative for the same reason `test:` is
#: root-relative: each is resolved from the thing that authored it.
SCRATCH_SPEC = "spec/CP-SPEC-SCRATCH.md"

#: Prose CONTAINING the canonical phrase, as a real roster would carry it —
#: the phrase is a substring, never the whole field.
_DOCSTRING_FORM_ROSTER = (
    f"each executing test cites its gate: {CONVENTION_DOCSTRING_FORM},"
    " e.g. `ZZ-G01` on the first line of `test_first`."
)
_NAME_FORM_ROSTER = (
    f"{CONVENTION_NAME_FORM}, followed by a slug of the statement —"
    " `ZZ-G01` becomes `test_zz_g01_first`."
)

FORMS = ("docstring", "name")

#: The cp-04 ids, READ FROM THE ARTIFACT that declares them (``24.6-L-10``,
#: B-10). It was a hand-typed comprehension — ``CFT-G01..G16`` plus
#: ``CFT-G18``, with a hole at the id Dave WITHDREW — and a hand-typed roster
#: audits clean with a wrong member forever: the real-tree control below
#: compares what the modules claim against THIS set, so a set that had drifted
#: from ``gates.yaml`` would report agreement between two wrong things.
#: Deriving it means the control compares the tree against the declaration,
#: which is the comparison it was always meant to be.
#:
#: Sixteen ids held Dave's 2026-08-31 ruling; ``CFT-G18`` joined on 2026-09-03
#: under Phase 24.5.1 criterion 19 as amended (CRITERIA-LOCK Amendment 1;
#: ``D-IMPL-245`` (4), the ambiguous-anchor refusal) by Dave's ruling at
#: ``D-IMPL-248`` — the one ``tools/`` edit of that phase. That history is why
#: the hole at 17 is asserted BY NAME below rather than inferred from a range.
CP04_IDS = frozenset(
    gate["id"] for gate in yaml.safe_load(CP04_ROSTER.read_text(encoding="utf-8"))["declaration"]["gates"]
)

#: ``CFT-G17`` is the withdrawn id and is never re-minted; ``CFT-G99`` never
#: existed. Both are named only in meta-test docstrings, which is why they are
#: visible under the docstring form and absent under cp-04's declared name form.
CP04_PHANTOMS = frozenset({"CFT-G17", "CFT-G99"})


# ---------------------------------------------------------------------------
# Scratch trees
# ---------------------------------------------------------------------------


def _node(function: str) -> str:
    return f"{SCRATCH_MODULE}::{function}"


def _gate(gate_id: str, test: str, *, criterion: int = 1) -> dict:
    return {
        "id": gate_id,
        "statement": f"{gate_id} holds",
        "criterion": criterion,
        "test": test,
        "sabotage": "break it",
        "observed_red": None,
    }


def _roster(convention: str, gates: list[dict]) -> dict:
    return {
        "semver": "1.0.0",
        "class_id": "cp-04-scratch.product-gates",
        "declaration": {
            "product": "scratch.product",
            "test_naming_convention": convention,
            "gates": gates,
        },
    }


def _scratch_tree(
    tmp_path: pathlib.Path,
    *,
    roster: dict | None,
    tests: dict[str, str],
    spec: str | None = None,
) -> pathlib.Path:
    """A root carrying one ``cp-04-scratch`` rung, its test modules, and the schema.

    ``spec`` writes the tree's own specification at :data:`SCRATCH_SPEC`, so a
    ``spec_clause`` citation has something to resolve against (`D-IMPL-326`).
    Omitted — the default — is the tree that has no specification at all, which
    is itself a case the checker must report rather than skip.
    """
    artifacts = tmp_path / SCRATCH_TREE / "artifacts"
    artifacts.mkdir(parents=True)
    if spec is not None:
        spec_path = tmp_path / SCRATCH_TREE / SCRATCH_SPEC
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(textwrap.dedent(spec).lstrip(), encoding="utf-8")
    if roster is not None:
        (artifacts / "gates.yaml").write_text(
            yaml.safe_dump(roster, sort_keys=False), encoding="utf-8"
        )
    (tmp_path / "tests" / "examples").mkdir(parents=True)
    for name, source in tests.items():
        (tmp_path / "tests" / "examples" / name).write_text(
            textwrap.dedent(source).lstrip(), encoding="utf-8"
        )
    schema_copy = tmp_path / SCHEMA_RELATIVE
    schema_copy.parent.mkdir(parents=True)
    shutil.copy(SCHEMA_PATH, schema_copy)
    return tmp_path


def _judge(root: pathlib.Path, collected: set[str]) -> list[str]:
    return check_tree(
        root,
        root / SCRATCH_TREE,
        collected=frozenset(collected),
        schema=load_schema(root),
    )


DOCSTRING_MODULE = '''
def test_first():
    """ZZ-G01 holds."""


def test_second():
    """ZZ-G02 holds."""
'''

NAME_MODULE = """
def test_zz_g01_first():
    pass


def test_zz_g02_second():
    pass
"""


def _clean_case(form: str) -> tuple[dict, str, set[str]]:
    """``(roster, module source, collected)`` for a two-gate tree under ``form``."""
    if form == "docstring":
        roster = _roster(
            _DOCSTRING_FORM_ROSTER,
            [_gate("ZZ-G01", _node("test_first")), _gate("ZZ-G02", _node("test_second"))],
        )
        return roster, DOCSTRING_MODULE, {_node("test_first"), _node("test_second")}
    roster = _roster(
        _NAME_FORM_ROSTER,
        [
            _gate("ZZ-G01", _node("test_zz_g01_first")),
            _gate("ZZ-G02", _node("test_zz_g02_second")),
        ],
    )
    return roster, NAME_MODULE, {_node("test_zz_g01_first"), _node("test_zz_g02_second")}


# ---------------------------------------------------------------------------
# Clean, then the three sabotages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("form", FORMS)
def test_a_clean_scratch_tree_has_no_problems(tmp_path: pathlib.Path, form: str) -> None:
    roster, module, collected = _clean_case(form)
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    assert _judge(root, collected) == []


@pytest.mark.parametrize("form", FORMS)
def test_a_declared_id_with_no_executing_test_is_red_naming_it(
    tmp_path: pathlib.Path, form: str
) -> None:
    """Sabotage 1: drop ``ZZ-G02``'s node from the collection."""
    roster, module, collected = _clean_case(form)
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    dropped = next(node for node in collected if "g02" in node or "second" in node)
    problems = _judge(root, collected - {dropped})
    assert len(problems) == 1, problems
    assert "ZZ-G02" in problems[0]
    assert "did not collect" in problems[0]
    assert dropped in problems[0]
    assert "ZZ-G01" not in problems[0]


@pytest.mark.parametrize("form", FORMS)
def test_a_test_naming_an_undeclared_id_is_red_naming_it(
    tmp_path: pathlib.Path, form: str
) -> None:
    """Sabotage 2: a test claims ``ZZ-G99``, which no roster declares."""
    roster, module, collected = _clean_case(form)
    if form == "docstring":
        phantom = '\n\ndef test_extra():\n    """ZZ-G99 holds."""\n'
        node = _node("test_extra")
    else:
        phantom = "\n\ndef test_zz_g99_something():\n    pass\n"
        node = _node("test_zz_g99_something")
    root = _scratch_tree(
        tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module + phantom}
    )
    problems = _judge(root, collected | {node})
    assert len(problems) == 1, problems
    assert "ZZ-G99" in problems[0]
    assert "does not declare" in problems[0]
    assert node in problems[0]
    assert SCRATCH_ROSTER in problems[0]


def test_a_zero_declared_roster_is_red(tmp_path: pathlib.Path) -> None:
    """Sabotage 3a: ``gates: []`` — `D-IMPL-224` (3), zero is not green."""
    roster = _roster(_NAME_FORM_ROSTER, [])
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": NAME_MODULE})
    problems = _judge(root, set())
    assert problems, "an empty roster was judged clean"
    assert all(SCRATCH_ROSTER in problem for problem in problems), problems
    assert any("ZERO gates" in problem for problem in problems), problems


def test_a_missing_artifact_is_red(tmp_path: pathlib.Path) -> None:
    """Sabotage 3b: no ``gates.yaml`` at all — `D-IMPL-224` (1)."""
    root = _scratch_tree(tmp_path, roster=None, tests={"test_cp_04_scratch.py": NAME_MODULE})
    problems = _judge(root, set())
    assert len(problems) == 1, problems
    assert "is missing" in problems[0]
    assert SCRATCH_TREE in problems[0]


def test_an_undeclared_key_is_refused_before_any_id_is_read(tmp_path: pathlib.Path) -> None:
    """The closed schema is applied first (threat T-24.5-20).

    The module also names an undeclared id, so a checker that read ids past
    a schema failure would produce a second problem; exactly one is expected.
    """
    roster, module, collected = _clean_case("name")
    roster["declaration"]["notes"] = "an open key"
    phantom = "\n\ndef test_zz_g99_something():\n    pass\n"
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module + phantom})
    problems = _judge(root, collected)
    assert len(problems) == 1, problems
    assert SCRATCH_ROSTER in problems[0]
    assert "notes" in problems[0]
    assert "ZZ-G99" not in problems[0]


# ---------------------------------------------------------------------------
# The convention is declared, never inferred
# ---------------------------------------------------------------------------


def test_a_docstring_mention_of_a_phantom_id_under_the_name_form_is_not_an_observation(
    tmp_path: pathlib.Path,
) -> None:
    """The MEASURED cp-04 shape: meta-test docstrings naming withdrawn and control ids.

    Under the declared name form the docstring is not read, so the tree is
    clean. The positive control: applying the docstring form to the same
    module DOES surface both ids — the phantoms are there to be misread.
    """
    module = '''
def test_zz_g01_first():
    pass


def test_the_roster_check_refuses_the_withdrawn_id():
    """ZZ-G17 was withdrawn and ZZ-G99 is a side-observation control."""
'''
    roster = _roster(_NAME_FORM_ROSTER, [_gate("ZZ-G01", _node("test_zz_g01_first"))])
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    collected = {_node("test_zz_g01_first"), _node("test_the_roster_check_refuses_the_withdrawn_id")}
    assert _judge(root, collected) == []

    misread = named_ids(root / SCRATCH_MODULE, convention="docstring", root=root)
    assert {"ZZ-G17", "ZZ-G99"} <= set(misread), misread


def test_an_unrecognized_convention_is_a_problem_naming_the_tree(tmp_path: pathlib.Path) -> None:
    """Neither phrase: one problem naming the roster, judgment stops, nothing defaulted.

    The module carries an undeclared ``ZZ-G99`` under BOTH forms, so a
    checker that fell back to either form would report a second problem.
    """
    module = '''
def test_zz_g01_first():
    """ZZ-G01 holds."""


def test_zz_g99_phantom():
    """ZZ-G99 holds."""
'''
    roster = _roster("ids are matched somehow", [_gate("ZZ-G01", _node("test_zz_g01_first"))])
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    problems = _judge(root, {_node("test_zz_g01_first"), _node("test_zz_g99_phantom")})
    assert len(problems) == 1, problems
    assert SCRATCH_ROSTER in problems[0]
    assert "not recognized" in problems[0]
    assert "ZZ-G99" not in problems[0]


def test_a_convention_containing_both_phrases_is_a_problem(tmp_path: pathlib.Path) -> None:
    both = f"{CONVENTION_DOCSTRING_FORM}; or {CONVENTION_NAME_FORM}."
    assert declared_convention({"declaration": {"test_naming_convention": both}}) is None
    roster = _roster(both, [_gate("ZZ-G01", _node("test_zz_g01_first"))])
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": NAME_MODULE})
    problems = _judge(root, {_node("test_zz_g01_first"), _node("test_zz_g02_second")})
    assert len(problems) == 1, problems
    assert SCRATCH_ROSTER in problems[0]
    assert "not recognized" in problems[0]


def test_declared_convention_reads_each_phrase_and_folds_whitespace() -> None:
    folded = "the gate id lower-cased with its hyphen dropped,\n    prefixed `test_`, then a slug"
    assert declared_convention({"declaration": {"test_naming_convention": folded}}) == "name"
    assert (
        declared_convention({"declaration": {"test_naming_convention": _DOCSTRING_FORM_ROSTER}})
        == "docstring"
    )
    assert declared_convention({"declaration": {}}) is None
    assert declared_convention({}) is None


def test_a_module_docstring_id_is_not_read(tmp_path: pathlib.Path) -> None:
    """The ``OFS-G14`` shape: a retired id in a MODULE docstring is not an observation."""
    module = '''
"""ZZ-G14 was retired with the earlier design and is named here for the record."""


def test_zz_g01_first():
    pass


def test_zz_g02_second():
    pass
'''
    roster, _module, collected = _clean_case("name")
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    assert _judge(root, collected) == []

    # Under the docstring form too: the module docstring is still not a function's.
    doc_module = '"""ZZ-G14 retired."""\n' + DOCSTRING_MODULE
    roster, _module, collected = _clean_case("docstring")
    root = _scratch_tree(tmp_path / "doc", roster=roster, tests={"test_cp_04_scratch.py": doc_module})
    assert _judge(root, collected) == []


def test_each_form_is_read_only_where_declared(tmp_path: pathlib.Path) -> None:
    """One module, one name claim and one docstring claim; each form sees only its own."""
    module = '''
def test_zz_g01_first():
    pass


def test_second():
    """ZZ-G02 holds."""
'''
    gates = [_gate("ZZ-G01", _node("test_zz_g01_first")), _gate("ZZ-G02", _node("test_second"))]
    collected = {_node("test_zz_g01_first"), _node("test_second")}

    root = _scratch_tree(tmp_path / "name", roster=_roster(_NAME_FORM_ROSTER, gates), tests={"test_cp_04_scratch.py": module})
    problems = _judge(root, collected)
    assert len(problems) == 1, problems
    assert "ZZ-G02" in problems[0] and "does not name ZZ-G02" in problems[0]
    assert "name form" in problems[0]
    assert "ZZ-G01" not in problems[0]

    root = _scratch_tree(tmp_path / "doc", roster=_roster(_DOCSTRING_FORM_ROSTER, gates), tests={"test_cp_04_scratch.py": module})
    problems = _judge(root, collected)
    assert len(problems) == 1, problems
    assert "ZZ-G01" in problems[0] and "does not name ZZ-G01" in problems[0]
    assert "docstring form" in problems[0]
    assert "ZZ-G02" not in problems[0]


def test_a_declaration_pointing_at_a_test_that_does_not_claim_the_id_is_red(
    tmp_path: pathlib.Path,
) -> None:
    module = '''
def test_unrelated():
    """Something else entirely."""
'''
    roster = _roster(_DOCSTRING_FORM_ROSTER, [_gate("ZZ-G01", _node("test_unrelated"))])
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    problems = _judge(root, {_node("test_unrelated")})
    assert len(problems) == 1, problems
    assert "ZZ-G01" in problems[0]
    assert _node("test_unrelated") in problems[0]
    assert "does not name" in problems[0]


def test_a_declared_test_whose_module_is_not_on_disk_is_red_naming_it(
    tmp_path: pathlib.Path,
) -> None:
    """Phase 24.5 close panel (2026-09-03): the claim check must not fail OPEN.

    The declared ``test:`` is in the (injected) collected set, so "did not
    collect" stays green — but its module is not a file under ``root``, so
    the executing test cannot be read and the "must claim the id" check has
    nothing to judge. Before the fix the loop silently ``continue``d and the
    row measured clean. Sabotage: restore the ``continue`` and this is RED.
    """
    ghost = "tests/examples/test_cp_04_ghost.py::test_zz_g01_first"
    roster = _roster(_NAME_FORM_ROSTER, [_gate("ZZ-G01", ghost)])
    root = _scratch_tree(tmp_path, roster=roster, tests={})
    problems = _judge(root, {ghost})
    assert any("ZZ-G01" in p and "not a file" in p for p in problems), problems


def test_a_non_object_schema_file_is_red_not_a_vacuous_pass(tmp_path: pathlib.Path) -> None:
    """Phase 24.5 close panel (2026-09-03): a corrupted closed schema must not fail OPEN.

    ``load_schema`` used to fold a non-object document into ``{}``, and an
    empty schema validates every roster — the closed-keys guarantee vanished
    silently. Sabotage: restore the ``{}`` fold with no guard and this is RED.
    """
    roster, module, collected = _clean_case("name")
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    (root / SCHEMA_RELATIVE).write_text("[]", encoding="utf-8")
    problems = _judge(root, collected)
    assert any("schema" in p and "not an object" in p for p in problems), problems


def test_a_duplicated_id_is_red_naming_it(tmp_path: pathlib.Path) -> None:
    roster = _roster(
        _NAME_FORM_ROSTER,
        [_gate("ZZ-G01", _node("test_zz_g01_first")), _gate("ZZ-G01", _node("test_zz_g01_first"))],
    )
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": NAME_MODULE})
    problems = _judge(root, {_node("test_zz_g01_first"), _node("test_zz_g02_second")})
    assert any("ZZ-G01" in p and "more than once" in p for p in problems), problems


# ---------------------------------------------------------------------------
# L-18: the witness string is never read
# ---------------------------------------------------------------------------


def test_the_witness_string_is_never_read(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`L-18`: a planted recipe witness changes no verdict, and the recipe is never opened.

    Forward: a witness naming a function that exists NOWHERE, beside a clean
    roster → clean. Inverse: a roster whose ``test:`` names that witness
    function → RED naming the id, because the executing test is the
    evidence and the witness is not. Both ways the recipe file is absent
    from the set of files the checker opened.
    """
    witness = "test_zz_g01_every_returned_node_carries_a_non_empty_fibo_type_chain"
    roster, module, collected = _clean_case("name")
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    recipe = root / SCRATCH_TREE / "artifacts" / "assembly-recipe.yaml"
    recipe.write_text(
        "steps:\n  - step: 3\n    witness:\n      kind: test_function\n"
        f"      argument: {witness}\n",
        encoding="utf-8",
    )

    opened: list[pathlib.Path] = []
    real_read_text = pathlib.Path.read_text

    def recording_read_text(self: pathlib.Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        opened.append(self.resolve())
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", recording_read_text)

    assert _judge(root, collected) == []
    assert recipe.resolve() not in opened, "the checker opened the recipe"
    assert (root / SCRATCH_ROSTER).resolve() in opened, "the positive control: the roster was opened"
    assert witness not in "\n".join(real_read_text(p) for p in opened if p.suffix == ".py"), (
        "the witness function must exist in no test module for this control to mean anything"
    )

    inverse = _roster(
        _NAME_FORM_ROSTER,
        [_gate("ZZ-G01", _node(witness)), _gate("ZZ-G02", _node("test_zz_g02_second"))],
    )
    (root / SCRATCH_ROSTER).write_text(yaml.safe_dump(inverse, sort_keys=False), encoding="utf-8")
    opened.clear()
    problems = _judge(root, collected)
    assert len(problems) == 1, problems
    assert "ZZ-G01" in problems[0] and "did not collect" in problems[0]
    assert witness in problems[0]
    assert recipe.resolve() not in opened


# ---------------------------------------------------------------------------
# Collection and scope
# ---------------------------------------------------------------------------


def test_collection_failure_is_undecidable_not_clean(tmp_path: pathlib.Path) -> None:
    roster, module, _collected = _clean_case("name")
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    assert collect_node_ids(root, python="/bin/false") is None
    problems = check(root, python="/bin/false")
    assert len(problems) == 1, problems
    assert "no roster can be judged" in problems[0]


def test_main_collects_exactly_once_and_reports_the_count(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One ``pytest --collect-only`` per invocation; the verdict and the count read the same set.

    A REAL collection over the scratch root (two functions), with
    ``subprocess.run`` counted rather than replaced, so a second collection
    on the success path — which is where one crept in during this plan —
    would be a second call here.
    """
    import subprocess as real_subprocess

    import tools.check_product_gates as checker

    roster, module, _collected = _clean_case("name")
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module})
    calls: list[list[str]] = []
    real_run = real_subprocess.run

    def counting_run(argv, *args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(checker.subprocess, "run", counting_run)
    rc = checker.main(["--root", str(root)])
    assert rc == 0, capsys.readouterr().err
    assert len(calls) == 1, calls
    assert "--collect-only" in calls[0]
    assert capsys.readouterr().out.strip() == "checked 1 product trees, 2 declared gates, 2 executing"


def test_a_root_with_no_product_tree_is_not_clean(tmp_path: pathlib.Path) -> None:
    """A wrong ``--root`` must not read as a passing run."""
    (tmp_path / "tests" / "examples").mkdir(parents=True)
    (tmp_path / "tests" / "examples" / "test_nothing.py").write_text(
        "def test_nothing():\n    pass\n", encoding="utf-8"
    )
    problems = check(tmp_path)
    assert len(problems) == 1, problems
    assert "no examples/cp-* tree" in problems[0]


def test_only_the_cp_ladder_is_in_scope() -> None:
    """`D-IMPL-224` (4): ``hw1-*`` and ``s1-*`` exist on the tree and are not trees here."""
    others = sorted(
        p.name for p in (REPO_ROOT / "examples").iterdir() if p.is_dir() and not p.name.startswith("cp-")
    )
    assert any(name.startswith(("hw1-", "s1-")) for name in others), others
    trees = product_trees(REPO_ROOT)
    assert trees, "the real ladder was not found"
    assert all(tree.name.startswith("cp-") for tree in trees), trees


def test_test_modules_follow_the_rung_number(tmp_path: pathlib.Path) -> None:
    roster, module, _collected = _clean_case("name")
    root = _scratch_tree(tmp_path, roster=roster, tests={"test_cp_04_scratch.py": module, "test_cp_03_other.py": module})
    modules = modules_for_rung(root, root / SCRATCH_TREE)
    assert [m.name for m in modules] == ["test_cp_04_scratch.py"]
    assert modules_for_rung(root, root / "examples" / "not-a-rung") == []


# ---------------------------------------------------------------------------
# The real cp-04 tree — the control that the instrument fires on real ids
# ---------------------------------------------------------------------------


def test_the_real_cp_04_convention_parses_as_the_name_form() -> None:
    assert declared_convention(load_roster(CP04_ROSTER)) == "name"


def test_cp04_ids_are_derived_from_the_artifact(tmp_path: pathlib.Path) -> None:
    """``24.6-L-10``: the roster is read, and the read is live.

    Three claims, because "derived" on its own is a word rather than a
    property. It read something (non-empty, and ``CFT-G01`` by name — the
    ``tests/deployment/test_class_lookup.py::test_the_sdk_artifact_classes_were_actually_discovered``
    idiom). It excludes the withdrawn id by name rather than by arithmetic.
    And removing an id from a COPY of the artifact changes what the same
    derivation produces, so the constant cannot be a cached literal wearing a
    ``yaml.safe_load`` for decoration.
    """
    assert CP04_IDS, "the derivation read no gate at all"
    assert "CFT-G01" in CP04_IDS, sorted(CP04_IDS)
    assert "CFT-G17" not in CP04_IDS, (
        "CFT-G17 is the id Dave withdrew; a roster that re-mints it has been"
        " regenerated from a range rather than read from the declaration"
    )
    assert CP04_PHANTOMS.isdisjoint(CP04_IDS), sorted(CP04_PHANTOMS & CP04_IDS)

    document = yaml.safe_load(CP04_ROSTER.read_text(encoding="utf-8"))
    dropped = document["declaration"]["gates"][0]["id"]
    document["declaration"]["gates"] = document["declaration"]["gates"][1:]
    copy = tmp_path / "gates.yaml"
    copy.write_text(yaml.safe_dump(document), encoding="utf-8")
    rederived = frozenset(
        gate["id"] for gate in yaml.safe_load(copy.read_text(encoding="utf-8"))["declaration"]["gates"]
    )
    assert rederived == CP04_IDS - {dropped}, sorted(rederived ^ (CP04_IDS - {dropped}))


def test_the_real_cp_04_tree_is_clean() -> None:
    """One REAL collection; cp-04 judged under its DECLARED name form.

    Two facts are asserted by name so "clean" cannot be vacuous: every one of
    the seventeen ``CFT-G`` ids (a hole at 17) is claimed by function name in cp-04's own
    modules, and ``CFT-G17``/``CFT-G99`` — which the seams module names only
    in function DOCSTRINGS — are absent under the name form and present
    when the docstring form is deliberately applied to that file.
    """
    collected = collect_node_ids(REPO_ROOT)
    assert collected, "collection over tests/examples/ failed or read nothing"

    problems = check_tree(REPO_ROOT, CP04_TREE, collected=collected, schema=load_schema(REPO_ROOT))
    assert problems == [], "\n".join(problems)

    by_name: dict[str, set[str]] = {}
    for module in modules_for_rung(REPO_ROOT, CP04_TREE):
        for gate_id, nodes in named_ids(module, convention="name", root=REPO_ROOT).items():
            by_name.setdefault(gate_id, set()).update(nodes)
    assert set(by_name) == CP04_IDS, sorted(set(by_name) ^ CP04_IDS)
    assert not (set(by_name) & CP04_PHANTOMS)

    misread = set(named_ids(CP04_SEAMS, convention="docstring", root=REPO_ROOT))
    assert CP04_PHANTOMS <= misread, sorted(misread)


def test_no_test_edits_the_real_tree() -> None:
    """The checker, cp-04's tree and the seams module are byte-identical to HEAD.

    Scoped to the paths this plan must not have moved. Sibling plans hold
    uncommitted work elsewhere on a shared tree, and a whole-tree status
    would read their work as tampering.
    """
    status = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--",
            "tools/check_product_gates.py",
            "examples/cp-04-corporate-family-tree",
            "tests/examples/test_cp_04_seams.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert status == "", status


# ---------------------------------------------------------------------------
# The acceptance-authority model (`D-IMPL-326`)
# ---------------------------------------------------------------------------
#
# Dave, 2026-09-10: *"`product-gates` must accept the authority that actually
# governed the Context Product. A product may be gated by either a numbered
# ROADMAP/phase criterion, or a cited clause / definition-of-done in its
# `CP-SPEC`. Do not fabricate ROADMAP criterion numbers for cp-04 through cp-07
# merely to satisfy the tool."*
#
# And the question the gate is meant to ask, in his words: *"What approved
# acceptance authority says this product is done?"* — which a fabricated
# integer answers falsely and a citation answers checkably.
#
# **The goal is not to make the gate easier.** A citation that cannot be
# resolved is worth less than no citation at all, because it reads as authority
# while pointing at nothing. So the checker walks the whole chain — the
# specification exists, the clause exists in it, and the gate's own id appears
# in that clause — and every link has its own red below.

SPEC_WITH_CLAUSE = """
    # CP-SPEC-SCRATCH — the scratch rung

    ## G. Gates

    ### G.1 Scope

    This clause names no gate. It sits BEFORE `G.2` deliberately: a clause
    reader that ran to end-of-file rather than to the next heading would sweep
    `G.2`'s table into this clause's body, and
    `test_the_clause_body_ends_at_the_next_heading` is red exactly then.

    ### G.2 Product gates

    | Gate | Asserts |
    |---|---|
    | `ZZ-G01` | the first thing holds |
    | `ZZ-G02` | the second thing holds |

    ### G.3 Something else entirely

    No gate id lives in this clause.
    """


def _spec_gate(gate_id: str, test: str, *, clause: str = "G.2",
               document: str = SCRATCH_SPEC) -> dict:
    """A gate whose authority is a cited spec clause rather than a criterion."""
    return {
        "id": gate_id,
        "statement": f"{gate_id} holds",
        "spec_clause": {"document": document, "clause": clause},
        "test": test,
        "sabotage": "break it",
        "observed_red": None,
    }


def _both(first: dict) -> list[dict]:
    """``first`` plus a well-formed ``ZZ-G02``.

    The scratch module claims BOTH ids, so a roster declaring one is correctly
    reported for the other — which would make every negative below pass for a
    reason that has nothing to do with its subject. Declaring both isolates the
    one fault under test.
    """
    return [first, _spec_gate("ZZ-G02", _node("test_second"))]


def test_a_gate_may_cite_a_spec_clause_instead_of_a_roadmap_criterion(
    tmp_path: pathlib.Path,
) -> None:
    """The positive case, and the reason the whole change exists.

    No rung built since cp-04 has a locked ROADMAP criterion to point at, and
    inventing one would put a number in the roster that binds to nothing.
    """
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM,
                       _both(_spec_gate("ZZ-G01", _node("test_first")))),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    assert _judge(root, {_node("test_first"), _node("test_second")}) == []


def test_the_legacy_criterion_form_is_still_accepted(
    tmp_path: pathlib.Path,
) -> None:
    """*"Existing ROADMAP behavior stays valid"* (Dave).

    The control for the test above: adding a second authority form must not
    retire the first, and frozen cp-04's roster is written in it.
    """
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM,
                       [_gate("ZZ-G01", _node("test_first")),
                        _gate("ZZ-G02", _node("test_second"), criterion=2)]),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
    )
    assert _judge(root, {_node("test_first"), _node("test_second")}) == []


def test_the_two_authority_forms_may_be_mixed_across_one_roster(
    tmp_path: pathlib.Path,
) -> None:
    """One gate per authority, not one roster per authority.

    Nothing requires a product to migrate wholesale, and a rule that did would
    be a migration cost the ruling never asked for.
    """
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM,
                       [_gate("ZZ-G01", _node("test_first")),
                        _spec_gate("ZZ-G02", _node("test_second"))]),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    assert _judge(root, {_node("test_first"), _node("test_second")}) == []


def test_a_gate_declaring_BOTH_authorities_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """Exactly one, because two authorities for one gate is two answers.

    If a gate could carry both, a reader asking *"what says this is done?"*
    gets two answers with no rule ordering them — the shape `D-IMPL-315` keeps
    out one layer down.
    """
    both = _spec_gate("ZZ-G01", _node("test_first"))
    both["criterion"] = 1
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM, _both(both)),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    assert _judge(root, {_node("test_first"), _node("test_second")}) != []


def test_a_gate_declaring_NEITHER_authority_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """A gate nobody approved is the thing this field exists to prevent."""
    naked = _spec_gate("ZZ-G01", _node("test_first"))
    del naked["spec_clause"]
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM, _both(naked)),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    assert _judge(root, {_node("test_first"), _node("test_second")}) != []


def test_a_citation_naming_a_specification_that_does_not_exist_is_red(
    tmp_path: pathlib.Path,
) -> None:
    """Link 1 of the chain. A dangling document reads as authority and is none."""
    root = _scratch_tree(
        tmp_path,
        roster=_roster(
            CONVENTION_DOCSTRING_FORM,
            _both(_spec_gate("ZZ-G01", _node("test_first"),
                             document="spec/CP-SPEC-NOT-THERE.md"))),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    problems = _judge(root, {_node("test_first"), _node("test_second")})
    assert any("CP-SPEC-NOT-THERE.md" in problem for problem in problems), problems


def test_a_tree_with_no_specification_at_all_is_red(
    tmp_path: pathlib.Path,
) -> None:
    """The `cp-04-canonical` shape, measured rather than assumed.

    A rung with no `spec/` directory cannot cite a clause, and the checker must
    SAY so rather than pass the citation through unresolved.
    """
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM,
                       _both(_spec_gate("ZZ-G01", _node("test_first")))),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
    )
    assert _judge(root, {_node("test_first"), _node("test_second")}) != []


def test_a_citation_naming_a_clause_the_specification_lacks_is_red(
    tmp_path: pathlib.Path,
) -> None:
    """Link 2. The document resolving is not the clause resolving."""
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM,
                       _both(_spec_gate("ZZ-G01", _node("test_first"), clause="Q.9"))),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    problems = _judge(root, {_node("test_first"), _node("test_second")})
    assert any("Q.9" in problem for problem in problems), problems


def test_a_clause_that_does_not_carry_the_gates_own_id_is_red(
    tmp_path: pathlib.Path,
) -> None:
    """Link 3, and the one a coarser check would miss.

    `G.3` is a real clause of a real specification, so links 1 and 2 both pass;
    it simply says nothing about `ZZ-G01`. Without this link a roster could
    cite any heading in the document and read as governed.
    """
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM,
                       _both(_spec_gate("ZZ-G01", _node("test_first"), clause="G.3"))),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    problems = _judge(root, {_node("test_first"), _node("test_second")})
    assert any("ZZ-G01" in problem and "G.3" in problem for problem in problems), problems


def test_the_clause_body_ends_at_the_next_heading(
    tmp_path: pathlib.Path,
) -> None:
    """A clause is its own body, not the rest of the file.

    Cited against `G.1`, which sits BEFORE the gate table and names no id. A
    reader that ran to end-of-file would sweep `G.2`'s table into `G.1`'s body
    and report this citation as good.

    **This test was vacuous when first written** and is recorded as such: it
    cited `G.3`, the LAST clause of the fixture, where running to end-of-file
    adds nothing — so removing the body bound left it green. The bound is
    load-bearing only against a clause with something after it, which is why
    the fixture now has one.
    """
    root = _scratch_tree(
        tmp_path,
        roster=_roster(CONVENTION_DOCSTRING_FORM,
                       [_spec_gate("ZZ-G01", _node("test_first"), clause="G.1"),
                        _spec_gate("ZZ-G02", _node("test_second"))]),
        tests={"test_cp_04_scratch.py": DOCSTRING_MODULE},
        spec=SPEC_WITH_CLAUSE,
    )
    problems = _judge(root, {_node("test_first"), _node("test_second")})
    assert any("ZZ-G01" in problem and "G.1" in problem for problem in problems), problems


def test_the_token_and_the_schema_pattern_agree_on_what_an_id_is() -> None:
    """Two readers of one vocabulary, held together (`D-IMPL-326`).

    The schema decides which ids a roster may DECLARE; :data:`GATE_ID_TOKEN`
    decides which ids the checker can SEE in a docstring. They were widened
    together to admit cp-07's `C36-G01`, and a later widening of one alone
    would produce ids a roster can declare and the checker cannot find — which
    reads as a missing test rather than as a mismatched pattern.

    Compared over cases rather than by string equality: the two patterns are
    anchored differently on purpose (one whole-string, one word-bounded), so
    equal text would be the wrong assertion.
    """
    import json
    import re

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    declared = re.compile(
        schema["properties"]["declaration"]["properties"]["gates"]["items"]
        ["properties"]["id"]["pattern"]
    )
    accepted = ["CFT-G01", "CSC-G12", "C36-G08", "ZZ-G01", "ABCD-G99"]
    rejected = ["cft-G01", "C-G01", "ABCDE-G01", "CFT-G1", "CFT-X01", "36C-G01"]
    for candidate in accepted:
        assert declared.fullmatch(candidate), f"schema rejects {candidate}"
        assert GATE_ID_TOKEN.search(candidate), f"the token cannot see {candidate}"
    for candidate in rejected:
        assert not declared.fullmatch(candidate), f"schema accepts {candidate}"
        assert not GATE_ID_TOKEN.fullmatch(candidate), f"the token accepts {candidate}"


def test_two_trees_of_one_rung_do_not_see_each_others_modules(
    tmp_path: pathlib.Path,
) -> None:
    """Rung 4 carries two trees, and a bare rung glob conflates them.

    `D-IMPL-327`. `examples/cp-04-corporate-family-tree` is the frozen specimen
    and `examples/cp-04-canonical-…` is the current pattern (`D-IMPL-319`).
    Before the partition, `test_cp_04_*.py` handed each tree the OTHER's
    modules, and the canonical roster was reported as failing to declare the
    specimen's `CFT-G19` and `CFT-G99`.

    Asserted over a scratch pair rather than the real trees, so the rule is
    tested and not one deployment's file names — and asserted in BOTH
    directions, because a partition that gave the discriminated tree its module
    while starving the base tree would also make this pass.
    """
    from tools.check_product_gates import test_modules_for

    for name in ("examples/cp-09-base-thing/artifacts",
                 "examples/cp-09-special-base-thing/artifacts"):
        (tmp_path / name).mkdir(parents=True)
    examples = tmp_path / "tests" / "examples"
    examples.mkdir(parents=True)
    for module in ("test_cp_09_output.py", "test_cp_09_seams.py",
                   "test_cp_09_special_output.py"):
        (examples / module).write_text("", encoding="utf-8")

    special = [
        p.name
        for p in test_modules_for(tmp_path, tmp_path / "examples/cp-09-special-base-thing")
    ]
    base = [
        p.name for p in test_modules_for(tmp_path, tmp_path / "examples/cp-09-base-thing")
    ]
    assert special == ["test_cp_09_special_output.py"]
    assert base == ["test_cp_09_output.py", "test_cp_09_seams.py"]
    assert set(special).isdisjoint(base), "one module answers to two trees"


def test_the_rung_four_trees_are_partitioned_in_the_real_repository() -> None:
    """The rule above, measured where it actually has to hold.

    The scratch pair proves the rule; this proves the repository satisfies it —
    and that the specimen KEEPS its modules rather than being starved, which is
    the failure mode a one-sided assertion would miss.
    """
    from tools.check_product_gates import test_modules_for

    canonical = {
        p.name
        for p in test_modules_for(
            REPO_ROOT, REPO_ROOT / "examples/cp-04-canonical-corporate-family-tree"
        )
    }
    specimen = {
        p.name
        for p in test_modules_for(
            REPO_ROOT, REPO_ROOT / "examples/cp-04-corporate-family-tree"
        )
    }
    assert canonical == {"test_cp_04_canonical_output.py"}
    assert canonical.isdisjoint(specimen)
    assert "test_cp_04_traversal.py" in specimen, "the specimen lost its own modules"
    assert len(specimen) > 5, f"the specimen was starved: {sorted(specimen)}"
