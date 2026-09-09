"""Count a Python file's executable lines — ``R-04``'s method, made re-runnable.

``24.10-04`` / ``R-03``. **SDK-defined tooling** (CLAUDE.md §11): this measures
a property of the repository, not a property of CCF, so it cites this project's
own governance rather than a whitepaper section.

Why this exists
---------------

``D-IMPL-282`` (Dave, 2026-09-08) rules the ``R-03`` measurement's method by
naming another measurement's: *"Measure the before/after executable-line count
using the same instrument as ``R-04``."* ``R-04``'s numbers are published in
``examples/cp-05-credit-exposure-rollup/spec/CP-SPEC-005_Credit_Exposure_Rollup.md``
§D.10 question 2 and quoted in ``.planning/CP-05-REMEDIATION-SET.md``:

    *"Measured, blank lines / comments / docstrings excluded: cp-04's door
    **260**, cp-05's **204** — a 22% reduction."*

**No instrument was committed with them.** So "the same instrument" had to be
reconstructed from the stated method, and a reconstruction nobody can check is
an assertion. This module is the reconstruction; ``tools/lints/tests/
test_measure_executable_lines.py`` is the check, and it is a **positive
control** rather than a self-consistency test: it runs this code over the exact
two doors ``R-04`` measured and requires 204 and 260 back. Both are reproduced
exactly, which is what makes an ``R-03`` number comparable with an ``R-04``
number rather than merely similar to one.

The method, stated so it can be disagreed with
----------------------------------------------

A physical line counts when it is **all three** of: not blank, not
comment-only, and not part of a *docstring expression statement*. Concretely:

* **Blank** is ``str.strip()`` empty — spaces and tabs included.
* **Comment-only** is a stripped line beginning ``#``. A line with code and a
  trailing comment has code on it and counts.
* **Docstring expression statement** is any :class:`ast.Expr` whose value is a
  string constant, excluded across its **whole span** including the opening and
  closing quote lines. That is deliberately broader than
  :func:`ast.get_docstring`, which sees only the first statement of a module,
  class or function: the attribute-docstring convention (a bare string after an
  assignment) is prose by every reading of ``R-04``'s *"docstrings excluded"*,
  and this repository uses it heavily in ``src/ccf/controlplane``.

Two consequences worth stating rather than discovering. A line inside a
multi-line **non**-docstring string literal that happens to begin with ``#`` is
excluded, because the scan is textual; and a source that does not parse is
**refused** rather than measured by a line scan, because a degraded number that
prints in the same format as a good one is worse than no number.

What this is not
----------------

It is **not** ``tools/measure_examples.py``. That tool measures the AST
mechanical-surface audit — ``removable`` and ``relocatable`` — for ERGO-03, a
different question with different keys, and its own docstring warns that
relocation is not removal. The two share no code on purpose: coupling them
would let one silently redefine the other.

Usage::

    python -m tools.measure_executable_lines PATH [PATH ...]
    git show <rev>:<path> | python -m tools.measure_executable_lines --stdin NAME

Either form prints one ``path<TAB>count`` line per subject. The ``--stdin``
form is what makes a *committed* baseline measurable without a checkout, so the
before-number is the file as it was rather than a working tree somebody had
begun editing.
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys
from collections.abc import Sequence

__all__ = ["count_executable_lines", "main"]


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Every physical line occupied by a docstring expression statement.

    Walks the whole tree rather than consulting :func:`ast.get_docstring` at
    three node types, so an attribute docstring — a bare string statement after
    an assignment — is excluded on the same terms as a module docstring. Both
    are prose; only one of them is what ``get_docstring`` can see.
    """
    occupied: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        occupied.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return occupied


def count_executable_lines(source: str) -> int:
    """How many of ``source``'s physical lines carry code.

    Args:
        source: The full text of one Python module.

    Returns:
        The count of lines that are not blank, not comment-only and not part of
        a docstring expression statement.

    Raises:
        SyntaxError: ``source`` does not parse. Refused rather than
            approximated: without an AST there are no docstring spans to
            exclude, so a fallback line scan would over-count by however much
            prose the file carries and would print in the same format as a
            trustworthy number.
    """
    excluded = _docstring_lines(ast.parse(source))
    counted = 0
    for number, line in enumerate(source.splitlines(), start=1):
        if number in excluded:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        counted += 1
    return counted


def main(argv: Sequence[str] | None = None) -> int:
    """Print ``path<TAB>count`` for each subject named on the command line."""
    parser = argparse.ArgumentParser(
        description=(
            "Count executable lines (blank lines, comments and docstrings"
            " excluded) — the method R-04 measured cp-04's and cp-05's doors"
            " by, reconstructed and positive-controlled against its published"
            " 260 and 204."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="Python files to measure",
    )
    parser.add_argument(
        "--stdin",
        default=None,
        metavar="NAME",
        help=(
            "measure the bytes on standard input, reporting them under NAME —"
            " so `git show <rev>:<path>` can be measured without a checkout"
        ),
    )
    arguments = parser.parse_args(argv)

    if arguments.stdin is None and not arguments.paths:
        parser.error("name at least one PATH, or pass --stdin NAME")

    if arguments.stdin is not None:
        print(f"{arguments.stdin}\t{count_executable_lines(sys.stdin.read())}")

    for path in arguments.paths:
        source = pathlib.Path(path).read_text(encoding="utf-8")
        print(f"{path}\t{count_executable_lines(source)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
