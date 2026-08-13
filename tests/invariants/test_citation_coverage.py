"""The unanchored-citation population is held from both sides.

``D-IMPL-114`` (Dave, 2026-08-11) ruled that *"a line-anchored citation is wrong
the moment code moves, and code moves every phase; the anchor therefore encodes
a fact with a shorter half-life than the claim it supports"*, and that prose
cites ``path::Symbol`` instead. ``D-IMPL-123`` (Dave, 2026-08-12) scoped the
sweep that discharges its consequence (2): **every unanchored citation whose
target is a Python file, except the thirteen in the records ``D-IMPL-114`` says
a later editor should not silently revise.** This module is that sweep's
ratchet — the thing that stops the population growing back.

**The citation gate is GREEN, and this module is not a repair of it.**

Stated first because a reader arriving at a failure here will otherwise assume
the opposite. ``python3 -m tools.lints --citations`` reports **zero findings**;
it reported zero before the sweep and reports zero after. An *unanchored*
citation is not a failing citation — it is a citation the checker declines to
check, because there is no anchor to check it against. The population this
module bounds is therefore a statement about **coverage**, and every assertion
here is a coverage ratchet. Nothing in this file is evidence that the citation
invariant is broken, and the failure messages say so in their own text.

Both directions, and why that has no precedent here
---------------------------------------------------

Every other count-pinning gate in this tree is a **floor**:
``tests/products/test_gate_two_call_shape.py`` carries
``MINIMUM_GATE_CALL_SITES``, ``MINIMUM_PROJECTING_BODIES`` and
``MINIMUM_RESOLVED_BINDER_SITES``, each asserting that a scan found *at least*
what the tree is known to hold. A citation sweep needs the opposite: a
**ceiling**, so that the swept population cannot regrow one citation at a time
across later phases. :data:`MAXIMUM_UNANCHORED_PY_CITATIONS` is the first
ceiling in this tree, and ``tools/retirement_sweep.py::_floors`` — which
recognises only ``ast.GtE``/``ast.Gt`` against a ``MINIMUM_*`` constant — cannot
see it. That is why the non-vacuity halves below are named ``MINIMUM_*``: a
ceiling alone would leave this module invisible to the sweep that re-floors
count gates when the tree changes.

**Measured, not assumed, because "the sweep can see it" has two halves.**
``tools/retirement_sweep.py::_floors`` recognises both floors below — run
against this module it reports ``MINIMUM_SCANNED_CITATION_HOSTS`` and
``MINIMUM_CITATIONS_READ``, each paired with the scan function feeding it — and
``count_coupling_rows`` run with ``roots=[tests/invariants]`` emits four live
rows, because both scans walk ``examples/`` and the first breaks at wave 8 when
``examples/03-harness-portability`` retires. What the sweep's *default* walk
does not reach is this tree: ``COUNT_COUPLING_TREES`` is ``("tests/products",)``.
Widening it is one line of data — the sweep's own docstring invites exactly that
— but it also changes ``docs/surface/examples/RETIREMENT-COUPLINGS.md``, a
Phase 16 artifact already carried as stale under ``DI-15.6-01``, so plan
``15.6-11`` left the widening to the plan that owns that report and recorded the
four rows in its deferred items instead.

A ceiling on its own is also unsafe in a way a floor is not. A ceiling over a
**broken scan** reports zero and passes forever, which is exactly the posture
``tools/publish_scan.py::require_populated`` refuses — *"refusing to report
clean over an empty tree"*. So the ceiling is paired with two floors asserting
that the scan read something: files, and citations inside them.

Everything is derived from the shipped checker
----------------------------------------------

:func:`citation_sites` calls into ``tools/lints/citations.py`` for every
predicate it applies — ``CITATION`` and ``NODE_ID`` for the two citation forms,
``prose_lines`` for the comments-and-docstrings-only rule inside ``.py`` files,
``exemption_reason`` for the ``HISTORICAL_RECORDS``-minus-``MAINTAINED_RECORDS``
policy, ``is_historical`` for the historicity markers, and ``resolve_cited``
plus ``parse_line_spec`` for target resolution. There is **no citation regex in
this module**. A bespoke rule here would re-litigate a scope that
``tools/lints/citations.py`` says outright was *"written after scanning every
top-level tracked directory for citations, not before"*, and would drift from
the checker the moment either changed.

What this module does NOT claim
-------------------------------

* It does **not** claim the swept citations are *true*. ``cite03-node-id``
  proves a cited symbol exists; no checker in this tree proves the sentence
  around a citation is right.
* It makes **no** statement about the thirteen held-back citations in
  :data:`HELD_BACK_HOSTS`. They are out of ``D-IMPL-123``'s scope by ruling,
  and two of them still carry the exact stale range ``D-IMPL-114`` was written
  about — *"the sweep therefore leaves the originating defect visibly extant in
  two places by ruling, which is the intended outcome and not an oversight."*
* It bounds only citations whose **target** is a ``.py`` file. Unanchored
  citations of Markdown, YAML and TOML targets are the larger population and
  are outside ``D-IMPL-123``.
"""

from __future__ import annotations

import fnmatch
import pathlib
from typing import NamedTuple

from tools.lints.citations import (
    CITATION,
    NODE_ID,
    RULE_NODE_ID,
    anchor_before,
    check_source,
    exemption_reason,
    is_historical,
    iter_scanned_files,
    parse_line_spec,
    prose_lines,
    repo_index,
    resolve_cited,
    scan_tree,
)

#: Anchored on this file rather than on ``Path.cwd()`` — a scan root that
#: depends on the working directory passes or fails for reasons that have
#: nothing to do with the tree. ``parents[2]`` is the repo root from
#: ``tests/invariants/<module>.py``.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The thirteen citations ``D-IMPL-123`` holds back, named by **host** so the
#: boundary is checkable rather than asserted. Five landed plan fragments under
#: ``docs/surface-changes/`` carry eleven between them; ``docs/SURFACE-CHANGES.md``
#: carries two and is the whole-tree-assembled artifact that ``make
#: surface-changes`` regenerates from those fragments, so editing it directly is
#: overwritten rather than preserved. ``docs/DECISIONS.md`` is the third record
#: ``D-IMPL-114`` names and contributes zero here, because
#: ``tools/lints/citations.py::HISTORICAL_RECORDS`` already exempts it wholesale.
#:
#: Matched with :func:`fnmatch.fnmatch` against the repo-relative POSIX path,
#: the same way ``exemption_reason`` matches its own patterns.
HELD_BACK_HOSTS: tuple[tuple[str, str], ...] = (
    (
        "docs/surface-changes/*",
        "landed plan fragments — a later editor should not silently revise one"
        " to chase a line number (D-IMPL-114)",
    ),
    (
        "docs/SURFACE-CHANGES.md",
        "the whole-tree-assembled artifact, regenerated by `make"
        " surface-changes` from the fragments above; a direct edit is"
        " overwritten rather than preserved",
    ),
)

#: The checker's own two files, excluded by name rather than by class. Plan
#: ``15.6-11``'s pre-sweep sample found 19 of 19 code-tree false positives
#: concentrated here, because these files carry docstring examples and fixture
#: strings *about* the citation form — test data, not claims about the tree —
#: and the rate elsewhere in the sample was zero.
#:
#: Measured at ``962e75d``: both contribute **zero** to the population today,
#: because the false-positive strings sit on code lines, which
#: ``prose_lines`` already excludes inside a ``.py`` file. The exclusion is
#: kept anyway, so that a later edit moving one of those strings into a
#: docstring cannot silently raise the ceiling's subject.
CHECKER_OWN_FILES: tuple[str, ...] = (
    "tools/lints/citations.py",
    "tools/lints/tests/test_citations.py",
)

#: The ceiling. **The first ceiling in this tree** — every other count gate
#: here is a ``MINIMUM_*`` floor, and ``tools/retirement_sweep.py::_floors``
#: recognises only ``ast.GtE``/``ast.Gt`` against a ``MINIMUM_*`` constant, so
#: this constant is invisible to that sweep. The ``MINIMUM_*`` floors below are
#: what keeps this module visible to it.
#:
#: **Measured, not carried.** Derived by re-using the checker's own scanner at
#: commit ``962e75d`` (plan ``15.6-11``'s base): the ``no_anchor`` bucket of
#: ``scan_tree`` was reproduced exactly — 434 of 434 — and filtered to citations
#: whose *target* is a ``.py`` file, giving **113** across 27 host files, of
#: which **13** are held back by :data:`HELD_BACK_HOSTS`, leaving **100**
#: sweepable. ``D-IMPL-123`` ruled the same measurement at ``4b407e0`` as 114 /
#: 13 / 101; the one-citation difference is drift between the two commits and is
#: recorded in plan ``15.6-11``'s SUMMARY rather than smoothed over.
#:
#: **This is the PRE-sweep value.** The ceiling ships before the sweep that
#: lowers it, so the sweep is measured against a gate rather than against a
#: hope; plan ``15.6-11`` task 2 lowers it in the same commit as the sweep.
MAXIMUM_UNANCHORED_PY_CITATIONS = 100

#: Non-vacuity, half one: the walk read files. Named ``MINIMUM_*`` so
#: ``tools/retirement_sweep.py::_floors`` can see this module at all — a gate
#: that sweep cannot see is a gate nobody re-floors when the tree changes.
#:
#: The posture is ``tools/publish_scan.py::require_populated``'s, quoted because
#: the reason travels better than the rule: *"refusing to report clean over an
#: empty tree"*. Without this, a scanner that silently read nothing would report
#: a population of zero and satisfy the ceiling forever.
#:
#: Measured at ``962e75d`` **with this module present**: ``scan_tree`` reports
#: 954 scanned and 465 exempt. No headroom, following
#: ``tests/products/test_gate_two_call_shape.py``'s stated convention that a
#: floor is the count observed in the tree.
MINIMUM_SCANNED_CITATION_HOSTS = 954

#: Non-vacuity, half two: the files the walk read actually contained citations.
#: Half one alone passes over a walk that found 953 files and matched nothing in
#: any of them — a broken pattern, an import that resolved to a stub, a
#: ``prose_lines`` that returned an empty set. Both halves together are what
#: makes a ceiling of zero mean *swept* rather than *unread*.
#:
#: Measured at ``962e75d`` **with this module present**: ``scan_tree`` reports
#: 808 citations matched (801 before this module, which itself cites seven).
#: ``D-IMPL-123`` recorded 762 at ``4b407e0``; the tree gained citations between
#: the two commits, which is why this is a floor and not an equality.
MINIMUM_CITATIONS_READ = 808

#: The counterpart of ``tests/products/test_gate_two_call_shape.py``'s
#: ``FLOOR_REMOVAL_INSTRUCTION``, for a ceiling's opposite case. Raising a
#: ceiling deliberately and raising it to make a red build green need the
#: identical edit, so nothing at the failure site distinguishes them.
CEILING_RAISE_INSTRUCTION = (
    "A DELIBERATE addition and an accidental regression need the identical edit"
    " to this constant, so nothing at this failure site tells them apart. Prefer"
    " converting the citation to the `path.py::Symbol` form D-IMPL-114 ruled. If"
    " the citation genuinely cannot carry a symbol, raise the constant in the"
    " same commit and name the citation in the commit message — `git log` is then"
    " the only thing that distinguishes the two afterwards."
)

#: Prepended to every failure here, because the misreading it prevents is the
#: expensive one: a reader who takes a red line in this module as evidence that
#: the citation invariant is broken will go looking for a defect that does not
#: exist.
GATE_IS_GREEN_NOTE = (
    "NOTE BEFORE READING THE FAILURE: the citation gate is GREEN. `python3 -m"
    " tools.lints --citations` reports zero findings, and did before this"
    " module existed. An unanchored citation is one the checker DECLINES TO"
    " CHECK for want of an anchor, not one that failed. This is a COVERAGE"
    " ratchet. Re-measure with `python3 -m tools.lints --report`."
)


class Site(NamedTuple):
    """One unanchored citation of a Python target, and where it was read."""

    host: str
    line: int
    cited: str
    lines: str
    held_back: bool

    def __str__(self) -> str:  # pragma: no cover - failure-message formatting
        return f"{self.host}:{self.line} cites {self.cited}:{self.lines}"


def _held_back_reason(host: str) -> str | None:
    """Why `host`'s citations are out of ``D-IMPL-123``'s scope, or ``None``."""
    for pattern, reason in HELD_BACK_HOSTS:
        if fnmatch.fnmatch(host, pattern):
            return reason
    return None


def scanned_citation_hosts() -> list[str]:
    """Every gated file the citation checker reads, repo-relative.

    The checker's own walk and the checker's own exemption policy, so this
    cannot drift from what ``scan_tree`` covers.
    """
    hosts: list[str] = []
    for path in iter_scanned_files(REPO_ROOT):
        host = path.relative_to(REPO_ROOT).as_posix()
        if exemption_reason(host) is not None:
            continue
        hosts.append(host)
    return hosts


def citations_read() -> list[str]:
    """Every citation the checker matches, as ``host:line`` sites.

    Both forms, counted the way ``check_source`` counts them into
    ``Scan.total``: one per ``NODE_ID`` match and one per ``CITATION`` match,
    on prose lines only inside ``.py`` files.
    """
    sites: list[str] = []
    for host in scanned_citation_hosts():
        path = REPO_ROOT / host
        source = path.read_text(encoding="utf-8", errors="replace")
        prose = prose_lines(source) if path.suffix == ".py" else None
        for lineno, line in enumerate(source.splitlines(), 1):
            if prose is not None and lineno not in prose:
                continue
            for _ in NODE_ID.finditer(line):
                sites.append(f"{host}:{lineno}")
            for _ in CITATION.finditer(line):
                sites.append(f"{host}:{lineno}")
    return sites


def citation_sites() -> list[Site]:
    """Every unanchored citation whose target is a Python file.

    Reproduces the branch of ``tools.lints.citations.check_source`` that lands
    a citation in ``Scan.no_anchor`` — not historical, target resolves, every
    cited line inside the target, and no backticked anchor immediately before
    it — then keeps only the ones citing a ``.py`` target. Every predicate is
    the checker's own.
    """
    index = repo_index(REPO_ROOT)
    found: list[Site] = []
    for host in scanned_citation_hosts():
        if host in CHECKER_OWN_FILES:
            continue
        path = REPO_ROOT / host
        source = path.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        prose = prose_lines(source) if path.suffix == ".py" else None
        for lineno, line in enumerate(lines, 1):
            if prose is not None and lineno not in prose:
                continue
            for match in CITATION.finditer(line):
                cited = match.group("path")
                if not cited.endswith(".py"):
                    continue
                if is_historical(lines, lineno, match.start()):
                    continue
                target, _ambiguous = resolve_cited(cited, REPO_ROOT, index)
                if target is None:
                    continue
                target_lines = target.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
                if max(parse_line_spec(match.group("lines"))) > len(target_lines):
                    continue
                if anchor_before(line, match.start()) is not None:
                    continue
                found.append(
                    Site(
                        host=host,
                        line=lineno,
                        cited=cited,
                        lines=match.group("lines"),
                        held_back=_held_back_reason(host) is not None,
                    )
                )
    return found


def sweepable_citation_sites() -> list[Site]:
    """The population ``D-IMPL-123`` ruled in scope: everything not held back."""
    return [site for site in citation_sites() if not site.held_back]


def test_the_citation_walk_is_not_vacuous() -> None:
    """The scan read files. ``require_populated``'s posture, as a floor."""
    found = scanned_citation_hosts()
    assert len(found) >= MINIMUM_SCANNED_CITATION_HOSTS, (
        f"{GATE_IS_GREEN_NOTE} The citation walk read {len(found)} gated files,"
        f" {MINIMUM_SCANNED_CITATION_HOSTS} expected. A ceiling over a walk that"
        " read nothing reports zero and passes forever, which is the posture"
        " tools/publish_scan.py::require_populated refuses. Either the walk"
        " broke, or files were legitimately removed — if the latter, lower this"
        " constant in the same commit and name the removal in the commit"
        " message."
    )


def test_the_citation_scan_matched_something() -> None:
    """The files the walk read carried citations. Non-vacuity, half two."""
    found = citations_read()
    scan = scan_tree(REPO_ROOT)
    assert len(found) >= MINIMUM_CITATIONS_READ, (
        f"{GATE_IS_GREEN_NOTE} The scan matched {len(found)} citations,"
        f" {MINIMUM_CITATIONS_READ} expected. A walk that reads files and"
        " matches nothing in any of them satisfies the file floor and still"
        " tells the ceiling nothing."
    )
    assert len(found) == scan.total, (
        f"{GATE_IS_GREEN_NOTE} This module enumerated {len(found)} citations"
        f" where `scan_tree()` counted {scan.total}. The two must agree by"
        " construction: `citations_read()` reuses the patterns and the"
        " exemption policy of tools/lints/citations.py precisely so that it"
        " cannot drift from what the gate covers. A mismatch means one of the"
        " reused helpers changed shape."
    )


def test_the_unanchored_python_citation_population_cannot_regrow() -> None:
    """The ceiling. ``D-IMPL-123``'s ruled scope, held at its swept size."""
    found = sweepable_citation_sites()
    assert len(found) <= MAXIMUM_UNANCHORED_PY_CITATIONS, (
        f"{GATE_IS_GREEN_NOTE} {len(found)} unanchored citations of Python"
        f" targets are in D-IMPL-123's scope, ceiling"
        f" {MAXIMUM_UNANCHORED_PY_CITATIONS}. D-IMPL-114 ruled that prose cites"
        " `path.py::Symbol`, because a line anchor is wrong the moment code"
        f" moves. {CEILING_RAISE_INSTRUCTION} Found:"
        + "".join(f"\n  - {site}" for site in found)
    )


def test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident() -> None:
    """The boundary ``D-IMPL-123`` drew is checkable, not asserted.

    Held back rather than swept, and the count is pinned so that a later edit
    quietly pulling one of these hosts into scope — or quietly dropping one out
    of it — is visible. The two directions matter for different reasons: losing
    one means a landed fragment was rewritten, gaining one means the ceiling's
    subject shrank without a ruling.
    """
    held_back = [site for site in citation_sites() if site.held_back]
    hosts = sorted({site.host for site in held_back})
    assert len(held_back) == 13, (
        f"{GATE_IS_GREEN_NOTE} D-IMPL-123 held back 13 citations — 11 in five"
        " landed plan fragments under docs/surface-changes/, plus 2 in the"
        f" assembled docs/SURFACE-CHANGES.md. {len(held_back)} are here now,"
        f" across {hosts}. If a fragment was legitimately edited, that is a"
        " ruling-scope change and belongs in a decision entry, not in this"
        " constant."
    )
    for pattern, _reason in HELD_BACK_HOSTS:
        assert any(fnmatch.fnmatch(host, pattern) for host in hosts), (
            f"{GATE_IS_GREEN_NOTE} No held-back citation matches {pattern!r}"
            " any more. Either the fragment was swept — which D-IMPL-123"
            " forbids — or the pattern no longer names anything and this"
            " exclusion is dead."
        )


def test_cite03_node_id_is_registered_and_enforced() -> None:
    """``D-IMPL-114``'s consequence (1) is discharged, and stays discharged.

    Asserted behaviourally rather than by name: a symbol citation naming
    something the target does not define must produce a ``cite03-node-id``
    finding. A rule that exists as a constant but reaches no citation is the
    convention-not-enforcement shape ``D-IMPL-121`` flagged as worth watching.
    """
    from tools.lints.__main__ import WHOLE_TREE_CHECKERS

    assert "citations" in WHOLE_TREE_CHECKERS, (
        f"{GATE_IS_GREEN_NOTE} The citations checker is no longer registered in"
        " tools/lints/__main__.py::WHOLE_TREE_CHECKERS, so `make lint` no longer"
        " runs it and this module's premise — a green gate — is unverifiable."
    )

    index = repo_index(REPO_ROOT)
    absent = "tools/lints/citations.py" + "::" + "no_such_symbol_exists_here"
    findings = check_source(
        f"# {absent}\n",
        pathlib.Path("tests/invariants/test_citation_coverage.py"),
        REPO_ROOT,
        index,
    )
    assert any(RULE_NODE_ID in finding for finding in findings), (
        f"{GATE_IS_GREEN_NOTE} A citation of a symbol the target does not"
        f" define produced no {RULE_NODE_ID} finding. The rule that makes"
        " `path.py::Symbol` the *enforced* form rather than the *trusted* one"
        " has stopped reaching citations, which would make the whole sweep"
        f" unchecked. Findings were: {findings}"
    )
