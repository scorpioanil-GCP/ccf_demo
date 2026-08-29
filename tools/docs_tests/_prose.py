"""Paragraph-scoped reading of the published tree, extracted once.

**Why this module exists at all.** Three gates in this package need to ask a
question of the form *"does any published paragraph say X without also saying
Y?"* — the Gate-2 wording gate, the stale-path gate, and the documented-command
gate. `16-PATTERNS.md` § *No Analog Found* records that nothing in the tree did
paragraph-scoped matching over ``public/**/*.md``: two halves existed —
`tools.publish_scan.normalize` knows how to strip markup, and
`tools.lints.citations.citation_sentence` knows how to join a window and map an
offset back into it — and this module is their composition. Extracted once
rather than inlined three times, because three copies of a scoping rule drift
into three different scoping rules.

**Why paragraph scoping rather than line scoping.** RESEARCH P-2: Phase 15.1
under-counted the same sweep six times, and the fix that finally worked was
paragraph-scoping. The failure mode is structural, not incidental. Markdown
prose wraps at the author's whim, so a claim and its qualification routinely
land on different lines::

    Comparing them establishes **assembly-path integrity** — the product
    served was assembled by the path the deployment claimed. It is not an
    independent check on the claim itself: the engine builds its invoked set
    and its execution steps in one loop over the same operator plan.

A line-scoped scan for "independent" finds line 3 and reports a page that is
saying exactly the right thing; a line-scoped scan for the correction finds
line 1 and misses that the qualification two lines down is what makes the
paragraph correct. Neither direction is recoverable by widening the regex,
because the unit of meaning is the paragraph and the unit of matching was the
line. `tools.lints.citations.MARKER_WINDOW` carries the same finding with a
measured example from a different tree.

**The warning sign.** A plan step spelled ``grep -rn "<phrase>" public/`` is the
thing this module exists to remove. If a new gate reaches for a line-scoped
regex over an unjoined file, it has reintroduced the defect that cost Phase
15.1 six sweeps.

**Casing is preserved.** Callers want case-insensitive *matching*, which is a
property of the match and not of the corpus; lowercasing here would make it
impossible for a caller to report an offending phrase as the page actually
spells it. This is the one deliberate divergence from
`tools.publish_scan.normalize`, which lowercases because its consumer is a
shingle set.

**Fenced blocks are marked, not dropped.** A fenced code block is not running
prose, so the wording gates must skip it; but ``make`` invocations live almost
exclusively in fenced ``sh`` blocks, so the command gate must read it. Both are
served by emitting fenced regions as paragraphs carrying ``fenced=True``
rather than by deciding here which consumer is right.
"""

from __future__ import annotations

import pathlib
import re
from collections.abc import Iterable, Iterator
from typing import NamedTuple

#: The repo root, resolved from this file rather than from the process CWD.
#: A CWD-relative walk yields zero pages off-root and turns every gate built on
#: this module into a test that passes over nothing — WR-04's exact failure,
#: recorded at
#: `tools/publish_scan_tests/test_docstring_leaks.py::test_the_walk_does_not_depend_on_the_process_cwd`.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The published tree. D-01: `public/` is the only tree mkdocs reads, so it is
#: the whole corpus a "published prose" gate has jurisdiction over.
PUBLIC_DIR = REPO_ROOT / "public"

#: HTML tags go first so an element boundary inside a sentence cannot split a
#: phrase; backtick code spans go next so a rendered identifier does not glue
#: two unrelated words together. Both borrowed verbatim from
#: `tools.publish_scan.normalize`, whose docstring states the ordering reason.
_TAG_RE = re.compile(r"<[^>]*>")
_CODE_SPAN_RE = re.compile(r"`[^`]*`")

#: A fence opener or closer: three-or-more backticks or tildes at line start,
#: optionally followed by an info string. Matching the whole line is what lets a
#: closing fence be told from an opening one — the closer carries no info string.
_FENCE_RE = re.compile(r"^\s*(?P<marker>`{3,}|~{3,})\s*(?P<info>\S*)")


class Paragraph(NamedTuple):
    """One paragraph of a published page.

    Attributes:
        text: The paragraph's running prose — non-blank lines joined,
            HTML tags and backtick code spans removed, whitespace collapsed,
            **original casing preserved**. This is what a wording gate matches
            against.
        lineno: 1-based line number of the paragraph's first line, so a failure
            can be reported as ``page:line`` and opened directly.
        raw: The same lines joined and whitespace-collapsed with **nothing
            stripped**. Code spans survive here, which is the only way a gate
            can see a command an author wrote as `` `make ci` ``.
        fenced: Whether this paragraph is a fenced code block rather than
            running prose.
        info: The fence's info string (``sh``, ``py``, ``yaml``, ...) when
            ``fenced`` is true, otherwise the empty string.
    """

    text: str
    lineno: int
    raw: str
    fenced: bool
    info: str


def strip_markup(text: str) -> str:
    """`text` with HTML tags and backtick code spans removed, casing intact."""
    return _CODE_SPAN_RE.sub(" ", _TAG_RE.sub(" ", text))


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _emit(lines: list[str], lineno: int, *, fenced: bool, info: str) -> Paragraph:
    joined = " ".join(lines)
    return Paragraph(
        text=_collapse(strip_markup(joined)),
        lineno=lineno,
        raw=_collapse(joined),
        fenced=fenced,
        info=info,
    )


def paragraphs(text: str) -> list[Paragraph]:
    """Every paragraph in one page's `text`, in document order.

    Outside a fence, a paragraph is a run of non-blank lines. A fenced block is
    emitted whole — blank lines inside it do not split it, because a blank line
    in a shell transcript is not a paragraph break.

    An unterminated fence is emitted as a fenced paragraph at end of file
    rather than discarded: the strict build would reject such a page anyway,
    and silently dropping the tail is how a gate comes to scan less than it
    reports.
    """
    found: list[Paragraph] = []
    buffer: list[str] = []
    start = 0
    fence: str | None = None
    info = ""

    for lineno, line in enumerate(text.splitlines(), start=1):
        match = _FENCE_RE.match(line)
        if fence is None:
            if match is not None and match.group("info") != "":
                # An opening fence with an info string.
                if buffer:
                    found.append(_emit(buffer, start, fenced=False, info=""))
                    buffer = []
                fence, info, start = match.group("marker"), match.group("info"), lineno
                buffer = [line]
                continue
            if match is not None:
                # A bare fence with no info string opens a block too.
                if buffer:
                    found.append(_emit(buffer, start, fenced=False, info=""))
                    buffer = []
                fence, info, start = match.group("marker"), "", lineno
                buffer = [line]
                continue
            if not line.strip():
                if buffer:
                    found.append(_emit(buffer, start, fenced=False, info=""))
                    buffer = []
                continue
            if not buffer:
                start = lineno
            buffer.append(line)
            continue

        # Inside a fence: only a matching-or-longer marker of the same kind closes it.
        buffer.append(line)
        if (
            match is not None
            and match.group("info") == ""
            and match.group("marker")[0] == fence[0]
            and len(match.group("marker")) >= len(fence)
        ):
            found.append(_emit(buffer, start, fenced=True, info=info))
            buffer, fence, info = [], None, ""

    if buffer:
        found.append(_emit(buffer, start, fenced=fence is not None, info=info))
    return found


#: What ends a sentence: terminal punctuation, **any run of markup closers**,
#: then whitespace.
#:
#: **Why the closer class is not optional.** The obvious spelling — ``[.!?]\s``
#: — cannot see a sentence that ends inside markup, and Markdown prose ends
#: sentences inside markup constantly: ``.**`` closing a bold run, ``."`` and
#: ``.'`` closing a quotation, ``.)`` and ``.]`` closing a parenthetical,
#: ``.` `` closing a code span, ``._`` closing an emphasis run. Measured on the
#: published tree at the Phase 22 close: **88 sentence boundaries across 16
#: pages were invisible** under the narrow form, six of them on
#: ``public/concepts/answers-no-document-contains.md`` alone (lines 3, 18, 25,
#: 35, 51 and 244).
#:
#: **And the failure is not one-directional, which is what makes it a defect
#: rather than a coarseness.** :func:`sentence_at` promises to stop a paragraph
#: being exonerated by a negation belonging to a different sentence. An
#: invisible boundary breaks that promise BOTH ways: a bold-closed denial merges
#: with the following sentence and exempts a claim it never qualified, and a
#: bold-closed sentence naming an external approach merges with the next
#: sentence's limit verb and condemns prose that is correct. The first is a hole,
#: the second is a false positive, and neither is the "safe truncation" the
#: citation lint's comment describes.
#:
#: Still deliberately crude, and still copied in spirit from
#: `tools.lints.citations._SENTENCE_BREAK`, whose comment states the reason a
#: mis-split is safe: it truncates the window, which can only cost a match,
#: never invent one. That lint keeps the narrow form because its window is a
#: two-line source slice rather than a joined paragraph; widening it is a
#: separate change against a separate consumer and was not made here.
#:
#: `citation_sentence()` itself is NOT reused, and the reason is a signature
#: mismatch rather than an oversight: it takes ``(lines, lineno, column)`` and
#: joins a `MARKER_WINDOW` of source lines around a point. By the time this
#: module hands a caller a paragraph, the joining has already happened and the
#: unit is a whole paragraph rather than a two-line window. What is reused is
#: the finding — *match in a joined window, then map the offset back to a
#: sentence* — which is the part that took Phase 15.1 six sweeps to learn.
SENTENCE_BREAK = re.compile(r"""[.!?][)\]"'*`_]*\s""")


def sentence_bounds(text: str, offset: int) -> tuple[int, int]:
    """``(start, end)`` of the sentence of `text` containing `offset`.

    Exposed alongside :func:`sentence_at` rather than folded into it because a
    caller that needs to compare POSITIONS inside the sentence — is this anchor
    before that verb? — has to map them back into the paragraph's coordinate
    system, and recovering the offset with ``text.index(sentence)`` silently
    picks the FIRST occurrence when a paragraph repeats a sentence. Returning
    the bounds removes the search.
    """
    start = 0
    for match in SENTENCE_BREAK.finditer(text, 0, offset):
        start = match.end()
    end_match = SENTENCE_BREAK.search(text, offset)
    return start, end_match.end() if end_match else len(text)


def sentence_at(text: str, offset: int) -> str:
    """The sentence of `text` containing character `offset`.

    Scoping a qualification to the sentence that carries the claim, rather than
    to the whole paragraph, is what stops a paragraph from being exonerated by
    a negation that belongs to a different sentence three lines away.

    That promise is only as good as :data:`SENTENCE_BREAK`, and it was false for
    every sentence this tree closes inside markup until the closer class was
    added — see that constant's comment for the measurement and for both
    directions of the failure.
    """
    start, end = sentence_bounds(text, offset)
    return text[start:end]


def published_pages(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    """Every Markdown page under `root` (default: the published tree)."""
    base = PUBLIC_DIR if root is None else root
    return sorted(base.rglob("*.md"))


#: Context Product SPECIFICATIONS and the standard they are authored to.
#: Published, but NOT SDK documentation prose — they are authored to an external
#: format contract and carry ITS vocabulary.
SPECIFICATION_DIR = PUBLIC_DIR / "reference" / "specifications"


def sdk_prose_pages(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    """`published_pages()` minus the Context Product specifications.

    **Why the exclusion exists, because a narrowed population is exactly how a
    gate goes quietly blind.** The wording gates in this package police how *the
    SDK's own documentation* describes *SDK concepts*. Specification documents
    under `reference/specifications/` legitimately use vocabulary that collides:

    * **"lineage strict equality"** is one of the SIX universal validation gates
      of Specification Standard v0.3 §4.7. It is a *product contract* gate and
      has nothing to do with the SDK deployment gate of `D-IMPL-86`, whose
      wording rule demands the phrase "assembly-path integrity".
    * **"Gate 1" / "Gate 2"** in `spec_generation.md` are the two *approval*
      checkpoints of the authoring process — spec approved, then built — not the
      SDK's deployment gates.

    Applying the SDK rule to those documents asks a question the documents were
    never answering. It is the defect class this repository keeps recording: **a
    check whose population is not its question.**

    **What this does NOT excuse.** The exclusion is scoped to *wording* gates.
    Specifications remain subject to every other published-tree check, and the
    non-vacuity assertions beside each wording gate run over THIS set, so a
    narrowing that emptied it would fail rather than pass.
    """
    excluded = SPECIFICATION_DIR.resolve()
    return [
        page
        for page in published_pages(root)
        if excluded not in page.resolve().parents
    ]


def page_paragraphs(path: pathlib.Path) -> list[Paragraph]:
    """Every paragraph of the page at `path`."""
    return paragraphs(path.read_text(encoding="utf-8"))


def iter_paragraphs(
    pages: Iterable[pathlib.Path],
    *,
    prose_only: bool = True,
) -> Iterator[tuple[pathlib.Path, Paragraph]]:
    """`(page, paragraph)` across `pages`.

    `prose_only` skips fenced code blocks, which is what a *wording* gate wants
    and what a *command* gate does not.
    """
    for page in pages:
        for paragraph in page_paragraphs(page):
            if prose_only and paragraph.fenced:
                continue
            yield page, paragraph


def relative(path: pathlib.Path) -> str:
    """`path` as a repo-relative POSIX string, or absolute if it is off-root.

    Failure messages name pages the way a reader would type them; a temporary
    directory in a control test is off-root and reports absolutely, which is
    still the most useful thing that can be said about it.
    """
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
