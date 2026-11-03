#!/usr/bin/env python3
"""The head region: text before a document's first structure marker.

`segment()` built its spans as `[p[0] for p in points] + [len(text)]`, which
starts at the FIRST break point. Everything from offset 0 to that point was
never covered by any span, so no passage anchor could reach it. Measured over
the Wave 15 EX-10 corpus: 880,471 characters unreachable, and one document
(Smith & Wesson `swbi-ex10_107.htm`, whose first marker sits at offset 42,968
of 43,198) produced zero passages and vanished from `passages.json` with no
message at all.

The recovered head spans are APPENDED to the span list rather than prepended.
Passage ids are positional -- `{document_id}#p{idx:05d}` -- so putting the head
first would renumber every later passage in the document, and 43 Fluree
`ex:evidencedBy` triples point at those ids in a ledger that cannot delete.
Appending recovers the text and leaves every existing id exactly where it was.

    uv run --with pytest pytest validators/test_segment_head.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "segment_passages", REPO / "generators" / "segment_passages.py")
seg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seg)


def _covered(passages: list[dict]) -> set[int]:
    """Every character offset some passage covers."""
    out: set[int] = set()
    for p in passages:
        out.update(range(p["start_offset"], p["end_offset"]))
    return out


def _doc(head_chars: int, body_sections: int = 4) -> str:
    """A document with `head_chars` of preamble before the first Section."""
    head = ("This Agreement is entered into among the parties named below. "
            * ((head_chars // 60) + 1))[:head_chars]
    body = "".join(
        f"\nSection {i}.1 Covenants. "
        + ("The Borrower shall maintain a leverage ratio not greater than "
           "3.00 to 1.00 tested quarterly. " * 12)
        for i in range(1, body_sections + 1)
    )
    # No head means the document must START at the marker, offset 0 -- the
    # leading newline the section joiner adds would otherwise put the first
    # break point at offset 1 and give the negative control a 1-char head.
    return (head + body) if head_chars else body.lstrip("\n")


# -- the defect ------------------------------------------------------------

def test_head_text_is_reachable():
    """Offset 0 must be covered when the first marker is deep in the text."""
    text = _doc(head_chars=8000)
    first = seg.break_points(text)[0][0]
    assert first > 5000, "fixture must actually have a deep first marker"

    covered = _covered(seg.segment(text, "d"))
    assert 0 in covered, "the first character of the document is unreachable"
    missing = [o for o in range(0, first, 500) if o not in covered]
    assert not missing, f"head offsets never covered: {missing[:5]}"


def test_document_with_only_a_late_marker_still_segments():
    """Smith & Wesson's shape: 99.5% head, two tiny spans after it.

    Before the fix this returned [] and the document silently disappeared.
    """
    text = _doc(head_chars=43000, body_sections=1)[:43200]
    passages = seg.segment(text, "swbi")
    assert passages, "document produced no passages and would be dropped"


# -- the constraint the fix must not break ---------------------------------

def test_existing_passage_ids_are_preserved():
    """Head recovery must not renumber the spans that already had ids.

    Reproduces the pre-fix numbering directly rather than trusting a stored
    fixture, so this fails if the head spans are ever moved to the front.
    """
    text = _doc(head_chars=8000)
    points = seg.break_points(text)
    bounds = [p[0] for p in points] + [len(text)]

    # The pre-fix span list, verbatim: first break point onward.
    legacy: list[tuple[int, int]] = []
    for i in range(len(points)):
        s, e = bounds[i], bounds[i + 1]
        if e - s > seg.MAX_CHARS:
            c = s
            while c < e:
                stop = min(c + seg.FALLBACK_WINDOW, e)
                legacy.append((c, stop))
                c = stop
        else:
            legacy.append((s, e))
    expected = {
        f"d#p{i:05d}": (s, e)
        for i, (s, e) in enumerate(legacy)
        if len(text[s:e].strip()) >= seg.MIN_CHARS
    }

    got = {p["passage_id"]: (p["start_offset"], p["end_offset"])
           for p in seg.segment(text, "d")}

    for pid, span in expected.items():
        assert pid in got, f"{pid} disappeared -- ids were renumbered"
        assert got[pid] == span, f"{pid} moved from {span} to {got[pid]}"


# -- negative control: the check must be able to answer "no" ---------------

def test_no_head_passages_when_the_document_starts_at_a_marker():
    """A document whose first break point IS offset 0 gains nothing.

    Without this, a fix that appended head spans unconditionally would pass
    every test above while inventing passages for documents that never had a
    head region.
    """
    text = _doc(head_chars=0)
    points = seg.break_points(text)
    assert points and points[0][0] == 0, "fixture must start at a marker"

    kinds = {p["alignment"] for p in seg.segment(text, "d")}
    assert "window-head" not in kinds, (
        f"head passages invented for a document with no head: {kinds}")


def test_head_passages_are_labelled_not_structure_aligned():
    """Recovered head text is a best-effort window, and must say so.

    `covenant-cross-reference` distinguishes a clean citation from a
    best-effort one by `structure_aligned`; head text has no structure by
    definition, so counting it as aligned would inflate that measure.
    """
    text = _doc(head_chars=8000)
    head = [p for p in seg.segment(text, "d") if p["alignment"] == "window-head"]
    assert head, "fixture produced no head passages"
    assert all(p["structure_aligned"] is False for p in head)
