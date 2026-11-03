#!/usr/bin/env python3
"""Wave 6 — embed the passage corpus.

Deliberately a **separate, resumable pass** rather than part of the corpus
load. `covenant-cross-reference` §E: embeddings are model-version-driven, and
re-embedding on a model change "invalidates the retrieval surface, not the
text". Coupling them to ingestion would mean re-ingesting filed documents —
which are immutable — every time a model changes.

Consequences of that separation, all of them wanted:

  * a passage with no vector is still retrievable **by anchor**, just not by
    similarity. Lineage does not depend on the retrieval surface.
  * `embedding_model` is stored per passage, so a mixed-model corpus is
    detectable rather than silently incoherent.
  * re-running only embeds what is missing, so a partial failure costs only
    the remainder.

    uv run loaders/embed_passages.py --dry-run
    uv run loaders/embed_passages.py --limit 500     # bounded trial
    uv run loaders/embed_passages.py

Idempotent and resumable: passages already carrying this model's vector are
skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import requests
from pymongo import UpdateOne

from ccf.config import mongo_db

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536
ENDPOINT = "https://api.openai.com/v1/embeddings"

#: Inputs per request. Well under the 2048 cap, chosen so a single failure
#: costs little and progress is visible.
BATCH = 96

#: Characters per input. text-embedding-3-small accepts 8192 tokens; passages
#: are capped at ~3000 chars by the segmenter, so this only guards outliers.
MAX_CHARS = 7000

#: Rough per-1M-token price, for the cost line only. Not authoritative.
PRICE_PER_1M = 0.02


def embed_batch(texts: list[str], api_key: str, *, attempt: int = 0) -> list[list[float]]:
    resp = requests.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": MODEL, "input": texts},
        timeout=120,
    )
    if resp.status_code == 429 or resp.status_code >= 500:
        if attempt >= 5:
            raise RuntimeError(f"{resp.status_code} after retries: {resp.text[:200]}")
        wait = 2 ** attempt
        print(f"      {resp.status_code}; backing off {wait}s")
        time.sleep(wait)
        return embed_batch(texts, api_key, attempt=attempt + 1)
    if resp.status_code >= 400:
        raise RuntimeError(f"{resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    # The API returns results in input order, but index is authoritative.
    ordered = sorted(body["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in ordered], body.get("usage", {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0,
                        help="embed at most N passages (bounded trial)")
    parser.add_argument("--aligned-only", action="store_true",
                        help="embed only structure-aligned passages")
    parser.add_argument("--collection", default="passage",
                        help="collection to embed (passage | research_note | "
                             "memorandum). Research notes and memoranda must "
                             "share the passage embedding space, or the "
                             "ranking-difference measurement is meaningless.")
    parser.add_argument("--text-field", default="text",
                        help="field holding the text to embed")
    parser.add_argument("--filter", default=None,
                        help="extra JSON filter, ANDed onto the missing-"
                             "embedding query -- e.g. restrict a run to one "
                             "wave's rows (`--filter '{\"regime\": \"crr\"}'`) "
                             "without touching other passages that also "
                             "happen to lack a vector for unrelated reasons "
                             "(see docs/known-issues.md #38, #42).")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is unset")
        return 1

    db = mongo_db()
    coll = args.collection
    field = args.text_field
    query: dict = {"$or": [{"embedding": None},
                           {"embedding_model": {"$ne": MODEL}}]}
    if args.aligned_only:
        query["structure_aligned"] = True
    if args.filter:
        # $and, not a top-level key merge -- the base query already uses
        # $or, and a second top-level $or from the filter would silently
        # overwrite it rather than combine with it.
        query = {"$and": [query, json.loads(args.filter)]}

    total_missing = db[coll].count_documents(query)
    already = db[coll].count_documents({"embedding_model": MODEL})
    target = min(total_missing, args.limit) if args.limit else total_missing

    print(f"Embedding pass — {MODEL} ({DIMENSIONS}d) on '{coll}'\n")
    print(f"  already embedded  {already:>7,}")
    print(f"  missing           {total_missing:>7,}")
    print(f"  this run          {target:>7,}")

    if args.dry_run or target == 0:
        if target == 0:
            print("\n  nothing to do — corpus fully embedded with this model")
        else:
            print("\n  DRY RUN — no API calls made.")
        return 0

    done = 0
    tokens = 0
    started = time.monotonic()

    while done < target:
        batch = list(
            db[coll].find(query, {field: 1})
            .limit(min(BATCH, target - done))
        )
        if not batch:
            break
        texts = [(p.get(field) or "")[:MAX_CHARS] or " " for p in batch]
        try:
            vectors, usage = embed_batch(texts, api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"\n  FAILED after {done:,} passages: {exc}")
            print("  re-run to resume; embedded passages are skipped")
            return 1

        tokens += usage.get("total_tokens", 0)
        db[coll].bulk_write([
            UpdateOne(
                {"_id": p["_id"]},
                {"$set": {"embedding": v,
                          "embedding_model": MODEL,
                          "embedding_dimensions": DIMENSIONS}},
            )
            for p, v in zip(batch, vectors)
        ], ordered=False)
        done += len(batch)

        if done % (BATCH * 10) < BATCH:
            rate = done / max(time.monotonic() - started, 0.1)
            print(f"    {done:>7,}/{target:,}  {rate:.0f}/s  "
                  f"{tokens:,} tokens")

    elapsed = time.monotonic() - started
    print(f"\n  embedded {done:,} passages in {elapsed:.0f}s")
    print(f"  {tokens:,} tokens  ~${tokens / 1e6 * PRICE_PER_1M:.4f}")
    print(f"  {coll} now: "
          f"{db[coll].count_documents({'embedding_model': MODEL}):,} "
          f"embedded of {db[coll].count_documents({}):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
