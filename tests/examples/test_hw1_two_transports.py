"""HW-1 answers the same question the same way over both shipped transports.

**Who reads this and what fails when it moves.** ``make ci-core`` runs it on
every invocation and the CI ``tests`` job runs it on every push. The day the
example's ``mcp+stdio`` leg stops producing what its ``inprocess`` leg produces
— or stops running at all — this goes red in the same commit that did it.

Why it exists
-------------
``D-IMPL-150`` (Dave, 2026-08-17). Plan ``17-10`` recorded as its Output that
*"*``CCF_BINDING="mcp+stdio:…"`` *runs the same* ``consume.py``\\ *"*, and it did
not: ``consume.py`` imported one adapter module, ``D-05`` ships no discovery
chain, and the documented invocation raised ``BindingError``. Nothing measured
it, because the claim lived in a plan document and in prose.

Dave's framing is what shapes this module: *the conformance suite proves
portability to us; the example proves it to an adopter.* An adopter does not run
``tests/client/conformance``. So the subject here is the **shipped example** —
the README's own commands, the shipped ``consume.py``, the shipped deployment —
driven as a subprocess exactly as a reader would drive it.

Why an empty deployment is the right subject, not a limitation
----------------------------------------------------------------
``D-32`` (Dave, 2026-08-15) forbids committing data to ``examples/``, so a clean
checkout's ``deployment/`` holds no graph. Booting one produces an empty fabric,
and the example prints ``0 of 0 assembled`` with ``D_c`` at ``1.0000`` routing to
``fail_closed``. That is the honest mechanism reporting an honest measurement,
and it is **exactly as good a subject for this claim**: two transports returning
the same governed refusal to the same question are returning the same answer.
Manufacturing data to get a prettier one would trade a claim a clean checkout
can make for a claim only a populated one can.

What is compared, and why it is the whole of stdout
-----------------------------------------------------
Every line ``consume.py`` prints, byte for byte: the answer, the measured ``D_c``
and its routing signal, the content address, the replay reference and the
expiry. Comparing only the content address would pass a transport that agreed on
the product and disagreed on the debt it was assembled under or on the decision
record that authorized it — and those are two of the four things the example
exists to show a ``SELECT`` cannot give you.

The child server's own ``INFO`` lines arrive on **stderr** and are not part of
the comparison. That is not a convenience: stdout is the answer and stderr is the
server talking, and a comparison that mixed them would fail on a logging format
change that means nothing.

The commands are read from the shipped README, never restated here
--------------------------------------------------------------------
:func:`~tests.examples.test_client_example_purity.documented_commands` already
holds the README's blocks and the ``make`` recipes to being one string. This
module takes the same blocks and *runs* them, so the strings a reader types are
the strings under test. A module carrying its own copy of the two commands would
go green on an example whose documentation had drifted away from it — which is
the precise shape of the defect being repaired here.
"""

from __future__ import annotations

import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

import pytest

from tests.examples.test_client_example_purity import (
    CLIENT_EXAMPLE_ROOTS,
    REPO_ROOT,
    documented_commands,
)

#: The example under test, and the path prefix its documented commands spell.
EXAMPLE_ROOT = CLIENT_EXAMPLE_ROOTS[0]
SHIPPED_PREFIX = EXAMPLE_ROOT.relative_to(REPO_ROOT).as_posix()

#: What a populated deployment leaves on disk. Never copied into the temporary
#: subject: a developer who has populated their own tree must not be able to
#: make this test pass — or fail — with data that is not in the repository.
NOT_COPIED = shutil.ignore_patterns(
    "graph.sqlite3", "graph.sqlite3-*", "artifact-store", "__pycache__"
)

#: The content address line, for the non-vacuity check. A run that printed
#: nothing at all would otherwise "agree" with another run that printed nothing.
ADDRESS = re.compile(r"^\s*content address\s+([0-9a-f]{64})$", re.MULTILINE)

#: How long one leg may take. Generous — the MCP leg spawns an interpreter and
#: boots a fabric in it — but bounded, because a hung stdio child that never
#: answers is a failure this suite should report rather than inherit
#: (``T-17-41`` dispositions the adapter's own no-timeout posture as accepted
#: for v0; a test runner is a different reader with a different obligation).
TIMEOUT_SECONDS = 300


def _rebase(token: str, *, example: pathlib.Path) -> str:
    """Point one command token at ``example`` instead of at the repository copy.

    A literal prefix substitution rather than a path rewrite, because an
    ``mcp+stdio`` address carries **two** paths inside one token and both must
    move together.
    """
    return token.replace(SHIPPED_PREFIX, example.as_posix())


def invocation(
    command: str, *, example: pathlib.Path
) -> tuple[str, list[str]]:
    """Split one documented command into ``(CCF_BINDING value, argv)``.

    ``shlex.split`` because an ``mcp+stdio`` address is two whitespace-separated
    tokens inside one quoted value — a naive split would tear it in half. The
    interpreter is replaced with the one running this test, so the assertion
    does not depend on a ``.venv`` existing where the README says a reader's is;
    every other token is preserved, including the pinned ``--as-of`` that makes
    the printed address reproducible.

    Returns:
        The binding address to put in the environment, and the argument vector
        to run.
    """
    tokens = shlex.split(command)
    name, separator, address = tokens[0].partition("=")
    assert (name, separator) == ("CCF_BINDING", "="), (
        f"the documented command does not begin with a `CCF_BINDING`"
        f" assignment: {command!r}"
    )
    # tokens[1] is the interpreter the README spells; the rest is the script and
    # its flags.
    return _rebase(address, example=example), [
        sys.executable,
        *(_rebase(token, example=example) for token in tokens[2:]),
    ]


def run_leg(command: str, *, example: pathlib.Path) -> str:
    """Run one documented command against ``example`` and return its stdout."""
    address, argv = invocation(command, example=example)
    completed = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env={**os.environ, "CCF_BINDING": address},
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, (
        f"`CCF_BINDING={address}` exited {completed.returncode}\n"
        f"--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}"
    )
    return completed.stdout


def parity_violations(answers: dict[str, str]) -> list[str]:
    """Every way a set of per-binding answers fails to be the same answer.

    A function of the answers rather than a bare ``assert``, so the controls can
    feed the **shipped** comparison a divergent pair and be watched failing. A
    comparison that can only ever be handed the passing pair is a comparison
    nobody has watched fail.
    """
    violations: list[str] = []
    if len(answers) < 2:
        return [
            "fewer than two transports answered, so nothing was compared —"
            f" {sorted(answers)}"
        ]
    for binding, answer in answers.items():
        if not ADDRESS.search(answer):
            violations.append(
                f"`{binding}` printed no content address, so its answer carries"
                " nothing to agree about:\n" + answer
            )
    if violations:
        return violations

    distinct = set(answers.values())
    if len(distinct) != 1:
        left, right = sorted(answers)
        violations.append(
            "the transports disagree.\n"
            f"--- {left} ---\n{answers[left]}\n"
            f"--- {right} ---\n{answers[right]}"
        )
    return violations


@pytest.fixture()
def example(tmp_path: pathlib.Path) -> pathlib.Path:
    """One private copy of the shipped example, with no data in it.

    **One** copy, deliberately: the claim is *the same deployment* reached two
    ways, and two copies would soften it into *two deployments that agree*.
    """
    root = tmp_path / EXAMPLE_ROOT.name
    shutil.copytree(EXAMPLE_ROOT, root, ignore=NOT_COPIED)
    assert not list(root.glob("deployment/graph.sqlite3*")), (
        "the copy carries a graph — `D-32` says the repository holds none, so"
        " this subject would be a developer's local data rather than the"
        " example a clean checkout ships"
    )
    return root


def test_both_documented_transports_return_the_same_answer(
    example: pathlib.Path,
) -> None:
    """``D-IMPL-150``. The same ``consume.py``, a different ``CCF_BINDING``.

    Both legs are run in the README's order — in-process first, then the child
    process — against one deployment, and every printed line must match.
    """
    answers = {
        shlex.split(command)[0].partition("=")[2]: run_leg(
            command, example=example
        )
        for command in documented_commands(EXAMPLE_ROOT)
    }
    assert not parity_violations(answers), "\n".join(parity_violations(answers))


def test_the_two_documented_transports_are_actually_different(
    example: pathlib.Path,
) -> None:
    """Non-vacuity. Two runs of one transport agreeing proves nothing.

    Reads the schemes off the same commands the test above runs, so a README
    that quietly documented ``inprocess:`` twice turns this red rather than
    making the parity assertion trivially true.
    """
    schemes = {
        shlex.split(command)[0].partition("=")[2].partition(":")[0]
        for command in documented_commands(EXAMPLE_ROOT)
    }
    assert schemes == {"inprocess", "mcp+stdio"}, (
        "the example documents commands for"
        f" {sorted(schemes)}; the portability claim is about those two"
    )


def test_the_mcp_leg_really_runs_the_examples_own_server_program(
    example: pathlib.Path,
) -> None:
    """The ``mcp+stdio`` address names a program that exists, and the SDK's none.

    ``build_egress_server`` requires five deployment values in their entirety
    (CINV-01), so a server program is the deployment's to write. An address
    pointing at a file that is not there raises ``BindingError`` at ``ask``
    time — the failure mode ``17-10``'s claim actually had — and this states
    where the shipped program lives so a move is a red check rather than a
    surprise.
    """
    mcp = next(
        command
        for command in documented_commands(EXAMPLE_ROOT)
        if "mcp+stdio:" in command
    )
    address, _ = invocation(mcp, example=example)
    program, root = (
        pathlib.Path(token) for token in shlex.split(address.partition(":")[2])
    )
    assert program.is_file(), f"{program} is not a file"
    assert root.is_dir(), f"{root} is not a directory"
    assert program.parent != root, (
        "the server program sits inside the deployment root — `D-IMPL-141`"
        " Amendment A.3 grants that directory one Python module and it is the"
        " projection"
    )


# ---------------------------------------------------------------------------
# Controls. The comparison must be watched refusing, or it is decorative.
# ---------------------------------------------------------------------------


def test_the_comparison_refuses_two_answers_that_differ() -> None:
    """A one-character divergence in the content address is a disagreement."""
    address = "a" * 64
    violations = parity_violations(
        {
            "inprocess:x": f"   content address    {address}\n",
            "mcp+stdio:y z": f"   content address    {'b' + address[1:]}\n",
        }
    )
    assert violations, "two different addresses were reported as agreement"
    assert any("disagree" in entry for entry in violations), violations


def test_the_comparison_refuses_answers_carrying_no_address() -> None:
    """**Vacuity control.** Two empty answers are not the same answer."""
    violations = parity_violations({"inprocess:x": "", "mcp+stdio:y z": ""})
    assert violations, "two empty outputs were reported as agreement"
    assert any("no content address" in entry for entry in violations), violations


def test_the_comparison_refuses_a_single_transport() -> None:
    """**Vacuity control.** One leg that ran is not two legs that agreed."""
    violations = parity_violations({"inprocess:x": "   content address    " + "a" * 64})
    assert violations, "one answer was reported as a parity result"
    assert any("nothing was compared" in entry for entry in violations), violations
