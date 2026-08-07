"""Unit tests for the cross-file citation checker (`tools/lints/citations.py`).

Every case is built as a real two-file tree under `tmp_path`, because a
citation is a claim about a *second* file and a checker for it cannot be
exercised from one source string.

The first test in the file is the **watched-to-fail** case: it reproduces the
exact defect this checker was written for — a docstring edit above a function
shifts the function down and silently falsifies every citation of it — and it
asserts both halves, that the citation was true before the edit and false
after. That pair is what makes the check a discriminator rather than a
tripwire that is always red or always green.
"""

from __future__ import annotations

import pathlib

from tools.lints.citations import (
    RULE_ANCHOR,
    RULE_NODE_ID,
    RULE_RESOLVES,
    check_tree,
    exemption_reason,
    scan_tree,
)


def _write(base: pathlib.Path, rel: str, text: str) -> pathlib.Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


#: The cited module, before and after a two-line docstring insertion. The
#: insertion is the only difference; it moves `refuse` from line 5 to line 7.
_CITED_BEFORE = '''"""A module.

Line three.
"""
def refuse(x: int) -> None:
    """Refuse."""
    raise ValueError(x)
'''

_CITED_AFTER = '''"""A module.

Line three.

Two more lines of docstring, exactly as plan 15.1-19's binder.py edit added.
"""
def refuse(x: int) -> None:
    """Refuse."""
    raise ValueError(x)
'''

#: The citer. Anchored: the backticked symbol, then only " (`" before the
#: citation, which is the shape every rotted citation in this phase had.
_CITER = "The refusal `refuse` (`src/pkg/mod.py:5-7`) raises on divergence.\n"


# --- the watched-to-fail pair ----------------------------------------------


def test_the_citation_is_clean_before_the_docstring_edit(
    tmp_path: pathlib.Path,
) -> None:
    """Without the shift the citation is true, and the checker admits it.

    Half one of the discrimination proof: a checker that reported this red
    would be the red-on-correct-code failure, not a guard.
    """
    _write(tmp_path, "src/pkg/mod.py", _CITED_BEFORE)
    _write(tmp_path, "docs/note.md", _CITER)
    assert check_tree(tmp_path) == []


def test_a_docstring_edit_above_the_cited_symbol_is_caught(
    tmp_path: pathlib.Path,
) -> None:
    """The defect, reproduced: two docstring lines falsify a live citation.

    Half two. Nothing else in the tree changes — the citing file is
    byte-identical to the passing case above, and the cited file differs only
    by two lines of prose. This is the event that happened four times in Phase
    15.1 and that nothing caught; watched to fail here means watched to be
    *found* here, and the case above is the control proving it is found for
    the right reason.
    """
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(tmp_path, "docs/note.md", _CITER)

    findings = check_tree(tmp_path)
    assert _rules(findings) == [RULE_ANCHOR]
    assert "src/pkg/mod.py:5-7" in findings[0]
    assert "refuse" in findings[0]


# --- historical citations pass ---------------------------------------------


def test_a_citation_marked_as_a_past_snapshot_is_admitted(
    tmp_path: pathlib.Path,
) -> None:
    """The convention `ccf.deployment.binder` already uses, mechanised.

    The same stale citation as the case above, with the sentence saying
    outright that it is where the symbol stood when the citation was written.
    A citation scoped to a past tree is correct, and a checker that reddened
    it would push authors to delete true statements.
    """
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "docs/note.md",
        "The correction cites `refuse` as `src/pkg/mod.py:5-7`, which is where"
        " it stood in the tree the correction was written against; the"
        " definition has moved since.\n",
    )
    assert check_tree(tmp_path) == []


def test_a_git_object_id_in_the_same_sentence_marks_a_snapshot(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "docs/note.md",
        "At `f18289c`, `refuse` (`src/pkg/mod.py:5-7`) was the refusal.\n",
    )
    assert check_tree(tmp_path) == []


def test_a_marker_in_a_neighbouring_sentence_does_not_exempt(
    tmp_path: pathlib.Path,
) -> None:
    """Nearness is not scoping — the marker must be in the citation's sentence.

    `.planning/REQUIREMENTS.md` has one four-thousand-character paragraph that
    opens by saying an *earlier* record's line numbers have since moved and
    then makes six present-tense citations of its own. A line-scoped marker
    exempts all six.
    """
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "docs/note.md",
        "An earlier record's line numbers have since moved. Re-checked today:"
        " `refuse` (`src/pkg/mod.py:5-7`) is the refusal.\n",
    )
    assert _rules(check_tree(tmp_path)) == [RULE_ANCHOR]


# --- cite01: existence and range -------------------------------------------


def test_a_line_past_the_end_of_the_cited_file_is_caught(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_BEFORE)
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py:400`.\n")
    findings = check_tree(tmp_path)
    assert _rules(findings) == [RULE_RESOLVES]
    assert "has 7 lines" in findings[0]


def test_a_citation_of_a_file_that_does_not_exist_is_not_a_finding(
    tmp_path: pathlib.Path,
) -> None:
    """Unresolvable is unchecked, never red.

    A bare name matching nothing is far more often a placeholder in prose
    (`module.py:NNN` in a worked example) than a broken pointer, and guessing
    is how a lint goes red on correct code. It is counted in `--report`.
    """
    _write(tmp_path, "docs/note.md", "See `nowhere/at/all.py:12`.\n")
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.unresolved_path == 1


def test_an_ambiguous_bare_filename_is_not_a_finding(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "examples/a/run.py", "x = 1\n")
    _write(tmp_path, "examples/b/run.py", "x = 1\n")
    _write(tmp_path, "docs/note.md", "See `run.py:900`.\n")
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.ambiguous_path == 1


# --- cite02: what may and may not become an anchor -------------------------


def test_an_unanchored_citation_is_reported_unchecked_not_red(
    tmp_path: pathlib.Path,
) -> None:
    """The checker's largest blind spot, asserted so it stays honest."""
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "docs/note.md",
        "- `src/pkg/mod.py:5-7`\n",
    )
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.no_anchor == 1


def test_a_labelling_colon_does_not_bind_an_anchor(
    tmp_path: pathlib.Path,
) -> None:
    """`rule: site` names the rule, not what lives at the site.

    Measured as a real false positive on `docs/surface-changes/` before the
    gap rule excluded `:`; kept as a regression case.
    """
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "docs/note.md",
        "False positives of `cinv01a-prompt-shape`: `src/pkg/mod.py:1-2`.\n",
    )
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.no_anchor == 1


def test_a_locator_word_still_binds_the_anchor(tmp_path: pathlib.Path) -> None:
    """"X at Y" is a locating construction and must stay anchored."""
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(tmp_path, "docs/note.md", "`refuse` at `src/pkg/mod.py:5-7`.\n")
    assert _rules(check_tree(tmp_path)) == [RULE_ANCHOR]


def test_a_verb_between_anchor_and_citation_breaks_the_binding(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "docs/note.md",
        "`refuse` is discussed by the docstring at `src/pkg/mod.py:1-2`.\n",
    )
    assert check_tree(tmp_path) == []


def test_an_anchor_matching_two_definitions_is_unchecked(
    tmp_path: pathlib.Path,
) -> None:
    _write(
        tmp_path,
        "src/pkg/mod.py",
        "class A:\n    def go(self) -> None: ...\n\n\nclass B:\n"
        "    def go(self) -> None: ...\n",
    )
    _write(tmp_path, "docs/note.md", "`go` (`src/pkg/mod.py:1`).\n")
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.unusable_anchor == 1


def test_a_namespaced_id_anchor_is_checked_as_text(
    tmp_path: pathlib.Path,
) -> None:
    """The `src/ccf/peering/admission.py` shape: an artifact class id anchor."""
    _write(
        tmp_path,
        "src/pkg/mod.py",
        "A = 1\nB = 2\nC = ArtifactClass(class_id='ccf.debt-profile')\n",
    )
    _write(tmp_path, "docs/note.md", "The id `ccf.debt-profile` (`src/pkg/mod.py:1`).\n")
    assert _rules(check_tree(tmp_path)) == [RULE_ANCHOR]

    _write(tmp_path, "docs/note.md", "The id `ccf.debt-profile` (`src/pkg/mod.py:3`).\n")
    assert check_tree(tmp_path) == []


# --- cite03: symbol citations ----------------------------------------------


def test_a_node_id_naming_no_definition_is_caught(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::refuse_renamed`.\n")
    findings = check_tree(tmp_path)
    assert _rules(findings) == [RULE_NODE_ID]
    assert "refuse_renamed" in findings[0]


def test_a_node_id_that_resolves_is_admitted_and_survives_a_line_shift(
    tmp_path: pathlib.Path,
) -> None:
    """Why `::` is the preferred form: the shift that breaks a line citation
    leaves the symbol citation true, and the checker agrees on both trees."""
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::refuse`.\n")
    for body in (_CITED_BEFORE, _CITED_AFTER):
        _write(tmp_path, "src/pkg/mod.py", body)
        assert check_tree(tmp_path) == []


# --- what is scanned, and what is exempt -----------------------------------


def test_a_node_id_inside_python_code_is_not_scanned(
    tmp_path: pathlib.Path,
) -> None:
    """Test data is not a claim about the tree."""
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "tests/test_x.py",
        'RESULTS = {"src/pkg/mod.py::test_renamed": 1.0}\n',
    )
    assert check_tree(tmp_path) == []


def test_a_node_id_inside_a_python_docstring_is_scanned(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(
        tmp_path,
        "tests/test_x.py",
        '"""Mirrors `src/pkg/mod.py::refuse_renamed`."""\n',
    )
    assert _rules(check_tree(tmp_path)) == [RULE_NODE_ID]


def test_a_node_id_inside_a_python_comment_is_scanned(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(tmp_path, "tests/test_x.py", "# see `src/pkg/mod.py::refuse_renamed`\n")
    assert _rules(check_tree(tmp_path)) == [RULE_NODE_ID]


def test_the_decision_log_is_exempt_and_deferred_items_is_not() -> None:
    """The scope split is *maintained* versus *dated*, stated in config."""
    assert exemption_reason("docs/DECISIONS.md") is not None
    assert exemption_reason(".planning/phases/15.1-x/15.1-01-PLAN.md") is not None
    assert exemption_reason(".planning/phases/15.1-x/deferred-items.md") is None
    assert exemption_reason(".planning/REQUIREMENTS.md") is None
    assert exemption_reason("public/tutorial/adopters-guide.md") is None
    assert exemption_reason("src/ccf/deployment/binder.py") is None


def test_an_exempt_file_is_not_scanned_at_all(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(tmp_path, "docs/DECISIONS.md", _CITER)
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.exempt_files == 1


def test_a_clean_tree_is_clean(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(tmp_path, "docs/note.md", "`refuse` (`src/pkg/mod.py:7-9`).\n")
    assert check_tree(tmp_path) == []
