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

#: The cp-04 ids, as a roster, so the real-tree control names what it
#: expects rather than counting. Sixteen (``CFT-G01..G16``) held Dave's
#: 2026-08-31 ruling; ``CFT-G18`` joined on 2026-09-03 under Phase 24.5.1
#: criterion 19 as amended (CRITERIA-LOCK Amendment 1; ``D-IMPL-245`` (4),
#: the ambiguous-anchor refusal), and this roster was amended in-phase by
#: Dave's ruling at ``D-IMPL-248`` — the one ``tools/`` edit of that phase.
#: ``CFT-G17`` is the id Dave WITHDREW and stays a phantom: it is never
#: re-minted, so the roster is seventeen ids with a hole at 17.
CP04_IDS = frozenset(f"CFT-G{n:02d}" for n in range(1, 17)) | {"CFT-G18"}
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
) -> pathlib.Path:
    """A root carrying one ``cp-04-scratch`` rung, its test modules, and the schema."""
    artifacts = tmp_path / SCRATCH_TREE / "artifacts"
    artifacts.mkdir(parents=True)
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
