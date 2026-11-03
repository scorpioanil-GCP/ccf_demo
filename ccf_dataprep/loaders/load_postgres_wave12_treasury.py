#!/usr/bin/env python3
"""Wave 12 Task 7 — load the treasury client tables and intraday ticks.

Six new tables plus one extension, per `task-7-brief.md`:

    treasury_client       synthetic — internal   15 clients (F1: `intent` column)
    investment_position   synthetic — internal   200 positions
    concentration_limit   synthetic — internal   60 limits, keyed (holder_lei,
                                                  counterparty_lei, intent) (F1)
    permitted_instrument  synthetic — internal   45 rows = 15 clients x 3
                                                  instrument kinds (F14 — one
                                                  mandate per client, not 75)
    stale_signal          synthetic — engineered 4 rows, its own table (F5),
                                                  `as_of` is the decision
                                                  reference, never now() (F15)
    intraday_tick         synthetic — engineered 11,700 rows (5 tenors x 30
                                                  trading days x 78 ticks/day)
    deposit_account       synthetic — internal   +100 `W12-` rows, EXTENDING
                                                  the table Wave 9 owns

## The brief's "~75 mandates" is stale — trust the count, not the prose

`task-7-brief.md` Step 2 still says "~75 mandates" from a plan draft written
before ruling F14 (`progress.md`, `task-5-report.md` fix round 1) corrected
`wave12_treasury.json` to one mandate per client. The artifact on disk has
**45** mandate rows (15 clients x 3 instrument kinds, the full permitted
set for every client) and that is what `main()` asserts against — a stale
sentence in a brief does not outrank a recount of the bytes.

## The two-writer table — `deposit_account`

Wave 9's `load_collateral_wave9.py` owns 20 rows, ids `DEP-0001..DEP-0020`.
This loader adds ~100 more, ids `W12-####`. To keep that boundary real:

  - every `account_id` this loader inserts is asserted `W12-` prefixed
    BEFORE the upsert runs, not just by construction;
  - there is no DELETE or TRUNCATE against this table anywhere in this
    file — grep it if in doubt;
  - the upsert's ON CONFLICT target is `account_id` alone, so a rerun only
    ever touches the rows this loader itself wrote;
  - `main()` ends by asserting Wave 9's 20 rows are still present, split
    from Wave 12's, and raises if the wave9 count has moved.

A prior sibling loader in this repo turned exactly this shape (a loader
that believed it owned a key outright) into a silent data-loss hazard.
Deletion, not error, is the failure mode this guards against.

    uv run loaders/load_postgres_wave12_treasury.py --dry-run
    uv run loaders/load_postgres_wave12_treasury.py

Idempotent: every upsert keys on its natural primary key and sets EVERY
non-key column on conflict — no column is left to go stale on reload.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.currency import verify_current

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".treasury_client (
    lei             char(20)    PRIMARY KEY,
    mandate_id      text        NOT NULL,
    intent          text        NOT NULL,   -- RULING F1: limits are keyed by intent
    home_currency   char(3)     NOT NULL,
    reported_cash   numeric,
    cash_fact_asof  date,
    cash_provenance text        NOT NULL,
    provenance      text        NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".investment_position (
    position_id      text        PRIMARY KEY,
    holder_lei       char(20)    NOT NULL,
    counterparty_lei char(20)    NOT NULL,
    instrument_kind  text        NOT NULL,
    instrument_id    text        NOT NULL,
    currency         char(3)     NOT NULL,
    notional         numeric     NOT NULL,
    yield_bp         numeric     NOT NULL,
    maturity_date    date        NOT NULL,
    provenance       text        NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".concentration_limit (
    holder_lei       char(20)    NOT NULL,
    counterparty_lei char(20)    NOT NULL,
    limit_pct        numeric     NOT NULL,
    intent           text        NOT NULL,
    provenance       text        NOT NULL,
    PRIMARY KEY (holder_lei, counterparty_lei, intent)
);

CREATE TABLE IF NOT EXISTS "{S}".permitted_instrument (
    mandate_id      text        NOT NULL,
    instrument_kind text        NOT NULL,
    max_tenor_days  integer     NOT NULL,
    provenance      text        NOT NULL,
    PRIMARY KEY (mandate_id, instrument_kind)
);

-- RULING F5: the stale signal gets its own table rather than being smuggled
-- into `reference_rate`, whose provenance column is `public` on every row. An
-- engineered row wearing a public label is the misrepresentation §C warns of.
CREATE TABLE IF NOT EXISTS "{S}".stale_signal (
    signal_id   text        PRIMARY KEY,
    series_id   text        NOT NULL,
    observed_at timestamptz NOT NULL,
    as_of       timestamptz NOT NULL,   -- RULING F15: the decision reference
    value       numeric     NOT NULL,
    provenance  text        NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".intraday_tick (
    tenor_years  numeric     NOT NULL,
    obs_ts       timestamptz NOT NULL,
    trading_day  date        NOT NULL,
    value_pct    numeric     NOT NULL,
    provenance   text        NOT NULL,
    PRIMARY KEY (tenor_years, obs_ts)
);

-- Defensive only: Wave 9's load_collateral_wave9.py is the actual owner and
-- creator of this table. IF NOT EXISTS makes re-declaring its shape here a
-- no-op when (as expected) the table already exists; it only matters if this
-- loader is ever run before Wave 9's. Column-for-column identical to that
-- loader's DDL — never altered here.
CREATE TABLE IF NOT EXISTS "{S}".deposit_account (
    account_id              TEXT PRIMARY KEY,
    holder_lei              TEXT NOT NULL,
    currency                TEXT NOT NULL,
    balance                 NUMERIC NOT NULL,
    jurisdiction             TEXT NOT NULL,
    setoff_contractual      BOOLEAN NOT NULL,
    setoff_enforceable      BOOLEAN NOT NULL,
    provenance              TEXT NOT NULL
);
"""

CURRENCY_NOTES: list[str] = []


def load(name: str) -> dict:
    """Read one artifact, refusing a STALE one (`ccf/currency.py`)."""
    doc, note = verify_current(name)
    CURRENCY_NOTES.append(note)
    return doc


def build_rows(treasury_doc: dict, ticks_doc: dict):
    clients = treasury_doc["clients"]
    deposits = treasury_doc["deposit_accounts"]
    positions = treasury_doc["positions"]
    limits = treasury_doc["limits"]
    mandates = treasury_doc["mandates"]
    stale = treasury_doc["stale_signal"]
    ticks = ticks_doc["ticks"]

    client_rows = [
        (c["lei"], c["mandate_id"], c["intent"], c["home_currency"],
         c["reported_cash"], c["cash_fact_asof"], c["cash_provenance"],
         c["provenance"])
        for c in clients
    ]

    # Every deposit row this artifact carries must be a NEW (`W12-`) account —
    # this loader never touches Wave 9's `DEP-####` rows. Asserted here,
    # before any SQL runs, not merely assumed from the generator's naming.
    bad_ids = [d["account_id"] for d in deposits
               if not d["account_id"].startswith("W12-")]
    if bad_ids:
        raise RuntimeError(
            f"refusing to load: {len(bad_ids)} deposit row(s) do not carry "
            f"the W12- prefix this loader owns: {bad_ids[:5]}"
        )
    deposit_rows = [
        (d["account_id"], d["holder_lei"], d["currency"], d["balance"],
         d["jurisdiction"], d["setoff_contractual"], d["setoff_enforceable"],
         d["provenance"])
        for d in deposits
    ]

    position_rows = [
        (p["position_id"], p["holder_lei"], p["counterparty_lei"],
         p["instrument_kind"], p["instrument_id"], p["currency"],
         p["notional"], p["yield_bp"], p["maturity_date"], p["provenance"])
        for p in positions
    ]

    limit_rows = [
        (l["holder_lei"], l["counterparty_lei"], l["limit_pct"],
         l["intent"], l["provenance"])
        for l in limits
    ]

    mandate_rows = [
        (m["mandate_id"], m["instrument_kind"], m["max_tenor_days"],
         m["provenance"])
        for m in mandates
    ]

    stale_rows = [
        (s["signal_id"], s["series_id"], s["observed_at"], s["as_of"],
         s["value"], s["provenance"])
        for s in stale
    ]

    tick_rows = [
        (t["tenor_years"], t["obs_ts"], t["trading_day"], t["value_pct"],
         t["provenance"])
        for t in ticks
    ]

    return (client_rows, deposit_rows, position_rows, limit_rows,
            mandate_rows, stale_rows, tick_rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    treasury_doc = load("wave12_treasury.json")
    ticks_doc = load("wave12_ticks.json")

    (client_rows, deposit_rows, position_rows, limit_rows, mandate_rows,
     stale_rows, tick_rows) = build_rows(treasury_doc, ticks_doc)

    tenor_counts = Counter(t[0] for t in tick_rows)

    print(f"Wave 12 Task 7 — load into {S}\n")
    print("  artifact currency:")
    for note in CURRENCY_NOTES:
        print(f"    {note}")
    print()
    print(f"  treasury_client       {len(client_rows):>6}")
    print(f"  investment_position   {len(position_rows):>6}")
    print(f"  concentration_limit   {len(limit_rows):>6}")
    print(f"  permitted_instrument  {len(mandate_rows):>6}  "
          f"(brief's prose says ~75; F14 fixed the artifact to one mandate "
          f"per client — 45 is the correct, counted figure)")
    print(f"  stale_signal          {len(stale_rows):>6}")
    print(f"  intraday_tick         {len(tick_rows):>6}  "
          f"(tenors: {sorted(tenor_counts)})")
    print(f"  deposit_account       {len(deposit_rows):>6}  new W12- rows "
          f"(extends Wave 9's 20 DEP- rows; never deletes them)")

    # Counted expectations, not restated ones (per house rule: "count
    # anything you restate").
    expected = {
        "treasury_client": (len(client_rows), 15),
        "investment_position": (len(position_rows), 200),
        "concentration_limit": (len(limit_rows), 60),
        "permitted_instrument": (len(mandate_rows), 45),
        "stale_signal": (len(stale_rows), 4),
        "intraday_tick": (len(tick_rows), 11_700),
        "deposit_account (new)": (len(deposit_rows), 100),
    }
    mismatches = {k: v for k, v in expected.items() if v[0] != v[1]}
    if mismatches:
        raise RuntimeError(f"row-count mismatch vs. artifact expectation: "
                            f"{mismatches}")

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".treasury_client '
            "(lei, mandate_id, intent, home_currency, reported_cash, "
            " cash_fact_asof, cash_provenance, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei) DO UPDATE SET "
            "mandate_id=EXCLUDED.mandate_id, intent=EXCLUDED.intent, "
            "home_currency=EXCLUDED.home_currency, "
            "reported_cash=EXCLUDED.reported_cash, "
            "cash_fact_asof=EXCLUDED.cash_fact_asof, "
            "cash_provenance=EXCLUDED.cash_provenance, "
            "provenance=EXCLUDED.provenance",
            client_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".investment_position '
            "(position_id, holder_lei, counterparty_lei, instrument_kind, "
            " instrument_id, currency, notional, yield_bp, maturity_date, "
            " provenance) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (position_id) DO UPDATE SET "
            "holder_lei=EXCLUDED.holder_lei, "
            "counterparty_lei=EXCLUDED.counterparty_lei, "
            "instrument_kind=EXCLUDED.instrument_kind, "
            "instrument_id=EXCLUDED.instrument_id, "
            "currency=EXCLUDED.currency, notional=EXCLUDED.notional, "
            "yield_bp=EXCLUDED.yield_bp, "
            "maturity_date=EXCLUDED.maturity_date, "
            "provenance=EXCLUDED.provenance",
            position_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".concentration_limit '
            "(holder_lei, counterparty_lei, limit_pct, intent, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (holder_lei, counterparty_lei, intent) DO UPDATE SET "
            "limit_pct=EXCLUDED.limit_pct, provenance=EXCLUDED.provenance",
            limit_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".permitted_instrument '
            "(mandate_id, instrument_kind, max_tenor_days, provenance) "
            "VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (mandate_id, instrument_kind) DO UPDATE SET "
            "max_tenor_days=EXCLUDED.max_tenor_days, "
            "provenance=EXCLUDED.provenance",
            mandate_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".stale_signal '
            "(signal_id, series_id, observed_at, as_of, value, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (signal_id) DO UPDATE SET "
            "series_id=EXCLUDED.series_id, observed_at=EXCLUDED.observed_at, "
            "as_of=EXCLUDED.as_of, value=EXCLUDED.value, "
            "provenance=EXCLUDED.provenance",
            stale_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".intraday_tick '
            "(tenor_years, obs_ts, trading_day, value_pct, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenor_years, obs_ts) DO UPDATE SET "
            "trading_day=EXCLUDED.trading_day, "
            "value_pct=EXCLUDED.value_pct, provenance=EXCLUDED.provenance",
            tick_rows,
        )

        # deposit_account — the two-writer table. INSERT only, ON CONFLICT
        # keyed on account_id alone. No DELETE, no TRUNCATE, anywhere. This
        # can only ever touch a `W12-` row because deposit_rows was filtered
        # (and asserted) to W12- ids above.
        cur.executemany(
            f'INSERT INTO "{S}".deposit_account '
            "(account_id, holder_lei, currency, balance, jurisdiction, "
            " setoff_contractual, setoff_enforceable, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (account_id) DO UPDATE SET "
            "holder_lei=EXCLUDED.holder_lei, currency=EXCLUDED.currency, "
            "balance=EXCLUDED.balance, jurisdiction=EXCLUDED.jurisdiction, "
            "setoff_contractual=EXCLUDED.setoff_contractual, "
            "setoff_enforceable=EXCLUDED.setoff_enforceable, "
            "provenance=EXCLUDED.provenance",
            deposit_rows,
        )

        conn.commit()

        print()
        for table in ("treasury_client", "investment_position",
                      "concentration_limit", "permitted_instrument",
                      "stale_signal", "intraday_tick"):
            cur.execute(f'SELECT COUNT(*) FROM "{S}".{table}')
            print(f"  {table:24} store count: {cur.fetchone()[0]}")

        # The two-writer survival check. This is the load's most important
        # assertion: if Wave 9's 20 rows have moved, something deleted rows
        # this loader does not own.
        cur.execute(
            f"""SELECT CASE WHEN account_id LIKE 'W12-%%' THEN 'wave12'
                             ELSE 'wave9' END AS bucket, COUNT(*)
                  FROM "{S}".deposit_account GROUP BY 1 ORDER BY 1"""
        )
        split = dict(cur.fetchall())
        print(f"  {'deposit_account (split)':24} store count: {split}")

        wave9_count = split.get("wave9", 0)
        if wave9_count != 20:
            raise RuntimeError(
                f"WAVE 9 SURVIVAL CHECK FAILED: expected 20 wave9 "
                f"deposit_account rows, found {wave9_count}. This loader "
                f"never issues DELETE/TRUNCATE against deposit_account, so "
                f"this indicates rows were removed elsewhere."
            )

    print("\n  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
