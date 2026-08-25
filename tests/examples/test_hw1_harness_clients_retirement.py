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

**`H-14` is a marking, not a deletion**, so the historical example stays and
keeps `client_adk.py`, `client_anthropic.py` and `client_bare.py`.
:func:`historical_example_violations` asserts that positively. Without it this
module would only ever push toward deleting things, and a later change could
satisfy a count by removing the historical example — the opposite of what was
ruled.

**Where that example lives changed at Phase 23, and `D-IMPL-193` is why the
change is not a contradiction.** `H-14`'s words are *"stays CI-green and is
marked historical"*. Dave clarified at the Phase 23 scope lock that
**"CI-green" means ITS TESTS KEEP PASSING** — not that the tree stays in the
always-on `examples:` aggregate — so plan `23-04` moved it, intact and
runnable, to `archive/examples/external/00-hello-context/`, and plan `23-07`
re-pointed the five assertions here that name it. Read the ruling's second
half with the first: it *"does NOT authorize deleting the tree or dropping the
tests that execute it … the five standing tests that go red on the move must
be RE-POINTED and GREEN. Satisfying this by removing a test rather than
re-pointing it is a scope breach."* Nothing here was removed, skipped or
`xfail`ed; the module collects the same sixteen tests it collected before the
move, and the "two of these names" census widened its subject rather than
lowering its count. The **prose** half of the marking obligation — the README
sentence naming the pre-Phase-17 surface and Phase 20's trio as canonical —
is `CLNT-30`'s and lands with the other README work in plan `23-09`; this
module has never asserted it and does not begin to here.

**What was carried forward, and in what shape.**
`tests/examples/test_s2_client_transport_spike.py` was deleted by plan `20-07`;
its subject moved out of `examples/` and its retiring owner (plan 16-09) was
withdrawn with Phase 16 under `docs/DECISIONS.md` `D-IMPL-152`. One assertion
in it was not about the moved directory — `test_the_shipped_external_example_is_untouched`
ran `git status --porcelain` over `examples/external/00-hello-context/` and
required it empty, because the spike *"both spawns that server and reads its
artifacts"*. `tests/examples/test_ext00_hardening.py` does not carry it, so it
is carried forward here **in full**, as two arms over one `git status` read:

* :func:`untracked_paths_violations` — a **new, non-ignored file** appeared
  under the shipped tree. A run that wrote a scratch file, a store, or a
  captured fixture into an example instead of into a temporary copy.
* :func:`modified_tracked_violations` — a **tracked file was modified and not
  committed**. This is the arm that catches a run writing *back over* a
  shipped artifact, and it is the reason both are needed:
  `make example-ext-00` spawns that server on every CI run, so an example
  that overwrites its own committed artifacts is a live risk rather than a
  hypothetical one. The untracked arm cannot see it — the file already exists
  and is already tracked.

**The verbatim guard was restored rather than narrowed, and the reason it
briefly looked unrestorable is recorded so it is not re-litigated.** During
plan `20-07` this arm reads red while the `H-14` marking to
`examples/external/00-hello-context/README.md` is *uncommitted* — which is
transient, and is resolved by committing before verifying rather than by
weakening the assertion. The guard never objected to reviewed edits: a
committed change leaves `git status` clean. It objects to **uncommitted**
ones, and an example that dirties its own tracked files during a run is
uncommitted by definition. See `docs/DECISIONS.md` `D-IMPL-166`.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The tree of shipped examples. `H-13`'s claims are scoped to it, and it stays
#: `examples/` — `H-13` is about what a directory listing of the LIVE tree
#: shows.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Where Phase 23 moved the ten condemned example trees, `H-14`'s among them
#: (`docs/DECISIONS.md` `D-IMPL-191` ruling 1, plan `23-04`). A second root
#: rather than a re-pointed one: `H-13`'s census and `H-14`'s presence check
#: are now about DIFFERENT trees, and collapsing them would let a claim about
#: one be satisfied by the other.
ARCHIVE_EXAMPLES_ROOT = REPO_ROOT / "archive" / "examples"

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

#: The example `H-14` rules stays, relative to :data:`ARCHIVE_EXAMPLES_ROOT`
#: since plan `23-04`. `D-IMPL-193` ruled that `H-14`'s *"stays CI-green"*
#: means THESE TESTS KEEP PASSING, not that the tree stays in the always-on
#: `examples:` aggregate — so the tree moved and this constant was re-pointed.
#: The same ruling refuses the other reading: it *"does not authorize dropping
#: or weakening the tests that still execute it"*.
HISTORICAL_EXAMPLE = pathlib.PurePosixPath("external/00-hello-context")

#: The three client programs `H-14`'s example must keep. Two of these names
#: also exist under `examples/hw1-harness-clients/`; that duplication is the
#: MANDATED state and is discharged by the historical marking in
#: `archive/examples/external/00-hello-context/README.md`, never by a count.
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
    mandates**: `archive/examples/external/00-hello-context/` legitimately
    keeps its own `client_adk.py` and `client_anthropic.py` alongside
    `examples/hw1-harness-clients/`'s, so the two example roots carry two of
    each name after plan `20-07` and that is the ruled state, not a violation.
    ADK and Anthropic duplication is discharged by the historical marking in
    `archive/examples/external/00-hello-context/README.md`, which
    :func:`historical_example_violations` protects from being "satisfied" by
    deletion. Do not widen this function into a general census.

    **This function keeps `examples_root` as its only subject and is called
    with the LIVE tree.** `H-13`'s sentence is about what `examples/` holds;
    the archive is not `examples/` and adding it here would answer a different
    question with the same number.
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


#: `git status --porcelain` marks an untracked entry with this status code.
#: Everything else it reports is a tracked path the working tree has changed.
UNTRACKED_STATUS_CODE = "??"


def porcelain_entries(
    repo_root: pathlib.Path, relative: pathlib.PurePosixPath
) -> list[tuple[str, str]] | None:
    """`git status --porcelain` under `relative`, as `(status code, path)`.

    ``None`` when the subject is not a directory, so each arm can report its
    own vacuity failure rather than sharing one message. One `git` read feeds
    both arms, which is what keeps them from disagreeing about the tree.
    """
    if not (repo_root / relative).is_dir():
        return None

    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", str(relative)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        (line[:2].strip() or line[:2], line[3:])
        for line in completed.stdout.splitlines()
        if line.strip()
    ]


def untracked_paths_violations(
    repo_root: pathlib.Path, relative: pathlib.PurePosixPath
) -> list[str]:
    """Arm 1 — new, non-ignored files under `relative`, by name.

    Half of the deleted spike's
    `test_the_shipped_external_example_is_untouched`. Catches a run that wrote
    a NEW file into a shipped example tree instead of into a temporary copy.
    It cannot see a run that overwrote an existing tracked artifact; that is
    :func:`modified_tracked_violations`, and both ship.
    """
    entries = porcelain_entries(repo_root, relative)
    if entries is None:
        return [
            f"{repo_root / relative} is not a directory, so `git` was never"
            " asked and nothing was checked"
        ]

    return [
        f"{path} is untracked under a shipped example tree. Something wrote"
        " into an example rather than into a temporary copy; the shipped tree"
        " is read-only to the suite"
        for code, path in entries
        if code == UNTRACKED_STATUS_CODE
    ]


def modified_tracked_violations(
    repo_root: pathlib.Path, relative: pathlib.PurePosixPath
) -> list[str]:
    """Arm 2 — tracked files under `relative` changed and not committed.

    The other half of the spike's assertion, restored rather than dropped.
    **This is the arm that catches a run writing back over a shipped
    artifact**, which the untracked arm structurally cannot: the file already
    exists and is already tracked, so `git` reports it as a modification and
    never as `??`. `make example-ext-00` spawns that example's server on every
    CI run, so the damage mode is live.

    A committed change leaves `git status` clean, so this does not object to
    reviewed edits — only to uncommitted ones, which is what a run dirtying
    its own tree produces.
    """
    entries = porcelain_entries(repo_root, relative)
    if entries is None:
        return [
            f"{repo_root / relative} is not a directory, so `git` was never"
            " asked and nothing was checked"
        ]

    return [
        f"{path} is a tracked file with uncommitted changes under a shipped"
        f" example tree (`git status` code `{code}`). A run that writes back"
        " over a committed artifact is the damage mode the untracked arm"
        " cannot see. If the edit is deliberate, commit it before verifying"
        for code, path in entries
        if code != UNTRACKED_STATUS_CODE
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
    """`H-14`: the marking is a sentence, so the example must still be here.

    Re-pointed at :data:`ARCHIVE_EXAMPLES_ROOT` by plan `23-07`, never
    relaxed: `D-IMPL-193` calls satisfying this ruling by removing a test
    rather than re-pointing it a scope breach, and the assertion below is the
    identical positive one, over the tree's new location.
    """
    violations = historical_example_violations(ARCHIVE_EXAMPLES_ROOT)
    assert not violations, "\n".join(violations)


#: The tree the deleted spike guarded, repo-relative. Under `archive/` since
#: plan `23-04`; the guard follows the tree, because what it protects is the
#: example's own committed bytes and those moved with it.
GUARDED_EXAMPLE = pathlib.PurePosixPath("archive/examples") / HISTORICAL_EXAMPLE


def test_nothing_is_untracked_under_the_historical_example() -> None:
    """Arm 1 of the carried-forward assertion, over the real tree."""
    violations = untracked_paths_violations(REPO_ROOT, GUARDED_EXAMPLE)
    assert not violations, "\n".join(violations)


def test_no_tracked_file_under_the_historical_example_is_dirty() -> None:
    """Arm 2, restored: the shipped example must not overwrite its own tree.

    Red while a deliberate edit to that example is uncommitted. That is the
    guard working, not the guard misfiring — commit before verifying.
    """
    violations = modified_tracked_violations(REPO_ROOT, GUARDED_EXAMPLE)
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


def _repo_with_a_committed_example(root: pathlib.Path) -> pathlib.PurePosixPath:
    """A real `git` repo holding one committed file under the guarded tree.

    A genuine `git init` and a genuine commit rather than a stubbed lister,
    because both arms' whole content is what `git` answers. Committed, not
    merely staged: an added-but-uncommitted file is itself a tracked
    modification, and a control built on one would go red for the wrong
    reason and prove nothing about the arm under test.
    """
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for key, value in (("user.email", "gate@example.invalid"), ("user.name", "gate")):
        subprocess.run(["git", "config", key, value], cwd=str(root), check=True)

    guarded = pathlib.PurePosixPath("examples/external/00-hello-context")
    (root / guarded).mkdir(parents=True)
    (root / guarded / "client_bare.py").write_text("shipped\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", str(guarded)], cwd=str(root), check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "shipped example"], cwd=str(root), check=True
    )
    return guarded


def test_control_an_untracked_file_under_the_guarded_tree_is_a_violation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 6 — arm 1, sabotaged in a real repo by a NEW file."""
    guarded = _repo_with_a_committed_example(tmp_path)

    assert untracked_paths_violations(tmp_path, guarded) == []

    (tmp_path / guarded / "graph.sqlite3").write_text("x", encoding="utf-8")

    violations = untracked_paths_violations(tmp_path, guarded)

    assert any("graph.sqlite3" in entry for entry in violations), violations


def test_control_a_dirty_tracked_file_under_the_guarded_tree_is_a_violation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 7 — arm 2, sabotaged by OVERWRITING a committed artifact.

    The damage mode arm 1 structurally cannot see, asserted here as such: the
    same mutation is shown to leave :func:`untracked_paths_violations` empty,
    which is what makes the second arm necessary rather than redundant.
    """
    guarded = _repo_with_a_committed_example(tmp_path)

    assert modified_tracked_violations(tmp_path, guarded) == []

    (tmp_path / guarded / "client_bare.py").write_text(
        "the server wrote back over its own artifact\n", encoding="utf-8"
    )

    violations = modified_tracked_violations(tmp_path, guarded)

    assert any("client_bare.py" in entry for entry in violations), violations
    assert untracked_paths_violations(tmp_path, guarded) == [], (
        "arm 1 must NOT see this; if it does, the two arms are not"
        " independent and CONTROL 7 is watching arm 1 twice"
    )


def test_control_a_missing_guarded_tree_is_a_violation_in_both_arms(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 8 — vacuity, for BOTH arms of the carried-forward guard.

    Written because the sabotage sweep found it missing: mutating
    :func:`porcelain_entries` to answer a missing subject with ``[]`` instead
    of ``None`` left CONTROL 6 and CONTROL 7 both green, because neither
    exercises that branch. A guard pointed at a directory that is not there
    must fail loudly; returning no findings is how a gate stops finding
    things.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    absent = pathlib.PurePosixPath("examples/external/00-hello-context")

    assert porcelain_entries(tmp_path, absent) is None

    for arm in (untracked_paths_violations, modified_tracked_violations):
        violations = arm(tmp_path, absent)
        assert any("nothing was checked" in entry for entry in violations), (
            f"{arm.__name__} reported no violation over a missing subject",
            violations,
        )


# ---------------------------------------------------------------------------
# The control deliberately NOT written, stated so it is not scored as a gap.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["client_adk.py", "client_anthropic.py"])
def test_two_of_these_names_under_examples_is_the_mandated_state(name: str) -> None:
    """There is NO control for "two ADK clients", because two is correct.

    `H-14` keeps `archive/examples/external/00-hello-context/` and `H-10` puts
    Phase 20's trio at `examples/hw1-harness-clients/`, so the two example
    roots together carry two `client_adk.py` and two `client_anthropic.py` by
    ruling. This test records that as the expected state rather than leaving
    the absence of a per-harness census looking like an oversight — and it
    fails if a later change quietly resolves the duplication by deletion
    instead of by the marking.

    **The census spans BOTH roots since plan `23-07`, and the count of two is
    unchanged.** Plan `23-04` moved `H-14`'s example under `archive/`; a
    census left scoped to `EXAMPLES_ROOT` would find one of each and could be
    made green only by lowering the expected count to one — which is the
    deletion-shaped outcome this test exists to refuse, arrived at by
    arithmetic instead of by `rm`. `D-IMPL-193` forbids weakening these
    assertions, so the subject widened and the number did not.
    """
    found = sorted(
        path.relative_to(root).as_posix()
        for root in (EXAMPLES_ROOT, ARCHIVE_EXAMPLES_ROOT)
        for path in root.rglob(name)
    )
    assert len(found) == 2, found
