"""The executable-line instrument, held to two known answers and four edges.

``24.10-04`` / ``R-03``. ``D-IMPL-282`` pins the method: *"Measure the
before/after executable-line count using the same instrument as ``R-04``."*
``R-04``'s numbers were published without a committed instrument
(``.planning/CP-05-REMEDIATION-SET.md`` — *"Measured, blank lines / comments /
docstrings excluded: cp-04's door **260**, cp-05's **204**"*), so
:mod:`tools.measure_executable_lines` reconstructs the method and this module
is what says it reconstructed the *same* method rather than a nearby one.

**The positive control is the whole point.** A counting instrument with no
known answer behind it is how a wrong number survives re-checking: every
re-run agrees with itself. So the two assertions that matter here are not the
hand-stated toy counts — they are
:func:`test_the_instrument_reproduces_r04s_published_cp05_door_number` and
:func:`test_the_instrument_reproduces_r04s_published_cp04_door_number`, which
run the instrument over the exact files ``CP-SPEC-005`` §D.10 question 2
measured and require **204** and **260** back. An instrument that does not
reproduce a known answer on known input is not a measurement.

Both control files live under ``examples/cp-04-…`` and ``examples/cp-05-…``,
which Phase 24.10's boundary holds CLOSED. They are **read** here and never
written — which is exactly the use the boundary sentence permits: *"cp-05
declarations and measured estate behavior may be used as test inputs to prove
the SDK changes."*
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from tools.measure_executable_lines import count_executable_lines

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: ``R-04``'s two published numbers and the files behind them
#: (``examples/cp-05-credit-exposure-rollup/spec/CP-SPEC-005_Credit_Exposure_Rollup.md``
#: §D.10 question 2: *"cp-04's door (``compose.py`` + ``serve.py``) | 733 |
#: **260**"* and *"cp-05's door (``serve.py``) | 334 | **204**"*). Read-only
#: subjects under the Phase 24.10 boundary.
#: The commit `R-04` measured at — the one that created cp-05's door and took
#: "the two measurements it was built to take". **The subjects are read AT THIS
#: COMMIT and not from the working tree**, because these are controls on the
#: METHOD and a live file conflates two different failures.
#:
#: Measured 2026-09-11, which is why the pin exists: the instrument reports 199
#: for cp-05's door in the working tree and 204 at this commit, so the tool was
#: correct all along and `60b0fc38` (`D-IMPL-302`/`303`, a declared number
#: crossing the wire as decimal text) simply removed five executable lines. The
#: old assertion read the live file and announced "the method has drifted" — a
#: false diagnosis it could not distinguish from a legitimate edit, and it had
#: been red on `main` long enough to stop `make gate-tools` before its third
#: leg ran at all.
#:
#: cp-04's control passed throughout and that is the confirming evidence rather
#: than a coincidence: its door is the FROZEN specimen and could not move.
R04_PUBLICATION_COMMIT = "8283deb4044245c836ecf14629867b6082c66753"

CP05_DOOR = ("examples/cp-05-credit-exposure-rollup/server/serve.py",)
CP05_DOOR_EXECUTABLE = 204
CP04_DOOR = (
    "examples/cp-04-corporate-family-tree/server/compose.py",
    "examples/cp-04-corporate-family-tree/server/serve.py",
)
CP04_DOOR_EXECUTABLE = 260

#: A source whose executable-line count is stated **by hand**, so the
#: instrument is anchored to a human reading and not only to itself. Counting
#: the lines that are neither blank, nor comment-only, nor part of a docstring
#: expression statement gives six: ``import os``, ``def f(a):``, ``b = a + 1``,
#: ``return b  # trailing``, ``class C:`` and ``x = 1``.
HAND_COUNTED = '''"""Module docstring.

Spanning three lines, all excluded.
"""

# A comment-only line.
import os


def f(a):
    """One-line docstring, excluded."""
    # Another comment.
    b = a + 1
    return b  # trailing comment does not exclude this line


class C:
    """Class docstring."""

    x = 1
'''
HAND_COUNTED_EXECUTABLE = 6


def _measured_at_publication(paths: tuple[str, ...]) -> int:
    """The instrument's total over ``paths`` AS THEY WERE at `R-04`'s commit.

    Read through `git show` rather than from the working tree. These tests ask
    *"does this instrument implement R-04's method?"*, and a live subject cannot
    answer it: a later legitimate edit to the file produces exactly the failure
    a drifted method would, and the assertion then reports the wrong cause.
    """
    total = 0
    for path in paths:
        shown = subprocess.run(
            ["git", "show", f"{R04_PUBLICATION_COMMIT}:{path}"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
        total += count_executable_lines(shown.stdout)
    return total


def test_the_instrument_reproduces_r04s_published_cp05_door_number() -> None:
    """**The positive control.** ``R-04`` published 204 for cp-05's door.

    If this fails, the instrument implements a different method from the one
    ``D-22`` pinned, and every number it produces is incomparable with
    ``R-04``'s — which is the only reason ``D-22`` named an instrument at all.
    """
    measured = _measured_at_publication(CP05_DOOR)
    assert measured == CP05_DOOR_EXECUTABLE, (
        f"the instrument measures cp-05's door at {measured} executable lines"
        f" AS R-04 MEASURED IT and R-04 published {CP05_DOOR_EXECUTABLE}; the"
        " method has drifted and no number this tool produces is comparable"
        " with R-04's. (The subject is pinned, so this cannot mean the door"
        " was edited.)"
    )


def test_the_instrument_reproduces_r04s_published_cp04_door_number() -> None:
    """**The second positive control**, and it is not redundant.

    cp-04's door is *two* files summed, so this pins the aggregation rule as
    well as the per-file rule — a per-file method that happened to match on one
    file could still sum wrongly.
    """
    measured = _measured_at_publication(CP04_DOOR)
    assert measured == CP04_DOOR_EXECUTABLE, (
        f"the instrument measures cp-04's door at {measured} executable lines"
        f" AS R-04 MEASURED IT and R-04 published {CP04_DOOR_EXECUTABLE}"
    )


def test_a_hand_stated_count_is_reproduced() -> None:
    """A human counted six; the instrument must agree with the human."""
    assert count_executable_lines(HAND_COUNTED) == HAND_COUNTED_EXECUTABLE


def test_a_multi_line_docstring_is_excluded_in_full() -> None:
    """Opening and closing quote lines included — the whole expression goes."""
    source = 'def f():\n    """One\n\n    Two\n    """\n    return 1\n'
    assert count_executable_lines(source) == 2


def test_a_trailing_comment_does_not_exclude_its_line() -> None:
    """A line with code on it is a line with code on it."""
    assert count_executable_lines("x = 1  # why\n") == 1


def test_a_file_of_blank_and_comment_lines_counts_zero() -> None:
    """No code is a zero, not a one."""
    assert count_executable_lines("\n\n# only a comment\n   \n\t\n") == 0


def test_the_count_is_stable_across_two_invocations() -> None:
    """The same bytes measure the same twice — no state, no ordering."""
    source = (
        REPO_ROOT / "examples" / "cp-05-credit-exposure-rollup" / "server" / "serve.py"
    ).read_text(encoding="utf-8")
    assert count_executable_lines(source) == count_executable_lines(source)


def test_an_attribute_docstring_is_excluded_too() -> None:
    """Any bare string expression statement is prose, wherever it sits.

    ``ast.get_docstring`` sees only the first statement of a module, class or
    function; the attribute-docstring convention puts prose after an
    assignment, and counting it as code would inflate every artifact class in
    ``src/ccf/controlplane``.
    """
    source = 'x = 1\n"""What x is.\n\nAt length.\n"""\ny = 2\n'
    assert count_executable_lines(source) == 2


def test_the_cli_prints_path_tab_count_for_a_path() -> None:
    """Runnable as a tool, so the two numbers are re-derivable by anyone."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.measure_executable_lines",
            str(CP05_DOOR[0]),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    path, count = completed.stdout.strip().split("\t")
    assert path == CP05_DOOR[0]
    # The CLI reads the WORKING TREE, so it is held against the working
    # tree's own figure rather than against R-04's published one. What this
    # control owes is that the CLI and the imported function AGREE — that
    # the tool is runnable and its numbers re-derivable by anyone — not that
    # the door has never been edited since publication.
    assert int(count) == count_executable_lines(
        (REPO_ROOT / CP05_DOOR[0]).read_text(encoding="utf-8")
    )


def test_the_cli_measures_bytes_on_stdin_under_a_caller_supplied_name() -> None:
    """``git show <rev>:<path> | … --stdin NAME`` measures a committed file.

    Without it the baseline would be a working tree somebody had begun
    editing, which is not a baseline.
    """
    completed = subprocess.run(
        [sys.executable, "-m", "tools.measure_executable_lines", "--stdin", "NAME"],
        cwd=REPO_ROOT,
        input=HAND_COUNTED,
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == f"NAME\t{HAND_COUNTED_EXECUTABLE}"


def test_a_source_that_does_not_parse_is_refused_rather_than_guessed() -> None:
    """A file the instrument cannot parse has no docstring spans to exclude.

    Falling back to a line scan would report a number that looks like every
    other number this tool prints and means something else.
    """
    with pytest.raises(SyntaxError):
        count_executable_lines("def (:\n")
