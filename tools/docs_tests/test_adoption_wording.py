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

import pytest

from tools.docs_tests import _prose

#: AW-1's subjects — the external approaches the page is compared against.
#: **Matched against ``Paragraph.text``**: these are prose nouns, and an
#: approach named inside a code span is a reference to an identifier rather
#: than a claim about a tool. Word-bounded where a bare substring would
#: over-match: unbounded ``RAG`` also matches "storage", "paragraph",
#: "coverage", "leverage" and "average".
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
    r"|chunked documents",
    re.IGNORECASE,
)

#: AW-1's offence — the ``X can't Y`` shape. **Matched against
#: ``Paragraph.text``**: it is ordinary prose, and a limit verb inside a code
#: span is a literal, not an assertion. Word-bounded on purpose; an unbounded
#: ``no`` matches "note" and "nothing" and would make every paragraph an
#: offender.
LIMIT_VERB = re.compile(
    r"\bcannot\b"
    r"|\bcan't\b"
    r"|\bcan not\b"
    r"|\bunable to\b"
    r"|\blacks\b"
    r"|\blacking\b"
    r"|\bfails to\b"
    r"|\bfail to\b"
    r"|\bhas no\b"
    r"|\bhave no\b"
    r"|\bdoes not support\b"
    r"|\bdoesn't support\b"
    r"|\bdo not support\b"
    r"|\bincapable of\b"
    r"|\bno way to\b"
    r"|\bfalls short\b",
    re.IGNORECASE,
)

#: AW-2's subject. **Matched against ``Paragraph.text``**: the prose forms are
#: what a reader takes away. **Never a bare ``passage``** — ``public/charter.md``
#: writes *"A page that names a proprietary passage fails the build"* in an
#: entirely unrelated sense, and a bare token would report that correct
#: sentence as an offender. Note that the underscored identifier
#: ``passage_anchor`` is deliberately NOT matched here; it belongs to
#: ``CAVEAT_CONTRACT``, which reads ``.raw``.
PASSAGE_ANCHOR = re.compile(
    r"passage anchors?|passage-level lineage",
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
EXTRACTION_DENIAL = re.compile(
    r"no shipped pipeline"
    r"|no such pipeline"
    r"|no pipeline"
    r"|was never built"
    r"|never built"
    r"|does not produce"
    r"|do not produce"
    r"|does not extract"
    r"|do not extract"
    r"|nothing in the shipped",
    re.IGNORECASE,
)

#: The denial limb's condition (iii). **Matched against ``Paragraph.text``**:
#: a pivot written inside a code span is not a pivot a reader reads. A sentence
#: that opens with a denial and then TURNS against it is asserting the claim on
#: the far side of the pivot, and conditions (i) and (ii) alone exempt it
#: outright — measured, not supposed. ``so`` is absent from this vocabulary on
#: purpose: the shipped caveat denies and then EXPLAINS, which is the
#: construction the limb exists to permit.
CONTRASTIVE_PIVOT = re.compile(
    r"\bthough\b"
    r"|\bbut\b"
    r"|\bhowever\b"
    r"|\byet\b"
    r"|\bwhile\b"
    r"|\bwhereas\b"
    r"|\balthough\b",
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
CAVEAT_ABSENCE = re.compile(
    r"no shipped pipeline\b[^.]{0,80}\bpassage anchors\b[^.]{0,40}\bdocuments\b",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# Predicates. Each returns openable ``page:line — sentence`` strings, because
# a red run whose message cannot be opened is a red run nobody acts on.
# Paragraph is the unit of CANDIDACY; sentence is the unit of JUDGEMENT.
# --------------------------------------------------------------------------


def sentences_asserting_a_capability_limit(
    pages: list[pathlib.Path],
) -> list[str]:
    """AW-1: ``page:line — sentence`` for each naked ``X can't Y``.

    A paragraph naming an external approach is a candidate; the offence is
    judged on the SENTENCE carrying the approach, so a limit verb three
    sentences away — attached to something else entirely — does not condemn a
    correct sentence, and a negation three sentences away does not exonerate an
    incorrect one.
    """
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages):
        for match in EXTERNAL_APPROACH.finditer(paragraph.text):
            sentence = _prose.sentence_at(paragraph.text, match.start())
            if LIMIT_VERB.search(sentence) is None:
                continue
            report = f"{_prose.relative(page)}:{paragraph.lineno} — {sentence.strip()}"
            if report not in offenders:
                offenders.append(report)
    return offenders


def sentences_claiming_passage_extraction(
    pages: list[pathlib.Path],
) -> list[str]:
    """AW-2, negative: ``page:line — sentence`` for each extraction claim.

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
    (iii) **Pivot.** No ``CONTRASTIVE_PIVOT`` stands between that denial and
          any later extraction verb. Without this, a denial at the START of a
          sentence exempts everything after it — measured: *"No shipped
          pipeline produces passage anchors, though CCF does extract them from
          documents."* was EXEMPTED under the two-condition form.

    In one line: **the limb exempts a sentence that denies and then EXPLAINS,
    and refuses one that denies and then TURNS.** The shipped caveat joins its
    halves with ``so``, which is not a pivot, so it stays exempt.

    Do not delete a condition as clutter. Each one is watched by its own
    sabotage mutation and its own half of control 11; the mutation count tracks
    the condition count, and a fourth condition would ship with a fourth
    mutation.
    """
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages):
        for match in PASSAGE_ANCHOR.finditer(paragraph.text):
            sentence = _prose.sentence_at(paragraph.text, match.start())
            verbs = [found.start() for found in EXTRACTION_VERB.finditer(sentence)]
            if not verbs or DOCUMENT_SOURCE.search(sentence) is None:
                continue
            denials = [found.start() for found in EXTRACTION_DENIAL.finditer(sentence)]
            if denials:
                denial = min(denials)
                precedes = denial < min(verbs)
                turns = any(
                    denial < pivot.start() < verb
                    for pivot in CONTRASTIVE_PIVOT.finditer(sentence)
                    for verb in verbs
                )
                if precedes and not turns:
                    # The sentence DENIES extraction rather than asserting it,
                    # and denies it in the one word order that cannot be read
                    # the other way: an in-vocabulary denial, standing ahead of
                    # every extraction verb, with nothing turning against it
                    # before one. That is a legitimate way to be right, and it
                    # is the way ROADMAP criterion 6 requires the caveat to be
                    # written.
                    continue
            report = f"{_prose.relative(page)}:{paragraph.lineno} — {sentence.strip()}"
            if report not in offenders:
                offenders.append(report)
    return offenders


def paragraphs_carrying_the_caveat(
    pages: list[pathlib.Path],
) -> list[str]:
    """AW-2, positive: ``page:line`` for each paragraph with BOTH halves.

    **One ``Paragraph`` object, two fields, and that is deliberate.**
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
    paragraph named RAG, a vector store or a semantic layer at all. Ten
    candidate sentences match today.
    """
    triggered = [
        f"{_prose.relative(page)}:{paragraph.lineno}"
        for page, paragraph in _prose.iter_paragraphs(_prose.published_pages())
        if EXTERNAL_APPROACH.search(paragraph.text)
    ]
    assert triggered, (
        "no published paragraph matches EXTERNAL_APPROACH, so AW-1 is "
        "filtering an empty set and its green means nothing — this is AW-1's "
        "corpus floor and it is red"
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

    Two things are asserted, and both are needed. First, that the published
    tree really does carry a sentence matching ``PASSAGE_ANCHOR``,
    ``EXTRACTION_VERB`` and ``DOCUMENT_SOURCE`` all three — so there is a
    candidate the limb has to exempt. Second, that the predicate nonetheless
    reports no offender. Without the first, deleting the limb would leave the
    build green and nobody would find out; without the second, the caveat the
    page is required to carry would be reported as the overclaim it denies.
    """
    pages = _prose.published_pages()
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
