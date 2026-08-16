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
    ``def`` / ``class`` / module-level binding in the cited file is checked
    against that symbol's own line span; a dot- or kebab-namespaced literal id
    anchor (an artifact class id, say) is checked by looking for the token in
    the cited lines.

``cite03-node-id``
    A ``file.py::symbol`` citation must resolve to something of that name in
    that file — a ``def``, a ``class``, or a module-level binding. This is the
    form plan 15.1-19 migrated *to*, because it does not rot silently under a
    line shift; but an unchecked symbol citation rots silently under a
    *rename*, and checking it is what makes the preferred form the enforced
    form rather than the trusted one. See
    ``tools/lints/citations.py::symbol_spans`` for what "resolve" means.

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
  symbol with ``::``.
* **Ambiguity.** A bare ``run.py:NNN`` naming one of eleven ``run.py`` files,
  or an anchor matching two ``def``\\ s in the cited file, is counted as
  *unchecked* and is never a finding. Guessing which one was meant is how a
  lint goes red on correct code.
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
    "check_source",
    "check_tree",
    "exemption_reason",
    "scan_tree",
]

RULE_RESOLVES = "cite01-resolves"
RULE_ANCHOR = "cite02-anchor"
RULE_NODE_ID = "cite03-node-id"

#: Trees walked by the gate. Measured, not assumed: every top-level tracked
#: directory was scanned for citations before this tuple was written. The two
#: absent from it — ``references`` and the repo-root files — were scanned and
#: carry none; they are excluded to keep the walk honest about what it covers
#: rather than because nobody looked.
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

#: A backticked span: RST ``x`` and Markdown `x` alike. Newline-free, so a
#: span never straddles two lines.
_BACKTICKED = re.compile(r"(?P<ticks>`+)(?P<body>[^`\n]+)(?P=ticks)")

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
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            yield path


def repo_index(base: pathlib.Path) -> dict[str, list[str]]:
    """Map every repo file's basename to the repo-relative paths carrying it."""
    index: dict[str, list[str]] = {}
    for path in base.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
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


def anchor_before(line: str, start: int) -> str | None:
    """The backticked span immediately preceding the citation at `start`."""
    best: str | None = None
    for match in _BACKTICKED.finditer(line):
        if match.start() >= start:
            break
        if match.end() > start:  # the span wrapping the citation itself
            continue
        best = (
            match.group("body").strip()
            if _gap_is_an_anchor_gap(line[match.end() : start])
            else None
        )
    return best


def symbol_spans(source: str, path: pathlib.Path) -> dict[str, list[tuple[int, int]]]:
    """Line spans of every ``def`` / ``class`` / module-level binding, by name.

    A ``def``'s span runs from its first decorator (or its ``def`` line) to its
    last line, so a citation of any line inside the body is "inside the
    symbol". A binding's span is the assignment statement.
    """
    spans: dict[str, list[tuple[int, int]]] = {}
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return spans
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            spans.setdefault(node.name, []).append(
                (first, node.end_lineno or node.lineno)
            )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    spans.setdefault(target.id, []).append(
                        (node.lineno, node.end_lineno or node.lineno)
                    )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            spans.setdefault(node.target.id, []).append(
                (node.lineno, node.end_lineno or node.lineno)
            )
    return spans


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
            if symbol in cache.spans(target):
                bump("checked")
                continue
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
    )


def check_tree(base: pathlib.Path) -> list[str]:
    """The gate entrypoint: findings only, in the shared finding format."""
    return scan_tree(base).findings
