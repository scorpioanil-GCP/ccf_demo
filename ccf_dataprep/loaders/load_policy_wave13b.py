#!/usr/bin/env python3
"""Wave 13b Task 6 — load policy, residency constraint and refresh state.

Reads `sources/screening/wave13b_policy.json`.

    Postgres  bo_threshold        18 rows  (P) keyed (jurisdiction, intent)
              kyc_refresh_state   50 rows  (T)
              principal           +1 row, +1 column `sees_eu_person_data`
    Fluree    ResidencyConstraint  1 node with 27 appliesToCountry assertions
              subjectToConstraint  one edge per EU-resident person

## Why `principal` gains a column rather than a lookup table

The estate already expresses entitlement as a boolean column on `principal`
(`sees_mnpi`, `sees_need_to_know`), and `validators/conditions.py` reads those
columns live specifically so a loader regression that leaves a flag at its
default is caught. A third entitlement in a different shape would need its own
reading convention for no gain.

The new principal `PRIN-KYC-004` differs from the existing three on **exactly
one** entitlement. That is what makes §F7's diff interpretable: when the same
traversal returns different results under two principals, there is one
candidate cause.

## The constraint is in Fluree because it is policy binding, not an attribute

§C files data-residency constraints under Fluree (`P`), and Q019 §3 gives
Fluree policy binding. `ex:subjectToConstraint` is an object property, so a
`Person` node gains an edge to the constraint and no literal — the graph can be
traversed under a policy without any person attribute being copied out of
Postgres.

    uv run loaders/load_policy_wave13b.py --dry-run
    uv run loaders/load_policy_wave13b.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf import fluree
from ccf.config import (
    EX,
    EX_EXTENSION_SCHEMA_NOTE,
    FLUREE_LEDGER_V2,
    PG_SCHEMA_V2,
    REPO_ROOT,
    assert_v2_schema,
    pg_connect,
)

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_policy.json"
BATCH = 500

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"

C_RESIDENCY_CONSTRAINT = f"{EX}ResidencyConstraint"
P_SUBJECT_TO_CONSTRAINT = f"{EX}subjectToConstraint"
P_REQUIRES_ENTITLEMENT = f"{EX}requiresEntitlement"
P_APPLIES_TO_COUNTRY = f"{EX}appliesToCountry"
P_IS_FIBO_TERM = f"{EX}isFiboTerm"
P_SCHEMA_NOTE = f"{EX}schemaNote"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".bo_threshold (
    jurisdiction  text    NOT NULL,
    -- §B: the threshold is bound to INTENT. Onboarding uses the statutory
    -- 25%; sanctions screening uses any stake, because a sanctioned party at
    -- 3% still taints the exposure. One threshold per jurisdiction would make
    -- the intent parameter decorative.
    intent        text    NOT NULL,
    threshold_pct numeric NOT NULL,
    basis         text    NOT NULL,
    provenance    text    NOT NULL,
    PRIMARY KEY (jurisdiction, intent)
);

CREATE TABLE IF NOT EXISTS "{S}".kyc_refresh_state (
    lei          char(20) PRIMARY KEY,
    client_name  text     NOT NULL,
    risk_rating  text     NOT NULL,
    cycle_days   integer  NOT NULL,
    last_refresh date     NOT NULL,
    next_due     date     NOT NULL,
    -- The decision reference. Anchored to the artifact's fixed as_of, never
    -- to now(): a tracker anchored on the clock reclassifies its own rows
    -- every day it is not re-run (known-issues.md §12).
    as_of        date     NOT NULL,
    status       text     NOT NULL,
    days_overdue integer  NOT NULL,
    provenance   text     NOT NULL
);

ALTER TABLE "{S}".principal
    ADD COLUMN IF NOT EXISTS sees_eu_person_data boolean NOT NULL DEFAULT false;
"""


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def uri(local: str) -> str:
    return f"{EX}{local}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Load Wave 13b policy")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())
    constraint = doc["residency_constraint"]
    principal = doc["eu_principal"]

    threshold_rows = [(t["jurisdiction"], t["intent"], t["threshold_pct"],
                       t["basis"], t["provenance"]) for t in doc["thresholds"]]
    refresh_rows = [(r["lei"], r["client_name"], r["risk_rating"],
                     r["cycle_days"], r["last_refresh"], r["next_due"],
                     r["as_of"], r["status"], r["days_overdue"],
                     r["provenance"]) for r in doc["refresh_state"]]

    print(f"Wave 13b Task 6 — policy into {S} + Fluree\n")
    print(f"  as_of                 {doc['as_of']}")
    print(f"  bo_threshold          {len(threshold_rows):>4}   "
          f"intents: {dict(Counter(t[1] for t in threshold_rows))}")
    print(f"  kyc_refresh_state     {len(refresh_rows):>4}   "
          f"status: {dict(Counter(r[7] for r in refresh_rows))}")
    print(f"  principal             +1  {principal['principal_id']}")
    print(f"  residency constraint  {constraint['constraint_id']} over "
          f"{len(constraint['applies_to_countries'])} countries")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.execute(f'SELECT count(*) FROM "{S}".principal')
        principals_before = cur.fetchone()[0]

        cur.executemany(
            f'INSERT INTO "{S}".bo_threshold '
            "(jurisdiction, intent, threshold_pct, basis, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (jurisdiction, intent) DO UPDATE SET "
            "threshold_pct=EXCLUDED.threshold_pct, basis=EXCLUDED.basis, "
            "provenance=EXCLUDED.provenance",
            threshold_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".kyc_refresh_state '
            "(lei, client_name, risk_rating, cycle_days, last_refresh, "
            " next_due, as_of, status, days_overdue, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei) DO UPDATE SET "
            "client_name=EXCLUDED.client_name, "
            "risk_rating=EXCLUDED.risk_rating, cycle_days=EXCLUDED.cycle_days, "
            "last_refresh=EXCLUDED.last_refresh, next_due=EXCLUDED.next_due, "
            "as_of=EXCLUDED.as_of, status=EXCLUDED.status, "
            "days_overdue=EXCLUDED.days_overdue, provenance=EXCLUDED.provenance",
            refresh_rows,
        )
        cur.execute(
            f'INSERT INTO "{S}".principal '
            "(principal_id, name, side, perspective, sees_mnpi, "
            " sees_need_to_know, sees_eu_person_data, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (principal_id) DO UPDATE SET "
            "name=EXCLUDED.name, side=EXCLUDED.side, "
            "perspective=EXCLUDED.perspective, sees_mnpi=EXCLUDED.sees_mnpi, "
            "sees_need_to_know=EXCLUDED.sees_need_to_know, "
            "sees_eu_person_data=EXCLUDED.sees_eu_person_data, "
            "provenance=EXCLUDED.provenance",
            (principal["principal_id"], principal["name"], principal["side"],
             principal["perspective"], principal["sees_mnpi"],
             principal["sees_need_to_know"],
             principal["sees_eu_person_data"], principal["provenance"]),
        )
        conn.commit()

        # Which persons the constraint actually binds — resolved from the
        # store, not from the generator's idea of who is EU-resident.
        cur.execute(
            f'SELECT person_key FROM "{S}".psc_person '
            "WHERE country_of_residence = ANY(%s) ORDER BY person_key",
            (constraint["applies_to_countries"],),
        )
        eu_resident = [r[0] for r in cur.fetchall()]

        cur.execute(f'SELECT count(*) FROM "{S}".bo_threshold')
        n_thresholds = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".kyc_refresh_state')
        n_refresh = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".principal')
        principals_after = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".principal '
                    "WHERE sees_eu_person_data")
        n_eu_entitled = cur.fetchone()[0]
        cur.execute(f"""
            SELECT count(*) FROM (
                SELECT jurisdiction FROM "{S}".bo_threshold
                GROUP BY jurisdiction
                HAVING count(DISTINCT threshold_pct) > 1) t""")
        n_intent_sensitive = cur.fetchone()[0]

    node = uri(constraint["constraint_id"])
    triples = [
        triple(node, RDF_TYPE, C_RESIDENCY_CONSTRAINT),
        triple(node, RDFS_LABEL, constraint["label"], literal=True),
        triple(node, RDFS_COMMENT, constraint["basis"], literal=True),
        triple(node, P_REQUIRES_ENTITLEMENT,
               constraint["requires_entitlement"], literal=True),
    ]
    for country in constraint["applies_to_countries"]:
        triples.append(triple(node, P_APPLIES_TO_COUNTRY, country, literal=True))
    for person_key in eu_resident:
        triples.append(triple(uri(person_key), P_SUBJECT_TO_CONSTRAINT, node))
    for term in (C_RESIDENCY_CONSTRAINT, P_SUBJECT_TO_CONSTRAINT,
                 P_REQUIRES_ENTITLEMENT, P_APPLIES_TO_COUNTRY):
        triples += [
            triple(term, P_IS_FIBO_TERM, "false", literal=True),
            triple(term, P_SCHEMA_NOTE, EX_EXTENSION_SCHEMA_NOTE, literal=True),
        ]

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    n_bound = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_SUBJECT_TO_CONSTRAINT}> ?o }}")
    n_countries = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_APPLIES_TO_COUNTRY}> ?o }}")

    print(f"\n  Postgres: bo_threshold {n_thresholds} "
          f"({n_intent_sensitive} jurisdictions where intent CHANGES the "
          f"answer) · kyc_refresh_state {n_refresh} · principals "
          f"{principals_before} -> {principals_after} ({n_eu_entitled} EU-entitled)")
    print(f"  Fluree:   {n_bound} persons bound to {constraint['constraint_id']} "
          f"· {n_countries} countries in scope")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")

    failures = []
    if n_thresholds != len(threshold_rows) or n_refresh != len(refresh_rows):
        failures.append("Postgres counts disagree with the artifact")
    if n_intent_sensitive < 1:
        failures.append("no jurisdiction's threshold changes with intent — "
                        "the intent parameter would be decorative")
    if n_eu_entitled != 1:
        failures.append(f"{n_eu_entitled} principals hold EU entitlement; "
                        f"§F7's diff needs exactly one that does and others "
                        f"that do not")
    if n_bound != len(eu_resident):
        failures.append(f"{n_bound} persons bound to the constraint, expected "
                        f"{len(eu_resident)}")
    if not eu_resident:
        failures.append("no EU-resident person exists to bind — §F7 cannot be "
                        "demonstrated")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  both stores match the artifact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
