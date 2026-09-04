"""HW-1's README ``### Expected output`` fence IS the program's output, byte for byte.

The verbatim-output discipline, `public/reference/specifications/example_delivery.md`
§7 (lines 274-322): *"Every code fence that looks like program output must be
the program's exact text, or be explicitly labeled an excerpt"*, verified by
capturing the documented command's output, extracting the fence, testing the
block for equality, and running *"a control: a plausible string that must NOT
be found. If it is, the instrument is broken and the greens mean nothing."*
Phase 24.5.1 criterion 11 makes that a CI check for this README.

Why whole-block equality and not containment
--------------------------------------------
The pre-phase fence elided the middle of the answer with a ``...`` line and
quoted an address from a run nobody could reproduce. The recipe's containment
rule exists for *labeled* excerpts; this fence is labeled as the whole of the
in-process command's stdout, so the comparison is equality after stripping
exactly one trailing newline from each side — the newline ``print`` adds and a
fence does not carry — and nothing else. A leading blank line is part of the
output (``consume.py`` prints one before the question) and is therefore part of
the fence.

The subject is the seeded copy ``test_hw1_two_transports.py`` builds, driven by
the README's own first documented command, so the string a reader types is the
string under test and the output a reader sees is the output compared.
"""

from __future__ import annotations

import difflib
import pathlib
import re

from tools.docs_tests._prose import _FENCE_RE

from tests.examples.test_client_example_purity import documented_commands
from tests.examples.test_hw1_two_transports import (
    EXAMPLE_ROOT,
    example,  # noqa: F401 — `seeded_example` is built on it
    run_leg,
    seeded_example,  # noqa: F401 — the populated copy fixture
)

#: The heading the fence sits under, and where its section ends.
EXPECTED_OUTPUT_HEADING = re.compile(r"^### Expected output\s*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{1,3} ", re.MULTILINE)

#: The pre-phase output — what an EMPTY fabric printed before `24.5-L-24`. It is
#: the must-not-match control: plausible, once true, and never to be found in a
#: seeded run's output.
MUST_NOT_MATCH = "0 of 0 assembled"


def expected_output_fence(readme_text: str) -> str:
    """The body of the one fenced block under ``### Expected output``.

    Lines are taken verbatim between the opening and closing fence — never
    whitespace-collapsed, which is why this does not reuse
    :func:`tools.docs_tests._prose.paragraphs` (its ``raw`` collapses
    whitespace, by design, for a wording gate). The fence regex IS that
    module's, so the two agree on what a fence is.
    """
    heading = EXPECTED_OUTPUT_HEADING.search(readme_text)
    assert heading is not None, "the README has no `### Expected output` heading"
    section = readme_text[heading.end():]
    following = NEXT_HEADING.search(section)
    if following is not None:
        section = section[: following.start()]

    blocks: list[str] = []
    inside: list[str] | None = None
    marker = ""
    for line in section.splitlines():
        match = _FENCE_RE.match(line)
        if inside is None:
            if match is not None:
                inside, marker = [], match.group("marker")
            continue
        if (
            match is not None
            and match.group("info") == ""
            and match.group("marker")[0] == marker[0]
            and len(match.group("marker")) >= len(marker)
        ):
            blocks.append("\n".join(inside))
            inside = None
            continue
        inside.append(line)
    assert inside is None, "the `### Expected output` fence is never closed"
    assert len(blocks) == 1, (
        f"the `### Expected output` section holds {len(blocks)} fenced blocks;"
        " it holds exactly one, the program's output"
    )
    return blocks[0]


def _strip_one_newline(text: str) -> str:
    return text[:-1] if text.endswith("\n") else text


def fence_violations(fence: str, stdout: str) -> list[str]:
    """Every way the fence fails to be the run's output.

    A function of two strings so the controls can hand the shipped comparison a
    divergent pair and be watched failing.
    """
    if not fence.strip() or not stdout.strip():
        return [
            "one side is empty, so nothing was compared —"
            f" fence={fence!r} stdout={stdout!r}"
        ]
    expected = _strip_one_newline(fence)
    actual = _strip_one_newline(stdout)
    if expected != actual:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile="README.md ### Expected output",
                tofile="consume.py stdout",
                lineterm="",
            )
        )
        return [f"the fence and the run differ.\n{diff}"]
    return []


def _readme() -> str:
    return (EXAMPLE_ROOT / "README.md").read_text(encoding="utf-8")


def test_the_readme_fence_is_the_in_process_commands_output(
    seeded_example: pathlib.Path,
) -> None:
    """Criterion 11. The first documented command, run; the fence, compared."""
    in_process = documented_commands(EXAMPLE_ROOT)[0]
    assert in_process.startswith('CCF_BINDING="inprocess:'), in_process
    stdout = run_leg(in_process, example=seeded_example)
    fence = expected_output_fence(_readme())
    assert MUST_NOT_MATCH not in stdout, (
        f"the seeded run printed {MUST_NOT_MATCH!r} — the empty-fabric output"
    )
    violations = fence_violations(fence, stdout)
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Controls. The comparison must be watched refusing, or it is decorative.
# ---------------------------------------------------------------------------


def test_the_comparison_refuses_one_altered_hex_digit() -> None:
    """A one-character divergence in the content address is a difference."""
    fence = expected_output_fence(_readme())
    address = re.search(r"content address\s+([0-9a-f]{64})", fence)
    assert address is not None, "the shipped fence carries no content address"
    digit = address.group(1)[0]
    altered = fence.replace(address.group(1), ("0" if digit != "0" else "1") + address.group(1)[1:], 1)
    assert altered != fence, "the altered-digit control did not change anything"
    violations = fence_violations(altered, fence + "\n")
    assert violations, "one altered hex digit was reported as equality"
    assert any("differ" in entry for entry in violations), violations


def test_the_must_not_match_control_is_reported_when_planted() -> None:
    """The pre-phase string, planted into a copy of the fence, is a difference."""
    fence = expected_output_fence(_readme())
    assert MUST_NOT_MATCH not in fence, (
        f"the shipped fence carries {MUST_NOT_MATCH!r}, the empty-fabric output"
    )
    planted = re.sub(r"\d+ of \d+ assembled", MUST_NOT_MATCH, fence, count=1)
    assert MUST_NOT_MATCH in planted, "the plant did not land"
    violations = fence_violations(planted, fence + "\n")
    assert violations, "a planted must-not-match string was reported as equality"
    assert any("differ" in entry for entry in violations), violations


def test_the_comparison_refuses_empty_output() -> None:
    """**Vacuity control.** An empty run does not equal anything."""
    fence = expected_output_fence(_readme())
    violations = fence_violations(fence, "")
    assert violations, "empty stdout was reported as equality"
    assert any("empty" in entry for entry in violations), violations
