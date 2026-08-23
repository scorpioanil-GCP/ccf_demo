"""DOCS-15 — the adoption page's two wording obligations, standing.

**What this module is for.** Phase 22 ships
``public/concepts/answers-no-document-contains.md``, a page whose whole subject
is honest citation: it names three approaches it is usually compared against
and it declines, everywhere, to assert what any of them cannot do. That
discipline is a property of *wording*, and wording is exactly what a green
build cannot speak to. `22-CONTEXT.md` **D-04** therefore rules that a gate
ships with the page, in the ``tools/docs_tests/test_gate_two_wording.py``
shape, carrying two obligations. Dave's reasoning, on the record: *"A stretch
goal means that standard is enforced only by reviewer diligence — the same
pattern that let unevidenced Completes and vacuous checks ship for years."*
And: *"if the criterion matters, something can go red when it is violated."*

The two obligations, each named so a failure says which one broke:

``AW-1``
    No published sentence asserts a capability limit of an external approach.
    `22-CONTEXT.md` **D-02** requires every *"what the alternative lacks"*
    claim to be recast as a checkable fact about the question — *"No document
    in any source system states Jane's 30.0%"* is verifiable against the
    example's own artifacts; *"RAG can't do this"* is not. **D-03** allows a
    paired contrast as a bounded fallback, and this obligation is what stops a
    residual pairing from still reading as a naked *"X can't Y"*.

``AW-2``
    No published sentence claims CCF extracts passage anchors from documents,
    and the honesty caveat is present with **both** halves in one paragraph:
    the contract ships (``D-IMPL-46``, the ``passage_anchor`` field) *and* no
    shipped pipeline produces those anchors, because Pattern 5 — unstructured
    ingestion — was never built.

**Scope is `public/` and stays there** (`22-CONTEXT.md` **D-05**). This module
walks ``_prose.published_pages()`` and nothing else. It is not a repo-wide
rhetoric linter and must not become one.

**Why AW-2's non-vacuity is proven by an injected control rather than by a
corpus floor.** This is the ``A-3`` shape in
``tools/docs_tests/test_advisory_discharge.py``: a floor is right when the
corpus *should* contain the thing being filtered, and wrong when it should
not. Measured at this plan's HEAD, the published tree carries exactly three
paragraph-level ``passage anchor`` / ``passage-level lineage`` occurrences —
one in the adoption page's caveat, and two correct ``passage-level lineage``
sentences in ``public/concepts/pillars/hitl.md`` and
``public/how-to/compose-a-workflow-with-hitl.md`` — and **zero** paragraphs
assert extraction from documents, by design. A floor demanding that some
paragraph trigger the extraction predicate would therefore be RED on a correct
tree, which is a floor that teaches authors to write a defect to satisfy it.
Non-vacuity for that predicate comes from controls 2, 10 and 11 instead, which
inject the offence into a copy and require refusal. The *positive* half of
AW-2 does get a corpus floor, because the caveat genuinely must be on the page.

**What this module is blind to. Stated here, because a check that does not say
what it cannot see is how a defect class survives a green build:**

1. **Includes.** It reads Markdown *source*, so any content arriving through a
   ``--8<--`` snippet include is never scanned. A naked capability claim, or a
   passage-extraction claim, written inside an included artifact would be
   invisible to this gate. The adoption page carries five such includes. That
   case is covered from the other side — the included artifacts are example
   inputs the always-on example suite runs — but it is not covered *here*.
2. **Code spans.** ``_prose.strip_markup`` removes backtick code spans from
   ``Paragraph.text``, so every vocabulary matched against ``.text`` is blind
   to a backticked spelling. That is usually right — a claim hidden inside a
   code span is not a claim a reader takes away — and it is exactly wrong for
   identifier-shaped vocabulary. Measured on this tree: of the ten published
   paragraphs carrying a ``D-IMPL-NN`` id, four write it *only* inside a code
   span; ``.text`` sees six and ``.raw`` sees ten. ``CAVEAT_CONTRACT`` is
   therefore matched against ``.raw`` and is the only constant here that is.
   Control 9 holds that choice and sabotage 6 was watched breaking it.

Every constant below states, in its ``#:`` comment, which ``Paragraph`` field
it is matched against. That is not decoration: matching the wrong field turns a
correct page red and an incorrect one green, and the four consequences of
getting ``CAVEAT_CONTRACT`` wrong all read as either a mysterious floor failure
or a control passing for the wrong reason.
"""

from __future__ import annotations

import pathlib
import re
import shutil
from collections.abc import Iterator

import pytest

from tools.docs_tests import _prose
from tools.lints.citations import NODE_ID, repo_index, resolve_cited, symbol_spans

#: AW-1's subjects — the external approaches the page is compared against.
#: **Matched against ``Paragraph.text``**: these are prose nouns, and an
#: approach named inside a code span is a reference to an identifier rather
#: than a claim about a tool. Word-bounded where a bare substring would
#: over-match: unbounded ``RAG`` also matches "storage", "paragraph",
#: "coverage", "leverage" and "average".
#:
#: **The second block is the page's own vocabulary, and its absence was the
#: Phase 22 close's most severe finding.** The page writes *"a document search"*
#: at line 319 and *"a retrieval system"* at line 332 and neither was in this
#: constant, so a limit asserted of either was outside candidacy entirely.
#: Measured before the addition, all three of *"A retrieval system cannot
#: answer…"*, *"A document search is unable to compute…"* and *"An embedding
#: index has no way to represent an ownership path."* were ADMITTED — written in
#: the page's own nouns.
EXTERNAL_APPROACH = re.compile(
    r"\bRAG\b"
    r"|retrieval-augmented"
    r"|vector stores?"
    r"|vector databases?"
    r"|embedding search"
    r"|semantic layers?"
    r"|prompt templates?"
    r"|hand-rolled"
    r"|hand rolled"
    r"|chunked documents"
    # The page's own nouns for the same three subjects.
    r"|retrieval systems?"
    r"|document searches"
    r"|document search"
    r"|embedding indexe?s?"
    r"|vector indexe?s?"
    r"|\bchunks?\b",
    re.IGNORECASE,
)

#: Subjects that are NOT an external approach, for AW-1's condition (ii).
#: **Matched against ``Paragraph.text``.**
#:
#: Two families, and both are on the page. CCF-side subjects, because a limit
#: predicated of **CCF** is not the AW-1 offence: with paragraph-and-heading
#: candidacy the page's most honest sentence would otherwise be reported, since
#: line 331 concedes *"…the one place on this page where a retrieval system does
#: something this deployment does not do"*. And question-side subjects, because
#: ``D-02``'s REQUIRED form is a fact about the question and those facts are
#: written with limit verbs: *"The question itself has no way to be answered by
#: reading one record"* is the recast the page is obliged to use, and control
#: 4's (b) half has held it since the gate shipped.
#:
#: Recasting correct prose to satisfy a gate that misjudges it is how a gate
#: teaches authors to write worse pages — the failure controls 5 and 6 exist to
#: prevent.
#:
#: This is nonetheless an EXEMPTION vocabulary, in the same spirit as
#: ``EXTRACTION_DENIAL``: an exemption that fires too easily switches the
#: obligation off while the suite stays green. So it names specific subjects and
#: nothing generic — **no bare pronoun**, in particular. A bare ``it`` would
#: exempt *"It cannot answer a question whose answer no single document
#: states."*, which is the measured sentence the heading-carry exists to catch.
RE_ANCHORING_SUBJECT = re.compile(
    # CCF's side of the comparison.
    r"\bCCF\b"
    r"|\bthe SDK\b"
    r"|\bthe fabric\b"
    r"|\bthis fabric\b"
    r"|\bthis deployment\b"
    r"|\bthe deployment\b"
    r"|\bthis page\b"
    r"|\bthis example\b"
    r"|\bPattern 5\b"
    r"|\bno shipped pipeline\b"
    r"|\bthe projection\b"
    r"|\bthe product\b"
    # The question's side — D-02's required recast.
    r"|\bthe question\b"
    r"|\bthis question\b"
    r"|\bthe answer\b"
    r"|\bthe figure\b"
    r"|\bthe record\b"
    r"|\bthe estate\b",
    re.IGNORECASE,
)

#: What disqualifies a ``RE_ANCHORING_SUBJECT`` from re-anchoring — AW-1's
#: condition (iii). **Matched against the ``Paragraph.text`` window immediately
#: preceding the subject.**
#:
#: Without it, condition (ii) is a hole rather than a correction. *"RAG over a
#: vector store, unlike this deployment, cannot answer the question."* and
#: *"…where a retrieval system does something this deployment does not do"* have
#: the identical shape — approach, then CCF subject, then limit verb — and only
#: the contrastive frame tells them apart. The first is the naked ``X can't Y``
#: the obligation exists to refuse; the second is the page conceding a limit of
#: its own. Both are held, verbatim, by control 14.
CONTRASTIVE_FRAME = re.compile(
    r"\b(?:unlike|rather than|instead of|compared to|compared with|whereas"
    r"|as opposed to|versus|vs\.?)\s*$",
    re.IGNORECASE,
)

#: How wide a window ahead of a ``RE_ANCHORING_SUBJECT`` is searched for a
#: ``CONTRASTIVE_FRAME``. Wide enough for ``as opposed to `` plus a comma and a
#: space; narrow enough that a contrastive word belonging to an earlier clause
#: cannot reach. A constant rather than a literal because control 14 asserts
#: against it.
CONTRASTIVE_WINDOW = 24

#: AW-1's offence — the ``X can't Y`` shape. **Matched against
#: ``Paragraph.text``**: it is ordinary prose, and a limit verb inside a code
#: span is a literal, not an assertion. Word-bounded on purpose; an unbounded
#: ``no`` matches "note" and "nothing" and would make every paragraph an
#: offender.
#:
#: **The bare plural was missing and it is the requirement's own word.**
#: ``DOCS-15`` reads *"states what each **lacks**"*; this constant carried
#: ``lacks`` and ``lacking`` and not ``lack``, so the one spelling the
#: requirement uses was the one spelling that got through. Measured ADMITTED
#: with ``Vector stores`` as the subject, before the widening below: *"lack an
#: ownership path"*, *"will never compute"*, *"are not able to"*, *"simply do
#: not compute"*, *"stop short of computing"*, *"miss the ownership path
#: entirely"*.
#:
#: ``never`` is admitted only behind a modal — ``can|could|will|would|shall`` —
#: and NOT bare. Bare ``never`` matches the honesty caveat AW-2 requires the
#: page to carry (*"Pattern 5, unstructured ingestion, was never built"*), which
#: sits under a heading naming ``document search``, so under
#: paragraph-and-heading candidacy a bare token would have made the two
#: obligations contradict each other: AW-2 demands the sentence and AW-1 would
#: refuse it.
LIMIT_VERB = re.compile(
    r"\bcannot\b"
    r"|\bcan't\b"
    r"|\bcan not\b"
    r"|\bunable to\b"
    r"|\bnot able to\b"
    r"|\black(?:s|ed|ing)?\b"
    r"|\bfails? to\b"
    r"|\bhas no\b"
    r"|\bhave no\b"
    r"|\bdoes not support\b"
    r"|\bdoesn't support\b"
    r"|\bdo not support\b"
    r"|\bincapable of\b"
    r"|\bno way to\b"
    r"|\bfalls? short\b"
    r"|\bstops? short\b"
    r"|\b(?:can|could|will|would|shall)\s+never\b"
    r"|\bdo(?:es)?\s+not\s+\w+"
    r"|\bdo(?:es)?n't\s+\w+"
    r"|\bmiss(?:es)?\b",
    re.IGNORECASE,
)

#: AW-2's subject. **Matched against ``Paragraph.text`` AND ``Paragraph.raw``**
#: — see :func:`sentences_claiming_passage_extraction` for why the negative
#: predicate reads both. **Never a bare ``passage``** — ``public/charter.md``
#: writes *"A page that names a proprietary passage fails the build"* in an
#: entirely unrelated sense, and a bare token would report that correct
#: sentence as an offender.
#:
#: **The underscored identifier is matched here now, and its absence was a
#: hole.** It used to be left to ``CAVEAT_CONTRACT`` on the grounds that
#: ``CAVEAT_CONTRACT`` reads ``.raw`` — but that is the POSITIVE half of AW-2,
#: and the negative half was reading ``.text`` only, from which
#: ``strip_markup`` deletes backtick spans. Measured ADMITTED at the Phase 22
#: close, both in the page's own house spelling (it writes ``passage_anchor``
#: at line 321):
#:
#: * ``CCF produces a `passage_anchor` for every claim it extracts from your
#:   documents.``
#: * ``The unstructured pipeline extracts `passage_anchor` values from PDFs at
#:   ingest.``
PASSAGE_ANCHOR = re.compile(
    r"passage anchors?|passage-level lineage|passage_anchors?",
    re.IGNORECASE,
)

#: AW-2's verb. **Matched against ``Paragraph.text``**. Note that ``generated``
#: is absent on purpose: *"generated content"* appears in both correct
#: ``passage-level lineage`` sentences in the published tree and describes what
#: a review queue holds, not what a pipeline does to a document.
EXTRACTION_VERB = re.compile(
    r"\bextracts?\b"
    r"|\bextracted\b"
    r"|\bextracting\b"
    r"|\bderives?\b"
    r"|\bpulls?\b"
    r"|\blifts?\b"
    r"|\bproduces?\b"
    r"|\bgenerates?\b",
    re.IGNORECASE,
)

#: AW-2's object of extraction. **Matched against ``Paragraph.text``**: it is
#: prose. Required alongside ``EXTRACTION_VERB`` so that a sentence about
#: producing a *Context Product* is not read as a claim about documents.
DOCUMENT_SOURCE = re.compile(
    r"\bdocuments?\b|\bPDFs?\b|\bcorpus\b|\bunstructured\b",
    re.IGNORECASE,
)

#: The denial limb's vocabulary — condition (i). **Matched against
#: ``Paragraph.text``**: it is prose. Deliberately NARROW: only phrases that
#: take a *production claim* as their object. It is not a general negation
#: vocabulary, and it must not be widened. A bare ``not`` or ``no`` would
#: exonerate any sentence carrying an unrelated negative clause anywhere in it,
#: and an exemption that broad becomes the hole it was added to close —
#: control 11's (a) half is written against exactly that failure.
#:
#: **``no pipeline`` was too bare and it was a hole of exactly that kind.**
#: Measured at the Phase 22 close: *"No pipeline-related cost is incurred, and
#: CCF extracts passage anchors from documents."* was EXEMPTED, because a
#: negation about pipeline COST satisfied a denial vocabulary that is supposed
#: to take a production claim as its object. Every ``pipeline`` form now refuses
#: a **hyphenated modifier** — ``pipeline-related``, ``pipeline-adjacent`` — and
#: that one guard is the whole fix.
#:
#: A second guard was drafted alongside it (a lookahead requiring a production
#: verb within one clause) and was **removed before it shipped**, because it was
#: redundant with the hyphen guard on every case either could catch: sabotaging
#: each in turn left the suite green, since the other still refused the
#: sentence. Two conditions that cannot be told apart by any control are one
#: condition and one piece of decoration, and the decoration is what a later
#: reader trusts.
EXTRACTION_DENIAL = re.compile(
    r"\bno shipped pipelines?\b(?!-)"
    r"|\bno such pipelines?\b(?!-)"
    r"|\bno pipelines?\b(?!-)"
    r"|was never built"
    r"|never built"
    r"|does not produce"
    r"|do not produce"
    r"|does not extract"
    r"|do not extract"
    r"|nothing in the shipped",
    re.IGNORECASE,
)

#: The denial limb's condition (iii) — a CLAUSE BOUNDARY. **Matched against
#: ``Paragraph.text``**: a join written inside a code span is not a join a
#: reader reads. A sentence that opens with a denial and then starts a new
#: clause is asserting whatever that new clause says, and conditions (i) and
#: (ii) alone exempt it outright — measured, not supposed.
#:
#: **The adversative-only form was a hole, and all three close reviewers found
#: it.** Modelling only ``though``/``but``/``however`` means any COORDINATING
#: join slips past. Measured EXEMPTED before this widening:
#:
#: * ``No shipped pipeline produces passage anchors from documents, and CCF
#:   extracts them anyway.``
#: * ``No pipeline produces passage anchors; CCF extracts them from documents.``
#: * ``There is no pipeline for this question and CCF produces passage anchors
#:   from documents.``
#:
#: So ``and``, ``;`` and ``so`` join the vocabulary. **A bare comma does NOT**,
#: and that is a deliberate boundary rather than an omission: the shipped caveat
#: reads *"…was never built, so no shipped pipeline produces passage anchors
#: from documents"*, whose denial and production verb are separated by a comma.
#: A comma-as-boundary would refuse the one sentence ``ROADMAP`` criterion 6
#: requires the page to carry.
#:
#: ``so`` is now IN the vocabulary, reversing this constant's earlier comment,
#: and condition (iv) is what makes that safe: the shipped caveat's clause after
#: ``so`` REPEATS the denial (*"no shipped pipeline produces…"*), so it is not a
#: turn. The exemption no longer rests on one conjunction being absent from a
#: list — it rests on the trailing clause still denying.
CONTRASTIVE_PIVOT = re.compile(
    r"\bthough\b"
    r"|\bbut\b"
    r"|\bhowever\b"
    r"|\byet\b"
    r"|\bwhile\b"
    r"|\bwhereas\b"
    r"|\balthough\b"
    r"|\band\b"
    r"|\bso\b"
    r"|;",
    re.IGNORECASE,
)

#: The caveat's first half — the contract ships. **Matched against
#: ``Paragraph.raw``, and it is the only constant here that is.** Both tokens
#: are identifiers and this repository writes identifiers backticked as house
#: style, which ``strip_markup`` deletes from ``.text``; measured on the
#: shipped caveat, ``D-IMPL-46`` and ``passage_anchor`` are both ``.raw``-only.
#: Written as two mirrored alternatives so the two tokens may appear in either
#: order while both remain required.
CAVEAT_CONTRACT = re.compile(
    r"\bD-IMPL-46\b(?=.*passage_anchor)|passage_anchor(?=.*\bD-IMPL-46\b)",
    re.IGNORECASE | re.DOTALL,
)

#: The caveat's second half — no shipped pipeline produces those anchors.
#: **Matched against ``Paragraph.text``**: it is ordinary un-backticked prose
#: on the shipped page, and it is a sentence a reader must actually read.
#:
#: **The bounded gaps exclude EVERY terminal, not just the full stop.** They
#: read ``[^.!?]`` rather than ``[^.]`` because the point of bounding them at
#: all is to keep the three tokens inside ONE sentence — a "caveat" stitched out
#: of fragments of two sentences is not a caveat a reader reads. Measured with
#: ``[^.]``: replacing the shipped caveat clause with ``**No shipped pipeline
#: ships!** CCF produces passage anchors from your documents on every
#: assembly.`` still satisfied this constant, so the positive AW-2 obligation
#: reported GREEN on a page whose caveat had been swapped for the overclaim the
#: obligation exists to prevent. Control 13 holds it.
CAVEAT_ABSENCE = re.compile(
    r"no shipped pipeline\b[^.!?]{0,80}\bpassage anchors\b[^.!?]{0,40}\bdocuments\b",
    re.IGNORECASE,
)


#: The page under guard, repo-relative inside the published tree. Declared here
#: rather than beside the controls because two assertions ABOVE the controls are
#: named for this page and must actually be scoped to it.
ADOPTION_PAGE = "concepts/answers-no-document-contains.md"


def shipped_page() -> list[pathlib.Path]:
    """The one-page list for assertions whose NAME says *the shipped page*.

    Two tests below say ``..._on_the_shipped_page`` and used to walk
    ``_prose.published_pages()``. Nothing was lost by narrowing them: the
    tree-wide statement of each is already made by the standing assertions in
    the section above, and a test whose name and scope disagree is a message
    quality defect in a module whose whole subject is checks that pass for the
    wrong reason.

    The existence assertion is what stops a renamed or moved page from turning
    both of them into tests over an empty list.
    """
    page = _prose.PUBLIC_DIR / ADOPTION_PAGE
    assert page.is_file(), (
        f"the page under guard is missing: {page}. Every assertion named "
        "'on the shipped page' would pass over nothing"
    )
    return [page]


# --------------------------------------------------------------------------
# Predicates. Each returns openable ``page:line — sentence`` strings, because
# a red run whose message cannot be opened is a red run nobody acts on.
# Paragraph is the unit of CANDIDACY; sentence is the unit of JUDGEMENT.
# --------------------------------------------------------------------------


#: An ATX heading line, with its level. Applied to ``Paragraph.text``, which is
#: exactly the heading line for a heading paragraph: a heading is a run of one
#: non-blank line, so ``_prose.paragraphs`` emits it on its own.
HEADING = re.compile(r"(#{1,6})\s+(?P<title>\S.*)$")


def paragraphs_with_their_subject(
    pages: list[pathlib.Path],
) -> Iterator[tuple[pathlib.Path, _prose.Paragraph, str]]:
    """``(page, paragraph, subject)`` for every prose paragraph in `pages`.

    ``subject`` is the paragraph's own text joined with the text of every
    heading it sits under — the whole ancestor stack, not just the nearest one,
    so a subject established at ``##`` still governs a ``###`` subsection that
    does not restate it.

    **Why this exists, and it is the Phase 22 close's most severe finding.**
    AW-1 used to require the approach noun and the limit verb in the SAME
    SENTENCE. The page establishes each of its three comparison subjects in a
    heading — ``### RAG over a vector store``, ``### Hand-rolled context
    assembly``, ``### A semantic layer plus prompt templates`` — and then never
    restates it in the body. Measured: the entire published tree yielded FOUR
    ``EXTERNAL_APPROACH`` candidate paragraphs and THREE OF THEM WERE THOSE
    HEADINGS, so every subsection BODY was outside candidacy and the obligation
    had jurisdiction over nothing where it mattered most. *"It cannot answer a
    question whose answer no single document states."* dropped straight into a
    subsection body and was ADMITTED.

    Candidacy widens; judgement does not. The unit of judgement stays the
    sentence, and the three conditions in
    :func:`sentences_asserting_a_capability_limit` are what stop a carried
    subject from condemning a sentence whose limit belongs to CCF.
    """
    for page in pages:
        stack: dict[int, str] = {}
        for paragraph in _prose.page_paragraphs(page):
            if paragraph.fenced:
                continue
            heading = HEADING.match(paragraph.text)
            if heading is not None:
                level = len(heading.group(1))
                stack = {
                    depth: title for depth, title in stack.items() if depth < level
                }
                stack[level] = paragraph.text
            subject = " || ".join([paragraph.text, *stack.values()])
            yield page, paragraph, subject


def _reanchoring_subjects(sentence: str) -> list[int]:
    """Offsets of the ``RE_ANCHORING_SUBJECT`` matches in `sentence` that count.

    A subject standing behind a ``CONTRASTIVE_FRAME`` — *"RAG, **unlike** this
    deployment, cannot…"* — is naming CCF as the thing being contrasted AGAINST,
    not as the thing the limit is predicated of, so it does not re-anchor. That
    is condition (iii).
    """
    return [
        match.start()
        for match in RE_ANCHORING_SUBJECT.finditer(sentence)
        if CONTRASTIVE_FRAME.search(
            sentence[max(0, match.start() - CONTRASTIVE_WINDOW) : match.start()]
        )
        is None
    ]


def sentences_asserting_a_capability_limit(
    pages: list[pathlib.Path],
) -> list[str]:
    """AW-1: ``page:line — sentence`` for each naked ``X can't Y``.

    **Candidacy is the paragraph plus its heading stack**
    (:func:`paragraphs_with_their_subject`); **judgement is the sentence**. A
    limit verb three sentences away — attached to something else entirely — does
    not condemn a correct sentence.

    A ``LIMIT_VERB`` inside a candidate paragraph is an offence unless one of
    three conditions exempts it. Each is watched by its own half of control 14,
    and each was measured before it was written:

    (i)   **Anchoring.** The nearest subject anchor standing BEFORE the verb
          decides what the limit is predicated of. Approach anchors come from
          ``EXTERNAL_APPROACH``, CCF anchors from ``CCF_SUBJECT``. With no
          anchor before the verb at all, the carried subject rules and the
          sentence is an offender — that is what catches *"It cannot answer a
          question whose answer no single document states."* under a heading
          naming RAG.
    (ii)  **Re-anchoring.** A nearest-preceding non-approach anchor exempts,
          because the limit is being predicated of something other than the
          approach. Two live cases: line 331 of the page, *"…where a retrieval
          system does something this deployment does not do"*, is the page
          conceding its own limit; and *"The question itself has no way to be
          answered by reading one record"* is ``D-02``'s required recast, held
          by control 4's (b) half since the gate shipped.
    (iii) **Contrastive frame.** A CCF anchor introduced by ``unlike``, ``rather
          than``, ``compared to`` and their siblings does NOT re-anchor. Without
          this, condition (ii) is a hole: *"RAG over a vector store, unlike this
          deployment, cannot answer the question."* has the identical anchor
          order to line 331 and is the naked claim the obligation exists to
          refuse.

    Do not delete a condition as clutter, and do not narrow the vocabularies to
    make a red go away. Narrowing the gate to fit the prose is the move this
    module exists to stop; if the page goes red, the page is what changes.
    """
    offenders: list[str] = []
    for page, paragraph, subject in paragraphs_with_their_subject(pages):
        if EXTERNAL_APPROACH.search(subject) is None:
            continue
        for match in LIMIT_VERB.finditer(paragraph.text):
            start, end = _prose.sentence_bounds(paragraph.text, match.start())
            sentence = paragraph.text[start:end]
            verb = match.start() - start
            anchors = [
                (found.start(), "approach")
                for found in EXTERNAL_APPROACH.finditer(sentence)
            ]
            anchors += [
                (offset, "other") for offset in _reanchoring_subjects(sentence)
            ]
            preceding = [anchor for anchor in anchors if anchor[0] < verb]
            if preceding and max(preceding)[1] == "other":
                # The nearest subject standing ahead of the verb is not the
                # approach, so the limit is predicated of something else — CCF,
                # or the question. That is a legitimate way to be right, and
                # both the page's most honest sentence and D-02's required
                # recast are written exactly this way.
                continue
            report = f"{_prose.relative(page)}:{paragraph.lineno} — {sentence.strip()}"
            if report not in offenders:
                offenders.append(report)
    return offenders


def sentences_claiming_passage_extraction(
    pages: list[pathlib.Path],
) -> list[str]:
    """AW-2, negative: ``page:line — sentence`` for each extraction claim.

    **Both ``Paragraph`` fields are scanned, and the reason is the same one
    :func:`paragraphs_carrying_the_caveat` gives for its positive half** — this
    is the single place the field choice for AW-2 is stated, because the two
    halves were asymmetric and undocumented and that asymmetry was a hole.
    ``strip_markup`` deletes backtick code spans from ``.text``; this repository
    writes identifiers backticked as house style, and the guarded page itself
    writes ``passage_anchor`` that way at line 321. So the positive half already
    read ``.raw`` for its identifier tokens while this half read ``.text``
    only — and the page's own house spelling was therefore an evasion. Measured
    ADMITTED: ``CCF produces a `passage_anchor` for every claim it extracts from
    your documents.``

    Scanning both and de-duplicating by report string is preferred to scanning
    ``.raw`` alone: ``.text`` is what a reader takes away, and a report quoting
    the stripped sentence is the more openable of the two. Control 17 holds it.

    A sentence is a CANDIDATE when it names a passage anchor, applies an
    extraction verb, and names a document source. **All three, and that is the
    problem this predicate has to solve**, because the honesty caveat ROADMAP
    criterion 6 requires — *"Pattern 5, unstructured ingestion, was never
    built, so no shipped pipeline produces passage anchors from documents."* —
    matches all three too. A predicate built from those three alone reads the
    SHAPE of an extraction claim without reading whether the sentence ASSERTS
    it or DENIES it, so the most careful possible statement of the caveat
    becomes indistinguishable from the overclaim the obligation exists to
    prevent. On a correct tree that predicate turns this module's own AW-2
    assertion red.

    The denial limb below is the fix, and it is deliberately narrow, because an
    exemption limb is itself a vacuity risk: an exemption that fires too easily
    switches the obligation off while the suite stays green. It exempts a
    candidate only when **all three** of these hold:

    (i)   **Vocabulary.** ``EXTRACTION_DENIAL`` matches the sentence. Only
          phrases that take a production claim as their object; an unrelated
          negative clause must not exonerate anything.
    (ii)  **Ordering.** The earliest denial stands BEFORE the earliest
          extraction verb in the same sentence, so a denial appended after the
          claim cannot retroactively withdraw it.
    (iii) **Clause boundary.** No ``CONTRASTIVE_PIVOT`` stands between that
          denial and any later extraction verb. Without this, a denial at the
          START of a sentence exempts everything after it — measured: *"No
          shipped pipeline produces passage anchors, though CCF does extract
          them from documents."* was EXEMPTED under the two-condition form, and
          so was every COORDINATING join until ``and``, ``;`` and ``so`` were
          added at the Phase 22 close.
    (iv)  **The trailing clause still denies.** A boundary only counts as a TURN
          if the clause carrying the later verb has no denial of its own. This
          is what keeps the widened vocabulary from refusing correct prose: *"No
          shipped pipeline extracts passage anchors from documents, and no
          shipped pipeline produces them either."* crosses an ``and`` and is
          still a denial throughout, and the shipped caveat's clause after
          ``so`` repeats ``no shipped pipeline`` verbatim. Without (iv) the
          exemption would rest on ``so`` being absent from a list, which is a
          much weaker thing to rest on.

    In one line: **the limb exempts a sentence that denies and keeps denying,
    and refuses one that denies and then TURNS.**

    Do not delete a condition as clutter. Each one is watched by its own
    sabotage mutation and its own half of control 11; the mutation count tracks
    the condition count, and condition (iv) shipped with the (f) half.
    """
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages):
        for field in (paragraph.text, paragraph.raw):
            for match in PASSAGE_ANCHOR.finditer(field):
                sentence = _prose.sentence_at(field, match.start())
                if _sentence_denies_or_asserts_extraction(sentence):
                    report = (
                        f"{_prose.relative(page)}:{paragraph.lineno}"
                        f" — {sentence.strip()}"
                    )
                    if report not in offenders:
                        offenders.append(report)
    return offenders


def _sentence_denies_or_asserts_extraction(sentence: str) -> bool:
    """Whether `sentence` ASSERTS passage extraction from documents.

    Split out of :func:`sentences_claiming_passage_extraction` when that
    predicate started reading two fields, so the four conditions are written
    once. Two copies of a judgement rule drift into two judgement rules —
    ``_prose``'s own docstring records the same finding about scoping.
    """
    verbs = [found.start() for found in EXTRACTION_VERB.finditer(sentence)]
    if not verbs or DOCUMENT_SOURCE.search(sentence) is None:
        return False
    denials = [found.start() for found in EXTRACTION_DENIAL.finditer(sentence)]
    if denials:
        denial = min(denials)
        precedes = denial < min(verbs)
        turns = any(
            denial < boundary.start() < verb
            and not any(boundary.start() < later < verb for later in denials)
            for boundary in CONTRASTIVE_PIVOT.finditer(sentence)
            for verb in verbs
        )
        if precedes and not turns:
            # The sentence DENIES extraction rather than asserting it, and
            # denies it in the one word order that cannot be read the other
            # way: an in-vocabulary denial, standing ahead of every extraction
            # verb, with no clause boundary turning against it before one — or,
            # where a boundary is crossed, with the trailing clause still
            # denying. That is a legitimate way to be right, and it is the way
            # ROADMAP criterion 6 requires the caveat to be written.
            return False
    return True


def paragraphs_carrying_the_caveat(
    pages: list[pathlib.Path],
) -> list[str]:
    """AW-2, positive: ``page:line`` for each paragraph with BOTH halves.

    **One ``Paragraph`` object, two fields, and that is deliberate.** The
    negative half's field choice is stated at
    :func:`sentences_claiming_passage_extraction`; the two are written down
    together on purpose, because they were asymmetric and silent about it until
    the Phase 22 close.
    ``CAVEAT_CONTRACT`` is matched against ``.raw`` because both of its tokens
    are identifiers the page writes backticked, and ``strip_markup`` deletes
    code spans from ``.text``; ``CAVEAT_ABSENCE`` is matched against ``.text``
    because it is ordinary prose a reader must read. This is still *both halves
    in one paragraph* — the scoping is the paragraph, not the field. Do not
    "simplify" it onto a single field: against ``.text`` alone the contract
    half finds nothing on a correct page, and control 9 exists to say so out
    loud when someone tries.
    """
    return [
        f"{_prose.relative(page)}:{paragraph.lineno}"
        for page, paragraph in _prose.iter_paragraphs(pages)
        if CAVEAT_CONTRACT.search(paragraph.raw)
        and CAVEAT_ABSENCE.search(paragraph.text)
    ]


# --------------------------------------------------------------------------
# Non-vacuity floors — a vacuous pass is the failure this module exists to
# prevent. WR-04: a CWD-relative walk scanned zero files and the gate passed
# over nothing.
#
# The corpus floor is THREE tests, not one test with three clauses. A bundled
# floor fails ambiguously: a red from "the directory exists" satisfies any
# control that only asks for "a red naming the external-approach vocabulary",
# which is a control that proves nothing.
# --------------------------------------------------------------------------


def test_the_published_directory_exists() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), (
        "the published tree is missing: _prose.PUBLIC_DIR resolves to "
        f"{_prose.PUBLIC_DIR}, which is not a directory — every assertion in "
        "this module would pass over nothing"
    )


def test_the_published_tree_has_pages() -> None:
    pages = _prose.published_pages()
    assert pages, (
        f"no markdown pages under {_prose.PUBLIC_DIR} — published_pages() "
        "returned 0 pages, so AW-1 and AW-2 are both scanning an empty corpus"
    )


def test_some_published_paragraph_names_an_external_approach() -> None:
    """AW-1's corpus floor.

    This became satisfiable only when this phase's page shipped: before
    ``public/concepts/answers-no-document-contains.md`` existed, no published
    paragraph named RAG, a vector store or a semantic layer at all.

    **Measured today: 17 candidate paragraphs, all on that page** — and the
    number is stated as paragraphs because that is the unit of candidacy.
    The earlier docstring here said *"Ten candidate sentences match today"*,
    which was ten regex MATCHES across four paragraphs, three of them headings.
    A match count reads as coverage evidence and is not one: it counted the same
    four paragraphs repeatedly while the three subsection bodies the obligation
    most needed to reach were outside candidacy entirely. Counting the wrong
    unit is how the most severe finding of the Phase 22 close hid behind a green
    floor.
    """
    triggered = [
        f"{_prose.relative(page)}:{paragraph.lineno}"
        for page, paragraph, subject in paragraphs_with_their_subject(
            _prose.published_pages()
        )
        if EXTERNAL_APPROACH.search(subject)
    ]
    assert triggered, (
        "no published paragraph matches EXTERNAL_APPROACH, so AW-1 is "
        "filtering an empty set and its green means nothing — this is AW-1's "
        "corpus floor and it is red"
    )


def test_the_heading_carry_is_load_bearing_on_the_shipped_page() -> None:
    """Candidacy really does reach subsection BODIES, not only their headings.

    The floor above would stay green with the heading carry deleted, because
    the headings themselves match either way. This is the assertion that goes
    red instead — and the two numbers it compares are the finding: measured at
    the Phase 22 close, the published tree yielded **6** paragraphs naming an
    approach in their own text and **4 of the 6 were headings**, so the bodies
    of ``### RAG over a vector store``, ``### Hand-rolled context assembly`` and
    ``### A semantic layer plus prompt templates`` were outside AW-1's
    jurisdiction completely. With the carry they are 17.

    **Scoped to the shipped page, because that is what its name says**, and
    because every one of those 17 is on it. The tree-wide corpus floor is the
    test above.
    """
    pages = shipped_page()
    own_text = {
        (_prose.relative(page), paragraph.lineno)
        for page, paragraph in _prose.iter_paragraphs(pages)
        if EXTERNAL_APPROACH.search(paragraph.text)
    }
    carried = {
        (_prose.relative(page), paragraph.lineno)
        for page, paragraph, subject in paragraphs_with_their_subject(pages)
        if EXTERNAL_APPROACH.search(subject)
    }
    assert own_text <= carried, (
        "the heading carry LOST candidates the own-text scan finds, which "
        f"means it is not a widening at all: {sorted(own_text - carried)}"
    )
    assert carried - own_text, (
        "no published paragraph becomes a candidate through its heading, so "
        "paragraphs_with_their_subject is carrying nothing and AW-1 is back to "
        "requiring the approach noun and the limit verb in the same sentence — "
        "the shape under which every comparison subsection BODY on this page "
        "was outside candidacy"
    )
    headings_only = {
        (_prose.relative(page), paragraph.lineno)
        for page, paragraph in _prose.iter_paragraphs(pages)
        if EXTERNAL_APPROACH.search(paragraph.text) and HEADING.match(paragraph.text)
    }
    assert len(headings_only) >= 3, (
        "fewer than three published headings name an external approach, so the "
        "page has stopped establishing its comparison subjects in headings and "
        f"this test is measuring something else: {sorted(headings_only)}"
    )


def test_the_passage_vocabulary_is_present_in_the_published_tree() -> None:
    """AW-2's walk is reading something.

    Satisfied today by three paragraphs: the adoption page's caveat, and the
    two correct ``passage-level lineage`` sentences in
    ``public/concepts/pillars/hitl.md`` and
    ``public/how-to/compose-a-workflow-with-hitl.md``.
    """
    triggered = [
        f"{_prose.relative(page)}:{paragraph.lineno}"
        for page, paragraph in _prose.iter_paragraphs(_prose.published_pages())
        if PASSAGE_ANCHOR.search(paragraph.text)
    ]
    assert triggered, (
        "no published paragraph matches PASSAGE_ANCHOR, so AW-2's negative "
        "predicate is scanning nothing"
    )


def test_the_positive_caveat_assertion_has_something_to_assert_over() -> None:
    """The contract half exists somewhere in the tree.

    **Tree-scoped, and the name deliberately does not say otherwise** — it asks
    whether the vocabulary has anything to match ANYWHERE, which is a corpus
    floor. Its shipped-page counterpart is control 3.

    Separate from the assertion below, which requires BOTH halves in one
    paragraph. If only this one is red, the contract half has gone missing or
    ``CAVEAT_CONTRACT`` has been moved onto the wrong ``Paragraph`` field.
    """
    triggered = [
        f"{_prose.relative(page)}:{paragraph.lineno}"
        for page, paragraph in _prose.iter_paragraphs(_prose.published_pages())
        if CAVEAT_CONTRACT.search(paragraph.raw)
    ]
    assert triggered, (
        "no published paragraph's .raw matches CAVEAT_CONTRACT, so the "
        "positive AW-2 assertion is filtering an empty set — check that "
        "CAVEAT_CONTRACT is still matched against Paragraph.raw and not .text"
    )


def test_the_denial_limb_is_load_bearing_on_the_shipped_page() -> None:
    """The limb is exercised by the real tree, not dead code.

    **Scoped to the shipped page, because that is what its name says.** The
    tree-wide form of the second assertion is already made by
    ``test_no_published_sentence_claims_ccf_extracts_passage_anchors_from_documents``
    above, so narrowing costs no coverage and makes the name true.

    Two things are asserted, and both are needed. First, that the published
    tree really does carry a sentence matching ``PASSAGE_ANCHOR``,
    ``EXTRACTION_VERB`` and ``DOCUMENT_SOURCE`` all three — so there is a
    candidate the limb has to exempt. Second, that the predicate nonetheless
    reports no offender. Without the first, deleting the limb would leave the
    build green and nobody would find out; without the second, the caveat the
    page is required to carry would be reported as the overclaim it denies.
    """
    pages = shipped_page()
    candidates = [
        f"{_prose.relative(page)}:{paragraph.lineno} — {sentence.strip()}"
        for page, paragraph in _prose.iter_paragraphs(pages)
        for sentence in (
            _prose.sentence_at(paragraph.text, match.start())
            for match in PASSAGE_ANCHOR.finditer(paragraph.text)
        )
        if EXTRACTION_VERB.search(sentence) and DOCUMENT_SOURCE.search(sentence)
    ]
    assert candidates, (
        "no published sentence matches PASSAGE_ANCHOR, EXTRACTION_VERB and "
        "DOCUMENT_SOURCE together, so the EXTRACTION_DENIAL limb is exempting "
        "nothing on this tree — it is dead code and its removal would not be "
        "noticed"
    )
    offenders = sentences_claiming_passage_extraction(pages)
    assert not offenders, (
        "the EXTRACTION_DENIAL limb failed to exempt the shipped caveat, which "
        "denies extraction rather than asserting it. Either the page's wording "
        "now denies and then TURNS rather than denying and then EXPLAINING — "
        "which is plan 02's defect to fix, not this limb's to widen — or the "
        "limb regressed: " + "; ".join(offenders)
    )


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _prose.published_pages(), "the walk resolved against the CWD, not the repo"


# --------------------------------------------------------------------------
# The three assertions over the tree as it stands.
# --------------------------------------------------------------------------


def test_no_published_sentence_asserts_a_capability_limit_of_an_external_approach() -> (
    None
):
    offenders = sentences_asserting_a_capability_limit(_prose.published_pages())
    assert not offenders, (
        "AW-1 is violated: published prose asserts what an external approach "
        "cannot do. D-02 requires the claim be recast as a checkable fact "
        "about the QUESTION — show what the question demands and what the "
        "gated path does, and let the reader draw the inference — because an "
        "uncited 'lacks' sentence is a strong-looking claim with nothing to "
        "open: " + "; ".join(offenders)
    )


def test_no_published_sentence_claims_ccf_extracts_passage_anchors_from_documents() -> (
    None
):
    offenders = sentences_claiming_passage_extraction(_prose.published_pages())
    assert not offenders, (
        "AW-2 is violated: published prose claims CCF extracts passage anchors "
        "from documents. The contract ships — D-IMPL-46 rules the "
        "PassageCitationProvider Protocol and lineage carries a passage_anchor "
        "field — but Pattern 5, unstructured ingestion, was never built, so no "
        "shipped pipeline produces those anchors: " + "; ".join(offenders)
    )


def test_the_passage_anchor_caveat_states_both_halves_in_one_paragraph() -> None:
    carrying = paragraphs_carrying_the_caveat(_prose.published_pages())
    assert carrying, (
        "AW-2 is violated: no published paragraph states both halves of the "
        "passage-anchor caveat. Half a caveat still parses as honest — the "
        "contract half alone reads as a shipped capability, and the absence "
        "half alone reads as a gap with no contract behind it — which is why "
        "both halves are required in ONE paragraph, the contract half matched "
        "against Paragraph.raw and the absence half against Paragraph.text"
    )


# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may scan nothing.
#
# The fixture source is the page THIS PHASE SHIPS, not the adopter's guide. An
# injected violation appended to the adoption page proves the gate guards the
# page it exists for, and the unmodified-copy baseline (control 3) then also
# proves the shipped page is clean. Every control mutates a COPY under
# ``tmp_path``; nothing here writes to ``public/``.
# --------------------------------------------------------------------------


#: The shipped caveat clause control 13 substitutes away, **verbatim as the page
#: wraps it**. A paraphrase would either fail to anchor — turning the control
#: into a no-op the fixture-integrity assertion has to catch — or drop the
#: markup-closed boundary that is half of what the control measures.
CAVEAT_CLAUSE = (
    "Pattern 5, unstructured ingestion, was\n"
    "never built, so no shipped pipeline produces passage anchors from documents."
)

#: What control 13 puts in its place: a denial fragment about something else,
#: closed with ``!**``, followed by the overclaim. Measured before the fix, this
#: page passed **both** AW-2 obligations.
CAVEAT_CLAUSE_SWAPPED_FOR_AN_OVERCLAIM = (
    "**No shipped pipeline ships!** CCF produces passage anchors from your\n"
    "documents on every assembly."
)


def _copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """An unmodified copy of the adoption page, for substitution controls."""
    source = _prose.PUBLIC_DIR / ADOPTION_PAGE
    assert source.is_file(), f"control fixture source missing: {source}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    target = tmp_path / pathlib.Path(ADOPTION_PAGE).name
    shutil.copy(source, target)
    return target


def _copied_tree(tmp_path: pathlib.Path, extra: str) -> list[pathlib.Path]:
    """A one-page tree: the adoption page with `extra` appended.

    The source-exists assertion lives in :func:`_copy` and is what stops a
    renamed fixture from silently yielding an empty list — an empty list makes
    every predicate return ``[]``, which turns every refusal control green for
    the worst possible reason.
    """
    target = _copy(tmp_path)
    if extra:
        with target.open("a", encoding="utf-8") as handle:
            handle.write("\n\n" + extra + "\n")
    return [target]


def _standalone(tmp_path: pathlib.Path, body: str) -> list[pathlib.Path]:
    """A one-page tree built from `body` under a heading naming NO approach.

    The counterpart to :func:`_copied_tree`, and it exists because appending is
    the wrong fixture for a **candidacy** question. The adoption page's last
    heading is ``## Where a document search is stronger, and this is not``, so
    an appended paragraph is a candidate through the heading carry whatever noun
    it uses — which made the first draft of control 16 survive two of the three
    vocabulary sabotages it exists to catch.

    Use :func:`_copied_tree` when the question is *"does the gate guard the
    shipped page?"* and this when the question is *"does this vocabulary
    matter?"*.
    """
    page = tmp_path / "standalone.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(f"{NEUTRAL_HEADING}\n\n{body}\n", encoding="utf-8")
    return [page]


def test_control_1_an_injected_capability_limit_sentence_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """AW-1 fires on an injected naked claim, and AW-2 stays silent."""
    pages = _copied_tree(
        tmp_path,
        "RAG over a vector store cannot answer a question whose answer no "
        "single document states.",
    )
    offenders = sentences_asserting_a_capability_limit(pages)
    assert offenders, (
        "AW-1 admitted a naked capability claim — the gate is scanning "
        "nothing, or EXTERNAL_APPROACH/LIMIT_VERB have drifted"
    )
    assert any(
        pathlib.Path(ADOPTION_PAGE).name in offender and re.search(r":\d+ — ", offender)
        for offender in offenders
    ), f"the offender string names no page and line: {offenders}"
    # The cross-assertion: the two obligations must be proven to be testing
    # different things, so AW-2 must behave here exactly as it does on the
    # clean page — no extraction offender, and the caveat still found.
    assert sentences_claiming_passage_extraction(pages) == [], (
        "AW-2's negative predicate fired on an AW-1 violation; the two "
        "obligations are not testing different things"
    )
    assert paragraphs_carrying_the_caveat(pages), (
        "AW-2's positive predicate lost the caveat when an AW-1 violation was "
        "injected; the two obligations are not independent"
    )


def test_control_2_an_injected_extraction_claim_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """AW-2 fires on an injected extraction claim, and AW-1 stays silent."""
    pages = _copied_tree(
        tmp_path,
        "CCF extracts passage anchors from your documents and attaches one to "
        "every claim it serves.",
    )
    offenders = sentences_claiming_passage_extraction(pages)
    assert offenders, (
        "AW-2 admitted a claim that CCF extracts passage anchors from "
        "documents — either the gate is scanning nothing, or the denial limb "
        "has become unconditional"
    )
    # The cross-assertion, in the other direction.
    assert sentences_asserting_a_capability_limit(pages) == [], (
        "AW-1 fired on an AW-2 violation; the two obligations are not testing "
        "different things"
    )


def test_control_3_the_unmodified_copy_passes_every_assertion(
    tmp_path: pathlib.Path,
) -> None:
    """The controls' baseline: every refusal above comes from the mutation.

    Routed through ``_copied_tree`` with an empty injection on purpose, so that
    breaking the helper is visible here too — a baseline that cannot notice its
    own fixture disappearing vouches for nothing.
    """
    pages = _copied_tree(tmp_path, "")
    assert sentences_asserting_a_capability_limit(pages) == [], (
        "the shipped page asserts a capability limit of an external approach"
    )
    assert sentences_claiming_passage_extraction(pages) == [], (
        "the shipped page claims CCF extracts passage anchors from documents"
    )
    assert paragraphs_carrying_the_caveat(pages), (
        "the shipped page does not carry both halves of the caveat in one "
        "paragraph"
    )


def test_control_4_a_negation_in_a_different_sentence_does_not_exonerate(
    tmp_path: pathlib.Path,
) -> None:
    """Sentence scoping, proven from both sides rather than asserted.

    First: a paragraph whose opening sentence is emphatically not a capability
    claim still fails if a later sentence is one. A paragraph-scoped reading
    would call the whole thing exonerated.

    Second, the reverse: an approach named in one sentence and a limit verb
    belonging to a different subject in the next is NOT an offender. Together
    the two halves pin the unit of judgement to the sentence.

    Third, the same reverse case **with the boundary closed by markup**. The two
    halves above both spell their sentence ends as ``. `` and therefore pass
    under a ``SENTENCE_BREAK`` that cannot see ``.**``, ``."``, ``.)`` or
    ``.` ``, which is how the narrow form survived Phase 22 with 88 invisible
    boundaries in the published tree and six on this very page. Markdown prose
    ends sentences inside markup constantly, so the plain-punctuation fixture
    was proving the scoping for the spelling the tree uses least.
    """
    offending = _copied_tree(
        tmp_path / "a",
        "RAG over a vector store is not the target of this page. A vector "
        "store cannot answer a question whose answer no single document "
        "states.",
    )
    assert sentences_asserting_a_capability_limit(offending), (
        "a negation in a neighbouring sentence exonerated a capability claim "
        "— the scoping regressed from sentence to paragraph"
    )
    innocent = _copied_tree(
        tmp_path / "b",
        "The deployment is compared against RAG over a vector store. The "
        "question itself has no way to be answered by reading one record, "
        "because the answer is a sum over two ownership paths.",
    )
    assert sentences_asserting_a_capability_limit(innocent) == [], (
        "a limit verb in a neighbouring sentence, attached to the question "
        "rather than to the approach, was reported as an offender — the "
        "scoping widened from sentence to paragraph"
    )
    # (c) The same innocent shape with the boundary closed by ``**``. Measured
    # under the narrow ``[.!?]\s`` form: REPORTED as an offender, because the
    # two sentences were read as one. Verbatim, and not to be re-punctuated.
    markup_closed = _copied_tree(
        tmp_path / "c",
        "The deployment is compared against **RAG over a vector store.** The "
        "question itself has no way to be answered by reading one record, "
        "because the answer is a sum over two ownership paths.",
    )
    assert sentences_asserting_a_capability_limit(markup_closed) == [], (
        "a sentence boundary closed by markup was invisible, so an approach "
        "named in one sentence merged with the next sentence's limit verb and "
        "correct prose was reported as an offender — _prose.SENTENCE_BREAK has "
        "lost its markup-closer class"
    )


def test_control_5_a_bare_enumeration_of_the_three_approaches_is_not_an_offender(
    tmp_path: pathlib.Path,
) -> None:
    """The AW-1 trigger boundary, held from the other side.

    Naming the three approaches asserts nothing about any of them. If this
    ever fails, the gate has started demanding padding in correct prose.
    """
    pages = _copied_tree(
        tmp_path,
        "The three approaches this deployment is usually compared against are "
        "RAG over a vector store, hand-rolled context assembly, and a "
        "semantic layer plus prompt templates.",
    )
    assert sentences_asserting_a_capability_limit(pages) == [], (
        "AW-1 reported a bare enumeration of the three approaches as an "
        "offender; the gate is now demanding padding in correct prose"
    )


def test_control_6_a_question_fact_recast_is_not_an_offender(
    tmp_path: pathlib.Path,
) -> None:
    """The form D-02 REQUIRES the page to use must pass.

    Dave's ruling: *"'No document in any source system states Jane's 30.0%' is
    verifiable against `events.yaml` and `source-estate.yaml` — includable.
    'RAG can't do this' is not."* A gate that refused the first would make the
    obligation unsatisfiable.
    """
    pages = _copied_tree(
        tmp_path,
        "No document in any source system states the 30.0% aggregate "
        "ownership figure; it is a sum over two paths, and the example's "
        "expectation artifact declares it before the run computes it.",
    )
    assert sentences_asserting_a_capability_limit(pages) == [], (
        "AW-1 reported a D-02-conforming question-fact as an offender; the "
        "gate now refuses the only form the page is permitted to use"
    )


def test_control_7_a_caveat_missing_its_absence_half_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """Substitute the absence half away; the contract half survives intact."""
    page = _copy(tmp_path)
    text = page.read_text(encoding="utf-8").replace(
        "no shipped pipeline produces passage anchors from documents",
        "the ingestion pipeline is out of scope for this deployment",
    )
    page.write_text(text, encoding="utf-8")
    # Fixture integrity first: assert the mutation removed the RIGHT half.
    assert "D-IMPL-46" in text and "passage_anchor" in text, (
        "the fixture removed the wrong half — the contract half is gone too, "
        "so an empty result below would prove nothing"
    )
    assert "no shipped pipeline produces" not in text, (
        "the fixture removed nothing; the absence half is still present"
    )
    assert paragraphs_carrying_the_caveat([page]) == [], (
        "AW-2's positive predicate accepted a caveat carrying only its "
        "contract half — half a caveat still parses as honest, which is the "
        "whole reason both halves are required in one paragraph"
    )


def test_control_8_a_correct_passage_level_lineage_sentence_is_not_an_offender(
    tmp_path: pathlib.Path,
) -> None:
    """AW-2's false-positive boundary, held from the other side.

    Lineage ATTACHMENT is a shipped capability and the published tree already
    describes it twice, in ``public/concepts/pillars/hitl.md`` and
    ``public/how-to/compose-a-workflow-with-hitl.md``. Only extraction FROM
    DOCUMENTS is the overclaim.
    """
    pages = _copied_tree(
        tmp_path,
        "A review queue holds generated content with its passage-level "
        "lineage attached, so a reviewer can see what each claim rests on "
        "before the content is released.",
    )
    assert sentences_claiming_passage_extraction(pages) == [], (
        "AW-2 reported a correct passage-level-lineage attachment sentence as "
        "an extraction claim; the vocabulary has widened past its subject"
    )


def test_control_9_a_backticked_identifier_spelling_is_still_seen(
    tmp_path: pathlib.Path,
) -> None:
    """The ``.raw`` field choice, held rather than asserted.

    ``_prose.strip_markup`` deletes backtick code spans from
    ``Paragraph.text``, and this repository writes decision ids and identifiers
    backticked as house style: measured, four of the ten published paragraphs
    carrying a ``D-IMPL-NN`` id write it ONLY inside a code span, so ``.text``
    sees six and ``.raw`` sees ten. Matched against ``.text``,
    ``CAVEAT_CONTRACT`` would therefore find nothing on a CORRECT page.

    This control builds its own page rather than copying the shipped one, on
    purpose: the field choice must not silently depend on how plan 02 happened
    to spell the caveat. Control 3 and
    ``test_the_positive_caveat_assertion_has_something_to_assert_over`` already
    cover the shipped spelling.

    If a later reader "simplifies" the predicate onto one field, this goes red
    and says why.
    """
    page = tmp_path / "backticked.md"
    page.write_text(
        "# A control page\n"
        "\n"
        "The lineage entry carries a `passage_anchor` field and the contract\n"
        "behind it ships: `D-IMPL-46` rules the Protocol that fills it. No\n"
        "shipped pipeline produces passage anchors from documents, because\n"
        "the unstructured ingestion pattern was never built.\n",
        encoding="utf-8",
    )
    carrying = paragraphs_carrying_the_caveat([page])
    assert len(carrying) == 1, (
        "the backticked identifier spelling was not seen: CAVEAT_CONTRACT "
        f"must be matched against Paragraph.raw, not .text — got {carrying}"
    )
    # The inverse, in the same test, for the field that would be wrong.
    paragraph = next(
        par for par in _prose.page_paragraphs(page) if CAVEAT_ABSENCE.search(par.text)
    )
    assert CAVEAT_CONTRACT.search(paragraph.raw) is not None, (
        "the contract half is not visible in Paragraph.raw — the fixture is "
        "wrong, not the field choice"
    )
    assert CAVEAT_CONTRACT.search(paragraph.text) is None, (
        "the contract half is visible in Paragraph.text, so strip_markup no "
        "longer removes code spans and the .raw/.text split has stopped "
        "meaning anything — re-measure before changing the field"
    )


def test_control_10_a_positive_extraction_claim_without_any_denial_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """The denial limb did not simply switch AW-2 off.

    The exemption is CONDITIONAL, and here its condition is absent: a bare
    positive claim with no denial anywhere in the sentence. Without this
    control, a limb that exempted unconditionally would ship green — which is
    exactly what sabotage 7a produces.
    """
    pages = _copied_tree(
        tmp_path,
        "CCF produces passage anchors from your documents as part of every "
        "assembly.",
    )
    assert sentences_claiming_passage_extraction(pages), (
        "AW-2 admitted a bare positive extraction claim carrying no denial at "
        "all — the denial limb has become unconditional and the obligation is "
        "switched off"
    )


def test_control_11_a_decoy_negation_does_not_exonerate(
    tmp_path: pathlib.Path,
) -> None:
    """The limb's three conditions, held one at a time.

    Three copied trees, three assertions, three messages naming which shape
    failed. If ANY half ever goes green, the limb has become the hole it was
    added to close.

    The (c) sentences are used VERBATIM and must not be paraphrased. They are
    the measured cases: under the two-condition form — vocabulary and ordering,
    with no pivot check — both were EXEMPTED outright, reported by nothing, and
    a paraphrase that happened to drop the pivot would pass under the very
    predicate this half exists to refuse, leaving the control vouching for
    nothing.
    """
    # (a) VOCABULARY — an unrelated negative clause is not a denial of
    # extraction. This is what a general negation vocabulary would exempt.
    decoy = _copied_tree(
        tmp_path / "a",
        "CCF produces passage anchors from documents, and no vector store is "
        "involved.",
    )
    assert sentences_claiming_passage_extraction(decoy), (
        "condition (i) failed: an out-of-vocabulary negation exonerated a "
        "positive extraction claim — EXTRACTION_DENIAL has been widened into "
        "a general negation vocabulary"
    )

    # (b) ORDERING — an in-vocabulary denial appended AFTER the claim cannot
    # retroactively withdraw it.
    trailing = _copied_tree(
        tmp_path / "b",
        "CCF produces passage anchors from documents, though no shipped "
        "pipeline is involved in the UBO example.",
    )
    assert sentences_claiming_passage_extraction(trailing), (
        "condition (ii) failed: a denial standing AFTER the extraction verb "
        "exonerated the claim — the limb has become position-blind"
    )

    # (c) PIVOT — a denial at the START of a sentence must not exempt a claim
    # that rides the clause after ``though`` or ``but``. Verbatim, measured.
    pivoted = _copied_tree(
        tmp_path / "c",
        "No shipped pipeline produces passage anchors, though CCF does "
        "extract them from documents.",
    )
    assert sentences_claiming_passage_extraction(pivoted), (
        "condition (iii) failed: a leading denial followed by a contrastive "
        "pivot exonerated the claim riding the clause after it — this is the "
        "exact sentence the two-condition form exempted"
    )
    sibling = _copied_tree(
        tmp_path / "d",
        "No shipped pipeline produces passage anchors from documents, but CCF "
        "extracts them from your documents anyway.",
    )
    assert sentences_claiming_passage_extraction(sibling), (
        "condition (iii) failed on its sibling measured case: a leading "
        "denial followed by ``but`` exonerated the claim after the pivot"
    )

    # (e) SENTENCE SCOPING under condition (ii). The denial is a complete,
    # correct sentence of its own; the overclaim is the NEXT sentence and the
    # denial qualifies nothing in it. The limb must not reach across the
    # boundary — and it did, measured, whenever the denial closed inside
    # markup, because ``[.!?]\s`` cannot see ``.**``. Verbatim: re-punctuating
    # this fixture with a plain ``. `` would make it pass under the very
    # SENTENCE_BREAK this half exists to refuse.
    across = _copied_tree(
        tmp_path / "e",
        "**No shipped pipeline produces passage anchors.** CCF extracts "
        "passage anchors from your documents on every assembly.",
    )
    # This half also watches the OTHER way sentence scoping can be lost: a
    # denial searched over the whole PARAGRAPH rather than the sentence exempts
    # the second sentence here just as an invisible boundary does. Measured —
    # that mutation turns this control and control 13 red and nothing else.
    assert sentences_claiming_passage_extraction(across), (
        "condition (ii) failed across a markup-closed sentence boundary: a "
        "denial that is its own complete sentence exempted an overclaim in the "
        "NEXT sentence — _prose.SENTENCE_BREAK has lost its markup-closer "
        "class, so sentence scoping silently became paragraph scoping"
    )

    # (f) CONDITION (iv), from the side that must stay GREEN. A sentence that
    # denies, crosses a boundary, and KEEPS denying is correct prose. Without
    # (iv), widening condition (iii) to coordinating joins would refuse it —
    # and would refuse the shipped caveat's ``so`` clause with it.
    still_denying = _copied_tree(
        tmp_path / "f",
        "No shipped pipeline extracts passage anchors from documents, and no "
        "shipped pipeline produces them either.",
    )
    assert sentences_claiming_passage_extraction(still_denying) == [], (
        "condition (iv) failed: a sentence that denies, crosses an ``and``, and "
        "denies again was reported as an overclaim. The widened clause-boundary "
        "vocabulary is only safe because a boundary counts as a TURN when the "
        "trailing clause has no denial of its own — restore that, do not narrow "
        "CONTRASTIVE_PIVOT back to adversatives only"
    )

    # (g) CONDITION (iii), the coordinating joins. All three measured EXEMPTED
    # at the Phase 22 close, and all three panel reviewers found the same hole:
    # modelling only ``though``/``but``/``however`` lets ``and`` and ``;``
    # through. VERBATIM.
    for index, sentence in enumerate(MEASURED_COORDINATING_JOINS):
        joined = _copied_tree(tmp_path / f"g{index}", sentence)
        assert sentences_claiming_passage_extraction(joined), (
            f"condition (iii) failed on {sentence!r} — a leading denial "
            "exonerated a claim riding a COORDINATING clause. "
            "CONTRASTIVE_PIVOT has been narrowed back to adversatives, which "
            "is the shape all three close reviewers independently reported"
        )

    # (h) CONDITION (i), the hyphen guard, ISOLATED. The only denial-vocabulary
    # hit is ``no pipeline`` inside ``pipeline-related``, and **no clause
    # boundary is crossed** — ``when`` is not one — so this half goes red if and
    # only if the hyphen guard is removed.
    #
    # The isolation is the point and it was got wrong first: the (g) sentences
    # are refused by the boundary widening as well, so they stay green with the
    # vocabulary sabotaged. A control that survives the mutation it names is
    # this module's own subject.
    unrelated_cost = _copied_tree(
        tmp_path / "h",
        "No pipeline-related cost is produced when CCF extracts passage "
        "anchors from documents.",
    )
    assert sentences_claiming_passage_extraction(unrelated_cost), (
        "condition (i) failed: a negation about pipeline COST satisfied a "
        "denial vocabulary that is supposed to take a PRODUCTION claim as its "
        "object, and exonerated an extraction claim in the same clause — the "
        "``no pipelines?\\b(?!-)`` hyphen guard is gone"
    )


def test_control_14_the_three_aw_1_conditions_are_held_one_at_a_time(
    tmp_path: pathlib.Path,
) -> None:
    """AW-1's conditions, each with its own tree and its own message.

    Four copied trees. If any assertion here ever inverts, AW-1 has either
    lost jurisdiction over the subsection bodies again or acquired an exemption
    broad enough to switch itself off.

    Every sentence below is VERBATIM and must not be paraphrased. They are the
    measured cases from the Phase 22 close review, and a paraphrase that
    happened to restate the approach noun inside the sentence would pass under
    the very predicate the (a) half exists to refuse.
    """
    # (a) ANCHORING — the subject is established in the HEADING and never
    # restated, so the body sentence carries only a pronoun. Measured ADMITTED
    # under sentence-scoped candidacy: three of the four candidate paragraphs on
    # the whole published tree were headings, and the bodies were unreachable.
    carried = _standalone(
        tmp_path / "a",
        "## RAG over a vector store\n\nIt cannot answer a question whose "
        "answer no single document states.",
    )
    assert sentences_asserting_a_capability_limit(carried), (
        "condition (i) failed: a naked capability claim in a subsection BODY, "
        "whose subject is established only in the subsection HEADING, was "
        "admitted — the heading carry in paragraphs_with_their_subject is gone "
        "and every comparison subsection is outside AW-1's jurisdiction"
    )

    # (b) RE-ANCHORING — the page's own line 331, verbatim. The limit is
    # predicated of THIS DEPLOYMENT, and it is the page conceding what it does
    # not do. Reporting it would be the gate demanding the page be less honest.
    conceded = _copied_tree(
        tmp_path / "b",
        "Extractive provenance over a document corpus is the one place on this "
        "page where a retrieval system does something this deployment does not "
        "do, and the page says so rather than routing around it.",
    )
    assert sentences_asserting_a_capability_limit(conceded) == [], (
        "condition (ii) failed: the page's own concession — a limit predicated "
        "of THIS DEPLOYMENT, standing after the approach noun — was reported as "
        "a claim about the approach. AW-1 is now demanding that the page stop "
        "admitting what it cannot do, which is the opposite of what D-02 asks"
    )

    # (b') RE-ANCHORING, the D-02 recast. The required form is a fact about the
    # QUESTION and it is written with a limit verb.
    recast = _copied_tree(
        tmp_path / "b2",
        "The deployment is compared against RAG over a vector store. The "
        "question itself has no way to be answered by reading one record, "
        "because the answer is a sum over two ownership paths.",
    )
    assert sentences_asserting_a_capability_limit(recast) == [], (
        "condition (ii) failed on D-02's REQUIRED recast: a fact about the "
        "question, in a paragraph that also names an approach, was reported as "
        "a claim about the approach — the gate now refuses the only form the "
        "page is permitted to use"
    )

    # (c) CONTRASTIVE FRAME — the same anchor order as (b), and the opposite
    # meaning. Without condition (iii), condition (ii) is a hole this walks
    # straight through.
    framed = _copied_tree(
        tmp_path / "c",
        "RAG over a vector store, unlike this deployment, cannot answer the "
        "question.",
    )
    assert sentences_asserting_a_capability_limit(framed), (
        "condition (iii) failed: a CCF subject introduced by ``unlike`` "
        "re-anchored a limit that is plainly predicated of RAG — the "
        "CONTRASTIVE_FRAME guard is gone, so condition (ii) has become an "
        "exemption any author can reach by naming CCF anywhere ahead of the verb"
    )


#: The six ``X can't Y`` spellings measured ADMITTED at the Phase 22 close, with
#: ``Vector stores`` as the subject in every one so the only variable is the
#: verb. VERBATIM: each is a real miss, and the first is ``DOCS-15``'s own word.
MEASURED_LIMIT_SPELLINGS = (
    "Vector stores lack an ownership path.",
    "Vector stores will never compute a sum over two paths.",
    "Vector stores are not able to compute a sum over two paths.",
    "Vector stores simply do not compute a sum over two paths.",
    "Vector stores stop short of computing a sum over two paths.",
    "Vector stores miss the ownership path entirely.",
)


def test_control_15_every_measured_limit_spelling_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """``LIMIT_VERB``'s vocabulary, held against the spellings it let through.

    One tree per spelling, so a red names the spelling rather than the set. A
    single tree carrying all six would go green the moment any ONE of them was
    caught, which is the shape of control this project keeps finding vacuous.

    The cross-assertion matters as much as the refusal: none of these is an
    AW-2 offence, so AW-2 must stay silent on all six. A LIMIT_VERB widening
    that started firing AW-2 would mean the two obligations had stopped testing
    different things.

    Built on :func:`_standalone` so that the only thing varying is the verb:
    the subject ``Vector stores`` is in ``EXTERNAL_APPROACH`` on its own, and
    the heading names no approach, so a red here is a red about the verb.
    """
    for index, sentence in enumerate(MEASURED_LIMIT_SPELLINGS):
        pages = _standalone(tmp_path / f"v{index}", sentence)
        assert sentences_asserting_a_capability_limit(pages), (
            f"AW-1 admitted {sentence!r} — LIMIT_VERB has lost the spelling "
            "that carries it. This set is the measured miss list from the "
            "Phase 22 close; the first entry is the word DOCS-15 itself uses"
        )
        assert sentences_claiming_passage_extraction(pages) == [], (
            f"AW-2 fired on {sentence!r}, which is an AW-1 shape carrying no "
            "passage-anchor claim at all — the two obligations are no longer "
            "testing different things"
        )


#: The three coordinating-join evasions measured EXEMPTED at the Phase 22
#: close. VERBATIM: each is a real miss, and a paraphrase that happened to use
#: ``but`` instead of ``and`` would pass under the very predicate the (g) half
#: exists to refuse.
MEASURED_COORDINATING_JOINS = (
    "No shipped pipeline produces passage anchors from documents, and CCF "
    "extracts them anyway.",
    "No pipeline produces passage anchors; CCF extracts them from documents.",
    "There is no pipeline for this question and CCF produces passage anchors "
    "from documents.",
)

#: A heading that names no external approach, so a control built on it tests
#: its sentence's vocabulary and not the heading's. Asserted inside control 16
#: rather than trusted.
NEUTRAL_HEADING = "# A control page"

#: The three claims measured ADMITTED at the Phase 22 close **written in the
#: page's own nouns** — line 320 says "document search", line 332 says "a
#: retrieval system" — none of which was in ``EXTERNAL_APPROACH``. VERBATIM.
MEASURED_APPROACH_NOUNS = (
    "A retrieval system cannot answer a question whose answer no single "
    "document states.",
    "A document search is unable to compute a sum over two ownership paths.",
    "An embedding index has no way to represent an ownership path.",
)


def test_control_16_the_pages_own_nouns_for_the_three_approaches_are_refused(
    tmp_path: pathlib.Path,
) -> None:
    """``EXTERNAL_APPROACH`` covers the vocabulary the page actually writes.

    A subject vocabulary that misses the words the guarded page uses is a
    vocabulary that guards a different page. All three of these were admitted
    at the close, and the evasion needed no ingenuity: it needed a thesaurus the
    page had already opened.

    **This control builds its own page rather than appending to the shipped
    one, and the reason is that the appending form was measured VACUOUS.** The
    adoption page's last heading is ``## Where a document search is stronger,
    and this is not``, which names an approach — so an appended paragraph
    inherits candidacy from that heading no matter what noun it uses, and two
    of the three vocabulary sabotages below passed green on the first draft of
    this control. A control that survives the mutation it exists to catch is
    the exact defect this module is written against, so the fixture changed
    rather than the assertion. Control 9 sets the same precedent for the same
    reason.

    The neutral heading is asserted, not assumed: a heading that drifted into
    naming an approach would silently reintroduce the vacuity.
    """
    assert EXTERNAL_APPROACH.search(NEUTRAL_HEADING) is None, (
        f"the control's own heading {NEUTRAL_HEADING!r} names an external "
        "approach, so every sentence below is a candidate through the heading "
        "carry and the vocabulary sabotages this control exists to catch would "
        "pass green — which is what happened on this control's first draft"
    )
    for index, sentence in enumerate(MEASURED_APPROACH_NOUNS):
        assert sentences_asserting_a_capability_limit(
            _standalone(tmp_path / f"n{index}", sentence)
        ), (
            f"AW-1 admitted {sentence!r} — EXTERNAL_APPROACH does not name the "
            "subject, so the claim was never a candidate. The page writes this "
            "noun itself; a vocabulary that misses it guards nothing"
        )


#: The two overclaims measured ADMITTED at the Phase 22 close **in the page's
#: own house spelling** — it writes ``passage_anchor`` backticked at line 321.
#: VERBATIM, backticks included: strip them and the sentences pass under the
#: predicate this control exists to refuse.
MEASURED_IDENTIFIER_SPELLINGS = (
    "CCF produces a `passage_anchor` for every claim it extracts from your "
    "documents.",
    "The unstructured pipeline extracts `passage_anchor` values from PDFs at "
    "ingest.",
)


def test_control_17_the_backticked_identifier_spelling_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """AW-2's negative half sees what its positive half has always seen.

    Two things must both hold and each has its own message, because they fail
    for different reasons: ``PASSAGE_ANCHOR`` must carry the underscored
    identifier, and the predicate must scan a field the identifier survives in.
    Either alone leaves the evasion open.

    The second assertion is the field one and it is written as a property of
    ``Paragraph`` rather than of the predicate: if ``strip_markup`` ever stopped
    deleting code spans, the ``.raw``/``.text`` split would have stopped meaning
    anything and this control would be passing for a reason unrelated to what it
    claims. Control 9 makes the same assertion for the positive half.
    """
    assert PASSAGE_ANCHOR.search("passage_anchor") is not None, (
        "PASSAGE_ANCHOR no longer matches the underscored identifier, so the "
        "spelling the guarded page uses at line 321 is invisible to AW-2's "
        "negative half"
    )
    for index, sentence in enumerate(MEASURED_IDENTIFIER_SPELLINGS):
        pages = _copied_tree(tmp_path / f"i{index}", sentence)
        assert not any(
            "passage_anchor" in par.text for _, par in _prose.iter_paragraphs(pages)
        ), (
            "the injected identifier survived strip_markup into Paragraph.text, "
            "so this control would pass with the predicate reading .text alone "
            "— the fixture has lost its backticks, or strip_markup has stopped "
            "removing code spans"
        )
        assert sentences_claiming_passage_extraction(pages), (
            f"AW-2 admitted {sentence!r} — the page's own house spelling is an "
            "evasion. Either PASSAGE_ANCHOR has lost the underscored form, or "
            "the negative predicate is back to reading Paragraph.text only "
            "while the positive half reads .raw"
        )


def test_control_18_the_two_caveat_halves_in_different_paragraphs_are_refused(
    tmp_path: pathlib.Path,
) -> None:
    """The property the positive assertion's own TITLE names, finally watched.

    ``test_the_passage_anchor_caveat_states_both_halves_in_one_paragraph`` says
    *in one paragraph* and nothing measured it. Splitting the halves across two
    paragraphs turned NO test red, so the words "in one paragraph" were carried
    by the assertion's name rather than by the assertion. Control 7 does not
    reach it: 7 removes the absence half from the page entirely, which stays red
    under a page-scoped predicate too.

    The scoping matters for the reason the assertion's own docstring gives: half
    a caveat still parses as honest. A contract half at the top of a page and an
    absence half four screens down are not a caveat a reader reads together.

    Fixture integrity comes first and is what stops this from being a control
    that passes because its page carries neither half.
    """
    page = tmp_path / "split.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        "# A control page\n"
        "\n"
        "The lineage entry carries a `passage_anchor` field and the contract\n"
        "behind it ships: `D-IMPL-46` rules the Protocol that fills it.\n"
        "\n"
        "Some entirely unrelated paragraph stands between the two halves, which\n"
        "is the whole point of the fixture.\n"
        "\n"
        "No shipped pipeline produces passage anchors from documents, because\n"
        "the unstructured ingestion pattern was never built.\n",
        encoding="utf-8",
    )
    paragraphs = [par for par in _prose.page_paragraphs(page) if not par.fenced]
    assert any(CAVEAT_CONTRACT.search(par.raw) for par in paragraphs), (
        "the fixture carries no contract half at all, so the refusal below "
        "would prove nothing about paragraph scoping"
    )
    assert any(CAVEAT_ABSENCE.search(par.text) for par in paragraphs), (
        "the fixture carries no absence half at all, so the refusal below "
        "would prove nothing about paragraph scoping"
    )
    assert not any(
        CAVEAT_CONTRACT.search(par.raw) and CAVEAT_ABSENCE.search(par.text)
        for par in paragraphs
    ), "the fixture put both halves in ONE paragraph; it is not testing the split"

    assert paragraphs_carrying_the_caveat([page]) == [], (
        "AW-2's positive predicate accepted a caveat whose two halves sit in "
        "DIFFERENT paragraphs. The assertion this backs is named 'states both "
        "halves in one paragraph'; the scoping is the paragraph, not the page, "
        "because half a caveat four screens from its other half is not a caveat "
        "a reader reads"
    )


def test_control_13_the_caveat_clause_swapped_for_an_overclaim_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """The Phase 22 close's composed defect, held as one control.

    Both AW-2 obligations reported GREEN on a page whose caveat clause had been
    replaced by the exact overclaim the obligations exist to prevent, and it
    took two independent defects to do it:

    * ``CAVEAT_ABSENCE`` bounded its gaps with ``[^.]``, which excludes the full
      stop and nothing else — so ``no shipped pipeline`` from the denial
      fragment stitched across ``!`` to ``passage anchors ... documents`` in the
      overclaim, and the POSITIVE obligation found a caveat that was gone; and
    * ``_prose.SENTENCE_BREAK`` could not see ``.**``, so the denial and the
      claim were one sentence, the denial preceded every extraction verb, no
      pivot stood between them, and the NEGATIVE obligation's limb exempted the
      overclaim outright.

    Control 3 does not reach this: the mutation is IN the page, so the
    unmodified-copy baseline carries it. This control substitutes rather than
    appends for the same reason.

    Both halves are asserted here rather than split, because the finding is
    that they compose. Either one alone leaves the page reported honest.
    """
    page = _copy(tmp_path)
    text = page.read_text(encoding="utf-8")
    assert CAVEAT_CLAUSE in text, (
        "the fixture's anchor clause is gone from the shipped page, so the "
        "substitution below is a no-op and both refusals would prove nothing"
    )
    text = text.replace(CAVEAT_CLAUSE, CAVEAT_CLAUSE_SWAPPED_FOR_AN_OVERCLAIM)
    page.write_text(text, encoding="utf-8")

    assert paragraphs_carrying_the_caveat([page]) == [], (
        "AW-2's positive obligation still found the caveat on a page whose "
        "caveat clause has been replaced by an overclaim — CAVEAT_ABSENCE is "
        "stitching its three tokens across a sentence terminal again, so its "
        "bounded gaps must exclude every terminal (`[^.!?]`), not only `.`"
    )
    assert sentences_claiming_passage_extraction([page]), (
        "AW-2's negative obligation admitted the substituted overclaim — the "
        "denial fragment ahead of it exempted it, which is what happens when "
        "_prose.SENTENCE_BREAK cannot see the markup-closed boundary between "
        "the two"
    )


# --------------------------------------------------------------------------
# D-06 — the per-claim symbol resolver. `22-CONTEXT.md` rules this STRETCH and
# NON-BLOCKING, and explicitly not a substitute for the D-04 gate above. It
# landed because the decision rule's three conditions all held: the module was
# green with every sabotage reverted, `make gate-tools` was exit 0, and the
# executing context was under half consumed.
#
# **What this adds over `cite03-node-id`, stated plainly rather than left to be
# assumed, because a duplicate check is worse than no check.** The citation
# lint already runs `cite03` over `public/`, and it resolves the same node ids
# through the same functions — this test imports them rather than
# reimplementing either, so the two cannot drift. It is stronger in exactly one
# place: `cite03` treats a node id whose PATH does not resolve as UNCHECKED,
# because in general prose `module.py::test_name` is more often a placeholder
# than a broken pointer. On the published tree that policy leaves a hole — a
# node id on a page is an invitation to the reader to go and open it, and one
# pointing at a file that no longer exists is exactly the DCD-02 defect this
# phase's page exists to model the opposite of. Here an unresolvable path is a
# FAILURE, not a shrug.
#
# It is also reached by a different gate: this runs under `make gate-tools` and
# the CI docs job, where `cite03` runs under `make lint`.
# --------------------------------------------------------------------------


def published_node_ids(
    pages: list[pathlib.Path] | None = None,
) -> list[tuple[str, int, str, str]]:
    """``(page, lineno, cited path, symbol)`` for every node id in `pages`.

    Defaults to the whole published tree. **The `pages` parameter exists so
    :func:`unresolved_node_ids` can call this rather than re-implement it** —
    it used to carry its own copy of the same line scan, which is two copies of
    one scoping rule, and this package's own ``_prose`` docstring records what
    three copies of a scoping rule turn into.

    Line-scoped on purpose and NOT a violation of this package's
    paragraph-scoping rule: a node id is a token, not a claim, so there is no
    qualification two lines down that could change its reading. The rule exists
    for prose whose unit of meaning is the paragraph.
    """
    found: list[tuple[str, int, str, str]] = []
    for page in _prose.published_pages() if pages is None else pages:
        for lineno, line in enumerate(
            page.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for match in NODE_ID.finditer(line):
                found.append(
                    (
                        _prose.relative(page),
                        lineno,
                        match.group("path"),
                        match.group("symbol"),
                    )
                )
    return found


def unresolved_node_ids(pages: list[pathlib.Path]) -> list[str]:
    """``page:line — reason`` for every node id in `pages` that does not resolve.

    The scan is :func:`published_node_ids`; this function is only the
    resolution. Keeping them one scan is what stops a page from being read by
    the floor and not by the resolver, or the reverse.
    """
    base = _prose.REPO_ROOT
    index = repo_index(base)
    offenders: list[str] = []
    for relative, lineno, cited, symbol in published_node_ids(pages):
        target, ambiguous = resolve_cited(cited, base, index)
        if target is None:
            offenders.append(
                f"{relative}:{lineno} — {cited}::{symbol} names"
                f" {'an ambiguous' if ambiguous else 'no'} file in the repo"
            )
            continue
        source = target.read_text(encoding="utf-8", errors="replace")
        if symbol not in symbol_spans(source, target):
            offenders.append(f"{relative}:{lineno} — {cited} defines no {symbol!r}")
    return offenders


def test_the_published_tree_carries_node_ids_to_resolve() -> None:
    """D-06's non-vacuity floor.

    A resolver that reports green over an empty set is worse than none.
    Twenty-two node ids are written across the published tree today, all of
    them on this phase's page.
    """
    found = published_node_ids()
    assert found, (
        "no path::symbol node id appears anywhere under "
        f"{_prose.PUBLIC_DIR} — the D-06 resolver is passing over an empty set"
    )


def test_every_published_node_id_resolves() -> None:
    offenders = unresolved_node_ids(_prose.published_pages())
    assert not offenders, (
        "D-06: a published page cites a symbol that does not resolve. A node "
        "id on a page is an invitation to the reader to open it, so a stale "
        "one is a strong-looking claim with nothing behind it — re-resolve it "
        "against the tree, or remove it: " + "; ".join(offenders)
    )


def test_control_12_a_renamed_symbol_and_a_missing_file_are_both_refused(
    tmp_path: pathlib.Path,
) -> None:
    """D-06's injected control, in two halves — symbol, then path.

    The second half is the one ``cite03-node-id`` would let through: an
    unresolvable path is UNCHECKED there and a FAILURE here, which is the
    entire reason this test earns its place beside the lint rather than
    duplicating it.
    """
    renamed = _copy(tmp_path / "symbol")
    text = renamed.read_text(encoding="utf-8")
    assert "src/ccf/client/client.py::ProductClient" in text, (
        "the fixture's anchor node id is gone; the mutation below would be a "
        "no-op and the refusal would prove nothing"
    )
    renamed.write_text(
        text.replace(
            "src/ccf/client/client.py::ProductClient",
            "src/ccf/client/client.py::ProductClientX",
        ),
        encoding="utf-8",
    )
    offenders = unresolved_node_ids([renamed])
    assert any("ProductClientX" in offender for offender in offenders), (
        "a renamed symbol resolved anyway — the resolver is reading nothing, "
        f"got {offenders}"
    )

    missing = _copy(tmp_path / "path")
    missing.write_text(
        text.replace(
            "src/ccf/client/client.py::ProductClient",
            "src/ccf/client/no_such_module.py::ProductClient",
        ),
        encoding="utf-8",
    )
    offenders = unresolved_node_ids([missing])
    assert any("no_such_module.py" in offender for offender in offenders), (
        "a node id naming a file that does not exist was admitted — this is "
        "the half cite03 leaves UNCHECKED, and it is the reason this test "
        f"exists, so it must not be green: {offenders}"
    )
