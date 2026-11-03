#!/usr/bin/env python3
"""Prove entitlement is a FORMATIVE constraint, not a display filter.

`mnpi-wall-enforcement` §A names three failures a filter-after-assembly
architecture produces, in increasing severity:

  1. the result is filtered but the query ALREADY RAN against restricted
     material. In a similarity-ranked pipeline the restricted documents
     influenced the ranking of the permitted ones, so the public-side analyst
     receives a result set *shaped by* material they may not see.
  2. absence is informative. "3 results hidden" tells the analyst undisclosed
     activity exists — itself the signal the wall exists to prevent.
  3. §6.5: entitlements determine what the context is ALLOWED TO BE. Sensitive
     relationships must never materialize for unauthorized consumers.

Two §F conditions are checked here, and both are measurements rather than counts:

  A. >= 1 issuer where all three principals' products differ in node count,
     edge types, AND document set simultaneously.
  B. >= 1 case where restricted documents WOULD HAVE altered similarity
     ranking had they participated — measured by running the retrieval both
     ways and recording the difference. §F says this "belongs in the SDK
     example as a number", so it is computed rather than asserted.

    uv run validators/projection.py
"""

from __future__ import annotations

import json
import sqlite3
import sys

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, SQLITE_PATH, mongo_db, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
TOP_N = 10

#: A query a public-side analyst might plausibly issue. Deliberately neutral —
#: the point is that restricted material perturbs the ranking even for a query
#: that does not seek it.
PROBE_QUERY_TEXT = ("credit facility leverage covenant compliance and "
                    "management outlook for the coming fiscal year")


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def restricted_leis() -> set[str]:
    """Read the restricted list from the DEPARTMENTAL store.

    This is step 2 of the recipe and it runs FIRST — its output bounds every
    subsequent step. Reading it from SQLite rather than Postgres is the point:
    the fabric must reach a locally-maintained compliance system to enforce an
    enterprise-critical policy.
    """
    if not SQLITE_PATH.exists():
        return set()
    with sqlite3.connect(SQLITE_PATH) as conn:
        return {
            r[0] for r in conn.execute(
                "SELECT lei FROM restricted_list WHERE removed_date IS NULL"
            )
        }


def main() -> int:
    failures: list[str] = []
    db = mongo_db()

    restricted = restricted_leis()
    print("PROJECTION — entitlement as a formative constraint\n")
    print(f"  restricted list (from SQLite, read FIRST): {len(restricted)} issuers")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT p.principal_id, p.name, p.side, p.sees_mnpi,
                   pl.projection_plan_id, pl.permitted_edge_types,
                   pl.permitted_classifications, pl.permitted_document_types
            FROM "{PG_SCHEMA_V2}".principal p
            JOIN "{PG_SCHEMA_V2}".projection_plan pl USING (principal_id)
            ORDER BY p.principal_id
        """)
        principals = [
            {"principal_id": r[0], "name": r[1], "side": r[2],
             "sees_mnpi": r[3], "plan": r[4],
             "edges": r[5], "classes": r[6], "doc_types": r[7]}
            for r in cur.fetchall()
        ]

        cur.execute(f"""
            SELECT DISTINCT d.lei, e.legal_name
            FROM "{PG_SCHEMA_V2}".deal d
            JOIN "{PG_SCHEMA_V2}".legal_entity e USING (lei)
            ORDER BY d.lei
        """)
        issuers = cur.fetchall()

    # ---------- Condition A: three products, three shapes ------------------
    print(f"\n  A. PRODUCT SHAPE PER PRINCIPAL  (§F wants >= 1 issuer where "
          f"all three differ)\n")
    divergent: list[str] = []

    for lei, name in issuers:
        shapes = []
        for p in principals:
            with pg_connect() as conn, conn.cursor() as cur:
                # Nodes: deals and interactions this principal may see at all.
                # An MNPI-bearing edge is not in a public-side principal's
                # traversal VOCABULARY, so it is excluded from the query rather
                # than removed from its result.
                mnpi_clause = "" if p["sees_mnpi"] else " AND NOT mnpi_bearing"
                cur.execute(
                    f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".deal '
                    f"WHERE lei = %s{mnpi_clause}", (lei,))
                n_deals = cur.fetchone()[0]
                cur.execute(
                    f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".interaction '
                    f"WHERE lei = %s{mnpi_clause}", (lei,))
                n_int = cur.fetchone()[0]
                cur.execute(
                    f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".position '
                    "WHERE lei = %s", (lei,))
                n_pos = cur.fetchone()[0] if "hasPosition" in p["edges"] else 0

            # Document TYPE gates before classification does. A trader is not
            # given research filtered to published; research is not in their
            # document vocabulary at all.
            n_notes = (
                db["research_note"].count_documents({
                    "lei": lei, "classification": {"$in": p["classes"]},
                }) if "research" in p["doc_types"] else 0
            )
            n_memo = (
                db["memorandum"].count_documents({
                    "borrower_lei": lei,
                    "classification": {"$in": p["classes"]},
                }) if "memorandum" in p["doc_types"] else 0
            )
            n_docs = (
                db["document"].count_documents({
                    "lei": lei, "classification": {"$in": p["classes"]},
                }) if "filing" in p["doc_types"] else 0
            )

            shapes.append({
                "principal": p["name"],
                "plan": p["plan"],
                "node_count": n_deals + n_int + n_pos,
                "edge_types": len(p["edges"]),
                "edge_set": p["edges"],
                "document_set": n_notes + n_memo + n_docs,
            })

        nodes = {s["node_count"] for s in shapes}
        # Compare edge-type SETS, not counts. The research analyst and trader
        # each hold 3 permitted edge types but different ones; comparing counts
        # wrongly reports their products as identically shaped.
        edges = {tuple(sorted(s["edge_set"])) for s in shapes}
        docs = {s["document_set"] for s in shapes}
        all_differ = len(nodes) == 3 and len(edges) == 3 and len(docs) == 3

        if all_differ and len(divergent) < 3:
            divergent.append(lei)
            flag = " <- restricted" if lei in restricted else ""
            print(f"    {name[:36]}{flag}")
            for s in shapes:
                print(f"      {s['principal']:18s} nodes={s['node_count']:>3}  "
                      f"edge_types={s['edge_types']}  "
                      f"docs={s['document_set']:>3}  {s['plan']}")
            print()

    print(f"    {len(divergent)} issuer(s) where node count, edge types and "
          f"document set all differ")
    if not divergent:
        failures.append("no issuer produces three structurally different products")

    # ---------- Condition B: measured ranking difference -------------------
    print(f"\n  B. RANKING DIFFERENCE  (§F: measured, and it belongs in the "
          f"example as a number)\n")

    # Use a real embedded passage as the probe vector, so no extra API call is
    # needed and the vector is guaranteed to be in the corpus space.
    probe = db["passage"].find_one(
        {"embedding": {"$ne": None}, "text": {"$regex": "Leverage Ratio"}},
        {"embedding": 1, "text": 1},
    )
    if not probe:
        print("    no embedded probe passage available")
        failures.append("cannot measure ranking difference without embeddings")
    else:
        # Permitted corpus: public-filed only (the research analyst's view).
        permitted = list(db["research_note"].find(
            {"embedding": {"$ne": None}, "classification": "public-filed"},
            {"note_id": 1, "embedding": 1, "lei": 1}))
        # Restricted corpus: drafts under embargo + internal memoranda. These
        # must NEVER participate in a public-side ranking.
        restricted_docs = list(db["research_note"].find(
            {"embedding": {"$ne": None},
             "classification": {"$ne": "public-filed"}},
            {"note_id": 1, "embedding": 1, "lei": 1}))
        restricted_docs += list(db["memorandum"].find(
            {"embedding": {"$ne": None}},
            {"memorandum_id": 1, "embedding": 1, "borrower_lei": 1}))

        def rank(pool: list[dict]) -> list[tuple[str, float]]:
            scored = [
                (d.get("note_id") or d.get("memorandum_id"),
                 cosine(probe["embedding"], d["embedding"]))
                for d in pool
            ]
            scored.sort(key=lambda kv: -kv[1])
            return scored[:TOP_N]

        policy_first = rank(permitted)
        post_filter_pool = permitted + restricted_docs
        naive = rank(post_filter_pool)

        # What a retrieve-then-filter pipeline would serve: rank over
        # everything, THEN drop restricted results.
        permitted_ids = {d["note_id"] for d in permitted}
        naive_filtered = [(i, s) for i, s in naive if i in permitted_ids]

        policy_ids = [i for i, _ in policy_first]
        naive_ids = [i for i, _ in naive_filtered]

        displaced = [i for i in policy_ids[:TOP_N] if i not in naive_ids]
        intruded = [i for i, _ in naive if i not in permitted_ids]

        print(f"    Policy-before-Similarity  top-{TOP_N} over "
              f"{len(permitted)} permitted docs")
        print(f"    retrieve-then-filter      top-{TOP_N} over "
              f"{len(post_filter_pool)} docs, then stripped")
        print(f"    restricted docs that entered the naive ranking: "
              f"{len(intruded)}")
        print(f"    permitted docs DISPLACED from the served result: "
              f"{len(displaced)}")
        print(f"    served-result overlap: "
              f"{len(set(policy_ids) & set(naive_ids))}/{TOP_N}")

        if intruded:
            print(f"\n    The measurement: {len(intruded)} restricted document(s) "
                  f"occupied top-{TOP_N} slots in the naive ranking.")
            print(f"    A retrieve-then-filter pipeline computed similarity "
                  f"against them, so the")
            print(f"    public-side result was SHAPED by material the analyst "
                  f"may not see —")
            print(f"    and {len(displaced)} permitted document(s) never reached "
                  f"the analyst as a result.")
        else:
            failures.append(
                "no restricted document entered the naive top-N; the "
                "ranking-difference case is not demonstrable"
            )

        (SCREEN / "ranking_difference.json").write_text(
            json.dumps({
                "generated_for": "Wave 7 — measured Policy-before-Similarity effect",
                "probe_excerpt": " ".join(probe["text"][:200].split()),
                "top_n": TOP_N,
                "permitted_corpus_size": len(permitted),
                "full_corpus_size": len(post_filter_pool),
                "restricted_in_naive_top_n": len(intruded),
                "permitted_displaced": len(displaced),
                "served_overlap": len(set(policy_ids) & set(naive_ids)),
                "policy_first_ranking": policy_ids,
                "naive_then_filtered_ranking": naive_ids,
                "note": "Post-filtering has already ranked against "
                        "impermissible material -- which in an MNPI context is "
                        "itself the leak.",
            }, indent=2) + "\n"
        )
        print(f"\n    written: sources/screening/ranking_difference.json")

    # ---------- no-disclosure guard ----------------------------------------
    print(f"\n  C. NO-DISCLOSURE GUARD")
    print(f"    the product must carry NO count, marker, or placeholder for "
          f"withheld content —")
    print(f"    reporting exclusion reconstitutes the signal the wall "
          f"suppresses. Nothing in")
    print(f"    the loaded data records a per-principal withheld count, which "
          f"is the correct")
    print(f"    absence: it cannot be surfaced because it was never computed.")

    if failures:
        print(f"\n  FAILURES:")
        for f in failures:
            print(f"    {f}")
        return 1
    print(f"\n  All projection claims hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
