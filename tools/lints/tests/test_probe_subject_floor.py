"""The subject-floor probe's CLASSIFIER, held to one row per decision it makes.

``D-IMPL-357`` C5, round-2 item 5. Every other module under ``tools/`` is
referenced from a test tree; :mod:`tools.probe_subject_floor` was the one that
was not, and the gap was not cosmetic. The probe ships two controls of its own
— :func:`~tools.probe_subject_floor.positive_control` proves the **matcher**
can refuse, and a reviewer's three negative controls proved the **pipeline**
can — but neither exercises the **classifier's judged-or-not decision**, and
that decision is the whole of what the wave's adoption answer rests on.

Both round-1 misses lived exactly there. A reviewer planted an out-of-grammar
literal at ``question(subject=…)`` — the SDK's own request constructor and the
door path the examples actually take — and the probe exited 0 with ``PASS``,
listing the value among the NON-findings. And three examples build their
request as ``subject=<id> or ""``, whose right operand IS a literal in that
module and IS outside the grammar, and all three were filed as *"not a literal
and not bound to one in this module"*.

**Why table-driven, and why the reason string is asserted and not just the
flag.** A classifier that returns the right boolean for the wrong reason is a
classifier that will return the wrong boolean as soon as the tree changes
shape, and the reason string is what a reader uses to overturn the author's
call. So each row pins both. The rows below cover every collection path
(YAML subject, YAML parameter, Python subject keyword, Python parameter
keyword, Python module binding, command-line option default) and every node
shape the Python recorder branches on (a plain literal, a name folded from a
module binding, a boolean expression, a conditional expression, a subscript off
a YAML-loaded document, an attribute access, an unbound name, a non-string
constant).

**Sabotage, measured, with the population named.** Six classifier branches were
severed in turn. The population is this file alone —
``pytest tools/lints/tests/test_probe_subject_floor.py -q -p no:randomly``,
**21 collected**, green at ``21 passed, 0 failed, 0 errors, 0 skipped`` — and
the probe was restored from saved bytes after each severing with the sha256
re-verified, never by a ``git checkout``. Every severing reddened at least one
row; the counts below are the measured ones, not the intended ones:

- ``judged = callee in judged_callees`` narrowed back to
  ``callee == REQUEST_CALLEE`` — **1 red**, the
  ``question`` collection-path row. This is the round-1 blind spot itself.
- the ``BoolOp``/``IfExp`` fold removed — **2 reds**, one per branch shape.
- ``_option_name`` returning ``None`` unconditionally — **3 reds**: the
  ``--subject`` collection-path row, the non-literal-default reason row, and
  the residual row (which is red only because its positive control lives in the
  same function — see that row's own docstring).
- the transitive YAML hop in ``_module_bindings`` removed — **1 red**, the
  name-bound-transitively row.
- ``_why_unresolved`` collapsed to one blanket reason — **3 reds**, the three
  rows that reach it. The two YAML-source rows and the non-string row go
  through different branches of the recorder and are correctly insensitive.
- ``question_constructor_name`` always failing to derive — **1 red**, the
  positive derivation row.
  ``test_a_tree_with_no_question_constructor_is_a_could_not_tell`` is
  **insensitive to that severing by construction** — it asserts ``None`` and
  gets ``None`` — so it is a shape control for the message, not a control on the
  derivation. The row above it is the control on the derivation. Said here
  rather than left for a later reader to discover.

Nothing here writes to the repository tree: every row is written into
``tmp_path`` and scanned from there, and the two derivation rows READ
``src/**/*.py``. ``examples/`` and ``archive/`` are never touched.
"""

from __future__ import annotations

import pathlib
import textwrap
from typing import Any

import pytest

from tools.probe_subject_floor import (
    NOT_A_STRING,
    REQUEST_CALLEE,
    UNRESOLVED,
    question_constructor_name,
    scan_python,
    scan_yaml,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The judged callee set the rows are classified against. Stated here rather
#: than derived, so a row's expectation does not move when the derivation does
#: — the derivation itself has its own two rows at the bottom of this file.
JUDGED_CALLEES = frozenset({REQUEST_CALLEE, "question"})


def _scan(tmp_path: pathlib.Path, source: str) -> tuple[list[Any], list[Any]]:
    """Run the Python scanner over one snippet written into ``tmp_path``."""
    path = tmp_path / "snippet.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    values, unresolved, errors = scan_python(
        path, "snippet.py", "row", judged_callees=JUDGED_CALLEES
    )
    assert errors == [], errors
    return values, unresolved


# --- the judged-or-not decision, one row per collection path ----------------

#: ``(row id, source, expected (judged, key fragment, value, why fragment))``.
JUDGED_ROWS: tuple[tuple[str, str, bool, str, str, str], ...] = (
    (
        "a plain literal at the request contract",
        'ProductRequest(subject="ACCT-1")',
        True,
        "ProductRequest(subject=)",
        "ACCT-1",
        "is a judged request constructor",
    ),
    (
        # THE round-1 blind spot: judged only `ProductRequest` before.
        "a plain literal at the SDK's own question constructor",
        'opened.question(subject="ACCT-1")',
        True,
        "question(subject=)",
        "ACCT-1",
        "is a judged request constructor",
    ),
    (
        "a literal at a callee that is neither",
        'batching_violations(subject="a message label")',
        False,
        "batching_violations(subject=)",
        "a message label",
        "not one of",
    ),
    (
        "a name folded from a module-level string binding",
        'SUBJECT = "ACCT-1"\nProductRequest(subject=SUBJECT)',
        True,
        "ProductRequest(subject=SUBJECT)",
        "ACCT-1",
        "folded from the module binding SUBJECT",
    ),
    (
        "a nested literal under parameters=",
        'ProductRequest(parameters={"scope": ["LEI-1"]})',
        True,
        "ProductRequest(parameters=)",
        "LEI-1",
        "is a judged request constructor",
    ),
    (
        "a string-literal default at a subject-shaped option",
        'parser.add_argument("--subject", default="FAC-1")',
        True,
        "add_argument(--subject, default=)",
        "FAC-1",
        "what the example asks with when the flag is omitted",
    ),
)


@pytest.mark.parametrize(
    ("row", "source", "judged", "key", "value", "why"),
    JUDGED_ROWS,
    ids=[row[0] for row in JUDGED_ROWS],
)
def test_the_classifier_judges_each_collection_path_as_stated(
    tmp_path: pathlib.Path,
    row: str,
    source: str,
    judged: bool,
    key: str,
    value: str,
    why: str,
) -> None:
    """One row per collection path: the judged flag AND the reason for it.

    Matched on the KEY rather than on the text, because a snippet declaring
    ``SUBJECT = "ACCT-1"`` is collected twice on purpose — once as the
    subject-named module binding and once at the position it is folded into —
    and the row under test is the second."""
    values, _ = _scan(tmp_path, source)
    matching = [v for v in values if v.key == key]
    assert len(matching) == 1, [(v.key, v.value) for v in values]
    found = matching[0]
    assert found.judged is judged, found.why
    assert found.value == value
    assert why in found.why


def test_an_option_default_under_another_name_is_the_stated_residual(
    tmp_path: pathlib.Path,
) -> None:
    """The residual the module docstring discloses, asserted so it stays a
    disclosure rather than becoming a silent gap: `--lei` is NOT collected.

    This row is the reason the residual is worth writing down. A reader who
    sees `--subject` collected will reasonably assume every option is, and the
    probe's zero would then be read over a population it never looked at.

    **Its positive control is in the same function, and that is deliberate.**
    Measured: a severing that makes `_option_name` return `None` unconditionally
    leaves an assertion of *"nothing was collected"* green — a vacuous pass, and
    exactly the shape this wave has found five times. Scanning both options in
    one test makes the row say *"`--subject` yes, `--lei` no"*, which no broken
    collector can satisfy."""
    collected, unresolved = _scan(
        tmp_path, 'parser.add_argument("--subject", default="FAC-1")'
    )
    assert [v.value for v in collected] == ["FAC-1"], "the control must collect"
    assert unresolved == []

    values, unresolved = _scan(
        tmp_path, 'parser.add_argument("--lei", default="LEI-1")'
    )
    assert values == []
    assert unresolved == []


# --- the node shapes, and the reason each one gives -------------------------

#: ``(row id, source, expected (residual class, why fragment))``.
REASON_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "a subscript off a YAML-loaded document",
        'QUESTION = yaml.safe_load(TEXT)\n'
        'ProductRequest(subject=QUESTION["question"]["subject"])',
        UNRESOLVED,
        "is a parsed YAML document",
    ),
    (
        # The transitive hop. Without it this row reads "no module-level
        # binding in this file at all", which is false — there is one.
        "a name bound transitively to a YAML-loaded document",
        'QUESTION = yaml.safe_load(TEXT)\n'
        'SUBJECT = QUESTION["question"]["subject"]\n'
        "ProductRequest(subject=SUBJECT)",
        UNRESOLVED,
        "is a parsed YAML document",
    ),
    (
        "an attribute access",
        "ProductRequest(subject=record.claim.entity_uri)",
        UNRESOLVED,
        "an attribute access",
    ),
    (
        "a name with no module-level binding at all",
        "def build(subject):\n    return ProductRequest(subject=subject)",
        UNRESOLVED,
        "has no module-level binding in this file at all",
    ),
    (
        "a non-string constant under parameters=",
        "ProductRequest(parameters={'depth': 3})",
        NOT_A_STRING,
        "not a string",
    ),
    (
        "a non-literal default at a subject-shaped option",
        'parser.add_argument("--subject", default=asked["subject"])',
        UNRESOLVED,
        "a subscript",
    ),
)


@pytest.mark.parametrize(
    ("row", "source", "cls", "why"),
    REASON_ROWS,
    ids=[row[0] for row in REASON_ROWS],
)
def test_each_unresolved_shape_gives_its_own_reason_not_a_blanket_one(
    tmp_path: pathlib.Path, row: str, source: str, cls: str, why: str
) -> None:
    """Round-2 item 4's principle, held per shape.

    Round-1 printed one reason — *"not a literal and not bound to one in this
    module"* — over 229 positions, and it was FALSE about three of them. A
    residual that states the wrong reason is worse than one that states none:
    it is a don't-know wearing a confident answer's clothes, which is the exact
    failure this probe's own docstring is built against."""
    _, unresolved = _scan(tmp_path, source)
    matching = [u for u in unresolved if why in u.why]
    assert len(matching) == 1, [(u.cls, u.detail, u.why) for u in unresolved]
    assert matching[0].cls == cls
    assert "not a literal and not bound to one in this module" not in matching[0].why


# --- the two-branch shapes, reported once per branch ------------------------


@pytest.mark.parametrize(
    ("row", "source", "label"),
    (
        ("boolean or", 'ProductRequest(subject=anchor or "")', "or-branch"),
        (
            "conditional",
            'ProductRequest(subject=anchor if anchor else "")',
            "conditional-branch",
        ),
    ),
    ids=("boolean or", "conditional"),
)
def test_a_two_branch_expression_is_reported_once_per_branch(
    tmp_path: pathlib.Path, row: str, source: str, label: str
) -> None:
    """The shape three shipped examples actually write.

    `subject=facility_id or ""` carries the RIGHT operand whenever the left one
    is falsy, the right operand is a literal, and the empty string is outside
    the floor because the grammar requires a leading alphanumeric. So the
    position yields TWO reports — a value for the literal branch and a residual
    for the branch whose value is not in the source — and the literal branch is
    a finding. Judging the node as one expression is how three real
    out-of-grammar literals were filed as "not a literal"."""
    values, unresolved = _scan(tmp_path, source)
    assert len(values) == 1, [(v.key, v.value) for v in values]
    assert values[0].value == ""
    assert values[0].judged is True
    assert label in values[0].key
    assert values[0].refuses is True, "the empty string must be outside the floor"
    assert len(unresolved) == 1, [(u.detail, u.why) for u in unresolved]
    assert label in unresolved[0].detail


# --- the YAML classifier ----------------------------------------------------


@pytest.mark.parametrize(
    ("row", "document", "judged", "why"),
    (
        (
            "a subject beside another request field",
            'question:\n  subject: "ACCT-1"\n  intent: "review"\n',
            True,
            "sibling request fields",
        ),
        (
            "a subject under a question key",
            'question:\n  subject: "ACCT-1"\n',
            True,
            "parent key 'question'",
        ),
        (
            "a subject that is an operator step's prose",
            "steps:\n  - operator: traverse\n    subject: the dominant security\n",
            False,
            "no request field among siblings",
        ),
    ),
    ids=("sibling field", "parent key", "operator prose"),
)
def test_the_yaml_classifier_judges_by_the_three_stated_tests(
    tmp_path: pathlib.Path, row: str, document: str, judged: bool, why: str
) -> None:
    """The YAML half of the judged-or-not decision, one row per test it applies.

    `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml` names
    each operator step's `subject:` in prose, and those values do NOT pass the
    floor — so the not-judged row here is the one keeping six real refusals out
    of the finding count, and it is the one a reader most needs to be able to
    overturn."""
    path = tmp_path / "doc.yaml"
    path.write_text(document, encoding="utf-8")
    values, _, errors = scan_yaml(path, "doc.yaml")
    assert errors == []
    subjects = [v for v in values if v.kind == "yaml-subject"]
    assert len(subjects) == 1, [(v.key, v.value, v.why) for v in values]
    assert subjects[0].judged is judged, subjects[0].why
    assert why in subjects[0].why


def test_a_yaml_parameter_string_at_any_depth_is_judged(
    tmp_path: pathlib.Path,
) -> None:
    """`refuse_floor` walks every DECLARED string at every declared depth, so a
    string nested inside `parameters` is a judged position and a scan that only
    read the top level would under-report exactly where the floor judges."""
    path = tmp_path / "doc.yaml"
    path.write_text(
        'question:\n  parameters:\n    scope:\n      - "LEI-1"\n', encoding="utf-8"
    )
    values, _, errors = scan_yaml(path, "doc.yaml")
    assert errors == []
    parameters = [v for v in values if v.kind == "yaml-parameter"]
    assert [(v.value, v.judged) for v in parameters] == [("LEI-1", True)]


# --- the derivation: the name comes from the SDK ----------------------------


def test_the_question_constructor_name_is_derived_from_the_library_tree() -> None:
    """Round-2 item 3. The name is taken FROM the SDK, by parsing rather than by
    importing, and the derivation is structural: the one function under
    `src/**/*.py` whose keyword-only parameters are exactly the request axes a
    caller supplies and whose return annotation names `ProductRequest`.

    The assertion is on the derived NAME and on the evidence line, because a
    derivation that returns the right name from the wrong place would silently
    stop tracking a rename."""
    name, why = question_constructor_name(REPO_ROOT)
    assert name == "question"
    assert "src/ccf/products/product.py" in why
    assert "derived structurally" in why


def test_a_tree_with_no_question_constructor_is_a_could_not_tell(
    tmp_path: pathlib.Path,
) -> None:
    """A derivation that has stopped working must fail LOUDLY. Returning
    `ProductRequest` alone would narrow the judged set back to exactly the
    round-1 blind spot, and the probe would report `PASS` over a population it
    had stopped looking at — which is the collapse of don't-know into pass this
    module exists to refuse."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "empty.py").write_text("X = 1\n", encoding="utf-8")
    name, why = question_constructor_name(tmp_path)
    assert name is None
    assert "could not derive" in why
    assert "0 candidate name(s)" in why
