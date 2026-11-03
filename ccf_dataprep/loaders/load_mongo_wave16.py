#!/usr/bin/env python3
"""Wave 16 Task 13 — merger proxy / S-4 corpus into MongoDB `fibo_v2`.

Reads `sources/screening/wave16_merger_docs.json` (15 documents: 5 DEFM14A,
4 PREM14A, 3 S-4, 3 S-4/A across 8 entities) and loads it into the same
`document` / `passage` collections Wave 6 and Wave 13a already own, using the
same structure-aligned segmenter (`generators/segment_passages.py`) so a
passage offset here means exactly what it means everywhere else in the
corpus -- an index into THIS document's stored `text`, never re-searched.

**`doc_type` is set here and ONLY here.** All 178 pre-existing `document`
rows carry no `doc_type` at all (a gap from earlier waves -- see
`docs/known-issues.md`). Back-filling those 178 is exactly the kind of
positional/silent rewrite CLAUDE.md and this estate's own history warn
against: this loader did not write those rows and does not know, for many of
them, what the honest value would even be. It sets `doc_type` on the 15 rows
it DOES write, and leaves the pre-existing gap named rather than patched.

`doc_type` mirrors the `signal_type` vocabulary
`generators/generate_opportunity_signals.py` already uses for these same
filings (`merger_proxy` for DEFM14A/PREM14A, `registration_s4` for S-4/S-4A),
so a consumer joining Mongo documents to Fluree `OpportunitySignal` nodes on
`source_ref == accession` sees the same category name on both sides.

Narrative segmentation (`segment(..., narrative=True)`), not the EX-10
credit-agreement mode: these are proxies and registration statements, not
credit agreements, and Wave 13a already established that the EX-10 STRUCTURE
regex alone catches almost nothing in narrative SEC prose.

    uv run loaders/load_mongo_wave16.py --dry-run
    uv run loaders/load_mongo_wave16.py

Idempotent: upsert by `_id` (document_id / passage_id), no delete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date

from pymongo import ASCENDING, UpdateOne

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, mongo_db, pg_connect
from generators.extract_facilities import TextExtractor
from generators.segment_passages import segment

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave16_merger_docs.json"
BATCH = 500

DOC_TYPE = {
    "DEFM14A": "merger_proxy",
    "PREM14A": "merger_proxy",
    "S-4": "registration_s4",
    "S-4/A": "registration_s4",
}

CLASSIFICATION = "public-filed"  # filed with the SEC; public by construction


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    art = json.loads(ARTIFACT.read_text())
    docs_in = art["documents"]

    with pg_connect() as cn, cn.cursor() as cu:
        cu.execute(f'SELECT lei, legal_name FROM "{S}".legal_entity')
        names = dict(cu.fetchall())

    today = date.today().isoformat()
    documents, passages = [], []
    for d in docs_in:
        path = REPO_ROOT / "sources" / d["path"]
        if not path.exists():
            print(f"  MISSING on disk, skipped: {d['path']}")
            continue
        parser = TextExtractor()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        text = parser.text()

        nodash = d["accession"].replace("-", "")
        url = (f"https://www.sec.gov/Archives/edgar/data/{d['cik']}/{nodash}/"
               f"{d['primary_document']}")
        document_id = f"{d['accession']}:{d['primary_document']}"
        ps = segment(text, document_id, narrative=True)
        if not ps:
            print(f"  no passages segmented, skipped: {document_id}")
            continue

        documents.append({
            "document_id": document_id,
            "cik": d["cik"], "lei": d["lei"],
            "sec_name": names.get(d["lei"], d["lei"]),
            "accession": d["accession"], "document": d["primary_document"],
            "form": d["form"], "doc_type": DOC_TYPE[d["form"]],
            "filed_date": d["filing_date"],
            "url": url,
            "text": text,
            "text_length": len(text),
            "text_sha256": sha256(text),
            "passage_count": len(ps),
            "classification": CLASSIFICATION,
            "residency": "US",
            "provenance": d["provenance"],
            "source": "SEC EDGAR merger proxy / S-4 registration",
            "retrieved_at": today,
        })
        passages.extend(ps)

    by_type: dict[str, int] = {}
    for d in documents:
        by_type[d["doc_type"]] = by_type.get(d["doc_type"], 0) + 1

    print("Wave 16 Task 13 — merger corpus into MongoDB\n")
    for k, v in sorted(by_type.items()):
        print(f"  {k:<18}{v:>4} documents")
    print(f"\n  {len(documents)} documents, {len(passages):,} passages")
    aligned = sum(1 for p in passages if p["structure_aligned"])
    if passages:
        print(f"  {aligned:,} structure-aligned "
              f"({aligned / len(passages):.0%})")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    db = mongo_db()
    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in documents
    ], ordered=False)

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

    n_doc = db["document"].count_documents(
        {"_id": {"$in": [d["document_id"] for d in documents]}})
    n_pass = db["passage"].count_documents(
        {"_id": {"$in": [p["passage_id"] for p in passages]}})
    print(f"\n  written this run: {n_doc} of {len(documents)} documents, "
          f"{n_pass:,} of {len(passages):,} passages resolve back")
    print(f"  collection totals: document {db['document'].estimated_document_count():,}, "
          f"passage {db['passage'].estimated_document_count():,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
