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

import ast
import contextlib
import pathlib
import re
import subprocess
from collections.abc import Callable, Iterator, Sequence
from typing import NamedTuple

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

#: A tree that genuinely differs between the pinned base and HEAD.
#:
#: **It is no longer `CONTROL A`'s subject, nor `CONTROL 13`'s, and that is the
#: whole of `RR-9`.** Both controls diffed THIS while vouching for emptiness
#: assertions over :data:`FABRIC`, :data:`FENCE`, :data:`UAT_RECORDS`,
#: :data:`PINNED_FILES` and :data:`TESTS_TREE`, so neither could see a one-key
#: typo in any of those — the control stayed green because `.planning/` had
#: changed, which is true of every phase and says nothing about the constant the
#: assertion passes. Plan `21.1-08` re-aimed both onto their own constants
#: against a base derived PER MEMBER by :func:`derived_base`.
#:
#: Retained rather than deleted because :func:`asserted_pathspecs` enumerates it
#: and :func:`test_every_asserted_pathspec_names_a_tracked_subject` therefore
#: holds it to naming a real subject. It is not the target of any aim.
CHANGED_TREE: tuple[str, ...] = (".planning/",)

#: A SHA that resolves to nothing, for `CONTROL B`. Hex, so it is
#: syntactically a revision; absent, so it is not one.
UNRESOLVABLE_BASE = "0000000000000000000000000000000000000000"


# ===========================================================================
# Limb identity — the refusal dispatcher, the frozen roster, and the switch.
#
# `VAC-06`, plan `21.1-05`. Research found this phase's GENERATOR by mutation:
# neuter each refusal branch one at a time and EIGHT of this module's refusals
# could be deleted with all 51 tests still green. Nothing here proved that a
# CONTROL's mutation reaches the assertion it vouches for, which is why
# `CONTROL A`, `CONTROL 5` and `CONTROL 13` all shipped mis-aimed.
#
# **A limb with no identity cannot be quantified over.** Criterion 12 asks that
# EVERY refusal branch be either reachable and watched or identified and
# removed, and criterion 13 asks that every control be proven to reach the limb
# it vouches for. Neither is expressible until each limb has a name the module
# can hold, which is what this section installs.
# ===========================================================================

#: Every refusal branch in this module, one NAMED id per branch, as
#: `<function>.<branch>`.
#:
#: A frozen roster of NAMES and never a count (`D-21`). It is asserted by
#: MEMBERSHIP — :func:`_refuse` refuses an id that is not in it — and never by
#: length: a length test is satisfied by any roster of the right size, which is
#: precisely the substitution a roster exists to prevent.
#:
#: **Refusals only.** The four `path::symbol` findings inside
#: :func:`refuse_unresolvable` — the ambiguous basename, the unique basename,
#: the absent path, the directory, the unindexed path — are APPENDED to a
#: returned list rather than raised, so they are not limbs of this dispatcher.
#: They are watched by `CONTROL 1`–`CONTROL 4b` through the returned messages.
#:
#: Enumerated by reading the module rather than by transcription, and the
#: enumeration is held to that by :func:`test_no_refusal_bypasses_the_dispatcher`
#: below — a `raise AssertionError` outside a test body and outside the
#: dispatcher itself is a refusal that shipped without an identity.
LIMBS: frozenset[str] = frozenset(
    {
        "tracked_under.nonzero_exit",
        "fabric_diff.empty_base",
        "fabric_diff.empty_paths",
        "fabric_diff.untracked_member",
        "fabric_diff.nonzero_exit",
        "near_miss.too_short_to_transpose",
        "traceability_rows.header_absent",
        "traceability_rows.cell_count",
        "traceability_rows.zero_rows",
        "traceability_rows.duplicate_ids",
        "checkbox_channel.empty",
        "checkbox_channel.duplicate_ids",
        "_doctored.anchor_not_unique",
        "_table_line.not_unique",
        "_checkbox_line.not_unique",
        "_index.anchor_unresolved",
        "refuse_unresolvable.zero_citations",
        "uncovered_lint_citations.lint_matches_nothing",
        "derived_base.no_history",
        "derived_base.no_parent",
        "base_ledger_text.nonzero_exit",
        "roster_verdicts.absent_id",
        "uncited_verdicts.empty_roster",
        "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.cell_count",
        "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.verdict_unusable",
        "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.lead_not_bolded",
        "_duplicated_table_row.cell_count",
        "_duplicated_table_row.phase_collision",
        "_duplicated_table_row.twin_identical",
        "_duplicated_checkbox_bullet.not_a_bullet",
        "_duplicated_checkbox_bullet.twin_identical",
        "_duplicated_checkbox_bullet.twin_not_read",
        "carried_counts.empty_roster",
        "carried_counts.empty_source",
        "carried_counts.unbound_roster",
    }
)

#: The limbs currently turned OFF, for the length of one :func:`neutered` block.
#:
#: **This is the most dangerous object in the module and it is guarded twice.**
#: A limb in here does not raise; :func:`_refuse` returns and control flow
#: continues past the branch, which is exactly the mutation research used to
#: find the eight unfalsified refusals. Leaked, it disarms every assertion
#: downstream of it in silence. :func:`neutered` restores in a `finally`, an
#: autouse fixture asserts the set is empty after EVERY test in this module,
#: and :func:`test_the_neutering_switch_is_off_at_rest` asserts it at rest.
_NEUTERED: set[str] = set()


def _require_registered(limb: str) -> None:
    """Refuse a limb id that is not in :data:`LIMBS`.

    **Deliberately NOT routed through :func:`_refuse`, and this is structural.**
    A guard on the switch that can disarm every other guard must not itself be
    disarmable: were this a limb, neutering it would let an unregistered
    refusal ship AND let :func:`neutered` silently turn off a typo, which is
    failure mode 3 — *the mutation was invisible to the whole module*.
    """
    if limb not in LIMBS:
        raise AssertionError(
            f"the limb id {limb!r} is not in `LIMBS`. A refusal with no"
            " registered identity cannot be quantified over: no control can"
            " name it, no coverage check can see it is unwatched, and"
            " `neutered()` cannot tell it from a typo. Register it in `LIMBS`"
            " or use the id the branch already carries"
        )


def _refuse(limb: str, message: str) -> None:
    """Raise `message`, tagged with `limb` — unless `limb` is neutered.

    **Every refusal in this module raises through here**, so that each carries
    a UNIQUE registered id and a control can assert the IDENTITY of the limb it
    observes rather than a phrase two limbs happen to share. `CONTROL 5` is the
    cautionary case: it asserted `"no rows" in str(failure)`, which passes on
    the message of `refuse_unresolvable`'s zero-row limb AND on
    `traceability_rows`' — and it had been observing the second while its
    docstring named the first, for the whole of Phase 21.

    The id is APPENDED to the message rather than replacing any of it, so every
    control asserting a substring of its refusal keeps passing unamended.

    ``from None`` because :func:`traceability_rows` calls this from inside an
    ``except ValueError`` block and the chained `ValueError` is noise there.

    **Returning under neuter is the point, not a convenience.** Control flow
    continues past the branch, so a meta-control can ask the only question that
    matters about a guard — *does anything in this module notice when it stops
    guarding?*
    """
    _require_registered(limb)
    if limb in _NEUTERED:
        return
    raise AssertionError(f"{message} [limb:{limb}]") from None


@contextlib.contextmanager
def neutered(limb: str) -> Iterator[None]:
    """Turn one NAMED limb off for the length of the block, then restore it.

    Restores in a `finally`, so an assertion failing inside the block cannot
    leave the switch on. The id is required to be registered first: neutering a
    typo would turn nothing off while reading exactly like a mutation that
    landed, which is how a control passes for a reason unrelated to its subject.
    """
    _require_registered(limb)
    already_off = limb in _NEUTERED
    _NEUTERED.add(limb)
    try:
        yield
    finally:
        if not already_off:
            _NEUTERED.discard(limb)


def neutering_switch_offenders() -> list[str]:
    """Every limb currently turned off — empty at rest, and asserted so.

    A named function rather than an inline `assert not _NEUTERED`, so the
    fixture's predicate is one a control can call with a leak in force and
    watch report it. A guard falsifiable only by a one-off is the shape this
    phase exists to end, and this one guards the switch that can disarm
    everything else.
    """
    return sorted(_NEUTERED)


@pytest.fixture(autouse=True)
def _the_neutering_switch_is_restored() -> Iterator[None]:
    """After EVERY test in this module, the neutering switch is off.

    A :func:`neutered` block that failed to restore would leave its limb
    disarmed for every later test in the session — and every one of them would
    go GREEN over a guard that was no longer guarding. This reddens the run at
    the test that leaked instead.
    """
    yield
    leaked = neutering_switch_offenders()
    assert not leaked, (
        f"the neutering switch was left ON for {leaked!r} at the end of this"
        " test. Every refusal named there is disarmed for the rest of the"
        " session, so every later assertion that depends on one passes"
        " VACUOUSLY — the failure this module exists to catch, arriving"
        " through the machinery built to catch it"
    )


def test_the_neutering_switch_is_off_at_rest() -> None:
    """No limb is neutered in a module nobody has neutered anything in.

    The standing half of the pair. The autouse fixture catches a `neutered()`
    block that leaked; this catches a limb turned off at import — a module-level
    `_NEUTERED.add(...)`, or a fixture that adds and never removes — which the
    fixture would report against whichever unlucky test ran first.
    """
    assert neutering_switch_offenders() == [], (
        "a limb is turned off before any test asked for it:"
        f" {neutering_switch_offenders()!r}. Every refusal named there is"
        " disarmed for the whole session"
    )


def test_no_refusal_bypasses_the_dispatcher_and_no_limb_id_is_orphaned() -> None:
    """Every refusal has a registered id, and every registered id has a site.

    Read from this module's own SOURCE, by `ast`, because the property is
    structural: a `raise AssertionError` added tomorrow in a checker would be a
    refusal with no identity, invisible to every coverage question plans
    `21.1-06`–`21.1-08` are built to ask, and no behavioural test can see it
    until someone happens to hit it. `21.1-02` established the precedent — a
    source-level control, added after two divergent inline copies satisfied the
    behavioural one.

    **Three limbs, and the third is the one that bites.**

    1. no `raise AssertionError` outside a `test_*` body and outside the
       dispatcher itself. :func:`_refuse` and :func:`_require_registered` are
       the exceptions BY NAME — the dispatcher must raise, and its registration
       guard must raise un-neuterably;
    2. every `_refuse(...)` call names a literal id that is in :data:`LIMBS`
       AND whose prefix is the function it sits in, so `<function>.<branch>` is
       a fact rather than a convention;
    3. every id in :data:`LIMBS` has at least one call site. **An id with no
       site is the mirror of a site with no id** — it is what a removed limb
       leaves behind, and it makes a coverage sweep report a control watching
       a branch that no longer exists.
    """
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    dispatcher = {"_refuse", "_require_registered"}

    bypassing: list[str] = []
    mismatched: list[str] = []
    sited: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name.startswith("test_") or node.name in dispatcher:
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Raise)
                and isinstance(inner.exc, ast.Call)
                and isinstance(inner.exc.func, ast.Name)
                and inner.exc.func.id == "AssertionError"
            ):
                bypassing.append(f"{node.name}:{inner.lineno}")
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_refuse"
                and inner.args
                and isinstance(inner.args[0], ast.Constant)
            ):
                limb = inner.args[0].value
                sited.add(limb)
                if limb not in LIMBS or not limb.startswith(f"{node.name}."):
                    mismatched.append(f"{node.name}:{inner.lineno} -> {limb!r}")

    assert not bypassing, (
        f"these refusals raise `AssertionError` directly rather than through"
        f" `_refuse`, so they carry no limb id: {bypassing}. A refusal with no"
        " identity cannot be quantified over — no control can name it, and no"
        " coverage check can see that nothing watches it"
    )
    assert not mismatched, (
        f"these `_refuse` call sites name an id that is unregistered, or whose"
        f" prefix is not the function it sits in: {mismatched}. The id form is"
        " `<function>.<branch>`, and it is a fact about the source rather than"
        " a naming convention"
    )
    orphaned = sorted(LIMBS - sited)
    assert not orphaned, (
        f"these ids are in `LIMBS` with no `_refuse` call site anywhere:"
        f" {orphaned}. An id with no site is the mirror of a site with no id —"
        " it is what removing a limb leaves behind, and it makes a coverage"
        " sweep report a control watching a branch that no longer exists"
    )


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
        _refuse(
            "tracked_under.nonzero_exit",
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
        _refuse(
            "fabric_diff.empty_base",
            "no diff base was given, so `git diff` would compare HEAD against"
            " nothing and print nothing — which reads exactly like a clean tree"
        )
    if not paths:
        _refuse(
            "fabric_diff.empty_paths",
            "no paths were given, so the diff is limited to nothing and is"
            " empty regardless of what the phase changed"
        )
    for member in paths:
        if not tracked_under((member,)):
            _refuse(
                "fabric_diff.untracked_member",
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
        _refuse(
            "fabric_diff.nonzero_exit",
            f"`git diff --stat {base}..HEAD -- {list(paths)}` exited"
            f" {completed.returncode}, so its empty output says nothing about"
            f" the tree.\nstderr: {completed.stderr.strip()}"
        )
    return completed.stdout


def repository_root_commit() -> str:
    """This repository's root commit — the one commit that has no parent.

    DERIVED by ``git rev-list --max-parents=0 HEAD``, never written down.
    Criterion 14 forbids a hardcoded SHA in a derived base and a root commit is
    not exempt from that merely because it never moves.

    It exists so that :func:`derived_base`'s no-parent limb is REACHABLE. A
    registered limb nothing can reach is the dead-limb disposition criterion 12
    forbids, and registering one inside the plan that closes criterion 14 would
    be this phase's own defect class arriving in its own repair. Plan
    `21.1-05` applied the same discipline to :func:`base_ledger_text`, whose
    shallow-clone limb was unreachable until the base became a parameter.

    Returns the LAST line, which is the oldest root when a repository has more
    than one. An empty string when `git` finds none at all: the caller is
    `CONTROL 37`, which asserts the result is a full SHA before it uses it, so
    this needs no limb of its own — and a limb no input could reach is exactly
    what the paragraph above rules out.
    """
    completed = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    roots = completed.stdout.split()
    return roots[-1] if roots else ""


def derived_base(member: str, last_touching: str | None = None) -> str:
    """A commit at which ONE pathspec member genuinely differs from HEAD.

    `VAC-06`, criterion 14, plan `21.1-08`. **The shape `CONTROL 13` and
    `CONTROL A` needed and did not have.** Both claimed to be the non-vacuity
    proof for an emptiness assertion and both diffed :data:`CHANGED_TREE`
    instead of the constant the assertion they vouch for actually passes —
    `RR-9`. Neither could be repaired by swapping the constant in, because
    ``fabric_diff(pinned_base, TESTS_TREE)`` is the EMPTY STRING: `tests/` is
    genuinely untouched, which is the whole point of the assertion, so a
    re-aimed control asserting a non-empty diff against the PINNED base would
    simply fail. The base has to differ per member instead.

    **Derived, never written down.** ``git log -1 --format=%H -- <member>``
    names the commit that last touched this member; its parent is a base at
    which the member necessarily differs from HEAD, because nothing after that
    commit touched it. A SHA in the source would go stale on the first rebase
    or squash-merge while reading exactly as authoritative — criterion 14's
    prohibition, and the reason this is a function rather than a table.

    **ONE member, never a tuple, and that quantifier is the whole point.** It
    is the same per-member property plan `21.1-01` installed in
    :func:`fabric_diff`, arriving from the other side: a tuple-level derivation
    would take its base from whichever member happened to have history and
    carry a typo'd sibling along in silence.

    **Self-guarding, which is criterion 14's second half.** ``git log`` EXITS
    ZERO on a pathspec that matches nothing and prints NOTHING — measured for
    ``scr/``, ``runtimes/``, ``example/`` and ``tests-typo/`` — so a control
    reading that output would SKIP the member without noticing. The empty
    result is refused by name instead.

    `last_touching` is a parameter with a default for the reason
    :func:`base_ledger_text`'s base is: it makes the no-parent limb reachable.
    A member whose last-touching commit is a root commit has no ``^``, and
    nothing in this repository's history puts one there, so `CONTROL 37` hands
    it :func:`repository_root_commit` — a real root, derived — rather than the
    limb being registered and unreachable.

    Both refusals NAME the member. An aggregate report one level up is the
    defect class this module is about.
    """
    if last_touching is None:
        found = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", member],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        last_touching = found.stdout.strip()
        if not last_touching:
            _refuse(
                "derived_base.no_history",
                f"`git log -1 --format=%H -- {member!r}` named no commit, so"
                " nothing tracked has ever matched this member and no base can"
                " be derived from it. `git log` exits ZERO on a pathspec that"
                " matches nothing, so a one-key typo produces the empty string"
                " and a control reading it would SKIP the member in silence"
                " rather than fail — which is a member of a pathspec constant"
                " going unchecked while the control stays green."
                f"\nstderr: {found.stderr.strip()}"
            )
    parent = subprocess.run(
        ["git", "rev-parse", "--verify", f"{last_touching}^"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if parent.returncode != 0:
        _refuse(
            "derived_base.no_parent",
            f"the commit that last touched {member!r} has no resolvable"
            f" parent — `git rev-parse --verify {last_touching}^` exited"
            f" {parent.returncode} — so there is no earlier commit to diff"
            " this member against. A root commit reaches this, and so does a"
            " history truncated by a shallow clone. Returning its empty stdout"
            " would hand `fabric_diff` an empty base, which compares HEAD"
            f" against nothing and prints nothing.\nstderr:"
            f" {parent.stderr.strip()}"
        )
    return parent.stdout.strip()


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


#: The four emptiness assertions `CONTROL A` is the non-vacuity proof for, named
#: by the pathspec constant each one passes.
#:
#: A frozen roster of NAMES (`D-21`), resolved through
#: :func:`asserted_pathspecs` at call time rather than spelled as literals in
#: the control's body — which is the property that makes `CONTROL 38`'s
#: substitution visible to the control at all.
#:
#: **Kept at four rather than narrowed to fit a weaker control.** `CONTROL A`'s
#: docstring has always claimed to be "the non-vacuity proof for all four
#: emptiness assertions above at once", and `RECON-08`'s shipped ledger cell
#: repeats that claim verbatim. Narrowing a claim to fit a weak control is the
#: move this phase exists to stop, so the control was strengthened to the claim
#: instead: nineteen members, each against its own derived base.
CONTROL_A_PATHSPECS: frozenset[str] = frozenset(
    {"FABRIC", "FENCE", "UAT_RECORDS", "PINNED_FILES"}
)


def test_control_a_a_base_and_path_that_differ_produce_output() -> None:
    """CONTROL A — the four emptiness assertions, proven to be comparing something.

    **This is the control that matters**, and it is the non-vacuity proof for
    all four emptiness assertions above at once —
    :func:`test_the_fabric_is_untouched` over :data:`FABRIC`,
    :func:`test_the_scope_fence_holds` over :data:`FENCE`,
    :func:`test_the_human_needed_verification_records_are_untouched` over
    :data:`UAT_RECORDS` and :func:`test_the_citation_lint_is_not_modified` over
    :data:`PINNED_FILES`. Every one of them passes on an empty string, and an
    empty string is what a broken command, an unresolvable base and a misspelled
    path all produce.

    **It did not pass any of those four constants until plan `21.1-08`, and it
    was never observed RED.** It diffed :data:`CHANGED_TREE` — `.planning/`,
    which every phase writes to — so it was green for a reason unrelated to
    what it claimed to test, and a one-key typo in any of the nineteen members
    below left all four assertions vacuous with this control still green.
    `RR-9`, the third instance of this project's own defect class arriving
    inside the machinery built to catch it.

    **Per member, against a base derived per member.** The pinned base cannot
    serve: `tests/` is genuinely untouched against it and so, by construction,
    is anything else these assertions hold empty. :func:`derived_base` takes
    each member's own last-touching commit and uses its parent, which carries no
    SHA and produces a differing base for every one of the nineteen (criterion
    14). A member that matches nothing REFUSES there rather than being skipped.

    **The constants are resolved through :func:`asserted_pathspecs` at call
    time**, never spelled as literals here. A control carrying its constant in
    its own body does not read the constant at all, which would make
    `CONTROL 38`'s substitution invisible to it — `RR-9` re-shipping inside the
    repair for `RR-9`.
    """
    resolved = dict(asserted_pathspecs())
    unresolvable = sorted(CONTROL_A_PATHSPECS - set(resolved))
    assert not unresolvable, (
        f"`CONTROL_A_PATHSPECS` names {unresolvable}, which"
        " `asserted_pathspecs()` does not resolve. The assertions those names"
        " stand for would then be vouched for by nothing at all"
    )
    compared: list[str] = []
    for name in sorted(CONTROL_A_PATHSPECS):
        for member in resolved[name]:
            base = derived_base(member)
            diff = fabric_diff(base, (member,))
            compared.append(f"{name}:{member}")
            assert diff.strip(), (
                f"`git diff --stat {base}..HEAD -- {member}` produced NOTHING"
                f" for the member {member!r} of {name}, whose base is the parent"
                " of its own last-touching commit — so the member demonstrably"
                " changed in that commit and nothing has touched it since. An"
                " empty diff here means the comparison is broken, and the"
                f" emptiness assertion over {name} is therefore saying nothing"
                " about that member at all"
            )
    assert compared, (
        "this control compared NOTHING — `CONTROL_A_PATHSPECS` or the constants"
        " it names resolved to no members at all, so it passed over the empty"
        " set and all four emptiness assertions are vouched for by nothing."
        " That is the vacuity this control exists to detect, arriving inside"
        " the control itself"
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
        _refuse(
            "near_miss.too_short_to_transpose",
            f"the pathspec member {member!r} is too short to misspell by"
            " transposition, so no near miss can be derived from it"
        )
        return member
    return f"{stem[:-2]}{stem[-1]}{stem[-2]}{slash}"


def multi_member_cases() -> tuple[tuple[str, int], ...]:
    """`CONTROL 18`'s subjects: each multi-member constant, EVERY member.

    **Widened from two positions to every member at the phase close, by the
    §3.1 panel's `B-1`.** Two positions — first and last — defeats a degenerate
    implementation that inspects ``paths[0]``, and defeats one that inspects
    ``paths[-1]``. It does NOT defeat one that inspects both ends, and that is
    the implementation the per-member fix exists to exclude. Measured: with
    :func:`fabric_diff` degraded to ``paths[:1] + paths[-1:]`` the whole suite
    stayed green, while a typo in any of :data:`UAT_RECORDS`' nine interior
    members still produced a silent empty diff — `RR-1`'s own failure mode,
    unwatched.

    A control that quantifies over a spot-check while the code it vouches for
    quantifies over a collection is the tuple-versus-members defect one level
    up, which is why the cases now come from the constants' own arity.

    Each case still mutates EXACTLY ONE member, which is what criterion 2 asks
    for; there are simply as many cases as there are members. The second
    element is the member INDEX, so what a case mutates is visible to
    :func:`test_control_41_the_multi_member_cases_reach_every_member` rather
    than derived privately inside `CONTROL 18`.

    The arity is read from this module's own globals and NOT from
    :func:`asserted_pathspecs`, for one reason that is easy to "fix" back into
    a defect: this function runs at IMPORT time, inside
    ``@pytest.mark.parametrize``, and :func:`asserted_pathspecs` names
    :data:`TESTS_TREE`, which is bound far below this line. Calling it here
    raises `NameError` at collection. The tie to the authoritative resolver is
    kept where it can be checked instead —
    :func:`test_control_41_the_multi_member_cases_reach_every_member` compares
    these cases against :func:`asserted_pathspecs` at TEST time, so the two
    cannot drift apart in silence.
    """
    return tuple(
        (name, index)
        for name in sorted(MULTI_MEMBER_PATHSPECS)
        for index in range(len(globals()[name]))
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


def test_control_41_the_multi_member_cases_reach_every_member() -> None:
    """CONTROL 41 — `CONTROL 18`'s subjects reach EVERY member, not two ends.

    **`B-1`, found by the §3.1 close panel — cursor and codex converged on it
    independently.** `RR-1` was that :func:`tracked_under` was applied to the
    pathspec TUPLE and not to its MEMBERS. Wave 1 quantified
    :func:`fabric_diff` per member and built `CONTROL 18` to prove it, and
    `CONTROL 18` did not prove it: :func:`multi_member_cases` yielded two cases
    per constant, the first member and the last, so every member BETWEEN the
    ends was mutated by nothing.

    Measured against the shipped module before this control existed:
    :func:`fabric_diff` degraded to validate only ``paths[:1] + paths[-1:]``
    left the whole suite GREEN. :data:`UAT_RECORDS` has eleven members, so a
    one-key typo in any of members 2 through 10 produced a silent empty diff
    over a real breach — `RR-1`'s own failure mode, in the constant with the
    most members, watched by nothing.

    Two ends is not an arbitrary weakening: it is what defeats a degenerate
    implementation reading ONE end. It does not defeat one reading BOTH ends,
    and *that* is the implementation the fix has to exclude. The remedy is to
    quantify the CASES the way the fix quantifies the members.

    The case's second element is the member INDEX rather than a position word,
    because a position word leaves `CONTROL 18` to derive the index privately
    and leaves this check nothing to compare. What a control mutates has to be
    visible in the case, or its coverage is unmeasurable from outside it.

    No count is asserted (`D-21`): what is compared is two sets of indices,
    derived from the constants' own arity.
    """
    resolved = dict(asserted_pathspecs())
    covered: dict[str, set[object]] = {}
    for name, index in multi_member_cases():
        covered.setdefault(name, set()).add(index)

    assert covered, (
        "`multi_member_cases()` produced NO cases at all, so `CONTROL 18` is"
        " parametrized over the empty set and reports green having mutated"
        " nothing. That is the vacuity this module exists to detect, arriving"
        " in the generator that feeds the control which closed `RR-1`"
    )

    unmutated: list[str] = []
    for name in sorted(MULTI_MEMBER_PATHSPECS):
        every = set(range(len(resolved[name])))
        gap = sorted(every - covered.get(name, set()), key=repr)
        if gap:
            unmutated.append(
                f"{name} has members at indices {sorted(every)} and"
                f" `multi_member_cases()` mutates {sorted(covered.get(name, set()), key=repr)}."
                f" Members {gap} are mutated by no case, so a `fabric_diff`"
                f" that validated only the members it does mutate would pass"
                f" `CONTROL 18` while a typo in {gap} still produced a silent"
                " empty diff — which is RR-1 exactly"
            )
    assert not unmutated, "\n".join(unmutated)


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


@pytest.mark.parametrize("name,index", multi_member_cases())
def test_control_18_one_misspelled_member_of_a_multi_member_pathspec_is_refused(
    name: str, index: int
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


def _control_18_over_every_case() -> None:
    """`CONTROL 18`'s registry thunk — EVERY case, not a representative one.

    The entry used to bind one pair and say that a proof on one case is a proof
    of reach, because every case reaches the same limb. That reasoning is sound
    about the LIMB and silent about the CASES: a control whose parametrization
    shrinks still satisfies a thunk that names one surviving case by hand. The
    close panel raised exactly that (cursor, finding 3), and since `B-1` widened
    the case set from two per constant to every member, a hand-bound
    representative is also a second place the arity has to be maintained.

    Running the generator means `CONTROL 35`'s neutered invocation covers every
    member of every multi-member constant, and nothing here names a case.
    """
    for name, index in multi_member_cases():
        test_control_18_one_misspelled_member_of_a_multi_member_pathspec_is_refused(
            name, index
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

#: The requirement ids THIS PHASE FAMILY MINTED FOR ITSELF, across both of its
#: phases: Phase 21's ten `RECON-` ids, minted into both channels as `Pending`
#: by plan `21-01` task 2 and verdicted by plan `21-06`, and Phase 21.1's six
#: `VAC-` ids, minted by plan `21.1-01` task 3 and verdicted by plan `21.1-09`.
#:
#: **Why the phase's own rows are held to the gate the phase imposes.** Four
#: checks read this roster — :func:`test_every_phase_own_row_carries_a_verdict`,
#: :func:`test_every_recon_row_is_present_in_both_channels`, the roster-scoped
#: two-verdict gate, and :func:`uncited_verdicts` through
#: :func:`test_every_verdicted_roster_row_cites_its_evidence`. A phase that
#: exempted its own rows from them would be auditing everyone's ledger honesty
#: but its own, which is the defect one level up rather than a smaller one. The
#: argument is not decoration: it is why the six were minted in WAVE 1 rather
#: than at the gate. Rows written inside the gate checkpoint carry verdicts no
#: reviewer and no approver has ever seen, and the panel would then be reading a
#: different document from the one Dave approves.
#:
#: **The ORDER of the two edits is load-bearing and is the sequencing trap Phase
#: 21 learned the hard way.** Extending this roster makes those four gates start
#: reading the new ids, and they are TRUE only once the verdicts are written. A
#: roster extension landing before the verdicts ships a red module.
#:
#: A FROZEN ROSTER OF NAMED IDS, per `D-21`, never a count. Its members are NOT
#: members of the 54-row working set Phase 21 audits — that set is its own
#: frozen roster, taken by the strict parse at the pinned base — and the two
#: rosters are deliberately unioned rather than merged wherever a check must
#: cover both.
#:
#: Provenance, as HISTORY and read by no assertion here: the traceability table
#: carried 133 rows at the pinned base, 143 from plan `21-01` task 2, and 149
#: from plan `21.1-01`. `D-21`'s binding consequence is that no standing check
#: in this phase family hardcodes any of those figures — what is asserted is
#: that the two channels agree id-for-id on whatever the ledger contains. A
#: reader who greps the pinned base and counts 133 has not found a discrepancy.
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
        "VAC-01",
        "VAC-02",
        "VAC-03",
        "VAC-04",
        "VAC-05",
        "VAC-06",
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
        _refuse(
            "traceability_rows.header_absent",
            "the traceability table header"
            f" {TABLE_HEADER!r} was not found in the document. A parser that"
            " returned nothing here would report a clean, agreeing, fully"
            " vocabularised ledger over a table it never located",
        )
        return []
    rows: list[tuple[str, str, str]] = []
    for line in lines[header_at + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != CELLS_PER_ROW:
            _refuse(
                "traceability_rows.cell_count",
                f"traceability row {line!r} split into {cells!r}, which is not"
                " the three cells a `| id | phase | status |` row has"
            )
            continue
        rows.append((cells[0], cells[1], cells[2]))
    if not rows:
        _refuse(
            "traceability_rows.zero_rows",
            "the traceability table header was found but no rows followed it."
            " Every check built on this parse would pass over nothing"
        )
    twice = repeated_ids([req_id for req_id, _phase, _status in rows])
    if twice:
        _refuse(
            "traceability_rows.duplicate_ids",
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
        _refuse(
            "checkbox_channel.empty",
            "the checkbox channel parsed to nothing. Either the document is"
            " not the ledger or the bullet shape changed; either way a"
            " comparison against an empty channel agrees with everything"
        )
    twice = repeated_ids(matched)
    if twice:
        _refuse(
            "checkbox_channel.duplicate_ids",
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
        _refuse(
            "_doctored.anchor_not_unique",
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
        _refuse(
            "_table_line.not_unique",
            f"{req_id} matched {matches!r} traceability lines; a control that"
            " doctors nothing, or doctors twice, is not the control it claims"
        )
    return matches[0] if matches else ""


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
        _refuse(
            "_checkbox_line.not_unique",
            f"{req_id} matched {matches!r} checkbox bullets; a control that"
            " doctors nothing, or doctors twice, is not the control it claims"
        )
    return matches[0] if matches else ""


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

    **The name says `recon` and the roster is now wider.** It reads
    :data:`PHASE_OWN_ROSTER`, which plan `21.1-09` extended to the six `VAC-`
    ids alongside the ten `RECON-` ids; the name is left as landed because
    renaming a shipped test to track a widened subject buys nothing a reader
    needs and costs every citation that names it. What the test asserts has
    never been "the `RECON-` rows" — it has always been *whatever this phase
    family minted for itself*, and that is what the roster holds.

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
        _refuse(
            "_index.anchor_unresolved",
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

    **One vacuity limb, and the second was REMOVED as structurally dead.**
    A zero-ROW parse raised here from plan ``21-01`` until plan ``21.1-05``
    deleted the branch: :func:`traceability_rows` refuses the same input FIRST,
    so no argument to this function could ever reach it. Research found it by
    mutation — neutered, the whole suite stayed green — and criterion 12's
    second disposition applies: *unreachable, and REMOVED*. Measured at the
    removal, the branch was reachable ONLY with the upstream limb disarmed,
    which is test machinery and not an input:

    * both limbs present → ``[limb:traceability_rows.zero_rows]``
    * ``traceability_rows.zero_rows`` neutered →
      ``[limb:refuse_unresolvable.zero_rows]``

    and **both messages contain the phrase "no rows"**, which is exactly how
    `CONTROL 5` observed one limb for the whole of Phase 21 while its docstring
    named the other.

    A zero-CITATION parse raises since plan ``21-02`` task 1, and not before:
    measured with this module's own extractor
    at the phase's pinned base, ``citations_in_status_cells(ledger_text())``
    returned **zero** tokens across every status cell, so the guard would have
    failed on landing and reddened ``ci-core`` for five waves. It was
    RELOCATED to the wave that writes the first citations, never weakened —
    ``CONTROL 5b`` watches it refuse, and
    :func:`test_the_scan_finds_citations_to_check` is the precondition proving
    the real ledger now yields citations for the refusal to be about.
    """
    # The parse still runs, and its OWN refusals still fire — a header that
    # was never found and a table with zero rows are refused inside
    # `traceability_rows`, by `traceability_rows.header_absent` and
    # `traceability_rows.zero_rows`. Its return value is deliberately unused.
    traceability_rows(document_text)
    cited_pairs = citations_in_status_cells(document_text)
    if not cited_pairs:
        _refuse(
            "refuse_unresolvable.zero_citations",
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
    """The wave-one vacuity floor: no subject means refuse, never return clean.

    **RE-AIMED by plan `21.1-05`, and the history is the point.** Through the
    whole of Phase 21 this docstring claimed the limb inside
    :func:`refuse_unresolvable`. The refusal it has ALWAYS observed belongs to
    :func:`traceability_rows`, which raises on the same input one function
    earlier — and the limb it named was structurally unreachable and is now
    removed. Found by mutation in Phase 21.1; it is the third mis-aimed control
    in this module, after `CONTROL A` and `CONTROL 13`.

    **What let the mis-aim survive is the ASSERTION, not the docstring.** It
    read ``"no rows" in str(failure)``, and both limbs' messages contain that
    phrase — measured before the removal, with the upstream limb neutered the
    downstream one caught the same subject and this control stayed GREEN over
    an entirely different refusal. Two limbs sharing a substring are
    indistinguishable to a substring assertion.

    So it asserts the LIMB ID from here on. A control names the identity of the
    refusal it observes, never a phrase two refusals happen to share, and
    `neutered("traceability_rows.zero_rows")` turns this control RED — the
    first time in this module's life a control has been proven to reach the
    limb it names.
    """
    limb = "traceability_rows.zero_rows"
    empty = "\n".join((TABLE_HEADER, "|-------------|-------|--------|", ""))
    try:
        messages = refuse_unresolvable(empty)
    except AssertionError as failure:
        assert f"[limb:{limb}]" in str(failure), (
            f"a table with no rows was refused by a limb other than {limb!r}:"
            f" {failure}. This control's subject is the zero-row parse, and"
            " asserting the shared phrase 'no rows' instead of the limb id is"
            " what let it vouch for a refusal one function further in for the"
            " whole of Phase 21"
        )
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
#: THE TEN `RECON-` ROWS ARE NOT MEMBERS, and neither are the six `VAC-` rows
#: Phase 21.1 minted; their absence is structural rather than a judgement call.
#: They are this phase family's OWN requirements, minted by plan `21-01` task 2
#: and plan `21.1-01` task 3, both AFTER the base was pinned, so a parse taken
#: at that base cannot contain them by construction. They are audited by
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


def base_ledger_text(base: str | None = None) -> str:
    """`.planning/REQUIREMENTS.md` as it stood at `base`, or at the pinned base.

    Raises on a non-zero `git` exit for the reason :func:`fabric_diff` does:
    an empty string from a failed command is indistinguishable from an empty
    string from a real read, and a roster comparison against an empty parse
    would be a comparison against nothing. In CI this is the assertion that
    needs full history — a depth-1 clone cannot resolve the base, `git`
    exits non-zero, and this raises rather than reporting a clean roster. **A
    depth-1 clone is not hypothetical here: it is a CI failure this project hit
    for real at the Phase 20 close.**

    **It takes its base as an ARGUMENT since plan `21.1-05`, and the repair is
    the whole reason the guard still exists.** Taking no argument made the
    refusal unreachable — no caller could hand it a base that fails to resolve
    — and criterion 12 as authored offered only *reachable and watched* or
    *unreachable and REMOVED*, which would have deleted a guard against a
    failure this project has actually hit. `D-IMPL-179` limb 2 (Dave,
    2026-08-22) ruled repair permitted: *"Deletion is for unreachable or
    revoked limbs, not for a limb that can be made true."* Repaired, the limb
    satisfies criterion 12's FIRST disposition outright, so this is arguably
    not a third disposition at all — only the first one reached honestly.

    The parameter defaults to :func:`phase_base_commit`, so every existing call
    site is unchanged, and it is the same shape :func:`derived_uat_records` and
    :func:`derived_working_set` already take. Its control lands in `21.1-06`.
    """
    completed = subprocess.run(
        [
            "git",
            "show",
            f"{base or phase_base_commit()}:.planning/REQUIREMENTS.md",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        _refuse(
            "base_ledger_text.nonzero_exit",
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
        _refuse(
            "roster_verdicts.absent_id",
            f"{absent} named in {roster_name} but absent from the traceability"
            " table. A completeness assertion that skipped them would report"
            " green over a ledger that had quietly lost a row"
        )
    return [
        (req_id, verdict_token(table[req_id]))
        for req_id in sorted(roster)
        if req_id in table
    ]


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
        _refuse(
            "uncited_verdicts.empty_roster",
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
    """The phase family's own sixteen, held to the gate they impose on the fifty-four.

    Ten `RECON-` ids from Phase 21, verdicted by plan `21-06`, and six `VAC-`
    ids from Phase 21.1, verdicted by plan `21.1-09`.

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

    Both rosters at once — the fifty-four this phase audits and the sixteen
    this phase family minted for itself — because `RECON-02` claims this
    property of the whole audit and the phase's own rows are held to the gate
    they impose. From plan `21.1-09` the second roster includes the six `VAC-`
    ids, so `VAC-03`'s verdict, whose evidence is a `.planning/` document, is
    held to the citation rule exactly as a verdict citing Python is.

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

    :func:`test_no_test_was_written_to_manufacture_a_citation` diffs
    :data:`TESTS_TREE` and requires the result to be empty. This proves that
    comparison is a comparison of something. `CONTROL A` makes the same argument
    for the fabric, the fence, the verification records and the citation lint;
    this one is stated separately because it falsifies a different claim and
    because criterion 6's mechanical limb rests on it alone. `RECON-02`'s
    shipped ledger cell cites it for exactly that proposition.

    **Until plan `21.1-08` it diffed :data:`CHANGED_TREE` and had never
    mentioned `tests/` at all** — `21-06-SUMMARY.md:144` recorded it as "GREEN,
    non-vacuously" and it was NEVER OBSERVED RED. Rename :data:`TESTS_TREE` to
    ``tests-typo/`` and criterion 6's mechanical limb went vacuous while this
    control stayed green, because `.planning/` had changed and `.planning/`
    always changes. `RR-9`, and `D-IMPL-170`: a control never observed failing
    is not a control.

    **It could not be repaired by swapping the constant in.**
    ``fabric_diff(pinned_base, TESTS_TREE)`` is the EMPTY STRING — `tests/` is
    genuinely untouched, which is the whole point of the assertion — so a
    re-aimed control asserting a non-empty diff against the pinned base would
    simply fail. :func:`derived_base` supplies a base at which the member does
    differ, derived from the member's own history and carrying no SHA, and it
    REFUSES on a member that matches nothing rather than skipping it.

    The constant is resolved through :func:`asserted_pathspecs` AT CALL TIME
    and never spelled as a literal here, so `CONTROL 38`'s substitution is
    visible to this control. :func:`fabric_diff` is reused rather than
    reimplemented: a second diff path could pass here and be broken there.
    """
    resolved = dict(asserted_pathspecs())
    assert "TESTS_TREE" in resolved, (
        "`asserted_pathspecs()` no longer resolves `TESTS_TREE`, so this"
        " control has nothing to diff and the `tests/` emptiness assertion is"
        " vouched for by nothing"
    )
    compared: list[str] = []
    for member in resolved["TESTS_TREE"]:
        base = derived_base(member)
        diff = fabric_diff(base, (member,))
        compared.append(member)
        assert diff.strip(), (
            f"`git diff --stat {base}..HEAD -- {member}` produced NOTHING for"
            f" the member {member!r} of TESTS_TREE, whose base is the parent of"
            " its own last-touching commit — so the member demonstrably changed"
            " in that commit and nothing has touched it since. An empty diff"
            " here means the comparison is broken, and criterion 6's mechanical"
            " limb is vacuous"
        )
    assert compared, (
        "this control compared NOTHING — `TESTS_TREE` resolved to no members at"
        " all, so it passed over the empty set and criterion 6's mechanical"
        " limb is vouched for by nothing"
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
        _refuse(
            "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.cell_count",
            f"{req_id}'s traceability line split into {cells!r}, which is not"
            " the three cells this mutation is built on"
        )
        return document_text
    status = cells[2]
    lead = verdict_token(status)
    if lead not in VERDICT_VOCABULARY or lead == later:
        _refuse(
            "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.verdict_unusable",
            f"{req_id} reads {lead!r}, which is either outside the vocabulary"
            f" or already {later!r}. Either way the mutation would not produce"
            " a cell asserting TWO DIFFERENT verdicts, which is the whole"
            " subject of this control"
        )
    if not status.startswith(f"**{lead}**"):
        _refuse(
            "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.lead_not_bolded",
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
        _refuse(
            "_duplicated_table_row.cell_count",
            f"{req_id}'s traceability line split into {cells!r}, which is not"
            " the three cells this mutation needs to rebuild the row"
        )
        return document_text
    other_phase = "Phase 99"
    if cells[1] == other_phase:
        _refuse(
            "_duplicated_table_row.phase_collision",
            f"{req_id}'s phase cell already reads {other_phase!r}, so the"
            " derived twin would be byte-identical to the row and"
            " `_doctored` would refuse a non-unique anchor for the wrong"
            " reason"
        )
    twin = f"| {cells[0]} | {other_phase} | {cells[2]} |"
    if twin == line:
        _refuse(
            "_duplicated_table_row.twin_identical",
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
        _refuse(
            "_duplicated_checkbox_bullet.not_a_bullet",
            f"{line!r} is not a checkbox bullet",
        )
        return document_text
    flipped = "x" if match.group(1).lower() != "x" else " "
    twin = line[: match.start(1)] + flipped + line[match.end(1) :]
    if twin == line:
        _refuse(
            "_duplicated_checkbox_bullet.twin_identical",
            f"the derived twin bullet for {req_id} is identical to its"
            " bullet, so the mutation would not be a SECOND bullet at all"
        )
    if CHECKBOX_LINE.match(twin) is None or CHECKBOX_LINE.match(twin).group(2) != req_id:  # type: ignore[union-attr]
        _refuse(
            "_duplicated_checkbox_bullet.twin_not_read",
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


def uncovered_lint_citations(
    document_text: str,
    lint_pattern: re.Pattern[str],
    widened: re.Pattern[str],
    name: str,
) -> list[str]:
    """One message per lint match no widened match's SPAN covers, in `document_text`.

    The subsumption predicate, taking its subject as an argument for the reason
    every other checker here does — so a control can point it at something
    other than the real ledger. Plan `21.1-05` task 0, `RR-11`, ruled by
    `D-IMPL-180`.

    **It compares SPANS, not path strings, and that is the whole repair.** The
    predicate shipped in wave 3 computed ``set(lint_pairs) - set(widened_pairs)``
    over PATH STRINGS. On a dotted citation the lint's `CITATION` opens its path
    group `[A-Za-z0-9_]`, matches one character LATE and yields the truncated
    twin `planning/…`; :data:`LOOSE_CITATION` matches at the dot and yields
    `.planning/…`. The widened match starts EARLIER and covers the lint's span
    entirely — **nothing was corrected away** — but `planning/…` is not
    `.planning/…`, so the twin scored as a silent drop and the gate could never
    be satisfied by the shape :data:`LOOSE_CITATION` exists to admit. Measured
    at the repair, on this module's own ledger path:

    * lint `CITATION`  → `planning/REQUIREMENTS.md` at ``(11, 37)``
    * `LOOSE_CITATION` → `.planning/REQUIREMENTS.md` at ``(10, 37)``

    Wave 3 was green here only because no dotted citation existed anywhere in
    the tree — failure mode 1, *the subject never reached the branch under
    test*, and it took a whole wave to produce a subject.

    **The anti-vacuity clause is kept and lives HERE rather than at the call
    site**, so a control can watch it refuse. *"Every lint match is covered"*
    is trivially true of a lint pattern that matches nothing, which is exactly
    the failure the check is for; and a repair that dropped the clause while
    adding span containment would pass every acceptance limb a control could
    write. It is refused with the subject, not asserted about the real ledger
    alone.

    **Containment of the SPAN, never of the string.** A lint match whose path
    string is a SUBSTRING of an unrelated widened path elsewhere in the same
    cell is still a drop; only the span form can tell a correction from a loss.
    `CONTROL 23b`'s fourth limb is that discriminator.

    Coverage is scoped to ONE CELL, because the extraction it stands in for is:
    a widened match in some other row says nothing about a lint match in this
    one.
    """
    messages: list[str] = []
    lint_matches_anything = False
    for req_id, _phase, status in traceability_rows(document_text):
        widened_spans = [match.span() for match in widened.finditer(status)]
        for match in lint_pattern.finditer(status):
            lint_matches_anything = True
            start, end = match.span()
            if any(
                covering_start <= start and end <= covering_end
                for covering_start, covering_end in widened_spans
            ):
                continue
            messages.append(
                f"{req_id}: the lint's `{name}` finds {match.group(0)!r} at"
                f" {match.span()} in its status cell and no match of the"
                " module-local widening covers that span — the widened"
                f" matches are {widened_spans}. The extraction tuple consults"
                " the widened pattern and NOT the lint's, so this citation is"
                " now invisible to `refuse_unresolvable`: dropped in silence,"
                " which is the exact hole this module exists to dodge from the"
                " outside"
            )
    if not lint_matches_anything:
        _refuse(
            "uncovered_lint_citations.lint_matches_nothing",
            f"the lint's `{name}` matches nothing in this document's status"
            " cells, so 'every citation the lint finds, the widening finds"
            " too' is quantified over the empty set and is trivially true."
            " A refusal that has never had a subject is not a refusal"
        )
    return messages


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
    to detect. It now lives inside :func:`uncovered_lint_citations` rather than
    in this test body, so `CONTROL 23b` can watch it refuse on a subject of its
    own — a clause no control can reach is the shape this phase is about.

    **It compares SPANS, repaired by plan `21.1-05` under `D-IMPL-180`.** As
    shipped in wave 3 it compared PATH STRINGS, and a dotted `.planning/…`
    citation was therefore scored a silent drop against the lint's truncated
    twin `planning/…` — which the widened match COVERS. The gate could not be
    satisfied by the one shape :data:`LOOSE_CITATION` was added for, and it was
    green only because no dotted citation existed anywhere in the tree.
    `RR-11`, found by wave 4 being the first plan to actually use the pattern.

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
        uncovered = uncovered_lint_citations(text, lint_pattern, widened, name)
        assert not uncovered, "\n".join(uncovered)


# ===========================================================================
# CONTROL 24 — CONTROL 33: THE REFUSALS NOTHING IN THIS MODULE COULD SEE.
#
# `VAC-06`, plan `21.1-06`. Research found the class by MUTATION: neuter one
# refusal branch at a time and re-run the suite. Every branch below could be
# disarmed with the whole module still GREEN — a guard nothing observes is a
# guard nobody can tell has stopped guarding, which is this phase's thesis
# arriving inside the machinery built to prove it.
#
# **CRITERION 8'S READING FOR A REFUSAL THAT ALREADY SHIPS.** Criterion 8 asks
# that every control this phase adds be watched failing against the PRE-FIX
# module and passing against the POST-FIX one. For these there is no fix: the
# refusals already work. Run against the pre-fix module they PASS. So the RED
# is produced by NEUTERING THE AIMED LIMB — the same mutation that found them
# — and that is STRONGER evidence, not weaker: a pre-fix red shows a control
# failing against a module that lacks the guard, whereas a neutered red shows
# it failing against the SHIPPED module with exactly one NAMED branch
# disarmed. That is what "proven to reach that branch" actually means, and it
# is what criterion 12 asks for. Both readings, and the conflict between them,
# are recorded in `21.1-06-SUMMARY.md` for the gate.
#
# **EVERY CONTROL HERE ASSERTS THE LIMB ID, NEVER A PHRASE.** `CONTROL 5` spent
# the whole of Phase 21 vouching for a refusal one function away from the one
# it watched, because both messages contain `"no rows"`. Two limbs sharing a
# substring are indistinguishable to a substring assertion; they are never
# indistinguishable to `[limb:<id>]`.
# ===========================================================================


def _table_document(*rows: str, bullets: Sequence[str] = ()) -> str:
    """A minimal well-formed ledger carrying exactly `rows` and `bullets`.

    The same idiom as :func:`_document_with_citation`, widened so a control can
    hand the parsers a MALFORMED row or an EMPTY checkbox channel. Built rather
    than doctored from the real file on purpose: doctoring a real row into
    malformedness makes the control depend on which row happened to be
    verdicted the day it ran, which is the drift :func:`_table_line` exists to
    end.
    """
    separator = "|-------------|-------|--------|"
    return "\n".join((*bullets, "", TABLE_HEADER, separator, *rows, ""))


def test_control_24_a_pathspec_git_rejects_refuses_rather_than_reading_empty() -> None:
    """CONTROL 24 — `tracked_under` on a pathspec `git` exits non-zero for.

    **An empty stdout from a FAILED command is indistinguishable from an empty
    stdout from a real answer**, and this function's empty list is what
    :func:`fabric_diff` reads to decide whether a pathspec names a real
    subject. So a `tracked_under` that swallowed a non-zero exit would report
    "this pathspec matches nothing" for a pathspec `git` never evaluated —
    which turns `fabric_diff`'s untracked-member refusal, and therefore every
    `D-11` scope-fence assertion in this module, into a test of nothing.

    Two measured subjects rather than one, because they fail `git` for
    different reasons: a path that escapes the repository, and a pathspec magic
    word that is not one. Both exit 128. Asserting the LIMB ID and not the word
    ``exited`` is deliberate — :data:`fabric_diff`'s own non-zero-exit limb
    carries the same word, and this control's subject is the one in
    :func:`tracked_under`.
    """
    limb = "tracked_under.nonzero_exit"
    for pathspec in (("../outside/",), (":(nonsense)x",)):
        try:
            tracked = tracked_under(pathspec)
        except AssertionError as failure:
            assert f"[limb:{limb}]" in str(failure), (
                f"`git ls-files` rejected {pathspec!r} and the refusal came"
                f" from a limb other than {limb!r}: {failure}"
            )
            continue
        raise AssertionError(
            f"`git ls-files -- {list(pathspec)}` exits non-zero and"
            f" `tracked_under` returned {tracked!r} instead of refusing. An"
            " empty list here reads exactly like 'this pathspec matches no"
            " tracked file', so `fabric_diff` would refuse a real subject —"
            " or, with the exit swallowed the other way, accept a comparison"
            " that had none"
        )


def test_control_25_a_traceability_row_that_is_not_three_cells_is_refused() -> None:
    """CONTROL 25 — `traceability_rows` on a row that is not `| id | phase | status |`.

    The parse is positional: the first, second and third cells are the id, the
    phase and the verdict. A row with a fourth cell — an unescaped `|` inside a status cell
    is the way this actually happens — would otherwise be read with its verdict
    in the wrong position, or silently dropped.

    **The subject carries a WELL-FORMED row beside the malformed one**, and
    that is not decoration. Neutered, this limb `continue`s and the malformed
    row is dropped; with no other row the parse would then be empty and
    :data:`traceability_rows.zero_rows` would refuse instead — a NEIGHBOURING
    limb catching the control's subject and passing on the aimed limb's behalf.
    That is exactly how `CONTROL 5` survived mis-aimed, and the well-formed row
    is what makes the neutered degradation SILENT rather than someone else's
    refusal.
    """
    limb = "traceability_rows.cell_count"
    subject = _table_document(
        "| TEST-01 | Phase 21 | Pending |",
        "| TEST-02 | Phase 21 | Pending | a fourth cell |",
    )
    try:
        rows = traceability_rows(subject)
    except AssertionError as failure:
        assert f"[limb:{limb}]" in str(failure), (
            f"a four-cell traceability row was refused by a limb other than"
            f" {limb!r}: {failure}. If the id names `zero_rows`, the malformed"
            " row was dropped and the parse then had no rows at all — a"
            " neighbouring limb catching this control's subject, which is the"
            " shape that let `CONTROL 5` vouch for the wrong refusal"
        )
        return
    raise AssertionError(
        f"a row that is not three cells parsed to {rows!r} instead of being"
        " refused. The parse is positional, so a row read with its verdict in"
        " the wrong cell is a verdict nobody wrote, and a row silently dropped"
        " is a requirement that stops being audited"
    )


def test_control_26_an_empty_checkbox_channel_is_refused() -> None:
    """CONTROL 26 — `checkbox_channel` on a document with a table and no bullets.

    **An empty channel AGREES WITH EVERYTHING.** :func:`channel_disagreements`
    compares the table against this mapping id by id; over an empty mapping
    every one of its three loops is quantified over the empty set, so it
    returns no messages and `D-02`'s two-channel discipline reports clean on a
    ledger whose second channel it never found. That is the same failure
    `CONTROL 8` watches one channel over, and it is why this parser raises
    rather than returning `{}`.

    The subject is a well-formed table with the bullet list REMOVED rather than
    a malformed bullet, because the failure being defended against is the
    bullet SHAPE changing — which makes every bullet invisible at once.
    """
    limb = "checkbox_channel.empty"
    subject = _table_document("| TEST-01 | Phase 21 | Pending |")
    try:
        boxes = checkbox_channel(subject)
    except AssertionError as failure:
        assert f"[limb:{limb}]" in str(failure), (
            "a document with no checkbox bullets was refused by a limb other"
            f" than {limb!r}: {failure}"
        )
        return
    raise AssertionError(
        f"a document with no checkbox bullets parsed to {boxes!r} instead of"
        " being refused. Every comparison against an empty channel agrees, so"
        " `channel_disagreements` would report a clean, agreeing ledger over a"
        " channel it never located"
    )


def test_control_27_a_control_mutation_that_lands_nowhere_or_twice_is_refused() -> None:
    """CONTROL 27 — `_doctored` on BOTH failure shapes: zero anchors and two.

    **This one matters more than its size suggests.** :func:`_doctored` is what
    every mutation-based control in this module relies on to have mutated
    anything at all. A control whose anchor drifted would hand the checker an
    UNMODIFIED document and then assert a refusal that never came — or worse,
    pass because something unrelated was wrong. It is the fixture that protects
    the controls, and until this landed nothing protected it: neutered, the
    whole module stayed green.

    Both shapes, because they are different failures with the same cost. Zero
    occurrences is an anchor that DRIFTED — the shape that broke `CONTROL 6`,
    `9` and `11` when plan `21-06` wrote the verdicts they had transcribed. Two
    occurrences is an anchor that is not the row it names, so the mutation
    lands somewhere the control never claimed.
    """
    limb = "_doctored.anchor_not_unique"
    cases = (
        ("lands nowhere", "a document", "an anchor that drifted"),
        ("lands twice", "a row and a row", "a row"),
    )
    for shape, document, anchor in cases:
        try:
            mutated = _doctored(document, anchor, "mutated")
        except AssertionError as failure:
            assert f"[limb:{limb}]" in str(failure), (
                f"a mutation that {shape} was refused by a limb other than"
                f" {limb!r}: {failure}"
            )
            continue
        raise AssertionError(
            f"a mutation that {shape} returned {mutated!r} instead of being"
            " refused. Every control in this module that doctors a document"
            " asserts a refusal afterwards; a mutation that did not land makes"
            " that assertion a claim about an unmodified subject"
        )


def test_control_28_a_table_anchor_that_is_absent_or_doubled_is_refused() -> None:
    """CONTROL 28 — `_table_line` on BOTH failure shapes: no line and two.

    :func:`_table_line` is :func:`_doctored`'s resolver: it turns an id into
    the one line a control may mutate, so that a control is anchored on the ROW
    rather than on a snapshot of the row's contents. Its refusal is what stops
    a control doctoring nothing (the id is gone) or doctoring an ambiguous
    subject (the id is doubled).

    **The subject is SYNTHETIC, and that is a deliberate choice with a reason
    on the record.** The real ledger reaches this refusal today for all
    fourteen `CPS-` ids, because the CPS-lane evidence table further down the
    file is a THIRD `| CPS-NN |` channel — carried advisory `A-7`, out of this
    phase's scope by Dave's bounding, re-measured in `21.1-06-SUMMARY.md`. A
    control keyed on `CPS-01` would be keyed on a defect someone may later
    close, and would go red on the day it was fixed.
    """
    limb = "_table_line.not_unique"
    absent = _table_document("| TEST-01 | Phase 21 | Pending |")
    doubled = _table_document(
        "| TEST-01 | Phase 21 | Pending |",
        "| TEST-01 | Phase 99 | Pending |",
    )
    cases = (
        ("matches no traceability line", absent, "NOPE-99"),
        ("matches two traceability lines", doubled, "TEST-01"),
    )
    for shape, subject, req_id in cases:
        try:
            line = _table_line(subject, req_id)
        except AssertionError as failure:
            assert f"[limb:{limb}]" in str(failure), (
                f"an anchor that {shape} was refused by a limb other than"
                f" {limb!r}: {failure}"
            )
            continue
        raise AssertionError(
            f"an id that {shape} resolved to {line!r} instead of being"
            " refused. A control anchored on it would doctor nothing, or"
            " doctor a subject it never named, and then assert a refusal about"
            " a document it did not change"
        )


def test_control_29_a_path_on_disk_but_absent_from_the_index_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONTROL 29 — `refuse_unresolvable`'s MOVED-PATH branch: `RR-6`'s other half.

    **This is the branch the function's own docstring calls "the second silent
    hole" it exists to dodge, and until this landed nothing in the module could
    see it work.** Its subject is a citation that resolves on disk while the
    lint's resolver index lists a DIFFERENT path for that basename — which is
    what a file move looks like from the index's side, and the shape the lint
    drops without a finding.

    **What the pre-fix module did, measured in plan `21.1-03` and recorded
    here where the next reader will find it.** On a THINNED index this branch
    returned SILENCE and an on-disk-but-unindexed path was ACCEPTED, while the
    ambiguity branch one clause up happened to go red — but only because
    `CONTROL 1` asserts the word AMBIGUOUS. One branch was guarded by ACCIDENT
    and this one by NOTHING. `CONTROL 22` closed the index's own refusal;
    this closes the branch downstream of it.

    **Substituting :func:`_index` bypasses the non-vacuity guard plan `21.1-03`
    installed inside it, and that is correct here.** This control is about the
    branch that READS the index, not about the index — an anchor check on a
    mapping the control built would only be re-asserting the control's own
    fixture.

    **The discriminator is a PHRASE and not a limb id, because this branch is
    not a limb.** The five `path::symbol` findings inside
    :func:`refuse_unresolvable` are APPENDED to a returned list rather than
    raised through :func:`_refuse`, so they carry no `[limb:…]` tag by design —
    registering them would have made :data:`LIMBS` a roster of FINDINGS rather
    than of refusal branches. The phrase asserted below is unique to this
    branch in the module; the check that it is unique is in
    `21.1-06-SUMMARY.md`, and it is the reason the assertion names the CITED
    PATH as well as the phrase.
    """
    moved_to = "some/other/place/client.py"
    basename = INDEX_ANCHOR.rsplit("/", maxsplit=1)[-1]
    monkeypatch.setattr(f"{__name__}._index", lambda: {basename: [moved_to]})
    assert (REPO_ROOT / INDEX_ANCHOR).is_file(), (
        f"{INDEX_ANCHOR} is not on disk, so this control's subject is not the"
        " on-disk-but-unindexed shape at all — it is the absent-path shape,"
        " which a different branch catches"
    )
    messages = refuse_unresolvable(_document_with_citation(f"{INDEX_ANCHOR}::ask"))
    assert any(
        "on disk but absent from the resolver's index" in message
        and INDEX_ANCHOR in message
        for message in messages
    ), (
        f"a citation to `{INDEX_ANCHOR}` — which IS on disk — was accepted"
        f" against an index that lists only {moved_to!r} for `{basename}`:"
        f" {messages!r}. That is the moved-path branch going SILENT, which is"
        " exactly what it did on a thinned index before `CONTROL 22` and what"
        " nothing in this module could observe until now. The lint treats such"
        " a basename as AMBIGUOUS and drops the citation without a finding"
    )


def test_control_30_an_unresolvable_diff_base_refuses_rather_than_reading_clean() -> (
    None
):
    """CONTROL 30 — `base_ledger_text` on a base `git show` cannot resolve.

    **The failure it guards is one this project hit for real at the Phase 20
    close: a depth-1 CI clone.** `git show <pinned base>:.planning/REQUIREMENTS.md`
    then exits non-zero and prints nothing, and a function that returned that
    empty stdout would hand :func:`derived_working_set` an empty document. The
    strict parse of nothing is the empty set, so the working-set roster would
    be re-derived as empty and every comparison against it would report a
    clean, fully-verdicted ledger — forever, and only in CI.

    Reachable only since plan `21.1-05` parameterised the function. Taking no
    argument made the limb unreachable, and criterion 12 as authored offered
    only *reachable and watched* or *unreachable and REMOVED* — which would
    have deleted a guard against a failure that has already happened here.
    `D-IMPL-179` limb 2 (Dave, 2026-08-22) ruled repair permitted, and this
    control is the second half of that ruling: repaired, the limb satisfies
    criterion 12's FIRST disposition outright.
    """
    limb = "base_ledger_text.nonzero_exit"
    try:
        text = base_ledger_text(UNRESOLVABLE_BASE)
    except AssertionError as failure:
        assert f"[limb:{limb}]" in str(failure), (
            "a base `git show` cannot resolve was refused by a limb other than"
            f" {limb!r}: {failure}"
        )
        return
    raise AssertionError(
        "`git show <unresolvable>:.planning/REQUIREMENTS.md` exits non-zero"
        f" and `base_ledger_text` returned {len(text)} characters instead of"
        " refusing. In a shallow CI clone the working-set roster would then be"
        " re-derived from an empty document, and a roster comparison against"
        " the empty set reports a clean ledger"
    )


def test_control_31_a_per_row_rule_over_an_empty_roster_is_refused() -> None:
    """CONTROL 31 — `uncited_verdicts` on an empty roster.

    **A per-row rule quantified over no rows is trivially satisfied**, which is
    the single shape this whole phase is about. Criterion 3 — every verdict
    other than `Not built` or `Orphaned` cites its evidence — is a per-row rule,
    and over an empty roster it holds without a single row having been looked
    at.

    **Research classified this limb as UNREACHABLE and that classification is
    wrong; the correction belongs on the page where the next reader will find
    it.** Both production call sites pass a populated roster, so no CALLER
    reaches it — but the function takes its roster as an ARGUMENT and a control
    can hand it an empty one. The distinction research missed is between a limb
    no INPUT can reach (:func:`refuse_unresolvable`'s zero-row branch, which
    plan `21.1-05` removed because :func:`traceability_rows` refuses the same
    input one function earlier) and a limb no CALLER happens to reach. Only the
    first is unreachable. Taking the subject as an argument is this module's
    own idiom, stated in :func:`derived_uat_records`' docstring.
    """
    limb = "uncited_verdicts.empty_roster"
    try:
        offenders = uncited_verdicts(ledger_text(), frozenset(), "an empty roster")
    except AssertionError as failure:
        assert f"[limb:{limb}]" in str(failure), (
            "an empty roster was refused by a limb other than"
            f" {limb!r}: {failure}"
        )
        return
    raise AssertionError(
        f"a per-row citation rule over an EMPTY roster returned {offenders!r}"
        " instead of refusing. No row was examined, so the rule held without"
        " being about anything — which is the vacuity this module exists to"
        " detect, arriving at the boundary of the check that detects it"
    )


# ---------------------------------------------------------------------------
# CONTROL 27b, 27c, 28b, 31b — TEN MORE UNWATCHED LIMBS, FOUND BY RUNNING THE
# MUTATION SWEEP OVER THE WHOLE ROSTER RATHER THAN OVER RESEARCH'S TABLE A.
#
# Research inventoried TWENTY refusal branches and found EIGHT unfalsified.
# Plan `21.1-05` built :data:`LIMBS` by reading the module and registered
# THIRTY. Re-run across all thirty — one limb neutered at a time, the whole
# module re-run each time — EIGHTEEN went unnoticed, not eight. The ten beyond
# research's list are the ones wave 5 added, and they are almost all in the
# CONTROL FIXTURES: the mutation helpers every other control in this module
# depends on to have mutated the thing it claims to have mutated.
#
# That is the same class as `CONTROL 27`, one level wider. These controls take
# sub-lettered numbers on the module's own convention (`4b`, `5b`, `9b`, `17b`,
# `23b`) so that no number belonging to plan `21.1-07` or `21.1-08` is
# consumed.
# ---------------------------------------------------------------------------


def test_control_27b_the_two_verdict_mutation_refuses_a_cell_it_cannot_mutate() -> None:
    """CONTROL 27b — all three limbs of `CONTROL 19`'s mutation helper.

    :func:`_cell_with_an_unbolded_lead_and_a_later_bolded_verdict` builds
    `RR-2`'s shape — an unbolded lead with a different verdict bolded after it
    — by DERIVING it from the victim's real cell. Three ways that derivation
    can fail to be the mutation it claims, and each one leaves `CONTROL 19`
    asserting a refusal about a cell that never asserted two verdicts:

    * the row is not three cells, so cell two is not the status at all;
    * the lead is outside the vocabulary, or is ALREADY the verdict the
      mutation would append — either way the result asserts one verdict, not
      two; and
    * the lead is not BOLDED to begin with, so un-bolding it is a no-op and
      the mutated cell is not `RR-2`'s shape.

    Each subject is chosen so the aimed limb fires FIRST. The vocabulary limb
    is reached through a lead that is already `Partial` rather than through a
    nonsense word, because a nonsense lead is also unbolded-by-the-time-it-is-
    read and the third limb would catch it on the second's behalf.
    """
    limb = "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict"
    cases = (
        (
            f"{limb}.cell_count",
            _table_document("| TEST-01 | Phase 21 | **Complete** x | a fourth |"),
        ),
        (
            f"{limb}.verdict_unusable",
            _table_document("| TEST-01 | Phase 21 | **Partial** — x |"),
        ),
        (
            f"{limb}.lead_not_bolded",
            _table_document("| TEST-01 | Phase 21 | Complete — x |"),
        ),
    )
    for aimed, subject in cases:
        try:
            mutated = _cell_with_an_unbolded_lead_and_a_later_bolded_verdict(
                subject, "TEST-01", "Partial"
            )
        except AssertionError as failure:
            assert f"[limb:{aimed}]" in str(failure), (
                f"the subject aimed at {aimed!r} was refused by a different"
                f" limb: {failure}. A neighbouring limb catching this"
                " control's subject is how `CONTROL 5` vouched for the wrong"
                " refusal for the whole of Phase 21"
            )
            continue
        raise AssertionError(
            f"a cell this mutation cannot turn into `RR-2`'s shape produced"
            f" {mutated[:120]!r} instead of being refused by {aimed!r}."
            " `CONTROL 19` would then assert that eight gates refuse a cell"
            " asserting two verdicts, over a cell asserting one"
        )


def test_control_27c_the_duplicate_row_mutation_refuses_a_twin_that_is_not_one() -> (
    None
):
    """CONTROL 27c — `_duplicated_table_row`'s two reachable limbs.

    `CONTROL 20`'s mutation helper derives a SECOND row for the same id,
    differing only in its phase cell. Two ways the derivation stops being that:
    a row that is not three cells cannot be rebuilt, and a row already reading
    the twin's phase would produce a byte-identical copy — which
    :func:`_doctored` would then refuse as a non-unique anchor, for the wrong
    reason and with the wrong message.

    The phase-collision subject uses a TIGHT status cell (``|Pending|`` rather
    than ``| Pending |``) on purpose. With canonical spacing the derived twin
    is byte-identical to the row, so neutering the aimed limb hands the subject
    to :data:`_duplicated_table_row.twin_identical` one clause down and the
    control would go red on a NEIGHBOUR rather than on silence. Tight spacing
    makes the twin genuinely different, so the aimed limb is the only thing
    standing between this subject and a silent, wrong mutation.
    """
    cases = (
        (
            "_duplicated_table_row.cell_count",
            _table_document("| TEST-01 | Phase 21 | Pending | a fourth |"),
        ),
        (
            "_duplicated_table_row.phase_collision",
            _table_document("| TEST-01 | Phase 99 |Pending|"),
        ),
    )
    for aimed, subject in cases:
        try:
            mutated = _duplicated_table_row(subject, "TEST-01")
        except AssertionError as failure:
            assert f"[limb:{aimed}]" in str(failure), (
                f"the subject aimed at {aimed!r} was refused by a different"
                f" limb: {failure}"
            )
            continue
        raise AssertionError(
            f"a row this mutation cannot duplicate produced {mutated[:120]!r}"
            f" instead of being refused by {aimed!r}. `CONTROL 20` would then"
            " watch the duplicate-id refusal over a document carrying no"
            " duplicate"
        )


def test_control_28b_a_checkbox_anchor_that_is_absent_or_doubled_is_refused() -> None:
    """CONTROL 28b — `_checkbox_line` on both failure shapes, `CONTROL 28`'s twin.

    The checkbox channel's resolver, and it needs its own control for the same
    reason the channel needs its own duplicate-id refusal: **a guard on one
    channel says nothing about the other.** `CONTROL 21` doctors a bullet
    resolved through this function, so an id that resolves to nothing — or to
    two bullets — would leave that control asserting a refusal about a document
    it did not change.
    """
    limb = "_checkbox_line.not_unique"
    absent = _table_document(
        "| TEST-01 | Phase 21 | Pending |",
        bullets=("- [ ] **TEST-01**: a control fixture",),
    )
    doubled = _table_document(
        "| TEST-01 | Phase 21 | Pending |",
        bullets=(
            "- [ ] **TEST-01**: a control fixture",
            "- [x] **TEST-01**: and its twin, ticked the other way",
        ),
    )
    cases = (
        ("matches no checkbox bullet", absent, "NOPE-99"),
        ("matches two checkbox bullets", doubled, "TEST-01"),
    )
    for shape, subject, req_id in cases:
        try:
            line = _checkbox_line(subject, req_id)
        except AssertionError as failure:
            assert f"[limb:{limb}]" in str(failure), (
                f"an anchor that {shape} was refused by a limb other than"
                f" {limb!r}: {failure}"
            )
            continue
        raise AssertionError(
            f"an id that {shape} resolved to {line!r} instead of being"
            " refused. `CONTROL 21`'s mutation would land nowhere, or land on"
            " a bullet it never named, and the refusal it then asserts would"
            " be about a document nobody mutated"
        )


def test_control_31b_a_pathspec_member_too_short_to_misspell_is_refused() -> None:
    """CONTROL 31b — `near_miss` on a member it cannot derive a misspelling from.

    :func:`near_miss` is `CONTROL 16`'s and `CONTROL 18`'s whole subject: it
    DERIVES a one-key typo by transposing a member's last two characters,
    rather than reading one out of a literal table that could drift away from
    the constants it names. A member too short to transpose has no near miss,
    and a helper that returned the member UNCHANGED would hand those controls
    the REAL pathspec — which matches real tracked files, so the assertion
    ``tracked_under(near_miss(member)) == []`` would fail confusingly, or, in
    the mutation direction, ``fabric_diff`` would be handed a spec that names a
    real subject and the control would report that a typo was accepted.

    Reachable at the function's own boundary, in the idiom `CONTROL 31`
    records: no production caller passes a one-character member — every member
    of every asserted pathspec is longer — but the function takes its member as
    an argument, and a limb no CALLER happens to reach is not a limb no INPUT
    can reach.
    """
    limb = "near_miss.too_short_to_transpose"
    for member in ("a", "x/"):
        try:
            derived = near_miss(member)
        except AssertionError as failure:
            assert f"[limb:{limb}]" in str(failure), (
                f"the member {member!r} was refused by a limb other than"
                f" {limb!r}: {failure}"
            )
            continue
        raise AssertionError(
            f"near_miss({member!r}) returned {derived!r} instead of refusing."
            " A near miss that is not a misspelling is the REAL pathspec, and"
            " a control handed the real pathspec is watching nothing"
        )


# ===========================================================================
# CONTROL 32 AND CONTROL 33 — THE GUARDS ON THE MACHINERY THIS PHASE BUILT.
#
# Plan `21.1-05` installed the refusal dispatcher, the `LIMBS` roster and the
# neutering switch, and it built the switch's own guards STANDING rather than
# as one-offs precisely so that these two controls could be aimed at them. It
# also quoted `D-IMPL-170` on the same page: **a sabotage run once and written
# up in a SUMMARY is a probe, not a control.** Until here, the two mechanisms
# whose silent failure would make every other control in this module VACUOUS
# were held by a probe each.
#
# Neither is a control over a refusal in the audited sense, so both belong to
# plan `21.1-07`'s `guard` aim kind — the one whose obligation is INVERTED:
# sabotage the guarded mechanism and require the control to fail. Each carries
# its saboteur in its docstring under `SABOTEUR:` so `21.1-07` can lift it into
# `CONTROL_AIM` without re-deriving it.
#
# **They are deliberately NOT `meta`.** A `meta` entry is excluded from every
# invocation loop by design, so filing them there would leave the two controls
# holding the two most dangerous mechanisms in the module registered,
# enumerated and AIM-UNPROVEN. `meta` is a regress-stopper for the aim-proving
# controls themselves; it is not a filing cabinet for a control that does not
# fit.
# ===========================================================================


def test_control_32_a_refusal_with_no_registered_identity_is_itself_refused() -> None:
    """CONTROL 32 — the dispatcher's UNREGISTERED-LIMB guard, held standing.

    **What it guards.** :func:`_require_registered` is what stops a refusal
    shipping without an identity. Every other control in this module asserts
    `[limb:<id>]`, `neutered()` disarms exactly one named id, and plan
    `21.1-07`'s coverage sweep quantifies over :data:`LIMBS` — all three rest on
    the id being REGISTERED rather than merely spelled. A later edit that
    turned this guard into a pass would let an unregistered id through
    silently, and the whole `LIMBS`/`CONTROL_AIM` scheme would quietly stop
    binding: a new refusal would carry a tag nobody enumerates, no coverage
    check would see it unwatched, and `neutered("typo")` would turn nothing off
    while reading exactly like a mutation that landed.

    **Both directions, because both callers matter.** :func:`_refuse` refuses
    an unregistered id at the RAISING side; :func:`neutered` refuses one at the
    DISARMING side. A guard on only the first would let a typo silently neuter
    nothing.

    **The refusal NAMES the offending id**, and this control asserts that it
    does. A message saying only "unregistered limb" would leave a reader to
    find the typo among thirty ids, which is the aggregate report this module
    is about one level up.

    **This guard is deliberately un-neuterable**, per plan `21.1-05`: it is not
    in :data:`LIMBS` and does not route through :func:`_refuse`, because a
    guard on the switch that can disarm every other guard must not itself be
    disarmable. So its RED comes from a source-level saboteur rather than from
    `neutered()`.

    SABOTEUR: make :func:`_require_registered` ACCEPT an unregistered id —
    replace its body with `return`.
    """
    stranger = "no.such.function.no_such_branch"
    assert stranger not in LIMBS, (
        f"{stranger!r} is a registered limb, so this control's subject is not"
        " an unregistered id at all and the guard it watches is never reached"
    )
    for name, call in (
        ("_refuse", lambda: _refuse(stranger, "a refusal with no identity")),
        ("neutered", lambda: neutered(stranger).__enter__()),
    ):
        try:
            call()
        except AssertionError as failure:
            assert stranger in str(failure), (
                f"`{name}` refused an unregistered id without NAMING it:"
                f" {failure}. A reader would have to find the typo among thirty"
                " registered ids"
            )
            assert "[limb:" not in str(failure), (
                f"`{name}`'s registration guard raised through the dispatcher"
                f" and carries a limb id: {failure}. It must not — a guard"
                " routed through `_refuse` is a guard `neutered()` can turn"
                " off, and this one guards the switch that turns the others off"
            )
            continue
        raise AssertionError(
            f"`{name}` ACCEPTED the unregistered limb id {stranger!r}. A"
            " refusal with no registered identity cannot be quantified over:"
            " no control can name it, no coverage sweep can see that nothing"
            " watches it, and `neutered()` cannot tell it from a typo — so"
            " every id-keyed guarantee in this module stops binding, in silence"
        )


def test_control_33_the_neutering_off_switch_cannot_leak_and_its_guard_can_fail() -> (
    None
):
    """CONTROL 33 — the `_NEUTERED` OFF-SWITCH, and the fixture that watches it.

    **What it guards, and why this is the most dangerous mechanism in the
    module.** :data:`_NEUTERED` disarms refusals. A limb left in it is disarmed
    for every test that runs afterwards in the session, and every one of those
    tests goes GREEN over a guard that is no longer guarding — the phase's own
    thesis arriving inside the machinery built to close it. One leak makes an
    arbitrary suffix of this module vacuous, and nothing about the run looks
    wrong.

    **Two limbs, because there are two ways the switch fails.**

    1. :func:`neutered` fails to RESTORE. Asserted the only way that matters:
       an exception is raised inside the block, which is precisely the case a
       restore written after the `yield` instead of in a `finally` would miss —
       and a control's assertion failing INSIDE a `neutered()` block is the
       single most likely way this module ever raises in one.
    2. The autouse fixture's PREDICATE stops reporting. A fixture nobody has
       watched fire is a fixture that might not. :func:`neutering_switch_offenders`
       is a named function for exactly this reason (plan `21.1-05`), so this
       limb leaks an id deliberately inside a scoped subject and requires the
       predicate to NAME it — rather than trusting a fixture that has only ever
       been observed passing.

    The leak is scoped in a `try`/`finally` of its own, so this control cannot
    become the leak it is testing for.

    SABOTEUR: (1) move :func:`neutered`'s restore out of its `finally` and
    after the `yield`; (2) make :func:`neutering_switch_offenders` return `[]`
    unconditionally.
    """
    limb = "traceability_rows.zero_rows"

    class _ControlBoom(Exception):
        """Raised inside a `neutered()` block, to prove the restore is a `finally`."""

    # --- limb 1: the restore survives an exception raised inside the block ---
    try:
        with neutered(limb):
            assert limb in neutering_switch_offenders(), (
                f"`neutered({limb!r})` did not turn the limb OFF, so the rest"
                " of this control watches a switch that was never thrown and"
                " the restore it asserts is a restore of nothing"
            )
            raise _ControlBoom
    except _ControlBoom:
        pass
    assert neutering_switch_offenders() == [], (
        f"`neutered({limb!r})` did not restore the limb when the block raised:"
        f" {neutering_switch_offenders()!r}. An assertion failing inside a"
        " `neutered()` block is the most likely way this module ever raises in"
        " one, and a restore written after the `yield` rather than in a"
        " `finally` would leave that limb disarmed for every test after it"
    )

    # --- limb 2: the fixture's own predicate REPORTS a leak, by name ---
    _NEUTERED.add(limb)
    try:
        leaked = neutering_switch_offenders()
    finally:
        _NEUTERED.discard(limb)
    assert leaked == [limb], (
        "the neutering switch was left ON and the guard's own predicate"
        f" reported {leaked!r} rather than {[limb]!r}. That predicate is what"
        " the autouse fixture asserts after EVERY test in this module; a"
        " predicate that cannot see a leak makes the fixture a decoration, and"
        " every assertion downstream of a leaked limb passes VACUOUSLY"
    )
    assert neutering_switch_offenders() == [], (
        "this control left the switch ON, which is the failure it exists to"
        f" detect: {neutering_switch_offenders()!r}"
    )


# ===========================================================================
# CONTROL 27d and CONTROL 27e — the four DEGRADATION SHIMS, held to the
# INVERTED obligation of `D-IMPL-181` (criterion 15).
#
# Plan `21.1-06` swept all thirty registered limbs and found four reachable
# ONLY with a sibling neutered. It filed them as `RR-12` and stopped, because
# criterion 12 as authored offered only *reachable-and-watched* or
# *unreachable-and-REMOVED*, and REMOVING these reinstates the crash plan
# `21.1-05` shaped them to prevent. Dave ruled the third disposition
# (`D-IMPL-181`, 2026-08-22): they are CONTROLLED, under a new aim kind
# `shim`, with an inverted obligation — and **coverage quantifies over `shim`
# exactly as over every other kind, with no exempt roster**, because an exempt
# roster *"excuses them without proving they work"*.
#
# WHY THE INVERSION MATTERS TO THE MACHINERY BELOW, AND NOT MERELY TO THE
# TAXONOMY. A crash and a caught defect are INDISTINGUISHABLE to a coverage
# assertion. If neutering limb X made this module explode, `CONTROL 34`'s
# coverage limb and `CONTROL 35`'s aim proof would both conclude "the control
# reaches limb X" when all either reached was the wreckage. These four exist
# so that a neutered sibling produces a NAMED refusal or a plain return, never
# an `AttributeError` — and each control below asserts BOTH halves: the shim
# fires by name when its sibling is disarmed, and the degradation stays SILENT
# when the shim itself is disarmed on top.
#
# HOW THEY ARE REACHED, MEASURED RATHER THAN REASONED. Three of the four need
# only a sibling neutered. The fourth —
# `_duplicated_checkbox_bullet.twin_identical` — is unreachable under EVERY
# input and every real regex, because `twin == line` requires the flipped tick
# to equal the tick it replaced and the tick class admits no such value. It is
# reached here by substituting a PATTERN OBJECT whose reported group span is a
# character the twin would rewrite to itself. That is a control fixture in
# this module's established idiom (`CONTROL 22` substitutes `repo_index`,
# `CONTROL 29` substitutes `_index`), not a reshaping of the shim — Dave
# rejected reshaping as *"new mechanism in a prove-existing-mechanism wave"*.
# ===========================================================================


class _TickSpanMatch:
    """A match object reporting a tick span that rewrites to ITSELF.

    `_duplicated_checkbox_bullet` builds its twin as
    ``line[:m.start(1)] + flipped + line[m.end(1):]`` where `flipped` is `"x"`
    unless `m.group(1)` already lowercases to `"x"`. Reporting a group VALUE
    the flip reads as "not a tick" while reporting a group SPAN that already
    holds an ``x`` makes the twin byte-identical to the line — which is the
    one shape `_duplicated_checkbox_bullet.twin_identical` exists to refuse and
    the only way to put a subject in front of it.
    """

    def __init__(self, span_at: int, req_id: str) -> None:
        self._span_at = span_at
        self._req_id = req_id

    def group(self, index: int) -> str:
        return "not-a-tick" if index == 1 else self._req_id

    def start(self, index: int) -> int:
        return self._span_at

    def end(self, index: int) -> int:
        return self._span_at + 1


class _TickSpanPattern:
    """:data:`CHECKBOX_LINE`, with every match's group-1 span moved onto an `x`.

    Delegates `finditer` to the real pattern so `checkbox_channel` and
    `_checkbox_line` still see the document exactly as they would; only the
    twin derivation inside `_duplicated_checkbox_bullet` is affected.
    """

    def __init__(self, real: re.Pattern[str], req_id: str) -> None:
        self._real = real
        self._req_id = req_id

    def match(self, line: str) -> _TickSpanMatch | None:
        found = self._real.match(line)
        if found is None:
            return None
        return _TickSpanMatch(found.start(1), self._req_id)

    def finditer(self, text: str) -> Iterator[re.Match[str]]:
        return self._real.finditer(text)


def _bullet_document(tick: str = "x") -> str:
    """A minimal ledger whose one row carries one checkbox bullet."""
    return _table_document(
        "| TEST-01 | Phase 21 | Pending |",
        bullets=(f"- [{tick}] **TEST-01**: a control fixture, not a requirement",),
    )


def test_control_27d_the_duplicate_row_twin_guard_fires_and_degrades_silently() -> (
    None
):
    """CONTROL 27d — `_duplicated_table_row.twin_identical`, a SHIM (`D-IMPL-181`).

    **Three limbs, in the order that makes the disposition legible.**

    1. the guard is DOWNSTREAM — on the same subject with nothing neutered,
       `_duplicated_table_row.phase_collision` one clause above catches it
       first, which is exactly why no input reaches this branch and why plan
       `21.1-06` could not write an ordinary control for it;
    2. with the sibling neutered the shim fires BY NAME, as an
       `AssertionError` carrying its own limb id — the SILENT degradation,
       rather than the `IndexError` a missing guard would produce further
       down;
    3. with the shim neutered on top, the helper returns without raising and
       the "duplicate" it produced is BYTE-IDENTICAL to the row it copied —
       a mutation that is not a mutation, handed to `CONTROL 20` as though it
       were one. That is what the shim is holding back, shown rather than
       asserted.

    SABOTEUR: `neutered("_duplicated_table_row.twin_identical")` — limb 2's
    refusal stops arriving and this control goes red on limb 2's own message.
    """
    limb = "_duplicated_table_row.twin_identical"
    sibling = "_duplicated_table_row.phase_collision"
    subject = _table_document("| TEST-01 | Phase 99 | Pending |")

    try:
        _duplicated_table_row(subject, "TEST-01")
    except AssertionError as failure:
        assert f"[limb:{sibling}]" in str(failure), (
            f"the subject was refused by a limb other than {sibling!r}:"
            f" {failure}. This control's whole disposition rests on the shim"
            " sitting DOWNSTREAM of a guard that catches every real input"
        )
    else:
        raise AssertionError(
            "the subject was ACCEPTED with nothing neutered, so"
            f" {limb!r} is reachable by an ordinary input after all and it is"
            " not a shim — it is a limb owed an ordinary control"
        )

    with neutered(sibling):
        try:
            produced = _duplicated_table_row(subject, "TEST-01")
        except AssertionError as failure:
            assert f"[limb:{limb}]" in str(failure), (
                f"with {sibling!r} disarmed the refusal came from a limb other"
                f" than {limb!r}: {failure}"
            )
        else:
            raise AssertionError(
                f"with {sibling!r} disarmed the derived twin was accepted and"
                f" the helper returned {produced[-60:]!r}. The mutation is then"
                " not a second row at all, and `CONTROL 20` would assert a"
                " duplicate-id refusal over a document carrying one row"
            )

        with neutered(limb):
            degraded = _duplicated_table_row(subject, "TEST-01")

    twins = [
        line for line in degraded.splitlines() if line.startswith("| TEST-01 | ")
    ]
    assert twins[1:] and twins[0] == twins[1], (
        "with the shim disarmed the helper was expected to degrade SILENTLY"
        " into a byte-identical pair — the shape the shim refuses — and it"
        f" produced {twins!r} instead. A crash here would be read as coverage"
        " by every meta-control below"
    )


def test_control_27e_the_duplicate_bullet_shims_fire_and_degrade_silently() -> None:
    """CONTROL 27e — the three `_duplicated_checkbox_bullet` SHIMS (`D-IMPL-181`).

    One control over all three because they are ONE degradation apparatus: the
    `not_a_bullet` shim's plain `return` is what stops `match.start(1)` raising
    an `AttributeError` when `_checkbox_line` has been disarmed, and the two
    twin guards below it are the tripwires that catch a derivation which
    stopped being a duplicate. Splitting them to fit a schema is the narrowing
    this phase exists to stop; `CONTROL C` is the standing precedent.

    **Each of the three is reached, fired by name, and then disarmed and
    watched degrading silently.**

    * `not_a_bullet` — reached with `_checkbox_line.not_unique` disarmed, so
      the helper is handed the empty string that limb returns. Disarmed on
      top, the helper RETURNS THE DOCUMENT UNCHANGED: that plain `return` is
      the shim, and deleting it is what brings the `AttributeError` back.
    * `twin_not_read` — reached by narrowing :data:`CHECKBOX_LINE` to the
      ticked form alone, so the flipped twin is no longer read as a bullet.
    * `twin_identical` — reached by substituting :class:`_TickSpanPattern`,
      because no input and no real pattern can make the flipped tick equal the
      tick it replaced (the class is `[ xX]` and the flip is total on all
      three). See the section banner for why that is a fixture rather than a
      reshaping.

    SABOTEUR: `neutered(<the shim's own id>)` — the named refusal stops
    arriving and this control goes red on that shim's `else` branch.
    """
    subject = _bullet_document()

    # --- `not_a_bullet`: the shim whose removal restores the AttributeError ---
    absent = "not_a_bullet"
    with neutered("_checkbox_line.not_unique"):
        try:
            _duplicated_checkbox_bullet(subject, "NOSUCH-99")
        except AssertionError as failure:
            assert f"[limb:_duplicated_checkbox_bullet.{absent}]" in str(failure), (
                "an id with no bullet, reached through a disarmed"
                f" `_checkbox_line`, was refused by another limb: {failure}"
            )
        else:
            raise AssertionError(
                "an id with no bullet at all was accepted by"
                " `_duplicated_checkbox_bullet`"
            )
        with neutered(f"_duplicated_checkbox_bullet.{absent}"):
            degraded = _duplicated_checkbox_bullet(subject, "NOSUCH-99")
    assert degraded == subject, (
        "with the `not_a_bullet` shim disarmed the helper was expected to"
        " return its subject UNCHANGED — that plain `return` is the shim, and"
        " without it `match.start(1)` raises `AttributeError` on a `None`"
        f" match. It returned {degraded[:60]!r} instead"
    )

    # --- `twin_not_read`: the flipped twin is no longer read as a bullet ---
    real_pattern = CHECKBOX_LINE
    ticked_only = re.compile(r"^- \[(x)\] \*\*([A-Z]+-\d+)\*\*", re.MULTILINE)
    for shim, replacement in (
        ("twin_not_read", ticked_only),
        ("twin_identical", _TickSpanPattern(real_pattern, "TEST-01")),
    ):
        limb = f"_duplicated_checkbox_bullet.{shim}"
        globals()["CHECKBOX_LINE"] = replacement
        try:
            try:
                produced = _duplicated_checkbox_bullet(subject, "TEST-01")
            except AssertionError as failure:
                assert f"[limb:{limb}]" in str(failure), (
                    f"the {shim!r} subject was refused by another limb:"
                    f" {failure}"
                )
            else:
                raise AssertionError(
                    f"the {shim!r} subject was ACCEPTED and the helper returned"
                    f" {produced[:60]!r}. A twin the channel cannot read as a"
                    " second bullet for this id is not a duplicate at all, and"
                    " `CONTROL 21` would then assert a duplicate-id refusal"
                    " over a document that carries no duplicate"
                )
            with neutered(limb):
                degraded = _duplicated_checkbox_bullet(subject, "TEST-01")
        finally:
            globals()["CHECKBOX_LINE"] = real_pattern
        assert degraded != subject, (
            f"with the {shim!r} shim disarmed the helper was expected to"
            " degrade SILENTLY into a document carrying the useless twin, and"
            " it returned its subject unchanged instead"
        )

    assert CHECKBOX_LINE is real_pattern, (
        "this control did not restore `CHECKBOX_LINE`, so every checkbox"
        " assertion after it in the session reads the document through a"
        " pattern it never agreed to"
    )


def test_control_37_a_derived_base_refuses_a_member_it_cannot_resolve() -> None:
    """CONTROL 37 — both of :func:`derived_base`'s refusals, watched by ID.

    Criterion 14's second half: *a member matching no tracked file makes that
    control REFUSE rather than silently skip.* The proof is that the refusal
    fires, and that it is the refusal this control names — asserted as the
    `[limb:…]` tag rather than as a phrase, because `CONTROL 5` spent the whole
    of Phase 21 green over the WRONG refusal on the strength of the substring
    ``"no rows"``, which two limbs' messages carry.

    **Both limbs, because both are registered.** Plan `21.1-07`'s coverage limb
    requires every id in :data:`LIMBS` to be claimed by a control, so a limb
    landed here without a subject that reaches it reddens `CONTROL 34` on the
    day it lands. That is criterion 12's dead-limb disposition, and shipping one
    inside the plan that closes criterion 14 would be this phase's own defect
    class arriving in its own repair.

    * `no_history` — a one-key misspelling, DERIVED through :func:`near_miss`
      from a member of a real constant rather than written down beside it, and
      required to be untracked before it is used. ``git log`` exits ZERO and
      prints nothing for it, which is precisely the silent skip.
    * `no_parent` — this repository's own ROOT commit, handed in through
      `last_touching`. Nothing in the tree puts a root commit at the head of a
      member's history, so without the parameter this limb would be
      unreachable; :func:`repository_root_commit` derives a real one.
    """
    root = repository_root_commit()
    assert re.fullmatch(r"[0-9a-f]{40}", root), (
        f"`git rev-list --max-parents=0 HEAD` produced {root!r} rather than a"
        " root commit, so the no-parent limb below has no subject and this"
        " control would report success over a refusal it never reached"
    )

    for member in (near_miss(FABRIC[0]), near_miss(TESTS_TREE[0])):
        assert not tracked_under((member,)), (
            f"the derived misspelling {member!r} names something `git` tracks,"
            " so it has history and cannot reach the no-history limb. The"
            " subject has drifted into a real path and this control would pass"
            " for a reason unrelated to what it claims to test"
        )
        try:
            produced = derived_base(member)
        except AssertionError as failure:
            assert "[limb:derived_base.no_history]" in str(failure), (
                f"the member {member!r} was refused by a DIFFERENT limb:"
                f" {failure}"
            )
        else:
            raise AssertionError(
                f"`derived_base({member!r})` returned {produced!r} instead of"
                " refusing. `git log` exits zero on a pathspec that matches"
                " nothing, so the member would be SKIPPED in silence — and a"
                " pathspec constant with an unchecked member is exactly the"
                " state `RR-1` and `RR-9` both describe"
            )

    try:
        produced = derived_base(TESTS_TREE[0], last_touching=root)
    except AssertionError as failure:
        assert "[limb:derived_base.no_parent]" in str(failure), (
            f"the root-commit subject was refused by a DIFFERENT limb: {failure}"
        )
    else:
        raise AssertionError(
            f"`derived_base(..., last_touching=<root commit>)` returned"
            f" {produced!r} instead of refusing. `git rev-parse` writes NOTHING"
            " to stdout when it fails, so the empty string would be handed on"
            " as a diff base — and `git diff ..HEAD` compares HEAD against"
            " nothing and prints nothing, which reads exactly like a clean tree"
        )


# ===========================================================================
# CONTROL_AIM — every control DECLARES what it vouches for, and CONTROL 34
# holds the declaration complete in both directions.
#
# `VAC-06`, criterion 13, plan `21.1-07`. This is the phase's GENERATOR, not
# another instance of it. Nothing in this module has ever proved that a
# CONTROL's mutation reaches the assertion it vouches for, which is why
# `CONTROL A`, `CONTROL 5` and `CONTROL 13` all shipped mis-aimed and why
# eighteen refusals sat unfalsified for a whole phase. Closing those without
# closing this would clear the board and leave the engine running.
#
# IT LANDS LATE, OVER A FROZEN SET, AND DOES NOT GROW. Every control this
# phase ships exists by the end of plan `21.1-06` (plus the two shim controls
# above). Landing the registry earlier would have frozen it over a partial set
# and forced an amendment in every later wave — and an artefact amended once
# per wave is an artefact nobody reads on the wave that matters. The
# forward-binding property comes from the COVERAGE limb rather than from the
# landing date: once this exists, a control added by any later phase without
# an entry reddens the run, which is the same shape `_refuse` already performs
# on refusal ids.
#
# THE ENTRY CARRIES A FROZENSET OF TARGETS, NEVER ONE TARGET, and two measured
# cases force it. `CONTROL C` is ONE test looping over TWO refusals —
# `fabric_diff`'s empty-base limb and its no-paths limb — and no other test
# exercises either; with one target per control one of the two is unclaimed
# and the coverage limb is red on landing. `CONTROL A` vouches for FOUR
# pathspec constants, and `RECON-08`'s shipped ledger cell repeats that claim
# verbatim; with one target the aim proof would establish that it reaches ONE
# of the four while it satisfies its entry and remains unproven for three.
# The consequence that makes the plural honest rather than decorative: the aim
# proofs quantify over the SET, one target at a time. A control that survives
# with one of its targets broken has not been proven for that target, whatever
# it proves for the others. `CONTROL C` is NOT split to fit the schema — its
# docstring calls its two subjects "the two other ways to compare nothing and
# call it clean", and narrowing a control to fit a registry is the move this
# phase exists to stop.
# ===========================================================================

#: The six aim kinds, as a frozen roster of NAMES (`D-21`).
#:
#: * `limb` — the control observes a NAMED refusal raised through
#:   :func:`_refuse`. Proof: neuter that one limb and the control must fail.
#: * `pathspec` — the control vouches for an emptiness assertion over a named
#:   pathspec constant. Proof: plan `21.1-08`, in the same plan as the
#:   `CONTROL A` and `CONTROL 13` re-aims and committed before them.
#: * `discriminator` — the control's subject must be ACCEPTED. Criterion 13's
#:   red-on-the-aimed-limb wording does not fit a control with no mutation and
#:   no limb; the obligation is INVERTED (see `CONTROL 36`).
#: * `guard` — the control holds one of the module's own guard mechanisms,
#:   which REPORTS its findings rather than raising a limb. Obligation
#:   inverted the same way: sabotage the mechanism and the control must fail
#:   (see `CONTROL 36b`).
#: * `shim` — the control holds a DEGRADATION SHIM: a limb reachable only
#:   under a sibling's neutering, existing so that degradation is SILENT
#:   rather than a crash (`D-IMPL-181`, criterion 15; `CONTROL 36c`).
#: * `meta` — the control is one of the aim-proving controls itself.
AIM_KINDS: frozenset[str] = frozenset(
    {"limb", "pathspec", "discriminator", "guard", "shim", "meta"}
)


class Aim(NamedTuple):
    """What one CONTROL vouches for, and how a meta-control can run it.

    `invoke` is a ZERO-ARGUMENT thunk that runs the control's own subject —
    most often the control function itself. **A meta-control that builds its
    own subject proves nothing about the control**, so where a control takes a
    fixture or a parameter the thunk supplies it rather than reimplementing
    what the control does.

    `invoke` is `None` for, and ONLY for, `meta` entries. That is not a
    convenience: `meta` entries are EXCLUDED from every invocation loop by
    design — a meta-control that invoked itself would recurse forever — and
    carrying no thunk makes the exclusion structural rather than a filter
    someone can drop. You cannot prove the prover forever, and the regress has
    to stop somewhere it can be seen stopping.

    `saboteur` maps ONE target name to a context manager that breaks it, for
    the kinds whose obligation is inverted. It is carried here, as DATA beside
    the aim, rather than as a chain of special cases inside the meta-controls.
    """

    kind: str
    targets: frozenset[str]
    invoke: Callable[[], None] | None = None
    saboteur: Callable[[str], contextlib.AbstractContextManager[None]] | None = None


@contextlib.contextmanager
def _substituted(name: str, replacement: object) -> Iterator[None]:
    """Replace this module's global `name` for the length of the block.

    A module global rather than an attribute patch because every checker here
    is called by NAME from the control bodies, so this is the substitution the
    control actually sees — the same reason `CONTROL 29` patches `_index` in
    this module's namespace rather than somewhere upstream.
    """
    original = globals()[name]
    globals()[name] = replacement
    try:
        yield
    finally:
        globals()[name] = original


def _substituting(**by_target: object) -> Callable[[str], contextlib.AbstractContextManager[None]]:
    """A saboteur that swaps each NAMED target for its stand-in.

    Keyed by target so an entry with two targets carries two stand-ins and the
    aim proofs can break exactly one at a time.
    """

    def _saboteur(target: str) -> contextlib.AbstractContextManager[None]:
        return _substituted(target, by_target[target])

    return _saboteur


def _returning(make_value: Callable[[], object]) -> Callable[..., object]:
    """A stand-in that ignores its arguments and returns a fresh `make_value()`.

    Fresh rather than shared, so a control that mutates what it was handed
    cannot poison the next invocation.
    """

    def _replacement(*_args: object, **_kwargs: object) -> object:
        return make_value()

    return _replacement


def _two_ends_only_cases() -> tuple[tuple[str, int], ...]:
    """`CONTROL 41`'s saboteur — the generator as it stood before `B-1`.

    First and last member of each constant, which is exactly the coverage the
    close panel proved insufficient. A control asserting completeness has to be
    watched refusing the incomplete case, or it is a check that cannot fail.
    """
    resolved = dict(asserted_pathspecs())
    return tuple(
        (name, index)
        for name in sorted(MULTI_MEMBER_PATHSPECS)
        for index in sorted({0, len(resolved[name]) - 1})
    )


def _every_bolded_run(status_cell: str) -> set[str]:
    """`cell_verdicts` with the vocabulary filter removed — `CONTROL 9b`'s saboteur.

    The reader `CONTROL 9b` exists to reject: it calls `DCD-02`'s second
    bolded phrase a second verdict, which is the shape that would make the
    one-verdict-per-cell gates red on the ledger's own honest rows.
    """
    return {run.group(1).strip() for run in BOLDED_RUN.finditer(status_cell)}


@contextlib.contextmanager
def _restore_written_after_the_yield(limb: str) -> Iterator[None]:
    """`neutered` with its restore moved OUT of the `finally` — `CONTROL 33`'s saboteur.

    Named in plan `21.1-06` task 3 and lifted here rather than re-derived. It
    leaks the limb when the block raises, which is precisely the case
    `CONTROL 33`'s first limb exists to catch; `_run_control` restores
    :data:`_NEUTERED` afterwards so the leak cannot escape the meta-control.
    """
    _require_registered(limb)
    already_off = limb in _NEUTERED
    _NEUTERED.add(limb)
    yield
    if not already_off:
        _NEUTERED.discard(limb)


def _with_monkeypatch(control: Callable[[pytest.MonkeyPatch], None]) -> Callable[[], None]:
    """A thunk for a control that takes the `monkeypatch` fixture.

    A fixture cannot be requested from inside another test, so the thunk opens
    the context itself. It runs the CONTROL, not a copy of it.
    """

    def _thunk() -> None:
        with pytest.MonkeyPatch.context() as patcher:
            control(patcher)

    return _thunk


#: Every CONTROL in this module, keyed by its test-function NAME, with the aim
#: it vouches for.
#:
#: **Keyed by a literal name rather than by `function.__name__`**, so that a
#: control renamed without its entry orphans the entry and `CONTROL 34` says
#: so. A derived key would satisfy the "every entry names a control that
#: exists" direction unconditionally, which is a check that cannot fail.
CONTROL_AIM: dict[str, Aim] = {
    # --- the diff machinery -------------------------------------------------
    "test_control_a_a_base_and_path_that_differ_produce_output": Aim(
        kind="pathspec",
        targets=frozenset({"FABRIC", "FENCE", "UAT_RECORDS", "PINNED_FILES"}),
        invoke=lambda: test_control_a_a_base_and_path_that_differ_produce_output(),
    ),
    "test_control_b_an_unresolvable_base_fails_loudly": Aim(
        kind="limb",
        targets=frozenset({"fabric_diff.nonzero_exit"}),
        invoke=lambda: test_control_b_an_unresolvable_base_fails_loudly(),
    ),
    "test_control_c_an_empty_path_list_fails_loudly": Aim(
        kind="limb",
        targets=frozenset({"fabric_diff.empty_base", "fabric_diff.empty_paths"}),
        invoke=lambda: test_control_c_an_empty_path_list_fails_loudly(),
    ),
    "test_control_37_a_derived_base_refuses_a_member_it_cannot_resolve": Aim(
        kind="limb",
        # BOTH ids in one target set. A single target would leave the other
        # limb unclaimed and redden `CONTROL 34`'s coverage limb, which is the
        # case the frozenset schema was written for.
        targets=frozenset({"derived_base.no_history", "derived_base.no_parent"}),
        invoke=lambda: test_control_37_a_derived_base_refuses_a_member_it_cannot_resolve(),
    ),
    "test_control_16_a_pathspec_that_names_nothing_is_refused": Aim(
        kind="limb",
        targets=frozenset({"fabric_diff.untracked_member"}),
        invoke=lambda: test_control_16_a_pathspec_that_names_nothing_is_refused(),
    ),
    "test_the_positive_control_a_real_pathspec_is_still_accepted": Aim(
        kind="discriminator",
        targets=frozenset({"tracked_under"}),
        invoke=lambda: test_the_positive_control_a_real_pathspec_is_still_accepted(),
        # `fabric_diff` is made to refuse EVERY pathspec by way of the module's
        # OWN untracked-member limb rather than by a fake `AssertionError`: a
        # `tracked_under` that reports nothing tracked is exactly the state
        # `CONTROL 16` refuses, and it produces a real `[limb:…]` refusal.
        saboteur=_substituting(tracked_under=_returning(list)),
    ),
    "test_control_41_the_multi_member_cases_reach_every_member": Aim(
        kind="guard",
        targets=frozenset({"multi_member_cases"}),
        invoke=lambda: test_control_41_the_multi_member_cases_reach_every_member(),
        # The stand-in is the generator as it shipped before `B-1` — first and
        # last member only. A completeness check that has never been watched
        # refusing an incomplete case is the shape this control was added to
        # close, one level up.
        saboteur=_substituting(multi_member_cases=_returning(_two_ends_only_cases)),
    ),
    "test_control_18_one_misspelled_member_of_a_multi_member_pathspec_is_refused": Aim(
        kind="limb",
        targets=frozenset({"fabric_diff.untracked_member"}),
        # The thunk runs EVERY case rather than a bound representative. A
        # representative satisfies the entry while the parametrization shrinks
        # underneath it, and after `B-1` widened the cases to every member it
        # would also be a second site holding the arity by hand.
        invoke=_control_18_over_every_case,
    ),
    # --- the two status channels -------------------------------------------
    "test_control_6_a_row_completed_in_one_channel_only_is_refused": Aim(
        kind="guard",
        targets=frozenset({"channel_disagreements"}),
        invoke=lambda: test_control_6_a_row_completed_in_one_channel_only_is_refused(),
        saboteur=_substituting(channel_disagreements=_returning(list)),
    ),
    "test_control_7_an_id_present_in_only_one_channel_is_refused": Aim(
        kind="guard",
        targets=frozenset({"channel_disagreements"}),
        invoke=lambda: test_control_7_an_id_present_in_only_one_channel_is_refused(),
        saboteur=_substituting(channel_disagreements=_returning(list)),
    ),
    "test_control_8_a_misspelled_table_header_refuses_rather_than_reporting_clean": Aim(
        kind="limb",
        targets=frozenset({"traceability_rows.header_absent"}),
        invoke=lambda: (
            test_control_8_a_misspelled_table_header_refuses_rather_than_reporting_clean()
        ),
    ),
    "test_control_9_a_verdict_outside_the_vocabulary_is_refused": Aim(
        kind="guard",
        targets=frozenset({"vocabulary_offenders"}),
        # Parametrized over three minted words; the thunk binds one.
        invoke=lambda: test_control_9_a_verdict_outside_the_vocabulary_is_refused("Done"),
        saboteur=_substituting(vocabulary_offenders=_returning(list)),
    ),
    "test_control_9b_the_second_bolded_phrase_in_dcd_02_is_not_a_second_verdict": Aim(
        kind="discriminator",
        targets=frozenset({"cell_verdicts"}),
        invoke=lambda: (
            test_control_9b_the_second_bolded_phrase_in_dcd_02_is_not_a_second_verdict()
        ),
        saboteur=_substituting(cell_verdicts=_every_bolded_run),
    ),
    "test_control_11_a_cell_with_two_verdict_tokens_is_refused": Aim(
        kind="guard",
        targets=frozenset({"doubled_verdicts"}),
        invoke=lambda: test_control_11_a_cell_with_two_verdict_tokens_is_refused(),
        saboteur=_substituting(doubled_verdicts=_returning(list)),
    ),
    "test_control_15_a_verdict_that_is_not_leading_is_not_read_as_the_verdict": Aim(
        kind="guard",
        targets=frozenset({"vocabulary_offenders"}),
        invoke=lambda: (
            test_control_15_a_verdict_that_is_not_leading_is_not_read_as_the_verdict()
        ),
        saboteur=_substituting(vocabulary_offenders=_returning(list)),
    ),
    "test_control_19_an_unbolded_lead_and_a_later_bolded_verdict_is_two_verdicts": Aim(
        kind="guard",
        targets=frozenset({"doubled_verdicts", "roster_rows_with_two_verdicts"}),
        invoke=lambda: (
            test_control_19_an_unbolded_lead_and_a_later_bolded_verdict_is_two_verdicts()
        ),
        saboteur=_substituting(
            doubled_verdicts=_returning(list),
            roster_rows_with_two_verdicts=_returning(list),
        ),
    ),
    # --- the citation checks ------------------------------------------------
    "test_control_1_an_ambiguous_basename_is_refused": Aim(
        kind="guard",
        targets=frozenset({"refuse_unresolvable"}),
        invoke=lambda: test_control_1_an_ambiguous_basename_is_refused(),
        saboteur=_substituting(refuse_unresolvable=_returning(list)),
    ),
    "test_control_2_a_unique_basename_is_refused_too": Aim(
        kind="guard",
        targets=frozenset({"refuse_unresolvable"}),
        invoke=lambda: test_control_2_a_unique_basename_is_refused_too(),
        saboteur=_substituting(refuse_unresolvable=_returning(list)),
    ),
    "test_control_3_a_path_that_does_not_exist_is_refused": Aim(
        kind="guard",
        targets=frozenset({"refuse_unresolvable"}),
        invoke=lambda: test_control_3_a_path_that_does_not_exist_is_refused(),
        saboteur=_substituting(refuse_unresolvable=_returning(list)),
    ),
    "test_control_4_a_symbol_citation_on_a_non_python_path_is_refused": Aim(
        kind="guard",
        targets=frozenset({"refuse_unresolvable"}),
        invoke=lambda: test_control_4_a_symbol_citation_on_a_non_python_path_is_refused(),
        saboteur=_substituting(refuse_unresolvable=_returning(list)),
    ),
    "test_control_4b_a_directory_path_is_refused": Aim(
        kind="guard",
        targets=frozenset({"refuse_unresolvable"}),
        invoke=lambda: test_control_4b_a_directory_path_is_refused(),
        saboteur=_substituting(refuse_unresolvable=_returning(list)),
    ),
    "test_control_5_a_table_with_no_rows_raises": Aim(
        kind="limb",
        targets=frozenset({"traceability_rows.zero_rows"}),
        invoke=lambda: test_control_5_a_table_with_no_rows_raises(),
    ),
    "test_control_5b_a_table_with_no_citations_raises": Aim(
        kind="limb",
        targets=frozenset({"refuse_unresolvable.zero_citations"}),
        invoke=lambda: test_control_5b_a_table_with_no_citations_raises(),
    ),
    "test_the_positive_control_a_real_citation_is_not_refused": Aim(
        kind="discriminator",
        targets=frozenset({"refuse_unresolvable"}),
        invoke=lambda: test_the_positive_control_a_real_citation_is_not_refused(),
        saboteur=_substituting(
            refuse_unresolvable=_returning(
                lambda: ["sabotage: every citation refused, compliant or not"]
            )
        ),
    ),
    "test_control_23_a_planning_document_can_be_cited_and_a_missing_one_cannot": Aim(
        kind="guard",
        targets=frozenset({"refuse_unresolvable", "citations_in_status_cells"}),
        invoke=lambda: (
            test_control_23_a_planning_document_can_be_cited_and_a_missing_one_cannot()
        ),
        saboteur=_substituting(
            refuse_unresolvable=_returning(list),
            citations_in_status_cells=_returning(list),
        ),
    ),
    "test_control_23b_the_subsumption_gate_compares_spans_not_path_strings": Aim(
        kind="limb",
        targets=frozenset({"uncovered_lint_citations.lint_matches_nothing"}),
        invoke=lambda: (
            test_control_23b_the_subsumption_gate_compares_spans_not_path_strings()
        ),
    ),
    "test_control_29_a_path_on_disk_but_absent_from_the_index_is_refused": Aim(
        kind="guard",
        targets=frozenset({"refuse_unresolvable"}),
        invoke=_with_monkeypatch(
            test_control_29_a_path_on_disk_but_absent_from_the_index_is_refused
        ),
        saboteur=_substituting(refuse_unresolvable=_returning(list)),
    ),
    # --- completeness -------------------------------------------------------
    "test_control_10_a_ledger_with_one_row_still_pending_is_refused": Aim(
        kind="guard",
        targets=frozenset({"unverdicted"}),
        invoke=lambda: test_control_10_a_ledger_with_one_row_still_pending_is_refused(),
        saboteur=_substituting(unverdicted=_returning(list)),
    ),
    "test_control_12_a_roster_id_absent_from_the_table_is_refused": Aim(
        kind="limb",
        targets=frozenset({"roster_verdicts.absent_id"}),
        invoke=lambda: test_control_12_a_roster_id_absent_from_the_table_is_refused(),
    ),
    "test_control_13_a_changed_tests_tree_would_be_detected": Aim(
        kind="pathspec",
        targets=frozenset({"TESTS_TREE"}),
        invoke=lambda: test_control_13_a_changed_tests_tree_would_be_detected(),
    ),
    "test_control_14_a_phase_own_row_returned_to_pending_is_refused": Aim(
        kind="guard",
        targets=frozenset({"unverdicted"}),
        invoke=lambda: test_control_14_a_phase_own_row_returned_to_pending_is_refused(),
        saboteur=_substituting(unverdicted=_returning(list)),
    ),
    "test_control_17_a_verdicted_row_stripped_of_its_citation_is_refused": Aim(
        kind="guard",
        targets=frozenset({"uncited_verdicts"}),
        invoke=lambda: (
            test_control_17_a_verdicted_row_stripped_of_its_citation_is_refused()
        ),
        saboteur=_substituting(uncited_verdicts=_returning(list)),
    ),
    "test_control_17b_a_not_built_row_may_cite_nothing": Aim(
        kind="discriminator",
        targets=frozenset({"CITATION_EXEMPT_VERDICTS"}),
        invoke=lambda: test_control_17b_a_not_built_row_may_cite_nothing(),
        saboteur=_substituting(CITATION_EXEMPT_VERDICTS=frozenset()),
    ),
    # --- the parsers and the control fixtures -------------------------------
    "test_control_20_a_duplicate_id_in_the_traceability_table_is_refused": Aim(
        kind="limb",
        targets=frozenset({"traceability_rows.duplicate_ids"}),
        invoke=lambda: (
            test_control_20_a_duplicate_id_in_the_traceability_table_is_refused()
        ),
    ),
    "test_control_21_a_duplicate_id_in_the_checkbox_channel_is_refused": Aim(
        kind="limb",
        targets=frozenset({"checkbox_channel.duplicate_ids"}),
        invoke=lambda: test_control_21_a_duplicate_id_in_the_checkbox_channel_is_refused(),
    ),
    "test_control_22_an_index_that_resolved_nothing_is_refused": Aim(
        kind="limb",
        targets=frozenset({"_index.anchor_unresolved"}),
        invoke=_with_monkeypatch(test_control_22_an_index_that_resolved_nothing_is_refused),
    ),
    "test_control_24_a_pathspec_git_rejects_refuses_rather_than_reading_empty": Aim(
        kind="limb",
        targets=frozenset({"tracked_under.nonzero_exit"}),
        invoke=lambda: (
            test_control_24_a_pathspec_git_rejects_refuses_rather_than_reading_empty()
        ),
    ),
    "test_control_25_a_traceability_row_that_is_not_three_cells_is_refused": Aim(
        kind="limb",
        targets=frozenset({"traceability_rows.cell_count"}),
        invoke=lambda: (
            test_control_25_a_traceability_row_that_is_not_three_cells_is_refused()
        ),
    ),
    "test_control_26_an_empty_checkbox_channel_is_refused": Aim(
        kind="limb",
        targets=frozenset({"checkbox_channel.empty"}),
        invoke=lambda: test_control_26_an_empty_checkbox_channel_is_refused(),
    ),
    "test_control_27_a_control_mutation_that_lands_nowhere_or_twice_is_refused": Aim(
        kind="limb",
        targets=frozenset({"_doctored.anchor_not_unique"}),
        invoke=lambda: (
            test_control_27_a_control_mutation_that_lands_nowhere_or_twice_is_refused()
        ),
    ),
    "test_control_27b_the_two_verdict_mutation_refuses_a_cell_it_cannot_mutate": Aim(
        kind="limb",
        targets=frozenset(
            {
                "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.cell_count",
                "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.verdict_unusable",
                "_cell_with_an_unbolded_lead_and_a_later_bolded_verdict.lead_not_bolded",
            }
        ),
        invoke=lambda: (
            test_control_27b_the_two_verdict_mutation_refuses_a_cell_it_cannot_mutate()
        ),
    ),
    "test_control_27c_the_duplicate_row_mutation_refuses_a_twin_that_is_not_one": Aim(
        kind="limb",
        targets=frozenset(
            {
                "_duplicated_table_row.cell_count",
                "_duplicated_table_row.phase_collision",
            }
        ),
        invoke=lambda: (
            test_control_27c_the_duplicate_row_mutation_refuses_a_twin_that_is_not_one()
        ),
    ),
    "test_control_27d_the_duplicate_row_twin_guard_fires_and_degrades_silently": Aim(
        kind="shim",
        targets=frozenset({"_duplicated_table_row.twin_identical"}),
        invoke=lambda: (
            test_control_27d_the_duplicate_row_twin_guard_fires_and_degrades_silently()
        ),
    ),
    "test_control_27e_the_duplicate_bullet_shims_fire_and_degrade_silently": Aim(
        kind="shim",
        targets=frozenset(
            {
                "_duplicated_checkbox_bullet.not_a_bullet",
                "_duplicated_checkbox_bullet.twin_identical",
                "_duplicated_checkbox_bullet.twin_not_read",
            }
        ),
        invoke=lambda: (
            test_control_27e_the_duplicate_bullet_shims_fire_and_degrade_silently()
        ),
    ),
    "test_control_28_a_table_anchor_that_is_absent_or_doubled_is_refused": Aim(
        kind="limb",
        targets=frozenset({"_table_line.not_unique"}),
        invoke=lambda: (
            test_control_28_a_table_anchor_that_is_absent_or_doubled_is_refused()
        ),
    ),
    "test_control_28b_a_checkbox_anchor_that_is_absent_or_doubled_is_refused": Aim(
        kind="limb",
        targets=frozenset({"_checkbox_line.not_unique"}),
        invoke=lambda: (
            test_control_28b_a_checkbox_anchor_that_is_absent_or_doubled_is_refused()
        ),
    ),
    "test_control_30_an_unresolvable_diff_base_refuses_rather_than_reading_clean": Aim(
        kind="limb",
        targets=frozenset({"base_ledger_text.nonzero_exit"}),
        invoke=lambda: (
            test_control_30_an_unresolvable_diff_base_refuses_rather_than_reading_clean()
        ),
    ),
    "test_control_31_a_per_row_rule_over_an_empty_roster_is_refused": Aim(
        kind="limb",
        targets=frozenset({"uncited_verdicts.empty_roster"}),
        invoke=lambda: test_control_31_a_per_row_rule_over_an_empty_roster_is_refused(),
    ),
    "test_control_31b_a_pathspec_member_too_short_to_misspell_is_refused": Aim(
        kind="limb",
        targets=frozenset({"near_miss.too_short_to_transpose"}),
        invoke=lambda: (
            test_control_31b_a_pathspec_member_too_short_to_misspell_is_refused()
        ),
    ),
    # --- this phase's own machinery -----------------------------------------
    "test_control_32_a_refusal_with_no_registered_identity_is_itself_refused": Aim(
        kind="guard",
        targets=frozenset({"_require_registered"}),
        invoke=lambda: (
            test_control_32_a_refusal_with_no_registered_identity_is_itself_refused()
        ),
        saboteur=_substituting(_require_registered=_returning(lambda: None)),
    ),
    "test_control_33_the_neutering_off_switch_cannot_leak_and_its_guard_can_fail": Aim(
        kind="guard",
        targets=frozenset({"neutered", "neutering_switch_offenders"}),
        invoke=lambda: (
            test_control_33_the_neutering_off_switch_cannot_leak_and_its_guard_can_fail()
        ),
        saboteur=_substituting(
            neutered=_restore_written_after_the_yield,
            neutering_switch_offenders=_returning(list),
        ),
    ),
    # --- the aim-proving controls themselves --------------------------------
    "test_control_34_every_control_declares_an_aim_and_every_limb_is_claimed": Aim(
        kind="meta",
        targets=frozenset(AIM_KINDS),
    ),
    "test_control_35_every_limb_aimed_control_reaches_the_limb_it_names": Aim(
        kind="meta",
        targets=frozenset({"limb"}),
    ),
    "test_control_36_every_discriminator_discriminates": Aim(
        kind="meta",
        targets=frozenset({"discriminator"}),
    ),
    "test_control_36b_every_guard_aimed_control_reaches_the_guard_it_holds": Aim(
        kind="meta",
        targets=frozenset({"guard"}),
    ),
    "test_control_36c_every_shim_keeps_its_degradation_silent": Aim(
        kind="meta",
        targets=frozenset({"shim"}),
    ),
    "test_control_38_every_pathspec_aimed_control_exercises_the_constant_it_names": Aim(
        kind="meta",
        targets=frozenset({"pathspec"}),
    ),
    # --- `D-21` made standing ----------------------------------------------
    "test_control_39_the_count_sweep_finds_a_planted_count": Aim(
        kind="guard",
        targets=frozenset({"carried_counts", "module_source"}),
        invoke=lambda: test_control_39_the_count_sweep_finds_a_planted_count(),
        # Two stand-ins, because the two targets fail differently and the
        # aim proof breaks exactly one at a time. A `carried_counts` that
        # finds nothing is the sweep gone blind; a `module_source` that
        # returns a line the sweep matches is the sweep pointed at a
        # subject that is not this module, and `CONTROL 39` asserts the
        # real source CLEAN before it plants anything, so it notices.
        saboteur=_substituting(
            carried_counts=_returning(list),
            module_source=_returning(
                lambda: "assert len(rows) " + "=" + "= " + str(149) + "\n"
            ),
        ),
    ),
    "test_control_40_the_count_sweep_refuses_a_subject_it_cannot_sweep": Aim(
        kind="limb",
        targets=frozenset(
            {
                "carried_counts.empty_roster",
                "carried_counts.empty_source",
                "carried_counts.unbound_roster",
            }
        ),
        invoke=lambda: test_control_40_the_count_sweep_refuses_a_subject_it_cannot_sweep(),
    ),
}

#: Every control in this module, by NAME — the roster the enumeration below is
#: frozen against.
#:
#: **Why a roster as well as an enumeration.** :func:`enumerated_controls`
#: reads the module's globals with a name predicate, and a predicate that
#: quietly stops matching a control satisfies coverage VACUOUSLY for that
#: control while both directions of `CONTROL 34` still pass. The four positive
#: twins are the standing proof that this is not hypothetical: they are named
#: `test_the_positive_control_…`, outside the `test_control_` convention, and
#: a predicate written to that convention alone drops them in silence.
#:
#: Named ids, set equality, no count (`D-21`).
CONTROLS: frozenset[str] = frozenset(
    {
        "test_control_a_a_base_and_path_that_differ_produce_output",
        "test_control_b_an_unresolvable_base_fails_loudly",
        "test_control_c_an_empty_path_list_fails_loudly",
        "test_control_16_a_pathspec_that_names_nothing_is_refused",
        "test_control_41_the_multi_member_cases_reach_every_member",
        "test_control_37_a_derived_base_refuses_a_member_it_cannot_resolve",
        "test_the_positive_control_a_real_pathspec_is_still_accepted",
        "test_control_18_one_misspelled_member_of_a_multi_member_pathspec_is_refused",
        "test_control_6_a_row_completed_in_one_channel_only_is_refused",
        "test_control_7_an_id_present_in_only_one_channel_is_refused",
        "test_control_8_a_misspelled_table_header_refuses_rather_than_reporting_clean",
        "test_control_9_a_verdict_outside_the_vocabulary_is_refused",
        "test_control_9b_the_second_bolded_phrase_in_dcd_02_is_not_a_second_verdict",
        "test_control_11_a_cell_with_two_verdict_tokens_is_refused",
        "test_control_15_a_verdict_that_is_not_leading_is_not_read_as_the_verdict",
        "test_control_19_an_unbolded_lead_and_a_later_bolded_verdict_is_two_verdicts",
        "test_control_1_an_ambiguous_basename_is_refused",
        "test_control_2_a_unique_basename_is_refused_too",
        "test_control_3_a_path_that_does_not_exist_is_refused",
        "test_control_4_a_symbol_citation_on_a_non_python_path_is_refused",
        "test_control_4b_a_directory_path_is_refused",
        "test_control_5_a_table_with_no_rows_raises",
        "test_control_5b_a_table_with_no_citations_raises",
        "test_the_positive_control_a_real_citation_is_not_refused",
        "test_control_23_a_planning_document_can_be_cited_and_a_missing_one_cannot",
        "test_control_23b_the_subsumption_gate_compares_spans_not_path_strings",
        "test_control_29_a_path_on_disk_but_absent_from_the_index_is_refused",
        "test_control_10_a_ledger_with_one_row_still_pending_is_refused",
        "test_control_12_a_roster_id_absent_from_the_table_is_refused",
        "test_control_13_a_changed_tests_tree_would_be_detected",
        "test_control_14_a_phase_own_row_returned_to_pending_is_refused",
        "test_control_17_a_verdicted_row_stripped_of_its_citation_is_refused",
        "test_control_17b_a_not_built_row_may_cite_nothing",
        "test_control_20_a_duplicate_id_in_the_traceability_table_is_refused",
        "test_control_21_a_duplicate_id_in_the_checkbox_channel_is_refused",
        "test_control_22_an_index_that_resolved_nothing_is_refused",
        "test_control_24_a_pathspec_git_rejects_refuses_rather_than_reading_empty",
        "test_control_25_a_traceability_row_that_is_not_three_cells_is_refused",
        "test_control_26_an_empty_checkbox_channel_is_refused",
        "test_control_27_a_control_mutation_that_lands_nowhere_or_twice_is_refused",
        "test_control_27b_the_two_verdict_mutation_refuses_a_cell_it_cannot_mutate",
        "test_control_27c_the_duplicate_row_mutation_refuses_a_twin_that_is_not_one",
        "test_control_27d_the_duplicate_row_twin_guard_fires_and_degrades_silently",
        "test_control_27e_the_duplicate_bullet_shims_fire_and_degrade_silently",
        "test_control_28_a_table_anchor_that_is_absent_or_doubled_is_refused",
        "test_control_28b_a_checkbox_anchor_that_is_absent_or_doubled_is_refused",
        "test_control_30_an_unresolvable_diff_base_refuses_rather_than_reading_clean",
        "test_control_31_a_per_row_rule_over_an_empty_roster_is_refused",
        "test_control_31b_a_pathspec_member_too_short_to_misspell_is_refused",
        "test_control_32_a_refusal_with_no_registered_identity_is_itself_refused",
        "test_control_33_the_neutering_off_switch_cannot_leak_and_its_guard_can_fail",
        "test_control_34_every_control_declares_an_aim_and_every_limb_is_claimed",
        "test_control_35_every_limb_aimed_control_reaches_the_limb_it_names",
        "test_control_36_every_discriminator_discriminates",
        "test_control_36b_every_guard_aimed_control_reaches_the_guard_it_holds",
        "test_control_36c_every_shim_keeps_its_degradation_silent",
        "test_control_38_every_pathspec_aimed_control_exercises_the_constant_it_names",
        "test_control_39_the_count_sweep_finds_a_planted_count",
        "test_control_40_the_count_sweep_refuses_a_subject_it_cannot_sweep",
    }
)


def enumerated_controls() -> dict[str, Callable[..., None]]:
    """Every CONTROL in this module, read from its own globals.

    **The predicate is `_control_` anywhere in the name, NOT the
    `test_control_` prefix.** The four positive twins are named
    `test_the_positive_control_…`; a predicate written to the prefix alone
    drops all four in silence, and each of them is the discriminator half of a
    pair whose negative half the prefix DOES match — so the enumeration would
    look complete while covering only one side of four discriminations.

    Enumerated rather than transcribed so that a control added by a later
    phase reddens :func:`test_control_34_every_control_declares_an_aim_and_every_limb_is_claimed`
    on its first run, and frozen against :data:`CONTROLS` so that a predicate
    which stops matching a control cannot satisfy coverage vacuously for it.
    """
    return {
        name: value
        for name, value in globals().items()
        if name.startswith("test_") and "_control_" in name and callable(value)
    }


def test_control_34_every_control_declares_an_aim_and_every_limb_is_claimed() -> None:
    """CONTROL 34 — the registry is complete, in BOTH directions, by NAME.

    Six limbs, none of them a count (`D-21`):

    1. the enumeration equals :data:`CONTROLS` — a control the predicate stops
       matching is named here rather than silently exempted;
    2. every enumerated control has a :data:`CONTROL_AIM` entry, and every
       entry names a control that exists. **A control that ships without an
       entry fails the run**, which is the forward-binding clause: this is why
       the registry does not have to be re-visited by a later phase to keep
       working;
    3. every kind is one of :data:`AIM_KINDS`, and every entry declares at
       least one target — an entry with an empty target set claims nothing and
       would satisfy the union below for free;
    4. every limb id in :data:`LIMBS` is claimed by the UNION of the `limb`
       and `shim` target sets, and every id in those sets is in `LIMBS`.
       **`shim` is quantified over exactly as every other kind — there is no
       exempt roster** (`D-IMPL-181`; Dave rejected one because it *"excuses
       them without proving they work"*);
    5. every `pathspec` target names a constant :func:`asserted_pathspecs`
       resolves, and every `discriminator`, `guard` and `shim` entry carries a
       target this module actually defines;
    6. every `discriminator` and `guard` entry carries a SABOTEUR and no
       other kind does — a control whose obligation is inverted has no limb to
       neuter, and the thing that breaks its subject is carried as data beside
       the aim;
    7. `meta` entries carry NO thunk and every other entry carries one. That
       is what makes the invocation exclusion structural rather than a filter
       someone can drop — see :class:`Aim`.

    **Not satisfiable by a partial or an empty roster.** The union is compared
    to `LIMBS` by set equality in both directions, the enumeration to
    `CONTROLS` the same way, and both are required to be non-empty — so a
    registry emptied by a bad edit reddens rather than passing over nothing,
    which is the vacuity this whole module exists to detect arriving at the
    boundary of the check that detects it.
    """
    enumerated = enumerated_controls()
    assert enumerated, (
        "the control enumeration found NOTHING, so every limb below is"
        " quantified over the empty set and this check reports green over a"
        " module with no controls in it at all"
    )

    unmatched = sorted(CONTROLS - set(enumerated))
    unrostered = sorted(set(enumerated) - CONTROLS)
    assert not unmatched and not unrostered, (
        "the enumeration and the frozen `CONTROLS` roster disagree."
        f"\n  in `CONTROLS`, not found by the predicate: {unmatched}"
        f"\n  found by the predicate, not in `CONTROLS`: {unrostered}"
        "\nA control the predicate stops matching satisfies every coverage"
        " limb below VACUOUSLY for that control while both directions still"
        " pass — which is why the roster exists beside the enumeration"
    )

    unregistered = sorted(set(enumerated) - set(CONTROL_AIM))
    orphaned = sorted(set(CONTROL_AIM) - set(enumerated))
    assert not unregistered and not orphaned, (
        "`CONTROL_AIM` does not name exactly the controls this module has."
        f"\n  controls with no registry entry: {unregistered}"
        f"\n  registry entries naming no control: {orphaned}"
        "\nA control that ships without an entry is a control nothing proves"
        " is aimed at anything, which is how `CONTROL A`, `CONTROL 5` and"
        " `CONTROL 13` all shipped mis-aimed"
    )

    bad_kinds = sorted(
        f"{name} -> {aim.kind!r}"
        for name, aim in CONTROL_AIM.items()
        if aim.kind not in AIM_KINDS
    )
    assert not bad_kinds, (
        f"these entries declare a kind outside {sorted(AIM_KINDS)}:"
        f" {bad_kinds}. A kind with no proof loop behind it is a filing"
        " cabinet, not a disposition"
    )
    aimless = sorted(name for name, aim in CONTROL_AIM.items() if not aim.targets)
    assert not aimless, (
        f"these entries declare no target at all: {aimless}. An empty target"
        " set claims nothing, satisfies every union below for free, and leaves"
        " the control it belongs to registered and aim-unproven"
    )

    claimed: set[str] = set()
    for aim in CONTROL_AIM.values():
        if aim.kind in {"limb", "shim"}:
            claimed |= aim.targets
    unwatched = sorted(LIMBS - claimed)
    unregistered_limbs = sorted(claimed - LIMBS)
    assert not unwatched and not unregistered_limbs, (
        "the `limb` and `shim` aims do not account for `LIMBS`, id for id."
        f"\n  registered limbs no control claims: {unwatched}"
        f"\n  claimed ids that are not registered limbs: {unregistered_limbs}"
        "\nAn unclaimed limb is a refusal nothing is proven to reach; a"
        " claimed id that is not a limb is a control vouching for a branch"
        " that does not exist"
    )

    pathspec_names = {name for name, _spec in asserted_pathspecs()}
    module = globals()
    misdirected: list[str] = []
    for name, aim in CONTROL_AIM.items():
        for target in sorted(aim.targets):
            if aim.kind == "pathspec" and target not in pathspec_names:
                misdirected.append(
                    f"{name} -> {target!r} is not a constant"
                    " `asserted_pathspecs()` resolves"
                )
            if aim.kind in {"discriminator", "guard"} and target not in module:
                misdirected.append(
                    f"{name} -> {target!r} is not defined in this module"
                )
            if aim.kind == "meta" and target not in AIM_KINDS:
                misdirected.append(f"{name} -> {target!r} is not an aim kind")
    assert not misdirected, (
        "these aims name a target that does not exist:\n"
        + "\n".join(misdirected)
        + "\nA control vouching for a subject the module does not have is"
        " vouching for nothing, and its aim proof would be about a name"
    )

    saboteurless = sorted(
        f"{name} ({aim.kind})"
        for name, aim in CONTROL_AIM.items()
        if aim.kind in {"discriminator", "guard"} and aim.saboteur is None
    )
    over_saboteured = sorted(
        f"{name} ({aim.kind})"
        for name, aim in CONTROL_AIM.items()
        if aim.kind not in {"discriminator", "guard"} and aim.saboteur is not None
    )
    assert not saboteurless and not over_saboteured, (
        f"inverted-obligation entries with no saboteur: {saboteurless}"
        f"\nentries carrying a saboteur that is never used: {over_saboteured}"
        "\nA `discriminator` or a `guard` cannot be proven by neutering a limb"
        " — it has no limb — so the thing that breaks its subject is carried"
        " HERE, as data beside the aim, rather than as a chain of special"
        " cases inside the meta-controls. `limb` and `shim` aims break their"
        " subject with `neutered()` and need none"
    )

    thunkless = sorted(
        name
        for name, aim in CONTROL_AIM.items()
        if aim.kind != "meta" and aim.invoke is None
    )
    thunked_meta = sorted(
        name
        for name, aim in CONTROL_AIM.items()
        if aim.kind == "meta" and aim.invoke is not None
    )
    assert not thunkless and not thunked_meta, (
        f"entries with no invocation thunk: {thunkless}"
        f"\nmeta entries carrying one: {thunked_meta}"
        "\n`meta` entries are EXCLUDED from every invocation loop by design —"
        " a meta-control that invoked itself would recurse forever — and"
        " carrying no thunk is what makes that exclusion structural. Every"
        " other kind needs one, because a meta-control that builds its own"
        " subject proves nothing about the control"
    )


# ===========================================================================
# CONTROL 35 — every `limb`-aimed control is PROVEN to reach the limb it names.
#
# Criterion 13's own words made mechanical: red on the aimed limb, green when
# that limb is intact. It is the check that would have caught `CONTROL 5` in
# wave 1 — and the `CONTROL 5` re-point sabotage in this plan's SUMMARY
# reproduces that historical defect and watches this control name it.
# ===========================================================================


def _run_control(aim: Aim) -> Exception | None:
    """Invoke a control through its thunk; return what it raised, or `None`.

    **It restores :data:`_NEUTERED` on the way out, unconditionally.** A
    sabotaged control can leak the switch — `CONTROL 32` under its own
    saboteur calls `neutered(...).__enter__()` with no matching `__exit__`,
    deliberately — and a leaked limb is disarmed for every test that runs
    afterwards in the session. That is the phase's own thesis arriving inside
    the machinery built to close it, and the autouse fixture would report it
    against whichever meta-control happened to be last.

    :class:`Exception` and not :class:`BaseException`: a `KeyboardInterrupt`
    is not a control failing.
    """
    if aim.invoke is None:  # pragma: no cover - `CONTROL 34` holds this
        raise ValueError("a `meta` entry has no thunk and is never invoked")
    snapshot = set(_NEUTERED)
    try:
        aim.invoke()
    except Exception as failure:
        return failure
    else:
        return None
    finally:
        _NEUTERED.clear()
        _NEUTERED.update(snapshot)


#: The `(control, limb)` pairs whose neutered RED is a CASCADE rather than the
#: control's own `AssertionError` — a frozen roster of NAMED pairs (`D-21`).
#:
#: **Why this is asserted rather than tolerated.** Neutering a limb makes
#: control flow continue past a branch that was protecting later code, so some
#: controls go red with something other than an `AssertionError`. That still
#: establishes reachability, and the paired green-when-intact run bounds it.
#: But *a crash and a caught defect are indistinguishable to a coverage
#: assertion* — the whole reason `D-IMPL-181` exists — so every cascade is
#: NAMED here and the set of observed cascades is compared to this roster id
#: for id. A control that starts crashing where it used to assert reddens the
#: run and gets read by a human, rather than quietly counting as coverage.
#:
#: **It is EMPTY today, and that is a measurement rather than an oversight.**
#: Swept across every `limb` target in :data:`CONTROL_AIM`, one limb neutered
#: at a time, every single red was the control's own `AssertionError` —
#: including `traceability_rows.header_absent`, which plan `21.1-07` predicted
#: would cascade. It does not, because plan `21.1-05` reshaped six branches to
#: degrade to SILENCE rather than crash for exactly this reason. That
#: reshaping is what makes `CONTROL 34`, `35`, `36b` and `36c` trustworthy at
#: all, and this empty roster is the standing evidence that it still holds.
CASCADING_REDS: frozenset[tuple[str, str]] = frozenset()


def test_control_35_every_limb_aimed_control_reaches_the_limb_it_names() -> None:
    """CONTROL 35 — neuter the limb a control names, and the control must fail.

    For every `limb` entry and for EACH target in its set INDEPENDENTLY, not
    per entry: `CONTROL C` covers two limbs and a proof that it reaches one of
    them is not a proof that it reaches the other. `CONTROL 27b` covers three
    and `CONTROL 27c` two, for the same reason.

    **Three properties, and the third is the one this wave was commissioned
    for.**

    1. with every limb intact the control PASSES — otherwise its red below
       says nothing, because a control that is red anyway is red under any
       mutation;
    2. with exactly ONE of its named limbs neutered the control does NOT pass.
       Any exception counts; the property under test is that the control does
       not report success over a guard that stopped guarding;
    3. the RED is either the control's own `AssertionError` or a NAMED
       cascade in :data:`CASCADING_REDS`. **A crash is not coverage** — if
       neutering a limb made the module explode, this loop would conclude
       "the control reaches that limb" when all it reached was the wreckage.

    `meta` entries are excluded because they carry no thunk (see :class:`Aim`),
    and `pathspec` aims are PROVEN in plan `21.1-08`, in the same plan as the
    `CONTROL A` and `CONTROL 13` re-aims and committed before them, so that the
    pathspec prover is observed RED naming exactly the two controls this
    project shipped mis-aimed.
    """
    failures: list[str] = []
    cascades: set[tuple[str, str]] = set()
    proven: set[str] = set()

    for name in sorted(CONTROL_AIM):
        aim = CONTROL_AIM[name]
        if aim.kind != "limb":
            continue
        intact = _run_control(aim)
        if intact is not None:
            failures.append(
                f"{name} does not pass with every limb INTACT — it raised"
                f" {type(intact).__name__}: {intact}. A control that is red"
                " anyway is red under any mutation, so nothing below about it"
                " would mean anything"
            )
            continue
        for target in sorted(aim.targets):
            with neutered(target):
                raised = _run_control(aim)
            if raised is None:
                failures.append(
                    f"{name} PASSED with {target!r} neutered. It does not"
                    " reach the limb it vouches for: the refusal it watches"
                    " was turned OFF and the control reported success anyway,"
                    " which is exactly the state `CONTROL 5` shipped in for"
                    " the whole of Phase 21"
                )
                continue
            proven.add(target)
            if not isinstance(raised, AssertionError):
                cascades.add((name, target))

    unexpected = sorted(cascades - CASCADING_REDS)
    stale = sorted(CASCADING_REDS - cascades)
    assert not failures and not unexpected and not stale, (
        "\n".join(failures)
        + ("\n" if failures else "")
        + f"cascading reds observed but not in `CASCADING_REDS`: {unexpected}"
        f"\ncascades in `CASCADING_REDS` that did not happen: {stale}"
        + "\nA red that is not the control's own `AssertionError` is a CRASH,"
        " and a crash is indistinguishable from a caught defect to every"
        " coverage assertion in this module. Each one is named so a human"
        " reads it rather than counting it as coverage"
    )
    assert proven, (
        "no limb aim was proven at all, so this control passed over the empty"
        " set — the vacuity it exists to detect, arriving inside itself"
    )


# ===========================================================================
# CONTROL 36, 36b and 36c — the three INVERTED obligations.
#
# Criterion 13 says every control's "mutation is watched RED on the aimed limb
# and GREEN when that limb is intact". Three families of control in this
# module have no mutation and no limb, and reading the criterion literally
# either excludes them — which is the narrowing-a-claim-to-fit-a-weak-control
# move this phase exists to stop — or is unsatisfiable:
#
# * the four POSITIVE TWINS, whose job is that a compliant subject is
#   ACCEPTED. "Red on everything is not a check" is their whole purpose and
#   each of their docstrings says so;
# * the controls over guards that REPORT their findings rather than raising a
#   limb — `channel_disagreements`, `unverdicted`, `refuse_unresolvable` and
#   the rest — including `CONTROL 32` and `CONTROL 33`, which hold the two
#   mechanisms whose silent failure makes every other control here vacuous;
# * the four DEGRADATION SHIMS (`D-IMPL-181`, criterion 15).
#
# THE READING, recorded for Dave at the close. Each of the three is proven by
# breaking what it vouches for and requiring the control to FAIL: a
# discriminator that stays green while its subject predicate refuses
# everything is discriminating nothing; a control over a guard that stays
# green while the guard reports nothing is holding nothing; and a shim whose
# refusal can be turned off without a control noticing is not being kept
# silent by anything. Same obligation as `CONTROL 35`, inverted subject.
#
# EACH RED IS REQUIRED TO BE THE CONTROL'S OWN `AssertionError`. A crash and a
# caught defect are indistinguishable to a coverage assertion, and building an
# instrument that cannot tell them apart is what this whole wave exists to
# avoid.
# ===========================================================================


def _aim_proof(
    kind: str,
    broken: Callable[[Aim, str], contextlib.AbstractContextManager[None]],
    verb: str,
) -> tuple[list[str], set[tuple[str, str]]]:
    """Run one inverted-obligation loop, returning `(failures, proven pairs)`.

    Shared by `CONTROL 36`, `36b` and `36c` because the three differ in one
    thing only — HOW the subject is broken — and three hand-copied loops is
    the two-divergent-inline-copies shape plan `21.1-02` was written to end.
    """
    failures: list[str] = []
    proven: set[tuple[str, str]] = set()
    for name in sorted(CONTROL_AIM):
        aim = CONTROL_AIM[name]
        if aim.kind != kind:
            continue
        intact = _run_control(aim)
        if intact is not None:
            failures.append(
                f"{name} does not pass with its subject INTACT — it raised"
                f" {type(intact).__name__}: {intact}. A control that is red"
                " anyway is red under any sabotage"
            )
            continue
        for target in sorted(aim.targets):
            with broken(aim, target):
                raised = _run_control(aim)
            if raised is None:
                failures.append(
                    f"{name} PASSED with {target!r} {verb}. It does not reach"
                    " what it vouches for: the subject was broken and the"
                    " control reported success anyway"
                )
            elif not isinstance(raised, AssertionError):
                failures.append(
                    f"{name} went red with {target!r} {verb}, but it CRASHED"
                    f" — {type(raised).__name__}: {raised}. A crash is not"
                    " coverage: it is indistinguishable from a caught defect"
                    " to every assertion in this module, which is the"
                    " instrument this wave exists NOT to build"
                )
            else:
                proven.add((name, target))
    return failures, proven


def test_control_36_every_discriminator_discriminates() -> None:
    """CONTROL 36 — a positive twin whose subject predicate refuses everything.

    Four entries, each with a saboteur carried in its registry entry:

    * the positive pathspec control — `tracked_under` reports NOTHING tracked,
      so `fabric_diff` refuses every pathspec through its own
      `fabric_diff.untracked_member` limb. Sabotaging the predicate `CONTROL
      16` depends on, rather than raising a manufactured `AssertionError`,
      keeps the refusal a REAL one carrying a real limb id;
    * `CONTROL 9b` — `cell_verdicts` returns every bolded run whether or not
      it is a vocabulary word, which is precisely the reader `CONTROL 9b`
      exists to reject: it calls `DCD-02`'s second bolded phrase a second
      verdict;
    * `CONTROL 17b` — :data:`CITATION_EXEMPT_VERDICTS` is emptied, so a
      `Not built` row is required to cite a file it cannot have;
    * the positive citation control — `refuse_unresolvable` returns an
      offender for every citation, compliant or not.

    Without this, a checker rewritten to refuse EVERYTHING would satisfy every
    negative control in this module and be caught by nothing. Red on
    everything is not a check.
    """
    failures, proven = _aim_proof(
        "discriminator",
        lambda aim, target: aim.saboteur(target),  # type: ignore[misc]
        "forced to refuse everything",
    )
    assert not failures, "\n".join(failures)
    assert proven, (
        "no discriminator was proven at all, so this control passed over the"
        " empty set"
    )


def test_control_36b_every_guard_aimed_control_reaches_the_guard_it_holds() -> None:
    """CONTROL 36b — sabotage the guarded mechanism; the control must fail.

    **The `guard` kind is real and `CONTROL 32`/`33` take it, not `meta`.**
    A `meta` entry is excluded from every invocation loop by design, and for
    the aim-proving controls that exclusion is legitimate — you cannot prove
    the prover forever, and the regress has to stop somewhere it can be seen
    stopping. `CONTROL 32` and `CONTROL 33` are not provers. They are ordinary
    controls over two ordinary in-module guards, and filing them under `meta`
    would have left the two controls holding the two mechanisms whose silent
    failure makes every other control here vacuous registered, enumerated and
    AIM-UNPROVEN. That is not stopping a regress; it is dodging the taxonomy.
    Both saboteurs are lifted from their `SABOTEUR:` docstring lines rather
    than re-derived.

    **A LETTER SUFFIX rather than the next free number**, on the module's own
    convention for a control landing beside its sibling — `4b`, `5b`, `9b`,
    `17b`, `23b`, `27b`..`27e`, `28b` and `31b` all did. This is the
    guard-kind twin of `CONTROL 36`'s discriminator loop: same inverted
    obligation, different subject. Numbers 37 and 38 belong to plan `21.1-08`
    and are not renumbered around it.
    """
    failures, proven = _aim_proof(
        "guard",
        lambda aim, target: aim.saboteur(target),  # type: ignore[misc]
        "sabotaged",
    )
    assert not failures, "\n".join(failures)
    assert proven, (
        "no guard aim was proven at all, so this control passed over the empty"
        " set"
    )


def test_control_36c_every_shim_keeps_its_degradation_silent() -> None:
    """CONTROL 36c — the shims, held to criterion 15's inverted obligation.

    `D-IMPL-181`. A shim is a limb reachable ONLY with a sibling neutered,
    existing so that the degradation is SILENT rather than an `AttributeError`
    or an `IndexError`. Its control proves both halves — the shim fires by
    name with the sibling disarmed, and the helper still returns rather than
    crashing when the shim is disarmed on top — and this loop proves the
    control is aimed at it: **disarm the shim and the control goes red, with
    its own `AssertionError` rather than with the wreckage.**

    That last clause is the point of the whole kind. If disarming a shim made
    the module explode, `CONTROL 34`'s coverage limb and `CONTROL 35`'s aim
    proof would both conclude "the control reaches that limb" when all either
    reached was the crash — the instrument this wave was commissioned to
    destroy, rebuilt inside the wave that destroys it.

    **Coverage quantifies over `shim` exactly as over every other kind and
    there is no exempt roster**, which Dave rejected explicitly: an exempt
    roster *"excuses them without proving they work"*. The four ids are
    `_duplicated_table_row.twin_identical`,
    `_duplicated_checkbox_bullet.not_a_bullet`,
    `_duplicated_checkbox_bullet.twin_identical` and
    `_duplicated_checkbox_bullet.twin_not_read`.
    """
    failures, proven = _aim_proof(
        "shim",
        lambda _aim, target: neutered(target),
        "disarmed",
    )
    assert not failures, "\n".join(failures)
    assert proven, (
        "no shim aim was proven at all, so this control passed over the empty"
        " set — and the four limbs `D-IMPL-181` ruled on would be back to"
        " being excused rather than proven"
    )


# ===========================================================================
# CONTROL 38 — every `pathspec`-aimed control EXERCISES the constant it names.
#
# `VAC-06`, criterion 13's pathspec half, plan `21.1-08`. The last of the six
# aim kinds to get a proof, and it lands BEFORE the two repairs it forces so
# that it is observed RED naming exactly the two controls this project shipped
# mis-aimed for a whole phase.
#
# THE REASONING IS THE MODULE'S OWN: if a control genuinely exercises a
# constant, corrupting that constant must break it. `CONTROL 13` diffs
# `CHANGED_TREE` while vouching for an assertion over `TESTS_TREE`, so
# corrupting `TESTS_TREE` does nothing to it — which is precisely the defect,
# expressed as a test rather than as a paragraph. `CONTROL A` is the same shape
# four times over.
#
# PER CONSTANT, NEVER PER ENTRY. `CONTROL A`'s docstring calls it "the
# non-vacuity proof for all four emptiness assertions above at once" and
# `RECON-08`'s shipped ledger cell repeats that claim verbatim. A proof that it
# reaches ONE of the four while its entry counts as satisfied is `RR-9` living
# inside the meta-control built to end `RR-9`. Three-quarters-proven is not
# proven.
#
# THIS ONLY WORKS BECAUSE THE CONTROLS READ THEIR CONSTANTS THROUGH THE MODULE
# GLOBAL AT CALL TIME. :func:`asserted_pathspecs` is a function for exactly
# that reason and its docstring says so. A control carrying `("tests/",)` in
# its body does not read the constant at all, the substitution below is
# invisible to it, and this check would pass over a control it proves nothing
# about.
# ===========================================================================


def test_control_38_every_pathspec_aimed_control_exercises_the_constant_it_names() -> (
    None
):
    """CONTROL 38 — misspell ONE named pathspec constant; the control must fail.

    For every `pathspec` entry in :data:`CONTROL_AIM` and for EACH constant in
    its target set INDEPENDENTLY: replace that one module global with a tuple
    of near-miss misspellings of its own members, invoke the control through
    its registry thunk, and require it NOT to pass. Then restore and require it
    to pass.

    **The misspellings are DERIVED through :func:`near_miss` from the members
    the constant actually holds**, never written down — a literal typo table is
    one edit away from naming a member that no longer exists, and a control
    whose subject has drifted out of its own constant is this phase's defect
    class by a third route. Each derived misspelling is required to be untracked
    before it is used, so a transposition that happened to name a real file is
    caught here rather than making the proof vacuous.

    **The red must be the control's own `AssertionError`.** A crash is not
    coverage: it is indistinguishable from a caught defect to every coverage
    assertion in this module, which is the instrument this phase exists NOT to
    build. Same requirement `CONTROL 36`, `36b` and `36c` carry.

    The shared :func:`_aim_proof` loop is reused rather than hand-copied for the
    fourth time — the three-divergent-inline-copies shape plan `21.1-02` was
    written to end.
    """
    targets = sorted(
        target
        for aim in CONTROL_AIM.values()
        if aim.kind == "pathspec"
        for target in aim.targets
    )
    assert targets, (
        "no `pathspec` aim is registered at all, so the loop below runs over"
        " the empty set — the vacuity this module exists to detect, arriving"
        " inside the check that detects it"
    )
    resolved = dict(asserted_pathspecs())
    unresolvable = sorted(set(targets) - set(resolved))
    assert not unresolvable, (
        f"these `pathspec` targets name no constant `asserted_pathspecs()`"
        f" resolves: {unresolvable}"
    )
    for target in targets:
        for member in resolved[target]:
            typo = near_miss(member)
            assert not tracked_under((typo,)), (
                f"the derived misspelling {typo!r} of {target}'s member"
                f" {member!r} names something `git` tracks, so substituting it"
                " would not break the control and this proof would pass over a"
                " constant it corrupted only in name"
            )

    failures, proven = _aim_proof(
        "pathspec",
        lambda _aim, target: _substituted(
            target, tuple(near_miss(member) for member in resolved[target])
        ),
        "misspelled member by member",
    )
    assert not failures, "\n".join(failures)
    assert proven, (
        "no pathspec aim was proven at all, so this control passed over the"
        " empty set"
    )


# ===========================================================================
# `D-21`, made standing — the carried-count sweep, and the sweep watched
# finding a planted count.
#
# `VAC-05` criterion 9, plan `21.1-09`. Every wave of this phase ran the sweep
# `grep -nE "== *[0-9]{2,}|len\(.*\) *[=!<>]= *[0-9]"` by hand and recorded that
# it exited 1. **That is a probe, and `D-IMPL-170` is that a probe is not a
# control**: a shell command in a SUMMARY is evidence somebody looked once, it
# runs in no gate, and nothing in the tree notices when it stops being run.
# The identical argument this phase makes about every other check applies to
# the check that polices this phase's own house rule.
#
# **The grep is a FLOOR, not the check, and the floor's own hole is named.**
# Phase 21's wave 1 had to widen a guard because it could not detect
# `EXPECTED_ROWS` bound to a literal — a bare assignment matches neither
# shape. So the sweep carries a SECOND limb the grep never had: no fixed set
# in this module may be compared by LENGTH. That is where a carried count
# actually does damage, because a length comparison is satisfied by any roster
# of the right size, which is precisely the substitution a roster exists to
# prevent.
# ===========================================================================

#: The line shapes that carry a count into a check, by the name of the defect.
#:
#: The two patterns are the ones every wave of this phase ran by hand, kept
#: byte-identical so the standing check and the recorded probes are the same
#: question. Their limits are stated rather than hidden: neither sees a bare
#: `NAME = <literal>` binding, and neither sees an inequality such as `> 1`.
#: The second limb below is what covers the damage those miss.
CARRIED_COUNT_SHAPES: dict[str, re.Pattern[str]] = {
    "an equality against a multi-digit literal": re.compile(r"== *[0-9]{2,}"),
    "a length compared against a numeric literal": re.compile(
        r"len\(.*\) *[=!<>]= *[0-9]"
    ),
}

def derived_fixed_sets() -> frozenset[str]:
    """Every FIXED SET this module holds, ENUMERATED from its own globals.

    The predicate is: a module-level name that is UPPERCASE, does not open
    with an underscore, and is bound to a `frozenset`, `tuple` or `dict`.

    **Derived rather than transcribed, on the `MULTI_MEMBER_PATHSPECS`
    precedent plan `21.1-01` set** — a constant that a later phase adds is
    dragged into the length check on its first run instead of waiting for
    somebody to remember this list. That is not hypothetical: written as a
    transcription first, this roster shipped MISSING TWO — the sweep's own
    :data:`CARRIED_COUNT_SHAPES`, and `CITED_SUFFIXES` — and the omission was
    found by writing the enumeration and diffing it, not by re-reading the
    list.

    The leading-underscore exclusion is deliberate and NAMED: `_NEUTERED` and
    `_REPO_INDEX_CACHE` are MUTABLE RUNTIME STATE, not fixed sets. `_NEUTERED`
    in particular is emptied and refilled by :func:`neutered`, and the autouse
    fixture asserts it EMPTY after every test — a rule saying it must never be
    measured by length would be wrong about it. Note that `str.isupper()` is
    true of `_NEUTERED`, so the underscore test is doing real work rather than
    restating the case test.
    """
    return frozenset(
        name
        for name, value in globals().items()
        if name.isupper()
        and not name.startswith("_")
        and isinstance(value, (frozenset, tuple, dict))
    )


#: Every FIXED SET this module holds, by NAME — the roster
#: :func:`derived_fixed_sets` is frozen against.
#:
#: A roster of names, not a count — the rule applied to itself. The membership
#: obligation is `D-21`'s: each of these is compared id-for-id, by membership
#: or by set equality, and never by length. :func:`carried_counts` holds that
#: mechanically, and refuses a name that is not bound here at all: a roster
#: renamed out from under this list would leave the length limb quantified
#: over nothing while still reporting clean.
#:
#: **Why a roster AS WELL AS the enumeration**, on exactly the reasoning
#: :data:`CONTROLS` carries: a predicate that quietly stops matching a
#: constant drops it from the length check in silence while both directions
#: still look healthy. The frozen roster is what makes that visible.
FIXED_SETS: frozenset[str] = frozenset(
    {
        "AIM_KINDS",
        "CARRIED_COUNT_SHAPES",
        "CASCADING_REDS",
        "CHANGED_TREE",
        "CITATION_EXEMPT_VERDICTS",
        "CITED_SUFFIXES",
        "COMPLETE_FAMILY",
        "CONTROLS",
        "CONTROL_AIM",
        "CONTROL_A_PATHSPECS",
        "FABRIC",
        "FENCE",
        "FIXED_SETS",
        "LIMBS",
        "MULTI_MEMBER_PATHSPECS",
        "PHASE_OWN_ROSTER",
        "PINNED_FILES",
        "TESTS_TREE",
        "UAT_RECORDS",
        "VERDICT_VOCABULARY",
        "WORKING_SET_ROSTER",
    }
)


def carried_counts(source: str) -> list[str]:
    """One message per line of `source` that carries a count into a check.

    Two limbs, both NAMED in the message so a reader can act on it:

    1. the line matches one of :data:`CARRIED_COUNT_SHAPES`; or
    2. the line calls `len(...)` on one of :data:`FIXED_SETS`.

    Findings are RETURNED rather than raised, which is what makes this a
    `guard` in the sense `D-IMPL-182` ratified: the control that holds it
    sabotages it and requires the control to notice, because there is no limb
    to neuter.
    """
    if not source.strip():
        _refuse(
            "carried_counts.empty_source",
            "the carried-count sweep was handed an empty subject, so 'no"
            " standing check carries a row count' is quantified over no lines"
            " at all and is trivially true. This is the shape a sweep takes"
            " when its subject moved and nobody noticed"
        )
    empty = sorted(
        name
        for name, roster in (
            ("CARRIED_COUNT_SHAPES", CARRIED_COUNT_SHAPES),
            ("FIXED_SETS", FIXED_SETS),
        )
        if not roster
    )
    if empty:
        _refuse(
            "carried_counts.empty_roster",
            f"the carried-count sweep's own rosters {empty} are EMPTY, so the"
            " limb each one drives is quantified over nothing and reports"
            " clean for free. A sweep whose subject roster has been emptied is"
            " the vacuity this module exists to detect, arriving inside the"
            " check that detects it"
        )
    module = globals()
    unbound = sorted(name for name in FIXED_SETS if name not in module)
    if unbound:
        _refuse(
            "carried_counts.unbound_roster",
            f"`FIXED_SETS` names {unbound}, which this module does not define."
            " The length limb below is then quantified over a name nothing"
            " holds, so a set renamed out from under this roster is swept for"
            " free while the sweep still reports clean"
        )
    length_patterns = {
        name: re.compile(r"len\([^)\n]*\b" + re.escape(name) + r"\b")
        for name in sorted(FIXED_SETS)
    }
    offenders: list[str] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        for defect, pattern in CARRIED_COUNT_SHAPES.items():
            found = pattern.search(line)
            if found is not None:
                offenders.append(
                    f"line {lineno} carries {defect}: {found.group(0)!r} in"
                    f" {line.strip()!r}"
                )
        for name, pattern in length_patterns.items():
            if pattern.search(line) is not None:
                offenders.append(
                    f"line {lineno} compares the fixed set `{name}` by LENGTH:"
                    f" {line.strip()!r}. A length is satisfied by any roster"
                    " of the right size, which is the substitution a roster of"
                    " named ids exists to prevent (`D-21`)"
                )
    return offenders


def module_source() -> str:
    """This module's own source, which is the sweep's subject."""
    return pathlib.Path(__file__).read_text(encoding="utf-8")


def test_no_standing_check_in_this_module_carries_a_carried_count() -> None:
    """Criterion 9, standing: no check here carries a row count.

    The house rule every wave of this phase asserted with a shell command now
    runs in `gate-tools` → `ci-core` → `ci` like everything else it polices.

    Two limbs, and the first is the one that keeps the second honest: the
    frozen :data:`FIXED_SETS` roster must agree ID FOR ID with
    :func:`derived_fixed_sets`, so a constant a later phase adds cannot sit
    outside the length check while this test still reports green.
    """
    derived = derived_fixed_sets()
    undeclared = sorted(derived - FIXED_SETS)
    stale = sorted(FIXED_SETS - derived)
    assert not undeclared and not stale, (
        "`FIXED_SETS` and the enumeration of this module's own constants"
        " disagree."
        f"\n  constants the module holds that the roster does not name:"
        f" {undeclared}"
        f"\n  names in the roster the module no longer holds: {stale}"
        "\nA constant missing from the roster is swept for FREE by the length"
        " limb below while this check still reports clean — which is how this"
        " very roster shipped its first draft missing two"
    )

    offenders = carried_counts(module_source())
    assert offenders == [], (
        "a standing check in this module carries a count. `D-21`: no"
        " hardcoded row count, and every fixed set is a frozen roster of named"
        " ids asserted id-for-id.\n" + "\n".join(offenders)
    )


def test_control_39_the_count_sweep_finds_a_planted_count() -> None:
    """CONTROL 39 — the sweep watched FINDING a planted count, on both limbs.

    **A sweep never observed finding anything is this phase's defect class
    inside the audit of this phase's defect class.** Phase 21 shipped three
    mis-aimed controls; a green grep is exactly the artefact those produced.

    Green-before/red-after, so the finding is attributable to the plant and to
    nothing else: the real module source is asserted CLEAN first, then each
    plant is appended to a copy of it and the sweep is required to NAME the
    planted line. Both limbs are exercised, because :data:`CONTROL_AIM` claims
    both and a proof of one is not a proof of the other.

    **The plants are ASSEMBLED at run time rather than written as literals,
    and the ROSTER NAME is assembled too.** A source file containing the
    offending text verbatim would be found by the standing sweep above — the
    control would redden the module it is defending. The first draft of this
    control did exactly that: it named the roster inside a `len(...)` call in
    its own body, and `test_no_standing_check_in_this_module_carries_a_carried_count`
    reported it on line 6665. That red is the best evidence in this file that
    the sweep works, and it is recorded here rather than quietly fixed.
    Assembling every offending piece keeps the plant out of the swept source
    while leaving it a real line the real sweep really matches.
    """
    real = module_source()
    assert carried_counts(real) == [], (
        "this module already carries a count, so this control cannot"
        " distinguish its plant from the status quo"
    )

    equality = "=" + "="
    shape_plant = f"    assert len(rows) {equality} {149}"
    found = carried_counts(real + "\n" + shape_plant + "\n")
    assert found, "a planted row count was swept over and reported clean"
    assert any("carries a" in message for message in found), (
        f"the sweep fired but named no defect shape: {found!r}"
    )

    roster = "LIM" + "BS"
    length_plant = "    assert len(" + roster + ") " + equality + " " + str(31)
    found = carried_counts(real + "\n" + length_plant + "\n")
    assert found, "a fixed set compared by LENGTH was swept over and reported clean"
    assert any("`LIMBS`" in message and "LENGTH" in message for message in found), (
        "the sweep fired but did not name the fixed set compared by length:"
        f" {found!r}. A count of offending lines is not something a reader can"
        " act on"
    )


def test_control_40_the_count_sweep_refuses_a_subject_it_cannot_sweep() -> None:
    """CONTROL 40 — the sweep's two anti-vacuity limbs, by limb id.

    A sweep over an empty subject reports clean, and so does a length limb
    whose roster names something the module no longer defines. Both are the
    vacuity this module exists to detect arriving at the boundary of the check
    that detects it, so both refuse and both are watched refusing here.

    **`try`/`except` and not `pytest.raises`**, on the idiom `CONTROL 24`
    established. `pytest.raises` raises `Failed` when nothing was raised, and
    `Failed` is not an `AssertionError` — so `CONTROL 35` would score this
    control's neutered red as a CASCADE and require it in
    :data:`CASCADING_REDS`, turning a clean proof of reach into a named crash.
    Measured: written with `pytest.raises`, this control reddened `CONTROL 35`
    on exactly that clause.
    """
    absent = "A_ROSTER_THIS_MODULE_DOES_NOT_DEFINE"
    try:
        swept = carried_counts("   \n\n  ")
    except AssertionError as refusal:
        assert "[limb:carried_counts.empty_source]" in str(refusal), (
            "an empty subject was refused by a limb other than"
            f" `carried_counts.empty_source`: {refusal}"
        )
    else:
        raise AssertionError(
            "the carried-count sweep was handed an empty subject and returned"
            f" {swept!r} rather than refusing. Zero offending lines out of zero"
            " lines is the report a sweep gives when its subject has moved"
        )

    try:
        with _substituted("CARRIED_COUNT_SHAPES", {}):
            swept = carried_counts(module_source())
    except AssertionError as refusal:
        assert "[limb:carried_counts.empty_roster]" in str(refusal), (
            "an emptied shape roster was refused by a limb other than"
            f" `carried_counts.empty_roster`: {refusal}"
        )
        assert "CARRIED_COUNT_SHAPES" in str(refusal), (
            f"the refusal fired but did not name the emptied roster: {refusal}"
        )
    else:
        raise AssertionError(
            "`CARRIED_COUNT_SHAPES` was emptied and the sweep returned"
            f" {swept!r} rather than refusing. Zero offending lines out of"
            " zero shapes is the report a sweep gives when its own roster has"
            " been emptied under it"
        )

    with _substituted("FIXED_SETS", FIXED_SETS | {absent}):
        try:
            swept = carried_counts(module_source())
        except AssertionError as refusal:
            assert "[limb:carried_counts.unbound_roster]" in str(refusal), (
                "a stale roster name was refused by a limb other than"
                f" `carried_counts.unbound_roster`: {refusal}"
            )
            assert absent in str(refusal), (
                f"the refusal fired but did not name {absent!r}: {refusal}. A"
                " count of unbound names is not something a reader can act on"
            )
        else:
            raise AssertionError(
                "`FIXED_SETS` named a set this module does not define and the"
                f" sweep returned {swept!r} rather than refusing. The length"
                " limb is then quantified over a name nothing holds"
            )
