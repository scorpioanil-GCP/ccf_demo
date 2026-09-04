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

Why the subject is SEEDED, and how
-----------------------------------
``D-32`` (Dave, 2026-08-15) forbids committing producer output to ``examples/``
— a populated ``graph.sqlite3``, an ``artifact-store/`` — so a clean checkout's
``deployment/`` holds no graph, and the temporary copy this module makes holds
none either (``NOT_COPIED``). What the checkout DOES hold is the example's own
declared input, ``runner/signal-batch.yaml``, and the program that interprets
it, ``runner/seed.py`` (``D-IMPL-245`` amendment 2, Dave, 2026-09-03: *"the seed
should be treated as declared input to the example, not as a hidden bootstrap
feature of the SDK"*; ``D-IMPL-163`` narrows ``D-32`` to producer output). The
``seeded_example`` fixture runs that program inside the copy, through the
fabric's single writer, before either leg boots — so the claim a clean checkout
can make is now the SUCCESSFUL one: the answer, the measured ``D_c`` routing to
``forced_llm``, the content address, the replay reference and the expiry the
README says the example demonstrates.

Two transports returning the same governed *refusal* on an empty fabric is
still a useful conformance claim, and it did not go away: it moved to
``test_hw1_empty_fabric_refusal.py``, which runs both legs against the UNSEEDED
copy (``D-IMPL-245`` (2); the refusal is ``empty-operator-result`` by name,
``D-IMPL-242``). Dave's framing of the split: transport parity on a refusal is
*"a useful conformance test, but a poor primary teaching experience."*

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

from ccf.client.adapters.binding_document import load_binding_document

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

    A literal prefix substitution rather than a path rewrite, so it stays
    correct for a token carrying more than one path. Since ``18.1-02`` an
    ``mcp+stdio`` address carries exactly one — the deployment root — but the
    substitution is the cheaper rule either way, and it moves the script path
    and the binding by the same code.
    """
    return token.replace(SHIPPED_PREFIX, example.as_posix())


def invocation(
    command: str, *, example: pathlib.Path
) -> tuple[str, list[str]]:
    """Split one documented command into ``(CCF_BINDING value, argv)``.

    ``shlex.split`` rather than a hand-rolled split, so a quoted value survives
    whatever a scheme puts inside it — and so the ``CCF_BINDING=`` assignment is
    recovered as one token rather than reconstructed. The interpreter is
    replaced with the one running this test, so the assertion does not depend on
    a ``.venv`` existing where the README says a reader's is; every other token
    is preserved, including the pinned ``--as-of`` that makes the printed
    address reproducible.

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


def seed_copy(root: pathlib.Path) -> None:
    """Run the example's own seed program inside the copy at ``root``.

    The program takes no arguments and seeds the deployment beside itself, so
    running the COPY's ``runner/seed.py`` populates the copy's deployment and
    never the repository's. ``check=True``: a seed that fails is this module's
    failure to report, not a condition to run the legs under.
    """
    subprocess.run(
        [sys.executable, str(root / "runner" / "seed.py")],
        cwd=REPO_ROOT,
        env={**os.environ},
        check=True,
        timeout=TIMEOUT_SECONDS,
    )
    assert (root / "deployment" / "graph.sqlite3").is_file(), (
        "the seed program exited 0 but left no graph in the copy's deployment"
    )


@pytest.fixture()
def seeded_example(example: pathlib.Path) -> pathlib.Path:
    """The same private copy, populated from its own declared input.

    Built ON the unseeded ``example`` fixture rather than beside it, so the
    positive and negative modules share one copy shape and differ only in
    whether the seed ran.
    """
    seed_copy(example)
    return example


def test_both_documented_transports_return_the_same_answer(
    seeded_example: pathlib.Path,
) -> None:
    """``D-IMPL-150``. The same ``consume.py``, a different ``CCF_BINDING``.

    Both legs are run in the README's order — in-process first, then the child
    process — against one seeded deployment, and every printed line must match.
    """
    answers = {
        shlex.split(command)[0].partition("=")[2]: run_leg(
            command, example=seeded_example
        )
        for command in documented_commands(EXAMPLE_ROOT)
    }
    assert not parity_violations(answers), "\n".join(parity_violations(answers))


def test_the_seeded_run_reports_the_demonstrated_signal(
    seeded_example: pathlib.Path,
) -> None:
    """The README's demonstration sentence, measured.

    The README says the filings' spread of ages under the one-year half-life
    makes freshness decay and routes the answer to ``forced_llm``. That is a
    claim about the shipped input document and the shipped deployment together,
    so it is asserted on the in-process leg's stdout rather than trusted.
    """
    in_process = documented_commands(EXAMPLE_ROOT)[0]
    stdout = run_leg(in_process, example=seeded_example)
    assert ADDRESS.search(stdout), f"no content address was printed:\n{stdout}"
    assert "forced_llm" in stdout, (
        "the seeded run did not route to `forced_llm`, which is the signal the"
        f" README says the example demonstrates:\n{stdout}"
    )


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
    seeded_example: pathlib.Path,
) -> None:
    """The documented address names a deployment that DECLARES a program.

    Needs no data, but the documented address must name a deployment that
    SERVES, so it stays on the seeded copy rather than the empty one.

    ``build_egress_server`` requires five deployment values in their entirety
    (CINV-01), so a server program is the deployment's to write. Since
    ``18.1-02`` the address no longer names it: the address is the root, one
    token, and the program is the root's own ``server:`` key. So the chain the
    documented command actually walks is asserted link by link — the token is a
    directory, the document loads, it declares a ``server:``, and that
    declaration is a file — because a break anywhere along it reaches an adopter
    as a ``BindingError`` at ``ask`` time, which is the failure mode ``17-10``'s
    claim actually had.
    """
    mcp = next(
        command
        for command in documented_commands(EXAMPLE_ROOT)
        if "mcp+stdio:" in command
    )
    address, _ = invocation(mcp, example=seeded_example)
    tokens = shlex.split(address.partition(":")[2])
    assert len(tokens) == 1, (
        f"the documented `mcp+stdio` address states {len(tokens)} tokens; it"
        f" states one, the deployment root — {tokens}"
    )
    root = pathlib.Path(tokens[0])
    assert root.is_dir(), f"{root} is not a directory"

    document = load_binding_document(root)
    assert document.server is not None, (
        f"{root}'s `binding.yaml` declares no `server:`, so the documented"
        " `mcp+stdio` command cannot run — the address names no program and"
        " the deployment states none either"
    )
    assert document.server.is_file(), f"{document.server} is not a file"
    assert document.server.parent != root, (
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
            "mcp+stdio:y": f"   content address    {'b' + address[1:]}\n",
        }
    )
    assert violations, "two different addresses were reported as agreement"
    assert any("disagree" in entry for entry in violations), violations


def test_the_comparison_refuses_answers_carrying_no_address() -> None:
    """**Vacuity control.** Two empty answers are not the same answer."""
    violations = parity_violations({"inprocess:x": "", "mcp+stdio:y": ""})
    assert violations, "two empty outputs were reported as agreement"
    assert any("no content address" in entry for entry in violations), violations


def test_the_comparison_refuses_a_single_transport() -> None:
    """**Vacuity control.** One leg that ran is not two legs that agreed."""
    violations = parity_violations({"inprocess:x": "   content address    " + "a" * 64})
    assert violations, "one answer was reported as a parity result"
    assert any("nothing was compared" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# `D-12`'s structural criterion: one file, one concern.
#
# `D-12` refused a line budget for this server — Dave has called it temporary
# and not the focus, and a second declared budget would put a server line-count
# back inside the reader's own document. What it ruled instead is *structural*:
# `serve.py` holds only door concerns and the composition lives in the module
# beside it. Nothing below counts a line.
#
# It is asserted here rather than in `test_client_example_purity.py` because
# that module's subject is the example's READER-VISIBLE modules, which `server/`
# is deliberately not — while this module already asserts things about this
# example's shipped server (`document.server.parent != root`).
# ---------------------------------------------------------------------------

#: The directory the criterion is about.
SERVER_DIR = EXAMPLE_ROOT / "server"

#: How many Python modules "one file, one concern" leaves in it: the door and
#: the boot. Compared with `!=`, never `>`, for `assert_one_python_module`'s
#: reason — a gate that stops checking without going red is the defect.
SERVER_MODULE_COUNT = 2

#: The door's own governance document. `serve.py` must still name it, or the
#: door's governance document moved out with the composition and nobody can say
#: which document the running server interpreted.
DOOR_DOCUMENT = "egress-door.yaml"

#: The one basename this directory may never hold.
#: `tests/examples/test_artifact_schema_headers.py::EXAMPLE_ROOT_MARKER` is
#: `run.py` and is matched by an **rglob**, so a `server/run.py` would register
#: `server/` as an example root and fail the artifacts bijection over a
#: directory that owns no `artifacts/`.
FORBIDDEN_MODULE = "run.py"


def server_shape_violations(server: pathlib.Path) -> list[str]:
    """Every way ``server`` fails `D-12`'s criterion, by name.

    A function over a directory rather than a bare ``assert`` on the shipped
    one, so the controls can hand the **shipped** check a divergent subject and
    be watched failing. A check that can only ever be handed the passing subject
    is a check nobody has watched fail.
    """
    violations: list[str] = []
    modules = sorted(path.name for path in server.glob("*.py"))

    if len(modules) != SERVER_MODULE_COUNT:
        violations.append(
            f"{server} holds {len(modules)} Python modules, not"
            f" {SERVER_MODULE_COUNT} — `D-12` leaves the door in `serve.py` and"
            f" the composition in the module beside it: {modules}"
        )
    if FORBIDDEN_MODULE in modules:
        violations.append(
            f"{server} holds a `{FORBIDDEN_MODULE}` —"
            " `test_artifact_schema_headers.py` treats a directory directly"
            f" holding `{FORBIDDEN_MODULE}` as an example root, by rglob, and"
            " this directory owns no `artifacts/` to satisfy the bijection with"
        )

    door = server / "serve.py"
    if not door.is_file():
        violations.append(
            f"{door} is not there, so the directory holds no door at all"
        )
    elif DOOR_DOCUMENT not in door.read_text(encoding="utf-8"):
        violations.append(
            f"{door} no longer names `{DOOR_DOCUMENT}` — the door's own"
            " governance document left with the composition, and nothing now"
            " says which document the running server interpreted"
        )
    return violations


def copied_server(tmp_path: pathlib.Path, name: str) -> pathlib.Path:
    """A private copy of the shipped ``server/``, for a control to diverge.

    Copied rather than mutated in place: a control that edited ``examples/`` and
    reverted would leave the repository dirty the moment it failed.
    """
    subject = tmp_path / name
    shutil.copytree(SERVER_DIR, subject, ignore=NOT_COPIED)
    return subject


def test_the_shipped_server_holds_one_file_per_concern() -> None:
    """`D-12`. The door and the boot, and no third thing."""
    violations = server_shape_violations(SERVER_DIR)
    assert not violations, "\n".join(violations)


def test_the_shape_check_refuses_a_third_module(
    tmp_path: pathlib.Path,
) -> None:
    """**Sabotage control.** A third concern arriving in the directory."""
    subject = copied_server(tmp_path, "third-module")
    original = sorted(path.name for path in subject.glob("*.py"))
    (subject / "extras.py").write_text('"""A third concern."""\n', encoding="utf-8")
    mutated = sorted(path.name for path in subject.glob("*.py"))
    assert mutated != original, "the third-module control did not change anything"

    violations = server_shape_violations(subject)
    assert violations, "a third Python module was reported as one file per concern"
    assert any("Python modules, not" in entry for entry in violations), violations


def test_the_shape_check_refuses_a_run_py(tmp_path: pathlib.Path) -> None:
    """**Sabotage control.** The `run.py` landmine, which `compose.py` avoids."""
    subject = copied_server(tmp_path, "run-py")
    original = sorted(path.name for path in subject.glob("*.py"))
    # RENAMED rather than added, so the module COUNT stays at two and this
    # control can only be satisfied by the forbidden-basename rule. A control
    # that also tripped the count rule would not tell the two apart.
    (subject / "compose.py").rename(subject / FORBIDDEN_MODULE)
    mutated = sorted(path.name for path in subject.glob("*.py"))
    assert mutated != original, "the run.py control did not change anything"
    assert len(mutated) == SERVER_MODULE_COUNT, mutated

    violations = server_shape_violations(subject)
    assert violations, f"a `{FORBIDDEN_MODULE}` was reported as an acceptable shape"
    assert any(FORBIDDEN_MODULE in entry for entry in violations), violations


def test_the_shape_check_refuses_a_door_that_dropped_its_document(
    tmp_path: pathlib.Path,
) -> None:
    """**Sabotage control.** The door's governance document moving out silently."""
    subject = copied_server(tmp_path, "no-door-document")
    door = subject / "serve.py"
    original = door.read_text(encoding="utf-8")
    door.write_text(original.replace(DOOR_DOCUMENT, "somewhere-else.yaml"), encoding="utf-8")
    mutated = door.read_text(encoding="utf-8")
    assert mutated != original, "the door-document control did not change anything"

    violations = server_shape_violations(subject)
    assert violations, f"a `serve.py` naming no `{DOOR_DOCUMENT}` was accepted"
    assert any(DOOR_DOCUMENT in entry for entry in violations), violations


def test_the_shape_check_refuses_an_empty_directory(
    tmp_path: pathlib.Path,
) -> None:
    """**Vacuity control.** Zero modules is not two modules.

    The count is compared with ``!=`` rather than ``>`` for exactly this: a
    directory that lost both modules would satisfy ``> 2`` forever.
    """
    subject = tmp_path / "empty"
    subject.mkdir()
    violations = server_shape_violations(subject)
    assert violations, "an empty directory was reported as one file per concern"
    assert any("Python modules, not" in entry for entry in violations), violations
