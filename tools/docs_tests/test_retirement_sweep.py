"""The standing gate over `tools/retirement_sweep.py`.

A sweep that runs once and writes a file is a snapshot. Plans 16-15 (wave 8),
16-17 (wave 10) and 16-18 (wave 11) delete into the couplings this sweep
measures, and they re-run it rather than reading the committed file — so what
has to be gated is the *sweep*, not the snapshot.

Four properties, each with a recorded failure behind it:

* **CWD-independence.** WR-04 is the recorded failure where a CWD-relative
  walk scanned zero files and the gate passed over nothing. The walk is
  re-run from an unrelated directory and required to be identical.
* **Non-vacuity.** A scan that found nothing would satisfy every assertion
  about what it found. Both the file set and the coupling set are required to
  be non-empty at HEAD, and the fourteen files the phase already knows about
  are required by name — a floor, not a ceiling.
* **Filter polarity, both directions.** A retiring path inside a docstring is
  documentary; the same path in a `pathlib.Path(...)` call is live. Getting
  this wrong in either direction is a defect: dropping the documentary hit
  loses four of the fourteen files (two conformance modules, `perf/suites/
  common.py` and `perf/synth/artifacts/controlplane.yaml`), each of which is
  already in an owning plan's `files_modified`; treating it as live tells an
  owner a docstring will turn the build red.
* **Shape coverage.** All four no-path-token shapes are proven on synthetic
  modules built under `tmp_path`, not merely observed in the checked-in tree.
  The third shape survived a full review round undetected and the fourth
  survived two; a gate that only asserts against HEAD would go green the day
  a refactor moved the last instance.

The synthetic fixtures build their paths out of `RETIREMENT_SCHEDULE` rather
than writing them as literals, so this module contributes no rows to the sweep
it gates and cannot drift from the schedule it is testing against.

SDK-defined tooling (CLAUDE.md §3.1): a gate over the phase's own retirement
work, not fabric mechanism.
"""

from __future__ import annotations

import collections.abc
import dataclasses
import pathlib
import subprocess
import sys
import textwrap
from typing import Sequence

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# The repo root joins `sys.path` here for the same reason the sweep puts it
# there: this module must import and behave identically from any CWD, and a
# `from tools...` import cannot bootstrap the package that contains it.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.retirement_sweep import (  # noqa: E402
    DOCUMENTARY,
    LIVE,
    REPORT_PATH,
    RETIREMENT_SCHEDULE,
    Retirement,
    SHAPE_COUNT_CONSTANT,
    SHAPE_COUNT_SCAN_FUNCTION,
    SHAPE_DOCSTRING,
    SHAPE_INDIRECT_EXECUTION,
    SHAPE_INLINE_TREE_WITNESS,
    UNOWNED,
    Coupling,
    Sweep,
    Unexaminable,
    count_coupling_rows,
    main,
    record_unexaminable,
    indirect_execution_rows,
    inline_tree_witness_rows,
    iter_source_files,
    outside_swept_trees,
    python_hits,
    read_text,
    render,
    reset_unexaminable,
    sweep,
    unexaminable,
)

#: The prefixes an *example directory* row can carry. `archive/examples/` is
#: here because plan 23-04 moved the ten condemned trees there and plan 23-10
#: re-pointed the schedule at their new home; a predicate that still admitted
#: only `examples/` would match nothing for waves 8, 10 and 11, `next()` would
#: raise `StopIteration` DURING COLLECTION, and this whole module would vanish
#: — which reads exactly like a module that passed. Watched: with the schedule
#: re-pointed and this tuple left at `("examples/",)`, `--collect-only` reports
#: **0 tests collected, 1 error** where the phase base reports **47**.
#:
#: `examples/` is KEPT rather than replaced: the `17-08` `s1` rows still live
#: under `examples/` (`D-05` leaves them alone), and a later wave that adds an
#: unmoved tree at waves 8/10/11 must not re-break collection.
EXAMPLE_DIR_PREFIXES: tuple[str, ...] = ("examples/", "archive/examples/")


def _example_dir_for_wave(wave: int) -> str:
    """One retiring example directory from `wave`, taken from the schedule.

    Derived so this module carries no retiring-path token of its own — the
    reason the fixtures are computed rather than written down.
    """
    return next(
        entry.path
        for entry in RETIREMENT_SCHEDULE
        if entry.wave == wave and entry.path.startswith(EXAMPLE_DIR_PREFIXES)
    )


#: One retiring example directory per wave, taken from the schedule so this
#: module carries no retiring-path token of its own.
WAVE_8 = _example_dir_for_wave(8)
WAVE_10 = _example_dir_for_wave(10)
WAVE_11 = _example_dir_for_wave(11)

#: The known instances, assembled by hand across three review rounds. The
#: sweep exists because hand assembly kept missing rows, so this is the floor
#: of what it must find — finding more means the hand list was incomplete.
KNOWN_COUPLED_FILES: tuple[str, ...] = (
    "README.md",
    "perf/suites/common.py",
    "perf/suites/crossproc/conftest.py",
    "perf/synth/artifacts/controlplane.yaml",
    "tests/cli/test_schema_export.py",
    "tests/conformance/test_a3_discharge.py",
    "tests/conformance/test_harness_portability.py",
    "tests/examples/test_artifact_schema_headers.py",
    "tests/lints/test_examples_scope.py",
    "tests/perf_smoke/test_smoke.py",
    "tests/products/test_gate_two_call_shape.py",
    "tests/products/test_required_operators_guard.py",
    "tools/measure_examples.py",
    "tools/publish_scan_tests/test_publish_scan.py",
)

_HEAD: Sweep | None = None


def head() -> Sweep:
    """The HEAD sweep, measured once — the walk is the expensive part."""
    global _HEAD  # noqa: PLW0603 - a one-shot measurement shared by the module
    if _HEAD is None:
        _HEAD = sweep()
    return _HEAD


def _write(base: pathlib.Path, relative: str, source: str) -> pathlib.Path:
    path = base / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_walk_reads_a_non_empty_tree() -> None:
    """The sweep read files. Without this every assertion below is vacuous."""
    files = iter_source_files()
    assert files, f"no files walked from {REPO_ROOT}"
    assert len(files) > 100, f"only {len(files)} files walked — the walk is truncated"


def test_the_sweep_finds_couplings_at_head() -> None:
    """At HEAD there are couplings. A clean sweep here would be a broken sweep."""
    result = head()
    assert result.files_scanned > 0
    assert result.rows, "no couplings found — the sweep is reporting clean over a tree that has them"


def test_every_known_coupled_file_is_found() -> None:
    """The fourteen hand-assembled instances are a floor, and it is met."""
    found = {row.file for row in head().rows}
    missing = sorted(name for name in KNOWN_COUPLED_FILES if name not in found)
    assert not missing, (
        "the sweep missed files three review rounds already identified as"
        " coupled: " + ", ".join(missing)
    )


# ---------------------------------------------------------------------------
# The schedule must still be about the tree — plan 23-10, criterion 10.
#
# The gap these two close, named by the researcher as S-13 and reproduced
# before they were written: leave the schedule pointed at the OLD `examples/…`
# paths after plan 23-04's move and the sweep reports a confident **384 rows
# across 117 files at EXIT 0** over ten directories that are not there, while
# **46 of the 47 tests in this module pass**. The one red is
# `test_the_committed_report_is_current`, which is red whenever the report has
# not been regenerated and therefore cannot tell a stale schedule from a stale
# snapshot. That is the Phase 22.1 defect exactly — a tool reporting clean
# because it did not look — arriving in the table the tool reads.
# ---------------------------------------------------------------------------

#: The prefix an archived tree's path carries. A PREFIX, not a retiring path:
#: this module still spells no retiring path of its own, and every concrete
#: path below is taken from `RETIREMENT_SCHEDULE`.
ARCHIVE_PREFIX = "archive/examples/"


def _no_archived_tree(schedule: Sequence[Retirement]) -> str:
    """The two ways a schedule can name no archived tree, told apart.

    **ONE clause, two diagnoses, and the shape is a sabotage result rather
    than a preference.** Both predicates below first shipped with a separate
    `if not schedule` early return in front of this condition. Sabotage
    S-16v(c) deleted `archive_sweep_problems`' copy and **every control stayed
    GREEN** — because an empty schedule contains no archived path either, so
    the emptiness guard was detecting nothing this condition was not already
    detecting. It was a second check kept for the look of it. Its only real
    contribution was the MESSAGE, which is preserved here: "empty" and "names
    only survivors" are very different states to find a schedule in, and a
    refusal that cannot tell them apart sends its reader to the wrong place.
    """
    if not schedule:
        return "the schedule is EMPTY and schedules nothing at all"
    return f"the schedule is SILENT about the archive — no path under {ARCHIVE_PREFIX}"


def scheduled_path_problems(schedule: Sequence[Retirement]) -> list[str]:
    """Every way the schedule's own existence claim fails to hold.

    The claim is the schedule's own comment, quoted rather than paraphrased so
    that this is visibly the comment's enforcement and not a new rule:

        "Each path was confirmed to exist before being listed — the unowned-row
        gate is fail-closed, and a schedule naming a path that is not there is
        the same class of defect as one that omits a path."

    Nothing asserted it until plan 23-10, which is why plan 23-04 could move
    ten directories out from under the table and leave every gate green.

    Takes the schedule as an ARGUMENT — this module's idiom — so the controls
    can point it at a synthetic one instead of reasoning about what it would
    do. **The anti-vacuity clauses live INSIDE the predicate** for the same
    reason: a check whose emptiness guard sits in the caller is a check a
    second caller can lose.

    Four clauses, and the last two are the halves that matter:

    1. An empty schedule. `all(...)` over nothing is `True`.
    2. A schedule naming no archived tree. This is the *silence* case, and it
       is the same defect class as a stale path rather than a milder one: a
       table that stops naming ten directories reports clean about them just
       as effectively as a table that names them wrongly. Deleting the ten
       rows would otherwise satisfy clause 3 perfectly.
    3. A scheduled `path` that does not exist — the stale-path case, S-13.
    4. A `former_path` that DOES exist. `former_path` records the spelling a
       tree had BEFORE the move; if something is at that location again then
       either the move was undone or the field was "corrected" to a live path,
       and in both readings the row is lying about the tree.
    """
    problems: list[str] = []
    if not any(entry.path.startswith(ARCHIVE_PREFIX) for entry in schedule):
        problems.append(
            _no_archived_tree(schedule)
            + " — a resolution check whose subject set contains no moved tree"
            " cannot demonstrate the property it was written for, and passes"
            " over the ten directories it is supposed to be about"
        )
    for entry in schedule:
        if not (REPO_ROOT / entry.path).exists():
            problems.append(
                f"{entry.path} is scheduled (owner {entry.owner}, wave"
                f" {entry.wave}) and is NOT on disk"
            )
        if entry.former_path and (REPO_ROOT / entry.former_path).exists():
            problems.append(
                f"{entry.path} records {entry.former_path} as its pre-move"
                " spelling, but something exists at that path — the row"
                " no longer describes the tree"
            )
    return problems


def test_every_scheduled_path_resolves_on_disk() -> None:
    """The schedule is about this tree, not about a tree it used to be about."""
    assert not scheduled_path_problems(RETIREMENT_SCHEDULE), "; ".join(
        scheduled_path_problems(RETIREMENT_SCHEDULE)
    )


def archive_sweep_problems(
    schedule: Sequence[Retirement], rows: Sequence[Coupling]
) -> list[str]:
    """Every way "the archive is swept" fails to be what the row set shows.

    `D-IMPL-191` ruling 3: *an archived path CONTINUES to count as a live
    coupling, because deletion is still owed and the coupling is still a real
    obligation.* This asserts the walk actually reaches it.

    The floor is tied to the SCHEDULE rather than set at `>= 1`, because one
    stray row would satisfy `>= 1` while nine of the ten trees went unseen.

    **The count floor is NOT the whole check, and the reason is a measurement
    made at the phase close rather than an argument.** Criterion 10's own words
    are *"suppressing an archived path's coupling row is watched RED, so the
    sweep cannot go blind to the archive"*. Against the count floor alone that
    is FALSE: at the close the row set held 131 archive rows across ten trees,
    and suppressing **every one of the 21 rows** for
    `archive/examples/03-harness-portability` left 110 rows against a floor of
    10 and this predicate returned EMPTY — green over a tree it did not look
    at. The same input in its concentrated form (21 rows, all naming one tree,
    nine trees contributing nothing) also passed. **The criterion's own named
    mutation could not turn it red**, which is this phase's defect class — a
    tool that reports clean because it did not look — arriving inside the
    control written to prevent it.

    So the coverage is asserted PER TREE and not summed. The count floor is
    kept because it names a different diagnosis (a shrunken row set) and
    because a reader following the old reasoning should still find it, but the
    per-tree clause is what discharges criterion 10.

    **The docstring's former escape clause is retired deliberately.** It read
    *"a tree whose last reference is legitimately discharged should not turn
    this red"*. That case cannot arise silently: deletion is still OWED for
    every scheduled row (`D-IMPL-191` ruling 3), and a tree whose last
    reference is genuinely discharged is a tree on its way out of the schedule
    — so the row leaves `archived` with it and the clause stops applying by
    itself. Until then, zero rows for a scheduled archived tree is the exact
    state the criterion says must be red.
    """
    problems: list[str] = []
    archived = [
        entry.path for entry in schedule if entry.path.startswith(ARCHIVE_PREFIX)
    ]
    if not archived:
        return [
            _no_archived_tree(schedule)
            + ", so a sweep that produced ZERO archive rows would satisfy this"
            " check vacuously"
        ]
    archive_rows = [
        row for row in rows if row.retiring_path.startswith(ARCHIVE_PREFIX)
    ]
    if len(archive_rows) < len(archived):
        problems.append(
            f"{len(archive_rows)} coupling rows name a path under"
            f" {ARCHIVE_PREFIX}, against {len(archived)} archived trees in the"
            " schedule — the sweep is reporting clean over a tree it did not"
            " look at"
        )
    seen = {row.retiring_path for row in archive_rows}
    unseen = [path for path in archived if path not in seen]
    if unseen:
        problems.append(
            f"{len(unseen)} of {len(archived)} scheduled archived trees have"
            " ZERO coupling rows, so the sweep is reporting clean over them"
            " while the row TOTAL stays above the floor — a count cannot see a"
            f" tree go dark: {', '.join(unseen)}"
        )
    return problems


def test_the_sweep_reaches_the_archive() -> None:
    """An archived path still counts, and the row set proves the walk got there.

    Measured at the phase close: **131 rows** name an archived path and **all
    ten** archived trees are named by at least one of them — the smallest
    contribution is 2 rows (`archive/examples/06-decision-replay`) and the
    largest 29 (`archive/examples/04-cross-process`). Both clauses are
    asserted: the total against the floor, and every scheduled archived tree
    against zero.
    """
    assert not archive_sweep_problems(RETIREMENT_SCHEDULE, head().rows), "; ".join(
        archive_sweep_problems(RETIREMENT_SCHEDULE, head().rows)
    )


def _s1_only_schedule() -> tuple[Retirement, ...]:
    """The unmoved survivors, derived rather than spelled.

    The `s1` pair and its three test modules are the rows `D-05` leaves alone.
    As a control input they are the *silence* case: every path resolves, so a
    resolution check written without clause 2 passes over them while the
    schedule says nothing at all about ten moved directories.
    """
    survivors = tuple(
        entry
        for entry in RETIREMENT_SCHEDULE
        if not entry.path.startswith(ARCHIVE_PREFIX) and not entry.former_path
    )
    assert survivors, "no unmoved rows to build the s1-only control from"
    return survivors


def _one_missing_path_schedule() -> tuple[Retirement, ...]:
    """The real schedule with one archived row re-pointed at a near miss."""
    return tuple(
        dataclasses.replace(entry, path=entry.path + "-old")
        if entry.path.startswith(ARCHIVE_PREFIX)
        and entry.path == _example_dir_for_wave(11)
        else entry
        for entry in RETIREMENT_SCHEDULE
    )


def _former_path_resolves_schedule() -> tuple[Retirement, ...]:
    """The real schedule with one row claiming a pre-move spelling that exists."""
    live = next(
        entry.path
        for entry in RETIREMENT_SCHEDULE
        if not entry.path.startswith(ARCHIVE_PREFIX)
    )
    return tuple(
        dataclasses.replace(entry, former_path=live)
        if entry.path == _example_dir_for_wave(11)
        else entry
        for entry in RETIREMENT_SCHEDULE
    )


@pytest.mark.parametrize(
    ("label", "build", "expected_fragment"),
    [
        ("an EMPTY schedule — the vacuity case", tuple, "EMPTY"),
        ("an s1-ONLY schedule — the silence case", _s1_only_schedule, "SILENT"),
        (
            "one archived path re-pointed to a near miss",
            _one_missing_path_schedule,
            "NOT on disk",
        ),
        (
            "a former_path that resolves — the row stops describing the tree",
            _former_path_resolves_schedule,
            "pre-move spelling",
        ),
    ],
)
def test_control_the_resolution_check_refuses_a_broken_schedule(
    label: str,
    build: "collections.abc.Callable[[], Sequence[Retirement]]",
    expected_fragment: str,
) -> None:
    """Control: each of the four clauses fires, and fires for its own reason.

    Asserting the message FRAGMENT rather than merely that some problem was
    reported, because four clauses sharing one `assert problems` is four
    clauses of which any one may have stopped working.
    """
    problems = scheduled_path_problems(build())
    assert problems, label
    assert any(expected_fragment in problem for problem in problems), (
        f"{label}: refused, but no problem mentions {expected_fragment!r}."
        f" Problems: {problems}"
    )


@pytest.mark.parametrize(
    ("label", "build", "rows", "expected_fragment"),
    [
        ("an EMPTY schedule — the vacuity case", tuple, "head", "EMPTY"),
        ("an s1-ONLY schedule — the silence case", _s1_only_schedule, "head", "SILENT"),
        (
            "a sweep that produced no rows at all",
            lambda: RETIREMENT_SCHEDULE,
            "none",
            "did not look at",
        ),
        (
            "ONE stray archive row against ten scheduled archived trees",
            lambda: RETIREMENT_SCHEDULE,
            "one",
            "against 10 archived trees",
        ),
        (
            "criterion 10's OWN mutation — every row for ONE archived tree"
            " suppressed, the total left far above the floor",
            lambda: RETIREMENT_SCHEDULE,
            "one-tree-dark",
            "have ZERO coupling rows",
        ),
        (
            "the CONCENTRATED set — enough rows to clear the floor, all of them"
            " naming a single tree",
            lambda: RETIREMENT_SCHEDULE,
            "concentrated",
            "have ZERO coupling rows",
        ),
    ],
)
def test_control_the_archive_sweep_check_refuses_a_blind_sweep(
    label: str,
    build: "collections.abc.Callable[[], Sequence[Retirement]]",
    rows: str,
    expected_fragment: str,
) -> None:
    """Control: the archive-swept check cannot pass over nothing.

    The third case is the REAL schedule with an EMPTY row set. A check written
    as "some row names the archive" would report the same thing here as an
    empty schedule does, and the two are entirely different failures.

    **The fourth case is what makes the floor a floor.** One stray archive row
    against ten scheduled archived trees is exactly the input a `>= 1`
    assertion would wave through while nine of the ten went unseen — so this
    case is the proof that the floor is TIED to the schedule rather than set
    at a constant. Without it, weakening `len(archived)` to `1` would pass
    every control in this module.

    **The fifth and sixth cases were added at the phase close, and they are
    there because the first four PASSED on the exact mutation criterion 10
    names.** Cases 1-4 all shrink the row set below the floor, so a count alone
    refuses every one of them and the per-tree question is never asked. Case 5
    is criterion 10's own words — *"suppressing an archived path's coupling
    row"* — applied to every row of one tree with the total left far above the
    floor; case 6 is the concentrated form, where the row set is large enough
    to clear the floor because a single tree contributes all of it. Both were
    measured GREEN against the count floor before the per-tree clause existed.
    Each asserts the `ZERO coupling rows` fragment specifically, because a
    refusal that merely says "too few rows" would send a reader to look for a
    shrunken sweep instead of a tree that went dark.
    """
    row_set: Sequence[Coupling]
    if rows == "none":
        row_set = ()
    elif rows == "one":
        stray = [
            row
            for row in head().rows
            if row.retiring_path.startswith(ARCHIVE_PREFIX)
        ][:1]
        assert stray, "no archive row at HEAD to build the stray-row control from"
        row_set = tuple(stray)
    elif rows in {"one-tree-dark", "concentrated"}:
        # The victim is derived from the SCHEDULE, never spelled, so a future
        # re-point cannot leave this control silently pointed at nothing.
        victim = next(
            entry.path
            for entry in RETIREMENT_SCHEDULE
            if entry.path.startswith(ARCHIVE_PREFIX)
        )
        victim_rows = [row for row in head().rows if row.retiring_path == victim]
        assert victim_rows, (
            f"no coupling row at HEAD names {victim}, so this control would"
            " suppress nothing and prove nothing"
        )
        if rows == "one-tree-dark":
            row_set = tuple(
                row for row in head().rows if row.retiring_path != victim
            )
            # The whole point: the total must stay ABOVE the floor, or the
            # count clause refuses first and the per-tree clause goes unproven.
            above = [
                row
                for row in row_set
                if row.retiring_path.startswith(ARCHIVE_PREFIX)
            ]
            assert len(above) >= len(
                [e for e in RETIREMENT_SCHEDULE if e.path.startswith(ARCHIVE_PREFIX)]
            ), (
                "suppressing one tree dropped the archive row total below the"
                " floor, so the count clause fires and this control no longer"
                " isolates the per-tree clause"
            )
        else:
            row_set = tuple(victim_rows)
    else:
        row_set = head().rows
    problems = archive_sweep_problems(build(), row_set)
    assert problems, label
    assert any(expected_fragment in problem for problem in problems), (
        f"{label}: refused, but no problem mentions {expected_fragment!r}."
        f" Problems: {problems}"
    )


def test_the_coverage_is_repo_wide() -> None:
    """Rows lie outside the three trees the § A.1/§ A.2 inventory swept.

    This is the whole argument for the sweep: `testpaths = ["tests"]` puts
    gates in six more trees into `make ci`, and none of them was measured.
    """
    outside = outside_swept_trees(head().rows)
    assert outside, "every row is inside the already-swept trees — nothing new was measured"
    assert len({row.file for row in outside}) >= 10


# ---------------------------------------------------------------------------
# CWD-independence — WR-04's exact failure.
# ---------------------------------------------------------------------------


def test_the_walk_is_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Re-scanning from an unrelated directory yields the identical result."""
    before = [path.as_posix() for path in iter_source_files()]
    monkeypatch.chdir(tmp_path)
    after = [path.as_posix() for path in iter_source_files()]
    assert after == before, "the walk followed the process CWD instead of REPO_ROOT"


def test_the_sweep_is_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The whole sweep — not only the walk — is rooted at REPO_ROOT."""
    monkeypatch.chdir(tmp_path)
    elsewhere = sweep()
    assert [row.sort_key() for row in elsewhere.rows] == [
        row.sort_key() for row in head().rows
    ]
    assert elsewhere.files_scanned == head().files_scanned


# ---------------------------------------------------------------------------
# Filter polarity — both directions, on synthetic modules.
# ---------------------------------------------------------------------------


def test_a_docstring_reference_is_documentary_not_live(
    tmp_path: pathlib.Path,
) -> None:
    """A retiring path named in a docstring does not turn a build red.

    It is still a row with an owner: prose that outlives its subject is work,
    and four of the fourteen known files carry nothing but hits of this shape.
    What it is not is `live`.
    """
    path = _write(
        tmp_path,
        "synthetic_docstring.py",
        f'''
        """Prose that mentions {WAVE_10} and resolves nothing."""

        VALUE = 1
        ''',
    )
    rows = python_hits(path, path.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0].shape == SHAPE_DOCSTRING
    assert rows[0].liveness == DOCUMENTARY
    assert not [row for row in rows if row.liveness == LIVE]


def test_the_same_path_in_a_path_call_is_live(tmp_path: pathlib.Path) -> None:
    """The other polarity: the identical string, resolved, is one live row."""
    path = _write(
        tmp_path,
        "synthetic_live.py",
        f'''
        import pathlib

        TARGET = pathlib.Path("{WAVE_10}")
        ''',
    )
    rows = python_hits(path, path.read_text(encoding="utf-8"))
    live = [row for row in rows if row.liveness == LIVE]
    assert len(live) == 1
    assert live[0].retiring_path == WAVE_10
    assert live[0].owner != UNOWNED


# ---------------------------------------------------------------------------
# Shape coverage — all four no-path-token shapes, proven synthetically.
# ---------------------------------------------------------------------------


def _synthetic_floor_module(tmp_path: pathlib.Path) -> pathlib.Path:
    """A module carrying a `MINIMUM_*` floor over sites in two retiring trees."""
    return _write(
        tmp_path,
        "test_synthetic_floor.py",
        f'''
        """A non-vacuity floor whose witnesses live under retiring paths."""

        MINIMUM_SITES = 2


        def _sites():
            return [
                "{WAVE_8}/run.py:1",
                "{WAVE_11}/run.py:2",
            ]


        def test_the_scan_is_not_vacuous() -> None:
            found = _sites()
            assert len(found) >= MINIMUM_SITES
        ''',
    )


def test_shape_1_the_count_constant_is_detected(tmp_path: pathlib.Path) -> None:
    """A module-level `MINIMUM_*` floor fed by a retiring tree yields a row."""
    _synthetic_floor_module(tmp_path)
    rows = count_coupling_rows(roots=[tmp_path])
    constants = [row for row in rows if row.shape == SHAPE_COUNT_CONSTANT]
    assert len(constants) == 1
    row = constants[0]
    assert row.witnesses == "2"
    assert "MINIMUM_SITES" in row.note
    assert "headroom 0" in row.note
    assert row.owner != UNOWNED


def test_shape_2_the_count_scan_function_is_detected(tmp_path: pathlib.Path) -> None:
    """The scan whose length the floor bounds is a row of its own."""
    _synthetic_floor_module(tmp_path)
    rows = count_coupling_rows(roots=[tmp_path])
    scans = [row for row in rows if row.shape == SHAPE_COUNT_SCAN_FUNCTION]
    assert len(scans) == 1
    assert "_sites()" in scans[0].note
    assert scans[0].owner != UNOWNED


def test_shape_2_reports_the_wave_the_floor_first_breaks(
    tmp_path: pathlib.Path,
) -> None:
    """Owner and first-break are different questions, and both are answered.

    The owner is the plan retiring the *last* witness, because that is the
    plan after which the floor takes its final value. The wave at which the
    floor first goes red can be earlier, and a row that did not say so would
    send the earlier plan into a red build with no warning.
    """
    _synthetic_floor_module(tmp_path)
    row = next(
        row
        for row in count_coupling_rows(roots=[tmp_path])
        if row.shape == SHAPE_COUNT_CONSTANT
    )
    assert row.owner == next(e.owner for e in RETIREMENT_SCHEDULE if e.path == WAVE_11)
    assert "first break: wave 8" in row.note


def test_shape_3_the_inline_tree_witness_is_detected(tmp_path: pathlib.Path) -> None:
    """An assertion with neither a floor constant nor a named scan function.

    The scan is written inline in the test body over a module-level
    scanned-tree tuple. Detector 2 cannot see it (no constant), detector 3
    cannot see it (no module-level scan bound to a floor), and a token pass
    cannot see it either — in the measured instance the witness path appears
    in the module only inside a docstring.
    """
    _write(
        tmp_path,
        "test_synthetic_inline.py",
        f'''
        import pathlib

        REPO = pathlib.Path({str(REPO_ROOT)!r})
        SCANNED_TREES = ("examples",)


        def _sources(trees):
            return [REPO / "{WAVE_8}" / "run.py"]


        def test_a_witness_exists() -> None:
            found = []
            for path in _sources(SCANNED_TREES):
                found.append(path)
            assert found
        ''',
    )
    # The shape is defined by the absence of the other two: no floor here.
    assert count_coupling_rows(roots=[tmp_path]) == []

    rows = inline_tree_witness_rows(roots=[tmp_path])
    assert len(rows) == 1
    row = rows[0]
    assert row.shape == SHAPE_INLINE_TREE_WITNESS
    assert row.retiring_path == WAVE_8
    assert row.witnesses == "1"
    assert row.owner == next(e.owner for e in RETIREMENT_SCHEDULE if e.path == WAVE_8)


def test_shape_3_ignores_an_assertion_with_headroom(tmp_path: pathlib.Path) -> None:
    """A scan sustained by a path nothing retires is not a coupling.

    Without this the detector would file every tree-scanning assertion in
    `tests/products/` as work for a plan that has nothing to do.
    """
    _write(
        tmp_path,
        "test_synthetic_headroom.py",
        f'''
        import pathlib

        REPO = pathlib.Path({str(REPO_ROOT)!r})
        SCANNED_TREES = ("src", "examples")


        def _sources(trees):
            return [
                REPO / "{WAVE_8}" / "run.py",
                REPO / "src" / "ccf" / "__init__.py",
            ]


        def test_a_witness_exists() -> None:
            found = []
            for path in _sources(SCANNED_TREES):
                found.append(path)
            assert found
        ''',
    )
    assert inline_tree_witness_rows(roots=[tmp_path]) == []


def test_shape_4_the_indirect_execution_is_detected(tmp_path: pathlib.Path) -> None:
    """A test that shells out to a script which builds the path from `__file__`.

    Neither file carries a retiring-path token — asserted here rather than
    assumed, because "the path is constructed, not written" is the whole
    reason a token pass is blind to this shape and the reason it survived two
    review rounds.

    **The synthetic runner joins EVERY segment of `WAVE_10`, not the first
    two.** The earlier form spelled `/ "{...split('/')[0]}" / "{...split('/')[1]}"`,
    which silently assumed a two-segment retiring path. Plan 23-10 re-pointed
    the schedule at `archive/examples/…` — three segments — and the fixture
    then built `archive/examples`, a path that retires nothing, so the detector
    correctly found zero rows and the test failed on its own fixture rather
    than on the detector. Watched: 0 rows where 1 was asserted.
    """
    test_module = _write(
        tmp_path,
        "tests/test_synthetic_shells_out.py",
        '''
        import subprocess
        import sys


        def test_runs_a_script_outside_this_tree() -> None:
            subprocess.run([sys.executable, "tools/synthetic_runner.py"], check=True)
        ''',
    )
    # Twelve spaces because that is the column `{segments}` sits at below, and
    # `_write` runs `textwrap.dedent`: a continuation line indented less than
    # the block would shrink the common prefix and un-indent the whole fixture.
    segments = ("\n" + " " * 12).join(f'/ "{part}"' for part in WAVE_10.split("/"))
    runner = _write(
        tmp_path,
        "tools/synthetic_runner.py",
        f'''
        import pathlib

        TARGET = (
            pathlib.Path(__file__).resolve().parents[1]
            {segments}
        )
        ''',
    )
    for path in (test_module, runner):
        assert WAVE_10 not in path.read_text(encoding="utf-8"), (
            f"{path.name} carries the retiring path as a token — the fixture no"
            " longer demonstrates the shape it exists to demonstrate"
        )

    rows = indirect_execution_rows(tests_root=tmp_path / "tests", repo_root=tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row.shape == SHAPE_INDIRECT_EXECUTION
    assert row.retiring_path == WAVE_10
    assert row.intermediate.endswith("synthetic_runner.py")
    assert row.owner == next(e.owner for e in RETIREMENT_SCHEDULE if e.path == WAVE_10)


#: No-path-token shapes with at least one measured instance in the checked-in
#: tree. Three of the four; the fourth is below with its reason.
HEAD_PRESENT_SHAPES: tuple[str, ...] = (
    SHAPE_COUNT_CONSTANT,
    SHAPE_COUNT_SCAN_FUNCTION,
    SHAPE_INDIRECT_EXECUTION,
)

#: No-path-token shapes with **no** instance at HEAD, each with the measurement
#: that put it here. A shape in this map is still exercised — by the synthetic
#: fixtures that build the shape under `tmp_path` — so it is unexercised
#: *against the real tree* rather than unexercised.
HEAD_ABSENT_SHAPES: dict[str, str] = {
    SHAPE_INLINE_TREE_WITNESS: (
        "the one instance this shape had —"
        " `test_gate_two_call_shape.py::test_the_plan_recognition_refuses_an_"
        "unrelated_required_keyword` — was sustained solely by"
        " `examples/03-harness-portability`, and plan 17-09 added"
        " `examples/hw1-companies-over-revenue`, a SECOND witness that nothing"
        " retires. The scan therefore has headroom and is no longer a coupling."
        " Measured both ways: parking the new example restores the row, and"
        " restoring it dissolves the row again."
    ),
}


#: The four shapes that carry no path token, which is what makes each of them
#: need a detector rather than a `git grep`.
NO_PATH_TOKEN_SHAPES: frozenset[str] = frozenset(
    {
        SHAPE_COUNT_CONSTANT,
        SHAPE_COUNT_SCAN_FUNCTION,
        SHAPE_INLINE_TREE_WITNESS,
        SHAPE_INDIRECT_EXECUTION,
    }
)


def shape_accounting_problems(
    shapes_at_head: set[str],
    *,
    present: tuple[str, ...],
    absent: dict[str, str],
) -> list[str]:
    """Every way the shape accounting fails to account for something.

    **A function of its inputs**, so the controls below can hand it a violating
    census and watch it refuse. An assertion that can only ever be handed the
    passing tree is an assertion nobody has watched fail — the discipline this
    phase's fifteen example-gate controls already follow.
    """
    problems: list[str] = []
    overlap = set(present) & set(absent)
    if overlap:
        problems.append(
            f"listed as both present and absent at HEAD: {sorted(overlap)}"
        )
    unaccounted = NO_PATH_TOKEN_SHAPES - set(present) - set(absent)
    if unaccounted:
        problems.append(
            f"no-path-token shapes in neither set, so nothing accounts for"
            f" them: {sorted(unaccounted)}"
        )
    stray = (set(present) | set(absent)) - NO_PATH_TOKEN_SHAPES
    if stray:
        problems.append(f"accounted shapes that carry a path token: {sorted(stray)}")
    for shape in present:
        if shape not in shapes_at_head:
            problems.append(
                f"no `{shape}` row at HEAD, but it is recorded as present — the"
                " detector is now unexercised against the real tree. Move it to"
                " HEAD_ABSENT_SHAPES with the measurement that put it there."
            )
    for shape, reason in absent.items():
        if shape in shapes_at_head:
            problems.append(
                f"`{shape}` has a row at HEAD again, but it is recorded as"
                f" absent: {reason} Move it to HEAD_PRESENT_SHAPES and restore"
                " the row's own assertion — a returning coupling is news."
            )
    return problems


def test_every_no_path_token_shape_is_accounted_for_at_head() -> None:
    """Each shape either has a HEAD instance or is recorded as having none.

    **The accounting is the assertion, and it is what the old form could not
    say.** This used to require all four shapes at HEAD, which was true when it
    was written and stopped being true the moment a coupling *dissolved* — the
    outcome the whole retirement inventory exists to produce. A gate that goes
    red when its subject improves teaches the reader to edit the gate, so it is
    restated: every shape is in exactly one of two named sets, and moving one
    between them is a visible edit with a reason attached.

    Nothing here is weakened. Both directions are refused — a shape recorded as
    present that has no HEAD row, and a shape recorded as absent that has one —
    so the set of shapes the real tree exercises can neither shrink nor grow
    without an edit somebody makes on purpose.
    """
    problems = shape_accounting_problems(
        {row.shape for row in head().rows},
        present=HEAD_PRESENT_SHAPES,
        absent=HEAD_ABSENT_SHAPES,
    )
    assert not problems, "; ".join(problems)


@pytest.mark.parametrize(
    ("label", "census", "present", "absent"),
    [
        (
            "a shape recorded present with no HEAD row",
            {SHAPE_COUNT_CONSTANT},
            (SHAPE_COUNT_CONSTANT, SHAPE_INDIRECT_EXECUTION),
            {SHAPE_COUNT_SCAN_FUNCTION: "r", SHAPE_INLINE_TREE_WITNESS: "r"},
        ),
        (
            "a shape recorded absent that reappeared at HEAD",
            NO_PATH_TOKEN_SHAPES,
            (SHAPE_COUNT_CONSTANT, SHAPE_COUNT_SCAN_FUNCTION, SHAPE_INDIRECT_EXECUTION),
            {SHAPE_INLINE_TREE_WITNESS: "r"},
        ),
        (
            "a shape in neither set",
            NO_PATH_TOKEN_SHAPES,
            (SHAPE_COUNT_CONSTANT,),
            {SHAPE_COUNT_SCAN_FUNCTION: "r"},
        ),
        (
            "a shape in both sets",
            NO_PATH_TOKEN_SHAPES,
            tuple(sorted(NO_PATH_TOKEN_SHAPES)),
            {SHAPE_INLINE_TREE_WITNESS: "r"},
        ),
        (
            "an EMPTY census — the vacuity case",
            set(),
            HEAD_PRESENT_SHAPES,
            HEAD_ABSENT_SHAPES,
        ),
    ],
)
def test_the_shape_accounting_refuses_a_violating_census(
    label: str, census: set[str], present: tuple[str, ...], absent: dict[str, str]
) -> None:
    """Control: the shipped checker, fed a census that does not add up.

    The last case is the one that matters most. A sweep returning **no rows at
    all** — a broken walk, a moved tree — would satisfy an "is this shape
    absent?" check for every shape, and a gate built only from absence claims
    would report green over a detector that measured nothing.
    """
    problems = shape_accounting_problems(census, present=present, absent=absent)
    assert problems, label


def test_the_head_indirect_execution_row_names_its_intermediate() -> None:
    """The row is filed against the always-on test, not the file two hops away.

    `perf/suites/crossproc/conftest.py` is where the path is resolved;
    `tests/perf_smoke/test_smoke.py` is where `make ci` goes red. A report
    naming only the former tells nobody which build breaks.
    """
    rows = [
        row for row in head().rows if row.shape == SHAPE_INDIRECT_EXECUTION
    ]
    assert rows
    smoke = [row for row in rows if row.file == "tests/perf_smoke/test_smoke.py"]
    assert smoke, "the always-on smoke module's indirect coupling is not reported"
    assert smoke[0].intermediate == "perf/suites/crossproc/conftest.py"
    assert smoke[0].retiring_path == WAVE_10
    assert smoke[0].owner == next(
        e.owner for e in RETIREMENT_SCHEDULE if e.path == WAVE_10
    )


#: The module that carried the one `inline-tree-witness` row, and the scanning
#: assertion inside it that the row was filed against. Named so the test below
#: can tell *the coupling dissolved* from *the subject was deleted* — two very
#: different reasons for a detector to return nothing, and only one of them is
#: good news.
INLINE_WITNESS_SUBJECT_FILE = "tests/products/test_gate_two_call_shape.py"
INLINE_WITNESS_SUBJECT_TEST = (
    "def test_the_plan_recognition_refuses_an_unrelated_required_keyword"
)


def test_the_inline_tree_witness_coupling_dissolved_rather_than_vanished() -> None:
    """The row is gone because the scan gained headroom — not because it did.

    **Replaces an assertion whose subject no longer exists.** The `n = 1` row
    used to be pinned here to wave 8's owner. Plan 17-09 added a second example
    under `examples/`, nothing retires it, and the scan it witnesses is
    therefore no longer sustained solely by a retiring path. That is a coupling
    being *retired by the tree improving*, which the inventory should record
    rather than resist.

    Three separate reasons a detector returns nothing, and only the first is
    acceptable — so all three are distinguished here rather than collapsed into
    an empty-list check:

    1. The coupling dissolved. Asserted by the subject still being present and
       the detector still working (see below).
    2. The subject was deleted. Refused: the module and the scanning assertion
       are both asserted to still exist.
    3. The detector broke. Refused: `test_shape_3_produces_a_row` builds the
       shape under `tmp_path` and asserts exactly one row with the right path,
       witness count and owner, so the detector is exercised whether or not
       HEAD carries an instance.

    If the row returns, `test_every_no_path_token_shape_is_accounted_for_at_head`
    goes red and says to restore the ownership assertion this replaced.
    """
    problems = dissolution_problems(
        [row for row in head().rows if row.shape == SHAPE_INLINE_TREE_WITNESS],
        subject_exists=(REPO_ROOT / INLINE_WITNESS_SUBJECT_FILE).is_file(),
        subject_source=_subject_source(),
    )
    assert not problems, "; ".join(problems)


def _subject_source() -> str:
    subject = REPO_ROOT / INLINE_WITNESS_SUBJECT_FILE
    return subject.read_text(encoding="utf-8") if subject.is_file() else ""


def dissolution_problems(
    rows: list[Coupling], *, subject_exists: bool, subject_source: str
) -> list[str]:
    """Every way "the coupling dissolved" fails to be the true explanation.

    A function of its three inputs so the controls can feed it each of the bad
    explanations in turn. Empty return means *dissolved*; anything else names
    which of the other two happened.
    """
    problems: list[str] = []
    if rows:
        problems.append(
            "the inline-tree-witness coupling is back; restore the wave-8"
            f" ownership assertion this test replaced. Rows: {rows}"
        )
    if not subject_exists:
        problems.append(
            f"{INLINE_WITNESS_SUBJECT_FILE} is gone, so an empty row set says"
            " nothing about headroom — the subject was DELETED instead"
        )
    elif INLINE_WITNESS_SUBJECT_TEST not in subject_source:
        problems.append(
            f"{INLINE_WITNESS_SUBJECT_FILE} no longer carries the scanning"
            " assertion the row was filed against, so the detector returning"
            " nothing is a DELETION rather than the headroom claimed here"
        )
    return problems


@pytest.mark.parametrize(
    ("label", "rows", "exists", "source"),
    [
        (
            "the subject module was deleted",
            [],
            False,
            "",
        ),
        (
            "the scanning assertion was deleted from a surviving module",
            [],
            True,
            "def test_something_else() -> None: ...",
        ),
        (
            "an EMPTY source — the vacuity case",
            [],
            True,
            "",
        ),
    ],
)
def test_the_dissolution_check_refuses_a_deletion(
    label: str, rows: list[Coupling], exists: bool, source: str
) -> None:
    """Control: a detector returning nothing because its subject went away.

    This is the whole reason the check is three conditions rather than
    ``assert rows == []``. An empty row list is what a dissolved coupling looks
    like AND what a deleted subject looks like AND what a broken detector looks
    like; only the first is the good news this test claims.
    """
    problems = dissolution_problems(
        rows, subject_exists=exists, subject_source=source
    )
    assert problems, label


def test_the_dissolution_check_refuses_a_returning_coupling() -> None:
    """Control: the row coming back is refused even with the subject intact."""
    returned = [row for row in head().rows if row.file == INLINE_WITNESS_SUBJECT_FILE][:1]
    assert returned, "the subject module carries no rows to build the control from"
    problems = dissolution_problems(
        returned, subject_exists=True, subject_source=_subject_source()
    )
    assert problems and "coupling is back" in problems[0], problems


def test_the_gate_two_module_carries_rows_with_two_different_owners() -> None:
    """Ownership is per ROW, not per file.

    A report that gave the whole module one owner would hand a plan a red build
    it had no notice of — that is the claim, and it is a claim about the sweep's
    ownership resolution rather than about any particular pair of shapes.

    **Asserted over the module's whole row set**, which is the honest scope for
    it. The previous form filtered to the two count shapes plus the inline one,
    and drew its second owner from the inline row; with that coupling dissolved
    every remaining *count* row in this module belongs to one plan, and
    narrowing the claim to fit would have been the gate being edited to pass.
    The module's rows still carry four distinct owners, and the property the
    docstring names — one file, several owners — is what is asserted.
    """
    problems = per_row_ownership_problems(
        [row for row in head().rows if row.file == INLINE_WITNESS_SUBJECT_FILE]
    )
    assert not problems, "; ".join(problems)


def per_row_ownership_problems(rows: list[Coupling]) -> list[str]:
    """Whether ``rows`` demonstrate per-row rather than per-file ownership.

    **Empty input is a problem, not a pass.** A module with no rows cannot
    demonstrate anything about ownership, and a filter that silently stopped
    matching would otherwise make this report green while measuring nothing —
    the failure mode this whole phase has been finding.
    """
    if not rows:
        return [
            f"{INLINE_WITNESS_SUBJECT_FILE} carries no coupling rows at all, so"
            " nothing here demonstrates per-row ownership"
        ]
    owners = {row.owner for row in rows}
    if len(owners) < 2:
        return [
            "every coupling row in one module resolved to a single owner, which"
            " is what a per-file ownership rule would produce and a per-row one"
            f" would not: {sorted(owners)}"
        ]
    return []


def test_the_ownership_check_refuses_a_single_owner_and_an_empty_set() -> None:
    """Control: both ways the ownership claim can be unearned.

    The empty case is the vacuity control — a filter matching nothing would
    make the shipped assertion pass over an empty list forever.
    """
    rows = [row for row in head().rows if row.file == INLINE_WITNESS_SUBJECT_FILE]
    assert rows, "no rows to build the single-owner control from"

    one_owner = [row for row in rows if row.owner == rows[0].owner]
    assert per_row_ownership_problems(one_owner), (
        "a row set with one distinct owner was accepted as demonstrating"
        " per-row ownership"
    )
    empty = per_row_ownership_problems([])
    assert empty and "no coupling rows at all" in empty[0], empty


# ---------------------------------------------------------------------------
# The property later waves need.
# ---------------------------------------------------------------------------


def test_no_row_has_an_owning_plan_the_schedule_cannot_supply() -> None:
    """An unowned row is a hard failure, closed by assigning an owner.

    It means a coupling exists that no plan owns, and waves 8, 10 and 11
    delete into it. There is no disposition that closes it by narration.
    """
    unowned = head().unowned
    assert not unowned, "rows with no owning plan: " + ", ".join(
        f"{row.file}:{row.line} -> {row.retiring_path}" for row in unowned
    )


def test_the_committed_report_carries_no_unowned_row() -> None:
    """The property is asserted against the committed file, not only the sweep."""
    assert REPORT_PATH.is_file(), f"missing inventory: {REPORT_PATH}"
    assert UNOWNED not in REPORT_PATH.read_text(encoding="utf-8")


def test_the_report_render_is_deterministic() -> None:
    """Two renders of one sweep are byte-identical — no timestamps, no paths."""
    result = head()
    assert render(result) == render(result)


def test_the_committed_report_is_current() -> None:
    """The checked-in inventory matches what the sweep produces now.

    This is what makes `--report && git diff` a usable gate for plans 16-15,
    16-17 and 16-18: a stale snapshot fails here rather than misleading them.
    """
    assert REPORT_PATH.read_text(encoding="utf-8") == render(head()), (
        "docs/surface/examples/RETIREMENT-COUPLINGS.md is stale — re-run"
        " `python tools/retirement_sweep.py --report`"
    )


def test_no_gitignored_path_reaches_the_report() -> None:
    """The inventory measures the tracked tree, not build output.

    Found by the wave-2 post-merge gate rather than by this module: the first
    committed report carried 301 rows from `.pytest_cache/v/cache/nodeids`,
    whose contents are whatever tests were last selected. The inventory was
    therefore a function of the developer's last pytest run, which makes
    `--report && git diff` — the gate plans 16-15, 16-17 and 16-18 re-run
    before deleting — produce spurious diffs and mask a real coupling change.

    Asserted against `git check-ignore` rather than against `ARTIFACT_DIRS`,
    so adding a new build directory to `.gitignore` without adding it to the
    prune set fails here instead of silently polluting the next inventory.
    """
    scanned = sorted({row.file for row in head().rows})
    if not scanned:
        pytest.fail("no rows to check — the sweep found nothing")
    proc = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        input="\n".join(scanned),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    # check-ignore exits 0 when at least one path is ignored, 1 when none is.
    ignored = sorted(line for line in proc.stdout.splitlines() if line.strip())
    assert not ignored, (
        "the sweep read gitignored paths, so the inventory is not reproducible:\n  "
        + "\n  ".join(ignored)
    )


# ---------------------------------------------------------------------------
# The sweep must not report "no coupling" when it means "I could not look".
# ---------------------------------------------------------------------------
#
# Phase 22.1. The sweep decides what is safe to delete. Every failure path in
# it used to return `None` and let the caller move on, so a gate module that
# would not import contributed no rows and the run printed a confident total
# at exit 0. MEASURED on the real tree, both before and after: under
# `/usr/bin/python3` rather than `.venv/bin/python`,
# `tests/products/test_gate_two_call_shape.py` fails to import for want of
# `joserfc`, its SIX floor rows vanish, and the total drops 267 -> 261 at
# EXIT 0. The staleness gate then reports the CORRECT committed report as
# stale. This is the project's own check-vacuity class (`D-GATE-21.1`) one
# tool over, and it sits directly upstream of the retirement decision.
#
# A correction to the record while closing it: the Phase 22 discuss sitting
# recorded "three modules fail to import". On this tree it is ONE module, and
# that one accounts for all six rows -- attributed row by row, not inferred
# from the delta. The smaller true number is recorded rather than the larger
# remembered one.


def _module_that_will_not_import(tmp_path: pathlib.Path) -> pathlib.Path:
    """A floor-carrying module whose import raises, as `joserfc` does at HEAD.

    It carries a real floor so it reaches `_load_module` at all: the walk
    parses first and only imports a module that has something to measure.
    """
    return _write(
        tmp_path,
        "test_will_not_import.py",
        f'''
        """A floor whose module cannot be imported."""

        import a_package_that_is_not_installed_anywhere  # noqa: F401

        MINIMUM_SITES = 2


        def _sites():
            return [
                "{WAVE_8}/run.py:1",
                "{WAVE_11}/run.py:2",
            ]


        def test_the_scan_is_not_vacuous() -> None:
            assert len(_sites()) >= MINIMUM_SITES
        ''',
    )


def test_head_examines_every_subject_it_walks() -> None:
    """At HEAD, in the venv, nothing was unexaminable — and that is measured."""
    assert head().unexaminable == (), (
        "the sweep could not examine every subject at HEAD: "
        + "; ".join(item.line() for item in head().unexaminable)
    )


def test_the_examination_record_is_not_vacuous(tmp_path: pathlib.Path) -> None:
    """The floor under the assertion above.

    An empty `unexaminable` tuple is the right answer only if the sweep
    actually tried to import something. If the walk imported nothing, the
    tuple would be empty for the wrong reason and
    `test_head_examines_every_subject_it_walks` would pass over a sweep that
    looked at nothing. This proves the recorder fires when there IS something
    to record, so its silence at HEAD carries information.
    """
    _module_that_will_not_import(tmp_path)
    reset_unexaminable()
    count_coupling_rows(roots=[tmp_path])

    # NOT `!= ()`. A recorder mutated to append a constant placeholder on every
    # failure would satisfy non-emptiness while carrying no information, which
    # is this project's own vacuity class inside its own floor. The subject and
    # the stage are asserted so the record has to be ABOUT the thing that failed.
    recorded = unexaminable()
    assert recorded, "the recorder never fired on a module that cannot import"
    assert any(
        item.subject.endswith("test_will_not_import.py") and item.stage == "import"
        for item in recorded
    ), [item.line() for item in recorded]


def test_a_module_that_will_not_import_is_recorded_rather_than_skipped(
    tmp_path: pathlib.Path,
) -> None:
    """The import site: recorded, named, and with the reason attached."""
    _module_that_will_not_import(tmp_path)
    reset_unexaminable()
    rows = count_coupling_rows(roots=[tmp_path])

    assert rows == [], "a module that will not import cannot have yielded rows"
    recorded = unexaminable()
    assert len(recorded) == 1, [item.line() for item in recorded]
    item = recorded[0]
    assert item.subject.endswith("test_will_not_import.py")
    assert item.stage == "import"
    assert "a_package_that_is_not_installed_anywhere" in item.detail, item.detail


def test_control_the_rows_a_broken_module_owes_are_exactly_what_vanishes(
    tmp_path: pathlib.Path,
) -> None:
    """The HEAD defect in miniature: same module, importable vs not.

    Proves the loss is silent WITHOUT the recorder — the row count alone
    cannot tell the two runs apart — which is the whole reason the recorder
    has to exist. Two rows here stand in for the six at HEAD.
    """
    good = tmp_path / "good"
    bad = tmp_path / "bad"
    good.mkdir()
    bad.mkdir()

    _synthetic_floor_module(good)
    _module_that_will_not_import(bad)

    reset_unexaminable()
    healthy = count_coupling_rows(roots=[good])
    assert len(healthy) == 2, "the healthy fixture must yield rows to lose"

    owed = {(row.shape, row.witnesses, row.retiring_path) for row in healthy}
    assert owed, "the healthy fixture pinned no rows, so nothing is owed"

    reset_unexaminable()
    broken = count_coupling_rows(roots=[bad])

    # The name of this test says EXACTLY what vanishes, so it pins the rows
    # rather than counting them. Asserting only `broken == []` would be
    # satisfied by a module with no floor at all, which is the very confusion
    # the recorder exists to end.
    assert {(row.shape, row.witnesses, row.retiring_path) for row in broken} == set()
    assert owed - {(row.shape, row.witnesses, row.retiring_path) for row in broken} == owed, (
        "the broken module yielded some of the rows it could not have measured"
    )

    # The row counts alone are indistinguishable from a module with no floor.
    # Only the record separates "no coupling" from "could not look" — and it has
    # to NAME the module, or it cannot be acted on.
    recorded = unexaminable()
    assert any(
        item.subject.endswith("test_will_not_import.py") and item.stage == "import"
        for item in recorded
    ), f"the loss was silent or unattributed: {[i.line() for i in recorded]}"


def test_a_scan_that_will_not_run_is_recorded(tmp_path: pathlib.Path) -> None:
    """The scan site: the module imports, the floor's scan function raises."""
    _write(
        tmp_path,
        "test_scan_raises.py",
        f'''
        """A floor whose scan cannot be run."""

        MINIMUM_SITES = 2


        def _sites():
            raise RuntimeError("this scan cannot be measured")


        def test_the_scan_is_not_vacuous() -> None:
            assert len(_sites()) >= MINIMUM_SITES


        _UNUSED = ["{WAVE_8}/run.py", "{WAVE_11}/run.py"]
        ''',
    )
    reset_unexaminable()
    count_coupling_rows(roots=[tmp_path])

    scans = [item for item in unexaminable() if item.stage == "scan"]
    assert len(scans) == 1, [item.line() for item in unexaminable()]
    assert scans[0].subject.endswith("::_sites")
    assert "this scan cannot be measured" in scans[0].detail


def _sweep_with_one_unexaminable() -> Sweep:
    return Sweep(
        rows=(),
        files_scanned=1,
        excluded=(),
        retiring_source_hits=0,
        unexaminable=(
            Unexaminable(
                subject="tests/products/test_gate_two_call_shape.py",
                stage="import",
                detail="ModuleNotFoundError: No module named 'joserfc'",
            ),
        ),
    )


def test_the_run_refuses_when_a_subject_could_not_be_examined(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit non-zero, and NAME the subject — a bare count is not actionable."""
    monkeypatch.setattr(
        "tools.retirement_sweep.sweep", _sweep_with_one_unexaminable
    )
    assert main([]) == 1
    err = capsys.readouterr().err
    assert "REFUSING" in err
    assert "tests/products/test_gate_two_call_shape.py" in err
    assert "joserfc" in err


def test_the_refusal_does_not_write_the_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An exit code alone does not protect the file.

    The refusal has to come BEFORE the write. Rendering an incomplete walk
    over the committed report replaces a good inventory with a smaller one,
    and the staleness gate then reports the CORRECT report as stale — which
    is exactly the confusing symptom the original defect produced.
    """
    target = tmp_path / "REPORT.md"
    target.write_text("the good inventory\n", encoding="utf-8")
    monkeypatch.setattr(
        "tools.retirement_sweep.sweep", _sweep_with_one_unexaminable
    )
    monkeypatch.setattr("tools.retirement_sweep.REPORT_PATH", target)

    assert main(["--report"]) == 1
    assert target.read_text(encoding="utf-8") == "the good inventory\n", (
        "the refusing run overwrote the committed report"
    )
    assert "was NOT written" in capsys.readouterr().err


def test_control_a_clean_sweep_still_exits_zero_and_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """The refusal's own false-positive control.

    A guard that refuses everything is not a guard. With nothing unexaminable
    the run must still write and still exit 0 — otherwise the two assertions
    above are satisfied by a tool that never works.
    """
    target = tmp_path / "REPORT.md"
    monkeypatch.setattr(
        "tools.retirement_sweep.sweep",
        lambda: Sweep(rows=(), files_scanned=1, excluded=(), retiring_source_hits=0),
    )
    monkeypatch.setattr("tools.retirement_sweep.REPORT_PATH", target)

    assert main(["--report"]) == 0
    assert target.exists(), "a clean run did not write the report"
    # `exists()` alone is satisfied by a zero-byte write. The written bytes must
    # be what `render` produces for that result, or this control passes on a
    # tool that creates an empty file and reports success.
    assert target.read_text(encoding="utf-8") == render(
        Sweep(rows=(), files_scanned=1, excluded=(), retiring_source_hits=0)
    ), "the clean run wrote something other than the rendered report"


def test_the_sweep_carries_the_examination_record_into_its_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`sweep()` must WIRE the collector into the `Sweep` it returns.

    **This is the hole the close panel found, and it was decisive.** Every other
    test in this section proves one of two things: that the RECORDER fires
    (against `count_coupling_rows` and the module-level collector directly), or
    that `main()` refuses (against a monkeypatched `sweep` returning a canned
    `Sweep`). Neither touches the single line that joins them.

    Measured, before this landed: deleting `unexaminable=unexaminable()` from
    `sweep()`'s `Sweep(...)` construction left **all 41 tests green** while the
    tool regressed completely — 261 rows at exit 0 under the system interpreter,
    which is the original defect exactly. A guard that survives the deletion of
    the thing it guards is not a guard.

    It is also this repo's own `D-IMPL-188` residual one module over: *nothing
    asserts that the bounded assertion actually READS the pin*. Here it does.
    """
    marker = Unexaminable(
        subject="tests/synthetic/test_marker.py",
        stage="import",
        detail="planted by the wiring test",
    )

    def recording_stage() -> list[Coupling]:
        record_unexaminable(marker.subject, marker.stage, marker.detail)
        return []

    # Patch one of the three row-producing stages `sweep()` calls, so the record
    # is made INSIDE the real `sweep()` run rather than handed to it.
    monkeypatch.setattr(
        "tools.retirement_sweep.count_coupling_rows", recording_stage
    )
    result = sweep()

    assert marker in result.unexaminable, (
        "a subject recorded during the real sweep did not reach the Sweep it"
        f" returned: {[item.line() for item in result.unexaminable]}. `main()`"
        " reads `result.unexaminable`, so the refusal cannot fire and the run"
        " reports a smaller total at exit 0 — the original defect, restored"
    )


def test_control_the_wiring_test_fails_when_the_sweep_records_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wiring test's own false-positive control.

    If `sweep()` returned every record ever made by any earlier caller — a
    collector never reset — the assertion above would pass for the wrong
    reason. `sweep()` calls `reset_unexaminable()` at its top, so a record made
    BEFORE it must not survive into its result.
    """
    stale = Unexaminable(
        subject="tests/synthetic/test_stale.py",
        stage="import",
        detail="recorded before the sweep began",
    )
    record_unexaminable(stale.subject, stale.stage, stale.detail)

    monkeypatch.setattr(
        "tools.retirement_sweep.count_coupling_rows", lambda: []
    )
    result = sweep()

    assert stale not in result.unexaminable, (
        "a record made before `sweep()` ran survived into its result, so"
        " `reset_unexaminable()` is not being called and the wiring assertion"
        " above proves nothing about THIS run"
    )


def test_a_file_that_will_not_parse_is_recorded(tmp_path: pathlib.Path) -> None:
    """The parse site, found by the close panel — all three reviewers named it.

    A `test_*.py` that is readable but unparsable was selected and read, then
    dropped with a bare `continue`. Failing to parse a file is not evidence it
    carried no floor; it is the same "could not look" polarity as the import
    swallow, one step earlier in the same loop.
    """
    _write(
        tmp_path,
        "test_will_not_parse.py",
        f'''
        """A floor in a file that cannot be parsed."""

        MINIMUM_SITES = 2


        def _sites():
            return ["{WAVE_8}/run.py:1", "{WAVE_11}/run.py:2"]


        def test_the_scan_is_not_vacuous() -> None:
            assert len(_sites()) >= MINIMUM_SITES

        this is not python(((
        ''',
    )
    reset_unexaminable()
    rows = count_coupling_rows(roots=[tmp_path])

    assert rows == [], "an unparsable file cannot have yielded measured rows"
    parses = [item for item in unexaminable() if item.stage == "parse"]
    assert len(parses) == len(unexaminable()), [i.line() for i in unexaminable()]
    assert parses[0].subject.endswith("test_will_not_parse.py")
    assert "SyntaxError" in parses[0].detail, parses[0].detail


def test_a_floor_whose_scan_symbol_is_missing_is_recorded(
    tmp_path: pathlib.Path,
) -> None:
    """The clearest adjacent instance, in codex's words — and it is.

    Here the module IMPORTS and the AST has already FOUND the floor, so the
    subject is not merely unreadable: it is a known, real floor whose scan
    cannot be run. Dropping it left a floor unmeasured while the total still
    read complete.
    """
    _write(
        tmp_path,
        "test_scan_symbol_missing.py",
        f'''
        """A floor whose named scan does not survive to module scope."""

        MINIMUM_SITES = 2


        def _sites():
            return ["{WAVE_8}/run.py:1", "{WAVE_11}/run.py:2"]


        def test_the_scan_is_not_vacuous() -> None:
            assert len(_sites()) >= MINIMUM_SITES


        del _sites
        ''',
    )
    reset_unexaminable()
    count_coupling_rows(roots=[tmp_path])

    scans = [item for item in unexaminable() if item.stage == "scan"]
    assert scans, [item.line() for item in unexaminable()]
    assert scans[0].subject.endswith("::_sites"), scans[0].subject
    assert "not callable" in scans[0].detail, scans[0].detail


def test_a_file_that_cannot_be_read_is_recorded(tmp_path: pathlib.Path) -> None:
    """The `read` stage, which had no control until the close panel said so.

    `read_text` fires on ZERO files in this tree today — measured — so its
    recording had no live subject and could have regressed in silence while the
    import and scan tests stayed green. A control does not need a live subject;
    it needs a subject it can make.
    """
    unreadable = tmp_path / "not-utf8.py"
    unreadable.write_bytes(b"\xff\xfe\x00 this is not utf-8 \x00")

    reset_unexaminable()
    assert read_text(unreadable) is None, "the fixture is readable after all"

    reads = [item for item in unexaminable() if item.stage == "read"]
    assert reads, [item.line() for item in unexaminable()]
    assert reads[0].subject.endswith("not-utf8.py"), reads[0].subject
    assert "UnicodeDecodeError" in reads[0].detail, reads[0].detail


def test_a_sabotage_run_that_cannot_be_measured_is_recorded(
    tmp_path: pathlib.Path,
) -> None:
    """The `sabotage-run` stage — the last site the close panel found uncontrolled.

    Detector 3 measures an inline witness by RESTRICTING the helper the test
    calls and re-running the test. An `AssertionError` from that re-run IS the
    measurement: the test failed without its retiring witnesses, so the coupling
    is real. Any OTHER exception is the ABSENCE of a measurement, and returning
    `False` for it reports one.

    The fixture indexes into the helper's result, so under restriction — where
    the result is empty — the re-run raises `IndexError` rather than failing an
    assertion.
    """
    _write(
        tmp_path,
        "test_unmeasurable_inline.py",
        f'''
        import pathlib

        REPO = pathlib.Path({str(REPO_ROOT)!r})
        SCANNED_TREES = ("examples",)


        def _sources(trees):
            return [REPO / "{WAVE_8}" / "run.py"]


        def test_a_witness_exists() -> None:
            found = _sources(SCANNED_TREES)
            # Indexes rather than asserting: under restriction this raises
            # IndexError, which is not a measurement of anything.
            assert found[0] is not None
        ''',
    )
    reset_unexaminable()
    inline_tree_witness_rows(roots=[tmp_path])

    runs = [item for item in unexaminable() if item.stage == "sabotage-run"]
    assert runs, (
        "an inline re-run that raised a non-AssertionError was reported as a"
        f" measurement: {[item.line() for item in unexaminable()]}"
    )
    assert runs[0].subject.endswith("::test_a_witness_exists"), runs[0].subject
    assert "IndexError" in runs[0].detail, runs[0].detail
