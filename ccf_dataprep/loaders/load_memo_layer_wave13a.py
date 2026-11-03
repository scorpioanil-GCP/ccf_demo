#!/usr/bin/env python3
"""Wave 13a stage 4b — the internal memo layer into its three stores.

    uv run loaders/load_memo_layer_wave13a.py --dry-run
    uv run loaders/load_memo_layer_wave13a.py

Store split per Q019 §3, single-writer throughout:

    MongoDB    the memoranda themselves (§F3) — document text is Mongo's slice
    Postgres   section templates (§F7) and Context Debt weights — reference data
    Fluree     the policy envelopes and their versions (§F8) — `P`, `T`

**The debt weights live in Postgres on purpose.** §D step 7 computes aggregate
Context Debt from four weighted components. If the weights were constants in
the computation, a validator recomputing debt would be checking the computation
against its own constants — true by construction and unable to fail. Putting
them in a table means the gate and the product read the same rows, and changing
a weight changes both.

Additive and idempotent: upsert everywhere, no DELETE, no TRUNCATE. Ids are
content-derived (`known-issues.md` §13.3), so re-running cannot repoint an
existing row.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from pymongo import ASCENDING, UpdateOne

from ccf import fluree
from ccf.config import EX, EX_EXTENSION_SCHEMA_NOTE
from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import assert_v2_schema, mongo_db, pg_connect
from generators.generate_memo_layer import ARTIFACT

BATCH = 400
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

#: Reused, NOT redeclared — Wave 5 asserts this class's T-box and Waves 11a,
#: 11b and 12 already reuse it. A second declaration would be a duplicate
#: assertion of the same triple, which is harmless in RDF and misleading in a
#: repository people read.
C_POLICY_VERSION = f"{EX}PolicyVersion"

#: New `ex:` predicates. Each is an application extension with no FIBO
#: equivalent — a credit-memo policy envelope is a bank-internal construct.
#: Declared with the standard schema note so `validators/orphan_terms.py` can
#: reproduce them from this source.
P_ECOA_RESTRICTED = f"{EX}ecoaReasoningPathRestricted"
P_REG_O_THRESHOLD = f"{EX}regOInsiderThresholdUsd"
P_LIMIT_ENVELOPE = f"{EX}creditLimitEnvelopeUsd"
P_DEBT_TOLERANCE = f"{EX}debtToleranceDefault"
NEW_PREDICATES = [P_ECOA_RESTRICTED, P_REG_O_THRESHOLD, P_LIMIT_ENVELOPE,
                  P_DEBT_TOLERANCE]

P_VALID_FROM = f"{EX}validFrom"
P_VALID_TO = f"{EX}validTo"
P_SUPERSEDED_BY = f"{EX}supersededBy"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".memo_section_template (
    memo_type     TEXT    NOT NULL,
    section_order INTEGER NOT NULL,
    section_name  TEXT    NOT NULL,
    provenance    TEXT    NOT NULL,
    PRIMARY KEY (memo_type, section_order)
);
COMMENT ON TABLE "{S}".memo_section_template IS
  'credit-memo-context §F7: four memo types with DISTINCT section sets. The '
  'section-coverage gate requires every section here to carry either evidence '
  'or a named debt entry.';

CREATE TABLE IF NOT EXISTS "{S}".debt_weight (
    component   TEXT    NOT NULL PRIMARY KEY,
    weight      NUMERIC NOT NULL,
    provenance  TEXT    NOT NULL,
    CONSTRAINT debt_weight_unit CHECK (weight >= 0 AND weight <= 1)
);
COMMENT ON TABLE "{S}".debt_weight IS
  'credit-memo-context §D step 7 component weights. Stored rather than coded '
  'so a validator recomputing aggregate debt reads the same rows the product '
  'does, instead of checking a computation against its own constants.';
"""


def t(s: str, p: str, o: str, *, lit: bool = False) -> str:
    obj = ('"' + str(o).replace("\\", "\\\\").replace('"', '\\"')
           .replace("\n", " ") + '"') if lit else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_v2_schema(S)
    art = json.loads(ARTIFACT.read_text())
    memoranda = art["memoranda"]
    templates = art["section_templates"]
    weights = art["debt_weights"]
    versions = art["policy_versions"]
    today = date.today().isoformat()

    # --- Fluree triples ---------------------------------------------------
    triples: list[str] = []
    for pred in NEW_PREDICATES:
        triples += [
            t(pred, RDFS_LABEL, f"{pred.rsplit('/', 1)[-1]} (ex: extension)",
              lit=True),
            t(pred, f"{EX}isFiboTerm", "false", lit=True),
            t(pred, f"{EX}schemaNote", EX_EXTENSION_SCHEMA_NOTE, lit=True),
        ]
    for i, v in enumerate(versions):
        node = f"{EX}{v['policy_version']}"
        triples += [
            t(node, RDF_TYPE, C_POLICY_VERSION),
            t(node, RDFS_LABEL, v["policy_version"], lit=True),
            t(node, P_VALID_FROM, v["effective_date"], lit=True),
            t(node, P_ECOA_RESTRICTED,
              str(v["ecoa_reasoning_path_restricted"]).lower(), lit=True),
            t(node, P_REG_O_THRESHOLD, str(v["reg_o_insider_threshold_usd"]),
              lit=True),
            t(node, P_LIMIT_ENVELOPE, str(v["credit_limit_envelope_usd"]),
              lit=True),
            t(node, P_DEBT_TOLERANCE, str(v["debt_tolerance_default"]),
              lit=True),
            t(node, f"{EX}provenance", "synthetic — internal", lit=True),
        ]
        # The earlier version is closed the day before the later begins, and
        # points at its successor, so an `as_of` query resolves exactly one.
        if i + 1 < len(versions):
            nxt = versions[i + 1]
            end = date.fromisoformat(nxt["effective_date"]).toordinal() - 1
            triples.append(t(node, P_VALID_TO,
                             date.fromordinal(end).isoformat(), lit=True))
            triples.append(t(node, P_SUPERSEDED_BY,
                             f"{EX}{nxt['policy_version']}"))

    print("Wave 13a — internal memo layer load\n")
    print(f"  MongoDB   {len(memoranda)} memoranda")
    print(f"  Postgres  {len(templates)} template rows, {len(weights)} weights")
    print(f"  Fluree    {len(triples)} triples "
          f"({len(versions)} policy versions, {len(NEW_PREDICATES)} new ex: terms)")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{S}".memo_section_template '
            "(memo_type, section_order, section_name, provenance) "
            "VALUES (%s,%s,%s,%s) ON CONFLICT (memo_type, section_order) "
            "DO UPDATE SET section_name=EXCLUDED.section_name",
            [(r["memo_type"], r["section_order"], r["section_name"],
              r["provenance"]) for r in templates])
        cur.executemany(
            f'INSERT INTO "{S}".debt_weight (component, weight, provenance) '
            "VALUES (%s,%s,%s) ON CONFLICT (component) DO UPDATE SET "
            "weight=EXCLUDED.weight",
            [(k, v, "synthetic — internal") for k, v in weights.items()])
        conn.commit()

    db = mongo_db()
    db["memorandum"].bulk_write([
        UpdateOne({"_id": m["memorandum_id"]}, {"$set": m}, upsert=True)
        for m in memoranda], ordered=False)
    db["memorandum"].create_index([("borrower_lei", ASCENDING)])
    db["memorandum"].create_index([("memo_type", ASCENDING)])

    print(f"\n  memorandum            {db['memorandum'].count_documents({}):>6}"
          f"   (§F3 wants ~40)")
    with pg_connect() as conn, conn.cursor() as cur:
        for tbl in ("memo_section_template", "debt_weight"):
            cur.execute(f'SELECT count(*) FROM "{S}".{tbl}')
            print(f"  {tbl:<22}{cur.fetchone()[0]:>6}")
    print(f"  ledger t={fluree.ledger_t()}, {fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
