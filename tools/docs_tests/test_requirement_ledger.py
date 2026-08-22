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

import pytest

from tools.lints.citations import CITATION, NODE_ID, repo_index

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

#: `D-09`'s six words, plus `Pending`. `Pending` is admitted because unaudited
#: rows still carry it while the phase runs; the phase's LAST plan is what
#: refuses a leftover `Pending`, and it is deliberately not this module's job —
#: an assertion that every row is verdicted is red from the moment it lands
#: until the final row is written.
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


def checkbox_channel(document_text: str) -> dict[str, bool]:
    """Requirement id to checked-state, from the checkbox list.

    Raises rather than returning an empty mapping, for the reason
    :func:`traceability_rows` states: an empty channel makes every comparison
    against it trivially agreeable.
    """
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
    """One message per status cell carrying more than one vocabulary word in bold.

    A cell reading `**Complete** **Partial** (…)` is ambiguous about what the
    row claims, and the leading-token reader above would silently report the
    first. `CONTROL 11` is this check watched refusing exactly that shape.
    """
    offenders: list[str] = []
    for req_id, _phase, status in traceability_rows(document_text):
        bolded = [match.group(1).strip() for match in BOLDED_RUN.finditer(status)]
        verdicts = [word for word in bolded if word in VERDICT_VOCABULARY]
        if verdicts[1:]:
            offenders.append(
                f"{req_id}'s status cell carries the bolded verdicts"
                f" {verdicts!r}. A row claims one thing; a reader taking the"
                " leading token would report only the first"
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
    """The wave-1 mint's own floor; plan `21-06` turns these into verdicts."""
    table = {
        req_id: status for req_id, _phase, status in traceability_rows(ledger_text())
    }
    boxes = checkbox_channel(ledger_text())
    for req_id in sorted(PHASE_OWN_ROSTER):
        assert req_id in table, f"{req_id} is missing from the traceability table"
        assert req_id in boxes, f"{req_id} is missing from the checkbox list"
        assert verdict_token(table[req_id]) == "Pending", (
            f"{req_id} reads {table[req_id]!r}. The phase's own rows are minted"
            " `Pending` in wave 1 and verdicted in plan `21-06`, before the"
            " close panel — not here"
        )
        assert boxes[req_id] is False, (
            f"{req_id} is ticked in the checkbox list while its table row is"
            " still `Pending`"
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
    doctored = _doctored(
        ledger_text(),
        "| RECON-10 | Phase 21 | Pending |",
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
    doctored = _doctored(
        ledger_text(),
        "| RECON-10 | Phase 21 | Pending |",
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
    doctored = _doctored(
        ledger_text(),
        "| RECON-10 | Phase 21 | Pending |",
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
# WHAT IS NOT HERE, AND WHY THAT IS NOT AN OVERSIGHT. The zero-CITATION vacuity
# guard, and the precondition asserting the real ledger yields citations to
# check, are plan `21-02`'s. Measured at this phase's pinned base: there are
# ZERO citation-shaped tokens in any status cell, scanned with the lint's own
# symbol and line-citation patterns. A guard raising on zero citations would
# FAIL on landing and would redden `ci-core` for five waves, in a phase whose
# own Makefile contract is that `ci-core` stays green from wave one. Both are
# RELOCATED to the wave where the first citations exist, not weakened. Only the
# zero-ROW guard lands here, because a zero-row parse is false today.
#
# The REFUSAL itself is correct here and needs nothing added later: a citation,
# IF present, must resolve as written. That is vacuously true at zero citations
# and becomes load-bearing the instant the first one is written.
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

_REPO_INDEX_CACHE: dict[str, list[str]] = {}


def _index() -> dict[str, list[str]]:
    """`tools.lints.citations.repo_index` over this repo, computed once.

    The lint's own index rather than a bare `rglob`, because `repo_index`
    prunes `SKIP_DIRS` — and a bare walk over a live agent worktree makes
    EVERY basename ambiguous, which is how an ambiguity check silently stops
    checking anything.
    """
    if not _REPO_INDEX_CACHE:
        _REPO_INDEX_CACHE.update(repo_index(REPO_ROOT))
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

    The lint's own two patterns — `path.py::symbol` and `path.ext:NN[-MM]` —
    plus the wider symbol form above, so a `::symbol` citation on a
    non-Python path reaches the refusal instead of vanishing.
    """
    found: list[tuple[str, str]] = []
    for req_id, _phase, status in traceability_rows(document_text):
        seen: set[str] = set()
        patterns = (NODE_ID, CITATION, LOOSE_NODE_ID)
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
    """
    rows = traceability_rows(document_text)
    if not rows:
        raise AssertionError(
            "the traceability table parsed to no rows, so 'every citation is a"
            " full path' would pass over nothing. A refusal that has never had"
            " a subject is not a refusal"
        )
    symbol_paths = set(symbol_cited_paths(document_text))
    index = _index()
    messages: list[str] = []
    for req_id, cited in citations_in_status_cells(document_text):
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

    Built rather than doctored from the real file because at this wave the
    real file carries no citations at all, so there is nothing to doctor.
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

    **Vacuously true at this wave, measured and stated**: the ledger carries
    zero citation-shaped tokens in any status cell today. Plan `21-02` lands
    the precondition that makes it non-vacuous, in the same task as the first
    citations. The refusal needs nothing added when it does — it is already
    the assertion that a citation, if present, resolves as written.
    """
    assert refuse_unresolvable(ledger_text()) == []


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


def test_the_positive_control_a_real_citation_is_not_refused() -> None:
    """Red on everything is not a discriminator.

    The subject is deliberately a path whose BASENAME is ambiguous in this
    repo — there are two `client.py`. It is accepted anyway, which is the
    whole design: a path that exists as written resolves at the direct branch
    and the ambiguity never arises.
    """
    cited = "src/ccf/client/client.py::ProductClient"
    assert refuse_unresolvable(_document_with_citation(cited)) == []
