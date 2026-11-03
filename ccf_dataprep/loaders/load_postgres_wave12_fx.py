#!/usr/bin/env python3
"""Wave 12 Task 14 — load FX trades, system records, breaks, and thresholds
into Postgres, per `task-14-brief.md`.

Seven tables, all `ccf_v2`. Per spec §C (`fx-post-trade-reconciliation`),
three classes, not two (CLAUDE.md rule 1) — fix round 2 corrected a blanket
`synthetic — engineered` label that had collapsed `fx_trade`,
`system_trade_record`, and `materiality_threshold` into the wrong class (see
`generators/generate_fx_trades.py`'s `PROVENANCE_INTERNAL` /
`PROVENANCE_ENGINEERED`):

    fx_trade              synthetic — internal     500 trades, 6 pairs —
                                                    "internal trade records
                                                    per system" (§C)
    system_trade_record   synthetic — internal     1,815 per-system, per-
                                                    amendment records (§C)
    fx_intraday_tick      synthetic — engineered   10,368 ticks (6 pairs x
                                                    36 sessions x 288 ticks —
                                                    RULING F3: anchored to
                                                    real H.10 closes, only the
                                                    within-day path engineered)
    break_record          synthetic — engineered   60 breaks — RULING F22,
                                                    see below; genuinely
                                                    engineered per §C
                                                    ("timing-artefact breaks",
                                                    "genuine breaks")
    materiality_threshold synthetic — internal     3 rows, ops policy — bank-
                                                    internal by nature, NOT
                                                    tuned toward the break mix
    fx_pip_size           public                   6 rows, market convention
                                                    (RULING F13)
    part43_profile        public                   44 rows — real DTCC Part
                                                    43 counts, 4 dimensions

## What is deliberately NOT loaded into Postgres here

`wave12_fx.json` also carries `amendments` (105 records) and `clock_offsets`
(3 records). Neither gets a Postgres table — the DDL in `task-14-brief.md`
declares none for them, and that is not an oversight: amendment events and
clock offsets are graph/temporal objects with no numeric "current value" for
Postgres to own, the same shape as Wave 5's amendment nodes (`ex:Amendment`,
`validFrom`/`assertedAt`) which likewise have no Postgres-side row. Both load
into Fluree only, via `load_fluree_wave12_fx.py`.

## RULING F22 — `break_record` carries seven columns and nothing else

The generator's `breaks` array records its own working values — `gap_s`,
`true_a`, `true_b`, `aligned_a`, `aligned_b`, `aligned_diff_pips`,
`timing_component_pips`, `classification_raw`, `classification_aligned`,
`observed_a`, `observed_b`, `local_drift_per_s`, `booking_error_pips`, `note`
— several of which are perfect discriminators between the two break classes:
`gap_s` is exactly `0.0` for every genuine break and positive for every
timing break; `aligned_diff_pips` and `timing_component_pips` encode the
post-alignment answer directly. None of that reaches this table. `build_rows`
below reads exactly six fields off each break record — `break_id`, `trade_id`,
`system_a`, `system_b`, `raw_diff_pips` (-> `raw_variance`, the PRE-alignment
variance a consumer actually observes), `break_type` (-> `designed_class`) —
plus `provenance`. Nothing else from the break dict is ever touched.

`designed_class` (sourced from the artifact's `break_type` field) is the
**deliberate exception** — it is the answer key: present so a validator can
report disagreement between what was designed and what recomputation from
`raw_variance` / the aligned Postgres+Fluree data finds. **No reconciliation
path in this repository may consult `designed_class` to classify a break.**
Task 15's gate reads it only to count disagreements.

`main()` ends by recomputing, per column, whether that column alone
partitions the 60 loaded breaks exactly along `break_type` — the same check
`task-14-brief.md` asks for, run against the STORED rows, not the artifact,
so it catches a mistake in this loader too. `break_id` and `trade_id` trivially
"partition" because every break has a unique id (a singleton group is always
pure) — that is an unavoidable property of being an identifier, not a leak
that would let a consumer classify an unseen break, and is reported as
expected-and-benign. `designed_class` partitioning is the one expected,
by-construction result. Any OTHER column partitioning purely (a repeated
value whose rows are all one class) raises, because RULING F22 was violated.

    uv run loaders/load_postgres_wave12_fx.py --dry-run
    uv run loaders/load_postgres_wave12_fx.py

Idempotent: every upsert keys on its natural primary key and sets EVERY
non-key column on conflict.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from decimal import Decimal

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.currency import verify_current

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".fx_trade (
    trade_id         text        PRIMARY KEY,
    pair             text        NOT NULL,
    notional_band    text        NOT NULL,
    execution_ts     timestamptz NOT NULL,
    value_date       date        NOT NULL,
    counterparty_lei char(20)    NOT NULL,
    provenance       text        NOT NULL
);

-- RULING F23: NO `observed_at` HERE. The spec's §C assigns "System observation
-- timestamps and clock offsets" to Fluree, and "Internal trade records per
-- system" to Postgres. Postgres owns the VALUE; Fluree owns WHEN it was
-- observed (as `ex:systemObservedAt`). Carrying the timestamp in both stores
-- is a single-writer violation, and it is the one attribute this product is
-- actually about — Task 15 reads observations from Fluree and values from
-- Postgres precisely so the reconciliation is a real cross-store assembly.
-- Fix round 1: this column previously existed and was dropped below.
CREATE TABLE IF NOT EXISTS "{S}".system_trade_record (
    trade_id    text        NOT NULL,
    system_name text        NOT NULL,
    value_rate  numeric     NOT NULL,
    amendment_seq integer   NOT NULL DEFAULT 0,
    provenance  text        NOT NULL,
    PRIMARY KEY (trade_id, system_name, amendment_seq)
);

-- Migration for a table this loader already created in fix round 0, when
-- `observed_at` was still a column: `CREATE TABLE IF NOT EXISTS` above is a
-- no-op against an existing table, so the drop has to be explicit and
-- separate. Safe to re-run — IF EXISTS makes it a no-op once the column is
-- already gone.
ALTER TABLE "{S}".system_trade_record DROP COLUMN IF EXISTS observed_at;

-- RULING F3: revaluation happens at each system's own observation time, which
-- a daily series cannot express. Anchored to the H.10 closes exactly as
-- `intraday_tick` is anchored to `benchmark_curve`.
CREATE TABLE IF NOT EXISTS "{S}".fx_intraday_tick (
    pair        text        NOT NULL,
    obs_ts      timestamptz NOT NULL,
    value_date  date        NOT NULL,
    rate        numeric     NOT NULL,
    provenance  text        NOT NULL,
    PRIMARY KEY (pair, obs_ts)
);

CREATE TABLE IF NOT EXISTS "{S}".break_record (
    break_id       text     PRIMARY KEY,
    trade_id       text     NOT NULL,
    system_a       text     NOT NULL,
    system_b       text     NOT NULL,
    raw_variance   numeric  NOT NULL,
    designed_class text     NOT NULL,   -- 'timing' | 'genuine' -- NOT trusted by the validator
    provenance     text     NOT NULL
);

-- RULING F13: thresholds are in PIPS, not raw rate units. A pip is 0.01 for
-- JPY pairs and 0.0001 for the rest, so one absolute threshold across six
-- pairs classifies USD/JPY and EUR/USD on scales 100x apart.
CREATE TABLE IF NOT EXISTS "{S}".materiality_threshold (
    intent          text    PRIMARY KEY,
    threshold_pips  numeric NOT NULL,
    provenance      text    NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".fx_pip_size (
    pair       text    PRIMARY KEY,
    pip_size   numeric NOT NULL,
    provenance text    NOT NULL   -- public: market convention
);

CREATE TABLE IF NOT EXISTS "{S}".part43_profile (
    dimension   text    NOT NULL,   -- 'pair' | 'hour' | 'action' | 'chain'
    key         text    NOT NULL,
    observed_n  integer NOT NULL,
    provenance  text    NOT NULL,
    source      text    NOT NULL,
    retrieved_at timestamptz NOT NULL,
    PRIMARY KEY (dimension, key)
);
"""

#: Market convention (public): 0.01 for any pair quoted in JPY, 0.0001
#: otherwise. RULING F13.
def pip_size_for(pair: str) -> Decimal:
    return Decimal("0.01") if "JPY" in pair else Decimal("0.0001")

#: The seven `break_record` columns this loader will ever read off a break
#: dict, keyed to the DDL column name. RULING F22: nothing else in a break
#: record is touched, ever — see module docstring.
BREAK_FIELD_MAP = {
    "break_id": "break_id",
    "trade_id": "trade_id",
    "system_a": "system_a",
    "system_b": "system_b",
    "raw_variance": "raw_diff_pips",
    "designed_class": "break_type",
    "provenance": "provenance",
}

CURRENCY_NOTES: list[str] = []


def load(name: str) -> dict:
    """Read one artifact, refusing a STALE one (`ccf/currency.py`)."""
    doc, note = verify_current(name)
    CURRENCY_NOTES.append(note)
    return doc


def build_rows(fx_doc: dict, ticks_doc: dict, profile_doc: dict):
    trades = fx_doc["trades"]
    system_records = fx_doc["system_records"]
    breaks = fx_doc["breaks"]
    thresholds = fx_doc["materiality_thresholds"]
    ticks = ticks_doc["ticks"]

    trade_rows = [
        (t["trade_id"], t["pair"], t["notional_band"], t["execution_ts"],
         t["value_date"], t["counterparty_lei"], t["provenance"])
        for t in trades
    ]

    # RULING F23: observed_at is deliberately not read here. Fluree owns it
    # (`ex:systemObservedAt`, load_fluree_wave12_fx.py) — see the DDL note.
    system_rows = [
        (r["trade_id"], r["system_name"], r["value_rate"],
         r["amendment_seq"], r["provenance"])
        for r in system_records
    ]

    tick_rows = [
        (t["pair"], t["obs_ts"], t["value_date"], t["rate"], t["provenance"])
        for t in ticks
    ]

    # RULING F22 — read EXACTLY these six fields off each break dict, via
    # BREAK_FIELD_MAP, never the dict directly. gap_s / true_a / true_b /
    # aligned_a / aligned_b / aligned_diff_pips / timing_component_pips /
    # classification_raw / classification_aligned / observed_a / observed_b /
    # local_drift_per_s / booking_error_pips / note are never referenced here.
    break_rows = [
        (
            b[BREAK_FIELD_MAP["break_id"]],
            b[BREAK_FIELD_MAP["trade_id"]],
            b[BREAK_FIELD_MAP["system_a"]],
            b[BREAK_FIELD_MAP["system_b"]],
            b[BREAK_FIELD_MAP["raw_variance"]],
            b[BREAK_FIELD_MAP["designed_class"]],
            b[BREAK_FIELD_MAP["provenance"]],
        )
        for b in breaks
    ]

    threshold_rows = [
        (m["intent"], m["threshold_pips"], m["provenance"])
        for m in thresholds
    ]

    pairs = sorted({t["pair"] for t in trades})
    pip_rows = [
        (pair, pip_size_for(pair), "public")
        for pair in pairs
    ]

    profile_source = profile_doc["_meta"]["source"]
    profile_retrieved_at = profile_doc["_meta"]["retrieved_at"]
    profile_rows = []
    for dimension in ("pair", "hour", "action", "chain"):
        for key, observed_n in profile_doc[f"{dimension}_mix" if dimension != "chain"
                                            else "chain_lengths"].items():
            profile_rows.append(
                (dimension, key, observed_n, "public", profile_source,
                 profile_retrieved_at)
            )

    return (trade_rows, system_rows, tick_rows, break_rows, threshold_rows,
            pip_rows, profile_rows)


def verify_f22(break_rows: list[tuple]) -> None:
    """RULING F22's own check, run against the STORED rows: does any
    `break_record` column, alone, partition the 60 breaks exactly along
    `designed_class`? Only `designed_class` should — by construction.

    `break_id` / `trade_id` are unique per row, so every value's group is a
    singleton and trivially "pure" — that is an identifier property, not a
    generalizable discriminator, and is reported as expected rather than as
    a defect.
    """
    columns = ("break_id", "trade_id", "system_a", "system_b",
               "raw_variance", "designed_class", "provenance")
    print("\n  RULING F22 verification — per-column partition of the 60 "
          "breaks by designed_class:")
    violations = []
    for idx, col in enumerate(columns):
        groups: dict = defaultdict(set)
        for row in break_rows:
            groups[row[idx]].add(row[5])  # row[5] is designed_class
        pure = all(len(v) == 1 for v in groups.values())
        n_distinct = len(groups)
        trivial = n_distinct == len(break_rows)  # every value unique
        if col == "designed_class":
            verdict = "PURE (expected — this IS the answer key)"
        elif pure and trivial:
            verdict = "pure, but TRIVIAL (identifier column, every value " \
                      "unique — not a generalizable discriminator)"
        elif pure:
            verdict = "PURE — RULING F22 VIOLATION"
            violations.append(col)
        else:
            verdict = "not pure (safe)"
        print(f"    {col:16} distinct={n_distinct:3}  {verdict}")

    if violations:
        raise RuntimeError(
            f"RULING F22 VIOLATED: column(s) {violations} partition the 60 "
            f"breaks exactly along designed_class without being an "
            f"identifier — a consumer could classify every break by reading "
            f"one column. Fix build_rows() before loading."
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fx_doc = load("wave12_fx.json")
    ticks_doc = load("wave12_fx_ticks.json")
    profile_doc = load("wave12_part43_profile.json")

    (trade_rows, system_rows, tick_rows, break_rows, threshold_rows,
     pip_rows, profile_rows) = build_rows(fx_doc, ticks_doc, profile_doc)

    break_type_counts = Counter(r[5] for r in break_rows)

    print(f"Wave 12 Task 14 — load into {S}\n")
    print("  artifact currency:")
    for note in CURRENCY_NOTES:
        print(f"    {note}")
    print()
    print(f"  fx_trade              {len(trade_rows):>6}")
    print(f"  system_trade_record   {len(system_rows):>6}")
    print(f"  fx_intraday_tick      {len(tick_rows):>6}")
    print(f"  break_record          {len(break_rows):>6}  "
          f"(designed_class: {dict(break_type_counts)})")
    print(f"  materiality_threshold {len(threshold_rows):>6}")
    print(f"  fx_pip_size           {len(pip_rows):>6}")
    print(f"  part43_profile        {len(profile_rows):>6}")
    print(f"  NOT loaded to Postgres: amendments "
          f"({len(fx_doc['amendments'])}, Fluree-only), clock_offsets "
          f"({len(fx_doc['clock_offsets'])}, Fluree-only)")

    # Counted expectations, not restated ones.
    expected = {
        "fx_trade": (len(trade_rows), 500),
        "system_trade_record": (len(system_rows), 1_815),
        "fx_intraday_tick": (len(tick_rows), 10_368),
        "break_record": (len(break_rows), 60),
        "materiality_threshold": (len(threshold_rows), 3),
        "fx_pip_size": (len(pip_rows), 6),
        "part43_profile": (len(profile_rows), 44),
    }
    mismatches = {k: v for k, v in expected.items() if v[0] != v[1]}
    if mismatches:
        raise RuntimeError(f"row-count mismatch vs. artifact expectation: "
                            f"{mismatches}")

    verify_f22(break_rows)

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".fx_trade '
            "(trade_id, pair, notional_band, execution_ts, value_date, "
            " counterparty_lei, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (trade_id) DO UPDATE SET "
            "pair=EXCLUDED.pair, notional_band=EXCLUDED.notional_band, "
            "execution_ts=EXCLUDED.execution_ts, "
            "value_date=EXCLUDED.value_date, "
            "counterparty_lei=EXCLUDED.counterparty_lei, "
            "provenance=EXCLUDED.provenance",
            trade_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".system_trade_record '
            "(trade_id, system_name, value_rate, amendment_seq, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (trade_id, system_name, amendment_seq) DO UPDATE SET "
            "value_rate=EXCLUDED.value_rate, "
            "provenance=EXCLUDED.provenance",
            system_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".fx_intraday_tick '
            "(pair, obs_ts, value_date, rate, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (pair, obs_ts) DO UPDATE SET "
            "value_date=EXCLUDED.value_date, rate=EXCLUDED.rate, "
            "provenance=EXCLUDED.provenance",
            tick_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".break_record '
            "(break_id, trade_id, system_a, system_b, raw_variance, "
            " designed_class, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (break_id) DO UPDATE SET "
            "trade_id=EXCLUDED.trade_id, system_a=EXCLUDED.system_a, "
            "system_b=EXCLUDED.system_b, "
            "raw_variance=EXCLUDED.raw_variance, "
            "designed_class=EXCLUDED.designed_class, "
            "provenance=EXCLUDED.provenance",
            break_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".materiality_threshold '
            "(intent, threshold_pips, provenance) VALUES (%s,%s,%s) "
            "ON CONFLICT (intent) DO UPDATE SET "
            "threshold_pips=EXCLUDED.threshold_pips, "
            "provenance=EXCLUDED.provenance",
            threshold_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".fx_pip_size '
            "(pair, pip_size, provenance) VALUES (%s,%s,%s) "
            "ON CONFLICT (pair) DO UPDATE SET "
            "pip_size=EXCLUDED.pip_size, provenance=EXCLUDED.provenance",
            pip_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".part43_profile '
            "(dimension, key, observed_n, provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (dimension, key) DO UPDATE SET "
            "observed_n=EXCLUDED.observed_n, provenance=EXCLUDED.provenance, "
            "source=EXCLUDED.source, retrieved_at=EXCLUDED.retrieved_at",
            profile_rows,
        )

        conn.commit()

        print()
        for table in ("fx_trade", "system_trade_record", "fx_intraday_tick",
                      "break_record", "materiality_threshold",
                      "fx_pip_size", "part43_profile"):
            cur.execute(f'SELECT COUNT(*) FROM "{S}".{table}')
            print(f"  {table:24} store count: {cur.fetchone()[0]}")

    print("\n  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
