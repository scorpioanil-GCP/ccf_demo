#!/usr/bin/env python3
"""Wave 13b Task 7 — load KYC documents and passages into MongoDB.

Reads `sources/screening/wave13b_kyc_documents.json`.

    kyc_document   32 docs   synthetic — internal   (§C: no public equivalent)
    passage       +84 rows   derived                (spans and offsets)

## A separate collection, and the check that keeps it honest

KYC files are not filings. They carry no accession, no CIK and no filer, and
mixing them into `document` — which holds 136 real EDGAR filings — would make
every query over that collection need a provenance filter to stay correct.

But `validators/partition.py` asserts *"passages anchor to a document"* by
checking `passage.document_id` against `document.distinct("document_id")`, so a
passage pointing at a `kyc_document` would read as orphaned. The check is
right and the fix is to widen what counts as a document, not to weaken the
anchor claim — extended in the same commit.

## Offsets are re-verified against the stored text

Every passage is re-sliced out of the document text at its own offsets and the
sha256 compared, on load, from the artifact. An offset that drifted between
generation and load would otherwise sit in the store looking exactly like a
correct one — the Wave 6 anchoring discipline.

## No embeddings here

`loaders/embed_passages.py` is a separate step and stays that way. Writing an
empty embedding field would be worse than writing none: a consumer cannot tell
"not embedded yet" from "embedded to zeros".

    uv run loaders/load_kyc_documents_wave13b.py --dry-run
    uv run loaders/load_kyc_documents_wave13b.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter

from ccf.config import MONGO_DB_V2, REPO_ROOT, mongo_db
from pymongo import UpdateOne

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_kyc_documents.json"
DOC_COLLECTION = "kyc_document"
PASSAGE_COLLECTION = "passage"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_offsets(doc: dict) -> list[str]:
    """Re-slice every passage out of its document. Returns failures."""
    by_doc = {d["document_id"]: d["text"] for d in doc["documents"]}
    bad = []
    for p in doc["passages"]:
        text = by_doc.get(p["document_id"])
        if text is None:
            bad.append(f"{p['passage_id']}: no such document")
            continue
        if sha(text[p["start_offset"]:p["end_offset"]]) != p["sha256"]:
            bad.append(f"{p['passage_id']}: offsets do not re-slice to its hash")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description="Load KYC documents into MongoDB")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())
    documents = doc["documents"]
    passages = doc["passages"]

    kinds = Counter(d["kind"] for d in documents)
    residency = Counter(d["residency"] for d in documents)

    print(f"Wave 13b Task 7 — KYC documents into MongoDB {MONGO_DB_V2}\n")
    print(f"  artifact           {ARTIFACT.relative_to(REPO_ROOT)}")
    print(f"  {DOC_COLLECTION:<18} {len(documents):>4}   {dict(kinds)}")
    print(f"  passage (+)        {len(passages):>4}")
    print(f"  residency          {dict(residency)}")
    print(f"  declarations       "
          f"{sum(1 for d in documents if d['kind'] == 'ownership_declaration')}")

    bad = verify_offsets(doc)
    print(f"  offset check       {len(passages) - len(bad)}/{len(passages)} "
          f"passages re-slice to their own hash")
    if bad:
        for b in bad[:5]:
            print(f"      FAIL  {b}")
        return 1

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0

    # `mongo_db()` refuses any database v2 does not own; the shared host also
    # runs rtdetect, and there is deliberately no way to enumerate databases.
    db = mongo_db()

    db[DOC_COLLECTION].bulk_write([
        UpdateOne({"document_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in documents
    ])
    db[PASSAGE_COLLECTION].bulk_write([
        UpdateOne({"passage_id": p["passage_id"]}, {"$set": p}, upsert=True)
        for p in passages
    ])
    db[DOC_COLLECTION].create_index("document_id", unique=True)
    db[DOC_COLLECTION].create_index("entity_id")

    # --- remove what the artifact no longer contains ----------------------
    #
    # Upserting alone is not idempotent for a variable-length child
    # collection. A regenerated artifact can turn a four-section ownership
    # declaration into a two-section certificate, and the old P03/P04 passages
    # then SURVIVE — anchored to a document whose text no longer contains
    # them. Found by this loader's own re-slice check on the second run: 12
    # stale passages, every one of which would have looked live.
    #
    # Scoped exactly like the OFAC delisting: only passages this loader owns
    # (`KYC-` prefixed document ids) are eligible, so the 19,683 passages
    # belonging to Waves 6 and 13a are untouchable from here.
    keep = [p["passage_id"] for p in passages]
    stale = db[PASSAGE_COLLECTION].delete_many({
        "document_id": {"$regex": "^KYC-"},
        "passage_id": {"$nin": keep},
    })
    stale_docs = db[DOC_COLLECTION].delete_many({
        "document_id": {"$nin": [d["document_id"] for d in documents]},
    })
    if stale.deleted_count or stale_docs.deleted_count:
        print(f"  removed {stale.deleted_count} stale passage(s) and "
              f"{stale_docs.deleted_count} stale document(s) the artifact no "
              f"longer contains")

    n_docs = db[DOC_COLLECTION].count_documents({})
    n_passages = db[PASSAGE_COLLECTION].count_documents(
        {"document_id": {"$regex": "^KYC-"}})
    n_decl = db[DOC_COLLECTION].count_documents(
        {"kind": "ownership_declaration"})
    # Read back and re-verify from the STORE, not from the artifact: a loader
    # that dropped a field would otherwise pass on the artifact's own numbers.
    stored_bad = []
    for stored in db[DOC_COLLECTION].find({}, {"document_id": 1, "text": 1}):
        for p in db[PASSAGE_COLLECTION].find(
                {"document_id": stored["document_id"]},
                {"passage_id": 1, "start_offset": 1, "end_offset": 1,
                 "sha256": 1}):
            slice_ = stored["text"][p["start_offset"]:p["end_offset"]]
            if sha(slice_) != p["sha256"]:
                stored_bad.append(p["passage_id"])

    print(f"\n  loaded: {DOC_COLLECTION} {n_docs} ({n_decl} ownership "
          f"declarations) · KYC passages {n_passages}")
    print(f"  re-verified from the store: "
          f"{n_passages - len(stored_bad)}/{n_passages} passages anchor exactly")

    failures = []
    if n_docs != len(documents):
        failures.append(f"{n_docs} documents in the store, expected "
                        f"{len(documents)}")
    if n_passages != len(passages):
        failures.append(f"{n_passages} KYC passages, expected {len(passages)}")
    if stored_bad:
        failures.append(f"{len(stored_bad)} passage(s) do not anchor in the "
                        f"store: {stored_bad[:3]}")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  store matches the artifact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
