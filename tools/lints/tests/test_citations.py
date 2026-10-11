# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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

import pytest

from tools.lints.citations import (
    _MEMBER_TAIL,
    NODE_ID,
    RULE_ANCHOR,
    RULE_NODE_ID,
    RULE_RESOLVES,
    _Tree,
    anchor_before,
    check_source,
    check_tree,
    exemption_reason,
    iter_scanned_files,
    member_verdict,
    prose_lines,
    repo_index,
    resolve_cited,
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


#: Spans that may sit immediately before a citation and are themselves a
#: citation: a line citation, a ``::`` symbol citation, and the bare ``:NNN``
#: continuation of a line citation. Each points at a location; none names what
#: the cited lines hold, which is what the module docstring says an anchor is.
#: Paired with the number of ``no_anchor`` citations the line must then show:
#: a leading line citation is itself unanchored, a leading symbol citation is
#: checked by ``cite03`` instead, and a continuation is not a citation at all.
_POINTERS: tuple[tuple[str, int], ...] = (
    ("`src/pkg/mod.py:1-2`", 2),
    ("`src/pkg/mod.py::refuse`", 1),
    ("`:1-2`", 1),
)


@pytest.mark.parametrize(("pointer", "unanchored"), _POINTERS)
def test_a_citation_is_never_the_anchor_of_the_citation_after_it(
    tmp_path: pathlib.Path, pointer: str, unanchored: int
) -> None:
    """D-IMPL-378 C6: an adjacent citation is a pointer, not an anchor.

    Lane ``378e-c6`` measured 86 line citations of Python files in three
    documents that the coverage ratchet could not see, because
    ``anchor_before`` returned *any* backticked span right before a citation
    as its anchor -- another citation included -- and the ratchet skips a
    citation that has one. Dave (2026-10-08 16:40 MST): *"fix the checker's
    adjacent-backtick blind spot and re-scan the 86 hidden citations; zero
    findings from a blind checker is insufficient evidence."*

    Asserted on the mechanism by name: ``anchor_before`` returns no anchor for
    the second citation, and the scan counts it as unanchored rather than as
    carrying an anchor it could not resolve.
    """
    line = f"See {pointer}, `src/pkg/mod.py:7-9`.\n"
    _write(tmp_path, "src/pkg/mod.py", _CITED_AFTER)
    _write(tmp_path, "docs/note.md", line)

    assert anchor_before(line, line.index("src/pkg/mod.py:7-9")) is None
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.unusable_anchor == 0
    assert scan.no_anchor == unanchored


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


# --- cite03: qualified names (D-IMPL-378, OWED-RULINGS-3 item 7 (a)) --------

#: The repo root, for the one case reproduced on the real tree.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: A cited module carrying every kind of member a qualified citation names:
#: methods, an async method, a class-level field, two annotations, a nested
#: class and its members, a method under a compound statement, a subclass, a
#: function nested in a function, and an alias bound by assignment.
_MEMBERS = '''"""A module."""
from typing import TYPE_CHECKING


class Gate:
    """A class."""

    LIMIT = 3
    tenant: str
    ceiling: int = 7

    class Config:
        strict = True

        def check(self) -> None: ...

    def admit(self) -> None: ...

    async def drain(self) -> None: ...

    if TYPE_CHECKING:
        def typed_only(self) -> None: ...


class Strict(Gate):
    def refuse(self) -> None: ...


def build_router() -> None:
    async def resume() -> None: ...


TestGate = Gate.Config
'''


def test_a_citation_of_a_member_the_real_class_does_not_define_is_caught() -> None:
    """The hole as ``D-IMPL-378`` OWED-RULINGS-3 item 7 words it, on the real tree.

    Lane ``378f-c6b`` measured that *"a citation of
    ``GrantBoundChildResolver.no_such_method_anywhere`` gives no finding"*:
    ``cite03`` resolved ``GrantBoundChildResolver`` and never read the rest.
    Dave ruled (a): check the full qualified name.
    """
    cited = "src/ccf/products/child_resolver.py"
    findings = check_source(
        f"See `{cited}::GrantBoundChildResolver.no_such_method_anywhere`.\n",
        pathlib.Path("docs/note.md"),
        _REPO_ROOT,
        repo_index(_REPO_ROOT),
    )
    assert _rules(findings) == [RULE_NODE_ID], findings
    assert "GrantBoundChildResolver.no_such_method_anywhere" in findings[0]


def test_a_citation_of_a_member_the_class_does_not_define_is_caught(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/pkg/mod.py", _MEMBERS)
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::Gate.no_such_member`.\n")
    findings = check_tree(tmp_path)
    assert _rules(findings) == [RULE_NODE_ID]
    assert "Gate.no_such_member" in findings[0]


@pytest.mark.parametrize(
    "qualified",
    [
        "Gate.Config.no_such_member",
        "Gate.no_such_member.deeper",
        "build_router.no_such_member",
    ],
)
def test_a_missing_member_is_caught_at_any_depth(
    tmp_path: pathlib.Path, qualified: str
) -> None:
    _write(tmp_path, "src/pkg/mod.py", _MEMBERS)
    _write(tmp_path, "docs/note.md", f"See `src/pkg/mod.py::{qualified}`.\n")
    findings = check_tree(tmp_path)
    assert _rules(findings) == [RULE_NODE_ID]
    assert "no_such_member" in findings[0]


@pytest.mark.parametrize(
    "qualified",
    [
        "Gate.admit",
        "Gate.drain",
        "Gate.LIMIT",
        "Gate.tenant",
        "Gate.ceiling",
        "Gate.Config",
        "Gate.Config.strict",
        "Gate.Config.check",
        "Gate.typed_only",
        "Strict.refuse",
        "build_router.resume",
    ],
)
def test_a_citation_of_a_real_member_is_admitted(
    tmp_path: pathlib.Path, qualified: str
) -> None:
    """Methods, class-level fields and annotations, nested classes, a member
    under ``if TYPE_CHECKING:``, and a function nested in a function: each is
    what Python's ``__qualname__`` spells (``<locals>`` dropped), so none is a
    finding. A checker red on these would be red on correct prose."""
    _write(tmp_path, "src/pkg/mod.py", _MEMBERS)
    _write(tmp_path, "docs/note.md", f"See `src/pkg/mod.py::{qualified}`.\n")
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.checked == 1


def test_an_inherited_member_is_cited_at_the_class_that_defines_it(
    tmp_path: pathlib.Path,
) -> None:
    """``Strict.admit`` resolves at runtime, but ``admit`` is defined in
    ``Gate``'s body: its qualified name is ``Gate.admit``. A citation is a
    pointer into the cited file, and ``Strict``'s body holds no ``admit``."""
    _write(tmp_path, "src/pkg/mod.py", _MEMBERS)
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::Strict.admit`.\n")
    findings = check_tree(tmp_path)
    assert _rules(findings) == [RULE_NODE_ID]
    assert "Strict.admit" in findings[0]

    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::Gate.admit`.\n")
    assert check_tree(tmp_path) == []


def test_a_member_reached_through_an_assignment_is_unchecked_and_counted(
    tmp_path: pathlib.Path,
) -> None:
    """``TestGate = Gate.Config``: what ``TestGate.check`` names depends on a
    runtime value, the shape of Hypothesis's ``TestX = Machine.TestCase``. It
    is never a finding — guessing is how a lint goes red on correct code — and
    it is counted, because an unchecked citation nobody counts is a blind spot
    nobody sees."""
    _write(tmp_path, "src/pkg/mod.py", _MEMBERS)
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::TestGate.check`.\n")
    scan = scan_tree(tmp_path)
    assert scan.findings == []
    assert scan.unfollowable_member == 1
    assert scan.checked == 0


# --- cite03: bindings only from module and class bodies (D-IMPL-378 1.7) ---
#
# Dave, 2026-10-09 10:54 MST, repair 1.7 as the findings brief specifies it:
# *"Take bindings only from the cited file's module and class bodies; let
# tuple, `for` and `with` targets bind; cap the 'unfollowable member' count at
# 0 with a test."* Evidence: Fable G2 F-G2-3 (probes `p_citations_shadow.py`,
# `p_citations_synthetic2.py`) and the panel's K68 (`p_b6_homonym_anywhere.py`),
# on `dl-378-record` @ `15e79163`.

#: The cited class of the repair 1.7 cases: ``A.m`` exists, ``A.nope`` does not.
_CLASS_A = "class A:\n    def m(self) -> None: ...\n"

#: Bindings of the cited class's name inside a function. Before repair 1.7 the
#: first three made the dead citation ``A.nope`` "member not followable", and a
#: class nested in a function that defines ``nope`` made it *checked*. The last
#: three bound nothing before the repair; they are here because the repair also
#: makes those three target kinds bind, and a function's body must stay out.
_FUNCTION_LOCAL_HOMONYMS: dict[str, str] = {
    "an assignment (F-G2-3 (a))": "def f() -> None:\n    A = object()\n",
    "an annotated assignment": "def f() -> None:\n    A: object = object()\n",
    "an assignment in an async function": "async def f() -> None:\n    A = object()\n",
    "a nested class that defines the member": (
        "def f() -> None:\n    class A:\n        def nope(self) -> None: ...\n"
    ),
    "a for target": "def f() -> None:\n    for A in ():\n        pass\n",
    "a with target": "def f() -> None:\n    with open('x') as A:\n        pass\n",
    "a tuple target": "def f() -> None:\n    A, B = 1, 2\n",
}


@pytest.mark.parametrize("homonym", sorted(_FUNCTION_LOCAL_HOMONYMS))
def test_a_function_local_homonym_cannot_launder_a_missing_member(
    tmp_path: pathlib.Path, homonym: str
) -> None:
    """Fable G2 F-G2-3 (a): a function-local ``A = object()`` turned the dead
    citation ``x.py::A.nope`` into "member not followable", a count with no
    ceiling, so no finding ever named it. A function's local is not what ``A``
    names in that file; the class is. Asserted on the mechanism: the
    ``cite03`` finding names ``A.nope``, and the scan neither checked the
    citation nor counted it unfollowable."""
    _write(
        tmp_path, "src/pkg/mod.py", _CLASS_A + "\n\n" + _FUNCTION_LOCAL_HOMONYMS[homonym]
    )
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::A.nope`.\n")
    scan = scan_tree(tmp_path)
    assert _rules(scan.findings) == [RULE_NODE_ID], scan
    assert "A.nope" in scan.findings[0]
    assert (scan.checked, scan.unfollowable_member) == (0, 0), scan


#: Names bound only inside a function's body. Each is a local of that function:
#: Python's ``__qualname__`` spells a nested definition
#: ``build_router.<locals>.retrieve``, and gives a local variable none at all.
_FUNCTION_LOCALS = '''"""A module."""
import contextlib


def build_router() -> None:
    limit = 3
    first, second = 1, 2
    for item in ():
        pass
    with contextlib.nullcontext() as handle:
        pass

    def retrieve() -> None: ...

    async def resume() -> None: ...

    class Payload:
        size = 1


class Gate:
    def admit(self) -> None:
        decision = 1
'''


@pytest.mark.parametrize(
    "bare", ["retrieve", "resume", "Payload", "limit", "first", "item", "handle", "decision"]
)
def test_a_name_bound_only_inside_a_function_is_not_a_citable_first_name(
    tmp_path: pathlib.Path, bare: str
) -> None:
    """Repair 1.7 for the first name: a citation resolves only through a
    binding in the module body or a class body. ``x.py::retrieve`` named a
    route handler nested in ``build_router``, and the checker found it only by
    walking the whole file (lane ``378i-docs``' out-of-scope finding 3,
    *"function locals resolve"*). The finding names the missing first name;
    the qualified citation the next test admits is the one that resolves."""
    _write(tmp_path, "src/pkg/mod.py", _FUNCTION_LOCALS)
    _write(tmp_path, "docs/note.md", f"See `src/pkg/mod.py::{bare}`.\n")
    findings = check_tree(tmp_path)
    assert _rules(findings) == [RULE_NODE_ID], findings
    assert f"defines no {bare!r}" in findings[0]


@pytest.mark.parametrize(
    ("qualified", "resolves"),
    [
        ("build_router.retrieve", True),
        ("build_router.resume", True),
        ("build_router.Payload", True),
        ("build_router.Payload.size", True),
        ("build_router.limit", False),
        ("build_router.first", False),
        ("build_router.item", False),
        ("build_router.handle", False),
        ("Gate.admit.decision", False),
    ],
)
def test_a_member_is_a_definition_nested_in_a_function_never_its_local_variable(
    tmp_path: pathlib.Path, qualified: str, resolves: bool
) -> None:
    """Repair 1.7 for the members, *"never a function's local"*: an
    assignment, a loop target or a ``with`` target inside a function is never a
    member a citation resolves through -- ``Gate.admit.decision`` names a
    method's local variable, which nobody can reach. Unchanged by the repair,
    and asserted here as its boundary: a ``def`` or ``class`` nested in a
    function stays citable by naming the function first, the name Python's
    ``__qualname__`` gives it with ``<locals>`` dropped (``D-IMPL-378``
    OWED-RULINGS-3 item 7 (a) as built)."""
    _write(tmp_path, "src/pkg/mod.py", _FUNCTION_LOCALS)
    _write(tmp_path, "docs/note.md", f"See `src/pkg/mod.py::{qualified}`.\n")
    scan = scan_tree(tmp_path)
    if resolves:
        assert (scan.findings, scan.checked) == ([], 1), scan
    else:
        assert _rules(scan.findings) == [RULE_NODE_ID], scan
        assert qualified in scan.findings[0]
        assert scan.unfollowable_member == 0


#: A module whose class body and module body bind names by tuple-unpacking,
#: ``for`` and ``with`` targets. Fable G2 F-G2-3 (b): each such member was
#: reported missing, red on correct prose.
_TARGETS = '''"""A module."""
import contextlib

ROW, COLUMN = 1, 2
for LOOPED in (1, 2):
    pass
with contextlib.nullcontext() as HANDLED:
    pass


class Table:
    x, y = 1, 2
    first, *rest = (1, 2, 3)
    (outer, (inner, last)) = (1, (2, 3))
    [left, right] = [1, 2]
    for z in (1, 2):
        pass
    for key, value in {}.items():
        pass
    with contextlib.nullcontext() as fh:
        pass
    with contextlib.nullcontext() as src, contextlib.nullcontext() as (dst, extra):
        pass
'''


@pytest.mark.parametrize(
    "cited",
    [
        "ROW",
        "COLUMN",
        "LOOPED",
        "HANDLED",
        "Table.x",
        "Table.y",
        "Table.first",
        "Table.rest",
        "Table.outer",
        "Table.inner",
        "Table.last",
        "Table.left",
        "Table.right",
        "Table.z",
        "Table.key",
        "Table.value",
        "Table.fh",
        "Table.src",
        "Table.dst",
        "Table.extra",
    ],
)
def test_tuple_for_and_with_targets_bind(tmp_path: pathlib.Path, cited: str) -> None:
    """Repair 1.7, *"let tuple, `for` and `with` targets bind"*: in the module
    body and in a class body, a name a tuple or list target unpacks to
    (starred and nested included), a ``for`` target and a ``with ... as``
    target are bound there, exactly as Python binds them. Fable G2 F-G2-3 (b)
    measured ``A.x`` (tuple), ``A.z`` (``for``) and ``A.fh`` (``with``) reported
    missing."""
    _write(tmp_path, "src/pkg/mod.py", _TARGETS)
    _write(tmp_path, "docs/note.md", f"See `src/pkg/mod.py::{cited}`.\n")
    scan = scan_tree(tmp_path)
    assert (scan.findings, scan.checked) == ([], 1), scan


#: Homonyms of the cited class bound where repair 1.7 still takes bindings: the
#: module body or a class body. The panel's K68 measured the first three
#: turning a missing member into "member not followable"; the last three bind
#: once tuple, ``for`` and ``with`` targets do, and do the same.
_MODULE_OR_CLASS_HOMONYMS: dict[str, str] = {
    "a module-level alias": "A = A\n",
    "an annotated module-level alias": "A: type = A\n",
    "an unrelated class body": "class B:\n    A = 1\n",
    "a module-level for target": "for A in ():\n    pass\n",
    "a module-level with target": "with open('x') as A:\n    pass\n",
    "a module-level tuple target": "A, B = A, 1\n",
}


@pytest.mark.parametrize("homonym", sorted(_MODULE_OR_CLASS_HOMONYMS))
def test_a_homonym_in_the_module_or_a_class_body_never_passes_a_missing_member(
    tmp_path: pathlib.Path, homonym: str
) -> None:
    """What the ruling leaves to the cap (K68). A binding in the module or a
    class body that shares the cited class's name is still taken, so which
    binding ``A`` names is unknown; the citation is never *checked*. It is a
    finding or it is counted "member not followable", and
    ``test_the_unfollowable_member_count_is_capped_at_zero`` holds that count
    at 0 on the real tree -- so neither passes the gate."""
    _write(
        tmp_path, "src/pkg/mod.py", _CLASS_A + "\n\n" + _MODULE_OR_CLASS_HOMONYMS[homonym]
    )
    _write(tmp_path, "docs/note.md", "See `src/pkg/mod.py::A.nope`.\n")
    scan = scan_tree(tmp_path)
    assert scan.checked == 0, scan
    assert len(scan.findings) + scan.unfollowable_member == 1, scan


#: The ceiling on "member not followable" (repair 1.7: *"cap the 'unfollowable
#: member' count at 0 with a test"*). A citation counted there is one
#: ``cite03`` could not check -- its name before the member is bound by an
#: assignment (an alias, an instance), or a homonym in the module or a class
#: body hides which binding it names -- so the member could be missing and no
#: finding would say so. Measured 0 on this tree before the cap was written.
MAXIMUM_UNFOLLOWABLE_MEMBER_CITATIONS = 0

#: What to do when the cap is exceeded. Raising it on purpose and raising it to
#: turn a red build green are the identical edit, so the edit must say which.
UNFOLLOWABLE_CAP_INSTRUCTION = (
    "Re-cite the member at the class or function that defines it, by its own"
    " name (`path.py::Class.member`, or `path.py::function.nested` for a"
    " definition nested in a function), or remove the binding that shares the"
    " cited name. If a citation genuinely cannot be followed, raise"
    " MAXIMUM_UNFOLLOWABLE_MEMBER_CITATIONS in the same commit and name the"
    " citation in the commit message."
)


def unfollowable_member_sites(root: pathlib.Path) -> list[str]:
    """Every symbol citation the scan of `root` counts "member not followable".

    As ``host:line cites path::A.b``. Reproduces the ``cite03`` branch of
    ``tools/lints/citations.py::check_source`` that bumps
    ``unfollowable_member`` -- path resolved, first name present, a member
    tail, and ``member_verdict`` answering ``None`` -- with the checker's own
    walk, exemption policy, prose filter, patterns and verdict. The tests below
    assert that its length equals ``scan_tree``'s count, so it cannot drift
    from what the gate counts.
    """
    index = repo_index(root)
    trees = _Tree()
    sites: list[str] = []
    for path in iter_scanned_files(root):
        host = path.relative_to(root).as_posix()
        if exemption_reason(host) is not None:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        prose = prose_lines(source) if path.suffix == ".py" else None
        for lineno, line in enumerate(source.splitlines(), 1):
            if prose is not None and lineno not in prose:
                continue
            for match in NODE_ID.finditer(line):
                cited, symbol = match.group("path"), match.group("symbol")
                target, _ambiguous = resolve_cited(cited, root, index)
                if target is None or symbol not in trees.spans(target):
                    continue
                tail = _MEMBER_TAIL.match(line, match.end())
                if tail is None:
                    continue
                qualified = [symbol, *tail.group(0)[1:].split(".")]
                verdict, _stop = member_verdict(trees.definitions(target), qualified)
                if verdict is None:
                    sites.append(f"{host}:{lineno} cites {cited}::{'.'.join(qualified)}")
    return sites


def test_the_unfollowable_member_count_is_capped_at_zero() -> None:
    """The cap, on this tree. A count nobody bounds is how F-G2-3's laundered
    citations stayed invisible: the scan counted them and nothing failed."""
    sites = unfollowable_member_sites(_REPO_ROOT)
    assert len(sites) == scan_tree(_REPO_ROOT).unfollowable_member, sites
    assert len(sites) <= MAXIMUM_UNFOLLOWABLE_MEMBER_CITATIONS, (
        f"{len(sites)} symbol citations are 'member not followable', ceiling"
        f" {MAXIMUM_UNFOLLOWABLE_MEMBER_CITATIONS}: cite03 could not check"
        f" them, so a missing member behind them is no finding."
        f" {UNFOLLOWABLE_CAP_INSTRUCTION} Found:"
        + "".join(f"\n  - {site}" for site in sites)
    )


def test_the_cap_sees_every_site_the_scan_counts(tmp_path: pathlib.Path) -> None:
    """The cap's positive control: on a tree carrying a member reached through
    an assignment (``TestGate = Gate.Config``) and a missing member behind a
    module-level alias (K68), the cap's own lister names both sites, agrees
    with ``scan_tree``'s count, and would fail the ceiling. A cap whose lister
    found nothing would pass forever."""
    _write(tmp_path, "src/pkg/mod.py", _MEMBERS)
    _write(tmp_path, "src/pkg/alias.py", _CLASS_A + "\n\nA = A\n")
    _write(
        tmp_path,
        "docs/note.md",
        "See `src/pkg/mod.py::TestGate.check`.\nSee `src/pkg/alias.py::A.nope`.\n",
    )
    sites = unfollowable_member_sites(tmp_path)
    assert sites == [
        "docs/note.md:1 cites src/pkg/mod.py::TestGate.check",
        "docs/note.md:2 cites src/pkg/alias.py::A.nope",
    ], sites
    assert len(sites) == scan_tree(tmp_path).unfollowable_member
    assert len(sites) > MAXIMUM_UNFOLLOWABLE_MEMBER_CITATIONS


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


#: The two dated records ``D-IMPL-378`` ruling C6 (c) exempts: 41 and 5 of the
#: 362 unique sites the citation ratchet listed on ``dl-378-integ`` @
#: ``8cfe77b2``.
C6_DATED_RECORDS: tuple[str, ...] = (
    "docs/V1.0.2-SPEC-REVIEWS.md",
    "docs/superpowers/plans/2026-09-27-wave-2-HANDOFF.md",
)

#: The three documents the same ruling CONVERTS rather than exempts (the other
#: 316 sites), once the security lanes stop editing them.
C6_LIVING_DOCUMENTS: tuple[str, ...] = (
    "docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md",
    "docs/superpowers/plans/2026-09-25-v1-0-2-wave-1-opening-sheet.md",
    "docs/superpowers/plans/2026-09-27-v1-0-2-wave-2-opening-sheet.md",
)


def test_d_impl_378_c6_exempts_the_two_dated_records_and_not_the_living_three() -> None:
    """``D-IMPL-378`` ruling C6 (c), as configuration, checked from both sides.

    Dave: *"exempt the review record and the handoff (46 citations) and convert
    the three documents security fixes still edit (316) once the lanes stop
    editing them."* Each record is exempt by the entry that names the ruling,
    not by some broader pattern that happens to match it; each living document
    stays gated, because an exemption of one would empty part of the ratchet's
    population without a ruling.
    """
    for record in C6_DATED_RECORDS:
        reason = exemption_reason(record)
        assert reason is not None, (
            f"{record} is gated; D-IMPL-378 ruling C6 (c) exempts it as a dated record"
        )
        assert "D-IMPL-378" in reason and "C6" in reason, (
            f"{record} is exempt by a reason that does not name D-IMPL-378 C6: {reason!r}"
        )
    for living in C6_LIVING_DOCUMENTS:
        assert exemption_reason(living) is None, (
            f"{living} is exempt; D-IMPL-378 ruling C6 (c) converts it instead"
        )


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
