"""HW-1 refuses an EMPTY fabric by name, identically over both shipped transports.

The negative test ``D-IMPL-245`` (2) keeps (Dave, 2026-09-03: *"seed it so the
normal example succeeds. Keep the empty-fabric refusal as a negative test."*).
Before that ruling the empty fabric was the positive test's subject, and the
example's own README taught the refusal as the thing a clean checkout
demonstrates. Dave's framing of why that is the wrong primary experience and
the right conformance check, verbatim: transport parity on a refusal is *"a
useful conformance test, but a poor primary teaching experience."*

What is refused, and why by name
--------------------------------
``24.5-L-24`` separated the empty-operator gate into two halves and this is the
RETURNED half: hw1 declares one operator, so the empty-operator *guard* passes,
and the fabric having nothing for it to return is refused as
``empty-operator-result`` (``D-IMPL-242``). It reaches ``consume.py`` as a
``RefusalEnvelope`` whose ``reason`` is that token and whose ``key`` is ``None``
— a gate refusal names no parameter — and since ``24.5.1-04`` the example prints
the ``— <key>`` suffix ONLY when there is a key. So the one line both legs must
print, byte for byte, is ``refused: empty-operator-result``. A ``— None`` on
that line is the pre-phase cosmetic defect (``24.5`` deferred item 3) coming
back, and it is refused here by name so it cannot.

Why this module cannot reuse the sibling's comparison
-----------------------------------------------------
``test_hw1_two_transports.py::run_leg`` asserts exit 0 and
``parity_violations`` refuses any answer that carries no content address —
both correct for a served product and both exactly wrong for a refusal. This
module has its own leg runner (returning the exit code rather than asserting
it) and its own comparison, with its own controls, because a comparison nobody
has watched fail is decorative. The subject fixture, the command source and
``invocation`` ARE shared: the copy shape is the sibling's ``example`` fixture
— the UNSEEDED copy, which is precisely the subject this claim is about.
"""

from __future__ import annotations

import os
import pathlib
import re
import shlex
import subprocess

import pytest

from tests.examples.test_client_example_purity import documented_commands
from tests.examples.test_hw1_two_transports import (
    EXAMPLE_ROOT,
    REPO_ROOT,
    TIMEOUT_SECONDS,
    example,  # noqa: F401 — the UNSEEDED copy fixture, re-exported for pytest
    invocation,
)

#: The one line a refusing leg must print. Anchored at both ends so a trailing
#: ``— None`` — or any other suffix — is not a match.
REFUSED = re.compile(r"^refused: empty-operator-result$", re.MULTILINE)

#: Any refusal line at all — what each leg is read for BEFORE the legs are
#: compared, so two legs refusing for different reasons are reported as a
#: disagreement rather than as two legs that printed nothing.
ANY_REFUSAL = re.compile(r"^refused: .*$", re.MULTILINE)

#: The suffix the pre-phase ``consume.py`` printed for a key-less refusal.
NONE_SUFFIX = "— None"


def run_refusing_leg(command: str, *, example: pathlib.Path) -> tuple[int, str]:
    """Run one documented command against ``example``; return (rc, stdout).

    No return-code assertion here: which code is right is the comparison's
    business, so that a leg exiting 0 on the empty copy is reported as a named
    violation rather than as a fixture error.
    """
    address, argv = invocation(command, example=example)
    completed = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env={**os.environ, "CCF_BINDING": address},
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    return completed.returncode, completed.stdout


def refusal_parity_violations(answers: dict[str, tuple[int, str]]) -> list[str]:
    """Every way a set of per-binding refusals fails to be the same refusal.

    In order: nothing compared; a leg that did not exit 1; a leg that printed no
    refusal line; a leg that printed the ``— None`` suffix; two legs whose
    refusal lines differ; and a refusal line — the one both agreed on — that
    does not name ``empty-operator-result``. Each is a distinct string so the
    controls below can name the one they expect.
    """
    if len(answers) < 2:
        return [
            "fewer than two transports answered, so nothing was compared —"
            f" {sorted(answers)}"
        ]
    violations: list[str] = []
    for binding, (returncode, stdout) in answers.items():
        if returncode != 1:
            violations.append(
                f"`{binding}` exited {returncode}, not 1 — an empty fabric is"
                f" refused, and a refusal exits 1:\n{stdout}"
            )
    if violations:
        return violations

    lines: dict[str, str] = {}
    for binding, (_, stdout) in answers.items():
        match = ANY_REFUSAL.search(stdout)
        if match is None:
            violations.append(
                f"`{binding}` printed no refusal line, so its answer carries"
                f" nothing to agree about:\n{stdout}"
            )
            continue
        if NONE_SUFFIX in stdout:
            violations.append(
                f"`{binding}` printed a None key — a gate refusal names no"
                f" key, and the example prints a suffix only for one:\n{stdout}"
            )
        lines[binding] = match.group(0)
    if violations:
        return violations

    if len(set(lines.values())) != 1:
        left, right = sorted(answers)
        violations.append(
            "the transports disagree on the refusal.\n"
            f"--- {left} ---\n{answers[left][1]}\n"
            f"--- {right} ---\n{answers[right][1]}"
        )
        return violations
    (line,) = set(lines.values())
    if not REFUSED.fullmatch(line):
        violations.append(
            f"both transports refused with {line!r}, which does not name"
            " `empty-operator-result` — the returned half of the"
            " empty-operator gate is what an empty fabric trips"
        )
    return violations


def test_both_documented_transports_refuse_an_empty_fabric_by_name(
    example: pathlib.Path,
) -> None:
    """``D-IMPL-245`` (2), ``D-IMPL-242``. The unseeded copy, both legs, one line."""
    answers = {
        shlex.split(command)[0].partition("=")[2]: run_refusing_leg(
            command, example=example
        )
        for command in documented_commands(EXAMPLE_ROOT)
    }
    violations = refusal_parity_violations(answers)
    assert not violations, "\n".join(violations)


def test_the_two_refusing_transports_are_actually_different() -> None:
    """Non-vacuity. Two runs of one transport refusing alike proves nothing."""
    schemes = {
        shlex.split(command)[0].partition("=")[2].partition(":")[0]
        for command in documented_commands(EXAMPLE_ROOT)
    }
    assert schemes == {"inprocess", "mcp+stdio"}, (
        "the example documents commands for"
        f" {sorted(schemes)}; the refusal-parity claim is about those two"
    )


# ---------------------------------------------------------------------------
# Controls. The comparison must be watched refusing, or it is decorative.
# ---------------------------------------------------------------------------


def test_the_comparison_refuses_two_refusals_that_differ() -> None:
    """Two legs refusing for different reasons is not the same refusal."""
    violations = refusal_parity_violations(
        {
            "inprocess:x": (1, "refused: empty-operator-result\n"),
            "mcp+stdio:y": (1, "refused: empty-operator-guard\n"),
        }
    )
    assert violations, "two different refusal lines were reported as agreement"
    assert any("disagree" in entry for entry in violations), violations


def test_the_comparison_refuses_an_agreed_refusal_naming_the_wrong_gate() -> None:
    """Agreement on the wrong token is not the empty-fabric refusal."""
    line = "refused: empty-operator-guard\n"
    violations = refusal_parity_violations(
        {"inprocess:x": (1, line), "mcp+stdio:y": (1, line)}
    )
    assert violations, "an agreed refusal naming the guard half was accepted"
    assert any("does not name" in entry for entry in violations), violations


def test_the_comparison_refuses_a_single_transport() -> None:
    """**Vacuity control.** One leg that refused is not two legs that agreed."""
    violations = refusal_parity_violations(
        {"inprocess:x": (1, "refused: empty-operator-result\n")}
    )
    assert violations, "one refusal was reported as a parity result"
    assert any("nothing was compared" in entry for entry in violations), violations


def test_the_comparison_refuses_empty_output() -> None:
    """**Vacuity control.** Two legs that exited 1 and said nothing agreed on nothing."""
    violations = refusal_parity_violations({"inprocess:x": (1, ""), "mcp+stdio:y": (1, "")})
    assert violations, "two empty outputs were reported as agreement"
    assert any("no refusal line" in entry for entry in violations), violations


def test_the_comparison_refuses_a_none_key() -> None:
    """The pre-phase ``— None`` suffix is refused by name, not by inequality."""
    line = "refused: empty-operator-result — None\n"
    violations = refusal_parity_violations(
        {"inprocess:x": (1, line), "mcp+stdio:y": (1, line)}
    )
    assert violations, "a `— None` suffix on both legs was reported as agreement"
    assert any("None key" in entry for entry in violations), violations


def test_the_comparison_refuses_a_leg_that_served() -> None:
    """A leg exiting 0 on the empty copy is the seeded subject, not this one."""
    violations = refusal_parity_violations(
        {
            "inprocess:x": (0, "   content address    " + "a" * 64 + "\n"),
            "mcp+stdio:y": (1, "refused: empty-operator-result\n"),
        }
    )
    assert violations, "a leg that exited 0 was reported as a refusal"
    assert any("exited 0, not 1" in entry for entry in violations), violations
