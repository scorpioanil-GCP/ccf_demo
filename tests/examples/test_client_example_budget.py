"""The client example stays small enough to read — as a red CI check.

**Who reads this number and what fails when it moves.** ``make ci-core`` reads
it on every run and the CI ``tests`` job reads it on every push. The day
``consume.py`` grows past its declared budget — or the day the README's number
is edited without the file shrinking to match — this test goes red in the same
commit. Phase 16's 722-line first example becomes a failing check rather than a
retrospective.

That last sentence is the whole design, and it is the phase's own lesson stated
as machinery: **a measurement nobody is looking at does not protect anything.**
48 config lines were measured, reported and celebrated in Phase 16 while 722
lines of Python sat unexamined beside them. So the budget is not a note in a
README; it is an assertion with a named reader.

The counting rule, decided rather than assumed
------------------------------------------------
**Physical lines, total, no exclusions.** Blank lines count. Comment lines
count. Docstring lines count. That is the strictest and simplest reading of
*"the ENTIRE example a reader studies"*, and it is the only rule a 300-line file
of one-statement-per-comment cannot game. Both padding forms get a control
below, which is what makes the rule decided rather than merely written down.

The number has exactly one home
--------------------------------
It is parsed out of the example's own README, so the figure a reader sees and
the figure the gate enforces are the same characters. Duplicating it into a
constant here would create two numbers to keep in step, and the one that drifts
is always the one nobody runs.

**The subject is a parameter, never a fixed path.** ``check_example_budget``
takes the root it checks, so every control feeds a ``tmp_path`` copy into the
**same** function the shipped assertion calls.

**Zero matches is a failure, not a pass.** A budget gate counting lines in a
tree that moved counts zero and passes — silently, and precisely when the
example it protects has been renamed away. Every vacuity case here returns a
violation, and two controls watch it happen.
"""

from __future__ import annotations

import pathlib
import re
import shutil

import pytest

from tests.examples.test_client_example_purity import (
    CLIENT_EXAMPLE_ROOTS,
    reader_visible_modules,
)

#: How the README states its budget. Deliberately tolerant of surrounding
#: markup and wording — the *number* is the contract, not the sentence — but
#: anchored on "budget" and "lines" so an unrelated figure cannot be picked up.
BUDGET_PATTERN = re.compile(
    r"declared\s+budget:?\s*\**\s*(\d+)\s*lines", re.IGNORECASE
)

#: The README each example's budget is declared in.
README_NAME = "README.md"


def physical_lines(path: pathlib.Path) -> int:
    """Total physical lines in ``path``. No exclusions, by ruling.

    ``splitlines()`` rather than counting newlines, so a final line with no
    trailing newline still counts — otherwise the counting rule would have a
    one-line hole that a single missing ``\\n`` opens.
    """
    return len(path.read_text(encoding="utf-8").splitlines())


def declared_budget(root: pathlib.Path) -> int | None:
    """The line budget ``root``'s README declares, or ``None`` if it states none."""
    readme = root / README_NAME
    if not readme.is_file():
        return None
    found = BUDGET_PATTERN.findall(readme.read_text(encoding="utf-8"))
    if len(found) != 1:
        return None
    return int(found[0])


def check_example_budget(example_root: pathlib.Path) -> list[str]:
    """Every budget violation in the example at ``example_root``, by name.

    An empty list means the example was checked and passed — never that there
    was nothing to check. A missing root, a missing README, a README declaring
    no budget (or two), and a root with no reader-visible module are each a
    violation, because each is a way this gate could otherwise report green
    while measuring nothing.
    """
    if not example_root.is_dir():
        return [
            f"{example_root} is not a directory, so no line was counted and"
            " nothing was checked"
        ]

    budget = declared_budget(example_root)
    if budget is None:
        return [
            f"{example_root.name}/{README_NAME} declares no line budget in a"
            " form this gate can parse (expected exactly one 'declared budget:"
            " <n> lines'). The number lives in the README so a reader and this"
            " gate see the same figure; with none there, this gate enforces"
            " nothing at all"
        ]

    modules = reader_visible_modules(example_root)
    if not modules:
        return [
            f"{example_root} carries no top-level `.py` module, so this gate"
            " counted zero lines and would otherwise have passed. A budget"
            " satisfied by an absent file is the vacuous pass this check exists"
            " to be immune to"
        ]

    violations: list[str] = []
    for module in modules:
        counted = physical_lines(module)
        if counted > budget:
            violations.append(
                f"{example_root.name}/{module.name} is {counted} physical"
                f" lines against a declared budget of {budget}. Blank lines and"
                " comments count — the rule is the ENTIRE example a reader"
                " studies. Either the file shrinks or the README's number"
                " changes, and changing the number is a decision somebody makes"
                " on purpose"
            )
    return violations


# ---------------------------------------------------------------------------
# Preconditions.
# ---------------------------------------------------------------------------


def test_every_gated_example_declares_a_parseable_budget() -> None:
    """Non-vacuity: the number must be findable before it can be enforced."""
    for root in CLIENT_EXAMPLE_ROOTS:
        assert declared_budget(root) is not None, (
            f"{root}/{README_NAME} declares no parseable line budget"
        )


# ---------------------------------------------------------------------------
# The budget.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "root", CLIENT_EXAMPLE_ROOTS, ids=lambda path: path.name
)
def test_the_client_example_is_within_its_declared_budget(
    root: pathlib.Path,
) -> None:
    violations = check_example_budget(root)
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Controls. Two padding forms, because the counting rule is the thing being
# decided — plus the vacuity cases a decorative budget gate passes silently.
# ---------------------------------------------------------------------------


@pytest.fixture()
def example_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """A private copy of the real example, for a control to pad."""
    root = tmp_path / "example"
    shutil.copytree(CLIENT_EXAMPLE_ROOTS[0], root)
    return root


def _pad(root: pathlib.Path, line: str, count: int = 20) -> None:
    module = reader_visible_modules(root)[0]
    with module.open("a", encoding="utf-8") as handle:
        handle.write(line * count)


def test_the_unmodified_example_passes_the_checker(
    example_copy: pathlib.Path,
) -> None:
    """The controls' baseline: refusals below must come from the padding."""
    assert check_example_budget(example_copy) == []


def test_the_gate_refuses_twenty_appended_blank_lines(
    example_copy: pathlib.Path,
) -> None:
    """Padding form 1. Blank lines count — that is half the counting rule."""
    _pad(example_copy, "\n")
    violations = check_example_budget(example_copy)
    assert violations, "20 blank lines did not breach the budget"
    assert any("physical" in entry for entry in violations), violations


def test_the_gate_refuses_twenty_appended_comment_lines(
    example_copy: pathlib.Path,
) -> None:
    """Padding form 2. Comments count — the other half.

    This is the form that would let a 300-line file of one statement per
    comment claim it was eighty lines of code.
    """
    _pad(example_copy, "# padding\n")
    violations = check_example_budget(example_copy)
    assert violations, "20 comment lines did not breach the budget"
    assert any("physical" in entry for entry in violations), violations


def test_the_readmes_number_is_what_the_gate_enforces(
    example_copy: pathlib.Path,
) -> None:
    """Editing the README's figure changes the verdict, with the file untouched.

    This is what "the number has exactly one home" means operationally: the
    gate reads the README, so lowering the README's figure below the shipped
    file's length must turn the gate red without a line of Python moving.
    """
    readme = example_copy / README_NAME
    original = declared_budget(example_copy)
    assert original is not None
    assert check_example_budget(example_copy) == []

    shipped = physical_lines(reader_visible_modules(example_copy)[0])
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            f"budget: {original} lines", f"budget: {shipped - 1} lines"
        ),
        encoding="utf-8",
    )
    assert declared_budget(example_copy) == shipped - 1, (
        "the control did not change the README's declared figure"
    )
    assert check_example_budget(example_copy), (
        "lowering the README's budget below the file's length did not turn the"
        " gate red — the gate is not reading the README"
    )


def test_the_gate_refuses_a_readme_declaring_no_budget(
    example_copy: pathlib.Path,
) -> None:
    """**Vacuity control.** A missing number must fail, not enforce nothing."""
    readme = example_copy / README_NAME
    readme.write_text(
        BUDGET_PATTERN.sub("declared ceiling: some lines", readme.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    violations = check_example_budget(example_copy)
    assert violations, "a README declaring no budget passed the budget gate"
    assert any("declares no line budget" in entry for entry in violations), violations


def test_the_gate_refuses_an_example_root_with_no_module(
    example_copy: pathlib.Path,
) -> None:
    """**Vacuity control.** Counting zero lines is not staying under budget."""
    for module in reader_visible_modules(example_copy):
        module.unlink()
    violations = check_example_budget(example_copy)
    assert violations, "an example with no module passed the budget gate"
    assert any("counted zero lines" in entry for entry in violations), violations


def test_the_gate_refuses_a_root_that_does_not_exist(
    tmp_path: pathlib.Path,
) -> None:
    """**Vacuity control.** An unresolvable subject is a failure, not a pass."""
    violations = check_example_budget(tmp_path / "was-renamed-away")
    assert violations, "a non-existent example root passed the budget gate"
    assert any("nothing was checked" in entry for entry in violations), violations
