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

Per module, and now over two roots
-----------------------------------
The budget is enforced against **each** reader-visible module, never against
their sum. That mattered little while
:data:`~tests.examples.test_client_example_purity.CLIENT_EXAMPLE_ROOTS` held one
root with one ``consume.py``; it is the whole rule now that
``examples/hw1-harness-clients`` carries three client programs, because a sum
would let one bloated client hide behind two small ones.

**This module gained that second root without a line changing here**, by
importing ``CLIENT_EXAMPLE_ROOTS`` and parametrizing over it. That is convenient
and it is also the risk: an automatically-armed gate is a gate nobody chose to
arm, and every control below the fixtures builds its subject from
``CLIENT_EXAMPLE_ROOTS[0]`` — the hw1 root. ``C-20-9`` at the foot of the file
is the one that watches the *new* root fail.

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
    HARNESS_ROOT,
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


# ---------------------------------------------------------------------------
# C-20-9 — the control for the root this gate was newly ARMED against.
#
# Nothing above watches `examples/hw1-harness-clients`. Every control in this
# module builds its doctored subject from ``CLIENT_EXAMPLE_ROOTS[0]``, which is
# the hw1 root, and they were all green on the day the harness root joined
# :data:`CLIENT_EXAMPLE_ROOTS` — which is precisely the shape of a gate that is
# armed on paper and unwatched in fact.
#
# `CLNT-12` reads "every parity, guard and example gate this phase adds", and a
# gate newly armed against a root whose README the same plan authors is a gate
# that plan added in the only sense that matters. `T-20-41`.
#
# What this control CANNOT catch, stated so nobody mistakes it for cover: a
# budget set too high. Padding past 300 and padding past 3000 both fail here.
# The only defence against a formality is the number itself, so the README
# declares 300 against a largest client of 288 — twelve lines of headroom,
# recorded rather than left as slack.
# ---------------------------------------------------------------------------


@pytest.fixture()
def harness_example_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """A private copy of the **harness-clients** example, for ``C-20-9``."""
    root = tmp_path / "harness-example"
    shutil.copytree(
        HARNESS_ROOT, root, ignore=shutil.ignore_patterns("__pycache__")
    )
    return root


def test_c20_9_the_gate_refuses_an_over_budget_harness_client(
    harness_example_copy: pathlib.Path,
) -> None:
    """``C-20-9`` — pad one client program past the budget and watch it refuse.

    Built from :data:`HARNESS_ROOT`, deliberately, not from
    ``CLIENT_EXAMPLE_ROOTS[0]``. The whole point is that this control's subject
    is the root the two padding controls above do not reach.

    The violation must **name the padded module**: this root carries three
    client programs and the budget is enforced per module, so a gate that
    reported "the example is over budget" without saying which file would leave
    a reader diffing three of them.
    """
    assert check_example_budget(harness_example_copy) == [], (
        "the harness copy was already over budget, so the padding below proves"
        " nothing"
    )
    modules = reader_visible_modules(harness_example_copy)
    assert len(modules) == 3, (
        f"expected three client programs, found {[m.name for m in modules]}"
    )

    # The LAST module, not the first. Every other root this gate walks holds
    # exactly one reader-visible program, so "check `modules[0]`" is a passing
    # implementation everywhere else in the tree and a hole exactly here. This
    # control is the one that would notice.
    padded = modules[-1]
    budget = declared_budget(harness_example_copy)
    assert budget is not None
    overshoot = budget - physical_lines(padded) + 1
    with padded.open("a", encoding="utf-8") as handle:
        handle.write("# filler\n" * overshoot)
    assert physical_lines(padded) > budget, "the control did not breach the budget"

    violations = check_example_budget(harness_example_copy)
    assert violations, f"{padded.name} over the declared budget passed the gate"
    assert any(padded.name in entry for entry in violations), violations
    assert any("physical" in entry for entry in violations), violations

    # The other two are untouched and must not be blamed for it.
    for innocent in modules[:-1]:
        assert not any(innocent.name in entry for entry in violations), (
            f"{innocent.name} is within budget and was named anyway: {violations}"
        )
