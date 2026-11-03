#!/usr/bin/env python3
"""Load the bank-internal ABS overlay into Postgres and Fluree.

    uv run loaders/load_abs_overlay_wave14.py --dry-run
    uv run loaders/load_abs_overlay_wave14.py

Postgres owns the holdings, the materialization policy and the entitlement
grants (`E` and `P` reference). Fluree owns the loan-level privacy
constraints, which §C files under `P` on the Fluree row. Everything this
loader writes is `synthetic — internal` -- the bank's own book, invented
because it is bank-internal by nature.

## ⚠️ Fluree is append-only

The Fluree write happens after the `--dry-run` early return and after the
Postgres write, deliberately last: a wrong triple here cannot be deleted,
only superseded, so everything reversible happens first. Idempotency for the
Fluree side is a `ledger_conflicts` pre-write check (same shape as
`loaders/load_abs_fluree_wave14.py`) rather than reliance on RDF set
semantics alone -- a changed `PRIVACY_RESTRICTED_FIELDS` constant would
otherwise silently accumulate a second, disagreeing value on the same
subject/predicate with nothing marking which supersedes which.

## Task 12 rulings applied

1. **Three `ex:` terms bound before this write, not after** --
   `LoanLevelPrivacyConstraint`, `restrictsField`, `minimumGranularity`.
   Bound in `docs/ccf_dataprep_v2.md` in the same commit as this loader.
   They are application attributes, not FIBO terms, so there was nothing to
   verify against the EDM Council source -- see the doc for the near-neighbour
   found (`ex:ResidencyConstraint` / `ex:subjectToConstraint`, Wave 13b) and
   why it was not reused.
2. **Every `stable_scalar` query carries `FROM <FLUREE_LEDGER_V2>`.** Fluree
   returns HTTP 500, not a helpful 400, without it.
3. **Upserts update every non-key column, not one.** The brief's draft
   updated only `notional` / `posture` / `max_granularity`; a re-run after a
   genuine change (a corrected notional, a widened entitlement) would leave
   every other column stale while the row count stayed the same -- Wave 13b's
   exact defect, this time on write rather than on read.
4. **The loader inserts the three crosswalk rows itself**, idempotently, on
   `(lei)` conflict, and NEVER touches `internal_client_id` in the UPDATE SET
   -- a re-run must not renumber a row that already exists
   (`positional-identity-is-a-defect-class`). The next id is read from
   `MAX(...)` over the existing table, never from a loop index or a JSON
   array position.

## A fifth thing, found while implementing #4: `lei` is blank-padded `CHAR(20)`

The three trusts have no real GLEIF LEI (see docs/ccf_dataprep_v2.md,
"Instance data source" section, the 2026-08-23 note under the 2026-08-16
supersession) and get `SYN-<deal_id>` instead -- 15-16 characters, not 20.
Postgres `CHAR(n)`
right-pads a shorter value to `n` and returns the padding on every read.
SQL equality treats the padding as insignificant, but a Python read-back does
not: `cur.fetchone()` for `'SYN-TAOT-2022-B'` comes back as
`'SYN-TAOT-2022-B     '` (20 chars), which is wrong for a value a downstream
consumer -- or this loader's own idempotency check -- must match exactly.
`crosswalk.lei` and `legal_entity.lei` are widened to `VARCHAR(20)` below,
which keeps the same 20-character ceiling with no padding. Confirmed
non-destructive against a scratch table: real, already-20-character LEIs are
unaffected in content, and re-running the `ALTER COLUMN TYPE` is a no-op.

## Why `legal_entity` rows too, when the brief only asked for `crosswalk`

`validators/conditions.py`'s counterparty-reference-snapshot orphan gate is a
`FULL OUTER JOIN crosswalk ... legal_entity USING (lei)`. A crosswalk row with
no matching `legal_entity` row IS an orphan by that query, so three
crosswalk-only rows for the trusts would turn the "0 orphans" gate red. The
three minimal `legal_entity` rows below (`is_anchor = false`, so the existing
`>= 50 anchor obligors` floor is untouched) are what keeps that join whole --
CLAUDE.md's own definition-of-done #2, "the correlation keys resolve".
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date

from ccf import fluree, views
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)
OVERLAY = REPO_ROOT / "sources" / "absee" / "overlay.json"
PROV = "synthetic — internal"

#: RULING F54: the trust's own legal_entity row is `public`, not `synthetic —
#: internal`. Rule 1 defines `synthetic — internal` as "invented because it is
#: bank-internal by nature" -- a securitization trust's legal identity is not.
#: Its legal name and CIK come straight from EDGAR; the only invented part is
#: the `SYN-` surrogate key, minted because GLEIF holds no registration, and
#: CLAUDE.md's settled decision already provides for real entities carrying a
#: visibly distinct synthetic identifier. The CROSSWALK rows stay `synthetic —
#: internal` and correctly so: `internal_client_id` genuinely is bank-internal.
ENTITY_PROV = "public"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

C_PRIVACY_CONSTRAINT = f"{EX}LoanLevelPrivacyConstraint"
P_RESTRICTS_FIELD = f"{EX}restrictsField"
P_MIN_GRANULARITY = f"{EX}minimumGranularity"
P_PROVENANCE = f"{EX}provenance"          # bound since Wave 11c -- reused, not new

TRUST_SOURCE = (
    "no GLEIF LEI record for this deal trust: absent from the prospectus, the "
    "ABS-EE file and the servicer report, and no exact-legal-name match in "
    "GLEIF; a GLEIF fulltext search finds Santander/Toyota trust "
    "registrations only for 2013-2017 vintages, none for 2022 or 2024 -- "
    "per-trust LEI registration appears to have lapsed. Verified against "
    "api.gleif.org 2026-08-23."
)

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_holding (
    holding_id text PRIMARY KEY,
    deal_id    text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    tranche_id text NOT NULL REFERENCES "{S}".abs_tranche(tranche_id),
    position_type text NOT NULL,
    notional numeric NOT NULL,
    is_risk_retention boolean NOT NULL,
    provenance text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_materialization_policy (
    granularity text PRIMARY KEY,
    posture     text NOT NULL,          -- materialized | on-demand
    refresh_days integer NOT NULL,
    note        text NOT NULL,
    provenance  text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_granularity_entitlement (
    principal text PRIMARY KEY,
    max_granularity text NOT NULL,      -- deal | tranche | cohort | loan
    rationale text NOT NULL,
    provenance text NOT NULL
);

-- First non-LEI identifier to land in these columns. CHAR(20) blank-pads a
-- shorter value and returns the padding on read; VARCHAR(20) keeps the same
-- ceiling with none. Idempotent to re-run: real 20-character LEIs carry no
-- padding either way, so their stored value is unchanged.
--
-- `v_entity_jurisdiction` (ccf/views.py) reads legal_entity.lei, and Postgres
-- refuses ALTER COLUMN TYPE on a column a view depends on. Dropped here and
-- rebuilt by `ccf.views.ensure_views` right after, in the same transaction,
-- so nothing is ever a query away from a missing view.
DROP VIEW IF EXISTS "{S}".v_ownership_cross_border;
DROP VIEW IF EXISTS "{S}".v_entity_jurisdiction;
ALTER TABLE "{S}".crosswalk ALTER COLUMN lei TYPE VARCHAR(20);
ALTER TABLE "{S}".legal_entity ALTER COLUMN lei TYPE VARCHAR(20);
"""

#: Granularity ordering, coarse to fine. The ceiling is a MIN over this.
#: Imported by Task 13's gate -- keep this name and `effective_granularity`'s
#: signature stable.
ORDER = {"deal": 0, "tranche": 1, "cohort": 2, "loan": 3}


def effective_granularity(requested: str, principal_max: str) -> str:
    """The lower of what was asked for and what the principal may have."""
    return requested if ORDER[requested] <= ORDER[principal_max] else principal_max


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def constraint_uri(field: str) -> str:
    return f"{EX}abs-privacy-constraint-{field.replace('_', '-')}"


def build_triples(fields: list[str]) -> list[tuple[str, str, str, bool]]:
    """One `LoanLevelPrivacyConstraint` node per restricted field.

    `(subject, predicate, object, literal?)`, kept structured rather than
    rendered, so the conflict check can compare incoming objects against what
    the ledger already holds without re-parsing N-Triples.
    """
    triples: list[tuple[str, str, str, bool]] = []
    for field in fields:
        c_uri = constraint_uri(field)
        triples.append((c_uri, RDF_TYPE, C_PRIVACY_CONSTRAINT, False))
        triples.append((c_uri, P_RESTRICTS_FIELD, field, True))
        triples.append((c_uri, P_MIN_GRANULARITY, "cohort", True))
        triples.append((c_uri, P_PROVENANCE, PROV, True))
    return triples


def render(stmt: tuple[str, str, str, bool]) -> str:
    s, p, o, literal = stmt
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def ledger_conflicts(triples: list[tuple[str, str, str, bool]]) -> list[str]:
    """Refuse to write when the ledger already holds a DIFFERENT value.

    Same shape as `loaders/load_abs_fluree_wave14.py`'s guard: RDF set
    semantics make an identical re-run a no-op for free, but say nothing
    about a *changed* source value -- if `PRIVACY_RESTRICTED_FIELDS` or
    `minimumGranularity`'s constant ever changed, a plain re-run would INSERT
    a second, disagreeing triple on the same (subject, predicate) with
    nothing marking which supersedes which. Fluree has no
    upsert-by-subject-predicate.
    """
    by_pred: dict[str, dict[str, set[tuple[bool, str]]]] = defaultdict(
        lambda: defaultdict(set))
    for s, p, o, literal in triples:
        by_pred[p][s].add((literal, o))

    conflicts: list[str] = []
    for pred, incoming in by_pred.items():
        values = " ".join(f"<{s}>" for s in sorted(incoming))
        rows = fluree.query(
            f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> "
            f"WHERE {{ VALUES ?s {{ {values} }} ?s <{pred}> ?o }}"
        )["results"]["bindings"]
        for b in rows:
            subj = b["s"]["value"]
            held = (b["o"]["type"] != "uri", b["o"]["value"])
            if held not in incoming[subj]:
                kind = "literal" if held[0] else "uri"
                want = ", ".join(sorted(o for _, o in incoming[subj])) or "(none)"
                conflicts.append(
                    f"{subj}\n      predicate {pred}\n"
                    f"      ledger holds ({kind}): {held[1]!r}\n"
                    f"      this run asserts:     {want}")
    return conflicts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ov = json.loads(OVERLAY.read_text())

    holdings = [(f"{h['deal_id']}-{h['class_name']}-{h['position_type']}",
                 h["deal_id"], h["tranche_id"], h["position_type"],
                 h["notional"], h["is_risk_retention"], PROV)
                for h in ov["holdings"]]
    materialization = [(m["granularity"], m["posture"], m["refresh_days"],
                        m["note"], PROV) for m in ov["materialization"]]
    entitlements = [(e["principal"], e["max_granularity"], e["rationale"], PROV)
                     for e in ov["entitlements"]]
    fields = ov["privacy_restricted_fields"]
    triples = build_triples(fields)
    lines = [render(t) for t in triples]

    print(f"  {len(holdings)} holdings, {len(materialization)} policy rows, "
          f"{len(entitlements)} entitlements")
    print(f"  {len(triples)} Fluree triples across {len(fields)} privacy "
          f"constraints ({len(fields)} nodes)")

    # The restricted principal must actually bite -- pure function, needs no
    # store, so this prints in a dry run too.
    print("\n  restricted-principal check (request=loan against each ceiling):")
    for principal, max_g, _rationale, _prov in entitlements:
        got = effective_granularity("loan", max_g)
        flag = "  <-- LOWERED" if got != "loan" else ""
        print(f"    {principal:24s} ceiling={max_g:8s} -> {got}{flag}")

    if args.dry_run:
        print("\n  DRY RUN -- nothing written. Fluree triples:")
        for line in lines:
            print(f"    {line}")
        try:
            conflicts = ledger_conflicts(triples)
            if conflicts:
                print(f"\n  NOTE: {len(conflicts)} conflict(s) would block a "
                      "real run:")
                for c in conflicts:
                    print(f"    - {c}")
        except Exception as exc:  # noqa: BLE001 -- dry run must not need Fluree up
            print(f"\n  WARNING: conflict check skipped, ledger unreachable: {exc}")
        return 0

    # Read-only, and runs BEFORE any write to either store. Fluree is
    # append-only, so a real run must not write Postgres and then discover a
    # Fluree conflict -- check first, fail closed.
    conflicts = ledger_conflicts(triples)
    if conflicts:
        print(f"\n  REFUSING TO WRITE -- {len(conflicts)} conflict(s). The "
              "ledger already holds a different value for:")
        for c in conflicts:
            print(f"    - {c}")
        print("\n  Nothing was written. Resolve by hand -- superseding is a "
              "deliberate act, not a side effect of re-running a loader.")
        return 1

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        rebuilt = views.ensure_views(cur, S)
        print(f"  views rebuilt after widening lei: {rebuilt}")

        cur.executemany(
            f'INSERT INTO "{S}".abs_holding VALUES (%s,%s,%s,%s,%s,%s,%s) '
            "ON CONFLICT (holding_id) DO UPDATE SET "
            "deal_id = EXCLUDED.deal_id, "
            "tranche_id = EXCLUDED.tranche_id, "
            "position_type = EXCLUDED.position_type, "
            "notional = EXCLUDED.notional, "
            "is_risk_retention = EXCLUDED.is_risk_retention, "
            "provenance = EXCLUDED.provenance",
            holdings)
        cur.executemany(
            f'INSERT INTO "{S}".abs_materialization_policy VALUES (%s,%s,%s,%s,%s) '
            "ON CONFLICT (granularity) DO UPDATE SET "
            "posture = EXCLUDED.posture, "
            "refresh_days = EXCLUDED.refresh_days, "
            "note = EXCLUDED.note, "
            "provenance = EXCLUDED.provenance",
            materialization)
        cur.executemany(
            f'INSERT INTO "{S}".abs_granularity_entitlement VALUES (%s,%s,%s,%s) '
            "ON CONFLICT (principal) DO UPDATE SET "
            "max_granularity = EXCLUDED.max_granularity, "
            "rationale = EXCLUDED.rationale, "
            "provenance = EXCLUDED.provenance",
            entitlements)

        # The three trusts, from abs_deal (their own real, already-loaded
        # CIK/name) -- never a positional id.
        cur.execute(f'SELECT deal_id, cik, legal_name FROM "{S}".abs_deal '
                    "ORDER BY deal_id")
        trusts = cur.fetchall()

        cur.execute(f'SELECT lei, internal_client_id FROM "{S}".crosswalk')
        lei_to_id = {lei: cid for lei, cid in cur.fetchall()}
        next_seq = 1 + max(
            (int(cid.split("-")[1]) for cid in lei_to_id.values()), default=0)

        today = date.today().isoformat()
        crosswalk_rows = []
        entity_rows = []
        for deal_id, cik, legal_name in trusts:
            syn_lei = f"SYN-{deal_id}"
            if syn_lei in lei_to_id:
                internal_id = lei_to_id[syn_lei]   # NEVER renumber an existing row
            else:
                internal_id = f"CLI-{next_seq:06d}"
                next_seq += 1
            crosswalk_rows.append(
                (internal_id, syn_lei, int(cik), None, PROV, TRUST_SOURCE))
            entity_rows.append((
                syn_lei, legal_name, None, None, None, None, None, None,
                "trust",   # public: every trust's own legal name says so
                None, None, None, None, None, None,
                False, None, None, ENTITY_PROV, TRUST_SOURCE, today,
            ))

        print(f"\n  crosswalk: {len(crosswalk_rows)} trust rows "
              f"({', '.join(r[0] + '<->' + r[1] for r in crosswalk_rows)})")

        cur.executemany(
            f'INSERT INTO "{S}".crosswalk '
            "(internal_client_id, lei, cik, ticker, provenance, source) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei) DO UPDATE SET "
            "cik = EXCLUDED.cik, "
            "ticker = EXCLUDED.ticker, "
            "provenance = EXCLUDED.provenance, "
            "source = EXCLUDED.source",
            # internal_client_id is deliberately absent from DO UPDATE SET.
            crosswalk_rows)
        cur.executemany(
            f'INSERT INTO "{S}".legal_entity '
            "(lei, legal_name, gleif_legal_name, legal_jurisdiction, entity_status, "
            " registration_status, next_renewal_date, initial_registration, legal_form, "
            " legal_address_country, legal_address_city, legal_address_region, "
            " sic, sic_description, "
            " fiscal_year_end, is_anchor, lei_match_band, lei_match_score, "
            " provenance, source, retrieved_at) "
            "VALUES (" + ",".join(["%s"] * 21) + ") "
            "ON CONFLICT (lei) DO UPDATE SET "
            "legal_name = EXCLUDED.legal_name, "
            "gleif_legal_name = EXCLUDED.gleif_legal_name, "
            "legal_jurisdiction = EXCLUDED.legal_jurisdiction, "
            "entity_status = EXCLUDED.entity_status, "
            "registration_status = EXCLUDED.registration_status, "
            "next_renewal_date = EXCLUDED.next_renewal_date, "
            "initial_registration = EXCLUDED.initial_registration, "
            "legal_form = EXCLUDED.legal_form, "
            "legal_address_country = EXCLUDED.legal_address_country, "
            "legal_address_city = EXCLUDED.legal_address_city, "
            "legal_address_region = EXCLUDED.legal_address_region, "
            "sic = EXCLUDED.sic, "
            "sic_description = EXCLUDED.sic_description, "
            "fiscal_year_end = EXCLUDED.fiscal_year_end, "
            "is_anchor = EXCLUDED.is_anchor, "
            "lei_match_band = EXCLUDED.lei_match_band, "
            "lei_match_score = EXCLUDED.lei_match_score, "
            "provenance = EXCLUDED.provenance, "
            "source = EXCLUDED.source, "
            "retrieved_at = EXCLUDED.retrieved_at",
            entity_rows)

        conn.commit()

        cur.execute(f"""
            SELECT -COUNT(*) FROM "{S}".crosswalk c
            FULL OUTER JOIN "{S}".legal_entity e USING (lei)
            WHERE c.lei IS NULL OR e.lei IS NULL""")
        orphans = -cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".crosswalk')
        n_cross = cur.fetchone()[0]
        print(f"  crosswalk rows total: {n_cross}  "
              f"orphans against legal_entity (want 0): {orphans}")
        if orphans:
            print("  FAIL: crosswalk and legal_entity do not fully join")
            return 1

    # Fluree last -- append-only, so everything reversible happens first.
    fluree.update("INSERT DATA { " + " ".join(lines) + " }")

    # stable_scalar, not a bare query: a read immediately after INSERT DATA
    # can return 0 while the index catches up. Every statement carries an
    # explicit FROM -- Fluree 500s without it.
    n = fluree.stable_scalar(
        f"SELECT (COUNT(?c) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?c a <{C_PRIVACY_CONSTRAINT}> }}")
    print(f"  privacy constraints in ledger: {n} (expected {len(fields)})")
    if n != len(fields):
        print("  FAIL: ledger disagrees with the generated triple set.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
