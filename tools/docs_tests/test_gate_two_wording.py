"""Criterion 8 — no published page reframes Gate 2 as an independence check.

**The corrected fact.** Gate 2 (lineage strict equality, ``INV-CH7-47``)
verifies **assembly-path integrity**: the Control Plane claim as transcribed
into the Contract, against the engine's execution of the plan. It is *not* an
independent witness of whether the claim was right in the first place, because
:meth:`ccf.projection.engine.ProjectionEngine.execute` builds
``operators_invoked`` and ``steps`` in one loop over the same operator plan —
so it has no return path where invoked ≠ planned. The ruling of record is
``docs/DECISIONS.md`` **D-IMPL-86** and its correction of 2026-08-05, whose
words are the ones worth keeping: *"the engine is a faithful transcriber of the
plan, not an independent witness."* The canonical statement lives at
``src/ccf/deployment/__init__.py`` lines 72-79 and is copied, never paraphrased
(RESEARCH P-4).

**Why a standing gate rather than a sweep.** Plan 15.1-20 already swept
``public/`` correct, so this module is green at HEAD over the pages that exist
today. Its subject is the pages that do *not* exist yet: a phase that rewrites
forty-one published pages will restate what Gate 2 does many times, and the
independence framing is the natural thing to write if you have not read
D-IMPL-86. A one-off sweep protects the tree it swept; a gate protects
everything written afterwards.

**Two assertions, deliberately different in shape.**

*Negative* — the direct reintroduction. A paragraph that talks about Gate 2 and
calls something "independent" must be negating the claim, not making it. The
negation is scoped to the **sentence** carrying the word, not to the paragraph,
so a paragraph cannot be exonerated by a "not" that belongs elsewhere in it.

*Positive* — the subtler reintroduction, which uses none of the trigger words.
A paragraph that **characterizes what Gate 2 verifies or establishes** must
carry the correction. "Gate 2 verifies that the declared operator set matches
the executed one" contains no "independent" anywhere and is exactly the
sentence this phase must not ship.

The positive trigger is characterization, not mention, and that boundary is
load-bearing. Two paragraphs in the tree today name lineage strict equality as
one item in a list of the three validation gates
(``public/concepts/invariants.md`` and ``public/concepts/replay-anatomy.md``)
and assert nothing whatever about independence. Requiring the correction in a
bare enumeration would force padding into prose that is already correct, which
is how a gate teaches authors to write worse pages to satisfy it.
"""

from __future__ import annotations

import pathlib
import re
import shutil

import pytest

from tools.docs_tests import _prose

#: The subject. ``Gate 2`` is included alongside the invariant id and the long
#: name because published prose uses all three interchangeably, and a gate that
#: reads only the formal id is defeated by an author writing English.
GATE_TWO = re.compile(
    r"INV-CH7-47|lineage strict equality|\bGate 2\b",
    re.IGNORECASE,
)

#: The correction that must be present when Gate 2's job is described.
CORRECTION = re.compile(r"assembly-path integrity", re.IGNORECASE)

#: Verbs that turn a *mention* of Gate 2 into a *characterization* of it. A
#: paragraph containing one of these is making a claim about what the gate
#: establishes, and therefore owes the reader the correction.
CHARACTERIZES = re.compile(
    r"\b(?:verif(?:y|ies|ying)|establish(?:es|ing)?|prove[sd]?|proving"
    r"|witness(?:es|ing)?|confirm(?:s|ing)?|guarantee(?:s|ing)?"
    r"|attest(?:s|ing)?|demonstrat(?:e|es|ing))\b",
    re.IGNORECASE,
)

#: The claim being guarded against.
INDEPENDENCE = re.compile(r"\bindependent(?:ly)?\b", re.IGNORECASE)

#: Tokens that turn an independence mention into a denial of one. Word-bounded
#: on purpose: an unbounded ``not`` matches "nothing", "note" and "another",
#: which would exonerate every paragraph in the tree.
NEGATION = re.compile(
    r"\b(?:not|never|cannot|rather than|instead of|no)\b",
    re.IGNORECASE,
)


def paragraphs_missing_the_correction(
    pages: list[pathlib.Path],
) -> list[str]:
    """`page:line` for every paragraph that characterizes Gate 2 without it."""
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages):
        if not GATE_TWO.search(paragraph.text):
            continue
        if not CHARACTERIZES.search(paragraph.text):
            continue
        if CORRECTION.search(paragraph.text):
            continue
        if INDEPENDENCE.search(paragraph.text) and _denies_independence(paragraph.text):
            # The paragraph makes the point in the negative rather than by
            # naming the correction. That is a legitimate way to be right.
            continue
        offenders.append(f"{_prose.relative(page)}:{paragraph.lineno}")
    return offenders


def _denies_independence(text: str) -> bool:
    """Whether every ``independent`` in `text` sits in a negating sentence."""
    matches = list(INDEPENDENCE.finditer(text))
    if not matches:
        return False
    return all(
        NEGATION.search(_prose.sentence_at(text, match.start())) is not None
        for match in matches
    )


def paragraphs_asserting_independence(
    pages: list[pathlib.Path],
) -> list[str]:
    """`page:line — sentence` for every affirmative independence claim."""
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages):
        if not GATE_TWO.search(paragraph.text):
            continue
        for match in INDEPENDENCE.finditer(paragraph.text):
            sentence = _prose.sentence_at(paragraph.text, match.start())
            if NEGATION.search(sentence) is None:
                offenders.append(
                    f"{_prose.relative(page)}:{paragraph.lineno} — {sentence.strip()}"
                )
    return offenders


# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# WR-04: a CWD-relative walk scanned zero files and the gate passed over
# nothing.
# `tools/publish_scan_tests/test_docstring_leaks.py::test_the_walk_does_not_depend_on_the_process_cwd`
# is the model.
# --------------------------------------------------------------------------


def test_the_published_tree_is_populated() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), f"missing published tree: {_prose.PUBLIC_DIR}"
    pages = _prose.sdk_prose_pages()
    assert pages, f"no markdown pages under {_prose.PUBLIC_DIR}"
    assert any(
        GATE_TWO.search(paragraph.text)
        for _, paragraph in _prose.iter_paragraphs(pages)
    ), "no published paragraph mentions Gate 2 — this gate is scanning nothing"


def test_the_positive_assertion_has_something_to_assert_over() -> None:
    """At least one published paragraph *characterizes* Gate 2.

    The positive assertion below is a filter, and a filter that matches nothing
    passes forever. Two paragraphs trigger it today —
    ``public/reference/artifacts/product-registration.md`` and
    ``public/tutorial/adopters-guide.md`` — and both carry the correction. If
    this ever fails, the assertion has stopped scanning and the "green" it
    reports means nothing.
    """
    triggered = [
        f"{_prose.relative(page)}:{paragraph.lineno}"
        for page, paragraph in _prose.iter_paragraphs(_prose.sdk_prose_pages())
        if GATE_TWO.search(paragraph.text) and CHARACTERIZES.search(paragraph.text)
    ]
    assert triggered, (
        "no published paragraph characterizes what Gate 2 verifies, so the "
        "positive assertion is passing over an empty set"
    )


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _prose.sdk_prose_pages(), "the walk resolved against the CWD, not the repo"


# --------------------------------------------------------------------------
# The two assertions over the tree as it stands.
# --------------------------------------------------------------------------


def test_every_characterization_of_gate_two_carries_the_correction() -> None:
    offenders = paragraphs_missing_the_correction(_prose.sdk_prose_pages())
    assert not offenders, (
        "published paragraphs describe what Gate 2 verifies without saying it "
        "verifies assembly-path integrity — see D-IMPL-86 and its correction "
        "of 2026-08-05, and copy the canonical sentence from "
        "src/ccf/deployment/__init__.py:72-79: " + ", ".join(offenders)
    )


def test_no_published_paragraph_asserts_gate_two_independence() -> None:
    offenders = paragraphs_asserting_independence(_prose.sdk_prose_pages())
    assert not offenders, (
        "published prose frames Gate 2 as a check between independently "
        "authored sets. The engine is a faithful transcriber of the plan, not "
        "an independent witness (D-IMPL-86): " + "; ".join(offenders)
    )


# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may scan nothing.
# Each injects a violation into a COPY of a real page and asserts refusal.
# --------------------------------------------------------------------------


def _copied_tree(tmp_path: pathlib.Path, extra: str) -> list[pathlib.Path]:
    """A copy of a real published page with `extra` appended."""
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    assert source.is_file(), f"control fixture source missing: {source}"
    target = tmp_path / source.name
    shutil.copy(source, target)
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n\n" + extra + "\n")
    return [target]


def test_the_gate_refuses_an_injected_affirmative_independence_claim(
    tmp_path: pathlib.Path,
) -> None:
    pages = _copied_tree(
        tmp_path,
        "Lineage strict equality compares two independently authored sets, "
        "which is what makes it trustworthy.",
    )
    assert paragraphs_asserting_independence(pages), (
        "the gate admitted an affirmative independence claim — it is scanning "
        "nothing, or the vocabulary has drifted"
    )


def test_the_gate_refuses_a_characterization_missing_the_correction(
    tmp_path: pathlib.Path,
) -> None:
    # No trigger word anywhere: this is the subtle reintroduction, and the
    # negative assertion alone would pass it.
    pages = _copied_tree(
        tmp_path,
        "Gate 2 verifies that the operator set the product declares matches "
        "the set the engine resolved while executing the plan.",
    )
    assert paragraphs_missing_the_correction(pages), (
        "the gate admitted a characterization of Gate 2 that omits "
        "assembly-path integrity"
    )
    assert not paragraphs_asserting_independence(pages), (
        "this control must be caught by the positive assertion alone; if the "
        "negative one also fires, the two are not testing different things"
    )


def test_the_unmodified_copy_passes_both_assertions(tmp_path: pathlib.Path) -> None:
    """The control's own baseline: the copy is clean before injection.

    Without this, a control that "refuses" proves nothing — the refusal could
    be coming from the page rather than from the injected paragraph.
    """
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    target = tmp_path / source.name
    shutil.copy(source, target)
    assert paragraphs_missing_the_correction([target]) == []
    assert paragraphs_asserting_independence([target]) == []


def test_a_negation_in_a_different_sentence_does_not_exonerate(
    tmp_path: pathlib.Path,
) -> None:
    """Sentence scoping, proven rather than asserted.

    A paragraph-scoped negation check would pass this, because "not" appears
    in the paragraph. It appears in the wrong sentence.
    """
    pages = _copied_tree(
        tmp_path,
        "Gate 2 is not optional. It is an independent witness that the "
        "operator set was right.",
    )
    assert paragraphs_asserting_independence(pages), (
        "a negation in a neighbouring sentence exonerated an independence "
        "claim — the scoping regressed from sentence to paragraph"
    )


def test_a_bare_enumeration_is_not_an_offender(tmp_path: pathlib.Path) -> None:
    """The trigger boundary, held from the other side.

    Naming lineage strict equality in a list of the three validation gates
    asserts nothing about independence. If this ever fails, the gate has
    started demanding padding in correct prose.
    """
    pages = _copied_tree(
        tmp_path,
        "The three validation gates are the empty-operator guard, lineage "
        "strict equality, and the TTL bound.",
    )
    assert paragraphs_missing_the_correction(pages) == []
