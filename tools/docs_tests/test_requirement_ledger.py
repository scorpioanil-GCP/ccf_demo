"""The requirement ledger is guarded *while* it is filled in, not graded after.

`.planning/REQUIREMENTS.md` carries two status channels — a checkbox list and a
traceability table — and Phase 21 rewrites the second one row by row. This
module holds the properties that are true of a *partially filled* ledger, so
that a mid-phase `make ci-core` goes red on the first bad verdict rather than
at the phase close: the citation form a status cell may carry, the agreement
between the two channels, the verdict vocabulary, and one verdict per cell. It
also holds the untouched-tree assertions that keep an audit phase from
quietly becoming an implementation phase.

The completeness count — *every row needing a verdict has one* — was
deliberately NOT here for five waves. It is red from the moment it lands until
the last row is written, and the `Makefile`'s `ci-core` target says in its own
help text that it must stay green from wave one onward, so it belonged to the
phase's last execution plan. **Plan `21-06` landed it**, in `Check C` at the
foot of this module, together with the phase's own ten rows held to the same
gate and the proof that no test was written under `tests/` to manufacture a
citation. From that commit forward the ledger cannot silently lose a verdict,
cannot carry two on one row, and cannot shrink either roster.

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

import pytest

from tools.lints.citations import CITATION, CITED_SUFFIXES, NODE_ID, repo_index

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


def tracked_under(paths: Sequence[str]) -> list[str]:
    """Every path tracked by `git` that the pathspec `paths` matches.

    Added at the phase close, by the §3.1 cross-AI panel. It exists so that
    :func:`fabric_diff` can tell a pathspec that names a real subject from one
    that names nothing — see the fourth refusal there for why that distinction
    is load-bearing rather than tidy.

    Raises on a non-zero `git` exit for the reason every other subprocess in
    this module does: an empty stdout from a failed command reads exactly like
    an empty stdout from a real answer.
    """
    completed = subprocess.run(
        ["git", "ls-files", "--", *paths],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"`git ls-files -- {list(paths)}` exited {completed.returncode}, so"
            " its empty output says nothing about whether the pathspec names a"
            f" real subject.\nstderr: {completed.stderr.strip()}"
        )
    return [line for line in completed.stdout.splitlines() if line]


def fabric_diff(base: str, paths: Sequence[str]) -> str:
    """``git diff --stat <base>..HEAD -- <paths>``, as a string.

    A function of its arguments so a control can hand it a base and a path
    that genuinely **do** differ and watch it produce output. That control is
    the point of the design: *an assertion that a diff is empty passes
    trivially when the diff command is broken, unresolvable or misspelled*,
    and an empty string from a failed command is indistinguishable from an
    empty string from a clean tree.

    Four refusals rather than a quiet empty string: an empty base (``git diff
    ..HEAD`` compares HEAD against nothing), an empty path list (the diff is
    limited to nothing and is empty regardless of what the phase changed), **a
    pathspec ANY MEMBER of which matches no tracked file**, and a non-zero exit
    from `git` itself.

    **The third refusal is quantified PER MEMBER, and that quantifier is the
    whole of `RR-1`.** It was added at the Phase 21 close as ONE truthiness test
    on the whole tuple, and the write-up recorded the hole as closed; it was
    closed for arity one. ``fabric_diff(base, ("scr/", "runtime/"))`` returned
    the empty string with NO refusal — ``runtime/`` matches seventy-one tracked
    files, satisfied the aggregate test on the typo's behalf, and left the
    assertion reporting a clean fabric over a diff that had lost half its
    subject. :data:`FENCE` has five members and :data:`UAT_RECORDS` eleven, so
    a one-key typo in any of sixteen places converted a `D-11` scope-fence
    assertion into a test of nothing. `CONTROL 18` is the refusal watched
    firing, one mutated member at a time, on every multi-member constant.

    **The refusal NAMES the member, not the tuple.** A refusal that reported
    only ``['src/', 'runtime/']`` would leave a reader to find the one-key typo
    among eleven paths — the same aggregate report one level up, which is the
    defect class this module is about.

    **Mechanism, chosen deliberately.** One :func:`tracked_under` call per
    member rather than a single ``git ls-files --error-unmatch``. The latter
    gives per-member semantics in ONE subprocess call and names the offending
    member in stderr, and it is cheaper — but its refusal reads ``exited 1``
    rather than ``matches no file tracked``, and `CONTROL 16` asserts that
    literal substring. Buying one subprocess call with an amendment to a
    shipped control's assertion is a weakening of exactly the thing this phase
    exists to strengthen. :data:`UAT_RECORDS` is the worst case at eleven
    calls and the whole module still runs in about two seconds.

    **The third refusal was added at the phase close and it closes a real
    hole**, found independently by two reviewers on the §3.1 panel and then
    measured. ``git diff --stat <base>..HEAD -- scr/`` exits ZERO and prints
    NOTHING — a misspelled pathspec is indistinguishable from a clean tree, and
    every emptiness assertion in this module is built on exactly that
    comparison. `CONTROL A` and `CONTROL 13` could not see it, because both
    diff :data:`CHANGED_TREE` rather than the constant the assertion they
    vouch for actually passes: rename :data:`TESTS_TREE` to ``tests-typo/`` and
    criterion 6's mechanical limb becomes vacuous while its own control stays
    green. That is this project's defect class — *a check that passes for a
    reason unrelated to what it claims to test* — arriving inside the machinery
    built to catch it, for the third time in this phase. `CONTROL 16` is the
    refusal watched firing on four near-miss spellings.

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
    for member in paths:
        if not tracked_under((member,)):
            raise AssertionError(
                f"the pathspec member {member!r} of {list(paths)} matches no"
                " file tracked by `git`, so `git diff` limited to it exits ZERO"
                " and prints NOTHING whatever the phase changed. A misspelled"
                " pathspec and a clean tree are indistinguishable, and every"
                " 'is empty' assertion built on this function would report"
                " success over a comparison that had no subject"
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


def asserted_pathspecs() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Every pathspec this module asserts a diff is EMPTY over, by name.

    A function rather than a module constant so that :data:`TESTS_TREE` — which
    is declared with `Check C` at the foot of this module, next to the claim it
    falsifies — is resolved when this runs rather than when the module is read.
    A second copy of the tuple up here would be one edit away from disagreeing
    with the constants it names, which is the drift this whole phase is about.
    """
    return (
        ("FABRIC", FABRIC),
        ("FENCE", FENCE),
        ("UAT_RECORDS", UAT_RECORDS),
        ("PINNED_FILES", PINNED_FILES),
        ("TESTS_TREE", TESTS_TREE),
        ("CHANGED_TREE", CHANGED_TREE),
    )


#: The names of the pathspec constants with MORE THAN ONE member — the set
#: `RR-1` exposes, and the set `CONTROL 18` is parametrized over.
#:
#: `FABRIC` has two members, `FENCE` five and `UAT_RECORDS` eleven. The other
#: three constants in :func:`asserted_pathspecs` are single-member and were
#: genuinely protected by the tuple-level truthiness test that `B-1` installed;
#: these three were not. **`CHANGED_TREE` is NOT a member of this roster** — it
#: is single-member (`.planning/`), and the `D-GATE-21` re-run record's claim
#: that it is multi-member is wrong. Recorded here because a later reader
#: holding that record will otherwise think a constant went missing.
#:
#: A frozen roster of NAMED constants per `D-21`, never a count — and it is
#: not allowed to be a transcription either. :func:`
#: test_the_multi_member_pathspec_roster_matches_the_modules_own_arity` requires
#: it to equal, by set equality on names, exactly the constants
#: :func:`asserted_pathspecs` resolves to more than one member. That is what
#: makes criterion 2 STANDING rather than true-on-the-day: a constant that
#: gains a second member tomorrow is dragged into `CONTROL 18` automatically,
#: and one that loses a member drops out of it automatically.
MULTI_MEMBER_PATHSPECS: frozenset[str] = frozenset(
    {"FABRIC", "FENCE", "UAT_RECORDS"}
)


def near_miss(member: str) -> str:
    """A one-key misspelling of one pathspec member: its last two characters swapped.

    DERIVED from the member rather than written down beside it. A literal table
    of ``{"src/": "scr/"}`` is one edit away from naming a member that no longer
    exists, and a control whose subject has drifted out of its own constant is
    the failure this phase exists to close, arriving by a third route.

    A trailing ``/`` is preserved so the mutation stays a directory pathspec:
    ``src/`` becomes ``scr/``, ``runtime/`` becomes ``runtiem/``,
    ``pyproject.toml`` becomes ``pyproject.tolm``, and a record path ending
    ``-VERIFICATION.md`` becomes ``-VERIFICATION.dm``. Every caller then hands
    the result to :func:`tracked_under` and REQUIRES an empty list, so a
    transposition that happened to name a real file is caught here rather than
    silently making the control vacuous.
    """
    stem, slash = (member[:-1], "/") if member.endswith("/") else (member, "")
    if len(stem) < 2:
        raise AssertionError(
            f"the pathspec member {member!r} is too short to misspell by"
            " transposition, so no near miss can be derived from it"
        )
    return f"{stem[:-2]}{stem[-1]}{stem[-2]}{slash}"


def multi_member_cases() -> tuple[tuple[str, str], ...]:
    """`CONTROL 18`'s subjects: each multi-member constant, first and last member.

    Two positions rather than one, because a single position cannot tell a
    per-member loop from a degenerate implementation that inspects only one end
    of the tuple. Mutating the FIRST member alone passes for an implementation
    that checks ``paths[0]``; mutating the LAST alone passes for one that checks
    ``paths[-1]``. Each case still mutates EXACTLY ONE member, which is what
    criterion 2 asks for.
    """
    return tuple(
        (name, position)
        for name in sorted(MULTI_MEMBER_PATHSPECS)
        for position in ("first", "last")
    )


def test_the_multi_member_pathspec_roster_matches_the_modules_own_arity() -> None:
    """:data:`MULTI_MEMBER_PATHSPECS` is derived, not transcribed.

    Set equality on NAMES against the constants :func:`asserted_pathspecs`
    resolves to more than one member. No count is asserted anywhere — what is
    compared is two sets of names, so `D-21` is untouched and the roster cannot
    drift away from the constants it claims to enumerate.
    """
    from_module = {name for name, spec in asserted_pathspecs() if len(spec) > 1}
    assert MULTI_MEMBER_PATHSPECS == from_module, (
        "the multi-member roster no longer matches the module's own arity."
        f" MULTI_MEMBER_PATHSPECS names {sorted(MULTI_MEMBER_PATHSPECS)};"
        f" asserted_pathspecs() resolves {sorted(from_module)} to more than one"
        " member. A constant that gained a member is unguarded by CONTROL 18"
        " until this roster is corrected, and a constant that lost one is being"
        " guarded by a control that can no longer mutate exactly one member"
    )


def test_every_asserted_pathspec_names_a_tracked_subject() -> None:
    """Each emptiness assertion is over a pathspec that names something real.

    Added at the phase close by the §3.1 panel. Every "this tree is untouched"
    assertion in this module resolves to `git diff --stat <base>..HEAD -- <spec>`
    being the empty string, and `git` returns the empty string just as
    willingly for a spec that matches nothing at all. Without this, a one-key
    typo in :data:`FABRIC`, :data:`FENCE`, :data:`PINNED_FILES`,
    :data:`UAT_RECORDS` or :data:`TESTS_TREE` silently converts the assertion
    it feeds into a test of nothing, and the run stays green.

    **Quantified per MEMBER, which is what the paragraph above always promised
    and what the code did not do.** It named five constants and said a one-key
    typo in any of them silently converts the assertion it feeds into a test of
    nothing — then tested the TUPLE, so a live sibling satisfied it on the
    typo's behalf for all three multi-member constants. Keeping the promise is
    the change; `RR-1` is the finding.

    Per `D-21` this carries NO count — it names each pathspec constant AND the
    member at fault, and requires every member to match at least one tracked
    path. A floor of "at least N files under `src/`" would be a carried number
    and would have to be re-edited by every later phase.
    """
    for name, spec in asserted_pathspecs():
        for member in spec:
            assert tracked_under((member,)), (
                f"the member {member!r} of the pathspec {name} = {list(spec)}"
                " matches no file tracked by `git`. Every assertion built on"
                f" {name} is then a diff that has lost that member's subject"
                " while its live siblings keep the pathspec looking real, and"
                " it prints nothing forever and reports a clean tree"
            )


def test_control_16_a_pathspec_that_names_nothing_is_refused() -> None:
    """CONTROL 16 — a misspelled pathspec refuses instead of reading clean.

    The subjects are deliberately **near misses of the real constants** rather
    than obvious nonsense, because a typo is what actually happens: `scr/` for
    `src/`, `runtimes/` for `runtime/`, `citation.py` for `citations.py`,
    `test/` for `tests/`.

    **The fifth subject is MIXED and it is the one that could not have passed
    before**: ``("src/", "runtimes/")`` — one live member and one typo. The
    four subjects above are all single-member, so the tuple-level truthiness
    test `B-1` installed refused every one of them and none could reach `RR-1`.
    A live sibling satisfies that test on the typo's behalf, and the pathspec
    then limits `git diff` to a tree the phase never touched while reporting it
    as the whole fence. See `CONTROL 18` for the same failure quantified over
    every multi-member constant this module asserts emptiness over.

    Each subject is first handed to raw `git diff` to establish that the
    mutation was genuinely INVISIBLE before this guard existed — exit 0, empty
    stdout, indistinguishable from the clean tree the real constants produce.
    A control that only watched the new refusal fire would not show what the
    refusal adds.
    """
    base = phase_base_commit()
    near_misses = (
        ("scr/",),
        ("runtimes/",),
        ("tools/lints/citation.py",),
        ("test/",),
        ("src/", "runtimes/"),
    )
    for spec in near_misses:
        raw = subprocess.run(
            ["git", "diff", "--stat", f"{base}..HEAD", "--", *spec],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert raw.returncode == 0 and raw.stdout == "", (
            f"the near-miss pathspec {list(spec)} was expected to be the silent"
            " kind — exit 0 and empty stdout — which is what makes it"
            f" indistinguishable from a clean tree. It returned"
            f" {raw.returncode}/{raw.stdout!r} instead, so this control is no"
            " longer about the failure it was written for"
        )
        try:
            result = fabric_diff(base, spec)
        except AssertionError as failure:
            assert "matches no file tracked" in str(failure), (
                f"{list(spec)} was refused for the wrong reason: {failure}"
            )
            continue
        raise AssertionError(
            f"the misspelled pathspec {list(spec)} returned {result!r} instead"
            " of refusing. An emptiness assertion over it would report a clean"
            " tree for a comparison that had no subject"
        )


def test_the_positive_control_a_real_pathspec_is_still_accepted() -> None:
    """CONTROL 16's discriminator. Red on everything is not a check.

    :data:`FABRIC` is the subject precisely because its diff IS empty — the
    phase touched no file under `src/` or `runtime/`. The guard must let that
    empty result through while refusing the empty result a typo produces, and
    those two are the same string.
    """
    assert fabric_diff(phase_base_commit(), FABRIC) == ""


@pytest.mark.parametrize("name,position", multi_member_cases())
def test_control_18_one_misspelled_member_of_a_multi_member_pathspec_is_refused(
    name: str, position: str
) -> None:
    """CONTROL 18 — a typo in ONE member of a multi-member pathspec is refused.

    `RR-1`, quantified. `B-1` closed the misspelled-pathspec hole for arity 1
    and the write-up said the hole was closed; it was closed for arity 1.
    :func:`tracked_under` was applied to the TUPLE, so
    ``fabric_diff(base, ("scr/", "runtime/"))`` returned the empty string with
    no refusal at all — ``runtime/`` matches seventy-one tracked files and
    satisfied the truthiness test on the typo's behalf, while the diff the
    assertion was built on had lost half its subject.

    Four things are established per subject, in order, and each is a run rather
    than an assumption:

    1. the mutated member matches NOTHING — :func:`tracked_under` is run on it
       and required to be empty, so the sabotage target is picked by running
       the predicate rather than by trusting :func:`near_miss`;
    2. every OTHER member is still live — which is precisely what makes the
       tuple-level test pass, and without it this control would degenerate into
       the all-members-broken case the pre-fix module already refused;
    3. the mutated tuple is the SILENT kind through raw `git diff` — exit 0,
       empty stdout, indistinguishable from the clean tree the real constant
       produces — exactly as `CONTROL 16` establishes for its own subjects, so
       the control shows what the refusal ADDS rather than only that it fires;
    4. :func:`fabric_diff` refuses, and the refusal NAMES the mutated member
       rather than the tuple. Naming the tuple would be the same aggregate
       report one level up.
    """
    base = phase_base_commit()
    real = dict(asserted_pathspecs())[name]
    index = 0 if position == "first" else len(real) - 1
    broken = near_miss(real[index])
    mutated = tuple(
        broken if at == index else member for at, member in enumerate(real)
    )

    assert not tracked_under((broken,)), (
        f"the near miss {broken!r} derived from {name}[{index}] ="
        f" {real[index]!r} matches a tracked file, so it is not a broken member"
        " at all and this control would be watching the guard ACCEPT a live"
        " pathspec. Pick the sabotage target by running the predicate"
    )
    survivors = tuple(member for at, member in enumerate(real) if at != index)
    assert tracked_under(survivors), (
        f"every member of {name} other than {real[index]!r} matches nothing"
        " either, so this subject is the all-members-broken case the tuple-level"
        " test already refused. It cannot reach RR-1 and proves nothing about"
        " per-member quantification"
    )

    raw = subprocess.run(
        ["git", "diff", "--stat", f"{base}..HEAD", "--", *mutated],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert raw.returncode == 0 and raw.stdout == "", (
        f"{name} with {broken!r} substituted for {real[index]!r} was expected to"
        " be the silent kind through raw `git diff` — exit 0 and empty stdout,"
        " which is what makes a half-broken pathspec indistinguishable from a"
        f" clean tree. It returned {raw.returncode}/{raw.stdout!r} instead, so"
        " this control is no longer about the failure it was written for"
    )

    try:
        result = fabric_diff(base, mutated)
    except AssertionError as failure:
        assert broken in str(failure), (
            f"{name} with {broken!r} substituted was refused, but the refusal"
            f" does not name the offending member: {failure}. A refusal that"
            " reports the whole tuple leaves a reader to find the one-key typo"
            " among eleven paths, and is the same aggregate report that let"
            " RR-1 through"
        )
        return
    raise AssertionError(
        f"{name} with the single member {real[index]!r} misspelled as"
        f" {broken!r} returned {result!r} instead of refusing. The surviving"
        f" members {list(survivors)} match tracked files and satisfy the"
        " pathspec guard on the typo's behalf, so every emptiness assertion"
        f" built on {name} reports a clean tree over a comparison that lost"
        " part of its subject"
    )


# ===========================================================================
# The strict parse, and Check B — channel agreement, vocabulary, one verdict
# per cell.
#
# The parse is `21-RESEARCH.md`'s algorithm, reimplemented here rather than
# shipped as a tool: locate the traceability table by its literal header line,
# take the contiguous run of `|` lines after the separator row, split on `|`,
# and require exactly three cells.
#
# THE WORKING-SET PREDICATE IS A MEMBERSHIP TEST AGAINST THE COMPLETE FAMILY,
# NEVER A STRING INEQUALITY AGAINST "Complete". A literal `!= "Complete"`
# reading yields 56 rows because it drags in `DCD-09` (`Complete as ruled`) and
# `DCD-10` (`Complete over the ruled scope`) — both already ruled on by Dave,
# both checked `[x]` in the checkbox channel, and both therefore treated as
# Complete by the ledger's other channel. The correct working set is 54. A
# later reader running `grep -vc "| Complete |"` will get 56 and conclude a row
# was skipped; that reader is holding the wrong predicate, not finding a gap.
# ===========================================================================

#: The ledger this module is about.
LEDGER_PATH = REPO_ROOT / ".planning" / "REQUIREMENTS.md"

#: The literal line the traceability table is located by. Matched exactly:
#: a fuzzy match on a misspelled header is how a parser reports "clean" over a
#: table it never found, which is `CONTROL 8`.
TABLE_HEADER = "| Requirement | Phase | Status |"

#: A traceability row is `| id | phase | status |` and nothing else.
CELLS_PER_ROW = 3

#: The checkbox channel. Anchored at `^- ` so an indented continuation
#: sub-bullet cannot be read as a requirement id.
CHECKBOX_LINE = re.compile(r"^- \[([ xX])\] \*\*([A-Z]+-\d+)\*\*", re.MULTILINE)

#: The LEADING verdict of a status cell: the alphabetic run at the very start,
#: cut at the first `(`, em dash or hyphen. Anchored at `^` so that `DCD-02`'s
#: second bolded phrase after the em dash is not read as a second verdict.
VERDICT_LEAD = re.compile(r"^([A-Za-z][A-Za-z ]*?)(?=\s*[(—-]|$)")

#: Any `**bolded**` run inside a cell, for the one-verdict-per-cell check.
BOLDED_RUN = re.compile(r"\*\*([^*]+)\*\*")

#: The three ways this ledger says Complete. `D-09` fixed the vocabulary at six
#: words precisely so a stricter scheme could not re-open `DCD-02`, `DCD-09`
#: and `DCD-10`, which Dave has already ruled on.
COMPLETE_FAMILY: frozenset[str] = frozenset(
    {"Complete", "Complete as ruled", "Complete over the ruled scope"}
)

#: `D-09`'s six words, plus `Pending`. `Pending` is admitted here because
#: unaudited rows still carried it while the phase ran, and an assertion that
#: every row is verdicted is red from the moment it lands until the final row
#: is written. What refuses a LEFTOVER `Pending` is `Check C` at the foot of
#: this module, landed by plan `21-06` once every row was written: a token in
#: this vocabulary is admissible anywhere, but a roster row reading the bare
#: `Pending` is refused by name. The two are deliberately separate — this set
#: says what a cell MAY read, `Check C` says what a roster row MUST NOT.
VERDICT_VOCABULARY: frozenset[str] = COMPLETE_FAMILY | frozenset(
    {"Partial", "Not built", "Orphaned", "Pending"}
)

#: This phase's OWN ten requirement ids, minted into both channels as `Pending`
#: by plan `21-01` task 2 and verdicted by plan `21-06` before the close panel.
#:
#: A FROZEN ROSTER OF NAMED IDS, per `D-21`, never a count. They are NOT
#: members of the 54-row working set this phase audits — that set is its own
#: frozen roster, taken by the strict parse at the pinned base.
#:
#: Provenance, as HISTORY and read by no assertion here: the traceability table
#: carried 133 rows at the pinned base and carries 143 from plan `21-01` task 2
#: forward. `D-21`'s binding consequence is that no standing check in this
#: phase hardcodes either figure — what is asserted is that the two channels
#: agree id-for-id on whatever the ledger contains. A reader who greps the
#: pinned base and counts 133 has not found a discrepancy.
PHASE_OWN_ROSTER: frozenset[str] = frozenset(
    {
        "RECON-01",
        "RECON-02",
        "RECON-03",
        "RECON-04",
        "RECON-05",
        "RECON-06",
        "RECON-07",
        "RECON-08",
        "RECON-09",
        "RECON-10",
    }
)


def ledger_text() -> str:
    """The real `.planning/REQUIREMENTS.md`, read from the repo root."""
    return LEDGER_PATH.read_text(encoding="utf-8")


def repeated_ids(req_ids: Sequence[str]) -> list[str]:
    """Every requirement id appearing more than once, NAMED and sorted.

    **Deliberately not ``len(rows) == len(set(ids))``.** A self-comparison
    would survive `D-21` on a technicality — it carries no number — but it
    reports a SHORTFALL, and a shortfall is not something a reader can act on.
    :func:`unverdicted` says so in its own docstring, and every other refusal
    in this module names its rows. So does this one.

    Returned sorted rather than in first-appearance order so a refusal message
    is stable across two parses of the same document.
    """
    seen: set[str] = set()
    twice: set[str] = set()
    for req_id in req_ids:
        if req_id in seen:
            twice.add(req_id)
        seen.add(req_id)
    return sorted(twice)


def traceability_rows(document_text: str) -> list[tuple[str, str, str]]:
    """`(id, phase, status)` triples from the traceability table.

    Rows are the CONTIGUOUS run of lines starting with `|` after the header's
    separator row, which is what stops the parse at the table's end rather
    than running on into the two-column evidence table further down the file.

    **This RAISES rather than returning an empty list when the header is not
    found or the run is empty.** That is a deliberate deviation from
    `tools/docs_tests/test_advisory_discharge.py`'s navigation reader, which
    returns an empty set when its heading is missing. The deviation exists
    because the consumers here are *disagreement counters*: a reader that
    returned nothing would let `channel_disagreements` report "zero
    disagreements, clean" over a table it never located. `CONTROL 8` is
    exactly that failure mode, watched refusing.
    """
    lines = document_text.splitlines()
    try:
        header_at = lines.index(TABLE_HEADER)
    except ValueError:
        raise AssertionError(
            "the traceability table header"
            f" {TABLE_HEADER!r} was not found in the document. A parser that"
            " returned nothing here would report a clean, agreeing, fully"
            " vocabularised ledger over a table it never located"
        ) from None
    rows: list[tuple[str, str, str]] = []
    for line in lines[header_at + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != CELLS_PER_ROW:
            raise AssertionError(
                f"traceability row {line!r} split into {cells!r}, which is not"
                " the three cells a `| id | phase | status |` row has"
            )
        rows.append((cells[0], cells[1], cells[2]))
    if not rows:
        raise AssertionError(
            "the traceability table header was found but no rows followed it."
            " Every check built on this parse would pass over nothing"
        )
    twice = repeated_ids([req_id for req_id, _phase, _status in rows])
    if twice:
        raise AssertionError(
            f"duplicate requirement ids in the traceability table: {twice}."
            " Every consumer of this parse keys by id — four dict builds and"
            " two comprehensions — so one of the two rows survives and the"
            " other's phase and verdict vanish without a finding. The"
            " ledger's own `Coverage` sentence says each requirement is"
            " mapped to exactly one phase; a repeated id falsifies it and"
            " nothing observed that. `uncited_verdicts` is worse still: it"
            " APPENDS citations per id, so a duplicated row's citations MERGE"
            " and an UNCITED duplicate is masked by its cited twin"
        )
    return rows


def verdict_token(status_cell: str) -> str:
    """The LEADING bolded verdict of a status cell, and only that one.

    `DCD-02`'s cell reads `**Partial** (plans …) — … **Pending by design** …`.
    A reader that took the last bolded run, or every bolded run, would call
    that row `Pending` or would call it two verdicts. It is one: `Partial`.
    `CONTROL 9b` is the positive half of that discrimination.
    """
    bare = status_cell.replace("**", "").strip()
    match = VERDICT_LEAD.match(bare)
    if match is None:
        return ""
    return match.group(1).strip()


def cell_verdicts(status_cell: str) -> set[str]:
    """Every verdict a status cell asserts, across BOTH ways this module reads one.

    The union of two readings that were previously separate and could disagree
    in silence:

    * the LEADING token — :func:`verdict_token` — when it is in
      :data:`VERDICT_VOCABULARY`; and
    * every ``**bolded**`` run of the cell that is in
      :data:`VERDICT_VOCABULARY`.

    **A cell asserts one thing. When this set has more than one member, the
    cell does not, and the two readers disagree about which one it is.** That
    is `RR-2`: ``Complete — later **Partial** (…)`` is `Complete` to the
    leading-token reader, one bolded verdict to the bolded-run reader, and was
    accepted by eight gates with zero refusals — on a working-set row that
    visibly reads `**Partial**`.

    **This rule was CHOSEN BY MEASUREMENT, from three candidates, run across
    every row of the real traceability table.** The counts are recorded as
    HISTORY and are read by no assertion here (`D-21`); what a later reader
    needs from them is the SHAPE of the two rejected rules, not their
    arithmetic:

    * **This rule — the union, at most one member: flagged ZERO rows.** It
      therefore required no ledger edit and surfaced no hidden bad row.
    * *"Any vocabulary word appearing anywhere in the cell"* flagged thirteen
      rows, among them `DCD-02`, `DCD-09`, `DCD-10`, `CPS-03`, `EXAM-02` and
      three of this phase family's own `RECON-` rows — several of which Dave
      has personally ruled on. `D-09` fixed the vocabulary at six words
      precisely to stop a stricter scheme re-opening them, and `CONTROL 15`
      states the same thing from the other side: a reader that hunts for a
      vocabulary word anywhere in the prose finds one in almost any honest
      sentence.
    * *"The leading verdict must be bolded"* flagged seventy-five — a bare
      leading verdict is a long-standing convention across `HARD-04`, the
      `PERF-`, `DEMO-`, `ERGO-`, `SUBQ-` and `CPS-` lanes, `CLNT-23`..`32`,
      `DOCS-22` and the six `VAC-` rows. Roughly half the table.

    What makes the union rule safe rather than lucky, also measured: NO
    bare-lead row carries any bolded vocabulary word, and NO row carries a
    bolded vocabulary word different from its leading token. (At the research
    anchor the table held 143 rows and at this writing 149, plan `21.1-01`
    having minted `VAC-01`..`06`; all three rules were re-measured against 149
    and the shape of every result held. A reader who counts 143 has not found
    a discrepancy.)

    **Known residual `R-α`, stated rather than designed around:** this does NOT
    catch ``Complete — later Partial (…)`` with BOTH verdicts unbolded. There
    is no bolded vocabulary word, the leading token is `Complete`, and the
    disagreement is invisible to every reader in this module including this
    one. That shape is WIDER than what criteria 3 and 4 name, and every
    predicate measured that catches it flags rows already ruled on. It is
    recorded open in `21.1-02-SUMMARY.md`, not closed.

    :func:`verdict_token` is deliberately NOT changed. The verdict of a row is
    the word its cell opens with; `CONTROL 15` holds that property.
    """
    verdicts = {
        run.group(1).strip()
        for run in BOLDED_RUN.finditer(status_cell)
        if run.group(1).strip() in VERDICT_VOCABULARY
    }
    leading = verdict_token(status_cell)
    if leading in VERDICT_VOCABULARY:
        verdicts.add(leading)
    return verdicts


def checkbox_channel(document_text: str) -> dict[str, bool]:
    """Requirement id to checked-state, from the checkbox list.

    Raises rather than returning an empty mapping, for the reason
    :func:`traceability_rows` states: an empty channel makes every comparison
    against it trivially agreeable.

    **It refuses a repeated id INDEPENDENTLY of the table parser**, and
    independently is the operative word. The two channels are two claims; a
    guard on one says nothing about the other, and this dict comprehension
    would keep the LAST bullet for a repeated id no matter what
    :func:`traceability_rows` refused. Measured pre-fix on a duplicated
    `HARD-02` whose twin carried the opposite tick: the channel resolved the
    row to the TWIN's value, so a duplicated bullet silently decided what the
    checkbox channel said about a row and `channel_disagreements` then
    compared the table against a claim nobody wrote.
    """
    matched = [match.group(2) for match in CHECKBOX_LINE.finditer(document_text)]
    found = {
        match.group(2): match.group(1).lower() == "x"
        for match in CHECKBOX_LINE.finditer(document_text)
    }
    if not found:
        raise AssertionError(
            "the checkbox channel parsed to nothing. Either the document is"
            " not the ledger or the bullet shape changed; either way a"
            " comparison against an empty channel agrees with everything"
        )
    twice = repeated_ids(matched)
    if twice:
        raise AssertionError(
            f"duplicate requirement ids in the checkbox channel: {twice}. The"
            " mapping keeps the LAST bullet, so the earlier one's tick is"
            " discarded without a finding and every comparison against this"
            " channel is then about a claim nobody wrote"
        )
    return found


def vocabulary_offenders(document_text: str) -> list[str]:
    """One message per status cell whose leading verdict is not a known word."""
    offenders: list[str] = []
    for req_id, _phase, status in traceability_rows(document_text):
        token = verdict_token(status)
        if token not in VERDICT_VOCABULARY:
            offenders.append(
                f"{req_id} carries the verdict {token!r}, which is not one of"
                f" {sorted(VERDICT_VOCABULARY)}. `D-09` fixes the vocabulary at"
                " six words and no seventh is minted; a new word here is a"
                " ruling for Dave, not an executor's choice"
            )
    return offenders


def doubled_verdicts(document_text: str) -> list[str]:
    """One message per status cell asserting more than one verdict.

    A cell reading `**Complete** **Partial** (…)` is ambiguous about what the
    row claims, and the leading-token reader above would silently report the
    first. `CONTROL 11` is this check watched refusing exactly that shape.

    **Reads :func:`cell_verdicts`, and reads nothing else.** Until plan
    `21.1-02` this counted BOLDED runs only, so `Complete — later **Partial**`
    — an unbolded lead and a later bolded verdict — yielded exactly one bolded
    verdict and was accepted, while :func:`verdict_token` read the same cell as
    `Complete`. Two readers, disagreeing, neither refusing: `RR-2`.
    `CONTROL 19` is that shape watched refusing.
    """
    offenders: list[str] = []
    for req_id, _phase, status in traceability_rows(document_text):
        verdicts = sorted(cell_verdicts(status))
        if verdicts[1:]:
            offenders.append(
                f"{req_id}'s status cell asserts the verdicts {verdicts!r}."
                " A row claims one thing; a reader taking the leading token"
                " would report only the first, and a reader taking the bolded"
                " runs would report only the others"
            )
    return offenders


def channel_disagreements(document_text: str) -> list[str]:
    """One message per disagreement between the ledger's two status channels.

    `D-02`: the checkbox list and the traceability table are two channels
    saying the same thing, and a verdict written into one and not the other is
    the drift this phase must not introduce. Every message NAMES the offending
    id, because a count of disagreements is not something anyone can act on.
    """
    table = {
        req_id: status for req_id, _phase, status in traceability_rows(document_text)
    }
    boxes = checkbox_channel(document_text)
    messages: list[str] = []
    for req_id in sorted(set(table) - set(boxes)):
        messages.append(
            f"{req_id} is in the traceability table and not in the checkbox"
            " list — a row minted into one channel only"
        )
    for req_id in sorted(set(boxes) - set(table)):
        messages.append(
            f"{req_id} is in the checkbox list and not in the traceability"
            " table — a row minted into one channel only"
        )
    for req_id in sorted(set(table) & set(boxes)):
        reads_complete = verdict_token(table[req_id]) in COMPLETE_FAMILY
        if boxes[req_id] is not reads_complete:
            messages.append(
                f"{req_id} reads {table[req_id]!r} in the traceability table"
                f" and checked={boxes[req_id]} in the checkbox list. The two"
                " channels disagree about whether this requirement is"
                " discharged"
            )
    return messages


def _doctored(document_text: str, old: str, new: str) -> str:
    """Replace exactly one occurrence, refusing when the anchor is not unique.

    A control that silently replaced nothing — because its anchor drifted —
    would hand the checker an UNMODIFIED document and then assert a refusal
    that never came, or worse, pass because something else was wrong. The
    uniqueness check is what keeps a control attributable to its mutation.
    """
    occurrences = document_text.count(old)
    if occurrences != 1:
        raise AssertionError(
            f"the control anchor {old!r} appears {occurrences} times in the"
            " document; a mutation that lands nowhere, or lands twice, is not"
            " the mutation the control claims to make"
        )
    return document_text.replace(old, new)


def _table_line(document_text: str, req_id: str) -> str:
    """The one traceability line for `req_id`, or a refusal.

    Added by plan `21-06`, and the reason is worth recording. `CONTROL 6`,
    `CONTROL 9` and `CONTROL 11` were written against the literal anchor
    ``| RECON-10 | Phase 21 | Pending |``, which was correct for the five
    waves in which the phase's own rows were unverdicted and stopped existing
    the moment this plan wrote their verdicts. :func:`_doctored` refuses an
    anchor that is not unique, so all three went red rather than silently
    doctoring nothing — but the lesson is the general one: **a control anchored
    on a literal string is anchored on a snapshot of the subject.** Resolving
    the line at run time makes the mutation survive every later edit to the
    row's contents while still refusing if the row is gone.
    """
    matches = [
        line
        for line in document_text.splitlines()
        if line.startswith(f"| {req_id} | ")
    ]
    if not matches or matches[1:]:
        raise AssertionError(
            f"{req_id} matched {matches!r} traceability lines; a control that"
            " doctors nothing, or doctors twice, is not the control it claims"
        )
    return matches[0]


def _checkbox_line(document_text: str, req_id: str) -> str:
    """The one checkbox bullet for `req_id`, or a refusal.

    The checkbox twin of :func:`_table_line`, added by plan `21.1-03` for
    `CONTROL 21`, and it exists for the same reason: a control anchored on a
    literal bullet is anchored on a snapshot of a line that Phase 21 rewrote
    row by row. Resolved at run time, refusing when the bullet is absent or
    doubled — so a control that doctors nothing cannot then assert a refusal
    that never came.

    The anchor is :data:`CHECKBOX_LINE`'s own shape rather than a prefix
    match, because the bullet carries its tick between the dash and the id and
    a `startswith` test would have to guess which tick is there.
    """
    matches = [
        line
        for line in document_text.splitlines()
        if CHECKBOX_LINE.match(line) is not None
        and CHECKBOX_LINE.match(line).group(2) == req_id  # type: ignore[union-attr]
    ]
    if not matches or matches[1:]:
        raise AssertionError(
            f"{req_id} matched {matches!r} checkbox bullets; a control that"
            " doctors nothing, or doctors twice, is not the control it claims"
        )
    return matches[0]


# --- Preconditions — a vacuous pass is the failure this module exists to prevent.


def test_the_ledger_parses_to_a_populated_table() -> None:
    """The table is found, every row is three cells, and two known ids are in it.

    Per `D-21` this carries NO row count. A NAMED member is a stronger floor
    than a number: it does not have to be re-edited every time a row is
    minted, and it cannot be silently satisfied by a row that happens to
    restore an expected total. Naming one of the phase's own rows is also what
    proves the wave-1 mint landed in THIS channel.
    """
    ids = [req_id for req_id, _phase, _status in traceability_rows(ledger_text())]
    assert "HARD-01" in ids, "the ledger's first requirement id is missing"
    assert "RECON-10" in ids, (
        "the phase's own last row is not in the traceability table — the wave-1"
        " mint did not land in this channel"
    )


def test_the_checkbox_channel_parses_to_a_populated_list() -> None:
    """The other channel, held to the same floor and to no count."""
    boxes = checkbox_channel(ledger_text())
    assert "HARD-01" in boxes
    assert "RECON-10" in boxes, (
        "the phase's own last row is not in the checkbox list — the wave-1"
        " mint landed in one channel only, which is the drift `D-02` forbids"
    )


def test_the_parse_does_not_depend_on_the_process_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Run from anywhere, this module still reads the ledger it is about."""
    monkeypatch.chdir(tmp_path)
    assert TABLE_HEADER in ledger_text()


# --- Check B, shipped: the properties true of a partially filled ledger ---


def test_the_two_status_channels_agree() -> None:
    """Criterion 10 as `D-21` amended it: id-for-id, on every id there is."""
    disagreements = channel_disagreements(ledger_text())
    assert disagreements == [], (
        "the ledger's two status channels have drifted apart (`D-02`). The id"
        " set is read from the ledger rather than compared against a carried"
        " number (`D-21`); the channels were measured at ZERO drift on"
        " 2026-08-21, and this phase must not introduce the first:\n"
        + "\n".join(disagreements)
    )


def test_every_verdict_token_is_in_the_vocabulary() -> None:
    """Criterion 2's mechanical limb: the six words, and no seventh."""
    offenders = vocabulary_offenders(ledger_text())
    assert offenders == [], "\n".join(offenders)


def test_no_status_cell_carries_two_verdict_tokens() -> None:
    """A row claims one thing. `CONTROL 11` is this gate watched refusing."""
    offenders = doubled_verdicts(ledger_text())
    assert offenders == [], "\n".join(offenders)


def test_every_recon_row_is_present_in_both_channels() -> None:
    """The wave-1 mint's own floor: the phase's own rows exist in BOTH channels.

    **Amended by plan `21-06`, which is the plan wave 1 said would amend it.**
    As landed, this test additionally asserted that every `RECON-` row read a
    bare `Pending` and was unticked — true for the five waves in which the
    rows were minted and not yet audited, and false the moment their verdicts
    were written. The Pending expectation is RETIRED rather than relaxed: what
    replaces it is stricter, not looser. `test_every_phase_own_row_carries_a_verdict`
    now requires the opposite — a vocabulary token that is NOT a bare
    `Pending` — with `CONTROL 14` watching that refusal fire. What stays here
    is the floor that outlives both states: the ids are in both channels, and
    the two channels agree about each one.
    """
    table = {
        req_id: status for req_id, _phase, status in traceability_rows(ledger_text())
    }
    boxes = checkbox_channel(ledger_text())
    for req_id in sorted(PHASE_OWN_ROSTER):
        assert req_id in table, f"{req_id} is missing from the traceability table"
        assert req_id in boxes, f"{req_id} is missing from the checkbox list"
        reads_complete = verdict_token(table[req_id]) in COMPLETE_FAMILY
        assert boxes[req_id] is reads_complete, (
            f"{req_id} reads {table[req_id]!r} in the traceability table and"
            f" checked={boxes[req_id]} in the checkbox list — the phase's own"
            " rows are held to `D-02` exactly as the rows they audit are"
        )


# --- CONTROL 6-9, 9b, 11: channel_disagreements and the parser, watched refusing


def test_the_unmodified_document_passes() -> None:
    """The baseline, so every refusal below is attributable to its mutation."""
    text = ledger_text()
    assert channel_disagreements(text) == []
    assert vocabulary_offenders(text) == []
    assert doubled_verdicts(text) == []


def test_control_6_a_row_completed_in_one_channel_only_is_refused() -> None:
    """The commonest drift: a verdict written into the table and not the list."""
    real = ledger_text()
    doctored = _doctored(
        real,
        _table_line(real, "RECON-10"),
        "| RECON-10 | Phase 21 | Complete |",
    )
    messages = channel_disagreements(doctored)
    assert messages, "a row Complete in one channel and unticked in the other passed"
    assert any("RECON-10" in message for message in messages), (
        f"the refusal fired but named no id: {messages!r}. A count of"
        " disagreements is not something a reader can act on"
    )


def test_control_7_an_id_present_in_only_one_channel_is_refused() -> None:
    """A row minted into the table and forgotten in the list."""
    line = [
        candidate
        for candidate in ledger_text().splitlines()
        if candidate.startswith("- [ ] **RECON-10**")
    ][0]
    doctored = _doctored(ledger_text(), line + "\n", "")
    messages = channel_disagreements(doctored)
    assert any("RECON-10" in message for message in messages), (
        f"deleting an id from one channel was not refused by name: {messages!r}"
    )


def test_control_8_a_misspelled_table_header_refuses_rather_than_reporting_clean() -> (
    None
):
    """The vacuity floor. A parser that returned nothing here would report
    "zero disagreements, clean" over a table it never found — which is this
    project's recurring defect shape, a check structurally incapable of
    reporting the thing it appears to report."""
    doctored = _doctored(
        ledger_text(), TABLE_HEADER, "| Requirment | Phase | Status |"
    )
    try:
        rows = traceability_rows(doctored)
    except AssertionError as failure:
        assert "was not found" in str(failure)
        return
    raise AssertionError(
        f"a misspelled header parsed to {len(rows)} rows instead of raising"
    )


@pytest.mark.parametrize("minted", ["Done", "Shipped", "Closed"])
def test_control_9_a_verdict_outside_the_vocabulary_is_refused(minted: str) -> None:
    """Criterion 2's mechanical limb, watched refusing three plausible words."""
    real = ledger_text()
    doctored = _doctored(
        real,
        _table_line(real, "RECON-10"),
        f"| RECON-10 | Phase 21 | {minted} |",
    )
    offenders = vocabulary_offenders(doctored)
    assert any(minted in message for message in offenders), (
        f"the verdict {minted!r} was accepted, or refused without being named:"
        f" {offenders!r}"
    )


def test_control_9b_the_second_bolded_phrase_in_dcd_02_is_not_a_second_verdict() -> None:
    """The POSITIVE half of the one-verdict-per-cell discrimination.

    Without it, a reader that reported every bolded run would pass `CONTROL 9`
    and `CONTROL 11` by refusing a compliant row — red on everything is not a
    discriminator. `DCD-02`'s real cell is the subject, taken from the ledger
    rather than retyped, so the control cannot drift away from its subject.
    """
    cell = [
        status
        for req_id, _phase, status in traceability_rows(ledger_text())
        if req_id == "DCD-02"
    ][0]
    assert "Pending by design" in cell, (
        "`DCD-02`'s cell no longer carries a second bolded phrase, so this"
        " control has stopped testing the thing it was written for"
    )
    assert verdict_token(cell) == "Partial", (
        f"the leading verdict of {cell!r} read as {verdict_token(cell)!r}"
    )
    assert doubled_verdicts(ledger_text()) == []


def test_control_11_a_cell_with_two_verdict_tokens_is_refused() -> None:
    """The NEGATIVE control for the one-verdict-per-cell gate.

    It lands in the same wave as the gate it falsifies, deliberately. It
    operates on a doctored in-memory cell and needs no written verdicts, so
    nothing justifies deferring it — in a phase whose thesis is that an
    unfalsified gate is not a gate, shipping the gate five waves before its
    refusal is ever watched fire would be exactly that.
    """
    real = ledger_text()
    doctored = _doctored(
        real,
        _table_line(real, "RECON-10"),
        "| RECON-10 | Phase 21 | **Complete** **Partial** (doctored) |",
    )
    offenders = doubled_verdicts(doctored)
    assert any("RECON-10" in message for message in offenders), (
        f"a cell carrying two bolded verdicts was accepted: {offenders!r}"
    )


# ===========================================================================
# Check A — a cited path in a status cell names a full, repo-relative, EXISTING
# file, and `::` is reserved to Python.
#
# THE D-17 READING, recorded here because this is where it bites, and marked as
# a READING rather than a relaxation granted to make a criterion reachable.
# Success criterion 3 asks for evidence in `path::symbol` form; its operative
# clause is its own final one, "that the citation lint resolves". The lint
# anchors its `::` pattern to `\.py`, so a markdown document has NO
# `path::symbol` form at all, and roughly twenty-four of the fifty-four rows
# this phase audits are about documentation. So: `path::symbol` stays preferred
# and is REQUIRED wherever the evidence is Python; where the evidence is a
# document, an anchored line citation the lint resolves is admissible. D-06 is
# unchanged — full repo-relative paths, bare basenames REFUSED. Ruled by Dave
# 2026-08-21 and logged as `D-IMPL-172` in `docs/DECISIONS.md`.
#
# WHERE THIS REFUSAL APPLIES, AND WHERE IT DOES NOT. It is scoped to the
# TRACEABILITY STATUS CELL, deliberately, because `D-01` puts the evidence
# there and that is therefore the evidence surface. Plan `21-02` also appends
# the long form to each row's checkbox-channel twin; those copies are a READING
# CONVENIENCE, not a second evidence surface, and they are covered only by the
# repo-wide citation lint — the surface that carries the two silent-drop holes.
# A reader who assumes the refusal covers both places this phase writes
# citations has assumed too much, which is why it is said here.
#
# THE ZERO-CITATION GUARD LANDED ONE WAVE LATE, ON PURPOSE, AND HERE IS THE
# MEASUREMENT THAT FORCED IT. At this phase's pinned base there were ZERO
# citation-shaped tokens in any status cell, scanned with the lint's own symbol
# and line-citation patterns plus this module's wider symbol form. A guard
# raising on zero citations would have FAILED on landing and would have
# reddened `ci-core` for five waves, in a phase whose own Makefile contract is
# that `ci-core` stays green from wave one. So plan `21-01` landed the zero-ROW
# limb only — false the day it shipped, therefore honest the day it shipped —
# and plan `21-02` task 1 landed the zero-CITATION limb immediately AFTER
# writing the first eight rows' citations. RELOCATED, never weakened: the limb
# raises, `CONTROL 5b` watches it raise, and
# `test_the_scan_finds_citations_to_check` proves the real ledger yields
# citations for `test_every_cited_path_in_a_status_cell_resolves_as_written` to
# be about.
# ===========================================================================

#: A `path::symbol` token with ANY suffix, and permitting a leading dot so a
#: `.planning/...` path is visible too. Deliberately wider than the lint's
#: `NODE_ID`, which is hard-anchored to `\.py`: a `::symbol` citation on a
#: non-Python path matches NEITHER of the lint's patterns and is therefore
#: entirely invisible to it, so it has to be refused BY NAME here or it is
#: refused nowhere.
LOOSE_NODE_ID = re.compile(
    r"(?P<path>[A-Za-z0-9_.][A-Za-z0-9_./+-]*\.[A-Za-z0-9_+-]+)"
    r"::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"
)

#: A LINE citation — `path/to/file.md:12`, `file.py:12-34` — with the same
#: single character added to the front of the path group that
#: :data:`LOOSE_NODE_ID` adds above: a leading dot.
#:
#: **Without it a `.planning/` document could not be cited AT ALL, in either
#: direction.** The lint's `CITATION` opens its path group `[A-Za-z0-9_]`,
#: which excludes `.`, so a cell citing `.planning/…/RECORD.md:1` matched one
#: character LATE and yielded `planning/…/RECORD.md` — a path that is not in
#: the tree, refused as absent. The `::symbol` spelling is refused too, because
#: :func:`refuse_unresolvable` reserves `::` to Python and a `.planning/`
#: record is markdown. Cite it with the dot and the citation is refused; omit
#: it and `uncited_verdicts` refuses the row. There was no legal spelling, and
#: nothing in this module said so.
#:
#: `D-07` stands — the lint is byte-identical and this is a MODULE-LOCAL
#: widening, on exactly the precedent :data:`LOOSE_NODE_ID` set one shape up.
#:
#: **It REPLACES `CITATION` in :func:`citations_in_status_cells`'s tuple and is
#: not added beside it.** Measured both ways: appended or prepended, the tuple
#: extracts the citation TWICE — `planning/…` AND `.planning/…` — because the
#: dedup there is a `set[str]` over the PATH STRING, and the truncated twin is
#: then refused by name. Order cannot suppress it. One shape, one pattern, no
#: twin by construction.
#:
#: Measured when it landed: the real ledger yielded the SAME 127 citations
#: before and after, set-equal AND order-equal, with zero added and zero
#: dropped — no existing citation begins with a dot. Those numbers are HISTORY
#: and are read by no assertion (`D-21`); the standing property is
#: :func:`test_each_widened_pattern_subsumes_the_lint_pattern_it_replaced`.
LOOSE_CITATION = re.compile(
    r"(?P<path>[A-Za-z0-9_.][A-Za-z0-9_./+-]*\.(?:"
    + "|".join(CITED_SUFFIXES)
    + r"))"
    r":(?P<lines>\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)(?![\w-])"
)

_REPO_INDEX_CACHE: dict[str, list[str]] = {}

#: A NAMED path this module already depends on, required to resolve through
#: the index before :func:`_index` will hand it to anything.
#:
#: It is the subject of `the positive citation control`
#: (:func:`test_the_positive_control_a_real_citation_is_not_refused`), chosen
#: there precisely because its basename is AMBIGUOUS in this repo — there are
#: two `client.py`. So an index that still resolves it is an index whose
#: ambiguity branch has a live subject, which is the property the anchor is
#: for.
#:
#: A NAME and not a floor, per `D-21`. "More than five thousand basenames"
#: would be a carried number that every later phase had to re-edit, and a
#: growing tree would satisfy it while the entries this module actually
#: consults had been pruned away.
INDEX_ANCHOR = "src/ccf/client/client.py"


def _index() -> dict[str, list[str]]:
    """`tools.lints.citations.repo_index` over this repo, computed once.

    The lint's own index rather than a bare `rglob`, because `repo_index`
    prunes `SKIP_DIRS` — and a bare walk over a live agent worktree makes
    EVERY basename ambiguous, which is how an ambiguity check silently stops
    checking anything.

    **It REFUSES an index that resolved nothing rather than returning it, and
    the test is that it resolves :data:`INDEX_ANCHOR`.** `RR-6`: an index with
    no subject makes :func:`refuse_unresolvable` report ZERO unresolvable
    citations, which is indistinguishable from a clean ledger. Measured on a
    thinned index, the two branches that read this mapping behave differently
    and BOTH are wrong:

    * the ambiguity branch degrades to the weaker bare-basename message and
      happens to go red, but only because `CONTROL 1` asserts the word
      AMBIGUOUS — it is guarded by ACCIDENT, not by design; and
    * the moved-path branch — the one this module's own docstring calls "the
      second silent hole" it exists to dodge — returns SILENCE, and an
      on-disk-but-unindexed path is ACCEPTED.

    The anchor form is chosen over "refuse an empty mapping" deliberately: an
    emptiness test accepts a THINNED index, and thinned is the shape that
    makes the moved-path branch go quiet. `CONTROL 22` carries both subjects
    and the thinned one is the discriminating half.
    """
    if not _REPO_INDEX_CACHE:
        _REPO_INDEX_CACHE.update(repo_index(REPO_ROOT))
    basename = INDEX_ANCHOR.rsplit("/", maxsplit=1)[-1]
    if INDEX_ANCHOR not in _REPO_INDEX_CACHE.get(basename, []):
        raise AssertionError(
            f"the resolver index does not resolve `{INDEX_ANCHOR}`, a path"
            " this module already cites in its own positive citation control."
            f" Its entries for `{basename}` are"
            f" {_REPO_INDEX_CACHE.get(basename, [])}. An index with no subject"
            " does not make `refuse_unresolvable` fail — it makes it return"
            " ZERO unresolvable citations, which reads exactly like a clean"
            " ledger. The moved-path branch stops checking and says nothing,"
            " and the ambiguity branch is guarded only by `CONTROL 1`"
            " happening to assert the word AMBIGUOUS"
        )
    return _REPO_INDEX_CACHE


def symbol_cited_paths(document_text: str) -> list[tuple[str, str]]:
    """`(id, path)` for every `path::symbol` token in a status cell, any suffix."""
    found: list[tuple[str, str]] = []
    for req_id, _phase, status in traceability_rows(document_text):
        for match in LOOSE_NODE_ID.finditer(status):
            found.append((req_id, match.group("path")))
    return found


def citations_in_status_cells(document_text: str) -> list[tuple[str, str]]:
    """`(id, cited_path)` for every citation-shaped token inside a status cell.

    **ONE PATTERN PER CITATION SHAPE.** There are two shapes — `path::symbol`
    and `path.ext:NN[-MM]` — and this tuple carries the module-local widening
    of each, :data:`LOOSE_NODE_ID` and :data:`LOOSE_CITATION`, rather than the
    widening AND the lint pattern it widens.

    That is a structural choice with a measured reason. A widened pattern
    carried BESIDE the lint's extracts the same citation twice whenever the two
    disagree about where the path starts: appended or prepended, a cell citing
    `.planning/…/RECORD.md:1` yields BOTH `planning/…/RECORD.md` and
    `.planning/…/RECORD.md`, because the dedup below is a `set[str]` over the
    PATH STRING. The truncated twin names a path that is not in the tree and
    :func:`refuse_unresolvable` then refuses it by name — so the row stays
    uncitable, behind a pattern that looks like it landed. Order cannot
    suppress the twin; only carrying one pattern per shape can.

    `NODE_ID` was DROPPED rather than assumed redundant. Measured over the real
    ledger's status cells before it went, it and :data:`LOOSE_NODE_ID` returned
    the same `(id, path)` pairs and the SETS WERE EQUAL. The subsumption is
    kept standing by
    :func:`test_each_widened_pattern_subsumes_the_lint_pattern_it_replaced`,
    which is what stops a later narrowing of either widened pattern dropping
    citations in silence.
    """
    found: list[tuple[str, str]] = []
    for req_id, _phase, status in traceability_rows(document_text):
        seen: set[str] = set()
        patterns = (LOOSE_NODE_ID, LOOSE_CITATION)
        for pattern in patterns:
            for match in pattern.finditer(status):
                cited = match.group("path")
                if cited not in seen:
                    seen.add(cited)
                    found.append((req_id, cited))
    return found


def refuse_unresolvable(document_text: str) -> list[str]:
    """One message per citation that does not name a full, existing file.

    Two reasons this exists, both measured against the shipped lint.

    **The lint silently drops a citation whose basename is ambiguous.** With
    two `client.py` in the tree, `client.py::NoSuchThing` produces no finding
    at all — it is counted as an ambiguous path and skipped. **And it silently
    drops a citation to a path that does not exist**: `src/ccf/nope/nope.py::x`
    is counted as unresolved and skipped. The same silence, two holes.

    A single existence predicate closes both without opening the lint. A path
    that exists as written makes the lint's resolver return at its DIRECT
    branch before the index is ever consulted, so the ambiguity branch becomes
    structurally unreachable for this file's citations. `D-07` stands: the
    repo-wide hole is NOT fixed here, and it stays named.

    It also catches what the lint cannot see at all — a file MOVE. The lint
    catches a symbol RENAME (a wrong symbol on a real path is a finding); a
    citation whose path moved away is simply unresolved and dropped.

    The predicate is ``(REPO_ROOT / cited).is_file()`` and NOT ``exists()``, so
    a citation naming a DIRECTORY is refused rather than quietly resolving. A
    directory is never evidence: nothing in it is the thing the row claims.

    **Two vacuity limbs, landed one wave apart, and the gap was deliberate.**
    A zero-ROW parse raises here since plan ``21-01``, because a zero-row parse
    was false the day it landed. A zero-CITATION parse raises since plan
    ``21-02`` task 1, and not before: measured with this module's own extractor
    at the phase's pinned base, ``citations_in_status_cells(ledger_text())``
    returned **zero** tokens across every status cell, so the guard would have
    failed on landing and reddened ``ci-core`` for five waves. It was
    RELOCATED to the wave that writes the first citations, never weakened —
    ``CONTROL 5b`` watches it refuse, and
    :func:`test_the_scan_finds_citations_to_check` is the precondition proving
    the real ledger now yields citations for the refusal to be about.
    """
    rows = traceability_rows(document_text)
    if not rows:
        raise AssertionError(
            "the traceability table parsed to no rows, so 'every citation is a"
            " full path' would pass over nothing. A refusal that has never had"
            " a subject is not a refusal"
        )
    cited_pairs = citations_in_status_cells(document_text)
    if not cited_pairs:
        raise AssertionError(
            "the traceability table has rows but not one citation-shaped token"
            " in any status cell, so 'every citation is a full path' is"
            " quantified over the empty set and is trivially true. A verdict"
            " resting on no citation is a claim, not a finding (`D-03`)"
        )
    symbol_paths = set(symbol_cited_paths(document_text))
    index = _index()
    messages: list[str] = []
    for req_id, cited in cited_pairs:
        basename = cited.rsplit("/", maxsplit=1)[-1]
        candidates = index.get(basename, [])
        if "/" not in cited:
            if candidates[1:]:
                messages.append(
                    f"{req_id} cites `{cited}`, a BARE BASENAME that is"
                    f" AMBIGUOUS in this repo — it names {candidates}. The"
                    " citation lint DROPS an ambiguous basename without a"
                    " finding, which is the hole this refusal exists to dodge"
                    " from the outside (`D-06`, `D-07`)"
                )
            else:
                messages.append(
                    f"{req_id} cites `{cited}`, a BARE BASENAME. `D-06`"
                    " requires a FULL repo-relative path, not an unambiguous"
                    " one: a basename that is unique today becomes ambiguous"
                    " the day someone adds a second file with that name, and"
                    " the citation is then dropped in silence"
                )
            continue
        target = REPO_ROOT / cited
        if not target.is_file():
            if target.is_dir():
                messages.append(
                    f"{req_id} cites `{cited}`, which is a DIRECTORY. The"
                    " predicate is `is_file()` and not an existence test on"
                    " purpose — a directory is never the evidence a row"
                    " claims, and an existence test would let it through"
                )
            else:
                messages.append(
                    f"{req_id} cites `{cited}`, which is not in the tree at"
                    " all. The citation lint counts this as an unresolved path"
                    " and drops it WITHOUT a finding — the second silent hole,"
                    " and the one that catches a file MOVE"
                )
            continue
        if (req_id, cited) in symbol_paths and not cited.endswith(".py"):
            messages.append(
                f"{req_id} cites `{cited}` with a `::symbol`, but the path is"
                " not Python. The lint's symbol pattern is hard-anchored to"
                " `.py`, so this citation matches neither of its patterns and"
                " is invisible to it. Where the evidence is a document, use an"
                " anchored line citation the lint resolves (`D-IMPL` reading"
                " of criterion 3, recorded above)"
            )
            continue
        if candidates and cited not in candidates:
            messages.append(
                f"{req_id} cites `{cited}`, which is on disk but absent from"
                f" the resolver's index, whose entries for `{basename}` are"
                f" {candidates}. The lint would treat the basename as"
                " AMBIGUOUS and drop the citation"
            )
    return messages


def _document_with_citation(cited: str) -> str:
    """A minimal well-formed ledger carrying exactly one citation.

    Built rather than doctored from the real file because the subject each
    control needs is a SPECIFIC malformed citation, and doctoring a real cell
    into one would make the control depend on which row happened to be
    verdicted at the time it ran.
    """
    return "\n".join(
        (
            "- [ ] **TEST-01**: a control fixture, not a requirement",
            "",
            TABLE_HEADER,
            "|-------------|-------|--------|",
            f"| TEST-01 | Phase 21 | Pending (`{cited}`) |",
            "",
        )
    )


def test_every_cited_path_in_a_status_cell_resolves_as_written() -> None:
    """Criterion 4, shipped: every citation names a full, existing file.

    **No longer vacuous, and the thing that makes it non-vacuous is a test
    rather than a claim.** It was vacuous through plan `21-01`, because the
    ledger carried no citations at all; plan `21-02` task 1 wrote the first
    ones and landed both the zero-citation limb inside
    :func:`refuse_unresolvable` and the precondition below in the same commit.
    The refusal itself needed nothing added: it has always been the assertion
    that a citation, IF present, resolves as written.
    """
    assert refuse_unresolvable(ledger_text()) == []


def test_the_scan_finds_citations_to_check() -> None:
    """The precondition. The real ledger yields citations, so the gate has work.

    **The measurement that forced this test to be written one wave after the
    gate it guards.** Run against this phase's pinned base,
    ``citations_in_status_cells(ledger_text())`` returned an EMPTY list —
    across every status cell, scanned with the citation lint's own symbol and
    line-citation patterns plus :data:`LOOSE_NODE_ID`. So
    :func:`test_every_cited_path_in_a_status_cell_resolves_as_written` passed
    over nothing for the whole of plan `21-01`, and this assertion could not
    have been written there without failing. Plan `21-02` task 1 wrote the
    first citations into eight `CLNT` rows and then landed this, in that
    order, so that the guard is honest from the moment it exists.

    Per `D-21` this carries NO count. Non-emptiness is the property; a floor of
    fifteen would have to be re-edited by every later wave and could be
    silently satisfied by a citation nobody meant to write.
    """
    found = citations_in_status_cells(ledger_text())
    assert found, (
        "not one status cell in the real ledger carries a citation-shaped"
        " token, so `test_every_cited_path_in_a_status_cell_resolves_as_written`"
        " is quantified over the empty set and reports green over nothing. That"
        " was TRUE at this phase's pinned base and is why this test landed in"
        " plan `21-02` rather than `21-01`; it is not true again without a"
        " regression"
    )


# --- CONTROL 1-5: refuse_unresolvable, watched refusing ---


def test_control_1_an_ambiguous_basename_is_refused() -> None:
    """A basename with two paths behind it — the lint's own silent drop."""
    messages = refuse_unresolvable(_document_with_citation("client.py::ask"))
    assert messages, "an ambiguous bare basename was accepted"
    assert any("AMBIGUOUS" in message for message in messages), (
        f"refused, but without naming the ambiguity: {messages!r}"
    )


def test_control_2_a_unique_basename_is_refused_too() -> None:
    """`D-06` is FULL paths, not unambiguous paths.

    A basename that resolves to exactly one file today is still refused,
    because it becomes ambiguous the day a second file takes that name — and
    on that day the citation is dropped in silence rather than reported.
    """
    messages = refuse_unresolvable(_document_with_citation("spine.py::ask"))
    assert any("BARE BASENAME" in message for message in messages), (
        f"a unique bare basename was accepted: {messages!r}"
    )


def test_control_3_a_path_that_does_not_exist_is_refused() -> None:
    """The SECOND silent-drop hole: an unresolved path is not a finding."""
    cited = "src/ccf/nope/nope.py::x"
    messages = refuse_unresolvable(_document_with_citation(cited))
    assert any("src/ccf/nope/nope.py" in message for message in messages), (
        f"a nonexistent path was accepted, or refused without being named:"
        f" {messages!r}"
    )


def test_control_4_a_symbol_citation_on_a_non_python_path_is_refused() -> None:
    """`::` is reserved to Python because the lint's pattern is anchored to it.

    Two subjects, and the second is the discriminating one. A nonexistent
    markdown path is refused for the ordinary reason — it is not in the tree.
    An EXISTING markdown path carrying a `::symbol` is refused for the reason
    this control is about: the lint cannot match it, so nothing else would
    ever refuse it.
    """
    absent = refuse_unresolvable(_document_with_citation("docs/foo.md::heading"))
    assert absent, "a `::symbol` on a nonexistent markdown path was accepted"
    present = refuse_unresolvable(
        _document_with_citation("docs/DECISIONS.md::heading")
    )
    assert any("not Python" in message for message in present), (
        f"a `::symbol` on an EXISTING markdown path was accepted, or refused"
        f" for the wrong reason: {present!r}"
    )


def test_control_4b_a_directory_path_is_refused() -> None:
    """Why the predicate is `is_file()` and not an existence test.

    The subject is a real tracked directory whose name carries a dot, so a
    citation pattern can actually name it. Under an existence test it would
    resolve and the row would carry a "citation" pointing at no evidence at
    all.
    """
    cited = ".planning/phases/15.6-decision-completeness-and-defect-closure::x"
    messages = refuse_unresolvable(_document_with_citation(cited))
    assert any("DIRECTORY" in message for message in messages), (
        f"a directory citation was accepted, or refused for the wrong reason:"
        f" {messages!r}"
    )


def test_control_5_a_table_with_no_rows_raises() -> None:
    """The wave-one vacuity floor: no subject means refuse, never return clean."""
    empty = "\n".join((TABLE_HEADER, "|-------------|-------|--------|", ""))
    try:
        messages = refuse_unresolvable(empty)
    except AssertionError as failure:
        assert "no rows" in str(failure)
        return
    raise AssertionError(
        f"a table with no rows returned {messages!r} instead of raising; every"
        " citation check built on it would then pass over nothing"
    )


def test_control_5b_a_table_with_no_citations_raises() -> None:
    """The vacuity floor `21-01` could not land: rows, verdicts, no citations.

    ``CONTROL 5`` catches a table with no ROWS. This catches the subtler one —
    a table full of confidently-verdicted rows that cite nothing at all, over
    which "every citation is a full repo-relative path" is trivially true. The
    subject is doctored in memory and carries two rows whose status cells hold
    a bolded verdict and a qualifying clause and no citation, which is exactly
    the shape a lazy audit produces.
    """
    doctored = "\n".join(
        (
            "- [ ] **TEST-01**: a control fixture, not a requirement",
            "- [ ] **TEST-02**: a second one, so the table is not a single row",
            "",
            TABLE_HEADER,
            "|-------------|-------|--------|",
            "| TEST-01 | Phase 21 | **Complete** — someone looked once |",
            "| TEST-02 | Phase 21 | **Partial** — and wrote it down |",
            "",
        )
    )
    assert traceability_rows(doctored), "the control's own subject is empty"
    try:
        messages = refuse_unresolvable(doctored)
    except AssertionError as failure:
        assert "not one citation-shaped token" in str(failure)
        return
    raise AssertionError(
        f"a table of verdicts carrying no citations returned {messages!r}"
        " instead of raising. `D-03` is that a verdict rests on a citation the"
        " lint resolves; a refusal quantified over zero citations enforces"
        " nothing while reporting green"
    )


def test_the_positive_control_a_real_citation_is_not_refused() -> None:
    """Red on everything is not a discriminator.

    The subject is deliberately a path whose BASENAME is ambiguous in this
    repo — there are two `client.py`. It is accepted anyway, which is the
    whole design: a path that exists as written resolves at the direct branch
    and the ambiguity never arises.
    """
    cited = "src/ccf/client/client.py::ProductClient"
    assert refuse_unresolvable(_document_with_citation(cited)) == []


# ===========================================================================
# Check C — completeness. Every row of the working set carries exactly one
# verdict, the phase's own rows are held to the same gate, and `tests/` is
# untouched.
#
# WHY THIS LANDS IN THE PHASE'S LAST EXECUTION PLAN AND NOT ITS FIRST. An
# assertion that every row needing a verdict has one is RED from the moment it
# lands until the final row is written, and the `Makefile`'s `ci-core` target
# says in its own help text that it must stay green from wave one onward. Plan
# `21-01` therefore shipped every property that is true of a PARTIALLY filled
# ledger and deliberately withheld this one. Every row is written now, so the
# assertion is true — and from this commit forward the ledger cannot silently
# lose a verdict, cannot carry two on one row, and cannot shrink either roster.
#
# THE WORKING-SET PREDICATE IS MEMBERSHIP AGAINST `COMPLETE_FAMILY`, NEVER A
# STRING INEQUALITY AGAINST "Complete". The section banner above states the
# measurement; it is restated here because this is the section that consumes
# it: the literal `!= "Complete"` reading yields 56 by dragging in `DCD-09`
# (`Complete as ruled`) and `DCD-10` (`Complete over the ruled scope`), both
# already ruled on by Dave and both checked `[x]` in the other channel.
# ===========================================================================

#: The `tests/` tree, for criterion 6's mechanical limb (`D-05`). Its own
#: constant rather than a member of `FENCE`, because it falsifies a different
#: claim: `FENCE` is "the audit closed no gap it discovered", and this is "the
#: audit wrote no test in order to manufacture a citation for itself".
TESTS_TREE: tuple[str, ...] = ("tests/",)

#: The fifty-four rows this phase was commissioned to verdict — a FROZEN ROSTER
#: OF NAMED IDS, per `D-21`, and never a count.
#:
#: Provenance: produced by the strict parse of `.planning/REQUIREMENTS.md` at
#: this phase's pinned base, keeping every row whose leading verdict token was
#: NOT in `COMPLETE_FAMILY`. It is frozen precisely because the phase MUTATES
#: the predicate that produced it: every verdict written moves a row into the
#: Complete family, so re-deriving the working set from the file as it stands
#: today returns a shrinking set, and an assertion over a shrinking set reports
#: green the instant the last row is written no matter which rows were skipped.
#: `test_the_working_set_roster_is_exactly_the_strict_parse_at_the_pinned_base`
#: re-derives it from the base and compares ID FOR ID, so the constant cannot
#: silently drift from the thing it claims to be.
#:
#: THE TEN `RECON-` ROWS ARE NOT MEMBERS, and their absence is structural
#: rather than a judgement call. They are this phase's OWN requirements, minted
#: by plan `21-01` task 2 AFTER the base was pinned, so a parse taken at that
#: base cannot contain them by construction. They are audited by
#: `PHASE_OWN_ROSTER` and `test_every_phase_own_row_carries_a_verdict` — a
#: separate roster and a separate assertion, because a phase does not audit
#: itself inside the set it was commissioned to audit. Held to the same gate,
#: and held to it BEFORE the close panel rather than after Dave's approval.
#:
#: History, read by no assertion here (`D-21`): the table carried 133 rows at
#: the pinned base and carries 143 from plan `21-01` task 2 forward, and 54 of
#: the former were outstanding. A reader who greps and counts has not found a
#: discrepancy; no check in this module compares against any of those figures.
WORKING_SET_ROSTER: frozenset[str] = frozenset(
    {
        # Phase 17 and Phase 18's client lane.
        "CLNT-01",
        "CLNT-02",
        "CLNT-03",
        "CLNT-04",
        "CLNT-05",
        "CLNT-06",
        "CLNT-07",
        "CLNT-08",
        "CLNT-09",
        "CLNT-10",
        "CLNT-11",
        "CLNT-12",
        "CLNT-13",
        "CLNT-14",
        "CLNT-15",
        "CLNT-16",
        "CLNT-17",
        "CLNT-18",
        "CLNT-19",
        "CLNT-20",
        "CLNT-21",
        "CLNT-22",
        # Phase 14's documentation lane.
        "DOCS-01",
        "DOCS-02",
        "DOCS-03",
        "DOCS-04",
        "DOCS-05",
        "DOCS-06",
        # Phase 16's lane — the eighteen reported as a two-sided split.
        "DOCS-07",
        "DOCS-08",
        "DOCS-09",
        "DOCS-10",
        "DOCS-11",
        "DOCS-12",
        "DOCS-13",
        "DOCS-14",
        "DOCS-15",
        "DOCS-16",
        "DOCS-17",
        "DOCS-18",
        "DOCS-19",
        "DOCS-20",
        "DOCS-21",
        "DOCS-23",
        "DOCS-24",
        "DOCS-25",
        # Phase 9's hardening lane.
        "HARD-01",
        "HARD-02",
        "HARD-03",
        # Phase 13's examples lane.
        "EXAM-01",
        "EXAM-02",
        "EXAM-03",
        # The two rows a naive `grep -c "| Pending |"` misses, which is the
        # miscount this phase exists to correct: one bolded, one `Partial`.
        "CPS-03",
        "DCD-02",
    }
)


def base_ledger_text() -> str:
    """`.planning/REQUIREMENTS.md` as it stood at the pinned base.

    Raises on a non-zero `git` exit for the reason :func:`fabric_diff` does:
    an empty string from a failed command is indistinguishable from an empty
    string from a real read, and a roster comparison against an empty parse
    would be a comparison against nothing. In CI this is the assertion that
    needs full history — a depth-1 clone cannot resolve the base, `git`
    exits non-zero, and this raises rather than reporting a clean roster.
    """
    completed = subprocess.run(
        ["git", "show", f"{phase_base_commit()}:.planning/REQUIREMENTS.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "`git show <pinned base>:.planning/REQUIREMENTS.md` exited"
            f" {completed.returncode}, so the working-set roster cannot be"
            " re-derived and the comparison below would be against nothing."
            " In CI this is a shallow checkout.\nstderr:"
            f" {completed.stderr.strip()}"
        )
    return completed.stdout


def derived_working_set(document_text: str) -> frozenset[str]:
    """Every id whose leading verdict is NOT in the Complete family.

    A function of its argument so it can be pointed at the pinned base's copy
    of the ledger rather than at today's — which is the whole point, since
    today's is the mutated one.
    """
    return frozenset(
        req_id
        for req_id, _phase, status in traceability_rows(document_text)
        if verdict_token(status) not in COMPLETE_FAMILY
    )


def roster_verdicts(
    document_text: str, roster: frozenset[str], roster_name: str
) -> list[tuple[str, str]]:
    """`(id, leading verdict)` for every member of `roster`, or a refusal.

    **It raises when a roster id is absent from the table**, and that refusal
    is the reason this function exists at all. An assertion written as "for
    every row the parser matched, check the verdict" passes over the empty set
    when the parser matches nothing, and passes over fifty-three rows when one
    is deleted — reporting green on a ledger that lost a row. `CONTROL 12` and
    `CONTROL 14` are that refusal watched firing, on each roster.
    """
    table = {
        req_id: status for req_id, _phase, status in traceability_rows(document_text)
    }
    absent = sorted(roster - set(table))
    if absent:
        raise AssertionError(
            f"{absent} named in {roster_name} but absent from the traceability"
            " table. A completeness assertion that skipped them would report"
            " green over a ledger that had quietly lost a row"
        )
    return [(req_id, verdict_token(table[req_id])) for req_id in sorted(roster)]


def working_set(document_text: str) -> list[tuple[str, str]]:
    """The fifty-four, each with its leading verdict token."""
    return roster_verdicts(
        document_text, WORKING_SET_ROSTER, "the frozen working-set roster"
    )


def phase_own_verdicts(document_text: str) -> list[tuple[str, str]]:
    """The phase's own ten, each with its leading verdict token."""
    return roster_verdicts(
        document_text, PHASE_OWN_ROSTER, "the phase's own roster"
    )


def unverdicted(pairs: Sequence[tuple[str, str]]) -> list[str]:
    """One message per row still lacking a verdict, NAMING the row.

    A red run has to name the rows rather than report a shortfall: "three rows
    are unverdicted" is not something a reader can act on, and it is one digit
    away from being the kind of carried count `D-21` forbids.
    """
    return [
        f"{req_id} reads {verdict!r}, which is not a verdict — it is either the"
        " bare `Pending` a row carries before it is audited, or a token outside"
        f" {sorted(VERDICT_VOCABULARY)}"
        for req_id, verdict in pairs
        if verdict == "Pending" or verdict not in VERDICT_VOCABULARY
    ]


def roster_rows_with_two_verdicts(
    document_text: str, roster: frozenset[str]
) -> list[str]:
    """One message per roster row whose cell asserts more than one verdict.

    **Reads :func:`cell_verdicts` — the SAME predicate**
    :func:`doubled_verdicts` reads, and this is the load-bearing part of plan
    `21.1-02` rather than a tidy-up. Until that plan these two carried
    byte-identical inline copies of the bolded-run reading, which is one edit
    away from the ledger-wide gate and the gate the working set is actually
    held to disagreeing about what a cell says. That is `RR-2`'s own defect
    class one level up, and
    :func:`test_the_two_one_verdict_gates_read_the_same_predicate` is what
    keeps it from returning.
    """
    offenders: list[str] = []
    for req_id, _phase, status in traceability_rows(document_text):
        if req_id not in roster:
            continue
        verdicts = sorted(cell_verdicts(status))
        if verdicts[1:]:
            offenders.append(
                f"{req_id}'s status cell asserts the verdicts {verdicts!r}."
                " Criterion 1 is that no row carries two"
            )
    return offenders


#: The two verdicts criterion 3 exempts from citing evidence, because what they
#: assert is an ABSENCE and an absence has no file to point at. `D-10` requires
#: them to name the absence specifically instead — a directory listing, a
#: `Makefile` target, a grep that returns zero — and that is a judgement no
#: assertion can make. What IS mechanical is the other side: a row claiming a
#: PRESENCE must point at one.
CITATION_EXEMPT_VERDICTS: frozenset[str] = frozenset({"Not built", "Orphaned"})


def uncited_verdicts(
    document_text: str, roster: frozenset[str], roster_name: str
) -> list[str]:
    """One message per roster row that claims a presence and cites nothing.

    **Added at the phase close, by the §3.1 cross-AI panel, which found the
    same hole from two directions independently.** Criterion 3 — and
    `RECON-02`, which claims it `Complete` — say that *every verdict other than
    `Not built` and `Orphaned` cites its evidence in the status cell*. Nothing
    in this module enforced that per row. :func:`refuse_unresolvable` answers a
    different question: *given a citation, does it resolve* — plus a single
    global floor that SOME citation exists somewhere in the table. So a row
    reading ``**Complete** — asserted without evidence`` was invisible to every
    gate here, measured, as long as any other row anywhere carried a citation.

    **That is not hypothetical: it is how `DCD-02` survived five waves.** Its
    cell carried a verdict, two plan numbers and no file at all, and the only
    thing that found it was plan `21-06` running criterion 3's predicate by
    hand across the roster. A defect found by hand once is a defect that
    returns; this is that predicate made standing.

    **Roster-scoped, deliberately, and this is the load-bearing choice.**
    Seventy-nine rows elsewhere in the table carry a Complete-family verdict
    and no citation — the `CPS-`, `DCD-` and `CLNT-23`..`32` lanes, all ruled
    on in earlier phases and all outside this phase's working set by `D-19`'s
    explicit carve-out. A ledger-wide form of this check would be red on the
    day it landed for rows `D-11` forbids this phase to touch, and would be
    narrowed or deleted on its first run — leaving the one place it can honestly
    hold enforced by nothing. The pre-existing debt is REPORTED to Dave in
    `21-CLOSE-REVIEWS.md` rather than smoothed over, which is the same
    disposition `D-07` and `D-20` take.

    Raises on an empty roster, for the reason every other checker here does: a
    per-row rule quantified over no rows is trivially satisfied.
    """
    if not roster:
        raise AssertionError(
            f"{roster_name} is empty, so 'every verdicted row cites its"
            " evidence' is quantified over nothing and is trivially true"
        )
    cited: dict[str, list[str]] = {}
    for req_id, path in citations_in_status_cells(document_text):
        cited.setdefault(req_id, []).append(path)
    offenders: list[str] = []
    for req_id, verdict in roster_verdicts(document_text, roster, roster_name):
        if verdict in CITATION_EXEMPT_VERDICTS:
            continue
        if not cited.get(req_id):
            offenders.append(
                f"{req_id} reads {verdict!r} and its status cell carries no"
                " citation-shaped token at all. Criterion 3: a verdict other"
                " than `Not built` or `Orphaned` rests on evidence a reader can"
                " follow, and a verdict resting on no citation is a claim, not"
                " a finding (`D-03`). This is the shape `DCD-02` carried"
                " undetected for five waves"
            )
    return offenders


# --- Check C, shipped ---


def test_the_working_set_roster_is_exactly_the_strict_parse_at_the_pinned_base() -> (
    None
):
    """The frozen roster is re-derived from the base and compared ID FOR ID.

    **Never by length**, per `D-21` and per the idiom
    :func:`test_the_uat_roster_matches_the_records_on_disk` already sets in
    this module. A length comparison is weaker in a way that matters here: it
    cannot see a SWAP — drop `CLNT-17` and add `CLNT-23` and the number is
    unmoved — and it is itself the hardcoded row count `D-21` removed from
    criterion 10 after this phase's own first action falsified it.

    The re-derivation is also the non-vacuity proof. If
    :func:`base_ledger_text` returned nothing the derived set would be empty
    and this comparison would fail loudly, rather than a roster assertion
    passing over a set nobody produced.
    """
    derived = derived_working_set(base_ledger_text())
    missing_from_roster = sorted(derived - WORKING_SET_ROSTER)
    absent_from_base = sorted(WORKING_SET_ROSTER - derived)
    assert derived == WORKING_SET_ROSTER, (
        "the frozen working-set roster and the strict parse at the pinned base"
        " have diverged.\n  outstanding at the base but not in the roster:"
        f" {missing_from_roster}\n  in the roster but not outstanding at the"
        f" base: {absent_from_base}"
    )
    table = {
        req_id for req_id, _phase, _status in traceability_rows(ledger_text())
    }
    lost = sorted(WORKING_SET_ROSTER - table)
    assert not lost, (
        f"{lost} are in the roster and no longer in the traceability table —"
        " a row the phase was commissioned to verdict was dropped instead"
    )


def test_every_row_in_the_working_set_carries_a_verdict() -> None:
    """Criterion 1, shipped: no row missed.

    Held back from plan `21-01` deliberately and landed here, in the plan that
    writes the last verdicts. The subject is the frozen roster rather than a
    re-derivation from today's file, because every verdict written moves a row
    out of a re-derived working set — so a re-derived assertion reports green
    the moment the last row is written, whichever rows were skipped.
    """
    offenders = unverdicted(working_set(ledger_text()))
    assert offenders == [], (
        "rows the phase was commissioned to verdict are still unverdicted."
        " They are named rather than counted, because a count is not something"
        " a reader can act on:\n" + "\n".join(offenders)
    )


def test_no_row_in_the_working_set_carries_two_verdicts() -> None:
    """Criterion 1's other half: and none carrying two.

    `CONTROL 11` — landed in plan `21-01` with the ledger-wide gate it
    falsifies — is the refusal watched firing on a doctored doubled cell.
    """
    offenders = roster_rows_with_two_verdicts(ledger_text(), WORKING_SET_ROSTER)
    assert offenders == [], "\n".join(offenders)


def test_no_test_was_written_to_manufacture_a_citation() -> None:
    """Criterion 6's MECHANICAL limb (`D-05`), and only the mechanical limb.

    The phase's one new check lives in `tools/docs_tests/`, so `tests/` must be
    byte-identical to the pinned base. That a named test genuinely GUARDS the
    property a row claims is a judgement no assertion can make, and it is
    attested by inspection rather than by this test — said plainly here so
    that a reader does not take a green run as more than it is.

    `CONTROL 13` proves the comparison is comparing something.
    """
    diff = fabric_diff(phase_base_commit(), TESTS_TREE)
    assert diff == "", (
        "this phase wrote under `tests/`. `D-05` forbids it: a test written"
        " during the audit to give a row a name to cite is a citation the"
        " phase manufactured for itself, which is the opposite of evidence"
        f":\n{diff}"
    )


def test_every_phase_own_row_carries_a_verdict() -> None:
    """The phase's own ten, held to the gate they impose on the fifty-four.

    And held to it BEFORE the close panel, not after. Rows verdicted inside
    the gate checkpoint would carry verdicts no reviewer and no approver had
    seen — the ledger-debt pattern this phase was commissioned to end,
    reproduced one level up.
    """
    offenders = unverdicted(phase_own_verdicts(ledger_text()))
    assert offenders == [], (
        "the phase's own requirement rows are unverdicted while the rows it"
        " audits are not:\n" + "\n".join(offenders)
    )
    doubled = roster_rows_with_two_verdicts(ledger_text(), PHASE_OWN_ROSTER)
    assert doubled == [], "\n".join(doubled)


def test_every_verdicted_roster_row_cites_its_evidence() -> None:
    """Criterion 3's per-row limb, made standing at the phase close.

    Both rosters at once — the fifty-four this phase audits and the ten it
    minted for itself — because `RECON-02` claims this property of the whole
    audit and the phase's own rows are held to the gate they impose.

    Until this landed, criterion 3 was enforced only in the direction that does
    not matter on its own: a citation that IS written must resolve. A row that
    wrote none was clean. `CONTROL 17` is the refusal watched firing, and
    `CONTROL 17b` is the discriminator proving it does not simply refuse
    everything — a `Not built` row rightly carries no citation.
    """
    roster = WORKING_SET_ROSTER | PHASE_OWN_ROSTER
    offenders = uncited_verdicts(
        ledger_text(), roster, "the working set and the phase's own roster"
    )
    assert offenders == [], (
        "a row this phase verdicted claims a presence and cites nothing. The"
        " rows are named rather than counted:\n" + "\n".join(offenders)
    )


def test_control_17_a_verdicted_row_stripped_of_its_citation_is_refused() -> None:
    """CONTROL 17 — the refusal that would have caught `DCD-02` in wave 1.

    The subject is verified to reach the branch under test before it is
    doctored: `HARD-02` is asserted ABSENT from the offender list on the real
    ledger first, so a green-before/red-after pair is attributable to the
    mutation and to nothing else. That is the wave-1 lesson — a control whose
    subject is already an offender tests nothing — made structural.

    The doctored cell is deliberately *fluent*: it reads like a verdict
    somebody thought about. That is exactly the shape `DCD-02` carried, and the
    shape a reader skims past.
    """
    real = ledger_text()
    roster = WORKING_SET_ROSTER | PHASE_OWN_ROSTER
    victim = "HARD-02"
    name = "the working set and the phase's own roster"
    assert not any(
        victim in message for message in uncited_verdicts(real, roster, name)
    ), (
        f"{victim} already cites nothing on the real ledger, so this control"
        " cannot distinguish its mutation from the status quo"
    )
    doctored = _doctored(
        real,
        _table_line(real, victim),
        f"| {victim} | Phase 9 | **Complete** — verified against the tree |",
    )
    offenders = uncited_verdicts(doctored, roster, name)
    assert offenders, "a `Complete` resting on no citation at all was accepted"
    assert any(victim in message for message in offenders), (
        f"the refusal fired but did not name {victim}: {offenders!r}. A count"
        " of uncited rows is not something a reader can act on"
    )


def test_control_17b_a_not_built_row_may_cite_nothing() -> None:
    """CONTROL 17b — the discriminator. Red on everything is not a check.

    `D-10` is that a `Not built` row names its absence specifically rather than
    pointing at a file, because there is no file to point at. A per-row
    citation rule that refused those rows too would be refusing the ledger's
    own honest shape, and would be relaxed within a day.

    Both halves are asserted on the SAME doctored cell, differing only in the
    verdict word, so the discrimination is attributable to the verdict and to
    nothing else about the row.
    """
    real = ledger_text()
    roster = WORKING_SET_ROSTER | PHASE_OWN_ROSTER
    victim = "DOCS-15"
    name = "the working set and the phase's own roster"
    line = _table_line(real, victim)
    absence = "the page is absent from `public/` and every grep returns zero"
    exempt = _doctored(
        real, line, f"| {victim} | Phase 16 | **Not built** — {absence} |"
    )
    assert not any(
        victim in message for message in uncited_verdicts(exempt, roster, name)
    ), (
        f"a `Not built` row citing no file was refused. `D-10` requires it to"
        " name an absence, and an absence has no path — a rule that refuses"
        " this refuses the ledger's honest shape"
    )
    claimed = _doctored(
        real, line, f"| {victim} | Phase 16 | **Complete** — {absence} |"
    )
    assert any(
        victim in message for message in uncited_verdicts(claimed, roster, name)
    ), (
        "the SAME cell reading `Complete` instead of `Not built` was also"
        " accepted, so the check is not discriminating on the verdict at all"
    )


# --- CONTROL 10, 12, 13, 14: Check C, watched refusing ---
#
# CONTROL 11 is NOT here. It landed in plan `21-01` task 2, in the same wave as
# the ledger-wide one-verdict-per-cell gate it falsifies, and it is not
# duplicated or renumbered here. The numbering continues at 10, 12, 13, 14 for
# that reason.
#
# Each control hands the SAME function the shipped assertion calls a doctored
# IN-MEMORY document. Nothing on disk is mutated.


def test_control_10_a_ledger_with_one_row_still_pending_is_refused() -> None:
    """CONTROL 10 — the control that matters for criterion 1.

    Without it, an assertion over a roster the parser failed to match would
    pass over an empty set and report that every row is verdicted. The subject
    is verified to reach the branch under test: it is asserted ABSENT from the
    offender list on the real document first, so a green-before/red-after pair
    is attributable to the mutation and to nothing else.
    """
    real = ledger_text()
    victim = "HARD-02"
    assert not any(victim in message for message in unverdicted(working_set(real))), (
        f"{victim} is already reported unverdicted on the real ledger, so this"
        " control cannot distinguish its mutation from the status quo"
    )
    doctored = _doctored(
        real, _table_line(real, victim), f"| {victim} | Phase 9 | Pending |"
    )
    offenders = unverdicted(working_set(doctored))
    assert offenders, "a roster row returned to `Pending` was accepted"
    assert any(victim in message for message in offenders), (
        f"the refusal fired but did not name {victim}: {offenders!r}. A red run"
        " that reports a shortfall rather than a row is not actionable"
    )


def test_control_12_a_roster_id_absent_from_the_table_is_refused() -> None:
    """CONTROL 12 — a roster row deleted from the table refuses by name.

    The failure this refuses is quieter than `CONTROL 10`'s: a deleted row is
    not an unverdicted row, it is no row at all, and a completeness check
    written as "for every row the parser matched" would report green over the
    fifty-three that survived.
    """
    real = ledger_text()
    victim = "EXAM-03"
    assert working_set(real), "the control's own subject is empty"
    doctored = _doctored(real, _table_line(real, victim) + "\n", "")
    try:
        pairs = working_set(doctored)
    except AssertionError as failure:
        assert victim in str(failure), (
            f"the refusal fired but did not name {victim}: {failure}"
        )
        return
    raise AssertionError(
        f"deleting {victim} from the traceability table left"
        f" {len(pairs)} pairs and no refusal; the assertion would then have"
        " reported green over a ledger that lost a row"
    )


def test_control_13_a_changed_tests_tree_would_be_detected() -> None:
    """CONTROL 13 — the non-vacuity twin of the `tests/`-untouched assertion.

    `CONTROL A` makes the same argument for the fabric, the fence, the
    verification records and the citation lint; this one is stated separately
    because it falsifies a different claim and because criterion 6 rests on it
    alone. The helper is reused rather than reimplemented: a second diff path
    could pass here and be broken there.
    """
    diff = fabric_diff(phase_base_commit(), CHANGED_TREE)
    assert diff.strip(), (
        "`git diff` produced nothing for a tree this phase demonstrably writes"
        f" to ({list(CHANGED_TREE)}), so the `tests/` emptiness above says"
        " nothing about `tests/` and criterion 6's mechanical limb is vacuous"
    )


def test_control_14_a_phase_own_row_returned_to_pending_is_refused() -> None:
    """CONTROL 14 — `CONTROL 10`'s shape, aimed at the phase's own roster.

    Without it, a phase-own assertion over a roster the parser failed to match
    would pass over an empty set — and the rows it passed over would be the
    ten this phase minted for itself, which is the least-watched corner of the
    ledger and therefore the one most worth a control.
    """
    real = ledger_text()
    victim = "RECON-08"
    assert not any(
        victim in message for message in unverdicted(phase_own_verdicts(real))
    ), (
        f"{victim} is already reported unverdicted on the real ledger, so this"
        " control cannot distinguish its mutation from the status quo"
    )
    doctored = _doctored(
        real, _table_line(real, victim), f"| {victim} | Phase 21 | Pending |"
    )
    offenders = unverdicted(phase_own_verdicts(doctored))
    assert any(victim in message for message in offenders), (
        f"a phase-own row returned to `Pending` was accepted, or refused"
        f" without being named: {offenders!r}"
    )


def test_control_15_a_verdict_that_is_not_leading_is_not_read_as_the_verdict() -> None:
    """CONTROL 15 — the discrimination `CONTROL 9`/`9b` leave open on one side.

    **Written because a sabotage this plan was told to run reported GREEN, and
    the reason was measured rather than assumed** (the wave-4 lesson, applied
    to this plan's own machinery). The mutation was: make :func:`verdict_token`
    return the first ``**…**`` run *anywhere* in the cell instead of the
    leading one, and watch `CONTROL 11` fail. It did not fail, for two
    independent reasons, and neither is a defect in `CONTROL 11`:

    * :func:`doubled_verdicts`, which is `CONTROL 11`'s entire subject, never
      calls :func:`verdict_token` — it reads :data:`BOLDED_RUN` directly. No
      mutation of the token reader can move that control.
    * Measured across every status cell in the ledger, the first bolded run and
      the leading token are IDENTICAL on every row, because every cell in this
      ledger opens with its verdict. The mutation was invisible to the whole
      module, not just to `CONTROL 11`.

    `CONTROL 9b` covers the other side — a reader taking the LAST bolded run
    goes red there, and on four shipped assertions besides. This covers the
    first-run-anywhere side, by handing the reader the one cell shape the
    corpus does not contain: a verdict that is not leading. The shipped reader
    returns the prose prefix, which is not in the vocabulary and is refused by
    name. A first-run-anywhere reader returns `Complete` and accepts it, which
    is how a cell reading *"shipped in wave five — Complete"* would come to be
    counted as a verdict.
    """
    real = ledger_text()
    doctored = _doctored(
        real,
        _table_line(real, "RECON-10"),
        "| RECON-10 | Phase 21 | shipped in wave five — **Complete** |",
    )
    offenders = vocabulary_offenders(doctored)
    assert any("RECON-10" in message for message in offenders), (
        "a status cell whose verdict is not leading was accepted, or refused"
        f" without being named: {offenders!r}. The verdict of a row is the word"
        " the cell OPENS with; a reader that hunts for a vocabulary word"
        " anywhere in the prose will find one in almost any honest sentence"
    )


# --- CONTROL 19: RR-2, the two verdict readers that could disagree in silence ---
#
# Landed in plan `21.1-02` task 1, BEFORE the fix it falsifies, and watched
# failing against the committed pre-fix module (`D-IMPL-170`). Its two
# assertions are red at that commit and green at the next.


def _cell_with_an_unbolded_lead_and_a_later_bolded_verdict(
    document_text: str, req_id: str, later: str
) -> str:
    """`req_id`'s real cell, re-opened UNBOLDED with `later` bolded after it.

    Derived from the row as it stands rather than retyped, for the reason
    :func:`_table_line` records: a control anchored on a literal cell string is
    anchored on a snapshot of its subject, and three controls broke exactly
    that way when plan `21-06` wrote the verdicts they had transcribed.

    The row's CITATIONS are carried through untouched, so a refusal is
    attributable to the verdict alone and not to a cell that lost its evidence
    on the way through the mutation.
    """
    line = _table_line(document_text, req_id)
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) != CELLS_PER_ROW:
        raise AssertionError(
            f"{req_id}'s traceability line split into {cells!r}, which is not"
            " the three cells this mutation is built on"
        )
    status = cells[2]
    lead = verdict_token(status)
    if lead not in VERDICT_VOCABULARY or lead == later:
        raise AssertionError(
            f"{req_id} reads {lead!r}, which is either outside the vocabulary"
            f" or already {later!r}. Either way the mutation would not produce"
            " a cell asserting TWO DIFFERENT verdicts, which is the whole"
            " subject of this control"
        )
    if not status.startswith(f"**{lead}**"):
        raise AssertionError(
            f"{req_id}'s cell does not open with a BOLDED {lead!r}, so"
            " un-bolding its lead is not the mutation this control claims to"
            f" make. The cell reads {status[:60]!r}"
        )
    remainder = status[len(lead) + 4 :]
    mutated = f"{lead} — later **{later}**{remainder}"
    return _doctored(
        document_text, line, f"| {cells[0]} | {cells[1]} | {mutated} |"
    )


def test_control_19_an_unbolded_lead_and_a_later_bolded_verdict_is_two_verdicts() -> (
    None
):
    """CONTROL 19 — `RR-2`, handed to the SHIPPED functions.

    The defect: :func:`verdict_token` strips `**` and reads the LEADING
    alphabetic run, while :func:`doubled_verdicts` reads only BOLDED runs. A
    cell reading ``Complete — later **Partial** (…)`` is `Complete` to the
    first and one verdict to the second. Measured against the real ledger with
    `HARD-02` doctored to exactly that shape: `verdict_token` returns
    ``'Complete'`` unchanged, and :func:`vocabulary_offenders`,
    :func:`doubled_verdicts`, :func:`roster_rows_with_two_verdicts`,
    :func:`channel_disagreements`, both :func:`unverdicted` calls, both
    :func:`uncited_verdicts` calls and :func:`refuse_unresolvable` all return
    empty. **Eight gates, zero refusals**, on a working-set row that visibly
    reads `**Partial**`.

    BOTH gates are asserted, not one. :func:`roster_rows_with_two_verdicts` is
    a second implementation of the same predicate and it is the gate the
    working set is actually held to; a control that watched only the
    ledger-wide half would let the two drift apart, which is this phase's
    defect class arriving one level up.

    The victim is asserted NOT to be an offender on the real document first —
    the reachability idiom `CONTROL 10`, `14` and `17` use — so a
    green-before/red-after pair is attributable to the mutation and to nothing
    else, and a refusal fired by some neighbouring row cannot satisfy it.
    """
    real = ledger_text()
    victim = "HARD-02"
    assert victim in WORKING_SET_ROSTER, (
        f"{victim} is not in `WORKING_SET_ROSTER`, so the roster-scoped half of"
        " this control would be quantified over a row the roster never reaches"
        " and would pass no matter what the gate did"
    )
    assert not any(victim in message for message in doubled_verdicts(real)), (
        f"{victim} is already reported as doubled on the real ledger, so this"
        " control cannot distinguish its mutation from the status quo"
    )
    assert not any(
        victim in message
        for message in roster_rows_with_two_verdicts(real, WORKING_SET_ROSTER)
    ), (
        f"{victim} is already reported as doubled by the roster-scoped gate on"
        " the real ledger; same reason"
    )

    doctored = _cell_with_an_unbolded_lead_and_a_later_bolded_verdict(
        real, victim, "Partial"
    )
    mutated = [
        status
        for req_id, _phase, status in traceability_rows(doctored)
        if req_id == victim
    ][0]
    assert verdict_token(mutated) == "Complete", (
        "the leading-token reader no longer reads this cell as `Complete`, so"
        " the two readers no longer disagree about it and the control is not"
        f" testing `RR-2` any more. It read {verdict_token(mutated)!r}"
    )
    assert "**Partial**" in mutated, (
        "the mutation did not leave a bolded second verdict in the cell"
    )

    ledger_wide = doubled_verdicts(doctored)
    assert any(victim in message for message in ledger_wide), (
        "a cell whose leading verdict is `Complete` and which later asserts"
        " `**Partial**` was accepted by the ledger-wide gate. The two readers"
        f" disagree and neither refuses: {ledger_wide!r}"
    )
    roster_scoped = roster_rows_with_two_verdicts(doctored, WORKING_SET_ROSTER)
    assert any(victim in message for message in roster_scoped), (
        "the ledger-wide gate refused but the roster-scoped one did not. They"
        " are two implementations of one predicate and this is them drifting"
        f" apart: {roster_scoped!r}"
    )
    for message in (
        [m for m in ledger_wide if victim in m]
        + [m for m in roster_scoped if victim in m]
    ):
        assert "Complete" in message and "Partial" in message, (
            "the refusal fired but did not name the verdicts it found:"
            f" {message!r}. A reader who cannot see WHICH two verdicts the"
            " cell asserts cannot act on the refusal"
        )


def test_the_two_one_verdict_gates_read_the_same_predicate() -> None:
    """The ledger-wide and roster-scoped gates share ONE reader, by source.

    Not decoration. `RR-2` is two readers of a cell disagreeing in silence;
    :func:`doubled_verdicts` and :func:`roster_rows_with_two_verdicts` are two
    readers of a cell that today carry byte-identical inline copies of the same
    predicate. `CONTROL 19` asserts both refuse the doctored cell, which two
    divergent copies of the union rule would also satisfy — on the day they
    land. This is the assertion that stops one of them being amended later
    without the other.

    Discriminating, and stated so a reader can check it: the shared predicate
    is REQUIRED to reference :data:`BOLDED_RUN` itself, so this is not the
    vacuous "``BOLDED_RUN`` appears nowhere" assertion, which a module that had
    deleted the bolded reading entirely would also pass.
    """
    import inspect

    assert "cell_verdicts" in globals(), (
        "no shared verdict predicate exists in this module, so the ledger-wide"
        " and roster-scoped one-verdict gates are two independent readers of"
        " the same cell — which is `RR-2`'s own shape, one level up"
    )
    shared = inspect.getsource(globals()["cell_verdicts"])
    assert "BOLDED_RUN" in shared, (
        "the shared predicate does not read bolded runs at all, so requiring"
        " the two gates not to read them is quantified over nothing"
    )
    for gate in (doubled_verdicts, roster_rows_with_two_verdicts):
        source = inspect.getsource(gate)
        assert "cell_verdicts(" in source, (
            f"{gate.__name__} does not call the shared verdict predicate. A"
            " second implementation is exactly what lets the ledger-wide and"
            " roster-scoped gates drift apart"
        )
        assert "BOLDED_RUN" not in source, (
            f"{gate.__name__} still reads {'BOLDED_RUN'} directly. A gate that"
            " keeps its own copy of the reading is one edit away from"
            " disagreeing with the other about what a cell says"
        )


# ===========================================================================
# CONTROL 20, 21 and 22 — `RR-4` and `RR-6`, the two shapes that make a check
# report clean over a subject it never had.
#
# Landed in plan `21.1-03` task 1, BEFORE the fixes they falsify, and watched
# failing against the committed pre-fix module (`D-IMPL-170`).
#
# `RR-4` — A DUPLICATE REQUIREMENT ID COLLAPSES INTO A DICT AND THE LEDGER
# REPORTS CLEAN. Measured against the real ledger at this plan's HEAD:
# `HARD-02`'s row duplicated with a different phase cell and its citations
# intact yields a parse holding the id TWICE, while every consumer that keys
# by id keeps ONE — and `channel_disagreements`, `vocabulary_offenders`,
# `doubled_verdicts`, `unverdicted(working_set)` and `uncited_verdicts` all
# return empty. There are FOUR dict builds plus two comprehensions over
# :func:`traceability_rows` and :func:`checkbox_channel`, which is why the
# refusal belongs in the PARSERS: a guard written into one consumer leaves
# five holes. `:1760`'s `uncited_verdicts` is a WORSE shape than a collapse —
# it APPENDS, so a duplicated row's citations MERGE and an uncited duplicate
# is masked by its cited twin. That is closed upstream by the parser refusal
# rather than patched at the site.
#
# The ledger's own `Coverage` sentence says each requirement is mapped "to
# exactly one phase". That sentence was falsified by nothing and guarded by
# nothing.
#
# `RR-6` — `_index()` RETURNS AN EMPTY MAPPING RATHER THAN REFUSING. On a
# thinned index the moved-path branch of :func:`refuse_unresolvable` — the one
# its own docstring calls "the second silent hole" it exists to dodge —
# returns SILENCE, and an on-disk-but-unindexed path is accepted. The
# ambiguity branch is guarded only BY ACCIDENT, because `CONTROL 1` happens to
# assert the word AMBIGUOUS in the message.
# ===========================================================================


def _duplicated_table_row(document_text: str, req_id: str) -> str:
    """`req_id`'s real table line, followed by a SECOND copy under another phase.

    DERIVED from the row rather than retyped, on `CONTROL 19`'s pattern. The
    twin differs only in its PHASE cell and carries the row's citations through
    untouched, so a refusal is attributable to the REPETITION and not to a
    malformed, unverdicted or uncited second row. It refuses if the derived
    twin is not actually a second row for the same id.
    """
    line = _table_line(document_text, req_id)
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) != CELLS_PER_ROW:
        raise AssertionError(
            f"{req_id}'s traceability line split into {cells!r}, which is not"
            " the three cells this mutation needs to rebuild the row"
        )
    other_phase = "Phase 99"
    if cells[1] == other_phase:
        raise AssertionError(
            f"{req_id}'s phase cell already reads {other_phase!r}, so the"
            " derived twin would be byte-identical to the row and"
            " `_doctored` would refuse a non-unique anchor for the wrong"
            " reason"
        )
    twin = f"| {cells[0]} | {other_phase} | {cells[2]} |"
    if twin == line:
        raise AssertionError(
            f"the derived twin for {req_id} is identical to its row, so the"
            " mutation would not be a SECOND row at all"
        )
    return _doctored(document_text, line, f"{line}\n{twin}")


def _duplicated_checkbox_bullet(document_text: str, req_id: str) -> str:
    """`req_id`'s real checkbox bullet, followed by a SECOND copy with the tick flipped.

    The tick is flipped rather than copied verbatim for two reasons. A
    byte-identical copy makes :func:`_doctored`'s uniqueness check refuse the
    anchor before the mutation lands, and — the load-bearing one — a flipped
    tick is the shape that actually costs something: the dict comprehension
    keeps the LAST bullet, so a duplicated `[x]`/`[ ]` pair silently decides
    what the checkbox channel says about the row.
    """
    line = _checkbox_line(document_text, req_id)
    match = CHECKBOX_LINE.match(line)
    if match is None:  # pragma: no cover - `_checkbox_line` already refused
        raise AssertionError(f"{line!r} is not a checkbox bullet")
    flipped = "x" if match.group(1).lower() != "x" else " "
    twin = line[: match.start(1)] + flipped + line[match.end(1) :]
    if twin == line:
        raise AssertionError(
            f"the derived twin bullet for {req_id} is identical to its"
            " bullet, so the mutation would not be a SECOND bullet at all"
        )
    if CHECKBOX_LINE.match(twin) is None or CHECKBOX_LINE.match(twin).group(2) != req_id:  # type: ignore[union-attr]
        raise AssertionError(
            f"the derived twin bullet {twin!r} is not read by CHECKBOX_LINE as"
            f" a bullet for {req_id}, so the control's subject is not a"
            " duplicate id at all"
        )
    return _doctored(document_text, line, f"{line}\n{twin}")


def test_control_20_a_duplicate_id_in_the_traceability_table_is_refused() -> None:
    """CONTROL 20 — `RR-4` in the table channel, watched refusing.

    Reachability first, in this module's idiom: the real document parses, the
    victim is a row of it, and :func:`_table_line` refuses unless the victim
    matches EXACTLY ONE line — so a mutation that landed nowhere cannot be
    mistaken for a refusal that never fired.

    The assertion is on the PARSER, not on a consumer. Four dict builds and
    two comprehensions read :func:`traceability_rows`; a control aimed at one
    of them would say nothing about the other five.
    """
    real = ledger_text()
    victim = "HARD-02"
    rows = traceability_rows(real)
    assert victim in [req_id for req_id, _phase, _status in rows], (
        f"{victim} is not a row of the real traceability table, so this"
        " control's mutation would be a row the ledger never had and the"
        " refusal it watches would be about nothing"
    )
    doctored = _duplicated_table_row(real, victim)
    twins = [
        line for line in doctored.splitlines() if line.startswith(f"| {victim} | ")
    ]
    assert twins[1:] and not twins[2:], (
        f"the mutation produced {twins!r} rather than exactly two rows for"
        f" {victim}; the control's own subject is not a duplicate id"
    )
    try:
        parsed = traceability_rows(doctored)
    except AssertionError as failure:
        assert victim in str(failure), (
            "the duplicate was refused, but the refusal does not NAME the"
            f" repeated id: {str(failure)!r}. A reader handed a shortfall"
            " rather than a row cannot act on it (`D-21`, and"
            " `unverdicted`'s own docstring)"
        )
        return
    ids = [req_id for req_id, _phase, _status in parsed]
    raise AssertionError(
        "a traceability table carrying two rows for"
        f" {victim} parsed to {len(ids)} rows and was accepted. Every"
        " consumer that keys by id then keeps ONE of them, the other's phase"
        " and verdict vanish, and the ledger's own claim that each"
        " requirement maps to exactly one phase is falsified by nothing and"
        " guarded by nothing"
    )


def test_control_21_a_duplicate_id_in_the_checkbox_channel_is_refused() -> None:
    """CONTROL 21 — `RR-4` in the checkbox channel, INDEPENDENTLY.

    Independently is the operative word. The two channels are two claims, and
    a guard on one says nothing about the other: :func:`checkbox_channel`
    builds its own dict from its own regex and would keep the LAST bullet for
    a repeated id no matter what the table parser refused.
    """
    real = ledger_text()
    victim = "HARD-02"
    assert victim in checkbox_channel(real), (
        f"{victim} is not a bullet of the real checkbox channel, so this"
        " control's mutation would be a bullet the ledger never had"
    )
    doctored = _duplicated_checkbox_bullet(real, victim)
    twins = [
        line
        for line in doctored.splitlines()
        if CHECKBOX_LINE.match(line) is not None
        and CHECKBOX_LINE.match(line).group(2) == victim  # type: ignore[union-attr]
    ]
    assert twins[1:] and not twins[2:], (
        f"the mutation produced {twins!r} rather than exactly two bullets for"
        f" {victim}; the control's own subject is not a duplicate id"
    )
    try:
        channel = checkbox_channel(doctored)
    except AssertionError as failure:
        assert victim in str(failure), (
            "the duplicate was refused, but the refusal does not NAME the"
            f" repeated id: {str(failure)!r}"
        )
        return
    raise AssertionError(
        f"a checkbox channel carrying two bullets for {victim} was accepted"
        f" and resolved it to {channel[victim]!r}. The dict keeps the LAST"
        " bullet, so a duplicated tick silently decides what the channel says"
        " about the row — and `channel_disagreements` then compares the table"
        " against a claim nobody wrote"
    )


def test_control_22_an_index_that_resolved_nothing_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONTROL 22 — `RR-6`: an index with no subject must refuse, not return `{}`.

    TWO subjects, and the SECOND is the discriminating one.

    * The EMPTY mapping is the obvious shape.
    * A THINNED mapping — populated, but not with the path the module's own
      citation checks depend on — is the shape that asks *what weaker
      implementation would still pass this control?* A guard written as "refuse
      an empty index" passes the first subject and accepts the second, and the
      second is the one the research actually measured going silent: on a
      thinned index the moved-path branch of :func:`refuse_unresolvable`
      returns SILENCE and an on-disk-but-unindexed path is accepted. Only the
      ambiguity branch is guarded today, and only BY ACCIDENT, because
      `CONTROL 1` happens to assert the word AMBIGUOUS.

    **`_REPO_INDEX_CACHE` is process-lifetime state, so the restoration is the
    control's own obligation.** The real mapping is saved, the cache is cleared
    around each subject, and the `finally` clears it a second time and puts the
    saved contents back — a control that left junk in it would poison every
    test that ran after it, which is a fresh instance of this phase's own
    defect class arriving through the control rather than through the check.
    The last assertion is that the restoration WORKED.
    """
    saved = dict(_REPO_INDEX_CACHE)
    live = _index()
    assert live, (
        "the real resolver index is empty before this control does anything,"
        " so the mutation below is indistinguishable from the baseline"
    )
    subjects = (
        ("an EMPTY mapping", {}),
        (
            "a THINNED mapping that resolves nothing this module depends on",
            {"nothing.py": ["nowhere/nothing.py"]},
        ),
    )
    try:
        for description, thinned in subjects:
            monkeypatch.setattr(
                "tools.docs_tests.test_requirement_ledger.repo_index",
                lambda _root, _thinned=thinned: dict(_thinned),
            )
            _REPO_INDEX_CACHE.clear()
            try:
                returned = _index()
            except AssertionError as failure:
                assert "index" in str(failure), (
                    f"{description} was refused, but the refusal does not say"
                    f" what went silent: {str(failure)!r}"
                )
                continue
            raise AssertionError(
                f"`_index()` returned {description} as {returned!r} instead of"
                " refusing. A resolver index with no subject makes"
                " `refuse_unresolvable` report ZERO unresolvable citations,"
                " which is indistinguishable from a clean ledger — the"
                " moved-path branch stops checking and says nothing about it"
            )
    finally:
        monkeypatch.undo()
        _REPO_INDEX_CACHE.clear()
        _REPO_INDEX_CACHE.update(saved)
    restored = _index()
    assert restored == live, (
        "this control left `_REPO_INDEX_CACHE` thinned. Every citation check"
        " that runs after it would then be quantified over an index with no"
        " subject, and would report clean"
    )


# ===========================================================================
# CONTROL 23 — A `.planning/` DOCUMENT COULD NOT BE CITED AT ALL, IN EITHER
# DIRECTION, AND NOTHING SAID SO.
#
# Landed in plan `21.1-03` task 3, BEFORE the pattern it falsifies, and
# watched failing against the committed pre-fix module (`D-IMPL-170`).
#
# THE MEASUREMENT. A status cell citing an EXISTING `.planning/` document with
# a line anchor extracted to a path that IS NOT IN THE TREE. `CITATION`'s path
# group opens `[A-Za-z0-9_]`, which excludes `.`, so the match starts one
# character LATE and names `planning/...` — refused as absent. The `::symbol`
# spelling is refused too, because `refuse_unresolvable` reserves `::` to
# Python and a `.planning/` record is markdown. Cite it with the dot and the
# citation is refused; omit the citation and `uncited_verdicts` refuses the
# row. There was NO LEGAL SPELLING.
#
# It is NEW debt rather than pre-existing: at this plan's HEAD the ledger
# carried 127 citations and not one of them started with a dot, so nothing
# had ever been refused for this reason. It is the SAME defect Phase 21
# wave 2 hit on `.github/workflows/ci.yml` and carried; nobody connected it
# to `.planning/`.
#
# `D-07` STANDS: the citation lint is NOT touched. The fix is a MODULE-LOCAL
# widening, which is the move this module already makes one shape up —
# `LOOSE_NODE_ID` is that precedent, in the module already, with the reasoning
# written at the constant.
#
# WHY THE WIDENED PATTERN *REPLACES* THE LINT'S RATHER THAN JOINING IT, AND
# WHY THAT IS NOT AN AESTHETIC CHOICE. Adding a dot-tolerant line-citation
# pattern ALONGSIDE `CITATION` in the tuple `citations_in_status_cells`
# iterates extracts the citation TWICE, in EITHER order — measured both ways
# against a real `.planning/` path:
#
#     appended  -> ['planning/…/21-FINDINGS.md', '.planning/…/21-FINDINGS.md']
#     prepended -> ['.planning/…/21-FINDINGS.md', 'planning/…/21-FINDINGS.md']
#
# Order cannot suppress the twin, because the dedup inside
# `citations_in_status_cells` is a `set[str]` over the PATH STRING and
# `planning/…` is not `.planning/…`. The truncated twin names a path that is
# not in the tree, `refuse_unresolvable` refuses it BY NAME, and the row is
# still uncitable — now behind a pattern that looks like it landed. So: the
# tuple carries ONE PATTERN PER CITATION SHAPE. No twin by construction, and
# no span arithmetic to get wrong.
# ===========================================================================


def _planning_document_citation() -> str:
    """A repo-relative `.planning/` path that certainly exists, DERIVED not typed.

    :data:`LEDGER_PATH` is the strongest possible anchor for this control: it
    is the module's own subject, so a run in which it is absent has already
    failed everywhere else. A transcribed phase-record path would be anchored
    on a snapshot of `.planning/phases/`, which is exactly the drift
    :func:`_table_line` exists to avoid one level down.
    """
    return LEDGER_PATH.relative_to(REPO_ROOT).as_posix()


def test_control_23_a_planning_document_can_be_cited_and_a_missing_one_cannot() -> (
    None
):
    """CONTROL 23 — the widened line citation, watched in BOTH directions.

    **The acceptance half asserts `refuse_unresolvable(...) == []`, never
    merely that something was extracted.** That is the assertion the naive
    two-pattern spelling fails, because the truncated dot-less twin is refused
    and the list is not empty — and the cheap way to make this control green
    would be to weaken it to "a citation was extracted". Weakened, it would
    report green over a row that still cannot be cited, which is this phase's
    own defect class arriving inside this phase's own fix.

    **The refusal half is not optional either.** A pattern that extracts a
    citation nobody checks is worse than no pattern at all: it converts a
    silent drop into a silent acceptance.

    The extraction is asserted to be EXACTLY ONE path, which is what refuses
    the twin structurally rather than by consequence.
    """
    existing = _planning_document_citation()
    assert existing.startswith("."), (
        f"{existing!r} does not begin with a dot, so this control's subject is"
        " not the shape it is about and it would pass under the unwidened"
        " pattern"
    )
    assert (REPO_ROOT / existing).is_file(), (
        f"{existing!r} is not a file, so the acceptance half below would be"
        " asserting that an ABSENT path resolves"
    )

    accepted = _document_with_citation(f"{existing}:1")
    extracted = [path for _req_id, path in citations_in_status_cells(accepted)]
    assert extracted == [existing], (
        f"a status cell citing `{existing}:1` extracted to {extracted!r}"
        f" rather than exactly [{existing!r}]. An empty list is the unwidened"
        " pattern failing to see a leading dot at all; a list of TWO is the"
        " truncated twin, which is what a dot-tolerant pattern ADDED beside"
        " the lint's produces in either order"
    )
    assert refuse_unresolvable(accepted) == [], (
        f"a status cell citing the EXISTING `{existing}` with a line anchor"
        f" was refused: {refuse_unresolvable(accepted)!r}. There is then no"
        " legal way to cite a `.planning/` document at all — the dotted"
        " spelling is refused as absent and the `::symbol` spelling is"
        " refused as non-Python — and any row whose only evidence lives"
        " under `.planning/` is trapped in both directions"
    )

    absent = ".planning/phases/no-such-phase/NO-SUCH-RECORD.md"
    assert not (REPO_ROOT / absent).exists(), (
        f"{absent!r} exists, so the refusal half below is about a path that"
        " resolves and would be asserting the opposite of what it claims"
    )
    messages = refuse_unresolvable(_document_with_citation(f"{absent}:1"))
    assert any(absent in message for message in messages), (
        f"a `.planning/` path that is NOT in the tree was accepted, or refused"
        f" without being named: {messages!r}. A widened pattern whose"
        " extractions nobody checks turns the citation lint's silent DROP into"
        " a silent ACCEPTANCE, which is worse"
    )


def _document_with_citations(*cited: str) -> str:
    """A minimal well-formed ledger whose ONE status cell carries every `cited`.

    The plural twin of :func:`_document_with_citation`, added by plan `21.1-05`
    for `CONTROL 23b`. Subsumption is a property of ONE CELL against itself —
    the lint's matches and the widening's matches are compared inside the same
    status cell — so a control that discriminates span containment from
    path-string equality needs two citations in one cell, not two rows.
    """
    tokens = " ".join(f"`{one}`" for one in cited)
    return "\n".join(
        (
            "- [ ] **TEST-01**: a control fixture, not a requirement",
            "",
            TABLE_HEADER,
            "|-------------|-------|--------|",
            f"| TEST-01 | Phase 21 | Pending ({tokens}) |",
            "",
        )
    )


def test_control_23b_the_subsumption_gate_compares_spans_not_path_strings() -> None:
    """CONTROL 23b — `RR-11`, the gate that forbade the pattern it was built for.

    Wave 3 shipped :data:`LOOSE_CITATION` **and, beside it, a gate that cannot
    be satisfied by a dotted citation** — the exact shape the pattern exists to
    admit. Wave 4 was the first plan to actually USE it and found the gate red
    on a correct citation. Measured there, and re-measured by the first limb
    below rather than transcribed: on `.planning/ROADMAP.md:1` the lint's
    `CITATION` matches ONE CHARACTER LATE and yields the truncated twin
    `planning/ROADMAP.md`, while `LOOSE_CITATION` matches at the dot and yields
    the correct `.planning/ROADMAP.md`. As PATH STRINGS the twin scores as a
    silent DROP; as SPANS the widened match **covers the lint's entirely** and
    nothing was corrected away. `D-IMPL-180` (Dave, 2026-08-22) ruled the
    repair: subsumption by SPAN CONTAINMENT, anti-vacuity clause kept.

    It was green in wave 3 for failure mode 1 — *the subject never reached the
    branch under test.* No dotted citation existed anywhere in the tree, and it
    took a whole wave to produce one.

    **Four limbs, because three weaker implementations pass fewer than four.**

    1. the RR-11 shape ACCEPTED — and the truncation is RUN here, not assumed,
       so this limb fails loudly if the two patterns ever stop disagreeing and
       the control quietly stops being about anything;
    2. a widening narrowed until it no longer covers a lint match is REFUSED
       BY NAME — this is what a predicate that dropped the coverage test
       entirely would pass;
    3. a subject the LINT pattern matches nowhere RAISES — the anti-vacuity
       clause, which is what *"every lint match is covered"* degenerates into
       when there are no lint matches. A predicate that merely dropped this
       clause would pass limbs 1 and 2 untouched;
    4. **the substring trap.** A lint match whose PATH STRING is a substring of
       an unrelated widened path elsewhere in the same cell is still uncovered.
       An implementation comparing path strings by containment rather than
       spans passes limbs 1, 2 and 3 and fails only this one.
    """
    assert "uncovered_lint_citations" in globals(), (
        "the subsumption gate has no predicate a control can point at a"
        " subject: it compares path STRINGS inline, so a dotted citation's"
        " correct `.planning/…` match is scored a silent DROP against the"
        " lint's truncated twin `planning/…`, and the gate can never be"
        " satisfied by the shape `LOOSE_CITATION` exists to admit. That is"
        " `RR-11`: wave 3 shipped a pattern and, beside it, a gate forbidding"
        " its use for the thing it was built for"
    )
    uncovered = globals()["uncovered_lint_citations"]

    # --- limb 1: the RR-11 shape is admissible, and the truncation is RUN ---
    dotted = f"{_planning_document_citation()}:1"
    subject = _document_with_citations(dotted)
    cell = traceability_rows(subject)[0][2]
    lint_hit = CITATION.search(cell)
    widened_hit = LOOSE_CITATION.search(cell)
    assert lint_hit is not None and widened_hit is not None, (
        f"one of the two patterns matches nothing in {cell!r}, so this control"
        " has no subject and its acceptance limb would be vacuous"
    )
    assert lint_hit.group("path") != widened_hit.group("path"), (
        f"both patterns yield {lint_hit.group('path')!r} on a DOTTED citation,"
        " so the truncated twin this control is about no longer exists and the"
        " limbs below would pass for a reason unrelated to RR-11"
    )
    assert widened_hit.start() < lint_hit.start() and (
        widened_hit.end() >= lint_hit.end()
    ), (
        f"the widened match {widened_hit.span()} does not start earlier than"
        f" and cover the lint's {lint_hit.span()}, so the premise of the"
        " repair — that nothing was corrected AWAY — is not true of this"
        " subject"
    )
    assert uncovered(subject, CITATION, LOOSE_CITATION, "CITATION") == [], (
        "a real dotted citation is still scored a silent drop against its own"
        f" correction: the lint finds {lint_hit.group('path')!r} at"
        f" {lint_hit.span()} and the widening finds"
        f" {widened_hit.group('path')!r} at {widened_hit.span()}, which covers"
        " it. Compared as path strings the twin is 'missing'; compared as"
        " spans nothing was lost. `VAC-03`'s only evidence lives under"
        " `.planning/`, so this gate blocks the phase's own close"
    )

    # --- limb 2: a widening narrowed until it drops a citation is refused ---
    plain = "src/ccf/client/client.py:1"
    mixed = _document_with_citations(dotted, plain)
    dotted_only = re.compile(
        r"(?P<path>\.[A-Za-z0-9_./+-]*\.md):(?P<lines>\d+)"
    )
    messages = uncovered(mixed, CITATION, dotted_only, "CITATION")
    assert any("client.py" in message for message in messages), (
        "a widening narrowed to dotted `.md` paths alone stopped finding"
        f" {plain!r}, which the lint's own pattern does find, and the gate"
        f" said nothing: {messages!r}. The extraction tuple consults the"
        " widened pattern and NOT the lint's, so a later narrowing drops"
        " citations in SILENCE — the hole the replacement itself opens"
    )

    # --- limb 3: anti-vacuity — no lint match at all is a refusal ---
    barren = _document_with_citations()
    try:
        result = uncovered(barren, CITATION, LOOSE_CITATION, "CITATION")
    except AssertionError as failure:
        assert "CITATION" in str(failure), (
            f"the empty-subject refusal does not name the pattern: {failure}"
        )
    else:
        raise AssertionError(
            f"a subject the lint's `CITATION` matches NOWHERE returned"
            f" {result!r} instead of refusing. 'Every lint match is covered by"
            " a widened match' is trivially true over zero lint matches, which"
            " is the vacuity this whole module is about — and a predicate that"
            " simply dropped this clause would pass every other limb here"
        )

    # --- limb 4: the substring trap — coverage is a SPAN, not a substring ---
    trap = _document_with_citations("docs/DECISIONS.md:1", "DECISIONS.md:2")
    with_a_slash = re.compile(
        r"(?P<path>[A-Za-z0-9_.][A-Za-z0-9_./+-]*/[A-Za-z0-9_.+-]*\.md)"
        r":(?P<lines>\d+)"
    )
    trapped = uncovered(trap, CITATION, with_a_slash, "CITATION")
    assert any("DECISIONS.md:2" in message for message in trapped), (
        "the bare `DECISIONS.md:2` citation was dropped by the narrowed"
        " widening and the gate reported clean, because its path string is a"
        f" SUBSTRING of `docs/DECISIONS.md`, which the widening does find:"
        f" {trapped!r}. Containment of the STRING is not containment of the"
        " SPAN, and only the span form can tell a correction from a loss"
    )


def test_each_widened_pattern_subsumes_the_lint_pattern_it_replaced() -> None:
    """Every citation the lint's own pattern finds, the widened one finds too.

    **The hole this closes is opened BY the replacement.** Once
    :func:`citations_in_status_cells` carries one module-local pattern per
    citation shape, the lint's `NODE_ID` and `CITATION` are no longer consulted
    at all — so a widened pattern that was later narrowed, or mis-transcribed,
    would stop seeing citations SILENTLY.
    :func:`test_the_scan_finds_citations_to_check` cannot catch that: it
    asserts non-emptiness and carries no count (`D-21`, correctly), so losing
    almost every citation still passes it. This is the assertion that a
    replacement is a SUPERSET of what it replaced.

    It is also why the two lint patterns stay imported. They are not dead: they
    are the reference this check measures against, and measuring against the
    lint's own regexes is stronger than measuring against a copy of them.

    **Anti-vacuity clause:** the lint pattern is REQUIRED to find something in
    the real ledger. "Every match is also a match" is trivially true of a
    pattern that matches nothing, which is precisely the failure this is here
    to detect.

    This is what let `NODE_ID` be dropped from the extraction tuple rather than
    assumed redundant. Measured over the real ledger at the time it landed,
    `NODE_ID` and :data:`LOOSE_NODE_ID` returned the SAME 213 `(id, path)`
    pairs and the sets were EQUAL — the counts are history and are read by no
    assertion here; the subsumption below is the standing property.
    """
    assert "LOOSE_CITATION" in globals(), (
        "no module-local line-citation pattern exists, so a status cell cannot"
        " name a `.planning/` document at all: the lint's `CITATION` path"
        " group excludes a leading dot and starts its match one character"
        " late, and `refuse_unresolvable` reserves `::symbol` to Python. There"
        " is no legal spelling, and nothing in this module says so"
    )
    text = ledger_text()
    for name, lint_pattern, widened in (
        ("NODE_ID", NODE_ID, LOOSE_NODE_ID),
        ("CITATION", CITATION, globals()["LOOSE_CITATION"]),
    ):
        lint_pairs: list[tuple[str, str]] = []
        widened_pairs: list[tuple[str, str]] = []
        for req_id, _phase, status in traceability_rows(text):
            for match in lint_pattern.finditer(status):
                lint_pairs.append((req_id, match.group("path")))
            for match in widened.finditer(status):
                widened_pairs.append((req_id, match.group("path")))
        assert lint_pairs, (
            f"the lint's `{name}` matches nothing in the real ledger's status"
            " cells, so 'the widened pattern finds everything it finds' is"
            " quantified over the empty set and is trivially true"
        )
        missing = sorted(set(lint_pairs) - set(widened_pairs))
        assert not missing, (
            f"the module-local widening of `{name}` no longer finds"
            f" {missing!r}, which the lint's own pattern does find. The"
            " extraction tuple consults the widened pattern and NOT the"
            " lint's, so these citations are now invisible to"
            " `refuse_unresolvable` — dropped in silence, which is the exact"
            " hole this module exists to dodge from the outside"
        )
