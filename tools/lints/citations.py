"""Cross-file citation drift, checked mechanically (SDK-defined; CLAUDE.md §11).

A citation of the form ``path/to/file.py:NNN`` is an *assertion about another
file*, and until this module existed nothing in this repository checked one.
Phase 15.1 watched the class rot four times — twice inside the very commit that
was correcting it — while every other claim class here had a gate: the surface
drift gate, the AST tripwires, schema regeneration, ``docs-strict``. That
asymmetry is what this module removes. Like every other checker here it is
stdlib-only and hand-rolled (D-06) and it blocks (D-07): it is wired into
``python -m tools.lints --all``, which is what ``make lint``, ``make ci`` and
the CI lint job all run.

Three rules
-----------

``cite01-resolves``
    The cited file resolves and every cited line number is inside it. Catches
    a citation of a deleted, renamed or shortened file. Pure arithmetic — it
    cannot be wrong about a file it resolved.

``cite02-anchor``
    When a citation is *anchored* — a backticked code span sits immediately
    before it, separated by nothing but whitespace, opening punctuation and at
    most a locator word (``at``, ``in``, ``line``) — the cited lines must still
    hold what the anchor names. A Python-name anchor resolving to exactly one
    binding in the cited file's module body or a class body (as ``cite03``
    resolves a name) is checked against that symbol's own line span; a dot- or
    kebab-namespaced literal id anchor (an artifact class id, say) is checked
    by looking for the token in the cited lines. A span that is itself a
    citation — a line citation, a ``::`` symbol citation, or a bare ``:NNN``
    continuation — names a location, not what the cited lines hold, so it is
    never an anchor and the citation after it is unanchored (``D-IMPL-378``
    C6; see ``tools/lints/citations.py::anchor_before``).

``cite03-node-id``
    A ``file.py::symbol`` citation must resolve to something of that name in
    that file — a ``def``, a ``class``, an assignment, or a tuple, ``for`` or
    ``with`` target in its module body or in a class body, never a function's
    local (``D-IMPL-378`` repair 1.7: *"take bindings only from the cited
    file's module and class bodies"*; until then the whole file was read, so a
    name bound only inside a function resolved, and a local sharing a cited
    class's name hid its members, Fable G2 F-G2-3). This is the form plan
    15.1-19 migrated *to*, because it does not rot silently under a line
    shift; but an unchecked symbol citation rots silently under a *rename*,
    and checking it is what makes the preferred form the enforced form rather
    than the trusted one. See
    ``tools/lints/citations.py::symbol_spans`` for what "resolve" means.
    A qualified citation, ``file.py::A.b.c``, is checked name by name
    (``D-IMPL-378``, OWED-RULINGS-3 item 7 (a); until then only ``A`` was
    read, so ``A.no_such_member`` passed): ``A`` resolves as above, and each
    later name must be bound in the body of a ``def`` or ``class`` the name
    before it resolved to, which is the name Python's ``__qualname__`` gives a
    definition, with ``<locals>`` dropped. In a class body any binding counts;
    in a function's body only a ``def`` or ``class`` nested in it does, never a
    local variable. An inherited member is therefore a finding: cite it at the
    class that defines it. See ``tools/lints/citations.py::member_verdict``.

What this checker cannot see
----------------------------

Stated at length, because the standing lesson of Phase 15.1 is that a check
that does not say what it is blind to is how a defect class survives five
reviews.

* **Semantics.** ``cite01`` proves a line exists; it does not prove the line
  says what the citer claims. Only ``cite02`` binds a citation to content, and
  only as far as the anchor reaches — it verifies that the cited range lies
  inside the named symbol, never that the sentence around the citation is true.
* **Unanchored citations.** A citation with no adjacent backticked anchor —
  *"the docstring at ``x.py:NNN`` says …"* — gets ``cite01`` only. There is
  nothing to bind, so a line shift inside the cited file is invisible. This is
  the largest blind spot by count and it is reported: ``--report`` prints the
  unanchored total. The remedy is authorial — anchor the citation, or cite the
  symbol with ``::``. A citation whose adjacent span ``cite02`` cannot check
  — a name defined twice, an expression — is exactly as unchecked; ``--report``
  counts it as "anchor not resolvable", and the coverage ratchet counts both
  kinds (``tools/lints/citations.py::checkable_anchor``).
* **Ambiguity.** A bare ``run.py:NNN`` naming one of eleven ``run.py`` files,
  or an anchor matching two ``def``\\ s in the cited file, is counted as
  *unchecked* and is never a finding. Guessing which one was meant is how a
  lint goes red on correct code.
* **A member reached through an assignment.** In ``file.py::A.b`` where
  ``A`` is bound only by an assignment — an instance, or an alias such as
  Hypothesis's ``TestX = Machine.TestCase`` — what ``b`` names depends on a
  value only runtime knows. So does ``A`` when another binding in the module
  body or a class body shares its name (``A = A``; ``A = 1`` in another
  class), because which binding is meant is unknown (the panel's K68). The
  citation is counted unchecked (``--report``'s "member not followable") and
  is never a finding; the count is capped at 0 by a test,
  ``tools/lints/tests/test_citations.py::test_the_unfollowable_member_count_is_capped_at_zero``
  (``D-IMPL-378`` repair 1.7), so such a citation fails the build until it is
  re-cited.
* **A homonym in a class body that defines the member.** The first name is
  looked up in the module body and in every class body together, so where a
  class ``B`` nests its own class ``A`` that defines ``b``, ``file.py::A.b``
  resolves even if the module-level ``A`` defines no ``b``.
* **Extensionless and non-source targets.** ``Makefile:NNN`` and
  ``README:NNN`` are not matched at all — ``CITED_SUFFIXES`` is the whole list
  of what a citation may name.
* **Bare continuations.** ``x.py:NNN`` followed later by a bare ``:MMM`` for
  the same file is matched only at its first half; the continuation carries no
  path and is invisible.
* **Non-citation claims.** A false statement carrying no citation — "the
  manifest deliberately cannot name the author-versioned classes" — is
  invisible at every rule. It is a claim about mechanism, not a pointer, and
  no pointer-checker reaches it. Claims of that kind need a reader, or a test.
* **Code, in Python files.** Inside ``.py`` files only comments and docstrings
  are scanned. A node id inside a code string is test data, not a claim about
  the tree, and flagging it would be exactly the red-on-correct-code failure
  this phase kept regenerating.
* **Quoted claims — deliberately excluded after measurement.** A fourth rule
  was prototyped: where a citation is followed by a *"quoted sentence"* the
  citer says lives there, check the quote against the cited lines. Measured
  tree-wide it matched 7 sites and failed 3, and all 3 were **false**
  positives — two because the citer abridged an RST role (``SDK_ARTIFACT_
  CLASSES`` for ``:data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES```) and
  one because the cited lines are a ``#`` comment block whose prefixes break
  the quoted text. A rule red on correct prose is the defect this gate exists
  to prevent, so it is not shipped. Recorded here rather than dropped
  silently, because "we tried and it does not work" is information and an
  absent rule is not.

Historical citations pass
-------------------------

A citation deliberately scoped to a past state of the tree is *correct* and
must not be flagged. The convention already in the tree is prose: the
``ccf.deployment.binder`` module docstring cites ``load_and_boot``'s signature
by line and then says outright that this is "where it stood in the tree the
correction was written against; the definition has moved since".
``HISTORICITY_MARKERS`` is that convention made mechanical — a citation whose
surrounding lines carry one of those phrases, or a bare git object id, is
exempt from ``cite01`` and ``cite02`` alike.

Scope is configured, and was measured
-------------------------------------

``GATED_TREES`` names the trees walked; it was written after scanning every
top-level tracked directory for citations, not before. ``HISTORICAL_RECORDS``
names what is exempt and why, and ``MAINTAINED_RECORDS`` names what is pulled
back in. The split is *maintained* versus *dated*: a reader is entitled to
expect a maintained file's citations true of the current tree, while a dated
append-only record's citations are a snapshot of the tree at the entry's date.
``docs/DECISIONS.md`` says so in its own text — one entry there is explicitly
"preserved **unedited**" — and a file whose record discipline forbids
correcting a citation cannot be gated on citation freshness. That is a stated
policy with a reason, not an omission; the price is that citation drift inside
those files is out of this gate's reach, which is recorded here so nobody
reads a green gate as a claim about them.
"""

from __future__ import annotations

import ast
import fnmatch
import io
import pathlib
import re
import tokenize
from typing import Iterator, NamedTuple

from tools.lints import format_finding

__all__ = [
    "CITATION",
    "GATED_TREES",
    "HISTORICAL_RECORDS",
    "MAINTAINED_RECORDS",
    "NODE_ID",
    "RULE_ANCHOR",
    "RULE_NODE_ID",
    "RULE_RESOLVES",
    "Scan",
    "anchor_before",
    "check_source",
    "checkable_anchor",
    "check_tree",
    "exemption_reason",
    "member_verdict",
    "scan_tree",
    "scope_bindings",
]

RULE_RESOLVES = "cite01-resolves"
RULE_ANCHOR = "cite02-anchor"
RULE_NODE_ID = "cite03-node-id"

#: Trees walked by the gate. Measured, not assumed: every top-level tracked
#: directory was scanned for citations before this tuple was written. The two
#: absent from it — ``references`` and the repo-root files — were scanned and
#: carry none; they are excluded to keep the walk honest about what it covers
#: rather than because nobody looked.
#:
#: ``archive`` joined in plan ``23-03``, ahead of Phase 23's move of ten
#: condemned example trees into ``archive/examples/`` (``D-03``). Measured on
#: the pre-move tree, **252** of the 1109 hosts this walk reads live inside
#: those ten trees; without the member the walk would read 857 after the move
#: and ``tests/invariants/test_citation_coverage.py::MINIMUM_SCANNED_CITATION_HOSTS``
#: would go red in a way that reads like a legitimate removal. Archiving a file
#: does not make its citations stop being claims about this tree.
#:
#: The member is the top-level ``archive`` rather than ``archive/examples``,
#: matching this tuple's existing shape (tree names, not path prefixes) and
#: ``tools/lints/__main__.py::LINTED_TREES``'s spelling. For a walk whose
#: default is default-allow, the inheriting spelling is the safe one; the
#: publication allowlist in ``tools/publish_scan.py`` deliberately took the
#: narrow one for the opposite reason. Guarded by
#: ``tools/lints/tests/test_scope.py``.
GATED_TREES: tuple[str, ...] = (
    "src",
    "runtime",
    "tools",
    "tests",
    "examples",
    "public",
    "docs",
    "perf",
    ".planning",
    ".github",
    "archive",
)

#: Files whose citations are dated snapshots rather than maintained pointers,
#: each with the reason it is exempt. Matched with :func:`fnmatch.fnmatch`
#: against the repo-relative POSIX path, where ``*`` spans ``/`` as well.
#:
#: The test of membership is *record discipline*, not tree: a file that may not
#: be edited to correct a citation cannot be gated on citation freshness.
HISTORICAL_RECORDS: dict[str, str] = {
    "docs/DECISIONS.md": (
        "dated append-only decision log — entries are corrected by appending a"
        " new dated entry, never by editing, and one entry is explicitly"
        " 'preserved unedited'; its citations are snapshots of the tree at the"
        " entry's own date"
    ),
    "docs/CCF_Whitepaper_1-2.md": (
        "the canonical specification (CLAUDE.md §2) — a frozen external"
        " document, not a description of this tree"
    ),
    "docs/PHASE_*.md": (
        "dated phase-gate records; each states its triage as it stood at its"
        " own checkpoint"
    ),
    ".planning/phases/*": (
        "phase documents are dated records of a moment — a plan records intent"
        " at its date, a SUMMARY what it measured when it ran, a review or"
        " verification what the tree said that day. See MAINTAINED_RECORDS for"
        " the exception"
    ),
    # D-IMPL-378 ruling C6 (c) (Dave): "exempt the review record and the
    # handoff (46 citations) and convert the three documents security fixes
    # still edit (316) once the lanes stop editing them". Measured on
    # dl-378-integ @ 8cfe77b2, the two exemptions take 46 unanchored citations
    # of Python targets out of the ratchet's population, and 122 citations out
    # of this gate's reach, 41 of which it checked (40 of the hand-off's
    # `::Symbol` citations among them).
    "docs/V1.0.2-SPEC-REVIEWS.md": (
        "the v1.0.2 spec's review record: the panel's and the internal"
        " review's findings with their dispositions (2026-09-25, last edited"
        " 2026-09-26); a dated record by D-IMPL-378 ruling C6 (c), so its"
        " citations are snapshots of the tree it reviewed"
    ),
    "docs/superpowers/plans/2026-09-27-wave-2-HANDOFF.md": (
        "the Wave 2 hand-off, written 2026-09-27 to survive a cleared context"
        " and amended until 2026-10-01; a dated record by D-IMPL-378 ruling"
        " C6 (c), so its citations are snapshots of the tree that wave worked on"
    ),
}

#: Pulled back into the gate despite matching a HISTORICAL_RECORDS pattern.
#: ``deferred-items.md`` is the live phase-to-phase hand-off contract: every
#: inheriting phase amends it in place, it states its citations in the present
#: tense, and Phase 16 reads it as authoritative. Exactly the file whose
#: pointers must be true now.
MAINTAINED_RECORDS: tuple[str, ...] = (".planning/phases/*/deferred-items.md",)

#: Suffixes of files this checker reads citations *out of*.
SCANNED_SUFFIXES: frozenset[str] = frozenset({".py", ".md", ".yaml", ".yml"})

#: Suffixes a citation may name.
CITED_SUFFIXES: tuple[str, ...] = (
    "py",
    "md",
    "yaml",
    "yml",
    "json",
    "toml",
    "txt",
    "cfg",
    "ini",
    "sh",
)

#: Directories never worth walking.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        # Agent worktrees hold a full copy of the tree. Walking them makes
        # every basename resolve to N+1 paths, and an ambiguous basename is
        # DROPPED from the sweep rather than checked -- so a live worktree
        # silently turns this gate vacuous. Measured 2026-08-15 (DEF-17-04):
        # six worktrees put seven entries under one basename and hid two real
        # unanchored citations behind a green run.
        ".claude",
        ".venv",
        "venv",
        "build",
        "dist",
        "site",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
    }
)

_SUFFIX_ALT = "|".join(CITED_SUFFIXES)

#: A line citation: ``path/to/file.py:12``, ``file.py:12-34``, ``x.py:12,34``.
CITATION = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.(?:" + _SUFFIX_ALT + r"))"
    r":(?P<lines>\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)(?![\w-])"
)

#: A symbol citation — the rot-resistant form, checked rather than trusted.
NODE_ID = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.py)::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"
)

#: The dotted member path after a symbol citation's first name: the ``.b.c``
#: of ``file.py::A.b.c``. Matched where ``NODE_ID`` ends rather than folded
#: into it, so ``NODE_ID``'s span and groups, which other modules read, are
#: unchanged.
_MEMBER_TAIL = re.compile(r"(?:\.[A-Za-z_][A-Za-z0-9_]*)+")

#: What a qualified name can step into: a definition with a body of its own.
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

#: A function. The names its body binds are its locals: a citation never
#: resolves through one, and a definition nested in it is reached only by
#: naming the function first (``D-IMPL-378`` repair 1.7).
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)

#: A backticked span: RST ``x`` and Markdown `x` alike. Newline-free, so a
#: span never straddles two lines.
_BACKTICKED = re.compile(r"(?P<ticks>`+)(?P<body>[^`\n]+)(?P=ticks)")

#: The bare line-number continuation of a line citation — the ``:394`` after a
#: cited path — which ``CITATION`` does not match because it carries no path
#: (the "Bare continuations" entry in the module docstring).
_CONTINUATION = re.compile(r":\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*(?![\w-])")

#: Punctuation that may sit between an anchor and the citation it anchors.
#: ``:`` and ``=`` are deliberately absent: ``rule: site`` and ``name = value``
#: are *labelling* constructions, where the backticked span before the colon
#: names something other than what lives at the cited lines.
_GAP_PUNCT = re.compile(r"[\s`(\[,;—–-]+")

#: The only words allowed inside an anchor gap. "X at Y", "X in Y", "X on line
#: Y" are locating constructions; anything else means the backticked span is
#: not about the citation and the citation is left unanchored rather than bound
#: to the wrong thing.
_GAP_WORDS: frozenset[str] = frozenset(
    {"at", "in", "on", "see", "line", "lines", "defined", "declared", "now"}
)

#: The convention that marks a citation as a snapshot of a past tree. The
#: phrases are the wording already in use (``ccf.deployment.binder``'s module
#: docstring; ``docs/PHASE_I4_GATE.md``); the last two admit an explicit commit
#: scope, which is how a verification report writes one.
HISTORICITY_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:it|they) stood\b", re.IGNORECASE),
    re.compile(r"\bwritten against\b", re.IGNORECASE),
    re.compile(r"\b(?:has|have) (?:since )?moved\b", re.IGNORECASE),
    re.compile(r"\b(?:correct|accurate|true) (?:as of|at)\b", re.IGNORECASE),
    re.compile(r"\bat commit\b", re.IGNORECASE),
    re.compile(r"`[0-9a-f]{7,40}`"),
)

#: How many lines either side of a citation are joined before the citation's
#: own sentence is cut out of them. Two, because the convention's instance in
#: ``ccf.deployment.binder`` wraps one sentence across three lines.
#:
#: The marker must then land in *the citation's own sentence*, not merely
#: nearby. Nearness is not enough: one line of `.planning/REQUIREMENTS.md` is a
#: four-thousand-character paragraph that opens by saying an *earlier* record's
#: line numbers "have since moved" and then makes six present-tense citations
#: of its own. A line-scoped marker exempts all six; a sentence-scoped marker
#: exempts none, which is right.
MARKER_WINDOW = 2

#: What ends a sentence for marker scoping: terminal punctuation followed by
#: whitespace. Deliberately crude — a mis-split truncates the window, which can
#: only cost a marker, never invent one.
_SENTENCE_BREAK = re.compile(r"[.!?]\s")

#: An anchor that is a plain Python name, optionally dotted, optionally
#: followed by a call signature — ``foo``, ``A.b``, ``foo(*, x) -> None``.
_SYMBOLISH = re.compile(
    r"^(?::[a-z]+:)?[~!]?(?P<dotted>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
    r"\s*(?:\(|$)"
)

#: An anchor that is a dot- or kebab-namespaced literal id rather than a Python
#: name — an artifact class id, a rule token. Checked as text, since it names
#: no ``def``.
_TOKENISH = re.compile(r"^[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)+$")


class Scan(NamedTuple):
    """One tree-wide run's findings and its coverage.

    ``findings`` are citations that failed a rule. The rest is what the run
    could *not* check — an unresolvable path, an ambiguous bare filename, an
    anchorless citation — reported rather than hidden, because the coverage of
    a check is part of what the check claims.
    """

    findings: list[str]
    total: int
    checked: int
    historical: int
    unresolved_path: int
    ambiguous_path: int
    no_anchor: int
    unusable_anchor: int
    exempt_files: int
    scanned_files: int
    unfollowable_member: int


def exemption_reason(rel: str) -> str | None:
    """Why `rel` is out of the gate's scope, or ``None`` when it is gated."""
    if any(fnmatch.fnmatch(rel, keep) for keep in MAINTAINED_RECORDS):
        return None
    for pattern, reason in HISTORICAL_RECORDS.items():
        if fnmatch.fnmatch(rel, pattern):
            return reason
    return None


def iter_scanned_files(base: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield every scannable file under the gated trees of `base`."""
    for tree in GATED_TREES:
        root = base / tree
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in SCANNED_SUFFIXES or not path.is_file():
                continue
            # Relative to `base`, never the absolute path: a checkout whose own
            # root sits inside a skipped directory -- an agent worktree under
            # `.claude/` is the live case -- would otherwise match every file
            # and walk NOTHING. Measured 2026-08-15 (DEF-17-06).
            if any(part in SKIP_DIRS for part in path.relative_to(base).parts):
                continue
            yield path


def repo_index(base: pathlib.Path) -> dict[str, list[str]]:
    """Map every repo file's basename to the repo-relative paths carrying it."""
    index: dict[str, list[str]] = {}
    for path in base.rglob("*"):
        # Relative to `base` -- see the note in `iter_scanned_files`.
        if (
            any(part in SKIP_DIRS for part in path.relative_to(base).parts)
            or not path.is_file()
        ):
            continue
        index.setdefault(path.name, []).append(path.relative_to(base).as_posix())
    return index


def prose_lines(source: str) -> frozenset[int] | None:
    """Line numbers carrying comments or docstrings, or ``None`` for all lines.

    Only Python files distinguish prose from code. ``None`` means "no
    distinction to draw" — every line of a Markdown or YAML file is prose for
    this purpose.
    """
    lines: set[int] = set()
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                lines.update(range(token.start[0], token.end[0] + 1))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            lines.update(
                range(first.lineno, (first.end_lineno or first.lineno) + 1)
            )
    return frozenset(lines)


def parse_line_spec(spec: str) -> list[int]:
    """Every line number named by a ``12`` / ``12-34`` / ``12,34`` citation tail."""
    numbers: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo, _, hi = part.partition("-")
            numbers.extend((int(lo), int(hi)))
        else:
            numbers.append(int(part))
    return numbers


def resolve_cited(
    cited: str, base: pathlib.Path, index: dict[str, list[str]]
) -> tuple[pathlib.Path | None, bool]:
    """Resolve a cited path; returns ``(path, ambiguous)``.

    A path that exists as written wins outright. Otherwise the citation is a
    suffix — ``manifest.py``, ``deployment/manifest.py`` — and resolves only
    when exactly one repo file ends with it. Two candidates is ambiguity, and
    ambiguity is never a finding.
    """
    direct = base / cited
    if direct.is_file():
        return direct, False
    name = cited.rsplit("/", 1)[-1]
    candidates = [
        c for c in index.get(name, ()) if c == cited or c.endswith("/" + cited)
    ]
    if len(candidates) == 1:
        return base / candidates[0], False
    return None, len(candidates) > 1


def _gap_is_an_anchor_gap(gap: str) -> bool:
    """True when `gap` only locates: punctuation and at most locator words."""
    for word in _GAP_PUNCT.sub(" ", gap).split():
        if word.lower() not in _GAP_WORDS:
            return False
    return True


def _points_elsewhere(span: str) -> bool:
    """True when a backticked span is itself a citation rather than a name.

    A line citation, a ``::`` symbol citation, or a bare ``:NNN``
    continuation points at a location. The module docstring defines an anchor
    as the thing *the cited lines must still hold*; a pointer names nothing
    those lines hold, so it is never one.
    """
    return bool(
        CITATION.match(span) or NODE_ID.match(span) or _CONTINUATION.match(span)
    )


def anchor_before(line: str, start: int) -> str | None:
    """The anchor immediately preceding the citation at `start`, or ``None``.

    The backticked span immediately before the citation, when only an anchor
    gap separates them and the span is not itself a citation. Returning the
    neighboring citation as the anchor was the blind spot ``D-IMPL-378`` C6
    ruled on: the citation after it then counted as anchored, and the
    coverage ratchet, which skips anchored citations, could not see it.
    """
    best: str | None = None
    for match in _BACKTICKED.finditer(line):
        if match.start() >= start:
            break
        if match.end() > start:  # the span wrapping the citation itself
            continue
        body = match.group("body").strip()
        best = (
            body
            if _gap_is_an_anchor_gap(line[match.end() : start])
            and not _points_elsewhere(body)
            else None
        )
    return best


def symbol_spans(source: str, path: pathlib.Path) -> dict[str, list[tuple[int, int]]]:
    """Line spans of every binding :func:`_definitions` takes, by name.

    That is, of the module body and every class body; never a function's
    local. A ``def``'s span runs from its first decorator (or its ``def``
    line) to its last line, so a citation of any line inside the body is
    "inside the symbol". A binding's span is the statement that binds it.
    """
    spans: dict[str, list[tuple[int, int]]] = {}
    for name, nodes in _definitions(source, path).items():
        for node in nodes:
            first = node.lineno
            if isinstance(node, _SCOPES):
                first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            spans.setdefault(name, []).append((first, node.end_lineno or node.lineno))
    return spans


def _target_names(target: ast.expr) -> list[str]:
    """The names an assignment, ``for`` or ``with`` target binds.

    A plain name, or every name a tuple or list target unpacks to, nested and
    starred ones included. An attribute or subscript target binds no name in
    the scope it sits in.
    """
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for element in target.elts for name in _target_names(element)]
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return []


def _binds(node: ast.AST) -> list[str]:
    """The names `node` binds, of the kinds ``cite03`` resolves.

    A ``def`` or a ``class``; and every name an assignment, an annotation, a
    ``for`` loop or a ``with ... as`` binds, a tuple or list target unpacked
    (``D-IMPL-378`` repair 1.7, *"let tuple, `for` and `with` targets bind"*;
    until then only a plain-name assignment or annotation target bound, so a
    member bound any other way was reported missing, Fable G2 F-G2-3 (b)).
    :func:`_definitions` (and so :func:`symbol_spans`) and
    :func:`scope_bindings` both read these kinds from here, so what a first
    name and a member may resolve to cannot drift apart.
    """
    if isinstance(node, _SCOPES):
        return [node.name]
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, (ast.AnnAssign, ast.For, ast.AsyncFor)):
        targets = [node.target]
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        targets = [
            item.optional_vars for item in node.items if item.optional_vars is not None
        ]
    else:
        return []
    return [name for target in targets for name in _target_names(target)]


def _own_statements(scope: ast.AST) -> Iterator[ast.stmt]:
    """Every statement in `scope`'s own body.

    At any depth of the compound statements in the body (an ``if
    TYPE_CHECKING:`` block, a ``try``, a loop or ``with`` body), and never
    inside a nested ``def`` or ``class``, whose body is its own scope.
    """
    pending: list[ast.AST] = list(getattr(scope, "body", []))
    while pending:
        node = pending.pop()
        if isinstance(node, ast.stmt):
            yield node
        if isinstance(node, _SCOPES):
            continue
        pending.extend(
            child
            for child in ast.iter_child_nodes(node)
            if isinstance(child, (ast.stmt, ast.ExceptHandler, ast.match_case))
        )


def _definitions(source: str, path: pathlib.Path) -> dict[str, list[ast.stmt]]:
    """Every statement binding a name in `source`'s module or class bodies.

    By name: the module body, and the body of every class reached from it
    through class bodies alone — never a function's body, whose names are its
    locals (``D-IMPL-378`` repair 1.7, *"take bindings only from the cited
    file's module and class bodies"*). Until the repair this walked the whole
    file: a local sharing a cited class's name made the class's members
    unfollowable (Fable G2 F-G2-3 (a)), and a name bound only inside a
    function resolved as a first name.
    """
    found: dict[str, list[ast.stmt]] = {}
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return found
    pending: list[ast.AST] = [tree]
    while pending:
        scope = pending.pop()
        for node in _own_statements(scope):
            for name in _binds(node):
                found.setdefault(name, []).append(node)
            if isinstance(node, ast.ClassDef):  # a function's body is never read
                pending.append(node)
    return found


def scope_bindings(scope: ast.AST) -> dict[str, list[ast.stmt]]:
    """The names bound in `scope`'s own body, by name.

    In the statements :func:`_own_statements` yields. In a module or class
    body, every kind :func:`_binds` names. In a function's body, only the
    ``def`` and ``class`` statements nested in it — what Python's
    ``__qualname__`` names, with ``<locals>`` dropped — and never a local
    variable, which no citation resolves through (``D-IMPL-378`` repair 1.7,
    *"never a function's local"*). A name set on an instance (``self.x =
    ...``) is not bound in a class body, and an inherited member is bound in
    its base's body, not here.
    """
    bound: dict[str, list[ast.stmt]] = {}
    for node in _own_statements(scope):
        if isinstance(scope, _FUNCTIONS) and not isinstance(node, _SCOPES):
            continue  # a function's local variable
        for name in _binds(node):
            bound.setdefault(name, []).append(node)
    return bound


def member_verdict(
    definitions: dict[str, list[ast.stmt]], qualified: list[str]
) -> tuple[bool | None, int]:
    """Whether a qualified name resolves, name by name, and where it stopped.

    `definitions` maps each name to every node binding it in the cited file's
    module body or a class body (:func:`_definitions`); `qualified` is ``["A",
    "b", "c"]`` for ``file.py::A.b.c``. The first name resolves through those
    bindings. Each later name must be bound (:func:`scope_bindings`) in the
    body of a ``def`` or ``class`` the name before it resolved to — in a
    function's body, as a ``def`` or ``class`` nested in it, never a local
    variable.

    Returns ``(True, len(qualified))`` when every name resolves; ``(False,
    i)`` when ``qualified[i]`` is bound in none of the bodies it was looked
    for in, which is a finding; and ``(None, i)`` when it could not be looked
    for, because the name before it is bound by an assignment, whose value
    only runtime knows. ``(False, 0)`` means the first name is not bound at
    all.
    """
    current = definitions.get(qualified[0], [])
    if not current:
        return False, 0
    for i, name in enumerate(qualified[1:], 1):
        scopes = [node for node in current if isinstance(node, _SCOPES)]
        found = [hit for scope in scopes for hit in scope_bindings(scope).get(name, [])]
        if not found:
            return (None if len(scopes) < len(current) else False), i
        current = found
    return True, len(qualified)


def citation_sentence(lines: list[str], lineno: int, column: int) -> str:
    """The sentence carrying the citation at `lineno`/`column`."""
    lo = max(0, lineno - 1 - MARKER_WINDOW)
    before = lines[lo : lineno - 1]
    window = " ".join(before + lines[lineno - 1 : lineno + MARKER_WINDOW])
    offset = sum(len(line) + 1 for line in before) + column

    start = 0
    for match in _SENTENCE_BREAK.finditer(window, 0, offset):
        start = match.end()
    end_match = _SENTENCE_BREAK.search(window, offset)
    end = end_match.end() if end_match else len(window)
    return window[start:end]


def is_historical(lines: list[str], lineno: int, column: int) -> bool:
    """True when the citation's own sentence carries a historicity marker."""
    sentence = citation_sentence(lines, lineno, column)
    return any(marker.search(sentence) for marker in HISTORICITY_MARKERS)


class _Tree:
    """Lazily-read cited files: source, lines and symbol spans, once each."""

    def __init__(self) -> None:
        self._source: dict[str, str] = {}
        self._spans: dict[str, dict[str, list[tuple[int, int]]]] = {}
        self._definitions: dict[str, dict[str, list[ast.stmt]]] = {}

    def source(self, path: pathlib.Path) -> str:
        key = str(path)
        if key not in self._source:
            self._source[key] = path.read_text(encoding="utf-8", errors="replace")
        return self._source[key]

    def spans(self, path: pathlib.Path) -> dict[str, list[tuple[int, int]]]:
        key = str(path)
        if key not in self._spans:
            self._spans[key] = symbol_spans(self.source(path), path)
        return self._spans[key]

    def definitions(self, path: pathlib.Path) -> dict[str, list[ast.stmt]]:
        key = str(path)
        if key not in self._definitions:
            self._definitions[key] = _definitions(self.source(path), path)
        return self._definitions[key]


def _anchor_verdict(
    anchor: str, target: pathlib.Path, numbers: list[int], trees: _Tree
) -> bool | None:
    """True/False when the anchor is checkable, ``None`` when it is not."""
    lo, hi = min(numbers), max(numbers)

    symbolish = _SYMBOLISH.match(anchor)
    if symbolish and target.suffix == ".py":
        name = symbolish.group("dotted").rsplit(".", 1)[-1]
        spans = trees.spans(target).get(name, [])
        if len(spans) != 1:
            return None
        start, end = spans[0]
        return start <= lo and hi <= end

    if _TOKENISH.match(anchor):
        body = trees.source(target).splitlines()
        return anchor in "\n".join(body[lo - 1 : hi])

    return None


def checkable_anchor(
    line: str,
    start: int,
    target: pathlib.Path,
    numbers: list[int],
    trees: _Tree | None = None,
) -> str | None:
    """The anchor ``cite02`` checks the citation at `start` against, or ``None``.

    ``None`` when :func:`anchor_before` finds no anchor, and also when the
    anchor it finds is one ``cite02`` cannot check against `target`: a name
    defined there zero times or more than once, or a span that is neither a
    Python name nor a namespaced id. ``check_source`` counts that second case
    as ``unusable_anchor``. Both leave the citation unchecked, which is the
    population ``D-IMPL-123`` puts under the coverage ratchet — *"citations the
    checker declines to check because they carry no anchor to check against"*
    (``tests/invariants/test_citation_coverage.py::citation_sites``).
    """
    anchor = anchor_before(line, start)
    if anchor is None:
        return None
    cache = trees if trees is not None else _Tree()
    if _anchor_verdict(anchor, target, numbers, cache) is None:
        return None
    return anchor


def check_source(
    source: str,
    path: pathlib.Path,
    base: pathlib.Path,
    index: dict[str, list[str]],
    trees: _Tree | None = None,
    tally: dict[str, int] | None = None,
) -> list[str]:
    """Check every citation in `source`, attributed to `path`.

    `path` is the repo-relative path the findings are reported against; `base`
    is the repo root the citations resolve inside.
    """
    counts = tally if tally is not None else {}
    cache = trees if trees is not None else _Tree()

    def bump(key: str) -> None:
        counts[key] = counts.get(key, 0) + 1

    lines = source.splitlines()
    prose = prose_lines(source) if path.suffix == ".py" else None
    findings: list[str] = []

    for lineno, line in enumerate(lines, 1):
        if prose is not None and lineno not in prose:
            continue

        for match in NODE_ID.finditer(line):
            bump("total")
            cited, symbol = match.group("path"), match.group("symbol")
            target, ambiguous = resolve_cited(cited, base, index)
            if target is None:
                # An unresolvable path in a symbol citation is far more often a
                # placeholder in prose (`module.py::test_name`) than a broken
                # pointer, so it is unchecked rather than a finding.
                bump("ambiguous_path" if ambiguous else "unresolved_path")
                continue
            if symbol not in cache.spans(target):
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_NODE_ID,
                        f"cites {cited}::{symbol}, but {cited} defines no"
                        f" {symbol!r} — the symbol was renamed or removed;"
                        " re-resolve it before citing it",
                    )
                )
                continue
            tail = _MEMBER_TAIL.match(line, match.end())
            if tail is None:
                bump("checked")
                continue
            qualified = [symbol, *tail.group(0)[1:].split(".")]
            verdict, stop = member_verdict(cache.definitions(target), qualified)
            if verdict is None:
                bump("unfollowable_member")
            elif verdict:
                bump("checked")
            else:
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_NODE_ID,
                        f"cites {cited}::{'.'.join(qualified)}, but"
                        f" {'.'.join(qualified[:stop])} in {cited} defines no"
                        f" {qualified[stop]!r} — the member was renamed or"
                        " removed, or is inherited (cite it at the class that"
                        " defines it); re-resolve it before citing it",
                    )
                )

        for match in CITATION.finditer(line):
            bump("total")
            cited = match.group("path")
            if is_historical(lines, lineno, match.start()):
                bump("historical")
                continue
            target, ambiguous = resolve_cited(cited, base, index)
            if target is None:
                bump("ambiguous_path" if ambiguous else "unresolved_path")
                continue

            target_lines = cache.source(target).splitlines()
            numbers = parse_line_spec(match.group("lines"))
            if max(numbers) > len(target_lines):
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_RESOLVES,
                        f"cites {cited}:{match.group('lines')}, but that file"
                        f" has {len(target_lines)} lines",
                    )
                )
                continue

            anchor = anchor_before(line, match.start())
            if anchor is None:
                bump("no_anchor")
                continue

            verdict = _anchor_verdict(anchor, target, numbers, cache)
            if verdict is None:
                bump("unusable_anchor")
            elif verdict:
                bump("checked")
            else:
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_ANCHOR,
                        f"cites {cited}:{match.group('lines')} for {anchor!r},"
                        " which is not what those lines hold — re-read the"
                        " file and re-cite, or cite the symbol with `::`",
                    )
                )

    return findings


def scan_tree(base: pathlib.Path) -> Scan:
    """Run every rule over `base`, returning findings and coverage."""
    index = repo_index(base)
    trees = _Tree()
    tally: dict[str, int] = {}
    findings: list[str] = []
    exempt = 0
    scanned = 0
    for path in iter_scanned_files(base):
        rel = path.relative_to(base).as_posix()
        if exemption_reason(rel) is not None:
            exempt += 1
            continue
        scanned += 1
        findings.extend(
            check_source(
                path.read_text(encoding="utf-8", errors="replace"),
                path.relative_to(base),
                base,
                index,
                trees,
                tally,
            )
        )
    return Scan(
        findings=sorted(findings),
        total=tally.get("total", 0),
        checked=tally.get("checked", 0),
        historical=tally.get("historical", 0),
        unresolved_path=tally.get("unresolved_path", 0),
        ambiguous_path=tally.get("ambiguous_path", 0),
        no_anchor=tally.get("no_anchor", 0),
        unusable_anchor=tally.get("unusable_anchor", 0),
        exempt_files=exempt,
        scanned_files=scanned,
        unfollowable_member=tally.get("unfollowable_member", 0),
    )


def check_tree(base: pathlib.Path) -> list[str]:
    """The gate entrypoint: findings only, in the shared finding format."""
    return scan_tree(base).findings
