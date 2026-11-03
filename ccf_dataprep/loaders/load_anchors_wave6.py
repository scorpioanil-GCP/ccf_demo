#!/usr/bin/env python3
"""Wave 6 — link Fluree covenants to MongoDB passages by anchor.

This is the join the whole T4 tier rests on. Per `covenant-cross-reference` §C:

    `covenant_id` in Fluree carries a passage anchor of
    {document_id, start_offset, end_offset} resolving into MongoDB.
    This anchor IS the join.

Two disciplines it enforces.

**Resolve by offset, never by re-search.** A covenant extracted at offset N is
anchored to the passage whose span *contains* N. Searching MongoDB for the
covenant's text would risk matching a different occurrence — agreements restate
covenant language in amendments, recitals, and defined terms — and silently
relocate the citation to a passage that says something similar but governs
something else.

**§8.4 Algorithmic Verification.** An anchor is a candidate until the span it
points at hashes to the recorded sha256. Anchors that fail are not served: they
are recorded as **Context Debt**, which `covenant-cross-reference` §F wants
present (>= 1 covenant with an unresolvable definition) rather than papered over.

    uv run loaders/load_anchors_wave6.py --dry-run
    uv run loaders/load_anchors_wave6.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date

from ccf import fluree
from ccf.config import (EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2,
                        REPO_ROOT, mongo_db, pg_connect)

SCREEN = REPO_ROOT / "sources" / "screening"
BATCH = 400

P_EVIDENCED_BY = f"{EX}evidencedBy"
P_CONTEXT_DEBT = f"{EX}contextDebt"

#: The rows in `ccf_v2.context_debt` this loader OWNS, and may therefore
#: replace on a re-run. The register is estate-wide -- Wave 10 writes
#: `subject_kind='person'` rows and Wave 11a writes `subject_kind='rating_action'`
#: rows into the same table -- so scoping this predicate is what keeps a re-run
#: of Wave 6 from destroying them.
#:
#: The boundary is not a convention invented here: Wave 10's migration created
#: the partial unique index
#:
#:     ux_context_debt_subject ON context_debt (subject_kind, subject_key)
#:         WHERE subject_kind IS NOT NULL
#:
#: explicitly so that covenant-shaped rows never participate in its upsert.
#: This predicate is that index's exact complement, so the two territories are
#: disjoint by schema rather than by discipline.
#:
#: Exported as a module constant, NOT inlined, because
#: `validators/test_context_debt_scope.py` proves the scoping works by
#: executing THIS string -- a copy would let the test drift from what ships
#: (known-issues.md §9.1 is the same lesson, learned the expensive way).
DEBT_OWNED_BY_WAVE6 = "subject_kind IS NULL"



def _slug(s: str) -> str:
    """Filename -> URI-safe segment. Keeps the document distinguishable."""
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")


def t(s: str, p: str, o: str, *, lit: bool = False) -> str:
    obj = ('"' + str(o).replace("\\", "\\\\").replace('"', '\\"')
           .replace("\n", " ") + '"') if lit else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = mongo_db()
    today = date.today().isoformat()

    # Covenants extracted from filed text carry a source accession and offset.
    # Engineered covenants have no offset and are correctly unanchorable.
    covenant_docs = json.loads(
        (SCREEN / "covenants_extracted.json").read_text()
    )["documents"]

    # Map accession -> the document_id(s) segmented into MongoDB.
    doc_by_accession: dict[str, list[str]] = {}
    # `.get`, not `[...]`: 89 of the 249 documents in `fibo_v2` carry no
    # `accession` -- later waves (narrative, ABS, UCC) segment documents that
    # are not SEC filings keyed that way. This loader matches ON accession, so
    # a document without one simply cannot match and is skipped. Indexing
    # raised `KeyError` and made the loader UNRUNNABLE against the current
    # estate, which is how a Wave 6 re-run stopped being possible without
    # anyone noticing -- nothing re-runs it in the suite.
    for d in db["document"].find({}, {"document_id": 1, "accession": 1}):
        acc = d.get("accession")
        if acc:
            doc_by_accession.setdefault(acc, []).append(d["document_id"])

    triples: list[str] = []
    anchored = 0
    debt: list[dict] = []
    verified = 0
    hash_failed = 0

    for doc in covenant_docs:
        if not doc["covenants"]:
            continue
        doc_ids = doc_by_accession.get(doc["accession"], [])
        if not doc_ids:
            for c in doc["covenants"]:
                debt.append({
                    "facility_accession": doc["accession"],
                    "covenant_type": c["covenant_type"],
                    "reason": "source document not in the MongoDB corpus",
                })
            continue

        for c in doc["covenants"]:
            offset = c["offset"]
            found = None
            for document_id in doc_ids:
                # Resolve BY OFFSET: the passage whose span contains it.
                passage = db["passage"].find_one({
                    "document_id": document_id,
                    "start_offset": {"$lte": offset},
                    "end_offset": {"$gt": offset},
                }, {"passage_id": 1, "start_offset": 1, "end_offset": 1,
                    "sha256": 1, "text": 1})
                if passage:
                    found = (document_id, passage)
                    break

            if not found:
                debt.append({
                    "facility_accession": doc["accession"],
                    "covenant_type": c["covenant_type"],
                    "offset": offset,
                    "reason": "no passage span contains the extracted offset",
                })
                continue

            document_id, passage = found

            # §8.4: the anchor is a candidate until the span verifies.
            actual = hashlib.sha256(
                (passage.get("text") or "").encode("utf-8")
            ).hexdigest()
            if actual != passage["sha256"]:
                hash_failed += 1
                debt.append({
                    "facility_accession": doc["accession"],
                    "covenant_type": c["covenant_type"],
                    "passage_id": passage["passage_id"],
                    "reason": "sha256 mismatch — span no longer hashes to the "
                              "recorded value; claim dropped rather than served",
                })
                continue
            verified += 1

            # The key MUST carry the document. `covenants_extracted.json`
            # holds 60 entries across 47 accessions -- one filing appears once
            # per exhibit, and XPO 0001104659-26-068522 carries two separate
            # credit agreements (ex10-1, ex10-2) each with its own `leverage`,
            # `fixed_charge_coverage` and `secured_leverage` covenant at
            # different thresholds and different spans. Keyed on accession
            # alone, six URIs each received two covenants from two agreements,
            # and a join over the four anchor literals returned the
            # cross-product: 79 candidates, 36 failing their own sha256.
            #
            # The truncation is gone too. `secured_leverage` and
            # `fixed_charge_coverage` reduce to `SECURED_` and `FIXED_CH`,
            # which do not collide today and are one covenant type away.
            # See docs/known-issues.md 61.3 and the Wave 22 binding section.
            cid = (f"{EX}COVSRC-{doc['accession'].replace('-', '')}"
                   f"-{_slug(doc['document'])}"
                   f"-{c['covenant_type'].upper()}")
            triples += [
                t(cid, f"{EX}covenantType", c["covenant_type"], lit=True),
                t(cid, f"{EX}threshold", str(c["threshold"]), lit=True),
                # The anchor: four fields, and the join.
                t(cid, P_EVIDENCED_BY, f"{EX}passage/{passage['passage_id']}"),
                t(cid, f"{EX}documentId", document_id, lit=True),
                t(cid, f"{EX}startOffset", str(passage["start_offset"]), lit=True),
                t(cid, f"{EX}endOffset", str(passage["end_offset"]), lit=True),
                t(cid, f"{EX}passageSha256", passage["sha256"], lit=True),
                t(cid, f"{EX}anchorVerified", "true", lit=True),
                t(cid, f"{EX}provenance", "public", lit=True),
            ]
            anchored += 1

    # Context Debt is asserted, not logged. A consumer must be able to see the
    # completeness shortfall in the product rather than infer it from absence.
    #
    # T-Box first. Waves 5 and 7 declare their ex: classes; this one never
    # did, so `ex:ContextDebt` carried a schemaNote in the ledger written by
    # no code in the repo. Restored 2026-08-21 — validators/orphan_terms.py.
    triples += [
        t(f"{EX}ContextDebt", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
          "http://www.w3.org/2002/07/owl#Class"),
        t(f"{EX}ContextDebt", "http://www.w3.org/2000/01/rdf-schema#label",
          "ContextDebt (ex: extension)", lit=True),
        t(f"{EX}ContextDebt", f"{EX}isFiboTerm", "false", lit=True),
        t(f"{EX}ContextDebt", f"{EX}schemaNote",
          EX_EXTENSION_SCHEMA_NOTE, lit=True),
    ]
    for i, d in enumerate(debt):
        did = f"{EX}DEBT-{i:04d}"
        triples += [
            t(did, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
              f"{EX}ContextDebt"),
            t(did, f"{EX}covenantType", d["covenant_type"], lit=True),
            t(did, f"{EX}reason", d["reason"], lit=True),
            t(did, f"{EX}sourceAccession", d["facility_accession"], lit=True),
        ]

    print("Wave 6 — passage anchors\n")
    print(f"  covenants anchored and verified   {anchored:>5}")
    print(f"  sha256 verifications passed       {verified:>5}")
    print(f"  sha256 failures (claims dropped)  {hash_failed:>5}")
    print(f"  Context Debt entries              {len(debt):>5}   "
          f"(§F wants >= 1)")
    print(f"  triples to write                  {len(triples):>5}")

    if debt:
        reasons: dict[str, int] = {}
        for d in debt:
            reasons[d["reason"][:52]] = reasons.get(d["reason"][:52], 0) + 1
        print(f"\n  Context Debt reasons:")
        for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"    {n:>4}  {reason}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    # Record the debt in Postgres too, so a join query can surface it without
    # a SPARQL round trip.
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".context_debt (
                debt_id      SERIAL PRIMARY KEY,
                accession    TEXT NOT NULL,
                covenant_type TEXT,
                reason       TEXT NOT NULL,
                recorded_at  DATE NOT NULL
            )""")
        # Replace only THIS loader's rows. An unconditional TRUNCATE stood
        # here until 2026-08-22 and silently destroyed Wave 10's 133 person
        # rows and Wave 11a's 169 rating-action rows on any re-run, on any
        # branch -- known-issues.md §12.8.
        cur.execute(f'DELETE FROM "{PG_SCHEMA_V2}".context_debt '
                    f'WHERE {DEBT_OWNED_BY_WAVE6}')
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".context_debt '
            "(accession, covenant_type, reason, recorded_at) "
            "VALUES (%s,%s,%s,%s)",
            [(d["facility_accession"], d["covenant_type"], d["reason"], today)
             for d in debt],
        )
        conn.commit()

    print(f"\n  written. ledger t={fluree.ledger_t()}, "
          f"{fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
