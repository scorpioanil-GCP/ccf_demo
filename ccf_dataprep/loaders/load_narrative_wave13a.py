#!/usr/bin/env python3
"""Wave 13a stage 3b — narrative sections and their passages into MongoDB.

    uv run loaders/load_narrative_wave13a.py --dry-run
    uv run loaders/load_narrative_wave13a.py

Segments the 10-K Item 1A/7, 10-Q MD&A and 8-K EX-99 sections that
`generators/fetch_narrative_docs.py` extracted, and upserts them alongside
Wave 6's EX-10 corpus. Same collections, same field shapes, same
structure-aligned segmentation function — imported from
`generators/segment_passages.py`, never reimplemented, because a second
segmenter would produce offsets that disagree with the first for the same
text and nothing would notice.

**Offsets are document-local and stay that way.** A section is a *slice* of its
filing, and `segment()` numbers passages from the start of the text it is
given. So a passage offset here is relative to the SECTION, and the section's
own offset within the filing rides on the document record as
`source_offset`. Keeping the two separate is what lets a citation resolve
without re-searching text: `passage.start_offset` indexes into
`document.text`, which is the section, exactly as it does for Wave 6's EX-10s.
Adding `source_offset` into passage offsets would make them index into a
filing this collection does not store.

Idempotent: upsert by `_id`, no delete, no drop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date

from pymongo import ASCENDING, UpdateOne

from ccf.config import REPO_ROOT, mongo_db
from generators.fetch_narrative_docs import ARTIFACT
from generators.segment_passages import segment

BATCH = 500

#: A memo cites filed text, and filed text is public. Wave 6 varied
#: `classification` across its corpus because credit agreements can carry
#: restricted terms; these are 10-K/10-Q/8-K sections, which are published to
#: the world by definition. Marking any of them restricted would be a policy
#: claim contradicted by the document's own existence.
CLASSIFICATION = "public-filed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    art = json.loads(ARTIFACT.read_text())
    sections = art["documents"]
    today = date.today().isoformat()

    documents, passages = [], []
    for sec in sections:
        text = sec["text"]
        ps = segment(text, sec["document_id"], narrative=True)
        documents.append({
            "document_id": sec["document_id"],
            "cik": sec["cik"], "lei": sec["lei"], "sec_name": sec["sec_name"],
            "accession": sec["accession"], "document": sec["document"],
            "form": sec["form"], "section": sec["section"],
            "filed_date": sec["filed_date"],
            # Where this section begins inside the filing it was cut from.
            # Passage offsets are section-local; see the module docstring.
            "source_offset": sec["source_offset"],
            "text": text,
            "text_length": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "passage_count": len(ps),
            "classification": CLASSIFICATION,
            "residency": "US",
            "provenance": sec["provenance"], "source": sec["source"],
            "retrieved_at": today,
        })
        passages.extend(ps)

    by_form: dict[str, int] = {}
    for d in documents:
        k = f"{d['form']} {d['section']}"
        by_form[k] = by_form.get(k, 0) + 1

    print("Wave 13a — narrative sections into MongoDB\n")
    for k, v in sorted(by_form.items()):
        print(f"  {k:<24}{v:>4} sections")
    print(f"\n  {len(documents)} documents, {len(passages):,} passages")
    aligned = sum(1 for p in passages if p["structure_aligned"])
    print(f"  {aligned:,} structure-aligned ({aligned / len(passages):.0%})")
    print(f"  median passage {sorted(p['length'] for p in passages)[len(passages)//2]:,} chars")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    db = mongo_db()
    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in documents], ordered=False)
    for i in range(0, len(passages), BATCH):
        db["passage"].bulk_write([
            UpdateOne({"_id": p["passage_id"]},
                      {"$set": {**p, "embedding": None,
                                "embedding_model": None,
                                "provenance": "public"}},
                      upsert=True)
            for p in passages[i:i + BATCH]], ordered=False)
    db["passage"].create_index([("document_id", ASCENDING),
                                ("start_offset", ASCENDING)])

    print(f"\n  document  {db['document'].estimated_document_count():>7,}")
    print(f"  passage   {db['passage'].estimated_document_count():>7,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
