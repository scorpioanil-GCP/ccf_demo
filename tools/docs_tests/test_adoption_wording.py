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

import pytest

from tools.docs_tests import _prose
from tools.lints.citations import NODE_ID, repo_index, resolve_cited, symbol_spans

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


# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may scan nothing.
#
# The fixture source is the page THIS PHASE SHIPS, not the adopter's guide. An
# injected violation appended to the adoption page proves the gate guards the
# page it exists for, and the unmodified-copy baseline (control 3) then also
# proves the shipped page is clean. Every control mutates a COPY under
# ``tmp_path``; nothing here writes to ``public/``.
# --------------------------------------------------------------------------

#: The page under guard, repo-relative inside the published tree.
ADOPTION_PAGE = "concepts/answers-no-document-contains.md"

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
    assert sentences_claiming_passage_extraction(across), (
        "condition (ii) failed across a markup-closed sentence boundary: a "
        "denial that is its own complete sentence exempted an overclaim in the "
        "NEXT sentence — _prose.SENTENCE_BREAK has lost its markup-closer "
        "class, so sentence scoping silently became paragraph scoping"
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


def published_node_ids() -> list[tuple[str, int, str, str]]:
    """``(page, lineno, cited path, symbol)`` for every node id in `public/`.

    Line-scoped on purpose and NOT a violation of this package's
    paragraph-scoping rule: a node id is a token, not a claim, so there is no
    qualification two lines down that could change its reading. The rule exists
    for prose whose unit of meaning is the paragraph.
    """
    found: list[tuple[str, int, str, str]] = []
    for page in _prose.published_pages():
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
    """``page:line — reason`` for every node id in `pages` that does not resolve."""
    base = _prose.REPO_ROOT
    index = repo_index(base)
    offenders: list[str] = []
    for page in pages:
        for lineno, line in enumerate(
            page.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for match in NODE_ID.finditer(line):
                cited, symbol = match.group("path"), match.group("symbol")
                target, ambiguous = resolve_cited(cited, base, index)
                if target is None:
                    offenders.append(
                        f"{_prose.relative(page)}:{lineno} — {cited}::{symbol} names"
                        f" {'an ambiguous' if ambiguous else 'no'} file in the repo"
                    )
                    continue
                source = target.read_text(encoding="utf-8", errors="replace")
                if symbol not in symbol_spans(source, target):
                    offenders.append(
                        f"{_prose.relative(page)}:{lineno} — {cited} defines no"
                        f" {symbol!r}"
                    )
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
