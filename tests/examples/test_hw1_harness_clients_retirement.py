"""The Phase 16 orphans are out of `examples/`, and the historical example is not.

`H-13` and `H-14` of
`.planning/phases/20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a/20-CONTEXT.md`
discharge ROADMAP ruling 3 — *the tree must not carry three ADK and two
LangGraph clients at mixed vintages* — by two different mechanisms, and this
module asserts both, in the numbered-`CONTROL` shape
`tests/client/test_surface.py` sets.

**`H-13` is a move, and the claim it licenses is exactly one sentence wide.**
Its own words are *"afterwards `examples/` holds exactly one LangGraph
client"*. The census below is therefore scoped to LangGraph and to nothing
else. See :func:`langgraph_client_count` for why a wider census would be a
gate that goes red against the tree this phase was ruled to produce.

**`H-14` is a marking, not a move**, so `examples/external/00-hello-context/`
stays and keeps `client_adk.py`, `client_anthropic.py` and `client_bare.py`.
:func:`historical_example_violations` asserts that positively. Without it this
module would only ever push toward deleting things, and a later change could
satisfy a count by removing the historical example — the opposite of what was
ruled.

**What was carried forward, and in what shape.**
`tests/examples/test_s2_client_transport_spike.py` was deleted by plan `20-07`;
its subject moved out of `examples/` and its retiring owner (plan 16-09) was
withdrawn with Phase 16 under `docs/DECISIONS.md` `D-IMPL-152`. One assertion
in it was not about the moved directory — it checked that the spike, which
spawned `examples/external/00-hello-context/`'s server and read its artifacts,
had written nothing into that shipped tree. `tests/examples/test_ext00_hardening.py`
does not carry it. It is carried forward here as
:func:`untracked_paths_violations` — **narrowed to untracked files** rather
than the spike's `git status --porcelain`, because a working-tree-cleanliness
assertion in a module that is not the thing doing the writing goes red for any
legitimate uncommitted edit, including the `H-14` marking plan `20-07` makes
in the very same example. Untracked files are the damage mode the original was
protecting against — a test writing *into* the shipped tree — and a deliberate
edit to a tracked file is not.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The tree of shipped examples. Every claim below is scoped to it.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Where the Phase 16 orphans went. Outside `examples/`, outside every
#: `tools/lints/__main__.py::RULE_TREE_SCOPE` tree, and unpublished — `mkdocs.yml`
#: reads only `public/`.
RETIRED_ROOT = REPO_ROOT / "docs" / "retired" / "16-external-consumers"

#: The directory name `H-13` condemns, as it sat under `examples/`.
CONDEMNED_DIRECTORY_NAME = "s2-01-external-consumers"

#: The written record the retired destination must carry. This repository's
#: precedent for retiring things is deletion PLUS a record
#: (`docs/surface/examples/ERGO-03-FROZEN.md`), so a record-less quarantine is
#: a partial retirement, not a completed one.
RETIREMENT_RECORD_NAME = "README.md"

#: The client program `H-13`'s claim is about.
LANGGRAPH_CLIENT_NAME = "client_langgraph.py"

#: `H-13`'s claim, as a number: "afterwards `examples/` holds exactly one
#: LangGraph client".
MAXIMUM_LANGGRAPH_CLIENTS = 1

#: The example `H-14` rules stays, relative to `EXAMPLES_ROOT`.
HISTORICAL_EXAMPLE = pathlib.PurePosixPath("external/00-hello-context")

#: The three client programs `H-14`'s example must keep. Two of these names
#: also exist under `examples/hw1-harness-clients/`; that duplication is the
#: MANDATED state and is discharged by the historical marking in
#: `examples/external/00-hello-context/README.md`, never by a count.
HISTORICAL_EXAMPLE_CLIENTS = (
    "client_adk.py",
    "client_anthropic.py",
    "client_bare.py",
)


# ---------------------------------------------------------------------------
# The properties, each taking its subject as a parameter.
# ---------------------------------------------------------------------------


def retirement_violations(
    examples_root: pathlib.Path, retired_root: pathlib.Path
) -> list[str]:
    """Every way the `H-13` move is incomplete, by name.

    An empty list means the move was checked and holds — never that there was
    nothing to check. A missing ``examples_root`` is itself a violation: a
    comparison over a tree that is not there finds no condemned directory and
    would otherwise report green while measuring nothing.
    """
    violations: list[str] = []

    if not examples_root.is_dir():
        violations.append(
            f"{examples_root} is not a directory, so no example tree was"
            " walked and nothing was checked. A vacuous pass is the failure"
            " mode this branch exists to be immune to"
        )
        return violations

    condemned = examples_root / CONDEMNED_DIRECTORY_NAME
    if condemned.exists():
        violations.append(
            f"{condemned} still exists under the example tree. `H-13` moves"
            " the Phase 16 orphans OUT of `examples/` entirely, because"
            " leaving them in place — even marked — leaves files that look"
            " live in a directory listing"
        )

    if not retired_root.is_dir():
        violations.append(
            f"{retired_root} is missing, so the condemned material has no"
            " declared destination. `H-13` is a move, not a deletion: the two"
            " client programs carry shapes Phase 20 inherited"
        )
        return violations

    record = retired_root / RETIREMENT_RECORD_NAME
    if not record.is_file():
        violations.append(
            f"{record} is missing. This repository retires things by deletion"
            " PLUS a written record; a directory of quarantined code with no"
            " record is a partial retirement and is exactly what looks live"
            " to the next reader"
        )

    return violations


def langgraph_client_count(examples_root: pathlib.Path) -> int:
    """How many `client_langgraph.py` programs sit anywhere under `examples_root`.

    **Scoped to LangGraph deliberately, and the narrowness is the point.**
    `H-13`'s claim is *"afterwards `examples/` holds exactly one LangGraph
    client"* — a 2→1 reduction and nothing wider. A per-harness census
    refusing any count above one would go **red against the tree `H-14`
    mandates**: `examples/external/00-hello-context/` legitimately keeps its
    own `client_adk.py` and `client_anthropic.py` alongside
    `examples/hw1-harness-clients/`'s, so `examples/` carries two of each name
    after plan `20-07` and that is the ruled state, not a violation. ADK and
    Anthropic duplication is discharged by the historical marking in
    `examples/external/00-hello-context/README.md`, which
    :func:`historical_example_violations` protects from being "satisfied" by
    deletion. Do not widen this function into a general census.
    """
    return len(list(examples_root.rglob(LANGGRAPH_CLIENT_NAME)))


def langgraph_census_violations(examples_root: pathlib.Path) -> list[str]:
    """`H-13`'s 2→1 reduction, as a violation list. Vacuity guarded."""
    if not examples_root.is_dir():
        return [
            f"{examples_root} is not a directory, so the census counted"
            " nothing and would otherwise have reported one LangGraph client"
            " by finding zero"
        ]

    found = sorted(
        path.relative_to(examples_root).as_posix()
        for path in examples_root.rglob(LANGGRAPH_CLIENT_NAME)
    )
    counted = langgraph_client_count(examples_root)

    if counted < MAXIMUM_LANGGRAPH_CLIENTS:
        return [
            f"{examples_root} holds {counted} `{LANGGRAPH_CLIENT_NAME}`"
            f" against the {MAXIMUM_LANGGRAPH_CLIENTS} `H-13` leaves behind."
            " The reduction is 2→1, not 2→0: Phase 20's leg 3 is the surviving"
            " one and its absence is a regression, not compliance"
        ]

    if counted > MAXIMUM_LANGGRAPH_CLIENTS:
        return [
            f"{examples_root} holds {counted} LangGraph clients against the"
            f" {MAXIMUM_LANGGRAPH_CLIENTS} `H-13` permits: {', '.join(found)}."
            " ROADMAP ruling 3 refuses two LangGraph clients at mixed"
            " vintages; the Phase 16 one is retired out of `examples/`"
        ]

    return []


def historical_example_violations(examples_root: pathlib.Path) -> list[str]:
    """`H-14`: the historical example stays, with all three of its clients.

    Asserted positively so that no later change can satisfy a count by
    deleting the example. `H-14` rejected retiring it — that would delete
    eight passing CI assertions (auth refusal, dual serve-path byte equality,
    replay reproduction) which have nothing to do with Phase 20.
    """
    example = examples_root / HISTORICAL_EXAMPLE

    if not example.is_dir():
        return [
            f"{example} is missing. `H-14` rules that this example STAYS,"
            " running and CI-green, marked historical in its README. Ruling 3"
            " is satisfied there by a sentence, not by a move and not by a"
            " deletion"
        ]

    return [
        f"{example / name} is missing. `H-14` keeps this example's three"
        " client programs; the ADK and Anthropic duplication with"
        " `examples/hw1-harness-clients/` is discharged by the historical"
        " marking, so removing a client here does not satisfy anything"
        for name in HISTORICAL_EXAMPLE_CLIENTS
        if not (example / name).is_file()
    ]


def untracked_paths_violations(
    repo_root: pathlib.Path, relative: pathlib.PurePosixPath
) -> list[str]:
    """Untracked, non-ignored files under `relative`, by name.

    Carried forward from the deleted spike's
    `test_the_shipped_external_example_is_untouched`, narrowed from
    `git status --porcelain` to untracked files only — see this module's
    docstring for why. A test that writes a new file into a shipped example
    tree is the damage mode; a reviewed edit to a tracked file is not.
    """
    if not (repo_root / relative).is_dir():
        return [
            f"{repo_root / relative} is not a directory, so `git` was never"
            " asked and nothing was checked"
        ]

    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", str(relative)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    stray = [line for line in completed.stdout.splitlines() if line.strip()]
    if not stray:
        return []

    return [
        f"{path} is untracked under a shipped example tree. Something wrote"
        " into an example rather than into a temporary copy; the shipped tree"
        " is read-only to the suite"
        for path in stray
    ]


# ---------------------------------------------------------------------------
# The shipped assertions, over the real tree.
# ---------------------------------------------------------------------------


def test_the_phase_16_orphans_are_out_of_the_example_tree() -> None:
    """`H-13`: moved, with a destination and a written record."""
    violations = retirement_violations(EXAMPLES_ROOT, RETIRED_ROOT)
    assert not violations, "\n".join(violations)


def test_the_example_tree_holds_exactly_one_langgraph_client() -> None:
    """`H-13`'s claim in its own words, and no wider claim than that."""
    violations = langgraph_census_violations(EXAMPLES_ROOT)
    assert not violations, "\n".join(violations)


def test_the_historical_example_keeps_all_three_of_its_clients() -> None:
    """`H-14`: the marking is a sentence, so the example must still be here."""
    violations = historical_example_violations(EXAMPLES_ROOT)
    assert not violations, "\n".join(violations)


def test_nothing_is_untracked_under_the_historical_example() -> None:
    """The carried-forward assertion, over the tree the spike used to guard."""
    violations = untracked_paths_violations(
        REPO_ROOT, pathlib.PurePosixPath("examples") / HISTORICAL_EXAMPLE
    )
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Non-vacuity: the numbers the gate compares against must be findable.
# ---------------------------------------------------------------------------


def test_the_census_counts_something_rather_than_nothing() -> None:
    """A ceiling over a walk that finds nothing is a gate wired to nothing."""
    assert langgraph_client_count(EXAMPLES_ROOT) == MAXIMUM_LANGGRAPH_CLIENTS


# ---------------------------------------------------------------------------
# The controls, each handing a synthetic subject to the same function.
# ---------------------------------------------------------------------------


def _examples_tree(root: pathlib.Path, *relative: str) -> pathlib.Path:
    """Build a synthetic `examples/` tree holding each path in `relative`."""
    examples = root / "examples"
    for entry in relative:
        target = examples / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    examples.mkdir(parents=True, exist_ok=True)
    return examples


def _retired_tree(root: pathlib.Path, *, with_record: bool) -> pathlib.Path:
    """Build a synthetic retired destination, with or without its record."""
    retired = root / "docs" / "retired" / "16-external-consumers"
    retired.mkdir(parents=True, exist_ok=True)
    (retired / LANGGRAPH_CLIENT_NAME).write_text("", encoding="utf-8")
    if with_record:
        (retired / RETIREMENT_RECORD_NAME).write_text("", encoding="utf-8")
    return retired


def test_control_a_surviving_condemned_directory_is_a_violation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 1 — the move did not happen, so the gate must not be green."""
    examples = _examples_tree(
        tmp_path, f"{CONDEMNED_DIRECTORY_NAME}/{LANGGRAPH_CLIENT_NAME}"
    )
    retired = _retired_tree(tmp_path, with_record=True)

    violations = retirement_violations(examples, retired)

    assert any(CONDEMNED_DIRECTORY_NAME in entry for entry in violations), violations


def test_control_a_retired_destination_without_a_record_is_a_violation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 2 — a record-less quarantine is a partial retirement."""
    examples = _examples_tree(tmp_path)
    retired = _retired_tree(tmp_path, with_record=False)

    violations = retirement_violations(examples, retired)

    assert any(RETIREMENT_RECORD_NAME in entry for entry in violations), violations


def test_control_a_missing_example_tree_is_a_violation_not_an_empty_finding(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 3 — vacuity. A walk over a missing tree must fail, not pass."""
    absent = tmp_path / "examples"
    retired = _retired_tree(tmp_path, with_record=True)

    violations = retirement_violations(absent, retired)

    assert any("nothing was checked" in entry for entry in violations), violations
    assert langgraph_census_violations(absent), "the census reported green on nothing"


def test_control_two_langgraph_clients_are_a_named_violation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 4 — the state `H-13` exists to refuse, and it names both."""
    examples = _examples_tree(
        tmp_path,
        f"{CONDEMNED_DIRECTORY_NAME}/{LANGGRAPH_CLIENT_NAME}",
        f"hw1-harness-clients/{LANGGRAPH_CLIENT_NAME}",
    )

    violations = langgraph_census_violations(examples)

    assert langgraph_client_count(examples) == 2
    assert any("LangGraph" in entry for entry in violations), violations


def test_control_a_historical_example_missing_its_adk_client_is_a_violation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 5 — the `H-14` side. Deleting the example satisfies nothing.

    The control on the OTHER direction, and the reason it exists: without it a
    retirement gate only ever pushes toward removing things.
    """
    examples = _examples_tree(
        tmp_path,
        *(
            f"{HISTORICAL_EXAMPLE}/{name}"
            for name in HISTORICAL_EXAMPLE_CLIENTS
            if name != "client_adk.py"
        ),
    )

    violations = historical_example_violations(examples)

    assert any("client_adk.py" in entry for entry in violations), violations


def test_control_an_untracked_file_under_the_guarded_tree_is_a_violation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 6 — the carried-forward assertion, sabotaged in a real repo.

    A genuine `git init` rather than a stubbed lister, because the assertion's
    whole content is what `git` answers.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    guarded = pathlib.PurePosixPath("examples/external/00-hello-context")
    (tmp_path / guarded).mkdir(parents=True)
    (tmp_path / guarded / "client_bare.py").write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "add", "--", str(guarded)], cwd=str(tmp_path), check=True
    )

    assert untracked_paths_violations(tmp_path, guarded) == []

    (tmp_path / guarded / "graph.sqlite3").write_text("x", encoding="utf-8")

    violations = untracked_paths_violations(tmp_path, guarded)

    assert any("graph.sqlite3" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# The control deliberately NOT written, stated so it is not scored as a gap.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["client_adk.py", "client_anthropic.py"])
def test_two_of_these_names_under_examples_is_the_mandated_state(name: str) -> None:
    """There is NO control for "two ADK clients", because two is correct.

    `H-14` keeps `examples/external/00-hello-context/` and `H-10` puts Phase
    20's trio at `examples/hw1-harness-clients/`, so `examples/` carries two
    `client_adk.py` and two `client_anthropic.py` by ruling. This test records
    that as the expected state rather than leaving the absence of a per-harness
    census looking like an oversight — and it fails if a later change quietly
    resolves the duplication by deletion instead of by the marking.
    """
    found = sorted(
        path.relative_to(EXAMPLES_ROOT).as_posix()
        for path in EXAMPLES_ROOT.rglob(name)
    )
    assert len(found) == 2, found
