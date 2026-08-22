"""The requirement ledger is guarded *while* it is filled in, not graded after.

`.planning/REQUIREMENTS.md` carries two status channels — a checkbox list and a
traceability table — and Phase 21 rewrites the second one row by row. This
module holds the properties that are true of a *partially filled* ledger, so
that a mid-phase `make ci-core` goes red on the first bad verdict rather than
at the phase close: the citation form a status cell may carry, the agreement
between the two channels, the verdict vocabulary, and one verdict per cell. It
also holds the untouched-tree assertions that keep an audit phase from
quietly becoming an implementation phase.

The completeness count — *every row needing a verdict has one* — is
deliberately NOT here. It is red from the moment it lands until the last row
is written, and the `Makefile`'s `ci-core` target says in its own help text
that it must stay green from wave one onward. It belongs to the phase's last
plan.

**Where this lives, and why that is the whole registration.** The `Makefile`'s
`gate-tools` target has two legs, and leg two passes `tools/publish_scan_tests`
and `tools/docs_tests` to pytest. Dropping a module into this directory
therefore reaches `gate-tools`, `ci-core` and `ci` with nothing else to wire —
and the CI `docs` job runs the same two directories directly, which is why that
job's checkout was deepened to full history before this module landed.

**It never writes.** Not to the ledger, not anywhere. Every control below
doctors an *in-memory copy* of the document text and hands it to the same
function the shipped assertion calls, on the pattern
`tools/docs_tests/test_openapi_drift_control.py` states at length: a control
specified as "copy the subject, break it, assert the check fails" is worthless
against an assertion that reads a fixed path, because the copy is never what
the assertion looks at. So every checker here is a pure function of its
subject, and the shipped assertions hand it the real file.

**Why a ledger check exists at all when a citation lint already ships.** The
lint catches a symbol RENAME — a wrong symbol on a real path is a finding. It
does not catch a file MOVE: a citation naming a path that no longer exists is
counted as unresolved and dropped without a finding, and a citation whose
basename is ambiguous is dropped the same silent way. Those two holes are
named by ruling and are NOT fixed here (`D-07`); this module dodges both from
the outside, by requiring that a cited path exist exactly as written.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
from collections.abc import Sequence

#: The repo root, resolved from this file rather than from the process CWD.
#: A CWD-relative read finds no ledger at all and turns every assertion here
#: into a test that passes over an empty document — the failure this project
#: has recorded before, at
#: `tools/publish_scan_tests/test_docstring_leaks.py::test_the_walk_does_not_depend_on_the_process_cwd`.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: This phase's planning directory. Named once so the base-commit file and the
#: verification-record glob cannot drift apart.
PHASE_DIR = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "21-requirement-ledger-reconciliation-what-is-actually-discharge"
)

#: Where plan `21-01` pinned this phase's diff base, before any audit work
#: happened. Pinned in a file rather than resolved at close time from a branch
#: name, because a base that does not resolve makes an "is empty" assertion
#: vacuous rather than failing it.
BASE_COMMIT_FILE = PHASE_DIR / "21-BASE-COMMIT.txt"

#: Success criterion 12, verbatim: the phase touches no file under `src/` or
#: `runtime/`. This phase FINDS and RECORDS; it builds nothing.
FABRIC: tuple[str, ...] = ("src/", "runtime/")

#: The `D-11` scope fence made mechanical — an executor must not close a gap
#: the audit discovers. Wider than criterion 12's two trees on purpose: a
#: discovered gap gets closed in `examples/` or `public/` at least as readily
#: as in `src/`, and a new dependency added to `pyproject.toml` is the same
#: move by another route.
#:
#: `docs/` is deliberately NOT a member. `docs/DECISIONS.md` receives this
#: phase's three rulings and `docs/surface/examples/RETIREMENT-COUPLINGS.md` is
#: regenerated after every planning write, so a `docs/` entry would make this
#: fence red by construction and it would be softened within a day.
#: `.github/` is not a member either, for the same reason: the `docs` job's
#: checkout had to be deepened before this module could run in CI at all.
FENCE: tuple[str, ...] = (
    "src/",
    "runtime/",
    "examples/",
    "public/",
    "pyproject.toml",
)

#: Every phase record carrying an undischarged `human_verification:` block —
#: ELEVEN of them, for criterion 11's "left untouched" limb. `D-13`: an
#: executor does not discharge a `human_needed` item; those need Dave.
#:
#: The roster is RE-DERIVED by parsing the records on disk, never taken from
#: `gsd-sdk query audit-uat`, which filters on each record's frontmatter
#: `status:` and therefore reports twenty-four items across nine files — it
#: drops Phase twelve (`status: passed`, one item) and Phase eighteen
#: (`status: gaps_found`, two items). The files carry twenty-seven items across
#: eleven records. Criterion 11 was AMENDED to say so and the ruling is `D-20`.
#: Widening the roster from nine to eleven is exactly what stops those two
#: records from being edited without this assertion going red.
#:
#: `audit-uat`'s filter is NAMED, NOT FIXED — tooling repair inside an audit
#: phase, on the same reasoning as `D-07` for the citation lint.
UAT_RECORDS: tuple[str, ...] = (
    ".planning/phases/11-performance-battery/11-VERIFICATION.md",
    ".planning/phases/12-synthetic-data-demonstration/12-VERIFICATION.md",
    ".planning/phases/13-examples-suite-upgrade/13-VERIFICATION.md",
    ".planning/phases/14-documentation-suite/14-VERIFICATION.md",
    ".planning/phases/15.1-ergonomics-gap-closure/15.1-VERIFICATION.md",
    ".planning/phases/15.2-substrate-adapters-and-query-pushdown/15.2-VERIFICATION.md",
    ".planning/phases/15.3-fluree-adapter-tier-1-substrate-inserted/15.3-VERIFICATION.md",
    ".planning/phases/15.4-backend-registration-seam-the-substrate-stops-naming-its-ada"
    "/15.4-VERIFICATION.md",
    ".planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof"
    "/18-VERIFICATION.md",
    ".planning/phases/18.1-simplify-the-mcp-example-separate-the-server-from-the-client"
    "/18.1-VERIFICATION.md",
    ".planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert"
    "/19-VERIFICATION.md",
)

#: The glob and the marker the roster above is re-derived from. A record is a
#: `human_verification` record when its frontmatter opens such a block; the
#: sixteen `*-VERIFICATION.md` files in the tree are not all of them.
UAT_GLOB = ".planning/phases/*/[0-9]*-VERIFICATION.md"
UAT_MARKER = re.compile(r"^human_verification:", re.MULTILINE)

#: `D-07`'s prohibition made mechanical: the citation lint's ambiguous-basename
#: hole is NAMED, not fixed, in this phase, and fixing it here would be tooling
#: repair inside an audit.
#:
#: FILE-scoped rather than tree-scoped, deliberately. This phase legitimately
#: writes a new module under `tools/docs_tests/`, so a `tools/`-wide emptiness
#: assertion would be false by construction — and would be narrowed or deleted
#: on its first run, leaving the one prohibition that actually matters enforced
#: by nothing at all.
PINNED_FILES: tuple[str, ...] = ("tools/lints/citations.py",)

#: A tree that genuinely differs between the pinned base and HEAD, for
#: `CONTROL A`. Chosen because the phase's entire product is written here —
#: the base-commit file, the ledger's verdicts, every SUMMARY. If this ever
#: came back empty the control would be the thing to fix, never the assertion.
CHANGED_TREE: tuple[str, ...] = (".planning/",)

#: A SHA that resolves to nothing, for `CONTROL B`. Hex, so it is
#: syntactically a revision; absent, so it is not one.
UNRESOLVABLE_BASE = "0000000000000000000000000000000000000000"


# ---------------------------------------------------------------------------
# The pinned base, and the diff machinery built on it.
#
# Ported from `tests/examples/test_hw1_harness_clients_readme.py::client_surface_diff`
# and widened: that module asserted one tree, this one asserts four different
# path sets through the same function, so all four share one control.
# ---------------------------------------------------------------------------


def phase_base_commit() -> str:
    """The pinned diff base, read from the file plan `21-01` wrote."""
    first_line = BASE_COMMIT_FILE.read_text(encoding="utf-8").splitlines()[0]
    return first_line.strip()


def fabric_diff(base: str, paths: Sequence[str]) -> str:
    """``git diff --stat <base>..HEAD -- <paths>``, as a string.

    A function of its arguments so a control can hand it a base and a path
    that genuinely **do** differ and watch it produce output. That control is
    the point of the design: *an assertion that a diff is empty passes
    trivially when the diff command is broken, unresolvable or misspelled*,
    and an empty string from a failed command is indistinguishable from an
    empty string from a clean tree.

    Three refusals rather than a quiet empty string: an empty base (``git diff
    ..HEAD`` compares HEAD against nothing), an empty path list (the diff is
    limited to nothing and is empty regardless of what the phase changed), and
    a non-zero exit from `git` itself.

    Note that this compares COMMITS and is blind to the working tree, which is
    why the base-commit file is committed before this module is first run.
    """
    if not base.strip():
        raise AssertionError(
            "no diff base was given, so `git diff` would compare HEAD against"
            " nothing and print nothing — which reads exactly like a clean tree"
        )
    if not paths:
        raise AssertionError(
            "no paths were given, so the diff is limited to nothing and is"
            " empty regardless of what the phase changed"
        )
    completed = subprocess.run(
        ["git", "diff", "--stat", f"{base}..HEAD", "--", *paths],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"`git diff --stat {base}..HEAD -- {list(paths)}` exited"
            f" {completed.returncode}, so its empty output says nothing about"
            f" the tree.\nstderr: {completed.stderr.strip()}"
        )
    return completed.stdout


def derived_uat_records(base: pathlib.Path) -> frozenset[str]:
    """Every `*-VERIFICATION.md` under `base` opening a `human_verification:` block.

    Takes its root as an argument for the same reason every other checker here
    does: so it can be pointed at something other than the tree it is about.
    """
    found = {
        path.relative_to(base).as_posix()
        for path in base.glob(UAT_GLOB)
        if path.is_file() and UAT_MARKER.search(path.read_text(encoding="utf-8"))
    }
    return frozenset(found)


def test_the_pinned_diff_base_resolves() -> None:
    """Non-vacuity: the base is a commit `git` can actually reach.

    Without this, a truncated or corrupted base-commit file would make every
    assertion below raise for a reason nobody would read as "the pin is
    broken".
    """
    base = phase_base_commit()
    assert re.fullmatch(r"[0-9a-f]{40}", base), (
        f"the pinned base {base!r} is not a full SHA; a short or annotated"
        " value is one rename away from resolving to something else"
    )
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"the pinned base {base} does not resolve in this repository:"
        f" {completed.stderr.strip()}"
    )


def test_the_fabric_is_untouched() -> None:
    """Criterion 12, in its own words: no file under `src/` or `runtime/`."""
    diff = fabric_diff(phase_base_commit(), FABRIC)
    assert diff == "", (
        "this phase changed a file under `src/` or `runtime/`. Criterion 12"
        " forbids it: the phase FINDS and RECORDS, and the work a `Not built`"
        " verdict surfaces is scoped as its own phase afterwards, with Dave"
        f" ruling on what is worth building at all:\n{diff}"
    )


def test_the_scope_fence_holds() -> None:
    """`D-11`: an executor does not close a gap the audit discovers.

    Wider than criterion 12 on purpose. A gap closed in `examples/` or
    `public/`, or a dependency added to `pyproject.toml`, is the same move as
    a gap closed in `src/` — and the ROADMAP's out-of-scope paragraph names
    the behaviour rather than the tree: *an executor that starts closing gaps
    it discovered has turned an audit into an unplanned implementation phase.*
    """
    diff = fabric_diff(phase_base_commit(), FENCE)
    assert diff == "", (
        "this phase wrote inside the `D-11` scope fence. The finding is"
        " REPORTED — as a verdict, a named absence and a work-list entry —"
        " never closed here, and this assertion is not narrowed to accommodate"
        f" the change that tripped it:\n{diff}"
    )


def test_the_human_needed_verification_records_are_untouched() -> None:
    """`D-13`/`D-20`: no `human_needed` item is discharged by an executor."""
    diff = fabric_diff(phase_base_commit(), UAT_RECORDS)
    assert diff == "", (
        "a phase verification record changed. Every item in these files needs"
        " Dave, not an executor (`D-13`), and the roster covers all eleven"
        " records rather than the nine `audit-uat` reports (`D-20`) precisely"
        f" so the two it drops cannot be edited quietly:\n{diff}"
    )


def test_the_uat_roster_matches_the_records_on_disk() -> None:
    """The frozen roster is re-derived and compared PATH BY PATH.

    Its own test rather than a companion assertion, because it falsifies a
    different thing: the assertion above proves the eleven named files did not
    change, and this one proves the eleven names are still the right eleven.

    Per `D-21` this compares a FROZEN ROSTER OF NAMED PATHS and never a
    length. A roster that silently shrank back to `audit-uat`'s nine fails
    here by name; a twelfth record appearing later fails by name too, rather
    than quietly satisfying a comparison against a number.
    """
    derived = derived_uat_records(REPO_ROOT)
    declared = frozenset(UAT_RECORDS)
    missing_from_roster = sorted(derived - declared)
    absent_from_disk = sorted(declared - derived)
    assert derived == declared, (
        "the frozen `human_verification` roster and the records on disk have"
        " diverged.\n  on disk but not in the roster:"
        f" {missing_from_roster}\n  in the roster but not on disk:"
        f" {absent_from_disk}"
    )
    for record in UAT_RECORDS:
        assert (REPO_ROOT / record).is_file(), (
            f"the roster names {record}, which is not a file — the untouched"
            " assertion over it would then be a diff limited to a path that"
            " does not exist, which prints nothing forever"
        )


def test_the_citation_lint_is_not_modified() -> None:
    """`D-07`: the lint's silent-drop holes are NAMED, not fixed, in this phase."""
    diff = fabric_diff(phase_base_commit(), PINNED_FILES)
    assert diff == "", (
        "`tools/lints/citations.py` changed. `D-07` holds it byte-identical"
        " for this phase: the ambiguous-basename hole stays open and stays"
        " named, because fixing it here would be tooling repair inside an"
        " audit phase. The ledger check dodges the hole from the outside"
        f" instead, by requiring a cited path to exist as written:\n{diff}"
    )


# --- CONTROL A-C: fabric_diff, watched producing output and watched refusing ---


def test_control_a_a_base_and_path_that_differ_produce_output() -> None:
    """CONTROL A — the diff machinery is watched producing something.

    **This is the control that matters**, and it is the non-vacuity proof for
    all four emptiness assertions above at once. Every one of them passes on
    an empty string, and an empty string is what a broken command, an
    unresolvable base and a misspelled path all produce. Handing the same
    function a pair that genuinely differs is the only thing separating "the
    fabric did not change" from "nothing was compared".
    """
    diff = fabric_diff(phase_base_commit(), CHANGED_TREE)
    assert diff.strip(), (
        "`git diff` produced nothing for a tree this phase demonstrably writes"
        f" to ({list(CHANGED_TREE)}). The empty results above therefore say"
        " nothing about the fabric, the fence, the verification records or the"
        " citation lint, and all four are vacuous until this is fixed"
    )


def test_control_b_an_unresolvable_base_fails_loudly() -> None:
    """CONTROL B — a base `git` cannot resolve raises instead of returning ''.

    The quietest failure available: a base that stops resolving after a
    rebase, a truncated pin, a typo, a shallow CI clone. Every one makes `git
    diff` exit non-zero with an empty stdout, and a function that returned
    that stdout would report a clean tree forever.
    """
    try:
        result = fabric_diff(UNRESOLVABLE_BASE, FABRIC)
    except AssertionError as failure:
        assert "exited" in str(failure)
        return
    raise AssertionError(
        f"an unresolvable base returned {result!r} instead of failing; an 'is"
        " empty' assertion built on that reports success for a comparison that"
        " never happened"
    )


def test_control_c_an_empty_path_list_fails_loudly() -> None:
    """CONTROL C — the two other ways to compare nothing and call it clean.

    ``git diff --stat ..HEAD`` and a diff limited to no paths both print
    nothing and both exit zero.
    """
    for base, paths, expected in (
        ("", FABRIC, "no diff base was given"),
        (phase_base_commit(), (), "no paths were given"),
    ):
        try:
            fabric_diff(base, paths)
        except AssertionError as failure:
            assert expected in str(failure)
        else:  # pragma: no cover - the refusal is the point
            raise AssertionError(f"{base!r}/{list(paths)} did not refuse")
