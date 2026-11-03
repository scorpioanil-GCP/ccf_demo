#!/usr/bin/env python3
"""Re-running the Wave 6 corpus load must not discard the retrieval surface.

`load_mongo_wave6.py` documents itself as "Idempotent: upserts on
document_id / passage_id", and for the passage record it was. But the `$set`
payload carried `embedding: None` and `embedding_model: None`, so every
re-run overwrote every vector with null. Observed 2026-08-24: a re-load after
re-segmentation left 17,387 of 23,100 passages with a null embedding, all of
them previously embedded.

Nothing counted this. The passage count is identical before and after, so a
count-based idempotency check passes while the whole similarity surface is
gone -- the vectors are a FIELD being reset, and a cardinality cannot see a
field.

The rule this pins down has two halves, and a fix that gets only the first
half is worse than the defect:

  * an UNCHANGED passage keeps its vector across a re-load, and
  * a passage whose TEXT changed under the same id must LOSE it, because a
    vector computed from different text is not a stale vector, it is a wrong
    one, and it answers similarity queries confidently.

    uv run --with pytest pytest validators/test_mongo_embedding_preservation.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "load_mongo_wave6", REPO / "loaders" / "load_mongo_wave6.py")
loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loader)

PASSAGE = {
    "passage_id": "acc:doc.htm#p00007",
    "document_id": "acc:doc.htm",
    "start_offset": 100, "end_offset": 1600, "length": 1500,
    "sha256": "aaaa", "alignment": "structure", "structure_aligned": True,
    "heading": "Section 5.1", "text": "The Borrower shall maintain...",
}


def _fields(update: dict) -> tuple[dict, dict]:
    return update.get("$set", {}), update.get("$setOnInsert", {})


def test_new_passage_starts_with_a_null_embedding():
    """A passage Mongo has never seen is initialised, not left absent."""
    setd, oninsert = _fields(loader.passage_update(PASSAGE, existing_sha=None))
    both = {**setd, **oninsert}
    assert both["embedding"] is None
    assert both["embedding_model"] is None


def test_unchanged_passage_keeps_its_vector():
    """Same id, same sha256 -- the re-load must not touch the vector."""
    setd, _ = _fields(loader.passage_update(PASSAGE, existing_sha="aaaa"))
    assert "embedding" not in setd, (
        "re-load overwrites the embedding of an unchanged passage")
    assert "embedding_model" not in setd


def test_changed_passage_loses_its_vector():
    """Same id, DIFFERENT sha256 -- the old vector describes other text.

    Without this the fix trades a wiped surface for a lying one.
    """
    setd, _ = _fields(loader.passage_update(PASSAGE, existing_sha="bbbb"))
    assert setd.get("embedding", "missing") is None, (
        "a passage whose text changed kept a vector computed from the old text")
    assert setd.get("embedding_model", "missing") is None


def test_the_rest_of_the_record_is_always_written():
    """Preserving the vector must not stop offsets and text from updating."""
    for sha in (None, "aaaa", "bbbb"):
        setd, oninsert = _fields(loader.passage_update(PASSAGE, existing_sha=sha))
        both = {**setd, **oninsert}
        for k in ("passage_id", "document_id", "start_offset", "end_offset",
                  "length", "sha256", "alignment", "structure_aligned",
                  "heading", "text", "provenance"):
            assert k in both, f"{k} not written when existing_sha={sha!r}"
        assert both["sha256"] == "aaaa"
        assert both["provenance"] == "public"
