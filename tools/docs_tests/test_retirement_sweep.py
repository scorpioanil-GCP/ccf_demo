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

import pathlib
import subprocess
import sys
import textwrap

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
    SHAPE_COUNT_CONSTANT,
    SHAPE_COUNT_SCAN_FUNCTION,
    SHAPE_DOCSTRING,
    SHAPE_INDIRECT_EXECUTION,
    SHAPE_INLINE_TREE_WITNESS,
    UNOWNED,
    Sweep,
    count_coupling_rows,
    indirect_execution_rows,
    inline_tree_witness_rows,
    iter_source_files,
    outside_swept_trees,
    python_hits,
    render,
    sweep,
)

#: One retiring example directory per wave, taken from the schedule so this
#: module carries no retiring-path token of its own.
WAVE_8 = next(
    entry.path
    for entry in RETIREMENT_SCHEDULE
    if entry.wave == 8 and entry.path.startswith("examples/")
)
WAVE_10 = next(
    entry.path
    for entry in RETIREMENT_SCHEDULE
    if entry.wave == 10 and entry.path.startswith("examples/")
)
WAVE_11 = next(
    entry.path
    for entry in RETIREMENT_SCHEDULE
    if entry.wave == 11 and entry.path.startswith("examples/")
)

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
    runner = _write(
        tmp_path,
        "tools/synthetic_runner.py",
        f'''
        import pathlib

        TARGET = (
            pathlib.Path(__file__).resolve().parents[1]
            / "{WAVE_10.split("/")[0]}"
            / "{WAVE_10.split("/")[1]}"
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


def test_all_four_no_path_token_shapes_are_present_at_head() -> None:
    """Each shape has at least one measured instance in the checked-in tree."""
    shapes = {row.shape for row in head().rows}
    for shape in (
        SHAPE_COUNT_CONSTANT,
        SHAPE_COUNT_SCAN_FUNCTION,
        SHAPE_INLINE_TREE_WITNESS,
        SHAPE_INDIRECT_EXECUTION,
    ):
        assert shape in shapes, f"no `{shape}` row at HEAD"


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


def test_the_head_inline_tree_witness_row_is_owned_three_waves_early() -> None:
    """The `n = 1` row belongs to wave 8, not to the wave-11 re-flooring plan."""
    rows = [row for row in head().rows if row.shape == SHAPE_INLINE_TREE_WITNESS]
    assert len(rows) == 1
    row = rows[0]
    assert row.file == "tests/products/test_gate_two_call_shape.py"
    assert row.witnesses == "1"
    assert row.owner == next(e.owner for e in RETIREMENT_SCHEDULE if e.path == WAVE_8)


def test_the_gate_two_module_carries_rows_with_two_different_owners() -> None:
    """The count rows and the inline row are owned by different plans.

    A report that gave the whole module one owner would hand the wave-8 plan
    a red build it had no notice of.
    """
    rows = [
        row
        for row in head().rows
        if row.file == "tests/products/test_gate_two_call_shape.py"
        and row.shape
        in {SHAPE_COUNT_CONSTANT, SHAPE_COUNT_SCAN_FUNCTION, SHAPE_INLINE_TREE_WITNESS}
    ]
    assert len({row.owner for row in rows}) >= 2


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
