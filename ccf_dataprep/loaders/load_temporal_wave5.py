#!/usr/bin/env python3
"""Wave 5 — load the bitemporal covenant layer.

Split per `covenant-in-force-as-of` §C, which is explicit about who owns what:

    Fluree    covenant structure, definition edges, amendment events with
              effective AND booked dates, policy version history, breach events
    Postgres  drawdown events, breach-threshold policy values, compliance
              statements

Bitemporality is represented as explicit attributes rather than left implicit
in the ledger:

    ex:validFrom / ex:validTo   VALID time      -> answers `as_of`
    ex:assertedAt               ASSERTION time  -> answers `known_as_of`

The ledger's own `t` is a third, stronger thing — an exact replay anchor for
`graph_snapshot_at`, reproducible by construction rather than by best-effort
timestamp query. Both are wanted: the attributes make the two axes queryable,
the ledger makes the reconstruction exact.

**FIBO has no Covenant class.** An exhaustive search of all 295 modules returns
only `BreachOfCovenant`. So `ex:Covenant`, `ex:CovenantDefinition`,
`ex:covenantOf`, `ex:definedBy` and `ex:measuredBy` are application extensions
and are labelled as such — a consumer told these were FIBO terms would query a
conformant store and get nothing. The breach event itself DOES have a real
binding and uses it.

    uv run loaders/load_temporal_wave5.py --dry-run
    uv run loaders/load_temporal_wave5.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf import fluree
from ccf.config import (EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2,
                        REPO_ROOT, assert_v2_schema, pg_connect)

SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

# Real FIBO bindings, verified against the EDM Council source in Wave 0.
C_CREDIT_FACILITY = f"{FIBO}FBC/DebtAndEquities/Debt/CreditFacility"
C_BREACH_OF_COVENANT = f"{FIBO}FND/Agreements/Contracts/BreachOfCovenant"
P_HAS_BORROWER = f"{FIBO}FBC/DebtAndEquities/Debt/hasBorrower"

# ex: extensions — NOT FIBO terms. FIBO has no Covenant class.
C_COVENANT = f"{EX}Covenant"
C_COVENANT_DEFINITION = f"{EX}CovenantDefinition"
C_AMENDMENT = f"{EX}Amendment"
C_POLICY_VERSION = f"{EX}PolicyVersion"
#: Bound in the contract since Wave 5 and carrying a schemaNote in the
#: ledger, but never declared by this loader — so its T-Box was orphan
#: residue. Declared here 2026-08-21; it has no instances by design.
C_MEASUREMENT_PERIOD = f"{EX}MeasurementPeriod"

#: Why an amendment's effective date is what it is. The amendment COUNT is
#: public (8-K Item 1.01 filings are counted); the individual amendment
#: DATES are not disclosed, so they are stepped forward from the facility
#: date. Asserted as a literal, so this string must stay byte-stable.
AMENDMENT_DATE_NOTE = (
    "derived by stepping forward from the facility public effective date; "
    "NOT the 8-K Item 1.01 filing date. Amendment COUNT is public; "
    "amendment DATES are not."
)
P_COVENANT_OF = f"{EX}covenantOf"
P_MEASURED_BY = f"{EX}measuredBy"
P_AMENDS = f"{EX}amends"
P_SUPERSEDED_BY = f"{EX}supersededBy"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

BATCH = 400

PG_DDL = f"""
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".drawdown (
    drawdown_id      TEXT PRIMARY KEY,
    facility_id      TEXT NOT NULL REFERENCES "{PG_SCHEMA_V2}".facility(facility_id),
    drawdown_date    DATE NOT NULL,
    amount           NUMERIC NOT NULL,
    currency         CHAR(3) NOT NULL DEFAULT 'USD',
    falls_in_booking_gap BOOLEAN NOT NULL DEFAULT false,
    amendment_number INTEGER,
    provenance       TEXT NOT NULL,
    note             TEXT,
    retrieved_at     DATE NOT NULL
);
COMMENT ON COLUMN "{PG_SCHEMA_V2}".drawdown.falls_in_booking_gap IS
  'True where this drawdown occurred after an amendment took effect but before '
  'the bank booked it. On that date the bank was operating in good faith '
  'against the OLD terms -- which is the only way as_of and known_as_of can be '
  'shown to diverge. Engineered deliberately; assertion time has no public source.';

CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".covenant_policy (
    policy_version   TEXT PRIMARY KEY,
    effective_from   DATE NOT NULL,
    effective_to     DATE,
    leverage_breach_buffer NUMERIC,
    cure_period_days INTEGER,
    provenance       TEXT NOT NULL,
    note             TEXT
);
COMMENT ON TABLE "{PG_SCHEMA_V2}".covenant_policy IS
  'Policy VALUES live here; Fluree holds the policy-version BINDING and its '
  'temporal validity -- the Control/Data plane split from §7.8. Evaluating a '
  '2025 covenant against a 2026 policy produces an anachronism that reads as '
  'a finding, which is why the recipe loads policy as at as_of.';

CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".covenant_breach (
    facility_id      TEXT NOT NULL REFERENCES "{PG_SCHEMA_V2}".facility(facility_id),
    covenant_type    TEXT NOT NULL,
    breach_date      DATE NOT NULL,
    observed_value   NUMERIC,
    threshold_at_breach NUMERIC,
    cured_date       DATE,
    compliant_today  BOOLEAN NOT NULL DEFAULT true,
    provenance       TEXT NOT NULL,
    note             TEXT,
    PRIMARY KEY (facility_id, covenant_type, breach_date)
);

CREATE INDEX IF NOT EXISTS idx_drawdown_facility
    ON "{PG_SCHEMA_V2}".drawdown (facility_id, drawdown_date);
CREATE INDEX IF NOT EXISTS idx_drawdown_gap
    ON "{PG_SCHEMA_V2}".drawdown (falls_in_booking_gap)
    WHERE falls_in_booking_gap;
"""


def esc(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def t(s: str, p: str, o: str, *, lit: bool = False) -> str:
    obj = f'"{esc(o)}"' if lit else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."



def _entity_uri_by_lei() -> dict[str, str]:
    """Resolve LEI -> the Fluree entity node Wave 3 actually created.

    Facilities must attach to a REAL entity. Looking this up rather than
    constructing a URI is the whole point: a constructed one cannot be wrong
    loudly, it just points at nothing.
    """
    from ccf.config import FLUREE_LEDGER_V2
    query = f"SELECT ?s ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}lei> ?l }}"
    out: dict[str, str] = {}
    for b in fluree.query(query)["results"]["bindings"]:
        out.setdefault(b["l"]["value"], b["s"]["value"])
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    assert_v2_schema(PG_SCHEMA_V2)
    layer = json.loads((SCREEN / "temporal_layer.json").read_text())
    today = date.today().isoformat()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT facility_id, borrower_lei FROM "{PG_SCHEMA_V2}".facility')
        borrower = dict(cur.fetchall())

    triples: list[str] = []

    # T-Box for the ex: extensions, declared so they are discoverable and
    # unmistakably not FIBO.
    for cls, label in [
        (C_COVENANT, "Covenant (ex: extension — FIBO has no Covenant class)"),
        (C_COVENANT_DEFINITION, "CovenantDefinition (ex: extension)"),
        (C_AMENDMENT, "Amendment (ex: extension)"),
        (C_POLICY_VERSION, "PolicyVersion (ex: extension)"),
        (C_MEASUREMENT_PERIOD, "MeasurementPeriod (ex: extension)"),
    ]:
        triples.append(t(cls, RDF_TYPE, OWL_CLASS))
        triples.append(t(cls, RDFS_LABEL, label, lit=True))
        triples.append(t(cls, f"{EX}isFiboTerm", "false", lit=True))
        # Says WHY the term is not FIBO, to a consumer holding only the graph.
        # Restored 2026-08-21: asserted in the ledger, written by nothing.
        triples.append(t(cls, f"{EX}schemaNote",
                         EX_EXTENSION_SCHEMA_NOTE, lit=True))

    # --- facilities as typed nodes (lei + label only; attrs are Postgres') ---
    #
    # Wave 9 correction. This previously pointed hasBorrower at `ex:lei/{lei}`,
    # a URI convention that exists nowhere else: Wave 3 entities are
    # `ex:{LocalName}` and the documented instance pattern is
    # `http://example.org/fibo/{LocalName}`. So every facility pointed at a node
    # with ZERO triples on it — 15 phantom borrowers, dangling since Wave 5.
    #
    # Nothing caught it because nothing checked that an edge's object resolves.
    # The triples were syntactically fine and the counts looked right; the
    # traversal simply arrived nowhere. `validators/partition.py` now asserts
    # that every hasBorrower object is a typed entity.
    entity_uri = _entity_uri_by_lei()
    dangling = 0
    for fid, lei in borrower.items():
        s = f"{EX}{fid}"
        triples.append(t(s, RDF_TYPE, C_CREDIT_FACILITY))
        triples.append(t(s, RDFS_LABEL, fid, lit=True))
        obligor = entity_uri.get(lei)
        if obligor:
            triples.append(t(s, P_HAS_BORROWER, obligor))
        else:
            dangling += 1
    if dangling:
        print(f"  WARNING: {dangling} facilities have no entity node to point at")

    # --- covenants, with valid time -----------------------------------------
    for i, c in enumerate(layer["covenants"]):
        cid = f"{EX}COV-{c['facility_id'][4:]}-{c['covenant_type'][:6].upper()}-{i}"
        triples += [
            t(cid, RDF_TYPE, C_COVENANT),
            t(cid, RDFS_LABEL, f"{c['covenant_type']} {c['facility_id']}", lit=True),
            t(cid, P_COVENANT_OF, f"{EX}{c['facility_id']}"),
            t(cid, f"{EX}covenantType", c["covenant_type"], lit=True),
            t(cid, f"{EX}direction", c["direction"], lit=True),
            t(cid, f"{EX}threshold", str(c["threshold"]), lit=True),
            t(cid, f"{EX}unit", c["unit"], lit=True),
            t(cid, f"{EX}testFrequency", c["test_frequency"], lit=True),
            # VALID time — answers as_of
            t(cid, f"{EX}validFrom", c["effective_from"], lit=True),
            t(cid, f"{EX}provenance", c["provenance"], lit=True),
        ]
        if c.get("source_accession"):
            triples.append(t(cid, f"{EX}sourceAccession",
                             c["source_accession"], lit=True))
            triples.append(t(cid, f"{EX}sourceOffset",
                             str(c.get("source_offset", "")), lit=True))

    # --- amendments: the bitemporal core ------------------------------------
    for i, a in enumerate(layer["amendments"]):
        aid = f"{EX}AMD-{a['facility_id'][4:]}-{a['amendment_number']}"
        triples += [
            t(aid, RDF_TYPE, C_AMENDMENT),
            t(aid, RDFS_LABEL,
              f"Amendment {a['amendment_number']} to {a['facility_id']}", lit=True),
            t(aid, P_AMENDS, f"{EX}{a['facility_id']}"),
            t(aid, f"{EX}amendmentNumber", str(a["amendment_number"]), lit=True),
            # VALID time: when the amendment took effect
            t(aid, f"{EX}validFrom", a["effective_date"], lit=True),
            # ASSERTION time: when the bank recorded it. This is the axis a
            # single-timeline store cannot answer at all.
            t(aid, f"{EX}assertedAt", a["booked_date"], lit=True),
            t(aid, f"{EX}bookingLagDays", str(a["booking_lag_days"]), lit=True),
            t(aid, f"{EX}effectiveDateProvenance",
              a["effective_date_provenance"], lit=True),
            # Names the DERIVATION, which the provenance class alone does not:
            # "synthetic — engineered" says the date was invented, not how or
            # why. Restored 2026-08-21 (25 assertions in the ledger, no
            # writer) — see validators/orphan_terms.py.
            t(aid, f"{EX}effectiveDateNote", AMENDMENT_DATE_NOTE, lit=True),
            t(aid, f"{EX}bookingDateProvenance",
              a["booking_date_provenance"], lit=True),
        ]
        if a["is_engineered_lag"]:
            triples.append(t(aid, f"{EX}isEngineeredBookingLag", "true", lit=True))
            triples.append(t(aid, f"{EX}provenance",
                             "synthetic — engineered", lit=True))

    # --- policy versions, with their own validity --------------------------
    for p in layer["policy_versions"]:
        pid = f"{EX}{p['policy_version']}"
        triples += [
            t(pid, RDF_TYPE, C_POLICY_VERSION),
            t(pid, RDFS_LABEL, p["policy_version"], lit=True),
            t(pid, f"{EX}validFrom", p["effective_from"], lit=True),
            t(pid, f"{EX}provenance", p["provenance"], lit=True),
        ]
        if p["effective_to"]:
            triples.append(t(pid, f"{EX}validTo", p["effective_to"], lit=True))

    # --- breach events: a real FIBO binding exists, so use it --------------
    for i, b in enumerate(layer["breach_events"]):
        bid = f"{EX}BREACH-{b['facility_id'][4:]}-{i}"
        triples += [
            t(bid, RDF_TYPE, C_BREACH_OF_COVENANT),
            t(bid, RDFS_LABEL,
              f"{b['covenant_type']} breach {b['breach_date']}", lit=True),
            t(bid, P_COVENANT_OF, f"{EX}{b['facility_id']}"),
            t(bid, f"{EX}validFrom", b["breach_date"], lit=True),
            t(bid, f"{EX}validTo", b["cured_date"], lit=True),
            t(bid, f"{EX}observedValue", str(b["observed_value"]), lit=True),
            t(bid, f"{EX}compliantToday", "true", lit=True),
            t(bid, f"{EX}provenance", b["provenance"], lit=True),
        ]

    print(f"Wave 5 — temporal layer\n")
    print(f"  Fluree triples      {len(triples):>6}")
    print(f"  Postgres drawdowns  {len(layer['drawdowns']):>6}")
    print(f"  policy versions     {len(layer['policy_versions']):>6}")
    print(f"  breach events       {len(layer['breach_events']):>6}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    # --- Postgres ----------------------------------------------------------
    draw_rows = [
        (f"DRW-{d['facility_id'][4:]}-{i:04d}", d["facility_id"],
         d["drawdown_date"], d["amount"], "USD",
         d["falls_in_booking_gap"], d.get("amendment_number"),
         d["provenance"], d.get("note"), today)
        for i, d in enumerate(layer["drawdowns"])
    ]
    policy_rows = [
        (p["policy_version"], p["effective_from"], p["effective_to"],
         p["leverage_breach_buffer"], p["cure_period_days"],
         p["provenance"], p.get("note"))
        for p in layer["policy_versions"]
    ]
    breach_rows = [
        (b["facility_id"], b["covenant_type"], b["breach_date"],
         b["observed_value"], b["threshold_at_breach"], b["cured_date"],
         b["compliant_today"], b["provenance"], b.get("note"))
        for b in layer["breach_events"]
    ]

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(PG_DDL)
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".drawdown '
            "(drawdown_id, facility_id, drawdown_date, amount, currency, "
            " falls_in_booking_gap, amendment_number, provenance, note, "
            " retrieved_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (drawdown_id) DO UPDATE SET amount=EXCLUDED.amount",
            draw_rows,
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".covenant_policy '
            "(policy_version, effective_from, effective_to, "
            " leverage_breach_buffer, cure_period_days, provenance, note) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (policy_version) DO UPDATE SET "
            "effective_to=EXCLUDED.effective_to",
            policy_rows,
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".covenant_breach '
            "(facility_id, covenant_type, breach_date, observed_value, "
            " threshold_at_breach, cured_date, compliant_today, provenance, note) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (facility_id, covenant_type, breach_date) "
            "DO UPDATE SET cured_date=EXCLUDED.cured_date",
            breach_rows,
        )
        conn.commit()
        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".drawdown')
        n_draw = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".drawdown '
                    "WHERE falls_in_booking_gap")
        n_gap = cur.fetchone()[0]

    print(f"\n  Postgres: {n_draw} drawdowns, {n_gap} inside a booking gap")

    # --- Fluree ------------------------------------------------------------
    print(f"  Fluree: writing {len(triples)} triples in batches of {BATCH}...")
    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"    ledger t={fluree.ledger_t()}, "
          f"{fluree.count_triples():,} triples in current state")
    return 0


if __name__ == "__main__":
    sys.exit(main())
