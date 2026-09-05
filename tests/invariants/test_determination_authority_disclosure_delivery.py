"""The `D-IMPL-254` invariant is recorded as SDK architecture, and its four sabotages exist.

``24.6-11`` Task 2; criterion 27. The ruling of record is ``D-IMPL-254``, which
Dave elevated out of the Q1–Q28 rulings and stated in his own words
(``24.6-RULINGS.md`` §3):

    *"Internal truth, governing authority, and permitted disclosure are
    distinct concerns. The fabric preserves the governed truth of why a
    determination was reached; Policy determines what of that truth may cross
    the consumer boundary; the response shell expresses only the permitted
    disclosure. Decision Replay preserves sufficient governed evidence to
    reconstruct both the determination and the disclosure decision."*

    *"That gives us four distinct layers: Determination → Authority →
    Disclosure → Delivery."*

Criterion 27 asks for two things, and plan ``24.6-08`` shipped the first: the
invariant **recorded** in the module docstrings of the resolver, the refusal
envelope and the door, cited SDK-defined under CLAUDE.md §11 rather than as a
whitepaper commitment. This module is the second: the invariant **enforced by
construction**, which criterion 27 spells out as *"criteria 6, 10, 21 and 22
are its four sabotages and every one goes RED when its sabotage is applied"*.

What that enforcement can and cannot be, stated plainly
-------------------------------------------------------

A sabotage's RED is proven where the sabotage lives — inside the module that
owns the guard, against a scratch copy of the source it corrupts. This module
does not re-run those sabotages, and it would be worse if it did: a second copy
of a sabotage is a second thing to keep in step with the source it mutates.

What this module holds is the claim the four sabotages depend on and none of
them can make about itself: **that they exist in the tree, by exact name, in
the module the criterion assigns them to, and that pytest collects them.** A
sabotage named in a plan and absent from the tree enforces nothing (T-24.6-39),
and a sabotage present in a file pytest never collects enforces nothing either.
Both halves are asserted, from the tree, and each predicate is watched
reporting an absence before its emptiness is trusted.

The three docstrings are read by AST rather than by ``grep``, for plan
``24.6-09``'s reason: a module's own prose can trip a source-text claim, and
``ast.get_docstring`` reads the docstring and nothing else.

CLAUDE.md is not edited, and that is the criterion's own instruction
--------------------------------------------------------------------

Criterion 27 ends *"CLAUDE.md's own invariant lists are NOT edited (a revision
for Dave to order; no contradiction measured, ``24.6-RESEARCH.md`` §M7)"*, and
``D-IMPL-254``'s own text leaves adding the invariant to those lists as a
revision for Dave. §M7's measurement, recorded here so the claim travels with
the gate rather than only in a planning file: CLAUDE.md §3.1's Phase D bullet
(lines 308 to 317), §16's named-invariant list (lines 1371 to 1375) and §11
(lines 994 to 1060) were read against ``D-IMPL-254``, and **no contradiction
was measured** — each listed invariant is orthogonal to the four layers or
reinforced by them. Nothing was returned to Dave under amendment 3 (4). The one
tension worth naming is not a contradiction: *"three validation gates"* is
stated as a count in both lists while ``run_gates`` already carries more
tokens, which is ``D-IMPL-237``/``D-IMPL-238``'s existing reading rather than
``D-IMPL-254``'s doing.

So the gate here is a diff against the phase base, on both documents, and it
fails if either moves.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

# --- what the invariant IS, and where it is recorded --------------------------

#: The four layers, as the arrow string plan ``24.6-08`` wrote into the three
#: docstrings. Spelled once here; every assertion below reads this.
ARROW = "Determination → Authority → Disclosure → Delivery"

#: The two citations the recording must carry beside the arrow. The first says
#: this is SDK-defined mechanism under CLAUDE.md §11 rather than a whitepaper
#: commitment (the whitepaper is deliberately not edited, ``D-IMPL-253`` Q28);
#: the second names the decision of record.
REQUIRED_CITATIONS = ("CLAUDE.md §11", "D-IMPL-254")

#: The repository root, resolved from this file rather than from a working
#: directory, so the gate reads the same tree however pytest was invoked.
ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The three modules criterion 27 names, in the order it names them: the
#: resolver, the refusal envelope, the door.
INVARIANT_MODULES: tuple[str, ...] = (
    "src/ccf/products/resolver.py",
    "src/ccf/products/refusal.py",
    "src/ccf/products/door.py",
)

#: The phase base. ``git diff --quiet`` against it is the whole of the
#: not-edited claim, and the commit is named rather than described so a reader
#: can resolve it.
PHASE_BASE = "1022ad59"

#: The two documents that stay untouched, and the reason each does:
#: CLAUDE.md's invariant lists are a revision for Dave to order (criterion 27);
#: the whitepaper is not edited at all in this phase (``D-IMPL-253`` Q28).
UNEDITED = ("CLAUDE.md", "docs/CCF_Whitepaper_1-2.md")


# --- the four sabotages, by criterion ----------------------------------------

#: The roster criterion 27 names, one row per shipped sabotage function.
#:
#: Read the fourth column as *what its RED proves*, because that is what makes
#: this a roster of enforcement rather than a list of names:
#:
#: ===========  =========================================================
#: Criterion    What the sabotage's RED proves about ``D-IMPL-254``
#: ===========  =========================================================
#: 6            **Authority is a record, never a scalar.** A resolution that
#:              collapsed provenance to an effective number would still
#:              answer every question about the value and none about who set
#:              it — which is the first of the four mistakes Dave's text says
#:              the layering exists to prevent.
#: 10           **Naming a policy is not authority to override it.** An
#:              override honored on its name alone would put the Authority
#:              layer under the caller's control, so the layer would exist and
#:              decide nothing.
#: 21           **Disclosure withholds the internal cause.** The internal
#:              statement crossing at ``minimal`` is *"destroying audit truth
#:              to achieve suppression silence"* inverted: the truth survives
#:              and the silence does not.
#: 22           **Delivery expresses only the permitted disclosure.** Two
#:              subjects a policy says are indistinguishable becoming
#:              distinguishable at a door is the Delivery layer deciding
#:              something the Disclosure layer already decided.
#: ===========  =========================================================
#:
#: Each row is asserted present **by AST** in its module — never by ``grep``,
#: which would find a name in a comment — and asserted collected by pytest.
SABOTAGES: tuple[tuple[int, str, str], ...] = (
    (
        6,
        "tests/products/test_policy_constraints.py",
        "test_provenance_is_never_a_scalar_sabotage",
    ),
    (
        10,
        "tests/products/test_policy_constraint_resolver.py",
        "test_a_name_only_override_being_honored_is_red_sabotage",
    ),
    (
        21,
        "tests/products/test_disclosure.py",
        "test_leaking_the_internal_cause_at_minimal_is_red_sabotage",
    ),
    # Criterion 22 is a pair rather than a single function: the ruling is about
    # two subjects being indistinguishable AT A DOOR, and there are two doors.
    # Each is parametrized over the three disclosure levels, so the name below
    # is the function and the `minimal` leg is asserted separately by node id.
    (
        22,
        "tests/http_api/test_product_disclosure.py",
        "test_unauthorized_and_nonexistent_are_observationally_equivalent",
    ),
    (
        22,
        "tests/mcp/test_egress_disclosure.py",
        "test_unauthorized_and_nonexistent_are_observationally_equivalent",
    ),
)

#: The divergence controls beside criterion 22's two equivalence tests — the
#: functions that show the comparison **reporting** a planted divergence.
#:
#: They are rostered because an equivalence assertion is worth exactly as much
#: as the comparison behind it: a helper that returned no violations for
#: everything would make both equivalence tests green forever, and no sabotage
#: of the doors would ever go RED. Enumerated by name rather than counted, for
#: the reason a count over a roster stops naming its members.
EQUIVALENCE_CONTROLS: tuple[tuple[str, str], ...] = (
    (
        "tests/http_api/test_product_disclosure.py",
        "test_the_comparison_refuses_a_single_answer",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_status_divergence_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_an_evidence_presence_divergence_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_field_set_divergence_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_sentinel_against_a_reference_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_reference_that_does_not_resolve_is_reported",
    ),
    (
        "tests/mcp/test_egress_disclosure.py",
        "test_the_comparison_refuses_a_single_answer",
    ),
    ("tests/mcp/test_egress_disclosure.py", "test_the_status_control_fires"),
    (
        "tests/mcp/test_egress_disclosure.py",
        "test_the_evidence_presence_control_fires",
    ),
    ("tests/mcp/test_egress_disclosure.py", "test_the_field_set_control_fires"),
    (
        "tests/mcp/test_egress_disclosure.py",
        "test_the_sentinel_versus_reference_control_fires",
    ),
)

#: The level criterion 22 names. Both equivalence tests are parametrized over
#: the three levels, so the leg the criterion is about is pinned by node id
#: rather than assumed to be among them.
CRITERION_22_LEVEL = "minimal"


# --- predicates over the tree -------------------------------------------------


def missing_from_docstring(source: str) -> list[str]:
    """What a module's docstring fails to say, of the three required things.

    A function over its subject, so the control below can hand it a corrupted
    copy and watch it report — rather than asserting an emptiness over the
    tree that has only ever been empty.

    Read by AST: a module whose *prose elsewhere* mentioned the arrow would
    satisfy a source-text search while recording nothing, and plan ``24.6-09``
    already had to move one claim off ``grep`` for exactly that reason.
    """
    docstring = ast.get_docstring(ast.parse(source)) or ""
    return [
        wanted
        for wanted in (ARROW, *REQUIRED_CITATIONS)
        if wanted not in docstring
    ]


def function_names(source: str) -> frozenset[str]:
    """Every module-level function defined in ``source``, by name.

    Module-level rather than any ``FunctionDef`` anywhere: a name that pytest
    collects is a name at module scope, so a helper nested inside another test
    must not satisfy the roster.
    """
    tree = ast.parse(source)
    return frozenset(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"{relative} is not in the tree"
    return path.read_text(encoding="utf-8")


def _collected_node_ids(modules: tuple[str, ...]) -> frozenset[str]:
    """Every node id pytest collects over ``modules``, as a set.

    A subprocess, because collection is what is being measured: the question
    is whether *pytest* reaches these functions, and asking the running
    session about another module's items would answer a different question.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            *modules,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return frozenset(
        line.strip()
        for line in completed.stdout.splitlines()
        if "::" in line and not line.startswith(" ")
    )


# --- (a) the invariant is recorded -------------------------------------------


@pytest.mark.parametrize("module", INVARIANT_MODULES)
def test_the_module_docstring_records_the_invariant(module: str) -> None:
    """Criterion 27's first half: the three docstrings say it, and cite it.

    The arrow alone is not the recording. A docstring naming the four layers
    without saying that they are SDK-defined under CLAUDE.md §11 would leave a
    reader to infer that the whitepaper committed to them, which is exactly the
    inference ``D-IMPL-253`` Q28 refuses — the whitepaper is not edited, and
    the extension is labeled as one.
    """
    assert missing_from_docstring(_read(module)) == [], (
        f"{module} does not record the invariant: "
        f"{missing_from_docstring(_read(module))}"
    )


def test_a_docstring_without_the_sentence_is_caught(tmp_path: pathlib.Path) -> None:
    """The control: the predicate is watched reporting, on a scratch copy.

    Three plants, one per required element, because a predicate that only ever
    looked for the arrow would pass a docstring that dropped both citations.
    The mutation is a copy under ``tmp_path``; the shipped module is read and
    never written, and the no-edit guard below measures that.
    """
    source = _read("src/ccf/products/door.py")
    docstring = ast.get_docstring(ast.parse(source)) or ""
    assert docstring, "the control needs a module that HAS a docstring"

    for removed in (ARROW, *REQUIRED_CITATIONS):
        assert docstring.count(removed) >= 1, removed
        scratch = tmp_path / f"door_without_{abs(hash(removed))}.py"
        scratch.write_text(source.replace(removed, "", 1), encoding="utf-8")
        assert removed in missing_from_docstring(
            scratch.read_text(encoding="utf-8")
        ), (
            f"a docstring with {removed!r} removed was not reported: the"
            " recording gate is measuring nothing"
        )

    # And the shipped source, through the same predicate, is clean — so the
    # green above is this predicate's and not an empty read's.
    assert missing_from_docstring(source) == []


# --- (b) the four sabotages exist, and pytest collects them -------------------


def test_the_roster_covers_the_four_criteria_the_invariant_names() -> None:
    """Criterion 27 names four criteria; the roster answers for all four.

    A roster, not a count (``verify-rosters-not-counts``): a roster of five
    rows one of which pointed at the wrong criterion would satisfy "five"
    forever. The set of criteria covered is compared for equality against the
    four the criterion names.
    """
    assert {criterion for criterion, _module, _name in SABOTAGES} == {6, 10, 21, 22}


@pytest.mark.parametrize(
    ("criterion", "module", "name"),
    SABOTAGES,
    ids=[f"c{criterion}-{name}" for criterion, _module, name in SABOTAGES],
)
def test_every_sabotage_in_the_roster_is_defined_in_its_module(
    criterion: int, module: str, name: str
) -> None:
    """T-24.6-39: a sabotage named in a plan and absent from the tree enforces nothing."""
    defined = function_names(_read(module))
    assert name in defined, (
        f"criterion {criterion}'s sabotage {name!r} is not defined at module"
        f" scope in {module}; the guard it is supposed to hold is unwatched"
    )


@pytest.mark.parametrize(
    ("module", "name"),
    EQUIVALENCE_CONTROLS,
    ids=[f"{pathlib.Path(m).stem}-{n}" for m, n in EQUIVALENCE_CONTROLS],
)
def test_every_equivalence_control_is_defined_in_its_module(
    module: str, name: str
) -> None:
    """Criterion 22's equivalence tests are only worth their comparison's controls."""
    assert name in function_names(_read(module)), (
        f"{name!r} is not defined at module scope in {module}; criterion 22's"
        " equivalence assertion at that door rests on a comparison nothing"
        " watches"
    )


def test_the_ast_presence_check_reports_an_absent_function() -> None:
    """The control for both roster checks above.

    Watched from both sides: a name the source defines is found, and a name it
    does not define is not. Without the second half, a predicate that returned
    every possible name would satisfy every row of the roster.
    """
    source = "def test_a(): pass\n\n\ndef helper(): pass\n"
    assert function_names(source) == frozenset({"test_a", "helper"})
    assert "test_b" not in function_names(source)

    # A function nested inside another is deliberately NOT reported: pytest
    # does not collect one, so a roster satisfied by one would be satisfied by
    # a sabotage that never runs.
    nested = "def test_a():\n    def test_inner(): pass\n"
    assert function_names(nested) == frozenset({"test_a"})


def test_every_rostered_function_is_collected_by_pytest() -> None:
    """The other half of existence: pytest reaches them.

    A sabotage defined in a file pytest never collects — a module outside the
    rootdir, a name a plugin deselects, a file whose import fails — enforces
    exactly as much as a sabotage that does not exist. So the roster is held
    against what pytest actually reports, and criterion 22's own level is
    pinned by node id, because both equivalence tests are parametrized over
    three levels and the criterion is about one of them.
    """
    modules = tuple(
        sorted({module for _criterion, module, _name in SABOTAGES})
        + sorted({module for module, _name in EQUIVALENCE_CONTROLS})
    )
    collected = _collected_node_ids(tuple(sorted(set(modules))))
    assert collected, "collection reported nothing — the roster proves nothing"

    for _criterion, module, name in SABOTAGES:
        prefix = f"{module}::{name}"
        assert any(node.startswith(prefix) for node in collected), prefix

    for module, name in EQUIVALENCE_CONTROLS:
        prefix = f"{module}::{name}"
        assert any(node.startswith(prefix) for node in collected), prefix

    for _criterion, module, name in SABOTAGES:
        if _criterion != 22:
            continue
        assert f"{module}::{name}[{CRITERION_22_LEVEL}]" in collected, (
            f"{module}::{name} is collected but not at {CRITERION_22_LEVEL!r},"
            " which is the level criterion 22 is about"
        )

    # The control on the collector itself: a name nothing defines is absent.
    assert not any(
        node.startswith("tests/products/test_disclosure.py::test_nothing_defines_this")
        for node in collected
    )


# --- (c) the two documents this phase does not edit ---------------------------


@pytest.mark.parametrize("document", UNEDITED)
def test_the_document_is_unchanged_since_the_phase_base(document: str) -> None:
    """Criterion 27's last clause, and ``D-IMPL-253`` Q28, as a diff.

    CLAUDE.md's invariant lists gaining ``D-IMPL-254`` is a revision for Dave
    to order and not a phase deliverable; the whitepaper is not edited at all.
    A diff against the phase base says both, and says them about the whole
    file rather than about the lists — which is stronger and is what the
    criterion asks for.
    """
    completed = subprocess.run(
        ["git", "diff", "--quiet", PHASE_BASE, "--", document],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"{document} differs from {PHASE_BASE}: criterion 27 leaves it to Dave"
        f" to order a revision.\n{completed.stdout}{completed.stderr}"
    )


def test_the_unchanged_check_can_report_a_difference(tmp_path: pathlib.Path) -> None:
    """The control: ``git diff --quiet`` is shown answering non-zero.

    The subject is a scratch repository rather than this one, so nothing is
    written anywhere near the two documents the test above guards — and the
    predicate is still the same command with the same flags.
    """
    scratch = tmp_path / "scratch-repo"
    scratch.mkdir()

    def run(*argv: str) -> None:
        subprocess.run(
            argv, cwd=scratch, capture_output=True, text=True, check=True
        )

    run("git", "init", "-q")
    run("git", "config", "user.email", "fixture@example.invalid")
    run("git", "config", "user.name", "fixture")
    document = scratch / "DOCUMENT.md"
    document.write_text("the original\n", encoding="utf-8")
    run("git", "add", "DOCUMENT.md")
    run("git", "commit", "-q", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=scratch,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    unchanged = subprocess.run(
        ["git", "diff", "--quiet", base, "--", "DOCUMENT.md"],
        cwd=scratch,
        capture_output=True,
        text=True,
        check=False,
    )
    assert unchanged.returncode == 0

    document.write_text("the original, edited\n", encoding="utf-8")
    changed = subprocess.run(
        ["git", "diff", "--quiet", base, "--", "DOCUMENT.md"],
        cwd=scratch,
        capture_output=True,
        text=True,
        check=False,
    )
    assert changed.returncode != 0, (
        "git diff --quiet reported no difference over an edited file: the"
        " not-edited gate above is measuring nothing"
    )


def test_no_control_here_edits_the_real_source_tree() -> None:
    """Every mutation above is a copy under ``tmp_path``; the tree is read only.

    Asserted rather than assumed, because the two controls that mutate — the
    docstring plant and the scratch repository — both write files, and a plant
    that landed on the shipped path would be a sabotage nobody restored.
    """
    for module in (*INVARIANT_MODULES, *{m for _c, m, _n in SABOTAGES}):
        assert (ROOT / module).is_file(), module
    assert missing_from_docstring(_read("src/ccf/products/door.py")) == []
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", "src", "runtime"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "", (
        "src/ or runtime/ is dirty while this module's controls were running:"
        f"\n{completed.stdout}"
    )
