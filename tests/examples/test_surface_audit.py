"""ERGO-03 — the executable half of the Criterion 1 surface audit (D-11/D-12).

`tools/measure_examples.py` produces the numbers; this module is what makes
them a *check* rather than a report. Three things are asserted:

1. **No silent regression.** For every example file that has an `after/`
   fragment, the live measurement equals the recorded numbers. Per D-12 there
   is no target number — the test pins the *achieved* number, so a later edit
   cannot quietly re-inflate an example that a rewrite plan already thinned.
2. **The before-baseline is real and non-empty.** Every `before/` fragment
   names a file that still exists, and the set is non-empty. The baseline is
   the phase-start record; it is written once by plan 15-03 and never
   regenerated.
3. **Relocation is never conflated with removal.** `audit_report()` returns
   four separate figures — mechanical before/after and relocated before/after
   — and is structurally incapable of returning a single combined "lines
   saved" number. D-09 *relocates* assertions into `tests/` while the wiring
   is *removed*; D-12's stated risk is a target hit by moving lines rather
   than removing work. Plan 15-21 calls `audit_report()` to produce the
   phase-close report.

Files with no `after/` fragment are skipped by assertion 1, not failed — the
rewrite plans land across later waves, and an audit that failed on unrewritten
files would be red for most of the phase.

Fragments are globbed rather than enumerated so the eight example-rewrite
plans can each add their own `after/` fragment in parallel worktrees without
touching this module.
"""

from __future__ import annotations

import ast
import inspect
import json
import pathlib
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:  # the tools/ package is not installed
    sys.path.insert(0, str(REPO_ROOT))

from tools.measure_examples import (  # noqa: E402
    BEFORE_DIR,
    fragment_name,
    measure_file,
    serialize,
)

AFTER_DIR = REPO_ROOT / "docs" / "surface" / "examples" / "after"

#: The phase-start tree carried 24 measured modules; a baseline that shrank
#: below the research-documented floor means fragments were deleted, not that
#: examples got smaller (removing a file removes its fragment's meaning too).
MINIMUM_BASELINE_FRAGMENTS = 20

REGENERATION_COMMAND = "make measure-examples"


def _fragments(directory: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Fragment name -> parsed measurement, empty if the directory is absent."""
    if not directory.is_dir():
        return {}
    return {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    }


def audit_report() -> dict[str, Any]:
    """The four separate figures Criterion 1 reports (D-11/D-12).

    Deliberately returns four independent totals plus a per-file breakdown and
    **no** combined figure. Removal (`mechanical_*`) and relocation
    (`relocated_*`) answer different questions: whether the SDK absorbed
    wiring, and whether assertions merely moved to `tests/`. Summing them
    would produce exactly the overstated number D-12 forbids.
    """
    before = _fragments(BEFORE_DIR)
    after = _fragments(AFTER_DIR)

    per_file: dict[str, dict[str, int | None]] = {}
    totals = {
        "mechanical_before": 0,
        "mechanical_after": 0,
        "relocated_before": 0,
        "relocated_after": 0,
    }

    for name, recorded in before.items():
        rewritten = after.get(name)
        per_file[recorded["path"]] = {
            "mechanical_before": recorded["removable"],
            "mechanical_after": (
                rewritten["removable"] if rewritten is not None else None
            ),
            "relocated_before": recorded["relocatable"],
            "relocated_after": (
                rewritten["relocatable"] if rewritten is not None else None
            ),
        }
        totals["mechanical_before"] += recorded["removable"]
        totals["relocated_before"] += recorded["relocatable"]
        # A file with no after/ fragment has not been rewritten; carrying its
        # before-number forward keeps the two totals comparable.
        totals["mechanical_after"] += (
            rewritten["removable"] if rewritten is not None else recorded["removable"]
        )
        totals["relocated_after"] += (
            rewritten["relocatable"]
            if rewritten is not None
            else recorded["relocatable"]
        )

    return {**totals, "per_file": per_file, "rewritten_files": sorted(after)}


def test_the_baseline_is_not_vacuous() -> None:
    """Assertion 2: an empty glob would make every other assertion trivial."""
    before = _fragments(BEFORE_DIR)
    assert len(before) >= MINIMUM_BASELINE_FRAGMENTS, (
        f"{BEFORE_DIR} holds {len(before)} fragments; the phase-start baseline"
        f" had at least {MINIMUM_BASELINE_FRAGMENTS}"
    )


@pytest.mark.parametrize("fragment", sorted(_fragments(BEFORE_DIR)))
def test_every_baseline_fragment_names_a_file_that_still_exists(
    fragment: str,
) -> None:
    """Assertion 2: the baseline describes the tree, not a vanished one."""
    recorded = _fragments(BEFORE_DIR)[fragment]
    path = REPO_ROOT / recorded["path"]
    assert path.is_file(), (
        f"{fragment} records {recorded['path']}, which no longer exists;"
        " deleting a measured example needs a surface-change entry, not a"
        " silently orphaned baseline fragment"
    )
    assert fragment_name(recorded["path"]) == fragment


def test_no_rewritten_example_has_silently_regressed() -> None:
    """Assertion 1: the achieved number is pinned, per D-12's no-target rule."""
    after = _fragments(AFTER_DIR)
    divergent: list[str] = []
    for name, recorded in after.items():
        path = REPO_ROOT / recorded["path"]
        if not path.is_file():
            divergent.append(f"{name} (file missing)")
            continue
        if serialize(measure_file(path)) != serialize(recorded):
            divergent.append(name)
    assert not divergent, (
        "These rewritten examples no longer measure what their after/ fragment"
        f" records: {', '.join(sorted(divergent))}. Run"
        f" `{REGENERATION_COMMAND}`-equivalent re-measurement and review the"
        " diff — a growing example is a regression, not a test bug."
    )


def test_audit_report_returns_four_separate_figures() -> None:
    """Assertion 3: the report shape cannot overstate the win."""
    report = audit_report()
    for key in (
        "mechanical_before",
        "mechanical_after",
        "relocated_before",
        "relocated_after",
    ):
        assert key in report, key
        assert isinstance(report[key], int)
    assert report["mechanical_before"] > 0
    assert report["relocated_before"] > 0


def test_audit_report_never_returns_a_combined_figure() -> None:
    """Assertion 3: structural, not stylistic — D-12's forbidden number.

    The forbidden names are assembled rather than written out, so this test's
    own source cannot be what the scan trips over.
    """
    forbidden = {
        "_".join(parts)
        for parts in (
            ("lines", "saved"),
            ("total", "reduction"),
            ("total", "saved"),
        )
    }

    report = audit_report()
    assert not forbidden & set(report)

    tree = ast.parse(inspect.getsource(audit_report))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    keys = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not forbidden & (names | keys), forbidden & (names | keys)


def test_the_report_covers_every_baseline_file() -> None:
    """The per-file breakdown is what 15-21 renders; it must be complete."""
    report = audit_report()
    recorded_paths = {
        fragment["path"] for fragment in _fragments(BEFORE_DIR).values()
    }
    assert set(report["per_file"]) == recorded_paths
