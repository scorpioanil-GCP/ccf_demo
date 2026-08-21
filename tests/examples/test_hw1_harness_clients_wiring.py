"""``example-hw1-harness-clients`` is wired into the target CI actually runs.

A target nobody runs is criterion 6's own *documented but never run* failure
mode, one level out: `examples/hw1-harness-clients` can be perfect, its runner
green under a hand invocation, and still prove nothing about the always-on
pipeline if `make examples` never reaches it. The examples job runs bare
`make examples` (`.github/workflows/ci.yml`), so membership on that target's
prerequisite line is the whole of what makes this example a gate.

**Every property here is a module-level function taking its subject as a
parameter**, which is the design of the module and not a style choice. The
defect class it avoids spans three plans of Phase 17: a control specified as
*"copy the subject, break it, assert the test fails"* against an assertion that
reads a **fixed path**. The copy is never what the assertion looks at, so the
control passes for the wrong reason and the property stays unproven — the
discipline ``tests/client/test_surface.py`` states at length and this module
inherits. So :func:`examples_prerequisites` takes Makefile TEXT and
:func:`wiring_violations` takes a prerequisite tuple; the shipped assertion
hands them the real `Makefile`, and `CONTROL 1`-`CONTROL 3` hand the very same
functions a doctored one and watch them fail.
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The target this plan wired in. Named once so the shipped assertion and the
#: controls cannot drift into checking different strings.
TARGET = "example-hw1-harness-clients"

#: The prerequisite line whose membership is the gate.
AGGREGATE = "examples:"


def examples_prerequisites(makefile_text: str) -> tuple[str, ...]:
    """The prerequisite tokens on the ``examples:`` line of ``makefile_text``.

    The trailing ``## …`` help comment is stripped, because a target named only
    inside the help text is not a prerequisite and must not read as one. A text
    carrying no ``examples:`` line at all yields an empty tuple, which
    :func:`wiring_violations` refuses rather than passes — see `CONTROL 3`.
    """
    for line in makefile_text.splitlines():
        if not line.startswith(AGGREGATE):
            continue
        body = line[len(AGGREGATE) :].split("##", 1)[0]
        return tuple(token for token in body.split() if token)
    return ()


def wiring_violations(prerequisites: Sequence[str], target: str) -> list[str]:
    """Every way ``target`` fails to be a prerequisite of the aggregate.

    Two violations, and the second is the one that matters: an EMPTY
    prerequisite tuple is refused explicitly, because a membership test over
    nothing reports "not present" for a reason that has nothing to do with the
    target — a renamed aggregate, a reformatted line, a parser that stopped
    matching — and a bare ``in`` test cannot tell those apart from the defect
    it exists to catch.
    """
    violations: list[str] = []
    if not prerequisites:
        violations.append(
            f"the `{AGGREGATE}` line yielded no prerequisites at all, so a"
            " membership test over it says nothing about any target"
        )
        return violations
    if target not in prerequisites:
        violations.append(
            f"`{target}` is not a prerequisite of `{AGGREGATE}`; the examples"
            f" job runs `make examples`, so a target off this line never runs"
            f" in CI. Present: {list(prerequisites)}"
        )
    return violations


def test_the_harness_clients_example_is_a_prerequisite_of_examples() -> None:
    """The shipped assertion: CI's `make examples` reaches this example."""
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    violations = wiring_violations(examples_prerequisites(makefile_text), TARGET)
    assert violations == [], "\n".join(violations)


def test_a_missing_target_is_a_violation() -> None:
    """CONTROL 1 — a synthetic ``examples:`` line without the target goes red.

    The doctored subject is passed to the SAME function the shipped assertion
    calls, so this control cannot pass by reading something else.
    """
    doctored = "examples: example-00 example-ext-00 ## Run the examples\n"
    assert wiring_violations(examples_prerequisites(doctored), TARGET)


def test_an_empty_prerequisite_tuple_is_a_violation() -> None:
    """CONTROL 2 — vacuity is named, not silently reported as absence."""
    violations = wiring_violations((), TARGET)
    assert violations
    assert "no prerequisites at all" in violations[0]


def test_a_makefile_with_no_examples_line_is_a_violation() -> None:
    """CONTROL 3 — a text carrying no aggregate at all does not pass quietly.

    Without this, a rename of the aggregate target would make
    :func:`examples_prerequisites` return an empty tuple forever and the gate
    would report a clean tree over a line it can no longer find.
    """
    doctored = "lint:\n\techo hi\n\nci: lint\n"
    assert examples_prerequisites(doctored) == ()
    assert wiring_violations(examples_prerequisites(doctored), TARGET)


def test_the_help_text_is_not_read_as_a_prerequisite() -> None:
    """The ``##`` comment is stripped, so a name in the help text is not wiring.

    Not numbered as a control because it guards the parser rather than the
    property, but it is the difference between this gate reading the
    dependency graph and reading a sentence about it.
    """
    doctored = f"examples: example-00 ## Run everything including {TARGET}\n"
    assert examples_prerequisites(doctored) == ("example-00",)
    assert wiring_violations(examples_prerequisites(doctored), TARGET)
