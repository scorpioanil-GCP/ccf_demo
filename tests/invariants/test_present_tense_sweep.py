"""The criterion-15-class present-tense sweep, codified — derived universe, declared vocabulary.

``24.6-L-09`` (B-09). The instrument this module replaces was a shell command
living in a planning document — the criterion-15 grep recorded in
``.planning/phases/24.5.1-the-return-trip/24.5.1-BASELINES.md`` §3. It had three
holes, each of which is closed here by construction rather than by care:

* **R-3 — ``deployment.py`` was outside its universe.** The grep named
  ``{README.md,summary_explanations.md,assembler.py}`` per rung plus cp-04's
  ``server/*.py``; every rung's largest interpreter was unread. :func:`universe`
  is built by ``rglob`` over the rung directories, so a file cannot fall outside
  it by never having been listed.
* **R-4 — a fixed, case-sensitive phrase list.** :data:`SUPERSEDED_PHRASES` is a
  declared roster in which every phrase carries the ruling that superseded it,
  and matching is case-insensitive.
* **R-6 — hw1 was outside the universe entirely.** ``hw1-companies-over-revenue``
  is a rung of the universe here, README included.

**What the sweep is for.** A phase that changes what the SDK does leaves prose
behind that describes the SDK it replaced. The lie is not that the sentence was
never true; it is that it is written in the present tense. This module is the
ratchet: for every supersession this phase makes, the sentence that stated the
old behavior is a phrase in the roster, and the sweep says where it survives.

**Why an invariants module and not a ``tests/examples/`` one.** It reads
``examples/`` and ``tests/examples/``, but the C-01 fence for this phase admits
only cp-04, hw1 and cp-01 paths under ``tests/examples/``. A sweep whose subject
is every rung cannot live inside a fence that names three of them.

Wrapping, and why a line-at-a-time sweep would report clean
-----------------------------------------------------------

The lies this phase creates are mostly in wrapped comment blocks and wrapped
Markdown, and they cross line boundaries. ``examples/cp-04-corporate-family-tree/run.py``
reads ``… the SDK knows`` / ``# neither, and …``; ``transport.py`` reads
``… is not in`` / ``` `ccf.products.refusal::REFUSAL_KINDS`, so … ```. A
per-line ``grep`` sees neither, which is the failure mode the 24.5.1 instrument
had and nobody noticed, because a sweep that reports clean looks the same
whether it is clean or blind. So the scan normalizes before it matches:

1. lines are grouped into **paragraphs** — runs of consecutive non-blank lines,
   which is exactly how both a comment block and a Markdown paragraph wrap;
2. leading decoration (``#``, ``>``, ``*``, ``|`` and whitespace) is stripped,
   so a comment continuation joins its predecessor as prose;
3. backticks and asterisks are removed and quotes become spaces, so emphasis
   and inline code cannot split a phrase;
4. a symbol qualifier is reduced to its bare symbol —
   ``ccf.products.refusal::REFUSAL_KINDS`` reads as ``REFUSAL_KINDS`` — because
   the roster names what a sentence *says*, not how precisely it cites;
5. whitespace is collapsed and the comparison is case-folded.

The reported line is the line the match STARTS on, so a wrapped hit points at
the sentence rather than at its continuation.

What is NOT in the roster, deliberately
---------------------------------------

cp-00 through cp-03 carry prose saying their assemblers RAISE an assembly
refusal. Under ``D-IMPL-254`` those fourteen sites are governed determinations
that should return — but ``D-IMPL-255`` (1) ruled them **classified debt**,
deferred to each rung's own return trip, with no conversion in this phase. Their
prose is therefore still true of the tree it describes, and a roster entry for
it would report a lie that is not one. The sweep's vocabulary is this phase's
*shipped* supersessions only.

The rungs' ``spec/`` directories are excluded BY DIRECTORY. A CP-SPEC page is a
dated historical record under the 24.5.1 discipline — *"appended supersession
notes, never rewrites"* — so it carries superseded tokens on purpose, and
``D-IMPL-257`` recast four of them in place as prose beneath dated notes rather
than deleting them. The exclusion is asserted, and asserted to be load-bearing:
:func:`test_the_spec_exclusion_is_load_bearing` runs the same scanner over the
excluded pages and requires it to find something, so the exclusion can never
become a silent no-op nobody re-reads.

Two exemptions, both marked, both tested in both directions
------------------------------------------------------------

:data:`SUPERSESSION_NOTE_PREFIX` — a line that begins (after decoration) with
``SUPERSEDED`` is a dated historical quotation, and quoting the old sentence is
the discipline, not the defect. :data:`SWEEP_EXEMPT_MARKER` — a ``.py`` line
under ``tests/`` ending with ``# sweep-exempt: sabotage input`` is a sabotage's
INPUT: a control that plants the retired output and watches the comparison
reject it has to name the retired output. It has exactly one user
(``tests/examples/test_hw1_empty_fabric_refusal.py``, plan ``24.6-06``), the
count is asserted to be one, and the marker does nothing under ``examples/``.

Both exemptions make an exempt line a paragraph BOUNDARY rather than a skipped
line, so an exempt line's words cannot join their neighbors' and smuggle a
phrase past the scan from inside the carve-out.
"""

from __future__ import annotations

import functools
import pathlib
import re
import shutil
from typing import Iterable, NamedTuple

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class Supersession(NamedTuple):
    """One retired sentence, and the ruling that retired it."""

    phrase: str
    ruling: str


#: This phase's supersessions, as a declared vocabulary. Every entry names the
#: ruling that made it false, so a reader at a failure site can check the claim
#: rather than trusting the roster.
SUPERSEDED_PHRASES: tuple[Supersession, ...] = (
    Supersession(
        "the SDK knows neither",
        "D-15/`D-IMPL-254`: the depth outcomes cp-04 calls the SDK ignorant of"
        " become governed determinations the fabric's own vocabulary names."
        " Plan 24.6-13 rewrites cp-04's prose.",
    ),
    Supersession(
        "declares no envelope",
        "D-15/`D-IMPL-254`: same sentence, second half — a governed refusal that"
        " returns has an envelope by construction.",
    ),
    Supersession(
        "not in REFUSAL_KINDS",
        "Plan 24.6-08: `AssemblyRefused` narrows to invariant failure and the"
        " governed determinations return typed refusals the closed vocabulary"
        " does name. The gap the sentence records is closed.",
    ),
    Supersession(
        "refused by name at 6",
        "D-21: the declared bound of 6 is DELETED as a bound and kept only as a"
        " documented measurement; refusal moves to the backend's technical"
        " ceiling, read as a capability with authority `technical`.",
    ),
    Supersession(
        "declared ceiling of 6",
        "D-21: as above — after 24.6 there is no declared ceiling of 6 to name.",
    ),
    Supersession(
        "never clamped",
        "D-21: the promise survives, but every sentence carrying it on this tree"
        " states it OF the deleted bound of 6. Plan 24.6-13 restates it of the"
        " technical limit; until then each site is declared debt below.",
    ),
    Supersession(
        "stays a raise",
        "D-15 and plan 24.6-08: identity and contract determinations RETURN."
        " A forward guard — the tree carries no occurrence today.",
    ),
    Supersession(
        "raised and never enveloped",
        "D-15 and plan 24.6-08: same. A forward guard.",
    ),
    Supersession(
        "governance and identity stay raises",
        "D-15 and plan 24.6-08: same, in the summary form the 24.5 pages used."
        " A forward guard.",
    ),
    Supersession(
        "empty-operator-result",
        "`D-IMPL-253` Q12 and criteria 14/15: an operator over an empty graph has"
        " COMPUTED, the gate and the refusal kind are retired, and both"
        " transports serve. Its one surviving occurrence is a sabotage's input,"
        " under the marker below.",
    ),
    Supersession(
        "debt_ceiling",
        "`D-IMPL-251` C1=A: a product class may not hold a debt CEILING, only a"
        " default filling an omission. `effective_debt_ceiling` was deleted by"
        " plan 24.6-03.",
    ),
    Supersession(
        "class declares the ceiling",
        "`D-IMPL-251` C1=A: as above — the class declares a default, and the"
        " caller's tolerance is honored as requested. A forward guard.",
    ),
)

#: The sabotage-input carve-out. A ``.py`` line under ``tests/`` ending with
#: this marker is skipped: a control that plants a retired output and watches
#: the comparison reject it must spell the retired output. Nowhere else.
SWEEP_EXEMPT_MARKER = "# sweep-exempt: sabotage input"

#: The dated-supersession carve-out. A line whose text (decoration stripped)
#: begins with this word is quoting history on purpose.
SUPERSESSION_NOTE_PREFIX = "SUPERSEDED"

#: Non-vacuity floor. Named ``MINIMUM_*`` so ``tools/retirement_sweep.py``'s
#: floor scan can see this module if its walk is ever widened to
#: ``tests/invariants``. 69 paths at ``24.6-12``; the floor keeps headroom for
#: ordinary rung growth and refuses a walk that has started reading nothing.
MINIMUM_UNIVERSE_PATHS = 60

#: Non-vacuity floor, half two. A universe of 69 paths that scanned no text is
#: the ``tools/publish_scan.py::require_populated`` failure — *"refusing to
#: report clean over an empty tree"* — with a path list to make it look busy.
MINIMUM_SCANNED_PARAGRAPHS = 2000

#: Rung directories, as globs. The universe is every ``.py`` and ``.md`` under
#: them, so a new file joins the sweep by existing.
RUNG_GLOBS: tuple[str, ...] = ("cp-0*", "hw1-companies-over-revenue")

#: Test modules that belong to a rung, by module-name glob under
#: ``tests/examples/``. Their prose describes the same behavior the rungs do.
RUNG_TEST_GLOBS: tuple[str, ...] = ("test_cp_0*.py", "test_hw1_*.py")

#: Directory name whose contents are dated historical records (above).
SPEC_DIRECTORY = "spec"

_DECORATION = re.compile(r"^[\s>#*|]*")
_QUALIFIER = re.compile(r"[A-Za-z0-9_./-]+::")
_STRIPPED = str.maketrans({"`": "", "*": "", '"': " ", "'": " "})


class Violation(NamedTuple):
    """One surviving superseded sentence: the file, the line, the phrase."""

    path: str
    line: int
    phrase: str


class KnownDebt(NamedTuple):
    """A cp-04 site the phase has already scheduled, with its measured count."""

    path: str
    phrase: str
    occurrences: int


#: cp-04's surviving supersessions, MEASURED and DECLARED here rather than
#: derived from the run they excuse — a table computed from today's violations
#: would excuse tomorrow's as well. Every row is ``xfail(strict=True)``, so a
#: fixed site turns RED here until the row goes, which is the property that
#: makes this a schedule rather than a silencer.
#:
#: SHRUNK 2026-09-05 by ``24.6-13``, in two steps and never in one:
#:
#: * the nine rows naming ``assembler.py``, ``deployment.py``, ``produce.py``,
#:   ``run.py``, ``transport.py`` and ``server/compose.py`` went with the
#:   BEHAVIOR rebuild, after each was watched XPASSing — 9 strict xfails turned
#:   RED, plus this table's own equality: 10 failures over 826 passes;
#: * the four ``tests/examples`` rows went with the tests they describe, again
#:   after being watched XPASSing — 4 strict xfails turned RED, plus the
#:   equality, over 834 passes.
#:
#: What is left is the two DOCUMENT rows. ``README.md`` and
#: ``summary_explanations.md`` are plan ``24.6-14``'s prose fence rather than
#: this plan's, and their counts are re-measured here rather than carried.
CP04_KNOWN_DEBT: tuple[KnownDebt, ...] = (
    KnownDebt("examples/cp-04-corporate-family-tree/README.md", "declared ceiling of 6", 1),
    KnownDebt("examples/cp-04-corporate-family-tree/README.md", "never clamped", 2),
    KnownDebt("examples/cp-04-corporate-family-tree/summary_explanations.md", "never clamped", 4),
)

#: The pairs alone, for the parametrization's marker lookup.
CP04_DEBT_PAIRS: frozenset[tuple[str, str]] = frozenset(
    (row.path, row.phrase) for row in CP04_KNOWN_DEBT
)

XFAIL_REASON = "24.6-13 rebuilds cp-04 under D-21/D-15; RED-when-fixed until then"


# ---------------------------------------------------------------------------
# The universe — derived, never listed
# ---------------------------------------------------------------------------


def universe(root: pathlib.Path = REPO_ROOT) -> tuple[pathlib.Path, ...]:
    """Every rung file and rung test module under `root`, repo-relative.

    Derived: ``rglob`` over each rung directory and a glob over
    ``tests/examples``. Nothing here is a file list, which is the whole
    difference between this and the instrument it replaces — a file that did
    not exist when the sweep was written is still inside it.

    Excluded: ``__pycache__`` (build output) and each rung's ``spec/``
    directory (dated historical records; see the module docstring).
    """
    found: set[pathlib.Path] = set()
    examples = root / "examples"
    for pattern in RUNG_GLOBS:
        for rung in sorted(examples.glob(pattern)):
            if not rung.is_dir():
                continue
            for suffix in ("*.py", "*.md"):
                for path in rung.rglob(suffix):
                    if not path.is_file() or _is_excluded(path):
                        continue
                    found.add(path.relative_to(root))
    tests = root / "tests" / "examples"
    for pattern in RUNG_TEST_GLOBS:
        for path in sorted(tests.glob(pattern)):
            if path.is_file() and not _is_excluded(path):
                found.add(path.relative_to(root))
    return tuple(sorted(found))


def _is_excluded(path: pathlib.Path) -> bool:
    return "__pycache__" in path.parts or SPEC_DIRECTORY in path.parts


def spec_pages(root: pathlib.Path = REPO_ROOT) -> tuple[pathlib.Path, ...]:
    """The pages :func:`universe` excludes by directory — the exclusion's subject."""
    examples = root / "examples"
    found: set[pathlib.Path] = set()
    for pattern in RUNG_GLOBS:
        for rung in sorted(examples.glob(pattern)):
            for suffix in ("*.py", "*.md"):
                for path in rung.rglob(suffix):
                    if path.is_file() and SPEC_DIRECTORY in path.parts:
                        found.add(path.relative_to(root))
    return tuple(sorted(found))


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------


def _normalize(line: str) -> str:
    """One line as prose: decoration off, emphasis off, qualifiers reduced."""
    text = _DECORATION.sub("", line).translate(_STRIPPED)
    return " ".join(_QUALIFIER.sub("", text).split())


def _is_exempt(line: str, *, under_tests: bool) -> bool:
    if under_tests and line.rstrip().endswith(SWEEP_EXEMPT_MARKER):
        return True
    return _DECORATION.sub("", line).lstrip().startswith(SUPERSESSION_NOTE_PREFIX)


def paragraphs(text: str, *, under_tests: bool) -> list[list[tuple[int, str]]]:
    """`text` as runs of consecutive prose lines, each line with its number.

    A blank line and an exempt line both END a run. An exempt line ending it
    rather than merely being skipped is deliberate: otherwise the carve-out's
    words would join their neighbors' and a phrase could cross it.
    """
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        normalized = "" if _is_exempt(line, under_tests=under_tests) else _normalize(line)
        if not normalized:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append((number, normalized))
    if current:
        blocks.append(current)
    return blocks


def present_tense_violations(
    paths: Iterable[pathlib.Path | str],
    *,
    root: pathlib.Path = REPO_ROOT,
) -> list[Violation]:
    """Every surviving superseded phrase under `paths`, as (file, line, phrase).

    `paths` are interpreted relative to `root`; an absolute path is made
    relative to it first, so a scratch tree under ``tmp_path`` reports the same
    names the real tree does.
    """
    violations: list[Violation] = []
    for candidate in paths:
        relative = pathlib.Path(candidate)
        if relative.is_absolute():
            relative = relative.relative_to(root)
        violations.extend(_scan(root, relative.as_posix()))
    return violations


def _scan(root: pathlib.Path, relative: str) -> tuple[Violation, ...]:
    path = root / relative
    text = path.read_text(encoding="utf-8", errors="replace")
    under_tests = "tests" in pathlib.PurePosixPath(relative).parts and path.suffix == ".py"
    found: list[Violation] = []
    for block in paragraphs(text, under_tests=under_tests):
        joined = " ".join(normalized for _, normalized in block)
        haystack = joined.casefold()
        lines: list[int] = []
        for number, normalized in block:
            lines.extend([number] * (len(normalized) + 1))
        for supersession in SUPERSEDED_PHRASES:
            needle = supersession.phrase.casefold()
            start = 0
            while True:
                at = haystack.find(needle, start)
                if at < 0:
                    break
                found.append(Violation(relative, lines[at], supersession.phrase))
                start = at + 1
    return tuple(sorted(found))


@functools.lru_cache(maxsize=None)
def _cached_scan(relative: str) -> tuple[Violation, ...]:
    return _scan(REPO_ROOT, relative)


# ---------------------------------------------------------------------------
# The universe is derived
# ---------------------------------------------------------------------------


def test_the_universe_is_derived_and_non_empty() -> None:
    """R-3 and R-6, closed by name: every interpreter, and hw1, are inside it."""
    paths = universe()
    assert len(paths) >= MINIMUM_UNIVERSE_PATHS, (
        f"the universe holds {len(paths)} paths, below the floor of"
        f" {MINIMUM_UNIVERSE_PATHS}. Either rungs were removed — lower this"
        " constant in the same commit and name the removal — or the derivation"
        " has stopped reading the tree."
    )
    names = {path.as_posix() for path in paths}

    interpreters = sorted(
        rung.name
        for pattern in RUNG_GLOBS
        for rung in (REPO_ROOT / "examples").glob(pattern)
        if (rung / "deployment.py").is_file()
    )
    assert interpreters, "no rung ships a deployment.py — the probe read nothing"
    for rung in interpreters:
        assert f"examples/{rung}/deployment.py" in names, (
            f"{rung}'s interpreter is outside the universe — this is R-3, the"
            " hole the 24.5.1 grep had."
        )

    assert "examples/hw1-companies-over-revenue/README.md" in names, (
        "hw1 is outside the universe — this is R-6."
    )
    assert "examples/cp-01-counterparty-reference-snapshot/page/build_page.py" in names, (
        "a page generator is outside the universe; captions are prose too."
    )
    assert not [name for name in names if f"/{SPEC_DIRECTORY}/" in name], (
        "a spec page reached the universe; those are dated historical records."
    )


def test_a_planted_spec_path_is_excluded_and_its_sibling_is_not(
    tmp_path: pathlib.Path,
) -> None:
    """The exclusion is a property of the derivation, not of today's tree."""
    rung = tmp_path / "examples" / "cp-09-scratch"
    (rung / SPEC_DIRECTORY).mkdir(parents=True)
    (rung / SPEC_DIRECTORY / "CP-SPEC-009.md").write_text("never clamped\n", encoding="utf-8")
    (rung / "README.md").write_text("ordinary prose\n", encoding="utf-8")
    (tmp_path / "tests" / "examples").mkdir(parents=True)

    names = {path.as_posix() for path in universe(tmp_path)}
    assert "examples/cp-09-scratch/README.md" in names, names
    assert "examples/cp-09-scratch/spec/CP-SPEC-009.md" not in names, names


def test_the_spec_exclusion_is_load_bearing() -> None:
    """An exclusion that excludes nothing is a rule nobody has to obey.

    The same scanner over the excluded pages must find something, or the
    exclusion above is decoration and a later reader will delete it as dead.
    """
    pages = spec_pages()
    assert pages, "no spec page was found at all — the probe read nothing"
    found = present_tense_violations(pages)
    assert found, (
        "the spec pages carry no superseded phrase, so excluding them changes"
        " nothing. Either the roster no longer names what those dated notes"
        " quote — in which case the exclusion can go — or the scan is blind."
    )


def test_the_scan_reads_a_non_empty_population() -> None:
    """Half two of non-vacuity: the walk read text, not just filenames."""
    total = 0
    for path in universe():
        text = (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")
        under_tests = "tests" in path.parts and path.suffix == ".py"
        total += sum(len(block) for block in paragraphs(text, under_tests=under_tests))
    assert total >= MINIMUM_SCANNED_PARAGRAPHS, (
        f"the scan read {total} prose lines across the universe, below the"
        f" floor of {MINIMUM_SCANNED_PARAGRAPHS}. A sweep that reads nothing"
        " reports clean forever."
    )


# ---------------------------------------------------------------------------
# The roster
# ---------------------------------------------------------------------------


def test_every_phrase_names_the_ruling_that_superseded_it() -> None:
    """A phrase without a ruling is a banned string nobody can argue with."""
    assert SUPERSEDED_PHRASES, "the roster is empty"
    phrases = [entry.phrase for entry in SUPERSEDED_PHRASES]
    assert len(set(phrases)) == len(phrases), sorted(phrases)
    for entry in SUPERSEDED_PHRASES:
        assert entry.phrase.strip(), entry
        assert len(entry.ruling.strip()) >= 40, (
            f"{entry.phrase!r} is superseded by {entry.ruling!r}, which is too"
            " short to be a reason a reader can check."
        )


# ---------------------------------------------------------------------------
# The sweep itself
# ---------------------------------------------------------------------------


def _rows() -> list[tuple[str, str]]:
    return [
        (path.as_posix(), entry.phrase)
        for path in universe()
        for entry in SUPERSEDED_PHRASES
    ]


def _row(path: str, phrase: str) -> object:
    marks = [pytest.mark.xfail(strict=True, reason=XFAIL_REASON)] if (path, phrase) in CP04_DEBT_PAIRS else []
    return pytest.param(path, phrase, marks=marks, id=f"{path}::{phrase}")


@pytest.mark.parametrize(("path", "phrase"), [_row(path, phrase) for path, phrase in _rows()])
def test_no_superseded_phrase_survives(path: str, phrase: str) -> None:
    """One row per (file, phrase). cp-04's declared debt is the only exception."""
    found = [row for row in _cached_scan(path) if row.phrase == phrase]
    assert not found, (
        f"{path} still states {phrase!r} in the present tense at line(s)"
        f" {[row.line for row in found]}. Superseded by:"
        f" {next(e.ruling for e in SUPERSEDED_PHRASES if e.phrase == phrase)}"
    )


def test_the_declared_cp_04_debt_is_exactly_what_the_tree_carries() -> None:
    """The excuse list is measured against the tree, counts included.

    Three ways this goes red, all of them wanted: plan 24.6-13 fixes a site
    (delete the row), a new cp-04 lie appears (fix it or rule it), or an
    already-excused pair grows an occurrence (the pair is excused, the growth
    is not).
    """
    measured: dict[tuple[str, str], int] = {}
    for path in universe():
        for row in _cached_scan(path.as_posix()):
            measured[(row.path, row.phrase)] = measured.get((row.path, row.phrase), 0) + 1

    declared = {(row.path, row.phrase): row.occurrences for row in CP04_KNOWN_DEBT}
    assert measured == declared, (
        "the tree's surviving supersessions and CP04_KNOWN_DEBT disagree."
        f" only in the tree: {sorted(set(measured) - set(declared))};"
        f" only declared: {sorted(set(declared) - set(measured))};"
        " differing counts: "
        + str(
            {
                key: (declared[key], measured[key])
                for key in set(declared) & set(measured)
                if declared[key] != measured[key]
            }
        )
    )


def test_every_declared_debt_row_is_a_cp_04_row() -> None:
    """The carve-out is cp-04's rebuild, not a general amnesty."""
    for row in CP04_KNOWN_DEBT:
        assert row.path.startswith("examples/cp-04-") or row.path.startswith(
            "tests/examples/test_cp_04_"
        ), f"{row.path} is excused but is not a cp-04 path"
        assert row.occurrences >= 1, row


# ---------------------------------------------------------------------------
# Controls — every one of them catches something on a scratch copy
# ---------------------------------------------------------------------------


def _scratch(tmp_path: pathlib.Path, relative: str, text: str) -> str:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return relative


def test_a_planted_phrase_in_a_scratch_copy_is_red(tmp_path: pathlib.Path) -> None:
    """The sweep's own positive control: a real file, copied, one line added."""
    source = REPO_ROOT / "examples/hw1-companies-over-revenue/README.md"
    original = source.read_text(encoding="utf-8")
    assert not present_tense_violations(
        ["examples/hw1-companies-over-revenue/README.md"]
    ), "the control's subject is not clean to begin with"

    relative = _scratch(
        tmp_path,
        "examples/hw1-companies-over-revenue/README.md",
        original + "\nThe gate declares no envelope for it.\n",
    )
    found = present_tense_violations([relative], root=tmp_path)
    assert [row.phrase for row in found] == ["declares no envelope"], found
    assert found[0].line == len(original.splitlines()) + 2, found


def test_the_sweep_is_case_insensitive(tmp_path: pathlib.Path) -> None:
    """R-4's second half: a phrase re-cased is the same phrase."""
    relative = _scratch(
        tmp_path, "examples/cp-09-scratch/README.md", "Both are ours; The Sdk Knows Neither.\n"
    )
    found = present_tense_violations([relative], root=tmp_path)
    assert [row.phrase for row in found] == ["the SDK knows neither"], found


def test_a_phrase_wrapped_across_two_lines_is_caught(tmp_path: pathlib.Path) -> None:
    """The hole a per-line grep has, and the reason for the paragraph rule."""
    relative = _scratch(
        tmp_path,
        "examples/cp-09-scratch/produce.py",
        "# BOTH are this example's own types, the SDK knows\n"
        "# neither, and the fabric says so.\n",
    )
    found = present_tense_violations([relative], root=tmp_path)
    assert [(row.line, row.phrase) for row in found] == [(1, "the SDK knows neither")], found


def test_a_phrase_split_by_a_blank_line_is_not_joined(tmp_path: pathlib.Path) -> None:
    """The paragraph rule's other side, so the join cannot run away with a file."""
    relative = _scratch(
        tmp_path,
        "examples/cp-09-scratch/produce.py",
        "# the SDK knows\n\n# neither of them matters here\n",
    )
    assert present_tense_violations([relative], root=tmp_path) == []


def test_the_supersession_note_exemption_needs_the_marker(tmp_path: pathlib.Path) -> None:
    """A dated quotation is exempt; the same sentence unmarked is not."""
    unmarked = _scratch(
        tmp_path,
        "examples/cp-09-scratch/ONE.md",
        "> The fabric declares no envelope for either.\n",
    )
    assert [row.phrase for row in present_tense_violations([unmarked], root=tmp_path)] == [
        "declares no envelope"
    ]

    marked = _scratch(
        tmp_path,
        "examples/cp-09-scratch/TWO.md",
        "> SUPERSEDED 2026-09-04: the fabric declares no envelope for either.\n",
    )
    assert present_tense_violations([marked], root=tmp_path) == []


def test_the_sabotage_input_exemption_needs_the_marker_and_a_tests_path(
    tmp_path: pathlib.Path,
) -> None:
    """Marked and under `tests/` is exempt; either half alone is not."""
    body = 'reverted = (1, "refused: empty-operator-result\\n")'

    marked_test = _scratch(
        tmp_path, "tests/examples/test_scratch.py", f"    {body}  {SWEEP_EXEMPT_MARKER}\n"
    )
    assert present_tense_violations([marked_test], root=tmp_path) == []

    unmarked_test = _scratch(tmp_path, "tests/examples/test_other.py", f"    {body}\n")
    assert [row.phrase for row in present_tense_violations([unmarked_test], root=tmp_path)] == [
        "empty-operator-result"
    ], "the marker is doing the work, not the path"

    marked_example = _scratch(
        tmp_path, "examples/cp-09-scratch/produce.py", f"    {body}  {SWEEP_EXEMPT_MARKER}\n"
    )
    assert [row.phrase for row in present_tense_violations([marked_example], root=tmp_path)] == [
        "empty-operator-result"
    ], "the marker worked under examples/, where a sabotage input has no business"


def test_the_marked_needle_is_the_only_marked_line() -> None:
    """One user, asserted, so the carve-out cannot grow a second one quietly."""
    marked: list[str] = []
    for path in universe():
        text = (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip().endswith(SWEEP_EXEMPT_MARKER):
                marked.append(f"{path.as_posix()}:{number}")
    assert marked == ["tests/examples/test_hw1_empty_fabric_refusal.py:466"], (
        "the sabotage-input carve-out has moved or grown. One line, plan"
        f" 24.6-06's needle, is the whole of it; found {marked}"
    )


def test_no_control_edits_the_real_source_tree(tmp_path: pathlib.Path) -> None:
    """Every plant above happened on a copy; the subject is unread-only proof."""
    source = REPO_ROOT / "examples/hw1-companies-over-revenue/README.md"
    before = source.read_bytes()
    copied = tmp_path / "README.md"
    shutil.copyfile(source, copied)
    copied.write_text(copied.read_text(encoding="utf-8") + "never clamped\n", encoding="utf-8")
    assert present_tense_violations([copied], root=tmp_path)
    assert source.read_bytes() == before
