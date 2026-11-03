#!/usr/bin/env python3
"""Load the reporting bank entity and its capital base.

Reads `sources/screening/reporting_bank.json`.

    Postgres  reporting_bank    2 rows  (the bank and its holding company)
              bank_capital     12 rows  (quarterly Call Report capital)
    Fluree    2 nodes + the RSSD hierarchy edge   (§C files this under `R`)

## Why a new table rather than rows in `legal_entity`

The same reason `registry_company` is separate (Wave 13b Task 2): three checks
in `validators/conditions.py` count `legal_entity` **without** filtering
`is_anchor`, including a `FULL OUTER JOIN` orphan gate against `crosswalk`. Two
crosswalk-less bank rows would turn a green gate red.

There is a second reason here. The bank is not an obligor — it is the
counterparty on the other side of every exposure, and the entity whose capital
is the denominator. Putting it in the obligor table would make
`SELECT * FROM legal_entity` mean two different things.

## What is real, and the boundary that must stay visible

Everything loaded here is public and factual **about the bank itself**: RSSD,
CERT, LEI, holding company, and its own filed Call Report capital. Nothing is
invented, and `provenance` is `public` on every row.

The estate's exposures are `synthetic — internal` and remain so. Attaching them
to a real bank is what the estate already does with 50 real named obligors.
**What must never happen is an engineered limit BREACH reading as a factual
claim about a real institution** — so this loader stops at the entity and the
denominator. Breach scenarios belong to the capstone wave, where they must be
labelled `synthetic — engineered` at the point they are built.

    uv run loaders/load_reporting_bank.py --dry-run
    uv run loaders/load_reporting_bank.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf import fluree
from ccf.party_roles import with_ancestors
from ccf.config import (
    EX,
    FLUREE_LEDGER_V2,
    PG_SCHEMA_V2,
    REPO_ROOT,
    assert_v2_schema,
    pg_connect,
)

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "reporting_bank.json"
BATCH = 500

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
CMNS = "https://www.omg.org/spec/Commons/"
C_BANK = f"{FIBO}FBC/FunctionalEntities/FinancialServicesEntities/Bank"
C_BANK_HOLDING = (f"{FIBO}FBC/FunctionalEntities/FinancialServicesEntities/"
                  f"BankHoldingCompany")
C_ORGANIZATION = f"{CMNS}Organizations/Organization"
C_FORMAL_ORG = f"{CMNS}Organizations/FormalOrganization"
C_LEGAL_ENTITY = f"{CMNS}Organizations/LegalEntity"
P_OWNS = f"{FIBO}FND/OwnershipAndControl/Ownership/owns"
P_LEI = f"{EX}lei"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".reporting_bank (
    rssd          text     PRIMARY KEY,   -- FFIEC NIC identifier
    cert          integer,                -- FDIC certificate, banks only
    legal_name    text     NOT NULL,
    lei           char(20),
    role          text     NOT NULL,      -- reporting_bank | holding_company
    parent_rssd   text,
    city          text,
    state         text,
    provenance    text     NOT NULL,
    source        text     NOT NULL,
    retrieved_at  date     NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".bank_capital (
    rssd            text     NOT NULL
                    REFERENCES "{S}".reporting_bank(rssd) ON DELETE CASCADE,
    -- The Call Report date. §E puts the capital base at ~90 days' volatility
    -- against four hours for exposure — the sharpest freshness mismatch in
    -- the catalog, and one the capstone must DISCLOSE rather than resolve.
    report_date     date     NOT NULL,
    tier1_capital   numeric  NOT NULL,
    tier2_capital   numeric,
    risk_weighted_assets numeric NOT NULL,
    tier1_ratio_pct numeric,
    total_ratio_pct numeric,
    cet1_ratio_pct  numeric,
    total_assets    numeric,
    total_equity    numeric,
    total_deposits  numeric,
    -- Does the quarter's own tier 1 / RWA reproduce its own reported ratio?
    -- Measured at load, stored rather than corrected. 2025-12-31 does NOT:
    -- its RWA is 1,864,923,000 against a reported 15.29% that implies
    -- ~1,928,103,000, a 0.52pp gap where every other quarter agrees to within
    -- 0.005pp. Its RWA is also the only round-thousand figure in the series.
    -- That is an anomaly in FDIC's published data, and silently smoothing it
    -- would hide exactly what §D's "capital-base date coherence" gate exists
    -- to surface.
    ratio_consistent boolean NOT NULL,
    ratio_delta_pp  numeric  NOT NULL,
    -- Unit of every money column in this row. FDIC BankFind reports in
    -- thousands of dollars; ccf_v2.facility is in dollars. Recorded because
    -- the ratio checks above cannot observe the difference -- a ratio is
    -- unit-invariant, so a lost factor of 1,000 passes them silently. See
    -- loaders/load_wave19_postgres.py::assert_capital_magnitudes, which
    -- checks the MAGNITUDE this column implies rather than a ratio.
    unit            text     NOT NULL DEFAULT 'USD_THOUSANDS',
    provenance      text     NOT NULL,
    source          text     NOT NULL,
    PRIMARY KEY (rssd, report_date)
);

CREATE INDEX IF NOT EXISTS bank_capital_date_idx
    ON "{S}".bank_capital (report_date DESC);

COMMENT ON COLUMN "{S}".bank_capital.unit IS
    'Unit of every money column in this row. FDIC BankFind reports in '
    'thousands of dollars; ccf_v2.facility is in dollars. Recorded because '
    'the ratio checks on this table cannot observe the difference.';
"""


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def uri(local: str) -> str:
    return f"{EX}{local}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Load the reporting bank entity")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())
    bank, holdco = doc["bank"], doc["holding_company"]
    retrieved = doc["generated_at"][:10]
    source = "FDIC BankFind API (Call Report figures) + GLEIF"

    bank_rows = [
        (holdco["rssd"], None, holdco["legal_name"], holdco["lei"],
         "holding_company", None, None, None, "public", source, retrieved),
        (bank["rssd"], bank["cert"], bank["legal_name"], bank["lei"],
         "reporting_bank", holdco["rssd"], bank["city"], bank["state"],
         "public", source, retrieved),
    ]

    RATIO_TOLERANCE_PP = 0.15

    capital_rows = []
    inconsistent = []
    for q in doc["capital"]:
        d = q["REPDTE"]
        report_date = date(int(d[:4]), int(d[4:6]), int(d[6:8])).isoformat()
        tier1, rwa = float(q["RBCT1J"]), float(q["RWAJT"])
        reported = q.get("RBC1RWAJ")
        recomputed = tier1 / rwa * 100.0
        delta = abs(recomputed - float(reported)) if reported is not None else 0.0
        consistent = delta <= RATIO_TOLERANCE_PP
        if not consistent:
            inconsistent.append((report_date, round(recomputed, 4), reported,
                                 round(delta, 4)))
        capital_rows.append((
            bank["rssd"], report_date,
            q["RBCT1J"], q.get("RBCT2"), q["RWAJT"], reported,
            q.get("RBCRWAJ"), q.get("RBCT1CER"), q.get("ASSET"), q.get("EQ"),
            q.get("DEP"), consistent, round(delta, 4), "public", source,
        ))

    print(f"Reporting bank entity into {S} + Fluree\n")
    print(f"  bank            {bank['legal_name']}")
    print(f"                  RSSD {bank['rssd']} · LEI {bank['lei']}")
    print(f"  holding company {holdco['legal_name']}  RSSD {holdco['rssd']} · "
          f"LEI {holdco['lei']}")
    print(f"  capital base    {len(capital_rows)} quarters, "
          f"{capital_rows[-1][1]} → {capital_rows[0][1]}")
    print(f"  latest tier 1   {capital_rows[0][2]:,} "
          f"(RWA {capital_rows[0][4]:,.0f}, CET1 {capital_rows[0][7]}%)")
    print(f"  selection       {doc['selection_basis'][:96]}…")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{S}".reporting_bank '
            "(rssd, cert, legal_name, lei, role, parent_rssd, city, state, "
            " provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (rssd) DO UPDATE SET cert=EXCLUDED.cert, "
            "legal_name=EXCLUDED.legal_name, lei=EXCLUDED.lei, "
            "role=EXCLUDED.role, parent_rssd=EXCLUDED.parent_rssd, "
            "city=EXCLUDED.city, state=EXCLUDED.state, "
            "provenance=EXCLUDED.provenance, source=EXCLUDED.source, "
            "retrieved_at=EXCLUDED.retrieved_at",
            bank_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".bank_capital '
            "(rssd, report_date, tier1_capital, tier2_capital, "
            " risk_weighted_assets, tier1_ratio_pct, total_ratio_pct, "
            " cet1_ratio_pct, total_assets, total_equity, total_deposits, "
            " ratio_consistent, ratio_delta_pp, provenance, source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (rssd, report_date) DO UPDATE SET "
            "tier1_capital=EXCLUDED.tier1_capital, "
            "tier2_capital=EXCLUDED.tier2_capital, "
            "risk_weighted_assets=EXCLUDED.risk_weighted_assets, "
            "tier1_ratio_pct=EXCLUDED.tier1_ratio_pct, "
            "total_ratio_pct=EXCLUDED.total_ratio_pct, "
            "cet1_ratio_pct=EXCLUDED.cet1_ratio_pct, "
            "total_assets=EXCLUDED.total_assets, "
            "total_equity=EXCLUDED.total_equity, "
            "total_deposits=EXCLUDED.total_deposits, "
            "ratio_consistent=EXCLUDED.ratio_consistent, "
            "ratio_delta_pp=EXCLUDED.ratio_delta_pp, "
            "provenance=EXCLUDED.provenance, source=EXCLUDED.source",
            capital_rows,
        )
        conn.commit()

        cur.execute(f'SELECT count(*) FROM "{S}".reporting_bank')
        n_banks = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".bank_capital')
        n_capital = cur.fetchone()[0]
        # The ratio the capstone divides by, RECOMPUTED from the two figures
        # rather than read from the reported ratio column. If they disagree,
        # one of them is not what it claims to be.
        cur.execute(f'SELECT count(*) FROM "{S}".bank_capital '
                    "WHERE NOT ratio_consistent")
        n_ratio_drift = cur.fetchone()[0]
        # The LIVE denominator specifically. An anomaly three quarters back is
        # a disclosure; one in the quarter the capstone actually divides by
        # would make every utilisation percentage wrong.
        cur.execute(f'SELECT report_date, ratio_consistent '
                    f'FROM "{S}".bank_capital ORDER BY report_date DESC LIMIT 1')
        latest_date, latest_ok = cur.fetchone()
        cur.execute(f'SELECT count(*) FROM "{S}".legal_entity')
        n_legal_entity = cur.fetchone()[0]

    bank_node, holdco_node = uri(f"RSSD-{bank['rssd']}"), uri(f"RSSD-{holdco['rssd']}")
    triples = []
    for node, cls, name, lei in (
        (bank_node, C_BANK, bank["legal_name"], bank["lei"]),
        (holdco_node, C_BANK_HOLDING, holdco["legal_name"], holdco["lei"]),
    ):
        # Chain closure from ccf.party_roles (known-issues §62).
        for t in (cls, *with_ancestors(C_LEGAL_ENTITY)):
            triples.append(triple(node, RDF_TYPE, t))
        triples.append(triple(node, RDFS_LABEL, name, literal=True))
        if lei:
            triples.append(triple(node, P_LEI, lei, literal=True))
    # §C: "Bank holding structure — FFIEC NIC RSSD hierarchy — Fluree — R".
    # The hierarchy is the EDGE; the RSSD identifiers themselves are Postgres
    # attributes, so nothing is duplicated across the two stores.
    triples.append(triple(holdco_node, P_OWNS, bank_node))

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    n_bank_nodes = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_BANK}> }}")
    n_hierarchy = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ <{holdco_node}> <{P_OWNS}> ?o }}")

    print(f"\n  Postgres: reporting_bank {n_banks} · bank_capital {n_capital}")
    print(f"            quarters where tier 1 / RWA disagrees with the "
          f"reported ratio: {n_ratio_drift} of {n_capital}  "
          f"(flagged, not corrected)")
    for d, recomputed, reported, delta in inconsistent:
        print(f"                {d}  recomputed {recomputed}% vs reported "
              f"{reported}% — {delta}pp")
    print(f"            latest quarter {latest_date}: "
          f"{'reconciles' if latest_ok else 'DOES NOT RECONCILE'}")
    print(f"            legal_entity still {n_legal_entity} (untouched)")
    print(f"  Fluree:   {n_bank_nodes} Bank node · {n_hierarchy} RSSD "
          f"hierarchy edge")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")

    failures = []
    if n_banks != len(bank_rows) or n_capital != len(capital_rows):
        failures.append("Postgres counts disagree with the artifact")
    # Not "every quarter reconciles" — one genuinely does not, and asserting
    # otherwise would mean either loosening the tolerance until the anomaly
    # vanished or dropping the row. Both hide a real property of the source.
    # What must hold: the anomaly is the exception, it is FLAGGED, and the
    # quarter the capstone divides by is not the anomalous one.
    if n_ratio_drift > 2:
        failures.append(f"{n_ratio_drift} of {n_capital} quarters do not "
                        f"reconcile; that is no longer an anomaly in the "
                        f"source, it is a broken load")
    if not latest_ok:
        failures.append(f"the most recent quarter ({latest_date}) does not "
                        f"reconcile — it is the live denominator, and every "
                        f"utilisation percentage would be wrong")
    if n_legal_entity != 50:
        failures.append(f"legal_entity moved to {n_legal_entity}; the bank "
                        f"must not enter the obligor table")
    if n_bank_nodes < 1 or n_hierarchy < 1:
        failures.append("the Fluree bank node or its hierarchy edge is absent")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  both stores match the artifact; the obligor table is untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
