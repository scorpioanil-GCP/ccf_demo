#!/usr/bin/env python3
"""Wave 6 — load the document corpus into MongoDB `fibo_v2`.

MongoDB owns **passage-level lineage** and nothing else. Per
`covenant-cross-reference` §C it holds filed text, document structure, passage
spans with character offsets, embeddings, and classification tags. It does NOT
hold typed edges — those are Fluree's — and the partition validator checks that.

Collections:

    document        filed text + its sha256. The text IS the coordinate system
                    every offset indexes into; storing it is not redundancy.
    passage         {document_id, start_offset, end_offset, sha256} + body.
                    The anchor contract the whole tier rests on.
    memorandum      internal credit opinions — `synthetic — internal`, and the
                    only corpus `corpus_scope=filed-and-internal` unlocks.

Embeddings are deliberately absent: §E notes they are model-version-driven, so
they are added by a separate re-runnable pass with a recorded model version.
A passage with no vector is retrievable by anchor and simply not by similarity.

**The host is shared.** It also carries `rtdetect`, ~5.5M documents of live
telemetry. Everything here goes through `ccf.config.mongo_db()`, which refuses
any database outside `fibo_v2` and offers no enumeration helper.

    uv run loaders/load_mongo_wave6.py --dry-run
    uv run loaders/load_mongo_wave6.py

Idempotent: upserts on document_id / passage_id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import date, timedelta

from pymongo import ASCENDING, UpdateOne

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, mongo_db, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260817
BATCH = 500
MEMO_COUNT = 22

#: Classification drives `corpus_scope`. Filed material is public by
#: construction; internal memoranda are not, and an unentitled principal must
#: be refused rather than silently given a narrowed corpus.
CLASSIFICATIONS = ["public-filed", "internal-confidential", "internal-restricted"]

MEMO_TEMPLATES = [
    ("Annual review — {name}",
     "Recommend renewal of the {facility} at existing commitment. Leverage has "
     "trended within covenant since the last amendment; headroom at the most "
     "recent test date was adequate. Management guidance implies continued "
     "deleveraging. No change to internal grade recommended at this time."),
    ("Covenant headroom assessment — {name}",
     "Headroom on the consolidated leverage covenant has narrowed over the "
     "trailing four quarters. Sensitivity analysis indicates a breach under a "
     "downside EBITDA case absent the addback for non-recurring charges. "
     "Recommend quarterly rather than semi-annual monitoring."),
    ("Amendment recommendation — {name}",
     "Borrower has requested an amendment to the financial covenant package. "
     "Credit view is supportive subject to a pricing step-up and a tightened "
     "restricted-payments basket. Note the effective date precedes our booking "
     "date; exposure between those dates was drawn under the prior terms."),
    ("Watchlist rationale — {name}",
     "Adding to watchlist following a deterioration in fixed-charge coverage. "
     "No covenant breach has occurred. Rationale is forward-looking and rests "
     "on sector conditions rather than a specific reported metric."),
    ("Sector view — {name}",
     "Peer set comparison at identical reporting periods places the obligor in "
     "the third quartile on leverage and the second on coverage. Peer selection "
     "is on SIC and size; matching on filing date rather than period would "
     "materially change the ranking."),
]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


AGREEMENT_VERSIONS = SCREEN / "agreement_versions.json"


def passage_update(p: dict, existing_sha: str | None) -> dict:
    """The upsert body for one passage, preserving a still-valid vector.

    Embeddings are written by a separate pass (`loaders/embed_passages.py`),
    which is the right separation -- but this loader used to `$set` them back
    to None on every run, so a re-load silently discarded the entire
    similarity surface. Nothing caught it: the passage count is unchanged by
    a wipe, so a count-based idempotency check reports success while every
    vector is gone.

    The vector survives only while the text it was computed from survives.
    `sha256` is over the passage body, so an unchanged hash means an unchanged
    body and the vector still describes it. A CHANGED hash under the same id
    means the span now holds different text, and keeping the old vector there
    would not be staleness -- it would be a wrong answer served confidently to
    every similarity query. So that case clears it, and the next embedding
    pass recomputes.
    """
    body = {
        "passage_id": p["passage_id"],
        "document_id": p["document_id"],
        "start_offset": p["start_offset"],
        "end_offset": p["end_offset"],
        "length": p["length"],
        "sha256": p["sha256"],
        "alignment": p["alignment"],
        "structure_aligned": p["structure_aligned"],
        "heading": p["heading"],
        "text": p["text"],
        "provenance": "public",
    }
    if existing_sha == p["sha256"]:
        # Unchanged: write everything except the embedding fields, which are
        # simply left alone.
        return {"$set": body}
    if existing_sha is None:
        # New passage: initialise the fields so a consumer can distinguish
        # "not embedded yet" from "field absent".
        return {"$set": body,
                "$setOnInsert": {"embedding": None, "embedding_model": None}}
    # Same id, different text -- the old vector is not ours to keep.
    return {"$set": {**body, "embedding": None, "embedding_model": None}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rng = random.Random(SEED)
    today = date.today()
    assert_v2_schema(PG_SCHEMA_V2)

    payload = json.loads((SCREEN / "passages.json").read_text())
    documents = payload["documents"]
    passages = payload["passages"]

    # --- classification tags (synthetic — internal) -----------------------
    doc_class: dict[str, str] = {}
    for doc in documents:
        # Filed exhibits are public by construction. The tag still exists so
        # the Policy Operator has something uniform to reason over.
        doc_class[doc["document_id"]] = "public-filed"

    # --- internal memoranda ------------------------------------------------
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT f.facility_id, f.facility_type, e.legal_name, f.borrower_lei
            FROM "{PG_SCHEMA_V2}".facility f
            JOIN "{PG_SCHEMA_V2}".legal_entity e ON e.lei = f.borrower_lei
            ORDER BY f.facility_id
        """)
        facilities = cur.fetchall()

    memoranda = []
    for i in range(MEMO_COUNT):
        fid, ftype, name, lei = facilities[i % len(facilities)]
        title_t, body_t = MEMO_TEMPLATES[i % len(MEMO_TEMPLATES)]
        title = title_t.format(name=name[:40])
        body = body_t.format(name=name[:40], facility=ftype)
        classification = ("internal-restricted" if i % 5 == 2
                          else "internal-confidential")
        authored = today - timedelta(days=rng.randint(30, 700))
        memoranda.append({
            "memorandum_id": f"MEMO-{i:04d}",
            "title": title,
            "body": body,
            "text_sha256": sha256(body),
            "facility_id": fid,
            "borrower_lei": lei,
            "classification": classification,
            "residency": rng.choice(["US", "US", "UK", "EU"]),
            "authored_date": authored.isoformat(),
            "provenance": "synthetic — internal",
            "source": "generated: no public equivalent exists for internal "
                      "credit opinions",
            "retrieved_at": today.isoformat(),
        })

    print(f"Wave 6 — MongoDB load into fibo_v2\n")
    print(f"  documents    {len(documents):>7,}")
    print(f"  passages     {len(passages):>7,}")
    print(f"  memoranda    {len(memoranda):>7,}   (§F asks ~20)")
    aligned = sum(1 for p in passages if p["structure_aligned"])
    print(f"  structure-aligned passages {aligned:>7,}   (§F asks ~2,500)")
    print(f"  embeddings   {'none':>7}   separate pass, model-version-driven")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    # mongo_db() refuses anything but fibo_v2 and never enumerates databases.
    db = mongo_db()

    print(f"\n  writing documents...")
    # Agreement identity, derived by generators/link_agreement_versions_wave15.py
    # from the amendment text itself. Carried onto the document record because
    # `covenant-cross-reference` §F needs `as_of` to CHOOSE between two texts,
    # and a corpus holding both with nothing linking them offers nothing to
    # choose between. Absent artifact -> no fields, not an error: the corpus
    # loads fine without it, only the as_of selection is unavailable.
    versions: dict[str, dict] = {}
    if AGREEMENT_VERSIONS.exists():
        for r in json.loads(AGREEMENT_VERSIONS.read_text())["documents"]:
            versions[r["document_id"]] = {
                "agreement_id": r["agreement_id"],
                "agreement_date": r["agreement_date"],
                "agreement_role": r["role"],
                "governs_from": r["governs_from"],
            }
        print(f"  agreement identity for {len(versions)} documents")
    else:
        print("  no agreement_versions.json — as_of selection will be absent")

    db["document"].bulk_write([
        UpdateOne(
            {"_id": d["document_id"]},
            {"$set": {
                **versions.get(d["document_id"], {}),
                "document_id": d["document_id"],
                "cik": d["cik"], "lei": d["lei"], "sec_name": d["sec_name"],
                "accession": d["accession"], "document": d["document"],
                "form": d["form"], "filed_date": d["filed_date"],
                "url": d["url"],
                "text": d["text"],
                "text_length": d["text_length"],
                "text_sha256": d["text_sha256"],
                "passage_count": d["passage_count"],
                "classification": doc_class[d["document_id"]],
                "residency": "US",
                "provenance": d["provenance"],
                "source": d["source"],
                "retrieved_at": today.isoformat(),
            }},
            upsert=True,
        )
        for d in documents
    ], ordered=False)

    print(f"  writing passages in batches of {BATCH}...")
    for i in range(0, len(passages), BATCH):
        chunk = passages[i:i + BATCH]
        # What Mongo already holds for these ids, so an unchanged passage
        # keeps its vector. Fetched per batch rather than per passage: one
        # query of 500 ids instead of 500 round trips.
        existing = {
            row["_id"]: row.get("sha256")
            for row in db["passage"].find(
                {"_id": {"$in": [p["passage_id"] for p in chunk]}},
                {"sha256": 1},
            )
        }
        db["passage"].bulk_write([
            UpdateOne(
                {"_id": p["passage_id"]},
                passage_update(p, existing.get(p["passage_id"])),
                upsert=True,
            )
            for p in chunk
        ], ordered=False)
        if (i // BATCH) % 8 == 0:
            print(f"    {min(i + BATCH, len(passages)):>7,}/{len(passages):,}")

    print(f"  writing memoranda...")
    db["memorandum"].bulk_write([
        UpdateOne({"_id": m["memorandum_id"]}, {"$set": m}, upsert=True)
        for m in memoranda
    ], ordered=False)

    db["passage"].create_index([("document_id", ASCENDING),
                               ("start_offset", ASCENDING)])
    db["passage"].create_index([("structure_aligned", ASCENDING)])
    db["memorandum"].create_index([("classification", ASCENDING)])

    # --- corpus-scope entitlement rules -> Postgres (§C says Postgres) ----
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".corpus_entitlement (
                principal        TEXT NOT NULL,
                corpus_scope     TEXT NOT NULL,
                permitted_class  TEXT NOT NULL,
                provenance       TEXT NOT NULL,
                PRIMARY KEY (principal, permitted_class)
            )""")
        cur.execute(f"""
            COMMENT ON TABLE "{PG_SCHEMA_V2}".corpus_entitlement IS
            'corpus_scope is a POLICY parameter, not a convenience filter. '
            'Widening it changes which documents may be retrieved at all, and '
            'a principal without the entitlement is REFUSED rather than '
            'silently narrowed.'""")
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".corpus_entitlement '
            "(principal, corpus_scope, permitted_class, provenance) "
            "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [
                ("credit-officer", "filed", "public-filed", "synthetic — internal"),
                ("credit-officer", "filed-and-internal", "internal-confidential",
                 "synthetic — internal"),
                ("relationship-manager", "filed", "public-filed",
                 "synthetic — internal"),
                ("control-room", "filed-and-internal", "public-filed",
                 "synthetic — internal"),
                ("control-room", "filed-and-internal", "internal-confidential",
                 "synthetic — internal"),
                ("control-room", "filed-and-internal", "internal-restricted",
                 "synthetic — internal"),
            ],
        )
        conn.commit()

    n_doc = db["document"].count_documents({})
    n_pass = db["passage"].count_documents({})
    n_memo = db["memorandum"].count_documents({})
    print(f"\n  loaded: {n_doc} documents, {n_pass:,} passages, {n_memo} memoranda")
    return 0


if __name__ == "__main__":
    sys.exit(main())
