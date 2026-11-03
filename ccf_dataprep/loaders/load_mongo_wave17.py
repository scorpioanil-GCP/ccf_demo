#!/usr/bin/env python3
"""Wave 17 Task 3 (+ Task 15) — FinCEN advisory text/passages and SAR
narratives into MongoDB `fibo_v2`.

Reads `sources/screening/wave17_advisory_passages.json`
(`generators/extract_advisory_passages.py`) and upserts into the same
`document` / `passage` collections every other wave's corpus lives in.

MongoDB owns passage-level lineage; per `aml-typology-match` §C, typology
definitions and narrative patterns (FinCEN advisories) are `public`, and
passage spans derived at ingestion are `derived`. Nothing here belongs in
any other store -- single-writer discipline.

**`doc_type: "fincen_advisory"` is set on these 4 rows and ONLY these 4.**
178 pre-existing `document` rows carry no `doc_type` at all (a gap recorded
in `docs/known-issues.md` #21, first surfaced by Wave 16 Task 13's merger
corpus loader). This loader does not touch those rows and does not widen
the gap.

**Field names follow the estate convention** -- `document_id`, `passage_id`,
`start_offset`, `end_offset` -- matching all 37,305 pre-existing passages
and `validators/partition.py`'s orphan-anchor check. This loader's first cut
also wrote `doc_id` / `start` / `end` as duplicate aliases (controller
ruling: two fields holding the same value are two things that can drift),
and separately EXCLUDED `passage_id` from every passage's `$set` body
(kept only as `_id`), which broke `db.passage.find_one({"passage_id": ...})`
lookups -- exactly how Task 4 resolves a citation. Both are fixed here:
every field in the artifact record is written with `$set`, including
`document_id` / `passage_id` themselves, and every upsert also `$unset`s the
retired alias keys so a stale `doc_id`/`start`/`end` left by an earlier run
of this loader is removed rather than merely un-set-going-forward.

Idempotent: upsert by `_id` (== `document_id` / `passage_id`, both
content-derived -- see the generator's docstring), no delete.

## Task 15 addition — SAR narratives

Reads `sources/screening/wave17_sar_records.json`
(`generators/generate_sar_records.py`) and upserts a digest-selected
SUBSET of the engineered cases into the SAME `document` collection, with
`doc_type: "sar_narrative"` set on these rows and ONLY these rows --
following the Task 3 precedent above exactly (`doc_type: "fincen_advisory"`
is likewise scoped to its own 4 rows). No `passage` rows are written for
SAR narratives: a SAR is loaded whole, with no span-level anchoring the way
an advisory's typology citations need. The confidentiality classification
itself does NOT live here -- it lives in SQLite's `sar_classification`
table (`loaders/load_sqlite_wave17.py`), the departmental store this
product exists to demonstrate a reach into. Mongo carries only the
narrative text and the identifiers needed to join back to it.

Idempotent AND reconciled: upsert by `_id` (== `sar_id`, content-derived --
see the generator's docstring), then `delete_many` any `doc_type:
"sar_narrative"` document whose `_id` is no longer in the current artifact
-- scoped strictly to that `doc_type`, so it can never remove a
`fincen_advisory` row or touch the pre-existing 178-row `doc_type` gap.
Coordinator ruling (fix round 2): SAR coverage is now a deliberate PROPER
SUBSET of the 24 cases (see the generator's own docstring for why), so a
case that used to file under an earlier, wider selection must not leave a
phantom `sar_narrative` document behind.

    uv run loaders/load_mongo_wave17.py --dry-run
    uv run loaders/load_mongo_wave17.py
"""
from __future__ import annotations

import argparse
import json
import sys

from pymongo import ASCENDING, UpdateOne

from ccf.config import REPO_ROOT, mongo_db

ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave17_advisory_passages.json"
SAR_ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave17_sar_records.json"

#: Retired duplicate-offset aliases from this loader's first cut. Unset on
#: every upsert so a row written before the fix does not keep them forever
#: -- `$set` alone cannot remove a field absent from the new document.
RETIRED_DOC_FIELDS = {"doc_id": ""}
RETIRED_PASSAGE_FIELDS = {"doc_id": "", "start": "", "end": ""}

#: Fields a `sar_narrative` document used to carry and must no longer. An
#: upsert is `$set`-only, so a field REMOVED from the generator survives on
#: every already-loaded document forever unless it is explicitly unset --
#: the estate's "idempotency proofs by count are blind" defect, which a row
#: count cannot see. `case_exposure_usd` is whole-branch review CT-8.
RETIRED_SAR_FIELDS = {"case_exposure_usd": ""}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not ARTIFACT.exists():
        print(f"missing {ARTIFACT} -- run "
              f"generators/extract_advisory_passages.py first")
        return 1
    if not SAR_ARTIFACT.exists():
        print(f"missing {SAR_ARTIFACT} -- run "
              f"generators/generate_sar_records.py first")
        return 1

    art = json.loads(ARTIFACT.read_text())
    documents = art["documents"]
    passages = art["passages"]

    sar_art = json.loads(SAR_ARTIFACT.read_text())
    sars = sar_art["sars"]
    # SAR narratives are loaded whole into `document` -- no `passage` rows,
    # and no fields from `sar_classification` (that table is SQLite-only;
    # see load_sqlite_wave17.py and the single-writer test it satisfies).
    sar_documents = [
        {
            "document_id": r["sar_id"],
            "doc_type": "sar_narrative",
            "sar_id": r["sar_id"],
            "alert_id": r["alert_id"],
            "case_id": r["case_id"],
            "subject_party": r["subject_party"],
            "typology_id": r["typology_id"],
            "filed_at": r["filed_at"],
            "text": r["text"],
            "provenance": r["provenance"],
            # No `case_exposure_usd` -- whole-branch review CT-8. It was a
            # derived aggregate of Postgres-owned `aml_transaction.amount_usd`
            # sitting in a Mongo document, with no consumer, surviving from
            # the fix-round-2 filing design that was rejected. Its warning
            # label existed only because the field misled.
            "filing_rationale": r["filing_rationale"],
        }
        for r in sars
    ]

    print("Wave 17 Task 3 — MongoDB load\n")
    for d in documents:
        print(f"  {d['advisory_number']:<16} {d['typology']:<22} "
              f"{d['passage_count']:>3} passages  doc_type={d['doc_type']}")
    print(f"\n  {len(documents)} documents, {len(passages)} passages")
    print(f"\nWave 17 Task 15 — MongoDB load\n")
    print(f"  {len(sar_documents)} sar_narrative documents")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    db = mongo_db()

    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]},
                  {"$set": d, "$unset": RETIRED_DOC_FIELDS},
                  upsert=True)
        for d in documents
    ], ordered=False)

    db["passage"].bulk_write([
        UpdateOne({"_id": p["passage_id"]},
                  {"$set": p, "$unset": RETIRED_PASSAGE_FIELDS},
                  upsert=True)
        for p in passages
    ], ordered=False)

    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]},
                  {"$set": d, "$unset": RETIRED_SAR_FIELDS},
                  upsert=True)
        for d in sar_documents
    ], ordered=False)

    # Reconcile, don't just append -- this loader is the only writer of
    # doc_type: "sar_narrative" documents, and the artifact is authoritative
    # for the FULL set that should exist. Coordinator ruling (fix rounds
    # 2-3): SAR coverage shrank from 1:1 with the cases to a digest-selected
    # subset, so a document for a case that no longer files must be REMOVED, not left
    # behind as a phantom `find({"doc_type": "sar_narrative"})` hit. Scoped
    # to doc_type: "sar_narrative" specifically, so this can never touch the
    # 4 fincen_advisory rows or the pre-existing 178-row doc_type gap.
    sar_ids = [d["document_id"] for d in sar_documents]
    delete_result = db["document"].delete_many({
        "doc_type": "sar_narrative",
        "_id": {"$nin": sar_ids},
    })

    db["passage"].create_index([("document_id", ASCENDING),
                                ("start_offset", ASCENDING)])
    db["document"].create_index([("doc_type", ASCENDING)])

    doc_ids = [d["document_id"] for d in documents]
    passage_ids = [p["passage_id"] for p in passages]
    n_doc = db["document"].count_documents({"_id": {"$in": doc_ids}})
    n_pass = db["passage"].count_documents({"_id": {"$in": passage_ids}})
    n_sar = db["document"].count_documents(
        {"_id": {"$in": sar_ids}, "doc_type": "sar_narrative"})
    n_gap = db["document"].count_documents({"doc_type": None})
    stale = db["passage"].count_documents({
        "_id": {"$in": passage_ids},
        "$or": [{"doc_id": {"$exists": True}},
                {"start": {"$exists": True}},
                {"end": {"$exists": True}}],
    })
    print(f"\n  resolved back: {n_doc}/{len(documents)} documents, "
          f"{n_pass}/{len(passages)} passages, "
          f"{n_sar}/{len(sar_documents)} sar_narrative documents")
    print(f"  stale sar_narrative documents reconciled away: "
          f"{delete_result.deleted_count}")
    print(f"  pre-existing doc_type gap (should stay 178): {n_gap}")
    print(f"  passages still carrying a retired alias key: {stale} (want 0)")

    # Named value, not a cardinality: a count of documents cannot see a
    # field that should have been removed still sitting on every one of
    # them. Checked against ALL sar_narrative documents, not just the ids
    # written this run.
    stale_sar = db["document"].count_documents({
        "doc_type": "sar_narrative",
        "$or": [{k: {"$exists": True}} for k in RETIRED_SAR_FIELDS],
    })
    print(f"  sar_narrative documents still carrying a retired field "
          f"({', '.join(sorted(RETIRED_SAR_FIELDS))}): {stale_sar} (want 0)")
    if stale_sar:
        raise RuntimeError(
            f"{stale_sar} sar_narrative document(s) still carry a retired "
            f"field {sorted(RETIRED_SAR_FIELDS)} after the unset -- the "
            "upsert did not reconcile them away")
    return 0


if __name__ == "__main__":
    sys.exit(main())
