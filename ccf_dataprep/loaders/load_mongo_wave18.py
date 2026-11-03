#!/usr/bin/env python3
"""Wave 18 Task 11 -- voting-threshold and assignment-provision passages into
MongoDB `fibo_v2`. Also Task 12 (added below `build()`'s main loop) -- the
interagency Shared National Credit annual report, one `document` row, no
passages. Extends this loader rather than adding a second Mongo loader, per
the Task 12 brief's explicit instruction; see `_snc_document()`.

Reads `sources/screening/wave18_amendment_assignment.json`
(`generators/extract_amendment_assignment_articles.py`) and upserts into the
SAME `document` / `passage` collections every other wave's corpus lives in --
Wave 6 first built them (`loaders/load_mongo_wave6.py`), Wave 16 and Wave 17
both reused them rather than starting a second passage schema.

## Reusing Wave 6/15/17's schema, not inventing a parallel one

`passage` field names follow the estate convention exactly: `document_id`,
`passage_id`, `start_offset`, `end_offset`, `length`, `sha256`, `alignment`,
`structure_aligned`, `heading`, `text`, `provenance` -- matching all 37,377
pre-existing passages and `validators/partition.py`'s orphan-anchor check
(`check_mongo`'s P3b). Wave 17's loader docstring records why this matters:
an earlier cut of THAT loader wrote `doc_id`/`start`/`end` as duplicate alias
fields, and the controller ruling was explicit -- "two fields holding the
same value are two things that can drift". The brief for this task illustrates
its resolvability test with `p["start"]`/`p["end"]`; those are NOT this
estate's spelling (they are the exact alias pair Wave 17 introduced and then
retired), so `validators/test_syndicate.py`'s test below is written against
`start_offset`/`end_offset` instead, and would fail identically -- and for
the same reason -- against a loader that wrote the wrong field.

`alignment="structure"` / `structure_aligned=True` are reused too, not a new
value. Every passage here begins at a real, verified section heading (see
the extractor module's own docstring for how TOC-row false positives are
excluded), which is exactly what `alignment="structure"` already means
elsewhere in this collection -- introducing a fourth-ish value that means
the same thing would be the "second schema" this task is warned against.

## `document_id` is the bare filing filename, not `accession:document`

Every OTHER document in this collection keys `document_id` as
`f"{accession}:{document}"` (Wave 6/16/17). This loader deliberately does
NOT follow that -- because Task 8/9's Fluree `ex:sourcePassage` literals
(`loaders/load_fluree_wave18.py`, `f"{doc}#offset={row['offset']}-{row['end']}"`)
already cite these SAME six filings by their bare local filename (the
`ccf.syndicate.TRANCHE_TO_FACILITIES` key, e.g.
`"1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm"`), and that string is
the join key CLAUDE.md rule 4 requires: a Mongo document keyed any other way
would make `ex:sourcePassage` unresolvable from this store. `_id` ==
`document_id` == that filename, matching the general pattern (`_id` equals
the join key) even though the join key's SHAPE is Wave-18-local.

## Provenance: `public` on both the document and the passage

Ruling T11-R1 (coordinator, 2026-08-26), overriding this loader's own first
cut, which set `passage.provenance = "derived"`. Measured before ruling:
across the whole `passage` collection, 37,295 rows are `public` and 94 are
`derived`; of those 94, 82 carry NO `passage_kind` and NO `source` at all
(a pre-existing anomaly recorded in `docs/known-issues.md`, not a
precedent) and the other 12 were this loader's own `derived` rows. So
`derived` was never an established convention for a passage here -- Wave
15's agreement passages, the direct analogue of this task's work, are
`public`.

Both §C rows for what this loader builds say `public` -- "Voting thresholds
and amendment mechanics ... public" and "Assignment and transfer provisions
... public". The separate "Passage spans on agreement text ... derived"
row describes span METADATA as a category, not the passage document that
carries filed text: the text genuinely is filed public text, from a named
EX-10 with a retrieval date, and the offsets are metadata ABOUT that public
text, not a second claim with a provenance of its own. A consumer filtering
`provenance == "public"` -- an entirely reasonable query, and the one
37,295 of 37,389 rows already answer -- would otherwise silently miss
exactly these 12 rows: the same failure mode this loader's field-naming
section above was written to avoid, now on a different field.

## Idempotency

Upsert on `_id`. `document._id` is the filename (content-derived: the same
six filenames every run, keyed by what they ARE, not by load order).
`passage._id` is `f"{document}#{passage_kind}"` -- deliberately NOT a hash
of `(document, start, end)` as the brief's Step 3 example suggests. A hash
of the offsets would ORPHAN the old row if a future extractor tweak shifts
an offset by one character: the new row would upsert under a new hash and
the old one would sit in the collection as a stale duplicate forever (an
instance of "positional identity" masquerading as content identity -- the
offsets are an OUTPUT of the extraction, not a stable identifier of WHICH
passage this is). `document#passage_kind` is unique (one of each kind per
document, verified below) and stable across re-runs even when the exact
span moves.

    uv run loaders/load_mongo_wave18.py --dry-run
    uv run loaders/load_mongo_wave18.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from pymongo import ASCENDING, UpdateOne

from ccf.config import REPO_ROOT, mongo_db

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave18_amendment_assignment.json"

#: Task 12 -- the interagency Shared National Credit annual report. Optional:
#: §C names this source specifically (no substitute), but per the Task 12
#: brief's PREFLIGHT RULING P4, its absence must never block the rest of
#: this loader -- only its own test skips. `generators/fetch_snc_report.py`
#: writes this artifact; if it hasn't been run, the SNC document row is
#: simply omitted from this run's `documents` list.
SNC_EXTRACT = REPO_ROOT / "sources" / "snc" / "extract.json"


def _snc_document() -> dict | None:
    """One `document` row for the SNC report, or None if not fetched.

    `source` names the publisher (Ruling T12-R1); the retrievable address
    lives in `url`, matching every other row in this collection.
    """
    if not SNC_EXTRACT.exists():
        return None
    snc = json.loads(SNC_EXTRACT.read_text())
    return {
        "document_id": snc["document_id"],
        "text": snc["text"],
        "text_length": snc["text_length"],
        "text_sha256": snc["text_sha256"],
        "page_count": snc["page_count"],
        "doc_type": "snc_annual_report",
        "classification": "public",
        "residency": "US",
        "provenance": "public",
        "source": snc["source"],
        "url": snc["url"],
        "retrieved_at": snc["retrieved_at"],
    }


def build() -> tuple[list[dict], list[dict]]:
    if not ARTIFACT.exists():
        raise SystemExit(
            f"{ARTIFACT} missing -- run "
            f"generators/extract_amendment_assignment_articles.py first")
    art = json.loads(ARTIFACT.read_text())
    today = date.today().isoformat()

    documents: list[dict] = []
    passages: list[dict] = []
    for d in art["documents"]:
        documents.append({
            "document_id": d["document"],
            "cik": d["cik"], "lei": d["lei"], "sec_name": d["sec_name"],
            "accession": d["accession"], "document": d["document"],
            "form": d["form"], "filed_date": d["filed_date"], "url": d["url"],
            "text": d["text"],
            "text_length": d["text_length"],
            "text_sha256": d["text_sha256"],
            "passage_count": len(d["passages"]),
            "doc_type": "credit_agreement_wave18",
            "classification": "public-filed",
            "residency": "US",
            "provenance": "public",
            "source": "SEC EDGAR EX-10 exhibit",
            "retrieved_at": today,
        })
        for p in d["passages"]:
            passage_id = f"{p['document']}#{p['passage_kind']}"
            passages.append({
                "passage_id": passage_id,
                "document_id": p["document"],
                "passage_kind": p["passage_kind"],
                "start_offset": p["start_offset"],
                "end_offset": p["end_offset"],
                "length": p["length"],
                "sha256": p["sha256"],
                "alignment": "structure",
                "structure_aligned": True,
                "heading": p["heading"],
                "text": p["text"],
                "provenance": "public",  # ruling T11-R1
            })

    snc_doc = _snc_document()
    if snc_doc is not None:
        documents.append(snc_doc)

    return documents, passages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    documents, passages = build()

    by_kind: dict[str, int] = {}
    for p in passages:
        by_kind[p["passage_kind"]] = by_kind.get(p["passage_kind"], 0) + 1

    n_credit_agreements = sum(
        1 for d in documents if d["doc_type"] == "credit_agreement_wave18")
    n_snc = sum(1 for d in documents if d["doc_type"] == "snc_annual_report")

    print("Wave 18 Tasks 11 & 12 -- MongoDB voting-threshold / assignment "
          "passages, SNC report\n")
    print(f"  documents  {n_credit_agreements:>3}   doc_type=credit_agreement_wave18")
    for kind, n in sorted(by_kind.items()):
        print(f"  passages   {n:>3}   passage_kind={kind}")
    if n_snc:
        print(f"  documents  {n_snc:>3}   doc_type=snc_annual_report")
    else:
        print("  documents    0   doc_type=snc_annual_report -- "
              f"{SNC_EXTRACT.relative_to(REPO_ROOT)} not found, run "
              "generators/fetch_snc_report.py")

    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    db = mongo_db()

    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in documents
    ], ordered=False)

    db["passage"].bulk_write([
        UpdateOne({"_id": p["passage_id"]}, {"$set": p}, upsert=True)
        for p in passages
    ], ordered=False)

    db["passage"].create_index([("document_id", ASCENDING), ("passage_kind", ASCENDING)])

    doc_ids = [d["document_id"] for d in documents]
    passage_ids = [p["passage_id"] for p in passages]
    n_doc = db["document"].count_documents({"_id": {"$in": doc_ids}})
    n_pass = db["passage"].count_documents({"_id": {"$in": passage_ids}})
    print(f"\n  loaded: {n_doc}/{len(documents)} documents, "
          f"{n_pass}/{len(passages)} passages resolve back")
    return 0


if __name__ == "__main__":
    sys.exit(main())
