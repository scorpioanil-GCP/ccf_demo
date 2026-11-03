#!/usr/bin/env python3
"""Prospectus and servicer-report text into MongoDB, with passage spans.

    uv run loaders/load_abs_prospectus_wave14.py --dry-run
    uv run loaders/load_abs_prospectus_wave14.py

Reuses `generators.segment_passages.segment` rather than reimplementing
segmentation -- Wave 13a's rule, so passage semantics stay identical across
every corpus this project stores.

## Stale passages must be removed, not upserted over -- write-then-delete

`known-issues.md` §14.10 again: an upsert-only reload of a document whose
text shrank leaves passages anchored to offsets the text no longer has. The
loader deletes a document's stale passages, scoped to this wave's own
`document_id`s so the 19,765 passages belonging to earlier waves are never
touched.

The delete happens AFTER the new passages are written and the document is
upserted, not before. Delete-then-write leaves a window -- a crash between
the delete and the rewrite -- where a document exists with zero passages
behind it, and a document with no passages means its trigger anchors resolve
to nothing. Write-then-delete inverts the failure window into a transient
*superset* (stale rows alongside the new ones) instead of a *gap*: a
superset self-heals on the next successful run because the delete step
excludes every id just written; a gap does not self-heal and is exactly the
shape someone would copy into a loader where self-healing does not apply.
No Mongo transaction is used -- this is a standalone mongod, not a replica
set -- the ordering alone gives the guarantee.

## Embeddings survive a reload of unchanged text

Every passage upsert used to unconditionally `$set` `embedding: None,
embedding_model: None`, which meant every re-run discarded the entire
Step 4 embedding pass -- 1,882 vectors wiped by a loader with no reason to
touch them, since `loaders/embed_passages.py` exists precisely so
"re-running only embeds what is missing, so a partial failure costs only
the remainder." A delete-and-rewrite loader silently made every reload cost
the whole corpus instead.

Fixed by comparing each passage's freshly computed `sha256` against what is
already stored for that `_id`: unchanged text leaves `embedding` and
`embedding_model` out of the `$set` entirely (so the stored vector is
untouched), changed or new text explicitly nulls them. The comparison is
per-passage, not per-document -- a document's overall hash can differ while
most of its passages do not, and clearing every vector under a document
whose only change is a paragraph the trigger anchors don't even touch would
throw away work for no reason.

## `trigger_anchor` gets the same treatment -- this is the third appearance

The brief this loader was drafted from upserted `trigger_anchor` rows by id
with no prior delete. That is idempotent only for a fixed row set: if a
future extractor change drops a trigger, the stale anchor for it survives
forever and every query still reads it as live. Same defect family as
§14.10, now in its third appearance this wave (Task 5 guarded against it in
Postgres; here it is Mongo).

Fix: delete this run's `trigger_anchor` rows before writing, scoped to the
`deal_id`s this loader owns. The anchor set is fully re-derived from
`prospectus_extract.json` on every run, so nothing is lost by deleting first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date

from pymongo import ASCENDING, UpdateOne

from ccf.config import REPO_ROOT, mongo_db
from ccf.servicer_report import parse_servicer_report
from generators.extract_prospectus import normalize
from generators.segment_passages import segment

REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
EXTRACT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"
CLASSIFICATION = "public"
BATCH = 500


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    ext = {d["deal_id"]: d for d in json.loads(EXTRACT.read_text())["deals"]}
    today = date.today().isoformat()

    documents, passages, trigger_anchors = [], [], []
    deal_ids: list[str] = []

    for deal in reg["deals"]:
        deal_id = deal["deal_id"]
        deal_ids.append(deal_id)
        base = REPO_ROOT / "sources" / "absee" / deal["slug"]

        text = normalize((base / "prospectus.htm").read_text(errors="replace"))
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest != ext[deal_id]["text_sha256"]:
            raise RuntimeError(
                f"{deal_id}: prospectus text hash disagrees with the extract. "
                f"The offsets in prospectus_extract.json point at different "
                f"characters than the text about to be stored. Re-run "
                f"generators/extract_prospectus.py.")

        doc_id = f"abs-prospectus-{deal_id}"
        ps = segment(text, doc_id)
        documents.append({
            "document_id": doc_id, "deal_id": deal_id, "form": "424B5",
            "cik": deal["cik"], "sec_name": deal["legal_name"],
            "text": text, "text_length": len(text), "text_sha256": digest,
            "passage_count": len(ps), "classification": CLASSIFICATION,
            "residency": "US", "provenance": "public",
            "source": "SEC EDGAR Form 424B5", "retrieved_at": today,
        })
        passages.extend(ps)

        # Bind each trigger to the passage whose span contains its definition.
        for trig in ext[deal_id]["triggers"]:
            hit = next((p for p in ps
                        if p["start_offset"] <= trig["start_offset"]
                        and p["end_offset"] >= trig["end_offset"]), None)
            if hit is None:
                # The definition straddles a passage boundary. Take the
                # passage containing the START and record that it is partial,
                # rather than silently anchoring to nothing.
                hit = next((p for p in ps
                            if p["start_offset"] <= trig["start_offset"]
                            < p["end_offset"]), None)
            if hit is None:
                raise RuntimeError(
                    f"{deal_id} {trig['name']}: no passage contains offsets "
                    f"{trig['start_offset']}..{trig['end_offset']}. §D requires "
                    f"every threshold to resolve to prospectus text.")
            trigger_anchors.append({
                "_id": f"{trig['trigger_id']}-anchor",
                "trigger_id": trig["trigger_id"], "deal_id": deal_id,
                "document_id": doc_id, "passage_id": hit["passage_id"],
                "start_offset": trig["start_offset"],
                "end_offset": trig["end_offset"],
                "quoted_text": trig["definition_text"],
                "complete_span": (hit["start_offset"] <= trig["start_offset"]
                                  and hit["end_offset"] >= trig["end_offset"]),
                "provenance": "public",
            })

        for month in reg["window"]:
            raw = (base / f"servicer-{month}.htm").read_text(errors="replace")
            stext = normalize(raw)
            sdoc_id = f"abs-servicer-{deal_id}-{month}"
            sps = segment(stext, sdoc_id)
            measures = parse_servicer_report(raw)
            documents.append({
                "document_id": sdoc_id, "deal_id": deal_id, "period": month,
                "form": "10-D EX-99.1", "cik": deal["cik"],
                "sec_name": deal["legal_name"],
                "text": stext, "text_length": len(stext),
                "text_sha256": hashlib.sha256(stext.encode()).hexdigest(),
                "passage_count": len(sps),
                # RULING F52: `source_format` ONLY. This used to carry every
                # parsed servicer measure -- 12 keys x 36 documents, 288 values
                # byte-identical to `abs_servicer_report`, which is their single
                # writer. `delinquency_trigger` was among them, putting one
                # threshold in three stores. The argument for keeping it was
                # that a document transcript is evidence; the argument against
                # is in this repo already -- load_abs_fluree_wave14.py declines
                # to write the same measures for the same reason, so the estate
                # was contradicting itself. Mongo keeps what only Mongo has:
                # the text, the passages and the span offsets.
                #
                # `source_format` stays because it IS a property of the
                # document -- which of the two issuer layouts this filing uses
                # -- and nothing else records it.
                "published_measures": {"source_format":
                                       str(measures["source_format"])},
                "classification": CLASSIFICATION, "residency": "US",
                "provenance": "public",
                "source": "SEC EDGAR Form 10-D EX-99.1", "retrieved_at": today,
            })
            passages.extend(sps)

    print(f"  {len(documents)} documents, {len(passages):,} passages, "
          f"{len(trigger_anchors)} trigger anchors")
    partial = [a for a in trigger_anchors if not a["complete_span"]]
    if partial:
        print(f"  {len(partial)} anchors span a passage boundary (recorded, not hidden)")

    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    db = mongo_db()
    doc_ids = [d["document_id"] for d in documents]
    passage_ids = [p["passage_id"] for p in passages]

    # Only invalidate the embedding when the passage's own text actually
    # changed. Keying on the document hash would be wrong -- a document can
    # change while most of its passages do not -- so this compares against
    # each existing passage's stored `sha256`, which `segment()` already
    # computes per passage. A reload that reproduces byte-identical text
    # (the common case) must not cost the whole corpus its embeddings; that
    # would silently defeat `loaders/embed_passages.py`'s entire reason for
    # being a separate, resumable pass.
    existing_sha = {
        d["_id"]: d.get("sha256")
        for d in db["passage"].find(
            {"document_id": {"$in": doc_ids}}, {"sha256": 1})
    }

    # Write-then-delete, not delete-then-write. A crash between the two
    # steps must leave a *superset* of passages behind, never a document
    # with zero passages behind it -- a document is upserted only after its
    # full new passage set already exists, so it is never visible without
    # the text its trigger anchors resolve into. See the module docstring.
    for i in range(0, len(passages), BATCH):
        ops = []
        for p in passages[i:i + BATCH]:
            fields = {**p, "provenance": "public"}
            if existing_sha.get(p["passage_id"]) != p["sha256"]:
                # New passage, or its text changed since the last load.
                fields["embedding"] = None
                fields["embedding_model"] = None
            # else: leave `embedding`/`embedding_model` out of $set
            # entirely, so whatever Step 4 already wrote is untouched.
            ops.append(UpdateOne({"_id": p["passage_id"]},
                                  {"$set": fields}, upsert=True))
        db["passage"].bulk_write(ops, ordered=False)

    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in documents], ordered=False)

    # Now remove this wave's stale passages -- ones anchored to a
    # document_id we own whose current text no longer produces them.
    # Scoped exactly as before (document_id in doc_ids), plus excluding the
    # ids just written, so the 19,765 passages belonging to earlier waves
    # stay unreachable and nothing just-written is deleted.
    db["passage"].delete_many({
        "document_id": {"$in": doc_ids},
        "_id": {"$nin": passage_ids},
    })

    # Ruling (Defect 1): trigger_anchor is fully re-derived from
    # prospectus_extract.json every run, so delete this wave's anchors before
    # writing rather than upserting over them. Scoped to `deal_id in deal_ids`
    # -- the three deals this loader owns -- so a future run that drops a
    # trigger cannot leave a ghost anchor behind, and no other wave's anchors
    # (there are none yet, but the guard must hold regardless) are reachable.
    db["trigger_anchor"].delete_many({"deal_id": {"$in": deal_ids}})
    db["trigger_anchor"].bulk_write([
        UpdateOne({"_id": a["_id"]}, {"$set": a}, upsert=True)
        for a in trigger_anchors], ordered=False)

    db["passage"].create_index([("document_id", ASCENDING),
                                ("start_offset", ASCENDING)])
    db["trigger_anchor"].create_index([("deal_id", ASCENDING)])
    print("  written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
