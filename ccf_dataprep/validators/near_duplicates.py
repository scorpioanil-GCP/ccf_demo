#!/usr/bin/env python3
"""Detect near-duplicate covenant passages across different facilities.

`covenant-cross-reference` §A names the counterfactual precisely: an LLM
confidently fuses two distinct covenant definitions because their chunked
similarity is high, while passage-level provenance would have shown them
originating in different documents governing different facilities.

A leverage covenant in a 2023 term loan and a leverage covenant in a 2025
revolver look near-identical as text. They are not the same covenant, they do
not share addbacks, and a retrieval pipeline ranking by similarity has **no
structural reason to keep them apart**.

§F wants >= 2 such pairs so the counterfactual can be *demonstrated* — run
similarity without the graph and watch it conflate them, then run it with the
graph and watch the typed edge keep them separate.

This validator finds the pairs and records them, so the demonstration has
named subjects rather than a hope that similarity happens to collide.

    uv run validators/near_duplicates.py
"""

from __future__ import annotations

import json
import sys

from ccf.config import REPO_ROOT, mongo_db

SCREEN = REPO_ROOT / "sources" / "screening"

#: Cosine similarity above which two passages are "near-duplicate" for the
#: purposes of the counterfactual. High enough that a retrieval pipeline would
#: plausibly treat them as the same claim.
THRESHOLD = 0.92

#: Only compare covenant-bearing passages; comparing all 15,934 pairwise is
#: 127M comparisons and the interesting collisions are all in covenant text.
COVENANT_MARKERS = [
    "Leverage Ratio", "Coverage Ratio", "Consolidated EBITDA",
    "shall not permit", "shall not exceed",
]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    # text-embedding-3 returns unit-normalised vectors, so the dot product is
    # already cosine. Normalising again would be harmless but wasteful.
    return dot


def main() -> int:
    db = mongo_db()

    query = {
        "embedding": {"$ne": None},
        "$or": [{"text": {"$regex": m}} for m in COVENANT_MARKERS],
    }
    candidates = list(db["passage"].find(
        query,
        {"passage_id": 1, "document_id": 1, "embedding": 1, "text": 1,
         "heading": 1},
    ).limit(1200))

    print(f"Near-duplicate covenant detection\n")
    print(f"  {len(candidates)} covenant-bearing passages with embeddings")
    if len(candidates) < 2:
        print("  too few to compare — run loaders/embed_passages.py first")
        return 1

    # Document -> filer, so a pair can be confirmed as CROSS-facility. Two
    # near-identical passages inside one agreement are not the interesting
    # case; the counterfactual needs different governing documents.
    doc_meta = {
        d["document_id"]: (d.get("sec_name", ""), d.get("accession", ""))
        for d in db["document"].find({}, {"document_id": 1, "sec_name": 1,
                                          "accession": 1})
    }

    pairs: list[dict] = []
    n = len(candidates)
    for i in range(n):
        pi = candidates[i]
        for j in range(i + 1, n):
            pj = candidates[j]
            if pi["document_id"] == pj["document_id"]:
                continue          # same document — not the counterfactual
            sim = cosine(pi["embedding"], pj["embedding"])
            if sim >= THRESHOLD:
                name_i, acc_i = doc_meta.get(pi["document_id"], ("", ""))
                name_j, acc_j = doc_meta.get(pj["document_id"], ("", ""))
                pairs.append({
                    "similarity": round(sim, 4),
                    "passage_a": pi["passage_id"],
                    "passage_b": pj["passage_id"],
                    "filer_a": name_i, "filer_b": name_j,
                    "accession_a": acc_i, "accession_b": acc_j,
                    "same_filer": name_i == name_j,
                    "excerpt_a": " ".join(pi["text"][:180].split()),
                    "excerpt_b": " ".join(pj["text"][:180].split()),
                })

    pairs.sort(key=lambda p: -p["similarity"])
    cross_filer = [p for p in pairs if not p["same_filer"]]

    print(f"  {len(pairs)} cross-document pairs above {THRESHOLD}")
    print(f"  {len(cross_filer)} of those span DIFFERENT filers  "
          f"(§F wants >= 2)\n")

    for p in (cross_filer or pairs)[:5]:
        print(f"  sim {p['similarity']}  {p['filer_a'][:26]} <-> {p['filer_b'][:26]}")
        print(f"    A: {p['excerpt_a'][:110]}")
        print(f"    B: {p['excerpt_b'][:110]}")
        print()

    (SCREEN / "near_duplicates.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 6 — near-duplicate covenant pairs",
                "threshold": THRESHOLD,
                "note": "These pairs are textually similar and structurally "
                        "distinct. Similarity alone conflates them; the typed "
                        "covenantOf edge keeps them apart. That contrast IS the "
                        "counterfactual §A describes.",
                "pair_count": len(pairs),
                "cross_filer_count": len(cross_filer),
                "pairs": pairs[:200],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"  written: sources/screening/near_duplicates.json")

    if len(cross_filer) < 2:
        print(f"\n  SHORTFALL: §F wants >= 2 cross-filer near-duplicate pairs; "
              f"found {len(cross_filer)}. Lower THRESHOLD or widen the corpus.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
